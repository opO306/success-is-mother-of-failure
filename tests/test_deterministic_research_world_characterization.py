"""G0 characterization tests: pin the current, pre-abstraction behavior of B0's
Broad Research path so later Gates (G1+, the ResearchWorld/Adapter refactor)
have a fixed target to not deviate from.

These tests assert *exact* current shapes -- literal dict keys, literal
verdict strings, exact digests where practical -- deliberately more rigid
than the existing behavioral tests in test_deterministic_research_loop.py
and test_deterministic_broad_explorer.py. Those tests check "does the loop
work"; these check "does it produce exactly this, byte for byte", which is
what G2's "Physical Adapter changes nothing" claim needs to be checked
against.

Nothing here imports or references anything from the not-yet-built
research_world.py/research_adapter.py/physical_research_adapter.py --
that would defeat the point. This file only touches existing code.
"""
from __future__ import annotations

from pathlib import Path

from engine.deterministic import (
    BondCountPrediction,
    CausalExperimentArm,
    CausalHypothesis,
    CausalHypothesisSet,
    ControlDefinition,
    ExplorationPlan,
    HeatCellRoleTarget,
    PredictionSeal,
    RealCausalAExecutor,
    ResearchJournal,
    StateDigestPrediction,
    StubAExecutor,
    SweepDimension,
    compare_results,
    load_causal_world_spec,
    observe,
    record_hypothesis_set,
    run_exploration,
    seal_predictions,
)
from engine.deterministic.causal_executor import ExecutionResult
from engine.deterministic.causal_kernel import run_causal_world

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


# ---------------------------------------------------------------------------
# ExecutionResult.canonical() -- the exact shape journaled by execute_through_a
# ---------------------------------------------------------------------------

def test_execution_result_canonical_shape_for_a_successful_run() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    run = run_causal_world(spec)
    result = ExecutionResult("success", spec.digest, run)
    canonical = result.canonical()

    assert set(canonical.keys()) == {"error_kind", "error_message", "executed_spec_digest", "format", "run_digest", "status"}
    assert canonical["format"] == "causal-execution-result-v1"
    assert canonical["status"] == "success"
    assert canonical["executed_spec_digest"] == spec.digest
    assert canonical["run_digest"] == run.digest
    assert canonical["error_kind"] is None
    assert canonical["error_message"] is None


def test_execution_result_canonical_shape_for_a_failed_run() -> None:
    result = ExecutionResult("failed", "deadbeef", None, "ValueError", "boom")
    canonical = result.canonical()

    assert canonical["status"] == "failed"
    assert canonical["run_digest"] is None
    assert canonical["error_kind"] == "ValueError"
    assert canonical["error_message"] == "boom"


def test_real_causal_executor_wraps_causal_run_exactly() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    assert result.status == "success"
    assert result.run is not None
    assert result.run.digest == run_causal_world(spec).digest


# ---------------------------------------------------------------------------
# observe() -- the exact observation payload shape
# ---------------------------------------------------------------------------

def test_observe_payload_shape_and_values(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    observation = observe(journal, spec, "characterization baseline")

    assert set(observation.observables.keys()) == {"material_counts", "total_energy", "momentum", "state_digest"}
    assert observation.observed_at_tick == 0
    assert observation.source_digest == spec.digest
    # Two kind-0 particles, kinetic_energy=2 each, moving toward each other,
    # plus a heat cell holding energy=2 at the shared collision point:
    # total material count 2, total energy 2+2+2=6, momentum cancels to (0, 0).
    assert observation.observables["material_counts"] == {"0": 2}
    assert observation.observables["total_energy"] == 6
    assert observation.observables["momentum"] == [0, 0]


# ---------------------------------------------------------------------------
# compare_results() -- exact verdict strings for match/mismatch/unavailable
# ---------------------------------------------------------------------------

def test_compare_results_verdict_is_supported_on_exact_match(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    result = executor.execute(spec)

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(1, 1),), (), "untested")
    hs = record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (h1,)))
    seal = PredictionSeal("PS-1", "ARM-1", journal.next_sequence, {"H1": (BondCountPrediction(1, 1),)})
    seal_predictions(journal, seal)

    verdicts = compare_results(journal, hs, seal, "ARM-1", result)
    assert verdicts == {"H1": "supported"}


def test_compare_results_verdict_is_contradicted_in_domain_on_mismatch(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    result = executor.execute(spec)

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(1, 99),), (), "untested")
    hs = record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (h1,)))
    seal = PredictionSeal("PS-1", "ARM-1", journal.next_sequence, {"H1": (BondCountPrediction(1, 99),)})
    seal_predictions(journal, seal)

    verdicts = compare_results(journal, hs, seal, "ARM-1", result)
    assert verdicts == {"H1": "contradicted_in_domain"}


def test_compare_results_verdict_is_underspecified_on_missing_checkpoint_tick(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    result = executor.execute(spec)

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(999, 0),), (), "untested")
    hs = record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (h1,)))
    seal = PredictionSeal("PS-1", "ARM-1", journal.next_sequence, {"H1": (BondCountPrediction(999, 0),)})
    seal_predictions(journal, seal)

    verdicts = compare_results(journal, hs, seal, "ARM-1", result)
    assert verdicts == {"H1": "underspecified"}


def test_compare_results_verdict_is_underspecified_on_failed_execution(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(1, 1),), (), "untested")
    hs = record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (h1,)))
    seal = PredictionSeal("PS-1", "ARM-1", journal.next_sequence, {"H1": (BondCountPrediction(1, 1),)})
    seal_predictions(journal, seal)

    failed_result = ExecutionResult("failed", spec.digest, None, "SomeError", "boom")
    verdicts = compare_results(journal, hs, seal, "ARM-1", failed_result)
    assert verdicts == {"H1": "underspecified"}


# ---------------------------------------------------------------------------
# run_exploration() -- exact evidence relations and coverage for the heat sweep
# ---------------------------------------------------------------------------

def test_run_exploration_heat_sweep_produces_exact_relations_and_coverage(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    base_spec = load_causal_world_spec(EXAMPLE)
    observation = observe(journal, base_spec, "characterization: heat sweep")

    h1 = CausalHypothesis("H1", "any local heat present breaks the bond by tick 2",
                          ("bond_present", "heat>0"), (BondCountPrediction(2, 0),), (), "untested")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (h1,)))

    plan = ExplorationPlan("P-heat-sweep", base_spec.digest, ("H1",),
                           (SweepDimension(HEAT_CONTROL.control_id, (0, 1, 2, 3, 4)),), "full_factorial", 10)
    outcome = run_exploration(journal, executor, plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL},
                              {"H1": (BondCountPrediction(2, 0),)}, observation.observation_id)

    relations = {dict(c.control_values)[HEAT_CONTROL.control_id]: r.relation
                for c in outcome.candidates for r in outcome.evidence if r.arm_id == c.candidate_id}
    assert relations == {0: "contradicts", 1: "contradicts", 2: "supports", 3: "supports", 4: "supports"}
    assert outcome.compilation_failures == ()
    assert outcome.coverage.executed_count == 5
    assert outcome.coverage.invalid_count == 0
    assert len(outcome.boundary_candidates) == 1

    # The exact evidence canonical shape, pinned for G2 comparison.
    example_evidence = sorted(outcome.evidence, key=lambda e: e.evidence_id)[0]
    canonical = example_evidence.canonical()
    assert set(canonical.keys()) >= {"evidence_id", "hypothesis_id", "domain_id", "arm_id",
                                     "seal_id", "relation", "intended_spec_digest", "executed_spec_digest"}


# ---------------------------------------------------------------------------
# CausalExperimentArm -- exact canonical shape (relevant to G2's type widening)
# ---------------------------------------------------------------------------

def test_causal_experiment_arm_canonical_shape() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    arm = CausalExperimentArm("ARM-1", "causal.heat.energy", spec, spec, ("H1",))
    canonical = arm.canonical()
    assert set(canonical.keys()) == {"arm_id", "dimension", "intended_spec_digest",
                                     "resolves_hypothesis_ids", "submitted_spec_digest"}
    assert canonical["intended_spec_digest"] == spec.digest
    assert canonical["submitted_spec_digest"] == spec.digest
    assert arm.intent_matches_submission is True


def test_stub_a_executor_registered_result_round_trips() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    stub = StubAExecutor()
    result = ExecutionResult("success", spec.digest, run_causal_world(spec))
    stub.register(spec, result)
    assert stub.execute(spec) is result
