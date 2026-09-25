"""C1-B1 boundary study (designer 14th ed.): the seven E = 10 De scattering cases rebuilt INSIDE the validated range.

Study 1 put the nominal state (E = 10 De exactly) on the FX(64,32) grid; five of the seven represented states then
lay up to 1.06e-10 (relative) ABOVE 10 De, so the strict integrator contract refuses them. The contract stays strict
(no tolerance); the test input is fixed instead: for each impact parameter the nominal radial momentum is rounded to
the MOMENTUM profile FX(64,48) and, while new_run(validated_only=True) refuses the state, its magnitude is lowered by
one raw unit (2^-48 a.u.). The tangential momentum -- hence the angular momentum -- and the positions are untouched,
so this is the nearest stored state along the radial momentum whose exact relative energy is <= 10 De.

Each rebuilt state is then run with the typed pair position FX(96,48) + momentum FX(64,48) at dt = 10, 20, 40 (the
run is built with validated_only=True: the world contract itself accepts it) and compared with the independent
audit reference for exactly that stored state. Measurement only.

Run: python -m a_reference.c1b1_boundary_study   (needs D:\\reference for the audit's Fortran parameters)
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
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_boundary_study_v1.json"
POS, MOM = FixedPoint(96, 48), FixedPoint(64, 48)
TYPED = "POS96_48+MOM64_48"
DTS = [10, 20, 40]
E_FRAC = Q(10)


def _accepted(P) -> bool:
    ri, rj = (-S.R_START / 2, Q(0), Q(0)), (S.R_START / 2, Q(0), Q(0))
    try:
        C.new_run(POS, 40, ri, tuple(-x for x in P), rj, P, momentum_profile=MOM)
        return True
    except C.IntegratorDomainExceeded:
        return False


def boundary_state(b: Q):
    """The nearest stored state (radial momentum only, 2^-48 steps) at nominal E = 10 De that the contract accepts."""
    mpmath.mp.dps = 50
    E = E_FRAC * S.DE_GRID
    p_inf = mpmath.sqrt(2 * S.mp(S.MU) * S.mp(E))
    L = S.mp(b * S.RE_GRID) * p_inf
    V0 = S.mp(C.potential_high(S.R_START ** 2))
    Pt = L / S.mp(S.R_START)
    Pr = -mpmath.sqrt(2 * S.mp(S.MU) * (S.mp(E) - V0) - Pt * Pt)
    q = lambda x: MOM.to_exact(MOM.from_exact(S.mq(x)))
    P = [q(Pr), q(Pt), Q(0)]
    first = list(P)
    lowered = 0
    while not _accepted(tuple(P)):
        P[0] += Q(1, 1 << MOM.frac_bits)                        # Pr < 0: one raw unit smaller in magnitude
        lowered += 1
        if lowered > 1 << 20:
            raise RuntimeError("no accepted state near the boundary")
    P = tuple(P)
    ri, rj = (-S.R_START / 2, Q(0), Q(0)), (S.R_START / 2, Q(0), Q(0))
    run = C.new_run(POS, 40, ri, tuple(-x for x in P), rj, P, momentum_profile=MOM)
    lo, hi = C.relative_energy_enclosure(run, 512)
    f_lo, f_hi = C.relative_energy_enclosure(C.new_run(POS, 40, ri, tuple(-x for x in first), rj, first,
                                                       momentum_profile=MOM, validated_only=False), 512)
    E_rep = C.relative_kinetic(tuple(-x for x in P), P, C.AR40_MASS_ME, C.AR40_MASS_ME) + \
        C.potential_high(S.R_START ** 2, 512)
    return {"E_nom": E, "L_nom": mpmath.nstr(L, 40), "E_rep": E_rep, "L_rep": S.R_START * P[1],
            "r_i": ri, "p_i": tuple(-x for x in P), "r_j": rj, "p_j": P,
            "raw_units_lowered": lowered,
            "E_rep_over_10De_minus_1": mpmath.nstr(S.mp((hi + lo) / 2 / C.INTEGRATOR_E_MAX - 1), 6),
            "E_rep_hi_le_10De": hi <= C.INTEGRATOR_E_MAX,
            "first_rounding_over_10De_minus_1": mpmath.nstr(S.mp((f_hi + f_lo) / 2 / C.INTEGRATOR_E_MAX - 1), 6)}


def task(args):
    S.PROFILES[TYPED] = (POS, MOM)
    case, st, dt, pname, cap = args
    C.new_run(POS, dt, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=MOM)   # the world contract accepts
    return S.run_case(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    cs = [{"kind": "scatter", "e": E_FRAC, "b": b, "name": f"scatter E/De={E_FRAC} b/Re={b} (inside 10 De)"}
          for b in S.B_FRACS]
    t0 = time.time()
    with Pool(procs) as pool:
        states = pool.map(boundary_state, [c["b"] for c in cs])
        refs = pool.map(S.reference_for, list(zip(cs, states)))
        tasks = []
        for c, st, rf in zip(cs, states, refs):
            t_ref = float(rf["represented"]["time"])
            for dt in DTS:
                tasks.append((c, st, dt, TYPED, int(3 * t_ref / dt) + 200))
        runs = list(pool.imap_unordered(task, tasks))
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    keep = ("raw_units_lowered", "E_rep_over_10De_minus_1", "E_rep_hi_le_10De", "first_rounding_over_10De_minus_1")
    doc = {"format": "c1b1-boundary-study-v1", "contract": C.CONTRACT_VERSION, "typed": {
               "position": POS.name, "momentum": MOM.name}, "dts": DTS, "integrator_E_max": str(C.INTEGRATOR_E_MAX),
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty),
                          "code_sha256": {f: _sha(ROOT / f) for f in (
                              "a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py",
                              "a_reference/c1b1_boundary_study.py", "audit/independent_physics/c1b1_two_atom.py")}},
           "cases": [{"name": c["name"], "b": str(c["b"]), "p_j": [str(x) for x in st["p_j"]], "L_rep": str(st["L_rep"]),
                      **{k: st[k] for k in keep}} for c, st in zip(cs, states)],
           "references": refs, "runs": sorted(runs, key=lambda r: (r["case"], r["dt"]))}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
