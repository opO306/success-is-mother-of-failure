"""Needs of the mind and the hidden temperament that decides what satisfies them.

Nothing here says what is fun. An experience has physical features (who was there, whether it was new, whether it could
hurt, whether the body worked, whether something was made); a person has hidden sensitivities to those features.
The same afternoon can be a delight to one and dull to another, and anything done again and again wears thin.

Body and mind are not separate channels. A body in distress (thirst, hunger, cold, pain) makes everything else less
enjoyable and keeps the mind uneasy, and the moment that distress lifts is itself a pleasure, whatever one's temperament.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

NEEDS = ("즐거움", "호기심", "사람", "친밀함", "인정", "안전", "자율")
FEATURES = ("함께", "새로움", "위험", "몸씀", "실력", "맛", "취함", "만듦", "이김", "평온")
BASE_RISE = {"즐거움": 2.0, "호기심": 1.5, "사람": 2.0, "친밀함": 1.0, "인정": 0.7, "안전": 0.0, "자율": 0.0}

# starting constants, open to review like every other number in config
RELIEF_WEIGHT = 1.5      # a parched throat getting water pleases anyone; not a temperament, and it does not wear thin
DISTRESS_DAMPING = 0.5   # at the worst distress, every other kind of enjoyment is felt at half strength
DISTRESS_UNEASE = 3.0    # how much the worst distress raises unease each slot

# why a moment felt good, told the way a person would say it; which of these applied is computed, never chosen
REASONS = {
    "함께": "사람들과 함께여서", "새로움": "처음 겪는 것이어서", "위험": "아슬아슬해서", "몸씀": "몸을 힘껏 써서",
    "실력": "손에 익어 가는 게 느껴져서", "맛": "맛이 좋아서", "취함": "머리가 몽롱하게 풀려서", "만듦": "무언가가 만들어져서",
    "이김": "이겨서", "평온": "마음 편히 쉬어서",
}


@dataclass
class Mind:
    need: dict[str, float]
    rise: dict[str, float]
    temperament: dict[str, float]
    habituation: dict[str, float] = field(default_factory=dict)
    bonds: dict[str, float] = field(default_factory=dict)
    known: set[str] = field(default_factory=set)
    best: tuple | None = None    # (pleasure, context, reasons)
    worst: tuple[float, str] | None = None


def new_mind(rng: random.Random, start: float) -> Mind:
    return Mind(
        need={n: start for n in NEEDS},
        rise={n: BASE_RISE[n] * rng.uniform(0.5, 1.5) for n in NEEDS},
        temperament={f: rng.uniform(0.1, 1.9) for f in FEATURES},
    )


def is_new(mind: Mind, key: str) -> float:
    if key in mind.known:
        return 0.0
    mind.known.add(key)
    return 1.0


def experience(
    mind: Mind, features: dict[str, float], activity: str, context: str, companions: list[str] = (),
    distress: float = 0.0, relief: float = 0.0, relief_reason: str = "",
) -> float:
    """One slot lived. Returns how much it pleased them; the needs move accordingly.
    `distress` is how bad the body feels now (0-1); `relief` how much of a bodily distress lifted during this slot."""
    worn = mind.habituation.get(activity, 0.0)
    damp = 1.0 - DISTRESS_DAMPING * min(1.0, distress)
    shares = [(mind.temperament[f] * features.get(f, 0.0) * (1.0 - worn) * damp, REASONS[f]) for f in FEATURES]
    if relief > 0:
        shares.append((RELIEF_WEIGHT * relief, relief_reason or "괴로움이 가셔서"))
    pleasure = sum(value for value, _ in shares)
    mind.need["즐거움"] = _clip(mind.need["즐거움"] - pleasure * 12)
    mind.need["호기심"] = _clip(mind.need["호기심"] - features.get("새로움", 0.0) * 20 * mind.temperament["새로움"])
    mind.need["사람"] = _clip(mind.need["사람"] - features.get("함께", 0.0) * 10)
    closeness = sum(mind.bonds.get(p, 0.0) for p in companions)
    mind.need["친밀함"] = _clip(mind.need["친밀함"] - closeness * 8)
    for p in companions:
        mind.bonds[p] = min(1.0, mind.bonds.get(p, 0.0) + 0.02)
    if features.get("평온", 0.0) > 0:
        mind.need["안전"] = _clip(mind.need["안전"] - 3 * features["평온"])
    mind.habituation[activity] = min(0.9, worn + 0.15)
    if pleasure > 0 and (mind.best is None or pleasure > mind.best[0]):
        reasons = [reason for value, reason in sorted(shares, key=lambda s: -s[0]) if value >= 0.3 * pleasure][:2]
        mind.best = (pleasure, context, reasons)
    return pleasure


def event(mind: Mind, need: str, amount: float, context: str = "") -> None:
    """Something that happened to them: violence seen (안전 up), being robbed or held (자율 up), a gift (인정 down)."""
    mind.need[need] = _clip(mind.need[need] + amount)
    suffer(mind, amount, context)


def suffer(mind: Mind, amount: float, context: str) -> None:
    """A moment that was hard to bear, kept as a candidate for the worst of the day."""
    if amount > 0 and context and (mind.worst is None or amount > mind.worst[0]):
        mind.worst = (amount, context)


def slot_passes(mind: Mind, alone: bool, distress: float = 0.0) -> None:
    for need, rate in mind.rise.items():
        if need == "사람" and not alone:
            continue
        mind.need[need] = _clip(mind.need[need] + rate)
    mind.need["안전"] = _clip(mind.need["안전"] + DISTRESS_UNEASE * min(1.0, distress))


def day_passes(mind: Mind) -> tuple[str | None, str | None]:
    for activity in list(mind.habituation):
        mind.habituation[activity] *= 0.7
        if mind.habituation[activity] < 0.01:
            del mind.habituation[activity]
    mind.need["안전"] = _clip(mind.need["안전"] - 5)
    mind.need["자율"] = _clip(mind.need["자율"] - 5)
    best = None
    if mind.best:
        _, context, reasons = mind.best
        best = f"{context} — {', '.join(reasons)} 좋았다" if reasons else context
    worst = mind.worst[1] if mind.worst else None
    mind.best = mind.worst = None
    return best, worst


def capability(mind: Mind) -> float:
    factor = 1.0
    if mind.need["즐거움"] >= 80:
        factor *= 0.85
    if mind.need["사람"] >= 85 or mind.need["친밀함"] >= 85:
        factor *= 0.9
    if mind.need["안전"] >= 80:
        factor *= 0.9
    return factor


def sleep_quality(mind: Mind) -> float:
    return 0.5 if mind.need["안전"] >= 70 else 1.0


# Each need reaches a person as it does a body: something felt in the chest or limbs and a thought, at the same moment.
# A need is felt faintly long before it is overwhelming: in the first real run nobody's curiosity (at most 44) ever
# crossed the single line of 60, so every mind read "편하다" for three days. Levels, lowest first.
_SIGNALS = {
    "즐거움": [(30, "몸이 조금 나른하다. 뭔가 재미있는 일이 있었으면 싶다"),
            (60, "몸이 늘어지고 근질거린다. 사는 게 몹시 따분하고 무엇에도 흥이 나지 않는다"),
            (85, "몸이 축 처져 일어나기도 싫다. 이렇게 사는 게 다 무슨 소용인가 싶다")],
    "호기심": [(30, "눈길이 자꾸 이리저리 간다. 조금 궁금한 것들이 있다"),
            (60, "가만히 있으면 좀이 쑤신다. 이것저것 궁금하다"),
            (85, "발이 들썩여 가만히 있을 수가 없다. 궁금해서 견딜 수가 없다")],
    "사람": [(30, "주위가 조용한 게 조금 허전하다. 누군가와 말을 나누고 싶다"),
           (60, "가슴 한쪽이 서늘하다. 사람들 틈에 있고 싶다"),
           (85, "가슴이 시리도록 서늘하다. 혼자인 게 견디기 힘들다")],
    "친밀함": [(30, "문득 가까운 누군가의 얼굴이 떠오른다"),
            (60, "가슴이 허전하다. 마음을 나눌 사람이 그립다"),
            (85, "가슴이 텅 빈 것 같다. 기댈 사람이 몹시 그립다")],
    "인정": [(30, "누가 나를 봐 주었으면 하는 마음이 조금 든다"),
           (60, "어깨가 처진다. 아무도 나를 알아주지 않는 것 같다"),
           (85, "고개가 자꾸 숙여진다. 나는 아무 쓸모도 없는 것 같다")],
    "안전": [(25, "주위 소리에 귀가 조금 쫑긋해진다. 어딘가 마음이 놓이지 않는다"),
           (50, "가슴이 두근거리고 잠이 얕다. 마음이 불안하고 주위를 자꾸 살피게 된다"),
           (80, "심장이 쿵쾅거리고 손끝이 차갑다. 무서워서 몸이 굳는다")],
    "자율": [(25, "어딘가 답답하다"),
           (50, "속에서 열이 치민다. 억눌린 느낌에 속이 끓는다"),
           (80, "주먹에 힘이 들어가고 몸이 떨린다. 더는 참을 수가 없다")],
}


def signals(mind: Mind) -> list[tuple[float, str]]:
    """(how strongly, what is felt): the highest level each need has reached. The strength only orders what comes
    first; it is never shown."""
    out = []
    for need, levels in _SIGNALS.items():
        reached = [text for line, text in levels if mind.need[need] >= line]
        if reached:
            out.append((0.2 + 0.8 * mind.need[need] / 100.0, reached[-1]))
    return out


def felt(mind: Mind) -> list[str]:
    return [text for _, text in signals(mind)] or ["마음은 대체로 편하다"]


def _clip(value: float) -> float:
    return max(0.0, min(100.0, value))
