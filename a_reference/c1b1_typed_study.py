"""C1-B1 study 3 (designer 13th ed. item 3 of the order): the typed profile pair position = FX(96,48),
momentum = FX(64,48) on all 40 study cases at dt = 10, 20, 40 -- compared bit for bit (observables) with the
single-profile FX(64,48) runs of study 2 (same fraction bits, so they must agree while no position leaves the
FX(64,48) range), and against the 80-digit references. Measurement only.

Run: python -m a_reference.c1b1_typed_study
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import a_reference.c1b1_dt_study as S
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_typed_study_v1.json"
TYPED = "POS96_48+MOM64_48"
DTS = [10, 20, 40]


def task(args):
    S.PROFILES[TYPED] = (FixedPoint(96, 48), FixedPoint(64, 48))
    return S.run_case(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main(procs: int = 11):
    cs = S.cases()
    states = [S.scattering_state(c["e"], c["b"]) if c["kind"] == "scatter" else S.bound_state(c["f"]) for c in cs]
    old = {r["case"]: r for r in json.loads(S.OUT.read_text(encoding="utf-8"))["references"]}
    tasks = []
    for c, st in zip(cs, states):
        nom = old[c["name"]].get("nominal", {})
        t_ref = float(nom.get("time", nom.get("two_periods", 4e5)))
        for dt in DTS:
            tasks.append((c, st, dt, TYPED, int(3 * t_ref / dt) + 200))
    tasks.sort(key=lambda t: -t[4])
    t0 = time.time()
    with Pool(procs) as pool:
        runs = list(pool.imap_unordered(task, tasks))
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit"], capture_output=True,
                           text=True, cwd=ROOT).stdout.strip()
    doc = {"format": "c1b1-typed-study-v1", "typed": {"position": "FX(96,48)", "momentum": "FX(64,48)"},
           "dts": DTS, "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_or_audit": bool(dirty),
                                      "code_sha256": {f: _sha(ROOT / f) for f in (
                                          "a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py",
                                          "a_reference/c1b1_typed_study.py")}},
           "runs": sorted(runs, key=lambda r: (r["case"], r["dt"]))}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
