import random

import pytest

from engine.brain import choices, senses
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector  # noqa: E402

from engine.brain import brains, evolve, regions  # noqa: E402


def _moment(seed=0):
    world = build_world(seed=seed, band_size=2, land="danyang", energy=True, plants=True, sky=True, graded=True,
                        animals=True, puddles=True, wildlife=True)
    person = next(iter(world.people.values()))
    return world, person, senses.sense(world, person, 1), choices.options(world, person)


def test_brain_d_chooses_among_what_is_possible_and_says_which_area_pushed_for_it():
    brain = brains.make("D", seed=0, learns=True)
    world, person, sense, options = _moment()
    option, picks, info = brain.decide(person.name, sense, options, random.Random(0))
    assert option in options and len(picks) == len(option.args)
    assert set(info["areas"]) == set(regions.AREAS) and 1 <= info["think_steps"] <= regions.MAX_STEPS
    assert "trace" in info


def test_asking_d_what_it_would_do_leaves_its_memories_as_they_were():
    brain = brains.make("D", seed=0, learns=True)
    world, person, sense, options = _moment()
    brain.decide(person.name, sense, options, random.Random(0))
    state = {k: v.clone() for k, v in brain.state[person.name].items()}
    brain.op_probs(person.name, sense, options)
    assert all(torch.equal(state[k], brain.state[person.name][k]) for k in state)


def test_an_area_carries_its_memory_from_moment_to_moment():
    brain = brains.make("D", seed=0, learns=True)
    world, person, sense, options = _moment()
    brain.decide(person.name, sense, options, random.Random(0))
    first = brain.state[person.name]["hippocampus"].clone()
    brain.decide(person.name, sense, options, random.Random(0))
    assert not torch.equal(first, brain.state[person.name]["hippocampus"])


def test_a_graft_gives_d_the_senses_another_lineage_learned_and_nothing_else(tmp_path):
    donor = brains.make("A", seed=7, learns=True)
    torch.save(parameters_to_vector(donor.parameters()).detach(), tmp_path / "a.pt")
    brain = brains.make("D", seed=0, learns=True)
    before = {n: p.clone() for n, p in brain.named_parameters()}
    genome = regions.graft(brain, tmp_path / "a.pt", "A")
    assert genome.numel() == parameters_to_vector(brain.parameters()).numel()
    assert torch.equal(brain.encoder.kind.weight, donor.encoder.kind.weight)
    assert torch.equal(brain.areas["hypothalamus"].vote.weight, before["areas.hypothalamus.vote.weight"])


def test_a_band_lives_days_with_brain_d():
    brain = brains.make("D", seed=0, learns=True)
    result = evolve.evaluate(brain, [0], per_camp=2, max_days=2)
    assert result["lifespan"] > 0 and result["think_steps"] >= 1
