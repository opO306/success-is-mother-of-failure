import pytest

from engine.agentworld.model import Injury
from engine.primal import body as physiology
from engine.primal import sky
from engine.primal.body import PrimalBody
from engine.primal.config import SLOTS, PrimalConfig


def _real_seasons():
    c = PrimalConfig()
    c.days_per_season = 91
    return c


def _sim_day(day_of_year):
    return 1 + round((day_of_year - sky.MARCH_FIRST) / 365 * 364)


def test_day_length_follows_the_sun_at_danyang_and_slots_are_lit_accordingly():
    c = _real_seasons()
    summer, winter = _sim_day(172), _sim_day(355)
    assert 14.3 < sky.day_length(summer, c) < 14.9 and 9.4 < sky.day_length(winter, c) < 9.9
    assert sky.daylight("낮", winter, c) == 1.0 and sky.daylight("밤", summer, c) == 0.0
    assert sky.daylight("새벽", summer, c) > 0.0 == sky.daylight("새벽", winter, c)


def test_the_moon_lights_a_night_a_little_and_a_fire_more():
    c = _real_seasons()
    full = 1 + int(sky.SYNODIC_MONTH / 2)
    assert sky.light("밤", 1, c) == 0.0
    assert 0.2 < sky.light("밤", full, c) <= sky.MOONLIGHT
    assert sky.light("밤", 1, c, fire=True) == sky.FIRELIGHT


def test_the_body_clock_pushes_toward_sleep_at_night_later_for_an_owl_and_light_holds_it_back():
    assert sky.circadian_pressure("밤", -2.0, 0.0) > sky.circadian_pressure("밤", 2.0, 0.0)
    assert sky.circadian_pressure("새벽", 2.0, 0.0) > sky.circadian_pressure("새벽", -2.0, 0.0)
    assert sky.circadian_pressure("밤", 0.0, 1.0) < sky.circadian_pressure("밤", 0.0, 0.0)


def test_feelings_come_in_degrees_and_adrenaline_dulls_pain_and_hunger():
    c = PrimalConfig(graded_feelings=True)
    assert 0 < physiology.felt_levels(PrimalBody(hydration=0.8), c)["thirst"] < physiology.felt_levels(PrimalBody(hydration=0.3), c)["thirst"]
    hurt = PrimalBody(injuries=[Injury(kind="깊은 상처", bleeding=False)], reserve=0.2)
    calm = physiology.felt_levels(hurt, c)
    hurt.adrenaline = 1.0
    rushed = physiology.felt_levels(hurt, c)
    assert rushed["pain"] == pytest.approx(calm["pain"] * (1 - physiology.ANALGESIA))
    assert rushed["hunger"] < calm["hunger"]
    assert physiology.felt_levels(PrimalBody(sleep_debt=1.0), c, circadian=1.0)["sleepy"] > \
        physiology.felt_levels(PrimalBody(sleep_debt=1.0), c, circadian=0.0)["sleepy"]


def test_adrenaline_surges_with_a_wound_and_halves_and_a_frightened_cold_body_sleeps_badly():
    body = PrimalBody()
    physiology.hormones_slot(body, fear=0.0, harmed=True, felt_total=1.0)
    assert body.adrenaline == 1.0
    physiology.hormones_slot(body, fear=0.0, harmed=False, felt_total=1.0)
    assert body.adrenaline == 0.5
    c = PrimalConfig()
    assert physiology.sleep_quality(PrimalBody(), c, {}) == 1.0
    shaken = PrimalBody(cold=c.cold_felt)
    shaken.adrenaline = 0.8
    assert physiology.sleep_quality(shaken, c, {"pain": 0.6}) == pytest.approx(0.5 * 0.5 * 0.3)


def test_in_the_dark_nobody_sees_what_another_did():
    pytest.importorskip("torch")
    from engine.brain import brains, life
    from engine.primal.scenario import build_world
    world = build_world(seed=0, band_size=2, sky=True)
    camp = next(iter(world.people.values())).camp
    eater, onlooker = [p for p in world.people.values() if p.camp == camp][:2]
    world.lands[camp].fire = None
    world.day = 1                                       # a new moon
    stats = life.new_stats()
    life._born(world, brains.RandomPolicy(), stats, None)
    chosen = {eater.name: ("eat", [], None)}
    life._observe(world, stats, chosen, {}, None, SLOTS.index("밤"))
    assert onlooker.name not in stats["seen"]
    life._observe(world, stats, chosen, {}, None, SLOTS.index("낮"))
    assert onlooker.name in stats["seen"]


def test_a_genome_from_before_the_sky_and_the_body_clock_grows_in(tmp_path):
    torch = pytest.importorskip("torch")
    from torch.nn.utils import parameters_to_vector, vector_to_parameters
    from engine.brain import brains, evolve
    old = brains.make("A", seed=4, n_extra=brains.PRE_SKY_EXTRA, n_genes=brains.PRE_CLOCK_GENES, foresight=False, drives=False)
    torch.save(parameters_to_vector(old.parameters()).detach(), tmp_path / "old.pt")
    new = brains.make("A", seed=0)
    vector_to_parameters(evolve.load_genome(new, tmp_path / "old.pt"), new.parameters())
    assert torch.equal(new.genes.mean[: brains.PRE_CLOCK_GENES], old.genes.mean) and float(new.genes.mean[-1]) == 0.0
    width = new.encoder.situation.in_features - (senses_extra := len(__import__("engine.brain.senses", fromlist=["x"]).EXTRA_KINDS) - brains.PRE_SKY_EXTRA)
    assert torch.equal(new.encoder.situation.weight[:, :width], old.encoder.situation.weight)
    assert senses_extra == 3
