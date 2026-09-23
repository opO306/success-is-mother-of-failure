"""G10: the physical probe (constitution art. 25) -- gates from the G10 design.

  direct-write   B-side code has no path to A's state or physics
  locality       the probe acts only on its neighbouring cell
  conservation   solid matter and energy are conserved every tick
  failure        a physically impossible step changes nothing and says nothing
  id-leak        B sees no real action, direction, channel or world name
  capacity       the probe holds at most one unit
  trace/seal     programs are journaled; a program changed after sealing is caught
  tool           a built structure counts only if it changes what happens next
  primitive      exactly five purpose-free primitives
  law            "solids occupy space" is a general law, off by default, digest-neutral
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from itertools import product
from pathlib import Path

import pytest

from engine.deterministic.blind_probe import (
    BlindProbeProgram, ProbePrediction, control_program, probe_prediction_holds, structure_has_effect,
)
from engine.deterministic.blind_probe_evaluator import INVALID_ACTION, BlindProbeExecutor, make_probe_session
from engine.deterministic.blind_protocol import audit_protocol
from engine.deterministic.causal_experiment import PredictionSeal
from engine.deterministic.environment_spec import BlockedEdgeSpec, EnvironmentWorldSpec
from engine.deterministic.probe_world import (
    ACTIONS, GRASP, HEAT, MOVE, RELEASE, WAIT, MalformedProbeAction, ProbeSpec, ProbeWorldSpec, apply_action,
    conserved_totals, initial_probe_state, run_probe_world, step_probe_world,
)
from engine.deterministic.research_journal import ResearchJournal, read_journal
from engine.deterministic.research_loop import execute_through_a, seal_predictions
from tests.test_deterministic_blind_hypothesis import _closure

ROOT = Path(__file__).resolve().parents[1]


def _env(cells, occupy=False, water_rate=1, blocked=()):
    raw = copy.deepcopy(json.loads((ROOT / "worlds" / "deterministic_open_water_cycle_v3.json").read_text("utf-8")))
    raw["causal_world"]["kernel"]["width"], raw["causal_world"]["kernel"]["height"] = 6, 4
    raw["causal_world"]["heat"] = []
    raw["solute_kinds"] = 1
    raw["cells"] = [{"x": x, "y": y, "elevation": 0, "water": w, "vapor": 0, "mineral": m, "solutes": [0]}
                    for (x, y, w, m) in cells]
    raw["blocked_edges"] = [{"first": list(a), "second": list(b)} for a, b in blocked]
    raw["energy_boundaries"] = []
    raw["law"].update({"max_heat_transfer": 0, "max_water_transfer": water_rate, "max_solute_transfer": 0,
                       "dissolve_heat_at_least": 100, "max_mineral_conversion": 0, "max_vapor_transfer": 0,
                       "evaporation_heat_at_least": 100, "max_water_phase_change": 0})
    env = EnvironmentWorldSpec.from_mapping(raw)
    return replace(env, law=replace(env.law, solids_occupy_space=True)) if occupy else env


def _world(cells=((3, 0, 0, 2),), probe=(2, 0, 5), channels=("water", "mineral", "heat"), **kwargs):
    return ProbeWorldSpec("PW-TEST", "R-PROBE1", _env(list(cells), **kwargs), ProbeSpec(*probe), channels, 12)


def _mineral(state, x, y):
    return next((c.mineral for c in state.environment.cells if (c.x, c.y) == (x, y)), 0)


# ---------------------------------------------------------------------------
# Primitives and physics.
# ---------------------------------------------------------------------------

def test_exactly_five_purpose_free_primitives() -> None:
    assert set(ACTIONS) == {MOVE, GRASP, RELEASE, HEAT, WAIT}
    assert ACTIONS == {MOVE: True, GRASP: True, RELEASE: True, HEAT: True, WAIT: False}


def test_grasp_reaches_only_the_neighbouring_cell() -> None:
    spec = _world(cells=((4, 0, 0, 3),))                      # two cells east of the probe
    state = apply_action(spec, initial_probe_state(spec), GRASP, "E")
    assert state.holding == 0 and _mineral(state, 4, 0) == 3
    moved = apply_action(spec, apply_action(spec, initial_probe_state(spec), MOVE, "E"), GRASP, "E")
    assert moved.holding == 1 and _mineral(moved, 4, 0) == 2


def test_probe_holds_at_most_one_unit() -> None:
    spec = _world()
    state = apply_action(spec, apply_action(spec, initial_probe_state(spec), GRASP, "E"), GRASP, "E")
    assert state.holding == 1 and _mineral(state, 3, 0) == 1


def test_water_cannot_be_grasped() -> None:
    spec = _world(cells=((3, 0, 5, 0),))
    state = apply_action(spec, initial_probe_state(spec), GRASP, "E")
    assert state.holding == 0


def test_heat_and_move_spend_the_probe_s_own_energy() -> None:
    spec = _world(probe=(2, 0, 1))
    heated = apply_action(spec, initial_probe_state(spec), HEAT, "N")
    assert heated.energy == 0
    assert apply_action(spec, heated, MOVE, "E") == heated     # nothing left: nothing happens


def test_walls_stop_the_probe_and_its_reach() -> None:
    spec = _world(blocked=[((2, 0), (3, 0))])
    state = initial_probe_state(spec)
    assert apply_action(spec, state, MOVE, "E") == state
    assert apply_action(spec, state, GRASP, "E") == state


def test_the_grid_wraps_for_the_probe_as_for_the_fields() -> None:
    spec = _world(probe=(5, 0, 3))
    assert (apply_action(spec, initial_probe_state(spec), MOVE, "E").x) == 0


def test_particle_worlds_are_refused() -> None:
    from engine.deterministic.causal_spec import CausalParticleSpec
    env = _env([(3, 0, 0, 1)])
    particle = CausalParticleSpec(1, 0, 1, 1, "E", "E", 1)
    with_particles = replace(env, causal_world=replace(env.causal_world, particles=(particle,)))
    with pytest.raises(ValueError):
        ProbeWorldSpec("PW", "R", with_particles, ProbeSpec(0, 0, 1), ("water",), 4)


def test_malformed_intents_are_rejected_but_physical_failures_are_not() -> None:
    spec = _world()
    state = initial_probe_state(spec)
    with pytest.raises(MalformedProbeAction):
        apply_action(spec, state, "DIG", "E")
    with pytest.raises(MalformedProbeAction):
        apply_action(spec, state, WAIT, "E")
    assert apply_action(spec, state, RELEASE, "E") == state    # holding nothing: silently nothing


# ---------------------------------------------------------------------------
# Conservation, every tick, over every short program.
# ---------------------------------------------------------------------------

STEPS = [(MOVE, "E"), (MOVE, "W"), (GRASP, "E"), (GRASP, "W"), (RELEASE, "E"), (RELEASE, "N"), (HEAT, "S"), (WAIT, None)]


@pytest.mark.parametrize("occupy", [False, True])
def test_solid_and_energy_are_conserved_every_tick(occupy) -> None:
    spec = _world(cells=((0, 0, 6, 0), (3, 0, 0, 2)), occupy=occupy)
    start = conserved_totals(spec, initial_probe_state(spec))
    for program in product(STEPS, repeat=3):
        state = initial_probe_state(spec)
        for action, direction in program:
            state = step_probe_world(spec, state, action, direction)
            assert conserved_totals(spec, state) == start, program


# ---------------------------------------------------------------------------
# B's side: symbols, leaks, failures.
# ---------------------------------------------------------------------------

REAL_NAMES = ('"MOVE"', '"GRASP"', '"RELEASE"', '"HEAT"', '"WAIT"', '"N"', '"E"', '"S"', '"W"',
              '"water"', '"mineral"', '"heat"', "PW-TEST", "R-PROBE1")


def _session(spec, seed=0):
    descriptor, manifest = make_probe_session(spec, seed)
    return descriptor, manifest, BlindProbeExecutor(spec, manifest)


def test_b_sees_only_neutral_symbols() -> None:
    spec = _world()
    descriptor, manifest, executor = _session(spec)
    a, d = manifest.action_symbol, manifest.direction_symbol
    run = executor.execute(BlindProbeProgram(descriptor.alias_world_id, ((a[GRASP], d["E"]), (a[WAIT], None)))).run
    text = json.dumps({"descriptor": descriptor.canonical(), "run": run.canonical()})
    for name in REAL_NAMES:
        assert name not in text
    assert all(s.startswith("ACT-") for s, _ in descriptor.actions)
    assert all(s.startswith("DIR-") for s in descriptor.directions)


def test_symbols_are_reshuffled_per_seed() -> None:
    spec = _world()
    first, second = make_probe_session(spec, 0)[1], make_probe_session(spec, 1)[1]
    assert first.action_symbol != second.action_symbol and first.direction_symbol != second.direction_symbol


def test_only_public_channels_reach_b() -> None:
    spec = _world(channels=("water",))
    descriptor, manifest, executor = _session(spec)
    run = executor.execute(BlindProbeProgram(descriptor.alias_world_id, ((manifest.action_symbol[WAIT], None),))).run
    assert {ch for cp in run.checkpoints for _x, _y, ch, _v in cp.cells} <= {manifest.channel_symbol["water"]}


def test_physical_failure_is_a_normal_run_with_no_reason() -> None:
    spec = _world(probe=(2, 0, 0))
    descriptor, manifest, executor = _session(spec)
    a, d = manifest.action_symbol, manifest.direction_symbol
    result = executor.execute(BlindProbeProgram(descriptor.alias_world_id, ((a[MOVE], d["E"]),)))
    assert result.status == "success" and result.error_kind is None and result.error_message is None
    assert result.run.checkpoints[0].probe == result.run.checkpoints[1].probe


def test_malformed_program_gets_one_fixed_answer() -> None:
    spec = _world()
    descriptor, manifest, executor = _session(spec)
    for steps in (((("ACT-NOPE"), None),), ((manifest.action_symbol[WAIT], manifest.direction_symbol["E"]),)):
        result = executor.execute(BlindProbeProgram(descriptor.alias_world_id, steps))
        assert result.status == "failed" and result.error_kind == INVALID_ACTION
        assert "WAIT" not in result.error_message and "ACT-NOPE" not in result.error_message


# ---------------------------------------------------------------------------
# Trace and seal.
# ---------------------------------------------------------------------------

def test_program_is_sealed_journaled_and_audited(tmp_path) -> None:
    spec = _world()
    descriptor, manifest, executor = _session(spec)
    a, d = manifest.action_symbol, manifest.direction_symbol
    program = BlindProbeProgram(descriptor.alias_world_id, ((a[GRASP], d["E"]), (a[WAIT], None)))
    journal = ResearchJournal.create(tmp_path / "j.jsonl")
    prediction = ProbePrediction(1, "probe.holding", 1)
    seal_predictions(journal, PredictionSeal(f"SEAL-{program.program_id}", program.program_id,
                                             journal.next_sequence, {"H-PROBE": (prediction,)}))
    result = execute_through_a(journal, executor, program.program_id, program)
    assert result.executed_spec_digest == program.digest
    assert probe_prediction_holds(program, prediction, result.run)
    journal.close()
    assert [e.event_type for e in read_journal(tmp_path / "j.jsonl")] == ["prediction_sealed", "execution_completed"]


def test_a_program_changed_after_sealing_is_caught(tmp_path) -> None:
    spec = _world()
    descriptor, manifest, executor = _session(spec)
    a, d = manifest.action_symbol, manifest.direction_symbol
    sealed = BlindProbeProgram(descriptor.alias_world_id, ((a[GRASP], d["E"]),))
    swapped = BlindProbeProgram(descriptor.alias_world_id, ((a[GRASP], d["W"]),))
    assert sealed.program_id != swapped.program_id
    journal = ResearchJournal.create(tmp_path / "j.jsonl")
    seal_predictions(journal, PredictionSeal(f"SEAL-{sealed.program_id}", sealed.program_id, journal.next_sequence,
                                             {"H": (ProbePrediction(1, "probe.holding", 1),)}))
    execute_through_a(journal, executor, swapped.program_id, swapped)
    journal.close()
    assert "EXECUTION_WITHOUT_PRIOR_SEAL" in audit_protocol(tmp_path / "j.jsonl").violation_codes


def test_prediction_about_a_tick_the_program_never_reaches_is_refused() -> None:
    spec = _world()
    descriptor, manifest, executor = _session(spec)
    program = BlindProbeProgram(descriptor.alias_world_id, ((manifest.action_symbol[WAIT], None),))
    run = executor.execute(program).run
    with pytest.raises(ValueError):
        probe_prediction_holds(program, ProbePrediction(5, "probe.x", 2), run)


# ---------------------------------------------------------------------------
# The law and physical tools.
# ---------------------------------------------------------------------------

def _dam_runs(occupy: bool):
    spec = _world(cells=((0, 0, 8, 0), (3, 0, 0, 2)), occupy=occupy, channels=("water", "mineral"))
    descriptor, manifest, executor = _session(spec)
    a, d = manifest.action_symbol, manifest.direction_symbol
    program = BlindProbeProgram(descriptor.alias_world_id, ((a[GRASP], d["E"]), (a[RELEASE], d["W"]))
                                + tuple((a[WAIT], None) for _ in range(4)))
    control = control_program(program, 2, a[WAIT])
    water = manifest.channel_symbol["water"]
    subjects = tuple(f"cell:{x},{y}:{water}" for x in range(6) for y in range(4))
    return executor.execute(program).run, executor.execute(control).run, subjects


def test_without_the_law_moving_solid_cannot_change_the_water() -> None:
    built, control, water_cells = _dam_runs(occupy=False)
    assert not structure_has_effect(built, control, water_cells)


def test_with_solids_occupying_space_a_placed_unit_changes_where_water_goes() -> None:
    """B is never told this law. It is the *possibility* of a physical tool:
    the same build, compared against doing nothing for as long, changes the
    water elsewhere only when solid matter occupies space."""
    built, control, water_cells = _dam_runs(occupy=True)
    assert structure_has_effect(built, control, water_cells)


def test_the_law_is_off_and_digest_neutral_by_default() -> None:
    env = _env([(0, 0, 1, 1)])
    assert "solids_occupy_space" not in env.law.canonical(env.format)
    on = replace(env, law=replace(env.law, solids_occupy_space=True))
    assert on.law.canonical(on.format)["solids_occupy_space"] is True and on.digest != env.digest


def test_gpu_path_refuses_the_new_law_rather_than_diverging() -> None:
    from engine.deterministic.gpu_environment import _require_cuda
    env = _env([(0, 0, 1, 1)])
    v4 = replace(env, format="deterministic-environment-world-spec-v4",
                 law=replace(env.law, solids_occupy_space=True))
    with pytest.raises(ValueError, match="solids_occupy_space"):
        _require_cuda(v4)


# ---------------------------------------------------------------------------
# Direct-write gate.
# ---------------------------------------------------------------------------

def test_b_side_probe_module_cannot_reach_a_s_physics_or_the_translator() -> None:
    closure = _closure("blind_probe")
    assert not closure & {"probe_world", "environment_kernel", "environment_spec", "blind_probe_evaluator",
                          "causal_kernel", "blind_evaluator", "synthetic_runtime"}
    assert "probe_world" in _closure("blind_probe_evaluator")
