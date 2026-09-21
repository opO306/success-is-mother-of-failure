"""Does learning within a life change what a genome does? The same genome in the same worlds, learning off, then on.

If learning works, people who learn should drink more often when thirsty at water late in life than early, and more
than the same genome without learning. The worlds are fixed test worlds no evolution run selected on.

  python -m tools.learning_check --brain A --genome runs/evolve_20260915_A/best_gen039.pt --rates 0.03,0.1,0.3
"""
from __future__ import annotations

import argparse
import json
import math

import torch
from torch.nn.utils import vector_to_parameters

from engine.brain import brains, evolve


def main(argv: list[str] | None = None) -> list[dict]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=["A", "B", "C"])
    parser.add_argument("--genome", default=None, help="a saved genome; random weights if left out")
    parser.add_argument("--worlds", default="5001,5002,5003,5004,5005")
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--max-days", type=int, default=30)
    parser.add_argument("--rates", default="0.1", help="learning rates to try when the genome has none of its own")
    parser.add_argument("--rule", default="rpe", choices=["rpe", "plain"],
                        help="rpe: learn from surprise against a running expectation, shared back over recent choices")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    seeds = [int(s) for s in args.worlds.split(",")]
    results = []
    conditions = [("off", None)] + [("on", float(r)) for r in args.rates.split(",")]
    for label, rate in conditions:
        brain = brains.make(args.brain, 0, learns=label == "on", rule=args.rule)
        if args.genome:
            vector_to_parameters(evolve.load_genome(brain, args.genome), brain.parameters())
        if rate is not None:
            with torch.no_grad():
                brain.learning.log.fill_(math.log(rate))
        result = {"learning": label, "rule": args.rule if label == "on" else None, "rate": brain.learning_rate(),
                  **evolve.evaluate(brain, seeds, args.per_camp, args.max_days)}
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in result.items()}, ensure_ascii=False), flush=True)
        results.append(result)
    return results


if __name__ == "__main__":
    main()
