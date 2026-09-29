# C1-B1 Runtime Rounding Contract V1 — 제안

**문서 상태: PROPOSAL / 설계자 승인 전.** 이 문서를 근거로 코드를 바꾸지 않는다. 승인 전에는 실행기·인증서·coverage·D_valid를 한 줄도 바꾸지 않는다.
**현재 상태(변경 없음):** coverage 14/64 region·gap 81, ④-4b NotCertified, ④ 미동결, ⑤ 미착수, 정밀도 cap 16384.
**근거:** [실행 기반 정밀도 조사](C1B1_RUNTIME_STRESS_SURVEY_V1.md), [Fail-Closed v0 + 국소 witness prototype](C1B1_RUNTIME_FAIL_CLOSED_V0.md), 설계자 판정(2026-09-29).
**관련 제안:** [A 실행 증명서](../proposals/A_RUNTIME_CERTIFICATE_PROPOSAL.md)(Proof Atom→Segment→Box→Domain),
[증명 조립 아키텍처](../proposals/A_PROOF_COMPOSITION_ARCHITECTURE_V1.md), Warehouse 설계(별도 브랜치 `claude/proof-warehouse-architecture-skrgwm`, 구현 보류).

## 0. 한 줄 요약

반올림 완전성(④-4)을 **사전 전수 인증**이 아니라 **실행 중 판정 + 판정 불가 시 정지 + 그 지점만 국소 증명**으로 다룬다.
버리는 것은 "shell마다 수억 개 경계를 미리 열거하는 방법"뿐이다. **④의 의무는 약화하지 않는다.** ④를 Safety와 Liveness로 나누고, 둘 다 닫혀야 ④가 끝난다.

## 1. 네 상태

판정 단위는 **충격량 한 성분의 반올림 판정**이다. step 단위 결과는 그 step 안의 모든 판정 상태로 정해진다.

| 상태 | 뜻 | 세계 진행 | 현재 코드 |
|---|---|---|---|
| **RESOLVED** | 실행기가 계약 schedule(128→256→…→16384) 안에서 구간 양 끝이 같은 raw로 반올림됨을 직접 확인 | 진행 | `C._decide` 반환 |
| **STOPPED** | 16384까지도 판정 불가. step 전체를 버리고 run은 **정지 전 그대로** | 멈춤 | `ReferenceUndecided` + Fail-Closed v0 시험 |
| **WITNESS_RESOLVED** | 바로 그 입력(상대 위치·성분·binding)에 대해 **검증된 국소 witness**가 있음 | 같은 step을 **처음부터** 재실행하고, 그 입력에서만 witness 값을 씀 | prototype만 존재(시험 설정 cap 128). **실제 cap에서 승인된 witness 방법은 아직 0개** |
| **UNPROVED** | 국소 prover도 해결 못 함 | **절대 진행하지 않음.** run은 STOPPED 상태로 끝나며 결과를 "실행기 정지"로 기록 | 해당 경로 없음 = 현재 모든 실제 STOP의 결말 |

규칙:
- STOPPED에서 벗어나는 길은 WITNESS_RESOLVED 하나뿐이다. 더 높은 cap으로 몰래 다시 돌리거나, 가까운 값·통계·Hazard Atlas(6절)로 채우는 경로는 없다.
- WITNESS_RESOLVED는 **실행기가 스스로 계산한 입력**이 witness의 입력과 정확히 같을 때만 성립한다. witness가 입력을 정하지 않는다.
- 이 네 상태는 **반올림 판정**에만 적용된다. `PhysicsDomainExceeded`, `IntegratorDomainExceeded`, 위치/운동량 범위 초과(`ExecutorLimitExceeded`), `_decide`의 같은 쪽 실제 overflow(`VMHalt`)는 witness로 풀지 않는 **종결 거부**다. Fail-Closed(run 불변)만 적용된다.
- 입장 검사(`check_integrator_domain`, E_rel ≤ 10 De)의 판정 불가도 `ReferenceUndecided`다. run이 만들어지지 않으므로 이 계약의 witness 경로 밖에 둔다(별도 결정 전까지 UNPROVED와 같이 취급).

## 2. ④를 두 조각으로

| | ④-Safety | ④-Liveness |
|---|---|---|
| 질문 | 애매한 반올림으로 **틀린 세계 상태를 만들지 않는가** | 인정한 C1-B1 영역의 모든 실행에서 **필요한 판정이 결국 모두 해결되는가** |
| 기차 비유 | 모르는 철길을 무시하고 지나가지 않는다 | 허용된 모든 기차가 목적지까지 간다 |
| 현재 | prototype과 시험으로 상당히 확인. 아래 S1〜S6을 채우면 완료 후보 | **NotCertified** |

**④ 전체 동결 = ④-Safety 완료 + ④-Liveness 완료 + 설계자 판정.** 둘 중 하나만으로 ④를 동결하지 않는다.

### 2.1 ④-Safety 완료 조건

| # | 조건 | 현재 |
|---|---|---|
| S1 | **Fail-Closed:** 모든 거부에서 run이 불변(`vars(run)` 비교, validation 캐시 미접근) | v0: 판정 불가(첫 충격량·kick/drift 뒤), drift 선분, 위치 범위 확인. **남음:** `_decide`의 실제 overflow(`VMHalt`) 경로, 운동량 범위 초과 |
| S2 | **RESOLVED의 정확성:** 실행기 판정 = 정확한 모델 값을 한 번 반올림한 값 | **평가기 구간이 참값을 감싼다는 전제(A-EV)에 조건부.** 아래 한계 참조 |
| S3 | **witness 계약:** binding 전체(7절), 입력 키, 빌더와 다른 검증 경로, 저장 형태 검증, 변조 거부, binding이 하나라도 다르면 stale | prototype에서 변조 15종 거부 확인. 실제 cap용 witness 방법은 없음 |
| S4 | **UNPROVED에서 진행하는 코드 경로가 없음:** RESOLVED/WITNESS_RESOLVED가 아닌 판정으로 step을 확정하는 경로 0개. 결함 주입(강제 진행 변형)을 시험이 잡음 | prototype의 "witness 없이 재개" 결함 주입은 잡힘. 정식 경로의 시험은 없음 |
| S5 | **차등 회귀 시험:** 기준 실행이 존재하는 모든 경우(cap을 낮춘 rehearsal 등) 매 step raw 상태가 기준 실행과 비트 동일, witness 수 = 거부 수 | prototype 3궤적(1,640 / 5,775 / 21,056 step) 동일 |
| S6 | **비간섭:** Proof Cache·Hazard Atlas를 켜고 끈 결과가 같다. 단 Proof Cache는 STOPPED를 WITNESS_RESOLVED로 바꾸는 것만 할 수 있다 | 미구현 |

**S2의 한계 (먼저 공개):** RESOLVED가 옳다는 것은 "구간 양 끝이 같은 raw로 반올림됨"과 "평가기 구간이 참값을 감쌈(A-EV)"의 결합이다.
A-EV는 지금까지의 모든 인증서가 공유하는 전제이며, 전 입력에 대해 증명된 것이 아니다. 과거에 EXP 고정 cutoff가 높은 정밀도에서 틀린 구간을 준 결함이 실제로 있었다([rounding-decision](C1B1_ROUNDING_DECISION_V1.md) 2.1절).
따라서 ④-Safety의 완료는 "A-EV 아래에서"이며, A-EV 자체의 강화(예: 독립 구간 힘 평가기)는 별도 과제로 남긴다. audit의 독립 Lang 모델은 V만 구간으로 감싸고 힘은 수치 미분이라 지금은 A-EV를 독립 검증하지 못한다.

### 2.2 ④-Liveness 완료 조건

**대상 영역을 먼저 정해야 한다(설계자 결정 L0).** 후보: (a) 입장 계약 전체(E_rel ≤ 10 De, b < R_START), (b) D_valid `numerical_validated` 영역, (c) 그 사이의 명시 영역.

주장: 그 영역의 모든 초기 상태에서, 종료 조건(R_J로 나가 tail에 인계, 또는 선언된 다른 끝)까지 **모든 판정이 RESOLVED 또는 승인된 방법의 WITNESS_RESOLVED**이다.

| 증거 | 상태 | 비고 |
|---|---|---|
| tail(R ≥ R_J = 10,240 bohr) | 형식 인증(최대 512 bit) | 기존 |
| outgoing shell 16〜26 | 형식 인증(14/64 region) | R=20 기준 enclosure에 대한 것 |
| shell 0〜15의 gap 81 | **미인증** | 전수 hard-case 방식은 shell 15에서 STOP |
| 안쪽(R < 20)·inbound | 형식 liveness **없음** | 기존 ④ 범위 밖이기도 함 |
| 실행 조사(약 2.3억 판정, 바깥 비행 포함) | STOP 0 | **survey_only.** 증명 아님 |

닫는 길(설계자가 고른다. 지금 결정하지 않는다):
- **L-a** 기존 전역 경로: gap 81을 더 싼 수학(lattice/SLZ 등)으로 닫는다.
- **L-b** 실행 단위 liveness: "이 실행은 모든 판정이 해결되어 끝났다"를 실행 증명서로 남긴다. 영역 전체의 liveness보다 **약하다.** ④-Liveness의 대체로 쓰려면 ④의 정의를 바꾸는 것이므로 설계자 판정이 필요하다.
- **L-c** "UNPROVED 정지 가능성을 허용하는 조건부 계약": ④를 약화하는 것이다. 설계자 방침(④ 의무 약화 금지)과 충돌하므로 **권하지 않는다.** 기록만 한다.

## 3. 차등 비교의 역할 분리

| 층 | 강제하는 것 | 이유 |
|---|---|---|
| 개발·회귀 시험 | 기준 실행이 존재하는 모든 경우 **매 step raw 상태 비트 동일**, witness 수 = 거부 수 | 마지막 상태만 비교하면 중간에 다른 길로 갔다 돌아온 것을 놓친다 |
| 실제 runtime 계약 | **같은 입력 + 검증된 witness → 정확히 그 rounding 결과만 허용** | 실제 16384 STOP에서는 비교할 "정상 16384 기준 실행"이 존재하지 않는다 |
| 결함 주입(상시 유지) | 틀린 witness, witness 없는 재개, 다른 입력용 witness, stale binding을 모두 잡는다 | 검사기가 눈을 감고 있지 않은지 |

차등 비교는 **시험 계약**이지 runtime의 수학적 정의가 아니다.

## 4. 국소 prover (설계만 — 이번 문서 승인 뒤 별도 설계)

입력: 상대 위치 dr, 성분 k, kick 간격, momentum profile, binding. 출력(검증 가능한 주장 중 하나):
- "정확한 값은 half-ulp 경계 b의 **왼쪽/오른쪽**에 있다 → raw = X"
- "정확한 값은 b와 **정확히 같다**(tie) → half-even 결과 raw = X"
- 해결 못 함 → UNPROVED

후보 방법(비용 낮은 순, 실제 STOP이 난 한 점에만 적용하며 shell 전체에 미리 뿌리지 않는다):
1. 기존 rational/modular-distance 기법의 **한 점 판**: 충격량의 유리식 부분 P/Q와 경계의 정확한 거리(≥ 1/(2Q)형 하한)와 지수 잔여항·수치 오차 상한을 비교. shell 19〜23 family 인증에서 쓴 방식의 점 버전.
2. 정확한 tie 판정: tie가 가능한지 유리식·valuation으로 판정(④-4b fractional phase 조사에서 24/24 domain의 rational tie를 배제한 방법의 점 버전).

**설계자 결정 필요(P1):** 별도 prover가 16384보다 높은 정밀도의 **구간**으로 한 점의 경계 쪽을 증명하는 것을 허용하는가.
수학적으로는 타당한 증명이지만, 계약의 "cap 상향 금지"를 우회하는 것으로 볼 수도 있다. 설계자 방침("더 높은 bit로 몰래 뚫지 않는다")에 따라 **기본값은 불허**로 둔다.

각 방법은 채택 전에 자기 checker(빌더와 다른 경로)와 결함 주입 시험을 가져야 한다. 방법이 하나도 승인되지 않은 동안 모든 실제 STOP은 UNPROVED다.

## 5. Proof Cache — 재사용 가능한 실제 증명

- **넣는 것:** 실제 cap(16384)에서 STOPPED였고, 승인된 prover가 만든 뒤 검증된 witness **만**. 128→256처럼 실행기가 스스로 푼 판정은 넣지 않는다(실측 약 0.64%, 2억 판정이면 백만 건 이상 — 넣으면 창고가 철길보다 커진다).
- **쓰는 때:** 실행기가 STOPPED를 낸 입력에 대해서만 조회한다. 실행기의 계산을 건너뛰는 용도가 아니다.
- **쓸 때마다** binding 일치 확인 + witness 전체 재검증(Warehouse Q3 "④ 동결 전 full re-verify"와 같은 원칙). 저장된 `status`를 믿지 않는다.
- binding이 하나라도 다르면 STALE — 쓰지 않고 다시 증명한다. 지우지 않는다(STALE·REJECTED 보존).
- **Proof Box 승격:** 여러 witness가 한 구간에 모이면, 그 구간 **전체가** 같은 반올림 결과를 가진다는 구간 증명(기존 multi-output region·hard-case 인증서와 같은 종류)이 있을 때만 box로 올린다. "비슷해 보여서" 묶지 않는다.
  box가 있으면 그 안의 처음 보는 입력의 STOP도 box로 풀 수 있다. 이미 인증된 14개 region은 이 의미의 box/domain이다.
- 저장 형식: prototype witness는 `runs/`에만 둔다(fixture 아님). 정식 Proof Cache의 형식·위치는 첫 승인된 prover와 함께 정한다.

## 6. Hazard Atlas — 통계 지도 (증명 아님)

- 내용: 판정의 R 구간·성분·최종 정밀도·128-bit 구간 폭 분포, 높은 정밀도(예: ≥ 4096 bit) 판정과 모든 STOP의 위치 목록. 이번 조사 결과(R 20〜320은 0.6%대, 320〜640 전환, ≥ 640은 항상 256)가 첫 내용이다.
- 쓰임: prover 작업 우선순위, 캐시 예열, 비용 예측. **어떤 판정도 대신하지 않는다.** 인증 입력 금지(Warehouse의 `survey_only`와 같은 지위).
- 시험: Atlas를 켜고 끈 실행 결과가 비트 동일해야 한다(S6).

## 7. witness binding (필수 필드)

모델 지문(`L.parameter_fingerprint()`), C1-A 동결 지문, 실행기·모델 소스의 LF 정규화 SHA-256, 위치/운동량 profile(이름·폭·소수 비트), dt, kick 간격, drift 규칙, retardation, 반올림 방식(half-even), 정밀도 schedule(128…16384), 정확한 입력 위치(유리수), 성분 축, **proof method와 그 checker의 해시**.
prototype은 proof method 필드가 없다(방법이 하나뿐). 정식 witness에는 추가한다.

## 8. 기존 원칙과의 충돌 — 설계자 판단 필요

| # | 충돌 | 내용 | 구현자 의견 |
|---|---|---|---|
| C1 | Warehouse 8절 "Warehouse는 A의 실행 경로에 없다" | Proof Cache는 STOPPED 때 **실행 중에** 조회된다 | Proof Cache를 Warehouse와 **분리된 작은 저장소**로 두고, runtime 역할을 "STOPPED 입력에 재검증한 witness로 답하기"로 한정한다. Warehouse는 실행 경로 밖에 그대로 두고 Proof Cache artifact를 색인만 한다 |
| C2 | 헌법 제2조(과정 보존)·RULES "캐시는 인과 영향 반경 전체의 정확한 입력이 같을 때만" | witness는 계산을 생략하는 것이 아니라, 실행기가 무한 정밀도라면 냈을 **바로 그 값**을 증명으로 제공한다. 입력 키가 충격량 입력 전체(상대 위치 전 성분 + binding)다 | 충돌 없음으로 본다. 다만 "캐시"라는 이름이 오해를 부를 수 있어 문서에서는 "Proof Cache = 증명 저장, 계산 캐시 아님"으로 못 박는다 |
| C3 | ④ 동결 조건 | 기존 ④는 "reachable enclosure 전체의 사전 인증"을 요구했다 | 이 제안은 **방법**을 바꾸고 **의무**는 Safety+Liveness로 유지한다. Liveness를 무엇으로 닫을지(L-a/L-b)는 설계자 결정 |
| C4 | Proof Warehouse 보류 결정 | "반올림 전략이 바뀌면 저장할 proof의 양·종류도 달라진다"는 이유로 보류했다 | 전략이 바뀐 지금, 저장 대상은 **실제 STOP의 witness와 box뿐**이라 훨씬 작다. Warehouse v0 재개 여부는 첫 실제 witness가 생긴 뒤 판단해도 늦지 않다 |

## 9. 설계자 결정 항목 요약

| # | 질문 | 구현자 권고 |
|---|---|---|
| D1 | 네 상태와 규칙(1절)을 계약으로 채택 | 채택 |
| D2 | ④를 Safety/Liveness로 나누고 둘 다 있어야 ④ 동결(2절) | 채택 |
| D3 | ④-Safety가 A-EV에 조건부임을 명시하고, A-EV 강화는 별도 과제로 둠 | 채택 |
| L0 | ④-Liveness의 대상 영역 | 설계자 결정 |
| D4 | Liveness를 닫는 길(L-a / L-b) | 첫 prover 설계 뒤 결정. L-c는 권하지 않음 |
| P1 | 별도 prover의 16384 초과 구간 증명 허용 여부 | 기본 불허 |
| D5 | 차등 비교를 개발·회귀 시험 계약으로 두고 runtime 계약은 "같은 입력+검증된 witness"로(3절) | 채택 |
| D6 | Proof Cache를 Warehouse와 분리하고 STOPPED 입력에만 쓰기(C1) | 채택 |
| D7 | Hazard Atlas는 survey_only, 결과 비간섭 시험 필수 | 채택 |

## 10. 승인 뒤 순서 (제안)

1. S1의 남은 Fail-Closed 시험(`VMHalt` 경로, 운동량 범위) 추가 — 몇 초짜리, 실행기 무변경.
2. 네 상태를 코드 상수·결과 기록으로 표현하는 **얇은 runtime wrapper** 설계(실행기 무변경, prototype 대체).
3. 국소 prover 방법 1(유리식 한 점 판) 설계 문서 → 승인 뒤 구현. 실제 STOP이 없으므로 cap을 낮춘 rehearsal과 합성 사례로 시험한다.
4. Proof Cache·Hazard Atlas는 첫 승인된 prover가 생긴 뒤.

이번 문서로 바꾸는 코드는 없다. 궤적 추가 주행·shell 14 탐색도 하지 않는다.
