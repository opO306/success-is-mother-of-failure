"""Ask a saved brain Pearl's three questions (engine/brain/probe.py) in worlds with every law on.

  python -m tools.probe_brain --brain A --genome runs/.../best_gen147.pt --worlds 4 --days 20
  python -m tools.probe_brain --brain random            # the floor

Writes the scores as JSON next to the genome (or to --out) and prints them.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from torch.nn.utils import vector_to_parameters

from engine.brain import brains, evolve, probe


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", default="A", choices=["A", "B", "C", "D", "random"])
    parser.add_argument("--genome", default=None)
    parser.add_argument("--no-learn", action="store_true")
    parser.add_argument("--trust", type=float, default=None, help="set the forecast's trust instead of the genome's")
    parser.add_argument("--forecast-rate", type=float, default=None, help="set how fast people correct their forecast")
    parser.add_argument("--worlds", type=int, default=4)
    parser.add_argument("--first-world", type=int, default=7000)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--ask-every", type=int, default=10)
    parser.add_argument("--branch-every", type=int, default=25)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    brain = brains.make(args.brain, 0, learns=not args.no_learn)
    if args.genome:
        vector_to_parameters(evolve.load_genome(brain, Path(args.genome)), brain.parameters())
    if args.trust is not None:
        with torch.no_grad():
            brain.foresight.trust.fill_(args.trust)
    if args.forecast_rate is not None:
        with torch.no_grad():
            brain.foresight.log_rate.fill_(math.log(args.forecast_rate))
    seeds = list(range(args.first_world, args.first_world + args.worlds))
    result = probe.run(brain, seeds, args.per_camp, args.days, args.ask_every, args.branch_every, energy=True,
                       wildlife=True, puddles=True, land="danyang", plants=True, sky=True, graded=True, animals=True,
                       sleep_switch=True)
    result.update(brain=args.brain, genome=args.genome, trust=args.trust, learns=not args.no_learn)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    print(text)
    out = Path(args.out) if args.out else (Path(args.genome).with_suffix(".probe.json") if args.genome else None)
    if out:
        out.write_text(text, encoding="utf-8")
    return result


if __name__ == "__main__":
    main()
