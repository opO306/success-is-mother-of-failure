"""Phase 5.0 agent world: the engine holds truth and arithmetic, every decision comes from a person.

Requires Ollama with engine/config.py's `llm_model`. Everything the run produces is written under runs/.
"""
import json
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from engine import recorder as recording
from engine.config import SimulationConfig
from engine.scenarios import build_agent_world

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 0
TICKS = 15


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _print_ops(operations: list[dict], results: list[dict]) -> None:
    for op, result in zip(operations, results):
        status = "성공" if result["ok"] else "실패"
        print(f"      → {op['op']} target={op.get('target')} amount={op.get('amount')} | {status}: {result['detail']}")


def _report(root: Path, world) -> None:
    calls = _read(root / "llm_calls.jsonl")
    print(f"\nLLM 호출 {len(calls)}건 (실패 {sum(not c['ok'] for c in calls)}건)")
    by_kind = Counter(c["label"].split(":")[0] for c in calls)
    print("호출 종류:", dict(by_kind))

    declarations = _read(root / "declarations.jsonl")
    silent = sum(1 for d in declarations if not d["declaration"])
    print(f"선언 {len(declarations)}건 (아무것도 안 함 {silent}건)")

    transcriptions = _read(root / "transcriptions.jsonl")
    print("받아적힌 동작:", dict(Counter(o["op"] for t in transcriptions for o in t["operations"])))
    print("\n--- 선언과 받아적기 (최근 20건) ---")
    for t in transcriptions[-20:]:
        print(f"틱{t['tick']:>2} {t['person']}: {t['declaration']}")
        _print_ops(t["operations"], t["results"])

    resolutions = _read(root / "resolutions.jsonl")
    print(f"\n--- 가결된 결의 {len(resolutions)}건 ---")
    for r in resolutions:
        print(f"틱{r['tick']:>2} {r['org']} (제안 {r['proposer']}): {r['proposal']}")
        _print_ops(r["operations"], r["results"])

    print("\n--- 최종 상태 (사람만 보는 표: 원형은 시작 조건일 뿐 에이전트에게 보이지 않음) ---")
    for c in world.companies:
        state = "생존" if c.alive else "해산"
        print(
            f"  {c.name} [{c.archetype.name}] {state}: {len(c.employees)}명, "
            f"자본 {c.resources.capital:.1f}, 기술 {c.resources.tech:.1f}, 강제력 {c.resources.coercion:.2f}"
        )
    for v in world.vigilantes:
        print(f"  {v.name} [자경단, {v.disposition}] 돈 {v.resources.capital:.1f}")
    for i in world.individuals:
        print(f"  {i.name} [무소속] 돈 {i.resources.capital:.1f}")


def main() -> None:
    run = recording.start_run(
        f"agent_seed{SEED}", {"seed": SEED, "ticks": TICKS, "mode": "agent", "config": asdict(SimulationConfig())}
    )
    print(f"전체 기록 저장 위치: {run.root}")
    world = build_agent_world(seed=SEED)
    print("조직 (에이전트가 보는 이름 → 시작 조건 원형):")
    for c in world.companies:
        print(f"  {c.name} → {c.archetype.name}, {len(c.employees)}명, 자본 {c.resources.capital:.1f}")

    started = time.time()
    for _ in range(TICKS):
        tick_started = time.time()
        tick = world.tick()
        alive = sum(1 for c in world.companies if c.alive)
        print(
            f"틱 {tick.index:>2}: 표결 {len(tick.council_votes)}건, 이동 {len(tick.member_exits)}건, "
            f"살아있는 조직 {alive}, {time.time() - tick_started:.0f}s"
        )
    print(f"총 {time.time() - started:.0f}s")
    _report(run.root, world)


if __name__ == "__main__":
    try:
        main()
    finally:
        recording.stop_run()
