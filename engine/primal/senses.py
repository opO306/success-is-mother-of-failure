"""Turning properties into what a person can see, feel, smell or taste. The only door from the engine to a mind.

Nothing here may name a technique, a made object or a property. A fired clay bowl is "붉고 단단하게 굳은 오목한 점토".
"""
from __future__ import annotations

from .matter import Thing

# words that must never come out of the engine toward a person (checked by tests over everything the code writes)
FORBIDDEN = (
    "법칙", "규칙", "시뮬레이션", "설계", "엔진", "성질", "수치", "확률",
    "경도", "가소성", "다공성", "인성", "영양가", "독성",
    "토기", "도자기", "그릇", "항아리", "도끼", "화살", "작살", "농사", "농경", "발효", "요리", "가마", "기술", "발명",
    "길들", "가축", "석기", "뗀석기", "간석기", "도구",
)


_PARTICLES = [("이(가)", "이", "가"), ("을(를)", "을", "를"), ("은(는)", "은", "는"), ("과(와)", "과", "와"), ("(으)로", "으로", "로"), ("(이)라고", "이라고", "라고")]


def polish(text: str) -> str:
    """Pick the right Korean particle for the word before it: '점토이(가)' reads as '점토가'. Plain grammar, no meaning."""
    for marker, with_final, without_final in _PARTICLES:
        parts = text.split(marker)
        if len(parts) == 1:
            continue
        rebuilt = parts[0]
        for part in parts[1:]:
            last = rebuilt.rstrip()[-1:] if rebuilt.rstrip() else ""
            if last and "가" <= last <= "힣":
                final = (ord(last) - ord("가")) % 28
                if marker == "(으)로":
                    chosen = without_final if final in (0, 8) else with_final  # ㄹ takes 로
                else:
                    chosen = with_final if final else without_final
            else:
                chosen = marker
            rebuilt = rebuilt + chosen + part
        text = rebuilt
    return text


def sharp_word(value: float) -> str:
    if value >= 0.6:
        return "매우 날카롭다"
    if value >= 0.35:
        return "날카롭다"
    if value >= 0.15:
        return "조금 날이 서 있다"
    return "뭉툭하다"


def hard_word(value: float) -> str:
    if value >= 0.8:
        return "돌처럼 단단하다"
    if value >= 0.5:
        return "단단하다"
    if value >= 0.25:
        return "조금 무르다"
    return "무르다"


def weight_word(value: float) -> str:
    if value >= 0.8:
        return "무겁다"
    if value >= 0.35:
        return "묵직하다"
    if value >= 0.1:
        return "가볍다"
    return "아주 가볍다"


_SHAPE_WORDS = {"오목함": "오목한", "길쭉함": "길쭉한", "납작함": "납작한", "뾰족함": "뾰족한", "넓음": "넓게 펼친", "둥긂": "둥근"}


def describe(thing: Thing, person: str | None = None) -> str:
    """How a thing looks to someone holding or seeing it, plus what that person found out by trying it."""
    if person and person in thing.labels:
        base = thing.labels[person]
    elif thing.parts:
        base = " 에 ".join(describe(part, person) for part in thing.parts[:-1]) + " 를 " + describe(thing.parts[-1], person) + "(으)로 묶은 것"
    else:
        base = thing.kind
    looks = []
    if thing.p("fired") >= 1.0:
        looks.append("붉고 단단하게 굳은")
    elif thing.kind == "점토" and thing.p("plasticity") >= 0.5:
        looks.append("말랑한")
    elif thing.kind == "점토" and thing.p("moisture") < 0.15 and thing.shape:
        looks.append("말라 굳은")
    if thing.p("cooked") >= 3.0:
        looks.append("까맣게 탄")
    elif thing.p("cooked") >= 1.0:
        looks.append("익힌")
    if thing.p("spoil") >= 1.0:
        looks.append("썩은")
    elif thing.p("spoil") >= 0.5:
        looks.append("상해가는")
    if thing.p("ferment") >= 0.5 and thing.p("spoil") < 1.0:
        looks.append("시큼한 냄새가 나는")
    if thing.kind == "가죽":
        if thing.p("scraped") >= 1.0 and thing.p("moisture") < 0.2:
            looks.append("부드럽게 마른")
        elif thing.p("moisture") < 0.2:
            looks.append("뻣뻣하게 굳은")
    if thing.shape in _SHAPE_WORDS:
        looks.append(_SHAPE_WORDS[thing.shape])
    if thing.p("sharpness") >= 0.35 and not thing.parts:
        looks.append("날이 선")
    text = " ".join(looks + [base]) if looks else base
    found = thing.tested.get(person or "", set())
    notes = []
    if "water" in found:
        notes.append("물이 새지 않음" if thing.p("porosity") < 0.3 else "물이 스며 나옴")
    if "cut" in found:
        notes.append(f"베어 보니 {sharp_word(max(thing.p('sharpness'), *(p.p('sharpness') for p in thing.parts)) if thing.parts else thing.p('sharpness'))}")
    if "taste" in found:
        notes.append(taste_words(thing))
    if thing.contents:
        notes.append("안에 " + ", ".join(describe(c, person) for c in thing.contents))
    return text + (f" ({'; '.join(notes)})" if notes else "")


def taste_words(thing: Thing) -> str:
    words = []
    if thing.p("sweetness") >= 0.4:
        words.append("달다")
    if thing.p("toxicity") >= 0.3:
        words.append("쓰고 혀가 아리다")
    if thing.p("ferment") >= 0.3:
        words.append("시큼하고 톡 쏜다")
    if thing.p("spoil") >= 0.5:
        words.append("역한 맛이 난다")
    return ", ".join(words) or "별맛이 없다"
