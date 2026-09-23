"""G10: evaluator side of the probe -- the only code that sees both B's
symbols and the real actions, directions and channels.

`make_probe_session(spec, seed)` returns the B-facing descriptor and, as a
separate value, the manifest that maps symbols back (G7.1 pattern).
`BlindProbeExecutor` is the `AExecutor` a harness hands B: it translates a
`BlindProbeProgram` into real intents, lets A (`probe_world`) decide what
happens, and translates the result back -- public channels only, every name
replaced by its symbol.

A malformed program (unknown symbol, a direction where none belongs, too
long) fails with a fixed message: the only rejection B ever sees. A
physically impossible step is *not* a failure -- it simply changed nothing.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .blind_probe import BlindProbeCheckpoint, BlindProbeDescriptor, BlindProbeProgram, BlindProbeRun
from .execution import ExecutionResult
from .probe_world import ACTIONS, DIRECTIONS, MalformedProbeAction, ProbeWorldSpec, run_probe_world
from .research_world import ResearchWorldSpec, WorldCompatibilityError

INVALID_ACTION = "InvalidAction"
_INVALID_MESSAGE = "malformed program (details withheld -- blind boundary)"


def _token(spec: ProbeWorldSpec, seed: int, kind: str, name: str, prefix: str) -> str:
    raw = f"{spec.digest}:{seed}:{kind}:{name}".encode("utf-8")
    return f"{prefix}-{hashlib.sha256(raw).hexdigest()[:8].upper()}"


@dataclass(frozen=True)
class ProbeManifest:
    alias_world_id: str
    action_symbol: Mapping[str, str]
    direction_symbol: Mapping[str, str]
    channel_symbol: Mapping[str, str]

    @property
    def action_of(self) -> Mapping[str, str]:
        return {v: k for k, v in self.action_symbol.items()}

    @property
    def direction_of(self) -> Mapping[str, str]:
        return {v: k for k, v in self.direction_symbol.items()}


def make_probe_session(spec: ProbeWorldSpec, seed: int) -> tuple[BlindProbeDescriptor, ProbeManifest]:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    manifest = ProbeManifest(
        alias_world_id=_token(spec, seed, "world", spec.world_id, "ALIAS"),
        action_symbol={a: _token(spec, seed, "action", a, "ACT") for a in ACTIONS},
        direction_symbol={d: _token(spec, seed, "direction", d, "DIR") for d in DIRECTIONS},
        channel_symbol={c: _token(spec, seed, "channel", c, "CH") for c in spec.public_channels},
    )
    kernel = spec.environment.causal_world.kernel
    descriptor = BlindProbeDescriptor(
        alias_world_id=manifest.alias_world_id, width=kernel.width, height=kernel.height,
        max_program_length=spec.max_program_length,
        actions=tuple(sorted((manifest.action_symbol[a], takes) for a, takes in ACTIONS.items())),
        directions=tuple(sorted(manifest.direction_symbol.values())),
        channels=tuple(sorted(manifest.channel_symbol.values())),
        wraps=kernel.boundary == "wrap",
    )
    return descriptor, manifest


@dataclass(frozen=True)
class BlindProbeExecutor:
    spec: ProbeWorldSpec
    manifest: ProbeManifest

    def execute(self, program: ResearchWorldSpec) -> ExecutionResult:
        if not isinstance(program, BlindProbeProgram):
            raise WorldCompatibilityError(f"BlindProbeExecutor runs BlindProbeProgram, got {type(program).__name__}")
        if program.world_id != self.manifest.alias_world_id:
            raise WorldCompatibilityError("program names a different world")
        action_of, direction_of = self.manifest.action_of, self.manifest.direction_of
        try:
            real_steps = tuple((action_of[a], None if d is None else direction_of[d]) for a, d in program.steps)
            checkpoints, _final = run_probe_world(self.spec, real_steps)
        except (KeyError, MalformedProbeAction):
            return ExecutionResult("failed", program.digest, None, INVALID_ACTION, _INVALID_MESSAGE)
        public = {name: symbol for name, symbol in self.manifest.channel_symbol.items()}
        blind = tuple(
            BlindProbeCheckpoint(c.tick, (c.x, c.y, c.energy, c.holding),
                                 tuple(sorted((x, y, public[ch], v) for x, y, ch, v in c.cells if ch in public)))
            for c in checkpoints)
        return ExecutionResult("success", program.digest, BlindProbeRun(self.manifest.alias_world_id, blind))

