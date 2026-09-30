# C1-B1 inbound V0 — 시간역전 lemma(TR)와 inbound outer handoff 계약

**문서 분류: 현재 활성 A / C1-B1.** 활성 Gate는 C1-B1, outer formal bound ④ 진행. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
**상태:** 구현자 작성. **설계자 판정 2026-09-30: IN-1 승인, IN-2 inbound V1 먼저, IN-3 승인, IN-4 실행기 변경 없이 기록(문구 제한 부가).** Lemma TR의 독립 감사는 없다. 날짜 2026-09-30. 기준 HEAD `c3e0e3c`.
**지시(설계자 2026-09-30):** inbound V0. KDK + drift v2 + half-even의 정확한 시간가역성을 lemma와 회귀시험으로 고정하고, outgoing 구조 중 역방향 재사용 가능/불가능을 나누고, inbound handoff의 입력·출력·실패 조건을 적는다. inner·global shadowing·전체 산란각·E_min 재생성은 하지 않는다. 판정 대상은 "inbound outer 구간을 기존 outgoing 구조와 연결할 수 있는가"까지다.
**코드:** `a_reference/c1b1_time_reversal.py`(새 파일, 실행기 변경 0), 시험 `tests/test_c1b1_time_reversal.py` 7개.

## 0. 한 줄 판정

**연결할 수 있다 — 단, 시간역전만으로는 아니다.** outgoing의 1-step 상한·힘 envelope·shell 덮개·zero-impulse 반경·packet 형식·실패 의미는 inbound에 그대로 쓴다. 그러나 **inbound 순방향 infall(바깥 → R = 20)을 보장하는 shell 귀납은 시간역전으로 얻어지지 않는다.** T는 순방향 inbound 궤도를 **역방향** outgoing 궤도로 보내고, ④-2 귀납은 알려진 입구에서 **순방향**으로 가는 명제이기 때문이다. inbound에는 같은 모양의 작은 **거울 귀납 하나**(스칼라 부등식 몇 줄, 4절)가 새로 필요하다. 거대한 inbound 탐색은 필요 없다.

## 1. 먼저 공개: 전제 정정 세 가지

1. **조사 문서 R2의 "④-2 귀납 구조를 inbound에도 공유"는 과장이었다.** 공유되는 것은 귀납의 **모양**이지 **정리**가 아니다(3절). 조사 문서에 정정을 달았다.
2. **조사 문서 6.2의 "drift 선분 domain 검사도 선분 대칭이다"는 틀렸다.** 역방향 step의 선분은 순방향 선분을 drift 반올림 잔차 d(|d_k| ≤ 2^−48)만큼 **평행이동**한 것이다. 그래서 r_min 바로 위(격자 한 칸 안)에서는 순방향은 합법인데 정확한 역방향이 guard에 걸리는 **실제 반례**가 있다(2절 (ii), 시험). **outer inbound에서는 R ≥ 20이라는 기하학적 여유 때문에 무관하다. 전체 D_valid/inner에 대해 무관하다고 아직 일반화하지 않는다(반례는 E ≫ 10 De라는 것만 보였을 뿐 D_valid 궤도가 r_min 한 칸 위에 오지 않는다는 증명이 아니다).** 실행기 사상의 실제 성질이다.
3. **"inbound"라는 말이 두 가지로 쓰였다.** Runtime Rounding Contract V1은 inbound를 "R 20 → 최근접"(즉 R < 20 안쪽)으로 적었다. 이번 지시의 inbound는 **바깥 영역 R ≥ 20에서 안으로 들어오는 구간**이다. 이 문서는 뒤의 뜻만 다룬다. 앞의 뜻은 inner의 일이다.
   - 코드 확인: D_valid의 L·H 부분은 출발 반지름·방향을 제한하지 않는다(`evaluate_run`의 비-canonical 가지). **R ≈ 28.4에서 안으로 들어오는 상태(E ≈ 4.4 De, b = 5)도, R ≈ 10에서 출발하는 상태도 `numerical_validated`다**(시험에서 확인). 그래서 바깥 inbound 구간은 D_valid에 실제로 있다. canonical F 상태는 R = 20 출발이라 바깥 inbound 구간이 0 step이다.

## 2. Lemma TR (정확한 시간역전) — 코드로 고정

**설정.** 위치·운동량 FixedPoint(from_exact는 half-even이라 round(−x) = −round(x)), drift v2(변위를 반올림한 뒤 정확히 더함). T는 모든 운동량 raw의 부호를 바꾸고 위치는 그대로 둔다. `step(s0)`가 성공해 s1이 되고 s0의 J_cache가 None 또는 J(q0)라고 하자. 저장·반 step 운동량 raw가 profile 최솟값(−2^95, 부호를 바꾸면 범위 밖)이 아니면, `step(T s1)`(J_cache = J(q1) 유지 또는 None)은

- **(i)** 정확히 T s0를 돌려주거나(J_cache = J(q0)),
- **(ii)** drift **선분** guard에서 `PhysicsDomainExceeded`를 낸다. 이것은 **정확히** `segment_min_R2(q0 + d, v·h) < r_min²`일 때다. v·h는 순방향의 정확한 상대 drift, d = q1 − q0 − v·h는 그 반올림 잔차(|d_k| ≤ 2^−48)다.

다른 예외는 없다. 역방향 step이 쓰는 충격량은 q1과 q0에서의 값뿐이고 둘 다 순방향이 이미 판정했다(같은 반올림 질문 → 같은 STOP·같은 Proof Cache witness. cache 열쇠는 상대 위치·성분·dt_kick이다). 저장하는 모든 수는 순방향이 저장한 수의 부호 반대다.

**증명.** `_kick`은 p_i − J, p_j + J이고 J는 위치만의 함수다. 순방향: p′ = (p_i0 − J0, p_j0 + J0), p1 = (p_i′ − J1, p_j′ + J1). 역방향 첫 kick(q1): −p_i1 − J1 = −p_i′, −p_j1 + J1 = −p_j′. drift는 −p′h/m을 −round(p′h/m)으로 반올림하므로 위치가 r0로 정확히 돌아온다. 둘째 kick(q0): −p_i′ − J0 = −p_i0, −p_j′ + J0 = −p_j0. 저장 끝점 guard는 |q0|²를 보는데 순방향이 이미 합법으로 저장한 값이다. 선분 guard가 보는 집합은 {q1 − s·v·h} = {q0 + d + (1−s)·v·h}다. ∎

**N step 따름정리.** 순방향 N step이 모두 성공하고 각 step에서 (ii)가 일어나지 않으면, T s_N에서 N step은 T s_{N−1}, …, T s0를 차례로 지난다. 각 순방향 선분의 최소 R이 r_min + √3·2^−48 이상이면 (ii)는 일어나지 않는다(삼각부등식). 바깥 영역에서는 자명하다.

**코드.** `c1b1_time_reversal.time_reverse(run)`(T, 전제 위반은 `NotReversible`), `forward_drift(run)`(다음 step의 q0·v·h·저장 변위·d), `reverse_segment_passes(run)`((ii)의 정확한 예측). 실행기(`c1b1_two_atom`)는 바꾸지 않았다.

**시험(7개, 30.8초).**
1. **D_valid 산란 사건 전체의 역추적:** R ≈ 28.4 inbound(H 부분, `numerical_validated`) → 안쪽 벽(R < 7) → R > 20 outbound, 3,600 step. 역방향 run이 **모든 중간 상태**를 비트 단위로 되짚고 J_cache까지 맞는다.
2. 역방향 run이 묻는 충격량 질문은 모두 순방향이 판정한 질문의 부분집합이다(안쪽 벽을 지나는 700 step, J_cache 유지·폐기 둘 다).
3. 역방향 선분 = 순방향 선분 + d, |d_k| ≤ 2^−48, d ≠ 0.
4. **반례:** r_min 바로 위 격자점에서 바깥으로 가는 상태(스트레스 상태, E ≫ 10 De). 순방향 합법, 역방향은 선분 guard에서 거부, `reverse_segment_passes`가 미리 False로 예측. guard만 살짝 낮추면 정확히 T s0로 돌아온다(사상 자체는 가역). 잔차가 간격보다 작으면 예측 True, 정확히 돌아온다.
5. D_valid는 T에 대해 닫혀 있지 않다: H 상태의 T 상은 같은 E·b라 같은 판정, canonical F 상태의 T 상은 비-canonical이라 `unsupported`.
6. 전제 위반 거부(운동량 raw = 최솟값, drift v1).
7. 결함 주입: drift를 floor(홀함수가 아님)로 바꾸면 한 step 왕복이 돌아오지 않는다.

## 3. 재사용 경계: outgoing 구조 중 무엇을 inbound에 쓰는가

| outgoing 구성요소 | inbound 재사용 | 이유 |
|---|---|---|
| ④-1 `step_budget`, `Shell.prove`, 도함수 enclosure | **그대로** | 선분이 shell 안에 있고 \|P_h\| ≤ P_cap이라는 전제만 쓴다. 운동 방향과 무관 |
| `ForceEnvelope`, `_covered_shell`, `zero_impulse_radius`(R_J = 10240) | **그대로** | 위치만의 함수 |
| R ≥ R_J에서 실행기 충격량이 정확히 0 | **그대로.** inbound는 정확한 격자 직선 q_n = q0 + n·δ가 되고 R_J 안으로 들어오는 첫 n은 2차 부등식의 정확한 정수 해다 | 위치만의 함수 |
| `residence_steps`, `_check_overflow`, packet 형식, `NotCertified` 의미, `EXECUTION_SCOPE` | **형식 그대로**(엄격히 R < a에 도달하는 step 수는 floor(·) + 1) | 방향과 무관한 산술 |
| `certify_outgoing_outer`의 chain 조립 | **구조 그대로, 방향 반대**(R_J → 20) | |
| `_shell_induction`(w ≥ w_floor > 0, ΔR² ≥ g_min > 0) | **재사용 불가. 거울 귀납 필요**(4절) | 순방향 명제다. T는 순방향 inbound를 역방향 outgoing으로 보낸다 |
| `certify_tail`(연속 tail, 방향 오차) | **해당 없음** | incoming 점근선은 전체 산란각·global shadowing 단계의 일이다 |
| 반올림 판정·Proof Cache witness | **공유** | J가 위치만의 함수라서다(TR 없이도 참). TR이 더하는 것은 "역방향 run은 정확히 같은 위치를 지난다"뿐이다 |
| r_min guard | **바깥에서는 무관**(R ≥ 20 ≫ r_min). 일반적으로는 TR (ii)의 비대칭 | |

**시간역전이 실제로 주는 것.** (1) 역방향 run의 정확성과 새 판정 질문 없음. (2) 한 궤도의 inbound 구간이 지나는 위치 = 역방향 궤도의 outgoing 구간이 지나는 위치(나중에 global shadowing·도달 위치 집합에서 쓸 수 있는 관계). (3) inner의 입구 packet과 출구 packet의 형식이 서로의 T 상이라는 대칭.
**주지 않는 것.** inbound 순방향 infall 보장, 위치 집합·half-ulp 간격 문제의 축소(판정 입력은 위치이고 T는 위치를 바꾸지 않는다), D_valid의 T 불변성.

## 4. 거울 귀납 (구현자 유도 — 미구현·미감사, 설계자 판단용)

inbound shell [a, b), 안으로 이동. 입구 R_e ∈ [a, b), w0 = q·P ≤ W0 < 0, \|P\| ∈ [p0_lo, p0_hi]. g = α·P_cap + D, 선분은 [a − g, b] 안에 머문다(a − g ≥ 20이어야 ④-1을 쓴다). K = h·F/2 + U(덮개 [a − g, b]).

```
운동량   |P_n| ≤ p0_hi + 2nK ≤ P_cap                         (outgoing과 같음)
w 상한   w_(n+1) ≤ w_n + gain,  gain = 2bK + α P_cap² + D P_cap
         (반 kick마다 |q·J| ≤ bK, drift는 q·P_h에 α|P_h|² + d·P_h를 더한다 — inbound에서는 불리한 방향)
반 step  q_n·P_h ≤ W0 + n·gain + bK =: hw_ceil(n) < 0
ΔR²     2 q_n·δ + |δ|² ≤ 2α·hw_ceil(N) + 2bD + (α P_cap + D)² =: −g_in,   g_in > 0 이어야 함
step 수  count = floor((R_e² − a²)/g_in) + 1  이후 R < a
```

outgoing과 다른 점: w의 **상한**을 쓰고, drift 항 α\|P_h\|²와 \|δ\|²가 **불리한** 쪽으로 작용한다(w는 전환점 쪽으로 커진다). 그래서 귀납이 닫히려면 \|W0\|가 N·gain보다 충분히 커야 한다. D_valid의 b ≤ 2Re ≈ 14.2에서 R = 20의 w는 대략 −\|P\|·√(400 − b²) ≤ −14\|P\|라 여유가 있을 것으로 **추정**한다(계산하지 않음). 크기는 `_shell_induction` 한 함수와 비슷하다.

## 5. inbound outer handoff 계약 (명세만, 구현 전)

**입력.** C1-B1 실행 profile의 실제 저장 상태(두 Ar40, FX(96,48)/FX(96,80), h = 40, drift v2), R² ≥ 20², w = q·P < 0, J_cache ∈ {None, J(q)}, 동결 모델 fingerprint. D_valid 소속은 요구하지도 함의하지도 않는다(실행기 사상에 관한 증거이고 D_valid 연결은 별도).

**구간.**
- (Z) R ≥ R_J: 충격량 정확히 0. q_n = q0 + n·δ. q0·δ < 0을 요구하고, R_J² 아래로 처음 들어가는 n을 정확한 정수로 구한다. 격자 직선이 R_J 안에 들어오지 않으면(최소 R²가 R_J² 이상) NotCertified.
- (S) R_J > R ≥ 20 + g: 거울 귀납 shell을 R_J에서 20 + g까지 이어 붙인다(5/4 분할, outgoing과 같은 탐색 예산 두 배 규칙).

**출력(= inner의 입구 packet).** 모든 바깥 선분이 R ≥ 20 안에 있는 마지막 구간의 끝 상태 s_h: R_h ∈ [20, 20 + g), w_h ≤ w_ceil < 0, \|P_h\| ∈ [p_lo, p_hi], J_cache = J(q_h), 누적 step 상한, ④-1 원인별 에너지·L 예산 × count, 절대 위치·운동량 overflow 여유, `reference_decision_within_precision_cap = not_proved_for_future_steps`(④-2와 같은 범위).

**실패(`NotCertified`, reason `outer_bound_not_certified`).** profile·모델 불일치, R < 20(이미 inner), w ≥ 0(inbound 아님: outgoing이면 ④-2로), 운동량 cap 예산, w 상한이 음수를 유지하지 못함(바깥에서 전환점 가능), 엄격한 안쪽 ΔR²가 닫히지 않음, sub-grid stall, overflow, cache 불일치.

**연결.** inbound outer → (s_h) → inner → (R ≥ 20, w > 0 출구 packet) → ④-2 outgoing → R_J → tail. inbound와 outgoing은 **inner를 거쳐서만** 이어진다. TR에 따라 inner의 입구·출구 packet 형식은 서로의 T 상이다.

## 6. 하지 않은 것

거울 귀납·(Z) 구간 구현, inner scattering, global shadowing, 전체 산란각(incoming 점근선 포함), E_min 재생성, 실행기 변경, D_valid 변경. 시간역전으로 위치 집합·half-ulp 간격 문제가 풀렸다고 주장하지 않는다. **④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결** 그대로다.

## 7. 설계자 판단 요청

| # | 질문 | 구현자 의견 |
|---|---|---|
| **IN-1** | 판정: "바깥 inbound는 outgoing과 같은 계약으로 다룰 수 있다, 단 거울 귀납 하나가 새로 필요하다"를 받아들일지 | 받아들이기를 권한다. 시간역전만으로 닫힌다고 쓰면 틀린다 |
| **IN-2** | 다음 단계를 inbound V1(거울 귀납 + (Z) 구간 + chain, 결함 주입 포함)로 할지, inner로 바로 갈지 | inbound V1이 작고(함수 몇 개) inner의 입구 packet을 확정하므로 먼저 하기를 권한다. 수학 계약이라 강한 모델 |
| **IN-3** | handoff 위치: 바깥 인증은 선분 전체가 R ≥ 20인 step만 덮고, s_h는 R ∈ [20, 20 + g)에서 넘긴다 | 권장. 대안(R < 20 첫 저장 상태에서 넘김)은 경계를 넘는 step의 1-step 상한을 R < 20에서 요구해 ④-1 범위 밖이 된다 |
| **IN-4** | TR (ii)의 guard 비대칭 | 실행기는 바꾸지 않고 기록만 하기를 권한다. ~~바깥과 D_valid 에너지에서는 일어나지 않는다~~ → 설계자 문구 제한: outer inbound에서는 R ≥ 20이라는 기하학적 여유 때문에 무관하다. 전체 D_valid/inner에 대해 무관하다고 아직 일반화하지 않는다(반례는 E ≫ 10 De라는 것만 보였을 뿐 D_valid 궤도가 r_min 한 칸 위에 오지 않는다는 증명이 아니다) |

## 7.1 설계자 판정 (2026-09-30)

- **IN-1 승인.** 바깥 inbound는 outgoing의 1-step bound, force envelope, shell/packet 형식, 실패 의미를 재사용한다. outgoing shell induction **정리 자체**를 재사용하는 것은 아니며 inbound 방향의 별도 mirror induction이 필요하다. 시간역전만으로 inbound infall이 증명됐다고 쓰지 않는다.
- **IN-2 inbound V1을 inner보다 먼저.** 범위: (Z) R ≥ R_J zero-impulse 직선 + mirror shell induction + R ≈ 20 handoff chain. inner·global shadowing·전체 산란각·E_min은 하지 않는다.
- **IN-3 승인.** outer formal bound는 선분 전체가 R ≥ 20인 step만 책임진다. 마지막 outer 인증 상태를 R ∈ [20, 20 + g), w < 0 packet으로 inner에 넘긴다. R < 20으로 실제 넘어가는 step은 outer 증명에 넣지 않는다.
- **IN-4 실행기 변경 없이 반례·비대칭 기록.** outer inbound에서는 R ≥ 20이라는 기하학적 여유 때문에 무관하다. 전체 D_valid/inner에 대해 무관하다고 아직 일반화하지 않는다(반례는 E ≫ 10 De라는 것만 보였을 뿐 D_valid 궤도가 r_min 한 칸 위에 오지 않는다는 증명이 아니다). inner에서는 필요하면 별도로 다룬다.
- **V1 성공 조건:** shell별 momentum cap, w_ceil < 0, strict g_in > 0, 선분 전체 R ≥ 20, overflow 안전, R_J 직선 구간 exact. 하나라도 못 닫으면 NotCertified. **표본 궤적(3,600 step 시험 포함)을 증명의 대체물로 쓰지 않는다.** executor·D_valid·동결 계약 불변. mirror induction은 구현 후 독립 감사 전에는 승인된 정리로 쓰지 않는다.

## 8. 검증

신규 파일만(모듈 1, 시험 1, 문서). 기존 실행 코드·공용 모듈·동결 계약·fixture 변경 없음 → **LOCAL FULL 생략 / 관련 시험으로 대체**(AGENTS.md 기준). 결과는 `CURRENT_STATE.md`의 해당 항목.
