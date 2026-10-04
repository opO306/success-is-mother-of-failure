# Atomic / Electronic Matter Foundation — Electronic State / History Gate V1

2026-10-04. **P1–P5 PASS / finite closed numerical counterexample / NOT CERTIFIED / foundation 미승인.**
순간 전자 밀도만으로 이 dynamic 문제의 상태를 표현하기에는 부족하다.
현재 full state는 선언한 closed 고정-H 공간에서 충분한 후보지만 **별도 history 변수 필요성은 확인되지 않았다.**
본체 fresh AO/28-root 계산과 노트북 stored-H/eigenvector 재현을 구분한다. 둘 다 외부 physics audit가 아니다.
이전 Sector Panel P1–P5 PASS/NOT CERTIFIED, H₂ PARTIAL, QZ short-R/minimum UNRESOLVED는 그대로 유지한다.

## START GIT STATE

기준 Sector worktree에서 직접 확인: status clean, HEAD `7b91cfff3642edcc5d957145052814e4cb0f3bbd`,
branch `codex/electronic-sector-panel-v1`, origin 같은 branch ref도 같은 SHA.
새 worktree `C:\Users\zun24\.codex\worktrees\electronic-state-history-v1\성공은 실패의 어머니`,
branch `codex/electronic-state-history-gate-v1`를 그 커밋에서 생성했다.
[시작 receipt](electronic_state_history_v1/git_start.json), [실행 전 seal](electronic_state_history_v1/desktop_seal.json).
이번 요청의 push 금지를 적용한다. 이전 Panel에 대한 push 지시는 이번 새 Gate에 적용하지 않는다.

## WHY SECTOR IS NOT YET A STATE

핵 Z/위치·N_e·sector·Hamiltonian/basis는 풀 문제와 허용 공간을 정한다.
그 공간 안에서 현재 어느 상태인지는 다른 정보다. Lowest root만 선택하는 solver의 동작이
세계가 항상 ground state라는 물리 law를 정당화하지 않는다.

한 geometry만 사용했다: Z1 nuclei at (0,0,±0.7) bohr, R1.4, N_e1, doublet, 원래 spherical contracted cc-pVTZ.
ghost/새 거리/새 basis는 없다. Spin-free law의 doublet 한 spin projection 대표에서 전체28공간 orbital을 유지한다.
28개 orbital amplitude를 full state라고 부르는 범위는 이 선언된 공간이다. 일반 spinor/모든 spin 변화의 충분성은 조사하지 않았다.

## MULTIPLE EIGENSTATE TEST

fresh Psi41.3.2/Libint AO의 raw S/h가 이전 Sector R1.4 N_e1의 SHA와 정확히 일치한다.
원래 TZ exponents/원래 contraction coefficient도 값별 exact equality다.
고유문제 Hc=ESc를 직접 풀어 **28개 모든 roots/vectors를 저장**했다. 정규직교는 c†Sc로 검사한다.

| 항목 | φ0 | φ1 |
|---|---:|---:|
| electronic E, hartree | -1.2836621966579087 | -0.6116001269436644 |
| E+V_NN, hartree | -0.5693764823721944 | +0.1026855873420499 |
| norm c†Sc | 1.0000000000000002 | 1.0 |
| residual sqrt(r†S⁻¹r), hartree | 1.47603e-15 | 3.79373e-15 |

gap=0.6720620697142443 hartree, φ0†Sφ1=-8.34836e-17.
최저 root의 이전 Sector total difference는 저장 binary64 값에서0.0 hartree이며 봉인된1e-9 이내다.
모든 root S-metric residual max1.63016e-13, 전체 S-orthogonality error4.56302e-14.
**P1 PASS: 같은 nuclei/Ne/sector/law에 서로 다른 두 상태가 있다.**

## ψ+ / ψ- CONSTRUCTION

실수 정규직교 φ0/φ1에서 ψ±=(φ0±iφ1)/sqrt2를 각각 직접 만들었다.
상태 norm은1 안팎의 binary64 오차 이내, |ψ+†Sψ−|=1.75379e-16이다.
정규직교 좌표의 두 pure-state projector 사이 Frobenius 거리는1.4142135623730938이다.
따라서 ψ+와 ψ−는 global phase만 다른 표현이 아니라 서로 다른 physical pure state다.
두 초기 energy expectation은 모두 -0.9476311618007874 hartree다. 이는 ground-state energy가 아니다.

## SAME-DENSITY TEST

밀도를 전체 **실수 AO** 함수 χ에 대해 n(r)=χ(r)^T Kχ(r), K=Re(c c†)로 표현했다.
executor는 Re(c)Re(c)^T+Im(c)Im(c)^T를 계산하고, 별도 checker는 Re(outer(c,conj(c)))를 사용한다.
ψ+와 ψ−의 t0 K max difference는 **0.0**이다. 이 동일한 계수 kernel은 모든 r에서 같은 밀도를 뜻한다.
밀도를 평균화하거나 하나로 복사해서 같게 만들지 않았다. 각 복소 state에서 따로 계산한 결과다.

K는 Γ=c c† 전체가 아니다. 두 상태는 반대 imaginary coherence를 가지며 Γ/projector는 다르다.
실공간 density grid의 pointwise max 차이와 absolute L1 quadrature는 **NOT_EVALUATED**다.
설치된 Psi41.3.2에는 발견하려던 BasisSet.compute_phi API가 없었다. 이는 preflight capability 기록이며 물리 solve 실패가 아니다.
이번 계약은 실행 전에 AO kernel/적분 dipole 비교로 봉인했다.

## SHORT-TIME EVOLUTION

t=[0,0.5,1.0] atomic time units(ℏ/E_h), θ=0.731 radians를 spectrum을 보기 전에 고정했다.
0,1/2,1의 짧은 정해진 시간 비교이며 gap에 맞춰 시간이나 결과 점을 조정하지 않았다.
U(t)=exp(-iH_et)로 전개한다. 상수 V_NN을 포함하면 global phase만 추가되어 physical observables는 같다.
eigenbasis에 투영한 initial amplitude **전28성분**을 위상 전개하고 AO로 되돌렸다.
처음 두 root의 중첩 준비는 상태 준비이며 나머지 eigenvector 삭제/공간 cutoff가 아니다.

별도 checker는 S^(±1/2)를 새로 계산하고 full matrix expm(-i S⁻¹/²H S⁻¹/²t)로 직접 대조한다.
executor의 준비/전개/밀도 함수를 import하지 않는다. saved AO와 SciPy를 공유하므로 외부 독립 physics audit는 아니다.
두 전개식 coeff max difference7.60719e-14≤사전1e-9,
norm error max6.66134e-16≤1e-10, energy conservation max1.11022e-15≤1e-9.
finite matrix analytic evolution을 부동소수점으로 계산했으며 엄밀 exact arithmetic 인증이 아니다.
시간 전개식의 근거는 [MIT Tokmakoff의 time-evolution operator notes](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2004/a2ea850ec85d53686c5ee8c6304278dd_2.pdf)에 대응한다.

## FUTURE OBSERVABLE DIFFERENCE

μ_e,z=-z의 AO dipole을 사용했다. 첫 왼쪽 s AO의 μ/S=+0.7로 operator 부호를 확인했다.
핵의 dipole 합은 원점 대칭이라0이다. Origin은 고정했고 단위는 e·bohr다.

| t, atomic | μ_z(ψ+) | μ_z(ψ−) | μ_z(ψ+)−μ_z(ψ−) | max difference of AO density K |
|---|---:|---:|---:|---:|
| 0 | -2.30610e-15 | -2.30610e-15 | 0.0 | 0.0 |
| 0.5 | -0.2730137516243194 | +0.2730137516243153 | -0.5460275032486346 | 0.1467028505386283 |
| 1.0 | -0.5154886410608964 | +0.5154886410608917 | -1.0309772821217882 | 0.2769957652828672 |

사전 future dipole difference floor1e-6을 두 시간 모두 초과했다.
같은 초기 밀도에서 미래의 density-weighted integral dipole이 달라지므로 미래 density도 같을 수 없다.
표의 마지막 수치는 AO 계수 kernel 차이이며 bohr⁻³의 실공간 max density로 부르지 않는다.
signed integrated electron number Tr(SD)는 모두1, error max8.88178e-16이다. 총 전자 수는 같다.
독립 analytic identity Δμ_z=2 sin[(E1−E0)t] φ0^T μ_z φ1도 사전1e-9 이내로 일치했다.
**P2 PASS = instantaneous n(r) alone NOT SUFFICIENT for this dynamic problem.**

## CURRENT STATE VS HISTORY

Path A는 직접 준비한 ψ+에서 global gauge만 canonicalize한다.
Path B는 exp(i·0.731)ψ+로 준비한 뒤 같은 gauge 규칙으로 canonicalize한다.
두 current physical projector가 같은지 검사하고, 같은 H의 미래 projector도 비교했다.
future A/B projector max error2.77561e-16≤1e-10이다. history argument는 evaluator에 없다.
이는 서로 다른 representation preparation이며 실제 핵/전자 과거 궤적 두 개를 만든 것은 아니다.

닫힌 계의 time-independent Schrödinger law에서는 현재 full state와 H가 이후 전개를 정한다.
이 pilot의 **P3 PASS / current full state sufficient candidate / separate history necessity NOT ESTABLISHED**다.
현재 complete state가 같지만 과거 때문에 미래가 달라지는 반례를 발견한 것은 아니다.
history를 authoritative state로 추가하지 않았다. audit/observer 기록과 physical state를 구분한다.
이 조건부 해석은 [MIT의 현재 상태에 대한 propagator 표현](https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2004/08900d53193e71d69d931b59883a114d_1.pdf)에 따른다.

## GLOBAL PHASE / PHYSICAL EQUIVALENCE

ψ+와 exp(i·0.731)ψ+는 raw coefficients가 다르지만 같은 pure state다.
S-metric |overlap|²와 정규직교 projector로 판정하며 bitstring equality를 물리 기준으로 사용하지 않는다.
세 시간의 global-phase projector max error2.91434e-16≤1e-10,
density/energy/dipole은 허용오차 안에서 같다. **P4 PASS.**
ψ+와 ψ−의 다른 relative phase는 없애지 않았다. canonicalization은 각 입력의 전체 global phase만 제거한다.

## STATE REPRESENTATION CANDIDATES

| 후보 | 이번 결과 | 남은 문제 |
|---|---|---|
| full Ψ, global phase quotient | 선언된28 orbital closed 공간에서 필요한 coherence 보존·충분한 후보 | 일반 전자 수/스핀/state-space 확장 비용 |
| full density operator Γ=|Ψ><Ψ| | phase 자동 제거·같은 unitary 정보 표현 가능 | dense D² 저장; mixed state는 이번에 실행하지 않음 |
| instantaneous electron density n(r) | 두 다른 상태를 같은 값으로 보내므로 dynamic authority 단독 불충분 | ground-static density 정리나 density functional 모든 종류를 부정하지 않음 |
| reduced density matrix/current 포함 표현 | 후보만 기록 | 충분성·closure·correlation 비용 미검사 |

이번 one-electron 계의 full one-particle density operator는 spatial Γ이며 diagonal density n(r)와 다르다.
many-electron의 one-body reduced density matrix가 full many-body Γ를 대체할 수 있다는 결론은 없다.
production representation 선택·정보 삭제·유효 모델 채택 없음.

## SCALING COST

pilot M28/N1/고정 doublet projection D28, 복소 wavefunction coefficient28개=448 bytes(complex128),
dense Γ784 entries=12,544 bytes다. 저장한 real AO K full array는6,272 bytes로 더 작은 Ψ보다도 크다.
이번 전체 phase/path initial arrays2,240 bytes, wave trace6,720 bytes, density kernels94,080 bytes.
본체 fresh AO/eigenstates/evolution/checker 구간 wall0.133164초. Python/WSL startup은 이 숫자에 포함하지 않는다.

확장 예는 **고정 N_alpha/N_beta, M_s sector**의 D=C(M,N_alpha)C(M,N_beta)다.
순수 total-spin S에 적응된 singlet/triplet 차원과 혼동하지 않는다. M28,N2,alpha1/beta1의784는 singlet406+triplet378이다.

| M spatial / N / (Nα,Nβ) | D, complex Ψ coefficients | Ψ bytes | dense full Γ bytes |
|---|---:|---:|---:|
| 28 / 1 / (1,0) | 28 | 448 | 12,544 |
| 28 / 2 / (1,1) | 784 | 12,544 | 9,834,496 |
| 28 / 4 / (2,2) | 142,884 | 2,286,144 | 326,653,399,296 |
| 56 / 8 / (4,4) | 134,901,944,100 | 2,158,431,105,600 | 291,176,552,351,352,396,960,000 |
| 100 / 10 / (5,5) | 5,668,210,667,750,400 | 90,691,370,684,006,400 | 514,057,794,783,990,967,337,547,202,560,000 |

[정확한 조합 계수 장부](electronic_state_history_v1/scaling_v1.json).
이는 symbolic storage count이며 해당 many-electron 문제를 실행하거나 비용을 benchmark한 것이 아니다.
순수 Γ의 factorization/representation 후보는 남아 있다. 비싸다는 이유만으로 필요한 coherence를 삭제하지 않는다.

## DUAL-MACHINE REPRODUCIBILITY

본체 Ubuntu24.04 WSL: Python3.12.3, Psi41.3.2/Libint1.2.1, NumPy1.26.4, SciPy1.11.4.
노트북 DESKTOP-0EASI0F: Python3.12.7, NumPy2.5.3, SciPy1.18.1, 기존 Panel 별도 venv를 사용했다.
CPU worker1, 저장된 S/H/dipole/28개 eigenvectors에서 준비·밀도·세 시간 전개·별도 expm checker를 다시 실행했다.
Source SHA/input manifest 검증 후 exit0/P1–P4 PASS.
desktop dipole difference max8.88178e-16, AO density comparison metric difference max1.52101e-14≤1e-9.
입력 ZIP24,683 bytes, SHA256 `436f333c72a1f5797e4ea9464e080b1f36a8fa3914b70dfb17b3bc2bda6e6919` 양측 일치.
LAN 임시 server는 종료했다. [실제 노트북 receipt](electronic_state_history_v1/laptop_results_v1.json).
**SAVED-HAMILTONIAN/EIGENVECTORS ENVIRONMENT REPRODUCTION PASS / NOT independent physics audit.**
노트북 fresh AO·continuum 검증·A-world bitwise 실행기 동등성은 주장하지 않는다.

## TEST / MUTATION RESULTS

Windows 관련150 passed,2.17초 / 별도WSL159 passed,13.94초 / 신규39.
failures/errors/actual skips0. 기존 Sector/H₂/QZ/body freeze 관련 시험도 포함했다.
요청된 변이10종을 합성 비직교 algebra 사례와 **실제28orbital 결과** 양쪽에 적용해 전부 FAIL로 검출했다:
φ0=φ1, 직교성 파괴, ±i 동일 부호, 정규화 제거, 잘못된 E0/E1,
time-phase sign 반전, density imaginary 성분 누락, global phase를 다른 state로 분류, Ne mismatch, sector mismatch.
chemist labels/history/독립charge 입력, full-space 축소, nonfinite 데이터도 거부했다.

첫 synthetic 시험은1 failed/25 passed: NumPy bool 반환을 checker의 Python True로 판정하지 못했다.
실행 전 Python bool 변환으로 수정한 뒤26 passed; 처음 log/XML과 수정 사유를 보존했다.
최종 물리 실행 후 source/time/tolerance 변경은 없다.
**LOCAL FULL 생략 / 관련 시험으로 대체 / 새 격리 연구·시험·문서만 변경, 공용 runtime/frozen contract 불변. 공식 기준선 미갱신.**
구상 일치성은 시험 밖 [author review](electronic_state_history_v1/author_review_v1.json)로 별도 검토했다. 외부 audit 승인은 아니다.

## WHAT THIS PROVES

P1: 같은 sector tuple에서 두 다른 정규화 eigenstate가 존재한다.
P2: 두 상태의 같은 현재 n(r)는 다른 미래 density observable을 가질 수 있다.
P3: 선언된 closed fixed-H 공간의 current full state는 이후 evolution을 정하는 충분한 후보다. 별도 history 필요성은 미확인이다.
P4: global phase는 physical-state 차이가 아니다.
P5: strict 핵/Ne/sector/law/basis와 복소 initial state로 계산하며 bond/molecule/reaction/H2+ label은 selector가 아니다.
**P1–P5 PASS**는 이 finite numerical pilot의 조건부 결과다.

## WHAT THIS DOES NOT PROVE

TDDFT production/nonadiabatic/surface hopping/실제 전자-핵 dynamics/photon/collapse/open-system/decoherence 미구현.
open/reduced system의 memory 필요성, 실제 nuclear motion에 ground-state re-solve가 충분한지, many-electron representation 충분성 미검사.
history가 모든 상황에서 불필요하다는 증명도 아니다. 현재 state를 불완전하게 저장하면 누락된 정보가 memory처럼 나타날 수 있다.
비상대론 고정 핵·spin-free model 오차, contracted TZ basis 오차, binary64 AO/고유해/complex128 위상 반올림은 남아 있다.
별도 checker는 같은 saved AO와 numerical library를 공유한다. AO accuracy/continuum/엄밀 spectrum·unitarity 인증 및 외부 감사는 아니다.
새 density counterexample가 기존 QZ short-R를 해결하거나 실제 화학/생명/세계 formation을 증명하지 않는다.
AGENTS/RULES 전체, CURRENT_STATE/REPO_MAP 활성 Gate·전자 연구 범위 부분, Sector 보고서 관련 범위와 evaluator를 직접 읽었다.
기존 메모는 state/증거/오차 구분 원칙에만 사용했고, 이번 수치와 Git는 새 실행·조회다.

## FOUNDATION MINIMALITY UPDATE

보수적 후보: **핵 Z/상태 + N_e + 실제 electronic quantum state + Hamiltonian/law**.
Q는 derived, bond/molecule/reaction은 Observer label이다.
spin sector는 full state/law에서의 성질 또는 state-space restriction 후보이며 이번 Gate에서 저장 형식을 제거·확정하지 않는다.
instantaneous n(r) alone는 이 dynamic authority로 불충분, 전체 과거 history의 authority 필요성은 미확인이다.
global phase 제외한 current state와 필요한 자유도를 보존하는 표현 문제를 다음 단계로 남긴다. Foundation 최종 승인 없음.

## NEXT DESIGNER DECISION

**Electronic Representation Gate부터 검토하는 쪽이 현재 자료로 시작하기 쉬운 후보**다.
고정 H와 저장 state에서 Ψ/Γ/reduced-current 표현의 정보 보존을 비교할 수 있기 때문이다.
Electron–Nuclear Dynamics Gate는 움직이는 핵·backreaction/force·보존·전이 계약이 추가로 필요하다.
이는 준비 범위에 따른 비용 추론이며 두 Gate의 실측 비용 비교는 없다.
어느 쪽을 먼저 할지는 설계자가 정한다. **둘 다 자동 착수하지 않았다.**

## GIT END STATE

새 branch의 local commit으로 보존한다. **PUSH NOT PERFORMED**, master merge도 없다.
실제 최종 commit/clean status/origin 불변 receipt는 commit 뒤 `runs/electronic_state_history_v1_20261004/git_end_v1.json`에 별도 기록한다.
기존 보호tracked217개와 Sector acquisition/test raw95개의 전후 SHA 유지.
Raw source snapshots/S/H/dipole/전체 eigenvectors/복소 전개를 별도 `runs/electronic_state_history_v1_20261004/`에 보존한다.
작은 [full experiment NPZ](electronic_state_history_v1/desktop_experiment.npz)와 [eigenstates](electronic_state_history_v1/eigenstates.npz)는 Git에도 포함한다.
[Raw manifest](electronic_state_history_v1/raw_manifest_v1.json)는 닫힌32개 파일을 봉인하며 이후 commit/package receipts와 구분한다.
새 변경 파일과 이32개 raw의 복구 ZIP·별도 파일별 SHA manifest를 만들고 빈 디렉터리로 풀어 바이트 일치를 검사한다.
이는 파일 복구 검사이며 외부 audit나 전체 repository 재구축이 아니다. 최종 receipt는 봉인된 ZIP 밖에 보존한다.

방법 검토에 scientific-critical-thinking skill을 적용했다. 참고:
Kassis,T.; Agarwal,V.; He,Y.; Patel,D.; Brueckner,A.M.(2026),
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), 최신2026-09-02개정 확인.
AO API는 [Psi4 1.3.2 MintsHelper 문서](https://psicode.org/psi4manual/1.3.2/api/psi4.core.mintshelper)와 현재 설치의 docstring을 확인했다.
이 자료들은 방법/법칙/API 근거이며 fresh physical reference 비교나 외부 승인으로 세지 않는다.

## 쉽게 답하면

1. **같은 핵/Ne/sector에 여러 상태가 있나?** 있다. 서로 다른 energy의 φ0/φ1을 계산했다.
2. **sector만으로 현재 전자를 정하나?** 아니다. 허용 공간을 정할 뿐이다.
3. **같은 density의 다른 상태를 만들었나?** ψ±를 만들었고 initial density K는 같고 physical projector는 달랐다.
4. **미래가 다른가?** 두 미래 dipole이 반대 방향으로 달라졌다.
5. **density만 저장해도 되나?** 이번 dynamic 문제에서는 부족하다.
6. **full current state에 history도 필요한가?** 이 closed law에서는 full current state가 충분한 후보, 별도 history 필요성은 확인되지 않았다.
7. **global phase는 다른 상태인가?** 아니다. 표현만 다르다.
8. **현재 최소 후보는?** 핵 상태·Ne·실제 electronic quantum state·law, Q는 derived다.
9. **어디서 규모가 폭발하나?** many-electron Ψ의 조합 차원D, dense full Γ의D²에서 커진다.
10. **어느 다음 Gate가 더 싼가?** Representation부터 현재자료로 시작하기 쉽다는 추론이다. 실제 비용비교·자동착수는 없다.
