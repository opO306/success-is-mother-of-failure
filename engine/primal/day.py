"""A day in the primal land: everyone plans at once, six slots are lived, then bodies, minds and the land move on."""
from __future__ import annotations

import pickle
from collections import Counter
from pathlib import Path

from .. import llm_agent
from .. import recorder as recording
from ..agentworld import body as base_body
from ..agentworld.actions import advance
from ..knowledge import Knowledge
from . import body as physiology
from . import animals, clerk, contest, energy, experience, laws, leak, nature, origins, plants, prompts, sky, wildlife
from . import mind as minds
from .actions import CONTEST_OPS, DURATION_OPS, Cursor, SlotIntent, arrived, execute_instant, execute_main, failed_move
from .clerk import Step
from .config import SLOTS
from .contest import Reactor
from .world import Person, World


def _write(stream: str, payload: dict) -> None:
    recorder = recording.active()
    if recorder is not None:
        recorder.write(stream, payload)


def _felt(world: World, person: Person) -> tuple[str, ...]:
    return tuple(prompts.feelings(world, person.name))


# ---- planning
def make_plans(world: World) -> None:
    c = world.config
    callers = []
    for person in world.living():
        felt = _felt(world, person)
        knowledge = world.knowledge.get(person.name)
        if person.habit and person.plan_steps and (knowledge.unread if knowledge else 0) == 0 and felt == person.felt_at_plan:
            continue
        callers.append((person, felt))
    texts = []
    for person, _ in callers:
        person.plan_item_ids = [t.id for t in person.carried]
        texts.append(prompts.plan_prompt(world, person.name))
        world.knowledge.setdefault(person.name, Knowledge()).mark_read()
    declarations = llm_agent.run_concurrently(
        [lambda p=p, t=t: llm_agent.call_llm_decision(t, prompts.DayDeclaration, c.llm, temperature=p.temperature, label=f"plan:{p.name}")
         for (p, _), t in zip(callers, texts)],
        c.llm,
    )
    spoken = []
    for (person, felt), declaration in zip(callers, declarations):
        person.felt_at_plan = felt
        if declaration is None:
            person.plan_steps, person.habit = [], False
            continue
        text = declaration.plan.strip()
        hits = leak.words_in(text + " " + declaration.reasoning)
        if any(hits.values()):
            world.leaks_today[person.name] = hits["later_world"] + hits["technique_names"]
            _write("leaks", {"day": world.day, "person": person.name, **hits, "text": text})
        _write("plans", {"day": world.day, "person": person.name, "plan": text, "reasoning": declaration.reasoning,
                         "same_as_yesterday": declaration.same_as_yesterday})
        # where what they say they know came from: counted outside the world, never told to them
        claims = origins.judge(world, person, text + "\n" + declaration.reasoning)
        if claims:
            _write("knowledge_origins", {"day": world.day, "person": person.name, "claims": claims})
        experience.remember_thought(world, person, declaration.reasoning.strip())
        if declaration.same_as_yesterday and person.plan_steps:
            person.habit = True
            continue
        person.habit = declaration.same_as_yesterday
        if not text:
            person.plan_steps = []
            continue
        world.plans_today.append((person.name, text))
        world.tell(person.name, f"오늘의 계획: {text}", incoming=False)
        spoken.append((person, text, prompts.carried_lines(world, person.name)))
    plans = llm_agent.run_concurrently(
        [lambda p=p, t=t, items=items: clerk.transcribe(p.name, t, items, sorted(world.acquaintances.get(p.name, set())),
                                                        sorted(p.known_places), p.camp, c.llm)
         for p, t, items in spoken],
        c.llm,
    )
    for (person, text, _), plan in zip(spoken, plans):
        raw = plan.steps if plan is not None else [Step(op="intent", content=text)]
        person.plan_steps = clerk.keep_said(raw, text)
        _write("schedules", {"day": world.day, "person": person.name, "plan": text,
                             "steps": [s.model_dump() for s in person.plan_steps], "clerk_steps": [s.model_dump() for s in raw]})


def llm_reactor(world: World) -> Reactor:
    def react(asks: list[tuple[Person, str]], slot: str) -> dict[str, list[Step]]:
        c = world.config
        for person, _ in asks:
            person.plan_item_ids = [t.id for t in person.carried]
        replies = llm_agent.run_concurrently(
            [lambda p=p, s=s: llm_agent.call_llm_decision(prompts.reaction_prompt(world, p.name, slot, s), prompts.Reaction, c.llm,
                                                          temperature=p.temperature, label=f"react:{p.name}")
             for p, s in asks],
            c.llm,
        )
        spoken = [(p, r.response.strip(), s) for (p, s), r in zip(asks, replies) if r is not None and r.response.strip()]
        plans = llm_agent.run_concurrently(
            [lambda p=p, t=t: clerk.transcribe(p.name, t, prompts.carried_lines(world, p.name), sorted(world.acquaintances.get(p.name, set())),
                                               sorted(p.known_places), p.camp, c.llm, reaction=True)
             for p, t, _ in spoken],
            c.llm,
        )
        out = {}
        for (person, text, situation), plan in zip(spoken, plans):
            raw = plan.steps if plan is not None else [Step(op="intent", content=text)]
            out[person.name] = clerk.keep_said(raw, text)
            _write("reactions", {"day": world.day, "slot": slot, "person": person.name, "situation": situation, "response": text,
                                 "steps": [s.model_dump() for s in out[person.name]]})
        return out

    return react


# ---- a slot
def _notice(world: World, person: Person, slot: str) -> None:
    land = world.lands[person.location]
    seen = world.seen_today.setdefault(person.name, {}).setdefault(land.name, set())
    known = world.acquaintances.setdefault(person.name, set())
    for other in world.at(land.name):
        if other.name == person.name:
            continue
        if other.name not in known:
            world.tell(person.name, f"{land.name}에서 처음 보는 사람 {other.name}을(를) 봄", slot=slot)
            known.add(other.name)
            world.feature(person.name, "새로움", 1.0)
        seen.add(other.name)
    for corpse in land.corpses:
        if corpse not in world.seen_corpses.setdefault(person.name, set()):
            world.seen_corpses[person.name].add(corpse)
            world.tell(person.name, f"{land.name}에 {corpse if corpse in known else '모르는 사람'}의 시신이 있다", slot=slot)
            minds.event(person.mind, "안전", 15, f"{land.name}에서 시신을 본 때")
    person.encountered.update(g.kind for g in land.gather.values() if g.stock >= 1)
    person.encountered.update(t.kind for t in land.lying)
    person.encountered.update(h.species for h in world.herds if h.place == land.name and h.count > 0)
    if minds.is_new(person.mind, f"place:{land.name}"):
        world.feature(person.name, "새로움", 1.0)


def _on_death(world: World, person: Person, slot: str) -> None:
    land = world.lands[person.location]
    land.corpses.append(person.name)
    for witness in world.awake_at(land.name, exclude={person.name}):
        world.seen_corpses.setdefault(witness.name, set()).add(person.name)
        world.tell(witness.name, f"{person.name}이(가) {land.name}에서 쓰러져 숨을 거둠", slot=slot)
        minds.event(witness.mind, "안전", 25, f"{land.name}에서 {person.name}이(가) 죽는 것을 본 때")
    land.lying.extend(person.carried + person.worn)
    person.carried, person.worn = [], []
    world.events_today.append(f"{slot} {land.name}: {person.name} 사망({person.body.cause_of_death})")
    _write("deaths", {"day": world.day, "slot": slot, "person": person.name, "place": land.name, "cause": person.body.cause_of_death})


def run_slot(world: World, cursors: dict[str, Cursor], slot_index: int, reactor: Reactor) -> None:
    c = world.config
    slot = SLOTS[slot_index]
    world.asleep, world.busy, world.guarding = set(), set(), {}
    world.slot_features, world.slot_activity, world.slot_done = {}, {}, {}
    world.animal_acts = []
    distress_before = {p.name: physiology.distress(p.body, c) for p in world.living()}
    began = {p.name: experience.cue(world, p, distress_before[p.name]) for p in world.living()}
    if slot == "낮":
        for place in nature.lightning(world.lands, world.weather, world.rng, c, world.maker):
            world.events_today.append(f"{slot} {place}: 벼락으로 불이 남")
            for witness in world.at(place):
                world.tell(witness.name, "벼락이 떨어져 숲에 불이 붙었다", slot=slot)
                minds.event(witness.mind, "안전", 20, f"{place}에서 불길을 본 때")
                world.feature(witness.name, "위험", 1.0)
    for land in world.lands.values():
        nature.burn_slot(land, world.weather, len(world.at(land.name)))

    intents: dict[str, tuple[SlotIntent, bool]] = {}
    arrivals: dict[str, str | None] = {}
    for person in world.living():
        cursor = cursors.setdefault(person.name, Cursor(list(person.plan_steps)))
        if person.restrained_day == world.day:
            world.busy.add(person.name)
            intents[person.name] = (SlotIntent(), False)
            continue
        if c.sleep_switch:
            land = world.lands[person.location]
            lit = sky.light(slot, world.day, c, fire=land.fire is not None, raining=world.weather.raining)
            clock = sky.circadian_pressure(slot, person.body.chronotype, lit)
            lying = person.body.asleep or (cursor.index < len(cursor.steps) and cursor.steps[cursor.index].op == "sleep")
            person.body.asleep = physiology.sleep_switch(person.body, c, clock, lit, lying)
            if person.body.asleep:
                world.asleep.add(person.name)
                intents[person.name] = (SlotIntent(main="sleep"), True)
                continue
        elif person.body.sleep_debt >= c.collapse_debt:
            world.asleep.add(person.name)
            intents[person.name] = (SlotIntent(main="sleep"), True)
            continue
        leader = world.person(world.following.get(person.name))
        if leader is not None and leader.alive and cursor.index >= len(cursor.steps) and leader.location != person.location:
            cursor.replace_rest([Step(op="go", target=leader.location)])
        intent = advance(world, person, cursor, slot_index, duration_ops=DURATION_OPS, contest_ops=CONTEST_OPS, on_fail=failed_move)
        finished = cursor.remaining is None
        intents[person.name] = (intent, finished)
        if intent.main == "travel":
            world.busy.add(person.name)
            arrivals[person.name] = intent.arrive_at
        elif intent.main == "sleep" and not c.sleep_switch:   # with the switch, lying down awake is only rest
            world.asleep.add(person.name)
        elif intent.main == "guard":
            world.guarding[person.name] = intent.main_step.target or person.location
        elif intent.main == "hunt" and finished:
            world.slot_activity[person.name] = (f"hunt:{intent.main_step.target}", "")

    for person in world.living():
        if person.name not in world.asleep and person.name not in world.busy:
            _notice(world, person, slot)

    acting = [p for p in world.living() if intents[p.name][0].instants]
    world.rng.shuffle(acting)
    for person in acting:
        for step in intents[person.name][0].instants:
            if person.alive:
                execute_instant(world, person, step, slot)

    contesting = [p for p in world.living() if intents[p.name][0].contests]
    world.rng.shuffle(contesting)
    for person in contesting:
        for step in intents[person.name][0].contests:
            if person.alive and person.restrained_day != world.day:
                (contest.attack if step.op == "attack" else contest.steal)(world, person, step, slot, reactor, cursors)

    for person in world.living():
        intent, finished = intents[person.name]
        if intent.main and person.restrained_day != world.day:
            execute_main(world, person, intent, slot, finished)
    for name, records in world.slot_done.items():   # a mouth remembers the kinds it has had in it
        for record in records:
            if record["op"] in ("eat", "test") and record["ok"]:
                person = world.people.get(name)
                for thing in (person.carried[:1] if person else []):
                    world.tasted_kinds.setdefault(name, set()).add(thing.kind)

    temp = nature.air_temp(world.weather, slot, c)
    for person in world.living():
        awake_here = person.name not in world.asleep and person.name not in world.busy
        companions = [p.name for p in world.awake_at(person.location, exclude={person.name})] if awake_here else []
        features = dict(world.slot_features.get(person.name, {}))
        if companions:
            features["함께"] = max(features.get("함께", 0.0), min(1.0, len(companions) / 3))
        activity, context = world.slot_activity.get(person.name, ("idle", ""))
        land = world.lands[person.location]
        roof, warmth = nature.shelter_at(land, len(world.at(land.name)))
        asleep = person.name in world.asleep
        physiology.exposure(person.body, temp, world.weather.raining, person.clothing(), land.fire.heat if land.fire else 0.0,
                            roof, warmth, features.get("몸씀", 0.0), c)
        base_body.slot_update(person.body, asleep, c)
        if c.energy_balance:
            energy.slot_spend(person.body, intents[person.name][0].main, [r["op"] for r in world.slot_done.get(person.name, [])],
                              asleep, c.illness_onset)
        if asleep:
            person.body.slept_today -= 1 - minds.sleep_quality(person.mind)
        if c.sleep_switch:
            quality = minds.sleep_quality(person.mind)
            if asleep and c.graded_feelings:
                quality *= physiology.sleep_quality(person.body, c, physiology.felt_levels(person.body, c))
            physiology.pressure_slot(person.body, asleep, quality)
        # the body and the mind in the same slot: what presses now, and what lifted since the slot began
        before, after = distress_before.get(person.name, {}), physiology.distress(person.body, c)
        pressing = max(after.values(), default=0.0)
        lifted = {kind: before.get(kind, 0.0) - after.get(kind, 0.0) for kind in physiology.RELIEF_REASONS}
        relieved = max(lifted, key=lifted.get)
        relief = max(0.0, lifted[relieved])
        pleasure = 0.0
        if awake_here:
            moment = f"{slot}, {context or person.location + '에 있던 때'}"
            if companions:
                moment += f", 곁에 {', '.join(companions[:3])}{' 등' if len(companions) > 3 else ''}"
            pleasure = minds.experience(person.mind, features, activity, moment, companions, distress=pressing,
                                        relief=relief, relief_reason=physiology.RELIEF_REASONS[relieved] if relief > 0 else "")
        if pressing >= 0.5 and not asleep:
            worst_kind = max(after, key=after.get)
            minds.suffer(person.mind, 20 * pressing, f"{slot}, {person.location}에서 {physiology.SUFFERING[worst_kind]}")
        minds.slot_passes(person.mind, alone=not companions, distress=pressing)
        experience.record(world, person, slot, began.get(person.name), intents[person.name][0], after, relieved, relief, pleasure)

    if c.animal_minds:
        animals.slot(world, slot)
    elif c.wildlife:
        wildlife.slot(world, slot)
    else:
        contest.wolves_at_night(world, slot)

    for person in list(world.living()):
        if not person.body.alive:
            _on_death(world, person, slot)
    for person in world.people.values():
        if not person.alive and person.name not in world.lands[person.location].corpses:
            _on_death(world, person, slot)

    for name, place in arrivals.items():
        person = world.people[name]
        if person.alive and place:
            world.arrive(person, place)
            arrived(world, person, intents[name][0].main_step, slot)


# ---- the day
def seen_line(world: World, person: Person) -> str | None:
    """Who they saw today. The people of their own camp are told by who was missing when that is shorter: in the first run
    the same 14 names filled every memory each day, and people copied the list into their plans."""
    by_place = {place: names for place, names in world.seen_today.get(person.name, {}).items() if names}
    if not by_place:
        return None
    seen = set().union(*by_place.values())
    band = {p.name for p in world.people.values() if p.camp == person.camp and p.name != person.name}
    parts = []
    band_seen = seen & band
    missed = sorted(band - seen)  # the dead among them were not seen either; being unseen is all they know of it
    if band_seen:
        if not missed:
            parts.append("함께 지내는 사람 모두")
        elif len(missed) <= len(band_seen):
            parts.append(f"함께 지내는 사람 중 {', '.join(missed)}만 빼고 모두")
        else:
            parts.append("함께 지내는 사람 중 " + ", ".join(sorted(band_seen)))
    for place, names in by_place.items():
        others = sorted(n for n in names if n not in band)
        if others:
            parts.append(f"{place}에서 {', '.join(others)}")
    return "오늘 본 사람: " + "; ".join(parts)


def end_day(world: World, snapshot_dir: Path | None) -> dict:
    c = world.config
    for person in world.living():
        physiology.day_update(person.body, c)
    for person in world.people.values():
        if not person.alive and person.name not in world.lands[person.location].corpses:
            _on_death(world, person, "밤")
    for person in world.living():
        best, worst = minds.day_passes(person.mind)
        lines = world.day_log.get(person.name, [])
        if lines:
            world.tell(person.name, "오늘 한 일과 겪은 것: " + " / ".join(lines[-10:]), incoming=False)
        seen = seen_line(world, person)
        if seen:
            world.tell(person.name, seen, incoming=False)
        if best:
            world.tell(person.name, f"오늘 가장 좋았던 순간: {best}", incoming=False)
        if worst:
            world.tell(person.name, f"오늘 가장 괴로웠던 순간: {worst}", incoming=False)

    temp = world.weather.base_temp
    collapsed = []
    for land in world.lands.values():
        for thing in land.lying:
            laws.day_passes(thing, temp, sealed=False)
        nature.plantings_day(land, world.weather.season, c)
        if c.living_plants:
            plants.plants_day(land, world.weather, c)
            nature.soil_day(land, world.weather.raining)
        else:
            nature.regenerate(land, world.weather.season, world.weather.raining)
        for fallen in nature.storm_damage(land, world.weather):
            collapsed.append(land.name)
    for person in world.living():
        for thing in person.carried + person.worn:
            laws.day_passes(thing, temp, sealed=False)
    if c.animal_minds:
        moves = animals.day(world)
    else:
        moves = nature.herds_day(world.herds, world.lands, world.map, world.day, world.weather.season, world.rng, c)

    summary = {
        "day": world.day, "season": world.weather.season, "temp": round(world.weather.base_temp, 1), "rain": world.weather.raining,
        "storm": world.weather.storm, "alive": len(world.living()), "dead": [p.name for p in world.people.values() if not p.alive],
        "events": list(world.events_today), "herds": {f"{h.id}:{h.species}@{h.place}": h.count for h in world.herds},
        "herd_moves": moves, "structures": sum(1 for l in world.lands.values() for s in l.structures if s.complete),
        "fires": [l.name for l in world.lands.values() if l.fire], "plantings": sum(len(l.plantings) for l in world.lands.values()),
        "collapsed": collapsed, "leaks": dict(world.leaks_today),
    }
    _write("days", summary)
    _write("people", {"day": world.day, "people": {
        p.name: {"alive": p.alive, "place": p.location, "health": round(p.body.health, 1), "reserve": round(p.body.reserve, 2),
                 "hydration": round(p.body.hydration, 2), "cold": round(p.body.cold, 2), "sleep_debt": p.body.sleep_debt,
                 "needs": {k: round(v, 1) for k, v in p.mind.need.items()}, "temperament": {k: round(v, 2) for k, v in p.mind.temperament.items()},
                 "carried": Counter(t.kind for t in p.carried), "skills": {k: round(v, 2) for k, v in p.skills.items()},
                 "practice": dict(p.__dict__.get("practice", {}))}
        for p in world.people.values()
    }})
    _digest(world, summary)
    world.day_log, world.seen_today, world.events_today, world.plans_today = {}, {}, [], []
    world.following, world.leaks_today, world.hunts_done = {}, {}, set()
    world.day += 1
    world.weather = nature.weather_for(world.day, world.rng, c)
    if c.puddles:
        for land in world.lands.values():
            nature.puddles_day(land, world.weather)
    if snapshot_dir is not None:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        with (snapshot_dir / f"day_{world.day - 1:03d}.pkl").open("wb") as f:
            pickle.dump(world, f)
    return summary


def _digest(world: World, summary: dict) -> None:
    recorder = recording.active()
    if recorder is None:
        return
    sky = "폭풍" if summary["storm"] else ("비" if summary["rain"] else "맑음")
    lines = [
        f"## {summary['day']}번째 날 ({summary['season']}, {summary['temp']}도, {sky})",
        f"- 살아 있는 사람 {summary['alive']}명" + (f", 죽은 사람: {', '.join(summary['dead'])}" if summary["dead"] else ""),
        f"- 지어진 것 {summary['structures']}채, 불 {len(summary['fires'])}곳, 심은 것 {summary['plantings']}곳",
    ]
    lines += [f"- {event}" for event in summary["events"][:25]]
    if summary["leaks"]:
        lines.append(f"- 지식 누출 의심: {summary['leaks']}")
    for name, text in world.plans_today[:5]:
        lines.append(f"- {name}의 계획: {text[:160]}")
    with (recorder.root / "digest.md").open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")


def step_day(world: World, reactor: Reactor | None = None, snapshot_dir: Path | None = None) -> dict:
    reactor = reactor or llm_reactor(world)
    make_plans(world)
    cursors = {p.name: Cursor(list(p.plan_steps)) for p in world.living()}
    for slot_index in range(len(SLOTS)):
        run_slot(world, cursors, slot_index, reactor)
    return end_day(world, snapshot_dir)
