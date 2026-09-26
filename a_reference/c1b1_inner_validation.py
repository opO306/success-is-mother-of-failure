"""C1-B1 inner-region numerical validation (designer 18th ed., option C): R < 20 bohr is NUMERICALLY VALIDATED, not certified.

Scattering events are started at R = 20 bohr inbound and followed until they are back at 20 bohr outbound (the inner
region). Low energies on a log grid (1e-2 ... 1e-13 De), several impact parameters, head-on (deepest into the repulsive
wall) and near-orbiting cases where the orbiting impact parameter lies inside the studied range.
Two errors are measured separately:
  quantization   = candidate (position FX(96,48), momentum FX(96,80), drift v2) - high precision (exact positions,
                   momentum FX(256,192)), same dt = 40
  discretization = high precision at dt = 40 (and 20) - the independent audit reference (continuous dynamics, quadrature)
Initial states are put on the FX(96,80) momentum grid: on the FX(64,32) grid of study 1 the representation error of the
kinetic energy (~1e-15 hartree at 20 bohr) exceeds the relative energy itself below ~1e-11 De.

Run: python -m a_reference.c1b1_inner_validation          (needs D:\\reference for the audit)
Writes fixtures/c1b1_inner_validation_v1.json; progress in runs/c1b1_inner_validation.log, partial results in
runs/c1b1_inner_validation_partial.jsonl (resumable, one job per worker, longest first).
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

import a_reference.c1b1_dt_study as S
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_inner_validation_v1.json"
PARTIAL = ROOT / "runs" / "c1b1_inner_validation_partial.jsonl"
POS, MOM, HPM = FixedPoint(96, 48), FixedPoint(96, 80), FixedPoint(256, 192)
PROFILES = {"cand": (POS, MOM, "v2"), "hp": (C.ExactPosition(), HPM, "v2")}
E_FRACS = [Q(1, 10 ** k) for k in range(2, 14)]            # 1e-2 ... 1e-13 De
B_FRACS = [Q(0), Q(1, 4), Q(1, 2), Q(1), Q(3, 2), Q(2)]      # x R_e (grid value), up to b_max(study) = 2 R_e
R_START = Q(20)
MU = C.AR40_MASS_ME / 2
CODE_FILES = ("a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py", "a_reference/c1b1_inner_validation.py",
              "audit/independent_physics/c1b1_two_atom.py")


def _register():
    for k, v in PROFILES.items():
        S.PROFILES[k] = v


def mp(x: Q):
    return mpmath.mpf(x.numerator) / x.denominator


def barrier_energy(R: Q, M: int = 320):
    """(E, V'(R)) at a centrifugal-barrier top R*: dV_eff/dR = 0 gives L^2 = mu R^3 V'(R), V_eff(R*) = V + R V'/2 = E
    (diagnostic enclosure midpoints at 2^-M)."""
    V, dV = C.potential_high(R * R, M), -C.force_high(R * R, M)
    return V + R * dV / 2, dV


def orbiting(e: Q):
    """(b_orb, R*) in bohr at which E = e De sits exactly on a barrier top (orbiting), or None when E is above every
    barrier top (E_max ~ 0.9964 De for this potential). Outer branch of E(R*) (falling to 0 as R* grows); bisection on
    exact rationals, b = L / p."""
    E = e * S.DE_GRID
    grid = [S.RE_GRID * Q(101, 100) ** i for i in range(1, 900)]
    vals = [barrier_energy(R)[0] for R in grid]
    k = max(range(len(grid)), key=lambda i: vals[i])
    if vals[k] < E:
        return None
    lo, hi = grid[k], grid[-1]
    if not barrier_energy(hi)[0] < E:
        raise ValueError("energy below the grid's outer end")
    for _ in range(200):
        mid = (lo + hi) / 2
        if barrier_energy(mid)[0] > E:
            lo = mid
        else:
            hi = mid
    R = (lo + hi) / 2
    L2 = MU * R ** 3 * barrier_energy(R)[1]
    with mpmath.workdps(60):
        b = mpmath.sqrt(mp(L2) / mp(2 * MU * E))
    with mpmath.workdps(40):     # the rational is b rounded to 40 digits, EXPLICITLY: it used to be rounded at the
        bq = S.mq(b)             # caller's global precision (40 in every recorded study; 60 after a state() call),
    return bq, R                 # a global-state dependence found by the D_valid fixture load check (2026-09-27)


def orbiting_b(e: Q, b_cap: Q | None = None):
    """b_orb (bohr) if orbiting exists at e De and b_orb <= b_cap (default b_max = 2 R_e), else None.
    (Fixed twice, 2026-09-26: the first grid version started inside the repulsive wall and always returned 0 -- the v1
    record holds the b = 0 case three times per energy and no near-orbiting case; the second grid version took the
    grid's edge at R_e for a barrier top and invented orbiting above E_max. Now the barrier-top conditions are solved.)"""
    r = orbiting(e)
    cap = b_cap if b_cap is not None else 2 * S.RE_GRID
    return r[0] if r is not None and r[0] <= cap else None


def state(e: Q, b: Q):
    """Relative position (20, 0, 0) inbound, E = e De, L = b sqrt(2 mu E), momenta on the FX(96,80) grid."""
    mpmath.mp.dps = 60
    E = e * S.DE_GRID
    p_inf = mpmath.sqrt(2 * mp(MU) * mp(E))
    L = mp(b) * p_inf
    V0 = mp(C.potential_high(R_START ** 2, 512))
    Pt = L / mp(R_START)
    Pr = -mpmath.sqrt(2 * mp(MU) * (mp(E) - V0) - Pt * Pt)
    g = lambda x: MOM.to_exact(MOM.from_exact(S.mq(x)))
    P = (g(Pr), g(Pt), Q(0))
    ri, rj = (-R_START / 2, Q(0), Q(0)), (R_START / 2, Q(0), Q(0))
    run = C.new_run(POS, 40, ri, tuple(-x for x in P), rj, P, momentum_profile=MOM, validated_only=False)
    lo, hi = C.relative_energy_enclosure(run, 512)
    assert lo > 0, "represented state is not a scattering state"
    E_rep = (lo + hi) / 2
    return {"E_nom": E, "L_nom": mpmath.nstr(L, 40), "E_rep": E_rep, "E_rep_width": hi - lo, "L_rep": R_START * P[1],
            "r_i": ri, "p_i": tuple(-x for x in P), "r_j": rj, "p_j": P}


def cases():
    out = []
    for e in E_FRACS:
        bs = [bf * S.RE_GRID for bf in B_FRACS]
        bo = orbiting_b(e)
        if bo is not None:
            bq = S.mq(bo)
            bs += [bq * Q(999999, 1000000), bq * Q(1000001, 1000000)]
        for b in bs:
            if b <= 2 * S.RE_GRID:
                out.append({"kind": "scatter", "e": e, "b_bohr": b, "name": f"inner E/De={e} b={float(b):.6f}",
                            "near_orbiting": bo is not None and b not in [bf * S.RE_GRID for bf in B_FRACS]})
    return out


def reference_task(args):
    case, st = args
    mpmath.mp.dps = 40
    from audit.independent_physics.c1b1_two_atom import Reference
    ref = Reference(dps=40)
    try:
        a, t, r0 = ref.sweep_and_time(ref._mp(st["E_rep"]), ref._mp(st["L_rep"]), R_START)
        return {"case": case["name"], "sweep": mpmath.nstr(a, 30), "time": mpmath.nstr(t, 30), "r0": mpmath.nstr(r0, 15)}
    except (ValueError, ArithmeticError) as exc:
        return {"case": case["name"], "error": str(exc)}


def run_task(args):
    case, st, dt, pname, cap = args
    _register()
    return S.run_case((case, st, dt, pname, cap))


def _run(item):
    key, task, args = item
    _register()
    return key, task.__name__, task(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    code = {f: _sha(ROOT / f) for f in CODE_FILES}
    cs = cases()
    sts = [state(c["e"], c["b_bohr"]) for c in cs]
    print(f"{len(cs)} cases ({sum(c['near_orbiting'] for c in cs)} near orbiting), states built {time.time() - t0:.0f}s",
          flush=True)
    done = {}
    if PARTIAL.exists():
        lines = PARTIAL.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[0]) == {"git_head": head, "code": code}:
            for l in lines[1:]:
                r = json.loads(l)
                done[r["key"]] = r
        else:
            PARTIAL.unlink()
    if not PARTIAL.exists():
        PARTIAL.parent.mkdir(parents=True, exist_ok=True)
        PARTIAL.write_text(json.dumps({"git_head": head, "code": code}) + "\n", encoding="utf-8")
    refs = {}
    with Pool(procs) as pool, PARTIAL.open("a", encoding="utf-8") as f:
        todo = [(f"ref|{c['name']}", reference_task, (c, st)) for c, st in zip(cs, sts) if f"ref|{c['name']}" not in done]
        for key, name, res in pool.imap_unordered(_run, todo, chunksize=1):
            f.write(json.dumps({"key": key, "task": name, "result": res}) + "\n")
            f.flush()
            done[key] = {"key": key, "task": name, "result": res}
        print(f"references done {time.time() - t0:.0f}s", flush=True)
        jobs = []
        for c, st in zip(cs, sts):
            r = done[f"ref|{c['name']}"]["result"]
            t_ref = float(r.get("time", 4e6))
            for dt, pname in ((40, "cand"), (40, "hp"), (20, "hp")):
                cap = int(3 * t_ref / dt) + 400
                jobs.append((cap * (2.5 if pname == "hp" else 1), (f"run|{c['name']}|{dt}|{pname}", run_task,
                                                                   (c, st, dt, pname, cap))))
        todo = [j for _, j in sorted(jobs, key=lambda x: -x[0]) if j[0] not in done]
        print(f"{len(todo)} runs to do", flush=True)
        for i, (key, name, res) in enumerate(pool.imap_unordered(_run, todo, chunksize=1)):
            f.write(json.dumps({"key": key, "task": name, "result": res}) + "\n")
            f.flush()
            done[key] = {"key": key, "task": name, "result": res}
            if i % 20 == 0:
                print(f"  {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
    doc = {"format": "c1b1-inner-validation-v1", "status": "NUMERICALLY VALIDATED evidence (not certified)",
           "contract": C.CONTRACT_VERSION, "position": POS.name, "momentum": MOM.name, "hp": "exact positions + FX(256,192)",
           "R_start": str(R_START), "e_fracs": [str(e) for e in E_FRACS], "b_fracs_Re": [str(b) for b in B_FRACS],
           "cases": [{"name": c["name"], "e": str(c["e"]), "b_bohr": str(c["b_bohr"]), "near_orbiting": c["near_orbiting"],
                      "E_rep": str(st["E_rep"]), "E_rep_width": str(st["E_rep_width"]), "L_rep": str(st["L_rep"]),
                      "p_j": [str(x) for x in st["p_j"]]} for c, st in zip(cs, sts)],
           "references": [done[f"ref|{c['name']}"]["result"] for c in cs],
           "runs": [done[k]["result"] for k in sorted(k for k in done if k.startswith("run|"))],
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty), "code_sha256": code},
           "seconds_this_session": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
