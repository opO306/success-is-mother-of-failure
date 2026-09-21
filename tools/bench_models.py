"""Compare models for the two LLM roles on a rented GPU, on this project's own measures, before a simulation.

  clerk  the fixed sheet (tools/clerk_sheet.py) through the real pipeline, and real answers harvested from runs
         (tools/harvest_clerk_cases.py) asked again and checked by code (tools/clerk_checks.py)
  agent  morning prompts recorded in a run, asked again with each person's own temperature: how alike the plans are
         (tools/plan_sameness.py), leak words, length, failures. This is one morning's answer to the same situation;
         how a world would unfold on that model only a run can show.

Every call is recorded under runs/<stamp>_bench/, with report.json and report.md. Every agent plan, and the recorded
run's own plans for the same mornings, go to agent_plans.jsonl with the situation they were written in, so that
tools/bench_compare.py can later measure all models with one clerk.

Example, vLLM serving an OpenAI-compatible API on the rented machine:
  python -m tools.harvest_clerk_cases
  python -m tools.bench_models --backend openai --host http://<pod>:8000 --concurrency 16 \
      --clerk-models Qwen/Qwen3-32B --agent-models Qwen/Qwen3-32B --plans-from runs/20260914-212324_primal_seed0
A vLLM server serves one model; for several, give each its own address: --clerk-models name@http://<pod>:8001,other@http://<pod>:8002
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

from engine import llm_agent
from engine import recorder as recording
from engine.config import SimulationConfig
from engine.primal import leak
from engine.primal.clerk import ask_clerk
from engine.primal.prompts import DayDeclaration
from tools.clerk_checks import problems
from tools.clerk_sheet import run_sheet
from tools.harvest_clerk_cases import parse_clerk_prompt
from tools.plan_sameness import read_jsonl, sameness

_DAY = re.compile(r"오늘은 (\d+)번째 날입니다")
_SELF = re.compile(r"당신은 (P\d{2})입니다")
_PERSON = re.compile(r"P\d{2}")
_HERE = re.compile(r"^- 지금 있는 곳: (.+)$", re.M)
_HERE_PEOPLE = re.compile(r"^- 이곳에 있는 사람: (.*)$", re.M)
_STRANGER = re.compile(r"처음 보는 사람 (P\d{2})")
_CAMP = re.compile(r"이 무리와 함께 (.+?)에서 지낸다")
BASELINE = "(기록된 실행의 답)"


def model_config(spec: str, backend: str, host: str, concurrency: int, num_ctx: int) -> SimulationConfig:
    model, _, own_host = spec.partition("@")
    return dataclasses.replace(SimulationConfig(), llm_backend=backend, llm_host=own_host or host, llm_model=model,
                               llm_concurrency=concurrency, llm_num_ctx=num_ctx)


def load_cases(path: Path, limit: int) -> list[dict]:
    cases = read_jsonl(path)
    cases.sort(key=lambda c: (not c["problems"], c["t"]))  # the answers that went wrong first
    return cases[:limit]


def bench_clerk(config: SimulationConfig, cases: list[dict], sheet_limit: int | None = None, sheet_repeats: int = 1) -> dict:
    # Temperature 0 is not bit-exact when a server batches requests together: the same sentence scored OK in one check
    # and BAD in the next on the same 8B. A single pass can differ by a case or two, so the sheet can be run several times.
    sheets = [run_sheet(config, sheet_limit) for _ in range(max(1, sheet_repeats))]
    sheet = sheets[0]
    started = time.perf_counter()
    answers = llm_agent.run_concurrently(
        [lambda c=c: ask_clerk(c["name"], c["text"], c["carried"], c["names"], c["places"], c["camp"], config, c.get("reaction", False))
         for c in cases], config,
    )
    now, before, clean = {}, {}, 0
    for case, answer in zip(cases, answers):
        steps = [s.to_step() for s in answer.steps] if answer is not None else None
        found = problems(case["text"], steps, len(case["carried"]), case["names"], case["places"], case["camp"])
        clean += not found
        for p in found:
            now[p] = now.get(p, 0) + 1
        for p in case["problems"]:
            before[p] = before.get(p, 0) + 1
    return {
        "sheet": {k: v for k, v in sheet.items() if k != "cases"},
        "sheet_passed_each": [s["passed"] for s in sheets],
        "sheet_held_passed_each": [s["held_passed"] for s in sheets],
        "sheet_failed": [c["label"] for c in sheet["cases"] if not c["ok"]],
        "sheet_unsteady": sorted({c["label"] for s in sheets for c in s["cases"]} - {
            c["label"] for c in sheet["cases"] if all(x["ok"] == c["ok"] for s in sheets for x in s["cases"] if x["label"] == c["label"])}),
        "harvested": {"cases": len(cases), "clean": clean, "problems": now, "recorded_answer_problems": before,
                      "seconds": round(time.perf_counter() - started, 1)},
    }


def morning_context(prompt: str) -> dict:
    """What the clerk would have been shown that morning, read back out of the recorded plan prompt, so every model's
    plan can be transcribed against the situation it was written in. People known only from memories that fell out of
    the prompt's window are missing: the clerk is shown a little less than the world knew."""
    name = _SELF.search(prompt).group(1)
    carried, places = [], []
    if "지니고 있는 것:\n" in prompt:
        block = prompt.split("지니고 있는 것:\n", 1)[1].split("\n\n", 1)[0]
        carried = [re.sub(r"^\d+\. ", "", line) for line in block.splitlines() if line.strip()]
    if "걸리는 시간(칸):\n" in prompt:
        block = prompt.split("걸리는 시간(칸):\n", 1)[1].split("\n\n", 1)[0]
        places = [line[2:].rsplit(": ", 1)[0] for line in block.splitlines() if line.startswith("- ")]
    here = _HERE.search(prompt)
    if here:
        places.append(here.group(1))
    # "처음 보는 사람" in the list of who is here means not yet known; in a memory it is the moment they became known
    here_people = _HERE_PEOPLE.search(prompt)
    strangers = set(_STRANGER.findall(here_people.group(1))) if here_people else set()
    camp = _CAMP.search(prompt)
    return {"name": name, "carried": carried, "names": sorted(set(_PERSON.findall(prompt)) - strangers - {name}),
            "places": sorted(set(places)), "camp": camp.group(1) if camp else ""}


def recorded_mornings(run_dir: Path, days: set[int]) -> list[dict]:
    rows = read_jsonl(run_dir / "llm_calls.jsonl")
    # The morning prompt keeps only recent memories: in the last local run 184 of 310 mornings no longer said which camp
    # the person lives at, and 91 missed people they knew. The clerk prompts of the same run still show both, and
    # nobody is ever forgotten, so the people known at an earlier clerk call were known that morning too.
    shown: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for row in rows:
        if row.get("label", "").startswith("clerk:"):
            fields = parse_clerk_prompt(row["prompt"])
            if fields is not None:
                shown[fields["name"]].append((row["t"], fields))
    mornings: dict[str, dict] = {}
    for row in rows:
        if not row.get("label", "").startswith("plan:"):
            continue
        day = _DAY.search(row["prompt"])
        if day and int(day.group(1)) in days and row["prompt"] not in mornings:
            context = morning_context(row["prompt"])
            before = [fields for t, fields in shown.get(context["name"], []) if t <= row["t"]]
            context["names"] = sorted(set(context["names"]).union(*(fields["names"] for fields in before)))
            context["camp"] = context["camp"] or next((f["camp"] for _, f in shown.get(context["name"], []) if f["camp"]), "")
            mornings[row["prompt"]] = {"person": row["label"].split(":", 1)[1], "day": int(day.group(1)),
                                       "prompt": row["prompt"], "temperature": row["temperature"], "context": context}
    return list(mornings.values())


def bench_agent(config: SimulationConfig, mornings: list[dict]) -> dict:
    started = time.perf_counter()
    answers = llm_agent.run_concurrently(
        [lambda m=m: llm_agent.call_llm_decision(m["prompt"], DayDeclaration, config, temperature=m["temperature"],
                                                 label=f"bench-plan:{m['person']}") for m in mornings], config,
    )
    plans = [{"day": m["day"], "person": m["person"], "plan": a.plan, "reasoning": a.reasoning, "context": m.get("context")}
             for m, a in zip(mornings, answers) if a is not None and a.plan.strip()]
    leaking = sum(1 for a in answers if a is not None and any(leak.words_in(a.plan + " " + a.reasoning).values()))
    return {"asked": len(mornings), "answered": len(plans), "sameness": sameness(plans)["overall"], "plans_with_leak_words": leaking,
            "mean_chars": round(statistics.mean(len(p["plan"]) for p in plans), 1) if plans else None,
            "seconds": round(time.perf_counter() - started, 1), "plans": plans}


def throughput(run_root: Path, since: float, until: float) -> dict:
    rows = [r for r in read_jsonl(run_root / "llm_calls.jsonl") if since <= r["t"] <= until]
    tokens = sum((r.get("usage") or {}).get("output_tokens") or 0 for r in rows if r["ok"])
    return {"calls": sum(r["ok"] for r in rows), "failed_attempts": sum(not r["ok"] for r in rows), "output_tokens": tokens,
            "output_tokens_per_s": round(tokens / max(1e-9, until - since), 1)}


def markdown(report: dict) -> str:
    lines = ["# 모델 비교", "", "## 서기", "",
             "| 모델 | 시험지 | 처음 보는 문장 | 실제 답에서 문제 없음 | 문제 종류 | 출력 토큰/초 |", "|---|---|---|---|---|---|"]
    for spec, r in report["clerk"].items():
        s, h, tp = r["sheet"], r["harvested"], r.get("throughput", {})
        each, held = r.get("sheet_passed_each", [s["passed"]]), r.get("sheet_held_passed_each", [s["held_passed"]])
        passed = f"{min(each)}~{max(each)}" if min(each) != max(each) else f"{each[0]}"
        held_passed = f"{min(held)}~{max(held)}" if min(held) != max(held) else f"{held[0]}"
        lines.append(f"| {spec} | {passed}/{s['total']} | {held_passed}/{s['held_total']} | {h['clean']}/{h['cases']} "
                     f"| {h['problems']} | {tp.get('output_tokens_per_s', '')} |")
    lines += ["", "## 에이전트 (같은 아침에 다시 물음)", "",
              "| 모델 | 답 | 사람 사이 유사도 | 어제와 유사도 | 서로 다른 조각 | 누출 단어가 있는 계획 | 평균 길이 | 출력 토큰/초 |",
              "|---|---|---|---|---|---|---|---|"]
    for spec, r in report["agent"].items():
        sm, tp = r["sameness"], r.get("throughput", {})
        lines.append(f"| {spec} | {r['answered']} | {sm.get('between_people')} | {sm.get('same_person_vs_yesterday')} "
                     f"| {sm.get('distinct_3grams')} | {r.get('plans_with_leak_words', '')} | {r.get('mean_chars', '')} "
                     f"| {tp.get('output_tokens_per_s', '')} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="ollama", choices=["ollama", "openai"])
    parser.add_argument("--host", default=SimulationConfig().llm_host)
    parser.add_argument("--clerk-models", default="")
    parser.add_argument("--agent-models", default="")
    parser.add_argument("--plans-from", default=None, help="a primal run whose recorded mornings are asked again")
    parser.add_argument("--plan-days", default="1,2,3")
    parser.add_argument("--cases", default="data/clerk_cases/harvested.jsonl")
    parser.add_argument("--case-limit", type=int, default=200)
    parser.add_argument("--sheet-limit", type=int, default=None)
    parser.add_argument("--sheet-repeats", type=int, default=3, help="the sheet is run this many times; the report shows the range")
    parser.add_argument("--morning-limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--num-ctx", type=int, default=8192)
    args = parser.parse_args(argv)
    days = {int(d) for d in args.plan_days.split(",") if d}
    clerk_specs = [s for s in args.clerk_models.split(",") if s]
    agent_specs = [s for s in args.agent_models.split(",") if s]
    cases = load_cases(Path(args.cases), args.case_limit)
    mornings = recorded_mornings(Path(args.plans_from), days)[: args.morning_limit] if args.plans_from and agent_specs else []
    run = recording.start_run("bench", {"args": vars(args), "cases": len(cases), "mornings": len(mornings)})
    report: dict = {"args": vars(args), "clerk": {}, "agent": {}}
    windows = []
    try:
        for spec in clerk_specs:
            config = model_config(spec, args.backend, args.host, args.concurrency, args.num_ctx)
            since = time.time()
            report["clerk"][spec] = bench_clerk(config, cases, args.sheet_limit, args.sheet_repeats)
            windows.append(("clerk", spec, since, time.time()))
            print(f"clerk {spec}: {report['clerk'][spec]['sheet']} {report['clerk'][spec]['harvested']}", flush=True)
        if mornings:
            by_key = {(m["day"], m["person"]): m for m in mornings}
            recorded = [p for p in read_jsonl(Path(args.plans_from) / "plans.jsonl") if (p["day"], p["person"]) in by_key]
            report["agent"][BASELINE] = {"answered": len(recorded), "sameness": sameness(recorded)["overall"]}
            for p in recorded:
                run.write("agent_plans", {"spec": BASELINE, "day": p["day"], "person": p["person"], "plan": p["plan"],
                                          "reasoning": p.get("reasoning", ""), "context": by_key[(p["day"], p["person"])]["context"]})
        for spec in agent_specs:
            config = model_config(spec, args.backend, args.host, args.concurrency, args.num_ctx)
            since = time.time()
            report["agent"][spec] = bench_agent(config, mornings)
            windows.append(("agent", spec, since, time.time()))
            for plan in report["agent"][spec].pop("plans"):
                run.write("agent_plans", {"spec": spec, **plan})
            print(f"agent {spec}: {report['agent'][spec]}", flush=True)
    finally:
        recording.stop_run()
    for kind, spec, since, until in windows:
        report[kind][spec]["throughput"] = throughput(run.root, since, until)
    (run.root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (run.root / "report.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return run.root


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
