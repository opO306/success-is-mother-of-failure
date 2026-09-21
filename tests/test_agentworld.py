import pickle
import random

import pytest

import engine.llm_agent as llm_agent
from engine.agent_prompts import AgentVote
from engine.agentworld import body as physiology
from engine.agentworld import economy
from engine.agentworld.actions import Cursor
from engine.agentworld.clerk import DayPlan, OrgPlan, OrgStep, Step, keep_said
from engine.agentworld.config import WorldConfig
from engine.agentworld.day import make_plans, run_slot, step_day
from engine.agentworld.model import Bank, Body, Org, Person, Place, WorldMap
from engine.agentworld.prompts import DayDeclaration, Reaction, plan_prompt
from engine.agentworld.scenario import build_world
from engine.agentworld.world import World, note_name
from engine.entities import Proposal

NAMES = ["P1", "P2", "P3", "P4"]


def tiny_world() -> World:
    m = WorldMap()
    m.add_place(Place("마을", "마을"))
    m.add_place(Place("시장", "시장"))
    m.add_place(Place("은행", "은행"))
    m.add_place(Place("농지", "농지", deposits={"식량": 100.0}, yields={"식량": 2.0}))
    m.add_place(Place("먼곳", "숲", deposits={"목재": 50.0}, yields={"목재": 3.0}))
    m.add_place(Place("조직 건물", "조직 건물"))
    m.connect("마을", "시장", 1)
    m.connect("시장", "은행", 0)
    m.connect("마을", "농지", 0)
    m.connect("마을", "먼곳", 2)
    m.connect("마을", "조직 건물", 0)
    people = {}
    for name in NAMES:
        home = f"{name}의 집"
        m.add_place(Place(home, "집", village="마을"))
        m.connect("마을", home, 0)
        people[name] = Person(name=name, home=home, location=home, money=20.0, inventory={"식량": 3.0}, body=Body(strength=20.0))
    for person in people.values():
        person.known_places = set(m.places)
    orgs = {"조직": Org("조직", "조직 건물", money=100.0, tech=5.0, members=["P1", "P2", "P3"])}
    for name in ["P1", "P2", "P3"]:
        people[name].org = "조직"
    world = World(config=WorldConfig(), map=m, people=people, orgs=orgs, bank=Bank(coins=100.0), rng=random.Random(0))
    for name in NAMES:
        world.acquaintances[name] = (set(NAMES) - {name}) | {"조직"}
    return world


def no_reaction(asks, slot):
    return {}


def play(world, plans: dict[str, list[Step]], slots=range(6), reactor=no_reaction, cursors=None):
    cursors = cursors if cursors is not None else {name: Cursor(list(steps)) for name, steps in plans.items()}
    for slot_index in slots:
        run_slot(world, cursors, slot_index, reactor)
    return cursors


def _patch_llm(monkeypatch, respond):
    calls = []

    def fake(prompt, schema, config, temperature=None, label=""):
        calls.append((label, schema, prompt))
        return respond(schema, label, prompt)

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    return calls


# ---- map and time
def test_travel_takes_the_slots_the_road_takes(world=None):
    world = tiny_world()
    cursors = play(world, {"P1": [Step(op="go", target="먼곳"), Step(op="work", good="목재")]}, slots=[0])
    assert world.people["P1"].location == "마을"  # still on the two-slot road
    play(world, {}, slots=[1], cursors=cursors)
    assert world.people["P1"].location == "먼곳"
    assert "목재" not in world.people["P1"].inventory
    play(world, {}, slots=[2], cursors=cursors)
    assert world.people["P1"].inventory["목재"] > 0


def test_nobody_goes_somewhere_they_have_never_heard_of():
    world = tiny_world()
    world.people["P1"].known_places = {"P1의 집", "마을"}
    play(world, {"P1": [Step(op="go", target="먼곳")]}, slots=[0, 1, 2])
    assert world.people["P1"].location == "P1의 집"


def test_words_reach_only_people_awake_in_the_same_place():
    world = tiny_world()
    for name in ["P1", "P2", "P3"]:
        world.people[name].location = "시장"
    world.people["P4"].location = "마을"
    play(world, {"P1": [Step(op="talk", target="여기", content="밀가루 값이 오른다")], "P3": [Step(op="sleep")]}, slots=[0])
    heard = {name: any("밀가루" in e.text for e in world.knowledge.get(name).entries) if world.knowledge.get(name) else False for name in NAMES}
    assert heard == {"P1": False, "P2": True, "P3": False, "P4": False}


def test_a_note_arrives_only_when_the_carrier_hands_it_over():
    world = tiny_world()
    world.people["P1"].location = world.people["P2"].location = "시장"
    world.people["P3"].location = "마을"
    play(world, {"P1": [Step(op="note", target="P2", recipient="P3", content="오늘 밤 창고")]}, slots=[0])
    assert not world.knowledge.get("P3")
    world.people["P2"].location = "마을"
    play(world, {"P2": [Step(op="deliver", target="P3")]}, slots=[1])
    assert any("오늘 밤 창고" in e.text for e in world.knowledge["P3"].entries)


# ---- body
def test_going_hungry_becomes_malnutrition_then_illness_then_death():
    c = WorldConfig()
    body = Body(reserve=0.0)
    for day in range(1, 60):
        physiology.day_update(body, True, c)
        if day == c.malnutrition_after_days:
            assert physiology.malnourished(body, c)
            assert any("제대로 먹지 못한" in line for line in physiology.felt(body, c))
        if day == c.malnutrition_illness_after_days:
            assert body.illness >= c.illness_onset
        if not body.alive:
            break
    assert not body.alive and day > c.starvation_after_days


def test_a_day_of_food_and_sleep_keeps_a_body_whole():
    c = WorldConfig()
    body = Body()
    for _ in range(20):
        physiology.eat(body, "식량", 1.0)
        body.slept_today = 2
        physiology.day_update(body, True, c)
    assert body.alive and body.health == 100.0 and body.underfed_days == 0 and body.sleep_debt == 0


def test_without_sleep_the_body_weakens_and_finally_sleeps_on_its_own():
    world = tiny_world()
    person = world.people["P1"]
    fresh = physiology.capability(person.body, world.config)
    person.body.sleep_debt = world.config.collapse_debt
    assert physiology.capability(person.body, world.config) < fresh
    play(world, {"P1": [Step(op="work", good="식량")]}, slots=[0])
    assert person.body.slept_today == 1


def test_a_deep_wound_bleeds_until_someone_treats_it():
    c = WorldConfig()
    body = Body()
    physiology.wound(body, heavy=True)
    after_wound = body.health
    for _ in range(3):
        physiology.slot_update(body, False, c)
    assert body.health == after_wound - 3 * c.bleeding_health_loss_per_slot
    physiology.use(body, "약", c)
    for _ in range(3):
        physiology.slot_update(body, False, c)
    assert body.health == after_wound - 3 * c.bleeding_health_loss_per_slot


def test_training_builds_strength_only_on_a_fed_body():
    c = WorldConfig()
    fed, hungry = Body(strength=20.0), Body(strength=20.0, reserve=0.0)
    for body in (fed, hungry):
        body.trained_today = 3
    physiology.eat(fed, "식량", 1.0)
    for body in (fed, hungry):
        body.eaten_today += 0.0
    hungry.underfed_days = 0
    physiology.day_update(fed, True, c)
    physiology.day_update(hungry, True, c)
    assert fed.strength > 20.0
    assert hungry.strength == 20.0


def test_an_addicted_body_suffers_without_the_drug():
    c = WorldConfig()
    body = Body()
    for _ in range(2):
        physiology.use(body, "아편", c)
        physiology.eat(body, "식량", 1.0)
        body.slept_today = 2
        physiology.day_update(body, True, c)
    assert body.addiction >= c.addiction_threshold
    assert physiology.withdrawing(body, c)
    assert physiology.capability(body, c) < physiology.capability(Body(), c)


# ---- economy
def test_work_depletes_the_deposit_and_better_tech_gets_more_out():
    world = tiny_world()
    low, high = world.people["P1"], world.people["P4"]
    low.location = high.location = "농지"
    world.orgs["조직"].tech = 0.0
    high.tech = 20.0
    economy.extract(world, low, "식량", for_org=False)
    economy.extract(world, high, "식량", for_org=False)
    got_low = low.inventory["식량"] - 3.0
    got_high = high.inventory["식량"] - 3.0
    assert got_high > got_low
    assert world.map.places["농지"].deposits["식량"] == pytest.approx(100.0 - got_low - got_high)


def test_making_things_needs_the_know_how_and_the_materials():
    world = tiny_world()
    maker = world.people["P1"]
    assert economy.craft(world, maker, "머스킷", None, False) == (False, "머스킷을(를) 만들 기술이 없음")
    assert not economy.craft(world, maker, "칼", None, False)[0]
    maker.inventory["철"] = 1.0
    assert economy.craft(world, maker, "칼", None, False)[0]
    assert maker.inventory["칼"] == 1.0 and "철" not in maker.inventory


def test_a_market_trade_happens_at_the_price_already_on_the_board():
    world = tiny_world()
    seller, buyer = world.people["P1"], world.people["P2"]
    seller.location = buyer.location = "시장"
    economy.post_order(world, seller, "sell", "식량", 2, 3, "낮")
    economy.post_order(world, buyer, "buy", "식량", 2, 5, "낮")
    assert seller.money == 26.0 and buyer.money == 14.0
    assert buyer.inventory["식량"] == 5.0
    assert [(t.good, t.qty, t.price) for t in world.trades] == [("식량", 2, 3)]


def test_coins_are_conserved_and_only_notes_grow_the_money_supply():
    world = tiny_world()
    before = economy.money_report(world)
    person = world.people["P1"]
    person.location = "은행"
    ok, _ = economy.borrow(world, person, 50.0)
    assert ok
    world.contracts.append(economy.Contract("조직", "P2", 10.0, 1, world.day))
    economy.payday(world)
    after = economy.money_report(world)
    assert after["coins"] == pytest.approx(before["coins"])
    assert after["money_supply"] == pytest.approx(before["money_supply"] + 50.0)
    assert economy.redeem_notes(world, person, "은행", 50.0)[0]  # the bank holds 100 coins
    economy.issue_notes(world.people["P2"].inventory, "P3", 10.0)
    world.people["P3"].money = 0.0
    world.people["P2"].location = world.people["P3"].location = "시장"
    assert economy.redeem_notes(world, world.people["P2"], "P3", 5.0) == (False, "P3에게 바꿔줄 주화가 없음")


def test_the_bank_will_not_put_out_more_notes_than_its_coins_allow():
    world = tiny_world()
    world.config.bank_max_principal = 1000.0
    person = world.people["P1"]
    person.location = "은행"
    assert economy.borrow(world, person, 300.0)[0]
    assert economy.borrow(world, person, 1.0) == (False, "은행이 거절(더 내줄 수 없음)")
    assert person.inventory[note_name("은행")] == 300.0


# ---- contests
def test_a_sleeping_target_is_jumped_without_being_asked():
    world = tiny_world()
    world.people["P1"].location = world.people["P2"].location = "마을"
    asked = []

    def reactor(asks, slot):
        asked.extend(p.name for p, _ in asks)
        return {}

    play(world, {"P1": [Step(op="attack", target="P2")], "P2": [Step(op="sleep")]}, slots=[0], reactor=reactor)
    assert "P2" not in asked
    assert world.people["P2"].body.injuries
    assert "attackers" in world.events_today[-1]


def test_an_even_fight_goes_back_to_the_fighters_before_chance_settles_it():
    world = tiny_world()
    world.people["P1"].location = world.people["P2"].location = "마을"
    asked = []

    def reactor(asks, slot):
        asked.append(sorted(p.name for p, _ in asks))
        return {p.name: [Step(op="attack", target="P2" if p.name == "P1" else "P1")] for p, _ in asks}

    play(world, {"P1": [Step(op="attack", target="P2")]}, slots=[2], reactor=reactor)
    assert asked == [["P2"], ["P1", "P2"]]
    assert "우연 몫" in world.events_today[-1]


def test_a_night_theft_from_a_sleeping_home_is_only_found_out_later():
    world = tiny_world()
    thief, owner = world.people["P1"], world.people["P2"]
    owner.inventory = {}
    world.stash("P2의 집", "P2")["식량"] = 5.0
    thief.location = "P2의 집"
    play(world, {"P1": [Step(op="steal", target="P2", good="식량", qty=2)], "P2": [Step(op="sleep")]}, slots=[5])
    assert thief.inventory["식량"] == 5.0
    assert not any("없어졌다" in e.text for e in world.knowledge.get("P2", type("K", (), {"entries": []})()).entries)
    play(world, {"P2": []}, slots=[0])
    assert any("식량 2이(가) 없어졌다" in e.text for e in world.knowledge["P2"].entries)


def test_someone_awake_who_sees_a_theft_decides_what_to_do():
    world = tiny_world()
    thief, witness = world.people["P1"], world.people["P2"]
    world.stash("조직 건물", "조직")["식량"] = 10.0
    thief.location = witness.location = "조직 건물"
    thief.org = None
    world.orgs["조직"].members.remove("P1")

    def reactor(asks, slot):
        return {p.name: [Step(op="attack", target="P1")] if p.name == "P2" else [Step(op="attack", target="P2")] for p, _ in asks}

    witness.body.strength = 40.0
    play(world, {"P1": [Step(op="steal", target="조직", good="식량", qty=3)]}, slots=[2], reactor=reactor)
    assert world.stash("조직 건물", "조직")["식량"] == 10.0
    assert thief.restrained_day == world.day


def test_nobody_carries_off_more_than_a_body_can_hold_whatever_was_said():
    world = tiny_world()
    thief = world.people["P1"]
    world.stash("조직 건물", "조직")["식량"] = 50.0
    thief.location = "조직 건물"
    play(world, {"P1": [Step(op="steal", target="조직", good="식량")]}, slots=[5])
    assert thief.inventory["식량"] == 3.0 + world.config.carry_limit
    assert world.stash("조직 건물", "조직")["식량"] == 50.0 - world.config.carry_limit


def test_shouting_with_the_place_as_the_target_reaches_whoever_is_there():
    world = tiny_world()
    world.people["P1"].location = world.people["P2"].location = "시장"
    play(world, {"P1": [Step(op="talk", target="시장", content="싸게 판다")]}, slots=[0])
    assert any("싸게 판다" in e.text for e in world.knowledge["P2"].entries)


def test_any_name_for_the_only_thing_a_place_yields_is_that_thing():
    world = tiny_world()
    farmer = world.people["P1"]
    farmer.location = "농지"
    ok, detail = economy.extract(world, farmer, "감자", for_org=False)
    assert ok and farmer.inventory["식량"] > 3.0


# ---- orgs
def test_only_members_at_the_building_get_a_vote(monkeypatch):
    world = tiny_world()
    world.people["P1"].location = world.people["P2"].location = "조직 건물"
    world.people["P3"].location = "시장"
    world.orgs["조직"].agenda.append(Proposal("P1", "창고의 식량을 나눈다", 1))

    def respond(schema, label, prompt):
        if schema is AgentVote:
            return AgentVote(support_action=True, reasoning="좋다")
        if schema is OrgPlan:
            return OrgPlan(steps=[OrgStep(op="intent", content="나눈다")])
        return None

    calls = _patch_llm(monkeypatch, respond)
    play(world, {}, slots=[2])
    voters = {label.split(":")[-1] for label, schema, _ in calls if schema is AgentVote}
    assert voters == {"P1", "P2"}
    assert world.orgs["조직"].resolutions


# ---- planning
def test_a_chosen_routine_is_kept_without_asking_again(monkeypatch):
    world = tiny_world()

    def respond(schema, label, prompt):
        if schema is DayDeclaration:
            return DayDeclaration(plan="식량 하나 먹고 밤에 두 칸 잔다", same_as_yesterday=True)
        if schema is DayPlan:
            return DayPlan(steps=[Step(op="eat", good="식량", qty=1), Step(slot="밤", op="sleep", slots=2)])
        return None

    calls = _patch_llm(monkeypatch, respond)
    step_day(world, reactor=no_reaction)
    first = sum(1 for label, *_ in calls if label.startswith("plan:"))
    step_day(world, reactor=no_reaction)
    second = sum(1 for label, *_ in calls if label.startswith("plan:")) - first
    assert first == 4 and second == 0


def test_prompts_carry_no_origin_era_or_bank_terms():
    world = build_world(seed=0)
    prompt = plan_prompt(world, next(iter(world.people)))
    for word in ["DOOMSAYER", "SAFETY", "GROWTH", "CONGLOMERATE", "산업혁명", "이자", "기업", "직업", "해결사", "자경단"]:
        assert word not in prompt


def test_keep_said_reads_korean_counts_and_drops_unsaid_numbers():
    step = Step(op="sell", good="식량", qty=2, price=3)
    assert keep_said([step], "식량 두 개를 하나에 3씩 판다")[0] == step
    dropped = keep_said([step], "식량을 판다")[0]
    assert dropped.qty is None and dropped.price is None
    # a number inside a name is not an amount anyone said
    assert keep_said([Step(op="give", target="P30", amount=30)], "P30에게 돈을 준다")[0].amount is None
    assert keep_said([Step(op="sell", good="물고기", qty=3, price=2)], "물고기 세 마리를 하나에 2씩 판다")[0].qty == 3


def test_money_never_moves_the_wrong_way_on_a_misheard_verb():
    # seen with the real 8B: "빚 20을 갚는다" transcribed as borrow
    step = keep_said([Step(op="borrow", amount=20)], "은행에 들러 빚 20을 갚는다")[0]
    assert step.op == "intent" and step.amount is None
    assert keep_said([Step(op="borrow", amount=20)], "은행에서 20을 빌린다")[0].op == "borrow"


# ---- whole world
def _simple_day(monkeypatch):
    def respond(schema, label, prompt):
        if schema is DayDeclaration:
            return DayDeclaration(plan="시장에 가서 식량 하나를 2에 팔고 하나를 2에 사서 먹고 잔다")
        if schema is DayPlan:
            return DayPlan(steps=[
                Step(op="go", target="시장"), Step(op="sell", good="식량", qty=1, price=2),
                Step(op="buy", good="식량", qty=1, price=2), Step(op="eat", good="식량", qty=1), Step(op="sleep", slots=2),
            ])
        if schema is Reaction:
            return Reaction(response="지켜본다")
        return None

    return _patch_llm(monkeypatch, respond)


def test_the_starting_world_runs_and_keeps_every_coin(monkeypatch):
    world = build_world(seed=0)
    assert len(world.people) == 48 and len(world.orgs) == 4
    coins = economy.money_report(world)["coins"]
    _simple_day(monkeypatch)
    for _ in range(2):
        step_day(world, reactor=no_reaction)
    assert economy.money_report(world)["coins"] == pytest.approx(coins)
    assert world.trades


def test_a_snapshot_continues_exactly_like_the_world_it_was_taken_from(monkeypatch):
    _simple_day(monkeypatch)
    world = build_world(seed=1, org_sizes=(2, 2, 1, 1), unaffiliated=2)
    step_day(world, reactor=no_reaction)
    copy = pickle.loads(pickle.dumps(world))
    step_day(world, reactor=no_reaction)
    step_day(copy, reactor=no_reaction)

    def state(w):
        return sorted((p.name, p.location, round(p.money, 6), round(p.body.health, 6), tuple(sorted(p.inventory.items()))) for p in w.people.values())

    assert state(world) == state(copy)
