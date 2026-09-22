"""Shared role-matching rules for anything that names a subject by role rather than by raw id.

Both `exploration_control.py` (Broad Explorer's mutation targets) and
`trace_model.py` (Deep Investigator's observation targets) need to answer
the same question -- "which particle/heat cell/bond rule in this base spec
does this role predicate name?" -- and they must answer it the *same way*.
If control resolved a role one way and trace resolved it another, a plan
could mutate one particle while believing it was tracing that same particle:
the program would run fine and only the research conclusion would be wrong.

The matching rule stays deliberately strict: zero matches or more than one
match is always an error, never a silent choice.
"""
from __future__ import annotations

from .causal_spec import CausalWorldSpec


def resolve_particle_role(spec: CausalWorldSpec, role: str, match_x: int, match_y: int,
                          match_direction: str) -> int:
    """The one particle_id in `spec` at `(match_x, match_y)` moving `match_direction`."""
    matches = [p.particle_id for p in spec.particles
              if p.x == match_x and p.y == match_y and p.direction == match_direction]
    if not matches:
        raise ValueError(f"role {role!r} matched no particle in spec {spec.digest[:12]}")
    if len(matches) > 1:
        raise ValueError(f"role {role!r} matched {len(matches)} particles in spec {spec.digest[:12]}; ambiguous")
    return matches[0]


def resolve_heat_cell_role(spec: CausalWorldSpec, role: str, x: int, y: int) -> tuple[int, int]:
    """The one heat cell location `(x, y)`. Always resolves -- a cell may be legally absent (zero energy)."""
    return (x, y)


def resolve_bond_rule_role(spec: CausalWorldSpec, role: str, rule_id: str) -> str:
    """The one bond rule in `spec` declaring `rule_id`."""
    matches = [r.rule_id for r in spec.bond_rules if r.rule_id == rule_id]
    if not matches:
        raise ValueError(f"bond rule {rule_id!r} not found in spec {spec.digest[:12]}")
    return matches[0]
