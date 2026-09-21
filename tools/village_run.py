"""One band, left alone (2026-09-17). No generations, no scoring, no ranking: a world runs for years, people are born
with brains mixed from their parents', and a line either continues or ends.

  python -m tools.village_run --brain A --genome runs/.../best_gen282.pt --world 9001 --years 5
  python -m tools.village_run --brain A --genome ... --inherit learning    # only the machinery for learning is passed on

Writes runs/<out>/world<seed>.json: what happened each day and how it ended.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

import torch
from torch.nn.utils import parameters_to_vector, vector_to_parameters

from engine.brain import band as band_module
from engine.brain import brains, evolve, life, lifecycle
from engine.primal.scenario import build_world

YEAR_DAYS = 364


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", default="A", choices=["A", "B", "C", "D"])
    parser.add_argument("--genome", default=None, help="the brain the founders are born with; random if left out")
    parser.add_argument("--inherit", default="all", choices=["all", "learning"])
    parser.add_argument("--second-brain", default=None, choices=["A", "B", "C", "D"], help="another make of brain, camp by camp")
    parser.add_argument("--second-genome", default=None)
    parser.add_argument("--world", type=int, default=9001)
    parser.add_argument("--years", type=float, default=5.0)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--out", default="runs/village")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)

    seed_brain = brains.make(args.brain, 0, learns=True)
    if args.genome:
        vector_to_parameters(evolve.load_genome(seed_brain, Path(args.genome)), seed_brain.parameters())
    seed = parameters_to_vector(seed_brain.parameters()).detach().clone()

    others = {}
    if args.second_brain:
        second = brains.make(args.second_brain, 0, learns=True)
        if args.second_genome:
            vector_to_parameters(evolve.load_genome(second, Path(args.second_genome)), second.parameters())
        others[args.second_brain] = parameters_to_vector(second.parameters()).detach().clone()
    rng = random.Random(args.world)
    band = band_module.Band(args.brain, seed, learns=True, inherit=args.inherit, rng=rng, others=others)
    world = build_world(seed=args.world, band_size=args.per_camp, energy=True, wildlife=True, puddles=True,
                        land="danyang", plants=True, sky=True, graded=True, animals=True, sleep_switch=True)
    population = lifecycle.found(world, band.genes_values())
    kinds = {}
    if args.second_brain:   # camp by camp: the first camp is one make of brain, the next another
        camps = sorted({p.camp for p in world.people.values()})
        for person in world.people.values():
            kinds[person.name] = args.brain if camps.index(person.camp) % 2 == 0 else args.second_brain
    band.found(sorted(world.people), kinds)
    stats = life.new_stats()
    days = int(args.years * YEAR_DAYS)
    started = time.time()
    known = set(world.people)
    history, causes, days_by_make = [], Counter(), Counter()
    for day in range(days):
        summary = life.live_day(world, band, rng, stats, population)
        for name, lived in population.lives.items():
            if name not in known:
                known.add(name)
                band.born(name, lived.mother, lived.father)
        for name in [n for n in list(band.genomes) if not world.people[n].alive]:
            causes[world.people[name].body.cause_of_death or "?"] += 1
            band.buried(name)
        for name, kind in band.kind_of.items():
            if name in world.people and world.people[name].alive:
                days_by_make[kind] += 1
        alive = summary["alive"]
        if day % 7 == 0 or alive == 0:
            history.append({"day": world.day - 1, "alive": alive, "born": population.born_count,
                            "makes": {k: sum(1 for n, kk in band.kind_of.items() if kk == k and world.people[n].alive)
                                      for k in sorted(set(band.kind_of.values()))},
                            "deepest": max((l.generation for l in population.lives.values()), default=0),
                            "drift": round(band.drift(), 2)})
        if alive == 0:
            break
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "world": args.world, "brain": args.brain, "genome": args.genome, "inherit": args.inherit,
        "days_lived": world.day - 1, "days_asked": days, "people_ever": len(known),
        "born": population.born_count, "matings": population.matings,
        "deepest_generation": max((l.generation for l in population.lives.values()), default=0),
        "ended": "died out" if not any(p.alive for p in world.people.values()) else "still alive",
        "alive_at_end": sum(1 for p in world.people.values() if p.alive),
        "person_days": stats["person_days"], "drift": round(band.drift(), 2),
        "by_make": {kind: sum(1 for n, k in band.kind_of.items() if k == kind and world.people[n].alive)
                    for kind in sorted(set(band.kind_of.values()))},
        "days_by_make": dict(days_by_make), "ever_by_make": {kind: sum(1 for k in band.kind_of.values() if k == kind)
                         for kind in sorted(set(band.kind_of.values()))},
        "deaths": dict(causes.most_common()), "seconds": round(time.time() - started), "history": history,
    }
    (out / f"world{args.world}_{args.inherit}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "history"}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
