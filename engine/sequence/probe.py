"""Observer-only capability probes over bounded sequence experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations_with_replacement, product
from typing import Iterable, Iterator

from engine.living.events import SeededEventSource

from .experiment import SequenceExperiment, build_causal_trace, event_counts, repeated_configurations, run_experiment
from .substrate import Contact, SequenceState, Strand


@dataclass(frozen=True)
class ProbeCase:
    tag: str
    initial_state: SequenceState
    seeds: tuple[int, ...]
    max_events: int

    def __post_init__(self) -> None:
        if not self.tag:
            raise ValueError("probe tag cannot be empty")
        if not self.seeds:
            raise ValueError("a probe case needs at least one seed")
        if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in self.seeds):
            raise TypeError("probe seeds must be integers")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("probe seeds must be unique")
        if isinstance(self.max_events, bool) or not isinstance(self.max_events, int) or self.max_events < 0:
            raise ValueError("max_events must be a non-negative integer")


@dataclass(frozen=True)
class ProbeObservation:
    case_tag: str
    seed: int
    stop_reason: str
    event_count: int
    event_type_counts: tuple[tuple[str, int], ...]
    unique_configurations: int
    repeated_configuration_groups: int
    longest_contact_state_span: int
    causal_edge_count: int
    participation_spread_events: int
    structural_context_events: int
    final_state_hash: str


@dataclass(frozen=True)
class ProbeTrial:
    case: ProbeCase
    seed: int
    experiment: SequenceExperiment
    observation: ProbeObservation


@dataclass(frozen=True)
class ProbeReport:
    trials: tuple[ProbeTrial, ...]

    @property
    def observations(self) -> tuple[ProbeObservation, ...]:
        return tuple(trial.observation for trial in self.trials)


def _longest_contact_state_span(experiment: SequenceExperiment) -> int:
    active: dict[Contact, int] = {}
    longest = 0
    for state in experiment.states():
        present = set(state.contacts)
        active = {contact: span for contact, span in active.items() if contact in present}
        for contact in present:
            active[contact] = active.get(contact, 0) + 1
            longest = max(longest, active[contact])
    return longest


def observe_experiment(case_tag: str, seed: int, experiment: SequenceExperiment) -> ProbeObservation:
    """Describe a completed run without assigning success, fitness, or rank."""
    trace = build_causal_trace(frame.event for frame in experiment.frames)
    by_index = {node.index: node for node in trace}
    spread_events = 0
    for node in trace:
        inherited_participants = {
            participant
            for parent_index in node.parent_indices
            for participant in by_index[parent_index].participant_ids
        }
        if node.parent_indices and set(node.participant_ids) - inherited_participants:
            spread_events += 1
    context_events = sum(
        int(frame.event.payload().get("context_multiplier", 1)) > 1 for frame in experiment.frames
    )
    repeats = repeated_configurations(experiment)
    return ProbeObservation(
        case_tag=case_tag,
        seed=seed,
        stop_reason=experiment.stop_reason,
        event_count=len(experiment.frames),
        event_type_counts=tuple(event_counts(experiment).items()),
        unique_configurations=len({state.configuration_hash() for state in experiment.states()}),
        repeated_configuration_groups=len(repeats),
        longest_contact_state_span=_longest_contact_state_span(experiment),
        causal_edge_count=sum(len(node.parent_indices) for node in trace),
        participation_spread_events=spread_events,
        structural_context_events=context_events,
        final_state_hash=experiment.final_state.state_hash(),
    )


def iter_probe_trials(cases: Iterable[ProbeCase]) -> Iterator[ProbeTrial]:
    """Run one trial at a time so full records need not accumulate in memory."""
    seen_tags: set[str] = set()
    for case in cases:
        if case.tag in seen_tags:
            raise ValueError(f"duplicate probe tag: {case.tag}")
        seen_tags.add(case.tag)
        for seed in case.seeds:
            experiment = run_experiment(case.initial_state, SeededEventSource(seed), case.max_events)
            yield ProbeTrial(case, seed, experiment, observe_experiment(case.tag, seed, experiment))


def run_probe(cases: Iterable[ProbeCase]) -> ProbeReport:
    return ProbeReport(tuple(iter_probe_trials(cases)))


def _short_sequences(max_length: int) -> tuple[tuple[int, ...], ...]:
    return tuple(
        symbols
        for length in range(1, max_length + 1)
        for symbols in product(range(4), repeat=length)
    )


def _sequence_label(symbols: tuple[int, ...]) -> str:
    return "".join(str(symbol) for symbol in symbols)


def exhaustive_short_cases(
    max_length: int = 2,
    seeds: tuple[int, ...] = (0, 1),
    max_events: int = 16,
    thermal_energy_per_symbol: int = 2,
) -> tuple[ProbeCase, ...]:
    """Enumerate every single sequence and every unordered pair up to a small length."""
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length <= 0:
        raise ValueError("max_length must be a positive integer")
    if (
        isinstance(thermal_energy_per_symbol, bool)
        or not isinstance(thermal_energy_per_symbol, int)
        or thermal_energy_per_symbol < 0
    ):
        raise ValueError("thermal_energy_per_symbol must be a non-negative integer")
    sequences = _short_sequences(max_length)
    cases: list[ProbeCase] = []
    for symbols in sequences:
        state = SequenceState(
            (Strand(1, symbols),),
            thermal_energy_per_symbol * len(symbols),
        )
        cases.append(ProbeCase(f"single:{_sequence_label(symbols)}", state, seeds, max_events))
    for left, right in combinations_with_replacement(sequences, 2):
        state = SequenceState(
            (Strand(1, left), Strand(2, right)),
            thermal_energy_per_symbol * (len(left) + len(right)),
        )
        cases.append(
            ProbeCase(f"pair:{_sequence_label(left)}|{_sequence_label(right)}", state, seeds, max_events)
        )
    return tuple(cases)


def sampled_triple_cases(
    max_length: int = 3,
    sample_size: int = 512,
    selection_key: str = "stage-c-triples-v1",
    seeds: tuple[int, ...] = (0, 1),
    max_events: int = 24,
    thermal_energy_per_symbol: int = 2,
) -> tuple[ProbeCase, ...]:
    """Select triples before execution by stable hash rank, never by their outcomes."""
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length <= 0:
        raise ValueError("max_length must be a positive integer")
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size < 0:
        raise ValueError("sample_size must be a non-negative integer")
    if not selection_key:
        raise ValueError("selection_key cannot be empty")
    if (
        isinstance(thermal_energy_per_symbol, bool)
        or not isinstance(thermal_energy_per_symbol, int)
        or thermal_energy_per_symbol < 0
    ):
        raise ValueError("thermal_energy_per_symbol must be a non-negative integer")
    if sample_size == 0:
        return ()

    sequences = _short_sequences(max_length)
    triples = combinations_with_replacement(sequences, 3)
    ranked: list[tuple[bytes, tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]]] = []
    for triple in triples:
        canonical = json.dumps(triple, separators=(",", ":"))
        digest = hashlib.sha256(f"{selection_key}:{canonical}".encode("utf-8")).digest()
        ranked.append((digest, triple))
    if sample_size > len(ranked):
        raise ValueError("sample_size exceeds the available triple combinations")

    selected = sorted(ranked, key=lambda item: (item[0], item[1]))[:sample_size]
    cases = []
    for _, (first, second, third) in selected:
        state = SequenceState(
            (Strand(1, first), Strand(2, second), Strand(3, third)),
            thermal_energy_per_symbol * (len(first) + len(second) + len(third)),
        )
        tag = "triple:" + "|".join(
            (_sequence_label(first), _sequence_label(second), _sequence_label(third))
        )
        cases.append(ProbeCase(tag, state, seeds, max_events))
    return tuple(sorted(cases, key=lambda case: case.tag))
