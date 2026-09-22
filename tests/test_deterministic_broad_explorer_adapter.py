"""G4-G5: run_research_exploration produces byte-identical results to
run_exploration through StaticPredictionProvider, and FunctionalPredictionProvider
actually varies predictions per candidate (proving the seam is not just
decorative -- see research_prediction.py's docstring on why this exists).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.deterministic import (
    BondCountPrediction,
    CausalHypothesis,
    CausalHypothesisSet,
    ControlDefinition,
    ExplorationPlan,
    HeatCellRoleTarget,
    RealCausalAExecutor,
    ResearchJournal,
    StateDigestPrediction,
    SweepDimension,
    load_causal_world_spec,
    observe,
    record_hypothesis_set,
    run_exploration,
)
from engine.deterministic.broad_explorer import run_research_exploration
from engine.deterministic.physical_research_adapter import PhysicalCausalResearchAdapter
from engine.deterministic.research_prediction import FunctionalPredictionProvider, StaticPredictionProvider
from engine.deterministic.research_world import UnknownControlError, WorldCompatibilityError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


def _heat_sweep_plan(base_spec) -> ExplorationPlan:
    return ExplorationPlan("P-heat-sweep", base_spec.digest, ("H1",),
                           (SweepDimension(HEAT_CONTROL.control_id, (0, 1, 2, 3, 4)),), "full_factorial", 10)


def test_run_research_exploration_with_static_provider_matches_run_exploration_exactly(tmp_path: Path) -> None:
    base_spec = load_causal_world_spec(EXAMPLE)
    predictions = {"H1": (BondCountPrediction(2, 0),)}

    journal_a = ResearchJournal.create(tmp_path / "a.jsonl")
    executor_a = RealCausalAExecutor()
    obs_a = observe(journal_a, base_spec, "sweep a")
    record_hypothesis_set(journal_a, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), predictions["H1"], (), "untested"),)))
    via_wrapper = run_exploration(journal_a, executor_a, _heat_sweep_plan(base_spec), base_spec,
                                  {HEAT_CONTROL.control_id: HEAT_CONTROL}, predictions, obs_a.observation_id)

    journal_b = ResearchJournal.create(tmp_path / "b.jsonl")
    executor_b = RealCausalAExecutor()
    obs_b = observe(journal_b, base_spec, "sweep a")
    record_hypothesis_set(journal_b, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), predictions["H1"], (), "untested"),)))
    via_generic = run_research_exploration(
        journal_b, executor_b, PhysicalCausalResearchAdapter(), StaticPredictionProvider(predictions),
        _heat_sweep_plan(base_spec), base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL}, obs_b.observation_id,
    )

    assert via_wrapper.canonical() == via_generic.canonical()


def test_functional_prediction_provider_varies_predictions_per_candidate(tmp_path: Path) -> None:
    """Unlike StaticPredictionProvider, a functional one can look at the
    candidate's own compiled spec and predict differently per candidate --
    the seam GT-2-style per-value truth tables will eventually need."""
    base_spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    observation = observe(journal, base_spec, "functional provider test")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), (StateDigestPrediction(2, "placeholder"),), (), "untested"),)))

    seen_candidates: list[str] = []

    def provider_fn(candidate, compiled_spec):
        seen_candidates.append(candidate.candidate_id)
        # Predict this candidate's own actual final-tick digest -- always "true" by
        # construction, proving the provider genuinely saw this candidate's spec.
        from engine.deterministic.causal_kernel import run_causal_world
        run = run_causal_world(compiled_spec)
        final_checkpoint = next(c for c in run.checkpoints if c.tick == 2)
        return {"H1": (StateDigestPrediction(2, final_checkpoint.state_digest),)}

    plan = _heat_sweep_plan(base_spec)
    outcome = run_research_exploration(
        journal, executor, PhysicalCausalResearchAdapter(), FunctionalPredictionProvider(provider_fn),
        plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL}, observation.observation_id,
    )

    assert len(seen_candidates) == 5  # saw every candidate, not just the first
    # Every candidate's self-predicted digest must match exactly (the whole point).
    assert all(item.relation == "supports" for item in outcome.evidence)


def test_run_research_exploration_never_swallows_world_compatibility_error(tmp_path: Path) -> None:
    """A wiring mistake (wrong adapter for this spec kind) must propagate,
    never become a CandidateCompilationFailure -- that would hide a
    programming error as if it were a fact about the world."""
    base_spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    observation = observe(journal, base_spec, "wrong adapter")

    class AlwaysIncompatibleAdapter:
        adapter_id = "always-incompatible"

        def assert_compatible(self, spec):
            raise WorldCompatibilityError("never compatible")

        def validate(self, spec):
            raise WorldCompatibilityError("never compatible")

        def apply_control(self, spec, control, value):
            raise WorldCompatibilityError("never compatible")

        def initial_observation(self, spec):
            raise WorldCompatibilityError("never compatible")

        def evaluate_prediction(self, prediction, result):
            raise WorldCompatibilityError("never compatible")

    with pytest.raises(WorldCompatibilityError):
        run_research_exploration(
            journal, executor, AlwaysIncompatibleAdapter(), StaticPredictionProvider({"H1": ()}),
            _heat_sweep_plan(base_spec), base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL}, observation.observation_id,
        )
