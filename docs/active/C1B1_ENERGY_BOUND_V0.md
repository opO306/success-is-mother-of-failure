# C1-B1 Energy Bound v0 — 에너지 기반 운동량 범위(inbound·outgoing 공용)와 에너지 장벽 셸 lemma

**문서 분류: 현재 활성 A / C1-B1.** 활성 Gate는 C1-B1, outer formal bound ④ 진행. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
**상태:** 구현·시험(구현자). **독립 감사 전 — 방법 채택 ≠ 정리 승인.** 날짜 2026-09-30. 기준 HEAD `99a2eec`.
**근거:** 설계자 판정(2026-09-30, [Field Map 조사](C1B1_FIELD_MAP_SURVEY_V0.md) 뒤): (1) 에너지 기반 운동량 상한 진행 승인(inbound·outgoing 공용), (2) 에너지 장벽 셸 같이 진행(독립 lemma, D_valid 도달 불가 주장에는 에너지 오차와 step overshoot 포함), (3) inner 도함수 재정식화 보류. 순서 ①〜⑦ 중 **이번은 ①〜③**이다.
**코드:** `a_reference/c1b1_energy_bound.py`(공용), `a_reference/c1b1_outgoing_energy.py`(outgoing 새 판), `a_reference/c1b1_inbound_outer.py`(energy 모드 추가, 기본 동작 불변). 시험 `tests/test_c1b1_energy_bound.py` 21개 + `tests/test_c1b1_inbound_outer.py` 3개 추가. 실행기·D_valid·dt·동결 계약·기존 outgoing 코드(`c1b1_outer_bootstrap`/`c1b1_outer_chain`/`c1b1_outer_bound`) 변경 없음.

## 0. 한 줄 결과

**에너지로 운동량을 묶으면 kick 누적 없이 느린 상태도 닫힌다.** inbound는 grid 저에너지 상태가 닫히고(3절 survey), outgoing은 v1이 못 닫던 E = 1e-4 De가 닫힌다. survey 72개 격자: **inbound 46 → 72/72, outgoing 63 → 69/72.** **남은 한계:** outgoing의 출발 R 25 극저에너지 3개(1e-8 De b 7·14, 1e-4 De b 14)는 R_J까지의 긴 비행(약 10¹⁰ step)에서 1-step 에너지 예산 합이 전체 에너지(1e-8 De에서 약 4.5·10⁻¹² hartree)에 닿아 닫히지 않는다(추정). 에너지 장벽 셸 [5.32, 5.35]는 E~ ≤ 10 De에서 셀 3개로 인증된다. **④ "D_valid가 R ≈ 5.3 아래에 못 간다"는 아직 증명하지 않았다**(inner 궤적의 에너지 예산이 없다).

## 1. 수학 (구현자 유도, 독립 감사 전)

기호: q, P = (p_j − p_i)/2, μ = m/2, R = \|q\|, H = \|P\|²/(2μ) + V(R), **E~ = H − h²V′(R)²/(8μ)**(④-1이 1-step마다 묶는 수정 에너지), α = h/μ, D = √3·2^−48, U = √3·2^−80/2.

**(E1) 에너지 범위.** 저장 상태의 E~는 정확한 \|P\|²와 V·V′의 구간으로 감싼다(`energy_of_state`, 구간 R이면 `energy_of_packet`). 1-step 전제(선분이 증명된 셸 안, \|P_h\| ≤ P_cap)가 성립하는 성공 step n번 뒤 E~는 처음 범위를 1-step 예산(`c1b1_outer_bound.step_budget`의 energy total)의 합만큼 넓힌 범위 안에 있다.

**(E2) 운동량 범위.** R이 V ∈ [V_lo, V_hi], \|V′\| ≤ F인 셀 안에 있고 E~ ∈ [E_lo, E_hi]이면

```
|P|² = 2μ(E~ − V) + h²V′²/4  ∈  [2μ(E_lo − V_hi),  2μ(E_hi − V_lo) + h²F²/4]
```

위 끝이 음수면 그 셀에는 그 에너지의 상태가 없다(**에너지 금지**). **kick을 누적하지 않는다.** 범위는 에너지 범위와 "지금 어느 셀에 있는가"만으로 정해진다.

**셸 귀납에서의 사용(inbound 거울 셸, outgoing 셸 공통).** 탐색 예산 n에 대해 E_n = E_entry를 n·dE만큼 넓히고, 셸 guard 영역(셸 + overshoot)의 V·F로 (E2)를 적용한다. kick 누적 범위 [p_lo − 2nK, p_hi + 2nK]와 **교집합**을 쓴다(둘 다 유효). 귀납: k번째 step에서 \|P_k\| ≤ p_hi_E이면 \|P_h\| ≤ p_hi_E + K ≤ P_cap(검사) → 1-step 예산이 적용 → E~_(k+1) ∈ E_entry ± (k+1)dE. 출구 운동량 범위도 같은 교집합이다(출구 상태는 guard 영역 안).
- **inbound:** 운동량 하한이 각운동량 천장 −√(a²p_lo² − L_hi²)(inbound V1)에 들어간다. kick 누적만으로는 느린 상태에서 p_lo → 0이 되어 천장이 사라졌다.
- **outgoing(새 판):** q·P **바닥** w_f = max(w_0 − n·loss, √(a²p_lo² − L_hi²)). w_(k+1) ≥ w_k − loss ≥ w_f − loss > 0(검사)이라 q·P > 0이 유지되고, R ≥ a라서 항등식이 다시 w ≥ w_f를 준다. loss의 α·P_floor²에도 에너지 하한 p_lo − K를 쓴다. 나머지(g_min, count, 출구, tail packet, overflow)는 v1과 같다.

**(E3) 에너지 장벽 셸 lemma(`certify_energy_barrier`).** [c, d]를 호출자가 정한 고정 개수의 같은 셀로 나누어 모든 셀이 E~ ≤ E_hi에서 에너지 금지이고, d − c > α·P_h_cap + D이면: \|P_h\| ≤ P_h_cap인 R_n ≥ d의 저장 상태에서 성공 step 뒤 저장 상태의 E~ ≤ E_hi라면 **R_(n+1) ≥ d**다. 이유: 저장 변위 ≤ α\|P_h\| + D < d − c이므로 R_(n+1) > c이고, [c, d)에는 그 에너지의 상태가 없다.
- 설계자 지적 두 조건(장벽 안 V > 에너지 상한, 한 step 최대 이동 < 장벽 두께)을 모두 검사한다.
- **전제 두 개는 lemma가 증명하지 않는다**(기록에 `premises_not_proved_here`로 남긴다): 궤적 전체에서 E~ ≤ E_hi, R ≥ d에서 매 step \|P_h\| ≤ P_h_cap. 이것이 ④의 일이다.
- 측정: [5.32, 5.35]를 셀 3개로 나누면 V ≥ 12.6897 De이고, \|P_h\| ≤ 20에서 한 step은 0.022 bohr < 0.03이다.

**R < 20의 V.** `radial_derivatives`는 `c1b1_outer_bound.derivatives`에서 R ≥ 20 guard만 뺀 것이다(시험이 구문 트리 동일성과 R ≥ 20 값 동일성을 확인). 공용 코드를 바꾸지 않은 이유: outer bound 원본은 outgoing 해석 예시 fixture의 source hash에 묶여 있다. R ≲ 5에서는 구간이 매우 넓다(Field Map 조사 2.4). 넓어도 건전하지만 쓸모가 없을 뿐이다.

## 2. 이번에 고친 V1 결함 (공개)

inbound V1의 기록 필드 `relative_L_change_before_last_kick_exact`가 `steps * tuple`로 계산되어 **튜플을 steps번 반복**했다(값을 곱하지 않음). R 10245 시험에서는 조용히 1,140개짜리 튜플이 저장됐고, 느린 상태(E = 1e-8 De, R 20000)에서는 메모리가 터졌다. 증명 논리에는 쓰이지 않는 기록 필드였다. 고쳤고, 시험이 정확한 값(L_0 + n·δ×P_0 = q_exit×P_0)을 확인한다.

## 3. 시험과 survey

**시험(`test_c1b1_energy_bound.py` 21개, 약 200초).**
- `radial_derivatives` = 원본(구문 트리, R ≥ 20 값), R < 20 고정밀 값 포함.
- 에너지·운동량 범위가 실제 실행기 상태 600 step을 모두 포함(일치 검사, 증명 아님). 에너지 금지 셀.
- 장벽: [5.32, 5.35] 인증. 거부 3종(넓은 셀 하나, 한 step보다 얇음, E = 13 De). 실제 정면 반사(E ≈ 9.9 De, R 6.5에서 안으로)의 모든 저장 R > 5.35.
- outgoing energy: 기록 재검사, 첫 셸에서 실행기가 모든 주장 안에 있음, **v1이 못 닫는 E = 1e-4 De 인증**(같은 cap에서 v1은 NotCertified), 문서화된 한계(1e-8 De, R 25) NotCertified.
- 결함 주입 3종: 운동량 하한을 V의 잘못된 끝으로 계산 → 실제 상태가 하한 아래. 장벽 두께 검사 제거 → 한 step이 뛰어넘을 수 있는 장벽을 받아들임(원본은 거부). outgoing 항등식 바닥을 먼 끝 b에서 계산 → 실제 q·P가 그 아래. (처음 넣은 "loss 부호 반전" 변이는 10 De에서 loss가 0이라 아무것도 바꾸지 못해 **무의미한 변이**였고, 바꿨다.)

**시험(`test_c1b1_inbound_outer.py` 추가 3개).** energy 모드가 V1이 못 닫는 E = 1e-2 De(R 25, b = 7)를 인증, 기록 재검사, 실행기가 매 step 셸의 에너지 운동량 범위·천장·g_in 안, 결함 주입(에너지 운동량 상한을 하한으로 사용 → 실제 궤적이 천장 위).

**survey(survey_only, 같은 72개 격자, 같은 cap 사다리).** 결과는 `runs/c1b1_energy_bound_survey_20260930/`. 요약은 `CURRENT_STATE.md`와 아래 표.

| E/De | inbound V1(kick) | **inbound energy** | outgoing v1 | **outgoing energy** |
|---|---|---|---|---|
| 1e-8 | 0/9 | **9/9** | 3/9 | 7/9 |
| 1e-4 | 0/9 | **9/9** | 6/9 | 8/9 |
| 1e-2 | 1/9 | **9/9** | 9/9 | 9/9 |
| 0.1 〜 10 | 45/45 | 45/45 | 45/45 | 45/45 |
| **합계** | 46/72 | **72/72** | 63/72 | **69/72** |

- inbound energy는 R 20000 출발 E = 1e-8 De까지 전부 닫힌다(shell step 상한 약 180억).
- outgoing energy는 v1이 인증한 상태를 하나도 잃지 않고 6개를 더한다. 남은 3개는 모두 **출발 R 25**의 극저에너지(1e-8 De b 7·14, 1e-4 De b 14)이며 사유는 전부 "q·P 바닥이 양수를 유지하지 못함"이다. R_J까지의 긴 비행에서 1-step 예산 합이 작은 전체 에너지에 닿는 것으로 추정한다(분해 계산 안 함).
- outgoing v1 격자는 이번에 처음 같은 조건으로 돌렸다(`outgoing_v1.json`). inbound V1 수치는 [inbound V1](C1B1_INBOUND_V1.md) 3.2절.

## 4. 하지 않은 것 · 한계

- **④ D_valid 도달 불가 증명은 하지 않았다.** inner 궤적(R < 20)의 에너지 예산이 없기 때문이다. 필요한 것: inner 셸의 1-step 예산(R ≥ 5.35 영역의 도함수 구간), inbound handoff에서 inner를 거쳐 outgoing 입구까지의 E~ 누적, 그 전체에서 \|P_h\| cap. 그 뒤 장벽 lemma의 전제가 채워진다.
- outgoing E = 1e-8 De 같은 극저에너지 장거리는 1-step 예산 합이 에너지를 넘어 닫히지 않는다.
- 독립 감사 없음. (E1)〜(E3), 셸에서의 교집합 귀납, outgoing 항등식 바닥이 감사 대상이다.
- inner 도함수 재정식화는 설계자 판정대로 보류.
- **④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결** 그대로다.

## 5. 검증 기준

신규 모듈 2개 + inbound 모듈 energy 모드(기본 경로 불변, V1 시험 16개 그대로 통과; 변이 시험 하나의 대상 문자열만 바뀐 코드에 맞춤) + V1 기록 필드 버그 수정 + survey 모듈 mode 인자. **기존 실행 코드·공용 모듈(outer_bootstrap/outer_bound/outer_chain/two_atom)·동결 계약·fixture 변경 없음 → LOCAL FULL 생략 / 관련 시험으로 대체.** (inbound 모듈과 survey 모듈은 이번 세션의 새 파일이며 공용이 아니다.)
