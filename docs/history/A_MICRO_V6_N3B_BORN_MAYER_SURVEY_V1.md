# N3-B 조사 v1 — Born–Mayer 매개변수는 어디서 오는가

**문서 분류: 역사 / 과거 설계·실측 기록.** 본문의 “현재”, “다음”, 시험 개수와 후보는 기록 당시의 상태다. 현재 작업 지시나 새 동결 판정으로 읽지 않는다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


**상태:** 조사 v1 (2026-09-25) → **설계자 6판 판정으로 종결**(C0 수치 계획 11.4): Born–Mayer 방향 철회, C0는 합성 퍼텐셜로 역학 검증,
C1에서 Ar을 첫 현실 검증 종으로. 다음 조사: [A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md](A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md).
**상위:** [A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md](A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md) 11.3(N3-A 방향 승인, N3-B 미정).
**한 줄 결론:** Born–Mayer의 `A`, `ρ`는 **특정한 실제 원자·이온 쌍**에 대해, **특정한 거리 범위**에서 맞춘 값으로만 존재한다.
그래서 **C0 입자가 현실의 무엇인지 먼저 정해야** 값을 고를 수 있다 — 설계자가 예상한 그 결론이다.

---

## 0. 현재 C0 입자의 정체 (문서 확인)

- [A_MICRO_V6_PARTICLE_DESIGN_V1.md](A_MICRO_V6_PARTICLE_DESIGN_V1.md) 2절: 점입자, `species → 명세의 상호작용 매개변수(이름이 아니라 값)`. 3절: "지금 v6의 첫 세계들은
  **추상 매개변수 = 시험 세계**". 실제 원자 값으로 맞추면 근거 등급이 "실험 보정"으로 올라간다고만 적혀 있다.
- [A_MICRO_V6_PHYSICS_CLOSURE_V1.md](../reference/A_MICRO_V6_PHYSICS_CLOSURE_V1.md) 1.2: 전하·정전기는 **C0·C1에서 열지 않음**(C2-Q).
- → **C0 입자는 현실의 무엇도 아직 대표하지 않는다.**

---

## 1. 자료 조사 — 설계자 질문 9개에 대한 답

| | Born & Mayer 1932 / Huggins–Mayer 1933, Tosi & Fumi 1964 | Abrahamson 1969 | 비활성 기체 exp-6 (Buckingham 계열) | ZBL 1985 / Nordlund·Lehtola·Hobler 2025 |
|---|---|---|---|---|
| **어떤 쌍** | **이온** 결정(NaCl형 알칼리 할로젠화물) | **중성 바닥 상태 원자** 동종 쌍 104개(Z=2~105), 이종은 결합 규칙 `U₁₂ ≈ √(U₁₁U₂₂)` | 비활성 기체 원자(예: Ar) | 모든 원자 쌍(ZBL: 보편 함수, Nordlund 2025: Z₁,Z₂ ≤ 92 쌍별) |
| **식** | `b·exp((rᵢ+rⱼ−r)/ρ)` + 쿨롱 + 분산. Tosi–Fumi는 경도 ρ를 염마다 다르게 | `U(R) = A·exp(−bR)` | `A·exp(−r/ρ) − C/r⁶` (반발·인력 **함께** 맞춤) | 가려진 쿨롱 `Z₁Z₂e²/r · Σaᵢe^{−bᵢr/a}` |
| **매개변수 출처** | **실험 맞춤**: 격자 상수·압축률 등 결정 자료 | **이론**: 토마스–페르미–디랙(TFD) 통계 모형 계산을 지수로 맞춤(맞춤 오차 ≤ 6%) | 실험(기체 확산·상태 방정식)·양자 계산, 매개변수 세트가 여러 개이고 서로 꽤 다름 | ZBL: 여러 쌍의 이론 퍼텐셜에 보편 함수를 맞춤(2 eV 이상에서 표준편차 18%). 2025: MP2·DFT로 쌍별 계산, 데이터 CC-BY 공개 |
| **유효 거리** | 결정 평형 근처(이온 간 거리) | **R ≈ 1.5 a₀ ~ 3.5 a₀ (≈ 0.8 ~ 1.9 Å)**, 실효 상한 6~8 a₀ 추정 | 평형 거리 근처(Ar은 약 3.8 Å) | 에너지 ≫ 10 eV인 아주 가까운 거리(이온 주입·스퍼터링) |
| **짧은 거리에서 왜 깨지나** | 이온 모형·겹침 근사의 한계 | TFD가 바깥 전자껍질을 거칠게 다룸, 핵 반발 영역에선 ZBL류로 | 단일 지수는 넓은 범위에서 부정확 — Ar 이량체에서 반발 벽을 **과대평가**한다는 비교(Van Vleet 외 2016) | (이것이 가장 짧은 거리의 기준) |
| **차단 근거** | 쿨롱이 장거리라 차단보다 에발트 합 | 지수라 빨리 작아짐, 상한 밖은 맞춤 범위 밖 | r⁻⁶ 꼬리가 차단 문제의 본체 | 해당 없음 |
| **다른 물질에 옮기기** | **안 됨** — 염마다 다른 값 | 결합 규칙으로 이종 쌍 **근사** 가능, 정확도는 동종 맞춤보다 낮음 | 안 됨 — 원소별 | ZBL은 보편(대신 거침), 2025 자료는 쌍별 |

**직접 읽지 못한 것 (공개):** Born–Mayer 1932, Tosi–Fumi 1964, Gilbert 1970(Z=2~36), Van Vleet 2016은 **초록·요약만** 봤다. 표에
**구체적인 A·ρ 숫자를 적지 않은 이유**다. 숫자는 원문 표에서 옮겨야 하고, 그 전에 아래 2절 결정이 먼저다.

---

## 2. 발견 — 왜 지금 A·ρ를 고를 수 없는가

1. **보편적인 A·ρ는 없다.** 모든 자료가 "이 원자(이온) 쌍에 대한 값"이다. 쌍을 정하지 않으면 숫자를 고를 수 없다.
2. **거리·에너지 영역이 자료마다 다르다.**
   - Abrahamson(중성 원자)은 0.8~1.9 Å — 두 원자가 **수십~수백 eV**로 부딪혀야 도달하는 거리다. 상온 물질의 원자는 대략 3~4 Å에서 서로를
     밀어낸다. 즉 이 자료는 **고에너지 충돌용**이고 상온 C0 세계의 "접촉 반발"을 맞춘 값이 아니다.
   - 상온 접촉 거리의 반발(비활성 기체 등)은 **인력(r⁻⁶)과 함께** 맞춘 값뿐이다. 두 항이 서로 보정하며 맞춰졌으므로 **지수 항만 떼어 C0로
     쓰면 검증된 물리 모델이 아니다.**
   - 이온 결정 값(Tosi–Fumi)은 **쿨롱과 함께** 맞춘 것 — C0·C1은 전하를 열지 않으므로(Z1) 쓸 수 없다.
3. **C0(반발만) / C1(인력)의 나눔은 구현 순서이지 물리의 나눔이 아니다.** 현실 자료는 둘을 한 식으로 맞춘다. 이것은 폐쇄 문서의 C0·C1
   경계를 다시 봐야 한다는 신호다 — 결정은 설계자 몫.
4. **N3-A 자체도 재검토 여지:** 단일 지수가 "넓은 거리 범위에서 부정확"하고 Ar 이량체의 반발 벽을 과대평가한다는 보고가 있다(Van Vleet 2016).
   C0 입자가 비활성 기체 원자라면, 가장 좋은 선택은 Born–Mayer보다 **양자 계산으로 정한 이량체 퍼텐셜**일 수 있다.

---

## 3. 그래서 먼저 정해야 할 것 — C0 요소의 물리적 정체 (설계자 결정)

| 선택 | 뜻 | 매개변수 출처 | 대가 |
|---|---|---|---|
| **I1 특정 중성 닫힌껍질 원자** (예: 아르곤) | "C0 입자 1개 = Ar 원자 1개" | 비활성 기체 이량체 퍼텐셜(양자 계산 + 실험, 가장 잘 알려진 계 중 하나) | 반발만으로는 검증된 모델이 아님 → C0와 C1(분산 인력)을 같은 자료에서 함께 가져와야 함. 화학이 없음(비활성) |
| **I2 이온** (예: Na⁺, Cl⁻) | 알칼리 할로젠화물 | Tosi–Fumi 등 실험 맞춤 | **전하 필요 → C2-Q를 먼저 열어야 함**(Z1과 충돌) |
| **I3 추상 시험 종** | 현실을 대표하지 않음 | 없음 — 선언된 가짜 값 | 정직하지만 "현실 근거" 없음. 지금 문서의 상태 그대로. 수치 틀·E4/E8 시험에는 충분 |
| **I4 축약 덩어리(parcel)** | 원자 여러 개를 대표(9절 원칙) | 유효 퍼텐셜은 보통 **부드럽고 상태(온도·밀도)에 의존** — Born–Mayer가 아님 | N3-A의 근거(전자 밀도 겹침)는 원자에 대한 것이라 덩어리엔 그대로 안 맞음 |

**구현자 권고 (결정 아님):**
- 현실 근거를 원하면 **I1, 첫 종은 아르곤**. 이유: 전하·화학 없이 순수 역학(C0)과 응집(C1)을 현실 자료로 검증할 수 있는 가장 단순한 원소이고,
  이량체 퍼텐셜이 양자 계산과 실험 양쪽으로 잘 확립되어 있다. 대신 **C0 = "Ar의 반발 부분"만**이 아니라, C0를 "Ar–Ar 퍼텐셜 전체를 쓰되
  C0 시험은 반발 영역에서만 한다"처럼 다시 정의해야 할 수 있다.
- 그 전까지 **E4·E8·N9 같은 수치 시험은 I3(선언된 가짜 매개변수)로 진행 가능** — 11.3의 "dummy 허용, C0 물리라 부르지 않음"과 같다.
- `r_min`(물리 범위 밖 중단): I1이면 반발 벽 자료의 최소 거리(이량체 계산 범위)에서 오고, 그보다 가까우면 ZBL/Nordlund 2025 영역 → 지금은
  `physics_domain_exceeded`로 멈춤. 상온 세계에선 거의 도달하지 않는다(수십 eV 필요).

**설계자에게 묻는 것:**
1. C0 입자의 정체: I1 / I2 / I3 / I4 중 무엇? (I1이면 어느 원소)
2. I1이면 C0·C1 경계를 "반발만 / 인력 추가"에서 "같은 퍼텐셜의 영역별 검증"으로 바꿀지.
3. ~~I1에서 N3-A(Born–Mayer 모양)를 유지할지, 그 원소의 가장 좋은 이량체 퍼텐셜(양자 계산 표)로 바꿀지 — 후자면 VM에 표 보간 연산이 필요~~
   **→ 설계자 정정: 거짓 양자택일이었다.** 고정밀 퍼텐셜이 곧 표는 아니다 — Ar에는 지수·역거듭제곱·감쇠 함수를 조합한 **고정밀 해석적** 퍼텐셜
   (Tang–Toennies 계열 등)도 있다. 후보는 최소 셋: Born–Mayer 단일 지수 / 고정밀 해석적 PES / 표 PES + 보간. **자료가 요구하는 것을 먼저
   보고 VM 연산이 따라간다** — VM에 EXP가 있다고 지수식을 고르면 꼬리가 개를 흔드는 것.

---

## 출처

- A. A. Abrahamson, Born–Mayer-type interatomic potential for neutral ground-state atoms with Z = 2 to Z = 105, Phys. Rev. 178, 76 (1969) —
  [APS](https://link.aps.org/doi/10.1103/PhysRev.178.76), [ADS 초록](https://ui.adsabs.harvard.edu/abs/1969PhRv..178...76A/abstract)
- Born–Mayer interatomic potential for atoms with Z = 2 to Z = 36, Chem. Phys. Lett. 7, 360 (1970) — [ADS](https://ui.adsabs.harvard.edu/abs/1970CPL.....7..360G/abstract)
- M. P. Tosi, F. G. Fumi, Ionic sizes and Born repulsive parameters in the NaCl-type alkali halides II, J. Phys. Chem. Solids 25, 45 (1964) —
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/002236976490160X)
- M. J. Van Vleet et al., Beyond Born–Mayer: Improved models for short-range repulsion in ab initio force fields, JCTC (2016) —
  [ACS](https://pubs.acs.org/doi/10.1021/acs.jctc.6b00209), [arXiv](https://arxiv.org/abs/1606.00734)
- K. Nordlund, S. Lehtola, G. Hobler, Repulsive interatomic potentials calculated at three levels of theory, Phys. Rev. A 111, 032818 (2025) —
  [데이터(Zenodo, CC-BY)](https://zenodo.org/records/22092149)
- ZBL 보편 퍼텐셜의 맞춤 정확도(2 eV 이상 표준편차 18%) — [K. Nordlund 강의 자료](http://beam.helsinki.fi/~knordlun/mdh/rangetext.html)
- LAMMPS ZBL 문서(설계자 제시) — [pair_zbl](https://docs.lammps.org/pair_zbl.html)
- Buckingham 퍼텐셜 개요 — [Wikipedia](https://en.wikipedia.org/wiki/Buckingham_potential)
