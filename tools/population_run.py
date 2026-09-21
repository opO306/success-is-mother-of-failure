"""One world lived for many compressed years with births, so selection happens inside it (design doc 4, generations).

Every --every days a census line: who is alive at what stage, births and matings so far, the deepest generation, the
living's mean trait values, and the gene pool (the summed allele means of each trait's loci, the share of harmful copies,
how common the commonest allele of each neutral marker has become). At the end: heritability of every trait from children
on mid-parents, every birth, and every life with its age at death and cause.

  python -m tools.population_run --brain A --genome runs/evolve_20260915_A_temper/best_gen102.pt --learn --days 600
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import torch
from torch.nn.utils import vector_to_parameters

from engine.brain import brains, evolve, genetics, life, lifecycle
from engine.primal.scenario import build_world


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", required=True, choices=["A", "B", "C"])
    parser.add_argument("--genome", default=None)
    parser.add_argument("--learn", action="store_true")
    parser.add_argument("--rule", default="rpe", choices=["rpe", "plain"])
    parser.add_argument("--seed", type=int, default=7001)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--days", type=int, default=600)
    parser.add_argument("--every", type=int, default=10)
    parser.add_argument("--epigenetic", type=float, default=0.0, help="share of a mother's early mark passed on (experiment)")
    parser.add_argument("--old-food", action="store_true", help="the food rule before the energy balance law")
    parser.add_argument("--tame", action="store_true", help="animals as before wildlife.py")
    parser.add_argument("--no-puddles", action="store_true", help="rain leaves no standing water")
    parser.add_argument("--land", default="danyang", choices=["danyang", "old"])
    parser.add_argument("--static-plants", action="store_true")
    parser.add_argument("--no-sky", action="store_true")
    parser.add_argument("--stepped-feelings", action="store_true")
    parser.add_argument("--scripted-animals", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    genetics.EPIGENETIC_INHERITANCE = args.epigenetic
    out = Path(args.out) if args.out else Path("runs") / f"{datetime.now():%Y%m%d-%H%M%S}_population_{args.brain}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "settings.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"기록: {out}", flush=True)
    brain = brains.make(args.brain, 0, learns=args.learn, rule=args.rule)
    if args.genome:
        vector_to_parameters(evolve.load_genome(brain, Path(args.genome)), brain.parameters())
    world = build_world(seed=args.seed, band_size=args.per_camp, energy=not args.old_food, wildlife=not args.tame,
                        puddles=not args.no_puddles, land=args.land, plants=not args.static_plants,
                        sky=not args.no_sky, graded=not args.stepped_feelings, animals=not args.scripted_animals)
    population = lifecycle.found(world, brain.genes_values())
    stats = life.new_stats()
    rng = random.Random(args.seed)
    with (out / "census.jsonl").open("w", encoding="utf-8") as census:
        for day in range(1, args.days + 1):
            summary = life.live_day(world, brain, rng, stats, population)
            if day % args.every == 0 or summary["alive"] == 0 or day == args.days:
                line = json.dumps(lifecycle.census(population, world), ensure_ascii=False)
                census.write(line + "\n")
                census.flush()
                print(line, flush=True)
            if summary["alive"] == 0:
                break
    (out / "births.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in population.births), encoding="utf-8")
    lives = []
    for name, lived in population.lives.items():
        person = world.people[name]
        lives.append({"person": name, "sex": lived.sex, "generation": lived.generation, "mother": lived.mother,
                      "father": lived.father, "born": lived.born, "age": world.day - lived.born, "alive": person.alive,
                      "cause": None if person.alive else person.body.cause_of_death, "days_lived": stats["days"][name],
                      "vigour": round(genetics.vigour(lived.genome), 3),
                      "traits": {t: round(v, 3) for t, v in lived.development.traits(population.means).items()}})
    (out / "lives.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lives), encoding="utf-8")
    heritability = lifecycle.heritability(population)
    (out / "heritability.json").write_text(json.dumps(heritability, ensure_ascii=False, indent=2), encoding="utf-8")
    print("heritability", json.dumps({k: (None if v is None else round(v, 2)) for k, v in heritability.items()}), flush=True)
    return out


if __name__ == "__main__":
    main()
