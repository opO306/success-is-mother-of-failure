# C1-B1 outer dt40 적분기 비교 — 실행 전 계획/프로토콜

2026-10-01. 기준 HEAD/실제 origin/master 508bba4fd01826aa6fb52f91c5011413a114f1aa, clean, ahead/behind 0/0. 사용자의 첨부 비교 실험 지시와 $1/hr·총 $1 상한 승인을 근거로 Vast 한 노드 CPU 실험을 수행한다. GPU 계산·push 금지. production 및 기존 O-1 STOP/unsupported 판정과 원인 격리 TIME_DISCRETIZATION_SUPPORTED를 유지한다.

**Goal:** outer dt40 새 후보 최대 두 개와 저장 KDK40/20 baseline의 관측 정확도·계산 비용·확장 복잡도를 비교한다. 새 production 구현/채택 판정은 하지 않는다.

**Architecture:** 새 관측 package c1b1_integrator_benchmark에서 갱신/계측/단계별 gate를 구현한다. 기존 공개 모델 파서, c1b1_o1_diagnostic.kdk.Lang.value_derivative를 byte 불변으로 사용한다. 기존 연속 기준을 재생성하지 않고 각 진단 출구의 짧은 연속 구간만 보정한다. 후보 수식/계수·소스·입력·baseline 해시는 첫 trajectory 전에 봉인한다.

**Tech:** Python/mpmath 1.3.0, 고정밀 40/60자리, gzip JSONL, pytest. 최종 산란 실험은 Vast만 사용. 로컬은 파일 준비 및 짧은 대수 시험만 가능하며 장시간 trajectory 계산 없음.

## 수식과 출처 — 후보 두 개로 고정

**A: Yoshida/Forest–Ruth 4차 symmetric composition.** s=2^(1/3), w=1/(2-s), z=-s/(2-s). 2차 대칭 흐름 S2(w h) S2(z h) S2(w h)를 대수적으로 합친 kick/drift 계수 사용: kick [w/2,(w+z)/2,(w+z)/2,w/2], drift [w,z,w]. outer h=40. 내부 음수 drift 약 -68.0976568 a.u.를 표시하고 모든 내부 drift chord의 r_min을 검사한다. adjacent 경계의 force 재사용은 동일한 정확 q만 허용한다. 새 갱신은 기존 KDK step을 복사/호출하지 않고 계수 흐름으로 구현한다. 출처: Yoshida 1990, https://tlakoba.w3.uvm.edu/math6737/for_final_topics/SSM_1990_Yoshida.pdf ; Chin–Chen 2003의 식9도 같은 합성을 설명한다.

**B: Chin–Chen forward 4A.** kick h/6, drift h/2, middle kick 2h/3 Ftilde, drift h/2, kick h/6. Ftilde=F+h²/(48 mu) grad(|F|²). 중심력 F=-V'(r) q/r이므로 추가항은 h²/(24 mu) V'(r)V''(r)q/r. mu=m/2를 누락하지 않는다. 모든 내부 drift 계수 양수. V''는 기존 value_derivative의 dV/dr를 mpmath.diff로 추가 계산하며 evaluator 자체를 최적화/변경하지 않는다. 실제 derivative 호출 횟수·추가 PES 비용을 센다. 임의 coefficient tuning/세 번째 후보 없음. 출처: https://arxiv.org/html/astro-ph/0304223 식15–18. 이 연구는 단위 질량 표기이므로 mu를 복원했다.

계수는 위 algebraic/rational 식에서 해당 dps로 계산한다. 60자리 값도 봉인에 기록한다. gradient 항은 적분 알고리즘의 수치 항이며 원래 Hamiltonian/PES/보존량 정의를 바꾸지 않는다.

## 실행 순서와 사전 기준

1. [ ] 손계산 harmonic/4차 수렴/역행·mass factor/음수 drift 감시/gate 시험을 RED→GREEN으로 검증한다.
2. [ ] 기존 입력·연속 값·O-1/원인 격리 원본 hashes 및 새 소스/계수/아래 기준을 봉인한다.
3. [ ] 기존 stopped 노드 한 대만 시작한다. CPU/RAM/vCPU/가격/시각/가용 affinity/패키지/MP backend를 기록한다. CUDA_VISIBLE_DEVICES=-1, BLAS/OpenMP threads=1. 최대 process 4, 각각 별도 CPU affinity. GPU는 연산에 쓰지 않는다.
4. [ ] 첫 단계는 boundary_pass 단 하나, 각 후보 40/60자리. χ/direction/r_min/final q,p의 자릿수 변화 <=1e-20. 그렇지 않으면 UNRESOLVED_PRECISION로 종료. 동일 CPU 슬롯에 대한 60자리 시간과 전체 observer 시간을 기록한다.
5. [ ] 비용 보정은 저장 KDK20 trace에서 사전 고정한 균등 index 1024개를 읽어 독립 one-step kernel을 재기동한다(연결된 baseline 궤적/새 χ 생성 금지). 이전 step의 force cache를 측정 밖에서 준비하고, end force와 갱신 kernel을 측정한다. 3 반복 median CPU/wall 및 범위를 기록한다. 동일 표본에서 후보 kernel도 측정한다. 미시 benchmark이므로 전체 KDK20 원격 실행 시간이라고 쓰지 않는다. 기존 local full-trajectory 시간은 역사값으로 별도 표시한다.
6. [ ] 1차 accuracy |delta χ|<=1e-5, r_min>=2.4의 모든 내부 chord, max stored |deltaH|/De<=1e-3, max deltaL<=1e-20. 미준수 candidate STOP. 기존 KDK20 각도 오차/후보 오차를 gain으로 표시하지만 한 점수로 합치지 않는다. kernel 비용 median ratio>2면 REJECT_COST; ratio>1이고 gain<10이면 REJECT_COST. 비용<=1 및 오차<=KDK20이면 BEATS_KDK20_KERNEL. 그 외 gain>=10 및 cost<=2면 PROMISING_PARETO로 제한된 panel 진행. 이것은 production 채택 아님. 비용 측정이 불안정(3회 max/min>1.2)이면 UNRESOLVED_COST로 STOP.
7. [ ] 살아남은 후보만 기존 O-1 9-input panel의 나머지 8개를 60자리 계산한다. boundary_pass의 1차 결과를 재사용해 총9개로 집계한다. 필요한 경우 40자리 안정 확인만 추가한다. 각 입력별 새로운 χ·direction·chord min·energy·L·count·CPU/wall/peak RSS와 기존 KDK40/continuous 값을 나란히 기록한다. KDK20은 boundary_pass 외에 저장값 없으면 N/A. 새 random/rho=-0.0001 없음.
8. [ ] 모든 결과/실패/exit/log/환경/해시를 회수하고 로컬 보존을 확인한 즉시 instance stop한다. 총 $1 또는 시작 후 최대1시간 전 종료(가격 확인 후 안전 시간 제한 적용). 다운로드 실패 시 종료와 데이터 보존 위험을 즉시 보고한다. 다른 기존 instance는 건드리지 않는다.
9. [ ] 문서 및 최종 A/B/C 판정. accuracy·kernel cost·실제 whole-run CPU/wall·검증복잡도 구분. 엄밀 end-to-end baseline 비용이 없으므로 kernel 우위만으로 전체 production cost 우위를 인증하지 않는다. 자료 부족/불안정이면 C. 기존 코드를 변경하지 않으면 관련 시험 대체 및 LOCAL FULL 생략 이유를 명시한다.

## 관측·안전·원본

기존 연속 계산은 각 A의 정확 raw 출구 반경에서 정의됐다. 그 반경을 HP의 최초 outbound 전체 outer step 종료 표면으로 사용한다. HP의 실제 overshoot까지 기존 H,L outbound radial quadrature만 추가하고 원본 reference는 불변이다. χ는 signed principal finite-outlet angle, extra winding은 sweep으로 기록한다. 내부 drift 선분 전부를 r_min 검사하고, 외부 chord minimum과 내부 chord minimum을 구분해 저장한다. 내부 partial kick 상태의 에너지는 원래 full-time energy와 같은 지표가 아니므로 outer stored energy를 기준으로 비교한다. 필요 시 내부 최대도 별도 표시한다.

force vector evaluation과 scalar PES call의 정의를 분리한다. cache miss의 PES 평가, force-gradient용 scalar derivative 평가, 관측용 추가 PES 평가, endpoint correction용 PES 평가를 각각 기록한다. CPU/wall은 kernel과 전체 trajectory/observer를 구분한다. memory는 Linux ru_maxrss이다. 두 후보와 KDK20 비용 표본은 동일 arithmetic precision·동일 evaluator·동일 node/affinity에서 측정한다. coefficient/허용오차/physics/force 최적화/production 계약 변경은 없다.

many-body: 합성법은 일반 separable Hamiltonian에 적용 가능하나 음수 stage의 domain/운영 계약이 별도 과제다. 4A는 일반 mass-weighted Hessian-force product가 필요하며 이번 scalar radial gradient 구현은 Ar-Ar 두 입자 전용이다. full many-body 구현·오차 budget·검증 계약은 이번 범위 밖이다. replay 성공은 새 integrator/O-1 성공을 뜻하지 않는다.
