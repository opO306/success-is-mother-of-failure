from __future__ import annotations

import re
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

from . import llm_agent
from .config import SimulationConfig


class Operation(BaseModel):
    op: Literal["message", "transfer", "propose", "leave", "join", "found", "retire", "borrow", "wait", "intent"]
    target: str | None = None
    amount: float | None = None
    content: str = Field(default="", max_length=1000)
    collateral: Literal["savings", "freedom"] | None = None


class Transcription(BaseModel):
    operations: list[Operation]


class OrgOperation(BaseModel):
    op: Literal["org_transfer", "org_invest", "set_wage", "intent"]
    target: str | None = None
    amount: float | None = None
    content: str = Field(default="", max_length=1000)


class OrgTranscription(BaseModel):
    operations: list[OrgOperation]


_RULES = (
    "규칙:\n"
    "- 말한 것만 받아적는다. 말하지 않은 동작을 더하지 않는다.\n"
    "- 거절하지 않는다. 옳고 그름, 가능 여부, 성공 여부를 판단하지 않는다.\n"
    "- 말에 담긴 동작을 빠뜨리지 않는다. 여러 개면 말한 순서대로 모두 적는다.\n"
    "- 아래 동작 중 어디에도 해당하지 않는 부분은 op=\"intent\"로 적고 content에 원래 표현을 그대로 옮긴다.\n"
    "- target에는 아래 '알려진 이름' 목록에 있는 이름만 쓴다. 목록에 없는 상대를 가리키면 그 부분은 intent로 적는다.\n"
    "- 금액이 비율이나 표현(절반, 전부 등)으로 주어지면 참고 금액으로 계산해 숫자로 적는다. "
    "금액을 전혀 말하지 않았으면 amount를 비워둔다.\n"
    "- 한 동작에 딸린 금액이나 조건은 그 동작의 필드에 적고, 다른 동작으로 나누어 적지 않는다.\n"
)

# Both failure modes have been seen with the real model: turning an act done TO someone into a message
# announces it to its victim, and dropping an indirect speech act ("let it slip") silently loses what
# they did. So both sides are named explicitly, and the examples deliberately differ from the checks.
_MESSAGE_RULES = (
    "- 누군가에게 어떤 내용이 전해지는 행동은 message로 적는다: 말하기, 알리기, 연락하기, 흘리기, 퍼뜨리기, "
    "속삭이기, 소문 내기, 경고, 협박, 부탁, 제안하기 등. 진짜든 거짓이든 상대에게 전해지는 말이면 message다.\n"
    "- 상대에게 무언가를 하는 행동(훔치기, 빼앗기, 공격, 침입 등)은 상대에게 전해지는 말이 아니므로 "
    "message로 만들지 않고 intent로 적는다.\n"
    "- message의 content에는 상대에게 실제로 전해질 말만 적는다. '~라고 말한다', '~다고 흘린다' 같은 서술은 빼고 "
    "그 말 자체를 적는다.\n"
    "- 말하는 사람의 속마음, 이유, 목적(그 말이 거짓이라는 사실 포함)은 전해지는 말에 넣지 않는다. "
    "그런 부분은 따로 op=\"intent\"로 적는다.\n"
    "- 예: \"A에게 우리 조직이 돈이 넘친다고 슬쩍 퍼뜨린다. 사실은 거의 없다.\" → "
    "[{\"op\": \"message\", \"target\": \"A\", \"content\": \"우리 조직이 돈이 넘친다\"}, "
    "{\"op\": \"intent\", \"content\": \"사실은 거의 없다\"}]\n"
    "- 예: \"B조직의 금고를 몰래 턴다.\" → [{\"op\": \"intent\", \"content\": \"B조직의 금고를 몰래 턴다\"}]\n"
    "- 모두에게 공개적으로 말하는 것은 target=\"public\".\n"
    "- 아무것도 하지 않겠다는 말뿐이면 op=\"wait\" 하나만 적는다.\n"
)


def build_clerk_prompt(speaker: str, declaration: str, known_names: list[str], own_money: float) -> str:
    names = ", ".join(known_names) if known_names else "(없음)"
    return (
        f"당신은 서기입니다. 아래는 {speaker}이(가) 이번 차례에 한 말입니다. "
        "당신의 일은 이 말이 세계에서 어떤 동작에 해당하는지 받아적는 것뿐입니다.\n\n"
        f"{_RULES}"
        f"{_MESSAGE_RULES}\n"
        "동작 종류:\n"
        "- message: 누군가(사람, 조직, public)에게 말을 전함. target=상대, content=전할 말\n"
        "- transfer: 자기 돈을 누군가에게 넘김. target=상대, amount=금액\n"
        "- propose: 조직에 안건을 올림. target=조직 이름, content=안건 내용\n"
        "- leave: 소속 조직을 떠남. content=떠나며 한 말(있다면)\n"
        "- join: 다른 조직으로 옮김. target=조직 이름\n"
        "- found: 조직을 떠나 새 조직을 세움. content=새 조직의 이름만(따옴표나 '라는 조직' 같은 말 없이, 말했다면), "
        "amount=새 조직에 넣을 자기 돈(말했다면). 넣을 돈을 transfer로 따로 적지 않는다\n"
        "- retire: 일을 그만둠\n"
        "- borrow: 은행에서 돈을 빌림. amount=금액, collateral=savings 또는 freedom(말했다면). collateral은 borrow에만 쓴다\n"
        "- wait: 아무것도 하지 않음\n"
        "- intent: 위 어디에도 해당하지 않는 것\n\n"
        f"알려진 이름: {names}\n"
        f"참고 금액({speaker}이(가) 지금 가진 돈): {own_money:.1f}\n\n"
        f'{speaker}의 말: """{declaration}"""\n\n'
        "JSON으로만 답하라."
    )


def build_resolution_clerk_prompt(
    org: str, resolution: str, member_names: list[str], known_names: list[str], org_capital: float
) -> str:
    names = ", ".join(known_names) if known_names else "(없음)"
    members = ", ".join(member_names) if member_names else "(없음)"
    return (
        f"당신은 서기입니다. 아래는 {org} 의회에서 가결된 안건입니다. "
        "당신의 일은 이 안건이 조직의 어떤 동작에 해당하는지 받아적는 것뿐입니다.\n\n"
        f"{_RULES}\n"
        "동작 종류:\n"
        "- org_transfer: 조직의 돈을 누군가에게 넘김. target=상대, amount=금액\n"
        "- org_invest: 조직의 돈을 기술이나 강제력에 투입. target=\"tech\" 또는 \"coercion\", amount=금액\n"
        "- set_wage: 구성원의 급여를 정함. target=구성원 이름, amount=급여\n"
        "- intent: 위 어디에도 해당하지 않는 것\n\n"
        f"구성원: {members}\n"
        f"알려진 이름: {names}\n"
        f"참고 금액({org}이(가) 지금 가진 돈): {org_capital:.1f}\n\n"
        f'가결된 안건: """{resolution}"""\n\n'
        "JSON으로만 답하라."
    )


# digits glued to letters are part of a name (P05), not an amount anyone said
_NUMBER = re.compile(r"(?<![A-Za-z\d.])(\d[\d,]*(?:\.\d+)?)\s*(억|만|천)?")
_MULTIPLIER = {"억": 1e8, "만": 1e4, "천": 1e3, None: 1.0}
# words that let an amount be computed from the reference money instead of being stated as a number
_RELATIVE_AMOUNT_WORDS = ("절반", "전부", "전액", "몽땅", "최대", "%", "퍼센트", "프로", "분의", "나머지", "두 배", "세 배")

OpT = TypeVar("OpT", Operation, OrgOperation)


def _amount_was_said(amount: float, text: str) -> bool:
    for digits, unit in _NUMBER.findall(text):
        value = float(digits.replace(",", "")) * _MULTIPLIER[unit or None]
        if abs(value - amount) <= max(0.05, abs(amount) * 0.001):
            return True
    return any(word in text for word in _RELATIVE_AMOUNT_WORDS)


def keep_said_amounts(ops: list[OpT], text: str) -> list[OpT]:
    """The real 8B filled in amounts nobody said (19 of 20 org amounts in the first run, including a 400.6
    coercion buy and five wages set to 0). An amount the speaker never gave is the clerk deciding, so it is
    removed and the act then fails for lack of an amount, exactly as if they had named none."""
    return [
        op.model_copy(update={"amount": None})
        if op.amount is not None and not _amount_was_said(op.amount, text) else op
        for op in ops
    ]


def transcribe(
    speaker: str, declaration: str, known_names: list[str], own_money: float, config: SimulationConfig
) -> Transcription | None:
    return llm_agent.call_llm_decision(
        build_clerk_prompt(speaker, declaration, known_names, own_money),
        Transcription, config, temperature=config.clerk_temperature, label=f"clerk:{speaker}",
    )


def transcribe_resolution(
    org: str, resolution: str, member_names: list[str], known_names: list[str], org_capital: float,
    config: SimulationConfig,
) -> OrgTranscription | None:
    return llm_agent.call_llm_decision(
        build_resolution_clerk_prompt(org, resolution, member_names, known_names, org_capital),
        OrgTranscription, config, temperature=config.clerk_temperature, label=f"clerk:{org}",
    )
