"""When one person's act meets another's body. Outcomes come from who was actually there, awake, and how strong;
the people involved get asked what they do. Chance only settles what the world has no information to settle."""
from __future__ import annotations

from collections.abc import Callable

from .. import recorder as recording
from . import body as physiology
from . import economy
from .actions import Cursor
from .clerk import Step
from .config import NIGHT_SLOTS
from .model import Person
from .world import World

# people and what they are seeing -> each person's steps in response
Reactor = Callable[[list[tuple[Person, str]], str], dict[str, list[Step]]]
FIGHT_OPS = frozenset({"attack", "rob"})


def power(world: World, person: Person, consume: bool) -> tuple[float, str | None]:
    c = world.config
    base = person.body.strength * physiology.capability(person.body, c)
    inventory = person.inventory
    if economy.holding(inventory, "머스킷") >= 1 and economy.holding(inventory, "화약") >= 1:
        if consume:
            economy._add(inventory, "화약", -1)
        return base + c.weapon_power["머스킷"], "머스킷"
    for weapon in ("칼", "도구"):
        if economy.holding(inventory, weapon) >= 1:
            return base + c.weapon_power[weapon], weapon
    return base, None


def _record(world: World, kind: str, payload: dict) -> None:
    fight_result = payload.get("fight") or {}
    world.events_today.append(
        f"{payload.get('slot')} {payload.get('place')}: {kind} {payload.get('actor')} → "
        f"{payload.get('owner') or payload.get('target')} ({payload.get('outcome') or fight_result.get('winner')}"
        f"{', 우연 몫 ' + str(fight_result['chance_share']) if fight_result.get('chance_share') else ''})"
    )
    recorder = recording.active()
    if recorder is not None:
        recorder.write("contests", {"day": world.day, "kind": kind, **payload})


def _witnesses(world: World, place: str, text: str, slot: str, exclude: set[str]) -> None:
    for person in world.awake_at(place, exclude=exclude):
        world.tell(person.name, text, slot=slot)


def fight(
    world: World, attackers: list[Person], defenders: list[Person], slot: str, reactor: Reactor,
    cursors: dict[str, Cursor], surprise: bool,
) -> dict:
    c = world.config
    fled: list[str] = []
    reasked = False
    chance_share = 0.0

    def totals(consume: bool) -> tuple[float, float, dict[str, tuple[float, str | None]]]:
        detail = {p.name: power(world, p, consume) for p in attackers + defenders}
        a = sum(detail[p.name][0] for p in attackers) * (c.surprise_factor if surprise else 1.0)
        d = sum(detail[p.name][0] for p in defenders)
        return a, d, detail

    a, d, detail = totals(consume=False)
    ratio = abs(a - d) / (a + d) if a + d > 0 else 0.0
    if ratio < c.fight_close_ratio and attackers and defenders:
        # nobody is clearly winning: everyone in it gets to decide once more before anything is left to chance
        reasked = True
        situation = "몸싸움이 벌어졌는데 힘이 비슷해 결판이 나지 않고 있다. 상대: {others}"
        asks = [
            (p, situation.format(others=", ".join(q.name for q in (defenders if p in attackers else attackers))))
            for p in attackers + defenders
        ]
        responses = reactor(asks, slot)
        for side in (attackers, defenders):
            for p in list(side):
                steps = responses.get(p.name, [])
                if any(s.op == "flee" for s in steps):
                    side.remove(p)
                    fled.append(p.name)
                    cursors.setdefault(p.name, Cursor()).replace_rest([s for s in steps if s.op == "flee"])
                elif not any(s.op in FIGHT_OPS for s in steps):
                    side.remove(p)  # stopped fighting: gave up, talked, or froze
        a, d, detail = totals(consume=False)
        ratio = abs(a - d) / (a + d) if a + d > 0 else 0.0

    if not attackers and not defenders:
        winner = None
    elif not defenders:
        winner = "attackers"
    elif not attackers:
        winner = "defenders"
    elif ratio < c.fight_close_ratio:
        chance_share = 1.0 - ratio / c.fight_close_ratio
        winner = "attackers" if world.rng.random() < a / (a + d) else "defenders"
    else:
        winner = "attackers" if a > d else "defenders"

    injuries: dict[str, str] = {}
    if winner and attackers and defenders:
        a, d, detail = totals(consume=True)
        winners, losers = (attackers, defenders) if winner == "attackers" else (defenders, attackers)
        musket = any(detail[p.name][1] == "머스킷" for p in winners)
        for loser in losers:
            mortal = musket and ratio >= c.mortal_ratio
            heavy = mortal or musket or ratio >= c.heavy_injury_ratio
            physiology.wound(loser.body, heavy, c.mortal_health_loss if mortal else 0.0)
            injuries[loser.name] = "치명상" if mortal else ("깊은 상처" if heavy else "가벼운 상처")
        if ratio < 0.2:
            for p in winners:
                physiology.wound(p.body, heavy=False)
                injuries[p.name] = "가벼운 상처"
    result = {
        "attackers": [p.name for p in attackers], "defenders": [p.name for p in defenders], "surprise": surprise,
        "power": {name: {"power": round(v[0], 2), "weapon": v[1]} for name, v in detail.items()},
        "ratio": round(ratio, 3), "reasked": reasked, "chance_share": round(chance_share, 3),
        "winner": winner, "fled": fled, "injuries": injuries,
    }
    return result


def _target_person(world: World, actor: Person, name: str | None) -> Person | None:
    if not name:
        return None
    target = world.person(name)
    if target is None or target.location != actor.location or target.name in world.busy:
        return None
    return target


def _notice(world: World, actor: Person, observers: list[Person], owner: str | None, slot: str) -> tuple[list[Person], dict]:
    c = world.config
    stealth = actor.skills.get("은밀", 0.0)
    stealth += c.stealth_night_bonus if slot in NIGHT_SLOTS else 0.0
    stealth += c.stealth_tool_bonus if economy.holding(actor.inventory, "도구") >= 1 else 0.0
    noticed: list[Person] = []
    checks = {}
    for observer in observers:
        attention = c.attention_awake
        guarded = world.guarding.get(observer.name)
        if guarded in (actor.location, owner, actor.name):
            attention += c.attention_guarding
        if observer.name == owner:
            attention += 2.0  # it is their own pocket
        margin = attention - stealth
        if margin > c.detection_close_margin:
            seen, chance = True, 0.0
        elif margin < -c.detection_close_margin:
            seen, chance = False, 0.0
        else:
            chance = 1.0 - abs(margin) / c.detection_close_margin
            seen = world.rng.random() < 0.5 + margin / (2 * c.detection_close_margin)
        checks[observer.name] = {"attention": attention, "stealth": round(stealth, 2), "seen": seen, "chance_share": round(chance, 3)}
        if seen:
            noticed.append(observer)
    actor.skills["은밀"] = actor.skills.get("은밀", 0.0) + c.skill_gain_per_slot
    return noticed, checks


def _source_bag(
    world: World, actor: Person, owner: str | None, good: str | None, wants_money: bool,
) -> tuple[dict[str, float] | None, str, str | None]:
    """Where the thing being taken physically is: on someone's body here, in their home, in their org's building, on a corpse."""
    if not owner:
        return None, "", None
    here = actor.location
    person = world.people.get(owner)
    if person is not None:
        on_body = person.location == here and (not person.alive or person.name not in world.busy)
        home = world.stash(here, person.name) if person.home == here else None
        if on_body and (wants_money or home is None or economy.holding(person.inventory, good or "") > 0):
            return person.inventory, ("시신" if not person.alive else "몸"), person.name
        if home is not None and not wants_money:
            return home, "집", person.name
        return None, "", None
    org = world.orgs.get(owner)
    if org is not None and org.building == here:
        return world.stash(here, org.name), "창고", org.name
    return None, "", None


def _move(bag: dict[str, float], dest: dict[str, float] | None, good: str | None, qty: float | None, limit: float) -> float:
    """Unsaid or not, nobody walks off with more than a body can carry; the engine never picks "all of it"."""
    if not good:
        return 0.0
    wanted = limit if qty is None else min(qty, limit)
    moved = min(economy.holding(bag, good), wanted)
    if moved <= 0:
        return 0.0
    economy._add(bag, good, -moved)
    if dest is not None:
        economy._add(dest, good, moved)
    return moved


def _take_money(world: World, actor: Person, owner: str, amount: float | None, destroy: bool = False) -> float:
    person = world.people.get(owner)
    org = world.orgs.get(owner)
    holder = person if person is not None else org
    if holder is None:
        return 0.0
    # an amount nobody named is capped like any other load, never "everything they had"
    moved = min(holder.money, amount if amount is not None else world.config.carry_limit)
    holder.money -= moved
    if not destroy:
        actor.money += moved
    return moved


def resolve_covert(world: World, actor: Person, step: Step, slot: str, reactor: Reactor, cursors: dict[str, Cursor]) -> None:
    """steal / sabotage: done quietly; whoever is awake there may notice and may do something about it."""
    wants_money = step.amount is not None or (step.good or "") in ("주화", "돈")
    bag, where, owner = _source_bag(world, actor, step.target, step.good, wants_money)
    if owner is None:
        from .actions import record
        record(world, actor, step, slot, False, f"{step.target}의 물건이 이곳에 없음")
        return
    observers = world.awake_at(actor.location, exclude={actor.name})
    noticed, checks = _notice(world, actor, observers, owner, slot)
    verb = "몰래 가져가려는" if step.op == "steal" else "망가뜨리려는"
    what = "주화" if wants_money else (step.good or "물건")
    stopped_by: list[Person] = []
    fight_result = None
    if noticed:
        responses = reactor([(p, f"{actor.name}이(가) {owner}의 {what}을(를) {verb} 것을 봤다") for p in noticed], slot)
        for observer in noticed:
            steps = responses.get(observer.name, [])
            _carry_out_talk(world, observer, steps, slot)
            if any(s.op in FIGHT_OPS and s.target in (None, actor.name) for s in steps):
                stopped_by.append(observer)
        if stopped_by:
            fight_result = fight(world, [actor], stopped_by, slot, reactor, cursors, surprise=False)
    succeeded = not stopped_by or (fight_result is not None and fight_result["winner"] in ("attackers", None) and actor.name not in fight_result["fled"])
    moved = 0.0
    if succeeded:
        destroy = step.op == "sabotage"
        if wants_money:
            moved = _take_money(world, actor, owner, step.amount, destroy)
        else:
            moved = _move(bag, None if destroy else actor.inventory, step.good, step.qty, world.config.carry_limit)
        victim = world.people.get(owner)
        if moved > 0 and victim is not None and victim.alive and victim.name not in [p.name for p in noticed]:
            line = f"{where}에 있던 {what} {moved:g}이(가) 없어졌다" if where != "몸" else f"지니고 있던 {what} {moved:g}이(가) 없어졌다"
            if where == "몸":
                world.losses_to_tell.setdefault(victim.name, []).append(line)
            else:
                world.pending_losses.setdefault((actor.location, victim.name), []).append(line)
    elif fight_result is not None and fight_result["winner"] == "defenders":
        actor.restrained_day = world.day
    outcome = "성공" if succeeded and moved > 0 else ("저지당함" if not succeeded else "가져갈 것이 없음")
    for observer in noticed:
        world.tell(observer.name, f"{actor.name}이(가) {owner}의 {what}을(를) {verb} 것을 봄: {outcome}", slot=slot)
    if noticed:
        world.tell(actor.name, f"{', '.join(p.name for p in noticed)}에게 들킴", slot=slot)
    from .actions import record
    record(world, actor, step, slot, succeeded and moved > 0, f"{outcome} ({what} {moved:g})")
    _record(world, step.op, {
        "slot": slot, "place": actor.location, "actor": actor.name, "owner": owner, "where": where, "what": what,
        "moved": moved, "detection": checks, "stopped_by": [p.name for p in stopped_by], "fight": fight_result, "outcome": outcome,
    })


def resolve_violent(world: World, actor: Person, step: Step, slot: str, reactor: Reactor, cursors: dict[str, Cursor]) -> None:
    """attack / rob: a body against a body. The target, if awake, decides what to do; others join only if called."""
    from .actions import record

    target = _target_person(world, actor, step.target)
    if target is None or not target.alive:
        record(world, actor, step, slot, False, f"{step.target}이(가) 이곳에 없음")
        return
    asleep = target.name in world.asleep
    attackers, defenders = [actor], [target]
    what = "주화" if step.amount is not None or (step.good or "") in ("주화", "돈") else (step.good or "")
    act = f"{actor.name}이(가) 당신에게 달려든다" + (f" ({what}을(를) 빼앗으려 함)" if step.op == "rob" else "")
    if not asleep:
        steps = reactor([(target, act)], slot).get(target.name, [])
        _carry_out_talk(world, target, steps, slot)
        if any(s.op == "flee" for s in steps):
            cursors.setdefault(target.name, Cursor()).replace_rest([s for s in steps if s.op == "flee"])
            defenders = []
        if any(s.op == "talk" and s.target in (None, "", "여기", "모두") for s in steps):
            bystanders = world.awake_at(actor.location, exclude={actor.name, target.name})
            if bystanders:
                called = reactor([(p, f"{target.name}이(가) {actor.name}에게 공격당하며 도움을 청한다") for p in bystanders], slot)
                for bystander in bystanders:
                    joined = called.get(bystander.name, [])
                    _carry_out_talk(world, bystander, joined, slot)
                    if any(s.op in FIGHT_OPS and s.target == actor.name for s in joined):
                        defenders.append(bystander)
                    elif any(s.op in FIGHT_OPS and s.target == target.name for s in joined):
                        attackers.append(bystander)
    else:
        world.asleep.discard(target.name)  # nobody sleeps through being jumped
    fled = not defenders
    result = fight(world, attackers, defenders, slot, reactor, cursors, surprise=asleep) if defenders else {
        "attackers": [actor.name], "defenders": [], "winner": None, "fled": [target.name], "injuries": {},
    }
    taken = 0.0
    if step.op == "rob" and result["winner"] == "attackers" and actor.name not in result.get("fled", []):
        if what == "주화":
            taken = _take_money(world, actor, target.name, step.amount)
        else:
            taken = _move(target.inventory, actor.inventory, step.good, step.qty, world.config.carry_limit)
    if result["winner"] == "defenders":
        actor.restrained_day = world.day
    summary = (
        f"{target.name}이(가) 달아남" if fled else
        f"{'이김' if result['winner'] == 'attackers' else ('짐' if result['winner'] == 'defenders' else '결판 없이 끝남')}"
        + (f", {what} {taken:g} 빼앗음" if taken else "")
    )
    injuries = ", ".join(f"{n} {k}" for n, k in result.get("injuries", {}).items())
    seen = f"{actor.name}이(가) {target.name}을(를) 공격함: {summary}" + (f" ({injuries})" if injuries else "")
    for name in {p.name for p in (*attackers, *defenders, target)}:
        world.tell(name, seen, slot=slot)
    _witnesses(world, actor.location, seen, slot, exclude={p.name for p in (*attackers, *defenders, target)})
    record(world, actor, step, slot, result["winner"] == "attackers", summary)
    _record(world, step.op, {"slot": slot, "place": actor.location, "actor": actor.name, "target": target.name,
                             "asleep": asleep, "fight": result, "taken": taken, "what": what})


def _carry_out_talk(world: World, person: Person, steps: list[Step], slot: str) -> None:
    from .actions import execute_instant

    for step in steps:
        if step.op in ("talk", "give"):
            execute_instant(world, person, step, slot)
