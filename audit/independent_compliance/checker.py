"""Check that a recorded run obeyed the rules its world declared.

Conservation and trace integrity both pass on a run where matter moved by an
illegal route. Water that crosses a blocked edge, jumps to a cell it never
touches, or moves more in one step than the declared limit allows, leaves
every total unchanged and every hash consistent.

This checks the routes. For each recorded stage it asks what the declared
rules permit at that stage, and reports any change that falls outside.

The stage name in the trace says which rules apply:

    causal                     particles and bonds; cells must not change
    horizontal_*, vertical_*   transport along that phase's cell pairs only
    external_energy            heat only, at declared boundaries, by declared amounts
    mineral_conversion         mineral <-> solute in place, paid for in local heat
    water_phase_change         water <-> vapor in place, paid for in local heat

Findings are collected rather than raised: one pass reports everything it can
see, so a systematic violation shows up as a pattern rather than a first hit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Any, Mapping

from .field import FieldError, FieldView, changed_points, read_field
from .rules import RuleError, WorldRules, read_rules

_TRANSPORT_CHANNELS = ("heat", "water", "vapor")


@dataclass
class ComplianceFinding:
    code: str
    detail: str
    tick: int | None = None
    phase: str | None = None
    point: tuple[int, int] | None = None

    def canonical(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail, "phase": self.phase,
                "point": list(self.point) if self.point else None, "tick": self.tick}


@dataclass
class ComplianceReport:
    source: str
    stages_checked: int = 0
    transport_stages: int = 0
    findings: list[ComplianceFinding] = dataclass_field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.findings

    def canonical(self) -> dict[str, Any]:
        return {"findings": [item.canonical() for item in self.findings],
                "source": self.source,
                "stages_checked": self.stages_checked,
                "transport_stages": self.transport_stages,
                "valid": self.valid}


def _note(report: ComplianceReport, code: str, detail: str,
          tick: int | None, phase: str | None,
          point: tuple[int, int] | None = None) -> None:
    report.findings.append(ComplianceFinding(code, detail, tick, phase, point))


def _check_causal_stage(report: ComplianceReport, rules: WorldRules,
                        before: FieldView, after: FieldView, tick: int | None) -> None:
    """The causal stage advances particles, bonds and the heat they carry.

    Heat lives in the causal world alongside the particles, so this stage
    legitimately redistributes it. What it must not touch is the environment
    fields — water, vapour, mineral and solutes belong to transport and
    conversion.
    """
    for point in set(before.water) | set(after.water) | set(before.mineral) | set(after.mineral):
        for name in ("water", "vapor", "mineral"):
            if before.channel(name, point) != after.channel(name, point):
                _note(report, "causal_stage_touched_environment",
                      f"the causal stage changed {name}, which only transport and "
                      f"conversion stages may do",
                      tick, "causal", point)
        if any(before.solute(point, k) != after.solute(point, k)
               for k in range(rules.solute_kinds)):
            _note(report, "causal_stage_touched_environment",
                  "the causal stage changed dissolved solutes, which only transport "
                  "and conversion stages may do",
                  tick, "causal", point)
        if before.elevation.get(point, 0) != after.elevation.get(point, 0):
            _note(report, "causal_stage_touched_environment",
                  "the causal stage changed terrain elevation", tick, "causal", point)


def _check_transport_stage(report: ComplianceReport, rules: WorldRules, before: FieldView,
                           after: FieldView, tick: int | None, phase: str) -> None:
    """Transport may only move quantities between the pairs this phase names."""
    try:
        pairs = list(rules.phase_pairs(phase))
    except RuleError as error:
        _note(report, "unknown_phase", str(error), tick, phase)
        return

    allowed: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for first, second in pairs:
        if rules.is_blocked(first, second):
            continue
        allowed.setdefault(first, set()).add(second)
        allowed.setdefault(second, set()).add(first)

    for point in changed_points(before, after, rules.solute_kinds):
        partners = allowed.get(point)
        if not partners:
            _note(report, "transport_outside_phase_pairs",
                  f"cell changed during {phase}, which does not pair it with any cell "
                  f"(a blocked edge or a cell this phase should not touch)",
                  tick, phase, point)
            continue
        for partner in partners:
            if not rules.neighbours(point) >= {partner}:
                _note(report, "transport_between_non_neighbours",
                      f"phase pairs {point} with {partner}, which is not an adjacent cell",
                      tick, phase, point)

    # A pair's exchange must balance: what one side loses the other gains.
    for first, second in pairs:
        blocked = rules.is_blocked(first, second)
        for channel in _TRANSPORT_CHANNELS:
            if channel == "vapor" and not rules.has_vapor:
                continue
            left_change = after.channel(channel, first) - before.channel(channel, first)
            right_change = after.channel(channel, second) - before.channel(channel, second)
            if blocked and (left_change or right_change):
                _note(report, "blocked_edge_crossed",
                      f"{channel} moved across the blocked edge {first}-{second} "
                      f"({left_change:+d}/{right_change:+d})",
                      tick, phase, first)
                continue
            if left_change == 0 and right_change == 0:
                continue
            if left_change != -right_change:
                # Another pair in the same phase may also touch these cells only
                # if the grid is 2 wide, where both neighbours are the same cell.
                if rules.width > 2 and rules.height > 2:
                    _note(report, "transport_did_not_balance",
                          f"{channel} across {first}-{second} changed "
                          f"{left_change:+d}/{right_change:+d}, which does not balance",
                          tick, phase, first)
                continue
            moved = abs(left_change)
            limit = rules.transfer_limit(channel)
            if limit and moved > limit:
                _note(report, "transfer_limit_exceeded",
                      f"{channel} moved {moved} across {first}-{second}, "
                      f"above the declared limit {limit}",
                      tick, phase, first)
            if channel in ("water", "vapor"):
                source, amount = (first, before.channel(channel, first)) if left_change < 0 \
                    else (second, before.channel(channel, second))
                if moved > amount:
                    _note(report, "moved_more_than_present",
                          f"{channel} moved {moved} out of {source}, which held {amount}",
                          tick, phase, source)

    for point in set(before.elevation) | set(after.elevation):
        if before.elevation.get(point, 0) != after.elevation.get(point, 0):
            _note(report, "elevation_changed",
                  "terrain elevation changed during transport", tick, phase, point)
        if before.mineral.get(point, 0) != after.mineral.get(point, 0):
            _note(report, "solid_mineral_moved",
                  "solid mineral changed during transport, which only conversion may do",
                  tick, phase, point)


def _check_external_energy_stage(report: ComplianceReport, rules: WorldRules, before: FieldView,
                                 after: FieldView, tick: int | None) -> None:
    """Only declared boundaries may add or remove heat, by their declared amounts."""
    phase = "external_energy"
    for point in set(before.heat) | set(after.heat):
        change = after.heat.get(point, 0) - before.heat.get(point, 0)
        if change == 0:
            continue
        given = rules.energy_inputs.get(point, 0)
        taken = rules.energy_outputs.get(point, 0)
        if not given and not taken:
            _note(report, "energy_crossed_undeclared_boundary",
                  f"heat changed {change:+d} at a cell with no declared energy boundary",
                  tick, phase, point)
            continue
        if change > given:
            _note(report, "energy_input_above_declared",
                  f"heat rose {change:+d}, above the declared input {given}", tick, phase, point)
        if -change > taken:
            _note(report, "energy_output_above_declared",
                  f"heat fell {change:+d}, below the declared output -{taken}", tick, phase, point)

    supplied = after.energy_supplied - before.energy_supplied
    removed = after.energy_removed - before.energy_removed
    if supplied < 0 or removed < 0:
        _note(report, "energy_ledger_went_backwards",
              f"the external ledger moved supplied {supplied:+d}, removed {removed:+d}",
              tick, phase)
    total_input = sum(rules.energy_inputs.values())
    if supplied > total_input:
        _note(report, "energy_ledger_above_declared_input",
              f"ledger recorded {supplied} supplied, declared inputs total {total_input}",
              tick, phase)

    for point in set(before.water) | set(after.water):
        if (before.water.get(point, 0) != after.water.get(point, 0)
                or before.vapor.get(point, 0) != after.vapor.get(point, 0)):
            _note(report, "external_energy_stage_moved_matter",
                  "the external energy stage changed water or vapor", tick, phase, point)


def _check_mineral_stage(report: ComplianceReport, rules: WorldRules, before: FieldView,
                         after: FieldView, tick: int | None) -> None:
    """Mineral dissolves or precipitates in place, paid for in local heat."""
    phase = "mineral_conversion"
    kind = rules.mineral_solute_kind
    for point in set(before.mineral) | set(after.mineral):
        mineral_change = after.mineral.get(point, 0) - before.mineral.get(point, 0)
        solute_change = after.solute(point, kind) - before.solute(point, kind)
        if mineral_change == 0 and solute_change == 0:
            continue
        if not rules.has_mineral_conversion or rules.max_mineral_conversion == 0:
            _note(report, "mineral_converted_when_disabled",
                  f"mineral moved {mineral_change:+d} in a world that declares no conversion",
                  tick, phase, point)
            continue
        if mineral_change != -solute_change:
            _note(report, "mineral_conversion_unbalanced",
                  f"solid moved {mineral_change:+d} but dissolved moved {solute_change:+d}",
                  tick, phase, point)
            continue
        amount = abs(mineral_change)
        if amount > rules.max_mineral_conversion:
            _note(report, "mineral_conversion_above_limit",
                  f"converted {amount}, above the declared limit {rules.max_mineral_conversion}",
                  tick, phase, point)
        if before.water.get(point, 0) == 0:
            _note(report, "mineral_converted_without_water",
                  "mineral converted in a cell holding no water", tick, phase, point)

        heat_change = after.heat.get(point, 0) - before.heat.get(point, 0)
        expected = -amount * rules.mineral_conversion_energy if solute_change > 0 \
            else amount * rules.mineral_conversion_energy
        if heat_change != expected:
            _note(report, "mineral_conversion_energy_mismatch",
                  f"converting {amount} should change local heat {expected:+d}, "
                  f"but it changed {heat_change:+d}",
                  tick, phase, point)

        if solute_change > 0 and before.heat.get(point, 0) < rules.dissolve_heat_at_least:
            _note(report, "dissolved_below_declared_heat",
                  f"dissolved at local heat {before.heat.get(point, 0)}, "
                  f"below the declared threshold {rules.dissolve_heat_at_least}",
                  tick, phase, point)
        if solute_change < 0 and before.heat.get(point, 0) > rules.precipitate_heat_at_most:
            _note(report, "precipitated_above_declared_heat",
                  f"precipitated at local heat {before.heat.get(point, 0)}, "
                  f"above the declared threshold {rules.precipitate_heat_at_most}",
                  tick, phase, point)

    for point in set(before.water) | set(after.water):
        if before.water.get(point, 0) != after.water.get(point, 0):
            _note(report, "mineral_stage_moved_water",
                  "the mineral stage changed liquid water", tick, phase, point)


def _check_phase_change_stage(report: ComplianceReport, rules: WorldRules, before: FieldView,
                              after: FieldView, tick: int | None) -> None:
    """Water becomes vapour in place, paid for in local heat."""
    phase = "water_phase_change"
    for point in set(before.water) | set(after.water) | set(before.vapor) | set(after.vapor):
        water_change = after.water.get(point, 0) - before.water.get(point, 0)
        vapor_change = after.vapor.get(point, 0) - before.vapor.get(point, 0)
        if water_change == 0 and vapor_change == 0:
            continue
        if not rules.has_vapor or rules.max_water_phase_change == 0:
            _note(report, "phase_changed_when_disabled",
                  f"water moved {water_change:+d} in a world that declares no phase change",
                  tick, phase, point)
            continue
        if water_change != -vapor_change:
            _note(report, "phase_change_unbalanced",
                  f"water moved {water_change:+d} but vapour moved {vapor_change:+d}",
                  tick, phase, point)
            continue
        amount = abs(water_change)
        if amount > rules.max_water_phase_change:
            _note(report, "phase_change_above_limit",
                  f"converted {amount}, above the declared limit {rules.max_water_phase_change}",
                  tick, phase, point)

        heat_change = after.heat.get(point, 0) - before.heat.get(point, 0)
        expected = -amount * rules.vaporization_energy if vapor_change > 0 \
            else amount * rules.vaporization_energy
        if heat_change != expected:
            _note(report, "phase_change_energy_mismatch",
                  f"converting {amount} should change local heat {expected:+d}, "
                  f"but it changed {heat_change:+d}",
                  tick, phase, point)

        if vapor_change > 0 and before.heat.get(point, 0) < rules.evaporation_heat_at_least:
            _note(report, "evaporated_below_declared_heat",
                  f"evaporated at local heat {before.heat.get(point, 0)}, "
                  f"below the declared threshold {rules.evaporation_heat_at_least}",
                  tick, phase, point)
        if vapor_change < 0 and before.heat.get(point, 0) > rules.condensation_heat_at_most:
            _note(report, "condensed_above_declared_heat",
                  f"condensed at local heat {before.heat.get(point, 0)}, "
                  f"above the declared threshold {rules.condensation_heat_at_most}",
                  tick, phase, point)


_STAGE_CHECKS = {
    "external_energy": _check_external_energy_stage,
    "mineral_conversion": _check_mineral_stage,
    "water_phase_change": _check_phase_change_stage,
}


def check_stage(report: ComplianceReport, rules: WorldRules, before: FieldView, after: FieldView,
                tick: int | None, phase: str | None) -> None:
    """Apply whichever rules govern the named stage."""
    report.stages_checked += 1
    if phase == "causal":
        _check_causal_stage(report, rules, before, after, tick)
    elif phase in _STAGE_CHECKS:
        _STAGE_CHECKS[phase](report, rules, before, after, tick)
    elif phase and (phase.startswith("horizontal") or phase.startswith("vertical")):
        report.transport_stages += 1
        _check_transport_stage(report, rules, before, after, tick, phase)
    else:
        _note(report, "unrecognised_stage",
              f"the trace records a stage named {phase!r}, which has no declared rules",
              tick, phase)


def check_trace_compliance(run_dir: Path, spec: Mapping[str, Any]) -> ComplianceReport:
    """Replay a recorded trace stage by stage and check every change was permitted."""
    run_dir = Path(run_dir)
    report = ComplianceReport(source=str(run_dir))

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        _note(report, "manifest_missing", f"no manifest.json in {run_dir}", None, None)
        return report
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records_path = run_dir / manifest.get("records_file", "records.jsonl")
    if not records_path.is_file():
        _note(report, "records_missing", f"no {records_path.name}", None, None)
        return report

    try:
        rules = read_rules(spec)
    except RuleError as error:
        _note(report, "spec_unreadable", str(error), None, None)
        return report

    declared = set(rules.phase_order)
    current: FieldView | None = None
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("stream") != "A":
            continue
        payload = raw.get("payload") or {}
        kind, tick, phase = raw.get("kind"), raw.get("tick"), raw.get("phase")

        try:
            if kind in ("run_start", "tick_start", "tick_commit"):
                snapshot = payload.get("full_snapshot")
                if isinstance(snapshot, Mapping):
                    current = read_field(snapshot, rules.solute_kinds)
                continue
            if kind != "stage_commit":
                continue
            after_snapshot = payload.get("after_snapshot")
            if not isinstance(after_snapshot, Mapping):
                _note(report, "stage_without_snapshot",
                      "stage commit carries no after_snapshot", tick, phase)
                continue
            after = read_field(after_snapshot, rules.solute_kinds)
        except FieldError as error:
            _note(report, "snapshot_unreadable", str(error), tick, phase)
            return report

        if current is None:
            _note(report, "stage_without_predecessor",
                  "a stage was recorded before any snapshot", tick, phase)
            current = after
            continue

        if (phase and phase not in declared
                and phase not in _STAGE_CHECKS and phase != "causal"):
            _note(report, "phase_not_declared",
                  f"the trace records transport phase {phase!r}, which the world's "
                  f"phase_order does not declare: {list(rules.phase_order)}",
                  tick, phase)

        check_stage(report, rules, current, after, tick, phase)
        current = after

    if report.stages_checked == 0:
        _note(report, "no_stages", "trace records no A-stream stages", None, None)
    return report
