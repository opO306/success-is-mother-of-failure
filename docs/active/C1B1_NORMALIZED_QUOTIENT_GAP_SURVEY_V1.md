# ④-4c-3 — 정규화 gap·가변 divisor·quotient 조건 조사 v1

**기준 `875aa31`, 2026-09-28. 상태: survey_only.**
새 shell 전체 lemma·인증 region은 0개다. **④-4b NotCertified, 11/64 region, gap 84**를 유지한다.
④ 전체 동결·⑤·E_min·전체 산란각은 보류한다.

## 정확한 목표와 교정

기존 [점별 조사](C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md)의 `nearest_half`도 이미
`abs((2P mod 2Q)-Q)`를 계산하며, [class 조사](C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md)도 홀수 h를 포함한다.
이번 목표는 홀수 조건을 새로 넣는 것이 아니라 **전체 class의 하한**을 조사하는 것이다.

class 전체에서 증명된 상수 공통 인수 g>0를 사용해 P=gP′, Q=gQ′로 놓으면

\[
m=\left\lceil\frac{M}{g}\right\rceil,\qquad
\forall j\in[0,N-1]\cap\mathbb Z:\quad
\left|(2P'(j)\bmod 2Q'(j))-Q'(j)\right|\ge m.
\]

원래 M을 정규화 gap에 그대로 적용하지 않는다. g는 기존 class의 **증명된 2/5 공통 인수**이며,
모든 점의 최대 gcd라는 주장은 하지 않는다. 추가 odd gcd를 임의로 제거하지 않는다.
shell 18부터 조사하지만 약분 전 M의 220-bit 크기만으로 가장 쉽다고 판정하지 않는다.

기존 remainder는 전체 Q에 대한 remainder가 아니라 `c₀·2P=A₀·D_int²+R₀`다.
이를 그대로 보존하고, class에서 n=n₀+s·j, D_int=H·D_normalized를 대입한다.

\[
c_0g\,2P'=H^2A_0(n_0+sj)D_{\rm normalized}^2+R_0(n_0+sj).
\]

이 항등식의 모든 정수 계수와 multiplier에 공통인 양의 상수만 추가로 나눠
`c·2P′=A·V+R`, `V=D_normalized²`를 얻는다. 이 추가 나눗셈은 항등식의 scalar 정리이며,
P′/Q′의 정의와 m을 다시 바꾸는 약분이 아니다. 별도로 `Q′=B·V`를 계수별로 검사한다.
기존 자료의 R을 전체 Q′ remainder로 바꾸거나 c의 modular 역원을 가정하지 않는다.

non-singleton에서 P′ 22차·Q′ 29차를 검사한다. 상수 약분과 선형 치환은 차수를 낮추지 않는다.
따라서 전체 Q′로 다항식 나눗셈을 하면 quotient 0, remainder 2P′이며 새로운 단순화가 없다.
V로 나눈 낮은 차수의 R과 **나머지 분모 인수 B 및 홀수 quotient**를 함께 조사한다.

## 이번에 사용한 충분조건

z=2P′−hQ′, h 홀수이면 같은 j에서

\[
cz=(A-chB)V+R,\qquad k=A-chB,\qquad
k\equiv A-cB\pmod{2cB}.
\]

R의 부호·크기만으로 gap을 판정하지 않는다. 예를 들어 c=1, B=1, R=0에서
A가 홀수이면 gap=0, A가 짝수이면 최소 gap=Q′다.

작은 정수 gap은 `|z|<m`, 즉 `|z|≤m−1`이다. 그러려면

\[
\frac{2P'-(m-1)}{Q'}\le h\le\frac{2P'+(m-1)}{Q'},\qquad
\frac{-R-c(m-1)}{V}\le k\le\frac{-R+c(m-1)}{V}
\]

가 같은 입력에서 성립해야 한다. 각 ratio를 **정확 유리수 Bernstein enclosure**로 감싼다.
분자·분모를 같은 차수로 올렸을 때 분모의 모든 Bernstein 계수가 양수이면,
ratio는 계수별 분자/분모 비율의 양의 가중 평균이므로 그 최소·최대 사이에 있다.
양수를 증명하지 못하면 `unresolved`이며 부호를 추정하지 않는다.

quotient의 가변 합동식에서 class 전체에 성립하는 고정 coset을 유도한다.
C=A−cB라고 쓰고, `2cB`의 모든 계수와 C의 상수항 이외 모든 계수의 gcd를 L이라 하면
**k≡C(0) mod L**이 모든 정수 j와 홀수 h에 성립한다. c를 역원으로 소거하지 않는다.
먼저 h 범위의 홀수 정수 개수, 이어 k 범위의 이 coset 정수 개수를 계산한다.
어느 하나가 0이면 전체 class에서 gap≥m이다.

이는 원래 같은-j 조건의 **필요조건을 완화한 검사**다. interval 범위와 고정 coset이 겹쳐도
하나의 j에서 모두 실현된다고 증명한 것이 아니다. 후보 h/k를 열거하거나 그 후보를 실제 입력으로 바꾸지 않는다.
한 class마다 전체 parameter 구간 하나를 사용했으며, 분석 subdivision을 인증 region으로 세지 않는다.

## 실제 결과

원래 shell 15〜18의 **14,271 class·230,627,472,909,852,564 격자 입력**을 모두 유지했다.
기존 class 하한 5,541개를 보존하고, 미해결 class 중 입력이 8개 이하인 class는 전체 허용 입력을 정확 계산했다.
큰 class에 표본을 추가하지 않았다. 작은 class 전수 계산은 전체 shell 전수 계산과 구별한다.
추가 전수 계산은 **2,680개 입력**이며 별도 raw P/Q 정수 평가와 가까운 홀수 h 탐색으로 다시 확인했다.
class별 정규화 기준의 bit 범위는 shell 18/17/16/15 각각 **1〜220 / 1〜549 / 1〜810 / 1〜1018**이다.
이 범위도 정규화 Q′ 및 quotient/remainder 구조를 대신하는 난이도 순위가 아니다.

| shell | 전체 class | 기존 하한 | 작은 class 전수로 추가 하한 | 남은 미해결 |
|---|---:|---:|---:|---:|
| 18 | 2,972 | 2,381 | 10 | 581 |
| 17 | 3,604 | 1,539 | 171 | 1,894 |
| 16 | 3,782 | 980 | 215 | 2,587 |
| 15 | 3,913 | 641 | 258 | 3,014 |
| 합계 | 14,271 | 5,541 | 654 | 8,076 |

**큰 class의 interval/coset 검사로 얻은 새 하한은 0개**다.
겹치는 후보 개수는 실제 입력 개수가 아니다. 미해결 8,076개는 존재·비존재 미판정이다.
작은 class의 실제 작은 gap 반례는 0개이며 non-singleton 전체에서 없다는 주장은 하지 않는다.
전체 shell 하한이 없으므로 새 independent lemma checker나 coverage 연결도 만들지 않았다.

결과에는 세 상태를 구분한다.

1. `whole_class_lower_bound`: class 전체 하한. 기존 하한 또는 작은 class 전수, 향후 독립 checker 대상.
2. `actual_small_gap_input`: 실제 n·j·홀수 h·정수 P′/Q′로 재확인한 해당 sufficient condition의 반례.
3. `unresolved`: 느슨한 조건에 후보가 남거나 positivity 증거가 없는 상태. 실제 입력 존재 주장이 아니다.

실제 작은 **유리식 gap**도 전체 impulse=P/Q+S의 반올림 실패나 16384-bit 초과를 증명하지 않는다.
S는 실제 지수 물리항이며 수치오차와 다르다. 원래 signed residual 및 numeric error의 provenance는
이전 자료에 그대로 남겼으며 이번에 값을 재조정하지 않았다. 좌표 이동만으로 증거가 강화되지 않는다.
하나의 region에서 다른 output을 허용하는 기존 계약도 유지한다.
여러 입력을 합친 bound가 경계와 겹치면 현재 bound로 미인증이라는 뜻이다.

## 구현과 검증 경계

구현 `a_reference/c1b1_quotient_gap_survey.py`, fixture
`a_reference/fixtures/c1b1_quotient_gap_survey_v1.json`, 시험 `tests/test_c1b1_quotient_gap_survey.py`.
fixture는 모든 class의 정규화 threshold·판정·하한·입력 수·상세 행 hash를 보존한다.
정확 ratio 범위와 quotient coset은 `runs/c1b1_quotient_gap_20260928/raw_classes_final.jsonl`에 보존한다.
fixture의 상태별 대표 예시는 전체 계수 항등식으로 재구성해 검사한다.
이번 모듈은 기존 class 자료와 모든 앞선 fixture/source 연결을 확인하며 기존 checker는 이 모듈을 import하지 않는다.

정규화 threshold의 올림, 음의 분자, 양수 분모 증명, 전체 작은 입력/홀수 quotient 독립 전수,
R=0에서 홀수/짝수 quotient, 분모 cofactor, c와 modulus가 비서로소인 사례를 검사한다.
항등식·multiplier·분모·class hash·inventory·이전 fixture 변조를 거부한다.
홀수 quotient coset을 전체 정수로 잘못 바꾸는 결함은 출력 판정을 바꾸며 해당 시험이 이를 감지한다.
느슨한 bound가 겹치지만 실제 정수 입력에는 tie가 없는 예도 포함한다.

자동 시험과 별도로 구상 경계를 검토했다. 실제 물리·동결 D_valid·실행 cap·원래 domain·기존 인증을 보존한다.
새 물리 규칙·숨은 도달가능 조건·원하는 gap을 강제하는 조건을 추가하지 않았다.
전체 impulse·장시간 궤적·181 probe replay를 새로 검증한 결과가 아니다.
기존 물리·D_valid·checker·이전 조사·fixture·시험 **36개 파일**을 기준 commit과 LF 바이트 비교해 보존했다.
공통 상수/기존 numeric error/EXP 기반을 재사용하므로 새 독립 물리 감사로도 해석하지 않는다.

집중 시험 및 LOCAL FULL의 실제 결과는 아래 실행 기록과 `verification_summary.json`에 기록한다.
신규 집중 직렬 **34 passed, 1.38초**.
**LOCAL FULL: 2686 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 433.59초**.
신규 34개 직렬/병렬 결과는 항목별로 동일하다. cp949 컴파일러 출력 해독 경고 25건은 남았다.
로그/JUnit·exit code와 전체 대조는 `runs/c1b1_quotient_gap_20260928/verification_summary.json`을 본다.
첫 fixture 실행의 구형 parent hash 형식 처리 오류와 집중 시험의 부적절한 toy 사례 실패는 보존하며 최종 검증과 구별한다.
중간 시도의 원인과 보존 경로는 `runs/c1b1_quotient_gap_20260928/attempt_notes.json`에 있다.

## 다음 의무

큰 class에서 Bernstein ratio 범위와 고정 coefficient coset을 합친 제약만으로는 작은 gap을 배제하지 못했다.
다음은 가변 B(j)와 quotient 조건의 같은-j 상관관계를 더 보존하거나,
다른 분모 인수와 낮은 차수 remainder를 함께 쓰는 lemma다.
단순히 고정 modulus를 확대하거나 작은 remainder만 관측하는 것으로 이 의무를 대체하지 않는다.
shell 0〜14의 다른 문제는 계속 별도이며 새 shell 하한과 독립 checker가 나오기 전까지 현재 인증 판정을 유지한다.
