"""Bounded sequence experiments and observer-only causal views."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from engine.living.events import HistoryLog, RandomDraw, WorldEvent

from .substrate import ChoiceSource, SequenceState, event_candidates, step


@dataclass(frozen=True)
class ExperimentFrame:
    index: int
    candidates_before: int
    total_weight_before: int
    random_draw: RandomDraw
    event: WorldEvent
    state: SequenceState


@dataclass(frozen=True)
class SequenceExperiment:
    initial_state: SequenceState
    frames: tuple[ExperimentFrame, ...]
    stop_reason: str

    def __post_init__(self) -> None:
        if self.stop_reason not in {"quiescent", "event_limit"}:
            raise ValueError("unknown experiment stop reason")

    @property
    def final_state(self) -> SequenceState:
        return self.frames[-1].state if self.frames else self.initial_state

    def states(self) -> tuple[SequenceState, ...]:
        return (self.initial_state, *(frame.state for frame in self.frames))


@dataclass(frozen=True)
class CausalNode:
    index: int
    world_time: float
    event_type: str
    participant_ids: tuple[int, ...]
    parent_indices: tuple[int, ...]
    state_hash: str


def run_experiment(
    initial_state: SequenceState,
    chance: ChoiceSource,
    max_events: int,
) -> SequenceExperiment:
    """Run without a recorder; observer products are derived only after transitions."""
    if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 0:
        raise ValueError("max_events must be a non-negative integer")
    state = initial_state
    frames: list[ExperimentFrame] = []
    for index in range(max_events):
        candidates = event_candidates(state)
        if not candidates:
            return SequenceExperiment(initial_state, tuple(frames), "quiescent")
        total_weight = sum(candidate.weight for candidate in candidates)
        result = step(state, chance)
        if result.event is None or result.random_draw is None:
            raise RuntimeError("an event candidate set produced no transition")
        state = result.state
        frames.append(
            ExperimentFrame(
                index=index,
                candidates_before=len(candidates),
                total_weight_before=total_weight,
                random_draw=result.random_draw,
                event=result.event,
                state=state,
            )
        )
    return SequenceExperiment(initial_state, tuple(frames), "event_limit")


def append_experiment_history(experiment: SequenceExperiment, history: HistoryLog) -> None:
    """Copy a completed experiment into an outside log; never called by the world."""
    history.append(
        WorldEvent.create(
            experiment.initial_state.time,
            "sequence.experiment.initialized",
            {
                "state": experiment.initial_state.canonical(),
                "state_hash": experiment.initial_state.state_hash(),
            },
        )
    )
    for frame in experiment.frames:
        history.append(frame.random_draw.as_event(frame.state.time))
        history.append(frame.event)


def event_counts(experiment: SequenceExperiment) -> dict[str, int]:
    """Observer summary only; values are never fitness or world input."""
    counts = Counter(frame.event.event_type for frame in experiment.frames)
    return dict(sorted(counts.items()))


def repeated_configurations(experiment: SequenceExperiment) -> dict[str, tuple[int, ...]]:
    seen: dict[str, list[int]] = {}
    for index, state in enumerate(experiment.states()):
        seen.setdefault(state.configuration_hash(), []).append(index)
    return {digest: tuple(indices) for digest, indices in seen.items() if len(indices) > 1}


def _participants(event: WorldEvent) -> tuple[int, ...]:
    payload = event.payload()
    found: set[int] = set()
    for key in ("left_id", "right_id", "new_strand_id", "parent_strand_id", "template_id"):
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            found.add(value)
    for key in ("parent_strand_ids", "child_strand_ids"):
        values = payload.get(key, ())
        if isinstance(values, list):
            found.update(value for value in values if isinstance(value, int) and not isinstance(value, bool))
    return tuple(sorted(found))


def build_causal_trace(events: Iterable[WorldEvent]) -> tuple[CausalNode, ...]:
    """Infer proximal participation links outside the simulated world."""
    last_event_by_participant: dict[int, int] = {}
    nodes: list[CausalNode] = []
    for index, event in enumerate(events):
        participants = _participants(event)
        parents = tuple(
            sorted({last_event_by_participant[item] for item in participants if item in last_event_by_participant})
        )
        payload = event.payload()
        node = CausalNode(
            index=index,
            world_time=event.world_time,
            event_type=event.event_type,
            participant_ids=participants,
            parent_indices=parents,
            state_hash=str(payload.get("state_hash", "")),
        )
        nodes.append(node)
        for participant in participants:
            last_event_by_participant[participant] = index
    return tuple(nodes)
