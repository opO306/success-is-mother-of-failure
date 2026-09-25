"""C1-B1 study 2 (designer 12th ed., steps 1-3 + item 7): reference convergence, domain-guard stress,
wider fixed-point candidates, sensitivity benchmark. Measurements only -- nothing here chooses a profile.

A. references: every case of study 1 (c1b1_dt_study) recomputed by the corrected audit (analytic endpoint
   limits) at 30, 50 and 80 digits -- represented and nominal initial states.
B. domain-guard stress (not an accuracy claim): head-on, E = f * V(r_min), f = 0.25, 0.75, 0.99, 1.01, dt from 40
   down to 1.25, FX(256,192). The continuous path turns above r_min for f < 1 and needs R < r_min for f = 1.01.
C. wider fixed point: FX(64,40), FX(64,48), FX(96,64), FX(128,96) on all 40 cases at dt = 10, 20, 40, from the
   same initial states; the rounding error is measured against study 1's FX(256,192) runs.
D. sensitivity: E = De and 0.5 De at b = 1.5 Re, with b shifted by delta_b = -1e-3, +1e-3 Re (and the base case);
   each run against ITS OWN reference; local sensitivity d(sweep)/db and d(chi)/db recorded.

Run: python -m a_reference.c1b1_numrep_study   (needs D:\\reference)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from fractions import Fraction as Q
from multiprocessing import Pool
from pathlib import Path

import mpmath

import a_reference.c1b1_dt_study as S
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_numrep_study_v1.json"
DIGITS = [30, 50, 80]
CANDIDATES = {"FX64_40": (64, 40), "FX64_48": (64, 48), "FX96_64": (96, 64), "FX128_96": (128, 96)}
CAND_DTS = [10, 20, 40]
STRESS_F = [Q(1, 4), Q(3, 4), Q(99, 100), Q(101, 100)]
STRESS_DTS = [40, 20, 10, 5, Q(5, 2), Q(5, 4)]
SENS = [(Q(1), Q(3, 2)), (Q(1, 2), Q(3, 2))]
SENS_DB = [Q(-1, 1000), Q(0), Q(1, 1000)]
SENS_DTS = [10, 20, 40]


def _ref_values(ref, kind, st, name_e, name_l=None):
    if kind == "bound":
        T, rm, rp = ref.radial_period(ref._mp(st[name_e]), ref._mp(S.RE_GRID))
        return {"two_periods": mpmath.nstr(2 * T, 45)}
    Lx = st[name_l]
    a, t, r0 = ref.sweep_and_time(ref._mp(st[name_e]), ref._mp(Lx) if isinstance(Lx, Q) else mpmath.mpf(Lx),
                                  S.R_START)
    return {"sweep": mpmath.nstr(a, 45), "time": mpmath.nstr(t, 45)}


def task(args):
    kind = args[0]
    from audit.independent_physics.c1b1_two_atom import Reference
    if kind == "ref":
        _, case, st, dps = args
        mpmath.mp.dps = dps
        ref = Reference(dps=dps)
        out = {"task": "ref", "case": case["name"], "dps": dps}
        out["represented"] = _ref_values(ref, case["kind"], st, "E_rep", "L_rep")
        out["nominal"] = _ref_values(ref, case["kind"], st, "E_nom", "L_nom")
        return out
    if kind == "cand":
        _, case, st, dt, pname, cap = args
        W, F = CANDIDATES[pname]
        S.PROFILES[pname] = FixedPoint(W, F)
        r = S.run_case((case, st, dt, pname, cap))
        r["task"] = "cand"
        return r
    if kind == "stress":
        _, f, dt = args
        return {"task": "stress", **stress_run(f, dt)}
    if kind == "sens":
        _, e, b, db, dt = args
        return {"task": "sens", **sens_run(e, b, db, dt)}
    if kind == "sens_ref":
        _, e, b, db = args
        mpmath.mp.dps = 50
        ref = Reference(dps=50)
        st = S.scattering_state(e, b + db)
        vals = _ref_values(ref, "scatter", st, "E_rep", "L_rep")
        E_m = ref._mp(st["E_nom"])
        chi = ref.deflection(E_m, ref._mp((b + db) * S.RE_GRID) * mpmath.sqrt(2 * ref._mp(S.MU) * E_m))
        return {"task": "sens_ref", "e": str(e), "b": str(b), "db": str(db), "represented": vals,
                "chi_infinity_nominal": mpmath.nstr(chi, 40)}
    raise ValueError(kind)


# --- B: domain-guard stress ---------------------------------------------------------------------------------

V_RMIN = C.potential_high(C.R_MIN2)


def stress_run(f: Q, dt):
    """Head-on from 20 bohr with total energy f * V(r_min); FX(256,192)."""
    prof = FixedPoint(256, 192)
    E = f * V_RMIN
    V0 = C.potential_high(S.R_START ** 2)
    P = -mpmath.sqrt(2 * S.mp(S.MU) * S.mp(E - V0))
    Px = S.g(S.mq(P))
    ri, rj = (-S.R_START / 2, Q(0), Q(0)), (S.R_START / 2, Q(0), Q(0))
    run = C.new_run(prof, dt, ri, (-Px, Q(0), Q(0)), rj, (Px, Q(0), Q(0)), validated_only=False)  # stress only
    lo, hi = C.relative_energy_enclosure(run, 256)    # the reference's K_rel + V (not an ad hoc formula)
    E_rep = (lo + hi) / 2
    min_R2 = seg_min = Q(10 ** 6)
    status = "ok"
    try:
        for _ in range(int(40 * 20000 / Q(dt)) + 100):
            q_old = C.relative(prof, *run.atoms)
            C.step(run)
            q = C.relative(prof, *run.atoms)
            R2 = sum((x * x for x in q), Q(0))
            min_R2 = min(min_R2, R2)
            seg_min = min(seg_min, C.segment_min_R2(q_old, tuple(b - a for a, b in zip(q_old, q))))
            if R2 >= S.R_START ** 2 and q[0] > q_old[0]:
                break
    except C.PhysicsDomainExceeded as e:
        status = f"physics_domain_exceeded: {e}"
    # continuous turning point for the represented energy (L = 0): V(r_t) = E_rep, by bisection on the reference
    lo, hi = C.R_MIN2 / 4, Q(36)                      # R^2 bracket
    turning = None
    if E_rep < V_RMIN:
        lo = C.R_MIN2
        for _ in range(100):
            mid = (lo + hi) / 2
            if C.potential_high(mid, 200) > E_rep:
                lo = mid
            else:
                hi = mid
        turning = float(lo) ** 0.5
    return {"f": str(f), "dt": str(dt), "status": status, "steps": run.t_steps,
            "E_rep_over_V_rmin": float(E_rep / V_RMIN), "min_R_step_endpoints": float(min_R2) ** 0.5,
            "min_R_drift_segments": float(seg_min) ** 0.5,
            "continuous_turning_R": turning, "r_min": float(C.R_MIN2) ** 0.5}


# --- D: sensitivity -----------------------------------------------------------------------------------------

def sens_run(e, b, db, dt):
    st = S.scattering_state(e, b + db)
    case = {"kind": "scatter", "e": e, "b": b + db, "name": f"sens E/De={e} b/Re={b}{'+' if db >= 0 else ''}{db}"}
    r = S.run_case((case, st, dt, "HP", int(3 * 400000 / dt) + 200))
    r.update({"e": str(e), "b": str(b), "db": str(db)})
    return r


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    cs = S.cases()
    states = [S.scattering_state(c["e"], c["b"]) if c["kind"] == "scatter" else S.bound_state(c["f"]) for c in cs]
    old = json.loads(S.OUT.read_text(encoding="utf-8"))
    old_refs = {r["case"]: r for r in old["references"]}
    tasks = []
    for c, st in zip(cs, states):
        for dps in DIGITS:
            tasks.append(("ref", c, st, dps))
        nom = old_refs[c["name"]].get("nominal", {})
        t_ref = float(nom.get("time", nom.get("two_periods", 4e5)))
        for dt in CAND_DTS:
            for pname in CANDIDATES:
                tasks.append(("cand", c, st, dt, pname, int(3 * t_ref / dt) + 200))
    for f in STRESS_F:
        for dt in STRESS_DTS:
            tasks.append(("stress", f, dt))
    for e, b in SENS:
        for db in SENS_DB:
            tasks.append(("sens_ref", e, b, db))
            for dt in SENS_DTS:
                tasks.append(("sens", e, b, db, dt))
    weight = {"ref": 3, "cand": 1, "stress": 1, "sens": 2, "sens_ref": 3}
    tasks.sort(key=lambda t: -weight[t[0]] * (t[3] if t[0] == "ref" else 1) / (t[3] if t[0] == "cand" else 1))
    print(f"{len(tasks)} tasks", flush=True)
    results = []
    t0 = time.time()
    with Pool(procs) as pool:
        for i, r in enumerate(pool.imap_unordered(task, tasks)):
            results.append(r)
            if i % 50 == 0:
                print(f"  {i}/{len(tasks)} ({time.time() - t0:.0f}s)", flush=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    doc = {"format": "c1b1-numrep-study-v1", "contract": C.CONTRACT_VERSION, "digits": DIGITS,
           "candidates": {k: f"FX({w},{f})" for k, (w, f) in CANDIDATES.items()}, "candidate_dts": CAND_DTS,
           "stress": {"f": [str(x) for x in STRESS_F], "dts": [str(x) for x in STRESS_DTS],
                      "V_rmin": str(float(V_RMIN))},
           "sensitivity": {"cases": [[str(e), str(b)] for e, b in SENS], "db": [str(x) for x in SENS_DB],
                           "dts": SENS_DTS},
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty),
                          "study1": str(S.OUT.name),
                          "code_sha256": {f: _sha(ROOT / f) for f in (
                              "a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py",
                              "a_reference/c1b1_numrep_study.py", "audit/independent_physics/c1b1_two_atom.py")}},
           "results": sorted(results, key=lambda r: json.dumps({k: r.get(k) for k in ("task", "case", "dps", "dt",
                                                                                   "profile", "f", "e", "db")},
                                                              default=str))}
    OUT.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
