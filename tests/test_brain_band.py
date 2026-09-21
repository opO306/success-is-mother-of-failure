import pytest

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector  # noqa: E402

from engine.brain import band as band_module  # noqa: E402
from engine.brain import brains, life, lifecycle  # noqa: E402
from engine.primal.scenario import build_world  # noqa: E402


def _band(inherit="all"):
    brain = brains.make("A", seed=0, learns=True)
    seed = parameters_to_vector(brain.parameters()).detach().clone()
    return band_module.Band("A", seed, inherit=inherit), seed


def test_every_founder_gets_a_brain_of_their_own_near_the_seed():
    band, seed = _band()
    band.found(["P01", "P02"])
    assert not torch.equal(band.genomes["P01"], band.genomes["P02"])
    assert float((band.genomes["P01"] - seed).abs().mean()) < 0.1


def test_a_child_is_a_mix_of_its_parents_and_an_orphan_falls_back_to_the_seed():
    band, seed = _band()
    band.found(["P01", "P02"])
    band.born("P03", "P01", "P02")
    a, b, child = band.genomes["P01"], band.genomes["P02"], band.genomes["P03"]
    between = ((child - a).norm() + (child - b).norm()) / 2
    assert float(between) < float((a - b).norm()) + 1.0
    band.born("P04", None, None)
    assert float((band.genomes["P04"] - seed).abs().mean()) < 0.1


def test_inheriting_only_the_learning_machinery_leaves_the_rest_untaught():
    band, seed = _band(inherit="learning")
    band.found(["P01", "P02"])
    band.born("P03", "P01", "P02")
    mask = band._mask
    child = band.genomes["P03"]
    assert float((child[mask] - seed[mask]).abs().mean()) < 0.2          # the machinery came from the parents
    assert float((child[~mask] - seed[~mask]).abs().mean()) > 0.01       # the rest did not


def test_a_band_of_its_own_brains_lives_a_day_and_the_dead_are_buried():
    band, _ = _band()
    world = build_world(seed=0, band_size=2, sky=True, graded=True, sleep_switch=True)
    population = lifecycle.found(world, band.genes_values())
    band.found(sorted(world.people))
    import random
    life.live_day(world, band, random.Random(0), life.new_stats(), population)
    someone = sorted(world.people)[0]
    band.buried(someone)
    assert someone not in band.genomes and len(band.genomes) == len(world.people) - 1
