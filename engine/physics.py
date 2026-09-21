from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import recorder as recording
from .clerk import Operation, OrgOperation
from .council import CouncilOutcome, MemberResult
from .credit import issue_loan, quoted_rate
from .entities import Company, Employee, IndividualAgent, IndividualArchetype, Proposal, Resources, Vigilante
from .exits import MemberExitEvent, apply_member_exits
from .knowledge import Knowledge


@dataclass
class OpResult:
    actor: str
    op: str
    ok: bool
    detail: str


def person_names(world: Any) -> list[str]:
    names = [e.name for c in world.companies if c.alive for e in c.employees]
    names += [v.name for v in world.vigilantes if v.alive]
    names += [i.name for i in world.individuals if i.alive]
    return names


def find_person(world: Any, name: str | None) -> Employee | Vigilante | IndividualAgent | None:
    if not name:
        return None
    for company in world.companies:
        if company.alive:
            for employee in company.employees:
                if employee.name == name:
                    return employee
    for person in [*world.vigilantes, *world.individuals]:
        if person.alive and person.name == name:
            return person
    return None


def employer_of(world: Any, name: str) -> Company | None:
    return next((c for c in world.companies if c.alive and any(e.name == name for e in c.employees)), None)


def find_company(world: Any, name: str | None) -> Company | None:
    if not name:
        return None
    return next((c for c in world.companies if c.alive and c.name == name), None)


def money_of(person: Employee | Vigilante | IndividualAgent) -> float:
    return person.savings if isinstance(person, Employee) else person.resources.capital


def add_money(person: Employee | Vigilante | IndividualAgent, delta: float) -> None:
    if isinstance(person, Employee):
        person.savings += delta
    else:
        person.resources.capital += delta


def _knows(world: Any, actor: str, name: str | None) -> bool:
    # you can only reach someone you have actually heard of; IDs being guessable is not a way in
    return bool(name) and name in world.acquaintances.get(actor, set())


def tell(world: Any, person: str, tick: int, text: str, source: str | None = None, incoming: bool = True) -> None:
    world.knowledge.setdefault(person, Knowledge()).add(tick, text, source=source, incoming=incoming)
    known = world.acquaintances.setdefault(person, set())
    if source and source != person:
        known.add(source)
    # hearing a name is how someone comes to know that person or org exists
    for company in world.companies:
        if company.name in text:
            known.add(company.name)
    for other in person_names(world):
        if other != person and other in text:
            known.add(other)
    recorder = recording.active()
    if recorder is not None:
        recorder.write("deliveries", {"tick": tick, "to": person, "text": text, "source": source, "incoming": incoming})


def tell_members(
    world: Any, company: Company, tick: int, text: str, source: str | None = None,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> None:
    for employee in list(company.employees):
        if employee.name not in exclude:
            tell(world, employee.name, tick, text, source=source)


def tell_everyone(
    world: Any, tick: int, text: str, source: str | None = None, exclude: set[str] | frozenset[str] = frozenset()
) -> None:
    for name in person_names(world):
        if name not in exclude:
            tell(world, name, tick, text, source=source)


def _message(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    content = op.content.strip()
    if not content:
        return OpResult(actor, "message", False, "전할 말이 없음"), []
    if op.target == "public":
        tell_everyone(world, tick, f"{actor}이(가) 공개적으로 말함: {content}", source=actor, exclude={actor})
        tell(world, actor, tick, f"당신은 공개적으로 말함: {content}", incoming=False)
        return OpResult(actor, "message", True, "public"), []
    company = find_company(world, op.target)
    person = None if company is not None or op.target == actor else find_person(world, op.target)
    if company is None and person is None:
        tell(world, actor, tick, f"당신은 {op.target}에게 말하려 했으나 닿지 않음", incoming=False)
        return OpResult(actor, "message", False, f"대상 없음: {op.target}"), []
    if not _knows(world, actor, op.target):
        tell(world, actor, tick, f"당신은 {op.target}에게 말하려 했으나 닿지 않음", incoming=False)
        return OpResult(actor, "message", False, f"모르는 상대: {op.target}"), []
    if company is not None:
        tell_members(world, company, tick, f"{actor}이(가) {company.name}에 말함: {content}", source=actor, exclude={actor})
        tell(world, actor, tick, f"당신은 {company.name}에 말함: {content}", incoming=False)
        return OpResult(actor, "message", True, company.name), []
    tell(world, op.target, tick, f"{actor}이(가) 당신에게 말함: {content}", source=actor)
    tell(world, actor, tick, f"당신은 {op.target}에게 말함: {content}", incoming=False)
    return OpResult(actor, "message", True, op.target), []


def _transfer(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    amount = op.amount
    if amount is None or amount <= 0:
        return OpResult(actor, "transfer", False, "금액 없음"), []
    sender = find_person(world, actor)
    company = find_company(world, op.target)
    recipient = None if company is not None or op.target == actor else find_person(world, op.target)
    if company is None and recipient is None:
        tell(world, actor, tick, f"당신은 {op.target}에게 {amount:.1f}을 보내려 했으나 닿지 않음", incoming=False)
        return OpResult(actor, "transfer", False, f"대상 없음: {op.target}"), []
    if not _knows(world, actor, op.target):
        tell(world, actor, tick, f"당신은 {op.target}에게 {amount:.1f}을 보내려 했으나 닿지 않음", incoming=False)
        return OpResult(actor, "transfer", False, f"모르는 상대: {op.target}"), []
    if money_of(sender) < amount:
        tell(world, actor, tick, f"당신은 {op.target}에게 {amount:.1f}을 보내려 했으나 가진 돈이 모자람", incoming=False)
        return OpResult(actor, "transfer", False, "잔고 부족"), []
    add_money(sender, -amount)
    if company is not None:
        company.resources.capital += amount
        tell_members(world, company, tick, f"{actor}이(가) {company.name}에 {amount:.1f}을 보냄", source=actor, exclude={actor})
    else:
        add_money(recipient, amount)
        tell(world, op.target, tick, f"{actor}이(가) 당신에게 {amount:.1f}을 보냄", source=actor)
    tell(world, actor, tick, f"당신은 {op.target}에게 {amount:.1f}을 보냄", incoming=False)
    return OpResult(actor, "transfer", True, f"{op.target} {amount:.1f}"), []


def _propose(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    content = op.content.strip()
    own = employer_of(world, actor)
    company = find_company(world, op.target) if op.target else own
    if not content or company is None:
        return OpResult(actor, "propose", False, f"안건이나 조직 없음: {op.target}"), []
    if company is own:
        company.agenda.append(Proposal(proposer=actor, text=content, tick=tick))
        tell_members(world, company, tick, f"{actor}이(가) {company.name}에 안건을 올림: {content}", source=actor, exclude={actor})
        tell(world, actor, tick, f"당신은 {company.name}에 안건을 올림: {content}", incoming=False)
        return OpResult(actor, "propose", True, company.name), []
    if not _knows(world, actor, company.name):
        return OpResult(actor, "propose", False, f"모르는 조직: {company.name}"), []
    # only members can put items on an org's agenda; from outside it is just something said to them
    tell_members(world, company, tick, f"{actor}이(가) {company.name}에 제안함: {content}", source=actor)
    tell(world, actor, tick, f"당신은 {company.name}에 제안함: {content}", incoming=False)
    return OpResult(actor, "propose", True, f"{company.name}(외부 제안)"), []


_EXIT_ACTIONS = {"leave": "leave", "join": "join_other_org", "found": "found_new_org", "retire": "retire"}


_NAME_QUOTES = "'\"‘’“”「」『』"


def _requested_org_name(op: Operation) -> str:
    # the clerk usually puts a new org's name in content, but sometimes only in target
    if op.op != "found":
        return ""
    return (op.content.strip() or (op.target or "").strip()).strip(_NAME_QUOTES).strip()


def _unique_org_name(world: Any, base: str) -> str:
    taken = {c.name for c in world.companies} | set(person_names(world))
    name, n = base, 2
    while name in taken:
        name, n = f"{base}-{n}", n + 1
    return name


def _exit(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    company = employer_of(world, actor)
    if op.op == "join" and not _knows(world, actor, op.target):
        tell(world, actor, tick, f"당신은 {op.target}에 들어가려 했으나 닿지 않음", incoming=False)
        return OpResult(actor, "join", False, f"모르는 조직: {op.target}"), []
    if company is None:
        target = find_company(world, op.target) if op.op == "join" else None
        if target is None:
            detail = f"대상 없음: {op.target}" if op.op == "join" else "소속 조직 없음"
            return OpResult(actor, op.op, False, detail), []
        said = f": {op.content.strip()}" if op.content.strip() else ""
        tell_members(world, target, tick, f"{actor}이(가) {target.name}에 들어오려 함{said}", source=actor)
        tell(world, actor, tick, f"당신은 {target.name}에 들어가려 함", incoming=False)
        # no org-side hiring exists yet; the org only learns that they tried
        return OpResult(actor, "join", False, "비구성원 합류는 아직 없음(조직에는 전달됨)"), []

    employee = find_person(world, actor)
    before = company.name
    outcome = CouncilOutcome(
        proceeds=False, disclosed=False, votes_for=0, votes_total=0,
        member_results=[
            MemberResult(
                name=actor, support=False, disclosed=False, reasoning="", source="declaration",
                personal_action=_EXIT_ACTIONS[op.op],
                personal_target=op.target if op.op == "join" else None,
                # money only moves when the person names an amount; silence is not "all of it"
                personal_stake=(op.amount if op.amount is not None else 0.0) if op.op == "found" else None,
                personal_intent=op.content,
            )
        ],
    )
    events, new_companies, new_individuals = apply_member_exits(company, outcome, world.companies)
    if not events:
        return OpResult(actor, op.op, False, "처리되지 않음"), []
    event = events[0]
    if event.blocked_reason:
        tell(world, actor, tick, f"당신은 {before}을(를) 떠나려 했으나 그럴 수 없었음: {event.blocked_reason}", incoming=False)
        return OpResult(actor, op.op, False, event.blocked_reason), events

    # the same person walks out, with what they actually have (debt included), not a renamed husk
    for individual in new_individuals:
        individual.name = actor
        individual.resources.capital = employee.savings
        individual.temperature = employee.temperature
    if op.op == "retire":
        new_individuals.append(IndividualAgent(
            name=actor, archetype=IndividualArchetype.UNAFFILIATED,
            resources=Resources(capital=employee.savings), temperature=employee.temperature,
        ))
    world.individuals.extend(new_individuals)
    requested = _requested_org_name(op)
    for founded in new_companies:
        if requested:
            founded.name = _unique_org_name(world, requested)
        world.companies.append(founded)
        world.acquaintances.setdefault(actor, set()).add(founded.name)
        event.became = founded.name

    left = "일을 그만둠" if op.op == "retire" else "떠남"
    tell_members(world, company, tick, f"{actor}이(가) {before}에서 {left}", source=actor)
    if op.op == "join":
        target = find_company(world, event.became)
        tell(world, actor, tick, f"당신은 {before}을(를) 떠나 {event.became}에 들어감", incoming=False)
        if target is not None:
            world.acquaintances.setdefault(actor, set()).update(e.name for e in target.employees if e.name != actor)
            tell_members(world, target, tick, f"{actor}이(가) {target.name}에 들어옴", source=actor, exclude={actor})
    elif op.op == "found":
        stake = new_companies[0].resources.capital if new_companies else 0.0
        tell(world, actor, tick, f"당신은 {before}을(를) 떠나 {event.became}을(를) 세움(자기 돈 {stake:.1f} 투입)", incoming=False)
    elif op.op == "retire":
        tell(world, actor, tick, f"당신은 {before}에서 일을 그만둠", incoming=False)
    else:
        tell(world, actor, tick, f"당신은 {before}을(를) 떠남", incoming=False)
    if not company.employees:
        company.alive = False
    return OpResult(actor, op.op, True, event.became or ""), events


def _borrow(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    company = employer_of(world, actor)
    employee = find_person(world, actor)
    if company is None or not isinstance(employee, Employee):
        tell(world, actor, tick, "당신은 은행에서 돈을 빌리려 했으나 응답을 받지 못함", incoming=False)
        return OpResult(actor, "borrow", False, "비구성원 대출은 아직 없음"), []
    if op.collateral is None:
        tell(world, actor, tick, "당신은 은행에서 돈을 빌리려 했으나 담보를 정하지 않아 성립하지 않음", incoming=False)
        return OpResult(actor, "borrow", False, "담보 미지정"), []
    rate = quoted_rate(
        world.config, unpaid_streak=employee.unpaid_streak, savings=employee.savings,
        has_income=company.resources.capital > 0,
    )
    loan, event = issue_loan(
        world.bank, borrower=actor, borrower_kind="employee", principal=op.amount or 0.0,
        collateral=op.collateral, rate=rate, tick=tick, config=world.config,
    )
    if loan is None:
        tell(world, actor, tick, f"당신은 은행에서 {op.amount or 0.0:.1f}을 빌리려 했으나 거절됨({event.detail})", incoming=False)
        return OpResult(actor, "borrow", False, event.detail), []
    employee.savings += loan.principal
    tell(
        world, actor, tick,
        f"당신은 은행에서 {loan.principal:.1f}을 빌림(이자 분기당 {loan.rate:.0%}, {loan.due_tick}분기에 상환, 담보={loan.collateral})",
        incoming=False,
    )
    return OpResult(actor, "borrow", True, f"{loan.principal:.1f}"), []


def _noop(world: Any, actor: str, op: Operation, tick: int) -> tuple[OpResult, list[MemberExitEvent]]:
    return OpResult(actor, op.op, True, op.content), []


_PERSON_HANDLERS = {
    "message": _message, "transfer": _transfer, "propose": _propose,
    "leave": _exit, "join": _exit, "found": _exit, "retire": _exit,
    "borrow": _borrow, "wait": _noop, "intent": _noop,
}


def resolve_person_ops(
    world: Any, actor: str, ops: list[Operation], tick: int
) -> tuple[list[OpResult], list[MemberExitEvent]]:
    results: list[OpResult] = []
    exits: list[MemberExitEvent] = []
    # the name someone gave an org they just founded -> the name it actually got, so money they then
    # send "to it" by that name can't land in an older org that already had the name
    founded_as: dict[str, str] = {}
    for op in ops:
        if op.target in founded_as:
            op = op.model_copy(update={"target": founded_as[op.target]})
        handler = _PERSON_HANDLERS.get(op.op)
        if handler is None:
            results.append(OpResult(actor, op.op, False, "알 수 없는 동작"))
            continue
        result, events = handler(world, actor, op, tick)
        results.append(result)
        exits.extend(events)
        requested = _requested_org_name(op)
        if result.ok and requested:
            founded_as[requested] = result.detail
    return results, exits


def _org_transfer(world: Any, company: Company, op: OrgOperation, tick: int) -> OpResult:
    amount = op.amount
    if amount is None or amount <= 0:
        return OpResult(company.name, "org_transfer", False, "금액 없음")
    target_company = find_company(world, op.target)
    if target_company is company:
        return OpResult(company.name, "org_transfer", False, "자기 조직으로 송금")
    recipient = None if target_company is not None else find_person(world, op.target)
    member_knows = any(_knows(world, e.name, op.target) for e in company.employees)
    if (target_company is None and recipient is None) or not member_knows:
        tell_members(world, company, tick, f"{company.name}이(가) 의결에 따라 {op.target}에 {amount:.1f}을 보내려 했으나 닿지 않음")
        return OpResult(company.name, "org_transfer", False, f"대상 없음 또는 모르는 상대: {op.target}")
    if company.resources.capital < amount:
        tell_members(world, company, tick, f"{company.name}이(가) 의결에 따라 {op.target}에 {amount:.1f}을 보내려 했으나 조직의 돈이 모자람")
        return OpResult(company.name, "org_transfer", False, "조직 자본 부족")
    company.resources.capital -= amount
    if target_company is not None:
        target_company.resources.capital += amount
        tell_members(world, target_company, tick, f"{company.name}이(가) {target_company.name}에 {amount:.1f}을 보냄")
    else:
        add_money(recipient, amount)
        tell(world, op.target, tick, f"{company.name}이(가) 당신에게 {amount:.1f}을 보냄")
    tell_members(world, company, tick, f"{company.name}이(가) 의결에 따라 {op.target}에 {amount:.1f}을 보냄")
    return OpResult(company.name, "org_transfer", True, f"{op.target} {amount:.1f}")


_INVEST_FIELDS = {"tech": "tech", "기술": "tech", "coercion": "coercion", "강제력": "coercion"}


def _org_invest(world: Any, company: Company, op: OrgOperation, tick: int) -> OpResult:
    field_name = _INVEST_FIELDS.get((op.target or "").strip().lower())
    amount = op.amount
    if field_name is None or amount is None or amount <= 0:
        return OpResult(company.name, "org_invest", False, f"투입처나 금액 없음: {op.target}")
    label = "기술" if field_name == "tech" else "강제력"
    if company.resources.capital < amount:
        tell_members(world, company, tick, f"{company.name}이(가) 의결에 따라 {amount:.1f}을 {label}에 투입하려 했으나 조직의 돈이 모자람")
        return OpResult(company.name, "org_invest", False, "조직 자본 부족")
    rate = world.config.invest_tech_rate if field_name == "tech" else world.config.invest_coercion_rate
    gained = amount * rate
    company.resources.capital -= amount
    setattr(company.resources, field_name, getattr(company.resources, field_name) + gained)
    tell_members(world, company, tick, f"{company.name}이(가) 의결에 따라 {amount:.1f}을 {label}에 투입함({label} +{gained:.2f})")
    return OpResult(company.name, "org_invest", True, f"{label} +{gained:.2f}")


def _set_wage(world: Any, company: Company, op: OrgOperation, tick: int) -> OpResult:
    member = next((e for e in company.employees if e.name == op.target), None)
    if member is None or op.amount is None or op.amount < 0:
        return OpResult(company.name, "set_wage", False, f"구성원이나 금액 없음: {op.target}")
    member.wage = op.amount
    tell(world, member.name, tick, f"{company.name}의 의결로 당신의 계약 급여가 분기당 {op.amount:.1f}로 정해짐")
    tell_members(
        world, company, tick, f"{company.name}이(가) 의결에 따라 {member.name}의 급여를 {op.amount:.1f}로 정함",
        exclude={member.name},
    )
    return OpResult(company.name, "set_wage", True, f"{member.name} {op.amount:.1f}")


def _org_intent(world: Any, company: Company, op: OrgOperation, tick: int) -> OpResult:
    return OpResult(company.name, op.op, True, op.content)


_ORG_HANDLERS = {"org_transfer": _org_transfer, "org_invest": _org_invest, "set_wage": _set_wage, "intent": _org_intent}


def resolve_org_ops(world: Any, company: Company, ops: list[OrgOperation], tick: int) -> list[OpResult]:
    results: list[OpResult] = []
    for op in ops:
        handler = _ORG_HANDLERS.get(op.op)
        results.append(
            handler(world, company, op, tick) if handler is not None
            else OpResult(company.name, op.op, False, "알 수 없는 동작")
        )
    return results
