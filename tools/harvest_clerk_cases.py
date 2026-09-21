"""Every clerk answer recorded in primal runs, with what the clerk was shown and what code finds wrong with it.

The runs make the cases; nobody writes them. Answers with no problems are kept too: they are the candidates for a
clerk's training data once checked, and a model that newly breaks them has regressed.

  python -m tools.harvest_clerk_cases [runs/<run> ...]      (default: every runs/*primal_seed* folder)
  -> data/clerk_cases/harvested.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import ValidationError

from engine.primal.clerk import SpokenPlan
from tools.clerk_checks import problems
from tools.plan_sameness import read_jsonl

OUT = Path("data/clerk_cases/harvested.jsonl")
_HEAD = re.compile(r"아래는 (.+?)이\(가\) (지금 이 순간에 한 말|오늘 하루 계획으로 한 말)입니다")
_CAMP = re.compile(r"해 질 녘에 (.+?)로 돌아와")


def _listed(line: str) -> list[str]:
    return [] if line.strip() in ("", "(없음)") else line.strip().split(", ")


def parse_clerk_prompt(prompt: str) -> dict | None:
    """What the clerk was shown, read back out of the recorded prompt."""
    head = _HEAD.search(prompt)
    if head is None:
        return None
    name = head.group(1)
    try:
        text = prompt.split(f'{name}의 말: """', 1)[1].rsplit('"""', 1)[0]
        block = prompt.split(f"{name}이(가) 지니고 있는 물건:\n", 1)[1].split("\n알려진 사람:", 1)[0]
        names = re.search(r"^알려진 사람: (.*)$", prompt, re.M).group(1)
        places = re.search(r"^알려진 장소: (.*)$", prompt, re.M).group(1)
    except (IndexError, AttributeError):
        return None
    carried = [] if block.strip() == "(없음)" else [re.sub(r"^\d+\. ", "", line) for line in block.splitlines() if line.strip()]
    camp = _CAMP.search(prompt)
    return {"name": name, "reaction": head.group(2).startswith("지금"), "text": text, "carried": carried,
            "names": _listed(names), "places": _listed(places), "camp": camp.group(1) if camp else ""}


def harvest(run_dirs: list[Path]) -> list[dict]:
    cases: dict[str, dict] = {}
    for run in run_dirs:
        tries_by_prompt: dict[str, list[dict]] = defaultdict(list)
        for row in read_jsonl(run / "llm_calls.jsonl"):
            if row.get("label", "").startswith("clerk:"):
                tries_by_prompt[row["prompt"]].append(row)
        for prompt, tries in tries_by_prompt.items():
            fields = parse_clerk_prompt(prompt)
            if fields is None:
                continue
            final = next((r for r in tries if r["ok"]), tries[-1])
            raw = final.get("raw_response")
            spoken = None
            if raw:
                try:
                    spoken = SpokenPlan.model_validate_json(raw)
                except ValidationError:
                    spoken = SpokenPlan.salvage(raw)
            steps = [s.to_step() for s in spoken.steps] if spoken is not None else None
            key = json.dumps([fields["text"], fields["carried"], fields["names"], fields["places"]], ensure_ascii=False)
            usage = final.get("usage") or {}
            cases[key] = {
                "source_run": run.name, "t": final["t"], **fields, "answered_by": usage.get("model"),
                "attempts": len(tries), "cut_off": bool(usage.get("salvaged")) or (spoken is not None and not final["ok"]),
                "raw": raw, "steps": [s.model_dump(exclude_defaults=True) for s in steps] if steps is not None else None,
                "problems": problems(fields["text"], steps, len(fields["carried"]), fields["names"], fields["places"], fields["camp"]),
            }
    return sorted(cases.values(), key=lambda c: c["t"])


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    runs = [Path(a) for a in args] or sorted(p for p in Path("runs").glob("*primal_seed*") if p.is_dir())
    cases = harvest(runs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    counts = Counter(p for c in cases for p in c["problems"])
    clean = sum(1 for c in cases if not c["problems"])
    print(f"{len(runs)} runs -> {len(cases)} clerk answers, {clean} with no problem found -> {OUT}")
    for problem, n in counts.most_common():
        print(f"  {problem}: {n}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
