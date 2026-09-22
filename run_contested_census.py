"""Count where the kernel decides by id instead of by physics.

Principle 3 of `LOCAL_INTERACTION_PRINCIPLES_V1.md`: when the declared state
does not single out one outcome, an id must not pick for it. This reports how
much of the current physics rests on that, so the fix can be measured rather
than asserted.

    python run_contested_census.py --worlds
    python run_contested_census.py --spec worlds/deterministic_polymer_chain_v2.json

Exit code 1 when any contested moment was found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.deterministic import contested_causal_world, load_causal_world_spec
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
    parser.add_argument("--worlds", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    paths = list(args.spec)
    if args.worlds:
        paths.extend(_causal_specs())
    if not paths:
        parser.error("pass --spec or --worlds")

    reports = []
    total = 0
    for path in paths:
        census = contested_causal_world(load_causal_world_spec(path))
        total += len(census.moments)
        reports.append({"spec": str(path), "census": census.canonical()})

        print(f"{census.world_id}  ({census.ticks} ticks)")
        if not census.moments:
            print("  no contested moment: every outcome was determined by the state")
        else:
            for kind, count in census.by_kind().items():
                print(f"  {kind}: {count}")
            for moment in census.moments[:5]:
                print(f"    tick {moment.tick} ({moment.x},{moment.y})  "
                      f"candidates {list(moment.candidates)}  {moment.detail}")
            if len(census.moments) > 5:
                print(f"    ... and {len(census.moments) - 5} more")
        print()

    if args.output is not None:
        payload = {"format": "deterministic-contested-census-report-v1",
                   "reports": reports}
        rendered = json.dumps(payload, ensure_ascii=False, indent=2,
                              sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)

    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
