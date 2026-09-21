"""How far apart people are in talent, in skill, and in what their hands actually produced.

Spread is SD / mean, the measure of Hunter, Schmidt & Judiesch (1990): about 19% in simple work, 32% in middling, 48% in
complex. The talent spread was set from those numbers; the outcome spread is what should be compared with them.

    python tools/talent_spread.py runs/<run folder> [--min-acts 3]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.primal.talent import FAMILY, SPREAD  # noqa: E402

STUDY = {"repeat": "19%", "body": "23%(시작 힘)", "perceive": "32%", "hand": "48%"}


def rows(run: Path, stream: str) -> list[dict]:
    path = run / f"{stream}.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def spread(values: list[float]) -> str:
    if len(values) < 3 or statistics.mean(values) <= 0:
        return f"(n={len(values)})"
    return f"{statistics.stdev(values) / statistics.mean(values):.0%} (n={len(values)})"


def outcomes(actions: list[dict], min_acts: int) -> dict[str, list[float]]:
    """Per person, the mean of what one act produced, grouped by what it was done to or gathered."""
    per: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for a in actions:
        op, made = a["step"]["op"], a.get("made") or []
        if op == "strike" and made:
            target = a["inputs"][1]["kind"] if len(a["inputs"]) >= 2 else "?"
            per[f"치기 날카로움 ({target})"][a["person"]].append(max(m["props"].get("sharpness", 0.0) for m in made))
        elif op in ("gather", "fish") and a["ok"]:
            kind = made[0]["kind"] if made else (a["step"].get("what") or "?")
            per[f"{'채집' if op == 'gather' else '물고기'} 개수 ({kind})"][a["person"]].append(float(len(made)))
    return {label: [statistics.mean(v) for v in people.values() if len(v) >= min_acts] for label, people in per.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--min-acts", type=int, default=3)
    args = parser.parse_args()

    talents = rows(args.run, "talent")
    print("## 재능 값 (숨김)")
    for family in SPREAD:
        ceilings = [r["talent"][family]["ceiling"] for r in talents]
        rates = [r["talent"][family]["rate"] for r in talents]
        print(f"- {family}: 한계 {spread(ceilings)}, 속도 {spread(rates)} | 연구 {STUDY[family]}")

    people = rows(args.run, "people")
    if people:
        last = people[-1]
        print(f"\n## 실력 ({last['day']}번째 날, {args.min_acts * 3}번 이상 한 사람)")
        by_op: dict[str, list[float]] = defaultdict(list)
        for p in last["people"].values():
            for op, value in p.get("skills", {}).items():
                if p.get("practice", {}).get(op, 0) >= args.min_acts * 3:
                    by_op[op].append(value)
        for op, values in sorted(by_op.items(), key=lambda kv: -len(kv[1])):
            print(f"- {op} [{FAMILY.get(op, '-')}]: {spread(values)}, 평균 {statistics.mean(values):.2f}")

    print(f"\n## 실제 결과 (한 번에 나온 양의 사람별 평균, {args.min_acts}번 이상 한 사람)")
    for label, values in sorted(outcomes(rows(args.run, "actions"), args.min_acts).items(), key=lambda kv: -len(kv[1])):
        print(f"- {label}: {spread(values)}")


if __name__ == "__main__":
    main()
