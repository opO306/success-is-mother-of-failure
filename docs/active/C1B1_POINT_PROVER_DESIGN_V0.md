# C1-B1 point prover generator 설계 V0

**상태:** 설계 + **V0 구현·시험·검증 완료(9절). V0 승인(설계자 판정 2026-09-30)**, 추정 overflow를 NOT_A_DECISION에서 `EXHAUSTED("estimate_out_of_output_range")`로 정정([wrapper V0](C1B1_RUNTIME_WRAPPER_V0.md) 6절).  **먼저 공개: 현재 checker V1은 실제 16384 STOP을 운영상 풀 수 없다(5절 측정, P-5).** 후속: checker V2가 구현·신뢰 승인됐고([V2](C1B1_EXACT_IMPULSE_CHECKER_V2_DESIGN.md) 9.7), prover V0가 같은 2^-17000 사례를 스스로 raw를 찾아 위·아래 모두 첫 시도에 VALID로 풀었다(9절).
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

## 9. 구현 결과 V0 (2026-09-29, 기준 HEAD `1baedc8`)

승인된 방향(설계자 판정 8차): checker V2 신뢰 승인 → Point Prover V0. 아래는 V2 checker 위에 구현한 V0의 결과다. runtime wrapper·Proof Cache는 하지 않았다.

### 9.1 파일과 설계에서 정한 것

- `a_reference/c1b1_point_prover.py`(prover), `a_reference/c1b1_point_prover_survey.py`(검증 드라이버), `tests/test_c1b1_point_prover.py`(24개). **checker V1·V2, 실행기, 평가기, 동결 계약은 변경하지 않았다.**
- 설계 P-1〜P-4는 권고대로 확정했다. **(c) mpmath 추정 + checker 1회**(P-1), 실제 cap을 넘는 합성은 검증(P-2), 예산 기본값은 운영 초기값(P-3), ANOMALY는 재시도하지 않고 기록한 뒤 멈춘다(P-4). P-5(checker V2)는 승인·구현됐다.
- prover는 checker V2 모듈만 import한다(상수·`check_certificate`용). 실행기, C1-A 평가기, `MAX_PRECISION_BITS`, V1 checker는 참조하지 않는다(AST 시험).
- **알고리즘 변경(설계 3절 대비):** N 증가를 두 배가 아니라 3/2배(64의 배수)로 하고, 첫 N을 추정한 거리에서 정한다: `N = round64(max(128, d_bits + y_bits + 40))`, `P = N + 96`. 40과 96은 이 **비신뢰 생성기의 휴리스틱**이다(근거: 측정된 enclosure 폭이 약 |y|·2^(−N)·2^7 ulp이고 반올림 항을 폭보다 작게 유지). checker는 어떤 N·P에서도 건전하다. exp 모드·차수는 생성기 안의 부동소수점 추정으로 고른다(검증 보조 모듈 `c1b1_exact_impulse_search`와 같은 방식이지만 prover가 자기 것을 갖는다).
- 추정기: 두 정밀도(p, 2p)의 mpmath 값이 경계까지 거리 d보다 훨씬 작게 일치할 때까지 p를 두 배씩 올린다. 이 수락 규칙은 **휴리스틱**이다(엄밀한 오차 상한이 아님). 틀리면 checker가 `raw_mismatch`로 거부하고 결과는 ANOMALY가 된다. 추정기 자체의 mpmath 식은 prover 안에 따로 옮긴 것이며, 교차검증 드라이버의 mpmath 구현과 일치함을 시험한다.

### 9.2 시험 24개 (35초)

| 시험 | 내용 |
|---|---|
| FOUND = 실행기 | 결정적 표본(안쪽·축·바깥·먼 점·65점·hard-case·shell 24〜26)의 모든 성분에서 FOUND, 실행기 raw와 같고, FOUND는 항상 checker로 재검증됨. dr_k = 0인 성분은 NOT_A_DECISION |
| cap-128 rehearsal | 실제 궤적 2개(1,640 / 5,775 step)에서 cap 128이 거부한 충격량 전부를 **실행기 raw를 받지 않고** 해결 |
| near-tie 사다리 | 경계에서 2^-10〜2^-1000, 위·아래, 4개 입력. prover가 raw와 거리(`dist_bits`)를 스스로 찾고, 필요한 √ 비트가 거리와 함께 커짐 |
| 깊은 near-tie | 2^-4000 위·아래 FOUND |
| 추정기 일관성 | prover의 mpmath 식 = 교차검증 드라이버의 mpmath 구현 |
| NOT_A_DECISION | dr_k = 0, dt = 0, R < r_min, 위치 프로필 밖, 값의 overflow. 잘못된 입력 형식은 ValueError |
| EXHAUSTED | 2^-17000: Python 자릿수 한도에서는 `serialization_limit`, 한도를 풀면 checker가 `integer_size_limit`로 REFUSED. prover 예산(√ 비트, 시도 수, 시간)과 checker REFUSED가 서로 다른 이유로 보고됨. 느슨한 예산·한도에서는 같은 raw로 FOUND(**가용성만 바뀜**) |
| ANOMALY | 틀린 raw(+1, −1, +5)를 추정하면 checker를 **정확히 1회** 부른 뒤 ANOMALY. 예상 밖 INVALID(exp_condition)도 ANOMALY, 재시도 없음 |
| 정적·결정성 | import 집합과 금지 이름 검사. 같은 입력·예산이면 certificate 바이트와 시도 기록이 동일 |
| 결함 주입 | checker를 건너뛰는 prover, not_separated를 성공으로 처리, ANOMALY를 재시도로 덮음, REFUSED 무시, 거리 측정 상실 — 전부 시험이 잡음 |

**먼저 공개(시험 과정의 실패 두 건):**
1. 처음 전체 실행이 25분 걸렸다. 원인은 **시험 설계**였다. "ANOMALY를 재시도로 덮는 결함" 변이체가 틀린 raw로 √ 비트를 1.5배씩 키우며 예산 상한(65536)까지 checker를 돌려, 뒤쪽 시도가 수 분〜수십 분씩 걸렸다. 변이체의 시도 수를 4로 제한해 35초로 줄였다. prover 결함이 아니다.
2. 2^-17000 시험에서 `dist_bits`를 17000으로 기대했으나 17001이 나왔다. `dt_kick` 양자화 때문에 거리가 2^-17000보다 아주 조금 작다. 기대값 오류였고 다른 시험처럼 ±1을 허용하도록 고쳤다.

### 9.3 검증 캠페인 (survey_only, 로컬 6 워커, 약 318초 + 2^-17000)

증거: `runs/c1b1_point_prover_20260929/`. **prover는 raw를 받지 않는다.**

**1단계 표본: 2,660 성분 판정, 전부 FOUND, checker VALID, 실행기 raw(near-tie는 구성한 raw도)와 일치, 불일치 0.** 안쪽 899·축 341·바깥 900·먼 점 18·65점 65·hard-case 후보 234(shell 16/17/18의 표본 61/64/109)·shell 24〜26 3·near-tie 200(2^-10〜2^-140 위·아래).
- **첫 시도에 VALID가 2,660/2,660(100%).** √ 비트 128이 2,497건, 192가 106건, 256이 51건, 320이 6건. 재시도(not_separated)는 한 번도 필요 없었다.
- prover 한 번의 시간: 중앙값 0.05초, 99분위 0.13초, 최대 0.17초. 총 CPU 145초.

**2단계 cap-128 rehearsal: 실제 궤적 3개, cap 128이 거부한 충격량 전부 해결.**

| 궤적 | step | 거부(STOP) | 해결한 성분 | 128 초과 필요 | 일치 | 최대 √ 비트 |
|---|---|---|---|---|---|---|
| e=9 De, b=Re/2 | 1,640 | 25 | 50 | 25 | 50/50 | 128 |
| e=1/2 De, b=Re/2 | 5,775 | 77 | 154 | 77 | 154/154 | 128 |
| e=1/10 De, b=2Re | 21,056 | 239 | 478 | 239 | 478/478 | 192 |

(해결한 성분 수는 거부된 입력의 0이 아닌 성분 전부이고, 그중 128을 넘어야 했던 것이 거부 수와 같다.) 모든 raw가 full-cap 실행기의 raw와 같다.

**3단계 2^-17000 (실행기가 cap 16384에서 `ReferenceUndecided`를 내는 합성 STOP, 위·아래):**

| | 기본 checker 한도 | 한도를 올림(`digits_max` 10^5, `bits_max` 10^8, 3000초) |
|---|---|---|
| 위(+) | EXHAUSTED `checker_refused:integer_size_limit`(3.3초) | **FOUND**, raw = mpmath 기대값, 첫 시도 √ 17152 / P 17248 VALID, 188초(checker 185초) |
| 아래(−) | 같음 | **FOUND**, raw = 기대값, 첫 시도 VALID, 188초 |

- prover는 raw와 거리(`dist_bits` 17000/17001)를 **스스로 추정**했다(추정 3초). 재시도가 필요 없었다.
- 두 FOUND 모두 같은 한도로 checker를 다시 돌려 VALID·같은 raw임을 재확인했다.
- 기본 한도 결과는 합성 `dt_kick`(약 5,300자리)이 `digits_max`에 걸리는 합성법의 문제이고 실제 runtime 입력(dt=20)에는 없다.
- 이 사례의 일치는 **prover의 mpmath 추정, 구성 시 mpmath 기대값, V2 checker의 정확 구간**이라는 서로 다른 계산들의 일치다. V1과의 교차검증은 아니다.

**먼저 공개(캠페인 과정의 실패 두 건, 삭제하지 않고 보존):**
1. 3단계 첫 결과의 두 행이 `agree: false`였다. 원인은 **드라이버 결함**이다. FOUND 뒤 재검증을 기본 한도로 해서 5,300자리 `dt_kick`이 REFUSED가 되었다. prover의 FOUND는 올린 한도의 checker가 VALID로 판정한 것이 맞았다. 재검증을 실행과 같은 한도로 고쳐 3단계만 다시 돌렸다. 첫 요약은 `summary_first_run_stage3_verify_used_default_limits.json`으로 보존한다.
2. 3단계 재실행을 처음에 `python -`(표준입력 스크립트)로 띄웠더니 Windows spawn 방식 프로세스 풀의 워커가 죽었다(`BrokenProcessPool`). **실행 방법 문제**이며 코드 결함이 아니다. 모듈 진입점 `--stage3`을 추가해 다시 돌렸고, 실패 로그는 `stage3_rerun_FAILED_stdin_spawn_BrokenProcessPool.log`로 보존한다.

### 9.4 아직 증명되지 않은 것 (먼저 공개)

1. **prover는 비신뢰다.** 위 결과는 "prover가 checker가 받아 주는 certificate를 찾았다"는 것이지 "prover가 옳다"는 것이 아니다. 옳음의 근거는 V2 checker이고, V2 checker의 신뢰는 형식 증명이 아니라 논증·시험·교차검증이다.
2. **추정기의 수락 규칙은 휴리스틱이다.** 지금까지 2,660건 표본과 near-tie 사다리에서 ANOMALY는 0건이었지만, 추정이 조용히 틀릴 수 있는 입력(예: 극단적 상쇄)이 없다는 증명은 아니다. 그 경우에는 ANOMALY로 드러나며 FOUND가 되지 않는다.
3. **표본 캠페인은 결정적 표본이다.** 첫 시도 100% VALID는 이 표본의 결과이며, 모든 입력에 대한 보장이 아니다. 필요한 N에는 사전 상한이 없다(Lemma A+B는 유한한 certificate가 있다는 것만 준다).
4. **A-EV 미해결, ④-Safety Conditional, ④-Liveness NotCertified.** prover가 실제 STOP을 푼다는 것이 D_valid 전체의 Liveness를 보였다는 뜻이 아니다. runtime wrapper·Proof Cache는 연결하지 않았다.
5. 비용은 한 기계·한 입력 계열의 측정이다. 2^-17000 한 번의 checker 시간은 185초였다.
6. 아직 하지 않은 것: runtime wrapper(STOP 상태에서 prover 호출, 결과의 WITNESS_RESOLVED 기록, 같은 step 재실행, certificate 바이트 크기 상한), Proof Cache. wrapper는 실패 의미와 correctness path를 실제 실행기에 연결하므로 설계자 권고대로 더 강한 모델(Opus 5.5 High)로 설계한다.

