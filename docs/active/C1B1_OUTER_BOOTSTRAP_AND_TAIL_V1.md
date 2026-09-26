# C1-B1 ④-2 / ④-3 — 실제 격자 outgoing shell과 해석적 tail

**문서 분류: 현재 활성 A / C1-B1.** 활성 Gate는 C1-B1, outer formal bound ④ 진행이다. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


2026-09-27. 계약 `c1b1-outer-bootstrap-tail-v1`.
④-1 [C1B1_OUTER_FORMAL_BOUND_V1.md](C1B1_OUTER_FORMAL_BOUND_V1.md)의 조건부 1-step 식에 **전제 유지와 유한 step 수**를 붙인다.
실측 D_valid와 독립인 증거 계층이며 D_valid v2·canonical 생성기·기준 fixture를 바꾸지 않는다.

## 1. 정확한 적용 범위와 아직 하지 않은 것

- 동결 Lang 2024 명목 계수·Ar40 질량, 두 Ar40, 위치 FX(96,48), 운동량 FX(96,80), h=40, drift v2, half-even.
- 입력은 **실제로 저장된 상태**다. q=r_j-r_i, P=(p_j-p_i)/2, μ=m_Ar40/2, w=q·P.
- 유한 outgoing 영역 R≥20에서 아래 충분조건을 전부 닫는 상태만 인증한다. E>0만으로 탈출을 인정하지 않는다.
- 귀납식은 **정확한 반올림 상태 전이**에 관한 것이다. 기존 실행기의 `MAX_PRECISION_BITS=16384` 안에서 미래의 모든 impulse가
  결정된다는 liveness는 증명하지 않았다. 초기 impulse는 실제로 계산하지만, 미래 `ReferenceUndecided` 중단 가능성은 남는다.
  모든 shell/tail/전체 record의 `reference_decision_within_precision_cap=not_proved_for_future_steps`로 고정한다.
  영역/overflow 보장과 정밀도 한도 내 실행 가능성을 혼동하지 않는다.
- `certify_shell`은 지정한 [a,b)의 첫 출구까지, `certify_outgoing_outer`는 입구→R_J까지 shell 보장을 조립한다.
- `p_cap`, `n_cap`은 호출자의 증명 탐색 예산이다. 운동량/step 귀납식을 검사하므로 가정만 적어 둔 값이 아니다.
  부족한 예산·stall·inward·캐시 불일치·overflow 위험은 `NotCertified(reason=outer_bound_not_certified)`.
  **인증 실패는 물리 실패나 궤적 불가능의 증명이 아니다.**
- 상대 수정 에너지 E_tilde=H−h²|F|²/(8μ), H=|P|²/(2μ)+V(R); 상대 L=q×P를 사용한다.
  lab-frame 질량중심 각운동량은 포함하지 않는다.
- inbound·inner scattering·속박 궤도·E_min 재생성·원래 초기 상태에서 시작한 연속 궤적과의 global shadowing은 미완료.
  **④ 전체/C1-B1 전체 동결 또는 전체 산란각 오차 인증을 주장하지 않는다. ⑤도 시작하지 않았다.**
- 무한시간 균일 L 상한은 명시적으로 제외한다. formal 인증을 `run.validation`이나 D_valid 범위에 자동 연결하지 않는다.
- Lean/Coq 같은 증명 보조기 검증은 없다. 해석적 귀납 유도 + 정확 유리수/outward 구간 구현 + 실제 실행/결함 주입 시험이다.
  동결 모델의 실험적 매개변수·질량 불확도는 이 수치 계약의 항이 아니다.

## 2. 실제 양자화된 drift의 귀납식

α=h/μ, u_x=2^-48, u_p=2^-80.
상대 drift 오차의 norm 상한 D=√3 u_x, 한 half-kick 반올림 오차 U=√3 u_p/2를 outward 유리수로 잡는다.
성공한 정수 운동량 덧셈 자체의 추가 반올림은 0이다.

```
P_h = P_n + J_n
q_(n+1) = q_n + α P_h + d,       |d| ≤ D
P_(n+1) = P_h + J_(n+1)
```

shell [a,b)의 출구 overshoot를 포함하는 guard c=b+α P_cap+D를 쓴다.
[a,c] 전체를 고정 비율 5/4의 구간으로 덮고 ④-1의 도함수 enclosure를 합친다.
각 half-kick norm은 K=h F_guard/2+U 이하다.
입구에서 |P|∈[p0_lo,p0_hi], w≥w0, 최대 탐색 step N에 대해 다음을 검사한다.

```
p0_hi + 2 N K ≤ P_cap
P_floor = max(0, p0_lo − 2 N K)
loss = max(0, 2 c K + D P_cap − α P_floor²)
w_floor = w0 − N loss
half_w_floor = w_floor − c K
g_min = 2 α half_w_floor − 2 c D > 0
```

근거: 두 endpoint kick은 각각 q·P를 최대 cK 낮춘다. drift는
q_(n+1)·P_h=q_n·P_h+α|P_h|²+d·P_h로부터 최소 α P_floor²−D P_cap를 더한다.
따라서 w_(n+1)≥w_n−loss이며 n≤N 동안 위 하한과 운동량 cap이 귀납적으로 유지된다.

실제 저장 displacement δ=αP_h+d에 대해서는

```
q_n·δ ≥ α half_w_floor − c D > 0
ΔR² = 2 q_n·δ + |δ|² ≥ g_min > 0.
```

즉 이동량 norm이 양수인 것과 구별되는 **엄격한 바깥 drift**다.
q_n·P_h도 양수이므로 unrounded chord와 실제 저장 endpoint chord 모두 입구보다 안쪽으로 내려가지 않는다.
R_(n+1)≤b+αP_cap+D=c이므로 첫 출구까지 ④-1의 whole-chord 전제가 성립한다.
최초 impulse 캐시가 실제 반올림 결과인지, 실제 최초 격자 drift의 ΔR²>0인지도 검사한다.
향후 step마다 실행기가 반올림을 결정하면 그 실제 전이에 귀납식이 적용된다. 계산 자원 한도로 중간에 중단된 프로그램의 출구 도달은 보장하지 않는다.

체류 step 충분 상한은 정확한 정수 올림으로

```
count = ceil((b² − R_entry_lower²)/g_min) ≤ N.
```

단일 실제 입구는 정확한 R_entry²를 사용하고, 연결 packet은 보수적으로 a²를 사용한다.
R² 증가를 합하면 count step 이전에 반드시 R≥b가 된다. 경계에 이미 도달한 packet은 0-step handoff가 가능하다.
**sub-grid stall과 원주 방향 이동은 이 strict 조건을 만족하지 못한다.**

## 3. 유한 shell 연결과 overflow

중간 궤적을 돌리거나 미래 측정값을 읽지 않고 출구 packet을 전달한다.

```
R_exit ∈ [b,c]
|P_exit| ∈ [max(0,p0_lo−2 count K), p0_hi+2 count K]
w_exit ≥ w0−count loss
```

다음 shell의 a=b, 다음 c는 이전 c보다 크다. overshoot로 이미 다음 b를 넘었다면 그 shell은 실제로 0 step이며,
보수적인 양수 count를 packet 오차 예산에 더해도 유효하다. 5/4 분할은 구간 의존성 팽창을 줄이기 위한 고정 규칙이며 실측으로 맞추지 않는다.
step 예산을 최대 16회 두 배로 늘리는 것은 증명 탐색일 뿐이다. 모든 폐쇄 조건을 재검사하고, 닫히지 않으면 거부한다.

절대 위치·절대 운동량의 FX overflow도 별도로 막는다. 질량중심이 정지한다고 가정하지 않는다.
전체 half-kick cap 합 S_K, 전체 count N_total로 각 원자의 각 lab 성분에 대해

```
|p_k| ≤ |p_k,initial| + 2 S_K = p_lab_cap
|Δr_k| ≤ h p_lab_cap/m + u_x/2
|r_k| ≤ |r_k,initial| + N_total (h p_lab_cap/m + u_x/2)
```

를 FX 양의 최대값 아래에서 검사한다(음의 끝에는 더 보수적인 대칭 cap 사용).
상대량만 검사하여 큰 공통 위치/운동량의 overflow를 놓치지 않는다.

각 shell의 ④-1 source별 1-step 상한에 count를 곱하고 triangle inequality로 더한다.
위치·momentum update(0)·impulse·시간 이산화·기타 산술(0)을 모두 provenance에 남긴다.
이미 저장된 입구에서 시작하므로 초기 연속 상태의 투영항을 매 step 더하지 않는다.

## 4. 모든 먼 R에 적용되는 힘 envelope

`ForceEnvelope`는 **전체 R≥20**에서 |V'(R)|≤F_bar(R)=Σ c_k/R^k, c_k>0, k>1을 유도한다.
표본 최대값이나 유한 EXP 정밀도의 오차 바닥을 무한 tail에 사용하지 않는다.

- short-range와 Tang–Toennies damping correction의 미분을 c exp(−λR) R^t 항들로 분리한다.
  exp(λR)의 양수 급수에서 exp(−λR)≤m!/(λR)^m.
  m=max(0,t+10)이므로 각 항의 exponent k=m−t≥10. 계수는 정확한 |c|m!/λ^m.
- 일반 inverse-power의 미분을 2k|C_2k|/R^(2k+1)로 덮는다.
  REL 첫 항의 원래 cancellation은 보존하고 존재하지 않는 bare R^-4를 더하지 않는다.
- retarded BO 첫 항은 −C6 R^-6 A(R)/B(R). 동결 A,B의 모든 계수 양수이고 B(R)≥B6 R^6.
  A_j R^j 항에서 미분 상한은
  (6+j)|C6| A_j/B6 · R^(j−13)와
  |C6| A_j ell B_ell/B6² · R^(j+ell−19)의 합으로 충분하다.
  여기서 j≤5, ell≤6이므로 모든 inverse-power exponent가 1보다 크다.

따라서 정확한 무한 적분

```
I_F(R) = ∫_R^∞ F_bar(s) ds = Σ c_k/(k−1) R^(1−k)
```

이 유한하다. 동결 모델의 V(∞)=0도 각 원래 항의 감쇠로 성립한다.
interval shell force cap과 이 전역 cap 중 작은 것을 선택해도 둘 다 독립적으로 유효한 상한이다.

## 5. R_J: 실행기 impulse 0과 연속 물리 tail을 분리

R_J는 고정 수열 20·2^j에서 **h F_bar(R_J)<u_p**를 처음 만족하는 값이다.
이는 최소 실수 반경을 찾았다는 주장이 아니며, D_valid/산란 실측을 읽지 않는다.
모든 R≥R_J에서 |h f_k(R)/2|<u_p/2이므로 각 half-kick이 정확히 raw 0으로 round된다. 동점도 아니다.

같은 실제 상태에서 그 이후 실행기 atom momentum은 정확히 상수이고 각 atom의 quantized drift도 상수다.
relative δ가 상수이면 q_n=q_entry+nδ이며,

```
ΔR_n² = 2 q_entry·δ + (2n+1)|δ|².
```

입구의 q·δ≥0, |δ|²>0(연결 packet은 더 강한 q·δ>0)을 인증하면 R≥R_J를 유지한다.
따라서 `executor_remaining_impulse=0`이며 반올림 impulse 잔여를 무한히 합하지 않는다.

하지만 실제 연속 Lang force는 0이 아니다. tail 입구의 **동일 q,P에서 새로 시작한 연속 중심력 궤적**만 비교한다.
초기 radial speed 하한 v0=w_lower/(μ R_entry_upper)>0에 대해

```
margin = 3 v0²/4 − 2 I_F(R_entry_lower)/μ > 0
v_floor = v0/2.
```

연속 radial 식 R_ddot=|P_t|²/(μ²R)+f_rad/μ≥−F_bar(R)/μ에 2 dR을 적분하면
v(R)²≥v0²−2∫ F_bar/μ>v_floor²다.
v가 처음으로 v_floor에 도달한다고 가정하면 모순이므로 radial escape 조건은 전체 tail에서 유지된다.
v≥v_floor>0이므로 R은 무한대로 가고, 남은 연속 impulse는

```
I_tail ≤ I_F(R_entry_lower)/v_floor.
```

이 양이 entry momentum norm의 하한 P_lower보다 작은지도 검사한다.
|P_infinity−P_entry|≤I_tail, 최종 운동량의 평행 성분≥P_lower−I_tail>0이므로

```
angle(P_infinity,P_entry) ≤ atan(I_tail/(P_lower−I_tail))
                         ≤ I_tail/(P_lower−I_tail) radians.
```

실행기 momentum 방향은 상수다. 따라서 이것은 **같은 tail 입구에서 시작한 연속 기준과 실행기 점근 momentum 방향**의 상한이다.
원래 산란 초기 상태에서 두 궤적을 출발시켜 같은 handoff에 도착한다고 증명하지 않았으므로 전체 산란각 상한으로 바꾸면 안 된다.

실행기 H의 tail 변화는 I_F 이하, E_tilde 변화는 I_F+h² F_bar²/(8μ) 이하다.
연속 중심력 기준의 H 변화는 정확히 0이며, 이 사실을 실행기 에너지 보존과 혼동하지 않는다.
finite E_tilde source 합에 `tail_potential`과 `tail_modified_correction`을 따로 더한다.
physical H로 변환하려면 별도 기록된 전체 endpoint correction h² F_max²/(8μ)를 붙인다.

## 6. 무한 L과 유한 FX 폭의 명시적인 한계

force가 0으로 round되어도 위치 grid drift δ가 P에 정확히 평행하지 않으면
L_(n+1)−L_n=δ×P≠0이다. 실제 zero-impulse 반례에서 매 step (−1,−1,+1)·2^-47가 남는다.
따라서 L은 **유한 입구→R_J**까지만 상한화한다. 무한 균일 L bound를 주장하지 않는다.

FX(96,48)는 유한 폭이므로 프로그램이 무한대까지 실행된다는 주장도 하지 않는다.
tail 인증은 overflow 전 안전 step 수를 별도 기록한다. 점근 방향은 이후 동일 상수 momentum/drift의
**수학적 연장**과, 동일 tail 입구의 연속 기준에 대한 것이다. 실제 overflow로 중단된 실행과 구별한다.

## 7. 해석 예시, 느슨함, 재생성

`a_reference/fixtures/c1b1_outer_bootstrap_example_v1.json`은
q=(20,0,0), P=(1,0,0), 정지 질량중심, P_cap=2의 **해석적 인증 예시(실측 fixture 아님)**다.
실제 궤적을 한 step도 돌리지 않고 28개 shell을 연결한다. 모든 분수·입구/출구 packet·source별 항·7개 소스 SHA256을 보존한다.

| 항목 | 결과 (소수는 표시용 근삿값; 계약값은 정확한 분수) |
|---|---|
| R_J | 10240 bohr |
| 입구→R_J step 충분 상한 | 2,387,040,365 |
| E_tilde 위치항 | ≈2.13180×10^-17 hartree |
| E_tilde impulse항 | ≈1.87789×10^-19 hartree |
| E_tilde 시간 이산화항 | ≈6.32216×10^-13 hartree |
| E_tilde tail potential항 | ≈6.62036×10^-24 hartree |
| E_tilde 전체 outgoing 상한 | ≈6.32237×10^-13 hartree |
| 유한 상대 L 상한 | ≈2.93772×10^-5 bohr·momentum |
| 동일 입구 연속 tail impulse 상한 | ≈2.46924×10^-16 momentum |
| 동일 입구 tail 방향 상한 | ≈2.86646×10^-16 rad |

이 step 상한은 실제 체류 step 수가 아니다. 전역 w 하한을 보수적으로 고정하고, P_cap를 입구 norm보다 크게 잡고,
shell 전체 M3와 triangle inequality를 사용하는 비용이 포함된다.
이산화항이 지배적이지만 실제 attainable worst case라는 증거는 없으며 `attainability=not_proved`다.
기존 20~21 bohr 예시의 8.458×10^-18 hartree도 **증명된 충분 상한**이지 실제 최악값이 아니다.
이 느슨함을 D_valid 실측으로 보정하지 않았다. E_min/domain 또는 실측 대비 정보량은 아직 판정하지 않는다.

재생성: `python -m a_reference.c1b1_outer_chain a_reference/fixtures/c1b1_outer_bootstrap_example_v1.json`.
source hash는 CRLF→LF 정규화 후 계산한다. Windows/Linux의 source bytes 차이가 물리 provenance 차이가 되지 않게 한다.

## 8. 시험과 검증 범위

`tests/test_c1b1_outer_bootstrap.py` 31개: strict ΔR², 정확 ceil, outward 실제 KDK step,
radial drag가 있는 작은 momentum의 귀납·출구, E>0 sub-grid stall, inward, 부족한 탐색 cap,
profile/캐시/절대 위치 overflow, 실행 시 retardation/질량 계약 불일치 거부, model force 대조, 무한 적분, model-derived cutoff,
zero discrete impulse/nonzero continuous tail, 지속 L drift, global precision 15/40/60/100의 동일성,
D_valid 읽기 금지, 궤적 step 호출 금지, 미래 반올림 liveness 미증명 scope, 예시 완전 재생성·source hash 대조를 검사한다.

결함 주입: force envelope=0, w의 누적 radial drag 생략, residence ceil→floor가 각각 원래 force/실제 step/실제 출구 시험을 실패시킨다.
잘못된 캐시 `(0,)`를 zero impulse로 인정하던 초기 구현도 red 시험으로 잡아 `(0,0,0)` 정확 비교로 수정했다.
유한 실제 step 시험은 해석 귀납을 대체하지 않으며, 모든 실수 상태를 표본 시험했다는 뜻도 아니다.

이번 검증은 설계자 요청에 따라 Vast Linux 한 대에서 수행한다. `REMOTE PYTHON FULL`은 Linux에서 실행 가능한 Python 경로 전체다.
MSVC·Windows/CUDA 계약 skip이 있으므로 LOCAL FULL과 동등하게 보고하지 않는다.
관련 59개 통과. REMOTE PYTHON FULL은 **2258 passed + 108 skipped + 1 strict xfailed / 실패 0**, 71.23초.
LOCAL FULL은 게임 중 로컬 GPU를 쓰지 않도록 이번에는 재실행하지 않았다. 로그·JUnit: `runs/c1b1_outer_bootstrap_full_v1.*`.
