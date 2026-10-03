# H₂ R=0.4 Open-Hypothesis Adversarial Audit V0

**2026-10-03 / 작성자 실행·검토 numerical audit / NOT CERTIFIED / push 없음.**

전체 오차 예산은 닫히지 않았다. 엄격한 spatial irrep 검사에서 작은 inversion 오염을 발견했고,
uncontracted QZ 및 native AO의 fixed-C 경로는 기존 guard에서 거절됐다.
Reference의 R=.4 독립 pointwise uncertainty와 MO ERI pair-interchange는 **UNRESOLVED**다.
기존 QZ44의 FAIL, 0.001 hartree 기준, production 미승인은 그대로다.

이번에 얻은 가장 강한 새 증거는 **R=.4 cardinal progression의 체계적인 접근**이다.
DZ→TZ→QZ→V5Z의 reference 차이가 .096834→.015634→.002199→.000633 hartree로 감소했다.
Finite Gaussian trial space의 한계 가설은 **SUPPORTED UNDER CHECKED ASSUMPTIONS**로 올린다.
그러나 모든 .002199 hartree를 basis 하나에 배분했다는 뜻은 아니다.
아주 작은 AO 차이가 조건이 나쁜 변환에서 증폭되는 별도 numerical 문제도 직접 관측했다.

## 명령·범위·봉인

설계자 명령은 기존 reference gate 미완료 상태에서도 우리 front-end/basis 쪽 one-point 진단을
진행하도록 새로 승인했다. 이전 보고서의 D–G 미실행 상태는 당시 기록으로 보존한다.
실행 시작 시 branch `codex/h2-qz-cause-v0`, HEAD/origin branch
`f462cc0a9470eb3e9631d4aa7103a5fc168a6301`, origin/master
`6c53eec71e981cef35f850095da76b965457866c`, clean·ahead/behind0/0를 확인했다.
같은 기존 worktree에서 새 isolated audit만 추가했다.

- `AGENTS.md`·`RULES.md`와 CURRENT_STATE/REPO_MAP의 해당 활성 H₂ 범위를 읽었다.
  기존 H₂ source·계약·primary reference 증거를 범위 지정해 확인했다. 저장소/runs 전체 스캔은 하지 않았다.
- 새 [protocol](../../electronic_pilot/adversarial_v0/protocol.json)은 spatial state 검사 우선,
  basis 정의, R=.4의 다섯 one-point, 독립 AO/MO, 연결된 2×2 실험을 정의한다.
- 기존 numerical guards: Smin>1e-10, orthogonality norm2≤1e-10,
  H asymmetry≤1e-10, eigen L2≤1e-9, vector norm error≤1e-10.
  Same-basis band1e-9와 physical reference criterion0.001도 변경하지 않았다.
- 단계별 source/config/input seal을 계산 전에 기록했다. 마지막 phase에는 **1,178 byte bindings**,
  그중 이전 reference audit의1,095 bindings가 포함된다. 전후 불변을 검사했다.
  원래 AO artifact, 재현 vector/order, 이전 실패·반례·보고서도 보존했다.
- 실제 vector는 **reproduced from sealed replay**다. original saved vector로 부르지 않는다.
  기존 vector hash `cfb1113166b72f050f3d2d8c24de6d9aa2b00a72f64f10d83c65470f2f8d35b6`는 불변이다.
- 실행 WSL Python3.12, NumPy2.5.3, SciPy1.18.1, PySCF2.12.1, mpmath1.3.0,
  OMP/OPENBLAS/MKL threads1. Native executable/libint binary/deb 및 입력은 실행 전 hash 봉인했다.
  Python package/library 전체 관측 파일은 **postrun observation**이며 pre-run runtime seal로 과장하지 않는다.
- 새 분석 phase를 늦게 추가한 경우 별도 seal이다. 처음 seal에 존재했던 것으로 기록하지 않았다.
  사후 실패에 맞춰 tolerance·canonical rule·기존 integral path를 바꾸지 않았다.

## 실제 저장 상태의 spatial symmetry

CI builder·eigensolver·integral driver를 호출하지 않고 저장된 v/C/S에 실제 대칭 연산을 적용했다.
MO 이름을 세는 방식이 아니라 AO 계수 행렬 W=CVCᵀ의 **S-metric wavefunction norm**을 측정했다.
Closed/open singlet 계수와 fermion ladder도 직접 전개했다. 고정밀80자리 측정은 저장된 binary64
계수/overlap을 정확히 승격한 linear algebra다. AO integral 자체의 정밀도를 올린 계산이 아니다.

| 검사 | 80자리 측정 잔차 또는 norm | 기존 dimensionless guard1e-10 |
|---|---:|---|
| inversion g | 6.20849892308254e-10 | **초과** |
| y-reflection + | 2.27548227911063e-15 | 통과 |
| axial angular generator, Σ | 2.17156320132903e-12 | 통과 |
| 회전 π/7, π/5, π/2 | 최대2.10424143896362e-12 | 통과 |
| spatial electron exchange + | 7.65e-80 | 통과; singlet 구성 정의에 대한 확인 |
| S+·S−·Sz | 0,0,0 | singlet 확인 |

따라서 **엄격한 ¹Σg⁺ 판정은 UNRESOLVED**다. 아주 작은 반전 오염을 보정해 PASS로 만들지 않았다.
Angular operator의 부호/순서 오류도 조사했다. 실제 spherical polynomial map의 회전 생성자
항등식은 l≤3에서 최대5.55e-17, 반사 항등식은0; 실제 AO 함수 세 probe의 inversion/reflection
관계도0으로 일치했다. 잘못된 angular convention 때문에 생긴 오염이라는 반례는 발견하지 못했다.

기존 상태의 odd component S-metric norm²는 **9.63636471947927e-20**다.
진단 목적으로만 even projection을 적용한 vector를 별도 이름으로 보존했다.
기존 독립 SC matrix의 Rayleigh 변화는 **-4.440892098500626e-16 hartree**였다.
원래 상태·에너지·guard는 변경하지 않았다. 이는 .002199 차이가 spatial tail에서 왔다는 증거가 없음을
보여주는 측정이며, 정확한 ground-energy error bound나 pure-irrep 인증은 아니다.
[측정](h2_adversarial_v0/evidence/symmetry.json),
[convention·tail 진단](h2_adversarial_v0/evidence/symmetry_diagnostic.json).

이전 `PHYSICAL_QUANTITY_MATCH_SUPPORTED`는 Hamiltonian·단위·BO energy convention 범위에서
살아남는다. 동일 spatial trial space/정확한 irrep 판정으로 확대하지 않는다.
공간 상태 선택 항목을 열어 두고, 기존 CI/action/eigen equivalence도 **같은 기존 MO 입력**이라는
가정을 붙여 유지한다. 앞으로 실제 반례가 나오면 이 판정들도 다시 연다.

## 실제 basis 정의와 normalization

[Basis Set Exchange API](https://molssi-bse.github.io/basis_set_exchange-apidoc/)에서 H의
cc-pVDZ/TZ/QZ/V5Z version1 JSON을 raw bytes로 취득해 봉인했다.
PySCF 이름만 믿지 않고 모든 exponent/contraction coefficient, 중심, 구면 convention,
함수 순서, primitive/contracted normalization을 대조했다.

첫 strict-column checker는 DZ에서 거절됐다. BSE는 일반 contraction 열을, PySCF는 일부
segmented 열을 사용해 열 자체가 달랐다. **열 차이를 basis-span 오류로 판정한 초기 기준이 너무 강했다.**
초기 source·refusal·seal을 보존하고, energy 실행 전에 별도 V1 checker로 다음을 확인했다.

- angular momentum별 exponent identity 및 전체 coefficient matrix의 rank/union rank를
  **정확한 유리수 산술**로 비교했다. cutoff/rank tolerance를 쓰지 않았다.
- DZ/TZ/QZ/V5Z 모두 같은 전체 AO span이다. 공급된 binary64 exponent/coefficient의 exact dyadic
  비교이며, 무한정밀 real integral/모든 library correctness의 증명은 아니다.
- 독립 Gamma radial normalization + analytic primitive overlap으로 실제 radial 계수를 재구성했다.
  다섯 정의의 최대 relative 차이는 **3.092531380725353e-16**였다.
- spherical60 QZ, Cartesian70, 실중심두 개(0,0,±.2) Bohr, Z=1+1, ghost 없음.
  실제 real-spherical polynomial metadata를 저장하고 angular algebra/함수값으로 대조했다.
- uncontracted QZ는 동일 exponent의 (l,exponent)별 primitive 하나다. 원래 contracted span을 포함하는
  64 AO trial space다. basis/eigenvalue cutoff나 원래 함수 삭제를 하지 않았다.

[전체 정의·정확한 span 기록](h2_adversarial_v0/evidence/basis_definitions.json),
[초기 잘못된 column-level refusal](h2_adversarial_v0/evidence/initial_column_refusal.json).
Authoritative BSE raw JSON/provenance는 `h2_adversarial_v0/basis_sources/`에도 원본 bytes로 보존했다.

## Fresh R=.4 cardinal·contraction 진단

각 basis는 새 프로세스에서 기존 canonical AO/compact MO/full singlet CI/evr 경로를 호출했다.
S floor·orthogonality를 CI 전에 검사했고, 실패한 entry의 energy는 계산/승격하지 않았다.
QZ는 기존 E_elec의 bit pattern `-0x1.4f1ba4e9683fep+1`과 **bitwise 동일**했다.
Reference target은 기존 Pachucki 값이며 진실/엄밀한 lower bound로 가정하지 않았다.

| basis | AO | numerical 결과 | BO hartree | target와 signed 차이 | orth norm2 | 시간s | peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|---:|
| DZ | 10 | accepted | -.02339662924402841 | +.0968337119347946 | 3.85871e-14 | .033 | 91.95 |
| TZ | 28 | accepted | -.10459627062352972 | +.0156340705552933 | 9.32036e-13 | .134 | 108.91 |
| QZ | 60 | accepted | -.11803113362157003 | +.0021992075572530 | 5.34287e-11 | 1.647 | 453.90 |
| V5Z | 110 | accepted | -.11959699456988826 | +.0006333466089347 | 4.20105e-11 | 46.139 | 3874.16 |
| uncontracted QZ | 64 | **REFUSED: orthonormalization** | — | — | 5.87016e-10 | .138 | 110.16 |

V5Z의 eigen L2 residual3.01610e-14, H asymmetry1.77636e-15로 기존 guard를 통과했다.
그 MO pair-interchange residual3.81319e-6도 여전히 남아 있다.
QZ의 기존 residual2.98114800794148e-5를 해소한 실험이 아니다.
[결과·spectrum·runtime](h2_adversarial_v0/evidence/summary.json).

**관측된 cardinal trend는 finite-basis limitation의 강한 조건부 증거다.**
다른 cardinal의 trial spaces가 모두 nested라고 가정하지 않았으며, extrapolated basis-limit energy를
만들지 않았다. variational 원리상 exact finite trial energy가 exact full-space energy보다 높다는
방향은 일관적이지만, approximate/non-Hermitian numerical integral의 error bound가 없어서
현재 숫자들을 rigorous variational upper bound로 인증하지 않는다.
비수축 comparison은 실패점으로 남겨 contraction과 cardinal contribution을 분리하지 못했다.
V5Z의 one-point 결과를 production basis 선택이나 QZ44 PASS로 승격하지 않았다.

## 독립 AO engine

Ubuntu task-local Libint2 **2.7.2**를 별도 native executable로 사용했다.
Python/PySCF wrapper로 libcint를 다시 호출한 것이 아니다. Libint integral code/linked binary에서
Cartesian70의 S/T/V/ERI를 모든 ordered shell pair/quartet에 대해 계산했다.
Raw monomial shell에 확인된 radial 계수를 공급하고 normalization embedding을 껐다.
Libint `standard` Cartesian convention, screening precision0, null ERI block0이다.
실제 native time2.544s/peak195.63MiB; spherical mapping/conversion 비용은 별도 Python phase다.

공유한 것은 actual basis 입력·radial 계수와 spherical polynomial 표현이다.
계수 normalization은 별도 Gamma formula, native S/T/V/ERI는 primitive closed-form 시험으로도 확인했다.
서로 다른 engine이므로 AO-generation independent numerical comparison이라고 부를 수 있으나,
공유한 representation을 완전히 독립으로 취급하거나 어느 engine을 진실로 놓지는 않는다.

| full raw spherical AO | Libint−libcint 최대 절대 차이 | 위치 |
|---|---:|---|
| S | 7.77156117237610e-16 | (10,40) |
| T | 6.21724893790088e-15 | (17,17) |
| V_nuc | 7.10542735760100e-14 | (0,0) |
| ERI | 2.84217094304040e-14 | (0,0,53,53) |

Libint raw spherical ERI pair-swap residual2.22045e-15, within-pair≤1.55432e-15.
Raw asymmetry를 별도 보존했다. downstream 비교는 양 engine에 **동일한 기존 canonical AO representative**
규칙을 적용했다. lower S/h와 eightfold AO class의 한 값을 재사용하며 평균하지 않았다.
이 대칭 quantity reuse를 MO pair averaging이나 H repair로 바꾸지 않았다.
[전체 AO 비교](h2_adversarial_v0/evidence/AO_comparison.json),
[native executable/input/dependency seal](h2_adversarial_v0/evidence/native_execution_seal.json).

## 동일 AO의 독립 direct AO→MO 및 연결된 2×2

독립 transform은 네 단계의 명시적 `einsum` contraction이다. 기존 AO2MO helper를 호출하지 않는다.
기존 compact arm만 historical helper를 사용한다. 양 arm에는 같은 canonical full AO tensor를 넣었다.
그 span을 별도 eightfold index algebra로 전개하고 기존 restore와 byte equality를 확인했다.
고정한 saved C/v를 모든 cell에서 그대로 사용했다. Full SC matrix는 기존 독립 fermionic action으로
구성해 모든 원소의 비대칭과 같은 v의 action을 측정했다. H를 평균하지 않았다.

| cell: AO / MO | orth norm2 | H asymmetry | MO pair-interchange | 기존 guard 결과 |
|---|---:|---:|---:|---|
| libcint / compact (00) | 5.34287e-11 | 2.22045e-16 | 2.98115e-5 | accepted |
| libcint / direct (01) | 5.34287e-11 | 7.61382e-5 | 9.42422e-5 | **REFUSED: H Hermiticity** |
| Libint / compact (10) | 1.67969e-10 | 2.22045e-16 | 5.63943e-5 | **REFUSED: orthogonality** |
| Libint / direct (11) | 1.67969e-10 | 3.49584e-5 | 4.61290e-5 | **REFUSED: orthogonality first** |

Eigensolver는 accepted00에서만 호출했다. 세 refusal은 **새 accepted energy가 없다.**
cell00의 독립 SC eigen/residual은 기존 동일 MO ground-state 결과를 재확인한다.
그 상태의 action L2는00/01/10/11에서 각각2.36850e-14 /1.08406e-7 /5.15993e-6 /5.17920e-6이다.

관측용 같은-v Rayleigh(E_elec)는 다음과 같다. Refused cells의 ground energy로 부르지 않는다.

| cell | 같은-v Rayleigh hartree | 00 대비 효과 |
|---|---:|---:|
| 00 | -2.6180311336215683 | 0 |
| 01 | -2.618031133599658 | +2.1910473e-11 |
| 10 | -2.618031132483421 | +1.1381474e-9 |
| 11 | -2.6180311324788352 | +1.1427330e-9 |

Interaction E11−E10−E01+E00 = **-1.73248082546706e-11 hartree**.
Ground-energy interaction은 **UNAVAILABLE**이다. 같은-v 값은 변화하는 lowest state의 이동이나
rigorous bound가 아니다. 단독 효과가 작다고 모든 결합 효과를 작다고 가정하지 않았다.
이 실제 연결된 pair를 측정했고, 근거 없는 higher-order/2^N expansion은 하지 않았다.
[모든 cell·worst element](h2_adversarial_v0/evidence/factorial.json).

## Conditioning과 causation

QZ S condition≈9.84446e6, C condition≈3137.59, max|C|≈761.893다.
Canonical AO의 engine 차이 S≤7.77e-16, h≤6.84e-14, ERI≤2.84e-14가
**CᵀΔSC norm2≈1.33681e-10**으로 증폭됐다. 저장 C를 Libint S에 그대로 적용한 guard 초과와 연결된다.
선택한 MO worst/permutation element의 C4 weight, 최대 weighted AO term, absolute cancellation sum과
실제 cell 값을 기록했다. Native/direct의 최대 baseline MO 차이는 약.01197까지 커졌다.
큰 virtual-integral 오차를 ground-state Rayleigh≈1e-9 관측만으로 무해하다고 결론내리지 않는다.
[조건·선택된 AO/MO terms](h2_adversarial_v0/evidence/conditioning.json).

따라서 **AO arithmetic differences × short-R conditioning × transform cancellation**은 관측된
numerical 문제의 연결 구조다. 어느 AO engine의 exact-integral error가 얼마인지는 아직 bound가 없다.
이는 libcint가 .002199 hartree만큼 틀렸다는 판정도, 둘이 맞는다는 인증도 아니다.
Cardinal trend와 numerical 증폭을 동시에 장부에 두며 단일 범인을 확정하지 않는다.

## Reference 재조사

기존 Pachucki/Sims primary acquisition·전사·실패를 보존했다.
Pachucki의 TableIV는 complete-basis extrapolation 결과이며, exponential Omega convergence를 논의한다.
공개된 상세 convergence 표는1.4011/6/12 Bohr이며 **R=.4의 개별 convergence/error series는 확보하지 못했다.**
다른 점의 convergence β/uncertainty를 R=.4로 옮겨 쓰지 않았다.
Sims와9.586e-13 차이라는 강한 일치가 있지만 독립 R=.4 reported uncertainty가 여전히 없다.
[Pachucki primary](https://arxiv.org/abs/1007.0406), [Sims paper](https://doi.org/10.1063/1.2173250).

추가로 [Ndeke 대학 원문](https://edoc.hu-berlin.de/bitstreams/87e5b794-5696-4bca-8a37-e505e5ba1529/download)의
Table5.3(PDF59/printed49)를 시각적으로 확인했다. R=.4 값은 **-.1202303300**,
Pachucki와 **+1.1178823e-8 hartree** 차이다. 실제 새 계산이나,
[H2SOLV](https://users.fuw.edu.pl/~krp/papers/h2solv.pdf)의 Pachucki 계열 integral algorithm/code를 공유한다.
R=.4의 별도 uncertainty도 없어서 세 번째 완전 독립 검증으로 세지 않는다.
Ndeke의 convergence series도 R=.4를 포함하지 않는다.

[FC-LSE2018 primary](https://www.qcri.or.jp/lab/wp-content/uploads/2018/12/J.Chem.Phys._149_244116_2018.pdf)는
다른 연구진의 integral-free 방법이다. 확보한 main TableI의 ground-state 비교는 R≥1.2이고,
reference columns는 재인용이며 FC 결과는 비변분이다. 이 표를 R=.4의 independent bound로 쓰지 않았다.
[FC variational2019](https://doi.org/10.1039/C8CP05949G)는 유망한 별도 계산이지만
이번 main/supplement 취득은403으로 거절돼 R=.4 primary 숫자를 확보하지 못했다.
제한된 correction/follow-up 검색에서 R=.4를 뒤집는 correction을 찾지 못했다. 전 문헌에 없다는 뜻은 아니다.

**REFERENCE_SIDE_UNRESOLVED** 유지. 새 primary 반례에서 reference 오류를 확인하지 못했지만
reference 정확성을 인증하지도 않았다. 원문 byte/hash와 읽은 범위, 계산·재인용·공유 lineage를
[reference ledger](h2_adversarial_v0/evidence/reference_ledger.json)에 분리했다.

## Hypothesis ledger 및 상태

전체 causal mechanism·반대 증거·직접 시험·connections는
[hypothesis ledger](h2_adversarial_v0/evidence/hypothesis_ledger.json)에 있다.

| 후보 | 현재 상태 | 판정 범위 |
|---|---|---|
| 전사 / R·단위·energy-zero / basis-span·normalization 오류 | CONTRADICTED | 확인한 정의·입력 범위 |
| reference common-mode/extrapolation 오류 | UNRESOLVED | 독립 R=.4 uncertainty 미확보 |
| 작은 inversion 오염 | SUPPORTED | strict irrep 미통과; .002199 기여 확인 못함 |
| finite cardinal representation 한계 | SUPPORTED | 강한 조건부 one-point trend |
| contraction 제한의 에너지 기여 | UNRESOLVED | uncontracted refusal |
| AO arithmetic 차이·MO cancellation | SUPPORTED | 직접 측정; exact error budget 없음 |
| AO×MO numerical interaction | SUPPORTED | 같은-v interaction; ground shift 미확보 |
| 기존 MO의 CI/solve 오류 | NOT_OBSERVED | 기존독립SC와 이번 baseline이 일치 |
| higher-order 조합 | NOT_TESTED | pair 이후 확대 근거/accepted contraction arm 없음 |

`NUMERICAL CAUSE IDENTIFIED`는 위 **측정된 증폭·refusal 구조**에 한정한다.
전체 discrepancy 원인 배분은 **UNRESOLVED**다.
`SAME-FINITE-BASIS EQUIVALENCE`: authoritative coefficient-span 대조 및 기존 MO의 CI 경로는
SUPPORTED UNDER CHECKED ASSUMPTIONS; independent AO/direct 전체 accepted equivalence는 미완료다.
`QZ CURVE`: 기존44-point 실행의43 accepted/1 refused·physical comparison FAIL 유지, 이번에는 재실행하지 않았다.
`PHYSICAL COMPARISON`: QZ R=.4 +.002199207557>기존.001, 그대로 FAIL.
`NOT CERTIFIED`: solver 전체, 모든 MO integrals, reference 진실, production electronic foundation 인증 아님.

## 보존된 실패·검증·구상 일치

초기 column checker의 과한 mismatch 분류, reference acquisition의 exclusive-write I/O 오류,
Windows test collection의 Linux `resource` import 오류 로그를 보존했다.
각각 새 span checker·append-safe acquirer·sealed pure-definition AST 검사로 처리했으며
이미 실행한 numerical source는 편집하지 않았다. Native 준비의 shell quoting/Git path 문제도
계산 전 infrastructure 실패로 구분했다. Windows TLS/403 취득 거절도 숨기지 않았다.
이들은 physics/guard를 세 차례 바꾸는 retry가 아니다. 실제 numerical refusals는 재맞춤하지 않았다.
Native build의 Libint header `std::iterator` deprecation 경고2건도 compile log에 보존했다.
원문 failure log의 CRLF를 whitespace 수정을 이유로 바꾸지 않았다.

신규 algebra/fault-injection20개, native analytic integral3개가 우선 통과했다.
최종 관련 회귀·증거 검사는 **Windows217 passed(6.09s), WSL220 passed(33.04s)**,
failure/error/skip0이다. WSL에는 기존 PySCF integration3개가 추가된다.
[test result record](h2_adversarial_v0/evidence/test_results.json)에 명령·junit/log hash를 기록했다.
**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 isolated 감사·시험·문서만 추가,
기존 실행·공용·물리·frozen source와 fixtures는 byte 불변. 공식 LOCAL FULL 기준선은 갱신하지 않았다.

자동 시험 외에 설계자 구상 일치성을 따로 검토했다: reference/우리 계산 어느 쪽도 진실로 고정하지 않고,
실제 상태부터 검사하고, finite basis 정의를 확인한 뒤 causally connected pair를 측정했다.
오류를 고쳐 desired PASS를 만들지 않았다. 강한 finite-basis 증거와 numerical/referral 한계를 함께 보존했다.
Force·nuclear dynamics·formation·복잡한 atom system·world integration·production 선택은 구현하지 않았다.

Scientific critical-thinking 절차를 적용한 procedural software reference:
[Kassis et al., Scientific Agent Skills (2026), arXiv2609.00065v2](https://arxiv.org/abs/2609.00065),
DOI10.48550/arXiv.2609.00065. 증거 등급/가설 장부 절차의 출처이며 H₂ physical evidence는 아니다.
