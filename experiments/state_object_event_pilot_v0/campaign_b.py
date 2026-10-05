"""PART B campaign: stage 1 (96 bit, steps 10/100), the protocol's fixed extension rule, stage 2 (96 and 128 bit,
steps 10/100/1000) only if the rule says so. Fresh process per run, sequential, 3 runs per (path, precision).
Before stage 1 the PART B soundness tests are run; any failure forbids the campaign.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from fractions import Fraction as Q
from pathlib import Path

from .campaign import PKG, REPS, ROOT, log, run_worker, seal

SEALED_B = ["experiments/state_object_event_pilot_v0/" + f for f in
            ("__init__.py", "event_lineage.py", "derivative_certificate.py", "campaign.py", "campaign_b.py",
             "protocol.json")] + \
           ["exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py",
            "a_reference/ar2_lang2024.py", "a_reference/c1b1_energy_bound.py", "a_reference/c1b1_outer_bound.py",
            "a_reference/c1b1_outer_bootstrap.py", "docs/active/state_object_event_pilot_v0/derivative_certificate.json.gz"]
STAGE1 = [(96, 100, [10, 100])]
STAGE2 = [(96, 1000, [10, 100, 1000]), (128, 1000, [10, 100, 1000])]
CPU_WALL = 10


def name(path, prec, last, rep):
    return f"B__{path}__p{prec}__s{last}__t{rep}"


def run_stage(out, plan):
    for rep in range(REPS):
        for prec, last, want in plan:
            for path in ("baseline", "candidate"):
                run_worker(out, "event_lineage", ["--path", path, "--prec", str(prec), "--last", str(last),
                                                  "--want", ",".join(map(str, want))], name(path, prec, last, rep))


def load(out, path, prec, last):
    docs = []
    for rep in range(REPS):
        f = out / f"{name(path, prec, last, rep)}.json"
        if f.exists():
            docs.append(json.loads(f.read_text(encoding="utf-8")))
    return docs


def _intersect(r1, r2):
    return all(Q(a[0]) <= Q(b[1]) and Q(b[0]) <= Q(a[1]) for a, b in zip(r1, r2))


def decide_extension(out):
    """The protocol's fixed rule, evaluated on stage-1 runs (the checker re-derives it independently)."""
    prec, last, want = STAGE1[0]
    base, cand = load(out, "baseline", prec, last), load(out, "candidate", prec, last)
    d = {"rule": "extend iff (candidate DECIDED at 96-bit step 100 OR baseline worst >= 2 x candidate worst) AND "
                 "soundness PASS AND candidate CPU <= 10 x baseline CPU", "runs": [len(base), len(cand)]}
    if len(base) != REPS or len(cand) != REPS:
        d["decision"] = "INCOMPLETE"
        return d
    sound = []
    for b, c in zip(base, cand):
        for s in map(str, want):
            rb, rc = b["read"].get(s), c["read"].get(s)
            if rb is None or rc is None:
                sound.append(False)
                continue
            if rb["cells"] is not None and rc["cells"] is not None:
                sound.append(rb["cells"] == rc["cells"])
            sound.append(_intersect(rb["ranges"], rc["ranges"]))
            sound.append(rc["tags"] <= 3 * (int(s) + 1))
        sound.append(c["stop"] is None)
    rb, rc = base[0]["read"]["100"], cand[0]["read"]["100"]
    worst_b = max(Q(rb["norm_radius_pos_exact"]), Q(rb["norm_radius_mom_exact"]))
    worst_c = max(Q(rc["norm_radius_pos_exact"]), Q(rc["norm_radius_mom_exact"]))
    cpu_b = statistics.median(x["cpu_s"] for x in base)
    cpu_c = statistics.median(x["cpu_s"] for x in cand)
    decided_c, decided_b = rc["cells"] is not None, rb["cells"] is not None
    signal = (decided_c and not decided_b) or worst_b >= 2 * worst_c
    d.update(campaign_soundness_pass=all(sound), candidate_decided_100=decided_c, baseline_decided_100=decided_b,
             worst_norm_baseline=float(worst_b), worst_norm_candidate=float(worst_c),
             radius_ratio=float(worst_b / worst_c) if worst_c else None,
             cpu_median_baseline=cpu_b, cpu_median_candidate=cpu_c, cpu_ratio=cpu_c / cpu_b, signal=signal)
    if not all(sound):
        d["decision"] = "EVENT_LINEAGE_SOUNDNESS_FAIL"
    elif cpu_c > CPU_WALL * cpu_b:
        d["decision"] = "EVENT_LINEAGE_COST_WALL"
    elif not signal:
        d["decision"] = "EVENT_LINEAGE_NO_SIGNAL"
    else:
        d["decision"] = "EXTEND"
    return d


def soundness_gate(out):
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_state_object_event_pilot_v0.py", "-q",
                        "-p", "no:cacheprovider", "-k", "lineage or certificate"], cwd=ROOT, capture_output=True,
                       text=True)
    (out / "soundness_gate_pytest.txt").write_text(p.stdout + "\n" + p.stderr, encoding="utf-8")
    return p.returncode == 0


def run(what, out: Path):
    if what == "part_b_stage1":
        seal(out, SEALED_B, {"part": "B", "stage": 1, "reps": REPS, "plan": STAGE1})
        if not soundness_gate(out):
            log(out, "PART B soundness tests FAILED: campaign forbidden")
            (out / "decision.json").write_text(json.dumps({"decision": "EVENT_LINEAGE_SOUNDNESS_FAIL",
                                                           "reason": "unit soundness tests failed"}, indent=1))
            return
        log(out, "PART B soundness gate passed; stage 1")
        run_stage(out, STAGE1)
        d = decide_extension(out)
        (out / "decision.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        log(out, f"stage-1 decision: {d['decision']}")
    elif what == "part_b_stage2":
        d = json.loads((out / "decision.json").read_text(encoding="utf-8"))
        if d.get("decision") != "EXTEND":
            log(out, f"stage 2 not allowed: {d.get('decision')}")
            return
        from .campaign import git, lf_sha
        (out / "execution_seal_stage2.json").write_text(json.dumps(
            {"stage": 2, "plan": STAGE2, "stage1_decision": d, "head": git("rev-parse", "HEAD"),
             "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED_B)),
             "source_sha256_lf": {s: lf_sha(ROOT / s) for s in SEALED_B}}, indent=1), encoding="utf-8")
        log(out, "stage 2")
        run_stage(out, STAGE2)
        log(out, "stage 2 finished")
