"""Run the exhaustive small sequence probe and preserve every trial frame."""

from __future__ import annotations

import argparse
import gzip
import io
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from engine.sequence import archive_experiment, exhaustive_short_cases, iter_probe_trials, sampled_triple_cases


def _trial_record(trial) -> dict[str, object]:
    return {
        "case_tag": trial.case.tag,
        "seed": trial.seed,
        "max_events": trial.case.max_events,
        "initial_state": trial.experiment.initial_state.canonical(),
        "stop_reason": trial.experiment.stop_reason,
        "observation": asdict(trial.observation),
        "frames": [
            {
                "index": frame.index,
                "candidates_before": frame.candidates_before,
                "total_weight_before": frame.total_weight_before,
                "random_draw": asdict(frame.random_draw),
                "event": frame.event.canonical(),
                "state": frame.state.canonical(),
            }
            for frame in trial.experiment.frames
        ],
    }


def _trial_archive_record(trial, checkpoint_interval: int) -> dict[str, object]:
    archive = archive_experiment(trial.experiment, checkpoint_interval)
    return {
        "archive": archive.canonical(),
        "archive_digest": archive.digest(),
        "case_tag": trial.case.tag,
        "max_events": trial.case.max_events,
        "observation": asdict(trial.observation),
        "seed": trial.seed,
    }


@contextmanager
def _text_writer(path: Path):
    if path.suffix.lower() == ".gz":
        with path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                    yield text
    else:
        with path.open("w", encoding="utf-8", newline="\n") as text:
            yield text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-length", type=int, default=2)
    parser.add_argument("--events", type=int, default=16)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--triple-sample-size", type=int, default=0)
    parser.add_argument("--triple-selection-key", default="stage-c-triples-v1")
    parser.add_argument("--checkpoint-interval", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("runs/sequence_probe_stage_c.jsonl"))
    args = parser.parse_args()
    if args.checkpoint_interval < 0:
        parser.error("--checkpoint-interval must be zero or a positive integer")

    exhaustive = exhaustive_short_cases(
        max_length=args.max_length,
        seeds=tuple(args.seeds),
        max_events=args.events,
    )
    triples = sampled_triple_cases(
        max_length=args.max_length,
        sample_size=args.triple_sample_size,
        selection_key=args.triple_selection_key,
        seeds=tuple(args.seeds),
        max_events=args.events,
    )
    cases = (*exhaustive, *triples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    observations = []
    with _text_writer(args.output) as handle:
        for trial in iter_probe_trials(cases):
            record = (
                _trial_archive_record(trial, args.checkpoint_interval)
                if args.checkpoint_interval > 0
                else _trial_record(trial)
            )
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            observations.append(trial.observation)

    summary = {
        "cases": len(cases),
        "exhaustive_single_pair_cases": len(exhaustive),
        "preselected_triple_cases": len(triples),
        "storage": "checkpoint+events" if args.checkpoint_interval > 0 else "full-state-frames",
        "checkpoint_interval": args.checkpoint_interval or None,
        "trials": len(observations),
        "quiescent": sum(item.stop_reason == "quiescent" for item in observations),
        "event_limit": sum(item.stop_reason == "event_limit" for item in observations),
        "with_repeated_configuration": sum(item.repeated_configuration_groups > 0 for item in observations),
        "with_contact_persistence": sum(item.longest_contact_state_span >= 2 for item in observations),
        "with_participation_spread": sum(item.participation_spread_events > 0 for item in observations),
        "with_structural_context": sum(item.structural_context_events > 0 for item in observations),
        "output": str(args.output.resolve()),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
