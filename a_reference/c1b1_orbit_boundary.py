"""C1-B1 orbital-capture boundary width, ASYMMETRIC (designer verdicts on section 22 and on 3f2f73c / eadb413).

rho(E, b) = b / b_orb(E) - 1. Section 22 found the dt = 40 discretization error (sweep angle vs the audit quadrature)
exceeds the 1e-5 rad target somewhere inside |rho| <~ 1e-4 and is fine at |rho| = 1e-2. For each energy and each side
(sign -1: b < b_orb, sign +1: b > b_orb) this finds the boundary of the failing band as an INTERVAL, never a point:

    largest_nonpass <= delta_c <= smallest_pass          (all |rho|, on this side)

smallest_pass is the innermost pass with NO non-pass (fail or unknown) farther out: a pass island inside an unknown
stretch never pulls the validated region inward.

Only |rho| >= smallest_pass may later be called numerically validated; everything closer to b_orb, including the
uncertain interval itself, stays unsupported (designer: "그 사이 전체를 unsupported로 취급").

Per side:
  1. SCAN a fixed log ladder of |rho| (real evidence for monotonicity, not just the bisection's own bracket);
  2. if no probe passes, EXPAND outward (x2) to the side's physical limit (b -> 0, or b -> b_max); if still nothing
     passes, status = "no_pass_found" and the whole side is unsupported -- no boundary is invented;
  3. BISECT in log|rho| between the largest non-pass below the smallest pass and that pass, until their ratio is
     <= BISECT_RATIO.
A probe whose audit quadrature or run fails is "unknown": recorded, and counted as NON-pass (it can only push the
boundary outward, never inward). Monotonicity is checked over all MEASURED probes (every fail closer to b_orb than
every pass); if it breaks, status = "non_monotone", the simple band model -delta_- < rho < delta_+ does not hold at
this energy, the fixture says so and the script exits with code 3 (a result file, but not a successful run).

Run: python -m a_reference.c1b1_orbit_boundary [procs]     (needs D:\\reference for the audit)
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

E_FRACS = [Q(15, 100), Q(2, 10), Q(3, 10), Q(1, 2), Q(7, 10), Q(9, 10), Q(99, 100)]
TARGET = 1e-5                          # sweep-angle target, rad (sections 20 / 22)
SCAN = [Q(1, 10 ** 2), Q(3, 10 ** 3), Q(1, 10 ** 3), Q(3, 10 ** 4), Q(1, 10 ** 4), Q(3, 10 ** 5), Q(1, 10 ** 5),
        Q(1, 10 ** 6)]                 # |rho| ladder, outermost first
BISECT_RATIO = 1.05                    # stop when smallest_pass / largest_nonpass <= this
MAX_BISECT = 24
B_MAX = 2 * I.S.RE_GRID
CODE_FILES = ("a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py", "a_reference/c1b1_inner_validation.py",
              "a_reference/c1b1_orbit_boundary.py", "audit/independent_physics/c1b1_two_atom.py")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def one_point(e: Q, bo: Q, rho: Q) -> dict:
    """dt = 40 (high precision) vs the audit quadrature at b = b_orb (1 + rho): {"status": "ok", "e40": ...} or
    {"status": "audit_fail" | "run_fail", "reason": ...}."""
    b = bo * (1 + rho)
    st = I.state(e, b)
    I._register()
    ref = I.reference_task(({"e": e, "b_bohr": b, "name": "probe"}, st))
    if "error" in ref:
        return {"status": "audit_fail", "reason": ref["error"]}
    cap = int(3 * float(ref.get("time", 2e6)) / 40) + 400
    r = S.run_case(({"kind": "scatter", "name": "probe"}, st, 40, "hp", cap))
    if r.get("status") != "ok":
        return {"status": "run_fail", "reason": str(r.get("status"))}
    with mpmath.workdps(50):
        return {"status": "ok", "e40": float(mpmath.mpf(r["sweep"]) - mpmath.mpf(ref["sweep"]))}


def side_limit(bo: Q, sign: int) -> Q:
    """Largest |rho| reachable on this side inside 0 < b <= b_max."""
    return Q(99, 100) if sign < 0 else B_MAX / bo - 1


def search_side(e: Q, bo: Q, sign: int, probe=one_point) -> dict:
    """The boundary interval on one side (see module doc). `probe` is injectable for the logic tests."""
    limit = side_limit(bo, sign)
    probes = []

    def run(a: Q):
        r = probe(e, bo, sign * a)
        rec = {"abs_rho": float(a), "status": r["status"]}
        if r["status"] == "ok":
            rec["e40_sweep_rad"] = r["e40"]
            rec["pass"] = abs(r["e40"]) < TARGET
        else:
            rec["reason"] = r.get("reason", "")
            rec["pass"] = None                      # unknown: counted as non-pass
        probes.append(rec)
        return rec["pass"]

    def nonpass():
        return [Q(p["abs_rho"]) for p in probes if p["pass"] is not True]

    def outer_passes():
        """Passes with no non-pass (fail or unknown) farther out: the contiguous outer pass region."""
        n = max(nonpass(), default=Q(0))
        return [Q(p["abs_rho"]) for p in probes if p["pass"] is True and Q(p["abs_rho"]) > n]

    for a in SCAN:                                 # 1. scan
        if a <= limit:
            run(a)
    a = max([x for x in SCAN if x <= limit], default=limit)
    while not outer_passes() and a < limit:        # 2. expand outward
        a = min(2 * a, limit)
        run(a)
    if not outer_passes():
        return {"status": "no_pass_found", "side_limit": float(limit), "largest_fail": None, "largest_nonpass": None,
                "smallest_pass": None, "unknown_probes": sum(p["pass"] is None for p in probes), "probes": probes}
    for _ in range(MAX_BISECT):                    # 3. bisect (geometric mean) between the tightest pair
        sp, lo = min(outer_passes()), max(nonpass(), default=None)
        if lo is None or float(sp / lo) <= BISECT_RATIO:
            break
        mid = mpmath.sqrt(mpmath.mpf(lo.numerator) / lo.denominator * mpmath.mpf(sp.numerator) / sp.denominator)
        run(Q(mpmath.nstr(mid, 12)))
    sp, lo = min(outer_passes()), max(nonpass(), default=None)
    fails = [p["abs_rho"] for p in probes if p["pass"] is False]
    passes = [p["abs_rho"] for p in probes if p["pass"] is True]
    monotone = not fails or not passes or max(fails) < min(passes)   # no measured pass closer in than a measured fail
    return {"status": "ok" if monotone else "non_monotone", "side_limit": float(limit),
            "largest_fail": max(fails, default=None), "largest_nonpass": None if lo is None else float(lo),
            "smallest_pass": float(sp), "unknown_probes": sum(p["pass"] is None for p in probes), "probes": probes}


def _job(args):
    e, sign = args
    r = I.orbiting(e)
    if r is None or r[0] > B_MAX:
        return e, sign, None
    bo, Rs = r
    return e, sign, {"b_orb": str(bo), "R_star": str(Rs), "side": search_side(e, bo, sign)}


def main(procs: int = 14) -> int:
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    code = {f: _sha(ROOT / f) for f in CODE_FILES}
    results = {}
    jobs = [(e, s) for e in E_FRACS for s in (-1, 1)]
    with Pool(min(procs, len(jobs))) as pool:
        for e, sign, res in pool.imap_unordered(_job, jobs, chunksize=1):
            s = None if res is None else res["side"]
            print(f"E/De={e} side {sign:+d}: " + ("no orbiting in range" if s is None else
                  f"{s['status']} nonpass<={s['largest_nonpass']} pass>={s['smallest_pass']} "
                  f"({len(s['probes'])} probes)") + f" ({time.time() - t0:.0f}s)", flush=True)
            if res is not None:
                row = results.setdefault(str(e), {"b_orb": res["b_orb"], "R_star": res["R_star"]})
                row["delta_minus" if sign < 0 else "delta_plus"] = s
    bad = sorted(f"{e} {k}" for e, row in results.items() for k in ("delta_minus", "delta_plus")
                 if row[k]["status"] == "non_monotone")
    doc = {"format": "c1b1-orbit-boundary-v2",
           "status": ("FAILED: non-monotone pass/fail at " + ", ".join(bad)) if bad else
                     "NUMERICALLY VALIDATED evidence (not certified)",
           "contract": C.CONTRACT_VERSION, "target_sweep_rad": TARGET, "scan_abs_rho": [str(a) for a in SCAN],
           "bisect_ratio": BISECT_RATIO, "b_max": str(B_MAX),
           "energies": [{"e": e, **v} for e, v in sorted(results.items(), key=lambda kv: Q(kv[0]))],
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty), "code_sha256": code},
           "seconds": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s; status: {doc['status']}")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 14))
