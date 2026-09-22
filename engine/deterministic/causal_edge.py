"""CausalEdge, CausalPath, and the states a causal claim moves through -- never PROVEN, always revisable.

Names follow docs/README/B0.6's semantic contract but use this codebase's
existing status vocabulary where it already fits (`hypothesis_assessment.py`
already distinguishes "what the evidence shows" from "what happened to the
claim's standing" -- the same split applies here between `EdgeStatus` and
the raw evidence a `PathEvidenceBundle` carries).

An edge is never deleted when contradicted (section 12): contradicting
evidence is *added* to the same edge's bundle, and only the status field
moves. A `CausalPath`'s status is never stronger than its weakest edge
(section 23) -- `path_status` computes that directly rather than storing an
independent value a caller could set inconsistently.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .causal_graph_model import CausalCondition, PathEvidenceBundle

FORMAT = "causal-edge-v1"

EDGE_STATUSES = frozenset({"PROPOSED", "SUPPORTED", "STRONGLY_SUPPORTED", "CONTRADICTED", "UNRESOLVED"})
_STATUS_STRENGTH = {"CONTRADICTED": 0, "UNRESOLVED": 1, "PROPOSED": 2, "SUPPORTED": 3, "STRONGLY_SUPPORTED": 4}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def derive_edge_status(
    has_observation: bool, has_intervention: bool, has_contradiction: bool,
    independent_supporting_domain_count: int,
) -> str:
    """The one place edge status is computed -- never set directly by a caller.

    Rules, in order (docs/README sections 6, 11, 12, 28 -- no vote-counting,
    no percentage-of-truth):
    - any contradiction alongside support -> UNRESOLVED (mixed evidence)
    - contradiction with no supporting evidence at all -> CONTRADICTED
    - intervention evidence, no contradiction, repeated across >= 3
      independently-varied domains -> STRONGLY_SUPPORTED
    - intervention evidence, no contradiction -> SUPPORTED
    - observation evidence only, no intervention -> PROPOSED
    """
    if has_contradiction and (has_observation or has_intervention):
        return "UNRESOLVED"
    if has_contradiction:
        return "CONTRADICTED"
    if has_intervention and independent_supporting_domain_count >= 3:
        return "STRONGLY_SUPPORTED"
    if has_intervention:
        return "SUPPORTED"
    if has_observation:
        return "PROPOSED"
    raise ValueError("an edge needs at least observation or intervention evidence to derive a status")


@dataclass(frozen=True)
class CausalEdge:
    """One causal connection: source -> target, optionally under a condition, backed by a PathEvidenceBundle.

    `status` is always the output of `derive_edge_status` applied to
    `evidence` -- constructors in `causal_path_builder.py` compute it that
    way rather than accepting an arbitrary caller-supplied value.
    """
    edge_id: str
    source_node_id: str
    target_node_id: str
    condition: CausalCondition | None
    evidence: PathEvidenceBundle
    status: str

    def __post_init__(self) -> None:
        _text(self.edge_id, "edge_id")
        _text(self.source_node_id, "source_node_id")
        _text(self.target_node_id, "target_node_id")
        if self.status not in EDGE_STATUSES:
            raise ValueError(f"unsupported edge status {self.status!r}")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {"edge_id": self.edge_id, "evidence": self.evidence.canonical(), "format": FORMAT,
                  "source_node_id": self.source_node_id, "status": self.status,
                  "target_node_id": self.target_node_id}
        if self.condition is not None:
            result["condition"] = self.condition.canonical()
        return result


@dataclass(frozen=True, order=True)
class MissingLink:
    """`A -> ? -> C`: current evidence cannot explain the middle, not a claim that a hidden variable exists.

    Exactly the honest gap docs/README section 25 requires: this node
    records that a connection could not be built between `source_node_id`
    and `target_node_id`, given the evidence available -- not why.
    """
    source_node_id: str
    target_node_id: str
    reason: str

    def __post_init__(self) -> None:
        _text(self.source_node_id, "source_node_id")
        _text(self.target_node_id, "target_node_id")
        _text(self.reason, "reason")

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "reason": self.reason, "source_node_id": self.source_node_id,
                "target_node_id": self.target_node_id}


def path_status(edge_statuses: tuple[str, ...]) -> str:
    """A path's status is its weakest edge's status -- never stronger (docs/README section 23)."""
    if not edge_statuses:
        raise ValueError("a path needs at least one edge to derive a status")
    return min(edge_statuses, key=lambda status: _STATUS_STRENGTH[status])


@dataclass(frozen=True)
class CausalPath:
    """An ordered chain of edges, or a partial chain with `MissingLink`s where evidence runs out.

    `edge_ids` and `missing_links` are both allowed to be non-empty at once
    (docs/README section 24: partial paths are not a failure).
    """
    path_id: str
    edge_ids: tuple[str, ...]
    missing_links: tuple[MissingLink, ...]
    status: str

    def __post_init__(self) -> None:
        _text(self.path_id, "path_id")
        if not self.edge_ids and not self.missing_links:
            raise ValueError("a path needs at least one edge or missing link")
        if self.status not in EDGE_STATUSES:
            raise ValueError(f"unsupported path status {self.status!r}")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"edge_ids": list(self.edge_ids), "format": FORMAT,
                "missing_links": [x.canonical() for x in sorted(self.missing_links)],
                "path_id": self.path_id, "status": self.status}
