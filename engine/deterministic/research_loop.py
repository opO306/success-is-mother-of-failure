"""B0 research loop: observe -> hypothesize -> design -> seal -> execute -> compare -> update -> archive.

This module owns no physics and no intelligence: hypothesis generation is a
caller-supplied step (a human, or later a rule-based or learned adapter) --
see docs/README/08 on why B0 tests the loop itself before any reasoning
component. What this module guarantees is the bookkeeping discipline: every
step is journaled before the next runs, predictions are sealed before A is
asked to execute, and `ResearchState` is always derived by replaying the
journal rather than carried as separately-trusted memory.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Mapping

from .causal_executor import AExecutor, ExecutionResult
from .causal_experiment import CausalExperimentPortfolio, PredictionSeal
from .causal_hypothesis import CausalHypothesisSet
from .causal_kernel import initial_causal_state
from .causal_spec import CausalWorldSpec
from .research_journal import ResearchJournal, read_journal
from .research_state import (
    AccidentRecord,
    AnomalyRecord,
    ObservationRecord,
    ResearchState,
)


def observe(journal: ResearchJournal, spec: CausalWorldSpec, description: str) -> ObservationRecord:
    """Record what was directly read off `spec`'s initial state, before any interpretation."""
    initial = initial_causal_state(spec)
    observation = ObservationRecord(
        f"OBS-{journal.next_sequence}", spec.digest, initial.tick,
        {"material_counts": {str(k): v for k, v in initial.material_counts().items()},
         "total_energy": initial.total_energy(),
         "momentum": list(initial.momentum(spec)), "state_digest": initial.digest},
        description,
    )
    journal.append("observation_recorded", observation.observation_id, observation.canonical())
    return observation


def record_hypothesis_set(journal: ResearchJournal, hypothesis_set: CausalHypothesisSet) -> CausalHypothesisSet:
    """Journal a caller-supplied set of hypotheses. Generation itself is out of scope here."""
    journal.append("hypothesis_set_created", hypothesis_set.subject_digest, hypothesis_set.canonical())
    return hypothesis_set


def design_experiments(journal: ResearchJournal, portfolio: CausalExperimentPortfolio) -> CausalExperimentPortfolio:
    """Journal a caller-supplied portfolio of arms spanning several physical dimensions."""
    journal.append("portfolio_designed", portfolio.portfolio_id, portfolio.canonical())
    return portfolio


def seal_predictions(journal: ResearchJournal, seal: PredictionSeal) -> PredictionSeal:
    """Journal predictions before execution. `seal.sealed_at_seq` must match this append's sequence.

    Enforcing that match here is what makes the seal-before-execution ordering
    a checkable fact rather than a convention callers might violate.
    """
    if seal.sealed_at_seq != journal.next_sequence:
        raise ValueError(
            f"seal claims sequence {seal.sealed_at_seq} but the journal's next "
            f"sequence is {journal.next_sequence}; seal immediately before appending")
    journal.append("prediction_sealed", seal.seal_id, seal.canonical())
    return seal


def execute_through_a(journal: ResearchJournal, executor: AExecutor,
                      arm_id: str, submitted_spec: CausalWorldSpec) -> ExecutionResult:
    """Run `submitted_spec` through `executor` and journal the outcome, success or failure."""
    result = executor.execute(submitted_spec)
    journal.append("execution_completed", arm_id, result.canonical())
    return result


def _predicted_value(prediction: object) -> object:
    return prediction.canonical()


def _observed_value(prediction: object, result: ExecutionResult) -> object | None:
    if result.run is None:
        return None
    kind = prediction.canonical()["kind"]
    checkpoints = {item.tick: item for item in result.run.checkpoints}
    checkpoint = checkpoints.get(prediction.tick)
    if checkpoint is None:
        return None
    if kind == "state_digest":
        return {"expected_digest": checkpoint.state_digest, "kind": "state_digest", "tick": prediction.tick}
    if kind == "conservation":
        return {"expected_total_energy": checkpoint.total_energy, "kind": "conservation", "tick": prediction.tick}
    if kind == "momentum":
        return {"expected_momentum": list(checkpoint.momentum), "kind": "momentum", "tick": prediction.tick}
    if kind == "bond_count":
        return {"expected_bond_count": checkpoint.bonds, "kind": "bond_count", "tick": prediction.tick}
    if kind == "material_counts":
        return {"expected_counts": {str(k): v for k, v in checkpoint.material_counts},
                "kind": "material_counts", "tick": prediction.tick}
    raise ValueError(f"unsupported prediction kind {kind!r}")


def compare_results(
    journal: ResearchJournal, hypothesis_set: CausalHypothesisSet, seal: PredictionSeal,
    arm_id: str, result: ExecutionResult,
) -> Mapping[str, str]:
    """Compare each hypothesis's sealed predictions against the executed run.

    Returns `{hypothesis_id: "supported" | "contradicted_in_domain" | "underspecified"}`
    for hypotheses this seal covers. A hypothesis is `underspecified` when the
    execution failed outright or a predicted tick has no checkpoint to compare
    against -- that is a gap in what could be checked, not evidence against
    the claim.
    """
    verdicts: dict[str, str] = {}
    for hypothesis_id, predictions in seal.predictions_by_hypothesis.items():
        if result.status == "failed":
            verdicts[hypothesis_id] = "underspecified"
            continue
        outcomes = []
        for prediction in predictions:
            observed = _observed_value(prediction, result)
            if observed is None:
                outcomes.append("underspecified")
            elif observed == _predicted_value(prediction):
                outcomes.append("supported")
            else:
                outcomes.append("contradicted_in_domain")
        if "contradicted_in_domain" in outcomes:
            verdicts[hypothesis_id] = "contradicted_in_domain"
        elif "underspecified" in outcomes:
            verdicts[hypothesis_id] = "underspecified"
        else:
            verdicts[hypothesis_id] = "supported"
    journal.append("result_compared", arm_id, {
        "arm_id": arm_id, "hypothesis_set_digest": hypothesis_set.digest,
        "seal_id": seal.seal_id, "verdicts": dict(sorted(verdicts.items())),
    })
    return verdicts


def update_hypothesis_status(journal: ResearchJournal, hypothesis_id: str,
                             previous_status: str, new_status: str, reason: str) -> None:
    journal.append("hypothesis_status_changed", hypothesis_id, {
        "hypothesis_id": hypothesis_id, "new_status": new_status,
        "previous_status": previous_status, "reason": reason,
    })


def record_accident(journal: ResearchJournal, accident: AccidentRecord) -> AccidentRecord:
    journal.append("accident_recorded", accident.accident_id, accident.canonical())
    return accident


def record_anomaly(journal: ResearchJournal, anomaly: AnomalyRecord) -> AnomalyRecord:
    journal.append("anomaly_recorded", anomaly.anomaly_id, anomaly.canonical())
    return anomaly


def detect_accident(arm_id: str, intended_spec: CausalWorldSpec, submitted_spec: CausalWorldSpec,
                    result: ExecutionResult, observation_id: str) -> AccidentRecord | None:
    """Compare intended -> submitted -> executed specs. Returns None if all three agree."""
    executed_digest = result.executed_spec_digest
    if intended_spec.digest == submitted_spec.digest == executed_digest:
        return None
    difference = (
        f"intended={intended_spec.digest[:12]} submitted={submitted_spec.digest[:12]} "
        f"executed={executed_digest[:12]}"
    )
    return AccidentRecord(
        f"ACC-{arm_id}", arm_id, intended_spec.digest, submitted_spec.digest, executed_digest,
        difference, observation_id, intended_spec.digest == submitted_spec.digest, "unresolved",
    )


def archive(journal: ResearchJournal) -> ResearchState:
    """Fold the journal from the beginning into a fresh `ResearchState`.

    This is the only way `ResearchState` is produced: never mutated in place,
    always rebuilt from the append-only history so that replaying the same
    journal prefix is guaranteed to reproduce the same state.
    """
    journal.close()
    return rebuild_research_state(journal.path)


def rebuild_research_state(path: Path) -> ResearchState:
    active: dict[str, str] = {}
    open_anomalies: list[str] = []
    open_accidents: list[str] = []
    domains_seen: set[str] = set()
    last_sequence = -1
    for entry in read_journal(path):
        last_sequence = entry.sequence
        if entry.event_type == "hypothesis_set_created":
            for hypothesis in entry.payload["hypotheses"]:
                active[hypothesis["hypothesis_id"]] = hypothesis["status"]
                domains_seen.update(hypothesis["applicability_conditions"])
        elif entry.event_type == "hypothesis_status_changed":
            active[entry.payload["hypothesis_id"]] = entry.payload["new_status"]
        elif entry.event_type == "anomaly_recorded":
            open_anomalies.append(entry.payload["anomaly_id"])
        elif entry.event_type == "accident_recorded":
            open_accidents.append(entry.payload["accident_id"])
    return ResearchState(
        tuple(sorted(active)), dict(active), tuple(open_anomalies), tuple(open_accidents),
        tuple(sorted(domains_seen)), (), None, last_sequence,
    )
