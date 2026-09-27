# ④-4c-2 — shell 15〜18 full residue-class lemma survey v1

**기준 `23144df`, 2026-09-28. survey_only.**
합동류 덮개는 원래 네 domain의 모든 격자점을 포함한다. 하지만 **full variable-modulus의 작은 Δ 배제는 미완료**다.
새 shell 전체 lemma 후보 0, 실제 작은 Δ 입력의 반례 0, 새 인증 region 0이다.
기존 checker·coverage **11/64 region·gap 84·④-4b NotCertified**를 유지한다.
④ 동결·⑤·E_min·전체 산란각은 보류한다. shell 0〜14의 조사/인증 논리는 변경하지 않았다.

## 결과를 먼저 읽기

| shell | 처음 valuation/unit class | 최종 분석 class | 필요한 하한 확인 class | 미해결 class | 전체 고정 2/5 조건만으로 부족함을 확인한 미해결 class |
|---|---:|---:|---:|---:|---:|
| 15 | 2,600 | 3,913 | 641 | 3,272 | 2,659 |
| 16 | 2,631 | 3,782 | 980 | 2,802 | 1,619 |
| 17 | 2,662 | 3,604 | 1,539 | 2,065 | 860 |
| 18 | 2,692 | 2,972 | 2,381 | 591 | 232 |
| 합계 | 10,585 | **14,271** | **5,541** | **8,730** | **5,370** |

분석 class는 인증 region이 아니다. 64-region 예산과 합치거나 비교하지 않는다.
전체 원래 격자점 **230,627,472,909,852,564개**를 중복 없이 덮는다.
그중 현재 하한 조건을 확인한 부분집합의 점 수는 **404,470,754,219,196개**다.
이 부분집합도 새 독립 lemma checker/coverage에 연결하지 않았으므로 인증 region 수는 늘지 않는다.

| shell | 하한 조건 확인 부분집합 점 수 | 미해결 부분집합 점 수 |
|---|---:|---:|
| 15 | 1,202,215 | 40,000,618,226,260,926 |
| 16 | 246,766,509 | 50,000,617,980,696,632 |
| 17 | 157,930,224,416 | 62,500,460,297,238,725 |
| 18 | 404,312,576,026,056 | 77,721,305,651,437,085 |

전수로 끝난 것은 **valuation/unit partition과 선택한 고정 congruence period의 검사**다.
`u^17`·`D_normalized(u)^2`의 가변 modulus에 대한 전수 feasibility 검사를 끝냈다는 뜻은 아니다.
모든 미해결 class에 이 잔여 의무를 명시했다. 실제 full Δ가 작다고 주장하지 않는다.

## 원래 domain을 빠짐없이 분류하는 방법

양의 정수 n은 유일하게

\[
n=2^a5^b u,\qquad\gcd(u,10)=1
\]

로 표현된다. 각 (a,b)에 대해 u의 닫힌 정수 범위를 원래 [lo,hi]에서 직접 계산하고,
u mod 10∈{1,3,7,9}를 전부 포함한다. 각 progression의 첫 점·마지막 점·개수는 정수 나눗셈으로 구한다.
합계가 hi−lo+1인지 검사하고, 시험에서는 같은 valuation을 가진 leaf들의 CRT 교차가 실제 구간 안에서
존재하지 않는지 별도로 확인했다. valuation이 다르면 원래 n도 겹칠 수 없다.

P와 D의 항별 p-adic order 최소값이 유일하면 모든 unit u에서 valuation이 정확히 결정된다.
최소 항이 충돌하면 **공통 p 인수를 먼저 제거한 다항식**을 unit residue에서 평가한다.
나머지가 0이 아니면 정확 valuation이고, 0이면 그 자리수 이상의 하한일 뿐이다.
0을 정확 valuation이나 tie로 읽지 않는다.

미해결 정규화 residue만 radix refinement한다. unit digit 작업 한도는 2-adic 8자리·5-adic 4자리이며
한도 뒤에도 전체 class는 유지하되 미결정 valuation을 하한으로 표시한다.
이미 필요한 Δ 하한을 만족하면 불필요한 추가 refinement를 하지 않는다.
class가 한 점이면 그 **class의 전체 허용 입력 하나**를 정확 계산한다.
이런 singleton class는 총 **1,005개**이고 모두 필요한 rational Δ 조건을 만족했다.
이는 추가 표본 추출이 아니며, 실제 궤적이나 물리 point API의 새 인증도 아니다.

원래 domain은 줄이지 않는다. 작은 modulus가 허용하는 모든 lift를 포함한다.
분석 leaf 작업 한도 10,000/domain을 넘기면 incomplete를 성공으로 표시하지 않고 중단한다.
물리 precision cap과 인증 region budget은 바꾸지 않았다.

## 정확한 공통 인수 제거와 남은 인수

Q=5^8 n^17 D(n)^2, D(0)=2^318·5^32를 source-bound identity로 다시 확인한다.
gcd(n,D(n))|D(0)이므로 u와 정규화한 D의 공통 소인수는 없다.
P(0)의 절댓값은 **2^1539·5^73·2147456683**이다.
gcd(n,P(n))|P(0)이며 마지막 cofactor를 소수라고 가정하지 않는다.

각 class에서 보장되는 공통 2/5 인수 g=2^c2·5^c5를 제거한다.
u=r+mj, j=0〜count−1로 치환한 모든 다항식의 계수가 g로 정확히 나누어지는지 검사한다.
불완전한 valuation이면 g는 보장되는 공통 인수이며 **실제 전체 gcd라고 주장하지 않는다.**
정확 2/5 cancellation 여부는 class별 필드로 구분한다.
추가적인 odd gcd는 없어졌다고 가정하지 않고 가변 인수의 조건으로 남긴다.

\[
\frac{Q}{g}=F\,u(j)^{17}D_{\rm normalized}(j)^2,
\quad F=2^{17a+2d_2-c_2}5^{8+17b+2d_5-c_5}.
\]

이 identity를 **다항식 계수 전체**에서 다시 곱해 확인한다.
D의 2/5 valuation이 정확하면 D_normalized와 10이 서로소다.
따라서 F, u^17, D_normalized²의 pairwise coprimality도 확인할 수 있다.
valuation이 미결정이면 해당 서로소성 주장을 하지 않는다.
gcd가 확정되지 않은 인수를 단순한 coprime CRT로 합치지 않는다.

## 고정 CRT period의 전수 검사

필요한 M은 [④-4c-1](C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md)의 pinned
4096-bit numeric error·signed residual guard에 대한 strict M_req를 그대로 사용한다.
shell 15/16/17/18에서 M_req의 bit length는 각각 **1018/810/549/220**이다.
16384-bit를 넘기거나 precision을 높여 해결한 결과가 아니다.

Δ/g=z, P/g=P′, Q/g=Q′라 쓰면 odd multiplier h=2k+1에 대해

\[
z=2P'-hQ'.
\]

공통 인수 제거 후 의미가 남는 작은 2/5 modulus를 고른다.
2 modulus는 확인된 Δ valuation과 제거한 common valuation의 차이에 따라 선택하고,
5 modulus는 Q′가 5로 나누어지면서 P′가 5-unit인 경우에만 추가한다.
단순히 큰 modulus를 고르지 않는다. 현재 선택된 고정 period는 최대 80이다.

정수 다항식의 j residue는 이 고정 period로 완전히 덮을 수 있다.
각 residue의 원래 class 안 multiplicity를 구하고, odd h의 모든 residue를
`z≡2P′−Q′ mod gcd(2Q′,W)`라는 정확 coset으로 합친다.
coset의 최소 **비영** 정수 거리를 검사한다. 0은 이전 별도 tie proof가 배제한 상태다.
실제 Lang의 rational tie 배제는 기존 checker의 `check_tie_cover`로 네 domain에 다시 확인했다.
실제 point precision이나 전체 impulse 인증과는 구별한다.

작은 signed z가 고정 coset에 들어가면 그 class를 보존한다.
`actual_full_delta_witness=False`, `variable_moduli_checked_by_this_witness=False`를 반드시 기록한다.
이는 추가 검사하지 않은 가변 인수까지 만족하는 반례가 아니다.

## 더 높은 2/5 modulus도 해결하지 못하는 class

D valuation이 정확한 class에서는 Q′=F·v이고 gcd(v,10)=1이다.
W가 2F의 배수이며 2/5 소인수만 가진다면

\[
\gcd(2Q',W)=2F,\qquad z\equiv2P'-F\pmod{2F}.
\]

즉 더 높은 모든 2/5 prime power도 같은 coset만 남긴다.
모든 coset에는 0이 아닌 |z|≤2F인 정수가 존재한다.
따라서 **2gF<M_req**라면 어떤 높은 고정 2/5 modulus를 사용해도
작은 Δ와 양립하는 residue를 전부 배제할 수 없다.
이 조건을 만족한 미해결 class가 **5,370개**다.
이것은 전체 physical Δ에 대한 반례가 아니라 **고정 2/5 정보만의 한계**다.
이 한계는 odd quotient h의 범위를 제한하지 않는 현재 합동식에 해당한다.
h의 유한 범위나 가변 divisor까지 함께 사용하는 미래 증명 방식을 반박하지 않는다.
나머지 class는 이 sufficient obstruction이 성립하지 않거나 D valuation이 미결정이다.
그들을 자동으로 통과/반박된 것으로 취급하지 않는다.

예를 들어 네 shell 모두 n≡3 mod 10, a=b=0 class가 남는다.
낮은 고정 congruence에서는 signed Δ=−1과 양립한다.
전체 고정 2/5 정보까지 사용해도 비영 compatible gap을 **2·5^8=781250 이하**에서 찾을 수 있다.
이 수는 가장 작은 shell 18의 M_req보다도 작다.
**실제 Δ=1 또는 Δ≤781250 입력을 발견했다는 뜻은 아니다.**
아직 u^17·D_normalized²의 나눗셈 조건을 만족시키지 않았기 때문이다.

## 무엇이 아직 필요한가

같은 class의 첫 n과 다음 n은 normalized Q 및 D²가 다르다.
고정 residue만으로 전체 variable CRT residue가 하나로 정해지지 않는다.
모든 class는 덮었지만 미해결 8,730개에서는 가변 divisor와 parameter 범위를 포함한
`|2P′(j)−(2k+1)Q′(j)|`의 정수 gap 문제를 아직 풀지 못했다.
실제 작은 Δ 입력 반례는 singleton 전수에서 0개이며, non-singleton의 존재/비존재는 미판정이다.
따라서 새 independent lemma checker를 설계하거나 coverage를 올리지 않는다.

다음은 가변 u^17/D_normalized²를 그대로 유지한 parametric gap lemma 또는
odd quotient 범위와 함께 작은 Δ를 배제하는 별도 산술 구조 조사다.
고정 2/5 modulus 확대나 point 표본 추가로 이 의무를 대신하지 않는다.
shell 4 및 shell 0〜3의 다른 증명 문제는 계속 별도로 보류한다.

## 구현·검증과 구상 일치성

구현: `a_reference/c1b1_residue_class_survey.py`.
fixture: `a_reference/fixtures/c1b1_residue_class_survey_v1.json`.
시험: `tests/test_c1b1_residue_class_survey.py`.
fixture는 class schema와 columnar rows를 사용하며 반복되는 g 배수는 작은 multiplier로 보관한다.
`unpacked_report`가 원래 이름과 정확 정수를 복원하고, 손실 없는 round-trip을 시험한다.
이 복원 함수는 certification checker가 아니다.

작은 synthetic domain 전수, 비서로소 residue 교차, 모든 odd multiplier의 독립 전수,
고정 prime-power coset lemma, normalized polynomial·분모 identity를 검사한다.
source/inventory·tie 전제·class 누락·분모 변조·예산 부족·거짓 인증 객체도 결함 주입으로 검사한다.
원래 checker·물리·이전 survey·Frozen D_valid 등 기존 파일 **33개**를 `23144df`와 LF 비교해 보존했다.
181 probe의 긴 replay를 다시 수행한 결과는 아니다.
공통 EXP/numeric error/물리 상수를 재사용하므로 새 독립 물리 감사로 해석하지 않는다.

자동 시험과 별도로 구상 경계를 점검했다. 모든 원래 입력을 보존하고 새로운 물리·도달 제약·목표를 넣지 않았다.
분석 cover, 부분집합 하한, shell 인증, 실제 작은 Δ 반례를 서로 구별한다.
신규 직렬 **27 passed, 22.48초**.
**LOCAL FULL: 2652 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 425.76초**.
신규 27개 시험의 직렬/병렬 결과는 항목별로 동일하다.
cp949 컴파일러 출력 해독 경고 25건은 남았으며 해결됐다고 해석하지 않는다.
완료 로그/JUnit·exit code·보존 해시·별도 구상 경계 점검은
`runs/c1b1_residue_class_20260928/{verification_summary.json,unchanged_contracts.json,concept_alignment.json}`에 기록한다.
정규식의 괄호 처리로 실패한 중간 시험 로그도 삭제하지 않고 보존한다.
