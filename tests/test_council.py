import random

from engine.config import SimulationConfig
from engine.council import record_memory, tally_votes
from engine.entities import Company, CompanyArchetype, Employee, Resources
from engine.llm_agent import CouncilMemberResponse, _format_transcript, build_council_member_prompt


def make_employees(n: int) -> list[Employee]:
    return [
        Employee(
            name=f"e{i}", wage=10, expected_wage=10, value_alignment=0.5,
            retaliation_cost=0.1, alternative_attractiveness=0.2,
        )
        for i in range(n)
    ]


def responses(*flags: bool) -> list[CouncilMemberResponse]:
    return [CouncilMemberResponse(support_action=f, disclose_to_outsiders=False, reasoning="") for f in flags]


def test_majority_support_proceeds():
    employees = make_employees(5)
    outcome = tally_votes(responses(True, True, True, False, False), employees, SimulationConfig(), random.Random(0))
    assert outcome.proceeds is True
    assert outcome.votes_for == 3
    assert outcome.votes_total == 5


def test_minority_support_does_not_proceed():
    employees = make_employees(5)
    outcome = tally_votes(responses(True, True, False, False, False), employees, SimulationConfig(), random.Random(0))
    assert outcome.proceeds is False


def test_tie_does_not_proceed():
    employees = make_employees(4)
    outcome = tally_votes(responses(True, True, False, False), employees, SimulationConfig(), random.Random(0))
    assert outcome.proceeds is False  # strict majority required, a tie is not one


def test_single_disclosure_exposes_whole_vote_even_if_against():
    employees = make_employees(3)
    resp = [
        CouncilMemberResponse(support_action=False, disclose_to_outsiders=False, reasoning=""),
        CouncilMemberResponse(support_action=False, disclose_to_outsiders=True, reasoning=""),
        CouncilMemberResponse(support_action=False, disclose_to_outsiders=False, reasoning=""),
    ]
    outcome = tally_votes(resp, employees, SimulationConfig(), random.Random(0))
    assert outcome.proceeds is False
    assert outcome.disclosed is True


def test_no_disclosure_when_nobody_discloses():
    employees = make_employees(3)
    outcome = tally_votes(responses(True, True, True), employees, SimulationConfig(), random.Random(0))
    assert outcome.disclosed is False


def test_all_failed_calls_fall_back_without_crashing():
    employees = make_employees(5)
    outcome = tally_votes([None] * 5, employees, SimulationConfig(), random.Random(0))
    assert outcome.votes_total == 5
    assert all(r.source == "fallback" for r in outcome.member_results)
    assert isinstance(outcome.proceeds, bool)
    assert isinstance(outcome.disclosed, bool)


def test_record_memory_appends_one_entry_per_member():
    employees = make_employees(3)
    outcome = tally_votes(responses(True, True, False), employees, SimulationConfig(), random.Random(0))
    record_memory(employees, outcome, 0, Resources(capital=10, tech=1, coercion=0.1, legitimacy=0.5), "test agenda")
    assert all(len(e.memory) == 1 for e in employees)


def test_record_memory_accumulates_across_ticks_in_order():
    employees = make_employees(2)
    for tick in range(3):
        outcome = tally_votes(responses(True, False), employees, SimulationConfig(), random.Random(0))
        record_memory(employees, outcome, tick, Resources(capital=10 + tick), "test agenda")
    assert [e.memory for e in employees][0] == employees[0].memory  # sanity: independent lists
    assert len(employees[0].memory) == 3
    assert "0분기차" in employees[0].memory[0]
    assert "1분기차" in employees[0].memory[1]
    assert "2분기차" in employees[0].memory[2]


def test_format_transcript_empty_is_blank():
    assert _format_transcript(None) == ""
    assert _format_transcript([]) == ""


def test_format_transcript_includes_round_number_and_name():
    resp = CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="my reason")
    text = _format_transcript([(1, "Alice", resp)])
    assert "1라운드" in text
    assert "Alice" in text
    assert "my reason" in text
    assert "찬성" in text


def test_format_transcript_accumulates_multiple_rounds_in_order():
    r1 = CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="first")
    r2 = CouncilMemberResponse(support_action=False, disclose_to_outsiders=True, reasoning="second")
    text = _format_transcript([(1, "Alice", r1), (2, "Bob", r2)])
    assert text.index("Alice") < text.index("Bob")
    assert "외부공개 의향 있음" in text  # Bob's disclosure flag shows up


def test_prompt_includes_transcript_section_when_given():
    employee = Employee(
        name="e1", wage=10, expected_wage=10, value_alignment=0.5,
        retaliation_cost=0.1, alternative_attractiveness=0.2,
    )
    company = Company(name="TestCo", archetype=CompanyArchetype.DOOMSAYER, resources=Resources())
    resp = CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="prior reasoning")
    prompt = build_council_member_prompt(
        employee, company, [], "test agenda", SimulationConfig(),
        discussion_transcript=[(1, "OtherMember", resp)],
    )
    assert "OtherMember" in prompt
    assert "prior reasoning" in prompt


def test_prompt_omits_transcript_section_when_none():
    employee = Employee(
        name="e1", wage=10, expected_wage=10, value_alignment=0.5,
        retaliation_cost=0.1, alternative_attractiveness=0.2,
    )
    company = Company(name="TestCo", archetype=CompanyArchetype.DOOMSAYER, resources=Resources())
    prompt = build_council_member_prompt(employee, company, [], "test agenda", SimulationConfig())
    assert "지금까지 이 회의에서 나온" not in prompt


def test_mixed_success_and_failure_calls():
    employees = make_employees(3)
    resp = [
        CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="real"),
        None,
        CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="real"),
    ]
    outcome = tally_votes(resp, employees, SimulationConfig(), random.Random(0))
    assert outcome.member_results[0].source == "llm"
    assert outcome.member_results[1].source == "fallback"
    assert outcome.member_results[2].source == "llm"
