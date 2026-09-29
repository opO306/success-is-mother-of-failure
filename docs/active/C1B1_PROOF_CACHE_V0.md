# C1-B1 Proof Cache V0 — 검증된 witness의 선반, 쓸 때마다 다시 검증

**상태:** 계약 + 구현 + 시험(아래 6절). 기준 HEAD `073c9c3`.
**현재 상태(변경 없음):** A-EV 미해결(별도 작업선), ④-Safety Conditional, **④-Liveness NotCertified**. 실행기·평가기·checker V1/V2·prover·물리 계약·D_valid 변경 0.
**근거:** 설계자 판정 2026-09-30 Q-PC1〜Q-PC4([관계 검토](C1B1_PROOF_CACHE_WAREHOUSE_RELATION_V0.md) 6절), [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) 5·7절(개정), [Runtime Wrapper V0](C1B1_RUNTIME_WRAPPER_V0.md) 9절의 필수 조건.

## 0. 한 줄

실행기가 **멈췄을 때만** 선반을 본다. 전에 똑같은 입력(같은 수학적 binding, 같은 dr·성분·dt_kick)을 증명해 둔 witness가 있으면, 그 **바이트를 다시 읽어 wrapper와 같은 검증(크기 → JSON → binding → 입력 → checker V2 VALID)을 전부 다시 한 뒤에만** 쓴다. 캐시가 아끼는 것은 prover의 탐색뿐이고 checker는 아끼지 않는다. 캐시는 계산 캐시가 아니라 **증명 저장소**다.

## 1. 선반 (Q-PC1)

정식 선반은 `runs/c1b1_proof_cache_v0/` **하나**다(Git 밖, 실행별로 쪼개지 않음, single writer). 시험은 전부 임시 디렉터리를 쓰고 정식 선반을 건드리지 않는다.

| 파일 | 내용 |
|---|---|
| `shelf.json` | `{"format": "c1b1-proof-cache-v0", "kind": "production" \| "test_only"}`. 만들 때 정해지고 바뀌지 않는다. 다른 kind로 열면 거부 |
| `objects/<sha256>` | witness canonical bytes(certificate + runtime binding) **그대로**. 파일 이름 = 바이트의 SHA-256(content address). 덮어쓰지 않는다 |
| `index.jsonl` | 줄마다 `{seq, prev, key_id, key, address}`: **정확한 lookup key → content address만** |
| `events.jsonl` | 입고(admission metadata, prover 요약, run id), 사용 결과(hit / STALE / REJECTED / REFUSED), 입고 거부 |

- **lookup key** = `{binding_sha256, input: {dr_raw, component, dt_kick}}`. binding은 wrapper의 수학적 binding 전체의 canonical SHA-256이다. `key_id` = 이 문서의 canonical SHA-256.
- 두 로그는 canonical JSON 줄의 **해시 체인**이다(`prev` = 앞 줄의 SHA-256). 색인 줄의 해시는 그 줄을 만든 입고 event에도 적힌다(`index_line_sha256`). 체인이 끊기거나 이 교차 참조가 없으면 선반 전체를 **쓰지 않는다**(조회 없음, 입고 없음). 세계는 prover 경로로 그대로 진행한다.
- 아무것도 지우거나 덮어쓰지 않는다(RULES 5절). 같은 주소에 다른 바이트가 이미 있으면(손상) 입고를 거부하고 event로 남긴다.

## 2. 조회와 결과 (Q-PC3)

wrapper가 STOP을 만나면(W1, 지원 profile 확인 뒤) `Config.cache.lookup`을 먼저 부른다. 같은 key의 항목을 최신부터 보며, 각 항목에 대해:

1. 객체 파일이 있는가 → 바이트의 SHA-256이 주소와 같은가
2. `verify_witness(bytes, key, run, claimed_raw=None, config)` — wrapper W2와 **같은 함수**. 외부 raw 주장이 없으므로 raw는 checker가 인정한 값이다

| 결과 | 조건 | 처리 |
|---|---|---|
| hit | 전부 통과 | raw를 witness로 쓴다. 기록 `source: cache` |
| **STALE** | 바이트의 binding ≠ 현재 binding | 보존, 이 항목은 다시 쓰지 않음 |
| **REJECTED** | 객체 없음, 주소 불일치, JSON 깨짐, 입력 불일치, checker INVALID | 보존, 다시 쓰지 않음, **스스로 부활하지 않음**(선반을 다시 열어도, 바이트를 고쳐도) |
| **REFUSED** | checker REFUSED, 바이트 크기 상한(W6) | **REJECTED가 아니다.** 이번 사용만 실패하고 event로 남긴다. 항목은 그대로 쓸 수 있다 |

hit이 없으면 기존 prover 경로로 간다. REFUSED 때 prover도 같은 한도로 거부되면 step은 UNPROVED이고 run은 바뀌지 않는다(세계 진행 금지). 같은 key에 새 prover가 만든 certificate는 새 색인 줄로 들어갈 수 있다(죽은 항목과 별개의 새 증거).

- 바이트 크기 상한을 REFUSED로 분류한 것은 구현자 해석이다(판정 표에 없음). W6에서 이 상한은 가용성만 제한한다고 정했기 때문이다.
- STALE은 정상 운영에서는 조회에 걸리지 않는다. binding이 바뀌면 key도 바뀌므로 옛 항목은 그냥 찾히지 않는다(보존). `status(run)` 보고가 현재 binding과 다른 항목을 STALE로 센다. 조회 중 STALE은 색인이 가리키는 바이트의 binding이 key와 어긋날 때만 생긴다.

## 3. 입고 (Q-PC2) — wrapper 밖의 admission 층

- wrapper는 캐시에 **쓰지 않는다**. `StepOutcome.new_certificates`에 prover가 새로 만든 (key, bytes)를 넘길 뿐이다. wrapper는 여전히 `MAX_PRECISION_BITS`를 읽지 않는다(정적 시험).
- `c1b1_proof_cache.step(run, cache, config)`이 admission 층이다. step **전후로** 실행기 cap을 읽고, 진행한 step의 새 certificate마다 admission metadata를 만든다: `kind, cap_before, cap_after, schedule(128…cap), production_stop, time, host`(+ run id, prover 요약). 이 정보는 events에만 있고 binding·key·객체에는 없다.
- **production 선반**은 `kind = production`, `cap_before = cap_after = 16384`, `production_stop = true`일 때만 받는다. 아니면 `admission_refused`로 기록한다. **test_only 선반**은 cap-128 rehearsal 등 무엇이든 받는다. test_only 증거가 정식 선반에 들어갈 경로는 없다(선반 kind 고정 + 규칙).
- W1에 의해 prover가 만든 모든 witness는 실제 STOP에서 나온다. 그래서 production_stop은 "그 STOP이 production cap에서 일어났다"와 같다.

## 4. 기록 (wrapper 9절 조건 3)

WITNESS_RESOLVED의 witness 기록마다 `certificate_sha256`(= content address), `certificate_bytes`, `source`(`prover` / `cache`)를 남긴다. 바이트 본문은 선반의 `objects/`에 있다. 기록 자체는 JSON으로 직렬화 가능한 값만 담는다.

## 5. 하지 않은 것 / 먼저 공개

1. **로그 마지막 줄의 한계.** 해시 체인은 각 줄이 앞 줄을 가리키므로 **마지막 events 줄의 변조는 볼 수 없다**. 색인 줄은 입고 event의 교차 참조로 막았지만 events 마지막 줄은 막을 수 없다. 예: 마지막 사용 결과를 REJECTED → REFUSED로 바꾸면 그 항목이 다시 검사 대상이 된다. **안전은 로그에 기대지 않는다:** 저장된 것은 쓸 때마다 바이트에서 전부 다시 검증되므로, 위조된 로그는 가용성을 떨어뜨리거나 죽은 항목을 한 번 더 검사하게 할 수 있을 뿐 검증 안 된 raw를 세계에 넣지 못한다. 이것을 시험으로 고정했다.
2. **실제 production 입고의 종단 시험은 스위트에 없다.** 실제 cap 16384 STOP은 합성 2^-17000 사례뿐이고 한 step에 약 13분이 든다. 스위트는 입고 규칙 자체(5가지 조합)와 cap-128에서 production 선반이 거부하는 것을 시험한다.
3. **손상된 객체가 있는 주소는 다시 입고할 수 없다.** 덮어쓰지 않기 때문이다. 그 key는 prover 경로로만 풀린다(가용성 손실, 안전 영향 없음).
4. **single writer.** 두 프로세스가 같은 선반에 동시에 쓰는 경우는 막지 않는다. xdist 시험은 각자 임시 선반을 쓴다. wrapper의 hook처럼 스레드 안전하지 않다.
5. Proof Box, Warehouse 등록, 선반 간 복사·병합, 저장 계층 이동은 하지 않았다. A-EV와 섞지 않았다.
6. 실제 궤적에서 cap 16384 STOP은 아직 관측되지 않았으므로 **정식 선반은 지금 비어 있다**(만들지도 않았다).

## 6. 결과

(시험 실행 뒤 채운다)
