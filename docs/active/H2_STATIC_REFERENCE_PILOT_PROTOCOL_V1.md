# 고정 핵 H₂ 정적 reference pilot — 실행 전 사양 V1

2026-10-02. 사용자 첨부의 구현/로컬 계산/commit 허용 지시에 따른 독립 연구다.
최종 electronic foundation·production BO·A-world 산술/상태·Gate 승인과 구별한다.
입력 사양 정본: [protocol_v1.json](../../electronic_pilot/protocol_v1.json).
실행 전에 campaign이 입력, 소스, 실제 H basis coefficients, dependency versions를 seal.json에 저장한다.

## 질문과 선택

사전 bond/molecule/reaction/equilibrium 입력 없이 두 고정 proton, 전자 2개의
선언한 singlet sector에서 Coulomb 전자 Hamiltonian의 낮은 에너지가 유한 R의
안정 구조와 해리 방향을 만드는가? minimum이 없거나 reference와 불일치해도
그대로 결과로 남긴다. 계산 결과를 보고 law/basis/오차 기준을 조정하지 않는다.

선택: 비상대론적 clamped-nuclei isolated Coulomb, real spherical standard contracted
cc-pVDZ/VTZ/VQZ basis, full spatial singlet CI, canonical overlap orthonormalization,
explicit Hermitian matrix + LAPACK lowest two eigenpairs. FCI는 finite basis의 모든
singlet configurations를 포함하며 SCF/단일 determinant 해리 근사를 쓰지 않는다.
PySCF 2.12.1/libcint integral backend, SciPy LAPACK, binary64, thread 1.
두 전자이므로 singlet dimension M(M+1)/2가 작고 독립 고정밀 공개 곡선이 있다.
직접 Gaussian integral engine를 새로 만드는 복잡도보다 기존 backend를 쓰며,
그 backend 자체의 독립 integral 감사는 이번에 완수했다고 주장하지 않는다.

대안: HF는 상관·해리 오류가 이 질문에 섞이고, DFT는 XC 선택 오류가 추가된다.
explicitly correlated exponential method는 고정밀 reference에 적합하지만 새 integral
recursion/고정밀 basis optimization 구현 부담이 크다. 미래 foundation 선택의 순위가 아니다.

## 정확한 energy와 symmetry

Atomic units:
`He = -1/2 Σi ∇i² - ΣiA 1/riA + 1/r12`, `ENN = 1/R`, `EBO = Ee + ENN`.
핵은 `(0,0,-R/2)`, `(0,0,R/2)`. 핵 spin/운동 없음. symmetry label을 추가로
제한하지 않고 전체 spatial-symmetric singlet space의 최저 numerical root를 계산한다.
spatial symmetric × spin antisymmetric = 전체 전자 교환 antisymmetric.
전자 Hamiltonian에는 ENN이 없으며 total에서 정확히 한 번 더한다.
proton 중심 basis는 함수 표현 위치이며 H-H bond graph가 아니다.

`S^-1/2`로 정규직교화한 h와 `(ik|jl)`에서
`Hij,kl = hik δjl + δik hjl + (ik|jl)`를 만든 뒤 대칭 pair basis에 투영한다.
SCF guess, reference energy, 알려진 결합 길이, geometry optimization, warm start가 없다.
각 점은 fresh process에서 독립 계산한다. direct eigensolve라 iteration count는
`null / not iterative`이며 임의 iteration 숫자를 지어내지 않는다.

## 실행·판정·오차·비용

먼저 각 basis의 R=0.4,2,20 sanity. 이후 0.4–4 bohr의 고정 0.1 간격과
5,6,8,10,12,16,20의 44-point curve/basis; 전체 132점.
원자 H 3개, ghost-basis H를 R=1,2,6,20에서 basis마다 별도 계산한다.
ghost 결과는 BSSE 진단이며 EBO에 보정으로 주입하지 않는다.

P1: interior sampled minimum이 같은 basis의 isolated 2H보다 낮은지.
인접 grid points로만 minimum bracket을 제시하며 연속 함수 최소의 엄밀 증명은 아니다.
P2: E(20)-2EH의 절댓값 ≤1e-6 hartree, R=10/12/16/20에서 차이 절댓값 감소.
같은 basis 원자 해리와 continuum `2EH=-1` 비교를 분리한다. 유한 R≠무한 거리.
P3: cc-pVQZ 44-point external curve max absolute difference ≤1e-3 hartree,
sampled minimum 위치 차이 ≤0.1 bohr, exact-atom 기준 깊이 차이 ≤1e-3 hartree.
이 수치는 pilot 진단 기준이며 reference uncertainty나 최종 world accuracy 요구가 아니다.
불일치 시 기준/모델을 바꾸지 않고 어느 지점에서 초과했는지 보고한다.

독립 reference: [Pachucki 2010 원고 v2](https://arxiv.org/pdf/1007.0322v2),
Eq.2, Table IV, abstract/Table I의 equilibrium 비교. 별도 checker만 읽는다.
동일 적분의 PySCF FCI contraction 비교는 R=1,2,6,20의 보조 검사이며
독립 물리/reference 감사로 세지 않는다. residual은 정규직교 finite matrix 진단이며
최저 root/continuum energy를 인증하는 enclosure가 아니다.

오차 장부: 제외 physics/model, finite basis, solver residual, arithmetic/backend,
reference uncertainty를 분리한다. basis differences는 rigorous error bound가 아니다.
overlap minimum ≤1e-10 또는 orthogonality >1e-10 또는 residual >1e-9면 REFUSED,
basis를 조용히 지우거나 축소하지 않는다. failure/traceback/부분 결과를 보존한다.

비용: basis M, singlet dimension, ERI/matrix bytes, fresh worker process peak RSS,
integral/assembly/diagonalize/solve/CPU/startup 포함 wall 시간을 기록한다.
큰 계 실행 없음. 로컬 Windows 호스트의 WSL Ubuntu CPU에서 실행, Vast/GPU 0.
cross-platform bit parity·certified rounding·전자 time history·실제 H+H 포획·힘/Pulay·
excitation/ionization/radiation·모든 화학/life·production 채택은 검사하지 않는다.

## V1 sanity 뒤 실패 수집 정책의 별도 개정

V1 sanity가 TZ R=0.4의 수치 검사에서 중단된 뒤
[protocol_v2.json](../../electronic_pilot/protocol_v2.json)을 따로 봉인했다.
Hamiltonian/basis/grid/arithmetic/허용오차를 바꾸지 않고, 실패한 점을 보존하고
나머지 독립 geometry를 한 번씩 실행하는 수집 정책만 바꿨다.
V1 원본 seal/부분 결과를 그대로 보존한다. [최종 보고서](H2_STATIC_REFERENCE_PILOT_V1.md)는
13 intentional refusal과 3 refusal-message 오류 및 후속 메시지 수정 진단을 구분한다.
