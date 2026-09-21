"""Resolution audit for all A2.3 transport channels using physical flux v4."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from .environment_kernel import EnvironmentState, run_environment_world
from .environment_spec import EnvironmentWorldSpec
from .physical_scale import RefinementLevel, reference_scale_family


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(level: RefinementLevel, channel: str) -> dict[str, object]:
    family = reference_scale_family()
    raw: dict[str, object] = {
        "format": "deterministic-environment-world-spec-v4",
        "causal_world": {
            "format": "deterministic-causal-world-spec-v1", "world_id": f"physical-{channel}-{level.grid_size}",
            "kernel": {"width": level.grid_size, "height": level.grid_size, "boundary": "wrap",
                       "arithmetic": "integer", "deterministic": True,
                       "tick_order": ["break_existing_bonds", "stream_free_particles", "resolve_local_collisions"]},
            "materials": [{"kind": 0, "mass": 1, "ports": 4}], "particles": [], "heat": [],
            "bond_rules": [], "execution": {"ticks": level.ticks}, "observer": {"hash_interval": level.ticks},
        },
        "solute_kinds": 2, "cells": [], "blocked_edges": [], "energy_boundaries": [],
        "law": {
            "max_heat_transfer": 1000000000 if channel == "heat" else 0,
            "max_water_transfer": 1000000000 if channel == "water_surface" else 0,
            "max_solute_transfer": 1000000000 if channel == "solute" else 0,
            "phase_order": ["horizontal_even", "horizontal_odd", "vertical_even", "vertical_odd"],
            "max_carried_solute_per_water": 0, "mineral_solute_kind": 0,
            "dissolve_heat_at_least": 1000000000, "precipitate_heat_at_most": 0,
            "hot_solubility_per_water": 2, "cold_solubility_per_water": 1,
            "max_mineral_conversion": 0, "mineral_conversion_energy": 1,
            "max_vapor_transfer": 1000000000 if channel == "vapor" else 0,
            "evaporation_heat_at_least": 1000000000, "condensation_heat_at_most": 0,
            "max_water_phase_change": 0, "vaporization_energy": 1,
        },
        "physical_scale": {
            "cell_length_pm": level.cell_length_pm, "tick_duration_fs": level.tick_duration_fs,
            "units": family.units.canonical(), "flux_laws": [x.canonical() for x in family.flux_laws],
        },
    }
    side = 16 // level.cell_length_pm
    start = level.grid_size // 2 - side // 2
    square = {(x, y) for y in range(start, start + side) for x in range(start, start + side)}
    if channel == "heat":
        raw["causal_world"]["heat"] = [
            {"x": x, "y": y, "energy": 256 * level.cell_length_pm ** 2} for x, y in sorted(square)]
    elif channel == "water_surface":
        raw["cells"] = [
            {"x": x, "y": y, "elevation": 0, "water": 256, "vapor": 0,
             "mineral": 0, "solutes": [0, 0]} for x, y in sorted(square)]
    elif channel == "vapor":
        raw["cells"] = [
            {"x": x, "y": y, "elevation": 0, "water": 0, "vapor": 256,
             "mineral": 0, "solutes": [0, 0]} for x, y in sorted(square)]
    elif channel == "solute":
        raw["cells"] = [
            {"x": x, "y": y, "elevation": 0, "water": 1, "vapor": 0,
             "mineral": 0, "solutes": [0, 256 * level.cell_length_pm ** 2 if (x, y) in square else 0]}
            for y in range(level.grid_size) for x in range(level.grid_size)]
    else:
        raise ValueError("unsupported channel")
    return raw


def make_physical_channel_spec(level: RefinementLevel, channel: str) -> EnvironmentWorldSpec:
    return EnvironmentWorldSpec.from_mapping(_mapping(level, channel))


def _field(state: EnvironmentState, channel: str) -> dict[tuple[int, int], int]:
    if channel == "heat": return {(x.x, x.y): x.energy for x in state.causal.heat}
    if channel == "water_surface": return {(x.x, x.y): x.water for x in state.cells if x.water}
    if channel == "vapor": return {(x.x, x.y): x.vapor for x in state.cells if x.vapor}
    if channel == "solute": return {(x.x, x.y): x.solutes[1] for x in state.cells if x.solutes[1]}
    raise ValueError("unsupported channel")


def _physical_amount(value: int, channel: str, cell_length_pm: int) -> int:
    return value * cell_length_pm ** 2 if channel in ("water_surface", "vapor") else value


def _moment(values: dict[tuple[int, int], int], channel: str, level: RefinementLevel) -> Fraction:
    domain = level.domain_length_pm; center2 = domain
    total = 0; weighted = 0
    for (x, y), value in values.items():
        amount = _physical_amount(value, channel, level.cell_length_pm)
        x2 = (2 * x + 1) * level.cell_length_pm; y2 = (2 * y + 1) * level.cell_length_pm
        dx2 = min((x2 - center2) % (2 * domain), (center2 - x2) % (2 * domain))
        dy2 = min((y2 - center2) % (2 * domain), (center2 - y2) % (2 * domain))
        total += amount; weighted += amount * (dx2 * dx2 + dy2 * dy2)
    return Fraction(weighted, total * (2 * domain) ** 2)


@dataclass(frozen=True)
class PhysicalChannelObservation:
    channel: str
    level: RefinementLevel
    initial_physical_amount: int
    final_physical_amount: int
    normalized_second_moment: Fraction
    final_state_digest: str

    def canonical(self) -> dict[str, object]:
        moment = self.normalized_second_moment
        return {"channel": self.channel, "final_physical_amount": self.final_physical_amount,
                "final_state_digest": self.final_state_digest, "initial_physical_amount": self.initial_physical_amount,
                "level": self.level.canonical(),
                "normalized_second_moment": {"numerator": moment.numerator, "denominator": moment.denominator}}


@dataclass(frozen=True)
class PhysicalChannelAudit:
    channel: str
    observations: tuple[PhysicalChannelObservation, ...]
    successive_differences: tuple[Fraction, ...]
    differences_decrease: bool
    status: str

    def canonical(self) -> dict[str, object]:
        return {"channel": self.channel, "differences_decrease": self.differences_decrease,
                "observations": [x.canonical() for x in self.observations], "status": self.status,
                "successive_differences": [{"numerator": x.numerator, "denominator": x.denominator}
                                           for x in self.successive_differences]}


@dataclass(frozen=True)
class PhysicalEnvironmentScalingAudit:
    contract_digest: str
    channels: tuple[PhysicalChannelAudit, ...]
    all_channels_candidate: bool

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"all_channels_candidate": self.all_channels_candidate, "channels": [x.canonical() for x in self.channels],
                "contract_digest": self.contract_digest, "format": "physical-environment-scaling-audit-v1"}


def _audit_channel(channel: str) -> PhysicalChannelAudit:
    family = reference_scale_family(); observations = []
    for level in family.levels:
        spec = make_physical_channel_spec(level, channel)
        initial_run = run_environment_world(EnvironmentWorldSpec.from_mapping({
            **spec.canonical(), "causal_world": {**spec.causal_world.canonical(), "execution": {"ticks": 0}}
        }))
        initial_values = _field(initial_run.final_state, channel)
        run = run_environment_world(spec); final_values = _field(run.final_state, channel)
        initial_amount = sum(_physical_amount(x, channel, level.cell_length_pm) for x in initial_values.values())
        final_amount = sum(_physical_amount(x, channel, level.cell_length_pm) for x in final_values.values())
        observations.append(PhysicalChannelObservation(channel, level, initial_amount, final_amount,
                                                        _moment(final_values, channel, level), run.final_state.digest))
    differences = tuple(abs(observations[index + 1].normalized_second_moment - observations[index].normalized_second_moment)
                        for index in range(len(observations) - 1))
    decreasing = bool(differences) and all(b <= a for a, b in zip(differences, differences[1:]))
    conserved = len({x.initial_physical_amount for x in observations} | {x.final_physical_amount for x in observations}) == 1
    status = "candidate-converging" if decreasing and conserved else ("not-conserved" if not conserved else "not-converging")
    return PhysicalChannelAudit(channel, tuple(observations), differences, decreasing, status)


def run_physical_environment_scaling_audit() -> PhysicalEnvironmentScalingAudit:
    family = reference_scale_family()
    channels = tuple(_audit_channel(channel) for channel in ("heat", "water_surface", "solute", "vapor"))
    return PhysicalEnvironmentScalingAudit(family.digest, channels,
                                           all(x.status == "candidate-converging" for x in channels))
