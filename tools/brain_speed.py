"""Stage 1 of design doc 4: how long does a day take when brains live it, and how does each candidate do untrained?

Every candidate lives the same seed with the same small band. Their weights are random, so the survival numbers are the
floor that learning and evolution must climb from, not a comparison of what the designs can become. The time split
(sensing, thinking, engine) shows where a generation's hours would go.

  python -m tools.brain_speed --per-camp 5 --days 10 --brains random,A,B,C
"""
from __future__ import annotations

import argparse
import json
import random
import time

from engine.brain import brains, life
from engine.primal.scenario import build_world

GENERATION_DAYS, PEOPLE = 600, 45


def run(name: str, seed: int, per_camp: int, days: int) -> dict:
    world = build_world(seed=seed, band_size=per_camp)
    brain = brains.make(name, seed)
    rng = random.Random(seed)
    stats = life.new_stats()
    started = time.perf_counter()
    lived = 0
    alive_by_day = []
    for _ in range(days):
        summary = life.live_day(world, brain, rng, stats)
        lived += 1
        alive_by_day.append(summary["alive"])
        if summary["alive"] == 0:
            break
    wall = time.perf_counter() - started
    per_person_day = wall / max(1, stats["person_days"])
    return {
        "brain": name, "parameters": brain.parameters_count(), "people": per_camp * 3, "days_lived": lived, "alive_by_day": alive_by_day,
        "wall_s": round(wall, 2), "sense_s": round(stats["sense_s"], 2), "brain_s": round(stats["brain_s"], 2), "engine_s": round(stats["engine_s"], 2),
        "decisions": stats["decisions"], "decisions_per_person_day": round(stats["decisions"] / max(1, stats["person_days"]), 2),
        "mean_think_steps": round(stats["think_steps"] / max(1, stats["decisions"]), 2),
        "ms_per_decision": round(1000 * stats["brain_s"] / max(1, stats["decisions"]), 3),
        "generation_hours_45_people": round(per_person_day * PEOPLE * GENERATION_DAYS / 3600, 2),
        "drank_when_thirsty_at_water": f"{stats['drank_when_thirsty_at_water']}/{stats['thirsty_at_water']}",
        "ops_ok_top": dict(stats["ops_ok"].most_common(8)),
    }


def main(argv: list[str] | None = None) -> list[dict]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--brains", default="random,A,B,C")
    args = parser.parse_args(argv)
    results = []
    for name in args.brains.split(","):
        result = run(name, args.seed, args.per_camp, args.days)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        results.append(result)
    return results


if __name__ == "__main__":
    main()
