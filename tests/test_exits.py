import random

from engine.config import SimulationConfig
from engine.council import CouncilOutcome, MemberResult, tally_votes
from engine.entities import (
    Company,
    CompanyArchetype,
    Employee,
    IndividualArchetype,
    Resources,
)
from engine.exits import apply_member_exits
from engine.llm_agent import CouncilMemberResponse
from engine.payroll import run_payroll


def _employee(name: str, wage: float = 10.0, savings: float = 0.0) -> Employee:
    return Employee(
        name=name, wage=wage, expected_wage=10.0, value_alignment=0.5,
        retaliation_cost=0.1, alternative_attractiveness=0.3, savings=savings,
    )


def _company(employees: list[Employee], capital: float = 100.0, name: str = "Org") -> Company:
    return Company(
        name=name, archetype=CompanyArchetype.DOOMSAYER,
        resources=Resources(capital=capital, tech=5.0, legitimacy=0.5),
        employees=employees, decision_mode="llm",
    )


def _outcome(company: Company, results: dict[str, dict]) -> CouncilOutcome:
    return CouncilOutcome(
        proceeds=True, disclosed=False, votes_for=len(company.employees),
        votes_total=len(company.employees),
        member_results=[
            MemberResult(
                name=e.name, support=True, disclosed=False, reasoning="", source="llm",
                **results.get(e.name, {"personal_action": "stay"}),
            )
            for e in company.employees
        ],
    )


def test_everyone_staying_changes_nothing():
    company = _company([_employee("e1"), _employee("e2")])
    events, orgs, individuals = apply_member_exits(company, _outcome(company, {}), [company])
    assert events == [] and orgs == [] and individuals == []
    assert len(company.employees) == 2


def test_leaving_takes_only_their_own_savings_not_the_company_till():
    company = _company([_employee("e1", savings=25.0), _employee("e2")])
    events, orgs, individuals = apply_member_exits(
        company, _outcome(company, {"e1": {"personal_action": "leave"}}), [company]
    )

    assert [e.name for e in company.employees] == ["e2"]
    assert company.resources.capital == 100.0  # the org's books are untouched
    assert events[0].savings_at_exit == 25.0
    assert individuals[0].archetype is IndividualArchetype.UNAFFILIATED
    assert individuals[0].resources.capital == 25.0
    assert orgs == []


def test_a_broke_member_may_still_found_an_org_the_engine_never_refuses():
    company = _company([_employee("e1", savings=0.0)])
    events, orgs, _ = apply_member_exits(
        company, _outcome(company, {"e1": {"personal_action": "found_new_org"}}), [company]
    )

    assert events[0].blocked_reason is None
    assert len(orgs) == 1
    assert orgs[0].resources.capital == 0.0  # founded on nothing; the world decides how that goes
    assert company.employees == []


def test_the_member_decides_how_much_of_their_savings_to_stake():
    company = _company([_employee("e1", savings=50.0)])
    _, orgs, _ = apply_member_exits(
        company,
        _outcome(company, {"e1": {"personal_action": "found_new_org", "personal_stake": 20.0}}),
        [company],
    )

    assert orgs[0].resources.capital == 20.0
    assert orgs[0].employees[0].savings == 30.0  # they kept the rest


def test_stake_above_what_they_have_is_capped_at_their_balance():
    company = _company([_employee("e1", savings=10.0)])
    _, orgs, _ = apply_member_exits(
        company,
        _outcome(company, {"e1": {"personal_action": "found_new_org", "personal_stake": 999.0}}),
        [company],
    )
    assert orgs[0].resources.capital == 10.0
    assert orgs[0].employees[0].savings == 0.0


def test_founder_carries_their_memory_into_the_new_org():
    founder = _employee("e1", savings=30.0)
    founder.memory.append("3분기차 회의: 당신은 반대")
    company = _company([founder, _employee("e2")])

    _, orgs, _ = apply_member_exits(
        company, _outcome(company, {"e1": {"personal_action": "found_new_org"}}), [company]
    )

    assert orgs[0].spawned_from == "Org"
    assert orgs[0].decision_mode == "llm"
    assert orgs[0].employees[0].memory == ["3분기차 회의: 당신은 반대"]


def test_joining_another_org_moves_the_person_and_their_savings():
    other = _company([_employee("x1", wage=14.0)], name="Other")
    mover = _employee("e1", wage=8.0, savings=12.0)
    company = _company([mover, _employee("e2")])

    events, orgs, individuals = apply_member_exits(
        company,
        _outcome(company, {"e1": {"personal_action": "join_other_org", "personal_target": "Other"}}),
        [company, other],
    )

    assert [e.name for e in company.employees] == ["e2"]
    assert [e.name for e in other.employees] == ["x1", "e1"]
    assert other.employees[1].savings == 12.0
    assert other.employees[1].wage == 8.0  # the engine invents no new terms for them
    assert events[0].became == "Other"
    assert orgs == [] and individuals == []


def test_joining_a_nonexistent_org_is_recorded_and_they_stay_put():
    company = _company([_employee("e1")])
    events, _, _ = apply_member_exits(
        company,
        _outcome(company, {"e1": {"personal_action": "join_other_org", "personal_target": "없는회사"}}),
        [company],
    )
    assert events[0].blocked_reason is not None
    assert [e.name for e in company.employees] == ["e1"]


def test_retiring_removes_the_member_without_creating_anything():
    company = _company([_employee("e1"), _employee("e2")])
    events, orgs, individuals = apply_member_exits(
        company, _outcome(company, {"e1": {"personal_action": "retire"}}), [company]
    )

    assert [e.name for e in company.employees] == ["e2"]
    assert orgs == [] and individuals == []
    assert events[0].action == "retire" and events[0].became is None


def test_an_emptied_council_still_tallies_without_crashing():
    outcome = tally_votes([], [], SimulationConfig(), random.Random(0))
    assert outcome.votes_total == 0
    assert outcome.proceeds is False


def test_a_failed_llm_call_never_makes_someone_quit():
    employees = [_employee("e1"), _employee("e2")]
    outcome = tally_votes([None, None], employees, SimulationConfig(), random.Random(0))
    assert all(r.personal_action == "stay" for r in outcome.member_results)


def test_personal_fields_default_to_staying_put():
    response = CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="")
    assert response.personal_action == "stay"
    assert response.personal_target is None and response.personal_stake is None


def test_payroll_moves_wages_from_the_company_into_personal_savings():
    config = SimulationConfig(living_cost=6.0)
    rich = _employee("rich", wage=14.0)
    poor = _employee("poor", wage=5.0)
    company = _company([rich, poor], capital=100.0)

    events = run_payroll([company], config)

    assert company.resources.capital == 81.0
    assert rich.savings == 8.0    # earns more than it costs to live
    assert poor.savings == -1.0   # same council, structurally in the red
    assert events[0].unpaid_members == []


def test_a_drained_company_cannot_make_payroll_and_it_shows_on_the_person():
    config = SimulationConfig(living_cost=6.0)
    employee = _employee("e1", wage=10.0)
    company = _company([employee], capital=4.0)

    events = run_payroll([company], config)

    assert company.resources.capital == 0.0
    assert employee.last_wage_paid == 4.0
    assert employee.unpaid_streak == 1
    assert employee.savings == -2.0
    assert events[0].unpaid_members == ["e1"]


def test_an_org_everyone_left_stays_dead_even_with_money_in_the_bank():
    from engine.bankruptcy import apply_state

    company = _company([], capital=108.0)
    company.alive = False  # emptied by apply_member_exits
    apply_state(company, SimulationConfig())
    assert company.alive is False  # capital must not resurrect it
