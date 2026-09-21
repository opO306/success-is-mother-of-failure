from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import SimulationConfig
from .entities import Company


@dataclass
class PayrollEvent:
    company: str
    owed: float
    paid: float
    unpaid_members: list[str]


def run_payroll(
    companies: list[Company], config: SimulationConfig, bank: Any = None, tick: int = 0
) -> list[PayrollEvent]:
    """Pure layer-0 bookkeeping: wages actually leave the company's capital and
    actually land in a person's savings, minus their living cost.

    This is what connects an org's decisions to its members' wallets. A council
    that votes every quarter to pour 40% of capital into weapons is voting to
    drain its own payroll, and nobody has to be told that -- it shows up as a
    smaller number in their own ledger a few ticks later."""
    events: list[PayrollEvent] = []
    for company in companies:
        if not company.alive or not company.employees:
            continue
        owed = sum(e.wage for e in company.employees)
        if owed <= 0:
            continue
        available = max(0.0, company.resources.capital)
        ratio = 1.0 if available >= owed else (available / owed if owed else 0.0)
        paid_total = 0.0
        unpaid: list[str] = []

        for employee in company.employees:
            paid = employee.wage * ratio
            paid_total += paid
            employee.last_wage_paid = paid
            if paid < employee.wage - 1e-9:
                employee.unpaid_streak += 1
                unpaid.append(employee.name)
            else:
                employee.unpaid_streak = 0
            if employee.bound_to and tick < employee.bound_until:
                # they pledged their freedom and defaulted: the wage is earned but
                # it isn't theirs, and they still have to live
                if bank is not None:
                    bank.capital += paid
                employee.savings -= config.living_cost
                continue
            # savings can go negative: debt is a real position, and a member in the
            # red has a materially different stake in the org than one who isn't
            employee.savings += paid - config.living_cost

        company.resources.capital = max(0.0, company.resources.capital - paid_total)
        events.append(
            PayrollEvent(company=company.name, owed=owed, paid=paid_total, unpaid_members=unpaid)
        )
    return events
