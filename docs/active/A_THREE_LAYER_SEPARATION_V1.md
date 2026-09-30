# A 세 층 분리 — 세계 / 검증 / 관측 (V1)

**상태:** 설계자 승인(2026-10-01). N-1〜N-5 승인(N-1은 2차 판정으로 일반화, N-4는 직접 산란 O-3 weak로 확정).
**근거:** 제안서 v0(`44240ef` 기준), v1(`5c5d6f8` 기준), 판정 기록 v2와 설계자 검토. 제안서 원문은 저장소 밖 보관. 사후 검증 조사 [C1B1_POSTVERIFY_SURVEY_V0.md](C1B1_POSTVERIFY_SURVEY_V0.md)(`ac14385`).
**변경 범위:** 이 문서는 코드를 바꾸지 않는다. 구현은 이 계약 뒤에 별도 Gate로 한다.

## 1. 원칙

A의 목적은 증명기가 아니라 관측 가능한 세계다(헌법 제3조, A 계산 구조 제안 1.1절).

| 층 | 내용 | 규칙 |
|---|---|---|
| 세계 층 | 상태 + 법칙 + 실행기 | 스스로 판정한 값만 기록. 판정 불가·범위 초과·r_min → fail-closed. TEMP/SPECULATIVE 계산은 검증기 허락을 기다리지 않음. 확정은 검증 뒤 |
| 검증 층 | 실행기와 다른 코드 | 기초는 A-EV. 독립 재실행·표본 감사·성질 증명. 증거 등급을 매김 |
| 관측 층 | 측정·비교·분류 | CONFIRMED 구간만 읽음. 수렴 시험, 모델 재현, 현실 검증, 운영 통계 |

**실행 ≠ 세계 상태 확정.** TEMP/SPECULATIVE 실행 → POST VERIFICATION → VALID → COMMIT RESULT 순서이며, INVALID / REFUSED는 결과를 확정하지 않는다. 이 문서는 계약이고 runtime pipeline은 아직 미구현이다.

**formal proof는 버리지 않는다.** 역할이 "다음 단계로 가는 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다.
기존 자산(checker V1/V2, prover, wrapper, Proof Cache, shell 인증서, outer bound, Energy Bound, inbound V1, S4d 결과, 사후 검증 조사)은 검증 층 자산으로 보존한다.

**A-EV와 replay verifier는 서로 대체하지 않는다. A-EV는 세계 실행기의 판정 방법 자체에 대한 건전성 의무이고, replay verifier는 실제 생성된 세계 역사의 독립 재검증이다. 두 작업에서 같은 증명을 중복 요구하지 않는다.**
구현 전에 양쪽 의무와 증거 범위를 구분한다. replay verifier가 A-EV 모듈을 호출해야 한다는 뜻은 아니다.

**채택 근거(S4d 결과와 무관):** R1 A의 목적은 세계다. R2 reference executor와 proof checker는 별도의 실행 경로다. 승인 변경안의 약 2.35억 회·checker 경로 0회 수치는 이전 기록이며, 이번 문서 반영에서 원로그를 재검증하거나 재계측하지 않았다. R3 다원자에서 전 궤적 사전 증명 Gate는 확장성 병목이다. R4 현실 비교가 최종 목적에 직접 연결된다.

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

**현재 상태:** `POSTVERIFY feasibility = HYBRID(가능)`. [production replay verifier V1](C1B1_PRODUCTION_REPLAY_VERIFIER_V1.md)은 독립 모듈 `c1b1_replay/`로 구현·전 step 검증·LOCAL FULL을 완료했고 commit `8996aa60`의 지정 fingerprint 조합이 설계자 승인됐다([production approval manifest](C1B1_REPLAY_VERIFIER_PRODUCTION_APPROVAL_V1.json)). scratch verifier(`runs/c1b1_postverify_survey_20261001/verifier.py`)와 그 7개 VALID 결과는 자동 승격하지 않는다.

**N-1 공식 첫 비용 자료(설계자 승인, production V1 commit `8996aa60`):**

| 측정 항목 | 공식 첫 자료 |
|---|---|
| verifier / executor CPU | **약 2.773배**. 같은 7개, executor step CPU109.625s / streaming verifier CPU304.016s |
| 4-worker batch wall | **약 2.537배**. 양쪽 모두4 worker, executor40.952s / verifier103.905s. per-trajectory step 병렬화 수치가 아님 |
| 메모리·저장 | 원본 witness1,757,342 B(22.220 B/step), stream worker peak28.18〜29.95 MiB, aggregate RSS50ms 표본 peak145.64 MiB. summary는 재검증 원본 아님 |
| 실제 불일치 | 이전 production 전체 검증에서0건. 승인 후 보존 witness 재검증 결과는 [승인 기록](C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md)에 별도 기록. 심은 결함은 실제 불일치로 세지 않음 |
| 새 법칙의 양측 구현 작업량·대안 예상 비용 | 미측정. 이번 승인 작업에 새 법칙 없음 |

원 비용 파일의 hash와 지정 fingerprint는 [approval manifest](C1B1_REPLAY_VERIFIER_PRODUCTION_APPROVAL_V1.json)에 결합한다.
`ac14385` scratch의 약1배 wall(0.98〜1.19배)은 역사적 feasibility 자료다.
**N-1 공식 비용값으로 사용하지 않는다.** 승인 후 재검증의 실행 시간도 이 최초 비용
자료를 덮어쓰지 않는다. REPLAY_VERIFIED 승인은 CERTIFIED 승인이나 trusted origin
자동 승인이 아니다.

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
- **희박 Ar 점성은 폐기하지 않고 다원자 기체 단계의 강한 O-3로 이동한다.** 그 단계의 적분기 에너지 범위 확장 후보는 기존 조사에서 약 35〜50 De로 추정했다(충돌 빈도 가중 ∝ x e⁻ˣ 모델에서 300 K 약 5%, 400 K 약 13%가 10 De 초과; 실제 운영 실측이나 새 범위 승인이 아님). 적분기 범위 확장은 C1-B1 Gate에 넣지 않는다.

**O-3 착수 순서(확정):** 원문 확보·후보 확인·수치화 및 오차 평가 방법·WKB/양자 비교 코드 설계·비교 지표·성공 기준 봉인 준비는 지금 가능하다. 공식 결과는 production replay verifier 완성·설계자 승인 → trajectory 전 step 검증 → REPLAY_VERIFIED → CONFIRMED → O-3 관측 계산·실험 비교 순서를 따른다. 개발 탐색 실행은 `EXECUTED`, `NOT OFFICIAL O-3`로 구분하며 공식 결과로 발표하지 않는다.

## 7. 정확한 분수 대리식

법칙(Lang 2024)은 바꾸지 않는다. 결과 비트가 같은 fast path 후보로만 survey한다. 지금 반올림은 병목이 아니다.

## 8. C1-B1 종료 조건

- Gate: A-EV, **production independent replay verifier 구현·설계자 승인**(3절 요건 1〜6), `_decide` 예외 분류 정리, 등급·확정 계약 문서화와 최소 시험(자동 승격 금지, 롤백 시 자손 폐기, 최대 거리 정지, REFUSED 미확정 처리), [완료] fail-closed·r_min guard·세 가지 거부·결정론·기록
- 별도 Gate(C1-B1 종료 조건에서 제외 확정): native J 비트 동등성(사용 전 통과)
- 관측: O-1, O-2 기록, **O-3 weak(직접 산란, 착수 전 봉인)**, 운영 통계 형식
- 연구 과제(보존): 5절 목록, 대리식 fast path survey
