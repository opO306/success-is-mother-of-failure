"""Phase 3: same starting scenario (a near-ready doomsayer + 3 vigilante
factions), run once with the existing heuristic decisions and once with
Qwen3 8B (via Ollama) making the judgment calls, then diff them side by side.

This is the tool for answering "is 8B actually shallow here?" with real
output instead of guessing — run it, read the reasoning strings, decide
whether Phase 3.5 (fine-tuning) is worth doing.

Requires Ollama running locally with the model in engine/config.py's
`llm_model` pulled (default "qwen3:8b"). If the LLM is unreachable, the
"llm" run transparently falls back to the heuristic decision per tick
(engine/llm_agent.py's fallback contract) — so this script never crashes,
it just shows the fallback happening in the reasoning column.
"""
import sys
import time

from engine.scenarios import build_llm_vs_heuristic_pair

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SEED = 0
TICKS = 15  # Phase 3.7: rounds x 7 members makes each vote ~4x costlier -- start modest


def run_and_collect(world) -> dict:
    wmd_log = []
    vigilante_log = []
    council_log = []
    exit_log = []  # (tick_index, MemberExitEvent)
    meeting_transcripts = []  # (tick_index, company_name, all_rounds)
    news_log = []
    for tick in world.run(TICKS):
        for w in tick.wmd_attempts:
            wmd_log.append((tick.index, w.company, w.leaked, w.leak_probability))
        for v in tick.vigilante_interventions:
            vigilante_log.append((tick.index, v.vigilante, v.intervened, v.target, v.intensity, v.reasoning))
        for outcome in tick.council_votes:
            council_log.append((tick.index, outcome))
        for exit_event in tick.member_exits:
            exit_log.append((tick.index, exit_event))
        # reset per-tick in World.tick(), so this only ever holds THIS tick's meetings
        for company_name, (roster, all_rounds) in world.last_meeting_transcripts.items():
            meeting_transcripts.append((tick.index, company_name, roster, all_rounds))
    news_log = list(world.news_log)
    return {
        "wmd": wmd_log, "vigilante": vigilante_log, "council": council_log,
        "exits": exit_log, "meetings": meeting_transcripts, "news": news_log,
        "final": {c.name: c.resources.legitimacy for c in world.companies},
        "survivors": {c.name: [e.name for e in c.employees] for c in world.companies},
        "individuals": [i.name for i in world.individuals],
        "ledgers": {
            c.name: [(e.name, e.wage, e.savings, e.unpaid_streak) for e in c.employees]
            for c in world.companies
        },
    }


def print_section(title: str, heuristic_rows, llm_rows, formatter) -> None:
    print(f"\n--- {title} ---")
    print(f"{'HEURISTIC':<70} | LLM")
    max_len = max(len(heuristic_rows), len(llm_rows))
    if max_len == 0:
        print("(이번 시드/틱 범위에서 이벤트 없음 — TICKS를 늘리거나 SEED를 바꿔보세요)")
        return
    for i in range(max_len):
        left = formatter(heuristic_rows[i]) if i < len(heuristic_rows) else ""
        right = formatter(llm_rows[i]) if i < len(llm_rows) else ""
        print(f"{left:<70} | {right}")


def main() -> None:
    from dataclasses import asdict

    from engine.config import SimulationConfig
    from engine import recorder as recording

    heuristic_world, llm_world = build_llm_vs_heuristic_pair(seed=SEED)
    run = recording.start_run(
        f"seed{SEED}", {"seed": SEED, "ticks": TICKS, "config": asdict(SimulationConfig())}
    )
    print(f"전체 기록 저장 위치: {run.root}")

    print(f"시드 {SEED}, {TICKS}틱 — 멸망론자 + 자경단 3파: 휴리스틱 vs LLM(Qwen3 8B) 판단 비교")
    print("LLM 서버가 응답 안 하면 자동으로 휴리스틱 규칙으로 폴백합니다 (reasoning에 표시).")

    t0 = time.time()
    heuristic_result = run_and_collect(heuristic_world)
    t1 = time.time()
    llm_result = run_and_collect(llm_world)
    t2 = time.time()
    print(f"소요 시간: 휴리스틱 {t1 - t0:.1f}s, LLM {t2 - t1:.1f}s")

    print_section(
        "멸망론자 WMD 실행 시도",
        heuristic_result["wmd"], llm_result["wmd"],
        lambda row: f"틱{row[0]:>3} {row[1]} 유출={row[2]} (확률{row[3]:.2f})",
    )
    def format_vigilante_row(row):
        tick, name, intervened, target, intensity, reasoning = row
        action = f"{target} 강도{intensity:.2f}" if intervened else "개입 안 함"
        return f"틱{tick:>3} {name}→{action}: {reasoning[:40]}"

    print_section("자경단 개입/판단", heuristic_result["vigilante"], llm_result["vigilante"], format_vigilante_row)

    if llm_result["council"]:
        companies_with_councils = sorted({outcome.company for _, outcome in llm_result["council"]})
        for company_name in companies_with_councils:
            rows = [(t, o) for t, o in llm_result["council"] if o.company == company_name]
            # everyone who ever sat on this council, in first-seen order -- people
            # who left partway through still have a history worth printing
            member_names = []
            for _, outcome in rows:
                for m in outcome.member_results:
                    if m.name not in member_names:
                        member_names.append(m.name)

            print(f"\n--- {company_name} 의회 표결 요약 (틱별 찬성표수) ---")
            for tick_index, outcome in rows:
                phase = "실행/발표여부" if ("실행한다" in outcome.action_description or "발표한다" in outcome.action_description) else "투자여부"
                print(f"틱{tick_index:>3} [{phase}] 찬성 {outcome.votes_for}/{outcome.votes_total} -> "
                      f"{'가결' if outcome.proceeds else '부결'}, 외부유출={'있음' if outcome.disclosed else '없음'} "
                      f"({outcome.action_description})")

            print(f"\n--- {company_name} 구성원별 표결 이력 (틱이 지날수록 갈라지는 지점이 있는지) ---")
            for name in member_names:
                history = []
                for tick_index, outcome in rows:
                    m = next((r for r in outcome.member_results if r.name == name), None)
                    history.append(("찬" if m.support else "반") if m is not None else "·")
                print(f"  {name}: {''.join(history)}")

            # print full reasoning only for the last few votes (where memory has
            # had the most ticks to accumulate and any divergence would show up)
            print(f"\n--- {company_name} 최근 5회 표결의 최종 라운드 reasoning ---")
            for tick_index, outcome in rows[-5:]:
                print(f"\n틱 {tick_index} [{outcome.action_description}]: 찬성 {outcome.votes_for}/{outcome.votes_total}")
                for m in outcome.member_results:
                    vote = "찬성" if m.support else "반대"
                    disclose = " [외부에 알림]" if m.disclosed else ""
                    print(f"  - {m.name} ({m.source}) {vote}{disclose}: {m.reasoning}")

            print(f"\n--- {company_name} 최근 2회 회의의 라운드별 전체 토론 (의견이 라운드마다 바뀌는지) ---")
            company_meetings = [m for m in llm_result["meetings"] if m[1] == company_name]
            for tick_index, _, roster, all_rounds in company_meetings[-2:]:
                print(f"\n=== 틱 {tick_index} ({company_name}) — {len(all_rounds)}라운드 ===")
                for round_num, round_responses in enumerate(all_rounds, start=1):
                    print(f" [라운드 {round_num}]")
                    for member_name, resp in zip(roster, round_responses):
                        if resp is None:
                            print(f"   {member_name}: (응답 실패)")
                            continue
                        vote = "찬성" if resp.support_action else "반대"
                        disclose = " [외부공개]" if resp.disclose_to_outsiders else ""
                        print(f"   {member_name} {vote}{disclose}: {resp.reasoning}")

    print("\n--- 구성원의 개인적 선택 (남기/떠나기/새 조직/은퇴) ---")
    for label, result in (("휴리스틱", heuristic_result), ("LLM", llm_result)):
        if not result["exits"]:
            print(f"{label}: 아무도 조직을 떠나지 않음")
            continue
        print(f"{label}:")
        for tick_index, event in result["exits"]:
            became = f" -> {event.became}" if event.became else ""
            blocked = f" [무산: {event.blocked_reason}]" if event.blocked_reason else ""
            intent = f" | 본인의 말: {event.intent}" if event.intent else ""
            print(f"  틱{tick_index:>3} {event.company}/{event.member} {event.action}{became}{blocked} "
                  f"(저축 {event.savings_at_exit:.1f}){intent}")

    print("\n--- 구성원 개인 장부 (LLM, 최종) ---")
    for company_name, ledger in llm_result["ledgers"].items():
        if not ledger:
            continue
        print(f"  {company_name}:")
        for name, wage, savings, streak in ledger:
            flag = f" 급여 {streak}분기째 밀림" if streak else ""
            print(f"    {name}: 급여={wage:.1f} 저축={savings:+.1f}{flag}")

    print("\n--- 최종 잔류 인원 (LLM) ---")
    for company_name, names in llm_result["survivors"].items():
        print(f"  {company_name}: {len(names)}명 {names}")
    if llm_result["individuals"]:
        print(f"  무소속 개인: {llm_result['individuals']}")

    if llm_result["news"]:
        print("\n--- LLM 세계 뉴스 로그 (순수 코드 기록, 전체) ---")
        for entry in llm_result["news"]:
            print(f"  - {entry}")

    print("\n--- 최종 정당성(legitimacy) ---")
    all_names = sorted(set(heuristic_result["final"]) | set(llm_result["final"]))
    print(f"{'기업':<14} {'휴리스틱':>10} {'LLM':>10}")
    for name in all_names:
        h = heuristic_result["final"].get(name, float("nan"))
        l = llm_result["final"].get(name, float("nan"))
        print(f"{name:<14} {h:>10.3f} {l:>10.3f}")


if __name__ == "__main__":
    from engine import recorder as recording

    try:
        main()
    finally:
        recording.stop_run()
