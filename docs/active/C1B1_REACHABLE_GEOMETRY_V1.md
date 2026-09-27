# C1-B1 ④-4b — 귀납적 reachable projection 축소

**문서 분류: 현재 활성 A / C1-B1.** 2026-09-27. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
구현: `a_reference/c1b1_reachable_geometry.py`, 계약 `c1b1-reachable-geometry-v1`.
기존 [④-2 귀납](C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md)에 좌표·방향 제약을 붙이고
[④-4 cover](C1B1_ROUNDING_DECISION_V1.md)에 전달한다. 실행기·D_valid·물리 법칙은 바꾸지 않는다.

## 1. evaluator 변경에 대한 frozen replay

`8b498f0` 직전 evaluator (`78a1a25`)와 현재 evaluator를 frozen 181개 probe의 같은 초기 상태에 적용했다.
경계 탐색·독립 quadrature·산란각 측정을 재실행하지 않았다.

- 초기 상태를 양쪽 evaluator의 V0로 각각 재생성: 181/181 동일하며 frozen `p_j_raw`와 일치.
- D_valid 결과: 181/181 동일. `numerical_validated` 69, `unsupported` 112.
- 원래 경계 측정의 exact position + FX(256,192) momentum, dt=40, drift v2로 매 KDK 전이를 비교.
  좌표·운동량·impulse cache·step 수·실행 status가 181/181 동일. 총 3,470,163 전이, 모두 정상 종료.
- Fixture 변경 없음. SHA256: `eb2582228bb25b762cc4edf676ec2da59949bd1b28f84234adf65a9947648cf9`.
- exit code 0, 3815.645초. 상세: `runs/c1b1_frozen_replay_20260927/{stdout.log,stderr.log,report.json,probes.jsonl,exit.json}`.

**한계:** fixture에는 최종 궤적 비트가 없다. 그 비트는 수정 전 evaluator와 비교했다.
기존 `audit_fail` 6개의 독립 감사 status/reason은 보존했으며 재검증하지 않았다. 나머지 175개는 frozen probe status가 `ok`다.
새 replay의 `ok`를 기존 `audit_fail` 해소로 읽지 않는다. 원래 probe별 cap은 저장되지 않아 별도 operational cap 150400을 사용했다.
최장은 58205 step이며 cap 소진은 없었다. D_valid 재측정이나 확대가 아니다.

## 2. 정확히 보존되는 상대 좌표 0

같은 Ar40 질량, 위치 FX(96,48), 운동량 FX(96,80), drift v2에서 초기 `q_k=0`과 `P_k=0`이 **함께** 성립하는 축만 보존한다.

1. 두 raw 좌표와 raw 운동량이 각각 같다.
2. 실제 `impulse`는 `q_k*h/2=0`인 성분을 exact raw 0으로 반환한다. 해당 kick은 두 운동량을 바꾸지 않는다.
3. 같은 운동량·질량에서 `round_pos(h*p_k/m)`가 같으므로 drift v2 뒤 raw 좌표도 같다.
4. 다음 full/half state에서도 같은 조건이 유지되므로 모든 성공한 step에 귀납 적용한다.

공통 운동량은 0일 필요가 없다. 평면 자체가 이동해도 **상대 좌표** 0은 유지된다.
한 축을 제외하면 상대 위치 cover는 2D, 두 축을 제외하면 1D다. `q_k=0`만 보고 축을 고정하지 않는다.
**임의의 기울어진 평면은 가정하지 않는다.** 성분별 반올림은 일반 선형 관계를 보존하지 않는다.
실제 drift의 raw displacement `(0.4,0.4,0.8)` 부근이 `(0,0,1)`로 반올림되어 `z=x+y`를 벗어나는 정수 시험을 둔다.
연속 중심력의 평면 보존을 FX 실행기에 그대로 옮기지 않는다.

## 3. 좌표 tube와 방향 제약

shell별 체류 상한 `N_s`, half-kick norm 상한 `K_s`, `α=h/μ`에 대해 `T_s=2 Σ_(j≤s) N_j K_j`다.
각 full step은 두 kick이고 중간 half state는 kick 하나 적으므로 해당 상태 모두에서 `|P-P0|≤T_s`다.
미래 impulse 판정이 성공한다는 기존 조건부 전이 범위에서의 귀납이다.

상대 drift 성분은 `δq_k=α P_half,k+d_k`, `|d_k|≤u_x`다. 비고정 축에서는

```
v_k^- = α(P0_k-T_s)-u_x
v_k^+ = α(P0_k+T_s)+u_x
δq_k ∈ [v_k^-, v_k^+]
```

고정 축은 오차까지 정확히 0이다. 입구 좌표 interval `[l_k,h_k]`, 실제 체류 `0≤n≤N_s`에 대해
shell 내부와 출구를 `[l_k+min(0,N_s v_k^-), h_k+max(0,N_s v_k^+)]`로 덮는다.
이를 다음 shell에 전달한다. 이미 다음 경계를 넘은 0-step handoff도 포함한다.
raw box는 하단 ceil·상단 floor로 변환해 해당 radial guard와 교차한다.

기존 angular source별 유한 오차합 `A_s`, 초기 상대 각운동량 norm의 outward 상한 `L0`에서
`L_s=L0+A_s`로 `|q×P|≤L_s`다. 정확한 각운동량 보존을 가정하지 않는다.
guard radius `c_s`와 `w_floor`에서 triangle/Cauchy 부등식으로

```
|q×P0| ≤ L_s+c_s T_s
q·P0 ≥ w_floor-c_s T_s
```

를 얻는다. 첫 식은 cone의 횡방향을, 둘째는 가능한 경우 outward branch를 제한한다.
제약이 느슨해 반대 방향을 제거하지 못하면 제거하지 않는다.
cell의 `q·P0` **상한**이 요구 하한보다 작거나, `q×P0` 각 성분 interval로 얻은 norm² **하한**이 cap²보다 클 때만 제외한다.
등호와 겹치는 cell은 남긴다. 충분한 제외 검사이며 정확한 feasible-set 계산은 아니다.
남은 cell은 기존 evaluator endpoint를 포함하는 signed rounding-cell 인증을 통과해야 한다.

## 4. 검증과 완료 범위

신규 **9 passed, 22.81초**. 실제 KDK 입구→출구의 좌표·운동량·각운동량·cone 포함,
3D/2D/1D, 이동하는 질량중심, 궤적/D_valid 조회 금지, cone 등호 보존을 검사한다.
결함 주입으로 운동량을 무시한 축 고정과 초기 각운동량 누락이 실제 의무 시험에 잡혔다.

예시 재생성과 관련 5개 시험 파일 검증 완료: **106 passed, 51.59초**.
재생성한 R=20 예시의 상대 좌표는 3D→1D, exact zero 축은 y/z다.
기존 64-cell 예산을 유지하여 64개를 검사했으며 미해결 record 76개(미검사 shell 포함)가 남아 `NotCertified`다.

VAST의 동일 소스 snapshot에서 **REMOTE PYTHON FULL: 2292 passed + 121 skipped + 1 strict xfailed, 실패/오류 0, 98.89초, exit 0**.
JUnit 2414개 case와 exit/log를 대조했고 동결 fixture hash도 동일하다.
skip 121개는 MSVC/Windows native·CUDA compiler 계약 98개, CUDA 미가용 10개, 외부 Lang 원문 자료 13개다.
원격에는 공개 Fortran 원문을 byte/hash 동일하게 제공했고 평가기나 감사 코드를 바꾸지 않았다.
첫 원격 실행은 pydantic 및 Fortran 원문 부재로 실패했으며 준비를 보완한 두 번째 실행 결과가 위 값이다. 실패 로그도 보존한다.
설계자의 원격 이전 지시로 이번 LOCAL FULL은 중단했다. 원격 결과를 LOCAL FULL로 부르거나 skip을 통과로 세지 않는다.
로그 회수 뒤 VAST 정지를 실제 상태로 확인했다.
로그: `runs/c1b1_reachable_geometry_20260927/remote_results_attempt2/{remote_python_full.log,remote_python_full.xml,stages.json,exit.json,provenance.json}`.
**이 변경만으로 20→R_J 비영 completeness 완료를 주장하지 않는다.** 열린 cell은 `NotCertified`로 보존한다.
④ 최종 동결·⑤·E_min 재생성·전체 산란각은 보류한다. 측정 궤적으로 enclosure를 맞추지 않는다.
수학 유도 + 정확 유리수 구현 + 실제 전이/결함 주입 검증이며 Lean/Coq 또는 완전 독립 증명은 아니다.
