"""The clerk writes down what a person said as steps the world can carry out. It never decides, judges or fills in."""
from __future__ import annotations

import re
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

from .. import llm_agent
from ..clerk import _amount_was_said
from ..config import SimulationConfig

SlotName = Literal["새벽", "아침", "낮", "오후", "저녁", "밤"]
PersonOp = Literal[
    "go", "work", "craft", "research", "train", "sleep", "guard", "install",
    "eat", "use", "give", "take", "store",
    "talk", "note", "deliver", "post", "telegraph",
    "buy", "sell", "cancel",
    "steal", "attack", "rob", "sabotage", "flee",
    "propose", "join", "leave", "found", "hire", "accept", "issue", "redeem", "borrow", "repay",
    "wait", "intent",
]
OrgOp = Literal["pay", "give_goods", "set_wage", "hire", "fire", "issue", "intent"]


class Step(BaseModel):
    slot: SlotName | None = None
    op: PersonOp
    target: str | None = None
    good: str | None = None
    qty: float | None = None
    price: float | None = None
    amount: float | None = None
    slots: int | None = None
    recipient: str | None = None
    for_org: bool = False
    content: str = Field(default="", max_length=600)


class DayPlan(BaseModel):
    steps: list[Step]


class OrgStep(BaseModel):
    op: OrgOp
    target: str | None = None
    good: str | None = None
    qty: float | None = None
    amount: float | None = None
    content: str = Field(default="", max_length=600)


class OrgPlan(BaseModel):
    steps: list[OrgStep]


_RULES = (
    "규칙:\n"
    "- 말한 것만 받아적는다. 말하지 않은 동작, 장소, 시간, 수량, 금액을 더하지 않는다.\n"
    "- 거절하지 않는다. 옳고 그름, 가능 여부, 성공 여부를 판단하지 않는다. 불가능해 보여도 말한 대로 적는다.\n"
    "- 말한 순서대로 모든 동작을 적는다. 어디에도 해당하지 않는 부분은 op=\"intent\"로 원래 표현을 content에 옮긴다.\n"
    "- target, recipient에는 아래 '알려진 이름'이나 '알려진 장소'에 있는 이름만 쓴다. 목록에 없는 상대나 장소는 intent로 적는다.\n"
    "- 언제 할지 말했으면 slot에 그 시간대를 적고, 말하지 않았으면 비워둔다. 여러 시간대에 걸쳐 하면 slot에 시작 시간대, slots에 칸 수를 적는다.\n"
    "- 수량·금액·가격을 말하지 않았으면 비워둔다. 아래 사실 목록에 있는 숫자는 그 사람이 원래 가진 것이지 요구한 수량이 아니다.\n"
    "- 누군가에게 전해지는 말은 talk로, 그 말 자체만 content에 적는다. 속마음이나 그 말이 거짓이라는 사실은 따로 intent로 적는다.\n"
    "- 상대 몰래 가져가기는 steal, 힘으로 빼앗기는 rob, 때리거나 덮치기는 attack이다. 이것들은 상대에게 하는 말이 아니다.\n"
    "- 한 문장에 동작이 여러 개면 하나도 빠뜨리지 않는다. '어디에 가서 무엇을 한다'는 go와 그 다음 동작 두 개로 적는다.\n"
)

_OPS = (
    "동작 종류:\n"
    "- go: 장소로 이동. target=장소\n"
    "- work: 지금 있는 곳에서 자원을 캐거나 거둠. good=자원(식량·물고기·석탄·철광석·목재·약초), for_org=조직을 위해서면 true\n"
    "- craft: 물건을 만듦. good=물건 이름, qty=만들 개수(말했다면), for_org\n"
    "- research: 기술을 연구함. for_org\n"
    "- train: 몸을 단련함\n"
    "- sleep: 잠을 잠\n"
    "- guard: 장소나 사람이나 물건을 지킴. target=지킬 장소·사람\n"
    "- install: 증기기관이나 전신을 지금 있는 곳에 설치. good\n"
    "- eat: 먹음. good, qty / use: 약·술·아편 등을 씀. good\n"
    "- give: 곁에 있는 상대에게 건넴. target, good+qty 또는 amount(주화), content=무엇의 대가인지(말했다면)\n"
    "- take / store: 자기 집이나 자기 조직 창고에서 꺼내거나 넣음. target=조직 이름(조직 창고일 때), good+qty 또는 amount\n"
    "- talk: 말함. target=곁에 있는 사람, 또는 \"여기\"(그 자리의 모두), 또는 \"은행\". content=전할 말\n"
    "- note: 쪽지를 누군가에게 맡겨 전하게 함. target=맡을 사람, recipient=받을 사람, content\n"
    "- deliver: 맡은 쪽지를 전함. target=받을 사람\n"
    "- post: 시장 게시판에 글을 붙임. content / telegraph: 전신으로 보냄. target=장소, content\n"
    "- buy / sell: 시장에서 사거나 팜. good, qty, price=개당 주화 / cancel: 시장에 걸어둔 주문을 거둠. good\n"
    "- steal: 몰래 가져감. target=주인(사람·조직), good, qty / rob: 힘으로 빼앗음. target, good+qty 또는 amount\n"
    "- attack: 공격함. target / sabotage: 남의 물건을 망가뜨림. target=주인, good, qty / flee: 도망침. target=장소(말했다면)\n"
    "- propose: 조직에 안건을 올림. target=조직, content / join: 조직에 들어가고 싶다고 함. target=조직\n"
    "- leave: 조직을 떠남 / found: 새 조직을 세움. content=이름, amount=넣을 주화\n"
    "- hire: 곁에 있는 사람에게 일자리를 제안. target, amount=급여, qty=며칠마다 / accept: 받은 일자리 제안을 받아들임. target=제안한 쪽\n"
    "- issue: 자기 이름의 지폐를 발행. qty / redeem: 남의 지폐를 주화로 바꿔 달라고 함. target=발행한 쪽, qty\n"
    "- borrow / repay: 은행에서 빌리거나 갚음. amount\n"
    "- wait: 아무것도 하지 않음 / intent: 위 어디에도 해당하지 않는 것\n"
)

def _example(home: str) -> str:
    # the real 8B copied a placeholder like "(그 사람의 집)" into target, so the example uses the speaker's real home
    return (
        "예: \"새벽에 철광에 가서 낮부터 오후까지 철광석을 캔다. 저녁에 시장에 들러 칼 한 자루를 8에 판다. 밤엔 집에 가서 잔다.\" → "
        "[{\"slot\":\"새벽\",\"op\":\"go\",\"target\":\"철광\"},{\"slot\":\"낮\",\"op\":\"work\",\"good\":\"철광석\",\"slots\":2},"
        "{\"slot\":\"저녁\",\"op\":\"go\",\"target\":\"시장\"},{\"op\":\"sell\",\"good\":\"칼\",\"qty\":1,\"price\":8},"
        f"{{\"slot\":\"밤\",\"op\":\"go\",\"target\":\"{home}\"}},{{\"op\":\"sleep\"}}]\n"
    )


def build_plan_clerk_prompt(
    name: str, text: str, facts: list[str], known_names: list[str], known_places: list[str], reaction: bool = False,
) -> str:
    what = "지금 이 순간에 한 말" if reaction else "오늘 하루 계획으로 한 말"
    return (
        f"당신은 서기입니다. 아래는 {name}이(가) {what}입니다. 이 말이 세계에서 어떤 동작들에 해당하는지 받아적는 것뿐입니다.\n\n"
        f"{_RULES}\n{_OPS}\n{_example(f'{name}의 집')}\n"
        f"{name}에 대한 사실:\n" + "\n".join(f"- {line}" for line in facts) + "\n"
        f"알려진 이름: {', '.join(known_names) or '(없음)'}\n"
        f"알려진 장소: {', '.join(known_places) or '(없음)'}\n\n"
        f'{name}의 말: """{text}"""\n\nJSON으로만 답하라.'
    )


def build_resolution_clerk_prompt(org: str, text: str, members: list[str], known_names: list[str], facts: list[str]) -> str:
    return (
        f"당신은 서기입니다. 아래는 {org} 의회에서 가결된 안건입니다. 조직의 어떤 동작에 해당하는지 받아적는 것뿐입니다.\n\n"
        f"{_RULES}\n"
        "동작 종류:\n"
        "- pay: 조직의 주화를 줌. target, amount\n"
        "- give_goods: 조직 창고의 물건을 줌. target, good, qty\n"
        "- set_wage: 구성원의 급여를 정함. target=구성원, amount\n"
        "- hire: 일자리를 제안. target, amount=급여, qty=며칠마다\n"
        "- fire: 구성원을 내보냄. target\n"
        "- issue: 조직 이름의 지폐를 발행. qty\n"
        "- intent: 위 어디에도 해당하지 않는 것\n\n"
        f"{org}에 대한 사실:\n" + "\n".join(f"- {line}" for line in facts) + "\n"
        f"구성원: {', '.join(members) or '(없음)'}\n알려진 이름: {', '.join(known_names) or '(없음)'}\n\n"
        f'가결된 안건: """{text}"""\n\nJSON으로만 답하라.'
    )


def transcribe_plan(
    name: str, text: str, facts: list[str], known_names: list[str], known_places: list[str],
    config: SimulationConfig, reaction: bool = False,
) -> DayPlan | None:
    return llm_agent.call_llm_decision(
        build_plan_clerk_prompt(name, text, facts, known_names, known_places, reaction),
        DayPlan, config, temperature=config.clerk_temperature, label=f"clerk:{name}",
    )


def transcribe_resolution(
    org: str, text: str, members: list[str], known_names: list[str], facts: list[str], config: SimulationConfig,
) -> OrgPlan | None:
    return llm_agent.call_llm_decision(
        build_resolution_clerk_prompt(org, text, members, known_names, facts),
        OrgPlan, config, temperature=config.clerk_temperature, label=f"clerk:{org}",
    )


_KOREAN_COUNTS = {
    "한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3, "네": 4, "넷": 4, "다섯": 5,
    "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10, "스무": 20, "스물": 20,
}
_COUNTERS = "개|장|자루|병|그릇|포대|섬|근|끼|번|칸|명|일|닢|푼|냥|덩이|묶음|마리|벌|채|대|알|권|잔|줌|되|말"
_KOREAN_COUNT_PATTERN = re.compile(rf"(?<![가-힣])({'|'.join(sorted(_KOREAN_COUNTS, key=len, reverse=True))})\s*(?:{_COUNTERS})")
# "식량 하나를", "둘씩": a count word followed by a particle. 열 is left out there because "열이 난다" is a fever.
_STANDALONE_COUNT = re.compile(
    r"(?<![가-힣])(?:(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉)(?:[을를이가에씩만도은는과와](?![가-힣])|(?![가-힣]))|(열)(?![가-힣]))"
)


def _said(value: float, text: str) -> bool:
    if _amount_was_said(value, text):
        return True
    words = _KOREAN_COUNT_PATTERN.findall(text) + [a or b for a, b in _STANDALONE_COUNT.findall(text)]
    for word in words:
        if abs(_KOREAN_COUNTS[word] - value) < 1e-9:
            return True
    return False


StepT = TypeVar("StepT", Step, OrgStep)
# a quantity nobody said is the clerk deciding; consumption and making default to one portion instead
_QTY_MUST_BE_SAID = {"give", "take", "store", "buy", "sell", "issue", "redeem", "give_goods", "sabotage"}


# The real 8B wrote "빚 20을 갚는다" as borrow. Where money changes direction, the word itself has to be there.
_MONEY_VERBS = {"borrow": ("빌", "대출", "꾸어", "꿔"), "repay": ("갚", "상환")}


def keep_said(steps: list[StepT], text: str) -> list[StepT]:
    kept: list[StepT] = []
    for step in steps:
        verbs = _MONEY_VERBS.get(step.op)
        if verbs and not any(word in text for word in verbs):
            kept.append(step.model_copy(update={"op": "intent", "amount": None, "content": step.content or text[:200]}))
            continue
        update: dict = {}
        for field_name in ("amount", "price"):
            value = getattr(step, field_name, None)
            if value is not None and not _said(value, text):
                update[field_name] = None
        if step.qty is not None and step.op in _QTY_MUST_BE_SAID and not _said(step.qty, text):
            update["qty"] = None
        kept.append(step.model_copy(update=update) if update else step)
    return kept
