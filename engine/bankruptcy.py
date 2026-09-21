from __future__ import annotations

from enum import Enum, auto

from .config import SimulationConfig
from .entities import Company
from .formulas import will_desert


class CompanyState(Enum):
    ALIVE = auto()
    ISOLATED = auto()  # doc 10: legitimacy == 0 -> no one trades, functionally inert
    DEAD = auto()       # doc 10: mass desertion, or capital-out with no legitimacy to lean on


def _desertion_fraction_at_zero_wage(company: Company, config: SimulationConfig) -> float:
    """Doc 10: when capital hits 0, wages effectively drop to 0 and each
    employee's alignment is re-evaluated. A high-legitimacy org can still hold
    people via the value-alignment term even with no pay."""
    if not company.employees:
        return 0.0
    original_wages = [e.wage for e in company.employees]
    try:
        for e in company.employees:
            e.wage = 0.0
        deserting = sum(1 for e in company.employees if will_desert(e, company, config))
    finally:
        for e, wage in zip(company.employees, original_wages):
            e.wage = wage
    return deserting / len(company.employees)


def check_company_state(company: Company, config: SimulationConfig) -> CompanyState:
    if not company.employees:
        current_fraction = 0.0
    else:
        current_fraction = sum(
            1 for e in company.employees if will_desert(e, company, config)
        ) / len(company.employees)

    if current_fraction >= config.mass_desertion_fraction:
        return CompanyState.DEAD

    if company.resources.capital <= config.capital_bankruptcy_threshold:
        if _desertion_fraction_at_zero_wage(company, config) >= config.mass_desertion_fraction:
            return CompanyState.DEAD
        # legitimacy-backed loyalty holds the org together despite zero capital

    if company.resources.legitimacy <= config.legitimacy_isolation_threshold:
        return CompanyState.ISOLATED

    return CompanyState.ALIVE


def apply_state(company: Company, config: SimulationConfig) -> CompanyState:
    state = check_company_state(company, config)
    # Death is one-way. This check only reads resources, so without this an org
    # that everyone walked out of (engine/exits.py marks it dead) came back to
    # life every tick on the strength of the capital its departed staff left in
    # the account -- and went on holding meetings with nobody in the room.
    if state is CompanyState.DEAD:
        company.alive = False
    company.isolated = company.alive and state is CompanyState.ISOLATED
    return state
