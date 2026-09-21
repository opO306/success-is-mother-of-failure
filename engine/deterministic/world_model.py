"""B world model v0: exact, read-only forecasts over the A1 causal kernel.

This first model deliberately reuses the sealed deterministic transition law on
an immutable copy.  It establishes the prediction/evaluation/archive contract;
it is not yet a learned or independent surrogate model.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .causal_kernel import CausalRun, CausalWorldState, initial_causal_state, step_causal_world
from .causal_spec import CausalWorldSpec

MAX_FORECAST_TICKS = 10


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bond_key(value) -> tuple[object, ...]:
    return value.left_id, value.right_id, value.rule_id, value.x, value.y, value.stored_energy


@dataclass(frozen=True)
class RuleMapEntry:
    rule_id: str
    locality: str
    event: str
    requirements: tuple[str, ...]
    effects: tuple[str, ...]
    conserves: tuple[str, ...]

    def canonical(self) -> dict[str, object]:
        return {
            "conserves": list(self.conserves),
            "effects": list(self.effects),
            "event": self.event,
            "locality": self.locality,
            "requirements": list(self.requirements),
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True)
class CausalForecastStep:
    tick: int
    before_digest: str
    after_digest: str
    predicted_events: tuple[dict[str, object], ...]
    total_energy: int
    momentum: tuple[int, int]
    material_counts: tuple[tuple[int, int], ...]

    def canonical(self) -> dict[str, object]:
        return {
            "after_digest": self.after_digest,
            "before_digest": self.before_digest,
            "material_counts": {str(kind): amount for kind, amount in self.material_counts},
            "momentum": list(self.momentum),
            "predicted_events": list(self.predicted_events),
            "tick": self.tick,
            "total_energy": self.total_energy,
        }


@dataclass(frozen=True)
class WorldForecast:
    spec_digest: str
    model_kind: str
    rule_map: tuple[RuleMapEntry, ...]
    initial_digest: str
    steps: tuple[CausalForecastStep, ...]

    @property
    def final_digest(self) -> str:
        return self.steps[-1].after_digest if self.steps else self.initial_digest

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "final_digest": self.final_digest,
            "format": "b-world-forecast-v0",
            "initial_digest": self.initial_digest,
            "model_kind": self.model_kind,
            "rule_map": [item.canonical() for item in self.rule_map],
            "spec_digest": self.spec_digest,
            "steps": [item.canonical() for item in self.steps],
        }


@dataclass(frozen=True)
class ForecastEvaluation:
    forecast_digest: str
    run_digest: str
    compared_ticks: tuple[int, ...]
    matched_ticks: tuple[int, ...]
    mismatches: tuple[dict[str, object], ...]
    spec_matches: bool

    @property
    def complete_match(self) -> bool:
        return self.spec_matches and not self.mismatches and self.compared_ticks == self.matched_ticks

    def canonical(self) -> dict[str, object]:
        return {
            "compared_ticks": list(self.compared_ticks),
            "complete_match": self.complete_match,
            "forecast_digest": self.forecast_digest,
            "format": "b-world-model-evaluation-v0",
            "matched_ticks": list(self.matched_ticks),
            "mismatches": list(self.mismatches),
            "run_digest": self.run_digest,
            "spec_matches": self.spec_matches,
        }


def build_rule_map(spec: CausalWorldSpec) -> tuple[RuleMapEntry, ...]:
    entries = []
    for rule in spec.bond_rules:
        entries.append(RuleMapEntry(
            rule.rule_id,
            "same_cell",
            "local_reversible_bond",
            (
                f"left.kind={rule.left_kind}", f"right.kind={rule.right_kind}",
                f"left.orientation={rule.left_orientation}", f"right.orientation={rule.right_orientation}",
                f"total_kinetic>={rule.minimum_collision_energy}", f"local_heat_for_break>={rule.break_heat}",
            ),
            (
                "formation: particle kinetic -> bond stored energy",
                "separation: bond stored energy + local heat -> opposite particle motion",
            ),
            ("material", "energy", "momentum"),
        ))
    return tuple(entries)


def explain_causal_transition(before: CausalWorldState, after: CausalWorldState) -> tuple[dict[str, object], ...]:
    events = []
    before_bonds = {_bond_key(item): item for item in before.bonds}
    after_bonds = {_bond_key(item): item for item in after.bonds}
    for key in sorted(after_bonds.keys() - before_bonds.keys()):
        bond = after_bonds[key]
        events.append({"kind": "bond_formed", "rule_id": bond.rule_id, "location": [bond.x, bond.y],
                       "particle_ids": [bond.left_id, bond.right_id], "stored_energy": bond.stored_energy})
    for key in sorted(before_bonds.keys() - after_bonds.keys()):
        bond = before_bonds[key]
        events.append({"kind": "bond_broken", "rule_id": bond.rule_id, "location": [bond.x, bond.y],
                       "particle_ids": [bond.left_id, bond.right_id], "stored_energy_before": bond.stored_energy})
    before_particles = {item.particle_id: item for item in before.particles}
    for item in after.particles:
        previous = before_particles[item.particle_id]
        if (previous.x, previous.y) != (item.x, item.y):
            events.append({"kind": "particle_moved", "particle_id": item.particle_id,
                           "from": [previous.x, previous.y], "to": [item.x, item.y]})
        if previous.kinetic_energy != item.kinetic_energy:
            events.append({"kind": "particle_kinetic_changed", "particle_id": item.particle_id,
                           "before": previous.kinetic_energy, "after": item.kinetic_energy})
    before_heat = {(item.x, item.y): item.energy for item in before.heat}
    after_heat = {(item.x, item.y): item.energy for item in after.heat}
    for point in sorted(set(before_heat) | set(after_heat)):
        if before_heat.get(point, 0) != after_heat.get(point, 0):
            events.append({"kind": "local_heat_changed", "location": list(point),
                           "before": before_heat.get(point, 0), "after": after_heat.get(point, 0)})
    return tuple(events)


def forecast_world(spec: CausalWorldSpec, ticks: int | None = None) -> WorldForecast:
    horizon = min(spec.ticks, MAX_FORECAST_TICKS) if ticks is None else ticks
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 0 <= horizon <= MAX_FORECAST_TICKS:
        raise ValueError(f"forecast horizon must be from zero through {MAX_FORECAST_TICKS}")
    state = initial_causal_state(spec)
    initial_digest = state.digest
    steps = []
    for _ in range(horizon):
        before = state
        state = step_causal_world(spec, before)
        steps.append(CausalForecastStep(
            state.tick, before.digest, state.digest, explain_causal_transition(before, state),
            state.total_energy(), state.momentum(spec), tuple(state.material_counts().items()),
        ))
    if initial_causal_state(spec).digest != initial_digest:
        raise AssertionError("world forecast changed the supplied specification")
    return WorldForecast(spec.digest, "exact-read-only-a1-clone", build_rule_map(spec), initial_digest, tuple(steps))


def evaluate_forecast(forecast: WorldForecast, run: CausalRun) -> ForecastEvaluation:
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
        mismatches.append({"tick": tick, "predicted": predicted[tick], "actual": None, "reason": "run has no checkpoint"})
    return ForecastEvaluation(
        forecast.digest, run.digest, compared, tuple(matched), tuple(mismatches),
        forecast.spec_digest == run.spec_digest,
    )
