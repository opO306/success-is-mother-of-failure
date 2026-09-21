"""Deterministic CPU scaling and resolution audit for A2 environments.

Local-size invariance is a hard check. Resolution convergence is deliberately
not certified until a physical mapping for cell width and tick duration exists.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .environment_kernel import EnvironmentState, run_environment_world
from .environment_spec import EnvironmentWorldSpec


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _base_mapping(size: int, ticks: int, world_id: str) -> dict[str, object]:
    if isinstance(size, bool) or not isinstance(size, int) or size < 16 or size % 2:
        raise ValueError("scaling grids must have an even size of at least 16")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 0:
        raise ValueError("ticks must be a nonnegative integer")
    return {
        "format": "deterministic-environment-world-spec-v2",
        "causal_world": {
            "format": "deterministic-causal-world-spec-v1", "world_id": world_id,
            "kernel": {"width": size, "height": size, "boundary": "wrap", "arithmetic": "integer",
                       "deterministic": True,
                       "tick_order": ["break_existing_bonds", "stream_free_particles", "resolve_local_collisions"]},
            "materials": [{"kind": 0, "mass": 1, "ports": 4}], "particles": [], "heat": [],
            "bond_rules": [], "execution": {"ticks": ticks}, "observer": {"hash_interval": max(1, ticks)},
        },
        "solute_kinds": 2, "cells": [], "blocked_edges": [],
        "law": {
            "max_heat_transfer": 1, "max_water_transfer": 1, "max_solute_transfer": 1,
            "phase_order": ["horizontal_even", "horizontal_odd", "vertical_even", "vertical_odd"],
            "max_carried_solute_per_water": 1, "mineral_solute_kind": 0,
            "dissolve_heat_at_least": 3, "precipitate_heat_at_most": 1,
            "hot_solubility_per_water": 2, "cold_solubility_per_water": 1,
            "max_mineral_conversion": 0, "mineral_conversion_energy": 1,
        },
    }


def make_locality_probe_spec(size: int, ticks: int = 6) -> EnvironmentWorldSpec:
    raw = _base_mapping(size, ticks, f"locality-probe-{size}")
    x = y = 16
    raw["causal_world"]["heat"] = [{"x": x, "y": y, "energy": 32}]
    raw["cells"] = [
        {"x": x, "y": y, "elevation": 2, "water": 16, "mineral": 4, "solutes": [8, 4]},
        {"x": x + 1, "y": y, "elevation": 0, "water": 4, "mineral": 0, "solutes": [0, 0]},
    ]
    return EnvironmentWorldSpec.from_mapping(raw)


def make_resolution_probe_spec(size: int, ticks: int) -> EnvironmentWorldSpec:
    raw = _base_mapping(size, ticks, f"resolution-probe-{size}-{ticks}")
    raw["law"]["max_water_transfer"] = 0
    raw["law"]["max_solute_transfer"] = 0
    raw["law"]["max_carried_solute_per_water"] = 0
    raw["law"]["max_heat_transfer"] = 2
    side = size // 4
    start = size // 2 - side // 2
    raw["causal_world"]["heat"] = [
        {"x": x, "y": y, "energy": 16}
        for y in range(start, start + side) for x in range(start, start + side)
    ]
    return EnvironmentWorldSpec.from_mapping(raw)


def _local_signature(state: EnvironmentState, origin: tuple[int, int], radius: int) -> str:
    ox, oy = origin
    heat = {(x.x, x.y): x.energy for x in state.causal.heat}
    cells = {(x.x, x.y): x for x in state.cells}
    payload = []
    for y in range(oy - radius, oy + radius + 1):
        for x in range(ox - radius, ox + radius + 1):
            cell = cells.get((x, y))
            energy = heat.get((x, y), 0)
            if cell is not None or energy:
                payload.append({"dx": x - ox, "dy": y - oy, "heat": energy,
                                "cell": cell.canonical() if cell is not None else None})
    return _digest(payload)


def _normalized_heat_moment(state: EnvironmentState, size: int) -> Fraction:
    center = size // 2
    total = 0
    weighted = 0
    for cell in state.causal.heat:
        dx = min((cell.x - center) % size, (center - cell.x) % size)
        dy = min((cell.y - center) % size, (center - cell.y) % size)
        total += cell.energy
        weighted += cell.energy * (dx * dx + dy * dy)
    return Fraction(weighted, total * size * size) if total else Fraction(0, 1)


def _fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


@dataclass(frozen=True)
class ResolutionObservation:
    grid_size: int
    ticks: int
    normalized_heat_second_moment: Fraction
    final_state_digest: str

    def canonical(self) -> dict[str, object]:
        return {"final_state_digest": self.final_state_digest, "grid_size": self.grid_size,
                "normalized_heat_second_moment": _fraction(self.normalized_heat_second_moment), "ticks": self.ticks}


@dataclass(frozen=True)
class TickScalingAudit:
    mapping: str
    observations: tuple[ResolutionObservation, ...]
    successive_differences: tuple[Fraction, ...]
    differences_decrease: bool

    def canonical(self) -> dict[str, object]:
        return {"differences_decrease": self.differences_decrease, "mapping": self.mapping,
                "observations": [x.canonical() for x in self.observations],
                "successive_differences": [_fraction(x) for x in self.successive_differences]}


@dataclass(frozen=True)
class ScalingAudit:
    locality_sizes: tuple[int, ...]
    locality_signatures: tuple[str, ...]
    locality_equivalent: bool
    tick_scaling_audits: tuple[TickScalingAudit, ...]
    convergence_status: str
    convergence_reason: str

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"convergence_reason": self.convergence_reason, "convergence_status": self.convergence_status,
                "format": "deterministic-scaling-audit-v1", "locality_equivalent": self.locality_equivalent,
                "locality_signatures": list(self.locality_signatures), "locality_sizes": list(self.locality_sizes),
                "tick_scaling_audits": [x.canonical() for x in self.tick_scaling_audits]}


def _tick_audit(mapping: str, schedule: tuple[tuple[int, int], ...]) -> TickScalingAudit:
    observations = []
    for size, ticks in schedule:
        run = run_environment_world(make_resolution_probe_spec(size, ticks))
        observations.append(ResolutionObservation(size, ticks,
                            _normalized_heat_moment(run.final_state, size), run.final_state.digest))
    differences = tuple(abs(observations[index + 1].normalized_heat_second_moment -
                            observations[index].normalized_heat_second_moment)
                        for index in range(len(observations) - 1))
    decreasing = bool(differences) and all(b <= a for a, b in zip(differences, differences[1:]))
    return TickScalingAudit(mapping, tuple(observations), differences, decreasing)


def run_scaling_audit() -> ScalingAudit:
    locality_sizes = (32, 64, 128)
    signatures = tuple(_local_signature(run_environment_world(make_locality_probe_spec(size)).final_state,
                                        (16, 16), 10) for size in locality_sizes)
    audits = (
        _tick_audit("ticks_proportional_to_grid_width", ((16, 4), (32, 8), (64, 16))),
        _tick_audit("ticks_proportional_to_grid_width_squared", ((16, 1), (32, 4), (64, 16))),
    )
    return ScalingAudit(
        locality_sizes, signatures, len(set(signatures)) == 1, audits, "not-established",
        "Cell width and tick duration have no declared physical-unit mapping; normalized trends are diagnostics, not proof.",
    )


def benchmark_environment_sizes(sizes: Iterable[int] = (64, 128, 256), ticks: int = 4) -> tuple[dict[str, object], ...]:
    results = []
    for size in sizes:
        spec = make_locality_probe_spec(size, ticks)
        started = time.perf_counter()
        run = run_environment_world(spec)
        elapsed = time.perf_counter() - started
        results.append({"grid_size": size, "ticks": ticks, "elapsed_seconds": elapsed,
                        "cell_ticks_per_second": (size * size * ticks / elapsed) if elapsed else None,
                        "final_state_digest": run.final_state.digest,
                        "conserved_resources": run.final_state.conserved_resources(spec),
                        "total_energy": run.final_state.total_energy(spec)})
    return tuple(results)
