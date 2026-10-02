# C1-C / MULTIPARTICLE GAS FOUNDATION — SMALL-A FOUNDATION V0

**작성일:** 2026-10-01. **분류: PROPOSAL / DESIGN ONLY / 미구현 / 미승인 / 미동결.**
설계 기준 HEAD `985c6e29574bc70060a0400ee3dc64995f7e8d79`.
이 문서는 C1-B1 종료나 C1-C 착수 승인이 아니다. 최종 숫자·경계·검증 전략의 결정권자는 설계자다.

## 1. 목적

40Ar 여러 개가 3차원에서 장시간 상호작용하는 첫 작은 A를 만들기 전에, 두 원자 계약의 확장 가능성과 필요한 새 계약을 정리한다. Small-A0의 질문은 **다원자 물리 세계를 결정론·과정 보존·독립 검증과 함께 운영할 수 있는가**다. 생명·화학·물·광물·막·복제·생태·기후·대륙은 이번 단계의 목표가 아니다.

먼저 공개할 한계:

- 현재 two-body PES와 두 원자 계산 검증은 다원자 현실 검증이 아니다. pairwise Ar는 선언된 모델 후보다.
- 온도만으로 가능한 최대 pair 에너지, 희박성, N, 박스, 운영시간을 정할 수 없다.
- pair별 반올림과 총힘 반올림은 다른 이산 법칙이다. PBC의 nearest image와 모든 image 역시 다른 법칙이다.
- 다원자 KDK·periodic guard·reference·independent verifier·CPU/GPU fast path는 미구현이다. 비용은 식으로 추정하고 시간 실측은 하지 않았다.

표현은 **기존 승인**, **현재 코드 사실**, **문헌 근거**, **독립 대수 결과**, **조건부 추정**, **권고 후보**, **설계자 미결**로 구분한다. 수치 검증을 인증으로, proposal을 승인으로 승격하지 않는다.

## 2. 기존 승인 계약과 제약

| 출처 | 이번 설계에 적용하는 내용 | 확장 시 새 의무 |
|---|---|---|
| [헌법](../../PROJECT_CONSTITUTION.md), [RULES](../../RULES.md) | 결정론 A, 과정·역사 보존, B 비간섭, 계산 기술의 물리 비간섭 | 초기조건도 정확히 기록; scheduler·ID로 결과 선택 금지 |
| [X1–X5](../reference/A_EXECUTION_ARCHITECTURE_V1.md) | X2 reference 영구 유지; 정규화 상태·사건 이력·인과 결과 정확 일치. X3 정확한 전체 영향 입력 캐시. X4 현재 무손실 요약만 | long-range에서 국소 색인/캐시의 인과 입력을 임의로 줄이지 않음 |
| [세 층 분리](../active/A_THREE_LAYER_SEPARATION_V1.md) | 세계/검증/관측 분리. C1-B1 N-1: 승인된 verifier의 전 step 재검증을 거쳐 CONFIRMED; C1-C 전 재평가 | C1-C 최소 등급과 새 fingerprint의 설계자 판정 |
| [C1-A 동결](../frozen/C1A_AR2_FREEZE_V1.md), [C1-B1 설계](../active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) | Lang exact published decimals, retardation ON, r_min=1.2 Å, source-versioned 단위·질량. exact Δr/R², pair impulse once-round, 변위 once-round drift, fail-closed | 합산·image·wrap·동시 갱신·overflow·다원자 오차 계약 |
| [reachable-domain 감사](../active/C1B1_SMALL_WORLD_REACHABLE_DOMAIN_V1.md) | SMALL_WORLD_ENVELOPE_UNDEFINED; 현재 목표 세계의 boundary_pass 판정 불가 | 공간·물질량·시간·초기 총에너지부터 정의 |
| [L 원칙 v2](../reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md) 6.1 | 작은 영향만으로 경로 삭제 금지; 전체 범위 누적 상한·사전 기준·확장 시 재검토 | 이번 Ar에서도 누락 힘/다체 효과의 적용 범위를 기록 |
| [상위 계산 proposal](A_WORLD_COMPUTE_ARCHITECTURE_AND_SCALE_V0.md) 32절 | 미승인. 멀티스케일과 X2/X4 충돌 미해결; GPU 조건부 | 이 문서를 가속·손실 모델의 승인 근거로 사용하지 않음 |

**현재 코드 사실:** [two_atom](../../a_reference/c1b1_two_atom.py)은 FX(96,48) 위치 / FX(96,80) 운동량의 기존 사용 프로파일, KDK dt=40 a.u., E_rel≤10 D_e 초기 적분기 검사와 drift 선분 r_min guard를 가진 두 원자 경로다. E_rel 검사는 현재 초기화 경로의 검사이며 매 step의 다원자 범위 gate가 아니다. D_valid는 동결 canonical 초기 상태의 제한된 실측 evidence이고 scope=`initial_state`다. 에너지가 10 D_e 아래라는 사실만으로 D_valid 멤버가 되지 않는다. D_valid를 순간 pair 상태의 인증서나 불변 영역으로 재사용하지 않는다.

현재 [Yoshida40](../active/C1B1_YOSHIDA40_CANDIDATE_STATUS_V1.md)은 `VALIDATED NUMERICAL CANDIDATE / NOT PRODUCTION / NOT FORMALLY CERTIFIED`. 기존 O-1 STOP, A-EV 미해결, ④-Liveness NotCertified, ④-Safety Conditional을 이 proposal로 바꾸지 않는다.

## 3. Small-A0 후보 정의

| 항목 | 권고 출발 후보 | 미결/검증할 점 |
|---|---|---|
| 물질·차원 | 40Ar only, 3D | 현실 비교 자료의 동위원소 조성 차이 |
| 상태 | 위치+운동량; 질량은 species 계약 | 프로파일·범위·periodic image counter 형식 |
| 상 | 희박 기체 | n=N/V, 초기 구조·에너지, 상/cluster 통계가 필요 |
| 경계 | 3D periodic 후보 | minimum image / full image / 다른 경계 결정 |
| driving·thermostat | 외부 driving 없음; production thermostat 없음 | 준비 단계도 별도 기록; thermostat로 검증 결과 교정 금지 |
| ensemble | 닫힌 NVE 의도 | 연속 H 보존과 이산 KDK의 H 오차를 분리 |
| 법칙 | 기존 Ar-Ar PES에 기반한 pairwise 후보 | nonadditive physics를 빠뜨린 현실 오차 |
| 초기조건 | 정확한 q,p 목록과 생성 절차를 사전 봉인 | 난수/확률 추첨 없음; 결정론적 준비가 Maxwell 분포를 보장하지 않음 |

온도는 관측량 후보 `T_kin=2 K_int/[3(N−1) k_B]`(N>1, COM 3 자유도 제거)에 붙이는 이름이다. 작은 비평형 상태의 단일 순간값을 열평형 온도라고 선언하지 않는다. 준비 목표, 순간 T_kin, 구간 평균, equilibrium 판정 기준을 따로 기록한다. 평형을 만들기 위한 production 온도 보정·속도 재척도화는 넣지 않는다.

initial exclusion은 현실 준비 조건으로 근거를 제시해야 한다. cluster/3-atom encounter가 관측되었다는 이유로 원자를 분리하거나 세계를 다시 고르지 않는다. 준비 목록을 봉인하고 실패·정지·미발생을 포함해 모두 보고한다.

## 4. 온도 후보 200/300/400 K 비교

`≤T_max`는 하한·평형·밀도를 정의하지 않는다. 아래는 **각 상한 온도에서의 고전 Maxwell 기체 계산식 비교**다. 0 K까지 지원한다는 뜻이 아니다. 첫 물성 비교 구간 후보는 200–300 K, 첫 상한 후보는 300 K다. 200 K 미만은 별도 E-QC·phase 범위 검토 없이 포함하지 않는다.

단위 환산은 [NIST CODATA 2022](https://physics.nist.gov/cuu/pdf/factors_2022.pdf)의 k_B=3.1668115634564×10⁻⁶ E_h/K, 기존 `D_e=0.000451995775 E_h`를 썼다. 이 환산은 설계 표 계산용이며 frozen 상수 갱신이 아니다. `x=E∞/(k_BT)`에서 E∞는 **고립 산란의 점근 상대 운동에너지**다.

| 상한 후보 | k_BT / D_e | 무작위 pair의 E∞>10 D_e | 충돌 flux proxy의 ≤10 D_e / >10 D_e | 점성 kernel proxy의 >10 D_e |
|---|---:|---:|---:|---:|
| ≤200 K | 1.40126 | 0.2556% | 99.3527% / 0.6473% | 7.4924% |
| ≤300 K | 2.10189 | 2.3170% | 95.0565% / 4.9435% | 30.0708% |
| ≤400 K | 2.80251 | 6.7674% | 87.1149% / 12.8851% | 52.1985% |

**가정/조건부 추정:** Maxwell에서 무작위 pair는 Gamma(3/2)이며 tail=`erfc(√x)+2√(x/π)e⁻ˣ`. 일정 encounter cross-section σ를 가정한 flux는 Gamma(2), tail=`e⁻ˣ(1+x)`. 실제 Ar encounter는 σ(E)·b 선택·상관에 따라 다르다. 장거리 힘에서는 아무 거리 제한 없이 모든 약한 접근을 세는 “충돌 횟수” 자체가 적절한 관측량이 아닐 수 있다. encounter 정의는 관측 층에서 봉인하고 힘 계산을 자르지 않는다.

점성 표는 `Q^(2)(E)`를 상수로 둔 Gamma(4)의 **kernel proxy**다. 실제 점성 누락 비율, 실제 충돌 비율, 운영 STOP 확률, D_valid coverage, certified coverage가 아니다. [Lang §IV.3, 식50](https://arxiv.org/html/2304.14719v2)에서 첫 점성 collision integral의 weight는 `E³ exp(−E/k_BT) Q^(2)(E)`이다. higher-order CE는 다른 적분도 필요하다.

## 5. 필요한 collision-energy envelope

### 5.1 꼬리 기준에서 역산한 후보

비교용 기준은 q=10⁻⁴(0.01%)와 10⁻⁶(0.0001%). 실제 O-3 총오차를 먼저 배분한 뒤 선택한다. q_vis proxy=`e⁻ˣ(1+x+x²/2+x³/6)`를 이분법으로 역산했다. **점성 계산이나 궤적 실행은 하지 않았다.**

| T_max | flux proxy q≤10⁻⁴ / 10⁻⁶에 필요한 E∞/D_e | 점성 kernel proxy q≤10⁻⁴ / 10⁻⁶에 필요한 E∞/D_e |
|---|---:|---:|
| 200 K | 16.474 / 23.385 | 22.299 / 29.917 |
| 300 K | 24.711 / 35.077 | 33.449 / 44.876 |
| 400 K | 32.947 / 46.770 | 44.599 / 59.835 |

```text
T_MAX_CANDIDATE = 300 K                  # 설계자 미승인
T_MIN_FOR_FIRST_O3_CANDIDATE = 200 K     # ≤300 K 전체를 보증하지 않음
TAIL_BUDGET_CANDIDATE = 1e-4            # 실제 Q(E) 적분 오차에 적용할 후보
E_O3_SCAN_START_CANDIDATE ≈ 33.45 De    # constant-Q proxy로 조사 시작점을 산출
stricter alternative ≈ 44.88 De        # proxy 1e-6
E_WORLD_HARD_MAX = UNDEFINED
E_INTEGRATOR_VALIDATION_MAX = UNDEFINED # hard world 조건과 O3 필요 범위 판정 후
```

33.45 D_e나 44.88 D_e는 공식 상한이 아니다. 실제 high-E tail은 `Q^(2)(E)` upper enclosure와 Ω의 lower bound를 사용해 `tail Ω / Ω≤q`를 확인해야 한다. η와 Ω는 역수 관계이므로 허용 η 오차로 변환해야 한다. higher-order CE·low-E·large-b tail도 별도 배분한다. 세계에서 33.45 D_e 밖 힘/사건을 삭제하는 규칙은 제안하지 않는다.

**200 K:** 지원 high-E 부담을 줄이고 thermal O-3를 시작할 수 있으나 10 D_e를 완전 영역으로 만들지는 못한다. 낮은 온도로 내려갈수록 quantum·cluster·상 검토가 더 필요하다. **300 K:** 현실 자료가 있는 상온 근처부터 시작하는 절충 후보. **400 K:** 물성 비교 범위를 늘리지만 proxy 필요 상한이 300 K의 4/3이고 더 빠른 근접 접근으로 dt·정밀도 비용 위험이 커진다. 실제 비용 배수는 미측정이다. 35–50 D_e의 옛 추정을 복사한 것이 아니다.

### 5.2 유한 deterministic 세계의 hard bound는 별도다

**독립 대수 결과:** 동일 질량 m, P=Σp_i, K_int=Σ|p_i−P/N|²/(2m), H_int=H−|P|²/(2Nm)라 두면

```text
K_rel,ij = |p_i−p_j|²/(4m) ≤ K_int
K_int = H_int−U
H_int(t) ≤ H_int(0)+δ_H(t), U≥U_min
⇒ K_rel,ij ≤ H_int(0)+δ_H(t)−U_min.
```

따라서 초기 총에너지·potential 전역 하한·운영시간 동안 numerical energy residual 상한이 필요하다. 순간 `E_pair=K_rel,ij+V_ij`는 다른 원자가 있으면 보존되지 않는다. finite primary-pair model에서 M=N(N−1)/2, **증명된** `V≥−D_*`가 있으면 조건부로 `K_rel≤H_int(0)+δ_H+M D_*`, `E_pair≤H_int(0)+δ_H+(M−1)D_*`를 얻는다. nominal D_e를 certified global minimum D_*로 대신하지 않는다. 이는 넓은 충분 상한이고 attainable 최대/실제 reachable 영역 증명이 아니다. full periodic model에는 별도 lattice/stability 하한과 energy 분해가 필요하다.

Maxwell 분포는 무한 tail을 갖는다. 유한 thermal E_max는 전체 분포의 100%를 덮지 않는다. T_kin 상한을 매 순간 만족한다는 조건하에서는 K_int에서 상한을 얻지만, T_max를 초기 목표로만 준 상태에서 그 조건이 영원히 유지된다고 가정할 수 없다. 에너지 guard가 필요한지, 선언 영역 이탈 시 정지하는지, 관측 envelope와 물리 정의를 어디까지 나누는지는 미결이다.

## 6. 다입자 force/impulse accumulation 계약 후보

**권고 후보 P:** 한 half-kick의 동일 q에서 각 unordered pair를 한 번 정의한다. j에 줄 exact real impulse A_ij=h F_real(R) Δr/R를 momentum grid로 한번 반올림하여 J_ij를 얻고, i에는 −J_ij를 준다. 모든 원자별 Δp를 **넓은 정수에서 정확 합산**한 다음 모든 최종 p의 범위를 검사하고 동시에 반영한다. R과 F를 먼저 반올림하지 않는다. 성공한 grid 정수 덧셈에 추가 손실 반올림은 없다.

| 조건 | 결과/한계 |
|---|---|
| 같은 q snapshot·같은 grid·±같은 J·정확 합·범위 성공 | ΣΔp=0 정확; pair·worker·thread 순서 무관 |
| pair를 찾는 ID 순서만 다름 | 정규화된 물리 결과 동일이어야 함; ID는 저장 참조 역할뿐 |
| 원자 p에 pair마다 즉시 쓰기 | 임시 overflow·부분 갱신·순서 의존 위험; 금지 후보 |
| pair tiny force가 개별 0으로 round | 집단 real 총힘을 한번 round한 결과와 달라질 수 있음 |

**다른 후보 T:** exact analytic ΣA_ij를 원자마다 enclosure로 합친 뒤 once-round. pair rounding noise는 줄지만 총운동량 exact 보존은 자동이 아니다. grid 단위로 `round(.4)+round(.4)=0`, `round(.8)=1`; 반대로 총합 0인 원자 impulse `(-.8,.4,.4)`의 개별 round 결과 합은 −1이다. P와 T는 다른 계약이다. 잔차를 ID가 작은 원자에 보정하면 label leakage다. coupled rounding을 원하면 교환/평행이동 대칭·N=2 환원·범위·결정성의 새 계약을 따로 설계한다.

P의 finite-primary model에서는 원자 성분당 half-kick real aggregate와의 rounding residual이 ≤(N−1)u_p/2이다. S step의 2 half-kick에 대한 동일 경로 직접 residual 합은 ≤S(N−1)u_p. 이는 **전체 궤적 오차 상한이 아니다**. full-image에서 image마다 round하면 항 수·순서·tail 합산 문제가 달라진다. 권고는 image force 전체를 pair 단위로 enclosure해 once-round하는 후보이며, image별 round와 분리해 승인받는다.

reference accumulator는 arbitrary integer 후보. fixed 96-bit J와 p를 N개 규모로 합할 때 `97+ceil(log2 N)` bit는 보수적인 합산 용량 예시다. 실제 J 입력 범위·부호·carry와 최종 p 범위를 따로 규정해야 한다. aggregate J는 96 bit를 넘을 수 있어 witness도 자동으로 96 bit가 아니다. GPU fixed wide accumulator overflow는 resource refusal이고 물리 clamp가 아니다. fast 채택 전에 선언 N/J 범위에서 accumulator 폭이 충분함을 증명하거나 exact fallback을 정의한다. CPU는 성공하지만 GPU 내부 폭 때문에 거부하는 지원 범위 차이는 공개해야 한다. 모든 pair·drift·guard·마지막 kick이 성공하기 전 committed state는 갱신하지 않는다.

## 7. integrator 확장 의무

첫 reference는 **KDK 의미 유지 후보**다. 다원자와 새 적분기를 동시에 도입하지 않는다. dt=40은 자동 채택하지 않는다. 기존 dt=40/E_rel≤10 D_e의 두 원자 validation과 O-1 진단을 구분하고 현재 STOP을 보존한다.

검증 계획 후보는 (1) N=2 비periodic reduction, (2) 동시 N≥3 force 합산·교환/순서 불변, (3) 선택 에너지 범위에서 dt 수렴, (4) 가깝고 겹친 encounters에서 총 가속도·curvature·guard, (5) periodic drift/image, (6) 긴 finite 기간 H drift/oscillation·P와 기록 비용이다. pair E_max만으로 N-body accuracy를 보증하지 않는다. force Hessian·동시 이웃 수·전체 envelope가 새 오차 원인이다.

drift는 기존 의미 `δq=round_pos(p_half dt/m)` 뒤 exact grid 이동을 보존한다. guard는 최소한 실제 반올림 전 상대 drift 선분과 저장 끝점의 r_min 검사라는 기존 두 원자 의미를 환원해야 한다. periodic에서는 unwrapped 선분의 모든 관련 images를 검사하고, wrapped endpoint만 보지 않는다. guard·정밀도·overflow 실패는 명확한 사유로 전체 step을 중단한다. step 뒤 조용히 dt를 줄여 재실행하거나 reflection/clamp로 이어가지 않는다.

동결 상수 r_min=1.2 Å 아래의 physics는 undefined다. 그 아래 실재 사건을 “반발해서 안전함”으로 처리하지 않는다. 끝까지 실행된 표본은 그 표본의 검증이며 전체 Liveness 인증이 아니다. Yoshida40·KDK20 production 승격은 이번 범위 밖이다.

## 8. long-range interaction 문제

| 후보 | 계약 관계 | 계산/증명 의무 |
|---|---|---|
| A: reference all pairs | finite pair 법칙이면 M pair 전부 직접 계산 | PBC full image라면 pair 내부 image 무한 합까지 별도 처리 |
| B: spatial index | pair 나열/타일/순서의 실행 기술 | 멀리 있는 pair도 계산하거나 동등한 정확 경로로 연결; index만으로 O(N) force가 되지 않음 |
| C: finite cutoff | 세계 법칙 근사 변경 | 거리·밀도·N·기간의 누적 오차, guard 경계, 희귀 사건 영향을 사전 봉인. 지금 적용하지 않음 |
| D: analytic/bounded tail | 포함한 법칙의 정확 rounding evaluator 또는 관측 근사 | 둘을 구분. omitted sum enclosure가 유일 round를 결정하면 계산 표현; 힘을 0으로 두면 근사 |
| E: dispersion Ewald/PME/FMM 등 | 조사할 실행 후보 | Lang 전체 항·정확 rounding·X2 일치 증명/차등 검사 필요; 일반 MD accuracy만으로 승인 못 함 |

전체 omitted direct impulse의 장부는 같은 경로에서 `N−1`, M, 기간 τ 또는 step sum을 써서 작성한다. `작은 힘×pair 수×시간`만으로 실제 두 세계의 trajectory 차이가 닫히지 않는다. 힘 누락이 위치를 바꾸고 후속 힘을 바꾸므로 force derivative·domain 유지·오차 전파 또는 선언 관측량 비교가 추가로 필요하다. 희귀 경로는 공간·물질량·시간 전체의 rate/candidate count를 중복 없이 계산한다. 이것도 실제 deterministic 발생 확률의 증명이 아니다.

**문헌/코드 범위:** Lang retarded 법칙은 단순 −C6/r⁶가 아니다. BO g(R), damping, REL의 r⁻⁴ 상쇄, 작은 REL/QED r⁻⁶ 잔여 등을 그대로 다뤄야 한다. 순수 London 또는 순수 r⁻⁷로 교체하지 않는다([Lang §III.4](https://arxiv.org/html/2304.14719v2), [frozen source](../../a_reference/ar2_lang2024.py)). [GROMACS dispersion 문서](https://manual.gromacs.org/current/reference-manual/functions/long-range-vdw.html)의 LJ-PME는 r⁻⁶ 처리의 알고리즘 선례다. Lang 전체·fixed grid 비트 일치 구현의 증거가 아니다.

상한을 만족할 수 없으면 먼저 공간·N·운영시간을 줄인다. 수학적으로 동일한 raw 0 결정은 가능하지만, pair별 0을 여러 개 합해 총힘도 0이라고 바꾸는 것은 P/T 반올림 계약과 결합해 검토한다.

## 9. pairwise vs many-body 현실성

**문헌 근거:** Ar의 nonadditive three-body potential과 third virial 연구가 존재한다([Cencek 등, 2013/NIST](https://www.nist.gov/publications/three-body-nonadditive-potential-argon-estimated-uncertainties-and-third-virial)). 이 자료는 three-body 효과를 조사해야 한다는 근거이며 현재 Lang pair 합의 특정 밀도에서 오차가 몇 %라는 답은 아니다. 연구의 pair PES도 현재 계약과 다르다.

밀도 제한은 **UNDEFINED**다. `Z=1+B(T)n+C(T)n²+…`에서 nonadditive가 C에 주는 ΔC를 조사해 `|n² ΔC|`를 압력/평형 오차 budget과 대조하는 방법은 후보다. third virial 전체에는 pair 유래 항도 있으므로 C 전체를 three-body 오차로 세지 않는다. 이 조건만으로 viscosity나 순간 three-body force 오차가 닫히지는 않는다.

현실 정당화에는 (a) 해당 T 구간의 density expansion·uncertainty, (b) triple geometry별 V3/F3 범위, (c) close triple encounter의 정의/빈도, (d) 전체 τ,N,V에서의 누적 상한, (e) 관측량별 finite-density error budget이 필요하다. 고밀도·cluster·동시 근접 접근·finite-density 물성 budget 초과·long duration에서 누적 영향이 작지 않은 경우는 3-body 연구를 요구하는 재검토 조건 후보다. 물리 force를 새로 구현하지 않고 먼저 적용 범위를 줄이거나 현실성 표기를 제한한다.

희박성은 pair approximation에 유리하지만 close triples를 불가능하게 만들지 않는다. 그 사건을 삭제하면 선언한 세계도 바뀐다. pairwise 세계의 내부 정확 실행과 현실 Ar의 정확 재현을 구분한다.

## 10. periodic boundary 문제

**설계자 미결:** 다음 세 모델을 섞지 않는다.

1. **minimum image:** 각 pair에 nearest displacement 하나만 사용한 유한 torus potential. all-primary-pair 계산이지만 먼 복제 image를 생략한다. Lang 무한 periodic 합과 다르다. half-box 면에서 gradient cusp/tie가 있다.
2. **full periodic images:** fixed orthorhombic box 후보에서 `U=1/2 Σ_i,j Σ_n' V(|q_i−q_j+nL|)`, n∈Z³, i=j,n=0만 제외. 모든 images를 pair 단위로 합쳐 round하는 법칙 후보. 3D에서 충분히 빠른 inverse-power tail의 lattice 합은 수렴하나 실제 frozen 각 항의 finite shell+remainder enclosure·derivative·rounding 결정은 미구현이다.
3. **다른 경계:** 비periodic 유한 cloud/현실 wall 등. free cloud는 팽창하며 bulk density·장시간 homogeneous gas를 보장하지 않는다. wall은 새 외부 물리와 교환/운동량 계약이 필요하다.

minimum image half-box에서는 `L/2≡−L/2`라 representative 불변 nearest displacement와 odd sign을 동시에 유지할 수 없다. ID로 부호를 정하면 물리에 이름이 들어간다. 명시적 대칭 tie law(새 법칙), tie에서 refusal(운영 한계), full image 후보를 비교하고 승인받는다. generic half-open wrap을 force law로 숨기지 않는다. full image force는 대칭 image pairing으로 tied component를 상쇄할 수 있다.

self image(i=j,n≠0)는 fixed box에서 위치와 무관한 energy를 주며 중앙 force의 ±n 쌍은 상쇄한다. self force를 임의로 더하지 않지만 energy 영점·box derivative/pressure 정의에서는 그 항의 포함 여부를 명시한다. box가 너무 작아 self image 자체가 r_min 안에 들면 물리 domain 문제다.

wrap은 물리 벽/충돌이 아니라 표현 후보다. box 길이를 position grid의 정확 정수 배수로 두고 floor/divmod로 modulo를 정의하는 후보, wrapped q+정확한 integer image counter로 unwrapped q를 보존하는 후보를 검토한다. counter 범위·overflow·정확한 역사 복원·canonical 비교를 새 계약에 포함한다. 기존 비periodic overflow를 조용히 wrap으로 바꾸지 않는다. 과거 two-atom 좌표 contract는 그대로 둔다.

r_min guard는 상대 unwrapped drift segment가 거리 r_min 내로 갈 수 있는 image lattice 후보를 정확 bounding box로 찾아 검사하는 설계가 필요하다. multi-wrap·경계 통과·stored endpoint 모두 포함한다. guard에 쓰는 유한 image 후보 검색은 힘 cutoff가 아니다. 힘은 선언한 전체 image 법칙대로 계산한다. PBC의 모든 pair image force에도 ±동일 J와 exact aggregate를 적용해야 P가 보존된다.

N,L 변경 시 image 힘·energy·반복 충돌·finite-size correlation이 달라진다. 같은 n에서 N을 늘리는 시험과 같은 N에서 L을 바꾸는 시험은 다른 질문이다. PBC 채택을 일반 MD 관행만으로 승인하지 않는다. **권고: PBC를 원하면 full-image 의미부터 설계하되 evaluator 비용을 확인하기 전 채택하지 않음.**

## 11. reference executor

X2대로 single-thread, no GPU, no spatial index, no cache, no summary. exact rational geometry/단위·wide integer aggregate·enclosure로 J once-round·단순 KDK를 정의할 후보다. transcendental 값을 exact rational인 척하지 않고 enclosure로 유일 반올림을 결정한다. reference는 모든 primary pair와 선택한 image 법칙을 명시적으로 계산한다. full image remainder가 결정되지 않으면 REFUSED다.

초기 q,p·box·법칙 fingerprint·dt·프로파일·rounding·guard·step index·정규화 사건/causal record를 포함하는 직렬 명세가 필요하다. 로그 ID는 참조 용도이고 force 우선순위가 아니다. 동일 종류 원자 permutation은 입력/출력 label bijection 아래 물리 결과가 같아야 한다. 정지/불일치도 canonical history에 기록한다.

N=2 비periodic 모드에서 기존 계약 환원, N=3에서 상쇄·rounding·동시 갱신·triple geometry, N=4에서 서로 다른 두 장소의 pair-dominated encounter 동시 진행 검사를 먼저 설계한다. N=4에서도 모든 cross-pair tail을 유지하며 “한 번에 사건 하나만 처리”하는 숨은 천장이 없는지 본다. 이는 계약 pilot의 최소 구조별 시험 목적이며 장기 기체를 대표할 N을 정하는 것이 아니다. N=3/4는 충분한 gas ensemble이 아니다. reference를 fast path 개발 뒤 삭제하지 않는다.

## 12. fast CPU/GPU path

| 후보 | 기대/비용 | 채택 전 의무 |
|---|---|---|
| high-clock ~16 core CPU | 적은 N·높은 정밀도/직렬 단계에 유리할 가능성 | 실제 profile·승인된 소규모 비용 조사 전 성능 미확인 |
| ≤64 physical core CPU | 독립 pair tile/검증 chunk 병렬 후보 | 정수 exact reduction, oversubscription·메모리 경합·비균일 정밀도 비용 |
| single CUDA GPU, L40/L40S 48 GB class 후보 | regular pair batch 후보 | native J 비트 동등성 사용 전 Gate; multiword integer·enclosure·CPU fallback |
| spatial indexing/batching/cache | 정확한 pair 나열·동일 입력 재사용 | omitted interaction 없음, global/image input dependency, X2/X3 |

GPU float atomic accumulation은 후보 P의 계약과 맞지 않는다. 일반 96-bit atomic 지원을 가정하지 않는다. tile별 wide exact accumulator와 segmented reduction 또는 검증 가능한 multiword 표현 후보를 두고 overflow/정밀도 거부를 분리한다. scheduling을 바꿔도 canonical history가 같아야 한다.

fast adoption은 **X2 정규화 상태+이력+인과 결과 정확 일치**다. X4는 정확한 summary/multiresolution을 도입할 때 추가 적용한다. 단순 CUDA 채택을 X4의 승인으로 해석하지 않는다. 통계적 pressure/η 일치만으로 X2를 통과시키지 않는다. GPU와 verifier가 같은 evaluator를 공유해 서로를 독립 검증했다고 말하지 않는다.

하드웨어는 resource 후보이며 물리 계약이 아니다. host128 GB target / 256 GB ceiling 후보, GPU 한 장, Small-A0 multi-GPU 없음이라는 요청의 비교 범위에서 검토한다. VRAM≥40 GB 필수 여부는 미결이며 현재 raw memory 식으로 정당화되지 않는다.

## 13. verification scaling

**N-1 재평가 요청안:** 처음 finite Small-A pilot은 전 step independent replay를 권고 후보로 유지하되, 설계자 판정 전 C1-C CONFIRMED 규칙으로 고정하지 않는다. 기존 C1-B1 N-1은 그대로다. 새 accumulation·boundary/image·guard·wrap에 대한 양측 구현·fingerprint·결함 주입 승인 비용을 포함한다.

| 경로 | 저장/연산 | 증거 의미/결정 |
|---|---|---|
| 모든 step pair J witness+independent replay | witness O(SM), verifier O(SM) 이상 | 정보가 많지만 저장 큼; REPLAY_VERIFIED 자격은 새 verifier 승인 후 |
| 모든 step net atom half-kick witness+independent replay | witness O(SN), verifier는 모든 pair를 재계산해 O(SM) 이상 | 무손실 상태/역사 복원 규칙을 만족하면 절약 후보. 계산비는 자동 감소하지 않음 |
| checkpoint+결정론적 재생성 | checkpoint O(SN/C), 재검증 계산 그대로 | spec·initial·실패·사건 기록과 무손실 전체 복원 증명 필요; certificate만 남기면 불충분 |
| streaming/pipeline | peak buffer/지연·backpressure 조절 | 모든 step 검사와 원본 재검증 자료 보존 의무 동일 |
| 일부 sampled audit | verifier 샘플 비용 감소 | SAMPLED_AUDITED는 검사한 샘플만. 전체를 REPLAY_VERIFIED/CERTIFIED로 부르지 않음 |
| 별도 formal step/checker | proof 생성·검사 비용·completeness 미측정 | CERTIFIED는 정의/승인 scope의 증명이 있어야 함; 자동 대체 없음 |

net witness는 reference가 pair별 once-round하여 만든 aggregate를 verifier가 **모든 pair의 독립 계산**으로 확인할 때만 같은 의미다. 단순 real total-force enclosure를 once-round해 검증하면 후보 T를 검사하는 셈이다. net은 개별 pair J를 역복원하지 못하지만, 초기 상태·모든 net transition·법칙으로 canonical 세계 역사와 관측 사건을 정확히 재구성할 수 있는지 명세해야 한다. required causal record를 따로 저장해야 하는 경우 그 비용을 추가한다.

기존 승인 비용 2.773×CPU, 2.537×4-worker batch wall, 22.220 B/step는 **두 원자 지정 7개 역사 자료**다([세 층 문서](../active/A_THREE_LAYER_SEPARATION_V1.md) 3절). 새 N-body 비율·시간·저장 상수로 쓰지 않는다. 비용 모형은 `T_exec≈S(aM c_pair+c_guard+c_drift N+c_record)`, `T_verify≈S(a'M c_independent+c_guard'+c_replay N)`이며 image count/정밀도 refinement도 c에 들어간다. 실측 전 a,c와 비율은 UNKNOWN이다.

새 물리 추가 시 명세→executor→독립 verifier→fault injection→원자료 binding→승인·회귀의 양측 작업이 필요하다. 동일 코드를 복사한 두 실행은 독립 구현으로 세지 않는다. 기간/개발시간 견적은 아직 근거가 없어 미정이다. pipeline 동시 운영에서는 CPU·RAM·I/O 동시 점유와 verifier가 느릴 때 SPECULATIVE 한계 정지 비용을 계산한다. checkpoint 간격 C·최대 speculative 거리 D는 증거 등급이 아니라 운영/복원 선택이다.

## 14. Small-A envelope에 필요한 미결 값

| 범주 | 봉인할 값/정의 |
|---|---|
| 공간 | boundary 법칙, Lx/Ly/Lz·grid 정합, V, image/tie/self 계약 |
| 물질량 | N 후보 범위, 40Ar 조성, n·cluster/3-body 현실성 범위 |
| 시간 | 준비 기간, production τ/S, checkpoint·SPECULATIVE 한계, 관측 간격 |
| 준비 | 정확 q,p 및 생성 provenance, H0/P0, r separation, 현실 근거·사전 목록 |
| 온도·에너지 | T 하한/상한과 관측 정의, hard vs thermal E, U_min·δ_H 또는 운영 이탈 처리 |
| 수치 | rounding 단위, accumulator/witness 폭, dt 검증 계획, precision cap·overflow·guard |
| 관측 | equilibrium/encounter 정의, O-3 범위·오차 budget·STOP 기준, density/finite-size 검토 |
| 검증·자원 | C1-C N-1, independent dependency 목록, witness/reconstruction, CPU/RAM/GPU/I/O 제한 |

이 중 근거 없는 값을 채워 reachable 영역을 만들지 않는다. n을 정한 뒤 cubic 후보 L=(N/n)^(1/3)을 grid로 **선언해** 양자화하고 실제 n을 기록한다. 같은 n에서 늘어난 N은 correlation length·mean free path와 박스의 관계, 반복 image encounter, collective relaxation의 새 검증을 요구한다. N=64…4096은 비용 식의 예시/후속 scaling 후보 목록이며 선택 결과가 아니다.

## 15. 현실 O-3 viscosity 연결

**zero-density 연결:** 독립 검증된 고립 Ar pair 산란 `χ(E∞,b)` → 관측 층 `Q_cl^(2)(E)=2π∫[1−cos²χ(E,b)]b db` → collision integral Ω^(2,2)(T) 및 필요한 고차 Ω → Chapman–Enskog η0(T) → 모델 구축에 쓰이지 않은 실험과 비교. convention·identical-particle 취급·단위와 계수를 실행 전 봉인한다. 이 계산은 N-body production을 대신하지 않으며, zero-density η0는 N-body MD를 꼭 실행해야만 얻는 값은 아니다.

**Small-A 연결:** pair/triple encounter·평형/밀도·H/P·r_min/REFUSED·verified history가 필요하다. finite-density gas의 stress correlation(Green–Kubo 등)으로 η(n,T)를 계산하는 것은 별도 설계/관측 후보이며 η0와 자동 동일하지 않다. finite-size·time correlation·deterministic preparation 편향·통계오차·n→0 extrapolation 오차를 추가로 분리한다. 이번에는 어느 경로도 실제 계산하지 않는다.

O-3 실험 후보는 [May–Berg–Moldover 2007/NIST](https://www.nist.gov/publications/reference-viscosities-h2-ch4-ar-and-xe-low-densities)의 200–400 K 저밀도 Ar 자료다. 보고된 Ar 표준불확실도 0.084%에는 helium reference 의존성이 있다. 독립 실험 ratio, density extrapolation, 원자료, isotope composition와 calibration provenance를 실행 전에 확보·검토한다. 최신 reference correlation이나 Lang 저자 η 표를 그대로 독립 실험으로 취급하지 않는다.

| 오차 | 분리할 내용/산출 계획 |
|---|---|
| E-exp | 원 실험 표준불확실도·k·상관·He calibration·온도·density extrapolation; 임의 95%로 변환 금지 |
| E-model | PES ±σ·mass/isotope·pair-only/nonadditive·finite density/box 모델. uncertainty 함수는 universal formal bound가 아님 |
| E-QC | 같은 PES의 independent quantum vs classical collision integral/η 차이; 동일 보손 교환 대칭·양자 통계 처리. 보정은 관측 층 |
| E-CE | Sonine/CE order 수렴과 dilute Boltzmann 가정 한계 |
| E-num | χ의 dt·rounding·precision·r_min/unsupported·A-EV. replay bit equality는 이 오차를 0으로 만들지 않음 |
| E-quad | E/b grid·quadrature·low/high-E와 large-b tail·interpolation 오차; 실제 Q(E) 기반 tail |

tail q=10⁻⁴는 0.084% 표준불확실도와 비교해 수치 꼬리를 더 작게 조사하려는 **오차 배분 후보**다. 전체 성공 기준이 아니다. correlated 항을 무조건 RSS로 합하지 않고 systematic bound와 stochastic uncertainty를 구분한다. unsupported E/b나 r_min 아래 요구를 기존 동결 계약 밖에서 조용히 외삽하지 않는다. quantum reference와 Lang 자료는 O-1/O-2/E-QC 자산이며 O-3 independent 실험 자체가 아니다.

## 16. 계산량/메모리 scaling 예상

**조건부 산술, benchmark 아님:** finite primary-pair M=N(N−1)/2, S steps, 같은 raw96 state 후보(6×12=72 B/atom). reference no-cache는 보통 2M half-kick pair evaluation/step. fast는 같은 endpoint J 재사용을 X3로 확인하면 초기 endpoint 뒤 약 M/step로 줄일 후보다. full image는 pair마다 lattice evaluation/refinement 비용을 더한다. N 2배에서 M은 약4배이고, τ 고정에서 dt 절반은 S 약2배다. 한 pair cost의 E/geometry/정밀도 의존은 미측정이다.

| N 예시 | M | raw q,p state B | pair J 1 endpoint B(36M) | net atom 2 half-kick B/step(72N) |
|---:|---:|---:|---:|---:|
| 64 | 2,016 | 4,608 | 72,576 | 4,608 |
| 128 | 8,128 | 9,216 | 292,608 | 9,216 |
| 256 | 32,640 | 18,432 | 1,175,040 | 18,432 |
| 512 | 130,816 | 36,864 | 4,709,376 | 36,864 |
| 1024 | 523,776 | 73,728 | 18,855,936 | 73,728 |
| 2048 | 2,096,128 | 147,456 | 75,460,608 | 147,456 |
| 4096 | 8,386,560 | 294,912 | 301,916,160 | 294,912 |

pair J는 3개 raw96 성분이라는 조건의 logical payload다. net 값은 wide일 수 있으므로 72N은 **96 bit에 들어가는 경우의 조건부 값**이며 상한이 아니다. 보수적인 109 bit를 성분당 14 B로 pack하는 N=4096 예시는 2×3×14×4096=344,064 B/step이다. 최종 p가 96 bit여도 Δp는 차이로서 97 bit를 요구할 수 있다. Python integer/object/header/compression overhead, interval precision, image counters, failure/event/causal records, temporary buffers는 모두 별도다.

`B_witness≈S×(pair/net payload)+headers+events`; checkpoint `≈ceil(S/C)×[72N+image counters+metadata]`. pair endpoint를 무손실 재사용하는 기록이면 36M(S+1), 단순히 두 half를 각각 쓰면 72MS다. net도 endpoint 공유 후보가 가능하지만 reconstruction 계약을 먼저 확인한다. 모든 q,p를 매 step 추가 보관하면 72NS가 더 든다.

S=10⁶을 **저장 식만의 예시**로 두면 N=256의 one-endpoint pair J는 약 1.175 TB, N=4096은 약 301.916 TB(decimal, header 제외)다. N=4096 net96 two-half는 약 294.912 GB, wide14B 후보는 344.064 GB다. 실행 기간/step 수의 추천이 아니다. 두 원자 22.220 B/step에서 lossless 압축률을 가져오지 않는다.

force pair matrix 전체를 상주시킬 필요는 없다. tile 폭 B로 state/accumulator O(N)+temporary O(B²)에 stream하는 후보다. all-pair neighbor list는 O(M)이고 작은 반경 list만 쓰면 먼 force의 다른 경로가 필요하다. GPU 1 endpoint 301.9 MB라는 조건부 payload에서 40 GB 필수를 도출할 수 없다. 고정밀 interval limbs·refinement 수·parallel worker·double buffering·verifier 동시 실행·disk backlog가 미산정이므로 128 GB면 충분하다고 단언하지도 않는다.

## 17. 위험과 숨은 비용

| 위험 | 공개할 비용/대응 의무 |
|---|---|
| pairwise rounding | 다수 tiny J 소실과 T 방식 차이; discretization/model error와 별도 집계 |
| periodic 법칙 | infinite image enclosure, half-box tie, guard image 탐색, box 의존, self energy |
| 새 energy 영역 | binary 고E뿐 아니라 동시 force/Hessian·저E bound/cluster; dt/precision refinement |
| 물리 미정의 | r_min 아래 거부 빈도·원인 보존; 전체 Ar를 재현했다고 주장하지 않음 |
| NVE 표기 | discrete H exact 보존 아님; 측정된 진동을 bounded proof로 승격하지 않음 |
| 희귀 경로 | τ,N,V 확대마다 누적 재평가; 장기 hash/cache 영향 범위도 확대 |
| verifier | 새 법칙 이중 구현·fault coverage·library 신뢰 기반·pipeline 정지 |
| 데이터 | 원본 witness 저장/I/O/재검증 대역폭, 실패·DISCARDED·snapshot 비용 |
| 적용 범위 | initial T를 running T 상한으로, finite-N을 Maxwell thermal 세계로 오인 |

**필수 운영 통계 후보:** collision energy distribution과 maximum encountered E_rel(E∞ 추정/순간 K_rel/E_pair 구분), r_min guard activations, REFUSED/STOP counts와 원인, required precision distribution, H drift/oscillation, total momentum exact raw, pair/triple/multibody encounter statistics, executor/replay CPU/wall·backpressure, state/witness/checkpoint/event storage growth, CPU/GPU utilization. 각 값의 채취 간격·미채취 구간·all-step 검사인지 sample인지·동시 정지 원인의 집계 규칙을 봉인한다.

관측 통계는 q,p를 바꾸지 않는다. maximum sampled를 전 step 최대값으로 부르지 않는다. all-pair all-step energy 측정은 O(SM)의 추가 PES 비용이 있으므로 force 평가에서의 정확한 재사용/별도 관측 계산과 완전성을 설계한다. 근접 사건의 distance/time 기준은 label이지 force cutoff가 아니다. net witness에서 필요한 pair 통계를 재구성하는 계산비도 포함한다.

## 18. 더 싼 대안

| 안 | 절약 | 한계/유지할 조건 |
|---|---|---|
| 작은 N·짧은 τ·좁은 T 범위부터 | executor/verifier/storage 감소 | bulk 물성·장기 희귀 현상의 주장 범위도 축소 |
| pair/triple 계약의 유한 작은 pilot 선행 | gas 전에 rounding/guard/경계 반례 검사 | 다원자 기체 현실성 증명 아님 |
| net witness+full 독립 replay | disk O(N²)→O(N) 후보 | pair-round aggregate 독립 재계산·정확한 역사 보존 필요 |
| CPU 먼저·GPU 나중 | native/GPU 이중 개발 연기 | reference 가능 규모를 넘는 속도 약속 없음 |
| isolated collision→CE로 먼저 η0 연결 | N-body 장시간 stress sampling 연기 | Small-A 성립 증거 아님; O3 error 계약 필요 |
| full-image가 어려우면 finite cloud 계약 pilot | lattice/tie 문제 분리 | homogeneous 장기 gas/PBC 물성에는 사용 못 함 |

cutoff·thermostat·큰 dt·sample을 전 replay라고 부르는 방법은 승인된 비용 절약 대안이 아니다. 새 근사를 원하면 설계자의 명시적 판정과 독립 오차 계약이 필요하다.

## 19. 설계자 결정이 필요한 항목

모든 항목 **PENDING / 결정자=설계자**. 구체적인 선택지와 결정 후 의무를 제시한다.

| 항목 | 권고 후보 | 대안과 결정 후 의무 |
|---|---|---|
| D1 목적/ensemble | Ar40 3D dilute, driving/production thermostat 없음, closed NVE | 다른 준비/경계면 외부 법칙·교환·provenance 계약 |
| D2 온도 | 첫 200–300 K 비교, T_max300 K 후보 | 200은 highE 부담 작음/저T 검토, 400은 영역/비용 증가. 전체 ≤를 지원 범위로 부르지 않음 |
| D3 O3 tail budget | actual Ω tail10⁻⁴ 조사 후보, proxy 시작33.45De | 10⁻⁶ proxy44.88De. actual Q로 확정, world hardE 별도 |
| D4 rounding 단위 | pair once-round+wide exact aggregate P | atom total once-round T/coupled 방식은 P 보존·label 대칭의 새 설계 |
| D5 PBC 법칙 | periodic을 원하면 full-image pair-sum once-round 의미 조사 | minimum-image 별도 모델/tie·finite cloud. evaluator 비용·현실 근사 판정 전 고정하지 않음 |
| D6 reality/density | pairwise 적용 n/τ를 오차 budget으로 제한 | 3body 조사 필요 조건·누적 상한 미정. 구체 n은 아직 선택하지 않음 |
| D7 hard envelope/dt | H0/P0/Umin/δH와 동시 force 정의→KDK convergence | dt40 자동 유지 없음, 새 integrator 동시 도입 없음. range guard 처리도 판정 |
| D8 N/box/time/initial | 위 결정 후 후보를 만들고 작은 pilot 봉인 | N64…4096은 후보 목록. 준비 편향·finite-size·재방문 검사 |
| D9 C1-C N-1 | finite pilot 전 step 독립 replay 권고 후보 | sampled는 기존 grade, CERTIFIED 대체는 scope 증명. 자동 영구 규칙화 없음 |
| D10 recording/resource | net/lossless 역사 후보, checkpoint/backpressure 명시 | pair raw 보관 비교,128/256GB·16/64core·singleGPU는 비용 후 판정 |
| D11 현실 비교 | original 저밀도 실험+6종 error 사전 봉인 | quantum/model 표는 보조, Green–Kubo는 별도 관측 design |

## 20. 권고 작업 순서

1. 이번 설계자 결정: 먼저 D1–D6/D9 방향과 경계·rounding 미결을 판정한다. 미결 숫자는 남겨 둔다.
2. 선택한 boundary/rounding의 계약안·반례·reference/verifier 독립 명세를 만든다. image/tie/overflow/guard/fingerprint를 고정 전 review한다.
3. T·tail·density·초기 총energy·시간에서 hard/관측 envelope와 오차 배분을 만든다. 닫히지 않은 상한을 thermal coverage로 대체하지 않는다.
4. 기존 C1-B1 잔여 Gate/STOP을 해결하거나 설계자가 선언한 이행 조건으로 처리한다. 이 proposal에서 C1-C 시작을 추정하지 않는다.
5. 명시적 구현 승인 후 작은 pair/triple reference와 independent verifier를 별도 경로로 구현한다. dt는 새 계약의 수렴 검증 후 결정한다.
6. 작은 유한 pilot에서 exact 역사·fault injection·P/H·전 step replay·storage/비용을 검증한다. 적용 범위를 정한 뒤 CPUfast/nativeJ/GPU 순서를 비용으로 선택한다.
7. 승인된 scaling study로 N/box/τ/16vs64core/GPU를 선택한다. 현실 O3는 원자료·기준·6종 오차·density/finite-size를 먼저 봉인한 뒤 계산한다.

### 작업·읽기·검사 기록

시작 HEAD=origin/master=`985c6e29574bc70060a0400ee3dc64995f7e8d79`, master, clean, ahead/behind0/0. remote fetch로 확인했다. 종료 Git/검사 결과는 아래 완료 기록에 추가한다. commit/push는 이번에 하지 않는다.

AGENTS/RULES/헌법, X1–X5, 세 층 분리, L 원칙, reachable 감사, O3 survey, proposal README는 전문을 읽었다. CURRENT_STATE/REPO_MAP은 현재 Gate 관련 범위, 109KB C1-B1 설계는 contract·D_valid·23–26절 등 관련 부분, 상위 계산 proposal은 해당 구조와 우선32절을 읽었다. 이 큰 문서들의 전체 정밀 검토는 이번에 하지 않았다. code는 two_atom의 contract/초기 energy/impulse/kick/drift와 Lang 매개변수/retardation을 제한 참조했다. runs 전체를 검색하지 않았다.

외부 일차 자료는 Lang 공개 본문 관련 절, NIST2007/2013 공개 요약·2022 상수 표, GROMACS 장거리 공식 설명을 참조했다. 2007 실험 원자료 전문/2013 수치 표·density별 오차는 미확보이며 현실 허용 density를 확정하지 않았다.

독립 agent는 저자의 안과 별도로 대수식·contract를 검토하고 rounding/P, PBC/tie, finite-N energy, 누적 trajectory, witness/grade 문제를 지적했다. 초안 전문의 2차 검토에서도 accumulator 지원 범위, N=4 동시 encounter pilot, quantum exchange 표현을 지적해 반영했다. simulation이나 독립 code 검증을 수행한 review는 아니다. 절차 보조에 scientific-brainstorming skill을 사용했고 [Kassis, Agarwal, He, Patel & Brueckner (2026), Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065)를 기록한다(최신 공개 record v2 확인, 물리 근거 아님).

이번 새 계산은 위 tail 식 역산과 payload 식 산술뿐이다. 재현 수치는 Git 밖 `runs/c1c_foundation_design_20261001_v0/design_arithmetic.json`. 실제 η, N-body trajectory, benchmark, guard 빈도, replay 비용은 측정하지 않았다. 기존 code/fixture/contract 변경 없고 LOCAL FULL은 document-only로 실행하지 않는다.

**완료 검사:** C1-A freeze와 기존 C1-B1 inner validation 관련 시험을 새로 실행해 **10 passed / 실패·error·skip 0 / 19.96초 / exit 0**. LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 신규 설계 문서와 안내 링크만 변경하고 기존 실행 코드·공용 로직·동결 계약·fixture를 수정하지 않았다. 이 시험은 Small-A 검증이 아니다. 로그·JUnit·exit는 Git 밖 `runs/c1c_foundation_design_20261001_v0/related.*`에 보존했다.

변경 문서 3개의 local links **139개 존재 확인**, 요청된 1–20절 순서 확인, 변경 범위 검사, `git diff --check` 통과. 최초 link check는 기존 URL-encoded 경로 9개를 decode하지 않아 잘못된 누락을 보고했고 검사기에서 percent decoding을 적용해 해결했다. 첫 검사 기록도 `document_check.json`, 수정 검사 `document_check_v2.json`으로 보존했다. Git LF→CRLF 안내는 있었으며 이를 물리/시험 경고 해결로 해석하지 않는다.

종료 HEAD=시작 HEAD=origin/master=`985c6e29574bc70060a0400ee3dc64995f7e8d79`, master, ahead/behind0/0. 종료 dirty: 수정2개+신규1개, 모두 문서. 변경 파일은 이 proposal, `docs/proposals/README.md`, `docs/DOCUMENT_STATUS_INDEX.md`. commit 없음 / push 없음. 기존 CURRENT_STATE와 C1-B1 상태·실행 코드·fixture는 변경하지 않았다.

**DESIGN READY FOR DESIGNER DECISIONS**
