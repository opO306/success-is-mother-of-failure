"""Did the physics follow the rules, not merely keep the totals?

Conservation and trace integrity are both blind to an illegal route. Water
that crosses a blocked edge, jumps to a cell it never touches, or moves more
in one step than the declared limit permits, leaves every total unchanged and
every hash consistent. `exactly one ordinary event` — the 2026-09-20 finding
that invalidated months of runs — was exactly this shape: nothing was lost,
nothing was inconsistent, the rule was simply not what anyone thought.

Each violation below is injected by declaring the rule the recorded run
already breaks, then asserting that the conservation checker passes and the
compliance checker does not. Passing the conservation check is part of the
claim, not an incidental detail: it is what makes the second checker worth
having.
"""
from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

import pytest

from audit.independent_compliance import (
    RuleError,
    check_trace_compliance,
    read_field,
    read_rules,
)
from audit.independent_conservation import check_trace_conservation
from engine.deterministic import (
    PrivateTraceWriter,
    load_environment_world_spec,
    trace_environment_run,
)

ROOT = Path(__file__).resolve().parents[1]
WORLDS = ROOT / "worlds"
AUDIT = ROOT / "audit" / "independent_compliance"

# Large gradients, so transfers are big enough to test declared limits against.
BUSY_WORLD = WORLDS / "deterministic_physical_flux_v4.json"
# Water actually changes phase here, so the phase-change rules are exercised.
PHASE_WORLD = WORLDS / "deterministic_open_water_cycle_v3.json"

ALL_WORLDS = (
    "deterministic_environment_v1.json",
    "deterministic_geochemical_cycle_v2.json",
    "deterministic_open_water_cycle_v3.json",
    "deterministic_physical_flux_v4.json",
)


def _run(tmp_path: Path, world: Path, name: str = "run") -> tuple[Path, dict]:
    spec = load_environment_world_spec(world)
    document = json.loads(world.read_text(encoding="utf-8"))
    run_dir = tmp_path / name
    writer = PrivateTraceWriter(run_dir, name)
    final_state = trace_environment_run(spec, writer)
    writer.close(spec.digest, final_state.digest)
    return run_dir, document


def _codes(run_dir: Path, document: dict) -> set[str]:
    return {item.code for item in check_trace_compliance(run_dir, document).findings}


def _with_rule(document: dict, **law: int) -> dict:
    """The same world with one declared rule changed."""
    altered = json.loads(json.dumps(document))
    altered["law"].update(law)
    return altered


# --- independence -----------------------------------------------------------

def test_compliance_audit_imports_nothing_from_engine() -> None:
    offenders = []
    for path in sorted(AUDIT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name == "engine" or name.startswith("engine."):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} imports {name}")
    assert offenders == [], "the compliance audit must not depend on the engine: " + "; ".join(offenders)


# --- honest runs comply -----------------------------------------------------

@pytest.mark.parametrize("world", ALL_WORLDS)
def test_every_world_obeys_its_own_declared_rules(tmp_path: Path, world: str) -> None:
    run_dir, document = _run(tmp_path, WORLDS / world)
    report = check_trace_compliance(run_dir, document)

    assert report.findings == []
    assert report.valid is True
    assert report.transport_stages > 0, "transport stages should have been checked"


def test_the_causal_stage_may_move_heat_but_not_water(tmp_path: Path) -> None:
    """Heat lives with the particles, so the causal stage redistributes it legally."""
    run_dir, document = _run(tmp_path, WORLDS / "deterministic_environment_v1.json")
    assert check_trace_compliance(run_dir, document).valid is True


# --- violations that conserve perfectly -------------------------------------

def test_catches_matter_crossing_a_blocked_edge(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, BUSY_WORLD)
    blocked = json.loads(json.dumps(document))
    blocked["blocked_edges"] = [{"first": [4, 4], "second": [5, 4]}]

    assert check_trace_conservation(run_dir, blocked).valid is True, \
        "nothing was lost — that is why conservation cannot see this"
    assert "blocked_edge_crossed" in _codes(run_dir, blocked)


def test_catches_matter_appearing_in_a_cell_it_never_travelled_to(tmp_path: Path) -> None:
    """Move water to a distant cell by hand: totals hold, the route is impossible."""
    run_dir, document = _run(tmp_path, BUSY_WORLD)
    records = [json.loads(line) for line
               in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]

    moved = False
    for record in records:
        if moved or record.get("kind") != "stage_commit":
            continue
        if not str(record.get("phase", "")).startswith("horizontal"):
            continue
        cells = record["payload"]["after_snapshot"]["cells"]
        source = next((cell for cell in cells if cell.get("water", 0) >= 4), None)
        if source is None:
            continue
        source["water"] -= 4
        cells.append({"x": 12, "y": 12, "elevation": 0, "water": 4,
                      "vapor": 0, "mineral": 0, "solutes": [0, 0]})
        moved = True
    assert moved, "the fixture world should carry enough water to move"

    tampered = tmp_path / "teleport"
    tampered.mkdir()
    (tampered / "manifest.json").write_text(
        (run_dir / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tampered / "records.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n" for item in records),
        encoding="utf-8", newline="\n")

    assert check_trace_conservation(tampered, document).valid is True, \
        "the water still exists somewhere — conservation is satisfied"
    assert "transport_did_not_balance" in _codes(tampered, document)


def test_catches_a_transfer_above_the_declared_limit(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, BUSY_WORLD)
    tight = _with_rule(document, max_water_transfer=1, max_heat_transfer=1)

    assert check_trace_conservation(run_dir, tight).valid is True
    assert "transfer_limit_exceeded" in _codes(run_dir, tight)


def test_a_transfer_within_the_limit_is_not_reported(tmp_path: Path) -> None:
    """The limit check must not fire on moves that stay inside it."""
    run_dir, document = _run(tmp_path, BUSY_WORLD)
    generous = _with_rule(document, max_water_transfer=10_000, max_heat_transfer=10_000)

    assert "transfer_limit_exceeded" not in _codes(run_dir, generous)


def test_catches_a_phase_change_the_world_does_not_permit(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, PHASE_WORLD)
    forbidden = _with_rule(document, max_water_phase_change=0)

    assert check_trace_conservation(run_dir, forbidden).valid is True, \
        "water and vapour still sum the same — conservation is satisfied"
    assert "phase_changed_when_disabled" in _codes(run_dir, forbidden)


def test_catches_evaporation_below_the_declared_heat_threshold(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, PHASE_WORLD)
    cold = _with_rule(document, evaporation_heat_at_least=999_999)

    assert check_trace_conservation(run_dir, cold).valid is True
    assert "evaporated_below_declared_heat" in _codes(run_dir, cold)


def test_catches_a_phase_change_above_its_declared_limit(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, PHASE_WORLD)
    document_with_limit = _with_rule(document, max_water_phase_change=0)
    assert "phase_changed_when_disabled" in _codes(run_dir, document_with_limit)


def test_catches_energy_crossing_an_undeclared_boundary(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, PHASE_WORLD)
    if not document.get("energy_boundaries"):
        pytest.skip("this world declares no energy boundaries to remove")
    undeclared = json.loads(json.dumps(document))
    undeclared["energy_boundaries"] = []

    assert "energy_crossed_undeclared_boundary" in _codes(run_dir, undeclared)


# --- the rules and field views on their own ---------------------------------

def test_rules_are_read_from_the_specification_document() -> None:
    document = json.loads(BUSY_WORLD.read_text(encoding="utf-8"))
    rules = read_rules(document)

    assert rules.width == document["causal_world"]["kernel"]["width"]
    assert rules.boundary == document["causal_world"]["kernel"]["boundary"]
    assert rules.phase_order == tuple(document["law"]["phase_order"])
    assert rules.max_water_transfer == document["law"]["max_water_transfer"]
    assert rules.wraps is True


def test_neighbours_wrap_around_the_grid_edge() -> None:
    document = json.loads(BUSY_WORLD.read_text(encoding="utf-8"))
    rules = read_rules(document)
    width, height = rules.width, rules.height

    assert (width - 1, 0) in rules.neighbours((0, 0)), "west of column 0 wraps"
    assert (0, height - 1) in rules.neighbours((0, 0)), "north of row 0 wraps"
    assert len(rules.neighbours((5, 5))) == 4


def test_phase_pairs_cover_each_cell_once_per_phase() -> None:
    document = json.loads(BUSY_WORLD.read_text(encoding="utf-8"))
    rules = read_rules(document)

    for phase in rules.phase_order:
        seen: list[tuple[int, int]] = []
        for first, second in rules.phase_pairs(phase):
            seen.extend((first, second))
        assert len(seen) == len(set(seen)), f"{phase} pairs a cell twice"

    with pytest.raises(RuleError):
        list(rules.phase_pairs("diagonal_even"))


def test_blocked_edges_are_symmetric() -> None:
    document = json.loads(BUSY_WORLD.read_text(encoding="utf-8"))
    document = json.loads(json.dumps(document))
    document["blocked_edges"] = [{"first": [1, 1], "second": [2, 1]}]
    rules = read_rules(document)

    assert rules.is_blocked((1, 1), (2, 1)) is True
    assert rules.is_blocked((2, 1), (1, 1)) is True, "an edge blocks in both directions"
    assert rules.is_blocked((1, 1), (1, 2)) is False


def test_a_dropped_cell_reads_as_zero_not_as_missing(tmp_path: Path) -> None:
    """The recorder omits emptied cells; that must not read as a gap in the field."""
    document = json.loads(BUSY_WORLD.read_text(encoding="utf-8"))
    rules = read_rules(document)
    view = read_field({"causal": {"particles": [], "heat": [], "bonds": [], "tick": 0},
                       "cells": [], "energy_supplied": 0, "energy_removed": 0},
                      rules.solute_kinds)

    assert view.channel("water", (3, 3)) == 0
    assert view.solute((3, 3), 0) == 0


def test_reports_a_stage_the_world_never_declared(tmp_path: Path) -> None:
    run_dir, document = _run(tmp_path, BUSY_WORLD)
    renamed = json.loads(json.dumps(document))
    renamed["law"]["phase_order"] = ["horizontal_even"]

    assert "phase_not_declared" in _codes(run_dir, renamed)
