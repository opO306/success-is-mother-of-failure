"""Independent ground-truth audit: seal the answer key B0.7 will be graded against.

Usage:
    python run_ground_truth_audit.py                 # run all three, print verdicts
    python run_ground_truth_audit.py --json           # machine-readable
    python run_ground_truth_audit.py --seal           # write sealed/*.json (refuses to overwrite)
    python run_ground_truth_audit.py --seal --force   # re-seal after a deliberate, recorded change

This audit does not import anything from `engine.deterministic` newer than
the A0 causal kernel (world 1) or nothing from `engine` at all (worlds 2/3)
-- see `audit/ground_truth/__init__.py`. It exists to answer, independently
of B0.4-B0.7's own code, whether three small worlds' intended causal
structure (a hidden mediator, a direct relation, a gated relation) is
actually true of A.

`--seal` writes one JSON file per world under `audit/ground_truth/sealed/`,
each carrying its own `ground_truth_digest`. Once sealed, a file is not
silently overwritten: rerunning `--seal` without `--force` on an unchanged
answer is a no-op, and on a *changed* answer it refuses and tells you the
old and new digests, so quietly editing the answer key after seeing how B
did requires a conscious `--force` and leaves both digests in your terminal
history.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit.ground_truth import (
    GroundTruthReport,
    audit_world1_mediator,
    audit_world2_direct,
    audit_world3_conditional,
)

SEALED_DIR = Path(__file__).resolve().parent / "audit" / "ground_truth" / "sealed"

AUDITS = (audit_world1_mediator, audit_world2_direct, audit_world3_conditional)


def describe(report: GroundTruthReport) -> str:
    lines = [f"[{report.verdict}] {report.world_id}",
             f"    world_spec_digest    : {report.world_spec_digest}",
             f"    ground_truth_digest  : {report.digest}",
             f"    exhaustive            : {report.exhaustive}"
             + (f" ({report.exhaustive_cases_checked} cases)" if report.exhaustive else "")]
    for check in report.checks:
        mark = "OK " if check.passed else "!! "
        lines.append(f"    {mark}{check.name}")
        if not check.passed:
            lines.append(f"        expected: {check.expected!r}")
            lines.append(f"        observed: {check.observed!r}")
            if check.detail:
                lines.append(f"        detail  : {check.detail}")
    return "\n".join(lines)


def seal(report: GroundTruthReport, force: bool) -> tuple[bool, str]:
    """Write the sealed report. Returns (wrote, message)."""
    SEALED_DIR.mkdir(parents=True, exist_ok=True)
    path = SEALED_DIR / f"{report.world_id}.json"
    new_body = report.sealed()
    if path.is_file():
        old_body = json.loads(path.read_text(encoding="utf-8"))
        old_digest = old_body.get("ground_truth_digest")
        if old_digest == report.digest:
            return False, f"unchanged, already sealed at {old_digest}"
        if not force:
            return False, (f"REFUSED: sealed digest {old_digest} differs from new digest "
                           f"{report.digest} -- rerun with --force if this change is intentional "
                           f"and you can explain why in the commit message")
    path.write_text(json.dumps(new_body, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True, f"sealed to {path}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument("--seal", action="store_true", help="write sealed/*.json")
    parser.add_argument("--force", action="store_true", help="allow --seal to overwrite a changed answer")
    arguments = parser.parse_args(argv)

    reports = [fn() for fn in AUDITS]

    if arguments.json:
        print(json.dumps([r.sealed() for r in reports], ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for report in reports:
            print(describe(report))
            print()
        valid = sum(1 for r in reports if r.verdict == "VALID")
        print(f"VALID: {valid}/{len(reports)}")

    if arguments.seal:
        for report in reports:
            if report.verdict != "VALID":
                print(f"NOT SEALING {report.world_id}: verdict is {report.verdict}, not VALID", file=sys.stderr)
                continue
            wrote, message = seal(report, arguments.force)
            print(f"{'wrote' if wrote else 'skip '} {report.world_id}: {message}", file=sys.stderr)

    return 0 if all(r.verdict == "VALID" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
