"""Evaluator side: find where B's language loses information.

A *language gap* is two situations that really differ -- different actual
structure behind the same observable, per the sealed answer key -- that B
ends up recording identically: same verdict, same surviving claims, same
self-diagnosis. B cannot tell them apart, not because it reasoned badly but
because its record of them is the same sentence. Each gap is evidence that
the language needs a new word or structure, with the key's declared limits
attached as a hint about which.

Only the answer layer is checked here. Observations themselves are not
lossy at the recording step: every executed run is journaled in full
(`observation_recorded`, all ticks, every public observable) -- a property
tested directly in `tests/test_language_gaps.py` by translating the
journaled observations back and comparing with A's real run.

Reads scores (ground_truth tier) and the key; writes a `language_gap_report`
to the ground_truth tier. Contains real names and structures -- never
b_visible.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from ._core import GROUND_TRUTH, StoreRecord
from .evaluator import EvaluatorStore
from .score_blind import SCORE_SEMANTICS, claim_key

SCHEMA_VERSION = 1


def _b_record(question: Mapping[str, Any]) -> tuple:
    """What B wrote down about one question, in real-name terms."""
    survivors = tuple(tuple(tuple(x) if isinstance(x, list) else x for x in claim) for claim in question["survivors"])
    return (question["target"], question["b_verdict"], survivors, question.get("b_diagnosis"))


def find_language_gaps(scores: Iterable[Mapping[str, Any]], key: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Group every scored question by B's record of it; a group whose cases
    have more than one actual structure is a gap."""
    groups: dict[tuple, dict[tuple, dict[str, Any]]] = {}
    for score in scores:
        scenario = key[score["scenario_id"]]
        for question in score["questions"]:
            if question["verdict"] == "UNSCORABLE":
                continue
            entry = scenario["targets"][question["target"]]
            structure = claim_key(entry["structural_claim"]) if entry.get("structural_claim") else None
            case_key = (score["scenario_id"], question["target"])
            groups.setdefault(_b_record(question), {})[case_key] = {
                "scenario_id": score["scenario_id"], "target": question["target"],
                "structural_claim": entry.get("structural_claim"),
                "structure_key": structure,
                "hidden_variable_present": entry["hidden_variable_present"],
                "limits": dict(entry["limits"]),
            }
    gaps = []
    for record, cases in sorted(groups.items(), key=lambda item: repr(item[0])):
        structures = {case["structure_key"] for case in cases.values()}
        if len(structures) < 2:
            continue
        target, verdict, survivors, diagnosis = record
        gaps.append({
            "b_record": {"target": target, "b_verdict": verdict, "survivors": [list(s) for s in survivors],
                         "b_diagnosis": diagnosis},
            "distinct_structures": len(structures),
            "cases": [{k: v for k, v in case.items() if k != "structure_key"}
                      for _key, case in sorted(cases.items())],
        })
    return gaps


def store_language_gap_report(root: Path, key: Mapping[str, Any], key_digest: str,
                              provenance: Mapping[str, Any]) -> tuple[StoreRecord, list[dict[str, Any]]]:
    """Recompute gaps over every stored score for `key_digest` and record them."""
    store = EvaluatorStore(root)
    scores = [store.get(r.payload) for r in store.records(GROUND_TRUTH, "blind_run_score", semantics=SCORE_SEMANTICS)
              if r.tags.get("key_digest") == key_digest]
    gaps = find_language_gaps(scores, key)
    ref = store.put(GROUND_TRUTH, {"gaps": gaps, "key_digest": key_digest, "scores_considered": len(scores)})
    record = store.record(GROUND_TRUTH, "language_gap_report", SCHEMA_VERSION,
                          {**provenance, "semantics": SCORE_SEMANTICS},
                          {"key_digest": key_digest, "gap_count": str(len(gaps))}, ref)
    return record, gaps
