"""C1-B1 near-orbiting validation (designer 20th ed., item 3): the orbital-capture boundary b ~ b_orb, NUMERICALLY VALIDATED.

Orbiting exists only below E_max ~ 0.9964 De; from ~0.14 De up to E_max its impact parameter lies inside b <= 2 R_e; there the pair can
circle on the centrifugal barrier top for a long time -- the most sensitive trajectories -- and no study had run them
(the first orbiting_b always returned 0, section 20). Here b_orb is computed precisely from the barrier-top
conditions (c1b1_inner_validation.orbiting), not from a grid:
    dV_eff/dR = 0  ->  L^2 = mu R^3 V'(R),     V_eff(R*) = E  ->  E = V(R*) + R* V'(R*) / 2     (outer branch)
and each energy is run at b below / at / above b_orb: 0.8 b_orb, b_orb (1 -+ delta) for delta = 1e-2, 1e-4, 1e-6, b_orb,
1.2 b_orb (only b <= 2 R_e). Same three runs and audit reference as c1b1_inner_validation (quantization: candidate vs
high precision at dt = 40; discretization: high precision at dt 40 / 20 vs the audit quadrature). Measurement only.

Run: python -m a_reference.c1b1_orbit_validation     (the audit needs the published Lang 2024 files)
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

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_orbit_validation_v1.json"
PARTIAL = ROOT / "runs" / "c1b1_orbit_validation_partial.jsonl"
E_FRACS = [Q(15, 100), Q(2, 10), Q(3, 10), Q(1, 2), Q(7, 10), Q(9, 10), Q(99, 100)]   # orbiting exists below ~0.9964 De
DELTAS = [Q(1, 100), Q(1, 10 ** 4), Q(1, 10 ** 6)]
B_MAX = 2 * I.S.RE_GRID
CODE_FILES = ("a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py", "a_reference/c1b1_inner_validation.py",
              "a_reference/c1b1_orbit_validation.py", "audit/independent_physics/c1b1_two_atom.py")


def cases():
    out = []
    for e in E_FRACS:
        r = I.orbiting(e)
        if r is None:
            continue
        bo, Rs = r
        bs = [("0.8", Q(4, 5) * bo)] + [(f"1-{d}", bo * (1 - d)) for d in DELTAS] + [("1", bo)] + \
             [(f"1+{d}", bo * (1 + d)) for d in reversed(DELTAS)] + [("1.2", Q(6, 5) * bo)]
        for tag, b in bs:
            if b <= B_MAX:
                out.append({"kind": "scatter", "e": e, "b_bohr": b, "b_over_b_orb": tag, "b_orb": bo, "R_star": Rs,
                            "name": f"orbit E/De={e} b=b_orb*{tag}"})
    return out


def _run(item):
    key, task, args = item
    I._register()
    return key, task.__name__, task(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 20):
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    code = {f: _sha(ROOT / f) for f in CODE_FILES}
    cs = cases()
    sts = [I.state(c["e"], c["b_bohr"]) for c in cs]
    print(f"{len(cs)} cases, states built {time.time() - t0:.0f}s", flush=True)
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
    with Pool(procs) as pool, PARTIAL.open("a", encoding="utf-8") as f:
        todo = [(f"ref|{c['name']}", I.reference_task, (c, st)) for c, st in zip(cs, sts) if f"ref|{c['name']}" not in done]
        for key, name, res in pool.imap_unordered(_run, todo, chunksize=1):
            f.write(json.dumps({"key": key, "task": name, "result": res}) + "\n")
            f.flush()
            done[key] = {"key": key, "task": name, "result": res}
        print(f"references done {time.time() - t0:.0f}s", flush=True)
        jobs = []
        for c, st in zip(cs, sts):
            r = done[f"ref|{c['name']}"]["result"]
            t_ref = float(r.get("time", 2e6))
            for dt, pname in ((40, "cand"), (40, "hp"), (20, "hp")):
                cap = int(3 * t_ref / dt) + 400
                jobs.append((cap * (2.5 if pname == "hp" else 1),
                             (f"run|{c['name']}|{dt}|{pname}", I.run_task, (c, st, dt, pname, cap))))
        todo = [j for _, j in sorted(jobs, key=lambda x: -x[0]) if j[0] not in done]
        print(f"{len(todo)} runs to do", flush=True)
        for i, (key, name, res) in enumerate(pool.imap_unordered(_run, todo, chunksize=1)):
            f.write(json.dumps({"key": key, "task": name, "result": res}) + "\n")
            f.flush()
            done[key] = {"key": key, "task": name, "result": res}
            if i % 10 == 0:
                print(f"  {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
    doc = {"format": "c1b1-orbit-validation-v1", "status": "NUMERICALLY VALIDATED evidence (not certified)",
           "contract": C.CONTRACT_VERSION, "position": I.POS.name, "momentum": I.MOM.name, "b_max": str(B_MAX),
           "cases": [{"name": c["name"], "e": str(c["e"]), "b_bohr": str(c["b_bohr"]), "b_over_b_orb": c["b_over_b_orb"],
                      "b_orb": str(c["b_orb"]), "R_star": str(c["R_star"]), "E_rep": str(st["E_rep"]),
                      "L_rep": str(st["L_rep"])} for c, st in zip(cs, sts)],
           "references": [done[f"ref|{c['name']}"]["result"] for c in cs],
           "runs": [done[k]["result"] for k in sorted(k for k in done if k.startswith("run|"))],
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty), "code_sha256": code},
           "seconds_this_session": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
