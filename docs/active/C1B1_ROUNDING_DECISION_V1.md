# C1-B1 ④-4 — rounding-decision completeness v1

**문서 분류: 현재 활성 A / C1-B1.** 활성 Gate는 C1-B1, outer formal bound ④ 진행이다. ④ 전체는 FROZEN이 아니며 ⑤는 미착수다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


2026-09-27, 계약 `c1b1-rounding-decision-v1`.
설계자 판정: ④-2/④-3 implemented, **conditional on rounding-decision completeness**. ④ FROZEN은 아직 금지.

## 상태: tail은 닫음, 일반적인 pre-tail은 아직 열림

- profile: 두 Ar40, FX(96,48)/FX(96,80), h=40, drift v2, half-even, 동결 Lang retardation ON.
- 기존 평가기의 실제 정밀도 순서 128→256→512→…→16384를 사용한다. 한도를 높이거나 실패를 skip/xfail로 바꾸지 않는다.
- **R≥R_J인 모든 표현 가능한 상대 위치**의 impulse 판정을 최대 512 bit에서 인증했다.
  R_J=10240 bohr. FX 위치 범위 밖까지 실제 프로그램이 무한히 실행된다는 주장은 아니다.
- 일반 pre-tail 인증은 **④-2가 생성한 reachable enclosure 전체의 격자 cover**를 대상으로 한다.
  임의의 20≤R<R_J 상태공간으로 확장하지 않는다. 단일 궤적의 point witness는 별도 증거이며 일반 인증을 대신하지 않는다.
  현재 R=20 예시의 induced enclosure cover는 **NotCertified**이고 비영 구간 전체는 **미완료**.
- 따라서 ④ 전체 동결·⑤ 진입·전체 산란각/E_min 재생성은 하지 않는다. D_valid v2·기준 경계 fixture·canonical 생성기 변경 없음.

## 1. 유한 step 수와 정밀도 완전성은 다른 의무다

④-2는 `N≤N_max<∞`를 보장하지만, N개의 값이 각 half-ulp 경계에서 얼마나 떨어져 있는지는 별도다.
16384-bit 완전성을 얻으려면 **각 필요한 입력의 결정성 또는 전체 reachable enclosure의 결정성**을 증명해야 한다.
유한 개라는 사실만으로 정해진 정밀도 한도를 도출할 수 없다.

판정 보조기의 명시적 예시: `x=2^-81+2^-20000`이면 FX(96,80)의 정확한 raw는 1이다.
그러나 16384-bit 이하 outward dyadic enclosure의 아래 끝점은 half-ulp인 2^-81이고 위 끝점은 그보다 크다.
아래 끝은 half-even으로 raw 0, 위 끝은 raw 1이므로 유한 한도 안에서 결정되지 않는다.
**이는 일반 결정 보조기의 반례이며, 이 값이 실제 Lang 힘으로 발생한다는 주장이 아니다.**

2,387,040,365 step도 **certified upper bound, not predicted/observed residence time**다.
그 횟수를 brute-force 실행하도록 작업을 확장하지 않았다. 실제 짧은 prefix 인증과 해석적 구간 cover를 구별한다.

## 2. 이번 점검에서 재현한 평가기 결함 두 개

### 2.1 EXP의 고정 cutoff가 높은 정밀도에서 거짓 구간을 반환

기존 `c1b1_two_atom._exp_neg`는 x≥4096이면 항상 [0,1]·2^-M을 반환했다.
이것은 작은 M에서만 안전하다. M=8192, x=4096일 때 e<3에서

```
e^-4096 > 3^-4096 > 2^-8192
```

이므로 제시한 upper end가 실제 값보다 작다. 마지막 부등식은 3<4에서 따른다.
검증은 별도 EXP 근삿값이나 같은 cutoff 함수를 참조하지 않는 정수·유리수 비교다.

수정: `x_lower≥M*LN2_UPPER`, `LN2_UPPER=6932/10000>ln(2)`일 때만 [0,1]·2^-M을 사용한다.
그 조건이면 e^-x<2^-M. 그 밖에는 기존 정수 Taylor/squaring enclosure를 계산한다.
동결 C1-A와 A-Numeric EXP 자체는 변경하지 않았다. ④-1의 fixed 160-bit EXP cutoff도 별개이며 이 결함의 대상이 아니다.

### 2.2 양 끝의 같은 overflow 사유를 값 전체의 overflow로 오판

거친 interval이 [−2^20,+2^20]이면 FX(96,80)에서 양 끝 모두 overflow하지만 가운데 0은 정상 값이다.
기존 `_decide`는 두 끝의 halt **사유 문자열**이 같다는 이유로 즉시 중단했다.
실제 `q=(2^47,0,0), h_kick=20`에서도 이 오류가 재현됐다. 실제 힘은 매우 작아 impulse가 0인데도 coarse enclosure로 잘못 중단했다.

수정: 동일 halt 사유라도 구간이 0을 가로지르면 계속 정밀도를 높인다.
같은 부호 쪽의 실제 overflow는 그대로 halt한다. 한도까지 여전히 모호하면 `ReferenceUndecided`로 중단한다.
point witness도 coarse endpoint overflow를 exact value overflow라고 간주하지 않는다.

이는 물리 법칙이나 반올림 규칙의 변경이 아니라, 그 규칙을 잘못 구현한 구간/판정 코드의 수정이다.
기존 정상 fixture를 잘못됐다고 폐기하지 않는다. D_valid 파일과 측정 데이터는 그대로 유지한다.

## 3. 실제 평가기를 덮는 uniform tail decision cover

각 위치 성분은 signed 96-bit raw / 2^48이다. 두 raw의 차에서 `|q_k|<2^48`이므로
`R<sqrt(3)*2^48<2^49`이다. 따라서 실제 실행기의 모든 legal tail 입력은 유한 radial 범위 [R_J,2^49] 안에 있다.
2^49는 endpoint cover를 위한 충분 cap이며 그 거리의 축방향 좌표 자체를 profile로 표현할 수 있다는 뜻이 아니다.

이 범위를 비율 9/8인 **210개 연속 구간 [a,b]**으로 덮는다. gap과 overlap 누락이 없는지를 시험한다.
동역학 shell의 5/4보다 좁은 cover는 rational retardation derivative의 interval dependency 팽창을 줄인다.
실측 궤적을 보고 반경이나 error bound를 맞추지 않는다. 각 cell의 검증이 실패하면 인정하지 않는다.

정밀도 M마다 실제 평가기의 `C._model_R([floor(a 2^M),ceil(b 2^M)], M, True)`를 사용한다.
point의 sqrt(R²) enclosure는 이 radial cover 안에 포함된다.
각 cell에서 모든 EXP argument의 lower bound가 `M*LN2_UPPER` 이상인지 **기계적으로 검사한다**.
따라서 모든 point와 parent의 EXP가 같은 [0,1] branch를 사용한다. range-reduction guard가 달라지는
일반 Taylor endpoint의 수치 단조성을 가정하지 않는다. 이 충분조건이 안 닫히는 zero cell은 거부한다.
outward 덧셈·곱셈·스케일·양수 분모 나눗셈·inverse power와 이 constant EXP branch의 interval inclusion으로
whole-cell evaluator enclosure는 cell 안의 각 point evaluator enclosure를 포함한다.
EXP shortcut의 [0,1] branch도 포함된다: 그 branch의 실제 값은 양수이면서 1 ulp보다 작으므로,
이를 포함하는 dyadic parent enclosure의 아래 끝은 ≤0, 위 끝은 ≥1이어야 한다.

cell의 signed derivative interval과 inverse R interval을 실제 `C._mul`로 곱하여 G=F/R의 구간 [G_lo,G_hi]를 만든다.
어떤 방향도 `|q_k|≤R≤b`이므로 실제 component impulse enclosure의 끝점은

```
|J_k,end| ≤ max(|G_lo|,|G_hi|)/2^M * b*h/2 = J_cap.
```

각 cell에서 `J_cap<u_p/2`를 엄격하게 검사한다. 따라서 각 point의 양 끝 모두 raw 0으로 round된다.
half-ulp 동점에 걸리지 않으며, 세 component를 따로 표본 추출할 필요도 없다.
현재 cover의 62개 cell은 256 bit, 148개 cell은 512 bit에서 닫힌다. 전체 충분 정밀도는 **512 bit**다.
이것이 actual worst necessary precision의 증명은 아니다.

더 낮은 M에서 정상 raw가 결정되면 그것도 같은 정확한 값이다.
coarse interval이 서로 반대쪽 overflow를 만나도 이제 refine하므로 512-bit 판정 전에 잘못 halt하지 않는다.
같은 쪽 overflow는 정확한 impulse가 정상 raw 0인 값의 유효 enclosure와 양립할 수 없다.
따라서 수정된 실제 `_decide`가 precision cap 때문에 tail에서 중단하지 않는다는 실행 연결이 성립한다.

이 인증은 위치 profile가 유효한 동안의 impulse 결정성이다. FX 위치 overflow, continuous physical tail force,
무한 L 또는 무한 실제 FX 실행을 없애는 인증이 아니다. ④-3의 연속 nonzero impulse/방향 bound는 그대로 별개다.

## 4. pre-tail 인증 API와 실패 상태

`a_reference/c1b1_rounding_completeness.py`:

- `certify_zero_tail()`: 위 uniform cover. runtime 모델과 정밀도 schedule을 확인한다.
  낮아진 cap의 cache 재사용을 막고 public result 변경이 cached proof를 오염시키지 않게 복사한다.
- `zero_cell(a,b)`: 해당 finite radial cell의 모든 방향을 raw 0으로 결정할 때만 인정한다.
  비영 impulse가 있는 cell을 zero라고 부르지 않는다.
- `certify_impulse_point(q)`: 실제 상대 위치 grid의 한 점에서 signed endpoint, 각 component raw와 필요한 M을 남긴다.
  두 끝이 실제 profile에서 같은 값으로 round되어야 한다. 이 한 점을 주변 상태 인증으로 확대하지 않는다.
- `certify_outgoing_decisions(run,p_cap,max_steps=64)`: ④-2/④-3의 geometry certificate와 조립한다.
  모든 finite guard cell이 zero cover로 닫히면 미래 궤적을 돌리지 않고 완료할 수 있다.
  아니면 복사한 상태에서 **기존 C.step**으로 제한된 정확 replay와 point witness를 만든다.
  원본 상태·validation을 바꾸지 않는다. D_valid를 읽지 않으며 물리 오차의 실측값에 맞추지 않는다.

완료는 finite 영역 전체가 덮이고 tail에 인계된 경우에만 `certified_for_this_initial_state`다.
확인한 전이가 남은 비영 구간을 덮지 못하면 `status=incomplete_budget`, completeness=`not_proved`.
판정이 미결정이면 `status=not_certified_decision`, completeness=`not_proved`와 실패 위치/종류/메시지를 보존한다.
자동 budget 증가·미검사 미래의 인정·실패 삭제·skip/xfail 처리는 없다.
단일 초기 상태 인증을 전체 초기 상태 family의 인증으로 바꾸지 않는다.

## 5. 예시와 provenance

`fixtures/c1b1_rounding_decision_examples_v1.json`은 측정 fixture가 아닌 증명 구현 예시다.

| 예시 | 결과 |
|---|---|
| legal FX tail 전체 | 210 cell, 모든 impulse raw 0, 충분 정밀도 최대 512 bit |
| nominal R=R_J−0.01, P=(1,0,0), P_cap=2에서 양자화한 실제 상태 | finite zero-cell cover + tail로 완료. trajectory step 호출 0 |
| R=20, P=(1,0,0), P_cap=2, replay budget=2 | 전이 2개, point witness 3개. **incomplete_budget**이며 전체 pre-tail 미인증 |
| 같은 R=20 상태의 shell-induced enclosure, cell budget=64 | trajectory 호출 0, 64 cell 검사 후 **NotCertified**. 미해결 cell/미검사 shell 기록 38개 보존 |

모든 Fraction은 분자/분모 문자열로 저장한다. 8개 소스의 LF-normalized SHA256과 실제 초기 raw 상태를 보존한다.
재생성: `python -m a_reference.c1b1_rounding_completeness a_reference/fixtures/c1b1_rounding_decision_examples_v1.json`.

기존 `c1b1_outer_bootstrap_example_v1.json`도 evaluator 소스 수정에 따라 provenance를 재생성했다.
`78a1a25` 기록과의 자동 대조에서 **certificate 전체는 완전히 동일**하고 `c1b1_two_atom.py`의 소스 hash만 달라진다.
그 파일은 analytic example이며 D_valid 기준 fixture가 아니다. 이전 버전은 Git 이력에 보존한다.

## 6. 검증과 남은 의무

신규 rounding 시험 24개와 adaptive cover 시험 14개. 관련 outer/rounding 시험 **97 passed, 27.99초**.
EXP 고정 cutoff 실제 실패→수정, opposite overflow endpoint 및 실제 far-tail 입력 실패→수정,
진짜 같은 쪽 overflow 유지, 낮은 precision cap의 거부, 반환 cache 오염 방지,
signed point witness, incomplete prefix, future ReferenceUndecided 보존,
D_valid 비간섭, source hash·예시 재생성 등을 검증한다.
결함 주입: EXP 고정 cutoff 복원, tail cover의 cell 하나 삭제, incomplete prefix를 certified로 승격하면 원래 의무 시험이 실패한다.

최종 LOCAL FULL: **2404 passed + 1 strict xfailed / failure 0 / skip 0, 388.84초**, 기존 cp949 경고 25건.
현재 상태 문서와 `runs/c1b1_rounding_decision_local_full_v1.*`에 기록한다.
컴파일러 진단 출력의 기존 encoding 경고를 물리 실패나 해결된 문제로 바꾸지 않는다.

현재 shell induction의 20→R_J 비영 reachable enclosure에서 16384-bit completeness는 아직 닫히지 않았다.
남은 목표는 아래 adaptive cover를 완결하는 것이다. 정확한 초기 상태 하나의 실제 전 구간 추적은 이후 ⑤의 독립 대조 사례로 남긴다.
현재 2-step prefix와 finite N_max만으로 전체를 인증하지 않는다. ⑤·전체 산란각·E_min·④ FROZEN은 계속 보류한다.
이 구현은 평가기 자체의 interval 연산을 사용하는 proof layer다. Lean/Coq 검증이나 완전 독립 evaluator 증명은 아니다.

## 7. shell-induced reachable enclosure의 adaptive rounding-cell subdivision

`certify_reachable_rounding(run,p_cap,max_cells=64)`는 기존 ④-2 certificate를 직접 생성하여 그 shell guard만 사용한다.
외부에서 임의의 더 큰 shell을 입력해 인증 범위를 확장하지 않는다. `C.step`이나 D_valid 조회를 호출하지 않는다.

원래 ④-2 packet은 `a≤R≤guard_b`, `|P|≤P_cap`, `q·P≥w_floor` 등의 scalar 조건을 전달했다.
④-4b에서는 [귀납적 geometry 제약](C1B1_REACHABLE_GEOMETRY_V1.md)을 추가한다.
초기 `q_k=P_k=0`이 보존되는 축을 고정하고, 누적 kick/체류/유한 L bound로
좌표 tube와 `q·P0`, `|q×P0|` 제약을 유도한다. 임의의 기울어진 평면이나 초기 ray 고정은 가정하지 않는다.
이 제약을 radial guard와 함께 교차한 projection을 덮는다. exact reachable trajectory 집합이라고 부르지 않는다.
임의의 다른 실행 profile/에너지/초기 상태 family를 함께 인증하지 않는다.

원래 root box는 `[-floor(guard_b/u_x),+floor(guard_b/u_x)]³`이었다.
현재 root는 해당 shell의 귀납적 coordinate tube를 교차한 **정수 raw 격자**다.
dot 상한 또는 cross norm² 하한으로 direction 제약과 교집합이 없다고 증명한 cell만 추가 제외한다.
등호와 겹치는 cell은 계속 판정 대상이다.
`certify_grid_cell(box,a,b)`는 각 좌표 interval의 정확한 제곱 최솟값/최댓값으로 R² 범위를 계산하고
shell guard의 [a²,b²]와 교차시킨다. 교집합이 비면 증명으로 제외한다. 표본이 없다는 이유로 제외하지 않는다.
다른 경우에는 outward sqrt interval → 실제 evaluator의 signed G=F/R enclosure → 각 성분의 signed impulse interval로 이어진다.
각 component interval의 양 끝을 실제 FX(96,80) half-even으로 반올림해서 **동일한 정수 raw**일 때만 그 cell을 인정한다.
0과 비영 정수 impulse 모두 지원한다. singleton에서는 기존 실제 point evaluator의 precision schedule 전부를 사용한다.

일반 Taylor EXP의 수치 endpoint 단조성은 가정하지 않는다. `execution_exp_cover(x,M)`는
실제 `_exp_neg`가 선택할 수 있는 모든 range-reduction k와 shortcut을 포함한다.
negative Taylor의 floor/ceil term·교대 합을 interval로 실행하고, `t_hi≤1`로 멈출 수 있는 **모든 iteration**의 출력을 합친다.
그 stopping branch에서 remainder margin `2*t_hi+2≤4`를 사용하고 실제 k회 outward squaring을 적용한다.
따라서 parent EXP cover는 수학적 값뿐 아니라 child evaluator가 실제 반환하는 dyadic endpoint도 포함한다.
`_model_R`의 선택적 proof EXP 인자를 통해 이후의 실제 interval 연산을 재사용한다.
기본 실행 경로는 기존 `_exp_neg`를 그대로 호출한다. 별도 EXP로 실행기 결과를 교체하지 않는다.

셀을 닫지 못하면 가장 긴 raw 축을 `[lo,mid]`와 `[mid+1,hi]`로 나눈다.
두 child는 격자에서 겹치지 않고 빠진 raw 정수도 없다. 연속 좌표의 `mid→mid+1` 틈은 이 계약의 입력이 아니다.
탐색은 고정된 cell budget을 넘기거나 singleton의 판정이 닫히지 않으면 멈춘다.
`NotCertified` exception의 `report`에 이미 확인한 leaves, pending cells, 미검사 shells와 원래 geometry certificate를 보존한다.
열린 cell이 하나라도 있으면 성공 record를 반환하지 않는다. tie를 거의 불가능하다고 배제하거나 자동 재시도하지 않는다.

현재 R=20 예시는 64-cell 예산에서 닫히지 않았다. 이것은 **16384 bit의 실제 Lang 반례도, 불가능성 증명도 아니다**.
원래 scalar enclosure 예시의 결과는 위 기록이다. coordinate/direction projection을 적용해 재생성한 예시는
상대 좌표 3D→1D, exact zero 축 y/z이며 64 cell 검사 뒤 미해결 record 76개(미검사 shell 포함)가 남아 `NotCertified`다.
geometry를 포함한 관련 시험은 **106 passed, 51.59초**.
후속 **REMOTE PYTHON FULL은 2292 passed + 121 skipped + 1 strict xfailed, 실패 0, 98.89초, exit 0**이다.
이번 LOCAL FULL은 설계자의 원격 이전 지시로 중단했다. 위 2404개 LOCAL FULL은 이전 구현의 기록이며 원격 skip을 통과로 세지 않는다.
더 좁은 projection의 구현만으로 completeness를 인정하지 않는다. 미해결 cell은 그대로 보존한다.
비영 multi-state cell과 실제 signed impulse의 일치, 분할 gap mutation, precision cap 저하 거부,
synthetic exact tie 거부 등을 시험한다. synthetic tie는 reachable Lang 상태라는 주장이 아니다.

## 8. 64-cell 미해결 진단: 현재 uniform-output 방식의 예산 충돌

[원인별 진단](C1B1_ROUNDING_DIAGNOSIS_V1.md)은 원래 76개 기록을 보존하여 분석한다.
74개는 실제 구간 양 끝의 raw impulse가 달라 uniform cell일 수 없고, 1개는 singleton,
1개는 끝점은 0이지만 parent enclosure가 rounding 경계를 가로지른다.
첫 shell의 현재 projection에 서로 다른 output 65개가 있어 최소 65 uniform leaf가 필요하다.
64-cell 예산이나 16384-bit 한도를 늘리지 않았다. 이것은 현재 cover 방식의 한계이며
실제 궤적의 precision failure 또는 전체 pointwise completeness 불가능성 증명이 아니다.
더 강한 이산 도달가능 제약 또는 비상수-output 구간의 pointwise separation 증명이 남는다.
④-4b NotCertified와 ④ 전체 FROZEN·⑤·E_min·전체 산란각 보류를 유지한다.
