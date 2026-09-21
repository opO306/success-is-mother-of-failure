import math

import pytest

from engine.bankruptcy import CompanyState
from engine.entities import CompanyArchetype
from engine.scenarios import build_full_world

SEEDS = range(20)  # keep the pytest run fast; run_batch.py covers the full 100-seed sweep
TICKS = 30


@pytest.mark.parametrize("seed", SEEDS)
def test_resources_never_go_negative(seed):
    world = build_full_world(seed=seed)
    for _ in range(TICKS):
        world.tick()
        for company in world.companies:
            r = company.resources
            assert r.capital >= 0
            assert r.tech >= 0
            assert r.legitimacy >= 0
            assert r.coercion >= 0
            assert r.coercion_abuse_cumulative >= 0
        for individual in world.individuals:
            assert individual.resources.capital >= 0
        for vigilante in world.vigilantes:
            assert vigilante.resources.capital >= 0


@pytest.mark.parametrize("seed", SEEDS)
def test_currency_values_stay_finite_and_non_negative(seed):
    world = build_full_world(seed=seed)
    for tick in world.run(TICKS):
        for value in tick.currency_values.values():
            assert value >= 0
            assert math.isfinite(value)


@pytest.mark.parametrize("seed", SEEDS)
def test_hive_mind_company_is_never_marked_dead(seed):
    world = build_full_world(seed=seed)
    hive_names = {c.name for c in world.companies if c.archetype is CompanyArchetype.HIVE_MIND}
    for tick in world.run(TICKS):
        for name in hive_names:
            if name in tick.company_states:
                assert tick.company_states[name] is not CompanyState.DEAD


@pytest.mark.parametrize("seed", SEEDS)
def test_dead_companies_stay_dead(seed):
    world = build_full_world(seed=seed)
    ever_dead: set[str] = set()
    for tick in world.run(TICKS):
        for name, state in tick.company_states.items():
            if name in ever_dead:
                assert state is CompanyState.DEAD, f"{name} revived at tick {tick.index}"
            if state is CompanyState.DEAD:
                ever_dead.add(name)


@pytest.mark.parametrize("seed", SEEDS)
def test_full_batch_runs_without_raising(seed):
    world = build_full_world(seed=seed)
    world.run(TICKS)  # the assertion is simply that this doesn't raise


def test_company_count_stays_bounded_over_a_long_run():
    # the 30-tick tests above stop before the point where self-replication once ran away
    world = build_full_world(seed=0)
    for _ in range(60):
        world.tick()
        assert len(world.companies) < 200


def test_companies_with_nobody_in_them_do_not_trade():
    world = build_full_world(seed=0)
    shell = world.companies[0]
    shell.employees = []
    tick = world.tick()
    assert not any(shell.name in (t.actor, t.counterpart) for t in tick.trades)
