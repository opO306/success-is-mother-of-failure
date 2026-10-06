"""MULTIATOM_PARALLEL_V1 campaign (protocol.json). One record file per run; resumes by skipping existing records.
The campaign process is pinned to logical CPU 3 and only launches and waits.

    python -m experiments.multiatom_parallel_v1.campaign --out DIR [--phase gates|runs|all]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
PKG = "experiments.multiatom_parallel_v1"
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
N_LIST = PROTO["scenario_family"]["N_list"]
HORIZONS = [("H100", 100, N_LIST), ("H1000", 1000, [2, 3, 4, 6, 8, 12])]
P = PROTO["precision_and_horizons"]["p"]
MACHINES = PROTO["amendment_2_execution_machine"]["machines"]
WORKER_CORES = [2, 4, 6, 8, 10, 0]
MAIN_CPU, SERIAL_CPU, CAMPAIGN_CPU = 1, 2, 3
MACHINE = "desktop"


def set_machine(name):
    global WORKER_CORES, MAIN_CPU, SERIAL_CPU, CAMPAIGN_CPU, MACHINE
    m = MACHINES[name]
    WORKER_CORES, MAIN_CPU, SERIAL_CPU, CAMPAIGN_CPU = m["worker_cores"], m["main_cpu"], m["serial_cpu"], m["campaign_cpu"]
    MACHINE = name
CONFIGS = ["SER_E1", "SER_E2", "PAR_1", "PAR_2", "PAR_3", "PAR_4", "PAR_6"]
REPS = 3
CPU_CAP = 10800.0
SEALED = [f"experiments/multiatom_parallel_v1/{f}" for f in
          ("protocol.json", "scenarios.py", "run.py", "e2gate.py", "campaign.py", "checker.py", "analyze.py")] + \
         ["exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py",
          "experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/rewrite_pilot_a3/runner.py",
          "experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py"]


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def command(cfg, n, T, out):
    if cfg.startswith("SER_"):
        ev = {"SER_E1": "algebra", "SER_E2": "rw:R1+R2"}[cfg]
        return [sys.executable, "-m", f"{PKG}.run", "serial", ev, str(n), str(T), str(P), str(SERIAL_CPU), str(out)]
    W = int(cfg.split("_")[1])
    return [sys.executable, "-m", f"{PKG}.run", "parallel", str(n), str(T), str(P), str(W), str(MAIN_CPU),
            ",".join(str(c) for c in WORKER_CORES[:W]), str(out)]


class Camp:
    def __init__(self, out):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.w = self.out / "work"
        self.w.mkdir(exist_ok=True)

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(self.out / "campaign.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def spent(self):
        return sum(json.loads(f.read_text(encoding="utf-8")).get("total_cpu_s", 0)
                   for f in self.out.glob("H*.json"))

    def snapshot(self):
        procs = list(psutil.process_iter(["pid", "name"]))
        for pr in procs:
            try:
                pr.cpu_percent(None)
            except psutil.Error:
                pass
        time.sleep(1.0)
        busy = []
        for pr in procs:
            try:
                v = pr.cpu_percent(None)
                if v >= 5.0:
                    busy.append((pr.info["name"], pr.info["pid"], round(v, 1)))
            except psutil.Error:
                pass
        self.log(f"load snapshot: system {psutil.cpu_percent(interval=0.5):.0f}% busy "
                 f"{sorted(busy, key=lambda x: -x[2])[:6]}")

    def seal(self):
        f = self.out / "execution_seal.json"
        if f.exists():
            return
        s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
             "status_porcelain": git("status", "--porcelain"), "origin_master": git("rev-parse", "origin/master"),
             "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
             "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
             "started": time.strftime("%Y-%m-%d %H:%M:%S"), "campaign_cpu": CAMPAIGN_CPU,
             "machine": MACHINE, "machine_map": MACHINES[MACHINE], "host": __import__("platform").node()}
        f.write_text(json.dumps(s, indent=1), encoding="utf-8")

    def run(self, name, cfg, n, T):
        f = self.out / f"{name}.json"
        if f.exists():
            return
        if self.spent() > CPU_CAP:
            self.log(f"CPU cap reached before {name}: STOP")
            raise SystemExit(2)
        tmp = self.w / f"{name}.out.json"
        cmd = command(cfg, n, T, tmp)
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        e2e = time.perf_counter() - t0
        if r.returncode != 0:
            self.log(f"ERROR {name}: rc {r.returncode} {r.stderr[-600:]}")
            raise SystemExit(3)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        d.update(name=name, config=cfg, end_to_end_wall_s=e2e, command=cmd[3:],
                 total_cpu_s=d["main_cpu_s"] + sum(d.get("worker_cpu_s", [])),
                 cpu_percent_after=psutil.cpu_percent(interval=None))
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
            ([f"{PKG}.e2gate", str(P), str(g / "e2_domain.json")], "e2_domain.json")]
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
        for hname, T, ns in HORIZONS:
            for n in ns:
                c.snapshot()
                cfgs = CONFIGS[rep:] + CONFIGS[:rep]
                for cfg in cfgs:
                    c.run(f"{hname}__N{n}__{cfg}__r{rep}", cfg, n, T)
        c.log(f"repetition {rep} finished; campaign CPU {c.spent():.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", default="all")
    ap.add_argument("--machine", default="desktop", choices=sorted(MACHINES))
    a = ap.parse_args()
    set_machine(a.machine)
    psutil.Process().cpu_affinity([CAMPAIGN_CPU])
    c = Camp(a.out)
    c.seal()
    c.log(f"MULTIATOM_PARALLEL_V1 phase {a.phase} machine {MACHINE} workers {WORKER_CORES} main {MAIN_CPU} "
          f"serial {SERIAL_CPU} campaign {CAMPAIGN_CPU}")
    if a.phase in ("gates", "all"):
        phase_gates(c)
    if a.phase in ("runs", "all"):
        phase_runs(c)
    c.log("finished")


if __name__ == "__main__":
    main()
