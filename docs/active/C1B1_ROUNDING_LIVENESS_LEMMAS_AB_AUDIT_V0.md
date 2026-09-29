# C1-B1 반올림 Liveness 보조정리 A·B 감사 v0

**상태:** 구현자 감사(문서만). 코드·시험·Vast 0. **인증 아님.** "감사 통과"는 구현자가 전제와 추론 단계를 원본 코드와 대조해 오류를 찾지 못했다는 뜻이다. 증명 보조기 검증이나 외부 수학 검토는 아니다.
**현재 상태(변경 없음):** ④-Liveness NotCertified, ④-Safety Conditional(A-EV 미해결), 14/64·gap 81, ④ 미동결, ⑤ 미착수.
**근거:** 설계자 판정(2026-09-29, 아래 1절), [Liveness 경로 조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md), 동결 원본 `a_reference/ar2_lang2024.py`(C1-A), 실행기 `a_reference/c1b1_two_atom.py`.

## 0. 결론

| | 내용 | 감사 결과 |
|---|---|---|
| **Lemma A** | r ≥ r_min, dr_k ≠ 0인 모든 유리수 입력에서 정확한 충격량 J_k는 유리수가 아니다(초월수다). 따라서 half-ulp tie는 불가능하다 | **감사 통과.** 설계자가 제안한 QED short-2 단일 계수 증명이 그대로 성립한다. 9개 공통근 조사는 필요 없다. 전제는 Lindemann–Weierstrass 정리와 "정확한 값 = 공개식의 실수값" 두 가지다 |
| **Lemma B** | 독립 exact-rational certificate의 구간이 임의 정확도로 수렴하고, 각 certificate를 작은 checker가 정확 산술만으로 판정할 수 있다 | **수학적으로 성립(증명 스케치 감사 통과). 구현 전.** 남은 실제 위험은 checker가 쓰는 식이 동결 모델과 같은지(식 전사 충실도)이며, 이는 구현 단계의 시험 의무다 |
| A + B | 물리 영역에서 판정되는 모든 충격량이 유한한 exact certificate로 결정된다 → **정성적 finite rounding liveness** | D_valid의 모양과 무관하게 성립한다. ④-Liveness 인정은 checker 구현·시험·설계자 판정 뒤다 |

**정정:** 조사 v0에서 전역 tie 배제를 "새로 찾은 후보"라고 썼다. 그러나 동결 C1-A 모듈 머리말에 이미 "Lindemann-Weierstrass makes an exact tie impossible unless all transcendental coefficients vanish together"가 있다(`ar2_lang2024.py` 24〜26행, 유리수 R에서의 V·F 평가). 이번에 새로 한 것은 두 가지다. C1-B1 충격량(R = √s, 성분 인수 dr_k/R)에 적용한 것, 그리고 "모든 계수가 동시에 0"인 경우를 단일 계수로 배제한 것이다.

## 1. 설계자 판정 기록 (2026-09-29, 3차)

| # | 판정 |
|---|---|
| Q1 | **L0 = D_valid 전체 유지.** F만이나 canonical만으로 줄이지 않는다. 정정된 모양(L·H 넓은 영역 + F 14구간)을 확인했다. no-tie lemma가 성립하면 반올림 부분은 D_valid 모양과 무관하게 더 넓게 증명된다 |
| Q2 | **④-rounding의 수학적 Liveness = 정성적 finite termination.** 16384를 몰래 삭제하지 않는다. 16384는 **실행기 fast-path의 자원 한도**이고, 별도 exact certificate prover가 **correctness path**다. 계약: ≤16384에서 RESOLVED, 아니면 prover가 유한한 exact certificate를 만들어 WITNESS_RESOLVED, 그것도 못 하면 STOP. 정량적 CPU/bit 상한은 별도 **operational bound**로 관리한다. **계약 변경으로 기록한다:** 기존 ④는 "필요한 모든 판정이 MAX_PRECISION_BITS=16384 안에서 결정됨"을 명시적으로 요구했다([rounding-decision](C1B1_ROUNDING_DECISION_V1.md) 1절, CURRENT_STATE "④가 열려 있는 이유") |
| Q3/P1b | **허용.** P1a 문구를 고친다. 기준은 "평가기와 다른 수학 방법"이 아니다(`a_numeric.exp.enclosure`도 Taylor + 나머지를 쓴다). 기준은 **"16384 초과 평가기의 결과를 신뢰하지 않아도, certificate의 참/거짓을 독립적인 작은 checker가 exact arithmetic으로 판정할 수 있어야 한다"**이다. **구현 공유 금지, `C._model` 호출 금지, `a_numeric.exp.enclosure` 재사용 금지.** 같은 Taylor 정리를 써도 증명 객체와 checker가 독립적이면 허용한다 |
| Q4 | **④-rounding Liveness에서 분리.** r_min 침범 없음, 운동량·위치 overflow 없음, 포획 없이 R_J 도달은 **별도의 trajectory-completion obligation**이다. C1-B1 최종 freeze 전에 닫는다 |
| 추가 | "tie 없음"만으로 Liveness가 자동 완료되지 않는다. `no exact tie + certified enclosure convergence = qualitative finite rounding liveness`. 다음 작업은 point prover 전체 구현이나 wrapper가 아니라 **Lemma A·B 감사**다 |

## 2. Lemma A — 전역 exact tie 배제

**진술.** dr ∈ Q³, R² = Σ dr_k² ≥ r_min²(r_min = 1.2 Å / 0.529177210903), dt_kick ∈ Q, dt_kick ≠ 0, dr_k ≠ 0이라 하자. 정확한 충격량
J_k = F(R)·dr_k·dt_kick/R, F = −V′(R)(retardation ON, 동결 C1-A 식)은 **대수적 수가 아니다.** 특히 FX(96,80)의 어떤 half-ulp 경계 (m+½)·2^-80와도 같지 않다.

**증명.**
1. 원본 식(`ar2_lang2024._component`)을 지수별로 모은다. V′(R) = A(R) + Σ_{j=1..9} B_j(R)·e^{−λ_j R}.
   - A(R)는 exp가 없는 부분의 도함수다. BO C6의 −C6·g(R)/R⁶(g = 유리함수, 분모 1+ΣB_m R^m의 계수 전부 양수)과 나머지 long-range의 −C_2k/R^{2k}이 여기에 속한다. REL C4는 retardation 분기(f−1)라 exp 부분만 남는다. 계수는 전부 유리수다.
   - λ_j는 short-range 지수 6개(6.92639712, 2.34781022, 1.66833595, 3.07137482, 1.64936036, 2.29848003)와 damping 지수 3개(3.65946625, 1.05249333, 3.91638946)다. **9개 모두 서로 다른 양의 유리수**이고, 각 λ_j의 항은 e^{−λ_j R} 한 번만 나온다(e^{−2λR} 같은 항 없음).
   - B_j는 유리수 계수 Laurent 다항식이다.
2. **QED short 2**의 계수는 {0: 0, 1: 0, 2: 6.921721e-2}이므로 P(R) = cR², c = 6.921721×10⁻² ≠ 0, α = 2.29848003이다. 이 지수를 가진 다른 항은 없으므로 V′에서의 계수는 정확히 B_α(R) = P′ − αP = **cR(2 − αR)**다(`_component` 166행의 `P' − αP`와 같다).
3. R ≥ r_min이면 αR ≥ α·r_min > 2다. 정확한 부등식은 1.2 × 2.29848003 = 2.758176036 > 2 × 0.529177210903 = 1.058354421806이다. 그리고 R > 0, c ≠ 0이다. 따라서 **B_α(R) ≠ 0**이다.
4. J_k = γ(γ는 대수적 수)라고 가정하자. dr_k·dt_kick ≠ 0이므로 V′(R) = −γR/(dr_k·dt_kick)이고,
   `[A(R) + γR/(dr_k·dt_kick)]·e⁰ + Σ_j B_j(R)·e^{−λ_j R} = 0`이다.
   R = √(R²), R² ∈ Q이므로 R은 대수적 수다. 계수는 유리수 계수 유리함수를 대수적 R에서 평가한 값(분모 R^m, 1+ΣB_m R^m > 0)이므로 모두 대수적이다. 지수 0, −λ_1R, …, −λ_9R은 서로 다른 대수적 수다.
5. **Lindemann–Weierstrass(Baker 형태):** 서로 다른 대수적 수 α_i와 모두 0은 아닌 대수적 계수 β_i에 대해 Σβ_i e^{α_i} ≠ 0이다. 3에서 β_α = B_α(R) ≠ 0이므로 4의 등식은 불가능하다. ∎

**원본 대조 체크리스트**

| 전제 | 확인한 곳 |
|---|---|
| 판정되는 모든 입력은 R² ≥ r_min² | `c1b1_two_atom.impulse` 286〜287행: 미만이면 `_decide` 전에 `PhysicsDomainExceeded` |
| dr_k = 0이면 판정하지 않는다 | 같은 함수 297〜300행: `c == 0`이면 `from_exact(0)` |
| 판정 대상은 F·dr_k·dt_kick/R | 같은 함수 284, 290〜305행 |
| 모델 = 공개식, 계수는 정확한 십진수(유리수) | `ar2_lang2024.py` 5〜9, 63〜79행 |
| 초월함수는 e^{−x}뿐이고 지수는 R에 선형 | `_component` 164〜185행(`sigma` 불확도 함수의 e^{−aR²}는 V·F에 들어가지 않는다) |
| QED short 2 계수와 지수율 | 68〜69행 |
| λ 9개가 서로 다름 | 64〜74행의 정확한 유리수 비교 |
| retardation 분모 양수 | 78〜79행 RET_B 전부 양수 |
| 실행기 C1-B1 평가기가 같은 상수·같은 분기(`g − T`, `−T`, `1 − T`)를 쓴다 | `c1b1_two_atom._model_R` 179〜224행 — **같은 수학 함수**임은 구조 대조로 확인했다. 수치 일치는 기존 시험의 영역이다 |

**이 lemma가 말하지 않는 것**
- 정량 정보가 없다. d(J_k, 경계) > 0이지만 얼마나 큰지는 모른다(16384 안의 해결을 보장하지 않는다).
- 실행기 enclosure가 참값을 포함한다(A-EV)는 것과는 무관하다. A-EV는 Safety의 선행조건으로 남는다.
- 같은 논리로 입장 검사의 V(R0) 비교도 동점이 불가능하다(QED short 2의 V 계수 cR² ≠ 0). 입장 판정은 이 계약의 witness 경로 밖이라 기록만 한다.
- 보강 관찰(필요 없음): 2/α는 격자 반지름이 될 수도 없다. R² ∈ 2^-96·Z인데 (2/α)² = 4·10^16/229848003²이고 229848003은 2·5와 서로소다. 그래서 r_min 검사가 없더라도 계수 B_α는 모든 격자 입력에서 0이 아니다.

## 3. Lemma B — 독립 exact-rational certificate의 수렴과 검사 가능성

**certificate(설계, 미구현).** 입력 (dr, k, dt_kick, 출력 profile, binding)과 정수 매개변수 (N, n).
checker는 동결 상수(데이터)만 읽고 아래를 정확한 유리수로 **다시 계산·확인**한다. `C._model`, `a_numeric.exp`, `ar2_lang2024`의 평가 함수는 부르지 않는다.
1. **√:** r_lo = isqrt(⌊R²·4^N⌋)/2^N, r_hi = r_lo + 2^-N. 확인할 것: 0 < r_lo, r_lo² ≤ R² ≤ r_hi²(정확 비교).
2. **exp:** y > 0 유리수에 대해 S_n(y) = Σ_{i≤n} yⁱ/i!, T_n(y) = y^{n+1}/(n+1)!.
   S_n(y) ≤ e^y이고, Lagrange 나머지에서 e^y ≤ S_n(y) + e^y·T_n(y)이다. 따라서 T_n(y) < 1이면
   **(1 − T_n(y))/S_n(y) ≤ e^{−y} ≤ 1/S_n(y)**이다. e^{−x}는 감소함수이므로 x ∈ [λr_lo, λr_hi]에 대해 e^{−x} ∈ [(1−T_n(λr_hi))/S_n(λr_hi), 1/S_n(λr_lo)]이다.
3. **나머지 식:** 유리수 구간 산술(반올림 없음, 포함 단조)로 원본과 같은 식 구조를 평가한다. 나눗셈은 양의 구간(R^m, 1+ΣB_m R^m)으로만 한다.
4. **결론 확인:** J_k의 구간 [lo, hi]가 어떤 정수 m에 대해 (m−½)·2^-80 < lo ≤ hi < (m+½)·2^-80이면 raw = m이다. 등호가 걸리면 certificate는 거부되고 prover가 (N, n)을 올린다.

**수렴 증명.** 입력 하나를 고정한다.
(i) N → ∞이면 r_hi − r_lo = 2^-N → 0이다.
(ii) 고정된 y에서 n → ∞이면 S_n(y) → e^y, T_n(y) → 0이므로 exp 구간 폭 → 0이다. 여기에 (i)와 e^{−x}의 연속성을 더하면 exp 구간 폭 → 0이다.
(iii) 3의 식은 참값 근방에서 분모가 0에서 떨어진 유리함수다. 따라서 정확 유리수 구간 확장은 포함 단조이고 입력 폭에 대해 Lipschitz이며(Moore의 natural interval extension 수렴), 폭 → 0이다.
(iv) Lemma A로 참값과 가장 가까운 경계의 거리 d > 0이다. 참값을 포함하고 폭 < d인 구간은 참값이 속한 열린 반올림 칸 안에 있다.
따라서 유한한 (N, n)에서 4의 확인이 성공한다. prover가 N·n을 단조 증가(예: 두 배)시키며 찾으면 **반드시 끝난다.** ∎

**검사 가능성.** 1〜4는 정수·유리수의 사칙연산, 비교, isqrt뿐이다. checker는 수치 평가기의 결과를 "믿지" 않고 모든 부등식을 스스로 판정한다. 이것은 P1a/P1b 기준을 충족한다. 같은 Taylor 정리를 쓰지만 증명 객체와 checker는 실행기와 독립이다.

**감사에서 찾은 위험과 구현 의무**

| # | 위험 | 성격 | 구현 단계 의무 |
|---|---|---|---|
| B1 | **식 전사 충실도.** 독립 checker가 식을 다르게 옮기면(부호, `kadd`, retardation 분기 `g − T`/`−T`, `2k/R^{2k+1}` 항) **다른 함수의 올바른 certificate**가 된다. 독립성이 공유 버그를 막는 대신 이 위험을 만든다 | 가장 큰 실제 위험 | 실행기가 RESOLVED하는 다수 입력에서 raw 일치를 비교한다. 동결 C1-A fixture와 비교한다. 식 변형 결함 주입(분기·부호·항 누락)이 비교에서 잡히는지 확인한다 |
| B2 | 상수 binding | 중간 | 상수는 데이터로 읽되 `parameter_fingerprint`와 같은 해시를 독립 재계산해 binding한다. 평가 코드는 공유하지 않는다 |
| B3 | 필요한 (N, n)의 사전 상한 없음 | 정성 lemma의 본성 | 설계자 판정대로 operational bound(CPU·bit·시간)로 따로 관리한다. 초과는 STOP |
| B4 | 큰 y에서 Taylor 비용. 예: pre-tail y ≤ 약 7×10⁴이면 n은 수십만 항, 유리수 크기가 매우 크다 | 운영 비용(수렴에는 영향 없음) | 정확한 argument reduction(e^{−y} = (e^{−y/2^s})^{2^s}, 양수 구간 거듭제곱)은 여전히 정확 산술이다. 채택하면 lemma의 2단계에 그 부등식을 추가한다 |
| B5 | 엄격 부등식만 인정 | 설계 | tie 처리 분기를 두지 않는다(Lemma A). 경계 등호는 거부 후 정제 |
| B6 | 출력 overflow | 범위 밖 | 참값이 profile 범위 밖이면 `VMHalt` 종결 거부이지 반올림 liveness가 아니다(계약 V1 1절) |

## 4. 두 lemma가 닫는 것과 닫지 않는 것

닫는 것(설계자 승인과 checker 구현·시험을 전제로):
물리 영역(R ≥ r_min)에서 판정되는 **모든** 충격량 성분은, 실행기가 16384 안에서 RESOLVED하지 못하더라도 유한한 exact certificate로 WITNESS_RESOLVED될 수 있다. D_valid의 L·H·F 모양, 도달 집합, 에너지와 무관하다.

닫지 않는 것:
- ④-Safety의 A-EV. 다만 이 checker는 실행기 enclosure와 겹치는지 대조하는 A-EV 보강 도구로도 쓸 수 있다.
- trajectory-completion(Q4 분리).
- 운영 상한(B3).
- prover·wrapper·Proof Cache 구현.

## 5. 다음 작업 제안

1. 설계자가 A·B 감사 결과를 판정한다.
2. 승인되면 **독립 checker + 시험 구현**(설계자 권고대로 Sonnet 5.5 가능): B1 대조·결함 주입, B2 binding, 수렴 시험(cap을 낮춘 rehearsal과 경계 바로 옆 합성 입력), P1b 금지 import의 정적 검사.
3. 그 뒤 point prover 설계(거의 기계적). wrapper는 그다음이다.

## 6. 검증

LOCAL FULL 생략 / 관련 시험 해당 없음 / 이유: 문서만 변경(이 문서, 계약 V1, 조사 v0 정정, CURRENT_STATE, docs/active/README). 실행 코드·시험·fixture·동결 계약 변경 0. 기준선 숫자는 갱신하지 않는다.
