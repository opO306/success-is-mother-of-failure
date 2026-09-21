from __future__ import annotations

from dataclasses import dataclass, field

from ..config import SimulationConfig

SLOTS: tuple[str, ...] = ("새벽", "아침", "낮", "오후", "저녁", "밤")
SLOT_INDEX = {name: i for i, name in enumerate(SLOTS)}
NIGHT_SLOTS = frozenset({"새벽", "밤"})


def _drugs() -> dict[str, float]:
    return {"술": 0.5, "아편": 2.0}


@dataclass
class WorldConfig:
    """Physical constants of the world. Starting values, meant to be reviewed; none of them is a decision."""

    llm: SimulationConfig = field(default_factory=SimulationConfig)
    knowledge_prompt_window: int = 20

    # food: a unit of 식량 is one day's need
    food_need_per_day: float = 1.0
    reserve_max_days: float = 2.0            # what a body can store beyond today
    underfed_share: float = 0.6              # eating less than this share of need makes it an underfed day
    malnutrition_after_days: int = 3
    malnutrition_illness_after_days: int = 5
    starvation_after_days: int = 10
    starvation_health_loss: float = 8.0
    malnutrition_factor: float = 0.8

    # sleep: slots slept per day
    sleep_need_slots: int = 2
    sleep_deprived_debt: float = 2.0
    sleep_deprived_factor: float = 0.85
    exhausted_debt: float = 5.0
    exhausted_factor: float = 0.6
    collapse_debt: float = 8.0               # the body sleeps whether or not it was planned

    # injury and illness
    bleeding_health_loss_per_slot: float = 5.0
    light_injury_factor: float = 0.9
    heavy_injury_factor: float = 0.6
    light_injury_heal_days: int = 3
    infection_after_untreated_days: int = 2
    illness_onset: float = 1.0
    illness_health_loss_per_day: float = 3.0
    illness_factor: float = 0.75
    illness_recovery_per_day: float = 0.25   # only when fed and rested
    health_recovery_per_day: float = 5.0

    # strength
    strength_gain_per_training_slot: float = 0.6
    strength_max: float = 60.0
    strength_decay_per_day: float = 0.1
    strength_floor: float = 5.0

    # drugs
    addiction_gain: dict[str, float] = field(default_factory=_drugs)
    addiction_threshold: float = 3.0
    addiction_decay_per_day: float = 0.3
    withdrawal_factor: float = 0.7
    withdrawal_health_loss: float = 2.0
    drug_boost_factor: float = 1.15

    # work
    tech_yield_bonus_per_level: float = 0.05
    tool_yield_factor: float = 1.5
    steam_yield_factor: float = 3.0
    skill_gain_per_slot: float = 0.1
    skill_yield_bonus_per_level: float = 0.1
    research_gain_per_slot: float = 0.2
    notice_days: int = 7

    # bank
    bank_daily_rate: float = 0.01
    bank_risk_premium: float = 0.01
    bank_term_days: int = 20
    bank_max_principal: float = 100.0
    bank_note_multiplier: float = 3.0        # bank notes it will have out, relative to the coins it holds

    # contests
    attention_awake: float = 3.0
    attention_guarding: float = 5.0
    stealth_night_bonus: float = 3.0
    stealth_tool_bonus: float = 1.0
    detection_close_margin: float = 1.0
    fight_close_ratio: float = 0.1
    surprise_factor: float = 1.5
    heavy_injury_ratio: float = 0.3
    mortal_ratio: float = 0.5
    mortal_health_loss: float = 60.0
    carry_limit: float = 10.0                # what one body can take away or wreck in one act
    weapon_power: dict[str, float] = field(default_factory=lambda: {"머스킷": 25.0, "칼": 8.0, "도구": 2.0})
