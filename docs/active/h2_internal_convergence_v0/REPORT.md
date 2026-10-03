# H2SOLV Internal Convergence Audit V0

2026-10-03. **종료 분기 관측·출력 불변5/5·실제 MAXIT fault detection 지원 / STOP.**

잔차·정규화·Rayleigh 값은 독립 계산했지만 사전 승인된 acceptance threshold가 없어
**MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD**다. Root selection과 integral truncation도
**UNRESOLVED**다. 전체 `H2SOLV_VENDOR_INTERNAL_SOLVER_CONVERGENCE_SUPPORTED`로
승격하지 않았다. **NOT_CERTIFIED / NOT_PRODUCTION_APPROVED**.
R=.4 실행0, B2 시작0, push0. 기존 QZ44 FAIL / same-basis reconstruction UNRESOLVED /
finite-basis limitation SUPPORTED UNDER CHECKED ASSUMPTIONS / MO ERI unresolved 유지.

## GIT STATE / 사전 봉인

시작 HEAD `1a3c1264f5e3e4cd1d5b52726e7d49e845606816`, branch
`codex/h2-representation-pilot1`, 시작 dirty/untracked0, 원격 Pilot보다 ahead2/behind0.
직접 조회한 origin/master `0f7b744cf754450424a63c47f305e0327c5b37c1`,
origin/Pilot `264f5880ee1dedd5a97b008c29dd8d67057664b9`.
[Git 기록](evidence/git_start.json)은 구현 전 clean 확인과 prepare 시 새 파일 상태를 구분한다.
Merge/rebase/fetch/push 없음. 원래 worktree·로컬 계보를 유지했다.

[실행 전 PLAN](PLAN.md), [protocol](evidence/protocol.json),
[protocol SHA256](evidence/protocol.sha256):
`b355f16226f32233b58b46312598abe6fe19e606c661c689271b3f3eeb7f2660`.
계약·구현11bindings와 과거 자료·원본·원본 executable183bindings를 실행 전후 확인했다.
불일치0. [보존 결과](evidence/preservation.json).
Residual tolerance를 실행 후 선택하지 않았다.
[새 evidence byte seal](evidence/final_seal.json)은 숫자 인증과 구분한다.

## SOURCE PROVENANCE / VENDOR · AUDIT · MUTANT

ZIP `3a2756179b4f74abe450b5383fd9d8c656501cc5e39b39af74de42ffcd4d615d`,
tar.gz `a0f2967b1d110e88fd929f3effd1b8616a6e4fcb0477a988cb564952814a86db` 유지.
원래20파일의 각 hash는 protocol inventory와 동일하다. [V2 봉인](../h2_vendor_build_resume_v2/REPORT.md),
첫 default-link 실패와 과거 [V1 봉인](../h2_representation_pilot1_resume_v1/REPORT.md) 불변.

| 실행물 | source SHA256 | 역할 |
|---|---|---|
| VENDOR | aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d | 이전 README static executable의 fresh 실행 |
| AUDIT | 9c62fdec5aacca8a86bc7b9668a0cc8f4a33480cf624cee3d2b720cdb6a97564 | 원래 계산+sidecar 관측 |
| LOW_ITMAX | 583f62caea3c3171ec89ed156a5ac9cb9ac6e67c2d9914a007241501901f3f4b | ITMAX=1인 시험 전용 사본 |
| BAD_EN | AUDIT와 동일 source/binary, 별도 경로·input | EN만−2.0으로 바꾼 observer 시험 |

Raw root는 `runs/h2_representation_pilot1/internal_convergence_v0_20261003/`.
VENDOR binary는 이전 `vendor_build_resume_v2_20261003/vendor_build/h2solv/f/`에서 그대로 사용했다.
AUDIT와 LOW_ITMAX build는 각각 새 `audit_build/`, `mutant_low_itmax_build/`다.
BAD_EN은 `mutant_bad_en_binary/`, 결과는 `mutants/BAD_EN/`에 격리했다.
제3자 전체 source/archive/executable과 대형 H/S/E/v는 Git 밖에 유지한다.
[raw 경로·dimension·format·hash inventory](evidence/raw_inventory.json).

## INSTRUMENTATION PATCH / 계산식 불변의 범위

[AUDIT patch](evidence/audit_build.patch), [LOW_ITMAX patch](evidence/mutant_low_itmax_build.patch).
원본 계산 줄 교체·삭제0, 관측 블록8개와 독립 helper 추가다.
추가 블록을 제거하면 원래 source bytes가 복원됨을 실행 전 및 시험에서 확인했다.

관측 위치(원본 line 번호):

- CALCEN539 앞: precision 축소 후 원래 HH/DN snapshot, initial EN/EPSKOR/입력 metadata.
- CALCEN539 뒤: 실제 반환 EN/WF/WA(1)/ierror 저장.
- invsg2541 뒤: errest, 실제 n/maxit/ijob 관측 시작.
- leq1s2566·2595 뒤: factorization/각 solve의 실제 ier 및 factor inertia.
- eig 갱신2606 뒤: iteration index, previous/updated eig, signed/abs delta, 원래 식의 threshold.
- loop 종료2609 뒤: 자연 종료 경로에만 EXHAUSTED marker.
- WA(1) 갱신2621 뒤: 정상 수렴 jump 또는 EXHAUSTED 경로를 구분한 normalization 완료 marker.

원래 goto100과 계산식은 그대로다. 로그는 `audit_invsg.log`에만 쓰며 stdout에는 추가하지 않는다.
H/S는 `audit_HS.bin`, 반환 E/v는 `audit_EV.bin`이다. lower-triangle row order,
precision/sign/exponent/active limbs를 저장하고 pointer·spare/unused limbs를 제외한다.
영의 mantissa는 canonical0이다. [native probe](evidence/calibration.json)는 6개의 알려진 dyadic,
1+2^−100, 2^−300, 음수 및 384/320-bit 혼합을 정확히 복원했다.

이것은 source의 계산 줄 불변과 **과학 출력·wavefunction의 관측된 byte 불변** 증거다.
전체 내부 machine state·메모리 배치까지 동일하다는 formal proof는 아니다.

## INVSG TERMINATION CONTRACT

[직접 재검토한 source 계약](evidence/source_audit.json).
ITMAX=40, EPSKOR=zero, ijob=0, 초기 EN은 desired eigenvalue 근처의 shift다.
고정 reps='1e-64', `errest=max(sixtn*n*reps,abs(eps))`, sixtn=16.
업데이트는 `eprev=eig`, `eig=eold+one/sm`이고,
**strict `abs(eprev-eig)<errest*abs(eig)`**일 때 goto100이다.
maxit 자연 종료도 label100 정규화에 도착하며 별도 nonconvergence error를 만들지 않는다.
leq1s ier65는 algorithmically singular warning,129는 exactly singular pivot/block이다.
invsg는 어느 nonzero ier도 E=0 early return으로 처리한다. CALCEN은 ierror를 print한 뒤 계속 반환한다.

WA(1)은 leq1s wa(n+1)의 음의 pivot inertia를 invsg에서 반환한 것이다.
EPSKOR=0, S 양의 정부호 및 신뢰 가능한 factorization 조건 아래에만
초기 EN 아래 generalized eigenvalue 개수라는 설명이 성립한다. 이번 native count 자체는
독립 SPD/inertia 또는 ground-root certificate가 아니다.

## VENDOR EXAMPLES / 실제 종료 판정

모두 원래 Ω7·NMAX·NDIGITS·EN·nonlinear parameters를 유지했다.
표의 initial EN은 input literal, final EN은 간략 표시이며 actual precision의 전체값은
[table.json](evidence/table.json) 및 case별 observation.json에 보존했다.
abs delta와 threshold는 아래에서7유효숫자로 표시한다. 전체94 iteration이 sidecar에 있다.

| case | basis / NMAX | input EN | final EN(Eh) | iterations | last abs delta | threshold | native inertia |
|---|---|---:|---:|---:|---:|---:|---:|
| H–He⁺ | 416 / 140 | −2.9044 | −2.90431153172832800319813 | 18 | 1.833169e−60 | 1.933110e−60 | 12 |
| JC symmetric | 228 / 80 | −1.0573 | −1.05732615365124475438347 | 16 | 4.717080e−63 | 3.857126e−61 | 1 |
| H₂ symmetric | 416 / 140 | −1.000836 | −1.00083567301341530581177 | 12 | 3.432724e−64 | 6.661562e−61 | 0 |
| JC asymmetric | 416 / 80 | −0.6908 | −0.69074695401689397878274 | 22 | 2.280457e−61 | 4.597612e−61 | 1 |
| General | 792 / 140 | −0.6940 | −0.69426663072570729800165 | 26 | 4.967179e−62 | 8.797747e−61 | 2 |

5/5: converged_by_eigenvalue_test=true, maxit_exhausted=false, final ierror0,
factorization 및 각 solve ier0, stderr0, 원래 scientific output/WF 불변.
initial literal은 REAL*16→문자열→MPFR 경로로 입력된다. literal과 actual binary 값을
동일한 정확 유리수로 취급하지 않았다. actual initial EN도 sidecar에 보존했다.

## INDEPENDENT RESIDUAL / NORMALIZATION / RAYLEIGH

Windows Python의 mpmath1.3.0, **160 decimal digits**.
원래 packed H/S와 실제 반환 E/v만 읽고 별도 Python matrix action·합을 사용했다.
invsg/avms/dot_product/native 중간 값과 기존 integral/CI evaluator를 재사용하지 않았다.
Snapshot H/S 전부320 bits, 반환 E/v 전부384 bits다.
MPFUN은 binary operation의 입력 정밀도 최댓값을384-bit cap 아래 사용한다.
NDIGITS=60의 matrix quantization320 bits와 실제 vector arithmetic을 구별한다.
160자리 재계산이 matrix 축소 또는 integral truncation으로 잃은 정보를 복원하지 않는다.

| case | residual L2 | residual L∞ | normalization absolute error | E_RQ−E_invsg(Eh) |
|---|---:|---:|---:|---:|
| H–He⁺ | 2.319331e−66 | 5.001929e−67 | 4.880725e−110 | +6.414387e−64 |
| JC symmetric | 7.371955e−68 | 5.078242e−68 | 2.081479e−115 | +3.009865e−67 |
| H₂ symmetric | 3.433317e−73 | 1.148098e−73 | 2.620751e−104 | +3.662344e−70 |
| JC asymmetric | 2.973909e−62 | 2.473974e−62 | 2.115252e−114 | −3.582200e−64 |
| General | 2.967139e−67 | 1.394853e−67 | 1.100800e−108 | −1.943033e−64 |

vTSv, E_RQ, E_invsg 전체160자리 및 scale-normalized η∞, componentwise η,
normalization cancellation ratio도 [case별 결과](evidence/cases/)와 table.json에 있다.
표시 숫자는 측정값의 반올림 요약이며 정확/interval bound가 아니다.
absolute residual은 기저 좌표·scale에 의존한다. 예제 사이 정확도 우열로 쓰지 않는다.

**Acceptance 판정은 MEASURED**다. 기존 vendor residual/normalization 계약이 없었으므로
사전 PLAN에서 숫자 tolerance를 채택하지 않았다. 결과를 보고 새 PASS 기준을 만들지 않았다.
이번 수치가 작다는 사실만으로 H2SOLV_GENERALIZED_RESIDUAL_SUPPORTED 또는 전체 solver
qualification을 선언하지 않는다. 원래 iteration 조건을 실제로 통과했다는 사실과 구분한다.

## ROOT DIAGNOSTIC / 중요한 미확인

보존 H/S를 그대로 float64로 변환했고 [SciPy eigh(type=1)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh.html)
로 lowest/second를 진단했다. S의 양의 정부호가 필요한 경로다.
Matrix 평균 대칭화·diagonal shift·rank cutoff는 하지 않았다.
4예제의 binary64 S는 양의 정부호성을 잃어 해당 경로를 UNAVAILABLE로 남겼다.
이것을 원래 고정밀 S의 음의 정부호 결함이나 integral 오류의 확정으로 읽지 않는다.

JC symmetric만 binary64에서 계산되어 lowest=−1.0573261536512444,
second=−0.6889481175600514였다. native E와 lowest의 표시 차이는−4.44e−16이다.
그러나 cond2(S)=1.148e16, cond2*n*eps64=581.2로 사전 qualification 조건을 크게 초과했다.
숫자 근접만으로 root PASS를 부여하지 않았다. 다섯 case 모두 ROOT_SELECTION_UNRESOLVED.

Native inertia **12/1/0/1/2**도 숨기지 않는다. 특히 H–He⁺와 JC asymmetric는
초기 shift가 반환 E보다 아래인데 native inertia가0이 아니다.
S가 SPD이고 native inertia가 정확하다면 반환 root 아래 다른 root 가능성을 시사한다.
이번에는 두 전제가 독립 확인되지 않았다. 따라서 단순 binary64 실패로 이 질문을
지워 버리거나, 바로 잘못된 root라고 단정하지 않는다. **최저 root 주장의 명시적 미확인 사유**다.
독립 고정밀 SPD/inertia/lowest-root 검사는 다음 설계자 결정 대상이다.

## FAULT INJECTION / 실제 실행

| 시험 전용 사본 | 실제 결과 | detector |
|---|---|---|
| JC symmetric ITMAX=1 | iteration1, MAXIT_EXHAUSTED, solver exit0, final ierror0, 과학 출력 생성 | exhaustion 탐지, 수렴 승인 거부 |
| JC symmetric EN=−2.0 | iteration40, MAXIT_EXHAUSTED, solver exit0, final ierror0, native inertia1→0 | 자연 소진 및 EN/count 변화 구분 |

[LOW_ITMAX 기록](evidence/mutants/LOW_ITMAX/result.json),
[BAD_EN 기록](evidence/mutants/BAD_EN/result.json).
이것은 exit0·ierror0 및 출력 생성이 정상 수렴을 보장하지 않는 **실제 반례**다.
Mutant 에너지는 physics 결과로 사용하지 않는다. 원본 예제 판정에 섞지 않았다.
Bad EN의 원래 H/S bytes는 baseline과 동일하며 Low ITMAX도 header를 제외한 H/S body가 동일하다.
검사기의 synthetic fault injection은 branch/count/threshold/delta/inertia/누락/중복/precision/layout
변조를 거부했다. Native fault 두 실행과 synthetic 시험을 구분한다.

## OUTPUT NONINTERFERENCE / 실행 환경·비용

Fresh VENDOR combined stdout == fresh AUDIT combined stdout == 이전 vendor reference **5/5 byte 동일**.
원본/계측판 wf_7.dat도5/5 동일. 두 executable의 solver/example exits 모두0, stderr empty.
case별 actual/reference/input hashes와 raw stdout·GNU time·RSS·process argv를 보존했다.

Ubuntu-24.04 WSL2 gfortran13.3/GNU ld2.42/MPFR4.2.1/GMP6.3;
기존 compile flags·README static MPFR/GMP 연결, OMP_NUM_THREADS1/OMP_DYNAMIC FALSE 유지.
[환경](evidence/environment.json), [AUDIT build](evidence/audit_build.stdout).
`mpfr_root` deprecation warning은 남아 있다. 해결됐다고 보고하지 않는다.

| case | fresh VENDOR solver s | AUDIT solver s | independent residual/root s |
|---|---:|---:|---:|
| H–He⁺ | 31.92 | 31.76 | 4.468 |
| JC symmetric | 7.13 | 7.25 | 1.641 |
| H₂ symmetric | 51.31 | 52.87 | 4.907 |
| JC asymmetric | 20.80 | 17.35 | 4.703 |
| General | 140.21 | 135.49 | 16.891 |

Native 표는 GNU time elapsed(process+timeout wrapper), 독립 표는 Python monotonic이다.
Windows/WSL launcher 포함 monotonic·CPU/RSS도 각 process.json에 별도 저장했다.
시스템 경합·한 번의 실행 차이가 있어 계측 오버헤드·표현 방식 성능 우열 또는 R=.4 비용
결론으로 사용하지 않는다. 대형 source/matrix/vector의 hash는 raw inventory에 있다.

## WHAT IS NOW SUPPORTED / FINAL CLASSIFICATION

- H2SOLV_VENDOR_OUTPUT_REPRODUCTION_PASS
- H2SOLV_INSTRUMENTATION_NONINTERFERENCE_PASS — scientific output/WF의 byte 범위
- H2SOLV_INVERSE_ITERATION_CONVERGENCE_SUPPORTED — 이번5예제의 원래 종료 분기
- H2SOLV_MAXIT_EXHAUSTION_DETECTION_SUPPORTED — 실제 시험 사본2개
- H2SOLV_GENERALIZED_RESIDUAL_MEASURED_ACCEPTANCE_UNRESOLVED
- H2SOLV_ROOT_SELECTION_UNRESOLVED
- H2SOLV_INTEGRAL_TRUNCATION_CONVERGENCE_UNRESOLVED
- STOP / NOT_CERTIFIED / NOT_PRODUCTION_APPROVED

공식 H2SOLV/논문/우리 observer·residual checker는 모두 감사 대상이다.
코드 경로가 solver와 독립이라는 뜻이며 새 외부 조직·별도 저자의 external audit라는 주장이 아니다.
이번에 원래 수렴 분기의 관측 가능성은 닫았지만 전체 물리·residual acceptance·ground root는 닫지 않았다.
NMAX ladder, recurrence 검증, R=.4 B1 계약, B2는 미착수다.

## TESTS / READ SCOPE / NEXT DESIGNER DECISION

최종 관련 시험 **129 passed / failure0 / error0 / skip0, 1.13초**(신규43개 포함).
이번에 새로 실행한 시험이며 과거 로그 열람 수치가 아니다.
[verification.json](evidence/verification.json), [시험 로그](evidence/related_tests.log).
사전 첫 시험은 잘못된 source 공백 anchor1건과 실제로 바뀌지 않은 limb를 변조 대상으로 고른
시험1건으로 2failed/29passed였다. 둘을 실행 봉인 전에 수정한 뒤31passed.
첫 실패·수정 후 로그 모두 보존했다. Native 결과를 본 뒤 code/tolerance를 조정하지 않았다.

LOCAL FULL 생략 / 관련 시험으로 대체 / 새 isolated observer·독립 분석·시험·문서만 추가하고
A physics/common/frozen fixture는 변경하지 않았다. 공식 기준선 갱신 없음.
AGENTS/RULES를 조회하고 불변조건·검증·중단·기록 규칙을 확인했다.
CURRENT_STATE 상단 현재 Gate·H2 범위, REPO_MAP 상단·전자구조 계통은 범위를 지정해 읽었다.
첨부 지시 전체 및 invsg/leq1s/avms/dot_product/CALCEN은 직접 읽었다.
H2SOLV 전체 recurrence와 CURRENT_STATE의 모든 과거 이력까지 재독·재증명한 것은 아니다.

다음 결정: (1) 저장 H/S의 독립 고정밀 SPD/inertia 및 lowest/second root 진단 범위,
(2) scale·condition을 반영한 residual/normalization acceptance 계약.
그 결정 전에 R=.4로 넘어가지 않는다. 이번 작업에서는 다음 실험을 승인·실행한 것으로 간주하지 않는다.

절차에 scientific-critical-thinking을 적용해 측정과 판정을 분리했다.
Software reference: Kassis et al. (2026), [Scientific Agent Skills](https://arxiv.org/abs/2609.00065),
현재 arXiv v2를 확인했다. H2 물리 correctness 근거로 사용하지 않는다.
