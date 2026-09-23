"""Run the G7.3c blind research loop on the benchmark worlds and store every
run in the research store (default: D: vault).

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
from engine.deterministic.research_journal import ResearchJournal
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
from research_store.evaluator import verify_store
from research_store.ingest_blind import store_blind_research_run
from research_store.provenance import BLIND_RESEARCH_SEMANTICS, provenance

REPO = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(r"D:\KiroCrewTraceVault\success-is-mother-of-failure\research_store")
V = ("x1", "x2", "x3")

README = """research_store -- 성공은 실패의 어머니 연구 데이터 저장소

b_visible/     B가 볼 수 있었던 데이터만 (별칭 전용). 학습형 B의 학습 데이터는 여기서만 가져온다.
evaluator/     실제 세계 이름, 실제 spec, 별칭<->실제 대응표. B 학습 데이터에 절대 섞지 않는다.
ground_truth/  정답·채점 (G7.4부터).

각 tier: objects/ (내용 해시가 파일 이름, 수정 불가), index.jsonl (해시 체인, 추가만 가능).
모든 레코드에 commit / dirty / producer / semantics 가 붙는다. semantics 가 다른 결과는 합산 금지.
무결성 검사: python run_blind_benchmark.py --verify-only
저장소 계약: 저장소의 docs/current/RESEARCH_STORE_V1.md

이 저장소 도입 이전의 runs/ 데이터는 출처 정보(commit, semantics)가 없어 들어 있지 않다.
"""


def _spec(world_id, revision, variables, controls, ticks, initial=None) -> SyntheticWorldSpec:
    initial = initial or {}
    return SyntheticWorldSpec(world_id=world_id, world_revision=revision, variables=variables,
                              initial_values=tuple((v, initial.get(v, False)) for v in variables), clamps=(),
                              public_controls=controls, public_observables=variables, ticks=ticks)


BENCHMARK = {
    "S01": _spec("WORLD-S01", "R-7F93C2", ("x1", "x3"), ("x1",), 1),
    "S02-t1": _spec("WORLD-S02", "R-A18D40", V, ("x1", "x2"), 1),
    "S02-t2": _spec("WORLD-S02", "R-A18D40", V, ("x1", "x2"), 2),
    "S03-t1": _spec("WORLD-S03", "R-51E8B7", V, ("x1", "x2"), 1),
    "S03-t2": _spec("WORLD-S03", "R-51E8B7", V, ("x1", "x2"), 2),
    "S02-x2-starts-true": _spec("WORLD-S02", "R-A18D40", V, ("x1", "x2"), 1, {"x2": True}),
}
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
    if not (root / "README.txt").exists():
        (root / "README.txt").write_text(README, encoding="utf-8")

    with tempfile.TemporaryDirectory() as scratch:
        for name, spec in BENCHMARK.items():
            for seed in SEEDS:
                world, manifest = make_blind_session(spec, seed)
                journal_path = Path(scratch) / f"{name}-{seed}.jsonl"
                journal = ResearchJournal.create(journal_path)
                outcome = run_blind_research(world, control_descriptors(spec, seed),
                                             observable_descriptors(spec, seed),
                                             SyntheticBlindAExecutor(spec, manifest), journal)
                journal.close()
                b_record, _ = store_blind_research_run(root, real_spec=spec, seed=seed, manifest=manifest,
                                                       outcome=outcome, journal_path=journal_path, provenance=prov)
                print(f"{name:20s} seed={seed} {outcome.termination:9s} "
                      f"discovery={outcome.discovery_experiment_count:2d} "
                      f"validation={outcome.validation_experiment_count:2d} "
                      f"verdicts={b_record.tags['verdicts']} protocol_valid={b_record.tags['protocol_valid']}")
    print(verify_store(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
