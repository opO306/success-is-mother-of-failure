"""Describe long sequence archives without assigning fitness or success."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Iterable


def _open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def analyze_records(rows: Iterable[dict]) -> dict[str, object]:
    event_counts: Counter[str] = Counter()
    trials_with_event: Counter[str] = Counter()
    family_stops: Counter[str] = Counter()
    context_multipliers: Counter[int] = Counter()
    exact_growth_outcomes: Counter[str] = Counter()
    growth_families: Counter[str] = Counter()
    growth_seeds: Counter[int] = Counter()
    trials = joins = context_events = repeated_growth_trials = 0
    repeated_context_trials = maximum_context_events_in_trial = 0
    maximum_joins_in_trial = maximum_contact_span = 0
    first_join_index: int | None = None
    last_join_index: int | None = None
    maximum_exact_growth_state_span = 0
    exact_growth_state_spans: list[int] = []
    growth_case_tags: set[str] = set()

    for row in rows:
        frames = row["archive"]["frames"]
        family = row["case_tag"].split(":", 1)[0]
        family_stops[f"{family}|{row['archive']['stop_reason']}"] += 1
        maximum_contact_span = max(maximum_contact_span, row["observation"]["longest_contact_state_span"])
        seen_types: set[str] = set()
        join_frames = []
        trial_context_events = 0
        for frame in frames:
            event = frame["event"]
            event_type = event["event_type"]
            payload = event["payload"]
            event_counts[event_type] += 1
            seen_types.add(event_type)
            multiplier = int(payload.get("context_multiplier", 1))
            if multiplier > 1:
                context_events += 1
                trial_context_events += 1
                context_multipliers[multiplier] += 1
            if event_type == "sequence.backbone_join":
                join_frames.append(frame)
        for event_type in seen_types:
            trials_with_event[event_type] += 1

        joins += len(join_frames)
        maximum_context_events_in_trial = max(maximum_context_events_in_trial, trial_context_events)
        if trial_context_events > 1:
            repeated_context_trials += 1
        maximum_joins_in_trial = max(maximum_joins_in_trial, len(join_frames))
        if len(join_frames) > 1:
            repeated_growth_trials += 1
        if join_frames:
            growth_families[family] += 1
            growth_seeds[int(row["seed"])] += 1
            growth_case_tags.add(row["case_tag"])
        for joined in join_frames:
            join_index = joined["index"]
            product_id = joined["event"]["payload"]["new_strand_id"]
            first_join_index = join_index if first_join_index is None else min(first_join_index, join_index)
            last_join_index = join_index if last_join_index is None else max(last_join_index, join_index)
            outcome = "present_at_end"
            end_index = len(frames) - 1
            for later in frames[join_index + 1 :]:
                payload = later["event"]["payload"]
                if later["event"]["event_type"] == "sequence.backbone_cleave" and payload.get(
                    "parent_strand_id"
                ) == product_id:
                    outcome = "cleaved"
                    end_index = later["index"]
                    break
                if later["event"]["event_type"] == "sequence.backbone_join" and product_id in payload.get(
                    "parent_strand_ids", []
                ):
                    outcome = "joined_again"
                    end_index = later["index"]
                    break
            exact_growth_outcomes[outcome] += 1
            state_span = max(1, end_index - join_index + (1 if outcome == "present_at_end" else 0))
            exact_growth_state_spans.append(state_span)
            maximum_exact_growth_state_span = max(maximum_exact_growth_state_span, state_span)
        trials += 1

    return {
        "trials": trials,
        "family_stop_counts": dict(sorted(family_stops.items())),
        "event_counts": dict(sorted(event_counts.items())),
        "trials_containing_event": dict(sorted(trials_with_event.items())),
        "context_events": context_events,
        "context_multipliers": dict(sorted(context_multipliers.items())),
        "repeated_context_trials": repeated_context_trials,
        "maximum_context_events_in_trial": maximum_context_events_in_trial,
        "join_events": joins,
        "growth_trials_by_family": dict(sorted(growth_families.items())),
        "growth_trials_by_seed": dict(sorted(growth_seeds.items())),
        "unique_growth_case_tags": len(growth_case_tags),
        "repeated_growth_trials": repeated_growth_trials,
        "maximum_joins_in_trial": maximum_joins_in_trial,
        "first_join_index": first_join_index,
        "last_join_index": last_join_index,
        "exact_growth_outcomes": dict(sorted(exact_growth_outcomes.items())),
        "maximum_exact_growth_state_span": maximum_exact_growth_state_span,
        "minimum_exact_growth_state_span": min(exact_growth_state_spans) if exact_growth_state_spans else 0,
        "median_exact_growth_state_span": median(exact_growth_state_spans) if exact_growth_state_spans else 0,
        "growth_spans_at_least_8": sum(span >= 8 for span in exact_growth_state_spans),
        "growth_spans_at_least_24": sum(span >= 24 for span in exact_growth_state_spans),
        "growth_spans_exactly_1": sum(span == 1 for span in exact_growth_state_spans),
        "maximum_contact_state_span": maximum_contact_span,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    with _open_text(args.path) as handle:
        result = analyze_records(json.loads(line) for line in handle)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
