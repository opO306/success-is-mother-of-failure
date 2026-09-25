# Ar–Ar 현실 퍼텐셜 비교 조사 v1 — C1 첫 현실 검증 종

**상태:** 조사 초안 (2026-09-25). **결정 없음.** 설계자 판정 대기.
**상위:** `A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md` 11.4 (6판: C1 = 첫 실제 물질, Ar = 첫 현실 검증 종, 표현 방식 미정, 3체 항 조사).
**원칙:** 자료가 요구하는 표현을 먼저 보고 VM 연산이 따라간다. 구현 편의로 고르지 않는다.

**읽은 범위 (공개):** 아래 문헌은 전부 **초록·요약·검색 결과**로만 확인했다. 식의 정확한 형태, 매개변수 표, 맞춤에 쓴 거리 범위는 **원문을
읽어야** 확정된다 — 이 문서는 "무엇을 읽고 비교해야 하는가"를 좁히는 1차 조사다.

---

## 1. 후보 — 쌍(2체) 퍼텐셜

| 후보 | 표현 | 이론 수준 / 출처 | 검증 (초록 기준) | 비고 |
|---|---|---|---|---|
| **Aziz 1993 (HFDID1)** | **해석적**: Hartree–Fock형 반발 + 항마다 따로 감쇠한 분산 급수 | 실험 맞춤 — Ar₂ 자외선 진동-회전 스펙트럼(Herman·LaRocque·Stoicheff)을 실험 오차 안에서 재현 | 여러 물성 예측, 당시 "가장 정확한 Ar 상호작용" | 실험 기반 기준선. 30년 전 |
| **Tang–Toennies 2003** | **해석적**: Born–Mayer 두 매개변수 + 감쇠된 분산 3항(C₆, C₈, C₁₀), 결합 규칙 | 모형 + 문헌 계수 | 희가스 21쌍 전부(He~Rn, 이종 포함) 한 틀로 | **모든 희가스로 일반화**되는 유일한 후보(He, Ne, Ar … 확장 계획과 맞음). 최신 양자 계산보다 덜 정확할 것 — 차이 크기 미확인 |
| **Jäger·Hellmann·Bich·Vogel 2009/2010** | 양자 계산 점 + 해석적 맞춤(형태 미확인) | CCSDT(Q)까지, 큰 기저, **상대론 보정** | 진동-회전 스펙트럼; 2부에서 2차 비리얼·음향·유전 비리얼·점성·열전도(83~10,000 K) — "표준값으로 쓸 만큼 정확" | 저밀도 기체 열물성의 사실상 기준 |
| **Patkowski–Szalewicz 2010** | 양자 계산 점 + 해석적 맞춤 | 기저·들뜸 **한계까지 수렴한 BO 에너지** — 비상대론 계산 중 가장 정확 | 비리얼 계수 등에 쓰임 | 순수 BO(상대론·QED 미포함) |
| **개선판 2023 (arXiv 2304.14719)** | 위 BO 퍼텐셜 + 보정(형태 미확인) | 2전자 Darwin·궤도-궤도 상대론, 장거리 지연, 선도 QED 보정 | 이량체 스펙트럼(진동 준위·결합 해리 에너지·회전 상수), 압력·음향 비리얼, 점성·열전도 | 가장 최신·가장 많은 보정. 초록: 열물성은 최신 실험보다 약간 덜 정확, 수송은 측정보다 불확도가 작음 |
| (참고) **Born–Mayer 단일 지수** | `A·e^{−r/ρ}` | — | Ar₂ 반발 벽 **과대평가** 보고(Van Vleet 2016) | 6판에서 기본 방향 철회. 비교군 |
| (참고) **표 PES + 보간** | 양자 계산 점을 그대로 | 위 계산들의 원자료 | — | 해석적 맞춤이 있으면 굳이 필요 없음. 원자료 공개 여부 미확인 |

**잘 알려진 값(대략, 원문 확인 필요):** 우물 깊이 ε/k ≈ 143 K(≈ 12 meV), 최소 위치 r ≈ 3.76 Å — Aziz 계열 값.

---

## 2. 3체 항 — 언제 필요한가

- **Cencek·Szalewicz·Garberoglio·Harvey·McLinden 2013:** 300개 배치에서 CCSDT(Q) + 핵심 상관·상대론 효과로 3체 비가산 에너지를 계산하고
  기하마다 불확도 추정, 해석적 함수로 맞춤 — "현재 가장 정확한 Ar 3체 퍼텐셜". 3차 비리얼 계수(80~10,000 K, 양자 효과 포함 경로적분)로 검증.
- **크기(검색 결과, 원문 확인 필요):** 고체 Ar 응집 에너지의 **최대 약 9%**가 3체(Axilrod–Teller–Muto 삼중 쌍극자), 액체 Ar에서 압력·내부
  에너지가 **약 10%** 달라짐.
- **판단 기준(구현자 정리):**
  - **희박 기체**(2차 비리얼, 점성, 열전도, 두 원자 충돌): **쌍 퍼텐셜만으로** 검증 가능.
  - **액체·고체**(밀도, 응집 에너지, 체적 탄성률, 상전이): 쌍만 쓰면 **약 10% 수준 차이가 예상**됨 → 3체를 넣거나, 그 차이를 **선언된 한계**로
    두고 비교해야 한다. "쌍만으로 고체 Ar이 맞다"는 주장은 금지.

---

## 3. 거리·에너지 범위와 A의 다른 계약

| 영역 | 거리(대략) | 무엇이 맞나 |
|---|---|---|
| 상온 기체·액체의 충돌 | 약 3 Å 이상 | 위 쌍 퍼텐셜들의 주된 검증 범위 |
| 강한 충돌 | 약 2~3 Å | 양자 계산 점이 있는 범위 안인지 원문 확인 필요 |
| 고에너지(≫ 10 eV) | 약 1 Å 이하 | Nordlund·Lehtola·Hobler 2025 / ZBL 영역 → 지금은 `physics_domain_exceeded` |

**A가 새로 떠안는 것 (공개):**
- **양자 효과.** 문헌의 비리얼 계수는 경로적분(양자) 계산으로 비교한다. A는 **고전 역학**이다 → 낮은 온도(수십 K)에서는 고전 A가 실제 Ar과
  다를 수 있다. 비교할 때 "고전 근사의 차이"를 따로 적어야 한다. C1 물성 비교 온도 범위를 정할 때 필요.
- **VM 연산.** 해석적 후보들(Aziz, Tang–Toennies, 양자 계산 맞춤)은 대개 지수·다항/역거듭제곱·감쇠 함수의 조합이고, 이는 VM 0.2의
  EXP·MUL·DIV·SUM으로 **표현 가능할 것으로 보인다**(원문 식 확인 전 추정). 표 보간은 새 연산이 필요. **이것은 선택 근거가 아니라 결과로만 기록한다.**
- **단위계.** A-MICRO가 쓸 단위(Å, K 또는 meV, 원자질량 단위 …)가 정해지지 않았다. 매개변수를 옮기기 전에 정해야 한다.

---

## 4. 다음 — 원문을 읽고 비교표를 채운다 (설계자 확인 후)

원문에서 옮길 것(후보마다): **식 전체와 매개변수 표 · 맞춤에 쓴 거리 범위(최소 거리 포함) · 불확도 · 검증한 물성과 온도 범위 · 데이터 공개 여부 ·
라이선스.**

우선 읽을 원문(구현자 제안): **Jäger 외 2009(1부)**, **개선판 2023**, **Aziz 1993**, **Tang–Toennies 2003**, **Cencek 외 2013**(3체).

**설계자에게 묻는 것:**
1. 비교 기준의 우선순위 — (a) 가장 정확한 현재 양자 계산(개선판 2023 등) / (b) 실험 스펙트럼 맞춤(Aziz) / (c) 희가스 전체로 일반화되는 틀(Tang–Toennies).
   세 가지가 서로 다른 목적을 가진다.
2. C1에서 처음 검증할 물성 범위 — 희박 기체만(쌍으로 충분) / 액체·고체까지(3체 필요 또는 차이 선언).
3. 원문 확보 방법 — 대부분 유료 학술지다. arXiv·저자 공개본으로 되는 것부터 읽을지.

---

## 출처

- R. A. Aziz, A highly accurate interatomic potential for argon, J. Chem. Phys. 99, 4518 (1993) — [AIP](https://pubs.aip.org/aip/jcp/article-abstract/99/6/4518/93952/A-highly-accurate-interatomic-potential-for-argon?redirectedFrom=fulltext)
- K. T. Tang, J. P. Toennies, The van der Waals potentials between all the rare gas atoms from He to Rn, J. Chem. Phys. 118, 4976 (2003) — [AIP](https://pubs.aip.org/aip/jcp/article-abstract/118/11/4976/535963/The-van-der-Waals-potentials-between-all-the-rare?redirectedFrom=fulltext)
- B. Jäger, R. Hellmann, E. Bich, E. Vogel, Ab initio pair potential energy curve for the argon atom pair … I, Mol. Phys. 107 (2009) — [T&F](https://www.tandfonline.com/doi/abs/10.1080/00268970903213305); II (2010) — [T&F](https://www.tandfonline.com/doi/abs/10.1080/00268976.2010.507557)
- K. Patkowski, K. Szalewicz, Argon pair potential at basis set and excitation limits, J. Chem. Phys. 133, 094304 (2010) — [AIP](https://pubs.aip.org/aip/jcp/article/133/9/094304/189065/Argon-pair-potential-at-basis-set-and-excitation)
- Thermophysical properties of argon gas from improved two-body interaction potential (2023) — [arXiv:2304.14719](https://arxiv.org/abs/2304.14719)
- W. Cencek et al., Three-body nonadditive potential for argon with estimated uncertainties and third virial coefficient, J. Phys. Chem. A 117, 7542 (2013) — [ACS](https://pubs.acs.org/doi/10.1021/jp4018579), [NIST](https://www.nist.gov/publications/three-body-nonadditive-potential-argon-estimated-uncertainties-and-third-virial)
- Three-body contribution to binding energy of solid argon, Phys. Rev. Lett. 79, 1301 (1997) — [APS](https://link.aps.org/doi/10.1103/PhysRevLett.79.1301)
- Pair-HNC closure for three-body potentials: argon with the Axilrod–Teller potential, Phys. Rev. A 45, 3659 — [APS](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.45.3659)
- M. J. Van Vleet et al., Beyond Born–Mayer (2016) — [ACS](https://pubs.acs.org/doi/10.1021/acs.jctc.6b00209)
- K. Nordlund, S. Lehtola, G. Hobler, Repulsive interatomic potentials calculated at three levels of theory (2025) — [Zenodo](https://zenodo.org/records/22092149)
