from engine.config import SimulationConfig
from engine.entities import (
    Company,
    CompanyArchetype,
    Employee,
    Resources,
)
from engine.formulas import (
    alignment_score,
    currency_value,
    exchange_rate,
    necessity,
    trade_will_proceed,
    will_desert,
)


def make_company(archetype=CompanyArchetype.GROWTH, **resource_kwargs) -> Company:
    return Company(name="test-co", archetype=archetype, resources=Resources(**resource_kwargs))


def test_alignment_score_is_clipped_to_unit_range():
    config = SimulationConfig()
    overpaid = Employee(
        name="a", wage=100, expected_wage=10, value_alignment=1.0,
        retaliation_cost=0, alternative_attractiveness=0,
    )
    assert alignment_score(overpaid, config) == 1.0

    unpaid = Employee(
        name="b", wage=0, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0, alternative_attractiveness=0,
    )
    assert alignment_score(unpaid, config) == 0.0


def test_low_alignment_without_exit_costs_deserts():
    config = SimulationConfig()
    company = make_company()
    disloyal = Employee(
        name="c", wage=0, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0.0, alternative_attractiveness=0.5,
    )
    assert will_desert(disloyal, company, config) is True


def test_retaliation_fear_can_keep_a_reluctant_stayer():
    config = SimulationConfig()
    company = make_company()
    reluctant = Employee(
        name="d", wage=0, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0.9, alternative_attractiveness=0.5,
    )
    assert will_desert(reluctant, company, config) is False


def test_hive_mind_employees_never_desert():
    config = SimulationConfig()
    hive = make_company(archetype=CompanyArchetype.HIVE_MIND)
    disloyal = Employee(
        name="e", wage=0, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0.0, alternative_attractiveness=1.0,
    )
    assert will_desert(disloyal, hive, config) is False


def test_emotionless_company_ignores_relationship_value_in_trades():
    config = SimulationConfig(lambda_relationship=0.9)
    emotionless = make_company(archetype=CompanyArchetype.EMOTIONLESS)
    # Deeply hated (-1) counterparty, but the trade is still marginally profitable.
    assert trade_will_proceed(0.01, -1.0, emotionless, config) is True


def test_ordinary_company_can_refuse_a_profitable_trade_out_of_spite():
    config = SimulationConfig(lambda_relationship=0.9)
    ordinary = make_company(archetype=CompanyArchetype.GROWTH)
    assert trade_will_proceed(0.01, -1.0, ordinary, config) is False


def test_zero_legitimacy_zeroes_currency_value_even_with_high_tech():
    config = SimulationConfig()
    assert currency_value(Resources(legitimacy=0.0, tech=999.0), necessity=1.0, config=config) == 0.0


def test_necessity_falls_as_alternative_suppliers_appear():
    high = necessity(demand_for_exclusive_resource=10, num_alternative_suppliers=0)
    low = necessity(demand_for_exclusive_resource=10, num_alternative_suppliers=9)
    assert high > low


def test_fast_follower_copy_crashes_original_currency_value():
    config = SimulationConfig()
    resources = Resources(legitimacy=1.0, tech=10.0)
    before = currency_value(resources, necessity(10, num_alternative_suppliers=0), config)
    after = currency_value(resources, necessity(10, num_alternative_suppliers=1), config)
    assert after < before


def test_coercion_abuse_suppresses_currency_value():
    config = SimulationConfig()
    clean = Resources(legitimacy=1.0, tech=1.0, coercion_abuse_cumulative=0.0)
    abusive = Resources(legitimacy=1.0, tech=1.0, coercion_abuse_cumulative=5.0)
    v_clean = currency_value(clean, necessity=1.0, config=config)
    v_abusive = currency_value(abusive, necessity=1.0, config=config)
    assert v_abusive < v_clean


def test_exchange_rate_is_symmetric_ratio():
    assert exchange_rate(2.0, 1.0) == 2.0
    assert exchange_rate(1.0, 2.0) == 0.5


def test_exchange_rate_handles_zero_counterpart():
    assert exchange_rate(0.0, 0.0) == 0.0
    assert exchange_rate(1.0, 0.0) == float("inf")
