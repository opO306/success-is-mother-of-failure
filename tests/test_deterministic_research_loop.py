import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    AccidentRecord,
    BondCountPrediction,
    CausalExperimentArm,
    CausalExperimentPortfolio,
    CausalHypothesis,
    CausalHypothesisSet,
    CausalWorldSpec,
    EvidenceReference,
    ExecutionResult,
    PredictionSeal,
    RealCausalAExecutor,
    ResearchJournal,
    StateDigestPrediction,
    StubAExecutor,
    archive,
    compare_results,
    design_experiments,
    detect_accident,
    execute_through_a,
    load_causal_world_spec,
    observe,
    read_journal,
    record_accident,
    record_anomaly,
    record_hypothesis_set,
    rebuild_research_state,
    run_causal_world,
    seal_predictions,
    update_hypothesis_status,
    verify_journal,
)
from engine.deterministic.research_state import AnomalyRecord

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

# Ground truth for EXAMPLE, established once by actually running causal A:
# two kind-0 particles moving toward each other bond at tick 1 (bond_count=1)
# and the bond breaks again at tick 2 once enough heat accumulates.
TICK_1_BOND_COUNT = 1


def _no_evidence(evidence_id: str, source_digest: str, description: str) -> tuple[EvidenceReference, ...]:
    return (EvidenceReference(evidence_id, "leaves_open", source_digest, description),)


def test_full_loop_observe_to_archive_with_real_a(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal_path = tmp_path / "run" / "journal.jsonl"
    journal = ResearchJournal.create(journal_path)

    observation = observe(journal, spec, "two kind-0 particles approach head-on with heat present")

    bonds_form = CausalHypothesis(
        "H-bonds-form", "the approaching particles bond by tick 1", ("material=kind0", "heat>=2"),
        (BondCountPrediction(1, TICK_1_BOND_COUNT),),
        _no_evidence("E1", spec.digest, "initial spec shows sufficient heat for the bond rule"),
        "untested",
    )
    no_bond = CausalHypothesis(
        "H-no-bond", "the particles pass through without bonding", ("material=kind0", "heat>=2"),
        (BondCountPrediction(1, 0),),
        _no_evidence("E1", spec.digest, "initial spec shows sufficient heat for the bond rule"),
        "untested",
    )
    hypothesis_set = CausalHypothesisSet(spec.digest, (bonds_form, no_bond))
    record_hypothesis_set(journal, hypothesis_set)

    arm = CausalExperimentArm("ARM-1", "temperature", spec, spec, ("H-bonds-form", "H-no-bond"))
    portfolio = CausalExperimentPortfolio(
        "P-1", ("H-bonds-form", "H-no-bond"), (arm,), {"temperature": True},
    )
    design_experiments(journal, portfolio)

    seal = PredictionSeal(
        "PS-1", "ARM-1", journal.next_sequence,
        {"H-bonds-form": (BondCountPrediction(1, TICK_1_BOND_COUNT),), "H-no-bond": (BondCountPrediction(1, 0),)},
    )
    seal_predictions(journal, seal)

    executor = RealCausalAExecutor()
    result = execute_through_a(journal, executor, "ARM-1", arm.submitted_spec)
    assert result.status == "success"

    accident = detect_accident("ARM-1", arm.intended_spec, arm.submitted_spec, result, observation.observation_id)
    assert accident is None  # intended == submitted == executed for this arm

    verdicts = compare_results(journal, hypothesis_set, seal, "ARM-1", result)
    assert verdicts == {"H-bonds-form": "supported", "H-no-bond": "contradicted_in_domain"}

    update_hypothesis_status(journal, "H-bonds-form", "untested", "supported", "tick-1 bond count matched prediction")
    update_hypothesis_status(journal, "H-no-bond", "untested", "contradicted_in_domain",
                             "tick-1 bond count contradicted the no-bond prediction in this domain")

    state = archive(journal)

    assert state.hypothesis_status["H-bonds-form"] == "supported"
    assert state.hypothesis_status["H-no-bond"] == "contradicted_in_domain"
    assert state.open_anomaly_ids == ()
    assert state.open_accident_ids == ()
    assert state.last_sequence == journal.next_sequence - 1

    verification = verify_journal(journal_path)
    assert verification["valid"] is True

    rebuilt = rebuild_research_state(journal_path)
    assert rebuilt == state


def test_journal_replay_reconstructs_identical_state_after_reopening(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal_path = tmp_path / "run" / "journal.jsonl"
    journal = ResearchJournal.create(journal_path)
    observe(journal, spec, "initial look")
    hypothesis = CausalHypothesis(
        "H-1", "placeholder claim", ("material=kind0",), (StateDigestPrediction(0, "irrelevant"),),
        (), "untested",
    )
    record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (hypothesis,)))
    state_before_close = rebuild_research_state(journal_path)
    journal.close()

    reopened = ResearchJournal.open(journal_path)
    update_hypothesis_status(reopened, "H-1", "untested", "conditional", "partial support found later")
    state_after_reopen = archive(reopened)

    assert state_before_close.hypothesis_status["H-1"] == "untested"
    assert state_after_reopen.hypothesis_status["H-1"] == "conditional"
    assert verify_journal(journal_path)["valid"] is True


def test_accident_is_detected_when_submitted_spec_differs_from_intended(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    contaminated = CausalWorldSpec.from_mapping({
        **spec.canonical(),
        "heat": [{"x": 10, "y": 10, "energy": 4}],
    })
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    observation = observe(journal, spec, "baseline observation")

    executor = RealCausalAExecutor()
    result = execute_through_a(journal, executor, "ARM-X", contaminated)

    accident = detect_accident("ARM-X", spec, contaminated, result, observation.observation_id)
    assert accident is not None
    assert accident.original_test_valid is False
    assert accident.intended_spec_digest == spec.digest
    assert accident.submitted_spec_digest == accident.executed_spec_digest == contaminated.digest

    recorded = record_accident(journal, accident)
    state = archive(journal)
    assert state.open_accident_ids == (recorded.accident_id,)


def test_anomaly_is_preserved_not_discarded_when_prediction_fails_unexpectedly(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    observation = observe(journal, spec, "baseline observation")

    hypothesis = CausalHypothesis(
        "H-wrong", "no bond forms by tick 1", ("material=kind0",), (BondCountPrediction(1, 0),),
        (), "untested",
    )
    record_hypothesis_set(journal, CausalHypothesisSet(spec.digest, (hypothesis,)))
    seal = PredictionSeal("PS-1", "ARM-1", journal.next_sequence, {"H-wrong": (BondCountPrediction(1, 0),)})
    seal_predictions(journal, seal)

    executor = RealCausalAExecutor()
    result = execute_through_a(journal, executor, "ARM-1", spec)
    verdicts = compare_results(journal, CausalHypothesisSet(spec.digest, (hypothesis,)), seal, "ARM-1", result)
    assert verdicts["H-wrong"] == "contradicted_in_domain"

    anomaly = AnomalyRecord(
        "ANOM-1", "H-wrong", "ARM-1", {"expected_bond_count": 0, "kind": "bond_count", "tick": 1},
        {"expected_bond_count": TICK_1_BOND_COUNT, "kind": "bond_count", "tick": 1},
        observation.observation_id, 1, "unresolved",
    )
    recorded = record_anomaly(journal, anomaly)
    state = archive(journal)

    assert state.open_anomaly_ids == (recorded.anomaly_id,)


def test_execution_failure_never_raises_and_is_journaled(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    stub = StubAExecutor()
    stub.register(spec, ExecutionResult("failed", spec.digest, None, "AssertionError",
                                        "causal tick changed total energy"))
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    result = execute_through_a(journal, stub, "ARM-FAIL", spec)

    assert result.status == "failed"
    assert result.error_kind == "AssertionError"

    hypothesis = CausalHypothesis(
        "H-1", "placeholder", ("material=kind0",), (BondCountPrediction(1, 0),), (), "untested",
    )
    seal = PredictionSeal("PS-1", "ARM-FAIL", journal.next_sequence, {"H-1": (BondCountPrediction(1, 0),)})
    seal_predictions(journal, seal)
    verdicts = compare_results(journal, CausalHypothesisSet(spec.digest, (hypothesis,)), seal, "ARM-FAIL", result)

    assert verdicts == {"H-1": "underspecified"}

    entries = read_journal(journal.path)
    assert [item.event_type for item in entries] == [
        "execution_completed", "prediction_sealed", "result_compared",
    ]


def test_seal_must_be_appended_immediately_at_its_claimed_sequence(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    observe(journal, spec, "baseline")

    stale_seal = PredictionSeal("PS-1", "ARM-1", 0, {"H-1": (BondCountPrediction(1, 0),)})
    with pytest.raises(ValueError, match="sequence"):
        seal_predictions(journal, stale_seal)
