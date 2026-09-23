"""Evidence links, B's own limitation diagnosis, and language-gap detection.

Sections:
  1. every final hypothesis carries evidence that resolves into the journal
  2. B's limitation diagnosis: computed from its own claims, graded by the key
  3. observations are recorded without loss (journal vs A's real run)
  4. language gaps: same B record, different real structure
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_execution import BlindCandidateSpec
from engine.deterministic.blind_hypothesis import DIRECT, NO_EFFECT, BlindCausalClaim
from engine.deterministic.blind_hypothesis_generator import BlindQuestion
from engine.deterministic.blind_limitations import (
    BUDGET_EXHAUSTED, NONE, NOT_DIAGNOSABLE, OBSERVATION_HORIZON, VOCABULARY_EXHAUSTED, assess_limitation,
)
from engine.deterministic.blind_prediction_materializer import BlindExperimentPlan
from engine.deterministic.blind_research_loop import run_blind_research
from engine.deterministic.blind_session import BlindControlDescriptor, BlindWorldDescriptor
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor, _resolve_real_spec
from engine.deterministic.exploration_space import ExplorationCandidate
from engine.deterministic.research_journal import ResearchJournal, read_journal
from engine.deterministic.synthetic_executor import SyntheticAExecutor
from research_store._core import B_VISIBLE, GROUND_TRUTH
from research_store.evaluator import verify_store
from research_store.language_gaps import find_language_gaps, store_language_gap_report
from research_store.score_blind import score_question
from ground_truth.benchmark_key import key_digest
from run_blind_benchmark import spec_from_key
from tests.test_blind_scoring import KEY, PROV, _entry, _run_and_score
from tests.test_deterministic_blind_hypothesis import FORBIDDEN_MODULES, _closure


def _loop(tmp_path: Path, scenario_id: str, seed: int = 0, **kwargs):
    spec = spec_from_key(KEY[scenario_id])
    world, manifest = make_blind_session(spec, seed)
    path = tmp_path / f"{scenario_id}.jsonl"
    journal = ResearchJournal.create(path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 SyntheticBlindAExecutor(spec, manifest), journal, **kwargs)
    journal.close()
    return spec, manifest, outcome, read_journal(path)


# ---------------------------------------------------------------------------
# 1. Evidence links.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ["S02-t1", "S03-t1", "S02-x2-starts-true"])
def test_every_final_hypothesis_carries_evidence_that_resolves_into_the_journal(tmp_path, scenario_id) -> None:
    _spec, _manifest, outcome, entries = _loop(tmp_path, scenario_id)
    compared = {e.record_digest: e for e in entries if e.event_type == "result_compared"}
    order = list(outcome.executed_candidate_ids)
    for hypothesis in outcome.final_hypothesis_set.hypotheses:
        assert hypothesis.evidence, hypothesis.hypothesis_id
        arms = [ev.evidence_id for ev in hypothesis.evidence]
        assert arms == order[:len(arms)]  # tested in every experiment while alive, in order
        for ev in hypothesis.evidence:
            entry = compared[ev.source_digest]
            assert entry.record_id == ev.evidence_id
            assert entry.payload["held"][hypothesis.hypothesis_id] == (ev.relation == "supports")
        relations = [ev.relation for ev in hypothesis.evidence]
        if hypothesis.status == "contradicted_in_domain":
            assert relations[-1] == "refutes" and relations.count("refutes") == 1
        else:
            assert set(relations) == {"supports"} and len(relations) == len(order)


def test_survivors_are_supported_never_confirmed(tmp_path) -> None:
    _spec, _manifest, outcome, _entries = _loop(tmp_path, "S03-t2")
    relations = {ev.relation for h in outcome.final_hypothesis_set.hypotheses for ev in h.evidence}
    assert relations <= {"supports", "refutes"}
    assert "confirmed" not in {h.status for h in outcome.final_hypothesis_set.hypotheses}


# ---------------------------------------------------------------------------
# 2. B's own limitation diagnosis.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id,target,expected", [
    ("S03-t1", "x3", OBSERVATION_HORIZON),
    ("S03-t1", "x2", NONE),
    ("S02-x2-starts-true", "x3", VOCABULARY_EXHAUSTED),
    ("S03-hidden-t2", "x3", VOCABULARY_EXHAUSTED),
])
def test_b_diagnoses_its_own_stopping_point(tmp_path, scenario_id, target, expected) -> None:
    _spec, manifest, outcome, entries = _loop(tmp_path, scenario_id)
    [question] = [q for q in outcome.questions if q.target_observable_id == manifest.observable_alias[target]]
    assert question.limitation["diagnosis"] == expected
    assessed = [e for e in entries if e.event_type == "limitation_assessed"]
    assert len(assessed) == len(outcome.questions)
    assert entries[-1].event_type == "final_discovery_sealed"


def test_one_tick_chain_tie_would_split_at_exactly_two_ticks(tmp_path) -> None:
    _spec, manifest, outcome, _entries = _loop(tmp_path, "S03-t1")
    [question] = [q for q in outcome.questions if q.target_observable_id == manifest.observable_alias["x3"]]
    assert [p["separable_at_horizon"] for p in question.limitation["pairs"]] == [2]


def test_budget_stop_is_diagnosed_as_budget(tmp_path) -> None:
    _spec, _manifest, outcome, _entries = _loop(tmp_path, "S02-t1", max_experiments=1)
    assert BUDGET_EXHAUSTED in {q.limitation["diagnosis"] for q in outcome.questions}


def test_tie_that_more_time_cannot_split_is_not_diagnosable() -> None:
    """Two claims differing only in a cause B never pins in its plan agree
    at every horizon: B must say it cannot diagnose, not guess 'time'."""
    world = BlindWorldDescriptor("ALIAS-00000000", ("ALIAS-0000000A", "ALIAS-0000000B", "ALIAS-0000000C"),
                                 ("ALIAS-000000C1", "ALIAS-000000C2"), ("ALIAS-000000D0",), ticks=1)
    controls = (BlindControlDescriptor("ALIAS-000000C1", "ALIAS-0000000A"),
                BlindControlDescriptor("ALIAS-000000C2", "ALIAS-0000000B"))
    direct = BlindCausalClaim(DIRECT, "ALIAS-0000000C", ("ALIAS-0000000A",))
    null = BlindCausalClaim(NO_EFFECT, "ALIAS-0000000C")
    question = BlindQuestion("ALIAS-000000D0", "ALIAS-0000000C", (direct, null))
    only_b = ExplorationCandidate("BCAND-0000000000000001", "BPLAN-0000000000000001", (("ALIAS-000000C2", 1),))
    plan = BlindExperimentPlan("BPLAN-0000000000000001", (only_b,), {
        only_b.candidate_id: BlindCandidateSpec(world.alias_world_id, only_b.candidate_id, only_b.control_values, 1)})
    result = assess_limitation(question, "INSEPARABLE", ((direct.claim_id, null.claim_id),), world, controls, plan)
    assert result.diagnosis == NOT_DIAGNOSABLE
    assert result.pairs[0].separable_at_horizon is None


def test_diagnosis_is_graded_by_the_key_on_every_scenario(tmp_path) -> None:
    for scenario_id in sorted(KEY):
        _root, _record, by_target, _score = _run_and_score(tmp_path / scenario_id, scenario_id)
        for target, question in by_target.items():
            assert question["diagnosis_consistent"] is True, (scenario_id, target)


def test_a_wrong_diagnosis_is_graded_inconsistent() -> None:
    entry = {**_entry("tie", [{"kind": "DIRECT", "causes": ["x1"], "target": "x3"},
                             {"kind": "DIRECT", "causes": ["x2"], "target": "x3"}]),
             "minimum_observation_horizon": 2}
    entry["limits"] = {**entry["limits"], "observation_limit": True}
    wrong = {"diagnosis": NOT_DIAGNOSABLE, "pairs": [{"hypothesis_ids": ["a", "b"], "separable_at_horizon": None}]}
    survivors = {("DIRECT", ("x1",), None, "x3"), ("DIRECT", ("x2",), None, "x3")}
    assert score_question(entry, "INSEPARABLE", survivors, None, True, wrong)["diagnosis_consistent"] is False
    late = {"diagnosis": OBSERVATION_HORIZON, "pairs": [{"hypothesis_ids": ["a", "b"], "separable_at_horizon": 3}]}
    assert score_question(entry, "INSEPARABLE", survivors, None, True, late)["diagnosis_consistent"] is False


def test_limitation_module_cannot_reach_the_answer_key() -> None:
    closure = _closure("blind_limitations")
    assert not closure & FORBIDDEN_MODULES
    assert "ground_truth" not in closure and "benchmark_key" not in closure
    assert "blind_limitations" in _closure("blind_research_loop")


# ---------------------------------------------------------------------------
# 3. Observations are recorded without loss.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ["S03-t2", "S03-hidden-t2", "S02-x2-starts-true"])
def test_journaled_observations_translate_back_to_a_s_real_run_exactly(tmp_path, scenario_id) -> None:
    """The recording step loses nothing: every journaled observation, mapped
    back to real names, equals A's own run of the same experiment -- every
    tick, every public observable."""
    from engine.deterministic.blind_prediction_materializer import BlindPredictionMaterializer
    spec, manifest, outcome, entries = _loop(tmp_path, scenario_id)
    world, _ = make_blind_session(spec, 0)
    plan = BlindPredictionMaterializer().plan(world, control_descriptors(spec, 0), observable_descriptors(spec, 0))
    real_of = {alias: real for real, alias in manifest.observable_alias.items()}
    observed = {e.record_id: e.payload["run"] for e in entries if e.event_type == "observation_recorded"}
    assert sorted(observed) == sorted(outcome.executed_candidate_ids)
    for candidate_id, run in observed.items():
        blind_spec = plan.compiled_specs[candidate_id]
        real_run = SyntheticAExecutor().execute(_resolve_real_spec(spec, manifest, blind_spec)).run
        translated = [(c["tick"], sorted((real_of[k], v) for k, v in c["observables"])) for c in run["checkpoints"]]
        real = [(c.tick, sorted(c.values)) for c in real_run.checkpoints]
        assert translated == real, candidate_id


# ---------------------------------------------------------------------------
# 4. Language gaps.
# ---------------------------------------------------------------------------

def _all_scores(tmp_path: Path):
    return [_run_and_score(tmp_path / sid, sid)[3] for sid in sorted(KEY)]


def test_benchmark_has_exactly_one_language_gap_and_it_is_the_expected_one(tmp_path) -> None:
    gaps = find_language_gaps(_all_scores(tmp_path), KEY)
    assert len(gaps) == 1
    [gap] = gaps
    assert gap["b_record"] == {"target": "x3", "b_verdict": "NO_SURVIVOR", "survivors": [],
                               "b_diagnosis": "vocabulary_exhausted"}
    assert [(c["scenario_id"], c["structural_claim"]["kind"]) for c in gap["cases"]] == [
        ("S02-x2-starts-true", "CONDITIONAL"), ("S03-hidden-t2", "MEDIATED")]
    assert [c["hidden_variable_present"] for c in gap["cases"]] == [False, True]


def test_same_structure_recorded_the_same_way_is_not_a_gap(tmp_path) -> None:
    scores = [_run_and_score(tmp_path / sid, sid)[3] for sid in ("S02-t1", "S02-t2")]
    assert find_language_gaps(scores, KEY) == []


def test_unscorable_questions_are_left_out(tmp_path) -> None:
    scores = _all_scores(tmp_path)
    for score in scores:
        for question in score["questions"]:
            question["verdict"] = "UNSCORABLE"
    assert find_language_gaps(scores, KEY) == []


def test_gap_report_is_stored_on_the_evaluator_side_only(tmp_path) -> None:
    root = tmp_path / "store"
    for sid in sorted(KEY):
        spec = spec_from_key(KEY[sid])
        world, manifest = make_blind_session(spec, 0)
        path = tmp_path / f"{sid}.jsonl"
        journal = ResearchJournal.create(path)
        outcome = run_blind_research(world, control_descriptors(spec, 0), observable_descriptors(spec, 0),
                                     SyntheticBlindAExecutor(spec, manifest), journal)
        journal.close()
        from research_store.ingest_blind import store_blind_research_run
        from research_store.score_blind import store_score
        b_record, e_record = store_blind_research_run(root, real_spec=spec, seed=0, manifest=manifest,
                                                      outcome=outcome, journal_path=path, provenance=PROV)
        store_score(root, KEY, sid, b_record, e_record, PROV)
    record, gaps = store_language_gap_report(root, KEY, key_digest(KEY), PROV)
    assert record.tier == GROUND_TRUTH and record.tags["gap_count"] == "1" and len(gaps) == 1
    verify_store(root)
    b_text = "".join(p.read_text(encoding="utf-8") for p in (root / B_VISIBLE).rglob("*") if p.is_file())
    assert "language_gap" not in b_text
