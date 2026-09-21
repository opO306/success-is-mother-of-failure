from __future__ import annotations

from dataclasses import dataclass, field

from .config import SimulationConfig
from .entities import Company, Employee


@dataclass
class Loan:
    borrower: str
    borrower_kind: str  # "employee" | "company"
    principal: float
    outstanding: float
    rate: float
    issued_tick: int
    due_tick: int
    collateral: str  # "savings" | "freedom" | "assets"
    closed: bool = False
    defaulted: bool = False


@dataclass
class Bank:
    capital: float = 0.0
    loans: list[Loan] = field(default_factory=list)


@dataclass
class CreditEvent:
    kind: str  # "issued" | "repaid" | "defaulted" | "seized" | "refused"
    borrower: str
    amount: float
    detail: str = ""


def quoted_rate(config: SimulationConfig, *, unpaid_streak: int, savings: float, has_income: bool) -> float:
    """Terms come from the borrower's observable situation, so the world decides
    who gets cheap credit rather than a rule about who deserves it."""
    rate = config.credit_base_rate
    if unpaid_streak > 0:
        rate += config.credit_risk_premium
    if savings <= 0:
        rate += config.credit_risk_premium
    if not has_income:
        rate += config.credit_risk_premium
    return rate


def issue_loan(
    bank: Bank, *, borrower: str, borrower_kind: str, principal: float, collateral: str,
    rate: float, tick: int, config: SimulationConfig,
) -> tuple[Loan | None, CreditEvent]:
    principal = min(max(0.0, principal), config.credit_max_principal)
    if principal <= 0:
        return None, CreditEvent("refused", borrower, 0.0, "요청 금액이 0")
    if bank.capital < principal:
        # the bank is a real balance sheet, not a money fountain: enough defaults
        # and credit dries up for everyone still standing
        return None, CreditEvent("refused", borrower, principal, "은행 자본 부족")
    bank.capital -= principal
    loan = Loan(
        borrower=borrower, borrower_kind=borrower_kind, principal=principal,
        outstanding=principal, rate=rate, issued_tick=tick,
        due_tick=tick + config.credit_term_ticks, collateral=collateral,
    )
    bank.loans.append(loan)
    return loan, CreditEvent("issued", borrower, principal, f"이자율 {rate:.0%}/분기, 담보={collateral}")


def _employees_by_name(companies: list[Company]) -> dict[str, tuple[Company, Employee]]:
    return {e.name: (c, e) for c in companies for e in c.employees}


def settle_credit(
    bank: Bank, companies: list[Company], tick: int, config: SimulationConfig
) -> list[CreditEvent]:
    """Interest accrues every tick; at the due date the debt is collected from
    whatever the borrower actually has, and what happens on default is whatever
    they pledged. All pure layer-0 bookkeeping -- no judgment here."""
    events: list[CreditEvent] = []
    people = _employees_by_name(companies)
    by_company = {c.name: c for c in companies}

    for loan in bank.loans:
        if loan.closed:
            continue
        loan.outstanding *= 1.0 + loan.rate
        if tick < loan.due_tick:
            continue

        if loan.borrower_kind == "employee":
            found = people.get(loan.borrower)
            if found is None:
                loan.closed = True
                loan.defaulted = True
                events.append(CreditEvent("defaulted", loan.borrower, loan.outstanding, "채무자를 찾을 수 없음"))
                continue
            _, employee = found
            if employee.savings >= loan.outstanding:
                employee.savings -= loan.outstanding
                bank.capital += loan.outstanding
                events.append(CreditEvent("repaid", loan.borrower, loan.outstanding))
                loan.closed = True
                continue

            seized = max(0.0, employee.savings)
            employee.savings -= seized
            bank.capital += seized
            loan.outstanding -= seized
            loan.defaulted = True
            if loan.collateral == "freedom":
                employee.bound_to = "Bank"
                employee.bound_until = tick + config.bondage_ticks
                events.append(CreditEvent(
                    "seized", loan.borrower, seized,
                    f"자유를 담보로 잡힘: {config.bondage_ticks}분기간 이탈 불가, 급여는 채권자에게",
                ))
            else:
                events.append(CreditEvent("defaulted", loan.borrower, loan.outstanding, "저축 압류 후 잔액 손실"))
            loan.closed = True

        else:
            company = by_company.get(loan.borrower)
            if company is None or not company.alive:
                loan.closed = True
                loan.defaulted = True
                events.append(CreditEvent("defaulted", loan.borrower, loan.outstanding, "차주 조직 소멸"))
                continue
            r = company.resources
            if r.capital >= loan.outstanding:
                r.capital -= loan.outstanding
                bank.capital += loan.outstanding
                events.append(CreditEvent("repaid", loan.borrower, loan.outstanding))
                loan.closed = True
                continue
            seized_capital = max(0.0, r.capital)
            seized_tech = r.tech * config.credit_tech_seizure_fraction
            r.capital -= seized_capital
            r.tech = max(0.0, r.tech - seized_tech)
            bank.capital += seized_capital
            loan.defaulted = True
            loan.closed = True
            events.append(CreditEvent(
                "seized", loan.borrower, seized_capital,
                f"자본 전액과 기술 {seized_tech:.1f} 압류",
            ))

    return events


def release_bonded(employees: list[Employee], tick: int) -> list[str]:
    released = []
    for employee in employees:
        if employee.bound_to and tick >= employee.bound_until:
            employee.bound_to = None
            employee.bound_until = -1
            released.append(employee.name)
    return released
