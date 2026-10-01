# C1-B1 O-1 독립 수치 재현 V1 — DISAGREE / STOP

2026-10-01. 결과: **AGREE 8 / DISAGREE 1 / UNRESOLVED 0 / NOT_RUN_AFTER_STOP 1**. O-1 전체 통과나 C1-B1 종료가 아니다.

`E=0.5 De, rho=-0.001, b=11.707286169880804 bohr`에서 독립 기준은 수렴했지만 A와의 산란각·출구 방향·휩쓴 각 차이가 사전 절대 1e-5 rad 기준을 넘었다. 즉시 STOP했고 rho=-0.0001은 실행하지 않았다. 이 입력의 기존 D_valid 분류는 unsupported다. D_valid의 실패 반례 또는 A/독립 계산기 어느 한쪽의 오류라고 자동 결론내리지 않는다.

[봉인 프로토콜](C1B1_O1_PROTOCOL_V1.md) / [정확한 입력·source hash 봉인](C1B1_O1_INPUTS_V1.json) / [전체 수치·비용·원본 해시](C1B1_O1_RESULTS_V1.json).

## 결과

| 입력 | E/De | b(bohr), rho | D_valid | 차이 χ(rad) | 차이 Rmin(bohr) | 판정 |
|---|---:|---|---|---:|---:|---|
| ordinary | 0.5 | 6 | unsupported | 1.12999486e-06 | 2.02381666e-06 | AGREE |
| small_b | 0.5 | 0.1 | unsupported | 2.29236994e-08 | 2.30745799e-06 | AGREE |
| large_b | 0.5 | 14 | unsupported | 1.99205874e-09 | 2.06285655e-09 | AGREE |
| low_energy | 0.01 | 7 | numerical_validated | 1.8786725e-07 | 1.47146809e-06 | AGREE |
| high_energy | 9.9 | 0 | numerical_validated | 0 | 3.19884842e-05 | AGREE |
| s4d_passing | 0.15 | 14.0321716094, rho=-0.005 | numerical_validated | 2.98832218e-07 | 1.10360602e-06 | AGREE |
| s4d_no_wall | 1 | 10 | numerical_validated | 5.98308813e-07 | 4.69362345e-08 | AGREE |
| boundary_reflect | 0.5 | 11.7307241802, rho=0.001 | numerical_validated | 5.90471656e-06 | 9.86649708e-07 | AGREE |
| boundary_pass | 0.5 | 11.7072861699, rho=-0.001 | unsupported | 1.30928186e-05 | 2.82996364e-07 | DISAGREE |
| boundary_challenge | 0.5 | rho=-0.0001 | unsupported | 미측정 | 미측정 | NOT_RUN_AFTER_STOP |

χ는 무한거리 산란각이 아니라 **정확히 같은 유한 출발 raw → A의 실제 유한 출구 반경**에서 상대 운동량 방향이 바뀐 signed principal angle이다. 같은 출력 반경을 사용해 마지막 step의 반경 overshoot를 다른 물리 사건으로 비교하지 않았다. 여러 회전은 별도 sweep으로 기록했다. 이 표본은 전체 O-1/D_valid를 대표하는 전수 조사나 인증이 아니다.

## 각 입력의 독립 기준값과 A 값

| 입력 | 독립 χ(rad) | A χ(rad) | 독립 Rmin(bohr) | A Rmin(bohr) |
|---|---:|---:|---:|---:|
| ordinary | -1.3037753458593 | -1.3037764758541 | 6.3325112078993 | 6.332513231716 |
| small_b | -3.113066849837 | -3.1130668727607 | 6.2296613056422 | 6.2296589981842 |
| large_b | 0.15462839263995 | 0.15462839064789 | 13.659605010021 | 13.659605007958 |
| low_energy | -1.999588704741 | -1.9995888926082 | 6.3468514663958 | 6.3468499949277 |
| high_energy | -3.1415926535898 | -3.1415926535898 | 5.5092583411739 | 5.5092903296582 |
| s4d_passing | -1.845716913916 | -1.8457172127482 | 6.5391641422805 | 6.5391630386745 |
| s4d_no_wall | 1.9147719101616 | 1.9147725084704 | 7.0733564016726 | 7.0733564486089 |
| boundary_reflect | 2.3214808647129 | 2.3214749599963 | 9.9504384836762 | 9.9504394703259 |
| boundary_pass | -0.1236323484416 | -0.123619255623 | 6.881880516381 | 6.8818807993774 |

## 입력별 독립 수렴

모든 실행 입력의 40/60/80자리 내부 적분 목표 1e-20/1e-30/1e-40가 충족됐고, 마지막 두 단계의 모든 비교 관측량 변화가 1e-20 이하였다. 아래 값은 60→80자리의 관측된 차이이며 엄밀 오차 상한으로 승격하지 않는다.

| 입력 | χ 차이(rad) | Rmin 차이(bohr) | 자체 수렴 |
|---|---:|---:|---|
| ordinary | 4.6370479495e-52 | 5.79487316785e-60 | 충족 |
| small_b | 9.49558583064e-54 | 2.85714978148e-60 | 충족 |
| large_b | 2.66135425698e-51 | 3.35639074009e-59 | 충족 |
| low_energy | 3.41282598387e-53 | 4.17457995597e-60 | 충족 |
| high_energy | 4.59230781641e-60 | 2.82696408318e-60 | 충족 |
| s4d_passing | 1.20564059735e-51 | 2.12595205113e-60 | 충족 |
| s4d_no_wall | 9.76187924524e-51 | 4.90878603435e-60 | 충족 |
| boundary_reflect | 4.20916155652e-50 | 5.95797024533e-60 | 충족 |
| boundary_pass | 8.39752390058e-51 | 1.2190939734e-60 | 충족 |

## 불일치 입력의 실제 값

| 관측량 | 독립 연속 기준(80자리 결과 일부) | A(dt=40) | 차이 |
|---|---:|---:|---:|
| χ(rad) | -0.123632348441596 | -0.123619255623002 | 1.30928186e-05 |
| 출구 방향(rad) | 2.39432640035996 | 2.39433949317855 | 1.30928186e-05 |
| 휩쓴 각(rad) | 8.05395958087667 | 8.05397267369515 | 1.30928185e-05 |
| Rmin(bohr) | 6.88188051638105 | 6.88188079937741 | 2.82996364e-07 |

60→80자리 차이: χ **8.39752390058e-51 rad**, Rmin **1.2190939734e-60 bohr**. 마지막 quadrature 내부 오차 추정 1.01000001100010121311000000000000000000000000000000000000000100001e-89 ≤1e-40. 별도 Cartesian DOP853(rtol=1e-12)의 출구 방향은 고정밀 기준과 7.92690358e-11 rad 차이다. UNRESOLVED를 AGREE로 바꾸지 않았다.

## 독립 계산기와 코드 공유 경계

- `c1b1_o1/model.py`: 공개 Fortran 십진 매개변수의 별도 파서와 연속 V(r). 원문 SHA-256은 동결 C1-A 원문과 동일. 동결 fixture와 V 및 자체 수치 미분 F를 230건 비교해 raw 불일치 0.
- `c1b1_o1/continuous.py`: H,L로 중심력 Hamilton 방정식을 줄여 r=rm+u²의 고정밀 quadrature로 시간·각을 계산한다. 40/60/80 digits, 목표 내부 적분 오차 1e-20/1e-30/1e-40. 같은 물리의 정확한 두 원자 환원이며 A의 KDK를 쓰지 않는다.
- Cartesian DOP853 보조 점검: 같은 독립 PES의 complex-step 미분으로 힘을 구하고 일반 연속 ODE를 rtol 1e-10/1e-12로 적분. 두 경로가 같은 독립 PES 구현을 공유하므로 potential 전사의 공통 오류 가능성은 남는다. 230 fixture 대조가 이를 완전 증명하지 않는다.
- 공유: Lang 2024 사양/공개 데이터, Ar40 질량(정확 u/me 비), 단위, retardation ON, canonical 초기조건의 정확 raw. 초기조건 생성기는 허용된 공유 영역이다.
- 비공유: reference step/kick/drift/force/impulse/rounding helper, replay verifier의 수치 모델. O-1 package의 import는 표준 라이브러리+mpmath뿐이다. scipy는 보조 ODE driver에서만 쓴다.
- replay wire writer와 전이 재구성은 **trajectory 보존·provenance binding** 단계에서만 사용한다. replay verifier를 연속 O-1 계산기로 사용하지 않았다.

## origin과 CONFIRMED

새 입력 10개를 trajectory 실행 전에 봉인했다(payload SHA-256 `60cfef99966f7d90fe19ee898812bc7c21cda1832c19510d1fa30139f9fd69a0`). 이번 사용자의 새 O-1 입력 봉인·정상 검증 지시를 O1_OBSERVATION_ONLY origin 생성 권한으로 사용했다. 9개 실행, 총 **104,843 step** 모두 approved production verifier로 전 step 검증해 REPLAY_VERIFIED / CONFIRMED를 얻었다. 승인 fingerprint와 초기 raw/step/원본 witness 결합을 확인했다.
기존 7개 PIPELINE_TEST_ONLY history는 읽어서 재분류하지 않았다. 초기 입장 E<=10 De/r_min 검사와 D_valid 초기 수치 분류는 다른 조건이며 unsupported도 표본에 남겼다. 기존 CONFIRMED 의미와 네 상태를 바꾸지 않았다. O-1 DISAGREE가 replay 비트 INVALID라는 뜻은 아니다.

## 에너지와 각운동량

| 입력 | A 전 저장 상태 최대 에너지 변화/De | A 최대 L 변화(a.u.) | 독립 ODE 최대 에너지 변화/De | 독립 ODE 최대 L 변화 |
|---|---:|---:|---:|---:|
| ordinary | 1.27702919e-05 | 4.81740533e-13 | 1.629017e-12 | 1.0658141e-13 |
| small_b | 2.05143496e-05 | 4.47943413e-13 | 1.62721797e-12 | 6.66133815e-15 |
| large_b | 1.56664848e-09 | 5.55580005e-13 | 8.99512423e-14 | 9.7912789e-12 |
| low_energy | 1.1006977e-05 | 6.01536533e-13 | 3.43141502e-13 | 5.32907052e-14 |
| high_energy | 0.000557707276 | 0 | 9.87880523e-12 | 0 |
| s4d_passing | 4.25902695e-06 | 1.81712221e-12 | 2.96719165e-13 | 4.58300065e-12 |
| s4d_no_wall | 4.55672378e-07 | 1.55996911e-12 | 4.34884273e-13 | 1.5063506e-12 |
| boundary_reflect | 1.6272636e-08 | 8.3211314e-13 | 1.63651293e-13 | 3.24007488e-12 |
| boundary_pass | 7.84810129e-07 | 1.42766432e-12 | 3.45352803e-13 | 4.25615099e-12 |

A 에너지는 모든 저장 상태에서 별도 PES를 35자리로 평가했다(표본 샘플링 아님). L은 raw 정수에서 정확 분수로 계산했고 모든 기록의 drift/kick 반올림 누적 torque 예산 안이다. budget의 half-step momentum cap은 실제 보존 J와 raw에서 별도로 확인했다. quadrature는 보존량으로 구성하므로 reconstruction 잔차가 작다는 것을 독립적인 에너지 보존 시험으로 세지 않는다. 그와 별도로 DOP853의 수치 보존 변동을 위 표에 기록했다.

## 허용 오차와 한계

χ/출구 방향/sweep 절대 1e-5 rad, Rmin 상대 1e-5, 전 저장 상태 에너지 변동 1e-3 De를 실행 전에 선언했다. 시간 이산화·fixed-point·관측·독립 수렴의 합성 배분은 봉인 프로토콜에 있다. 이는 engineering 상한 요구이며 원인별 실제 오차를 엄밀 분리한 certificate가 아니다. 기존 설계 6절의 상대 sweep/time 1e-5도 별도로 확인했으며 **9/9 만족**했다. 기존 상대 기준을 V1 절대 기준으로 대체·완화하지 않았다. 마지막 입력은 상대 sweep 기준에는 맞지만 추가 절대 1e-5 rad 기준에는 맞지 않는다.
Rmin 추가 기준은 이번 O-1의 사전 기준이다. A Rmin은 저장 drift chord의 최소 거리이며 관측 계산은 binary64로 한다. endpoint round-off와 chord 관측량의 의미를 연속 전환점과 구별한다. A의 시간 간격/위치/운동량 profile/r_min/PES/D_valid는 그대로이며 Δt=20/10 추가 연구도 실행하지 않았다.
수렴은 관측된 정밀도 안정성과 내부 error estimate에 근거한다. interval certificate/formal ODE error bound는 아니다. root는 시작 반경에서 내려가 최초 sign-change를 찾는 고정 mesh이며 임의 separatrix 전체의 root completeness를 증명하지 않는다. 이번 표본은 별도 일반 ODE로도 같은 궤도·출구를 확인했다. 일반 다입자/비중심력/속박 궤도는 V1 지원 밖이다.

## 원인 후보와 STOP

증거가 가리키는 우선 후보는 경계 근처에서 시간 이산화 오차가 증폭되는 현상이다(해석, 원인 확정 아님). 원인 후보는 (1) KDK dt=40 이산화, (2) fixed-point·초기 표현과 관측, (3) 독립 potential 전사·단위·μ/P 정의, (4) root/방향 branch·끝점 처리로 나눴다. 정확 raw 및 질량·단위 일치, 230 PES/F 대조, 60/80자리 안정, 별도 DOP853 일치가 3·4를 일부 좁히지만 제거하거나 어느 쪽이 틀렸다고 단정하지 않는다.
후속 후보 실험은 동일 raw의 Δt=20/10 **관측용 별도 reference study** 및 같은 dt의 더 높은 표현과 비교해 이산화/양자화를 구별하는 것이다. **이번에는 실행하지 않았다.** 사용자의 불일치 STOP 지시를 따르며 추가 물리 실행·허용오차 확대·기존 history 재해석 없이 보고한다.
Energy Bound v0 APPROVED / ④-Liveness NotCertified / ④-Safety Conditional / A-EV Unresolved 유지. O-3, A-EV, native J, live pipe, rollback controller, D_valid 재설계, 새 물리·potential/dt/r_min 변경 없음.

## 비용과 검증

9개 순차 campaign wall **1176.569s (19.61분)**. 기록된 단계별 CPU 합 **1084.484s**. 실행기 step CPU 123.594s / replay CPU 332.750s / O-1 계산·관측 CPU 628.141s. 봉인·일부 setup/원본 I/O CPU는 이 합 밖이다. LOCAL FULL이 초반과 겹쳤으므로 wall은 당시 경합 아래의 실제 측정값이다. 원격 임대/과금 없음.
관련 초기 묶음 113 passed +1 strict xfailed(35.95s), 최종 신규 O-1 18 passed(1.77s). 자유 궤도의 닫힌 해, 외측 root 선택, potential 변경, 관측량 fault 5종, 미수렴·미확정·허용오차 경계·봉인 변조를 확인했다. package의 금지 import도 AST 시험으로 확인했다.
**LOCAL FULL = python -m pytest tests -q -n 6: 3501 passed + 1 strict xfailed, 실제 skip 0, failures/errors 0, exit 0, 25 warnings, 669.38s.** JUnit tests 3502/skipped 1은 binary64 탈락 strict xfail. 기존 native subprocess cp949 해독 경고 25건을 해결하지 않았다. 공식 AGENTS 숫자는 설계자 판정 없이 갱신하지 않았다.

## 자동 시험과 별도의 구상 일치성 점검

구현의 데이터 흐름을 시험 결과와 별도로 대조했다. 실행기는 기준 물리로 raw를 만들고, 별도 approved verifier가 역사 전부를 확인한 뒤 CONFIRMED만 관측으로 넘긴다. O-1 연속 계산은 세계 값을 바꾸지 않는다. 초기조건·판정 기준·실패 가능 표본이 먼저 봉인되어 있고, 실패 시 다음 사례가 실행되지 않았다. 수치 검증·replay 확인·형식 인증·현실 실험을 구별했다. 이 점검은 작성자의 별도 설계 대조이며 타인의 독립 감사나 새 형식 증명이 아니다.

## 보존과 Git

모든 raw states와 .c1br 원본은 `runs/c1b1_o1_20261001_v1/` 및 각 confirmed_store에 보존했다. 전체 JSON은 경로·SHA-256·byte 수를 담는다. summary만으로 전 step 재검증할 수 없고, Git만 전달해도 runs 원본이 전달된다고 주장하지 않는다. 사전 실패 2건은 attempt_notes.json에 기록했고 실패 trajectory 삭제/자동 재실행 0이다.
기준 HEAD와 원격은 f03fb30c89c9f5d610bc1c6c419af8e6098431ec. 기존 실행 코드·승인 verifier·frozen fixture 변경 0이며 봉인한 소스와 마지막 상태의 bytes/hash가 일치한다. 신규 O-1 코드·시험·봉인·보고 문서와 상태 안내만 추가/갱신했다. commit/push 없음.
