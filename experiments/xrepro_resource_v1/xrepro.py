"""XREPRO_RESOURCE_V1 runner (protocol.json): the minimal cross-reproduction set of RESOURCE_EVOLUTION_PILOT_V1 on one
machine. Uses the sealed run-2 executor unchanged; only the in-memory core map (selector.PHYS_ORDER / ORCH_CPU) is set.

    python -m experiments.xrepro_resource_v1.xrepro --out DIR --machine desktop|laptop [--phase env|gates|t0|batch|s4|all]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from experiments.resource_evolution_v1 import campaign as CA
from experiments.resource_evolution_v1 import orch as O
from experiments.resource_evolution_v1 import selector as SEL

ROOT = SEL.ROOT
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
OWN = ["experiments/xrepro_resource_v1/protocol.json", "experiments/xrepro_resource_v1/xrepro.py",
       "experiments/xrepro_resource_v1/compare.py"]
RUN2_CAL = ROOT / "docs/active/resource_evolution_v1/run2/calibration.json"
T0_REQS = [(s, T) for T in (100, 1000) for s in SEL.SCEN] + [("A2_bound", 3000)]
E0_REQS = (("A2_bound", 100), ("A3_high", 100))


def set_machine(name):
    m = PROTO["machines"][name]
    SEL.PHYS_ORDER[:] = m["worker_core_order"]          # in-memory only; orch/campaign read it at call time
    SEL.ORCH_CPU = m["orchestrator_cpu"]
    O.pin_self()
    return m


def _ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip()


def phase_env(c, machine):
    def env():
        import mpmath
        import mpmath.libmp as ML
        import psutil
        import sympy
        try:
            import gmpy2  # noqa: F401
            gm = True
        except ImportError:
            gm = False
        files = CA.SEALED + OWN
        return {"machine": machine, "host": platform.node(), "python": sys.version, "executable": sys.executable,
                "platform": platform.platform(), "processor": platform.processor(),
                "cpu_name": _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"),
                "os_version": _ps("(Get-CimInstance Win32_OperatingSystem).Version"),
                "cpu_count_logical": psutil.cpu_count(True), "cpu_count_physical": psutil.cpu_count(False),
                "ram_bytes": psutil.virtual_memory().total, "mpmath": mpmath.__version__, "mpmath_backend": ML.BACKEND,
                "psutil": psutil.__version__, "sympy": sympy.__version__, "gmpy2_importable": gm,
                "git_head": CA.git("rev-parse", "HEAD"), "git_branch": CA.git("branch", "--show-current"),
                "git_status_porcelain": CA.git("status", "--porcelain"),
                "source_sha256_lf": {f: CA.lf(ROOT / f) for f in files},
                "core_map": PROTO["machines"][machine], "orch_affinity": __import__("psutil").Process().cpu_affinity(),
                "total_cpu_s": 0.0}
    c.rec("X1X2__env", env)


def phase_gates(c):
    gdir = c.out / "X3_e2_gates"
    gdir.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    for args, fn in ((["refs", str(gdir / "refs.json")], "refs.json"),
                     (["verify", "rw:R1+R2", str(gdir / "refs.json"), str(gdir / "verify.json")], "verify.json"),
                     (["sympy", "rw:R1+R2", str(gdir / "sympy.json")], "sympy.json")):
        if not (gdir / fn).exists():
            r = subprocess.run([sys.executable, "-m", "experiments.rewrite_pilot_a3.runner", *args], cwd=ROOT,
                               capture_output=True, text=True)
            if r.returncode != 0:
                c.log(f"ERROR gate {fn}: {r.stderr[-400:]}")
    v = json.loads((gdir / "verify.json").read_text(encoding="utf-8"))
    sy = json.loads((gdir / "sympy.json").read_text(encoding="utf-8"))
    c.log(f"X3 E2 gates S1-S6 {v.get('PASS_S1_S6_except_S3b')} sympy {sy.get('sympy_zero')} "
          f"wall {time.perf_counter() - t0:.1f}")


def phase_t0(c):
    order = SEL.PHYS_ORDER
    for s, T in T0_REQS:
        L = SEL.line(s, T) + 8
        evs = [SEL.E1, SEL.E2] + ([SEL.E0] if (s, T) in E0_REQS else [])
        for ev in evs:
            for pos, cpu in (("first", order[0]), ("last", order[-1])):
                spec = {"evaluator": ev, "scenario": s, "T": T, "mode": "single", "start_p": L}
                tag = f"X4_{ev}_{s}_{T}_{pos}".replace(":", "-").replace("+", "_")
                c.rec(f"X4__{ev.replace(':', '-').replace('+', '_')}__{s}_{T}__{pos}",
                      lambda: O.run_workers(c.w, tag, [spec], CA.h0_env([cpu]), s, T))


def phase_batch(c):
    us = json.loads(RUN2_CAL.read_text(encoding="utf-8"))["u"]      # run-2 LPT order, not re-measured
    kmax = len(SEL.PHYS_ORDER)
    ks = [1, 3, kmax]
    c.load_snapshot()
    for rep in range(3):
        order = ks[rep:] + ks[:rep]
        for k in order:
            for plan in (["BASE", "BASE_E2"] if rep % 2 == 0 else ["BASE_E2", "BASE"]):
                c.rec(f"X6__{plan}__k{k}__r{rep}",
                      lambda: O.run_batch(c.w, f"X6_{plan}_{k}_{rep}", plan, SEL.EVAL, k, us=us))
        c.load_snapshot()


def phase_s4(c):
    cpus = ",".join(str(x) for x in SEL.PHYS_ORDER[:4])
    for s in ("A3_low", "A3_high"):
        def s4():
            f = c.w / f"X8_{s}_100.json"
            t0 = time.perf_counter()
            subprocess.run([sys.executable, "-m", "experiments.resource_evolution_v1.pairloop", s, "100", "128", "3",
                            cpus, str(f)], cwd=ROOT, check=True)
            d = json.loads(f.read_text(encoding="utf-8"))
            d["wall_s"] = time.perf_counter() - t0
            d["total_cpu_s"] = d["serial"]["cpu_s"] + d["parallel"]["main_cpu_s"] + sum(d["parallel"]["worker_cpu_s"])
            d["status"] = "BIT_IDENTICAL" if d["bit_identical"] else "MISMATCH"
            return d
        c.rec(f"X8__S4__{s}_100", s4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--machine", required=True, choices=sorted(PROTO["machines"]))
    ap.add_argument("--phase", default="all")
    a = ap.parse_args()
    set_machine(a.machine)
    c = CA.Camp(a.out)
    c.seal()
    c.log(f"XREPRO machine {a.machine} core order {SEL.PHYS_ORDER} orch {SEL.ORCH_CPU} phase {a.phase}")
    phases = {"env": lambda: phase_env(c, a.machine), "gates": lambda: phase_gates(c), "t0": lambda: phase_t0(c),
              "batch": lambda: phase_batch(c), "s4": lambda: phase_s4(c)}
    for name in (phases if a.phase == "all" else [a.phase]):
        c.log(f"phase {name} start")
        phases[name]()
        c.log(f"phase {name} finished; CPU so far {c.spent():.0f}s")


if __name__ == "__main__":
    main()
