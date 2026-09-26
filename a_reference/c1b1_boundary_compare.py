"""Compare two orbital-capture boundary records side by side (designer verdict on 7532788: after re-measuring with the
one canonical generator, record how every side's boundary moved against the 50cceaa record).

Per energy and side (delta_minus = negative, delta_plus = positive): status, monotonicity (every measured fail closer
to b_orb than every measured pass), largest_nonpass, smallest_pass, outermost pass, the relative change of each, and
whether the probe sequence (|rho|, pass) is identical. Run: python -m a_reference.c1b1_boundary_compare OLD NEW OUT
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _side(s: dict) -> dict:
    probes = s.get("probes") or []
    passes = [p["abs_rho"] for p in probes if p.get("pass") is True]
    fails = [p["abs_rho"] for p in probes if p.get("pass") is False]
    return {"status": s["status"], "monotone": not passes or not fails or max(fails) < min(passes),
            "largest_nonpass": s.get("largest_nonpass"), "smallest_pass": s.get("smallest_pass"),
            "outermost_pass": max(passes, default=None), "probes": len(probes)}


def _rel(a, b):
    return None if a is None or b is None else (b - a) / a


def compare_records(old: dict, new: dict) -> list[dict]:
    rows = []
    olds = {r["e"]: r for r in old["energies"]}
    for rn in new["energies"]:
        ro = olds.get(rn["e"])
        for name in ("delta_minus", "delta_plus"):
            n = _side(rn[name])
            o = _side(ro[name]) if ro is not None else None
            seq = (lambda s: [(p["abs_rho"], p.get("pass")) for p in s["probes"]])
            rows.append({
                "e": rn["e"], "side": name, "old": o, "new": n,
                "rel_change": None if o is None else {k: _rel(o[k], n[k]) for k in
                                                      ("largest_nonpass", "smallest_pass", "outermost_pass")},
                "interval_identical": o is not None and all(o[k] == n[k] for k in
                                                            ("largest_nonpass", "smallest_pass", "outermost_pass")),
                "probe_sequence_identical": ro is not None and seq(ro[name]) == seq(rn[name])})
    return rows


def main(old: str, new: str, out: str) -> None:
    o, n = (json.loads(Path(x).read_text(encoding="utf-8")) for x in (old, new))
    rows = compare_records(o, n)
    doc = {"old": Path(old).name, "new": Path(new).name, "old_git_head": o["provenance"]["git_head"],
           "new_git_head": n["provenance"]["git_head"], "sides": rows,
           "summary": {"sides": len(rows), "interval_identical": sum(r["interval_identical"] for r in rows),
                       "probe_sequence_identical": sum(r["probe_sequence_identical"] for r in rows),
                       "all_monotone": all(r["new"]["monotone"] for r in rows)}}
    Path(out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(json.dumps(doc["summary"]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
