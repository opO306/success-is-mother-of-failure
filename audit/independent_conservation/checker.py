"""Check conservation across a recorded run, without the kernel's own tally.

`step_environment_world` asserts that `conserved_resources()` and
`energy_account()` agree before and after each tick. Both sides of that
comparison come from the same method, so it catches a kernel that moves
matter but not a tally that measures it wrongly.

Here every tick snapshot in the trace is recounted from raw numbers by
`ledger.recount` and compared tick to tick. A tally that skips a cell or
double-counts a pool disagrees with this recount and is reported.

Two distinct questions are answered separately, because they fail for
different reasons:

  conservation  did the totals stay put from one tick to the next?
  agreement     does the kernel's own recorded tally match this recount?

A run can conserve matter while the kernel mis-reports how much there is, and
the second question is the one the kernel cannot ask itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .ledger import Ledger, LedgerError, WorldParameters, read_parameters, recount


@dataclass
class ConservationFinding:
    code: str
    detail: str
    tick: int | None = None
    quantity: str | None = None

    def canonical(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail,
                "quantity": self.quantity, "tick": self.tick}


@dataclass
class ConservationReport:
    source: str
    ticks_checked: int = 0
    first_ledger: Ledger | None = None
    last_ledger: Ledger | None = None
    findings: list[ConservationFinding] = field(default_factory=list)
    kernel_tally_compared: int = 0

    @property
    def valid(self) -> bool:
        return not self.findings

    def canonical(self) -> dict[str, Any]:
        return {"findings": [item.canonical() for item in self.findings],
                "first_ledger": self.first_ledger.canonical() if self.first_ledger else None,
                "kernel_tally_compared": self.kernel_tally_compared,
                "last_ledger": self.last_ledger.canonical() if self.last_ledger else None,
                "source": self.source,
                "ticks_checked": self.ticks_checked,
                "valid": self.valid}


def _compare(report: ConservationReport, previous: Ledger, current: Ledger, tick: int) -> None:
    """Every conserved quantity must survive a tick unchanged."""
    if previous.energy_accounted != current.energy_accounted:
        report.findings.append(ConservationFinding(
            "energy_not_conserved",
            f"accounted energy moved {previous.energy_accounted} -> {current.energy_accounted}",
            tick=tick, quantity="energy"))
    if previous.water_total != current.water_total:
        report.findings.append(ConservationFinding(
            "water_not_conserved",
            f"water plus vapor moved {previous.water_total} -> {current.water_total}",
            tick=tick, quantity="water"))
    if previous.material_inventory != current.material_inventory:
        report.findings.append(ConservationFinding(
            "inventory_not_conserved",
            f"material inventory moved {list(previous.material_inventory)} -> "
            f"{list(current.material_inventory)}",
            tick=tick, quantity="material_inventory"))
    if previous.particle_counts != current.particle_counts:
        report.findings.append(ConservationFinding(
            "particle_counts_not_conserved",
            f"particle counts moved {dict(previous.particle_counts)} -> "
            f"{dict(current.particle_counts)}",
            tick=tick, quantity="particle_counts"))


def _compare_kernel_tally(report: ConservationReport, payload: Mapping[str, Any],
                          ledger: Ledger, tick: int, parameters: WorldParameters) -> None:
    """Hold the kernel's own recorded tally against this recount."""
    recorded = payload.get("conserved_resources")
    if isinstance(recorded, Mapping):
        report.kernel_tally_compared += 1
        if parameters.folds_mineral_into_inventory:
            if "water" in recorded and recorded["water"] != ledger.water_total:
                report.findings.append(ConservationFinding(
                    "kernel_water_tally_differs",
                    f"kernel recorded {recorded['water']}, independent recount is {ledger.water_total}",
                    tick=tick, quantity="water"))
            if "material_inventory" in recorded:
                if list(recorded["material_inventory"]) != list(ledger.material_inventory):
                    report.findings.append(ConservationFinding(
                        "kernel_inventory_tally_differs",
                        f"kernel recorded {recorded['material_inventory']}, "
                        f"independent recount is {list(ledger.material_inventory)}",
                        tick=tick, quantity="material_inventory"))

    account = payload.get("energy_account")
    if isinstance(account, Mapping) and "accounted" in account:
        report.kernel_tally_compared += 1
        if account["accounted"] != ledger.energy_accounted:
            report.findings.append(ConservationFinding(
                "kernel_energy_tally_differs",
                f"kernel recorded {account['accounted']}, "
                f"independent recount is {ledger.energy_accounted}",
                tick=tick, quantity="energy"))


def check_snapshots(snapshots: list[tuple[int, Mapping[str, Any], Mapping[str, Any]]],
                    parameters: WorldParameters, source: str) -> ConservationReport:
    """Recount and compare an ordered list of `(tick, snapshot, payload)`."""
    report = ConservationReport(source=source)
    previous: Ledger | None = None
    for tick, snapshot, payload in snapshots:
        try:
            ledger = recount(snapshot, parameters)
        except LedgerError as error:
            report.findings.append(ConservationFinding(
                "snapshot_unreadable", str(error), tick=tick))
            return report
        if report.first_ledger is None:
            report.first_ledger = ledger
        report.last_ledger = ledger
        report.ticks_checked += 1
        _compare_kernel_tally(report, payload, ledger, tick, parameters)
        if previous is not None:
            _compare(report, previous, ledger, tick)
        previous = ledger
    return report


def check_trace_conservation(run_dir: Path, spec: Mapping[str, Any]) -> ConservationReport:
    """Recount every tick of a recorded trace and check nothing moved.

    `spec` is the world specification document as JSON — the same file the run
    was launched from. It supplies masses and latent-energy constants, which a
    snapshot alone does not carry.
    """
    run_dir = Path(run_dir)
    report = ConservationReport(source=str(run_dir))

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        report.findings.append(ConservationFinding("manifest_missing", f"no manifest.json in {run_dir}"))
        return report
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records_path = run_dir / manifest.get("records_file", "records.jsonl")
    if not records_path.is_file():
        report.findings.append(ConservationFinding("records_missing", f"no {records_path.name}"))
        return report

    try:
        parameters = read_parameters(spec)
    except LedgerError as error:
        report.findings.append(ConservationFinding("spec_unreadable", str(error)))
        return report

    snapshots: list[tuple[int, Mapping[str, Any], Mapping[str, Any]]] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("stream") != "A":
            continue
        if raw.get("kind") not in ("run_start", "tick_commit"):
            continue
        payload = raw.get("payload") or {}
        snapshot = payload.get("full_snapshot")
        if isinstance(snapshot, Mapping):
            snapshots.append((raw.get("tick"), snapshot, payload))

    if not snapshots:
        report.findings.append(ConservationFinding(
            "no_snapshots", "trace carries no A-stream tick snapshots"))
        return report

    checked = check_snapshots(snapshots, parameters, str(run_dir))
    checked.source = str(run_dir)
    return checked
