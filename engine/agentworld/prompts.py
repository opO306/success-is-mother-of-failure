"""What a person is shown: only their own facts and what reached them. No roles, no era, no bank terms."""
from __future__ import annotations

from pydantic import BaseModel, Field

from . import body as physiology
from .config import SLOTS
from .world import World

DISPOSITION_BRIEF = {
    "protector": "당신은 원래 힘없는 사람이 힘센 자에게 당하는 걸 보면 참지 못하는 성격이다.",
    "grudge": "당신은 {target}에 대해 개인적으로 반감을 갖고 있다.",
    "opportunist": "당신은 손해와 이득을 따져서 실리적으로 움직이는 성격이다.",
    "indifferent": "당신은 특별한 신념 없이 그때그때 상황을 보고 판단하는 편이다.",
}


class DayDeclaration(BaseModel):
    plan: str = Field(default="", max_length=1200)
    reasoning: str = Field(default="", max_length=600)
    same_as_yesterday: bool = False


class Reaction(BaseModel):
    response: str = Field(default="", max_length=600)
    reasoning: str = Field(default="", max_length=400)


def _bag(bag: dict[str, float]) -> str:
    return ", ".join(f"{good} {qty:g}" for good, qty in sorted(bag.items()) if qty > 1e-9) or "없음"


def facts(world: World, name: str) -> list[str]:
    person = world.people[name]
    c = world.config
    lines = [
        f"지금 있는 곳: {person.location}",
        f"집: {person.home}",
        "몸: " + "; ".join(physiology.felt(person.body, c)),
        f"가진 주화: {person.money:g}",
        f"지니고 있는 것: {_bag(person.inventory)}",
        f"집에 둔 것: {_bag(world.map.places[person.home].stash.get(person.name, {}))}",
        f"소속: {person.org or '없음'}",
    ]
    for contract in world.contracts:
        if contract.worker == name:
            owed = f", 제대로 못 받은 급여일 {contract.unpaid}번" if contract.unpaid else ""
            lines.append(
                f"일 계약: {contract.employer}에서 {contract.every_days}일마다 {contract.wage:g} "
                f"(다음 급여일 {contract.next_pay_day}일째{owed})"
            )
        elif contract.employer == name:
            lines.append(f"당신이 고용한 사람: {contract.worker}, {contract.every_days}일마다 {contract.wage:g}")
    for offer in world.offers:
        if offer.worker == name and offer.told:
            lines.append(f"받은 일자리 제안: {offer.employer}, {offer.every_days}일마다 {offer.wage:g}")
    for loan in world.bank.loans:
        if loan.borrower == name and not loan.closed:
            lines.append(f"갚아야 할 빚: 은행에 {loan.outstanding:.1f} ({loan.due_day}일째 만기)")
    for letter in person.letters:
        lines.append(f"맡아 둔 쪽지: {letter.sender}이(가) {letter.recipient}에게 보내는 것")
    if person.disposition:
        lines.append(DISPOSITION_BRIEF[person.disposition].format(target=person.grudge_target or "누군가"))
    return lines


def org_lines(world: World, name: str) -> list[str]:
    person = world.people[name]
    org = world.org_of(person)
    if org is None:
        return []
    lines = [
        f"조직: {org.name}, 건물: {org.building}",
        f"주화: {org.money:g}, 기술: {org.tech:.1f}",
        f"창고: {_bag(world.map.places[org.building].stash.get(org.name, {}))}",
        f"구성원: {', '.join(org.members)}",
    ]
    if org.applicants:
        lines.append(f"들어오고 싶다고 한 사람: {', '.join(org.applicants)}")
    if org.agenda:
        lines.append(f"아직 표결되지 않은 안건: {len(org.agenda)}건 (건물에 구성원 절반 이상이 모이면 표결)")
    lines.extend(f"최근 결의: {r}" for r in org.resolutions[-3:])
    return lines


def known_places(world: World, name: str) -> list[str]:
    person = world.people[name]
    lines = []
    homes: dict[int, list[str]] = {}
    for place in sorted(person.known_places):
        if place == person.location:
            continue
        route = world.map.route(person.location, place)
        if route is None:
            continue
        if world.map.places[place].kind == "집" and place != person.home:
            # a neighbour's house is known, but a list of twenty houses would drown out every other place
            homes.setdefault(route[1], []).append(place[: -len("의 집")])
            continue
        lines.append(f"{place}: {route[1]}칸")
    for cost, owners in sorted(homes.items()):
        lines.append(f"집이 어딘지 아는 사람 ({cost}칸, 'OO의 집'): {', '.join(owners)}")
    return lines


def known_lines(world: World, name: str) -> list[str]:
    knowledge = world.knowledge.get(name)
    return [e.text for e in knowledge.recent(world.config.knowledge_prompt_window)] if knowledge else []


def _section(title: str, lines: list[str]) -> str:
    return f"{title}\n" + "\n".join(f"- {line}" for line in lines) + "\n\n" if lines else ""


def plan_prompt(world: World, name: str) -> str:
    return (
        f"당신은 {name}입니다. 오늘은 {world.day}일째입니다. 하루는 {'·'.join(SLOTS)}으로 흘러갑니다.\n\n"
        f"{_section('당신에 대한 사실:', facts(world, name))}"
        f"{_section('당신이 속한 조직의 장부:', org_lines(world, name))}"
        f"{_section('당신이 아는 곳과 지금 있는 곳에서 가는 데 걸리는 시간(칸):', known_places(world, name))}"
        f"{_section('당신이 겪었거나 전해 들은 것 (오래된 것부터):', known_lines(world, name)) or '당신이 겪었거나 전해 들은 것: 아직 없음' + chr(10) + chr(10)}"
        "오늘 하루를 어떻게 보낼지 자유롭게 말하라. 언제 어디서 무엇을 할지, 누구를 만날지, 쉴지 말지 모두 당신이 정한다. "
        "특정 상대나 장소를 가리킬 때는 이름을 그대로 적으라. 어제와 똑같이 보내려면 same_as_yesterday를 true로 하라.\n"
        "plan에 오늘의 계획을, reasoning에 그 이유를 적으라. JSON으로만 답하라."
    )


def reaction_prompt(world: World, name: str, slot: str, situation: str) -> str:
    person = world.people[name]
    brief = [line for line in facts(world, name) if line.startswith(("지금 있는 곳", "몸", "가진 주화", "지니고 있는 것"))]
    return (
        f"당신은 {name}입니다. 지금은 {world.day}일째 {slot}, 당신은 {person.location}에 있습니다.\n\n"
        f"{_section('당신에 대한 사실:', brief)}"
        f"{_section('당신이 겪었거나 전해 들은 것 (최근):', known_lines(world, name)[-8:])}"
        f"지금 이 순간 일어나고 있는 일: {situation}\n\n"
        "이 순간 어떻게 하겠는가? 무엇이든 괜찮고 아무것도 하지 않아도 된다. "
        "response에 할 행동이나 할 말을, reasoning에 이유를 적으라. JSON으로만 답하라."
    )
