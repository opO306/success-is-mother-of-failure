"""How alike people's plans are: a measure, never a judge. Nothing here feeds back into any world.

  between_people            mean similarity of every pair of plans on the same day (1 = word for word the same)
  same_person_vs_yesterday  mean similarity of each person's plan to their own plan the day before
  distinct_3grams           share of different 3-character pieces among all pieces that day (higher = more varied)
  common_phrases            8-character pieces found in at least 30% of that day's plans

Similarity is the cosine of character 3-gram counts. Person names (P01...) are removed first: in the first real run
plans copied lists of 14 names, which would make them look alike for a reason that says nothing about their thinking.

  python -m tools.plan_sameness runs/<run>
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

_NAME = re.compile(r"P\d{2}")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a line still being written by a running world
    return rows


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _NAME.sub("", text)).strip()


def grams(text: str, n: int = 3) -> Counter:
    t = _clean(text)
    return Counter(t[i:i + n] for i in range(max(0, len(t) - n + 1)))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    return dot / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())))


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def sameness(plans: list[dict], phrase_len: int = 8, phrase_share: float = 0.3) -> dict:
    by_day: dict[int, dict[str, str]] = defaultdict(dict)
    for p in plans:
        if p.get("plan"):
            by_day[p["day"]][p["person"]] = p["plan"]
    days, previous = {}, {}
    for day in sorted(by_day):
        texts = by_day[day]
        counted = {person: grams(text) for person, text in texts.items()}
        people = sorted(counted)
        pairs = [cosine(counted[a], counted[b]) for i, a in enumerate(people) for b in people[i + 1:]]
        selves = [cosine(counted[p], previous[p]) for p in people if p in previous]
        pieces = Counter()
        for g in counted.values():
            pieces.update(g)
        phrases = Counter()
        for text in texts.values():
            t = _clean(text)
            phrases.update({t[i:i + phrase_len] for i in range(max(0, len(t) - phrase_len + 1))})
        common = [(ph, round(n / len(texts), 2)) for ph, n in phrases.most_common(300) if len(texts) >= 3 and n / len(texts) >= phrase_share]
        days[day] = {
            "people": len(texts), "between_people": _mean(pairs), "same_person_vs_yesterday": _mean(selves),
            "distinct_3grams": round(len(pieces) / max(1, sum(pieces.values())), 3), "common_phrases": common[:10],
        }
        previous = counted
    overall = {key: _mean([d[key] for d in days.values() if d[key] is not None])
               for key in ("between_people", "same_person_vs_yesterday", "distinct_3grams")}
    return {"overall": overall, "days": days}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    for run in args:
        result = sameness(read_jsonl(Path(run) / "plans.jsonl"))
        print(f"== {run}\n overall: {result['overall']}")
        for day, d in result["days"].items():
            print(f" {day}일: 사람 {d['people']}, 사람 사이 {d['between_people']}, 어제와 {d['same_person_vs_yesterday']}, "
                  f"서로 다른 조각 {d['distinct_3grams']}")
            for phrase, share in d["common_phrases"][:5]:
                print(f"     {share:.0%}  「{phrase}」")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
