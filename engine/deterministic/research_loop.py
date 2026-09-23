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

from .execution import AExecutor, ExecutionResult
from .causal_experiment import CausalExperimentPortfolio, PredictionSeal
from .causal_hypothesis import CausalHypothesisSet
from .causal_spec import CausalWorldSpec
from .hypothesis_assessment import derive_hypothesis_assessment
from .hypothesis_graph import (
    ContradictionRecord,
    HypothesisDomainLink,
    HypothesisEdge,
    HypothesisGraph,
)
from .physical_research_adapter import PhysicalCausalResearchAdapter
from .research_adapter import ResearchWorldAdapter
from .research_axis import AxisRegistry, CAUSAL_AXIS_REGISTRY
from .research_domain import ResearchDomain
from .research_journal import ResearchJournal, read_journal
from .research_memory import DomainEvidence, ResearchMemoryIndex
from .research_state import (
    AccidentRecord,
    AnomalyRecord,
    ObservationRecord,
    ResearchState,
)
from .research_world import ResearchWorldSpec
# seal_predictions / execute_through_a live in `sealed_execution.py` (no
# physical-world imports) and are re-exported so existing imports keep working.
from .sealed_execution import execute_through_a, seal_predictions  # noqa: F401

_PHYSICAL_ADAPTER = PhysicalCausalResearchAdapter()


def observe_world(journal: ResearchJournal, adapter: ResearchWorldAdapter,
                  spec: ResearchWorldSpec, description: str) -> ObservationRecord:
    """Record what `adapter` read off `spec`'s initial state, before any interpretation.

    World-agnostic core of `observe()`: the observable payload comes from
    `adapter.initial_observation`, so this works for any `ResearchWorldSpec`
    an adapter knows how to read, not just `CausalWorldSpec`.
    """
    world_observation = adapter.initial_observation(spec)
    observation = ObservationRecord(
        f"OBS-{journal.next_sequence}", world_observation.world_digest, world_observation.tick,
        {**world_observation.observables, "state_digest": world_observation.state_digest}, description,
    )
    journal.append("observation_recorded", observation.observation_id, observation.canonical())
    return observation


def observe(journal: ResearchJournal, spec: CausalWorldSpec, description: str) -> ObservationRecord:
    """Record what was directly read off `spec`'s initial state, before any interpretation.

    Physical-A compatibility wrapper around `observe_world` -- unchanged
    signature and behavior for existing callers (see
    `test_deterministic_research_world_characterization.py` for the exact
    payload this must keep producing).
    """
    return observe_world(journal, _PHYSICAL_ADAPTER, spec, description)


def record_hypothesis_set(journal: ResearchJournal, hypothesis_set: CausalHypothesisSet) -> CausalHypothesisSet:
    """Journal a caller-supplied set of hypotheses. Generation itself is out of scope here."""
    journal.append("hypothesis_set_created", hypothesis_set.subject_digest, hypothesis_set.canonical())
    return hypothesis_set


def design_experiments(journal: ResearchJournal, portfolio: CausalExperimentPortfolio) -> CausalExperimentPortfolio:
    """Journal a caller-supplied portfolio of arms spanning several physical dimensions."""
    journal.append("portfolio_designed", portfolio.portfolio_id, portfolio.canonical())
    return portfolio


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


_EVALUATION_STATUS_TO_VERDICT = {
    "match": "supported", "mismatch": "contradicted_in_domain", "unavailable": "underspecified",
}


def compare_results_with_adapter(
    journal: ResearchJournal, adapter: ResearchWorldAdapter, hypothesis_set: CausalHypothesisSet,
    seal: PredictionSeal, arm_id: str, result: ExecutionResult,
) -> Mapping[str, str]:
    """World-agnostic core of `compare_results`: `adapter.evaluate_prediction`
    decides match/mismatch/unavailable per prediction; this function only
    folds several predictions for one hypothesis into one verdict, exactly
    as `compare_results` always has.
    """
    verdicts: dict[str, str] = {}
    for hypothesis_id, predictions in seal.predictions_by_hypothesis.items():
        if result.status == "failed":
            verdicts[hypothesis_id] = "underspecified"
            continue
        outcomes = [_EVALUATION_STATUS_TO_VERDICT[adapter.evaluate_prediction(prediction, result).status]
                   for prediction in predictions]
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

    Physical-A compatibility wrapper around `compare_results_with_adapter` --
    unchanged signature and behavior for existing callers.
    """
    return compare_results_with_adapter(journal, _PHYSICAL_ADAPTER, hypothesis_set, seal, arm_id, result)


def register_domain(journal: ResearchJournal, domain: ResearchDomain,
                    registry: AxisRegistry = CAUSAL_AXIS_REGISTRY) -> ResearchDomain:
    """Journal a `ResearchDomain` after checking every constraint names a registered axis."""
    domain.validate_against(registry)
    journal.append("domain_registered", domain.domain_id, domain.canonical())
    return domain


def link_hypothesis_domain(journal: ResearchJournal, link: HypothesisDomainLink) -> HypothesisDomainLink:
    """Journal the machine-checkable domain a hypothesis's applicability targets.

    Leaves `CausalHypothesis.applicability_conditions` (human text) untouched.
    """
    journal.append("hypothesis_domain_linked", link.hypothesis_id, link.canonical())
    return link


def record_domain_evidence(
    journal: ResearchJournal, evidence: DomainEvidence,
    existing_evidence: tuple[DomainEvidence, ...] = (),
) -> tuple[DomainEvidence, ContradictionRecord | None]:
    """Journal one arm's outcome as evidence for a hypothesis in a domain.

    If `existing_evidence` (for the same hypothesis and domain) already
    contains a valid opposite-relation entry, a `ContradictionRecord` is
    created and journaled too -- causal A is deterministic, so support and
    contradiction in the very same domain is never silently folded into
    `conditional`.
    """
    journal.append("domain_evidence_recorded", evidence.evidence_id, evidence.canonical())
    contradiction = None
    if evidence.valid_for_hypothesis and evidence.relation in ("supports", "contradicts"):
        opposite = "contradicts" if evidence.relation == "supports" else "supports"
        clashing = tuple(
            item for item in existing_evidence
            if item.hypothesis_id == evidence.hypothesis_id and item.domain_id == evidence.domain_id
            and item.valid_for_hypothesis and item.relation == opposite
        )
        if clashing:
            supporting = (evidence,) if evidence.relation == "supports" else clashing
            contradicting = (evidence,) if evidence.relation == "contradicts" else clashing
            contradiction = ContradictionRecord(
                f"CON-{evidence.hypothesis_id}-{evidence.domain_id}", evidence.hypothesis_id, evidence.domain_id,
                tuple(sorted({item.evidence_id for item in supporting})),
                tuple(sorted({item.evidence_id for item in contradicting})),
            )
            journal.append("contradiction_detected", contradiction.contradiction_id, contradiction.canonical())
    return evidence, contradiction


def add_hypothesis_edge(journal: ResearchJournal, edge: HypothesisEdge) -> HypothesisEdge:
    """Journal a lineage relation. The authoritative source of graph structure from B0.2 on."""
    journal.append("hypothesis_edge_added", edge.edge_id, edge.canonical())
    return edge


def update_contradiction_status(journal: ResearchJournal, contradiction_id: str,
                                previous_status: str, new_status: str, reason: str) -> None:
    journal.append("contradiction_status_changed", contradiction_id, {
        "contradiction_id": contradiction_id, "new_status": new_status,
        "previous_status": previous_status, "reason": reason,
    })


def update_anomaly_status(journal: ResearchJournal, anomaly_id: str,
                          previous_status: str, new_status: str, reason: str) -> None:
    journal.append("anomaly_status_changed", anomaly_id, {
        "anomaly_id": anomaly_id, "new_status": new_status,
        "previous_status": previous_status, "reason": reason,
    })


def update_accident_status(journal: ResearchJournal, accident_id: str,
                           previous_status: str, new_status: str, reason: str) -> None:
    journal.append("accident_status_changed", accident_id, {
        "accident_id": accident_id, "new_status": new_status,
        "previous_status": previous_status, "reason": reason,
    })


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


def rebuild_hypothesis_graph(path: Path) -> HypothesisGraph:
    """Replay the journal into a `HypothesisGraph`: edges, domain links, contradictions."""
    edges: dict[str, HypothesisEdge] = {}
    links: dict[tuple[str, str], HypothesisDomainLink] = {}
    contradictions: dict[str, ContradictionRecord] = {}
    for entry in read_journal(path):
        if entry.event_type == "hypothesis_edge_added":
            payload = entry.payload
            edge = HypothesisEdge(payload["edge_id"], payload["source_hypothesis_id"],
                                  payload["target_hypothesis_id"], payload["relation"],
                                  tuple(payload["evidence_ids"]))
            edges[edge.edge_id] = edge
        elif entry.event_type == "hypothesis_domain_linked":
            payload = entry.payload
            link = HypothesisDomainLink(payload["hypothesis_id"], payload["domain_id"], payload["role"])
            links[(link.hypothesis_id, link.domain_id)] = link
        elif entry.event_type == "contradiction_detected":
            payload = entry.payload
            contradictions[payload["contradiction_id"]] = ContradictionRecord(
                payload["contradiction_id"], payload["hypothesis_id"], payload["domain_id"],
                tuple(payload["supporting_evidence_ids"]), tuple(payload["contradicting_evidence_ids"]),
            )
        elif entry.event_type == "contradiction_status_changed":
            existing = contradictions[entry.payload["contradiction_id"]]
            contradictions[existing.contradiction_id] = replace(existing, status=entry.payload["new_status"])
    return HypothesisGraph(tuple(edges.values()), tuple(links.values()), tuple(contradictions.values()))


def rebuild_memory_index(path: Path) -> ResearchMemoryIndex:
    """Replay the journal into a `ResearchMemoryIndex`. Disposable, never authoritative."""
    evidence: dict[str, DomainEvidence] = {}
    domains: dict[str, ResearchDomain] = {}
    open_anomalies: dict[str, str] = {}
    open_accidents: dict[str, str] = {}
    for entry in read_journal(path):
        if entry.event_type == "domain_registered":
            domains[entry.record_id] = _domain_from_canonical(entry.payload)
        elif entry.event_type == "domain_evidence_recorded":
            payload = entry.payload
            evidence[payload["evidence_id"]] = DomainEvidence(
                payload["evidence_id"], payload["hypothesis_id"], payload["domain_id"], payload["arm_id"],
                payload["seal_id"], payload["relation"], tuple(payload["observation_ids"]),
                payload["intended_spec_digest"], payload["executed_spec_digest"],
                payload["valid_for_hypothesis"], payload["invalid_reason"],
            )
        elif entry.event_type == "anomaly_recorded":
            open_anomalies[entry.payload["anomaly_id"]] = entry.payload["status"]
        elif entry.event_type == "anomaly_status_changed":
            open_anomalies[entry.payload["anomaly_id"]] = entry.payload["new_status"]
        elif entry.event_type == "accident_recorded":
            open_accidents[entry.payload["accident_id"]] = "unresolved"
        elif entry.event_type == "accident_status_changed":
            open_accidents[entry.payload["accident_id"]] = entry.payload["new_status"]
    graph = rebuild_hypothesis_graph(path)
    return ResearchMemoryIndex(
        tuple(evidence.values()), tuple(domains.values()), graph.edges, graph.contradictions,
        tuple(sorted(k for k, v in open_anomalies.items() if v not in ("explained",))),
        tuple(sorted(k for k, v in open_accidents.items() if v not in ("resolved",))),
    )


def _domain_from_canonical(payload: Mapping[str, object]) -> ResearchDomain:
    from .research_domain import ExactConstraint, IntegerRangeConstraint, SetConstraint
    constraints = []
    for raw in payload["constraints"]:
        if raw["kind"] == "exact":
            constraints.append(ExactConstraint(raw["axis"], raw["value"]))
        elif raw["kind"] == "set":
            constraints.append(SetConstraint(raw["axis"], tuple(raw["values"])))
        elif raw["kind"] == "range":
            constraints.append(IntegerRangeConstraint(raw["axis"], raw["minimum"], raw["maximum"]))
        else:
            raise ValueError(f"unsupported constraint kind {raw['kind']!r}")
    return ResearchDomain(payload["domain_id"], tuple(constraints), payload["description"])


def rebuild_research_state(path: Path) -> ResearchState:
    active: dict[str, str] = {}
    open_anomalies: dict[str, str] = {}
    open_accidents: dict[str, str] = {}
    domains_seen: set[str] = set()
    last_sequence = -1
    domain_registered: set[str] = set()
    domain_tested: set[str] = set()
    for entry in read_journal(path):
        last_sequence = entry.sequence
        if entry.event_type == "hypothesis_set_created":
            for hypothesis in entry.payload["hypotheses"]:
                active[hypothesis["hypothesis_id"]] = hypothesis["status"]
                domains_seen.update(hypothesis["applicability_conditions"])
        elif entry.event_type == "hypothesis_status_changed":
            active[entry.payload["hypothesis_id"]] = entry.payload["new_status"]
        elif entry.event_type == "anomaly_recorded":
            open_anomalies[entry.payload["anomaly_id"]] = entry.payload["status"]
        elif entry.event_type == "anomaly_status_changed":
            open_anomalies[entry.payload["anomaly_id"]] = entry.payload["new_status"]
        elif entry.event_type == "accident_recorded":
            open_accidents[entry.payload["accident_id"]] = "unresolved"
        elif entry.event_type == "accident_status_changed":
            open_accidents[entry.payload["accident_id"]] = entry.payload["new_status"]
        elif entry.event_type == "domain_registered":
            domain_registered.add(entry.record_id)
        elif entry.event_type == "domain_evidence_recorded":
            domain_tested.add(entry.payload["domain_id"])

    graph = rebuild_hypothesis_graph(path)
    memory = rebuild_memory_index(path)
    evidence_status: dict[str, str] = {}
    lifecycle_status: dict[str, str] = {}
    unresolved_contradictions: list[tuple[str, str]] = []
    for hypothesis_id in active:
        assessment = derive_hypothesis_assessment(
            hypothesis_id, memory.evidence_for_hypothesis(hypothesis_id), graph.edges, graph.contradictions,
        )
        evidence_status[hypothesis_id] = assessment.evidence_status
        lifecycle_status[hypothesis_id] = assessment.lifecycle_status
        for contradiction_id in assessment.contradiction_ids:
            if graph.contradictions_for(hypothesis_id):
                for contradiction in graph.contradictions_for(hypothesis_id):
                    if contradiction.contradiction_id == contradiction_id and contradiction.status == "unresolved":
                        unresolved_contradictions.append((hypothesis_id, contradiction_id))

    domain_status = {domain_id: ("tested" if domain_id in domain_tested else "untested")
                     for domain_id in domain_registered}
    open_anomaly_ids = tuple(sorted(k for k, v in open_anomalies.items() if v not in ("explained",)))
    open_accident_ids = tuple(sorted(k for k, v in open_accidents.items() if v not in ("resolved",)))

    return ResearchState(
        tuple(sorted(active)), dict(active), open_anomaly_ids, open_accident_ids,
        tuple(sorted(domains_seen)), tuple(sorted(unresolved_contradictions)), None, last_sequence,
        evidence_status, lifecycle_status, domain_status, dict(open_anomalies), dict(open_accidents),
    )
