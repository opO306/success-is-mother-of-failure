"""How fast can a served model live primal days? Recorded morning prompts sent at several concurrency levels.

A world day costs almost nothing but model writing: 2.09 calls per living person-day and about 375 output tokens a
call (runs/20260915-065840_primal_seed7_notalent, qwen3:8b on the local 4060: 58 tokens/s, a 45-person day ~10 min).
This measures output tokens per second on a server and turns it into minutes per world day and hours per generation
(600 days, 45 people), both for the answer lengths the model really wrote and for the recorded 375.

  python -m tools.throughput_bench --host https://<pod>-8000.proxy.runpod.net --model Qwen/Qwen3-8B --levels 16,45,64
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import time
from pathlib import Path

from engine import llm_agent
from engine import recorder as recording
from engine.primal.prompts import DayDeclaration
from tools.bench_models import model_config
from tools.plan_sameness import read_jsonl

CALLS_PER_PERSON_DAY = 2.09
RECORDED_TOKENS_PER_CALL = 375
PEOPLE = 45
GENERATION_DAYS = 600


def recorded_prompts(run: Path, n: int) -> list[dict]:
    rows = [r for r in read_jsonl(run / "llm_calls.jsonl") if str(r.get("label", "")).startswith("plan:") and r.get("ok")]
    return rows[:n]


def projection(tokens_per_second: float, tokens_per_call: float) -> dict:
    day_seconds = PEOPLE * CALLS_PER_PERSON_DAY * tokens_per_call / tokens_per_second
    return {"minutes_per_day": round(day_seconds / 60, 2), "hours_per_generation": round(day_seconds * GENERATION_DAYS / 3600, 1)}


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="openai", choices=["ollama", "openai"])
    parser.add_argument("--host", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--levels", default="16,45,64", help="requests sent at once")
    parser.add_argument("--from-run", default="runs/20260915-065840_primal_seed7_notalent")
    # Without a cap, a JSON-constrained answer can run on for thousands of tokens and hold a slot for minutes.
    parser.add_argument("--max-tokens", type=int, default=600)
    args = parser.parse_args(argv)

    levels = [int(x) for x in args.levels.split(",") if x]
    pool = recorded_prompts(Path(args.from_run), 2 * max(levels))
    run = recording.start_run("throughput_bench", {"model": args.model, "levels": levels, "prompts": len(pool)})
    report = {"model": args.model, "local_baseline": {"tokens_per_second": 58.0, **projection(58.0, RECORDED_TOKENS_PER_CALL)}, "levels": []}
    try:
        for level in levels:
            config = dataclasses.replace(model_config(args.model, args.backend, args.host, level, 8192), llm_max_output_tokens=args.max_tokens)
            batch = pool[: 2 * level]
            label = f"tp{level}"
            started = time.perf_counter()
            llm_agent.run_concurrently(
                [lambda r=r, i=i: llm_agent.call_llm_decision(r["prompt"], DayDeclaration, config, temperature=r["temperature"], label=f"{label}:{i}")
                 for i, r in enumerate(batch)], config)
            wall = time.perf_counter() - started
            calls = [c for c in read_jsonl(run.root / "llm_calls.jsonl") if str(c.get("label", "")).startswith(f"{label}:")]
            ok = [c for c in calls if c.get("ok")]
            tokens = [((c.get("usage") or {}).get("output_tokens") or 0) for c in ok]
            latencies = sorted(c.get("latency_s") or 0 for c in ok)
            tps = sum(tokens) / wall if wall else 0.0
            mean_tokens = statistics.mean(tokens) if tokens else 0.0
            report["levels"].append({
                "concurrency": level, "sent": len(batch), "ok": len(ok), "failed_attempts": len(calls) - len(ok),
                "wall_s": round(wall, 1), "output_tokens_per_s": round(tps, 1), "mean_output_tokens": round(mean_tokens),
                "latency_p50_s": round(latencies[len(latencies) // 2], 1) if latencies else None,
                "latency_max_s": round(latencies[-1], 1) if latencies else None,
                "at_its_own_lengths": projection(tps, mean_tokens) if tps else None,
                "at_recorded_lengths": projection(tps, RECORDED_TOKENS_PER_CALL) if tps else None,
            })
            print(json.dumps(report["levels"][-1], ensure_ascii=False), flush=True)
    finally:
        recording.stop_run()
    (run.root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return run.root


if __name__ == "__main__":
    main()
