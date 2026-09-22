"""DomainEvidence and the searchable index rebuilt from it.

`DomainEvidence` sits between a raw comparison result and a hypothesis's
status: `research_loop.compare_results` no longer writes a hypothesis status
directly, it produces evidence, and `hypothesis_assessment.py` derives status
from the accumulated evidence. `ResearchMemoryIndex` is a query surface over
that evidence plus the hypothesis graph -- like `ResearchState`, it is always
rebuilt from the journal and is never itself the source of truth. A future
SQLite cache would sit at this same layer: disposable, rebuildable, never
authoritative.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .hypothesis_graph import ContradictionRecord, HypothesisEdge
from .research_domain import ResearchDomain

FORMAT = "domain-evidence-v1"
RELATIONS = frozenset({"supports", "contradicts", "underspecified"})


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
class DomainEvidence:
    """One arm's outcome, linked to the hypothesis and domain it bears on.

    `valid_for_hypothesis=False` (with `invalid_reason` set) is how an
    accident-tainted result is preserved without letting it decide the
    hypothesis's status: `hypothesis_assessment.derive_evidence_status`
    ignores evidence where this is False.
    """
    evidence_id: str
    hypothesis_id: str
    domain_id: str
    arm_id: str
    seal_id: str
    relation: str
    observation_ids: tuple[str, ...]
    intended_spec_digest: str
    executed_spec_digest: str
    valid_for_hypothesis: bool = True
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("evidence_id", "hypothesis_id", "domain_id", "arm_id", "seal_id",
                          "intended_spec_digest", "executed_spec_digest"):
            _text(getattr(self, field_name), field_name)
        if self.relation not in RELATIONS:
            raise ValueError(f"unsupported evidence relation {self.relation!r}")
        _texts(self.observation_ids, "observation_ids")
        if not isinstance(self.valid_for_hypothesis, bool):
            raise ValueError("valid_for_hypothesis must be boolean")
        if not self.valid_for_hypothesis and not self.invalid_reason:
            raise ValueError("invalid evidence must carry invalid_reason")
        if self.valid_for_hypothesis and self.invalid_reason is not None:
            raise ValueError("valid evidence must not carry invalid_reason")

    def canonical(self) -> dict[str, object]:
        return {"arm_id": self.arm_id, "domain_id": self.domain_id, "evidence_id": self.evidence_id,
                "executed_spec_digest": self.executed_spec_digest, "format": FORMAT,
                "hypothesis_id": self.hypothesis_id, "intended_spec_digest": self.intended_spec_digest,
                "invalid_reason": self.invalid_reason, "observation_ids": list(self.observation_ids),
                "relation": self.relation, "seal_id": self.seal_id,
                "valid_for_hypothesis": self.valid_for_hypothesis}


@dataclass(frozen=True)
class ResearchMemoryIndex:
    """A structural query surface over evidence, domains, and the hypothesis graph.

    No embeddings, no free-text search: every method here is an exact,
    deterministic lookup, matching B0.2's stated scope of structural memory
    before any learned retrieval.
    """
    evidence: tuple[DomainEvidence, ...]
    domains: tuple[ResearchDomain, ...]
    edges: tuple[HypothesisEdge, ...]
    contradictions: tuple[ContradictionRecord, ...]
    open_anomaly_ids: tuple[str, ...]
    open_accident_ids: tuple[str, ...]

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"contradictions": [x.canonical() for x in sorted(self.contradictions)],
                "domains": [x.canonical() for x in sorted(self.domains, key=lambda d: d.domain_id)],
                "edges": [x.canonical() for x in sorted(self.edges)],
                "evidence": [x.canonical() for x in sorted(self.evidence)], "format": FORMAT,
                "open_accident_ids": sorted(self.open_accident_ids),
                "open_anomaly_ids": sorted(self.open_anomaly_ids)}

    def _domain_by_id(self) -> dict[str, ResearchDomain]:
        return {item.domain_id: item for item in self.domains}

    def evidence_for_hypothesis(self, hypothesis_id: str) -> tuple[DomainEvidence, ...]:
        return tuple(sorted(item for item in self.evidence if item.hypothesis_id == hypothesis_id))

    def hypotheses_in_domain(self, domain_id: str) -> tuple[str, ...]:
        return tuple(sorted({item.hypothesis_id for item in self.evidence if item.domain_id == domain_id}))

    def contradictions_for(self, hypothesis_id: str) -> tuple[ContradictionRecord, ...]:
        return tuple(sorted(c for c in self.contradictions if c.hypothesis_id == hypothesis_id))

    def children_of(self, hypothesis_id: str) -> tuple[HypothesisEdge, ...]:
        return tuple(sorted(e for e in self.edges if e.source_hypothesis_id == hypothesis_id))

    def parents_of(self, hypothesis_id: str) -> tuple[HypothesisEdge, ...]:
        return tuple(sorted(e for e in self.edges if e.target_hypothesis_id == hypothesis_id))

    def experiments_in_domain(self, domain_id: str) -> tuple[str, ...]:
        return tuple(sorted({item.arm_id for item in self.evidence if item.domain_id == domain_id}))

    def open_anomalies(self) -> tuple[str, ...]:
        return tuple(sorted(self.open_anomaly_ids))

    def accidents_for_hypothesis(self, hypothesis_id: str) -> tuple[str, ...]:
        tainted = {item.evidence_id for item in self.evidence
                  if item.hypothesis_id == hypothesis_id and not item.valid_for_hypothesis}
        return tuple(sorted(tainted))

    def failed_hypotheses_overlapping(self, domain: ResearchDomain) -> tuple[str, ...]:
        """Hypotheses contradicted in some domain that overlaps `domain`.

        This is the past-failure-reuse query docs/README/05 and 06 describe:
        given a new condition to try, find prior contradicted hypotheses
        whose failure domain overlaps it, so they can be reconsidered rather
        than re-derived from scratch.
        """
        by_domain = self._domain_by_id()
        found = set()
        for item in self.evidence:
            if item.relation != "contradicts" or not item.valid_for_hypothesis:
                continue
            candidate = by_domain.get(item.domain_id)
            if candidate is not None and candidate.overlaps(domain):
                found.add(item.hypothesis_id)
        return tuple(sorted(found))
