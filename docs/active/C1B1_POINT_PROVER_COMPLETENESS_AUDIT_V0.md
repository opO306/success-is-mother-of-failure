# C1-B1 Point Prover 정성적 완결성 감사 V0 (문서·수학만)

**상태:** 감사 결과 **분류 B** — 수학적으로는 가능하지만 현재 `prove()` 경로에 실제 구멍이 있다. **코드 변경 없음, 설계자 판정 전 수정하지 않음.** 기준 HEAD `af0a341`.
**질문(설계자, 2026-09-30):** 현재 Point Prover의 unbounded precision schedule이 지원되는 모든 exact impulse 입력에서 반드시 유한 단계 안에 Checker V2 VALID certificate를 찾는가?
**읽은 것(전부):** `a_reference/c1b1_point_prover.py` 전체, `a_reference/c1b1_exact_impulse_checker_v2.py` 전체(1〜566행), [Lemma A·B 감사](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md) 2·3절, `c1b1_two_atom.impulse`/`_decide`(이전 작업에서 읽음).
**현재 상태(변경 없음):** A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**.

## 0. 결론

| 연결 | 판정 |
|---|---|
| 1. Lemma A (d > 0) | **성립.** 대상 입력 전부에 적용된다(1절) |
| 2. 비신뢰 estimate가 결국 안정되는가 | 극한에서는 안정된다(mpmath 정확도 가정 아래). **그러나 수락 규칙이 안정 전에 틀린 raw를 받아들이는 것을 배제하지 못한다 → 구멍 H1** |
| 3. N 증가 시 V2 enclosure 폭 → 0 | **성립하지만 문서화된 lemma가 없다.** 승인된 Lemma B는 V1형 정확 유리수 certificate(매개변수 N, n)에 대한 것이다. V2의 outward dyadic 반올림(P), `zero_floor` 모드, 부동소수로 고른 차수까지는 덮지 않는다. 확장 증명 스케치는 3절(빈칸 G1, 구멍 아님) |
| 4. prove() schedule이 N*을 넘는가 | N은 `round64(1.5N + 1)`로 **엄격 증가·무한**, P = N + 96도 무한, exp 차수도 P를 따라 증가한다. **단, 이 경로를 타는 것은 raw m이 맞을 때뿐이다.** m이 틀리면 `raw_mismatch` → ANOMALY로 **영구 정지**(설계상 재시도 없음) → H1 |
| 5. 그 시점 certificate가 VALID인가 | m이 참 raw이면 **VALID**(J가 참값을 포함하므로 그 전까지는 `not_separated`만 나온다). m이 틀리면 VALID가 될 수 없다 |
| 6. 운영 한도 분리 | 기본 budget·Limits·Python 정수 문자열 한도는 모두 EXHAUSTED/REFUSED(가용성)로 끝나며 수학 명제를 깨지 않는다(5절). **예외 하나: `estimate_out_of_output_range`는 운영 한도가 아니라 추정값 기반 즉시 정지다 → 구멍 H2** |

**따라서 지금 "Point Prover qualitative completeness lemma"를 쓸 수 없다.** 현재 코드 그대로의 정직한 명제는 "비신뢰 mpmath 추정이 맞는 raw를 받아들이는 경우에 한해 완결"이다. 완결성(Liveness)이 **비신뢰 구성요소의 정확성에 기대고 있다.** 건전성(Safety)은 그렇지 않다.

## 1. Lemma A — 대상 입력 전부에 적용됨

Lemma A의 가정은 dr ∈ Q³, R² ≥ r_min², dt_kick ∈ Q∖{0}, dr_k ≠ 0이다. 대상 입력과 대조했다.

| 대상 조건 | 근거 |
|---|---|
| R ≥ r_min | 실행기 `impulse`가 `_decide` 전에 `PhysicsDomainExceeded`. checker V2도 `physics_domain` INVALID로 같은 경계를 적용 |
| dr_k ≠ 0 | 실행기는 `c == 0`이면 `from_exact(0)`(판정 없음). prover는 NOT_A_DECISION |
| dt_kick ≠ 0 | canonical dt = 40 → dt_kick = 20. prover·checker 모두 0을 거부 |
| FX(96,48) 상대 위치 | 두 위치 raw는 [−2^95, 2^95−1]이므로 차이의 절댓값은 2^96 − 1 이하이고, checker의 `input_range`(|dr_raw| < 2^96)를 만족한다 |

따라서 지원되는 모든 입력에서 **d = |y − (가장 가까운 half-ulp 경계)| > 0**이다(y = J/ulp). d의 크기는 모른다(정성).

## 2. 구멍 H1 — raw를 비신뢰 추정이 고정하고, 틀리면 영구 정지

**코드:** `prove()`는 `_estimate()`가 준 m을 한 번 정하고 바꾸지 않는다(267행). 이후 루프는 `not_separated`일 때만 N을 올린다(288〜290행). 다른 INVALID, 특히 `raw_mismatch`는 ANOMALY로 끝난다(291행). ANOMALY는 재시도하지 않는 것이 설계자 원칙이다(모듈 머리말 11행, 23〜25행).

**결과:** m ≠ 참 raw m*이면, N이 충분히 커져 J가 m*의 칸 안으로 들어가는 순간 checker는 `raw_mismatch`를 낸다(`_decide_raw` 443〜444행). 그러면 prover는 ANOMALY로 멈춘다. **그 입력에 대해서는 어떤 budget으로도 FOUND가 나오지 않는다.**

**수락 규칙이 틀린 m을 배제하는가:** `_estimate()`는 정밀도 p와 p/2의 두 추정이 dist > 8·err를 만족하면 수락한다. 여기서 err = max(|y_p − y_{p/2}|, |y_p|·2^{−(p/2−8)})이다(145〜167행).
- 틀린 수락이 일어나려면 y_p가 경계 반대편에 있어야 한다. 그러면 |y_p − y| ≥ dist(y_p)이고, 수락 조건에서 |y_{p/2} − y| ≥ (7/8)·dist(y_p)이다. 즉 **두 정밀도가 거의 같은 크기로 함께 틀려야** 하고, 그 오차는 |y_p|·2^{−p/2+11}보다 커야 한다. 경계 근처에서는 |y| ≳ 1/2이므로 오차 > 약 2^{−p/2+10} ulp가 필요하다(첫 수락 가능 p = 1024).
- mpmath의 문서상 정확도(오차 ≲ 항 절댓값 합 × 2^{−p})를 **가정하면**, canonical 입력(dt_kick = 20, 유계 R)에서는 이 조건이 수백 비트의 여유로 불가능하다. **그러나** (a) 이것은 제3자 비신뢰 코드의 정확도 가정이고, (b) prover API는 임의의 유리수 dt_kick을 받는다(합성 2^-17000 사례의 dt는 17,600비트). 항 절댓값 합이 커지면 여유는 줄어든다. (c) `_dv_mp`는 prover가 스스로 옮긴 식이다. 전사 오류가 있으면 **틀린 m을 일관되게** 수락한다. 이것이 바로 ANOMALY가 잡으려던 경우다.
- 결론: 수락 규칙은 휴리스틱이며(prover 설계 V0에도 "틀리면 ANOMALY"로 공개됨), 신뢰 구성요소만으로 완결성을 증명할 수 없다.

**성격:** 건전성 결함이 아니다(틀린 raw는 절대 FOUND가 되지 않는다). **Liveness가 비신뢰 추정에 의존하는 결함이다.**

## 3. 빈칸 G1 — Lemma B의 V2 확장(증명 가능, 미작성)

승인된 Lemma B는 반올림 없는 정확 유리수 구간(매개변수 N, n, `full` 모드)의 수렴을 증명한다. V2는 여기에 세 가지를 더한다. 입력 하나를 고정하고 prover schedule(N → ∞, P = N + 96, 차수는 `_exp_plan`)을 따라가는 **확장 스케치**:

1. **√:** 폭 2^−N → 0(V1과 같음). `r.lo > 0`은 R² ≥ r_min² > 1이므로 N ≥ 1에서 성립한다.
2. **outward dyadic 반올림:** `down`/`up`은 가수 P+1〜P+2비트이므로 반올림 1회의 상대 오차는 2^−P 이하다. 한 enclosure의 반올림 횟수는 (고정 항 수) + O(exp 차수 n)이다. prover는 Taylor 꼬리 < 2^−(P+48)이 되도록 n을 고르므로, 고정된 x에서 n = O(P) 이하다. 누적 상대 오차 ≲ (1 + 2^−P)^{O(P)} − 1 → 0.
3. **exp:** `full`(n+2 > x.hi)은 Lemma B (ii)와 같이 폭 → 0이다. `zero_floor`는 [0, 1/S_n(x.lo)]이고 폭이 줄지 않지만, prover는 x^n/n! ≥ 2^{P+88}을 만족하는 n ≤ x_lo + 2가 있을 때만 이 모드를 고른다. 이때 폭 ≤ 2^{−(P+88)} → 0이다. 또 P > 약 x/ln2가 되면 그런 n이 없어 `full`로 넘어간다. 두 경우 모두 폭 → 0.
4. **부동소수로 고른 차수:** 차수가 부족하면 폭이 커질 뿐 건전성은 checker가 지킨다(`U_n`을 스스로 계산). 폭 → 0에 필요한 것은 P → ∞에서 n → ∞뿐이고 `_full_order`가 그것을 보장한다. `exp_condition`(n+2 > x.hi)은 prover가 n ≥ ⌈x_hi,float⌉ − 1로 약 1의 여유를 둔다. x < 2^52이면(R은 FX(96,48) 범위에서 약 1.4×10^14 bohr 이하, x ≲ 10^15) float 오차가 그 여유를 넘지 않는다. 이 논증은 경계가 빠듯하므로 lemma로 쓸 때 정확한 상한으로 다시 확인해야 한다.
5. **나머지 식:** 양의 분모(1 + ΣB_m R^m ≥ 1, r.lo > 0)로만 나누는 연속 유리식이므로 Moore 수렴(Lemma B (iii))이 적용된다.
6. 따라서 폭(J) → 0이다. Lemma A(d > 0)와 합치면 유한 N*에서 J ⊂ (m* − ½, m* + ½)·ulp이다.

이 확장은 **스케치**이며 독립 감사를 받지 않았다. 구멍은 아니지만 완결성 lemma의 필수 구성요소다.

## 4. 구멍 H2 — 추정 범위 밖에서 즉시 정지

`_estimate()`는 **어느 정밀도에서든** |y_p| > 2^{97}이면 곧바로 EXHAUSTED(`estimate_out_of_output_range`)를 낸다(153〜154행). 정밀도를 더 올리지 않는다. 참값이 범위 안이어도 낮은 정밀도 추정이 크게 틀리면 FOUND로 가는 경로가 없다. 이 상태는 운영 한도(budget·limit)가 아니라 **추정값에 따른 판단**이다. EXHAUSTED로 분류돼 있어도 "한도를 올리면 풀린다"는 성질이 없다. 실제로 일어날 가능성은 H1보다 훨씬 작지만 논리적 구멍이다.

**범위 밖 관련 사실(구멍 아님, 범위 공개):** 참값이 FX(96,80) 출력 overflow 경계 근처이면 실행기 `_decide`가 한쪽 끝은 `VMHalt`, 다른 쪽은 raw여서 계속 정제하다 STOP할 수 있다. 이 STOP은 현재 certificate 형식으로 표현할 수 없다(raw가 범위 밖). Lemma B 감사 B6는 overflow를 범위 밖으로 두었다. D_valid에서는 |J|가 2^15 a.u.에 한참 못 미친다고 보지만, **그 상한을 정확히 확인한 기록은 이번에 찾지 못했다.** 완결성 lemma에는 "참 raw가 출력 범위 안이고 overflow 경계가 아님"을 가정으로 적거나 D_valid 상한을 인용해야 한다.

## 5. 운영 한도 — 수학 명제와 분리됨

| 한도 | 결과 | 성격 |
|---|---|---|
| prover `max_attempts` 16, `max_sqrt_bits` 65536, `estimate_max_bits` 2^17, `seconds_max` | EXHAUSTED(`prover_budget:*`, `estimate_budget`) | 가용성 |
| checker `sqrt_bits_max`/`work_bits_max` 65536, `order_max` 200000, `bits_max` 4×10^6, `seconds_max` 600, `digits_max` 4300 | REFUSED → prover EXHAUSTED(`checker_refused:*`) | 가용성. REFUSED가 나면 prover는 더 큰 N을 시도하지 않고 멈춘다(더 커도 거부되므로 타당) |
| Python int/str 변환 한도 | EXHAUSTED(`serialization_limit`) 또는 REFUSED(`integer_size_limit`) | 가용성 |

이 한도들을 무한대로 두면 1〜3절의 경로가 막히지 않는다. **기본 한도 안에서 모든 STOP이 풀린다는 보장은 없다**(Lemma B 감사 B3와 같다). 정성 명제와 기본 budget을 섞지 않는다.

## 6. 설계자 판단이 필요한 것 (코드 수정 전)

| # | 선택지 | 효과 | 구현자 의견 |
|---|---|---|---|
| D1 | **raw를 신뢰 enclosure로 정한다.** 추정은 시작 N을 고르는 힌트로만 쓴다. 매 시도에서 checker V2의 enclosure J를 계산하고(`enclosure()` 진단 경로 또는 같은 `_compute`), J가 한 칸 (m′ ± ½) 안에 엄격히 들어가면 그 m′으로 certificate를 만들어 `check_certificate`로 최종 판정한다. 추정과 enclosure가 다르면 **기록**만 하고 멈추지 않는다 | H1 제거. 완결성이 Lemma A + G1(V2 수렴)만으로 서고, mpmath 정확도 가정이 Liveness에서 빠진다. 결정론 유지 | **권고.** ANOMALY의 의미가 바뀐다. 지금 ANOMALY가 잡는 "prover 전사와 checker의 불일치"는 진리값에 영향이 없고(checker가 판정), 식 전사 충실도(B1)는 checker 대 실행기 교차검증이 맡는다. 그래도 "ANOMALY 재시도 금지" 원칙을 바꾸는 것이므로 판정이 필요하다 |
| D2 | `estimate_out_of_output_range`에서 멈추지 않고 정밀도를 계속 올린다. D1을 채택하면 추정은 힌트일 뿐이라 이 정지 자체가 필요 없어진다 | H2 제거 | D1과 함께 |
| D3 | G1(Lemma B의 V2 확장)을 정식 lemma로 쓰고 독립 감사 | 완결성 lemma의 전제 확보 | D1/D2 뒤, 한 문서로 |
| D4 | 출력 overflow 경계와 D_valid의 \|J\| 상한을 lemma 가정으로 명시 | 범위 공개 | 상한은 기존 기록을 인용하거나 정확 부등식으로 한 번 확인 |

D1〜D4가 끝나면 쓸 수 있는 명제(초안, 아직 주장하지 않음): *대상 입력(1절)에서 참 raw가 출력 범위 안이고 overflow 경계가 아니면, budget·Limits가 무한인 `prove()`는 유한 단계에서 FOUND(checker V2 VALID)를 반환한다.*

## 7. 하지 않은 것

코드 수정, 계산 실행, 무작위 시험, budget 확대 실측, shell 전수조사, Proof Box, Warehouse, A-EV, D_valid 축소, ④-Liveness 승인 기록. **④-Liveness는 NotCertified 그대로다.**
