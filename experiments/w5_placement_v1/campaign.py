"""W5_PLACEMENT_V1 campaign (protocol.json). Laptop only. One record file per run; resumes by skipping existing records.

    python -m experiments.w5_placement_v1.campaign --out DIR
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import psutil

from experiments.e2_pair_parallel_v1.campaign import contamination, git, lf
from experiments.w5_placement_v1 import topology as TOPO
from experiments.w5_placement_v1.plan import ExecutionPlan

ROOT = Path(__file__).resolve().parents[2]
PKG = "experiments.w5_placement_v1"
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
SCOPE = PROTO["scope"]
CFG = PROTO["configurations"]
CONFIGS = ["SER_E2", "W4_DEDICATED", "W5_DEDICATED", "W6_SHARED"]
CAMPAIGN_CPU = 0
CPU_CAP = 5000.0
SEALED = [f"experiments/w5_placement_v1/{f}" for f in
          ("protocol.json", "plan.py", "topology.py", "run.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["experiments/e2_pair_parallel_v1/run.py", "experiments/e2_pair_parallel_v1/campaign.py",
          "experiments/multiatom_parallel_v1/run.py", "experiments/multiatom_parallel_v1/scenarios.py",
          "exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py",
          "experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/formula_repro_b_v0/harness.py",
          "experiments/formula_repro_b_v0/upstream/probe.py"]


def plan_for(cfg):
    c = CFG[cfg]
    return ExecutionPlan(evaluator="rw:R1+R2", precision=SCOPE["p"], backend=c["backend"],
                         worker_count=c["worker_count"], main_cpu=c["main_cpu"], worker_cpus=tuple(c["worker_cpus"]))


def expected_topology_ok(t):
    return t["logical"] == 6 and t["physical"] == 6 and all(
        not c["smt"] and c["group_cpus"] == [[0, [k]]] for k, c in enumerate(t["cores"]))


class Camp:
    def __init__(self, out):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.w = self.out / "work"
        self.w.mkdir(exist_ok=True)
        self.rate = None

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(self.out / "campaign.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def spent(self):
        return sum(json.loads(f.read_text(encoding="utf-8")).get("total_cpu_s", 0) for f in self.out.glob("N*.json"))

    def snapshot(self, tag):
        me = psutil.Process()
        own = {me.pid} | {c.pid for c in me.children(recursive=True)}
        procs = [pr for pr in psutil.process_iter(["pid", "name"]) if pr.pid not in own and pr.pid != 0]
        for pr in procs:
            try:
                pr.cpu_percent(None)
            except psutil.Error:
                pass
        time.sleep(1.0)
        rows = []
        for pr in procs:
            try:
                v = pr.cpu_percent(None)
                if v > 0:
                    rows.append((pr.info["name"], pr.pid, round(v, 1)))
            except psutil.Error:
                pass
        rows.sort(key=lambda x: -x[2])
        c = contamination(rows)
        snap = {"tag": tag, "time": time.strftime("%H:%M:%S"), "rows": rows[:40], **c}
        with open(self.out / "load_snapshots.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(snap) + "\n")
        self.log(f"load {tag}: others {c['other_total_pct']}% suspects {c['suspects']} "
                 f"{'CONTAMINATED' if c['contaminated'] else 'clean'} top {rows[:4]}")
        return snap

    def topology(self):
        t = TOPO.summary()
        (self.out / "topology.json").write_text(json.dumps(t, indent=1), encoding="utf-8")
        if not expected_topology_ok(t):
            self.log(f"TOPOLOGY DIFFERS FROM PROTOCOL: {t}")
            raise SystemExit(4)
        self.log("topology: 6 cores x 1 logical CPU, no SMT, core k = CPU k (as sealed)")

    def calibrate(self):
        f = self.out / "cycle_rate.json"
        if not f.exists():
            from experiments.multiatom_parallel_v1.run import cycle_rate
            rates = [cycle_rate() for _ in range(3)]
            f.write_text(json.dumps({"rates_hz": rates, "rate_hz": max(rates), "core": CAMPAIGN_CPU,
                                     "method": "max over 3 x 20 busy loops of 50 ms of cycles/wall"}, indent=1),
                         encoding="utf-8")
        self.rate = json.loads(f.read_text(encoding="utf-8"))["rate_hz"]
        self.log(f"cycle rate {self.rate / 1e9:.4f} GHz")

    def seal(self):
        f = self.out / "execution_seal.json"
        if f.exists():
            return
        s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
             "status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
             "untracked": git("status", "--porcelain", "--untracked-files=all"),
             "origin_master": git("rev-parse", "origin/master"),
             "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
             "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
             "started": time.strftime("%Y-%m-%d %H:%M:%S"), "host": platform.node(), "campaign_cpu": CAMPAIGN_CPU}
        f.write_text(json.dumps(s, indent=1), encoding="utf-8")

    def run(self, name, cfg, n, T, snap):
        f = self.out / f"{name}.json"
        if f.exists():
            return
        if self.spent() > CPU_CAP:
            self.log(f"CPU cap reached before {name}: STOP")
            raise SystemExit(2)
        plan = plan_for(cfg).validate(logical_cpus=psutil.cpu_count(True))
        pf = self.w / f"{name}.plan.json"
        pf.write_text(plan.to_json(), encoding="utf-8")
        tmp = self.w / f"{name}.out.json"
        cmd = [sys.executable, "-m", f"{PKG}.run", str(pf), str(n), str(T), str(tmp)]
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        e2e = time.perf_counter() - t0
        if r.returncode != 0:
            self.log(f"ERROR {name}: rc {r.returncode} {r.stderr[-600:]}")
            raise SystemExit(3)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        wcyc = [b["cycles"] for b in d.get("worker_bye", [])]
        cyc = d["main_cycles"] + sum(wcyc)
        d.update(name=name, config=cfg, end_to_end_wall_s=e2e, total_cycles=cyc, cycle_rate_hz=self.rate,
                 total_cpu_s=cyc / self.rate, main_cpu_cycle_s=d["main_cycles"] / self.rate,
                 worker_cpu_cycle_s=[c / self.rate for c in wcyc],
                 total_cpu_tick_s=d["main_cpu_s"] + sum(d.get("worker_cpu_s", [])),
                 group_contaminated=snap["contaminated"], group_snapshot_tag=snap["tag"])
        f.write_text(json.dumps(d), encoding="utf-8")
        tmp.unlink()
        busy = [round(b["busy_wall_s"], 2) for b in d.get("worker_bye", [])]
        self.log(f"done {name} {d['outcome']} e2e {e2e:.2f} loop {d['loop_wall_s']:.2f} cpu {d['total_cpu_s']:.2f} "
                 f"busy {busy}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    psutil.Process().cpu_affinity([CAMPAIGN_CPU])
    c = Camp(a.out)
    c.topology()
    c.seal()
    c.calibrate()
    c.log(f"W5_PLACEMENT_V1 pid {os.getpid()} configs {CONFIGS}")
    c.snapshot("start")
    T = SCOPE["T"]
    for rep in range(SCOPE["repetitions"]):
        for n in SCOPE["N"]:
            snap = c.snapshot(f"N{n}__r{rep}")
            k = rep % len(CONFIGS)
            for cfg in CONFIGS[k:] + CONFIGS[:k]:
                c.run(f"N{n}__{cfg}__r{rep}", cfg, n, T, snap)
        c.log(f"repetition {rep} finished; campaign CPU {c.spent():.0f}s")
    c.snapshot("end")
    c.log("finished")


if __name__ == "__main__":
    main()
