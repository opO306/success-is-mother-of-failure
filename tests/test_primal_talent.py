import json
import random
import statistics
import sys

from engine import recorder as recording
from engine.primal import laws, talent
from engine.primal.actions import _experience
from engine.primal.clerk import Step
from engine.primal.laws import Outcome
from engine.primal.matter import Maker
from engine.primal.scenario import build_world


def test_talent_spreads_as_wide_as_the_study_with_mean_one_and_never_below_zero():
    drawn = [talent.draw(0, f"P{i}") for i in range(4000)]
    for family, spread in talent.SPREAD.items():
        for key in ("rate", "ceiling"):
            values = [d[family][key] for d in drawn]
            assert min(values) > 0
            assert abs(statistics.mean(values) - 1) < 0.03
            assert abs(statistics.stdev(values) / statistics.mean(values) - spread) < 0.03, (family, key)
    # drawn apart: good hands say nothing of a good hunter, and learning fast says nothing of how far one gets
    assert abs(statistics.correlation([d["hand"]["ceiling"] for d in drawn], [d["perceive"]["ceiling"] for d in drawn])) < 0.06
    assert abs(statistics.correlation([d["hand"]["rate"] for d in drawn], [d["hand"]["ceiling"] for d in drawn])) < 0.06


def test_talent_comes_from_its_own_stream_the_same_for_the_same_seed_and_is_average_when_turned_off():
    a, b = build_world(seed=5), build_world(seed=5)
    name = next(iter(a.people))
    assert talent.of(a, a.people[name]) == talent.of(b, b.people[name]) != talent.draw(6, name)
    person = a.people[name]
    state = a.rng.getstate()
    del person.__dict__["talent"]
    talent.of(a, person)
    assert a.rng.getstate() == state
    a.config.talent = False
    del person.__dict__["talent"]
    assert all(v == 1.0 for values in talent.of(a, person).values() for v in values.values())


def test_skill_grows_fast_then_slow_and_stops_at_their_own_ceiling():
    world = build_world(seed=0)
    person = next(iter(world.people.values()))
    rate = talent.of(world, person)["hand"]["rate"]
    top = talent.ceiling(world, person, "strike")
    assert abs(talent.practise(world, person, "strike") - talent.GAIN * rate) < 1e-9
    gains = [talent.practise(world, person, "strike") for _ in range(400)]
    assert all(later <= earlier for earlier, later in zip(gains, gains[1:]))
    assert 0.95 * top < person.skills["strike"] <= top
    assert talent.practice(person)["strike"] == 401
    assert len({round(talent.ceiling(world, p, "strike"), 6) for p in world.people.values()}) == len(world.people)


def test_someone_from_an_older_snapshot_lives_their_old_practice_again_under_their_talent():
    world = build_world(seed=0)
    person = next(iter(world.people.values()))
    del person.__dict__["talent"]
    person.skills.update({"strike": 3.5, "gather": 1.4})
    talent.of(world, person)
    assert talent.practice(person) == {"strike": 35, "gather": 14}
    assert person.skills["strike"] <= talent.ceiling(world, person, "strike")
    assert 0 < person.skills["gather"] < 1.4 * talent.of(world, person)["repeat"]["rate"]


def test_a_striker_past_the_old_line_of_one_makes_sharper_flakes():
    def sharpest(skill):
        maker = Maker(random.Random(0))
        flint, hammer = maker.make("부싯돌"), maker.make("강돌")
        out = laws.strike(hammer, flint, strength=0.3, skill=skill, maker=maker, rng=random.Random(1))
        return max(f.p("sharpness") for f in out.made)

    assert sharpest(1.5) > sharpest(1.0)


def test_the_feel_of_getting_better_follows_what_really_improved_and_fades_near_their_ceiling():
    world = build_world(seed=0)
    person = next(iter(world.people.values()))
    felt = []
    for _ in range(300):
        world.slot_features = {}
        _experience(world, person, Step(op="weave"), [], Outcome(True, []))
        felt.append(world.slot_features[person.name]["실력"])
    assert 0 < felt[0] <= 0.3
    assert all(later <= earlier + 1e-12 for earlier, later in zip(felt, felt[1:]))
    assert felt[-1] < 0.02


def test_pair_runs_every_seed_with_and_without_talent_and_finishes_a_pair_cut_off_in_its_talent_half(monkeypatch):
    import run_primal
    calls = []

    def fake(seed, days, resume, models=None, talent_on=True):
        calls.append((seed, resume, talent_on))
        return True if resume else talent_on

    monkeypatch.setattr(run_primal, "run_world", fake)
    monkeypatch.setattr(sys, "argv", ["run_primal.py", "--seed", "6", "--talent", "pair"])
    run_primal.main()
    assert calls == [(6, None, True), (6, None, False)]
    calls.clear()
    monkeypatch.setattr(sys, "argv", ["run_primal.py", "--seed", "6", "--talent", "pair", "--resume", "x.pkl"])
    run_primal.main()
    assert calls == [(6, "x.pkl", True), (6, None, False)]


def test_a_world_built_without_talent_has_everyone_average():
    world = build_world(seed=0, talent_on=False)
    assert not world.config.talent
    assert all(v == 1.0 for p in world.people.values() for values in talent.of(world, p).values() for v in values.values())


def test_talent_is_written_for_measuring_and_never_told(tmp_path):
    world = build_world(seed=0)
    run = recording.start_run("t", {}, root=tmp_path)
    try:
        talent.record(world)
    finally:
        recording.stop_run()
    rows = [json.loads(line) for line in (run.root / "talent.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(world.people) and set(rows[0]["talent"]) == set(talent.SPREAD)
    assert not any("재능" in e.text for k in world.knowledge.values() for e in k.entries)
