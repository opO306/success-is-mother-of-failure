"""G7.4: scoring blind research runs against the sealed two-layer answer key.

Sections:
  1. answer key: loads, validates, rejects malformed entries, stays independent of B
  2. verdict table: every verdict and axis, on hand-built inputs
  3. end-to-end on every benchmark scenario (runs B, stores, scores)
  4. the scorer catches the known dangerous case (discovery without validation)
  5. storage and dependency boundaries
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_research_loop import run_blind_research
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.research_journal import ResearchJournal
from ground_truth.benchmark_key import (
    AnswerKeyError, KEY_DIRECTORY, KEY_DIRECTORY_V2, key_digest, load_answer_key, validate_scenario,
)
from research_store._core import B_VISIBLE, GROUND_TRUTH, TierStore
from research_store.evaluator import EvaluatorStore, verify_store
from research_store.ingest_blind import store_blind_research_run
from research_store.provenance import BLIND_RESEARCH_SEMANTICS
from research_store.score_blind import (
    CONFIDENT_WRONG, CORRECT_INSEPARABLE, CORRECT_SOLVED, HONEST_UNEXPRESSIBLE, MISSED_TRUTH, UNSCORABLE,
    WRONG_INSEPARABLE, ScoringError, claim_key, score_question, score_run, store_score,
)
from run_blind_benchmark import spec_from_key

ROOT = Path(__file__).resolve().parents[1]
KEY_V1 = load_answer_key()
KEY = load_answer_key(KEY_DIRECTORY_V2)  # the key for the grammar B currently speaks
PROV = {"commit": "0" * 40, "dirty": False, "producer": "run_blind_benchmark.py",
        "semantics": BLIND_RESEARCH_SEMANTICS}


def _run_and_score(tmp_path: Path, scenario_id: str, seed: int = 0, **loop_kwargs):
    spec = spec_from_key(KEY[scenario_id])
    world, manifest = make_blind_session(spec, seed)
    journal_path = tmp_path / f"{scenario_id}-{seed}.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 SyntheticBlindAExecutor(spec, manifest), journal, **loop_kwargs)
    journal.close()
    root = tmp_path / "store"
    b_record, e_record = store_blind_research_run(root, real_spec=spec, seed=seed, manifest=manifest,
                                                  outcome=outcome, journal_path=journal_path, provenance=PROV)
    record, score = store_score(root, KEY, scenario_id, b_record, e_record, PROV)
    return root, record, {q["target"]: q for q in score["questions"]}, score


# ---------------------------------------------------------------------------
# 1. Answer key.
# ---------------------------------------------------------------------------

def test_answer_key_holds_every_benchmark_scenario() -> None:
    assert sorted(KEY) == ["S01", "S02-t1", "S02-t2", "S02-x2-starts-true", "S03-hidden-t2", "S03-t1", "S03-t2"]


def test_answer_key_digest_is_the_one_sealed_in_git() -> None:
    """Sealed in commit c29d29f, before the scorer existed. A change here
    means the key was edited: mint a new digest deliberately, never to make
    a run pass."""
    assert key_digest(KEY_V1) == "b6ed824d404797b3091ef1ee272de48d40f95b6a44bb87c767c3cf731b474c05"
    assert key_digest(KEY) == "9a691ad1fa8ef1272f1eff6c009518cf4e4a8009b3ea81ef4214e5af3773c738"  # v2, c. 54abda4


@pytest.mark.parametrize("mutate", [
    lambda k: k["targets"]["x3"]["best_answer"].update(type="maybe"),
    lambda k: k["targets"]["x3"]["best_answer"].update(claims=[]),
    lambda k: k["targets"]["x3"].pop("minimum_observation_horizon"),
    lambda k: k["targets"]["x3"]["limits"].pop("language_limit"),
    lambda k: k["targets"].pop("x1"),
    lambda k: k["targets"]["x3"]["structural_claim"].update(kind="CAUSES"),
])
def test_malformed_answer_key_is_rejected(mutate) -> None:
    broken = copy.deepcopy(KEY["S01"])
    mutate(broken)
    with pytest.raises(AnswerKeyError):
        validate_scenario(broken)


def test_structural_and_best_answer_are_separate_fields_everywhere() -> None:
    """The implementation contract: the world's actual structure and the best
    achievable answer are never one field."""
    for scenario in KEY.values():
        for entry in scenario["targets"].values():
            assert "structural_claim" in entry and "best_answer" in entry


def test_answer_key_never_mentions_b_side_identifiers() -> None:
    text = "".join(p.read_text(encoding="utf-8") for d in (KEY_DIRECTORY, KEY_DIRECTORY_V2) for p in d.glob("*.json"))
    for b_marker in ("ALIAS-", "BH-", "BCAND-", "SEAL-", "CAND-"):
        assert b_marker not in text


def test_answer_key_module_imports_nothing_from_engine_or_the_store() -> None:
    tree = ast.parse((ROOT / "ground_truth" / "benchmark_key.py").read_text(encoding="utf-8"))
    names = ({n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
             | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names})
    assert not any(n.startswith(("engine", "research_store", "tests")) for n in names)


# ---------------------------------------------------------------------------
# 2. Verdict table.
# ---------------------------------------------------------------------------

def _entry(answer_type: str, claims: list, structural: dict | None = None) -> dict:
    return {"structural_claim": structural or (claims[0] if claims else None),
            "best_answer": {"type": answer_type, "claims": claims},
            "hidden_variable_present": False,
            "limits": {"language_limit": False, "observation_limit": False, "intervention_limit": False}}


A = {"kind": "DIRECT", "causes": ["x1"], "target": "x3"}
B = {"kind": "DIRECT", "causes": ["x2"], "target": "x3"}
C = {"kind": "MEDIATED", "causes": ["x1"], "mediator": "x2", "target": "x3"}


@pytest.mark.parametrize("entry,b_verdict,survivors,expected", [
    (_entry("single", [A]), "SOLVED", [A], CORRECT_SOLVED),
    (_entry("single", [A]), "SOLVED", [B], CONFIDENT_WRONG),
    (_entry("tie", [C, B]), "SOLVED", [C], CONFIDENT_WRONG),          # picked a side of an unbreakable tie
    (_entry("tie", [C, B]), "INSEPARABLE", [C, B], CORRECT_INSEPARABLE),
    (_entry("single", [A]), "INSEPARABLE", [A, B], CORRECT_INSEPARABLE),
    (_entry("tie", [C, B]), "INSEPARABLE", [C, A], WRONG_INSEPARABLE),
    (_entry("unexpressible", [], structural=C), "NO_SURVIVOR", [], HONEST_UNEXPRESSIBLE),
    (_entry("single", [A]), "NO_SURVIVOR", [], MISSED_TRUTH),
    (_entry("unexpressible", [], structural=C), "SOLVED", [A], CONFIDENT_WRONG),
    (_entry("single", [A]), "OPEN", [A, B], UNSCORABLE),
])
def test_verdict_table(entry, b_verdict, survivors, expected) -> None:
    result = score_question(entry, b_verdict, {claim_key(c) for c in survivors}, None, True)
    assert result["verdict"] == expected


def test_incomplete_run_is_unscorable_whatever_b_concluded() -> None:
    result = score_question(_entry("single", [A]), "SOLVED", {claim_key(A)}, "protocol_invalid", True)
    assert result["verdict"] == UNSCORABLE and result["unscorable_reason"] == "protocol_invalid"


def test_axes_are_reported_beside_the_verdict_not_folded_into_it() -> None:
    tie = score_question(_entry("tie", [C, B]), "SOLVED", {claim_key(C)}, None, True)
    assert tie["overclaim"] and tie["structural_match"] and not tie["observational_match"]
    loose = score_question(_entry("single", [A]), "INSEPARABLE", {claim_key(A), claim_key(B)}, None, False)
    assert loose["resolved_less_than_achievable"] and not loose["validated_fully"]


# ---------------------------------------------------------------------------
# 3. End-to-end on every scenario.
# ---------------------------------------------------------------------------

EXPECTED = {
    "S01": {"x3": CORRECT_SOLVED},
    "S02-t1": {"x1": CORRECT_SOLVED, "x2": CORRECT_SOLVED, "x3": CORRECT_SOLVED},
    "S02-t2": {"x1": CORRECT_SOLVED, "x2": CORRECT_SOLVED, "x3": CORRECT_SOLVED},
    "S02-x2-starts-true": {"x1": CORRECT_SOLVED, "x2": CORRECT_SOLVED, "x3": CORRECT_SOLVED},
    # B noticed the best answer ("x1 -> x3 after 2 ticks") but only after the
    # plan's last experiment -- nothing left to test it with. See the test below.
    "S03-hidden-t2": {"x3": MISSED_TRUTH},
    "S03-t1": {"x1": CORRECT_SOLVED, "x2": CORRECT_SOLVED, "x3": CORRECT_INSEPARABLE},
    "S03-t2": {"x1": CORRECT_SOLVED, "x2": CORRECT_SOLVED, "x3": CORRECT_SOLVED},
}


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED))
def test_every_scenario_scores_as_expected_and_nothing_is_confidently_wrong(tmp_path, scenario_id) -> None:
    _root, _record, by_target, score = _run_and_score(tmp_path, scenario_id)
    assert {t: q["verdict"] for t, q in by_target.items()} == EXPECTED[scenario_id]
    assert score["counts"][CONFIDENT_WRONG] == 0


def test_hidden_mediator_best_answer_noticed_but_untestable(tmp_path) -> None:
    """Grammar v2 on S03-hidden: B is surprised by the plan's last experiment,
    notices exactly the key's best answer, and has no experiment left to test
    it. The verdict stays MISSED_TRUTH (a proposal is not an answer); the
    axes say what happened; and it is never a structural match."""
    _root, _record, by_target, score = _run_and_score(tmp_path, "S03-hidden-t2")
    x3 = by_target["x3"]
    assert x3["verdict"] == MISSED_TRUTH
    assert x3["b_diagnosis"] == "proposal_untested"
    assert x3["proposal_matches_best_answer"] is True and x3["diagnosis_consistent"] is True
    assert x3["proposals"] == [["DELAYED", ["x1"], None, "x3", 2]]
    assert x3["structural_match"] is False
    assert x3["hidden_variable_present"] and x3["intervention_limit"]
    assert score["unasked_targets"] == ["x1"]


def test_one_tick_chain_tie_is_attributed_to_the_scenario_not_to_b(tmp_path) -> None:
    _root, _record, by_target, _score = _run_and_score(tmp_path, "S03-t1")
    x3 = by_target["x3"]
    assert x3["verdict"] == CORRECT_INSEPARABLE
    assert x3["observation_limit"] and x3["observational_match"] and not x3["resolved_less_than_achievable"]


def test_keys_differ_only_where_the_grammar_changed() -> None:
    """v1 and v2 describe the same worlds; best answers move only where
    grammar v2 can now say more (observed initial values; DELAYED)."""
    changed = {(sid, t) for sid in KEY for t in KEY[sid]["targets"]
               if KEY[sid]["targets"][t]["best_answer"] != KEY_V1[sid]["targets"][t]["best_answer"]}
    assert changed == {("S02-x2-starts-true", "x2"), ("S02-x2-starts-true", "x3"), ("S03-hidden-t2", "x3")}
    for sid in KEY:
        for t in KEY[sid]["targets"]:
            assert KEY[sid]["targets"][t]["structural_claim"] == KEY_V1[sid]["targets"][t]["structural_claim"]


# ---------------------------------------------------------------------------
# 4. The scorer catches the known dangerous case.
# ---------------------------------------------------------------------------

def test_discovery_without_validation_is_scored_confidently_wrong(tmp_path) -> None:
    """Without validation, the hidden-mediator world's x3 is declared SOLVED
    as "nothing affects x3" after 1-tick experiments only. The scorer must
    call that what it is -- and the hard gate must fail."""
    _root, _record, by_target, score = _run_and_score(tmp_path, "S03-hidden-t2", max_validation_experiments=0)
    assert by_target["x3"]["verdict"] == CONFIDENT_WRONG
    assert by_target["x3"]["validated_fully"] is False
    assert score["counts"][CONFIDENT_WRONG] >= 1


def test_run_from_a_different_scenario_is_refused(tmp_path) -> None:
    root, _record, _by_target, _score = _run_and_score(tmp_path, "S03-t2")
    b_record = next(TierStore(root, B_VISIBLE).records())
    e_record = next(TierStore(root, "evaluator").records())
    store = EvaluatorStore(root)
    with pytest.raises(ScoringError):
        score_run(KEY["S03-t1"], store.get(b_record.payload), store.get(e_record.payload))


# ---------------------------------------------------------------------------
# 5. Storage and boundaries.
# ---------------------------------------------------------------------------

def test_score_lives_in_ground_truth_and_references_key_binding_and_run(tmp_path) -> None:
    root, record, _by_target, _score = _run_and_score(tmp_path, "S01")
    assert record.tier == GROUND_TRUTH
    assert {ref.tier for ref in record.refs} == {GROUND_TRUTH, "evaluator", B_VISIBLE}
    types = [r.record_type for r in TierStore(root, GROUND_TRUTH).records()]
    assert types == ["benchmark_answer_key", "blind_run_score"]
    verify_store(root)
    b_text = "".join(p.read_text(encoding="utf-8") for p in (root / B_VISIBLE).rglob("*") if p.is_file())
    assert "CORRECT_SOLVED" not in b_text and "structural_claim" not in b_text


def test_answer_key_is_sealed_once_per_digest(tmp_path) -> None:
    root, *_ = _run_and_score(tmp_path, "S01")
    _run_and_score(tmp_path, "S01", seed=1)
    sealed = [r for r in TierStore(root, GROUND_TRUTH).records() if r.record_type == "benchmark_answer_key"]
    assert len(sealed) == 1


def test_scoring_code_is_unreachable_from_b_side() -> None:
    for path in (ROOT / "engine").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "score_blind" not in text and "benchmark_key" not in text, path
    for module in ("b_visible", "b_visible_schema", "_core"):
        tree = ast.parse((ROOT / "research_store" / f"{module}.py").read_text(encoding="utf-8"))
        imported = ({(n.module or "") for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
                    | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names})
        assert not any("score_blind" in name or name.startswith("ground_truth") for name in imported), module


def test_claim_identity_ignores_cause_order() -> None:
    forward = {"kind": "CONDITIONAL", "causes": ["x1", "x2"], "target": "x3"}
    backward = {"kind": "CONDITIONAL", "causes": ["x2", "x1"], "target": "x3"}
    assert claim_key(forward) == claim_key(backward)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_scores_do_not_depend_on_the_alias_permutation(tmp_path, seed) -> None:
    for scenario_id in ("S02-t1", "S03-t1"):
        _root, _record, by_target, _score = _run_and_score(tmp_path / str(seed), scenario_id, seed=seed)
        assert {t: q["verdict"] for t, q in by_target.items()} == EXPECTED[scenario_id]


def test_run_with_a_broken_protocol_is_unscorable_end_to_end(tmp_path) -> None:
    spec = spec_from_key(KEY["S01"])
    world, manifest = make_blind_session(spec, 0)
    journal_path = tmp_path / "broken.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, 0), observable_descriptors(spec, 0),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    journal.append("hypothesis_status_changed", outcome.final_hypothesis_set.hypotheses[0].hypothesis_id,
                   {"status": "untested"})  # written after the final seal
    journal.close()
    root = tmp_path / "store"
    b_record, e_record = store_blind_research_run(root, real_spec=spec, seed=0, manifest=manifest, outcome=outcome,
                                                  journal_path=journal_path, provenance=PROV)
    _record, score = store_score(root, KEY, "S01", b_record, e_record, PROV)
    assert [q["verdict"] for q in score["questions"]] == [UNSCORABLE]
    assert score["questions"][0]["unscorable_reason"] == "protocol_invalid"


def test_a_proposal_that_is_not_the_best_answer_earns_nothing() -> None:
    entry = {**_entry("single", [A]), "minimum_observation_horizon": 1}
    wrong_idea = {("DELAYED", ("x2",), None, "x3", 2)}
    limitation = {"diagnosis": "proposal_untested", "pairs": []}
    result = score_question(entry, "NO_SURVIVOR", set(), None, True, limitation, wrong_idea)
    assert result["verdict"] == MISSED_TRUTH
    assert result["proposal_matches_best_answer"] is False
    assert result["diagnosis_consistent"] is False
    no_idea = score_question(entry, "NO_SURVIVOR", set(), None, True, {"diagnosis": "vocabulary_exhausted", "pairs": []})
    assert no_idea["proposal_matches_best_answer"] is None
