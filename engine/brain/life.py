"""A day lived by brains instead of language models: the same slots, bodies and laws as the primal world.

A brain is asked only when its person has nothing left in hand to do. A walk of two slots or a hunt keeps them busy, and
nobody is asked mid-way. There is no morning plan and no clerk: what the brain picked is the step. Reactions to being
attacked are not asked yet, so an attacked person neither flees nor fights back by choice.

When the person is next asked, how much their body's distress eased since the last choice is handed back to the brain
as the only thing learned from (stage 3). The dead do not learn; what they would have learned dies with them, and
evolution is left to answer for it.

Stage 4: every person is born with a temper, and nerves that carry fear from slot to slot (temperament.py). Touch, smell
and taste reach the brain; fear now, the pain of those nearby, what was just tasted and how new the last moment was come
in as feelings. Fear and others' pain (as far as the person's empathy goes) count as distress. On top of the body's ease,
a taste pleases or repels as a newborn's does (sweet liked, bitter and foul refused), food that sickened lands once and
hard (taste aversion, Garcia), and something new pleases as much as the person is pulled by novelty.

Generations: given a population (lifecycle.py), tempers come from each person's genes and development instead of a draw,
infants are not asked, a crying infant's hunger and thirst reach those nearby, and matings and nursing are settled after
each slot with their innate pleasures. These are feelings; what to do about them is still the brain's.
"""
from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import replace

from ..agentworld.actions import Cursor
from ..primal import body as physiology
from ..primal import mind as minds
from ..primal import sky
from ..primal.config import SLOTS
from ..primal.day import end_day, run_slot
from ..primal.matter import Thing
from ..primal.world import Person, World
from . import choices, lifecycle, senses, temperament

APPROACH = frozenset({"hunt", "attack", "steal", "feed"})   # going at what can hurt: counted when afraid, never rewarded
SWEET_LIKED, BITTER_REFUSED, FOUL_REFUSED = 0.3, 0.5, 0.5
# Food itself pleases, not only the easing of hunger (2026-09-17). A starving body sits at hunger 1.0 for days, so one
# mushroom moves the felt level almost not at all and the choice that won it was barely rewarded. Animals do not learn
# food this way: the gut rewards calories as they arrive, quite apart from how hungry one still is (post-ingestive
# nutrient reward, Sclafani; de Araujo), which is why an animal learns to prefer what feeds it even without a taste.
FOOD_PLEASURE = 2.0
PAIN_SEEN, FEAR_SEEN = 0.5, 0.3   # how much another's pain or fright on their face weighs against their pleasure
# Watching the animals (2026-09-17). People learn what is worth eating by watching what eats it, and where the danger
# is by watching the hunt; a parrot copies a voice across the species line, and so does a forager watching a deer browse.
ANIMAL_EATING, ANIMAL_HUNTING = 0.3, -0.5
SEEN_KEEP = 8
# A bad meal is remembered for a day, the limit of one-trial taste aversion in animals; the fluke illness that follows
# raw fish by two weeks is beyond any animal's reach and stays unlearnable here too.
MEAL_MEMORY_DAYS = 1
MEALS_KEPT = 12
# The other half of learning what to eat: food that fed one is looked for again, and the kind itself is what is
# remembered (a search image, Tinbergen). The act of picking and biting is innate; which kind is worth it is learned.
RELISH = 0.4
INEDIBLE_REFUSED = 0.3   # biting on what cannot be chewed (a stone, a flake) is spat out, as a gag reflex does
SEE_LIGHT = 0.15         # below this much light nobody makes out what another does
# Trying things and learning them (2026-09-17). A policy that never varies cannot be corrected by any amount of
# learning: what is never done is never learned from. Two things widen the choice in animals - being young (juvenile
# play and neophilia, and a brain whose critical period is still open) and being in real want, which pushes an animal
# to try what it would not touch when fed. Both fade: an adult in good condition keeps to what it knows.
YOUTH_EXPLORING, YOUTH_LEARNING = 1.0, 2.0
WANT_EXPLORING = 1.0


def no_reaction(asks, slot):
    return {}


def _light(world: World, place: str, slot_index: int) -> float:
    c = world.config
    if not c.sky:
        return 1.0
    return sky.light(SLOTS[slot_index], world.day, c, fire=world.lands[place].fire is not None, raining=world.weather.raining)


def _circadian(world: World, person: Person, slot_index: int, temper: temperament.Temper) -> float:
    if not world.config.sky:
        return 0.0
    return sky.circadian_pressure(SLOTS[slot_index], temper.chronotype, _light(world, person.location, slot_index))


def _levels(world: World, person: Person, circadian: float = 0.0) -> dict[str, float]:
    c = world.config
    return physiology.felt_levels(person.body, c, circadian) if c.graded_feelings else physiology.distress(person.body, c)


def _extra(world: World, person: Person, stats: dict, slot_index: int, near: float) -> tuple[float, ...]:
    felt = stats["felt"].get(person.name, {})
    values = dict(felt)
    values.update(fear=stats["nerves"][person.name].fear, others_pain=near, light=_light(world, person.location, slot_index),
                  moon=sky.moon_fullness(world.day) if world.config.sky else 0.0, arousal=person.body.adrenaline)
    return tuple(values.get(k, 0.0) for k in senses.EXTRA_KINDS)


def idle(cursor: Cursor | None) -> bool:
    return cursor is None or (cursor.index >= len(cursor.steps) and cursor.remaining is None and cursor.path is None)


def others_pain(world: World, person: Person, population: lifecycle.Population | None = None) -> float:
    """How much those standing with a person hurt or are near death, and how hard its infants cry. Seen and heard."""
    others = [o for o in world.at(person.location) if o.name != person.name]
    if not others:
        return 0.0
    total = 0.0
    for other in others:
        pressing = _levels(world, other)
        total += pressing.get("pain", 0.0) + pressing.get("danger", 0.0)
        if population is not None and lifecycle.stage(population, world, other.name) == "infant":
            total += max(pressing.get("hunger", 0.0), pressing.get("thirst", 0.0))
    return total / len(others)


def drive(world: World, person: Person, fear: float = 0.0, pain_near: float = 0.0, empathy: float = 0.0,
          circadian: float = 0.0) -> float:
    """How far the body is from ease: every distress it feels, lost health, fear, and the pain of those nearby as far as
    empathy carries it. Lower is better."""
    pressing = _levels(world, person, circadian)
    return sum(pressing.values()) + 2.0 * (1.0 - max(0.0, person.body.health) / 100) + fear + empathy * pain_near


def new_stats(spread: float = temperament.SPREAD) -> dict:
    return {"decisions": 0, "think_steps": 0, "sense_s": 0.0, "brain_s": 0.0, "engine_s": 0.0, "ops_tried": Counter(),
            "ops_ok": Counter(), "thirsty_at_water": 0, "drank_when_thirsty_at_water": 0, "person_days": 0,
            "reward_sum": 0.0, "rewards": 0, "pending": {}, "by_day": {},
            "spread": spread, "tempers": {}, "nerves": {}, "felt": {}, "bonus": {}, "acts": {}, "days": Counter(),
            "afraid": Counter(), "afraid_approach": Counter(), "afraid_flee": Counter(), "tasted": 0, "aversions": 0,
            "seen": {}, "meals": {}}


def brain_neural(brain) -> dict:
    return getattr(brain, "neural", {})


def _born(world: World, brain, stats: dict, population: lifecycle.Population | None) -> None:
    """Each day: who they were born as, how widely they are trying things today, and how fast they still learn."""
    genes = brain.genes_values()
    for person in world.people.values():
        name = person.name
        if population is not None:
            stats["tempers"][name] = lifecycle.temper(population, name)   # the early window may have closed since
            if name not in brain_neural(brain):
                brain.set_neural(name, *lifecycle.neural(population, name))
        elif name not in stats["tempers"]:
            stats["tempers"][name] = temperament.draw(genes, world.seed, name, stats["spread"])
        stats["nerves"].setdefault(name, temperament.Nerves())
        youth = 0.0
        if population is not None:
            youth = max(0.0, 1.0 - lifecycle.age(population, world, name) / lifecycle.ADULT_DAYS)
        want = max(_levels(world, person).get("hunger", 0.0), _levels(world, person).get("thirst", 0.0))
        temper = stats["tempers"][name]
        stats["tempers"][name] = replace(temper, action_noise=temper.action_noise
                                         * (1.0 + YOUTH_EXPLORING * youth + WANT_EXPLORING * want))
        brain.set_plasticity(name, 1.0 + YOUTH_LEARNING * youth)
        brain.set_temper(name, stats["tempers"][name])
        person.body.chronotype = stats["tempers"][name].chronotype   # the body clock gene sets the body's own clock


def _taste(thing: Thing, gain: float) -> dict[str, float]:
    return {"sweet": gain * float(thing.p("sweetness") >= 0.4), "bitter": gain * float(thing.p("toxicity") >= 0.3),
            "sour": gain * float(thing.p("ferment") >= 0.3), "foul": gain * float(thing.p("spoil") >= 0.5)}


def _kind_token(kind: str) -> senses.Token:
    """A thing of this kind as the senses would give it, without any of this one's own marks."""
    return senses.Token(senses.CATEGORIES["carried"], senses.kind_id(kind), (0.0,) * senses.PROPS)


def _after_slot(world: World, brain, stats: dict, chosen: dict, before: dict, corpses: dict) -> None:
    onset = world.config.illness_onset
    for person in world.living():
        name = person.name
        if name not in before:
            continue
        temper, nerves = stats["tempers"][name], stats["nerves"][name]
        health, injuries, illness = before[name]
        harmed = person.body.health < health - 3.0 or len(person.body.injuries) > injuries
        temperament.feel_threat(nerves, temper, temperament.threat_at(world, person, corpses.get(person.location, 0)), harmed)
        if world.config.graded_feelings:
            levels = physiology.felt_levels(person.body, world.config)
            physiology.hormones_slot(person.body, nerves.fear, harmed, sum(levels.values()))
            if name in world.asleep:
                # the body's spoilers multiply the mind's (day.run_slot has already taken off 1 - the mind's quality).
                # Until 2026-09-16 both losses were subtracted whole: a hungry, stressed sleeper (mind 0.5, cortisol
                # 0.7) banked 1.2 slots in a day of collapse against a need of 2, never woke, and died of thirst beside
                # water. The replay of world 5001 showed it; it was most of the thirst deaths since graded feelings.
                quality = minds.sleep_quality(person.mind)
                person.body.slept_today -= quality * (1.0 - physiology.sleep_quality(person.body, world.config, levels))
        felt = {"novelty": world.slot_features.get(name, {}).get("새로움", 0.0)}
        bonus = temper.novelty_pull * felt["novelty"]
        if name in chosen:
            op, things, _ = chosen[name]
            engine_op = "test" if op == "taste" else op
            done = any(r["op"] == engine_op and r["ok"] for r in world.slot_done.get(name, []))
            if op == "eat" and not done and things and not things[0].is_food:
                bonus -= INEDIBLE_REFUSED
                brain.dislike(name, _kind_token(things[0].kind), INEDIBLE_REFUSED)   # spat out, and not tried so readily again
            if done and op in ("eat", "taste") and things:
                felt.update(_taste(things[0], temper.sensory_gain))
                bonus += SWEET_LIKED * felt["sweet"] - BITTER_REFUSED * felt["bitter"] - FOUL_REFUSED * felt["foul"]
                if op == "eat":
                    bonus += FOOD_PLEASURE * things[0].p("nutrition")
                stats["tasted"] += op == "taste"
                if op == "eat" and things[0].is_food:
                    brain.dislike(name, _kind_token(things[0].kind), -RELISH * (1.0 + felt["sweet"]))
                meals = stats["meals"].setdefault(name, [])
                meals.append((world.day, things[0].kind))
                del meals[:-MEALS_KEPT]
        if illness < onset <= person.body.illness:
            # whatever was eaten within the day before the sickness, not only what was eaten this very moment
            recent = [k for day, k in stats["meals"].get(name, []) if world.day - day <= MEAL_MEMORY_DAYS]
            for kind in dict.fromkeys(recent):
                brain.dislike(name, _kind_token(kind), temper.one_shot)
            if recent:
                bonus -= temper.one_shot
                stats["aversions"] += 1
        if name in chosen:
            op, things, _ = chosen[name]
            key = op + ":" + ",".join(sorted(t.kind for t in things))
            acts = stats["acts"].setdefault(name, Counter())
            fresh = 1.0 / (1.0 + temper.boredom * acts[key])
            acts[key] += 1
            bonus += temper.novelty_pull * max(0.0, fresh - felt["novelty"]) + 0.1 * temper.repetition * (1.0 - fresh)
            felt["novelty"] = max(felt["novelty"], fresh)
        stats["felt"][name] = felt
        stats["bonus"][name] = stats["bonus"].get(name, 0.0) + bonus


def _kin(population: lifecycle.Population | None, a: str, b: str) -> bool:
    if population is None or a not in population.lives or b not in population.lives:
        return False
    return population.lives[a].mother == b or population.lives[b].mother == a


def _watch_animals(world: World, stats: dict, slot_index: int) -> None:
    """What the beasts did where people could see it. Nothing is copied by the engine: the act and what it was done to
    reach the onlooker as a seen token, and their own brain makes of it what it will."""
    for place, species, op, kind in world.animal_acts:
        if _light(world, place, slot_index) < SEE_LIGHT:
            continue
        for onlooker in world.at(place):
            if onlooker.name in world.asleep or onlooker.name not in stats["tempers"]:
                continue
            fear = 1.0 if op == "hunt" else 0.0
            signal = ANIMAL_HUNTING if op == "hunt" else ANIMAL_EATING * (0.5 + stats["tempers"][onlooker.name].novelty_pull)
            token = senses.seen_token(op, kind, True, 0.0, 0.0, 0.0, fear, False, 0.0)
            memory = stats["seen"].setdefault(onlooker.name, [])
            memory.append((op, token, signal))
            del memory[:-SEEN_KEEP]


def _observe(world: World, stats: dict, chosen: dict, before: dict, population: lifecycle.Population | None,
             slot_index: int = 2, aimed: dict | None = None) -> None:
    """Who saw what this slot. Anyone awake where an act happened sees its sort, what it was done to, whether it worked,
    and the face that followed; a mother and her child watch each other twice as closely (stage 5). In the dark, with no
    moon or fire to see by, nothing is seen."""
    for actor_name, (op, things, target) in chosen.items():
        actor = world.people.get(actor_name)
        if actor is None or _light(world, actor.location, slot_index) < SEE_LIGHT:
            continue
        engine_op = "test" if op == "taste" else "wait" if op in ("mate", "nurse") else op
        done = any(r["op"] == engine_op and r["ok"] for r in world.slot_done.get(actor_name, []))
        felt = stats["felt"].get(actor_name, {})
        health, injuries, _ = before.get(actor_name, (actor.body.health, len(actor.body.injuries), 0.0))
        pain = 1.0 if (not actor.alive or actor.body.health < health - 3.0 or len(actor.body.injuries) > injuries) else 0.0
        fear = 1.0 if stats["nerves"].get(actor_name, temperament.Nerves()).fear >= 0.5 else 0.0
        pleasure = felt.get("sweet", 0.0)
        disgust = max(felt.get("bitter", 0.0), felt.get("foul", 0.0))
        kind = things[0].kind if things else target if op in ("hunt", "feed") else (aimed or {}).get(actor_name)
        for onlooker in world.at(actor.location):
            if onlooker.name == actor_name or onlooker.name in world.asleep or onlooker.name not in stats["tempers"]:
                continue
            kin = _kin(population, onlooker.name, actor_name)
            bond = onlooker.mind.bonds.get(actor_name, 0.0)
            weight = (0.5 + stats["tempers"][onlooker.name].empathy) * (2.0 if kin else 1.0)
            signal = weight * (SWEET_LIKED * pleasure - BITTER_REFUSED * disgust - PAIN_SEEN * pain - FEAR_SEEN * fear)
            token = senses.seen_token(op, kind, done, pleasure, disgust, pain, fear, kin, bond)
            memory = stats["seen"].setdefault(onlooker.name, [])
            memory.append((op, token, signal))
            del memory[:-SEEN_KEEP]


def live_day(world: World, brain, rng: random.Random, stats: dict, population: lifecycle.Population | None = None,
             observer=None) -> dict:
    """observer: called after every slot with (world, slot_index, chosen, decided, stats) to watch the day from
    outside (record.py); it must only read."""
    _born(world, brain, stats, population)
    cursors: dict[str, Cursor] = {}
    pending = stats["pending"]
    for slot_index in range(len(SLOTS)):
        thirsty_at_water = set()
        chosen: dict[str, tuple[str, list[Thing], str | None]] = {}
        decided: dict[str, tuple[list, choices.OpOption, dict]] = {}
        aimed: dict[str, str] = {}          # what a gatherer reached for, which is all an onlooker can see of it
        if population is not None:
            lifecycle.before_slot(population, world)
        for person in world.living():
            if not idle(cursors.get(person.name)):
                continue
            if population is not None and not lifecycle.asked(population, world, person):
                continue
            if person.body.asleep if world.config.sleep_switch else person.body.sleep_debt >= world.config.collapse_debt:
                continue   # the body is asleep (day.run_slot); a choice would never be lived
            name = person.name
            temper, nerves = stats["tempers"][name], stats["nerves"][name]
            near = others_pain(world, person, population)
            clock = _circadian(world, person, slot_index, temper)
            now = drive(world, person, nerves.fear, near, temper.empathy, clock)
            bonus = stats["bonus"].pop(name, 0.0)
            if name in pending:
                before, trace, felt_then = pending.pop(name)
                brain.learn(name, trace, before - now + bonus)
                brain.learn_body(name, trace, felt_then, senses.body_vector(world, person, clock))
                stats["reward_sum"] += before - now + bonus
                stats["rewards"] += 1
            person.plan_item_ids = [t.id for t in person.carried]
            extra = _extra(world, person, stats, slot_index, near)
            started = time.perf_counter()
            watched = stats["seen"].pop(name, [])
            perceived = senses.sense(world, person, slot_index, extra, temper.sensory_gain, [token for _, token, _ in watched],
                                     clock)
            brain.observe(name, watched)
            possible = choices.options(world, person, temper.sensory_gain)
            sensed = time.perf_counter()
            option, picks, info = brain.decide(name, perceived, possible, rng)
            decided[name] = (possible, option, info)
            stats["brain_s"] += time.perf_counter() - sensed
            stats["sense_s"] += sensed - started
            stats["decisions"] += 1
            stats["think_steps"] += info["think_steps"]
            if "trace" in info:
                pending[name] = (now, info["trace"], perceived.body)
            step = choices.to_step(option, picks)
            cursors[name] = Cursor([step])
            things = [person.carried[i - 1] for i in step.items if 0 < i <= len(person.carried)]
            if option.op == "eat" and not things:
                things = [t for t in reversed(person.carried) if t.is_food][:1]
            chosen[name] = (option.op, things, step.target)
            if step.what:
                aimed[name] = step.what
            if nerves.fear >= 0.5:
                stats["afraid"][name] += 1
                stats["afraid_approach"][name] += option.op in APPROACH
                stats["afraid_flee"][name] += option.op == "flee"
            if physiology.distress(person.body, world.config).get("thirst", 0.0) >= 0.5 and world.lands[person.location].water:
                thirsty_at_water.add(name)
        before = {p.name: (p.body.health, len(p.body.injuries), p.body.illness) for p in world.living()}
        corpses = {place: len(land.corpses) for place, land in world.lands.items()}
        started = time.perf_counter()
        run_slot(world, cursors, slot_index, no_reaction)
        stats["engine_s"] += time.perf_counter() - started
        drank = set()
        for name, done in world.slot_done.items():
            for record in done:
                stats["ops_tried"][record["op"]] += 1
                stats["ops_ok"][record["op"]] += record["ok"]
                if record["op"] == "drink" and record["ok"]:
                    drank.add(name)
        stats["thirsty_at_water"] += len(thirsty_at_water)
        stats["drank_when_thirsty_at_water"] += len(thirsty_at_water & drank)
        day = stats["by_day"].setdefault(world.day, [0, 0])
        day[0] += len(thirsty_at_water)
        day[1] += len(thirsty_at_water & drank)
        _after_slot(world, brain, stats, chosen, before, corpses)
        _observe(world, stats, chosen, before, population, slot_index, aimed)
        _watch_animals(world, stats, slot_index)
        if population is not None:
            def respond(target: str, proposer: str) -> bool:
                """The approached person's own brain answers, between going along with it and not."""
                person = world.people[target]
                temper = stats["tempers"][target]
                extra = _extra(world, person, stats, slot_index, others_pain(world, person, population))
                perceived = senses.sense(world, person, slot_index, extra, temper.sensory_gain,
                                         circadian=_circadian(world, person, slot_index, temper))
                possible = choices.options(world, person, temper.sensory_gain)
                mate = next((o for o in possible if o.op == "mate"), None)
                toward = [c for c in mate.args[0] if c.value == proposer] if mate else []
                if not toward:
                    return False
                answer = [choices.OpOption("mate", [toward]), next(o for o in possible if o.op == "wait")]
                option, _, _ = brain.decide(target, perceived, answer, rng)
                return option.op == "mate"

            pleasure = lifecycle.resolve(population, world, {n: (op, target) for n, (op, _, target) in chosen.items()}, respond)
            for name, value in pleasure.items():
                stats["bonus"][name] = stats["bonus"].get(name, 0.0) + value
        if observer is not None:
            observer(world, slot_index, chosen, decided, stats)
    stats["person_days"] += len(world.living())
    for person in world.living():
        stats["days"][person.name] += 1
    for name in [n for n in pending if not world.people[n].alive]:
        del pending[name]
    if population is not None:
        lifecycle.before_day_end(population, world, {n: nv.fear for n, nv in stats["nerves"].items()})
    started = time.perf_counter()
    summary = end_day(world, None)
    stats["engine_s"] += time.perf_counter() - started
    return summary
