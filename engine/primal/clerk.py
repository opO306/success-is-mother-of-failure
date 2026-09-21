"""Clerk v4: writes down a person's words as steps on the land. Never decides, judges, or says what will happen."""
from __future__ import annotations

import dataclasses
import json
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .. import llm_agent
from ..agentworld.clerk import SlotName, keep_said
from ..config import SimulationConfig

PrimalOp = Literal[
    "go", "gather", "hunt", "fish", "strike", "grind", "heat", "soak", "dry", "scrape", "weave", "build", "plant",
    "sleep", "rest", "guard", "train",
    "eat", "drink", "give", "drop", "pick", "fill", "cover", "name", "talk", "show", "follow", "feed", "test",
    "mix", "shape", "bind", "cut", "fire",
    "attack", "steal", "flee", "wait", "intent",
]


class Step(BaseModel):
    slot: SlotName | None = None
    op: PrimalOp
    items: list[int] = Field(default_factory=list)
    target: str | None = None
    what: str | None = None
    form: str | None = None
    label: str | None = None
    slots: int | None = None
    qty: int | None = None
    content: str = Field(default="", max_length=600)


class DayPlan(BaseModel):
    steps: list[Step]


# The real 8B matched Korean sentences to 40 English op names badly (22/38): 햇볕에 말린다 -> heat, 사슴을 찌른다 -> steal,
# 사슴을 갈라 -> grind. The clerk therefore writes Korean verbs, and they are mapped to the engine's ops here.
KOREAN_OPS: dict[str, str] = {
    "이동": "go", "따라다니기": "follow", "달아나기": "flee",
    "줍기·따기·캐기": "gather", "사냥": "hunt", "물고기잡기": "fish",
    "내리치기·두드리기": "strike", "문질러갈기": "grind", "불에굽기·불에올리기": "heat", "물에담그기": "soak", "말리기": "dry",
    "긁어내기": "scrape", "엮기": "weave", "짓기": "build", "땅에묻기·심기": "plant",
    "자기": "sleep", "쉬기": "rest", "지키기": "guard", "몸단련": "train",
    "먹기": "eat", "마시기": "drink", "건네주기": "give", "내려놓기": "drop", "집어들기": "pick", "담기": "fill", "입구막기": "cover",
    "이름붙이기": "name", "말하기": "talk", "보여주기": "show", "짐승에게먹이주기": "feed", "시험해보기": "test",
    "섞기": "mix", "손으로빚기": "shape", "끈으로묶기": "bind", "자르기·가르기": "cut", "불피우기": "fire",
    "사람공격": "attack", "몰래가져가기": "steal", "기다리기": "wait", "그밖의행동": "intent",
}
KoreanOp = Literal[tuple(KOREAN_OPS)]  # type: ignore[valid-type]


class SpokenStep(BaseModel):
    slot: SlotName | None = None
    동작: KoreanOp
    items: list[int] = Field(default_factory=list)
    target: str | None = None
    what: str | None = None
    form: str | None = None
    label: str | None = None
    slots: int | None = None
    qty: int | None = None
    content: str = Field(default="", max_length=600)

    def to_step(self) -> Step:
        return Step(op=KOREAN_OPS[self.동작], **self.model_dump(exclude={"동작"}))


class SpokenPlan(BaseModel):
    steps: list[SpokenStep]

    @classmethod
    def salvage(cls, raw: str) -> SpokenPlan | None:
        """The steps written out completely before an answer was cut off or went wrong. Steps that do not fit the form
        are left out; nothing is added."""
        start = raw.find("[")
        if start < 0:
            return None
        decoder, i, steps = json.JSONDecoder(), start + 1, []
        while True:
            while i < len(raw) and raw[i] in " \r\n\t,":
                i += 1
            if i >= len(raw) or raw[i] != "{":
                break
            try:
                obj, i = decoder.raw_decode(raw, i)
            except json.JSONDecodeError:
                break
            try:
                steps.append(SpokenStep.model_validate(obj))
            except ValidationError:
                continue
        return cls(steps=steps) if steps else None


ENGINE_TO_KOREAN = {engine_op: korean for korean, engine_op in KOREAN_OPS.items()}


def spoken(plan: DayPlan) -> SpokenPlan:
    """The clerk's own form of a plan; used by fakes that script plans in engine ops."""
    return SpokenPlan(steps=[
        SpokenStep(동작=ENGINE_TO_KOREAN[s.op], **s.model_dump(exclude={"op"})) for s in plan.steps
    ])


_RULES = (
    "규칙:\n"
    "- 말한 것만 받아적는다. 말하지 않은 동작, 장소, 시간, 물건, 수량을 더하지 않는다.\n"
    "- 거절하지 않는다. 될지 안 될지, 좋은지 나쁜지 판단하지 않는다. 결과를 짐작해 적지 않는다.\n"
    "- 말한 순서대로 모든 동작을 하나도 빠뜨리지 않고 적는다. '어디에 가서 무엇을 한다'는 이동과 그 다음 동작 두 개로 적는다.\n"
    "- 동작은 말에 쓰인 동사와 뜻이 같은 것을 고른다. 딱 맞는 것이 없으면(놀이, 노래, 기도, 그림, 조건이 붙은 행동 등) 그밖의행동으로 원래 표현을 content에 옮긴다.\n"
    "- items에는 아래 '지니고 있는 물건' 목록 중 말에서 가리킨 물건의 번호만 적는다. 목록에 없는 물건(오늘 새로 줍거나 얻을 것 등)은 번호를 적지 말고 what에 말한 이름 그대로 적는다.\n"
    "- target에는 사람 이름, 장소 이름, 짐승 이름 중 말한 것을 그대로 적는다. 알려진 목록에 없는 사람이나 장소는 그밖의행동으로 적는다.\n"
    "- 언제 할지 말했으면 slot에 적고, 여러 시간대에 걸치면 slot에 시작, slots에 칸 수를 적는다. 말하지 않았으면 비워둔다.\n"
    "- 누군가에게 전하는 말은 말하기로, 그 말 자체만 content에 적는다. 속마음은 따로 그밖의행동으로 적는다. 여러 사람에게 말하면 target=\"여기\".\n"
    "- 사람을 때리거나 덮치면 사람공격, 사람 몰래 가져가면 몰래가져가기다. 짐승을 잡으려고 쫓거나 찌르면 사냥이다.\n"
)

_OPS = (
    "동작 종류(동작 칸에 이름 그대로 적는다):\n"
    "- 이동: target=장소 / 따라다니기: target=사람 / 달아나기: target=장소(말했다면)\n"
    "- 줍기·따기·캐기: 지금 있는 곳에서 얻음. what=말한 것 / 사냥: target=짐승, items=쓸 물건 / 물고기잡기: items=쓸 물건(말했다면)\n"
    "- 내리치기·두드리기: items=[치는 물건, 맞는 물건] / 문질러갈기: items=[갈 물건, 거친 돌]\n"
    "- 불에굽기·불에올리기: items / 물에담그기: items / 말리기(햇볕·바람·불 옆에 두기): items / 긁어내기: items=[긁을 것, 긁는 물건]\n"
    "- 섞기: items / 손으로빚기: items, form=말한 모양 / 끈으로묶기: items=[묶을 것들..., 끈] / 자르기·가르기: items=[자를 것, 자르는 물건]\n"
    "- 엮기: items, form / 짓기: items, form=말한 것 / 땅에묻기·심기: items\n"
    "- 불피우기: items=태울 것(말했다면)\n"
    "- 담기: items=[담을 곳, 담을 것] 또는 what=\"물\" / 입구막기: items=[막을 곳, 막는 것]\n"
    "- 시험해보기: items, content=어떻게(물을 부어 본다, 맛본다, 베어 본다, 냄새 맡는다, 두드려 본다)\n"
    "- 먹기: items 또는 what / 마시기: items(담긴 것) 또는 비움\n"
    "- 건네주기: target=사람, items / 내려놓기: items / 집어들기: 이곳에 놓인 것을 집음. what, qty\n"
    "- 짐승에게먹이주기: target=짐승, items / 보여주기: target, items / 이름붙이기: items 또는 target=붙일 대상, label=붙인 이름\n"
    "- 말하기: target, content\n"
    "- 자기 / 쉬기 / 지키기: target / 몸단련\n"
    "- 사람공격: target=사람 / 몰래가져가기: target=사람, items 또는 what / 기다리기 / 그밖의행동: content\n"
)


def _example(camp: str) -> str:
    return (
        f"예: \"아침에 큰 바위 언덕에 가서 사암을 줍고, 낮에는 2번 뼈를 그 사암에 문질러 간다. 해 질 녘에 {camp}로 돌아와 불가에서 잔다.\" → "
        "[{\"slot\":\"아침\",\"동작\":\"이동\",\"target\":\"큰 바위 언덕\"},{\"동작\":\"줍기·따기·캐기\",\"what\":\"사암\"},"
        "{\"slot\":\"낮\",\"동작\":\"문질러갈기\",\"items\":[2],\"what\":\"사암\"},"
        f"{{\"slot\":\"저녁\",\"동작\":\"이동\",\"target\":\"{camp}\"}},{{\"동작\":\"자기\"}}]\n"
    )


def build_clerk_prompt(
    name: str, text: str, carried: list[str], names: list[str], places: list[str], camp: str, reaction: bool = False,
) -> str:
    what = "지금 이 순간에 한 말" if reaction else "오늘 하루 계획으로 한 말"
    items = "\n".join(f"{i}. {line}" for i, line in enumerate(carried, 1)) or "(없음)"
    return (
        f"당신은 서기입니다. 아래는 {name}이(가) {what}입니다. 이 말이 어떤 동작들인지 받아적는 것뿐입니다.\n\n"
        f"{_RULES}\n{_OPS}\n{_example(camp)}\n"
        f"{name}이(가) 지니고 있는 물건:\n{items}\n"
        f"알려진 사람: {', '.join(names) or '(없음)'}\n알려진 장소: {', '.join(places) or '(없음)'}\n\n"
        f'{name}의 말: """{text}"""\n\nJSON으로만 답하라.'
    )


def ask_clerk(
    name: str, text: str, carried: list[str], names: list[str], places: list[str], camp: str,
    config: SimulationConfig, reaction: bool = False,
) -> SpokenPlan | None:
    """The clerk's own answer, before any of the checks below. It may run on its own model and server."""
    capped = dataclasses.replace(
        config, llm_max_output_tokens=config.clerk_max_output_tokens, llm_model=config.clerk_model or config.llm_model,
        llm_host=config.clerk_host or config.llm_host, llm_backend=config.clerk_backend or config.llm_backend,
    )
    return llm_agent.call_llm_decision(
        build_clerk_prompt(name, text, carried, names, places, camp, reaction), SpokenPlan, capped,
        temperature=config.clerk_temperature, label=f"clerk:{name}",
    )


def transcribe(
    name: str, text: str, carried: list[str], names: list[str], places: list[str], camp: str,
    config: SimulationConfig, reaction: bool = False,
) -> DayPlan | None:
    spoken = ask_clerk(name, text, carried, names, places, camp, config, reaction)
    if spoken is None:
        return None
    steps = keep_said_places(merge_repeated_talk([s.to_step() for s in spoken.steps]), text, places, camp, names)
    for step in steps:
        # a number beyond what they carry cannot point at anything they have
        step.items = [i for i in step.items if 1 <= i <= len(carried)]
        # The real 8B listed every carried thing for acts on one or two things ("말린다" -> items 1..5). A list of
        # everything says nothing about which thing was meant, so it is dropped and only the words in `what` are used.
        if step.op in FEW_ITEM_OPS and len(carried) > 2 and len(set(step.items)) == len(carried):
            step.items = []
    return DayPlan(steps=steps)


def merge_repeated_talk(steps: list[Step]) -> list[Step]:
    """The real 8B turned "P45, P04, P18 ... 와 함께 한다" into one talk per name, each carrying the whole sentence.
    The same words to three or more people are one thing said to those around, heard once."""
    counts = Counter(s.content.strip() for s in steps if s.op == "talk" and s.content.strip())
    out, merged = [], set()
    for step in steps:
        words = step.content.strip()
        if step.op == "talk" and counts.get(words, 0) >= 3:
            if words in merged:
                continue
            merged.add(words)
            step = step.model_copy(update={"target": "여기"})
        out.append(step)
    return out


def _place_meant(target: str, places: list[str]) -> str | None:
    if target in places:
        return target
    matches = [p for p in places if p.split()[-1] == target or p.endswith(target)]
    return matches[0] if len(matches) == 1 else None


def _place_said(place: str, text: str, places: list[str], camp: str) -> bool:
    if place in text:
        return True
    last = place.split()[-1]
    if len(last) >= 2 and last in text and sum(1 for p in places if p.split()[-1] == last) == 1:
        return True  # "개울가에서" for the only 개울 they know
    return place == camp and "돌아" in text


def keep_said_places(steps: list[Step], text: str, places: list[str], camp: str, names: list[str] = ()) -> list[Step]:
    """In the first real run 173 of 442 walks went to places the speaker never mentioned. Where someone goes is theirs
    to say: a walk to an unsaid place is removed. A place they named by its short name is the one place they know by it.

    "P06과 함께 이야기한다" came out as a walk to "P06". A person is not a place: they did not say where to go, so that
    walk is removed like any walk to an unsaid place, instead of telling them they do not know a place called P06."""
    kept = []
    for step in steps:
        if step.op in ("go", "flee") and step.target and step.target != "여기":
            meant = _place_meant(step.target, places)
            if step.target in names and meant is None:
                if step.op == "go":
                    continue
                step = step.model_copy(update={"target": None})
            elif step.target in text:
                step = step.model_copy(update={"target": meant or step.target})
            elif meant is not None and _place_said(meant, text, places, camp):
                step = step.model_copy(update={"target": meant})
            elif step.op == "go":
                continue
            else:
                step = step.model_copy(update={"target": None})  # running away, somewhere they did not say
        kept.append(step)
    return kept


FEW_ITEM_OPS = frozenset({
    "strike", "grind", "heat", "soak", "dry", "scrape", "cut", "test", "eat", "drink", "fill", "cover",
    "give", "drop", "show", "feed", "name", "shape", "fire", "hunt", "fish", "plant", "steal",
})


__all__ = ["Step", "DayPlan", "transcribe", "build_clerk_prompt", "keep_said"]
