"""Carrying out a person's steps slot by slot: moving along roads, doing things where they stand."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .. import recorder as recording
from . import body as physiology
from . import economy
from .clerk import Step
from .config import SLOT_INDEX
from .model import Letter, Notice, Org, Person
from .world import World

DURATION_OPS = frozenset({"work", "craft", "research", "train", "sleep", "guard"})
CONTEST_OPS = frozenset({"steal", "attack", "rob", "sabotage"})
MOVE_OPS = frozenset({"go", "flee"})


@dataclass
class Cursor:
    steps: list[Step] = field(default_factory=list)
    index: int = 0
    remaining: int | None = None
    started: bool = False
    path: list[str] | None = None
    edge_left: int = 0

    def replace_rest(self, steps: list[Step]) -> None:
        self.steps = list(steps) + self.steps[self.index:]
        self.index = 0
        self.remaining = None
        self.started = False
        self.path = None
        self.edge_left = 0


@dataclass
class SlotIntent:
    instants: list[Step] = field(default_factory=list)
    contests: list[Step] = field(default_factory=list)
    main: str | None = None
    main_step: Step | None = None
    first_slot_of_main: bool = False
    arrive_at: str | None = None


def advance(
    world: World, person: Person, cursor: Cursor, slot_index: int,
    duration_ops: frozenset[str] = DURATION_OPS, contest_ops: frozenset[str] = CONTEST_OPS,
    on_fail: Callable[[World, Person, Step, str, str | None], None] | None = None,
) -> SlotIntent:
    """Shared by every world built on slots and roads; each world passes which of its ops take time or meet a body,
    and how a walk that cannot start is told to the walker."""
    fail = on_fail or (lambda w, p, s, reason, place: _fail(w, p, s, f"{reason}: {place}"))
    intent = SlotIntent()
    while cursor.index < len(cursor.steps):
        step = cursor.steps[cursor.index]
        if cursor.remaining is None and cursor.path is None and step.slot and SLOT_INDEX[step.slot] > slot_index:
            break  # waiting for the time they said
        if step.op in MOVE_OPS:
            if cursor.path is None:
                destination = step.target or (person.home if step.op == "flee" else None)
                if not destination or destination not in world.map.places:
                    fail(world, person, step, "모르는 곳", destination)
                    cursor.index += 1
                    continue
                if destination not in person.known_places:
                    fail(world, person, step, "가는 길을 모름", destination)
                    cursor.index += 1
                    continue
                route = world.map.route(person.location, destination)
                if route is None:
                    fail(world, person, step, "길이 없음", destination)
                    cursor.index += 1
                    continue
                cursor.path = route[0]
                cursor.edge_left = world.map.neighbors(person.location).get(cursor.path[0], 0) if cursor.path else 0
            while cursor.path and cursor.edge_left == 0:
                world.arrive(person, cursor.path.pop(0))
                cursor.edge_left = world.map.neighbors(person.location).get(cursor.path[0], 0) if cursor.path else 0
            if not cursor.path:
                cursor.path = None
                cursor.index += 1
                continue
            intent.main = "travel"
            intent.main_step = step
            cursor.edge_left -= 1
            if cursor.edge_left == 0:
                intent.arrive_at = cursor.path.pop(0)
                if not cursor.path:
                    cursor.path = None
                    cursor.index += 1
            break
        if step.op in duration_ops:
            if cursor.remaining is None:
                cursor.remaining = max(1, step.slots or 1)
                intent.first_slot_of_main = True
            intent.main = step.op
            intent.main_step = step
            cursor.remaining -= 1
            if cursor.remaining == 0:
                cursor.remaining = None
                cursor.index += 1
            break
        if step.op in contest_ops:
            intent.contests.append(step)
        else:
            intent.instants.append(step)
        cursor.index += 1
    return intent


def record(world: World, person: Person, step: Step, slot: str, ok: bool, detail: str) -> None:
    recorder = recording.active()
    if recorder is not None:
        recorder.write("actions", {
            "day": world.day, "slot": slot, "person": person.name, "place": person.location,
            "step": step.model_dump(), "ok": ok, "detail": detail,
        })
    verb = step.op if not step.content else f"{step.op}({step.content[:40]})"
    world.log(person.name, f"{slot} {person.location}: {verb} → {'성공' if ok else '실패'}: {detail}")


def _fail(world: World, person: Person, step: Step, detail: str, slot: str = "") -> None:
    record(world, person, step, slot, False, detail)


def execute_main(world: World, person: Person, intent: SlotIntent, slot: str) -> None:
    step = intent.main_step
    if step is None or intent.main in ("travel", "sleep", "guard"):
        return
    if intent.main == "work":
        ok, detail = economy.extract(world, person, step.good, step.for_org)
    elif intent.main == "craft":
        if not intent.first_slot_of_main:
            return
        ok, detail = economy.craft(world, person, step.good, step.qty, step.for_org)
    elif intent.main == "research":
        ok, detail = economy.research(world, person, step.for_org)
    else:  # train
        person.body.trained_today += 1
        ok, detail = True, "몸을 단련함"
    record(world, person, step, slot, ok, detail)


def execute_instant(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    handler = _HANDLERS.get(step.op)
    ok, detail = handler(world, person, step, slot) if handler else (True, step.content)
    record(world, person, step, slot, ok, detail)
    return ok, detail


# ---- handlers
def _eat(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    good = step.good or "식량"
    qty = step.qty or 1.0
    if economy.holding(person.inventory, good) < qty:
        return False, f"{good}이(가) 모자람"
    if good not in physiology.FOOD_VALUE:
        return False, f"{good}은(는) 먹을 수 없음"
    economy._add(person.inventory, good, -qty)
    physiology.eat(person.body, good, qty)
    if good in physiology.DRUGS:
        physiology.use(person.body, good, world.config)
    return True, f"{good} {qty:g} 먹음"


def _use(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    if step.good in ("증기기관", "전신"):
        return economy.install(world, person, step.good, step.for_org)
    if not step.good or economy.holding(person.inventory, step.good) < 1:
        return False, f"{step.good}이(가) 없음"
    economy._add(person.inventory, step.good, -1)
    return True, physiology.use(person.body, step.good, world.config)


def _install(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    if step.good not in ("증기기관", "전신"):
        return False, f"설치할 수 없는 물건: {step.good}"
    return economy.install(world, person, step.good, step.for_org)


def _give(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    if not step.target:
        return False, "누구에게 줄지 말하지 않음"
    receiver = world.person(step.target)
    if receiver is not None and receiver.name in world.busy:
        return False, f"{step.target}이(가) 이곳에 없음"
    ok, detail = economy.give(world, person, step.target, step.good, step.qty, step.amount)
    if ok:
        purpose = f" ({step.content})" if step.content else ""
        if receiver is not None:
            world.tell(receiver.name, f"{person.name}이(가) {person.location}에서 당신에게 {detail}을(를) 줌{purpose}", source=person.name, slot=slot)
        recorder = recording.active()
        if recorder is not None:
            recorder.write("payments", {
                "day": world.day, "slot": slot, "from": person.name, "to": step.target, "what": detail, "for": step.content,
            })
    return ok, detail


def _take(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    dead = world.people.get(step.target) if step.target else None
    if dead is not None and not dead.alive:
        return False, "시신에서 가져가는 것은 steal로"
    return economy.take_or_store(world, person, step.op, step.target, step.good, step.qty, step.amount)


def _talk(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    content = step.content.strip()
    if step.target == "은행":
        if person.location != world.bank.place:
            return False, "은행에 있지 않음"
        world.tell(person.name, economy.bank_terms(world, person), incoming=False, slot=slot)
        return True, "은행에 물음"
    if not content:
        return False, "전할 말이 없음"
    listeners = world.awake_at(person.location, exclude={person.name})
    # "shouting in the market" written as target=시장 is still speaking to whoever stands there
    if step.target in (None, "", "여기", "모두", person.location) or step.target in world.map.places:
        if step.target not in (None, "", "여기", "모두", person.location):
            return False, f"{step.target}에 있지 않음"
        for listener in listeners:
            world.tell(listener.name, f"{person.name}이(가) {person.location}에서 모두에게 말함: {content}", source=person.name, slot=slot)
        return True, f"그 자리 {len(listeners)}명에게"
    org = world.org(step.target)
    if org is not None:
        members = [p for p in listeners if p.name in org.members]
        if not members:
            return False, f"{org.name} 사람이 곁에 없음"
        for member in members:
            world.tell(member.name, f"{person.name}이(가) {org.name}에 말함: {content}", source=person.name, slot=slot)
        return True, f"{org.name} 사람 {len(members)}명에게"
    target = next((p for p in listeners if p.name == step.target), None)
    if target is None:
        return False, f"{step.target}이(가) 곁에 없거나 자고 있음"
    world.tell(target.name, f"{person.name}이(가) {person.location}에서 당신에게 말함: {content}", source=person.name, slot=slot)
    return True, step.target


def _note(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    carrier = next((p for p in world.awake_at(person.location, exclude={person.name}) if p.name == step.target), None)
    if carrier is None:
        return False, f"쪽지를 맡길 {step.target}이(가) 곁에 없음"
    if not step.recipient or not step.content.strip():
        return False, "받을 사람이나 내용이 없음"
    carrier.letters.append(Letter(person.name, step.recipient, step.content.strip(), world.day))
    world.tell(carrier.name, f"{person.name}이(가) {step.recipient}에게 전해 달라며 쪽지를 맡김: {step.content.strip()}", source=person.name, slot=slot)
    return True, f"{carrier.name}에게 맡김"


def _deliver(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    recipient = next((p for p in world.awake_at(person.location, exclude={person.name}) if p.name == step.target), None)
    letters = [l for l in person.letters if l.recipient == step.target]
    if not letters:
        return False, f"{step.target}에게 갈 쪽지가 없음"
    if recipient is None:
        return False, f"{step.target}이(가) 곁에 없음"
    for letter in letters:
        world.tell(recipient.name, f"{letter.sender}이(가) 보낸 쪽지를 {person.name}이(가) 전해줌: {letter.content}", source=letter.sender, slot=slot)
    person.letters = [l for l in person.letters if l not in letters]
    return True, f"쪽지 {len(letters)}장"


def _post(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    place = world.map.places[person.location]
    if place.kind != "시장" or not step.content.strip():
        return False, "시장이 아니거나 붙일 글이 없음"
    place.notices.append(Notice(person.name, step.content.strip(), world.day))
    return True, "게시판에 붙임"


def _telegraph(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    here = world.map.places[person.location]
    there = world.map.places.get(step.target or "")
    if not here.telegraph or there is None or not there.telegraph:
        return False, "전신이 닿지 않음"
    there.notices.append(Notice(person.name, f"(전신) {step.content.strip()}", world.day))
    return True, f"{there.name}으로 보냄"


def _market(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    if step.op == "cancel":
        return economy.cancel_orders(world, person, step.good)
    return economy.post_order(world, person, step.op, step.good, step.qty, step.price, slot)


def _propose(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    from ..entities import Proposal

    content = step.content.strip()
    org = world.org(step.target) or world.org_of(person)
    if not content or org is None:
        return False, "안건이나 조직이 없음"
    if person.name in org.members:
        org.agenda.append(Proposal(person.name, content, world.day))
        return True, f"{org.name}에 안건"
    if person.location != org.building:
        return False, f"{org.name}의 건물에 있지 않음"
    for member in world.awake_at(person.location, exclude={person.name}):
        if member.name in org.members:
            world.tell(member.name, f"{person.name}이(가) {org.name}에 제안함: {content}", source=person.name, slot=slot)
    return True, f"{org.name}에 바깥에서 제안"


def _join(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    org = world.org(step.target)
    if org is None or person.location != org.building:
        return False, f"{step.target}의 건물에 있지 않음"
    if person.name not in org.applicants:
        org.applicants.append(person.name)
    for member in world.awake_at(person.location, exclude={person.name}):
        if member.name in org.members:
            world.tell(member.name, f"{person.name}이(가) {org.name}에 들어오고 싶다고 함", source=person.name, slot=slot)
    return True, f"{org.name}에 들어오고 싶다고 함"


def leave_org(world: World, person: Person) -> None:
    org = world.org_of(person)
    if org is not None and person.name in org.members:
        org.members.remove(person.name)
    if org is not None:
        economy.end_contracts(world, person.name, org.name)
    person.org = None


def _leave(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    org = world.org_of(person)
    if org is None:
        return False, "소속이 없음"
    leave_org(world, person)
    return True, f"{org.name}을(를) 떠남"


def _found(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    base = step.content.strip().strip("'\"“”‘’「」『』") or f"{person.name}의 조직"
    name, n = base, 2
    while name in world.orgs or name in world.people or name in world.map.places:
        name, n = f"{base}-{n}", n + 1
    stake = step.amount or 0.0
    if stake > person.money:
        return False, "넣을 주화가 모자람"
    leave_org(world, person)
    person.money -= stake
    world.orgs[name] = Org(name=name, building=person.home, money=stake, tech=person.tech, members=[person.name])
    person.org = name
    world.acquaintances.setdefault(person.name, set()).add(name)
    return True, f"{name}을(를) 세움(주화 {stake:g}, 건물: {person.home})"


def _hire(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    target = next((p for p in world.awake_at(person.location, exclude={person.name}) if p.name == step.target), None)
    if target is None:
        return False, f"{step.target}이(가) 곁에 없음"
    ok, detail = economy.offer_job(world, person.name, target.name, step.amount, step.qty)
    if ok:
        world.offers[-1].told = True
        world.tell(target.name, f"{person.name}이(가) 당신에게 일자리를 제안함: {detail}", source=person.name, slot=slot)
    return ok, detail


def _accept(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    return economy.accept_job(world, person, step.target)


def _issue(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    return economy.issue_notes(person.inventory, person.name, step.qty)


def _redeem(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    return economy.redeem_notes(world, person, step.target, step.qty)


def _bank(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    return (economy.borrow if step.op == "borrow" else economy.repay)(world, person, step.amount)


def _noop(world: World, person: Person, step: Step, slot: str) -> tuple[bool, str]:
    return True, step.content


_HANDLERS = {
    "eat": _eat, "use": _use, "install": _install, "give": _give, "take": _take, "store": _take,
    "talk": _talk, "note": _note, "deliver": _deliver, "post": _post, "telegraph": _telegraph,
    "buy": _market, "sell": _market, "cancel": _market,
    "propose": _propose, "join": _join, "leave": _leave, "found": _found, "hire": _hire, "accept": _accept,
    "issue": _issue, "redeem": _redeem, "borrow": _bank, "repay": _bank,
    "wait": _noop, "intent": _noop,
}
