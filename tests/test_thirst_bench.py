import json

from tools import thirst_bench


def test_a_plan_is_judged_by_whether_water_comes_before_other_work():
    assert thirst_bench.judge("새벽에 북쪽 개울로 가서 물을 마시고, 낮에는 부싯돌로 불을 피운다") == {"water": True, "drink": True, "water_first": True}
    assert thirst_bench.judge("부싯돌로 불을 피우고 저녁에 개울에서 물을 마신다")["water_first"] is False
    assert thirst_bench.judge("부싯돌 조각을 치는 연습을 한다") == {"water": False, "drink": False, "water_first": False}


def test_mornings_are_chosen_by_what_the_prompt_says_not_by_how_the_life_ended(tmp_path):
    run = tmp_path / "w"
    run.mkdir()
    parched = "오늘은 4번째 날입니다. 당신은 P07입니다.\n- 지금 몸과 마음에 오는 것: 목이 타들어 가고 혀가 입천장에 붙는다 / 배가 고프다\n"
    hungry = "오늘은 4번째 날입니다. 당신은 P08입니다.\n- 지금 몸과 마음에 오는 것: 배가 고프다 / 목이 타들어 가고\n"
    calls = [{"label": "plan:P07", "ok": True, "prompt": parched, "temperature": 0.8},
             {"label": "plan:P08", "ok": True, "prompt": hungry, "temperature": 0.8},
             {"label": "clerk:P07", "ok": True, "prompt": parched, "temperature": 0.0}]
    plans = [{"person": "P07", "day": 4, "plan": "불을 피운다"}, {"person": "P08", "day": 4, "plan": "물을 마신다"}]
    (run / "llm_calls.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in calls), encoding="utf-8")
    (run / "plans.jsonl").write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in plans), encoding="utf-8")
    mornings = thirst_bench.parched_mornings([run], limit=10)
    assert [(m["person"], m["day"], m["recorded"]) for m in mornings] == [("P07", 4, "불을 피운다")]
