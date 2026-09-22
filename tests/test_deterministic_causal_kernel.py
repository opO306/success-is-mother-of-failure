import inspect
import json
from dataclasses import replace
from pathlib import Path

from engine.deterministic import (
    CausalWorldSpec,
    HeatCellSpec,
    initial_causal_state,
    load_causal_world_spec,
    run_causal_world,
    step_causal_world,
)
import engine.deterministic.causal_kernel as causal_kernel
from engine.deterministic.causal_kernel import PhysicalBond
from engine.deterministic.causal_spec import (
    FORMAT_V4,
    BondRuleSpec,
    CausalKernelSpec,
    CausalMaterialSpec,
    CausalParticleSpec,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _spec(raw=None):
    return CausalWorldSpec.from_mapping(raw or json.loads(EXAMPLE.read_text(encoding="utf-8")))


def test_particles_bond_from_collision_then_local_heat_breaks_the_bond() -> None:
    spec = _spec(); initial = initial_causal_state(spec)

    bonded = step_causal_world(spec, initial)
    separated = step_causal_world(spec, bonded)

    assert len(bonded.bonds) == 1
    assert bonded.bonds[0].stored_energy == 4
    assert all(item.kinetic_energy == 0 for item in bonded.particles)
    assert bonded.total_energy() == initial.total_energy() == 6
    assert len(separated.bonds) == 0
    assert [item.kinetic_energy for item in separated.particles] == [3, 3]
    assert separated.heat == ()
    assert {(item.x, item.direction) for item in separated.particles} == {(9, "W"), (11, "E")}
    assert separated.total_energy() == initial.total_energy()
    assert separated.momentum(spec) == initial.momentum(spec) == (0, 0)


def test_heat_elsewhere_cannot_break_a_bond() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 0, "y": 0, "energy": 2}]
    spec = _spec(raw)

    bonded = step_causal_world(spec, initial_causal_state(spec))
    still_bonded = step_causal_world(spec, bonded)

    assert len(still_bonded.bonds) == 1
    assert still_bonded.heat == (HeatCellSpec(0, 0, 2),)


def test_two_distant_collisions_form_bonds_in_the_same_tick() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["particles"].extend([
        {"particle_id": 3, "kind": 0, "x": 19, "y": 20, "direction": "E", "orientation": "E", "kinetic_energy": 2},
        {"particle_id": 4, "kind": 0, "x": 21, "y": 20, "direction": "W", "orientation": "W", "kinetic_energy": 2},
    ])
    raw["heat"].append({"x": 20, "y": 20, "energy": 2})
    spec = _spec(raw)

    result = step_causal_world(spec, initial_causal_state(spec))

    assert len(result.bonds) == 2
    assert {(bond.x, bond.y) for bond in result.bonds} == {(10, 10), (20, 20)}


def _physical_without_ids(state):
    particles = sorted((p.kind, p.x, p.y, p.direction, p.orientation, p.kinetic_energy) for p in state.particles)
    bonds = sorted((b.rule_id, b.stored_energy, b.x, b.y) for b in state.bonds)
    return particles, bonds, state.heat


def test_particle_labels_do_not_change_physical_history() -> None:
    original = _spec(); raw = original.canonical()
    raw["particles"][0]["particle_id"], raw["particles"][1]["particle_id"] = 102, 101
    relabeled = _spec(raw)

    first = run_causal_world(original)
    second = run_causal_world(relabeled)

    assert _physical_without_ids(first.final_state) == _physical_without_ids(second.final_state)


def test_same_causal_world_repeats_bit_identically() -> None:
    spec = _spec(); expected = run_causal_world(spec)

    assert all(run_causal_world(spec) == expected for _ in range(100))
    assert len({run_causal_world(spec).digest for _ in range(100)}) == 1


def test_every_tick_preserves_material_energy_and_momentum() -> None:
    spec = _spec(); state = initial_causal_state(spec)
    counts, energy, momentum = state.material_counts(), state.total_energy(), state.momentum(spec)

    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        assert state.material_counts() == counts
        assert state.total_energy() == energy
        assert state.momentum(spec) == momentum


def test_causal_kernel_has_no_random_interface() -> None:
    source = inspect.getsource(causal_kernel)

    assert "import random" not in source
    assert "choice_index" not in source
    assert "SeededEventSource" not in source
    assert "seed" not in inspect.signature(step_causal_world).parameters


def test_an_equal_energy_head_on_scatter_conserves_momentum() -> None:
    """The 90-degree scatter (`N/S -> E/W`) inherited from A0, in the case its
    premise actually holds.

    A0 had no `kinetic_energy`: every particle moved at speed 1, so swapping a
    head-on pair's axis always summed to zero either way. With equal energies
    that premise still holds here, and the scatter is correct.

    It does NOT hold for unequal energies on v1/v2/v3 -- see
    `tests/test_legacy_causal_semantics.py::
    test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour`. v4 narrows
    the scatter to equal energies (see the `test_v4_*` tests below); this
    test is the boundary either fix has to preserve, since removing the
    scatter outright would change this too.
    """
    spec = _spec()
    state = causal_kernel.CausalWorldState(
        0,
        (causal_kernel.CausalParticleSpec(1, 0, 10, 11, "N", "N", 2),
         causal_kernel.CausalParticleSpec(2, 0, 10, 9, "S", "S", 2)),
        (), (), {}, False)
    assert state.momentum(spec) == (0, 0)

    after = step_causal_world(spec, state)

    assert after.momentum(spec) == (0, 0)
    assert after.total_energy() == state.total_energy()
    assert {item.direction for item in after.particles} == {"E", "W"}


# --- causal v4 Stage A: corrected collision semantics ------------------------
#
# docs/current/CAUSAL_COLLISION_SEMANTICS_V4.md. v4 is `experimental`; these
# tests hold Stage A's two fixes (no implicit orientation rotation, scatter
# narrowed to equal energy) shut on the FORMAT_V4 code path only. v1/v2/v3
# keep the legacy behaviour these fixes replace -- see
# tests/test_legacy_causal_semantics.py.

def _v4_spec(rules: tuple[BondRuleSpec, ...] = ()) -> CausalWorldSpec:
    return CausalWorldSpec(
        "v4-stage-a-fixture",
        CausalKernelSpec(16, 16, "wrap", "integer", True,
                         ("break_existing_bonds", "stream_free_particles",
                          "resolve_local_collisions")),
        (CausalMaterialSpec(0, 1, 4),), (), (), rules, 4, 1, FORMAT_V4)


def test_v4_scatter_does_not_rotate_orientation() -> None:
    """v4's equal-energy scatter changes `direction` only; `orientation` is
    left exactly as it was, since nothing declares that a scatter should
    touch it (CAUSAL_COLLISION_SEMANTICS_V4.md 1.1, 2.1)."""
    spec = _v4_spec()
    state = causal_kernel.CausalWorldState(
        0,
        (CausalParticleSpec(1, 0, 10, 11, "N", "S", 2),
         CausalParticleSpec(2, 0, 10, 9, "S", "N", 2)),
        (), (), {}, False)

    after = step_causal_world(spec, state)

    by_id = {item.particle_id: item for item in after.particles}
    assert {item.direction for item in after.particles} == {"E", "W"}
    assert by_id[1].orientation == "S", "v4 must not rotate orientation on scatter"
    assert by_id[2].orientation == "N", "v4 must not rotate orientation on scatter"
    assert after.momentum(spec) == (0, 0)
    assert after.total_energy() == state.total_energy()


def test_v4_bond_break_does_not_rotate_orientation() -> None:
    """v4's break sets `direction` from the rule's release, and leaves
    `orientation` untouched (CAUSAL_COLLISION_SEMANTICS_V4.md 1.1, 2.1)."""
    rule = BondRuleSpec("ew", 0, 0, "E", "W", 3, 2, "W", "E")
    spec = _v4_spec((rule,))
    particles = (
        CausalParticleSpec(1, 0, 10, 10, "N", "S", 0),
        CausalParticleSpec(2, 0, 10, 10, "N", "S", 0),
    )
    bonds = (PhysicalBond(1, 2, "ew", 4, 10, 10),)
    heat = (HeatCellSpec(10, 10, 2),)
    state = causal_kernel.CausalWorldState(0, particles, heat, bonds, {0: 4}, False)

    broken = causal_kernel._break_existing(spec, state)

    by_id = {item.particle_id: item for item in broken.particles}
    assert by_id[1].direction == "W" and by_id[1].orientation == "S"
    assert by_id[2].direction == "E" and by_id[2].orientation == "S"


def test_v4_unequal_energy_head_on_leaves_particles_unchanged() -> None:
    """v4's narrowed scatter does not fire on an unequal-energy head-on pair,
    and no other declared rule matches -- so the tick leaves them as they
    are. CAUSAL_COLLISION_SEMANTICS_V4.md 1.2 shows this is the unique
    conservation-preserving outcome given the existing state representation,
    not new physics.

    v1/v2/v3 hit the same setup and break momentum instead -- see
    tests/test_legacy_causal_semantics.py::
    test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour.
    """
    spec = _v4_spec()
    state = causal_kernel.CausalWorldState(
        0,
        (CausalParticleSpec(1, 0, 10, 11, "N", "N", 1),
         CausalParticleSpec(2, 0, 10, 9, "S", "S", 2)),
        (), (), {}, False)
    assert state.momentum(spec) == (0, 1)

    after = step_causal_world(spec, state)

    assert after.momentum(spec) == (0, 1)
    assert after.total_energy() == state.total_energy()
    by_id = {item.particle_id: item for item in after.particles}
    assert by_id[1].direction == "N" and by_id[1].kinetic_energy == 1
    assert by_id[2].direction == "S" and by_id[2].kinetic_energy == 2


def test_v4_leaves_the_shipped_v1_digest_unchanged() -> None:
    """The governance constraint made concrete: v4's corrections must not
    leak onto any other format's code path. Pinned to the digest measured on
    this repository's shipped v1 world with Stage A's gating in place --
    unchanged from the digest measured before Stage A existed
    (test_particle_labels_do_not_change_physical_history and friends above
    exercise the same spec; this test exists so a future edit that widens the
    `FORMAT_V4` gate too far is caught here specifically)."""
    spec = _spec()  # the shipped deterministic_bond_cycle_v1.json, FORMAT (v1)
    assert spec.format != FORMAT_V4

    run = run_causal_world(spec)

    assert run.digest == (
        "2138518494c89e15d624932ee11cedd402f4f77ead4c4c10170ab8534793ce79")
