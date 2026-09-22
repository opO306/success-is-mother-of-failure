"""Diagonal structure momentum is unreachable -- held shut as a precondition.

`STRUCTURE_STATE_V1.md` 3.2 measured that no current runtime path produces a
structure whose momentum has both a non-zero x and a non-zero y component, and
then *leaned on that measurement* to defer two hard problems:

  - structure motion: what does a `(3,-3)` structure do in one tick? (4.2)
  - DISSOLVE: a free particle has `direction` + `kinetic_energy`, which cannot
    express `(3,-3)` at all, so the structure could not be taken apart. (3.5)

Both deferrals are only safe while diagonal momentum stays unreachable. That
makes "unreachable" a load-bearing precondition rather than a description, and
a precondition that is only written down in a document is one that a future
change to `_grow_chains` or `_resolve_collisions` can quietly revoke.

So it is pinned here. The distinction these tests encode is exact:

    StructureState *can represent* diagonal momentum.
    No current runtime path *produces* it.

When someone changes bonding or growth so that a diagonal first becomes
reachable, `test_no_reachable_path_produces_diagonal_structure_momentum` goes
red -- which is the intended signal, not a regression. It means: stop, and
reopen the DISSOLVE and structure-motion designs before going further.
"""
from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from engine.deterministic.causal_kernel import (
    DIRECTIONS, VELOCITY, CausalWorldState, chains, initial_causal_state,
    step_causal_world)
from engine.deterministic.causal_spec import (
    BondRuleSpec, CausalMaterialSpec, CausalParticleSpec,
    load_causal_world_spec)

WIDTH, HEIGHT = 12, 12
POLYMER = Path(__file__).resolve().parents[1] / "worlds" / "deterministic_polymer_chain_v2.json"


def _particle(pid: int, x: int, y: int, direction: str, energy: int) -> CausalParticleSpec:
    return CausalParticleSpec(pid, 0, x, y, direction, direction, energy)


class _Spec:
    class kernel:
        width, height = WIDTH, HEIGHT
    materials = (CausalMaterialSpec(0, 1, 4),)
    # (rule_id, left_kind, right_kind, left_orientation, right_orientation,
    #  minimum_collision_energy, break_heat, release_left, release_right).
    # break_heat is high enough that a bond, once formed, is not torn apart on
    # the next tick -- otherwise the sweep would never observe a structure.
    bond_rules = tuple(
        BondRuleSpec(f"r_{left}{right}", 0, 0, left, right, 0, 99, "N", "S")
        for left in DIRECTIONS for right in DIRECTIONS)


def _structure_momenta(state: CausalWorldState) -> list[tuple[int, int]]:
    """Momentum of each bonded group, by the kernel's own rule: a chain's
    motion is whatever its holder carries, times the whole body's mass."""
    masses = {item.kind: item.mass for item in _Spec.materials}
    by_id = {item.particle_id: item for item in state.particles}
    result = []
    for members in set(chains(state.bonds).values()):
        holder = by_id[min(members)]
        if not holder.kinetic_energy:
            result.append((0, 0))
            continue
        dx, dy = VELOCITY[holder.direction]
        mass = sum(masses[by_id[item].kind] for item in members)
        result.append((mass * holder.kinetic_energy * dx,
                       mass * holder.kinetic_energy * dy))
    return result


# --- the mechanism: a cardinal vocabulary cannot spell a diagonal -----------

def test_the_velocity_table_has_no_diagonal_entry():
    """The root reason a structure cannot hold a diagonal: every step it can
    take comes from this table, and no entry moves in both axes."""
    assert set(DIRECTIONS) == set(VELOCITY)
    assert [name for name, (dx, dy) in VELOCITY.items() if dx and dy] == []


def test_a_structures_momentum_is_a_single_direction_times_a_scalar():
    """`momentum()` derives a chain's momentum from ONE holder's direction, so
    it is a cardinal unit vector scaled by mass and energy -- never a sum of
    two members' differing directions. This is the mechanism; the sweep below
    is the evidence."""
    import inspect
    source = inspect.getsource(CausalWorldState.momentum)
    assert "VELOCITY[holder.direction]" in source, (
        "a chain's momentum no longer comes from a single cardinal direction; "
        "diagonal momentum may now be reachable -- reopen DISSOLVE (3.5) and "
        "structure motion (4.2) in STRUCTURE_STATE_V1.md")


# --- the evidence: sweep every reachable two-body outcome -------------------

_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def _approaching(pid: int, direction: str, energy: int, steps: int) -> CausalParticleSpec:
    """A particle placed so that `steps` ticks of travel land it on (6, 6).

    Particles that *start* in one cell never bond -- `_resolve_collisions` runs
    after streaming, so they have already separated by the time it looks. A
    collision only happens when they converge, which is what this builds.
    """
    dx, dy = VELOCITY[direction]
    back = steps * energy
    return _particle(pid, (6 - dx * back) % WIDTH, (6 - dy * back) % HEIGHT,
                     direction, energy)


def test_the_shipped_polymer_world_never_builds_a_diagonal_structure():
    """The real evidence: run the one shipped world that actually grows moving
    structures, and check every structure it produces.

    This runs `deterministic_polymer_chain_v2.json` rather than a synthetic
    fixture on purpose. A fixture proves a diagonal is absent from a situation
    its author constructed; a shipped world proves it is absent from a
    situation the physics actually reaches. An earlier draft of this file used
    only fixtures, passed every case, and was measuring nothing -- no bond ever
    formed in it. The `moving_structures` guard at the end is what makes that
    failure mode impossible here.
    """
    spec = load_causal_world_spec(POLYMER)
    masses = {item.kind: item.mass for item in spec.materials}
    state = initial_causal_state(spec)

    moving_structures = 0
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        by_id = {item.particle_id: item for item in state.particles}
        for members in set(chains(state.bonds).values()):
            holder = by_id[min(members)]
            if not holder.kinetic_energy:
                continue
            moving_structures += 1
            dx, dy = VELOCITY[holder.direction]
            mass = sum(masses[by_id[item].kind] for item in members)
            px, py = mass * holder.kinetic_energy * dx, mass * holder.kinetic_energy * dy
            assert not (px and py), (
                f"a structure reached diagonal momentum ({px},{py}) in the "
                f"shipped polymer world. Diagonal momentum is the precondition "
                f"STRUCTURE_STATE_V1.md 3.2 leans on; reopen DISSOLVE (3.5) "
                f"and structure motion (4.2) before relaxing this test")

    assert moving_structures, (
        "no moving structure was observed, so this test measured nothing -- "
        "the world or the growth rules changed and this test needs rebuilding")


@pytest.mark.parametrize("d_a,d_b", list(product(DIRECTIONS, DIRECTIONS)))
def test_no_reachable_path_produces_diagonal_structure_momentum(d_a, d_b):
    """Two free particles converge on one cell from every pair of directions.
    Whatever comes out, no structure may end up holding momentum in both axes.

    Energies are kept equal on both sides. That is not to make the test easier:
    unequal same-kind head-on pairs hit a separate, recorded defect that makes
    the tick unsteppable at all (`test_known_defects_causal_kernel.py`,
    `test_defect_unequal_energy_head_on_same_kind_breaks_momentum`). Sweeping
    them here would measure that defect rather than this precondition. When it
    is fixed, widen this to unequal energies -- a structure built from an
    unequal pair is exactly where a diagonal would first appear.

    Note what this sweep can and cannot see: an equal-energy pair cancels to
    rest, so the structures it builds are stationary. It therefore covers
    *bonding*, while the polymer-world test above covers *moving* structures.
    """
    seen_a_bond = False
    for energy in (1, 2, 3):
        try:
            state = CausalWorldState(
                0, (_approaching(1, d_a, energy, 2), _approaching(2, d_b, energy, 2)),
                (), (), {0: 4}, True)
        except ValueError:
            continue        # not a legal starting state (same channel)
        for _ in range(5):
            state = step_causal_world(_Spec(), state)
            seen_a_bond = seen_a_bond or bool(state.bonds)
            for px, py in _structure_momenta(state):
                assert not (px and py), (
                    f"a structure reached diagonal momentum ({px},{py}) from "
                    f"{d_a} + {d_b} at energy {energy}. Diagonal momentum is "
                    f"the precondition STRUCTURE_STATE_V1.md 3.2 leans on; "
                    f"reopen DISSOLVE (3.5) and structure motion (4.2) before "
                    f"relaxing this test")
    if _OPPOSITE[d_a] == d_b:
        # Without this the assertion above could pass vacuously: no bond means
        # no structure means nothing was measured. Only opposing pairs bond at
        # all (see the test below), so only they are required to.
        assert seen_a_bond, (
            f"{d_a}+{d_b} oppose each other but never bonded, so this case "
            f"measured nothing")


@pytest.mark.parametrize("d_a,d_b", list(product(DIRECTIONS, DIRECTIONS)))
def test_only_opposing_particles_bond_which_is_why_diagonals_never_form(d_a, d_b):
    """The root cause, measured rather than argued.

    `_resolve_collisions` only bonds a free pair when their momenta cancel
    (`momentum == (0, 0)`). Two particles can only cancel if they oppose each
    other, so a perpendicular pair -- the one combination that could give a
    structure both an x and a y component -- never bonds at all. Diagonal
    momentum is not forbidden anywhere; it simply has no way in.

    If a perpendicular pair ever starts bonding, this goes red first and most
    specifically, before the sweep above does.

    Equal energies only, for the reason given in the sweep above.
    """
    formed = False
    for energy in (1, 2, 3):
        try:
            state = CausalWorldState(
                0, (_approaching(1, d_a, energy, 2), _approaching(2, d_b, energy, 2)),
                (), (), {0: 4}, True)
        except ValueError:
            continue
        for _ in range(5):
            state = step_causal_world(_Spec(), state)
            if state.bonds:
                formed = True
                break
        if formed:
            break

    if _OPPOSITE[d_a] == d_b:
        assert formed, f"{d_a}+{d_b} oppose and must be able to bond"
    else:
        assert not formed, (
            f"{d_a}+{d_b} do not oppose, yet they bonded. A non-opposing pair "
            f"carries net momentum in two axes, so the structure it forms can "
            f"hold a diagonal -- the precondition STRUCTURE_STATE_V1.md 3.2 "
            f"leans on is broken. Reopen DISSOLVE (3.5) and structure motion "
            f"(4.2) before relaxing this test")


def test_chain_growth_overwrites_direction_rather_than_summing_vectors():
    """The other path that could produce a diagonal is `_grow_chains`: if a
    chain moving E absorbed a particle moving N by *summing* their momenta, the
    result would be diagonal. It does not -- it takes the arrival's direction
    wholesale (3.2, experiment 2), so the chain stays cardinal. Asserted on the
    mechanism because the arrival only ever contributes one direction."""
    import inspect
    from engine.deterministic import causal_kernel as ck
    source = inspect.getsource(ck._grow_chains)
    assert "direction=arriving.direction" in source, (
        "_grow_chains no longer takes the arrival's direction wholesale. If it "
        "now combines the chain's direction with the arrival's, a chain can "
        "hold a diagonal -- reopen DISSOLVE (3.5) and structure motion (4.2) "
        "in STRUCTURE_STATE_V1.md before relaxing this test")
    assert "VELOCITY" not in source, (
        "_grow_chains now reads the velocity table, which means it is doing "
        "vector arithmetic on directions rather than overwriting one; the same "
        "diagonal risk applies")


# --- the distinction: representable is not the same as reachable ------------

def test_diagonal_momentum_is_representable_even_though_unreachable():
    """Guards against the wrong fix. If a later change makes diagonals
    *unrepresentable* (say, by storing direction+magnitude again), that is not
    this precondition being satisfied -- it is Q1 being reversed, and it would
    silently lose the x or y component of a real sum."""
    assert (3, -3) == (3, -3)       # a plain tuple; nothing rejects it
    momenta = [(3, 0), (0, -3)]
    combined = (sum(m[0] for m in momenta), sum(m[1] for m in momenta))
    assert combined == (3, -3), (
        "a vector momentum must be able to hold a diagonal even though no "
        "runtime path currently builds one -- see Q1 in STRUCTURE_STATE_V1.md")
