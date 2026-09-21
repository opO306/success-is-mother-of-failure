from dataclasses import fields

import pytest

from engine.living.events import RandomDraw, ReplayEventSource, WorldEvent
from engine.sequence import (
    Contact,
    ExperimentFrame,
    ProbeCase,
    ProbeObservation,
    SequenceExperiment,
    SequenceState,
    Strand,
    event_candidates,
    exhaustive_short_cases,
    iter_probe_trials,
    observe_experiment,
    parse_symbols,
    run_probe,
    sampled_triple_cases,
    step,
)


def _choose(state: SequenceState, predicate):
    candidates = event_candidates(state)
    target = next(candidate for candidate in candidates if predicate(candidate))
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    return step(state, ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),)))


def test_exhaustive_length_one_cases_cover_all_singles_and_unordered_pairs() -> None:
    cases = exhaustive_short_cases(max_length=1, seeds=(3,), max_events=2)

    assert len(cases) == 14
    assert len({case.tag for case in cases}) == 14
    assert {case.tag for case in cases if case.tag.startswith("single:")} == {
        "single:0",
        "single:1",
        "single:2",
        "single:3",
    }
    assert "pair:0|3" in {case.tag for case in cases}
    assert "pair:3|0" not in {case.tag for case in cases}


def test_probe_keeps_each_seed_as_a_separate_unranked_trial() -> None:
    case = ProbeCase(
        "pair:0|3",
        SequenceState((Strand(1, (0,)), Strand(2, (3,))), thermal_energy=4),
        seeds=(5, 9),
        max_events=4,
    )

    report = run_probe((case,))

    assert [trial.seed for trial in report.trials] == [5, 9]
    assert all(trial.case is case for trial in report.trials)
    assert not ({"fitness", "score", "rank"} & {field.name for field in fields(ProbeObservation)})


def test_probe_is_reproducible() -> None:
    case = ProbeCase(
        "pair:00|33",
        SequenceState((Strand(1, (0, 0)), Strand(2, (3, 3))), thermal_energy=8),
        seeds=(21,),
        max_events=8,
    )

    assert run_probe((case,)) == run_probe((case,))


def test_streaming_trials_match_the_in_memory_report() -> None:
    cases = exhaustive_short_cases(max_length=1, seeds=(2,), max_events=2)
    assert tuple(iter_probe_trials(cases)) == run_probe(cases).trials


def test_triple_sample_is_fixed_before_world_execution() -> None:
    first = sampled_triple_cases(max_length=1, sample_size=5, selection_key="fixed", seeds=(7,), max_events=3)
    second = sampled_triple_cases(max_length=1, sample_size=5, selection_key="fixed", seeds=(7,), max_events=3)

    assert first == second
    assert len(first) == 5
    assert len({case.tag for case in first}) == 5
    assert all(case.tag.startswith("triple:") for case in first)
    assert all(len(case.initial_state.strands) == 3 for case in first)


def test_triple_sample_cannot_silently_exceed_the_population() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        sampled_triple_cases(max_length=1, sample_size=21)


def test_contact_persistence_counts_state_snapshots_not_a_success_label() -> None:
    contact = Contact(1, 0, 2, 0, 1, 2)
    initial = SequenceState((Strand(1, (0,)), Strand(2, (3,))), 4, contacts=(contact,), time=0)
    later = SequenceState((Strand(1, (0,)), Strand(2, (3,))), 4, contacts=(contact,), time=1)
    event = WorldEvent.create(1, "sequence.observer_test", {"state_hash": later.state_hash()})
    frame = ExperimentFrame(0, 1, 1, RandomDraw(0, "choice_index", (1,), 0), event, later)
    experiment = SequenceExperiment(initial, (frame,), "event_limit")

    observation = observe_experiment("persistence-fixture", 0, experiment)

    assert observation.longest_contact_state_span == 2
    assert observation.repeated_configuration_groups == 1


def test_participation_spread_is_derived_from_events_after_the_run() -> None:
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
    frames = tuple(
        ExperimentFrame(index, 1, 1, result.random_draw, result.event, result.state)
        for index, result in enumerate((first, second, joined))
    )
    experiment = SequenceExperiment(initial, frames, "event_limit")

    observation = observe_experiment("spread-fixture", 0, experiment)

    assert observation.causal_edge_count == 3
    assert observation.participation_spread_events == 2
    assert joined.state == experiment.final_state


def test_duplicate_case_tags_are_rejected_instead_of_merged() -> None:
    state = SequenceState((Strand(1, (0,)),), thermal_energy=0)
    cases = (ProbeCase("same", state, (0,), 1), ProbeCase("same", state, (1,), 1))
    with pytest.raises(ValueError, match="duplicate probe tag"):
        run_probe(cases)


@pytest.mark.parametrize("max_length", [0, -1, True])
def test_exhaustive_probe_length_must_be_positive(max_length) -> None:
    with pytest.raises(ValueError):
        exhaustive_short_cases(max_length=max_length)
