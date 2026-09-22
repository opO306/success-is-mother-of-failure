"""B0.6 core vocabulary: nodes, conditions, atomic co-occurring events, and evidence bundles.

Everything in this module is immutable data with canonical()/digest, exactly
like B0.1-B0.5's types -- a `CausalNode`'s id is derived deterministically
from its (type, role, field, domain_id) so the same subject in the same
domain always identifies the same way, without binding to a run's ephemeral
particle ids (docs/README/B0.6 section 34).

`AtomicPhaseEvent` exists specifically to prevent the failure mode the
design doc calls out repeatedly (sections 4/16/17/43): when several fields
diverge in the very same `(tick, phase)`, B0.6 must record them as siblings
under one common event, never as an invented A -> B -> C chain the observed
data does not actually support.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .causal_kernel import KernelPhase

FORMAT = "causal-graph-model-v1"
NODE_TYPES = frozenset({"control", "state", "condition", "event", "outcome"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


@dataclass(frozen=True, order=True)
class CausalNode:
    """A causal subject: something changed (a control), something A holds (a state), or a final outcome.

    `node_id` is derived from (node_type, role, field, domain_id) rather than
    assigned, so building the same node twice from the same inputs always
    yields the same id -- required for `build_from_evidence` to be
    idempotent (section 36's determinism requirement) and for two worlds'
    same-named-but-different-role fields to stay distinct (section 22).
    """
    node_type: str
    role: str
    field: str
    domain_id: str

    def __post_init__(self) -> None:
        if self.node_type not in NODE_TYPES:
            raise ValueError(f"unsupported causal node type {self.node_type!r}")
        _text(self.role, "role")
        _text(self.field, "field")
        _text(self.domain_id, "domain_id")

    @property
    def node_id(self) -> str:
        return f"NODE-{_digest(self.canonical())[:16]}"

    def canonical(self) -> dict[str, object]:
        return {"domain_id": self.domain_id, "field": self.field, "format": FORMAT,
                "node_type": self.node_type, "role": self.role}


@dataclass(frozen=True, order=True)
class CausalCondition:
    """A relation between values that must hold for an edge to apply -- e.g. `heat >= break_heat`.

    `expression` is a short, human-readable statement of the relation (the
    design doc explicitly allows this to stay a controlled-vocabulary
    string rather than a full expression AST for B0.6's scope); `axis_ids`
    names the registered research axes it references, so the condition can
    be checked for domain compatibility without re-parsing the expression.
    """
    condition_id: str
    expression: str
    axis_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.condition_id, "condition_id")
        _text(self.expression, "expression")
        _texts(self.axis_ids, "axis_ids", allow_empty=False)

    def canonical(self) -> dict[str, object]:
        return {"axis_ids": list(self.axis_ids), "condition_id": self.condition_id,
                "expression": self.expression, "format": FORMAT}


@dataclass(frozen=True, order=True)
class AtomicPhaseEvent:
    """Several (role, field) effects observed together at one instant -- siblings, not a chain.

    This is the structural answer to "the kernel changed heat, the bond, and
    the particles' energy all inside `AFTER_BOND_BREAK_PHASE`": rather than
    picking an arbitrary internal order, every affected node points *from*
    this one shared event, and nothing here claims any ordering among them.

    `observation_seq` is the real time coordinate (see `trace_model.TraceSnapshot`
    and `causal_timeline.py` on why `(tick, phase)` cannot serve that role);
    `tick`/`phase` are kept as descriptive metadata only.
    """
    observation_seq: int
    tick: int
    phase: KernelPhase
    effect_node_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.observation_seq, bool) or not isinstance(self.observation_seq, int) or self.observation_seq < 0:
            raise ValueError("observation_seq must be a nonnegative integer")
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        _texts(self.effect_node_ids, "effect_node_ids", allow_empty=False)

    @property
    def event_id(self) -> str:
        return f"EVENT-{_digest(self.canonical())[:16]}"

    def canonical(self) -> dict[str, object]:
        return {"effect_node_ids": sorted(self.effect_node_ids), "format": FORMAT,
                "observation_seq": self.observation_seq, "phase": self.phase.value, "tick": self.tick}


@dataclass(frozen=True)
class PathEvidenceBundle:
    """Every piece of evidence backing one causal edge, referenced by id -- never copied.

    Section 19's requirement: no original evidence is duplicated into B0.6's
    own records. `observation_evidence_ids` typically point at
    `DivergenceEvent`/`DivergenceChain` data (B0.4), `intervention_evidence_ids`
    at `MechanismEvidence` records (B0.5).
    """
    observation_evidence_ids: tuple[str, ...]
    intervention_evidence_ids: tuple[str, ...]
    contradiction_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _texts(self.observation_evidence_ids, "observation_evidence_ids")
        _texts(self.intervention_evidence_ids, "intervention_evidence_ids")
        _texts(self.contradiction_evidence_ids, "contradiction_evidence_ids")
        if not self.observation_evidence_ids and not self.intervention_evidence_ids:
            raise ValueError("a causal edge needs at least one observation or intervention evidence id")

    def canonical(self) -> dict[str, object]:
        return {"contradiction_evidence_ids": sorted(self.contradiction_evidence_ids), "format": FORMAT,
                "intervention_evidence_ids": sorted(self.intervention_evidence_ids),
                "observation_evidence_ids": sorted(self.observation_evidence_ids)}
