from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .config import SimulationConfig
from .entities import (
    Company,
    CompanyArchetype,
    IndividualAgent,
    IndividualArchetype,
    Resources,
    Vigilante,
    VigilanteFaction,
)
from .formulas import individual_leak_chance

if TYPE_CHECKING:
    from .interactions import VigilanteInterventionEvent


def _noise(rng: random.Random, scale: float) -> float:
    return rng.uniform(-scale, scale)


def _ordinary_income(company: Company, config: SimulationConfig, rng: random.Random) -> None:
    """Baseline market income shared by every archetype except the two whose
    doc entries explicitly say they don't sell into the ordinary market
    (truth-seeker's sponsorship, safety-coordinator's donations).

    The headcount term is what makes payroll survivable: people produce before
    they are paid, so an org that loses members loses revenue with them."""
    earned = config.base_income + config.revenue_per_employee * len(company.employees)
    company.resources.capital = max(0.0, company.resources.capital + earned + _noise(rng, 1.0))


def _heuristic_pure_efficiency(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    spend = min(r.capital, config.base_income)
    # diminishing returns as tech grows -> approximates a thermodynamic ceiling
    gain = config.efficiency_tech_conversion_rate * spend / (1 + r.tech * config.efficiency_diminishing_returns_k)
    r.capital -= spend
    r.tech += gain
    return None


def _heuristic_generic_profit_seeking(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    """Used by archetypes whose distinguishing behavior lives entirely in the
    structural traits already wired into formulas.py (emotionless -> lambda=0
    trades, hive-mind -> desertion immunity / no legitimacy buffer), not in a
    unique resource-allocation goal."""
    _ordinary_income(company, config, rng)
    r = company.resources
    r.tech = max(0.0, r.tech + config.base_income * 0.2 + _noise(rng, 0.3))
    return None


def _heuristic_growth(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    reinvest = r.capital * 0.3
    r.capital -= reinvest
    r.tech += reinvest * 0.5
    r.coercion = max(0.0, r.coercion + reinvest * 0.05)
    return None


def _heuristic_innovation(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    r.tech = max(0.0, r.tech + config.base_income * 0.2)
    if rng.random() < config.innovation_event_probability:
        r.tech += config.innovation_tech_bonus  # novelty breakthrough; a fast-follower target
    return None


def _heuristic_techno_solutionism(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    # "throw tech at every problem": whenever legitimacy or coercion look thin,
    # convert capital into tech first rather than addressing them directly.
    if r.legitimacy < 0.5 or r.coercion < 0.2:
        spend = min(r.capital, config.base_income * 1.5)
        r.capital -= spend
        r.tech += spend * 0.6
    return None


def _heuristic_doomsayer(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    if company.decision_mode == "llm":
        # Phase 3.6: the weapons-directed reinvestment below is no longer
        # automatic for an LLM-run council -- whether it happens at all is now
        # decided by a per-tick vote in simulation.py's WMD section, using this
        # exact same formula only when the council actually votes to invest.
        return None
    r = company.resources
    reinvest = r.capital * 0.4
    r.capital -= reinvest
    r.tech += reinvest * 0.4
    r.coercion += reinvest * 0.3
    # WMD attempt trigger (threshold check) lives in simulation.py's tick(),
    # so its WmdAttemptEvent can be collected into the Tick record.
    return None


def _heuristic_safety_coordinator(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    r = company.resources
    # doc 8: no product of its own, funded by other companies' voluntary
    # sponsorship -> chronic public-goods free-rider shortfall by construction
    # (nobody in `others` is forced to donate here). Scaled by legitimacy, so
    # this archetype lives or dies by how much it is trusted -- when its own
    # legitimacy falls it can no longer make payroll.
    donations = (
        r.legitimacy
        * config.revenue_per_employee
        * config.sponsor_revenue_multiplier
        * len(company.employees)
    )
    r.capital = max(0.0, r.capital + donations)
    return None


def _heuristic_self_replicator(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    r.tech = max(0.0, r.tech + config.base_income * 0.2)
    if r.capital >= config.self_replication_capital_threshold:
        spawn_capital = r.capital * config.self_replication_spawn_fraction
        r.capital -= spawn_capital
        child = Company(
            name=f"{company.name}-child-{rng.randint(1000, 9999)}",
            archetype=CompanyArchetype.SELF_REPLICATOR,
            resources=Resources(capital=spawn_capital, tech=r.tech * 0.5, legitimacy=r.legitimacy * 0.5),
            spawned_from=company.name,
        )
        return child
    return None


def _heuristic_truth_seeker(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    r = company.resources
    # doc 11: revenue is legitimacy-linked sponsorship, not market sales.
    r.capital = max(0.0, r.capital + r.legitimacy * config.sponsor_income_legitimacy_multiplier * 0.2)
    r.tech = max(0.0, r.tech + 0.1)
    return None


def _heuristic_conglomerate(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    _ordinary_income(company, config, rng)
    r = company.resources
    share = r.capital * 0.15
    r.capital -= 2 * share
    r.tech += share
    r.coercion = max(0.0, r.coercion + share * 0.3)
    return None


def _heuristic_fast_follower(company: Company, others: list[Company], config: SimulationConfig, rng: random.Random) -> Company | None:
    from .interactions import attempt_imitation

    _ordinary_income(company, config, rng)
    leader = max((o for o in others if o.name != company.name), key=lambda o: o.resources.tech, default=None)
    if leader is not None and leader.resources.tech > company.resources.tech:
        attempt_imitation(company, leader, config)
    return None


_COMPANY_HEURISTICS = {
    CompanyArchetype.PURE_EFFICIENCY: _heuristic_pure_efficiency,
    CompanyArchetype.EMOTIONLESS: _heuristic_generic_profit_seeking,
    CompanyArchetype.HIVE_MIND: _heuristic_generic_profit_seeking,
    CompanyArchetype.GROWTH: _heuristic_growth,
    CompanyArchetype.INNOVATION: _heuristic_innovation,
    CompanyArchetype.TECHNO_SOLUTIONISM: _heuristic_techno_solutionism,
    CompanyArchetype.DOOMSAYER: _heuristic_doomsayer,
    CompanyArchetype.SAFETY_COORDINATOR: _heuristic_safety_coordinator,
    CompanyArchetype.SELF_REPLICATOR: _heuristic_self_replicator,
    CompanyArchetype.TRUTH_SEEKER: _heuristic_truth_seeker,
    CompanyArchetype.CONGLOMERATE: _heuristic_conglomerate,
    CompanyArchetype.FAST_FOLLOWER: _heuristic_fast_follower,
}


def apply_company_heuristic(
    company: Company, all_companies: list[Company], config: SimulationConfig, rng: random.Random
) -> Company | None:
    fn = _COMPANY_HEURISTICS[company.archetype]
    spawned = fn(company, all_companies, config, rng)
    if company.is_industry_pmc:
        # #9 is a modifier, not a branch: extra coercion generation on top of
        # whatever the base archetype already did.
        company.resources.coercion = max(0.0, company.resources.coercion + config.base_income * 0.1)
    return spawned


def _heuristic_challenger(agent: IndividualAgent, companies: list[Company], config: SimulationConfig, rng: random.Random) -> None:
    r = agent.resources
    r.capital = max(0.0, r.capital + config.base_income * 0.3 + _noise(rng, 0.5))
    target = max(companies, key=lambda c: c.resources.capital, default=None)
    if target is not None and r.capital > 5.0:
        r.capital -= 5.0
        target.resources.legitimacy = max(0.0, target.resources.legitimacy - 0.02)


def _heuristic_mad_scientist(agent: IndividualAgent, companies: list[Company], config: SimulationConfig, rng: random.Random) -> None:
    r = agent.resources
    r.capital = max(0.0, r.capital + config.base_income * 0.2)
    if rng.random() < 0.3:
        r.tech = max(0.0, r.tech + _noise(rng, 3.0))  # high-variance gamble, can also fail (negative noise clipped at 0 by max)


def _heuristic_serial_failure(agent: IndividualAgent, companies: list[Company], config: SimulationConfig, rng: random.Random) -> None:
    r = agent.resources
    r.capital = max(0.0, r.capital + config.base_income * 0.2)
    if rng.random() < 0.7:  # tries often
        if rng.random() < 0.8:  # and fails often
            r.capital = max(0.0, r.capital - 1.0)
        else:
            r.tech += 0.5  # small persistent gain on the rare success


def _heuristic_unaffiliated(agent: IndividualAgent, companies: list[Company], config: SimulationConfig, rng: random.Random) -> None:
    # Someone who left an org. Deliberately does nothing to anyone: assigning
    # them a goal here would be the engine deciding what leaving "means".
    r = agent.resources
    r.capital = max(0.0, r.capital + config.base_income * 0.2 + _noise(rng, 0.3))


_INDIVIDUAL_HEURISTICS = {
    IndividualArchetype.CHALLENGER: _heuristic_challenger,
    IndividualArchetype.MAD_SCIENTIST: _heuristic_mad_scientist,
    IndividualArchetype.SERIAL_FAILURE: _heuristic_serial_failure,
    IndividualArchetype.UNAFFILIATED: _heuristic_unaffiliated,
}


def apply_individual_heuristic(
    agent: IndividualAgent, companies: list[Company], config: SimulationConfig, rng: random.Random
) -> None:
    _INDIVIDUAL_HEURISTICS[agent.archetype](agent, companies, config, rng)


def _pick_heuristic_target(
    vigilante: Vigilante, alive: list[Company], rng: random.Random
) -> Company | None:
    """Phase 3.9: the old single "always hit the strongest" rule is now just
    one possible disposition (opportunist), not a universal law -- vigilantes
    aren't police, so each disposition gets its own pure-code stand-in for
    "what this person would do," used in heuristic mode and as the LLM
    fallback."""
    if vigilante.disposition == "opportunist":
        return max(alive, key=lambda c: c.resources.capital, default=None)
    if vigilante.disposition == "protector":
        # proxy for "harms people most": highest coercion relative to legitimacy
        return max(alive, key=lambda c: c.resources.coercion, default=None)
    if vigilante.disposition == "grudge":
        return next((c for c in alive if c.name == vigilante.grudge_target), None)
    # indifferent: acts on a whim, and often doesn't bother at all
    if rng.random() < 0.5 or not alive:
        return None
    return rng.choice(alive)


def _vigilante_enforce_heuristic(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random
) -> VigilanteInterventionEvent | None:
    """Used directly in heuristic mode, and as the fallback when an "llm"
    vigilante's decision call fails."""
    from .interactions import VigilanteInterventionEvent

    alive = [c for c in companies if c.alive]
    if vigilante.resources.capital < config.vigilante_enforcement_capital_threshold or not alive:
        return None
    target = _pick_heuristic_target(vigilante, alive, rng)
    if target is None:
        return None
    vigilante.resources.capital -= config.vigilante_enforcement_capital_threshold
    target.resources.legitimacy = max(
        0.0, target.resources.legitimacy - config.vigilante_enforcement_legitimacy_penalty
    )
    return VigilanteInterventionEvent(
        vigilante=vigilante.name, intervened=True, target=target.name, intensity=1.0,
        reasoning=f"heuristic: {vigilante.disposition} disposition rule",
    )


def _vigilante_enforce_llm(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    from .llm_agent import VigilanteDecision, build_vigilante_prompt, call_llm_decision
    from .interactions import VigilanteInterventionEvent
    from .personas import DISPLAY_NAME
    from .council import record_vigilante_memory

    if vigilante.resources.capital < config.vigilante_enforcement_capital_threshold:
        return None
    alive = [c for c in companies if c.alive]
    decision = call_llm_decision(
        build_vigilante_prompt(vigilante, alive, config, news), VigilanteDecision, config,
        temperature=vigilante.temperature, label=f"vigilante:{vigilante.name}",
    )
    if decision is None:
        event = _vigilante_enforce_heuristic(vigilante, companies, config, rng)
        if event is not None:
            event.reasoning = "LLM 응답 실패 -> 휴리스틱 폴백: " + event.reasoning
        return event
    if not decision.intervene or decision.target_company is None:
        # Still return an event on a declined intervention -- the reasoning
        # for *not* acting is exactly what this comparison is meant to surface.
        record_vigilante_memory(vigilante, intervened=False, target=None, reasoning=decision.reasoning)
        return VigilanteInterventionEvent(
            vigilante=vigilante.name, intervened=False, target=None, intensity=0.0, reasoning=decision.reasoning
        )
    target = next((c for c in alive if DISPLAY_NAME.get(c.archetype) == decision.target_company), None)
    if target is None:
        record_vigilante_memory(
            vigilante, intervened=False, target=None,
            reasoning=f"존재하지 않는 대상을 지목해 개입 취소: {decision.reasoning}",
        )
        return VigilanteInterventionEvent(
            vigilante=vigilante.name, intervened=False, target=None, intensity=0.0,
            reasoning=f"LLM이 존재하지 않는 대상을 지목함({decision.target_company}) -> 개입 취소: {decision.reasoning}",
        )
    vigilante.resources.capital -= config.vigilante_enforcement_capital_threshold
    target.resources.legitimacy = max(
        0.0, target.resources.legitimacy - config.vigilante_enforcement_legitimacy_penalty * decision.intensity
    )
    record_vigilante_memory(vigilante, intervened=True, target=target.name, reasoning=decision.reasoning)
    return VigilanteInterventionEvent(
        vigilante=vigilante.name, intervened=True, target=target.name, intensity=decision.intensity,
        reasoning=decision.reasoning,
    )


def _vigilante_enforce(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    if vigilante.decision_mode == "llm":
        return _vigilante_enforce_llm(vigilante, companies, config, rng, news)
    return _vigilante_enforce_heuristic(vigilante, companies, config, rng)


def _heuristic_idealist(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    # doc 3: accepts no corporate funding -> chronic scarcity by construction
    vigilante.resources.capital = max(0.0, vigilante.resources.capital + config.base_income * 0.05)
    return _vigilante_enforce(vigilante, companies, config, rng, news)


def _heuristic_realist(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    sponsors = [c for c in companies if c.archetype is not CompanyArchetype.DOOMSAYER]
    income = sum(c.resources.legitimacy for c in sponsors) * 0.05
    vigilante.resources.capital = max(0.0, vigilante.resources.capital + income)
    return _vigilante_enforce(vigilante, companies, config, rng, news)


def _heuristic_balancer(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    vigilante.resources.capital = max(0.0, vigilante.resources.capital + config.base_income * 0.1)
    return _vigilante_enforce(vigilante, companies, config, rng, news)


_VIGILANTE_HEURISTICS = {
    VigilanteFaction.IDEALIST: _heuristic_idealist,
    VigilanteFaction.REALIST: _heuristic_realist,
    VigilanteFaction.BALANCER: _heuristic_balancer,
}


def apply_vigilante_heuristic(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, rng: random.Random,
    news: list[str] | None = None,
) -> VigilanteInterventionEvent | None:
    return _VIGILANTE_HEURISTICS[vigilante.faction](vigilante, companies, config, rng, news)


def employee_leak_probability(company: Company, config: SimulationConfig) -> float:
    """Doc 8: WMD threat level = tech ceiling x internal loyalty distribution.
    Each low-alignment employee independently risks leaking the attempt."""
    if not company.employees:
        return 0.0
    no_leak = 1.0
    for e in company.employees:
        no_leak *= (1 - individual_leak_chance(e, config))
    return 1 - no_leak
