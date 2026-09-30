# Energy Bound v0 독립 감사 인계 — 수학 연결 감사(⑤)

**감사 대상:** 커밋 `e2613cd`의 [Energy Bound v0](C1B1_ENERGY_BOUND_V0.md). 코드: `a_reference/c1b1_energy_bound.py`, `a_reference/c1b1_outgoing_energy.py`, `a_reference/c1b1_inbound_outer.py`(energy 모드).
**감사자:** 설계자 지정(GPT-5.6 Sol High 또는 Claude Opus 5.5 High). **작성자(Claude)는 감사자가 아니다.** 아래 "작성자 주장"은 확인할 대상이지 감사 결과가 아니다.
**설계자 판정(2026-09-30):** ④를 만들기 전에 이 감사를 먼저 한다. 시험 통과보다 **수학 연결**을 본다. 통과해야 ④(inner R ≥ 5.35 에너지 예산)로 간다.
**감사 결과(2026-09-30):** E1·E2·P/P_h·inbound 셸 귀납·outgoing·장벽·R < 20 도함수 **PASS**, inbound `certify_inbound_outer()` 조립 **FAIL**(zero leg 뒤 셸 0개일 때 handoff 반지름이 이동 전 상태를 씀). 수정 커밋 뒤 **그 경계 경로만 재감사 대상**(재감사 범위: `c1b1_inbound_outer._handoff_radius`와 그 호출, regression 시험 `test_audit_counterexample_*`, `test_the_four_composition_paths`).
**현재 상태:** 방법 채택, 정리 미승인. ④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결.

## 0. 감사할 명제 (한 줄씩)

- **(E1)** 1-step 전제(선분이 증명된 셸 안, \|P_h\| ≤ P_cap)가 성립하는 성공 step마다 \|ΔE~\| ≤ dE, E~ = H − h²V′(R)²/(8μ). 따라서 n step 뒤 E~ ∈ E_0 ± n·dE.
- **(E2)** R이 V ∈ [V_lo, V_hi], \|V′\| ≤ F인 셀 안이면 \|P\|² ∈ [2μ(E_lo − V_hi), 2μ(E_hi − V_lo) + h²F²/4]. 위 끝 < 0이면 그 셀에 상태 없음.
- **(E3)** 장벽 [c, d]의 모든 셀이 E~ ≤ E_hi에서 금지이고 d − c > α·P_h_cap + D이면, R_n ≥ d, \|P_h\| ≤ P_h_cap, E~_(n+1) ≤ E_hi인 성공 step 뒤 R_(n+1) ≥ d. **두 전제(E~ ≤ E_hi, \|P_h\| ≤ cap)는 호출자 몫이다.**
- **셸 귀납:** inbound 거울 셸과 outgoing 셸에서 kick 누적 범위와 (E2) 범위의 교집합으로 운동량을 묶고, 각운동량 항등식으로 q·P 천장(inbound)/바닥(outgoing)을 준다.

## 1. 설계자 지정 체크리스트와 코드 위치

각 항목에 **성립 / 성립하지 않음(반례·빠진 단계) / 불명확(무엇이 필요한가)** 중 하나와 근거를 적어 주기 바란다.

### 1. E1 에너지 누적
- `c1b1_outer_bound.step_budget`(230〜): energy 합 = position + impulse + discretization(+0 두 항). 유도는 [④-1 문서](C1B1_OUTER_FORMAL_BOUND_V1.md) "직접 대입한 에너지·각운동량 증명"이며 **E~ = H − h²\|F\|²/(8μ), F는 저장 끝점의 힘**이다.
- 사용: `c1b1_inbound_outer.py:108`(dE), `:113`(`energy.widen(n * dE)`), `:223`(셸 사이 누적). `c1b1_outgoing_energy.py:45`, `:122`.
- 확인할 것: (i) Energy Bound의 E~와 ④-1의 E~가 같은 양인지(V′² = \|F\|²). (ii) `step_budget`에 넘기는 `domain`이 `_CoveredShell`(셀 합집합)인데, ④-1의 전제 "선분 전체가 셸 안"과 M3(셀별 third_directional의 최대)이 그대로 성립하는지. (iii) ±n·dE가 k ≤ n인 모든 step을 덮는지, 전제 확인이 순환 없이 귀납적인지.
- **작성자 주장:** (i) 같다. (ii) M3 상한은 각 점이 어떤 셀에 속하므로 셀 최대로 덮인다. force는 셀 최대와 전역 envelope 중 작은 값인데 둘 다 유효 상한이다. (iii) k번째 step의 \|P_h\| ≤ P_cap은 E~_k ∈ E_0 ± k·dE(귀납 가정)와 R_k ∈ 영역에서 나오고, 그러면 1-step 예산이 적용되어 E~_(k+1)로 넘어간다.
- **유의:** ④-1 자체의 독립 감사 기록은 이 인계에 없다. E1은 ④-1에 전적으로 기댄다.

### 2. E2 에너지 → 운동량
- `c1b1_energy_bound.momentum_range`(107〜115), `energy_of_state`(89〜97), `energy_of_packet`(99〜105), `_sqrt_down`(`c1b1_outer_bootstrap`).
- 확인할 것: V의 위·아래 끝 방향. **운동량 하한이 너무 높게 잡히는 경우**(하한에 V_hi를 쓰는가, V′² 항을 하한에서 버리는 것이 안전한가). 상한에 h²F²/4를 더하는 것이 \|V′\| ≤ F에서 충분한가. `energy_of_state`의 E~ 하한은 V′²의 최대, 상한은 V′²의 최소(구간이 0을 포함하면 0)를 쓰는가.
- **작성자 주장:** \|P\|² = 2μ(E~ − V) + h²V′²/4. 하한은 E~ ≥ E_lo, V ≤ V_hi, V′² ≥ 0. 상한은 E~ ≤ E_hi, V ≥ V_lo, V′² ≤ F². `_sqrt_down`은 √x 이하를 준다.

### 3. 저장 운동량 P와 half-step P_h의 구분
- 에너지 식은 저장 상태의 \|P_k\|, ④-1 전제는 \|P_h\| = \|P_k + J_k\|, \|J_k\| ≤ K = hF/2 + U.
- `inbound_outer.py:111`〜`116`: `half_cap = min(p_hi + 2nK, pe_hi + K)`, `pl = max(p_lo − 2nK, pe_lo)`(저장 하한, 항등식에 사용).
- `outgoing_energy.py:50`〜`52`: `p_state = max(…, pe_lo)`(저장 하한, 항등식), `p_floor = max(…, pe_lo − K)`(half-step 하한, drift 항 α\|P_h\|²에 사용).
- 확인할 것: 각 ±K가 맞는 쪽에 붙었는지. kick 누적 경로 `p_hi + 2nK`가 k < n의 half-step을 덮는지(p_hi + 2kK + K ≤ p_hi + 2nK).

### 4. inbound/outgoing 귀납
- **교집합:** 두 범위가 모두 유효하면 교집합도 유효하다(`:116`, `:138`, outgoing `:50`〜`51`, 출구 p 범위).
- **inbound q·P < 0 유지:** 천장 w_c = min(W + n·gain, −√(a²p_lo² − L_hi²)), 검사 w_c + gain < 0(`:124`). 귀납: w_(k+1) ≤ w_k + gain ≤ w_c + gain < 0, R ≥ a이면 항등식으로 다시 ≤ w_c. [inbound V1 문서](C1B1_INBOUND_V1.md) 2절.
- **outgoing q·P > 0 유지:** 바닥 w_f = max(w_0 − n·loss, √(a²p_state² − L_hi²)), 검사 w_f − loss > 0(`:57`). 귀납: w_(k+1) ≥ w_k − loss ≥ w_f − loss > 0, R ≥ a(outgoing에서 R은 증가)이면 항등식으로 다시 ≥ w_f. 시작: w_0 ≥ w_lo이고 w_0 > 0이라 항등식도 성립하는가.
- **출구 → 다음 셸 전제:** inbound 출구 R ∈ [a − g, a), 다음 셸 b = a, 영역 [a′ − g, a]가 출구를 포함하는가. outgoing 출구 R ∈ [b, c], 다음 셸 a = b. 다음 셸의 energy_entry = 이전.widen(count·dE), q·P 경계, \|L\| 경계, p 경계가 출구 상태를 실제로 덮는가.
- **작성자 주장:** 모두 성립. 다만 inbound 천장의 L 항과 outgoing 바닥의 L 항은 각운동량 1-step 상한 dL(④-1 angular total)에 기댄다.

### 5. Energy Barrier
- `c1b1_energy_bound.certify_energy_barrier`(117〜): 금지 판정 `2μ(E_hi − V_lo) + h²·V′_cell² /4 < 0`(`:131`, \|V′\| 셀 최대 사용), 두께 `d − c > α·P_h_cap + D`(`:124`〜`125`).
- 확인할 것: (i) V만이 아니라 수정 에너지의 V′² 항까지 금지 판정에 들어갔는가(E~ ≤ E_hi인 상태의 \|P\|² 상한이 음수인가). (ii) 저장 상대 변위 δ = α·P_h + d, \|d\| ≤ D(두 원자 각 성분 반올림 ≤ u_x/2 → 상대 성분 ≤ u_x, 노름 ≤ √3·u_x)가 실제 저장 이동을 덮는가. (iii) **\|P_h\| ≤ cap과 E~ ≤ E_hi가 코드·문서·기록 어디에서도 증명된 것처럼 쓰이지 않는가**(기록 필드 `premises_not_proved_here`, 문서 1절 (E3), `CURRENT_STATE.md`의 "④ 아직 아님").
- 측정값(참고): [5.32, 5.35], 셀 3개, V ≥ 12.6897 De, \|P_h\| ≤ 20에서 한 step 0.022 < 0.03.

### 6. R < 20 도함수 복사
- `c1b1_energy_bound.radial_derivatives`(39〜) vs `c1b1_outer_bound.derivatives`(162〜). 시험은 **구문 트리 동일성**(guard와 docstring 제외, `B.` 접두 제거)과 R ≥ 20 값 동일성만 본다. **이것은 코드 복사 확인이지 수학 증명이 아니다**(설계자 지적).
- 확인할 것: 원래 유도가 R > 0에서도 성립하는가. 구체적으로 (i) `Jet.reciprocal`/`r**(−2k)`는 0을 포함하지 않는 구간만 요구하는가(R > 0). (ii) `Iv.exp`(94〜)는 인자 ≤ 0만 허용하고, 짧은 거리 항 −α·r의 α가 전부 양수인가(아니면 예외로 멈추는가). x ≤ −4096 단축과 `enclosure(x, BITS, guard)`가 모든 x ≤ 0에서 건전한가. (iii) retardation 분모 1 + ΣRET_B·r^j > 0이 R > 0에서 성립하는가(RET_B 전부 양수?). (iv) outer 유도 문서에 R ≥ 20만의 가정이 숨어 있는가(예: 감쇠 항 근사, 부호).
- **작성자 주장:** 연산 중 R ≥ 20에 기대는 것은 없고 outward 반올림이라 R > 0에서 건전하다. 다만 R ≲ 5에서 구간 폭이 매우 커진다(건전하지만 무용, [Field Map 조사](C1B1_FIELD_MAP_SURVEY_V0.md) 2.4).

## 2. 판단하지 않아도 되는 것

④(inner 에너지 예산, D_valid 도달 불가), A-EV, 실행 시간, survey 격자 결과의 의미(survey_only), 저에너지 outgoing 3개 실패의 원인 분석.

## 3. 결과 형식

항목 1〜6 각각에 판정과 근거. 성립하지 않으면 반례 또는 빠진 단계, 코드 수정 제안은 따로. 감사 결과는 설계자가 판정한다.

## 4. 현재 증거(참고, 증명 아님)

시험 `tests/test_c1b1_energy_bound.py` 21개, `tests/test_c1b1_inbound_outer.py` energy 3개(기록 재검사, 실행기 일치 검사, 결함 주입 4종). survey 72개 격자: inbound 46 → 72/72, outgoing 63 → 69/72(`runs/c1b1_energy_bound_survey_20260930/`).
