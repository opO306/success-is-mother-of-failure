"""The primal world: three bands, a land with seasons and beasts, laws nobody is told.

Usage:
  python run_primal.py --days 3
  python run_primal.py --days 37 --resume runs/<run>/snapshots/day_003.pkl
Everything goes under runs/<stamp>_primal_seed<seed>/, including digest.md (readable while it runs) and daily snapshots.
"""
import argparse
import dataclasses
import os
import pickle
import sys
import time
from dataclasses import asdict

import requests

from engine import llm_agent
from engine import recorder as recording
from engine.config import SimulationConfig
from engine.primal import talent
from engine.primal.day import step_day
from engine.primal.scenario import build_world

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def check_servers(llm: SimulationConfig) -> None:
    """Before anything is recorded: every server the run will use answers and serves its model.
    A world whose minds never arrive is not a world, and its folder would sit among the real runs."""
    servers = {(llm.llm_backend, llm.llm_host.rstrip("/"), llm.llm_model),
               (llm.clerk_backend or llm.llm_backend, (llm.clerk_host or llm.llm_host).rstrip("/"), llm.clerk_model or llm.llm_model)}
    key = os.environ.get("LLM_API_KEY")
    for backend, host, model in sorted(servers):
        try:
            if backend == "openai":
                resp = requests.get(f"{host}/v1/models", timeout=10, headers={"Authorization": f"Bearer {key}"} if key else None)
                resp.raise_for_status()
                served = {m["id"] for m in resp.json()["data"]}
            else:
                resp = requests.get(f"{host}/api/tags", timeout=10)
                resp.raise_for_status()
                served = {m["name"] for m in resp.json()["models"]}
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"서버 {host}({backend})에서 모델 목록을 받지 못함: {type(exc).__name__}: {exc}")
        if model not in served and f"{model}:latest" not in served:
            raise SystemExit(f"서버 {host}에 모델 {model}이(가) 없음. 있는 모델: {', '.join(sorted(served)) or '(없음)'}")


def run_world(seed: int, days: int, resume: str | None, models: dict | None = None, talent_on: bool = True) -> bool:
    """Runs one world; returns whether it had talent (a resumed world keeps what its snapshot had)."""
    if resume:
        with open(resume, "rb") as f:
            world = pickle.load(f)
        if world.seed is None:  # snapshots from before talent did not keep their seed
            world.seed = seed
        talent.settle(world)
    else:
        world = build_world(seed=seed, talent_on=talent_on)
    # a day lived without its minds is not data: a server that stays silent stops the run instead
    world.config.llm = dataclasses.replace(world.config.llm, llm_stop_when_unreachable=True, **(models or {}))
    check_servers(world.config.llm)
    try:
        ollama = requests.get(f"{world.config.llm.llm_host}/api/version", timeout=3).json().get("version")
    except (requests.RequestException, ValueError):
        ollama = None
    # a world on another model is a separate condition, and its folder says so
    tag = "".join(ch if ch.isalnum() else "-" for ch in f"_{models['llm_model']}") if models and models.get("llm_model") else ""
    tag += "" if world.config.talent else "_notalent"
    run = recording.start_run(f"primal_seed{seed}{tag}", {
        "seed": seed, "days": days, "resume": resume, "start_day": world.day, "people": len(world.people),
        "ollama_version": ollama, "config": asdict(world.config),
    })
    print(f"기록: {run.root}")
    talent.record(world)
    started = time.time()
    lived = 0
    try:
        while days == 0 or lived < days:
            day_started = time.time()
            try:
                s = step_day(world, snapshot_dir=run.root / "snapshots")
            except llm_agent.LLMUnreachable as exc:
                # the day stopped partway: what it wrote so far is not a whole day, and the last whole one is where to go on from
                last = str(run.root / "snapshots" / f"day_{world.day - 1:03d}.pkl") if lived else resume
                run.write("aborted", {"day": world.day, "reason": str(exc), "resume_from": last})
                with (run.root / "digest.md").open("a", encoding="utf-8") as f:
                    f.write(f"## {world.day}번째 날: 서버가 응답하지 않아 중단됨 (이 날의 기록은 온전하지 않다)\n\n")
                raise SystemExit(f"{world.day}번째 날 도중 중단: {exc}\n"
                                 + (f"이어서 하려면: --resume {last}" if last else "완료된 날이 없다: 처음부터 다시 시작"))
            lived += 1
            print(f"{s['day']}번째 날({s['season']}): 생존 {s['alive']}, 사건 {len(s['events'])}, 지은 것 {s['structures']}, "
                  f"심은 곳 {s['plantings']}, 누출 {len(s['leaks'])}명, {time.time() - day_started:.0f}s", flush=True)
            if s["alive"] == 0:
                print(f"{s['day']}번째 날에 마지막 사람이 죽었다. 이 세계는 여기서 끝난다.", flush=True)
                break
    finally:
        recording.stop_run()
    print(f"총 {time.time() - started:.0f}s")
    return world.config.talent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="0 = until nobody is left alive")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument("--forever", action="store_true", help="when a world ends, start a new one with the next seed")
    parser.add_argument("--talent", choices=["on", "off", "pair"], default="on",
                        help="pair: every seed once with talent and once without, to compare the two worlds")
    # models and servers (default: engine/config.py). On a rented GPU, e.g. --backend openai --host http://<pod>:8000
    parser.add_argument("--backend", choices=["ollama", "openai"], default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--model", default=None, help="the people's model")
    parser.add_argument("--clerk-model", default=None)
    parser.add_argument("--clerk-host", default=None)
    parser.add_argument("--clerk-backend", choices=["ollama", "openai"], default=None)
    parser.add_argument("--concurrency", type=int, default=None, help="requests sent at once")
    args = parser.parse_args()
    models = {key: value for key, value in {
        "llm_backend": args.backend, "llm_host": args.host, "llm_model": args.model, "clerk_model": args.clerk_model,
        "clerk_host": args.clerk_host, "clerk_backend": args.clerk_backend, "llm_concurrency": args.concurrency,
    }.items() if value is not None}
    seed, resume = args.seed, args.resume
    while True:
        if resume:
            had_talent = run_world(seed, args.days, resume, models)
            # a pair interrupted during its talent half still owes the world without talent
            conditions = [False] if args.talent == "pair" and had_talent else []
            resume = None
        else:
            conditions = [True, False] if args.talent == "pair" else [args.talent == "on"]
        for talent_on in conditions:
            run_world(seed, args.days, None, models, talent_on)
        if not args.forever:
            break
        seed += 1


if __name__ == "__main__":
    main()
