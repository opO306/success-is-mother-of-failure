"""RESOURCE_EVOLUTION_PILOT_V1 campaign (protocol.json): CAL, T0..T10. One record file per run; resumes by skipping
existing records. The orchestrator (this process) is pinned to logical CPU 1.

    python -m experiments.resource_evolution_v1.campaign --out DIR --phase CAL|T0|T1|T2|T34|T567|T8|T9|T10|all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

from . import orch as O
from . import selector as SEL
from . import verifier as VF

ROOT = SEL.ROOT
PKG = "experiments.resource_evolution_v1"
CPU_CAP = 14400.0
SEALED = ["experiments/resource_evolution_v1/" + f for f in
          ("protocol.json", "selector.py", "verifier.py", "worker.py", "orch.py", "vserver.py", "pairloop.py",
           "floatcand.py", "campaign.py")] + \
         ["experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a2t/frozen_policy_params_a1.json",
          "experiments/precision_pilot_a1/policies.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/rewrite_pilot_a3/runner.py",
          "experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py",
          "exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py"]


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


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
        if not hasattr(self, "_spent"):
            self._spent = sum(json.loads(f.read_text(encoding="utf-8")).get("total_cpu_s", 0)
                              for f in self.out.glob("*.json") if f.name not in ("execution_seal.json", "calibration.json"))
        return self._spent

    def load_snapshot(self):
        import psutil
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
        self.log(f"load snapshot: system {psutil.cpu_percent(interval=0.5):.0f}% busy {sorted(busy, key=lambda x: -x[2])[:6]}")

    def rec(self, name, fn):
        f = self.out / f"{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        if self.spent() > CPU_CAP:
            self.log(f"CPU cap reached before {name}: STOP")
            raise SystemExit(2)
        d = fn()
        d["name"] = name
        d["load"] = {"cpu_percent_after": __import__("psutil").cpu_percent(interval=None)}
        f.write_text(json.dumps(d, indent=1), encoding="utf-8")
        self._spent = self.spent() + d.get("total_cpu_s", 0)
        st = d.get("status") or d.get("summary") or ""
        self.log(f"done {name} {st} wall {d.get('wall_s', 0):.2f} cpu {d.get('total_cpu_s', 0):.2f}")
        return d

    def seal(self):
        f = self.out / "execution_seal.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
             "status_porcelain": git("status", "--porcelain"), "origin_master": git("rev-parse", "origin/master"),
             "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
             "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
             "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        f.write_text(json.dumps(s, indent=1), encoding="utf-8")
        return s

    def u(self):
        return json.loads((self.out / "calibration.json").read_text(encoding="utf-8"))["u"]


def h0_env(cores=None):
    e = SEL.env_for("H0", 1.0)
    if cores is not None:
        e.update(cores=len(cores), core_set=list(cores))
    return e


def phase_cal(c):
    rows = []
    for rep in range(3):
        for s, T in SEL.TRAIN:
            d = c.rec(f"CAL__{s}_{T}__r{rep}", lambda: O.run_plan(c.w, f"CAL_{s}_{T}_{rep}", "BASE", h0_env([2]), s, T))
            w = d["workers"][0]
            rows.append((s, T, w["passes"][0]["cpu_s"], w["cpu_s"] - sum(p["cpu_s"] for p in w["passes"])))
    o = statistics.median(r[3] for r in rows)
    kappa = {s: statistics.median(r[2] / r[1] for r in rows if r[0] == s) for s in SEL.SCEN}
    u = {f"{s}@{T}": o + kappa[s] * T for s in SEL.SCEN for T in (100, 1000, 3000)}
    (c.out / "calibration.json").write_text(json.dumps({"o": o, "kappa": kappa, "u": u, "rows": rows}, indent=1),
                                            encoding="utf-8")
    c.log(f"calibration o={o:.3f} kappa={kappa}")


def phase_t0(c):
    reqs = [(s, T) for T in (100, 1000) for s in SEL.SCEN] + [("A2_bound", 3000)]
    for s, T in reqs:
        L = SEL.line(s, T) + 8
        evs = [SEL.E1, SEL.E2] + ([SEL.E0] if (s, T) in (("A2_bound", 100), ("A3_high", 100)) else [])
        for ev in evs:
            for cpu in (2, 8):
                spec = {"evaluator": ev, "scenario": s, "T": T, "mode": "single", "start_p": L}
                c.rec(f"T0__{ev.replace(':', '-').replace('+', '_')}__{s}_{T}__cpu{cpu}",
                      lambda: O.run_workers(c.w, f"T0_{ev}_{s}_{T}_{cpu}".replace(":", "-").replace("+", "_"), [spec],
                                            h0_env([cpu]), s, T))
    gdir = c.out / "T0_e2_gates"
    gdir.mkdir(exist_ok=True)
    for args, fn in ((["refs", str(gdir / "refs.json")], "refs.json"),
                     (["verify", "rw:R1+R2", str(gdir / "refs.json"), str(gdir / "verify.json")], "verify.json"),
                     (["sympy", "rw:R1+R2", str(gdir / "sympy.json")], "sympy.json")):
        if not (gdir / fn).exists():
            r = subprocess.run([sys.executable, "-m", "experiments.rewrite_pilot_a3.runner", *args], cwd=ROOT,
                               capture_output=True, text=True)
            if r.returncode != 0:
                c.log(f"ERROR T0 gate {fn}: {r.stderr[-400:]}")
    v = json.loads((gdir / "verify.json").read_text(encoding="utf-8"))
    sy = json.loads((gdir / "sympy.json").read_text(encoding="utf-8"))
    c.log(f"T0 E2 gates S1-S6 {v['PASS_S1_S6_except_S3b']} sympy {sy['sympy_zero']}")
    for rep in range(3):
        for pair in ((2, 3), (2, 4)):
            def smt():
                t0 = time.perf_counter()
                ws = [O.Worker(c.w, f"smt_{pair}_{rep}_{i}", {"cpus": [cpu], "mode": "smt_burn", "n": 12_000_000})
                      for i, cpu in enumerate(pair)]
                for w in ws:
                    w.proc.wait()
                rows = [O._read_all(w) and w.lines for w in ws]
                return {"pair": list(pair), "burn_wall_s": [next(x["wall_s"] for x in r if x["kind"] == "burn")
                                                            for r in rows],
                        "affinity_readback": [r[0]["affinity_readback"] for r in rows],
                        "wall_s": time.perf_counter() - t0,
                        "total_cpu_s": sum(next(x["child_cpu_s"] for x in r if x["kind"] == "end") for r in rows)}
            c.rec(f"T0__smt_{pair[0]}_{pair[1]}__r{rep}", smt)


def phase_t1(c):
    us = c.u()
    ks = [1, 2, 3, 4, 6]
    for rep in range(3):
        order = ks[rep:] + ks[:rep] if rep % 2 == 0 else (ks[rep:] + ks[:rep])[::-1]
        for k in order:
            for plan in (["BASE", "BASE_E2"] if rep % 2 == 0 else ["BASE_E2", "BASE"]):
                c.rec(f"T1__{plan}__k{k}__r{rep}", lambda: O.run_batch(c.w, f"T1_{plan}_{k}_{rep}", plan, SEL.EVAL, k,
                                                                       us=us))
        for cores in ([2], SEL.PHYS_ORDER):
            def single():
                spec = dict(O.specs_for("BASE", "A3_high", 1000)[0])
                d = O.run_workers(c.w, f"T1single_{len(cores)}_{rep}", [spec], h0_env([2]), "A3_high", 1000)
                return d
            if len(cores) == 1:
                c.rec(f"T1__single_A3_high_1000__c1__r{rep}", single)
            else:
                def single6():
                    spec = dict(O.specs_for("BASE", "A3_high", 1000)[0])
                    w = O.Worker(c.w, f"T1single6_{rep}", dict(spec, cpus=list(SEL.PHYS_ORDER)))
                    t0 = time.perf_counter()
                    w.proc.wait()
                    O._read_all(w)
                    return {"wall_s": time.perf_counter() - t0, "total_cpu_s": w.cpu_final(), "passes": w.passes(),
                            "start": w.lines[0], "end": w.end(), "parent_pinned": w.parent_pinned,
                            "status": "VERIFIED" if VF.verify(w.passes()[-1], "A3_high", 1000)["verified"] else "NOT"}
                c.rec(f"T1__single_A3_high_1000__c6__r{rep}", single6)


def phase_t2(c):
    for rep in range(3):
        for i, (s, T) in enumerate(SEL.EVAL):
            plans = [("BASE", [2]), ("SPEC_P_E1", [2, 4, 6]), ("SPEC_EVAL", [2, 4])]
            if (i + rep) % 2:
                plans = plans[::-1]
            for plan, cores in plans:
                c.rec(f"T2__{plan}__{s}_{T}__r{rep}",
                      lambda: O.run_plan(c.w, f"T2_{plan}_{s}_{T}_{rep}", plan, h0_env(cores), s, T))
        for s in ("A3_low", "A3_high"):
            for T in (100, 1000):
                def s4():
                    f = c.w / f"S4_{s}_{T}_{rep}.json"
                    t0 = time.perf_counter()
                    subprocess.run([sys.executable, "-m", f"{PKG}.pairloop", s, str(T), "128", "3", "2,4,6,8", str(f)],
                                   cwd=ROOT, check=True)
                    d = json.loads(f.read_text(encoding="utf-8"))
                    d["wall_s"] = time.perf_counter() - t0
                    d["total_cpu_s"] = d["serial"]["cpu_s"] + d["parallel"]["main_cpu_s"] + sum(d["parallel"]["worker_cpu_s"])
                    d["status"] = "BIT_IDENTICAL" if d["bit_identical"] else "MISMATCH"
                    return d
                c.rec(f"T2__S4__{s}_{T}__r{rep}", s4)
        for mode in (["inline", "after", "pipeline"] if rep % 2 == 0 else ["pipeline", "after", "inline"]):
            c.rec(f"T2__S5_{mode}__r{rep}", lambda: O.run_batch(c.w, f"T2_S5_{mode}_{rep}", "BASE", SEL.EVAL, 5,
                                                                verify_mode=mode, us=c.u()))


def phase_t34(c):
    us = c.u()
    sels = ["FIXED_BASE", "FIXED_AGG3", "ADAPTIVE"]
    for tier in SEL.TIERS:
        for i, (s, T) in enumerate(SEL.EVAL):
            env = SEL.env_for(tier, us[f"{s}@{T}"])
            order = sels[i % 3:] + sels[:i % 3]
            for sel in order:
                def run():
                    vis = SEL.visible(env)
                    plan = {"FIXED_BASE": "BASE", "FIXED_AGG3": "AGG3"}.get(sel) or SEL.adaptive(vis)
                    d = O.run_plan(c.w, f"T34_{tier}_{sel}_{s}_{T}", plan, env, s, T)
                    d.update(selector=sel, selector_input={"visible_env": vis} if sel == "ADAPTIVE" else {})
                    return d
                c.rec(f"T34__{tier}__{sel}__{s}_{T}", run)


def phase_t567(c):
    us = c.u()
    rw = SEL.RW()
    n = 0
    for phase in ("T5", "T6", "T7A", "T7B"):
        for t, (cues, pressure) in enumerate(SEL.schedule(phase)):
            s, T = SEL.COND[n % len(SEL.COND)]
            n += 1
            u = us[f"{s}@{T}"]
            shown = SEL.env_for("H0", u)
            hidden = dict(shown, cpu_s=1.5 * u, wall_s=1.5 * u + 5.0, tier="P") if pressure else shown
            vis = SEL.visible(shown)
            plan, inputs = rw.choose(vis, cues)
            f = c.out / f"{phase}__{t:02d}__COND.json"
            if f.exists():
                d = json.loads(f.read_text(encoding="utf-8"))
                if d["plan"] != plan:
                    raise SystemExit(f"resume mismatch at {f.name}")
            else:
                def run():
                    d = O.run_plan(c.w, f"{phase}_{t}_COND", plan, hidden, s, T)
                    d.update(selector="CONDITIONED", selector_input=inputs, cues=cues, hidden_pressure=pressure,
                             V_before=dict(rw.V), trial_index=n - 1)
                    return d
                d = c.rec(f"{phase}__{t:02d}__COND", run)
            rw.update(cues, pressure)
            c.rec(f"{phase}__{t:02d}__NOLEARN", lambda: dict(O.run_plan(c.w, f"{phase}_{t}_NOLEARN", "AGG3", hidden, s, T),
                                                           selector="NO_LEARN", cues=cues, hidden_pressure=pressure))
        c.log(f"{phase} done V={rw.V}")


def phase_t8(c):
    plans = ["BASE", "CONS", "AGG1", "AGG3"]
    for rep in range(3):
        for i, (s, T) in enumerate(SEL.EVAL):
            k = (i + rep) % 4
            for plan in plans[k:] + plans[:k]:
                c.rec(f"T8__{plan}__{s}_{T}__r{rep}",
                      lambda: O.run_plan(c.w, f"T8_{plan}_{s}_{T}_{rep}", plan, h0_env(), s, T))


def phase_t9(c):
    for s, T in SEL.EVAL:
        def fl():
            f = c.w / f"float_{s}_{T}.json"
            t0 = time.perf_counter()
            subprocess.run([sys.executable, "-m", f"{PKG}.floatcand", s, str(T), "2", str(f)], cwd=ROOT, check=True)
            d = json.loads(f.read_text(encoding="utf-8"))
            d["wall_s"] = time.perf_counter() - t0
            d["total_cpu_s"] = d["cpu_s"]
            return d
        cand = c.rec(f"T9__float__{s}_{T}", fl)
        ver = c.rec(f"T9__verifier_BASE__{s}_{T}", lambda: O.run_plan(c.w, f"T9_ver_{s}_{T}", "BASE", h0_env([2]), s, T))
        c.rec(f"T9__typeA_E2__{s}_{T}", lambda: O.run_plan(c.w, f"T9_E2_{s}_{T}", "BASE_E2", h0_env([2]), s, T))

        def decide():
            vc = ver["result"]["cells"] if ver["status"] == "VERIFIED" else None
            wrong = list(cand["cells"])
            wrong[0] += 1
            return {"candidate_cells_equal_verified": cand["cells"] == vc, "accepted_result_source": "verified interval run",
                    "injected_wrong_accepted": wrong == vc, "verified_cells_present": vc is not None,
                    "total_cpu_s": 0.0, "wall_s": 0.0}
        c.rec(f"T9__decision__{s}_{T}", decide)


def phase_t10(c):
    us = c.u()
    for rep in range(2):
        for tier in ("H1", "H2", "H3"):
            for i, (s, T) in enumerate(SEL.EVAL):
                env = SEL.env_for(tier, us[f"{s}@{T}"])
                for plan in (["AGG3", "CONS"] if (i + rep) % 2 == 0 else ["CONS", "AGG3"]):
                    c.rec(f"T10__{tier}__{plan}__{s}_{T}__r{rep}",
                          lambda: O.run_plan(c.w, f"T10_{tier}_{plan}_{s}_{T}_{rep}", plan, env, s, T))


PHASES = {"CAL": phase_cal, "T0": phase_t0, "T1": phase_t1, "T2": phase_t2, "T34": phase_t34, "T567": phase_t567,
          "T8": phase_t8, "T9": phase_t9, "T10": phase_t10}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", required=True)
    a = ap.parse_args(argv)
    O.pin_self()
    c = Camp(a.out)
    if c.seal()["sealed_sources_dirty"]:
        c.log("sealed sources dirty: STOP")
        return
    names = list(PHASES) if a.phase == "all" else a.phase.split(",")
    for n in names:
        if n != "CAL" and not (c.out / "calibration.json").exists():
            phase_cal(c)
        c.log(f"phase {n} start")
        c.load_snapshot()
        PHASES[n](c)
        c.log(f"phase {n} finished; campaign CPU {c.spent():.0f}s")


if __name__ == "__main__":
    main()
