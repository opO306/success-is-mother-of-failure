# Atomic / Electronic Matter Foundation V0

**후속 구현 기록(2026-10-02):** 사용자가 §8의 고정 핵 H₂ pilot 실행을 지시하여
[독립 static pilot 보고서](../active/H2_STATIC_REFERENCE_PILOT_V1.md)를 추가했다.
DZ/TZ 표본 안정점·해리 방향과 일부 수치 비교가 있으며 QZ 최소점/전체 curve는
수치 거부로 미해결이다. 본 연구 원문의 "실행 없음"은 이 조사 당시 기록이고,
후속 결과로 concrete foundation/BO/world state/dynamics를 승인하지 않는다.

**상태: FOUNDATION SELECTION RESEARCH / DESIGN ONLY.** 2026-10-02. 설계자가 변경한 것은 Drude의 위치와 아래 층에서 chemistry를 계산한다는 방향이다. 이 문서는 concrete authoritative state, reactive/ML/electronic model, 양자/고전 경계, 측정 법칙을 승인하지 않는다. 새 코드·계산 실행·production 선택은 없다.

기존 [Support Map §13](STAGE1_PHYSICS_SUPPORT_MAP_V0.md#13-stage-1-first-material-model-selection--선택-기록-v0)은 **SUPERSEDED AS PRIMARY FOUNDATION / RETAINED AS EFFECTIVE / COMPARISON MODEL CANDIDATE**다. 조사 원문·출처를 보존한다. 기존 `E — REALITY_DATA_INSUFFICIENT`, 준비 M1–M4 미승인, C1-B1 `NotCertified`/활성 Gate/기존 STOP 상태를 승격하지 않는다. 이번 설계는 [CURRENT_STATE](../../CURRENT_STATE.md)의 Gate를 통과한 것으로 세지 않는다.

## 1. 설계자가 먼저 판단할 열 가지

1. **원자만으로 충분한가?** 핵의 종류·좌표·운동량에 고정 pair potential만 붙이는 일반 모델은 요청한 전자 이동·이온화·열린 chemistry의 충분한 기반이 아니다. 원자 배열에서 전자 상태를 풀거나 그 효과를 유효 many-body law로 담는 다른 뜻의 “원자 모델”은 별도 평가해야 한다.
2. **왜 부족한가?** 가까워졌다는 것만으로 전자의 재배치·반대칭성·교환/상관·spin·이산 전자 상태를 정하지 못한다. pair potential도 안정 배열/cluster를 만들 수는 있다. 그것을 새로운 전자구조까지 표현한 증거로 바꾸면 안 된다.
3. **전자를 하나씩 world state로 넣어야 하는가?** 자동 결론은 아니다. 고전적인 전자 구슬은 양자 전자와 다르다. wavefunction/density matrix·전자구조 solver처럼 electron count를 보존하면서 전자를 양자적으로 표현하는 후보가 있다.
4. **전자구조 solver가 더 적절한가?** 작은 ground-state 구조/해리 검증에는 유력하다. 그러나 핵 위치마다 전자를 재최소화하는 Born–Oppenheimer(BO) 방식은 실제 전자 시간 이력 전체를 계산하는 방식이 아니다. 최종 foundation 적합성은 미결이다.
5. **결합을 미리 넣지 않는 최소 표현은?** 제한된 ground-state 과제의 실용적 후보는 `핵종/배열 + 전체 전자 수 + spin/전자 sector + 전자 Hamiltonian/근사 + energy solve`다. reaction/bond ID 없이 energy minimum·해리 곡선을 계산할 수 있다. 이는 모든 chemistry를 위한 유일한 최소 상태라는 정리가 아니다.
6. **모르는 reaction path도 열 수 있는가?** 이름/반응 목록을 참조하지 않는 law라면 이름 없는 배열도 계산할 수 있다. 하지만 계산 가능, 해당 경로의 물리적 표현 가능, 현실 정확성, 수치 검증은 네 가지 다른 판정이다.
7. **계산량은 어디서 폭발하는가?** charge/electronic solve, basis·전자 수·spin sector 증가, 상관/여기/연속상태, 매 전이의 독립 검증, 전자 상태 역사 저장에서 각각 증가한다. §7에서 구조식으로 비교한다.
8. **가장 싼 구조는?** 전체 열린 chemistry를 현실적으로 지원하는 보편적인 최저비용 모델을 확인하지 못했다. 같은 승인 Hamiltonian의 작은 static vector, streaming/iterative evaluator, sound enclosure/refinement/cache가 먼저 비교할 계산 구조다.
9. **싼 구조가 물리를 바꾸지 않는가?** 연산 순서·정밀도·동일 결과를 보장한 cache는 계산 기술 후보다. BO/DFTB/ReaxFF/ML로 바꾸기, 핵 양자성/여기/방사를 제거하기는 물리 모델 변경이다.
10. **첫 pilot은 무엇인가?** 구현자 추천은 **고정 핵 H₂의 bond-ID 없는 전자 에너지/해리 곡선 reference pilot**, atomic H/H₂⁺ 보조 검사와 singlet/triplet 비교다. dynamics·안정 포획·production 채택은 아니다. 입력 grid/basis/reference/error는 실행 전 설계자 결정이다.

## 2. CONFIRMED FROM SOURCES — 알려진 구조와 근거의 강도

| 사실/근거 | 정확히 뒷받침하는 범위 |
|---|---|
| Hohenberg–Kohn, Kohn–Sham의 ground-state 전자구조 틀 | 특정 Hamiltonian/정리 조건에서 ground-state density/energy를 다루는 틀 [R1–2]. 실제 approximate XC가 exact라는 뜻도, 임의 순간 density 하나가 모든 quantum history를 정한다는 뜻도 아님 |
| BO AIMD는 핵 좌표에서 electronic energy를 구하고 그 force로 핵을 움직인다 | 원 방법 설명 [R3]. electronic minimization/가상 orbital dynamics와 실제 전자의 time evolution을 구별해야 함 |
| ReaxFF는 거리 의존 bond order를 쓰고 fixed bond graph를 요구하지 않는다 | 탄화수소 원 parameterization [R4]. LAMMPS 공식 문서에는 서로 다른 version·식/parameter sign 차이·QEq 조건이 명시됨 [R5]. 모든 chemistry/원소가 검증된 것은 아님 |
| COMB도 가변 charge와 bond-order/many-body 항을 사용한다 | 공식 energy/QEq 설명 [R6]. partial charge solve는 실제 electron wavefunction이나 이온화 이력과 다름 |
| DFTB의 electronic part와 repulsive fit는 parameter set에 의존한다 | 공식 설명/파일 목록 [R7]. 3ob 목록에는 H/O/Na/K/Cl/Ca가 있으며 다른 set를 임의 혼합하지 말라는 경고가 있음. 원소 이름의 존재는 모든 coordination/charge/반응 지원 증명이 아님 |
| GFN2-xTB는 Z≤86의 global/element parameter와 multipole electrostatics·density-dependent dispersion을 사용한다 | 원 논문의 대상은 주로 구조·진동·비결합 물성 [R8]. 폭넓은 원소 목록을 반응 barrier·ionization·excited state의 포괄적 정확성으로 승격하지 않음 |
| ML potential은 학습 reference와 원소/charge/spin 범위를 가진다 | 공식 MACE 목록 [R9]: OFF23의 neutral organic/SPICE와 MP 계열의 material/PBE+U 범위는 다름. OMol25는 variable charge/spin/reactive 구조도 포함 [R10]. “모든 ML이 neutral-only”라는 판단은 틀림 |
| 최신 ML에도 nonlocal polarization/charge-transfer 표현 후보가 있다 | MACE-POLAR-1의 2026 preprint [R11]는 OMol25와 spin-charge density/장거리 update를 사용하고 일부 charge-transfer/field 사례를 평가함. 저자는 liquid density의 실험 대비 약 5–10% systematic 차이도 보고함. 무조건 정확하다는 승인 아님 |
| approximate DFT에는 fractional-charge/static-correlation 문제가 있다 | 관련 원 연구 [R12]. 결합 해리·charge transfer에서 solver tolerance만 줄여 해결되는 error가 아님 |
| H₂의 고정 핵 BO potential에 고정밀 wavefunction reference가 존재한다 | Pachucki의 singlet 연구 [R13], internuclear distance 0.1–20 a.u.의 연구 결과. 이 범위를 pilot grid로 자동 채택하지 않음. 실제 spectrum에는 nuclear/adiabatic/nonadiabatic/relativistic/QED 보정도 필요 |
| electronic QMC는 stochastic wavefunction reference 계열이다 | 방법 연구 [R14]. fixed-node/통계 오차가 있으며 reference 역할과 A 내부 난수 사용 허용은 다른 문제 |

문헌 결과는 재실측하지 않았다. 원 논문·공식 문서·저자 preprint의 읽기 범위는 §11에 기록한다. 학습 데이터, fitting 성능, independent prediction, 구현 일치, rigorous numeric certificate, 현실 지원은 분리한다.

## 3. FOUNDATION CANDIDATES — 목적·확장·비용·싼 대안·장점 순서

| 후보 | 실제 해결하는 문제 / 열린 가능성 | 규모를 키울 때의 한계 | 계산/검증/유지 비용 및 더 싼 구조 | 그래도 필요한 장점 |
|---|---|---|---|---|
| A: fixed topology / Drude | 지정된 비반응 분자·물/ion의 힘/분극. 일반 topology 변화는 입력 밖 | 해리/proton/redox/새 종에서 law가 끊김. 막은 추가 cross 필요 | 장거리+분극 solve, topology/parameter 관리. streaming/동일 모델 enclosure 가능; chemistry를 추가하는 대체는 아님 | 비반응 domain 비교·빠른 effective 후보·실험 cross-check |
| B: ReaxFF / COMB | bond-order/가변 partial charge로 graph를 사후 분류. 반응 ID 호출 없이 일부 형성/파괴 가능 | functional form·valence/angle/charge fit와 element combination에 묶임. 이름 없는 coordination도 계산은 하지만 extrapolation 가능 | neighbor pair/triple/quadruple·QEq·cross parameter. 같은 law의 sound iterative charge solve/neighbor 계산 후보 | 특정 reactive material에 큰 계/긴 시간의 실용적 비교 후보 |
| C: MLIP — local 및 nonlocal | electronic reference PES/forces 등을 학습. 새 geometry에서 topology 변화 가능, charge/spin/nonlocal 입력 여부는 모델별 | OOD geometry/중간체/이온화/field/드문 collision. 학습 reference error 상속. local 모델의 장거리 누락; nonlocal도 guard 필요 | network·neighbor·charge update, training/reference data·weights·고정 checkpoint·독립 evaluation. frozen inference 최적화 가능 | 명시한 reference/domain의 많은 배열을 빠르게 비교, 실패 후보 탐색 |
| D1: semiempirical / xTB | 근사 electronic Hamiltonian을 풀어 전자 재배치·energy/force 평가 | minimal basis/fit·spin·금속/강한 field/해리 error. 구조 최적화용 fit≠반응 전체 정확성 | SCF/diagonalization·parameter/dispersion·force response. 동일 Hamiltonian iterative evaluation 후보 | 원소 폭이 넓은 저비용 electronic 비교 모델 |
| D2: DFTB / SCC-DFTB / DFTB3 | reference density expansion+SK electronic 항+repulsion으로 electronic response/결합 변화 계산 | pair set·repulsive fit·정해진 expansion/charge 환경. 3ob H–H 후속 수정 존재 자체가 단순 element coverage의 한계를 보임 | SK pairs/versions·SCC·basis/gradient 검증. 다른 set 혼합을 최적화라 부를 수 없음 | 공동 parameter가 있는 조건에서 electronic component/reference 비교 출발점 |
| D3: ground-state DFT | 같은 nuclei/전자 sector의 energy surface·density; bond ID 없이 변화 가능 | XC/self-interaction/strong correlation·basis/PP·spin branch. ground state는 excited dynamics/방사 아님 | SCF·grid/basis·exchange·Pulay·branch/수치 enclosure. locality 기반 가속은 조건과 오차 필요 | atom 배열을 화학 목록 없이 계산하는 폭넓은 틀과 현실/고급 reference 비교 |
| D4: TDDFT/비단열 전자-핵 접근 | 초기 전자 상태와 실제 시간 response를 다루는 더 상세한 후보 [R15] | XC memory/couplings·핵 양자성·spin-orbit·continuum·EM/measurement. Ehrenfest만으로 branching/decoherence 해결 안 됨 | orbital/state/time step/field memory와 독립 history 검증. 표면을 확률 추첨하는 알고리즘은 현재 A에 자동 도입 불가 | BO가 빠뜨리는 여기·시간 이력 문제를 직접 검토 가능 |
| E1: wavefunction / high-level ab initio | antisymmetry와 correlation을 직접 다루는 HF/CI/CC/multireference/explicitly-correlated reference | HF/일부 single-reference 해리 실패, active-space 누락, basis/relativity/QED/핵 운동 한계 | canonical CC/CI·integral/storage·force response. exact symmetry/block·certified matrix-free 가능, active-space 축소는 물리 오차 필요 | 작은 계의 강한 독립 electronic reference; finite-basis FCI와 continuum 정확성을 분리 가능 |
| E2: electronic QMC | 작은/더 큰 전자계의 correlation reference | stochastic sampling/fixed-node/sign·forces/rare data·통계 error | samples×per-sample work, walker 기록/통계. seed 재현≠exact reference certificate | 다른 systematic error를 가진 외부 reference 비교 |

### 3.1 지원 원소와 chemistry bias

* A는 SWM4와 고정 ion inventory까지의 과거 조사이며 새 foundation이 아니다. B는 **하나의 joint parameter 파일**의 원소/교차/함수형을 읽어야 한다. ReaxFF 원 연구 C/H, LAMMPS의 C/H/O/N 예시, COMB의 Si/Hf/O 예시는 각각의 범위이며 “ReaxFF/COMB 전체 지원 원소 목록”이 아니다. 필요한 H/O/Na/K/Cl/Ca 및 더 넓은 계의 완전한 joint reactive parameter inventory는 이번에 승인하지 않았다.
* C는 OFF23/MP/OMol/Polar를 한 모델로 합치지 않는다. R9의 model별 coverage/teacher를 구분하고 실제 checkpoint의 elements·charge/spin·cutoff·field API·weights/license·training split을 이후 고정한다. 이 조사에서 개별 checkpoint의 전체 parameter/element inventory 감사는 하지 않았다.
* D1의 Z≤86, D2의 3ob 종 목록, D3/E의 선택 가능한 nuclear Z는 서로 다른 의미다. D3/E도 basis/pseudopotential/relativity·전자 수/상관 처리가 빠지면 해당 원소의 현실 지원을 확보하지 못한다.
* B의 bond-order 항, C의 training distribution, D1/D2의 fit/repulsion, D3의 XC/basis, E의 ansatz/active space 모두 bias/근사 또는 representation restriction을 가진다. reaction database를 호출하지 않는다는 이유로 무제한 transferability를 주장하지 않는다.

### 3.2 현상별 표현 가능성과 물리적 한계

| 현상 | B/C에서의 의미 | D1/D2/D3의 ground-state electronic 후보 | 더 상세한 상태/법칙이 필요한 부분 |
|---|---|---|---|
| bond formation/breaking | parameter/teacher PES가 표현하는 graph 변화 | total energy의 안정 배열/해리·density 변화, fixed bond 입력 없이 가능 | near-degeneracy/여러 surface·안정화 dynamics·radiation은 별도 |
| charge transfer | QEq partial charge 또는 learned redistribution; 전자 이동 그 자체의 시간 해 아님 | fixed total N_e 안에서도 fragment density/charge 분포 변화 가능 | electron phase/coherence·비단열 전류·fragment charge definition/measurement |
| proton transfer | 지원 PES 위 고전 H 핵 이동 | over-barrier H 핵 이동 가능. H+ 객체를 이동시키는 reaction 명령 불필요 | tunneling·zero-point·quantum isotope dynamics는 classical nuclei로 지원 안 됨 |
| ionization | charge label 변경/fit가 electron escape를 구현하지 않음 | 다른 N_e/charge sector의 energy 차이를 연구할 수 있음 | 실제 방출은 continuum/전자 상태·장/경계 필요. 고정 전체 N_e여도 전자가 세계 안의 자유 상태로 이동하는 이온화는 원칙적으로 가능; 전자를 삭제하는 규칙이 아님 |
| spin / spin crossing | 버전별 입력/학습 여부, QEq만으로 표현 못함 | spin-polarized/sector별 계산 가능. unrestricted M_s와 순수 S² 상태를 혼동하지 않음 | spin-orbit 및 crossing/coupling의 시간 법칙 필요 |
| excited state | ground-state PES만 있으면 빠짐 | ground-state SCF 반복은 실제 들뜸 이력이 아님 | state-specific excited methods/TDDFT/다중 상태 wavefunction 및 준비 조건 |
| metal coordination | 지원 element-pair/coordination dataset에 의존 | 가능성은 있으나 core/valence·spin·strong correlation 검증 필요 | oxidation/multiplet와 ligand/solvent cross, relativistic 요구 |
| dispersion | source-defined empirical/learned 항의 범위 | semiempirical dispersion·XC/nonlocal/추가 correction별. 중복 추가 금지 | reference correlation/장거리 다체 검증 |
| strong field | 입력 가능 여부와 정확성은 별도 | scalar field/basis 안의 반응으로 제한될 수 있음 | continuum ionization/비단열·retardation·방사 및 source energy 장부 |

새 geometry/coordination/charge distribution/intermediate/이름 없는 구조에 대해 A는 고정 topology 밖이면 표현 불가, B/C는 수치 출력이 있어도 parameter/OOD guard에서 미결, D/E는 Hamiltonian의 동일 수식을 적용하되 basis·해 존재/상관/field domain에서 미결일 수 있다. **이름 없는 상태를 거부하지 않는 것과 모든 현실 경로를 열어 둔 것은 다르다.**

## 4. Authoritative state 후보 — 상태·파생 변수·분류값

서로 다른 세계 후보를 비교한다. **S0** fixed/reactive/ML effective nuclei world, **S1** semiclassical nuclei + ground-state BO, **S2** semiclassical nuclei + time-dependent electrons, **S3** nuclei/electrons/필요한 field까지 quantum state. 어느 것도 자동 채택하지 않는다.

| 항목 | S1 BO 후보 | S2/S3의 변화 / 판정 경계 |
|---|---|---|
| nuclear identity Z / isotope / mass | authoritative constant/state 후보. 원소는 결합·분자 이름과 다름 | nuclear reaction/질량 변화까지 지원할지는 별도. 낮은 에너지 chemistry만으로 자동 확정 안 함 |
| nuclear q,p | 고전 핵을 승인할 경우 authoritative; static pilot는 q만 입력 | S3에서 핵 wavefunction/density matrix를 택하면 동시에 정확한 개별 고전 q,p가 기본 상태는 아님 |
| total electron count N_e / total charge Q | authoritative sector/global bookkeeping, Q/e=ΣZ−N_e. reservoir/escape가 없으면 conserved | escape한 전자도 전체 세계에 포함할지 경계 밖 장부로 보낼지 정의. PP valence electron count와 실제 총수를 구분 |
| spin / electronic sector | 승인한 Hilbert subspace/state selection의 입력. branch 포함 여부 미결 | time-dependent superposition/coherence/coupling이면 전자 상태 일부. sector를 ID로 임의 전환하지 않음 |
| nuclear spin / identical-nucleus exchange statistics | clamped-nuclei spin-independent 전자 곡선에는 직접 넣지 않는 연구 범위 후보 | quantum nuclei/회전·진동/핵 spin coupling을 포함하면 nuclear state와 교환 대칭 조건이 필요. isotope의 질량만으로 대신하지 않음. 전자 singlet/triplet과 핵 ortho/para를 구별 |
| electron density n(r) | ground-state solve의 derived physical result / witness | S2 density history+initial state/closure가 필요; 현재 n(r) 하나만을 완전 state라 선언하지 않음 |
| many-electron Ψ / density operator Γ | ground-state solve의 파생 witness 후보 | S2/S3에서는 authoritative state 후보. Γ는 실제 electronic density n(r), 1-particle density matrix와 구별 |
| orbital-like coefficients / KS orbitals | solver 내부 표현. orbital rotation·phase/gauge가 비유일적 | KS orbital을 개별 전자의 실제 trajectory로 부르지 않음. physical equivalence와 serialization 규약 분리 |
| atomic partial charge / oxidation label | partition scheme에 따른 solver diagnostic/Observer label | 핵종이 Na라는 이유로 항상 +1 flag를 강제하지 않음. global conserved charge와 구별 |
| electromagnetic field | electrostatic BO에서는 law/boundary/source 입력 후보 | 동적 EM이면 field energy·momentum·gauge/constraints·source까지 authoritative 후보. classical Maxwell vs quantum radiation 선택도 미결 |
| bond/molecule/reaction ID, water/ATP/protein/neuron flag | **authoritative로 자동 채택 금지**, read-only Observer output | neighbor/basis/temporary connectivity 같은 계산 자료라도 법칙/힘을 결정하는 hidden input이면 공개·감사 필요 |
| model/Hamiltonian/parameter/weights/basis fingerprint | law/provenance, 물리 상태와 구별 | basis가 고정 finite law의 일부인지 continuum target의 evaluator인지 명시. 바꾸면 law 변경인지 refinement인지 달라짐 |
| SCF iteration/residual/initial guess/cache | execution witness/가속 변수 | convergence branch가 값에 영향을 주면 물리 선택 문제. 재생에 필요한 witness는 기록하되 물리 law를 대신하지 않음 |

정적 nuclei 배열만으로 임의 실제 전자 상태를 유일하게 정하지 못한다. N_e/spin/초기 Ψ/field/경계와 ground-state 또는 time-dependent law가 추가로 필요하다. ground-state density 정리를 현실 macro/structure 통계→유일한 실제 microstate의 근거로 오용하지 않는다. 초기 준비의 기존 E 문제는 남는다.

## 5. chemistry가 계산 결과가 되는 수준과 PHYSICAL LIMITATIONS

제한된 비상대론적 clamped-nuclei electronic 후보의 예를 atomic units로 쓰면 다음과 같다.

```text
H_e(R) = -1/2 Σ_i ∇_i² - Σ_i,A Z_A/|r_i-R_A|
         + Σ_i<j 1/|r_i-r_j|
V_NN(R) = Σ_A<B Z_A Z_B/|R_A-R_B|
E_e,0(R; sector) = inf_{Ψ in declared sector/domain, ||Ψ||=1} <Ψ|H_e(R)|Ψ>
E_BO(R; sector) = E_e,0(R; sector) + V_NN(R)
```

여기서 Ψ(x₁,…,x_Ne)의 x_i=(r_i,σ_i)는 위치와 spin 좌표다. **전체 spin-space 상태**가 electron exchange에 반대칭이어야 하며, singlet의 spatial 부분까지 반드시 반대칭이라고 요구하지 않는다. 위 inf는 선언한 sector/domain의 ground-energy 하한이며, 정규화 가능한 최저 상태가 존재하면 minimum이다. 아무 SCF stationary/metastable 해나 이 값으로 인정하지 않는다. sector 내부 최저 해와 sector 사이 전체 최저 해도 구분하고, bound state 부재/미증명은 숨기지 않는다.

V_NN은 전자 좌표와 무관한 nuclear repulsion이다. electronic energy와 total BO energy의 소유를 위처럼 분리해 **한 번만** 더한다. finite-basis Hamiltonian에 이미 scalar identity로 포함했다면 다시 더하지 않는다. 이 Ψ는 고전 electron bead의 q,p 목록이 아니다. 식에 molecule/bond/reaction ID가 없어도 kinetic/Coulomb/반대칭성과 선택한 electronic solve가 결합 energy surface를 만들 수 있다. 원자 중심 basis를 쓰는 것은 원자 위치의 함수 표현이며 분자 graph 입력과 같지 않다. 그러나 **BO·비상대론·clamped nuclei·선택 sector 자체는 근사/범위**이며 이 식을 모든 현실 물리의 완전 law로 승인하지 않는다.

* 고전 점전하 전자+핵의 bare Coulomb energy는 r→0에서 아래로 제한되지 않는다. quantum kinetic/반대칭성·상관을 물리적으로 표현해야 한다. ad hoc spring/Pauli potential/smearing을 추가하면 새 유효 모델이고 검증 범위가 필요하다.
* S1에서 핵의 움직임을 나중에 허용하면 force는 **같은** E의 gradient여야 한다. nuclear-coordinate-dependent basis의 Pulay/response·constraints·field/boundary 항이 빠진 단순 Hellmann–Feynman 값은 충분하지 않을 수 있다 [R16]. 구조 relaxation은 최소점 탐색이며 실제 시간/열/형성 경로가 아니다.
* **BO는 전자 과정을 손실 없이 빨리 계산한 것이 아니다.** 전자 시간 이력/여기/비단열/방사를 제거한 유효 law다. [RULES](../../RULES.md)의 과정 보존과 연결하려면 제외 경로의 적용 범위·누적 영향 근거와 설계자의 effective-law 허용 판단이 필요하다. Car–Parrinello 가상 orbital dynamics도 실제 electron dynamics로 바꾸어 부르지 않는다 [R3].
* 비상대론 Coulomb와 계 전체 electronic minimization은 finite-speed EM 인과를 직접 재현하지 않는다. regional independence/영향 범위와의 정합성을 선언해야 한다. global solver라는 실행 구조만으로 지역성 위반을 단정할 수는 없지만, instantaneous law의 물리적 근사를 cache/병렬화로 숨길 수는 없다.
* 핵 tunneling/zero-point·전자 continuum·photons·spin-orbit·relativistic/nuclear reaction의 제외는 일반적인 chemistry 가능성의 차단일 수 있다. 지원 선언에는 state/field/T/농도·물질량/시간별 영향 근거가 필요하며 모르면 `UNSUPPORTED / UNRESOLVED`다. 낮은 평균 에너지로 rare event가 없다고 판정하지 않는다.
* 핵 spin/동일 핵의 교환 통계는 전자 spin과 별개다. 실제 plasma chemistry에서 핵 spin modification의 선택성이 관측됐다 [R21]. 이는 반응 목록을 A에 넣으라는 뜻이 아니라 nuclear state/대칭과 상호작용을 생략할 때 별도 지원 근거가 필요하다는 뜻이다. 첫 clamped-nuclei electronic curve로 핵 ortho/para·회전 population·spin 전환 경로를 검증하지 않는다.

### 5.1 결정론적 전자 계산과 양자 측정은 다른 문제

닫힌 계의 주어진 Ψ에 대한 unitary evolution은 결정론적일 수 있다. 표준 Born 측정 확률과 “난수/확률 분포 없이 한 개의 고전 history만 남기는 A”의 정합성은 그것만으로 해결되지 않는다 [R17]. decoherence, 여러 branch 보존, deterministic interpretation/추가 변수, effective ground-state 범위 제한 등의 선택은 서로 다른 의미와 비용을 가지며 이번에 선택하지 않는다. 양자 결과의 기대값을 하나의 실제 measurement history로 바꾸거나 orbital occupation을 임의 추첨하지 않는다.

QMC의 sampling 난수는 이 물리적 측정 문제와도 다르다. 이번 요청의 **외부 reference 연구 후보**로 비교할 수 있으나 현재 A solver에 seed를 붙여 난수 금지를 해결한 것으로 처리하지 않는다. QMC error bar도 rigorous enclosure가 아니다. 기존 헌법/RULES를 수정하지 않으며 이 충돌을 설계자 결정 항목으로 남긴다.

복소 amplitude는 실수/허수 성분의 encoded 표현으로 다룰 후보가 있으나, 정확한 분수 저장만으로 quantum state의 normalization·unitarity·energy 보존과 실제 시간 evolution이 보장되지는 않는다. 일반 integral/eigenvalue/phase는 유한 rational 값으로 정확히 끝나지 않을 수 있다. 기존 rational VM의 canonical 상태·sound rounding을 새 표현에 어떻게 연결할지, finite discretization이 새 law인지 continuum 해의 enclosure인지가 추가 미결이다. 부동소수점 quantum package의 재현성을 기존 A 산술 계약 완료로 보고하지 않는다.

### 5.2 Observer의 단방향 역할

`CONFIRMED world result → read-only 구조/전자 진단 → 분류값 + 기준/불확실성`만 허용한다. “H₂”, “물”, “결합 변화”, “해리/반응”, “막/단백질/뉴런”은 이 뒤의 label이다. 가까워진 H를 보고 Observer가 H₂ 객체를 생성하거나 전하/force/topology를 바꾸지 않는다. ambiguous geometry는 분류 미결을 보존한다. bond order/거리/전자 basin 등 판정 기준이 다르면 label이 달라질 수 있고, label 선택이 세계 결과를 바꾸면 결함이다.

full-access 설계자/검사 도구의 electronic diagnostic과 연구자 B의 인간 실현 가능한 관측도 구분한다. 현실 자료/내부 Ψ를 B의 선천 관측에 자동 공개하지 않는다. [세 층 분리](../active/A_THREE_LAYER_SEPARATION_V1.md)의 TEMP/SPECULATIVE→독립 검증→VALID→확정 및 INVALID/REFUSED 보존 원칙을 새 표현에서 다시 계약해야 한다; 기존 Ar verifier가 electronic 세계를 승인하는 것은 아니다.

## 6. 계층형 Matter Model — law refinement와 model 교체를 분리

| 계층 구조 후보 | 싼 계산 사용 조건 | refine/실패의 의미 |
|---|---|---|
| H1: **같은 authoritative Hamiltonian**의 여러 evaluator | 상태/domain 판정과 sound enclosure가 같은 canonical 결과/rounding을 보장 | precision·basis/grid error enclosure·solver·reference를 정교화. 판정 불가면 REFUSED/UNRESOLVED. continuum target의 basis 축소 error도 bound 필요 |
| H2: 서로 다른 effective/electronic/reference law의 비교 | 각자 law_id·근거·state/domain/제외 경로를 기록하고 외부에서 같은 연구 입력 비교 | 차이는 model error/범위 조사 자료. 보통 energy bracket을 이루지 않음. high-level이라는 이름도 자동 참/상한·하한이 아님 |
| H3: runtime adaptive model/QM-MM/blend | selector·partition·cross energy·field/charge·state mapping·conservation·error/가능성 보존까지 승인한 새 **공동 law** | 싼 법칙→비싼 법칙을 몰래 교체하는 것이 아님. 현재 unresolved; production history에서 자동 사용 금지 |

추천은 먼저 H2의 작은 독립 reference 비교로 모델 오차를 드러내고, 선택된 target이 생긴 뒤 H1 가능성을 검토하는 순서다. “상태가 모델의 검증 범위 안”은 단순 최근접 train 거리/committee 일치/SCF 수렴/온도 임계값과 같지 않다. 학습된 불확실성은 calibrated diagnostic일 수 있으나 모든 미지 경로의 sound guard를 보장하지 않는다.

H3가 필요할 때 최소 계약은 **world law/selector fingerprint; 공통 state 또는 loss 없는 lifting; 동일 charge/energy/momentum owner; potential/gradient와 selector derivative; branch/history mapping; 경계/tail; 제외 physics/rare-path 누적 bound; switching 실패 기록; 독립 verifier**다. `U=wU1+(1-w)U2`라면 force에는 `-(U1-U2)∇w`도 생긴다. energy offset만 맞추거나 switch 순간 속도를 rescale하는 것은 일관된 law의 증명이 아니다.

S0의 nuclei+partial charge에서 S2의 phase/coherence/전자 density operator를 유일하게 복원하지 못한다면 refinement는 잃어버린 전자 이력을 되찾지 못한다. 여러 Ψ/branch를 임의 선택하거나 ground state로 snap하지 않는다. 완전한 higher-state를 계속 보존하는 방안은 정보 손실을 줄일 수 있으나 그 state를 sound하게 진화시키는 비용은 남는다. mapping 실패 시 last CONFIRMED에서 멈추고, 새로운 law의 외부 연구 분기와 원래 역사를 구분한다.

### 6.1 electronic solve의 수치 witness가 증명하지 못하는 것

작은 SCF residual은 chosen discrete equations의 stationarity 진단이다. global ground state/branch/기저·XC/PP·물리 accuracy와 force 인증을 대신하지 않는다. warm start·loop order·hardware가 다른 metastable 해를 골랐는데 최저 energy 후보로 자동 채택하면 hidden selection rule이다. degenerate eigenspace/phase/gauge를 canonical serialization 문제와 physical branch 문제로 분리한다.

**정규직교 기저·표준 내적**의 고정 finite Hermitian matrix H에서 normalized v의 Rayleigh quotient λ와 `||Hv−λv||≤r`는 **스펙트럼 중 어떤 값과 λ의 거리가 ≤r**임을 보이는 경로다. 그것이 최저 eigenvalue라고는 보이지 않는다. 비직교 AO 기저의 `Hc=λSc`에서 raw Euclidean residual을 이 r로 쓰면 안 된다. positive-definite S의 독립 conditioning bound와 변환 오차를 확인하고 `H_tilde=S^(-1/2) H S^(-1/2)`, `y=S^(1/2)c`, `||y||=1`의 Hermitian 문제/잔차를 쓰거나 동등한 S-metric 규약을 증명해야 한다. linear dependence로 S가 singular/ill-conditioned이면 별도 처리/거부 계약이 필요하다.

branch isolation/다른 eigenvalue의 enclosure·spectral gap·해 존재를 따로 확인한다. 같은 정규직교 표현에서 normalized eigenvector의 phase를 맞춘 error δ를 독립적으로 제한했다면 bounded derivative operator A의 expectation 차이는 `≤2||A||δ`로 제한하는 경로가 있다. force에는 integral/basis response/Pulay·overlap S의 R-derivative·boundary 오차도 더한다. continuum Coulomb의 unbounded operator에 이 finite-matrix 식을 자동 적용하지 않는다. 아직 실제 r/gap/δ/오차 숫자나 certificate가 없다.

독립 구현 검증은 **같은 Hamiltonian/basis/input 사양**을 공유하되 parser/integral/solver/gradient 코드를 재사용하지 않는 경로가 필요하다. 현실/model 정확성 검증은 다른 basis/method/고급 correlated reference 및 실험과 비교해야 한다. 같은 basis를 썼다는 이유만으로 독립 구현을 부정하지도, 두 code가 같은 approximate law에 동의했다고 reality accuracy를 주장하지도 않는다.

## 7. SCALING / HIDDEN COST

N은 nuclear 수, N_e는 electron 수, M은 spatial orbital/basis 크기(아래 finite-CI 예의 spin-orbital 수는 2M), G는 grid 크기, z는 relevant neighbor 수, I는 solve 반복, S는 역사 step 수, K는 비교 state/sector 수다. 정밀도 b의 연산 비용 c(b)를 별도로 둔다. 아래는 **조건부 구조식이며 hardware/runtime/GB 실측이 아니다**. 같은 N이라도 원소/전자 수/field/charge에 따라 비용이 달라진다.

| 후보/부분 | CPU/GPU work | memory·verification·확장 병목 |
|---|---|---|
| A | local pair O(Nz), direct long-range O(N²), polarization I회가 추가 | sites/Drude variables, solver stability/잔차→force. GPU 병렬화가 bit agreement를 자동 보장하지 않음 |
| B | local pair/triple/quadruple O(Nz)~O(Nz³), QEq matrix-free I·nnz 또는 dense solve O(N³) | coordination 변화·charge tail·parameter inventory·QEq failure. neighbor cap은 현실 상한이 아님 |
| C local | 고정 depth/width에서 O(Nz·network work), nonlocal electrostatics/charge solve는 추가 | graph/features/weights·gradient, training/teacher/reference 보관·OOD guard·interval activation/derivative. nonlocal 모델을 linear라고 자동 가정하지 않음 |
| D1/D2 | parameter Hamiltonian 구성+SCF dense diagonalization I·O(M³) | dense O(M²), SCC/charge/SPIN/force response·SK cross. 작은 Hamiltonian 상수는 정확성 보장 아님 |
| D3 | standard dense KS diagonalization I·O(M³) + grid/field 계산. hybrid/exchange의 dense integral path는 O(M⁴) 항도 가능 | O(M²) matrix/orbitals, 경우에 따라 O(M⁴) integral storage. iterative/DF/dense-free 선택 시 달라짐; XC/PP/basis error는 SCF 비용과 별개 |
| E1 | canonical CCSD O(M⁶), perturbative triples O(M⁷) 구조 [R18]. finite-basis determinant count D=binom(2M,N_e), spin restriction 시 축소 | CI vector O(D), 모든 H 저장 시 O(D²)·일반 dense diagonalization O(D³); matrix-free여도 D 증가. integral O(M⁴), active-space 누락/해리 multireference |
| E2 | L samples × per-sample electronic work; 통계 error를 ε로 줄이는 일반 MC 비용은 대략 ε^-2 배 | walker/state·fixed-node/systematic error·독립 표본·force noise. statistical ε와 rigorous ε 혼동 금지 |
| S2/S3 실제 quantum history | electronic time evolution/state count, 핵 grid tensor·entanglement·field modes가 추가 | 완전 joint wavefunction/Γ 차원, history/branch/measurement law. 단순 N³ 규칙으로 예측 불가 |

동일 원소 밀도·M∝N·같은 precision/반복을 가정한 **산식 예**에서는 N이 10배가 될 때 local work는 약 10배, cubic은 1,000배, M⁷는 10,000,000배다. 사용자 예시 `2→10→100→1000 atoms`는 이 곡선 차이를 드러내기 위한 비교 규모이며 production N 제안이 아니다. 2 atoms가 싸다는 결론도 heavy atom/전자 수에 무관하지 않다.

| 물리 확장 | 먼저 깨질 수 있는 전제와 추가 비용 |
|---|---|
| ground → excited / neutral → ionized | B/C teacher·D/E sector/basis 부족, continuum/grid·state/coupling 증가, branch certificate·전자/경계 장부 |
| weak → strong/local field | charge/response fit·BO 안정성·전자 escape/방사. field source energy·precision·basis diffusive tail 필요 |
| simple molecule → metal → organic → interface | element cross/valence/core/spin/strong correlation·long-range embedding·polarization/dispersion·surface boundary·training/reference 범위 |
| short → long | step마다 solve+independent replay, branch/transition 누적 error, rare pathway omission, history storage; 작은 static agreement로 장기 지원 불가 |
| isolated → interacting regions | global electronic solve/cache context 확대; partition/embedding 차이·charge/force 경계·QM/MM 누락 경로 |

숨은 비용은 constants/단위/source/license·parameter pairs와 basis/PP inventory·spin/charge sectors·training/reference data/weights·SCF/response/branch·adaptive precision·독립 parser/integrals/gradient/verifier·witness/실패/history/fingerprint·physical support guard·model switching·새 원소와 interface cross·문헌/실험 유지보수다. q/p만 저장하는 S1과 실제 Ψ/Γ를 저장하는 S2/S3는 같은 history 비용이 아니다. dense orbital coefficient는 O(MN_e), many-body vector는 O(D), full density operator는 O(D²)의 기록 비용 후보이며 lossless replay/checkpoint로 줄일 조건도 새 계약이다.

### 7.1 더 싼 구조를 고르는 경계

R19의 linear-scaling electronic methods는 locality/gap/허용 오차 등의 조건을 사용한다. 이를 어떤 금속·해리·강한 field에서도 동일하게 linear하다고 부르지 않는다. exact symmetry blocks, matrix-free diagonalization, sound long-range hierarchy, certified low-rank/integral enclosures, adaptive precision, full-input fingerprint cache, independent vector reuse를 조사할 가치가 있다. 각 방법은 energy/force만이 아니라 승인된 canonical state/step/causal history의 동일성을 유지해야 한다.

SCF warm start는 잘 검증된 동일 해로 빨리 가는 초기 guess일 수 있으나 physical branch 선택권이 아니다. BO global solve cache에는 필요한 Hamiltonian·geometry·charge/spin·field/boundary/branch context가 들어가야 한다. 온도·분자 이름·최근 neighbor만 같은 cache는 안 된다. element/geometry/basis/여기/장거리/전자/핵 과정을 삭제해 싼 결과를 얻으면 새로운 model이다. **가장 싼 구조라는 근거로 새 law를 A에 승격하지 않는다.**

## 8. IMPLEMENTER RECOMMENDATION / NEXT PILOT

추천은 “DFT 채택”이 아니라 **bond-ID 없는 작은 electronic reference 과제로 후보의 실패를 먼저 드러내는 것**이다. 첫 후보는 `H₂ clamped-nuclei electronic curve pilot`, static only. R13의 singlet BO reference가 있고 해리에서 correlation/branch 한계가 드러난다. molecule 생성 명령·반응 table 없이 핵의 Z와 위치/전자 sector를 입력한다.

| tiny 후보 | 얻을 수 있는 정보 | 못 보이는 것 / 다음 비용 |
|---|---|---|
| atomic H / H₂⁺ 보조 | 1-electron analytic/numerical 검증, units·Coulomb·normalization·basis/force | electron correlation·일반 chemistry 검증 아님. 보조 검사만 통과해 H₂ 지원 승격 불가 |
| **H₂ singlet curve — 첫 추천** | bound minimum·repulsion·해리 한계, energy와 dE/dR·density, stretched bond correlation | 실제 formation/time history·수용액·proton/ionization/막/life 증거 아님 |
| H₂ triplet/다른 sector | 가까우면 항상 같은 H₂를 만드는 hidden rule 반증, antisymmetry/spin 감사 | triplet reference/조건은 따로 확보. singlet R13 값을 triplet oracle로 쓰지 않음 |
| H/O 작은 배열 | water-like 안정 geometry가 bond template 없이 계산되는지 | H₂ 결과의 일반화 아님; 10전자/상관·basis·spin 및 독립 reference 확대 |
| Na/Cl 작은 배열 | fragment density/charge 분포·공유/이온성 해석 | larger electron/core/basis·dissociation/charge-transfer 오류. partial charge label≠실제 electron escape |
| H₂O cluster | hydrogen bonding/cooperative correlation/dispersion | nuclear quantum·cluster minima 다양성·size/field/temperature 및 reference 비용 |

**안정 곡선 ≠ 고립 두 원자의 안정 포획.** 보존적 단일 PES에서 멀리서 접근한 두 H의 에너지가 해리 threshold보다 높으면 지속 결합을 위해 에너지를 내보낼 통로가 필요하다. 제3체·표면·방사 등의 physical channel이 없이 결과를 식히거나 H₂로 snap하지 않는다. radiative association 연구도 별도의 photon transition을 다룬다 [R20]. bound 초기 H₂의 진동은 보존 시험 후보이며 formation 증거가 아니다. 첫 pilot에는 dynamics를 넣지 않는다.

### 8.1 승인 뒤 첫 실제 코드 과제의 구체적 범위

1. **선택해야 할 사양:** clamped-nuclei nonrelativistic Hamiltonian/units·finite/open 연구 boundary·N_e/spin·basis/integral definition·R grid/범위·비교 지표/오차·reference를 실행 전에 봉인한다. open finite reference 제안은 production PBC 결정이 아니다.
2. **가장 작은 실행 제안:** 작은 atom-centered basis의 general electronic Hamiltonian construction + **finite-basis full CI** evaluator를 tiny reference로 검토할 가치가 있다. 결합/분자 ID·H₂ fitted pair PES를 hard-code하지 않는다. FCI는 그 finite basis 안의 reference이며 continuum exact나 large-world backend가 아니다. 채택/구현은 아직 하지 않는다.
3. **두 종류의 대조:** 같은 Hamiltonian/basis에 대한 독립 parser/integral/eigensolve/gradient로 코드·산술 오류를 검토한다. 다른 고정밀 correlated BO curve/R13와 basis refinement로 model/discretization error를 조사한다. published curve를 world force로 lookup하여 “계산으로 결합이 나왔다”고 하지 않는다.
4. **반증 입력:** stretched/close nuclei, spin sector, ID permutation, 연속 표현에서 translation/rotation에 대한 energy 불변성과 force/density 공변성, encoded rounding 차이, basis ill-conditioning·degenerate roots, wrong electron count/Coulomb 부호/누락 repulsion·Pulay를 포함한다. density는 변환된 위치에서 비교하며 force는 벡터 회전을 비교한다. 변환/force/refusal 결과를 사전에 정의하고 실패도 보존한다.
5. **모르는 배열에 대한 검사:** bond/reaction ID가 없는 generic 입력 parser/energy 정의로 새 geometry를 계산할 수 있는지, unsupported species/field/state는 명시적으로 거부하는지 확인한다. 계산 가능을 현실 support로 바꾸지 않는다. H/O·Na/Cl·cluster는 이 과제 후 추가 reference가 확보될 때의 후보다.

**비교 지표와 오차 장부 후보:** total `E_BO(R)`, 같은 sector의 asymptotic fragment/reference를 선언한 `ΔE(R)=E_BO(R)−E_asym`, signed radial force `F_R=−dE_BO/dR`, minimum 위치/깊이, 선언한 electronic sector 사이의 energy ordering을 기록한다. published singlet curve와 triplet/다른 sector의 비교 기준을 섞지 않는다. 곡선의 bound minimum을 요구해 맞추는 것이 아니라 reference와의 일치/불일치·미해결을 기록한다. 수치 허용오차/합격 기준은 아직 지정하지 않았다.

장부는 **같은 finite law의 구현/solver·integral 오차**, **continuum target에 대한 basis/grid/discretization 오차**, **electronic approximation/제외 physics의 model discrepancy**, **published reference의 불확실성/지원 조건**, **encoding/rounding 오차**를 분리한다. 독립 코드의 차이·basis convergence·실험 deviation·MC error bar를 모두 rigorous bound로 합산하지 않는다. 같은 quantity/domain에 sound bound가 확보된 항만 보장된 총오차에 포함하고 나머지는 diagnostic/미결로 보존한다.

finite atom-centered basis에서는 atomic H 보조 계산과 stretched H₂의 fragment/asymptote가 같은 정확도를 가진다고 가정하지 않는다. fragment가 상대편 basis의 도움을 받는 **basis-set superposition error(BSSE)** 가능성을 점검하고 basis refinement/독립 reference/필요한 fragment 비교를 연구 사양으로 명시한다 [R22]. counterpoise 보정 등은 diagnostic 후보이며 world potential/force에 자동 주입하지 않는다. R13의 유한 R 구간을 무한 거리의 정확한 asymptote로 대체하지 않는다. 핵 spin·quantum nuclear spectrum·ortho/para는 이 electronic 지표의 지원 범위 밖이다.

이번에 pilot/code/test/reference 계산은 실행하지 않았다. static curve로 시작하면 dt/rounding/world transition/initializer를 정하지 않고도 lower electronic representation의 유용성과 한계를 검사할 수 있다. 실제 nuclear motion/전자 time history/production에는 별도 state·quantum/고전·전이/독립 replay 결정이 필요하다.

## 9. Drude / 뉴런 / L의 새 위치

**Atomic/Electronic 후보의 결과 ↔ Drude effective/comparison 후보 ↔ 실험**으로 비교한다. Drude에 없는 반응을 현실/A에서 없는 것으로 판정하지 않는다. source-defined nonreactive domain, 기존 source/cross/solver 미결을 보존하고 빠른 backend 자격도 자동 승인하지 않는다. 실제 electronic↔Drude runtime coupling은 §6 H3의 새 공동 law 과제다.

뉴런은 foundation의 원소/반응/기능 요구 목록을 역으로 만드는 기준이 아니다. 작은 atomic/electronic 검증→원소/상태/조건 확장→복잡한 물질 검증 뒤 막/세포/뉴런을 stress-test 후보로 둔다. ATP/water/protein/neuron 기능 규칙을 넣어 결과를 강제하지 않는다.

L은 raw matter의 구조 변화/새 상호작용을 관측할 후속 연구선이다. reaction list를 생명 가능성의 상한으로 고정하지 않는다. 그러나 electronic 이름을 붙였다고 가능한 chemistry/life를 충분히 열었다는 증거도 없다. 제외한 physical paths의 누적 영향과 [L 원칙](../reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md)을 유지한다. 이번에 생명 발생을 구현·승인하지 않았다. A ACTIVE → L 기반 이후 → B 후기/취소 아님을 유지한다.

## 10. UNRESOLVED / DESIGNER DECISION REQUIRED

| 결정 ID | 설계자가 결정해야 할 것 | 첫 static pilot와의 관계 |
|---|---|---|
| F0 | Drude 하위 위치와 lower matter 방향은 이번 사용자 지시로 확정. concrete foundation/유효 law는 어떤 것인가 | 후보 비교만 완료, 채택 없음 |
| F1 | world state S0–S3, classical/quantum nuclei, electron count/electronic spin/Ψ/Γ/field 및 nuclear spin/교환 통계의 권한 | static clamped nuclei 입력은 연구 범위로 승인 가능; world state 자동 결정 아님 |
| F2 | BO/비상대론의 과정 보존·인과 범위 정합성과 허용 domain | finite static energy 문제와 full dynamics law의 승인을 분리 |
| F3 | deterministic quantum evolution/Born structure/measurement·한 history와 난수 금지의 관계 | curve 연구가 측정 법칙 문제를 해결하지 않음. 헌법/RULES 변경 또는 해석 자동 수행 금지 |
| F4 | ground/electronic spin sectors만인지 nonadiabatic/excited/ionization/quantum nuclei/nuclear spin·ortho/para/radiation까지인지 | 제외 physics/누적 guard. 아직 현실 rate/영향 상한 미확보 |
| F5 | target Hamiltonian/XC/PP/basis/parameter/weights/units/boundary/source/license의 fingerprint | pilot가 시작하려면 해당 연구 target은 구체적으로 승인·고정해야 함 |
| F6 | solver branch/degeneracy/gauge·residual→energy/force enclosure·복소 state의 canonical 산술/normalization·독립 verifier | reference convergence와 certificate를 구분. 기존 rational VM의 새 state/전이 확장·실제 soundness proof 미구현 |
| F7 | H1/H2/H3 hierarchy와 lifting·charge/energy·transition/선택자 계약 | 먼저 독립 model comparison 추천. automatic runtime switch 미승인 |
| F8 | 현실/고급 reference·held-out geometry/field/charge/spin panel·오차/조건/공간/시간 | 실제 데이터를 확인하기 전 numerical agreement의 reality 승격 금지 |
| F9 | H₂ static pilot, H/H₂⁺·triplet 보조, basis/grid/지표/실패/허용오차 | 첫 구현 승인에 필요한 구체적 목록. pilot 실행 지시 전 구현 안 함 |
| F10 | 원소/계/시간 확대 및 history/support·비용 cap | 작은 성공으로 1000 atoms/막/뉴런/L 승격 없음; production N 미결 |

전자구조를 포함한 방향은 원 질문에 더 직접적으로 접근하지만 **최종 foundation이 무엇인지, 얼마의 계산으로 어떤 열린 chemistry를 보장하는지**는 아직 결론내리지 못했다. 모르는 경로를 수식/표로 전부 나열하는 것도 불가능하며 incomplete exclusion/coverage는 공개해야 한다. 정확재생·한 step 건전성·physical support를 혼동하지 않는다.

## 11. 조사 출처·범위·독립 검토

조사일 2026-10-02. 검색은 ground-state/TD electronic state, reactive charge/parameter, DFTB/xTB 원소/근사, 최신 ML의 charge/spin/nonlocal, H₂ 고정밀 reference, QMC/linear-scaling/측정 구분에 한정했다. 모델 시장·모든 parameter/checkpoint·reaction path의 systematic review는 아니다. 물리 근거는 원 논문/저자 methods 연구/공식 문서만 사용했다. 각 자료의 200-word 요약 범위를 넘기지 않도록 핵심 범위만 기록한다.

| ID / 출처 | 직접 읽은 범위 및 한계 |
|---|---|
| R1 [Hohenberg–Kohn, Inhomogeneous Electron Gas (1964)](https://journals.aps.org/pr/abstract/10.1103/PhysRev.136.B864) | primary abstract/정리 대상. 전체 증명 재검증 아님 |
| R2 [Kohn–Sham, Self-Consistent Equations (1965)](https://journals.aps.org/pr/abstract/10.1103/PhysRev.140.A1133) | primary abstract/ground-state equations. DOI 경유 실패 후 publisher page 확인 |
| R3 [Iftimie–Minary–Tuckerman, AIMD concepts (2005)](https://pmc.ncbi.nlm.nih.gov/articles/PMC1100773/) | primary indexed abstract/BO·CP·system-size/future sections. 전 trajectory/모든 method 식 전수 감사 아님 |
| R4 [van Duin 등, ReaxFF for Hydrocarbons (2001)](https://pubs.acs.org/doi/abs/10.1021/jp004368u) | primary abstract/parameterization 대상. 모든 후속 reactive parameter 검토 아님 |
| R5 [LAMMPS ReaxFF](https://docs.lammps.org/pair_reaxff.html), [QEq](https://docs.lammps.org/fix_qeq_reaxff.html) | 공식 description·version/sign·joint file·solver/총전하 constraints. code 실행/본 프로젝트 호환 시험 없음 |
| R6 [LAMMPS COMB/COMB3](https://docs.lammps.org/stable/pair_comb.html) | 공식 energy/variable-charge·parameter file·제한. 전체 ffield inventory 미감사 |
| R7 [DFTB parameter 소개](https://dftb.org/parameters/introduction.html), [공식 set 목록](https://www.dftb.org/parameters/download.html) | electronic/repulsive fit, SK pair·mixed-set 경고, 3ob/기타 목록. 최초 다른 URL 접근 실패 후 공식 실제 download page 확인; archive 미취득 |
| R8 [Bannwarth–Ehlert–Grimme, GFN2-xTB (2019)](https://pubs.acs.org/doi/10.1021/acs.jctc.8b01176) | primary indexed abstract/conclusions·multipole 관련 절. 전체 benchmarks/supplement 미감사 |
| R9 [MACE 공식 repository/model table](https://github.com/ACEsuit/mace) | README의 model/teacher/coverage·기능. weights 다운로드/실행/전체 code 감사 없음 |
| R10 [Open Molecules 2025 (OMol25)](https://arxiv.org/abs/2505.08762) | 저자 abstract/dataset 목적·charge/spin/reactive coverage. 실제 dataset/훈련/held-out 검증 없음 |
| R11 [MACE-POLAR-1 (2026)](https://arxiv.org/abs/2602.19411), [이번에 읽은 v1 본문](https://arxiv.org/html/2602.19411v1) | 저자 preprint methods의 spin-charge density/charge transfer 관련 결과·conclusions. independent replication/전체 paper/supplement 미검토 |
| R12 [Cohen–Mori-Sánchez–Yang, DFT limitations (2008)](https://pubmed.ncbi.nlm.nih.gov/18687952/) | primary abstract·fractional charge/spin failure 범위. 모든 functional 비교 아님 |
| R13 [Pachucki, H₂ BO potential (2010)](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.82.032509), [원고 PDF](https://arxiv.org/pdf/1007.0322) | abstract/서론/적분 관련 일부·numerical-results 앞부분. 14쪽 전체 식/Table/불확실성 전수 감사·수치 재현 없음 |
| R14 [Foulkes 등, Electronic QMC (2001)](https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.73.33) | primary abstract의 stochastic/variational/fixed-node reference. 전체 sample/보증 재검증 아님 |
| R15 [Runge–Gross, TDDFT (1984)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.52.997), [Ab initio nonadiabatic quantum MD (2018)](https://pubmed.ncbi.nlm.nih.gov/29465231/) | primary abstracts의 time-dependent/BO breakdown 범위. 모든 time-dependent approximation의 정확성 근거 아님 |
| R16 [Pulay, Forces and Equilibrium Geometries (1969)](https://doi.org/10.1080/00268976900100941) | primary abstract의 total derivative/단순 HF force 한계; force 코드/전체 derivation 미감사 |
| R17 [Schlosshauer, Decoherence and Measurement (2005)](https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.76.1267), [저자 원고](https://arxiv.org/pdf/quant-ph/0312059) | primary abstract/서지와 원고의 unitary evolution·definite outcome·Born rule 관련 부분. 41쪽 전체 읽기/어느 해석의 채택·입증 아님 |
| R18 [Friesner, Ab Initio Quantum Chemistry (2005)](https://pmc.ncbi.nlm.nih.gov/articles/PMC1100737/) | primary indexed quantum theory/CC 비용 관련 절. 현대 모든 가속의 성능 survey 아님. [Psi4 CI 공식 문서](https://psicode.org/psi4manual/master/detci.html)는 작은 CI reference 역할 확인에만 사용 |
| R19 [Bowler–Miyazaki, O(N) Electronic Structure (2012)](https://arxiv.org/abs/1108.5976) | 저자 abstract의 locality/algorithm 종류·조건. IOP 접근 robots 차단, 임의 재시도 없음; 본 프로젝트 exact-rounding/GPU 성능 보장 아님 |
| R20 [Forrey, Quadrupole Association/Dissociation of Hydrogen (2016)](https://arxiv.org/abs/1605.09651) | primary abstract의 radiative channel 사례. rate table/현실 조건 누적 상한 미확보 |
| R21 [Uy–Cordonnier–Oka, Observation of Ortho-Para H₃⁺ Selection Rules in Plasma Chemistry (1997)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.78.3844) | primary abstract의 hydrogen plasma/핵 spin 선택성 관측. 전체 실험 원자료/전환 rate/모든 핵종 지원 근거는 아님 |
| R22 [Boys–Bernardi, Calculation of Small Molecular Interactions (1970)](https://doi.org/10.1080/00268977000101561), [Psi4 공식 BSSE 문서](https://psicode.org/psi4manual/master/nbody.html) | 원 연구 indexed abstract와 공식 CP/NoCP·interaction/total·fragment basis 계산 설명. publisher 직접 접근 403, 처음 시도한 다른 문서 URL 접근 실패 뒤 실제 공식 nbody page 확인. 전체 원고/모든 fragment 정의·correction 정확성 검증 아님 |

기존 Drude의 출처/부분 읽기 기록은 Support Map §12–13을 유지한다. 이번에 source file/훈련 데이터/실험 원자료를 다시 취득하지 않았다. 직접 full text 접근이 안 된 자료는 indexed text/abstract 수준으로 제한했다. source-located와 unresolved를 구분하며, 제한된 검색에서 못 찾았다는 이유로 모델/가능성의 부재를 주장하지 않는다.

scientific-critical-thinking/scientific-brainstorming을 근거·후보·반론·비용 분리에 적용했다. 절차 출처 [Kassis, Agarwal, He, Patel, Brueckner, Scientific Agent Skills (2026)](https://doi.org/10.48550/arXiv.2609.00065)의 최신 arXiv record(v2)를 확인했다. 이 절차 논문은 물리 타당성 근거가 아니다. 사용자 요청의 독립 비교는 GPT-5.6 Sol High agent로 수행했다. 독립 후보 분석과 전체 문서 리뷰에서 ground-state 정의·핵 반발 소유·비직교 잔차·pilot 오차 장부·핵 spin/교환 통계를 보완했다. 이 리뷰는 계산 재현·물리 인증·채택 승인이 아니다. Claude Opus는 이 세션에서 호출 가능한 모델이 아니어서 두 vendor 검토를 했다고 보고하지 않는다.

## 12. 결과 상태와 작업 검증

| 결과 상태 | 이번 산출물 |
|---|---|
| **CONFIRMED FROM SOURCES** | §2의 제한된 문헌/공식 모델 구조·읽기 수준 |
| **FOUNDATION CANDIDATES** | A/B/C/D1–4/E1–2, state S0–3, hierarchy H1–3 비교. 단일 총점/전체 순위 없음 |
| **PHYSICAL LIMITATIONS** | BO/양자핵/여기/전자 escape/방사/측정/지역성·제외 누적 영향 |
| **SCALING / HIDDEN COST** | §7의 조건부 식/기록·검증·inventory·지원 guard 비용. runtime 미측정 |
| **IMPLEMENTER RECOMMENDATION** | 먼저 H₂ static electronic curve와 독립 reference로 실패를 드러내는 개발 순서 |
| **UNRESOLVED** | concrete law/state·범위/오차·branch/soundness·physics support·측정/양자-고전 계약 |
| **DESIGNER DECISION REQUIRED** | §10 F1–10. Drude 위치 변경 F0만 현재 지시로 확정 |
| **NEXT PILOT** | 승인 뒤 §8.1의 작은 component/reference/vector. 이번 실행 없음 |

Git 시작 HEAD/origin/master `71ab2b30be6e846b42994f3560f0642e305fd6a5`, master 0/0, clean; fetch 후 변동 없음. 최근 관련 commit은 `71ab2b3` first material selection, `5b90d54` support map, `994c6a0` roadmap, `322def5` preparation, `c3eb4a6` deterministic pilot다. 이 문서 한 개 추가와 기존 Support Map §13의 짧은 위치 표시만 변경한다. 헌법/RULES/CURRENT_STATE/실행 코드/동결 소스·fixture는 변경하지 않는다.

**LOCAL FULL 생략 / 관련 문서 정적 검사로 대체 / 이유:** proposal 문서만 추가·표시 변경, 기존 실행 코드/공용 계약/동결 fixture/기준선 변경 없음. pytest/forward dynamics/모델 실행/GPU/Vast·기준선 갱신·commit/push 없음. 첨부 전체와 AGENTS/RULES를 읽고 CURRENT_STATE/REPO_MAP/헌법·세 층·기존 선택 기록의 관련 범위를 확인했다. 저장소 전체 코드/`runs/` 전체 감사는 하지 않았다. 독립 문서 리뷰의 중요 지적 5개/사소 지적 2개를 반영하고 재검토에서 해소됨을 확인했다. 문서 구조(앞 열 답변·결과 상태 8개·표 11개·출처 ID 22개), 로컬 파일 링크 5개, whitespace/code fence, 변경 파일 두 개 및 기존 Support Map의 표시 외 원문 보존 검사를 통과했다. `git diff --check`도 통과했다(기존 map의 LF→CRLF 안내는 별도이며 물리 결함 해결의 증거가 아님). 끝 Git은 HEAD/origin/master 동일 `71ab2b30be6e846b42994f3560f0642e305fd6a5`, ahead/behind 0/0, 이 문서 untracked와 map 수정만 확인했다. 이는 실행 시험/수학적 증명/현실 검증을 대체한 결과가 아니다.
