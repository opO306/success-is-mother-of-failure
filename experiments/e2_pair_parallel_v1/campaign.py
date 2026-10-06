"""E2_PAIR_PARALLEL_V1 campaign (protocol.json). One record file per run; resumes by skipping existing records.

    python -m experiments.e2_pair_parallel_v1.campaign --out DIR --machine laptop|desktop [--phase gates|runs|all]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
PKG = "experiments.e2_pair_parallel_v1"
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
SCOPE = PROTO["scope"]
P = 128
CONFIGS = ["SER_E1", "SER_E2", "PAR_E1_W3", "PAR_E2_W3", "PAR_E1_W4", "PAR_E2_W4", "PAR_E1_W6", "PAR_E2_W6"]
EV = {"E1": "algebra", "E2": "rw:R1+R2"}
REPS = SCOPE["repetitions"]
CPU_CAP = 10800.0
SUSPECT = re.compile(r"python|roblox|codex|node", re.I)
SEALED = [f"experiments/e2_pair_parallel_v1/{f}" for f in
          ("protocol.json", "run.py", "campaign.py", "checker.py", "analyze.py")] + \
         [f"experiments/multiatom_parallel_v1/{f}" for f in ("run.py", "scenarios.py", "e2gate.py", "checker.py")] + \
         ["exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py",
          "experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/rewrite_pilot_a3/runner.py",
          "experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py"]


def horizons(machine):
    if machine == "desktop":
        ns = [3, 4, 6, 12]
        return [("H100", 100, ns), ("H1000", 1000, ns)]
    return [("H100", 100, SCOPE["N_list"]), ("H1000", 1000, [3, 4, 6, 12])]


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def contamination(rows):
    """Sealed rule: other processes summed >= 100 % of one logical CPU, or a suspect-named process >= 25 %."""
    total = sum(v for _, _, v in rows)
    suspects = [(n, pid, v) for n, pid, v in rows if SUSPECT.search(n or "") and v >= 25.0]
    return {"other_total_pct": round(total, 1), "suspects": suspects,
            "contaminated": total >= 100.0 or bool(suspects)}


class Camp:
    def __init__(self, out, machine):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.w = self.out / "work"
        self.w.mkdir(exist_ok=True)
        self.machine = machine
        self.m = PROTO["machines"][machine]
        self.rate = None

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(self.out / "campaign.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def spent(self):
        return sum(json.loads(f.read_text(encoding="utf-8")).get("total_cpu_s", 0) for f in self.out.glob("H*.json"))

    def snapshot(self, tag):
        """1 s snapshot of every other process (own process tree and System Idle Process excluded); stored."""
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

    def calibrate(self):
        f = self.out / "cycle_rate.json"
        if not f.exists():
            from experiments.multiatom_parallel_v1.run import cycle_rate
            rates = [cycle_rate() for _ in range(3)]
            f.write_text(json.dumps({"rates_hz": rates, "rate_hz": max(rates), "core": self.m["campaign_cpu"],
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
             "started": time.strftime("%Y-%m-%d %H:%M:%S"), "machine": self.machine, "machine_map": self.m,
             "host": platform.node()}
        f.write_text(json.dumps(s, indent=1), encoding="utf-8")

    def command(self, cfg, n, T, out):
        if cfg.startswith("SER_"):
            return [sys.executable, "-m", "experiments.multiatom_parallel_v1.run", "serial", EV[cfg[4:]], str(n),
                    str(T), str(P), str(self.m["serial_cpu"]), str(out)]
        _, e, w = cfg.split("_")
        W = int(w[1:])
        return [sys.executable, "-m", f"{PKG}.run", EV[e], str(n), str(T), str(P), str(W), str(self.m["main_cpu"]),
                ",".join(str(c) for c in self.m["worker_cores"][:W]), str(out)]

    def run(self, name, cfg, n, T, group_snapshot):
        f = self.out / f"{name}.json"
        if f.exists():
            return
        if self.spent() > CPU_CAP:
            self.log(f"CPU cap reached before {name}: STOP")
            raise SystemExit(2)
        tmp = self.w / f"{name}.out.json"
        cmd = self.command(cfg, n, T, tmp)
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        e2e = time.perf_counter() - t0
        if r.returncode != 0:
            self.log(f"ERROR {name}: rc {r.returncode} {r.stderr[-600:]}")
            raise SystemExit(3)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        cyc = d["main_cycles"] + sum(b["cycles"] for b in d.get("worker_bye", []))
        d.update(name=name, config=cfg, end_to_end_wall_s=e2e, command=cmd[3:], total_cycles=cyc,
                 cycle_rate_hz=self.rate, total_cpu_s=cyc / self.rate,
                 total_cpu_tick_s=d["main_cpu_s"] + sum(d.get("worker_cpu_s", [])),
                 group_contaminated=group_snapshot["contaminated"], group_snapshot_tag=group_snapshot["tag"])
        f.write_text(json.dumps(d), encoding="utf-8")
        tmp.unlink()
        self.log(f"done {name} {d['outcome']} steps {d['completed_steps']} e2e {e2e:.2f} loop {d['loop_wall_s']:.2f} "
                 f"cpu {d['total_cpu_s']:.2f}")


def phase_gates(c):
    g = c.out / "gates"
    g.mkdir(exist_ok=True)
    jobs = [(["experiments.rewrite_pilot_a3.runner", "refs", str(g / "refs.json")], "refs.json"),
            (["experiments.rewrite_pilot_a3.runner", "verify", "rw:R1+R2", str(g / "refs.json"), str(g / "verify.json")],
             "verify.json"),
            (["experiments.rewrite_pilot_a3.runner", "sympy", "rw:R1+R2", str(g / "sympy.json")], "sympy.json"),
            (["experiments.multiatom_parallel_v1.e2gate", str(P), str(g / "e2_domain.json")], "e2_domain.json")]
    for args, fn in jobs:
        if not (g / fn).exists():
            r = subprocess.run([sys.executable, "-m", *args], cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                c.log(f"ERROR gate {fn}: {r.stderr[-400:]}")
    v = json.loads((g / "verify.json").read_text(encoding="utf-8"))
    sy = json.loads((g / "sympy.json").read_text(encoding="utf-8"))
    dm = json.loads((g / "e2_domain.json").read_text(encoding="utf-8"))
    c.log(f"E2 gates S1-S6 {v.get('PASS_S1_S6_except_S3b')} sympy {sy.get('sympy_zero')} "
          f"new-domain containment {dm.get('PASS')} ({dm.get('n_distinct_R2')} distinct R^2)")


def phase_runs(c):
    for rep in range(REPS):
        for hname, T, ns in horizons(c.machine):
            for n in ns:
                snap = c.snapshot(f"{hname}__N{n}__r{rep}")
                k = (2 * rep) % len(CONFIGS)
                for cfg in CONFIGS[k:] + CONFIGS[:k]:
                    c.run(f"{hname}__N{n}__{cfg}__r{rep}", cfg, n, T, snap)
        c.log(f"repetition {rep} finished; campaign CPU {c.spent():.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--machine", required=True, choices=sorted(PROTO["machines"]))
    ap.add_argument("--phase", default="all")
    a = ap.parse_args()
    c = Camp(a.out, a.machine)
    psutil.Process().cpu_affinity([c.m["campaign_cpu"]])
    c.seal()
    c.calibrate()
    c.log(f"E2_PAIR_PARALLEL_V1 phase {a.phase} machine {a.machine} map {c.m} pid {os.getpid()}")
    c.snapshot("start")
    if a.phase in ("gates", "all"):
        phase_gates(c)
    if a.phase in ("runs", "all"):
        phase_runs(c)
    c.snapshot("end")
    c.log("finished")


if __name__ == "__main__":
    main()
