"""Validate the Olduvai world before any new lineage is allowed to evolve in it.

This is an observer, not a selection function.  Nothing reported here is fed to a
brain, a birth, a mutation, or a later world.  Hard failures are broken physical
invariants (disconnected ground, impossible stocks, NaN state).  Ecological
blockers are reported separately: extinction is still a real result, but a land
intended to represent a living food web is not frozen as an experimental
environment until an implausibly immediate trophic collapse has been understood.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

from engine.primal import animals, plants, terrain
from engine.brain import brains, choices, life, lifecycle
from engine.primal.config import SLOTS
from engine.primal.day import end_day
from engine.primal.matter import TEMPLATES
from engine.primal.scenario import TERRAIN_FILES, build_world


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "runs" / "olduvai_validation.json"
DEFAULT_MANIFEST = ROOT / "runs" / "olduvai_manifest.json"
LAND = "olduvai"
REFLEX_FOODS = frozenset({"덩이줄기", "들열매", "바오바브 열매", "들풀 씨앗", "벌꿀"})


def _world(seed: int, people_per_camp: int = 0):
    return build_world(
        seed=seed,
        band_size=people_per_camp,
        energy=True,
        wildlife=True,
        puddles=True,
        land=LAND,
        plants=True,
        sky=True,
        graded=True,
        animals=True,
        sleep_switch=True,
    )


def _terrain_data() -> dict:
    return terrain.load(terrain.ROOT / TERRAIN_FILES[LAND])


def _snapshot(world) -> dict:
    """Only initial physical state.  No memory addresses or recorder state."""
    return {
        "day": world.day,
        "weather": {
            "day": world.weather.day,
            "season": world.weather.season,
            "temp": world.weather.base_temp,
            "rain": world.weather.raining,
            "storm": world.weather.storm,
        },
        "config": {
            "days_per_season": world.config.days_per_season,
            "season_temp": world.config.season_temp,
            "rain_chance": world.config.rain_chance,
            "latitude": world.config.latitude,
        },
        "lands": {
            name: {
                "kind": land.kind,
                "water": land.water,
                "pasture": land.pasture,
                "pasture_cap": land.pasture_cap,
                "gather": {
                    kind: {
                        "stock": stand.stock,
                        "cap": stand.cap,
                        "regen": stand.regen,
                        "gdd": stand.gdd,
                    }
                    for kind, stand in sorted(land.gather.items())
                },
                "neighbors": sorted(world.map.neighbors(name)),
            }
            for name, land in sorted(world.lands.items())
        },
        "herds": [
            {
                "id": herd.id,
                "species": herd.species,
                "count": herd.count,
                "place": herd.place,
                "energy": herd.energy,
                "hydration": herd.hydration,
                "boldness": herd.boldness,
            }
            for herd in sorted(world.herds, key=lambda one: one.id)
        ],
    }


def state_hash(world) -> str:
    raw = json.dumps(_snapshot(world), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _physical_failures(world, day: int) -> list[str]:
    failures: list[str] = []
    for name, land in world.lands.items():
        for kind, stand in land.gather.items():
            if not math.isfinite(stand.stock) or not math.isfinite(stand.cap):
                failures.append(f"day {day}: non-finite stand {name}/{kind}")
            elif stand.stock < -1e-9 or stand.stock > stand.cap + 1e-9:
                failures.append(f"day {day}: stock outside 0..cap {name}/{kind}={stand.stock}/{stand.cap}")
        if not math.isfinite(land.pasture) or land.pasture < -1e-9 or land.pasture > land.pasture_cap + 1e-9:
            failures.append(f"day {day}: pasture outside 0..cap {name}={land.pasture}/{land.pasture_cap}")
        if not 0.0 <= land.soil_moisture <= 1.0:
            failures.append(f"day {day}: soil moisture outside 0..1 {name}={land.soil_moisture}")
    for herd in world.herds:
        values = (herd.energy, herd.hydration, herd.fear, herd.boldness)
        diet = animals.DIETS[herd.species]
        if herd.place not in world.lands:
            failures.append(f"day {day}: herd {herd.id} is outside the map at {herd.place}")
        if herd.count < 0 or not isinstance(herd.count, int):
            failures.append(f"day {day}: invalid herd count {herd.id}={herd.count}")
        if not all(math.isfinite(value) for value in values):
            failures.append(f"day {day}: non-finite herd state {herd.id}")
        if herd.energy < -1e-9 or herd.energy > diet.store + 1e-9:
            failures.append(f"day {day}: herd energy outside 0..store {herd.id}={herd.energy}/{diet.store}")
        if not 0.0 <= herd.hydration <= 1.0:
            failures.append(f"day {day}: herd hydration outside 0..1 {herd.id}={herd.hydration}")
        if not 0.0 <= herd.fear <= 1.0:
            failures.append(f"day {day}: herd fear outside 0..1 {herd.id}={herd.fear}")
        if not -1.0 <= herd.boldness <= 1.0:
            failures.append(f"day {day}: herd boldness outside -1..1 {herd.id}={herd.boldness}")
    return failures


def static_validation(seed: int = 1) -> dict:
    world = _world(seed)
    data = _terrain_data()
    camps = list(data["camps"])
    failures: list[str] = []

    for camp in camps:
        if camp not in world.lands:
            failures.append(f"missing camp: {camp}")
            continue
        unreachable = [name for name in world.lands if world.map.route(camp, name) is None]
        if unreachable:
            failures.append(f"{camp} cannot reach {len(unreachable)} places")

    water_routes: dict[str, float | None] = {}
    water_places = [name for name, land in world.lands.items() if land.water]
    for camp in camps:
        routes = [world.map.route(camp, name) for name in water_places]
        distances = [route[1] for route in routes if route is not None]
        water_routes[camp] = min(distances) if distances else None
        if not distances:
            failures.append(f"{camp} cannot reach water")

    for name, land in world.lands.items():
        if land.kind == "강" and not land.water:
            failures.append(f"river without water: {name}")
    failures.extend(_physical_failures(world, world.day))

    first_hash = state_hash(world)
    second_hash = state_hash(_world(seed))
    if first_hash != second_hash:
        failures.append("same seed produced different initial physical state")

    return {
        "seed": seed,
        "places": len(world.lands),
        "camps": camps,
        "water_places": len(water_places),
        "nearest_water_slots": water_routes,
        "state_hash": first_hash,
        "failures": failures,
    }


def plant_validation(seed: int = 1, years: int = 2) -> dict:
    world = _world(seed)
    world.herds.clear()  # isolate climate and plants from grazing; ecology is checked separately
    year_days = 4 * world.config.days_per_season
    days = years * year_days
    previous: dict[tuple[str, str], bool] = {}
    fruitings: Counter[str] = Counter()
    cycles: Counter[tuple[str, str]] = Counter()
    present = {
        kind
        for land in world.lands.values()
        for kind in land.gather
        if plants.bears_fruit(kind)
    }

    failures: list[str] = []
    for _ in range(days):
        end_day(world, None)
        for place, land in world.lands.items():
            for kind, stand in land.gather.items():
                key = (place, kind)
                if plants.bears_fruit(kind) and stand.bore and not previous.get(key, False):
                    fruitings[kind] += 1
                    cycles[key] += 1
                previous[key] = stand.bore
        failures.extend(_physical_failures(world, world.day - 1))
        if failures:
            break

    max_cycles = {
        kind: max((count for (place, seen_kind), count in cycles.items() if seen_kind == kind), default=0)
        for kind in present
    }
    missing = sorted(kind for kind in present if max_cycles[kind] < years)
    return {
        "seed": seed,
        "days": days,
        "fruiting_events": dict(sorted(fruitings.items())),
        "max_cycles_per_stand": dict(sorted(max_cycles.items())),
        "missing_repeated_fruiting": missing,
        "failures": failures,
    }


def _species_counts(world) -> Counter[str]:
    counts: Counter[str] = Counter()
    for herd in world.herds:
        if herd.count > 0:
            counts[herd.species] += herd.count
    return counts


class ReflexProbe(brains.RandomPolicy):
    """A diagnostic animal, not an ancestor: satisfy pressing body needs using only what is currently within reach."""

    def __init__(self, world, population):
        self.world = world
        self.population = population

    @staticmethod
    def _option(options, op: str):
        return next((option for option in options if option.op == op), None)

    @staticmethod
    def _pick(option, value):
        if option is None:
            return None
        picks = []
        for candidates in option.args:
            match = next((candidate for candidate in candidates if candidate.value == value), None)
            picks.append(match or candidates[0])
        return option, picks, {"think_steps": 0}

    def decide(self, person_name, sense, options, rng):
        person = self.world.people[person_name]
        land = self.world.lands[person.location]
        felt = life._levels(self.world, person)

        slot_index = max(range(len(SLOTS)), key=lambda index: sense.context[index])
        if SLOTS[slot_index] == "밤" and person.body.sleep_pressure >= 0.45:
            choice = self._pick(self._option(options, "sleep"), None)
            if choice:
                return choice

        if felt.get("thirst", 0.0) > 0.0:
            if land.water:
                return self._pick(self._option(options, "drink"), None)
            wet = [name for name in person.known_places if self.world.lands[name].water]
            if wet:
                goal = min(wet, key=lambda name: self.world.map.route(person.location, name)[1])
                return self._pick(self._option(options, "go"), goal)

        food_indices = [i + 1 for i, thing in enumerate(person.carried) if thing.is_food and thing.p("toxicity") < 0.3]
        local_food = [kind for kind, stand in land.gather.items()
                      if stand.stock >= 1 and kind in REFLEX_FOODS and kind in TEMPLATES and TEMPLATES[kind].props.get("nutrition", 0.0) > 0
                      and TEMPLATES[kind].props.get("hardness", 0.0) < 0.6
                      and TEMPLATES[kind].props.get("toxicity", 0.0) < 0.3]
        # A stomach does not stop taking a meal because the sharpest hunger signal dipped after its first mouthful.
        if food_indices and person.body.eaten_today < self.world.config.food_need_per_day:
            return self._pick(self._option(options, "eat"), food_indices[0])
        if felt.get("hunger", 0.0) > 0.0:
            if local_food:
                return self._pick(self._option(options, "gather"), max(
                    local_food, key=lambda kind: TEMPLATES[kind].props.get("nutrition", 0.0)))
            feeding = []
            for name in person.known_places:
                edible = any(stand.stock >= 1 and kind in REFLEX_FOODS and kind in TEMPLATES
                             and TEMPLATES[kind].props.get("nutrition", 0.0) > 0
                             and TEMPLATES[kind].props.get("hardness", 0.0) < 0.6
                             and TEMPLATES[kind].props.get("toxicity", 0.0) < 0.3
                             for kind, stand in self.world.lands[name].gather.items())
                route = self.world.map.route(person.location, name)
                if edible and route is not None:
                    feeding.append((route[1], name))
            if feeding:
                return self._pick(self._option(options, "go"), min(feeding)[1])

        if local_food and len(food_indices) < 2:
            return self._pick(self._option(options, "gather"), max(
                local_food, key=lambda kind: TEMPLATES[kind].props.get("nutrition", 0.0)))

        own = self.population.lives[person_name]
        if lifecycle.stage(self.population, self.world, person_name) == "adult":
            partners = [other for other in self.world.at(person.location) if other.name != person_name
                        and other.alive and self.population.lives[other.name].sex != own.sex
                        and lifecycle.stage(self.population, self.world, other.name) == "adult"]
            if partners:
                return self._pick(self._option(options, "mate"), sorted(partners, key=lambda one: one.name)[0].name)

        return self._pick(self._option(options, "rest"), None)


def reflex_validation(seed: int = 1, days: int = 140) -> dict:
    """Can a blind body-care oracle produce and raise a child to adulthood under the unchanged world laws?"""
    world = _world(seed, people_per_camp=2)
    population = lifecycle.found(world, None)
    # The probe controls starting conditions, not outcomes: one recently-adult female/male pair per camp avoids a
    # random all-same-sex camp or founder senescence answering an ecological viability question for us.
    young_name = None
    for camp_index, camp in enumerate(sorted({person.camp for person in world.people.values()})):
        pair = sorted((person for person in world.people.values() if person.camp == camp), key=lambda one: one.name)
        for person, sex in zip(pair, ("F", "M")):
            population.lives[person.name].sex = sex
            population.lives[person.name].born = world.day - lifecycle.ADULT_DAYS
        if camp_index == 0:
            young_name = pair[0].name
            population.lives[young_name].born = world.day - lifecycle.INFANT_DAYS
    policy = ReflexProbe(world, population)
    stats = life.new_stats()
    rng = random.Random(f"reflex:{seed}")
    failures: list[str] = []
    reached: list[str] = []
    for elapsed in range(1, days + 1):
        life.live_day(world, policy, rng, stats, population)
        failures.extend(_physical_failures(world, elapsed))
        reached = [name for name in [young_name] if name is not None and world.people[name].alive
                   and lifecycle.age(population, world, name) >= lifecycle.ADULT_DAYS]
        if failures or reached:
            break
    deaths = Counter(person.body.cause_of_death for person in world.people.values() if not person.alive)
    return {
        "seed": seed,
        "days_run": elapsed,
        "founders": 6,
        "births": population.born_count,
        "living": len(world.living()),
        "diagnostic_young": young_name,
        "young_reaching_adulthood": sorted(reached),
        "death_causes": dict(sorted(deaths.items())),
        "failures": failures,
    }


def ecology_validation(seed: int = 1, days: int = 728) -> dict:
    world = _world(seed)
    start = _species_counts(world)
    predator_species = sorted(species for species in start if animals.DIETS[species].prey)
    extinct_on: dict[str, int] = {}
    peaks = Counter(start)
    snapshots: dict[str, dict[str, int]] = {"0": dict(sorted(start.items()))}
    failures: list[str] = []
    predator_slots: Counter[str] = Counter()
    prey_colocated_slots: Counter[str] = Counter()
    hunt_attempts: Counter[str] = Counter()
    hunt_targets: Counter[tuple[str, str]] = Counter()
    losses: Counter[tuple[str, str]] = Counter()
    prey_killed: Counter[str] = Counter()
    predator_condition: dict[str, dict[str, dict[str, float | int]]] = {}

    def condition_snapshot() -> dict[str, dict[str, float | int]]:
        out: dict[str, dict[str, float | int]] = {}
        for species in predator_species:
            living = [herd for herd in world.herds if herd.species == species and herd.count > 0]
            bodies = sum(herd.count for herd in living)
            weighted_energy = sum(herd.energy * herd.count for herd in living)
            out[species] = {
                "groups": len(living),
                "population": bodies,
                "mean_energy_days": round(weighted_energy / bodies, 3) if bodies else 0.0,
            }
        return out

    predator_condition["0"] = condition_snapshot()

    checkpoints = {world.config.days_per_season, 2 * world.config.days_per_season,
                   4 * world.config.days_per_season, days}
    for elapsed in range(1, days + 1):
        for slot in SLOTS:
            for herd in world.herds:
                diet = animals.DIETS[herd.species]
                if herd.count <= 0 or not diet.prey:
                    continue
                predator_slots[herd.species] += 1
                if any(prey.count > 0 and prey.place == herd.place and prey.species in diet.prey
                       for prey in world.herds if prey is not herd):
                    prey_colocated_slots[herd.species] += 1
            before = _species_counts(world)
            animals.slot(world, slot)
            after = _species_counts(world)
            for species, count in before.items():
                if after[species] < count:
                    prey_killed[species] += count - after[species]
            for _, species, op, target in world.animal_acts:
                if op == "hunt":
                    hunt_attempts[species] += 1
                    hunt_targets[(species, target)] += 1
            world.animal_acts.clear()
        summary = end_day(world, None)
        for note in summary["herd_moves"]:
            match = re.match(r"^([^:]+):.* -(\d+) \((energy|hydration)\)$", note)
            if match:
                species, count, cause = match.groups()
                losses[(species, cause)] += int(count)
        counts = _species_counts(world)
        for species, value in counts.items():
            peaks[species] = max(peaks[species], value)
        for species in start:
            if counts[species] == 0 and species not in extinct_on:
                extinct_on[species] = elapsed
        failures.extend(_physical_failures(world, elapsed))
        if elapsed in checkpoints:
            snapshots[str(elapsed)] = dict(sorted(counts.items()))
            predator_condition[str(elapsed)] = condition_snapshot()
        if failures:
            break

    end = _species_counts(world)
    blockers: list[str] = []
    guild_extinction = max((extinct_on.get(species, days + 1) for species in predator_species), default=days + 1)
    if predator_species and guild_extinction <= 4 * world.config.days_per_season:
        blockers.append(f"all predator species were extinct by day {guild_extinction}")
    if not any(end[species] > 0 for species in start if not animals.DIETS[species].prey):
        blockers.append("all non-predator species were extinct")

    alerts = []
    for species, initial in start.items():
        if peaks[species] > 10 * max(1, initial):
            alerts.append(f"{species} exceeded 10x its initial population")

    return {
        "seed": seed,
        "days": days,
        "start": dict(sorted(start.items())),
        "end": dict(sorted(end.items())),
        "peak": dict(sorted(peaks.items())),
        "extinct_on": dict(sorted(extinct_on.items())),
        "snapshots": snapshots,
        "predator_diagnostics": {
            species: {
                "herd_slots": predator_slots[species],
                "prey_colocated_slots": prey_colocated_slots[species],
                "hunt_attempts": hunt_attempts[species],
                "hunt_targets": {
                    target: count for (hunter, target), count in sorted(hunt_targets.items()) if hunter == species
                },
                "starvation_losses": losses[(species, "energy")],
                "dehydration_losses": losses[(species, "hydration")],
            }
            for species in predator_species
        },
        "prey_killed_during_slots": dict(sorted(prey_killed.items())),
        "predator_condition": predator_condition,
        "blockers": blockers,
        "alerts": alerts,
        "failures": failures,
    }


def validate(seeds: list[int], days: int = 728, plant_years: int = 2) -> dict:
    static = static_validation(seeds[0])
    plant = plant_validation(seeds[0], plant_years)
    ecology = [ecology_validation(seed, days) for seed in seeds]
    reflex = [reflex_validation(seed) for seed in seeds]
    hard_failures = list(static["failures"]) + list(plant["failures"])
    hard_failures.extend(failure for result in ecology for failure in result["failures"])
    hard_failures.extend(failure for result in reflex for failure in result["failures"])
    blockers = [f"plants did not fruit repeatedly: {', '.join(plant['missing_repeated_fruiting'])}"] \
        if plant["missing_repeated_fruiting"] else []
    blockers.extend(f"seed {result['seed']}: {blocker}" for result in ecology for blocker in result["blockers"])
    if not any(result["young_reaching_adulthood"] for result in reflex):
        blockers.append("no reflex-probe child reached reproductive age")
    return {
        "land": LAND,
        "valid": not hard_failures and not blockers,
        "hard_failures": hard_failures,
        "blockers": blockers,
        "static": static,
        "plants": plant,
        "ecology": ecology,
        "reflex_probe": reflex,
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(report: dict, seeds: list[int], days: int, plant_years: int) -> dict:
    """Freeze the exact world laws validated by this report, without making the report part of those laws."""
    rule_paths = [
        ROOT / "engine/primal/scenario.py",
        ROOT / "engine/primal/nature.py",
        ROOT / "engine/primal/plants.py",
        ROOT / "engine/primal/animals.py",
        ROOT / "engine/primal/body.py",
        ROOT / "engine/primal/energy.py",
        ROOT / "engine/primal/actions.py",
        ROOT / "engine/brain/lifecycle.py",
        Path(terrain.ROOT) / TERRAIN_FILES[LAND],
    ]
    report_bytes = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    world = _world(seeds[0])
    return {
        "schema": 1,
        "lineage": "E",
        "land": LAND,
        "frozen_after_validation": True,
        "validation": {
            "seeds": seeds,
            "ecology_days": days,
            "plant_years": plant_years,
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "initial_state_sha256": report["static"]["state_hash"],
        },
        "climate": {
            "days_per_season": world.config.days_per_season,
            "latitude": world.config.latitude,
            "season_temp": world.config.season_temp,
            "rain_chance": world.config.rain_chance,
        },
        "files": {str(path.relative_to(ROOT)).replace("\\", "/"): _file_hash(path) for path in rule_paths},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--days", type=int, default=728)
    parser.add_argument("--plant-years", type=int, default=2)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    report = validate(args.seeds, args.days, args.plant_years)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = None
    if report["valid"]:
        manifest = build_manifest(report, args.seeds, args.days, args.plant_years)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "valid": report["valid"],
        "hard_failures": report["hard_failures"],
        "blockers": report["blockers"],
        "report": str(args.out),
        "manifest": str(args.manifest) if manifest else None,
    }, ensure_ascii=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
