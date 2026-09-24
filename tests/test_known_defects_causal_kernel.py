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


# test_defect_kernel_is_not_relabelling_invariant and
# test_defect_a_chain_takes_at_most_one_arrival_per_tick were here.
#
# FIXED on the v5 path (2026-09-24, GEO v1B -- docs/current/A_MICRO_V5_GEO_V1B_PLAN.md):
# v5 judges every contact against the frozen pre-event state, bonds all
# compatible contacts in one instant, and halts (choosing nobody) when one face
# is claimed twice -- all invariant under renaming. v2 keeps both defects,
# still physically wrong, for reproducibility. See:
#   tests/test_legacy_causal_semantics.py::
#     test_v2_legacy_defect_kernel_is_not_relabelling_invariant
#     test_v2_legacy_defect_a_chain_takes_at_most_one_arrival_per_tick
#   tests/test_v5_geo_v1b.py (7a, 7b, one-instant multi-bond, moving growth)
#
# This file now holds no live defect. It stays as the place for the next one
# found that is fixed nowhere.


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
