"""The single gate every proposed causal edge passes through, whether proposed automatically or by request.

Both `build_from_evidence` (automatic discovery) and
`evaluate_requested_relation` (a caller asking B0.6 to examine one specific
relation) end here: neither path is allowed to register an edge without
going through `validate_relation` first. This is what keeps "human asked
for it" from becoming a second, laxer way to create unsupported causal
claims (docs/README's insistence that a manual request only elevates
something to "worth reviewing", never straight to a stored edge).
"""
from __future__ import annotations

from dataclasses import dataclass

from .causal_graph_model import CausalNode
from .research_domain import ResearchDomain


@dataclass(frozen=True)
class RelationRejection:
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be non-empty text")


def validate_relation(
    source: CausalNode, target: CausalNode,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    same_atomic_event: bool, has_evidence: bool,
) -> RelationRejection | None:
    """Check the minimum conditions docs/README section 8 requires. Returns None if the edge may proceed.

    Deliberately does not check evidence *quality* (observation vs.
    intervention, contradiction, domain independence) -- that is
    `derive_edge_status`'s job once an edge is known to be legally
    constructible at all. This function only answers "can this connection
    exist as stated", not "how strong is it".
    """
    if source.node_id == target.node_id:
        return RelationRejection("a causal edge cannot connect a node to itself")
    if same_atomic_event:
        return RelationRejection(
            "source and target were observed together in the same (tick, phase) atomic event; "
            "ordering them would invent a sequence the evidence does not support -- "
            "record them as siblings of an AtomicPhaseEvent instead")
    if not source_domain.overlaps(target_domain):
        return RelationRejection(
            f"source domain {source_domain.domain_id!r} and target domain {target_domain.domain_id!r} "
            "do not overlap -- the two observations were never made under compatible conditions")
    if not has_evidence:
        return RelationRejection("no observation or intervention evidence was supplied for this relation")
    return None


def can_chain(
    first_target: CausalNode, second_source: CausalNode,
    first_domain: ResearchDomain, second_domain: ResearchDomain,
) -> RelationRejection | None:
    """Check docs/README section 21's conditions for joining `A -> B` and `B -> C` into `A -> B -> C`.

    The two edges' middle node must be the *same* node (same type, role,
    field, domain -- `CausalNode.node_id` already encodes all of that, so
    identity is a direct id comparison, not a heuristic "looks similar"
    check) and their domains must overlap for the chain to mean anything.
    """
    if first_target.node_id != second_source.node_id:
        return RelationRejection(
            "the first edge's target and the second edge's source are not the same node -- "
            "same-looking names or fields in different domains/roles are not the same causal subject")
    if not first_domain.overlaps(second_domain):
        return RelationRejection("the two edges' domains do not overlap; chaining them would mix incompatible conditions")
    return None
