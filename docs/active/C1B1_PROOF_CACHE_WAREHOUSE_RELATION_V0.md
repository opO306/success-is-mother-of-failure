# C1-B1 Proof Cache와 Proof Warehouse의 관계 V0 (검토, 문서만)

**상태:** 비교 검토. 코드 없음. 기준 HEAD `76f4240`(= origin/master).
**읽은 것:** Warehouse 제안서 전체(`origin/claude/proof-warehouse-architecture-skrgwm`의 `docs/proposals/A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md`, 749줄, 개정 1), [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) 5·7·8·9절, [Runtime Wrapper V0](C1B1_RUNTIME_WRAPPER_V0.md), [D_valid Liveness 경로 조사](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 6.3절.
**현재 상태(변경 없음):** Proof Cache 미착수, Warehouse 미구현(v0 착수 전 Q9〜Q11 확인 대기), A-EV 미해결(별도 작업선), ④-Safety Conditional, ④-Liveness NotCertified.

## 0. 결론

**캐시 저장소를 두 개 만들지 않는다. 역할이 다르고, 이미 설계자 판정으로 분리돼 있다.** 계약 V1 8절 C1과 9절 D6(2026-09-29 승인)이 정한 내용은 이렇다.

| | Runtime Proof Cache | Proof Warehouse |
|---|---|---|
| 무엇 | 실제 STOP을 푼 **검증된 witness 바이트**의 보관 선반 | 증명·계산 **결과 전체**의 색인과 의존성 장부 |
| 실행 경로 | **안에 있다.** STOP 때만 조회하고, 쓸 때마다 전부 재검증한다 | **밖에 있다.** A가 Warehouse를 조회해 실행을 결정하는 경로는 없다(Warehouse 8절) |
| 크기 | 아주 작다. 실제 cap STOP의 witness만 넣는다(계약 5절) | fixture 33〜34개와 `runs/` |
| 코드 위치 | wrapper가 쓰므로 `a_reference/` 쪽 | 별도 패키지 `proof_warehouse/`. `a_reference`는 이것을 import하지 않고, 이것도 `a_reference`를 import하지 않는다 |
| 구현 상태 | 다음 작업 | 미구현, 별도 Gate |

**관계는 한 방향이다.** 나중에 Warehouse가 생기면 Proof Cache의 객체를 **읽기 전용으로 등록**한다. fixture를 등록하는 것과 같은 방식이다. witness 바이트의 실제 사본은 Proof Cache 선반에만 있고, Warehouse는 metadata와 위치만 가진다. 반대 방향(Proof Cache가 Warehouse를 조회하거나 Warehouse 형식에 의존하는 것)은 없다.

**중복을 피하려면** Proof Cache가 지금부터 Warehouse의 규칙과 **같은 모양**으로 저장해야 한다. 그러면 나중에 등록할 때 변환이 필요 없다. 아래 2절이 그 목록이다.

## 1. 겹치는 원칙 — 이미 같은 것

| 원칙 | Warehouse | Proof Cache(계약 5절·wrapper 9절) |
|---|---|---|
| 저장된 상태를 믿지 않음 | 선언 `status`로는 CHECKED가 되지 않는다(Q2) | 저장된 `status`를 믿지 않는다 |
| 소비할 때마다 전체 재검증 | ④ 동결 전 full re-verify(Q3) | 쓸 때마다 binding 확인 + checker V2 재검증 |
| 지우지 않음 | STALE·REJECTED 보존, RULES 5절 | binding이 다르면 STALE: 쓰지 않고 다시 증명하되 지우지 않는다 |
| 내용 해시로 이름 붙임 | `payload_hash`, 연구 저장소 기법 | certificate 바이트의 SHA-256을 content address로(설계자 판정 2026-09-30) |
| 판정자는 checker | 창고는 판정하지 않는다 | 판정은 checker V2 `VALID`뿐 |

## 2. Proof Cache가 따를 Warehouse 규칙 (등록 때 변환이 없도록)

| # | Warehouse 규칙 | Proof Cache에서의 형태 | 현재 코드 실측 |
|---|---|---|---|
| R1 | 정체성과 내용 해시를 나눈다(7.3절: `artifact_id` ≠ `payload_hash`) | **조회 키**(binding 요약 + 정확한 입력) ≠ **content address**(바이트 SHA-256). 키로 찾고, 주소로 변조를 확인한다 | 키는 wrapper `_key`와 binding이 이미 있다 |
| R2 | run metadata는 정체성·해시 밖에 둔다(7.2절) | 저장 객체 = witness 바이트**만**. prover 시도·시간·호스트는 별도 기록 | **prover certificate에는 시간·시도 필드가 없다.** 같은 입력을 두 번 증명하면 certificate가 필드 단위로 같다(측정). prover 요약은 이미 `StepOutcome` 쪽에 따로 있다 |
| R3 | 정규 직렬화, 자료형 추측 금지, float 금지 | 바이트 = `json.dumps(sort_keys, compact)` UTF-8. 저장 전·후 바이트를 다시 만들지 않고 **그대로** 쓴다 | certificate 최상위에 float 없음(측정). 큰 정수는 문자열 |
| R4 | 검증 사건은 재생성할 수 없으므로 추가 전용 해시 체인 log에(7.5절, Q11) | 색인도 추가 전용 log로 둔다. 키 → 주소, 생산 기록(prover 요약), 이후 사용 결과 | 없음(설계 대상) |
| R5 | 신뢰를 낮추는 전이는 자동, 올리는 전이는 기록 필수. REJECTED는 스스로 풀리지 않는다(6.2절) | 저장 바이트의 해시가 주소와 다르거나 재검증이 거부되면 그 객체를 REJECTED로 기록하고 다시 쓰지 않는다. 같은 키는 prover 경로로 다시 푼다 | 설계자 확인 필요(4절 Q-PC3) |
| R6 | 저장 형식을 코드가 아니라 **파일 형식**으로 문서화 | Warehouse는 `a_reference`를 import할 수 없으므로 선반을 파일로 읽어야 한다. 객체 파일·색인 log 형식을 문서에 적는다 | 설계 대상 |
| R7 | import 방향(8절) | Proof Cache 모듈은 `proof_warehouse`를 import하지 않는다 | 현재 `proof_warehouse` 패키지 없음 |

## 3. 찾은 불일치·빈칸 (먼저 공개)

1. **master 문서가 master에 없는 문서를 가리킨다.** 계약 V1 5·8절은 "Warehouse Q3", "Warehouse 8절"을 인용한다. 하지만 Warehouse 제안서는 원격 브랜치 `claude/proof-warehouse-architecture-skrgwm`에만 있고 master에는 없다(`git ls-tree master docs/proposals/`로 확인). 그 브랜치를 master에 합칠지, 인용을 바꿀지는 설계자 결정이다. 이번에는 아무것도 합치지 않았다.
2. **binding 필드가 계약 7절 목록보다 하나 적다.** 7절은 "정밀도 schedule(128…16384)"을 요구한다. 현재 binding에는 없다. 모델 지문·C1-A 동결 지문(certificate `model.parameter_fingerprint`와 binding `model_fingerprint`가 같은 값이고, checker V2 `FROZEN_FINGERPRINT`와도 같다), proof method(`K2.METHOD`), checker 해시는 있다.
   - 충돌: 계약 5절은 "실제 cap(16384)에서 STOPPED였던 witness만" 넣으라고 한다. 이것을 검사하려면 cap을 알아야 한다. 그런데 wrapper 계약 5절과 정적 시험은 wrapper가 `MAX_PRECISION_BITS`를 **읽지도** 않게 강제한다. 둘을 동시에 만족할 방법은 설계자 결정이다(4절 Q-PC2).
3. **저장 위치가 정해지지 않았다.** 계약 5절은 prototype witness를 `runs/`에 둔다고만 했다. `runs/`는 Git 밖(D:)이고 RULES 5절(삭제·이동 금지, 8단계 절차)이 적용된다. Proof Cache는 추가 전용이라 이 규칙과 맞다. 다만 정식 위치(Git fixture인지, D:인지)는 정해야 한다(Q-PC1).
4. **Proof Box 승격(계약 5절)은 Proof Cache V0 범위 밖이다.** box는 구간 증명이라 성격상 Warehouse·인증서 쪽 artifact다. Proof Cache V0는 점 witness만 다룬다.
5. **실제 궤적에서 cap 16384 STOP은 아직 관측되지 않았다.** 지금까지 실제 cap STOP은 합성 2^-17000 두 건뿐이다. 따라서 Proof Cache는 실제 실행에서 대부분 비어 있을 것이다. 시험은 cap-128 rehearsal과 합성 STOP으로 한다. 성능 이득(791초 사례의 prover 탐색 약 절반)은 **같은 입력이 다시 나올 때만** 생긴다. 운동량 offset 다발(Liveness 조사 6.3절)이 그런 반복이 생기는 한 경로다.

## 4. Proof Cache V0 제안 범위 (코드 전에 확인받을 것)

- **넣기:** wrapper가 prover FOUND를 바이트에서 검증(W2)해 **통과한 뒤에만** 넣는다. 객체 파일 이름 = 바이트 SHA-256. 이미 있으면 바이트가 같은지 확인하고 새로 쓰지 않는다.
- **꺼내기:** STOP 키로 색인을 찾는다 → 바이트를 읽는다 → SHA-256이 주소와 같은지 본다 → `verify_witness` 전체(크기 → parse → binding → 입력 → V2 VALID → raw)를 거친다 → 통과하면 witness로 쓴다. 어느 단계든 실패하면 기존 prover 경로로 넘어간다. **캐시는 prover 탐색만 생략하고 checker는 생략하지 않는다.**
- **기록:** WITNESS_RESOLVED는 캐시를 쓰든 안 쓰든 content address와 출처(`prover` / `cache`)를 남긴다. 바이트 자체는 선반에 있다(설계자 판정 2026-09-30 조건 3).
- **시험(초안):** 캐시 on/off 매 step 비트 동일(계약 S6), 캐시 적중 시 prover 0회·checker 1회, 바이트 1비트 변조 / 객체 바꿔치기 / 색인 log 변조 / 다른 binding / 다른 입력 키 → 전부 사용 거부 후 prover 경로, 거부된 객체는 보존, 깨진 JSON·과대 크기는 파싱 전 거부.

**설계자 확인 항목:**

| # | 질문 | 구현자 권고 |
|---|---|---|
| Q-PC1 | 정식 선반 위치 | 시험은 임시 디렉터리. 실제 실행은 `runs/` 아래 실행별 선반(Git 밖, 추가 전용)으로 시작하고 Git fixture로 올리지 않는다 |
| Q-PC2 | "실제 cap 16384 STOP만" 조건과 "wrapper는 cap을 읽지 않음"의 충돌 | wrapper는 계속 cap을 읽지 않는다. 대신 **넣기를 호출자가 명시적으로 켜게** 한다(기본 끔, cap-128 rehearsal 시험에서는 켜서 동작만 확인). binding에 정밀도 schedule을 넣는 것은 V2 witness의 수학적 참과 무관하므로 넣지 않기를 권한다. 계약 7절 목록과 다르므로 판정이 필요하다 |
| Q-PC3 | 재검증에서 거부된 객체의 처리 | REJECTED로 기록하고 보존하며, 그 객체는 다시 쓰지 않는다. 같은 키는 prover로 다시 풀 수 있다(Warehouse 6.2의 "REJECTED는 스스로 풀리지 않는다"와 같다) |
| Q-PC4 | Warehouse 브랜치를 master에 합칠지 | 구현자 판단 밖. 합치지 않아도 Proof Cache V0 설계에는 지장이 없다. 다만 master 문서의 인용(3절 1번)은 어느 쪽이든 맞춰야 한다 |

## 5. 하지 않는 것

Warehouse 구현, Warehouse 브랜치 병합, Proof Box, A-EV 관련 작업(별도 작업선), ④-Safety 승격, Proof Cache와 A-EV를 한 증명으로 묶는 것, 실행기·checker·prover·물리 계약 변경.
