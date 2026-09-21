"""Build a non-destructive, hash-addressed project catalog for LLM handoff."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "LLM_HANDOFF"

CURRENT_A_MODULES = {
    "causal_kernel.py", "causal_spec.py", "environment_kernel.py", "environment_spec.py",
    "gpu_environment.py", "kernel.py", "physical_environment_scaling.py", "physical_scale.py",
    "scaling.py", "spec.py",
}
CURRENT_B_MODULES = {
    "adapter_comparison.py", "b_language.py", "brain_adapter.py", "change_graph.py",
    "cognitive_map.py", "counterfactual.py", "environment_world_model.py", "experiment_proposal.py",
    "hypotheses.py", "impact_scope.py", "provenance.py", "theory_revision.py",
    "trace_view_broker.py", "world_model.py",
}
CURRENT_RUN_DIRS = {
    "b_language_exact_adapter_v1", "cognitive_map_benchmark_v1", "deterministic_scaling_audit_v1",
    "gpu_environment_parity_v1", "gpu_resident_benchmark_v1", "physical_environment_scaling_audit_v1",
    "physical_scale_audit_v1",
}
PROB_RUN_PREFIXES = (
    "dual_gcp_", "local15_observer_", "local30_face_", "local30_lifecycle_", "local30_ligation_",
    "local30_lineage_", "local30_spatial_", "local60_observer_", "vm4h_lifecycle_",
    "component_motion_", "face_selective_", "inherited_context_", "lifecycle_", "ligation_",
    "local_dynamics_", "material_lifecycle_", "nonliving_", "physical_recombination_",
    "remote_lifecycle_", "remote_parallel_", "sequence_probe_", "spatial_boundary_", "spatial_energy_",
    "spatial_sequence_", "spatial_until_",
)
PROB_SCRIPT_NAMES = {
    "analyze_sequence_archive.py", "audit_join_bottlenecks.py", "compare_sequence_probe_records.py",
    "prepare_dual_gcp_manifest.py", "prepare_experiment_manifest.py", "run_compartment_lineage_probe.py",
    "run_component_motion_probe.py", "run_inherited_context_probe.py", "run_integrated_world_probe.py",
    "run_local_dynamics_probe.py", "run_nonliving_face_until.py", "run_nonliving_world_probe.py",
    "run_observer_cohort.py", "run_physical_recombination_probe.py", "run_sequence_probe.py",
    "run_spatial_boundary_probe.py", "run_spatial_energy_until.py", "run_spatial_sequence_probe.py",
    "run_spatial_sequence_until.py", "run_vm_lifecycle.sh", "trace_spatial_sequence_joins.py",
    "verify_local_dynamics_probe.py", "verify_sequence_archive.py",
}
SHARED_NAMES = {
    "PROJECT_CONSTITUTION.md", "EVOLVABLE_LANGUAGE_PLAN.md", "EVOLUTION_V2_PLAN.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path) -> str:
    rel = path.relative_to(ROOT); parts = rel.parts; name = path.name
    if any(part in {"__pycache__", ".pytest_cache"} for part in parts) or path.suffix == ".pyc":
        return "generated_cache"
    if parts[0] in {".kiro", ".claude", "LLM_HANDOFF"}: return "excluded_private_or_catalog"
    if parts[:2] == ("engine", "deterministic"):
        if name in CURRENT_A_MODULES: return "deterministic_a"
        if name in CURRENT_B_MODULES: return "model_neutral_b"
        return "shared_current"
    if parts[0] == "worlds" and name.startswith("deterministic_"): return "deterministic_a"
    if parts[0] == "schemas": return "model_neutral_b"
    if parts[0] == "tests" and name.startswith("test_deterministic_"):
        b_tokens = ("b_language", "change_graph", "cognitive_map", "counterfactual", "experiment_proposal",
                    "hypotheses", "impact_scope", "provenance", "theory_revision", "world_model", "adapter_comparison")
        return "model_neutral_b" if any(token in name for token in b_tokens) else "deterministic_a"
    if len(parts) == 1 and (name.startswith(("run_deterministic_", "run_gpu_", "run_physical_"))):
        return "deterministic_a"
    if len(parts) == 1 and name.startswith(("run_b_", "run_cognitive_", "run_change_", "run_adapter_",
                                            "run_private_", "run_impact_", "run_hypothesis_",
                                            "run_counterfactual_", "run_theory_", "run_experiment_proposal")):
        return "model_neutral_b"
    if parts[0] == "runs" and len(parts) > 1 and parts[1] in CURRENT_RUN_DIRS:
        return "current_evidence"
    if parts[:2] == ("engine", "sequence") or rel.as_posix() == "engine/living/events.py":
        return "legacy_probability_world"
    if parts[0] == "tests" and (name.startswith("test_sequence_") or name in {
        "test_dual_gcp_experiment.py", "test_prepare_experiment_manifest.py"}):
        return "legacy_probability_world"
    if len(parts) == 1 and name in PROB_SCRIPT_NAMES: return "legacy_probability_world"
    if parts[0] == "runs" and len(parts) > 1 and parts[1].startswith(PROB_RUN_PREFIXES):
        return "legacy_probability_world"
    if parts[0] == "docs" and (name.startswith(("SEQUENCE_", "STAGE_C_", "SPATIAL_SEQUENCE_")) or name in {
        "DUAL_GCP_EVALUATION_PROTOCOL.md", "EVENT_RATE_AND_TIME_AUDIT_V1.md", "SCHEDULER_V1_AUDIT.md",
        "SELF_INTERPRETING_SEQUENCE_SUBSTRATE_V0.md", "FORCING_ASSUMPTION_AUDIT.md",
        "ADR-001-shared-life-substrate.md", "INTEGRATED_GENETIC_WORLD_V0_REVIEW.md",
        "COMPONENT_MOTION_V1.md", "CONTEXTUAL_INHERITANCE_V1.md", "LOCAL_DYNAMICS_V1.md",
        "PHYSICAL_RECOMBINATION_V1.md", "SPATIAL_BOUNDARY_V1.md", "EMERGENT_AFFECT_SUBSTRATE.md",
        "EMERGENT_REPRODUCTIVE_MODES.md", "EVOLVABLE_COMPUTATION_SUBSTRATE.md",
        "WORLD_GENERATIVE_LANGUAGE_CONSTRAINTS.md", "STAGE_B_CONCEPT_REVIEW.md"}):
        return "legacy_probability_world"
    if parts[0] == "docs" and name in {
        "DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md", "DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md",
        "EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md"}:
        return "shared_current"
    if parts[0] == "docs" and name in {"MIDPOINT_A_B_AUDIT_2026-09-21.md", "PROJECT_CLEANUP_AUDIT_V1.md"}:
        return "shared_governance"
    if name in SHARED_NAMES or name in {"build_llm_handoff_catalog.py", "verify_llm_handoff_catalog.py"}:
        return "shared_governance"
    if len(parts) == 1 and (name.startswith(("run_agent_world", "run_primal", "run_llm_comparison",
                                               "run_batch", "run_v0_1", "export_csv", "export_dashboard"))
                            or path.suffix in {".log", ".csv", ".html"}
                            or name in {"agent_world_design_v1.md", "dashboard_data.json", "validation_results.json"}):
        return "legacy_society_primal_brain"
    if parts[0] in {"engine", "tests", "tools", "data", "runs"}:
        return "legacy_society_primal_brain"
    return "unclassified"


README = """# LLM Handoff Index

이 폴더는 원본 파일을 옮기거나 복사하지 않는 논리 카탈로그다. 각 하위 폴더의 `manifest.json`은 프로젝트 루트 기준 상대경로·크기·SHA-256을 제공한다.

## 먼저 읽을 것

1. `00_CURRENT_STATUS/README.md`
2. 확인하려는 계통의 `README.md`
3. 필요한 경우 같은 폴더의 `manifest.json`

## 계통

- `01_DETERMINISTIC_A`: 현재 결정론 물리·환경·CPU/GPU
- `02_MODEL_NEUTRAL_B`: B-Language·adapter·가설·계보·실험 제안
- `03_LEGACY_PROBABILISTIC_WORLD`: 보존된 scheduler-v1·sequence·GCP·계보 실험
- `04_LEGACY_SOCIETY_PRIMAL_BRAIN`: 현재 프로젝트 이전의 사회·원시인·뇌 계통
- `05_PRIVATE_TRACE`: 사용자 전용 D: trace 설명; raw 데이터는 이 카탈로그에 복사하지 않음
- `06_UNCLASSIFIED`: 자동 분류되지 않은 검토 대상
- `07_SHARED_CURRENT_DESIGN`: A·B 공용 현재 설계와 구현 순서
- `08_CURRENT_EVIDENCE`: 현재 결정론·GPU·B 기준 결과
- `09_SHARED_GOVERNANCE`: 헌법·중간 점검·정리 감사

## 주의

- 확률 세계와 결정론 세계의 결과를 합산하지 않는다.
- manifest는 파일 수집 지도로, 원본의 source of truth 위치는 바뀌지 않았다.
- 실제 이동·삭제는 별도 archive·SHA-256·시험 복원·사용자 승인 뒤에만 한다.
"""

LANE_NOTES = {
    "deterministic_a": """
## 권장 읽기 순서

1. `docs/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md`
2. `engine/deterministic/spec.py`, `causal_spec.py`, `environment_spec.py`
3. `engine/deterministic/kernel.py`, `causal_kernel.py`, `environment_kernel.py`
4. `engine/deterministic/physical_scale.py`, `gpu_environment.py`
5. `worlds/deterministic_physical_flux_v4.json`
6. `tests/test_deterministic_*.py`

## 확인된 범위

A0 이동·충돌, A1 에너지·결합, A2.3 환경 field, 물리 flux, CPU/GPU field 동등성까지다. 고분자·촉매·실제 경계·복사는 아직 없다.
""",
    "model_neutral_b": """
## 권장 읽기 순서

1. `docs/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md`
2. `schemas/b_language_boundary_v1.schema.json`
3. `engine/deterministic/b_language.py`, `brain_adapter.py`
4. `cognitive_map.py`, `change_graph.py`, `provenance.py`
5. `hypotheses.py`, `counterfactual.py`, `theory_revision.py`, `experiment_proposal.py`
6. 대응하는 `tests/test_deterministic_*.py`

## 해석 주의

현재 B 후보는 수작업 결정론 adapter다. 독립 학습형 JEPA·신경망이나 진짜 미지 변수 발견은 아직 없다. held-out 제안서는 미실행 상태다.
""",
    "legacy_probability_world": """
## 이 계통의 의미

현재 수정 대상이 아니라 보존된 비교 기준 `scheduler-v1`이다. 결정론 결과와 직접 합산하지 않는다.

## 가장 먼저 읽을 것

1. `docs/EVENT_RATE_AND_TIME_AUDIT_V1.md`
2. `docs/SCHEDULER_V1_AUDIT.md`
3. `docs/DUAL_GCP_EVALUATION_PROTOCOL.md`
4. `engine/sequence/nonliving_world.py`, `observation.py`, `lineage.py`
5. `engine/living/events.py`
6. `runs/dual_gcp_precommit_20260919_185150/`

## 확정된 판정

- GCP1: 64세계×6시간, 분할 4·융합 4
- GCP2: 12세계×32시간, 분할·융합 0
- 통합 768 세계·시간, 독립 후손 0
- 관찰된 분할은 같은 cyclic strand가 만든 일시적 위상 분할
- 독립 경계 scission+closure 경로 없음
- 전역 후보 경쟁·단위 불일치·벽시계 노출량 차이가 확인됨
- 추가 장기 확률 VM 실험은 중단
""",
    "legacy_society_primal_brain": """
## 의미

사회·원시인·기존 brain 진화 프로젝트다. 현재 결정론 A와 모델 중립 B의 직접 실행 의존성은 없지만 연구 이력으로 보존한다. 실제 분리는 archive·복원 검증 뒤에만 한다.
""",
    "shared_current": """
## 핵심

A·B 전체 설계와 현재 구현 순서를 함께 읽는 계통이다. `docs/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md`가 현재 완료·다음 단계의 기준이다.
""",
    "current_evidence": """
## 주의

이 폴더의 manifest는 프로젝트 내부의 작은 결정론 결과를 가리킨다. 사용자 전용 full trace 원본은 D: vault에 있으며 외부 LLM에 자동 제공하지 않는다.
""",
    "shared_governance": """
## 먼저 읽을 것

- `PROJECT_CONSTITUTION.md`
- `docs/MIDPOINT_A_B_AUDIT_2026-09-21.md`
- `docs/PROJECT_CLEANUP_AUDIT_V1.md`

삭제·물리 이동·승격 권한과 증거 해석 원칙을 담는다.
""",
    "unclassified": """
## 처리

이 파일들은 자동으로 현재/확률/이전 프로젝트 중 하나로 확정하기 어려웠다. 다른 계통에 넣기 전에 사람이 확인한다.
""",
}

PROMPTS = """# 다른 LLM에게 전달할 요청 예시

## Legacy 확률 세계 감사

```text
이 프로젝트의 legacy 확률 세계를 검토해줘. 먼저 LLM_HANDOFF/03_LEGACY_PROBABILISTIC_WORLD/README.md를 읽고, docs/EVENT_RATE_AND_TIME_AUDIT_V1.md와 docs/SCHEDULER_V1_AUDIT.md를 확인해. 필요할 때만 같은 폴더 manifest.json에서 원본 경로와 SHA-256을 찾아 읽어. 확률 결과를 결정론 결과와 합산하지 말고, 관찰된 분할을 독립 세포 분열이라고 부르지 마.
```

## 현재 결정론 A 검토

```text
현재 결정론 A 구현을 검토해줘. LLM_HANDOFF/01_DETERMINISTIC_A/README.md에서 읽기 순서를 확인하고 manifest.json으로 파일 경로와 SHA-256을 검증해. 난수 부재, 물질·에너지·운동량, 국소성, CPU/GPU 동등성, 아직 구현되지 않은 고분자·경계를 구분해 보고해.
```

## 모델 중립 B 검토

```text
모델 중립 B를 검토해줘. LLM_HANDOFF/02_MODEL_NEUTRAL_B/README.md와 docs/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md를 먼저 읽어. exact oracle, Cognitive Map, ChangeGraph, HypothesisSet, CounterfactualBranch, TheoryRevisionProposal의 실제 구현과 한계를 구분하고, 이것을 학습형 독립 모델이라고 과장하지 마. 사용자 전용 D: raw trace는 요청하지 마.
```

## 중간 상태 반대 검토

```text
프로젝트 중간 상태를 비판적으로 검토해줘. LLM_HANDOFF/00_CURRENT_STATUS/README.md와 docs/MIDPOINT_A_B_AUDIT_2026-09-21.md를 읽어. 특히 held-out 실행 전 후보별 예측 미봉인, 독립 trace parser 부재, held-out 다양성 부족, private stage API 결합을 확인해. 수정 제안은 A 실행 중 개입이나 기존 결과 삭제 없이 제시해.
```

## 폴더 실제 이동 검토

```text
LLM_HANDOFF/PHYSICAL_MOVE_PLAN.md와 각 lane manifest를 읽고 실제로 옮겨도 import·테스트·증거 경로가 깨지지 않을 파일만 제안해줘. 삭제는 제안만 하고 실행하지 마. archive·파일별 SHA-256·시험 복원·결정론/sequence 테스트·사용자 승인 순서를 지켜.
```
"""

DESCRIPTIONS = {
    "deterministic_a": ("01_DETERMINISTIC_A", "현재 결정론 A", "물리 명세·CPU/GPU 커널·환경·world spec·검증 테스트"),
    "model_neutral_b": ("02_MODEL_NEUTRAL_B", "모델 중립 B", "B-Language·adapter·world model·trace·가설·반사실·실험 제안"),
    "legacy_probability_world": ("03_LEGACY_PROBABILISTIC_WORLD", "Legacy 확률 세계", "scheduler-v1 sequence 계통과 GCP·계보·실패 실험 증거"),
    "legacy_society_primal_brain": ("04_LEGACY_SOCIETY_PRIMAL_BRAIN", "Legacy 사회·원시인·뇌", "현재 A/B 이전 연구 계통; 삭제가 아니라 별도 archive 후보"),
    "shared_current": ("07_SHARED_CURRENT_DESIGN", "현재 공용 설계 문서", "A와 B 양쪽에 걸친 현재 설계·구현 순서"),
    "current_evidence": ("08_CURRENT_EVIDENCE", "현재 결정론 증거", "CPU/GPU·스케일·B adapter의 현재 프로젝트 내부 결과"),
    "shared_governance": ("09_SHARED_GOVERNANCE", "공통 헌법·정리 감사", "프로젝트 헌법·중간 점검·정리 원칙"),
    "unclassified": ("06_UNCLASSIFIED", "미분류", "자동 분류가 확실하지 않아 사람이 확인할 파일"),
}


def main() -> None:
    files = [path for path in ROOT.rglob("*") if path.is_file() and "LLM_HANDOFF" not in path.parts]
    grouped: dict[str, list[dict[str, object]]] = {}
    for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix().lower()):
        lane = classify(path)
        if lane in {"generated_cache", "excluded_private_or_catalog"}: continue
        grouped.setdefault(lane, []).append({"bytes": path.stat().st_size,
                                              "path": path.relative_to(ROOT).as_posix(),
                                              "sha256": sha256(path)})
    OUT.mkdir(exist_ok=True)
    (OUT / "README.md").write_text(README, encoding="utf-8")
    status = OUT / "00_CURRENT_STATUS"; status.mkdir(exist_ok=True)
    (status / "README.md").write_text(
        "# 현재 상태\n\n- 중간 점검: `../../docs/MIDPOINT_A_B_AUDIT_2026-09-21.md`\n"
        "- 구현 순서: `../../docs/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md`\n"
        "- B 아키텍처: `../../docs/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md`\n"
        "- 최신 전체 테스트: 837 passed\n- held-out A 실행: 사용자 승인 대기, 현재 0개\n",
        encoding="utf-8")
    summary = {}
    for lane, (folder_name, title, description) in DESCRIPTIONS.items():
        folder = OUT / folder_name; folder.mkdir(exist_ok=True)
        entries = grouped.get(lane, [])
        payload = {"bytes": sum(int(x["bytes"]) for x in entries), "file_count": len(entries),
                   "format": "llm-handoff-manifest-v1", "lane": lane,
                   "project_root": str(ROOT), "files": entries}
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_sha = sha256(manifest)
        (folder / "README.md").write_text(
            f"# {title}\n\n{description}\n\n"
            f"- 파일 수: {payload['file_count']}\n- 총 bytes: {payload['bytes']}\n"
            f"- manifest SHA-256: `{manifest_sha}`\n\n"
            "다른 LLM에는 먼저 이 README와 필요한 원본 경로만 전달한다.\n"
            + LANE_NOTES.get(lane, ""),
            encoding="utf-8")
        summary[lane] = {"bytes": payload["bytes"], "file_count": payload["file_count"],
                         "folder": folder_name, "manifest_sha256": manifest_sha}
    private = OUT / "05_PRIVATE_TRACE"; private.mkdir(exist_ok=True)
    (private / "README.md").write_text(
        "# 사용자 전용 A/B Trace\n\n"
        "- Vault: `D:\\KiroCrewTraceVault\\success-is-mother-of-failure`\n"
        "- 접근: 현재 Windows 사용자 SID와 승인된 고정 검증기\n"
        "- B·외부 LLM에 raw trace 자동 공개 금지\n"
        "- 현재 private provenance trace 12개 모두 무결성 검증 통과\n"
        "- 이 handoff 폴더에는 raw trace를 복사하거나 파일 목록을 노출하지 않는다.\n",
        encoding="utf-8")
    excluded = {"generated_cache": sum(1 for path in files if classify(path) == "generated_cache"),
                "private_settings": sum(1 for path in files if classify(path) == "excluded_private_or_catalog")}
    catalog = {"excluded": excluded, "format": "llm-handoff-catalog-v1", "lanes": summary,
               "physical_moves_performed": 0, "project_root": str(ROOT)}
    catalog_path = OUT / "catalog_summary.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "PHYSICAL_MOVE_PLAN.md").write_text(
        "# 실제 이동 계획 — 미실행\n\n"
        "현재 단계에서는 import와 증거 경로를 보호하기 위해 원본 이동·삭제를 수행하지 않았다.\n\n"
        "다음 단계 후보:\n\n"
        "1. 현재 코드·문서 snapshot을 D:에 archive\n"
        "2. legacy society/primal/brain archive 생성\n"
        "3. 파일별 SHA-256 및 시험 복원\n"
        "4. 결정론·sequence 테스트 재실행\n"
        "5. 사용자에게 실제 이동·삭제 목록 제시\n"
        "6. 명시적 승인 후에만 원본 변경\n",
        encoding="utf-8")
    print(json.dumps({"catalog_sha256": sha256(catalog_path), "lanes": summary,
                      "physical_moves_performed": 0}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
