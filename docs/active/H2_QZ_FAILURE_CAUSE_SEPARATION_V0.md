# H₂ QZ Failure Cause Separation V0 — 2026-10-03

**부분 원인 분리 / Stage C 미완료 / NOT CERTIFIED / DESIGNER DECISION REQUIRED.**
R=0.5의 저장된 C/S에 대해서는 기존 orthogonality refusal이 검사기 연산 오차임을
정확한 산술의 residual 상한으로 분리했다. 추가한 독립 CI 후보는 R=0.4에서 검증을 실패했다.
네 short-R 점에 대한 유효한 same-basis reference는 확보하지 못했다.
**기존 QZ44 Gate NUMERICAL FAIL, 43 accepted / 1 refused와 reference 초과 네 점은 그대로다.**

이번 작업은 원래 FAIL을 PASS로 바꾸는 수리가 아니다. Hamiltonian, cc-pVQZ spherical
contracted basis, AO60 full span, 2-electron singlet1830, EBO=Ee+1/R, canonical rule,
numerical guard, Pachucki CSV 및 physical 기준 0.001 hartree를 수정하지 않았다.
R=0.5 energy를 채우지 않았고 QZ44 fresh run도 다시 하지 않았다.
force/dynamics/formation/cc-pV5Z/복잡한 분자/world/production은 진행하지 않았다.

## Git 및 격리

시작에 확인한 실제 상태는 아래와 같다. 원격 ref는 로컬에 저장된 ref를 읽은 값이며
이번에 fetch/push하지 않았다.

| 대상 | 확인한 commit / 상태 |
|---|---|
| 원래 checkout master | 951b07695e74abc633168ddb672b11e2289184c9 |
| origin/master | 6c53eec71e981cef35f850095da76b965457866c |
| master ahead/behind | 1 ahead / 0 behind, dirty 파일 없음 |
| codex/h2-ao-micro-v0 | 61bad943a1865ac1a6b2e89a6577fe03cb4f6b85 |
| origin/codex/h2-ao-micro-v0 | 61bad943a1865ac1a6b2e89a6577fe03cb4f6b85 |
| H₂ branch ahead/behind | 0/0 |
| 최근 H₂ history | 61bad94 → 0e9e454 → 6c53eec → 164ecde |

master의 별도 Candidate B commit은 요청서 예상보다 앞서 있어 먼저 보고했다.
H₂ 기준 61bad943에서 managed worktree를 만들고 **codex/h2-qz-cause-v0** branch로
격리했다. 기존 checkout/다른 트랙을 수정하거나 merge하지 않았다. **commit만 / push 없음.**

AGENTS/RULES의 작업·검증·중단 규칙을 읽었고, CURRENT_STATE/REPO_MAP의 관련 현재 상태와
H₂ 위치를 확인했다. 저장소 전체와 runs 전체를 읽지 않았다.
systematic-debugging skill의 원인 조사 절차를 사용했으며 numerical path 수리는 하지 않았다.

## 봉인과 두 번의 시작 실패

새 분석 protocol을 사전 작성했고 numerical execution 전에 기존 source/시험/compact
evidence **200개**, 신규 분석·시험 **7개**, 저장된 다섯 geometry의 JSON/NPZ **10개**를
hash로 봉인했다. 기존 numeric runtime 34개도 이전 seal과 같음을 별도 확인했다.
source/config/기존 증거는 실행·중단 후 다시 확인했다.

첫 시작은 WSL Git이 managed worktree의 Windows gitdir 경로를 해석하지 못해 **봉인 전**
중단됐다. GIT_DIR/GIT_WORK_TREE를 명시적으로 /mnt/c 경로에 매핑한 뒤 같은 HEAD를 확인했다.
두 번째는 Windows checkout에서 기존 시험 5개가 CRLF로 나온 것을 byte binding이 거부했다.
200개 전체를 대조하여 차이가 그 5개뿐이며 모두 CRLF-only임을 확인했다.
worktree 안의 그 5개를 정확한 Git blob bytes로 복원했다. 시험 의미나 numerical source를
고친 것이 아니다. 두 번 모두 물리/수치 진단을 시작하지 않았고 로그·checkout audit를 보존했다.

그 뒤 audit_v2에서 A/B 및 R=0.4의 C1 두 후보가 실행됐다.
독립 CI 후보의 residual 검증 실패 뒤 R=0.6의 진행 중 worker를 중단했다.
R=0.7/0.8 후보는 시작하지 않았다. 부분 실행을 완료나 PASS로 세지 않는다.
기존 AGENTS.md의 **“3회 시도해서 실패하면 멈추고 보고한다. 계속 고치려 들지 않는다.”**
규칙에 따라 두 봉인 전 실패와 C1 campaign의 검증 실패 후 추가 수치 실행을 멈췄다.
다른 solver 후보로 반복하여 결과를 맞추지 않았다.

## Stage A — 동일 C/S의 정확한 잔차 판정

[A 기록](h2_failure_cause_v0/A_R_0.5.json).
원래 저장된 binary64 C와 canonical S를 byte hash로 확인하고 다시 측정했다.
binary64 operator residual은 **1.5495072148621564e-10**으로 원래 값과 bit-identical이다.
기존 guard 1e-10보다 크므로 원래 판정은 REFUSED다.

새 verifier는 모든 저장 binary64 값을 정확한 dyadic 정수/2의 거듭제곱으로 변환한다.
정수 행렬 곱으로 B=CᵀSC−I를 정확하게 만들고,
각 column의 squared Euclidean norm 최댓값과 모든 entry squared sum을 분수로 계산한다.
이는 각각 operator 2-norm의 squared 하한과 squared Frobenius 상한이다.
square root 표시는 정수 isqrt를 이용한 바깥쪽 decimal enclosure다.
BLAS·executor·기존 MP evaluator를 호출하지 않는다.

**6.4438151402393377732039452515e-12 ≤ ||B||₂ ≤
1.06340119938833816988016412713e-11 < 1e-10.**

upper squared numerator/denominator도 기록하여 threshold 관계를 정확한 분수로 비교한다.
따라서 이 저장된 C/S의 실제 orthogonality residual은 threshold 아래다.
**MEASUREMENT / GUARD EVALUATION ERROR SUPPORTED → MEASUREMENT_ERROR**
분류다. 이는 단순 80자리 근삿값보다 강한 입력 한정의 상·하한 판정이다.

신뢰 전제는 binary64 input decoding, Python integer/Fraction, 구현한 행렬 곱·norm bound다.
이 algebra와 작은 독립 Fraction 계산을 시험으로 대조했다.
이 한 residual의 정확한 enclosure를 모든 AO integral/solver/physics 또는 formal certification으로
확대하지 않는다. S 자체의 physical accuracy와 이후 energy 계산은 별개다.
**원래 R=0.5 refusal/null energy는 변경하지 않았다.**

nominal exact decimal 1e-10과 원래 binary64 threshold
7737125245533627/77371252455336267181195264의 차이도 공개한다.
이 상한은 두 threshold 모두보다 충분히 작다. Stage A 원인 판정은 그 sub-ulp 차이에 의존하지 않는다.

## Stage B — Adaptive Precision Guard prototype

[B 기록](h2_failure_cause_v0/B_R_0.5.json).
production을 호출하지 않는 별도 prototype을 구현했다.

1. Binary64 각 곱·덧셈 뒤 nextafter로 outward interval을 만들어 residual matrix를 포함한다.
2. max-entry 하한과 n×max-entry 상한으로 operator norm의 빠른 구간을 얻는다.
3. threshold 관계가 모호하면 동일 C/S를 exact dyadic verifier로 평가한다.
4. 그 하·상한도 경계를 가르지 못하면 UNRESOLVED/STOP으로 남긴다.

R=0.5의 cheap norm 범위는 0에서 약 4.4643e-7로 넓어 **UNRESOLVED**였다.
정확한 fallback이 Stage A와 같은 BELOW 판정을 냈다.
cheap 0.013931732 s + exact fallback 0.023051617 s = **0.036983349 s**였다.
한 입력의 측정이며 일반 비용 benchmark가 아니다.

IEEE round-to-nearest·gradual underflow·FTZ 없음이 cheap interval의 신뢰 전제다.
Prototype은 nominal exact decimal threshold를 쓴다. 경계에서 원래 binary64 threshold의
bit semantics와 완전히 같다는 주장은 하지 않는다. 해당 차이는 이 R=0.5 판정에 영향이 없지만,
production 적용 전 처리해야 할 별도 한계다. 원래 guard source/constant는 불변이다.
**production 미적용 / QZ44 acceptance 변경 없음 / prototype만**이다.

## Stage C — 독립성 및 실패한 reference 후보

두 후보는 모두 저장된 동일 canonical binary64 S/h/s8 AO를 소비했다.
원래 full basis·singlet sector를 유지하고 within-pair 대표 규칙을 재사용했다.
MO pair-interchange 또는 Hamiltonian을 평균하여 강제 대칭화하지 않았다.

| 항목 | frozen-C 후보 | generalized-h / four-leg 후보 |
|---|---|---|
| CI/action | PySCF direct_spin1 determinant contraction을 full singlet에 투영; 별도 direct-pair matrix와 대조 | 같음 |
| diagonalization | SciPy ARPACK, deterministic start | 같음 |
| orbital coordinates | 원래 저장된 Cholesky C 공유 | generalized Hermitian hC=SCε의 전체 60개 벡터 |
| transformation | 원래 PySCF compact 경로 공유 | NumPy four-leg tensor contraction, 별도 algorithm |
| AO generation | 원래 libcint binary64 AO 공유 | 같음 |
| arithmetic | binary64, 기존 라이브러리/하드웨어 공유 | 같음 |

AO integral generation은 독립이 아니다. 두 번째 변환도 basis/norm metadata와 BLAS를 공유한다.
singlet projection은 수학적으로 UᵀHU의 sector 선택이며, H를 평균 대칭화하는 수리가 아니다.
독립성을 CI/변환/AO/산술로 분리하여 기록한다.

direct_spin0는 내부 ERI transpose_sum/평균 단계가 있어 처음부터 제외했다.
[공식 FCI source](https://pyscf.org/_modules/pyscf/fci/direct_spin0.html)와 설치된 소스를 확인했다.
direct_spin1을 사용했다고 정확한 operator가 자동 보장되는 것은 아니다.
그 contraction과 별도로 full singlet matrix를 직접 pair-index 식으로 구성하여
action·Hermiticity·eigen residual을 교차 확인했다.

### R=0.4에서 실제 발생한 불일치

| 값 | frozen-C 후보 | generalized-h 후보 |
|---|---:|---:|
| original BO energy | −0.11803113362157003 | 같음 |
| candidate BO energy **(invalid)** | −0.11803074665285074 | −0.11803129011100433 |
| candidate − original | +3.8696871929e-7 | −1.564894343e-7 |
| determinant vs direct-pair action, probe 최대 L2 | 3.339991356062226e-6 | 1.564212895669927e-5 |
| direct-pair eigen residual | 5.286950910592781e-7 | 1.9047846256647038e-6 |
| determinant eigen residual | 5.292977744207676e-7 | 1.9041325314332892e-6 |
| MO pair-interchange residual | 2.981148007941484e-5 | 4.60572483541033e-5 |
| validated same-basis reference | **false** | **false** |

두 후보 모두 기존 eigen residual guard 1e-9를 실패했다.
이 두 energy를 cc-pVQZ의 검증된 답으로 인정하지 않는다.
특히 frozen-C 후보는 같은 C/compact MO 입력에서 **CI Hamiltonian/action 계층**에
첫 관측 불일치가 있다. 매우 작은 direct-pair H asymmetry가 determinant action의
Hermiticity/정확성까지 보장하지 못했다.

MO pair-interchange 불일치와 determinant CI의 적분 symmetry 가정·h1e absorption·
연산 순서가 후보 원인이다. 그중 하나로 확정하거나 original solver 오류로 전가하지 않는다.
ARPACK 설정 tol=1e-12도 실제 residual guard 통과를 대신하지 않았다.
작은 synthetic symmetry-complete tensor에서 후보가 통과해도 실제 asymmetric MO tensor
입력에서 같은 operator를 구현한다는 보장은 없었다.

**새 독립 reference 후보의 numerical implementation/적용 조건 문제는 관측됐다.
원래 QZ44 solver가 틀렸는지와 cc-pVQZ 자체가 부족한지는 아직 UNRESOLVED다.**

### 네 short-R 점의 최종 비교 상태

| R | 우리 BO energy | 유효한 독립 same-basis energy | physical reference 차이 | 원인 분류 |
|---:|---:|---|---:|---|
| 0.4 | −0.11803113362157003 | 없음: 두 후보 invalid | +0.00219920755725297 | UNRESOLVED |
| 0.6 | −0.7680645543359941 | 없음: worker 중단, 결과 없음 | +0.0015708751499151 | UNRESOLVED |
| 0.7 | −0.9207565303731988 | 미실행 | +0.0012709311542648 | UNRESOLVED |
| 0.8 | −1.0189864733406209 | 미실행 | +0.0010701930198942 | UNRESOLVED |

REPRESENTATION_LIMIT_SUPPORTED 판정의 전제인 유효한 same-basis energy 일치를 확보하지 못했다.
C2 selected AO/MO 확대와 C3 full high-precision energy는 실행하지 않았다.
Pachucki physical reference 차이를 그대로 solver 오류 또는 basis 한계로 분류하지 않는다.

## 비용·시험·보존

| 방법 | worker wall | peak RSS | precision / 줄인 불확실성 |
|---|---:|---:|---|
| A exact audit | 0.134140906 s (exact kernel 0.025174697 s) | 47.52734375 MiB | exact dyadic; R=0.5 guard 오판 분리 |
| B prototype | 0.135393498 s (guard 내부 0.036983349 s) | 46.90234375 MiB | binary64 interval + exact fallback; 입력 한 점에서 판정 가능 |
| C1 R=0.4 frozen-C | 159.635321718 s | 755.93359375 MiB | binary64; candidate invalid 확인 |
| C1 R=0.4 generalized-h | 156.456609191 s | 758.12890625 MiB | binary64; 두 번째 candidate도 invalid 확인 |

추가 dependency는 없다. 기존 로컬 WSL Python/NumPy/SciPy/PySCF만 사용했다.
완료된 A/B/C1 두 후보까지 campaign timer는 320.642602227 s다.
seal file mtime에서 controlled-stop wall-clock timestamp까지는 362.788384199 s로,
중단된 R=0.6 worker·startup·재검사까지 포함한 별도 관측 시간이다.
완료한 전체 campaign 또는 정밀 비용 benchmark로 세지 않는다.
두 봉인 전 실패의 정확한 전체 elapsed는 별도로 측정하지 않아 그 합을 추정하지 않는다.
peak RSS는 각 WSL process의 ru_maxrss다. 중단 worker의 VmHWM/VmRSS는 stop metadata로 보존했다.

사전 Windows 새 시험 14 passed, WSL 새 시험+small integration 15 passed였다.
중단 뒤 source를 고치지 않고 최종 관련 시험을 실행했다:
**Windows 99 passed / 2.98 s; WSL 15 passed / 2.74 s; failed/error/skip 0.**
이번 WSL 15는 새 exact/interval/sector/transform 시험과 작은 synthetic CI 대조다.
과거 WSL 96을 이번 재실행 수로 인용하지 않는다. 중복 preflight 수를 합산하지 않는다.

새 fault tests는 정확한 Fraction 대조, guard 양쪽·불확실 경계, outward sqrt,
interval product inclusion, adaptive STOP, nonfinite, singlet projector의 norm,
direct pair matrix와 별도 product-space 식, four-leg 변환과 full index sum,
executor import 금지 및 hash drift를 확인한다. 실제 C1 실패를 시험 PASS로 덮지 않는다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 독립 분석·시험·문서만 추가했다.
기존 실행 code/common/frozen contract/fixture 및 numerical path는 수정하지 않았다.
공식 LOCAL FULL 기준선은 갱신하지 않는다.

기존 protected 200개, 새 sealed source 7개, 입력 10개를 중단 후 hash로 확인했다.
원래 raw 265+145+118+118=**646개**, 변경 0이다.
새 raw manifest는 16개 기록을 포함하며 원래 QZ44 결과/FAIL을 덮어쓰지 않는다.
[summary](h2_failure_cause_v0/summary.json),
[preservation](h2_failure_cause_v0/preservation.json),
[실행·중단·실패·시험 evidence](h2_failure_cause_v0/README.md).

## 원인 분류 및 설계자 결정

| 대상 | 직접 증거 | 분류 |
|---|---|---|
| R=0.5 orthogonality | 동일 C/S의 exact operator 상한 < guard, binary64 residual > guard | **MEASUREMENT_ERROR** |
| R=0.5 후속 AO/MO/energy | energy 미계산, residual 측정만 감사 | **UNRESOLVED** |
| R=0.4 독립 CI 후보 | direct pair action과 determinant action·eigen residual 불일치 | **새 진단 후보의 구현/적용 조건 문제** |
| 원래 short-R 네 점 | 유효한 독립 same-basis reference 없음 | **UNRESOLVED**, basis-limit 지지 판정 없음 |

구상 일치성을 별도 확인했다. 같은 물리 문제·기준을 유지했고, 검사기가 오판한 사실을
원래 curve의 acceptance 변경에 쓰지 않았다. 실패한 독립 reference 자체도 의심하고 보존했다.
동일 basis의 정답과 physical reference의 역할을 분리했다. numerical validation과
formal/production certification을 섞지 않는다.

**DESIGNER DECISION REQUIRED:** 다음 작은 진단을 허용할지 결정이 필요하다.
review 가능한 후보는 기존에 새로 작성한 direct-pair singlet matrix를 다른 dense LAPACK
driver로 대각화하고, 네 short-R 점의 두 transformation과 기존 energy를 비교하는 것이다.
canonical AO/within-pair rule·AO60/D1830·기존 guard·1e-9 same-basis band·physical0.001은 유지한다.
모든 guard를 통과한 reference만 basis-limit 판단에 사용한다.
우선 R=0.4에서 비용과 최초 불일치 계층을 확인한 뒤 나머지 3점 진행 여부를 판단한다.
이 후보의 실제 비용과 성공 여부는 아직 측정하지 않았다. 기존 direct dense timing을 새 독립
구현의 실측처럼 인용하지 않는다. 이번에는 실행하지 않았다.
