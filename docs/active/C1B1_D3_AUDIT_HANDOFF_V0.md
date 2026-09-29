# D3 독립 감사 인계 — Checker V2 수렴 lemma(개정 2) + Point Prover V0.2

**감사자:** GPT-5.6 Sol High(설계자 지정, 2026-09-30). 작성자(Claude)와 다른 계열이 교차 검증한다.
**감사 결과:** 1회차(개정 1, 대상 `5f1a4c7`) **불통과** → 개정 2(`8c5c4f7`) → 2회차 **통과**(2026-09-30). 기록은 6절. **상태 변경의 최종 승인은 설계자 몫이며 아직 내려지지 않았다.**
**감사 범위 밖(통과해도 바뀌지 않음):** ④-Liveness 전체(NotCertified), ④-Safety(Conditional), A-EV(별도 작업선, 미해결).

## 1. 감사할 명제

[C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md](C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md)(개정 2)의 두 명제.

- **Lemma B-V2 (3절):** 입력 하나를 고정하고 prover V0.2의 정밀도 순서를 따라가면 checker V2 enclosure J_j의 폭 → 0.
- **조립 정리 (5절):** 지원 입력(R ≥ r_min, dr_k ≠ 0, dt_kick ≠ 0, FX(96,48) 상대 위치, 참 raw가 FX(96,80) 범위 안)을 하나 고정하면, **그 입력에 대해 충분히 큰 유한** prover Budget과 checker V2 Limits(및 Python 정수 문자열 한도)가 **존재하여** `prove()`가 유한 단계에서 checker V2 VALID(참 raw)를 반환한다. 지원 입력 전체의 공통 유한 한도는 주장하지 않는다(임의 유리수 dt_kick은 참값을 반 ulp 경계에 얼마든지 가깝게 만든다).

전제로 쓰는 승인된 사실: Lemma A(참값은 half-ulp 경계가 아님, 승인), checker V2 enclosure의 건전성, D4(dt = 40에서 |J| ≤ 1277.3 a.u., 승인. `a_reference/c1b1_impulse_magnitude_bound.py`). canonical dt = 40에서는 D4가 출력 범위 가정을 따로 보장한다.

## 2. 읽을 코드

| 파일 | 볼 곳 |
|---|---|
| `a_reference/c1b1_exact_impulse_checker_v2.py` | `down`/`up`(150〜165행), `_sqrt_interval`, `_series_lower`/`_series_upper`/`_exp_combine`/`_exp_interval`(228〜283행), `_dv`(319〜357행), `_decide_raw`(438〜445행), `_compute`(448〜528행), `check_certificate`·`enclosure` |
| `a_reference/c1b1_point_prover.py` | 머리말(V0.1·V0.2 절), `_exp_plan`, `_exact_x`, `_dy_*`, `_full_ok`, `_zero_ok`, `_fallback_order`, `_fallback_ok`, `HINT_WORK_BITS_MAX`, `_hint_plan`, `_certified_plan`, `_cell`, `_enclosure`, `prove` |
| `a_reference/c1b1_runtime_wrapper.py` | `RuntimeContractViolation`, `_prove_and_verify`의 UNREPRESENTABLE 분기 |

## 3. 판단할 것 (lemma 6절 체크리스트 + 설계자 추가)

1. **F2:** `down`/`up` 1회의 상대 오차 < 2^−P(음수 floor 포함).
2. **F3:** checker 급수의 한쪽 반올림이 S⁻ ≤ S_n ≤ S⁺, U⁺ ≥ U_n을 지키는지.
3. **3절 3(b):** exp 폭을 (x_hi − x_lo) + 상대 꼬리로 묶는 논증. |d(1/S_n)/dx| ≤ 1이 **n에 균등**한지(S_n′ = S_{n−1} ≤ S_n, S_n ≥ 1). 급수 누적 반올림 (2n + O(1))·2^−P → 0에 n = O(P + x)면 충분한지.
4. **3절 4:** `_dv`의 반올림 위치가 식 모양으로 정해진 유한 개인지(루프 길이가 N·P에 의존하지 않음).
5. **5절 3:** `enclosure()`와 `check_certificate()`의 J가 정확히 같은지(출력 raw만 다른 cert, `_compute`는 raw를 J에 쓰지 않음). `_cell`이 `_decide_raw`와 같은 엄격 판정인지.
6. **4절 — H-B가 정리에 필요한 성질을 모두 보장하는지(설계자 강조):**
   - (i) fallback의 두 정확 비교(n+1 ≥ 2·E_UP·x_hi, n ≥ P+33)가 (C1)(n+2 > x_hi, U_n ≤ 2^−(P+32)·S_n)을 함의하는가. 부등식 사슬 (n+1)! ≥ ((n+1)/e)^{n+1}, (n+2)/(n+2−x) < 1.23. n_fb의 정의에서 두 비교가 **항상** 참인가. (비교는 Taylor 차수 n에 비례하는 반복이 없는 상수 개수의 정확 비교다. 비교 자체의 비용은 정수 비트 길이에 따라 는다.)
   - (ii) 힌트 인증기의 **건전성**: `_full_ok`/`_zero_ok`가 True면 (C1)/(C3)이 참인가. `_dy_*`의 모든 반올림 방향, `_zero_ok`의 n! ≤ e·n^{n+1/2}·e^−n.
   - (iii) 완결성이 CERT_BITS에 기대지 않는가(힌트 검사 False는 fallback으로만 간다).
   - (iv) `_exact_x`가 checker `_compute`의 x 구간과 **정확히** 같은가.
   - (v) (C2) n ≤ n_fb = O(P + x)가 모든 경로에서 성립하는가.
7. **힌트는 선택이다(4절 0):** P > 2^16에서 부동소수 planner가 호출되지 않는가. P ≤ 2^16에서 planner의 `ArithmeticError`·`ValueError`가 모두 fallback으로 가고 `prove()`의 `except ValueError`(serialization_limit)에 닿지 않는가. P ≤ 2^16에서 planner가 유한 시간에 끝나는가(`_zero_floor_order` ≤ ⌊x_lo⌋ + 2회, `_full_order`는 log-꼬리 → −∞).
8. **흐름과 유한 한도(5절 0〜5):** `prove()`의 반복이 유한한가(힌트 버림 최대 1회, `decided` 뒤 불일치는 ANOMALY). j*까지 쓰는 양(반복 수, N, P, 차수, 정수 비트, 호출 시간, 자릿수)이 모두 유한해서 그보다 큰 유한 한도를 고를 수 있는가. 그 한도에서 REFUSED·ANOMALY·`order_certification_failed`가 나올 수 없는가.
9. **UNREPRESENTABLE:** 참값이 범위 밖일 때만 나오는가. wrapper가 dt = 40에서만 `RuntimeContractViolation`을 내고 run을 바꾸지 않는가.

## 4. 판단하지 않아도 되는 것

A-EV(실행기 enclosure가 참값을 포함하는가, 별도 작업선), 실행기 자체의 정확성, 기본 운영 한도 안에서의 실제 가용성, 성능, Exact Aggregate·규모 제안서.

## 5. 결과 형식

각 항목(3절 1〜9)에 대해 **성립 / 성립하지 않음(반례·빠진 단계) / 불명확(무엇이 필요한가)** 중 하나와 근거. 코드 수정 제안은 따로 적는다. 감사 결과는 설계자가 판정한다.

## 6. 감사 기록

**1회차(2026-09-30, 대상 개정 1 / `5f1a4c7`): 불통과.** F2·F3·exp 폭·`_dv` 수렴·동일 J·UNREPRESENTABLE은 성립, fallback 부등식은 성립. 막는 구멍: 부동소수 힌트가 실제로는 필수 경로였다(`_certified_plan`이 fallback 전에 `_exp_plan`을 무조건 호출, 큰 P에서 `bits * LN2` → `OverflowError`). 문구: "budget·Limits 무한"은 코드 계약이 아니다(`range(budget.max_attempts)`). 부수: fallback "O(1)"은 부정확.

**개정 2(`8c5c4f7`):** `_hint_plan`(P > 2^16이면 planner 미호출, 그 아래 산술 예외는 fallback), 정리를 "입력마다 충분히 큰 유한 한도 존재"로, "O(1)" 표현 정정. prover 시험 48 → 54. LOCAL FULL 3333 passed + 1 xfailed, skip 0, 608.92초. 증거 `runs/c1b1_prover_v02_hint_bound_20260930/`.

**2회차(2026-09-30, 대상 개정 2 / `8c5c4f7`): 통과.** 3절 전 항목 성립. 첫 감사의 blocker는 닫혔다(P > 2^16에서 `_exp_plan` 호출 0회, `OverflowError`는 `ArithmeticError`로 잡힘, `ValueError`는 `_hint_plan` 안에서 소모). planner 종료 논증, 입력별 유한 한도 존재, `prove()` 유한 반복 성립. 남은 지적은 이 인계 문서의 낡은 문구(개정 1 제목·"무한 budget" 문장)뿐이었고 이 판에서 고쳤다(수학적 blocker 아님). 감사자가 통과시킨 명제:

> 지원되는 C1-B1 rounding-decision 입력을 고정하고 참 raw가 FX(96,80) 범위 안에 있다고 하자. Lemma A 및 Checker V2의 enclosure soundness를 전제로 하면, 그 입력에 대해 충분히 큰 유한 prover Budget과 Checker V2 Limits가 존재하며 Point Prover V0.2는 유한 단계 안에 Checker V2 `VALID` certificate를 찾는다.

**증거 등급:** 독립 수학/코드 감사 통과. proof assistant에 의한 formal certified가 **아니다.**
**이 통과로 영향을 받는 범위:** D3 / Point Prover의 rounding-decision 정성 완결성뿐. ④-Liveness 전체는 A-EV·inbound·inner·global shadowing·전체 산란각·E_min 재생성 등이 남아 **NotCertified**, ④-Safety **Conditional**, A-EV **미해결** 그대로다.
