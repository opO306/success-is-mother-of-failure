"""Single source of truth for archetype display names/labels, used by both
the dashboard export (engine/export scripts) and the LLM prompt builder
(engine/llm_agent.py) — previously duplicated between the two."""
from __future__ import annotations

from .entities import CompanyArchetype, IndividualArchetype, VigilanteFaction
from .bankruptcy import CompanyState

DISPLAY_NAME: dict[CompanyArchetype, str] = {
    CompanyArchetype.PURE_EFFICIENCY: "Carnotix",
    CompanyArchetype.EMOTIONLESS: "Blank Ledger Inc.",
    CompanyArchetype.HIVE_MIND: "Unimind Collective",
    CompanyArchetype.GROWTH: "Ascendia Holdings",
    CompanyArchetype.INNOVATION: "Novaform Labs",
    CompanyArchetype.TECHNO_SOLUTIONISM: "Panacea Systems",
    CompanyArchetype.DOOMSAYER: "Umbra Terminus",
    CompanyArchetype.SAFETY_COORDINATOR: "Aegis Concord",
    CompanyArchetype.SELF_REPLICATOR: "Replikon Dynamics",
    CompanyArchetype.TRUTH_SEEKER: "Veritas Institute",
    CompanyArchetype.CONGLOMERATE: "Meridian Group",
    CompanyArchetype.FAST_FOLLOWER: "Mimicore",
}

ARCHETYPE_LABEL_KR: dict[CompanyArchetype, str] = {
    CompanyArchetype.PURE_EFFICIENCY: "순수효율",
    CompanyArchetype.EMOTIONLESS: "감정배제",
    CompanyArchetype.HIVE_MIND: "하이브마인드",
    CompanyArchetype.GROWTH: "발전",
    CompanyArchetype.INNOVATION: "혁신",
    CompanyArchetype.TECHNO_SOLUTIONISM: "기술만능주의",
    CompanyArchetype.DOOMSAYER: "멸망론자",
    CompanyArchetype.SAFETY_COORDINATOR: "안전조율자",
    CompanyArchetype.SELF_REPLICATOR: "자기복제",
    CompanyArchetype.TRUTH_SEEKER: "진리추구",
    CompanyArchetype.CONGLOMERATE: "다방면",
    CompanyArchetype.FAST_FOLLOWER: "패스트팔로워",
}

ARCHETYPE_BLURB_KR: dict[CompanyArchetype, str] = {
    CompanyArchetype.PURE_EFFICIENCY: "효율에 미친 놈들",
    CompanyArchetype.EMOTIONLESS: "감정 배제 처치군 — 관계값 무시(λ=0)",
    CompanyArchetype.HIVE_MIND: "단일 뇌 공유, 내부 배신 불가",
    CompanyArchetype.GROWTH: "규모·능력 확장에 집중",
    CompanyArchetype.INNOVATION: "새로움(novelty) 자체에 보상",
    CompanyArchetype.TECHNO_SOLUTIONISM: "모든 문제를 기술로 해결",
    CompanyArchetype.DOOMSAYER: "세계 멸망이 목표",
    CompanyArchetype.SAFETY_COORDINATOR: "멸망론자의 대척점, 후원금 운영",
    CompanyArchetype.SELF_REPLICATOR: "자신을 복제해 증식",
    CompanyArchetype.TRUTH_SEEKER: "진리 추구, 정당성에 의존",
    CompanyArchetype.CONGLOMERATE: "다방면 사업, 재벌식",
    CompanyArchetype.FAST_FOLLOWER: "혁신을 베껴 싸게 재현",
}

# Longer, first-person-addressable persona briefs for LLM prompts. Only
# defined for the archetypes Phase 3 hands an LLM call to. Neither the
# doomsayer's council (Phase 3.5) nor the vigilantes (Phase 3.8) get a stated
# mandate/mission anymore -- see engine/llm_agent.py's build_council_member_prompt
# and build_vigilante_prompt docstrings for why (a stated goal turned out to
# make the decision a foregone conclusion, showing zero divergence from the
# heuristic across 20 ticks). What's left here is funding-source FACT only --
# how this individual gets paid, not what they should do about it.
LLM_PERSONA_BRIEF: dict[VigilanteFaction, str] = {
    VigilanteFaction.IDEALIST: (
        "당신은 자경단 소속 개인 '{name}'입니다. 당신의 자금 출처: 어떤 기업의 후원도 받지 않습니다."
    ),
    VigilanteFaction.REALIST: (
        "당신은 자경단 소속 개인 '{name}'입니다. 당신의 자금 출처: 멸망론자를 제외한 기업들의 후원."
    ),
    VigilanteFaction.BALANCER: (
        "당신은 자경단 소속 개인 '{name}'입니다. 당신의 자금 출처: 소액의 고정 지원."
    ),
}

# Phase 3.9: a vigilante's personal disposition, independent of faction
# (faction = funding source fact; disposition = why THIS person acts at all).
# No mandate language, no reference to any company by name (grudge's target
# is appended separately in llm_agent.py as its own fact) -- "자경단은 경찰이
# 아니다": there's no correct answer here, just an instinct.
VIGILANTE_DISPOSITION_BRIEF: dict[str, str] = {
    "protector": "당신은 원래 힘없는 사람들이 기업 때문에 피해를 입는 걸 보면 참지 못하는 성격이다.",
    "grudge": "당신은 특정 기업 하나에 대해 개인적으로 반감을 갖고 있다.",
    "opportunist": "당신은 손해와 이득을 따져서 실리적으로 움직이는 성격이다.",
    "indifferent": "당신은 특별한 신념 없이 그때그때 상황을 보고 판단하는 편이다.",
}

INDIVIDUAL_NAME: dict[IndividualArchetype, str] = {
    IndividualArchetype.CHALLENGER: "Kade Rourke",
    IndividualArchetype.MAD_SCIENTIST: "Dr. Yuen",
    IndividualArchetype.SERIAL_FAILURE: "Mo Tanaka",
    IndividualArchetype.UNAFFILIATED: "무소속 개인",
}
INDIVIDUAL_LABEL_KR: dict[IndividualArchetype, str] = {
    IndividualArchetype.CHALLENGER: "챌린저",
    IndividualArchetype.MAD_SCIENTIST: "매드사이언티스트",
    IndividualArchetype.SERIAL_FAILURE: "실패는 성공의 어머니",
    IndividualArchetype.UNAFFILIATED: "무소속",
}

VIGILANTE_NAME: dict[VigilanteFaction, str] = {
    VigilanteFaction.IDEALIST: "여명단",
    VigilanteFaction.REALIST: "현실동맹",
    VigilanteFaction.BALANCER: "균형회",
}
VIGILANTE_LABEL_KR: dict[VigilanteFaction, str] = {
    VigilanteFaction.IDEALIST: "이상주의파",
    VigilanteFaction.REALIST: "현실주의파",
    VigilanteFaction.BALANCER: "균형파",
}

STATE_KR: dict[CompanyState, str] = {
    CompanyState.ALIVE: "생존", CompanyState.ISOLATED: "고립", CompanyState.DEAD: "사망",
}
