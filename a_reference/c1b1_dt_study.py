"""C1-B1 step 3: measure the Delta t candidates 10, 20, 40, 80, 160 a.u. (designer 11th ed., D7, D9, D10).

For every case the three error sources are kept apart (D10):
  1. representation  = reference(represented initial state) - reference(nominal initial state)
  2. rounding        = run(profile, dt) - run(FX(256,192), dt)         -- same initial state, same dt
  3. discretisation  = run(FX(256,192), dt) - reference(represented initial state)
All profiles start from ONE represented initial state: the nominal state rounded to the FX(64,32) grid, whose
values are also exact binary64 values. The references come from the independent audit
(audit/independent_physics/c1b1_two_atom.py: quadrature of the audit's own Lang model), with the same finite
start radius (20 bohr) and, for scattering, also from infinity (tail effect).

Observables. Scattering: the polar angle swept by the relative coordinate from the start until it is back at
the start radius, and the time that takes; the crossing inside the last step is located by cubic Hermite
interpolation in (position, velocity) -- error O(dt^4), far below the integrator's O(dt^2). Bound (L = 0):
the time of two full radial periods, from the inner turning point (P = 0) to the second return of P from
negative to positive, located by Hermite interpolation of P with dP/dt = F.
Also: max |E - E0| (sampled every 25 steps, diagnostic V to 256 bits), final angular momentum and total
momentum changes (exact).

Run: python -m a_reference.c1b1_dt_study   (needs D:\\reference for the audit's Fortran parameters)
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import time
from fractions import Fraction as Q
from multiprocessing import Pool
from pathlib import Path

import mpmath

import a_reference.c1b1_two_atom as C
from a_numeric import Binary64Finite, FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_dt_study_v1.json"
DTS = [10, 20, 40, 80, 160]
PROFILES = {"B64": Binary64Finite(), "FX64_32": FixedPoint(64, 32), "HP": FixedPoint(256, 192)}
GRID = FixedPoint(64, 32)                      # the common initial-state grid
R_START = Q(20)
# grid scales only (exploration grid, designer 11th ed. D9): the model's well depth and position, rounded
DE_GRID = Q("0.000451995775")
RE_GRID = Q("7.1129")
E_FRACS = [Q(1, 2), Q(1), Q(2), Q(5), Q(10)]
B_FRACS = [Q(0), Q(1, 4), Q(1, 2), Q(3, 4), Q(1), Q(3, 2), Q(2)]
BOUND_F = [Q(1, 50), Q(1, 10), Q(3, 10), Q(6, 10), Q(9, 10)]
MU = C.AR40_MASS_ME / 2
mpmath.mp.dps = 40


def mp(x: Q):
    return mpmath.mpf(x.numerator) / x.denominator


def g(x: Q) -> Q:
    return GRID.to_exact(GRID.from_exact(x))


def mq(x) -> Q:
    """An mpf as an exact rational (its binary value)."""
    man, exp = mpmath.mpf(x).man_exp
    v = Q(abs(man)) * Q(2) ** exp
    return -v if x < 0 else v


# --- initial states ----------------------------------------------------------------------------------------

def scattering_state(e: Q, b: Q):
    """Nominal E = e De, L = b Re sqrt(2 mu E) at relative position (20, 0, 0); returns nominal and represented."""
    E = e * DE_GRID
    p_inf = mpmath.sqrt(2 * mp(MU) * mp(E))
    L = mp(b * RE_GRID) * p_inf
    V0 = mp(C.potential_high(R_START ** 2))
    Pt = L / mp(R_START)
    Pr = -mpmath.sqrt(2 * mp(MU) * (mp(E) - V0) - Pt * Pt)
    P = (g(mq(Pr)), g(mq(Pt)), Q(0))
    ri, rj = (-R_START / 2, Q(0), Q(0)), (R_START / 2, Q(0), Q(0))
    E_rep = (P[0] ** 2 + P[1] ** 2) / (2 * MU) + C.potential_high(R_START ** 2)
    L_rep = R_START * P[1]
    return {"E_nom": E, "L_nom": mpmath.nstr(L, 40), "E_rep": E_rep, "L_rep": L_rep,
            "r_i": ri, "p_i": tuple(-x for x in P), "r_j": rj, "p_j": P}


def bound_state(f: Q):
    """L = 0, E = V_min + f De, starting at rest at the inner turning point."""
    E = -DE_GRID + f * DE_GRID
    lo, hi = Q(5), RE_GRID
    for _ in range(90):                        # V(lo) > E > V(hi)
        mid = (lo + hi) / 2
        if C.potential_high(mid * mid, 160) > E:
            lo = mid
        else:
            hi = mid
    r_minus = (lo + hi) / 2
    ri, rj = (g(-r_minus / 2), Q(0), Q(0)), (g(r_minus / 2), Q(0), Q(0))
    R = rj[0] - ri[0]
    return {"E_nom": E, "E_rep": C.potential_high(R * R), "r_minus_nom": float(r_minus), "R_rep": R,
            "L_rep": Q(0), "r_i": ri, "p_i": (Q(0),) * 3, "r_j": rj, "p_j": (Q(0),) * 3}


def cases():
    out = []
    for e in E_FRACS:
        for b in B_FRACS:
            out.append({"kind": "scatter", "e": e, "b": b, "name": f"scatter E/De={e} b/Re={b}"})
    for f in BOUND_F:
        out.append({"kind": "bound", "f": f, "name": f"bound L=0 (E-Vmin)/De={f}"})
    return out


# --- one run ------------------------------------------------------------------------------------------------

def _hermite(q0, q1, v0, v1, h, s):
    s2, s3 = s * s, s * s * s
    h00, h10, h01, h11 = 2 * s3 - 3 * s2 + 1, s3 - 2 * s2 + s, -2 * s3 + 3 * s2, s3 - s2
    return [h00 * a + h10 * h * c + h01 * b + h11 * h * d for a, b, c, d in zip(q0, q1, v0, v1)]


def _rel(run):
    prof = run.profile
    q = C.relative(prof, *run.atoms)
    pi, pj = C.exact(prof, run.atoms[0].p), C.exact(prof, run.atoms[1].p)
    v = tuple((b - a) / C.AR40_MASS_ME for a, b in zip(pi, pj))
    return q, v, pj


def run_case(args):
    case, st, dt, pname, max_steps = args
    mpmath.mp.dps = 40
    prof = PROFILES[pname]
    t0 = time.time()
    # a measurement OF the integrator (it established the validated range), not A-world physics
    run = C.new_run(prof, dt, st["r_i"], st["p_i"], st["r_j"], st["p_j"], validated_only=False)
    q, v, pj = _rel(run)
    E0 = C.kinetic(run) + C.potential_high(sum((x * x for x in q), Q(0)))
    L0, P0 = C.angular_momentum(run), C.total_momentum(run)
    res = {"case": case["name"], "dt": dt, "profile": pname}
    Emax = Q(0)
    R2_start = sum((x * x for x in q), Q(0))
    theta0 = mpmath.atan2(mp(q[1]), mp(q[0]))
    approx_angle, prev_q = 0.0, q
    passed_min, prev_R2 = False, R2_start
    crossings = []
    try:
        for n in range(1, max_steps + 1):
            q_prev, v_prev, pj_prev = q, v, pj
            C.step(run)
            q, v, pj = _rel(run)
            R2 = sum((x * x for x in q), Q(0))
            if n % 25 == 0:
                Emax = max(Emax, abs(C.kinetic(run) + C.potential_high(R2) - E0))
            if case["kind"] == "scatter":
                a0, a1 = math.atan2(float(prev_q[1]), float(prev_q[0])), math.atan2(float(q[1]), float(q[0]))
                d = a1 - a0
                approx_angle += d - 2 * math.pi * round(d / (2 * math.pi))
                prev_q = q
                if R2 > prev_R2:
                    passed_min = True
                prev_R2 = R2
                if passed_min and R2 >= R2_start:
                    q0m, q1m = [mp(x) for x in q_prev], [mp(x) for x in q]
                    v0m, v1m = [mp(x) for x in v_prev], [mp(x) for x in v]
                    lo, hi, Rs = mpmath.mpf(0), mpmath.mpf(1), mp(R2_start)
                    for _ in range(140):
                        mid = (lo + hi) / 2
                        qq = _hermite(q0m, q1m, v0m, v1m, mp(Q(dt)), mid)
                        if qq[0] ** 2 + qq[1] ** 2 + qq[2] ** 2 < Rs:
                            lo = mid
                        else:
                            hi = mid
                    qq = _hermite(q0m, q1m, v0m, v1m, mp(Q(dt)), lo)
                    th = mpmath.atan2(qq[1], qq[0]) - theta0
                    k = round((approx_angle - float(th)) / (2 * math.pi))
                    res["sweep"] = mpmath.nstr(abs(th + 2 * mpmath.pi * k), 30)
                    res["time"] = mpmath.nstr((n - 1 + lo) * dt, 30)
                    break
            else:                                   # bound: P_x of atom j from negative to positive
                if pj_prev[0] < 0 <= pj[0]:
                    F0 = C.force_high(sum((x * x for x in q_prev), Q(0))) * (1 if q_prev[0] > 0 else -1)
                    F1 = C.force_high(R2) * (1 if q[0] > 0 else -1)
                    P0m, P1m = [mp(pj_prev[0])], [mp(pj[0])]
                    lo, hi = mpmath.mpf(0), mpmath.mpf(1)
                    for _ in range(140):
                        mid = (lo + hi) / 2
                        if _hermite(P0m, P1m, [mp(F0)], [mp(F1)], mp(Q(dt)), mid)[0] < 0:
                            lo = mid
                        else:
                            hi = mid
                    crossings.append((n - 1 + lo) * dt)
                    if len(crossings) == 2:
                        res["two_periods"] = mpmath.nstr(crossings[1], 30)
                        break
        else:
            res["status"] = "not_finished_within_cap"
        res.setdefault("status", "ok")
    except C.PhysicsDomainExceeded as e:
        res["status"] = f"physics_domain_exceeded: {e}"
    except C.ReferenceUndecided as e:
        res["status"] = f"reference_undecided: {e}"
    res["steps"] = run.t_steps
    res["max_abs_dE_over_De"] = float(Emax / DE_GRID)
    res["dLz"] = str(C.angular_momentum(run)[2] - L0[2])
    res["dP"] = [str(a - b) for a, b in zip(C.total_momentum(run), P0)]
    res["seconds"] = round(time.time() - t0, 1)
    return res


def reference_for(args):
    """Audit references for one case: nominal, represented, and (scattering) from infinity + sensitivity."""
    case, st = args
    mpmath.mp.dps = 40
    from audit.independent_physics.c1b1_two_atom import Reference
    ref = Reference()
    out = {"case": case["name"]}
    if case["kind"] == "scatter":
        for tag, E, Lx in (("nominal", st["E_nom"], st["L_nom"]), ("represented", st["E_rep"], st["L_rep"])):
            E_m = ref._mp(E)
            L_m = ref._mp(Lx) if isinstance(Lx, Q) else mpmath.mpf(Lx)
            try:
                a, t, r0 = ref.sweep_and_time(E_m, L_m, R_START)
                out[tag] = {"sweep": mpmath.nstr(a, 30), "time": mpmath.nstr(t, 30), "r0": mpmath.nstr(r0, 12)}
            except ValueError as e:
                out[tag] = {"error": str(e)}
        E_m = ref._mp(st["E_nom"])
        p = mpmath.sqrt(2 * ref._mp(MU) * E_m)
        chis = []
        for db in (-Q(1, 50), Q(0), Q(1, 50)):
            bb = case["b"] + db
            if bb < 0:
                chis.append(None)
                continue
            try:
                chis.append(ref.deflection(E_m, ref._mp(bb * RE_GRID) * p))
            except ValueError:
                chis.append(None)
        out["chi_infinity"] = mpmath.nstr(chis[1], 20) if chis[1] is not None else None
        if chis[0] is not None and chis[2] is not None:
            out["dchi_d(b/Re)"] = float((chis[2] - chis[0]) / mpmath.mpf("0.04"))
    else:
        for tag, E in (("nominal", st["E_nom"]), ("represented", st["E_rep"])):
            T, rm, rp = ref.radial_period(ref._mp(E), ref._mp(RE_GRID))
            out[tag] = {"two_periods": mpmath.nstr(2 * mpmath.re(T), 30), "imag": float(mpmath.im(T)),
                        "r_minus": mpmath.nstr(rm, 12), "r_plus": mpmath.nstr(rp, 12)}
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    cs = cases()
    states = [scattering_state(c["e"], c["b"]) if c["kind"] == "scatter" else bound_state(c["f"]) for c in cs]
    print(f"{len(cs)} cases", flush=True)
    with Pool(procs) as pool:
        refs = pool.map(reference_for, list(zip(cs, states)))
        print("references done", flush=True)
        tasks = []
        for c, st, rf in zip(cs, states, refs):
            nom = rf.get("nominal", {})
            t_ref = float(nom.get("time", nom.get("two_periods", 4e5)))
            for dt in DTS:
                cap = int(3 * t_ref / dt) + 200
                for pname in PROFILES:
                    tasks.append((c, st, dt, pname, cap))
        tasks.sort(key=lambda t: -t[4] * (2.5 if t[3] == "HP" else 1))   # longest first
        runs = []
        for i, r in enumerate(pool.imap_unordered(run_case, tasks)):
            runs.append(r)
            if i % 25 == 0:
                print(f"  {i}/{len(tasks)} runs", flush=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    doc = {"format": "c1b1-dt-study-v1", "contract": C.CONTRACT_VERSION, "mass_me": str(C.AR40_MASS_ME),
           "mass_sources": C.MASS_SOURCES, "grid_scales": {"De": str(DE_GRID), "Re": str(RE_GRID)},
           "R_start": str(R_START), "dts": DTS, "profiles": {k: v.name for k, v in PROFILES.items()},
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty),
                          "code_sha256": {f: _sha(ROOT / f) for f in (
                              "a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py",
                              "audit/independent_physics/c1b1_two_atom.py")}},
           "cases": [{"name": c["name"], "kind": c["kind"], "E_rep": str(st["E_rep"]), "L_rep": str(st["L_rep"]),
                      **({"e": str(c["e"]), "b": str(c["b"]), "p_j": [str(x) for x in st["p_j"]]}
                         if c["kind"] == "scatter" else {"f": str(c["f"]), "R_rep": str(st["R_rep"])})}
                     for c, st in zip(cs, states)],
           "references": refs, "runs": sorted(runs, key=lambda r: (r["case"], r["dt"], r["profile"]))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
