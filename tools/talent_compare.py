"""Worlds with and without talent, side by side: do people drift toward the work their hands are good at?

Nothing in the engine assigns work. If talent matters to how people live, in a world with talent a person's share of
work in a family should rise with their (hidden) ceiling in it. A world without talent is the check: there everyone is
average, so the talent they WOULD have had from the same seed (talent.draw) should say nothing about what they do.

    python tools/talent_compare.py runs/<seed6 folder> runs/<seed6_notalent folder> [more folders...]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.primal.talent import FAMILY, SPREAD, draw  # noqa: E402

# the work people choose; eating, drinking and picking things up are done by everyone every day
WORK = {op for op in FAMILY if op not in ("eat", "drink", "pick", "fill", "attack", "train")}
MIN_ACTS = 5   # in the first 18-day worlds only two people did ten pieces of work in half a world


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


def meta(run: Path) -> dict:
    found = rows(run, "meta")
    return found[0] if found else {}


def work_by_person(run: Path, first_day: int = 0, last_day: int = 10 ** 9) -> dict[str, Counter]:
    work: dict[str, Counter] = defaultdict(Counter)
    for a in rows(run, "actions"):
        if first_day <= a["day"] <= last_day and a["step"]["op"] in WORK and a["ok"]:
            work[a["person"]][FAMILY[a["step"]["op"]]] += 1
    for c in rows(run, "contests"):   # hunts are written there, not as actions
        if c.get("kind") == "hunt" and first_day <= c["day"] <= last_day:
            for hunter in c.get("hunters", []):
                work[hunter]["perceive"] += 1
    return work


def correlation(xs: list[float], ys: list[float]) -> str:
    if len(xs) < 5 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return f"-(n={len(xs)})"
    return f"{statistics.correlation(xs, ys):+.2f}(n={len(xs)})"


def summary(run: Path, min_acts: int) -> dict[str, str]:
    info = meta(run)
    seed = info.get("seed")
    with_talent = info.get("config", {}).get("talent", True)
    days = rows(run, "days")
    last_day = days[-1]["day"] if days else 0
    out = {"폴더": run.name, "재능": "켬" if with_talent else "끔(자리값 비교)", "날": str(last_day),
           "마지막 생존": str(days[-1]["alive"]) if days else "-"}
    periods = {"전체": (0, last_day), "전반": (0, last_day // 2), "후반": (last_day // 2 + 1, last_day)}
    for label, (a, b) in periods.items():
        work = {p: c for p, c in work_by_person(run, a, b).items() if sum(c.values()) >= min_acts}
        # how much each person's work is concentrated in one family (1 = only one, 0.25 = evenly spread)
        hhi = [sum((n / sum(c.values())) ** 2 for n in c.values()) for c in work.values()]
        out[f"{label} 쏠림"] = f"{statistics.mean(hhi):.2f}(n={len(hhi)})" if hhi else "-"
        for family in SPREAD:
            ceilings = [draw(seed, p)[family]["ceiling"] for p in work]
            shares = [c[family] / sum(c.values()) for c in work.values()]
            out[f"{label} {family} 한계↔비중"] = correlation(ceilings, shares)
    sharp = [max(m["props"].get("sharpness", 0.0) for m in a["made"]) for a in rows(run, "actions")
             if a["step"]["op"] == "strike" and a.get("made")]
    out["치기 날카로움 평균"] = f"{statistics.mean(sharp):.2f}(n={len(sharp)})" if sharp else "-"
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--min-acts", type=int, default=MIN_ACTS, help="work done in the period to be counted")
    args = parser.parse_args()
    table = [summary(run, args.min_acts) for run in args.runs]
    keys = list(dict.fromkeys(k for t in table for k in t))
    print("| 항목 | " + " | ".join(t["폴더"] for t in table) + " |")
    print("|---" * (len(table) + 1) + "|")
    for key in keys[1:]:
        print(f"| {key} | " + " | ".join(t.get(key, "-") for t in table) + " |")
    print(f"\n한계↔비중: 그 기간에 {args.min_acts}번 이상 일한 사람의 숨은 한계와 그 묶음 일의 비중 사이 상관. 재능을 끈 세계에서는 같은 씨앗으로 뽑았을 값을 쓰므로 0 근처가 정상.")


if __name__ == "__main__":
    main()
