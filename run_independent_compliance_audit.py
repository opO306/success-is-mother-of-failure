"""Check that a recorded run obeyed the rules its world declared.

Usage:
    python run_independent_compliance_audit.py --worlds
    python run_independent_compliance_audit.py --vault
    python run_independent_compliance_audit.py <run_dir> --spec <spec.json>

Conservation asks whether the totals held. This asks whether matter took a
legal route to get where it ended up — water across a blocked edge, a jump to
a cell it never touches, a transfer above the declared limit, a phase change
the world forbids. All of those conserve perfectly.

Raw vault contents are never printed: only paths, counts and findings.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

from audit.independent_compliance import ComplianceReport, check_trace_compliance

VAULT = Path("D:/KiroCrewTraceVault/success-is-mother-of-failure")
WORLDS = Path(__file__).resolve().parent / "worlds"


def audit_stored(run_dir: Path, spec_path: Path) -> ComplianceReport:
    return check_trace_compliance(run_dir, json.loads(spec_path.read_text(encoding="utf-8")))


def audit_world(world: Path, workspace: Path) -> ComplianceReport:
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
    report = check_trace_compliance(run_dir, json.loads(world.read_text(encoding="utf-8")))
    report.source = str(world)
    return report


def describe(report: ComplianceReport) -> str:
    head = "OK " if report.valid else "!! "
    lines = [f"{head}{report.source}",
             f"    stages      : {report.stages_checked}"
             f"  ({report.transport_stages} transport,"
             f" {report.particle_stages} particle)"]
    if report.findings:
        counts = Counter(item.code for item in report.findings)
        lines.append(f"    findings    : {len(report.findings)}")
        for code, count in counts.most_common():
            example = next(item for item in report.findings if item.code == code)
            where = f"tick={example.tick} phase={example.phase}"
            if example.point:
                where += f" at {tuple(example.point)}"
            lines.append(f"    - [{code}] x{count}  {where}")
            lines.append(f"        {example.detail[:88]}")
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

    reports: list[ComplianceReport] = []
    workspace = Path(tempfile.mkdtemp(prefix="compliance-audit-"))

    if arguments.worlds:
        for world in sorted(WORLDS.glob("*.json")):
            document = json.loads(world.read_text(encoding="utf-8"))
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
        print(f"\nobeyed their declared rules: {clean}/{len(reports)}")

    return 0 if all(item.valid for item in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
