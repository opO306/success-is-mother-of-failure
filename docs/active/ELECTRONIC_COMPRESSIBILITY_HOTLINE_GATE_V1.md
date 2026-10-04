# Electronic Representation Next Gate V1

Tensor Compressibility Diagnostic + Guaranteed Baseline / Hotline Prototype, 2026-10-04.
**SURVEY ONLY / NOT PRODUCTION / NOT CERTIFIED / NO PUSH.**

먼저 한계: 두 전자에서 작은 χ로 기존 오차 기준과 저장 이득을 함께 얻지 못했다.
Hotline은 영향을 보존했지만 이 구현의 감시·bound 계산은 full 계산보다 비싸다.
큰 TN, tensor-native evolution, production A 연결 및 두 축의 통합은 구현하지 않았다.
아래 수치는 봉인된 finite cc-pVTZ R=1.4 corpus와 작은 제어 시험의 결과다.

## TENSOR COMPRESSIBILITY

Dense Ψ를 REF로 두고 기존 `A_corpus.npz`(D28, 전자1), `B_corpus.npz`(D406, 전자2 singlet)를 그대로 사용했다.
ground / first excited / ψ+ / ψ− / global-phase 동치 상태 5개, t=0,0.5,1 au,
각 checkpoint 이후 추가 Δt=0.5 au를 시험했다. 새 AO 적분·물리 법칙·basis는 없다.
원본 SHA와 source seal은 [execution_seal.json](electronic_compressibility_hotline_v1/execution_seal.json)에 있다.

판정 기준은 실행 전 고정했다: state S-norm 오차 ≤1e-10, energy/density/dipole 및
미래 오차 ≤1e-9를 만족하고 χ≤8, 각 partition의 state factor payload+최소32B metadata가
dense보다 작아야 작은 χ 성공으로 센다. shared gauge 비용은 별도이며 이것을 제외한
성공을 전체 저장 이득으로 승격하지 않는다. 결과 뒤 tolerance나 χ를 바꾸지 않았다.

| corpus / state | original MO χ | energy MO χ | z-position basis χ |
|---|---:|---:|---:|
| 전자1 ground | 1 | 1 | 2 |
| 전자1 excited | 1 | 1 | 2 |
| 전자1 ψ+ / ψ− / global phase | 1 | 1 | 2 |
| 전자2 ground | 24 | 24 | 32 |
| 전자2 excited | 24 | 24 | 24 |
| 전자2 ψ+ / ψ− / global phase | 24 | 24 | 32 |

이는 세 cuts를 모두 통과하는 **시험한 χ 후보 중 최소값**이다. 정확한 최소 정수 χ를
찾은 것이 아니다. χ32는 이 문제의 모든 Schmidt 채널을 담는 상한 후보다.

ground뿐 아니라 excited·superposition·evolved 상태도 검사했다. 위 요구 χ는
봉인한 세 시간 모두 같았다. A는 state/gauge/time 45조합 중30개의 state-payload 조건부
성공으로 **CONDITIONAL**, B는0개로 **POOR**다. A의 rank2 상한은 전자1이라는
작은 입자 수의 구조를 반영하며 many-electron 압축 성공의 증거가 아니다.

## ENTANGLEMENT / χ SCALING

직교 orbital은 기존 B.c로 잡았다. A는 `v_MO=Cᵀ S v_AO`, B는 symmetric singlet
계수 행렬 W로 옮긴다: W_ii=v_ii, W_ij=W_ji=v_ij/√2. `CᵀSC−I` max는
4.5630166312093934e-14다. gauge R에서 A는 Rᵀv_MO, B는 RᵀWR를 사용한다.

사전 정의 세 gauges와 cuts7,14,21만 시험했다. energy 순서는 `diag(CᵀhC)` stable sort다.
실제 기존 순서와는 일부 거의 축퇴 orbital의 순서가 달랐으며 전체 permutation을
[gauge_metadata.json](electronic_compressibility_hotline_v1/gauge_metadata.json)에 보존했다.
z-position gauge는 `−Cᵀμ_zC`의 고유기저다. 이는 z 방향의 위치 대각화이지,
Boys localization이나 완전한 3D 공간 지역화가 아니다. 축퇴 공간 안의 LAPACK 기저 선택은
유일한 물리적 선택이 아니며 gauge artifact 자체를 봉인했다. 결과를 보고 ordering을 탐색하지 않았다.

분할은 interleaved spin creation order `(0α,0β,1α,1β,…)`를 고정한 orbital Fock
occupation amplitude의 좌/우 분할이다. **406개 raw index를 reshape한 SVD가 아니다.**
일전자에서는 좌측/우측 한 입자 sector 각각 rank1이므로 최대rank2다.
singlet에서는 N_left=2,0 sector의 singular 값이 각각 `||W_LL||F`, `||W_RR||F`이고,
N_left=1의 두 spin 채널은 `W_LR`와 `−W_LRᵀ`로 같은 singular spectrum을 갖는다.
cross singular 값은 두 번 기록한다. 고정 creation order의 수학적 mode-partition 지표이며,
구별 가능한 두 전자의 particle entanglement나 superselection 아래의 operational resource와 동일시하지 않는다.
이 구분은 [Friis et al., Phys. Rev. A 87, 022338](https://doi.org/10.1103/PhysRevA.87.022338)의
fermionic subsystem 주의점과 맞춘다.

singlet 절단은 cross spin 쌍을 같이 보존한다. LR sector 선택2²개와 가능한 cross rank를
비교하여 χ budget 안에서 보존 weight를 최대화했다. 그래서 일반 unconstrained SVD의
top-χ 절단과 다를 수 있다. 둘의 discarded weight를 모두 기록했다. 절단 뒤 renormalize하여
오차를 숨기지 않았다. norm, fidelity, normalized projector distance를 별도로 기록했다.

| 항목 | A | B |
|---|---:|---:|
| 상대 cutoff1e-12에서 최대 측정rank | 2 | 30 |
| entropy 범위(bits) | 7.046e-29–1 | 0.001527–2.357282 |
| B χ8의 state 오차 | — | 0.003741–0.029240 |
| B χ8의 energy 오차(Hartree) | — | 0.0001254–0.0051733 |
| B χ8의 AO density kernel max 오차 | — | 0.0002450–0.0381315 |
| B χ8의 dipole max 오차 | — | 2.33e-18–0.00084393 |

작은 entropy라도 약한 tail을 기존 엄격한 기준까지 보존하려면 χ가 클 수 있다.
rank30도 전자2·28orbital·middle cut의 입자 수 제한 `2+2 min(14,14)` 안의 결과다.
기저 크기·전자 수에 따른 asymptotic χ scaling을 측정한 것이 아니다.
모든27개의 MPS bond를 측정하거나 하나의 일관된 MPS를 만들지도 않았다.

1,890개 기록에 singular 값, rank, entropy, χ, discarded norm/weight, reconstruction,
energy/density/dipole/fidelity/projector 및 미래 실제 오차가 있다.
analytic quadratic bound `||O|| eps(2||ψ||+eps)`와 고정 unitary의 미래 norm bound eps도
기록했다. 이 bound의 binary64 수치 평가는 outward interval certificate가 아니다.
[tensor_rows.json](electronic_compressibility_hotline_v1/tensor_rows.json),
[reconstructions](electronic_compressibility_hotline_v1/tensor_reconstructions.npz).

ψ±는 같은 초기 real density로부터 미래 차이를 보이는 기존 반례다. 각 χ의
[phase distinction ledger](electronic_compressibility_hotline_v1/tensor_phase_distinction.json)를 보존했다.
χ32의 모든 gauges/cuts에서 미래 dipole 차이가0.1보다 컸다. χ를 작게 했을 때의
차이 손상은 state/observable 오차로 함께 판정하며, “작은 singular 값은 안전”이라고 가정하지 않는다.

## TENSOR COST / BENEFIT

| χ | A factor payload(B) | B factor payload(B) |
|---:|---:|---:|
| 1 | 120–344 | 456–3,704 |
| 2 | 464 | 456–4,160 |
| 4 | 464 | 3,832–4,616 |
| 8 | 464 | 4,744–5,528 |
| 16 | 464 | 6,568–7,352 |
| 24 | 464 | 7,352–8,392 |
| 32 | 464 | 7,352–9,760 |

Dense complex128 payload A448B/B6496B. payload는 실제 factor의 dtype/shape에 필요한
수치 배열 bytes 계수다. 완성된 standalone serializer의 총 파일 크기 측정은 아니다.
각 record의 최소 metadata32B와 shared C/R12,544B도 별도 필요하다. R=I 같은 경우의
metadata 최적화·여러 상태 간 gauge amortization은 구현하지 않았다.
B에서 inherited tolerance를 통과한 factor payload 범위도7,352–9,760B로 dense보다 크다.
한 partition의 축약 factor가 모든 bonds를 갖춘 TN보다 싸다는 주장도 하지 않는다.

| capture CPU median | A | B |
|---|---:|---:|
| decompose, 한 state/gauge/cut | 11.89μs | 120.11μs |
| truncate + 원좌표 복원 | 30.46μs | 149.31μs |
| 현재 상태의 metric 비교 | 63.90μs | 3.369ms |
| 복원 후 dense 고정-H evolution | 24.44μs | 34.088ms |

static metric 시간은 REF와 reconstruction의 비교 비용이며 future metric은 이 항목에
포함하지 않았다. capture의 evolve는 기존 all-root 식을 직접 실행해 일부 dense 행렬
곱을 매번 다시 만든다. 아래 live 비용에서는 공통 propagator를 한 번 만들고 사용했다.
위 표를 최적화된 dense executor와 tensor-native executor의 비교로 읽으면 안 된다.
정확한 소스·환경·각 개별 측정은 execution seal/results에 있다.

## GUARANTEED BASELINE

Axis B는 tensor 결과와 독립적으로 실행했다. A는 coefficient block size8(4블록),
B는64(7블록)다. **공간 물리 영역이 아닌 synthetic coefficient hierarchy**이며 실제
공간 인과 범위를 발견했다는 의미가 없다.

FULL / COARSE_CERTIFIED / COLD_EXACT_STORAGE만 있다. cold 원본은 complex128
메모리 checkpoint에 보존한다. coarse center는 complex64이고, 각 real/imag 차이를
Fraction으로 합한 정확한 coordinate L1 반경을 제공한다. “COLD=0” 경로는 없다.

모든 ordered block pair i,j를 norm·energy·세 dipole에 account했다. 따라서 diagonal
자기 기여뿐 아니라 off-diagonal coupling도 빠지지 않는다. 중심 pair 계산에 대해
`B_ij(L_i δ_j+L_j δ_i+δ_iδ_j)`와 floating evaluation 여유를 기록한다.
COARSE_CERTIFIED의 직접 정확 보증 범위는 **저장된 coefficient의 Fraction enclosure**다.
quadratic 계산은 명시된 부동소수점 error model에 의존하며 엄밀 interval library 인증은 없다.
coarse density entry 전체의 별도 certificate는 만들지 않았고, density는 canonical 복원 후 계산한다.

현재 계약은 최종 coefficient를 정확하게 요구한다. 모든 non-FULL 블록을 원본에서
복원한 뒤 output을 확정한다. 반경0인 non-FULL 블록도 복원하는 보수적 prototype이다.
기존 corpus15 checkpoint ×3paths ×3orders ×2corpora =90 실행에서 canonical bytes가 REF와 같았다.
[baseline receipts](electronic_compressibility_hotline_v1/baseline_receipts.json.gz).

처음 capture는 주어진 exact checkpoints를 account하는 시험이었다. 별도 source seal의
live corridor에서는 각 path가 실제 복원한 출력으로 다음0.5au step을 진행했다.
동일 full dense propagator 비용을 모든 path에 부과했으며, 별도 full-matrix expm와
energy/density/dipole/state를 비교했다. 6 path/corpus 조합마다45 physical rounds를
검사했다. 이 live cost probe의 classification 상태는 round마다 COLD에서 시작한다.
stateful hysteresis는 primary의 3-checkpoint trace와 별도 control sequence에서 시험했다.
electron evolution을 일부 blocks만 cheap하게 수행하는 알고리즘은 없다.

## HOTLINE TRIGGER

전자 prototype 진입 L1 radius >6e-9, 복귀 <2e-9, safety >8e-9이면 즉시 FULL이다.
상태 transition 입력은 bound뿐이고 bond/reaction/life 같은 의미 이름은 없다.
trigger는 더 정확한 coefficient/contribution을 사용하게 한다. 다른 블록의 baseline
갱신 권한이나 coverage를 줄이지 않는다. 정확한 canonical output 요청은 별도 REFINE 이유다.

“threshold가 적당했다”는 물리적 calibration은 하지 않았다. 봉인한 prototype 숫자의
규칙 준수 여부를 검사했다. entanglement/condition-number trigger와 timestep 변경은 미구현이다.

## STARVATION TEST

**K=1 round**를 실행 전 봉인했다. 매 round 모든 블록을 갱신한다. A는 path당
3 checkpoint에12 update, B는21 update로 전 실행에서 누락0이다. HOT 여부와 무관하다.
HOT 뒤 다른 update를 없애는 mutant와 이후 stable block을 영구 누락하는 mutant를
별도 검사했다. 둘 다 checker가 거부했다. finite trace 계약 검증이며 OS 또는 무한
scheduler의 liveness 증명은 아니다.

## THRASHING TEST

별도 NON_CANONICAL control thresholds: entry0.006, return0.002, safety0.008.
봉인한 radius `.0055,.0065,.0055,.0065,.0055,.0065,.001`에서 naive entry threshold만
사용하면6회 상태 전환이지만 hysteresis는2회(COARSE→FULL→COARSE)다.
정상 값0.0055의 복귀를 억제하면서 unsafe 값0.009는 FULL로 보낸다.
추가 branch probe에서는 entry0.02보다 낮아도 safety0.008 초과를 FULL로 보냈다.
이 probe의 threshold는 primary source seal에 들어 있으며 전자 결과 뒤 tuning이 아니다.

전자 primary의 ascending order, 5state 합계 HOT transitions는 A14/B5,
canonical REFINE copies는 A21/B90다. 모든 세 orders의 기록을 보존했다.
HOT 전환 자체의 복잡한 allocator/I/O 변환은 없다. complex64 생성과 Fraction 반경 획득
비용이 conversion 항목이다. production 전환 비용·장기 thrashing은 미평가다.

## SCHEDULER ORDER INDEPENDENCE

ascending / descending / even-then-odd를 미리 고정했다. 마지막 것은 RNG 없는 고정 permutation이다.
모든 primary final coefficients는 동일bytes다. live 경로에서도 각 state의 세 orders가
같은bytes였고, 각 physical round의 output은 같은 dense propagator REF와 같았다.
canonical 이후 계산한 norm/energy/density/dipole/future도 같다. 비교를 위해 REF의
round0→1→2와 각 후보의 실제 round0→1→2를 별도로 실행했다.
다른 플랫폼 전체의 byte equality나 일반 scheduler의 물리 불변성을 인증한 것이 아니다.

## HIDDEN-EVENT TEST

블록0 radius `0,.001,.004,.009,.012,.008,.004,.001`:
처음3round는 coarse, round3에서 SAFETY_OVERRIDE로 FULL, 마지막에 coarse로 복귀했다.
block1은 radius0으로 항상 stable/coarse였고, block2는 nonzero center3/radius0.0005를
항상 제공했다. cold block의 기여도 actual result에 남았다.
이는 **사전에 넣은 deterministic adversarial 제어 sequence**다. 전자 상태에서 새로운
사건이 자연 발생했거나 bond를 발견했다는 결과가 아니다.

## MONITORING COST

Linux 새 child process, BLAS1thread, five repeats, 각 repeat에5state ×3orders ×3round.
아래 engine CPU는 evolution+observable+candidate accounting의 합으로, 독립 검증 CPU와
공통 propagator setup을 제외한다. 검증을 포함한 전체 CPU samples도 따로 보존했다.

| corpus/path | engine CPU median(s) | observed RSS max(bytes) |
|---|---:|---:|
| A REF | 0.001384 | 49,020,928 |
| A Baseline | 0.328411 | 49,299,456 |
| A Hotline | 0.317094 | 49,205,248 |
| B REF | 0.101213 | 85,102,592 |
| B Baseline | 1.748878 | 84,828,160 |
| B Hotline | 1.934233 | 83,922,944 |

Hotline은 이 실험에서 REF engine 대비 A 약229배 / B 약19.11배 비용이다.
B baseline도 약17.28배다. 이는 작은 Python/Fraction prototype의 비용이며 최적 구현의
하한 또는 A 전체 성능 예측이 아니다. 속도·RAM 개선 주장은 하지 않는다.
RSS는 smaps_rollup 경계+2ms 관측 최대이며 interpreter·검증기를 포함한다.
작은 fresh-process 차이를 memory 개선이라고 읽지 않는다. exact checkpoint를 계속
보유하여 dense state의 메모리 요구도 없어지지 않았다.

| Hotline 비용, 같은45round 배치 | A | B |
|---|---:|---:|
| threshold monitor 자기 CPU | 0.001340s | 0.002174s |
| full-coordinate 반경 획득 포함 monitor | 0.015791s | 0.187540s |
| 위 값 / 후보 engine | 4.98% | 9.70% |
| 위 값 / REF engine | 약11.4배 | 약1.85배 |
| conversion CPU(반경 획득 포함) | 0.014553s | 0.185463s |
| exact restore copy CPU | 0.001582s | 0.001144s |
| 전체 pair enclosure CPU | 0.289287s | 1.619198s |

monitor 자기 CPU만 보면 작지만 **모든 exact coefficient를 읽는 반경 획득**은
REF 계산보다 비싸다. conversion은 baseline 비용의 부분집합이므로 합산할 때 중복하지 않는다.
candidate enclosure까지 포함하면 더 큰 병목이다. primary receipts에는 block당
threshold check CPU와 full component read count도 있다(A84/B1218, 3checkpoint 기준).
현재 구조의 cheap-monitor 목적은 충족하지 못했다.
[live_cost_results.json](electronic_compressibility_hotline_v1/live_cost_results.json).

## FAULT / MUTATION RESULTS

| 요청한 mutant | 판정 |
|---|---|
| COLD contribution=0 | CAUGHT |
| HOT 뒤 다른 update 중지 | CAUGHT |
| stale bound | CAUGHT |
| coupling 누락 | CAUGHT; 실제 전자 pair omission도 별도 CAUGHT |
| 잘못된 HOT threshold 적용 | CAUGHT |
| hysteresis로 unsafe COLD 유지 | CAUGHT |
| order에 따른 physical result 변경 | CAUGHT |
| permanent baseline starvation | CAUGHT |

기본8개는 제어 receipt의 행위를 변조한 checker challenge다. 여기에 실제 전자 block pair
누락 challenge1개와 작은 coupled Hamiltonian의 source/epoch/center/radius/output 변조 시험을 더했다.
그 결과를 모든 가능한 내부 실행 결함의 탐지 보장으로 승격하지 않는다.
checker는 producer module을 import하지 않는다. Fock occupation을 별도 열거한90개
Schmidt spectrum 검사가 통과했다. 모든1,890개의 별도 density/observable 비교 및
full-matrix expm future 비교에서 최대 차이는 A5.444e-12/B2.642e-12다.
같은 저장 행렬과 NumPy/SciPy를 공유한 **작성자의 독립 코드 검사**이며 외부 감사가 아니다.

구상 검토에서 primary 제어 checker가 receipt의 threshold metadata를 신뢰하는 좁은
공백도 확인했다. 원본을 수정하지 않고 별도 `policy_check.py`/seal을 추가하여 정상
threshold를 protocol에 결합했다. 의도적으로 다른 safety probe는 별도 봉인한 expected
policy를 명시해야 한다. 정상 policy로 둔갑시킨 threshold 변이가 추가로 거부됐다.
기존9개 capture fault 결과와 추가 policy 검사를 합쳐 하나의 최초 capture라고 부르지 않는다.

Windows CPU 시계의 0초 sample로 첫 신규 시험12failed/26passed가 생겼다.
0초 ratio를 UNAVAILABLE로 고친 뒤38passed. 이 pre-capture 실패는 별도 기록에 보존했다.
최종 관련 시험은 Windows296passed(5.42s) / 별도WSL305passed(22.80s), 실패/error/실제skip0.
관련 시험에는 새86개와 이전210개, WSL에는 추가9개 integration이 들어 있다.
**LOCAL FULL 생략 / 관련 시험으로 대체 / 새 독립 연구·시험·문서만 변경,
기존 실행·공용 물리·동결 계약·fixture 불변. 공식 기준선 미갱신.**

## COMBINED ARCHITECTURE POSSIBILITY

두 축을 독립 실행한 뒤 평가했다. tensor small-χ 이득은 B에서 실패했고 Hotline의
cheap-monitor/cost 이득도 실패했다. 따라서 이번 Gate에서 결합 prototype으로 진행할
근거는 부족하다. 형태상 block internal factor + 모든 block의 verified baseline이라는
계약은 공존할 수 있지만, 틀을 그릴 수 있다는 사실이 계산 이득을 뜻하지 않는다.
통합 production·tensor-block Hotline 구현은 하지 않았다.

## WHAT THIS PROVES

봉인한 finite corpus에서 지정한 세 mode partitions의 singular/error/cost를 재현했다.
고정-H의 짧은 evolution에서 required χ 증가는 관찰되지 않았다.
작은 hierarchy에서 영향 누락 없이 coarse account와 numeric escalation을 함께 제공했고,
정확한 output을 복원해 다음 step으로 넘겼다. 지정한 starvation/thrashing/order/hidden-event
및 mutation challenges를 통과했다. 최적화 이득의 부재도 결과다.

실행 시험과 별도로 [author_concept_review.md](electronic_compressibility_hotline_v1/author_concept_review.md)에
설계자 구상 일치성을 검토했다. layer/coverage/resolution의 의도는 지켰지만,
cheap global extension이라는 비용 목표는 아직 이루지 못했다.

## WHAT THIS DOES NOT PROVE

continuum electronic reality, complete basis limit, electron-nuclear dynamics, 큰 many-electron
state, long-time χ stability, 일반 TN 효율, 모든 MPS bonds, cold disk I/O 절약,
엄밀 roundoff certificate, 외부 audit, A 전체 확장성 또는 production 승인은 증명하지 않는다.

오차 장부: clamped-nuclei/nonrelativistic 모델은 기존과 같고 오차를 새로 추정하지 않았다.
finite cc-pVTZ basis 오차와 외부 reference 불확실성도 그대로 미평가다. 저장 eigensystem을
재사용했으며 새 lowest-root 인증은 없다. SVD·unitary·좌표 변환은 binary64 numerical
검증이다. representation discarded error만 이번 Gate에서 직접 측정했다.
Fraction coefficient enclosure의 정확성과 continuum 물리 정확성을 구분한다.

## NEXT DESIGNER DECISION

**현재 구현으로 큰 TN·통합 Hotline·A production 확장을 권하지 않는다.**
다음 가치 있는 좁은 질문은 (1) 전체 exact coefficient를 재읽지 않고 갱신 가능한 bound가
있는가, (2) 엄격한 상태 오차를 유지하면서 같은 문제의 일관된 모든-bond 표현이 dense보다
작아지는가다. 새 corpus나 더 긴 시간/더 큰 전자 수/새 오차 계약은 별도 설계자 결정 사항이다.
이번 결과를 좋게 보이게 만들기 위한 tolerance 완화나 ordering 추가 탐색은 하지 않았다.

## GIT END STATE

시작 local Survey HEAD `8c01884886e7f92fbbd25467428519d021a76eb0`, clean,
log5 확인 뒤 별도 managed worktree와 `codex/electronic-compressibility-hotline-v1`를 만들었다.
기존 H₂/Sector/StateHistory/Survey code/artifacts는 보존했다. preimplementation 보호
manifest234개 SHA와 기존 tracked diff를 끝에 재확인한다. 모든 새 raw는 별도
`runs/electronic_compressibility_hotline_v1_20261004/`에 있다.
최종 commit·clean 상태·recovery ZIP/복원 검사는 Git 밖 `git_end_v1.json`에 적는다.
이 보고서에 자기 자신의 최종 commit SHA를 넣어 순환 seal을 만들지 않는다.
**push하지 않았다. root/master나 이전 research branch를 merge하지 않았다.**

### 설계자 질문 12개에 대한 쉬운 답

1. 일부1전자 표현은 작지만2전자에서는 현재 엄격한 기준의 작은 χ 이득을 얻지 못했다.
2. ground뿐 아니라 excited·중첩·evolved도 검사했다. 두 전자에서 모두 작은 χ 승인 조건을 충족하지 못했다.
3. t=0,0.5,1에서는 요구 χ가 증가하지 않았다. 더 긴 시간·다른 많은 전자 상태는 모른다.
4. 모든 기여를 유지하고 일부를 정밀 승격하는 작은 prototype은 가능했다. 계산 절감은 달성하지 못했다.
5. COLD center/bound를 항상 포함하고 canonical output에서는 정확히 복원했다.
6. 매 round 모든 block을 갱신했다. 봉인한 K=1을 지켰다.
7. 세 계산 순서의 physical output bytes가 같았다.
8. 반경 획득까지 포함한 감시는 REF 계산보다 비쌌다. 감시가 새 병목이다.
9. 경계 제어 시험의 전환은6회에서2회로 줄었다. 실제 conversion/bound 비용은 여전히 컸다.
10. 정확성 계약의 공존 가능성은 있지만 결합 구현으로 갈 비용 근거는 부족하다.
11. A 전체 확장성 이득은 확인하지 못했다. 이 작은 구현은 더 느렸다.
12. 큰 통합 구현보다 cheap bound와 일관된 factor 표현을 좁게 검토할 가치는 있다. 자동 착수하지 않았다.

### 읽기·검증·방법 출처

첨부 요청과 AGENTS/RULES를 읽고 CURRENT_STATE/REPO_MAP의 활성 상태·전자 연구 경로를
부분 읽었다. 문서 안내/색인과 직전 corpus 구현을 확인했다. 저장소 전체·이전 runs 전체는
읽지 않았다. 신규38개 사전시험, 최종293/302개는 새로 실행한 결과이며 과거 로그를 세지 않았다.

Schmidt 범위 해석 참고: [Vidal, Phys. Rev. Lett. 91, 147902](https://doi.org/10.1103/PhysRevLett.91.147902).
orbital partition과 chemistry 적용 범위 참고: [Boguslawski & Tecmer, Int. J. Quantum Chem. 115](https://doi.org/10.1002/qua.24832).
수치 결론은 이 문헌의 성공 결과를 재사용한 것이 아니라 본 corpus의 직접 측정이다.

Scientific-critical-thinking skill을 구상 검토와 증거 경계에 사용했다.
방법 출처: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026),
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
현재 arXiv record(v2, 2026-09-02)를 확인했으며 이 skill 자체를 검증 보증으로 취급하지 않는다.
