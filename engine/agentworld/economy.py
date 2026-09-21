"""Work, goods, markets, notes, the bank and wage contracts. Arithmetic only: who does what is never decided here."""
from __future__ import annotations

from dataclasses import dataclass

from .. import recorder as recording
from . import body as physiology
from .model import Contract, Loan, Offer, Order, Person, Trade
from .world import World, note_issuer, note_name

RESOURCES = ("식량", "물고기", "석탄", "철광석", "목재", "약초")


@dataclass(frozen=True)
class Recipe:
    inputs: dict[str, float]
    tech: float
    output: float = 1.0


RECIPES: dict[str, Recipe] = {
    "철": Recipe({"철광석": 2, "석탄": 1}, tech=3),
    "도구": Recipe({"철": 1, "목재": 1}, tech=2),
    "칼": Recipe({"철": 1}, tech=2),
    "화약": Recipe({"석탄": 1, "약초": 1}, tech=6),
    "머스킷": Recipe({"철": 2, "목재": 1}, tech=10),
    "약": Recipe({"약초": 2}, tech=1),
    "술": Recipe({"식량": 2}, tech=1),
    "아편": Recipe({"약초": 3}, tech=4),
    "증기기관": Recipe({"철": 5, "석탄": 3}, tech=25),
    "전신": Recipe({"철": 4}, tech=40),
}


def _add(bag: dict[str, float], good: str, qty: float) -> None:
    bag[good] = bag.get(good, 0.0) + qty
    if bag[good] <= 1e-9:
        del bag[good]


def holding(bag: dict[str, float], good: str) -> float:
    return bag.get(good, 0.0)


def effective_tech(world: World, person: Person) -> float:
    org = world.org_of(person)
    return max(person.tech, org.tech if org is not None else 0.0)


def _output_bag(world: World, person: Person, for_org: bool) -> tuple[dict[str, float], str]:
    org = world.org_of(person)
    if for_org and org is not None:
        return world.stash(org.building, org.name), f"{org.name} 창고"
    return person.inventory, "당신의 소지품"


def _input_bag(world: World, person: Person, for_org: bool) -> dict[str, float]:
    org = world.org_of(person)
    if for_org and org is not None and person.location == org.building:
        return world.stash(org.building, org.name)
    return person.inventory


# ---- work
def extract(world: World, person: Person, good: str | None, for_org: bool) -> tuple[bool, str]:
    c = world.config
    place = world.map.places[person.location]
    candidates = [r for r in place.yields if place.deposits.get(r, 0.0) > 0]
    if good not in place.yields and len(place.yields) == 1:
        # only one thing grows or lies here: "potatoes" on a farm is still what the farm yields
        good = next(iter(place.yields))
    if good is None:
        return False, f"{place.name}에서 무엇을 캘지 말하지 않음"
    if good not in place.yields:
        return False, f"{place.name}에는 {good}이(가) 나지 않음"
    if good not in candidates:
        return False, f"{place.name}의 {good}이(가) 바닥남"
    skill = person.skills.get(good, 0.0)
    tools = c.tool_yield_factor if holding(person.inventory, "도구") >= 1 else 1.0
    owner = person.org if for_org and person.org else person.name
    steam = c.steam_yield_factor if place.steam_engines.get(owner, 0) > 0 else 1.0
    amount = (
        place.yields[good]
        * (1 + effective_tech(world, person) * c.tech_yield_bonus_per_level)
        * (1 + skill * c.skill_yield_bonus_per_level)
        * tools * steam * physiology.capability(person.body, c)
    )
    amount = min(amount, place.deposits[good])
    place.deposits[good] -= amount
    bag, where = _output_bag(world, person, for_org)
    _add(bag, good, amount)
    person.skills[good] = skill + c.skill_gain_per_slot
    return True, f"{good} {amount:.1f} → {where}"


def craft(world: World, person: Person, good: str | None, batches: float | None, for_org: bool) -> tuple[bool, str]:
    if not good:
        return False, "만들 물건을 말하지 않음"
    batches = max(1.0, batches or 1.0)
    recipe = RECIPES.get(good)
    bag, where = _output_bag(world, person, for_org)
    if recipe is None:
        if good in RESOURCES or note_issuer(good):
            return False, f"{good}은(는) 만드는 물건이 아님"
        # anyone can make and name a thing; it has no effect on bodies or fights, only whatever others will give for it
        _add(bag, good, batches)
        return True, f"{good} {batches:g} → {where}"
    if effective_tech(world, person) < recipe.tech:
        return False, f"{good}을(를) 만들 기술이 없음"
    source = _input_bag(world, person, for_org)
    for need, qty in recipe.inputs.items():
        if holding(source, need) < qty * batches:
            return False, f"{good} 재료 부족: {need}"
    for need, qty in recipe.inputs.items():
        _add(source, need, -qty * batches)
    _add(bag, good, recipe.output * batches)
    person.skills[good] = person.skills.get(good, 0.0) + world.config.skill_gain_per_slot
    return True, f"{good} {recipe.output * batches:g} → {where}"


def research(world: World, person: Person, for_org: bool) -> tuple[bool, str]:
    gain = world.config.research_gain_per_slot * physiology.capability(person.body, world.config)
    org = world.org_of(person)
    if for_org and org is not None:
        org.tech += gain
        return True, f"{org.name} 기술 +{gain:.2f}"
    person.tech += gain
    return True, f"기술 +{gain:.2f}"


def install(world: World, person: Person, good: str, for_org: bool) -> tuple[bool, str]:
    place = world.map.places[person.location]
    source = _input_bag(world, person, for_org)
    if holding(source, good) < 1:
        return False, f"{good}이(가) 없음"
    _add(source, good, -1)
    if good == "증기기관":
        owner = person.org if for_org and person.org else person.name
        place.steam_engines[owner] = place.steam_engines.get(owner, 0) + 1
        return True, f"{place.name}에 증기기관 설치"
    place.telegraph = True
    return True, f"{place.name}에 전신 설치"


# ---- handing things over
def give(world: World, giver: Person, target: str, good: str | None, qty: float | None, amount: float | None) -> tuple[bool, str]:
    receiver = world.person(target)
    org = world.org(target)
    if receiver is None and org is None:
        return False, f"대상 없음: {target}"
    if receiver is not None and (not receiver.alive or receiver.location != giver.location):
        return False, f"{target}이(가) 이곳에 없음"
    if org is not None and giver.location != org.building:
        return False, f"{org.name}의 건물에 있지 않음"
    if amount is not None:
        if amount <= 0 or giver.money < amount:
            return False, "가진 돈이 모자람" if amount > 0 else "금액 없음"
        giver.money -= amount
        if receiver is not None:
            receiver.money += amount
        else:
            org.money += amount
        return True, f"주화 {amount:g}"
    if not good or qty is None or qty <= 0:
        return False, "무엇을 얼마나 줄지 말하지 않음"
    if holding(giver.inventory, good) < qty:
        return False, f"{good}이(가) 모자람"
    _add(giver.inventory, good, -qty)
    _add(receiver.inventory if receiver is not None else world.stash(org.building, org.name), good, qty)
    return True, f"{good} {qty:g}"


def take_or_store(world: World, person: Person, op: str, owner: str | None, good: str | None, qty: float | None, amount: float | None) -> tuple[bool, str]:
    """Moving your own things between your body and a place you keep things: your home, or your org's building."""
    org = world.org_of(person)
    if owner and org is not None and owner == org.name:
        if person.location != org.building:
            return False, f"{org.name}의 건물에 있지 않음"
        bag, label = world.stash(org.building, org.name), f"{org.name} 창고"
        money_holder = org
    else:
        if person.location != person.home:
            return False, "집에 있지 않음"
        bag, label = world.stash(person.home, person.name), "집"
        money_holder = None
    if amount is not None and money_holder is not None:
        if op == "take":
            if amount <= 0 or org.money < amount:
                return False, f"{label}의 돈이 모자람"
            org.money -= amount
            person.money += amount
        else:
            if amount <= 0 or person.money < amount:
                return False, "가진 돈이 모자람"
            person.money -= amount
            org.money += amount
        return True, f"주화 {amount:g} ({label})"
    if not good or qty is None or qty <= 0:
        return False, "무엇을 얼마나 옮길지 말하지 않음"
    source, dest = (bag, person.inventory) if op == "take" else (person.inventory, bag)
    if holding(source, good) < qty:
        return False, f"{good}이(가) 모자람"
    _add(source, good, -qty)
    _add(dest, good, qty)
    return True, f"{good} {qty:g} ({label})"


# ---- market
def post_order(world: World, person: Person, side: str, good: str | None, qty: float | None, price: float | None, slot: str) -> tuple[bool, str]:
    place = world.map.places[person.location]
    if place.kind != "시장":
        return False, "시장에 있지 않음"
    if not good or qty is None or qty <= 0 or price is None or price <= 0:
        return False, "물건, 수량, 가격 중 말하지 않은 것이 있음"
    if side == "sell":
        if holding(person.inventory, good) < qty:
            return False, f"{good}이(가) 모자람"
        _add(person.inventory, good, -qty)
    else:
        if person.money < qty * price:
            return False, "가진 돈이 모자람"
        person.money -= qty * price
    order = Order(id=world.next_order_id, owner=person.name, side=side, good=good, qty=qty, price=price, day=world.day)
    world.next_order_id += 1
    world.orders.append(order)
    filled = _match(world, order, slot)
    left = f", 남은 주문 {order.qty:g}" if order.qty > 1e-9 else ""
    return True, f"{'팔기' if side == 'sell' else '사기'} {good} {qty:g}개 개당 {price:g}: 체결 {filled:g}{left}"


def _match(world: World, incoming: Order, slot: str) -> float:
    filled = 0.0
    opposite = "sell" if incoming.side == "buy" else "buy"
    book = sorted(
        (o for o in world.orders if o.side == opposite and o.good == incoming.good and o.qty > 1e-9 and o.owner != incoming.owner),
        key=lambda o: (o.price if opposite == "sell" else -o.price, o.id),
    )
    for resting in book:
        crosses = resting.price <= incoming.price if incoming.side == "buy" else resting.price >= incoming.price
        if not crosses or incoming.qty <= 1e-9:
            break
        qty = min(resting.qty, incoming.qty)
        price = resting.price
        buy, sell = (incoming, resting) if incoming.side == "buy" else (resting, incoming)
        buyer, seller = world.people[buy.owner], world.people[sell.owner]
        _add(buyer.inventory, incoming.good, qty)
        seller.money += qty * price
        # the buyer escrowed at their own limit; anything below it comes back
        buyer.money += qty * (buy.price - price)
        resting.qty -= qty
        incoming.qty -= qty
        filled += qty
        world.trades.append(Trade(world.day, slot, incoming.good, qty, price, buyer.name, seller.name))
        recorder = recording.active()
        if recorder is not None:
            recorder.write("trades", {
                "day": world.day, "slot": slot, "good": incoming.good, "qty": qty, "price": price,
                "buyer": buyer.name, "seller": seller.name,
            })
        for party, side in ((buyer, "샀"), (seller, "팔았")):
            world.tell(party.name, f"시장에서 {incoming.good} {qty:g}개를 개당 {price:g}에 {side}음", slot=slot)
    world.orders = [o for o in world.orders if o.qty > 1e-9]
    return filled


def cancel_orders(world: World, person: Person, good: str | None) -> tuple[bool, str]:
    if world.map.places[person.location].kind != "시장":
        return False, "시장에 있지 않음"
    mine = [o for o in world.orders if o.owner == person.name and (good is None or o.good == good)]
    for order in mine:
        if order.side == "sell":
            _add(person.inventory, order.good, order.qty)
        else:
            person.money += order.qty * order.price
    world.orders = [o for o in world.orders if o not in mine]
    return True, f"주문 {len(mine)}건 거둠"


# ---- notes
def issue_notes(bag: dict[str, float], issuer: str, qty: float | None) -> tuple[bool, str]:
    if qty is None or qty <= 0:
        return False, "발행할 수량을 말하지 않음"
    _add(bag, note_name(issuer), qty)
    return True, f"{note_name(issuer)} {qty:g}장 발행"


def redeem_notes(world: World, holder: Person, issuer: str | None, qty: float | None) -> tuple[bool, str]:
    if not issuer or qty is None or qty <= 0:
        return False, "누구의 지폐를 얼마나 바꿀지 말하지 않음"
    good = note_name(issuer)
    if holding(holder.inventory, good) < qty:
        return False, f"{good}이(가) 모자람"
    org = world.org(issuer)
    person = world.person(issuer)
    if issuer == "은행":
        if holder.location != world.bank.place:
            return False, "은행에 있지 않음"
        coins_holder, coins = "bank", world.bank.coins
    elif org is not None:
        if holder.location != org.building:
            return False, f"{org.name}의 건물에 있지 않음"
        coins_holder, coins = "org", org.money
    elif person is not None and person.alive and person.location == holder.location:
        coins_holder, coins = "person", person.money
    else:
        return False, f"{issuer}을(를) 이곳에서 만날 수 없음"
    if coins < qty:
        return False, f"{issuer}에게 바꿔줄 주화가 없음"
    _add(holder.inventory, good, -qty)
    holder.money += qty
    if coins_holder == "bank":
        world.bank.coins -= qty
    elif coins_holder == "org":
        org.money -= qty
    else:
        person.money -= qty
    return True, f"{good} {qty:g}장을 주화로 바꿈"


def notes_outstanding(world: World) -> dict[str, float]:
    totals: dict[str, float] = {}

    def count(bag: dict[str, float]) -> None:
        for good, qty in bag.items():
            issuer = note_issuer(good)
            if issuer:
                totals[issuer] = totals.get(issuer, 0.0) + qty

    for person in world.people.values():
        count(person.inventory)
    for place in world.map.places.values():
        for bag in place.stash.values():
            count(bag)
    for order in world.orders:
        if order.side == "sell" and note_issuer(order.good):
            totals[note_issuer(order.good)] = totals.get(note_issuer(order.good), 0.0) + order.qty
    return totals


def money_report(world: World) -> dict:
    coins = (
        sum(p.money for p in world.people.values())
        + sum(org.money for org in world.orgs.values())
        + world.bank.coins
        + sum(o.qty * o.price for o in world.orders if o.side == "buy")
    )
    notes = notes_outstanding(world)
    return {
        "day": world.day, "coins": round(coins, 6), "notes": notes,
        "money_supply": round(coins + sum(notes.values()), 6),
        "bank_coins": world.bank.coins,
        "loans_outstanding": sum(l.outstanding for l in world.bank.loans if not l.closed),
    }


# ---- bank
def quoted_rate(world: World, person: Person) -> float:
    c = world.config
    rate = c.bank_daily_rate
    if not any(k.worker == person.name for k in world.contracts):
        rate += c.bank_risk_premium
    return rate


def bank_terms(world: World, person: Person) -> str:
    c = world.config
    if person.name in world.bank.refused:
        return "은행: 전에 빚을 갚지 못했으니 빌려줄 수 없다고 함"
    return (
        f"은행: 하루 이자 {quoted_rate(world, person):.0%}, {c.bank_term_days}일 뒤 상환, 최대 {c.bank_max_principal:g}. "
        "빌린 돈은 은행 지폐로 주며 은행에서 주화로 바꿀 수 있음. 못 갚으면 지닌 주화와 은행 지폐를 거둬 감"
    )


def borrow(world: World, person: Person, amount: float | None) -> tuple[bool, str]:
    c = world.config
    if person.location != world.bank.place:
        return False, "은행에 있지 않음"
    if person.name in world.bank.refused:
        return False, "은행이 거절(전에 갚지 못함)"
    if amount is None or amount <= 0:
        return False, "빌릴 금액을 말하지 않음"
    principal = min(amount, c.bank_max_principal)
    out = notes_outstanding(world).get("은행", 0.0)
    if out + principal > world.bank.coins * c.bank_note_multiplier:
        return False, "은행이 거절(더 내줄 수 없음)"
    rate = quoted_rate(world, person)
    world.bank.loans.append(Loan(person.name, principal, principal, rate, world.day + c.bank_term_days))
    _add(person.inventory, note_name("은행"), principal)
    return True, f"은행 지폐 {principal:g} 빌림(하루 이자 {rate:.0%}, {world.day + c.bank_term_days}일째 상환)"


def repay(world: World, person: Person, amount: float | None) -> tuple[bool, str]:
    if person.location != world.bank.place:
        return False, "은행에 있지 않음"
    loans = [l for l in world.bank.loans if l.borrower == person.name and not l.closed]
    if not loans:
        return False, "갚을 빚이 없음"
    if amount is None or amount <= 0:
        return False, "갚을 금액을 말하지 않음"
    paid = _collect(world, person, min(amount, sum(l.outstanding for l in loans)), loans)
    return True, f"{paid:g} 갚음"


def _collect(world: World, person: Person, amount: float, loans: list[Loan]) -> float:
    notes = min(holding(person.inventory, note_name("은행")), amount)
    _add(person.inventory, note_name("은행"), -notes)
    coins = min(person.money, amount - notes)
    person.money -= coins
    world.bank.coins += coins
    paid = notes + coins
    remaining = paid
    for loan in loans:
        part = min(loan.outstanding, remaining)
        loan.outstanding -= part
        remaining -= part
        if loan.outstanding <= 1e-9:
            loan.closed = True
    return paid


def settle_bank(world: World) -> None:
    for loan in world.bank.loans:
        if loan.closed:
            continue
        loan.outstanding *= 1 + loan.rate
        if world.day < loan.due_day:
            continue
        person = world.person(loan.borrower)
        if person is None or not person.alive:
            loan.closed = loan.defaulted = True
            continue
        paid = _collect(world, person, loan.outstanding, [loan])
        if not loan.closed:
            loan.closed = loan.defaulted = True
            world.bank.refused.add(person.name)
            world.tell(person.name, f"은행 빚 만기: {paid:.1f}을 거둬 갔고 나머지는 갚지 못함")
        else:
            world.tell(person.name, f"은행 빚 만기: {paid:.1f}을 갚음")


# ---- wages
def offer_job(world: World, employer: str, worker: str, wage: float | None, every_days: float | None) -> tuple[bool, str]:
    if wage is None or wage <= 0:
        return False, "급여를 말하지 않음"
    days = int(every_days) if every_days else 7
    world.offers = [o for o in world.offers if not (o.employer == employer and o.worker == worker)]
    world.offers.append(Offer(employer, worker, wage, max(1, days), world.day))
    return True, f"{worker}에게 {days}일마다 {wage:g} 제안"


def accept_job(world: World, person: Person, employer: str | None) -> tuple[bool, str]:
    offer = next((o for o in world.offers if o.worker == person.name and (employer is None or o.employer == employer)), None)
    if offer is None:
        return False, f"받은 제안 없음: {employer}"
    world.offers.remove(offer)
    world.contracts.append(Contract(offer.employer, person.name, offer.wage, offer.every_days, world.day + offer.every_days))
    org = world.org(offer.employer)
    if org is not None and person.name not in org.members:
        previous = world.org_of(person)
        if previous is not None and person.name in previous.members:
            previous.members.remove(person.name)
        org.members.append(person.name)
        person.org = org.name
        if person.name in org.applicants:
            org.applicants.remove(person.name)
    return True, f"{offer.employer}에서 {offer.every_days}일마다 {offer.wage:g}에 일하기로 함"


def end_contracts(world: World, worker: str, employer: str | None = None) -> None:
    world.contracts = [k for k in world.contracts if not (k.worker == worker and (employer is None or k.employer == employer))]


def payday(world: World) -> None:
    for contract in world.contracts:
        if contract.next_pay_day != world.day:
            continue
        contract.next_pay_day += contract.every_days
        worker = world.person(contract.worker)
        if worker is None or not worker.alive:
            continue
        org = world.org(contract.employer)
        employer_person = world.person(contract.employer)
        available = org.money if org is not None else (employer_person.money if employer_person else 0.0)
        paid = min(available, contract.wage)
        if org is not None:
            org.money -= paid
        elif employer_person is not None:
            employer_person.money -= paid
        worker.money += paid
        if paid < contract.wage - 1e-9:
            contract.unpaid += 1
            world.tell(worker.name, f"급여일: {contract.employer}에서 {contract.wage:g} 중 {paid:g}만 받음")
        else:
            contract.unpaid = 0
            world.tell(worker.name, f"급여일: {contract.employer}에서 {paid:g}을 받음", incoming=False)


def regenerate(world: World) -> None:
    for place in world.map.places.values():
        for good, rate in place.regen.items():
            cap = place.caps.get(good, float("inf"))
            place.deposits[good] = min(cap, place.deposits.get(good, 0.0) + rate)
        place.notices = [n for n in place.notices if world.day - n.day < world.config.notice_days]
