from __future__ import annotations

from dataclasses import dataclass

from .council import CouncilOutcome
from .entities import (
    Company,
    IndividualAgent,
    IndividualArchetype,
    Resources,
)


@dataclass
class MemberExitEvent:
    member: str
    company: str
    action: str  # "leave" | "join_other_org" | "found_new_org" | "retire"
    intent: str
    savings_at_exit: float
    became: str | None = None
    blocked_reason: str | None = None


def apply_member_exits(
    company: Company, outcome: CouncilOutcome, all_companies: list[Company]
) -> tuple[list[MemberExitEvent], list[Company], list[IndividualAgent]]:
    """Applies what a member decided to do about their own life, after the vote
    they cast has already been tallied and remembered.

    Everything here runs off the person's OWN ledger, not the company till, and
    nothing is refused: a broke member may still found an org, and a solvent one
    decides for themselves how much of their savings to risk. The engine states
    what exists (a balance, the going rate elsewhere) and applies what they
    chose -- it never rules a choice out, and never draws the conclusion for
    them. Whatever it costs, they find out by living it, or by reading about
    someone else in the news."""
    events: list[MemberExitEvent] = []
    new_companies: list[Company] = []
    new_individuals: list[IndividualAgent] = []
    by_name = {e.name: e for e in company.employees}
    taken_names = {c.name for c in all_companies}

    def _unique(base: str) -> str:
        name, n = base, 2
        while name in taken_names:
            name, n = f"{base}-{n}", n + 1
        taken_names.add(name)
        return name

    for result in outcome.member_results:
        if result.personal_action == "stay":
            continue
        employee = by_name.get(result.name)
        if employee is None:
            continue

        if employee.bound_to:
            # the one choice the engine refuses -- because they sold it themselves
            # to get the money, and are still inside the term they signed for
            events.append(
                MemberExitEvent(
                    member=employee.name, company=company.name, action=result.personal_action,
                    intent=result.personal_intent, savings_at_exit=employee.savings,
                    blocked_reason=f"{employee.bound_to}에 대한 채무 이행 중({employee.bound_until}분기까지)",
                )
            )
            continue

        action = result.personal_action
        target: Company | None = None
        if action == "join_other_org":
            target = next(
                (c for c in all_companies if c.alive and c.name != company.name and c.name == result.personal_target),
                None,
            )
            if target is None:
                events.append(
                    MemberExitEvent(
                        member=employee.name, company=company.name, action=action,
                        intent=result.personal_intent, savings_at_exit=employee.savings,
                        blocked_reason=f"존재하지 않는 조직을 지목함({result.personal_target})",
                    )
                )
                continue
        company.employees = [e for e in company.employees if e.name != employee.name]
        savings = employee.savings
        became: str | None = None

        if action == "found_new_org":
            became = _unique(f"{employee.name}-org")
            # How much of their own money goes in is theirs to decide -- the engine
            # neither blocks a broke founder nor empties a solvent one's pockets.
            # Founding on nothing is allowed; the world, not a validation rule, is
            # what makes that a bad idea.
            stake = result.personal_stake if result.personal_stake is not None else savings
            stake = min(max(0.0, stake), max(0.0, savings))
            employee.savings = savings - stake
            new_companies.append(
                Company(
                    name=became,
                    # Inheriting the parent archetype is instrumentation, not a claim that they
                    # still want what their old org wanted: the founder carries their own memory,
                    # so their next vote on the same agenda is what actually answers that -- and
                    # it can only be observed if they keep getting asked.
                    archetype=company.archetype,
                    resources=Resources(capital=stake, tech=0.5, legitimacy=0.1),
                    employees=[employee],
                    spawned_from=company.name,
                    decision_mode=company.decision_mode,
                )
            )
        elif action == "join_other_org" and target is not None:
            became = target.name
            employee.unpaid_streak = 0
            target.employees.append(employee)
        elif action == "leave":
            became = f"{employee.name}-무소속"
            new_individuals.append(
                IndividualAgent(
                    name=became,
                    archetype=IndividualArchetype.UNAFFILIATED,
                    resources=Resources(capital=max(0.0, savings)),
                )
            )

        events.append(
            MemberExitEvent(
                member=employee.name, company=company.name, action=action,
                intent=result.personal_intent, savings_at_exit=savings, became=became,
            )
        )

    return events, new_companies, new_individuals
