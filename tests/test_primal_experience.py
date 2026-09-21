import json

import engine.llm_agent as llm_agent
from engine import recorder as recording
from engine.agentworld.actions import Cursor
from engine.primal import origins
from engine.primal.clerk import DayPlan, SpokenPlan, Step, spoken
from engine.primal.day import make_plans, run_slot
from engine.primal.prompts import DayDeclaration, plan_prompt
from engine.primal.scenario import build_world


def _rows(run, stream):
    path = run.root / f"{stream}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_a_claim_is_lived_only_after_the_body_went_through_it_heard_when_someone_said_it_and_none_otherwise():
    world = build_world(seed=0)
    person, other = [p for p in world.people.values() if p.camp == "남쪽 야영지"][:2]
    said = "비에 젖으면 몸이 떨리니 불 곁에 있자. 부싯돌로 불을 피운다. 마른 풀을 비벼 불을 붙인다"
    assert {c["relation"]: c["origin"] for c in origins.judge(world, person, said)} == {
        "wet_cold": "none", "flint_fire": "none", "rub_fire": "given"}
    origins.note_lived(person, "wet_cold", "1일 밤")
    world.tell(person.name, f"{other.name}이(가) 말함: 칡뿌리를 먹으면 허기가 가신다", source=other.name)
    judged = {c["relation"]: c["origin"] for c in origins.judge(world, person, said + ". 칡뿌리를 먹어 허기를 달랜다")}
    assert judged["wet_cold"] == "lived" and judged["food_hunger"] == "heard"
    # sentences from real runs that the first, looser patterns caught wrongly
    for sentence in ("점토와 풀을 더 모아 불을 지키기 위한 준비를 하려 한다",
                     "불이 붙지 않거나 준비가 부족해 실패했다",
                     "칡뿌리를 씹어 목마름을 달래고, 강돌을 이용해 부싯돌 조각의 날을 다듬어 본다",
                     "물을 찾아가며 목을 씻는다",
                     "가죽을 마른 나뭇가지로 문지르고, 저녁에는 불을 끄고 쉬자"):
        assert not {relation for relation, _ in origins.claims(sentence)} & {"rain_fire", "water_thirst", "rub_fire"}, sentence


def test_their_own_morning_thought_goes_into_their_memory_and_where_their_knowledge_came_from_is_never_told(monkeypatch, tmp_path):
    world = build_world(seed=0)
    first = next(iter(world.people))
    assert "속마음" in plan_prompt(world, first)

    def fake(prompt, schema, config, temperature=None, label=""):
        if schema is DayDeclaration:
            return DayDeclaration(plan="개울에 가서 물을 마신다", reasoning="목이 말라서 물부터 마시고 싶다. 비에 젖으면 추우니까")
        if schema is SpokenPlan:
            return spoken(DayPlan(steps=[Step(op="drink")]))
        return None

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    run = recording.start_run("t", {}, root=tmp_path)
    try:
        make_plans(world)
    finally:
        recording.stop_run()
    texts = [e.text for e in world.knowledge[first].entries]
    assert any("속으로 든 생각: 목이 말라서 물부터 마시고 싶다" in t for t in texts)
    assert not any(word in t for t in texts for word in ("none", "lived", "근거", "출처"))
    claims = next(r for r in _rows(run, "knowledge_origins") if r["person"] == first)["claims"]
    assert {c["relation"]: c["origin"] for c in claims} == {"water_thirst": "none", "wet_cold": "none"}


def test_a_slot_lived_is_recorded_with_what_was_on_them_what_they_did_and_what_it_did_to_the_body(tmp_path):
    world = build_world(seed=0)
    person = [p for p in world.people.values() if p.camp == "남쪽 야영지"][0]
    water = next(name for name, land in world.lands.items() if land.water == "맑은 물")
    person.location = water
    person.body.hydration, person.body.thirst_days = 0.0, 1
    run = recording.start_run("t", {}, root=tmp_path)
    try:
        run_slot(world, {person.name: Cursor([Step(op="drink")])}, 1, lambda asks, slot: {})
    finally:
        recording.stop_run()
    row = next(r for r in _rows(run, "experiences") if r["person"] == person.name)
    assert row["cue"]["felt"][0] == "thirst" and row["cue"]["place_kind"] == world.lands[water].kind
    assert [d["op"] for d in row["did"]] == ["drink"] and row["did"][0]["ok"]
    assert row["body"]["relieved"] == "thirst" and row["body"]["relief"] > 0 and row["how"] == "생각해서"
    assert origins.lived(person)["water_thirst"] == "1일 아침"
