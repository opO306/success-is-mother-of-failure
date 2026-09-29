# C1-B1 D3 — Checker V2 enclosure 수렴 lemma (Lemma B의 V2 확장) + prover V0.2 완결성 조립 — 개정 2

**상태:** **개정 2 — 독립 감사 통과(GPT-5.6 Sol High, 2회차, 2026-09-30, 대상 `8c5c4f7`). 설계자 상태 승인 대기.** 1회차(개정 1, `5f1a4c7`)는 불통과였다. 증거 등급: 독립 수학/코드 감사 통과이며 proof assistant의 formal certified가 아니다. 감사 기록: [인계 문서 6절](C1B1_D3_AUDIT_HANDOFF_V0.md). 기준: prover V0.2 + 힌트 상한(`a_reference/c1b1_point_prover.py`: D1·D2 + H-B + UNREPRESENTABLE + `HINT_WORK_BITS_MAX`), checker V2 소스(변경 없음).
**근거:** 설계자 판정 2026-09-30 D1 승인·D2 승인·**D3 진행**·D4 정확 상한([완결성 감사 V0](C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md) 6·8절), **H-B 승인과 그 수정**(부동소수 차수는 힌트, 정확 인증, fallback은 반복 없는 닫힌 부등식으로 인증), `UNREPRESENTABLE` 분리. [Lemma A·B 감사](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md)(A 승인, B 방향 승인).
**개정 1에서 바뀐 것:** 초판의 가정 (H-float, 부동소수 차수 선택)을 없앴다(4절). 3절에 필요한 차수 성질을 코드의 정확 인증이 보장한다. 정성 완결성은 **고정 `CERT_BITS = 64` 힌트 인증기에도 기대지 않는다**: 완결성이 쓰는 경로는 O(1) 닫힌 부등식으로 인증되는 fallback이다.
**개정 2에서 바뀐 것(감사 불통과 2건):** (1) **부동소수 힌트가 실제로는 필수 경로였다.** `_certified_plan`이 fallback보다 먼저 `_exp_plan`을 무조건 불렀고, 그 안의 `bits * LN2`는 P가 아주 크면 `OverflowError`를 낸다(재현: `_exp_plan(3.0, 128, 10**400)`). 임의 유리수 dt_kick에서는 필요한 P에 공통 상한이 없으므로 정성 정리에서 무시할 수 없다. 이제 힌트는 `_hint_plan`을 거친다: P > `HINT_WORK_BITS_MAX` = 2^16이면 부동소수 코드를 **호출하지 않고**, 그 아래에서도 planner의 산술 예외(`ArithmeticError`, `ValueError`)는 "힌트 없음"이다. 둘 다 전부 fallback으로 간다(4절 0). 수정 전에는 planner의 `ValueError`가 `prove()`에서 `EXHAUSTED(serialization_limit)`로 잘못 분류되기도 했다(시험으로 확인). (2) 5절의 "budget·Limits가 무한이면"은 실제 코드의 계약이 아니다(`for _ in range(budget.max_attempts)`). **"충분히 큰 유한 budget과 Limits가 존재한다"**로 고쳤다. 아울러 fallback의 "O(1)"은 "Taylor 차수 n에 비례하는 반복 없이 상수 개수의 정확 비교"로 고쳤다(큰 정수 비교 자체의 비용은 비트 길이에 따라 는다).
**현재 상태(변경 없음):** A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified.** 감사 통과가 영향을 주는 범위는 D3 / Point Prover의 rounding-decision 정성 완결성뿐이다. 이 문서만으로는 아무것도 승격하지 않는다.

## 0. 한 줄

입력 하나를 고정하고 prover V0.2의 정밀도 순서(N_j → ∞, P_j = N_j + 96, 차수는 `_certified_plan`)를 따라가면, checker V2가 계산하는 enclosure J_j의 폭은 0으로 간다(Lemma B-V2). Lemma A(참값이 경계에서 d > 0 떨어짐)와 합치면 유한한 j*에서 J가 참 raw의 열린 칸 안에 들어가고, 흐름(힌트 → raw_mismatch → enclosure가 결정)은 그 전에 또는 그때 VALID를 반환한다(조립 정리). **부동소수 가정은 남지 않는다**(4절).

## 1. 기호와 대상

- 입력: dr ∈ Z³(FX(96,48) raw), 성분 k(dr_k ≠ 0), dt_kick ∈ Q∖{0}, R² = Σdr_i²·2^−96 ≥ r_min². 참값 y* = J_k/ulp, ulp = 2^−80.
- prover V0.1 순서: N_0 = round64(max(128, 힌트 비트)) 또는 128(힌트 없음), N_{j+1} = round64(⌊3N_j/2⌋ + 1). 따라서 **N_j는 엄격 증가하고 N_j → ∞.** P_j = N_j + 96.
- 차수: 각 비율 λ(9개)에 대해 `_certified_plan`이 정한다. 부동소수 `_exp_plan`은 **힌트**만 주고, P ≤ 2^16일 때만 호출된다(`_hint_plan`, 4절 0). 힌트는 정확한 x 구간(checker와 같은 계산, `_exact_x`)에서 정확 인증을 통과하고 n ≤ n_fb, n ≤ order_max일 때만 쓰인다. 아니면 **fallback** (`full`, n_fb), n_fb = max(⌈2·E_UP·x_hi⌉, P + 32) + 1을 쓴다(E_LO = 2.7182 < e < E_UP = 2.7183, 유리수).
- J_j: 그 매개변수로 checker V2 `_compute`가 만드는 구간(`enclosure()`와 `check_certificate()`는 같은 `_compute`를 쓴다. 출력 raw는 J에 들어가지 않는다. 1〜528행 확인).

## 2. 보조 사실 (코드에서 직접)

**F1 (√).** r_j = [a/2^N, (a+1)/2^N], a = isqrt(⌊R²·4^N⌋) ⇒ R ∈ r_j, 폭 2^−N_j → 0. R² ≥ r_min² > 1이면 a ≥ 1, r.lo > 0 (`_sqrt_interval`, 511행 검사).

**F2 (outward 반올림 1회의 상대 오차).** `down(x, P)`: e = bitlen(a) − bitlen(b) − P − 1에서 버리는 양은 2^e 미만이다. |x| ≥ 2^{bitlen(a)−bitlen(b)−1}이므로 |x − down(x)| < 2^e ≤ |x|·2^−P이다. `up`도 같다. **상대 오차 < 2^−P.** 반올림은 항상 바깥쪽이라 포함 관계를 깨지 않는다(모듈 머리말, `_Iv.rnd`).

**F3 (exp, full).** x = [x_lo, x_hi], n + 2 > x_hi일 때 `_exp_interval`은 [down(1/(S⁺_n(x_hi) + U⁺_n(x_hi))), up(1/S⁻_n(x_lo))] ∋ e^−v (v ∈ x)를 준다. 여기서 S⁻, S⁺, U⁺는 각 항·부분합을 한쪽으로 반올림한 값이다(Lemma B 감사 3절의 부등식 + F2). 반올림 횟수는 급수당 2n + O(1)이다.

**F4 (exp, zero_floor).** [0, up(1/S⁻_n(x_lo))]. 모든 n에서 건전하다. 폭은 1/S_n(x_lo) ≤ n!/x_lo^n 이하다.

**F5 (나머지 식).** `_dv`는 R의 멱(−17..6), retardation 유리식 g = Nr/Dn(Dn ≥ 1: RET_B 전부 양수, R > 0), 9개 exp enclosure, 고정 길이(≤ 17)의 damping 합으로 이루어진 **고정 모양의 식**이다. 나눗셈은 양의 구간(Dn, Dn², r)으로만 한다. 반올림 위치는 식 모양으로 정해진 유한 개(exp 급수 제외)다.

## 3. Lemma B-V2 (수렴)

**진술.** 입력 하나를 고정한다. 차수가 4절의 성질 (C1)〜(C3)를 만족하면(prover V0.2는 항상 만족한다) width(J_j) → 0 (j → ∞)이다.

**증명.**
1. F1로 width(r_j) → 0.
2. 각 비율 λ의 x_j = r_j·λ(반올림 1회)는 폭 ≤ λ·2^−N_j + 2·λR·2^−P_j → 0이고 x* = λR로 수렴한다.
3. **exp 폭 → 0.** (a) `zero_floor`: (C3)로 폭 ≤ up(1/S⁻_n(x_lo)) ≤ 2^−(P+72)·(1 + O(n·2^−P)) → 0. (b) `full`: 참 enclosure [1/(S_n(x_hi) + U_n(x_hi)), 1/S_n(x_lo)]의 폭은
   |1/S_n(x_lo) − 1/S_n(x_hi)| + U_n(x_hi)/S_n(x_hi)² ≤ (x_hi − x_lo) + 2^−(P+32)
   이다. 첫 항은 S_n′ = S_{n−1} ≤ S_n, S_n ≥ 1에서 |d(1/S_n)/dx| ≤ 1이므로 **n에 대해 균등**하게 성립한다. 둘째 항은 (C1)의 상대 꼬리다. 두 항 모두 → 0이다. 여기에 checker의 한쪽 반올림(급수당 2n + O(1)회, 각 상대 오차 < 2^−P, F2)이 더하는 누적 상대 오차는 (C2)의 n = O(P + x)로 (2n + O(1))·2^−P·(1 + o(1)) → 0이다.
4. **나머지 식(F5).** 입력 구간(r, 9개 exp)의 폭 → 0이고, 반올림 위치가 유한 개이며 각 상대 오차 < 2^−P → 0이다. 분모는 0에서 떨어져 있다(Dn ≥ 1, r.lo ≥ r_min − 2^−N > 0). 따라서 이 고정 모양 식의 구간 확장은 참값 근방에서 입력 폭과 반올림 오차에 대해 Lipschitz이고(Moore의 자연 구간 확장 수렴, Lemma B (iii)와 같은 논리), 폭(dV) → 0이다.
5. G = −dV·[1/r.hi, 1/r.lo](반올림 2회), J = G·c(c = dr_k·dt_kick·2^−48, 정확 곱). width(J) = |c|·width(G) → 0. ∎

**Lemma B(V1형)와의 차이:** 반올림(P), `zero_floor`, 인증된 차수 선택 세 가지를 더했다. 수렴의 뼈대(√ 폭 → 0, exp 폭 → 0, 식의 연속성)는 같다. exp 폭은 절대 꼬리가 아니라 **상대 꼬리**와 n에 균등한 립시츠 성질로 묶는다(초판의 "S_n → e^x 균등"보다 직접적이다).

## 4. 차수 성질과 그 보장 — 부동소수·고정 비트 가정 없음 (개정 1)

3절이 쓰는 성질(모든 j, 모든 비율에서):
- **(C1) full:** n + 2 > x_hi(정확값, checker의 `exp_condition`과 같은 조건)이고 U_n(x_hi) ≤ 2^−(P+32)·S_n(x_hi).
- **(C2) 크기:** n ≤ n_fb(P, x_hi) = max(⌈2·E_UP·x_hi⌉, P + 32) + 1 = O(P + x).
- **(C3) zero_floor:** 1/S_n(v) ≤ 2^−(P+72) (모든 v ≥ x_lo).

**보장.** `_certified_plan`은 먼저 정확한 x(`_exact_x`)를 계산하고, 각 비율에 대해 아래 1·2 중 하나를 쓴다.
0. **힌트는 선택이다(개정 2).** `_hint_plan`은 P > `HINT_WORK_BITS_MAX` = 2^16이면 부동소수 코드를 부르지 않고 None을 돌려준다. P ≤ 2^16이면 `_exp_plan`을 부르고, `ArithmeticError`·`ValueError`는 None이 된다. None이거나 길이가 비율 수와 다르면 모든 비율이 fallback이다. 따라서 (a) 수열 P_j → ∞에서 P_j ≤ 2^16인 j는 **유한 개**이고 그 뒤로는 부동소수 코드가 전혀 실행되지 않는다. (b) P ≤ 2^16에서 planner는 유한한 부동소수 입력(R < 2^49·√3, 비율은 고정 상수, `2.0 ** -N`은 0으로 underflow할 뿐 예외 없음, need ≤ (2^16 + 88)·ln 2)으로 끝난다: `_zero_floor_order`는 많아야 ⌊x_lo⌋ + 2회, `_full_order`는 log-꼬리가 n에 대해 결국 −∞로 가므로(lgamma(n+2)가 (n+1)·log x_hi를 이긴다) 유한 회에서 멈춘다. 상한 값은 힌트냐 fallback이냐만 정하고 판정·거부에 영향을 주지 않는다. 상한 위에서는 fallback 차수(≥ P + 33)가 힌트 차수보다 클 수 있어 **속도만** 바뀐다.
1. **fallback (`full`, n_fb) — 완결성 경로.** `_fallback_ok`는 정확한 유리수 비교 두 개 n + 1 ≥ 2·E_UP·x_hi, n ≥ P + 33만 본다. Taylor 차수 n에 비례하는 반복이 없는 상수 개수의 정확 비교이고(비교 자체의 비용은 정수 비트 길이에 따라 는다), 반올림 사슬이 없으며 CERT_BITS와 무관하다. n_fb의 정의에서 n_fb + 1 ≥ ⌈2E_UP·x_hi⌉ + 2 > 2E_UP·x_hi이고 n_fb ≥ P + 33이므로 이 두 비교는 **대수적으로 항상 참**이다. 따라서 `order_certification_failed`는 정의상 일어나지 않는다(코드의 그 분기는 결함 탐지용). 두 비교가 (C1)을 함의하는 증명:
   - (n+1)! ≥ ((n+1)/e)^{n+1}(e^k ≥ k^k/k!)이므로 t_{n+1}(x_hi) = x_hi^{n+1}/(n+1)! ≤ (e·x_hi/(n+1))^{n+1} ≤ 2^−(n+1)(e·x_hi/(n+1) ≤ E_UP·x_hi/(n+1) ≤ 1/2).
   - x_hi ≤ (n+1)/(2e) < n + 2이므로 n + 2 > x_hi이고, (n+2)/(n+2−x_hi) ≤ 1/(1 − 1/(2e)) < 1.23.
   - 따라서 U_n(x_hi) = t_{n+1}·(n+2)/(n+2−x_hi) < 1.23·2^−(n+1) < 2^−n ≤ 2^−(P+33) < 2^−(P+32) ≤ 2^−(P+32)·S_n(x_hi)(S_n ≥ 1). (C2)는 등식이다.
2. **힌트 (선택적 빠른 길).** 부동소수 힌트 (mode, n)는 int이고 n ≤ n_fb, n ≤ order_max이며 정확 검사를 통과할 때만 쓰인다.
   - `full`: `_full_ok`가 t_{n+1}(x_hi)의 **상한**(위로 반올림한 사슬)과 S_n(x_hi)의 **하한**(아래로 반올림한 사슬)으로 (C1)을 검사한다. 사슬 값은 (가수 < 2^CERT_BITS, 정수 지수) 쌍이고 모든 반올림은 한쪽 방향이다(`_dy_norm`: floor/ceiling, `_dy_mul_div`: 나머지 있으면 올림, `_dy_add`: 지수 차가 2·CERT_BITS를 넘으면 작은 항을 버림(하한) 또는 마지막 자리 +1(상한)). 따라서 **True이면 (C1)이 참이다.**
   - `zero_floor`: `_zero_ok`가 n! ≤ e·n^{n+1/2}·e^−n ≤ e·n^{n+1}·e^−n에서 1/S_n(v) ≤ n!/x_lo^n ≤ e·n·(n/(e·x_lo))^n를 쓰고, q ≥ n/(E_LO·x_lo)를 위로 반올림한 뒤 q^n을 위로 반올림한 제곱 반복으로 상한한다. **True이면 (C3)이 참이다.**
   - (C2)는 n ≤ n_fb 검사로 보장된다.
   - **CERT_BITS의 역할:** 힌트 검사가 True를 **얼마나 자주** 내는지(속도)만 정한다. False는 fallback으로 가므로 완결성에 영향이 없다. 정리에 필요한 것은 힌트 검사의 **건전성**(True ⇒ 성질)뿐이다.
3. **order_max:** order_max가 j*까지 쓰이는 모든 차수보다 크면(5절의 충분히 큰 유한 Limits) 사전 검사가 발동하지 않는다. 그보다 작으면 checker와 같은 규칙(order > order_max면 거부)으로 무거운 계산 전에 `EXHAUSTED(checker_refused:order_limit)`를 낸다(가용성).

**부동소수가 남는 곳:** 힌트를 **만드는** `_exp_plan`(P ≤ 2^16에서만, 0)과 mpmath 추정(시작 전 1회)뿐이다. 둘 다 정리에서 값의 역할이 없다(틀리거나 실패하면 fallback·enclosure로 간다). 정리가 필요로 하는 것은 둘이 **끝난다**는 것뿐이다: planner는 0의 (b), 추정은 유한 `estimate_max_bits`에서 정밀도를 두 배씩 올리다 상한에서 `_Stop`으로 끝난다.

## 5. 조립 — prover V0.2 정성적 완결성 (독립 감사 조건부 초안)

**진술(초안, 개정 2).** 1절의 입력에서 참 raw m*가 FX(96,80) 범위 안이라고 하자(**D4 성립: dt = 40에서 실행기가 판정하는 모든 충격량은 \|J\| ≤ 1277.3 a.u. = 경계의 3.9%**, [감사 8절](C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md)). 그러면 **입력마다 충분히 큰 유한** prover Budget(`max_attempts`, `max_sqrt_bits`; `estimate_max_bits`는 아무 유한값, `seconds_max = None`)과 checker V2 Limits(`sqrt_bits_max`, `work_bits_max`, `order_max`, `bits_max`, `seconds_max`, `digits_max`)와 Python 정수 문자열 한도가 **존재하여**, `prove()`가 유한 단계에서 FOUND(checker V2 VALID, raw = m*)를 반환한다. 한도는 입력에 따라 다르며, 지원 입력 전체에 대한 공통 유한 한도는 주장하지 않는다(임의 유리수 dt_kick은 참값을 반 ulp 경계에 얼마든지 가깝게 만든다). (참 raw가 범위 밖이면 대신 `UNREPRESENTABLE`을 유한 단계에서 반환한다. 같은 논증에서 j*에 `_cell`이 범위 밖 칸을 준다.)

**증명.** Lemma A로 d = |y* − 가장 가까운 경계| > 0이다. Lemma B-V2로 width(J_j) → 0이다. J_j ∋ y*이므로 width(J_j) < d인 j*에서 J_{j*}는 m*의 열린 칸 안에 있다. 이제 V0.1의 흐름을 보면:
0. **한도 고르기.** 아래 1〜4에서 j*까지 쓰이는 양(반복 수 ≤ j* + 2, N_{j*}, P_{j*}, 인증된 차수, checker가 다루는 정수 비트, 각 호출 시간, certificate 숫자 자릿수)은 모두 유한하다. 이들보다 큰 유한 한도를 고르면 j*까지 어떤 한도에도 닿지 않는다. 시작 전의 추정은 유한 `estimate_max_bits`에서 끝나고(4절 끝), 실패해도 4의 경로로 간다.
1. 매 반복은 N을 늘리거나(`not_separated`), 같은 N에서 힌트를 버리거나(`raw_mismatch`, 최대 1회: 이후 `decided`), 끝난다. 그래서 j*까지의 반복 수는 유한하다(힌트 버림 1회 + N 증가 j*회 + 마지막 1회). 각 반복의 `_certified_plan`은 4절 0으로 끝나고 예외를 내지 않는다.
2. **힌트가 m*인 경우:** J는 항상 y* ∈ 칸(m*)을 포함하므로 `raw_mismatch`는 나올 수 없다. j* 이전에는 `not_separated`, j*에서는 VALID다.
3. **힌트 m ≠ m*인 경우:** 늦어도 j*에서 J ⊂ 칸(m*)이고, 이것은 m의 닫힌 칸과 서로소이므로 `raw_mismatch`가 나온다. 그러면 같은 N에서 `enclosure()`가 같은 J를 계산한다(같은 `_compute`, 출력 raw 무관). `_cell(J)`는 `_decide_raw`와 같은 엄격 판정으로 m*를 돌려준다(J ∋ y*이고 J가 한 칸 안이면 그 칸은 m*의 칸이다). 이어지는 `check_certificate`는 같은 J로 VALID(m*)다. 더 이른 j에서 raw_mismatch가 나와도 `_cell`은 None(→ N 증가)이거나 m*다.
4. **힌트 없음(추정 실패):** 3의 enclosure 경로를 N_0 = 128부터 탄다. j*에서 `_cell` = m*, 그다음 VALID.
5. ANOMALY는 일어나지 않는다. `exp_condition`은 (C1)로, `order_certification_failed`는 4절 1로, `enclosure_checker_disagree`는 3의 같은 J로 배제된다. 나머지 구조적 INVALID(`exp_rate`, `format` 등)는 prover가 만드는 certificate가 형식 상수를 그대로 쓰므로 나오지 않는다. REFUSED는 0에서 고른 Limits에서 j*까지 일어나지 않는다. `UNREPRESENTABLE`은 m*가 범위 밖일 때만이다(가정으로 배제; C1-B1 dt = 40에서는 D4로 불가능하며, 그때 wrapper는 `RuntimeContractViolation`을 낸다). ∎

## 6. 독립 감사가 봐야 할 곳 (감사 체크리스트)

1. F2의 상대 오차 부등식(`down`의 e 선택, 음수의 floor 포함).
2. F3: 급수를 한쪽으로 반올림할 때 S⁻ ≤ S_n ≤ S⁺, U⁺ ≥ U_n이 되는지(`_series_lower`/`_series_upper`/`_exp_combine`의 각 방향).
3. 3절 3(b): 상대 꼬리와 |d(1/S_n)/dx| ≤ 1(n에 균등)로 exp 폭을 묶는 논증, n_j = O(P_j + x)와 급수 누적 반올림 → 0.
4. 3절 4: `_dv`의 반올림 위치가 식 모양으로 정해진 유한 개인지(루프 길이가 N·P에 의존하지 않는지. damping 합은 k ≤ 8로 고정).
5. 5절 3: `enclosure()`와 `check_certificate()`의 J가 **정확히 같은지**(같은 cert에서 출력 raw만 다름. `_compute`가 raw를 J 계산에 쓰지 않음). Limits가 같을 때 REFUSED 여부도 같은지.
6. **4절 전체(개정 1의 핵심):** (i) fallback의 두 비교가 (C1)을 함의하는 부등식 사슬((n+1)! ≥ ((n+1)/e)^{n+1}, 1/(1 − 1/(2e)) < 1.23), n_fb 정의에서 두 비교가 항상 참이라는 것, (ii) 힌트 검사의 건전성: `_dy_*`의 모든 반올림이 올바른 방향인지(특히 `_dy_add`의 지수 차 분기와 `_dy_norm`의 ceiling), `_zero_ok`의 n! 상한, (iii) 완결성이 CERT_BITS에 기대지 않는다는 논증(False는 fallback으로만 간다), (iv) `_exact_x`가 checker `_compute`의 x와 **정확히** 같은지(같은 `_sqrt_interval`, 같은 `r.mul(_const(rate, P), P)`).
7. `UNREPRESENTABLE`의 정의와 wrapper의 `RuntimeContractViolation`(dt = 40에서만, run 불변).
8. **개정 2(재감사 대상):** (i) `_hint_plan`이 P > 2^16에서 부동소수 코드를 부르지 않는지, 그 아래 예외가 모두 fallback으로 가는지(수정 뒤 `prove()`의 `except ValueError`(serialization_limit)에 planner 예외가 닿지 않는지 포함), (ii) P ≤ 2^16에서 planner가 끝난다는 4절 0 (b)의 논증, (iii) 5절의 "입력마다 충분히 큰 유한 한도가 존재" 진술과 증명 0단계, (iv) `5f1a4c7` 이후 실제 diff.

감사자는 구현자와 다른 사람 또는 모델이 맡는다(설계자 지정). **개정 2는 2회차 감사를 통과했다. 설계자의 상태 승인 전에는 승인된 것으로 쓰지 않는다.**

## 7. 하지 않은 것

계산 캠페인, ④-Liveness 승격, A-EV. 코드(H-B, UNREPRESENTABLE, wrapper)는 prover V0.2 커밋에 있다. D4 상한은 별도 스크립트(`a_reference/c1b1_impulse_magnitude_bound.py`)이고 결과는 감사 문서 8절에 있다.
