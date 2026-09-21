import pytest

import engine.llm_agent as llm_agent
from engine.agent_prompts import AgentVote, Declaration
from engine.clerk import Operation, OrgOperation, OrgTranscription, Transcription, keep_said_amounts
from engine.config import SimulationConfig
from engine.entities import Employee, Proposal
from engine.physics import employer_of, find_company, find_person, resolve_org_ops, resolve_person_ops
from engine.scenarios import build_agent_world, build_full_world
from engine.scheduler import due_persons


@pytest.fixture
def world():
    return build_agent_world(seed=0)


def _patch_llm(monkeypatch, respond):
    captured = []

    def fake(prompt, schema, config, temperature=None, label=""):
        captured.append((label, schema, temperature, prompt))
        return respond(schema, label, prompt)

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    return captured


def _silent(schema, label, prompt):
    return Declaration(declaration="", next_wake_in=5) if schema is Declaration else None


def test_private_message_reaches_only_the_recipient_as_an_attributed_claim(world):
    a, b = world.companies[0].employees[:2]
    outsider = world.companies[1].employees[0]
    resolve_person_ops(world, a.name, [Operation(op="message", target=b.name, content="비밀 이야기")], tick=1)
    assert any(e.source == a.name and "비밀 이야기" in e.text for e in world.knowledge[b.name].entries)
    assert not any("비밀 이야기" in e.text for e in world.knowledge[outsider.name].entries)
    assert world.knowledge[b.name].unread == 1


def test_public_statement_reaches_everyone_as_what_was_said_not_as_fact(world):
    speaker = world.vigilantes[0]
    resolve_person_ops(world, speaker.name, [Operation(op="message", target="public", content="X가 무기를 만든다")], tick=2)
    expected = f"{speaker.name}이(가) 공개적으로 말함: X가 무기를 만든다"
    for company in world.companies:
        for employee in company.employees:
            assert any(entry.text == expected for entry in world.knowledge[employee.name].entries)


def test_message_to_an_org_reaches_its_members_only(world):
    speaker = world.vigilantes[0]
    org, other = world.companies[2], world.companies[3]
    resolve_person_ops(world, speaker.name, [Operation(op="message", target=org.name, content="거래하자")], tick=1)
    assert all(any("거래하자" in x.text for x in world.knowledge[e.name].entries) for e in org.employees)
    assert not any(any("거래하자" in x.text for x in world.knowledge[e.name].entries) for e in other.employees)
    assert speaker.name in world.acquaintances[org.employees[0].name]


def test_you_cannot_reach_someone_you_have_never_heard_of(world):
    stranger, target = world.vigilantes[0], world.vigilantes[1]
    results, _ = resolve_person_ops(world, stranger.name, [Operation(op="message", target=target.name, content="안녕")], tick=1)
    assert not results[0].ok
    assert not any("안녕" in e.text for e in world.knowledge[target.name].entries)
    resolve_person_ops(world, target.name, [Operation(op="message", target="public", content="나 여기 있다")], tick=1)
    results, _ = resolve_person_ops(world, stranger.name, [Operation(op="message", target=target.name, content="안녕")], tick=2)
    assert results[0].ok


def test_transfer_moves_exactly_what_was_sent(world):
    sender, recipient = world.vigilantes[0], world.vigilantes[1]
    world.acquaintances[sender.name].add(recipient.name)
    before_sender, before_recipient = sender.resources.capital, recipient.resources.capital
    results, _ = resolve_person_ops(world, sender.name, [Operation(op="transfer", target=recipient.name, amount=15.0)], tick=1)
    assert results[0].ok
    assert sender.resources.capital == before_sender - 15.0
    assert recipient.resources.capital == before_recipient + 15.0


def test_transfer_without_enough_money_moves_nothing(world):
    sender, recipient = world.vigilantes[0], world.vigilantes[1]
    world.acquaintances[sender.name].add(recipient.name)
    before = (sender.resources.capital, recipient.resources.capital)
    results, _ = resolve_person_ops(world, sender.name, [Operation(op="transfer", target=recipient.name, amount=10_000.0)], tick=1)
    assert not results[0].ok and results[0].detail == "잔고 부족"
    assert (sender.resources.capital, recipient.resources.capital) == before


def test_transfer_to_someone_who_does_not_exist_fails(world):
    results, _ = resolve_person_ops(world, world.vigilantes[0].name, [Operation(op="transfer", target="유령", amount=1.0)], tick=1)
    assert not results[0].ok


def test_members_put_items_on_the_agenda_outsiders_only_speak(world):
    org = world.companies[2]
    member, outsider = org.employees[0], world.vigilantes[0]
    resolve_person_ops(world, member.name, [Operation(op="propose", target=org.name, content="기술에 투자하자")], tick=1)
    resolve_person_ops(world, outsider.name, [Operation(op="propose", target=org.name, content="나에게 돈을 줘")], tick=1)
    assert [p.text for p in org.agenda] == ["기술에 투자하자"]
    assert any("나에게 돈을 줘" in e.text for e in world.knowledge[member.name].entries)


def test_leaving_keeps_the_same_person_with_their_real_savings(world):
    org = world.companies[0]
    person = org.employees[0]
    person.savings = -12.5
    name = person.name
    results, _ = resolve_person_ops(world, name, [Operation(op="leave")], tick=3)
    assert results[0].ok
    assert employer_of(world, name) is None
    individual = find_person(world, name)
    assert individual is not None and not isinstance(individual, Employee)
    assert individual.resources.capital == -12.5
    assert any(f"{name}이(가)" in e.text for e in world.knowledge[org.employees[0].name].entries)


def test_founding_uses_the_name_and_stake_the_person_chose(world):
    founder = world.companies[0].employees[0]
    founder.savings = 50.0
    resolve_person_ops(world, founder.name, [Operation(op="found", content="새벽회", amount=20.0)], tick=4)
    new_org = find_company(world, "새벽회")
    assert new_org is not None
    assert new_org.resources.capital == 20.0
    assert [e.name for e in new_org.employees] == [founder.name]
    assert founder.savings == 30.0


def test_founding_without_naming_an_amount_stakes_nothing(world):
    founder = world.companies[0].employees[0]
    founder.savings = 50.0
    resolve_person_ops(world, founder.name, [Operation(op="found", content="무명회")], tick=1)
    new_org = find_company(world, "무명회")
    assert new_org is not None and new_org.resources.capital == 0.0
    assert founder.savings == 50.0


def test_someone_who_pledged_their_freedom_and_defaulted_cannot_leave(world):
    org = world.companies[0]
    person = org.employees[0]
    person.bound_to, person.bound_until = "Bank", 99
    results, _ = resolve_person_ops(world, person.name, [Operation(op="leave")], tick=1)
    assert not results[0].ok
    assert employer_of(world, person.name) is org


def test_borrowing_without_choosing_collateral_does_not_happen(world):
    person = world.companies[0].employees[0]
    before = person.savings
    results, _ = resolve_person_ops(world, person.name, [Operation(op="borrow", amount=30.0)], tick=1)
    assert not results[0].ok and person.savings == before
    results, _ = resolve_person_ops(world, person.name, [Operation(op="borrow", amount=30.0, collateral="savings")], tick=1)
    assert results[0].ok and person.savings == before + 30.0


def test_org_investment_converts_capital_at_the_physical_rate(world):
    org = world.companies[2]
    org.resources.capital = 100.0
    tech_before = org.resources.tech
    results = resolve_org_ops(world, org, [OrgOperation(op="org_invest", target="tech", amount=50.0)], tick=1)
    assert results[0].ok
    assert org.resources.capital == 50.0
    assert org.resources.tech == pytest.approx(tech_before + 50.0 * world.config.invest_tech_rate)


def test_org_cannot_spend_money_it_does_not_have(world):
    org = world.companies[2]
    org.resources.capital = 5.0
    target = world.vigilantes[0].name
    world.acquaintances[org.employees[0].name].add(target)
    results = resolve_org_ops(world, org, [OrgOperation(op="org_transfer", target=target, amount=50.0)], tick=1)
    assert not results[0].ok and results[0].detail == "조직 자본 부족"
    assert org.resources.capital == 5.0


def test_an_org_cannot_pay_someone_none_of_its_members_know(world):
    org = world.companies[2]
    org.resources.capital = 100.0
    results = resolve_org_ops(world, org, [OrgOperation(op="org_transfer", target=world.vigilantes[0].name, amount=10.0)], tick=1)
    assert not results[0].ok and org.resources.capital == 100.0


def test_org_can_set_a_members_wage(world):
    org = world.companies[2]
    member = org.employees[0]
    resolve_org_ops(world, org, [OrgOperation(op="set_wage", target=member.name, amount=3.0)], tick=1)
    assert member.wage == 3.0


def test_only_people_with_something_new_or_a_due_wake_are_called(world):
    names = [e.name for c in world.companies for e in c.employees] + [v.name for v in world.vigilantes]
    for name in names:
        world.next_wake[name] = 10
    a, b = names[0], names[1]
    assert due_persons(world, tick=1) == []
    resolve_person_ops(world, a, [Operation(op="message", target=b, content="안녕")], tick=1)
    assert due_persons(world, tick=1) == [b]
    assert set(due_persons(world, tick=10)) == set(names)


def test_agent_world_runs_no_formula_trade_espionage_or_reputation_recovery(world, monkeypatch):
    _patch_llm(monkeypatch, _silent)
    world.config = SimulationConfig(espionage_attempt_probability=1.0)
    org = world.companies[2]
    org.resources.legitimacy = 0.1
    org.resources.legitimacy_baseline = 0.9
    for _ in range(3):
        tick = world.tick()
        assert tick.trades == [] and tick.espionage_events == [] and tick.wmd_attempts == []
    assert org.resources.legitimacy == 0.1


def test_agent_prompts_carry_no_archetype_labels_or_other_orgs_books(world, monkeypatch):
    captured = _patch_llm(monkeypatch, _silent)
    world.tick()
    prompts = {label: prompt for label, schema, _, prompt in captured if label.startswith("declare:")}
    assert prompts
    forbidden = ["멸망론자", "안전조율자", "Doomsayer", "SafetyCoordinator", "DOOMSAYER", "Umbra", "Aegis"]
    for prompt in prompts.values():
        assert not any(word in prompt for word in forbidden)
    org0, org1 = world.companies[0], world.companies[1]
    own_prompt = prompts[f"declare:{org0.employees[0].name}"]
    assert f"자본: {org1.resources.capital:.1f}," not in own_prompt


def test_a_failed_transcription_changes_nothing_in_the_world(world, monkeypatch):
    sender, recipient = world.vigilantes[0], world.vigilantes[1]

    def respond(schema, label, prompt):
        if schema is Declaration:
            if label == f"declare:{sender.name}":
                return Declaration(declaration=f"{recipient.name}에게 20을 보낸다", next_wake_in=5)
            return Declaration(declaration="", next_wake_in=5)
        return None

    _patch_llm(monkeypatch, respond)
    before = (sender.resources.capital, recipient.resources.capital)
    world.tick()
    living = world.config.living_cost
    assert sender.resources.capital == before[0] - living
    assert recipient.resources.capital == before[1] - living


def test_a_passed_proposal_is_transcribed_and_executed(world, monkeypatch):
    org = world.companies[2]
    org.agenda.append(Proposal(proposer=org.employees[0].name, text="자본 30을 기술에 투입하자", tick=0))

    def respond(schema, label, prompt):
        if schema is AgentVote:
            return AgentVote(support_action=True, reasoning="좋다")
        if schema is OrgTranscription:
            return OrgTranscription(operations=[OrgOperation(op="org_invest", target="tech", amount=30.0)])
        return _silent(schema, label, prompt)

    captured = _patch_llm(monkeypatch, respond)
    tech_before = org.resources.tech
    tick = world.tick()
    assert len(tick.council_votes) == 1 and tick.council_votes[0].proceeds
    assert org.resources.tech == pytest.approx(tech_before + 30.0 * world.config.invest_tech_rate)
    assert any(label.startswith("clerk:") for label, *_ in captured)


def test_the_clerk_runs_at_zero_temperature(world, monkeypatch):
    def respond(schema, label, prompt):
        if schema is Declaration:
            return Declaration(declaration="조직에 인사한다", next_wake_in=5)
        if schema is Transcription:
            return Transcription(operations=[Operation(op="wait")])
        return None

    captured = _patch_llm(monkeypatch, respond)
    world.tick()
    clerk_temps = [temperature for _, schema, temperature, _ in captured if schema is Transcription]
    assert clerk_temps and all(t == 0.0 for t in clerk_temps)


def test_formula_world_is_still_the_default_and_still_trades():
    world = build_full_world(seed=0)
    assert world.mode == "formula"
    assert world.tick().trades


def test_founding_then_funding_it_by_name_puts_in_exactly_what_was_said(world):
    # the real clerk transcribes "found X and put 15 in" as found + a separate transfer
    founder = world.companies[0].employees[0]
    founder.savings = 50.0
    ops = [Operation(op="found", target="새벽회", content="새벽회"), Operation(op="transfer", target="새벽회", amount=15.0)]
    results, _ = resolve_person_ops(world, founder.name, ops, tick=1)
    assert all(r.ok for r in results)
    assert find_company(world, "새벽회").resources.capital == 15.0
    assert founder.savings == 35.0


def test_money_follows_the_org_just_founded_even_if_its_name_was_already_taken(world):
    existing = world.companies[1]
    founder = world.companies[0].employees[0]
    founder.savings = 40.0
    existing_before = existing.resources.capital
    ops = [Operation(op="found", content=existing.name), Operation(op="transfer", target=existing.name, amount=10.0)]
    results, _ = resolve_person_ops(world, founder.name, ops, tick=1)
    founded = find_company(world, results[0].detail)
    assert founded is not existing and founded.resources.capital == 10.0
    assert existing.resources.capital == existing_before


def test_quotes_around_a_new_org_name_are_not_part_of_the_name(world):
    founder = world.companies[0].employees[0]
    resolve_person_ops(world, founder.name, [Operation(op="found", content="'새벽회'")], tick=1)
    assert find_company(world, "새벽회") is not None


def test_amounts_are_kept_only_when_said_as_a_number_or_a_share():
    def amount_after(text, amount):
        return keep_said_amounts([Operation(op="transfer", target="P01", amount=amount)], text)[0].amount

    assert amount_after("P01에게 25를 보낸다", 25.0) == 25.0
    assert amount_after("P01에게 1,500을 보낸다", 1500.0) == 1500.0
    assert amount_after("P01에게 10만을 보낸다", 100000.0) == 100000.0
    assert amount_after("P01에게 가진 돈의 절반을 보낸다", 37.5) == 37.5
    assert amount_after("P01에게 돈을 보낸다", 20.0) is None


def test_an_org_action_with_an_amount_nobody_proposed_does_not_happen(world, monkeypatch):
    # seen with the real 8B: a proposal about loans came back as a 400.6 coercion buy and wages set to 0
    org = world.companies[0]
    member = org.employees[0]
    org.agenda.append(Proposal(proposer=member.name, text="대출을 통해 자금을 확보하자", tick=0))

    def respond(schema, label, prompt):
        if schema is AgentVote:
            return AgentVote(support_action=True, reasoning="좋다")
        if schema is OrgTranscription:
            return OrgTranscription(operations=[
                OrgOperation(op="org_invest", target="coercion", amount=40.0),
                OrgOperation(op="set_wage", target=member.name, amount=0.0),
            ])
        return _silent(schema, label, prompt)

    _patch_llm(monkeypatch, respond)
    coercion_before, wage_before = org.resources.coercion, member.wage
    world.tick()
    assert org.resources.coercion == coercion_before
    assert member.wage == wage_before


def test_everyone_decides_from_what_they_knew_when_the_tick_began(world, monkeypatch):
    speaker, listener = world.companies[0].employees[:2]

    def respond(schema, label, prompt):
        if schema is Declaration:
            if label == f"declare:{speaker.name}":
                return Declaration(declaration=f"{listener.name}에게 비밀을 말한다", next_wake_in=5)
            return Declaration(declaration="", next_wake_in=5)
        if schema is Transcription:
            return Transcription(operations=[Operation(op="message", target=listener.name, content="비밀")])
        return None

    captured = _patch_llm(monkeypatch, respond)
    world.tick()
    listener_prompts = [prompt for label, _, _, prompt in captured if label == f"declare:{listener.name}"]
    assert len(listener_prompts) == 1 and "비밀" not in listener_prompts[0]
    assert world.knowledge[listener.name].unread == 1  # arrived during the tick, so it wakes them next tick

    world.tick()
    listener_prompts = [prompt for label, _, _, prompt in captured if label == f"declare:{listener.name}"]
    assert len(listener_prompts) == 2 and "비밀" in listener_prompts[1]
