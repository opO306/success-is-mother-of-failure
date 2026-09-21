import json

import pytest

torch = pytest.importorskip("torch")

from engine.brain import brains, record  # noqa: E402


def test_a_recorded_day_has_a_frame_per_slot_a_row_per_person_and_is_plain_json():
    brain = brains.make("A", seed=0, learns=True)
    data = record.run(brain, 0, days=2, per_camp=2, energy=True, wildlife=True, puddles=True, plants=True, sky=True,
                      graded=True, animals=True)
    head = data["head"]
    assert len(data["frames"]) == 2 * len(head["slots"]) or data["meta"]["days_lived"] < 2
    frame = data["frames"][0]
    assert len(frame["people"]) == len(head["people"]) == 6
    assert all(len(row) == len(head["person_fields"]) for row in frame["people"])
    assert all(p["lat"] is not None for p in head["places"])
    chose = [row for f in data["frames"] for row in f["people"] if row[3] is not None]
    top = head["person_fields"].index("top")
    assert chose and all(row[top] for row in chose), "every choice carries its most likely options"
    json.dumps(data)
