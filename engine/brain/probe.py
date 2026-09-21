"""Does a brain know its world, or only what went with what? The verification pipeline (2026-09-16).

The same lives are asked Pearl's three kinds of question, and every answer is set beside a baseline that could not
know the world, so a score means something only where the brain beats it (the causal world-model advantage, CWMA,
Krasnovsky 2026: a model against an empirical baseline on observational, interventional and counterfactual queries).

  seeing     What the brain's inner state holds at a choice. A linear read-out is fitted on some worlds and scored on
             the others (R²) for the body's feelings and for facts the brain was never handed as numbers (water here,
             food in hand, a predator here). Baseline: the same read-out with the answers shuffled.
  doing      At a moment a person is asked, one thing is changed in a copy of the world (thirst, hunger, sleepiness,
             a hungry tiger beside them) and the same brain is asked again, with nothing learned or used up. The
             chance of the acts the change calls for should rise. Baseline: a uniform pick among the same acts.
  imagining  At a moment, the world is copied once per act the person could do; each copy lives that act alone
             until the person would be asked again, and what the body did there is the truth. A brain with a body
             forecast (brains.Foresight) is scored on how far its forecast of each act's worsening misses, against
             knowing only the average change each act brought in the logged lives (associational) and against
             forecasting no change. It is also scored on how often it orders two acts as the copies did.

Nothing here changes a life that is being lived: the copies are thrown away and the brain is only asked.
"""
from __future__ import annotations

import copy
import random
from collections import defaultdict

import torch

from ..agentworld.actions import Cursor
from ..primal.config import SLOTS
from ..primal.day import run_slot
from ..primal.nature import SPECIES, Herd
from ..primal.scenario import build_world
from . import choices, life, senses, temperament
from .brains import EASE, OPS

BODY_READS = ("thirst", "hunger", "sleepy", "pain", "danger")
WORLD_READS = ("water_here", "food_in_hand", "predator_here", "others_here")


def _slot_of(sense: senses.Sense) -> int:
    return max(range(len(SLOTS)), key=lambda i: sense.context[i])


def _facts(world, person) -> dict[str, float]:
    land = world.lands[person.location]
    return {
        "water_here": float(bool(senses.water_tokens(world, person))),
        "food_in_hand": float(any(t.is_food for t in person.carried)),
        "predator_here": float(any(h.place == land.name and h.count > 0 and SPECIES[h.species].eats_meat
                                   for h in world.herds)),
        "others_here": float(len(world.at(land.name)) - 1),
    }


def _thirsty(world, person):
    person.body.hydration, person.body.drank_today = 0.0, 0.0


def _hungry(world, person):
    person.body.reserve, person.body.eaten_today = 0.0, 0.0
    person.body.fat = min(person.body.fat, 0.5)


def _sleepy(world, person):
    person.body.sleep_debt = world.config.exhausted_debt


def _tiger(world, person):
    world.herds.append(Herd(10_000, "호랑이", 1, person.location, energy=0.0, home=person.location))


# change, the acts it calls for, and when the question can be asked at all
INTERVENTIONS = {   # drinking is offered everywhere and fails away from water, so thirst is asked only at water
    "thirsty": (_thirsty, {"drink"}, lambda world, person, options: bool(senses.water_tokens(world, person))
                and any(o.op == "drink" for o in options)),
    "hungry": (_hungry, {"eat"}, lambda world, person, options: any(t.is_food for t in person.carried)
               and any(o.op == "eat" for o in options)),
    "sleepy": (_sleepy, {"sleep", "rest"}, lambda world, person, options: any(o.op == "sleep" for o in options)),
    "tiger": (_tiger, {"flee", "go"}, lambda world, person, options: any(o.op in ("flee", "go") for o in options)),
}


def _temper(brain, person: str) -> temperament.Temper:
    return getattr(brain, "temper", {}).get(person, temperament.DEFAULT)


class Probe:
    """Stands in for a brain in life.live_day: passes every call on, and at some choices asks its questions first."""

    def __init__(self, brain, ask_every: int = 10, branch_every: int = 25, seed: int = 0) -> None:
        self.brain = brain
        self.world = None
        self.picker = random.Random(seed)
        self.ask_every, self.branch_every = ask_every, branch_every
        self.decisions = 0
        self.reads: list[tuple[torch.Tensor, dict[str, float], int]] = []   # (inner state, answers, world seed)
        self.doing: dict[str, list[tuple[float, float]]] = defaultdict(list)   # change -> (brain's shift, uniform's shift)
        self.logged: dict[int, list[torch.Tensor]] = defaultdict(list)      # op index -> body changes after it, as lived
        self.branches: list[list[tuple[int, torch.Tensor, torch.Tensor | None]]] = []   # per moment: (op, true change, forecast)

    def __getattr__(self, name):
        return getattr(self.brain, name)

    def learn_body(self, person, trace, then, now):
        h, index, _, k, _ = trace
        self.logged[int(index[k])].append(torch.tensor(now) - torch.tensor(then))
        self.brain.learn_body(person, trace, then, now)

    def decide(self, person, sense, options, rng):
        self.decisions += 1
        world = self.world
        if world is not None and world.people[person].alive:
            if self.decisions % self.ask_every == 0:
                self._do(person, sense, options)
            if self.decisions % self.branch_every == 0:
                self._branch(person, sense, options)
        option, picks, info = self.brain.decide(person, sense, options, rng)
        if world is not None and info.get("hidden") is not None:
            answers = dict(zip(BODY_READS, (sense.body[senses.BODY_KINDS.index(k)] for k in BODY_READS)))
            answers.update(_facts(world, world.people[person]))
            self.reads.append((info["hidden"].detach().clone(), answers, world.seed))
        return option, picks, info

    def _asked_again(self, world, person_name, sense):
        person = world.people[person_name]
        slot = _slot_of(sense)
        temper = _temper(self.brain, person_name)
        clock = life._circadian(world, person, slot, temper)
        again = senses.sense(world, person, slot, sense.extra, temper.sensory_gain, circadian=clock)
        options = choices.options(world, person, temper.sensory_gain)
        return again, options

    def _do(self, person, sense, options):
        control_world = copy.deepcopy(self.world)
        again, control_options = self._asked_again(control_world, person, sense)
        control, _ = self.brain.op_probs(person, again, control_options)
        for name, (change, wanted, askable) in INTERVENTIONS.items():
            if not askable(control_world, control_world.people[person], control_options):
                continue
            changed = copy.deepcopy(self.world)
            change(changed, changed.people[person])
            again_do, do_options = self._asked_again(changed, person, sense)
            probs, _ = self.brain.op_probs(person, again_do, do_options)

            def share(p, opts):
                return float(sum(p[i] for i, o in enumerate(opts) if o.op in wanted))

            uniform = (sum(o.op in wanted for o in do_options) / len(do_options)
                       - sum(o.op in wanted for o in control_options) / len(control_options))
            self.doing[name].append((share(probs, do_options) - share(control, control_options), uniform))

    def _branch(self, person, sense, options):
        slot = _slot_of(sense)
        temper = _temper(self.brain, person)
        _, h = self.brain.op_probs(person, sense, options)
        moment = []
        seen_ops = set()
        for option in options:
            if option.op in seen_ops:
                continue
            seen_ops.add(option.op)
            picks = [candidates[0] for candidates in option.args]
            world = copy.deepcopy(self.world)
            body = world.people[person]
            then = senses.body_vector(world, body, life._circadian(world, body, slot, temper))
            cursor = Cursor([choices.to_step(option, picks)])
            s = slot
            while s < len(SLOTS):
                run_slot(world, {person: cursor}, s, life.no_reaction)
                s += 1
                if life.idle(cursor) or not body.alive:
                    break
            if s >= len(SLOTS) or not body.alive:
                continue   # the next choice would come after the night's reckoning or never: not what a forecast is of
            now = senses.body_vector(world, body, life._circadian(world, body, s, temper))
            truth = torch.tensor(now) - torch.tensor(then)
            forecast = None
            if h is not None and getattr(self.brain, "foresight", None) is not None:
                x = h + self.brain.op_embedding(torch.tensor(OPS.index(option.op)))
                if picks:
                    x = x + self.brain.encoder.tokens([picks[0].token])[0]
                forecast = self.brain.expect(person, x).detach()
            moment.append((OPS.index(option.op), truth, forecast))
        if len(moment) >= 2:
            self.branches.append(moment)

    # ---- scores
    def seeing(self, ridge: float = 1.0) -> dict:
        if len(self.reads) < 20:
            return {}
        worlds = sorted({w for _, _, w in self.reads})
        test_worlds = set(worlds[len(worlds) // 2:]) if len(worlds) > 1 else set()
        train = [r for r in self.reads if r[2] not in test_worlds] if test_worlds else self.reads[::2]
        test = [r for r in self.reads if r[2] in test_worlds] if test_worlds else self.reads[1::2]
        out = {}
        shuffler = random.Random(0)
        for key in BODY_READS + WORLD_READS:
            x_train = torch.stack([r[0] for r in train])
            y_train = torch.tensor([r[1][key] for r in train])
            x_test = torch.stack([r[0] for r in test])
            y_test = torch.tensor([r[1][key] for r in test])
            if float(y_test.var()) < 1e-9:
                continue

            def fit_score(y_fit):
                xm, ym = x_train.mean(0), y_fit.mean()
                xc = x_train - xm
                w = torch.linalg.solve(xc.T @ xc + ridge * torch.eye(xc.shape[1]), xc.T @ (y_fit - ym))
                pred = (x_test - xm) @ w + ym
                return 1.0 - float(((pred - y_test) ** 2).mean() / y_test.var(unbiased=False))

            shuffled = y_train[torch.tensor(shuffler.sample(range(len(y_train)), len(y_train)))]
            out[key] = {"r2": round(fit_score(y_train), 3), "shuffled_r2": round(fit_score(shuffled), 3)}
        return out

    def doing_scores(self) -> dict:
        out = {}
        for name, shifts in self.doing.items():
            if not shifts:
                continue
            brain = [s for s, _ in shifts]
            uniform = [u for _, u in shifts]
            out[name] = {"asked": len(shifts), "mean_shift": round(sum(brain) / len(brain), 4),
                         "rose_share": round(sum(s > 1e-6 for s in brain) / len(brain), 3),
                         "uniform_shift": round(sum(uniform) / len(uniform), 4)}
        return out

    def imagining(self) -> dict:
        if not self.branches:
            return {}
        mean = {op: torch.stack(v).mean(0) for op, v in self.logged.items() if v}
        errors = defaultdict(list)
        order = defaultdict(lambda: [0, 0])
        for moment in self.branches:
            worse = []
            for op, truth, forecast in moment:
                t = float(truth @ EASE)
                a = float(mean[op] @ EASE) if op in mean else 0.0
                errors["associational"].append((a - t) ** 2)
                errors["no_change"].append(t ** 2)
                f = float(forecast @ EASE) if forecast is not None else None
                if f is not None:
                    errors["forecast"].append((f - t) ** 2)
                worse.append((t, a, f))
            for i in range(len(worse)):
                for j in range(i + 1, len(worse)):
                    dt = worse[i][0] - worse[j][0]
                    if abs(dt) < 1e-6:
                        continue
                    for label, idx in (("associational", 1), ("forecast", 2)):
                        if worse[i][idx] is None:
                            continue
                        order[label][0] += (worse[i][idx] - worse[j][idx]) * dt > 0
                        order[label][1] += 1
        out = {"moments": len(self.branches), "acts_lived": sum(len(m) for m in self.branches)}
        for label, values in errors.items():
            out[f"mse_{label}"] = round(sum(values) / len(values), 5)
        for label, (right, total) in order.items():
            if total:
                out[f"order_right_{label}"] = round(right / total, 3)
        if "mse_forecast" in out:
            out["advantage_over_associational"] = round(out["mse_associational"] - out["mse_forecast"], 5)
        return out


def run(brain, seeds: list[int], per_camp: int = 5, days: int = 20, ask_every: int = 10, branch_every: int = 25,
        **world_flags) -> dict:
    """Lives the worlds with the probe standing in for the brain and returns the three kinds of score."""
    probe = Probe(brain, ask_every, branch_every)
    lifespan = 0.0
    for seed in seeds:
        brain.reset_people()
        world = build_world(seed=seed, band_size=per_camp, **world_flags)
        probe.world = world
        stats = life.new_stats()
        rng = random.Random(seed)
        for _ in range(days):
            if life.live_day(world, probe, rng, stats)["alive"] == 0:
                break
        lifespan += stats["person_days"] / len(world.people)
    return {"worlds": seeds, "days": days, "lifespan": round(lifespan / len(seeds), 2), "decisions": probe.decisions,
            "seeing": probe.seeing(), "doing": probe.doing_scores(), "imagining": probe.imagining()}
