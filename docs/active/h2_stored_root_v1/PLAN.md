# H2SOLV Stored-Matrix Lowest-Root Audit V1 — 실행 전 계약

2026-10-03, start HEAD ab3569b. 기존 Pilot 계보에서 새 분석 checker/test/report만 추가.
VENDOR/AUDIT 원본·소스·실행물·봉인 H/S/E/v 변경 없음. 원래 invsg 직전 lower-packed H/S 사용.
H/S320bit, 반환 E/v384bit, initial_EN native320bit를 exact dyadic으로 복원한다.
320bit 입력을 80자리 중간값으로 대체하지 않고 양 끝 방향 반올림으로 포함한다.

## 수학·독립성·판정 등급

독립 Python parser와 새 C++ MPFR interval Schur LDL^T. H2SOLV numerical routine이나
이전 residual/parser의 계산 코드는 import/reuse하지 않는다. WA1은 비교 대상일 뿐이다.
구간 연산은 RNDD/RNDU, 곱의 네 endpoint 조합, 0을 포함하지 않는 divisor의 역수다.
각 pivot은 exact matrix의 unpivoted LDL recurrence에 대한 inclusion interval이다.
완전한 nonzero pivot들의 부호는 Sylvester congruence로 inertia를 확정한다.
zero-containing pivot은 pivot 교체·중간값 선택 없이 UNCERTAIN. 이 단순 알고리즘은
비특이 행렬 [[0,1],[1,0]]도 거부한다. 거부를 특이성 증명으로 해석하지 않는다.
SPD 중 음의 pivot은 즉시 거부하며, 따로 출력한 dyadic Schur direction의 q=x^TSx를
Python integer accumulation으로 정확히 확인한다. q<0이면 stored S가 SPD 아님이 확정된다.
rank는 SPD 성공에서만 full rank, 실패 prefix로 전체 rank/inertia를 추정하지 않는다.

모든 positive interval pivots일 때 STORED_S_SPD_CERTIFIED(이 저장 행렬·MPFR/GMP/자체
구간 구현의 신뢰 기반에 한정). min pivot은 lambda_min이 아니다. 전역 하한은
lambda_min >= min(D_lower)/(n*max(b_i)^2), b_i=1+sum_{j<i}|L_ij|_upper*b_j_upper.
출력 Schur 방향의 exact RQ는 lambda_min의 상한이며 실제 최소 고유값으로 부르지 않는다.
H/S symmetry는 lower-packed 저장값의 mirror 복원으로 정확하다. 독립 upper half가
없으므로 적분 generator가 원래 양쪽을 같은 값으로 계산했다는 별도 증명은 아니다.

SPD일 때 S=C C^T와 T=C^-1 H C^-T를 사용하면
H-sigma S=C(T-sigma I)C^T. 따라서 negative inertia=#(lambda<sigma).
y=C^T v, r=Hv-ESv이면 (T-EI)y=C^-1 r.
스펙트럼 정리에서 dist(E,spectrum)<=||C^-1r||/||y||=sqrt(r^TS^-1r/nS)=rho.
|RQ-E|<=rho도 Cauchy–Schwarz 결과다. rho가 작은 사실만으로 lowest를 선언하지 않는다.
출처: [LAPACK GSEP](https://www.netlib.org/lapack/lug/node54.html),
[MPFR4.2.1 rounding](https://www.mpfr.org/mpfr-4.2.1/mpfr.html). 위 inertia/잔차 관계는 직접 유도.

## 사전 고정 수치·비용

검사 ladder80/120/160/240 decimal, 실제 bits266/399/532/798(ceil(d*log2(10))).
각 SPD/inertia에서 처음 닫힌 부호 판정에서 멈추고 UNCERTAIN일 때만 다음 rung.
max rung unresolved면 해당 case STOP. 실제 supplier precision/NMAX/NDIGITS 변경은 없다.
factor process timeout600초, 자동 재시도 없음. 순차 실행, 새 수치 라이브러리 설치 없음.
root initial delta=2^-64, E±delta. printed18자리보다 좁은 저장 root 주변 진단 폭;
reference를 읽거나 결과에 맞춰 widen하지 않는다. endpoint0/1일 때만 deterministic
bisection최대8회 또는 width<=2^-70. 첫 점은 (3low+high)/4로 E 자체의 singular shift를
피하고 이후 midpoint. E가 구간 밖으로 나가거나 uncertain/다른 count면 STOP.
second root는 bounded scope에서 추가 spectral search를 하지 않아 DEFERRED_COST이다.

raw residual/nS/RQ 및 SPD일 때 transformed residual은 독립 mpmath240자리로 MEASURED.
임의 residual tolerance 없음. root 성공에서 RQ 안쪽·|RQ-E|<=rho·[E-rho,E+rho]와
bracket의 교차 및 포함을 측정한다. 수치 측정의 포함은 interval-certified eigenvector
backward error나 formal certification으로 승격하지 않는다. 모든 case 성공해도 전체
H2SOLV/physical integrals/NMAX는 NOT_CERTIFIED / production 미승인이다.

## 순서·all-five와 STOP

prepare 기존 bytes 검증 → synthetic validation → code/test/PLAN/input/protocol 봉인 →
기존5개 저장 행렬만 검사. all-five 지시와 fail-closed 지시를 함께 적용: case별 S 실패는
그 case의 inertia/root/rho를 실행하지 않고 기록한다. 다른 case의 동일한 사전 승인
검사는 완료한다. aggregate에 한 case라도 실패/미확정이면 UNRESOLVED/STOP이며 확대0.
WA1 불일치가 있어도 root 자체의 분리된 판정은 남긴다. 미확정 WA1 의미는 성공으로
세지 않는다. Fault detector 실패/실행 오류는 즉시 전체 STOP, 같은 실패3회 전에 보고.

Synthetic: known exact congruent roots/SPD, 극단적 SPD2^-600, maximum rung ambiguity,
indefinite, exact root/near root, nonsingular zero pivot, parser/false count/layout corruption.
actual test-only copy의 S[0,0]=-abs(S[0,0])-1로 negative direction을 만든다.
authoritative 파일은 전후 hash 확인. 기존 authoritative computation을 반복하지 않는다.

관련 시험으로 대체 가능한 새 isolated analysis only. LOCAL FULL 기준선 갱신 없음.
local commit 허용, push/merge/rebase 금지. R=.4/B2/NMAX/NDIGITS/OMEGA sweep0.
scientific-critical-thinking으로 관찰과 주장을 분리한다. Software reference:
Kassis, Agarwal, He, Patel & Brueckner (2026),
[Scientific Agent Skills](https://arxiv.org/abs/2609.00065), 현재 arXiv v2 확인.
