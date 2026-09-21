"""Count what the causal worlds offer before bundle 4 rules are built.

Answers one question per world: could a catalyst, a polymer, a template or a
division have fired here at all? A zero is the finding -- it says the rule
would never run, and that building it first would repeat 2026-09-20.

    python run_precondition_census.py --worlds
    python run_precondition_census.py --spec worlds/deterministic_polymer_chain_v2.json

Exit code 1 when some world blocks a rule outright, so the absence of a
chance is visible without reading the table.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.deterministic import (
    census_causal_world,
    load_causal_world_spec,
    render_census,
)
from engine.deterministic.causal_spec import SUPPORTED_FORMATS

WORLDS = Path("worlds")


def _causal_specs() -> list[Path]:
    found = []
    for path in sorted(WORLDS.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("format") in SUPPORTED_FORMATS:
            found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, action="append", default=[])
    parser.add_argument("--worlds", action="store_true",
                        help="census every causal spec under worlds/")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    paths = list(args.spec)
    if args.worlds:
        paths.extend(_causal_specs())
    if not paths:
        parser.error("pass --spec or --worlds")

    reports = []
    blocked_any = False
    for path in paths:
        census = census_causal_world(load_causal_world_spec(path))
        blocked = census.blocked()
        blocked_any = blocked_any or bool(blocked)
        reports.append({"spec": str(path), "blocked": list(blocked),
                        "census": census.canonical()})

        print(f"{census.world_id}  ({census.ticks} ticks)")
        print(f"  three-or-more in one cell : {census.ticks_with_three_or_more_free} ticks"
              f"  (peak {census.peak_cell_crowding} cells)")
        print(f"  free particle meets chain : {census.ticks_with_chain_arrival} ticks")
        print(f"  longest chain             : {census.peak_longest_chain}"
              f"   (four or more on {census.ticks_with_four_chain} ticks)")
        print(f"  standing chain, free port : {census.ticks_with_standing_free_port} ticks")
        print(f"  chains at once            : peak {census.peak_coexisting_chains}"
              f"   (two or more on {census.ticks_with_two_chains} ticks)")
        if blocked:
            for item in blocked:
                print(f"  BLOCKED  {item}")
        else:
            print("  every bundle-4 precondition occurred at least once")
        print()

    if args.output is not None:
        payload = {"format": "deterministic-precondition-census-report-v1",
                   "reports": reports}
        rendered = json.dumps(payload, ensure_ascii=False, indent=2,
                              sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)

    return 1 if blocked_any else 0


if __name__ == "__main__":
    sys.exit(main())
