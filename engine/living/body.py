"""Physical exchange and upkeep shared by every living body.

The functions here enforce consequences, not goals.  A controller may request
uptake, release, or displacement even when that choice harms the body.  The body
reports internal shortage separately and never converts it into a compulsory act.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .foundation import LivingState, _finite

if TYPE_CHECKING:
    from .chemistry import Chemistry, ProcessResult


def _vector(values: tuple[float, ...], width: int, name: str, *, signed: bool = False) -> tuple[float, ...]:
    result = tuple(_finite(value, name) for value in values)
    if len(result) != width:
        raise ValueError(f"{name} must have {width} material channels")
    if not signed and any(value < 0 for value in result):
        raise ValueError(f"{name} cannot contain negative values")
    return result


@dataclass
class MatterPool:
    """Material available at one physical location, with anonymous channels."""

    amounts: list[float]

    def __post_init__(self) -> None:
        values = [_finite(value, "ambient amount") for value in self.amounts]
        if any(value < 0 for value in values):
            raise ValueError("ambient matter cannot be negative")
        self.amounts = values

    def snapshot(self) -> tuple[float, ...]:
        return tuple(self.amounts)


@dataclass(frozen=True)
class BodyIntent:
    """A controller's request; positive exchange is inward, negative is outward."""

    exchange: tuple[float, ...]
    displacement: tuple[float, ...] = ()
    process_rates: tuple[float, ...] = ()


@dataclass(frozen=True)
class ExchangeResult:
    active_flux: tuple[float, ...]
    passive_outflow: tuple[float, ...]


@dataclass(frozen=True)
class MotionResult:
    requested_distance: float
    actual_distance: float
    spent: tuple[float, ...]


@dataclass(frozen=True)
class MaintenanceResult:
    spent: tuple[float, ...]
    shortfall: tuple[float, ...]
    damage_added: float


@dataclass(frozen=True)
class BodyTickResult:
    exchange: ExchangeResult
    processes: ProcessResult | None
    motion: MotionResult
    maintenance: MaintenanceResult


def internal_signals(state: LivingState) -> tuple[float, ...]:
    """Return graded shortage (-surplus) signals without choosing an action."""
    signals = []
    capacities = state.boundary.capacities_for(state.structure)
    for amount, target, capacity in zip(state.reserves, state.boundary.targets, capacities):
        scale = target if target > 0 else capacity
        signals.append((target - amount) / scale if scale > 0 else 0.0)
    damage_signal = state.damage / state.boundary.failure_damage
    return tuple(signals) + (damage_signal,)


def exchange(state: LivingState, ambient: MatterPool, request: tuple[float, ...]) -> ExchangeResult:
    """Apply requested and passive boundary flux while conserving every channel."""
    width = len(state.reserves)
    if len(ambient.amounts) != width:
        raise ValueError("ambient pool and body must use the same material channels")
    requested = _vector(request, width, "exchange request", signed=True)
    active: list[float] = []
    passive: list[float] = []
    boundary = state.boundary
    capacities = boundary.capacities_for(state.structure)

    for i, wanted in enumerate(requested):
        if wanted >= 0:
            moved = min(wanted, boundary.inward_limits[i], ambient.amounts[i], capacities[i] - state.reserves[i])
        else:
            moved = -min(-wanted, boundary.outward_limits[i], state.reserves[i])
        state.reserves[i] += moved
        ambient.amounts[i] -= moved
        active.append(moved)

        leaked = min(state.reserves[i], state.reserves[i] * boundary.passive_loss[i])
        state.reserves[i] -= leaked
        ambient.amounts[i] += leaked
        passive.append(leaked)

    return ExchangeResult(tuple(active), tuple(passive))


def move(state: LivingState, ambient: MatterPool, displacement: tuple[float, ...]) -> MotionResult:
    """Move as far as physical reach and available material permit."""
    requested = tuple(_finite(value, "displacement") for value in displacement)
    if len(requested) != len(state.position):
        raise ValueError("displacement and position must have the same dimensions")
    width = len(state.reserves)
    if len(ambient.amounts) != width:
        raise ValueError("ambient pool and body must use the same material channels")

    requested_distance = math.sqrt(sum(value * value for value in requested))
    if requested_distance == 0 or state.boundary.max_displacement == 0:
        return MotionResult(requested_distance, 0.0, (0.0,) * width)

    distance = min(requested_distance, state.boundary.max_displacement)
    for amount, unit_cost in zip(state.reserves, state.boundary.motion_cost):
        if unit_cost > 0:
            distance = min(distance, amount / unit_cost)
    scale = distance / requested_distance
    spent = tuple(unit_cost * distance for unit_cost in state.boundary.motion_cost)
    for i, cost in enumerate(spent):
        state.reserves[i] -= cost
        ambient.amounts[i] += cost
    for i, delta in enumerate(requested):
        state.position[i] += delta * scale
    return MotionResult(requested_distance, distance, spent)


def maintain(state: LivingState, ambient: MatterPool) -> MaintenanceResult:
    """Pay unavoidable upkeep after chosen acts; shortages cause damage, not rescue."""
    if len(ambient.amounts) != len(state.reserves):
        raise ValueError("ambient pool and body must use the same material channels")
    spent: list[float] = []
    shortfall: list[float] = []
    for i, required in enumerate(state.boundary.maintenance):
        paid = min(required, state.reserves[i])
        missing = required - paid
        state.reserves[i] -= paid
        ambient.amounts[i] += paid
        spent.append(paid)
        shortfall.append(missing)

    total_required = sum(state.boundary.maintenance)
    missing_share = sum(shortfall) / total_required if total_required else 0.0
    damage = missing_share * state.boundary.damage_from_total_shortfall
    state.damage += damage
    state.age_ticks += 1
    return MaintenanceResult(tuple(spent), tuple(shortfall), damage)


def body_tick(
    state: LivingState,
    ambient: MatterPool,
    intent: BodyIntent,
    chemistry: Chemistry | None = None,
) -> BodyTickResult:
    """One consequence tick: chosen exchange and motion, then unavoidable upkeep."""
    exchanged = exchange(state, ambient, intent.exchange)
    processed = None
    if intent.process_rates:
        if chemistry is None:
            raise ValueError("process rates require frozen chemistry")
        from .chemistry import run_processes

        processed = run_processes(state, ambient, chemistry, intent.process_rates)
    moved = move(state, ambient, intent.displacement)
    upkeep = maintain(state, ambient)
    return BodyTickResult(exchanged, processed, moved, upkeep)


def alive(state: LivingState) -> bool:
    """Death is a physical threshold; this predicate never revives or replaces a body."""
    return state.damage < state.boundary.failure_damage
