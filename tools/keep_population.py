"""Keep population worlds running until a deadline (design doc 4, generations): when a world ends (everyone dead or its
days used up), the next seed starts, so data keeps piling up while nobody is watching. One line per finished world goes
to <out>/worlds.jsonl: how long it lasted, how many were born, the deepest generation, and the census at its end.

  python -m tools.keep_population --brain A --genome runs/evolve_20260915_A_temper/best_gen102.pt --learn --hours 2.5
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from tools import population_run


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=["A", "B", "C"])
    parser.add_argument("--genome", default=None)
    parser.add_argument("--learn", action="store_true")
    parser.add_argument("--days", type=int, default=600)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--first-seed", type=int, default=7001)
    parser.add_argument("--hours", type=float, default=2.5)
    parser.add_argument("--land", default="danyang", choices=["danyang", "old"])
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = Path(args.out) if args.out else Path("runs") / f"{datetime.now():%Y%m%d-%H%M%S}_keep_population_{args.brain}"
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.hours * 3600
    seed = args.first_seed
    while time.monotonic() < deadline:
        world_dir = out / f"seed_{seed}"
        started = time.monotonic()
        argv_run = ["--brain", args.brain, "--days", str(args.days), "--per-camp", str(args.per_camp), "--seed", str(seed),
                    "--land", args.land, "--out", str(world_dir)]
        if args.genome:
            argv_run += ["--genome", args.genome]
        if args.learn:
            argv_run.append("--learn")
        population_run.main(argv_run)
        lines = (world_dir / "census.jsonl").read_text(encoding="utf-8").splitlines()
        last = json.loads(lines[-1]) if lines else {}
        record = {"seed": seed, "minutes": round((time.monotonic() - started) / 60, 1), "last_day": last.get("day"),
                  "alive_at_end": last.get("alive"), "born": last.get("born"), "matings": last.get("matings"),
                  "deepest_generation": last.get("generation"), "census_at_end": last}
        with (out / "worlds.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print("world done", json.dumps({k: v for k, v in record.items() if k != "census_at_end"}, ensure_ascii=False), flush=True)
        seed += 1
    return out


if __name__ == "__main__":
    main()
