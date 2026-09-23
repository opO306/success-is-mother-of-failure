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


# test_defect_chain_motion_is_stored_on_the_lowest_numbered_member was here.
#
# FIXED on the v4 code path (2026-09-24, causal v4 Stage B --
# docs/current/STRUCTURE_STATE_V1.md): a v4 structure owns its motion as a
# `StructureState`; no member holds it. v2 keeps the old invariant on purpose
# (frozen legacy semantics). See:
#   tests/test_legacy_causal_semantics.py::
#     test_v2_chain_motion_stays_on_the_lowest_numbered_member  (v2)
#   tests/test_v4_structure_state.py::
#     test_chain_motion_belongs_to_the_structure                (v4, new)
#     test_relabelling_preserves_physical_outcome               (v4, new)
#
# The two tests below remain real defects: they live in `_grow_chains`, the
# v2 growth path, and v4 has NO growth path yet (a v4 structure cannot form
# or grow inside a run until the contact graph exists --
# MINIMAL_LOCAL_GEOMETRY_V1.md step 5). When v4 growth is built without them,
# they move to the legacy file the same way.


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


# test_defect_unequal_energy_head_on_same_kind_breaks_momentum was here.
#
# FIXED on the v4 code path (2026-09-22, causal v4 Stage A --
# docs/current/CAUSAL_COLLISION_SEMANTICS_V4.md). v4 narrows the 90-degree
# scatter to equal-energy pairs; an unequal pair matches no other declared
# rule and the tick leaves it unchanged, which section 1.2 of that document
# shows is the unique conservation-preserving outcome.
#
# v1/v2/v3 still exhibit the defect exactly as measured below, and are held
# there on purpose (LANGUAGE_REVISION_GOVERNANCE_V1.md 9-10: an existing
# format's meaning does not change). See:
#   tests/test_legacy_causal_semantics.py::
#     test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour  (v1/v2/v3)
#   tests/test_deterministic_causal_kernel.py::
#     test_v4_unequal_energy_head_on_leaves_particles_unchanged   (v4, new)
#     test_an_equal_energy_head_on_scatter_conserves_momentum     (the
#       positive case the rule was always built for, unaffected by v4)
