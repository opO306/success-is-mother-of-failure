# 저장소 지도

작업 대상을 빠르게 찾기 위한 지도다. 저장소 전체를 검색하지 말고 여기서 범위를 정한 뒤 해당 디렉터리만 읽는다.

**규모(과거 집계):** 32,795 파일 / 4.3GB — 이 중 4.2GB가 `runs/`(실험 결과)다. 코드+문서는 67MB. 현재 규모를 재집계한 값은 아니다.

---

## 프로젝트 구조 — A / B / L

```
A = 세계 (물리)        L = A 안의 생명 계통         B = 세계 밖 연구자
ACTIVE                A 기반이 충분한 뒤 진행     후기 단계로 보류, 취소 아님
```

현재 우선순위·Gate는 [CURRENT_STATE.md](CURRENT_STATE.md)가 정본이다. A 최우선 → A 기반이 충분한 뒤 L의 자연 발생·진화 → 작더라도 세계가 돌아가는 단계 뒤 B 본격 개발.
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 현재 활성 Gate는 C1-B1의 outer formal bound ④이며 ④ 전체는 FROZEN이 아니고 ⑤는 미착수다.

과거 번호는 `A-V4.x`, `A-V4.GEO`, `B-Gx`, `L-Px`로 읽는다. 번호 체계·옛 진행 방침은 [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)의 해당 절을 본다.

## 계통

이 저장소에는 **서로 다른 시기의 계통**이 공존한다. 섞어서 읽으면 혼란스럽다.

| 계통 | 위치 | 상태 | 수정 |
|---|---|---|---|
| **결정론 A** | `engine/deterministic/` (물리 부분) | 현재 주 개발 | 가능 |
| **B-classic 연구선** | `engine/deterministic/` (blind_*, probe_*, research_* 등) | 후기 비교군/연구 자산 보존 | 이번 정리에서 구현·시험 변경 없음. 동결 파일 7개의 새 버전 규약 유지 (`tests/test_probe_v3_freeze.py`) |
| **초기 B 관찰 도구** | `engine/deterministic/` (b_language, cognitive_map 등) | B0 시기 도구 보존. 본격 B 개발은 후기 단계 | 이번 정리에서 변경 없음 |
| **연구 데이터 저장소** | `research_store/` (코드) + D: (데이터) | 보존된 연구 기반 | 이번 정리에서 변경 없음 |
| **정답표** | `ground_truth/` | 봉인된 기준표 | **B 쪽 import 금지** |
| **독립 감사** | `audit/` | 현재 주 개발 | 가능 (**engine import 금지**) |
| **A-Numeric VM** | `a_numeric/` | A 계산 의미의 기준(VM 0.2: FX·A-Binary64-Finite·EXACT, 정수만 사용, SUM·DOT은 정확 누적 후 1회 반올림, EXP는 정확한 e^x를 1회 반올림) — [docs/reference/A_NUMERIC_EXECUTION_STACK_V1.md](docs/reference/A_NUMERIC_EXECUTION_STACK_V1.md) | 가능. 세계 실행기 아님, 실행기들이 이것에 맞춰 판정받음 |
| **물리 기준 평가기** | `a_reference/` | 물리 함수의 A 값 = 정확한 모델 값을 한 번 반올림(느림, 정답 정의). 현재 `ar2_lang2024.py`(C1-A Ar–Ar, 계약 `c1a-ar2-lang2024-v1`) + **Git fixture** `fixtures/ar2_lang2024_c1a_v1.json`(332 입력 × 7 양, 감사 판정·출처 기록, 생성기 `ar2_lang2024_fixture.py`) — **동결**([docs/frozen/C1A_AR2_FREEZE_V1.md](docs/frozen/C1A_AR2_FREEZE_V1.md), `tests/test_c1a_freeze.py`) — [docs/history/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md](docs/history/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md) 10·11절 | 가능. 세계 실행기 아님 |
| **C1-B1 두 원자 동역학 기준** | `a_reference/c1b1_two_atom.py`, `c1b1_*study.py`, `c1b1_*compare.py`, `fixtures/c1b1_*.json` | 정확 Δr·R², √R² 구간, 충격량 J 한 번 반올림, KDK, drift = r + round(p·Δt/m), drift 선분 r_min 감시(계약 `c1b1-two-atom-v2`). 현재 후보: 위치 FX(96,48)·운동량 FX(96,80)·Δt = 40·drift v2. 전체 동결은 속박 domain/error proof·native J와 비트 동등성 등을 기다림. 감사 `audit/independent_physics/c1b1_two_atom.py` — 설계 문서 23절(D_valid 동결)·24절(④-1)·25절(④-2/④-3)·26절(rounding 진행)을 함께 참조 | 가능. 세계 실행기 아님 |
| **C1-B1 D_valid v2** | `a_reference/c1b1_canonical_state.py`, `c1b1_domain_contract.py`, `c1b1_orbit_boundary.py`, `fixtures/c1b1_orbit_boundary_v3.json` | 단일 canonical 생성기·기준 fixture·계약 `c1b1-dvalid-v2` 동결. 7 에너지 × 2쪽 재측정, 181개 측정 상태 = 식별 상태. `run.validation`은 초기 상태만 분류(`numerical_validated` / `unsupported`), 궤적 인증 아님. 에너지 보간·바깥 탐침 외삽 없음, 실행 비간섭. analytic outer certificate와 자동 승격·연결 없음 | 새 결함 또는 다음 물리 단계의 필요가 생길 때만 재측정 |
| **물리 함수 네이티브 실행기** | `a_physics_native/` | C1-A V(R)·F(R)의 B0 직렬 C++·B1 병렬 C++·B2 CUDA. 기준·fixture와 같은 비트, 못 맞추면 거부. 조사 문서 11절. `bench_state.*` = C1-B1 상태 폭별 비용 측정 전용(세계 실행기 아님) | 가능. MSVC·nvcc·GPU 필요(없으면 시험 건너뜀) |
| **C1-B1 outer formal bound v1** | `a_reference/c1b1_outer_bound.py`, [docs/active/C1B1_OUTER_FORMAL_BOUND_V1.md](docs/active/C1B1_OUTER_FORMAL_BOUND_V1.md) | 정확 구간 Taylor 도함수 0~3차, 위치·초기 운동량·impulse·이산화 원인별 상한. 유한 shell/half-step momentum cap 아래 1-step·유한합. 후속 전제 인증은 아래 별도 계층, D_valid와 별도 | 가능. 실측으로 bound 조정 금지 |
| **C1-B1 outgoing bootstrap / tail v1** | `a_reference/c1b1_outer_bootstrap.py`, `c1b1_outer_chain.py`, `fixtures/c1b1_outer_bootstrap_example_v1.json`, [docs/active/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md](docs/active/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md) | 실제 ΔR²>0 귀납·유한 shell 체류/출구 packet 연결·절대 overflow 인증. model-derived R_J 이후 실행기 impulse 0과 동일 입구 연속 tail의 비영 impulse/점근 momentum 방향 분리. L은 유한 입구→R_J만. rounding-decision completeness에 조건부이며 ④ 전체 FROZEN 아님. inbound/inner/global shadowing/전체 산란각/E_min 미인증 | 가능. A/D_valid에 자동 연결·실측 보정 금지 |
| **C1-B1 rounding decision v1** | `a_reference/c1b1_rounding_completeness.py`, `fixtures/c1b1_rounding_decision_examples_v1.json`, [docs/active/C1B1_ROUNDING_DECISION_V1.md](docs/active/C1B1_ROUNDING_DECISION_V1.md) | legal FX tail 전체: 210 cell·최대 512 bit. 유한 부분: 기존 shell-induced reachable enclosure의 FX adaptive signed rounding cover. 미해결은 NotCertified(report). R=20의 64-cell 시도는 미인증; 단일 궤적으로 대체하지 않음 | 가능. precision cap 상향·미검사 future 인정·D_valid 확대 금지 |
| **C1-B1 reachable geometry v1** | `a_reference/c1b1_reachable_geometry.py`, [docs/active/C1B1_REACHABLE_GEOMETRY_V1.md](docs/active/C1B1_REACHABLE_GEOMETRY_V1.md) | 실제 KDK에서 상대 좌표 0 귀납·좌표 tube·유한 kick/L bound로 direction 제약 유도. 기존 rounding cover의 root와 제외 검사에 적용. 임의 평면 보존·전체 completeness는 주장하지 않음 | 가능. 궤적으로 enclosure 조정·cell budget 확대 금지 |
| **C1-B1 multi-output region v1** | `a_reference/c1b1_rounding_regions.py`, `c1b1_axis_decision_bounds.py`, `fixtures/c1b1_rounding_regions_v1.json`, [계약·결과](docs/active/C1B1_MULTI_OUTPUT_DECISION_V1.md) | 명시 65점 하나의 region·256 bit 인증. 29개 그룹 단조성·수치 오차 상한, 마지막 전체 축 구간 인증. 나머지 27개 그룹 margin 미증명, 전체 NotCertified. 기존 constant-output 보존 | 가능. 64 region·16384 bit 유지, 유한 점 인증을 전체 coverage로 승격 금지 |
| **C1-B1 half-ulp boundary exclusion v1** | `a_reference/c1b1_half_ulp_boundaries.py`, `fixtures/c1b1_half_ulp_boundaries_v1.json`, [계약·결과](docs/active/C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md) | 27개 domain span/경계 수 확정. 3개 큰 domain을 51개 경계·후보 3개로 인증. 나머지 24개 family 미증명. fresh coverage 6/64 region·gap 89, 전체 NotCertified | 가능. 경계 누락·inverse 방향 추정·domain 축소·precision cap 상향 금지 |
| **네이티브 실행기** | `a_numeric_native/` | VM 프로그램의 네이티브 실행기: B0 직렬 C++, B1 병렬 C++(스레드 수 E9), B2 CUDA(블록 크기 E9). VM이 판정자, 네이티브는 VM을 부르지 않음 — [docs/reference/A_NUMERIC_EXECUTION_STACK_V1.md](docs/reference/A_NUMERIC_EXECUTION_STACK_V1.md) 4.1 | 가능. MSVC·nvcc·NVIDIA GPU 필요(없으면 시험 건너뜀) |
| **확률 세계** | `engine/sequence/`, `engine/living/` | 동결된 기준선 | **읽기만** |
| **레거시 사회/원시인/뇌** | `engine/primal|brain|agentworld/` + 루트 `engine/*.py` | 이전 프로젝트 | 현재 대상 아님 |

A와 B가 같은 디렉터리에 있는 이유: 둘 다 결정론 계통에 속하고 `engine/deterministic/__init__.py`가 공통 진입점이기 때문이다. 파일 단위로는 명확히 나뉜다(아래).

---

## 결정론 A — 세계

**C1-B1 미해결 진단:** `a_reference/c1b1_rounding_diagnosis.py`와
`fixtures/c1b1_rounding_diagnosis_v1.json` — 현재 R=20의 76개 기록 전부 분류,
첫 shell projection에 최소 65 uniform leaf 필요. 64-cell/16384-bit 한도 유지,
④-4b NotCertified. 상세: [원인별 진단](docs/active/C1B1_ROUNDING_DIAGNOSIS_V1.md).

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
| `probe_world.py` | 환경 세계 안의 **탐침**(B-G10). 원시 동작 5개. 동결 파일 |
| `contested_census.py` / `precondition_census.py` | "물리가 결과를 못 정하는 순간"·전제조건 계수 |

**causal v5 (A-MICRO, 연속 시간·정확한 분수·정사각형 몸):** `v5_number.py`(정확 분수 창구) → `v5_spec.py`(세계 명세 / 실행 요청) →
`v5_state.py`(상태·불변식) → `v5_reference.py`(**기준 실행기** — 영구 유지, 모든 최적화의 비교 기준) → `v5_meter.py`(분모 측정).
독립 감사 `audit/independent_v5/`. 측정 세계 `v5_benchmark_worlds.py` + `run_v5_benchmarks.py`(A 분모 스트레스 / B 멈춤 조사, 결과는 `runs/v5_benchmarks/`).
설계 문서: `docs/current/A_MICRO_V5_*.md`, [A_EXECUTION_ARCHITECTURE_V1.md](docs/reference/A_EXECUTION_ARCHITECTURE_V1.md).

**causal 형식:** v1/v2/v3 = 동결 레거시(`tests/test_legacy_causal_semantics.py`가 보존 강제), v4 = experimental.
v4만 수정된 충돌 의미(A-V4.A)와 구조가 소유하는 운동 `StructureState`(A-V4.B)를 가진다.
**v4에는 구조가 생기거나 자라는 경로가 없다.** A-V4.GEO는 당시 다음 작업 이름이며 이후 v5에서 생성·성장·병합을 구현했다. 현재 활성 작업은 v6의 C1-B1이다.

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

## 모델 중립 B — 보존된 관찰 도구

아래는 기존 구현 위치와 동작 설명이다. B 본격 개발은 A·L 기반의 작은 세계가 돌아가는 후기 단계로 보류하며 자산과 시험은 보존한다.

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

### B-classic 연구선 (B-G0 ~ B-G11)

B는 정답을 모른 채 연구한다. 실제 이름은 평가자 쪽 번역기만 안다(별칭 `ALIAS-`/`ACT-`/`DIR-`/`CH-`).

```
세계 설명(별칭) ──> B: 가설 → 실험 설계 → 예측 봉인 → 실행 창구(AExecutor) → 관측 → 갱신 → 최종 봉인
                                                     │
                                평가자 쪽 번역기(blind_evaluator / blind_probe_evaluator)만 실제 세계를 앎
```

| 묶음 | 파일 |
|---|---|
| 봉인·실행 규약 | `blind_protocol.py`(감사), `sealed_execution.py`, `execution.py`(창구 모양), `research_journal.py` |
| 합성 세계 연구 (B-G7~G9) | `blind_research_loop.py`, `blind_hypothesis*.py`, `blind_noticing.py`, `blind_tools.py`, `blind_limitations.py`, `experiment_designer.py` |
| 탐침 연구 (B-G10~G11, **동결**) | `blind_probe.py`, `probe_grammar.py`, `probe_induction.py`, `probe_planning.py`, `probe_research.py` |
| 평가자 쪽 (B 금지) | `blind_evaluator.py`, `blind_probe_evaluator.py`, `blind_synthetic_executor.py`, `synthetic_*.py` |
| 공통 타입 | `evidence.py`, `causal_hypothesis.py`, `causal_experiment.py` |

**경계는 테스트가 강제한다:** B 쪽 모듈의 import 사슬 전체가 평가자·정답·세계 커널에 닿지 않는지
(`tests/test_deterministic_blind_hypothesis.py`의 `FORBIDDEN_MODULES`). 남은 것: 세계 기술 형식 `causal_spec`.

### 연구 데이터 저장소 — `research_store/`

데이터는 D:(Git 밖). 계층 b_visible / evaluator / ground_truth. **학습형 B는 `research_store.b_visible`만 import.**
설명: [docs/deferred/RESEARCH_STORE_V1.md](docs/deferred/RESEARCH_STORE_V1.md).

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
| `independent_conservation/ledger.py` | 스냅샷에서 에너지·물질·입자·운동량을 직접 재집계 |
| `independent_conservation/checker.py` | 매 tick 보존 + 커널 집계와 대조 |
| `independent_conservation/README.md` | 사각지대의 모양 (일정한 오류 vs 변하는 오류) |
| `independent_compliance/rules.py` | 명세에서 검사 가능한 규칙 추출 |
| `independent_compliance/field.py` | 스냅샷을 칸별 수치로 평탄화 |
| `independent_compliance/checker.py` | 단계별 규칙 준수 검사 (막힌 벽·짝 균형·한도·온도 조건) |
| `independent_compliance/particles.py` | 입자 물리 준수 (결합 규칙·최소 에너지·포트·한 칸 이동·사슬) |
| `independent_compliance/README.md` | 총량이 맞아도 경로가 틀릴 수 있다 |
| `independent_physics/ar2_lang2024.py` | C1-A Ar–Ar 기준 평가기의 독립 감사: Fortran에서 매개변수 파싱, mpmath 구간 V, 수치 미분 힘, FX 판정, 자체 영역 판정. `a_reference`·`a_numeric` import 금지 |
| `independent_numeric/exp_judge.py`, `exp_cases.py` | R1: EXP를 mpmath **구간** exp로 판정(끝값 정확 변환), 중점 근처·경계 사례 |
| `independent_numeric/` | R1-0: A-Numeric VM을 **어려운 입력**(동점·경계 옆·넘침/비정규 경계)으로 판정. 반올림을 계산하지 않고 "정확값이 결과의 반올림 구간 안에 있나"만 본다. `a_numeric` import 금지 |

**세 검증기가 보는 층이 다르다:**

```
trace       기록이 정확한가
conservation 총량이 보존되는가
compliance   규칙대로 움직였는가   <- 총량이 맞아도 위반 가능
             (환경 field + 입자 물리)
```

실행:
```bash
python run_independent_trace_audit.py --vault --compare-engine
python run_independent_conservation_audit.py --worlds --vault
python run_independent_compliance_audit.py --worlds --vault
```

독립성은 `tests/test_audit_*.py`가 AST 검사로 강제한다 — `audit/` 아래에 `engine` import가 생기면 테스트가 깨진다.

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

`tests/` — 기준선은 `AGENTS.md`가 정본(2026-09-27: 2502 passed + 1 strict xfailed, skip 0). 인수인계 당시 2307 passed는 `0898ca3`의 과거 실측이며 문서 정리의 2404 passed, 진단의 2430 passed, multi-output 단계의 2471 passed와도 구별한다.

```
test_deterministic_*.py   결정론 A/B (32개 파일)
test_audit_*.py           독립 감사 (trace 19 + 보존 17 + 준수 20 + 입자 25)
test_known_defects_*.py   현재 코드가 틀렸음을 기록. 실패하면 좋은 소식 — 파일 머리 참조
test_legacy_causal_*.py   v1/v2/v3가 일부러 보존하는 옛 동작. 실패하면 나쁜 소식(과거가 바뀜)
test_v4_structure_*.py    A-V4.B 구조 상태 + 재명명 불변성
test_blind_*.py / test_deterministic_blind_*.py   B-classic 연구선
test_probe*.py            탐침 세계·탐침 연구
test_probe_v3_freeze.py   동결 지문. 깨지면 지문을 고치지 말고 새 버전을 만든다
test_diagonal_*.py        대각 운동량 도달 불가능성. 다른 설계의 전제조건을 고정
test_sequence_*.py        확률 세계 (동결)
test_living_*.py          living 계통
test_primal_*.py          레거시 원시인
test_brain_*.py           레거시 뇌
test_agent*.py            레거시 사회
```

**`test_known_defects_causal_kernel.py`는 다른 파일과 규칙이 반대다.** 거기 있는
테스트는 코드가 **틀렸음**을 단언한다. 빨간불이 되면 누군가 결함을 고쳤다는
뜻이므로, 옛 동작을 되살려 초록불로 만들면 안 된다. 각 테스트의 `replace_with`가
무엇으로 교체할지 적어두고 있다.

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

**`docs/` 구조** (2026-09-27 상태별 폴더 정리, [전체 안내](docs/README.md)·[파일별 분류표](docs/DOCUMENT_STATUS_INDEX.md)):

```text
docs/
├── README.md                 문서 상태·읽는 순서
├── DOCUMENT_STATUS_INDEX.md  58개 원문의 이전/현재 위치
├── active/                  현재 C1-B1 / outer ④ 진행
├── frozen/                  동결 계약 원문·적용 범위 색인
├── reference/               공통 원칙·실행 구조·검증 기준
├── history/                 과거 설계·철회·실측·점검
├── deferred/                후기 B 연구 자산 (취소·폐기 아님)
│   └── b-design/            옛 docs/README 설명·설계 묶음
├── proposals/               미구현·미동결 장기 제안
├── legacy-probabilistic/    동결된 확률 세계 비교 기준선
├── legacy-society-brain/    이전 사회·원시인·뇌 자료
└── current/                 옛 경로 안내 + 경로 고정 신체 계약 원문
```

`docs/current`는 현재 개발 목록이 아니다. 코드·시험·규칙이 참조하던 경로에는 원문으로 연결하는 짧은 안내를 남겼다.
신체 계약은 시험이 경로와 해시를 고정하므로 기존 위치에 원문을 유지한다. **동결된 계약과 과거 초안은 서로 다르다.**

**참조용:**

| 문서 | 내용 |
|---|---|
| `PROJECT_CONSTITUTION.md` | 헌법 26조 |
| [docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md](docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md) | B 전체 아키텍처 (58KB) |
| [docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md](docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md) | 과거 구현 순서·완료 판정 (32KB), 현재 순서는 CURRENT_STATE |
| [docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md) | 정리 전 CURRENT_STATE 전체 원문, 과거 상태·실험·설계 보존 |
| [docs/history/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md](docs/history/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md) | A 물리 심화 설계 |
| [docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md](docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md) | 당시 중간 점검 (역사) |
| [docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md](docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md) | 검증이 무엇을 못 잡는가, 결함 주입 기록 |
| `docs/legacy-probabilistic/SCHEDULER_V1_AUDIT.md` | 확률 세계 실패 원인 분석 |
| `docs/legacy-probabilistic/EVENT_RATE_AND_TIME_AUDIT_V1.md` | 사건율·시간 감사 |
| `docs/legacy-probabilistic/DUAL_GCP_EVALUATION_PROTOCOL.md` | GCP 실험 프로토콜 |
| [docs/history/PROJECT_CLEANUP_AUDIT_V1.md](docs/history/PROJECT_CLEANUP_AUDIT_V1.md) | 정리 원칙 |
| `docs/legacy-probabilistic/STAGE_C_*_REVIEW.md` | 확률 세계 단계별 검토 (약 20개) |
| `LLM_HANDOFF/` | 계통별 파일 카탈로그 (외부 LLM 전달용, 생성 당시 논리 카탈로그. 문서 이동 후 현재 원문은 docs 안내/분류표 참조) |

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
