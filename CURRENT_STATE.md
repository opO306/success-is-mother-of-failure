# 현재 상태

**최종 갱신:** 2026-09-21
**검증:** 전체 테스트 892개 통과
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
| 결정론 화학·고분자 | 미착수 | 환경 기반까지만 |

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
- `independent_compliance/` — **명세 준수.** 막힌 벽·순간이동·한도 초과 등
  "총량은 맞는데 경로가 틀린" 위반 탐지
- 셋 다 결함 주입으로 실효성 확인됨 (`docs/VERIFICATION_LIMITS_AND_LESSONS.md`)

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

---

## A의 근본적 한계

현재 A는 초기 지구 화학이나 생명 발생을 시험할 수준이 **아니다.**

- 입자당 결합 하나
- 결합 구조 정지
- 다중 화학 중간체 없음
- 촉매 구조 없음
- **고분자 없음**
- **주형 기반 복사 없음**
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

세 방향이 열려 있고 **아직 선택되지 않았다.**

### (가) held-out v2 — B를 계속 판다

1. ~~독립 trace parser 구현~~ **완료 (2026-09-21)** — `audit/independent_trace/`
2. **후보별 수치 예측 봉인** ← 다음 차례
   세 후보(관측 pipeline / vapor 변수 추가 / vapor 관계 모델)가
   "heldout-vapor-5의 어느 위치에서 vapor가 얼마→얼마"를 각각 예측하게 하고 해시로 봉인
3. 위치·열 경계·격자 크기까지 바꾼 강한 held-out spec
4. v2 생성 (v1은 보존)
5. 사용자 승인 후 실행

### (나) A 화학·고분자 — 세계를 키운다 *(작업 묶음 4)*

- 결정론 화학, 고분자, 경계, 독립 분열
- **완료 데모:** 고수준 복사·분열 명령 없이 실제 충돌 과정이 고분자와 두 독립 경계를 만들거나 실패한다

현재 B가 "수작업 규칙 모델"이라 아무리 다듬어도 자율 발견이 안 나오는 점, A가 단순해서 B가 풀 흥미로운 문제 자체가 없는 점을 고려하면 이쪽이 원래 목표에 더 가깝다.

### (다) 기술 부채 정리

- 공개 stage API
- 평가 상태 플래그 분리

### (라) 감사 확장

- vault trace 중 `spec.json` 없는 8개는 보존·준수 감사 불가 → 이후 실행은 spec을 함께 저장
- ~~명세 준수 검증~~ **완료 (2026-09-21)** — `audit/independent_compliance/`
- 남은 미검증: 입자 충돌·결합 규칙 준수, 세밀한 이동량 공식

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
