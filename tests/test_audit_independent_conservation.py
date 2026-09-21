"""The conservation recount must stay independent, and must catch a bad tally.

`step_environment_world` compares `conserved_resources()` before and after
each tick. Both readings come from the same method, so the check is blind to
an error that is the *same size on both sides* — a pool counted twice, a term
left out, a cell skipped. The world still reports "conserved" while the number
it reports is wrong.

That blind spot is narrower than it first looks, and the shape matters:

- an error that varies with the state (skipping a cell matter moves through)
  *is* caught by the kernel, because the miscount changes tick to tick
- an error that is constant across the run is invisible to it

So the fault injected below is a constant one, in a world with no phase
change to perturb it. That is the case the independent recount exists for.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from audit.independent_conservation import (
    LedgerError,
    check_snapshots,
    check_trace_conservation,
    read_parameters,
    recount,
)
from engine.deterministic import (
    PrivateTraceWriter,
    environment_kernel,
    load_environment_world_spec,
    trace_environment_run,
)

ROOT = Path(__file__).resolve().parents[1]
WORLDS = ROOT / "worlds"
AUDIT = ROOT / "audit"

# No water phase change and no mineral conversion, so a constant miscount
# stays constant and the kernel's before/after check cannot see it.
STATIC_WORLD = WORLDS / "deterministic_physical_flux_v4.json"

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


# --- independence -----------------------------------------------------------

def test_conservation_audit_imports_nothing_from_engine() -> None:
    offenders = []
    for path in sorted((AUDIT / "independent_conservation").rglob("*.py")):
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
    assert offenders == [], "the conservation audit must not depend on the engine: " + "; ".join(offenders)


# --- agreement on honest runs ----------------------------------------------

@pytest.mark.parametrize("world", ALL_WORLDS)
def test_every_world_conserves_under_an_independent_recount(tmp_path: Path, world: str) -> None:
    run_dir, document = _run(tmp_path, WORLDS / world)
    report = check_trace_conservation(run_dir, document)

    assert report.findings == []
    assert report.valid is True
    assert report.ticks_checked > 1
    assert report.kernel_tally_compared > 0, "the kernel's own tally should have been compared"


def test_recount_totals_match_the_kernels_own_tally(tmp_path: Path) -> None:
    """The two routes must agree on the actual numbers, not merely both pass."""
    spec = load_environment_world_spec(STATIC_WORLD)
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    run_dir, _ = _run(tmp_path, STATIC_WORLD)

    records = [json.loads(line) for line
               in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    commit = next(item for item in records if item["kind"] == "tick_commit")
    ledger = recount(commit["payload"]["full_snapshot"], read_parameters(document))

    assert ledger.water_total == commit["payload"]["conserved_resources"]["water"]
    assert (list(ledger.material_inventory)
            == list(commit["payload"]["conserved_resources"]["material_inventory"]))
    assert ledger.energy_accounted == commit["payload"]["energy_account"]["accounted"]


def test_particles_and_momentum_are_recounted(tmp_path: Path) -> None:
    """The v1 world carries particles, so the particle terms are exercised."""
    run_dir, document = _run(tmp_path, WORLDS / "deterministic_environment_v1.json")
    report = check_trace_conservation(run_dir, document)

    assert report.valid is True
    assert report.first_ledger is not None
    assert dict(report.first_ledger.particle_counts) == {0: 2}
    assert report.first_ledger.particle_counts == report.last_ledger.particle_counts


# --- the point of the exercise: catching what the kernel cannot -------------

def test_catches_a_constant_miscount_the_kernel_cannot_see(tmp_path: Path) -> None:
    """A tally that is wrong by a fixed amount passes the kernel's own check.

    `resource_totals` is patched to double the water it reports. The kernel
    compares that doubled figure against itself each tick, finds it unchanged,
    and completes the run reporting conservation. The independent recount
    reads the same snapshots and gets the true total, so the two disagree.
    """
    spec = load_environment_world_spec(STATIC_WORLD)
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    original = environment_kernel.EnvironmentState.resource_totals

    def doubling_water(self, solute_kinds, include_vapor=False):
        totals = original(self, solute_kinds, include_vapor)
        totals["water"] = totals["water"] * 2
        return totals

    run_dir = tmp_path / "faulty"
    try:
        environment_kernel.EnvironmentState.resource_totals = doubling_water
        writer = PrivateTraceWriter(run_dir, "faulty")
        final_state = trace_environment_run(spec, writer)  # kernel asserts each tick
        writer.close(spec.digest, final_state.digest)
    finally:
        environment_kernel.EnvironmentState.resource_totals = original

    report = check_trace_conservation(run_dir, document)
    assert report.valid is False
    assert {item.code for item in report.findings} == {"kernel_water_tally_differs"}
    assert all(item.quantity == "water" for item in report.findings)


def test_a_state_dependent_miscount_is_caught_by_the_kernel_itself(tmp_path: Path) -> None:
    """Documents the other half of the picture, so the blind spot is not overstated.

    Skipping a cell that matter flows through makes the miscount vary tick to
    tick, which the kernel's before/after comparison does detect. The
    independent recount is for constant errors, not a claim that the kernel
    checks nothing.
    """
    spec = load_environment_world_spec(WORLDS / "deterministic_open_water_cycle_v3.json")
    original = environment_kernel.EnvironmentState.resource_totals

    def skipping_first_cell(self, solute_kinds, include_vapor=False):
        cells = self.cells[1:]
        totals = {"water": sum(x.water for x in cells),
                  "mineral": sum(x.mineral for x in cells),
                  "solutes": [sum(x.solutes[k] for x in cells) for k in range(solute_kinds)]}
        if include_vapor:
            totals["vapor"] = sum(x.vapor for x in cells)
        return totals

    try:
        environment_kernel.EnvironmentState.resource_totals = skipping_first_cell
        writer = PrivateTraceWriter(tmp_path / "varying", "varying")
        with pytest.raises(AssertionError):
            trace_environment_run(spec, writer)
    finally:
        environment_kernel.EnvironmentState.resource_totals = original


# --- the recount on its own -------------------------------------------------

def test_recount_reads_parameters_from_the_spec_document() -> None:
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)

    assert parameters.solute_kinds == document["solute_kinds"]
    assert parameters.mineral_solute_kind == document["law"]["mineral_solute_kind"]
    assert parameters.vaporization_energy == document["law"]["vaporization_energy"]
    assert parameters.masses == {0: 1}
    assert parameters.counts_vapor is True
    assert parameters.folds_mineral_into_inventory is True


def test_recount_counts_latent_energy_in_vapor_and_dissolved_mineral() -> None:
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    snapshot = {
        "causal": {"particles": [], "heat": [{"x": 0, "y": 0, "energy": 5}], "bonds": [], "tick": 0},
        "cells": [{"x": 0, "y": 0, "water": 2, "vapor": 3, "mineral": 1, "solutes": [4, 0]}],
        "energy_supplied": 0,
        "energy_removed": 0,
    }
    ledger = recount(snapshot, parameters)

    # 5 heat + 4 dissolved x 1 + 3 vapor x 1
    assert ledger.energy_internal == 12
    assert ledger.water_total == 5           # liquid plus vapor
    assert ledger.material_inventory == (5, 0)  # dissolved 4 plus solid 1
    assert ledger.particle_counts == ()


def test_recount_folds_the_external_energy_ledger_into_the_accounted_total() -> None:
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    base = {
        "causal": {"particles": [], "heat": [{"x": 0, "y": 0, "energy": 10}], "bonds": [], "tick": 0},
        "cells": [],
        "energy_supplied": 4,
        "energy_removed": 1,
    }
    ledger = recount(base, parameters)

    assert ledger.energy_internal == 10
    assert ledger.energy_accounted == 10 + 1 - 4


def test_recount_counts_momentum_for_free_particles_and_whole_chains() -> None:
    """Free particles count individually; a chain counts once, at its full mass."""
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    snapshot = {
        "causal": {
            "particles": [
                {"particle_id": 1, "kind": 0, "x": 0, "y": 0, "direction": "E", "kinetic_energy": 3},
                {"particle_id": 2, "kind": 0, "x": 1, "y": 0, "direction": "N", "kinetic_energy": 5},
            ],
            "heat": [], "bonds": [], "tick": 0,
        },
        "cells": [], "energy_supplied": 0, "energy_removed": 0,
    }
    free = recount(snapshot, parameters)
    assert free.momentum == (3, -5)
    assert free.energy_internal == 8

    # A standing pair: neither member is moving, so nothing is carried.
    standing = json.loads(json.dumps(snapshot))
    for particle in standing["causal"]["particles"]:
        particle["kinetic_energy"] = 0
        particle["x"], particle["y"] = 0, 0
    standing["causal"]["bonds"] = [
        {"left_id": 1, "right_id": 2, "rule_id": 0, "stored_energy": 2, "x": 0, "y": 0}]
    held = recount(standing, parameters)
    assert held.momentum == (0, 0), "a standing chain carries no momentum"
    assert held.energy_internal == 2, "the bond still holds the energy it absorbed"

    # The same pair travelling: one member holds the velocity for both, and the
    # chain's momentum is that velocity carried by the mass of the whole body.
    moving = json.loads(json.dumps(standing))
    moving["causal"]["particles"][0]["kinetic_energy"] = 4
    moving["causal"]["particles"][0]["direction"] = "E"
    chain = recount(moving, parameters)
    assert chain.momentum == (8, 0), "two unit masses at speed 4"
    assert chain.energy_internal == 6, "motion plus the energy stored in the bond"


def test_recount_rejects_a_chain_that_records_motion_twice() -> None:
    """Two members each holding the velocity would double the chain's momentum."""
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    snapshot = {
        "causal": {
            "particles": [
                {"particle_id": 1, "kind": 0, "x": 0, "y": 0, "direction": "E", "kinetic_energy": 3},
                {"particle_id": 2, "kind": 0, "x": 0, "y": 0, "direction": "E", "kinetic_energy": 3},
            ],
            "heat": [],
            "bonds": [{"left_id": 1, "right_id": 2, "rule_id": 0,
                       "stored_energy": 0, "x": 0, "y": 0}],
            "tick": 0,
        },
        "cells": [], "energy_supplied": 0, "energy_removed": 0,
    }
    with pytest.raises(LedgerError):
        recount(snapshot, parameters)


def test_recount_rejects_a_direction_it_does_not_know() -> None:
    """An unknown code must be an error, not a silently skipped particle."""
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    snapshot = {
        "causal": {"particles": [{"particle_id": 1, "kind": 0, "x": 0, "y": 0,
                                  "direction": "north", "kinetic_energy": 1}],
                   "heat": [], "bonds": [], "tick": 0},
        "cells": [], "energy_supplied": 0, "energy_removed": 0,
    }
    with pytest.raises(LedgerError):
        recount(snapshot, parameters)


def test_recount_rejects_non_integer_quantities() -> None:
    """The world is integer-only, so a float is a finding rather than a value."""
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    snapshot = {
        "causal": {"particles": [], "heat": [{"x": 0, "y": 0, "energy": 1.5}], "bonds": [], "tick": 0},
        "cells": [], "energy_supplied": 0, "energy_removed": 0,
    }
    with pytest.raises(LedgerError):
        recount(snapshot, parameters)


def test_check_snapshots_reports_each_quantity_that_moved() -> None:
    document = json.loads(STATIC_WORLD.read_text(encoding="utf-8"))
    parameters = read_parameters(document)
    first = {
        "causal": {"particles": [], "heat": [{"x": 0, "y": 0, "energy": 4}], "bonds": [], "tick": 0},
        "cells": [{"x": 0, "y": 0, "water": 2, "vapor": 0, "mineral": 0, "solutes": [0, 0]}],
        "energy_supplied": 0, "energy_removed": 0,
    }
    second = json.loads(json.dumps(first))
    second["causal"]["heat"][0]["energy"] = 9      # energy appears
    second["cells"][0]["water"] = 1                # water disappears

    report = check_snapshots([(0, first, {}), (1, second, {})], parameters, "synthetic")
    codes = {item.code for item in report.findings}

    assert report.valid is False
    assert {"energy_not_conserved", "water_not_conserved"} <= codes
    assert all(item.tick == 1 for item in report.findings)
