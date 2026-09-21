"""Agent world v2: bodies, a map, a day of six slots, an economy with no formula income.

Usage:
  python run_agent_world2.py --days 3                      # a fresh world
  python run_agent_world2.py --days 10 --resume runs/<run>/snapshots/day_003.pkl
Everything is written under runs/<stamp>_agentworld_seed<seed>/, including digest.md (readable while it runs)
and a snapshot of the whole world after every day.
"""
import argparse
import pickle
import sys
import time
from dataclasses import asdict

import requests

from engine import recorder as recording
from engine.agentworld.day import step_day
from engine.agentworld.scenario import build_world

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()

    if args.resume:
        with open(args.resume, "rb") as f:
            world = pickle.load(f)
    else:
        world = build_world(seed=args.seed)
    try:
        ollama = requests.get(f"{world.config.llm.llm_host}/api/version", timeout=3).json().get("version")
    except requests.RequestException:
        ollama = None
    run = recording.start_run(f"agentworld_seed{args.seed}", {
        "seed": args.seed, "days": args.days, "resume": args.resume, "start_day": world.day,
        "people": len(world.people), "ollama_version": ollama, "config": asdict(world.config),
        "orgs": {o.name: o.origin for o in world.orgs.values()},
    })
    print(f"기록: {run.root}")
    print("조직 (보이는 이름 → 시작 조건):", {o.name: o.origin for o in world.orgs.values()})
    started = time.time()
    try:
        for _ in range(args.days):
            day_started = time.time()
            summary = step_day(world, snapshot_dir=run.root / "snapshots")
            money = summary["money"]
            print(
                f"{summary['day']}일째: 생존 {summary['alive']}, 거래 {summary['trades']}, 사건 {len(summary['events'])}, "
                f"주화 {money['coins']:.0f}, 지폐 {sum(money['notes'].values()):.0f}, {time.time() - day_started:.0f}s",
                flush=True,
            )
    finally:
        recording.stop_run()
    print(f"총 {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
