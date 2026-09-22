"""GT-1 (legacy physical sanity test): does A0's own bond physics really run heat -> bond -> particle?

Status: **not the canonical mediator benchmark.** That role belongs to
GT-M1 (see `gt_m1_mediator.py`), a purpose-built synthetic world with a
public control on the mediator itself. GT-1 is kept as a *reference*
sanity check against the real physics engine, not the answer key B0.7 is
graded against -- see the caveat below on what its third intervention
actually shows.

This is the world `tests/test_deterministic_missing_link_investigator.py`
calls "the hidden mediator scenario" and grades B0.7 against. That test only
checks what B0.7's own code concludes about it -- it never independently
confirms, from A alone, that heat actually mediates through the bond rather
than (say) heat happening to correlate with particle motion for some other
reason. This module is that independent confirmation, built without
importing anything B0.7 touches.

Caveat (why this is not the canonical benchmark): A0 exposes no public
control that flips the bond independently of heat. Intervention 3 below
blocks the bond by placing the two particles far enough apart that they can
never collide -- but that changes the *initial world*, not just B, so
strictly this shows "in a world where no bond can ever form, heat has no
route to the particle" rather than "blocking B severs A's effect on C" in
the narrower, single-world sense GT-M1 tests. Still useful evidence, just
not a clean mediator proof on its own.

The candidate structure, named in A0's own vocabulary:

    A = heat_cell(10, 10).energy      (the source_role in the B0.7 test)
    B = bond(particle_a, particle_b)  (exists / broken -- the mediator)
    C = particle_a.kinetic_energy     (the outcome the B0.7 test reads)

Three interventions, run directly against `causal_kernel.step_causal_world`
(never through `run_traced` or any B0.4+ observation layer):

  intervention 1 (A changes B):
      heat=0 vs heat=2 at the shared cell, holding everything else fixed.
      A A0 bond only breaks when local heat covers its `break_heat` cost
      (see `_break_existing` in causal_kernel.py) -- so this is not a guess
      about the rule, it is the rule, read from the same module this audit
      drives.

  intervention 2 (B changes C):
      compare the run where the bond breaks against the run where it does
      not, holding heat fixed at 0 in both -- forced instead by whether the
      two particles are placed to collide and bond in the first place.

  intervention 3, the mediator-defining check (block B, vary A):
      place the two particles far apart so they can never collide and bond
      -- B is now pinned at "no bond, ever" regardless of heat -- then vary
      heat exactly as in intervention 1. If A really only reaches C through
      B, particle_a.kinetic_energy at the final tick must be identical in
      both runs, because there is no bond left for heat to interact with.

All three must pass for GT-1 to seal as VALID. If the third fails while the
first two pass, that means A0 has some route from heat to the particle that
does not go through the bond -- which would mean the existing B0.7 test is
grading against a mediator structure that is not actually true of A, not a
B0.7 bug.
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.deterministic.causal_kernel import initial_causal_state, step_causal_world
from engine.deterministic.causal_spec import CausalWorldSpec

from .report import GroundTruthReport

ROOT = Path(__file__).resolve().parents[1]
BASE_WORLD = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

TARGET_PARTICLE_ID = 1  # particle_a in the base spec: starts at (9, 10) heading E


def _load_base() -> dict:
    return json.loads(BASE_WORLD.read_text(encoding="utf-8"))


def _spec_with(raw_overrides: dict, world_id: str) -> CausalWorldSpec:
    raw = _load_base()
    raw.update(raw_overrides)
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


def _run_all_ticks(spec: CausalWorldSpec) -> list:
    """Every post-tick state, in order -- the plain A0 loop, no observer."""
    state = initial_causal_state(spec)
    states = [state]
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        states.append(state)
    return states


def _bond_ever_exists(states: list, particle_id: int) -> bool:
    return any(any(particle_id in (bond.left_id, bond.right_id) for bond in state.bonds)
               for state in states)


def _final_kinetic_energy(states: list, particle_id: int) -> int:
    final = states[-1]
    (particle,) = (item for item in final.particles if item.particle_id == particle_id)
    return particle.kinetic_energy


def _spec_no_collision(heat_energy: int, world_id: str) -> CausalWorldSpec:
    """particle_a and particle_b placed far enough apart that they never
    meet, so no bond is ever formed -- B pinned at "no bond, ever" by
    construction, independent of whatever heat does."""
    raw = _load_base()
    raw["particles"] = [
        {"particle_id": 1, "kind": 0, "x": 0, "y": 0, "direction": "E", "orientation": "E", "kinetic_energy": 0},
        {"particle_id": 2, "kind": 0, "x": 20, "y": 20, "direction": "W", "orientation": "W", "kinetic_energy": 0},
    ]
    raw["heat"] = [{"x": 10, "y": 10, "energy": heat_energy}] if heat_energy else []
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


def audit_world1_mediator() -> GroundTruthReport:
    base_raw = _load_base()
    base_spec = CausalWorldSpec.from_mapping(base_raw)
    report = GroundTruthReport(
        world_id="GT-1-mediator-heat-bond-particle",
        world_spec_digest=base_spec.digest,
        expected_edges=(("heat_cell.energy", "bond.exists"), ("bond.exists", "particle.kinetic_energy")),
        forbidden_edges=(("heat_cell.energy", "particle.kinetic_energy"),),
    )

    try:
        # --- intervention 1: A changes B (heat 0 vs 2, particles collide as in the base spec) ---
        spec_heat_0 = _spec_with({"heat": []}, "gt1-heat-0")
        spec_heat_2 = _spec_with({"heat": [{"x": 10, "y": 10, "energy": 2}]}, "gt1-heat-2")
        states_heat_0 = _run_all_ticks(spec_heat_0)
        states_heat_2 = _run_all_ticks(spec_heat_2)
        bond_survives_at_0 = _bond_ever_exists(states_heat_0, TARGET_PARTICLE_ID) and \
            any(TARGET_PARTICLE_ID in (b.left_id, b.right_id) for b in states_heat_0[-1].bonds)
        bond_survives_at_2 = _bond_ever_exists(states_heat_2, TARGET_PARTICLE_ID) and \
            any(TARGET_PARTICLE_ID in (b.left_id, b.right_id) for b in states_heat_2[-1].bonds)
        a_changes_b = bond_survives_at_0 != bond_survives_at_2
        report.add("A_changes_B_heat_toggles_final_bond_state", a_changes_b,
                   expected="bond survival differs between heat=0 and heat=2",
                   observed={"bond_survives_final_tick_heat_0": bond_survives_at_0,
                             "bond_survives_final_tick_heat_2": bond_survives_at_2},
                   detail="A0's own break_heat rule: heat=0 cannot pay the bond's break_heat cost, "
                          "heat=2 can (base world declares break_heat=2)")

        # --- intervention 2: B changes C ---
        # A0 exposes no public control that flips the bond directly -- forcibly
        # clearing `state.bonds` outside `_break_existing` does not run its release
        # logic, so it silently deletes the stored energy instead of transferring
        # it (confirmed by hand: the particle's kinetic_energy stays 0). Bypassing
        # the kernel's own state-transition function is not a fair intervention on
        # B, so this reuses the two runs intervention 1 already produced: same
        # collision geometry, differing only in whether the bond that forms at
        # tick 1 goes on to break. That the *only* A0-legal way to move B is
        # through heat is itself part of what "B mediates" means here.
        kinetic_with_bond = _final_kinetic_energy(states_heat_0, TARGET_PARTICLE_ID)
        kinetic_with_broken_bond = _final_kinetic_energy(states_heat_2, TARGET_PARTICLE_ID)
        b_changes_c = kinetic_with_bond != kinetic_with_broken_bond
        report.add("B_changes_C_bond_state_changes_final_kinetic_energy", b_changes_c,
                   expected="particle_a.kinetic_energy differs between bond-persists and bond-breaks",
                   observed={"kinetic_energy_bond_persists": kinetic_with_bond,
                             "kinetic_energy_bond_breaks": kinetic_with_broken_bond},
                   detail="same collision geometry (heat=0 vs heat=2), differing only in whether the "
                          "bond formed at tick 1 survives to the final tick")

        # --- intervention 3, the defining check: block B, vary A, see if C still moves ---
        spec_blocked_heat_0 = _spec_no_collision(0, "gt1-blocked-heat-0")
        spec_blocked_heat_2 = _spec_no_collision(2, "gt1-blocked-heat-2")
        states_blocked_0 = _run_all_ticks(spec_blocked_heat_0)
        states_blocked_2 = _run_all_ticks(spec_blocked_heat_2)
        no_bond_ever_0 = not _bond_ever_exists(states_blocked_0, TARGET_PARTICLE_ID)
        no_bond_ever_2 = not _bond_ever_exists(states_blocked_2, TARGET_PARTICLE_ID)
        if not (no_bond_ever_0 and no_bond_ever_2):
            report.mark_ambiguous(
                "B_blocked_precondition",
                "the far-apart placement was expected to prevent any bond from ever forming, "
                "but a bond appeared anyway -- the blocking construction itself is not valid, "
                "so intervention 3 cannot be judged from this world",
            )
        else:
            kinetic_blocked_0 = _final_kinetic_energy(states_blocked_0, TARGET_PARTICLE_ID)
            kinetic_blocked_2 = _final_kinetic_energy(states_blocked_2, TARGET_PARTICLE_ID)
            blocking_b_severs_a_to_c = kinetic_blocked_0 == kinetic_blocked_2
            report.add("blocking_B_severs_A_to_C_effect", blocking_b_severs_a_to_c,
                       expected="particle_a.kinetic_energy identical across heat=0 and heat=2 once no bond can ever form",
                       observed={"kinetic_energy_blocked_heat_0": kinetic_blocked_0,
                                 "kinetic_energy_blocked_heat_2": kinetic_blocked_2},
                       detail="with B pinned at 'no bond, ever' by particle placement, heat's only "
                              "declared route to the particle in A0 (via bond break_heat) is unavailable")
    except Exception as error:  # noqa: BLE001 -- this audit must report, never crash the whole run
        report.mark_audit_error(f"{type(error).__name__}: {error}")

    return report
