# C1-B1 Small-World Reachable Domain Audit V1

2026-10-01. 문서·계약·기존 증거 감사. 새로운 물리 범위나 작은 세계의 초기조건을 정하는 문서가 아니다.

## 0. 판정과 한계

```text
C. SMALL_WORLD_ENVELOPE_UNDEFINED
O-1 boundary_pass: UNDECIDABLE_FROM_CURRENT_WORLD_SPEC
```

**목표 작은 A 세계의 허용 초기 상태 집합과 운영 범위가 충분히 정의되지 않았다.** 따라서 현재 D_valid가 그 세계를 전부 담는지, 필요한 지원 gap이 있는지, 그 크기와 빈도를 판정할 수 없다. 요청의 사양 선행 조건에 따라 해석적 reachable envelope 유도와 수치 probe 단계에 들어가지 않았다.

확인된 것은 두 Ar40 원자의 기준 동역학·수치 검증 계약, v6의 물리 개발 방향, 일반 경계 방향, 관측용으로 직접 준비한 O-1 입력과 결과다. 이 자료를 다원자 작은 세계의 초기조건·온도·입자 수·총에너지·운영 시간으로 대체하지 않는다. **Undefined는 세계의 실패나 unreachable의 증명이 아니다.**

production 변경 없음. KDK40/dt=40, D_valid, profile, PES, r_min, 승인 replay verifier, Energy Bound, O-1 상태, ④-Liveness/④-Safety/A-EV, Yoshida 후보 상태를 유지한다. KDK20 production 적용 및 새 적분기 탐색 없음.

## 1. Git과 작업 범위

| 항목 | 시작 확인 |
|---|---|
| 브랜치 | master |
| HEAD | a1685e590702b58c38b09ee95b3f9d048b3c71dd |
| origin/master | a1685e590702b58c38b09ee95b3f9d048b3c71dd |
| 실제 원격 확인 | git fetch origin 성공 후 위 ref 재확인 |
| ahead / behind | 0 / 0 |
| dirty | 없음 |
| 실행 중 관련 계산 | 프로세스 조회에서 pytest/C1-B1/이 저장소 명령행에 해당하는 Python 계산을 찾지 못함 |

관련 최근 commit: `a1685e5` Yoshida 후보 보존, `9e794a8` 로컬 KDK20/Yoshida 비용, `508bba4` O-1 원인 격리, `504e837` O-1 불일치 기록, `f03fb30` 소스 결합 재감사. 기존 branch/worktree 및 원격 계산 자원에 개입하지 않았다. 종료 상태·검증은 9절에 기록한다.

## 2. 작은 세계 사양의 출처와 정의 여부

| 필요한 조건 | 확인된 정의와 출처 | 이번 목표 세계에 빠진 것 |
|---|---|---|
| 세계 정체·허용 물리 | [현재 상태](../../CURRENT_STATE.md)의 C1-B1 → 다원자 기체 단계 순서. [v6 물리 폐쇄](../reference/A_MICRO_V6_PHYSICS_CLOSURE_V1.md) 1·4절의 고전·비상대론·분자 규모 방향 | 이 감사의 대상이 될 특정 small-world spec/허용 초기 상태 집합의 지정 |
| 차원·세계 크기 | C1-B1 상태는 3성분 위치·운동량. 물리 폐쇄 1.1·9절은 2D 검증의 한계와 향후 3D 요구를 구분 | 목표 세계의 차원, 상자 길이/부피, 단위, 밀도 또는 그에 해당하는 배치 제한 |
| 종류·입자 수 | [기준 실행기](../../a_reference/c1b1_two_atom.py)의 SPECIES_MASS는 Ar40, Run은 두 원자. 물리 폐쇄 4절은 Ar을 첫 현실 검증 종으로 선정 | 작은 세계가 Ar만 쓰는지, 다른 종이 있는지, N과 종별 개수 |
| 초기 위치 | [canonical 생성기](../../a_reference/c1b1_canonical_state.py)는 두 원자 산란을 R_START=20 bohr로 준비 | 작은 세계 전체의 초기 배치 또는 허용 배치 집합, 최소 거리·배치 상관관계 |
| 초기 속도·운동량 | C1-B1은 직접 주어진 두 원자 상태를 격자에 표현. O-1은 입력별 12 raw가 봉인됨 | 각 입자의 초기 운동량 또는 허용 집합, 전체/중심질량 운동량, 상관관계 |
| 에너지·온도 | C1-B1 admission은 초기 E_rel ≤ 10 De. 물리 폐쇄 2절에서 온도는 유도량 | 목표 세계의 총에너지 상한·기준틀, 운동/퍼텐셜 분배. 온도만 지정한다면 유한 결정론 초기 상태를 만드는 규칙·실제 에너지 제한도 필요 |
| 경계조건 | **일반 방향은 있음:** 물리 폐쇄 9절에서 C0~C2 주기 경계, C3 저장소 경계. 4절 Z4는 난수 열욕 금지·경계 감사 | 목표 단계, 실제 주기 상자/저장소의 치수·상태와 경계 에너지 회계. C1-B1의 두 원자 step에는 주기 상자 처리가 없음 |
| 외부 에너지·물질 | RULES 보존·외부 장부, 물리 폐쇄 2·3·4절의 공급/배출 경계 원칙 | 이번 세계가 닫힌계인지 구동계인지, 구동·교환량의 유한 상한과 시간 의존 규칙 |
| 허용 상호작용 | C1-B1은 Lang Ar-Ar 보존적 두 원자 상호작용. [설계 기록](A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) 머리말에서 다입자 힘 합산·thermostat·3체를 범위 밖으로 명시 | 다원자 세계의 승인된 상호작용 조립 계약. 쌍 합산·주기 image·장거리 항·3체 등의 채택 여부를 임의 확정할 수 없음 |
| 충돌 후 최대 pair 에너지 | 작은 세계에 대한 값 없음 | 초기 총에너지·가능한 총퍼텐셜 하한·외부 일·수치 에너지 잔차를 연결할 전제 |
| 진화 시간 | O-1은 유한 두 원자 산란의 출구와 max_steps를 정함 | 목표 세계의 물리적 운영 시간/종료 조건. 관측 샘플 간격이나 두 원자 출구는 이를 대신하지 못함 |

[규모·계산 구조 v0](../proposals/A_WORLD_COMPUTE_ARCHITECTURE_AND_SCALE_V0.md) 25장 단계 2의 `2 → 10 → 100 → 1,000`은 **예시**, 단계 7의 작은 실제 물질 세계는 **미승인·미구현 제안**이다. 특정 N이나 초기 사양으로 채택하지 않았다. 대륙 규모 제안도 분자 작은 세계의 상자 크기가 아니다.

`worlds/`의 Git 추적 명세 7개는 REPO_MAP의 A0/A1/A2 및 이전 causal 계통 명세다. 해당 파일 목록과 지도상 계통을 확인했으며, 그 본문을 v6 Ar 세계로 해석하지 않았다. 과거 격자·결합·환경 세계의 수치를 가져오지 않았다.

## 3. 현재 D_valid가 실제로 말하는 것

정본은 [동결 색인](../frozen/D_VALID_V2.md), [계약 코드](../../a_reference/c1b1_domain_contract.py), [v3 fixture](../../a_reference/fixtures/c1b1_orbit_boundary_v3.json)다. 코드의 `SCOPE = initial_state`, `evaluate_run`과 `classify`를 확인했다.

| 부분 | 정확한 계약 요지 |
|---|---|
| 공통 D_base | 1e-8 De ≤ E_rel ≤ 10 De, 0 ≤ b ≤ B_MAX=2·RE_GRID, 위치 FX(96,48), 운동량 FX(96,80), dt=40, drift v2 |
| L | D_base 안에서 `b_orb > B_MAX·(1+B_ORB_MARGIN)`로 capture가 조사 b 범위 밖인 경우. fixture 7개 에너지에 한정되지 않음 |
| H | D_base 안에서 `e_lo > e_max_grid()·(1+E_MAX_MARGIN)`인 경우. E_MAX_MARGIN=1/1000. 모든 b라는 표현도 **D_base의 b 범위 안**이라는 뜻 |
| F | 정확한 fixture 에너지 3/20, 1/5, 3/10, 1/2, 7/10, 9/10, 99/100과 canonical lattice 초기 상태의 동일성이 필요. 각 쪽 smallest_pass ≤ |rho| ≤ outermost_pass |
| 미지원 | E/b/profile이 D_base 밖, 속박 상태 등 E_LOW 아래, 미측정 capture 에너지, canonical identity 불일치, inside_band/uncertain_edge/beyond_probes, 판단 불가 |

이것은 **초기 상태에 대한 numerical_validated evidence**다. YES를 formal certification이나 궤적 전체 지원으로 읽지 않는다. 단순 E 범위만으로 통과하지 않으며, F의 translated/rotated 상태도 동일성 요구를 다시 만족하지 않으면 인정되지 않는다.

별도 `new_run(validated_only=True)`는 초기 상대에너지의 적분기 admission 검사이고, D_valid 판정은 실행을 막지 않는다. `step()`에 매 step D_valid 검사나 매 step 10 De admission 검사가 있다고 해석하지 않는다.

**지도 비교의 미정 부분:** 목표 세계의 상태에서 비교할 pair 양을 정해야 한다. 임의 pair의 순간 E_rel·L·b를 산란 입구 좌표로 볼 것인지, 어떤 입구/분리 조건에서 두 원자 계약을 연결할 것인지가 아직 없다. `rho=b/b_orb-1`은 해당 산란 좌표에서 정의된 값이다. 현재 `run.validation`을 궤적 중간에 자동 재평가해서 판정이 바뀐 것으로 보고하지 않는다.

## 4. Reachability 등급과 유도 방법

| 등급 | 이번 감사 결과 |
|---|---|
| OBSERVED | 기존 O-1에서 직접 준비한 두 원자 입력과 그 유한 궤적이 기록돼 있음. 결과 JSON의 input/confirmation/A/비교 항목을 읽음. 이번에 새 궤적·전 step replay를 실행하지 않음 |
| PHYSICALLY REACHABLE | **목표 작은 세계에 대해서는 미판정.** 허용 초기 집합·경계·물리 조립·운영 시간이 없어서 도달 집합을 정의하지 못함 |
| NOT SHOWN REACHABLE | 증거가 없는 상태를 unreachable로 판정하지 않음. O-1 문제 입력의 지정된 최종 판정은 UNDECIDABLE_FROM_CURRENT_WORLD_SPEC |

해석적 bound 결과 **0개**. 수치 probe·sweep **0개**. 사양 미정 상태에서 임의 에너지·온도·N을 넣어 계속 계산하지 않았다. 보존법칙을 쓸 전제를 확인했지만, 세계의 수치 상한을 유도하지 않았다.

초기 pair E만으로 미래 최대 E를 묶지 않았다. 다입자 에너지 전달을 분석하려면 **승인된 다원자 상호작용 계약과 전체 상태**가 먼저 필요하다. 현재 두 원자 실행기에는 세 번째 원자의 에너지 전달이 없다. 향후 물리 폐쇄의 내부 자유도·3체/저장소 가능성을 현재 구현에서 실행된 과정으로 주장하지 않는다.

또한 RULES의 보존 요구를 KDK40에서 연속 에너지·각운동량이 정확한 불변량이라는 증명으로 바꾸지 않는다. [현재 상태](../../CURRENT_STATE.md)와 [Energy Bound 승인 범위](C1B1_ENERGY_BOUND_V0.md)의 유한·조건부 증거는 작은 다원자 세계 전체의 에너지 예산이 아니다. 형식 인증된 outer reachable enclosure도 특정 전제 아래의 반올림 증명 영역이며 이 감사의 전체 세계 도달 집합이 아니다.

## 5. 영역 표와 겹침 판정

`reachable?`는 **목표 small world에서의 reachability**다. 기존 두 원자 관측은 별도 근거 열에 둔다. 지원 필요도는 R1/R2/R3를 정할 근거가 없으므로 미분류로 보존한다.

| 영역 | reachable? | current D_valid? | 근거 | 지원 필요도 |
|---|---|---|---|---|
| D_valid의 L/H/F 인정 초기 상태 | UNKNOWN | YES | 계약 코드상 numerical_validated. 세계 초기 집합과 연결되지 않음 | 미분류 |
| O-1 low_energy: E=0.01 De, b=7 | UNKNOWN | YES | 기존 observed two-atom / O-1 AGREE. 세계의 자연 생성 증거 아님 | 미분류 |
| O-1 boundary_reflect: E=0.5 De, rho=+0.001 | UNKNOWN | YES | 기존 observed two-atom / O-1 AGREE | 미분류 |
| **O-1 boundary_pass: E=0.5 De, rho=-0.001** | **UNKNOWN** | **NO** | 기존 observed two-atom / inside_band / O-1 DISAGREE | **미분류** |
| O-1 ordinary: E=0.5 De, b=6 | UNKNOWN | NO | 기존 observed two-atom / beyond_probes / O-1 AGREE. unsupported가 정확도 실패와 동의어 아님 | 미분류 |
| D_base 밖 에너지·b 및 속박 상태 | UNKNOWN | NO | 계약상 unsupported. 세계 전제가 없어 도달/배제 여부 미판정 | 미분류 |
| REACHABLE ∩ D_valid | 집합 미정 | 교집합 정의상 YES | 도달 집합을 정의하지 못해 구성원·크기 계산 불가 | 미분류 |
| REACHABLE ∖ D_valid | 집합 미정 | 차집합 정의상 NO | 필수 지원 gap의 존재·폭·빈도 계산 불가 | 미분류 |
| D_valid ∖ REACHABLE | 집합 미정 | 차집합 정의상 YES | 작은 세계에서 불필요한 영역을 지정할 수 없음 | 미분류 |

**확인된 small-world gap은 0건이며, gap이 없다고 증명한 것도 아니다.** R1 필수, R2 조건부, R3 현재 불필요의 각 목록은 모두 미판정이다. UNKNOWN을 R3로 넣거나, 반복 관측이 없다는 이유로 희귀/불필요라고 하지 않는다.

## 6. O-1 DISAGREE의 위치

```text
E_nominal = 0.5 De
rho_nominal = -0.001
b_nominal = 11.707286169880804 bohr (표시값)
D_valid = unsupported / delta_minus inside_band
small-world reachable = UNDECIDABLE_FROM_CURRENT_WORLD_SPEC
```

정확한 b·12 raw·실현 에너지와 b_current/rho_current는 [입력 봉인](C1B1_O1_INPUTS_V1.json) 및 [기존 결과](C1B1_O1_RESULTS_V1.json)의 boundary_pass 행에 보존돼 있다. 표시 소수로 초기 상태를 재생성하지 않았다.

E=1/2 fixture 음쪽은 largest_nonpass=0.00127165784397, smallest_pass=0.00131607401295, outermost_pass=0.01이다. 문제 입력의 |rho|=0.001은 largest_nonpass보다 안쪽이다. 이 사실은 **현재 수치 검증 띠에서의 위치**이며, 목표 세계의 도달 가능성을 배제하는 물리 제약이 아니다. 새 reachable gap 폭은 계산하지 않았다.

기존 기록에서 boundary_pass는 admission passed, O1_OBSERVATION_ONLY origin, 17,284 step, REPLAY_VERIFIED/CONFIRMED이며 각도 차이 1.30928186e-5 rad로 사전 1e-5 기준을 초과했다. 의미는 “직접 준비한 해당 두 원자 역사를 승인 verifier로 확인했고 별도 연속 기준과 관측 차이가 났다”다. 다원자 세계의 다른 충돌에서 이 입력이 만들어졌다는 증거가 아니다. 이번 감사는 raw witness 전부를 재독해/replay한 결과가 아니라 Git 추적 결과·봉인·보고서의 확인이다.

```text
O-1 = STOPPED / NOT PASSED
TIME_DISCRETIZATION_SUPPORTED = numerical diagnostic
Yoshida40 = VALIDATED NUMERICAL CANDIDATE / NOT PRODUCTION / NOT FORMALLY CERTIFIED
```

이 상태를 유지한다. 기존 dt20/10/5 관측 진단이나 Yoshida panel 결과는 작은 세계의 reachability 증명이 아니다.

## 7. 감사를 재개하는 데 필요한 최소 설계 결정

다음 항목을 하나의 버전 붙은 small-world 명세로 지정해야 한다. **이번 감사에서 값을 선택하지 않았다.**

1. **대상과 물리:** 첫 다원자 Ar 기체인지 다른 세계인지, 차원·종·N·허용 상호작용 조립·pairwise 계약을 적용할 사건/입구의 의미. 현재 미구현 물리를 쓸 경우 명세 결정과 구현·검증을 구분한다.
2. **공간과 초기 상태:** 상자/경계 형식과 치수, 초기 위치·최소 간격, 운동량. 한 raw 초기 상태인지 허용 집합 전체인지도 정한다. 허용 집합은 에너지 총량·상관관계를 포함해야 한다.
3. **에너지 회계:** 닫힌계 또는 외부 구동, 초기 전체 에너지 상한·중심질량 운동량, 공급/배출·저장소의 상태/상한. 실제 수치 실행의 에너지 잔차를 어느 검증 계약으로 관리할지 지정한다. 온도 하나는 유한계의 최대 pair 에너지 제한을 대체하지 않는다.
4. **시간과 필요도:** 물리적 운영 기간·종료 조건, R1의 “흔함/반복됨”을 어떤 운영 관측 기준으로 구분할지. reachable의 존재 판정과 빈도 판정을 별도로 유지한다.

정의 뒤 첫 분석은 총에너지·허용 퍼텐셜 하한·경계 회계에서 pair 에너지/운동량의 **필요조건 enclosure**를 만들고, pair 상태와 D_valid 산란 입구 계약을 연결하는 것이다. 그러한 enclosure의 바깥은 배제 근거가 될 수 있으나, enclosure 안의 모든 점이 실제 reachable이라는 충분조건은 아니다. 실제 도달 경로나 추가 증명을 별도로 요구한다. 이번에는 그 유도도 시작하지 않았다.

300/400 K를 이 세계의 온도로 채택하지 않았다. [O-3 조사](C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md) 4.3절의 약 5%/13%는 온도 모델·충돌 가중을 가정한 추정이다. 고정된 유한 결정론 세계의 필수 사건, 엄밀 최대 에너지, 발생 빈도 또는 실행 중 중단 빈도의 증명이 아니다. 현재 코드의 에너지 admission은 new_run 시점이라는 점도 구분한다.

결론 B가 아니므로 KDK20 global / 제한 영역 substep / Yoshida40 재검토의 지원 비교 단계에 들어가지 않는다. 향후 B가 입증될 경우에만 사용자 요청의 후보 순서를 기록·비교한다.

## 8. 읽기 범위와 구상 일치성 확인

시작은 AGENTS/RULES/CURRENT_STATE/REPO_MAP이었다. AGENTS·RULES를 읽고, 큰 상태·지도 문서는 분할 읽기로 현재 대시보드와 이력·계통을 확인했다. 필수 문서 출력의 일부가 도구 출력 한도에서 잘려 관련 구간을 다시 읽었다. C1-B1 거대 설계 기록 전체의 정독이나 저장소 전체의 전수 감사라고 주장하지 않는다.

- 직접 확인: D_valid 코드 머리말·상수·canonical_member·classify·evaluate_run, two_atom의 상태/step/상대에너지/admission, 동결 색인, fixture의 E=1/2 행, O-1 입력/결과의 해당 행, 물리 폐쇄의 상태·경계·단계 규칙, O-3 조사, Yoshida 상태.
- 부분 확인: C1-B1 설계 기록의 범위 선언·관련 설계/판정 구간, 규모 제안의 상태·다원자 및 작은 세계 단계, 물질 아키텍처·입자 과거 초안의 관련 공간·상태·보존 원칙, Liveness 조사 0~2절. 필요한 값이 없음을 확인하기 위한 scoped 문서 검색 포함.
- 하지 않음: runs 전체 탐색, 기존 raw 전체 replay, 기존 수치 캠페인 재실행, 외부 문헌의 새 검증, 레거시 세계 본문 전수 읽기, A-EV 작업선 감사.

자동 시험과 별도로 요청과 결론을 대조했다. (a) 임의 사양 없이 undefined에서 멈춤, (b) 직접 준비한 observed 입력을 목표 세계 reachable로 승격하지 않음, (c) unsupported를 unreachable 또는 모두 부정확으로 바꾸지 않음, (d) 필요도 미정 상태에서 R3/production 확대를 선택하지 않음, (e) 기존 실패·후보·Gate의 상태를 유지함. 이는 작성자의 문서/논리 대조이며 별도 독립 감사자 승인이나 형식 증명은 아니다.

## 9. 계산·검증·종료 기록

새 궤적 0, 신규 해석적 bound 0, probe 0, sweep 0, Vast/SSH 0. JSON 읽기·Git/프로세스·문서 확인만 수행했다. 새로운 분석 도구·시험·production 소스는 추가하지 않았다. 관련 기존 시험과 문서 링크/변경 범위 검사를 아래에 기록한다.

관련 시험을 **이번에 새로 실행**했다.

```text
python -m pytest tests/test_c1b1_domain_contract.py tests/test_c1b1_canonical_state.py tests/test_c1b1_o1.py -q --junitxml=runs/c1b1_small_world_reachability_audit_20261001_v1/related.xml
60 passed in 66.38s
exit 0 / failure 0 / error 0 / skipped 0
```

이는 기존 D_valid·초기 상태 동일성·O-1 관측 계약의 관련 회귀 시험이다. 작은 세계 reachability를 증명하는 시험이 아니다. 신규 시험은 추가하지 않았다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 신규 감사 문서와 상태·색인·안내·O-3 해석 제한 문서만 변경했다. 변경 목록으로 production/common/frozen/fixture/시험 변경이 없음을 확인했다. 공식 LOCAL FULL 기준선 숫자는 갱신하지 않는다.

`git diff --check` 통과. 감사 문서와 새 색인의 로컬 링크 존재 검사 통과. 시작 HEAD와 LF 정규 바이트를 대조한 주요 소스·고정 증거 10개는 모두 동일했다(two_atom, domain_contract, canonical_state, ar2_lang2024, profiles, boundary fixture, O-1 seal/results, 원인 격리 results, production verifier approval). Git의 문서 LF→CRLF 안내가 있었으며 이를 물리 소스 변경이나 시험 실패로 세지 않는다.

증거: [관련 시험 로그](../../runs/c1b1_small_world_reachability_audit_20261001_v1/related.log), [JUnit](../../runs/c1b1_small_world_reachability_audit_20261001_v1/related.xml), [소스/증거·링크 검사](../../runs/c1b1_small_world_reachability_audit_20261001_v1/integrity.json). 이 Git 밖 폴더는 이번 감사의 새 로그만 담으며 기존 runs 원본은 건드리지 않았다.

종료 HEAD와 origin/master는 시작과 같은 `a1685e590702b58c38b09ee95b3f9d048b3c71dd`, ahead/behind **0/0**. 종료 dirty는 신규 이 문서 1개와 수정 문서 4개(CURRENT_STATE, DOCUMENT_STATUS_INDEX, active README, O-3 조사)다. staging/commit/push **없음**.
