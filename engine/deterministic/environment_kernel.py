"""A2 deterministic CPU environment fields over the A1 causal world."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from .causal_kernel import CausalWorldState, initial_causal_state, step_causal_world
from .causal_spec import HeatCellSpec
from .environment_spec import EnvironmentCellSpec, EnvironmentWorldSpec, FORMAT_V2, FORMAT_V3, FORMAT_V4


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EnvironmentState:
    causal: CausalWorldState
    cells: tuple[EnvironmentCellSpec, ...]
    energy_supplied: int = 0
    energy_removed: int = 0
    format: str = "deterministic-environment-world-spec-v1"

    def __post_init__(self) -> None:
        cells = tuple(sorted(self.cells))
        if len({(x.x, x.y) for x in cells}) != len(cells): raise ValueError("environment cells must be unique")
        if self.energy_supplied < 0 or self.energy_removed < 0: raise ValueError("energy ledgers cannot be negative")
        object.__setattr__(self, "cells", cells)

    @property
    def tick(self) -> int: return self.causal.tick
    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {"causal": self.causal.canonical(),
                  "cells": [x.canonical(self.format in (FORMAT_V3, FORMAT_V4)) for x in self.cells]}
        if self.format in (FORMAT_V3, FORMAT_V4):
            result["energy_removed"] = self.energy_removed
            result["energy_supplied"] = self.energy_supplied
        return result

    def resource_totals(self, solute_kinds: int, include_vapor: bool = False) -> dict[str, object]:
        result = {"water": sum(x.water for x in self.cells), "mineral": sum(x.mineral for x in self.cells),
                  "solutes": [sum(x.solutes[k] for x in self.cells) for k in range(solute_kinds)]}
        if include_vapor:
            result["vapor"] = sum(x.vapor for x in self.cells)
        return result

    def conserved_resources(self, spec: EnvironmentWorldSpec) -> dict[str, object]:
        raw = self.resource_totals(spec.solute_kinds, spec.format in (FORMAT_V3, FORMAT_V4))
        if spec.format not in (FORMAT_V2, FORMAT_V3, FORMAT_V4):
            return raw
        inventory = list(raw["solutes"])
        inventory[spec.law.mineral_solute_kind] += raw["mineral"]
        water_total = raw["water"] + (raw.get("vapor", 0) if spec.format in (FORMAT_V3, FORMAT_V4) else 0)
        return {"water": water_total, "material_inventory": inventory}

    def total_energy(self, spec: EnvironmentWorldSpec) -> int:
        energy = self.causal.total_energy()
        if spec.format in (FORMAT_V2, FORMAT_V3, FORMAT_V4):
            dissolved = sum(x.solutes[spec.law.mineral_solute_kind] for x in self.cells)
            energy += dissolved * spec.law.mineral_conversion_energy
        if spec.format in (FORMAT_V3, FORMAT_V4):
            energy += sum(x.vapor for x in self.cells) * spec.law.vaporization_energy
        return energy

    def energy_account(self, spec: EnvironmentWorldSpec) -> dict[str, int]:
        internal = self.total_energy(spec)
        return {"internal": internal, "supplied": self.energy_supplied, "removed": self.energy_removed,
                "accounted": internal + self.energy_removed - self.energy_supplied}


@dataclass(frozen=True)
class EnvironmentTickRecord:
    tick: int
    state_digest: str
    total_energy: int
    resources: dict[str, object]
    conserved_resources: dict[str, object] | None = None
    energy_account: dict[str, int] | None = None

    def canonical(self) -> dict[str, object]:
        result = {"resources": self.resources, "state_digest": self.state_digest,
                  "tick": self.tick, "total_energy": self.total_energy}
        if self.conserved_resources is not None:
            result["conserved_resources"] = self.conserved_resources
        if self.energy_account is not None:
            result["energy_account"] = self.energy_account
        return result


@dataclass(frozen=True)
class EnvironmentRun:
    spec_digest: str
    initial_state: EnvironmentState
    final_state: EnvironmentState
    checkpoints: tuple[EnvironmentTickRecord, ...]

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"checkpoints": [x.canonical() for x in self.checkpoints], "final_state": self.final_state.canonical(),
                "format": "deterministic-environment-run-v1", "initial_state": self.initial_state.canonical(),
                "spec_digest": self.spec_digest}


def initial_environment_state(spec: EnvironmentWorldSpec) -> EnvironmentState:
    return EnvironmentState(initial_causal_state(spec.causal_world), spec.cells, format=spec.format)


def _edges(width: int, height: int, phase: str):
    if phase.startswith("horizontal"):
        parity = 0 if phase.endswith("even") else 1
        for y in range(height):
            for x in range(parity, width, 2): yield (x, y), ((x + 1) % width, y)
    else:
        parity = 0 if phase.endswith("even") else 1
        for x in range(width):
            for y in range(parity, height, 2): yield (x, y), (x, (y + 1) % height)


def _scalar_transfer(left: int, right: int, limit: int) -> int:
    difference = left - right
    if abs(difference) < 2 or limit == 0: return 0
    amount = min(limit, abs(difference) // 2)
    return amount if difference > 0 else -amount


def _field_transfer(spec: EnvironmentWorldSpec, left: int, right: int,
                    limit: int, channel: str) -> int:
    if spec.format != FORMAT_V4:
        return _scalar_transfer(left, right, limit)
    if spec.physical_scale is None:
        raise AssertionError("environment v4 lost its physical scale")
    return spec.physical_scale.transfer(left - right, channel, limit)


def _cell(values, point, solute_kinds):
    return values.get(point, EnvironmentCellSpec(point[0], point[1], 0, 0, 0, (0,) * solute_kinds))


def _phase(spec: EnvironmentWorldSpec, state: EnvironmentState, phase: str) -> EnvironmentState:
    width, height = spec.causal_world.kernel.width, spec.causal_world.kernel.height
    blocked = {frozenset((x.first, x.second)) for x in spec.blocked_edges}
    heat_before = {(x.x, x.y): x.energy for x in state.causal.heat}; heat_after = dict(heat_before)
    cells_before = {(x.x, x.y): x for x in state.cells}; cells_after = dict(cells_before)
    for first, second in _edges(width, height, phase):
        if frozenset((first, second)) in blocked: continue
        left, right = _cell(cells_before, first, spec.solute_kinds), _cell(cells_before, second, spec.solute_kinds)
        heat_move = _field_transfer(spec, heat_before.get(first, 0), heat_before.get(second, 0),
                                    spec.law.max_heat_transfer, "heat")
        if heat_move:
            heat_after[first] = heat_after.get(first, 0) - heat_move
            heat_after[second] = heat_after.get(second, 0) + heat_move
        surface_left, surface_right = left.elevation + left.water, right.elevation + right.water
        if spec.law.solids_occupy_space:  # G10: solid matter occupies space too
            surface_left, surface_right = surface_left + left.mineral, surface_right + right.mineral
        water_move = _field_transfer(spec, surface_left, surface_right,
                                     spec.law.max_water_transfer, "water_surface")
        if water_move > 0: water_move = min(water_move, left.water)
        elif water_move < 0: water_move = -min(-water_move, right.water)
        solute_moves = []
        water_left_after = left.water - water_move
        water_right_after = right.water + water_move
        for kind in range(spec.solute_kinds):
            carried = 0
            carrying_limit = abs(water_move) * spec.law.max_carried_solute_per_water
            if water_move > 0:
                proportional = (left.solutes[kind] * water_move // left.water) if spec.format == FORMAT_V4 else carrying_limit
                carried = min(carrying_limit, proportional, left.solutes[kind])
            elif water_move < 0:
                proportional = (right.solutes[kind] * -water_move // right.water) if spec.format == FORMAT_V4 else carrying_limit
                carried = -min(carrying_limit, proportional, right.solutes[kind])
            left_after_carry = left.solutes[kind] - carried
            right_after_carry = right.solutes[kind] + carried
            diffused = 0
            wet_for_diffusion = ((water_left_after and water_right_after)
                                 if spec.format in (FORMAT_V2, FORMAT_V3, FORMAT_V4)
                                 else (left.water and right.water))
            if wet_for_diffusion:
                diffused = _field_transfer(spec, left_after_carry, right_after_carry,
                                           spec.law.max_solute_transfer, "solute")
                if diffused > 0: diffused = min(diffused, left_after_carry)
                elif diffused < 0: diffused = -min(-diffused, right_after_carry)
            solute_moves.append(carried + diffused)
        left_solutes = tuple(left.solutes[k] - solute_moves[k] for k in range(spec.solute_kinds))
        right_solutes = tuple(right.solutes[k] + solute_moves[k] for k in range(spec.solute_kinds))
        vapor_limit = spec.law.max_vapor_transfer if spec.format in (FORMAT_V3, FORMAT_V4) else 0
        vapor_move = _field_transfer(spec, left.vapor, right.vapor, vapor_limit, "vapor")
        cells_after[first] = EnvironmentCellSpec(*first, left.elevation, left.water - water_move,
                                                 left.mineral, left_solutes, left.vapor - vapor_move)
        cells_after[second] = EnvironmentCellSpec(*second, right.elevation, right.water + water_move,
                                                  right.mineral, right_solutes, right.vapor + vapor_move)
    heat = tuple(HeatCellSpec(x, y, value) for (x, y), value in sorted(heat_after.items()) if value)
    causal = replace(state.causal, heat=heat)
    cells = tuple(x for x in cells_after.values()
                  if x.elevation or x.water or x.mineral or x.vapor or any(x.solutes))
    return EnvironmentState(causal, cells, state.energy_supplied, state.energy_removed, state.format)


def _convert_local_mineral(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentState:
    if spec.format not in (FORMAT_V2, FORMAT_V3, FORMAT_V4) or spec.law.max_mineral_conversion == 0:
        return state
    heat = {(x.x, x.y): x.energy for x in state.causal.heat}
    cells = {(x.x, x.y): x for x in state.cells}
    kind = spec.law.mineral_solute_kind
    cost = spec.law.mineral_conversion_energy
    for point in sorted(cells):
        cell = cells[point]
        if cell.water == 0:
            continue
        local_heat = heat.get(point, 0)
        solutes = list(cell.solutes)
        if local_heat >= spec.law.dissolve_heat_at_least and cell.mineral:
            capacity = cell.water * spec.law.hot_solubility_per_water
            amount = min(spec.law.max_mineral_conversion, cell.mineral,
                         max(0, capacity - solutes[kind]), local_heat // cost)
            if amount:
                solutes[kind] += amount
                local_heat -= amount * cost
                cell = EnvironmentCellSpec(cell.x, cell.y, cell.elevation, cell.water,
                                           cell.mineral - amount, tuple(solutes), cell.vapor)
        elif local_heat <= spec.law.precipitate_heat_at_most and solutes[kind]:
            capacity = cell.water * spec.law.cold_solubility_per_water
            amount = min(spec.law.max_mineral_conversion, max(0, solutes[kind] - capacity))
            if amount:
                solutes[kind] -= amount
                local_heat += amount * cost
                cell = EnvironmentCellSpec(cell.x, cell.y, cell.elevation, cell.water,
                                           cell.mineral + amount, tuple(solutes), cell.vapor)
        heat[point] = local_heat
        cells[point] = cell
    heat_cells = tuple(HeatCellSpec(x, y, value) for (x, y), value in sorted(heat.items()) if value)
    causal = replace(state.causal, heat=heat_cells)
    return EnvironmentState(causal, tuple(cells.values()), state.energy_supplied, state.energy_removed, state.format)


def _exchange_external_energy(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentState:
    if spec.format not in (FORMAT_V3, FORMAT_V4):
        return state
    heat = {(x.x, x.y): x.energy for x in state.causal.heat}
    supplied, removed = state.energy_supplied, state.energy_removed
    for boundary in spec.energy_boundaries:
        point = (boundary.x, boundary.y)
        if boundary.input_per_tick:
            heat[point] = heat.get(point, 0) + boundary.input_per_tick
            supplied += boundary.input_per_tick
        if boundary.output_per_tick:
            amount = min(boundary.output_per_tick, heat.get(point, 0))
            heat[point] = heat.get(point, 0) - amount
            removed += amount
    heat_cells = tuple(HeatCellSpec(x, y, value) for (x, y), value in sorted(heat.items()) if value)
    causal = replace(state.causal, heat=heat_cells)
    return EnvironmentState(causal, state.cells, supplied, removed, state.format)


def _change_water_phase(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentState:
    if spec.format not in (FORMAT_V3, FORMAT_V4) or spec.law.max_water_phase_change == 0:
        return state
    heat = {(x.x, x.y): x.energy for x in state.causal.heat}
    cells = {(x.x, x.y): x for x in state.cells}
    latent = spec.law.vaporization_energy
    for point in sorted(cells):
        cell = cells[point]
        local_heat = heat.get(point, 0)
        water, vapor = cell.water, cell.vapor
        if local_heat >= spec.law.evaporation_heat_at_least and water:
            amount = min(spec.law.max_water_phase_change, water, local_heat // latent)
            water -= amount
            vapor += amount
            local_heat -= amount * latent
        elif local_heat <= spec.law.condensation_heat_at_most and vapor:
            amount = min(spec.law.max_water_phase_change, vapor)
            water += amount
            vapor -= amount
            local_heat += amount * latent
        heat[point] = local_heat
        cells[point] = EnvironmentCellSpec(cell.x, cell.y, cell.elevation, water,
                                           cell.mineral, cell.solutes, vapor)
    heat_cells = tuple(HeatCellSpec(x, y, value) for (x, y), value in sorted(heat.items()) if value)
    causal = replace(state.causal, heat=heat_cells)
    return EnvironmentState(causal, tuple(cells.values()), state.energy_supplied, state.energy_removed, state.format)


def step_environment_world(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentState:
    resources = state.conserved_resources(spec)
    accounted_energy = state.energy_account(spec)["accounted"]
    causal = step_causal_world(spec.causal_world, state.causal)
    result = EnvironmentState(causal, state.cells, state.energy_supplied, state.energy_removed, state.format)
    phases = list(spec.law.phase_order)
    start = state.tick % len(phases)
    for phase in phases[start:] + phases[:start]: result = _phase(spec, result, phase)
    result = _exchange_external_energy(spec, result)
    result = _convert_local_mineral(spec, result)
    result = _change_water_phase(spec, result)
    if result.conserved_resources(spec) != resources: raise AssertionError("environment tick changed conserved resources")
    if result.energy_account(spec)["accounted"] != accounted_energy:
        raise AssertionError("environment tick violated the external energy account")
    return result


def _record(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentTickRecord:
    conserved = state.conserved_resources(spec) if spec.format in (FORMAT_V2, FORMAT_V3, FORMAT_V4) else None
    account = state.energy_account(spec) if spec.format in (FORMAT_V3, FORMAT_V4) else None
    return EnvironmentTickRecord(state.tick, state.digest, state.total_energy(spec),
                                 state.resource_totals(spec.solute_kinds, spec.format in (FORMAT_V3, FORMAT_V4)),
                                 conserved, account)


def run_environment_world(spec: EnvironmentWorldSpec) -> EnvironmentRun:
    state = initial_environment_state(spec); initial = state; checkpoints = [_record(spec, state)]
    for _ in range(spec.causal_world.ticks):
        state = step_environment_world(spec, state)
        if state.tick % spec.causal_world.hash_interval == 0 or state.tick == spec.causal_world.ticks: checkpoints.append(_record(spec, state))
    return EnvironmentRun(spec.digest, initial, state, tuple(checkpoints))
