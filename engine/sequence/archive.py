"""Lossless checkpoint plus event archives for sequence experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from engine.living.events import RandomDraw, RandomSample, WorldEvent

from .experiment import ExperimentFrame, SequenceExperiment
from .substrate import Contact, SequenceState, Strand, event_candidates, step


@dataclass(frozen=True)
class ArchivedFrame:
    index: int
    candidates_before: int
    total_weight_before: int
    random_draw: RandomDraw
    event: WorldEvent

    def canonical(self) -> dict[str, object]:
        return {
            "candidates_before": self.candidates_before,
            "event": self.event.canonical(),
            "index": self.index,
            "random_draw": {
                "arguments": list(self.random_draw.arguments),
                "index": self.random_draw.index,
                "operation": self.random_draw.operation,
                "result": self.random_draw.result,
            },
            "total_weight_before": self.total_weight_before,
        }


@dataclass(frozen=True)
class StateCheckpoint:
    frame_index: int
    state: SequenceState

    def canonical(self) -> dict[str, object]:
        return {"frame_index": self.frame_index, "state": self.state.canonical()}


@dataclass(frozen=True)
class ExperimentArchive:
    checkpoint_interval: int
    stop_reason: str
    frames: tuple[ArchivedFrame, ...]
    checkpoints: tuple[StateCheckpoint, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.checkpoint_interval, bool)
            or not isinstance(self.checkpoint_interval, int)
            or self.checkpoint_interval <= 0
        ):
            raise ValueError("checkpoint_interval must be a positive integer")
        if self.stop_reason not in {"quiescent", "event_limit"}:
            raise ValueError("unknown experiment stop reason")
        if tuple(frame.index for frame in self.frames) != tuple(range(len(self.frames))):
            raise ValueError("archive frame indices must be contiguous")
        indices = tuple(checkpoint.frame_index for checkpoint in self.checkpoints)
        if not indices or indices[0] != -1 or indices != tuple(sorted(set(indices))):
            raise ValueError("archive needs one ordered initial checkpoint")
        if any(index < -1 or index >= len(self.frames) for index in indices):
            raise ValueError("checkpoint frame index is outside the archive")

    @property
    def initial_state(self) -> SequenceState:
        return self.checkpoints[0].state

    def canonical(self) -> dict[str, object]:
        return {
            "checkpoint_interval": self.checkpoint_interval,
            "checkpoints": [checkpoint.canonical() for checkpoint in self.checkpoints],
            "frames": [frame.canonical() for frame in self.frames],
            "format": "sequence-experiment-checkpoint-v1",
            "stop_reason": self.stop_reason,
        }

    def digest(self) -> str:
        raw = json.dumps(self.canonical(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def from_canonical(cls, raw: Mapping[str, Any]) -> ExperimentArchive:
        if raw.get("format") != "sequence-experiment-checkpoint-v1":
            raise ValueError("unknown sequence archive format")
        frames = tuple(_archived_frame_from_canonical(item) for item in raw["frames"])
        checkpoints = tuple(
            StateCheckpoint(int(item["frame_index"]), state_from_canonical(item["state"]))
            for item in raw["checkpoints"]
        )
        return cls(int(raw["checkpoint_interval"]), str(raw["stop_reason"]), frames, checkpoints)


def state_from_canonical(raw: Mapping[str, Any]) -> SequenceState:
    strands = tuple(Strand(int(item["strand_id"]), tuple(item["symbols"])) for item in raw["strands"])
    contacts = tuple(
        Contact(
            int(item["left_id"]),
            int(item["left_start"]),
            int(item["right_id"]),
            int(item["right_start"]),
            int(item["length"]),
            int(item["bond_energy"]),
        )
        for item in raw["contacts"]
    )
    return SequenceState(
        strands,
        int(raw["thermal_energy"]),
        contacts,
        int(raw["time"]),
        int(raw["next_strand_id"]),
    )


def _archived_frame_from_canonical(raw: Mapping[str, Any]) -> ArchivedFrame:
    draw_raw = raw["random_draw"]
    event_raw = raw["event"]
    return ArchivedFrame(
        int(raw["index"]),
        int(raw["candidates_before"]),
        int(raw["total_weight_before"]),
        RandomDraw(
            int(draw_raw["index"]),
            str(draw_raw["operation"]),
            tuple(draw_raw["arguments"]),
            draw_raw["result"],
        ),
        WorldEvent.create(
            event_raw["world_time"],
            event_raw["event_type"],
            event_raw["payload"],
            event_raw["subject_id"],
        ),
    )


def archive_experiment(experiment: SequenceExperiment, checkpoint_interval: int = 16) -> ExperimentArchive:
    if isinstance(checkpoint_interval, bool) or not isinstance(checkpoint_interval, int) or checkpoint_interval <= 0:
        raise ValueError("checkpoint_interval must be a positive integer")
    frames = tuple(
        ArchivedFrame(
            frame.index,
            frame.candidates_before,
            frame.total_weight_before,
            frame.random_draw,
            frame.event,
        )
        for frame in experiment.frames
    )
    checkpoints = [StateCheckpoint(-1, experiment.initial_state)]
    for frame in experiment.frames:
        if (frame.index + 1) % checkpoint_interval == 0 or frame.index == len(experiment.frames) - 1:
            checkpoints.append(StateCheckpoint(frame.index, frame.state))
    return ExperimentArchive(checkpoint_interval, experiment.stop_reason, frames, tuple(checkpoints))


class _ArchivedChoiceSource:
    def __init__(self, draw: RandomDraw) -> None:
        self.draw = draw
        self.used = False

    def choice_index(self, count: int) -> RandomSample:
        if self.used:
            raise ValueError("archived event requested more than one random draw")
        if self.draw.operation != "choice_index" or self.draw.arguments != (count,):
            raise ValueError("archived random draw diverges from reconstructed candidates")
        self.used = True
        return RandomSample(self.draw.result, self.draw)


def _replay_frame(state: SequenceState, archived: ArchivedFrame) -> SequenceState:
    candidates = event_candidates(state)
    if len(candidates) != archived.candidates_before:
        raise ValueError("archive candidate count diverged during reconstruction")
    if sum(candidate.weight for candidate in candidates) != archived.total_weight_before:
        raise ValueError("archive candidate weight diverged during reconstruction")
    result = step(state, _ArchivedChoiceSource(archived.random_draw))
    if result.event != archived.event:
        raise ValueError("archive event diverged during reconstruction")
    return result.state


def restore_state(archive: ExperimentArchive, frame_index: int) -> SequenceState:
    """Restore the state after frame_index; -1 addresses the initial state."""
    if isinstance(frame_index, bool) or not isinstance(frame_index, int):
        raise TypeError("frame_index must be an integer")
    if frame_index < -1 or frame_index >= len(archive.frames):
        raise ValueError("frame_index is outside the archive")
    checkpoint = max(
        (item for item in archive.checkpoints if item.frame_index <= frame_index),
        key=lambda item: item.frame_index,
    )
    state = checkpoint.state
    checkpoints = {item.frame_index: item.state for item in archive.checkpoints}
    for index in range(checkpoint.frame_index + 1, frame_index + 1):
        archived = archive.frames[index]
        state = _replay_frame(state, archived)
        expected_checkpoint = checkpoints.get(index)
        if expected_checkpoint is not None and state != expected_checkpoint:
            raise ValueError("archive checkpoint diverged during reconstruction")
    return state


def restore_experiment(archive: ExperimentArchive) -> SequenceExperiment:
    states = tuple(iter_restored_states(archive))[1:]
    frames = tuple(
        ExperimentFrame(
            archived.index,
            archived.candidates_before,
            archived.total_weight_before,
            archived.random_draw,
            archived.event,
            states[archived.index],
        )
        for archived in archive.frames
    )
    return SequenceExperiment(archive.initial_state, frames, archive.stop_reason)


def iter_restored_states(archive: ExperimentArchive) -> Iterator[SequenceState]:
    """Yield initial and every subsequent state by one linear verified replay."""
    state = archive.initial_state
    checkpoints = {item.frame_index: item.state for item in archive.checkpoints}
    yield state
    for archived in archive.frames:
        state = _replay_frame(state, archived)
        expected_checkpoint = checkpoints.get(archived.index)
        if expected_checkpoint is not None and state != expected_checkpoint:
            raise ValueError("archive checkpoint diverged during reconstruction")
        yield state


def verify_archive(archive: ExperimentArchive) -> bool:
    try:
        state = archive.initial_state
        for state in iter_restored_states(archive):
            pass
        if archive.stop_reason == "quiescent" and event_candidates(state):
            return False
        return True
    except (TypeError, ValueError):
        return False
