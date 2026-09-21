"""Phase 2 validation batch: confirms the heuristic-driven engine is stable
and matches the design doc's pre-registered predictions BEFORE any LLM
judgment is wired in (see .claude/plans -> Phase 2 plan, "완료 기준").
"""
import json
import statistics
import sys
from dataclasses import asdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from engine.batch import (
    DEFAULT_SEEDS,
    DEFAULT_TICKS,
    observe_espionage_tech_gap,
    run_emotionless_ab_batch,
    run_hive_mind_ab_batch,
    run_invariant_batch,
)


def main(seeds: int = DEFAULT_SEEDS, ticks: int = DEFAULT_TICKS) -> None:
    report: dict = {"seeds": seeds, "ticks": ticks, "checks": {}}

    print(f"[1/4] invariant batch ({seeds} seeds x {ticks} ticks, full 19-archetype world)...")
    invariants = run_invariant_batch(seeds, ticks)
    passed = invariants.passed
    print(f"      violations={len(invariants.violations)} exceptions={len(invariants.exceptions)} -> {'PASS' if passed else 'FAIL'}")
    for v in invariants.violations[:10]:
        print(f"      - seed {v.seed} tick {v.tick}: {v.detail}")
    for e in invariants.exceptions[:10]:
        print(f"      - {e}")
    report["checks"]["invariants"] = {
        "passed": passed,
        "violation_count": len(invariants.violations),
        "exception_count": len(invariants.exceptions),
    }

    print(f"\n[2/4] emotionless (treatment) vs control trade A/B ({seeds} seeds, R=-1.0 scripted)...")
    ab_trade = run_emotionless_ab_batch(seeds, ticks, scripted_relationship=-1.0)
    trade_passed = (
        ab_trade.treatment_proceed_rate_when_possible > 0.9 and ab_trade.control_proceed_rate_when_possible < 0.1
    )
    print(
        f"      when the pair could trade: treatment={ab_trade.treatment_proceed_rate_when_possible:.2f} "
        f"control={ab_trade.control_proceed_rate_when_possible:.2f} -> {'PASS' if trade_passed else 'FAIL'}\n"
        f"      over all ticks: treatment={ab_trade.treatment_proceed_rate:.2f} "
        f"control={ab_trade.control_proceed_rate:.2f} (a company died in {ab_trade.seeds_with_a_death}/{seeds} seeds)"
    )
    report["checks"]["emotionless_ab"] = {"passed": trade_passed, **asdict(ab_trade)}

    print(f"\n[3/4] hive-mind vs ordinary legitimacy-shock recovery A/B ({seeds} seeds)...")
    ab_legit = run_hive_mind_ab_batch(seeds, ticks_before_shock=5, ticks_after_shock=20)
    hive_no_recovery = abs(ab_legit.hive_mind_final - ab_legit.hive_mind_post_shock) < 1e-9
    ordinary_recovered = ab_legit.ordinary_final > ab_legit.ordinary_post_shock + 1e-6
    legit_passed = hive_no_recovery and ordinary_recovered
    print(
        f"      hive: pre={ab_legit.hive_mind_pre_shock:.3f} post={ab_legit.hive_mind_post_shock:.3f} final={ab_legit.hive_mind_final:.3f}\n"
        f"      ord.: pre={ab_legit.ordinary_pre_shock:.3f} post={ab_legit.ordinary_post_shock:.3f} final={ab_legit.ordinary_final:.3f}\n"
        f"      -> {'PASS' if legit_passed else 'FAIL'}"
    )
    report["checks"]["hive_mind_ab"] = {"passed": legit_passed, **asdict(ab_legit)}

    print(f"\n[4/4] espionage/Red Queen tech-gap observation ({seeds} seeds, no pre-registered direction)...")
    gaps = observe_espionage_tech_gap(seeds, ticks)
    initial_mean = statistics.mean(g.initial_gap for g in gaps)
    final_mean = statistics.mean(g.final_gap for g in gaps)
    print(f"      mean tech gap: initial={initial_mean:.2f} final={final_mean:.2f} (observational only, no pass/fail)")
    report["checks"]["espionage_tech_gap"] = {
        "observational_only": True,
        "initial_gap_mean": initial_mean,
        "final_gap_mean": final_mean,
    }

    overall_pass = passed and trade_passed and legit_passed
    report["overall_pass"] = overall_pass
    print(f"\n=== overall: {'PASS — ready for Phase 3 (Ollama+Qwen3 8B)' if overall_pass else 'FAIL — see above'} ===")

    with open("validation_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("\nwrote validation_results.json")


if __name__ == "__main__":
    main()
