# C1-B1 point prover generator 설계 V0

**상태:** 설계 제안(문서만). 코드 0. 설계자 승인 뒤 구현한다. **먼저 공개: 현재 checker V1은 실제 16384 STOP을 운영상 풀 수 없다(5절 측정, P-5).**
**현재 상태(변경 없음):** checker 신뢰 승인(`e9b30eb`), A-EV 미해결, ④-Safety Conditional, ④-Liveness NotCertified, ④ 전체 Certified/Frozen 아님, 실행기 cap 16384.
**근거:** 설계자 판정 2026-09-29(7차)의 원칙 1〜7, [checker 사양 V1](C1B1_EXACT_IMPULSE_CERTIFICATE_SPEC_V1.md), [Lemma A·B](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md), [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md).

## 0. 한 줄

point prover는 **checker가 받아 줄 certificate를 찾아 주는 비신뢰 생성기**다. 답을 정하는 권한은 없다.
성공의 정의는 하나뿐이다. prover가 만든 certificate에 대해 `check_certificate(cert)`가 `VALID(raw)`를 돌려주는 것이다.

## 1. 역할과 경계

| prover가 해도 되는 것 | prover가 하면 안 되는 것 |
|---|---|
| float·mpmath·휴리스틱·기존 탐색 코드 등 무엇이든 써서 후보를 찾는다 | 스스로 "성공"을 선언한다. checker의 VALID 없이 raw를 내놓는다 |
| raw를 **스스로** 추정한다. 실제 STOP에는 실행기가 준 raw가 없다 | 실행기 평가기(`C._model`, `C._decide`, `C.impulse`)를 부르거나 `C.MAX_PRECISION_BITS`를 바꾼다. 실행기 cap을 늘리는 프로그램이 되면 안 된다(원칙 3) |
| 싼 단계부터 시작해 필요한 만큼 올린다(원칙 4) | 처음부터 최대 정밀도로 계산한다 |
| 못 찾으면 못 찾았다고 말한다 | "못 찾음"을 "거짓"이나 "tie"로 바꿔 말한다 |

입력은 runtime wrapper가 넘겨주는, 실행기가 스스로 계산한 `(dr_raw, component, dt_kick)`다. prover는 입력을 만들거나 고치지 않는다.

## 2. 인터페이스

```
prove(dr_raw, component, dt_kick, budget) -> ProverResult
```

| status | 뜻 | 조건 |
|---|---|---|
| **FOUND** | certificate와 raw | checker가 그 certificate에 VALID(raw). 결과에 checker Result를 그대로 붙인다 |
| **NOT_A_DECISION** | 반올림 판정 대상이 아님 | dr_k = 0(실행기는 판정 없이 정확히 0), 또는 R < r_min(실행기는 판정 전에 `PhysicsDomainExceeded`) |
| **EXHAUSTED** | 운영 한도 안에서 아직 못 찾음 | 이유는 `prover_budget`(prover의 단계·시간 예산) 또는 `checker_refused:<limit>`(checker가 운영 한도로 REFUSED)다. **참/거짓에 대한 말이 아니다.** Lemma A+B는 유한한 단계에 certificate가 있다는 것만 주고, 현재 한도 안의 발견은 보장하지 않는다(원칙 5) |
| **ANOMALY** | prover의 예측과 checker가 모순 | 예: prover가 raw m으로 분리됐다고 예측했는데 checker가 `raw_mismatch`. 또는 checker가 예상 밖의 INVALID 이유를 냄. **재시도로 FOUND를 만들지 않고** 기록한 뒤 멈춘다. 두 구현 중 하나의 결함 신호다 |

runtime 계약 V1과의 연결(구현은 wrapper 단계): FOUND → WITNESS_RESOLVED, 나머지 셋 → STOP 유지(UNPROVED). EXHAUSTED는 한도를 올려 다시 시도할 수 있고, ANOMALY는 사람이 조사해야 한다.

## 3. 알고리즘 (권고안)

1. **판정 대상 확인:** dr_k = 0이거나 R < r_min이면 NOT_A_DECISION.
2. **추정(비신뢰):** 고정밀 부동소수점(mpmath)으로 J와, J에서 가장 가까운 half-ulp 경계까지의 거리 d를 구한다. 추정의 정밀도 p_est는 적응적으로 올린다. 추정 오차가 |d|보다 충분히 작아질 때까지 두 배씩 올리며, 그 결과로 후보 raw m을 정한다. mpmath 비용은 작다(5,600자리에서 0.2초 실측, 아래 5절).
3. **매개변수 선택:** √ 비트 N = max(128, ⌈−log₂ d⌉ + 여유 64)를 2의 거듭제곱으로 올림한다. exp 모드와 차수는 N에서 정한다(`full`, 멀면 `zero_floor`, 기존 탐색기의 휴리스틱).
4. **certificate 작성 → checker 호출:**
   - VALID(m) → FOUND.
   - `not_separated` → N을 두 배로 올려 3으로 돌아간다(추정의 여유가 부족했던 경우).
   - `raw_mismatch` 또는 예상 밖의 INVALID → ANOMALY.
   - REFUSED → EXHAUSTED(`checker_refused`).
5. **예산:** N이 checker의 `sqrt_bits_max`를 넘거나 prover의 단계·시간 예산이 끝나면 EXHAUSTED.

- **결정성:** 난수·시각 의존 분기가 없다. 같은 입력과 예산이면 같은 certificate를 낸다. 시간 예산은 결과를 잘라낼 수만 있다(가용성).
- **이 방식의 장점:** 비싼 exact 계산(checker)을 대개 **한 번만** 한다. 또 mpmath 추정과 checker라는 서로 다른 두 구현이 실제 운용 중에도 교차검증된다(ANOMALY 신호). mpmath 추정기는 교차검증 드라이버에 이미 있는 세 번째 구현을 prover 모듈로 옮겨 쓴다. 상수는 checker 상수표를 읽는다.

## 4. 설계 선택지 — 추정 엔진 (P-1)

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **(c) mpmath 추정 + checker 1회 (권고)** | 3절 | 비싼 exact 계산이 한 번이다. 두 구현의 불일치를 ANOMALY로 잡는다 | mpmath 추정기라는 비신뢰 코드가 하나 더 생긴다(틀려도 checker가 막고, ANOMALY로 드러남) |
| (a) checker 내부 루틴 재사용 사다리 | N = 128, 256, …마다 checker와 같은 exact 구간을 prover가 계산해 분리되면 제출 | 추가 수학 코드가 없고, prover의 예측이 checker와 항상 같다 | exact 계산을 두 번 한다(prover가 한 번, checker가 한 번). N이 크면 비싸다(5절). 불일치 신호가 거의 사라진다 |
| (b) 기존 탐색기처럼 N만 두 배씩 올리며 매번 checker 호출 | 가장 단순 | 코드가 가장 적다 | 깊은 near-tie에서 비싼 checker 호출을 여러 번 한다. raw 추정이 따로 필요하다 |

## 5. 비용 사실 (구현 전 측정, scratchpad, 저장소 코드 아님)

**실제 실행기 cap을 넘는 합성 사례를 만들 수 있다.** R ≈ 4.4 bohr 입력에서 `dt_kick`을 17,604-bit 유리수로 골라 정확값이 경계에서 2^-17000 ulp 떨어지게 했다. 실행기는 **cap 16384에서 `ReferenceUndecided`**를 냈다(13.0초). 구성 비용은 mpmath 5,600자리에서 0.2초였다.

그런데 이 합성법에는 두 가지 운영 문제가 있다.
1. `dt_kick`이 약 5,300자리라 checker의 `digits_max`(4300)에 걸려 **기본 한도로는 REFUSED**다. Python 자체 변환 한도도 넘는다. 실제 runtime 입력은 dt_kick = 20, dr_raw ≤ 약 30자리이므로 이것은 **합성 방법의 문제**이며 실제 STOP의 certificate는 작다.
2. checker의 `full` 모드 exp 급수는 반올림하지 않는 정확 유리수 계산이다. 그래서 끝점 분모가 2^N인 급수의 수 크기가 차수 n × N비트로 커지고, 비용이 대략 n²N²로 늘어난다. 측정(같은 2^-17000 입력, 현재 checker V1, 로컬 1 프로세스). 모두 분리 부족(`not_separated`)이라 INVALID였고, 시간만 본다:

| √ 비트 N | 시간 | 최대 정수 크기 | 최대 exp 차수 |
|---|---|---|---|
| 256 | 2.6초 | 0.41 Mbit | 198 |
| 512 | 14.6초 | 1.11 Mbit | 284 |
| 1024 | 104.8초 | 3.33 Mbit | 428 |
| 2048 | 871.3초 | 10.6 Mbit | 672 |

N이 두 배가 될 때 시간은 5.6배, 7.2배, 8.3배로 늘어 대략 **N³**에 가깝다. N=4096은 약 2시간으로 예상돼 중단했다. 첫 시도(N=8192)는 40분 안에 끝나지 않았다. 외삽하면(측정 아님) N=16384는 수일, 이 사례에 필요한 N ≈ 17,000 이상은 몇 주다.

**해석 — 먼저 공개할 결론:** **현재 checker V1로는 실제 16384 STOP을 사실상 풀 수 없다.**
- 실제 STOP은 정의상 정확값이 경계에서 약 2^-16300 ulp 안에 있을 때 생긴다. 그러면 certificate에 N ≳ 16,400이 필요하고, 현재 비용으로는 며칠〜몇 주다. 기본 운영 한도(√ 4096 bit, 300초)에서는 EXHAUSTED(`checker_refused`)로 끝난다.
- 반대로 **실행기는 같은 입력을 cap 16384까지 13초에 계산한다.** 실행기 평가기는 구간 끝점을 dyadic으로 반올림하기 때문이다. 즉 지금은 **correctness path가 fast path보다 운영상 짧다.** 정성적 Liveness(Lemma A+B)는 수학적으로 맞지만 현실에서는 쓸 수 없는 상태다.
- cap 128 rehearsal과 near-tie 2^-300 정도까지는 문제가 없다(교차검증에서 near-tie 2^-140의 certificate는 5.7초).
- 원인은 checker가 정확 유리수를 반올림 없이 끝까지 들고 가는 것이다. 수 크기가 차수 × N비트로 커진다. 표준 해법은 **구간 끝점을 바깥쪽 dyadic으로 반올림**(아래 끝은 내림, 위 끝은 올림)해 수 크기를 O(N)으로 묶는 것이다. 건전성은 유지되고 여전히 정확한 정수 산술이다. 실행기 평가기가 16384 bit를 13초에 계산하는 것이 이 방식의 비용 감각이다(checker에서의 측정은 아님).
- 이것은 **checker 사양 변경(V2)**이다. 신뢰 승인된 V1 코드를 바꾸는 일이므로 설계자 판정(P-5)이 필요하다. V2도 P1b 독립성을 지켜야 한다. `a_numeric.exp.enclosure`를 재사용하지 않고, 반올림 방향과 argument reduction을 checker 안에서 독립 구현하며, 같은 T1〜T11과 교차검증을 다시 통과해야 한다.

## 6. 검증 계획 (원칙 6: 첫 검증은 runtime 연결 없이)

| # | 시험 | 통과 조건 |
|---|---|---|
| V1 | **cap 128 rehearsal**: witness prototype의 실제 궤적 3개(1,640 / 5,775 / 21,056 step)를 cap 128로 돌려 생기는 모든 STOP 입력에 prove | 전부 FOUND. raw = full-cap 실행기 raw. STOP 수 = 정상 실행의 256-bit 판정 수 |
| V2 | near-tie 합성 사다리 2^-10〜2^-300 ulp, 경계 위/아래, 여러 R·성분 | 전부 FOUND, raw = 기대값. 선택된 N이 거리와 함께 커짐 |
| V3 | 실제 cap을 넘는 합성(2^-17000, P-2) | 실행기 cap 16384에서 `ReferenceUndecided`(13초 실측). **checker V1에서는** 기본 한도로 EXHAUSTED(`checker_refused`)만 시험할 수 있다(`dt_kick`이 digits_max 초과, √ 비트가 한도 초과). FOUND까지 가는 시험은 checker V2 뒤에만 현실적이다 |
| V4 | 결함 주입: raw를 ±1로 바꾸는 prover, checker를 건너뛰는 prover, not_separated를 FOUND로 처리하는 prover | 각각 ANOMALY 또는 시험 실패로 잡힘. FOUND에는 항상 checker Result가 붙고, 시험이 그 certificate를 checker로 다시 판정 |
| V5 | 정적 검사: prover가 실행기 평가기를 부르지 않음, `MAX_PRECISION_BITS`를 쓰지 않음 | AST 검사 |
| V6 | 결정성: 같은 입력·예산이면 certificate 바이트가 동일 | 두 번 실행 비교 |
| V7 | EXHAUSTED와 REFUSED 구분: prover 예산 소진 vs checker 한도 거부가 서로 다른 이유로 보고됨. 어느 쪽도 FOUND/거짓으로 보고되지 않음 | 한도 조합 시험 |
| V8 | NOT_A_DECISION: dr_k = 0, R < r_min | 실행기와 같은 분류 |

## 7. 범위 밖

runtime wrapper, Proof Cache, certificate 바이트 크기 상한(wrapper 과제), checker V2(dyadic 반올림), A-EV, trajectory-completion, VMHalt 정리. checker 코드는 건드리지 않는다.

## 8. 설계자 확인 요청

| # | 질문 | 구현자 권고 |
|---|---|---|
| P-1 | 추정 엔진(4절) | **(c) mpmath 추정 + checker 1회.** 불일치를 ANOMALY로 드러내는 운용 중 교차검증이 덤으로 생긴다 |
| P-2 | V3(실제 cap을 넘는 합성)을 시험에 넣을지 | **넣는다. 단 V1에서는 EXHAUSTED 분류만**(빠름: 실행기 13초 + checker의 즉시 REFUSED). FOUND 시험은 P-5 뒤로 미룬다 |
| P-3 | prover 예산 기본값 | checker 기본 한도와 맞춘다(√ 4096 bit). 시간 예산은 구현 시 실측해 기록한다(S4와 같은 방식). 운영 한도는 가용성만 바꾼다 |
| P-4 | ANOMALY에서 멈출지 | **멈춘다.** 재시도로 FOUND를 만들면 두 구현의 불일치가 조용히 사라진다 |
| **P-5** | **checker V2(바깥쪽 dyadic 반올림)를 prover 전에 할지, 뒤에 할지** | **prover V0를 먼저 만든다(cap 128 rehearsal·near-tie로 구조 검증). checker V2는 그다음, 별도 설계·판정으로.** 이유: prover 구조의 오류는 V1로도 다 드러나고, V2는 신뢰 승인된 코드를 바꾸는 더 무거운 일이다. 다만 **V2 없이는 실제 16384 STOP에 대해 WITNESS_RESOLVED가 현실적으로 불가능**하므로, ④-Liveness를 실용적으로 주장하려면 V2가 필수다 |
