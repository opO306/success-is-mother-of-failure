"""causal v5 benchmarks (designer decision, 2026-09-24): A and B are separate questions.

    python run_v5_benchmarks.py stress   # A: denominator growth along ONE lineage, 10..500 merges, corner-free
    python run_v5_benchmarks.py census   # B: how often undefined physics stops an ordinary world

A reads the meter row of every merge in a single depth-500 run, so the numbers at
depth 10, 25, ... are the same lineage caught at that depth. The arithmetic share is
measured from outside with cProfile on a shorter run (time inside `fractions`), because
the reference executor must stay free of instrumentation. Results go to
runs/v5_benchmarks/ (outside Git) and are printed.
"""
from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import time
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from engine.deterministic import v5_benchmark_worlds as worlds
from engine.deterministic.v5_meter import DenominatorMeter
from engine.deterministic.v5_reference import run_v5
from engine.deterministic.v5_spec import RunRequest

OUT = Path(__file__).resolve().parent / "runs" / "v5_benchmarks"
DEPTHS = (10, 25, 50, 100, 250, 500)
FOREVER = RunRequest(10 ** 15, 10 ** 15)
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97)


def _variant(name: str):
    if name == "rest":
        return lambda depth: worlds.merge_chain_world(depth)
    if name == "drift":
        return lambda depth: worlds.merge_chain_world(depth, Fraction(1, 7))
    if name == "primes":
        def build(depth):
            saved = worlds.STRESS_MASSES
            worlds.STRESS_MASSES = tuple(str(1 + Fraction(1, p)) for p in PRIMES)
            try:
                return worlds.merge_chain_world(depth, Fraction(1, 7))
            finally:
                worlds.STRESS_MASSES = saved
        return build
    raise ValueError(name)


def _arithmetic_share(spec) -> float:
    profile = cProfile.Profile()
    profile.enable()
    run_v5(spec, FOREVER)
    profile.disable()
    stats = pstats.Stats(profile)
    inside = sum(v[2] for k, v in stats.stats.items() if k[0].endswith("fractions.py"))
    return inside / stats.total_tt


def stress(max_depth: int, variants: list[str]) -> dict:
    report = {}
    for name in variants:
        build = _variant(name)
        meter = DenominatorMeter()
        started = time.perf_counter()
        result = run_v5(build(max_depth), FOREVER, meter)
        wall = time.perf_counter() - started
        assert result.outcome == "completed" and not result.unresolved, "a stress world must never halt"
        assert len(result.events) == max_depth and all(len(e.pre) == 2 for e in result.events)
        rows, elapsed, table = meter.rows, 0.0, {}
        for depth, row in enumerate(rows, start=1):
            elapsed += row["round_seconds"]
            if depth in DEPTHS:
                table[depth] = {k: row[k] for k in row if k.endswith("_bits")} | {"cumulative_seconds": round(elapsed, 3)}
        share_depth = min(100, max_depth)
        report[name] = {"depth": max_depth, "wall_seconds": round(wall, 2), "by_depth": table,
                        f"arithmetic_share_at_depth_{share_depth}": round(_arithmetic_share(build(share_depth)), 3)}
        print(f"\n[{name}] depth {max_depth}: {wall:.1f}s, arithmetic share "
              f"{report[name][f'arithmetic_share_at_depth_{share_depth}']:.0%}")
        print("  depth  time_den pos_num pos_den vel_den kin_den U_num U_den resid_den  cum_s")
        for depth, row in table.items():
            print(f"  {depth:5d}  {row['time_den_bits']:8d} {row['position_num_bits']:7d} {row['position_den_bits']:7d} "
                  f"{row['velocity_den_bits']:7d} {row['kinetic_den_bits']:7d} {row['internal_num_bits']:5d} "
                  f"{row['internal_den_bits']:5d} {row['residual_den_bits']:9d}  {row['cumulative_seconds']:7.1f}")
    return report


def census(n: int, seeds: int) -> dict:
    report = {}
    for masses in (("1",), ("1", "2", "3")):
        reasons: dict[str, int] = {}
        runs = []
        for seed in range(seeds):
            result = run_v5(worlds.random_world(n, seed, masses=masses), RunRequest(200, 200))
            key = f"{result.unresolved[0].kind}/{result.unresolved[0].reason}" if result.unresolved else "completed"
            reasons[key] = reasons.get(key, 0) + 1
            runs.append({"seed": seed, "outcome": result.outcome, "end_time": str(result.final_state.time),
                         "merges": len(result.events), "end": key})
        report["masses=" + ",".join(masses)] = {"reasons": reasons, "runs": runs}
        print(f"\nmasses {masses}: {reasons}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=("stress", "census"))
    parser.add_argument("--depth", type=int, default=500)
    parser.add_argument("--variants", nargs="+", default=["rest", "drift", "primes"])
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seeds", type=int, default=32)
    args = parser.parse_args()
    report = stress(args.depth, args.variants) if args.what == "stress" else census(args.n, args.seeds)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.what}-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
