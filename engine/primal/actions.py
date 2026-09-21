"""Carrying out steps on the land. Every physical result comes from laws.py or nature.py; this file only routes."""
from __future__ import annotations

from .. import recorder as recording
from ..agentworld.actions import Cursor, SlotIntent
from . import body as physiology
from . import laws, nature, talent
from . import mind as minds
from .clerk import Step
from .laws import Outcome
from .matter import Thing
from .nature import SPECIES, setting_at
from .senses import describe, polish
from .world import Person, World

DURATION_OPS = frozenset({
    "gather", "hunt", "fish", "strike", "grind", "heat", "soak", "dry", "scrape", "weave", "build", "plant",
    "sleep", "rest", "guard", "train",
})
PER_SLOT_OPS = frozenset({"gather", "fish", "build", "sleep", "rest", "guard", "train"})
CONTEST_OPS = frozenset({"attack", "steal"})
PROCESS_OPS = frozenset({"strike", "grind", "heat", "soak", "dry", "scrape", "weave", "mix", "shape", "bind", "cut"})


def strength(world: World, person: Person) -> float:
    return person.body.strength / 20 * physiology.capability(person.body, world.config) * minds.capability(person.mind)


# ---- which things a step means
def resolve_items(world: World, person: Person, step: Step) -> list[Thing]:
    found: list[Thing] = []
    by_id = {t.id: t for t in person.carried}
    for number in step.items:
        if 1 <= number <= len(person.plan_item_ids):
            thing = by_id.get(person.plan_item_ids[number - 1])
            if thing is not None and thing not in found:
                found.append(thing)
    if step.what:
        # "3번 강돌로 부싯돌을 친다": a numbered thing and a named one together. The named one is the most recently
        # gotten thing that matches, since what they just picked up is what they mean.
        words = [w for w in step.what.replace(",", " ").split() if w]
        for thing in reversed(person.carried):
            text = describe(thing, person.name)
            if any(w in text for w in words) and thing not in found:
                found.append(thing)
                break
    return found


def _record(world: World, person: Person, step: Step, slot: str, out: Outcome, inputs: list[Thing]) -> None:
    out.felt = [polish(line) for line in out.felt]
    world.__dict__.setdefault("slot_done", {}).setdefault(person.name, []).append(
        {"op": step.op, "target": step.target, "what": step.what, "ok": out.ok, "felt": list(out.felt)})
    recorder = recording.active()
    if recorder is not None:
        recorder.write("actions", {
            "day": world.day, "slot": slot, "person": person.name, "place": person.location, "step": step.model_dump(),
            "ok": out.ok, "felt": out.felt,
            "inputs": [{"id": t.id, "kind": t.kind, "props": {k: round(v, 3) for k, v in t.props.items()}, "shape": t.shape} for t in inputs],
            "made": [{"id": t.id, "kind": t.kind, "props": {k: round(v, 3) for k, v in t.props.items()}, "shape": t.shape} for t in out.made],
        })
        if step.op in PROCESS_OPS or step.op in ("test", "fire", "plant", "build"):
            recorder.write("experiments", {
                "day": world.day, "person": person.name, "op": step.op, "form": step.form, "how": step.content,
                "inputs": [t.kind for t in inputs], "made": [t.kind for t in out.made], "felt": out.felt,
            })
    if out.felt:
        world.log(person.name, f"{slot + ' ' if slot else ''}{person.location}: " + " / ".join(out.felt))


_MOVE_FAILURES = {
    "모르는 곳": "{place}(으)로 가려 했지만 그런 곳을 모른다",
    "가는 길을 모름": "{place}(으)로 가는 길을 모른다",
    "길이 없음": "{place}(으)로 가는 길이 없다",
}


def failed_move(world: World, person: Person, step: Step, reason: str, place: str | None) -> None:
    """A walk that could not start, told the way it is met — never in the engine's own words ("go → 실패")."""
    felt = _MOVE_FAILURES.get(reason, "{place}(으)로 갈 수 없었다").format(place=place or "어딘가")
    _record(world, person, step, "", Outcome(False, [felt]), [])


def arrived(world: World, person: Person, step: Step, slot: str) -> None:
    """A walk that reached a place, written to the record only: arriving is already met in what they see there. Until
    this existed only walks that failed left a trace, and the records read as if nobody ever got anywhere."""
    _record(world, person, step, slot, Outcome(True, []), [])


# what doing it was, for remembering a moment ("부싯돌 조각, 강돌을 내리치던 때")
_DOING = {
    "gather": "거두", "fish": "물고기를 잡", "strike": "내리치", "grind": "갈", "heat": "불에 굽", "soak": "물에 담그",
    "dry": "말리", "scrape": "긁", "weave": "엮", "build": "짓", "plant": "땅에 묻", "eat": "먹", "drink": "물을 마시",
    "give": "건네주", "drop": "내려놓", "pick": "집어 들", "fill": "담", "cover": "입구를 막", "name": "이름을 붙이",
    "talk": "말을 하", "show": "보여주", "follow": "따라다니", "feed": "짐승에게 먹이를 주", "test": "살펴보", "mix": "섞",
    "shape": "손으로 빚", "bind": "묶", "cut": "자르", "fire": "불을 피우", "wait": "기다리",
}
_NO_OBJECT = frozenset({"fish", "drink", "talk", "follow", "feed", "fire", "name", "wait", "cover"})


def doing(step: Step, inputs: list[Thing]) -> str:
    if step.op == "intent":
        return step.content[:40] or "무언가를 하던 때"
    verb = _DOING.get(step.op, "무언가를 하")
    kinds = ", ".join(dict.fromkeys(t.kind for t in inputs)) or (step.what or "")
    return f"{kinds}을(를) {verb}던 때" if kinds and step.op not in _NO_OBJECT else f"{verb}던 때"


def _apply(world: World, person: Person, out: Outcome, keep_made: bool = True) -> None:
    for used in out.used:
        if used in person.carried:
            person.carried.remove(used)
        land = world.lands[person.location]
        if used in land.lying:
            land.lying.remove(used)
    if keep_made:
        person.carried.extend(out.made)
    for thing in out.made:
        thing.handled_by.add(person.name)
        person.encountered.add(thing.kind)


def _experience(world: World, person: Person, step: Step, inputs: list[Thing], out: Outcome) -> None:
    kinds = ",".join(sorted({t.kind for t in inputs})) or (step.what or step.target or "")
    key = f"intent:{step.content[:12]}" if step.op == "intent" else f"{step.op}:{kinds}"
    # the moment is what they did and what they met doing it, not the result text alone ("불이 없다") or an op name
    felt = f" ({'/'.join(out.felt)[:60]})" if out.felt else ""
    world.slot_activity[person.name] = (key, f"{person.location}에서 {doing(step, inputs)}{felt}")
    world.feature(person.name, "새로움", minds.is_new(person.mind, key))
    for line in out.felt:
        world.feature(person.name, "새로움", 0.5 * minds.is_new(person.mind, "felt:" + line))
    world.feature(person.name, "몸씀", min(1.0, out.exertion))
    if out.made and step.op not in ("gather", "fish"):
        world.feature(person.name, "만듦", 1.0)
    gain = talent.practise(world, person, step.op)
    # the feel of getting better follows what really improved: strong at first, fading as they near their own ceiling
    world.feature(person.name, "실력", 0.3 * min(1.0, gain / talent.GAIN))


def _steady(world: World, person: Person, op: str) -> float:
    return laws.steadiness(person.skills.get(op, 0.0), world.rng)


# ---- time-taking work
def execute_main(world: World, person: Person, intent: SlotIntent, slot: str, finished: bool) -> None:
    step = intent.main_step
    if step is None or intent.main == "travel":
        return
    op = step.op
    if op in ("sleep", "guard"):
        return
    if op == "rest":
        land = world.lands[person.location]
        warm = land.fire is not None or nature.shelter_at(land, len(world.at(land.name)))[1] > 0.3
        world.feature(person.name, "평온", 1.0 if warm and person.body.reserve > 0 else 0.4)
        world.slot_activity[person.name] = ("rest", f"{person.location}에서 쉬던 때")
        return
    if op == "train":
        person.body.trained_today += 1
        world.feature(person.name, "몸씀", 1.0)
        world.slot_activity[person.name] = ("train", f"{person.location}에서 몸을 단련하던 때")
        return
    if op not in PER_SLOT_OPS and not finished:
        return
    slots = max(1, step.slots or 1)
    land = world.lands[person.location]
    setting = setting_at(land, world.weather, slot, world.config, len(world.at(land.name)))
    inputs = resolve_items(world, person, step)
    maker = world.maker
    s = strength(world, person)
    if op == "gather":
        out = nature.gather(land, step.what, 1, s, person.skills.get("gather", 0.0), maker, world.weather.season,
                            person.gather_progress)
    elif op == "fish":
        from .contest import fish
        out = fish(world, person, inputs)
    elif op == "hunt":
        from .contest import hunt
        hunt(world, person, step, slot, inputs)
        return
    elif op == "build":
        out = nature.build(land, person.name, inputs, step.form or step.what or "", 1, s, _steady(world, person, "build"))
    elif op == "plant":
        if not inputs:
            out = Outcome(False, ["묻을 것이 없다"])
        else:
            out = Outcome(True, [])
            for seed in inputs:
                result = nature.plant(land, seed, world.day)
                out.used.extend(result.used)
                out.felt = result.felt
    elif op == "strike":
        out = laws.strike(inputs[0], inputs[1], s, person.skills.get("strike", 0.0), maker, world.rng) if len(inputs) >= 2 else Outcome(False, ["무엇으로 무엇을 칠지 모자란다"])
    elif op == "grind":
        abrasive = inputs[1] if len(inputs) >= 2 else next((g for g in land.lying if g.p("roughness") >= 0.5), None)
        out = laws.grind(inputs[0], abrasive, slots, step.form or "", _steady(world, person, "grind")) if inputs and abrasive else Outcome(False, ["갈 것이나 문지를 돌이 없다"])
    elif op == "heat":
        out = Outcome(bool(inputs), [] if inputs else ["불에 넣을 것이 없다"])
        for thing in inputs:
            result = laws.heat(thing, slots, setting, maker)
            out.ok = out.ok and result.ok
            out.felt += result.felt
            out.used += result.used
            out.made += result.made
    elif op == "soak":
        has_water = land.water is not None or any(c.p("water") > 0 for t in person.carried for c in t.contents)
        out = Outcome(bool(inputs), [] if inputs else ["담글 것이 없다"])
        for thing in inputs:
            result = laws.soak(thing, slots, setting, has_water)
            out.ok, out.felt = out.ok and result.ok, out.felt + result.felt
    elif op == "dry":
        out = Outcome(bool(inputs), [] if inputs else ["말릴 것이 없다"])
        for thing in inputs:
            out.felt += laws.dry(thing, slots, setting).felt
    elif op == "scrape":
        out = laws.scrape(inputs[0], inputs[1], slots, _steady(world, person, "scrape")) if len(inputs) >= 2 else Outcome(False, ["긁을 것이나 긁을 물건이 모자란다"])
    elif op == "weave":
        out = laws.weave(inputs, step.form or "", maker, _steady(world, person, "weave"))
    else:
        out = Outcome(True, [])
    _apply(world, person, out)
    _record(world, person, step, slot, out, inputs)
    _experience(world, person, step, inputs, out)


# ---- instant acts
def execute_instant(world: World, person: Person, step: Step, slot: str) -> Outcome:
    inputs = resolve_items(world, person, step)
    handler = _HANDLERS.get(step.op, _noop)
    out = handler(world, person, step, slot, inputs)
    _apply(world, person, out, keep_made=step.op not in ("pick",))
    _record(world, person, step, slot, out, inputs)
    if step.op not in ("wait",):
        _experience(world, person, step, inputs, out)
    return out


def _noop(world, person, step, slot, inputs) -> Outcome:
    if step.op == "intent" and step.content:
        # something with no name here yet, like a game or a rite: still lived, with whoever is around
        world.slot_activity[person.name] = (f"intent:{step.content[:12]}", f"{person.location}에서 {step.content[:40]}")
    return Outcome(True, [])


def _eat(world, person, step, slot, inputs) -> Outcome:
    food = [t for t in inputs if t.is_food] or ([] if step.items else [t for t in reversed(person.carried) if t.is_food][:1] if not step.what else [])
    if not food:
        return Outcome(False, ["먹을 것이 없다"])
    out = Outcome(True, [])
    for thing in food:
        out.felt.append(f"{describe(thing, person.name)}을(를) 먹었다. {laws.taste_words(thing)}")
        out.felt += physiology.eat(person.body, thing, world.config)
        world.feature(person.name, "맛", min(1.0, thing.p("sweetness") + (0.5 if thing.p("cooked") >= 1.0 else 0.0)))
        if thing.p("ferment") >= 0.3:
            world.feature(person.name, "취함", min(1.0, thing.p("ferment")))
        out.used.append(thing)
    return out


def _drink(world, person, step, slot, inputs) -> Outcome:
    for vessel in inputs + [t for t in person.carried if t not in inputs]:
        water = [c for c in vessel.contents if c.p("water") > 0]
        if water and (inputs == [] or vessel in inputs):
            vessel.contents.remove(water[0])
            return Outcome(True, ["담아 온 물을 마셨다"] + physiology.drink(person.body, 1.0, False))
    land = world.lands[person.location]
    water = land.water or (nature.puddle_water(land, world.weather) if world.config.puddles else None)
    if water is None:
        return Outcome(False, ["마실 물이 없다"])
    if land.water is None:
        land.puddle = max(0.0, land.puddle - nature.PUDDLE_SIP)
        return Outcome(True, ["고인 빗물을 마셨다"] + physiology.drink(person.body, 1.0, True))
    return Outcome(True, ["물을 마셨다"] + physiology.drink(person.body, 1.0, water == "고인 물"))


def _give(world, person, step, slot, inputs) -> Outcome:
    receiver = next((p for p in world.awake_at(person.location, exclude={person.name}) if p.name == step.target), None)
    if receiver is None or not inputs:
        return Outcome(False, [f"{step.target}이(가) 곁에 없거나 줄 것이 없다"])
    for thing in inputs:
        person.carried.remove(thing)
        receiver.carried.append(thing)
        thing.handled_by.add(receiver.name)
        receiver.encountered.add(thing.kind)
    desc = ", ".join(describe(t, receiver.name) for t in inputs)
    world.tell(receiver.name, f"{person.name}이(가) 당신에게 {desc}을(를) 줌", source=person.name, slot=slot)
    minds.event(receiver.mind, "인정", -10)
    receiver.mind.bonds[person.name] = min(1.0, receiver.mind.bonds.get(person.name, 0.0) + 0.1)
    return Outcome(True, [f"{receiver.name}에게 {desc}을(를) 주었다"])


def _drop(world, person, step, slot, inputs) -> Outcome:
    if not inputs:
        return Outcome(False, ["내려놓을 것이 없다"])
    land = world.lands[person.location]
    for thing in inputs:
        person.carried.remove(thing)
        land.lying.append(thing)
    return Outcome(True, [f"{', '.join(t.kind for t in inputs)}을(를) 내려놓았다"])


def _pick(world, person, step, slot, inputs) -> Outcome:
    land = world.lands[person.location]
    words = (step.what or "").split()
    matches = [t for t in land.lying if not words or any(w in describe(t, person.name) for w in words)]
    matches = matches[: step.qty] if step.qty else matches[:1]
    if not matches:
        return Outcome(False, ["집을 것이 보이지 않는다"])
    for thing in matches:
        land.lying.remove(thing)
        person.carried.append(thing)
        thing.handled_by.add(person.name)
        person.encountered.add(thing.kind)
        if thing.kind.endswith("사체"):
            person.encountered.add(thing.kind[:-2].strip())
    return Outcome(True, [f"{', '.join(describe(t, person.name) for t in matches)}을(를) 집었다"])


def _fill(world, person, step, slot, inputs) -> Outcome:
    if not inputs:
        return Outcome(False, ["담을 곳이 없다"])
    vessel = inputs[0]
    if vessel.p("concavity") < 0.5:
        return Outcome(False, ["오목하지 않아 담기지 않는다"])
    if len(inputs) >= 2:
        for thing in inputs[1:]:
            person.carried.remove(thing)
            vessel.contents.append(thing)
        return Outcome(True, ["안에 담았다"])
    land = world.lands[person.location]
    if land.water is None and not (world.config.puddles and nature.puddle_water(land, world.weather)):
        return Outcome(False, ["담을 물이 없다"])
    if land.water is None:
        land.puddle = max(0.0, land.puddle - nature.PUDDLE_SIP)
    water = world.maker.make("물")
    vessel.contents.append(water)
    if vessel.p("porosity") >= 0.3:
        return Outcome(True, ["물을 담았는데 겉으로 물이 배어 나온다"])
    return Outcome(True, ["물을 담았다"])


def _cover(world, person, step, slot, inputs) -> Outcome:
    if len(inputs) < 2:
        return Outcome(False, ["덮을 것이 모자란다"])
    inputs[0].props["covered"] = 1.0
    person.carried.remove(inputs[1])
    return Outcome(True, [f"{inputs[1].kind}(으)로 입구를 막았다"])


def _name(world, person, step, slot, inputs) -> Outcome:
    if not step.label:
        return Outcome(False, ["부를 이름을 말하지 않았다"])
    for thing in inputs:
        thing.labels[person.name] = step.label
    if not inputs and step.target:
        world.tell(person.name, f"당신은 {step.target}을(를) '{step.label}'(이)라고 부르기로 했다", incoming=False, slot=slot)
    return Outcome(True, [f"'{step.label}'(이)라고 부르기로 했다"])


def _talk(world, person, step, slot, inputs) -> Outcome:
    content = step.content.strip()
    if not content:
        return Outcome(False, ["할 말이 없다"])
    listeners = world.awake_at(person.location, exclude={person.name})
    if step.target in (None, "", "여기", "모두", person.location) or (step.target and step.target not in world.people):
        for listener in listeners:
            world.tell(listener.name, f"{person.name}이(가) 모두에게 말함: {content}", source=person.name, slot=slot)
        heard = listeners
    else:
        heard = [p for p in listeners if p.name == step.target]
        for listener in heard:
            world.tell(listener.name, f"{person.name}이(가) 당신에게 말함: {content}", source=person.name, slot=slot)
            minds.event(listener.mind, "인정", -3)
    if not heard:
        return Outcome(False, ["들을 사람이 곁에 없다"])
    world.feature(person.name, "함께", 1.0)
    for listener in heard:
        world.feature(listener.name, "함께", 1.0)
    return Outcome(True, [f"{len(heard)}명에게 말했다"])


def _show(world, person, step, slot, inputs) -> Outcome:
    viewers = [p for p in world.awake_at(person.location, exclude={person.name}) if step.target in (None, "여기", p.name)]
    if not viewers or not inputs:
        return Outcome(False, ["보여줄 사람이나 물건이 없다"])
    for viewer in viewers:
        world.tell(viewer.name, f"{person.name}이(가) 보여줌: " + ", ".join(describe(t, viewer.name) for t in inputs), source=person.name, slot=slot)
        for thing in inputs:
            viewer.encountered.add(thing.kind)
    return Outcome(True, [f"{len(viewers)}명에게 보여주었다"])


def _follow(world, person, step, slot, inputs) -> Outcome:
    target = world.person(step.target)
    if target is None or not world.knows(person.name, target.name) and target.location != person.location:
        return Outcome(False, [f"따라갈 {step.target}이(가) 보이지 않는다"])
    world.following[person.name] = target.name
    minds.event(target.mind, "인정", -5)
    return Outcome(True, [f"{target.name}을(를) 따라다니기로 했다"])


def _feed(world, person, step, slot, inputs) -> Outcome:
    herd = next((h for h in world.herds if h.place == person.location and h.species == step.target and h.count > 0), None)
    food = [t for t in inputs if t.is_food]
    if herd is None or not food:
        return Outcome(False, ["먹이를 줄 짐승이나 먹이가 없다"])
    return nature.feed(herd, person.name, food[0], world.config)


def _test(world, person, step, slot, inputs) -> Outcome:
    if not inputs:
        return Outcome(False, ["시험해 볼 것이 없다"])
    land = world.lands[person.location]
    setting = setting_at(land, world.weather, slot, world.config)
    out = laws.test(inputs[0], step.content or step.form or "", person.name, setting, strength(world, person))
    if "taste" in inputs[0].tested.get(person.name, set()) and inputs[0].is_food:
        physiology.eat(person.body, _nibble(inputs[0]), world.config)
    return out


def _nibble(thing: Thing) -> Thing:
    bite = Thing(id=-1, kind=thing.kind, props={k: v * (0.1 if k in ("nutrition", "toxicity", "parasites") else 1.0) for k, v in thing.props.items()})
    return bite


def _process(world, person, step, slot, inputs) -> Outcome:
    land = world.lands[person.location]
    setting = setting_at(land, world.weather, slot, world.config)
    maker = world.maker
    if step.op == "mix":
        return laws.mix(inputs, maker, setting)
    if step.op == "shape":
        return laws.shape(inputs[0], step.form or "", _steady(world, person, "shape")) if inputs else Outcome(False, ["빚을 것이 없다"])
    if step.op == "bind":
        if len(inputs) < 3 and not any(t.p("fiber") >= 0.5 for t in inputs):
            return Outcome(False, ["묶을 끈이 없다"])
        binder = max(inputs, key=lambda t: t.p("fiber"))
        return laws.bind([t for t in inputs if t is not binder], binder, maker, _steady(world, person, "bind"))
    if step.op == "cut":
        if len(inputs) < 2:
            return Outcome(False, ["자를 것이나 자를 물건이 모자란다"])
        return laws.cut(inputs[0], inputs[1], strength(world, person), maker)
    return Outcome(False, [])


def _fire(world, person, step, slot, inputs) -> Outcome:
    land = world.lands[person.location]
    setting = setting_at(land, world.weather, slot, world.config, len(world.at(land.name)))
    fuel = inputs or [t for t in person.carried if t.p("flammability") >= 0.5 and t.p("moisture") < 0.3]
    fuel = fuel or [t for t in land.lying if t.p("flammability") >= 0.5 and t.p("moisture") < 0.3]
    out = nature.light_fire(land, fuel, setting, world.config)
    return out


_HANDLERS = {
    "eat": _eat, "drink": _drink, "give": _give, "drop": _drop, "pick": _pick, "fill": _fill, "cover": _cover,
    "name": _name, "talk": _talk, "show": _show, "follow": _follow, "feed": _feed, "test": _test,
    "mix": _process, "shape": _process, "bind": _process, "cut": _process, "fire": _fire,
    "wait": _noop, "intent": _noop,
}

__all__ = ["Cursor", "SlotIntent", "DURATION_OPS", "CONTEST_OPS", "execute_main", "execute_instant", "resolve_items", "strength"]
