"""A world's days written down for watching from outside (2026-09-16): where everyone was each slot, what they chose
among what, how their body felt, where the herds and fires were, and who died of what. Nothing here is seen by anyone
inside the world; the recorder only reads after each slot.

The record is plain JSON so a page can replay it: the land once (places with coordinates, roads), then one frame per
slot. People are rows of numbers to keep a sixty-day record small.
"""
from __future__ import annotations

import random

from ..primal import body as physiology
from ..primal import sky
from ..primal.config import SLOTS
from ..primal.scenario import TERRAIN_FILES, build_world
from . import choices, life

FELT = ("thirst", "hunger", "cold", "sleepy", "pain", "danger")
PERSON_FIELDS = ("place", "alive", "asleep", "op", "target", "ok", *FELT, "health", "fear", "adrenaline", "fat", "top",
                 "areas", "sleep_debt")
TOP = 5


def _r(value: float) -> float:
    return round(float(value), 2)


class Recorder:
    def __init__(self, world, land: str) -> None:
        self.world = world
        places = sorted(world.lands)
        self.place_index = {name: i for i, name in enumerate(places)}
        coords = {}
        if land in TERRAIN_FILES:
            from ..primal import terrain
            data = terrain.load(terrain.ROOT / TERRAIN_FILES[land])
            coords = {p["name"]: (p["lat"], p["lon"]) for p in data["places"]}
        self.people = sorted(world.people)
        self.species = sorted({h.species for h in world.herds})
        self.head = {
            "slots": list(SLOTS), "ops": list(choices.OPS), "felt": list(FELT), "person_fields": list(PERSON_FIELDS),
            "species": self.species,
            "places": [{"name": n, "kind": world.lands[n].kind, "water": world.lands[n].water is not None,
                        "lat": coords.get(n, (None, None))[0], "lon": coords.get(n, (None, None))[1]} for n in places],
            "roads": sorted({tuple(sorted((a, b))) for a in places for b in world.map.neighbors(a) if b in self.place_index}),
            "people": [{"name": n, "camp": world.people[n].camp, "sex": getattr(world.people[n], "sex", None)}
                       for n in self.people],
        }
        self.frames: list[dict] = []
        self.deaths: list[dict] = []
        self._alive = {n: world.people[n].alive for n in self.people}

    def __call__(self, world, slot_index, chosen, decided, stats) -> None:
        c = world.config
        rows = []
        for name in self.people:
            person = world.people[name]
            felt = physiology.felt_levels(person.body, c) if person.alive else {}
            op = target = areas = None
            ok = 0
            top = []
            if name in decided:
                possible, option, info = decided[name]
                op = choices.OPS.index(option.op)
                target = chosen[name][2]
                engine_op = "test" if option.op == "taste" else "wait" if option.op in ("mate", "nurse") else option.op
                ok = int(any(r["op"] == engine_op and r["ok"] for r in world.slot_done.get(name, [])))
                trace = info.get("trace")
                if trace is not None:
                    index, probs = trace[1], trace[2]
                    best = sorted(range(len(possible)), key=lambda i: -float(probs[i]))[:TOP]
                    top = [[int(index[i]), _r(probs[i])] for i in best]
                areas = info.get("areas")
            nerves = stats["nerves"].get(name)
            rows.append([self.place_index[person.location], int(person.alive), int(name in world.asleep), op, target, ok,
                         *[_r(felt.get(k, 0.0)) for k in FELT], _r(person.body.health),
                         _r(nerves.fear if nerves else 0.0), _r(person.body.adrenaline), _r(person.body.fat), top,
                         areas, _r(person.body.sleep_debt)])
            if self._alive[name] and not person.alive:
                self.deaths.append({"day": world.day, "slot": slot_index, "person": name,
                                    "cause": person.body.cause_of_death, "place": person.location})
            self._alive[name] = person.alive
        herds = [[self.species.index(h.species) if h.species in self.species else -1, h.count, self.place_index[h.place]]
                 for h in world.herds if h.count > 0 and h.place in self.place_index]
        self.frames.append({
            "day": world.day, "slot": slot_index, "season": world.weather.season, "temp": _r(world.weather.base_temp),
            "rain": int(world.weather.raining), "sun": _r(sky.daylight(SLOTS[slot_index], world.day, c)),
            "people": rows, "herds": herds,
            "fires": [self.place_index[n] for n, l in world.lands.items() if l.fire is not None],
        })

    def night(self) -> None:
        """Deaths reckoned at the end of the day (thirst, starvation) are written on the last frame's slot."""
        for name in self.people:
            person = self.world.people[name]
            if self._alive[name] and not person.alive:
                self.deaths.append({"day": self.world.day - 1, "slot": len(SLOTS) - 1, "person": name,
                                    "cause": person.body.cause_of_death, "place": person.location})
            self._alive[name] = person.alive

    def record(self, meta: dict) -> dict:
        return {"meta": meta, "head": self.head, "frames": self.frames, "deaths": self.deaths}


def run(brain, seed: int, days: int = 60, per_camp: int = 5, land: str = "danyang", **flags) -> dict:
    brain.reset_people()
    world = build_world(seed=seed, band_size=per_camp, land=land, **flags)
    recorder = Recorder(world, land)
    stats = life.new_stats()
    rng = random.Random(seed)
    lived = 0
    for _ in range(days):
        summary = life.live_day(world, brain, rng, stats, observer=recorder)
        recorder.night()
        lived += 1
        if summary["alive"] == 0:
            break
    meta = {"seed": seed, "days_lived": lived, "per_camp": per_camp, "land": land, "flags": flags,
            "lifespan": _r(stats["person_days"] / len(world.people))}
    return recorder.record(meta)
