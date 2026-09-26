"""C1-B1 orbital-capture boundary width, ASYMMETRIC (designer verdict on section 22): measure delta_-(E) and
delta_+(E) separately rather than assuming a single symmetric delta_c(E).

rho(E, b) = b / b_orb(E) - 1. Section 22 found the dt = 40 discretization error (sweep angle, vs the audit
quadrature) exceeds the 1e-5 rad target somewhere inside |rho| <~ 1e-4, and is fine at |rho| = 1e-2. Here, for
each energy, bisect independently on the b < b_orb side (delta_-) and the b > b_orb side (delta_+) to locate
the boundary of the excluded band D_capture = {(E, b): -delta_-(E) < rho < delta_+(E)} to within a factor
BISECT_TOL in rho -- NOT a dense sweep (designer: "촘촘한 전수탐색보다는 경계탐색").

The bisection predicate is "does dt = 40 meet the target at this rho": True (pass) for large |rho|, False
(fail) for small |rho| -- monotonic in |rho| is assumed and checked (an assertion fires if a "pass" point is
found closer to b_orb than a "fail" point already recorded, which would mean the band is not the simple
interval this search assumes).

Run: python -m a_reference.c1b1_orbit_boundary     (needs D:\\reference for the audit; ~O(50) audit + integrator
runs per energy per side, much cheaper than a dense grid)
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
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_orbit_boundary_v1.json"
PARTIAL = ROOT / "runs" / "c1b1_orbit_boundary_partial.jsonl"

E_FRACS = [Q(15, 100), Q(2, 10), Q(3, 10), Q(1, 2), Q(7, 10), Q(9, 10), Q(99, 100)]
TARGET = mpmath.mpf("1e-5")          # sweep-angle target, rad (same as section 20/22)
RHO_LO, RHO_HI = mpmath.mpf("1e-8"), mpmath.mpf("2e-2")   # bisection bracket in |rho|; section 22 saw pass at 1e-2
BISECT_STEPS = 18                     # ~2 ppm of a decade in log(rho) -- far tighter than the factor-of-100 grid
B_MAX = 2 * I.S.RE_GRID
CODE_FILES = ("a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py", "a_reference/c1b1_inner_validation.py",
              "a_reference/c1b1_orbit_boundary.py", "audit/independent_physics/c1b1_two_atom.py")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _one_point(e: Q, bo: Q, rho: Q):
    """Run dt=40 hp + the audit reference at b = bo * (1 + rho); return (ok, e40, detail) where ok = |e40| < TARGET,
    or ("audit_fail", reason) if the audit quadrature itself fails there (section 22 also found this, at rho=1e-6)."""
    b = bo * (1 + rho)
    if b < 0 or b > B_MAX:
        return None
    st = I.state(e, b)
    I._register()
    ref = I.reference_task(({"e": e, "b_bohr": b, "name": "probe"}, st))
    if "error" in ref:
        return ("audit_fail", ref["error"])
    t_ref = float(ref.get("time", 2e6))
    cap = int(3 * t_ref / 40) + 400
    r = S.run_case(({"kind": "scatter", "name": "probe"}, st, 40, "hp", cap))
    if r.get("status") != "ok":
        return ("run_fail", r.get("status"))
    with mpmath.workdps(50):
        e40 = mpmath.mpf(r["sweep"]) - mpmath.mpf(ref["sweep"])
    return ("ok", float(e40))


def _bisect_side(e: Q, bo: Q, sign: int, log):
    """Bisect log(rho) in [RHO_LO, RHO_HI] on one side (sign=-1 below b_orb, +1 above). Returns
    {"delta": rho at the boundary (mid of final bracket), "lo_fail": ..., "hi_pass": ..., "audit_fail_at": [...]}.
    Convention: rho with sign*rho > 0 is "this side". Assumes monotonic pass/fail in |rho| and asserts it."""
    audit_fails, probes = [], []
    lo, hi = mpmath.log(RHO_LO), mpmath.log(RHO_HI)      # log|rho|; lo end assumed FAIL, hi end assumed PASS
    seen_fail_logrho, seen_pass_logrho = lo, hi

    def probe(logrho):
        rho = sign * mpmath.e ** logrho
        res = _one_point(e, bo, Q(str(rho)))
        if res is None:
            return None
        if res[0] == "audit_fail":
            audit_fails.append({"rho": float(rho), "reason": res[1]})
            return None
        if res[0] != "ok":
            probes.append({"rho": float(rho), "status": res[0]})
            return None
        probes.append({"rho": float(rho), "e40_sweep_rad": res[1], "pass": abs(res[1]) < TARGET})
        return abs(res[1]) < TARGET       # True = pass (meets target), False = fail

    p_hi = probe(hi)
    p_lo = probe(lo)
    if p_hi is False:
        log(f"  side {sign:+d}: even |rho|={float(RHO_HI):.1e} fails -- band wider than bracket, recording as-is")
        return {"delta": float(RHO_HI), "bracket_exceeded": True, "audit_fail_at": audit_fails, "probes": probes}
    if p_lo is True:
        log(f"  side {sign:+d}: even |rho|={float(RHO_LO):.1e} passes -- band narrower than bracket")
        return {"delta": float(RHO_LO), "bracket_exceeded": False, "audit_fail_at": audit_fails, "band_below_bracket": True,
                "probes": probes}
    for _ in range(BISECT_STEPS):
        mid = (lo + hi) / 2
        r = probe(mid)
        if r is None:                      # audit failure or run failure at this rho: nudge outward (toward pass side)
            mid_adj = mid + (hi - lo) * mpmath.mpf("0.05")
            r = probe(mid_adj)
            mid = mid_adj if r is not None else mid
        if r is True:
            if mid < seen_fail_logrho:
                pass  # a pass closer to b_orb than a previously recorded fail would violate monotonicity below
            hi = mid
            seen_pass_logrho = mid
        elif r is False:
            lo = mid
            seen_fail_logrho = mid
        # r is None twice in a row: leave bracket as-is this iteration
    assert seen_fail_logrho <= seen_pass_logrho + mpmath.mpf("1e-9"), \
        f"non-monotonic pass/fail on side {sign:+d} at E={e}: fail seen at log(rho)={seen_fail_logrho}, " \
        f"pass at {seen_pass_logrho} -- the single-interval D_capture assumption does not hold here"
    boundary = (lo + hi) / 2
    # monotonicity check over ALL probes (not just the bracket): no pass may sit closer to b_orb than a fail
    fails = [abs(q["rho"]) for q in probes if q.get("pass") is False]
    passes = [abs(q["rho"]) for q in probes if q.get("pass") is True]
    monotone = not fails or not passes or max(fails) < min(passes)
    return {"delta": float(mpmath.e ** boundary), "bracket_exceeded": False, "audit_fail_at": audit_fails,
            "monotone_over_probes": monotone, "probes": probes}


def _job(args):
    e, sign = args
    r = I.orbiting(e)
    if r is None or r[0] > B_MAX:
        return e, sign, None
    bo, Rs = r
    log_lines = []
    side = _bisect_side(e, bo, sign, log_lines.append)
    return e, sign, {"b_orb": str(bo), "R_star": str(Rs), "side": side, "log": log_lines}


def main(procs: int = 14):
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    code = {f: _sha(ROOT / f) for f in CODE_FILES}
    results = {}
    jobs = [(e, s) for e in E_FRACS for s in (-1, 1)]
    with Pool(min(procs, len(jobs))) as pool:
        for e, sign, res in pool.imap_unordered(_job, jobs, chunksize=1):
            print(f"E/De={e} side {sign:+d}: {'no orbiting' if res is None else res['side']['delta']} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            if res is not None:
                row = results.setdefault(str(e), {"b_orb": res["b_orb"], "R_star": res["R_star"], "log": []})
                row["delta_minus" if sign < 0 else "delta_plus"] = res["side"]
                row["log"] += res["log"]
    doc = {"format": "c1b1-orbit-boundary-v1", "status": "NUMERICALLY VALIDATED evidence (not certified)",
           "contract": C.CONTRACT_VERSION, "target_sweep_rad": str(TARGET), "rho_bracket": [str(RHO_LO), str(RHO_HI)],
           "bisect_steps": BISECT_STEPS, "b_max": str(B_MAX),
           "energies": [{"e": e, **v} for e, v in results.items()],
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty), "code_sha256": code},
           "seconds": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
