# N-5 저장소 반영 변경안 v1 (수정할 문구 전체)

**상태:** 변경안만. 저장소·브랜치·commit·push **하지 않음** (설계자 N-5 옵션 2).
**기준 커밋:** 원격 `master` `5c5d6f84367f304b998e4d7f276d848daa5a8e60`
**작성일:** 2026-10-01
**반영 순서:** ① 승인 문서 신규 → ② L 원칙 문서 신규 → ③ `RULES.md` → ④ `CURRENT_STATE.md` → ⑤ `AGENTS.md` → ⑥ 색인 2개
**보류 항목 표기:** `【판정 대기】`가 붙은 문구는 설계자 판정 뒤 확정한다. 현재 대기: N-4(O-3 대상), 헌법 개정(L 문서 10절).
**검증(반영할 때):** 문서만 변경 → `LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 문서만 변경, 코드·동결 계약·fixture 변경 없음`. 문서 링크·색인 관련 시험이 있으면 그것만 실행.

---

## ① 신규: `docs/active/A_THREE_LAYER_SEPARATION_V1.md`

````markdown
# A 세 층 분리 — 세계 / 검증 / 관측 (V1)

**상태:** 설계자 승인(2026-10-01). N-1〜N-3·N-5 승인, N-4 【판정 대기】.
**근거:** 제안서 v0(`44240ef` 기준), v1(`5c5d6f8` 기준)과 설계자 검토 2회. 제안서 원문은 저장소 밖 보관.
**변경 범위:** 이 문서는 코드를 바꾸지 않는다. 구현은 이 계약 뒤에 별도 Gate로 한다.

## 1. 원칙

A의 목적은 증명기가 아니라 관측 가능한 세계다(헌법 제3조, A 계산 구조 제안 1.1절).

| 층 | 내용 | 규칙 |
|---|---|---|
| 세계 층 | 상태 + 법칙 + 실행기 | 스스로 판정한 값만 기록. 판정 불가·범위 초과·r_min → fail-closed. 검증기 허락을 기다리지 않음 |
| 검증 층 | 실행기와 다른 코드 | 기초는 A-EV. 독립 재실행·표본 감사·성질 증명. 증거 등급을 매김 |
| 관측 층 | 측정·비교·분류 | CONFIRMED 구간만 읽음. 수렴 시험, 모델 재현, 현실 검증, 운영 통계 |

**formal proof는 버리지 않는다.** 역할이 "다음 단계로 가는 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다.
기존 자산(checker V1/V2, prover, wrapper, Proof Cache, shell 인증서, outer bound, Energy Bound, inbound V1, S4d 결과)은 검증 층 자산으로 보존한다.

**채택 근거(S4d 결과와 무관):** R1 A의 목적은 세계다. R2 실행과 검증은 실행 중 이미 분리돼 있다(실제 판정 약 2.35억 회 중 checker 경로 0회). R3 다원자에서 전 궤적 사전 증명 Gate는 확장성 병목이다. R4 현실 비교가 최종 목적에 직접 연결된다.

**전역 증명 표현:** 장시간 모든 초기조건의 개별 궤적을 추적하는 shadowing 형 증명은 혼돈계에서 비싸지거나 의미를 잃을 수 있다. 성질(에너지 범위, 금지영역, 사건 수, 통계 분포) 증명은 가능할 수 있다. "다원자라서 증명 자체가 불가능하다"고 주장하지 않는다.

## 2. 증거 등급 (축 1)

| 등급 | 뜻 |
|---|---|
| `EXECUTED` | 실행기만 계산 (A-EV 조건부) |
| `SAMPLED_AUDITED` | 구간 안 일부 step만 독립 재검사 통과. **검사한 step에 대해서만** 주장 |
| `REPLAY_VERIFIED` | 구간 전체를 독립 실행기로 재실행, 전 step 비트 동일 |
| `CERTIFIED` | 구간 전체에 대한 증명/인증서가 독립 checker 통과 |

금지: 표본 → 상위 등급 자동 승격 금지. 표본 통과율을 구간 전체 성질로 서술 금지. 구간 등급 = 구간 안 최저 step 등급. 관측 결과는 사용 구간의 최저 등급을 표시. 등급 추가·개명은 설계자 판정.

## 3. 확정 상태 (축 2)

`SPECULATIVE`(관측·B 접근 불가) / `CONFIRMED`(세계 역사로 확정) / `DISCARDED`(폐기, 삭제하지 않고 보존).

**N-1 (승인):** C1-B1에서 CONFIRMED 최소 등급 = `REPLAY_VERIFIED`. **A 전체의 영구 규칙이 아니다.** C1-C 전에 재평가한다.
재평가에 쓸 측정 항목(지금 고정): verifier/executor 비용 비율(CPU초·wall·메모리), REPLAY_VERIFIED가 실제로 잡은 불일치 수와 원인, 새 법칙을 양쪽 구현에 넣는 작업량, 대안 후보별 예상 비용.
C1-B1의 두 구현 = 기준 실행기(`a_reference/c1b1_two_atom.py`)와 native J 평가기 경로. native J 비트 동등성이 끝나야 C1-B1 CONFIRMED 역사를 만들 수 있다. 공유 요소(동결 매개변수 등)는 독립성 한계로 기록한다.

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

**B 탐침 단계(L-7, 기록):** B의 관측 입력은 CONFIRMED 구간에서만. 탐침 행동은 CONFIRMED 경계 이후에만 세계에 들어간다. 롤백이 B가 본 구간을 지울 수 없어야 한다. 최대 거리는 B 설계 때 다시 판정한다.

## 5. Gate 재분류

**Gate 유지 — 한 걸음의 건전성:** 한 step 계산의 건전성(판정 규칙, 한 번 반올림), A-EV, fail-closed, overflow/unsupported/세 가지 거부 분리, **r_min 실행 guard**(drift 선분 포함), 결정론·상태 기록 계약, 실행기 간 비트 일치(native J 포함), 이 문서의 등급·확정 계약.

**Gate에서 내림 — 미래 전체의 사전 증명:** D_valid 모든 궤적 완주 전역 증명, global shadowing, 모든 입력의 전체 산란각 formal proof, 모든 inner 궤적의 사전 Liveness, ④ step 4 inner confinement(R ≥ 5.35 유지 증명), inbound 저에너지 잔여, E_min 재생성.
→ 연구 과제로 보존하고, 운영 통계로 감시한다(guard 발동 횟수, 정지 횟수, 필요 정밀도 분포, 궤도 경계 체류 분포).

**N-3 (승인):** r_min guard(한 걸음의 안전장치)와 "그 guard가 D_valid에서 절대 울리지 않는다"는 사전 증명(완주 보장)은 다르다. **S4d passing-side δ 문제는 C1-B1 Gate에서 연구 과제로 이동한다.** 잃는 것: "D_valid는 반드시 끝까지 간다"는 약속. 남는 것: "끝까지 가거나, 틀리지 않고 멈춘다"는 약속과 발생 빈도 기록.

## 6. 관측 층 비교의 세 종류

| 종류 | 비교 대상 | 강도 |
|---|---|---|
| O-1 수치 재현 | 같은 PES의 독립 고전 계산, Δt·정밀도 수렴 | 계산 검증 |
| O-2 모델 재현 | 모델 구축 자료 또는 같은 모델의 저자 계산값 | 약함, 독립 아님 |
| O-3 독립 현실 검증 | 모델 구축에 쓰이지 않은 실험값 | 가장 강함 |

Lang 2024의 S4·S6은 같은 퍼텐셜의 **양자** 계산이다. A는 고전이다. 이것들은 O-3가 아니다.

**N-4 【판정 대기】:** 조사 `C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0` 결과 `SCATTERING-O3-CHEAPER`(조건부).
- 제안: C1-B1 O-3 = Ar-Ar 교차 빔 미분 단면적(현재 E ≤ 10 De 안, 예: Kalos–Grosser 1972, 4.65 De). A의 χ(E, b) → 관측 층 반고전 변환 → 기기 평균 → 실험 lab 분포와 비교. 등급 표기 "O-3 weak".
- 희박 Ar 점성은 강한 O-3 후보로 유지하고, 에너지 범위 확장이 어차피 필요한 다원자 기체 단계로 옮긴다(300 K 기체 충돌의 약 5%가 10 De 초과).
- 적분기 범위 확장은 C1-B1 Gate에 넣지 않는다.

## 7. 정확한 분수 대리식

법칙(Lang 2024)은 바꾸지 않는다. 결과 비트가 같은 fast path 후보로만 survey한다. 지금 반올림은 병목이 아니다.

## 8. C1-B1 종료 조건

- Gate: A-EV, native J 비트 동등성, `_decide` 예외 분류 정리, 등급·확정 계약 문서화와 최소 시험(자동 승격 금지, 롤백 시 자손 폐기, 최대 거리 정지), [완료] fail-closed·r_min guard·세 가지 거부·결정론·기록
- 관측: O-1, O-2 기록, O-3 【N-4 판정 대기】, 운영 통계 형식
- 연구 과제(보존): 5절 목록, 대리식 fast path survey
````

---

## ② 신규: `docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md`

본문 = 별도 파일 `L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md` 전체 그대로.
머리말의 상태 줄만 반영 시점에 맞춰 바꾼다:

```markdown
**상태:** 설계자 승인(날짜). 10절 헌법 개정은 【판정 대기】이며 이 문서만으로 헌법이 바뀌지 않는다.
```

---

## ③ `RULES.md`

### ③-1 2절 "고수준 명령 금지" 바로 뒤에 새 소절 삽입

```markdown
### L은 생명을 만들지 않는다 (2026-10-01 설계자 결정)

세부: `docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md`.

- L은 생명 생성기가 아니라 A의 관측 층에서 생명 관련 현상을 관측·분류하는 연구선이다. L 전용 법칙을 A에 넣지 않는다.
- 초기조건은 현실 근거가 있는 화학 환경(물, 분자, 광물, 온도·압력, 빛, pH, 구배, 습윤-건조 주기 등)까지만 준다.
  복제·유전·막 성장·대사 목적·신호·기억·학습·신경망과, 그런 결과를 내려고 고른 분자·구조를 넣지 않는다.
- `Signal`·`Memory` 같은 객체를 세계에 넣지 않는다. 신호·감지·기억은 관측자의 사후 분류다.
- 아무것도 발생하지 않는 결과도 유효하다. 생명을 나오게 하려고 법칙·매개변수를 조정하지 않는다.
- 여러 초기 환경을 돌릴 때는 목록과 현실 근거를 실행 전에 봉인하고, 모든 실행 결과를 보고한다.
- 계산 방법은 검증된 유효 모델로 압축할 수 있지만 결과를 압축(삽입)하지 않는다. 유효 모델 선택 기준은 "생명이 잘 나오는가"가 아니다.
```

### ③-2 1절 "물리와 실행 기술을 분리한다" 바로 뒤에 새 소절 삽입

```markdown
### 세계 / 검증 / 관측 세 층 분리 (2026-10-01 설계자 결정)

세부: `docs/active/A_THREE_LAYER_SEPARATION_V1.md`.

- 세계 층(상태·법칙·실행기)은 스스로 판정한 값만 기록하고, 판정할 수 없으면 fail-closed로 멈춘다. 검증기 허락을 기다리지 않는다.
- 검증 층은 실행기와 다른 코드다(executor ≠ verifier 유지). 기초는 A-EV다.
- 증거 등급 `EXECUTED` / `SAMPLED_AUDITED` / `REPLAY_VERIFIED` / `CERTIFIED`를 섞지 않는다.
  **표본 감사는 구간 전체의 검증이나 인증으로 승격하지 않는다.** 구간 등급은 그 안의 최저 등급이다.
- 확정 상태 `SPECULATIVE` / `CONFIRMED` / `DISCARDED`. 관측 층과 B는 CONFIRMED만 읽는다.
  불일치가 나면 마지막 CONFIRMED 뒤의 자손은 전부 DISCARDED(삭제 아님)다.
- **불일치 시 자동 재실행 금지.** 양측 중단 → 원인 조사 → 결함 수정 → 마지막 CONFIRMED부터 재실행.
  "하드웨어 오류" 판정에는 다른 장비 교차 실행·장치 오류 로그·진단 실패 중 최소 하나의 독립 근거가 필요하다.
- 한 걸음의 건전성(판정 규칙, A-EV, fail-closed, r_min 실행 guard, 결정론·기록)은 Gate다.
  미래 전체의 사전 증명(전 궤적 완주, global shadowing 등)은 Gate가 아니라 연구 과제·운영 통계다.
- C1-B1의 CONFIRMED 최소 등급은 `REPLAY_VERIFIED`다. A 전체의 영구 규칙이 아니며 C1-C 전에 재평가한다.
```

### ③-3 6절 "중단 조건"에 한 줄 추가

```markdown
- 실행기와 검증기의 결과 불일치 (자동 재실행으로 해소하지 않는다)
```

---

## ④ `CURRENT_STATE.md`

### ④-1 상단 "현재 진행" 표 3행 교체

```markdown
| 현재 진행 | 상태 |
|---|---|
| **현재 활성 Gate** | **C1-B1** (세 층 분리 기준으로 종료 조건 재정의, 2026-10-01) |
| **현재 세부 단계** | **Gate 잔여: A-EV(별도 작업선), native J 비트 동등성, `_decide` 예외 분류 정리, 증거 등급·확정 계약 최소 시험. 관측: O-1 수치 재현, O-3 【N-4 판정 대기】. 전 궤적 사전 증명 항목(④ step 4, S4d δ, global shadowing 등)은 연구 과제로 이동** |
| **다음 Gate** | **C1-B1 종료 → 다원자 기체 단계(첫 항목: 적분기 에너지 범위 확장, 강한 O-3 = 희박 Ar 점성) → C1-C 전 N-1 재평가** |
```

### ④-2 표 아래 문장 교체

기존:
```markdown
위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 아직 FROZEN이 아니며 ⑤는 시작하지 않았다.**
```
교체:
```markdown
위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 FROZEN이 아니며 ⑤는 시작하지 않았다.**
2026-10-01 세 층 분리 결정으로 ④의 "전 궤적 사전 증명" 부분은 Gate에서 연구 과제로 이동했다(삭제·실패 판정 아님).
④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결 상태 표기는 그대로 유지한다.
```

### ④-3 "작업선 분리(설계자 지시 2026-09-30)" 문단 바로 앞에 새 기록 삽입

```markdown
**설계자 판정(2026-10-01, 기준 HEAD `5c5d6f8`): A 세 층 분리 채택, C1-B1 종료 조건 재정의.** ([A_THREE_LAYER_SEPARATION_V1.md](docs/active/A_THREE_LAYER_SEPARATION_V1.md))
- 세계 / 검증 / 관측 분리. formal proof의 역할은 "다음 단계 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다. 기존 증명 자산은 전부 보존한다.
- 증거 등급 4단계와 확정 상태 3단계를 분리한다. 표본 감사는 승격하지 않는다.
- **N-1** C1-B1 CONFIRMED 최소 = `REPLAY_VERIFIED`(C1-B1 한정, C1-C 전 재평가, 측정 항목 고정). **N-2** 불일치 시 자동 재실행 금지, 하드웨어 오류는 독립 근거 필요. **N-3** r_min 실행 guard는 Gate 유지, S4d passing-side δ는 연구 과제로 이동. **N-4 【판정 대기】** O-3 대상(조사 결과 SCATTERING-O3-CHEAPER 조건부). **N-5** 문서 먼저, 코드는 계약 확정 뒤.
- 채택 근거는 S4d 결과와 무관한 R1〜R4로 한정했다. S4d는 실패로도 닫힘으로도 판정하지 않는다.
- 발견 기록: 현재 적분기 계약(E_rel ≤ 10 De)으로는 300 K Ar 기체 충돌의 약 5%, 400 K의 약 13%를 계산할 수 없다. 다원자 기체 단계 전 에너지 범위 확장이 필요하다.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 문서만 변경.

**설계자 판정(2026-10-01): L 최상위 원칙.** ([L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md](docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md))
- L은 생명을 만들지 않는다. 현실적 초기 화학 조건에서 A를 실행하고 관측한다. 아무것도 발생하지 않는 결과도 유효하다.
- 헌법 제5·6·8·18·22조와 충돌 가능 조항은 【판정 대기】. `EVOLUTION_V2_PLAN.md`·`EVOLVABLE_LANGUAGE_PLAN.md`는 L의 근거 문서가 아니다(레거시, 보존).
```

### ④-4 "아직 남음" 문단 교체

기존:
```markdown
**아직 남음:** inbound / inner / global shadowing / 전체 산란각 / E_min 재생성 / 속박 궤도 domain·error proof / native J evaluator와 실행기 비트 동등성 / C1-B1 전체 freeze.
```
교체:
```markdown
**아직 남음 (Gate):** A-EV / native J evaluator와 실행기 비트 동등성 / `_decide` 예외 분류 정리 / 증거 등급·확정 계약 최소 시험 / O-1 / O-3 【N-4 판정 대기】 / C1-B1 전체 freeze.
**연구 과제 (Gate 아님, 보존):** inbound 저에너지 잔여 / inner(④ step 4) / S4d passing-side δ / global shadowing / 전체 산란각 formal proof / E_min 재생성 / 속박 궤도 domain·error proof / 정확 분수 대리식 fast path survey.
```

---

## ⑤ `AGENTS.md`

### ⑤-1 "현재 개발 우선순위" 문단의 마지막 문장 교체

기존:
```markdown
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1의 outer formal bound ④다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.
```
교체:
```markdown
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1이며, 2026-10-01부터 **세계 / 검증 / 관측 세 층 분리** 기준으로 종료 조건을 재정의했다(`docs/active/A_THREE_LAYER_SEPARATION_V1.md`). 한 걸음의 건전성은 Gate, 전 궤적 사전 증명은 연구 과제다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.
**L 원칙:** L은 생명을 만들지 않고 관측한다(`docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md`).
```

### ⑤-2 "먼저 읽을 것" 표에 행 추가 없음

(읽기 부담을 늘리지 않는다. RULES.md에 요약이 들어가므로 충분하다.)

---

## ⑥ 색인

### ⑥-1 `docs/active/README.md` 표의 첫 행 바로 아래에 추가

```markdown
| [A 세 층 분리 V1](A_THREE_LAYER_SEPARATION_V1.md) | **설계자 승인(2026-10-01).** 세계/검증/관측 분리, 증거 등급·확정 상태, speculative 계약, Gate 재분류(한 걸음 = Gate, 전 궤적 사전 증명 = 연구 과제). C1-B1 종료 조건 재정의. N-4 판정 대기 |
```

같은 파일 상단 상태 줄 교체:
```markdown
**상태: ACTIVE / C1-B1 / 세 층 분리 기준 종료 조건(2026-10-01).** A가 최우선이며 L·B의 진행 시점은 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.
```

### ⑥-2 `docs/DOCUMENT_STATUS_INDEX.md`

"현재 활성 A / C1-B1" 표에 추가:
```markdown
| [A_THREE_LAYER_SEPARATION_V1.md](active/A_THREE_LAYER_SEPARATION_V1.md) | 신규(2026-10-01). 세 층 분리·증거 등급·C1-B1 종료 조건 재정의 |
```

참조 문서 표(또는 해당 절)에 추가:
```markdown
| [L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md](reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V1.md) | 신규(2026-10-01). L 최상위 원칙. 헌법 개정 부분은 판정 대기 |
```

---

## ⑦ 이번 변경안에 넣지 않은 것

- 헌법(`PROJECT_CONSTITUTION.md`) 개정: L 문서 10절의 조항별 제안은 설계자 판정 뒤 별도 변경안으로 만든다.
- 조사 문서 `C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md`의 저장소 편입: N-4 판정 뒤 `docs/active/`에 넣을지 결정.
- 코드·시험·동결 계약·fixture·기준선 숫자: 변경 없음.
