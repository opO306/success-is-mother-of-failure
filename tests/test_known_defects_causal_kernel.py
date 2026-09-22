"""Defects the kernel HAS today, recorded on purpose. Do not "fix" these tests.

READ THIS BEFORE TOUCHING ANYTHING IN THIS FILE.

Every other test in this repository asserts that the code is right. These
assert that it is **wrong**, in specific measured ways, so that the wrongness
cannot be forgotten or quietly reintroduced.

    A failure here is GOOD NEWS. It means someone fixed the defect.

When one of these fails, the correct response is NOT to restore the old
behaviour so the test passes again. It is to:

    1. confirm the defect is genuinely gone
    2. delete the characterization test from this file
    3. add the positive test named in its `replace_with` note to the normal
       suite, asserting the property that now holds
    4. update `docs/current/LOCAL_INTERACTION_PRINCIPLES_V1.md`

The failure mode this file exists to prevent: a future agent sees a red test
named "relabelling changes which one bonds", reads it as a regression, and
restores id-ordered physics to make it green. That would undo the fix and
re-bury the defect. Naming the file and the tests for what they are is
cheaper than trusting everyone to read the docstring.

Background: `docs/current/LOCAL_INTERACTION_PRINCIPLES_V1.md`, principle 3 --
when the declared physical state does not single out one outcome, an id must
not pick for it. That is a missing state variable, not a tie to break.
"""
from __future__ import annotations

import pytest

from engine.deterministic.causal_kernel import (
    CausalWorldState,
    PhysicalBond,
    _resolve_collisions,
    _stream_free,
    step_causal_world,
)
from engine.deterministic.causal_spec import (
    BondRuleSpec,
    CausalKernelSpec,
    CausalMaterialSpec,
    CausalParticleSpec,
    CausalWorldSpec,
)

RULE = BondRuleSpec("ew", 0, 0, "E", "W", 3, 2, "W", "E")


def _spec() -> CausalWorldSpec:
    return CausalWorldSpec(
        "known-defect-fixture",
        CausalKernelSpec(16, 16, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles",
                          "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4),), (), (), (RULE,), 4, 1,
        "deterministic-causal-world-spec-v2")


def _twin_member_state(first: int, second: int, arrival: int) -> CausalWorldState:
    """A bonded pair whose two members are physically indistinguishable.

    Same cell, same kind, same orientation, same energy, same free ports. The
    arrival matches the bond rule against either one, so nothing in the
    declared physics says which should take it.
    """
    particles = (
        CausalParticleSpec(first, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(second, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(arrival, 0, 10, 10, "E", "E", 3),
    )
    bonds = (PhysicalBond(min(first, second), max(first, second), "ew", 4, 10, 10),)
    return CausalWorldState(0, particles, (), bonds, {0: 4}, True)


def test_defect_kernel_is_not_relabelling_invariant():
    """DEFECT: renaming identical particles changes which one bonds.

    measured:     2026-09-22
    principle:    3 -- no arbitrary collision ordering
    cause:        `_grow_chains` walks `sorted(members)` and takes the first
                  member whose port accepts the arrival, then breaks.
    replace_with: test_relabelling_preserves_physical_outcome -- assert that
                  the same physical configuration yields the same outcome
                  under any consistent renaming.

    Renaming is not a physical change, so a sound kernel's outcome cannot
    depend on it. This one's does: the arrival always goes to whichever
    member holds the lower number.
    """
    def attaches_to(first: int, second: int, arrival: int) -> str:
        after = _resolve_collisions(_spec(), _twin_member_state(first, second, arrival))
        for bond in after.bonds:
            if {bond.left_id, bond.right_id} != {first, second}:
                partner = bond.left_id if bond.right_id == arrival else bond.right_id
                return "first" if partner == first else "second"
        return "none"

    # The two calls describe the SAME physical situation, listed in a
    # different order. A sound kernel would answer identically.
    assert attaches_to(1, 2, 3) == "first"
    assert attaches_to(2, 1, 3) == "second"
    assert attaches_to(4, 7, 9) != attaches_to(7, 4, 9)


def test_defect_chain_motion_is_stored_on_the_lowest_numbered_member():
    """DEFECT: an id decides where a chain's motion is kept.

    measured:     2026-09-22
    principle:    3 -- no arbitrary collision ordering
    cause:        `CausalWorldState.__post_init__` enforces
                  "a chain carries its motion on its lowest-numbered member".
    replace_with: test_chain_motion_belongs_to_the_structure -- momentum and
                  mass live on the connected component, not on a member
                  chosen by name.

    A chain's momentum is a property of the structure. Here it is parked on
    one member picked by number, so a pure renaming can make a previously
    valid state raise. That the invariant is enforced consistently does not
    make it physical -- it makes the name load-bearing.
    """
    particles = (
        CausalParticleSpec(5, 0, 10, 10, "E", "E", 1),   # holds the motion
        CausalParticleSpec(9, 0, 10, 10, "W", "W", 0),
    )
    bonds = (PhysicalBond(5, 9, "ew", 4, 10, 10),)
    CausalWorldState(0, particles, (), bonds, {0: 4}, True)   # lowest id holds it: accepted

    # Same structure, same motion, same everything physical -- the motion is
    # simply held by the other member. Rejected purely on the numbering.
    swapped = (
        CausalParticleSpec(5, 0, 10, 10, "E", "E", 0),
        CausalParticleSpec(9, 0, 10, 10, "W", "W", 1),   # higher id holds it
    )
    with pytest.raises(ValueError, match="lowest-numbered member"):
        CausalWorldState(0, swapped, (), bonds, {0: 4}, True)


def test_defect_a_chain_takes_at_most_one_arrival_per_tick():
    """DEFECT: a structural ceiling with no physical cause.

    measured:     2026-09-22
    principle:    2 and 4 -- no forced pairwise decomposition, no artificial
                  structural ceiling
    cause:        `_grow_chains` ends each chain's turn with an unconditional
                  `break  # one arrival per chain per tick`.
    replace_with: test_compatible_bonds_commit_together -- two arrivals that
                  need different ports, different energy and conflict in no
                  way should be able to bond in the same local update.

    Nothing in any world specification limits a structure to one new bond per
    tick. Two arrivals reaching opposite free ports do not compete for
    anything, yet the second is made to wait.
    """
    # Two arrivals, both able to bond, at a standing pair with free ports.
    # They differ in heading because two free particles of one kind cannot
    # share a cell travelling the same way; both carry orientation E, which
    # is what the bond rule actually matches on.
    particles = (
        CausalParticleSpec(1, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(2, 0, 10, 10, "W", "W", 0),
        CausalParticleSpec(3, 0, 10, 10, "E", "E", 3),
        CausalParticleSpec(4, 0, 10, 10, "N", "E", 3),
    )
    bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
    state = CausalWorldState(0, particles, (), bonds, {0: 4}, True)

    after = _resolve_collisions(_spec(), state)
    added = [b for b in after.bonds if {b.left_id, b.right_id} != {1, 2}]
    assert len(added) == 1, "the ceiling is gone -- see replace_with in this docstring"


def test_defect_unequal_energy_head_on_same_kind_breaks_momentum():
    """DEFECT: the 90-degree scatter rule rotates momentum instead of conserving it.

    measured:     2026-09-22
    principle:    conservation -- a tick may move momentum around, not change it
    cause:        `_resolve_collisions` applies A0's fixed-speed lattice
                  collision (`N/S -> E/W`) whenever two particles of one kind
                  meet head-on, without checking that they carry equal energy.
                  A0 had no `kinetic_energy` at all: its `momentum()` sums
                  `mass * dx`, so every particle moved at speed 1 and a swapped
                  pair always summed to zero either way. causal added variable
                  energy and inherited the rule without narrowing its premise.
    replace_with: test_unequal_energy_head_on_collision_preserves_momentum --
                  the scatter applies only where its premise holds (equal
                  energy); an unequal pair is left alone and passes through,
                  which is the kernel's existing default when no interaction
                  rule applies.

    The rule was sound in A0 because every particle had the same speed:

        N + S  ->  E + W        momentum 0 -> 0

    With energy it is not:

        N/1 + S/2  ->  E/1 + W/2        momentum (0,1) -> (-1,0)

    Same magnitude, rotated 90 degrees. The kernel's own conservation check
    catches it and raises, so this is not silent -- but it means a legal world
    can be built today that cannot be stepped at all.

    Swept exhaustively over energies 1..4: 48 violating combinations, every one
    of them with unequal energies, and none with equal energies. That is what
    makes "equal energy" the right narrowing rather than a guess.

    Reachability note: the two shipped world files do not trigger this.
    `polymer_chain_v2` mixes energies 2 and 3 but has no same-kind head-on
    meeting. The defect is latent, not theoretical.
    """
    spec = _spec()
    # Converging on (10, 10): same kind, opposite headings, unequal energy.
    state = CausalWorldState(
        0,
        (CausalParticleSpec(1, 0, 10, 11, "N", "N", 1),
         CausalParticleSpec(2, 0, 10, 9, "S", "S", 2)),
        (), (), {}, False)
    assert state.momentum(spec) == (0, 1)

    streamed = _stream_free(spec, state)
    assert streamed.momentum(spec) == (0, 1), "streaming is not where it breaks"

    scattered = _resolve_collisions(spec, streamed)
    assert scattered.momentum(spec) == (-1, 0), (
        "the scatter no longer rotates momentum -- see replace_with above")

    # The kernel's own guard catches it, so the whole tick is unsteppable.
    with pytest.raises(AssertionError, match="changed momentum"):
        step_causal_world(spec, state)


def test_defect_equal_energy_head_on_is_the_case_the_rule_was_built_for():
    """Not a defect: the boundary of the one above, pinned so the fix is aimed.

    Equal energies make the scatter conserve momentum exactly, because both
    sides cancel before and after. A fix that narrows the rule to this case
    must keep this behaviour; a fix that removes the scatter altogether would
    change it, which is a different decision and should be made deliberately.
    """
    spec = _spec()
    state = CausalWorldState(
        0,
        (CausalParticleSpec(1, 0, 10, 11, "N", "N", 2),
         CausalParticleSpec(2, 0, 10, 9, "S", "S", 2)),
        (), (), {}, False)
    assert state.momentum(spec) == (0, 0)
    after = step_causal_world(spec, state)
    assert after.momentum(spec) == (0, 0)
    assert {p.direction for p in after.particles} == {"E", "W"}, (
        "the equal-energy scatter still happens")
