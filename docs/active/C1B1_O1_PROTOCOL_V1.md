# C1-B1 O-1 사전 봉인 프로토콜

2026-10-01. 기준 HEAD/실제 origin/master = f03fb30c89c9f5d610bc1c6c419af8e6098431ec, clean.
사용자의 이번 O-1 지시는 새 O-1 origin의 생성·봉인·정상 replay 확인을 허용한다.
기존 PIPELINE_TEST_ONLY origin/history를 재분류하거나 재사용하지 않는다.

## 방법과 경계

독립 계산은 공개 S2_ar2_pot.f90의 십진 매개변수를 별도 파싱한다. 같은 Lang
potential, retardation ON, 질량과 정확한 초기 raw만 공유한다. c1b1_o1은
a_reference/a_numeric/engine/audit/c1b1_replay를 import하지 않는다.
중심력의 연속 Hamilton 방정식을 에너지 H와 L로 정확히 줄인 radial quadrature:
g(r)=2μ(H−V(r))−L²/r², dθ/dr=L/(r²√g), dt/dr=μ/√g.
시작 반경에서 처음 만나는 전환점을 찾고 r=rm+u²로 끝점을 정규화한다.
이는 별도의 연속 방정식 계산이며 KDK step/kick/drift/force/rounding을 쓰지 않는다.
수치 미분으로 끝점 극한을 계산한다. 추가 Cartesian DOP853(별도 complex-step 힘)
교차 확인은 주 기준값의 대체물이 아니라 독립 경로의 구조 점검이다.
일반 다입자 ODE 계산기가 아니며 보존량으로 구성하는 기준의 에너지/L 잔차는
적분기의 독립 보존 증거가 아니다. DOP853의 보존 변동을 따로 기록한다.

산란각은 유한 시작에서 같은 유한 출구 반경까지 상대 운동량 방향의 변화다.
출구 overshoot를 보간하지 않고 A의 실제 마지막 저장 반경을 독립 계산에도 적용한다.
χ는 atan2(cross(p_in,p_out),dot(p_in,p_out))의 signed principal 값이다.
휩쓴 각은 매 step을 풀어 누적하므로 여러 회전을 χ에 숨기지 않는다.
점근 χ∞나 무한거리 산란 전체 인증이라고 부르지 않는다.

## 실행 전 입력 봉인

canonical generator로 정확한 12 raw를 만들고 입력 manifest + SHA-256을 실행 전에 저장한다.
E는 De 단위, b는 bohr. orbit b는 동결 fixture의 b_orb·(1+rho)를 사용한다.
순서는 고정하며 첫 DISAGREE/불안정/미수렴에서 추가 물리 실행을 STOP한다.
실행하지 못한 나머지는 NOT_RUN_AFTER_STOP이고 UNRESOLVED에 합산하지 않는다.

| id | E/De | b 또는 rho | 선정 이유 |
|---|---:|---|---|
| ordinary | 0.5 | b=6 | 평범한 wall 통과 |
| small_b | 0.5 | b=0.1 | 거의 정면인 산란 |
| large_b | 0.5 | b=14 | 큰 b, 작은 편향 |
| low_energy | 0.01 | b=7 | 저에너지/인력 우물 |
| high_energy | 9.9 | b=0 | 기존 상한 안의 높은 에너지 정면충돌 |
| s4d_passing | 0.15 | rho=-0.005 | 기존 S4d passing-side 난점 |
| s4d_no_wall | 1 | b=10 | 기존 S4d wall 미진입 난점 |
| boundary_reflect | 0.5 | rho=+0.001 | 궤도 경계 reflecting-side |
| boundary_pass | 0.5 | rho=-0.001 | 궤도 경계 passing-side |
| boundary_challenge | 0.5 | rho=-0.0001 | 기준 초과가 가능한 도전 사례; D_valid 밖일 수 있음 |

## 사전 오차 예산과 판정

작업 정밀도 40/60/80 decimal digits, quadrature 내부 오차 목표 각각
1e-20/1e-30/1e-40. 전환점 bisection은 dps에 비례하고 오차 추정과
단계간 차를 모두 기록한다. 마지막 두 단계 각 관측 차 ≤1e-20,
마지막 quadrature 오차 추정 ≤1e-40가 아니면 UNRESOLVED, A와 비교하지 않는다.
이것은 관측된 수렴/추정이며 엄밀 interval certificate가 아니다.

판정은 결과를 보기 전에 아래 고정 예산을 선언한다. 측정 결과로 확대하지 않는다.
기존 산란 기준(설계 6절 상대 1e-5, boundary fixture의 절대 sweep 1e-5 rad)을
참고하되 O-1은 χ/방향/sweep 절대 1e-5 rad로 고정한다.
근접거리 상대 1e-5는 이번 O-1 추가 engineering criterion이며 기존 인증으로 주장하지 않는다.

| 관측량 | 시간 이산화 할당 | fixed-point 할당 | 관측 계산 할당 | 독립 수렴 할당 | 합계 |
|---|---:|---:|---:|---:|---:|
| χ, 방향, sweep(rad) | 9.98e-6−1e-20 | 1e-8 | 1e-8 | 1e-20 | 1e-5 |
| Rmin(bohr) | (9.98e-6−1e-20)·rm | 1e-8·rm | 1e-8·rm | 1e-20·rm | 1e-5·rm |
| max stored |H−H0|/De | 1e-3−2e-10 | 1e-10 | 1e-10 | 包含됨 | 1e-3 |

위 할당은 합격을 위한 상한 요구이며 각 원인의 실제 오차를 분리 증명한 결과가 아니다.
독립 기준은 A와 같은 정확 raw에서 출발하므로 초기 투영 차는 0이다.
A dt/profile을 바꾸지 않는다. Δt=20/10 연구는 이번 V1에서 실행하지 않는다.
L은 전 step 변화와 drift/kick 반올림으로 유도한 누적 torque 예산을 함께 보고한다.
에너지·L의 연속 기준은 일정하며 reconstruction 잔차와 DOP853 변동을 구분한다.

AGREE: 독립 수렴·공식 CONFIRMED provenance·χ/방향/sweep/Rmin/에너지 기준 모두 만족.
DISAGREE: 독립 수렴 후 하나 이상 초과. UNRESOLVED: 미수렴/불안정/비교조건 부족.
단위·P=(pj−pi)/2·μ=m/2·potential 전사·방향 branch·관측·양자화·이산화를
원인 후보로 분리하며 자동으로 어느 계산기가 틀렸다고 판정하지 않는다.
표본 AGREE는 전체 D_valid 인증·A-EV·현실 실험 비교가 아니다.

## 구현·시험 계획

새 독립 package c1b1_o1(model, continuous, compare), producer/confirm/observe가
fresh process로 분리된 tools/c1b1_o1_study.py. 수렴·외측 root·free-flight·
잘못된 부호/잠재함수·미수렴·허용오차 경계·봉인 변조·origin/승인 검사를 시험한다.
원본 states와 .c1br는 Git 밖 새 runs 폴더에 추가 전용 보존한다.
관련 시험 후 최종 python -m pytest tests -q -n 6와 JUnit/log를 보존한다.
불일치 STOP 후에도 이미 작성된 코드의 회귀 시험과 보고는 완료한다. push 금지.
