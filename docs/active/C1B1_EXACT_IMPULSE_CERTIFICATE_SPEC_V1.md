# C1-B1 exact impulse certificate · 독립 checker 사양 V1

**상태:** 사양 제안(문서만). 코드·시험 0. **설계자 승인 뒤** 독립 checker와 결함 주입 시험을 구현한다(설계자 권고: Sonnet 5.5 Medium〜High).
**근거:** [Lemma A·B 감사](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md)(accepted design basis, not frozen certificate), [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) 1·4·7절, P1a/P1b 판정.
**현재 상태(변경 없음):** ④-Liveness NotCertified, ④-Safety Conditional(A-EV), 14/64·gap 81, ④ 미동결, ⑤ 미착수. 기존 shell 인증서는 삭제·무효화하지 않고 교차검증 자료로 쓴다.

## 0. 한 줄

checker는 certificate 하나를 받아 **VALID(m) / INVALID(이유) / REFUSED(운영 한도)** 중 하나만 돌려준다.
VALID(m)의 뜻: "동결 C1-A 모델의 정확한 충격량 성분 J_k를 FX(96,80)로 반올림한 raw는 m이다." 이 판정은 정수·유리수 산술만으로 내리며, 어떤 수치 평가기의 결과도 믿지 않는다.

## 1. checker가 보는 것 / 보지 않는 것

| 본다 | 보지 않는다 |
|---|---|
| certificate JSON(아래 2절) | 실행기 상태, run, J_cache, D_valid |
| checker 파일 안에 **직접 적은** 동결 모델 상수표(십진 문자열) | `a_reference`, `a_numeric`의 어떤 모듈(import 금지) |
| 표준 라이브러리 `fractions`, `math.isqrt`, `hashlib`, `json` | numpy·mpmath·sympy·부동소수점 |

**책임 분리:** checker는 **수학적 주장의 참/거짓**만 판정한다. certificate의 입력이 실행기가 실제로 계산한 입력과 같은지, 실행기·모델 소스와 profile·dt가 같은지(binding, 계약 V1 7절)는 **runtime wrapper·Proof Cache의 책임**이다. checker는 `runtime_binding`을 읽지 않는다.

## 2. certificate 형식 (`c1b1-exact-impulse-certificate-v1`)

유리수는 `"분자/분모"` 문자열, 정수는 십진 문자열로 쓴다. **모르는 키가 있으면 INVALID**다(형식 혼동 방지).

```json
{
  "format": "c1b1-exact-impulse-certificate-v1",
  "method": "rational-taylor-geomtail-v1",
  "model":  {"contract": "c1a-ar2-lang2024-v1",
             "parameter_fingerprint": "ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e",
             "retardation": true},
  "input":  {"position_frac_bits": 48, "dr_raw": ["…","…","…"], "component": 0, "dt_kick": "20/1"},
  "output": {"width": 96, "frac_bits": 80, "raw": "…"},
  "proof":  {"sqrt_bits": "N",
             "exp": [{"rate": "λ", "mode": "full" | "zero_floor", "order": "n"}, … 9개]},
  "runtime_binding": { … 계약 V1 7절 필드 + checker_sha256 … }
}
```

- `dr_raw`: 상대 위치 raw 정수(r_j − r_i). dr = dr_raw·2^-48.
- `exp`: 아래 3.3의 **고정 순서** 9개. 각 rate는 checker 상수표의 정확한 유리수와 같아야 한다.
- certificate에는 **매개변수만** 담는다(N, 각 exp의 모드·차수). 중간값은 넣지 않는다. checker가 매개변수에서 결정적으로 다시 계산한다.

## 3. checker 절차 (규범)

모든 값은 정확한 유리수 닫힌 구간 [lo, hi]다. 반올림하지 않는다.

### 3.1 모델 binding
1. checker 내장 상수표로 `parameter_fingerprint`를 **C1-A와 같은 문자열 형식**으로 다시 계산한다. 형식은 `ar2_lang2024.parameter_fingerprint`의 구성과 같게 문서화해 옮긴다. SIGMA 상수도 해시에 들어가므로 함께 적는다.
2. 계산값 = checker 안의 동결 리터럴 `ada6153b…839e` = certificate의 값이어야 한다. 하나라도 다르면 INVALID(`model_binding`).
3. `contract == "c1a-ar2-lang2024-v1"`, `retardation == true`(v1은 ON만).

### 3.2 입력
4. `position_frac_bits == 48`, component ∈ {0,1,2}, dt_kick ≠ 0.
5. `dr_raw[k] == 0` → INVALID(`not_a_decision`). 실행기는 이 성분을 판정하지 않고 정확히 0을 낸다.
6. R² = Σ dr_i². R²·(529177210903/10¹²)² < (6/5)²이면 INVALID(`physics_domain`). 실행기에서는 판정 전 `PhysicsDomainExceeded`인 경우다.

### 3.3 √ 구간
7. N은 정수, 1 ≤ N ≤ N_MAX. a = isqrt(⌊R²·4^N⌋), r_lo = a/2^N, r_hi = (a+1)/2^N.
8. 확인: r_lo > 0, r_lo² ≤ R² ≤ r_hi²(정확 비교). R_iv = [r_lo, r_hi].

### 3.4 exp 구간 (Lemma B, 정정된 표현)
고정 순서: BO short 1(6.92639712), BO short 2(2.34781022), REL short 1(1.66833595), REL short 2(3.07137482), QED short 1(1.64936036), QED short 2(2.29848003), BO long η(3.65946625), REL long η(1.05249333), QED long η(3.91638946).

각 rate λ에 대해 x_lo = λ·r_lo, x_hi = λ·r_hi, n = order(0 ≤ n ≤ n_MAX)로 둔다.
S_n(y) = Σ_{k≤n} y^k/k!, t_{n+1}(y) = y^{n+1}/(n+1)!, U_n(y) = t_{n+1}(y)·(n+2)/(n+2−y)이다.

| 모드 | 조건 | E(λ) = e^{−λR} 구간 | 근거 |
|---|---|---|---|
| `full` | n+2 > x_hi | [1/(S_n(x_hi)+U_n(x_hi)), 1/S_n(x_lo)] | 0 ≤ e^y−S_n ≤ U_n(기하급수 꼬리), e^{−x} 감소 |
| `zero_floor` | 없음 | [0, 1/S_n(x_lo)] | e^{−x} > 0, S_n ≤ e^{x} |

조건을 어기면 INVALID(`exp_condition`)다. **Liveness 증명(Lemma B의 수렴)은 `full`만으로 성립한다.** `zero_floor`는 항상 건전한 운영 지름길이다. 큰 x에서 대부분의 항은 ulp보다 훨씬 작아 하한 0으로 충분하고, n이 작으면 1/S_n ≤ n!/x^n이 매우 작다. 예: x ≈ 7×10⁴이면 `full`은 수십만 항이 필요하다.

### 3.5 dV/dR 구간 (동결 `ar2_lang2024._component`, deriv=True, retardation ON과 같은 식)

구간 규칙: 덧셈·뺄셈은 끝점별, 곱셈은 네 곱의 min/max, 나눗셈은 **lo > 0인 구간으로만**(아니면 INVALID). R^m은 m ≥ 0이면 [r_lo^m, r_hi^m], m < 0이면 [r_hi^m, r_lo^m]. 유리수 상수 c와 곱할 때는 부호에 따라 끝점을 바꾼다.

```
dV/dR = Σ_{comp ∈ BO,REL,QED} [ Σ_{short (α, P)} E(α)·(P'(R) − α·P(R))
                                − Σ_{k ∈ C_comp} C_2k · ( dD_k·R^{−2k} − 2k·D_k·R^{−2k−1} ) ]

x = η_comp·R,   n_k = 2k + kadd_comp,   Σ_k = Σ_{i≤n_k} x^i/i!,   T_k = E(η_comp)·Σ_k
base_k = η_comp · E(η_comp) · x^{n_k}/n_k!
  BO,  k = 3 (kmin):  D_k = g(R) − T_k,   dD_k = base_k + g'(R)
  REL, k = 2 (kmin):  D_k = −T_k,          dD_k = base_k
  그 밖:              D_k = 1 − T_k,       dD_k = base_k
g = Nr/Dn,  Nr = 1 + Σ_{m=0..4} A_m R^{m+1},  Dn = 1 + Σ_{m=0..5} B_m R^{m+1}
g' = (Nr'·Dn − Nr·Dn') / (Dn·Dn)
kadd: BO 1, REL 0, QED 0.   kmin: BO 3, REL 2, QED 3(QED는 특수 분기 없음)
```

같은 R_iv·x·E(η)를 여러 번 쓰므로 구간이 과대평가된다(의존성). 그래도 건전하고, 입력 폭 → 0이면 폭 → 0이다.

### 3.6 충격량과 판정
9. G = −(dV/dR) × [1/r_hi, 1/r_lo], J = G × (dr_k·dt_kick)(스칼라, 부호에 따라 끝점 교환).
10. u = 2^-80, m = output.raw. **(m − ½)·u < J.lo 그리고 J.hi < (m + ½)·u**(엄격)이고 −2^95 ≤ m ≤ 2^95 − 1이면 **VALID(m)**.
    구간이 경계에 닿거나 걸치면 INVALID(`not_separated`), 다른 칸이면 INVALID(`raw_mismatch`), 범위 밖이면 INVALID(`out_of_range`)다.
    엄격 분리이므로 tie 규칙(half-even)은 판정에 쓰이지 않는다. tie 불가능은 Lemma A다.

### 3.7 운영 한도
N_MAX, n_MAX, 유리수 크기(비트) 상한, 시간 상한을 넘으면 계산을 멈추고 **REFUSED(`operational_limit`)**를 돌려준다. 이것은 참/거짓 판정이 아니다. 기본값은 구현 단계에서 정해 결과에 기록한다. Liveness의 정량 상한이 아니라 설계자 판정의 operational bound다.

## 4. 건전성과 완결성

- **건전성:** 3.3〜3.5의 각 구간은 참값을 포함한다(Lemma B의 부등식과 구간 산술의 포함 단조성). 따라서 J_k ∈ [J.lo, J.hi]이다. 10의 엄격 분리에서 정확한 반올림 결과는 m이다. 평가기를 믿지 않으며 A-EV에 의존하지 않는다.
- **완결성(정성):** R ≥ r_min이고 dr_k ≠ 0인 모든 입력에 대해 `full` 모드의 어떤 유한 (N, n₁…n₉)가 VALID를 만든다(Lemma A + B, 운영 한도 무시). 상한은 주지 않는다.
- **주의:** checker 식이 동결 모델과 다르게 옮겨지면 "다른 함수의 건전한 certificate"가 된다(감사 B1). 이것은 시험으로만 막는다(5절). 식 전사의 형식 증명은 없다.

## 5. 구현 단계 시험 의무 (3단계)

| # | 시험 | 잡아야 하는 것 |
|---|---|---|
| T1 | 정적 import 검사(AST): 표준 라이브러리 4개 외 import 0, `a_reference`·`a_numeric` 문자열 import 0 | P1b 독립성 위반 |
| T2 | 내장 상수표 지문 = `ar2_lang2024.parameter_fingerprint()`(시험에서만 import) | 상수 전사 오류 |
| T3 | **교차검증:** 실행기가 RESOLVED하는 입력 수천 개(안쪽 R 2.3〜20 3D, 바깥 shell 0〜26, x·y·z축, 기울어진 방향, 65 multi-output 점, shell 15〜18 hard-case 후보 표본, shell 24〜26 후보 3개). prover 대용 두 배 탐색으로 certificate를 만들고 checker VALID raw = 실행기 raw | 식·분기 불일치 |
| T4 | **식 결함 주입**(checker 사본 변형): short 계수 부호, α 한 자리, `kadd` 0/1 교환, BO/REL retardation 분기 교환(g−T ↔ 1−T ↔ −T), `2k` → `k`, `P'−αP` → `P'+αP`, g' 분자 부호, dt·성분 인수 누락 | T3에서 raw 불일치 또는 INVALID로 **반드시** 잡힘. 안 잡히는 변형이 있으면 그 변형을 잡는 입력을 T3에 추가 |
| T5 | exp 부등식 단위 시험(시험에서만 mpmath 고정밀): 다양한 (y, n)에서 1/(S_n+U_n) ≤ e^{−y} ≤ 1/S_n, `zero_floor` 상한. 변형 U_n의 (n+2)→(n+1), 꼬리 항 하나 빠뜨림, x_lo/x_hi 교환 | 나머지 상한·단조성 오류(교차검증에서 안 보일 수 있는 경계 근처 결함) |
| T6 | √ 변형: r_hi = r_lo, a−1 | 구간이 참값을 놓치는 결함 |
| T7 | 음성 시험: raw ±1, dr_k = 0, R < r_min, 모르는 키, 지문·rate·순서 변조, N 너무 작음(`not_separated`), full 조건 위반, 범위 밖 raw | 각각 의도한 이유로 INVALID |
| T8 | **rehearsal:** 실행기 cap을 128로 낮춰 STOP한 입력에서 두 배 탐색 → certificate VALID → raw = cap 16384 정상 실행 결과. 폭이 N·n 증가에 따라 줄어드는지 기록 | 수렴·재개 경로 |
| T9 | 운영 한도: 한도 초과는 REFUSED이고 VALID·INVALID가 아님 | 한도가 참/거짓을 오염시키지 않음 |

추가(선택, 증명 아님): 실행기 `_model` 구간과 checker 구간이 겹치는지 대조하는 A-EV spot-check. 겹침은 둘 다 참값을 포함하는 데 필요한 조건일 뿐이며 A-EV 증명이 아니다. ④-Safety Conditional은 그대로다.

## 6. 설계자 확인 요청

| # | 질문 | 구현자 의견 |
|---|---|---|
| S1 | `zero_floor` 모드를 v1에 포함할지 | **포함.** 건전하고, 큰 R에서 `full`의 비용(수십만 항)을 없앤다. Liveness 증명은 `full`에만 의존한다고 명시한다 |
| S2 | certificate에 매개변수만 담고 checker가 재계산하는 방식 | **채택.** 중간값을 담으면 크기만 커지고 checker는 어차피 다시 계산해야 한다 |
| S3 | checker 상수표를 checker 파일에 직접 적고, 지문 일치로 동결 상수와 묶는 방식 | **채택.** 평가 코드 공유 없이 상수 동일성을 보장한다 |
| S4 | 운영 한도 기본값을 구현 단계에서 정해 기록 | 채택 제안. 변경은 결과 기록에 남긴다 |

## 7. 이번에 하지 않은 것

checker·prover·wrapper·Proof Cache 코드, 시험, Vast 사용. 기존 shell 인증서·coverage·실행기·D_valid 변경 없음.
