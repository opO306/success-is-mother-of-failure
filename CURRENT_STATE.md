# 현재 상태

**최종 갱신:** 2026-09-22
**검증:** 전체 테스트 1046개 통과
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
