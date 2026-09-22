"""B0.7 Missing Link Investigator: decompose a CausalPath gap into checkable hypotheses, cheapest first.

Takes the `MissingLink`s a `CausalPath` (B0.6) already carries as its input
-- B0.7 never invents a gap on its own, it investigates the ones B0.6 could
not close. For each gap, it runs the fixed, cheapest-first investigation
order docs/README fixes:

    EXISTING_EVIDENCE_MISSED -> OBSERVATION_GAP -> EXISTING_STATE_MEDIATOR
    -> DERIVED_RELATION -> CONDITIONAL_RELATION -> DIRECT_RELATION
    -> PARENT_RELATION_WRONG -> UNKNOWN

Per the confirmed scope: the first three and the last two kinds
(EXISTING_EVIDENCE_MISSED, OBSERVATION_GAP, EXISTING_STATE_MEDIATOR,
DIRECT_RELATION, PARENT_RELATION_WRONG, UNKNOWN) have real check logic here.
DERIVED_RELATION and CONDITIONAL_RELATION get only a narrow, budget-limited
candidate generator this round -- not open-ended feature search.

B0.7 never modifies a CausalPath directly (docs/README's core boundary):
its output is hypotheses and follow-up requests for B0.4/B0.5, which in
turn produce new evidence that flows back through `causal_path_builder.py`.
Whether a gap actually became RESOLVED is judged there, never declared here.
"""
from __future__ import annotations

from dataclasses import dataclass

from .causal_edge import CausalEdge, CausalPath, MissingLink
from .causal_edge_validator import validate_relation
from .causal_graph_model import CausalNode
from .causal_timeline import AtomicChangeGroup
from .derived_feature import DerivedFeatureCandidate, ObservableRef, candidate_relevant_to_gap
from .mechanism_test import MechanismEvidence
from .missing_link_hypothesis import (
    INVESTIGATION_ORDER,
    MissingLinkHypothesis,
    MissingLinkInvestigation,
    MissingLinkResult,
)
from .observation_catalog import ObservationCatalog, assess_observation_feasibility
from .observation_request import (
    InstrumentationRequest,
    InvestigationHistory,
    MechanismTestRequest,
    ObservationGap,
    ObservationRequest,
)
from .research_domain import ResearchDomain
from .research_journal import ResearchJournal


def seal_missing_link_investigation(journal: ResearchJournal, investigation: MissingLinkInvestigation) -> MissingLinkInvestigation:
    journal.append("missing_link_investigation_sealed", investigation.investigation_id, investigation.canonical())
    return investigation


def propose_missing_link_hypothesis(journal: ResearchJournal, hypothesis: MissingLinkHypothesis) -> MissingLinkHypothesis:
    journal.append("missing_link_hypothesis_proposed", hypothesis.hypothesis_id, hypothesis.canonical())
    return hypothesis


def record_missing_link_result(journal: ResearchJournal, result: MissingLinkResult) -> MissingLinkResult:
    journal.append("missing_link_result_recorded", result.investigation_id, result.canonical())
    return result


def submit_observation_request(journal: ResearchJournal, request: ObservationRequest,
                               history: InvestigationHistory) -> tuple[ObservationRequest | None, InvestigationHistory]:
    """Journal `request` unless its fingerprint has already been submitted (docs/README section 33-34)."""
    if history.has_been_requested(request.fingerprint):
        return None, history
    journal.append("observation_request_submitted", request.request_id, request.canonical())
    return request, history.with_fingerprint(request.fingerprint)


def submit_mechanism_test_request(journal: ResearchJournal, request: MechanismTestRequest,
                                  history: InvestigationHistory) -> tuple[MechanismTestRequest | None, InvestigationHistory]:
    if history.has_been_requested(request.fingerprint):
        return None, history
    journal.append("mechanism_test_request_submitted", request.request_id, request.canonical())
    return request, history.with_fingerprint(request.fingerprint)


def submit_instrumentation_request(journal: ResearchJournal, request: InstrumentationRequest,
                                   history: InvestigationHistory) -> tuple[InstrumentationRequest | None, InvestigationHistory]:
    if history.has_been_requested(request.fingerprint):
        return None, history
    journal.append("instrumentation_request_submitted", request.request_id, request.canonical())
    return request, history.with_fingerprint(request.fingerprint)


def is_eligible_missing_link(
    link: MissingLink,
    source_has_evidence: bool, target_has_evidence: bool,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    source_not_after_target: bool,
    relation_evidence_exists: bool,
) -> bool:
    """Docs/README section 2's five minimum conditions for treating a gap as worth investigating.

    A `MissingLink` a `CausalPath` already carries can still fail these
    checks (e.g. no evidence at all connects the two ends) -- in which case
    B0.7 declines to investigate it further rather than manufacturing a
    hypothesis about an unrelated pair.
    """
    if not source_has_evidence or not target_has_evidence:
        return False
    if not source_domain.overlaps(target_domain):
        return False
    if not source_not_after_target:
        return False
    if not relation_evidence_exists:
        return False
    return True


# ---------------------------------------------------------------------------
# Investigation order, step 1: EXISTING_EVIDENCE_MISSED
# ---------------------------------------------------------------------------

def check_existing_evidence_missed(
    investigation_id: str, link: MissingLink, known_edges: tuple[CausalEdge, ...],
) -> MissingLinkHypothesis | None:
    """Is there already an edge B0.6 built that connects these two nodes but was excluded from this path?

    If B0.4/B0.5 evidence already supports `source -> target` through some
    already-registered edge that simply is not part of this `CausalPath`,
    the fix is a B0.6 re-evaluation request, never a new observation or
    experiment.
    """
    for edge in known_edges:
        if edge.source_node_id == link.source_node_id and edge.target_node_id == link.target_node_id:
            return MissingLinkHypothesis(
                f"MLH-{link.source_node_id}-{link.target_node_id}-existing", investigation_id,
                "EXISTING_EVIDENCE_MISSED",
                {"existing_edge_id": edge.edge_id, "existing_edge_status": edge.status}, "TESTABLE",
            )
    return None


# ---------------------------------------------------------------------------
# Investigation order, step 2: OBSERVATION_GAP
# ---------------------------------------------------------------------------

def check_observation_gap(
    link: MissingLink, timeline: tuple[AtomicChangeGroup, ...],
    source_role: str, target_role: str,
) -> ObservationGap | None:
    """Is the observed gap between source and target's groups wide enough to suggest coarse resolution?

    A gap of more than one consecutive `AtomicChangeGroup` between the group
    touching `source_role` and the one touching `target_role` means the
    kernel may have finer steps in between that the current `TraceSpec`
    never asked to see.
    """
    source_index = next((i for i, g in enumerate(timeline) if any(c.role == source_role for c in g.changes)), None)
    target_index = next((i for i, g in enumerate(timeline) if any(c.role == target_role for c in g.changes)), None)
    if source_index is None or target_index is None:
        return None
    if target_index - source_index <= 1:
        return None
    earlier, later = timeline[source_index], timeline[target_index]
    return ObservationGap(
        f"GAP-{link.source_node_id}-{link.target_node_id}", earlier.observation_seq, later.observation_seq,
        (source_role, target_role), (),
        f"{target_index - source_index - 1} atomic change group(s) lie between {source_role} and {target_role}'s "
        "observed reactions -- finer-grained tracing may reveal intermediate steps",
    )


# ---------------------------------------------------------------------------
# Investigation order, step 3: EXISTING_STATE_MEDIATOR
# ---------------------------------------------------------------------------

def check_existing_state_mediator(
    investigation_id: str, link: MissingLink, catalog: ObservationCatalog,
    candidate_role_kind: str, candidate_field: str,
) -> tuple[MissingLinkHypothesis, InstrumentationRequest | None]:
    """Is there an already-catalogued observable near this gap that could be the mediator?

    Checks feasibility first (docs/README sections 9-11): a mediator
    candidate whose field is not in `catalog` becomes `BLOCKED`, paired with
    an `InstrumentationRequest` -- B0.7 never invents a value A does not
    expose, and never silently drops an otherwise-plausible mediator either.
    """
    feasibility = assess_observation_feasibility(catalog, candidate_role_kind, candidate_field)
    hypothesis_id = f"MLH-{link.source_node_id}-{link.target_node_id}-{candidate_role_kind}-{candidate_field}"
    if feasibility.status == "AVAILABLE":
        return MissingLinkHypothesis(
            hypothesis_id, investigation_id, "EXISTING_STATE_MEDIATOR",
            {"candidate_field": candidate_field, "candidate_role_kind": candidate_role_kind}, "TESTABLE",
        ), None
    request = InstrumentationRequest(
        f"IR-{hypothesis_id}", investigation_id, candidate_role_kind, candidate_field,
        f"mediator candidate {candidate_role_kind}.{candidate_field} is plausible but not currently observable",
    )
    return MissingLinkHypothesis(
        hypothesis_id, investigation_id, "EXISTING_STATE_MEDIATOR",
        {"candidate_field": candidate_field, "candidate_role_kind": candidate_role_kind}, "BLOCKED",
    ), request


# ---------------------------------------------------------------------------
# Investigation order, steps 4-5: DERIVED_RELATION / CONDITIONAL_RELATION (limited candidate generation)
# ---------------------------------------------------------------------------

def propose_derived_relation_candidates(
    investigation_id: str, link: MissingLink, candidates: tuple[DerivedFeatureCandidate, ...],
    source_role: str, target_role: str, related_roles: frozenset[str],
) -> tuple[MissingLinkHypothesis, ...]:
    """Filter `candidates` by relevance (docs/README section 14) and wrap the survivors as hypotheses.

    Does not search for candidates itself -- the caller supplies the fixed,
    small set of `DerivedFeatureCandidate`s to consider (docs/README section
    13's limited operation vocabulary), this function only decides which of
    them are worth proposing for this specific gap.
    """
    relevant = [c for c in candidates if candidate_relevant_to_gap(c, source_role, target_role, related_roles)]
    return tuple(
        MissingLinkHypothesis(f"MLH-{link.source_node_id}-{link.target_node_id}-derived-{c.candidate_id}",
                              investigation_id, "DERIVED_RELATION", {"derived_feature_candidate_id": c.candidate_id},
                              "TESTABLE")
        for c in relevant
    )


def propose_conditional_relation_candidate(
    investigation_id: str, link: MissingLink, differing_role: str, differing_field: str,
    successful_value, failed_value,
) -> MissingLinkHypothesis:
    """One condition candidate: a value that differed between an experiment where the relation held and one where it did not.

    Docs/README section 17: found by comparing prior experiments' recorded
    values, never derived from a hunch. `successful_value`/`failed_value`
    are supplied by the caller, already identified as the differing values
    across two known experiments.
    """
    return MissingLinkHypothesis(
        f"MLH-{link.source_node_id}-{link.target_node_id}-conditional-{differing_role}-{differing_field}",
        investigation_id, "CONDITIONAL_RELATION",
        {"differing_field": differing_field, "differing_role": differing_role,
         "failed_value": failed_value, "successful_value": successful_value},
        "TESTABLE",
    )


# ---------------------------------------------------------------------------
# Investigation order, step 6: DIRECT_RELATION
# ---------------------------------------------------------------------------

def propose_direct_relation_hypothesis(investigation_id: str, link: MissingLink) -> MissingLinkHypothesis:
    """No mediator required -- source may act on target directly. Always a valid candidate to keep open."""
    return MissingLinkHypothesis(
        f"MLH-{link.source_node_id}-{link.target_node_id}-direct", investigation_id, "DIRECT_RELATION", {},
        "TESTABLE",
    )


# ---------------------------------------------------------------------------
# Investigation order, step 7: PARENT_RELATION_WRONG
# ---------------------------------------------------------------------------

def check_parent_relation_wrong(
    investigation_id: str, link: MissingLink, source: CausalNode, target: CausalNode,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    same_atomic_event: bool, has_evidence: bool,
) -> MissingLinkHypothesis:
    """Is the original source -> target relation itself invalid under the same rules any edge must pass?

    Re-runs `validate_relation` -- the exact gate `causal_path_builder.py`
    uses -- against the two ends. If it already fails (self-loop, same
    atomic event, non-overlapping domains, no evidence at all), the parent
    relation was never legitimate and this hypothesis starts `SUPPORTED`
    rather than merely `TESTABLE`.
    """
    rejection = validate_relation(source, target, source_domain, target_domain, same_atomic_event, has_evidence)
    status = "SUPPORTED" if rejection is not None else "TESTABLE"
    detail = {"validation_reason": rejection.reason} if rejection is not None else {}
    return MissingLinkHypothesis(
        f"MLH-{link.source_node_id}-{link.target_node_id}-parent-wrong", investigation_id, "PARENT_RELATION_WRONG",
        detail, status,
    )


# ---------------------------------------------------------------------------
# Investigation order, step 8: UNKNOWN (always the fallback)
# ---------------------------------------------------------------------------

def fallback_unknown_hypothesis(investigation_id: str, link: MissingLink) -> MissingLinkHypothesis:
    return MissingLinkHypothesis(
        f"MLH-{link.source_node_id}-{link.target_node_id}-unknown", investigation_id, "UNKNOWN",
        {}, "PROPOSED",
    )


@dataclass(frozen=True)
class MissingLinkInvestigationOutcome:
    investigation: MissingLinkInvestigation
    hypotheses: tuple[MissingLinkHypothesis, ...]
    observation_gap: ObservationGap | None
    instrumentation_requests: tuple[InstrumentationRequest, ...]

    def canonical(self) -> dict[str, object]:
        return {"hypotheses": [h.canonical() for h in self.hypotheses],
                "instrumentation_requests": [r.canonical() for r in self.instrumentation_requests],
                "investigation": self.investigation.canonical(),
                "observation_gap": self.observation_gap.canonical() if self.observation_gap is not None else None}


def investigate_missing_link(
    journal: ResearchJournal,
    investigation: MissingLinkInvestigation,
    link: MissingLink,
    known_edges: tuple[CausalEdge, ...],
    timeline: tuple[AtomicChangeGroup, ...],
    source_role: str, target_role: str,
    catalog: ObservationCatalog,
    mediator_role_kind: str, mediator_field: str,
    source_node: CausalNode, target_node: CausalNode,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    same_atomic_event: bool, has_relation_evidence: bool,
    derived_feature_candidates: tuple[DerivedFeatureCandidate, ...] = (),
    related_roles: frozenset[str] = frozenset(),
) -> MissingLinkInvestigationOutcome:
    """Run the fixed, cheapest-first investigation order and return every hypothesis this cycle proposed.

    Stops proposing further-cost hypotheses only for `EXISTING_EVIDENCE_MISSED`
    (docs/README section 5: if evidence was simply missed, the fix is a
    B0.6 re-evaluation, nothing else needs to be proposed this cycle).
    Every other step always runs, since docs/README treats these as
    independently-worth-tracking possibilities, not a single true-or-false
    branch. `derived_feature_candidates` is caller-supplied (docs/README
    section 13's limited operation vocabulary) -- this function never
    searches for candidates itself.
    """
    seal_missing_link_investigation(journal, investigation)
    investigation_id = investigation.investigation_id
    hypotheses: list[MissingLinkHypothesis] = []
    instrumentation_requests: list[InstrumentationRequest] = []

    existing = check_existing_evidence_missed(investigation_id, link, known_edges)
    if existing is not None:
        hypotheses.append(propose_missing_link_hypothesis(journal, existing))
        return MissingLinkInvestigationOutcome(investigation, tuple(hypotheses), None, ())

    observation_gap = check_observation_gap(link, timeline, source_role, target_role)

    mediator_hypothesis, mediator_request = check_existing_state_mediator(
        investigation_id, link, catalog, mediator_role_kind, mediator_field)
    hypotheses.append(propose_missing_link_hypothesis(journal, mediator_hypothesis))
    if mediator_request is not None:
        instrumentation_requests.append(mediator_request)

    hypotheses.extend(propose_missing_link_hypothesis(journal, h) for h in propose_derived_relation_candidates(
        investigation_id, link, derived_feature_candidates, source_role, target_role, related_roles))

    direct = propose_direct_relation_hypothesis(investigation_id, link)
    hypotheses.append(propose_missing_link_hypothesis(journal, direct))

    parent_wrong = check_parent_relation_wrong(investigation_id, link, source_node, target_node,
                                               source_domain, target_domain, same_atomic_event, has_relation_evidence)
    hypotheses.append(propose_missing_link_hypothesis(journal, parent_wrong))

    if not hypotheses or all(h.status == "BLOCKED" for h in hypotheses):
        hypotheses.append(propose_missing_link_hypothesis(journal, fallback_unknown_hypothesis(investigation_id, link)))

    return MissingLinkInvestigationOutcome(investigation, tuple(hypotheses), observation_gap,
                                           tuple(instrumentation_requests))
