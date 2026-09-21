import random

import pytest

from engine.brain import choices, life, senses, temperament
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector, vector_to_parameters  # noqa: E402

from engine.brain import brains, evolve  # noqa: E402


def _person(world):
    return next(iter(world.people.values()))


class Scripted(brains.RandomPolicy):
    """Always does one act with the first of everything, or waits."""

    def __init__(self, op):
        self.op = op

    def decide(self, person, sense, options, rng):
        option = next((o for o in options if o.op == self.op), next(o for o in options if o.op == "wait"))
        return option, [c[0] for c in option.args], {"think_steps": 0}


def test_held_things_are_felt_lying_things_are_not_and_taste_shows_only_after_a_mouth_tried_it():
    world = build_world(seed=0, band_size=2)
    person = _person(world)
    stone = next(t for t in person.carried if t.kind == "강돌")
    held = senses.carried_tokens(person)[person.carried.index(stone)]
    assert len(held.props) == senses.PROPS and held.props[senses.LOOKS] == 1.0 and held.props[senses.LOOKS + 1] == 1.0
    world.lands[person.location].lying.insert(0, stone)
    assert senses.lying_tokens(world, person)[0][0].props[senses.LOOKS:senses.LOOKS + 4] == (0.0,) * 4
    mushroom = world.maker.make("붉은 버섯")
    person.carried.insert(0, mushroom)
    assert senses.carried_tokens(person)[0].props[senses.LOOKS + 7] == 0.0
    mushroom.tested.setdefault(person.name, set()).add("taste")
    assert senses.carried_tokens(person, gain=2.0)[0].props[senses.LOOKS + 7] == 2.0
    perceived = senses.sense(world, person, 0)
    assert len(perceived.extra) == senses.EXTRA_SIZE and set(perceived.extra) == {0.0}


def test_tasting_is_the_engines_nibble_and_a_bitter_poison_is_felt_and_refused():
    world = build_world(seed=0, band_size=1)
    person = _person(world)
    mushroom = world.maker.make("붉은 버섯")
    person.carried.insert(0, mushroom)
    taste = next(o for o in choices.options(world, person) if o.op == "taste")
    step = choices.to_step(taste, [taste.args[0][0]])
    assert step.op == "test" and step.content == "맛" and step.items == [1]
    stats = life.new_stats()
    life.live_day(world, Scripted("taste"), random.Random(0), stats)
    assert "taste" in mushroom.tested[person.name] and stats["tasted"] >= 1
    assert stats["felt"][person.name]["bitter"] > 0 and stats["bonus"][person.name] < 0


def test_the_same_pack_frightens_the_fearful_more_harmless_threats_wear_off_and_a_hurt_sensitises_at_once():
    calm = temperament.from_values([0.0] * len(temperament.GENES))
    fearful = temperament.from_values([1.0] + [0.0] * (len(temperament.GENES) - 1))
    assert temperament.feel_threat(temperament.Nerves(), fearful, 0.4, False) > temperament.feel_threat(temperament.Nerves(), calm, 0.4, False)
    worn = temperament.Nerves()
    first = temperament.feel_threat(worn, calm, 0.4, False)
    for _ in range(10):
        temperament.feel_threat(worn, calm, 0.4, False)
    assert worn.fear < first
    hurt = temperament.Nerves()
    assert temperament.feel_threat(hurt, calm, 0.4, True) > first
    world = build_world(seed=0, band_size=1)
    person = _person(world)
    wolves = next(h for h in world.herds if h.species == "늑대")
    wolves.place = person.location
    assert temperament.threat_at(world, person, len(world.lands[person.location].corpses)) >= 0.8


def test_people_of_one_lineage_differ_the_same_person_is_born_the_same_and_genes_move_the_mean():
    a = temperament.draw(None, 3, "P01")
    assert a == temperament.draw(None, 3, "P01") != temperament.draw(None, 3, "P02")
    assert temperament.draw(None, 3, "P01", spread=0.0) == temperament.DEFAULT
    names = [f"P{i:02d}" for i in range(200)]
    bold = [-1.0] + [0.0] * (len(temperament.GENES) - 1)
    assert sum(temperament.draw(bold, 3, n).fear_gain for n in names) < sum(temperament.draw(None, 3, n).fear_gain for n in names)


def test_action_noise_flattens_choices_and_people_pull_draws_toward_seeking_company():
    world = build_world(seed=0, band_size=2)
    person = _person(world)
    brain = brains.make("A", seed=0, learns=True)
    perceived, possible = senses.sense(world, person, 0), choices.options(world, person)
    follow = [o.op for o in possible].index("follow")

    def probs(z):
        brain.set_temper(person.name, temperament.from_values(z))
        return brain.decide(person.name, perceived, possible, random.Random(0))[2]["trace"][2]

    def entropy(p):
        return float(-(p * p.clamp_min(1e-12).log()).sum())

    zero = [0.0] * len(temperament.GENES)
    noisy, sharp, social = list(zero), list(zero), list(zero)
    noisy[6], sharp[6], social[7] = 1.5, -1.5, 2.0
    assert entropy(probs(noisy)) > entropy(probs(sharp))
    assert float(probs(social)[follow]) > float(probs(zero)[follow])


def test_a_genome_from_before_stage_4_grows_in_and_chooses_its_old_acts_exactly_as_before(tmp_path):
    old = brains.make("A", seed=5, legacy=True, n_categories=brains.PRE_SEEN_CATEGORIES, foresight=False, drives=False)
    torch.save(parameters_to_vector(old.parameters()).detach(), tmp_path / "old.pt")
    new = brains.make("A", seed=0)
    vector_to_parameters(evolve.load_genome(new, tmp_path / "old.pt"), new.parameters())
    world = build_world(seed=0, band_size=2)
    person = _person(world)
    perceived = senses.sense(world, person, 0, extra=(0.9,) * senses.EXTRA_SIZE)
    legacy = senses.Sense(perceived.body, perceived.context,
                          [senses.Token(t.category, t.kind, t.props[:senses.LOOKS]) for t in perceived.tokens])
    h_old, _ = old.think(person.name, legacy)
    h_new, _ = new.think(person.name, perceived)
    assert torch.allclose(old.op_head(h_old), new.op_head(h_new)[: brains.LEGACY_OPS], atol=1e-5)
    assert float(new.op_head.bias[choices.OPS.index("taste")]) == brains.NEW_OP_BIAS
    assert float(new.op_head.bias[choices.OPS.index("mate")]) == pytest.approx(float(old.op_head.bias.mean()), abs=1e-6)
    assert new.genes_values() == [0.0] * len(temperament.GENES)
    stage4 = brains.make("A", seed=2, n_ops=brains.STAGE4_OPS, n_categories=brains.PRE_SEEN_CATEGORIES,
                         n_extra=brains.PRE_SKY_EXTRA, n_genes=brains.PRE_CLOCK_GENES, foresight=False, drives=False)
    torch.save(parameters_to_vector(stage4.parameters()).detach(), tmp_path / "stage4.pt")
    assert evolve.load_genome(new, tmp_path / "stage4.pt").numel() == parameters_to_vector(new.parameters()).numel()
    learned = brains.make("B", seed=1, legacy=True, n_categories=brains.PRE_SEEN_CATEGORIES, foresight=False, drives=False)
    learned.enable_learning(0.3)
    torch.save(parameters_to_vector(learned.parameters()).detach(), tmp_path / "learned.pt")
    learner = brains.make("B", seed=0, learns=True)
    vector_to_parameters(evolve.load_genome(learner, tmp_path / "learned.pt"), learner.parameters())
    assert learner.learning_rate() == pytest.approx(0.3, rel=1e-4)


def test_a_band_lives_with_tempers_fear_and_feelings_and_every_person_gets_a_row():
    brain = brains.make("A", seed=0, learns=True)
    records = []
    result = evolve.evaluate(brain, [0], per_camp=2, max_days=3, records=records)
    assert {"afraid_approach_rate", "afraid_share", "tasted_per_person", "aversions_per_person", "places_known", "acts_tried"} <= set(result)
    assert len(records) == 6 and len({r["fear_gain"] for r in records}) == 6
    assert all(0 <= r["days"] <= 3 for r in records)
