"""GEO v1B: CREATE / GROW / MERGE on the v5 reference executor (docs/current/A_MICRO_V5_GEO_V1B_PLAN.md).

Not new physics -- a check that the one element-contact law extends, unchanged,
to growth of any size and shape, independent of names and order:

  1  a straight chain grows past the old length-3 ceiling (to 31 here)
  2  a branch: a particle bonds onto a chain end's side face; a MIDDLE side branch cannot
     happen in the equal-square model (corner halt or contest) -- recorded as a measured consequence
  3  a MOVING structure grows (impossible in v2)
  4  a cycle forms when a particle docks into a pocket with two faces at once -- plain bonds,
     no "ring" type; two aligned stacks cannot close a cycle face to face (corner halt)
  5  MERGE of two multi-member structures, both with U > 0, different masses and momenta
  6  several particles bond to different faces in one instant (v2 defect: one bond per tick)
  7a one particle bonding with two of its faces at once -- both bonds (v2 defect: lowest id wins)
  7b two contacts claiming one face -- nobody is chosen, the run halts
  8  a contact on an already-bonded face halts
  9-11 name / order / observation / Galilean invariance and the independent audit on growth-rich worlds
  12 `world_class` is metadata: changing it changes no physics
"""
from __future__ import annotations

import ast
import random
from fractions import Fraction
from pathlib import Path

import pytest

from audit.independent_v5 import audit_run
from engine.deterministic.v5_benchmark_worlds import merge_chain_world, offset_world, row_world
from engine.deterministic.v5_reference import run_v5
from engine.deterministic.v5_spec import RunRequest, WorldSpecV5
from engine.deterministic.v5_state import face_touch
from tests.test_v5_reference import free, run, world

ROOT = Path(__file__).resolve().parents[1]
MIXED_RULES = [{"rule_id": f"{a}E-{b}W", "a": {"kind": a, "port": "E"}, "b": {"kind": b, "port": "W"},
                "threshold": "0"} for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))]


def bonded(members, bonds, momentum=(0, 0), internal_energy=0):
    return {"members": members, "bonds": bonds, "momentum": momentum, "internal_energy": internal_energy}


def _shape_holds(result, spec) -> None:
    """Every bond is still a flush face contact on its declared faces."""
    state = result.final_state
    for s in state.structures:
        for b in s.bonds:
            assert face_touch(spec, state.element(b.a_label), state.element(b.b_label)) == b.a_port


# ---------------------------------------------------------------------------
# 1-4. Shapes.
# ---------------------------------------------------------------------------

def test_a_straight_chain_grows_past_the_old_ceiling() -> None:
    spec = merge_chain_world(30)
    result = run_v5(spec, RunRequest(10 ** 15, 10 ** 15))
    (chain,) = [s for s in result.final_state.structures if len(s.members) > 1]
    assert len(chain.members) == 31 and len(chain.bonds) == 30             # v2's measured ceiling was 3
    assert {b.a_port for b in chain.bonds} == {"E"}
    ys = {result.final_state.element(m).position[1] for m in chain.members}
    assert ys == {Fraction(0)}
    _shape_holds(result, spec)


def test_a_particle_bonds_onto_the_side_of_a_chain_end() -> None:
    """A branch: d falls onto the end member c, hanging half off the chain's end."""
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 2, 0), ("d", 0, "5/2", -3)],
                 [bonded(["a", "b", "c"], [["a", "E", "b", "W"], ["b", "E", "c", "W"]]), free("d", (0, 1))])
    result = run(spec)
    (event,) = result.events
    assert [b.canonical() for b in event.bonds] == [["c", "N", "d", "S"]]
    _shape_holds(result, spec)


@pytest.mark.parametrize("dx", [0, Fraction(1, 4)])
def test_a_middle_side_branch_cannot_happen_in_the_square_model(dx) -> None:
    """Measured geometric consequence of K3 (equal squares) + K6 (corner halts), not a bug:
    landing squarely on a middle member corner-touches both neighbours; landing a little
    off-centre puts one face on two members -- a contest. Either way the run halts."""
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 2, 0), ("d", 0, 1 + dx, -3)],
                 [bonded(["a", "b", "c"], [["a", "E", "b", "W"], ["b", "E", "c", "W"]]), free("d", (0, 1))])
    result = run(spec)
    assert result.outcome == "halted" and result.events == ()
    assert {u.kind for u in result.unresolved} == ({"corner_contact"} if dx == 0 else {"contested_contact"})


def test_a_moving_structure_grows() -> None:
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 5, 0)],
                 [bonded(["a", "b"], [["a", "E", "b", "W"]], momentum=(2, 0)), free("c")])
    (event,) = run(spec).events
    assert event.time == 3 and event.post.members == frozenset({"a", "b", "c"})
    assert event.post.momentum == (2, 0)                                    # the moving body kept all its momentum


def test_a_cycle_is_just_bonds() -> None:
    """x docks into the C-shaped structure's pocket with two faces at once: the bond
    graph closes into a cycle (8 bonds on 8 members) -- nothing but ordinary bonds."""
    result = run(_pocket())
    (ring,) = result.final_state.structures
    assert len(ring.members) == 8 and len(ring.bonds) == 8                 # edges == nodes, connected: one cycle
    _shape_holds(result, _pocket())


def test_two_stacked_pairs_cannot_close_a_cycle_face_to_face() -> None:
    """Measured consequence of the square model: aligned stacks meet with their diagonal
    members corner to corner -- a corner halt, not a four-member ring."""
    spec = world([("p", 0, 0, 0), ("q", 0, 0, 1), ("r", 0, 3, 0), ("s", 0, 3, 1)],
                 [bonded(["p", "q"], [["p", "S", "q", "N"]], momentum=(2, 0)),
                  bonded(["r", "s"], [["r", "S", "s", "N"]])])
    result = run(spec)
    assert result.outcome == "halted" and {u.kind for u in result.unresolved} == {"corner_contact"}


def test_a_rigid_structure_never_bonds_to_itself() -> None:
    """Two members of one structure touching face to face, unbonded, stay unbonded."""
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 1, 1), ("d", 0, 0, 1)],
                 [bonded(["a", "b", "c", "d"], [["a", "E", "b", "W"], ["b", "S", "c", "N"], ["c", "W", "d", "E"]],
                         momentum=(1, 0))])
    result = run(spec)
    assert result.events == () and len(result.final_state.structures[0].bonds) == 3


# ---------------------------------------------------------------------------
# 5. MERGE.
# ---------------------------------------------------------------------------

def test_merge_of_two_multi_member_structures() -> None:
    spec = world([("a1", 0, 0, 0), ("a2", 1, 1, 0), ("b1", 1, 5, 0), ("b2", 0, 6, 0)],
                 [bonded(["a1", "a2"], [["a1", "E", "a2", "W"]], momentum=(3, 1), internal_energy=3),
                  bonded(["b1", "b2"], [["b1", "E", "b2", "W"]], momentum=(-2, 1), internal_energy=2)],
                 rules=MIXED_RULES)
    result = run(spec)
    (event,) = result.events
    pa, pb = (Fraction(3), Fraction(1)), (Fraction(-2), Fraction(1))
    ma = mb = Fraction(3)
    k = lambda p, m: (p[0] ** 2 + p[1] ** 2) / (2 * m)
    p_after = (pa[0] + pb[0], pa[1] + pb[1])
    assert event.post.members == frozenset({"a1", "a2", "b1", "b2"})
    assert event.post.momentum == p_after
    assert event.post.internal_energy == 3 + 2 + k(pa, ma) + k(pb, mb) - k(p_after, ma + mb)
    (merged,) = result.final_state.structures
    assert {b.canonical()[0] + b.canonical()[2] for b in merged.bonds} == {"a1a2", "b1b2", "a2b1"}
    assert audit_run(spec.canonical(), result.canonical()) == []


# ---------------------------------------------------------------------------
# 6-8. One instant, many contacts.
# ---------------------------------------------------------------------------

def test_several_particles_bond_to_different_faces_in_one_instant() -> None:
    """v2 allowed one new bond per chain per tick; here w and e reach both ends of a
    resting chain at the same instant and both bond."""
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 2, 0), ("w", 0, -3, 0), ("e", 0, 5, 0)],
                 [bonded(["a", "b", "c"], [["a", "E", "b", "W"], ["b", "E", "c", "W"]]),
                  free("w", (1, 0)), free("e", (-1, 0))])
    (event,) = run(spec).events
    assert event.time == 2 and event.round == 0 and len(event.bonds) == 2 and len(event.pre) == 3


def _pocket():
    """A C-shaped structure with a pocket at (0, 1): x flies in diagonally and at
    t = 2 touches m1 with its N face and m2 with its E face at the same instant."""
    return world([("m1", 0, 0, 0), ("m4", 0, 0, -1), ("m5", 0, 1, -1), ("m6", 0, 2, -1), ("m7", 0, 2, 0),
                  ("m8", 0, 2, 1), ("m2", 0, 1, 1), ("x", 0, -2, 3)],
                 [bonded(["m1", "m4", "m5", "m6", "m7", "m8", "m2"],
                         [["m1", "N", "m4", "S"], ["m4", "E", "m5", "W"], ["m5", "E", "m6", "W"],
                          ["m6", "S", "m7", "N"], ["m7", "S", "m8", "N"], ["m8", "W", "m2", "E"]]),
                  free("x", (1, -1))])


def test_one_particle_bonds_with_two_of_its_faces_at_once() -> None:
    """7a: compatible -- different faces of x, different members. Both bonds, whatever the names."""
    result = run(_pocket())
    (event,) = result.events
    assert event.time == 2
    assert {tuple(b.canonical()) for b in event.bonds} == {("m1", "S", "x", "N"), ("m2", "W", "x", "E")}
    mapping = {"m1": "z", "m2": "a", "m4": "m", "m5": "k", "m6": "q", "m7": "b", "m8": "y", "x": "c"}
    assert run(_pocket().relabeled(mapping)).physics() == result.relabeled(mapping).physics()


def _contest():
    """7b: two members side by side under x; x falls onto both with its single S face."""
    return world([("l", 0, "-1/2", 1), ("r", 0, "1/2", 1), ("x", 0, 0, -2)],
                 [bonded(["l", "r"], [["l", "E", "r", "W"]]), free("x", (0, 1))])


def test_one_face_claimed_twice_chooses_nobody() -> None:
    result = run(_contest())
    assert result.outcome == "halted" and result.events == ()
    assert {u.kind for u in result.unresolved} == {"contested_contact"}
    assert {label for u in result.unresolved for label, _ in u.participants} == {"l", "r", "x"}
    mapping = {"l": "r", "r": "l", "x": "a"}
    assert run(_contest().relabeled(mapping)).physics() == result.relabeled(mapping).physics()


def test_a_contact_on_an_already_bonded_face_halts() -> None:
    """y2 sits a quarter off y1's east face, so part of that face is still exposed;
    t reaches it -- but the port is taken."""
    spec = world([("y1", 0, 0, 0), ("y2", 0, 1, "1/4"), ("t", 0, 3, "-4/5")],
                 [bonded(["y1", "y2"], [["y1", "E", "y2", "W"]], momentum=(2, 0)), free("t")])
    result = run(spec)
    assert result.outcome == "halted"
    (u,) = result.unresolved
    assert u.kind == "non_binding_collision_unresolved" and u.reason == "port_occupied"


# ---------------------------------------------------------------------------
# 9-11. Invariance and audit on growth-rich worlds.
# ---------------------------------------------------------------------------

GROWTH_WORLDS = [lambda: row_world(14, s) for s in range(3)] + [lambda: offset_world(16, s) for s in range(3)]


def _renamed(spec: WorldSpecV5, seed: int) -> tuple[WorldSpecV5, dict[str, str]]:
    labels = [e.label for e in spec.elements]
    shuffled = labels[:]
    random.Random(seed).shuffle(shuffled)
    mapping = {old: f"n{new}" for old, new in zip(labels, shuffled)}
    renamed = spec.relabeled(mapping)
    rng = random.Random(seed + 1)
    reordered = WorldSpecV5(renamed.world_id, renamed.units, tuple(rng.sample(renamed.materials, len(renamed.materials))),
                            tuple(rng.sample(renamed.bond_rules, len(renamed.bond_rules))),
                            tuple(rng.sample(renamed.elements, len(renamed.elements))),
                            tuple(rng.sample(renamed.structures, len(renamed.structures))), renamed.world_class)
    return reordered, mapping


@pytest.mark.parametrize("index", range(len(GROWTH_WORLDS)))
def test_growth_is_independent_of_names_and_order(index) -> None:
    spec = GROWTH_WORLDS[index]()
    result = run(spec, end=120)
    assert result.events                                                     # these worlds really grow
    for seed in (1, 2):
        renamed, mapping = _renamed(spec, seed)
        assert run(renamed, end=120).physics() == result.relabeled(mapping).physics()


@pytest.mark.parametrize("index", range(len(GROWTH_WORLDS)))
def test_growth_is_independent_of_observation_and_frame(index) -> None:
    spec = GROWTH_WORLDS[index]()
    plain = run(spec, end=60, interval=1)
    assert run(spec, end=60, interval=Fraction(1, 3)).physics() == plain.physics()
    u = (Fraction(-2, 3), Fraction(1, 5))
    kinds = {e.label: e.kind for e in spec.elements}
    boosted = WorldSpecV5(spec.world_id, spec.units, spec.materials, spec.bond_rules, spec.elements,
                          tuple(type(s)(s.members, s.bonds,
                                        (s.momentum[0] + u[0] * _mass(spec, kinds, s),
                                         s.momentum[1] + u[1] * _mass(spec, kinds, s)), s.internal_energy)
                                for s in spec.structures), spec.world_class)
    moved = run(boosted, end=60)
    assert [(e.time, e.round, e.bonds, e.post.internal_energy) for e in moved.events] == \
           [(e.time, e.round, e.bonds, e.post.internal_energy) for e in plain.events]
    assert moved.outcome == plain.outcome


def _mass(spec, kinds, s):
    return sum((spec.material(kinds[m]).mass for m in s.members), Fraction(0))


@pytest.mark.parametrize("index", range(len(GROWTH_WORLDS)))
def test_growth_worlds_pass_the_independent_audit(index) -> None:
    spec = GROWTH_WORLDS[index]()
    result = run(spec, end=120)
    assert audit_run(spec.canonical(), result.canonical()) == []
    _shape_holds(result, spec)


# ---------------------------------------------------------------------------
# 12. world_class is not physics.
# ---------------------------------------------------------------------------

def test_world_class_changes_no_physics() -> None:
    spec = row_world(14, 0)
    other = WorldSpecV5(spec.world_id, spec.units, spec.materials, spec.bond_rules, spec.elements, spec.structures,
                        "CANONICAL_A")
    assert other.digest != spec.digest
    assert run(other, end=120).physics() == run(spec, end=120).physics()


def test_the_executor_never_reads_world_class() -> None:
    for module in ("v5_reference", "v5_state", "v5_number"):
        source = (ROOT / "engine" / "deterministic" / f"{module}.py").read_text(encoding="utf-8")
        names = {n.attr for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute)}
        assert "world_class" not in names, module


def test_world_class_is_required_and_closed() -> None:
    spec = row_world(4, 0)
    raw = spec.canonical()
    with pytest.raises(ValueError):
        WorldSpecV5(spec.world_id, spec.units, spec.materials, spec.bond_rules, spec.elements, spec.structures,
                    "SOMETHING_ELSE")
    assert raw["world_class"] == "NON_CANONICAL_TEST_WORLD"
