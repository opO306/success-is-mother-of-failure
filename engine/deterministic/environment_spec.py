"""A2 deterministic environment specification: local heat, water, minerals, and solutes."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .causal_spec import CausalWorldSpec
from .physical_scale import DiffusiveFluxLaw, PhysicalUnitContract, PhysicalWorldScale

FORMAT_V1 = "deterministic-environment-world-spec-v1"
FORMAT_V2 = "deterministic-environment-world-spec-v2"
FORMAT_V3 = "deterministic-environment-world-spec-v3"
FORMAT_V4 = "deterministic-environment-world-spec-v4"
FORMAT = FORMAT_V1


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping): raise ValueError(f"{context} must be an object")
    return value


def _exact(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    missing, unknown = expected - set(value), set(value) - expected
    if missing or unknown: raise ValueError(f"{context} keys differ: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{context} must be an integer of at least {minimum}")
    return value


@dataclass(frozen=True, order=True)
class EnvironmentCellSpec:
    x: int
    y: int
    elevation: int
    water: int
    mineral: int
    solutes: tuple[int, ...]
    vapor: int = 0

    def canonical(self, include_vapor: bool = False) -> dict[str, object]:
        result = {"elevation": self.elevation, "mineral": self.mineral, "solutes": list(self.solutes),
                  "water": self.water, "x": self.x, "y": self.y}
        if include_vapor:
            result["vapor"] = self.vapor
        return result


@dataclass(frozen=True, order=True)
class BlockedEdgeSpec:
    first: tuple[int, int]
    second: tuple[int, int]

    def __post_init__(self) -> None:
        if self.second < self.first:
            first, second = self.second, self.first
            object.__setattr__(self, "first", first); object.__setattr__(self, "second", second)

    def canonical(self) -> dict[str, object]:
        return {"first": list(self.first), "second": list(self.second)}


@dataclass(frozen=True, order=True)
class EnergyBoundarySpec:
    x: int
    y: int
    input_per_tick: int
    output_per_tick: int

    def canonical(self) -> dict[str, object]:
        return {"input_per_tick": self.input_per_tick, "output_per_tick": self.output_per_tick,
                "x": self.x, "y": self.y}


@dataclass(frozen=True)
class EnvironmentLawSpec:
    max_heat_transfer: int
    max_water_transfer: int
    max_solute_transfer: int
    phase_order: tuple[str, ...]
    max_carried_solute_per_water: int = 0
    mineral_solute_kind: int = 0
    dissolve_heat_at_least: int = 0
    precipitate_heat_at_most: int = 0
    hot_solubility_per_water: int = 0
    cold_solubility_per_water: int = 0
    max_mineral_conversion: int = 0
    mineral_conversion_energy: int = 0
    max_vapor_transfer: int = 0
    evaporation_heat_at_least: int = 0
    condensation_heat_at_most: int = 0
    max_water_phase_change: int = 0
    vaporization_energy: int = 0
    # G10 (2026-09-24, RULES "laws at the most fundamental level"): solid
    # matter occupies space -- water's surface in a cell sits on top of the
    # ground *and* the solid matter there. A general property of matter, not a
    # purpose: nothing here mentions dams or channels. Off by default, and
    # absent from `canonical()` when off, so every existing world keeps its
    # exact digest. Not implemented on the GPU path, which refuses it.
    solids_occupy_space: bool = False

    def canonical(self, format_name: str = FORMAT_V1) -> dict[str, object]:
        result: dict[str, object] = {
            "max_heat_transfer": self.max_heat_transfer,
            "max_solute_transfer": self.max_solute_transfer,
            "max_water_transfer": self.max_water_transfer,
            "phase_order": list(self.phase_order),
        }
        if format_name in (FORMAT_V2, FORMAT_V3, FORMAT_V4):
            result.update({
                "cold_solubility_per_water": self.cold_solubility_per_water,
                "dissolve_heat_at_least": self.dissolve_heat_at_least,
                "hot_solubility_per_water": self.hot_solubility_per_water,
                "max_carried_solute_per_water": self.max_carried_solute_per_water,
                "max_mineral_conversion": self.max_mineral_conversion,
                "mineral_conversion_energy": self.mineral_conversion_energy,
                "mineral_solute_kind": self.mineral_solute_kind,
                "precipitate_heat_at_most": self.precipitate_heat_at_most,
            })
        if self.solids_occupy_space:
            result["solids_occupy_space"] = True
        if format_name in (FORMAT_V3, FORMAT_V4):
            result.update({
                "condensation_heat_at_most": self.condensation_heat_at_most,
                "evaporation_heat_at_least": self.evaporation_heat_at_least,
                "max_vapor_transfer": self.max_vapor_transfer,
                "max_water_phase_change": self.max_water_phase_change,
                "vaporization_energy": self.vaporization_energy,
            })
        return result


@dataclass(frozen=True)
class EnvironmentWorldSpec:
    causal_world: CausalWorldSpec
    solute_kinds: int
    cells: tuple[EnvironmentCellSpec, ...]
    blocked_edges: tuple[BlockedEdgeSpec, ...]
    law: EnvironmentLawSpec
    energy_boundaries: tuple[EnergyBoundarySpec, ...] = ()
    physical_scale: PhysicalWorldScale | None = None
    format: str = FORMAT

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {"blocked_edges": [x.canonical() for x in self.blocked_edges],
                  "causal_world": self.causal_world.canonical(),
                  "cells": [x.canonical(self.format in (FORMAT_V3, FORMAT_V4)) for x in self.cells],
                  "format": self.format, "law": self.law.canonical(self.format),
                  "solute_kinds": self.solute_kinds}
        if self.format in (FORMAT_V3, FORMAT_V4):
            result["energy_boundaries"] = [x.canonical() for x in self.energy_boundaries]
        if self.format == FORMAT_V4:
            if self.physical_scale is None: raise ValueError("environment v4 needs a physical scale")
            result["physical_scale"] = self.physical_scale.canonical()
        return result

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EnvironmentWorldSpec":
        format_name = raw.get("format")
        if format_name not in (FORMAT_V1, FORMAT_V2, FORMAT_V3, FORMAT_V4): raise ValueError("unsupported environment world format")
        base_keys = {"format", "causal_world", "solute_kinds", "cells", "blocked_edges", "law"}
        open_keys = {"energy_boundaries"} if format_name in (FORMAT_V3, FORMAT_V4) else set()
        scale_keys = {"physical_scale"} if format_name == FORMAT_V4 else set()
        _exact(raw, base_keys | open_keys | scale_keys, "environment world")
        causal = CausalWorldSpec.from_mapping(_object(raw["causal_world"], "causal_world"))
        if causal.kernel.width % 2 or causal.kernel.height % 2:
            raise ValueError("environment v1 needs even grid dimensions for disjoint edge phases")
        kinds = _integer(raw["solute_kinds"], "solute_kinds", 1)
        cells_raw = raw["cells"]
        if not isinstance(cells_raw, list): raise ValueError("cells must be a list")
        cells = []
        for index, value in enumerate(cells_raw):
            item = _object(value, f"cells[{index}]")
            cell_keys = {"x", "y", "elevation", "water", "mineral", "solutes"}
            _exact(item, cell_keys | ({"vapor"} if format_name in (FORMAT_V3, FORMAT_V4) else set()), f"cells[{index}]")
            solutes = item["solutes"]
            if not isinstance(solutes, list) or len(solutes) != kinds:
                raise ValueError("every environment cell needs one amount per solute kind")
            cell = EnvironmentCellSpec(_integer(item["x"], "cell.x"), _integer(item["y"], "cell.y"),
                _integer(item["elevation"], "cell.elevation"), _integer(item["water"], "cell.water"),
                _integer(item["mineral"], "cell.mineral"), tuple(_integer(x, "cell.solute") for x in solutes),
                _integer(item.get("vapor", 0), "cell.vapor"))
            if not (0 <= cell.x < causal.kernel.width and 0 <= cell.y < causal.kernel.height):
                raise ValueError("environment cell lies outside the world")
            cells.append(cell)
        if len({(x.x, x.y) for x in cells}) != len(cells): raise ValueError("environment cell locations must be unique")

        edges_raw = raw["blocked_edges"]
        if not isinstance(edges_raw, list): raise ValueError("blocked_edges must be a list")
        edges = []
        for index, value in enumerate(edges_raw):
            item = _object(value, f"blocked_edges[{index}]")
            _exact(item, {"first", "second"}, f"blocked_edges[{index}]")
            points = []
            for name in ("first", "second"):
                point = item[name]
                if not isinstance(point, list) or len(point) != 2: raise ValueError("blocked edge points need x and y")
                points.append((_integer(point[0], "edge.x"), _integer(point[1], "edge.y")))
            edge = BlockedEdgeSpec(points[0], points[1])
            if any(not (0 <= x < causal.kernel.width and 0 <= y < causal.kernel.height) for x, y in (edge.first, edge.second)):
                raise ValueError("blocked edge lies outside the world")
            dx = min((edge.first[0] - edge.second[0]) % causal.kernel.width, (edge.second[0] - edge.first[0]) % causal.kernel.width)
            dy = min((edge.first[1] - edge.second[1]) % causal.kernel.height, (edge.second[1] - edge.first[1]) % causal.kernel.height)
            if dx + dy != 1: raise ValueError("blocked edge points must be wrapped cardinal neighbors")
            edges.append(edge)
        if len(set(edges)) != len(edges): raise ValueError("blocked edges must be unique")

        boundaries = []
        if format_name in (FORMAT_V3, FORMAT_V4):
            boundary_raw = raw["energy_boundaries"]
            if not isinstance(boundary_raw, list): raise ValueError("energy_boundaries must be a list")
            for index, value in enumerate(boundary_raw):
                item = _object(value, f"energy_boundaries[{index}]")
                _exact(item, {"x", "y", "input_per_tick", "output_per_tick"}, f"energy_boundaries[{index}]")
                boundary = EnergyBoundarySpec(
                    _integer(item["x"], "energy_boundary.x"), _integer(item["y"], "energy_boundary.y"),
                    _integer(item["input_per_tick"], "energy_boundary.input_per_tick"),
                    _integer(item["output_per_tick"], "energy_boundary.output_per_tick"))
                if not (0 <= boundary.x < causal.kernel.width and 0 <= boundary.y < causal.kernel.height):
                    raise ValueError("energy boundary lies outside the world")
                if boundary.input_per_tick and boundary.output_per_tick:
                    raise ValueError("one energy boundary cannot supply and remove in the same tick")
                boundaries.append(boundary)
            if len({(x.x, x.y) for x in boundaries}) != len(boundaries):
                raise ValueError("energy boundary locations must be unique")

        lr = _object(raw["law"], "law")
        base_keys = {"max_heat_transfer", "max_water_transfer", "max_solute_transfer", "phase_order"}
        v2_keys = base_keys | {"max_carried_solute_per_water", "mineral_solute_kind", "dissolve_heat_at_least",
                               "precipitate_heat_at_most", "hot_solubility_per_water", "cold_solubility_per_water",
                               "max_mineral_conversion", "mineral_conversion_energy"}
        v3_keys = v2_keys | {"max_vapor_transfer", "evaporation_heat_at_least",
                             "condensation_heat_at_most", "max_water_phase_change", "vaporization_energy"}
        expected_keys = base_keys if format_name == FORMAT_V1 else (v2_keys if format_name == FORMAT_V2 else v3_keys)
        _exact(lr, expected_keys, "law")
        expected = ("horizontal_even", "horizontal_odd", "vertical_even", "vertical_odd")
        if not isinstance(lr["phase_order"], list) or tuple(lr["phase_order"]) != expected:
            raise ValueError("environment v1/v2/v3 requires the four declared disjoint phases")
        if format_name == FORMAT_V1:
            law = EnvironmentLawSpec(_integer(lr["max_heat_transfer"], "law.max_heat_transfer"),
                _integer(lr["max_water_transfer"], "law.max_water_transfer"),
                _integer(lr["max_solute_transfer"], "law.max_solute_transfer"), expected)
        else:
            mineral_kind = _integer(lr["mineral_solute_kind"], "law.mineral_solute_kind")
            if mineral_kind >= kinds: raise ValueError("mineral_solute_kind must name an existing solute channel")
            dissolve_at = _integer(lr["dissolve_heat_at_least"], "law.dissolve_heat_at_least")
            precipitate_at = _integer(lr["precipitate_heat_at_most"], "law.precipitate_heat_at_most")
            hot_capacity = _integer(lr["hot_solubility_per_water"], "law.hot_solubility_per_water")
            cold_capacity = _integer(lr["cold_solubility_per_water"], "law.cold_solubility_per_water")
            conversion_limit = _integer(lr["max_mineral_conversion"], "law.max_mineral_conversion")
            conversion_energy = _integer(lr["mineral_conversion_energy"], "law.mineral_conversion_energy")
            if dissolve_at <= precipitate_at:
                raise ValueError("dissolve heat threshold must exceed precipitate heat threshold")
            if hot_capacity < cold_capacity:
                raise ValueError("hot solubility must be at least cold solubility")
            if conversion_limit and conversion_energy == 0:
                raise ValueError("active mineral conversion needs positive stored energy")
            extra = (0, 0, 0, 0, 0)
            if format_name in (FORMAT_V3, FORMAT_V4):
                evaporation_at = _integer(lr["evaporation_heat_at_least"], "law.evaporation_heat_at_least")
                condensation_at = _integer(lr["condensation_heat_at_most"], "law.condensation_heat_at_most")
                phase_limit = _integer(lr["max_water_phase_change"], "law.max_water_phase_change")
                vaporization_energy = _integer(lr["vaporization_energy"], "law.vaporization_energy")
                if evaporation_at <= condensation_at:
                    raise ValueError("evaporation heat threshold must exceed condensation heat threshold")
                if phase_limit and vaporization_energy == 0:
                    raise ValueError("active water phase change needs positive latent energy")
                extra = (_integer(lr["max_vapor_transfer"], "law.max_vapor_transfer"),
                         evaporation_at, condensation_at, phase_limit, vaporization_energy)
            law = EnvironmentLawSpec(
                _integer(lr["max_heat_transfer"], "law.max_heat_transfer"),
                _integer(lr["max_water_transfer"], "law.max_water_transfer"),
                _integer(lr["max_solute_transfer"], "law.max_solute_transfer"), expected,
                _integer(lr["max_carried_solute_per_water"], "law.max_carried_solute_per_water"),
                mineral_kind, dissolve_at, precipitate_at, hot_capacity, cold_capacity,
                conversion_limit, conversion_energy, *extra)
        physical_scale = None
        if format_name == FORMAT_V4:
            sr = _object(raw["physical_scale"], "physical_scale")
            _exact(sr, {"cell_length_pm", "tick_duration_fs", "units", "flux_laws"}, "physical_scale")
            ur = _object(sr["units"], "physical_scale.units")
            _exact(ur, {"cell_length_unit", "tick_duration_unit", "height_quantum_pm",
                        "matter_quantum_unit", "matter_quantum_yoctomol",
                        "energy_quantum_unit", "energy_quantum_zj"}, "physical_scale.units")
            expected_units = {"cell_length_unit": "picometer", "tick_duration_unit": "femtosecond",
                              "matter_quantum_unit": "yoctomole", "energy_quantum_unit": "zeptojoule"}
            if any(ur[name] != value for name, value in expected_units.items()):
                raise ValueError("physical scale uses unsupported unit labels")
            units = PhysicalUnitContract(_integer(ur["height_quantum_pm"], "height_quantum_pm", 1),
                                         _integer(ur["matter_quantum_yoctomol"], "matter_quantum_yoctomol", 1),
                                         _integer(ur["energy_quantum_zj"], "energy_quantum_zj", 1))
            laws_raw = sr["flux_laws"]
            if not isinstance(laws_raw, list): raise ValueError("physical_scale.flux_laws must be a list")
            laws = []
            for index, value in enumerate(laws_raw):
                item = _object(value, f"physical_scale.flux_laws[{index}]")
                _exact(item, {"channel", "diffusivity"}, f"physical_scale.flux_laws[{index}]")
                diffusion = _object(item["diffusivity"], "diffusivity")
                _exact(diffusion, {"numerator_pm2", "denominator_fs"}, "diffusivity")
                if not isinstance(item["channel"], str): raise ValueError("flux channel must be text")
                laws.append(DiffusiveFluxLaw(item["channel"],
                    _integer(diffusion["numerator_pm2"], "diffusivity.numerator_pm2", 1),
                    _integer(diffusion["denominator_fs"], "diffusivity.denominator_fs", 1)))
            physical_scale = PhysicalWorldScale(
                units, _integer(sr["cell_length_pm"], "physical_scale.cell_length_pm", 1),
                _integer(sr["tick_duration_fs"], "physical_scale.tick_duration_fs", 1), tuple(laws))
        return cls(causal, kinds, tuple(sorted(cells)), tuple(sorted(edges)), law,
                   tuple(sorted(boundaries)), physical_scale, format_name)


def load_environment_world_spec(path: Path) -> EnvironmentWorldSpec:
    try: raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc: raise ValueError("environment world specification is not valid JSON") from exc
    return EnvironmentWorldSpec.from_mapping(_object(raw, "environment world"))
