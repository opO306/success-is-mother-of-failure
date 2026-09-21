import json

from engine.living.events import SeededEventSource
from engine.sequence import (
    ExperimentArchive,
    SequenceState,
    Strand,
    archive_experiment,
    parse_symbols,
    restore_experiment,
    restore_state,
    run_experiment,
    verify_archive,
)


def _experiment(events: int = 12):
    initial = SequenceState(
        (Strand(1, parse_symbols("TTT")), Strand(2, parse_symbols("AAA"))),
        thermal_energy=12,
    )
    return run_experiment(initial, SeededEventSource(91), events)


def test_every_frame_restores_exactly_from_periodic_checkpoints() -> None:
    experiment = _experiment()
    archive = archive_experiment(experiment, checkpoint_interval=3)

    assert restore_state(archive, -1) == experiment.initial_state
    for frame in experiment.frames:
        assert restore_state(archive, frame.index) == frame.state
    assert verify_archive(archive)


def test_archive_round_trip_preserves_digest_and_experiment() -> None:
    experiment = _experiment()
    archive = archive_experiment(experiment, checkpoint_interval=4)

    loaded = ExperimentArchive.from_canonical(archive.canonical())

    assert loaded == archive
    assert loaded.digest() == archive.digest()
    assert restore_experiment(loaded) == experiment


def test_event_tampering_is_detected_even_before_a_later_checkpoint() -> None:
    archive = archive_experiment(_experiment(), checkpoint_interval=3)
    raw = archive.canonical()
    raw["frames"][0]["event"]["payload"]["thermal_after"] += 1
    tampered = ExperimentArchive.from_canonical(raw)

    assert not verify_archive(tampered)


def test_checkpoint_tampering_is_detected() -> None:
    archive = archive_experiment(_experiment(), checkpoint_interval=3)
    raw = archive.canonical()
    raw["checkpoints"][1]["state"]["time"] += 1
    tampered = ExperimentArchive.from_canonical(raw)

    assert not verify_archive(tampered)


def test_archive_omits_repeated_full_state_frames() -> None:
    experiment = _experiment(events=24)
    archive = archive_experiment(experiment, checkpoint_interval=8)
    full = {
        "initial": experiment.initial_state.canonical(),
        "states": [frame.state.canonical() for frame in experiment.frames],
        "events": [frame.event.canonical() for frame in experiment.frames],
    }

    archive_bytes = len(json.dumps(archive.canonical(), separators=(",", ":")))
    full_bytes = len(json.dumps(full, separators=(",", ":")))

    assert archive_bytes < full_bytes


def test_quiescent_empty_experiment_round_trips() -> None:
    initial = SequenceState((Strand(1, (0,)),), thermal_energy=0)
    experiment = run_experiment(initial, SeededEventSource(1), max_events=10)
    archive = archive_experiment(experiment, checkpoint_interval=4)

    assert archive.frames == ()
    assert restore_experiment(archive) == experiment
    assert verify_archive(archive)
