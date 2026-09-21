"""Stages 2-4 and generations of design doc 4: an ancestor found by death alone, with or without learning within a life.

A genome is a brain's weights (and, when its people learn, how fast they learn). Every person of a small band lives by
the same genome, as one species with one set of instincts; bodies and talents still differ, and from stage 4 so do
tempers, scattered around the means the genome carries. A genome's fitness is how long its people lived, averaged over
the worlds that every genome of the generation lives in. With births on, people are born inside the world with genes of
their own (lifecycle.py), and fitness becomes the days lived by the founders and all their descendants per founder:
lifespan alone would count a pregnancy's cost and never its child. Nothing else is scored. The other numbers written per
generation (alive after day 6, drinking when thirsty at water, going at danger while afraid, places known, acts tried,
births) are watched, never selected on.

The first generation descends from one ancestor with small mutations, so every genome stays close enough to be mixed: a
child is a weighted average of two long-lived parents plus noise (networks that share an early ancestor stay linearly
connected, Frankle et al. 2020). The two longest-lived genomes pass on unchanged.
"""
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import torch
from torch.nn.utils import parameters_to_vector, vector_to_parameters

from ..primal.scenario import build_world
from . import brains, life, lifecycle, temperament


def _rate(counts: list[list[int]]) -> float | None:
    thirsty = sum(c[0] for c in counts)
    return sum(c[1] for c in counts) / thirsty if thirsty else None


def evaluate(brain, seeds: list[int], per_camp: int, max_days: int, spread: float = temperament.SPREAD,
             records: list | None = None, births: bool = False, energy: bool = True, wildlife: bool = True,
             puddles: bool = True, land: str = "danyang", plants: bool = True, sky: bool = True, graded: bool = True,
             animals: bool = True, sleep_switch: bool = True) -> dict:
    """records: when given, one row per person is appended (what they were born with and how they lived).
    energy: the energy balance law (engine/primal/energy.py), on for brain worlds since 2026-09-15."""
    persons = founders = person_days = alive_after_day6 = drank = thirsty = think = decisions = rewards = 0
    afraid = approach = tasted = aversions = tried = born = deepest = 0
    reward_sum = known = 0.0
    early: list[list[int]] = []
    late: list[list[int]] = []
    for seed in seeds:
        brain.reset_people()
        world = build_world(seed=seed, band_size=per_camp, energy=energy, wildlife=wildlife, puddles=puddles, land=land,
                            plants=plants, sky=sky, graded=graded, animals=animals, sleep_switch=sleep_switch)
        population = lifecycle.found(world, brain.genes_values()) if births else None
        stats = life.new_stats(spread)
        rng = random.Random(seed)
        founders += len(world.people)
        for day in range(1, max_days + 1):
            summary = life.live_day(world, brain, rng, stats, population)
            if day == 6:
                alive_after_day6 += summary["alive"]
            if summary["alive"] == 0:
                break
        persons += len(world.people)
        person_days += stats["person_days"]
        drank += stats["drank_when_thirsty_at_water"]
        thirsty += stats["thirsty_at_water"]
        think += stats["think_steps"]
        decisions += stats["decisions"]
        reward_sum += stats["reward_sum"]
        rewards += stats["rewards"]
        early += [c for d, c in stats["by_day"].items() if d <= 3]
        late += [c for d, c in stats["by_day"].items() if d >= 4]
        afraid += sum(stats["afraid"].values())
        approach += sum(stats["afraid_approach"].values())
        tasted += stats["tasted"]
        aversions += stats["aversions"]
        if population is not None:
            born += population.born_count
            deepest = max([deepest] + [l.generation for l in population.lives.values()])
        for person in world.people.values():
            share = len(person.known_places) / len(world.lands)
            acts = len(stats["acts"].get(person.name, {}))
            known += share
            tried += acts
            if records is not None:
                temper = stats["tempers"].get(person.name) or (
                    lifecycle.temper(population, person.name) if population is not None else temperament.DEFAULT)
                row = {
                    "world": seed, "person": person.name, "days": stats["days"][person.name], "alive": person.alive,
                    "cause": None if person.alive else person.body.cause_of_death, "places_known": round(share, 3),
                    "acts_tried": acts, "afraid": stats["afraid"][person.name],
                    "afraid_approach": stats["afraid_approach"][person.name], "afraid_flee": stats["afraid_flee"][person.name],
                    **{gene: round(getattr(temper, gene), 3) for gene in temperament.GENES},
                }
                if population is not None:
                    lived = population.lives[person.name]
                    row.update(sex=lived.sex, generation=lived.generation, mother=lived.mother, father=lived.father)
                records.append(row)
    return {
        "lifespan": person_days / persons,
        "lineage_days": person_days / founders,
        "alive_after_day6": alive_after_day6 / founders,
        "drank_when_thirsty_at_water": drank / thirsty if thirsty else None,
        "drank_early": _rate(early),
        "drank_late": _rate(late),
        "reward_per_choice": reward_sum / rewards if rewards else None,
        "think_steps": think / decisions if decisions else 0.0,
        "afraid_approach_rate": approach / afraid if afraid else None,
        "afraid_share": afraid / decisions if decisions else 0.0,
        "tasted_per_person": tasted / persons,
        "aversions_per_person": aversions / persons,
        "places_known": known / persons,
        "acts_tried": tried / persons,
        "births_per_founder": born / founders,
        "deepest_generation": deepest,
    }


# Weights held at zero in every genome: the inborn body forecast. While a lineage's trust in its forecast stayed near
# zero, mutations piled up in the forecast's weights with nothing to select them away, as in a gene no longer used (A
# gen210 and D gen39: weight norms 1.5-1.9, forecast errors 5.4-5.7 against 0.02 for forecasting no change). People
# still learn their own forecast while living; trust and the forecast's learning rate still evolve.
FROZEN = ("foresight.weight", "foresight.bias")


def frozen_mask(brain) -> torch.Tensor:
    return torch.cat([torch.full((p.numel(),), name in FROZEN, dtype=torch.bool) for name, p in brain.named_parameters()])


def breed(genomes: list[torch.Tensor], lifespans: list[float], population: int, elite: int, sigma: float,
          generator: torch.Generator, frozen: torch.Tensor | None = None) -> list[torch.Tensor]:
    order = sorted(range(len(genomes)), key=lambda i: -lifespans[i])
    children = [genomes[i].clone() for i in order[:elite]]
    pool = [genomes[i] for i in order[: max(2, len(genomes) // 4)]]
    while len(children) < population:
        a = pool[int(torch.randint(len(pool), (1,), generator=generator))]
        b = pool[int(torch.randint(len(pool), (1,), generator=generator))]
        w = float(torch.rand((), generator=generator))
        children.append(w * a + (1 - w) * b + sigma * torch.randn(a.shape, generator=generator))
    if frozen is not None:
        for child in children:
            child[frozen] = 0.0
    return children


def load_genome(brain, path: Path) -> torch.Tensor:
    """A saved genome, fitted to this brain: one that never learned gets the default learning rate appended, one that
    learned loses its rate (the last number) in a brain that does not learn, and one of an earlier shape grows into the
    current one (brains.grow)."""
    genome = torch.load(path)
    size = parameters_to_vector(brain.parameters()).numel()
    if brain.learns and genome.numel() == size - 1:
        genome = torch.cat([genome, torch.tensor([math.log(0.1)])])
    elif not brain.learns and genome.numel() == size + 1:
        genome = genome[:-1]
    elif genome.numel() != size and not getattr(brain, "legacy", True):
        genome = brains.grow(genome, brain)
    if genome.numel() != size:
        raise ValueError(f"{path} has {genome.numel()} numbers, this brain needs {size}")
    return genome


def run(brain_name: str, out_dir: Path, generations: int = 40, population: int = 24, per_camp: int = 5, max_days: int = 30,
        worlds: int = 2, sigma: float = 0.02, elite: int = 2, seed: int = 0, stop_alive: float = 0.8, stop_drink: float = 0.5,
        start: Path | None = None, first_generation: int = 0, learns: bool = False, rule: str = "rpe",
        spread: float = temperament.SPREAD, births: bool = False, energy: bool = True, wildlife: bool = True,
        puddles: bool = True, land: str = "danyang", plants: bool = True, sky: bool = True, graded: bool = True,
        animals: bool = True, graft: Path | None = None, graft_from: str = "A", sleep_switch: bool = True) -> list[dict]:
    """start: a saved genome to descend from instead of a random ancestor; generation numbers then go on from
    first_generation, and the worlds lived are the ones those generation numbers would have had.
    graft: for brain D, a saved genome of another brain (graft_from) whose senses D's ancestor is given (regions.graft)."""
    torch.set_num_threads(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    brain = brains.make(brain_name, seed, learns, rule)
    generator = torch.Generator().manual_seed(seed + first_generation)
    if graft is not None:
        from .regions import graft as give_senses
        ancestor = give_senses(brain, graft, graft_from)
    else:
        ancestor = load_genome(brain, start) if start else parameters_to_vector(brain.parameters()).detach().clone()
    frozen = frozen_mask(brain)
    ancestor[frozen] = 0.0
    genomes = [ancestor.clone()] + [ancestor + sigma * torch.randn(ancestor.shape, generator=generator) for _ in range(population - 1)]
    for genome in genomes:
        genome[frozen] = 0.0
    fitness_key = "lineage_days" if births else "lifespan"
    history = []
    for g in range(first_generation, first_generation + generations):
        started = time.perf_counter()
        seeds = [seed * 1000 + g * 10 + k for k in range(worlds)]
        results = []
        rates = []
        for genome in genomes:
            vector_to_parameters(genome, brain.parameters())
            results.append(evaluate(brain, seeds, per_camp, max_days, spread, births=births, energy=energy, wildlife=wildlife, puddles=puddles, land=land, plants=plants, sky=sky, graded=graded,
                                    animals=animals, sleep_switch=sleep_switch))
            rates.append(brain.learning_rate())
        fitness = [r[fitness_key] for r in results]
        best = max(range(len(genomes)), key=fitness.__getitem__)
        vector_to_parameters(genomes[best], brain.parameters())
        genes = brain.genes_values()
        drinks = [r["drank_when_thirsty_at_water"] for r in results if r["drank_when_thirsty_at_water"] is not None]
        top = results[best]
        record = {
            "generation": g, "brain": brain_name, "learns": learns, "rule": rule if learns else None, "spread": spread,
            "births": births, "energy": energy, "wildlife": wildlife, "puddles": puddles, "land": land, "plants": plants, "sky": sky, "graded": graded, "animals": animals, "sleep_switch": sleep_switch, "seconds": round(time.perf_counter() - started, 1), "worlds": seeds,
            "best_lifespan": round(top["lifespan"], 2), "mean_lifespan": round(sum(r["lifespan"] for r in results) / len(results), 2),
            "best_lineage_days": round(top["lineage_days"], 2),
            "mean_lineage_days": round(sum(r["lineage_days"] for r in results) / len(results), 2),
            "best_alive_after_day6": round(top["alive_after_day6"], 3),
            "mean_alive_after_day6": round(sum(r["alive_after_day6"] for r in results) / len(results), 3),
            "best_drank_when_thirsty_at_water": top["drank_when_thirsty_at_water"],
            "best_drank_early": top["drank_early"], "best_drank_late": top["drank_late"],
            "mean_drank_when_thirsty_at_water": round(sum(drinks) / len(drinks), 3) if drinks else None,
            "best_reward_per_choice": top["reward_per_choice"],
            "best_learning_rate": rates[best], "best_think_steps": round(top["think_steps"], 2),
            "best_afraid_approach_rate": top["afraid_approach_rate"], "best_afraid_share": round(top["afraid_share"], 3),
            "best_tasted_per_person": round(top["tasted_per_person"], 2),
            "best_aversions_per_person": round(top["aversions_per_person"], 2),
            "best_places_known": round(top["places_known"], 3), "best_acts_tried": round(top["acts_tried"], 1),
            "best_births_per_founder": round(top["births_per_founder"], 2), "best_deepest_generation": top["deepest_generation"],
            "best_genes": {name: round(v, 3) for name, v in zip(temperament.GENES, genes)} if genes else None,
        }
        history.append(record)
        with (out_dir / "generations.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        torch.save(genomes[best], out_dir / f"best_gen{g:03d}.pt")
        drank = top["drank_when_thirsty_at_water"]
        if top["alive_after_day6"] >= stop_alive and drank is not None and drank >= stop_drink:
            torch.save(genomes[best], out_dir / "ancestor.pt")
            break
        genomes = breed(genomes, fitness, population, elite, sigma, generator, frozen)
    return history
