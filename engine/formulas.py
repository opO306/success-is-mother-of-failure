from __future__ import annotations

import math

from .config import SimulationConfig
from .entities import Company, Employee


def alignment_score(employee: Employee, config: SimulationConfig) -> float:
    """Doc 5-1. Wage term and value-alignment term are pull factors; retaliation
    cost is a separate exit-cost term (see will_desert), not part of this sum."""
    wage_term = employee.wage / employee.expected_wage if employee.expected_wage else 0.0
    score = config.w_wage * wage_term + config.w_values * employee.value_alignment
    return max(0.0, min(1.0, score))


def individual_leak_chance(employee: Employee, config: SimulationConfig) -> float:
    """Doc 8: a single low-alignment employee's independent per-tick risk of
    leaking. Shared by the formula-driven WMD leak roll (heuristics.py) and
    the council-vote fallback (council.py) when an individual LLM call fails."""
    a = alignment_score(employee, config)
    return max(0.0, min(1.0, (1 - a) * config.wmd_leak_sensitivity))


def will_desert(employee: Employee, company: Company, config: SimulationConfig) -> bool:
    """Doc 5-1: A < alternative_attractiveness - expected_retaliation_cost.
    Hive-mind companies have no individual employees to desert (doc 9)."""
    if company.is_hive_mind:
        return False
    a = alignment_score(employee, config)
    threshold = employee.alternative_attractiveness - employee.retaliation_cost
    return a < threshold


def trade_will_proceed(
    expected_profit: float,
    relationship_value: float,
    company: Company,
    config: SimulationConfig,
) -> bool:
    """Doc 5-2: expected_profit + lambda * R(A->B) > 0.
    Emotionless companies (archetype 2) always use lambda = 0."""
    lam = 0.0 if company.is_emotionless else config.lambda_relationship
    return expected_profit + lam * relationship_value > 0


def currency_value(resources, necessity: float, config: SimulationConfig) -> float:
    """Doc 5-3: V = (legitimacy^alpha * tech^beta * necessity^delta)
    / (1 + coercion_abuse^gamma). Non-negative bases only; legitimacy/tech/necessity
    at 0 correctly zero out V (0 raised to a positive power)."""
    legitimacy = max(0.0, resources.legitimacy)
    tech = max(0.0, resources.tech)
    necessity = max(0.0, necessity)
    numerator = (
        (legitimacy ** config.alpha_legitimacy)
        * (tech ** config.beta_tech)
        * (necessity ** config.delta_necessity)
    )
    denominator = 1.0 + max(0.0, resources.coercion_abuse_cumulative) ** config.gamma_coercion_penalty
    return numerator / denominator


def necessity(demand_for_exclusive_resource: float, num_alternative_suppliers: int) -> float:
    """Doc 5-3: necessity falls toward 0 as more suppliers (e.g. a fast-follower
    copying the tech) enter the market."""
    return demand_for_exclusive_resource / (num_alternative_suppliers + 1)


def exchange_rate(v_domestic: float, v_counterpart: float) -> float:
    if v_counterpart == 0:
        return math.inf if v_domestic > 0 else 0.0
    return v_domestic / v_counterpart


def apply_legitimacy_event(
    company: Company,
    exposure: float,
    victim_weight: float,
    evasion_success: float,
    config: SimulationConfig,
) -> float:
    """Legitimacy hit from a betrayal/scandal being discovered. Adopted from the
    external-review pass referenced alongside the design doc, not yet folded
    into it: delta = -base * exposure * victim_weight * (1 - evasion_success).
    Hive-mind companies cannot scapegoat a single employee, so they take the
    full, undamped hit (doc section 9: no partial absorption)."""
    delta = -config.legitimacy_penalty_base * exposure * victim_weight * (1 - evasion_success)
    if not company.is_hive_mind:
        delta *= 0.5  # ordinary companies can partially absorb blame via a scapegoat
    company.resources.legitimacy = max(0.0, company.resources.legitimacy + delta)
    return delta


def decay_legitimacy_recovery(company: Company, config: SimulationConfig, target: float) -> float:
    """Half-life recovery toward `target` per tick. Hive-mind companies do not
    recover from a legitimacy hit (doc section 9)."""
    if company.is_hive_mind:
        return company.resources.legitimacy
    half_life = config.legitimacy_recovery_half_life_ticks
    if half_life <= 0:
        return company.resources.legitimacy
    decay = math.log(2) / half_life
    current = company.resources.legitimacy
    company.resources.legitimacy = current + (target - current) * (1 - math.exp(-decay))
    return company.resources.legitimacy
