from engine.bankruptcy import CompanyState, check_company_state
from engine.config import SimulationConfig
from engine.entities import Company, CompanyArchetype, Employee, Resources


def loyal_employee(name="e") -> Employee:
    return Employee(
        name=name, wage=10, expected_wage=10, value_alignment=1.0,
        retaliation_cost=0.0, alternative_attractiveness=0.0,
    )


def mercenary_employee(name="e") -> Employee:
    return Employee(
        name=name, wage=10, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0.0, alternative_attractiveness=0.5,
    )


def test_healthy_company_is_alive():
    config = SimulationConfig()
    company = Company(
        name="co", archetype=CompanyArchetype.GROWTH,
        resources=Resources(capital=100, legitimacy=1.0),
        employees=[loyal_employee()],
    )
    assert check_company_state(company, config) is CompanyState.ALIVE


def test_zero_legitimacy_is_isolated_not_dead():
    config = SimulationConfig()
    company = Company(
        name="co", archetype=CompanyArchetype.GROWTH,
        resources=Resources(capital=100, legitimacy=0.0),
        employees=[loyal_employee()],
    )
    assert check_company_state(company, config) is CompanyState.ISOLATED


def test_zero_capital_survives_on_legitimacy_if_employees_are_true_believers():
    config = SimulationConfig()
    company = Company(
        name="co", archetype=CompanyArchetype.TRUTH_SEEKER,
        resources=Resources(capital=0, legitimacy=1.0),
        employees=[loyal_employee(), loyal_employee("e2")],
    )
    # value_alignment=1.0 keeps A above the (0 - 0) desertion threshold even at wage=0
    assert check_company_state(company, config) is not CompanyState.DEAD


def test_zero_capital_with_mercenary_staff_collapses():
    config = SimulationConfig()
    company = Company(
        name="co", archetype=CompanyArchetype.GROWTH,
        resources=Resources(capital=0, legitimacy=1.0),
        employees=[mercenary_employee(), mercenary_employee("e2")],
    )
    assert check_company_state(company, config) is CompanyState.DEAD


def test_mass_desertion_kills_company_even_with_capital_remaining():
    config = SimulationConfig()
    # Fully paid, but a much more attractive outside option pulls everyone away
    # regardless of the company's own capital health.
    poached = Employee(
        name="e", wage=10, expected_wage=10, value_alignment=0.0,
        retaliation_cost=0.0, alternative_attractiveness=0.95,
    )
    company = Company(
        name="co", archetype=CompanyArchetype.GROWTH,
        resources=Resources(capital=1000, legitimacy=1.0),
        employees=[poached, Employee(**{**poached.__dict__, "name": "e2"})],
    )
    assert check_company_state(company, config) is CompanyState.DEAD


def test_hive_mind_never_dies_from_desertion():
    config = SimulationConfig()
    hive = Company(
        name="hive", archetype=CompanyArchetype.HIVE_MIND,
        resources=Resources(capital=0, legitimacy=1.0),
        employees=[mercenary_employee(), mercenary_employee("e2")],
    )
    assert check_company_state(hive, config) is not CompanyState.DEAD
