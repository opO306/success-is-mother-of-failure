# H₂ Representation Pilot 1 — B1 R=.4 Symmetric James–Coolidge V1

2026-10-04 / R=.4 한 점, 세 표현 크기에서 STOP. **NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.**

**한계부터:** NMAX/NDIGITS 변화와 세 포함 기저의 에너지 감소는 이번 점의 empirical numerical evidence다. 연속 Coulomb ground energy의 formal error bound, 전체 H2SOLV 인증, 외부기관 감사, A 채택, 다전자·시간 동역학 효율을 뜻하지 않는다. 자체 MEDIUM 검색은 7개 평가의 제한된 검색이며 최적 u를 증명하지 않는다. Gaussian과 JC의 검증 부하는 다르다. 전체 목표 확보 절차는 이번 fresh V5Z보다 느렸다.

## GIT STATE

- 작업 위치: `C:/Users/zun24/.codex/worktrees/h2-representation-pilot1/성공은 실패의 어머니`.
- 시작 HEAD `1503b6765b2f8db595200b3dc4725c879eead812`, branch `codex/h2-representation-pilot1`.
- Live remote master `0f7b744cf754450424a63c47f305e0327c5b37c1`, Pilot `264f5880ee1dedd5a97b008c29dd8d67057664b9`; 시작 ahead4/behind0, dirty0/untracked0. 새 파일 작성 후 prepare 시점 상태도 [git_start.json](evidence/git_start.json)에 별도 기록.
- 자동 merge/rebase/fetch/push 없음. 로컬 commit 허용 범위. 최종 commit/byte 검사는 별도 Git receipt.

## TARGET CONTRACT

H₂, ZA=ZB=1, 2 electrons, nominal R=.4 bohr, clamped nuclei, nonrelativistic Coulomb, atomic units, singlet gerade ¹Σg⁺. x=y=0, u=w>0 symmetric JC subset. HAM에 이미 ZA*ZB/R가 들어 있으므로 +1/R 재가산 0. R는 원본 REAL*16 입력 경유의 수치 표현이며 exact rational .4 Hamiltonian 인증이 아니다.

## JC ASYMMETRIC SEMANTICS CHECK

공식 asymmetric input 전체·README·CALCEN/EN comment를 좁게 확인했다. 입력 EN=-.6908이며 source는 EN을 desired eigenvalue 근사로 설명한다. 해당 예제를 ground/excited라고 명시하는 문구는 찾지 못했다. **JC_ASYMMETRIC_INTENDED_ROOT_UNRESOLVED**. 이전 반환 E 주변 inertia1→2는 보존하고 solver failure로 자동 승격하지 않는다. 설계자 변경에 따라 all5 lowest 요구는 이번 target의 선행 Gate에서 제외한다. 이전 보고/봉인 byte는 그대로 보존.

## BASIS SIZE ENUMERATION

에너지 실행 전 자체 조합 열거와 원본 계산 직전 DT export/STOP copy를 모든 tuple·순서까지 대조했다. Source restriction1=1(n2+n3 even), restriction2=1(n2>n3 또는 n2=n3,n4>=n5); sum powers<=Ω.

| Ω | Dimension | Native tuple/order match | Energy before selection |
|---:|---:|---|---|
| 1 | 3 | PASS | 0 |
| 2 | 9 | PASS | 0 |
| 3 | 20 | PASS | 0 |
| 4 | 42 | PASS | 0 |
| 5 | 78 | PASS | 0 |
| 6 | 138 | PASS | 0 |
| 7 | 228 | PASS | 0 |
| 8 | 363 | PASS | 0 |
| 9 | 553 | PASS | 0 |

## SEALED SMALL/MEDIUM/LARGE

| Size | Ω | Dimension | 선택 이유 |
|---|---:|---:|---|
| SMALL | 3 | 20 | 저차·저비용 |
| MEDIUM | 5 | 78 | 중간 크기에서 두 수치 축과 u 검색 |
| LARGE | 7 | 228 | 과거 practical vendor JC 차원과 동일한 제한 규모 |

공통 u=1로 degree-prefix tuple sets가 실제 포함 관계다. Ω8/9는 열거만, 에너지 0. Ω>7/R≠.4 계산 0.

## OPTIMIZER CONTRACT

결과 전 generic seed1, bounds[.5,1.5], MEDIUM 자체 accepted finite energy 목적 함수, pattern steps1/4→1/8→1/16, 양쪽 이웃 모두 평가·동률 작은 u, max7(재사용한 calibration seed 포함), 3단계 뒤 종료로 봉인. 문헌 seed/기준값 fitting/결과 후 범위 변경/Ω별 hand tuning 없음. 보정에서 선택된 NMAX80/ND60 사용. 하나의 u를 모든 크기에 옮긴다.

| u | own E (Eh) | 실행 |
|---:|---:|---|
| 1 | -0.1202282478897024 | cal_n80d60_try0 (calibration 재사용) |
| 0.75 | -0.1202167042995405 | opt_1_try0  |
| 1.25 | -0.1201462875787990 | opt_2_try0  |
| 0.875 | -0.1202257519770730 | opt_3_try0  |
| 1.125 | -0.1202203690874457 | opt_4_try0  |
| 0.9375 | -0.1202275454298635 | opt_5_try0  |
| 1.0625 | -0.1202270074565913 | opt_6_try0  |

선택 u=w=1.0. 추가 검색 wall 36.272s; seed의 원래 평가 비용은 calibration에 한 번만 계상. **BOUNDED_SEARCH_COMPLETED_NO_OPTIMALITY_CERTIFICATE**.

EN은 초기−2, 이후 latest accepted own E−1/256. 점별 최대 retry1이며 거부된 자신의 finite 반환 E−1/256을 hint로만 쓴다. MAXIT energy는 물리 비교에 넣지 않는다. 기존 ITMAX40·수렴 조건 변경0.

## NUMERICAL CALIBRATION

MEDIUM Ω5,u1에서 NMAX60/80/100/120 at ND60; NMAX120 고정 ND60/80. Integral MPIPL80(384bit) 불변; 실제 H/S ND60=320bit, ND80=384bit, returned E/v384bit. 에너지 변화<=1e−10 Eh는 empirical Pilot threshold이며 formal error bound 아님.

| 변경 축 | ΔE (Eh) |
|---|---:|
| n60d60_to_n80d60 | -1.61145e-58 |
| n80d60_to_n100d60 | -2.21306e-89 |
| n100d60_to_n120d60 | 0 |
| n120d60_to_n120d80 | 7.85718e-98 |

봉인된 선택 규칙으로 NMAX80/NDIGITS60 결정. ND80 실행과 NMAX120 비교 모두 accepted; 사후 checker tolerance 변경0. Seed u=1이 검색에서도 선택돼 동일 u 보정이 직접 적용된다.

## R=.4 B1 SMALL / MEDIUM / LARGE

| Size | Ω/N | u | NMAX/ND | E (Eh) | Iterations | Stored S | Returned-root inertia |
|---|---|---:|---|---:|---:|---|---|
| SMALL | 3/20 | 1.0 | 80/60 | -0.1200992227076850 | 28 | SPD | 0→1 |
| MEDIUM | 5/78 | 1.0 | 80/60 | -0.1202282478897024 | 29 | SPD | 0→1 |
| LARGE | 7/228 | 1.0 | 80/60 | -0.1202300965806720 | 28 | SPD | 0→1 |

각 점은 실제 EIGENVALUE_TEST 종료, MAXIT false, factor/solve error 0, 양의 metric 하한, 독립 initial EN inertia=WA1, 반환 E를 포함하는 lowest enclosure, 독립 residual/RQ의 기존 4가지 일관성 검사를 모두 통과했다. Accepted calibration/optimizer/final/spot 17개 실행도 같은 검사를 받았다. 아래 증거는 측정·저장된 유한 문제에 한정된다.

| Size | S λmin lower bound | Raw residual L2 | abs(nS−1) | RQ−E | ρ=√(rᵀS⁻¹r/nS) |
|---|---:|---:|---:|---:|---:|
| SMALL | 5.87997e-14 | 1.39207e-64 | 7.85229e-116 | 1.04654e-66 | 1.06567e-66 |
| MEDIUM | 8.80747e-28 | 8.02244e-63 | 1.26762e-117 | 5.92419e-67 | 6.06071e-67 |
| LARGE | 1.4052e-47 | 1.94444e-57 | 2.82927e-115 | -6.60118e-65 | 3.63258e-64 |

nS는 위 측정 오차 안에서 1이다. E_RQ·nS의 180자리 값, exact E pair, 각 root endpoint pair는 [실행 증거](evidence/runs/)에 저장했다. Raw/metric residual은 기존 V1의 MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD이며 물리 정확도의 상한은 아니다. 새 허용오차 없이 RQ inside, Cauchy consistency, residual spectral interval overlap, ρ interval containment의 기존 네 조건을 그대로 판정했다.

| Size | lowest enclosure [low, high] (Eh) | Width | E inside |
|---|---|---:|---|
| SMALL | [-0.1200992227076849610716429803312600547461756229879588734665758416430192161777074223511, -0.1200992227076849610710077056208193294918743811124491419950372979418473411777074223511] | 6.35275e-22 | true |
| MEDIUM | [-0.1202282478897023901054318104259723537545207851227203450845884807912008569410057657982, -0.1202282478897023901047965357155316285002195432472106136130499370900289819410057657982] | 6.35275e-22 | true |
| LARGE | [-0.1202300965806720097141827241249421378291598518364264438951787439501176103749691678339, -0.1202300965806720097135474494145014125748586099609167124236402002489457353749691678339] | 6.35275e-22 | true |

Stored H/S는 원본 invsg 호출 직전에 포착한 lower packed values를 exact dyadic으로 복원하고 대칭으로 배치한 것이다. 독립 upper triangle을 새로 내보내지는 않았다. SPD/lowest bracket은 이 저장 유한 문제의 interval 결과이며 exact Coulomb integral이나 NMAX 절단 오차의 인증은 아니다. 원본 계산 경로는 해시와 추가 관측 코드를 제거한 바이트 대조로 보호했다.

V1 checker.py SHA256 `1bc5cfa1310d5fc11d91f43eb4a611d6abae5fc4db6a396c5d0632d88671bc8e`; interval binary SHA256 `39055b462107aa41f6532c9a96774c3c71bd48c36ca7a89a3aeb162652a34beb`. 정밀도 ladder 80/120/160/240 decimal digits, returned-E δ2^-64/bisection<=8/width<=2^-70, residual 240 digits를 변경 없이 사용했다. 원본 H2SOLV inverse iteration/LDL을 독립 검사기의 정답으로 쓰지 않았다.

## REPRESENTATION CONVERGENCE

- SMALL_to_MEDIUM: ΔE=-0.0001290251820174290337888300947122990083451621347614716180126391481816407632983434471539 Eh.
- MEDIUM_to_LARGE: ΔE=-0.000001848690969619608750913698969784074639066713706098810590263158916753433963402035699697 Eh.

같은 u·같은 제한을 가진 nested 세 점에서 단조 감소를 실측했다. **R04_JC_REPRESENTATION_CONVERGENCE_SUPPORTED**는 이 세 점의 진행에 한정된다. 무한 Ω 극한, 수렴 속도 정리, 기저 오차 상한은 증명하지 않았다.

## NUMERICAL SPOT CHECKS

| Size | Final NMAX→spot | Same u/ND | abs(ΔE) Eh | Criterion |
|---|---|---|---:|---|
| SMALL | 80→100 | true | 6.19953e-67 | <=1e-10 PASS |
| MEDIUM | 80→100 | true | 9.68755e-67 | <=1e-10 PASS |
| LARGE | 80→100 | true | 8.75811e-67 | <=1e-10 PASS |

**R04_JC_NUMERICAL_CONVERGENCE_SUPPORTED**: MEDIUM의 분리한 수치 축과 세 최종점의 higher NMAX spot이 지지한다. 형식적 오차 상한이나 전체 integral 식을 독립 재구현한 검증은 아니다.

## REFERENCE COMPARISON

모든 B1 energy/hash를 [energy_seal.json](evidence/energy_seal.json)에 먼저 봉인하고, 별도 compare.py에서만 설계자가 고정한 reference −.120230341178823과 비교했다. EN/optimizer/contract는 이 값을 import하거나 사용하지 않는다. 비교는 지정된 값과의 수치 차이며 reference 자체의 독립 불확실성 평가를 새로 실행한 결과는 아니다.

| Final size | abs(E−reference) Eh | .001 criterion |
|---|---:|---|
| SMALL | 0.000131118 | MET |
| MEDIUM | 2.09329e-06 | MET |
| LARGE | 2.44598e-07 | MET |

**R04_TARGET_ACCURACY_MET**. 처음 목표를 달성한 최종 표현은 SMALL(Ω3/N20)이다.

## GAUSSIAN QZ/V5Z COMPARISON

| Gaussian | Historical E | abs gap Eh | Role |
|---|---:|---:|---|
| QZ | −.11803113362157003 | .00219920755725297 | baseline/목표 미달 |
| V5Z | −.11959699456988826 | .00063334660893474 | 목표 비용 비교의 주대상 |

B1 봉인과 목표 달성 확인 뒤에만 V5Z를 새로 실행했다. AO110/full singlet6105, 물리·기존 basis definition·guards 불변, accepted/postcheck true, fresh E=-0.11959699456988826이다. 과거 에너지의 소스나 원본을 덮어쓰지 않았다. PySCF2.12.1/NumPy2.5.3/SciPy1.18.1, 1 thread. 새 V5Z 실행의 목적은 비용 측정이며 과거 strict symmetry/reference uncertainty 판정을 닫지 않는다.

## COST COMPARISON

같은 Windows 호스트의 WSL2 Ubuntu, 같은 GNU time+outer wall wrapper, OMP/OPENBLAS/MKL=1로 측정했다. 포착·검증 부하는 경로에 따라 다르다. JC native에는 observer 출력, Gaussian에는 AO export·기존 guards가 포함되어 순수 eigensolver 속도 비교가 아니다. Windows HP controller sampled RSS와 WSL native GNU peak는 별도 값이며 전 호스트의 동시 RSS는 아니다.

| Work | Native wall s | Native peak MiB | Controller/outer or total s |
|---|---:|---:|---:|
| JC final SMALL 1 capture | 0.79 | 45.375 | 2.487 incl independent validation |
| JC final MEDIUM 1 capture | 3.13 | 99.250 | 5.973 incl independent validation |
| JC final LARGE 1 capture | 8.59 | 194.625 | 31.882 incl independent validation |
| Fresh Gaussian V5Z incl existing guard/export | 29.91 | 3873.645 | 33.300 |
| JC 목표 확보까지(calibration/search/retry/SMALL/spot/vendor/checker) | — | 143.125(max WSL native) | 79.549 |
| JC 세 크기 전체 campaign | — | 238.000 | 168.569 |

SMALL 목표까지 controller sampled peak는 35.406 MiB, 전체 campaign 최대는 79.0 MiB였다. 이를 native peak와 합산해 실측 global peak라고 부르지 않는다.

전체 수치 절차의 first-target cost 79.549s / V5Z fresh 33.300s = 2.389배다. **이번 전체 절차에서 JC의 wall 우위는 지지되지 않는다.** SMALL 단일 native 비용과 메모리는 작지만, 검색·정밀도·검증 비용을 제외하고 우월성을 선언하지 않는다. 기존 Gaussian basis의 외부 설계 비용은 이번 fresh benchmark에 포함되지 않으며 반복 사용으로 비용을 나누는 효과도 측정하지 않았다.

### 비용 장부 — 중복 합산 금지

| 항목 | 초 | 범위 |
|---|---:|---|
| numerical calibration | 36.840 | 5accepted+1refused; native+validation |
| parameter optimization 추가 | 36.244 | 새 trial6개; seed는 calibration에 이미 계상 |
| native integral generation | 63.273 | 전체18attempt의 단계 내역, 위 wall에 포함 |
| matrix/allocation | 1.928 | 위 wall에 포함 |
| precision conversion/setup | 0.046 | 위 wall에 포함 |
| native matrix snapshot | 0.210 | 위 wall에 포함 |
| native eigensolve+branch/return observer | 1.641 | 위 wall에 포함 |
| independent validation | 82.736 | 전체18attempt, 각 wall에 포함 |
| higher numerical calibration overhead | 22.552 | NMAX100/120d60/120d80 평가wall, calibration에 이미 계상 |
| retry/failure cost | 2.610 | 첫 MAXIT40, calibration에 이미 계상 |
| fresh unmodified vendor comparisons | 12.723 | 세 final의 stdout/wf 동일 검사, campaign에 이미 계상 |
| observer / enumeration binary build | 13.227 | numerical campaign 밖의 준비, 두 copy 합계 |
| basis-only enumeration process wall | 1.221 | numerical campaign 밖, Ω1..9, energy0 |
| preflight tests | .380 | numerical campaign 밖, 24tests의 pytest 표시 시간 |

준비의 build/enum 실측과 preflight 표시 시간 합계 14.827s를 별도로 더하면 first-target94.377s다. 이는 확인한 일부 준비 비용의 합산이며 사람의 조사·보고 시간, pytest 시작 부하, Gaussian/MPFR의 과거 설치 비용까지 포함하는 전체 개발 비용은 아니다. Native phase clock은 원래 계산 줄을 보존한 추가 호출이며, unmodified vendor와의 차이를 solver 성능 향상으로 취급하지 않는다.

## FAILURES / REFUSALS

- 첫 pre-energy 준비에서 observer anchor의 원문 끝 공백을 빠뜨려 앵커 검사에 실패했다. 에너지 미실행 상태에서 수정하고 24개 synthetic preflight 뒤 재개했다. [준비 실패 기록](evidence/preparation_failure_1.json).
- cal_n60d60_try0: exit0/ierror0이어도 실제 MAXIT40 소진으로 REFUSED_ITERATION. Energy는 reference/optimizer의 accepted 값으로 쓰지 않고 봉인한 한 번의 retry 힌트에만 썼다. try1은 정상 수락됐다. 총18attempt, accepted17/refused1. Target SPD failure/nonlowest0.
- 두 copy build의 mpfr_root deprecated warning을 보존했다. 해결됐다고 보고하지 않는다.
- H–He+ S indefinite, General SPD unresolved, JC asymmetric nonlowest/intended semantics unresolved, vendor MAXIT silent behavior는 이번 성공으로 수정·삭제·덮어쓰지 않았다.

## WHAT IS SUPPORTED

- R04_JC_NUMERICAL_CONVERGENCE_SUPPORTED: 지정 medium ladder/세 spots, 경험적 증거.
- R04_JC_REPRESENTATION_CONVERGENCE_SUPPORTED: common-u nested 세 점의 실측 진행.
- R04_JC_LOWEST_ROOT_SUPPORTED: 전체 accepted stored finite problems.
- R04_TARGET_ACCURACY_MET / R04_SYMMETRIC_JC_PILOT_SUPPORTED: 이번 R=.4 범위.
- COST_COMPARISON_AVAILABLE: 동일 host/wrapper 실측, 검증 부하 차이 공개. 전체 절차의 wall 우위는 미지원.

## WHAT REMAINS UNRESOLVED

JC_ASYMMETRIC_INTENDED_ROOT_UNRESOLVED, 전체 H2SOLV anomaly 해소, Coulomb/integral/series/representation formal bounds, reference uncertainty, u 최적성, 외부 독립 감사, B2 clean-room, R1.4/6 및 곡선, A 채택, 다전자·시간 동역학 확장은 미해결이다. NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.

## TESTS / PROVENANCE / CONCEPT ALIGNMENT

새 contract 시험24개는 MAXIT/SPD/excited/outside/missing consistency/WA1/residual의 거짓 성공을 주입해 거부를 검사한다. 실제 capture evidence 시험6개와 기존 관련169개를 합쳐 **199 passed, failure/error/skip0, 19.15s**. [시험 로그](evidence/related_tests.log) / [JUnit](evidence/related_tests.xml). 첫23개 실행 이후 봉인 전에 guard 시험1개를 추가해 preflight는24개다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 기존 A/common/frozen code/fixture는 불변이며 새 isolated analysis wrapper/tests/docs만 추가했다. 공식 LOCAL FULL 기준선은 갱신하지 않았다. 새 실행을 과거 로그 확인만으로 대체하지 않았다.

이전 source/checker/proof/evidence **985 hash bindings**은 전후 불변이다. 원본20파일·제3자 archive·binary·raw matrices는 Git 밖에 있다. Protocol SHA `be1bc1db192ccda9b257fd3699974c00ff94e742208f96cc857cc53ae52fafe1`, B1 energy seal SHA `0ed28c36a061730c5fbff5ee2f1b28eac4932b94894f5589cc514eef264ee375`. 최종 raw inventory/compact evidence seal/Git receipt로 후속 결과와 시험을 보완한다.

읽은 범위: 최신 지시 첨부 전체, AGENTS/RULES, 공식 README/asymmetric input 전체, 현재 상태/REPO_MAP/doc index의 관련 항목, 원본 basis/restriction/HAM/HAMLNORM/CALCEN/invsg 관련 부분. 저장 checker/observer와 새 wrapper도 관련 구현을 읽었다. 원본 전체 적분 재귀의 독립 유도나 저장소 전체를 읽은 것은 아니다.

자동 시험과 별도로 [구상 일치성 대조](CONCEPT_ALIGNMENT.md)에서 설계와의 일치·근사·미구현·숨은 강제 조건을 평가했다. 독립 checker는 vendor와 별도 구현이지만 작성자 측 검증이며 새로운 외부 감사로 부르지 않는다.

## DESIGNER DECISION REQUIRED

이번 승인 범위는 완료하고 STOP했다. 다음 선택은 accepted finite problem을 기준으로 B2 독립 구현을 시작할지, 별도 승인한 R1.4/6 시험을 할지, 검색·검증 비용을 포함한 실용 비용 설계를 할지다. 이번 결과만으로 A/production을 채택하지 않는다. 추가 계산이나 push를 하지 않는다.

## METHODS / SOFTWARE REFERENCES

SPD metric과 generalized symmetric reduction의 수학적 배경은 [LAPACK Users’ Guide](https://www.netlib.org/lapack/lug/node54.html)에 있다. 이 설명은 구현한 interval/measurement의 증명 대체물이 아니다.

Scientific critical thinking skill을 사전 계약·측정/해석 분리·비용 비교의 혼동 요인 정리에 사용했다. 절차 출처: Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), 최신 arXiv 기록 v2(2026-09-02), 2026-10-04 실시간 확인. 이 인용은 H₂ 물리나 solver 정확성의 근거가 아니다.
