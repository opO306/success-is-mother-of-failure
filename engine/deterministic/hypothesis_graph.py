"""Hypothesis lineage, domain links, and contradictions as edges, not mirrored fields.

`CausalHypothesis.parent_hypothesis_ids`/`child_hypothesis_ids` are kept for
backward compatibility with the B0.1 journal and are not touched, but they are
no longer the authoritative source of lineage: storing a relation on both
ends invites the two records disagreeing about it. From B0.2 on, an edge is
recorded once and read from both directions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "hypothesis-graph-v1"

EDGE_RELATIONS = frozenset({
    "derived_into", "specialized_into", "generalized_into",
    "superseded_by", "incompatible_with", "recombined_into",
})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True, order=True)
class HypothesisEdge:
    edge_id: str
    source_hypothesis_id: str
    target_hypothesis_id: str
    relation: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.edge_id, "edge_id")
        _text(self.source_hypothesis_id, "source_hypothesis_id")
        _text(self.target_hypothesis_id, "target_hypothesis_id")
        if self.source_hypothesis_id == self.target_hypothesis_id:
            raise ValueError("a hypothesis edge cannot join a hypothesis to itself")
        if self.relation not in EDGE_RELATIONS:
            raise ValueError(f"unsupported hypothesis edge relation {self.relation!r}")
        _texts(self.evidence_ids, "evidence_ids")

    def canonical(self) -> dict[str, object]:
        return {"edge_id": self.edge_id, "evidence_ids": list(self.evidence_ids), "format": FORMAT,
                "relation": self.relation, "source_hypothesis_id": self.source_hypothesis_id,
                "target_hypothesis_id": self.target_hypothesis_id}


@dataclass(frozen=True, order=True)
class HypothesisDomainLink:
    """Names which `ResearchDomain` a hypothesis's applicability targets.

    Kept separate from `CausalHypothesis.applicability_conditions`, which
    stays a human-readable description. This link is the machine-checkable
    counterpart, added without touching `causal-hypothesis-v1`'s digest.
    """
    hypothesis_id: str
    domain_id: str
    role: str

    def __post_init__(self) -> None:
        _text(self.hypothesis_id, "hypothesis_id")
        _text(self.domain_id, "domain_id")
        if self.role != "applicability":
            raise ValueError("unsupported hypothesis-domain link role")

    def canonical(self) -> dict[str, object]:
        return {"domain_id": self.domain_id, "format": FORMAT,
                "hypothesis_id": self.hypothesis_id, "role": self.role}


@dataclass(frozen=True, order=True)
class ContradictionRecord:
    """Two pieces of evidence for the same hypothesis, in overlapping domains, disagree.

    Causal A is deterministic: identical states must produce identical
    results, so a contradiction is never quietly folded into `conditional`.
    It is preserved as its own record and its `status` tracks investigation
    separately (see `research_loop.update_contradiction_status`).
    """
    contradiction_id: str
    hypothesis_id: str
    domain_id: str
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    status: str = "unresolved"

    def __post_init__(self) -> None:
        _text(self.contradiction_id, "contradiction_id")
        _text(self.hypothesis_id, "hypothesis_id")
        _text(self.domain_id, "domain_id")
        _texts(self.supporting_evidence_ids, "supporting_evidence_ids")
        _texts(self.contradicting_evidence_ids, "contradicting_evidence_ids")
        if not self.supporting_evidence_ids or not self.contradicting_evidence_ids:
            raise ValueError("a contradiction needs at least one supporting and one contradicting evidence id")
        if self.status not in ("unresolved", "explained_by_accident", "explained_by_hidden_variable",
                               "explained_by_bug", "irreducible"):
            raise ValueError("unsupported contradiction status")

    def canonical(self) -> dict[str, object]:
        return {"contradicting_evidence_ids": list(self.contradicting_evidence_ids),
                "contradiction_id": self.contradiction_id, "domain_id": self.domain_id, "format": FORMAT,
                "hypothesis_id": self.hypothesis_id, "status": self.status,
                "supporting_evidence_ids": list(self.supporting_evidence_ids)}


@dataclass(frozen=True)
class HypothesisGraph:
    """The full lineage/domain/contradiction graph, rebuilt from the journal like `ResearchState`."""
    edges: tuple[HypothesisEdge, ...]
    domain_links: tuple[HypothesisDomainLink, ...]
    contradictions: tuple[ContradictionRecord, ...]

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"contradictions": [x.canonical() for x in sorted(self.contradictions)],
                "domain_links": [x.canonical() for x in sorted(self.domain_links)],
                "edges": [x.canonical() for x in sorted(self.edges)], "format": FORMAT}

    def children_of(self, hypothesis_id: str) -> tuple[HypothesisEdge, ...]:
        return tuple(sorted(e for e in self.edges if e.source_hypothesis_id == hypothesis_id))

    def parents_of(self, hypothesis_id: str) -> tuple[HypothesisEdge, ...]:
        return tuple(sorted(e for e in self.edges if e.target_hypothesis_id == hypothesis_id))

    def domains_for(self, hypothesis_id: str) -> tuple[str, ...]:
        return tuple(sorted({link.domain_id for link in self.domain_links if link.hypothesis_id == hypothesis_id}))

    def contradictions_for(self, hypothesis_id: str) -> tuple[ContradictionRecord, ...]:
        return tuple(sorted(c for c in self.contradictions if c.hypothesis_id == hypothesis_id))

    def is_superseded(self, hypothesis_id: str) -> bool:
        return any(e.relation == "superseded_by" for e in self.parents_of(hypothesis_id))

    def is_incompatible(self, hypothesis_id: str) -> bool:
        return any(e.relation == "incompatible_with"
                  for e in self.edges if hypothesis_id in (e.source_hypothesis_id, e.target_hypothesis_id))
