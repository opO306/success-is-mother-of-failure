import pickle
import re

import engine.llm_agent as llm_agent
from engine.agentworld.actions import Cursor
from engine.primal import leak
from engine.primal.clerk import DayPlan, SpokenPlan, Step, spoken
from engine.primal.day import run_slot, step_day
from engine.primal.nature import Fire
from engine.primal.prompts import DayDeclaration, Reaction, plan_prompt
from engine.primal.scenario import CAMPS, build_world
from engine.primal.senses import FORBIDDEN


def no_reaction(asks, slot):
    return {}


def _patch(monkeypatch, respond):
    calls = []

    def fake(prompt, schema, config, temperature=None, label=""):
        calls.append((label, schema, prompt))
        if schema is SpokenPlan:
            plan = respond(DayPlan, label, prompt)
            return spoken(plan) if plan is not None else None
        return respond(schema, label, prompt)

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    return calls


def play(world, plans, slots):
    cursors = {name: Cursor(list(steps)) for name, steps in plans.items()}
    for slot in slots:
        run_slot(world, cursors, slot, no_reaction)
    return cursors


def band_of(world, camp):
    return [p for p in world.people.values() if p.camp == camp]


def test_three_bands_start_apart_and_know_nothing_of_each_other():
    world = build_world(seed=0)
    assert len(world.people) == 45
    for i, a in enumerate(CAMPS):
        for b in CAMPS[i + 1:]:
            assert 4 <= world.map.route(a, b)[1] <= 8
    north = band_of(world, "북쪽 야영지")
    east_names = {p.name for p in band_of(world, "동쪽 야영지")}
    assert not (world.acquaintances[north[0].name] & east_names)
    assert "동쪽 야영지" not in north[0].known_places


def test_the_morning_prompt_names_no_law_technique_era_or_number_of_any_property():
    world = build_world(seed=0)
    prompt = plan_prompt(world, next(iter(world.people)))
    for word in FORBIDDEN + ("DOOMSAYER", "산업", "시뮬레이션"):
        assert word not in prompt, word
    assert not re.search(r"\d+\.\d", prompt)
    assert "1. " in prompt  # things they carry are listed so they can point at them


def test_a_winter_night_in_the_open_without_fire_or_cover_is_felt_and_hurts():
    world = build_world(seed=0)
    world.weather.base_temp = -10
    person = band_of(world, "북쪽 야영지")[0]
    person.worn = []
    person.location = "북쪽 숲"
    world.lands["북쪽 숲"].fire = None
    play(world, {person.name: [Step(op="sleep", slots=2)]}, [4, 5])
    assert person.body.cold >= world.config.cold_harm and person.body.health < 100


def test_those_by_the_camp_fire_in_their_cloaks_stay_warm():
    world = build_world(seed=0)
    world.weather.base_temp = -5
    world.weather.raining = world.weather.storm = False  # rain would put out an unroofed fire and soak them: a different test
    person = band_of(world, "북쪽 야영지")[0]
    world.lands["북쪽 야영지"].fire = Fire(heat=0.9, fuel_slots=10)
    play(world, {person.name: [Step(op="sleep", slots=2)]}, [4, 5])
    assert person.body.cold < world.config.cold_felt


def test_hunters_together_can_bring_down_what_one_cannot():
    world = build_world(seed=3)
    hunters = band_of(world, "북쪽 야영지")[:4]
    herd = next(h for h in world.herds if h.species == "사슴" and h.place == "북쪽 숲")
    herd.fear = 0.0
    for p in hunters:
        p.location = "북쪽 숲"
        p.body.strength = 28
        p.skills["hunt"] = 5.0
    before = herd.count
    play(world, {p.name: [Step(op="hunt", target="사슴")] for p in hunters}, [5])
    assert herd.count == before - 1
    assert any(t.kind == "사슴 사체" for t in world.lands["북쪽 숲"].lying)


def test_wolves_bite_whoever_sleeps_in_the_open_without_fire_and_not_by_a_fire():
    world = build_world(seed=0)
    sleeper = band_of(world, "북쪽 야영지")[0]
    sleeper.location = "산기슭"
    play(world, {sleeper.name: [Step(op="sleep", slots=2)]}, [5])
    assert sleeper.body.injuries
    world2 = build_world(seed=0)
    world2.weather.raining = world2.weather.storm = False  # in the rain an unroofed fire goes out and the wolves come anyway
    safe = band_of(world2, "북쪽 야영지")[0]
    safe.location = "산기슭"
    world2.lands["산기슭"].fire = Fire(heat=0.7, fuel_slots=10)
    play(world2, {safe.name: [Step(op="sleep", slots=2)]}, [5])
    assert not safe.body.injuries


def test_giving_something_warms_the_receiver_toward_the_giver():
    world = build_world(seed=0)
    giver, receiver = band_of(world, "남쪽 야영지")[:2]
    giver.plan_item_ids = [t.id for t in giver.carried]
    before = receiver.mind.need["인정"]
    play(world, {giver.name: [Step(op="give", target=receiver.name, items=[4])]}, [1])
    assert receiver.mind.bonds.get(giver.name, 0) > 0 and receiver.mind.need["인정"] < before + 1
    assert any(t.kind == "칡뿌리" for t in receiver.carried[-1:])


def test_a_follower_goes_where_the_one_they_follow_goes():
    world = build_world(seed=0)
    leader, follower = band_of(world, "동쪽 야영지")[:2]
    cursors = play(world, {follower.name: [Step(op="follow", target=leader.name)], leader.name: [Step(op="go", target="큰 강")]}, [0])
    run_slot(world, cursors, 1, no_reaction)
    run_slot(world, cursors, 2, no_reaction)
    assert leader.location == "큰 강" and follower.location == "큰 강"


def test_a_clerk_list_of_everything_carried_points_at_nothing(monkeypatch):
    from engine.primal import clerk

    def fake(prompt, schema, config, temperature=None, label=""):
        return spoken(DayPlan(steps=[Step(op="dry", items=[1, 2, 3, 4, 5], what="흙덩이"), Step(op="strike", items=[3, 1])]))

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    from engine.config import SimulationConfig

    plan = clerk.transcribe("P01", "흙덩이를 말리고 3번 돌로 1번을 친다", ["a", "b", "c", "d", "e"], [], [], "야영지", SimulationConfig())
    assert plan.steps[0].items == [] and plan.steps[0].what == "흙덩이"
    assert plan.steps[1].items == [3, 1]


def test_what_the_model_brings_from_its_own_world_is_counted():
    hits = leak.words_in("철로 만든 칼을 들고 시장에 가서 그릇을 판다")
    assert "철" in hits["later_world"] and "시장" in hits["later_world"] and "그릇" in hits["technique_names"]
    assert leak.words_in("고기를 요리해 먹고 사슴을 길들인다")["technique_names"] == ["길들인", "요리"]


def test_ordinary_words_that_contain_a_later_word_are_not_counted():
    # all 9 leaks of the first real run were these
    text = "불을 피우는 데 유리하다. 관계를 돈독히 하고 더 철저히 준비한다. 봄철에 개구리가 울어 시장하다."
    assert leak.words_in(text) == {"later_world": [], "technique_names": []}


def test_a_clerk_answer_cut_off_mid_loop_keeps_the_steps_written_out_whole():
    raw = ('{"steps": [{"동작": "이동", "target": "호수"}, {"동작": "마시기"}, {"동작": "말하기", "target": "P01", "content": "같이'
           ' 간다"}, {"동작": "말하기", "target": "P02", "cont')
    plan = SpokenPlan.salvage(raw)
    assert [s.동작 for s in plan.steps] == ["이동", "마시기", "말하기"]
    assert SpokenPlan.salvage('{"steps": [{"동작": "날기"}') is None


def test_the_same_words_to_a_list_of_names_are_said_once_to_those_around():
    from engine.primal.clerk import merge_repeated_talk

    words = "P45, P04, P18와 함께 한다."
    steps = [Step(op="fire")] + [Step(op="talk", target=n, content=words) for n in ("P45", "P04", "P18")] + [Step(op="talk", target="P09", content="물 마시러 가자")]
    merged = merge_repeated_talk(steps)
    assert [(s.op, s.target) for s in merged] == [("fire", None), ("talk", "여기"), ("talk", "P09")]


def test_a_walk_to_a_place_nobody_mentioned_is_not_kept():
    from engine.primal.clerk import keep_said_places

    places = ["남쪽 야영지", "남쪽 숲", "호수", "부싯돌 비탈", "북쪽 개울"]
    text = "개울가에서 물을 마시고 야영지로 돌아와 쉰다"
    steps = [Step(op="go", target="부싯돌 비탈"), Step(op="go", target="북쪽 개울"), Step(op="drink"), Step(op="go", target="야영지"),
             Step(op="rest"), Step(op="go", target="큰 바위 언덕")]
    kept = keep_said_places(steps, text, places, "남쪽 야영지")
    assert [(s.op, s.target) for s in kept] == [("go", "북쪽 개울"), ("drink", None), ("go", "남쪽 야영지"), ("rest", None)]
    said_but_unknown = keep_said_places([Step(op="go", target="동굴")], "동굴에 가 본다", places, "남쪽 야영지")
    assert said_but_unknown[0].target == "동굴"  # still tried, and the walker finds out they do not know the way


def test_being_with_someone_is_not_a_walk_to_a_place_named_after_them():
    from engine.primal.clerk import keep_said_places

    places = ["북쪽 야영지", "북쪽 개울"]
    text = "북쪽 개울에서 물을 마시고 P06과 함께 이야기한다. 무서우면 P16에게 달아난다"
    steps = [Step(op="go", target="북쪽 개울"), Step(op="drink"), Step(op="go", target="P06"), Step(op="talk", target="P06", content="안녕"),
             Step(op="flee", target="P16")]
    kept = keep_said_places(steps, text, places, "북쪽 야영지", ["P06", "P16"])
    assert [(s.op, s.target) for s in kept] == [("go", "북쪽 개울"), ("drink", None), ("talk", "P06"), ("flee", None)]


def test_a_walk_that_arrives_is_in_the_record_and_adds_nothing_to_what_they_are_told(tmp_path):
    import json

    from engine import recorder as recording

    world = build_world(seed=0)
    walker = band_of(world, "동쪽 야영지")[0]
    run = recording.start_run("t", {}, root=tmp_path)
    try:
        play(world, {walker.name: [Step(op="go", target="큰 강")]}, [0, 1, 2])
    finally:
        recording.stop_run()
    rows = [json.loads(line) for line in (run.root / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    walks = [r for r in rows if r["person"] == walker.name and r["step"]["op"] == "go"]
    assert walker.location == "큰 강" and walks and all(r["ok"] for r in walks) and walks[-1]["place"] == "큰 강"
    assert not any("큰 강:" in line for line in world.day_log.get(walker.name, []))


def test_a_walk_that_cannot_start_is_remembered_in_plain_words_not_engine_ops():
    world = build_world(seed=0)
    person = band_of(world, "남쪽 야영지")[0]
    play(world, {person.name: [Step(op="go", target="야반")]}, [0])
    line = world.day_log[person.name][-1]
    assert "모른다" in line and "go" not in line and "실패" not in line


def test_the_best_moment_says_what_they_were_doing_and_who_was_there():
    world = build_world(seed=0)
    world.weather.raining = True
    person, *_ = band_of(world, "남쪽 야영지")
    world.lands[person.location].fire = None
    play(world, {person.name: [Step(op="fire", items=[1])]}, [1])
    best, _ = __import__("engine.primal.mind", fromlist=["day_passes"]).day_passes(person.mind)
    assert "불을 피우던 때" in best and "곁에" in best and "intent" not in best


def test_who_they_saw_names_the_missing_of_their_own_camp_instead_of_everyone():
    from engine.primal.day import seen_line

    world = build_world(seed=0)
    person, missing, *rest = band_of(world, "남쪽 야영지")
    stranger = band_of(world, "동쪽 야영지")[0]
    world.seen_today[person.name] = {person.location: {p.name for p in rest}, "호수": {stranger.name}}
    line = seen_line(world, person)
    assert line == f"오늘 본 사람: 함께 지내는 사람 중 {missing.name}만 빼고 모두; 호수에서 {stranger.name}"


def test_thirst_arrives_as_a_body_feeling_and_a_thought_at_once_and_does_not_hide_a_restless_mind():
    world = build_world(seed=0)
    person = band_of(world, "남쪽 야영지")[0]
    person.body.hydration, person.body.thirst_days = 0.0, 1
    person.mind.need["호기심"] = 75
    lines = prompts_feelings(world, person.name)
    assert lines[0].startswith("목이 타들어 가고") and "물 말고는 아무 생각도" in lines[0]
    assert any("궁금하다" in line for line in lines[1:])
    prompt = plan_prompt(world, person.name)
    assert "지금 몸과 마음에 오는 것:" in prompt and "마음:" not in prompt


def test_a_need_is_felt_faintly_before_it_overwhelms():
    from engine.primal import mind as minds

    import random

    mind = minds.new_mind(random.Random(0), 20)
    assert minds.felt(mind) == ["마음은 대체로 편하다"]
    for level, words in ((35, "조금 궁금한"), (65, "이것저것 궁금하다"), (90, "견딜 수가 없다")):
        mind.need["호기심"] = level
        lines = [line for line in minds.felt(mind) if "궁금" in line]
        assert len(lines) == 1 and words in lines[0]


def prompts_feelings(world, name):
    from engine.primal.prompts import feelings

    return feelings(world, name)


def test_a_body_in_distress_enjoys_less_and_grows_uneasy():
    from engine.primal import mind as minds

    import random

    calm, parched = minds.new_mind(random.Random(1), 20), minds.new_mind(random.Random(1), 20)
    features = {"함께": 1.0, "새로움": 1.0}
    assert minds.experience(calm, features, "talk", "이야기") > minds.experience(parched, features, "talk", "이야기", distress=1.0)
    before = parched.need["안전"]
    minds.slot_passes(parched, alone=False, distress=1.0)
    assert parched.need["안전"] > before


def test_water_to_a_parched_throat_is_the_best_moment_and_says_why():
    world = build_world(seed=0)
    person, mate = band_of(world, "남쪽 야영지")[:2]
    water = next(name for name, land in world.lands.items() if land.water == "맑은 물")
    person.location = mate.location = water
    person.body.hydration, person.body.thirst_days = 0.0, 1
    play(world, {person.name: [Step(op="drink")], mate.name: [Step(op="rest")]}, [1])
    from engine.primal import mind as minds

    best, _ = minds.day_passes(person.mind)
    assert "물을 마시던 때" in best and "목마름이 가셔서" in best and best.endswith("좋았다")


def test_a_day_spent_parched_is_remembered_as_the_worst_moment():
    world = build_world(seed=0)
    person = band_of(world, "남쪽 야영지")[0]
    person.body.hydration, person.body.thirst_days = 0.0, 1
    play(world, {person.name: [Step(op="rest")]}, [2])
    from engine.primal import mind as minds

    _, worst = minds.day_passes(person.mind)
    assert worst.endswith("목이 타들어 가던 때")


class _Answer:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self.content}, "prompt_eval_count": 10, "eval_count": 800, "done_reason": "length"}


def test_a_greedy_call_that_fails_on_its_answer_is_not_asked_again(monkeypatch):
    import requests
    from engine.config import SimulationConfig

    posts = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: posts.append(k) or _Answer('{"plan": "끝나지 않은'))
    assert llm_agent.call_llm_decision("p", DayDeclaration, SimulationConfig(), temperature=0.0) is None
    assert len(posts) == 1
    assert llm_agent.call_llm_decision("p", DayDeclaration, SimulationConfig(), temperature=0.7) is None
    assert len(posts) == 1 + SimulationConfig().llm_max_retries


def test_the_clerk_asks_for_a_capped_answer_and_keeps_what_was_whole(monkeypatch):
    import requests
    from engine.config import SimulationConfig
    from engine.primal import clerk

    posts = []
    raw = '{"steps": [{"동작": "이동", "target": "호수"}, {"동작": "마시기"}, {"동작": "말하기", "target": "P0'
    monkeypatch.setattr(requests, "post", lambda *a, **k: posts.append(k["json"]) or _Answer(raw))
    plan = clerk.transcribe("P01", "호수에 가서 물을 마신다", ["a"], ["P02"], ["호수"], "남쪽 야영지", SimulationConfig())
    assert [s.op for s in plan.steps] == ["go", "drink"]
    assert posts[0]["options"]["num_predict"] == SimulationConfig().clerk_max_output_tokens
    assert "num_predict" not in SimulationConfig().__dict__ or SimulationConfig().llm_max_output_tokens is None


def _day_plan(world):
    def respond(schema, label, prompt):
        name = label.split(":")[-1]
        person = world.people.get(name)
        water = person and next(p for p in sorted(person.known_places) if world.lands[p].water == "맑은 물")
        if schema is DayDeclaration:
            # the place has to be in the words: a walk to a place nobody said is not kept
            return DayDeclaration(plan=f"{water}에 가서 물을 마시고 돌을 줍고, 돌아와 뿌리를 먹고 잔다")
        if schema is DayPlan:
            return DayPlan(steps=[
                Step(op="go", target=water), Step(op="drink"), Step(op="gather", what="강돌"), Step(op="go", target=person.camp),
                Step(op="eat", items=[4]), Step(slot="밤", op="sleep", slots=2),
            ])
        if schema is Reaction:
            return Reaction(response="지켜본다")
        return None

    return respond


def test_a_band_day_runs_end_to_end_and_people_remember_their_best_moment(monkeypatch):
    world = build_world(seed=0)
    _patch(monkeypatch, _day_plan(world))
    for _ in range(2):
        step_day(world, reactor=no_reaction)
    drank = [p for p in world.people.values() if p.body.thirst_days == 0]
    assert len(drank) == len(world.people)
    assert any("가장 좋았던 순간" in e.text for k in world.knowledge.values() for e in k.entries)
    assert world.day == 3


def test_a_snapshot_continues_exactly_like_the_world_it_was_taken_from(monkeypatch):
    world = build_world(seed=2, band_size=4)
    _patch(monkeypatch, _day_plan(world))
    step_day(world, reactor=no_reaction)
    copy = pickle.loads(pickle.dumps(world))
    _patch(monkeypatch, _day_plan(copy))
    step_day(copy, reactor=no_reaction)
    _patch(monkeypatch, _day_plan(world))
    step_day(world, reactor=no_reaction)

    def state(w):
        return sorted((p.name, p.location, round(p.body.health, 6), round(p.mind.need["즐거움"], 6), len(p.carried)) for p in w.people.values())

    assert state(world) == state(copy)
