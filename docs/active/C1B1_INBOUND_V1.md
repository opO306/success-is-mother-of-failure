# C1-B1 inbound V1 — 바깥 inbound의 거울 shell 귀납과 R ≥ R_J 정확 직선

**문서 분류: 현재 활성 A / C1-B1.** 활성 Gate는 C1-B1, outer formal bound ④ 진행. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
**상태:** 구현·시험 완료(구현자). **독립 감사 전 — mirror induction은 승인된 정리로 쓰지 않는다.** 설계자 판정 대기. 날짜 2026-09-30. 기준 HEAD `5861a15`.
**근거:** [inbound V0](C1B1_INBOUND_V0.md)의 설계자 판정 IN-1〜IN-4(7.1절)와 V1 성공 조건.
**코드:** `a_reference/c1b1_inbound_outer.py`(새 파일), survey `a_reference/c1b1_inbound_outer_survey.py`(survey_only), 시험 `tests/test_c1b1_inbound_outer.py` 16개. 실행기·outgoing 코드·D_valid·동결 계약 변경 없음.

## 0. 한 줄 결과

**바깥 inbound는 이 방법으로 에너지가 충분할 때 닫힌다.** survey 격자 72개(E 1e-8〜10 De, b 0·7·14, 출발 R 25·200·20000) 중 **46개 인증:** E ≥ 0.1 De는 45/45 전부(R 20000 출발은 정확한 zero-impulse 직선 약 49만〜490만 step 포함), E = 0.01 De는 1/9, **E ≤ 1e-4 De는 0/18.** D_valid의 H 부분(E > 0.997 De)은 격자에서 전부 닫혔다. **L 부분의 저에너지는 이 귀납으로 닫히지 않는다.** 기존 outgoing chain도 E = 1e-4 De에서 닫히지 않는다(4절, 스크래치 비교).

## 1. 먼저 공개

1. **V0 4절의 거울 귀납 스케치는 그대로는 부족했다.** w 상한을 W + n·gain(gain에 α·P_cap²)으로만 쌓으면, P_cap > \|P\|가 **가짜 전환 반경 ≈ R0·√(2(P_cap/\|P\| − 1))**를 만든다. R_J(10240)에서 출발하면 P_cap/\|P\| − 1 < 2·10⁻⁶이어야 하는데 kick 누적이 이를 깬다. 실제로 R 10245 상태가 R ≈ 4000에서 실패했다. **고친 방법: 각운동량 항등식** (q·P)² = \|q\|²\|P\|² − \|q×P\|²와 ④-1의 1-step 각운동량 상한을 써서, shell마다 누적되지 않는 w 천장 −√(a²p_lo² − L_hi²)를 쓴다(2절). V0 스케치에 없던 성분이다.
2. **전역 force envelope는 R = 20 근처에서 쓸모없이 느슨하다**(R = 20에서 envelope 적분 약 1.9·10⁷ hartree, 실제 \|V\| 약 10⁻⁶). 첫 survey는 이것으로 P_cap을 정해 g가 터무니없이 커졌고, R0 = 25·200 상태가 **0-step handoff로 "인증"되는 무의미한 결과**가 나왔다. 그 행은 무효다. 인증 함수는 이제 P_cap < \|P\|를 거부한다. 둘째 survey는 여유가 너무 작은 cap 하나로 전부 실패했다. **두 실패 기록을 모두 보존했다**(`runs/c1b1_inbound_v1_survey_20260930/`). 최종 survey는 cap 사다리를 미리 고정하고 칸마다 결과를 남긴다.
3. **저에너지 실패의 원인(추정, 3.3절).** 느린 상태는 step 수가 크고, (i) 반 kick마다 \|q·J\| ≤ b·K로 **최악 방향**을 가정한다(실제 인력은 w를 더 음수로 만들어 오히려 돕는다). (ii) 운동량을 kick 누적 p ± 2nK로 묶는다(실제로는 에너지가 묶는다). 둘 다 느린 상태에서 크게 불어난다.

## 2. 정리 (구현자 유도, 독립 감사 전)

기호: q = r_j − r_i, P = (p_j − p_i)/2, w = q·P, L = q×P, α = h/μ, D = √3·2^−48, U = √3·2^−80/2, g = α·P_cap + D.

**(Z) R ≥ R_J.** ④-3(`zero_impulse_radius`)에 따라 R ≥ R_J의 모든 반 kick은 정확히 raw 0이다(위치만의 성질). 운동량과 원자별 저장 변위가 상수라 q_n = q_0 + n·δ가 정확하다. q_0·δ < 0을 요구하고, \|q_n\|² < R_J²인 첫 n을 **2차식의 정확한 정수 해**로 구한다(격자 직선이 R_J 안에 들어오지 않으면 NotCertified). 그 상태만 R < R_J의 kick 하나(\|J\| ≤ K_Z)를 가진다. 원자 위치는 선형으로 움직이므로 끝점만으로 overflow를 검사한다.

**(S) 거울 shell [a, b)**, a − g ≥ 20. 입구 R ≤ R_hi ≤ b, w ≤ W < 0, \|P\| ∈ [p_lo, p_hi], \|L\| ≤ L_hi. 탐색 예산 N에 대해 k < N이고 R_k ≥ a인 동안:

```
|P_k| ∈ [p_lo − 2kK, p_hi + 2kK],  p_hi + 2NK ≤ P_cap         (반 kick |J| ≤ K = hF/2 + U)
|L_k| ≤ L_hi + k·dL                                          (dL = ④-1 step_budget의 1-step 각운동량 합)
w_(k+1) ≤ w_k + gain,  gain = 2bK + α P_cap² + D P_cap
w_k ≤ w_c = min(W + N·gain, −√(a² p_lo(N)² − L_hi(N)²))     (근이 실수일 때만)
ΔR² = 2 q_k·δ + |δ|² ≤ 2α(w_c + bK) + c0 =: −g_in < 0,   c0 = 2bD + (αP_cap + D)²
```

- w 천장의 귀납: w_0 ≤ w_c. w_(k+1) ≤ w_c + gain < 0(검사)이라 q·P < 0이 유지되고, R ≥ a이므로 항등식이 다시 w_(k+1) ≤ w_c를 준다.
- R²는 매 step g_in 이상 줄고, **count = ⌊(R_hi² − a²)/g_in⌋ + 1 ≤ N** step 안에 R < a가 된다(N ← count 반복, 최대 64회).
- R_k ≤ R_hi ≤ b라 b를 쓴 상한이 유지되고, 노름이 볼록하므로 모든 저장 끝점 선분은 [a − g, b] 안에 있다.
- 출구: R ∈ [a − g, a), \|P\| ∈ [p_lo − 2·count·K, p_hi + 2·count·K], \|L\| ≤ L_hi + count·dL, w ≤ min(w_c + gain, a − g에서의 항등식 천장).

**조립.** 입구에서 A = 20 + g까지 비율 4/5 고정 분할(궤적에 맞추지 않음). 마지막 출구가 **handoff packet: R ∈ [20, 20 + g), w < 0**, \|P\|·\|L\| 구간(IN-3). R < 20으로 넘어가는 step은 증명에 넣지 않는다. 입구가 이미 [20, A)이면 0-step handoff다.

**성공 조건 대응.** shell별 momentum cap(p_hi + 2NK ≤ P_cap), w_ceil < 0(w_c + gain < 0), 엄격한 g_in > 0, 선분 전체 R ≥ 20(a − g ≥ 20), overflow(절대 원자 성분, 질량중심 정지 가정 없음), R_J 직선 exact. 하나라도 못 닫으면 `NotCertified(outer_bound_not_certified)`이며 물리 실패가 아니다. 미래 반올림 판정은 인증하지 않는다(`reference_decision_within_precision_cap = not_proved_for_future_steps`). 재사용: ④-1 `step_budget`·`_covered_shell`·`ForceEnvelope`·`zero_impulse_radius`·`_state`·`_jump`(outgoing 코드 변경 없음). outgoing shell **정리**는 쓰지 않는다(IN-1).

## 3. 시험과 survey

### 3.1 시험 16개(29초)
- **기록 재검사:** 인증서의 수치로 모든 닫힘 부등식을 시험 안의 별도 작은 checker가 다시 계산한다(guard ≥ 20, cap, w 천장, g_in, count의 최소성, shell 연결, handoff 모양).
- **실행기와의 일치 검사(증명 아님):** R ≈ 28.4 inbound 상태(E ≈ 4.4 De, b = 5, cap 13)를 실제로 돌리면 모든 저장 선분 R ≥ 20, 매 step ΔR² ≤ −g_in, q·P ≤ 해당 shell 천장, step 수 ≤ 인증 상한, handoff 상태가 packet 안(R·\|P\|·w·\|L\|)이다. 인증된 handoff 천장 w ≤ −232.23, 직선 운동의 실제 값 약 −232.5.
- **(Z) 정확성:** R 10245 상태에서 실행기가 380 step 동안 kick 없이 정확한 격자 직선을 따르고, 인증서의 정확한 출구 위치와 비트 단위로 같다. 이어지는 28개 shell chain도 닫힌다.
- 0-step handoff, 거부 8종(outbound, 이미 inner, cap = \|P\|, cap < \|P\|, b = 24 스침, R_J를 비껴가는 직선, cache 불일치 2종).
- **결함 주입(모듈 원문 변이):** gain에서 α·P_cap² 제거 → 실제 궤적이 천장을 넘어 잡힘. 출구 반지름에서 overshoot 제거 → 기록 재검사가 잡음. momentum cap 검사 제거 → 기록 재검사가 잡음.
- 정적: 모듈이 궤적 step을 돌리거나 D_valid를 읽지 않는다.

### 3.2 survey(survey_only, 증명 아님)
격자는 실행 전에 고정했다. cap 사다리 P_cap = √(\|P0\|² + 2μ\|V(20)\|)·(1 + ρ), ρ ∈ {1/1024, 1/128, 1/16, 1/4, 1, 4}. 결과 파일 `runs/c1b1_inbound_v1_survey_20260930/survey.json`.

| E/De | 인증 | 필요한 ρ | 비고 |
|---|---|---|---|
| 10, 5 | 9/9, 9/9 | 1/1024 | handoff w 천장이 −R\|P\| 근처(b = 0: E 10에서 −362.8 = −20·\|P\|) |
| 2 | 9/9 | 1/1024〜1/128 | |
| 1 | 9/9 | 1/128 | |
| 0.1 | 9/9 | 1/16 | R 20000: 정확 직선 4,897,770 step + shell 상한 약 577만 step |
| 0.01 | 1/9 | 1(b = 0, R 200만) | 나머지는 momentum·w 천장 |
| 1e-4, 1e-8 | 0/18 | — | w 천장이 음수를 유지하지 못함, momentum |

### 3.3 저에너지 실패 해석과 outgoing 비교
기존 `certify_outgoing_outer`를 R 25, b = 7의 outbound 거울 상태에 cap 사다리로 돌린 스크래치 비교: **E = 1e-4 De는 실패**(strict outward induction), 0.01·0.1·1 De는 인증(`runs/.../outgoing_low_energy_comparison.*`). 즉 저에너지 한계는 inbound만의 문제가 아니다. inbound가 0.01 De에서 더 나쁜 이유는 인력이 inbound를 **가속**하는데, count는 가장 느린 속도로 세고 w·운동량 상한은 kick 최악 방향을 가정하기 때문으로 추정한다(계산으로 분해하지 않음).

## 4. 하지 않은 것 · 한계

- inner, global shadowing, 전체 산란각(incoming 점근선 포함), E_min 재생성, 실행기·D_valid·outgoing 코드 변경.
- **독립 감사 없음.** 2절의 부등식, 특히 L 천장의 귀납(부호 유지)과 count의 정의는 감사 대상이다. 증명 보조기 검증 없음.
- 저에너지 L 부분(E ≤ 1e-4 De 격자 전부, 0.01 De 대부분)은 **이 방법으로 NotCertified**다. 이것은 물리 실패의 증거가 아니다.
- survey 격자 밖(다른 b·방향·3D 배치·출발 R)은 말하지 않는다. 격자의 인증도 해당 상태에 대한 인증 함수의 결과이지 survey가 증거가 아니다.
- step 상한은 실제 체류 step 수가 아니다(attainability not proved).
- **④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결** 그대로다.

## 5. 설계자 판단 요청

| # | 질문 | 구현자 의견 |
|---|---|---|
| **V1-1** | 1절 1의 **L 항등식 천장**(V0 스케치에 없던 성분)을 inbound 방법에 넣는 것을 승인할지 | 승인을 권한다. 없으면 R_J에서 오는 긴 구간이 원리적으로 닫히지 않는다. 독립 감사 항목으로 넣는다 |
| **V1-2** | 저에너지 L 부분을 어떻게 할지: (a) 인력 부호 정밀화(shell의 V′ enclosure가 양수이면 q·J_exact ≤ 0이라 반 kick 항 bK를 bU로 바꿈. 기존 도함수 enclosure만 씀) (b) 에너지 기반 운동량 상한(④-1 수정 에너지 예산으로 \|P\|² = 2μ(H − V)를 묶어 kick 누적 대신 사용) (c) 당분간 저에너지 L은 NotCertified로 두고 inner로 진행 | (c)로 inner를 진행하면서 (a)를 작은 후속으로 권한다. (b)는 outgoing에도 같은 문제가 있어 양방향 공용 개선으로 따로 판단하는 편이 낫다 |
| **V1-3** | 독립 감사(2절 + 코드)를 inner 전에 받을지 | inner의 입구 packet 모양이 이 결과에 의존하므로 inner 설계 전에 받기를 권한다 |

## 6. 검증

신규 파일만(모듈 2, 시험 1, 문서) + 문서 갱신. 기존 실행 코드·공용 모듈(outer_bootstrap·outer_bound·outer_chain·two_atom)·동결 계약·fixture 변경 없음 → **LOCAL FULL 생략 / 관련 시험으로 대체**. 결과는 `CURRENT_STATE.md`의 해당 항목.
