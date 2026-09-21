import json

import pytest

torch = pytest.importorskip("torch")
from engine.brain import brains, evolve  # noqa: E402


def test_a_genome_is_scored_by_how_long_its_people_lived_and_nothing_else():
    brain = brains.make("B", seed=0)
    result = evolve.evaluate(brain, seeds=[1], per_camp=1, max_days=3)
    assert 0 < result["lifespan"] <= 3
    assert 0 <= result["alive_after_day6"] <= 1
    assert set(result) == {"lifespan", "alive_after_day6", "drank_when_thirsty_at_water", "drank_early", "drank_late",
                           "reward_per_choice", "think_steps", "afraid_approach_rate", "afraid_share", "tasted_per_person",
                           "aversions_per_person", "places_known", "acts_tried", "lineage_days", "births_per_founder",
                           "deepest_generation"}


def test_the_longest_lived_pass_on_unchanged_and_children_are_mixed_with_noise():
    gen = torch.Generator().manual_seed(0)
    genomes = [torch.full((5,), float(i)) for i in range(8)]
    lifespans = [1, 9, 3, 7, 2, 8, 4, 5]
    children = evolve.breed(genomes, lifespans, population=8, elite=2, sigma=0.01, generator=gen)
    assert len(children) == 8
    assert torch.equal(children[0], genomes[1]) and torch.equal(children[1], genomes[5])
    # parents come only from the longest-lived quarter (genomes 1 and 5, values 1 and 5)
    assert all(0.9 <= float(c.mean()) <= 5.1 for c in children[2:])
    assert not any(torch.equal(c, g) for c in children[2:] for g in genomes)


def test_a_short_evolution_writes_every_generation_and_its_best_genome(tmp_path):
    history = evolve.run("A", tmp_path, generations=2, population=3, per_camp=1, max_days=2, worlds=1, elite=1, stop_alive=2.0)
    assert [h["generation"] for h in history] == [0, 1]
    rows = [json.loads(line) for line in (tmp_path / "generations.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2 and (tmp_path / "best_gen001.pt").exists() and not (tmp_path / "ancestor.pt").exists()
    more = evolve.run("A", tmp_path, generations=1, population=2, per_camp=1, max_days=2, worlds=1, elite=1, stop_alive=2.0,
                      start=tmp_path / "best_gen001.pt", first_generation=2)
    assert [h["generation"] for h in more] == [2] and (tmp_path / "best_gen002.pt").exists()
