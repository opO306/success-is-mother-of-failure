"""Bodies meeting bodies: people against beasts, people against people, wolves in the night."""
from __future__ import annotations

from collections.abc import Callable

from .. import recorder as recording
from ..agentworld import body as base_body
from ..agentworld.actions import Cursor
from . import laws, talent
from . import mind as minds
from .clerk import Step
from .config import NIGHT
from .laws import Outcome
from .matter import Thing
from .nature import SPECIES, Herd
from .senses import describe
from .world import Person, World

Reactor = Callable[[list[tuple[Person, str]], str], dict[str, list[Step]]]
FIGHT_OPS = frozenset({"attack"})


def _write(kind: str, world: World, payload: dict) -> None:
    world.events_today.append(f"{payload.get('slot')} {payload.get('place')}: {kind} {payload.get('summary', '')}")
    recorder = recording.active()
    if recorder is not None:
        recorder.write("contests", {"day": world.day, "kind": kind, **payload})


def best_weapon(person: Person) -> Thing | None:
    tools = [t for t in person.carried if t.p("sharpness") > 0 or t.parts]
    return max(tools, key=lambda t: laws.cutting_power(t, 1.0), default=None)


def power(world: World, person: Person, weapon: Thing | None = None) -> float:
    from .actions import strength
    weapon = weapon or best_weapon(person)
    edge = laws.cutting_power(weapon, 1.0) if weapon is not None else 0.0
    return 20 * strength(world, person) * (1 + 3 * edge)


def hunt(world: World, hunter: Person, step: Step, slot: str, inputs: list[Thing]) -> None:
    """A hunt at the end of the time they gave it. Everyone hunting the same beast here, finishing now, hunts together."""
    herd = next((h for h in world.herds if h.place == hunter.location and h.species == step.target and h.count > 0), None)
    if herd is None:
        _tell_self(world, hunter, slot, [f"{step.target or '짐승'}이(가) 보이지 않는다"])
        return
    key = (world.day, hunter.location, herd.id, slot)
    if key in world.hunts_done:
        return
    world.hunts_done.add(key)
    hunters = [hunter] + [
        p for p in world.awake_at(hunter.location, exclude={hunter.name})
        if p.name in world.slot_activity and world.slot_activity[p.name][0].startswith(f"hunt:{herd.species}")
    ]
    species = SPECIES[herd.species]
    # more hunters can drive and surround a herd; skill and darkness hide the approach
    stealth = 0.45 + 0.1 * (len(hunters) - 1) + sum(p.skills.get("hunt", 0.0) for p in hunters) * 0.05 + (0.2 if slot in NIGHT else 0.0)
    vigilance = species.evasion * (0.3 + herd.fear) * (0.8 if slot in NIGHT else 1.0)
    margin = stealth - vigilance
    chance_share = 0.0
    if margin < -0.15:
        spotted = True
    elif margin > 0.15:
        spotted = False
    else:
        chance_share = 1 - abs(margin) / 0.15
        spotted = world.rng.random() > 0.5 + margin / 0.3
    detail = {"hunters": [p.name for p in hunters], "species": herd.species, "stealth": round(stealth, 3), "vigilance": round(vigilance, 3)}
    for p in hunters:
        world.feature(p.name, "위험", species.aggression)
        world.feature(p.name, "몸씀", 1.0)
        world.slot_activity[p.name] = (f"hunt:{herd.species}", f"{p.location}에서 {herd.species}을(를) 쫓던 때")
        talent.practise(world, p, "hunt")
    if spotted:
        herd.fear = min(1.0, herd.fear + world.config.herd_fear_after_hunt)
        herd.hunted_days.append(world.day)
        felt = [f"{herd.species}이(가) 먼저 알아채고 달아났다"]
        for p in hunters:
            _tell_self(world, p, slot, felt)
        _write("hunt", world, {**detail, "slot": slot, "place": hunter.location, "result": "spotted", "chance_share": round(chance_share, 3), "summary": f"{herd.species} 사냥 실패(들킴)"})
        return
    damage = sum(power(world, p, inputs[0] if p is hunter and inputs else None) for p in hunters)
    ratio = damage / species.toughness
    if 0.9 <= ratio <= 1.1:
        chance_share = max(chance_share, 1 - abs(ratio - 1) / 0.1)
        killed = world.rng.random() < ratio - 0.5
    else:
        killed = ratio > 1.1
    herd.hunted_days.append(world.day)
    herd.fear = min(1.0, herd.fear + world.config.herd_fear_after_hunt)
    if killed:
        herd.count -= 1
        carcass = world.maker.derive(f"{herd.species} 사체", {"hardness": 0.3, "fiber": 0.5, "weight": species.toughness / 20})
        world.lands[hunter.location].lying.append(carcass)
        felt = [f"{herd.species} 한 마리를 쓰러뜨렸다. 사체가 그 자리에 있다"]
        for p in hunters:
            world.feature(p.name, "이김", 1.0)
            p.encountered.add(herd.species)
    else:
        felt = [f"{herd.species}에게 상처를 냈지만 놓쳤다"]
        if species.aggression > 0:
            victim = min(hunters, key=lambda p: p.body.strength)
            heavy = species.toughness > damage * 1.5
            base_body.wound(victim.body, heavy)
            felt.append(f"{herd.species}이(가) 들이받아 {victim.name}이(가) 다쳤다")
            minds.event(victim.mind, "안전", 25, f"{victim.location}에서 {herd.species}에게 다친 때")
    for p in hunters:
        _tell_self(world, p, slot, felt)
    _write("hunt", world, {**detail, "slot": slot, "place": hunter.location, "damage": round(damage, 2), "toughness": species.toughness,
                           "killed": killed, "chance_share": round(chance_share, 3), "summary": f"{herd.species} 사냥 {'성공' if killed else '실패'}"})


def _tell_self(world: World, person: Person, slot: str, felt: list[str]) -> None:
    world.log(person.name, f"{slot} {person.location}: " + " / ".join(felt))


def fish(world: World, person: Person, inputs: list[Thing]) -> Outcome:
    land = world.lands[person.location]
    stock = land.gather.get("물고기")
    if land.water is None or stock is None or stock.stock < 1:
        return Outcome(False, ["물고기가 보이지 않는다"])
    tool = inputs[0] if inputs else None
    if tool is not None and tool.props.get("mesh", 0) > 0:
        rate = 3.0 * tool.props["mesh"]
    elif tool is not None:
        rate = 0.5 + 2 * laws.cutting_power(tool, 1.0)
    else:
        rate = 0.3
    from .actions import strength
    # bare hands take about a third of a fish in a slot: whole fish, continuous work, so what is not yet a fish waits
    # for the next slot as gathering does (until 2026-09-17 it was thrown away and bare-handed fishing caught nothing)
    caught = min(stock.stock, rate * max(0.3, strength(world, person)) * (1 + 0.1 * person.skills.get("fish", 0.0)))
    carried = person.gather_progress.get("물고기", 0.0) + caught
    count = int(carried)
    person.gather_progress["물고기"] = carried - count
    if count <= 0:
        return Outcome(True, ["아직 한 마리도 손에 넣지 못했다"], exertion=0.4)
    stock.stock -= count
    return Outcome(True, [f"물고기 {count}마리를 잡았다"], made=[world.maker.make("물고기") for _ in range(count)], exertion=0.4)


def fight(world: World, attackers: list[Person], defenders: list[Person], slot: str, reactor: Reactor, cursors: dict[str, Cursor], surprise: bool) -> dict:
    fled: list[str] = []
    reasked = False
    chance_share = 0.0

    def totals() -> tuple[float, float]:
        a = sum(power(world, p) for p in attackers) * (1.5 if surprise else 1.0)
        return a, sum(power(world, p) for p in defenders)

    a, d = totals()
    ratio = abs(a - d) / (a + d) if a + d else 0.0
    if ratio < 0.1 and attackers and defenders:
        reasked = True
        answers = reactor([(p, "몸싸움이 벌어졌는데 힘이 비슷해 결판이 나지 않고 있다") for p in attackers + defenders], slot)
        for side in (attackers, defenders):
            for p in list(side):
                steps = answers.get(p.name, [])
                if any(s.op == "flee" for s in steps):
                    side.remove(p)
                    fled.append(p.name)
                    cursors.setdefault(p.name, Cursor()).replace_rest([s for s in steps if s.op == "flee"])
                elif not any(s.op in FIGHT_OPS for s in steps):
                    side.remove(p)
        a, d = totals()
        ratio = abs(a - d) / (a + d) if a + d else 0.0
    if not attackers and not defenders:
        winner = None
    elif not defenders:
        winner = "attackers"
    elif not attackers:
        winner = "defenders"
    elif ratio < 0.1:
        chance_share = 1 - ratio / 0.1
        winner = "attackers" if world.rng.random() < a / (a + d) else "defenders"
    else:
        winner = "attackers" if a > d else "defenders"
    injuries = {}
    if winner and attackers and defenders:
        winners, losers = (attackers, defenders) if winner == "attackers" else (defenders, attackers)
        for loser in losers:
            heavy = ratio >= 0.3 or any(best_weapon(w) is not None and laws.cutting_power(best_weapon(w), 1.0) > 0.5 for w in winners)
            base_body.wound(loser.body, heavy)
            injuries[loser.name] = "깊은 상처" if heavy else "가벼운 상처"
    for p in attackers + defenders:
        world.feature(p.name, "위험", 1.0)
        if winner and ((winner == "attackers" and p in attackers) or (winner == "defenders" and p in defenders)):
            world.feature(p.name, "이김", 1.0)
    return {"attackers": [p.name for p in attackers], "defenders": [p.name for p in defenders], "ratio": round(ratio, 3),
            "reasked": reasked, "chance_share": round(chance_share, 3), "winner": winner, "fled": fled, "injuries": injuries}


def attack(world: World, actor: Person, step: Step, slot: str, reactor: Reactor, cursors: dict[str, Cursor]) -> None:
    target = next((p for p in world.at(actor.location) if p.name == step.target and p.name not in world.busy), None)
    if target is None:
        _tell_self(world, actor, slot, [f"{step.target}이(가) 곁에 없다"])
        return
    asleep = target.name in world.asleep
    defenders = [target]
    if not asleep:
        steps = reactor([(target, f"{actor.name}이(가) 당신에게 달려든다")], slot).get(target.name, [])
        if any(s.op == "flee" for s in steps):
            cursors.setdefault(target.name, Cursor()).replace_rest([s for s in steps if s.op == "flee"])
            defenders = []
    else:
        world.asleep.discard(target.name)
    result = fight(world, [actor], defenders, slot, reactor, cursors, surprise=asleep) if defenders else {"winner": None, "fled": [target.name], "injuries": {}}
    if result["winner"] == "defenders":
        actor.restrained_day = world.day
        minds.event(actor.mind, "자율", 30, f"{actor.location}에서 붙잡힌 때")
    seen = f"{actor.name}이(가) {target.name}을(를) 덮침: " + ("달아남" if not defenders else {"attackers": "덮친 쪽이 이김", "defenders": "덮친 쪽이 제압됨", None: "흐지부지 끝남"}[result["winner"]])
    for witness in world.awake_at(actor.location):
        world.tell(witness.name, seen, slot=slot)
        minds.event(witness.mind, "안전", 15, f"{actor.location}에서 싸움을 본 때")
    minds.event(target.mind, "안전", 30, f"{actor.location}에서 {actor.name}에게 덮쳐진 때")
    _write("attack", world, {"slot": slot, "place": actor.location, "actor": actor.name, "target": target.name, "asleep": asleep, "fight": result, "summary": seen})


def steal(world: World, actor: Person, step: Step, slot: str, reactor: Reactor, cursors: dict[str, Cursor]) -> None:
    victim = next((p for p in world.at(actor.location) if p.name == step.target), None)
    if victim is None:
        _tell_self(world, actor, slot, [f"{step.target}이(가) 곁에 없다"])
        return
    words = (step.what or "").split()
    goods = [t for t in victim.carried if not words or any(w in describe(t, actor.name) for w in words)][: step.qty or 1]
    if not goods:
        _tell_self(world, actor, slot, ["가져갈 것이 보이지 않는다"])
        return
    stealth = actor.skills.get("steal", 0.0) * 0.3 + (3.0 if slot in NIGHT else 0.0)
    watchers = world.awake_at(actor.location, exclude={actor.name})
    noticed = [w for w in watchers if 3.0 + (2.0 if w is victim else 0.0) + (5.0 if world.guarding.get(w.name) in (victim.name, actor.location) else 0.0) > stealth + 1.0]
    talent.practise(world, actor, "steal")
    stopped = []
    if noticed:
        answers = reactor([(w, f"{actor.name}이(가) {victim.name}의 물건을 몰래 가져가려는 것을 봤다") for w in noticed], slot)
        stopped = [w for w in noticed if any(s.op == "attack" for s in answers.get(w.name, []))]
    result = fight(world, [actor], stopped, slot, reactor, cursors, surprise=False) if stopped else None
    succeeded = result is None or result["winner"] == "attackers"
    if succeeded:
        for thing in goods:
            victim.carried.remove(thing)
            actor.carried.append(thing)
        if victim not in noticed:
            world.tell(victim.name, "지니고 있던 것 일부가 없어졌다", slot=None)
            minds.event(victim.mind, "자율", 20, "가진 것을 잃은 것을 안 때")
    else:
        actor.restrained_day = world.day
    for w in noticed:
        world.tell(w.name, f"{actor.name}이(가) {victim.name}의 물건을 몰래 가져가려 함: {'가져감' if succeeded else '저지당함'}", slot=slot)
    _write("steal", world, {"slot": slot, "place": actor.location, "actor": actor.name, "victim": victim.name, "noticed": [w.name for w in noticed],
                            "fight": result, "succeeded": succeeded, "summary": f"{actor.name}→{victim.name} {'성공' if succeeded else '저지'}"})


def wolves_at_night(world: World, slot: str) -> None:
    """Hungry packs come for whoever sleeps in the open with no fire."""
    if slot not in NIGHT:
        return
    from .nature import shelter_at, wolf_attack_targets
    for herd in world.herds:
        if herd.species != "늑대" or herd.count <= 0:
            continue
        land = world.lands[herd.place]
        roof, _ = shelter_at(land, len(world.at(land.name)))
        sleepers = [p.name for p in world.at(land.name) if p.name in world.asleep and roof < 0.5]
        for name in wolf_attack_targets(herd, land, slot, sleepers, world.config):
            victim = world.people[name]
            base_body.wound(victim.body, heavy=herd.count >= 5)
            world.asleep.discard(name)
            text = "자다가 늑대 떼에게 물렸다"
            world.tell(name, text, slot=slot)
            minds.event(victim.mind, "안전", 40, f"{land.name}에서 늑대에게 물린 밤")
            for witness in world.awake_at(land.name, exclude={name}):
                world.tell(witness.name, f"늑대 떼가 {name}을(를) 물었다", slot=slot)
                minds.event(witness.mind, "안전", 20)
            _write("wolves", world, {"slot": slot, "place": land.name, "victim": name, "pack": herd.count, "summary": f"늑대가 {name}을(를) 물음"})
