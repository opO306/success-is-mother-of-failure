import dataclasses

import requests

import engine.llm_agent as llm_agent
from engine.config import SimulationConfig
from engine.primal import clerk
from engine.primal.clerk import DayPlan, Step, build_clerk_prompt, spoken
from engine.primal.prompts import DayDeclaration
from tools import bench_models
from tools.clerk_checks import problems
from tools.harvest_clerk_cases import parse_clerk_prompt
from tools.plan_sameness import cosine, grams, sameness


class _OpenAIAnswer:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"model": "served", "choices": [{"message": {"content": self.content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7}}


def test_an_openai_compatible_server_gets_a_json_schema_request_and_the_key_from_the_environment(monkeypatch):
    seen = {}

    def post(url, json=None, timeout=None, headers=None):
        seen.update(url=url, json=json, headers=headers)
        return _OpenAIAnswer('{"plan": "물을 마신다"}')

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setenv("LLM_API_KEY", "secret")
    config = dataclasses.replace(SimulationConfig(), llm_backend="openai", llm_host="http://pod:8000/", llm_model="Qwen/Qwen3-32B")
    decision = llm_agent.call_llm_decision("p", DayDeclaration, config, temperature=0.4)
    assert decision.plan == "물을 마신다"
    assert seen["url"] == "http://pod:8000/v1/chat/completions"
    assert seen["json"]["model"] == "Qwen/Qwen3-32B" and seen["json"]["temperature"] == 0.4
    assert seen["json"]["response_format"]["json_schema"]["schema"] == DayDeclaration.model_json_schema()
    assert seen["json"]["chat_template_kwargs"] == {"enable_thinking": False} and "max_tokens" not in seen["json"]
    assert seen["headers"] == {"Authorization": "Bearer secret"}
    assert "secret" not in repr(config)


def test_the_clerk_can_run_on_its_own_model_and_server(monkeypatch):
    seen = []

    def post(url, json=None, timeout=None, headers=None):
        seen.append((url, json["model"], json.get("max_tokens")))
        return _OpenAIAnswer('{"steps": [{"동작": "마시기"}]}')

    monkeypatch.setattr(requests, "post", post)
    config = dataclasses.replace(SimulationConfig(), clerk_model="small-clerk", clerk_host="http://clerk:9000", clerk_backend="openai")
    plan = clerk.transcribe("P01", "물을 마신다", ["a"], [], [], "야영지", config)
    assert [s.op for s in plan.steps] == ["drink"]
    assert seen == [("http://clerk:9000/v1/chat/completions", "small-clerk", config.clerk_max_output_tokens)]


def test_plans_that_say_the_same_thing_measure_as_alike_and_copied_names_do_not_count():
    plans = [
        {"day": 1, "person": "P01", "plan": "불을 피우고 돌을 깬다. P02, P03와 함께"},
        {"day": 1, "person": "P02", "plan": "불을 피우고 돌을 깬다. P04, P05와 함께"},
        {"day": 1, "person": "P03", "plan": "호수에 가서 물고기를 잡아 본다"},
        {"day": 2, "person": "P01", "plan": "불을 피우고 돌을 깬다."},
    ]
    assert cosine(grams(plans[0]["plan"]), grams(plans[1]["plan"])) > 0.999
    result = sameness(plans)
    assert 0 < result["days"][1]["between_people"] < 1
    assert result["days"][2]["same_person_vs_yesterday"] > 0.7  # the same sentence, minus yesterday's "와 함께" tail
    assert result["days"][1]["common_phrases"][0][1] >= 0.66


def test_code_finds_what_contradicts_the_words_without_judging_what_was_meant():
    steps = ([Step(op="go", target="부싯돌 비탈")] + [Step(op="talk", target=n, content="같이 가자") for n in ("P01", "P02", "P03")]
             + [Step(op="dry", items=[1, 2, 3]), Step(op="give", target="P99", items=[4])])
    found = problems("같이 가자고 말하고 가죽을 말린다", steps, 3, ["P01", "P02", "P03"], ["부싯돌 비탈", "호수"], "남쪽 야영지")
    assert set(found) == {"unsaid_place", "repeated_talk", "all_items", "item_out_of_range", "unknown_person"}
    assert problems("서른 글자가 넘는 긴 계획 문장이 통째로 하나의 그밖의행동이 되었다", [Step(op="intent", content="…")], 3, [], [], "") == ["whole_as_intent"]
    assert problems("호수에 가서 물을 마신다", [Step(op="go", target="호수"), Step(op="drink")], 3, [], ["호수"], "") == []
    assert problems("x", None, 0, [], [], "") == ["no_answer"]


def test_a_recorded_clerk_prompt_gives_back_exactly_what_the_clerk_was_shown():
    prompt = build_clerk_prompt("P07", '오늘은 "호수"에 간다', ["날이 선 부싯돌 조각", "칡뿌리"], ["P01", "P02"], ["남쪽 야영지", "호수"],
                                "남쪽 야영지", reaction=True)
    assert parse_clerk_prompt(prompt) == {
        "name": "P07", "reaction": True, "text": '오늘은 "호수"에 간다', "carried": ["날이 선 부싯돌 조각", "칡뿌리"],
        "names": ["P01", "P02"], "places": ["남쪽 야영지", "호수"], "camp": "남쪽 야영지",
    }
    empty = parse_clerk_prompt(build_clerk_prompt("P08", "잔다", [], [], [], "동쪽 야영지"))
    assert (empty["carried"], empty["names"], empty["places"], empty["reaction"]) == ([], [], [], False)


def test_the_bench_runs_both_roles_end_to_end(monkeypatch):
    def fake(prompt, schema, config, temperature=None, label=""):
        if schema is DayDeclaration:
            return DayDeclaration(plan=f"{label} 불을 피우고 호수에 간다")
        return spoken(DayPlan(steps=[Step(op="drink")]))

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    config = bench_models.model_config("m@http://x:1", "openai", "http://unused", 4, 8192)
    assert (config.llm_model, config.llm_host) == ("m", "http://x:1")
    case = {"name": "P01", "text": "물을 마신다", "carried": ["a"], "names": [], "places": [], "camp": "", "problems": ["no_answer"], "t": 0}
    result = bench_models.bench_clerk(config, [case], sheet_limit=2, sheet_repeats=2)
    assert result["sheet_passed_each"] == [result["sheet"]["passed"]] * 2 and result["sheet_unsteady"] == []
    assert "| m@http://x:1 |" not in bench_models.markdown({"clerk": {}, "agent": {}})
    assert result["sheet"]["total"] == 2 and result["harvested"] == {**result["harvested"], "cases": 1, "clean": 1,
                                                                        "recorded_answer_problems": {"no_answer": 1}}
    mornings = [{"person": p, "day": 1, "prompt": "p", "temperature": 0.5} for p in ("P01", "P02", "P03")]
    agent = bench_models.bench_agent(config, mornings)
    assert agent["answered"] == 3 and agent["sameness"]["between_people"] > 0.5
    assert [p["person"] for p in agent["plans"]] == ["P01", "P02", "P03"]


def test_a_recorded_morning_gives_back_what_the_clerk_would_have_been_shown():
    from engine.primal.prompts import carried_lines, plan_prompt
    from engine.primal.scenario import build_world

    world = build_world(seed=0)
    person = next(iter(world.living()))
    context = bench_models.morning_context(plan_prompt(world, person.name))
    assert context["name"] == person.name
    assert context["carried"] == carried_lines(world, person.name)
    assert context["places"] == sorted(set(person.known_places) | {person.location})
    assert context["camp"] == person.camp
    assert context["names"] and set(context["names"]) <= world.acquaintances.get(person.name, set())
    written = ("당신은 P01입니다. 오늘은 2번째 날입니다.\n\n당신에 대한 사실:\n- 지금 있는 곳: 호수\n"
               "- 이곳에 있는 사람: P02, 처음 보는 사람 P09\n\n지니고 있는 것: 없음\n\n"
               "당신이 겪었거나 전해 들은 것 (오래된 것부터):\n- [1번째 날] 호수에서 처음 보는 사람 P11을(를) 봄\n\n")
    assert bench_models.morning_context(written) == {"name": "P01", "carried": [], "names": ["P02", "P11"], "places": ["호수"], "camp": ""}


def test_what_a_morning_prompt_let_fall_out_of_its_window_comes_back_from_the_same_runs_clerk_prompts(tmp_path):
    import json

    earlier = build_clerk_prompt("P01", "물을 마신다", [], ["P05"], ["호수"], "남쪽 야영지")
    later = build_clerk_prompt("P01", "잔다", [], ["P05", "P07"], ["호수"], "남쪽 야영지")
    morning = ("당신은 P01입니다. 오늘은 2번째 날입니다.\n\n당신에 대한 사실:\n- 지금 있는 곳: 호수\n- 이곳에 있는 사람: P02\n\n"
               "지니고 있는 것: 없음\n\n")
    rows = [{"label": "clerk:P01", "prompt": earlier, "t": 1.0}, {"label": "plan:P01", "prompt": morning, "temperature": 0.5, "t": 2.0},
            {"label": "clerk:P01", "prompt": later, "t": 3.0}]
    (tmp_path / "llm_calls.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    [found] = bench_models.recorded_mornings(tmp_path, {2})
    assert found["context"]["names"] == ["P02", "P05"]  # P07 was met after that morning
    assert found["context"]["camp"] == "남쪽 야영지"


def test_one_clerk_counts_every_models_attacks_and_thefts_and_the_same_mornings_sit_side_by_side(monkeypatch, tmp_path):
    import json

    from tools import bench_compare

    def rows(spec, texts):
        return [{"spec": spec, "day": 1, "person": f"P0{i}", "plan": text, "reasoning": "이유",
                 "context": {"name": f"P0{i}", "carried": ["칡뿌리"], "names": ["P02", "P03"], "places": ["호수"], "camp": "호수"}}
                for i, text in enumerate(texts, 1)]

    for folder, spec, texts, recorded in (("a", "m1", ["P02를 때린다", "물을 마신다"], "물을 마신다"),
                                          ("b", "m2", ["물을 마신다", "P03 몰래 칡뿌리를 가져간다"], "다른 기록")):
        (tmp_path / folder).mkdir()
        lines = rows(spec, texts) + rows(bench_models.BASELINE, [recorded, recorded])
        (tmp_path / folder / "agent_plans.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in lines), encoding="utf-8")

    def fake(prompt, schema, config, temperature=None, label=""):
        said = prompt.split('의 말: """', 1)[1]
        step = Step(op="attack", target="P02") if "때린다" in said else Step(op="steal", target="P03", what="칡뿌리") if "몰래" in said else Step(op="drink")
        return spoken(DayPlan(steps=[step]))

    monkeypatch.setattr(llm_agent, "call_llm_decision", fake)
    by_spec = bench_compare.load_plans([tmp_path / "a", tmp_path / "b"])
    assert {r["plan"] for r in by_spec[bench_models.BASELINE]} == {"물을 마신다"}
    counts = bench_compare.count_contests(by_spec, bench_models.model_config("clerk@http://x:1", "openai", "", 4, 8192))
    assert (counts["m1"]["attack"], counts["m1"]["steal"], counts["m1"]["share"]) == (1, 0, 0.5)
    assert (counts["m2"]["attack"], counts["m2"]["steal"], counts["m2"]["either"]) == (0, 1, 1)
    assert counts[bench_models.BASELINE]["either"] == 0 and counts["m1"]["examples"] == ["1일 P01: P02를 때린다"]
    samples = bench_compare.side_by_side(by_spec, 5)
    assert [(s["day"], s["person"]) for s in samples] == [(1, "P01"), (1, "P02")]
    assert set(samples[0]["plans"]) == {"m1", "m2", bench_models.BASELINE}
    text = bench_compare.markdown({"clerk": "clerk", "contests": counts, "side_by_side": samples})
    assert "| m1 | 2/2 | 1 | 0 | 1 | 0.5 |" in text and "P03 몰래 칡뿌리를 가져간다" in text


def test_a_server_enforcing_the_answer_schema_cannot_let_a_model_leave_a_field_out():
    from engine.primal.prompts import Reaction

    assert set(DayDeclaration.model_json_schema()["required"]) == {"plan", "reasoning", "same_as_yesterday"}
    assert set(Reaction.model_json_schema()["required"]) == {"response", "reasoning"}
    assert DayDeclaration().plan == "" and Reaction().response == ""  # saying nothing is still an answer
