"""Physiology. Numbers stay inside the engine; a person only ever hears how their body feels."""
from __future__ import annotations

from .config import WorldConfig
from .model import Body, Injury

FOOD_VALUE = {"식량": 1.0, "물고기": 1.0, "술": 0.2}
DRUGS = ("술", "아편")
MEDICINE = "약"


def is_asleep_state(body: Body) -> bool:
    return not body.alive


def malnourished(body: Body, c: WorldConfig) -> bool:
    return body.underfed_days >= c.malnutrition_after_days


def withdrawing(body: Body, c: WorldConfig) -> bool:
    return body.addiction >= c.addiction_threshold and not body.used_drug_today


def capability(body: Body, c: WorldConfig) -> float:
    """How much of their strength and skill a body can actually bring to work or a fight right now."""
    if not body.alive:
        return 0.0
    factor = 1.0
    drugged = body.used_drug_today
    if malnourished(body, c):
        factor *= c.malnutrition_factor
    if body.sleep_debt >= c.exhausted_debt and not drugged:
        factor *= c.exhausted_factor
    elif body.sleep_debt >= c.sleep_deprived_debt and not drugged:
        factor *= c.sleep_deprived_factor
    for injury in body.injuries:
        if drugged:
            continue  # the pain is dulled, the wound is not
        factor *= c.heavy_injury_factor if injury.kind == "깊은 상처" else c.light_injury_factor
    if body.illness >= c.illness_onset:
        factor *= c.illness_factor
    if withdrawing(body, c):
        factor *= c.withdrawal_factor
    if drugged:
        factor *= c.drug_boost_factor
    return factor * min(1.0, max(0.1, body.health / 100.0) ** 0.5)


def eat(body: Body, good: str, qty: float) -> float:
    value = FOOD_VALUE.get(good, 0.0) * qty
    body.eaten_today += value
    return value


def use(body: Body, good: str, c: WorldConfig) -> str:
    if good in DRUGS:
        body.used_drug_today = True
        body.addiction += c.addiction_gain.get(good, 0.0)
        return "통증과 피로가 무뎌짐"
    if good == MEDICINE:
        treated = False
        for injury in body.injuries:
            if not injury.treated:
                injury.treated = True
                injury.bleeding = False
                treated = True
        if body.illness > 0:
            body.illness = max(0.0, body.illness - 1.0)
            treated = True
        return "상처와 병을 돌봄" if treated else "돌볼 상처나 병이 없음"
    return "아무 효과 없음"


def wound(body: Body, heavy: bool, extra_health_loss: float = 0.0) -> Injury:
    injury = Injury(kind="깊은 상처" if heavy else "가벼운 상처", bleeding=heavy)
    body.injuries.append(injury)
    body.health -= extra_health_loss + (15.0 if heavy else 5.0)
    _check_death(body, "싸움에서 입은 상처")
    return injury


def slot_update(body: Body, asleep: bool, c: WorldConfig) -> None:
    if not body.alive:
        return
    if asleep:
        body.slept_today += 1
    for injury in body.injuries:
        if injury.bleeding:
            body.health -= c.bleeding_health_loss_per_slot
    _check_death(body, "피를 너무 많이 흘림")


def day_update(body: Body, trained_bonus_allowed: bool, c: WorldConfig) -> None:
    """End of day. Order matters: what they ate today decides whether training built anything."""
    if not body.alive:
        return
    # food
    available = body.reserve + body.eaten_today
    body.reserve = min(c.reserve_max_days, max(0.0, available - c.food_need_per_day))
    underfed = available < c.food_need_per_day * c.underfed_share
    body.underfed_days = body.underfed_days + 1 if underfed else max(0, body.underfed_days - 1 if available >= c.food_need_per_day else body.underfed_days)
    if body.underfed_days >= c.starvation_after_days:
        body.health -= c.starvation_health_loss
    if body.underfed_days >= c.malnutrition_illness_after_days:
        body.illness = max(body.illness, c.illness_onset)

    # sleep
    body.sleep_debt = max(0.0, body.sleep_debt + (c.sleep_need_slots - body.slept_today))

    # wounds
    for injury in body.injuries:
        injury.days += 1
        if not injury.treated and injury.days >= c.infection_after_untreated_days:
            body.illness = max(body.illness, c.illness_onset)
    body.injuries = [
        i for i in body.injuries
        if not (i.kind == "가벼운 상처" and i.days >= c.light_injury_heal_days and not i.bleeding)
    ]

    # illness
    rested = body.sleep_debt < c.sleep_deprived_debt
    fed = not underfed
    if body.illness >= c.illness_onset:
        body.health -= c.illness_health_loss_per_day
    if body.illness > 0 and fed and rested:
        body.illness = max(0.0, body.illness - c.illness_recovery_per_day)

    # drugs
    if withdrawing(body, c):
        body.health -= c.withdrawal_health_loss
    if not body.used_drug_today:
        body.addiction = max(0.0, body.addiction - c.addiction_decay_per_day)

    # strength
    if body.trained_today and fed and trained_bonus_allowed:
        room = max(0.0, 1.0 - body.strength / c.strength_max)
        body.strength += c.strength_gain_per_training_slot * body.trained_today * room
    elif not body.trained_today:
        body.strength = max(c.strength_floor, body.strength - c.strength_decay_per_day)

    # recovery
    if fed and rested and body.illness < c.illness_onset and not any(i.bleeding for i in body.injuries):
        body.health = min(100.0, body.health + c.health_recovery_per_day)

    _check_death(body, "굶주림과 병" if underfed else "몸이 버티지 못함")
    body.eaten_today = 0.0
    body.slept_today = 0
    body.trained_today = 0
    body.used_drug_today = False


def _check_death(body: Body, cause: str) -> None:
    if body.alive and body.health <= 0:
        body.alive = False
        body.health = 0.0
        body.cause_of_death = cause


def felt(body: Body, c: WorldConfig) -> list[str]:
    """How the body feels from the inside. No numbers: nobody knows their own health as a figure."""
    if not body.alive:
        return []
    lines: list[str] = []
    if body.underfed_days >= c.starvation_after_days:
        lines.append("며칠째 거의 먹지 못해 몸이 무너지고 있다")
    elif malnourished(body, c):
        lines.append("제대로 먹지 못한 날이 이어져 기운이 없고 몸이 말라간다")
    elif body.reserve <= 0.0:
        lines.append("배가 몹시 고프다")
    elif body.reserve < 0.5:
        lines.append("배가 조금 고프다")
    if body.sleep_debt >= c.exhausted_debt:
        lines.append("잠을 너무 못 자서 눈이 감기고 몸이 제대로 움직이지 않는다")
    elif body.sleep_debt >= c.sleep_deprived_debt:
        lines.append("잠이 부족해 피곤하다")
    for injury in body.injuries:
        if injury.bleeding:
            lines.append("깊은 상처에서 피가 멈추지 않는다")
        elif injury.kind == "깊은 상처":
            lines.append("깊은 상처가 욱신거린다")
        else:
            lines.append("가벼운 상처가 있다")
    if body.illness >= c.illness_onset:
        lines.append("열이 나고 몸이 아프다")
    if withdrawing(body, c):
        lines.append("술이나 약 생각이 간절하고 손이 떨린다")
    if body.health < 30:
        lines.append("몸이 매우 위태롭다")
    return lines or ["몸에 특별한 이상은 없다"]
