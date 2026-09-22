"""The vocabulary B0.7 uses to describe why a CausalPath has an unexplained gap.

Fixed as a closed type contract now (docs/README's B0.7 design: "the type
contract is finished now, even though not every kind gets a full automatic
search this round") because these eight kinds are what gets journaled,
canonicalized, and replayed -- adding a ninth later is fine, but the meaning
of these eight must not shift under existing journals.

None of these types claim a hidden variable exists. `MISSING_LINK_KINDS`
lists *possible explanations* for an unexplained gap, one of which
(`EXISTING_STATE_MEDIATOR`) happens to be "an already-known state might be
the mediator" -- never "there is definitely a hidden cause". A hypothesis
never reaches a final truth state on its own; `RESOLVED` only happens via
`missing_link_investigator.py` sending new evidence back through
`causal_path_builder.py` and finding the gap actually closed there.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "missing-link-hypothesis-v1"

MISSING_LINK_KINDS = frozenset({
    "EXISTING_EVIDENCE_MISSED",   # evidence already recorded, just not used by B0.6
    "OBSERVATION_GAP",            # observation resolution is too coarse
    "EXISTING_STATE_MEDIATOR",    # an already-observable value may be the mediator
    "DERIVED_RELATION",           # a combination of existing values may matter more than either alone
    "CONDITIONAL_RELATION",       # the relation may hold only under some condition
    "DIRECT_RELATION",            # no mediator needed -- A may act on C directly
    "PARENT_RELATION_WRONG",      # the original A -> C relation itself may not hold
    "UNKNOWN",                    # none of the above currently explain the gap
})

HYPOTHESIS_STATUSES = frozenset({
    "PROPOSED", "TESTABLE", "INVESTIGATION_REQUESTED", "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "BLOCKED",
})

MISSING_LINK_STATUSES = frozenset({
    "RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED", "BLOCKED", "PARENT_RELATION_REJECTED", "BUDGET_EXHAUSTED",
})

# Investigation order docs/README fixes: cheapest checks first. Not a truth
# ranking -- a later kind is not "less likely", only "more expensive to check".
INVESTIGATION_ORDER = (
    "EXISTING_EVIDENCE_MISSED", "OBSERVATION_GAP", "EXISTING_STATE_MEDIATOR",
    "DERIVED_RELATION", "CONDITIONAL_RELATION", "DIRECT_RELATION", "PARENT_RELATION_WRONG", "UNKNOWN",
)


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


@dataclass(frozen=True)
class MissingLinkInvestigation:
    """Seals which gap is under investigation, before any hypothesis is proposed.

    Mirrors `investigation_target.InvestigationTarget`'s discipline: what is
    being investigated is fixed first, then hypotheses are proposed against it.
    """
    investigation_id: str
    missing_link_source_node_id: str
    missing_link_target_node_id: str
    domain_id: str
    evidence_version: str

    def __post_init__(self) -> None:
        for field_name in ("investigation_id", "missing_link_source_node_id", "missing_link_target_node_id",
                          "domain_id", "evidence_version"):
            _text(getattr(self, field_name), field_name)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"domain_id": self.domain_id, "evidence_version": self.evidence_version, "format": FORMAT,
                "investigation_id": self.investigation_id,
                "missing_link_source_node_id": self.missing_link_source_node_id,
                "missing_link_target_node_id": self.missing_link_target_node_id}


@dataclass(frozen=True, order=True)
class MissingLinkHypothesis:
    """One candidate explanation for why a CausalPath's gap is unexplained.

    `detail` carries kind-specific structured data (e.g. an
    `EXISTING_STATE_MEDIATOR` hypothesis's candidate node id, a
    `DERIVED_RELATION` hypothesis's `DerivedFeatureCandidate` id) --
    `missing_link_hypothesis.py` itself stays agnostic to what a kind's
    detail contains, so new kinds never require changing this type.
    """
    hypothesis_id: str
    investigation_id: str
    kind: str
    detail: dict
    status: str = "PROPOSED"

    def __post_init__(self) -> None:
        _text(self.hypothesis_id, "hypothesis_id")
        _text(self.investigation_id, "investigation_id")
        if self.kind not in MISSING_LINK_KINDS:
            raise ValueError(f"unsupported missing link hypothesis kind {self.kind!r}")
        if not isinstance(self.detail, dict):
            raise ValueError("detail must be an object")
        if self.status not in HYPOTHESIS_STATUSES:
            raise ValueError(f"unsupported hypothesis status {self.status!r}")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"detail": dict(sorted(self.detail.items())), "format": FORMAT,
                "hypothesis_id": self.hypothesis_id, "investigation_id": self.investigation_id,
                "kind": self.kind, "status": self.status}


@dataclass(frozen=True)
class MissingLinkResult:
    """The outcome of one investigation cycle -- never self-declared RESOLVED (see this module's docstring)."""
    investigation_id: str
    status: str
    hypothesis_ids: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        _text(self.investigation_id, "investigation_id")
        if self.status not in MISSING_LINK_STATUSES:
            raise ValueError(f"unsupported missing link status {self.status!r}")
        _texts(self.hypothesis_ids, "hypothesis_ids")
        _text(self.reason, "reason")

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "hypothesis_ids": list(self.hypothesis_ids), "investigation_id": self.investigation_id,
                "reason": self.reason, "status": self.status}
