"""Wrong behaviour v1/v2/v3 keep on purpose, now that a later format (v4 or v5) fixes it.

READ THIS BEFORE TOUCHING ANYTHING IN THIS FILE.

`test_known_defects_causal_kernel.py` holds behaviour that is wrong and NOT
yet fixed anywhere. This file holds behaviour that IS wrong but has been
fixed on a later format's own path (v4 or v5) -- and stays wrong in the old
formats deliberately. These are LEGACY DEFECTS, not features: moving a test
here never makes the behaviour right. Per
`docs/current/CAUSAL_COLLISION_SEMANTICS_V4.md` section 0:
`LANGUAGE_REVISION_GOVERNANCE_V1.md` 9-10 forbid changing what an existing
format means, so v1/v2/v3 keep the old, wrong behaviour for reproducibility
and v4 carries the corrected one.

    A failure here is BAD NEWS. It means a past format's behaviour changed.

If one of these fails, someone edited `_break_existing`, `_resolve_collisions`
or `_grow_chains` without gating the fix behind the new format, and a v1/v2/v3
digest that used to be reproducible no longer is.
The fix is to re-gate the change, not to update this file's expectations.

See also: tests/test_known_defects_causal_kernel.py (unfixed defects),
tests/test_deterministic_causal_kernel.py::
test_an_equal_energy_head_on_scatter_conserves_momentum (the positive case
that was always correct and is unaffected by v4).
"""
from __future__ import annotations

import pytest

from engine.deterministic.causal_kernel import (
    CausalWorldState,
    PhysicalBond,
    _break_existing,
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
    HeatCellSpec,
)

RULE = BondRuleSpec("ew", 0, 0, "E", "W", 3, 2, "W", "E")


def _spec(fmt: str = "deterministic-causal-world-spec-v2") -> CausalWorldSpec:
    return CausalWorldSpec(
        "legacy-semantics-fixture",
        CausalKernelSpec(16, 16, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles",
                          "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4),), (), (), (RULE,), 4, 1, fmt)


def test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour():
    """LEGACY: an unequal-energy head-on scatter still rotates momentum.

    This is the same measurement as
    test_known_defects_causal_kernel.py::
    test_defect_unequal_energy_head_on_same_kind_breaks_momentum, kept here
    as the boundary v1/v2/v3 must not cross now that v4 exists: their
    digests were built on this exact (wrong) behaviour.
    """
    for fmt in ("deterministic-causal-world-spec-v1",
                "deterministic-causal-world-spec-v2"):
        spec = _spec(fmt)
        state = CausalWorldState(
            0,
            (CausalParticleSpec(1, 0, 10, 11, "N", "N", 1),
             CausalParticleSpec(2, 0, 10, 9, "S", "S", 2)),
            (), (), {}, False)
        assert state.momentum(spec) == (0, 1)

        streamed = _stream_free(spec, state)
        scattered = _resolve_collisions(spec, streamed)

        assert scattered.momentum(spec) == (-1, 0), (
            f"{fmt} no longer keeps the legacy 90-degree scatter -- if this "
            "was intentional, it must be gated behind FORMAT_V4 instead of "
            "changed for every format")
        with pytest.raises(AssertionError, match="changed momentum"):
            step_causal_world(spec, state)


def test_v1_v2_v3_break_keeps_legacy_orientation_rotation():
    """LEGACY: breaking a bond still overwrites `orientation` to match the
    release `direction`, on every pre-v4 format.
    """
    for fmt in ("deterministic-causal-world-spec-v1",
                "deterministic-causal-world-spec-v2"):
        spec = _spec(fmt)
        # Both particles start facing S (orientation), bonded at rest. Release
        # sets direction to W/E; the legacy behaviour also drags orientation
        # along to match, even though nothing declares that a break should
        # touch orientation at all.
        particles = (
            CausalParticleSpec(1, 0, 10, 10, "N", "S", 0),
            CausalParticleSpec(2, 0, 10, 10, "N", "S", 0),
        )
        bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
        heat = (HeatCellSpec(10, 10, 2),)
        state = CausalWorldState(0, particles, heat, bonds, {0: 4}, False)

        broken = _break_existing(spec, state)

        by_id = {item.particle_id: item for item in broken.particles}
        assert by_id[1].orientation == by_id[1].direction, (
            f"{fmt} no longer rotates orientation on break -- if this was "
            "intentional, it must be gated behind FORMAT_V4 instead of "
            "changed for every format")
        assert by_id[2].orientation == by_id[2].direction


def test_v2_chain_motion_stays_on_the_lowest_numbered_member():
    """LEGACY (v2): an id decides where a chain's motion is kept.

    Fixed on v4 (Stage B, StructureState); kept here for v2 reproducibility.
    Moved from test_known_defects_causal_kernel.py on 2026-09-24.

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


# --- v2 _grow_chains legacy defects (moved 2026-09-24, fixed on v5 by GEO v1B) ---

GROW_RULE = BondRuleSpec("ew", 0, 0, "E", "W", 3, 2, "W", "E")


def _grow_spec() -> CausalWorldSpec:
    return CausalWorldSpec(
        "known-defect-fixture",
        CausalKernelSpec(16, 16, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles",
                          "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4),), (), (), (GROW_RULE,), 4, 1,
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


def test_v2_legacy_defect_kernel_is_not_relabelling_invariant():
    """LEGACY DEFECT (v2) -- still physically WRONG: renaming identical particles changes which one bonds.

    Fixed on the v5 path (GEO v1B, 2026-09-24: tests/test_v5_geo_v1b.py 7a/7b -- compatible
    contacts all bond, a face claimed twice picks nobody, both invariant under renaming).
    Kept here only so v2 stays reproducible; moved from test_known_defects_causal_kernel.py.

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
        after = _resolve_collisions(_grow_spec(), _twin_member_state(first, second, arrival))
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


def test_v2_legacy_defect_a_chain_takes_at_most_one_arrival_per_tick():
    """LEGACY DEFECT (v2) -- still physically WRONG: a structural ceiling with no physical cause.

    Fixed on the v5 path (GEO v1B, 2026-09-24: tests/test_v5_geo_v1b.py
    test_several_particles_bond_to_different_faces_in_one_instant; and a moving structure
    grows, test_a_moving_structure_grows). Kept here only so v2 stays reproducible.

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

    after = _resolve_collisions(_grow_spec(), state)
    added = [b for b in after.bonds if {b.left_id, b.right_id} != {1, 2}]
    assert len(added) == 1, "v2 changed: its legacy one-arrival ceiling must stay for reproducibility"
