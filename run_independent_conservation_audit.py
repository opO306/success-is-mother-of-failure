"""Recount conservation independently of the kernel's own tally.

Usage:
    python run_independent_conservation_audit.py --worlds
    python run_independent_conservation_audit.py --vault
    python run_independent_conservation_audit.py <run_dir> --spec <spec.json>

`--worlds` runs each world in `worlds/`, traces it, and recounts every tick.
`--vault` audits stored traces in the D: vault that kept their `spec.json`
alongside them — the recount needs masses and latent-energy constants, which
a snapshot alone does not carry.

Raw vault contents are never printed: only paths, totals and findings.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from audit.independent_conservation import ConservationReport, check_trace_conservation

VAULT = Path("D:/KiroCrewTraceVault/success-is-mother-of-failure")
WORLDS = Path(__file__).resolve().parent / "worlds"


def audit_stored(run_dir: Path, spec_path: Path) -> ConservationReport:
    return check_trace_conservation(run_dir, json.loads(spec_path.read_text(encoding="utf-8")))


def audit_world(world: Path, workspace: Path) -> ConservationReport:
    """Trace a world fresh, then recount it."""
    from engine.deterministic import (
        PrivateTraceWriter,
        load_environment_world_spec,
        trace_environment_run,
    )

    spec = load_environment_world_spec(world)
    run_dir = workspace / world.stem
    writer = PrivateTraceWriter(run_dir, world.stem)
    final_state = trace_environment_run(spec, writer)
    writer.close(spec.digest, final_state.digest)
    report = check_trace_conservation(run_dir, json.loads(world.read_text(encoding="utf-8")))
    report.source = str(world)
    return report


def describe(report: ConservationReport) -> str:
    head = "OK " if report.valid else "!! "
    lines = [f"{head}{report.source}"]
    ledger = report.first_ledger
    if ledger is not None:
        lines.append(f"    ticks       : {report.ticks_checked}"
                     f"  (kernel tally compared {report.kernel_tally_compared}x)")
        lines.append(f"    energy      : {ledger.energy_accounted}"
                     f"   (internal {ledger.energy_internal},"
                     f" supplied {ledger.energy_supplied}, removed {ledger.energy_removed})")
        lines.append(f"    water+vapor : {ledger.water_total}")
        lines.append(f"    inventory   : {list(ledger.material_inventory)}")
        if ledger.particle_counts:
            lines.append(f"    particles   : {dict(ledger.particle_counts)}"
                         f"   momentum {ledger.momentum}")
    for finding in report.findings[:6]:
        lines.append(f"    - [{finding.code}] tick={finding.tick}"
                     f" {finding.quantity}: {finding.detail[:80]}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="*", type=Path)
    parser.add_argument("--spec", type=Path, help="world spec for the given run directories")
    parser.add_argument("--worlds", action="store_true", help="trace and audit every world spec")
    parser.add_argument("--vault", action="store_true", help="audit vault traces that kept a spec.json")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    arguments = parser.parse_args(argv)

    reports: list[ConservationReport] = []
    workspace = Path(tempfile.mkdtemp(prefix="conservation-audit-"))

    if arguments.worlds:
        for world in sorted(WORLDS.glob("*.json")):
            document = json.loads(world.read_text(encoding="utf-8"))
            # Only environment worlds carry cells to recount; the bare causal
            # worlds have no resource ledger and are skipped rather than failed.
            if not str(document.get("format", "")).startswith("deterministic-environment-world-spec"):
                continue
            reports.append(audit_world(world, workspace))

    if arguments.vault:
        if not VAULT.is_dir():
            print(f"vault not found: {VAULT}", file=sys.stderr)
            return 2
        for spec_path in sorted(VAULT.rglob("spec.json")):
            if (spec_path.parent / "records.jsonl").is_file():
                reports.append(audit_stored(spec_path.parent, spec_path))

    for run_dir in arguments.run_dirs:
        if arguments.spec is None:
            parser.error("--spec is required when auditing a run directory")
        reports.append(audit_stored(run_dir, arguments.spec))

    if not reports:
        parser.error("give --worlds, --vault, or a run directory with --spec")

    if arguments.json:
        print(json.dumps([item.canonical() for item in reports],
                         ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for report in reports:
            print(describe(report))
        clean = sum(1 for item in reports if item.valid)
        print(f"\nconserved under independent recount: {clean}/{len(reports)}")

    return 0 if all(item.valid for item in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
