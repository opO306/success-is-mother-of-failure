# H₂ Representation Comparison Pilot 1

2026-10-03. **REPRESENTATION_PILOT1_FEASIBILITY_UNRESOLVED / STOP /
NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.**
실행 소스를 확보하지 못해 B 계산은 0회다. 이 결과는 James–Coolidge 표현의
성능 실패나 구현 불가능 증명이 아니다. 에너지·수렴·비용 우승자는 미판정이다.

## GIT STATE

부모 982e6d80ed37ab118bc68c3191952b934361202a에서 별도 worktree,
codex/h2-representation-pilot1 브랜치를 만들었다. 시작 시 dirty/untracked 없음.
실제 git ls-remote 확인: 원격 master 6c53eec71e981cef35f850095da76b965457866c,
부모 감사 브랜치 982e6d80ed37ab118bc68c3191952b934361202a.
[시작 기록](evidence/git_start.json). Commit 허용 범위, push 미실행.

기존 봉인 1269 bindings를 실제 부모 checkout/main raw 경로에서 전후 검사했다.
부모 worktree도 clean이다. [보호 검사](evidence/parent_protection.json).
QZ44 NUMERICAL FAIL, same-basis reconstruction UNRESOLVED / NOT CERTIFIED,
finite cardinal limitation SUPPORTED UNDER CHECKED ASSUMPTIONS,
AO/conditioning/transform 수치 문제, MO ERI UNRESOLVED를 유지한다.

## B IMPLEMENTATION FEASIBILITY

일차 후보는 H2SOLV AFBA_v1_0의 symmetric James–Coolidge subset이다.
[공식 version1 배포](https://data.mendeley.com/datasets/835yrp4rww/1),
[프로그램 논문](https://doi.org/10.1016/j.cpc.2016.07.024),
[저자 preprint](https://users.fuw.edu.pl/~krp/papers/h2solv.pdf).
이는 production foundation 선택이 아니다.

| 항목 | 출판/등록 근거 | 로컬 확인 상태 |
|---|---|---|
| Source | Catalogue와 versioned DOI 확인 | Archive bytes/hash 미확보 |
| Integral evaluator | Master integral와 recurrence 설명 존재 | Fortran recurrence source 미검토 |
| Precision | MPFUN2015 MPFR-backed v04 | Actual build/arithmetic 미검증 |
| Dependencies | Fortran90, OpenMP, MPFUN2015, MPFR, GMP | B 설치·연결 시험 미실행 |
| Platform | Linux/Unix가 기술됨 | WSL B build/native Windows 미시험 |
| Reproducible I/O | Charges/R/parities/Ω/digits/energy hint/x,y,u,w 예제 | Parser·retained list·vector output 미검토 |
| R=.4 BO meaning | Eq2에 +1/R 포함 | R=.4 actual output 미실행 |
| Ground root | Inverse iteration은 hint에 가까운 root 선택 | Lowest-root 독립 확인 미봉인 |
| Parameters | 고정 지수+크기 증가 또는 자기 에너지 최적화 가능 | Generic seed/optimizer/종료 미봉인 |

긴 recurrence는 논문에 모두 인쇄하지 않고 Fortran 형태로 저장했다고 기술된다.
출판 결과를 읽은 것과 실행 가능한 적분 코드 확보는 다르다.
새 대형 solver나 독자적인 recurrence 재유도로 feasibility gate를 우회하지 않았다.

라이선스는 식별했다. Preprint p2의 표기와 배포 metadata는 다르며,
versioned DataCite deposit은 CPC를 명시한다.
[현재 Elsevier CPC 조건](https://www.elsevier.com/about/policies-and-standards/open-access-licenses/elsevier-user/cpc)은
academic/non-profit 연구 사용과 제3자 재배포·commercial/proprietary 사용의 제한을 구분한다.
Public Git 재배포나 미래 production 이용 권한을 가정하지 않았다.
Archive 내부 조건은 미확인이다.

실제 source 접근의 세 경로:

1. Windows HTTP: 공식 landing/search/file API403; 옛 CPC 주소는 DNS 실패.
2. Codex in-app browser: 공식 version1 페이지 접근이 30.116초 후 timeout.
3. Ubuntu-24.04 WSL curl: 공식 public-dataset file API401, 인증 필요 응답.

세 경로 뒤 source 재시도·B 구현·계산을 STOP했다.
배포 등록은 확인했으므로 **코드가 존재하지 않는다는 결론은 아니다.**
[접근 기록](evidence/source_access_attempts.json)은 tool-output 전사,
[metadata snapshots](evidence/primary_metadata_acquisition.json)은 별도 HTTP raw bytes/hash다.
Raw는 Git 밖 runs/h2_representation_pilot1/feasibility_v0/에 보존했다.

Sims–Hagstrom modified JC, Pachucki2010 JC/Heitler–London, Ndeke2024 H2SOLV의
방법·계보도 검토했으나 이번 범위에서 다른 runnable source/license 묶음은 미확보다.
Ndeke 출판 에너지를 로컬 B 계산으로 사용하지 않았다.
[상세 feasibility](evidence/feasibility.json).

## PHYSICAL CONTRACT

두 Z=1 고정 핵, 두 전자, 비상대론 Coulomb Hamiltonian,
singlet ¹Σg⁺ ground state, Bohr/hartree atomic units.
첫 대상 nominal R=.4, BO=E_electronic+1/R.
H2SOLV Eq2에는 이미 핵 반발항이 있으므로 +1/R 이중 가산 금지.
Actual parser/입력값 해석은 source 확보 뒤 봉인해야 한다. 현재 B 입력 파일은 없다.
Gaussian AO60/CI1830을 B에 강제하지 않는다.

## REPRESENTATION DEFINITIONS

A-QZ: contracted Gaussian AO60/full singlet1830.
A-V5Z: contracted Gaussian AO110/full singlet6105. 기존 입력/source/guard 불변.
B 논문 정의: exp(-yΔ1-xΔ2-uΣ1-wΣ2)와 r12 및 네 핵 거리 조합의 다항식.
Σi=riA+riB, Δi=riA-riB, n0…n4≥0, Σn≤Ω, Eq6 정규화 R^(-Σn-3).
x=y=0, u=w>0은 symmetric JC이며 전자/핵 교환 projector와 중복 제한을 적용한다.
이는 논문 정의이고 actual retained list/rank는 미검토다.
SMALL/MEDIUM/LARGE, nested 여부: NOT_SEALED_FEASIBILITY_BLOCKED.

## PARAMETER OPTIMIZATION CONTRACT

Generic seed, optimizer, 내부 종료와 비용 계약은 미봉인이다.
문헌 최적 파라미터/reference를 이용한 실행은 없다.
재개 시 자기 variational energy만 목적함수로 사용한다.
문헌 seed는 WARM-START / LITERATURE-SEEDED 및 외부화된 탐색 비용으로 분리해야 한다.
Reference 에너지를 inverse-iteration hint에 넣지 않으며 hint는 ground-root 검증을 대신하지 않는다.

## R=0.4 RESULTS

| Arm | BO energy Eh | Signed reference 차이 Eh | 성격 |
|---|---:|---:|---|
| A-QZ | −0.11803113362157003 | +0.0021992075572529746 | 과거 numerical accepted, .001 초과 |
| A-V5Z | −0.11959699456988826 | +0.0006333466089347428 | 과거 numerical accepted, 이 한 점에서 .001 이내 |
| B-SMALL | — | — | NOT_EXECUTED_FEASIBILITY_STOP |
| B-MEDIUM | — | — | NOT_EXECUTED_FEASIBILITY_STOP |
| B-LARGE | — | — | NOT_EXECUTED_FEASIBILITY_STOP |

[QZ 원본 복사](evidence/historical_QZ_result.json),
[V5Z 원본 복사](evidence/historical_V5Z_result.json),
[원본 inventory hash 대조](evidence/historical_provenance.json).
이번 fresh calculation이 아니다. 이전 numerical accepted는 모든 MO 적분 정확성이나
별도 spatial irrep 인증이 아니다. V5Z 별도 저장 irrep 검증은 없다.

## REPRESENTATION CONVERGENCE

B NOT_EVALUATED. 세 크기/nested space가 없으므로 수렴이나 단조 감소를 주장하지 않는다.
과거 cardinal 추세는 기존 조건부 증거이며 이번 B 수렴의 증거가 아니다.

## ARITHMETIC CONVERGENCE

P1/P2/P3 미봉인. Hermiticity, metric condition/rank, normalization,
eigen residual, spatial symmetry 모두 미측정이다.
논문 default 적분80/선형대수60 decimal digits는 설명이며 Pilot precision 선택이 아니다.
Actual precision과 Taylor-series 내부 수렴은 별도 봉인·검사가 필요하다.

## PHYSICAL REFERENCE COMPARISON

기준 abs(E−reference)≤0.001 Eh 유지.
과거 Pachucki R=.4 BO=−0.120230341178823와 저장된 차이를 제시했다.
B는 R04_TARGET_ACCURACY_MET/NOT_MET 계산 판정 없이 NOT_EVALUATED_FEASIBILITY_STOP.
[Pachucki](https://arxiv.org/abs/1007.0406),
[Sims–Hagstrom](https://doi.org/10.1063/1.2173250).
Reference 진실/오차 상한이 완전히 닫혔다고 가정하지 않는다.
H2SOLV는 Pachucki 계보를 공유하므로 향후 일치도 자동 독립 reference 인증이 아니다.

## R=1.4 / 6.0

B-LARGE R=.4의 guards/산술 수렴/표현 수렴 설명/physical target gate가 미실행이다.
조건부 후속 두 점과 전체 곡선은 미실행이다.

## COST COMPARISON

| Arm | 표현/행렬 크기 | 과거 계산 구간 s | 과거 process peak RSS MiB | 이번 whole-run cost |
|---|---|---:|---:|---|
| A-QZ | AO60/CI1830 | 1.646757418 | 453.90234375 | 미측정 |
| A-V5Z | AO110/CI6105 | 46.139181346 | 3874.16015625 | 미측정 |
| B-SMALL | 미정 | — | — | 미실행 |
| B-MEDIUM | 미정 | — | — | 미실행 |
| B-LARGE | 미정 | — | — | 미실행 |

COST_COMPARISON_NOT_COMPARABLE / NOT SAME-RUN COST COMPARISON.
주요 Gaussian 비교 대상은 .001 목표에 도달한 A-V5Z다.
과거 timer는 입력 봉인 뒤 시작하고 계산/AO_C write 뒤 종료한다.
Process startup/result/postcheck write 제외; 세부 integral/basis/matrix/eigensolve/
validation/precision/실패·재시도 비용은 저장되지 않아 null이다.
RSS는 process high-water다. [비용 측정 범위](evidence/cost_comparison.json).

## SCALING / HIDDEN COST

A는 mature PySCF/libcint와 기존 CI 구현의 관측 비용이다.
B의 로컬 build/prototype 비용도 미측정이다. 함수 개수만으로 효율을 판정하지 않는다.
Parameter search, precision, validation, 실패 비용 및 구현 성숙도를 구분해야 한다.
H₂ two-electron efficiency ≠ many-electron efficiency.
Static energy efficiency ≠ time-dynamics efficiency.
전자쌍 N(N−1)/2 증가만으로 특정 구현의 전체 scaling을 정할 수는 없다.
관련 Hylleraas/Hy-CI 다전자 확장은 three-/four-electron 적분과 선형 종속성·고정밀
선형대수의 비용을 다룬다.
[Three-electron integral 연구](https://www.nist.gov/publications/mathematical-and-computational-science-issues-high-precision-hyileraas-configuration),
[NIST Hy-CI 방법](https://math.nist.gov/mcsd/savg/parallel/atomic/index.html).
이는 숨은 비용의 문헌 근거이며 이번 scaling 측정이 아니다.
Hy-CI, JC, 다른 R12/F12를 동일 알고리즘으로 취급하지 않는다.

## WHAT THIS SHOWS / DOES NOT SHOW

확인: 후보 물리량/방법 정의, 배포 DOI/제한 라이선스, 접근 blocker, 과거 비교 자료 provenance.
미확인: 로컬 integral 구현/lowest root/guards/수렴/B 정확도/비용 우승자.
QZ 수리·force·nuclear dynamics·formation·다른 분자·world integration·production 선택 미실행.

## FINAL CLASSIFICATION

- REPRESENTATION_PILOT1_FEASIBILITY_UNRESOLVED
- R04 representation/arithmetic/target: NOT_EVALUATED_FEASIBILITY_STOP
- MULTI_R_POINT_REPRODUCTION_SUPPORTED: 판정 없음
- COST_COMPARISON_NOT_COMPARABLE
- GENERALIZATION_UNRESOLVED
- NOT_CERTIFIED / NOT_PRODUCTION_APPROVED / STOP

시험 통과와 물리 계산 0회를 분리한다.
[Verification](evidence/verification.json), [final seal](evidence/final_seal.json).
LOCAL FULL 생략 / 관련 시험으로 대체: 새 문서·증거·시험과 대시보드 안내만 변경,
기존 numerical/production/frozen source·guards·fixture 불변. 공식 기준선 미갱신.

## DESIGNER DECISION REQUIRED

AFBA_v1_0의 정식 source archive를 확보할 접근 경로 또는 로컬 파일이 필요하다.
Archive/source/license/dependency hashes, 입력 의미와 허용 사용 범위를 확인한 뒤
세 크기/세 정밀도/native guards/내부 수렴/optimizer 계약을 봉인해야 재개할 수 있다.
확보가 불가능하면 licensed 대체 구현 조사 또는 원문 기반 새 구현의 범위·허용 여부를
설계자가 결정해야 한다. 이번 feasibility gate를 자동 우회하지 않았다.
추가 source 재시도·solver 개발·계산은 자동 진행하지 않는다.

## PROCEDURAL REFERENCE / READ SCOPE

첨부 명령/AGENTS/RULES 전체, CURRENT_STATE/REPO_MAP/docs 안내 관련 초기 절을 읽었다.
H2SOLV 물리·함수·integral·code/precision/input 절을 검토했다.
Sims/Ndeke는 관련 방법/계보와 기존 봉인 전사 범위이며 이번에 전체 원문을
재독했다고 주장하지 않는다. 기존 결과 확인과 새 numerical test를 구분한다.

scientific-critical-thinking의 방법/증거/주장 구분을 적용했다.
절차적 기여를 물리 reference와 분리하여 Kassis, T., Agarwal, V., He, Y.,
Patel, D., & Brueckner, A. M. (2026),
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065),
현재 v2 metadata 확인, DOI10.48550/arXiv.2609.00065를 기록한다.
