"""C1-B1 inner-region energy check (designer 19th ed.): the relative energy carried OUT of the inner region.

Complements c1b1_inner_validation (whose runs record momenta, not exit positions). Each case is started at 20 bohr
inbound and stepped until it is back at R >= 20 bohr outbound; the exit state gives
  E_exit  = |P|^2 / (2 mu) + V(R)                      (P = p_j, relative momentum of equal masses)
  E~_exit = E_exit - (dt^2 / (8 mu)) |F(R)|^2          (the KDK modified energy; -> E_exit as R -> infinity)
for the candidate (position FX(96,48), momentum FX(96,80), drift v2) and the high-precision run (exact positions,
momentum FX(256,192)). Quantization in energy = E~_cand - E~_hp; integrator energy error = E~_hp - E_initial.
V and F at the exit radius are enclosed at 2^-512 (the diagnostic midpoint is far below every reported difference).
Also two hybrids at a few energies to split the cause: pos_only (position rounded, momentum FX(256,192)) and
mom_only (exact positions, momentum FX(96,80)). Measurement only. Run: python -m a_reference.c1b1_inner_energy -> fixtures/c1b1_inner_energy_v1.json
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

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_inner_energy_v1.json"
E_FRACS = [Q(1, 10 ** k) for k in range(2, 14)]
B_BOHR = [Q(0), 2 * I.S.RE_GRID]
M = 512


# cause decomposition (designer 19th ed.: position vs momentum rounding): one representation rounded, the other exact-ish
HYBRID = {"pos_only": (I.POS, I.HPM, "v2"),           # position FX(96,48), momentum FX(256,192)
          "mom_only": (C.ExactPosition(), I.MOM, "v2")}  # exact positions, momentum FX(96,80)
DECOMP_E = [Q(1, 10 ** k) for k in (6, 8, 9, 10, 12)]


def energy(run):
    q = C.relative(run.pos, *run.atoms)
    R2 = sum((x * x for x in q), Q(0))
    P = C.exact(run.mom, run.atoms[1].p)
    E = sum((x * x for x in P), Q(0)) / (2 * I.MU) + C.potential_high(R2, M)
    F = C.force_high(R2, M)
    return E, E - run.dt ** 2 / (8 * I.MU) * F * F, R2


def task(args):
    e, b, pname = args
    t0 = time.time()
    st = I.state(e, b)
    pos, mom, rule = I.PROFILES.get(pname) or HYBRID[pname]
    run = C.new_run(pos, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=mom, validated_only=False,
                    drift=rule)
    E0, Em0, _ = energy(run)
    passed, prev = False, None
    while True:
        C.step(run)
        R2 = sum((x * x for x in C.relative(run.pos, *run.atoms)), Q(0))
        if prev is not None and R2 > prev:
            passed = True
        prev = R2
        if passed and R2 >= 400:
            break
    E1, Em1, R2 = energy(run)
    return {"e": str(e), "b": str(b), "profile": pname, "steps": run.t_steps, "E_initial": str(E0),
            "Emod_initial": str(Em0), "E_exit": str(E1), "Emod_exit": str(Em1), "R2_exit": str(R2),
            "dP": [str(x) for x in C.total_momentum(run)], "seconds": round(time.time() - t0, 1)}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    t0 = time.time()
    jobs = [(e, b, p) for e in E_FRACS for b in B_BOHR for p in ("hp", "cand")]
    jobs += [(e, b, p) for e in DECOMP_E for b in B_BOHR for p in HYBRID]
    with Pool(procs) as pool:
        res = pool.map(task, jobs, chunksize=1)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference"], capture_output=True, text=True,
                           cwd=ROOT).stdout.strip()
    doc = {"format": "c1b1-inner-energy-v1", "status": "NUMERICALLY VALIDATED evidence (measurement)",
           "contract": C.CONTRACT_VERSION, "dt": 40, "runs": res,
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference": bool(dirty),
                          "code_sha256": {f: _sha(ROOT / f) for f in ("a_reference/c1b1_two_atom.py",
                                                                      "a_reference/c1b1_inner_validation.py",
                                                                      "a_reference/c1b1_inner_energy.py")}},
           "seconds": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
