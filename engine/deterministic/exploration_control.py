"""Typed, role-bound targets a Broad Explorer may mutate on a `CausalWorldSpec`.

A control never names a raw path like `"particles[0].kinetic_energy"`: it
names a semantic role ("left_collider", "local_heat_source") which is bound
to exactly one concrete id (a `particle_id` or `rule_id`) in one base spec.
Renaming particle ids in that spec changes nothing about the plan -- only the
binding step re-resolves, which is what keeps an `ExplorationPlan` from being
married to one world's numbering. Zero or multiple matches for a role is a
plan error, never a silent choice.

A `ParticleIdTarget`/`HeatCellTarget` escape hatch exists for the rare case
of studying one specific object by its actual id, but the default path for
Broad Explorer plans is role binding.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Union

from .causal_spec import CausalWorldSpec

FORMAT = "exploration-control-v1"

PARTICLE_FIELDS = frozenset({"kinetic_energy", "direction", "orientation"})
HEAT_FIELDS = frozenset({"energy"})
BOND_RULE_FIELDS = frozenset({"minimum_collision_energy", "break_heat"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True, order=True)
class ParticleRoleTarget:
    """Selects the one particle in a base spec matching a role predicate.

    B0.3 keeps predicates deliberately narrow: matching by starting
    `(x, y)` and `direction` is enough to express "the particle moving east
    from cell (9, 10)" without particle ids ever entering the plan.
    """
    role: str
    match_x: int
    match_y: int
    match_direction: str
    field: str

    def __post_init__(self) -> None:
        _text(self.role, "role")
        if self.field not in PARTICLE_FIELDS:
            raise ValueError(f"unsupported particle control field {self.field!r}")

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "kind": "particle_role", "match_direction": self.match_direction,
                "match_x": self.match_x, "match_y": self.match_y, "role": self.role}

    def resolve(self, spec: CausalWorldSpec) -> int:
        matches = [p.particle_id for p in spec.particles
                  if p.x == self.match_x and p.y == self.match_y and p.direction == self.match_direction]
        if not matches:
            raise ValueError(f"role {self.role!r} matched no particle in spec {spec.digest[:12]}")
        if len(matches) > 1:
            raise ValueError(f"role {self.role!r} matched {len(matches)} particles in spec {spec.digest[:12]}; ambiguous")
        return matches[0]


@dataclass(frozen=True, order=True)
class HeatCellRoleTarget:
    """Selects the one heat cell in a base spec at a given grid position."""
    role: str
    x: int
    y: int
    field: str

    def __post_init__(self) -> None:
        _text(self.role, "role")
        if self.field not in HEAT_FIELDS:
            raise ValueError(f"unsupported heat control field {self.field!r}")

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "kind": "heat_cell_role", "role": self.role, "x": self.x, "y": self.y}

    def resolve(self, spec: CausalWorldSpec) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass(frozen=True, order=True)
class BondRuleRoleTarget:
    """Selects a bond rule in a base spec by its declared `rule_id`."""
    role: str
    rule_id: str
    field: str

    def __post_init__(self) -> None:
        _text(self.role, "role")
        _text(self.rule_id, "rule_id")
        if self.field not in BOND_RULE_FIELDS:
            raise ValueError(f"unsupported bond rule control field {self.field!r}")

    def canonical(self) -> dict[str, object]:
        return {"field": self.field, "kind": "bond_rule_role", "role": self.role, "rule_id": self.rule_id}

    def resolve(self, spec: CausalWorldSpec) -> str:
        matches = [r.rule_id for r in spec.bond_rules if r.rule_id == self.rule_id]
        if not matches:
            raise ValueError(f"bond rule {self.rule_id!r} not found in spec {spec.digest[:12]}")
        return matches[0]


ControlTarget = Union[ParticleRoleTarget, HeatCellRoleTarget, BondRuleRoleTarget]


@dataclass(frozen=True, order=True)
class ControlDefinition:
    """A mutation B0.3 is allowed to make, and the research axis its value is recorded under.

    `control_id` names the mechanism ("which field on which role"); `research_axis`
    names the registered `research_axis.AxisDefinition` id that a point
    domain should use for this control's value. The two are rarely the same
    string on purpose (docs/README's "what B researches" vs "what A lets you
    turn" split) -- keeping the field explicit means a `ResearchDomain` built
    from a candidate always names a real, registered axis instead of the raw
    control id, which registers nothing.
    """
    control_id: str
    target: ControlTarget
    research_axis: str

    def __post_init__(self) -> None:
        _text(self.control_id, "control_id")
        _text(self.research_axis, "research_axis")

    def canonical(self) -> dict[str, object]:
        return {"control_id": self.control_id, "format": FORMAT, "research_axis": self.research_axis,
                "target": self.target.canonical()}


@dataclass(frozen=True)
class ControlBinding:
    """A control resolved against one base spec: the role plus what it resolved to.

    Both the role and the resolved identity are kept, deliberately, so a
    journal reader can see *why* particle 1 was mutated ("it was the
    left_collider in this base world") rather than just that it was.
    """
    control_id: str
    role: str
    resolved_identity: str

    def canonical(self) -> dict[str, object]:
        return {"control_id": self.control_id, "resolved_identity": self.resolved_identity, "role": self.role}


def bind_control(control: ControlDefinition, spec: CausalWorldSpec) -> ControlBinding:
    target = control.target
    if isinstance(target, ParticleRoleTarget):
        return ControlBinding(control.control_id, target.role, str(target.resolve(spec)))
    if isinstance(target, HeatCellRoleTarget):
        x, y = target.resolve(spec)
        return ControlBinding(control.control_id, target.role, f"{x},{y}")
    if isinstance(target, BondRuleRoleTarget):
        return ControlBinding(control.control_id, target.role, target.resolve(spec))
    raise TypeError(f"unsupported control target type {type(target).__name__}")


def apply_control(spec: CausalWorldSpec, control: ControlDefinition, value: object) -> CausalWorldSpec:
    """Return a new spec with exactly one control's field mutated. Never touches A's code."""
    target = control.target
    if isinstance(target, ParticleRoleTarget):
        particle_id = target.resolve(spec)
        particles = tuple(replace(p, **{target.field: value}) if p.particle_id == particle_id else p
                          for p in spec.particles)
        return replace(spec, particles=particles)
    if isinstance(target, HeatCellRoleTarget):
        x, y = target.resolve(spec)
        remaining = tuple(cell for cell in spec.heat if (cell.x, cell.y) != (x, y))
        if value:
            from .causal_spec import HeatCellSpec
            remaining = tuple(sorted(remaining + (HeatCellSpec(x, y, value),)))
        return replace(spec, heat=remaining)
    if isinstance(target, BondRuleRoleTarget):
        rule_id = target.resolve(spec)
        rules = tuple(replace(r, **{target.field: value}) if r.rule_id == rule_id else r
                      for r in spec.bond_rules)
        return replace(spec, bond_rules=rules)
    raise TypeError(f"unsupported control target type {type(target).__name__}")
