"""G10: B's side of the physical probe -- intents, programs, observations,
predictions. Alias-only.

B sees the probe through neutral symbols: actions are `ACT-xxxxxxxx`,
directions `DIR-xxxxxxxx`, observable channels `CH-xxxxxxxx`, all permuted
per session seed. B is told only each action's *arity* (whether it takes a
direction) -- not what it does, which direction is which, or what a channel
measures. It learns those from what happens. Grid geometry (cell
coordinates, width, height) is public: it is the space B acts in, not an
answer.

A program is a fixed sequence of intents decided before it runs (the
"recipe" mode approved for G10; step-by-step control comes later). Its id is
derived from its content, so a program cannot be changed after its
predictions are sealed without its id -- and hence its seal -- changing too.

This module never imports the probe's physics (`probe_world`), the
environment kernel, or the evaluator-side translator: B can only *describe*
what it wants done. Checked transitively by tests.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FORMAT = "blind-probe-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BlindProbeDescriptor:
    """Everything B is told about a probe world before acting in it."""
    alias_world_id: str
    width: int
    height: int
    max_program_length: int
    actions: tuple[tuple[str, bool], ...]      # (action symbol, takes a direction)
    directions: tuple[str, ...]
    channels: tuple[str, ...]
    format: str = FORMAT
    # G11 (designer decision): the coordinate contract publishes that the grid
    # wraps -- B's measuring tape, not a law to discover.
    wraps: bool = True

    def canonical(self) -> dict[str, object]:
        return {"actions": [list(a) for a in sorted(self.actions)], "alias_world_id": self.alias_world_id,
                "channels": sorted(self.channels), "directions": sorted(self.directions), "format": self.format,
                "height": self.height, "max_program_length": self.max_program_length, "width": self.width,
                "wraps": self.wraps}


@dataclass(frozen=True)
class BlindProbeProgram:
    """A recipe: intents in order, one per tick. Satisfies `ResearchWorldSpec`
    (world_id / digest / canonical)."""
    world_id: str
    steps: tuple[tuple[str, str | None], ...]
    format: str = FORMAT

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("a program needs at least one step")
        for action, direction in self.steps:
            if not isinstance(action, str) or not action:
                raise ValueError("each step names an action symbol")
            if direction is not None and (not isinstance(direction, str) or not direction):
                raise ValueError("a direction is a symbol or None")

    @property
    def ticks(self) -> int:
        return len(self.steps)

    @property
    def program_id(self) -> str:
        return "BPROG-" + _digest({"steps": [list(s) for s in self.steps], "world_id": self.world_id})[:16]

    @property
    def candidate_id(self) -> str:
        return self.program_id

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"format": self.format, "program_id": self.program_id,
                "steps": [list(s) for s in self.steps], "world_id": self.world_id}


@dataclass(frozen=True)
class BlindProbeCheckpoint:
    tick: int
    probe: tuple[int, int, int, int]                 # x, y, energy, holding
    cells: tuple[tuple[int, int, str, int], ...]      # x, y, channel symbol, value (nonzero only)

    def canonical(self) -> dict[str, object]:
        return {"cells": [list(c) for c in self.cells], "probe": list(self.probe), "tick": self.tick}

    def value(self, subject: str) -> int:
        """`probe.x` / `probe.y` / `probe.energy` / `probe.holding`, or
        `cell:X,Y:CH-...` -- 0 for a channel with nothing there."""
        if subject.startswith("probe."):
            index = ("probe.x", "probe.y", "probe.energy", "probe.holding").index(subject)
            return self.probe[index]
        _, coords, channel = subject.split(":")
        x, y = (int(v) for v in coords.split(","))
        return next((v for cx, cy, ch, v in self.cells if (cx, cy, ch) == (x, y, channel)), 0)


@dataclass(frozen=True)
class BlindProbeRun:
    alias_world_id: str
    checkpoints: tuple[BlindProbeCheckpoint, ...]
    format: str = FORMAT

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"alias_world_id": self.alias_world_id, "checkpoints": [c.canonical() for c in self.checkpoints],
                "format": self.format}

    def checkpoint_at(self, tick: int) -> BlindProbeCheckpoint | None:
        return next((c for c in self.checkpoints if c.tick == tick), None)


@dataclass(frozen=True)
class ProbePrediction:
    """What B expects one subject to read at one tick of a program's run."""
    tick: int
    subject: str
    value: int

    def canonical(self) -> dict[str, object]:
        return {"kind": "probe_value", "subject": self.subject, "tick": self.tick, "value": self.value}


def probe_prediction_holds(program: BlindProbeProgram, prediction: ProbePrediction, run: BlindProbeRun) -> bool:
    """Compare only within the program's own run -- refusing ticks the program
    never reached (the G7.3b-4 rule, applied to probe programs)."""
    if not 0 <= prediction.tick <= program.ticks:
        raise ValueError("prediction is about a tick this program does not reach")
    if run.checkpoints[-1].tick != program.ticks:
        raise ValueError("run did not end where the program ends")
    return run.checkpoint_at(prediction.tick).value(prediction.subject) == prediction.value


def control_program(program: BlindProbeProgram, build_length: int, wait_symbol: str) -> BlindProbeProgram:
    """The same program with its first `build_length` steps replaced by waiting
    -- same duration, same later actions, no building. Comparing the two runs
    is how B tests whether what it built is a *tool*: a structure that
    changes what happens afterwards, not merely one that exists."""
    if not 0 < build_length <= program.ticks:
        raise ValueError("build_length must cover part of the program")
    return BlindProbeProgram(program.world_id,
                             tuple((wait_symbol, None) for _ in range(build_length)) + program.steps[build_length:])


def structure_has_effect(with_structure: BlindProbeRun, without_structure: BlindProbeRun,
                         subjects: tuple[str, ...]) -> bool:
    """Whether the chosen measurements differ at the end of the two runs. B
    picks the subjects; the cells it built with are the obvious difference
    and prove nothing -- the question is whether *something else* changed."""
    a, b = with_structure.checkpoints[-1], without_structure.checkpoints[-1]
    return any(a.value(s) != b.value(s) for s in subjects)
