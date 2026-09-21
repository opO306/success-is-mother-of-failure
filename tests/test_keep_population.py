import json

import pytest

pytest.importorskip("torch")

from tools import keep_population  # noqa: E402


def test_worlds_keep_starting_until_the_deadline_and_each_leaves_a_line(tmp_path, monkeypatch):
    clock = iter([0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 99999.0])   # deadline, check, start, end, check, start, end, check
    monkeypatch.setattr(keep_population.time, "monotonic", lambda: next(clock))
    out = keep_population.main(["--brain", "A", "--days", "1", "--per-camp", "1", "--hours", "1", "--land", "old",
                                "--out", str(tmp_path / "keep")])
    rows = [json.loads(line) for line in (out / "worlds.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["seed"] for r in rows] == [7001, 7002] and all(r["last_day"] for r in rows)
