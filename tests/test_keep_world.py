import json

from tools import keep_world


def test_a_stopped_world_goes_on_from_its_last_whole_day_and_is_marked_once(tmp_path):
    run = tmp_path / "20260915-040000_primal_seed6_notalent"
    (run / "snapshots").mkdir(parents=True)
    (run / "meta.jsonl").write_text(json.dumps({"seed": 6, "resume": None}) + "\n", encoding="utf-8")
    assert keep_world.where_to_go_on(run) == (6, None)
    for day in (1, 2, 10):
        (run / "snapshots" / f"day_{day:03d}.pkl").write_bytes(b"")
    seed, resume = keep_world.where_to_go_on(run)
    assert seed == 6 and resume.endswith("day_010.pkl")
    keep_world.mark(run, 1, resume)
    keep_world.mark(run, 1, resume)
    rows = (run / "aborted.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1 and json.loads(rows[0])["resume_from"] == resume


def test_a_world_resumed_from_a_snapshot_that_stops_before_a_new_whole_day_goes_on_from_that_snapshot(tmp_path):
    run = tmp_path / "20260915-050000_primal_seed7"
    run.mkdir()
    (run / "meta.jsonl").write_text(json.dumps({"seed": 7, "resume": "runs/x/snapshots/day_004.pkl"}) + "\n", encoding="utf-8")
    assert keep_world.where_to_go_on(run) == (7, "runs/x/snapshots/day_004.pkl")
