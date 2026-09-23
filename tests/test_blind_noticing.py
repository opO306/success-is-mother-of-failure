"""G8: look first, surprise, notice -- and test noticed ideas only on new data.

Sections:
  1. observation-only first run: declared, never sealed or scored, sets initial values
  2. protocol: the audit catches an observation-only arm that is scored or declared late
  3. surprise: journaled exactly when a question loses its last live hypothesis
  4. noticing: finds the delayed pattern, tests it only on later experiments
  5. a noticed idea with nothing left to test it stays a proposal
  6. switches reproduce the grammar-v1 behaviour; boundaries
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_execution import BlindCheckpoint, BlindRun
from engine.deterministic.blind_hypothesis import DELAYED, NO_EFFECT, BlindCausalClaim
from engine.deterministic.blind_hypothesis_generator import BlindQuestion
from engine.deterministic.blind_noticing import notice_delayed_relations
from engine.deterministic.blind_protocol import audit_protocol
from engine.deterministic.blind_research_loop import NO_SURVIVOR, SOLVED, run_blind_research
from engine.deterministic.blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.research_journal import ResearchJournal, read_journal
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
from tests.test_deterministic_blind_hypothesis import FORBIDDEN_MODULES, _closure

V = ("x1", "x2", "x3")


def _spec(controls, observables, ticks, initial=None, world="WORLD-S03", revision="R-51E8B7") -> SyntheticWorldSpec:
    initial = initial or {}
    return SyntheticWorldSpec(world_id=world, world_revision=revision, variables=V,
                              initial_values=tuple((v, initial.get(v, False)) for v in V), clamps=(),
                              public_controls=controls, public_observables=observables, ticks=ticks)


HIDDEN_T2 = lambda: _spec(("x1",), ("x1", "x3"), 2)                   # noqa: E731
HIDDEN_T3 = lambda: _spec(("x1",), ("x1", "x3"), 3)                   # noqa: E731
HIDDEN_STARTS_TRUE = lambda: _spec(("x1",), ("x1", "x3"), 2, {"x2": True})  # noqa: E731
S02_X2_TRUE = lambda: _spec(("x1", "x2"), V, 1, {"x2": True}, "WORLD-S02", "R-A18D40")  # noqa: E731


def _run(tmp_path: Path, spec: SyntheticWorldSpec, seed: int = 0, **kwargs):
    world, manifest = make_blind_session(spec, seed)
    path = tmp_path / f"j-{seed}-{len(list(tmp_path.iterdir()))}.jsonl"
    journal = ResearchJournal.create(path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 SyntheticBlindAExecutor(spec, manifest), journal, **kwargs)
    journal.close()
    real = {alias: name for name, alias in manifest.variable_alias.items()}
    statements = {h.hypothesis_id: " ".join(real.get(t, t) for t in h.statement.split())
                  for h in outcome.final_hypothesis_set.hypotheses}
    return outcome, read_journal(path), path, manifest, statements


# ---------------------------------------------------------------------------
# 1. Look first.
# ---------------------------------------------------------------------------

def test_observation_only_run_comes_first_and_is_never_scored(tmp_path) -> None:
    outcome, entries, path, _m, _s = _run(tmp_path, S02_X2_TRUE())
    [arm] = outcome.observation_arm_ids
    assert entries[0].event_type == "observation_only_declared" and entries[0].record_id == arm
    assert entries[1].event_type == "execution_completed" and entries[1].record_id == arm
    for entry in entries:
        if entry.event_type in ("prediction_sealed", "result_compared", "experiment_candidate_ranked"):
            assert entry.payload.get("arm_id", entry.record_id) != arm
    assert arm not in outcome.executed_candidate_ids
    assert audit_protocol(path).valid


def test_initial_values_are_what_b_saw_at_tick_zero(tmp_path) -> None:
    outcome, _entries, _path, manifest, _s = _run(tmp_path, S02_X2_TRUE())
    seen = dict(outcome.initial_values)
    assert seen == {manifest.variable_alias["x1"]: False, manifest.variable_alias["x2"]: True,
                    manifest.variable_alias["x3"]: False}


def test_hidden_variables_get_no_observed_initial_value(tmp_path) -> None:
    outcome, _entries, _path, manifest, _s = _run(tmp_path, HIDDEN_STARTS_TRUE())
    assert manifest.variable_alias["x2"] not in dict(outcome.initial_values)


def test_looking_first_solves_what_the_false_prior_could_not(tmp_path) -> None:
    looked, *_ = _run(tmp_path, S02_X2_TRUE())
    assumed, *_ = _run(tmp_path, S02_X2_TRUE(), observe_first=False)
    assert {q.verdict for q in looked.questions} == {SOLVED}
    assert NO_SURVIVOR in {q.verdict for q in assumed.questions}


# ---------------------------------------------------------------------------
# 2. Protocol.
# ---------------------------------------------------------------------------

def _journal_with(tmp_path: Path, events, name: str = "p.jsonl") -> Path:
    path = tmp_path / name
    journal = ResearchJournal.create(path)
    for event_type, record_id, payload in events:
        journal.append(event_type, record_id, payload)
    journal.close()
    return path


def _codes(path: Path) -> set[str]:
    return set(audit_protocol(path).violation_codes)


def test_observation_only_arm_without_seal_is_allowed(tmp_path) -> None:
    path = _journal_with(tmp_path, [("observation_only_declared", "BOBS-1", {}),
                                    ("execution_completed", "BOBS-1", {})])
    assert "EXECUTION_WITHOUT_PRIOR_SEAL" not in _codes(path)


def test_observation_only_arm_that_gets_scored_is_a_violation(tmp_path) -> None:
    path = _journal_with(tmp_path, [("observation_only_declared", "BOBS-1", {}),
                                    ("execution_completed", "BOBS-1", {}),
                                    ("result_compared", "BOBS-1", {"held": {}})])
    assert "OBSERVATION_ONLY_SCORED" in _codes(path)
    path2 = _journal_with(tmp_path, [("observation_only_declared", "BOBS-2", {}),
                                     ("prediction_sealed", "SEAL-BOBS-2", {"arm_id": "BOBS-2"})], "p2.jsonl")
    assert "OBSERVATION_ONLY_SCORED" in _codes(path2)


def test_declaring_observation_only_after_running_is_a_violation(tmp_path) -> None:
    path = _journal_with(tmp_path, [("execution_completed", "BOBS-1", {}),
                                    ("observation_only_declared", "BOBS-1", {})])
    assert {"EXECUTION_WITHOUT_PRIOR_SEAL", "OBSERVATION_DECLARED_AFTER_EXECUTION"} <= _codes(path)


# ---------------------------------------------------------------------------
# 3. Surprise.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spec,surprises", [(S02_X2_TRUE, 0), (HIDDEN_T2, 1), (HIDDEN_STARTS_TRUE, 1)])
def test_surprise_is_journaled_exactly_when_a_question_runs_out_of_hypotheses(tmp_path, spec, surprises) -> None:
    outcome, entries, *_ = _run(tmp_path, spec())
    anomalies = [e for e in entries if e.event_type == "anomaly_recorded"]
    assert len(anomalies) == surprises
    for anomaly in anomalies:
        assert anomaly.payload["kind"] == "all_hypotheses_refuted"
        assert anomaly.payload["arm_id"] in outcome.executed_candidate_ids


# ---------------------------------------------------------------------------
# 4. Noticing, tested only on later experiments.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2])
def test_noticed_delay_is_tested_on_new_experiments_and_solves_the_question(tmp_path, seed) -> None:
    outcome, entries, path, _m, statements = _run(tmp_path, HIDDEN_T3(), seed=seed)
    [question] = outcome.questions
    assert question.verdict == SOLVED
    assert [statements[h] for h in question.surviving_hypothesis_ids] == ["x1 -> x3 after 2 ticks"]
    [noticed] = [e for e in entries if e.event_type == "hypothesis_noticed"]
    fitted_on = set(noticed.payload["derived_from"])
    hypothesis = next(h for h in outcome.final_hypothesis_set.hypotheses if h.hypothesis_id == noticed.record_id)
    tested_on = {ev.evidence_id for ev in hypothesis.evidence}
    assert tested_on and not tested_on & fitted_on          # never scored on the data it was fitted to
    after = {e.record_id for e in entries if e.event_type == "execution_completed" and e.sequence > noticed.sequence}
    assert tested_on == after
    assert "origin:noticed" in hypothesis.applicability_conditions
    assert audit_protocol(path).valid


def test_noticing_needs_a_change_the_pattern_explains() -> None:
    """Runs where the target never moves say nothing a NO_EFFECT claim does
    not; no delayed pattern is proposed from them."""
    world = BlindWorldDescriptor("ALIAS-00000000", ("ALIAS-0000000A", "ALIAS-0000000T"), ("ALIAS-000000CA",),
                                 ("ALIAS-000000OT",), ticks=3)
    controls = (BlindControlDescriptor("ALIAS-000000CA", "ALIAS-0000000A"),)
    observables = (BlindObservableDescriptor("ALIAS-000000OT", "ALIAS-0000000T"),)
    question = BlindQuestion("ALIAS-000000OT", "ALIAS-0000000T",
                             (BlindCausalClaim(NO_EFFECT, "ALIAS-0000000T"),
                              BlindCausalClaim(DELAYED, "ALIAS-0000000T", ("ALIAS-0000000A",), lag=3)))
    flat = BlindRun("ALIAS-00000000", tuple(BlindCheckpoint(t, (("ALIAS-000000OT", False),)) for t in range(4)))
    assert notice_delayed_relations(question, world, controls, observables, [({"ALIAS-0000000A": False}, flat)]) == ()
    moved = BlindRun("ALIAS-00000000", tuple(BlindCheckpoint(t, (("ALIAS-000000OT", t >= 2),)) for t in range(4)))
    found = notice_delayed_relations(question, world, controls, observables, [({"ALIAS-0000000A": True}, moved)])
    assert [(c.kind, c.lag) for c in found] == [(DELAYED, 2)]
    contradicted = [({"ALIAS-0000000A": True}, moved), ({"ALIAS-0000000A": False}, moved)]
    assert notice_delayed_relations(question, world, controls, observables, contradicted) == ()


# ---------------------------------------------------------------------------
# 5. Nothing left to test it with.
# ---------------------------------------------------------------------------

def test_noticed_idea_with_no_experiment_left_is_a_proposal_not_an_answer(tmp_path) -> None:
    outcome, _entries, _path, _m, statements = _run(tmp_path, HIDDEN_T2())
    [question] = outcome.questions
    assert question.verdict == NO_SURVIVOR
    assert [statements[h] for h in question.proposed_hypothesis_ids] == ["x1 -> x3 after 2 ticks"]
    assert question.limitation["diagnosis"] == "proposal_untested"
    [proposal] = [h for h in outcome.final_hypothesis_set.hypotheses if h.hypothesis_id in question.proposed_hypothesis_ids]
    assert proposal.status == "untested" and proposal.evidence == ()
    assert proposal.hypothesis_id in outcome.final_seal.unresolved_hypothesis_ids


def test_world_outside_grammar_v2_notices_nothing_and_ends_honestly(tmp_path) -> None:
    outcome, entries, *_ = _run(tmp_path, HIDDEN_STARTS_TRUE())
    assert [q.verdict for q in outcome.questions] == [NO_SURVIVOR]
    assert not any(e.event_type == "hypothesis_noticed" for e in entries)


# ---------------------------------------------------------------------------
# 6. Switches and boundaries.
# ---------------------------------------------------------------------------

def test_without_noticing_the_surprise_simply_ends_the_question(tmp_path) -> None:
    outcome, entries, *_ = _run(tmp_path, HIDDEN_T3(), notice=False)
    assert [q.verdict for q in outcome.questions] == [NO_SURVIVOR]
    assert any(e.event_type == "anomaly_recorded" for e in entries)
    assert not any(e.event_type == "hypothesis_noticed" for e in entries)


def test_noticing_module_cannot_reach_evaluator_or_answer_modules() -> None:
    closure = _closure("blind_noticing")
    assert not closure & FORBIDDEN_MODULES and "ground_truth" not in closure
    assert "blind_noticing" in _closure("blind_research_loop")


def test_journal_of_a_noticing_run_carries_no_real_identity(tmp_path) -> None:
    spec = HIDDEN_T3()
    _outcome, _entries, path, _m, _s = _run(tmp_path, spec)
    text = path.read_text(encoding="utf-8")
    for secret in ("WORLD-S03", "R-51E8B7", spec.digest, '"x1"', '"x2"', '"x3"'):
        assert secret not in text
