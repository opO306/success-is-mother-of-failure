# [보류 초안] C1-B1 수 표현 동결안 — 위치 FX(96,48) · 운동량 FX(64,48) (C1-B1 한정)

**상태: 보류 — 동결 아님.** 14판 추가 판정(2026-09-26): drift 세 방식(v1 `round(r+x)` / v2 `r+round(x)` / 정확·잔여 drift) 비교 측정 뒤
최종 drift와 위치 profile을 함께 판정한다. 이 문서는 그때 쓸 초안이며 강제 시험은 없다(`test_c1b1_freeze.py`는 보류로 제거).
**근거:** `A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md` 8~10절.


## 1. 이 동결의 정확한 의미 — "C1-B1 기준 profile"

- **적용 범위: C1-B1(두 40Ar 원자, Δt = 40 a.u., E_rel ≤ 10Dₑ)뿐.** A 전체의 영구 좌표 형식이 아니다.
  ±2⁴⁷ bohr ≈ ±7.4 km는 미래의 지구 규모 A에 당연히 부족하다. 더 큰 세계의 좌표 표현은 그때 따로 설계·판정한다.
- FX(96,48)은 **의미 계약**이다(13판 11항). 내부 저장(3×32비트, 64+32비트 등)은 실행기 선택이며 결과 비트는 같아야 한다.

## 2. 동결하는 것

| 항목 | 내용 |
|---|---|
| 위치 profile | `FX(96,48)` — raw 정수 v가 v·2⁻⁴⁸ bohr, 범위 [−2⁹⁵, 2⁹⁵−1] raw |
| 운동량 profile | `FX(64,48)` — raw 정수 v가 v·2⁻⁴⁸ a.u.(ħ/a₀), 범위 [−2⁶³, 2⁶³−1] raw |
| 충격량 J | 운동량 profile로 **한 번** 반올림 (`J_k = round(F(R)·Δr_k/R·Δt/2)`, R = √R² 반올림 안 함) |
| 킥 | `p ± J` — 같은 격자의 정확한 덧셈 |
| **drift** | **`δr = round_pos(p·Δt/m)`, `r' = r + δr`** — 변위를 한 번 반올림(짝수 쪽), 위치에는 정확한 정수 이동. 동점이 아닐 때는 v1(`round(r + p·Δt/m)`)과 비트 동일 |
| 범위 초과 | 위치·운동량이 profile 범위를 벗어나면 `executor_limit_exceeded` — wrap·saturate 금지, 상태 저장 안 함 |
| r_min guard | 반올림 **전** 정확한 drift 선분 + 반올림 **후** 저장 위치, 둘 다 r ≥ r_min (아니면 `physics_domain_exceeded`) |
| 적분기 범위 | Δt = 40 a.u., 저장된 실제 상태의 정확한 E_rel ≤ 10Dₑ(여유 없음, 포함), 아니면 **실행 전** `integrator_domain_exceeded` |

## 3. 동결하지 않는 것

- A 전체의 좌표·운동량 형식, 다른 원소·다원자·다른 Δt의 profile.
- 실행기 내부 저장·limb·스레드·CUDA 구조·시간.

## 4. 알려진 한계 (공개)

- binary64 절대 위치는 탈락 기록으로 남는다(`test_representation_preserving_translation_b64`, strict xfail). binary64 위치 profile에서는
  v2 drift가 `r + δr`를 한 번 더 반올림한다 — 탈락한 profile이라 계약으로 쓰지 않는다.
- C1-B1 J 평가기(√R² 입력)의 네이티브 실행기는 아직 없다 — B0에서 만든다. `bench_state` 커널은 v2 drift를 따르지만 무작위 입력이라
  **동점 경로는 네이티브에서 아직 시험되지 않았다.** B0는 동점 입력을 명시적으로 시험해야 한다.
