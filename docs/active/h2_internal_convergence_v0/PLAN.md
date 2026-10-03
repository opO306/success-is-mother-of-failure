# H2SOLV Internal Convergence Audit V0 — 실행 전 계약

2026-10-03. Scope: vendor 5예제 내부 종료 관측·독립 residual·observer fault injection.
R=.4 실행0 / B2 시작0 / push·merge·rebase 금지 / NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.
시작 HEAD 1a3c1264f5e3e4cd1d5b52726e7d49e845606816, 기존 Pilot 계보 유지.

## 불변 원본 / 관측 사본

VENDOR는 이전 README static executable/hash와 원래20파일을 사용한다.
AUDIT는 새 runs/ 경로에 복사한 소스에 관측 호출·독립 helper만 추가한다.
기존 계산 줄은 삭제·교체하지 않는다. 추가 블록을 제거하면 원본 source bytes가
완전히 돌아와야 한다. 원본·이전 evidence와 wrapper도 전후 hash로 확인한다.
MUTANT-low-itmax만 ITMAX=1로 바꾸며 별도 build/input/output에 둔다.
MUTANT-bad-EN은 별도 input의 EN만 -2.0으로 변경하고 AUDIT와 별도 경로에서 실행한다.
원본 예제 NMAX/NDIGITS/EN/비선형 파라미터, recurrence, root 선택, 정규화는 불변이다.

## 관측 형식과 종료 분기

실제 source h2solv.f SHA256:
aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d.
PRMTS:74 ITMAX=40, CALCEN:537 EPSKOR=zero, 539 invsg 호출.
invsg:2536 reps='1e-64'; 2541 errest=max(16*n*reps,abs(eps)).
2605 eprev=eig; 2606 eig=eold+one/sm;
2607 strict abs(eprev-eig)<errest*abs(eig)일 때 goto100.
2609 loop 자연 종료도 2613 label100 정규화로 진행한다.
관측판은 자연 종료 직후 EXHAUSTED marker를 추가한다. marker를 거치지 않고
정규화에 도착한 것은 실제 원래 수렴 분기로 구분한다. 새 threshold를 쓰지 않는다.
leq1s 첫 factorization과 매 solve의 ier, 실제 iteration index, primitive 값 및
관측용 signed/abs delta와 threshold, final ierror, 반환 wa(1)을 sidecar에 남긴다.

CALCEN invsg 직전 HH/DN 및 invsg 반환 직후 EN/WF를 원래 MPFR significand/exponent
형식으로 저장한다. pointer·미사용 limb는 제거한다. x86_64 little-endian int64 stream,
precision/sign/exponent + 최대6개의 64-bit limbs, active precision만 해석한다.
H/S는 lower triangle row order k=i*(i-1)/2+j다(HAMLNORM:677,719; avms:2662-2672).
matrix·vector는 runs/에만 두며 compact metadata/hash만 Git에 둔다.
native calibration probe와 synthetic parser/corruption 시험으로 export path를 검사한다.
과거 matrix-export branch의 upper-row index(516)를 새 decoder에 복사하지 않는다.

## 독립 residual와 precision / 판정 강도

원본 invsg/avms/dot-product 및 중간 결과를 재사용하지 않는다.
Windows Python/mpmath 160 decimal digits로 exact snapshot을 읽고 별도 packed-matrix
action으로 Hv, Sv, residual, vTSv, Rayleigh quotient를 계산한다.
계산은 stored binary inputs의 numerical 재계산이며 interval/formal proof가 아니다.
MPFUN의 NDIGITS=60은 int(60/log10(2^64)+2)=5 words=320 bits로 양자화되며
default integral은6 words=384 bits다. 실제 파일의 precision 분포도 검증한다.
고정밀 계산은 저장 전에 생긴 손실이나 integral truncation을 복구하지 않는다.

기존 Pilot의 vendor residual/normalization 승인 계약은 없다(scoped source/report 검색).
따라서 residual/normalization/RQ는 **MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD**다.
값을 본 뒤 PASS tolerance를 만들지 않는다. finite/positive vTSv, 차원·layout·hash·
종료 branch의 자기 일관성은 검사하되, 수치 잔차가 충분하다는 승인과 구분한다.
기록: ||r||2, ||r||inf, vTSv, |vTSv-1|, ERQ, ERQ-E,
eta_inf=||r||inf/(||H||inf+|E|*||S||inf)/||v||inf,
absolute-action scale와 cancellation condition ratio.
이 때문에 전체 H2SOLV_VENDOR_INTERNAL_SOLVER_CONVERGENCE_SUPPORTED 승격은
residual/normalization 계약 없이는 보류한다. 실제 inverse-iteration 분기 지원은 별도다.

## root 진단

wa(1)은 leq1s의 wa(n+1), 즉 shifted H-EN*S의 음의 pivot inertia count다.
EPSKOR=0 및 양의 S라는 조건 아래 초기 EN 아래 generalized root 수라는 source 의미다.
독립 SPD/정확한 inertia 증명은 이번 값만으로 얻지 않는다.
각 case에 raw H/S를 float64로 변환하여 SciPy eigh(type=1)의 lowest/second roots를
진단한다. triangle mirror는 저장 형식 복원이며 평균 대칭화·rank cutoff·diagonal shift 없음.
binary64 S에서 양의 정부호성을 잃으면 UNRESOLVED로 기록하며 원래 S 결함으로 단정하지 않는다.
root 차이를 모순으로 쓰려면 S>0, cond2(S)*n*eps64<=1e-8 및
lowest gap 대비 잔차 기반 diagnostic uncertainty 조건을 먼저 만족해야 한다.
이 기준을 만족하지 못하면 root값은 MEASURED 또는 UNAVAILABLE이며 arbitrary-precision truth가 아니다.
diagnostic uncertainty는 두 binary64 eigensolver vector의 ||Hx-eSx||2/sqrt(lambda_min(S))
최댓값 +100*cond_scale*max(1,|lowest|,|second|)이다. gap>4*uncertainty이고
cond_scale<=1e-8일 때만 |E_invsg-lowest|>uncertainty를 모순으로 취급한다.
이는 엄밀한 eigenvalue enclosure가 아니라 사전 정의한 binary64 진단 제한이다.

## 실행 순서와 STOP

1. 봉인/hash, calibration·wrapper 시험, 별도 AUDIT build.
2. 같은 원래 input으로 VENDOR/AUDIT 및 각각 원래 example 실행, scientific stdout와
   wavefunction byte 비교, 실제 종료 sidecar·독립 residual·root 진단.
3. 최초 authoritative output/종료/error/구조 모순에서 다음 예제를 중단하고 반례 보존.
4. observer용 low-ITMAX, 가능하면 bad-EN mutant를 별도 실행. mutant 실패는 의도한 결과이며
   공식 예제 physics 판정에 합치지 않는다. detector가 못 잡으면 observer gate FAIL/STOP.
5. 관련 시험·보고·local commit 후 STOP. R=.4/B2는 성공해도 금지.

환경: 기존 Ubuntu-24.04 gfortran13.3/static MPFR4.2.1/GMP6.3, OMP_NUM_THREADS=1,
OMP_DYNAMIC=FALSE. Native process timeout600초, Python 독립 검사 timeout600초.
오류·불일치 자동 retry 없음. build/test 개발 실패는 보존, 동일 실패3회면 중단.

절차: scientific-critical-thinking의 evidence/interpretation 분리.
Software reference: Kassis et al. (2026), [Scientific Agent Skills](https://arxiv.org/abs/2609.00065).
산술/진단 근거: [MPFR manual](https://www.mpfr.org/mpfr-current/mpfr.html),
[SciPy eigh](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh.html).
이는 H2 물리 correctness reference가 아니다.
