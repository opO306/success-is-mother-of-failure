# 현재 상태

**최종 갱신:** 2026-09-24
**검증:** 전체 테스트 1830개 로컬 통과 (B0.7 완료 시점 실측 1228개 — 이 문서의 옛 "→1046" 표기는 B0.7 커밋이 갱신하지 않고 지나간 낡은 숫자였음, 2026-09-23 확인). GitHub Actions 독립 재실행 기록 없음 — 로컬 실행 결과임을 구분해 기록
**Git:** 2026-09-21 초기화. 이전 상태는 `D:\KiroCrewTraceVault\success-is-mother-of-failure\project-snapshots\20260921_090715_pre_git_init\` 에 봉인

이 문서는 작업이 진행될 때마다 갱신한다. 낡았다고 판단되면 먼저 고치고 작업한다.

---

## 한 줄 요약

결정론 A 물리 기반과 B 관찰 도구는 작동하지만, **진짜 학습형 B도 없고 A의 화학도 아직 없다.**
생명·복사·진화의 새 증거는 나오지 않았다.

---

## 프로젝트 구조 — A / B / L (2026-09-24 설계자 승인)

```
A = 세계 (물리·화학·공간·시간·에너지)
├── L = 생명 계통 (Living Lineage) — A **안**의 주민. 따로 만드는 것이 아니라 A의 물리에서 생겨야 한다
│     물질 → 결합 → 구획 → 촉매 → 지속 반응망 → 자기 유지 → 부분 복제 → 변이 전달 → 계보 → (기억? 학습? 지능?)
└── B = 연구자 (Researcher) — A **밖**. 관측·가설·실험·검증. A에는 선언된 탐침으로만 (헌법 제25조)
```

- **두 트랙.** 연구 트랙(B가 A를 이해·검증·확장)과 발생 트랙(A → 생명 후보 → 계보 → ?). B가 A의 빈틈을
  찾을수록 L이 사는 세계가 덜 가짜가 된다.
- **L에는 목표를 넣지 않는다.** 예측 오차·호기심·생존·번식 같은 동기를 설계해 넣으면 헌법 제1·9조 위반.
  학습이 생긴다면 물리 현상으로 생기고 자연선택이 우연히 남긴 것이어야 한다(제13조).
- **B는 설계 대상이다.** 현재 B(규칙 기반, "과학자의 절차를 사람이 코드로 적은 것")는 **B-classic** —
  최종형이 아니라 기준선·비교군. 학습형 연구자(가칭 B-origin, 예측 오차로 행동하는 외부 학습자)는 별도
  후보이며 **L과 다르다**(세계 밖, 동기를 설계해 넣어도 됨).
- **발생 트랙의 현재 병목은 A다.** 사슬 최장 3, 촉매·주형 없음, 물리가 particle_id에 의존. L 설계보다
  A 물리의 천장을 여는 것이 먼저.

**기존 자산의 쓰임**

| 자산 | 처리 |
|---|---|
| 결정론 A 물리·결합·구조 | 발생 트랙의 직접 기반 |
| `engine/living/` (경계·익명 신호·수용체 곡선·이름 없는 행동) | **동결 — 수정 금지.** 후기 단계(계보 이후)에 아이디어만 새 코드로 옮김. LUCA 이전 출발점으로는 너무 고수준(organism·genome·controller를 전제) |
| `EVOLVABLE_LANGUAGE_PLAN.md`, `docs/legacy-society-brain/EVOLVABLE_COMPUTATION_SUBSTRATE.md`, `EMERGENT_REPRODUCTIVE_MODES.md` | L 계통의 상위 설계로 재사용(고수준 명령 금지, 기억 = 남는 물질 구조, 번식 방식은 결과로 관찰) |
| 확률 세계 분할·융합(768 세계·시간, 독립 후손 0) | **생명 증거 아님.** 전구 현상 데이터 |
| 옛 A/B/C/D 뇌, 고정 Controller | 비교군·실험 자료로만 보존 |
| B-classic (G0~G11, 문법 v3 동결) | 계속 발전, 기준선 |

---

### 번호 체계와 현재 판 (2026-09-24 정리)

번호마다 트랙 접두사를 붙인다. 예전 문서의 `G7`, `Stage B`, `기하 단계 5`는 아래로 읽는다.

| 접두사 | 뜻 | 예전 표기 |
|---|---|---|
| `A-V4.A`~ | A 물리 causal v4의 단계 | causal v4 Stage A/B/C |
| `A-V4.GEO` | A 접촉 기하·구조 생성/성장 | 기하 단계 5~7, 옛 "Stage D" |
| `B-G0`~ | B-classic 연구선 | G0~G12, B0.x |
| `L-P0`~ | L 발생 관찰 | (없음) |

| 항목 | 내용 | 상태 |
|---|---|---|
| A-V4.A | 수정된 충돌 의미 | 완료 |
| A-V4.B | `StructureState` — 구조가 자기 운동 소유, 카디널 이동 포함 | 완료 |
| A-V4.C | 재명명·순서 불변성 | 현재 v4 경로에서 성립 |
| A-V4.GEO | 접촉 그래프 → 구조가 **생기고 자람** | 설계자 검토: G0(규모 분리)·G4 승인, G1 재설계, G2·G3 기각(미정의 물리는 기록 + 실행 중단). **선행 v1A 공간 표현 v2 초안 2판(물질 중심: 요소·구조·계산 묶음, 칸 없음, 새 형식 v5)** `docs/current/A_MICRO_SPATIAL_REPRESENTATION_V2.md` — 설계자 검토: S0·S1·S8·S9 승인, S7 기각, S3·S5·S6 보류. 운동학·시간 `A_MICRO_V5_KINEMATICS_TIME_V1.md` **K1·K2 승인, K3 v5 한정 승인**. 실행 구조 `A_EXECUTION_ARCHITECTURE_V1.md` **X1~X5 승인**(RULES 반영, 기준 실행기 영구 유지). S4 에너지 `A_MICRO_V5_ENERGY_V1.md` **승인**(구조 내부 에너지, 병합 보존식 `U' = ΣUᵢ + ΣKᵢ − K'`, 좌표계 무관 결합 문턱, 각운동량 잔차 감사). **다음: 기준 실행기 구현 계획** `A_MICRO_V5_REFERENCE_EXECUTOR_PLAN_V1.md` 검토 대기 → 승인 뒤 코드 |
| B-G11 | 탐침 문법 v3 | 완료 |
| B-FREEZE | 문법 v3 + 탐침 계약 지문 동결 | 완료 |
| B-G12 | 처음 보는 세계에서 블라인드 시험 | 세계(수화광맥, sol 설계) 받음 → 동결 탐침 계약과 형식이 달라 **동결 B는 들어갈 수 없음**. 세계는 신체 계약에 맞춰 수정 필요(계약 문서 9.2) |
| B-BODY | 인간 현실재현 가능 신체 계약 v1 (헌법 제26조) | **문서 확정·동결** (2026-09-24). 구현은 A-V4.GEO 뒤 |
| L-P0 | 생명 이전 발생 관찰 | A에 막힘. 코드 프로젝트 아님 — A에서 무언가 생기면 붙이는 관찰상의 계보 이름 |

**진행 순서 (2026-09-24 갱신, 설계자 Q6):** 동시에 한 트랙만 개발한다. 신체 계약 확정·동결(완료) →
**B-classic 보존**(수정 없음, 격자 탐침 기준선) → **A-V4.GEO**(신체가 요구하는 표면·가림·거리·접촉·크기·도달 범위의 물리 기반) →
신체 구현 → 신체를 받아들이는 세계로 B 시험 → 촉매·주형 → L 가능성.

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
| Stage B | `StructureState` — 구조가 운동량을 소유 | **완료 (2026-09-24)** — 단, v4 안에서 구조가 생기는 경로는 아직 없음 |
| Stage C | 재명명·순서 불변성 | **현재 v4 경로에서 테스트로 성립** (2026-09-24). 성장·접촉 경로가 생기면 같은 테스트를 다시 통과해야 함 |
| ~~Stage D~~ | ~~구조 이동~~ — **재정의 (2026-09-24):** 카디널 구조 이동은 Stage B에 이미 들어갔다. 남은 것은 단순 이동이 아니라 접촉·구조 생성/성장·구조–입자 상호작용이며, 이것을 `A-V4.GEO`로 부른다 | 다음 A 작업 |

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

### (마) Ground-Truth를 B가 실제로 연구 가능하게 만들기 *(2026-09-23 착수, G0~G7.4 + G8 + G9 + G10 + G11 완료)*

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
| 2026-09-23 | **Research World Abstraction G6c-3.3 완료** (같은 날, 1358→1361). 사용자가 G6c-3.2를 재검증하며 남은 문제 네 가지 지적, G6c-4 전에 마무리: **(1, 가장 중요) `SyntheticResearchAdapter.initial_observation`의 `state_digest`가 실제로는 `spec.digest` 그대로였음** — `spec.digest`엔 `world_revision`·`clamps`·`public_controls`·`public_observables`·`ticks`·**비공개 변수의 `initial_values`까지** 다 들어가므로, boolean 세계처럼 상태공간이 작으면 B가 digest 변화만 보고 private 값에 대한 간접 정보를 얻는 side channel이 될 수 있었음. `state_digest`를 `SyntheticCheckpoint(0, 공개 observables만).digest`로 교체해 공개 tick-0 상태만 해시하도록 수정 — "같은 공개 상태, 다른 spec 설정(특히 비공개 변수 값)"이면 `state_digest`가 반드시 같아야 함을 테스트로 고정, fix 이전 코드로는 실제 실패함을 확인. **(2) fingerprint 용어 정정** — "semantic fingerprint"가 아니라 정확히는 `inspect.getsource` 기반 **sealed source/implementation fingerprint**(진리표가 같아도 소스 표현이 다르면 값이 달라짐, 이건 의도된 보수적 설계). 이 구분과 한계(사람이 규칙도 바꾸고 fingerprint도 새로 계산해 넣으면 여전히 통과 — revision 변경을 수학적으로 강제하진 못하고 "실수로 규칙만 바꾸는" drift만 잡는 개발 계약임, HMAC·외부 immutable manifest 같은 건 의도적으로 범위 밖)를 `synthetic_runtime.py` 모듈 docstring에 명시. **(3) 변조 테스트가 verifier 로직을 재구현하고 있었음** — 기존 테스트가 `_verify_sealed_fingerprints()`를 호출하지 않고 그 비교 로직을 테스트 안에서 다시 작성해서, 실제 verifier가 나중에 no-op으로 망가져도 안 잡힐 위험이 있었음. `_verify_sealed_fingerprints()`를 파라미터화된 `verify_bindings(bindings, fingerprints)`로 분리해 production은 `verify_bindings(_BINDINGS, _SEALED_FINGERPRINTS)`를 호출하고, 테스트는 변조된 bindings를 넣어 실제 함수를 직접 호출하도록 재작성. **(4) 낡은 문서 2곳 정정** — `SyntheticCheckpoint` docstring이 아직 "every variable's value"라고 돼 있던 걸 "public_observables만"으로, `test_deterministic_synthetic_adapter.py` 상단이 generic core "zero changes"라고 적혀 있던 걸 "`register_domain`에 `axis_registry` 전달 버그 1줄만 수정"으로 정정. 신규 테스트 3개(state_digest가 spec.digest와 다름, 비공개 변수 값이 달라도 state_digest 불변, verify_bindings 정상 케이스 통과) + 기존 tamper 테스트 1개 재작성(verifier 로직 재구현 대신 `verify_bindings`를 실제 호출하도록 강화). 전체 테스트 1361개 통과 |
| 2026-09-23 | **문서 정정** — 커밋 메시지가 G6c-3.3을 "4 new tests"라고 표기했으나 실제로는 신규 3개 + 기존 tamper 테스트 1개 재작성이었음(사용자가 GitHub HEAD 재검증 중 지적). `CURRENT_STATE.md`의 해당 항목 표현만 정정, 기능 변경 없음 |
| 2026-09-23 | **Research World Abstraction G6c-4 완료** (같은 날, 1361→1371). WORLD-S01/S02/S03이 `ground_truth/`(GT-2/GT-3/GT-M1)와 실제로 같은 인과 구조를 갖는지 처음으로 교차 검증 — 지금까지는 두 쪽 다 "자기 자신에 대해서만" 옳음을 테스트했을 뿐, 서로 비교한 적이 없었다(한쪽이 조용히 틀려도 기존 테스트는 전부 통과했을 상황). 신규 `tests/test_ground_truth_synthetic_structural_parity.py`(10개): 매핑은 이름이 아니라 이 테스트 파일이 고정 — `WORLD-S01 <-> GT-2`, `WORLD-S02 <-> GT-3`, `WORLD-S03 <-> GT-M1`. 비교 대상은 tick 값이 아니라 각 `ground_truth/` auditor가 이미 쓰는 개입 성질 그 자체: **S01** x1 변화가 x3를 바꾸고(변수는 x1/x3 둘뿐, 매개 변수 없음). **S02** x2=OFF면 x1을 바꿔도 x3 불변, x2=ON이면 x1 변화가 x3를 바꿈, x1은 x2 자체를 절대 안 바꿈(gate이지 mediator 경로가 아님을 확인). **S03** (1) x2 FREE 상태에서 x1만 바꾸면 tick 1의 x2가 바뀜, (2) x1 고정·x2를 clamp로 직접 개입하면 tick 2의 x3가 바뀜, (3) x2를 OFF/ON 어느 값으로 고정하든 x1을 바꿔도 tick 2의 x3는 불변(mediator 차단 검사, GT-M1의 `forbidden_edges=(("source_active","outcome_active"),)`와 동일한 성질). S03은 GT-M1의 단일 `step()`과 달리 2 tick에 걸쳐 구현되므로(`run_synthetic_world`엔 "매개변수가 갱신된 후 즉시 읽는" 단일-tick 원시 연산이 없음) 의도적으로 tick 수/실행 형태는 비교 대상에서 제외 — 세 가지 개입 성질만 비교. 각 world의 `ground_truth/` 답안지가 여전히 VALID임을 먼저 확인하는 가드 테스트 3개도 포함(깨진 답안지와 비교하는 걸 방지). **실제로 구조 불일치를 잡는지 검증**: `RULE_S02`를 `AND`→`OR`로 임시 변조(sealed fingerprint도 같이 우회)한 뒤 재실행하니 "gate off/on" 두 테스트가 정확히 그 이유로 실패함을 확인 후 원상복구 — 다른 6개 테스트는 이 변조로 안 깨져서, 새 테스트가 실제로 구조를 검사하지 절차만 검사하는 게 아님을 확인. 첫 실행에서 10개 전부 통과 — WORLD-S01/S02/S03과 GT-2/GT-3/GT-M1이 실제로 같은 인과 구조를 독립적으로 구현했음이 처음으로 봉인됨. 전체 테스트 1371개 통과. 이제부터 B가 이 세 world에서 구조를 못 찾으면 "B의 추론 실패"라고 말할 수 있음(이전엔 "시험지 인쇄 상태 미확인" 상태였음) |
| 2026-09-23 | **G7 심화 설계, 그리고 그 전에 G6d 신설 필요성 발견** (같은 날). 사용자가 G7(Blind Causal Discovery Evaluation) 심화 설계를 작성 — Blind Wall, G7.0(Oracle Expressibility)~G7.7(9-session 인증), `BlindWorldDescriptor`/`BlindTranslationManifest`/`FinalDiscoverySeal`/`GroundTruthSignature`/`BlindEvaluationReport` 등 개념, 13종 verdict(HARNESS_INVALID/BLINDNESS_VIOLATION/.../PASS)와 우선순위, 3-permutation alias robustness(같은 world를 seed 0/1/2로 opaque 이름을 다르게 매겨 3번씩, 9 session 총합) 등을 확정. 구현 착수 전 기존 코드 조사 결과, **`broad_explorer.py`/`exploration_space.py`에 "B가 스스로 실험을 설계"하는 코드가 전혀 없음이 발견됨** — `SweepDimension`/`ExplorationPlan`은 항상 호출자가 손으로 만들고, `run_research_exploration`은 주어진 plan의 Cartesian product를 기계적으로 실행할 뿐. 즉 G7 원안의 "발견(Discovery)" 항목이 전제하는 능력이 현재 시스템에 없음. 사용자 판단: G7 범위를 축소하지 않고, 그 대신 G7 앞에 **G6d(Autonomous Experiment Design)**를 신설해 이 공백을 먼저 메운다 — "G6c는 시험 세계가 정답과 같은가, G6d는 B가 스스로 좋은 질문을 만들 수 있는가, G7은 답을 모르는 상태에서 그 질문으로 정답을 찾아내는가"로 세 Gate의 책임을 분리. 이어서 G6d 조사 결과, 필요한 조립 부품이 이미 정확히 맞는 모양으로 존재함을 확인: `CandidatePredictionProvider.predictions_for(candidate, spec) -> Mapping[hypothesis_id, predictions]`가 애초부터 "후보 → 가설별 예측" 구조였고, `ObservablePrediction`은 `==`로 바로 비교 가능 — 새 causal solver 없이 이 둘을 조립하는 얇은 오케스트레이션 층 하나면 충분하다는 결론. 초안 검토에서 사용자가 4가지 수정: (1) 스코어링을 "distinct prediction 종류 수 - 1"에서 **가설 쌍(pair) 중 예측이 갈리는 쌍의 개수**(`disagreement_pair_count`)로 변경 — 가설 4개가 3-1로 갈리든 2-2로 갈리든 distinct 값은 둘 다 2종이라 구분 못 하지만, pair count는 3-1이 3쌍, 2-2가 4쌍이라 더 정보량이 많은 실험을 자동으로 우대함. (2) `select_next_experiment`가 `disagreement_pair_count <= 0`인 후보를 절대 선택하지 않도록 명시 — 안 그러면 "구별할 실험이 없음"인데 의미 없는 실험을 계속 실행해 `EXPLORATION_FAILURE`의 의미가 흐려짐. (3) G7의 blindness 검증을 AST import 검사 하나로 끝내지 않고 **4중 경계**로 강화 — type boundary(B-facing 함수가 `BlindTranslationManifest`/`GroundTruthSignature`/real spec을 인자로조차 받을 수 없음) + dependency AST(B-side 전체 closure에서 `ground_truth.*`/`synthetic_runtime` import 금지) + data-leakage 검사(`canonical()`과 journal에 `WORLD-S0x`/`GT-x`/`real_world_id`/fingerprint/`axis.synthetic.*` 같은 문자열이 실제로 안 나타나는지) + runtime tripwire(evaluator 전용 접근을 monkeypatch해서 B 세션 전체를 돌려 한 번이라도 건드리면 즉시 테스트 실패). (4) 구현 순서를 "G6d 완결 → 전체 회귀 → 커밋 → CURRENT_STATE 갱신 → 그 다음에야 G7.0 착수"로 명시 확정, G6d/G7 병렬 진행 금지 — Gate를 잘게 봉인해온 이 프로젝트의 관행을 유지해 실패 원인이 여러 Gate에 걸쳐 뒤섞이지 않게 하기 위함 |
| 2026-09-23 | **Research World Abstraction G6d 완료** (같은 날, 1371→1380). 신규 `engine/deterministic/experiment_designer.py`(이번 Gate의 유일한 신규 프로덕션 파일) — `rank_discriminating_candidates(candidates, compiled_specs, prediction_provider)`가 각 후보를 `disagreement_pair_count`(살아있는 가설 쌍 중 예측이 갈리는 쌍의 개수, pairwise `==` 비교로 계산 — hashable 의존 없음)로 채점해 내림차순(동점은 candidate_id 오름차순)으로 정렬, `select_next_experiment(ranked, already_executed)`가 그중 아직 실행 안 했고 `disagreement_pair_count > 0`인 최상위 후보를 고름(0점 후보는 마지막 남은 선택지여도 절대 반환 안 함). 컴파일 실패한 후보(`compiled_specs`에 없음)는 조용히 스킵 — `broad_explorer.py`의 "컴파일 안 된 건 연구 데이터가 아니다" 원칙 재사용. 새 causal solver 없음: `CandidatePredictionProvider`가 이미 "후보→가설별 예측" 구조를 리턴하고 있었으므로 새 타입 없이 그 반환값을 그대로 소비. `research_journal.EVENT_TYPES`에 `"experiment_candidate_ranked"` 1개 추가(G7에서 journal replay로 판별 증거 유무를 감사할 수 있도록). 신규 테스트 9개(`tests/test_deterministic_experiment_designer.py`) — WORLD-S02 예시로 "H-always(x1이 항상 x3 결정)" vs "H-gated(x2가 x1 효과를 게이트)" 두 경쟁 가설을 손으로 만들어 gate 근처 후보가 실제로 최고 점수를 받는지 확인, 4-가설 3-1/2-2 분할 랭킹 순서 확인, 컴파일 실패 후보 스킵, 0점 후보 절대 미선택 확인, AST leakage 테스트(ground_truth/synthetic_runtime 미참조) 포함. **실제로 사용자가 지적한 회귀를 잡는지 검증**: `_disagreement_pair_count`를 사용자가 명시적으로 기각한 구 방식(distinct 값 수 - 1)으로 임시 되돌려 재실행하니 3-1 vs 2-2 랭킹 순서 테스트가 정확히 그 이유로 실패함을 확인 후 원상복구. 첫 실행에서 9개 전부 통과. 전체 테스트 1380개 통과, 로컬 실행. G7의 4중 blindness 경계(type boundary/dependency AST/data-leakage/runtime tripwire)는 아직 미구현 — 다음은 G7.0(Oracle Expressibility)부터 순차 착수 |
| 2026-09-23 | **Research World Abstraction G7.0 완료** (같은 날, 1380→1398). B를 blind로 시험하기 전에, 채점기(hypothesis 언어 + evaluator) 자체가 GT-2/GT-3/GT-M1의 정답 구조를 표현·판별할 수 있는지 먼저 검증 — 아직 blind session/alias/permutation/`ExperimentDesigner` 어느 것도 연결 안 함, 순수하게 "채점 규칙이 유효한가"만 확인. 신규 `engine/deterministic/ground_truth_signature.py`: `ConditionedPrediction(control_values, prediction)`이 `CausalHypothesis.predictions`엔 없던 "이 개입 하에서 이 값을 예측한다"는 맥락을 부여(기존 `CausalHypothesis.predictions`는 정적 tuple이라 임의 개입에 대한 예측을 계산하는 메서드가 없었음 — S01/S02/S03의 개입 공간이 2~4개로 작아서, 가설이 자신이 주장하는 모든 개입 조합에 대해 미리 예측을 나열하는 방식으로 충분함). `StructuralObligation.check(CausalHypothesisSet) -> bool`이 가설의 `hypothesis_id`/라벨을 절대 안 읽고, `ConditionedPrediction`들로부터 실제 불리언 관계(예: "x2=ON일 때만 x1 변화가 x3를 바꾼다")를 계산 — `if hypothesis.kind == "conditional": PASS` 같은 라벨 검사 설계를 명시적으로 금지한 사용자 지시 반영. `GroundTruthSignature`는 G6c-4에서 이미 봉인한 세 가지 개입 성질과 정확히 같은 의미의 obligation 7개로 구성(GT-2: 1개, GT-3: 3개, GT-M1: 3개) — parity 테스트로 G7.0이 G6c-4에서 조용히 벗어나지 않도록 고정. 신규 테스트 18개(`tests/test_ground_truth_signature_oracle.py`): 각 world 정답 이론 PASS, 대표 오답 FAIL(과소모델 — S01 constant/S02 unconditional-direct/S03 no-mediator-effect, 과잉모델 — S02 false x1→x2 edge/S03 false direct x1→x3 edge), 7개 obligation 각각을 정확히 하나만 깨는 격리 테스트(다른 obligation은 여전히 PASS임을 같이 확인), 커버리지 없는 조합은 절대 기본 PASS 처리 안 됨 확인. **실제로 채점기가 라벨이 아니라 구조를 검사하는지 검증**: 7개 obligation 함수 각각을 `return True`로 스텁 처리하는 스크립트를 순차 실행해, 7개 전부 최소 하나의 테스트에서 잡히는지 확인(대부분 전용 격리 테스트에서 잡힘) — 스텁 우회가 하나도 안 뚫림. 이 과정에서 초안 격리 테스트 하나(`x2_alone_changes_x3`)가 의도와 달리 다른 obligation까지 같이 깨뜨리는 걸 발견해 수정. 첫 통과 후 전체 테스트 1398개 통과, 로컬 실행. `ground_truth/`나 `synthetic_runtime.py`는 이 Gate에서 한 번도 import 안 됨(AST로 확인 가능 — import 문 자체가 없음), `SyntheticWorldSpec` 실행도 전혀 안 함 |
| 2026-09-23 | **G7.0 representation repair, G7.1 착수 전 필수 정정** (같은 날, 1398개 유지 — 개수 불변, 표현 계층만 교체). 사용자가 G7.0 결과를 재검토하며 핵심 결함 지적: `ConditionedPrediction`을 `ground_truth_signature.py` 내부에 evaluator 전용으로 정의하고, `CausalHypothesis.predictions` tuple의 원소 타입이 런타임에 강제되지 않는다는 이유로 그 안에 집어넣은 것 — 이는 "B의 실제 가설 언어가 정답 구조를 표현할 수 있는가"가 아니라 "evaluator 전용 확장 타입을 쓰면 표현할 수 있는가"를 증명한 것이므로 G7.0의 목적을 우회한 것이었음. 사용자가 짚은 파급 효과: 이 문제를 지금 안 잡으면 G7.5(held-out intervention query)에서 B의 이미 봉인된 최종 가설에게 "이 개입에서 뭘 예측하냐"고 물을 때, 가설 표현 자체에 "이 예측이 어떤 개입 하의 것인지" 표현할 방법이 없어서 답을 만들 수 없는 문제로 반드시 재발. 새 Gate를 추가하지 않고 G7.0 안에서 "representation repair"로 처리: 신규 `engine/deterministic/interventional_prediction.py` — `InterventionalPrediction(control_values, prediction)`을 `ObservablePrediction`과 동일한 지위의 **정식 프로덕션 prediction kind**(6/7번째 kind, `research_observable_prediction.py`의 kind-dispatch 원칙과 동일)로 승격, `canonical()` 보유, ground truth 정보 없음, G7.5에서도 동일 표현 재사용 예정으로 명시. `causal_hypothesis.py`엔 동작 변경 없이 docstring만 갱신해 `InterventionalPrediction`을 정식 허용 kind로 명문화. `ground_truth_signature.py`에서 `ConditionedPrediction`/`conditioned_predictions` 완전 제거, 7개 obligation 로직은 그대로 두고 `InterventionalPrediction`/`interventional_predictions()`만 사용하도록 교체(의미 변경 없음, 표현 계층만 교체). `tests/test_ground_truth_signature_oracle.py`의 18개 테스트를 전부 `InterventionalPrediction`으로 재구성 — 실제 프로덕션 `CausalHypothesis` 인스턴스만 사용, 테스트 전용 타입 없음. **재검증**: 18개 테스트 재실행 전부 통과, 7개 obligation 스텁(`return True`) mutation 스크립트를 다시 돌려 교체 전과 완전히 동일한 결과(7개 전부 최소 하나의 테스트에서 잡힘)를 확인 — 표현 계층 교체가 판정 로직 자체는 하나도 안 바꿨음을 증명. 전체 회귀 1398개 통과(신규 테스트 없음, 정정이므로 개수 불변). "Python이 런타임 타입을 안 막으니 넣는다"는 설계를 정식으로 기각하고, 구조화된 정보는 정식 구조화된 타입(B의 실제 predictions 계약 안)으로 가져와야 한다는 원칙을 재확인 |
| 2026-09-23 | **G7.0 최종 정리 — 정적 타입 계약까지 일치** (같은 날, 1398→1401). 사용자가 직전 repair를 재검토하며 지적: `InterventionalPrediction`을 정식 프로덕션 kind로 승격하고 docstring에 "허용된다"고 적었지만, `CausalHypothesis.predictions`의 실제 타입 힌트는 여전히 `tuple[CausalPrediction, ...]`(물리 A 5종 Union만)이었음 — 런타임은 허용, 문서는 허용한다고 적혀 있는데, 정적 타입 계약만 여전히 좁은 상태. "문서에 합법이라고 써놔도 타입 시스템은 동의 안 한다"는 지적과 함께, 이걸 지금 안 잡으면 나중에 `__post_init__`에 실제 타입 검사가 추가되는 순간 기존 `ObservablePrediction`/`InterventionalPrediction` 보유 가설이 전부 조용히 깨지는 지뢰가 된다는 경고. `causal_hypothesis.py`에 `ResearchPrediction = Union[CausalPrediction, ObservablePrediction, InterventionalPrediction]` 신설 — 기존 물리 전용 `CausalPrediction`은 그대로 닫아둠(넓히면 물리 A 전용 Union 매칭 코드가 절대 못 받을 두 kind까지 처리해야 하므로), `CausalHypothesis.predictions` 필드 타입을 `tuple[ResearchPrediction, ...]`로 변경해 실제 허용 범위와 타입 힌트를 일치시킴. 신규 테스트 3개(`tests/test_deterministic_causal_hypothesis.py`) — 물리 `CausalPrediction`/bare `ObservablePrediction`/`InterventionalPrediction` 세 도메인 모두로 `CausalHypothesis`가 실제 생성됨을 확인. 프로젝트에 mypy/pyright 등 정적 타입 검사 미설정 확인(따라서 런타임 회귀만 적용). 전체 테스트 1398→1401개 통과. 이제 표현(런타임)·문서·정적 타입 계약 세 가지가 전부 일치 — G7.0 완전히 종결. 다음은 G7.1(Blind Boundary — `BlindWorldDescriptor`/`BlindTranslationManifest`, type boundary/dependency AST/data-leakage/runtime tripwire 4중 blindness 경계 구현) |
| 2026-09-23 | **Research World Abstraction G7.1 완료 — Blind Boundary** (같은 날, 1401→1424). 사용자가 범위를 명시적으로 좁혀 착수 승인: 이번 Gate는 정보 차단 경계만 구현하고 9-session 실행/G6d 루프 연결/GT scoring/held-out intervention/`FinalDiscoverySeal`/PASS 판정은 전부 다음으로 미룸. 신규 `engine/deterministic/blind_session.py`(이번 Gate의 유일한 신규 프로덕션 파일): `BlindWorldDescriptor`/`BlindControlDescriptor`/`BlindObservableDescriptor`(B-facing, `real_world_id`/`real_world_revision`/`ground_truth_id`/`rule`/`fingerprint`/`source` 필드가 타입 수준에서 아예 존재하지 않음) 대 `BlindTranslationManifest`(evaluator-only, 실제<->alias 매핑 보유). `make_blind_session(spec, seed)`이 둘 다 보는 유일한 함수이며 **한 객체의 필드로 묶지 않고 독립된 두 값으로 반환** — B-facing 타입 어디에도 manifest를 담는 필드가 없어서 "안 쓰는 것"이 아니라 애초에 "받을 수 없는" 구조. alias는 `sha256(spec.digest:seed:kind:real_name)` 기반 결정론적 생성(같은 spec+seed → 같은 alias, 다른 seed → 다른 순열 — 3-permutation robustness는 G7.6 범위 밖, 여기선 seed 재현성만 보장). 4중 경계를 각각 `tests/test_deterministic_blind_session.py`(23개)로 봉인: (1) type boundary — `dataclasses.fields()`로 금지 필드명이 구조적으로 없음을 확인. (2) dependency AST — `blind_session.py`와 `experiment_designer.py`의 import closure에 `ground_truth`/`synthetic_runtime`(정규화된 이름과 relative-import가 실제로 만드는 bare 이름 `"synthetic_runtime"` 둘 다) 및 wildcard import가 없음을 확인. (3) serialized-data leakage — 실제 `WORLD-S01/S02/S03`/`R-7F93C2` 등 9종 secret 값이 `canonical()`과 시뮬레이션한 journal payload 직렬화 결과에 없음을 확인, 필드 이름이 무죄여도 값이 자백하는 경우(`metadata["note"]="WORLD-S02"`)를 잡는지도 자체 검증. (4) runtime tripwire — 정상 blind path(`_run_minimal_blind_path`: descriptor 읽기, control/observable 나열)는 `translate_control`/`translate_observable`을 monkeypatch로 강제 실패시켜도 통과, 반대로 `translate_control`을 실제로 호출하는 경로는 탐지됨을 모듈 레벨 이름 바인딩으로 정확히 확인. **실제로 결함을 잡는지 3종 mutation으로 검증**(RULES.md 검사기 결함 주입 원칙): (a) `BlindWorldDescriptor`에 `real_world_id` 필드를 임시로 넣어 type boundary 테스트가 잡는지 확인 — 잡음. (b) `blind_session.py`에 `from .synthetic_runtime import resolve_rule`를 실제로 추가해 재실행 — 처음엔 잘못된 `-k` 필터로 해당 테스트를 선택 안 해서 거짓 통과가 날 뻔했으나, 정확한 테스트 ID로 재실행해 실제로 실패함을 확인(디버깅 과정에서 relative import가 `ast.ImportFrom.module`에 점 없는 `"synthetic_runtime"`으로 나타난다는 사실 자체를 발견 — `FORBIDDEN_MODULES`에 그 형태가 누락돼 있던 진짜 결함을 이번 검증 중에 찾아 수정). (c) `BlindWorldDescriptor.canonical()`에 `"WORLD-S02"`를 담은 `debug_note` 필드를 임시로 추가해 serialization leakage 테스트가 잡는지 확인 — 잡음. 세 mutation 모두 원상복구 확인 후 전체 회귀 재실행. 전체 테스트 1401→1424개 통과, 로컬 실행. G7.1은 "B가 정답을 맞혔는가"를 아직 증명 못 하지만 "정답지를 구조적으로 볼 수 없다"는 주장은 이제 코드+테스트로 성립 |
| 2026-09-23 | **G7.1 module-boundary repair** (같은 날, 1424→1427). 사용자가 GitHub에서 실제 커밋(`9b45ea6`)을 직접 대조 확인한 뒤 지적: `BlindTranslationManifest`/`make_blind_session`/`translate_control`/`translate_observable`이 B-facing 타입(`BlindWorldDescriptor` 등)과 같은 `blind_session.py` 파일 안에 있었음 — 객체 그래프 경계(관리자가 두 값을 한 객체로 안 묶음)는 이미 검증됐지만, **모듈 경계**는 안 막혀 있어서 "B가 그 모듈을 import할 수 있는 환경이면 evaluator-only가 물리적으로 분리된 게 아니다"라는 정확한 지적. "안 쓰기로 했으니 안전하다"는 규율(discipline) 기반 경계와 "애초에 그 심볼이 이 파일에 없다"는 구조 기반 경계는 다르다는 지적을 수용, 새 Gate를 만들지 않고 **같은 G7.1 안에서 정정**(사용자가 제안한 정확한 분리안 그대로 채택). `blind_session.py`를 B-facing 전용으로 축소(`BlindWorldDescriptor`/`BlindControlDescriptor`/`BlindObservableDescriptor`만 남김, `dataclass`만 import), 신규 `blind_evaluator.py`(evaluator-only)로 `BlindTranslationManifest`/`make_blind_session`/`translate_control`/`translate_observable`/`ForbiddenBlindAccess` 이전. 의존 방향을 한쪽으로 고정: `blind_evaluator.py`는 `blind_session.py`에서 `BlindWorldDescriptor`를 import하지만 그 역은 금지. `tests/test_deterministic_blind_session.py`에 신규 테스트 3개 추가 — `test_blind_translation_manifest_is_not_defined_in_blind_session_module`(B-facing 모듈에 evaluator 심볼이 `hasattr`로도 없음을 확인), `test_blind_session_does_not_import_blind_evaluator`(이번 정정의 핵심 — B-facing 쪽이 evaluator 모듈을 import 안 하는지 AST로 확인, bare relative-import 형태 `"blind_evaluator"`도 금지 목록에 포함), `test_blind_evaluator_imports_from_blind_session_not_the_reverse`(허용된 방향의 edge가 실제로 존재하는지 확인). 기존 23개 테스트도 import 경로만 두 모듈로 나눠 그대로 재사용(`translate_control`/`translate_observable`의 monkeypatch 대상이 `blind_session.` → `blind_evaluator.`로 이동). **실제로 이번 결함을 재현·검증**: `blind_session.py`에 `from .blind_evaluator import BlindTranslationManifest`를 실제로 추가해 재실행하니 신규 `test_blind_session_does_not_import_blind_evaluator`가 정확히 그 이유로 실패함을 확인 후 원상복구. 전체 테스트 1424→1427개 통과, 로컬 실행. 이제 주장이 "B가 받는 객체에는 정답이 없다"에서 "B가 받는 객체에는 정답이 없고, B-facing 모듈 자체에도 정답을 복원하는 기능이 존재하지 않는다"로 강화됨 — 다만 프로세스/파일시스템 격리까지는 아니므로(같은 Python 프로세스에서 `engine.deterministic.blind_evaluator`를 직접 import하는 것 자체를 막지는 못함) "완전한 샌드박스"라고 주장하면 과장이라는 점은 명시해둠. **사용자가 GitHub에서 `da62d39` 직접 대조 확인 후 승인 — G7.1 최종 완료, 추가 repair 불필요.** 프로세스/OS 샌드박스는 지금 범위 밖(G7의 목표는 "B 연구 경로에 GT 정보가 구조적으로 안 흘러들어감"의 검증이지 보안 인프라가 아님)이라는 것도 사용자가 명시적으로 확인. **G7.2 착수 시 지켜야 할 것**: 지금까지는 `blind_session.py`/`blind_evaluator.py`/`experiment_designer.py` 등 개별 파일을 손으로 짚어 import를 검사했지만, G7.2에서 실제 blind execution wiring(B-side entrypoint)이 생기면 그 wiring이 끌어들이는 전체 transitive dependency closure를 검사해야 함 — entrypoint가 새 모듈을 몇 개 더 import하기 시작하는 순간 "개별 파일 목록을 손으로 검사"하는 지금 방식은 새로 추가된 모듈을 누락하기 쉬움. G7.2의 dependency-boundary 테스트는 entrypoint 하나로부터 재귀적으로 모든 import를 따라가며 `blind_evaluator`/`synthetic_runtime`/`ground_truth` 어디에도 닿지 않는지 확인하는 형태여야 G7.1이 세운 벽이 실행 그래프에서도 유지됨. 다음은 G7.2 |
| 2026-09-23 | **Research World Abstraction G7.2 완료 — Protocol Integrity** (같은 날, 1427→1452). G7.1이 "B가 정답을 못 본다"를 막았다면 G7.2는 "실험 결과를 본 뒤 예측/최종 가설을 고쳐 쓰지 못한다"를 막는 단계 — 사용자가 새 추론 기능을 만들지 말고 기존 `PredictionSeal`/`seal_predictions()`/append-only journal을 그대로 재사용하라고 명시, 4가지 확정 사항(① `experiment_candidate_ids`가 아니라 journal에서 실제로 독립 검증 가능한 `executed_arm_ids` 사용, ② final seal 이후 evaluator는 같은 journal에 안 쓰고 별도 artifact로, ③ seal의 digest/sequence/count는 호출자가 조립하지 않고 `seal_final_discovery()`가 journal에서 직접 계산, ④ G7.2는 PASS/INFERENCE_FAILURE 같은 최종 verdict를 만들지 않고 protocol audit만)을 미리 박아준 상세 설계로 착수. 신규 `engine/deterministic/blind_protocol.py`(이번 Gate의 유일한 신규 프로덕션 파일, `blind_session.py`처럼 B/protocol-side — `blind_evaluator`/`ground_truth`/`synthetic_runtime` import 금지): `FinalDiscoverySeal`(alias_world_id/sealed_at_seq/final_hypothesis_set_digest/journal_terminal_digest/executed_arm_ids/experiment_count/unresolved_hypothesis_ids, real identity 필드 없음)과 `seal_final_discovery(journal, alias_world_id, final_hypothesis_set, unresolved_hypothesis_ids)`(나머지 필드 전부 journal replay로 authoritative하게 계산 — 호출자가 못 속임), `audit_protocol(path)`(journal을 genesis부터 replay해 (1) 모든 `execution_completed`에 같은 `arm_id`의 선행 `prediction_sealed`가 있는지 — `prediction_sealed`의 journal `record_id`는 `seal_id`이지 `arm_id`가 아니므로 반드시 payload를 읽어야 함을 docstring과 전용 테스트로 고정, (2) 동일 arm_id 중복 실행, (3) `final_discovery_sealed` 이후 어떤 이벤트도 없는지(terminal invariant), (4) final seal의 sequence/journal_terminal_digest/executed_arm_ids가 replay 독립 재계산과 일치하는지). 9개 violation code를 구조화된 `BlindProtocolAudit(valid, violation_codes)`로만 리턴 — PASS/PROTOCOL_VIOLATION 같은 외부 verdict 합성은 다음 Gate 몫으로 명시적으로 안 함. 기존 코드 변경은 `research_journal.EVENT_TYPES`에 `"final_discovery_sealed"` 1개 추가뿐(스펙이 명시적으로 요구한 유일한 기존 코드 수정) — `PredictionSeal`/`seal_predictions()`/`causal_experiment.py`는 전혀 안 건드림. **accident와 protocol violation을 명확히 분리**: `causal_experiment.detect_accident`(intended/submitted/executed spec digest 불일치 — "실험 준비/실행 실패")와 이번 Gate의 seal/order/final-freeze 위반("연구 절차 자체가 깨짐")은 서로 다른 실패 종류이므로 `blind_protocol.py`는 accident를 전혀 보고하지 않고 `causal_experiment.py`도 protocol violation을 전혀 보고하지 않음. 신규 테스트 25개(`tests/test_deterministic_blind_protocol.py`) — 정상 seal→execute 순서 PASS, seal 없는 실행/실행 후 seal 각각 FAIL, `seal_predictions()`의 기존 `sealed_at_seq` 강제가 여전히 작동하는지, `prediction_sealed`의 record_id≠arm_id 구분이 실제로 맞게 읽히는지, 중복 arm 실행 FAIL, `seal_final_discovery`가 실제 journal 상태(빈 journal→genesis digest 포함)에서 필드를 정확히 계산하는지, terminal invariant(hypothesis 갱신이든 새 execution이든 final seal 뒤엔 뭐든 FAIL), 3종 tamper(sequence/journal digest/executed arm set 불일치) 각각 FAIL, 최종 hypothesis digest 일치/불일치, `FinalDiscoverySeal.canonical()`에 real identity 문자열 9종 부재, dependency AST 2종(`blind_protocol.py` 자신 + wildcard). **실제로 결함을 잡는지 3종 mutation 수행**(RULES.md 검사기 결함 주입 원칙, 매번 원상복구 확인): (a) `blind_protocol.py`에 `from .blind_evaluator import BlindTranslationManifest` 실제 추가 → dependency 테스트가 정확히 그 이유로 실패함을 확인. (b) seal-after-execution 감지 분기를 `if False`로 무력화 → `test_seal_after_execution_is_a_violation`이 실패함을 확인. (c) terminal invariant 분기를 `if False`로 무력화 → post-final-seal 테스트 2개가 실패함을 확인. 구현 중 실제 버그 2개 자체 발견·수정: ① 최초 `audit_protocol` 로직이 "seal이 execution보다 먼저 와야 한다"를 execution 처리 시점의 sequence 비교로만 검사해서, seal이 execution *이후*에 오는 경우(late seal)를 놓쳤음 — replay가 순서대로 진행되므로 sequence 비교 자체가 불필요하다는 걸 깨닫고 "seal 도착 시점에 이미 실행된 arm인지" 체크로 재작성(더 단순해짐). ② 테스트에서 `seal_predictions()`의 반환값을 `JournalEntry`로 착각(실제로는 `PredictionSeal` 반환) — `read_journal(path)[-1]`로 실제 저장된 entry를 다시 읽도록 수정. `CausalHypothesis` 생성 시 `status="active"`가 유효하지 않은 값이라 `HYPOTHESIS_STATUSES`(`untested`/`supported`/`conditional`/`contradicted_in_domain`/`underspecified`/`superseded`/`incompatible`/`anomalous`)에서 `"untested"`로 정정. 전체 테스트 1427→1452개 통과, 로컬 실행. 중복 arm_id 시나리오도 별도로 확인: `executed_arm_ids`는 집합 기반이라 자연히 dedupe되고, `audit_protocol`은 그와 별개로 `DUPLICATE_ARM_EXECUTION`을 여전히 잡아서 두 계산이 서로 숨기지 않음을 확인. G7.2는 아직 B가 인과구조를 맞혔는지 전혀 증명 안 함 — "B는 정답을 볼 수 없고, 결과를 보기 전에 예측을 남겨야 하며, 최종 답안 제출 후엔 수정할 수 없다"까지만 성립. **사용자가 재검토하며 문서 표현 하나를 정정**: 이번 dependency 테스트는 `blind_protocol.py` 자신의 **직접(direct) import**만 AST로 검사했을 뿐, "dependency graph 전체(transitive closure)를 검증 완료"라고 쓰면 과장 — 예를 들어 `blind_protocol.py → some_b_module.py → blind_evaluator.py`처럼 중간 모듈을 거친 우회 경로는 지금 검사 대상이 아니다. 다만 이건 G7.2를 다시 여는 문제는 아님: 지금은 seal/auditor라는 protocol 계층만 있고, 실제 B autonomous entrypoint(`blind descriptor → hypothesis → experiment_designer → prediction → execute → update`로 이어지는 진짜 실행 그래프)가 아직 존재하지 않으므로 검사할 transitive closure 자체가 없다. **G7.3의 필수 완료 조건으로 명시 이월**: G6d `ExperimentDesigner`가 실제 blind session에 연결되는 순간부터는 파일 하나가 아니라 B 실행 시작점(`run_blind_discovery()` 같은 entrypoint)에서 재귀적으로 도달 가능한 모든 모듈을 따라가며 `blind_evaluator`/`ground_truth`/`synthetic_runtime` 어디에도 안 닿는지 검사해야 함. 사용자 제안: G7.3은 세 world를 한 번에 돌리지 말고 먼저 WORLD-S01 하나로 "aliasing → B 초기 가설 → 후보 실험 생성 → G6d disagreement ranking → PredictionSeal → evaluator-side alias↔real 번역 → SyntheticAExecutor 실행 → 결과를 다시 alias로 관측 → 가설 갱신 → 반복 → FinalDiscoverySeal"까지 끝까지 도는 end-to-end vertical slice 하나를 먼저 완성한 뒤 S02/S03으로 확대. 다음은 G7.3(Autonomous Discovery) |
| 2026-09-23 | **G7.1 alias-model repair — control/observable이 같은 variable을 공유할 때 연결 정보 추가** (같은 날, 1452→1454). G7.3 착수 전 사용자가 구조적 공백을 지적: 실제로 같은 real variable(예: WORLD-S02의 x2)이 control이자 observable일 때, 기존 G7.1 구현은 control alias와 observable alias를 완전히 독립적으로 생성해서(`_alias_token(..., "control", name)`과 `_alias_token(..., "observable", name)`이 같은 `name`이어도 서로 무관한 해시) B 입장에서 "내가 조작한 이 control과 내가 읽는 이 observable이 같은 대상이다"를 알 방법이 전혀 없었음. 사용자 지적: 이건 정답 누출이 아니라 **세계의 공개 인터페이스 구조**이며, 이걸 숨기면 blind test가 아니라 "물리 자체가 아니라 배선도까지 맞혀라"는 다른(더 어려운) 문제가 됨 — 특히 S03/GT-M1처럼 매개변수가 조작 대상이자 관측 대상인 구조에서는 이 연결 정보 없이는 "B가 추론을 못한 것"과 "harness가 애초에 알려주지 않은 것"을 구분할 수 없게 됨. **수정**: `blind_session.py`의 `BlindControlDescriptor`/`BlindObservableDescriptor`에 `alias_variable_id` 필드 추가(real variable 이름은 여전히 비공개, 오직 "같은 공개 variable을 가리킨다"는 사실만 공개) — control/observable alias 자체는 서로 다른 핸들로 유지(B가 "조작"과 "관측"을 여전히 구분해야 하므로), `alias_variable_id`만 공유. `blind_evaluator.py`의 `make_blind_session`이 이제 `variable_alias[name]`(단일 per-variable 토큰)에서 control/observable의 `alias_variable_id`를 유도 — 신규 helper `control_descriptors(spec, seed)`/`observable_descriptors(spec, seed)`(`BlindWorldDescriptor`는 여전히 bare alias 문자열 튜플만 노출하므로, variable-identity 링크가 필요한 호출자는 이 helper를 씀). **구현 중 자체 발견한 버그**: 최초 구현이 이 구성 로직을 `make_blind_session` 내부와 독립 함수 `control_descriptors`/`observable_descriptors`에 두 번 복붙해서, 한쪽만 mutation을 걸었더니 다른 쪽 테스트가 못 잡는 사각지대가 실제로 발생 — `_control_descriptors_from_manifest`/`_observable_descriptors_from_manifest`라는 단일 shared 함수로 통합해 두 진입점이 절대 벌어질 수 없게 재구성. 신규 테스트 2개(`tests/test_deterministic_blind_session.py`, 26→28) — 같은 real variable을 공유하는 control/observable이 실제로 같은 `alias_variable_id`를 갖는지(WORLD-S02의 x2로 확인, evaluator-only manifest를 통해 real 이름으로도 교차 검증), control/observable alias 자체는 variable alias와 항상 다른지. **실제로 결함을 잡는지 mutation 검증**: 통합 함수의 `alias_variable_id` 계산을 `manifest.variable_alias[name]` 대신 `manifest.control_alias[name]`으로 바꿔서(링크가 끊긴 상황을 재현) 재실행하니 두 신규 테스트가 정확히 그 이유로 실패함을 확인 후 원상복구 — 통합 전 최초 mutation 시도에서는 잘못된 사본만 건드려 거짓 통과가 날 뻔했던 것도 이 과정에서 함께 드러나 고쳤음. 전체 회귀 1452→1454개 통과, 로컬 실행. 별도 커밋으로 G7.3a와 분리(사용자 명시 요청 — 나중에 G7.3a에서 문제가 나와도 alias 모델 자체를 의심할 필요가 없도록) |
| 2026-09-23 | **Research World Abstraction G7.3a 완료 — Blind Execution Substrate** (같은 날, 1454→1470). 사용자가 G7.3을 한 번에 구현하지 말고 G7.3a(실행 경계)→G7.3b(가설 공간)→G7.3c(자동 루프) 3단계로 쪼개라고 명시 — 이유: (1) `research_loop.py`는 여전히 가설 생성이 caller-supplied라 자동 발견이 성립 안 함, (2) G6d `rank_discriminating_candidates(compiled_specs: Mapping[str, ResearchWorldSpec])`에 실제 `SyntheticWorldSpec`을 넣으면 `world_id`/`world_revision`이 B로 새어나감(구조적 `ResearchWorldSpec` Protocol을 real spec도 만족하므로 지금까지 막을 장치가 없었음), (3) `ExecutionResult.canonical()`의 `executed_spec_digest`/`run_digest`가 real digest 그대로라 raw 실행 결과를 journal에 넣으면 G7.1의 벽에 구멍이 남. 이번 세션은 **G7.3a만** 구현하고 별도 커밋 — G7.3b(hypothesis space 자동 생성)/G7.3c(autonomous loop)는 각각 별도 승인 후 진행. 신규 두 모듈, 정확히 G7.1의 B-facing/evaluator-only 분리 패턴 재사용: **`engine/deterministic/blind_execution.py`(B-facing)** — `BlindCandidateSpec`(`world_id`가 곧 alias world id, `real_world_id` 필드 자체가 없음, `ResearchWorldSpec` Protocol을 구조적으로 만족 확인)과 `BlindCheckpoint`/`BlindRun`(`ResearchRun` Protocol 만족, digest는 자기 자신의 alias 데이터로만 계산 — real `SyntheticRun.digest`를 절대 복사하지 않음). **`engine/deterministic/blind_synthetic_executor.py`(evaluator-only)** — `SyntheticBlindAExecutor`가 real spec+manifest를 쥔 유일한 실행기: `BlindCandidateSpec`의 alias control 값을 manifest로 real variable에 역번역 → 실제 `SyntheticAExecutor` 실행 → 결과를 `BlindRun`으로 재번역(real observable 이름 → alias, real digest는 전혀 안 건드리고 `BlindCandidateSpec.digest`/`BlindRun.digest`로 완전 재계산) → 실패 시 `error_message`도 고정 문자열로 치환(traceback이 real 식별자를 담을 가능성 차단). B-facing 코드는 `executor: AExecutor`(Protocol)만 알고 이 클래스를 직접 import하지 않음 — 외부 harness가 조립해서 넘겨주는 의존성 역전 구조. 신규 테스트 16개(`tests/test_deterministic_blind_execution.py`) — Protocol 만족 확인 2종, end-to-end 실행이 real RULE_S02(`x3:=x1 AND x2`)와 실제로 같은 답을 내는지(alias 번역이 그냥 안 터지는 게 아니라 왕복이 맞는지 확인), wrong-world/unbound-control/real-spec-직접-전달 3종 거부, **G6d 통합 테스트**(`compiled_specs`에 `BlindCandidateSpec`만 넣고 H-always/H-gated 경쟁 가설로 실제 `rank_discriminating_candidates` 호출 — real spec이 전혀 안 들어갔음을 `isinstance` assert로 이중 확인), 직렬화 leakage(real digest/real 변수명 9종 secret 값 전부 부재, `executed_spec_digest`/`run_digest`가 항상 blind 값), dependency AST(B-facing `blind_execution.py`가 `blind_evaluator`/`blind_synthetic_executor`/`ground_truth`/`synthetic_runtime` 미참조, 반대 방향 `blind_synthetic_executor→blind_evaluator`는 실제로 존재하는지도 확인). **스펙이 요구한 결함 주입 4종 중 3종 실제 수행**(4번째 hypothesis-elimination은 G7.3b/c 영역이라 이번엔 대상 없음, 문서에 사유 명시): (A) `compiled_specs`에 real spec을 직접 넣음 → G6d 통합 테스트의 `isinstance` assert와 real-spec-거부 테스트 양쪽에서 잡힘. (B) `SyntheticBlindAExecutor`가 real `executed_spec_digest`를 그대로 반환 → digest 전용 테스트가 잡음; 이어서 real `SyntheticRun`을 `BlindRun` 대신 그대로 반환하는 변형까지 추가로 시도 → leakage/digest/AND-gate 의미 테스트 4종이 동시에 잡음(real checkpoint가 애초에 alias로 안 걸러져서 `WORLD-S02` 등 secret 문자열도 직렬화에 그대로 나타남). (C) "랭킹 무시하고 항상 첫 후보 선택" 결함을 별도 스크립트로 시뮬레이션(기존 `experiment_designer.py`는 스펙 원칙상 이번엔 건드리지 않음) — 깨진 선택이 `E-00`(score 0)을 고르는 반면 실제 랭킹 1위는 `E-10`(score 1)이라 `ranked[0].candidate_id == "E-10"` assertion이 이 결함 유형을 실제로 잡는다는 것을 확인. 전체 mutation 원상복구 확인 후 전체 회귀 1454→1470개 통과, 로컬 실행. G7.3a는 "B가 실제 spec 없이 G6d 실험 선택기를 쓸 수 있는가"만 증명 — 가설을 사람이 안 넣어도 되는지(G7.3b), B가 스스로 선택→실행→가설 갱신을 반복하는지(G7.3c), 최종 답이 실제 정답 구조인지(G7.4)는 전부 다음 |
| 2026-09-23 | **Research World Abstraction G7.3b 완료 — Blind Hypothesis Space Generation** (같은 날, 1470→1529). 설계자(사용자)가 뼈대(G7.3b-1 어휘 / -2 생성기 / -3 예측 물질화, 입력은 blind 정보만, 루프 반복은 G7.3c)를 주고 세부는 구현자에게 위임. 신규 B-facing 모듈 3개: `blind_hypothesis.py`(어휘 — `BlindCausalClaim`, 6종 kind, `predict_target`), `blind_hypothesis_generator.py`(`BlindHypothesisGenerator.generate(world, controls, observables)` → 목표 observable별 `BlindQuestion`), `blind_prediction_materializer.py`(`BlindExperimentPlan` — B 스스로 만든 실험 계획, 각 control을 1/0/자유로 둔 모든 조합에서 전부-자유 제외; claim → `CausalHypothesis`(`InterventionalPrediction`); `InterventionalPredictionProvider` → G6d). **뼈대에서 고친 4가지**: (1) `BlindWorldDescriptor`는 alias 문자열만 가지고 control↔observable 연결(`alias_variable_id`)은 개별 descriptor에만 있어서, 생성기는 descriptor 3종을 받고 같은 세계인지 검증함. (2) `CausalHypothesis`는 생성 시점에 prediction이 비어 있으면 안 되므로 생성기는 구조적 claim만 만들고 `CausalHypothesisSet`은 물질화 단계에서 만듦. (3) "V1↛V3"는 두 실행의 대조라 G6d(후보별 값 비교)가 못 씀 — 모든 claim을 baseline을 포함한 완전한 방정식으로 정의. (4) 다른 목표에 대한 가설을 한 집합에 섞으면 G6d가 가짜 불일치를 세므로 목표별 집합으로 분리. **어휘 확장**: 초안의 4종(DIRECT/NO_EFFECT/CONDITIONAL/MEDIATED)이 세 벤치마크 정답 구조와 1:1로 겹쳐 "정답 메뉴에서 고르기"가 되므로 가장 가까운 경쟁형 INVERTED(NOT)·DISJUNCTIVE(OR)를 추가 — 완화일 뿐 중립성 증명은 아님. **선언된 가정**: 자유 변수 baseline=False(파라미터), 정상상태(최종 tick에서 평가), 원인·매개는 조작 가능한 변수만. **평가자측 측정**(B는 결과를 안 봄): S01/S02/S03(ticks=2) 모두 전체 계획 실행 시 정답 구조 하나만 살아남음. **발견한 한계**: S03을 ticks=1로 관찰하면 틀린 claim `x2 -> x3`만 단독 생존 — 정상상태 가정이 조용히 틀린 답을 냄. known-limit 테스트로 고정. 결함 주입 6종(evaluator import, 자유 원인 True 해석, MEDIATED 누락, set 순서 의존, provider 빈 튜플, 자유 없는 계획) 전부 테스트가 잡음. G7.2에서 이월된 전이 의존성 검사를 이번에 구현(B 진입점 5개에서 import를 재귀 추적). 아직 안 한 것: 결과로 가설 갱신·반복·FinalDiscoverySeal 연결(G7.3c), 정답 채점(G7.4) |
| 2026-09-23 | **G7.3b-4 완료 — Temporal Observation Semantics** (같은 날, 1529→1543). G7.3b에서 발견한 한계(S03을 1 tick만 관찰하면 틀린 `x2 -> x3`가 단독 생존)를 G7.3c 전에 정정하라는 설계자 결정. 원칙: "개입+관측 대상+관측 시점(horizon)까지가 하나의 실험". 간선별 delay는 넣지 않고 A의 공개 tick 규칙(모든 간선이 정확히 1 tick)만 사용. 변경: (1) claim이 정적인 식에서 **tick 갱신 규칙**으로 바뀜 — `simulate_claim`이 tick 0(고정값+baseline)부터 모든 변수를 이전 tick 상태로 동시에 갱신, 같은 tick 안 연쇄 전파 없음. B는 A를 돌리지 않고 자기 가설만 시뮬레이션. (2) 실험 계획 = 개입 × horizon(1..world.ticks), horizon은 `BlindCandidateSpec.ticks` 한 곳에만 존재. (3) provider가 (고정 control, horizon)으로 예측을 찾음, 누락 시 오류. (4) `check_prediction_at_horizon` — 다른 horizon끼리 비교, horizon에서 끝나지 않은 run, 관측값 누락을 전부 오류로 거부. (5) `inseparable_pairs` — 허용된 실험으로는 못 가르는 가설 쌍을 B가 자기 예측만으로 보고. (6) G6d `rank_discriminating_candidates`에 선택적 `cost` 추가(구별력 같으면 짧은 horizon 우선, 미지정 시 기존 순서 그대로). **실제 버그 발견·수정**: `SyntheticBlindAExecutor`가 `BlindCandidateSpec.ticks`를 아예 읽지 않고 항상 실제 spec 길이로 실행하고 있었음(설계자가 예시로 든 결함 1번이 이미 코드에 존재) — 이제 후보 horizon대로 실행, 세계 한도 초과는 거부. **측정**(평가자측): S01/S02/S03(2 tick)은 전체 계획 후 정답 하나만 생존. S03(1 tick 한도)은 이제 `x2 -> x3`와 `x1 -> x2 -> x3` 둘 다 생존하고, B가 그 쌍을 스스로 '구별 불가'로 보고 — 기존 known-limit 테스트를 회귀 테스트로 뒤집음. 1 tick 한도 세계에서 생기는 구별 불가 쌍은 전부 '사슬 vs 그 마지막 간선' 형태뿐임을 테스트로 고정. 결함 주입 7종(horizon 무시 실행, 같은 tick 연쇄, 교차 horizon 비교, evaluator import, provider horizon 무시, 누락을 False로 채움, G6d cost 무시) 전부 테스트가 잡음 — 단 3·6·7번은 각각 전용 테스트 하나만 잡음. 여전히 가정: baseline=False, 모든 간선 1 tick. 다음은 G7.3c |
| 2026-09-23 | **G7.3c 완료 — Autonomous Blind Research Loop** (같은 날, 1543→1573). **규칙 변경(설계자 결정)**: RULES.md "자동 실행 금지"에 예외 추가 — blind 합성 세계에서만 B가 고른 실험을 승인 없이 자동 실행, 물리 A는 여전히 승인 필수(물리 실행기가 blind 후보를 거부함을 테스트로 확인). 신규 `engine/deterministic/blind_research_loop.py` — `run_blind_research(world, controls, observables, executor, journal)`: 발견 단계(G6d가 살아있는 가설 쌍을 가장 많이 가르는 실험 선택 → 모든 질문의 살아있는 예측을 봉인 → 실행 → `check_prediction_at_horizon`으로만 비교 → 반박된 가설 제외, 반복) → 검증 단계(발견 단계가 안 돌린 계획 실험을 생존자에게 전부 적용) → `FinalDiscoverySeal`. 질문별 판정 4종: SOLVED / INSEPARABLE / NO_SURVIVOR(가설 언어로 설명 불가) / OPEN(예산 소진). 전체 종료: COMPLETE / LIMIT_REACHED / HARNESS_FAILURE. 설계자 뼈대에서 바꾼 것: EXHAUSTED 제거(결정론+전체 나열 계획에서는 INSEPARABLE과 같은 조건이라 도달 불가 경로), 가설별 UNRESOLVED 제거(모름은 가설 집합의 성질), NO_SURVIVOR 추가, 상태는 기존 어휘 재사용(`contradicted_in_domain`/`supported`/`underspecified`, CONFIRMED 없음), 여러 질문 동시 봉인·갱신, G7.2 감사 통과를 성공 조건에 포함. **구현 중 발견한 위험**: 뼈대에 없던 검증 단계를 추가한 이유 — 가설 언어 밖의 세계(S02에서 x2 초기값 True)에서 발견 단계만 돌리면 x2가 틀린 "x1 -> x2"로 SOLVED(실험 1번만 거침), x3는 틀린 두 가설 사이 INSEPARABLE. 검증 단계를 거치면 둘 다 NO_SURVIVOR. 예측("전부 탈락할 것")이 틀렸던 것을 측정으로 발견. 검증 없는 결과는 `validated_fully=False`로 표시, 위험 사례를 테스트로 고정. **측정 결과**: S01/S02/S03(2tick) 정답 구조 SOLVED, S03(1tick) INSEPARABLE, 가설 언어 밖 세계 NO_SURVIVOR, 모든 journal이 G7.2 `audit_protocol` 통과. 발견 단계 실험 수: S02 5/8, S03 4/16, S03(1tick) 3/8 — 별칭 seed 0/1/2에서 동일. 점수 무시 선택기(아무 쌍이나 가르는 첫 실험) 대비 절대 더 많지 않고 여러 경우 더 적음(S02 2tick: 5 vs 6~8). 결함 주입 8종 전부 잡힘. 단 "G6d 점수 무시" 결함은 처음 효율 테스트(계획 크기보다 적음)로는 못 잡아서, 점수 무시 선택기와 직접 비교하는 테스트로 강화. 한계: 가설 메뉴는 닫혀 있음(새 설명 발명 없음), 세계가 작아 검증 단계가 계획 전체를 돎, baseline=False·간선 1tick 가정 유지. 다음은 메타인지(왜 모르는가) 단계 |
| 2026-09-23 | **연구 데이터 저장소 v1** (같은 날, 1573→1596). 설계자 결정: 저장 시스템을 초기부터 단단하게, 위치는 D:. `D:\KiroCrewTraceVault\success-is-mother-of-failure\research_store\`(Git 밖), 코드 `research_store/`(최상위), 채우는 스크립트 `run_blind_benchmark.py`, 계약 `docs/current/RESEARCH_STORE_V1.md`. 핵심: (1) 신뢰 등급을 태그가 아니라 디렉터리로 분리 — `b_visible`(학습형 B가 읽을 수 있는 유일한 곳) / `evaluator` / `ground_truth`, `b_visible.py` 모듈은 다른 tier로 가는 코드 경로가 없음(import 추적 테스트). (2) b_visible 쓰기마다 그 세계의 비밀 문자열 검사, 검사 목록은 필수 인자. (3) 참조는 덜 비밀스러운 tier로만. (4) 객체는 내용 해시 이름, 레코드는 해시 체인 추가 전용 — 편집·삭제·순서 변경·digest 재계산 위조 모두 검출. (5) 모든 레코드에 commit/dirty/producer/semantics, 스크립트는 커밋 안 된 코드로 쓰기 거부, 읽을 때 semantics 지정 필수(섞이면 오류). **발견한 공백**: B의 journal에 실행 결과가 digest로만 남고 실제 관측값이 없었음 — 학습 데이터로 쓸 원본이 어디에도 없었다. 루프가 `observation_recorded`로 관측 궤적을 journal에 남기도록 수정. 기존 `runs/`는 출처 정보가 없어 이관하지 않음. 결함 주입 8종 — 처음 2종(체인 검사 끄기, 참조 안 된 객체 손상)을 못 잡아서 테스트 2개 추가 후 전부 잡힘. 한계: OS 격리 아님, 단일 writer 가정, 물리 A 실행은 아직 저장 안 함, ground_truth tier는 G7.4부터 |
| 2026-09-23 | **저장 계약 보강 (G7.4 전 1단계)** (같은 날, 1596→1616). sol 검토 반영 + 구현자가 찾은 공백 2개. (1) **실험 선택 이유 기록**: 매 실험 직전 journal에 `experiment_candidate_ranked`(기존에 정의만 되고 아무도 안 쓰던 G6d 이벤트 재사용) — 단계(discovery/validation), horizon, 질문별 예상 분리 쌍 수. 발견 단계는 항상 >0, 검증 단계는 항상 0임을 테스트로 고정(검증은 생존자끼리가 아니라 생존자 대 현실을 봄). 메타인지 단계의 "예상만큼 정보를 줬나" 질문의 재료. (2) **b_visible 허용 목록** `research_store/b_visible_schema.py`: 금지 목록에 더해 모든 문자열(키 포함)이 별칭 ID 형태·가설 문장 문법·고정 조건·판정 단어·손으로 열거한 어휘 중 하나여야 함. "아무 snake_case 단어" 허용은 실제 변수 이름 `x1`도 통과시키므로 거부. 오류 메시지는 거부된 문자열을 되풀이하지 않음. 비문자열 구조(개수·순서)를 통한 누출은 못 막음을 명시. (3) `.claude/` dirty 제외 규칙을 계약·README·코드 docstring에 명시(그 외 예외 없음). (4) 평가 경로 단방향을 계약 8조로 명시. (5) semantics를 `.../selection-log`로 올리고 이력표 작성 — 기존 18회 기록은 옛 라벨로 남고 섞이지 않음. 결함 주입 7종 — 처음엔 "거부된 문자열을 오류에 노출" 결함을 못 잡음(테스트가 키 검사에서 먼저 걸려 값 분기를 안 탐), 테스트 보강 후 전부 잡힘 |
| 2026-09-23 | **G7.4 완료 — 정답 채점 (2층 기준표)** (같은 날, 1616→1660). 설계자 확정안 그대로: (1) 기준표 `ground_truth/benchmark/*.json`(시나리오 7개) — 실제 규칙 코드와 시나리오 정의만 보고 손으로 작성, B 코드·B 실행 결과 미참조(테스트로 B 쪽 식별자 부재 확인), 채점 코드보다 먼저 별도 커밋 `c29d29f`로 봉인(digest `b6ed824d…`, 테스트가 고정). 목표마다 **구조 정답(`structural_claim`)과 달성 가능한 최선의 답(`best_answer`: single/tie/unexpressible)을 절대 한 필드로 합치지 않음** + 한계 3종·최소 관측 horizon·표현 가능성. 벤치마크 스크립트가 세계를 기준표 파일에서 직접 만들어 둘이 어긋날 수 없음. (2) 채점기 `research_store/score_blind.py`: 질문별 판정 7종(CORRECT_SOLVED / CORRECT_INSEPARABLE·HONEST_UNEXPRESSIBLE / CONFIDENT_WRONG·MISSED_TRUTH·WRONG_INSEPARABLE / UNSCORABLE)을 4묶음으로, 별도 축(구조 일치, 관측 일치, 숨은 변수, 언어·관측·개입 한계, 과대주장, 덜 좁힘, 검증 완료)은 판정에 섞지 않음. 불가피한 동률에서 한쪽을 골라 SOLVED하면 맞더라도 CONFIDENT_WRONG(과대주장). 결과는 ground_truth tier에 저장(기준표·evaluator·b_visible 참조), b_visible에는 채점 정보가 들어가지 않음. (3) 신규 시나리오 S03-hidden-t2(x2가 조작·관측 불가): **실행 전에** 기준표에 "B의 언어로 표현 불가"라고 예측·봉인 → 실제 B는 NO_SURVIVOR → HONEST_UNEXPRESSIBLE, 구조 일치 false. **전체 결과(7 시나리오 × 별칭 3배치)**: CORRECT_SOLVED 39 / CORRECT_INSEPARABLE 3 / HONEST_UNEXPRESSIBLE 9 / 실패 0 / 채점 불가 0 — hard gate CONFIDENT_WRONG==0 통과. 검증 단계를 끈 실행은 채점기가 CONFIDENT_WRONG로 잡음을 테스트로 고정. 결함 주입 8종 — 처음 2종(프로토콜 위반 실행 채점, 원인 순서 의존)을 못 잡아 테스트 추가 후 전부 잡힘. 한계: 시나리오가 작고 기준표 작성자가 가설 언어를 아는 사람(표현 가능성 판단에 언어 정의를 씀 — B 실행 결과는 안 봄) |
| 2026-09-23 | **경험 기록 3단계: 근거 연결 · B 자신의 한계 진단 · 언어 공백 탐지** (같은 날, 1660→1681). sol의 "언어 3층" 제안을 코드와 대조해 3개로 좁혀 구현. (1) **근거 연결**: 최종 가설마다 `evidence` — 시험받은 실험마다 supports(예측 맞음, "확정" 아님)/refutes(틀림), 각각 journal의 `result_compared` 기록 digest를 가리킴. 탈락 가설의 마지막 근거는 반박한 실험. (2) **B 자신의 한계 진단** `engine/deterministic/blind_limitations.py`(B-facing): 기준표를 보지 않고 **자기 가설을 더 긴 horizon으로 시뮬레이션**해서 구별 불가 쌍이 시간을 늘리면 갈리는지 계산 — observation_horizon / not_diagnosable / mixed / vocabulary_exhausted / budget_exhausted / none. journal `limitation_assessed`(신규 이벤트)로 최종 봉인 전에 기록. 채점기가 이 진단을 기준표 한계 필드로 채점(`diagnosis_consistent`) — 기준표는 B에게 주지 않고 B의 판단을 평가만 함. 벤치마크 전 질문에서 일치(S03-t1: "2 tick이면 갈린다" = 기준표 최소 horizon 2). 정직한 한계: B는 "조작 가능한 변수가 하나 더 있으면"을 물을 수 없음(가설이 조작 가능한 변수만 이름으로 가짐) — not_diagnosable로만 말함. (3) **언어 공백 탐지** `research_store/language_gaps.py`(evaluator): B의 기록(판정·생존 가설·자기 진단)이 같은데 실제 구조가 다른 경우를 찾아 ground_truth tier에 저장. 벤치마크에서 **정확히 1건**: S02-x2(x3, 잘못된 baseline 가정의 AND)와 S03-hidden(x3, 숨은 2-tick 매개)이 B 기록상 똑같이 "설명 불가, 어휘 소진" — 언어 확장 필요의 첫 측정 증거. 기록 단계는 손실 없음을 별도 확인(journal 관측을 실제 이름으로 되돌리면 A의 실제 run과 모든 tick 일치). **검증 방법 결함 발견(유형 G 신설)**: 결함 주입 중 같은 길이 치환 + 같은 초 안 복구 → Python .pyc 캐시가 이미 복구된 결함 코드를 계속 실행해 무관한 결함들이 같은 테스트를 깨뜨림. `python -B` + `__pycache__` 삭제로 오늘의 결함 주입 5묶음 37종을 전부 재실행해 **전부 여전히 잡힘** 확인, 이번 7종도 각각 자기 테스트에서만 잡힘. `VERIFICATION_LIMITS_AND_LESSONS.md`에 기록 |
| 2026-09-23 | **언어 공백 보고서의 의미론 혼합 결함 — 실제 저장소에서 발견·정정** (같은 날, 1681→1683). 직전 커밋 `13347f3`으로 D:에 실제 실행했더니 공백이 1건이 아니라 **2건**으로 보고됨 — 두 번째는 같은 공백의 중복(B 진단 None). 원인: 보고서가 같은 기준표의 채점 기록을 **전부** 읽어서, B가 자기 진단을 기록하기 전(이전 G7.4 실행)과 후의 실행이 섞임 — 저장 계약 7조(의미론 혼합 금지) 위반. 채점 기록에 채점 대상 실행의 B 의미론이 없어서 거를 수 없었음. 정정: 채점 기록에 `b_semantics` 태그 추가, 보고서는 B 의미론을 필수 인자로 받아 그것만 읽음(태그 없는 옛 채점은 제외). 회귀 테스트가 옛 동작을 실제로 잡음을 확인. D:의 잘못된 보고서 레코드는 추가 전용 원칙대로 **지우지 않고 남기고**, 정정된 보고서를 새 레코드로 추가(태그 `b_semantics`로 구별). 교훈: 테스트는 저장소를 매번 새로 만들어서 "여러 버전의 기록이 섞인 저장소"라는 실제 상황을 재현하지 못했음 — 실제 저장소에 한 번 돌려본 것이 테스트보다 먼저 잡음 |
| 2026-09-24 | **G8 완료 — 가설 언어 v2: 먼저 보기 · 놀람 · 알아채기** (1683→1712). 설계자 결정: sol의 G7.4a~h 제안 중 코드와 대조해 좁힌 안 — 사람이 "지연" 단어를 메뉴에 넣는 대신 B가 **자기 관측에서 알아채게** 함. 순서: 기준표 v2를 코드보다 먼저 봉인(`54abda4`, digest `9a691ad1…`, v1은 그대로), 그 뒤 구현. (1) **먼저 보기**: 가설 전에 관찰 전용 실행 1회(아무것도 고정 안 함) — 실행 전에 journal에 `observation_only_declared`로 선언, 봉인·채점 금지(감사 규칙 확장: 위반 2종 신설). 0 tick 값을 보이는 변수의 초기값으로 사용, 안 보이는 변수만 False 가정. (2) **놀람**: 질문의 살아있는 가설이 전부 반박되는 순간 `anomaly_recorded`. (3) **알아채기** `engine/deterministic/blind_noticing.py`: 놀람 시 B가 가설 없이 자기 관측 전체를 훑어 "T는 S를 k(≥2) tick 뒤 따라간다"를 찾음(모든 run에서 예외 없고, 실제 변화를 최소 1번 설명해야 함) → 새 종류 DELAYED 가설로 추가(`hypothesis_noticed`, 유도에 쓴 실험 기록). **알아챈 가설은 그 뒤 실험으로만 검증** — 유도에 쓴 데이터는 근거가 아님. 시험할 실험이 안 남으면 "미검증 제안"으로만 남고 답이 될 수 없음. 문법 v2 동결(`GRAMMAR_DIGEST` 테스트 고정), v1 가설 ID 불변. **결과(기준표 v2)**: S02-x2 전부 CORRECT_SOLVED(v1에선 설명 불가) — 초기값 관측이 원인이었음을 확인. 나머지 5개 불변. **S03-hidden: B가 정확히 기준표의 최선의 답 "x1 -> x3 after 2 ticks"를 알아챘으나, 놀람이 계획의 마지막 실험에서 일어나 시험할 실험이 없음 → MISSED_TRUTH**(봉인된 기준표를 결과 보고 바꾸지 않음). 채점에 새 축 `proposal_matches_best_answer`(찾았으나 시험 못함)로 구별. 같은 세계를 3 tick 허용하면(테스트 전용) 놀람 → 알아채기 → 새 실험으로 검증 → SOLVED 전 사이클 동작(별칭 3배치 동일). 문법 v2 밖의 새 세계(숨은 x2가 True로 시작)는 정직하게 NO_SURVIVOR. v1의 언어 공백 1건은 v2에서 사라짐. 결함 주입 10종(캐시 끔) — 1종(채점기가 아무 제안이나 인정) 못 잡아 테스트 보강 후 전부 잡힘. **정직한 한계**: 알아채기 탐지기 자체가 "k tick 뒤 따라간다"는 개념을 이미 앎(어떤 변수·몇 tick·있는지 여부만 데이터에서 찾음), 반대 방향 지연은 문법 v2에 없음. 다음 결정: 시험할 실험이 없을 때의 처리(설계자), holdout 세계(문법 동결 후, 설계자가 규칙 지정) |
| 2026-09-24 | **G9 완료 — B가 원시 동작으로 실험 도구를 스스로 만듦** (1712→1733). 설계자 방향: "도구를 주지 말고 재료만", 호기심은 새 실험을 떠올리는 능력. (1) **A 쪽 원시 동작**: 합성 세계에 `SyntheticScheduledClamp`(특정 tick에 스위치 켜기/끄기) 추가 — 세계 규칙 불변, 스위치를 누르는 시점만 추가. 일정이 없는 세계·후보의 digest는 그대로. (2) **B 쪽** `engine/deterministic/blind_tools.py`: 계획된 실험을 다 쓴 뒤 미검증 아이디어나 동률이 남으면, B가 "t tick에 1/0"만으로 한 스위치의 켜기/끄기 패턴을 **자기 가설로 시뮬레이션해서** 탐색 — 새롭고(계속 켜두기 제외) 정보가 있는(가설 쌍을 가르거나 아이디어를 반박당할 위험에 놓는) 패턴 중 **가장 가혹한 시험**을 고름. 가혹함 = 이미 반박된 가설 중 **지금까지 데이터에서 아이디어와 가장 많이 일치했던 경쟁자부터** 이 시험에서 다르게 예측하는가. 처음엔 반박된 가설을 똑같이 세었는데, 먼 경쟁자(반대 방향 가설)가 가까운 경쟁자를 상쇄해 약한 시험([1,1,0])이 뽑힘을 측정으로 발견 → 가까운 순 정렬로 수정. 쓸모 있었던 패턴은 변수 이름 없는 `Tool`로 도구함에 보관, 다음 실행에서 먼저 재사용(저장소 b_visible `toolbox`). 못 찾으면 `tool_search_failed`로 기록. 도구 실험도 계획 실험과 똑같이 봉인·실행·비교·감사. **결과**: S03-hidden에서 B가 **아무도 이름 붙여주지 않은 "0 tick에만 켜고 끄기"(펄스)를 스스로 설계** → 알아챈 "x1 -> x3 after 2 ticks"를 새 실험으로 검증 → CORRECT_SOLVED(관측 수준, 구조 일치는 false). 다음 실행들은 같은 도구를 재사용. S03 1 tick 동률은 도구 탐색 실패로 기록되고 동률 유지(정직). 결함 주입 9종 전부 잡힘(단 "가까운 순 정렬 제거"는 별칭 seed 2/3에서만 잡힘 — seed 1은 알파벳 순서가 우연히 맞음). 한계: 원시 동작(한 스위치의 tick별 켜기/끄기)과 탐색 공간은 사람이 정함 — B는 어떤 패턴을 언제 쓸지 발명, 원시 동작 자체는 주어짐. 다음: 환경 세계 조사 → 행동 설계(설계자 승인) |
| 2026-09-24 | **헌법 제25조 신설 + G10 물리 탐침(레시피 방식)** (1733→1757). 설계자 승인: 헌법 제25조(세계 밖 연구자는 세계 안의 선언된 탐침으로만 영향, 목적 없는 행동, 실패 이유 비공개), RULES 2장 "B는 A를 **직접** 조작하지 않는다", RULES 신설 "법칙은 최소 근본 수준으로"(목적 수준 금지, 물질 일반 성질만). **A 쪽** `engine/deterministic/probe_world.py`: 입자 없는 환경 세계 안의 탐침(위치·들고 있는 것(최대 1)·에너지), 원시 동작 5개 MOVE/GRASP/RELEASE/HEAT/WAIT(방향은 이웃 칸, 격자는 wrap). 이동은 에너지 1 → 도착 칸의 열, 열 가하기는 탐침 에너지 → 이웃 칸 열, 집기는 이웃 칸 광물 1단위(물 불가). 물리적으로 불가능한 행동은 상태 불변·이유 없음; 형식 오류만 거부. 매 tick 고체·에너지 보존(짧은 프로그램 전수 검사). **새 법칙** `solids_occupy_space`(환경 법칙 선택 항목, 꺼짐 기본·꺼져 있으면 digest 불변, GPU 경로는 거부): 고체도 공간을 차지해 수면 계산에 포함. 측정: 법칙 없이는 광물 1단위를 옮겨도 물 흐름에 **영향 없음**(물리적 도구 불가능) / 법칙 있으면 같은 행동이 물 분포를 바꿈(도구 가능성). B에게는 비공개. **B 쪽** `engine/deterministic/blind_probe.py`: 행동·방향·채널 전부 중립 기호(ACT-/DIR-/CH-, seed마다 섞임), 행동의 인자 개수만 공개, 격자 좌표는 공개(공간). 프로그램 ID가 내용에서 파생 → 봉인 후 바꾸면 감사가 잡음. 물리적 도구 판정 = 만든 경우 vs 같은 시간 기다린 경우의 측정값 비교(`control_program`/`structure_has_effect`). 평가자 쪽 `blind_probe_evaluator.py`만 기호↔실제를 앎. 결함 주입 10종(설계안 9종 + 법칙 무시) 전부 잡힘. 한계: 실시간 제어 없음(다음 단계), 낱개 물체 없음(양만), B가 탐침으로 가설을 세우는 연구 루프는 문법 v3(G11) 이후 |
| 2026-09-24 | **G11 문법 v3 — B가 자기 탐침의 행동이 무엇을 하는지 배움** (1757→1778). 설계자 결정: 범위는 탐침 자신의 행동만(세계 자체의 흐름은 v3.1), 격자 wrap은 좌표 계약으로 공개, 조건은 최대 ALL(2)이며 없음→하나→둘 순서로만 올라감, 한 행동의 여러 효과는 별개 주장. **G11a** `probe_grammar.py`: 효과 주장 = (행동, 방향, 대상, 변화량, 조건 ≤2), 대상은 self.x/y/energy/holding 또는 상대 칸 `rel:dx,dy:CH`, 원자 조건은 `>= 1`/`= 0`뿐, 위치 변화는 wrap 격자에서 측정, `GRAMMAR_DIGEST` 7aff4cd7… 고정. **G11b** `probe_induction.py`: 본 변화 → 무조건 주장, 반박되면 조건 탐색(없음→하나→둘, 안 되면 '설명 불가'). **G11c** `probe_research.py`: 탐색(관찰 전용 선언) → 두 행동 번갈아 시험, 매 프로그램 전에 모든 주장 봉인, 호기심 순서(모르는 행동 먼저) 후 전체 풀 검증. 측정: 정지 세계에서 36개 효과 **정확히** 복원(seed 3개), 두 조건은 GRASP에만 그리고 정제로만 등장. **G11d** `probe_planning.py`: 벽 세계에서 B가 '발밑이 따뜻할 때 동쪽 이동'을 16회 통과 '지지됨'으로 남긴 **자신 있는 오답** 발견 → B가 자기 주장을 모델로 반박 실험을 직접 설계(충분성: 실패 상태 근처에서 성공 예측 / 필요성: 조건 하나만 거짓, 성공 상태 근처). 충분성만으로는 우연을 다른 우연으로 바꿨음(측정). 결과: 벽이 막는 동쪽 이동·집기·열 가하기가 전부 '설명 불가', 틀린 '지지됨' 0개. **경계 구멍 수리**(G7.3b부터 있던 것): B 모듈이 `hypotheses.py`를 거쳐 `environment_spec`까지 import → 순수 타입을 `evidence.py`로 분리, 기존 경계 테스트 금지 목록에 환경·탐침 모듈 추가. 결함 주입 9종 전부 잡힘(`python -B`). 한계: 반박 실험 설계는 접두 3단계 이내만 탐색, 세계 흐름 있는 세계는 v3.1, 연구 저장소에는 아직 기록 안 함, 실시간 제어 없음. 다음(설계자 승인 순서): 문법 v3 + 탐침 계약 digest 동결 → G12(문법을 모르는 설계자가 만든 새 블라인드 세계) |
| 2026-09-24 | **문법 v3 + 탐침 계약 동결 (G12 준비)** (1778→1787). B의 방법 4파일(`probe_grammar/induction/planning/research`) + 탐침 계약 3파일(`blind_probe`, `blind_probe_evaluator`, `probe_world`)을 내용 지문(sha256, 줄바꿈 정규화)으로 고정 — `tests/test_probe_v3_freeze.py`, 설명 `docs/current/PROBE_V3_FREEZE.md`(**G12 세계 설계자는 읽지 않음**). 깨지면 지문을 고치지 않고 새 버전을 만든다. **동결 직전 경계 구멍 2개 추가 수리**: `probe_research`/`blind_research_loop`의 import 사슬이 A의 입자 커널까지 닿음 — (1) `causal_executor`에서 `AExecutor`/`ExecutionResult`를 `execution.py`로, (2) `research_loop`에서 `seal_predictions`/`execute_through_a`를 `sealed_execution.py`로 분리(재수출로 기존 import 유지), 금지 목록에 `causal_kernel`/`kernel`/`physical_research_adapter` 추가. 남은 것(공개): 세계 기술 형식 `causal_spec`/`spec`은 `PredictionSeal` 경유로 여전히 닿음, 패키지 `__init__`이 실행 시 전 모듈을 올림(경계 테스트는 소스 의존성만 보장). 결함 주입 4종 전부 잡힘. **G12 착수 전 설계자 결정 대기**: RULES 자동 실행 예외를 탐침 세계로 넓힐지, G12 세계를 누가 설계할지 → 예외는 2026-09-24 결정·반영, 세계 설계자는 미정 |
| 2026-09-24 | **A/B/L 구조 기록 + causal v4 Stage B — 구조가 자기 운동을 소유** (1787→1827). 설계자 승인 순서(구조 문서화 → 발생 트랙의 병목 A). `STRUCTURE_STATE_V1.md`(2026-09-22 승인) 구현: `StructureState(members, momentum 벡터, motion_energy)`, v4 경로에서만. 구조 집합 = PortBond 연결 성분, 멤버는 운동 없음, 운동량·에너지 일치 검사, 카디널이면 한 몸으로 이동(인접·wrap 유지), 대각이면 이동 안 하고 `UnresolvedMotion`으로 보고, 구조–자유 입자 접촉은 미정의로 셀 수만 있게. **재명명 불변성**(id 치환·배열 순서·끝점 순서·규칙 순서, 6 tick 혼합 세계) 성립. v2의 '최저 번호 멤버' 결함은 레거시 파일로 이동. 결함 주입 11종 전부 검출(1종은 처음 놓쳐 테스트 보강). **한계: v4 안에서 구조가 생기거나 자라는 경로가 없다** — 지금 v4 구조는 손으로 만든 초기 상태에만 존재. 사슬 길이 3 천장·id 순서 성장은 v2 `_grow_chains`에 그대로이며, v4 성장은 접촉 그래프(기하 단계 5)가 만들어야 함. 다음: 기하 단계 5 설계(설계자 결정 필요) |
| 2026-09-24 | **중간 정리 (문서만, 코드 변경 없음).** 트랙 접두사 도입(A-V4.x / A-V4.GEO / B-Gx / L-Px)과 현재 판. 옛 'Stage D = 구조 이동'은 Stage B에 카디널 이동이 이미 들어가 의미가 충돌 → A-V4.GEO(접촉·생성·성장·구조–입자)로 재정의. RULES 자동 실행 예외를 blind 탐침 세계로 확장(설계자 결정, 조건 명시, B-G10/G11의 선행 자동 실행 소급 공개). REPO_MAP 갱신(테스트 1041→1827, B-classic 연구선 모듈·연구 저장소·탐침 세계·동결 테스트 반영). 순서: B-G12 → B-classic PARK → A-V4.GEO. B-G12의 남은 결정: 세계 설계자 |
| 2026-09-24 | **헌법 제26조 + 인간 현실재현 가능 신체 계약 v1 확정·동결** (1827→1830). 설계자 Q1~Q6 확정: 제26조(연구자 B의 관측·행동은 인간 감각 또는 세계 안에서 만든 도구로 재현 가능해야 함, 되감기 금지, 독립 표본) — **적용은 연구자 B만**, A 내부 주민·생명은 제17조(인간과 다른 감각 허용), 설계자·감사는 제15·24조(제24조에 'B에게 전달 금지' 문단 추가). RULES: 실험실 + 독립 표본 공급원 + B의 노트, 불변식 6개(state clone 금지 등), 신체 먼저·세계 나중, 두 손, B-classic 보존. 계약 1~8절을 지문으로 동결(`tests/test_body_contract_freeze.py`, 9절 '다음 결정 거리'는 편집 가능). 구현자 발견(9절): 모두가 이미 수화광맥 임계값을 봐서 Q4를 이 세계에 지킬 수 없음 → 감각 눈금을 실제 인간 생리값으로, 세계는 물리 단위를 선언하자는 제안. 작업 중 실수 1건: 결함 주입 정리에 `git checkout`을 써서 미커밋 계약 문서 편집이 날아감 → 같은 스크립트로 재적용, 동결 지문 일치로 동일성 확인 |
