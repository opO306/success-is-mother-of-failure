"""How processes change matter. Finite laws; what people try with them is endless.

Every function computes what physically happens and returns what the actor perceives, in sensory words only.
There is no table of outcomes such as "clay + fire = pot": a bowl that holds water is what you get when something
plastic was made concave, dried, and heated long enough that it stopped letting water through.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .matter import CLAY_KINDS, Maker, Thing
from .senses import hard_word, sharp_word, taste_words


@dataclass
class Setting:
    temp: float = 15.0
    raining: bool = False
    sheltered: bool = False
    fire: float = 0.0              # how hot a fire here burns; 0 when there is none
    fire_enclosed: bool = False    # the fire is inside something that keeps its heat in
    water_here: bool = False
    season: str = "봄"
    soil_moisture: float = 0.5


@dataclass
class Outcome:
    ok: bool
    felt: list[str] = field(default_factory=list)
    made: list[Thing] = field(default_factory=list)
    used: list[Thing] = field(default_factory=list)
    exertion: float = 0.0


def _clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def _mark(thing: Thing, what: str) -> None:
    thing.history.append(what)


def steadiness(skill: float, rng: random.Random) -> float:
    """How true a hand works this one time, 0..1. Anyone has hands (0.3); practice brings it toward 1 with less and
    less gain, and a practised hand also wavers less from one try to the next. Laws that take it default to 1.0, the
    result they gave for everyone before hands differed."""
    settled = 0.3 + 0.7 * (1 - math.exp(-skill))
    return _clip(settled + rng.uniform(-0.2, 0.2) * (1 - settled))


# ---- stone and bone
def strike(tool: Thing, target: Thing, strength: float, skill: float, maker: Maker, rng: random.Random) -> Outcome:
    """Hitting one thing with another. Hard, brittle stone struck by something harder sheds sharp flakes."""
    out = Outcome(ok=True, exertion=0.6)
    _mark(target, f"strike by {tool.kind}")
    if tool.p("hardness") < target.p("hardness") * 0.8:
        tool.set("hardness", tool.p("hardness") - 0.05)
        if tool.p("brittleness") >= 0.5:
            out.felt.append(f"치던 {tool.kind} 쪽이 이가 빠졌다")
        else:
            out.felt.append(f"{target.kind}은(는) 끄떡없고 치던 {tool.kind}만 상했다")
        return out
    if target.p("brittleness") >= 0.5 and target.p("weight") >= 0.15:
        # skill stops at each person's own ceiling (talent.py), not at one line for everyone
        quality = _clip(0.35 * min(1.5, strength) + 0.35 * skill + 0.3 + rng.uniform(-0.15, 0.15))
        count = max(1, min(3, int(target.p("weight") * 4 * quality)))
        piece_kind = target.kind if target.kind.endswith("조각") else f"{target.kind} 조각"
        for _ in range(count):
            flake = maker.derive(piece_kind, {
                "hardness": target.p("hardness"), "brittleness": target.p("brittleness"),
                "sharpness": _clip(target.p("brittleness") * target.p("hardness") * (0.4 + 0.6 * quality)),
                "weight": 0.08,
            })
            flake.history.append(f"flaked from {target.id}")
            out.made.append(flake)
        target.set("weight", target.p("weight") - 0.08 * count, cap=None)
        best = max(f.p("sharpness") for f in out.made)
        out.felt.append(f"{target.kind}에서 조각 {count}개가 떨어져 나왔다. 가장자리가 {sharp_word(best)}")
        if target.p("weight") < 0.1:
            out.used.append(target)
        return out
    if target.p("brittleness") >= 0.3 and target.p("hardness") < tool.p("hardness"):
        piece = maker.derive(target.kind if target.kind.endswith("조각") else f"{target.kind} 조각", {
            "hardness": target.p("hardness"), "brittleness": target.p("brittleness"),
            "sharpness": _clip(target.p("hardness") * 0.6), "weight": target.p("weight") / 2,
        })
        target.set("weight", target.p("weight") / 2, cap=None)
        out.made.append(piece)
        out.felt.append(f"{target.kind}이(가) 쪼개지며 날카로운 끝이 생겼다")
        return out
    out.felt.append(f"{target.kind}에 흠집만 났다")
    return out


def grind(item: Thing, abrasive: Thing, slots: int, form: str = "", steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.4 * slots)
    _mark(item, f"ground on {abrasive.kind} x{slots}")
    if abrasive.p("roughness") < 0.5 or item.p("hardness") < 0.3:
        out.felt.append("문질러도 별로 달라지지 않았다")
        return out
    before = item.p("sharpness")
    # an unsteady hand wears the edge unevenly: the same time takes it less far
    item.set("sharpness", min(item.p("hardness") + 0.1, before + 0.1 * slots * abrasive.p("roughness") * (0.5 + 0.5 * steady)))
    item.set("weight", item.p("weight") - 0.02 * slots, cap=None)
    if "뾰족" in form:
        item.shape = "뾰족함"
    surface = "표면이 고르게 매끄러워지고" if steady >= 0.5 else "군데군데만 갈려 나가고"
    out.felt.append(f"갈수록 {surface} 날이 {sharp_word(item.p('sharpness'))}")
    return out


# ---- clay, water, heat
def mix(items: list[Thing], maker: Maker, setting: Setting) -> Outcome:
    out = Outcome(ok=True, exertion=0.3)
    clay = [t for t in items if t.kind in CLAY_KINDS]
    wet = [t for t in items if t.p("water") > 0] or ([] if not setting.water_here else ["물가"])
    if clay and wet:
        for lump in clay:
            lump.set("plasticity", lump.p("plasticity") + 0.6)
            lump.set("moisture", 0.6)
            _mark(lump, "mixed with water")
        out.used.extend(t for t in items if isinstance(t, Thing) and t.p("water") > 0)
        out.felt.append("점토가 말랑하고 끈적해져 손으로 주무를 수 있게 되었다")
        return out
    things = [t for t in items if isinstance(t, Thing)]
    if len(things) < 2:
        out.ok = False
        out.felt.append("섞을 것이 모자란다")
        return out
    total = sum(max(0.01, t.p("weight")) for t in things)
    props: dict[str, float] = {}
    for thing in things:
        share = max(0.01, thing.p("weight")) / total
        for name, value in thing.props.items():
            props[name] = props.get(name, 0.0) + value * share
    props["weight"] = total
    blend = maker.derive("섞은 것", props)
    blend.history.append("mixed " + ",".join(t.kind for t in things))
    out.used.extend(things)
    out.made.append(blend)
    out.felt.append(f"{', '.join(t.kind for t in things)}이(가) 한데 섞였다")
    return out


def shape(item: Thing, form: str, steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.2)
    if item.p("plasticity") < 0.5:
        out.ok = False
        out.felt.append(f"{item.kind}은(는) 모양이 잡히지 않고 부서진다")
        return out
    for key, word in (("오목", "오목함"), ("길", "길쭉함"), ("납작", "납작함"), ("뾰족", "뾰족함"), ("둥글", "둥긂"), ("넓", "넓음")):
        if key in form:
            item.shape = word
            break
    else:
        item.shape = "빚은 모양"
    # how true the hand was stays in the clay: a lopsided hollow holds nothing, uneven walls seep once fired (heat)
    if item.shape == "오목함":
        item.set("concavity", 0.45 + 0.45 * steady)
    item.set("evenness", steady)
    _mark(item, f"shaped {item.shape}")
    if item.shape == "오목함" and item.p("concavity") < 0.5:
        out.felt.append("오목하게 빚으려 했지만 한쪽으로 기울어 우묵하게 잡히지 않았다")
        return out
    looks = {"오목함": "오목한", "길쭉함": "길쭉한", "납작함": "납작한", "뾰족함": "뾰족한", "둥긂": "둥근", "넓음": "넓적한"}
    out.felt.append(f"손으로 빚어 {looks.get(item.shape, '원하는')} 모양을 만들었다" + ("" if steady >= 0.5 else ". 두께가 고르지 않다"))
    return out


def dry(item: Thing, slots: int, setting: Setting) -> Outcome:
    out = Outcome(ok=True)
    _mark(item, f"dried x{slots}")
    if setting.raining and not setting.sheltered:
        item.set("moisture", item.p("moisture") + 0.1 * slots)
        out.felt.append(f"비를 맞아 {item.kind}이(가) 오히려 젖었다")
        return out
    rate = 0.06 * (1 + max(0.0, setting.temp) / 20) * (0.5 if setting.sheltered else 1.0)
    item.set("moisture", item.p("moisture") - rate * slots)
    if item.kind in CLAY_KINDS:
        item.set("plasticity", min(item.p("plasticity"), item.p("moisture") * 1.2))
        if item.shape and item.p("moisture") < 0.15:
            item.set("hardness", max(item.p("hardness"), 0.3))
            out.felt.append("마르면서 굳어 모양이 유지된다")
        else:
            out.felt.append("겉이 조금 말랐다")
    elif item.kind == "가죽":
        if item.p("moisture") < 0.2:
            if item.p("scraped") >= 1.0:
                item.set("insulation", 0.6)
                item.set("flexibility", 0.5)
                item.set("spoil", 0.0)
                out.felt.append("부드럽고 따뜻한 가죽이 되었다")
            else:
                item.set("flexibility", 0.1)
                out.felt.append("뻣뻣하게 굳었고 안쪽에서 냄새가 난다")
        else:
            out.felt.append("아직 축축하다")
    elif item.is_food:
        out.felt.append("쪼그라들며 말라간다" if item.p("moisture") < 0.3 else "조금 말랐다")
    else:
        out.felt.append("말랐다" if item.p("moisture") < 0.2 else "조금 말랐다")
    return out


def heat(item: Thing, slots: int, setting: Setting, maker: Maker) -> Outcome:
    """Putting something in or over a fire. What changes depends only on what the thing is and how hot and long."""
    out = Outcome(ok=True, exertion=0.1)
    if setting.fire <= 0:
        out.ok = False
        out.felt.append("불이 없다")
        return out
    intensity = setting.fire + (0.4 if setting.fire_enclosed else 0.0)
    dose = intensity * slots
    _mark(item, f"heated x{slots} at {intensity:.2f}")

    if item.kind in CLAY_KINDS:
        if item.p("fired") < 1.0 and item.p("moisture") > 0.3:
            item.shape = ""
            item.set("concavity", 0.0)
            out.felt.append("불 속에서 터지듯 갈라지고 부서졌다")
            return out
        before = item.p("fired")
        item.set("fired", before + 0.5 * dose, cap=None)
        if item.p("fired") >= 1.0:
            item.set("plasticity", 0.0)
            item.set("hardness", 0.65 + 0.2 * min(1.0, item.p("fired") - 1.0))
            # thin spots in unevenly shaped walls seep; clay shaped before hands differed counts as even
            item.set("porosity", max(0.1, 0.6 - 0.25 * item.p("fired")) + 0.2 * (1 - item.props.get("evenness", 1.0)))
            if before < 1.0:
                out.felt.append("색이 붉게 변하고 돌처럼 단단해졌다")
            else:
                out.felt.append("더 단단해진 것 같다")
        else:
            out.felt.append("뜨거워지며 조금 굳었다")
        _heat_contents(item, dose, out)
        return out

    if item.is_food:
        before = item.p("cooked")
        item.set("cooked", before + dose, cap=None)
        if before < 1.0 <= item.p("cooked"):
            item.set("toxicity", item.p("toxicity") * 0.3)
            item.set("nutrition", item.p("nutrition") * 1.2, cap=None)
            item.set("spoil", 0.0)
            item.set("moisture", item.p("moisture") * 0.7)
            item.set("parasites", 0.0)                   # heat kills cysts
            item.set("bones", item.p("bones") * 0.3)     # and softens small bones
        if item.p("cooked") >= 3.0 and before < 3.0:
            item.set("nutrition", item.p("nutrition") * 0.4, cap=None)
            out.felt.append("까맣게 타버렸다")
        elif item.p("cooked") >= 1.0:
            out.felt.append("익어서 좋은 냄새가 난다")
        else:
            out.felt.append("겉만 따뜻해졌다")
        return out

    if item.p("hardness") >= 0.6 and item.p("brittleness") >= 0.5 and item.p("fired") < 1.0 and dose >= 1.0:
        # a brittle stone that has been heated flakes more readily; nothing about that is visible except a slight colour
        item.set("brittleness", item.p("brittleness") + 0.15)
        item.set("fired", 1.0, cap=None)
        out.felt.append(f"{item.kind}의 빛깔이 조금 바뀌었다")
        return out

    if item.p("flammability") >= 0.3 and dose >= 1.0:
        out.used.append(item)
        remains = maker.make("숯" if setting.fire_enclosed and item.p("weight") >= 0.5 else "재")
        out.made.append(remains)
        out.felt.append(f"{item.kind}이(가) 타서 {'검은 덩이' if remains.kind == '숯' else '재'}만 남았다")
        return out
    out.felt.append("뜨거워졌을 뿐 달라진 것이 없다")
    return out


def _heat_contents(container: Thing, dose: float, out: Outcome) -> None:
    water = [c for c in container.contents if c.p("water") > 0]
    if not container.contents or dose < 1.0:
        return
    if container.p("porosity") >= 0.3:
        container.contents = [c for c in container.contents if c.p("water") <= 0]
        if water:
            out.felt.append("안에 든 물이 새어 나와 치익 하고 사라졌다")
        return
    if water:
        out.felt.append("안의 물이 부글부글 끓어올랐다")
    for food in container.contents:
        if food.is_food:
            before = food.p("cooked")
            food.set("cooked", max(before, 1.0) if water else before + dose, cap=None)
            if before < 1.0:
                food.set("toxicity", food.p("toxicity") * (0.15 if water else 0.3))
                food.set("nutrition", food.p("nutrition") * 1.2, cap=None)
                food.set("spoil", 0.0)
                food.set("parasites", 0.0)
                food.set("bones", food.p("bones") * 0.3)
    if water and any(f.is_food for f in container.contents):
        out.felt.append("물에 우러난 냄새가 퍼졌다")


def soak(item: Thing, slots: int, setting: Setting, has_water: bool) -> Outcome:
    out = Outcome(ok=True)
    if not has_water:
        out.ok = False
        out.felt.append("담글 물이 없다")
        return out
    _mark(item, f"soaked x{slots}")
    item.set("moisture", 1.0)
    if item.kind in CLAY_KINDS and item.p("fired") < 1.0:
        item.set("plasticity", item.p("plasticity") + 0.4)
        out.felt.append("점토가 물러졌다")
    elif item.kind == "가죽":
        item.set("flexibility", item.p("flexibility") + 0.2)
        out.felt.append("물을 먹어 부드러워졌다")
    elif item.is_food:
        if item.p("toxicity") > 0:
            item.set("toxicity", item.p("toxicity") * (0.8 ** slots))
            out.felt.append("담가둔 물이 조금 탁해졌다")
        else:
            out.felt.append("물에 불었다")
        if item.p("germination") > 0:
            item.set("germination", item.p("germination") + 0.05)
    elif item.p("fired") >= 1.0:
        out.felt.append("물에 담가도 무너지지 않는다")
    else:
        out.felt.append("젖었다")
    return out


# ---- hides, cutting, joining
def scrape(hide: Thing, tool: Thing, slots: int, steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.4 * slots)
    if tool.p("sharpness") < 0.3:
        out.ok = False
        out.felt.append("잘 긁히지 않는다")
        return out
    _mark(hide, f"scraped x{slots}")
    hide.set("scraped", hide.p("scraped") + 0.5 * slots * tool.p("sharpness") * 2 * (0.5 + 0.5 * steady), cap=None)
    out.felt.append("안쪽의 기름과 살점이 긁혀 나갔다" if hide.p("scraped") >= 1.0 else "안쪽이 조금 긁혀 나갔다")
    return out


def cutting_power(tool: Thing, strength: float) -> float:
    if tool.parts:
        edge = max(p.p("sharpness") for p in tool.parts)
        hardness = max(p.p("hardness") for p in tool.parts)
        reach = max(p.p("reach") for p in tool.parts)
        weight = sum(p.p("weight") for p in tool.parts)
    else:
        edge, hardness, reach, weight = tool.p("sharpness"), tool.p("hardness"), tool.p("reach"), tool.p("weight")
    return edge * (0.5 + hardness) * (0.5 + min(1.0, weight)) * (1 + reach) * max(0.2, strength)


def cut(item: Thing, tool: Thing, strength: float, maker: Maker) -> Outcome:
    out = Outcome(ok=True, exertion=0.4)
    power = cutting_power(tool, strength)
    resistance = item.p("hardness") * 0.8 + item.p("fiber") * 0.4 + (0.3 if item.kind.endswith("사체") else 0.0)
    if power < resistance * 0.5:
        out.ok = False
        out.felt.append(f"{item.kind}이(가) 잘리지 않는다")
        return out
    _mark(item, f"cut with {tool.kind}")
    if item.kind.endswith("사체"):
        species = item.kind[:-2].strip()
        yields = {"사슴": {"고기": 6, "가죽": 1, "뼈": 2, "힘줄": 2, "지방": 1, "뿔": 1},
                  "토끼": {"고기": 1, "가죽": 1}, "멧돼지": {"고기": 5, "가죽": 1, "뼈": 2, "지방": 2},
                  "들소": {"고기": 12, "가죽": 2, "뼈": 4, "힘줄": 4, "지방": 3, "뿔": 2}, "늑대": {"고기": 3, "가죽": 1, "뼈": 2},
                  "큰사슴": {"고기": 9, "가죽": 1, "뼈": 3, "힘줄": 2, "지방": 2, "뿔": 1}, "노루": {"고기": 3, "가죽": 1, "뼈": 1},
                  "말": {"고기": 10, "가죽": 1, "뼈": 3, "힘줄": 3, "지방": 2},
                  "원시소": {"고기": 16, "가죽": 2, "뼈": 5, "힘줄": 4, "지방": 4, "뿔": 2}}.get(species, {"고기": 2})
        efficiency = min(1.0, power / max(0.1, resistance))
        for kind, n in yields.items():
            for _ in range(max(1 if kind == "가죽" else 0, int(round(n * (0.5 + 0.5 * efficiency))))):
                out.made.append(maker.make(kind))
        out.used.append(item)
        out.felt.append(f"{species}을(를) 갈라 " + ", ".join(sorted({t.kind for t in out.made})) + "을(를) 얻었다")
        return out
    if item.p("bones") >= 0.3 and item.is_food:
        item.set("bones", 0.1)
        out.felt.append(f"{item.kind}을(를) 갈라 가시를 발라냈다")
        return out
    half = dict(item.props)
    half["weight"] = item.p("weight") / 2
    item.set("weight", item.p("weight") / 2, cap=None)
    piece = maker.derive(item.kind, half, item.shape)
    out.made.append(piece)
    out.felt.append(f"{item.kind}을(를) 둘로 잘랐다")
    return out


def bind(parts: list[Thing], binder: Thing, maker: Maker, steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.2)
    if binder.p("fiber") < 0.5:
        out.ok = False
        out.felt.append(f"{binder.kind}(으)로는 묶이지 않는다")
        return out
    if len(parts) < 2:
        out.ok = False
        out.felt.append("묶을 것이 하나뿐이다")
        return out
    tight = binder.p("fiber") * (1 - binder.p("moisture") * 0.3) * (0.6 + 0.4 * steady)
    joined = maker.derive("묶은 것", {"weight": sum(p.p("weight") for p in parts) + binder.p("weight"), "binding": tight})
    joined.parts = list(parts)
    joined.history.append(f"bound with {binder.kind}")
    out.used.extend(parts + [binder])
    out.made.append(joined)
    out.felt.append("단단히 고정되었다" if tight >= 0.6 else "묶였지만 조금 헐겁다")
    return out


def weave(fibers: list[Thing], form: str, maker: Maker, steady: float = 1.0) -> Outcome:
    out = Outcome(ok=True, exertion=0.3)
    usable = [f for f in fibers if f.p("fiber") >= 0.4 and f.p("flexibility") >= 0.4]
    if len(usable) < 3:
        out.ok = False
        out.felt.append("엮기에는 가닥이 모자라거나 뻣뻣하다")
        return out
    props = {
        "fiber": sum(f.p("fiber") for f in usable) / len(usable), "flexibility": 0.6, "porosity": 0.95,
        "weight": sum(f.p("weight") for f in usable), "insulation": 0.1 * len(usable), "flammability": 0.7,
    }
    woven = maker.derive(f"엮은 {usable[0].kind}", props)
    if "오목" in form:
        woven.shape = "오목함"
        woven.set("concavity", 0.45 + 0.25 * steady)
    elif "넓" in form or "펼" in form:
        woven.shape = "넓음"
        woven.props["mesh"] = 0.5 + 0.3 * steady   # uneven meshes let fish slip through (contest.fish)
    out.used.extend(usable)
    out.made.append(woven)
    if woven.shape == "오목함" and woven.p("concavity") < 0.5:
        out.felt.append("가닥을 엮었지만 오목하게 잡히지 않고 펑퍼짐하다")
    else:
        out.felt.append(f"가닥을 엮어 {form or '한 덩이'}을(를) 만들었다" + ("" if steady >= 0.5 else ". 코가 들쭉날쭉하다"))
    return out


# ---- trying things out
def test(thing: Thing, how: str, person: str, setting: Setting, strength: float) -> Outcome:
    """The only way to learn what cannot be seen: pour water in it, cut with it, taste it, smell it, lift it."""
    out = Outcome(ok=True)
    found = thing.tested.setdefault(person, set())
    if any(w in how for w in ("물", "붓", "담아", "새는")):
        if not (setting.water_here or thing.contents):
            out.ok = False
            out.felt.append("부어볼 물이 없다")
            return out
        found.add("water")
        if thing.p("concavity") < 0.5:
            out.felt.append("물이 그대로 흘러내린다")
        elif thing.p("porosity") < 0.3:
            out.felt.append("물을 부었더니 새지 않았다")
        else:
            out.felt.append("물을 부었더니 금방 스며 나왔다")
    elif any(w in how for w in ("베", "자르", "잘라", "긋")):
        found.add("cut")
        out.felt.append(f"베어 보니 {sharp_word(max([thing.p('sharpness')] + [p.p('sharpness') for p in thing.parts]))}")
    elif any(w in how for w in ("맛", "깨물", "핥")):
        found.add("taste")
        out.felt.append(f"맛을 보니 {taste_words(thing)}")
    elif "냄새" in how:
        found.add("smell")
        out.felt.append("시큼한 냄새가 난다" if thing.p("ferment") >= 0.3 else ("역한 냄새가 난다" if thing.p("spoil") >= 0.5 else "별 냄새가 없다"))
    elif any(w in how for w in ("두드", "눌러", "단단")):
        found.add("hard")
        out.felt.append(f"두드려 보니 {hard_word(max([thing.p('hardness')] + [p.p('hardness') for p in thing.parts]))}")
    else:
        found.add("lift")
        out.felt.append(f"들어 보니 {weight_word_for(thing)}")
    return out


def weight_word_for(thing: Thing) -> str:
    from .senses import weight_word
    return weight_word(thing.p("weight"))


# ---- time
def day_passes(thing: Thing, temp: float, sealed: bool) -> None:
    """What a day does to a thing lying somewhere: food spoils, sweet fruit shut away ferments, unscraped hides rot."""
    warmth = max(0.0, temp) / 20
    if thing.is_food and thing.p("cooked") < 3.0:
        dryness = 1.0 - thing.p("moisture")
        if sealed and thing.p("sweetness") >= 0.4 and thing.p("cooked") < 1.0:
            thing.set("ferment", thing.p("ferment") + 0.25 * (0.5 + warmth))
            thing.set("spoil", thing.p("spoil") + 0.03)
        else:
            rate = 0.2 * (0.3 + warmth) * (0.2 + thing.p("moisture")) * (0.6 if thing.p("cooked") >= 1.0 else 1.0)
            rate *= 0.3 if dryness > 0.75 else 1.0
            if thing.p("sweetness") >= 0.4 and thing.p("moisture") >= 0.5:
                thing.set("ferment", thing.p("ferment") + 0.08 * warmth)
            thing.set("spoil", thing.p("spoil") + rate, cap=None)
        if thing.p("spoil") >= 1.0:
            thing.set("toxicity", max(thing.p("toxicity"), 0.5))
            thing.set("nutrition", thing.p("nutrition") * 0.5, cap=None)
        if thing.p("germination") > 0 and thing.p("moisture") >= 0.6:
            thing.set("germination", thing.p("germination") - 0.1)
    if thing.kind == "가죽" and thing.p("scraped") < 1.0 and thing.p("moisture") >= 0.2:
        thing.set("spoil", thing.p("spoil") + 0.3 * (0.3 + warmth), cap=None)
    for content in thing.contents:
        # shut away only when the vessel both keeps air and water out and has something over its mouth
        day_passes(content, temp, sealed or (thing.p("porosity") < 0.3 and thing.p("covered") > 0))
    if thing.p("porosity") >= 0.3 and thing.contents:
        thing.contents = [c for c in thing.contents if c.p("water") <= 0]
