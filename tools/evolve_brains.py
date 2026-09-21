"""Stages 2-4 of design doc 4: evolve an ancestor for one brain candidate, selected by how long its people live.

  python -m tools.evolve_brains --brain B --generations 40 --population 24 --per-camp 5 --max-days 30 --worlds 2
  python -m tools.evolve_brains --brain A --learn --start runs/evolve_20260915_A/best_gen039.pt
  python -m tools.evolve_brains --brain A --learn --start runs/evolve_20260915_A/ancestor.pt --first-generation 63 --stop-alive 2

Writes runs/<stamp>_evolve_<brain>[_learn]/generations.jsonl, the best genome of each generation, and ancestor.pt when
the best genome keeps --stop-alive of its people alive past day 6 and they drink at least half the times they are thirsty
at water (2 never stops). A genome from before stage 4 given as --start grows into the stage 4 shapes.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from engine.brain import evolve, temperament


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=["A", "B", "C", "D"])
    parser.add_argument("--graft", default=None, help="brain D: a saved genome of another brain whose senses D starts with")
    parser.add_argument("--graft-from", default="A", choices=["A", "B", "C"])
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--max-days", type=int, default=30)
    parser.add_argument("--worlds", type=int, default=2)
    parser.add_argument("--sigma", type=float, default=0.02)
    parser.add_argument("--elite", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learn", action="store_true", help="people learn within their lives from how their body eases")
    parser.add_argument("--rule", default="rpe", choices=["rpe", "plain"])
    parser.add_argument("--spread", type=float, default=temperament.SPREAD, help="how far people scatter around the lineage's temper")
    parser.add_argument("--stop-alive", type=float, default=0.8)
    parser.add_argument("--births", action="store_true", help="people are born inside the world; fitness is days lived by founders and descendants")
    parser.add_argument("--old-food", action="store_true", help="the food rule before the energy balance law (fixed need, 2-day store)")
    parser.add_argument("--tame", action="store_true", help="animals as before wildlife.py: no drinking trips, stalking or charging, no large predators")
    parser.add_argument("--no-puddles", action="store_true", help="rain leaves no standing water")
    parser.add_argument("--land", default="danyang", choices=["danyang", "old"], help="the real Danyang/Jecheon land or the first made-up map")
    parser.add_argument("--static-plants", action="store_true", help="plants regrow by season numbers instead of warmth and moisture")
    parser.add_argument("--no-sky", action="store_true", help="no day length, light or moon")
    parser.add_argument("--stepped-feelings", action="store_true", help="feelings in steps, no hormones, sleep never spoiled")
    parser.add_argument("--scripted-animals", action="store_true", help="animals by wildlife.py's schedules and odds instead of their own needs")
    parser.add_argument("--forced-sleep", action="store_true", help="sleep by debt collapse and chosen sleep instead of the sleep switch")
    parser.add_argument("--out", default=None)
    parser.add_argument("--start", default=None, help="a saved genome (best_genNNN.pt) to go on from")
    parser.add_argument("--first-generation", type=int, default=0)
    args = parser.parse_args(argv)
    suffix = "_learn" if args.learn else ""
    out = Path(args.out) if args.out else Path("runs") / f"{datetime.now():%Y%m%d-%H%M%S}_evolve_{args.brain}{suffix}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "settings.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"기록: {out}", flush=True)
    evolve.run(args.brain, out, args.generations, args.population, args.per_camp, args.max_days, args.worlds, args.sigma,
               args.elite, args.seed, stop_alive=args.stop_alive, start=Path(args.start) if args.start else None,
               first_generation=args.first_generation, learns=args.learn, rule=args.rule, spread=args.spread,
               births=args.births, energy=not args.old_food, wildlife=not args.tame, puddles=not args.no_puddles, land=args.land, plants=not args.static_plants,
               sky=not args.no_sky, graded=not args.stepped_feelings, animals=not args.scripted_animals,
               graft=Path(args.graft) if args.graft else None, graft_from=args.graft_from, sleep_switch=not args.forced_sleep)
    for line in (out / "generations.jsonl").read_text(encoding="utf-8").splitlines():
        print(line, flush=True)
    return out


if __name__ == "__main__":
    main()
