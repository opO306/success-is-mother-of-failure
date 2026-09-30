# C1-B1 Actual-Trajectory Post-Verification feasibility 조사 v0

**상태:** feasibility 조사(scratch prototype + 문서). 저장소 코드 변경 0. runtime 구현 아님. 날짜 2026-10-01.
**Git(시작 시):** HEAD = origin/master = `5c5d6f84367f304b998e4d7f276d848daa5a8e60`, 작업 트리 깨끗함.
**증거:** `runs/c1b1_postverify_survey_20261001/` — `execute.py`(임시 실행·witness), `verifier.py`(독립 verifier), `verify.py`(W1/W2 검증), `stream.py`(streaming), `faults.py`(결함 주입), `perturb.py`(교란 전파), 결과 `vr_*.json`, `stream*.json`, `faults.json`, `perturb_*.json`, 로그 `*.out`.
**유지:** Energy Bound v0 = APPROVED, ④-Liveness = NotCertified, ④-Safety = Conditional, A-EV = 미해결, S4d = BOOTSTRAP-PARTIAL. 어느 것도 바꾸지 않는다.

## 0. 판정: **POSTVERIFY-HYBRID**

- **실제 궤적 하나는 싸고 안전하게 사후 검증된다.** S4d가 닫지 못한 넘는 쪽 4개를 포함한 7개 사례 전부 VALID. 모든 step의 J 반올림을 executor와 코드를 공유하지 않는 verifier가 128 bit에서 확인했고, R ≥ 5.35(모든 drift 선분)·R = 20 출구는 정확한 유리수 비교로 확인했다. **새 lemma 0개.** 결함 주입 12종 전부 잡음.
- **그러나 "실행보다 싼 증명서 확인"은 아니다.** step마다 초월함수 구간 평가 1회가 필요하고, 이것이 executor 비용의 약 93%다. J = round(x)를 확인하는 일과 계산하는 일은 같은 구간 평가가 필요하다(한쪽을 싸게 하는 기법은 다른 쪽도 똑같이 싸게 한다). 측정: 직렬 4.9〜5.8배(구현 상수), 6 작업자 병렬 wall-clock 0.98〜1.19배.
- **중간 step을 건너뛰는 사건 경계 검증(C)은 정확한 상태 확정에 쓸 수 없다.** 위치 1 raw 교란이 출구에서 운동량 10⁹〜10¹³ ulp로 커진다.
- **사후 검증이 대신할 수 없는 것:** 실행 전 Liveness 보장(끝나지 않으면 REFUSED뿐), D_valid 전체에 대한 명제, R_J 이후 무한 tail(해석적 formal tail이 계속 필요). 그래서 PROMISING이 아니라 HYBRID다.

## 1. 사례와 executor 실측 (문항 3, 4)

reference executor(`a_reference/c1b1_two_atom.py`, 수정 없음)를 `validated_only=False`로 이전 조사들과 같은 방식으로 실행했다(4 프로세스 동시). 시작은 `canonical_initial_state`, R = 20 inbound. 종료는 R² ≥ 400이고 q·P > 0인 첫 저장 상태.

| 사례 | 구분 | step | executor(s) | ms/step | 최소 R(drift 선분) | δ(수치, hartree) | S4d 누적 예산 |
|---|---|---|---|---|---|---|---|
| 0.5 De ρ −0.01 | S4d 미해결 | 13,093 | 14.7 | 1.12 | 6.855 | 6.49·10⁻⁶ | 9.8·10⁻⁶ |
| 0.5 De ρ −0.005 | S4d 미해결 | 14,367 | 15.9 | 1.10 | 6.870 | 3.26·10⁻⁶ | 1.05·10⁻⁵ |
| 0.15 De ρ −0.005 | S4d 미해결 | 26,451 | 31.4 | 1.19 | 6.539 | 9.77·10⁻⁷ | 2.9·10⁻⁶ |
| 1 De b 10 | S4d 미해결 | 7,221 | 7.9 | 1.10 | **7.073**(wall 미진입) | [7, 20]에 V_eff 극대 없음 | 1.7·10⁻⁵ |
| 0.5 De b 6 | 비교(닫힘) | 6,162 | 7.0 | 1.14 | 6.333 | 1.94·10⁻⁴ | — |
| 0.5 De ρ +0.005 | 비교(튕김) | 10,302 | 13.4 | 1.30 | 10.228 | −3.29·10⁻⁶ | — |
| 10 De b 0 | 비교(정면) | 1,491 | 1.6 | 1.04 | 5.505 | 장벽 없음(L = 0) | — |

step 수는 직접 궤도 조사 v0의 실행기 값과 같다. δ와 R_b는 verifier 평가기로 잰 **수치 진단값(인증 아님)**이며 판정에 쓰지 않는다.

사건 경계(검증된 상태에서 표시, step 번호): 예) 0.5 De ρ −0.005 — R20 inbound 1, barrier inbound 4,997(R_b 9.757), wall 진입 7,063, turning 7,184(R 6.870), wall 탈출 7,305, barrier 재통과 9,370, R20 outbound 14,367. 0.15 De ρ −0.005 — 1 / 8,738(R_b 11.746) / 13,065 / 13,226 / 13,386 / 17,713 / 26,451. 전 사례 사건 목록과 사건별 E~ 구간은 `vr_*_W1_serial.json`.

## 2. 사후 검증 방법과 독립성 (문항 5, 6)

**한 step의 검증(`verifier.transition` + `check_J`):**

```
state_k (정수) + J_k(주장) + J_(k+1)(주장)
 → p' = p ∓ J_k                       정확, 범위 검사
 → d = round_48(p'·dt/m) (ties-even)   정확
 → r_new = r + d                      정확, 범위 검사
 → drift 선분 최소 R² ≥ r_min²           정확 유리수
 → J_(k+1) 확인: G(R_new)·dr_c·h/2 의 구간이 (j − ½, j + ½) ulp 안에 **엄격히** 들어가면 VALID,
                 [j − ½, j + ½] 밖이면 INVALID, 경계에 걸리면 정밀도 2배(상한 16384 bit, 넘으면 REFUSED)
 → p'' = p' ∓ J_(k+1)                 정확
 → (W1) witness의 state_(k+1)과 정수 단위로 같아야 함
```

**executor ≠ verifier:**
- verifier는 `a_reference`·`a_numeric`·`engine`·`audit`를 **import하지 않는다**(검증 프로세스마다 `sys.modules` 검사, 전 실행 0건). A-EV 작업선의 `audit/independent_physics`도 쓰지 않았다.
- 동결 C1-A 상수는 소수 문자열로 **옮겨 적고**, 동결 계약의 sha256 fingerprint를 verifier 자체 코드로 다시 계산해 `ada6153b…`와 일치를 import 시점에 강제한다.
- V(R)는 계약 문서의 공식에서 새로 작성했고 **mpmath 구간 산술**(executor의 정수 고정소수 구간과 다른 라이브러리)로 평가한다.
- dV/dR은 **구간 위 전진 자동미분**(이중수)으로 구한다. executor의 손 유도 도함수와 다른 경로다.
- 반올림(ties-to-even), drift, kick, r_min guard는 원시 정수로 다시 구현했다.
- **공유하는 것:** 사양(공식·상수·반올림 규칙·dt·질량) 자체. 두 구현이 사양을 똑같이 잘못 읽으면 둘 다 틀린 채 일치한다(N-version의 공통 모드). mpmath 구간 함수의 엄밀성은 신뢰 가정이며 증명하지 않았다.

## 3. 비용 (문항 7, 8, 9)

| 사례 | W1 직렬 검증(s) / 비율 | W1 병렬 6(s) / 비율 | W2 병렬 6(s) / 비율 | streaming 비율 | W2 재구성(정확 부분만) |
|---|---|---|---|---|---|
| 0.5 De ρ −0.01 | 79.3 / 5.40 | 15.8 / 1.08 | 17.4 / 1.19 | 5.47 | 1.12 s (실행의 7.6%) |
| 0.5 De ρ −0.005 | 91.7 / 5.78 | 18.6 / 1.17 | 18.5 / 1.17 | 4.89 | 1.21 s (7.6%) |
| 0.15 De ρ −0.005 | 154.3 / 4.92 | 30.7 / 0.98 | 34.1 / 1.09 | 4.85 | 2.17 s (6.9%) |
| 1 De b 10 | 41.6 / 5.24 | 8.0 / 1.01 | 8.7 / 1.09 | 4.91 | 0.60 s (7.6%) |
| 비교 3개 | 4.88〜5.53 | — | — | — | — |

- **연산량:** step당 G 평가 정확히 1회(첫 상태 +1). 전 사례 전 step이 **128 bit에서 결정**(정밀도 상승 0회). 평가 1회 = mpmath 구간 exp 9개(이중수) + 이중수 곱 약 390개. profile에서 검증 시간의 약 96%가 이 평가다. 정확 정수/유리수 부분(kick·drift·guard·상태 비교)은 step당 수십 연산, 실행 시간의 약 7%.
- **비율의 의미:** 직렬 약 5배는 Python 이중수·mpmath 객체 부담(구현 상수)이다. 본질적 비율은 약 1이다. J를 확인하려면 J를 결정하는 것과 같은 구간이 필요하기 때문이다(NP식 "싼 확인"의 비대칭이 없다). 유일한 구조적 이점은 **병렬성**: witness가 있으면 step 검증이 서로 독립이라 병렬화되고, executor는 순차다. 병렬 6 작업자에서 wall-clock이 실행과 같은 수준(0.98〜1.19)이 됐다.
- **저장:**

| 방식 | 0.5 De ρ −0.005 | 0.15 De ρ −0.005 | 재검증 가능 |
|---|---|---|---|
| A. 전체 궤적 W1(상태 12정수 + J 3정수 / step) | 1.57 MB (gzip 1.30 MB) | 2.89 MB (2.33 MB) | 예, 병렬 |
| B. 초기 상태 + J만 W2(상태는 정확 재구성, 실행의 7%) | 315 KB (269 KB), 약 22 B/step | 578 KB (482 KB) | 예, 재구성 후 병렬 |
| C. streaming 후 certificate만 | 4.1〜4.5 KB (gzip 1.9〜2.1 KB) | 4.2 KB | **아니오** — 제3자는 다시 실행해 J 사슬 해시와 최종 상태를 대조할 수밖에 없다 |

## 4. full replay / segment / event 비교 (문항 10)

| 방식 | 결과 |
|---|---|
| **A. full step replay** | 가능, 강한 증거. 비용 ≈ 실행 1회(구현 상수 ×1〜6), 병렬 가능. 이번 조사의 실제 방법 |
| **B. segment** | 정확한 end state를 확정하려면 구간 안의 모든 J를 검증해야 한다. 결국 A에 checkpoint를 둔 것이고 이득은 저장(W2)과 병렬 분할뿐이다. end state를 **집합**으로 인증하는 segment certificate는 S4d식 worst-case bound이며 넘는 쪽에서 막힌 바로 그 방법이다 |
| **C. event-boundary** | 정확한 상태 확정에는 **불가능**. 교란 실험(`perturb_position.json`): 위치 x를 1 raw(2⁻⁴⁸ bohr) 바꾸고 executor로 출구까지 → 출구 상대 운동량 차이 최대 3.0·10⁹〜4.6·10¹³ ulp, 상대 위치 차이 최대 39,354 raw. 사건만 보고 중간을 건너뛰면 확정할 상태 자체가 정해지지 않는다 |

부수 관측(`perturb_momentum_run1.json`): 상대 운동량 1 ulp 교란은 출구까지 **정확히 그대로**(2 raw) 남고 위치는 0 차이다. 운동량 격자 2⁻⁸⁰의 변위 효과(약 2⁻⁹¹ bohr)가 위치 격자 2⁻⁴⁸보다 훨씬 작아 drift 반올림이 흡수하기 때문이다. 그래도 정확한 상태는 달라지므로 J 1 ulp 오류도 확정 전에 잡아야 한다(결함 주입에서 잡힘).

## 5. barrier 재통과와 E~ (문항 9, 11, 12)

**"올라갔으니 올라갈 수 있었다"가 아닌 형태:** barrier 재통과의 증거는 R_k < R_b ≤ R_(k+1)인 두 **검증된** 저장 상태와 그 사이 전이(J_(k+1) 반올림 포함)의 검증이다. 실제로는 R_b조차 필요 없다 — 판정에 쓰이는 것은 모든 전이의 검증 + 마지막 상태의 R² ≥ 400·q·P > 0(정확 비교)뿐이다. R_b는 관찰용 표시다.

**E~ = |P|²/(2μ) + V − h²F²/(8μ):** verifier가 **자기 V·V′ 구간**으로 모든 검증 상태에서 엄밀한 구간을 만든다(추가 비용 0: J 확인용 평가를 그대로 씀). 구간 폭 ≤ 6.2·10⁻³⁹ hartree라 사실상 정확값이다. executor가 출력한 E~(256-bit 중점, 미검증)는 쓰지 않고 대조만 했다(15자리 일치).

| 사례 | barrier in → out ΔE~(엄밀, hartree) | δ(수치) | δ / ΔE~ | 통과 중 E~ 최대 폭 | 출입 순변화 |
|---|---|---|---|---|---|
| 0.5 De ρ −0.01 | 3.11·10⁻¹⁴ | 6.49·10⁻⁶ | 2·10⁸ | 4.1·10⁻¹⁰ | −3.7·10⁻¹⁷ |
| 0.5 De ρ −0.005 | 1.74·10⁻¹⁴ | 3.26·10⁻⁶ | 2·10⁸ | 3.9·10⁻¹⁰ | −1.4·10⁻¹⁶ |
| 0.15 De ρ −0.005 | 4.0·10⁻¹⁶ | 9.77·10⁻⁷ | 2·10⁹ | 3.0·10⁻⁹ | 3.3·10⁻¹⁸ |
| 1 De b 10 | (barrier 없음) | — | — | 3.4·10⁻¹⁰ | −1.9·10⁻¹⁶ |
| 10 De b 0 | — | — | — | 5.2·10⁻⁷ | −3.1·10⁻¹⁴ |

- 넘는 쪽 사례에서 wall 진입 → turning → wall 탈출 사이 E~는 약 ±2.5·10⁻¹⁰ 오르내렸다가 거의 정확히 되돌아온다. S4d 인증 예산(10⁻⁶〜10⁻⁵)은 이 **양방향 상쇄를 모른 채 절댓값을 누적**하므로 실제보다 10³〜10⁵배(통과 중 폭 기준), barrier 사이 순변화 기준 10⁸배 이상 크다.
- E~ 사건 표는 **이 궤적에 대해서만** 엄밀하다. 다른 초기 상태로 일반화하지 않는다.

## 6. streaming (문항 13)

`stream.py`: executor 1 step → verifier가 즉시 전이·J 확인 → 이전 상태 버림 → 실행 중 인증서(J 사슬 sha256, 최종 상태, 사건과 E~ 구간, 최소 선분 R²)만 유지. 4개 사례 모두 VALID, **인증서가 W1 검증 인증서와 완전히 같다**(J 사슬 해시·최종 상태). 검증 루프 중 Python 힙 최고치 0.33 MB(1 De b 10, tracemalloc — 이 측정 실행은 느려져서 시간 값은 버림). 가능하다. 대가는 (1) 재검증용 witness가 남지 않음(C 저장), (2) 직렬 streaming이면 실행 시간 × (1 + 검증 비율). 여러 코어에 verifier를 두고 executor보다 몇 step 뒤에서 따라가게 하면(파이프라인) wall-clock 부담을 병렬 모드 수준으로 줄일 수 있다(설계만, 측정 안 함).

## 7. 결함 주입 (RULES 3)

`faults.json`, `python -B` + `__pycache__` 삭제 후 실행. **12/12 잡음.**

| 심은 결함 | 결과 |
|---|---|
| turning step J_x +1 ulp(상태 그대로) | INVALID(상태 불일치) |
| 같은 결함 + 이후 상태를 위조 J로 일관되게 재구성 | INVALID(J가 구간 밖) — 상태 일관성만으로는 통과 못 함 |
| barrier 재통과 step J_y −1 ulp, 일관 위조 | INVALID(J 구간 밖) |
| dr_z = 0인데 J_z = 1 | INVALID |
| 원자 j 위치 +1 raw / 원자 i 운동량 +1 raw(p_i ≠ −p_j) | INVALID / INVALID |
| 출구 60 step 전에서 witness 잘림 | REFUSED(출구 사건 없음) |
| verifier 쪽: QED 단거리항 삭제 / C6 끝자리 +10⁻⁷ / half kick dt/4 / 힘 부호 반전 | 모두 INVALID(틀린 verifier가 참 witness를 통과시키지 않음) |
| 대조: 참 witness + 참 verifier | VALID |

C6 끝자리 변경처럼 import 뒤에 상수를 바꾼 경우도 첫 step J에서 잡힌다(J 격자 2⁻⁸⁰이 모형 차이에 매우 민감). import 시점 전사 오류는 fingerprint가 먼저 잡는다.

## 8. S4d bootstrap과 비교 (문항 14)

| 항목 | S4d bootstrap(사전 worst-case) | 사후 검증(실제 궤적 1개) |
|---|---|---|
| 넘는 쪽 4개 | 닫히지 않음 | **4/4 VALID** |
| 증명 복잡도 | 셀 분류 부등식 3종 + 벽 차단 + 한 번 돌기 + first-crossing | step 검증 하나의 반복(정확 산술 + 구간 반올림 확인) |
| 새 lemma | 3개(분류 건전성, 한 번 돌기, 넘는 쪽 경계) — 미증명 | 0개 |
| 계산 | 셀 811개 도함수 약 63 s(공통) + 사례당 수 초 | 사례당 실행 1회분(직렬 ×5, 병렬 ×1) |
| 저장 | 사례당 작은 표 | 22 B/step(W2) 또는 약 4 KB 인증서(재검증 불가) |
| exact checker 복잡도 | 높음(worst-case 구간 부등식 다수) | 낮음(verifier 약 300줄, 경계 사례 없음) |
| 신뢰 기반 | 승인된 formal 부품 + 새 lemma | verifier 구현 + mpmath 구간 엄밀성 + 사양 공통 모드 |
| 실패 시 | NotCertified(실행 전 판정) | INVALID/REFUSED, 결과 미확정(실행 후 판정). 계산은 이미 소모 |
| 범위 | 초기 상태 하나에서 가능한 **모든** 이산 궤적 밴드 | 실제로 일어난 궤적 **하나** |
| 실행 전 보장 | Safety·inner Liveness(닫히는 사례) | 없음 — 끝나지 않으면 상한에서 REFUSED |
| many-body | 낮음(두 입자 R 한 변수 셀 분류) | **높음**: 검증 단위가 "쌍 impulse 반올림 1개"라 N체에서도 같은 형태, 비용 ∝ 쌍 수(executor와 같은 비율), 병렬 |

## 9. 새로 필요한 최소 구성요소 (문항 16)

1. **독립 J 반올림 verifier**(이번 scratch의 정식판): 전사 상수 + fingerprint, 별도 구간 라이브러리, 자동미분 도함수, 16384-bit 상한, INVALID/REFUSED 구분.
2. **정확 전이 검사기**: kick·drift(ties-even)·범위·r_min guard·상태 비교(정수).
3. **witness 형식**: 초기 상태 + J 열(W2) 또는 streaming 인증서(C). 어느 쪽을 확정 기록으로 둘지 결정 필요.
4. **commit 경계 규칙**: VALID 전에는 세계 상태로 쓰지 않음, 상한·REFUSED 처리. Proof Cache·Warehouse와의 관계는 이번 범위 밖.
5. **결함 주입 시험 세트**(이번 12종의 영구화).

## 10. 아직 증명되지 않은 것 (문항 17)

- mpmath 구간 exp·곱셈·sqrt의 엄밀성(신뢰 가정). 128 bit에서 모두 결정됐다는 사실은 이 가정 위에 있다.
- 사양 공통 모드: executor와 verifier가 공식(예: 지연 인자 적용 항, 감쇠 차수 n = 2k + K_add)을 같은 식으로 잘못 읽었을 가능성은 이 방식으로 배제되지 않는다. A-EV(독립 물리 감사)와는 다른 질문이며 섞지 않았다.
- 실행 전 Liveness: 사후 검증은 "끝났고 맞았다"만 준다. 갇히는 궤적이 있다면 REFUSED로 끝나고 세계는 진행하지 못한다. 이것을 ④-Liveness 대체로 받아들일지는 계약 결정이다.
- D_valid 전체·R_J 이후 무한 tail에 대한 명제는 이 방식으로 얻을 수 없다.
- 7개 사례 결과를 다른 초기 상태로 일반화하지 않는다. ρ → 0 쪽이나 ReferenceUndecided에 가까운 사례는 재지 않았다.
- 비율 약 5배(직렬)는 이 scratch 구현의 값이다. 최적화 구현의 비율은 재지 않았다(본질적 하한 약 1은 논증이며 측정이 아님).

## 11. 다음 최소 작업 (문항 18)

**설계자 결정 1개가 먼저다:** ④의 목적이 "모든 허용 입력에 대한 실행 전 보장"인지, "실제로 확정되는 모든 결과는 독립 검증을 통과한 것"인지. 후자를 허용하면 ④-Safety·Liveness·rounding-decision completeness 중 **실제 궤적 부분**은 사후 검증으로 닫고, formal 쪽은 (a) R_J 이후 tail, (b) REFUSED 빈도 상한(갇힘이 실제로 없음)만 남기는 HYBRID 구성이 된다. 결정 뒤 최소 작업은 이번 verifier를 시험 가능한 모듈로 옮기지 않고, **같은 scratch로 D_valid 경계 표본(넘는 쪽 가장 작은 |ρ|, H 아래 끝) 몇 개만** 재서 REFUSED가 0인지와 정밀도 상승이 일어나는지 확인하는 것이다.

## 12. 하지 않은 것

executor·dt·D_valid·장벽·Energy Bound v0·Proof Cache 변경, world state commit, runtime shortcut·Event Library 구현, A-EV 혼합(audit 모듈 미사용), 대규모 random survey, Vast. 관측을 인증으로 승격하지 않았다 — 이번 VALID는 7개 궤적 각각에 대한 사후 검증이며 ④ 인증이 아니다. **④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결** 유지.
