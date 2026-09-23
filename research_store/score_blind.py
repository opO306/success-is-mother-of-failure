"""G7.4: score a stored blind research run against the sealed answer key.

Evaluator side. Reads plain data only -- the b_visible payload (B's outcome
and final hypotheses), the evaluator binding (alias<->real mapping, real
spec), and the answer key (`ground_truth.benchmark_key`) -- and writes to
the ground_truth tier. Never imported by `engine` or by `research_store.b_visible*`.

Per question, one verdict relative to the key's *best achievable answer*
(not the structural truth -- B cannot be faulted for what its interface
cannot reveal):

    group            verdict                meaning
    SOLVED_SUCCESS   CORRECT_SOLVED         narrowed to one claim, and it is the best answer
    HONEST_SUCCESS   CORRECT_INSEPARABLE    a tie that contains every best-answer claim
                     HONEST_UNEXPRESSIBLE   "nothing fits", and truly nothing statable fits
    FAILURE          CONFIDENT_WRONG        narrowed to one claim that is not the best answer
                                            (including picking one side of an unbreakable tie)
                     MISSED_TRUTH           "nothing fits", but a statable claim did fit
                     WRONG_INSEPARABLE      a tie missing a best-answer claim
    UNSCORED         UNSCORABLE             run incomplete, protocol invalid, or question OPEN

Separate axes, never folded into the verdict:

    structural_match        B's answer is exactly the world's actual structure
    observational_match     B's answer is exactly the best achievable answer
    hidden_variable_present / language_limit / observation_limit /
    intervention_limit      copied from the key -- why the best answer is what it is
    resolved_less_than_achievable   B kept more claims than the best answer needs
    overclaim               B declared SOLVED where the best answer is a tie
    validated_fully         from B's outcome

The hard gate is CONFIDENT_WRONG == 0 -- but it is not a success criterion
on its own: a B that always said "nothing fits" would pass it. Counts per
verdict are always reported in full, never collapsed into one accuracy.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from ground_truth.benchmark_key import key_digest

from ._core import B_VISIBLE, EVALUATOR, GROUND_TRUTH, ObjectRef, StoreRecord, TierStore
from .evaluator import EvaluatorStore

SCORE_SEMANTICS = "blind-score/g7.4/two-layer-v1"
SCHEMA_VERSION = 1

CORRECT_SOLVED = "CORRECT_SOLVED"
CORRECT_INSEPARABLE = "CORRECT_INSEPARABLE"
HONEST_UNEXPRESSIBLE = "HONEST_UNEXPRESSIBLE"
CONFIDENT_WRONG = "CONFIDENT_WRONG"
MISSED_TRUTH = "MISSED_TRUTH"
WRONG_INSEPARABLE = "WRONG_INSEPARABLE"
UNSCORABLE = "UNSCORABLE"

GROUP_OF = {
    CORRECT_SOLVED: "SOLVED_SUCCESS",
    CORRECT_INSEPARABLE: "HONEST_SUCCESS", HONEST_UNEXPRESSIBLE: "HONEST_SUCCESS",
    CONFIDENT_WRONG: "FAILURE", MISSED_TRUTH: "FAILURE", WRONG_INSEPARABLE: "FAILURE",
    UNSCORABLE: "UNSCORED",
}
VERDICTS = tuple(GROUP_OF)

_ALIAS = r"ALIAS-[0-9A-F]{8}"
_PATTERNS = (
    ("NO_EFFECT", re.compile(rf"^no controllable variable affects (?P<t>{_ALIAS})$")),
    ("INVERTED", re.compile(rf"^NOT (?P<c>{_ALIAS}) -> (?P<t>{_ALIAS})$")),
    ("CONDITIONAL", re.compile(rf"^(?P<c>{_ALIAS}) AND (?P<g>{_ALIAS}) -> (?P<t>{_ALIAS})$")),
    ("DISJUNCTIVE", re.compile(rf"^(?P<c>{_ALIAS}) OR (?P<g>{_ALIAS}) -> (?P<t>{_ALIAS})$")),
    ("MEDIATED", re.compile(rf"^(?P<c>{_ALIAS}) -> (?P<m>{_ALIAS}) -> (?P<t>{_ALIAS})$")),
    ("DIRECT", re.compile(rf"^(?P<c>{_ALIAS}) -> (?P<t>{_ALIAS})$")),
)


class ScoringError(ValueError):
    """The run and the answer key do not describe the same scenario, or a
    statement cannot be read -- a harness defect, never a B verdict."""


def claim_key(claim: Mapping[str, Any]) -> tuple:
    """Order-free identity of a claim in real-name terms."""
    return (claim["kind"], tuple(sorted(claim["causes"])), claim.get("mediator"), claim["target"])


def parse_statement(statement: str, real_of: Mapping[str, str]) -> tuple:
    """B's alias statement -> claim_key in real names."""
    for kind, pattern in _PATTERNS:
        match = pattern.match(statement)
        if match:
            groups = match.groupdict()
            causes = [real_of[groups[g]] for g in ("c", "g") if groups.get(g)]
            mediator = real_of[groups["m"]] if groups.get("m") else None
            return (kind, tuple(sorted(causes)), mediator, real_of[groups["t"]])
    raise ScoringError("unreadable hypothesis statement")


def _check_same_scenario(scenario: Mapping[str, Any], binding: Mapping[str, Any]) -> None:
    world, spec = scenario["world"], binding["real_spec"]
    actual = {
        "world_id": spec["world_id"], "world_revision": spec["world_revision"],
        "variables": sorted(spec["variables"]), "initial_values": dict(spec["initial_values"]),
        "public_controls": sorted(spec["public_controls"]),
        "public_observables": sorted(spec["public_observables"]), "ticks": spec["ticks"],
    }
    expected = {**world, "variables": sorted(world["variables"]),
                "public_controls": sorted(world["public_controls"]),
                "public_observables": sorted(world["public_observables"])}
    if actual != expected:
        raise ScoringError(f"run does not match scenario {scenario['scenario_id']}")


def score_question(entry: Mapping[str, Any], b_verdict: str, survivors: set[tuple],
                   unscorable_reason: str | None, validated_fully: bool) -> dict[str, Any]:
    answer = entry["best_answer"]
    best = {claim_key(c) for c in answer.get("claims", [])}
    structural = claim_key(entry["structural_claim"]) if entry.get("structural_claim") else None

    if unscorable_reason is not None or b_verdict == "OPEN":
        verdict = UNSCORABLE
    elif b_verdict == "SOLVED":
        verdict = CORRECT_SOLVED if answer["type"] == "single" and survivors == best else CONFIDENT_WRONG
    elif b_verdict == "INSEPARABLE":
        verdict = CORRECT_INSEPARABLE if best and best <= survivors else WRONG_INSEPARABLE
    elif b_verdict == "NO_SURVIVOR":
        verdict = HONEST_UNEXPRESSIBLE if answer["type"] == "unexpressible" else MISSED_TRUTH
    else:
        raise ScoringError("unknown B verdict")

    return {
        "verdict": verdict, "group": GROUP_OF[verdict], "b_verdict": b_verdict,
        "unscorable_reason": unscorable_reason if verdict == UNSCORABLE else None,
        "structural_match": structural is not None and survivors == {structural},
        "observational_match": survivors == best,
        "hidden_variable_present": entry["hidden_variable_present"],
        **{name: entry["limits"][name] for name in ("language_limit", "observation_limit", "intervention_limit")},
        "resolved_less_than_achievable": b_verdict == "INSEPARABLE" and bool(best) and best < survivors,
        "overclaim": b_verdict == "SOLVED" and answer["type"] == "tie",
        "validated_fully": validated_fully,
        "survivors": sorted([list(map(_plain, s)) for s in survivors]),
        "best_answer": answer["type"],
    }


def _plain(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value


def score_run(scenario: Mapping[str, Any], b_payload: Mapping[str, Any],
              binding: Mapping[str, Any]) -> dict[str, Any]:
    _check_same_scenario(scenario, binding)
    real_of = {alias: real for real, alias in binding["variable_alias"].items()}
    real_observable = {alias: real for real, alias in binding["observable_alias"].items()}
    outcome = b_payload["outcome"]
    statements = {h["hypothesis_id"]: h["statement"] for h in b_payload["final_hypothesis_set"]["hypotheses"]}
    protocol_valid = b_payload["protocol_audit"]["valid"]
    run_reason = None
    if not protocol_valid:
        run_reason = "protocol_invalid"
    elif outcome["termination"] != "COMPLETE":
        run_reason = f"termination_{outcome['termination'].lower()}"

    questions, asked = [], set()
    for question in outcome["questions"]:
        target = real_observable[question["target_observable_id"]]
        asked.add(target)
        survivors = {parse_statement(statements[hid], real_of) for hid in question["surviving_hypothesis_ids"]}
        result = score_question(scenario["targets"][target], question["verdict"], survivors, run_reason,
                                outcome["validated_fully"])
        questions.append({"target": target, **result})
    counts = {verdict: sum(1 for q in questions if q["verdict"] == verdict) for verdict in VERDICTS}
    return {"scenario_id": scenario["scenario_id"], "questions": sorted(questions, key=lambda q: q["target"]),
            "unasked_targets": sorted(set(scenario["targets"]) - asked), "counts": counts}


def seal_answer_key(root: Path, key: Mapping[str, Any], provenance: Mapping[str, Any]) -> ObjectRef:
    """Store the answer key in the ground_truth tier once per key digest."""
    digest = key_digest(key)
    store = EvaluatorStore(root)
    ref = store.put(GROUND_TRUTH, {"answer_key": dict(key), "key_digest": digest})
    if not any(r.tags.get("key_digest") == digest for r in TierStore(root, GROUND_TRUTH).records()
               if r.record_type == "benchmark_answer_key"):
        store.record(GROUND_TRUTH, "benchmark_answer_key", SCHEMA_VERSION,
                     {**provenance, "semantics": SCORE_SEMANTICS}, {"key_digest": digest}, ref)
    return ref


def store_score(root: Path, key: Mapping[str, Any], scenario_id: str, b_record: StoreRecord,
                e_record: StoreRecord, provenance: Mapping[str, Any]) -> tuple[StoreRecord, dict[str, Any]]:
    """Score one stored run and write the result to the ground_truth tier,
    referencing the sealed key, the evaluator binding and B's payload."""
    key_ref = seal_answer_key(root, key, provenance)
    if b_record.tier != B_VISIBLE or e_record.tier != EVALUATOR:
        raise ScoringError("expected a b_visible run record and its evaluator binding")
    store = EvaluatorStore(root)
    b_payload = store.get(b_record.payload)
    binding = store.get(e_record.payload)
    if binding.get("b_visible_record_digest") != b_record.record_digest:
        raise ScoringError("evaluator binding does not belong to this b_visible record")
    score = score_run(key[scenario_id], b_payload, binding)
    score = {**score, "key_digest": key_digest(key), "b_visible_record_digest": b_record.record_digest,
             "evaluator_record_digest": e_record.record_digest}
    ref = store.put(GROUND_TRUTH, score)
    tags = {"scenario_id": scenario_id, "key_digest": key_digest(key),
            "verdicts": ",".join(q["verdict"] for q in score["questions"])}
    record = store.record(GROUND_TRUTH, "blind_run_score", SCHEMA_VERSION,
                          {**provenance, "semantics": SCORE_SEMANTICS}, tags, ref,
                          refs=(key_ref, e_record.payload, b_record.payload))
    return record, score
