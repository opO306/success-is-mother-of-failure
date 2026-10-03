# H₂ R=0.4 CI-Layer Micro-Audit V0 — 2026-10-03

**NOT CERTIFIED / 기존 QZ44 NUMERICAL FAIL 유지 / DESIGNER DECISION REQUIRED.**
R=0.4의 physical/reference 오차 원인은 아직 UNRESOLVED다. 이번 결과는 전체
1830×1830 행렬, 모든 MO 적분, solver, basis 정확성이나 production 승인이 아니다.
R=0.5의 기존 MEASUREMENT_ERROR 판정·refusal, 다른 short-R 상태는 그대로다.

**찾은 것은 이전 determinant 후보의 action 적용 조건 문제다.** 같은 MO 입력에서
원래 direct-pair 행렬과 새 독립 Slater–Condon 계산은 검사 범위에서 일치했다.
반면 이전 후보가 사용하는 PySCF `absorb_h1e → fourfold packing → contract_2e`
action은 한 입력 basis vector에서 19개 출력 성분이 사전 1e-10 기준을 초과해 달랐다.
1전자 항을 흡수한 뒤 서로 다른 성분을 packed 대표값으로 바꾸는 지점까지 분리했다.
그 반례를 보존하고 다른 벡터·eigensolver·energy·Pachucki 비교를 중단했다.

## Git·읽기·격리

요청한 **codex/h2-qz-cause-v0 / ab0d3f2520bb631793bdb08c8e96d8bc95db3b3e**의
기존 managed worktree를 재사용했다. 시작 worktree는 clean이었다. 주 checkout은
master / 41605579606cabe6a1ee161a5364e689fa11fbc1이며 별도 untracked 자료가 있었고
이를 수정·이동·merge하지 않았다.

| 시작에 읽은 ref | commit |
|---|---|
| origin/master | 6c53eec71e981cef35f850095da76b965457866c |
| origin/codex/h2-ao-micro-v0 | 61bad943a1865ac1a6b2e89a6577fe03cb4f6b85 |
| origin/codex/h2-qz-cause-v0 | ab0d3f2520bb631793bdb08c8e96d8bc95db3b3e |

이는 로컬 remote-tracking ref다. 이번에 fetch/push하지 않았다.
관련 history는 ab0d3f2 → 61bad94 → 0e9e454 → 6c53eec → 164ecde다.
AGENTS/RULES/REPO_MAP의 작업·보존·검증 규칙, CURRENT_STATE의 H₂·관련 활성 Gate를
확인했다. 직전 H₂ 원인 분리 보고서와 대상 CI/transform source는 읽었고, 관련 없는
runs 전체는 읽지 않았다. systematic-debugging/verification-before-completion 절차를
사용했다. 현재 요청은 이전 STOP 이후의 좁은 새 감사를 명시적으로 승인한다.

## 사전 봉인·입력·독립성

[protocol](h2_ci_layer_audit_v0/evidence/protocol.json),
[독립 수학 유도](../../electronic_pilot/ci_layer_audit_v0/DERIVATION.md),
[준비 봉인](h2_ci_layer_audit_v0/evidence/preparation_seal.json),
[실행 봉인](h2_ci_layer_audit_v0/evidence/execution_seal.json).

R=0.4 only, cc-pVQZ spherical AO60/MO60, 두 전자, full singlet1830을 유지했다.
기존 Hamiltonian·canonical rule·guards·reference 기준·원래 결과는 불변이다.
비교 기준은 결과를 보기 전에 기존 H_asym_max와 같은 **절대 1e-10**으로 고정했다.
relative difference는 설명용이며 판정 threshold가 아니다. 이는 새 entry/action
비교의 사전 기준이고 원래 acceptance guard를 변경한 것이 아니다.

원래 NPZ는 canonical AO S/h/s8와 C를 저장하고 MO h/g는 저장하지 않았다.
그 byte hash를 검증한 뒤 **동일 저장 C / 기존 one_electron_unique / 기존 compact
PySCF transform**으로 MO를 한 번 재현하여 h.npy/g.npy에 저장했다. 새 AO·C 계산은
없다. 세 비교 경로가 이 동일 저장 MO 입력을 소비했고 마지막까지 hash 불변이다.

| MO 입력 | array SHA-256 |
|---|---|
| h, 60×60 | 052e348a12072c6b598e3f9972ca7bca4b0a4d3aa6853c878d5ab3ed838e160a |
| g, 60⁴ | 27f16faaef7bffdaf35e8ba6a2e5767126eca9a14459692d7919e1ab1f4b5026 |

MO within-pair residual은 양쪽 모두 0이고 pair interchange는 원래와 bit-identical한
**2.9811480079414837e-5**다. 이를 평균·대표값 변경으로 고치지 않았다.

독립 evaluator `fermion.py`는 표준 라이브러리만 import한다. 생성·소멸 연산의
fermion 부호, interleaved spin-orbital determinant, spin singlet을 직접 구성한다.
원래 CI builder·element·norm·mapping helper를 import/call/copy하지 않는다.
선택 원소는 저장 binary64를 정확한 Fraction으로 더하고 sqrt2만 Decimal100으로
표시한다. 이는 libcint AO 자체를 고정밀 적분으로 만드는 일이 아니다.

`baseline.py`는 **비교 대상 값의 export adapter**다. 이쪽에서만 기존 CI builders를
호출한다. queried 상태의 orbital label 합집합에 해당하는 작은 배열로 기존 함수의
해당 원소를 꺼낸다. 원소 식은 다른 orbital을 합산하지 않으므로 동일 입력·동일
연산의 entry 추출이다. 작은 physical CI 문제로 바꾸거나 basis를 삭제·solve한 것이
아니다. full matrix를 생성하지 않았다. 이전 PySCF action은 해당 library kernel을
호출하되 determinant 순서 대응은 새로 유도한 permutation parity로 한다.

## Basis mapping

[전체 대응표](h2_ci_layer_audit_v0/evidence/basis_mapping.json).
숫자 index 대신 orbital pair, occupation, S=0/Ms=0, closed/open normalization class를
비교했다. 원래 upper-triangle 순서와 이전 lower-triangle 순서는 다르지만 상태는 같다.

| 항목 | 원래 A | 이전 후보 metadata | 독립 SC |
|---|---:|---:|---:|
| dimension | 1830 | 1830 | 1830 |
| unique state | 1830 | 1830 | 1830 |
| duplicate | 0 | 0 | 0 |
| missing / extra / unmappable | 0 | 0 | 0 |

Closed state는 unit determinant, open state는 서로 다른 두 determinant의
(D_alpha-beta−D_beta-alpha)/sqrt2다. exact integer sign으로 모든 S+ cancellation을
확인했다. norm은 각각 1, (1²+1²)/2=1이다.
**BASIS_MAPPING_MISMATCH_CONFIRMED가 아니다.**

## Stage A: 선택한 8개 원소

[원소·기여·부호·정규화·input hex](h2_ci_layer_audit_v0/evidence/matrix_elements.json).
아래 두 state는 canonical orbital pair이며 energy/eigenvalue가 아니다.

| bra ← ket | class | existing | independent | abs difference |
|---|---|---:|---:|---:|
| (0,0) ← (0,0) | closed diagonal | 2.2773287179377686 | 2.2773287179377686 | 0 |
| (0,1) ← (0,1) | open diagonal, Coulomb/exchange | 2.9171524472352304 | 2.917152447235231 | 4.4409e-16 |
| (0,0) ← (1,1) | nonzero off-diagonal | 0.1276275653359597 | 0.1276275653359597 | 0 |
| (0,0) ← (0,4) | odd-x expected zero | 0 | 0 | 0 |
| (0,0) ← (0,1) | closed/open, sqrt2 | −3.849484126852614 | −3.849484126852614 | 0 |
| (0,1) ← (4,5) | double change, parity zero | 0 | 0 | 0 |
| (50,50) ← (50,56) | previous worst MO quartet | 1.0022580229449902 | 1.0022580229449902 | 0 |
| (50,56) ← (50,50) | reverse ordering | 1.0022580229449902 | 1.0022580229449902 | 0 |

최대 차이는 4.440892098500626e-16, mismatch 0이다. 이전 작업의 direct-pair helper 값도
이 선택에서 일치했다. Exchange sign과 sqrt2 오류를 지지하는 증거는 없었다.

## Stage B: canonical 12×12 부분행렬

[부분행렬](h2_ci_layer_audit_v0/evidence/submatrix.json).
상태 subset을 physical pair의 lexicographic 순서로 사전 고정했다.

- max abs difference **3.552713678800501e-15**, mismatch **0/144**.
- 최대 차이 pair는 (50,56) ← (50,56).
- A symmetry residual **1.1102230246251565e-16**, independent **0**.

작은 비교가 충분히 정보를 주었으므로 full1830×1830 생성은 하지 않았다.

## Stage C: 첫 action vector에서 STOP

[action 기록](h2_ci_layer_audit_v0/evidence/matvec.json),
[전체 1830 output arrays](h2_ci_layer_audit_v0/evidence/matvec_single.npz).
사전 선택 첫 vector는 **e_(50,50)**다. 모든 output을 canonical 상태로 대응했다.

| 비교 | max component abs difference | L2 difference |
|---|---:|---:|
| original direct-pair column vs independent SC | 8.881784197001252e-16 | 1.0023081188196293e-15 |
| prior PySCF action vs independent SC | **5.566707771187396e-6** | **7.731971076104452e-6** |

PySCF action의 **19/1830** component가 1e-10을 초과했다. 첫 lexicographic output은
(0,50)이며 −0.010100309891357039 vs −0.010100193517049019다.
최대 차이는 (39,50)이다. 아래에 그 하나를 상세 축소했다.
**few-state sparse / mixed-sign vector는 NOT_EXECUTED**다. 세 벡터를 사전에 정했지만
첫 mismatch에서 중단하라는 규칙이 우선한다. 새 solver·eigenvector·lowest energy·
Pachucki comparison도 **NOT_EXECUTED**다.

## 반례: 두 상태와 흡수 후 K의 세 성분

[원래 반례](h2_ci_layer_audit_v0/evidence/counterexample.json),
[exact trace·세 K 성분 축소](h2_ci_layer_audit_v0/evidence/counterexample_reduction.json).

**bra=(39,50) singlet, ket=(50,50) closed state**.

| 계산 | matrix/action component |
|---|---:|
| existing direct-pair | −4.231303534059128 |
| independent raw-MO Slater–Condon | −4.231303534059129 |
| prior absorbed/packed PySCF action | −4.231297967351358 |
| difference | **+5.566707771187396e-6** |

독립 값의 1전자 기여는 −4.2034413444287914, Coulomb와 exchange 전자선 분해는
각각 −0.013931094815168781이다. 이 off-diagonal의 명칭은 determinant 전자선의
uncrossed/crossed 항을 뜻한다. 별도의 두 물리 observable이라고 해석하지 않는다.
모든 항·부호·정규화는 JSON에 보존했다. 이 원소의 단순화된 raw-MO 식은

`sqrt2*h[39,50] + (g[39,50,50,50]+g[50,50,39,50])/sqrt2`다.

MO pair 불일치가 있는 상태에서 `T[j,k]=sum_i g[j,i,i,k]`는 비대칭이다.
설치된 PySCF는 `f=(h−T/2)/2`를 만들어 ERI에 넣은 뒤 fourfold 형식으로 pack한다.
[공식 PySCF source](https://pyscf.org/_modules/pyscf/fci/direct_spin1.html)와
설치 source/library hash 및 실제 함수 본문을 별도 기록했다.

이 반례에서 저장 raw-MO를 exact dyadic으로 합하면

- T[39,50] = −0.14603262077716184
- T[50,39] = −0.1460404932907875
- difference = **18152780508729 / 2305843009213693952 ≈ 7.872513625686601e-6**.

흡수 전 raw h는 대칭이지만 f[39,50]와 f[50,39]는 다르다.
Fourfold storage가 lower representative를 재사용하여 다음 세 K 값을 바꾼다.

| K indices | uncompressed | packed | singlet numerator coefficient |
|---|---:|---:|---:|
| (39,39,39,50) | −0.7419690122063146 | −0.7419680281421114 | 2 |
| (39,50,50,50) | −0.7346679057206719 | −0.7346669216564686 | 4 |
| (50,50,39,50) | −0.734666421794103 | −0.7346654377298998 | 2 |

각 변화는 **4431831179 / 4503599627370496 ≈ 9.840642032354907e-7**이며,
coefficient 합 8과 sqrt2 denominator로 observed action 변화를 재현한다.
raw trace로 예측한 `2*sqrt2*(T[39,50]−T[50,39])/4`는
**5.566707769706489e-6**, 실제와 차이는 **1.4809e-15**다.

생성·소멸 연산으로 별도 평가한 **uncompressed K E·E**는 raw SC와 차이 0,
**packed K E·E**는 실제 PySCF action과 차이 8.8818e-16이다.
따라서 이 반례에서는 sign·sqrt2·state index·ERI convention mismatch가 아니라
**비대칭 absorbed intermediate를 within-pair packed 형식으로 표현한 정보 손실**이
최초 원인이다. PySCF 일반 오류라는 주장이 아니다. 입력 symmetry와 적용 조건 문제다.
Uncompressed K를 새 accepted solve에 넣거나 원래 evaluator를 수정하지 않았다.

## 비용·실패·시험·보존

- MO 재현/저장/실행 봉인 준비 구간: **2.81526074 s**.
- 첫 full-output column 비교/action: **1.57437033 s**.
- 반례 exact trace reduction: **0.00389630 s**.
- 원본 Git/hash 봉인과 전후 재검사를 포함한 전체: **164.35056902 s wall / 17.850031 s CPU**.
- worker peak RSS **440602624 bytes / 420.19140625 MiB**. 원본 hash/MO/흡수 중간값을
  포함한 프로세스 전체 값이며 CI solver peak라고 주장하지 않는다.
- summary의 audit seconds 51.4604는 내부 byte 재검사를 포함한다. A/B individual kernel
  timing은 따로 측정하지 않았다. 164초를 150초 candidate eigensolve와 같은 비용으로
  해석하지 않는다. 이번 eigensolver call은 0이다.

유효한 연구 접근은 **1개**다. 첫 physical action 반례가 나와 STOP했다.
준비/기록 실수는 별도 보존했다: Windows resource import, synthetic fault에 민감하지
않은 최초 시험 column, postprocessor cp949 decode, 최종 증거 시험의 Linux/Windows
path 변환, Windows에서 PySCF 의존 시험을 실행한 환경 선택. 물리 audit는 **1회**였고
이 실수들 때문에 source/protocol/MO/threshold를 결과 후 맞추거나 physical run을
반복하지 않았다. 이전 실패 로그와 새 첫 실패 모두 보존한다.

최종 관련 검증:

- **Windows 123 passed / 3.01 s**, failure/error/skip0.
- **WSL 126 passed / 10.05 s**, failure/error/skip0. PySCF 의존 기존 시험과 신규 synthetic
  integration은 WSL에서 실행했다. 두 플랫폼 시험 숫자를 합산하지 않는다.
- 신규 operator/semantic 17, evidence 10, WSL-only synthetic integration 2.
- Canonical mapping duplicate/missing/spin/norm, fermion anticommutation/Pauli, manual
  first-quantized wavefunction 교차 대조, sign/norm/input/action 결함 주입, byte drift,
  STOP/eigensolver 미실행 및 기존 Gate hash를 확인했다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 독립 분석·시험·문서만 추가했고
기존 실행 code/common/frozen contract/fixture와 guards/canonical source를 수정하지
않았다. 공식 FULL 기준선은 갱신하지 않는다.
기존 source/evidence **235**, 이전 raw **665(원래646+직전 cause19)**, 새 봉인 source8,
입력/저장 MO bytes를 포함한 **910개 binding**이 실행 후 불변이었다.
Large MO arrays는 Git 밖 원본 run에 남고 compact evidence·해시·원소·전체 action outputs를
commit에 보존한다. 배열 없이 compact 요약만으로 모든 MO 정확성을 재검증할 수는 없다.
추가 validation log/manifest는 evidence README에 있다.

구상 일치성도 별도 확인했다. 같은 물리 문제와 같은 저장 입력을 비교했고,
기존 실패를 고치거나 energy를 맞추는 실험을 하지 않았다. R=0.6/0.7/0.8 및 QZ44 재실행,
force/dynamics/formation/world/production/GPU/Vast 작업은 0이다. commit 가능 / push 없음.

## 분류와 다음 설계자 결정

| 대상 | 판정 |
|---|---|
| basis 의미 대응 | MATCH, mapping mismatch 증거 없음 |
| original direct-pair vs independent raw SC | **CI_LAYER_EQUIVALENCE_SUPPORTED**, 검사 원소/12×12/1 column 한정 |
| prior determinant candidate action | **CI_CONSTRUCTION_MISMATCH_CONFIRMED**, 위 한 반례와19 action component |
| eigensolver layer | 미실행, EIGENSOLVER_LAYER_SUSPECTED 판정 근거 없음 |
| R=0.4 physical/reference 원인 | **UNRESOLVED** |
| MO pair interchange, 전체 solver/integral | **UNRESOLVED / NOT CERTIFIED** |
| QZ44 / production | **NUMERICAL FAIL / NOT APPROVED**, 기존 기록 유지 |

**DESIGNER DECISION REQUIRED.** 이번 반례의 보존과 원인 분리를 완료했다.
다음 가장 싼 단계의 후보는 이 입력에서 raw physical CI를 보존하는 determinant action
사양을 먼저 정하고, 같은 한 반례와 사전 고정 sparse/mixed-sign vector만 재감사하는
것이다. 반례를 통과시키기 위해 integral 대표 규칙·guard를 바꾸는 방향은 아니다.
그 사양/수정은 아직 구현하지 않았다. CI action 동등성이 확보되기 전에는 동일-matrix
dense eigensolver나 다른 R로 넘어가지 않는다.
