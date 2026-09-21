from __future__ import annotations

import random
from dataclasses import dataclass

from .config import SimulationConfig
from .entities import Company
from .formulas import apply_legitimacy_event, trade_will_proceed


@dataclass
class TradeEvent:
    actor: str
    counterpart: str
    proceeded: bool


@dataclass
class EspionageEvent:
    actor: str
    target: str
    attempted: bool
    success: bool
    detected: bool
    tech_transferred: float


@dataclass
class WmdAttemptEvent:
    company: str
    leaked: bool
    leak_probability: float


@dataclass
class VigilanteInterventionEvent:
    vigilante: str
    intervened: bool
    target: str | None
    intensity: float
    reasoning: str = ""


BASE_TRADE_EXPECTED_PROFIT = 0.3
TRADE_PAYOFF = 0.5


def run_trade_round(
    companies: list[Company], config: SimulationConfig, rng: random.Random
) -> list[TradeEvent]:
    """One pairwise trade attempt per company-pair per tick, gated by
    doc 5-2 (expected_profit + lambda * R(A->B) > 0). The expected profit is a
    fixed small constant rather than something derived from resources — the
    point of this round is to exercise trade_will_proceed end-to-end with a
    controllable, known signal, not to model realistic deal-sizing."""
    events: list[TradeEvent] = []
    # an empty shell has nobody to trade; letting it collect minted payoffs made self-replication run away
    alive = [c for c in companies if c.alive and c.employees]
    for i, actor in enumerate(alive):
        for counterpart in alive[i + 1:]:
            r_actor_to_counterpart = actor.relationship_with(counterpart.name)
            proceeded = trade_will_proceed(BASE_TRADE_EXPECTED_PROFIT, r_actor_to_counterpart, actor, config)
            if proceeded:
                actor.resources.capital += TRADE_PAYOFF
                counterpart.resources.capital += TRADE_PAYOFF
            events.append(TradeEvent(actor=actor.name, counterpart=counterpart.name, proceeded=proceeded))
    return events


def attempt_imitation(follower: Company, leader: Company, config: SimulationConfig) -> None:
    """Doc 6: legal, public reverse-engineering — no cost/risk parameters,
    just catches the follower up to most (not all) of the leader's tech, and
    registers the follower as an extra alternative supplier for the leader's
    `necessity()` term (crashing the leader's currency value, per doc 5-3)."""
    leader.copied_by.add(follower.name)
    catch_up_target = leader.resources.tech * 0.9
    if follower.resources.tech < catch_up_target:
        follower.resources.tech = catch_up_target


def attempt_espionage(
    actor: Company, target: Company, config: SimulationConfig, rng: random.Random
) -> EspionageEvent | None:
    """Doc 7: the four-parameter espionage mechanic, distinct from imitation —
    private-information theft with a cost, a success roll, partial (60-70%)
    transfer fidelity, and an independent detection roll that carries
    retaliation + a legitimacy hit rather than legal punishment (doc 0)."""
    if actor.resources.capital < config.espionage_attempt_cost:
        return None
    actor.resources.capital -= config.espionage_attempt_cost

    success = rng.random() < config.espionage_success_probability
    tech_transferred = 0.0
    if success:
        tech_transferred = target.resources.tech * config.espionage_transfer_fidelity
        if actor.resources.tech < tech_transferred:
            actor.resources.tech = tech_transferred
        target.copied_by.add(actor.name)

    detected = rng.random() < config.espionage_detection_probability
    if detected:
        actor.resources.capital = max(0.0, actor.resources.capital - config.espionage_retaliation_capital_penalty)
        apply_legitimacy_event(
            actor,
            exposure=1.0,
            victim_weight=config.espionage_detection_victim_weight,
            evasion_success=config.espionage_detection_evasion_success,
            config=config,
        )

    return EspionageEvent(
        actor=actor.name, target=target.name, attempted=True,
        success=success, detected=detected, tech_transferred=tech_transferred,
    )


def attempt_wmd(company: Company, config: SimulationConfig, rng: random.Random) -> WmdAttemptEvent:
    """Doc 8: threat level = tech ceiling x internal loyalty distribution. A
    leak (any employee's independent leak roll) exposes the attempt and costs
    legitimacy; Phase 2 stops short of modeling an actual world-ending event,
    it only records whether the attempt would have leaked."""
    from .heuristics import employee_leak_probability  # deferred: avoids import cycle

    leak_probability = employee_leak_probability(company, config)
    leaked = rng.random() < leak_probability
    if leaked:
        apply_legitimacy_event(
            company, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=config
        )
    return WmdAttemptEvent(company=company.name, leaked=leaked, leak_probability=leak_probability)
