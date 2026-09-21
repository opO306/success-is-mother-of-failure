import json

from engine import recorder as recording
from engine.config import SimulationConfig
from engine.council import CouncilOutcome, MemberResult, collect_proposals
from engine.entities import Company, CompanyArchetype, Employee, Resources
from engine.llm_agent import CouncilMemberResponse, build_council_member_prompt


def _company(proposals=None):
    return Company(
        name="Org", archetype=CompanyArchetype.DOOMSAYER,
        resources=Resources(capital=50.0, tech=5.0, legitimacy=0.5),
        employees=[Employee(name="e1", wage=10.0, expected_wage=10.0, value_alignment=0.5,
                            retaliation_cost=0.1, alternative_attractiveness=0.3)],
        open_proposals=proposals or [],
    )


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_failed_calls_are_recorded_not_just_successful_ones(tmp_path):
    run = recording.start_run("t", {"seed": 0}, root=tmp_path)
    try:
        run.record_llm_call(
            label="council:Org:e1", schema="CouncilMemberResponse", prompt="P", temperature=0.7,
            attempt=1, ok=False, raw="{bad json", parsed=None, error="JSONDecodeError: x",
            latency_s=1.0,
        )
        run.record_llm_call(
            label="council:Org:e1", schema="CouncilMemberResponse", prompt="P", temperature=0.7,
            attempt=2, ok=True, raw='{"ok":1}', parsed={"support_action": True}, error=None,
            latency_s=1.0,
        )
    finally:
        recording.stop_run()

    rows = _read(run.root / "llm_calls.jsonl")
    assert [r["ok"] for r in rows] == [False, True]
    assert rows[0]["raw_response"] == "{bad json"
    assert rows[0]["error"].startswith("JSONDecodeError")
    assert rows[0]["prompt"] == "P"  # the exact prompt behind the decision is kept


def test_every_discussion_round_is_kept_not_just_the_binding_one(tmp_path):
    run = recording.start_run("t", {"seed": 0}, root=tmp_path)
    try:
        rounds = [
            [CouncilMemberResponse(support_action=False, disclose_to_outsiders=False, reasoning="r1")],
            [CouncilMemberResponse(support_action=True, disclose_to_outsiders=False, reasoning="r2")],
        ]
        run.record_meeting(
            tick_index=3, company="Org", action_description="A", roster=["e1"], all_rounds=rounds
        )
    finally:
        recording.stop_run()

    meeting = _read(run.root / "meetings.jsonl")[0]
    assert len(meeting["rounds"]) == 2
    assert meeting["rounds"][0][0]["reasoning"] == "r1"  # the round they changed their mind in
    assert meeting["rounds"][1][0]["support_action"] is True
    assert meeting["rounds"][0][0]["member"] == "e1"


def test_recording_is_off_by_default_so_the_engine_runs_without_it():
    assert recording.active() is None


def test_proposals_reach_the_org_and_the_next_prompt():
    company = _company()
    outcome = CouncilOutcome(
        proceeds=True, disclosed=False, votes_for=1, votes_total=1,
        member_results=[
            MemberResult(name="e1", support=True, disclosed=False, reasoning="", source="llm",
                         proposal="무기 말고 다른 걸 하자"),
        ],
    )
    raised = collect_proposals(company, outcome)

    assert raised == ["e1: 무기 말고 다른 걸 하자"]
    assert company.open_proposals == ["e1: 무기 말고 다른 걸 하자"]

    prompt = build_council_member_prompt(
        company.employees[0], company, [company], "안건", SimulationConfig()
    )
    assert "무기 말고 다른 걸 하자" in prompt


def test_empty_proposals_are_not_carried():
    company = _company()
    outcome = CouncilOutcome(
        proceeds=True, disclosed=False, votes_for=1, votes_total=1,
        member_results=[
            MemberResult(name="e1", support=True, disclosed=False, reasoning="", source="llm",
                         proposal="   "),
        ],
    )
    assert collect_proposals(company, outcome) == []
    assert company.open_proposals == []


def test_open_proposals_do_not_grow_without_bound():
    company = _company(proposals=[f"p{i}" for i in range(20)])
    outcome = CouncilOutcome(
        proceeds=True, disclosed=False, votes_for=1, votes_total=1,
        member_results=[
            MemberResult(name="e1", support=True, disclosed=False, reasoning="", source="llm",
                         proposal="새 제안"),
        ],
    )
    collect_proposals(company, outcome)
    assert len(company.open_proposals) == 20
    assert company.open_proposals[-1] == "e1: 새 제안"
