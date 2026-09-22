# 현재 상태

**최종 갱신:** 2026-09-23
**검증:** 전체 테스트 1361개 로컬 통과 (B0.7 완료 시점 실측 1228개 — 이 문서의 옛 "→1046" 표기는 B0.7 커밋이 갱신하지 않고 지나간 낡은 숫자였음, 2026-09-23 확인). GitHub Actions 독립 재실행 기록 없음 — 로컬 실행 결과임을 구분해 기록
**Git:** 2026-09-21 초기화. 이전 상태는 `D:\KiroCrewTraceVault\success-is-mother-of-failure\project-snapshots\20260921_090715_pre_git_init\` 에 봉인

이 문서는 작업이 진행될 때마다 갱신한다. 낡았다고 판단되면 먼저 고치고 작업한다.

---

## 한 줄 요약

결정론 A 물리 기반과 B 관찰 도구는 작동하지만, **진짜 학습형 B도 없고 A의 화학도 아직 없다.**
생명·복사·진화의 새 증거는 나오지 않았다.

---

## 영역별 상태

| 영역 | 상태 | 판정 |
|---|---|---|
| 결정론 A 물리 기반 | 안정 | 재현·지역성 검증됨. 보존은 2026-09-21 독립 재집계로 교차 검증 |
| CPU/GPU field 동등성 | 안정 | 매 tick 동일, 512²에서 약 3.9배 |
| B 외부 경계·권한 | 안정 | 내부 자유·외부 claim 검증 |
| 사용자 전용 계보 | 안정 | 12/12 private trace 검증 통과 |
| 독립 B 표현 | 초기 후보 | Cognitive Map·ChangeGraph는 **수작업 규칙 모델** |
| 불확실성·반사실 | 초기 후보 | 작은 고정 benchmark |
| 이론 수정 | 기준 사례 | A에 이미 있는 vapor를 제한 이론에서 뺀 실험 |
| Held-out 실험 | **실행 금지** | 제안서 봉인됨, 과학적 준비 미완 |
| 실제 학습형 B | 미착수 | JEPA·신경망·자율 변수 발견 없음 |
| 결정론 고분자 | 1단계 완료 | v2 다중 결합·사슬 성장. **실측 최장 길이 3** — 자유로운 성장 아님. 촉매·복사는 미착수 |
| 작업 묶음 4 전제조건 | 조사 완료 | 3체 충돌·길이 4는 **기회 0**. 주형·분열은 기회 있음 |

---

## 완료된 것

### A (결정론 세계)

- 난수·seed·추첨 없는 결정론 CPU 기준
- 물질·에너지·운동량 + 외부 에너지 장부
- 지역 열·물·용질·수증기 이동
- 광물 용해·침전, 물 상변화(증발·응축)
- 물리 단위·flux 계약, 해상도 수렴 후보
- CUDA int64 field transport, CPU와 매 tick 동등
- GPU 상주 field에서 CPU 대비 최대 약 3.9배

### B (관찰·이론 도구)

구현 순서대로:

1. `ExactOracleAdapter` — 정답을 아는 기준 어댑터
2. `b_language` + `BrainAdapter` — 외부 경계 규격
3. `CognitiveMap` — 현재 상태 압축 표현
4. `TraceViewBroker` + `ChangeGraph` — 변화 이력 기반 표현
5. `adapter_comparison` — 동일 외부 질의 병렬 비교
6. `impact_scope` — 다음 tick 영향 범위 예측
7. `HypothesisSet` — 여러 설명 동시 보존, 근거 없는 확률 금지
8. `CounterfactualBranch` — 다중 정밀도 분기 + 무행동 대조군
9. `ResidualPattern` + `TheoryRevisionProposal` — 반복 오차에서 수정 후보 생성
10. `ExperimentProposal` — 사용자 승인형, 자동 실행 차단

### 인프라

- 사용자 전용 매 tick A/B full trace + hash chain (D: vault)
- Git 저장소 + D: 스냅샷 (2026-09-21)

### 독립 감사 (`audit/`, engine import 금지)

- `independent_trace/` — 기록장 검증. 해시를 직접 정규화하고 델타를 **적용**해 확인
- `independent_conservation/` — 보존 재집계. 커널 집계와 대조
- `independent_compliance/` — **명세 준수.** 환경 field(막힌 벽·순간이동·한도 초과)와
  입자 물리(결합 규칙·최소 에너지·포트 한도·한 칸 이동·사슬 무결성)
- 셋 다 결함 주입으로 실효성 확인됨 (`docs/current/VERIFICATION_LIMITS_AND_LESSONS.md`)

---

## 막혀 있는 것 — held-out 제안서 v1

**위치:** `D:\KiroCrewTraceVault\success-is-mother-of-failure\heldout-experiment-proposal-v1`

```text
governance_valid  = true
scientific_status = not-run
execution_allowed = false
A records         = 0
```

**실행하면 안 되는 이유 4가지:**

1. **후보별 수치 예측이 봉인되지 않았다.**
   세 후보(관측 pipeline 검사 / vapor 변수 추가 / vapor 관계 모델)가 이름만 있고
   "heldout-vapor-5에서 어느 위치의 vapor가 얼마→얼마로 바뀔 것인가"라는 구체적 예측이 없다.
   이 상태로 실행하면 결과를 본 뒤 설명을 맞추는 사후 해석이 된다.

2. ~~**독립 trace parser가 없다.**~~ → **2026-09-21 해결됨.**
   `audit/independent_trace/`가 `engine`을 전혀 import하지 않는 두 번째 검증기다.
   해시는 정규화 규칙을 직접 명시해 생성하고, 델타는 재생성 비교가 아니라 **실제 적용**으로 검증한다.
   결함 주입 실험에서 엔진 검증기가 통과시킨 기록 결함을 독립 검증기가 잡아냈다.
   현재 vault trace 12/12가 엔진·독립·외부 `sha256sum` 3중 일치.
   실행: `python run_independent_trace_audit.py --vault --compare-engine`

3. **held-out이 약하다.**
   훈련 vapor 값 4·6·8·10 / held-out 0·5·13 — 값은 겹치지 않지만 **위치·열 경계·격자 크기가 거의 동일하다.**
   관계 모델이 특정 위치만 외워도 통과할 수 있다.

4. **이건 아직 "발견"이 아니다.**
   vapor는 A에 원래 있고 제한 이론에서만 뺀 변수다.
   증명된 것: 반복 잔차 → 누락 변수 후보 제안 pipeline이 작동한다.
   증명되지 않은 것: B가 A 명세에 없던 새 변수를 스스로 발견했다.

**v1은 삭제하지 않는다.** 보강하려면 v2를 새로 만든다.

---

## 알려진 기술 부채

| 항목 | 내용 | 영향 |
|---|---|---|
| private 함수 결합 | full trace·GPU가 환경 커널의 `_phase`, `_convert_local_mineral` 등 내부 함수를 직접 호출 | 커널 내부 이름이 바뀌면 추적기와 GPU가 함께 깨짐. 공개 stage API 필요 |
| 평가 의미 혼재 | `BoundaryEvaluation.complete_match=false`가 반박·미검사·예산 보류·실행 전을 모두 표현 | `protocol_valid` / `scientific_status` / `coverage_status` / `execution_status` 분리 필요 |
| 영향 범위 과잉 | 후보 263칸 vs 실제 변화 4칸 (누락 0, 과잉 259) | 안전하지만 "효율적"이라 부를 수 없음. 누락을 줄이기 전에 과잉부터 줄이면 원인을 놓칠 위험이 있어 현재 순서는 맞음 |
| 권한 격리 | Windows ACL은 다른 OS 계정만 차단. 같은 사용자 권한의 임의 B 코드는 못 막음 | 학습형 B 붙이기 전에 저권한 프로세스나 trace broker 필요 |
| MechanismCandidate 필드 의미 혼동 위험 | `MechanismCandidate.source_role`은 조사가 시작된 개입/관심 출발 role이고, 이 candidate가 실제로 분석하는 role은 `candidate.path[*].role`(현재 계약상 path 전체가 동일 role)이다. 이름만 보면 `source_role`이 관찰 대상처럼 보여 실제로 `causal_path_builder.build_from_evidence`에서 `source_role`을 잘못 참조해 path가 항상 None이 되는 버그가 발생한 적 있음 (수정됨) | `test_deterministic_causal_path_builder.py::test_build_from_evidence_uses_observed_role_not_source_role`로 현재 동작(`path`의 role 사용, `source_role` 미사용)을 회귀 고정함. 장기적으로는 `investigation_source_role`/`observed_role`처럼 필드명 자체를 분리하는 리팩터링 권장. 현재 동작을 깨지 않는 별도 변경으로 수행할 것 |

---

## A의 근본적 한계

현재 A는 초기 지구 화학이나 생명 발생을 시험할 수준이 **아니다.**

- ~~입자당 결합 하나~~ → v2에서 `ports`만큼 다중 결합
- ~~결합 구조 정지~~ → v2에서 사슬이 한 몸으로 이동
- 다중 화학 중간체 없음
- **다체 충돌 없음** — 한 칸에 3개 이상이면 커널이 건너뛴다 (2026-09-21 조사)
- **ID가 물리를 결정함** — 구별 불가능한 후보 중 번호가 작은 쪽이 이긴다 (2026-09-22 증명)
- 촉매 구조 없음
- **고분자 없음** — 사슬 최장 3. 움직이는 사슬은 자랄 수 없다
- **주형 기반 복사 없음** — 결합된 입자가 한 칸에 겹쳐 있어 "옆"이라는 개념이 없다
- 실제 경계 물질 없음
- **독립 경계 절단·봉합 없음**
- 초기 지구 실측 환경군 없음

---

## 동결된 계통 — 확률 세계 (`scheduler-v1`)

**수정 대상이 아니다. 보존된 비교 기준선이다.**

확정된 판정:

- GCP1: 64세계 × 6시간 → 분할 4, 융합 4
- GCP2: 12세계 × 32시간 → 분할 0, 융합 0
- 통합 768 세계·시간, **독립 후손 0**
- 관찰된 분할은 같은 cyclic strand의 일시적 위상 분할이었음
- 독립 경계 scission+closure 경로 없음
- 원인: 전역 후보 경쟁, 단위 불일치, 벽시계 노출량 차이
- **추가 장기 확률 VM 실험 중단**

핵심 코드: `engine/sequence/`, `engine/living/events.py`
(`engine.sequence`가 `engine.living.events`의 사건 기록 형식에 의존하므로 `engine/living/`을 통째로 지우면 안 된다.)

---

## 다음 갈림길

**2026-09-21: (나)를 선택했다.** 나머지 셋은 보존하되 진행하지 않는다.

### (가) held-out v2 — B를 계속 판다

1. ~~독립 trace parser 구현~~ **완료 (2026-09-21)** — `audit/independent_trace/`
2. **후보별 수치 예측 봉인** ← 다음 차례
   세 후보(관측 pipeline / vapor 변수 추가 / vapor 관계 모델)가
   "heldout-vapor-5의 어느 위치에서 vapor가 얼마→얼마"를 각각 예측하게 하고 해시로 봉인
3. 위치·열 경계·격자 크기까지 바꾼 강한 held-out spec
4. v2 생성 (v1은 보존)
5. 사용자 승인 후 실행

### (나) A 화학·고분자 — 세계를 키운다 *(작업 묶음 4)* ← **선택됨 (2026-09-21)**

- ~~다중 결합·사슬 성장~~ **완료 (2026-09-21)** — causal v2.
  **주의:** 성장 경로가 열렸다는 뜻이지 자유롭게 자란다는 뜻이 아니다 (실측 최장 3)
- ~~전제조건 조사~~ **완료 (2026-09-21)** — `docs/current/PRECONDITION_CENSUS_2026-09-21.md`
- **완료 데모:** 고수준 복사·분열 명령 없이 실제 충돌 과정이 고분자와 두 독립 경계를 만들거나 실패한다

**조사 결과 순서가 바뀌었다.** 촉매·주형에 선행 단계가 드러났다.

| 순서 | 할 일 | 왜 |
|---|---|---|
| 0 | ~~결정 불가능 상황 탐지~~ **완료 (2026-09-22)** | `contested_census.py`. **ID가 물리를 결정하고 있음이 증명됐다** — 구별 불가능한 두 멤버 중 번호가 작은 쪽이 이긴다 |
| 1 | **다체 충돌 처리** — `_resolve_collisions`의 `len(group) != 2` | 촉매의 전제. 3체가 한 칸에 모여도 커널이 건너뛰어 서로 통과한다. 입자 24개·60 tick에서도 3체 처리 **0회** |
| 2 | **사슬 성장 조건** — 움직이는 사슬은 자랄 수 없음 (`if holder.kinetic_energy: continue`) | 길이 4의 전제. 현재 최장 3에서 멈춘다. 완화할지는 **설계 결정, 버그 아님** |
| 2 | ~~`PhysicalBond` 재구성, 인접 불변조건~~ **완료 (2026-09-22)** | v3 `PortBond` 타입 신설(v1/v2 `PhysicalBond`는 그대로). `neighbour()`가 스트리밍과 같은 공식으로 인접 판정. 10개 성공 조건 검증, 결함 주입 5종 전부 검출. **v2 run digest byte 동일 유지** |
| 3 | **사슬의 공간 구조** — 결합된 입자가 전부 같은 칸에 겹쳐 있음 | 주형의 전제 → `docs/current/MINIMAL_LOCAL_GEOMETRY_V1.md`. v3 `PortBond`로 기하는 열렸고, 다음은 아래 v4 단계 |
| 4 | 촉매 / 주형 복사 / 경계 물질 / 독립 분열 | 위가 열린 뒤 |

**causal v4 — 다음 실제 작업 (2026-09-22 확정):**

유형 F 결함 둘이 v1부터 있었음이 측정으로 드러났다. 고치려 하자 v1 digest가
바뀌었고, 거버넌스 9·10번에 따라 **v1/v2/v3는 레거시로 동결하고 v4에서
고친다.** v4의 지위는 `experimental` — Stage D까지 끝난 뒤 동결을 판단한다.

| 단계 | 내용 | 상태 |
|---|---|---|
| **Stage A** | 수정된 충돌 의미 — 암묵적 orientation 회전 제거, 등에너지에서만 90도 산란 | **완료 (2026-09-22)** |
| Stage B | `StructureState` — 구조가 운동량을 소유 | **다음 차례** |
| Stage C | 재명명·순서 불변성 | |
| Stage D | 구조 이동 | |

**Stage A 구현 요약:**

- `causal_spec.py`: `FORMAT_V4` 추가. v3와 동일한 named-port 문법을 계승
  (`is_v3` → `has_named_ports = format in (FORMAT_V3, FORMAT_V4)`로 일반화)
- `causal_kernel.py`: `_break_existing`·`_resolve_collisions`에
  `corrected_collision_semantics = spec.format == FORMAT_V4` 게이트 추가.
  v4 경로에서만 (1) 방출·산란이 `orientation`을 건드리지 않음 (2) 90도
  산란이 등에너지 쌍에서만 발동 — 다른 규칙도 안 맞으면 상태 불변
- 레거시 테스트 분리: `test_known_defects_causal_kernel.py`의
  unequal-energy 결함 테스트를 `tests/test_legacy_causal_semantics.py`로
  이동(v1/v2/v3 전용, "실패하면 나쁜 소식"). v4용 positive test 3종을
  `test_deterministic_causal_kernel.py`에 추가
- 검증: 출하된 v1 세계 digest가 Stage A 적용 전후 동일
  (`21385184...93ce79`) — v3 상태 지속성·대각 불가능성 등 기존 테스트의
  `_Spec` fixture 두 곳이 `format` 속성이 없어 `AttributeError`로 드러남 →
  각각 v2/v3 레거시 포맷 명시로 수정 (설계 변경 아님, fixture 결함)
- 전체 테스트 1046개 통과 (기존 1041 + v4 신규 5)

설계: `docs/current/CAUSAL_COLLISION_SEMANTICS_V4.md`

이미 열려 있는 기회: **정지 사슬+빈 port**(60/60 tick), **동시 사슬 2개 이상**(최대 12).
주형·분열은 "기회 없음"이 아니다.

**아직 남은 것: 시험지.** 현재 causal 세계 2개는 손으로 배치한 스모크 테스트라 답이 정해져 있다.
1~3이 열린 뒤 답을 모르는 세계 묶음(실패하도록 설계된 것 포함)이 필요하다.

현재 B가 "수작업 규칙 모델"이라 아무리 다듬어도 자율 발견이 안 나오는 점, A가 단순해서 B가 풀 흥미로운 문제 자체가 없는 점을 고려하면 이쪽이 원래 목표에 더 가깝다.

### (다) 기술 부채 정리

- 공개 stage API
- 평가 상태 플래그 분리

### (라) 감사 확장

- vault trace 중 `spec.json` 없는 8개는 보존·준수 감사 불가 → 이후 실행은 spec을 함께 저장
- ~~명세 준수 검증~~ **완료 (2026-09-21)** — 환경 field + 입자 물리
- 남은 미검증: 세밀한 이동량 공식 (한도만 보고 정확한 양은 안 봄)

### (마) Ground-Truth를 B가 실제로 연구 가능하게 만들기 *(2026-09-23 착수, G0~G6c-3.3 완료)*

`ground_truth/`의 GT-M1/GT-2/GT-3는 현재 답안지 레벨(순수함수)에만 있고, B가 평소 쓰는
`AExecutor → research_loop → broad_explorer → prediction/evidence` 경로로 연구할 수 있는
A-compatible 실행 world가 아니다. B0.3~B0.7 blind evaluation(B가 정답을 모르는 채로 이 세
구조를 스스로 재발견하는가)을 하려면 이게 선행돼야 한다.

조사 결과(2026-09-23), "`AExecutor`만 얇은 Protocol로 감싸면 된다"는 최초 가정은 실제
코드에서 반박됨. `CausalWorldSpec`을 참조하는 B0 모듈이 20개 있고, 그중:

- **얕은 결합** (수 줄 내 어댑터화 가능): `causal_executor.py`(이미 Protocol), `research_loop.py`의
  `execute_through_a`/digest 비교/journal·domain·evidence 부기, `broad_explorer.py`의
  `apply_control`+`from_mapping` 호출(정확히 1곳)
- **구조적으로 깊음** (신규 타입/분기 추가가 불가피, 얇은 어댑터로 안 됨):
  - `causal_hypothesis.py` — `CausalPrediction` Union이 `expected_total_energy`/`expected_momentum`/
    `expected_bond_count`/`expected_counts` 등 A0 물리 필드에 하드코딩. generic observable
    (`"particle.kinetic_energy"` 같은 role.field 표현) prediction 타입이 아예 없음
  - `exploration_control.py` — `PARTICLE_FIELDS`/`HEAT_FIELDS`/`BOND_RULE_FIELDS` 화이트리스트와
    `apply_control()`이 `spec.particles`/`spec.heat`/`spec.bond_rules`를 직접 `replace()`하는
    A0 전용 로직. GT-2/3/M1용 새 `ControlTarget`이 병렬로 필요
  - `research_loop.py`의 `observe()`/`_observed_value()` — `initial_causal_state`/`CausalRun.checkpoints`
    필드에 직접 결합
  - `causal_experiment.py`의 `CausalExperimentArm.intended_spec`/`submitted_spec` — `CausalWorldSpec`
    타입 고정

사용자가 제안한 절단선: `ResearchWorldSpec`/`ResearchWorldAdapter` 최소 공통 Protocol을 새로
추가하고, `PhysicalCausalWorldAdapter`(기존 코드 그대로 감쌈, 물리 A 무변경)와
`SyntheticWorldAdapter`(GT-M1/GT-2/GT-3 공용) 두 구현체로 나눈다. `deep_investigator`,
`trace_model`, `mechanism_tester`, `intervention_feasibility`는 이번 범위에서 제외 — B0.4/B0.5
전체 일반화는 더 뒤로 미룬다. B에게는 world 이름에 "direct"/"conditional"/"mediator" 같은
정답 힌트를 노출하지 않는다(`WORLD-S02` 같은 익명 id만).

**사용자가 `RESEARCH_WORLD_ABSTRACTION_V1` 구현 명세를 완성** (Gate G0~G11, 커밋 A~I,
Phase 1~3 로드맵). 이번 세션은 **G0~G2까지만** 진행하기로 명시적으로 범위를 잘랐다 —
G3부터는 `research_loop`/`broad_explorer`의 실행 경로 자체를 바꾸기 시작해서 "새 추상화
검증"에서 "기존 B 동작 이주"로 성격이 바뀌기 때문.

**G0 완료** — `tests/test_deterministic_research_world_characterization.py` (11개).
아직 아무 코드도 바꾸지 않은 상태에서 `ExecutionResult.canonical()`, `observe()`의
observable payload, `compare_results()`의 정확한 verdict 문자열(`supported`/
`contradicted_in_domain`/`underspecified`), `run_exploration()`의 heat-sweep 정확한
evidence/coverage, `CausalExperimentArm.canonical()`을 리터럴 값으로 고정. 명세 초안에서
`total_energy == 4`, `spec_digest`, `CausalExperimentArm(arm_id, intended, submitted)` 등
여러 가정이 실제 코드와 달랐음을 이 단계에서 발견·정정 (heat cell 에너지를 빼먹음, 실제
키는 `intended_spec_digest`, 실제 생성자는 `dimension`/`resolves_hypothesis_ids` 필수).

**G1 완료** — `engine/deterministic/research_world.py`(`ResearchWorldSpec`/`ResearchRun`
Protocol, `ResearchWorldError`/`WorldCompatibilityError`/`UnknownControlError`/
`InvalidControlValueError`/`UnsupportedPredictionError`), `research_adapter.py`
(`ResearchControlDefinition` Protocol, `WorldObservation`, `PredictionEvaluation`,
`ResearchWorldAdapter` Protocol — `execute()` 없음, 실행과 해석 책임 분리). `CausalWorldSpec`/
`CausalRun`/`ControlDefinition`이 **코드 수정 없이** 구조적으로 Protocol을 만족함을 확인
(`test_deterministic_research_world.py` 4개, `test_deterministic_research_adapter.py` 6개).

**G2 완료** — `engine/deterministic/physical_research_adapter.py`:
`PhysicalCausalResearchAdapter`가 기존 `apply_control`/`CausalWorldSpec.from_mapping`/
`initial_causal_state`/`research_loop._observed_value`의 kind-dispatch를 그대로 감싼다
(런타임에서 `research_loop`를 import하지 않도록 dispatch 로직은 독립 재구현 — 주석으로
이유 명시: G3에서 `research_loop`가 adapter에 의존하게 될 예정이므로 반대 방향 의존을
만들지 않음). `test_deterministic_physical_research_adapter.py`(13개)가 adapter 출력과
"레거시 방식으로 직접 계산한 값"을 매번 나란히 비교해서 **한 비트도 다르지 않음**을 증명 —
하드코딩된 기대값이 아니라 기존 함수 재호출과의 동등성만 assert. `engine/deterministic/__init__.py`
에 신규 이름 export. 전체 테스트 1251→1285 (신규 34개), 전부 통과.

**G3~G5 완료** (같은 날, 1285→1290). `research_loop.py`: `observe()`/`compare_results()`가
새 generic core `observe_world()`/`compare_results_with_adapter()`의 얇은 물리-A 호환
wrapper가 됨 (`_PHYSICAL_ADAPTER = PhysicalCausalResearchAdapter()` 기본값 주입). 이 과정에서
동작 차이 하나 발견·수정: 기존 `observe()`는 `state_digest`를 `observables` 딕셔너리 **안에**
병합해 넣었는데, `WorldObservation`은 그걸 별도 필드로 분리해서 G2 설계 그대로 옮기면
관측 payload가 달라졌음 — `observe_world`에서 `{**observables, "state_digest": ...}`로 명시
병합해 정정. `broad_explorer.py`: `run_exploration()`이 새 generic core
`run_research_exploration()`의 wrapper가 됨. `apply_control`+`CausalWorldSpec.from_mapping`
→ `adapter.apply_control()`+`adapter.validate()`, `_compare` → `adapter.evaluate_prediction()`
기반 `_compare_with_adapter`로 치환. 신규 `research_prediction.py`:
`CandidatePredictionProvider` Protocol + `StaticPredictionProvider`(기존 동작 그대로: 모든
후보가 같은 prediction 공유) + `FunctionalPredictionProvider`(후보의 compiled spec을 보고
후보별로 다른 prediction 생성 — 아직 `CausalPrediction` 자체는 안 건드림, 후보별 "어디서
prediction을 가져오는가"만 분리). 예외 처리: `WorldCompatibilityError`/`UnknownControlError`
(설정 실수)는 컴파일 실패로 삼키지 않고 그대로 전파, `ValueError`/`TypeError`(후보 자신의
불법 값 — 기존 `apply_control`/`from_mapping`이 실제로 던지는 타입)만 `CandidateCompilationFailure`로
기록 — 이걸 테스트(`test_run_research_exploration_never_swallows_world_compatibility_error`)로
고정. 완료 조건 그대로 충족: 기존 G0 characterization 출력·digest 전부 동일
(`test_run_research_exploration_with_static_provider_matches_run_exploration_exactly` 등으로
확인). `CandidatePredictionProvider`가 실제로 후보마다 다른 prediction을 줄 수 있음을
`FunctionalPredictionProvider`로 검증(자기 자신의 실행 결과를 되읽어 예측하는 self-consistency
테스트). 이번 세션에서 건드리지 않음: `causal_experiment.py`/`causal_hypothesis.py`의 타입
일반화(`CausalPrediction`은 여전히 물리 필드 전용), synthetic kernel/spec/adapter,
GT-2/3/M1의 실행 가능 버전 — 이건 G6+ (다음 세션들).

**검증 수준 메모:** 아래 "1296개 전부 통과"도 이 세션에서 로컬로 직접 실행해 확인한 결과다.
GitHub Actions의 독립 CI 재실행 기록은 없다 — 이 구분을 흐리지 않을 것.

**G6a+G6b 완료** (같은 날, 1290→1296). 사용자가 G3~G5를 GitHub 실제 HEAD로 재검증한 뒤,
연구 쪽(Broad Explorer)은 world-generic이 됐는데 **실행 경계는 여전히 물리 전용**이라는
병목을 지적 — `AExecutor.execute(spec: CausalWorldSpec)`, `ExecutionResult.run: CausalRun | None`,
`execute_through_a(..., submitted_spec: CausalWorldSpec)`가 타입 힌트 레벨에서 아직 좁았음.

- **G6a**: `causal_executor.py`의 `AExecutor` Protocol과 `ExecutionResult.run`을
  `ResearchWorldSpec`/`ResearchRun`으로 확장. `research_loop.execute_through_a`도 동일하게
  확장. `RealCausalAExecutor`/`StubAExecutor`의 실제 동작은 무변경 — `@runtime_checkable`
  Protocol은 파라미터 타입을 검사하지 않으므로 안전하게 넓어짐을 확인. `RealCausalAExecutor.execute`
  자체의 파라미터는 의도적으로 `CausalWorldSpec`으로 유지(실제로 물리 전용이므로 거짓 계약을
  피함) — Protocol이 넓어진 것과 개별 구현체가 자기 세계에 맞게 좁은 것은 다른 문제.
- **G6b**: 오류 계약 정리. (1) `run_research_exploration`에서 `controls[control_id]`가
  없을 때 `KeyError`가 그대로 새는 구멍을 발견 — `UnknownControlError`로 명시 변환
  (동작 방향은 우연히 맞았지만 G1 오류 계약이 실제로 적용되지 않고 있었음). (2)
  `InvalidControlValueError`가 `ResearchWorldError`(설정 오류) 계층에 있는데 실제로는
  `broad_explorer`가 연구 데이터(`CandidateCompilationFailure`)로 처리하는 모순을 발견 —
  타입 계층은 그대로 두고 docstring으로 "이 타입만 예외: 설정 오류가 아니라 후보 자신의
  불법 값"임을 명시해 의미를 확정. 아직 어떤 adapter도 실제로 이 타입을 던지지 않음(향후
  synthetic adapter가 쓸 예정) — 그럼에도 `except` 절이 올바르게 처리 준비돼 있음을
  단위 테스트로 고정.
- **문서 정정**: `broad_explorer.py` 상단 docstring이 "각 candidate가 `CausalWorldSpec`으로
  컴파일된다"/"`causal_kernel`에서 실행된다"고 낡게 남아있던 것을 G4~G6a 이후 실제 구조에
  맞게 갱신.

신규 `tests/test_deterministic_research_execution_boundary.py`(6개): `_FakeSpec`/`_FakeRun`/
`_FakeExecutor`(물리 타입이 전혀 아닌 최소 fake)로 `AExecutor` Protocol이 실제로 비물리
executor를 받아들임을 증명, `UnknownControlError`/`InvalidControlValueError`가 각각
올바른 경로(전파 vs 컴파일 실패)로 가는지 확인. G6c(synthetic kernel/spec/adapter/executor)는
아직 미착수 — 이번엔 실행 경계 타입만 넓혔을 뿐 실제 synthetic 세계는 여전히 없음.

---

## 최근 이력

| 날짜 | 사건 |
|---|---|
| 2026-09-18 | GCP 64세계 실행. "자연 분열·융합 관찰"로 보고됨 |
| 2026-09-19 | GCP 2대 병렬 (1번 6시간, 2번 32시간). 계보 추적기 도입 |
| 2026-09-20 | **`exactly one ordinary event` 발견.** tick당 사건 하나만 처리되어 경쟁이 불가능했음이 드러남. 확률 → 결정론 전환 결정 |
| 2026-09-20~21 | A/B 분리 확정. B 도구 10종 구현 (806→837 테스트) |
| 2026-09-21 | 중간 점검, LLM_HANDOFF 카탈로그, D: 스냅샷 + Git 초기화 |
| 2026-09-21 | 지침 4종. 독립 검증기 3종 — trace(837→856), 보존(→872), 명세 준수(→892) |
| 2026-09-21 | causal v2 — 다중 결합·사슬 성장·사슬 이동 (→907). 독립 집계가 낡은 운동량 규칙을 잡아냄 |
| 2026-09-21 | 입자 물리 준수 검증기 (→932). 위반 9종 탐지, 전부 보존은 통과 |
| 2026-09-21 | **(나) 선택.** 전제조건 조사 (→947). 3체 조우는 가능하나 커널이 처리 안 함 — 촉매 이전에 다체 충돌이 먼저 |
| 2026-09-22 | **"둘씩 처리" 제안 기각.** 국소 상호작용 원칙 4종 채택. 경합 탐지기 (→957) — ID가 물리를 결정하고 있음이 증명됨 |
| 2026-09-22 | 기하가 단계 2의 **전제**로 재판정. known-defect 테스트 3종 분리 (→959) |
| 2026-09-22 | 최소 국소 기하 v1 설계. 근본 원인 규명 — **포트에 이름이 없어서** 고를 근거가 없었다. 승인됨 |
| 2026-09-22 | v3 명세 — 포트 이름 (→972) |
| 2026-09-22 | v3 `PortBond` + 인접 불변조건 (→990). v1/v2 `PhysicalBond`는 타입 분리로 무손상. digest 보존 확인 |
| 2026-09-22 | `StructureState` 설계 승인. Q2(에너지를 운동량에서 유도)가 측정으로 두 번 반박 — 별도 상태량으로 확정 |
| 2026-09-22 | **v3 구조가 tick을 못 넘기던 문제 해결** (→1040). 상태를 위치 인수로 재구성해 `port_bonds`·`grid_size`·`named_ports`가 매 tick 증발하고 있었다. causal 4곳 + environment 4곳 + GPU 2곳 + counterfactual 1곳을 `replace()`로 전환. environment 경로는 `port_limits`·`chains_may_move`까지 잃고 있었다 — v2 사슬도 환경 세계 안에서는 작동하지 않았다는 뜻 |
| 2026-09-22 | **새 결함 기록** — 고정 속도 격자 충돌 규칙(A0 상속)이 에너지가 다르면 운동량을 90도 회전시킨다. 교훈 유형 F 신설. 대각 도달 불가능성을 테스트로 고정 |
| 2026-09-22 | **v3의 `port_limits`/`chains_may_move`가 실측과 다르게 문서화돼 있었음을 발견·정정** (→1041). 둘 다 format 동등성 비교(`== FORMAT_V2`)로만 판정해 v3가 v2가 아니라 v1 갈래로 빠진다 — `port_limits=1`, `chains_may_move=False`. 값 자체는 현재 단계에 맞으므로(구조 이동 미구현) 코드는 그대로 두고 문서를 정정, 테스트로 고정. AST 회귀 검사도 `ck.CausalWorldState(...)` 같은 qualified call을 놓치는 구멍을 발견해 하드닝 |
| 2026-09-22 | **causal v4 Stage A 구현 완료** (→1046). `FORMAT_V4` 추가, v3 named-port 문법 계승. `corrected_collision_semantics = spec.format == FORMAT_V4` 게이트로 orientation 암묵 회전 제거 + 90도 산란을 등에너지로 제한 — v4 경로만. v1/v2/v3 digest는 Stage A 적용 전후 동일함을 측정 확인. known-defect 테스트 1종을 legacy로 이동, v4 positive test 3종 신설. 부수 발견: 대각 불가능성·v3 상태 지속성 테스트의 `_Spec` fixture 두 곳에 `format` 속성이 없어 새 게이트가 `AttributeError`를 냄 — 각각 레거시 포맷 명시로 수정 |
| 2026-09-23 | **독립 Ground-Truth 답안지 신설, 같은 날 세 차례 정정** (최종 `ground_truth/`, 저장소 최상위, 1228→1251). 최초 구현: `test_deterministic_missing_link_investigator.py`의 "hidden mediator" 시나리오가 B0.7 자신의 출력(`investigate_missing_link`)을 정답처럼 assert하는 순환논리였음을 사용자가 지적. B0.3 이상을 전혀 import하지 않는 답안지로 GT-1(Mediator, A0 `causal_kernel` 직접 조작)·GT-2(Direct)·GT-3(Conditional) 3-world를 `audit/ground_truth/`에 신설, 3/3 VALID로 봉인. 사용자가 같은 날 세 가지를 지적해 정정: (1) 테스트 개수 표기가 "1046→1246"으로 잘못됨(B0.7 완료 시점 실측은 1228) — "1228→1246"으로 수정. (2) `audit/`의 "engine import 절대 금지" 불변식에 `ground_truth`만 예외를 둔 게 그 불변식을 약화시킨다 — 예외를 없애고 `ground_truth/`를 저장소 최상위로 이동, `audit/`는 원래 불변식 복원. (3) GT-1의 intervention 3("B 차단")이 실제로는 입자 배치를 바꿔 다른 세계를 만든 것이라 순수 mediator 정답지로는 약하다 — GT-1은 "레거시 physical sanity test"로 격하하고, mediator(B)에 A와 독립된 public control(`step_with_mediator_override`)을 가진 전용 synthetic world **GT-M1**을 정답지 레벨에서 신설(4-world, 4/4 VALID, 신규 테스트 5개). GT-2/3(와 향후 GT-M1의 실행 가능 버전)가 B가 실제로 연구할 수 있는 A-compatible world가 아니라는 지적은 조사 결과 범위가 커서 별도 세션으로 분리: `CausalWorldSpec`이 `causal_hypothesis.py`(prediction 어휘가 물리 필드에 폐쇄)·`exploration_control.py`(control 필드 화이트리스트가 A0 물리 어휘 전용) 등 B0 20개 모듈에 구조적으로 얽혀 있어, "AExecutor만 얇게 Protocol화하면 된다"는 최초 가정이 조사로 반박됨 — `ResearchWorldAdapter` 공통 경계 설계가 선행돼야 함 |
| 2026-09-23 | **Research World Abstraction G0~G2 완료** (1251→1285). 사용자가 `RESEARCH_WORLD_ABSTRACTION_V1` 구현 명세(Gate G0~G11, Phase 1~3)를 작성, 이번 세션은 G0~G2로 명시적 절단. G0: `ExecutionResult.canonical()`/`observe()`/`compare_results()`/`run_exploration()`/`CausalExperimentArm.canonical()`의 현재 동작을 characterization test 11개로 리터럴 고정 — 이 단계에서 명세 초안의 여러 가정(`total_energy` 계산에서 heat 누락, 존재하지 않는 `spec_digest` 필드명, `CausalExperimentArm`의 실제 생성자 인자 수)이 실제 코드와 다름을 발견·정정. G1: `research_world.py`(`ResearchWorldSpec`/`ResearchRun` Protocol + 4종 오류 타입), `research_adapter.py`(`ResearchControlDefinition` Protocol, `WorldObservation`, `PredictionEvaluation`, `ResearchWorldAdapter` Protocol — `execute()` 없음, 실행/해석 책임 분리) 신설. `CausalWorldSpec`/`CausalRun`/`ControlDefinition`이 **코드 수정 없이** 구조적으로 Protocol을 만족함을 확인. G2: `PhysicalCausalResearchAdapter`가 기존 물리 경로(`apply_control`/`from_mapping`/`initial_causal_state`/`_observed_value` kind-dispatch)를 그대로 감쌈 — 하드코딩 기대값이 아니라 "레거시 함수 재호출과의 동등성"만 assert하는 방식으로 13개 테스트가 "한 비트도 안 바뀜"을 증명. 부수 발견: 이전 커밋(`1913829`)이 실제로는 `ModuleNotFoundError`로 깨진 상태였음을 이번 세션에서 발견해 별도 fix 커밋(`5771d60`)으로 수정 |
| 2026-09-23 | **Research World Abstraction G3~G5 완료** (같은 날, 1285→1290). `research_loop.observe/compare_results`와 `broad_explorer.run_exploration`이 각각 새 generic core(`observe_world`/`compare_results_with_adapter`/`run_research_exploration`)의 물리-A 호환 wrapper가 됨. `apply_control`+`CausalWorldSpec.from_mapping` → `adapter.apply_control()`+`adapter.validate()`, prediction 비교 → `adapter.evaluate_prediction()` 기반으로 치환. 신규 `research_prediction.py`: `CandidatePredictionProvider`(`StaticPredictionProvider`/`FunctionalPredictionProvider`) — 후보별로 다른 prediction을 줄 수 있는 구조이지만 `CausalPrediction` 자체는 여전히 물리 필드 전용, 이번엔 "출처 분리"만. 마이그레이션 중 실동작 차이 하나 발견: 기존 `observe()`는 `state_digest`를 `observables` 딕셔너리 안에 병합했는데 `WorldObservation`은 별도 필드라 그대로 옮기면 payload가 달라짐 — 명시 병합으로 정정. 예외 정책: `WorldCompatibilityError`/`UnknownControlError`(설정 실수)는 전파, `ValueError`/`TypeError`(후보 자신의 불법 값)만 컴파일 실패로 기록 — 이 구분을 테스트로 고정. G0 characterization 출력·digest가 새 경로에서도 완전히 동일함을 확인(완료 조건 충족). GitHub Actions 독립 CI 재실행 기록은 없음 — "1290개 통과"는 로컬 실행 결과. 다음은 G6+(synthetic kernel/spec/adapter, GT-2/3/M1 실행 가능 버전) |
| 2026-09-23 | **Research World Abstraction G6a+G6b 완료** (같은 날, 1290→1296). 사용자가 G3~G5를 GitHub HEAD로 재검증하며 "연구 쪽은 world-generic인데 실행 쪽(`AExecutor.execute`, `ExecutionResult.run`)은 여전히 `CausalWorldSpec`/`CausalRun` 전용 타입"이라는 병목을 지적. G6a: `AExecutor`/`ExecutionResult`/`execute_through_a`를 `ResearchWorldSpec`/`ResearchRun`으로 확장, `RealCausalAExecutor`/`StubAExecutor` 실제 동작은 무변경(`@runtime_checkable` Protocol이 파라미터 타입을 검사하지 않아 안전). G6b: `run_research_exploration`에서 `controls[control_id]` 조회 실패 시 `KeyError`가 그대로 새던 구멍을 `UnknownControlError`로 명시 변환(G1 오류 계약이 실제로는 적용 안 되고 있었음). `InvalidControlValueError`가 "설정 오류" 계층에 있으면서 실제로는 연구 데이터로 처리되는 의미 모순을 발견해 docstring으로 "이 타입만 예외"임을 명시 — 아직 아무 adapter도 실제로 던지지 않는 죽은 코드였음도 확인. `broad_explorer.py` 상단 docstring의 낡은 설명("각 candidate가 CausalWorldSpec으로 컴파일")도 정정. 신규 테스트 6개(`test_deterministic_research_execution_boundary.py`)가 비물리 fake executor/spec으로 Protocol이 실제로 넓어졌음을 증명. G6c(synthetic kernel/spec/adapter/executor)는 여전히 미착수 |
| 2026-09-23 | **Research World Abstraction G6a.1 완료** (같은 날, 1296→1299). 사용자가 G6a를 GitHub HEAD로 재검증하며 정적 타입 계약 결함 두 가지를 지적: (1) `RealCausalAExecutor.execute(spec: CausalWorldSpec)`이 넓어진 `AExecutor.execute(spec: ResearchWorldSpec)` Protocol을 `@runtime_checkable`(메서드명만 검사)로는 통과하지만 실제로는 `CausalWorldSpec`만 받는다는 약속을 어기고 있었음 — 잘못된 world를 넣으면 `run_causal_world`/`spec.digest`가 던지는 임의의 예외(`AttributeError` 등)로 실패해 원인이 불명확했음. (2) `ExecutionResult.run: ResearchRun \| None`이 `digest`만 보장하는데 `PhysicalCausalResearchAdapter._observed_value`가 `result.run.checkpoints`(`CausalRun` 전용 필드)를 검사 없이 읽고 있었음. 고침: `RealCausalAExecutor.execute`가 `isinstance(spec, CausalWorldSpec)`을 `try/except` **밖**에서 먼저 검사해 `WorldCompatibilityError`로 즉시 거부(물리 실행 실패와 wiring 실수를 같은 경로로 섞지 않기 위해 — `ExecutionResult(status="failed")`로 둔갑시키면 안 됨). `PhysicalCausalResearchAdapter._observed_value`도 `isinstance(result.run, CausalRun)` 검사 추가. 부수 정리: `InvalidControlValueError`가 `ResearchWorldError`(설정 오류) 계층에 있으면서 실제로는 연구 데이터로 처리되던 모순을 이번엔 문서가 아니라 **타입 계층 자체를 고쳐서** 해결 — `ResearchWorldError`가 아니라 `ValueError`를 직접 상속하도록 재설계, `broad_explorer.py`의 `except (InvalidControlValueError, ValueError, TypeError)`가 `except (ValueError, TypeError)`로 단순화됨(이름을 몰라도 자동으로 잡힘). 신규 테스트 2개로 `RealCausalAExecutor`/`PhysicalCausalResearchAdapter`가 실제로 잘못된 타입을 거부함을 확인, 기존 `test_error_hierarchy`는 새 계층에 맞게 둘로 분리. G6c(synthetic kernel/spec/adapter/executor)는 여전히 미착수 — 이제 실행 경계가 "넓게 약속하고 정확히 검사"하는 상태가 됐으니 다음 세션에서 synthetic executor/adapter를 붙이면 동일한 호환성 검사 패턴을 그대로 재사용 가능 |
| 2026-09-23 | **Research World Abstraction G6c-1~3 완료** (같은 날, 1299→1346). 사용자가 확인한 대로 `PredictionSeal.predictions_by_hypothesis: Mapping[str, tuple[object, ...]]`가 이미 임의 prediction 객체를 받으므로 `CausalExperimentArm`/`CausalPrediction` 일반화 없이 바로 synthetic world 도입 가능 — G6c-1~4 순서로 진행. **불변식 두 가지를 처음부터 강제**: (1) `engine/deterministic/synthetic_*.py`는 `ground_truth/`의 `step()`을 import하지 않는 독립 구현(양방향 AST leakage 테스트로 고정) — 문제지와 답안지가 같은 코드를 공유하면 독립 검증 의미가 무너지기 때문. (2) 변수명/world_id/control_id에 `direct`/`conditional`/`mediator`/`source_active`/`mediator_active`/`gate_enabled` 같은 정답 힌트를 절대 노출하지 않음(`x1`/`x2`/`x3`, `WORLD-S01`, `CTRL-X1`만 사용) — B가 실험으로 알아내야지 변수명으로 맞히면 오픈북 시험이 되므로. 이 규칙을 코드 주석이 아니라 **B-facing 데이터**(spec의 `canonical()`, control 필드)만 검사하는 테스트로 고정 — 처음엔 파일 텍스트 전체를 검사해 자기 설명 docstring까지 오탐되는 실수를 발견·수정. **G6c-1** (`synthetic_spec.py`): `SyntheticWorldSpec`/`SyntheticClamp`/`SyntheticCheckpoint`/`SyntheticRun`, `world_id/rule_id/variables/initial_values/clamps/public_controls/public_observables/ticks`. `rule_id`가 어떤 hidden rule이 이 world를 지배하는지 선택하지만 B에게는 노출 안 됨. **G6c-2** (`synthetic_kernel.py`/`synthetic_executor.py`): 독립 구현 3종 — `RULE-S01`(`x3:=x1`), `RULE-S02`(`x3:=x1 AND x2`), `RULE-S03`(통상 `x2:=x1, x3:=x2`, clamp로 x2 독립 개입 가능 — clamp가 매 tick 재적용됨을 별도 테스트로 확인, 안 그러면 mediator 검사가 무의미해짐). `SyntheticAExecutor`가 `RealCausalAExecutor`(G6a.1)와 정확히 같은 철학: 입구에서 `isinstance(spec, SyntheticWorldSpec)` 검사 후 `WorldCompatibilityError`, world 내부 실행 실패는 `ExecutionResult("failed", ...)`로. **G6c-3** (`synthetic_adapter.py`/`research_observable_prediction.py`): `SyntheticResearchAdapter`가 `PhysicalCausalResearchAdapter`와 동일한 5개 메서드 구현, 신규 `ObservablePrediction`(tick+observable_id+expected_value) 하나만 추가 — 기존 5종 물리 prediction은 무변경. `run_research_exploration`(G4~G6a의 generic core)이 synthetic world를 실제로 처리함을 확인(전수검사 sweep 포함) — **정확히는 "generic 알고리즘에 synthetic 특례를 추가하지 않고, 기존 경로의 registry 전달 버그 하나만 수정한 뒤 통과"**(사용자가 "코드 수정 없이"라는 표현을 다음 세션에 정정). 부수 발견: `SweepDimension`이 `bool` 값을 명시적으로 거부해서(`exploration_space.py`) control 값을 `True/False`가 아니라 `0/1/None`으로 설계 변경. **더 중요한 부수 발견**: `broad_explorer.run_research_exploration`이 `register_domain(journal, domain)`을 호출할 때 `axis_registry` 파라미터를 넘기지 않아서, `register_domain`의 기본값(`CAUSAL_AXIS_REGISTRY`)으로 내부 재검증되는 실제 버그 발견 — 물리 A 경로는 우연히 `CAUSAL_AXIS_REGISTRY`에 필요한 axis가 다 있어서 지금까지 증상이 없었음. `register_domain(journal, domain, axis_registry)`로 수정, "커스텀 registry는 통과하지만 `CAUSAL_AXIS_REGISTRY`엔 없는 axis"로 재현하는 회귀 테스트 추가(처음 작성한 테스트는 두 코드 경로를 구분 못 해서 버그가 있어도 통과했음 — fix 적용 전/후로 직접 비교해 진짜로 버그를 잡는지 검증) |
| 2026-09-23 | **Research World Abstraction G6c-3.1 완료** (같은 날, 1346→1354). 사용자가 G6c-1~3을 GitHub HEAD로 재검증하며 blind evaluation 준비에 구멍 4개를 지적, G6c-4(실제 GT-2/3/M1 실행 세계) 전에 먼저 처리: **A. `public_observables` 경계가 실행 후 깨짐** — `initial_observation()`은 `public_observables`만 노출했지만 `SyntheticRun.checkpoints`는 모든 변수를 담고 `evaluate_prediction`이 이름만 알면 비공개 변수도 읽을 수 있었음(B0.7의 "private engine state 몰래 읽기 금지"가 synthetic 쪽에서 재발). `synthetic_kernel.py`의 `run_synthetic_world`가 이제 `public_observables`에 없는 변수를 checkpoint 생성 시점에 필터링 — 어느 tick에서도 비공개 변수가 `SyntheticRun`에 존재하지 않음을 테스트로 고정. **B. `rule_id`가 B-facing spec에 그대로 노출** — `RULE-S01`이라는 이름 자체는 즉시 정답 누출은 아니지만 "이 world가 어떤 내부 프로그램을 쓰는지"를 가리키는 selector가 연구 대상 안에 있는 건 blind 원칙 위반. `SyntheticWorldSpec.rule_id` 필드를 완전히 제거하고, 의미 없는 opaque `world_revision`(`R-7F93C2` 등)으로 교체 — `digest`에 포함되므로 숨은 규칙이 바뀌면 반드시 revision도 바뀌어야 재현성이 깨지지 않음(재현성 보장이 목적, 정답 힌트 아님). 신규 `synthetic_runtime.py`: `(world_id, world_revision) → rule` private registry, `SyntheticResearchAdapter`는 이 registry를 전혀 import하지 않고(해석만 담당) `SyntheticAExecutor`만 참조(실행 담당) — 책임 분리를 코드 구조로 강제. **C. 미등록 `rule_id`가 `ExecutionResult(status="failed")`로 둔갑** — 이전엔 rule 조회가 `run_synthetic_world` 내부, 즉 executor의 `try` 안에 있어서 "world 자체가 실험 중 실패"와 "spec이 애초에 잘못 구성됨"이 구분 안 됐음(G6a.1에서 분리했던 wiring-error/research-data 경계가 재붕괴). `synthetic_runtime.resolve_rule` 호출을 `SyntheticAExecutor.execute`의 `try` **밖**으로 이동, 미등록 world/revision은 `WorldCompatibilityError` 즉시 전파. **D. `SyntheticControlDefinition.variable_id`가 `public_controls` 소속인지 사전 미검증** — 잘못된 control을 넣으면 `SyntheticWorldSpec.__post_init__`의 `ValueError`까지 가서 `broad_explorer`가 `CandidateCompilationFailure`로 삼킬 수 있었음(후보가 아니라 wiring이 잘못된 것인데). `apply_control`에 `control.variable_id in synthetic_spec.public_controls` 사전 검사 추가, 위반 시 `WorldCompatibilityError`. 4가지 모두 신규 테스트로 고정(A: 어느 tick도 비공개 변수 없음, B: digest가 revision에 따라 바뀜, C: 미등록 조합이 raise, D: 잘못된 control이 raise). 부수 지적: GT-M1의 `step()`은 한 호출에서 A→B→C가 다 반영되지만 `RULE-S03`은 전파에 2 tick이 필요 — G6c-4에서 tick 값 자체가 아니라 **인과 구조**(A가 B를 바꾸는가, B 독립 개입이 C를 바꾸는가, B 고정 시 A→C 효과가 사라지는가)로 비교해야 함을 다음 단계 설계 원칙으로 기록 |
| 2026-09-23 | **Research World Abstraction G6c-3.2 완료** (같은 날, 1354→1358). 사용자가 G6c-3.1을 재검증하며 남은 구멍 두 개를 지적, G6c-4 전에 마무리: **(1) `public_observables`의 privacy 범위가 spec 레벨까지는 아님** — `variables`/`initial_values`에는 비공개 변수(`x2` 등)도 존재·초기값이 그대로 남아있어 "값은 숨기지만 존재는 공개"인 모델. 이게 의도인지(완전 비공개는 GT-2/3/M1엔 불필요 — mediator/gate 변수는 B가 직접 조작·관측해야 구조를 알아낼 수 있으므로 애초에 public이어야 함) 확인 후, `synthetic_spec.py` 모듈 docstring에 **threat model을 명문화**: blindness는 B-facing API/데이터 기준이고 B는 저장소 소스·`synthetic_runtime.py`·`ground_truth/`에 접근 불가하다는 전제, 그리고 "존재는 공개, 값만 비공개"가 GT-2/3/M1에 필요한 전부라는 근거를 기록. 이 모델을 실제로 검증하는 테스트 추가(`x2`가 `canonical()`엔 있지만 `initial_observation`엔 tick 0부터 없음을 동시에 확인). **(2, 더 중요) `world_revision`의 재현성이 자동 강제가 아니었음** — `RULE_S01` 등의 실제 동작을 바꾸고 revision을 안 바꾸면 아무도 못 잡는 상태였음(기존 테스트는 "revision이 다르면 digest가 다르다"만 증명, "규칙이 바뀌면 revision도 반드시 바뀐다"는 별개 주장이라 미검증). `synthetic_runtime.py`에 `_SEALED_FINGERPRINTS`(각 binding의 규칙 함수 **소스 텍스트** sha256, 진리표 해시 금지 — 진리표를 해시하면 B가 가능한 조합을 전수 생성해 대조하는 오라클이 됨) 추가, 모듈 import 시점에 `_verify_sealed_fingerprints()`로 자동 검사 — 규칙이 조용히 바뀌면 모듈 자체가 import 실패. 실제로 `RULE_S01` 동작을 바꿔서 즉시 실패함을 수동 확인 후 값을 정식 커밋. 신규 테스트 3개(현재 상태가 sealed와 일치함을 명시적으로 assert, 변조 시뮬레이션이 mismatch를 잡아냄을 확인, 진리표가 같아도 소스가 다르면 fingerprint가 다름을 확인). 전체 테스트 1358개 통과 |
| 2026-09-23 | **Research World Abstraction G6c-3.3 완료** (같은 날, 1358→1361). 사용자가 G6c-3.2를 재검증하며 남은 문제 네 가지 지적, G6c-4 전에 마무리: **(1, 가장 중요) `SyntheticResearchAdapter.initial_observation`의 `state_digest`가 실제로는 `spec.digest` 그대로였음** — `spec.digest`엔 `world_revision`·`clamps`·`public_controls`·`public_observables`·`ticks`·**비공개 변수의 `initial_values`까지** 다 들어가므로, boolean 세계처럼 상태공간이 작으면 B가 digest 변화만 보고 private 값에 대한 간접 정보를 얻는 side channel이 될 수 있었음. `state_digest`를 `SyntheticCheckpoint(0, 공개 observables만).digest`로 교체해 공개 tick-0 상태만 해시하도록 수정 — "같은 공개 상태, 다른 spec 설정(특히 비공개 변수 값)"이면 `state_digest`가 반드시 같아야 함을 테스트로 고정, fix 이전 코드로는 실제 실패함을 확인. **(2) fingerprint 용어 정정** — "semantic fingerprint"가 아니라 정확히는 `inspect.getsource` 기반 **sealed source/implementation fingerprint**(진리표가 같아도 소스 표현이 다르면 값이 달라짐, 이건 의도된 보수적 설계). 이 구분과 한계(사람이 규칙도 바꾸고 fingerprint도 새로 계산해 넣으면 여전히 통과 — revision 변경을 수학적으로 강제하진 못하고 "실수로 규칙만 바꾸는" drift만 잡는 개발 계약임, HMAC·외부 immutable manifest 같은 건 의도적으로 범위 밖)를 `synthetic_runtime.py` 모듈 docstring에 명시. **(3) 변조 테스트가 verifier 로직을 재구현하고 있었음** — 기존 테스트가 `_verify_sealed_fingerprints()`를 호출하지 않고 그 비교 로직을 테스트 안에서 다시 작성해서, 실제 verifier가 나중에 no-op으로 망가져도 안 잡힐 위험이 있었음. `_verify_sealed_fingerprints()`를 파라미터화된 `verify_bindings(bindings, fingerprints)`로 분리해 production은 `verify_bindings(_BINDINGS, _SEALED_FINGERPRINTS)`를 호출하고, 테스트는 변조된 bindings를 넣어 실제 함수를 직접 호출하도록 재작성. **(4) 낡은 문서 2곳 정정** — `SyntheticCheckpoint` docstring이 아직 "every variable's value"라고 돼 있던 걸 "public_observables만"으로, `test_deterministic_synthetic_adapter.py` 상단이 generic core "zero changes"라고 적혀 있던 걸 "`register_domain`에 `axis_registry` 전달 버그 1줄만 수정"으로 정정. 신규 테스트 3개(state_digest가 spec.digest와 다름, 비공개 변수 값이 달라도 state_digest 불변, verify_bindings 정상 케이스 통과) + 기존 tamper 테스트 1개 재작성(verifier 로직 재구현 대신 `verify_bindings`를 실제 호출하도록 강화). 전체 테스트 1361개 통과. 다음은 G6c-4(WORLD-S01/S02/S03 JSON fixture + `ground_truth/`와 인과 구조 레벨 비교 — tick 값이 아니라 A가 B를 바꾸는가/B 독립 개입이 C를 바꾸는가/B 고정 시 A→C 효과 소멸 여부로 비교) |
