"""Who lived how, by what they were born with. One genome in fixed test worlds, one row per person, then how each
temperament dimension goes with days lived, places known, acts tried and going at danger while afraid (Pearson r).
No row is named after a diagnosis; combinations are for looking at, and the rows are saved with --out.

  python -m tools.temperament_report --brain A --genome runs/evolve_20260915_A/ancestor.pt --learn
  python -m tools.temperament_report --brain A --genome runs/evolve_20260915_A/ancestor.pt --spread 0
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from torch.nn.utils import vector_to_parameters

from engine.brain import brains, evolve, temperament


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main(argv: list[str] | None = None) -> tuple[dict, list[dict]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=["A", "B", "C"])
    parser.add_argument("--genome", default=None)
    parser.add_argument("--learn", action="store_true")
    parser.add_argument("--rule", default="rpe", choices=["rpe", "plain"])
    parser.add_argument("--worlds", default="5001,5002,5003,5004,5005")
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--max-days", type=int, default=30)
    parser.add_argument("--spread", type=float, default=temperament.SPREAD)
    parser.add_argument("--out", default=None, help="jsonl file for the per-person rows")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    brain = brains.make(args.brain, 0, learns=args.learn, rule=args.rule)
    if args.genome:
        vector_to_parameters(evolve.load_genome(brain, Path(args.genome)), brain.parameters())
    records: list[dict] = []
    result = evolve.evaluate(brain, [int(s) for s in args.worlds.split(",")], args.per_camp, args.max_days, args.spread, records)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in result.items()}, ensure_ascii=False), flush=True)
    for r in records:
        r["approach_when_afraid"] = r["afraid_approach"] / r["afraid"] if r["afraid"] else 0.0
    for outcome in ("days", "places_known", "acts_tried", "approach_when_afraid"):
        row = {}
        for gene in temperament.GENES:
            r = pearson([p[gene] for p in records], [p[outcome] for p in records])
            row[gene] = None if r is None else round(r, 2)
        print(outcome, json.dumps(row, ensure_ascii=False), flush=True)
    if args.out:
        Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return result, records


if __name__ == "__main__":
    main()
