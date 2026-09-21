"""Audit provenance traces with the independent reader.

Usage:
    python run_independent_trace_audit.py <run_dir> [<run_dir> ...]
    python run_independent_trace_audit.py --vault          # every trace in the D: vault
    python run_independent_trace_audit.py --vault --compare-engine

`--compare-engine` additionally runs the engine's own `verify_trace` and
reports whether the two routes agree. Disagreement is the finding: it means
one of the two is wrong, and which one is a question for inspection, not for
this script to assume.

Raw vault contents are never printed — only paths, counts and digests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit.independent_trace import sha256_via_external_tool, verify_trace_independently

VAULT = Path("D:/KiroCrewTraceVault/success-is-mother-of-failure")


def discover(root: Path) -> list[Path]:
    return sorted(
        path.parent for path in root.rglob("manifest.json")
        if (path.parent / "records.jsonl").is_file()
    )


def audit(run_dir: Path, compare_engine: bool) -> dict[str, object]:
    result = verify_trace_independently(run_dir)
    external = sha256_via_external_tool(run_dir / "records.jsonl")
    row: dict[str, object] = {
        "run_dir": str(run_dir),
        "independent_valid": result.valid,
        "record_count": result.record_count,
        "final_chain_hash": result.final_chain_hash,
        "records_sha256": result.records_sha256,
        "external_tool": external.canonical(),
        "external_agrees": external.available and external.digest == result.records_sha256,
        "findings": [item.canonical() for item in result.findings],
    }
    if compare_engine:
        try:
            from engine.deterministic import verify_trace

            engine_result = verify_trace(run_dir)
            row["engine_valid"] = bool(engine_result["valid"])
            row["engine_chain_hash"] = engine_result["final_chain_hash"]
            row["engine_error"] = None
        except Exception as error:  # the engine raises on any rejection
            row["engine_valid"] = False
            row["engine_chain_hash"] = None
            row["engine_error"] = f"{type(error).__name__}: {error}"
        row["routes_agree"] = (
            row["engine_valid"] == result.valid
            and (not result.valid or row["engine_chain_hash"] == result.final_chain_hash)
        )
    return row


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="*", type=Path)
    parser.add_argument("--vault", action="store_true", help="audit every trace in the D: vault")
    parser.add_argument("--compare-engine", action="store_true",
                        help="also run the engine's verifier and compare")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    arguments = parser.parse_args(argv)

    targets = list(arguments.run_dirs)
    if arguments.vault:
        if not VAULT.is_dir():
            print(f"vault not found: {VAULT}", file=sys.stderr)
            return 2
        targets.extend(discover(VAULT))
    if not targets:
        parser.error("give at least one run directory, or --vault")

    rows = [audit(path, arguments.compare_engine) for path in targets]

    if arguments.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for row in rows:
            name = row["run_dir"]
            state = "valid" if row["independent_valid"] else f"{len(row['findings'])} finding(s)"
            line = f"{'OK ' if row['independent_valid'] else '!! '}{name}\n"
            line += f"    independent : {state}, {row['record_count']} records\n"
            line += f"    records sha : {row['records_sha256']}\n"
            external = row["external_tool"]
            line += (f"    external    : {'agrees' if row['external_agrees'] else external['detail']}\n")
            if arguments.compare_engine:
                verdict = "agree" if row["routes_agree"] else "DISAGREE"
                line += f"    engine      : valid={row['engine_valid']} -> routes {verdict}\n"
                if row["engine_error"]:
                    line += f"                  {row['engine_error']}\n"
            for finding in row["findings"][:5]:
                line += (f"    - [{finding['code']}] seq={finding['sequence']} "
                         f"tick={finding['tick']}: {finding['detail'][:80]}\n")
            print(line, end="")

        total = len(rows)
        clean = sum(1 for row in rows if row["independent_valid"])
        print(f"\nindependent: {clean}/{total} valid")
        if arguments.compare_engine:
            agreed = sum(1 for row in rows if row["routes_agree"])
            print(f"routes agree: {agreed}/{total}")

    if any(not row["independent_valid"] for row in rows):
        return 1
    if arguments.compare_engine and any(not row["routes_agree"] for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
