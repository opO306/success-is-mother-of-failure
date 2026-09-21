"""After each model has been benched on its own server (tools/bench_models.py): one yardstick across all of them.

  contests      every agent plan is transcribed by ONE clerk, the same for every model, in the situation it was written
                in, and plans with a 사람공격 (attack) or 몰래가져가기 (steal) step are counted. A measure of what each model
                chooses in the same mornings, never a target: a model near zero where the others are not is avoiding
                the choice, which would quietly make a world where crime is free a peaceful one.
  side by side  the same person's plan on the same morning from every model, for a person to read. Whether the Korean
                sounds like someone, and whether the reasons are a person's, is not something code can score.

  python -m tools.bench_compare runs/<bench1> runs/<bench2> ... --clerk <model>@http://<pod>:8000 --backend openai
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine import llm_agent
from engine import recorder as recording
from engine.config import SimulationConfig
from engine.primal import clerk
from tools.bench_models import BASELINE, model_config
from tools.plan_sameness import read_jsonl

CONTESTS = ("attack", "steal")


def load_plans(bench_dirs: list[Path]) -> dict[str, list[dict]]:
    """Plans by model. Each model, and the recorded run's plans that every bench carries, come from the first bench
    that has them."""
    by_spec: dict[str, list[dict]] = {}
    for bench in bench_dirs:
        found: dict[str, list[dict]] = {}
        for row in read_jsonl(bench / "agent_plans.jsonl"):
            found.setdefault(row["spec"], []).append(row)
        for spec, rows in found.items():
            by_spec.setdefault(spec, rows)
    return by_spec


def count_contests(by_spec: dict[str, list[dict]], config: SimulationConfig, examples: int = 3) -> dict:
    rows = [(spec, row) for spec, spec_rows in by_spec.items() for row in spec_rows if row.get("context")]
    plans = llm_agent.run_concurrently(
        [lambda r=r: clerk.transcribe(r["context"]["name"], r["plan"], r["context"]["carried"], r["context"]["names"],
                                      r["context"]["places"], r["context"]["camp"], config)
         for _, r in rows], config,
    )
    result = {spec: {"plans": len(spec_rows), "transcribed": 0, **{op: 0 for op in CONTESTS}, "either": 0, "examples": []}
              for spec, spec_rows in by_spec.items()}
    for (spec, row), plan in zip(rows, plans):
        if plan is None:
            continue
        counted = result[spec]
        counted["transcribed"] += 1
        # the steps a real day would have kept from this answer
        ops = {step.op for step in clerk.keep_said(plan.steps, row["plan"])}
        for op in CONTESTS:
            counted[op] += op in ops
        if ops & set(CONTESTS):
            counted["either"] += 1
            if len(counted["examples"]) < examples:
                counted["examples"].append(f"{row['day']}일 {row['person']}: {row['plan']}")
    for counted in result.values():
        counted["share"] = round(counted["either"] / counted["transcribed"], 3) if counted["transcribed"] else None
    return result


def side_by_side(by_spec: dict[str, list[dict]], count: int) -> list[dict]:
    """Mornings every model answered, spread evenly over them."""
    keyed = {spec: {(r["day"], r["person"]): r for r in rows} for spec, rows in by_spec.items()}
    common = sorted(set.intersection(*(set(k) for k in keyed.values()))) if keyed else []
    picked = common[::max(1, len(common) // max(1, count))][:count]
    return [{"day": day, "person": person,
             "plans": {spec: {"plan": keyed[spec][(day, person)]["plan"], "reasoning": keyed[spec][(day, person)].get("reasoning", "")}
                       for spec in keyed}}
            for day, person in picked]


def markdown(report: dict) -> str:
    lines = ["# 모델 비교: 같은 서기로 잰 공격·도둑질, 같은 아침의 계획", "", f"서기: {report['clerk']}", "",
             "## 공격·도둑질이 든 계획", "",
             "높을수록 좋다는 뜻이 아니다. 같은 아침들에서 다른 모델은 고르는데 한 모델만 0에 가깝다면, 그 모델이 이 선택을 피한다는 신호다.", "",
             "| 모델 | 옮겨진 계획 | 사람공격 | 몰래가져가기 | 둘 중 하나라도 | 비율 |", "|---|---|---|---|---|---|"]
    for spec, c in report["contests"].items():
        lines.append(f"| {spec} | {c['transcribed']}/{c['plans']} | {c['attack']} | {c['steal']} | {c['either']} | {c['share']} |")
    for spec, c in report["contests"].items():
        if c["examples"]:
            lines += ["", f"**{spec}**"] + [f"- {text}" for text in c["examples"]]
    lines += ["", "## 같은 사람, 같은 아침"]
    for sample in report["side_by_side"]:
        lines += ["", f"### {sample['day']}일 {sample['person']}"]
        for spec, p in sample["plans"].items():
            lines += [f"- **{spec}**: {p['plan']}", f"  - 이유: {p['reasoning']}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("benches", nargs="+", help="runs/<stamp>_bench folders made by tools.bench_models")
    parser.add_argument("--clerk", required=True, help="the one clerk every model's plans are transcribed by: model[@host]")
    parser.add_argument("--backend", default="ollama", choices=["ollama", "openai"])
    parser.add_argument("--host", default=SimulationConfig().llm_host)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--samples", type=int, default=8, help="mornings shown side by side")
    args = parser.parse_args(argv)
    by_spec = load_plans([Path(b) for b in args.benches])
    config = model_config(args.clerk, args.backend, args.host, args.concurrency, args.num_ctx)
    run = recording.start_run("bench_compare", {"args": vars(args), "plans": {spec: len(rows) for spec, rows in by_spec.items()}})
    try:
        contests = count_contests(by_spec, config)
    finally:
        recording.stop_run()
    report = {"clerk": args.clerk, "benches": args.benches, "contests": contests, "side_by_side": side_by_side(by_spec, args.samples)}
    (run.root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (run.root / "report.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return run.root


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
