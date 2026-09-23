"""causal v4 Stage B: a structure owns its motion (docs/current/STRUCTURE_STATE_V1.md).

Sections:
  1. the defect is gone on v4: motion lives on the structure, not on the
     lowest-numbered member (replaces the known-defect characterization)
  2. the state refuses structures that disagree with their bonds or energy
  3. motion: cardinal momentum steps the whole body and keeps every bond's
     adjacency (across the wrap seam too); diagonal momentum is reported as
     physically undetermined, not guessed
  4. positive relabelling invariance (Q5): renaming ids, reordering
     particles/bonds/rules and swapping bond endpoints never changes the
     physical result, over several ticks of a mixed world
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from engine.deterministic.causal_kernel import (
    CausalWorldState,
    PhysicalBond,
    PortBond,
    StructureState,
    initial_causal_state,
    step_causal_world,
    structure_contacts,
    unresolved_motions,
)
from engine.deterministic.causal_spec import (
    FORMAT_V3,
    FORMAT_V4,
    BondRuleSpec,
    CausalKernelSpec,
    CausalMaterialSpec,
    CausalParticleSpec,
    CausalWorldSpec,
)

PORTS = ("N", "E", "S", "W")
RULES = (BondRuleSpec("ew", 0, 0, "E", "W", 2, 4, "W", "E"),
         BondRuleSpec("ns", 1, 1, "N", "S", 2, 4, "S", "N"))


def _spec(fmt: str = FORMAT_V4, rules=RULES, size: int = 16) -> CausalWorldSpec:
    return CausalWorldSpec(
        "structure-state-fixture",
        CausalKernelSpec(size, size, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles", "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4, PORTS), CausalMaterialSpec(1, 2, 4, PORTS)), (), (), rules, 8, 1, fmt)


def _p(pid, x, y, direction="N", energy=0, kind=0, orientation=None):
    return CausalParticleSpec(pid, kind, x, y, direction, orientation or direction, energy)


def _state(particles, port_bonds=(), structures=(), spec=None) -> CausalWorldState:
    base = initial_causal_state(spec or _spec())
    return replace(base, particles=tuple(particles), port_bonds=tuple(port_bonds), structures=tuple(structures))


def _pair(a=1, b=2, x=5, y=5, momentum=(0, 0), energy=0, kind=0):
    """Two members side by side, a.E <-> b.W, owning `momentum`."""
    particles = (_p(a, x, y, kind=kind), _p(b, (x + 1) % 16, y, kind=kind))
    return particles, (PortBond(a, "E", b, "W", "ew", 0),), (StructureState({a, b}, momentum, energy),)


# ---------------------------------------------------------------------------
# 1. The defect is gone on v4.
# ---------------------------------------------------------------------------

def test_chain_motion_belongs_to_the_structure() -> None:
    """Replaces the v2 characterization `..._stored_on_the_lowest_numbered_member`
    for v4: the same moving structure is valid whichever numbers its members
    carry -- no member holds the motion, the structure does."""
    for a, b in ((5, 9), (9, 5)):
        state = _state(*_pair(a, b, momentum=(2, 0), energy=1))
        assert all(item.kinetic_energy == 0 for item in state.particles)
        assert state.momentum(_spec()) == (2, 0)
        assert state.total_energy() == 1


def test_a_member_cannot_hold_motion_of_its_own() -> None:
    particles, bonds, structures = _pair(momentum=(2, 0), energy=1)
    moving_member = (replace(particles[0], kinetic_energy=1), particles[1])
    with pytest.raises(ValueError, match="hold no motion of their own"):
        _state(moving_member, bonds, structures)


# ---------------------------------------------------------------------------
# 2. Structures must agree with their bonds and their energy.
# ---------------------------------------------------------------------------

def test_every_bonded_component_needs_its_structure() -> None:
    particles, bonds, _ = _pair()
    with pytest.raises(ValueError, match="connected components"):
        _state(particles, bonds, ())


def test_a_structure_must_be_held_together_by_bonds() -> None:
    particles, bonds, _ = _pair()
    lone = _p(3, 9, 9)
    with pytest.raises(ValueError, match="connected components"):
        _state(particles + (lone,), bonds, (StructureState({1, 2, 3}),))


def test_a_particle_belongs_to_at_most_one_structure() -> None:
    particles, bonds, _ = _pair()
    with pytest.raises(ValueError, match="at most one structure"):
        _state(particles, bonds, (StructureState({1, 2}), StructureState({2})))


def test_an_empty_structure_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one member"):
        StructureState(frozenset())


def test_momentum_and_motion_energy_must_agree() -> None:
    with pytest.raises(ValueError, match="disagree"):
        _state(*_pair(momentum=(2, 0), energy=2))          # mass 2: energy 2 needs |p| = 4


def test_structures_exist_only_under_v4() -> None:
    v3 = _spec(FORMAT_V3)
    with pytest.raises(ValueError, match="causal v4"):
        _state(*_pair(), spec=v3)


# ---------------------------------------------------------------------------
# 3. Motion.
# ---------------------------------------------------------------------------

def test_a_structure_steps_as_one_body_and_keeps_its_bonds() -> None:
    state = _state(*_pair(momentum=(-2, 0), energy=1))
    after = step_causal_world(_spec(), state)
    assert {(p.particle_id, p.x, p.y) for p in after.particles} == {(1, 4, 5), (2, 5, 5)}
    assert after.port_bonds == state.port_bonds and after.structures == state.structures


def test_a_structure_crosses_the_wrap_seam_intact() -> None:
    state = _state(*_pair(x=15, momentum=(0, 2), energy=1))        # member 2 sits at x=0 across the seam
    for _ in range(20):
        state = step_causal_world(_spec(), state)                  # __post_init__ re-checks adjacency each tick
    assert {(p.particle_id, p.y) for p in state.particles} == {(1, 9), (2, 9)}


def test_diagonal_momentum_is_reported_not_guessed() -> None:
    """Q3: representable, but no declared step exists -- it stays, and the
    state says why, so a census can count it."""
    state = _state(*_pair(momentum=(1, -1), energy=1))
    after = step_causal_world(_spec(), state)
    assert after.particles == state.particles
    (record,) = unresolved_motions(after)
    assert record.members == (1, 2) and record.momentum == (1, -1)
    assert record.reason == "insufficient_physical_state"


def test_a_free_particle_meeting_a_structure_is_visible_not_silently_resolved() -> None:
    particles, bonds, structures = _pair()
    visitor = _p(3, 5, 5, "E", 2)
    state = _state(particles + (visitor,), bonds, structures)
    assert structure_contacts(state) == (((1, 2), 3),)
    after = step_causal_world(_spec(), state)
    assert after.structures == state.structures and after.port_bonds == state.port_bonds


def test_a_structure_member_is_not_a_free_body_in_a_collision() -> None:
    """A resting free particle facing a member head-on would match the
    equal-energy scatter if the member were treated as free. It is not: the
    member (and its structure) is left exactly as it was."""
    particles, bonds, structures = _pair()                          # members face N, energy 0
    facing = _p(3, 5, 5, "S", 0)
    state = _state(particles + (facing,), bonds, structures)
    after = step_causal_world(_spec(), state)
    assert {p.particle_id: p for p in after.particles}[1] == particles[0]
    assert {p.particle_id: p for p in after.particles}[3] == facing


def test_conservation_holds_over_many_ticks() -> None:
    """step_causal_world asserts material, energy and momentum every tick."""
    particles, bonds, structures = _pair(momentum=(2, 0), energy=1)
    state = _state(particles + (_p(3, 1, 1, "S", 3), _p(4, 1, 3, "N", 3)), bonds, structures)
    for _ in range(30):
        state = step_causal_world(_spec(), state)


def test_worlds_without_structures_keep_their_digest_shape() -> None:
    state = initial_causal_state(_spec())
    assert "structures" not in state.canonical()


# ---------------------------------------------------------------------------
# 4. Positive relabelling invariance (Q5).
# ---------------------------------------------------------------------------

def _relabel(state: CausalWorldState, mapping: dict[int, int], *, reverse_order: bool,
             swap_endpoints: bool) -> CausalWorldState:
    particles = [replace(p, particle_id=mapping[p.particle_id]) for p in state.particles]
    port_bonds = [PortBond(mapping[b.right_id], b.right_port, mapping[b.left_id], b.left_port, b.rule_id,
                           b.stored_energy) if swap_endpoints else
                  PortBond(mapping[b.left_id], b.left_port, mapping[b.right_id], b.right_port, b.rule_id,
                           b.stored_energy) for b in state.port_bonds]
    bonds = [PhysicalBond(mapping[b.left_id], mapping[b.right_id], b.rule_id, b.stored_energy, b.x, b.y)
             for b in state.bonds]
    structures = [StructureState({mapping[m] for m in s.members}, s.momentum, s.motion_energy)
                  for s in state.structures]
    if reverse_order:
        particles, port_bonds, bonds, structures = (list(reversed(x)) for x in (particles, port_bonds, bonds, structures))
    return replace(state, particles=tuple(particles), port_bonds=tuple(port_bonds), bonds=tuple(bonds),
                   structures=tuple(structures))


def _mixed_world() -> CausalWorldState:
    moving = _pair(1, 2, x=2, y=2, momentum=(2, 0), energy=1)
    diagonal = _pair(3, 4, x=8, y=8, momentum=(-1, 1), energy=1)
    resting = _pair(5, 6, x=12, y=3)
    free = (_p(7, 4, 12, "E", 2), _p(8, 6, 12, "W", 2),                    # head-on, bond rule "ew"
            _p(9, 10, 12, "N", 1), _p(10, 10, 10, "S", 1),                  # equal-energy scatter
            _p(11, 13, 6, "S", 2, kind=1, orientation="N"), _p(12, 13, 8, "N", 2, kind=1, orientation="S"),
            _p(13, 3, 2, "W", 1))                                           # visits the moving structure
    particles = moving[0] + diagonal[0] + resting[0] + free
    return _state(particles, moving[1] + diagonal[1] + resting[1], moving[2] + diagonal[2] + resting[2])


MAPPINGS = [
    {i: i for i in range(1, 14)},
    {i: 14 - i for i in range(1, 14)},                                       # full reversal
    dict(zip(range(1, 14), (91, 7, 44, 3, 58, 12, 70, 2, 33, 81, 19, 64, 5))),
]


@pytest.mark.parametrize("mapping", MAPPINGS)
@pytest.mark.parametrize("reverse_order", [False, True])
@pytest.mark.parametrize("swap_endpoints", [False, True])
@pytest.mark.parametrize("reverse_rules", [False, True])
def test_relabelling_preserves_physical_outcome(mapping, reverse_order, swap_endpoints, reverse_rules) -> None:
    spec = _spec()
    renamed_spec = _spec(rules=tuple(reversed(RULES))) if reverse_rules else spec
    state = _mixed_world()
    renamed = _relabel(state, mapping, reverse_order=reverse_order, swap_endpoints=swap_endpoints)
    for _ in range(6):
        state = step_causal_world(spec, state)
        renamed = step_causal_world(renamed_spec, renamed)
        assert _relabel(state, mapping, reverse_order=False, swap_endpoints=False) == renamed


def test_the_mixed_world_really_exercises_every_path() -> None:
    """Guard against a vacuous invariance test: the fixture moves a structure,
    reports a diagonal one, forms a bond, scatters a pair, and has a contact."""
    state = _mixed_world()
    assert unresolved_motions(state) and structure_contacts(state)
    after = step_causal_world(_spec(), state)
    assert after.bonds                                                        # the head-on pair bonded
    assert {p.particle_id: p.direction for p in after.particles}[9] in ("E", "W")   # scattered
    assert {(p.particle_id, p.x) for p in after.particles} >= {(1, 3), (2, 4)}      # structure moved
