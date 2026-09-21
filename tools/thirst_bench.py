"""Does a mind put water first when its body says it is parched? The same recorded mornings, asked of other models.

In the overnight worlds (seed 6-9) nearly everyone who died of thirst had "목이 타들어 가고 혀가 입천장에 붙는다" as the
first thing their morning prompt said they felt, and 47% of those mornings the 8B planned no water at all. Whether that is
the model or the structure can be told apart on exactly those prompts: a model that heeds the body plans water first.

Mornings are chosen by what the prompt says, never by how the person's life ended: every morning of those worlds whose
first felt line is the worst thirst. The recorded 8B plans for the same mornings are the baseline.

  python -m tools.thirst_bench --backend openai --host https://<pod>-8000.proxy.runpod.net --models Qwen/Qwen3.8-27B-FP8
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

from engine import llm_agent
from engine import recorder as recording
from engine.primal.prompts import DayDeclaration
from tools.bench_models import model_config
from tools.plan_sameness import read_jsonl

WORLDS = ["20260915-033616_primal_seed6", "20260915-044247_primal_seed6_notalent", "20260915-055029_primal_seed7",
          "20260915-065840_primal_seed7_notalent", "20260915-080627_primal_seed8", "20260915-091052_primal_seed8_notalent",
          "20260915-101354_primal_seed9", "20260915-112611_primal_seed9_notalent"]
BASELINE = "qwen3:8b (기록된 답)"
_DAY = re.compile(r"오늘은 (\d+)번째 날입니다")
_SELF = re.compile(r"당신은 (P\d{2})입니다")
PARCHED = "목이 타들어"
# "물을 구하고" was missed at first: read back, several Qwen plans the judge called waterless went looking for water
WATER = re.compile(r"마시|마신|마셔|목을 축|목을 적|갈증|물을 길|물을 뜨|물을 떠|물을 구|물을 찾|물가|개울|호수|큰 강|강 여울|강물|물부터")
DRINK = re.compile(r"마시|마신|마셔|목을 축|목을 적")
OTHER_WORK = re.compile(r"불|부싯돌|강돌|조각|짓|나뭇가지|칡|열매|사냥|물고기")


def first_felt(prompt: str) -> str:
    line = next((l for l in prompt.splitlines() if "지금 몸과 마음에 오는 것" in l), "")
    return line.split(":", 1)[-1].split(" / ")[0]


def judge(plan: str) -> dict[str, bool]:
    water, other = WATER.search(plan), OTHER_WORK.search(plan)
    return {"water": bool(water), "drink": bool(DRINK.search(plan)),
            "water_first": bool(water) and (other is None or water.start() < other.start())}


def parched_mornings(runs: list[Path], limit: int, seed: int = 0) -> list[dict]:
    mornings = []
    for run in runs:
        plans = {(p["person"], p["day"]): p for p in read_jsonl(run / "plans.jsonl")}
        seen = set()
        for row in read_jsonl(run / "llm_calls.jsonl"):
            if not str(row.get("label", "")).startswith("plan:") or not row.get("ok"):
                continue
            day, person = _DAY.search(row["prompt"]), _SELF.search(row["prompt"])
            if not day or not person or PARCHED not in first_felt(row["prompt"]):
                continue
            key = (person.group(1), int(day.group(1)))
            if key in seen or key not in plans:
                continue
            seen.add(key)
            mornings.append({"world": run.name, "person": key[0], "day": key[1], "prompt": row["prompt"],
                             "temperature": row["temperature"], "recorded": plans[key]["plan"]})
    random.Random(seed).shuffle(mornings)
    return mornings[:limit]


def rates(plans: list[str]) -> dict:
    judged = [judge(p) for p in plans]
    n = len(judged) or 1
    return {"answered": len(judged), **{k: round(sum(j[k] for j in judged) / n, 3) for k in ("water", "drink", "water_first")}}


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="openai", choices=["ollama", "openai"])
    parser.add_argument("--host", required=True)
    parser.add_argument("--models", required=True, help="comma-separated; name@host for a model on another address")
    parser.add_argument("--runs", default=",".join(WORLDS))
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args(argv)

    runs = [Path("runs") / r if not Path(r).exists() else Path(r) for r in args.runs.split(",")]
    mornings = parched_mornings(runs, args.limit)
    run = recording.start_run("thirst_bench", {"models": args.models, "mornings": len(mornings), "runs": args.runs})
    report = {"mornings": len(mornings), "results": {BASELINE: rates([m["recorded"] for m in mornings])}}
    try:
        for spec in [s for s in args.models.split(",") if s]:
            config = model_config(spec, args.backend, args.host, args.concurrency, 8192)
            started = time.perf_counter()
            answers = llm_agent.run_concurrently(
                [lambda m=m: llm_agent.call_llm_decision(m["prompt"], DayDeclaration, config, temperature=m["temperature"],
                                                         label=f"thirst:{m['person']}") for m in mornings], config)
            plans = []
            for m, a in zip(mornings, answers):
                if a is not None and a.plan.strip():
                    plans.append(a.plan)
                    run.write("thirst_plans", {"model": spec, "world": m["world"], "person": m["person"], "day": m["day"],
                                               "plan": a.plan, "reasoning": a.reasoning, "recorded": m["recorded"], **judge(a.plan)})
            report["results"][spec] = {**rates(plans), "seconds": round(time.perf_counter() - started, 1)}
    finally:
        recording.stop_run()
    (run.root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 목이 타는 아침 {report['mornings']}번", "", "| 모델 | 답 | 물 언급 | 마시기 언급 | 물이 다른 일보다 먼저 |", "|---|---|---|---|---|"]
    for model, r in report["results"].items():
        lines.append(f"| {model} | {r['answered']} | {r['water']:.0%} | {r['drink']:.0%} | {r['water_first']:.0%} |")
    (run.root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return run.root


if __name__ == "__main__":
    main()
