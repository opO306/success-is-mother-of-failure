import random

import pytest

from engine.brain import choices, life, senses
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector, vector_to_parameters  # noqa: E402

from engine.brain import brains, evolve, probe  # noqa: E402


def _moment(seed=0):
    world = build_world(seed=seed, band_size=2)
    person = next(iter(world.people.values()))
    return world, person, senses.sense(world, person, 1), choices.options(world, person)


def test_a_genome_from_before_foresight_grows_in_and_chooses_exactly_as_before(tmp_path):
    old = brains.make("A", seed=3, learns=True, foresight=False, drives=False)
    torch.save(parameters_to_vector(old.parameters()).detach(), tmp_path / "old.pt")
    new = brains.make("A", seed=0, learns=True, drives=False)   # drives of their own would move the scores
    vector_to_parameters(evolve.load_genome(new, tmp_path / "old.pt"), new.parameters())
    assert float(new.foresight.trust) == 0.0 and float(new.foresight.weight.abs().sum()) == 0.0
    world, person, sense, options = _moment()
    before, _ = old.op_probs(person.name, sense, options)
    after, _ = new.op_probs(person.name, sense, options)
    assert torch.allclose(before, after, atol=1e-6)


def test_the_body_forecast_learns_what_an_act_does_to_the_body():
    brain = brains.make("A", seed=0, learns=True)
    world, person, sense, options = _moment()
    option, picks, info = brain.decide(person.name, sense, options, random.Random(0))
    trace = info["trace"]
    then = tuple(sense.body)
    now = tuple(v - 0.5 if i == 0 else v for i, v in enumerate(then))   # thirst eased by half
    x = trace[0] + brain.op_embedding(trace[1][trace[3]])
    misses = []
    for _ in range(150):
        misses.append(abs(float(brain.expect(person.name, x)[0]) + 0.5))
        brain.learn_body(person.name, trace, then, now)
    assert misses[-1] < 0.1 * misses[0]


def test_trusting_a_forecast_of_feeling_worse_holds_that_act_back():
    brain = brains.make("A", seed=0, learns=True)
    world, person, sense, options = _moment()
    k = next(i for i, o in enumerate(options) if o.op == "wait")
    before, h = brain.op_probs(person.name, sense, options)
    with torch.no_grad():
        brain.foresight.trust.fill_(2.0)
        brain.foresight.weight.zero_()
    x = h + brain.op_embedding(torch.tensor(brains.OPS.index("wait")))
    own = torch.zeros(senses.BODY_SIZE, brain.d)
    own[0] = x / float(x @ x)            # waiting is forecast to make thirst one step worse; nothing else changes
    brain.expecting[person.name] = own
    after, _ = brain.op_probs(person.name, sense, options)
    assert float(after[k]) < float(before[k])


def test_asking_what_a_brain_would_do_changes_nothing_in_it():
    brain = brains.make("B", seed=0, learns=True)
    world, person, sense, options = _moment()
    brain.decide(person.name, sense, options, random.Random(0))
    state = [t.clone() for t in brain.state[person.name]]
    brain.op_probs(person.name, sense, options)
    assert all(torch.equal(a, b) for a, b in zip(state, brain.state[person.name]))


def test_a_band_lives_with_the_forecast_learning_and_the_probe_asks_all_three_questions():
    brain = brains.make("A", seed=0, learns=True)
    result = probe.run(brain, [0, 1], per_camp=2, days=3, ask_every=3, branch_every=6, energy=True, land="danyang",
                       plants=True, sky=True, graded=True, animals=True, puddles=True, wildlife=True)
    assert result["decisions"] > 0
    assert set(result["seeing"]) <= set(probe.BODY_READS + probe.WORLD_READS) and result["seeing"]
    assert result["imagining"]["moments"] > 0 and "mse_forecast" in result["imagining"]
    assert brain.expecting, "people's own forecasts were learned while living"
