from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from .bankruptcy import CompanyState
from .config import SimulationConfig
from .entities import CompanyArchetype
from .formulas import apply_legitimacy_event
from .scenarios import build_emotionless_ab_pair, build_full_world, build_hive_mind_shock_pair

DEFAULT_SEEDS = 100
DEFAULT_TICKS = 50


@dataclass
class InvariantViolation:
    seed: int
    tick: int
    detail: str


@dataclass
class InvariantBatchResult:
    seeds_run: int
    ticks_per_seed: int
    violations: list[InvariantViolation] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations and not self.exceptions


def run_invariant_batch(num_seeds: int = DEFAULT_SEEDS, ticks: int = DEFAULT_TICKS) -> InvariantBatchResult:
    result = InvariantBatchResult(seeds_run=num_seeds, ticks_per_seed=ticks)
    for seed in range(num_seeds):
        try:
            world = build_full_world(seed=seed)
            ever_dead: set[str] = set()
            for tick_record in world.run(ticks):
                for company in world.companies:
                    r = company.resources
                    if r.capital < 0 or r.tech < 0 or r.legitimacy < 0 or r.coercion < 0:
                        result.violations.append(
                            InvariantViolation(seed, tick_record.index, f"negative resource on {company.name}")
                        )
                for name, value in tick_record.currency_values.items():
                    if value < 0 or not math.isfinite(value):
                        result.violations.append(
                            InvariantViolation(seed, tick_record.index, f"bad currency value for {name}: {value}")
                        )
                for name, state in tick_record.company_states.items():
                    if name in ever_dead and state is not CompanyState.DEAD:
                        result.violations.append(
                            InvariantViolation(seed, tick_record.index, f"{name} revived after death")
                        )
                    if state is CompanyState.DEAD:
                        ever_dead.add(name)
            hive_names = {c.name for c in world.companies if c.archetype is CompanyArchetype.HIVE_MIND}
            if hive_names & ever_dead:
                result.violations.append(
                    InvariantViolation(seed, ticks, f"hive-mind company died: {hive_names & ever_dead}")
                )
        except Exception as exc:  # noqa: BLE001 - batch harness must survive per-seed failures
            result.exceptions.append(f"seed {seed}: {exc!r}")
    return result


@dataclass
class TradeRateSample:
    treatment_proceed_rate: float
    control_proceed_rate: float
    # The experiment is about the trade decision, so it is judged over ticks where the pair could trade at all.
    # Since payroll became real a one-employee counterpart can go bankrupt, which says nothing about lambda.
    treatment_proceed_rate_when_possible: float
    control_proceed_rate_when_possible: float
    seeds_with_a_death: int


def run_emotionless_ab_batch(
    num_seeds: int = DEFAULT_SEEDS, ticks: int = DEFAULT_TICKS, scripted_relationship: float = -1.0
) -> TradeRateSample:
    treatment_rates: list[float] = []
    control_rates: list[float] = []
    treatment_possible_rates: list[float] = []
    control_possible_rates: list[float] = []
    seeds_with_a_death = 0
    for seed in range(num_seeds):
        world = build_emotionless_ab_pair(seed=seed, scripted_relationship=scripted_relationship)
        proceeded = {"Treatment": 0, "Control": 0}
        possible = {"Treatment": 0, "Control": 0}
        died = False
        for tick_record in world.run(ticks):
            for trade in tick_record.trades:
                pair = {trade.actor, trade.counterpart}
                for arm in ("Treatment", "Control"):
                    if pair == {arm, "Counterpart"}:
                        possible[arm] += 1
                        proceeded[arm] += int(trade.proceeded)
            died = died or any(state is CompanyState.DEAD for state in tick_record.company_states.values())
        seeds_with_a_death += int(died)
        treatment_rates.append(proceeded["Treatment"] / ticks)
        control_rates.append(proceeded["Control"] / ticks)
        if possible["Treatment"]:
            treatment_possible_rates.append(proceeded["Treatment"] / possible["Treatment"])
        if possible["Control"]:
            control_possible_rates.append(proceeded["Control"] / possible["Control"])
    return TradeRateSample(
        treatment_proceed_rate=statistics.mean(treatment_rates),
        control_proceed_rate=statistics.mean(control_rates),
        treatment_proceed_rate_when_possible=statistics.mean(treatment_possible_rates),
        control_proceed_rate_when_possible=statistics.mean(control_possible_rates),
        seeds_with_a_death=seeds_with_a_death,
    )


@dataclass
class LegitimacyRecoverySample:
    hive_mind_pre_shock: float
    hive_mind_post_shock: float
    hive_mind_final: float
    ordinary_pre_shock: float
    ordinary_post_shock: float
    ordinary_final: float


def run_hive_mind_ab_batch(
    num_seeds: int = DEFAULT_SEEDS,
    ticks_before_shock: int = 5,
    ticks_after_shock: int = 20,
) -> LegitimacyRecoverySample:
    hive_pre, hive_post, hive_final = [], [], []
    ord_pre, ord_post, ord_final = [], [], []
    config = SimulationConfig()
    for seed in range(num_seeds):
        world = build_hive_mind_shock_pair(seed=seed)
        world.run(ticks_before_shock)
        by_name = {c.name: c for c in world.companies}
        hive, ordinary = by_name["HiveMind"], by_name["Ordinary"]
        hive_pre.append(hive.resources.legitimacy)
        ord_pre.append(ordinary.resources.legitimacy)

        # identical scripted shock to both, independent of any random events
        apply_legitimacy_event(hive, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=config)
        apply_legitimacy_event(ordinary, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=config)
        hive_post.append(hive.resources.legitimacy)
        ord_post.append(ordinary.resources.legitimacy)

        world.run(ticks_after_shock)
        hive_final.append(hive.resources.legitimacy)
        ord_final.append(ordinary.resources.legitimacy)

    return LegitimacyRecoverySample(
        hive_mind_pre_shock=statistics.mean(hive_pre),
        hive_mind_post_shock=statistics.mean(hive_post),
        hive_mind_final=statistics.mean(hive_final),
        ordinary_pre_shock=statistics.mean(ord_pre),
        ordinary_post_shock=statistics.mean(ord_post),
        ordinary_final=statistics.mean(ord_final),
    )


@dataclass
class TechGapObservation:
    seed: int
    initial_gap: float
    final_gap: float


def observe_espionage_tech_gap(
    num_seeds: int = DEFAULT_SEEDS, ticks: int = DEFAULT_TICKS
) -> list[TechGapObservation]:
    """Doc 6/7: direction is *not* pre-registered — this is a Red Queen
    observation, not a pass/fail gate. Tracks (max tech) - (DoomCorp-style
    laggard tech) across the run using the full 19-archetype world, where
    DOOMSAYER is a company that both accumulates its own tech and is a
    frequent espionage target/actor via the tech-leader chase logic."""
    observations: list[TechGapObservation] = []
    for seed in range(num_seeds):
        world = build_full_world(seed=seed)
        by_archetype = {c.archetype: c for c in world.companies}
        laggard = by_archetype[CompanyArchetype.DOOMSAYER]
        leader_initial = max(c.resources.tech for c in world.companies)
        initial_gap = leader_initial - laggard.resources.tech
        world.run(ticks)
        leader_final = max(c.resources.tech for c in world.companies if c.name != laggard.name)
        final_gap = leader_final - laggard.resources.tech
        observations.append(TechGapObservation(seed=seed, initial_gap=initial_gap, final_gap=final_gap))
    return observations
