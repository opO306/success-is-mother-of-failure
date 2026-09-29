# C1-B1 D3 — Checker V2 enclosure 수렴 lemma V0 (Lemma B의 V2 확장) + prover V0.1 완결성 조립

**상태:** **lemma 작성(구현자). 독립 감사 전 — 승인 아님.** 코드 변경 없음(이 문서는 수학 문서다). 기준: prover V0.1(D1·D2 구현), checker V2 소스 `a_reference/c1b1_exact_impulse_checker_v2.py`(변경 없음).
**근거:** 설계자 판정 2026-09-30 D1 승인·D2 승인·**D3 진행**·D4 정확 상한([완결성 감사 V0](C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md) 6절). [Lemma A·B 감사](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md)(A 승인, B 방향 승인).
**현재 상태(변경 없음):** A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified.** 이 문서만으로는 아무것도 승격하지 않는다.

## 0. 한 줄

입력 하나를 고정하고 prover V0.1의 정밀도 순서(N_j → ∞, P_j = N_j + 96, 차수는 `_exp_plan`)를 따라가면, checker V2가 계산하는 enclosure J_j의 폭은 0으로 간다(Lemma B-V2). Lemma A(참값이 경계에서 d > 0 떨어짐)와 합치면 유한한 j*에서 J가 참 raw의 열린 칸 안에 들어가고, V0.1의 흐름(힌트 → raw_mismatch → enclosure가 결정)은 그 전에 또는 그때 VALID를 반환한다(조립 정리). **단, 차수 선택이 부동소수 계산이라는 점 하나가 가정(H-float)으로 남는다(4절).**

## 1. 기호와 대상

- 입력: dr ∈ Z³(FX(96,48) raw), 성분 k(dr_k ≠ 0), dt_kick ∈ Q∖{0}, R² = Σdr_i²·2^−96 ≥ r_min². 참값 y* = J_k/ulp, ulp = 2^−80.
- prover V0.1 순서: N_0 = round64(max(128, 힌트 비트)) 또는 128(힌트 없음), N_{j+1} = round64(⌊3N_j/2⌋ + 1). 따라서 **N_j는 엄격 증가하고 N_j → ∞.** P_j = N_j + 96.
- 차수: 각 비율 λ(9개)에 대해 `_exp_plan(R_float, N_j, P_j)`가 (`full`, n) 또는 (`zero_floor`, n)을 준다.
- J_j: 그 매개변수로 checker V2 `_compute`가 만드는 구간(`enclosure()`와 `check_certificate()`는 같은 `_compute`를 쓴다. 출력 raw는 J에 들어가지 않는다. 1〜528행 확인).

## 2. 보조 사실 (코드에서 직접)

**F1 (√).** r_j = [a/2^N, (a+1)/2^N], a = isqrt(⌊R²·4^N⌋) ⇒ R ∈ r_j, 폭 2^−N_j → 0. R² ≥ r_min² > 1이면 a ≥ 1, r.lo > 0 (`_sqrt_interval`, 511행 검사).

**F2 (outward 반올림 1회의 상대 오차).** `down(x, P)`: e = bitlen(a) − bitlen(b) − P − 1에서 버리는 양은 2^e 미만이다. |x| ≥ 2^{bitlen(a)−bitlen(b)−1}이므로 |x − down(x)| < 2^e ≤ |x|·2^−P이다. `up`도 같다. **상대 오차 < 2^−P.** 반올림은 항상 바깥쪽이라 포함 관계를 깨지 않는다(모듈 머리말, `_Iv.rnd`).

**F3 (exp, full).** x = [x_lo, x_hi], n + 2 > x_hi일 때 `_exp_interval`은 [down(1/(S⁺_n(x_hi) + U⁺_n(x_hi))), up(1/S⁻_n(x_lo))] ∋ e^−v (v ∈ x)를 준다. 여기서 S⁻, S⁺, U⁺는 각 항·부분합을 한쪽으로 반올림한 값이다(Lemma B 감사 3절의 부등식 + F2). 반올림 횟수는 급수당 2n + O(1)이다.

**F4 (exp, zero_floor).** [0, up(1/S⁻_n(x_lo))]. 모든 n에서 건전하다. 폭은 1/S_n(x_lo) ≤ n!/x_lo^n 이하다.

**F5 (나머지 식).** `_dv`는 R의 멱(−17..6), retardation 유리식 g = Nr/Dn(Dn ≥ 1: RET_B 전부 양수, R > 0), 9개 exp enclosure, 고정 길이(≤ 17)의 damping 합으로 이루어진 **고정 모양의 식**이다. 나눗셈은 양의 구간(Dn, Dn², r)으로만 한다. 반올림 위치는 식 모양으로 정해진 유한 개(exp 급수 제외)다.

## 3. Lemma B-V2 (수렴)

**진술.** 입력 하나를 고정한다. (H-float, 4절)을 가정하면 width(J_j) → 0 (j → ∞)이다.

**증명.**
1. F1로 width(r_j) → 0.
2. 각 비율 λ의 x_j = r_j·λ(반올림 1회)는 폭 ≤ λ·2^−N_j + 2·λR·2^−P_j → 0이고 x* = λR로 수렴한다.
3. **exp 폭 → 0.** (a) `zero_floor`: prover는 n ≤ x_lo + 2이고 n ln x_lo − ln n! ≥ (P + 88)·ln2 + 1인 n이 있을 때만 이 모드를 고른다(`_zero_floor_order`, bits = P + 48, +40). 그러면 폭 ≤ n!/x_lo^n ≤ 2^−(P+88) → 0이다. 또 n ln x − ln n!의 최댓값은 x 근처에서 약 x이므로, P가 약 x*/ln2를 넘으면 그런 n이 없어 `full`로 넘어간다. (b) `full`: prover는 n_j를 x_hi 기준 꼬리 추정 ≤ 2^−(P_j+48)이 되는 가장 작은 n으로 고른다. (H-float)로 참 꼬리 U_n(x_hi) → 0이다. x_hi가 유계인 동안 n_j → ∞이고 n_j = O(P_j)이다. 급수 반올림의 누적 상대 오차는 (1 + 2^−P)^{2n+O(1)} − 1 ≤ (2n + O(1))·2^−P·(1 + o(1)) → 0이다. S_n(x) → e^x가 x에 대해 균등(x 유계)하고 e^−x는 연속이므로 [하한, 상한]의 폭 → 0이다.
4. **나머지 식(F5).** 입력 구간(r, 9개 exp)의 폭 → 0이고, 반올림 위치가 유한 개이며 각 상대 오차 < 2^−P → 0이다. 분모는 0에서 떨어져 있다(Dn ≥ 1, r.lo ≥ r_min − 2^−N > 0). 따라서 이 고정 모양 식의 구간 확장은 참값 근방에서 입력 폭과 반올림 오차에 대해 Lipschitz이고(Moore의 자연 구간 확장 수렴, Lemma B (iii)와 같은 논리), 폭(dV) → 0이다.
5. G = −dV·[1/r.hi, 1/r.lo](반올림 2회), J = G·c(c = dr_k·dt_kick·2^−48, 정확 곱). width(J) = |c|·width(G) → 0. ∎

**Lemma B(V1형)와의 차이:** 반올림(P)과 `zero_floor`와 부동소수 차수 선택 세 가지를 더했다. 수렴의 뼈대(√ 폭 → 0, exp 폭 → 0, 식의 연속성)는 같다.

## 4. 남는 가정 (H-float) — 먼저 공개

prover의 차수 선택(`_full_order`, `_zero_floor_order`)은 **부동소수** `math.log`, `math.lgamma`와 float x_lo/x_hi를 쓴다. 3절이 쓰는 성질은 세 가지다.
- (a) P_j → ∞이면 `full` 차수 n_j → ∞이고 참 꼬리 U_{n_j}(x_hi) → 0이다.
- (b) `full`에서 n + 2 > x_hi(정확값)이다. 그렇지 않으면 checker가 `exp_condition` INVALID → ANOMALY로 멈춘다.
- (c) `zero_floor`를 고르면 1/S_n(x_lo) ≤ 약 2^−(P+88)이다.

**현실적 범위에서의 근거:** float 상대 오차는 약 10^−16이다. (b)는 n ≥ ⌈x_hi,float⌉ − 1로 약 1의 여유를 두는데, x < 2^52(R은 2^49 bohr 미만, λ < 7)이면 float 오차가 그 여유를 넘지 않는다. (a)와 (c)에서 log 꼬리의 float 오차는 약 10^−16·n·ln n 크기라 목표 (P + 48)·ln2보다 한참 작다. 다만 P가 2^50 정도로 커지면 이 비교가 무의미해진다. 그 크기는 정수 하나가 페타바이트급이라 실제로는 실행할 수 없는 영역이다.

**엄밀한 수학적 정리로 쓰려면 둘 중 하나가 필요하다(설계자 판단):**
- **H-A (문서):** 완결성 정리를 "P ≤ P_max(예: 2^40)에서 VALID가 나오는 입력"으로 한정한다. 정성 정리가 아니게 된다.
- **H-B (코드, 작음):** 차수 선택을 정확 정수·유리수 계산으로 바꾼다. 예: n을 늘려 가며 checker와 같은 U_n 상한을 정확히 평가한다. 그러면 (a)〜(c)가 float 없이 성립하고, 정성 정리에서 H-float가 사라진다. prover는 비신뢰 생성기이므로 건전성에는 영향이 없고 가용성(속도)만 바뀐다.

구현자 권고: **H-B.** 수정은 prover 내부 두 함수에 한정되고 checker·실행기는 그대로다. 설계자 판정 전에는 구현하지 않는다.

## 5. 조립 — prover V0.1 정성적 완결성 (D4·H-float·독립 감사 조건부 초안)

**진술(초안).** 1절의 입력에서 참 raw m*가 FX(96,80) 범위 안이라고 하자(**D4 성립: dt = 40에서 실행기가 판정하는 모든 충격량은 \|J\| ≤ 1277.3 a.u. = 경계의 3.9%**, [감사 8절](C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md)).  budget·Limits가 무한이고 Python 정수 문자열 한도를 해제했으며 (H-float)가 성립하면, `prove()`는 유한 단계에서 FOUND(checker V2 VALID, raw = m*)를 반환한다.

**증명.** Lemma A로 d = |y* − 가장 가까운 경계| > 0이다. Lemma B-V2로 width(J_j) → 0이다. J_j ∋ y*이므로 width(J_j) < d인 j*에서 J_{j*}는 m*의 열린 칸 안에 있다. 이제 V0.1의 흐름을 보면:
1. 매 반복은 N을 늘리거나(`not_separated`), 같은 N에서 힌트를 버리거나(`raw_mismatch`, 최대 1회: 이후 `decided`), 끝난다. 그래서 j*까지의 반복 수는 유한하다(힌트 버림 1회 + N 증가 j*회 + 마지막 1회).
2. **힌트가 m*인 경우:** J는 항상 y* ∈ 칸(m*)을 포함하므로 `raw_mismatch`는 나올 수 없다. j* 이전에는 `not_separated`, j*에서는 VALID다.
3. **힌트 m ≠ m*인 경우:** 늦어도 j*에서 J ⊂ 칸(m*)이고, 이것은 m의 닫힌 칸과 서로소이므로 `raw_mismatch`가 나온다. 그러면 같은 N에서 `enclosure()`가 같은 J를 계산한다(같은 `_compute`, 출력 raw 무관). `_cell(J)`는 `_decide_raw`와 같은 엄격 판정으로 m*를 돌려준다(J ∋ y*이고 J가 한 칸 안이면 그 칸은 m*의 칸이다). 이어지는 `check_certificate`는 같은 J로 VALID(m*)다. 더 이른 j에서 raw_mismatch가 나와도 `_cell`은 None(→ N 증가)이거나 m*다.
4. **힌트 없음(추정 실패):** 3의 enclosure 경로를 N_0 = 128부터 탄다. j*에서 `_cell` = m*, 그다음 VALID.
5. `enclosure_checker_disagree`, `exp_condition` 등 ANOMALY는 (H-float)(b)와 1절의 입력 조건 아래 일어나지 않는다. REFUSED는 무한 Limits에서 일어나지 않는다. `output_out_of_range`는 m*가 범위 밖일 때만 일어난다(가정으로 배제). ∎

## 6. 독립 감사가 봐야 할 곳 (감사 체크리스트)

1. F2의 상대 오차 부등식(`down`의 e 선택, 음수의 floor 포함).
2. F3: 급수를 한쪽으로 반올림할 때 S⁻ ≤ S_n ≤ S⁺, U⁺ ≥ U_n이 되는지(`_series_lower`/`_series_upper`/`_exp_combine`의 각 방향).
3. 3절 3(b): `full` 차수 n_j = O(P_j)와 급수 누적 반올림 → 0.
4. 3절 4: `_dv`의 반올림 위치가 식 모양으로 정해진 유한 개인지(루프 길이가 N·P에 의존하지 않는지. damping 합은 k ≤ 8로 고정).
5. 5절 3: `enclosure()`와 `check_certificate()`의 J가 **정확히 같은지**(같은 cert에서 출력 raw만 다름. `_compute`가 raw를 J 계산에 쓰지 않음). Limits가 같을 때 REFUSED 여부도 같은지.
6. (H-float)의 범위 서술(4절)과 H-B 선택지.

감사자는 구현자와 다른 사람 또는 모델이 맡는다(설계자 지정). 감사 전에는 이 lemma를 승인된 것으로 쓰지 않는다.

## 7. 하지 않은 것

코드 변경, H-B 구현, 계산 캠페인, ④-Liveness 승격, A-EV. D4 상한은 별도 스크립트(`a_reference/c1b1_impulse_magnitude_bound.py`)이고 결과는 감사 문서 8절에 있다.
