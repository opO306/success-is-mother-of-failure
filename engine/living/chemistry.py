"""Frozen material transformations available to every living lineage.

Processes have no names such as photosynthesis, digestion, growth, or healing.
The world fixes balanced transformations; genomes only carry catalysts that can
accelerate a process, and controllers request rates.  All requested processes are
scaled together when they compete for matter, so tuple order cannot pick a winner.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from .body import MatterPool, _vector
from .foundation import LivingState, _finite


@dataclass(frozen=True)
class ProcessLaw:
    consumes: tuple[float, ...]
    reserve_products: tuple[float, ...]
    structure_products: tuple[float, ...]
    environmental_products: tuple[float, ...]
    damage_delta: float = 0.0


@dataclass(frozen=True)
class Chemistry:
    material_weights: tuple[float, ...]
    processes: tuple[ProcessLaw, ...]

    def __post_init__(self) -> None:
        weights = tuple(_finite(value, "material weight") for value in self.material_weights)
        if not weights or any(value <= 0 for value in weights):
            raise ValueError("material weights must be positive")
        object.__setattr__(self, "material_weights", weights)
        clean_laws = []
        for law in self.processes:
            vectors = {
                name: _vector(getattr(law, name), len(weights), name)
                for name in ("consumes", "reserve_products", "structure_products", "environmental_products")
            }
            damage = _finite(law.damage_delta, "damage_delta")
            consumed = sum(value * weight for value, weight in zip(vectors["consumes"], weights))
            produced = sum(
                value * weight
                for name in ("reserve_products", "structure_products", "environmental_products")
                for value, weight in zip(vectors[name], weights)
            )
            if consumed <= 0:
                raise ValueError("a material process must consume something")
            if not math.isclose(consumed, produced, rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("material process is not balanced")
            clean_laws.append(ProcessLaw(**vectors, damage_delta=damage))
        object.__setattr__(self, "processes", tuple(clean_laws))

    def fingerprint(self) -> str:
        payload = {
            "material_weights": self.material_weights,
            "processes": [
                {
                    "consumes": law.consumes,
                    "reserve_products": law.reserve_products,
                    "structure_products": law.structure_products,
                    "environmental_products": law.environmental_products,
                    "damage_delta": law.damage_delta,
                }
                for law in self.processes
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProcessResult:
    extents: tuple[float, ...]
    common_scale: float
    reserve_delta: tuple[float, ...]
    structure_added: tuple[float, ...]
    released: tuple[float, ...]
    damage_delta: float


def _zero_result(width: int, catalysts: int) -> ProcessResult:
    zeros = (0.0,) * width
    return ProcessResult((0.0,) * catalysts, 0.0, zeros, zeros, zeros, 0.0)


def run_processes(
    state: LivingState,
    ambient: MatterPool,
    chemistry: Chemistry,
    requested_rates: tuple[float, ...],
) -> ProcessResult:
    """Run all catalysed transformations simultaneously and conserve weighted matter."""
    width = len(state.reserves)
    if len(chemistry.material_weights) != width or len(ambient.amounts) != width:
        raise ValueError("chemistry, environment and body must use the same material channels")
    requests = _vector(requested_rates, len(state.genome.catalysts), "process rates")
    if not requests:
        return _zero_result(width, 0)

    desired: list[float] = []
    laws: list[ProcessLaw] = []
    for request, catalyst in zip(requests, state.genome.catalysts):
        if catalyst.process >= len(chemistry.processes):
            raise ValueError(f"genome refers to missing material process: {catalyst.process}")
        desired.append(min(request, catalyst.max_rate))
        laws.append(chemistry.processes[catalyst.process])

    consumed = [0.0] * width
    reserve_products = [0.0] * width
    structure_products = [0.0] * width
    released = [0.0] * width
    damage = 0.0
    for extent, law in zip(desired, laws):
        for i in range(width):
            consumed[i] += extent * law.consumes[i]
            reserve_products[i] += extent * law.reserve_products[i]
            structure_products[i] += extent * law.structure_products[i]
            released[i] += extent * law.environmental_products[i]
        damage += extent * law.damage_delta

    scale = 1.0 if any(desired) else 0.0
    for available, needed in zip(state.reserves, consumed):
        if needed > 0:
            scale = min(scale, available / needed)

    current_capacity = state.boundary.capacities_for(state.structure)
    capacity_growth = [
        sum(gain * added for gain, added in zip(row, structure_products))
        for row in state.boundary.capacity_gain
    ]
    for amount, cap, used, made, cap_gain in zip(
        state.reserves, current_capacity, consumed, reserve_products, capacity_growth
    ):
        net_fill = made - used - cap_gain
        if net_fill > 0:
            scale = min(scale, max(0.0, cap - amount) / net_fill)

    extents = tuple(extent * scale for extent in desired)
    reserve_delta = tuple((made - used) * scale for made, used in zip(reserve_products, consumed))
    structure_added = tuple(value * scale for value in structure_products)
    actual_released = tuple(value * scale for value in released)
    for i in range(width):
        state.reserves[i] += reserve_delta[i]
        state.structure[i] += structure_added[i]
        ambient.amounts[i] += actual_released[i]
    before_damage = state.damage
    state.damage = max(0.0, state.damage + damage * scale)
    applied_damage = state.damage - before_damage
    return ProcessResult(extents, scale, reserve_delta, structure_added, actual_released, applied_damage)


def weighted_matter(state: LivingState, ambient: MatterPool, chemistry: Chemistry) -> float:
    """Conservation ledger across free body matter, bound structure and local environment."""
    return sum(
        weight * (reserve + bound + outside)
        for weight, reserve, bound, outside in zip(
            chemistry.material_weights, state.reserves, state.structure, ambient.amounts
        )
    )
