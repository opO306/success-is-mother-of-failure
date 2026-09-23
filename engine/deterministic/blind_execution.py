"""G7.3a: the B-facing half of the blind execution boundary.

G7.1 sealed B's *object graph* (no `BlindWorldDescriptor`/`BlindControlDescriptor`/
`BlindObservableDescriptor` can carry real identity) and G7.2 sealed the
*order* predictions and results are journaled in. Neither, on its own, stops
a caller from handing G6d's `rank_discriminating_candidates` a real
`SyntheticWorldSpec` as `compiled_specs[candidate_id]` -- `ResearchWorldSpec`
is a structural Protocol (`world_id`/`digest`/`canonical()`), so a real spec
satisfies it exactly as well as a blind one does, and nothing before this
Gate stopped that substitution. This module is the type G6d (and any other
B-facing consumer of a `ResearchWorldSpec`) is meant to receive instead.

`BlindCandidateSpec` satisfies `ResearchWorldSpec` structurally
(`world_id`/`digest`/`canonical()`) using only alias data -- `world_id`
*is* `alias_world_id`; there is no real spec anywhere in its object graph
for a careless read to reach. `BlindRun` is the parallel type for
`ResearchRun`: `ExecutionResult.canonical()` (`causal_executor.py`) exposes
`executed_spec_digest` and `run_digest`, and both are real
`SyntheticWorldSpec`/`SyntheticRun` digests when a real executor runs a
real spec -- if that `ExecutionResult` reached B's journal unchanged, G7.1's
wall would have a B-shaped hole in it despite every direct import check
passing. `BlindCheckpoint`/`BlindRun` exist so an `ExecutionResult` handed
to B can carry only alias-derived digests and alias observable ids.

This module is B/protocol-side, exactly like `blind_session.py` and
`blind_protocol.py`: it must never import `blind_evaluator`,
`blind_synthetic_executor`, `ground_truth`, or `synthetic_runtime` -- see
`tests/test_deterministic_blind_execution.py`'s dependency-boundary tests.
It knows about `BlindWorldDescriptor`/`BlindControlDescriptor`/
`BlindObservableDescriptor` (`blind_session.py`), `ExecutionResult`/
`AExecutor` (`causal_executor.py` -- the executor Protocol itself is
world-agnostic and carries no real identity), and `ResearchWorldSpec`/
`ResearchRun` (`research_world.py`). Nothing about real world identity.

Translating a real `ExecutionResult` into a blind-safe one is evaluator
work and lives in `blind_synthetic_executor.py`, not here -- this module
only defines the B-facing shapes; it does not know how to produce one from
a real run.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "blind-execution-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True)
class BlindCandidateSpec:
    """A `ResearchWorldSpec` built from alias data only -- no real
    `SyntheticWorldSpec` is reachable from this object's fields.

    `world_id` *is* the alias world id (see `world_id`'s own value, never a
    separately-named `alias_world_id` field that might tempt a caller into
    thinking the "real" id lives elsewhere on this type -- it does not
    exist here at all). `digest` and `canonical()` are computed purely from
    this object's own alias-only fields, so a `BlindCandidateSpec`'s digest
    can never accidentally equal or encode a real spec's digest.
    """
    world_id: str
    candidate_id: str
    control_values: tuple[tuple[str, object], ...]
    ticks: int
    format: str = FORMAT
    # G9: (tick, alias control id, 1|0) -- press or release a control at one
    # tick. Empty for every pre-G9 candidate, whose digest is unchanged.
    schedule: tuple[tuple[int, str, int], ...] = ()

    def __post_init__(self) -> None:
        _text(self.world_id, "world_id")
        _text(self.candidate_id, "candidate_id")
        keys = []
        for entry in self.schedule:
            if not isinstance(entry, tuple) or len(entry) != 3:
                raise ValueError("schedule entries are (tick, control, value)")
            tick, control, value = entry
            if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0 or tick > self.ticks:
                raise ValueError("scheduled tick must fall within the run")
            _text(control, "scheduled control")
            if value not in (0, 1) or isinstance(value, bool):
                raise ValueError("scheduled value must be 0 or 1")
            keys.append((tick, control))
        if len(set(keys)) != len(keys):
            raise ValueError("schedule names each (tick, control) at most once")
        if not isinstance(self.control_values, tuple):
            raise ValueError("control_values must be a tuple")
        names = [name for name, _ in self.control_values]
        if len(set(names)) != len(names):
            raise ValueError("control_values must not repeat a control id")
        for name in names:
            _text(name, "control_values entry")
        if isinstance(self.ticks, bool) or not isinstance(self.ticks, int) or self.ticks < 1:
            raise ValueError("ticks must be a positive integer")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {
            "candidate_id": self.candidate_id,
            "control_values": [[name, value] for name, value in sorted(self.control_values)],
            "format": self.format,
            "ticks": self.ticks,
            "world_id": self.world_id,
        }
        if self.schedule:
            result["schedule"] = [list(entry) for entry in sorted(self.schedule)]
        return result


@dataclass(frozen=True)
class BlindCheckpoint:
    """One tick's alias-observable values -- the blind counterpart to
    `synthetic_spec.SyntheticCheckpoint`, holding alias observable ids in
    place of real variable names."""
    tick: int
    observables: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        names = [name for name, _ in self.observables]
        if len(set(names)) != len(names):
            raise ValueError("observables must not repeat an alias observable id")

    def canonical(self) -> dict[str, object]:
        return {"observables": [[name, value] for name, value in sorted(self.observables)], "tick": self.tick}

    def value_of(self, alias_observable_id: str) -> object | None:
        for name, value in self.observables:
            if name == alias_observable_id:
                return value
        return None


@dataclass(frozen=True)
class BlindRun:
    """A `ResearchRun` built from alias data only -- the blind counterpart
    to `synthetic_spec.SyntheticRun`. `digest` is computed from this
    object's own checkpoints, never copied from a real `SyntheticRun.digest`
    (which would fold in real observable names via `SyntheticCheckpoint`)."""
    alias_world_id: str
    checkpoints: tuple[BlindCheckpoint, ...]
    format: str = FORMAT

    def __post_init__(self) -> None:
        _text(self.alias_world_id, "alias_world_id")
        if not self.checkpoints:
            raise ValueError("a run must have at least one checkpoint")
        ticks = [c.tick for c in self.checkpoints]
        if ticks != sorted(ticks) or len(set(ticks)) != len(ticks):
            raise ValueError("checkpoints must be strictly increasing by tick")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"alias_world_id": self.alias_world_id, "checkpoints": [c.canonical() for c in self.checkpoints],
                "format": self.format}

    def checkpoint_at(self, tick: int) -> BlindCheckpoint | None:
        for checkpoint in self.checkpoints:
            if checkpoint.tick == tick:
                return checkpoint
        return None
