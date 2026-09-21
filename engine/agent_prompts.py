from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field

from . import llm_agent
from .config import SimulationConfig
from .entities import Employee
from .llm_agent import CouncilMemberResponse, TranscriptEntry, _format_transcript


class Declaration(BaseModel):
    declaration: str = Field(default="", max_length=1000)
    reasoning: str = Field(default="", max_length=600)
    next_wake_in: int = 1


class AgentVote(BaseModel):
    support_action: bool
    reasoning: str = Field(max_length=400)


def _section(title: str, lines: list[str]) -> str:
    if not lines:
        return ""
    return f"{title}\n" + "\n".join(f"- {line}" for line in lines) + "\n\n"


def _known_section(known: list[str]) -> str:
    return _section("당신이 겪었거나 전해 들은 것 (오래된 것부터):", known) or "당신이 겪었거나 전해 들은 것: 아직 없음\n\n"


def build_declaration_prompt(name: str, own_facts: list[str], org_lines: list[str], known: list[str]) -> str:
    return (
        f"당신은 {name}입니다.\n\n"
        f"{_section('당신에 대한 사실:', own_facts)}"
        f"{_section('당신이 속한 조직의 장부:', org_lines)}"
        f"{_known_section(known)}"
        "이번 차례에 하고 싶은 것을 자유롭게 말하라. 무엇이든 괜찮고, 아무것도 하지 않아도 된다. "
        "특정 상대를 가리킬 때는 그 이름을 그대로 적으라.\n"
        "declaration에 하려는 것을, reasoning에 그 이유를, "
        "next_wake_in에 몇 틱 뒤에 다시 움직일지(1 이상의 정수)를 적으라. JSON으로만 답하라."
    )


def build_agent_vote_prompt(
    name: str, org_name: str, own_facts: list[str], org_lines: list[str], known: list[str],
    proposer: str, proposal_text: str, transcript: list[TranscriptEntry] | None,
) -> str:
    return (
        f"당신은 {org_name}의 구성원 {name}입니다.\n\n"
        f"{_section('당신에 대한 사실:', own_facts)}"
        f"{_section('조직의 장부:', org_lines)}"
        f"{_known_section(known)}"
        f'{proposer}이(가) 조직에 올린 안건이 표결에 부쳐졌습니다: "{proposal_text}"\n\n'
        f"{_format_transcript(transcript)}"
        "이 안건에 찬성할지 반대할지 정하고, 그 이유를 말하라. JSON으로만 답하라."
    )


def hold_agent_meeting(
    members: list[Employee],
    build_prompt: Callable[[Employee, list[TranscriptEntry] | None], str],
    config: SimulationConfig,
    rounds: int,
    label_prefix: str,
) -> tuple[list[CouncilMemberResponse | None], list[list[CouncilMemberResponse | None]]]:
    transcript: list[TranscriptEntry] = []
    all_rounds: list[list[CouncilMemberResponse | None]] = []
    for round_num in range(1, rounds + 1):
        # members of one round cannot hear each other, so they are all asked at once
        prompts = [build_prompt(member, transcript or None) for member in members]
        votes = llm_agent.run_concurrently(
            [
                lambda prompt=prompt, member=member: llm_agent.call_llm_decision(
                    prompt, AgentVote, config, temperature=member.temperature, label=f"{label_prefix}:{member.name}",
                )
                for member, prompt in zip(members, prompts)
            ],
            config,
        )
        round_responses: list[CouncilMemberResponse | None] = [
            None if vote is None
            else CouncilMemberResponse(
                support_action=vote.support_action, disclose_to_outsiders=False, reasoning=vote.reasoning
            )
            for vote in votes
        ]
        all_rounds.append(round_responses)
        transcript = transcript + [
            (round_num, member.name, response)
            for member, response in zip(members, round_responses)
            if response is not None
        ]
    return all_rounds[-1], all_rounds
