"""Pure epistemic rules: evidence in, hypothesis status out.

This module imports nothing that touches storage or execution -- no
`ResearchJournal`, no `ResearchState`, no `Path`, no `AExecutor`, no causal
kernel. It receives only immutable evidence, edges, and contradictions, and
returns a status. That boundary is deliberate: as B's rules for what counts
as "supported" grow more nuanced, they belong here, as testable pure
functions, not scattered through journal-replay code.

`evidence_status` and `lifecycle_status` are kept separate because they are
different kinds of fact. Evidence status answers "what has been observed
about this claim". Lifecycle status answers "is this hypothesis still the
one B is tracking" (a hypothesis can be `superseded_by` a better one while
still being, on the evidence alone, `supported`). `effective_status` is what
callers usually want: lifecycle wins when it applies, evidence status
otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hypothesis_graph import ContradictionRecord, HypothesisEdge
from .research_memory import DomainEvidence
from .research_state import HYPOTHESIS_STATUSES

_LIFECYCLE_STATUSES = frozenset({"active", "superseded", "incompatible"})


def derive_evidence_status(evidence: tuple[DomainEvidence, ...]) -> str:
    """Fold a hypothesis's evidence into one of the B0.1 evidence-facing statuses.

    Rules, in order:
    - no valid evidence at all -> untested
    - only underspecified evidence -> underspecified
    - support and contradiction share a domain -> conditional (a
      `ContradictionRecord` should also exist for that case; this function
      does not create one, `research_loop` does)
    - support and contradiction in different domains -> conditional
    - contradiction only -> contradicted_in_domain
    - support only -> supported
    Evidence with `valid_for_hypothesis=False` (accidents) is ignored.
    """
    usable = tuple(item for item in evidence if item.valid_for_hypothesis)
    if not usable:
        return "untested"
    supporting_domains = {item.domain_id for item in usable if item.relation == "supports"}
    contradicting_domains = {item.domain_id for item in usable if item.relation == "contradicts"}
    has_underspecified = any(item.relation == "underspecified" for item in usable)
    if supporting_domains and contradicting_domains:
        return "conditional"
    if contradicting_domains:
        return "contradicted_in_domain"
    if supporting_domains:
        return "supported"
    if has_underspecified:
        return "underspecified"
    return "untested"


def derive_lifecycle_status(hypothesis_id: str, edges: tuple[HypothesisEdge, ...]) -> str:
    """A hypothesis is `superseded` or `incompatible` only via an explicit edge naming it."""
    for edge in edges:
        if edge.target_hypothesis_id == hypothesis_id and edge.relation == "superseded_by":
            return "superseded"
    for edge in edges:
        if edge.relation == "incompatible_with" and hypothesis_id in (
            edge.source_hypothesis_id, edge.target_hypothesis_id,
        ):
            return "incompatible"
    return "active"


def derive_effective_status(evidence_status: str, lifecycle_status: str) -> str:
    """What API callers who want one status should read: lifecycle overrides evidence."""
    if lifecycle_status == "superseded":
        return "superseded"
    if lifecycle_status == "incompatible":
        return "incompatible"
    return evidence_status


@dataclass(frozen=True)
class HypothesisAssessment:
    hypothesis_id: str
    evidence_status: str
    lifecycle_status: str
    effective_status: str
    supporting_domain_ids: tuple[str, ...]
    contradicting_domain_ids: tuple[str, ...]
    underspecified_domain_ids: tuple[str, ...]
    contradiction_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.evidence_status not in HYPOTHESIS_STATUSES:
            raise ValueError(f"unsupported evidence_status {self.evidence_status!r}")
        if self.lifecycle_status not in _LIFECYCLE_STATUSES:
            raise ValueError(f"unsupported lifecycle_status {self.lifecycle_status!r}")

    def canonical(self) -> dict[str, object]:
        return {"contradiction_ids": list(self.contradiction_ids),
                "contradicting_domain_ids": list(self.contradicting_domain_ids),
                "effective_status": self.effective_status, "evidence_status": self.evidence_status,
                "hypothesis_id": self.hypothesis_id, "lifecycle_status": self.lifecycle_status,
                "supporting_domain_ids": list(self.supporting_domain_ids),
                "underspecified_domain_ids": list(self.underspecified_domain_ids)}


def derive_hypothesis_assessment(
    hypothesis_id: str, evidence: tuple[DomainEvidence, ...], edges: tuple[HypothesisEdge, ...],
    contradictions: tuple[ContradictionRecord, ...],
) -> HypothesisAssessment:
    usable = tuple(item for item in evidence if item.hypothesis_id == hypothesis_id and item.valid_for_hypothesis)
    evidence_status = derive_evidence_status(tuple(item for item in evidence if item.hypothesis_id == hypothesis_id))
    lifecycle_status = derive_lifecycle_status(hypothesis_id, edges)
    return HypothesisAssessment(
        hypothesis_id, evidence_status, lifecycle_status,
        derive_effective_status(evidence_status, lifecycle_status),
        tuple(sorted({item.domain_id for item in usable if item.relation == "supports"})),
        tuple(sorted({item.domain_id for item in usable if item.relation == "contradicts"})),
        tuple(sorted({item.domain_id for item in usable if item.relation == "underspecified"})),
        tuple(sorted(item.contradiction_id for item in contradictions if item.hypothesis_id == hypothesis_id)),
    )
