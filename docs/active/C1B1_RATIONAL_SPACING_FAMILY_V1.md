# C1-B1 rational spacing family 인증 v1

**2026-09-28 / 기준 `f0484af` / shell 19〜23의 5개 전체 domain 인증.**
전체 ④-4b와 R=20은 **NotCertified**다. 새 domain 5개를 검증 후 연결한 fresh coverage는
**6/64 → 11/64 region, gap 89 → 84**다. 남은 19개에 대한 더 강한 수학은 이번 인증기에 넣지 않았다.
④ 동결·⑤·E_min·전체 산란각은 보류한다.

## 인증 계약

[생성기](../../a_reference/c1b1_family_certificates.py)는 기존 survey로 proof object를 제안한다.
[별도 checker](../../a_reference/c1b1_family_checker.py)는 survey나 생성기를 import하지 않으며,
그들의 pass flag·normal_form·residual·tie 함수도 호출하지 않는다.
원래 coverage 의무의 **외부 expected_domain**과 실행 precision 상한을 입력받아 다음을 재계산한다.

1. 동결 PES의 각 short/damping monomial을 직접 미분하고 retardation quotient를 전개한다.
   제공된 정수 P/Q와 지수 Laurent 계수 전부가 정확히 일치해야 한다.
2. 양의 계수 Q와 양의 n 때문에 `Q_max=Q(n_max)`가 **닫힌 domain 전체**의 상한임을 확인한다.
   `Q=5^8 n^17 D_int^2`도 정수 계수 전체를 곱해 확인한다.
3. 4096-bit 정수 EXP enclosure와 양의 반지름 monomial 양 끝값으로 signed `[L_exp,U_exp]`를 다시 감싼다.
4. 원래 평가기의 수치 endpoint error lemma에서 `E_p`를 다시 구한다.
   제공된 `[L_exp-E_p,U_exp+E_p]`가 정확히 일치해야 한다.
5. `s=1/(2Q_max)`, `margin=s-max(|L_exp|,|U_exp|)`을 구하고 **E_p < margin**을 요구한다.
   같은 조건인 `max(|L_exp-E_p|,|U_exp+E_p|)<s`도 strict하게 확인한다. 등호는 거부한다.
6. 모든 정수 n의 rational tie 배제에 대한 valuation/residue partition과 유한 예외를 검증한다.
7. 요구 precision은 실제 128→…→16384 schedule 안에 있어야 하며 외부 execution ceiling을 넘지 않아야 한다.
   proof의 최대 precision은 family p와 같고 예외 point p도 그 이하이어야 한다.
8. exact rational triangle bound에 residual/error를 더해 momentum FX(96,80)의 legal output도 보장한다.
   축 밖 두 impulse component는 정확히 0이다.

`P/Q`가 half-integer와 다르면 거리의 정수 분자는 적어도 1이므로 거리 ≥s다.
tie를 제외하고 residual을 더한 exact impulse의 거리는 margin 이상이다.
모든 계산 endpoint의 오차가 margin보다 작으므로 p에서 모든 endpoint는 같은 rounding 영역 안에 있다.
이것은 **region 안의 모든 결과가 같다**는 주장이 아니다. 각 입력의 결과가 유일하게 결정된다는 주장이다.
실제 평가기는 더 낮은 precision에서 이미 결정되면 종료할 수 있고, 이번 p는 필요한 유한 상한이다.

proof object는 JSON-compatible 정수와 canonical rational 문자열을 사용한다.
float error·손상된 정수 계수·중복 항·잘못된 버전/범위·source hash·전체 Certified 승격은 거부한다.
객체의 `certified` 표시는 검증 전에는 권위가 없다.

## Tie proof object의 전수 범위 검사

원래 `[n_min,n_max]`를 `n=2^t u`, u 홀수로 분류한다. 가능한 모든 t를 checker가 직접 계산한다.
whole-class 최소 valuation이 유일하면 그 값이 정확하다. 제곱 분모의 valuation parity도 사용할 수 있다.
판정되지 않은 분류는 u mod 256, 필요 시 mod 4096/65536의 radix tree로 검증한다.

checker는 원래 구간과 교차하는 모든 branch를 직접 방문한다. leaf가 없으면 더 깊은 증거를 요구하고,
마지막 modulus에서도 없으면 거부한다. 사용하지 않은 leaf·겹치는 ancestor/descendant·중복 leaf도 거부한다.
각 leaf의 valuation은 survey의 monomial sum과 다른 **modular Horner** 계산으로 다시 구한다.
따라서 끝점 몇 개나 pass flag로 전체 coverage를 대신하지 않는다.

마지막 shell 23의 미결정 leaf는 원래 구간 안에서 한 입력만 남긴다:
`n=1071856711314178048`, `R=3808`.
checker가 **입력 수를 먼저 센 뒤 64점 이하만** exact P,Q로 평가하며,
제공된 exception 목록과 residue가 정확히 일치하고 tie가 아니어야 한다.
이 입력의 실제 물리 point proof도 기존 API로 256-bit에서 다시 인증한다.
유한 예외 누락이나 예외 precision을 family p보다 크게 숨기는 것은 거부한다.

이 점만 남은 이유도 정확히 확인했다. t=53에서 정규화 전 최소 valuation은 P 1523, Q 1521인데,
u=119의 실제 valuation은 **P 1557, Q 1555**다. 양쪽 모두 최소값보다 **34** 높다.
따라서 정규화한 두 residue가 mod 2^16까지 0이라 기존 modulus cap 65536으로는 정확 valuation을 알 수 없었다.
인접 홀수 u=117/121에서는 P 1525, Q 1523이다. D_int(n)의 실제 valuation은 327이다.
이는 합동류 검사의 제한된 modulus에서 큰 상쇄가 남은 원인이며 실제 impulse가 tie에 가깝다는 뜻은 아니다.
원자료는 `runs/c1b1_family_checker_20260928/exception_structure.json`에 보존했다.

## 검증된 5개 domain

| shell | 원래 닫힌 domain의 격자점 수 | p 상한 | 유한 예외 |
|---|---|---|---|
| 19 | 97,656,868,227,463,141 | 2048 | 0 |
| 20 | 122,070,930,727,463,141 | 2048 | 0 |
| 21 | 152,588,508,852,463,141 | 2048 | 0 |
| 22 | 190,735,481,508,713,141 | 4096 | 0 |
| 23 | 238,419,197,329,025,641 | 4096 | 1 (point 256) |

이 수는 실제 방문 점 수가 아니라 보수적 input 의무의 수다.
원래 domain을 줄이거나 64-region/16384-bit를 늘리지 않았다.
기존 region 6개는 이전 checker로 다시 확인하고 새 5개는 별도 checker로 확인한 뒤,
fresh geometry의 **정수 gap**에서 이 닫힌 interval들을 뺀다.
gap 84개에는 첫 shell의 흩어진 gap 등도 포함되므로 남은 큰 family 19개와 같은 집계가 아니다.

재현 proof object와 coverage는
[fixture](../../a_reference/fixtures/c1b1_family_certificates_v1.json)에 함께 저장했다.

## 독립성의 범위와 변조 검사

checker의 물리식/잔여항/partition/strict 조건은 survey 생성기와 분리했다.
survey 주요 함수들을 모두 실패 함수로 바꾼 뒤에도 기존 객체의 5개 인증 검사가 통과한다.
survey가 shell 18을 통과했다고 거짓 표시해도 checker가 strict 조건으로 거부한다.

공통으로 신뢰하는 기반은 **동결된 물리 상수, 기존 source-bound endpoint error lemma,
정수 EXP enclosure, 기존 point/domain API**다.
이 기반까지 완전히 다른 구현으로 재증명한 전역 독립 물리 감사라고 부르지 않는다.
해당 소스 LF hash, live evaluator bindings, numeric helper/class/EXP-alias bindings,
고정 512-bit 수치 range 기반을 확인한다.

실제 5개 proof object에 P/Q·D·지수항 오류, Q_max 축소, residual/error/guard 축소·방향 반전,
precision/cap/max 필드 조작, domain 축소·축 변경, tie class/leaf/exception 누락·중복,
위조 residue·scope/global 승격 등을 주입해 거부되는지 확인한다.
synthetic exact tie와 `E=margin` 등호도 거부한다.
둘 다 실제 Lang reachable 반례라는 뜻은 아니다.

최종 LOCAL FULL·직렬/병렬 결과 대조·기존 소스 보존 증거는 CURRENT_STATE와
`runs/c1b1_family_checker_20260928/verification_summary.json`에 기록한다.
물리 실행기·181 Frozen D_valid·기존 인증기와 fixture는 보존한다.
신규 직렬 시험은 **54 passed, 32.93초**다. 초기 51개 검사 뒤 class/EXP-alias 교체 거부를 보강했고,
그 이전 전체 실행(2590 passed, 427.65초)은 별도 중간 로그로 보존한다.
최종 **LOCAL FULL: 2593 passed + 1 strict xfailed, skip 0, 실패/error 0,
exit 0, 385.03초**다. cp949 출력 해독 경고 25건은 남았다.
신규 54개 결과는 직렬/병렬 항목별로 동일하며 기존 관련 파일 26개가 `f0484af`와 LF 바이트 동일하다.
181 probe의 긴 replay를 새로 실행한 것은 아니다. 중간 검사 실패 로그도 보존했다.

다음 작업은 **별도의 ④-4c: 남은 19개 modular-distance lower-bound survey**다.
CRT를 사용하려면 인수들의 서로소 조건부터 확인해야 하며, 단순한 precision 상향으로 대체하지 않는다.
