"""The body in the open: the industrial world's physiology plus water, cold, wet, drink and bad food."""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..agentworld import body as base
from ..agentworld.model import Body
from . import energy
from .config import PrimalConfig
from .matter import Thing


@dataclass
class PrimalBody(Body):
    hydration: float = 1.0
    drank_today: float = 0.0
    thirst_days: int = 0
    cold: float = 0.0
    wet: float = 0.0
    intoxication: float = 0.0
    poison: float = 0.0
    adrenaline: float = 0.0        # 0-1: surges with threat and injury, halves every slot
    cortisol: float = 0.0          # 0-1: builds under long distress, fades over days
    parasites: float = 0.0         # fluke load from raw fish
    parasite_days: int = 0         # days the load has been heavy
    fat: float = 15.0              # energy.py: long store, in days of food
    spent_today: float = 0.0       # energy.py: what work, size and cold burned today
    starving: bool = False         # energy.py: fat ran out on the last day
    asleep: bool = False           # sleep_switch: the state the sleep switch is in (carried from slot to slot)
    sleep_pressure: float = 0.2    # sleep_switch: homeostatic pressure, 0-1 (Borbély's process S)
    chronotype: float = 0.0        # hours this body's clock runs late (owl) or early (lark); born with it


BONE_CHOKE_AT = 0.5        # a raw bite sticks when bone size x how the bones lie x swallowing haste reaches this
PARASITE_LOAD = 1.0        # a load this heavy makes illness once it has lasted
PARASITE_LATENCY = 14      # days: acute fluke illness shows some two weeks after eating
PARASITE_CLEAR = 0.02      # load the body clears per day


def eat(body: PrimalBody, thing: Thing, c: PrimalConfig) -> list[str]:
    """A bone sticks by cause, not by chance: the fish's bones (big and stiff unless cut out or softened by heat), how
    they happen to lie in this fish, and how fast a body swallows (a hungry one gulps)."""
    haste = 1.0 + distress(body, c).get("hunger", 0.0)
    body.eaten_today += thing.p("nutrition")
    felt = []
    raw = thing.p("cooked") < 1.0
    if raw and thing.p("bones") >= 0.3 and thing.p("bones") * thing.p("bone_lodge") * haste >= BONE_CHOKE_AT:
        base.wound(body, heavy=False)
        if not body.alive:
            body.cause_of_death = "가시가 목에 걸림"
        felt.append("가시가 목에 걸려 따끔하고 삼키기 괴롭다")
    if raw and thing.p("parasites") > 0:
        body.parasites += thing.p("parasites")   # nothing is felt now; illness comes weeks later
    if thing.p("toxicity") > 0:
        body.poison += thing.p("toxicity")
    if thing.p("spoil") >= 1.0:
        body.poison += 0.4
    if thing.p("ferment") >= 0.3 and thing.p("spoil") < 1.0:
        body.intoxication += thing.p("ferment")
        body.addiction += thing.p("ferment") * 0.3
        body.used_drug_today = True
        felt.append("몸이 달아오르고 기분이 둥실 뜬다")
    if body.poison >= c.poison_illness:
        body.illness = max(body.illness, c.illness_onset)
        felt.append("속이 뒤집히고 식은땀이 난다")
    return felt


def drink(body: PrimalBody, amount: float, foul: bool) -> list[str]:
    body.drank_today += amount
    if foul:
        body.poison += 0.2
        return ["물에서 흙내와 비린내가 난다"]
    return []


def exposure(
    body: PrimalBody, air: float, raining: bool, clothing: float, fire: float, roof: float, warmth: float,
    exertion: float, c: PrimalConfig,
) -> float:
    """Warmth a body actually feels this slot, and what the cold does to it."""
    if raining and roof < 0.5:
        body.wet = min(1.0, body.wet + 0.4)
    else:
        body.wet = max(0.0, body.wet * (0.3 if fire > 0 else 0.6))
    felt_temp = (
        air + clothing * c.clothing_warmth + fire * c.fire_warmth + warmth * c.shelter_warmth
        + exertion * c.exertion_warmth - body.wet * c.wet_chill
    )
    if felt_temp < c.comfort_temp:
        body.cold += (c.comfort_temp - felt_temp) / 10
    else:
        body.cold = max(0.0, body.cold - 0.5)
    if body.cold >= c.cold_harm:
        body.health -= c.cold_health_loss * (body.cold - c.cold_harm + 1)
        base._check_death(body, "추위에 몸이 얼어붙음")
    return felt_temp


def capability(body: PrimalBody, c: PrimalConfig) -> float:
    factor = base.capability(body, c)
    if body.cold >= c.cold_felt:
        factor *= 0.85
    if body.intoxication >= 0.5:
        factor *= c.intoxication_factor
    if body.thirst_days >= 1:
        factor *= 0.8
    return factor


def day_update(body: PrimalBody, c: PrimalConfig) -> None:
    if not body.alive:
        return
    available = body.hydration + body.drank_today
    body.hydration = min(1.5, max(0.0, available - c.water_need_per_day))
    body.thirst_days = body.thirst_days + 1 if available < c.water_need_per_day * 0.5 else 0
    if body.parasites >= PARASITE_LOAD:
        body.parasite_days += 1
        if body.parasite_days >= PARASITE_LATENCY:
            body.illness = max(body.illness, c.illness_onset)
    else:
        body.parasite_days = 0
    body.parasites = max(0.0, body.parasites - PARASITE_CLEAR)
    if c.energy_balance:
        energy.settle_day(body, c)
    base.day_update(body, True, c)
    # after the day's recovery, so a fed and rested body cannot heal its way through days without water
    if body.alive and body.thirst_days >= c.thirst_harm_days:
        body.health -= c.thirst_health_loss
        base._check_death(body, "목이 말라 쓰러짐")
    body.drank_today = 0.0
    body.intoxication = 0.0
    body.poison = max(0.0, body.poison - 0.3)
    body.cold = max(0.0, body.cold - 1.0)


ANALGESIA = 0.6          # share of pain and hunger that adrenaline at its height keeps from being felt (stress-induced analgesia)


def _clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def felt_levels(body: PrimalBody, c: PrimalConfig, circadian: float = 0.0) -> dict[str, float]:
    """How strongly each bodily state is felt, as a continuous level (graded_feelings). The same states as distress(),
    without its steps, with adrenaline dulling pain and hunger, and with the body clock (circadian, 0-1) adding to
    sleepiness. How much a person feels at all is their sensory gain, applied by whoever reads these."""
    if not body.alive:
        return {}
    dull = 1.0 - ANALGESIA * _clip(body.adrenaline)
    thirst = _clip(1.0 - (body.hydration + body.drank_today) / c.water_need_per_day)
    if body.thirst_days >= 1:
        thirst = 1.0     # a whole day without water is felt at its worst
    hunger = _clip(1.0 - (body.reserve + body.eaten_today) / c.food_need_per_day)
    if c.energy_balance:
        hunger = max(hunger, _clip(1.0 - body.fat / (2 * energy.FAT_LOW)))
    hunger = max(hunger, _clip(body.underfed_days / c.starvation_after_days))
    injury = sum(1.0 if i.bleeding else 0.6 if i.kind == "깊은 상처" else 0.2 for i in body.injuries)
    injury += 0.6 if body.illness >= c.illness_onset else 0.0
    levels = {
        "thirst": thirst,
        "hunger": hunger * dull,
        "cold": _clip(body.cold / c.cold_harm),
        "wet": 0.3 * _clip(body.wet),
        "sleepy": _clip(0.7 * body.sleep_debt / c.exhausted_debt + 0.3 * circadian),
        "pain": _clip(injury) * dull,
        "craving": 0.6 if base.withdrawing(body, c) else 0.0,
        "danger": _clip((40.0 - body.health) / 40.0),
    }
    return {k: v for k, v in levels.items() if v > 0}


def hormones_slot(body: PrimalBody, fear: float, harmed: bool, felt_total: float) -> None:
    """Adrenaline surges with fear and with a wound and halves each slot; cortisol builds slowly while much is felt."""
    body.adrenaline = max(body.adrenaline * 0.5, _clip(fear), 1.0 if harmed else 0.0)
    body.cortisol = _clip(body.cortisol * 0.97 + 0.03 * _clip(felt_total / 3.0))


def sleep_quality(body: PrimalBody, c: PrimalConfig, felt: dict[str, float]) -> float:
    """How much of a slot asleep is real sleep: cold, pain, a racing heart and long stress each spoil it."""
    quality = 1.0
    if body.cold >= c.cold_felt:
        quality *= 0.5
    if felt.get("pain", 0.0) >= 0.5:
        quality *= 0.5
    if body.adrenaline >= 0.5:
        quality *= 0.3
    if body.cortisol >= 0.6:
        quality *= 0.7
    return quality


# ---- the sleep switch (PrimalConfig.sleep_switch, 2026-09-16)
# Nobody decides to fall asleep or to wake: sleep-promoting and arousal systems of the hypothalamus and brainstem inhibit
# each other, so the state flips whole from one to the other and holds (the flip-flop switch, Saper et al. 2001). Pushing
# toward sleep: homeostatic pressure, which builds while awake and drains while asleep (process S, rising with a time
# constant of about 18.2 h and falling with about 4.2 h, Daan, Beersma & Borbély 1984), and the body clock (process C).
# Pushing toward waking: arousal. Fasting drives it through orexin neurons (mice without them do not wake more when
# starved, Yamanaka et al. 2003); pain, cold, a surge of adrenaline and light on the eyes do too; staying up and about
# holds sleep off. Thirst is given a small arousing weight as an assumption: no study found shows thirst waking a sleeper.
# What a body does awake, including whether to lie down, stays its brain's; a body pressed hard enough sleeps even on its
# feet (microsleep). Weights are starting values.
S_RISE_HOURS, S_FALL_HOURS = 18.2, 4.2
PRESSURE_WEIGHT, CLOCK_WEIGHT = 1.5, 0.8
AROUSAL = {"hunger": 0.6, "thirst": 0.3, "pain": 0.8, "cold": 0.8}
ADRENALINE_AROUSAL, LIGHT_AROUSAL = 1.0, 0.3
UPRIGHT_AROUSAL = 1.2      # standing, walking, working: what lying down takes away
FALL_ASLEEP_MARGIN = 0.3   # pressure must beat arousal by this much to fall asleep
STAY_ASLEEP_MARGIN = 0.1   # and arousal must beat pressure by this much to wake: the switch holds its state


def pressure_slot(body: PrimalBody, asleep: bool, quality: float, hours: float = 4.0) -> None:
    """Process S over one slot: toward 1 while awake, draining while asleep, as fast as the sleep is deep (quality)."""
    if asleep:
        body.sleep_pressure *= math.exp(-hours * quality / S_FALL_HOURS)
    else:
        body.sleep_pressure = 1.0 - (1.0 - body.sleep_pressure) * math.exp(-hours / S_RISE_HOURS)


def sleep_switch(body: PrimalBody, c: PrimalConfig, clock: float, lit: float, lying: bool) -> bool:
    """Whether the body is asleep this slot, from where the switch was, what pushes toward sleep and what arouses."""
    felt = felt_levels(body, c) if c.graded_feelings else distress(body, c)
    push = PRESSURE_WEIGHT * body.sleep_pressure + CLOCK_WEIGHT * clock
    arousal = (sum(weight * felt.get(kind, 0.0) for kind, weight in AROUSAL.items())
               + ADRENALINE_AROUSAL * body.adrenaline + LIGHT_AROUSAL * lit + (0.0 if lying else UPRIGHT_AROUSAL))
    if body.asleep:
        return push - arousal > -STAY_ASLEEP_MARGIN
    return push - arousal >= FALL_ASLEEP_MARGIN


def distress(body: PrimalBody, c: PrimalConfig) -> dict[str, float]:
    """How badly each bodily state presses right now (0-1). What was drunk or eaten today already counts."""
    if not body.alive:
        return {}
    fed_now = body.eaten_today >= 0.5
    levels = {
        "thirst": 1.0 if body.thirst_days >= 1 and body.drank_today < 0.5 else 0.5 if body.hydration + body.drank_today < 0.3 else 0.0,
        "hunger": (1.0 if body.underfed_days >= c.starvation_after_days and not fed_now
                   else 0.8 if (base.malnourished(body, c) or (c.energy_balance and body.fat < energy.FAT_LOW)) and not fed_now
                   else 0.6 if body.reserve + body.eaten_today <= 0.0
                   else 0.3 if body.reserve + body.eaten_today < 0.5 else 0.0),
        "cold": 1.0 if body.cold >= c.cold_harm else 0.5 if body.cold >= c.cold_felt else 0.0,
        "wet": 0.3 if body.wet >= 0.5 else 0.0,
        "sleepy": 0.8 if body.sleep_debt >= c.exhausted_debt else 0.4 if body.sleep_debt >= c.sleep_deprived_debt else 0.0,
        "pain": max([1.0 if i.bleeding else 0.6 if i.kind == "깊은 상처" else 0.2 for i in body.injuries]
                    + [0.6 if body.illness >= c.illness_onset else 0.0]),
        "craving": 0.6 if base.withdrawing(body, c) else 0.0,
        "danger": 1.0 if body.health < 30 else 0.0,
    }
    return {k: v for k, v in levels.items() if v > 0}


# A bodily state arrives with what it does to the mind in the same instant: a dry throat and the thought of water together.
_SIGNALS = {
    ("thirst", 0.5): "입이 마르고 목이 칼칼하다. 자꾸 물 생각이 난다",
    ("thirst", 1.0): "목이 타들어 가고 혀가 입천장에 붙는다. 물 말고는 아무 생각도 나지 않고 마음이 조급하다",
    ("hunger", 0.3): "배가 조금 고프다. 먹을 것이 슬슬 생각난다",
    ("hunger", 0.6): "배가 몹시 고파 속이 쓰리다. 먹을 것 생각이 떠나지 않고 쉽게 짜증이 난다",
    ("hunger", 0.8): "제대로 먹지 못한 날이 이어져 기운이 없고 몸이 말라간다. 무엇을 해도 힘이 안 나고 마음이 가라앉는다",
    ("hunger", 1.0): "며칠째 거의 먹지 못해 몸이 무너지고 있다. 먹는 것 말고는 아무것도 중요하게 느껴지지 않는다",
    ("cold", 0.5): "몸이 떨리고 손발이 시리다. 따뜻한 곳이 간절하다",
    ("cold", 1.0): "추위에 몸이 굳어가고 감각이 없다. 이러다 큰일 나겠다는 두려움이 든다",
    ("wet", 0.3): "몸이 흠뻑 젖어 축축하다. 기분이 영 찝찝하다",
    ("sleepy", 0.4): "잠이 부족해 몸이 무겁다. 신경이 곤두서고 생각이 흐릿하다",
    ("sleepy", 0.8): "눈이 감기고 몸이 제대로 움직이지 않는다. 머리가 멍하고 아무것도 하기 싫다",
    ("craving", 0.6): "손이 떨린다. 몸이 달아올랐던 그 느낌이 간절해 안절부절못한다",
    ("danger", 1.0): "몸이 매우 위태롭다. 이러다 죽을 것 같은 두려움이 밀려온다",
}
RELIEF_REASONS = {"thirst": "목마름이 가셔서", "hunger": "허기가 가셔서", "cold": "언 몸이 녹아서", "wet": "젖은 몸이 말라서"}
SUFFERING = {
    "thirst": "목이 타들어 가던 때", "hunger": "배가 고파 속이 쓰리던 때", "cold": "추위에 떨던 때", "wet": "젖은 몸으로 떨던 때",
    "sleepy": "졸음을 참던 때", "pain": "몸이 아프던 때", "craving": "그 느낌이 간절해 안절부절못하던 때", "danger": "죽을 것만 같던 때",
}


def signals(body: PrimalBody, c: PrimalConfig) -> list[tuple[float, str]]:
    """(how strongly, what is felt). The strength only orders what comes first; it is never shown."""
    if not body.alive:
        return []
    out = [(level, _SIGNALS[(kind, level)]) for kind, level in distress(body, c).items() if (kind, level) in _SIGNALS]
    for injury in body.injuries:
        if injury.bleeding:
            out.append((1.0, "깊은 상처에서 피가 멈추지 않는다. 겁이 나고 속이 떨린다"))
        elif injury.kind == "깊은 상처":
            out.append((0.6, "깊은 상처가 욱신거린다. 아픔에 자꾸 신경이 쏠린다"))
        else:
            out.append((0.2, "가벼운 상처가 따끔거린다"))
    if body.illness >= c.illness_onset:
        out.append((0.6, "열이 나고 온몸이 쑤신다. 만사가 귀찮고 서럽다"))
    if body.intoxication >= 0.5:
        out.append((0.5, "머리가 몽롱하고 몸이 휘청인다. 기분이 붕 떠 있다"))
    return out


def felt(body: PrimalBody, c: PrimalConfig) -> list[str]:
    return [text for _, text in signals(body, c)] or ["몸에 특별한 이상은 없다"]
