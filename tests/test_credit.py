import pytest

from engine.config import SimulationConfig
from engine.council import CouncilOutcome, MemberResult
from engine.credit import Bank, issue_loan, quoted_rate, release_bonded, settle_credit
from engine.entities import Company, CompanyArchetype, Employee, Resources
from engine.exits import apply_member_exits
from engine.payroll import run_payroll


def _employee(name="e1", wage=10.0, savings=0.0, unpaid=0):
    return Employee(
        name=name, wage=wage, expected_wage=10.0, value_alignment=0.5,
        retaliation_cost=0.1, alternative_attractiveness=0.3, savings=savings,
        unpaid_streak=unpaid,
    )


def _company(employees, capital=100.0, name="Org"):
    return Company(
        name=name, archetype=CompanyArchetype.DOOMSAYER,
        resources=Resources(capital=capital, tech=10.0, legitimacy=0.5),
        employees=employees, decision_mode="llm",
    )


def test_a_struggling_borrower_is_quoted_a_worse_rate():
    config = SimulationConfig()
    safe = quoted_rate(config, unpaid_streak=0, savings=50.0, has_income=True)
    risky = quoted_rate(config, unpaid_streak=3, savings=-10.0, has_income=False)
    assert risky > safe
    assert safe == config.credit_base_rate


def test_the_bank_is_a_real_balance_sheet_not_a_money_fountain():
    config = SimulationConfig()
    bank = Bank(capital=30.0)
    loan, event = issue_loan(
        bank, borrower="e1", borrower_kind="employee", principal=100.0,
        collateral="savings", rate=0.1, tick=0, config=config,
    )
    assert loan is None and event.kind == "refused"
    assert bank.capital == 30.0


def test_borrowing_moves_capital_out_of_the_bank():
    config = SimulationConfig()
    bank = Bank(capital=200.0)
    loan, event = issue_loan(
        bank, borrower="e1", borrower_kind="employee", principal=50.0,
        collateral="freedom", rate=0.1, tick=2, config=config,
    )
    assert event.kind == "issued"
    assert bank.capital == 150.0
    assert loan.due_tick == 2 + config.credit_term_ticks
    assert loan.outstanding == 50.0


def test_a_solvent_borrower_repays_with_interest():
    config = SimulationConfig(credit_term_ticks=1)
    bank = Bank(capital=200.0)
    employee = _employee(savings=0.0)
    company = _company([employee])
    loan, _ = issue_loan(
        bank, borrower="e1", borrower_kind="employee", principal=50.0,
        collateral="savings", rate=0.10, tick=0, config=config,
    )
    employee.savings = 100.0

    events = settle_credit(bank, [company], tick=1, config=config)

    assert [e.kind for e in events] == ["repaid"]
    assert employee.savings == pytest.approx(45.0)  # 100 - 55 owed
    assert bank.capital == pytest.approx(205.0)     # 150 left after lending, plus 55 back
    assert loan.closed


def test_defaulting_on_a_freedom_pledge_binds_the_person():
    config = SimulationConfig(credit_term_ticks=1, bondage_ticks=6)
    bank = Bank(capital=200.0)
    employee = _employee(savings=0.0)
    company = _company([employee])
    issue_loan(
        bank, borrower="e1", borrower_kind="employee", principal=50.0,
        collateral="freedom", rate=0.10, tick=0, config=config,
    )

    events = settle_credit(bank, [company], tick=1, config=config)

    assert [e.kind for e in events] == ["seized"]
    assert employee.bound_to == "Bank"
    assert employee.bound_until == 1 + 6


def test_a_bound_person_cannot_take_the_exit_they_chose():
    employee = _employee(savings=40.0)
    employee.bound_to = "Bank"
    employee.bound_until = 9
    company = _company([employee, _employee("e2")])
    outcome = CouncilOutcome(
        proceeds=True, disclosed=False, votes_for=2, votes_total=2,
        member_results=[
            MemberResult(name="e1", support=True, disclosed=False, reasoning="", source="llm",
                         personal_action="leave"),
            MemberResult(name="e2", support=True, disclosed=False, reasoning="", source="llm"),
        ],
    )

    events, orgs, individuals = apply_member_exits(company, outcome, [company])

    assert events[0].blocked_reason is not None
    assert "채무" in events[0].blocked_reason
    assert [e.name for e in company.employees] == ["e1", "e2"]  # still there
    assert orgs == [] and individuals == []


def test_a_bound_persons_wages_go_to_the_creditor_and_they_still_pay_to_live():
    config = SimulationConfig(living_cost=6.0)
    bank = Bank(capital=0.0)
    employee = _employee(wage=10.0, savings=20.0)
    employee.bound_to = "Bank"
    employee.bound_until = 5
    company = _company([employee], capital=100.0)

    run_payroll([company], config, bank=bank, tick=1)

    assert bank.capital == 10.0    # the wage was earned but is not theirs
    assert employee.savings == 14.0  # they still have to live
    assert company.resources.capital == 90.0


def test_bondage_ends_when_the_term_is_up():
    employee = _employee()
    employee.bound_to = "Bank"
    employee.bound_until = 4
    assert release_bonded([employee], tick=3) == []
    assert employee.bound_to == "Bank"
    assert release_bonded([employee], tick=4) == ["e1"]
    assert employee.bound_to is None


def test_a_defaulting_company_has_capital_and_tech_seized():
    config = SimulationConfig(credit_term_ticks=1, credit_tech_seizure_fraction=0.5)
    bank = Bank(capital=200.0)
    company = _company([_employee()], capital=10.0)
    issue_loan(
        bank, borrower="Org", borrower_kind="company", principal=100.0,
        collateral="assets", rate=0.10, tick=0, config=config,
    )
    company.resources.capital = 10.0

    events = settle_credit(bank, [company], tick=1, config=config)

    assert [e.kind for e in events] == ["seized"]
    assert company.resources.capital == 0.0
    assert company.resources.tech == 5.0  # half seized
