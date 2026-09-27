# C1-B1 ④-4b — 미해결 원인과 64-cell uniform cover의 한계

**상태: 진단 구현, ④-4b NotCertified 유지.** 2026-09-27, 기준 구현 `4088061`.
동일 R=20 / P=(1,0,0) / P_cap=2 / FX(96,48), FX(96,80), h=40, drift v2.
64-cell/16384-bit 한도·물리·실행기·D_valid·기존 인증기는 유지한다.

구현: `a_reference/c1b1_rounding_diagnosis.py`.
재생성: `python -m a_reference.c1b1_rounding_diagnosis a_reference/fixtures/c1b1_rounding_diagnosis_v1.json`.
JSON은 **진단·증명 구현 예시**이며 측정 fixture나 D_valid가 아니다.

## 1. 76개 기록의 전부 분류

기존 64회 cell 검사는 첫 shell에서 종료했고 닫힌 leaf는 singleton 8개다.
원래 미검사 여부를 보존하며 49개 대기 cell과 27개 미검사 shell root를 별도 진단한다.

| 원래 기록 | 실제 값 변화로 uniform 인증 불가 | 진단 정밀도에서 uniform 확인 | parent 구간 미분리 | 합계 |
|---|---:|---:|---:|---:|
| 첫 shell 대기 cell | 48 | 1 (singleton) | 0 | 49 |
| 미검사 shell root | 26 | 0 | 1 | 27 |
| 전체 | **74** | **1** | **1** | **76** |

74개 구간에서 기하 제약과 radial guard를 만족하는 두 끝 격자점의 **반올림 출력이 서로 다르다**.
각 끝점의 signed evaluator enclosure 양 끝은 같은 raw로 반올림되며 128 또는 256 bit에서 결정된다.
따라서 하나의 동일-output cell로 인정할 수 없는 원인은 단순 정밀도 부족이 아니다.
그 사이 모든 격자점의 판정 성공이나 실제 궤적 포함까지 증명한 것은 아니다.

singleton raw x=5629499534213128은 128 bit에서 결정된다.
마지막 shell은 radial/dot 교차 뒤 양 끝에서 impulse=(0,0,0)이지만,
256-bit parent x impulse enclosure는 설명용 소수로 약 [-2.6022, 1.4589] momentum ulp다.
JSON에는 정확한 유리수 끝값·폭·반올림 결과를 저장한다.
**양 끝 일치로 내부를 인증하지 않는다.** interval dependency인지 실제 내부 변화인지 미판정이다.
이 256-bit 진단을 해당 shell의 16384-bit cap 실패로 표현하지 않는다.

## 2. 각 cell의 막힌 조건과 그룹

각 기록에 원래 box·shell·미해결 사유·미검사 종류, 정확한 radial/dot 교차,
끝점 signed impulse·raw·정밀도·half-ulp 여유, parent R²·F/R·성분별 impulse 구간과 ulp 폭,
uniform 조건을 막는 축과 양 끝 반올림 결과/overflow 사유를 저장한다.
내부 pointwise completeness와 실제 궤적 포함은 `not_proved`다.

같은 shell·같은 원인의 격자상 연결 구간을 **29개 그룹**으로 묶고 원래 76개 기록을 모두 유지한다.
다른 shell의 전제를 합치거나 대칭을 이유로 입력을 건너뛰지 않는다.
정확한 교차는 좌표축 하나가 활성이고 나머지 상대 좌표/초기 운동량이 0인 1D만 지원한다.
기울어진 평면·2D/3D는 `unsupported_projection`이다. 교차의 등호는 보존한다.

## 3. 최소 65 uniform leaf가 필요한 증거

현재 `certify_grid_cell`은 cell 안 모든 점이 **같은 raw impulse vector**를 갖는 것을 요구한다.
원래 의무인 "각 점의 반올림이 한도 안에서 결정됨"보다 강한 충분조건이다.

첫 shell의 induced projection 안에 고정된 65개 격자점을 선택했다.
전부 상대 raw 좌표가 짝수이며 guard·coordinate tube·dot/cross 제약을 만족한다.
signed enclosure 양 끝이 해당 raw로 반올림되는지 재검사했고 65개의 impulse vector는 모두 다르다.
중복 점·중복 output을 서로 다른 증거로 세지 않는다.

하나의 uniform leaf는 서로 다른 두 output을 포함할 수 없다.
따라서 전체 projection의 uniform cover에는 **최소 65개의 leaf**가 필요하다.
내부 분할 노드까지 세는 현재 64-cell 검사 예산으로는 완료할 수 없다.
이는 65점으로 전체를 인증한 것이 아니라 64-leaf cover 주장에 대한 구성적 반박이다.

추가 65개는 고정된 **진단 witness budget**이다. 인증 cell budget을 늘리지 않고
진단 witness나 추가 점검 결과를 성공 cover로 채택하지 않는다.
궤적 replay·D_valid 조회·실측으로 bound 조정은 없다.

이 반박은 **현재 projection + uniform-output leaf 계약**에만 적용된다.
65개 모두가 실제 궤적에서 방문된다는 증거는 없고 더 강한 도달가능 제약이 제거할 가능성은 열려 있다.
원점 대칭 위치/운동량은 central kick과 half-even drift에서 부호 대칭이 보존되어 상대 raw 좌표가 짝수다.
짝수 witness만으로 반박이 성립하므로 이 예시에서 **parity 제약만 추가해도 obstruction은 남는다**.
실제 Lang ReferenceUndecided 반례, 16384-bit 불가능성, 물리 모순을 주장하지 않는다.

### 3.1 첫 64회 정상 전이에도 서로 다른 output 65개가 필요하다

위의 65개 격자 witness와 별도로, 기존 첫 shell 귀납 상한과 해석적 도함수로 조건부 의무를 점검했다.
이 단락의 전제는 **첫 64회 KDK 전이가 모두 정상적으로 결정되고 실행됨**이다.
이 전제를 미리 인증한 것은 아니며 실제 궤적을 실행하지 않았다.

`v_cap=α P_cap+D`에서 64회 상대 이동 길이 상한은 약 0.140569 bohr다.
정확한 유리수로 `20+64 v_cap < 20.15 < b=25`를 확인했다.
한 번 이동으로 q의 부호를 뒤집을 수도 없으므로 q는 양의 x축에 머물고 R=q_x다.
기존 귀납은 매 정상 전이에서 `ΔR²≥g_min>0`이며 guard 내에서
`ΔR≥g_min/(2 guard_b)`를 준다.

`B.derivatives(20, 2015/100)[2]`는 이 전체 작은 구간의 V''를 감싼다.
정확한 upper end가 음수임을 확인했다. 설명용 수치는 V''∈[-1.192504e-7,-1.088019e-7]이다.
양의 축에서 반올림 전 J(R)=-(h/2)V'(R)이므로 J'(R)=-(h/2)V''(R)>0.
인접 두 상태의 반올림 전 impulse 차이는

```
ΔJ ≥ -(h/2) upper(V'') g_min / (2 guard_b) > u_p
```

이다. 마지막 엄격 부등식은 정확한 유리수로 확인했으며 하한은 설명용으로 약 2.31e15 momentum ulp다.
동일 raw의 nearest-even rounding cell 폭은 u_p이므로 서로 같은 raw로 반올림될 수 없다.
따라서 이 전제 아래 초기 입력과 64회 뒤 입력, 총 65개 kick 입력은 서로 다른 output을 가진다.
어떤 정상 전이가 그 전에 미결정이라면 completeness는 이미 열려 있다.

**더 강한 도달가능 제약만으로 이 초기 상태의 전체 구간을 64개의 uniform-output cell에 담을 수는 없다.**
서로 다른 output을 허용하는 pointwise 판정 증명 표현이 필요하다.
조건부 유리수 점검과 소스 해시: `runs/c1b1_unresolved_diagnosis_20260927/conditional_obstruction.json`.
이는 기존 해석적 도함수 구현에 의존한 유도이며 독립 형식 증명이나 미래 실행 liveness 인증은 아니다.

## 4. 다음 증명 의무

같은 조건의 분할 반복이나 cell budget 증액으로 해결하지 않는다. 다음 중 수학적 근거가 필요하다.

1. 서로 다른 output을 허용하면서 **각 허용 격자점**의 half-ulp 분리와 실제 evaluator endpoint 오차를
   16384 bit 이내에서 일괄 보장하는 증명. 실수 구간 단조성만으로 격자점 경계 분리는 나오지 않는다.
2. 더 강한 이산 도달가능 불변량은 이 새 증명의 대상 집합을 축소하는 보조 수단으로 사용한다.
   같은-output cover를 64 cell에 맞추는 단독 해결책으로 취급하지 않는다.

어느 경로도 이번에 완성하지 않았다. 마지막 shell을 닫아도 첫 shell obstruction은 별도로 남는다.
④-4b NotCertified, ④ 전체 FROZEN·⑤·E_min 재생성·전체 산란각 보류를 유지한다.

## 5. 검증과 한계

관련 6개 파일 **122 passed, 71.35초**. 원래 기록 보존, 실제 끝점 impulse,
65-output 최소 leaf 수, 중복 count 방지, guard 밖/off-grid/거짓 raw/경계를 가로지르는 witness 거부,
미분리 실패 보존, 같은 끝점의 parent 인증 금지, 그룹 소속·등호 보존,
2D/3D 거부와 궤적/D_valid 접근 금지를 검사한다.
같은 끝점이면 uniform으로 승격하는 결함 주입도 해당 의무 시험에 잡혔다.

그 뒤 중복 count 결함 주입 시험을 추가한 최종 **LOCAL FULL: 2430 passed + 1 strict xfailed,
failure/error 0, skip 0, 362.74초**, 기존 컴파일러 cp949 해독 경고 25건.
JUnit 2431개 case와 exit 0·로그를 대조했고 신규 진단 시험은 17개다.
로그·JUnit·집계: `runs/c1b1_unresolved_diagnosis_20260927/{local_full.log,local_full.xml,verification_summary.json}`.
물리·기하·rounding 실행 코드 및 frozen C1-A/D_valid fixture는 `4088061`과 동일하다.

정확한 유리수·기존 evaluator의 signed enclosure를 쓰지만 PES 구현의 완전 독립 재증명이나 Lean/Coq 증명은 아니다.
자동 시험과 별도로 구상 일치성을 확인했다: A 물리와 성공/실패를 바꾸지 않고,
검사기의 과도한 충분조건을 드러내며 미검사 내부를 성공으로 승격하지 않는다.
새 생명·복사·진화 또는 현실 물리 정확성 증거가 아니다.
