import pytest

from engine.agentworld.actions import Cursor
from engine.primal import body as physiology
from engine.primal.body import PrimalBody
from engine.primal.clerk import Step
from engine.primal.config import PrimalConfig, SLOTS
from engine.primal.day import run_slot
from engine.primal.scenario import build_world


def _c():
    return PrimalConfig(graded_feelings=True, sky=True, sleep_switch=True)


def test_pressure_builds_awake_and_drains_asleep_faster_when_the_sleep_is_deep():
    body = PrimalBody()
    for _ in range(4):
        physiology.pressure_slot(body, asleep=False, quality=1.0)
    awake = body.sleep_pressure
    assert awake > 0.6
    deep, shallow = PrimalBody(sleep_pressure=awake), PrimalBody(sleep_pressure=awake)
    physiology.pressure_slot(deep, asleep=True, quality=1.0)
    physiology.pressure_slot(shallow, asleep=True, quality=0.35)
    assert deep.sleep_pressure < shallow.sleep_pressure < awake


def test_a_tired_body_lying_down_at_night_falls_asleep_and_a_rested_one_at_noon_only_rests():
    c = _c()
    tired = PrimalBody(sleep_pressure=0.7)
    assert physiology.sleep_switch(tired, c, clock=0.9, lit=0.0, lying=True)
    rested = PrimalBody(sleep_pressure=0.2)
    assert not physiology.sleep_switch(rested, c, clock=0.05, lit=1.0, lying=True)


def test_a_body_kept_up_long_enough_sleeps_on_its_feet_at_night_but_not_at_noon():
    c = _c()
    spent = PrimalBody(sleep_pressure=1.0)
    assert physiology.sleep_switch(spent, c, clock=0.9, lit=0.0, lying=False)
    assert not physiology.sleep_switch(PrimalBody(sleep_pressure=1.0), c, clock=0.05, lit=1.0, lying=False)


def test_a_starving_parched_sleeper_wakes_within_a_few_slots_even_sleeping_badly():
    c = _c()
    body = PrimalBody(sleep_pressure=1.0, asleep=True, hydration=0.0, thirst_days=2, reserve=0.0, fat=0.2,
                      underfed_days=10)
    slots = 0
    while body.asleep and slots < 8:
        physiology.pressure_slot(body, asleep=True, quality=0.35)
        body.asleep = physiology.sleep_switch(body, c, clock=0.3, lit=0.5, lying=True)
        slots += 1
    assert not body.asleep and slots <= 4


def test_the_switch_holds_its_state_between_the_two_margins():
    c = _c()
    between = physiology.FALL_ASLEEP_MARGIN / 2
    asleep = PrimalBody(asleep=True, sleep_pressure=0.0)
    awake = PrimalBody(asleep=False, sleep_pressure=0.0)
    clock = between / physiology.CLOCK_WEIGHT
    assert physiology.sleep_switch(asleep, c, clock, 0.0, True) and not physiology.sleep_switch(awake, c, clock, 0.0, True)


def test_in_the_world_choosing_sleep_lies_down_and_the_body_decides_whether_sleep_comes():
    world = build_world(seed=0, band_size=2, sky=True, graded=True, sleep_switch=True)
    people = list(world.people.values())
    tired, rested = people[0], people[1]
    tired.body.sleep_pressure, rested.body.sleep_pressure = 0.9, 0.0
    rested.location = tired.location
    night = SLOTS.index("밤")
    run_slot(world, {p.name: Cursor([Step(op="sleep")]) for p in (tired, rested)}, night, lambda asks, slot: {})
    assert tired.name in world.asleep and tired.body.asleep
    assert rested.name not in world.asleep and not rested.body.asleep


def test_without_the_switch_a_debt_still_collapses_the_body_as_before():
    world = build_world(seed=0, band_size=1)
    person = next(iter(world.people.values()))
    person.body.sleep_debt = world.config.collapse_debt
    run_slot(world, {}, 2, lambda asks, slot: {})
    assert person.name in world.asleep


def test_breeding_keeps_the_inborn_forecast_at_zero():
    torch = pytest.importorskip("torch")
    from torch.nn.utils import parameters_to_vector
    from engine.brain import brains, evolve
    brain = brains.make("A", seed=0, learns=True)
    frozen = evolve.frozen_mask(brain)
    assert int(frozen.sum()) == brain.foresight.weight.numel() + brain.foresight.bias.numel()
    base = parameters_to_vector(brain.parameters()).detach()
    children = evolve.breed([base + 1.0, base + 2.0], [1.0, 2.0], 5, 1, 0.1, torch.Generator().manual_seed(0), frozen)
    assert all(float(child[frozen].abs().sum()) == 0.0 for child in children)
