# 저장소 지도

작업 대상을 빠르게 찾기 위한 지도다. 저장소 전체를 검색하지 말고 여기서 범위를 정한 뒤 해당 디렉터리만 읽는다.

**규모:** 32,795 파일 / 4.3GB — 이 중 4.2GB가 `runs/`(실험 결과)다. 코드+문서는 67MB.

---

## 계통 4개

이 저장소에는 **서로 다른 시기의 4개 계통**이 공존한다. 섞어서 읽으면 혼란스럽다.

| 계통 | 위치 | 상태 | 수정 |
|---|---|---|---|
| **결정론 A** | `engine/deterministic/` (물리 부분) | 현재 주 개발 | 가능 |
| **모델 중립 B** | `engine/deterministic/` (관찰 부분) | 현재 주 개발 | 가능 |
| **독립 감사** | `audit/` | 현재 주 개발 | 가능 (**engine import 금지**) |
| **확률 세계** | `engine/sequence/`, `engine/living/` | 동결된 기준선 | **읽기만** |
| **레거시 사회/원시인/뇌** | `engine/primal|brain|agentworld/` + 루트 `engine/*.py` | 이전 프로젝트 | 현재 대상 아님 |

A와 B가 같은 디렉터리에 있는 이유: 둘 다 결정론 계통에 속하고 `engine/deterministic/__init__.py`가 공통 진입점이기 때문이다. 파일 단위로는 명확히 나뉜다(아래).

---

## 결정론 A — 세계

**데이터 흐름:**

```
worlds/*.json  (세계 명세)
   ↓  load_*_spec()
*_spec.py      (명세 → 검증된 Spec 객체)
   ↓  initial_*_state()
*_kernel.py    (Spec + State → 다음 State, 매 tick)
   ↓  run_*_world()
Run 객체 (TickRecord 목록 + 최종 digest)
```

| 파일 | 역할 |
|---|---|
| `spec.py` / `kernel.py` | A0 — 입자 이동·충돌. 가장 단순한 기준 세계 |
| `causal_spec.py` / `causal_kernel.py` | A1 — 에너지·결합·분리 |
| `environment_spec.py` / `environment_kernel.py` | A2 — 열·물·용질·수증기 field, 광물 용해/침전, 상변화 |
| `physical_scale.py` | 물리 단위·flux 계약 |
| `physical_environment_scaling.py` | 해상도 수렴 감사 |
| `scaling.py` | 격자 크기 독립성 감사 |
| `gpu_environment.py` | CUDA int64 field transport. **CPU와 매 tick 동일해야 함** |

**커널 내부 단계** (`environment_kernel.py`의 `step_environment_world`):

```
_phase()                    지역 열·물·용질 이동 (짝수/홀수 위상)
_convert_local_mineral()    광물 용해·침전
_exchange_external_energy() 외부 에너지 출입 + 장부 기록
_change_water_phase()       증발·응축
```

> **기술 부채:** 위 `_` 함수들은 private인데 full trace와 GPU가 직접 호출한다. 이름을 바꾸면 추적기와 GPU가 함께 깨진다. 공개 stage API가 필요하다.

**세계 명세** (`worlds/`):

```
deterministic_collision_smoke_v1.json    A0 최소 예제
deterministic_bond_cycle_v1.json         A1 결합 순환
deterministic_environment_v1.json        A2 환경
deterministic_geochemical_cycle_v2.json  광물 순환
deterministic_open_water_cycle_v3.json   개방 물 순환
deterministic_physical_flux_v4.json      물리 flux (최신)
```

---

## 모델 중립 B — 관찰자

**데이터 흐름:**

```
A의 상태/변화
   ↓  (TraceViewBroker 경유 — B는 A를 직접 못 봄)
B 어댑터 (CognitiveMap 또는 ChangeGraph)
   ↓  내부 표현 구성
ClaimSet (외부 주장)
   ↓  evaluate_*()
BoundaryEvaluation (A 실제값과 대조)
```

| 파일 | 역할 |
|---|---|
| `b_language.py` | **외부 경계 규격.** `Claim`, `ClaimSet`, `EvidenceBridge`, `BoundaryEvaluation`, `CapabilityManifest`, `ObservationContract` |
| `brain_adapter.py` | `BrainAdapter` 기반 클래스 + `ExactOracleAdapter`(정답을 아는 기준) |
| `cognitive_map.py` | 현재 상태 압축 표현 (관련 칸만) |
| `change_graph.py` | 변화 이력 기반 표현 (언제 무엇이 바뀌었는지 보존) |
| `trace_view_broker.py` | B가 trace를 직접 안 보고 중개받는 창구 |
| `adapter_comparison.py` | 두 어댑터에 동일 질의 → 병렬 비교 |
| `impact_scope.py` | 다음 tick 영향 범위 예측 + 누락·과잉 검사 |
| `hypotheses.py` | `HypothesisSet` — 여러 설명 동시 보존. 근거 없는 확률 금지 |
| `counterfactual.py` | 다중 정밀도 분기 (low→medium→exact) + 무행동 대조군 |
| `theory_revision.py` | `ResidualPattern` → `TheoryRevisionProposal` |
| `experiment_proposal.py` | 사용자 승인형 실험 제안. 자동 실행 차단 |
| `world_model.py` / `environment_world_model.py` | B 월드 모델 v0 |
| `provenance.py` | 사용자 전용 full trace 기록 + hash chain |

**스키마:** `schemas/b_language_boundary_v1.schema.json`

**정밀도 계층** (`counterfactual.py`):

```
low     ChangeGraph 영향 범위만        전 분기
medium  Cognitive Map 구성             전 분기
exact   실제 A 실행                    예산 제한 (보류분은 deferred_budget으로 보존)
```

---

## 독립 감사 — `audit/`

**`engine`을 import하지 않는다.** 기록장이 정확한지를 두 번째 경로로 확인한다.
기존 `verify_trace()`는 기록할 때 쓴 함수(`_delta`, `_digest`)를 검증할 때 다시 쓰므로,
그 함수에 결함이 있으면 스스로 잡지 못한다.

| 파일 | 역할 |
|---|---|
| `independent_trace/canonical.py` | 정규화·해시. `json.dumps`에 의존하지 않고 규칙을 직접 명시 |
| `independent_trace/delta.py` | 델타를 **적용**해서 검증 (재생성 비교 아님) |
| `independent_trace/verifier.py` | 체인·스냅샷·델타 전체 검사. 발견을 모두 수집 |
| `independent_trace/external_hash.py` | 외부 `sha256sum` 병행 |
| `independent_trace/README.md` | 왜 필요한지, 결함 주입 실험 결과 |

실행: `python run_independent_trace_audit.py --vault --compare-engine`

독립성은 `tests/test_audit_independent_trace.py`가 AST 검사로 강제한다.

---

## 실행 스크립트 (루트)

명명 규칙: `run_*.py`

**결정론 A:**
```
run_deterministic_world.py                A0
run_deterministic_causal_world.py         A1
run_deterministic_environment.py          A2
run_deterministic_scaling_audit.py        크기 독립성
run_physical_scale_audit.py               물리 단위
run_physical_environment_scaling_audit.py 해상도 수렴
run_gpu_environment_parity.py             CPU/GPU 동등성
run_gpu_resident_benchmark.py             GPU 성능
```

**B:**
```
run_b_world_model.py                 월드 모델
run_b_environment_world_model.py     환경 월드 모델
run_b_language_exact_adapter.py      exact oracle
run_cognitive_map_benchmark.py       Cognitive Map
run_change_graph_benchmark.py        ChangeGraph
run_adapter_comparison.py            두 어댑터 비교
run_impact_scope_benchmark.py        영향 범위
run_hypothesis_set_benchmark.py      HypothesisSet
run_counterfactual_benchmark.py      반사실
run_theory_revision_campaign.py      이론 수정 (4세계)
run_experiment_proposal.py           실험 제안서
run_private_ab_trace.py              사용자 전용 trace
```

**확률 세계 (동결):**
```
run_sequence_probe.py              sequence 기본
run_spatial_sequence_probe.py      공간 sequence
run_spatial_sequence_until.py      조건 도달까지
run_spatial_boundary_probe.py      경계
run_spatial_energy_until.py        에너지
run_nonliving_world_probe.py       비생명 세계
run_nonliving_face_until.py        face 경계
run_compartment_lineage_probe.py   구획 계보
run_component_motion_probe.py      성분 운동
run_inherited_context_probe.py     맥락 유전
run_integrated_world_probe.py      통합 세계
run_local_dynamics_probe.py        지역 동역학
run_observer_cohort.py             관찰자 코호트 (GCP 실험)
```

**레거시:** `run_agent_world.py`, `run_agent_world2.py`, `run_primal.py`, `run_llm_comparison.py`, `run_batch.py`, `run_v0_1.py`

**분석·검증·준비 스크립트** (루트, `run_` 아님):
```
verify_sequence_archive.py          sequence 아카이브 검증
verify_local_dynamics_probe.py      지역 동역학 검증
verify_llm_handoff_catalog.py       핸드오프 카탈로그 검증
analyze_sequence_archive.py         sequence 분석
audit_join_bottlenecks.py           결합 병목 감사
compare_sequence_probe_records.py   probe 기록 비교
trace_spatial_sequence_joins.py     공간 결합 추적
build_llm_handoff_catalog.py        핸드오프 카탈로그 생성
prepare_dual_gcp_manifest.py        GCP manifest 준비
prepare_experiment_manifest.py      실험 manifest 준비
export_csv.py / export_dashboard_data.py   레거시 출력
```

---

## 테스트

`tests/` — 총 837개 통과.

```
test_deterministic_*.py   결정론 A/B (26개 파일, 약 1,858줄)
test_sequence_*.py        확률 세계 (동결)
test_living_*.py          living 계통
test_primal_*.py          레거시 원시인
test_brain_*.py           레거시 뇌
test_agent*.py            레거시 사회
```

---

## 데이터

| 위치 | 내용 | 크기 |
|---|---|---|
| `runs/` | 실험 결과 233개 디렉터리. **Git 밖.** 통째로 읽지 말 것 | 4.2GB |
| `runs/dual_gcp_precommit_20260919_185150/` | 확률 세계 최대 실험 (원본 압축본 + 해제본) | 2.9GB |
| `data/terrain/` | 레거시 지형 데이터 | 51MB |
| `D:\KiroCrewTraceVault\success-is-mother-of-failure\` | **사용자 전용** A/B trace + 벤치마크 8종 | 524KB |
| `D:\...\project-snapshots\` | Git 이전 코드 스냅샷 | 52MB |

> D: vault의 raw trace는 사용자 전용이다. B나 외부 LLM에 공개하지 않는다.

---

## 문서

**작업 전 필수 4개:** `AGENTS.md`, `RULES.md`, `CURRENT_STATE.md`, `REPO_MAP.md`(이 문서)

**참조용:**

| 문서 | 내용 |
|---|---|
| `PROJECT_CONSTITUTION.md` | 헌법 24조 |
| `docs/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md` | B 전체 아키텍처 (58KB) |
| `docs/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md` | 구현 순서·완료 판정 (32KB) |
| `docs/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md` | A 물리 심화 설계 |
| `docs/MIDPOINT_A_B_AUDIT_2026-09-21.md` | 최근 중간 점검 |
| `docs/SCHEDULER_V1_AUDIT.md` | 확률 세계 실패 원인 분석 |
| `docs/EVENT_RATE_AND_TIME_AUDIT_V1.md` | 사건율·시간 감사 |
| `docs/DUAL_GCP_EVALUATION_PROTOCOL.md` | GCP 실험 프로토콜 |
| `docs/PROJECT_CLEANUP_AUDIT_V1.md` | 정리 원칙 |
| `docs/STAGE_C_*_REVIEW.md` | 확률 세계 단계별 검토 (약 20개) |
| `LLM_HANDOFF/` | 계통별 파일 카탈로그 (외부 LLM 전달용, 논리 카탈로그이며 원본 이동 없음) |

---

## 레거시 (현재 작업 대상 아님)

건드리지 않지만 존재는 알아둔다. 기존 테스트가 이 파일들을 사용하므로 지우면 회귀 기준도 사라진다.

```
engine/agentworld/   사회 시뮬레이션 (회사·계약·경제)
engine/primal/       원시인 세계 (지형·동식물·계절)
engine/brain/        뇌 진화 (유전·학습·기질)
engine/living/       생명 기반. events.py는 engine.sequence가 의존 → 삭제 금지
engine/*.py (루트)   사회 시뮬레이션 지원 모듈
tools/               레거시 분석·벤치마크 도구
루트 *.log, *.csv, dashboard*.html   레거시 출력
```
