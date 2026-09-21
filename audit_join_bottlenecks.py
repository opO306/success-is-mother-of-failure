"""Audit why first or repeated backbone growth candidates do or do not appear."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from statistics import median

from engine.sequence import ExperimentArchive, event_candidates, iter_restored_states, join_readiness


STAGES = (
    "energy_unavailable",
    "fewer_than_two_external_contacts",
    "no_shared_template",
    "same_fragment_only",
    "fragment_contact_not_exclusive",
    "fragment_not_fully_bound",
    "not_adjacent_on_template",
    "join_candidate_available",
)


def readiness_stage(readiness) -> int:
    if not readiness.energy_available:
        return 0
    if readiness.external_contacts < 2:
        return 1
    if readiness.shared_template_arrangements == 0:
        return 2
    if readiness.distinct_fragment_arrangements == 0:
        return 3
    if readiness.exclusive_fragment_arrangements == 0:
        return 4
    if readiness.fully_bound_arrangements == 0:
        return 5
    if readiness.adjacent_arrangements == 0:
        return 6
    return 7


def _open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    trials = growth_trials = 0
    trials_with_candidate = trials_with_candidate_but_no_growth = 0
    candidate_states = selected_join_states = 0
    no_candidate_trial_furthest: Counter[str] = Counter()
    post_growth_episode_furthest: Counter[str] = Counter()
    candidate_state_selected_events: Counter[str] = Counter()
    post_growth_candidate_selected_events: Counter[str] = Counter()
    post_growth_episodes = post_growth_states = post_growth_candidate_states = 0
    post_growth_episodes_with_candidate = 0
    opportunity_probabilities: list[float] = []
    selected_probabilities: list[float] = []
    post_growth_probabilities: list[float] = []
    post_growth_join_weights: list[int] = []
    post_growth_unbind_weights: list[int] = []

    with _open_text(args.path) as handle:
        for line in handle:
            row = json.loads(line)
            archive = ExperimentArchive.from_canonical(row["archive"])
            states = tuple(iter_restored_states(archive))
            frames = archive.frames
            trial_has_candidate = False
            trial_has_join = False
            furthest = 0
            readiness_by_frame = []

            for index, frame in enumerate(frames):
                state = states[index]
                readiness = join_readiness(state)
                readiness_by_frame.append(readiness)
                furthest = max(furthest, readiness_stage(readiness))
                if readiness.available_join_candidates:
                    trial_has_candidate = True
                    candidate_states += 1
                    candidates = event_candidates(state)
                    total_weight = sum(candidate.weight for candidate in candidates)
                    join_weight = sum(candidate.weight for candidate in candidates if candidate.kind == "join")
                    probability = join_weight / total_weight
                    opportunity_probabilities.append(probability)
                    candidate_state_selected_events[frame.event.event_type] += 1
                    if frame.event.event_type == "sequence.backbone_join":
                        selected_join_states += 1
                        selected_probabilities.append(probability)
                if frame.event.event_type == "sequence.backbone_join":
                    trial_has_join = True

            if trial_has_candidate:
                trials_with_candidate += 1
            else:
                no_candidate_trial_furthest[STAGES[furthest]] += 1
            if trial_has_candidate and not trial_has_join:
                trials_with_candidate_but_no_growth += 1
            if trial_has_join:
                growth_trials += 1

            join_indices = [
                frame.index for frame in frames if frame.event.event_type == "sequence.backbone_join"
            ]
            for join_index in join_indices:
                product_id = frames[join_index].event.payload()["new_strand_id"]
                destruction_index = len(frames)
                for later in frames[join_index + 1 :]:
                    payload = later.event.payload()
                    if later.event.event_type == "sequence.backbone_cleave" and payload.get(
                        "parent_strand_id"
                    ) == product_id:
                        destruction_index = later.index
                        break
                    if later.event.event_type == "sequence.backbone_join" and product_id in payload.get(
                        "parent_strand_ids", []
                    ):
                        destruction_index = later.index
                        break

                post_growth_episodes += 1
                episode_has_candidate = False
                episode_furthest = 0
                final_state_index = min(destruction_index, len(frames))
                for state_index in range(join_index + 1, final_state_index + 1):
                    post_growth_states += 1
                    readiness = join_readiness(states[state_index])
                    episode_furthest = max(episode_furthest, readiness_stage(readiness))
                    if readiness.available_join_candidates:
                        episode_has_candidate = True
                        post_growth_candidate_states += 1
                        if state_index < len(frames):
                            candidates = event_candidates(states[state_index])
                            total_weight = sum(candidate.weight for candidate in candidates)
                            join_weight = sum(candidate.weight for candidate in candidates if candidate.kind == "join")
                            unbind_weight = sum(candidate.weight for candidate in candidates if candidate.kind == "unbind")
                            post_growth_probabilities.append(join_weight / total_weight)
                            post_growth_join_weights.append(join_weight)
                            post_growth_unbind_weights.append(unbind_weight)
                            post_growth_candidate_selected_events[frames[state_index].event.event_type] += 1
                if episode_has_candidate:
                    post_growth_episodes_with_candidate += 1
                else:
                    post_growth_episode_furthest[STAGES[episode_furthest]] += 1
            trials += 1

    def probability_summary(values: list[float]) -> dict[str, float]:
        if not values:
            return {"minimum": 0.0, "median": 0.0, "maximum": 0.0}
        return {"minimum": min(values), "median": median(values), "maximum": max(values)}

    print(
        json.dumps(
            {
                "trials": trials,
                "growth_trials": growth_trials,
                "trials_with_join_candidate": trials_with_candidate,
                "trials_with_candidate_but_no_growth": trials_with_candidate_but_no_growth,
                "candidate_states": candidate_states,
                "selected_join_states": selected_join_states,
                "candidate_state_selected_events": dict(sorted(candidate_state_selected_events.items())),
                "join_candidate_probability": probability_summary(opportunity_probabilities),
                "selected_join_probability": probability_summary(selected_probabilities),
                "trials_without_candidate_furthest_gate": dict(sorted(no_candidate_trial_furthest.items())),
                "post_growth_episodes": post_growth_episodes,
                "post_growth_states": post_growth_states,
                "post_growth_candidate_states": post_growth_candidate_states,
                "post_growth_episodes_with_second_join_candidate": post_growth_episodes_with_candidate,
                "post_growth_candidate_probability": probability_summary(post_growth_probabilities),
                "post_growth_join_weight": probability_summary(post_growth_join_weights),
                "post_growth_unbind_weight": probability_summary(post_growth_unbind_weights),
                "post_growth_candidate_selected_events": dict(
                    sorted(post_growth_candidate_selected_events.items())
                ),
                "post_growth_without_candidate_furthest_gate": dict(
                    sorted(post_growth_episode_furthest.items())
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
