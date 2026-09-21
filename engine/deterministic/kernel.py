"""A0 deterministic CPU reference kernel.

Particles occupy directional channels.  Every tick streams all channels, then
applies the same reversible head-on collision rule at every location.  There is
no random source, event lottery, particle identity, or observer feedback.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass

from .spec import DIRECTIONS, DeterministicWorldSpec, ParticleSpec

VELOCITY = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE_COLLISION = {
    frozenset(("N", "S")): ("E", "W"),
    frozenset(("E", "W")): ("N", "S"),
}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DeterministicWorldState:
    tick: int
    particles: tuple[ParticleSpec, ...]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a non-negative integer")
        ordered = tuple(sorted(self.particles))
        if len(set(ordered)) != len(ordered):
            raise ValueError("duplicate directional particle channel")
        object.__setattr__(self, "particles", ordered)

    @property
    def particle_count(self) -> int:
        return len(self.particles)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"particles": [item.canonical() for item in self.particles], "tick": self.tick}

    def material_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for particle in self.particles:
            counts[particle.kind] = counts.get(particle.kind, 0) + 1
        return dict(sorted(counts.items()))

    def momentum(self, spec: DeterministicWorldSpec) -> tuple[int, int]:
        masses = {item.kind: item.mass for item in spec.materials}
        x = y = 0
        for particle in self.particles:
            dx, dy = VELOCITY[particle.direction]
            x += masses[particle.kind] * dx
            y += masses[particle.kind] * dy
        return x, y


@dataclass(frozen=True)
class TickRecord:
    tick: int
    state_digest: str
    particle_count: int
    material_counts: tuple[tuple[int, int], ...]
    momentum: tuple[int, int]

    def canonical(self) -> dict[str, object]:
        return {
            "material_counts": {str(kind): amount for kind, amount in self.material_counts},
            "momentum": list(self.momentum),
            "particle_count": self.particle_count,
            "state_digest": self.state_digest,
            "tick": self.tick,
        }


@dataclass(frozen=True)
class DeterministicRun:
    spec_digest: str
    initial_state: DeterministicWorldState
    final_state: DeterministicWorldState
    checkpoints: tuple[TickRecord, ...]

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "checkpoints": [item.canonical() for item in self.checkpoints],
            "final_state": self.final_state.canonical(),
            "format": "deterministic-world-run-v1",
            "initial_state": self.initial_state.canonical(),
            "spec_digest": self.spec_digest,
        }


def initial_state(spec: DeterministicWorldSpec) -> DeterministicWorldState:
    return DeterministicWorldState(0, spec.initial_particles)


def stream(spec: DeterministicWorldSpec, state: DeterministicWorldState) -> DeterministicWorldState:
    moved = []
    for particle in state.particles:
        dx, dy = VELOCITY[particle.direction]
        moved.append(ParticleSpec(
            particle.kind,
            (particle.x + dx) % spec.kernel.width,
            (particle.y + dy) % spec.kernel.height,
            particle.direction,
        ))
    return DeterministicWorldState(state.tick, tuple(moved))


def collide(state: DeterministicWorldState) -> DeterministicWorldState:
    grouped: dict[tuple[int, int, int], set[str]] = defaultdict(set)
    for particle in state.particles:
        grouped[(particle.x, particle.y, particle.kind)].add(particle.direction)
    particles = []
    for (x, y, kind), directions in sorted(grouped.items()):
        replacement = OPPOSITE_COLLISION.get(frozenset(directions)) if len(directions) == 2 else None
        for direction in replacement or tuple(sorted(directions, key=DIRECTIONS.index)):
            particles.append(ParticleSpec(kind, x, y, direction))
    return DeterministicWorldState(state.tick, tuple(particles))


def step_world(spec: DeterministicWorldSpec, state: DeterministicWorldState) -> DeterministicWorldState:
    before_counts = state.material_counts()
    before_momentum = state.momentum(spec)
    next_state = collide(stream(spec, state))
    next_state = DeterministicWorldState(state.tick + 1, next_state.particles)
    if next_state.material_counts() != before_counts:
        raise AssertionError("deterministic tick changed material counts")
    if next_state.momentum(spec) != before_momentum:
        raise AssertionError("deterministic tick changed momentum")
    return next_state


def _record(spec: DeterministicWorldSpec, state: DeterministicWorldState) -> TickRecord:
    return TickRecord(
        state.tick,
        state.digest,
        state.particle_count,
        tuple(state.material_counts().items()),
        state.momentum(spec),
    )


def run_world(spec: DeterministicWorldSpec) -> DeterministicRun:
    state = initial_state(spec)
    initial = state
    checkpoints = [_record(spec, state)]
    interval = spec.observer.hash_interval
    for _ in range(spec.execution.ticks):
        state = step_world(spec, state)
        if state.tick % interval == 0 or state.tick == spec.execution.ticks:
            checkpoints.append(_record(spec, state))
    return DeterministicRun(spec.digest, initial, state, tuple(checkpoints))
