"""G6c-1: the smallest possible A-compatible world -- a fixed set of named
boolean variables and a hidden, opaque one-tick rule.

This is not `ground_truth/`'s `world2_direct.py`/`world3_conditional.py`/
`gt_m1_mediator.py`. Nothing here imports from `ground_truth/`, and nothing
in `ground_truth/` imports this module -- see `engine/deterministic/__init__.py`'s
docstring and `tests/test_deterministic_synthetic_spec.py`'s leakage check.
Both independently implement whatever boolean relation a world is meant to
have; a shared `step()` function would mean the "world B researches" and
the "answer key B is graded against" are the same code, which defeats the
entire point of `ground_truth/` (see CURRENT_STATE.md's "hidden mediator"
circularity this project exists to avoid).

Variable and world names here are deliberately anonymous -- `x1`/`x2`/`x3`,
`WORLD-S01`, never `source_active`/`mediator_active`/`gate_enabled` or
`direct`/`conditional`/`mediator`. A name is not evidence; B has to find
the causal structure by intervening on the world, not by reading the
identifiers.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

FORMAT = "synthetic-research-world-v1"

CONTROL_MODES = frozenset({"FREE", "OFF", "ON"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be a boolean")
    return value


@dataclass(frozen=True, order=True)
class SyntheticClamp:
    """An intervention pinning one variable to a fixed value for the whole run.

    `mode="FREE"` means the variable is left to whatever the world's own
    (opaque, hidden) rule would set it to -- a clamp entry with `FREE` is
    equivalent to no clamp at all, but every declared variable gets one
    explicitly so a spec's `canonical()` form is unambiguous about which
    variables exist versus which are actually pinned.
    """
    variable_id: str
    mode: str

    def __post_init__(self) -> None:
        _text(self.variable_id, "variable_id")
        if self.mode not in CONTROL_MODES:
            raise ValueError(f"unsupported clamp mode {self.mode!r}")

    def canonical(self) -> dict[str, object]:
        return {"mode": self.mode, "variable_id": self.variable_id}


@dataclass(frozen=True)
class SyntheticWorldSpec:
    """An A-compatible world: named boolean variables, an initial value for
    each, optional clamps, and which variables/ticks B may control/observe.

    `world_revision` is an opaque identifier with no meaning to B -- it
    exists so a `(world_id, world_revision)` pair uniquely pins which
    hidden rule actually governs this world (see `synthetic_runtime.py`),
    without the spec itself naming or hinting at that rule the way an
    earlier draft's `rule_id` field did (`RULE-S01` etc.). If the hidden
    rule bound to a world ever changes, its `world_revision` must change
    too, so `digest` cannot claim two different rules are "the same
    world" -- exactly the reproducibility guarantee this field exists to
    protect. Never spell out what a revision represents (no `REV-DIRECT`);
    a short opaque token (`R-7F93C2`) is the right shape.
    """
    world_id: str
    world_revision: str
    variables: tuple[str, ...]
    initial_values: tuple[tuple[str, bool], ...]
    clamps: tuple[SyntheticClamp, ...]
    public_controls: tuple[str, ...]
    public_observables: tuple[str, ...]
    ticks: int
    format: str = FORMAT

    def __post_init__(self) -> None:
        _text(self.world_id, "world_id")
        _text(self.world_revision, "world_revision")
        if not self.variables:
            raise ValueError("variables must be non-empty")
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("variable ids must be unique")
        for name in self.variables:
            _text(name, "variable id")

        initial_names = [name for name, _ in self.initial_values]
        if set(initial_names) != set(self.variables) or len(initial_names) != len(self.variables):
            raise ValueError("initial_values must give exactly one value per declared variable")
        for name, value in self.initial_values:
            _bool(value, f"initial value for {name!r}")

        clamp_names = [clamp.variable_id for clamp in self.clamps]
        if len(set(clamp_names)) != len(clamp_names):
            raise ValueError("clamps must name each variable at most once")
        if not set(clamp_names) <= set(self.public_controls):
            raise ValueError("only a public control may be clamped")

        if not set(self.public_controls) <= set(self.variables):
            raise ValueError("public_controls must be a subset of variables")
        if not set(self.public_observables) <= set(self.variables):
            raise ValueError("public_observables must be a subset of variables")
        if len(set(self.public_controls)) != len(self.public_controls):
            raise ValueError("public_controls must not repeat")
        if len(set(self.public_observables)) != len(self.public_observables):
            raise ValueError("public_observables must not repeat")

        if isinstance(self.ticks, bool) or not isinstance(self.ticks, int) or self.ticks < 1:
            raise ValueError("ticks must be a positive integer")
        if self.format != FORMAT:
            raise ValueError("unsupported synthetic world format")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "clamps": [c.canonical() for c in sorted(self.clamps)],
            "format": self.format,
            "initial_values": [[name, value] for name, value in sorted(self.initial_values)],
            "public_controls": sorted(self.public_controls),
            "public_observables": sorted(self.public_observables),
            "ticks": self.ticks,
            "variables": sorted(self.variables),
            "world_id": self.world_id,
            "world_revision": self.world_revision,
        }

    def clamp_for(self, variable_id: str) -> str:
        for clamp in self.clamps:
            if clamp.variable_id == variable_id:
                return clamp.mode
        return "FREE"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "SyntheticWorldSpec":
        if not isinstance(raw, Mapping):
            raise ValueError("synthetic world spec must be an object")
        allowed_keys = {"format", "world_id", "world_revision", "variables", "initial_values",
                        "clamps", "public_controls", "public_observables", "ticks"}
        unknown = set(raw) - allowed_keys
        if unknown:
            raise ValueError(f"unknown synthetic world spec fields: {sorted(unknown)}")

        variables = raw.get("variables")
        if not isinstance(variables, list) or not all(isinstance(v, str) for v in variables):
            raise ValueError("variables must be a list of strings")

        initial_raw = raw.get("initial_values")
        if isinstance(initial_raw, Mapping):
            initial_values = tuple(sorted((str(k), v) for k, v in initial_raw.items()))
        elif isinstance(initial_raw, list):
            initial_values = tuple(sorted((str(k), v) for k, v in initial_raw))
        else:
            raise ValueError("initial_values must be an object or a list of [name, value] pairs")

        clamps_raw = raw.get("clamps", {})
        if isinstance(clamps_raw, Mapping):
            clamps = tuple(sorted(SyntheticClamp(str(k), v) for k, v in clamps_raw.items()))
        elif isinstance(clamps_raw, list):
            clamps = tuple(sorted(SyntheticClamp(str(item["variable_id"]), str(item["mode"]))
                                  for item in clamps_raw))
        else:
            raise ValueError("clamps must be an object or a list of clamp entries")

        controls = raw.get("public_controls")
        observables = raw.get("public_observables")
        if not isinstance(controls, list) or not all(isinstance(v, str) for v in controls):
            raise ValueError("public_controls must be a list of strings")
        if not isinstance(observables, list) or not all(isinstance(v, str) for v in observables):
            raise ValueError("public_observables must be a list of strings")

        execution = raw.get("ticks")
        if isinstance(execution, Mapping):
            ticks = execution.get("ticks")
        else:
            ticks = execution

        return cls(
            world_id=str(raw.get("world_id")), world_revision=str(raw.get("world_revision")),
            variables=tuple(variables), initial_values=initial_values, clamps=clamps,
            public_controls=tuple(controls), public_observables=tuple(observables),
            ticks=ticks, format=str(raw.get("format", FORMAT)),
        )


@dataclass(frozen=True)
class SyntheticCheckpoint:
    """One tick's worth of every variable's value, after clamps for that tick were applied."""
    tick: int
    values: tuple[tuple[str, bool], ...]

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        names = [name for name, _ in self.values]
        if len(set(names)) != len(names):
            raise ValueError("checkpoint values must not repeat a variable")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"tick": self.tick, "values": [[name, value] for name, value in sorted(self.values)]}

    def value_of(self, variable_id: str) -> bool | None:
        for name, value in self.values:
            if name == variable_id:
                return value
        return None


@dataclass(frozen=True)
class SyntheticRun:
    """The full record of one `SyntheticWorldSpec` execution: one checkpoint per tick, tick 0 included."""
    world_id: str
    spec_digest: str
    checkpoints: tuple[SyntheticCheckpoint, ...]

    def __post_init__(self) -> None:
        _text(self.world_id, "world_id")
        _text(self.spec_digest, "spec_digest")
        if not self.checkpoints:
            raise ValueError("a run must have at least one checkpoint")
        ticks = [c.tick for c in self.checkpoints]
        if ticks != sorted(ticks) or len(set(ticks)) != len(ticks):
            raise ValueError("checkpoints must be strictly increasing by tick")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"checkpoints": [c.canonical() for c in self.checkpoints], "format": FORMAT,
                "spec_digest": self.spec_digest, "world_id": self.world_id}

    def checkpoint_at(self, tick: int) -> SyntheticCheckpoint | None:
        for checkpoint in self.checkpoints:
            if checkpoint.tick == tick:
                return checkpoint
        return None
