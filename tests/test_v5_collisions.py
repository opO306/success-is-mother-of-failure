"""C1 collisions (docs/current/A_MICRO_V5_COLLISION_ROTATION_PLAN_V1.md, approved with R3 = halt).

contact -> a process the laws allow (today only a bond) -> otherwise a collision.
C1 resolves only: face-to-face, frictionless, e = 1, rigid, torque-free.
Everything else it cannot resolve without invented physics halts with a record.
"""
from __future__ import annotations

import copy
from fractions import Fraction

import pytest

from audit.independent_v5 import audit_run
from engine.deterministic.v5_spec import WorldSpecV5
from tests.test_v5_geo_v1b import _pocket, bonded
from tests.test_v5_reference import free, run, world

NO_RULES: list = []


def _momenta(result):
    return {s.key: s.momentum for s in result.final_state.structures}


# ---------------------------------------------------------------------------
# Textbook values.
# ---------------------------------------------------------------------------

def test_equal_masses_swap_velocities() -> None:
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (1, 0)), free("b", (-1, 0))], rules=NO_RULES))
    assert _momenta(result) == {("a",): (-1, 0), ("b",): (1, 0)}
    (c,) = result.collisions
    assert c.time == 1 and c.axis == "x"


def test_unequal_masses_follow_the_elastic_formula() -> None:
    """m1 = 2 at speed 1 onto m2 = 1 at rest: v1' = (m1-m2)/(m1+m2) = 1/3, v2' = 2m1/(m1+m2) = 4/3."""
    result = run(world([("a", 1, 0, 0), ("b", 0, 3, 0)], [free("a", (2, 0)), free("b")], rules=NO_RULES))
    assert _momenta(result) == {("a",): (Fraction(2, 3), 0), ("b",): (Fraction(4, 3), 0)}


def test_tangential_motion_is_untouched() -> None:
    """Frictionless: both slide north at 1/2 and collide on x; the y components stay."""
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (1, "1/2")), free("b", (-1, "1/2"))],
                       rules=NO_RULES))
    assert _momenta(result) == {("a",): (-1, Fraction(1, 2)), ("b",): (1, Fraction(1, 2))}


def test_kinetic_energy_and_momentum_are_conserved_and_audited() -> None:
    spec = world([("a", 1, 0, 0), ("b", 0, 3, 0), ("c", 0, 9, 0)],
                 [free("a", (3, 0)), free("b", ("-1/2", 0)), free("c", (-1, 0))], rules=NO_RULES)
    result = run(spec)
    assert len(result.collisions) >= 2
    from engine.deterministic.v5_state import initial_state
    assert initial_state(spec).totals(spec) == result.final_state.totals(spec)
    assert audit_run(spec.canonical(), result.canonical()) == []


# ---------------------------------------------------------------------------
# Structures.
# ---------------------------------------------------------------------------

def test_a_centred_collision_with_a_structure_uses_the_whole_contact() -> None:
    """A vertical pair (centre y = 1/2) is hit by a particle at y = 1/2 whose face
    touches BOTH members: one contact of two segments, centred -- a collision."""
    spec = world([("p", 0, 0, 0), ("q", 0, 0, 1), ("x", 0, 3, "1/2")],
                 [bonded(["p", "q"], [["p", "S", "q", "N"]]), free("x", (-1, 0))], rules=NO_RULES)
    result = run(spec)
    (c,) = result.collisions
    assert c.faces == frozenset({("p", "E"), ("q", "E"), ("x", "W")})      # x.W against both p.E and q.E
    # m_pair = 2, m_x = 1: v_pair' = 2*1/3 * (-1) = -2/3 -> P = -4/3; v_x' = (1-2)/3 * (-1) = 1/3
    assert _momenta(result) == {("p", "q"): (Fraction(-4, 3), 0), ("x",): (Fraction(1, 3), 0)}
    assert audit_run(spec.canonical(), result.canonical()) == []


def test_off_centre_collision_halts() -> None:
    """R3: the line through the two centres misses -- a real torque, and v5 has no
    rotation. Halt, not a silent bounce."""
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, "1/2")], [free("a", (1, 0)), free("b", (-1, 0))],
                       rules=NO_RULES))
    assert result.outcome == "halted" and result.collisions == ()
    assert result.unresolved[0].reason == "off_center_torque"


def test_contacts_on_two_axes_at_once_halt() -> None:
    """x docks into the pocket touching one member on its N face and one on its E face;
    with no rules nothing bonds -- a collision with two normals is not C1."""
    base = _pocket()
    spec = WorldSpecV5(base.world_id, base.units, base.materials, (), base.elements, base.structures, base.world_class)
    result = run(spec)
    assert result.outcome == "halted" and result.unresolved[0].reason == "mixed_normals"


def test_touching_faces_of_two_structures_that_bond_are_internal() -> None:
    """A bonds to B through p-r; q touches both r and s on faces that cannot bond. Because
    A and B become one rigid body in that instant, those touches are internal -- no collision."""
    rules = [{"rule_id": "0E-0W", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "0"}]
    spec = world([("p", 0, 0, 0), ("q", 1, 0, 1), ("r", 0, 3, "1/2"), ("s", 1, 3, "3/2")],
                 [bonded(["p", "q"], [["p", "S", "q", "N"]], momentum=(3, 0)),
                  bonded(["r", "s"], [["r", "S", "s", "N"]])], rules=rules)
    result = run(spec)
    assert result.collisions == () and len(result.events) == 1
    assert result.final_state.structures[0].members == frozenset({"p", "q", "r", "s"})


# ---------------------------------------------------------------------------
# One body in two events at one instant (R6).
# ---------------------------------------------------------------------------

def test_two_bodies_hitting_one_body_at_once_halt() -> None:
    result = run(world([("a", 0, -3, 0), ("b", 0, 0, 0), ("c", 0, 3, 0)],
                       [free("a", (1, 0)), free("b"), free("c", (-1, 0))], rules=NO_RULES))
    assert result.outcome == "halted" and {u.reason for u in result.unresolved} == {"shared_body"}


def test_newtons_cradle_halts_instead_of_sequencing() -> None:
    """a hits b; b already touches c. Resolving a-b first and then b-c at the same
    instant is exactly the pairwise sequencing R6 forbids."""
    result = run(world([("a", 0, -3, 0), ("b", 0, 0, 0), ("c", 0, 1, 0)],
                       [free("a", (1, 0)), free("b"), free("c")], rules=NO_RULES))
    assert result.outcome == "halted"
    assert result.unresolved[0].reason == "shared_body" and result.unresolved[0].round == 1


def test_a_bond_and_a_collision_on_one_body_halt() -> None:
    """a bonds onto b's west face while c (no rule for its face) hits b's east face."""
    rules = [{"rule_id": "0E-0W", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "0"}]
    materials = [{"kind": 0, "mass": "1", "contact_half_width": "1/2", "ports": ["E", "N", "S", "W"]},
                 {"kind": 1, "mass": "1", "contact_half_width": "1/2", "ports": []}]
    spec = world([("a", 0, -3, 0), ("b", 0, 0, 0), ("c", 1, 3, 0)],
                 [free("a", (1, 0)), free("b"), free("c", (-1, 0))], rules=rules, materials=materials)
    result = run(spec)
    assert result.outcome == "halted" and result.unresolved[0].reason == "shared_body"


def test_corners_still_halt() -> None:
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 3)], [free("a", (1, 1)), free("b", (-1, -1))], rules=NO_RULES))
    assert result.unresolved[0].kind == "corner_contact"


# ---------------------------------------------------------------------------
# Invariance and audit tampering.
# ---------------------------------------------------------------------------

def _bouncy():
    return world([("a", 1, 0, 0), ("b", 0, 3, 0), ("c", 0, 9, 0), ("d", 0, 0, 6), ("e", 1, 0, 11)],
                 [free("a", (3, 0)), free("b", ("-1/2", 0)), free("c", (-1, 0)), free("d", (0, "5/3")),
                  free("e", (0, -1))], rules=NO_RULES)


def test_collisions_are_independent_of_names() -> None:
    spec = _bouncy()
    mapping = {"a": "q", "b": "a", "c": "zz", "d": "d0", "e": "b"}
    assert run(spec.relabeled(mapping)).physics() == run(spec).relabeled(mapping).physics()


def test_collisions_are_independent_of_observation_interval() -> None:
    assert run(_bouncy(), interval=Fraction(1, 3)).physics() == run(_bouncy(), interval=1).physics()


def test_collisions_are_galilean_invariant() -> None:
    spec = _bouncy()
    kinds = {e.label: e.kind for e in spec.elements}
    u = (Fraction(1, 2), Fraction(-1, 3))
    mass = lambda s: sum((spec.material(kinds[m]).mass for m in s.members), Fraction(0))
    boosted = WorldSpecV5(spec.world_id, spec.units, spec.materials, spec.bond_rules, spec.elements,
                          tuple(type(s)(s.members, s.bonds, (s.momentum[0] + u[0] * mass(s), s.momentum[1] + u[1] * mass(s)),
                                        s.internal_energy) for s in spec.structures), spec.world_class)
    plain, moved = run(spec), run(boosted)
    assert [(c.time, c.axis, c.faces) for c in plain.collisions] == [(c.time, c.axis, c.faces) for c in moved.collisions]


@pytest.mark.parametrize("path, value, message", [
    (("post", 0, "internal_energy"), [5, 1], "changed internal energy"),
    (("post", 0, "momentum"), [[1, 1], [1, 1]], "tangential momentum changed"),
])
def test_audit_catches_tampered_collisions(path, value, message) -> None:
    spec = world([("a", 1, 0, 0), ("b", 0, 3, 0)], [free("a", (2, 0)), free("b")], rules=NO_RULES)
    document = copy.deepcopy(run(spec).canonical())
    target = document["collisions"][0]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert any(message in p for p in audit_run(spec.canonical(), document))


def test_audit_catches_a_wrong_elastic_result() -> None:
    """Swap the two post momenta: momentum and energy totals still balance, but the
    elastic formula does not."""
    spec = world([("a", 1, 0, 0), ("b", 0, 3, 0)], [free("a", (2, 0)), free("b")], rules=NO_RULES)
    document = copy.deepcopy(run(spec).canonical())
    post = document["collisions"][0]["post"]
    post[0]["momentum"], post[1]["momentum"] = post[1]["momentum"], post[0]["momentum"]
    assert any("elastic formula" in p for p in audit_run(spec.canonical(), document))
