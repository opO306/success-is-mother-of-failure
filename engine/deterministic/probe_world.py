"""G10: a physical probe inside the environment world -- A's side.

Constitution art. 25: the outside researcher (B) never changes A directly.
Its only channel is a probe declared in the world spec, which obeys A's own
laws. This module *is* that probe's physics; nothing on B's side imports it
(checked by tests) -- B only sends intents through the evaluator-side
executor, and A decides what happens.

The probe has three pieces of state -- a cell, what it holds (nothing, or
one unit of solid matter), and energy -- and five primitive actions, none
of which carries a purpose:

    MOVE(d)      step to the neighbouring cell in direction d. Costs 1 energy,
                 which becomes heat in the cell arrived at (conserved).
    GRASP(d)     take 1 unit of solid matter from the neighbouring cell, if the
                 probe holds nothing and there is some. Water cannot be taken.
    RELEASE(d)   put the held unit down in the neighbouring cell.
    HEAT(d)      move 1 unit of the probe's energy into the neighbouring cell as heat.
    WAIT         nothing.

Each program step is one world tick: the action is applied, then the
environment steps. An action the world does not allow -- no energy left, a
wall in the way, nothing to take, hands already full -- simply leaves the
world unchanged. A never says why (art. 25); only a *malformed* intent (an
unknown action, a direction where none belongs) is rejected, with
`MalformedProbeAction`.

Directions are grid neighbours (N/E/S/W); the grid's boundary rule
(wrapping or not) applies to the probe exactly as it does to the fields.
Worlds with particles are refused: the particle kernel still has the known
"lower particle id wins" defect (tests/test_known_defects_causal_kernel.py),
and B must not be able to discover an id-ordering artifact as a law.

Conservation, checked every tick by tests: solid matter in cells plus held
is constant; environment energy (ledger-accounted) plus probe energy is
constant.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from .causal_spec import HeatCellSpec
from .environment_kernel import EnvironmentState, initial_environment_state, step_environment_world
from .environment_spec import EnvironmentCellSpec, EnvironmentWorldSpec

FORMAT = "deterministic-probe-world-v1"
PROBE_CAPACITY = 1

MOVE, GRASP, RELEASE, HEAT, WAIT = "MOVE", "GRASP", "RELEASE", "HEAT", "WAIT"
ACTIONS = {MOVE: True, GRASP: True, RELEASE: True, HEAT: True, WAIT: False}  # takes a direction?
DIRECTIONS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
CHANNELS = ("elevation", "water", "mineral", "vapor", "heat")


class MalformedProbeAction(ValueError):
    """An intent that is not a well-formed action -- not a physical failure."""


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProbeSpec:
    x: int
    y: int
    energy: int

    def __post_init__(self) -> None:
        for name in ("x", "y", "energy"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"probe {name} must be a nonnegative integer")

    def canonical(self) -> dict[str, int]:
        return {"energy": self.energy, "x": self.x, "y": self.y}


@dataclass(frozen=True)
class ProbeWorldSpec:
    world_id: str
    world_revision: str
    environment: EnvironmentWorldSpec
    probe: ProbeSpec
    public_channels: tuple[str, ...]
    max_program_length: int
    format: str = FORMAT

    def __post_init__(self) -> None:
        kernel = self.environment.causal_world.kernel
        if not (0 <= self.probe.x < kernel.width and 0 <= self.probe.y < kernel.height):
            raise ValueError("probe must start inside the grid")
        if self.environment.causal_world.particles:
            raise ValueError("probe worlds are particle-free (known particle-id defect)")
        if not set(self.public_channels) <= set(CHANNELS) or len(set(self.public_channels)) != len(self.public_channels):
            raise ValueError(f"public channels must be distinct names from {CHANNELS}")
        if isinstance(self.max_program_length, bool) or not isinstance(self.max_program_length, int) \
                or self.max_program_length < 1:
            raise ValueError("max_program_length must be a positive integer")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"environment": self.environment.canonical(), "format": self.format,
                "max_program_length": self.max_program_length, "probe": self.probe.canonical(),
                "public_channels": sorted(self.public_channels), "world_id": self.world_id,
                "world_revision": self.world_revision}


@dataclass(frozen=True)
class ProbeState:
    environment: EnvironmentState
    x: int
    y: int
    energy: int
    holding: int

    @property
    def tick(self) -> int:
        return self.environment.tick


def initial_probe_state(spec: ProbeWorldSpec) -> ProbeState:
    return ProbeState(initial_environment_state(spec.environment), spec.probe.x, spec.probe.y, spec.probe.energy, 0)


def _neighbour(spec: ProbeWorldSpec, x: int, y: int, direction: str) -> tuple[int, int] | None:
    kernel = spec.environment.causal_world.kernel
    dx, dy = DIRECTIONS[direction]
    nx, ny = x + dx, y + dy
    if kernel.boundary == "wrap":
        return nx % kernel.width, ny % kernel.height
    if 0 <= nx < kernel.width and 0 <= ny < kernel.height:
        return nx, ny
    return None


def _blocked(spec: ProbeWorldSpec, a: tuple[int, int], b: tuple[int, int]) -> bool:
    return any(frozenset((e.first, e.second)) == frozenset((a, b)) for e in spec.environment.blocked_edges)


def _cell(state: EnvironmentState, spec: ProbeWorldSpec, point: tuple[int, int]) -> EnvironmentCellSpec:
    for cell in state.cells:
        if (cell.x, cell.y) == point:
            return cell
    return EnvironmentCellSpec(point[0], point[1], 0, 0, 0, (0,) * spec.environment.solute_kinds, 0)


def _with_cell(state: EnvironmentState, cell: EnvironmentCellSpec) -> EnvironmentState:
    others = tuple(c for c in state.cells if (c.x, c.y) != (cell.x, cell.y))
    keep = cell.elevation or cell.water or cell.mineral or cell.vapor or any(cell.solutes)
    return replace(state, cells=others + ((cell,) if keep else ()))


def _add_heat(state: EnvironmentState, point: tuple[int, int], amount: int) -> EnvironmentState:
    heat = {(h.x, h.y): h.energy for h in state.causal.heat}
    heat[point] = heat.get(point, 0) + amount
    cells = tuple(HeatCellSpec(x, y, e) for (x, y), e in sorted(heat.items()) if e)
    return replace(state, causal=replace(state.causal, heat=cells))


def apply_action(spec: ProbeWorldSpec, state: ProbeState, action: str, direction: str | None) -> ProbeState:
    """A's validator and physics for one intent. Physically impossible ->
    the state is returned unchanged, with no reason attached."""
    if action not in ACTIONS:
        raise MalformedProbeAction("unknown action")
    if ACTIONS[action] != (direction is not None) or (direction is not None and direction not in DIRECTIONS):
        raise MalformedProbeAction("direction does not fit this action")
    if action == WAIT:
        return state
    here = (state.x, state.y)
    there = _neighbour(spec, state.x, state.y, direction)
    if there is None or _blocked(spec, here, there):
        return state
    env = state.environment
    if action == MOVE:
        if state.energy < 1:
            return state
        return replace(state, environment=_add_heat(env, there, 1), x=there[0], y=there[1], energy=state.energy - 1)
    if action == HEAT:
        if state.energy < 1:
            return state
        return replace(state, environment=_add_heat(env, there, 1), energy=state.energy - 1)
    target = _cell(env, spec, there)
    if action == GRASP:
        if state.holding >= PROBE_CAPACITY or target.mineral < 1:
            return state
        return replace(state, environment=_with_cell(env, replace(target, mineral=target.mineral - 1)),
                       holding=state.holding + 1)
    # RELEASE
    if state.holding < 1:
        return state
    return replace(state, environment=_with_cell(env, replace(target, mineral=target.mineral + 1)),
                   holding=state.holding - 1)


def step_probe_world(spec: ProbeWorldSpec, state: ProbeState, action: str, direction: str | None) -> ProbeState:
    acted = apply_action(spec, state, action, direction)
    return replace(acted, environment=step_environment_world(spec.environment, acted.environment))


@dataclass(frozen=True)
class ProbeCheckpoint:
    """Full internal state at one tick -- evaluator-side; B receives only a
    translated, channel-filtered, alias-only copy."""
    tick: int
    x: int
    y: int
    energy: int
    holding: int
    cells: tuple[tuple[int, int, str, int], ...]   # (x, y, channel, value), nonzero only


def _checkpoint(spec: ProbeWorldSpec, state: ProbeState) -> ProbeCheckpoint:
    heat = {(h.x, h.y): h.energy for h in state.environment.causal.heat}
    values = []
    points = sorted({(c.x, c.y) for c in state.environment.cells} | set(heat))
    for point in points:
        cell = _cell(state.environment, spec, point)
        channel_values = {"elevation": cell.elevation, "water": cell.water, "mineral": cell.mineral,
                          "vapor": cell.vapor, "heat": heat.get(point, 0)}
        values.extend((point[0], point[1], name, value) for name, value in channel_values.items() if value)
    return ProbeCheckpoint(state.tick, state.x, state.y, state.energy, state.holding, tuple(sorted(values)))


def run_probe_world(spec: ProbeWorldSpec, program: tuple[tuple[str, str | None], ...]
                    ) -> tuple[tuple[ProbeCheckpoint, ...], ProbeState]:
    """Checkpoints at tick 0 and after every step, plus the final state."""
    if len(program) > spec.max_program_length:
        raise MalformedProbeAction("program longer than the world allows")
    state = initial_probe_state(spec)
    checkpoints = [_checkpoint(spec, state)]
    for action, direction in program:
        state = step_probe_world(spec, state, action, direction)
        checkpoints.append(_checkpoint(spec, state))
    return tuple(checkpoints), state


def conserved_totals(spec: ProbeWorldSpec, state: ProbeState) -> dict[str, int]:
    """Solid matter (cells + held) and energy (environment ledger + probe)."""
    account = state.environment.energy_account(spec.environment)
    return {"solid": sum(c.mineral for c in state.environment.cells) + state.holding,
            "energy": account["accounted"] + state.energy}
