import json

from tools import throughput_bench


def test_the_local_baseline_projects_to_the_ten_minute_day_actually_recorded():
    local = throughput_bench.projection(58.0, 375)
    assert 9 <= local["minutes_per_day"] <= 11
    assert 90 <= local["hours_per_generation"] <= 110
    assert throughput_bench.projection(580.0, 375)["hours_per_generation"] < 11


def test_only_answered_morning_plans_are_taken_as_prompts(tmp_path):
    rows = [{"label": "plan:P01", "ok": True, "prompt": "a", "temperature": 0.8},
            {"label": "clerk:P01", "ok": True, "prompt": "b", "temperature": 0.0},
            {"label": "plan:P02", "ok": False, "prompt": "c", "temperature": 0.8}]
    (tmp_path / "llm_calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert [r["prompt"] for r in throughput_bench.recorded_prompts(tmp_path, 10)] == ["a"]
