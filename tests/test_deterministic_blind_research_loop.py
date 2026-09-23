"""G7.3c: the autonomous blind research loop.

Sections:
  1. identifiable worlds end SOLVED on the real structure, by B's own choices
  2. S03 limited to 1 tick ends INSEPARABLE -- never a forced pick
  3. a world outside the vocabulary ends NO_SURVIVOR -- and why validation
     is required for that (discovery alone gives a confident wrong answer)
  4. efficiency: G6d ranking never needs more discovery experiments than a
     score-blind selector, and fewer on some alias seed (measured, pinned)
  5. budget stop, harness failure, horizon-lying executor, physical A refusal
  6. protocol: seal-before-execute, final seal terminal, audit passes
  7. statuses, determinism, alias robustness, leakage, dependency closure

The evaluator side (real spec, manifest, real names) appears only in the
harness helpers here -- to build the executor and to translate B's answer
back for checking. `run_blind_research` never receives any of it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_execution import BlindCheckpoint, BlindRun
from engine.deterministic.blind_prediction_materializer import (
    BlindExperimentPlan, observation_horizon,
)
from engine.deterministic.blind_protocol import audit_final_hypothesis_digest, audit_protocol
import engine.deterministic.blind_research_loop as loop_module
from engine.deterministic.blind_research_loop import (
    COMPLETE, HARNESS_FAILURE, INSEPARABLE, LIMIT_REACHED, NO_SURVIVOR, OPEN, SOLVED, run_blind_research,
)
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.causal_executor import ExecutionResult, RealCausalAExecutor
from engine.deterministic.research_journal import ResearchJournal, read_journal
from engine.deterministic.research_world import WorldCompatibilityError
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
from tests.test_deterministic_blind_hypothesis import FORBIDDEN_MODULES, _closure

V = ("x1", "x2", "x3")


def _spec(world_id, revision, variables, controls, observables, ticks, initial=None) -> SyntheticWorldSpec:
    initial = initial or {}
    return SyntheticWorldSpec(world_id=world_id, world_revision=revision, variables=variables,
                              initial_values=tuple((v, initial.get(v, False)) for v in variables), clamps=(),
                              public_controls=controls, public_observables=observables, ticks=ticks)


def _s01():
    return _spec("WORLD-S01", "R-7F93C2", ("x1", "x3"), ("x1",), ("x1", "x3"), 1)


def _s02(ticks=1):
    return _spec("WORLD-S02", "R-A18D40", V, ("x1", "x2"), V, ticks)


def _s03(ticks=2):
    return _spec("WORLD-S03", "R-51E8B7", V, ("x1", "x2"), V, ticks)


def _outside_vocabulary():
    """RULE_S02 with x2 starting True: an unforced x2 sits at True, against
    the vocabulary's baseline=False prior. No claim describes this world."""
    return _spec("WORLD-S02", "R-A18D40", V, ("x1", "x2"), V, 1, {"x2": True})


def _normalized(statement: str) -> str:
    """Two-cause claims store causes in alias-sorted order, so after
    translating back to real names "x1 AND x2" may read "x2 AND x1"
    depending on the alias seed. Same claim; sort the operands."""
    for op in (" AND ", " OR "):
        if op in statement:
            left, target = statement.split(" -> ")
            return op.join(sorted(left.split(op))) + " -> " + target
    return statement


@dataclass
class Run:
    outcome: object
    journal_path: Path
    manifest: object

    def verdict(self, real_target: str) -> str:
        return self._question(real_target).verdict

    def survivors(self, real_target: str) -> list[str]:
        real = {alias: name for name, alias in self.manifest.variable_alias.items()}
        statements = {h.hypothesis_id: h.statement for h in self.outcome.final_hypothesis_set.hypotheses}
        return sorted(_normalized(" ".join(real.get(t, t) for t in statements[hid].split()))
                      for hid in self._question(real_target).surviving_hypothesis_ids)

    def _question(self, real_target: str):
        [q] = [q for q in self.outcome.questions
               if q.target_observable_id == self.manifest.observable_alias[real_target]]
        return q


def _run(tmp_path: Path, spec: SyntheticWorldSpec, seed: int = 0, executor=None, name="journal.jsonl",
         **kwargs) -> Run:
    """Harness: builds the blind interface and executor, hands B only the blind parts."""
    world, manifest = make_blind_session(spec, seed)
    path = tmp_path / name
    journal = ResearchJournal.create(path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 executor or SyntheticBlindAExecutor(spec, manifest), journal, **kwargs)
    journal.close()
    return Run(outcome, path, manifest)


# ---------------------------------------------------------------------------
# 1. Identifiable worlds.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("make_spec,expected", [
    (_s01, ["x1 -> x3"]),
    (_s02, ["x1 AND x2 -> x3"]),
    (lambda: _s02(ticks=2), ["x1 AND x2 -> x3"]),
    (_s03, ["x1 -> x2 -> x3"]),
])
def test_identifiable_world_ends_solved_on_the_real_structure(tmp_path, make_spec, expected) -> None:
    run = _run(tmp_path, make_spec())
    assert run.outcome.termination == COMPLETE
    assert run.outcome.validated_fully
    assert run.verdict("x3") == SOLVED
    assert run.survivors("x3") == expected
    assert all(q.verdict == SOLVED for q in run.outcome.questions)


def test_s03_side_questions_are_also_answered(tmp_path) -> None:
    run = _run(tmp_path, _s03())
    assert run.survivors("x2") == ["x1 -> x2"]
    assert run.survivors("x1") == ["no controllable variable affects x1"]


# ---------------------------------------------------------------------------
# 2. One tick: an honest tie.
# ---------------------------------------------------------------------------

def test_one_tick_chain_ends_inseparable_not_picked(tmp_path) -> None:
    run = _run(tmp_path, _s03(ticks=1))
    assert run.outcome.termination == COMPLETE
    assert run.verdict("x3") == INSEPARABLE
    assert run.survivors("x3") == ["x1 -> x2 -> x3", "x2 -> x3"]
    [question] = [q for q in run.outcome.questions if q.verdict == INSEPARABLE]
    assert len(question.inseparable_pairs) == 1
    assert run.outcome.final_seal.unresolved_hypothesis_ids == question.surviving_hypothesis_ids


# ---------------------------------------------------------------------------
# 3. Outside the vocabulary.
# ---------------------------------------------------------------------------

def test_world_outside_the_vocabulary_ends_no_survivor(tmp_path) -> None:
    run = _run(tmp_path, _outside_vocabulary())
    assert run.verdict("x2") == NO_SURVIVOR
    assert run.verdict("x3") == NO_SURVIVOR
    assert run.verdict("x1") == SOLVED  # x1 really is untouched by x2 -- that part is describable
    assert run.outcome.validated_fully


def test_without_validation_the_same_world_gives_a_confident_wrong_answer(tmp_path) -> None:
    """Why the validation phase exists. Discovery alone stops once one
    claim is left: here x2 is declared SOLVED as "x1 -> x2" (wrong: x2 is
    simply stuck at True) after a single experiment where that claim
    happened to predict right. Pinned so the danger stays documented; the
    outcome says `validated_fully=False`, which is the flag a reader must
    check before trusting a SOLVED."""
    run = _run(tmp_path, _outside_vocabulary(), max_validation_experiments=0)
    assert run.verdict("x2") == SOLVED
    assert run.survivors("x2") == ["x1 -> x2"]
    assert not run.outcome.validated_fully
    assert run.outcome.validation_experiment_count == 0


# ---------------------------------------------------------------------------
# 4. Efficiency.
# ---------------------------------------------------------------------------

def _score_blind_select(sets, live, plan, executed):
    """Baseline selector: the first not-yet-run experiment (by horizon, then
    id) that splits *any* live pair -- same skip rule as G6d, but no ranking
    by how many pairs it splits."""
    ordered = sorted(plan.candidates, key=lambda c: (observation_horizon(plan.compiled_specs[c.candidate_id]),
                                                     c.candidate_id))
    for candidate in ordered:
        if candidate.candidate_id in executed:
            continue
        single = BlindExperimentPlan(plan.plan_id, (candidate,), plan.compiled_specs)
        chosen = _REAL_SELECT(sets, live, single, executed)
        if chosen is not None:
            return chosen
    return None


_REAL_SELECT = loop_module._select

WORLDS_FOR_EFFICIENCY = {
    "S02": (_s02, 5), "S02t2": (lambda: _s02(ticks=2), 5),
    "S03t1": (lambda: _s03(ticks=1), 3), "S03t2": (_s03, 4),
}


@pytest.mark.parametrize("name", sorted(WORLDS_FOR_EFFICIENCY))
def test_g6d_ranking_is_never_worse_than_score_blind_selection(tmp_path, monkeypatch, name) -> None:
    """Measured, not assumed: ranking by how many live pairs an experiment
    splits takes the pinned number of discovery experiments on every alias
    seed, never more than a score-blind selector (which still skips
    experiments that split nothing), and fewer on at least one seed. A
    plain "fewer than the whole plan" check could not tell these apart --
    a deliberately score-blind loop passed it during this Gate's own fault
    injection."""
    make_spec, expected = WORLDS_FOR_EFFICIENCY[name]
    ranked = [_run(tmp_path, make_spec(), seed=s, name=f"g{s}").outcome.discovery_experiment_count
              for s in (0, 1, 2)]
    plan_size = _run(tmp_path, make_spec(), name="p").outcome.plan_size
    monkeypatch.setattr(loop_module, "_select", _score_blind_select)
    blind = [_run(tmp_path, make_spec(), seed=s, name=f"b{s}").outcome.discovery_experiment_count
             for s in (0, 1, 2)]
    assert ranked == [expected] * 3
    assert all(r <= b for r, b in zip(ranked, blind))
    assert any(r < b for r, b in zip(ranked, blind))
    assert expected < plan_size


# ---------------------------------------------------------------------------
# 5. Stops that are not answers.
# ---------------------------------------------------------------------------

def test_budget_stop_is_limit_reached_with_open_questions_and_no_validation(tmp_path) -> None:
    run = _run(tmp_path, _s02(), max_experiments=1)
    assert run.outcome.termination == LIMIT_REACHED
    assert run.outcome.experiment_count == 1
    assert OPEN in {q.verdict for q in run.outcome.questions}
    assert not run.outcome.validated_fully
    assert audit_protocol(run.journal_path).valid


@dataclass(frozen=True)
class _FailingExecutor:
    def execute(self, spec) -> ExecutionResult:
        return ExecutionResult("failed", spec.digest, None, "RuntimeError", "withheld")


def test_failed_execution_ends_as_harness_failure(tmp_path) -> None:
    run = _run(tmp_path, _s02(), executor=_FailingExecutor())
    assert run.outcome.termination == HARNESS_FAILURE
    assert run.outcome.experiment_count == 1
    assert SOLVED not in {q.verdict for q in run.outcome.questions}
    assert audit_protocol(run.journal_path).valid


@dataclass(frozen=True)
class _OverlongExecutor:
    """Returns a run that goes one tick past the requested horizon -- the
    "executor ignored the horizon" defect, seen from B's side."""
    def execute(self, spec) -> ExecutionResult:
        values = tuple((f"ALIAS-OBS-{i}", False) for i in range(1))
        run = BlindRun(spec.world_id, tuple(BlindCheckpoint(t, values) for t in range(spec.ticks + 2)))
        return ExecutionResult("success", spec.digest, run)


def test_result_at_the_wrong_horizon_stops_the_loop_instead_of_rejecting(tmp_path) -> None:
    with pytest.raises(ValueError):
        _run(tmp_path, _s02(), executor=_OverlongExecutor())


def test_physical_a_executor_refuses_this_loop(tmp_path) -> None:
    """RULES.md's automation exception is for synthetic worlds only; the
    physical executor rejects a BlindCandidateSpec outright."""
    with pytest.raises(WorldCompatibilityError):
        _run(tmp_path, _s02(), executor=RealCausalAExecutor())


# ---------------------------------------------------------------------------
# 6. Protocol.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("make_spec", [_s01, _s02, _s03, lambda: _s03(ticks=1), _outside_vocabulary])
def test_journal_passes_the_g72_protocol_audit(tmp_path, make_spec) -> None:
    run = _run(tmp_path, make_spec())
    assert audit_protocol(run.journal_path).valid
    assert audit_final_hypothesis_digest(run.journal_path, run.outcome.final_hypothesis_set).valid
    entries = read_journal(run.journal_path)
    assert entries[-1].event_type == "final_discovery_sealed"
    assert run.outcome.final_seal.experiment_count == run.outcome.experiment_count


def test_every_execution_is_preceded_by_a_seal_holding_every_live_hypothesis(tmp_path) -> None:
    run = _run(tmp_path, _s03())
    entries = read_journal(run.journal_path)
    for index, entry in enumerate(entries):
        if entry.event_type == "execution_completed":
            seal = entries[index - 1]
            assert seal.event_type == "prediction_sealed" and seal.payload["arm_id"] == entry.record_id
            compared = next(e for e in entries[index:] if e.event_type == "result_compared")
            assert sorted(compared.payload["held"]) == sorted(seal.payload["predictions_by_hypothesis"])


# ---------------------------------------------------------------------------
# 7. Statuses, determinism, robustness, leakage, dependencies.
# ---------------------------------------------------------------------------

def test_final_statuses_never_claim_more_than_the_evidence(tmp_path) -> None:
    run = _run(tmp_path, _s03(ticks=1))
    statuses = {h.hypothesis_id: h.status for h in run.outcome.final_hypothesis_set.hypotheses}
    for question in run.outcome.questions:
        for hid in question.rejected_hypothesis_ids:
            assert statuses[hid] == "contradicted_in_domain"
        for hid in question.surviving_hypothesis_ids:
            assert statuses[hid] == ("supported" if question.verdict == SOLVED else "underspecified")
    assert set(statuses.values()) <= {"contradicted_in_domain", "supported", "underspecified"}


def test_same_world_same_outcome(tmp_path) -> None:
    first = _run(tmp_path, _s03(), name="a.jsonl").outcome
    second = _run(tmp_path, _s03(), name="b.jsonl").outcome
    assert first.canonical() == second.canonical()


@pytest.mark.parametrize("make_spec", [_s02, _s03, lambda: _s03(ticks=1), _outside_vocabulary])
def test_alias_permutation_does_not_change_the_findings(tmp_path, make_spec) -> None:
    def findings(seed):
        run = _run(tmp_path, make_spec(), seed=seed, name=f"j{seed}.jsonl")
        return (sorted((t, run.verdict(t), tuple(run.survivors(t)))
                       for t in ("x1", "x2", "x3") if t in run.manifest.observable_alias),
                run.outcome.discovery_experiment_count)
    assert findings(0) == findings(1) == findings(2)


SECRET_VALUES = ("WORLD-S01", "WORLD-S02", "WORLD-S03", "R-7F93C2", "R-A18D40", "R-51E8B7",
                 "GT-2", "GT-3", "GT-M1", "RULE_S01", "RULE_S02", "RULE_S03")


def test_journal_and_outcome_carry_no_real_identity(tmp_path) -> None:
    spec = _s03()
    run = _run(tmp_path, spec)
    text = run.journal_path.read_text(encoding="utf-8") + json.dumps(run.outcome.canonical())
    assert spec.digest not in text
    for secret in SECRET_VALUES:
        assert secret not in text
    for real_name in spec.variables:
        assert f'"{real_name}"' not in text and f" {real_name} " not in text


def test_loop_transitive_closure_never_reaches_evaluator_or_answer_modules() -> None:
    closure = _closure("blind_research_loop")
    assert not closure & FORBIDDEN_MODULES, sorted(closure & FORBIDDEN_MODULES)
    assert "ground_truth" not in closure and "*" not in closure
    assert "research_loop" in closure  # the walker really followed the reused seal/execute helpers
