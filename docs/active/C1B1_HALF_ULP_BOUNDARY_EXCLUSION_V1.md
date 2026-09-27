# C1-B1 half-ulp boundary 역상 배제 v1

**④-4b 전체는 NotCertified다.** 이번 단계는 `d59b565`의 남은 큰 domain 27개에서
경계 중심 증명이 실제로 압축되는지 확인한다. 물리·181 Frozen D_valid·기존 증명은 그대로다.
새 모듈은 `a_reference/c1b1_half_ulp_boundaries.py`, exact 기록은
`a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json`이다.

## 계약과 검사

n은 relative position raw 정수, I(n)은 impulse의 UP 단위 값이다.
기존 해석적 도함수 bound로 domain 전체의 `dI/dn>0`을 재검증한다.
끝점의 **정확한 값을 포함하는 구간**을 저장한다. irrational I를 유리수 하나로 대체하지 않는다.
physical point enclosure는 동결 `_model`의 512-bit V′ interval과 축의 정확한 q/R 부호를 사용한다.
이는 역상 증명의 물리값 bound이며 실행기의 impulse 계산을 교체하지 않는다.

공통 실행기 endpoint 오차를 E라 한다. 여유 있는 양수 margin을 얻기 위해 금지 반경은 **F=2E**로 둔다.
I(lo)의 enclosure [l0,u0], I(hi)의 [l1,u1]에서 포함될 수 있는 half-ulp index는
`ceil(l0−F−1/2) ≤ k ≤ floor(u1+F−1/2)`다.
안쪽 endpoint bound u0,l1로도 같은 index 끝점이 나와야 **정확한 경계 개수**로 인정한다.
그렇지 않으면 NotCertified다. 출력 span도 `[l1−u0,u1−l0]`로 저장한다.

각 `h=k+1/2`의 두 threshold h−F, h+F의 inverse를 정확한 유리수 이분법으로 둘러싼다.
physical point interval이 threshold를 포함하면 임의 방향으로 이동하지 않고 현재 bracket을 보존한다.
domain 밖의 root는 닫힌 domain 끝점으로 clip한다. 최종 금지 역상은
`[lower_inverse.left, upper_inverse.right]`의 보수 구간이며,
그 안의 정수는 `ceil(left)…floor(right)`다. 경계에 있는 정수도 포함한다.

checker는 이분법 탐색 경로를 신뢰하지 않는다. 최종 bracket의 물리값 부등식을 다시 확인한다:
domain 시작점이 아닌 lower endpoint L에는 `I(L).upper ≤ h−F`,
domain 끝점이 아닌 upper endpoint U에는 `I(U).lower ≥ h+F`가 필요하다.
엄격 증가성 때문에 n<L 또는 n>U인 모든 입력은 금지 영역 밖이다.
역상 안의 정수는 빠짐없이 직접 인증한다. 후보의 margin은 E보다 커야 한다.
필요하면 공통 precision과 후보 precision을 기존 schedule 안에서 16384까지 올린다.
전체 margin 하한은 `min(2E, 직접 인증한 후보들의 margin 하한)`으로 구성한다.
정확한 tie는 half-even 의미가 정의돼 있어도 이 strict-separation 인증에서 거부한다.

boundary certificate 검사에는 **외부 coverage 의무가 요구한 domain**을 따로 전달한다.
인증서가 domain을 스스로 축소해 전체 의무를 만족했다고 주장할 수 없다.
half-ulp index 하나, 후보 정수 하나라도 빠지면 거부한다.
새 coverage compositor는 기존 인증서와 새 인증서를 검사한 뒤 fresh shell geometry 전체와 비교한다.
빠진 구간이 있으면 성공으로 승격하지 않는다.

## 작업 한도와 증명 범위

- 기존 region budget **64 유지**, 이번 예시의 조합은 **6/64 region**이다.
- 별도의 경계 열거 작업 한도 **domain당 64**, 후보 정수 작업 한도 **64**를 둔다.
- inverse 이분법은 최대 64회, 목표 bracket 폭은 raw 단위 1/8이다.
- 경계 개수가 64를 넘으면 **열거하기 전에** family 증명 대상으로 기록한다.

이 작업 한도는 물리·실행기 precision 제한이 아니다. 249개 경계도 이번 한도 밖이지만
개별 열거가 원리적으로 불가능하다는 증거는 아니다. 큰 family에는 후보 수를 0으로 기록하지 않고
`null`(미열거)로 남긴다. 작업 한도·512-bit 역상 enclosure 실패도 실제 ReferenceUndecided 반례로 바꾸지 않는다.
공통·후보 precision까지 16384에서 분리하지 못하면 그 미증명 사유를 그대로 반환한다.

## 27개 domain의 압축 결과

아래 경계 수는 F=2E의 금지 band가 exact output range와 교차하는 **확정된 정수 개수**다.
입력 개수는 선언된 보수 격자 domain의 개수이며 실제 방문 점 수가 아니다.
I_min/I_max와 ulp span의 exact fraction enclosure는 fixture에 전부 보존한다.

| shell | domain 격자점 수 | half-ulp 경계 수 | 후보 정수 수 |
|---|---:|---:|---:|
| 0 | 1,407,993,111,016,412 | 6,304,880,043,134,911,522 | 미열거 |
| 1 | 1,759,836,831,904,741 | 1,275,836,578,970,861,015 | 미열거 |
| 2 | 2,199,641,483,015,141 | 261,469,731,581,708,160 | 미열거 |
| 3 | 2,749,397,296,903,141 | 53,965,208,610,120,830 | 미열거 |
| 4 | 3,436,592,064,263,141 | 11,178,362,272,975,953 | 미열거 |
| 5 | 4,295,585,523,463,141 | 2,318,465,154,091,740 | 미열거 |
| 6 | 5,369,327,347,463,141 | 480,622,934,703,578 | 미열거 |
| 7 | 6,711,504,627,463,141 | 99,428,165,869,040 | 미열거 |
| 8 | 8,389,226,227,463,141 | 20,494,702,562,076 | 미열거 |
| 9 | 10,486,378,227,463,141 | 4,202,193,470,594 | 미열거 |
| 10 | 13,107,818,227,463,141 | 855,468,986,467 | 미열거 |
| 11 | 16,384,618,227,463,141 | 172,556,911,090 | 미열거 |
| 12 | 20,480,618,227,463,141 | 34,412,627,968 | 미열거 |
| 13 | 25,600,618,227,463,141 | 6,770,975,915 | 미열거 |
| 14 | 32,000,618,227,463,141 | 1,312,115,504 | 미열거 |
| 15 | 40,000,618,227,463,141 | 250,139,754 | 미열거 |
| 16 | 50,000,618,227,463,141 | 46,892,493 | 미열거 |
| 17 | 62,500,618,227,463,141 | 8,645,949 | 미열거 |
| 18 | 78,125,618,227,463,141 | 1,568,498 | 미열거 |
| 19 | 97,656,868,227,463,141 | 280,063 | 미열거 |
| 20 | 122,070,930,727,463,141 | 49,245 | 미열거 |
| 21 | 152,588,508,852,463,141 | 8,541 | 미열거 |
| 22 | 190,735,481,508,713,141 | 1,465 | 미열거 |
| 23 | 238,419,197,329,025,641 | 249 | 미열거 |
| 24 | 298,023,842,104,416,266 | 42 | 2 |
| 25 | 372,529,648,073,654,547 | 8 | 0 |
| 26 | 465,661,905,535,202,398 | 1 | 1 |

shell 24〜26은 **51개 경계 → 보수 후보 정수 3개 → 직접 인증 3개**로 닫혔다.
48개 경계는 inverse outer interval 안에 정수가 없다. 후보는 실제로 금지 band에 있다는 주장이 아니다.
보수 bracket에 포함된 후보 3개도 공통 256-bit 오차보다 큰 margin을 확보했다.
따라서 이 세 **domain 전체가 Certified**이며 10^18급 입력 전수검사가 아니다.
기존 3개 region과 조합한 fresh coverage는 gap **92→89**, region **3→6**이다.
shell 24〜27의 미피복은 없지만 **24개 큰 domain이 남아 전체 NotCertified**다.

실제 PES는 rational retardation·inverse powers와 exponential Laurent 항의 합이다.
전체 impulse를 단순한 P(n)/Q(n)이라고 놓고 parity만 적용하지 않는다.
다음 family 증명은 실제 식의 rational 부분과 exponential 잔여항을 함께 제한해야 한다.
이번에는 symbolic/modular family 증명을 구현하지 않았다. ④ 최종 동결·⑤·E_min·전체 산란각은 보류한다.

## 검증

direction 반전, error 축소, half-ulp index 누락, inverse endpoint 조작, 후보 누락,
domain 축소, precision 변조를 거부한다. 실제 경계 바로 양옆 synthetic 입력,
정확한 tie, 16384-bit 미분리 synthetic 입력을 별도로 시험한다.
Synthetic 결과를 Lang 물리나 실제 도달가능 반례로 해석하지 않는다.
재전개한 기존 포텐셜 미분과 inverse용 point enclosure 대조,
부호 반사, 후보/경계 작업 한도, coverage gap 보존, 궤적·D_valid 접근 금지도 확인한다.
최대 판정 정밀도는 domain 공통 precision과 후보 precision을 모두 포함해야 한다.
이 최대값을 작게 바꾸는 변조도 거부하며 후보 3개의 실제 실행기 output과 인증서 output을 대조했다.
신규 직렬 시험 **31 passed, 26.86초**. 최종 **LOCAL FULL: 2502 passed + 1 strict xfailed,
skip 0 / 실패·error 0 / exit 0 / 405.59초**. 신규 31개는 직렬/병렬 결과가 항목별로 동일하다.
컴파일러 출력 cp949 해독 경고 27건은 남아 있다. 관련 기존 소스/fixture 19개가 `d59b565`와 LF 바이트 동일하다.
증거는 `runs/c1b1_boundary_exclusion_20260927/`의 `local_full_final.log`, `local_full_final.xml`,
`focused_final.xml`, `verification_summary.json`, `unchanged_contracts.json`에 보존한다.
최대 precision 검사 보강 전의 2501 passed 실행은 `local_full.log/xml`에 별도로 보존했다.
시험 통과와 domain 3개의 인증을 전체 ④-4b 완료로 해석하지 않는다.
