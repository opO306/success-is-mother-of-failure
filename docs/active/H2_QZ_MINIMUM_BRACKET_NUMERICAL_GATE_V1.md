# H₂ QZ Minimum-Bracket Numerical Gate V1

2026-10-04. **PARTIAL / R=1.3 UNSUPPORTED / MINIMUM BRACKET UNRESOLVED / NOT CERTIFIED.**

R=1.3의 신뢰 가능한 에너지를 확보하지 못했다. 새 독립 AO 경로는 기존 accepted controls와
두 좌표에서 모두 일치했지만, 두 R=1.3 시도는 원래 Hermiticity 검사에서 거부됐다.
고정밀 AO evaluator는 **NOT IMPLEMENTED / NOT EVALUATED**다.
기존 DZ/TZ energy well과 QZ supported subset의 증거는 보존한다.
이번 결과는 foundation 전체 실패, QZ minimum PASS, production 승인이 아니다.

## START GIT STATE

시작 checkout: master `0f7b744cf754450424a63c47f305e0327c5b37c1`, dirty 0.
2026-10-04 live `git ls-remote`의 origin/master도 같은 SHA였다.
요청한 freeze `24ee72e336b2c8faef6b4dadbd155a98ba68b3b4`에서 새 managed worktree와
`codex/h2-qz-minimum-bracket-v1` branch를 만들었다.

AGENTS/RULES는 전체 읽었다. CURRENT_STATE/REPO_MAP는 활성 상태, H₂ 경로와 검증
범위를 읽었으며 긴 C1-B1 역사·무관한 목록은 부분 확인이다. 기존 H₂ pilot 사양,
numerical-cause 보고서/사양, 관련 solver/core/HP diagnostic 소스, docs 안내/분류표를
읽었다. 저장소/runs 전체 감사나 기존 전체 curve 재실행은 하지 않았다.

## WHY THIS GATE IS NECESSARY

기존 fresh QZ 44점은 34 accepted / 10 refused였다. 가장 낮은 supported 값 R=1.4는
왼쪽 support 경계이므로 R=1.3 없이 sampled local minimum의 양쪽 이웃을 확인할 수
없었다. 이번 질문은 같은 finite-basis 문제의 1.3/1.4/1.5 bracket뿐이다.
전체 44점, short-R stress, dynamics, 새로운 world law는 범위에 넣지 않았다.

## INDEPENDENT BACKEND / PRECISION METHOD

Candidate A: 로컬 WSL Ubuntu 24.04의 **Psi4 1.3.2 / Libint 1.2.1**.
실제 `ldd`의 `libint.so.1` linkage와 Ubuntu package version을 봉인했다.
기존 PySCF 2.12.1/libcint와 다른 AO 생성 경로다. 이 시스템 package는 최신
Psi4/Libint2 비교가 아니며 다른 버전·모든 backend의 지원 여부를 판단하지 않는다.

fixed nuclei, isolated nonrelativistic Coulomb, 전자 2, charge 0, full spatial singlet,
standard spherical contracted cc-pVQZ, `EBO=Ee+1/R`를 유지했다.
두 H의 모든 shell에 대해 primitive 지수와 **원래 입력 contraction 계수**가
historical seal의 cc-pVQZ와 정확히 일치했다. AO 60개와 singlet 1,830개를 유지했다.
AO 순서/실수 spherical convention은 backend마다 달라도 전체 span을 유지한다.
[Psi4의 basis 형식·spherical 지원](https://psicode.org/psi4manual/1.3.2/basissets.html),
[MintsHelper AO API](https://psicode.org/psi4manual/1.2.1/api/psi4.core.mintshelper).

AO integral은 **새 독립 binary64 값**이다. 변환은 전체 tensor를 WSL longdouble
(64 significand bits)로 순차 수축했다. singlet matrix는 historical solver를 import하지
않는 별도 ordered-pair 식으로 만들었다. LAPACK evr의 lowest two numerical roots는
binary64다. SCF, occupancy truncation, reference energy/알려진 결합길이 힌트가 없다.
AO·변환 ERI·행렬에 평균 대칭화를 하지 않았다. longdouble/MPFR는 AO 자체를
고정밀로 재계산한 것이 아니며 certified rounding/enclosure가 아니다.

첫 후보는 full Cholesky 좌표였다. 거부 뒤 새 사양을 봉인해 **모든 generalized-h
eigenvector 60개**를 유지하는 두 번째 후보를 확인했다. 각 후보는 자기 control을
먼저 통과한 뒤 같은 source/protocol로 R=1.3을 실행했다. 각 실행 당시 source
snapshot은 seal과 일치한다. 최종 실행 source는 두 번째 후보와 일치하고 첫 후보
snapshot은 별도로 보존한다. 결과를 본 뒤 tolerance를 바꾸거나 거부 행렬의 에너지를
꺼내지 않았다.

Candidate B feasibility: [Libint의 공식 build 설정](https://github.com/evaleev/libint/blob/master/INSTALL.md)
에는 custom real type 경로가 있고 [engine의 별도 reference evaluator 분기](https://github.com/evaleev/libint/blob/master/include/libint2/engine.h)
도 있다. 고정밀 AO가 근본적으로 불가능하거나 소스가 없다고 주장하지 않는다.
그러나 설치된 Psi4/Libint1의 AO는 binary64다. 실제 고정밀 AO 경로에는 별도 build와
normalization/spherical shell/full-span 검증 및 같은 controls가 필요하다.
이번 실행에서는 그 경로를 build·구현·검증하지 않았다. 계산 시간/개발 기간의 수치
견적도 측정하지 않았다. 3회 실패 중단 규칙을 보수적으로 적용해 추가 해결 시도를
멈췄으며, foundation의 구조적 질문보다 큰 integral-engine 작업으로 확장하지 않는
판단으로 **PARTIAL**을 남긴다. B의 미실행을 수치 실패나 불가능성으로 세지 않는다.

## CONTROL EQUIVALENCE

실행 전 same-problem energy `1e-9 hartree`, overlap spectrum `1e-10` absolute,
nuclear repulsion `1e-15 hartree`를 봉인했다. 기존 overlap floor `1e-10`,
orthogonality operator norm `1e-10`, Hermiticity `1e-10`, eigen residual `1e-9`,
vector norm error `1e-10`을 유지했다. h/ERI 진단에도 같은 Hermiticity 기준을 적용했다.

각 후보의 QZ R=1.5/2/20은 **3/3 accepted**. 최종 generalized-h 후보:

| R (bohr) | Ee (hartree) | 1/R | EBO | 기존 accepted 값과 절대 차이 |
|---:|---:|---:|---:|---:|
| 1.5 | -1.8388684460381204 | 0.6666666666666666 | -1.1722017793714539 | 8.52207194e-13 |
| 2.0 | -1.637507696620721 | 0.5 | -1.137507696620721 | 1.88293825e-13 |
| 20 | -1.0498911934800135 | 0.05 | -0.9998911934800134 | 3.99680289e-15 |

Cholesky의 최대 energy 차이는 1.82964754e-13, 두 후보 전체 overlap spectrum
최대 차이는 7.10542736e-15다. full basis/sector/geometry/charge와 nuclear repulsion을
checker가 별도 확인했다. 전체 domain 동등성 인증이나 외부 감사 승인은 아니다.

## R=1.3 RESULT

두 시도 모두 **REFUSED: singlet_hermiticity**. Ee/EBO/residual은 null이며 eigensolve를
하지 않았다. Smin 2.1541278620031297e-4, condition 23846.12604는 두 좌표에서 같다.
raw AO S/h 비대칭은 0, ERI ij/kl permutation 최대 9.06236891e-14,
pair permutation 최대 1.07362036e-14다.

| 진단 | Cholesky | generalized-h |
|---|---:|---:|
| ||CᵀSC−I||₂ | 1.87497204e-13 | 1.86741069e-13 |
| transformed h max asymmetry | 1.34820540e-16 | 2.70732906e-16 |
| transformed ERI ij max | 9.17311058e-11 | 8.15148997e-11 |
| transformed ERI kl max | 9.79280793e-11 | 8.30628651e-11 |
| transformed ERI pair max | 7.47796409e-11 | 7.30124812e-11 |
| singlet Hamiltonian max asymmetry | **1.72547134e-10** | **1.29630400e-10** |
| eigen residual / Ee / EBO | NOT EVALUATED / null / null | NOT EVALUATED / null / null |

## R=1.3 / 1.4 / 1.5 MINIMUM BRACKET

**UNRESOLVED.** 새 R=1.3 energy가 없다. R=1.4는 첫 필수 점의 실패 때문에 이번
candidate에서 실행하지 않았다. R=1.5는 control로 fresh accepted다.
기존 R=1.4 EBO=-1.1737957922495874를 새 독립 삼점 계산에 삽입하지 않았다.
따라서 `E(1.4)<E(1.3) AND E(1.4)<E(1.5)`를 확인했다고 보고하지 않는다.
거부는 물리적 H₂ 부재가 아니라 이번 수치 경로의 지원 실패다.

## NUMERICAL FAILURE CLASSIFICATION

입력을 바꾸지 않고 거부된 대표 coupling을 저장 행렬에서 찾았다. 별도로 시험했던
historical MPFR scalar diagnostic을 다른 계산식으로 재사용해, 새 independent AO와
고정 C의 antisymmetric component를 60/80 decimal digits(231/297 bits)로 수축했다.
world/solver에 넣는 보정도 energy 계산도 없다.

| 대표 coupling | 저장 행렬의 부호 있는 비대칭 | AO에서 전파된 성분(80자리) | 잔여 성분 |
|---|---:|---:|---:|
| Cholesky (40,40)/(48,53) | +1.72547134e-10 | +1.72467266e-10 | +7.98678729e-14 |
| generalized-h (10,23)/(23,59) | -1.29630525e-10 | -1.29585084e-10 | -4.54408443e-14 |

60→80자리에서도 AO 성분은 표시 정밀도 안에서 같으며 각 대표 성분 자체가 1e-10을
넘는다. 이 두 coupling에서는 **독립 binary64 AO의 비대칭 성분이 주된 원인**이다.
같은 AO를 고정밀 type으로 옮기는 것만으로 그 성분을 고치지 못한다.
generalized-h의 Coulomb-only scan과 candidate 전체 행렬 scan 사이에는 약1.3e-16의
반올림 차이가 있으며 기록에 남겼다.

현재 분류는 backend/산술/condition에 따른 수치 지원 문제다. H₂의 물리적 부재나
Hamiltonian 변경이 필요하다는 증거가 아니다. PySCF/libcint 하나에만 고유한 문제라는
설명도 이번 독립 경로에는 충분하지 않다. 다만 전체 AO의 정확도 상한, 전체 행렬 norm
bound, 모든 binary64 좌표의 불가능성, 모든 Libint version의 결함을 증명하지 않았다.

## COST / SCALING

로컬 WSL CPU, threads 1, Vast/GPU 0. 8 fresh workers = controls 6 accepted +
target 2 refused. 네 stage wall 합172.520105초, worker CPU 합160.825502초다.
scalar MP 진단은48.611917초. 설치·시험·문서·hash 검사·준비 실패와 postrun product-action
검사의 전체 작업 시간은 이 stage wall에 포함하지 않는다. fresh worker 최대RSS는
**788.8828125 MiB**, 새 raw 증거는 약626 MiB다.

Ubuntu 의존 환경은28 package 추가, upgrade 0. apt는51.9 MB download /264 MB 추가
disk를 보고했다. 오래된 package의 SyntaxWarning은 install log에 보존했다.
AO entries M⁴=12,960,000, singlet D=1,830, longdouble transformed ERI 207,360,000
bytes, singlet matrix 53,582,400 bytes다. direct solve이므로 iteration count=null.
다전자·다원자·dynamics의 cost/scaling은 미실측이며 성능 최적화를 하지 않았다.

Windows **72 passed /1.15초**, 별도 WSL **78 passed /5.71초**.
각 failure/error/actual skip 0. 신규 시험29개이며 같은 시험의 양쪽 실행을 합산하지 않는다.
full-span/ordered-product 대조, basis/sector/charge/dimension/비유한값/residual/비대칭,
controls energy/spectrum 변조·누락·중복, bracket 미성립을 검사했다.
저장된6 accepted vector는 singlet matrix를 재사용하지 않는 full-product Hamiltonian
작용식으로 별도 확인했다. 최대 residual 4.38142877e-14, 모든 NPZ hash 일치,
거부2건의 null energy 유지. 저장 AO를 공유하는 작성자 검사이며 외부 AO 감사는 아니다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 isolated reference/postrun 코드,
새 시험과 문서만 추가했다. 기존 runtime/frozen contract/production selector는 불변이며
기존 source/compact evidence **89개**와 historical raw **410개**의 불변을 확인했다.
공식 통합 Gate 종료나 기준선 갱신으로 취급하지 않고 AGENTS의 LOCAL FULL 숫자를 유지한다.

실패 보존: 첫 startup은 WSL Git이 Windows worktree gitdir을 해석하지 못해 물리 계산0,
seal 작성 전에 멈췄다. host Git receipt로 수정하고 로그/주석을 보존했다. 뒤의 두
R=1.3 numerical refusal을 포함한 범위에서 추가 solver 시도를 종료했다.
별도로 packaging 첫 실행의 cp949/UTF-8 decode 오류가 있었다. 실패한 packaging 소스와
주석을 보존하고 UTF-8 읽기만 고친 새 compact folder로 출력했다. 물리 재실행0이다.
첫 raw manifest에는 작성 중이던 packaging stdout log의 중간 hash가 있었다.
검사에서 그 log 하나의 차이를 확인해 원래 목록을 보존하고, 모든 writer가 끝난 뒤
별도 `raw_manifest_closed_v3.json`을 만들었다. 최종83개 raw file의 hash가 모두 일치한다.
Gate source/compact evidence의 Git 줄바꿈 변환은 해당 새 폴더의 `.gitattributes`로 막았다.

## WHAT THIS PROVES

새 독립 AO와 기존 accepted QZ controls의 같은 finite-basis 표본 일치, 전체 차원 유지,
기존 검사 기준의 fail-closed 동작과 실패 보존을 확인했다. 독립 AO에도 작은 permutation
차이가 있고, 이번 R=1.3 대표 coupling에서는 전파 성분 자체가 검사 기준을 넘는다.
기존 DZ/TZ well·QZ supported subset 증거는 보존했다. DZ/TZ curve나 Pachucki reference를
이번에 새로 계산한 것은 아니다.

구상 일치성 2차 검토는 작성자의 source/input/evidence 별도 점검이다. bond/reaction/molecule
rule, HF/DFT/ML 대체, basis 삭제, 평균 대칭화, 기준 완화, energy hint, world 통합이 없다.
새 AO 입력과 고정밀 scalar 진단을 구분하고, 거부한 R=1.3 energy를 후속 판정에 넘기지 않았다.

## WHAT THIS DOES NOT PROVE

QZ 삼점 minimum, 44점 curve/P3 완료, 연속/continuum exact minimum, 실제 분자의 완전한
결합길이, 안정 capture/formation/dynamics, 생명·화학 전체, production foundation,
formal certificate나 독립 외부 감사 승인을 증명하지 않는다.
유한 basis 오차, fixed nuclei/비상대론/고립 Hamiltonian의 model 오차, solver residual,
AO/산술 오차, reference 오차를 별도 장부로 남겼다. B 미실행을 성공이나 불가능성으로 세지 않는다.

## NEXT FOUNDATION GATE

**Electronic Sector Panel V1**: atomic H, H₂⁺, H₂ singlet, H₂ triplet.
이번 설계자 지시에 따라 QZ short-R를 UNSUPPORTED로 격리하고 H₂ static pilot의
구조적 질문을 PARTIAL로 닫아 다음 비교로 진행할 근거는 있다. QZ minimum 수치 Gate를
PASS로 보고할 근거는 없다. 다음 panel과 dynamics는 이번에 실행하지 않았다.
고정밀 AO는 같은 basis의 정밀 reference가 별도 목적에 필요해질 때의 제한된 후보로 남긴다.

## GIT END STATE

`codex/h2-qz-minimum-bracket-v1`의 새 worktree에 보존한다. mainline master와 remote master
변경, merge/push는 없다. 새 code/tests/report/compact 증거를 local commit으로 저장하며
최종SHA는 종료 Git receipt와 채팅에 적는다.
Git 밖 NPZ는 attached worktree의 `runs/h2_qz_minimum_bracket_v1_20261004/`에 보존한다.
checkout을 archive하려면 먼저 별도 보관이 필요하다. preflight에서 생성한 timer.dat도
새 raw folder에 보존해 원래 master에 dirty를 남기지 않았다.

[결과·오차/비용/미실행 장부](h2_qz_minimum_bracket_v1/complete_v2/summary.json),
[source·입력·로그와 최종 raw hash 목록](h2_qz_minimum_bracket_v1/complete_v2/raw_manifest_closed_v3.json).
compact에는 control/target seal, 실행 source snapshot, 거부, postrun 기록과 시험 log/XML이 있다.

## 설계자에게 드리는 7개 답

1. **R=1.3을 신뢰 가능하게 계산했는가:** 아니요. 두 번 모두 거부됐으며 energy가 없다.
2. **accepted QZ controls와 독립 경로가 일치했는가:** 예. 각 경로1.5/2/20의 세 점 모두 같은 기준으로 일치했다.
3. **R=1.4 sampled minimum을 확인했는가:** 아니요. 왼쪽 이웃 energy가 없어 bracket이 성립하지 않았다.
4. **물리 모델인가, numerical backend인가:** 확인한 문제는 수치 지원/산술/condition이다. 물리적 부재의 증거가 아니다.
5. **44점을 더 계산해야 하는가:** 현재 foundation 구조 질문에는 필요하지 않다. 이전 full-curve/P3는 미완료로 보존한다.
6. **H₂ static pilot을 닫을 수 있는가:** 구조적 feasibility pilot은 PARTIAL·QZ short-R UNSUPPORTED를 명시하고 닫을 수 있다. minimum PASS나 foundation 승인은 아니다.
7. **Electronic Sector Panel로 넘어갈 수 있는가:** 예. 이번 격리 조건에 따라 다음 물리 질문으로 진행할 것을 제안한다. 이번에는 그 panel을 시작하지 않았다.

검토 절차 출처: scientific-critical-thinking 스킬을 control 설계와 주장 범위 확인에 사용했다.
Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026).
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
2026-10-04 공식 arXiv record에서 저자·연도·최신 revision을 확인했다. 수치 결과의 승인 기관은 아니다.
