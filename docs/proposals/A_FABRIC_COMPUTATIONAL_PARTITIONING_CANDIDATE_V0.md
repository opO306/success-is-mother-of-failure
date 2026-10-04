# A-Fabric 계산 분할 후보 v0 (A-Fabric Computational Partitioning Candidate)

> 상태: **DEFERRED DESIGN CANDIDATE / NOT APPROVED / NOT IMPLEMENTED**
> 작성: 2026-10-05 KST, 기준 로컬 master `bb58e98`. 설계자·sol·구현자 대화 정리. 설계자가 이 위치·형태로 기록을 승인했다(2026-10-05). 내용 승인은 아니다.
> 코드·시험·동결 계약·fixture 변경 없음.

## 0. 중심 명제

> A-Fabric은 물리계를 독립 영역으로 자르는 구조가 아니다. 계산 책임을 분산하고, 경계를 넘는 전체 영향에 대한 엄밀한 enclosure를 합성하여
> 기존 세계 계약의 authoritative canonical state가 유일하게 결정되는 동안에만 분할 계산을 유지한다. 결정되지 않으면 refinement, merge, STOP 순으로 진행한다.

**A-Fabric의 Calculator 분할은 세계의 물리적 분리를 의미하지 않는다.** 경계를 넘는 상호작용·얽힘·보존량은 Link 또는 공유 상태로 그대로 보존한다.
A-Fabric에는 물리를 결정할 권한이 없다. 이미 승인된 이산 세계 법칙을 더 싸게 계산하는 방법만 다룬다(X1).

## 1. 선행 자산 — 새 아이디어로 주장하지 않는다

A-Fabric은 아래 자산을 하나의 구조로 묶는 후보일 뿐이다.

| 내용 | 선행 자산 |
|---|---|
| 물리와 실행 기술 분리, 기준 실행기 영구 유지, 차등 검사, 정확 캐시, 다중 해상도 단계 | [A_EXECUTION_ARCHITECTURE_V1](../reference/A_EXECUTION_ARCHITECTURE_V1.md) X1〜X5 (승인) |
| 법칙 언어와 계산 방법의 분리 (대화의 "LAW IR / Execution IR") | [A_NUMERIC_EXECUTION_STACK_V1](../reference/A_NUMERIC_EXECUTION_STACK_V1.md) §7: Physics IR → Evaluation IR(반올림 지점·동점 규칙) → A-Numeric VM → 실행기 |
| 논리 계산 단위 ≠ CPU 코어, 범위가 반올림을 결정하면 확정·아니면 exact fallback | [계산·메모리·기록 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md) §4 Software Core, §6 |
| 다원자 반올림 단위 P / T / coupled, 생략 합 enclosure가 유일 반올림을 결정하면 계산 표현 | [C1-C 다원자 기체 제안](C1C_MULTIPARTICLE_GAS_FOUNDATION_V0.md) §6, D4, 144행 |
| 원자 집단의 정확 압축 (손실 없는 Morph의 한 형태) | [Exact Aggregate 제안](A_EXACT_AGGREGATE_RESEARCH_PROPOSAL_V0.md) |
| 표현 전환 fail-closed, 정밀 계산 요청(Hotline), 계속 울리면 계산법 실패 | [일반 세계 계약 V0](../active/general_world_contract_v0/V0_ORIGINAL.md) §20·§24·§25 |
| 동일 입자 대칭, 상위 유효 모델 승인 기준 사전 결정, 0-B1/0-B2 | [일반 세계 계약 V0.1](../active/GENERAL_ATOMIC_ELECTRONIC_WORLD_CONTRACT_V0_1.md) N11·N12·§36 |

## 2. 이 문서에서 새로 기록하는 것 (모두 미승인)

1. **물리적 분리 ≠ 계산적 분할.** 물리적 분리 = 결합항이 실제로 0이고 양자 상태가 곱 상태. 계산적 분할 = 결합이 남아 있고, 계산기를 나누되 Link가 결합항을 보존한다. A-Fabric의 `split`은 후자, 즉 계산 책임의 분배다.
   - 정확한 pair Link는 **병렬성만** 준다(쌍 수는 그대로). 계산량을 줄이는 후보는 먼 집단을 요약 + 증명된 범위로 다루는 **bounded Link**뿐이다.
2. **Truth ≠ Availability.** 묶는 방식((A+B)+C / A+(B+C)), Domain ID, 처리 순서는 확정된 canonical 값을 바꾸면 안 된다(Truth). 어느 방식이 더 빨리 확정되는지(Availability·비용)는 scheduler가 고를 수 있다. ID는 주소표이며 물리 입력이 아니다.
3. **RESOLVED → REFINE → MERGE → STOP.** 인증 대상은 중간 기여가 아니라 **세계 계약이 실제로 저장하는 최종 값**이다(각 기여를 따로 반올림한 결과는 합친 뒤 한 번 반올림한 결과와 다를 수 있다). 분할은 영구 독립이 아니라 step·전이 단위로 판정한다.
   - RESOLVED: 분할 구조와 Link bound를 합성해 기준 실행기와 같은 저장값이 유일하게 결정됨
   - REFINE: 아직 미결정, 더 정밀한 Link·요약으로 좁힐 수 있음
   - MERGE: 분할 표현으로는 좁히는 비용이 너무 크거나 불가
   - STOP: 합쳐도 승인된 방법으로 결정 불가 (fail-closed)
   - bound는 계속 들고 다니는 오차 빚이 아니라, 이번 전이를 더 열어볼지 판정하는 **일회성 certificate**다.
   - 1세대는 보수적 사전 인증(확정 → 실행). 추측 실행 + rollback(Time Warp 계열)은 연쇄 rollback 위험 때문에 장기 후보다.
4. **Correlation Link.** 양자 상태를 쪼개지 않고 계산 책임만 나누며 얽힘 정보는 Link로 유지하는 후보. 강하게 얽힌 상태에서는 Link 크기가 전체 결합 상태만큼 커질 수 있다.
5. **Morph 두 종류를 섞지 않는다.** Lossless Morph(언제든 정확히 되돌림)와 Effective Morph(미시 정보 일부를 버림). Effective Morph 뒤에 미시 상태를 다시 만들어내지 않는다. 원본 backing state를 유지하거나, 정확한 미시 상태로 돌아간다고 주장하지 않는다. Effective Morph는 N12 유효 모델이다.
6. **0-B2 전 명명 규칙.** 계산 이름(Domain, Calculator, Link)은 계산 층에, 관측 이름은 관측 층에 둔다. 0-B2가 닫히기 전 양자 부분에는 `History` 대신 `Evidence Node`, `Branch Candidate`, `Measurement Outcome Record`처럼 실제 세계 역사라고 주장하지 않는 이름을 쓴다. 세계 층에는 개별 입자 이름을 두지 않는다(N11, v2 particle_id 결함 선례).

## 3. 경고 자료 — 반올림 계약 P의 계산량 (ROUGH COST ESTIMATE / NOT LANG-2024-VERIFIED)

**설계 결론이 아니다.** "P 계약이면 이런 계산 폭발 가능성이 있다"는 경고 자료이며, 어떤 결정의 근거 숫자로 인용하지 않는다.

P(쌍마다 한 번 반올림)에서는 먼 쌍도 반올림 결과가 0이 아니면 세계 법칙상 계산해야 한다. 집단 하나에 대한 bound 하나로는 부족하고, 쌍마다 결과가 결정돼야 한다.

| 조건 | 값 |
|---|---|
| 충격량이 정확히 0으로 반올림되는 거리 R₀ | 약 1.1×10⁴ bohr (약 0.6 μm) |
| R₀ 안의 이웃 수, 1 atm·300 K | 원자당 약 2×10⁷ |
| 0.01 atm / 0.001 atm | 약 2×10⁵ / 약 2×10⁴ |

가정: h·6C₆/R⁷ < u_p/2, u_p = 2⁻⁸⁰(운동량 FX(96,80)), h = 20 a.u.(Δt=40의 half-kick), C₆ = 64.3 a.u.(지연 효과 없는 점근식), 이상기체 밀도.
**Lang 2024 포텐셜로 계산하지 않았다.** 지연 효과를 넣으면 R₀는 짧아진다. 크기의 자릿수만 의미가 있다.

함의(가설): T(원자별 합계를 한 번 반올림)는 먼 집단의 합을 계층 bound 하나로 결정할 수 있어 A-Fabric과 잘 맞지만 정확한 운동량 보존을 잃는다. coupled 계약은 아직 정의되지 않았다(C1-C D4: 새 계약 설계 필요, 잔차를 ID 작은 원자에 몰면 label 누출).
**따라서 다원자 반올림 계약은 마지막 몇 비트의 문제가 아니라 집단 효과, 보존, 병렬 분해, 계층 계산 가능성을 함께 정한다.** 반올림 Gate는 충실도·대칭·보존·결정성을 먼저 보고 비용은 그 다음에 본다.

## 4. 선행 Gate와 순서 (설계자 판정 2026-10-05)

A-Fabric의 의존 순서:

```
다원자 rounding contract → canonical multiparticle law → reference execution → A-Fabric feasibility
```

공식 진행 흐름은 바뀌지 않는다.

```
C1-B1 종료 → 다원자 기체 단계 → 다원자 rounding Gate → A-Fabric 첫 feasibility 측정
```

Nuclear State/Dynamics Gate V2는 병렬 연구 자산이다. 봉인된 survey의 실행·판정은 계속할 수 있지만 공식 순서를 바꾸지 않는다.

첫 feasibility 측정(구현 전): 희박 Ar에서 먼 집단을 bounded summary로 묶었을 때 최종 canonical Δp가 상세 pair 계산 없이 확정되는 비율.
첫 bound / 한 번 refine 후 / merge 필요 비율, certificate 비용 대 직접 pair 비용, N에 따른 변화를 잰다.
**확정 비율이 낮거나 certificate가 직접 계산보다 비싸면 그 방식은 탈락이다.** 희박 Ar은 짧은 거리 힘이라 쉬운 경우이므로 Coulomb 계로 일반화하지 않는다.

## 5. 미결

1. 다원자 rounding contract (P / T / coupled 또는 새 후보)
2. Law/Execution 분리를 다원자·양자에 확장할 때 Evaluation IR의 표현 범위(수치 실행 계층 §7.6: 첫 구현 후보 C1-C)
3. exact Link는 병렬성만 준다. 계산량 감소는 자동이 아니다
4. hierarchical / bounded Link가 실제 절감 후보이며 비용 미측정
5. Coulomb의 global influence: 비상대론 순간 작용이면 인과 영향 범위가 사실상 전역이라 지역성 기반 최적화를 못 쓴다. 유한 속도 전달은 EM Gate(§18)의 물리 선택이며 A-Fabric이 바꾸지 않는다
6. Correlation Link가 강한 얽힘에서 전체 상태 크기로 커질 위험
7. Effective Morph 뒤 미시 정보 재생성 금지
8. ID·순서는 Truth에 영향 금지
9. Gate 0-B2 미해결
10. 추측 실행 + rollback은 장기 후보이며 1세대가 아님

## 6. 하지 않는 것

구현, 새 물리 규칙, 기존 Gate·우선순위 변경, 3절 숫자를 결정 근거로 사용, 선행 자산의 내용을 새 발견으로 표기.
