import json

import pytest

from engine.living import HistoryLog, ReplayEventSource, SeededEventSource, WorldEvent


def _walk(seed, history=None):
    source = SeededEventSource(seed)
    position = 0
    draws = []
    for tick in range(20):
        direction = source.bernoulli(0.5)
        distance = source.uniform(0.0, 1.0)
        position += (1 if direction.value else -1) * distance.value
        draws.extend((direction.draw, distance.draw))
        if history is not None:
            history.append(direction.draw.as_event(tick))
            history.append(distance.draw.as_event(tick))
            history.append(WorldEvent.create(tick, "state.changed", {"position": position}))
    return position, source.draw_count, tuple(draws)


def test_recording_is_outside_the_world_and_does_not_change_randomness_or_result():
    history = HistoryLog()
    recorded = _walk(71, history)
    unrecorded = _walk(71, None)

    assert recorded == unrecorded
    assert history.verify()
    assert len(history.records) == 60


def test_different_seeds_can_produce_different_histories_without_changing_the_law():
    first = _walk(71, None)
    second = _walk(72, None)

    assert first[0] != second[0]
    assert first[1] == second[1] == 40


def test_history_is_hash_chained_serializable_and_detects_tampering():
    history = HistoryLog()
    _walk(5, history)
    encoded = history.to_json_lines()
    restored = HistoryLog.from_json_lines(encoded)
    assert restored.verify()
    assert restored.to_json_lines() == encoded

    lines = encoded.splitlines()
    raw = json.loads(lines[2])
    raw["event"]["payload"]["position"] = 999
    lines[2] = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError, match="digest"):
        HistoryLog.from_json_lines("\n".join(lines))


def test_event_payload_is_copied_before_the_observer_can_mutate_its_source():
    source = {"nested": {"values": [1, 2]}}
    event = WorldEvent.create(0, "structure.changed", source, subject_id=3)
    source["nested"]["values"].append(99)
    observed = event.payload()
    observed["nested"]["values"].append(100)

    assert event.payload() == {"nested": {"values": [1, 2]}}


def test_random_checkpoint_restores_the_exact_future_draws():
    source = SeededEventSource("lineage-a")
    source.unit()
    checkpoint = source.checkpoint()
    first_future = [source.unit().value for _ in range(5)]
    source.restore(checkpoint)
    second_future = [source.unit().value for _ in range(5)]

    assert first_future == second_future
    assert source.draw_count == checkpoint.draw_index + 5


def test_seed_and_rng_checkpoint_can_be_preserved_as_external_history():
    source = SeededEventSource(b"world-seed")
    history = HistoryLog()
    history.append(source.initialization_event())
    source.unit()
    history.append(source.checkpoint().as_event(1.0))

    initial = history.records[0].event.payload()
    checkpoint = history.records[1].event.payload()
    assert initial["algorithm"] == "python.random.MT19937"
    assert initial["seed"] == {"type": "bytes", "base64": "d29ybGQtc2VlZA=="}
    assert checkpoint["draw_index"] == 1
    assert checkpoint["state"]


def test_recorded_random_events_replay_without_access_to_the_original_rng():
    history = HistoryLog()
    final_position, _, _ = _walk(91, history)
    replay = ReplayEventSource.from_history(history)
    replay_position = 0.0
    for _ in range(20):
        direction = replay.bernoulli(0.5).value
        distance = replay.uniform(0.0, 1.0).value
        replay_position += (1 if direction else -1) * distance

    assert replay_position == final_position
    assert replay.exhausted()


def test_replay_stops_when_the_execution_path_differs_from_history():
    history = HistoryLog()
    _walk(91, history)
    replay = ReplayEventSource.from_history(history)

    with pytest.raises(ValueError, match="diverged"):
        replay.uniform(0.0, 1.0)


def test_invalid_event_and_probability_data_are_rejected():
    with pytest.raises(ValueError, match="finite JSON"):
        WorldEvent.create(0, "bad", {"value": float("nan")})
    with pytest.raises(ValueError, match="world_time"):
        WorldEvent.create(-1, "bad")
    with pytest.raises(ValueError, match="probability"):
        SeededEventSource(1).bernoulli(1.1)
