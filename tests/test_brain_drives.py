import pytest

from engine.brain import choices, senses
from engine.primal.scenario import build_world

torch = pytest.importorskip("torch")
from torch.nn.utils import parameters_to_vector, vector_to_parameters  # noqa: E402

from engine.brain import brains, evolve  # noqa: E402


def _moment(hunger=0.0, thirst=0.0):
    world = build_world(seed=0, band_size=2)
    person = next(iter(world.people.values()))
    person.carried.insert(0, world.maker.make("잣"))
    person.location = next(n for n, l in world.lands.items() if l.gather)   # somewhere there is something to gather
    sense = senses.sense(world, person, 2)
    body = list(sense.body)
    body[senses.BODY_KINDS.index("hunger")] = hunger
    body[senses.BODY_KINDS.index("thirst")] = thirst
    return world, person, senses.Sense(tuple(body), sense.context, sense.tokens, sense.extra), choices.options(world, person)


def _chance(brain, person, sense, options, op):
    probs, _ = brain.op_probs(person.name, sense, options)
    return float(sum(p for o, p in zip(options, probs) if o.op == op))


def test_a_hungry_body_pulls_a_brain_toward_food_and_a_thirsty_one_toward_water():
    brain = brains.make("A", seed=0, learns=True)
    world, person, calm, options = _moment()
    _, _, hungry, _ = _moment(hunger=1.0)
    _, _, parched, _ = _moment(thirst=1.0)
    assert _chance(brain, person, hungry, options, "eat") > _chance(brain, person, calm, options, "eat")
    assert _chance(brain, person, hungry, options, "gather") > _chance(brain, person, calm, options, "gather")
    assert _chance(brain, person, parched, options, "drink") > _chance(brain, person, calm, options, "drink")


def test_the_pull_is_a_gene_evolution_can_switch_off():
    brain = brains.make("A", seed=0, learns=True)
    world, person, hungry, options = _moment(hunger=1.0)
    with_drive = _chance(brain, person, hungry, options, "eat")
    with torch.no_grad():
        brain.drives.gain.zero_()
    assert _chance(brain, person, hungry, options, "eat") < with_drive


def test_a_genome_from_before_the_drives_grows_in_with_them_at_full_strength(tmp_path):
    old = brains.make("A", seed=5, learns=True, drives=False)
    torch.save(parameters_to_vector(old.parameters()).detach(), tmp_path / "old.pt")
    new = brains.make("A", seed=0, learns=True)
    vector_to_parameters(evolve.load_genome(new, tmp_path / "old.pt"), new.parameters())
    assert torch.equal(new.drives.gain, torch.ones(len(brains.DRIVE_STATES)))
    assert torch.equal(new.op_head.weight, old.op_head.weight)


def test_a_meal_that_sickened_a_day_ago_is_the_one_that_turns_the_stomach():
    import random
    from engine.brain import life, senses
    from engine.primal.scenario import build_world
    brain = brains.make("A", seed=0, learns=True)
    world = build_world(seed=0, band_size=1)
    person = next(iter(world.people.values()))
    stats = life.new_stats()
    stats["tempers"][person.name] = __import__("engine.brain.temperament", fromlist=["x"]).DEFAULT
    stats["nerves"][person.name] = __import__("engine.brain.temperament", fromlist=["x"]).Nerves()
    stats["meals"][person.name] = [(world.day, "붉은 버섯")]          # eaten earlier today
    person.body.illness = world.config.illness_onset
    before = {person.name: (person.body.health, len(person.body.injuries), 0.0)}
    life._after_slot(world, brain, stats, {}, before, {})
    assert stats["aversions"] == 1
    things = brain.lifetime[person.name][1]
    mushroom = brain.encoder.tokens([life._kind_token("붉은 버섯")])[0]
    assert float(things @ mushroom) < 0, "the kind eaten before the sickness is now repellent"


def test_biting_a_stone_is_remembered_as_not_food():
    import random
    from engine.brain import life
    from engine.primal.scenario import build_world
    brain = brains.make("A", seed=0, learns=True)
    world = build_world(seed=0, band_size=1)
    person = next(iter(world.people.values()))
    stone = world.maker.make("강돌")
    person.carried.insert(0, stone)
    stats = life.new_stats()
    import engine.brain.temperament as temperament
    stats["tempers"][person.name], stats["nerves"][person.name] = temperament.DEFAULT, temperament.Nerves()
    before = {person.name: (person.body.health, len(person.body.injuries), person.body.illness)}
    life._after_slot(world, brain, stats, {person.name: ("eat", [stone], None)}, before, {})
    things = brain.lifetime[person.name][1]
    assert float(things @ brain.encoder.tokens([life._kind_token("강돌")])[0]) < 0


def test_food_that_fed_someone_is_looked_for_again():
    from engine.brain import life
    from engine.primal.scenario import build_world
    import engine.brain.temperament as temperament
    brain = brains.make("A", seed=0, learns=True)
    world = build_world(seed=0, band_size=1)
    person = next(iter(world.people.values()))
    nut = world.maker.make("잣")
    person.carried.insert(0, nut)
    stats = life.new_stats()
    stats["tempers"][person.name], stats["nerves"][person.name] = temperament.DEFAULT, temperament.Nerves()
    world.slot_done = {person.name: [{"op": "eat", "ok": True}]}
    before = {person.name: (person.body.health, len(person.body.injuries), person.body.illness)}
    life._after_slot(world, brain, stats, {person.name: ("eat", [nut], None)}, before, {})
    things = brain.lifetime[person.name][1]
    assert float(things @ brain.encoder.tokens([life._kind_token("잣")])[0]) > 0


def test_a_hungry_child_beside_you_pulls_toward_handing_food_over():
    from engine.brain import senses as S
    brain = brains.make("A", seed=0, learns=True)
    world, person, sense, options = _moment()
    other = [p for p in world.people.values() if p.name != person.name][0]
    other.location = person.location
    options = choices.options(world, person)
    assert any(o.op == "give" for o in options)
    extra = list(sense.extra)
    quiet = S.Sense(sense.body, sense.context, sense.tokens, tuple(extra))
    extra[S.EXTRA_KINDS.index("others_pain")] = 1.0
    crying = S.Sense(sense.body, sense.context, sense.tokens, tuple(extra))
    assert _chance(brain, person, crying, options, "give") > _chance(brain, person, quiet, options, "give")


def test_hunger_with_nothing_here_pulls_toward_going_and_following():
    from engine.brain import senses as S
    brain = brains.make("A", seed=0, learns=True)
    world, person, calm, options = _moment()
    person.location = next(n for n, l in world.lands.items() if not l.gather)   # a bare camp: nothing to pick here
    calm = S.sense(world, person, 2)
    body = list(calm.body)
    body[S.BODY_KINDS.index("hunger")] = 1.0
    hungry = S.Sense(tuple(body), calm.context, calm.tokens, calm.extra)
    options = choices.options(world, person)
    bare = [o for o in options if o.op in ("go", "follow", "wait")]
    assert bare, "there is somewhere to go and someone to follow"
    for op in ("go", "follow"):
        if any(o.op == op for o in options):
            assert _chance(brain, person, hungry, options, op) > _chance(brain, person, calm, options, op)
