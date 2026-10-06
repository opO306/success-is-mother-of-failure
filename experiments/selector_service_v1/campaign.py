"""SELECTOR_SERVICE_V1 campaign (protocol.json). Laptop only. One file per service run and per shadow run; resumes by
skipping existing files.

    python -m experiments.selector_service_v1.campaign --out DIR
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
from experiments.selector_service_v1 import service as SV
from experiments.selector_service_v1.selector import fixed_plan
from experiments.w5_placement_v1 import topology as TOPO
from experiments.w5_placement_v1.campaign import expected_topology_ok

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REQUESTS = [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
REPS = PROTO["evaluation_requests"]["repetitions"]
STRATEGIES = [("SEL_WALL", "SELECTOR", "WALL_MIN"), ("SEL_CPU", "SELECTOR", "CPU_MIN"), ("FIXED_W6", "FIXED:W6", None)]
CAMPAIGN_CPU = 0
CPU_CAP = 12000.0
SEALED = [f"experiments/selector_service_v1/{f}" for f in
          ("protocol.json", "selector.py", "service.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["experiments/precision_pilot_a1/policies.py", "experiments/w5_placement_v1/plan.py",
          "experiments/w5_placement_v1/run.py", "experiments/w5_placement_v1/topology.py",
          "experiments/e2_pair_parallel_v1/run.py", "experiments/multiatom_parallel_v1/run.py",
          "experiments/multiatom_parallel_v1/scenarios.py", "exact_expression_gate_v1/stream.py",
          "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py",
          "experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/formula_repro_b_v0/harness.py",
          "experiments/formula_repro_b_v0/upstream/probe.py"]


class Camp:
    def __init__(self, out):
        self.out = Path(out).resolve()
        for sub in ("work", "service", "shadow", "probes"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        self.rate, self.snap, self.k = None, None, 0

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(self.out / "campaign.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def spent(self):
        tot = 0.0
        for f in (self.out / "service").glob("*.json"):
            tot += sum(p["record"]["total_cpu_s"] for p in json.loads(f.read_text(encoding="utf-8"))["passes"])
        for f in (self.out / "shadow").glob("*.json"):
            tot += json.loads(f.read_text(encoding="utf-8"))["total_cpu_s"]
        return tot

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
                 f"{'CONTAMINATED' if c['contaminated'] else 'clean'} top {rows[:3]}")
        self.snap = snap
        return snap

    def setup(self, check_topology=True):
        t = TOPO.summary()
        (self.out / "topology.json").write_text(json.dumps(t, indent=1), encoding="utf-8")
        self.topology = t
        if check_topology and not expected_topology_ok(t):
            self.log(f"TOPOLOGY DIFFERS FROM PROTOCOL: {t}")
            raise SystemExit(4)
        f = self.out / "execution_seal.json"
        if not f.exists():
            s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
                 "status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
                 "untracked": git("status", "--porcelain", "--untracked-files=all"),
                 "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
                 "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
                 "started": time.strftime("%Y-%m-%d %H:%M:%S"), "host": platform.node(), "campaign_cpu": CAMPAIGN_CPU}
            f.write_text(json.dumps(s, indent=1), encoding="utf-8")
        f = self.out / "cycle_rate.json"
        if not f.exists():
            from experiments.multiatom_parallel_v1.run import cycle_rate
            rates = [cycle_rate() for _ in range(3)]
            f.write_text(json.dumps({"rates_hz": rates, "rate_hz": max(rates), "core": CAMPAIGN_CPU}, indent=1),
                         encoding="utf-8")
        self.rate = json.loads(f.read_text(encoding="utf-8"))["rate_hz"]
        self.log(f"cycle rate {self.rate / 1e9:.4f} GHz")

    def execute(self, plan, N, T):
        """One fresh pass through the unchanged W5_PLACEMENT_V1 runner; returns the enriched record."""
        if self.spent() > CPU_CAP:
            self.log("CPU cap reached: STOP")
            raise SystemExit(2)
        self.k += 1
        pf = self.out / "work" / f"pass_{os.getpid()}_{self.k}.plan.json"
        pf.write_text(plan.to_json(), encoding="utf-8")
        tmp = pf.with_suffix(".out.json")
        cmd = [sys.executable, "-m", "experiments.w5_placement_v1.run", str(pf), str(N), str(T), str(tmp)]
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        e2e = time.perf_counter() - t0
        if r.returncode != 0:
            self.log(f"ERROR pass {plan}: rc {r.returncode} {r.stderr[-600:]}")
            raise SystemExit(3)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        tmp.unlink()
        pf.unlink()
        wcyc = [b["cycles"] for b in d.get("worker_bye", [])]
        cyc = d["main_cycles"] + sum(wcyc)
        d.update(end_to_end_wall_s=e2e, total_cycles=cyc, cycle_rate_hz=self.rate, total_cpu_s=cyc / self.rate,
                 main_cpu_cycle_s=d["main_cycles"] / self.rate, worker_cpu_cycle_s=[c / self.rate for c in wcyc],
                 group_contaminated=self.snap["contaminated"], group_snapshot_tag=self.snap["tag"])
        for k in ("endpoints_scaled",):            # kept: the checker re-derives cells from them
            d.setdefault(k, None)
        self.log(f"  pass N{N} T{T} p{plan.precision} {plan.backend} W{plan.worker_count} {d['outcome']} "
                 f"e2e {e2e:.2f} cpu {d['total_cpu_s']:.2f}")
        return d

    def service(self, name, N, T, strategy, goal):
        f = self.out / "service" / f"{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        res = SV.run_request(N, T, strategy, self.topology, self.execute, goal=goal)
        res.update(name=name, group_snapshot_tag=self.snap["tag"] if self.snap else None)
        f.write_text(json.dumps(res), encoding="utf-8")
        self.log(f"service {name}: {res['status']} passes {res['p_sequence']} wall {res['service_wall_s']:.2f}")
        return res

    def shadow(self, name, N, T, kind, p):
        f = self.out / "shadow" / f"{name}.json"
        if f.exists():
            return
        rec = self.execute(fixed_plan(kind, p), N, T)
        rec.update(name=name, shadow_kind=kind, requested_p=p)
        f.write_text(json.dumps(rec), encoding="utf-8")


def probes(c):
    """Refusal probes kept in the evidence: unsupported T and a GPU plan (both must execute zero passes)."""
    def none_executor(plan, N, T):
        raise AssertionError("a probe must not execute a pass")
    for name, N, T, strategy, goal in (("unsupported_T500_SEL_WALL", 5, 500, "SELECTOR", "WALL_MIN"),
                                       ("unsupported_T500_FIXED_W6", 5, 500, "FIXED:W6", None),
                                       ("gpu_plan_N5_T100", 5, 100, "FIXED:GPU", None)):
        res = SV.run_request(N, T, strategy, c.topology, none_executor, goal=goal)
        res["name"] = name
        (c.out / "probes" / f"{name}.json").write_text(json.dumps(res), encoding="utf-8")
        c.log(f"probe {name}: {res['status']} passes {res['n_passes']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    psutil.Process().cpu_affinity([CAMPAIGN_CPU])
    c = Camp(a.out)
    c.setup()
    c.log(f"SELECTOR_SERVICE_V1 pid {os.getpid()} requests {REQUESTS} reps {REPS}")
    c.snapshot("start")
    probes(c)
    for rep in range(REPS):
        for N, T in REQUESTS:
            c.snapshot(f"N{N}_T{T}__r{rep}")
            k = rep % len(STRATEGIES)
            seqs = {}
            for label, strategy, goal in STRATEGIES[k:] + STRATEGIES[:k]:
                res = c.service(f"N{N}_T{T}__{label}__r{rep}", N, T, strategy, goal)
                seqs[label] = res["p_sequence"]
            for i, p in enumerate(seqs["SEL_WALL"]):
                for kind in (("W3", "W4") if (i + rep) % 2 == 0 else ("W4", "W3")):
                    c.shadow(f"N{N}_T{T}__p{p}__{kind}__r{rep}", N, T, kind, p)
        c.log(f"repetition {rep} finished; campaign CPU {c.spent():.0f}s")
    c.snapshot("end")
    c.log("finished")


if __name__ == "__main__":
    main()
