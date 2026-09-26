# C1-B1 바깥 formal bound v1 — 원인별 해석적 상한

설계자 승인(2026-09-27): ④ 해석적 상한을 먼저 만들고, ⑤에서 실측과 독립 대조한다.

## 계약과 증명 범위

- 실행 profile: 두 Ar40, 위치 FX(96,48), 운동량 FX(96,80), dt=40 원자 시간 단위, drift v2, half-even.
- 영역: 유한 radial shell `20 <= a <= R <= b`. 두 저장 끝점뿐 아니라 **그 사이 직선 선분 전체**가 shell에 있어야 한다.
- 범위: 성공한 KDK **1 step의 실제 저장 상태**에서 상대 수정 에너지와 상대 각운동량의 변화. 초기 격자 투영은 별도 일회 항.
- `q=r_j-r_i`, `P=(p_j-p_i)/2`, `mu=m_Ar40/2`, `L=q cross P`, `H=|P|²/(2mu)+V(|q|)`.
- `E_tilde=H-h²|F|²/(8mu)`. 이 식은 무한 modified-Hamiltonian 급수 전체를 의미하지 않는다.
- overflow·r_min 침범·미결정 반올림으로 중단한 실행에는 적용하지 않는다. half-step 운동량 크기 `|P_h|<=P_cap`은 명시적 전제다.
- 무한 시간·무한 분리거리의 체류 step 수, 산란각·체류시간 상한, 영역 부트스트랩과 E_min 재생성은 이 계약의 결론이 아니다.
- 동결 D_valid와 별도다. D_valid 파일·fixture를 읽거나 경계를 변경하지 않는다.

## 도함수 상한

동결 Lang 2024의 정확한 계수로 V의 0~3차 도함수를 구간 Taylor 산술로 평가한다. Taylor 계수 k는 V^(k)/k!이다.
EXP는 정수 enclosure, 사칙·역수·거듭제곱은 유리수 기반 outward dyadic rounding을 쓴다.
`F=sup|V'|`, `A2=sup|V''|`, `A3=sup|V'''|`는 shell 전체 상한이다. 표본 최댓값을 사용하지 않는다.

`M3=A3+3*A2/a+3*F/a²`이면 shell을 벗어나지 않는 선분에서
`|D³V(q)[d,d,d]| <= M3 |d|³`이다. 방향 c=n dot d에 대해
`D³V[d,d,d]=V''' c³+3(V''/R-V'/R²)c(|d|²-c²)`로부터 따른다.

## 위치 반올림

상대 drift 오차 d는 두 원자의 오차 차이이므로 각 성분 `|d_k|<=u_x`, `u_x=2^-48`.
`D=sqrt(3)*u_x`의 유리수 상한, `s=h P_cap/mu`라 두면

`B_E,position = F D + M3 ((s+D)³-s³)/12`

`B_L,position = D P_cap`.

에너지의 두 번째 항은 **양자화 때문에 길어진 실제 drift 선분**의 사다리꼴 오차 증가분이다. 위치항에서 빠뜨리지 않는다.

## 운동량 양자화

초기 원자 운동량의 반올림으로 상대 운동량 성분 오차는 `u_p/2` 이하다. `U=sqrt(3)*u_p/2`, `u_p=2^-80`.
초기 연속 상대 운동량 크기 `P_initial`을 명시하면

`B_E,momentum_initial=(2 P_initial U+U²)/(2mu)`

`B_L,momentum_initial=b U` (격자 투영 후 위치 shell 기준).

이 항은 매 step 다시 더하지 않는다. kick 후 p±J는 같은 FX 격자의 정수 덧셈이어서 **성공한 경우 추가 반올림 0**.
초기 위치 투영도 원할 때 별도 계산하며 drift 항과 혼동하지 않는다.

## Impulse 반올림과 이산화

half-kick 오차 e0,e1 각각의 크기 `<=U`. 실제 `P_h=P0+h F0/2+e0`, `P1=P_h+h F1/2+e1`를 대입하면

`B_E,impulse = (2 P_cap U+h F U+U²)/mu`

`B_L,impulse = 2 b U`.

정확한 central kick 토크는 0, drift의 정확한 변위는 P_h와 평행하다. 따라서 L의 변화는 위 위치·impulse 토크뿐이다.

`B_E,discretization=M3 s³/12`.

수정 에너지에서 h²(F1²-F0²)/(8mu) 항이 정확히 소거되고, 남은 정확한 KDK 부분은 potential line integral의 사다리꼴 잔차다.
실제 선분 변위 `q1-q0=h P_h/mu+d`를 대입하여 위 위치·impulse 항과 조립한다.

## 조립과 누적의 의미

`B_E,step=B_E,position+B_E,impulse+B_E,discretization+B_E,arithmetic(=0)`.

`B_L,step=B_L,position+B_L,impulse+B_L,arithmetic(=0)`.

초기 momentum/position 투영은 시작 상태의 표현 오차이고, E_tilde(N)-E_tilde(0)에는 넣지 않는다.
**각 step의 shell·P_cap 전제가 확인된 유한 N개**에만 triangle inequality로 합산 가능하다.
이 합계로 무한 outer tail이나 자동 체류 step 수를 인증하지 않는다. 실제 H 변화가 필요하면
`|delta H|<=B_E,step+h²F²/(8mu)`라는 endpoint correction을 별도로 붙인다.

계수·전제·원인별 항·단위·모델 fingerprint를 결과에 모두 남긴다. 위치 지배를 가정하지 않는다.

## 외부 수학 문헌과 한계

수정 Hamiltonian의 일반적 장시간 이론은 [Hairer, Lubich, Wanner의 Störmer–Verlet 연구](https://www.unige.ch/~hairer/preprints/gniverlet.html)를 참조한다.
그 이론의 정성적 보존 주장을 이 모듈의 정량 인증으로 사용하지 않는다. 위 유한식의 직접 대입과 Taylor 잔차만 사용한다.
형식 증명 보조기(Lean/Coq)에 의한 검증은 없으며, 해석적 유도와 유리수 구간 구현·결함 주입 시험으로 검증한다.

## 직접 대입한 에너지·각운동량 증명

벡터 중심력 f(q)=-grad V(q), a_k=h/2, 실제 반올림 오차 e0,e1,d를 쓴다.

`P_h=P0+a_k f0+e0`, `q1=q0+h P_h/mu+d`, `P1=P_h+a_k f1+e1`.

K1-K0를 정확히 전개하고 수정 에너지 항을 빼면

```
delta E_tilde
 = (q1-q0) dot (f0+f1)/2 + V1-V0
   - d dot (f0+f1)/2
   + P_h dot (e0+e1)/mu
   + a_k (f1 dot e1 - f0 dot e0)/mu
   + (|e1|²-|e0|²)/(2mu).
```

첫 줄은 저장 끝점 사이 potential line integral의 사다리꼴 잔차다. 그 절댓값은 `M3 |q1-q0|³/12` 이하.
`|q1-q0|<=s+D`를 넣고 `s³`와 나머지 증가분을 분리하면 이산화항과 위치항이 나온다.
나머지 줄에 `|f0|,|f1|<=F`, `|e0|,|e1|<=U`를 적용하면 impulse 항이 나온다.
즉 이미 반올림으로 바뀐 **실제 P_h와 실제 끝점**에 적용하는 항등식이다. 연속 기준 궤적의 작은 섭동 가정을 쓰지 않는다.

각운동량은 중심력 토크 `q0 cross f0=q1 cross f1=0`와 `(h P_h/mu) cross P_h=0`을 사용하여

`delta L = q0 cross e0 + d cross P_h + q1 cross e1`.

따라서 L의 이산화항은 정확히 0이다. 일반 lab-frame 총 L의 질량중심 항은 이 상대 L 계약에 포함되지 않는다.
질량중심 정지·대칭 초기 상태에서는 두 양이 같다.

초기 투영의 위치항은 `|grad E_tilde|<=F+h² F A_H/(4mu)`에서 나온다.
`A_H=max(sup|V''|,F/a)`는 중심력 potential Hessian의 두 고윳값을 덮는다.
운동량항은 정확한 kinetic 차 `(|P+eps|²-|P|²)/(2mu)`와 `|eps|<=U`로부터 나온다.
초기 위치를 먼저 투영하고 운동량을 나중에 투영하는 telescoping으로 교차항도 이 두 상한 안에 포함된다.

## 기계적 검증과 해석 예시

`tests/test_c1b1_outer_bound.py`: signed interval 극단값, Taylor factorial과 역수 부호, EXP 도함수,
원문 Fortran을 독립 파싱한 고정밀 numerical derivative 0~3차 대조(이 대조 자체는 형식 증명 아님),
shell 전 구간 enclosure, 내부를 가로질러 20 bohr 아래로 가는 chord 거부,
성공한 실제 KDK step의 수정 에너지·각운동량 변화 포함, 0/최대 momentum 격자,
초기 kinetic·torque 잔여항, global mpmath 15/40/60/100에서 완전 동일, 유한합의 순서 불변을 검사한다.

결함 주입: V''' 부호 반전은 독립 미분 시험을 실패시키고, 상대 drift 오차를 반 칸으로 줄이면
직접 구성한 drift torque가 제시된 상한을 넘는다. 시험을 통과시키기 위해 상한을 맞추지 않았다.

`a_reference/fixtures/c1b1_outer_bound_examples_v1.json`은 shell `[20,21]`, `[100,101]`, `[10000,10001]`,
`P_cap=1`의 **해석적 계산 예시**다. 측정 자료가 아니며 모든 분수·항·도함수 enclosure·소스 해시를 보존한다.
재생성: `python -m a_reference.c1b1_outer_bound a_reference/fixtures/c1b1_outer_bound_examples_v1.json`.

모델 매개변수의 현실 측정 불확도·질량 불확도는 이 수치 상한의 항이 아니다. 동결 모델의 명목 계수를 정확한 상수로 사용한다.

검증 기록(2026-09-27): 관련 28개 통과, LOCAL FULL **2335 passed + 1 strict xfailed / 실패 0 / skip 0**, 447.41초.
컴파일러 출력 cp949 해독 경고 25건은 미해결이다. 로그·JUnit은 `runs/c1b1_outer_bound_local_full.*`.
