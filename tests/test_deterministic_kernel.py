import inspect
import json
from pathlib import Path

from engine.deterministic import (
    DeterministicWorldSpec,
    DeterministicWorldState,
    ParticleSpec,
    collide,
    initial_state,
    load_world_spec,
    run_world,
    step_world,
    stream,
)
import engine.deterministic.kernel as kernel_module


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_collision_smoke_v1.json"


def _spec(raw_particles, *, ticks=1, width=16, height=16):
    return DeterministicWorldSpec.from_mapping({
        "format": "deterministic-world-spec-v1",
        "world_id": "test-world",
        "kernel": {
            "kind": "hpp-lattice-v1",
            "deterministic": True,
            "arithmetic": "integer",
            "dimensions": 2,
            "width": width,
            "height": height,
            "boundary": "wrap",
            "collision": "head-on-right-angle-v1",
        },
        "materials": [{"kind": 0, "mass": 1}],
        "initial_particles": raw_particles,
        "execution": {"ticks": ticks},
        "observer": {"hash_interval": max(1, ticks // 4 or 1)},
    })


def test_stream_moves_every_particle_without_a_draw() -> None:
    spec = _spec([
        {"kind": 0, "x": 0, "y": 0, "direction": "N"},
        {"kind": 0, "x": 15, "y": 4, "direction": "E"},
    ])

    moved = stream(spec, initial_state(spec))

    assert set(moved.particles) == {
        ParticleSpec(0, 0, 15, "N"),
        ParticleSpec(0, 0, 4, "E"),
    }


def test_head_on_collision_always_rotates_and_is_an_involution() -> None:
    state = DeterministicWorldState(0, (
        ParticleSpec(0, 5, 5, "N"),
        ParticleSpec(0, 5, 5, "S"),
    ))

    first = collide(state)
    second = collide(first)

    assert set(first.particles) == {
        ParticleSpec(0, 5, 5, "E"),
        ParticleSpec(0, 5, 5, "W"),
    }
    assert second == state


def test_same_spec_repeated_one_hundred_times_is_bit_identical() -> None:
    spec = load_world_spec(EXAMPLE)
    expected = run_world(spec)

    assert all(run_world(spec) == expected for _ in range(100))
    assert all(run_world(spec).digest == expected.digest for _ in range(100))


def test_every_tick_conserves_material_count_and_momentum() -> None:
    spec = load_world_spec(EXAMPLE)
    state = initial_state(spec)
    counts = state.material_counts()
    momentum = state.momentum(spec)

    for _ in range(spec.execution.ticks):
        state = step_world(spec, state)
        assert state.material_counts() == counts
        assert state.momentum(spec) == momentum


def _translate(particle: ParticleSpec, dx: int, dy: int, width: int, height: int) -> ParticleSpec:
    return ParticleSpec(particle.kind, (particle.x + dx) % width, (particle.y + dy) % height, particle.direction)


def test_wrapped_world_is_translation_invariant() -> None:
    spec = load_world_spec(EXAMPLE)
    translated_raw = spec.canonical()
    for particle in translated_raw["initial_particles"]:
        particle["x"] = (particle["x"] + 7) % spec.kernel.width
        particle["y"] = (particle["y"] + 11) % spec.kernel.height
    translated = DeterministicWorldSpec.from_mapping(translated_raw)

    original_final = run_world(spec).final_state
    translated_final = run_world(translated).final_state

    assert set(translated_final.particles) == {
        _translate(item, 7, 11, spec.kernel.width, spec.kernel.height)
        for item in original_final.particles
    }


def _rotate_particle(item: ParticleSpec, size: int) -> ParticleSpec:
    direction = {"N": "E", "E": "S", "S": "W", "W": "N"}[item.direction]
    return ParticleSpec(item.kind, size - 1 - item.y, item.x, direction)


def test_square_world_is_quarter_turn_invariant() -> None:
    spec = load_world_spec(EXAMPLE)
    size = spec.kernel.width
    rotated_raw = spec.canonical()
    rotated_raw["initial_particles"] = [
        _rotate_particle(item, size).canonical() for item in spec.initial_particles
    ]
    rotated = DeterministicWorldSpec.from_mapping(rotated_raw)

    original_final = run_world(spec).final_state
    rotated_final = run_world(rotated).final_state

    assert set(rotated_final.particles) == {
        _rotate_particle(item, size) for item in original_final.particles
    }


def test_hash_checkpoints_are_observation_only() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["observer"]["hash_interval"] = 1
    dense = DeterministicWorldSpec.from_mapping(raw)
    raw["observer"]["hash_interval"] = 64
    sparse = DeterministicWorldSpec.from_mapping(raw)

    assert run_world(dense).final_state == run_world(sparse).final_state


def test_kernel_has_no_random_source_or_seed_interface() -> None:
    source = inspect.getsource(kernel_module)

    assert "import random" not in source
    assert "SeededEventSource" not in source
    assert "choice_index" not in source
    assert "seed" not in inspect.signature(step_world).parameters
