"""Run the G7.3c blind research loop on every benchmark scenario, store each
run in the research store (default: D: vault), and score it (G7.4) against
the sealed answer key in `ground_truth/benchmark/`.

Scenarios are built *from* the answer-key files, so the world B runs on and
the world the key describes cannot drift apart.

    python run_blind_benchmark.py                 # store to the D: vault
    python run_blind_benchmark.py --root PATH     # store somewhere else
    python run_blind_benchmark.py --verify-only   # just check the store

Store root resolution: --root, else $SIMOF_RESEARCH_STORE, else the default
below. Refuses to write from a dirty working tree unless --allow-dirty:
a record's commit must be enough to reproduce it.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_research_loop import run_blind_research
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.blind_tools import Tool
from research_store.b_visible import BVisibleReader
from engine.deterministic.research_journal import ResearchJournal
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
from research_store.evaluator import verify_store
from ground_truth.benchmark_key import KEY_DIRECTORY_V2, key_digest, load_answer_key
from research_store.ingest_blind import store_blind_research_run
from research_store.provenance import BLIND_RESEARCH_SEMANTICS, provenance
from research_store.language_gaps import store_language_gap_report
from research_store.score_blind import CONFIDENT_WRONG, GROUP_OF, VERDICTS, store_score

REPO = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(r"D:\KiroCrewTraceVault\success-is-mother-of-failure\research_store")

README = """research_store -- 성공은 실패의 어머니 연구 데이터 저장소

b_visible/     B가 볼 수 있었던 데이터만 (별칭 전용). 학습형 B의 학습 데이터는 여기서만 가져온다.
evaluator/     실제 세계 이름, 실제 spec, 별칭<->실제 대응표. B 학습 데이터에 절대 섞지 않는다.
ground_truth/  정답·채점 (G7.4부터).

각 tier: objects/ (내용 해시가 파일 이름, 수정 불가), index.jsonl (해시 체인, 추가만 가능).
모든 레코드에 commit / dirty / producer / semantics 가 붙는다. semantics 가 다른 결과는 합산 금지.
dirty 판정: 추적 파일 중 .claude/ 밖의 것이 커밋과 다르면 dirty (.claude/ 는 도구 상태라 제외, 그 외 예외 없음).
b_visible 쓰기: 금지 목록 + 허용 목록 이중 검사.
무결성 검사: python run_blind_benchmark.py --verify-only
저장소 계약·semantics 이력: 저장소의 docs/current/RESEARCH_STORE_V1.md

이 저장소 도입 이전의 runs/ 데이터는 출처 정보(commit, semantics)가 없어 들어 있지 않다.
"""


def spec_from_key(scenario: dict) -> SyntheticWorldSpec:
    world = scenario["world"]
    return SyntheticWorldSpec(
        world_id=world["world_id"], world_revision=world["world_revision"],
        variables=tuple(world["variables"]),
        initial_values=tuple((v, world["initial_values"][v]) for v in world["variables"]), clamps=(),
        public_controls=tuple(world["public_controls"]), public_observables=tuple(world["public_observables"]),
        ticks=world["ticks"])


SEEDS = (0, 1, 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("SIMOF_RESEARCH_STORE", DEFAULT_ROOT)))
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root: Path = args.root

    if args.verify_only:
        print(verify_store(root))
        return 0

    prov = provenance(REPO, BLIND_RESEARCH_SEMANTICS, "run_blind_benchmark.py")
    if prov["dirty"] and not args.allow_dirty:
        print("working tree has uncommitted changes -- commit first, or pass --allow-dirty", file=sys.stderr)
        return 2
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.txt").write_text(README, encoding="utf-8")  # documentation, not store data

    key = load_answer_key(KEY_DIRECTORY_V2)  # the key for grammar v2, the language B now speaks
    print(f"answer key {key_digest(key)} ({len(key)} scenarios)")
    totals = {verdict: 0 for verdict in VERDICTS}
    # B's toolbox: tools it composed in earlier runs (b_visible memory only),
    # growing as this invocation adds more.
    toolbox = tuple(Tool.from_canonical(t) for t in BVisibleReader(root).toolbox(semantics=BLIND_RESEARCH_SEMANTICS))
    print(f"toolbox at start: {len(toolbox)} tool(s)")
    with tempfile.TemporaryDirectory() as scratch:
        for name, scenario in key.items():
            spec = spec_from_key(scenario)
            for seed in SEEDS:
                world, manifest = make_blind_session(spec, seed)
                journal_path = Path(scratch) / f"{name}-{seed}.jsonl"
                journal = ResearchJournal.create(journal_path)
                outcome = run_blind_research(world, control_descriptors(spec, seed),
                                             observable_descriptors(spec, seed),
                                             SyntheticBlindAExecutor(spec, manifest), journal, toolbox=toolbox)
                journal.close()
                b_record, e_record = store_blind_research_run(root, real_spec=spec, seed=seed, manifest=manifest,
                                                              outcome=outcome, journal_path=journal_path,
                                                              provenance=prov)
                _score_record, score = store_score(root, key, name, b_record, e_record, prov)
                toolbox += tuple(Tool.from_canonical(u["tool"]) for u in outcome.tools_used if not u["reused"])
                for verdict, count in score["counts"].items():
                    totals[verdict] += count
                graded = " ".join(f"{q['target']}={q['verdict']}"
                                  + ("" if q["diagnosis_consistent"] else "(diagnosis!)")
                                  + ("(found-but-untested)" if q.get("proposal_matches_best_answer") else "")
                                  for q in score["questions"])
                print(f"{name:20s} seed={seed} discovery={outcome.discovery_experiment_count:2d} "
                      f"validation={outcome.validation_experiment_count:2d} "
                      f"tools={[(u['tool']['pattern'], 'reused' if u['reused'] else 'new') for u in outcome.tools_used]}"
                      f"  {graded}")
    print()
    for group in ("SOLVED_SUCCESS", "HONEST_SUCCESS", "FAILURE", "UNSCORED"):
        for verdict in VERDICTS:
            if GROUP_OF[verdict] == group:
                print(f"  {group:15s} {verdict:22s} {totals[verdict]:3d}")
    gate = "PASS" if totals[CONFIDENT_WRONG] == 0 else "FAIL"
    print(f"hard gate CONFIDENT_WRONG == 0: {gate}")
    _gap_record, gaps = store_language_gap_report(root, key, key_digest(key), prov,
                                                  b_semantics=BLIND_RESEARCH_SEMANTICS)
    print(f"language gaps (same B record, different real structure): {len(gaps)}")
    for gap in gaps:
        record = gap["b_record"]
        cases = ", ".join(f"{c['scenario_id']}:{c['structural_claim']['kind'] if c['structural_claim'] else '-'}"
                          f"{' (hidden variable)' if c['hidden_variable_present'] else ''}" for c in gap["cases"])
        print(f"  {record['target']} {record['b_verdict']} {record['b_diagnosis']} <- {cases}")
    print(verify_store(root))
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
