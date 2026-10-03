# N-5 저장소 반영 변경안 v2 (수정할 문구 전체)

**상태:** 설계자 최종 판정 반영(2026-10-01). 승인된 수정과 문서 체계를 저장소에 일괄 반영한다. 코드 변경·commit·push 없음.
**기준 커밋:** 원격 `master` `ac143855bec21352aaa86241b31baf86d6075eae` (v1은 `5c5d6f8` 기준이었다. 그 사이 커밋은 `ac14385` 사후 검증 조사 문서 하나이며, 아래 반영 위치와 겹치지 않는다)
**작성일:** 2026-10-01
**함께 반영하는 초안:** `PROJECT_CONSTITUTION_AMENDMENT_L_ORIGIN_V1.md`, `L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`, (저장소 편입) `C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md`
**반영 순서:** ⓪ 헌법 개정 → ① 세 층 분리 승인 문서 → ② L 원칙 문서 → ③ O-3 조사 문서 편입 → ④ `RULES.md` → ⑤ `CURRENT_STATE.md` → ⑥ `AGENTS.md` → ⑦ 색인 → ⑧ 레거시 계획 표기
**검증(반영할 때):** 문서만 변경 → `LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 문서만 변경, 코드·동결 계약·fixture 변경 없음`. 헌법 원문을 읽는 시험은 `tests/test_body_contract_freeze.py`(제26조)뿐이므로 그 파일을 실행한다. 제26조는 바꾸지 않는다.

**v1 → v2 변경:**
- 기준 커밋 `ac14385`.
- **N-4 확정:** C1-B1 O-3 = Ar-Ar 직접 산란, `O-3 weak`. 착수 전 봉인 항목 명시. 희박 Ar 점성은 다원자 기체 단계의 강한 O-3로 이동.
- **N-1 일반화:** `REPLAY_VERIFIED` 자격을 native J 특정 구현에 묶지 않고 "설계자가 승인한 independent replay verifier"로 바꿈. native J는 별도 이종 실행기 비트 동등성 Gate.
- **N-1 첫 실측값:** `ac14385` 사후 검증 조사 결과를 측정 항목의 첫 값으로 기록.
- 현재 scratch verifier는 정식 verifier가 아님을 명시하고, 정식판 요건을 적음. mpmath 구간 엄밀성은 신뢰 기반으로 공개.
- 헌법 개정을 판정 대기에서 **반영 순서 ⓪**으로 옮김. L 원칙 v2(희귀 경로 계약) 반영.
- 【판정 대기】 표기 제거. 남은 설계자 확인 항목은 문서 끝 ⑨에 모음.

---

## ⓪ `PROJECT_CONSTITUTION.md`

`PROJECT_CONSTITUTION_AMENDMENT_L_ORIGIN_V1.md`의 2절(개정문: 제5·6·7·8·18·21·22조, 제13조 유지), 3절(목적·제4조 해석 메모), 6절(개정 기록 줄)을 그대로 적용한다. 머리말 제목 줄 `v0.2` → `v0.3`. 제26조와 조 번호는 바꾸지 않는다.

---

## ① 신규: `docs/active/A_THREE_LAYER_SEPARATION_V1.md`

````markdown
# A 세 층 분리 — 세계 / 검증 / 관측 (V1)

**상태:** 설계자 승인(2026-10-01). N-1〜N-5 승인(N-1은 2차 판정으로 일반화, N-4는 직접 산란 O-3 weak로 확정).
**근거:** 제안서 v0(`44240ef` 기준), v1(`5c5d6f8` 기준), 판정 기록 v2와 설계자 검토. 제안서 원문은 저장소 밖 보관. 사후 검증 조사 [C1B1_POSTVERIFY_SURVEY_V0.md](C1B1_POSTVERIFY_SURVEY_V0.md)(`ac14385`).
**변경 범위:** 이 문서는 코드를 바꾸지 않는다. 구현은 이 계약 뒤에 별도 Gate로 한다.

## 1. 원칙

A의 목적은 증명기가 아니라 관측 가능한 세계다(헌법 제3조, A 계산 구조 제안 1.1절).

| 층 | 내용 | 규칙 |
|---|---|---|
| 세계 층 | 상태 + 법칙 + 실행기 | 스스로 판정한 값만 기록. 판정 불가·범위 초과·r_min → fail-closed. 검증기 허락을 기다리지 않음 |
| 검증 층 | 실행기와 다른 코드 | 기초는 A-EV. 독립 재실행·표본 감사·성질 증명. 증거 등급을 매김 |
| 관측 층 | 측정·비교·분류 | CONFIRMED 구간만 읽음. 수렴 시험, 모델 재현, 현실 검증, 운영 통계 |

**formal proof는 버리지 않는다.** 역할이 "다음 단계로 가는 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다.
기존 자산(checker V1/V2, prover, wrapper, Proof Cache, shell 인증서, outer bound, Energy Bound, inbound V1, S4d 결과, 사후 검증 조사)은 검증 층 자산으로 보존한다.

**A-EV와 replay verifier는 서로 대체하지 않는다. A-EV는 세계 실행기의 판정 방법 자체에 대한 건전성 의무이고, replay verifier는 실제 생성된 세계 역사의 독립 재검증이다. 두 작업에서 같은 증명을 중복 요구하지 않는다.**
구현 전에 양쪽 의무와 증거 범위를 구분한다. replay verifier가 A-EV 모듈을 호출해야 한다는 뜻은 아니다.

**채택 근거(S4d 결과와 무관):** R1 A의 목적은 세계다. R2 실행과 검증은 실행 중 이미 분리돼 있다(실제 판정 약 2.35억 회 중 checker 경로 0회). R3 다원자에서 전 궤적 사전 증명 Gate는 확장성 병목이다. R4 현실 비교가 최종 목적에 직접 연결된다.

**전역 증명 표현:** 장시간 모든 초기조건의 개별 궤적을 추적하는 shadowing 형 증명은 혼돈계에서 비싸지거나 의미를 잃을 수 있다. 성질(에너지 범위, 금지영역, 사건 수, 통계 분포) 증명은 가능할 수 있다. "다원자라서 증명 자체가 불가능하다"고 주장하지 않는다.

## 2. 증거 등급 (축 1)

| 등급 | 뜻 |
|---|---|
| `EXECUTED` | 실행기만 계산 (A-EV 조건부) |
| `SAMPLED_AUDITED` | 구간 안 일부 step만 독립 재검사 통과. **검사한 step에 대해서만** 주장 |
| `REPLAY_VERIFIED` | 설계자가 승인한 independent replay verifier가 구간의 **모든 step**을 재검증하고 실행기 결과와 비트 동일함을 확인 |
| `CERTIFIED` | 구간 전체에 대한 증명/인증서가 독립 checker 통과 |

금지: 표본 → 상위 등급 자동 승격 금지. 표본 통과율을 구간 전체 성질로 서술 금지. 구간 등급 = 구간 안 최저 step 등급. 관측 결과는 사용 구간의 최저 등급을 표시. 등급 추가·개명은 설계자 판정.

`REPLAY_VERIFIED`는 `CERTIFIED`보다 낮은 등급이다. 승인된 verifier의 **신뢰 기반**(예: 사용하는 구간 산술 라이브러리의 엄밀성, 실행기와 공유하는 사양)은 verifier 계약에 적고 숨기지 않는다. 신뢰 기반이 있다는 사실은 이 등급에서 허용된다.

## 3. 확정 상태 (축 2)

`SPECULATIVE`(관측·B 접근 불가) / `CONFIRMED`(세계 역사로 확정) / `DISCARDED`(폐기, 삭제하지 않고 보존).

**N-1 (승인, 2차 판정으로 일반화):** C1-B1에서 CONFIRMED 최소 등급 = `REPLAY_VERIFIED`. 자격은 **특정 구현에 고정하지 않는다** — 설계자가 승인한 independent replay verifier가 전체 구간의 모든 step을 재검증하고 비트 동일성을 확인한 경우에 부여한다. **A 전체의 영구 규칙이 아니다.** C1-C 전에 재평가한다.

**native J:** 이종 실행기(가속 경로) 비트 동등성은 별도 Gate로 유지한다. C1-B1 CONFIRMED의 전제가 아니며 **C1-B1 종료 조건에서 제외한다.** native J 경로가 실제 세계 실행에 쓰이려면 그 전에 이 Gate를 통과해야 한다.

**production replay verifier 요건(정식판 전 고정할 것):**

1. witness 형식(예: 초기 상태 + step별 J)과 저장·재검증 규칙. streaming도 모든 step의 witness를 즉시 검사한다. 최종 인증서만 남기면 제3자의 재검증이 불가능하다는 한계를 명시한다. 이 인증서만으로 헌법 제15조의 정확한 역사 복원 의무를 충족했다고 보지 않는다
2. 판정 세 가지 `VALID` / `INVALID` / `REFUSED`와 각각의 뜻(REFUSED = 정밀도 상한·step 상한·자원 부족, 결과 미확정)
3. transition contract: 한 step의 정확 부분(kick·drift·반올림 규칙·범위·r_min guard)과 J 반올림 확인 규칙
4. dependency fingerprint: 실행기와 공유하는 사양(동결 매개변수 fingerprint, 질량, Δt, 반올림 규칙)과 import 금지 목록(`a_reference`, `a_numeric`, `engine`, `audit`)의 검사
5. 신뢰 기반 명시: 구간 산술 라이브러리(현재 후보 mpmath interval)가 진짜 enclosure를 준다는 가정
6. 결함 주입 세트의 영구 시험화(현재 scratch 12종)

**현재 상태:** `POSTVERIFY feasibility = HYBRID(가능)`, `production replay verifier = 미구현`. scratch verifier(`runs/c1b1_postverify_survey_20261001/verifier.py`)를 정식 verifier라고 부르지 않는다.

**재평가 측정 항목(N-1, 지금 고정)과 첫 실측값(`ac14385` 사후 검증 조사, scratch verifier, 7개 궤적 79,087 step):**

| 측정 항목 | 첫 실측값 |
|---|---|
| verifier / executor 비용 비율 | 직렬 경과 시간: 4.9〜5.8배(scratch Python 구현 상수). wall(6 작업자 병렬): 0.98〜1.19배. CPU 시간 자체를 측정한 값은 아니며, 서로 다른 병렬 조건의 경과 시간을 CPU 연산 절감으로 해석하지 않는다. 정확 산술 부분은 실행의 약 7%, 나머지는 J 반올림 확인용 구간 평가 |
| 메모리·저장 | streaming 검증 중 Python 힙 최고치 0.33 MB. witness(초기 상태 + J) 약 22 B/step, streaming 인증서 약 4 KB(재검증 불가) |
| REPLAY_VERIFIED가 실제로 잡은 불일치 수와 원인 | 실제 실행 불일치 **0건**(7개 궤적 전 step 일치). 결함 주입 12/12 검출은 심은 결함이며 이 항목의 "실제 불일치"로 세지 않는다 |
| 새 법칙을 양쪽 구현에 넣는 작업량 | 미측정(새 법칙 없음) |
| 대안 후보별 예상 비용 | 미측정 |

## 4. Speculative execution 계약

| 번호 | 규칙 |
|---|---|
| S-1 | 관측 층과 B는 SPECULATIVE 구간을 읽지 않는다 |
| S-2 | 불일치 발견 시 마지막 CONFIRMED checkpoint 뒤의 모든 구간을 DISCARDED |
| S-3 | 최대 speculative 거리(step 수·저장 용량)를 두고, 넘으면 실행기가 멈춘다 |
| S-4 | checkpoint 간격·최대 거리는 운영 설정이며 CONFIRMED 역사를 바꾸지 않는다(시험 대상) |
| S-5 | DISCARDED 구간과 불일치 기록을 보존한다 |

**N-2 (승인) 불일치 절차:** 자동 재실행 금지(결정론 세계에서는 같은 결과가 또 나온다). 양측 중단 → speculative 자손 전부 DISCARDED → 원인 조사 → 결함 수정 → 마지막 CONFIRMED부터 재실행.
"하드웨어 오류" 판정에는 독립 근거가 최소 하나 필요하다: 다른 장비에서 같은 코드·입력이 기대값과 일치하고 원래 장비에서만 불일치 / ECC·메모리·GPU 오류 로그 / 원래 장비 진단 시험 실패. 근거가 없으면 "원인 미상"으로 기록하고 재발 감시 항목에 올린다.
verifier가 `REFUSED`를 내면 불일치가 아니라 미확정이다. 해당 구간은 CONFIRMED가 되지 않고, S-3 거리 안에서 멈춘다.

**B 탐침 단계(L-7, 기록):** B의 관측 입력은 CONFIRMED 구간에서만. 탐침 행동은 CONFIRMED 경계 이후에만 세계에 들어간다. 롤백이 B가 본 구간을 지울 수 없어야 한다. 최대 거리는 B 설계 때 다시 판정한다.

## 5. Gate 재분류

**Gate 유지 — 한 걸음의 건전성:** 한 step 계산의 건전성(판정 규칙, 한 번 반올림), A-EV, fail-closed, overflow/unsupported/세 가지 거부 분리, **r_min 실행 guard**(drift 선분 포함), 결정론·상태 기록 계약, **승인된 independent replay verifier와 실행기의 비트 일치**, 이 문서의 등급·확정 계약.

**별도 Gate — 이종 실행기:** native J 등 가속·이종 구현의 비트 동등성. 실제 세계 실행에 쓰기 전에 통과.

**Gate에서 내림 — 미래 전체의 사전 증명:** D_valid 모든 궤적 완주 전역 증명, global shadowing, 모든 입력의 전체 산란각 formal proof, 모든 inner 궤적의 사전 Liveness, ④ step 4 inner confinement(R ≥ 5.35 유지 증명), inbound 저에너지 잔여, E_min 재생성.
→ 연구 과제로 보존하고, 운영 통계로 감시한다(guard 발동 횟수, 정지 횟수, REFUSED 횟수, 필요 정밀도 분포, 궤도 경계 체류 분포).

**N-3 (승인):** r_min guard(한 걸음의 안전장치)와 "그 guard가 D_valid에서 절대 울리지 않는다"는 사전 증명(완주 보장)은 다르다. **S4d passing-side δ 문제는 C1-B1 Gate에서 연구 과제로 이동한다.** 잃는 것: "D_valid는 반드시 끝까지 간다"는 약속. 남는 것: "끝까지 가거나, 틀리지 않고 멈춘다"는 약속과 발생 빈도 기록.
참고(`ac14385`): S4d가 닫지 못한 passing-side 4개 사례는 실제 궤적 사후 검증으로 각각 VALID였다. 이것은 그 궤적들의 검증이며 D_valid 전체의 사전 증명이 아니다.

## 6. 관측 층 비교의 세 종류

| 종류 | 비교 대상 | 강도 |
|---|---|---|
| O-1 수치 재현 | 같은 PES의 독립 고전 계산, Δt·정밀도 수렴 | 계산 검증 |
| O-2 모델 재현 | 모델 구축 자료 또는 같은 모델의 저자 계산값 | 약함, 독립 아님 |
| O-3 독립 현실 검증 | 모델 구축에 쓰이지 않은 실험값 | 가장 강함 |

Lang 2024의 S4·S6은 같은 퍼텐셜의 **양자** 계산이다. A는 고전이다. 이것들은 O-3가 아니다.

**N-4 (확정 2026-10-01): C1-B1 O-3 = Ar-Ar 직접 산란, 등급 표기 `O-3 weak`(큰 결함 탐지기, 정밀 검증 아님).** 조사: [C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md](C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md).
- 대상: Ar-Ar 교차 빔 미분 단면적, 현재 계약 E ≤ 10 De 안(대표: Kalos–Grosser 1972, E = 9.16×10⁻¹⁴ erg ≈ 4.65 De). Lang 2024 맞춤에 쓰이지 않은 독립 자료.
- 경로: A의 χ(E, b) → 관측 층 반고전 변환(WKB 위상, 동일 보손 대칭화 부분파 합) → 기기 평균 → 실험 lab 분포와 비교. A의 동역학 입력은 χ뿐이다.
- **실행 전에 봉인할 것:** (1) 원 실험자료 확보와 자료 선택(Parson–Siska–Lee 1972·Cavallini 1970의 충돌 에너지·자료 형식 원문 확인 포함), (2) 수치화(digitize) 방식과 그 오차 추정, (3) 반고전 변환 오차 E-QC(sc) 측정 방법(같은 PES의 정확 양자 부분파 계산과의 차이), (4) 비교 지표와 성공 기준·허용 오차(실험 오차 ⊕ E-QC ⊕ 수치화 오차 ⊕ E-model ±σ).
- 비교 기준에 Aziz 계열 경험 퍼텐셜을 쓰지 않는다(실험을 맞춤에 써서 독립성이 섞인다).
- **희박 Ar 점성은 폐기하지 않고 다원자 기체 단계의 강한 O-3로 이동한다.** 그 단계는 적분기 에너지 범위 확장(약 35〜50 De)이 어차피 필요하다(300 K 기체 충돌의 약 5%, 400 K의 약 13%가 10 De 초과). 적분기 범위 확장은 C1-B1 Gate에 넣지 않는다.

**O-3 착수 순서(확정):** 원문 확보·후보 확인·수치화 및 오차 평가 방법·WKB/양자 비교 코드 설계·비교 지표·성공 기준 봉인 준비는 지금 가능하다. 공식 결과는 production replay verifier 완성·설계자 승인 → trajectory 전 step 검증 → REPLAY_VERIFIED → CONFIRMED → O-3 관측 계산·실험 비교 순서를 따른다. 개발 탐색 실행은 `EXECUTED`, `NOT OFFICIAL O-3`로 구분하며 공식 결과로 발표하지 않는다.

## 7. 정확한 분수 대리식

법칙(Lang 2024)은 바꾸지 않는다. 결과 비트가 같은 fast path 후보로만 survey한다. 지금 반올림은 병목이 아니다.

## 8. C1-B1 종료 조건

- Gate: A-EV, **production independent replay verifier 구현·설계자 승인**(3절 요건 1〜6), `_decide` 예외 분류 정리, 등급·확정 계약 문서화와 최소 시험(자동 승격 금지, 롤백 시 자손 폐기, 최대 거리 정지, REFUSED 미확정 처리), [완료] fail-closed·r_min guard·세 가지 거부·결정론·기록
- 별도 Gate(C1-B1 종료 조건에서 제외 확정): native J 비트 동등성(사용 전 통과)
- 관측: O-1, O-2 기록, **O-3 weak(직접 산란, 착수 전 봉인)**, 운영 통계 형식
- 연구 과제(보존): 5절 목록, 대리식 fast path survey
````

---

## ② 신규: `docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`

본문 = 별도 파일 `L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md` 전체 그대로. 파일명은 V2로 둔다(V1은 저장소에 들어간 적 없는 초안이며, 저장소 밖에 보존).
머리말의 상태 줄만 반영 시점에 맞춰 바꾼다:

```markdown
**상태:** 설계자 승인(날짜). 헌법 v0.3 개정(L 기원·관측)과 함께 적용.
```

---

## ③ 편입: `docs/active/C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md`

본문 = 저장소 밖 `C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md` 그대로. 머리말 상태 줄만 교체:

```markdown
**상태:** survey_only. 설계자 판정(2026-10-01): 권고 O3-1〜O3-5 채택 — C1-B1 O-3 = 직접 산란 `O-3 weak`, 점성은 다원자 기체 단계로 이동. 코드·동결 계약·적분기·Δt 변경 없음.
```

---

## ④ `RULES.md`

### ④-1 2절 "고수준 명령 금지" 바로 뒤에 새 소절 삽입

```markdown
### L은 생명을 만들지 않는다 (2026-10-01 설계자 결정, 헌법 v0.3)

세부: `docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`.

- L은 생명 생성기가 아니라 A의 관측 층에서 생명 관련 현상을 관측·분류하는 연구선이다. L 전용 법칙을 A에 넣지 않는다.
- 초기조건은 현실 근거가 있는 화학 환경(물, 분자, 광물, 온도·압력, 빛, pH, 구배, 습윤-건조 주기 등)까지만 준다.
  복제·유전·막 성장·대사 목적·신호·기억·학습·신경망과, 그런 결과를 내려고 고른 분자·구조를 넣지 않는다.
- `Signal`·`Memory` 같은 객체를 세계에 넣지 않는다. 신호·감지·기억은 관측자의 사후 분류다.
- **가능성 차단 ≠ 미발생(헌법 제21조).** 가능성이 열려 있었는데 아무것도 발생하지 않은 결과는 유효하다.
  세계 법칙이나 구현이 복제·변이·새 구조의 물리적 가능성을 인위적으로 제거한 것은 근본적 실패다.
- 생명을 나오게 하려고 법칙·매개변수를 조정하지 않는다. 여러 초기 환경을 돌릴 때는 목록과 현실 근거를 실행 전에 봉인하고, 모든 실행 결과를 보고한다.
- 계산 방법은 검증된 유효 모델로 압축할 수 있지만 결과를 압축(삽입)하지 않는다. 유효 모델 선택 기준은 "생명이 잘 나오는가"가 아니다.
- **희귀 경로 계약:** 유효 모델에서 제외하는 반응 경로는 목록으로 기록하고, 적용 범위(상태·온도·압력·농도)에서 경로별 속도·확률 상한과,
  모델이 선언한 공간·물질량·시간 범위 전체의 누적 기여 또는 예상 사건 수 상한(단위 후보·단위 시간당 속도 × 전체 시간 × 후보 수, 또는 1회 확률 × 전체 시도 횟수)을 제시한다.
  무시 가능함을 보이지 못한 경로는 계산 편의를 이유로 삭제하지 않는다. 무시 가능 기준은 결과를 보기 전에 정하고, 선언 범위를 넓히면 다시 확인한다.
```

### ④-2 1절 "물리와 실행 기술을 분리한다" 바로 뒤에 새 소절 삽입

```markdown
### 세계 / 검증 / 관측 세 층 분리 (2026-10-01 설계자 결정)

세부: `docs/active/A_THREE_LAYER_SEPARATION_V1.md`.

- 세계 층(상태·법칙·실행기)은 스스로 판정한 값만 기록하고, 판정할 수 없으면 fail-closed로 멈춘다. 검증기 허락을 기다리지 않는다.
- 검증 층은 실행기와 다른 코드다(executor ≠ verifier 유지). 기초는 A-EV다.
- A-EV는 실행기 판정 방법의 건전성 의무, replay verifier는 생성된 역사의 독립 재검증이다. 서로 대체하지 않으며 같은 증명을 중복 요구하지 않는다.
- 증거 등급 `EXECUTED` / `SAMPLED_AUDITED` / `REPLAY_VERIFIED` / `CERTIFIED`를 섞지 않는다.
  **표본 감사는 구간 전체의 검증이나 인증으로 승격하지 않는다.** 구간 등급은 그 안의 최저 등급이다.
- `REPLAY_VERIFIED`는 설계자가 승인한 independent replay verifier가 구간의 모든 step을 재검증하고 비트 동일함을 확인한 경우다.
  특정 구현에 자격을 묶지 않는다. verifier의 신뢰 기반(구간 산술 라이브러리의 엄밀성, 공유 사양)은 계약에 적고 숨기지 않는다.
- 확정 상태 `SPECULATIVE` / `CONFIRMED` / `DISCARDED`. 관측 층과 B는 CONFIRMED만 읽는다.
  불일치가 나면 마지막 CONFIRMED 뒤의 자손은 전부 DISCARDED(삭제 아님)다. verifier의 `REFUSED`는 불일치가 아니라 미확정이다.
- **불일치 시 자동 재실행 금지.** 양측 중단 → 원인 조사 → 결함 수정 → 마지막 CONFIRMED부터 재실행.
  "하드웨어 오류" 판정에는 다른 장비 교차 실행·장치 오류 로그·진단 실패 중 최소 하나의 독립 근거가 필요하다.
- 한 걸음의 건전성(판정 규칙, A-EV, fail-closed, r_min 실행 guard, 결정론·기록, 승인된 replay verifier와의 비트 일치)은 Gate다.
  미래 전체의 사전 증명(전 궤적 완주, global shadowing 등)은 Gate가 아니라 연구 과제·운영 통계다.
  이종 실행기(native J 등)의 비트 동등성은 별도 Gate이며, 실제 세계 실행에 쓰기 전에 통과한다.
- C1-B1의 CONFIRMED 최소 등급은 `REPLAY_VERIFIED`다. A 전체의 영구 규칙이 아니며 C1-C 전에 재평가한다.
```

### ④-3 6절 "중단 조건"에 한 줄 추가

```markdown
- 실행기와 검증기의 결과 불일치 (자동 재실행으로 해소하지 않는다)
```

---

## ⑤ `CURRENT_STATE.md`

### ⑤-1 상단 "현재 진행" 표 3행 교체

현행(`ac14385`, 18〜20행):
```markdown
| **현재 활성 Gate** | **C1-B1** |
| **현재 세부 단계** | **outer formal bound ④ 진행 — …(생략)… ④-Liveness 수학 연결 감사 중** |
| **다음 Gate** | **④-Safety(A-EV 선행) + ④-Liveness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증** |
```
교체:
```markdown
| **현재 활성 Gate** | **C1-B1** (세 층 분리 기준으로 종료 조건 재정의, 2026-10-01) |
| **현재 세부 단계** | **Gate 잔여: A-EV(별도 작업선), production independent replay verifier 구현·승인, `_decide` 예외 분류 정리, 증거 등급·확정 계약 최소 시험. 관측: O-1 수치 재현, O-3 weak(Ar-Ar 직접 산란, 착수 전 봉인). 별도 Gate: native J 비트 동등성. 전 궤적 사전 증명 항목(④ step 4, S4d δ, global shadowing 등)은 연구 과제로 이동** |
| **다음 Gate** | **C1-B1 종료 → 다원자 기체 단계(첫 항목: 적분기 에너지 범위 확장, 강한 O-3 = 희박 Ar 점성) → C1-C 전 N-1 재평가** |
```

### ⑤-2 표 아래 문장 교체

현행(22행):
```markdown
위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 아직 FROZEN이 아니며 ⑤는 시작하지 않았다.**
```
교체:
```markdown
위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 FROZEN이 아니며 ⑤는 시작하지 않았다.**
2026-10-01 세 층 분리 결정으로 ④의 "전 궤적 사전 증명" 부분은 Gate에서 연구 과제로 이동했다(삭제·실패 판정 아님).
④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결 상태 표기는 그대로 유지한다.
```

### ⑤-3 "작업선 분리(설계자 지시 2026-09-30)" 문단 바로 앞에 새 기록 삽입

(`ac14385`의 사후 검증 조사 기록 바로 뒤, 662행 앞이다.)

```markdown
**설계자 판정(2026-10-01, 기준 HEAD `ac14385`): A 세 층 분리 채택, C1-B1 종료 조건 재정의.** ([A_THREE_LAYER_SEPARATION_V1.md](docs/active/A_THREE_LAYER_SEPARATION_V1.md))
- 세계 / 검증 / 관측 분리. formal proof의 역할은 "다음 단계 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다. 기존 증명 자산은 전부 보존한다.
- 증거 등급 4단계와 확정 상태 3단계를 분리한다. 표본 감사는 승격하지 않는다.
- **N-1** C1-B1 CONFIRMED 최소 = `REPLAY_VERIFIED`. 자격은 native J 등 특정 구현이 아니라 **설계자가 승인한 independent replay verifier**에 둔다(C1-B1 한정, C1-C 전 재평가, 측정 항목 고정). 첫 실측값은 위 사후 검증 조사(직렬 경과 시간 4.9〜5.8배, 병렬 wall 0.98〜1.19배, 실제 불일치 0건). scratch verifier는 정식 verifier가 아니다 — production 요건 6개를 고정한 뒤 구현·승인한다. mpmath 구간 엄밀성은 신뢰 기반으로 공개한다.
- native J 비트 동등성은 **C1-B1 종료 조건에서 제외**하고 별도 이종 실행기 Gate로 유지한다. native J 경로를 실제 세계 실행에 사용하기 전에 통과해야 한다.
- **A-EV와 replay verifier는 서로 대체하지 않는다. A-EV는 세계 실행기의 판정 방법 자체에 대한 건전성 의무이고, replay verifier는 실제 생성된 세계 역사의 독립 재검증이다. 두 작업에서 같은 증명을 중복 요구하지 않는다.**
- O-3 자료 확보·봉인·관측 코드 준비는 지금 가능하다. 공식 O-3는 production verifier 승인 뒤 CONFIRMED trajectory만 사용한다. 개발 탐색 결과는 `EXECUTED / NOT OFFICIAL O-3`로 표시한다.
- **N-2** 불일치 시 자동 재실행 금지, 하드웨어 오류는 독립 근거 필요. **N-3** r_min 실행 guard는 Gate 유지, S4d passing-side δ는 연구 과제로 이동. **N-4** C1-B1 O-3 = Ar-Ar 직접 산란 `O-3 weak`(착수 전 자료·수치화·E-QC·성공 기준 봉인), 희박 Ar 점성은 다원자 기체 단계로 이동. **N-5** 문서 먼저, 코드는 계약 확정 뒤.
- 위 사후 검증 조사의 "다음 판단(설계자)" 질문(④의 목적)은 이 판정으로 답해졌다: 확정되는 결과의 독립 검증이 Gate이고, 모든 허용 입력의 사전 보장은 연구 과제다.
- 채택 근거는 S4d 결과와 무관한 R1〜R4로 한정했다. S4d는 실패로도 닫힘으로도 판정하지 않는다.
- 발견 기록: 현재 적분기 계약(E_rel ≤ 10 De)으로는 300 K Ar 기체 충돌의 약 5%, 400 K의 약 13%를 계산할 수 없다. 다원자 기체 단계 전 에너지 범위 확장이 필요하다.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 문서만 변경.

**설계자 판정(2026-10-01): L 최상위 원칙과 헌법 v0.3 개정.** ([L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md](docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md), [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md))
- L은 생명을 만들지 않는다. 현실적 초기 화학 조건에서 A를 실행하고 관측한다. 아무것도 발생하지 않는 결과도 유효하다.
- 헌법 제5·6·7·8·18·22조 의미 수정, 제21조 "가능성 차단(실패) ≠ 미발생(유효한 결과)" 명시, 제13조 원문·헌법 제목 유지, 목적·제4조 해석 메모. 제21조 예시는 해석 메모로 이동하고 검증된 유효모델의 정당한 경로 제외는 실패가 아님을 명시한다. 개정 전 v0.2는 `ac14385`에 보존.
- 유효 모델의 희귀 경로 계약: 제외 경로 목록 + 경로별 상한 + 선언 범위 전체의 누적 기여·예상 사건 수 상한.
- `EVOLUTION_V2_PLAN.md`·`EVOLVABLE_LANGUAGE_PLAN.md`는 L의 근거 문서가 아니다(레거시, 보존). 레거시·동결 확률 세계 코드는 개정 이전 기준선으로 보존하고 수정하지 않는다.
```

### ⑤-4 "아직 남음" 문단 교체

현행(664행):
```markdown
**아직 남음:** inbound / inner / global shadowing / 전체 산란각 / E_min 재생성 / 속박 궤도 domain·error proof / native J evaluator와 실행기 비트 동등성 / C1-B1 전체 freeze.
```
교체:
```markdown
**아직 남음 (Gate):** A-EV / production independent replay verifier 구현·승인 / `_decide` 예외 분류 정리 / 증거 등급·확정 계약 최소 시험 / O-1 / O-3 weak(직접 산란) / C1-B1 전체 freeze.
**별도 Gate:** native J evaluator와 실행기 비트 동등성(이종 실행기, CONFIRMED 전제 아님).
**연구 과제 (Gate 아님, 보존):** inbound 저에너지 잔여 / inner(④ step 4) / S4d passing-side δ / global shadowing / 전체 산란각 formal proof / E_min 재생성 / 속박 궤도 domain·error proof / 정확 분수 대리식 fast path survey.
```

---

## ⑥ `AGENTS.md`

### ⑥-1 "현재 개발 우선순위" 문단의 마지막 문장 교체

현행(28행):
```markdown
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1의 outer formal bound ④다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.
```
교체:
```markdown
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1이며, 2026-10-01부터 **세계 / 검증 / 관측 세 층 분리** 기준으로 종료 조건을 재정의했다(`docs/active/A_THREE_LAYER_SEPARATION_V1.md`). 한 걸음의 건전성과 승인된 independent replay verifier의 전 step 재검증은 Gate, 전 궤적 사전 증명은 연구 과제다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.
**L 원칙(헌법 v0.3):** L은 생명을 만들지 않고 관측한다. 가능성 차단은 실패, 미발생은 유효한 결과다(`docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`).
```

### ⑥-2 "먼저 읽을 것" 표에 행 추가 없음

(읽기 부담을 늘리지 않는다. RULES.md에 요약이 들어가므로 충분하다.)

### ⑥-3 "현재 정직한 한계" 목록

변경 없음. (L 원칙은 이미 "생명·복사·진화의 새 증거는 아직 나오지 않았다"와 모순되지 않는다.)

---

## ⑦ 색인

### ⑦-1 `docs/active/README.md`

상단 상태 줄 교체. 현행(3행):
```markdown
**상태: ACTIVE / C1-B1 / outer formal bound ④ 진행.** A가 최우선이며 L·B의 진행 시점은 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.
```
교체:
```markdown
**상태: ACTIVE / C1-B1 / 세 층 분리 기준 종료 조건(2026-10-01).** A가 최우선이며 L·B의 진행 시점은 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.
```

표의 첫 행(`C1-B1 설계·결정·검증`) 바로 아래에 두 행 추가:
```markdown
| [A 세 층 분리 V1](A_THREE_LAYER_SEPARATION_V1.md) | **설계자 승인(2026-10-01).** 세계/검증/관측 분리, 증거 등급·확정 상태, speculative 계약, Gate 재분류(한 걸음 = Gate, 전 궤적 사전 증명 = 연구 과제). CONFIRMED = 승인된 independent replay verifier의 전 step 재검증. native J는 별도 Gate. C1-B1 종료 조건 재정의 |
| [O-3 직접 산란 vs 점성 조사 v0](C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md) | survey_only. **설계자 판정: C1-B1 O-3 = Ar-Ar 직접 산란 `O-3 weak`**(E ≈ 4.65 De, Lang 맞춤과 독립, 착수 전 봉인). 희박 Ar 점성은 다원자 기체 단계로 이동(적분기 범위 확장 필요) |
```

### ⑦-2 `docs/DOCUMENT_STATUS_INDEX.md`

"현재 활성 A / C1-B1" 표(7행 절)에 추가:
```markdown
| [A_THREE_LAYER_SEPARATION_V1.md](active/A_THREE_LAYER_SEPARATION_V1.md) | 신규(2026-10-01). 세 층 분리·증거 등급·C1-B1 종료 조건 재정의 |
| [C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md](active/C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md) | 신규(2026-10-01). O-3 대상 조사, 직접 산란 O-3 weak 채택 |
```

참조 문서 표(45〜51행 절)에 추가:
```markdown
| [L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md](reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md) | 신규(2026-10-01). L 최상위 원칙, 헌법 v0.3과 함께 적용 |
```

### ⑦-3 `docs/reference/README.md`

표(`| 원문 | 이전 경로 |`)의 마지막 행 아래에 추가:
```markdown
| [L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md](L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md) | 신규(2026-10-01). L 최상위 원칙, 헌법 v0.3과 함께 적용 |
```

---

## ⑧ 레거시 계획 표기

`EVOLUTION_V2_PLAN.md`, `EVOLVABLE_LANGUAGE_PLAN.md` 맨 위(제목 바로 아래)에 한 줄 추가. 본문은 바꾸지 않는다.

```markdown
> **2026-10-01:** 헌법 v0.3(L 기원·관측) 이전 계획이다. 설계된 유전·발생 언어를 전제하므로 **L의 근거 문서가 아니다.** 역사 자료로 보존한다. 현재 L 원칙: `docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`.
```

---

## ⑨ 최종 설계자 판정(2026-10-01)

1. native J 비트 동등성은 C1-B1 종료 조건에서 제외. 실제 세계 실행에 사용할 때는 별도 Gate를 먼저 통과한다.
2. 제13조와 헌법 제목 유지. 제21조의 예시는 조문 밖 해석 메모로 이동하고 정당한 유효모델 경로 제외는 실패가 아님을 명시한다.
3. L 원칙 V2·희귀 경로 계약 승인.
4. N-4 직접 산란 O-3 weak 승인, 점성은 다원자 기체 단계로 이동.
5. O-3 자료 확보·봉인·코드 준비는 지금 가능. 공식 결과는 승인된 production verifier가 검증한 CONFIRMED trajectory만 사용한다.
6. A-EV / replay verifier 의무를 구분하고 동일 증명을 중복 요구하지 않는다.
7. 위 수정 후 문서 체계 일괄 반영. 코드 구현은 별도 Gate. commit/push 없음.

## ⑩ 이번 변경안에 넣지 않은 것

- 코드·시험·동결 계약·fixture·기준선 숫자: 변경 없음.
- production replay verifier 구현: 계약 확정 뒤 별도 Gate.
- 적분기 에너지 범위 확장: 다음 단계 계획의 첫 항목으로 기록만.
