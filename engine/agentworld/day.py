"""One day: everyone plans at once, the six slots are played out, then the body and the books settle."""
from __future__ import annotations

import math
import pickle
import statistics
from collections import defaultdict
from pathlib import Path

from .. import llm_agent
from .. import recorder as recording
from ..agent_prompts import build_agent_vote_prompt, hold_agent_meeting
from ..knowledge import Knowledge
from . import body as physiology
from . import clerk, economy, prompts
from .actions import Cursor, SlotIntent, advance, execute_instant, execute_main, leave_org
from .clerk import OrgStep, Step
from .config import SLOTS
from .contest import Reactor, resolve_covert, resolve_violent
from .model import Org, Person
from .world import World


def _write(stream: str, payload: dict) -> None:
    recorder = recording.active()
    if recorder is not None:
        recorder.write(stream, payload)


def _names(world: World, name: str) -> list[str]:
    return sorted(world.acquaintances.get(name, set()))


def _places(world: World, name: str) -> list[str]:
    return sorted(world.people[name].known_places)


# ---- planning
def make_plans(world: World) -> None:
    c = world.config
    callers: list[tuple[Person, tuple[str, ...]]] = []
    for person in world.living():
        felt = tuple(physiology.felt(person.body, c))
        knowledge = world.knowledge.get(person.name)
        unread = knowledge.unread if knowledge else 0
        # a routine they chose is kept without asking again, until something reaches them or their body changes
        if person.habit and person.plan_steps and unread == 0 and felt == person.felt_at_plan:
            continue
        callers.append((person, felt))
    texts = [prompts.plan_prompt(world, p.name) for p, _ in callers]
    for person, _ in callers:
        world.knowledge.setdefault(person.name, Knowledge()).mark_read()
    declarations = llm_agent.run_concurrently(
        [
            lambda p=p, t=t: llm_agent.call_llm_decision(t, prompts.DayDeclaration, c.llm, temperature=p.temperature, label=f"plan:{p.name}")
            for (p, _), t in zip(callers, texts)
        ],
        c.llm,
    )
    spoken: list[tuple[Person, str, list[str]]] = []
    for (person, felt), declaration in zip(callers, declarations):
        person.felt_at_plan = felt
        if declaration is None:
            person.plan_steps, person.habit = [], False
            continue
        text = declaration.plan.strip()
        _write("plans", {
            "day": world.day, "person": person.name, "plan": text, "reasoning": declaration.reasoning,
            "same_as_yesterday": declaration.same_as_yesterday,
        })
        if declaration.same_as_yesterday and person.plan_steps:
            person.habit = True
            continue
        person.habit = declaration.same_as_yesterday
        if not text:
            person.plan_steps = []
            continue
        world.plans_today.append((person.name, text))
        world.tell(person.name, f"오늘의 계획: {text}", incoming=False)
        spoken.append((person, text, prompts.facts(world, person.name)))
    plans = llm_agent.run_concurrently(
        [
            lambda p=p, t=t, f=f: clerk.transcribe_plan(p.name, t, f, _names(world, p.name), _places(world, p.name), c.llm)
            for p, t, f in spoken
        ],
        c.llm,
    )
    for (person, text, _), plan in zip(spoken, plans):
        raw = plan.steps if plan is not None else [Step(op="intent", content=text)]
        person.plan_steps = clerk.keep_said(raw, text)
        _write("schedules", {
            "day": world.day, "person": person.name, "plan": text,
            "steps": [s.model_dump() for s in person.plan_steps], "clerk_steps": [s.model_dump() for s in raw],
        })


def llm_reactor(world: World) -> Reactor:
    def react(asks: list[tuple[Person, str]], slot: str) -> dict[str, list[Step]]:
        c = world.config
        replies = llm_agent.run_concurrently(
            [
                lambda p=p, s=s: llm_agent.call_llm_decision(
                    prompts.reaction_prompt(world, p.name, slot, s), prompts.Reaction, c.llm,
                    temperature=p.temperature, label=f"react:{p.name}",
                )
                for p, s in asks
            ],
            c.llm,
        )
        spoken = [(p, r.response.strip(), s) for (p, s), r in zip(asks, replies) if r is not None and r.response.strip()]
        plans = llm_agent.run_concurrently(
            [
                lambda p=p, t=t: clerk.transcribe_plan(
                    p.name, t, prompts.facts(world, p.name), _names(world, p.name), _places(world, p.name), c.llm, reaction=True,
                )
                for p, t, _ in spoken
            ],
            c.llm,
        )
        out: dict[str, list[Step]] = {}
        for (person, text, situation), plan in zip(spoken, plans):
            raw = plan.steps if plan is not None else [Step(op="intent", content=text)]
            out[person.name] = clerk.keep_said(raw, text)
            _write("reactions", {
                "day": world.day, "slot": slot, "person": person.name, "situation": situation, "response": text,
                "steps": [s.model_dump() for s in out[person.name]], "clerk_steps": [s.model_dump() for s in raw],
            })
        return out

    return react


# ---- a slot
def _notice_surroundings(world: World, person: Person, slot: str) -> None:
    place = world.map.places[person.location]
    seen = world.seen_today.setdefault(person.name, {}).setdefault(place.name, set())
    for other in world.at(place.name):
        if other.name != person.name:
            seen.add(other.name)
            world.acquaintances.setdefault(person.name, set()).add(other.name)
    for line in world.pending_losses.pop((place.name, person.name), []):
        world.tell(person.name, line, slot=slot)
    for offer in world.offers:
        org = world.org(offer.employer)
        if offer.worker == person.name and not offer.told and org is not None and person.location == org.building:
            offer.told = True
            world.tell(person.name, f"{org.name}이(가) 당신에게 일자리를 제안해 두었음: {offer.every_days}일마다 {offer.wage:g}", slot=slot)
    read = world.notices_read.setdefault(person.name, set())
    for notice in place.notices:
        key = (place.name, notice.author, notice.day, notice.text)
        if key not in read:
            read.add(key)
            world.tell(person.name, f"{place.name}에 {notice.author}이(가) 붙인 글: {notice.text}", source=notice.author, slot=slot)
    seen_corpses = world.seen_corpses.setdefault(person.name, set())
    for corpse in place.corpses:
        if corpse not in seen_corpses:
            seen_corpses.add(corpse)
            label = corpse if world.knows(person.name, corpse) else "모르는 사람"
            world.tell(person.name, f"{place.name}에 {label}의 시신이 있다", slot=slot)


def _on_death(world: World, person: Person, slot: str) -> None:
    place = world.map.places[person.location]
    place.corpses.append(person.name)
    for witness in world.awake_at(place.name, exclude={person.name}):
        world.seen_corpses.setdefault(witness.name, set()).add(person.name)
        world.tell(witness.name, f"{person.name}이(가) {place.name}에서 쓰러져 숨을 거둠", slot=slot)
    world.events_today.append(f"{slot} {place.name}: {person.name} 사망({person.body.cause_of_death})")
    _write("deaths", {"day": world.day, "slot": slot, "person": person.name, "place": place.name, "cause": person.body.cause_of_death})


def run_slot(world: World, cursors: dict[str, Cursor], slot_index: int, reactor: Reactor) -> None:
    c = world.config
    slot = SLOTS[slot_index]
    world.asleep, world.guarding, world.busy = set(), {}, set()
    intents: dict[str, SlotIntent] = {}
    arrivals: dict[str, str | None] = {}
    for person in world.living():
        cursor = cursors.setdefault(person.name, Cursor(list(person.plan_steps)))
        if person.restrained_day == world.day:
            world.busy.add(person.name)
            intents[person.name] = SlotIntent()
            continue
        if person.body.sleep_debt >= c.collapse_debt:
            world.asleep.add(person.name)
            intents[person.name] = SlotIntent(main="sleep")
            world.log(person.name, f"{slot}: 너무 지쳐 쓰러져 잠듦")
            continue
        intent = advance(world, person, cursor, slot_index)
        intents[person.name] = intent
        if intent.main == "travel":
            world.busy.add(person.name)
            arrivals[person.name] = intent.arrive_at
        elif intent.main == "sleep":
            world.asleep.add(person.name)
        elif intent.main == "guard":
            world.guarding[person.name] = intent.main_step.target or person.location

    for person in world.living():
        if person.name not in world.asleep and person.name not in world.busy:
            _notice_surroundings(world, person, slot)

    acting = [p for p in world.living() if intents[p.name].instants]
    world.rng.shuffle(acting)  # simultaneous acts still need an order for the arithmetic; it is drawn, not chosen
    for person in acting:
        for step in intents[person.name].instants:
            if person.alive:
                execute_instant(world, person, step, slot)

    for org in list(world.orgs.values()):
        _maybe_meet(world, org, slot)

    contesting = [p for p in world.living() if intents.get(p.name) and intents[p.name].contests]
    world.rng.shuffle(contesting)
    for person in contesting:
        for step in intents[person.name].contests:
            if not person.alive or person.restrained_day == world.day:
                break
            resolve = resolve_violent if step.op in ("attack", "rob") else resolve_covert
            resolve(world, person, step, slot, reactor, cursors)

    for person in world.living():
        intent = intents.get(person.name)
        if intent is not None and intent.main and person.restrained_day != world.day:
            execute_main(world, person, intent, slot)

    for person in list(world.living()):
        physiology.slot_update(person.body, person.name in world.asleep, c)
        if not person.alive:
            _on_death(world, person, slot)

    for name, place in arrivals.items():
        person = world.people[name]
        if person.alive and place:
            world.arrive(person, place)


# ---- organisations
def _maybe_meet(world: World, org: Org, slot: str) -> None:
    c = world.config
    if not org.alive or not org.agenda:
        return
    living = [m for m in org.members if m in world.people and world.people[m].alive]
    present = [p for p in world.awake_at(org.building) if p.name in org.members]
    if not living or len(present) < math.ceil(len(living) / 2):
        return
    proposal = org.agenda.pop(0)

    def build(member, transcript):
        return build_agent_vote_prompt(
            member.name, org.name, prompts.facts(world, member.name), prompts.org_lines(world, member.name),
            prompts.known_lines(world, member.name), proposal.proposer, proposal.text, transcript,
        )

    final, rounds = hold_agent_meeting(present, build, c.llm, rounds=c.llm.council_discussion_rounds, label_prefix=f"council:{org.name}")
    roster = [p.name for p in present]
    recorder = recording.active()
    if recorder is not None:
        recorder.record_meeting(tick_index=world.day, company=org.name, action_description=proposal.text, roster=roster, all_rounds=rounds)
    votes = [r for r in final if r is not None]
    yes = sum(1 for v in votes if v.support_action)
    passed = bool(votes) and yes > len(votes) / 2
    verdict = "가결" if passed else "부결"
    line = f"{world.day}일째 {slot} {proposal.proposer}의 안건 \"{proposal.text[:80]}\" {verdict} (찬성 {yes}/{len(votes)}, 모인 사람 {len(present)})"
    org.resolutions.append(line)
    for member in present:
        world.tell(member.name, f"{org.name} 회의: {line}", slot=slot)
    if not passed:
        return
    known = sorted(set().union(*(world.acquaintances.get(p.name, set()) for p in present)) | set(org.members))
    plan = clerk.transcribe_resolution(org.name, proposal.text, org.members, known, prompts.org_lines(world, present[0].name), c.llm)
    raw = plan.steps if plan is not None else [OrgStep(op="intent", content=proposal.text)]
    steps = clerk.keep_said(raw, proposal.text)
    results = [_org_step(world, org, step, slot) for step in steps]
    _write("resolutions", {
        "day": world.day, "slot": slot, "org": org.name, "proposer": proposal.proposer, "proposal": proposal.text,
        "steps": [s.model_dump() for s in steps], "clerk_steps": [s.model_dump() for s in raw],
        "results": [{"ok": ok, "detail": detail} for ok, detail in results],
    })


def _org_step(world: World, org: Org, step: OrgStep, slot: str) -> tuple[bool, str]:
    target = world.person(step.target)
    if step.op == "pay":
        receiver_org = world.org(step.target)
        if (target is None or not target.alive) and receiver_org is None:
            return False, f"대상 없음: {step.target}"
        if step.amount is None or step.amount <= 0 or org.money < step.amount:
            return False, "금액이 없거나 조직의 주화가 모자람"
        org.money -= step.amount
        if target is not None:
            target.money += step.amount
            world.tell(target.name, f"{org.name}이(가) 당신에게 주화 {step.amount:g}을 줌", source=org.name, slot=slot)
        else:
            receiver_org.money += step.amount
        _write("payments", {"day": world.day, "slot": slot, "from": org.name, "to": step.target, "what": f"주화 {step.amount:g}", "for": step.content})
        return True, f"{step.target}에게 {step.amount:g}"
    if step.op == "give_goods":
        if target is None or target.location != org.building or not step.good or step.qty is None:
            return False, "받을 사람이 건물에 없거나 물건·수량이 없음"
        bag = world.stash(org.building, org.name)
        if economy.holding(bag, step.good) < step.qty:
            return False, f"창고에 {step.good}이(가) 모자람"
        economy._add(bag, step.good, -step.qty)
        economy._add(target.inventory, step.good, step.qty)
        return True, f"{step.target}에게 {step.good} {step.qty:g}"
    if step.op == "set_wage":
        if target is None or target.name not in org.members or step.amount is None:
            return False, "구성원이나 금액이 없음"
        contract = next((k for k in world.contracts if k.employer == org.name and k.worker == target.name), None)
        if contract is None:
            economy.offer_job(world, org.name, target.name, step.amount, 7)
            economy.accept_job(world, target, org.name)
        else:
            contract.wage = step.amount
        return True, f"{target.name} 급여 {step.amount:g}"
    if step.op == "hire":
        if target is None:
            return False, f"대상 없음: {step.target}"
        ok, detail = economy.offer_job(world, org.name, target.name, step.amount, step.qty)
        if ok and target.location == org.building:
            world.offers[-1].told = True
            world.tell(target.name, f"{org.name}이(가) 당신에게 일자리를 제안함: {detail}", slot=slot)
        return ok, detail
    if step.op == "fire":
        if target is None or target.name not in org.members:
            return False, "구성원이 아님"
        leave_org(world, target)
        world.tell(target.name, f"{org.name}에서 내보내짐", slot=slot)
        return True, f"{target.name} 내보냄"
    if step.op == "issue":
        return economy.issue_notes(world.stash(org.building, org.name), org.name, step.qty)
    return True, step.content


# ---- the day
def end_day(world: World, snapshot_dir: Path | None) -> dict:
    c = world.config
    for person in world.living():
        physiology.day_update(person.body, True, c)
        if not person.alive:
            _on_death(world, person, "밤")
    for person in world.living():
        lines = world.day_log.get(person.name, [])
        if lines:
            world.tell(person.name, "오늘 한 일: " + " / ".join(lines[-12:]), incoming=False)
        seen = {place: names for place, names in world.seen_today.get(person.name, {}).items() if names}
        if seen:
            world.tell(person.name, "오늘 본 사람: " + "; ".join(f"{p}에서 {', '.join(sorted(n))}" for p, n in seen.items()), incoming=False)
        for line in world.losses_to_tell.pop(person.name, []):
            world.tell(person.name, line)
    economy.payday(world)
    economy.settle_bank(world)
    economy.regenerate(world)

    money = economy.money_report(world)
    trades_today = [t for t in world.trades if t.day == world.day]
    prices: dict[str, list[float]] = defaultdict(list)
    for trade in trades_today:
        prices[trade.good].append(trade.price)
    summary = {
        "day": world.day, "alive": len(world.living()), "dead": [p.name for p in world.people.values() if not p.alive],
        "trades": len(trades_today), "prices": {g: round(statistics.median(v), 3) for g, v in prices.items()},
        "money": money, "events": list(world.events_today),
        "orgs": {o.name: {"money": o.money, "tech": round(o.tech, 2), "members": len(o.members), "alive": o.alive} for o in world.orgs.values()},
    }
    _write("days", summary)
    _write("bodies", {"day": world.day, "people": {
        p.name: {"alive": p.alive, "health": round(p.body.health, 1), "strength": round(p.body.strength, 2), "reserve": round(p.body.reserve, 2),
                 "underfed_days": p.body.underfed_days, "sleep_debt": p.body.sleep_debt, "illness": p.body.illness,
                 "addiction": round(p.body.addiction, 2), "injuries": [i.kind for i in p.body.injuries],
                 "location": p.location, "money": p.money, "inventory": dict(p.inventory)}
        for p in world.people.values()
    }})
    _write_digest(world, summary)
    world.day_log, world.seen_today, world.events_today, world.plans_today = {}, {}, [], []
    world.day += 1
    if snapshot_dir is not None:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        with (snapshot_dir / f"day_{world.day - 1:03d}.pkl").open("wb") as f:
            pickle.dump(world, f)
    return summary


def _write_digest(world: World, summary: dict) -> None:
    recorder = recording.active()
    if recorder is None:
        return
    money = summary["money"]
    lines = [
        f"## {summary['day']}일째",
        f"- 살아 있는 사람 {summary['alive']}명" + (f", 죽은 사람: {', '.join(summary['dead'])}" if summary["dead"] else ""),
        f"- 거래 {summary['trades']}건" + (f", 중간 가격: {summary['prices']}" if summary["prices"] else ""),
        f"- 주화 {money['coins']:.1f}, 지폐 {money['notes']}, 은행 대출 잔액 {money['loans_outstanding']:.1f}",
    ]
    lines += [f"- {event}" for event in summary["events"]]
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
