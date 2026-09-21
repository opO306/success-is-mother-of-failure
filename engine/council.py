from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import SimulationConfig
from .entities import Company, Employee, Resources, Vigilante
from .formulas import alignment_score, individual_leak_chance
from .llm_agent import CouncilMemberResponse


@dataclass
class MemberResult:
    name: str
    support: bool
    disclosed: bool
    reasoning: str
    source: str  # "llm" or "fallback"
    disclose_target: str | None = None
    proposal: str = ""
    personal_action: str = "stay"
    personal_target: str | None = None
    personal_stake: float | None = None
    borrow_amount: float | None = None
    borrow_collateral: str | None = None
    personal_intent: str = ""


@dataclass
class CouncilOutcome:
    proceeds: bool
    disclosed: bool
    votes_for: int
    votes_total: int
    member_results: list[MemberResult] = field(default_factory=list)
    action_description: str = ""  # set by the caller (simulation.py) for observability
    company: str = ""  # Phase 3.9: which company this vote belongs to (2 companies now hold councils)


def tally_votes(
    responses: list[CouncilMemberResponse | None],
    employees: list[Employee],
    config: SimulationConfig,
    rng: random.Random,
) -> CouncilOutcome:
    """Pure-code aggregation (doc principle: engine = rules, judgment = LLM).
    Simple majority decides whether the org proceeds; any single member
    disclosing to outsiders exposes the whole vote, regardless of the
    majority's choice. A member whose LLM call failed after retries degrades
    to that individual's alignment-based probability rather than dropping
    their vote or failing the whole council."""
    results: list[MemberResult] = []
    for employee, response in zip(employees, responses):
        if response is not None:
            results.append(
                MemberResult(
                    name=employee.name,
                    support=response.support_action,
                    disclosed=response.disclose_to_outsiders,
                    reasoning=response.reasoning,
                    source="llm",
                    disclose_target=response.disclose_target,
                    proposal=response.proposal,
                    personal_action=response.personal_action,
                    personal_target=response.personal_target,
                    personal_stake=response.personal_stake,
                    borrow_amount=response.borrow_amount,
                    borrow_collateral=response.borrow_collateral,
                    personal_intent=response.personal_intent,
                )
            )
        else:
            support = rng.random() < alignment_score(employee, config)
            disclosed = rng.random() < individual_leak_chance(employee, config)
            results.append(
                MemberResult(
                    name=employee.name,
                    support=support,
                    disclosed=disclosed,
                    reasoning="(LLM 응답 실패 -> 정렬도 기반 확률로 대체)",
                    source="fallback",
                    # personal_action stays "stay": an unreachable LLM must never
                    # be the reason someone walks out of their org.
                )
            )

    votes_for = sum(1 for r in results if r.support)
    return CouncilOutcome(
        proceeds=votes_for > len(results) / 2,
        disclosed=any(r.disclosed for r in results),
        votes_for=votes_for,
        votes_total=len(results),
        member_results=results,
    )


def record_memory(
    employees: list[Employee],
    outcome: CouncilOutcome,
    tick_index: int,
    resources: Resources,
    action_description: str,
) -> None:
    """Appends one factual (engine-written, not LLM-written) line per member
    to their own `memory` -- what they personally voted, what the group
    decided, and the resource state at that moment. This is the substrate for
    genuine divergence over time: each member's future prompt only ever sees
    their OWN accumulated history, so if any two members' votes ever differ
    even once, their memories (and thus their future reasoning) start to
    diverge from that point on."""
    outcome_label = "가결" if outcome.proceeds else "부결"
    for employee, result in zip(employees, outcome.member_results):
        vote_label = "찬성" if result.support else "반대"
        disclose_label = ", 외부에 알림" if result.disclosed else ""
        employee.memory.append(
            f"{tick_index}분기차 회의('{action_description}'): 당신은 {vote_label}{disclose_label}. "
            f"결과는 {outcome_label}. 그때 조직 자원: 자본={resources.capital:.1f} 기술={resources.tech:.1f} "
            f"강제력={resources.coercion:.2f} 정당성={resources.legitimacy:.2f}"
        )


def collect_proposals(company: Company, outcome: CouncilOutcome) -> list[str]:
    """Carries whatever members raised on their own into the org's standing list,
    so it reaches everyone's next prompt. The engine doesn't act on these and
    doesn't judge them -- it just refuses to drop them."""
    raised = [
        f"{r.name}: {r.proposal.strip()}"
        for r in outcome.member_results
        if r.proposal and r.proposal.strip()
    ]
    company.open_proposals.extend(raised)
    del company.open_proposals[:-20]
    return raised


def record_vigilante_memory(vigilante: Vigilante, intervened: bool, target: str | None, reasoning: str) -> None:
    """No committee here (doc: independent individuals, not a chain of
    command) -- just this one person's own decision and its immediate result,
    appended to their own memory. Called only for decision_mode=="llm"
    vigilantes; the heuristic path doesn't read memory so it doesn't need one."""
    r = vigilante.resources
    if intervened:
        entry = f"당신은 {target}에 개입했다. 그 직후 당신의 자본={r.capital:.1f}"
    else:
        entry = f"당신은 개입하지 않았다. 그 이유: {reasoning[:80]}. 그때 당신의 자본={r.capital:.1f}"
    vigilante.memory.append(entry)
