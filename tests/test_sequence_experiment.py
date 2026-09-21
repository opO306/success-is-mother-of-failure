import pytest

from engine.living.events import HistoryLog, RandomDraw, ReplayEventSource, SeededEventSource, WorldEvent
from engine.sequence import (
    ExperimentFrame,
    SequenceExperiment,
    SequenceState,
    Strand,
    append_experiment_history,
    build_causal_trace,
    event_candidates,
    event_counts,
    parse_symbols,
    repeated_configurations,
    run_experiment,
    step,
)


def _choose(state: SequenceState, predicate):
    candidates = event_candidates(state)
    target = next(candidate for candidate in candidates if predicate(candidate))
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    return step(state, ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),)))


def test_quiescent_world_stops_without_an_event() -> None:
    initial = SequenceState((Strand(1, (0,)),), thermal_energy=0)
    source = SeededEventSource(11)

    experiment = run_experiment(initial, source, max_events=10)

    assert experiment.stop_reason == "quiescent"
    assert experiment.frames == ()
    assert experiment.final_state == initial
    assert source.draw_count == 0


def test_event_limit_is_not_reported_as_natural_quiescence() -> None:
    initial = SequenceState((Strand(1, parse_symbols("ACGTACGT")),), thermal_energy=8)

    experiment = run_experiment(initial, SeededEventSource(17), max_events=3)

    assert experiment.stop_reason == "event_limit"
    assert len(experiment.frames) == 3


def test_same_seed_reproduces_every_frame() -> None:
    initial = SequenceState(
        (Strand(1, parse_symbols("TTTT")), Strand(2, parse_symbols("AAAA"))),
        thermal_energy=12,
    )

    first = run_experiment(initial, SeededEventSource(73), max_events=12)
    second = run_experiment(initial, SeededEventSource(73), max_events=12)

    assert first == second


def test_external_recording_does_not_change_a_completed_experiment() -> None:
    initial = SequenceState((Strand(1, parse_symbols("ACGTAC")),), thermal_energy=6)
    source = SeededEventSource(5)
    experiment = run_experiment(initial, source, max_events=4)
    before = experiment.final_state.state_hash()
    draws_before = source.draw_count
    history = HistoryLog()

    append_experiment_history(experiment, history)

    assert experiment.final_state.state_hash() == before
    assert source.draw_count == draws_before
    assert history.verify()
    assert len(history.records) == 1 + 2 * len(experiment.frames)


def test_recorded_experiment_replays_without_divergence() -> None:
    initial = SequenceState(
        (Strand(1, parse_symbols("TTT")), Strand(2, parse_symbols("AAA"))),
        thermal_energy=10,
    )
    original = run_experiment(initial, SeededEventSource(1234), max_events=15)
    history = HistoryLog()
    append_experiment_history(original, history)

    replayed = run_experiment(initial, ReplayEventSource.from_history(history), max_events=15)

    assert replayed == original


def test_configuration_hash_ignores_only_world_time() -> None:
    first = SequenceState((Strand(1, parse_symbols("AC")),), thermal_energy=2, time=0)
    later = SequenceState((Strand(1, parse_symbols("AC")),), thermal_energy=2, time=99)

    assert first.configuration_hash() == later.configuration_hash()
    assert first.state_hash() != later.state_hash()


def test_repeated_configuration_view_does_not_modify_the_world() -> None:
    initial = SequenceState((Strand(1, parse_symbols("AC")),), thermal_energy=2, time=0)
    later = SequenceState((Strand(1, parse_symbols("AC")),), thermal_energy=2, time=1)
    event = WorldEvent.create(1, "sequence.observer_test", {"state_hash": later.state_hash()})
    frame = ExperimentFrame(0, 1, 1, RandomDraw(0, "choice_index", (1,), 0), event, later)
    experiment = SequenceExperiment(initial, (frame,), "event_limit")

    repeats = repeated_configurations(experiment)

    assert list(repeats.values()) == [(0, 1)]
    assert experiment.initial_state == initial
    assert experiment.final_state == later


def test_causal_trace_links_shared_participants_without_becoming_world_logic() -> None:
    initial = SequenceState(
        (Strand(1, parse_symbols("TT")), Strand(2, (0,)), Strand(3, (0,))),
        thermal_energy=12,
    )
    first = _choose(
        initial,
        lambda candidate: candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 0
        and candidate.contact.right_id == 2,
    )
    second = _choose(
        first.state,
        lambda candidate: candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 1
        and candidate.contact.right_id == 3,
    )
    joined = _choose(second.state, lambda candidate: candidate.kind == "join")

    trace = build_causal_trace((first.event, second.event, joined.event))

    assert trace[0].parent_indices == ()
    assert trace[1].parent_indices == (0,)
    assert trace[2].parent_indices == (0, 1)
    assert trace[2].participant_ids == (1, 2, 3, 4)
    assert joined.state.strands != second.state.strands


def test_event_counts_are_descriptive_not_a_score() -> None:
    initial = SequenceState((Strand(1, parse_symbols("ACGT")),), thermal_energy=4)
    experiment = run_experiment(initial, SeededEventSource(8), max_events=2)

    counts = event_counts(experiment)

    assert sum(counts.values()) == len(experiment.frames)
    assert "fitness" not in counts
    assert "score" not in counts


@pytest.mark.parametrize("invalid", [-1, 1.5, True])
def test_event_limit_must_be_a_non_negative_integer(invalid) -> None:
    initial = SequenceState((Strand(1, (0,)),), thermal_energy=0)
    with pytest.raises(ValueError):
        run_experiment(initial, SeededEventSource(1), invalid)
