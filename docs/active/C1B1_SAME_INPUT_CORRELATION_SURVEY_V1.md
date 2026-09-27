# C1-B1 ④-4c-4 — 같은 입력 gap 필터·증명 객체·별도 검사기 v1

**기준 `0bdfa49`, 2026-09-28. 상태: 최소 구현 / survey_only.**
**큰 class의 새 symbolic 하한은 0개**이며, ④-4b `NotCertified`, **11/64 region·gap 84**를 유지한다.
전체 shell lemma·새 인증 region 0, 16384-bit cap·④ 미동결·⑤ 미착수 유지.
[단계 계획](C1B1_SAME_INPUT_CORRELATION_PLAN_V1.md)의 Phase 1과 최소 proof object/checker를 구현했다.
범용 증명 언어·창고·자동 탐색·B 연결은 구현하지 않았다.

## 무엇을 구현했는가

기존 원래 14,271 class 중 미해결 **8,076 class 전체**의 정규화 항등식과 후보 범위를 다시 계산했다.
원래 class의 n=n₀+s·j, j=0..N−1, g와 **m=ceil(M/g)**를 유지한다.

\[
c\,2P'=AV+R,\qquad Q'=BV,\qquad
F_h(j)=(A(j)-chB(j))V(j)+R(j)=c(2P'(j)-hQ'(j)).
\]

R은 전체 Q′ remainder가 아니다. c의 modular 역원과 인수의 서로소성은 가정하지 않는다.
각 식을 **같은 j에서 결합한 뒤** 범위를 계산한다. 지수 물리항 S와 numeric error는 기존 자료와 별도이며 조정하지 않았다.
이 모듈은 유리식 sufficient condition을 검사하며 전체 impulse=P/Q+S의 인증기는 아니다.

### 완전한 홀수 h inventory

작은 정수 gap은 |2P′−hQ′|≤m−1이다. Q′>0인 각 j 부분 구간에서

\[
\frac{2P'-(m-1)}{Q'}\le h\le\frac{2P'+(m-1)}{Q'}
\]

의 정확 Bernstein ratio enclosure를 계산한다. 양수 분모 계수가 증명되지 않으면 미해결이다.
그 범위의 **모든 홀수 정수 h**를 포함하는 first/last/count를 구성한다.
홀수 h가 없으면 해당 j 구간 전체에서 gap≥m이다.
후보가 16개 이하일 때만 각 h의 결합 다항식 F_h를 직접 검사한다.
범위 밖의 h는 ratio lemma로 이미 배제됐으므로 생략에 의한 누락이 아니다.

### 같은 입력 다항식 lemma

1. **Bernstein sign:** F_h 또는 −F_h의 모든 Bernstein 계수가 cm 이상이면 전체 구간에서 gap≥m이다.
2. **Quadratic integer minimum:** 결합한 F_h의 차수가 2 이하일 때만 적용한다.
   볼록 이차식의 정수 최솟값은 끝점과 꼭짓점의 floor/ceil 중에서 얻고,
   오목식·일차식·상수식의 최솟값은 끝점에서 얻는다. 모든 정수 j에 대한 최솟값이 cm 이상이면 배제한다.

이차 lemma는 샘플 최소값을 family 하한으로 승격하는 방식이 아니다.
왜 유한 후보 중에 전체 정수 구간의 최솟값이 반드시 포함되는지를 사용한다.
실제 non-singleton 식은 P′/Q′ 22/29차이고, 홀수 h≠0인 F_h는 29차다.
**실제 식에 이차 lemma를 적용하지 않았다.** 고차식은 별도 lemma가 필요하다.

합성 사례에서는 분리된 h/k 범위가 겹쳐 미해결이던 9입력 class를,
같은 j의 이차식 최솟값으로 **분할·전수 입력 평가 없이** 배제했다.
실제 Ar 식의 새 symbolic 인증과는 구별한다.

## 분할의 한도와 선택

각 class의 root 범위는 모두 검사한다. 추가 분할은 다음에만 적용한다.

- 입력 수 16개 이하인 모든 class: **241개**.
- 각 shell에서 입력 수 최소/최대 및 기준 bit 수 최소/최대인 대표 class.
  중복을 제거하면 **12개**다. 선택은 풀이 전에 기존 inventory에서 결정한다.

따라서 추가 분할 대상은 **253 class**다. 나머지 7,823 class는 root 검사 후 추가 분할을 시도하지 않았다.
한도는 **깊이 4, 노드 31, leaf의 홀수 h 열거 16개**다.
이는 외부 분석 작업 한도이며 64-region 또는 물리 precision cap을 늘리는 것이 아니다.

분할은 [lo,mid]와 [mid+1,hi]로 원래 정수 구간을 정확히 덮는다.
하나라도 미증명인 자식이 있으면 parent class를 하한 후보로 올리지 않는다.
부분적으로 증명된 leaf를 전체 class proof로 포장하지 않는다.
범위 겹침·작업 한도는 실제 입력 존재 또는 precision 실패 증거가 아니다.

## 실제 결과와 한계

모든 root에서 홀수 h inventory가 컸다. shell별 후보 수의 최소〜최대는 다음과 같다.

| shell | root의 홀수 h 후보 수 | 추가 검증된 class | 추가 검증된 입력 | 남은 미해결 class |
|---|---:|---:|---:|---:|
| 18 | 1,384,889〜1,568,498 | 3 | 41 | 578 |
| 17 | 6,814,352〜8,645,949 | 67 | 791 | 1,827 |
| 16 | 36,716,841〜46,892,493 | 78 | 957 | 2,509 |
| 15 | 192,655,889〜250,139,754 | 93 | 1,191 | 2,921 |
| 합계 | — | **241** | **2,980** | **7,835** |

후보 h 수는 같은 입력에서 실제로 가능한 h의 개수가 아니라 class 전체의 느슨한 range inventory다.
이 큰 수를 전부 열거하지 않았다.

새로 검증된 241개는 **모두 9〜16입력 class를 singleton leaf까지 나눈 결과**다.
실제 proof tree에는 split 2,739개와 `odd_range_empty` leaf 2,980개가 있다.
실제 새 proof에 `joint_polynomial_sign` leaf는 0개다.
따라서 이번 실제 추가 하한은 유한 입력의 완전한 덮개와 독립 재검사 성과이며,
**큰 class의 symbolic 같은-j 문제를 해결한 성과는 아니다.**

기존 survey 하한 6,195개와 이번 별도 검사기를 통과한 241개를 합친 class 하한 집계는 **6,436**이다.
남은 **7,835 class**의 존재·비존재는 미판정이다. 실제 작은 gap witness는 0개다.
기존 6,195개의 survey 지위를 이번 checker로 일괄 승격하지 않았다.
전체 shell proof가 없어 기존 coverage compositor에 새 연결을 하지 않았으며 fresh coverage 증가도 없다.

## 최소 proof object와 독립 검사

builder: `a_reference/c1b1_same_input_filter.py`.
checker: `a_reference/c1b1_same_input_checker.py`.
fixture: `a_reference/fixtures/c1b1_same_input_survey_v1.json`.
시험: `tests/test_c1b1_same_input.py`.

proof object는 target shell/class, 이전 fixture hash, normalized class/identity hash,
정확 m·g·M·N, 전체 j 분할 tree, 각 leaf의 모든 홀수 h inventory 및 배제 lemma를 담는다.
builder가 쓰는 `status: candidate`는 인증 권한이 아니다.

checker는 builder·quotient survey·residue survey·modular survey를 import하지 않는다.
기존 frozen component identity(K)와 numeric foundation guard는 공유된 신뢰 기반이다.
checker가 원래 class 데이터를 읽고 별도 Horner 다항식 합성으로 P′/Q′와 V/B/A/R/c를 다시 구성한다.
builder의 Fraction Bernstein helper 대신 **degree!로 정수화한 Bernstein 계수**를 계산한다.
이차 최솟값도 별도 정수 꼭짓점 계산으로 확인한다.

검사 항목은 다음과 같다.

- 외부에서 지정한 target과 proof target 일치.
- 원래 미해결 class·끝점·입력 수·source hash 일치.
- Q′=BV 및 c·2P′=AV+R의 정확 계수 항등식.
- 기준 m=ceil(M/g), 양수 분모, 홀수 h의 완전한 inventory.
- 분할의 누락 0과 각 leaf의 주장된 하한.
- 작업 한도·lemma 차수 전제.

`verify_certificate`의 결과 범위는 **original_class_rational_gap_only**다.
region·전체 impulse·장시간 궤적·현실 정확도·⑤ 인증을 반환하지 않는다.
별도 `verify_witness`도 실제 j·n·홀수 h에서 작은 gap을 재확인하고 더 강한 실패 주장을 거부한다.

## 검증과 구상 일치성

신규 집중 직렬 **38 passed, 9.06초**.
**LOCAL FULL: 2724 passed + 1 strict xfailed, failure/error 0, skip 0, exit 0, 453.76초**.
신규 38개 직렬/병렬 결과가 항목별로 동일하다. 기존 cp949 컴파일러 출력 해독 경고 25건은 남아 있다.
기존 물리·D_valid·인증·직전 survey 관련 39파일은 기준 `0bdfa49`와 LF 바이트가 동일하다.
8,076 원자료 행 해시와 241 proof를 재검사하고, 새 입력 2,980개를 원래 P(n)/Q(n)의 별도 정수 평가로 확인했다.
`raw_verification.json`, `unchanged_contracts.json`, `concept_alignment.json`, `verification_summary.json`에 기록한다.

합성 false overlap, 정수 이차 최솟값, 음의 분자, 비서로소 multiplier,
identity·divisor·remainder·multiplier 변조, source/target/threshold/끝점/자식 누락/홀수 inventory 변조,
고차식의 이차 lemma 위장, 상태 flag를 인증으로 쓰는 결함을 검사한다.
생성기의 sign helper가 거짓 성공을 반환하도록 주입하면 검사기가 출력 오류를 거부한다.
새로 성공한 lemma 때문에 예산 시험의 기존 toy가 더는 예산 부족 사례가 아니게 된 중간 시험도 보존한다.

자동 시험과 별도로 원래 물리·A/B/L 분리·도달 domain·64-region·16384-bit·multi-output·D_valid를 검토했다.
숨은 도달 조건이나 원하는 gap을 강제하는 법칙을 넣지 않았다.
181 probe replay 재실행 또는 새 독립 물리 감사가 아니다.

원자료·증명 객체·검증 기록은 `runs/c1b1_same_input_20260928/`에 보존한다.
분할 한도에서 실패한 대표 class의 부분 성공을 삭제하거나 전체 성공으로 바꾸지 않았다.

## 다음 수학 의무

현재 큰 class에서 단순 j 분할은 홀수 h의 넓은 range를 충분히 줄이지 못한다.
추가 전수/분할 한도를 계속 늘리는 것을 큰 class 해법으로 삼지 않는다.
실제 29차 F_h에서 가변 B(j)와 quotient 합동 조건을 열거 없이 유지하는 고차식 lemma,
또는 다른 분모 인수의 remainder와 결합하는 방식이 필요하다.
proof object/checker 최소 기반은 그 lemma의 실제 전제를 재검사하는 데 사용할 수 있지만,
이번 최소 기반 자체가 미해결 수학을 대신하지 않는다.
