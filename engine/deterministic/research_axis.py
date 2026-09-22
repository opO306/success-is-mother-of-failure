"""Namespaced, registered axes a `ResearchDomain` constraint may name.

An axis id such as `"causal.collision.left_energy"` looks like a spec field
but often is not: some axes read a `CausalWorldSpec` field directly, others
are derived from an event (a specific collision this tick) or a relation
between two other axes (`energy_relation = equal`). Letting constraints name
*any* string would let a typo (`collison` for `collision`) silently open a
second, disconnected axis with no error -- so axis ids are validated against
an immutable registry instead of accepted freely. `extractor_id` is recorded
alongside each axis so a future change in what an axis *means* becomes a new
extractor version rather than a silent redefinition of the same name.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "research-axis-registry-v1"
VALUE_KINDS = frozenset({"integer", "text", "boolean"})
OPERATORS = frozenset({"eq", "range", "set"})
SOURCE_KINDS = frozenset({"spec", "state", "derived_event", "derived_relation"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class AxisDefinition:
    axis_id: str
    value_kind: str
    allowed_operators: tuple[str, ...]
    source_kind: str
    extractor_id: str

    def __post_init__(self) -> None:
        _text(self.axis_id, "axis_id")
        if self.value_kind not in VALUE_KINDS:
            raise ValueError(f"unsupported value_kind {self.value_kind!r}")
        if not self.allowed_operators or any(op not in OPERATORS for op in self.allowed_operators):
            raise ValueError("allowed_operators must be a non-empty subset of the known operators")
        if len(set(self.allowed_operators)) != len(self.allowed_operators):
            raise ValueError("allowed_operators must not repeat")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"unsupported source_kind {self.source_kind!r}")
        _text(self.extractor_id, "extractor_id")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"allowed_operators": list(self.allowed_operators), "axis_id": self.axis_id,
                "extractor_id": self.extractor_id, "format": FORMAT,
                "source_kind": self.source_kind, "value_kind": self.value_kind}


@dataclass(frozen=True)
class AxisRegistry:
    axes: tuple[AxisDefinition, ...]

    def __post_init__(self) -> None:
        ids = [item.axis_id for item in self.axes]
        if len(set(ids)) != len(ids):
            raise ValueError("axis ids must be unique within a registry")

    def __contains__(self, axis_id: str) -> bool:
        return axis_id in self._by_id

    @property
    def _by_id(self) -> dict[str, AxisDefinition]:
        return {item.axis_id: item for item in self.axes}

    def resolve(self, axis_id: str) -> AxisDefinition:
        try:
            return self._by_id[axis_id]
        except KeyError:
            raise ValueError(f"unregistered research axis {axis_id!r}") from None

    def require_operator(self, axis_id: str, operator: str) -> AxisDefinition:
        axis = self.resolve(axis_id)
        if operator not in axis.allowed_operators:
            raise ValueError(f"axis {axis_id!r} does not support operator {operator!r}")
        return axis

    @property
    def digest(self) -> str:
        return _digest([item.canonical() for item in sorted(self.axes)])


CAUSAL_AXIS_REGISTRY = AxisRegistry((
    AxisDefinition("causal.world.format", "text", ("eq", "set"), "spec", "world_format_v1"),
    AxisDefinition("causal.material.kind", "integer", ("eq", "set"), "spec", "material_kind_v1"),
    AxisDefinition("causal.collision.left_kind", "integer", ("eq", "set"), "derived_event", "collision_left_kind_v1"),
    AxisDefinition("causal.collision.right_kind", "integer", ("eq", "set"), "derived_event", "collision_right_kind_v1"),
    AxisDefinition("causal.collision.left_energy", "integer", ("eq", "range", "set"), "derived_event", "collision_left_energy_v1"),
    AxisDefinition("causal.collision.right_energy", "integer", ("eq", "range", "set"), "derived_event", "collision_right_energy_v1"),
    AxisDefinition("causal.collision.energy_relation", "text", ("eq", "set"), "derived_relation", "collision_energy_relation_v1"),
    AxisDefinition("causal.collision.direction_relation", "text", ("eq", "set"), "derived_relation", "collision_direction_relation_v1"),
    AxisDefinition("causal.bond.break_heat", "integer", ("eq", "range", "set"), "spec", "bond_break_heat_v1"),
    AxisDefinition("causal.heat.energy", "integer", ("eq", "range", "set"), "spec", "heat_cell_energy_v1"),
))
