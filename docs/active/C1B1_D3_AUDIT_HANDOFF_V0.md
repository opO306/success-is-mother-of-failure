# D3 독립 감사 인계 — Checker V2 수렴 lemma(개정 1) + Point Prover V0.2

**감사자:** GPT-5.6 Sol High(설계자 지정, 2026-09-30). 작성자(Claude)와 다른 계열이 교차 검증한다.
**감사 대상 상태:** lemma는 **초안**, ④-Liveness는 **NotCertified**. 감사가 통과해도 A-EV(별도 작업선)와 ④-Safety(Conditional)는 바뀌지 않는다.

## 1. 감사할 명제

[C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md](C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md)(개정 1)의 두 명제.

- **Lemma B-V2 (3절):** 입력 하나를 고정하고 prover V0.2의 정밀도 순서를 따라가면 checker V2 enclosure J_j의 폭 → 0.
- **조립 정리 (5절, 초안):** 지원 입력(R ≥ r_min, dr_k ≠ 0, dt_kick ≠ 0, FX(96,48) 상대 위치, 참 raw가 FX(96,80) 범위 안)에서 budget·Limits가 무한이면 `prove()`는 유한 단계에서 checker V2 VALID(참 raw)를 반환한다.

전제로 쓰는 승인된 사실: Lemma A(참값은 half-ulp 경계가 아님, 승인), D4(dt = 40에서 |J| ≤ 1277.3 a.u., 승인. `a_reference/c1b1_impulse_magnitude_bound.py`).

## 2. 읽을 코드

| 파일 | 볼 곳 |
|---|---|
| `a_reference/c1b1_exact_impulse_checker_v2.py` | `down`/`up`(150〜165행), `_sqrt_interval`, `_series_lower`/`_series_upper`/`_exp_combine`/`_exp_interval`(228〜283행), `_dv`(319〜357행), `_decide_raw`(438〜445행), `_compute`(448〜528행), `check_certificate`·`enclosure` |
| `a_reference/c1b1_point_prover.py` | 머리말(V0.1·V0.2 절), `_exact_x`, `_dy_*`, `_full_ok`, `_zero_ok`, `_fallback_order`, `_fallback_ok`, `_certified_plan`, `_cell`, `_enclosure`, `prove` |
| `a_reference/c1b1_runtime_wrapper.py` | `RuntimeContractViolation`, `_prove_and_verify`의 UNREPRESENTABLE 분기 |

## 3. 반드시 판단할 것 (lemma 6절 체크리스트 + 설계자 추가)

1. **F2:** `down`/`up` 1회의 상대 오차 < 2^−P(음수 floor 포함).
2. **F3:** checker 급수의 한쪽 반올림이 S⁻ ≤ S_n ≤ S⁺, U⁺ ≥ U_n을 지키는지.
3. **3절 3(b):** exp 폭을 (x_hi − x_lo) + 상대 꼬리로 묶는 논증. |d(1/S_n)/dx| ≤ 1이 **n에 균등**한지(S_n′ = S_{n−1} ≤ S_n, S_n ≥ 1). 급수 누적 반올림 (2n + O(1))·2^−P → 0에 n = O(P + x)면 충분한지.
4. **3절 4:** `_dv`의 반올림 위치가 식 모양으로 정해진 유한 개인지(루프 길이가 N·P에 의존하지 않음).
5. **5절 3:** `enclosure()`와 `check_certificate()`의 J가 정확히 같은지(출력 raw만 다른 cert, `_compute`는 raw를 J에 쓰지 않음). `_cell`이 `_decide_raw`와 같은 엄격 판정인지.
6. **4절 — H-B가 정리에 필요한 성질을 모두 보장하는지(설계자 강조):**
   - (i) fallback의 두 정확 비교(n+1 ≥ 2·E_UP·x_hi, n ≥ P+33)가 (C1)(n+2 > x_hi, U_n ≤ 2^−(P+32)·S_n)을 함의하는가. 부등식 사슬 (n+1)! ≥ ((n+1)/e)^{n+1}, (n+2)/(n+2−x) < 1.23. n_fb의 정의에서 두 비교가 **항상** 참인가.
   - (ii) 힌트 인증기의 **건전성**: `_full_ok`/`_zero_ok`가 True면 (C1)/(C3)이 참인가. `_dy_norm`(floor/ceiling), `_dy`, `_dy_mul_div`(나머지 있으면 올림), `_dy_add`(지수 차 > 2·CERT_BITS에서 하한은 작은 항 버림, 상한은 마지막 자리 +1), `_dy_pow_up`의 모든 반올림 방향. `_zero_ok`의 n! ≤ e·n^{n+1/2}·e^−n.
   - (iii) 완결성이 CERT_BITS에 기대지 않는가(힌트 검사 False는 fallback으로만 간다).
   - (iv) `_exact_x`가 checker `_compute`의 x 구간과 **정확히** 같은가.
   - (v) (C2) n ≤ n_fb = O(P + x)가 모든 경로에서 성립하는가.
7. **흐름:** `prove()`의 반복이 유한한가(힌트 버림 최대 1회, `decided` 뒤 불일치는 ANOMALY). 무한 Limits에서 REFUSED·ANOMALY·`order_certification_failed`가 나올 수 없는가.
8. **UNREPRESENTABLE:** 참값이 범위 밖일 때만 나오는가. wrapper가 dt = 40에서만 `RuntimeContractViolation`을 내고 run을 바꾸지 않는가.

## 4. 판단하지 않아도 되는 것

A-EV(실행기 enclosure가 참값을 포함하는가, 별도 작업선), 실행기 자체의 정확성, 기본 운영 한도 안에서의 실제 가용성, 성능, Exact Aggregate·규모 제안서.

## 5. 결과 형식(요청)

각 항목(3절 1〜8)에 대해 **성립 / 성립하지 않음(반례·빠진 단계) / 불명확(무엇이 필요한가)** 중 하나와 근거. 코드 수정 제안은 따로 적는다. 감사 결과는 설계자가 판정한다.

## 6. 현재 증거(참고)

prover 시험 48, wrapper 시험 45, 관련 묶음 498 passed + 1 xfailed, LOCAL FULL은 `CURRENT_STATE.md`의 해당 항목. 증거 폴더 `runs/c1b1_prover_v02_hb_20260930/`. 시험 통과는 증명이 아니다.
