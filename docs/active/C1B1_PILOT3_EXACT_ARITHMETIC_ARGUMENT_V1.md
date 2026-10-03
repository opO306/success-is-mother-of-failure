# C1-B1 Pilot 3 exact arithmetic obligations

**구현 전 정리한 exact 산술 의무와 조건부 합성 논증.** Baseline 실제 계측은
최적화 구현 전에 완료됐고, A/B/BC/BCD/ABCD를 별도 구현했다. 아래 항등식과 같은 M의
끝값 검사를 분리해서 보존한다. 승격 최종 판정은 후속 결과 문서를 따른다.
근사와 새로운 물리식은 추가하지 않는다.

## 범위와 신뢰 조건

기존 slow REF, Candidate B 및 Combined는 보존한다. raw 경로의 전제는 정확한
`FixedPoint` 클래스와 일관된 width/F/lo/hi/name, 유효한 stored raw, 정확한 dt이다.
Binary64·subclass·동작을 덮어쓴 lookalike로 일반화하지 않는다. Python 정수 계산은
정확하며 물리·수치 프로그램을 실행 도중 외부에서 변경하지 않는다는 기존 조건을 따른다.
아래 합성 논증과 실제 동일 M 끝값 검사는 정식 증명기에서 얻은 프로그램 정리가 아니다.

## A: 동결 유리수와 도함수 계수 준비

양의 분모 d에 대해 c=n/d, 정수 i이면 c*i=(n*i)/d이다. 약분 여부는 이 정확한 값에
영향을 주지 않는다. 준비된 (n,d)와 (n*i,d)는 값과 부호를 그대로 유지해야 한다.
`2*k*c`, retardation 계수의 `(m+1)*a`도 같은 항등식이다. 입력 R/M에 대한 답을
저장하지 않고, 세계에서 고정된 계수 형식만 immutable tuple로 준비한다.

구간 정수쌍 (l,h)에 대해 기존 `_scale`은 c>=0일 때
`(floor(l*n/d), ceil(h*n/d))`, c<0일 때 양 끝을 교환한 같은 계산이다.
준비된 pair가 기존 Fraction과 같은 값이면 두 directed integer endpoint가 같다.
상수 alpha/eta를 2^-M 격자에 놓는 `_const`에도 같은 교차곱이 적용된다.
중간 interval multiply, divide, add, exponential과 그 순서는 보존해야 한다.

## B: raw 상대 좌표

같은 위치 격자 F에서 각 stored 좌표의 정확한 뜻은 r_raw/2^F이다. 따라서

```
to_exact(rj_raw)-to_exact(ri_raw) = (rj_raw-ri_raw)/2^F.
```

Python 정수 차는 stored 위치 범위를 넘을 수 있지만 정확한 상대 좌표이다. 이를
위치 profile에 먼저 반올림하거나 범위 검사하는 것은 허용되지 않는다. 상대 좌표를
segment guard에 넘길 때 필요한 Fraction은 이 비율을 정확하게 나타내야 한다.
세 축은 같은 위치 격자라는 전제이며, 운동량 F와 같다는 전제는 없다.

## C: raw R²와 동일 M 반지름 끝값

v_k=rj_raw,k-ri_raw,k이면

```
R² = sum(v_k*v_k) / 2^(2F).
```

음수·영·축 크기 차이에도 같은 항등식이다. 세 항 모두 포함하고 중간 반올림을
하지 않는다. 분자 N과 shift 2F는 약분하지 않아도 된다. 동일 M의 반지름 계산에서
`s=N*2^(2M-2F)`를 정수 quotient q와 remainder로 나눈다. e=2M-2F>=0이면
q=N<<e, remainder=0이고, e<0이면 divmod(N,2^-e)를 사용한다.
`l=isqrt(q)`는 기존 하한이며 상한은 `l + int(remainder!=0 or l*l!=q)`이다.
정확한 제곱에서만 두 끝값이 같다는 조건도 기존 radius와 동일하다.
R_MIN² 비교는 N*R_MIN².denominator와 R_MIN².numerator*2^(2F)의 비교로 보존된다.

## D: 마지막 component 구간과 nearest-even

같은 M의 F/R 정수 구간을 (g_l,g_h), dt_kick=t_n/t_d (t_d>0)로 놓으면
축 v의 두 정확한 끝값은

```
g_l*v*t_n / (2^(M+F)*t_d),
g_h*v*t_n / (2^(M+F)*t_d).
```

v 또는 t_n이 음수일 때 min/max 순서가 바뀐다. 기존 Fraction 경로의 각 끝값과
교차곱이 같아야 하며 마지막 J raw가 우연히 같은 것만으로 통과하지 않는다.
운동량 격자 H에서 rounding은 각 끝값에 2^H를 곱한 정확한 유리수를 nearest-even으로
반올림한다. 분자에 2^H를 곱하는 대신 e=M+F-H>=0이면 분모에 2^e를 두고,
e<0이면 분자에 2^-e를 곱할 수 있다. 공통 2 거듭제곱의 정확한 이동이며 반올림
위치를 옮기는 변환이 아니다. 반올림 몫·나머지와 half-even parity는 같아야 한다.

refinement는 기존 START/MAX, 배증 순서, M별 G 공유, 축 순서를 보존해야 한다.
양쪽 끝에서 같은 raw면 반환하고, 양쪽 overflow이며 0을 가로지르면 계속 refine하며,
한쪽 또는 서로 다른 raw이면 계속 refine한다. 같은 단측 overflow는 같은 VMHalt이고,
cap 뒤에는 같은 ReferenceUndecided다. 영 component도 기존 domain 검사 뒤 처리한다.

## 합성과 보존할 상태 계약

raw 준비값은 world/run/step/component 수명에 맞게 새로 계산한다. Run, dt, species,
질량 또는 profile 변경 뒤 다른 준비값을 재사용해서는 안 된다. 실패가 나면 상태,
J_cache와 step counter를 commit하지 않는 기존 계약을 보존한다. 성공 step은
같은 impulse raw, drift raw, exact endpoint, segment/stored-domain 결과 및 상태를
순서대로 얻어야 한다. 기존 endpoint 논증은 integration trajectory equality와 별개다.

## 필요한 반증 검사

각 원시 변환에 scale exponent±1, R² 항 누락, radius upper−1, dt numerator 변조,
분모 재사용 오류, half-even parity 반전, 부호 반전의 실제 잘못된 함수를 적용한다.
원본 REF의 같은 M 끝값 및 독립 Fraction 교차곱/rounding 비교가 이를 거부해야 한다.
128→256→512→1024 및 실제 16384 cap, midpoint 이웃, r_min 인접·먼 거리·overflow,
위조 profile과 stale run binding을 포함한 결과를 나중에 별도 기록한다.
