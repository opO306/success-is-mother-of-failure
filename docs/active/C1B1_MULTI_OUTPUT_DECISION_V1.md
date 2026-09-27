# C1-B1: 서로 다른 output을 허용하는 rounding 결정성 계약 v1

④-4b 전체 상태는 **NotCertified**다. 이 계약은 기존 constant-output cover를 보존하고,
그보다 약한 본래 의무인 **각 허용 입력의 유한 precision 결정성**을 표현한다.
64-region 한도, 128→256→…→16384-bit 실행기 schedule, 물리·181 Frozen D_valid를 바꾸지 않는다.

## 입력 집합과 승격 조건

인증서에는 입력 집합 자체를 기록한다. `finite_points`는 명시한 상대 위치 raw tuple 전부이며,
`axis_lattice_interval`은 한 좌표축의 닫힌 정수 구간 전부다. 후자는 보수 projection이지
실제 궤적에서 방문한 점의 목록이 아니다. 두 형식 모두 FX(96,48) 상대 위치와 FX(96,80)
impulse, Δt=40, frozen retardation ON만 대상으로 한다.

region 하나 안의 raw impulse는 달라도 된다. 같은 schedule precision p에서 각 성분의 정확한
impulse I를 포함하는 enclosure [l,u]를 얻고, 출력 raw n에 대해
`(n−1/2) UP < l ≤ I ≤ u < (n+1/2) UP`를 증명한다.
공통 margin δ는 모든 성분·입력의 양쪽 margin 하한의 최솟값이다.
공통 endpoint error ε는 각 enclosure 폭의 최댓값으로 충분하며, **0≤ε<δ**를 요구한다.
이 경우 p까지 실행기가 결정한다. 정확한 tie 자체는 half-even 물리가 정의되지 않는다는
뜻이 아니다. 이 strict-separation 증명 방법이 tie를 인증하지 못하는 것이다.

명시 유한 집합 증명은 그 모든 점을 평가한다. 65점이 한 region에서 인증될 수 있어도
수조 개 점을 포괄하는 하나의 해석적 증명을 얻었다고 표현하지 않는다.
전체 coverage 검사는 fresh outgoing geometry의 각 shell 축 격자 구간 전체를 인증된 domain으로
덮었는지 별도로 확인한다. 점 목록에 없는 구간을 보간하지 않는다. region 수는 64 이하다.
coverage가 완전해지고 tail 의무도 닫힌 경우에만 해당 **초기 상태의 outgoing kick coverage**를
Certified로 반환할 수 있다. 다른 초기 상태 계열, inbound, global scattering으로 승격하지 않는다.

## 해석적 축 증명

축 입력이면 R=|q|이고 축 impulse는 `J=−sign(q)·20·V′(R)`다.
포텐셜을 다음의 정확한 항으로 다시 쓴다:

- retardation rational 항 `−c N(R)/(R^6 D(R))`, D의 모든 계수 양수;
- inverse Laurent 다항식;
- `exp(−λR)` × Laurent 다항식.

rational 항의 n차 미분을 `P_n/(R^(6+n) D^(1+n))`로 쓰면
`P_(n+1)=RD P_n′−[(6+n)D+(1+n)RD′]P_n`이다.
다음 numerator의 계수가 모두 같은 부호면 현재 항의 단조성을 구간 전체에서 증명한다.
그때 끝점 bound를 사용한다. 나머지는 512-bit outward interval 연산으로 포함한다.
exp Laurent 미분은 `(d/dR−λ)^n P`다. subdivision·궤적 sampling은 하지 않는다.

물리 값의 구간 변화와 **한 고정 입력에서 계산기 endpoint가 정확값에서 벗어나는 오차**는
별도로 계산한다. 수치 오차 전파는 동결 실행기의 `_model_R` 연산 순서를 따른다.
각 연산의 directed rounding에 2^-p를 추가하고, 양수 denominator는 오차를 제외한 하한을 사용한다.
축 격자는 p≥128에서 sqrt(q²)가 dyadic으로 정확하다. 임의 3D 입력에 이 오차 증명을 쓰지 않는다.

EXP에는 |y|≤2^-8의 Taylor enclosure를 쓴다. term 폭은 2 ulp 이하,
`N=ceil(p/8)+1`번 안에 t_hi≤1, remainder 폭은 8 ulp 이하다.
argument reduction endpoint 오차 1 ulp를 포함한 시작 endpoint 오차는 `(2N+9)2^-p` 이하다.
nonnegative x에 대한 exp(−x)의 정확값은 [0,1]에 있다. squaring의 오차 전파를 4배와
directed rounding 1 ulp로 제한하면 `4^k(2N+10)2^-p`가 충분하다.
이 bound가 1 미만일 때만 [0,2] squaring 귀납을 사용한다. exp 입력 자체의 오차는
nonnegative 범위의 1-Lipschitz 성질로 더한다. 실행기/EXP 소스 및 live 함수 변경은 거부한다.

단조성과 인접 impulse separation은 **반올림 경계와의 margin이 아니다**.
`I_k=k UP+UP/2+2^-20000`은 단조이고 인접 차이가 UP여도 margin은 2^-20000이다.
따라서 29개 그룹의 부호·단조성을 증명하더라도 margin 의무가 남으면 NotCertified를 유지한다.
반사 q→−q는 impulse 부호와 half-even output을 반전하고 같은 margin/error를 보존한다.
이를 실제 양수 projection의 coverage를 생략하는 이유로 쓰지 않는다.

## 수용 기준과 한계

65개 서로 다른 output은 하나의 `finite_points` 인증서, 하나의 공통 p/ε/δ로 통과해야 한다.
마지막 특이 구간은 내부 부호, 극값/zero crossing 여부, 격자점 수를 별도로 조사하고
가능하면 구간 전체를 해석적으로 인증한다. 실제 방문 점 수는 별도 reachability 증거 없이는 모른다.
모든 해석적 inequality는 exact rational로 저장하며 화면용 소수는 판정에 쓰지 않는다.
독립 checker는 domain·enclosure·margin·error·coverage를 검사한다. PES/EXP 구현 전체의
독립 재증명은 아니다. frozen source guard와 기존 C1-A 감사·시험에 의존한다.

16384-bit 한도에 도달한 **증명 실패**를 실제 실행기의 ReferenceUndecided 반례로 바꾸지 않는다.
④ 최종 동결·⑤·E_min·전체 산란각은 전체 증명과 후속 감사 전까지 보류한다.

## 2026-09-27 구현 결과

기준 진단은 `6184700`의 76개 기록·29개 그룹을 그대로 읽는다.
`a_reference/c1b1_rounding_regions.py`는 domain을 포함하는 인증서와 별도의 coverage checker,
`c1b1_axis_decision_bounds.py`는 정확한 포텐셜 재전개와 수치 endpoint 오차 증명을 구현한다.
모든 fraction과 29개 그룹의 결과는 `fixtures/c1b1_rounding_regions_v1.json`에 기록했다.

| 대상 | 결과 | 증명 범위 |
|---|---|---|
| 서로 다른 output 65개 | **한 region, 공통 p=256로 Certified** | 명시한 65개 입력 전부를 평가한 유한 집합. 큰 연속/격자 구간 인증 아님 |
| singleton raw x=5629499534213128 | **p=128 Certified** | 그 점 하나 |
| 마지막 특이 구간 | **구간 전체 p=256 Certified** | 선언된 축 격자점 553,997,943,205,884,291개. 분할·sampling 불필요 |
| 29개 그룹의 단조성 | **전부 엄격 증가** | V′>0, V″<0, 인접 격자 impulse 차이의 양수 하한 |
| 나머지 27개 그룹 | **NotCertified** | 수치 오차 상한은 확보. 격자점 전체의 rounding-boundary margin 미증명 |
| R=20 outgoing coverage | **NotCertified** | 사용 region 3/64, 정확한 미피복 격자 구간 92개 |

화면용 근삿값(판정에는 exact fraction 사용): 65점의 공통 margin 하한은
0.00186078921895 UP, enclosure endpoint error 상한은 3.02025782114×10^-41 UP다.
128-bit 공통 enclosure는 이 집합에서 미분리여서 거부한다. 256은 기존 실행기 schedule 안이다.

마지막 그룹의 raw 구간은 `[2328306436538696290, 2882304379744580580]`이다.
정확한 물리 impulse 범위는 대략 `[-0.245999686, -0.044996089] UP`에 포함된다.
구간 전체 V′>0, V″<0이므로 impulse는 음수이고 엄격히 증가한다.
내부 극값·zero crossing은 없고, margin 하한은 약 0.254000314 UP,
256-bit endpoint error 상한은 약 6.12854431855×10^-21 UP다.
양 끝의 raw=0만 보고 결론내린 것이 아니다. 실제 궤적이 방문한 점의 수는 여전히 모른다.
impulse의 볼록성은 별도 조사에서 아직 증명되지 않았다. 기존 Jet3의 V‴ 구간은
대략 `[-8.074×10^-22, 6.064×10^-25]`로 양쪽 부호를 포함한다.
이는 V‴의 실제 부호가 바뀐다는 증거가 아니라 해당 enclosure의 미분리다.
`runs/c1b1_multi_output_20260927/convexity_supplement.json`에 exact bound를 보존했다.
현재 region 인증에는 이미 확보한 impulse 부호·단조성·margin/error만 필요하다.

92개 gap은 원래 76개 미해결 기록과 **다른 집계**다. 새 coverage checker가 65개 유한 점과
singleton, 마지막 전체 구간을 전체 shell domain에서 빼고 남긴 정확한 정수 구간 수다.
이를 92개 새 cell로 나눠 탐색하지 않았다. region 예산은 64로 유지했다.

반사 증명은 축·부호를 바꾼 마지막 구간에 대해 같은 error/margin을 재사용하는 시험으로 확인했다.
실제 예시 projection은 양수 축이므로 대칭을 이유로 입력을 삭제하지 않는다.
동결 PES·실행기·기존 constant-output 인증기·reachable geometry·181 D_valid에 변경이 없다.

**다음 수학 의무:** 서로 다른 output을 갖는 27개 큰 격자 domain에 대해
각 입력의 half-ulp boundary margin 하한을 얻고, 이미 구한 공통 endpoint error와 결합한다.
연속 함수는 서로 다른 rounding 영역 사이에서 경계를 지나므로 연속 구간의 공통 양수 margin을
그대로 요구할 수 없다. 이 단계는 격자 phase/경계 분리 증명이어야 한다.
단조성을 margin으로 대체하거나 65점의 성공을 수조 개 입력에 보간하지 않는다.

신규 시험은 41개다. 실제 실행기 출력 대조, 기존 Jet 미분 대조, polynomial 항 누락 검출,
endpoint zero-error 변조 검출, domain/result/margin/error 변조 거부, tie 거부, 예산·schedule 고정,
coverage gap 보존, 궤적·D_valid·subdivision 접근 금지, exact fixture 재현을 검사한다.
신규 직렬 시험 실행: **41 passed, 22.82초**.
**LOCAL FULL: 2471 passed + 1 strict xfailed / skip 0 / 실패·error 0 / exit 0 / 359.84초**.
신규 41개 시험은 직렬/병렬 결과가 항목별로 같다. 컴파일러 cp949 출력 해독 경고 26건은 남아 있다.
관련 물리·동결·기존 증명 소스/fixture 16개가 `6184700`과 LF 바이트 동일함을 확인했다.
로그·JUnit·결과 요약·파일 동일성 증거는 `runs/c1b1_multi_output_20260927/`에 보존했다.
전체 시험의 통과는 27개 격자 margin 미증명을 해소하거나 ④-4b를 승격하지 않는다.
