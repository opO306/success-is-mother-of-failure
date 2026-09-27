# ④-4c-1 — 19-domain exact modular-distance survey v1

**기준: `561a91e`, 2026-09-28. 상태: survey_only.**
새 family 거리 하한·반올림 분리 lemma·인증 checker는 만들지 않았다. 기존 coverage는 **11/64 region·gap 84**이고
R=20/④-4b 전체는 **NotCertified**다. 64는 region 예산이며 53은 남은 예산이다.
④ 전체 동결·⑤·E_min·전체 산란각은 보류한다.

## 무엇을 계산했는가

기존 [family checker](C1B1_RATIONAL_SPACING_FAMILY_V1.md)가 인증한 shell 19〜23을 제외한
**원래 shell 0〜18의 닫힌 양의 축 격자 domain 19개**를 그대로 사용했다.
이는 기존 reachable enclosure의 선언 domain이며 실제 궤적에서 방문한 모든 점의 목록이 아니다.
각 domain의 모든 격자점을 순회하지 않고, 미리 정한 선택법으로 총 **2,679점**만 조사했다.
endpoint·64등분 위치·양 끝과 중간의 연속 이웃·2/5 거듭제곱의 배수 anchor를 포함하며
domain당 최대 205점이다. 실제 선택 수는 134〜146점이다. 난수와 결과에 따른 표본 추가는 없다.

P/Q는 전체 정확 impulse의 **유리식 부분**이다. 정확 impulse는 별도의 지수 잔여항을 더해야 한다.
본 조사에서 exact Δ라 부르는 것은 이 유리식 부분의 정수 거리다.

\[
s=(2P\bmod 2Q)-Q,\qquad
k=\frac{2P-s-Q}{2Q},\qquad
\Delta=|s|=|2P-(2k+1)Q|,\qquad d=\frac{\Delta}{2Q}.
\]

음의 P도 같은 정수 나머지 규약을 사용한다. `mod Q`로 바꾸면 홀수 배수 경계 조건이 사라진다.
항상 0≤d≤½다. gcd(P,Q)를 먼저 나눈 Δ·Q도 별도로 기록한다.
약분 전 Δ가 커 보이는 것을 강한 위상 분리로 해석하지 않는다.
표본에서 관측한 gcd 비트 길이 범위는 1〜1,571이며, 모든 domain에 gcd=1인 표본도 있었다.

표본마다 P/Q·nearest k·signed Δ·약분 값·정확 거리·정확 2-adic valuation·분모 인수별 residue·gcd·CRT를 계산했다.
fixture에는 최소값의 원자료, 정확 quantile, 거리/정수 크기 histogram, 표본 선택·원자료 해시를 저장했다.
전체 2,679개 원자료 행은 Git 밖 실행 기록에 보존한다.
**관측 최소값·quantile은 선택한 점들에만 해당하며 domain 전체의 하한은 아니다.**

## 필요한 M과 조사 결과

기존 4096-bit 수학 enclosure의 signed residual [L,U]와 source-bound numeric error E를 사용했다.
E 진단의 execution precision은 고정 4096 bit다. 실제 물리 실행을 이 precision으로 새로 인증한 것은 아니다.
precision cap 16384와 기존 5개 family의 precision은 바꾸지 않았다.

\[
G=\max(|L|,|U|)+E,\qquad Q_{\max}=Q(n_{\rm hi}),\qquad
M_{\rm req}=\lfloor 2Q_{\max}G\rfloor+1.
\]

strict 조건은 M>2Q_max G다. M≥ 같은 느슨한 비교로 바꾸지 않는다.
Q는 양의 계수 다항식이므로 Q_min=Q(lo), Q_max=Q(hi)다.
M_req는 **이 특정한 공통 absolute guard·Q_max 방식**에 필요한 정수 하한이며
모든 가능한 미래 인증 방법의 필요조건이라는 뜻은 아니다.

아래는 정확 정수의 bit length다. bit length b는 2^(b−1)≤정수<2^b를 뜻한다.
표본 최소 Δ와 최소 약분 Δ는 서로 다른 입력에서 나올 수 있다.

| shell | 선택 점 수 | 표본 최소 Δ bit | 표본 최소 약분 Δ bit | M_req bit | 조사 분류 |
|---|---:|---:|---:|---:|---|
| 0 | 137 | 1689 | 221 | 1750 | shifted phase |
| 1 | 134 | 1701 | 246 | 1748 | shifted phase |
| 2 | 140 | 1707 | 184 | 1745 | shifted phase |
| 3 | 145 | 1711 | 194 | 1739 | shifted phase |
| 4 | 143 | 1717 | 240 | 1731 | 분모·guard의 구간 전체 묶음 개선 |
| 5 | 141 | 1726 | 203 | 1719 | stronger modular family bound |
| 6 | 146 | 1730 | 197 | 1702 | stronger modular family bound |
| 7 | 142 | 1737 | 217 | 1680 | stronger modular family bound |
| 8 | 139 | 1747 | 222 | 1650 | stronger modular family bound |
| 9 | 141 | 1752 | 194 | 1612 | stronger modular family bound |
| 10 | 139 | 1759 | 238 | 1562 | stronger modular family bound |
| 11 | 140 | 1769 | 243 | 1499 | stronger modular family bound |
| 12 | 140 | 1776 | 211 | 1417 | stronger modular family bound |
| 13 | 142 | 1780 | 221 | 1314 | stronger modular family bound |
| 14 | 140 | 1790 | 225 | 1184 | stronger modular family bound |
| 15 | 145 | 1794 | 227 | 1018 | CRT 우선 조사 후보 |
| 16 | 145 | 1802 | 280 | 810 | CRT 우선 조사 후보 |
| 17 | 146 | 1810 | 249 | 549 | CRT 우선 조사 후보 |
| 18 | 134 | 1819 | 258 | 220 | CRT 우선 조사 후보 |

**4+1+14로 나뉜다.** shell 0〜3은 G≥½여서 유리식 거리 d≤½가 기존 guard를 이길 수 없다.
단순히 느슨한 interval 때문이라고만 볼 수도 없다. 양 끝/중간의 별도 point residual enclosure
12개 중 11개는 residual의 절댓값 하한 자체가 ½ ULP보다 크다.
따라서 지수 잔여항으로 이동한 경계를 다루는 signed/shifted phase 방식이 필요한 후보들이다.
이 point 진단은 전체 impulse가 경계에 가깝다는 증거도, precision 실패라는 증거도 아니다.

shell 4는 G<½지만 M_req>Q_min이다. 모든 n에 대한 공통 M은
M≤Δ(lo)≤Q(lo)=Q_min이어야 하므로, 현재 `M/(2Q_max)>G` 구조로는 닫을 수 없다.
shell 0〜4 모두 원래 domain 안의 **실제 exact Δ<M_req 표본**도 저장했다.
bound만 크게 쓰거나 precision만 높여 해결할 문제로 분류하지 않는다.
point별 분모에 맞춘 정규화·더 긴밀한 local/signed guard 또는 shifted phase를 조사할 수 있다.

shell 5〜18은 선택한 모든 점에서 d>G다. 이는 **관측 사실**이며
최대 78,125,618,227,463,141개인 원래 domain 전체에 대한 증명은 아니다.
모든 `family_delta_lower_bound`, `family_phase_lower_bound` 필드는 None이고 새 인증 region은 0개다.

## 분모 산술 구조와 CRT

\[
Q(n)=5^8n^{17}D_{\rm int}(n)^2.
\]

D_int(0)=2^318·5^32를 exact integer로 확인했다.
D(n)−D(0)은 n의 정수 다항식 배수이므로 gcd(n,D(n))는 D(0)을 나눈다.
따라서 n과 D의 공통 소인수는 2와 5에 제한된다.
n에서 2/5 인수를 제거한 나머지는 “10과 서로소인 cofactor”로만 표시하며 소수라고 주장하지 않는다.
2P(n) mod n=2P(0) mod n이고, mod n^17에서는 0〜16차 항만 남는다.
D 및 D²로 나눈 다항식 remainder도 계산했으나 계수가 유리수일 수 있으므로 정수 배수 c로 분모를 제거해
`c·2P=A·D+remainder` 또는 `c·2P=A·D²+remainder` 형태로 보관한다.
**c의 modular 역원이 존재한다고 가정하지 않는다.** unscaled residue로 사용하는 것은 허용하지 않는다.

각 표본에서 세 인수의 pairwise gcd를 먼저 계산하고 **비서로소 generalized CRT**로 합쳤다.
L=lcm(5^8,n^17,D²), a=2P mod L이면
`min(a,L−a)≤Δ`는 그 입력에 대한 정수 하한이다.
L이 Q보다 작을 수 있고, 이 합동식은 `2P−홀수·Q`의 홀수 조건을 버리므로
전체 `mod 2Q` 거리보다 약해질 수 있다. 서로소라고 가정하거나 L을 곧바로 Q로 쓰지 않는다.
shell 15〜18에서는 **선택한 570개 점 전부**의 CRT 하한이 M_req 이상이었다.
이 네 domain을 다음 산술 lemma 조사 후보로 삼을 근거는 생겼지만 **family CRT 하한은 아직 없다.**

모든 원래 domain은 작은 modulus에 대해 모든 residue를 포함한다.
mod 10의 정확한 residue별 점 수를 interval 산술로 계산했고,
domain 길이가 5^8 이상임도 확인했다. shell 조건만으로 작은 residue들을 제외할 수 없다.
각 domain에 있는 5의 배수 하나에서 `2P mod 5^8=0`인 exact witness를 확인했다.
따라서 **고정 인수 5^8의 residue-distance 최소값은 0**이다.
그 입력의 전체 Δ는 0이 아니다. 이 부분 하한을 rational tie로 혼동하지 않는다.

정확 valuation은 정수 전체의 나눗셈으로 구했다.
R=3808 입력의 v2(P)=1557, v2(Q)=1555, 약분 뒤 (2,0)을 새 시험에서도 확인했다.
16-bit modulus에서 둘 다 0이 되는 것은 정보 손실이며 exact tie가 아니다.

## 구현·검증·구상 일치성

구현: `a_reference/c1b1_modular_distance_survey.py`.
fixture: `a_reference/fixtures/c1b1_modular_distance_survey_v1.json`.
시험: `tests/test_c1b1_modular_distance_survey.py`.
실행 원자료/로그: `runs/c1b1_modular_distance_20260928/`.

survey는 pinned 기존 자료를 읽고 S와 기존 독립 checker K의 정확 전개가 같은지 대조한다.
이는 독립 family 인증이나 독립 물리 감사가 아니다. 기존 numeric error·EXP·동결 상수는 공통 기반이다.
기존 checker는 이 module을 import하지 않으며 coverage compositor에도 새 연결이 없다.
source/fixture 변조, 정확 식의 계수 변경, CRT 비서로소 처리, 잘못된 modulus/factor-of-two,
약분 전 Δ의 과장, 유리 remainder의 무단 modular 사용을 시험했다.
거짓 pass/status flag를 붙인 survey 객체도 기존 checker가 거부한다.
표본 원자료 2,679행의 개수와 group별 해시도 별도로 대조했다.

자동 시험과 별도로 구상 경계를 점검했다. 원래 19개 domain·64 region·16384 bit를 유지하고
세계의 계산식·전이·A/B 분리·D_valid·이전 인증 결과를 변경하지 않았다.
19개 전수 enumeration, 관측 최소값의 인증 승격, hidden residue restriction도 없다.
관련 기존 소스·fixture·시험 30개가 `561a91e`와 LF 바이트 동일하다.
181 Frozen D_valid 장시간 replay를 새로 수행했다는 주장은 하지 않는다.

신규 직렬: **32 passed, 25.73초**.
**LOCAL FULL: 2625 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 383.44초**.
cp949 컴파일러 출력 해독 경고 25건은 남았으며 해결됐다고 해석하지 않는다.
신규 32개 결과는 직렬/병렬에서 항목별로 동일하다.
원자료 count/hash, 보존 해시, 종료 코드/JUnit 대조 및 별도 구상 경계 점검은
`verification_summary.json`·`unchanged_contracts.json`·`concept_alignment.json`에 남겼다.

## 다음 의무

기존 checker는 그대로 보존한다. shell 15〜18을 우선해 n의 2/5 valuation별로
gcd·L·정수화한 D² remainder의 합동 조건이 **전 domain에서** 작은 signed Δ를 배제하는지 조사한다.
shell 5〜14에는 별도 더 강한 구조가 필요한지 분리한다.
shell 4와 shell 0〜3은 현재 absolute guard 방식의 구조적 한계를 먼저 해결한다.
새 lemma의 증명 대상·strict inequality·source-bound error가 정해진 뒤에만
새 checker·fault injection·family certification·coverage 연결 순서로 진행한다.
그 전에는 ④-4b NotCertified와 downstream 보류를 유지한다.
