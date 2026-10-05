"""Independent checker for FORMULA_REPRO_B_V0. Imports neither harness, campaign, transform_checks nor the upstream
probe. Cells are recomputed from the stored exact endpoints (own half-even); stored cells and derived fields are only
compared. Completeness and record consistency are checked first; summary labels are computed last.

    python -m experiments.formula_repro_b_v0.checker RUN_DIR --out FILE
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import statistics
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCENARIOS = ("A2_bound", "A3_low", "A3_high")
EVALUATORS = ("original", "cache", "algebra")
FIXED_PRECS = (96, 128, 192)
POLICY_STEPS = (1, 10, 100, 1000)
GRID = [64, 96, 128, 192, 256, 384, 512]
REPS = 3
N_ATOMS = {"A2_bound": 2, "A3_low": 3, "A3_high": 3}


class CheckError(Exception):
    pass


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def half_even(x):
    q = x.numerator // x.denominator
    r = x - q
    if r > F(1, 2) or (r == F(1, 2) and q % 2):
        q += 1
    return q


def cells_from_scaled(spans):
    """spans are exact endpoints already multiplied by 2^48 (positions) / 2^80 (momenta)."""
    out = []
    for lo, hi in spans:
        a, b = half_even(F(lo)), half_even(F(hi))
        if a != b:
            return None
        out.append(a)
    return out


def ref_cells(key):
    """Own cells from the repository V1 endpoints_key text (repr of mpi raw tuples)."""
    from mpmath.libmp import to_rational
    ends = []
    for part in key.split("|"):
        lo, hi = ast.literal_eval(part)
        ends.append((F(*to_rational(lo)), F(*to_rational(hi))))
    n = len(ends) // 2
    scaled = [(lo * (1 << 48), hi * (1 << 48)) for lo, hi in ends[:n]] + [(lo * (1 << 80), hi * (1 << 80)) for lo, hi in ends[n:]]
    return cells_from_scaled(scaled)


def check(run_dir):
    d = Path(run_dir)
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    bad = [s for s, h in seal["source_sha256_lf"].items() if lf(ROOT / s) != h]
    if bad:
        raise CheckError(f"sources changed since the run: {bad}")
    up = HERE / "upstream"
    if any(hashlib.sha256((up / k).read_bytes()).hexdigest() != h for k, h in seal["upstream_sha256_raw"].items()):
        raise CheckError("upstream copy changed since the run")
    incomplete, invalid, mismatch = [], [], []
    if seal.get("sealed_sources_dirty"):
        incomplete.append("campaign started with uncommitted sealed sources")
    tc = json.loads((d / "transform_checks.json").read_text(encoding="utf-8"))
    upt = (d / "upstream_pytest.txt").read_text(encoding="utf-8")
    ref_doc = json.loads((d / "reference.json").read_text(encoding="utf-8"))
    if ref_doc.get("bits") != 384 or "repository" not in ref_doc.get("source", ""):
        invalid.append("reference is not the repository V1 stream at 384 bits")
    refs = {}
    for s in SCENARIOS:
        for st in POLICY_STEPS:
            r = ref_doc["results"][s][str(st)]
            mine = ref_cells(r["endpoints_key"])
            if mine is None or mine != r["cells"]:
                invalid.append(f"reference {s} step {st}: cells not reproduced from endpoints")
            refs[(s, st)] = mine
    runs = {}
    for rep in range(REPS):
        for s in SCENARIOS:
            for ev in EVALUATORS:
                for p in FIXED_PRECS:
                    runs[("fixed", s, p, ev, rep)] = f"fixed__{s}__p{p}__{ev}__t{rep}"
                for st in POLICY_STEPS:
                    runs[("policy", s, st, ev, rep)] = f"policy__{s}__s{st}__{ev}__t{rep}"
    docs = {}
    for key, stem in runs.items():
        if (d / f"{stem}.ERROR.txt").exists():
            incomplete.append(f"run failed: {stem}")
        f = d / f"{stem}.json"
        if not f.exists():
            incomplete.append(f"missing: {stem}")
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        mode, s, x, ev, _ = key
        meta_ok = doc.get("mode") == mode and doc.get("scenario") == s and doc.get("evaluator") == ev and \
            doc.get("steps" if mode == "policy" else "prec") == x
        if not meta_ok:
            invalid.append(f"{stem}: metadata differs from its name")
        if doc.get("child_exit_code") != 0 or not doc.get("child_pid_confirmed_exited"):
            invalid.append(f"{stem}: child exit not confirmed")
        n = 6 * N_ATOMS[s]
        if mode == "policy":
            bits = [a["bits"] for a in doc["attempts"]]
            if bits != GRID[:len(bits)]:
                invalid.append(f"{stem}: attempts are not the upstream grid prefix")
            if doc["status"] == "DECIDED":
                last = doc["attempts"][-1]
                if doc.get("decided_bits") != last["bits"]:
                    invalid.append(f"{stem}: decided_bits differs from the last attempt")
                mine = cells_from_scaled(last["spans_scaled"] or [])
                if mine is None or len(mine) != n or mine != doc["cells"]:
                    invalid.append(f"{stem}: cells not reproduced from stored endpoints")
                elif mine != refs[(s, x)]:
                    mismatch.append(f"{stem}: cells differ from the repository reference")
                for a in doc["attempts"][:-1]:
                    if a["status"] == "DECIDED":
                        invalid.append(f"{stem}: a DECIDED attempt before the last")
            else:
                incomplete.append(f"{stem}: not decided ({doc['status']})")
        else:
            if doc["status"] == "COMPLETED" and sorted(doc["reads"]) != ["100", "1000"]:
                invalid.append(f"{stem}: completed but checkpoints missing")
            for st, r in doc["reads"].items():
                if r["cells"] is not None:
                    mine = cells_from_scaled(r["spans_scaled"])
                    if mine != r["cells"]:
                        invalid.append(f"{stem} step {st}: cells not reproduced from stored endpoints")
                    elif mine != refs[(s, int(st))]:
                        mismatch.append(f"{stem} step {st}: decided cells differ from the reference")
                elif cells_from_scaled(r["spans_scaled"]) is not None:
                    invalid.append(f"{stem} step {st}: stored undecided but endpoints decide")
        docs[key] = doc

    def med(vals):
        vals = [v for v in vals if v is not None]
        return statistics.median(vals) if vals else None

    fixed = {}
    for s in SCENARIOS:
        for p in FIXED_PRECS:
            row = {}
            for ev in EVALUATORS:
                ds = [docs.get(("fixed", s, p, ev, r)) for r in range(REPS)]
                ds = [x for x in ds if x]
                row[ev] = {"status": sorted({x["status"] for x in ds}),
                           "compute_cpu_median": med(x["compute_cpu_s"] for x in ds),
                           "compute_wall_median": med(x["compute_wall_s"] for x in ds),
                           "decided_100": sorted({x["reads"].get("100", {}).get("cells") is not None for x in ds}),
                           "decided_1000": sorted({x["reads"].get("1000", {}).get("cells") is not None for x in ds})}
            same_work = all(row[ev]["status"] == ["COMPLETED"] for ev in EVALUATORS)
            for ev in ("cache", "algebra"):
                o, c = row["original"]["compute_cpu_median"], row[ev]["compute_cpu_median"]
                row[ev]["speedup_vs_original_same_work"] = (o / c) if (same_work and o and c) else None
            row["same_work"] = same_work
            fixed[f"{s}_p{p}"] = row
    policy = {}
    for s in SCENARIOS:
        for st in POLICY_STEPS:
            row = {}
            for ev in EVALUATORS:
                ds = [x for x in (docs.get(("policy", s, st, ev, r)) for r in range(REPS)) if x]
                row[ev] = {"decided_bits": sorted({x.get("decided_bits") for x in ds}, key=lambda v: (v is None, v)),
                           "attempt_bits": sorted({tuple(a["bits"] for a in x["attempts"]) for x in ds}),
                           "retry_cpu_median": med(x["compute_cpu_s"] for x in ds),
                           "retry_wall_median": med(x["compute_wall_s"] for x in ds),
                           "prepare_wall_median": med(x["prepare_wall_s"] for x in ds),
                           "prepare_cpu_median": med(x["prepare_cpu_s"] for x in ds),
                           "load_wall_median": med(x["load_wall_s"] for x in ds),
                           "child_total_cpu_median": med(x["child_total_cpu_s"] for x in ds),
                           "process_wall_median": med(x.get("parent_process_wall_s") for x in ds),
                           "process_wall_runs": [x.get("parent_process_wall_s") for x in ds]}
            for ev in ("cache", "algebra"):
                o, c = row["original"], row[ev]
                row[ev]["speedup_retry_cpu"] = (o["retry_cpu_median"] / c["retry_cpu_median"]) \
                    if o["retry_cpu_median"] and c["retry_cpu_median"] else None
                row[ev]["speedup_process_wall"] = (o["process_wall_median"] / c["process_wall_median"]) \
                    if o["process_wall_median"] and c["process_wall_median"] else None
            policy[f"{s}_s{st}"] = row
    evidence_ok = not incomplete and not invalid
    agreement = "INCOMPLETE" if not evidence_ok else ("MISMATCH" if mismatch else "ALL_DECIDED_CELLS_MATCH_REFERENCE")
    return {"checker": "FORMULA_REPRO_B_V0 independent checker",
            "incomplete": incomplete, "invalid_evidence": invalid, "mismatches": mismatch,
            "OBSERVATION_AGREEMENT": agreement,
            "TRANSFORM_CHECKS": "PASS" if tc.get("PASS") else "FAIL",
            "UPSTREAM_TESTS": upt.strip().splitlines()[-1] if upt.strip() else "missing",
            "transform_checks": {k: (v if not isinstance(v, list) else len(v)) for k, v in tc.items()},
            "fixed_precision": fixed, "policy": policy,
            "note": "Observed-cell agreement is not a certification of the exact state, trajectory or world history."}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    v = check(a.run_dir)
    Path(a.out).write_text(json.dumps(v, indent=1), encoding="utf-8")
    print(json.dumps({k: v[k] for k in ("OBSERVATION_AGREEMENT", "TRANSFORM_CHECKS", "UPSTREAM_TESTS")}, indent=1))
    print("incomplete", len(v["incomplete"]), "invalid", len(v["invalid_evidence"]), "mismatch", len(v["mismatches"]))


if __name__ == "__main__":
    main()
