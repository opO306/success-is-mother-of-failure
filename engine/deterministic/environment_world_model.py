"""B environment world model v0: exact read-only forecasts over A2/A2.1.

Like the A1 model, this first environment model executes the sealed transition
law on an immutable state copy. It establishes prediction and evaluation
contracts; it is not a learned or independent surrogate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .environment_kernel import (
    EnvironmentRun,
    EnvironmentState,
    initial_environment_state,
    step_environment_world,
)
from .environment_spec import EnvironmentWorldSpec, FORMAT_V2, FORMAT_V3, FORMAT_V4
from .world_model import (
    MAX_FORECAST_TICKS,
    ForecastEvaluation,
    RuleMapEntry,
    explain_causal_transition,
    build_rule_map,
)


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EnvironmentForecastStep:
    tick: int
    before_digest: str
    after_digest: str
    predicted_events: tuple[dict[str, object], ...]
    total_energy: int
    resources: dict[str, object]
    conserved_resources: dict[str, object]
    energy_account: dict[str, int] | None = None

    def canonical(self) -> dict[str, object]:
        result = {
            "after_digest": self.after_digest,
            "before_digest": self.before_digest,
            "conserved_resources": self.conserved_resources,
            "predicted_events": list(self.predicted_events),
            "resources": self.resources,
            "tick": self.tick,
            "total_energy": self.total_energy,
        }
        if self.energy_account is not None:
            result["energy_account"] = self.energy_account
        return result


@dataclass(frozen=True)
class EnvironmentWorldForecast:
    spec_digest: str
    model_kind: str
    rule_map: tuple[RuleMapEntry, ...]
    initial_digest: str
    steps: tuple[EnvironmentForecastStep, ...]

    @property
    def final_digest(self) -> str:
        return self.steps[-1].after_digest if self.steps else self.initial_digest

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "final_digest": self.final_digest,
            "format": "b-environment-world-forecast-v0",
            "initial_digest": self.initial_digest,
            "model_kind": self.model_kind,
            "rule_map": [item.canonical() for item in self.rule_map],
            "spec_digest": self.spec_digest,
            "steps": [item.canonical() for item in self.steps],
        }


def build_environment_rule_map(spec: EnvironmentWorldSpec) -> tuple[RuleMapEntry, ...]:
    entries = list(build_rule_map(spec.causal_world))
    entries.extend((
        RuleMapEntry(
            "environment.heat-transfer", "wrapped_cardinal_edge", "local_heat_transfer",
            ("absolute_heat_difference>=2", f"transfer_limit={spec.law.max_heat_transfer}", "edge_not_blocked"),
            ("heat moves from higher local amount to lower local amount",), ("energy",),
        ),
        RuleMapEntry(
            "environment.water-transfer", "wrapped_cardinal_edge", "downhill_water_transfer",
            ("absolute_surface_height_difference>=2", f"transfer_limit={spec.law.max_water_transfer}",
             "source_water>0", "edge_not_blocked"),
            ("water moves from higher elevation+water to lower elevation+water",), ("water",),
        ),
        RuleMapEntry(
            "environment.solute-diffusion", "wrapped_cardinal_edge", "local_solute_diffusion",
            ("both_cells_wet", "absolute_solute_amount_difference>=2",
             f"transfer_limit={spec.law.max_solute_transfer}", "edge_not_blocked"),
            ("solute moves from higher local amount to lower local amount",), ("material_inventory",),
        ),
    ))
    if spec.format in (FORMAT_V2, FORMAT_V3, FORMAT_V4):
        entries.append(RuleMapEntry(
            "environment.water-carried-solute", "wrapped_cardinal_edge", "water_coupled_solute_transport",
            ("water_transfer!=0", f"solute_per_water_limit={spec.law.max_carried_solute_per_water}",
             "edge_not_blocked"),
            ("moving water carries bounded local solute before diffusion",), ("water", "material_inventory"),
        ))
        if spec.law.max_mineral_conversion:
            entries.extend((
                RuleMapEntry(
                    "environment.mineral-dissolution", "same_cell", "local_mineral_dissolution",
                    ("water>0", "mineral>0", f"local_heat>={spec.law.dissolve_heat_at_least}",
                     f"solute<{spec.law.hot_solubility_per_water}*water",
                     f"conversion_limit={spec.law.max_mineral_conversion}"),
                    ("mineral -> selected solute", "local heat -> dissolved chemical storage"),
                    ("material_inventory", "energy"),
                ),
                RuleMapEntry(
                    "environment.mineral-precipitation", "same_cell", "local_mineral_precipitation",
                    ("water>0", f"local_heat<={spec.law.precipitate_heat_at_most}",
                     f"solute>{spec.law.cold_solubility_per_water}*water",
                     f"conversion_limit={spec.law.max_mineral_conversion}"),
                    ("selected solute -> mineral", "dissolved chemical storage -> local heat"),
                    ("material_inventory", "energy"),
                ),
            ))
    if spec.format in (FORMAT_V3, FORMAT_V4):
        entries.extend((
            RuleMapEntry(
                "environment.vapor-transfer", "wrapped_cardinal_edge", "local_vapor_diffusion",
                ("absolute_vapor_difference>=2", f"transfer_limit={spec.law.max_vapor_transfer}",
                 "edge_not_blocked"),
                ("vapor moves from higher local amount to lower local amount",), ("water", "energy"),
            ),
            RuleMapEntry(
                "environment.external-energy", "same_cell", "external_energy_exchange",
                ("declared_boundary_location", "fixed_input_or_bounded_output_per_tick"),
                ("boundary input -> local heat", "local heat -> boundary output ledger"),
                ("accounted_energy",),
            ),
            RuleMapEntry(
                "environment.evaporation", "same_cell", "local_evaporation",
                ("water>0", f"local_heat>={spec.law.evaporation_heat_at_least}",
                 f"phase_change_limit={spec.law.max_water_phase_change}"),
                ("liquid water -> vapor", "local heat -> vapor latent storage"), ("water", "energy"),
            ),
            RuleMapEntry(
                "environment.condensation", "same_cell", "local_condensation",
                ("vapor>0", f"local_heat<={spec.law.condensation_heat_at_most}",
                 f"phase_change_limit={spec.law.max_water_phase_change}"),
                ("vapor -> liquid water", "vapor latent storage -> local heat"), ("water", "energy"),
            ),
        ))
    return tuple(entries)


def _cell_map(state: EnvironmentState):
    return {(item.x, item.y): item for item in state.cells}


def _explain_environment_transition(
    before: EnvironmentState, after: EnvironmentState,
) -> tuple[dict[str, object], ...]:
    events = list(explain_causal_transition(before.causal, after.causal))
    if before.energy_supplied != after.energy_supplied:
        events.append({"kind": "external_energy_supplied", "before": before.energy_supplied,
                       "after": after.energy_supplied, "amount": after.energy_supplied - before.energy_supplied})
    if before.energy_removed != after.energy_removed:
        events.append({"kind": "external_energy_removed", "before": before.energy_removed,
                       "after": after.energy_removed, "amount": after.energy_removed - before.energy_removed})
    before_cells, after_cells = _cell_map(before), _cell_map(after)
    points = sorted(set(before_cells) | set(after_cells))
    solute_kinds = max((len(item.solutes) for item in before.cells + after.cells), default=0)
    for point in points:
        old = before_cells.get(point)
        new = after_cells.get(point)
        old_water, new_water = (old.water if old else 0), (new.water if new else 0)
        old_vapor, new_vapor = (old.vapor if old else 0), (new.vapor if new else 0)
        old_mineral, new_mineral = (old.mineral if old else 0), (new.mineral if new else 0)
        if old_water != new_water:
            events.append({"kind": "local_water_changed", "location": list(point),
                           "before": old_water, "after": new_water})
        if old_vapor != new_vapor:
            events.append({"kind": "local_vapor_changed", "location": list(point),
                           "before": old_vapor, "after": new_vapor})
        if old_mineral != new_mineral:
            kind = "mineral_dissolved" if new_mineral < old_mineral else "mineral_precipitated"
            events.append({"kind": kind, "location": list(point),
                           "before": old_mineral, "after": new_mineral})
        old_solutes = old.solutes if old else (0,) * solute_kinds
        new_solutes = new.solutes if new else (0,) * solute_kinds
        for channel in range(solute_kinds):
            if old_solutes[channel] != new_solutes[channel]:
                events.append({"kind": "local_solute_changed", "location": list(point), "channel": channel,
                               "before": old_solutes[channel], "after": new_solutes[channel]})
    return tuple(events)


def forecast_environment_world(
    spec: EnvironmentWorldSpec, ticks: int | None = None,
) -> EnvironmentWorldForecast:
    horizon = min(spec.causal_world.ticks, MAX_FORECAST_TICKS) if ticks is None else ticks
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 0 <= horizon <= MAX_FORECAST_TICKS:
        raise ValueError(f"forecast horizon must be from zero through {MAX_FORECAST_TICKS}")
    state = initial_environment_state(spec)
    initial_digest = state.digest
    steps = []
    for _ in range(horizon):
        before = state
        state = step_environment_world(spec, before)
        steps.append(EnvironmentForecastStep(
            state.tick, before.digest, state.digest, _explain_environment_transition(before, state),
            state.total_energy(spec),
            state.resource_totals(spec.solute_kinds, spec.format in (FORMAT_V3, FORMAT_V4)),
            state.conserved_resources(spec),
            state.energy_account(spec) if spec.format in (FORMAT_V3, FORMAT_V4) else None,
        ))
    if initial_environment_state(spec).digest != initial_digest:
        raise AssertionError("environment forecast changed the supplied specification")
    return EnvironmentWorldForecast(
        spec.digest, "exact-read-only-a2-environment-clone", build_environment_rule_map(spec),
        initial_digest, tuple(steps),
    )


def evaluate_environment_forecast(
    forecast: EnvironmentWorldForecast, run: EnvironmentRun,
) -> ForecastEvaluation:
    predicted = {item.tick: item.after_digest for item in forecast.steps}
    actual = {item.tick: item.state_digest for item in run.checkpoints if item.tick in predicted}
    compared = tuple(sorted(set(predicted) & set(actual)))
    matched = []
    mismatches = []
    for tick in compared:
        if predicted[tick] == actual[tick]:
            matched.append(tick)
        else:
            mismatches.append({"tick": tick, "predicted": predicted[tick], "actual": actual[tick]})
    for tick in sorted(set(predicted) - set(actual)):
        mismatches.append({"tick": tick, "predicted": predicted[tick], "actual": None,
                           "reason": "run has no checkpoint"})
    return ForecastEvaluation(
        forecast.digest, run.digest, compared, tuple(matched), tuple(mismatches),
        forecast.spec_digest == run.spec_digest,
    )
