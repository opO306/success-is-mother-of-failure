"""The clerk's fixed sheet: things people in the primal land would say, with the acts each must and must not become.

Labels starting with H or N are held out: they were written after the clerk prompt was last shaped and never shown to it.
Qwen3-8B on 2026-09-14: 31/46, held out 12/16 (the same before and after the place and talk guards).

  python -m tools.clerk_sheet [--backend ollama --host http://localhost:11434 --model qwen3:8b]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time

from engine import llm_agent
from engine.config import SimulationConfig
from engine.primal import prompts
from engine.primal.clerk import keep_said, transcribe
from engine.primal.scenario import build_world

# (label, what was said, acts that must appear in this order, acts that must not appear). {B} is a person they know.
CASES: list[tuple[str, str, list[str], list[str]]] = [
    ("물", "새벽에 북쪽 개울로 가서 물을 마시고 강돌을 몇 개 줍는다.", ["go", "drink", "gather"], []),
    ("돌깨기", "3번 강돌로 부싯돌을 세게 내리친다.", ["strike"], ["attack"]),
    ("반죽", "점토 강둑에서 점토를 파서 물을 섞어 반죽하고 오목하게 빚는다.", ["gather", "mix", "shape"], []),
    ("말리기", "빚은 흙덩이를 낮 동안 햇볕에 말린다.", ["dry"], []),
    ("굽기", "저녁에 북쪽 야영지로 돌아가 불 속에 그 흙덩이를 넣고 오래 굽는다.", ["go", "heat"], []),
    ("붓기", "구운 흙덩이에 물을 부어서 새는지 본다.", ["test"], []),
    ("사냥", "북쪽 숲에서 사슴을 몰래 쫓아가 1번 날카로운 돌로 찌른다.", ["hunt"], ["attack", "talk"]),
    ("가르기", "쓰러뜨린 사슴을 부싯돌 조각으로 갈라 고기와 가죽을 얻는다.", ["cut"], []),
    ("가죽", "가죽 안쪽을 부싯돌 조각으로 긁어내고 햇볕에 말린다.", ["scrape", "dry"], []),
    ("묶기", "나뭇가지 끝에 부싯돌 조각을 힘줄로 단단히 묶는다.", ["bind"], []),
    ("불", "마른 풀과 나뭇가지로 불을 피운다.", ["fire"], []),
    ("움막", "북쪽 숲에서 나뭇가지와 나무껍질을 모아 북쪽 야영지에 비를 피할 움막을 짓는다.", ["gather", "go", "build"], []),
    ("심기", "동쪽 초원에서 들풀 씨앗을 모아 땅에 묻어 둔다.", ["gather", "plant"], []),
    ("담그기", "도토리를 물에 하룻밤 담가 둔다.", ["soak"], []),
    ("밀봉", "산딸기를 구운 흙덩이에 담고 가죽으로 입구를 막아 둔다.", ["fill", "cover"], []),
    ("주기", "{B}에게 칡뿌리 하나를 준다.", ["give"], ["talk"]),
    ("말", "{B}에게 오늘 같이 사슴을 잡자고 말한다.", ["talk"], ["hunt"]),
    ("노래", "모두 둥글게 앉아 손뼉을 치며 노래한다.", ["intent"], ["attack"]),
    ("따라", "{B}을 하루 종일 따라다닌다.", ["follow"], []),
    ("이름", "이 오목한 흙덩이를 '물담이'라고 부르기로 한다.", ["name"], []),
    ("맛보기", "붉은 버섯을 조금 맛본다.", ["test"], ["eat"]),
    ("불지킴", "밤에 불가에서 자고 새벽까지 불을 지킨다.", ["sleep"], ["attack"]),
    ("훔치기", "{B}이 자는 틈에 그의 부싯돌 조각을 몰래 가져온다.", ["steal"], ["talk", "attack"]),
    ("때리기", "{B}을 돌로 내리친다.", ["attack"], ["strike"]),
    ("조건", "늑대가 오면 불붙은 나뭇가지를 휘두르며 도망친다.", [], ["attack"]),
    ("먹이", "사슴에게 들사과를 던져 준다.", ["feed"], ["attack", "hunt"]),
    ("낚시", "호수에 가서 맨손으로 물고기를 잡는다.", ["go", "fish"], []),
    ("갈기", "뼈를 사암에 문질러 뾰족하게 간다.", ["grind"], []),
    ("기도", "하늘에 대고 비가 그치게 해 달라고 빈다.", ["intent"], ["talk"]),
    ("쉬기", "오늘은 아무것도 하지 않고 동굴에 가서 쉰다.", ["go", "rest"], []),
    ("H모래", "개울가에서 점토 대신 모래를 섞어 본다.", ["mix"], []),
    ("H불꽃", "돌 두 개를 서로 부딪쳐 불꽃이 튀는지 본다.", ["strike"], ["attack"]),
    ("H육포", "고기를 잘게 잘라 햇볕에 말려 둔다.", ["cut", "dry"], []),
    ("H제안", "무리 사람들에게 동쪽으로 가 보자고 말한다.", ["talk"], ["go"]),
    ("H구경", "들소 벌판까지 가서 들소를 구경만 한다.", ["go"], ["hunt", "attack"]),
    ("H바구니", "엮은 풀 바구니에 도토리를 담는다.", ["fill"], []),
    ("H돌데우기", "불에 달군 돌을 물에 넣어 물을 데운다.", ["heat"], []),
    ("H그림", "잠들기 전에 동굴 벽에 숯으로 사슴을 그린다.", ["intent"], ["hunt"]),
    ("N날세우기", "강가에서 납작한 돌을 주워 모서리를 사암에 갈아 날을 세운다.", ["gather", "grind"], []),
    ("N토끼", "토끼 굴 앞에서 기다렸다가 토끼를 잡는다.", ["hunt"], ["attack", "steal"]),
    ("N반씩", "들사과를 따서 반은 먹고 나머지는 가죽 주머니에 넣어 둔다.", ["gather", "eat", "fill"], []),
    ("N지붕", "움막 지붕에 풀을 더 엮어 올린다.", [], ["attack", "hunt"]),
    ("N가죽말리기", "젖은 가죽을 불 옆에 걸어 말린다.", ["dry"], ["heat"]),
    ("N토란", "{B}과 함께 늪에서 토란을 캔다.", ["gather"], ["attack"]),
    ("N끓이기", "구운 흙덩이에 물을 담아 불 위에 올려 끓인다.", ["fill", "heat"], []),
    ("N일찍", "내일 아침 일찍 떠날 수 있게 오늘 밤은 일찍 잔다.", ["sleep"], ["go"]),
]


def run_sheet(config: SimulationConfig, limit: int | None = None) -> dict:
    """Every sentence through the real pipeline (clerk answer, then the guards), asked at once."""
    world = build_world(seed=0)
    speaker = next(p for p in world.people.values() if p.camp == "북쪽 야영지")
    mate = sorted(world.acquaintances[speaker.name])[0]
    speaker.known_places = set(world.lands)
    items = prompts.carried_lines(world, speaker.name)
    names, places = sorted(world.acquaintances[speaker.name]), sorted(speaker.known_places)
    cases = CASES[:limit] if limit else CASES
    sentences = [sentence.replace("{B}", mate) for _, sentence, _, _ in cases]
    started = time.perf_counter()
    plans = llm_agent.run_concurrently(
        [lambda s=s: transcribe(speaker.name, s, items, names, places, speaker.camp, config) for s in sentences], config,
    )
    results = []
    for (label, _, must, must_not), sentence, plan in zip(cases, sentences, plans):
        steps = keep_said(plan.steps, sentence) if plan is not None else []
        ops = [s.op for s in steps]
        remaining = iter(ops)
        ok = plan is not None and all(any(op == m for op in remaining) for m in must) and not any(op in must_not for op in ops)
        results.append({"label": label, "sentence": sentence, "held_out": label.startswith(("H", "N")), "ok": ok,
                        "steps": [s.model_dump(exclude_defaults=True) for s in steps]})
    held = [r for r in results if r["held_out"]]
    return {"passed": sum(r["ok"] for r in results), "total": len(results), "held_passed": sum(r["ok"] for r in held),
            "held_total": len(held), "seconds": round(time.perf_counter() - started, 1), "cases": results}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="ollama")
    parser.add_argument("--host", default=SimulationConfig().llm_host)
    parser.add_argument("--model", default=SimulationConfig().llm_model)
    parser.add_argument("--concurrency", type=int, default=SimulationConfig().llm_concurrency)
    args = parser.parse_args(argv)
    config = dataclasses.replace(SimulationConfig(), llm_backend=args.backend, llm_host=args.host, llm_model=args.model,
                                 llm_concurrency=args.concurrency)
    result = run_sheet(config)
    for case in result["cases"]:
        print(f"[{'OK ' if case['ok'] else 'BAD'}] {case['label']}: {case['sentence']}")
        for step in case["steps"]:
            print("       ", json.dumps(step, ensure_ascii=False))
    print(f"\n{result['passed']}/{result['total']} passed (held out {result['held_passed']}/{result['held_total']}), {result['seconds']}s")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
