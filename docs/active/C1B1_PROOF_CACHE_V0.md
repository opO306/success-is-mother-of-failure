# C1-B1 Proof Cache V0 — 검증된 witness의 선반, 쓸 때마다 다시 검증

**상태:** **Proof Cache V0 = APPROVED**(설계자 판정 2026-09-30: 기본 구조·재검증·OFF/empty/warm 불변성·STALE/REJECTED/REFUSED·로그 위조의 권한 없음·tail 한계 공개, 관련 시험 529, LOCAL FULL 3289 승인 + 마지막 종단 시험 1건 통과 조건 충족 → 6.4절). ④-Liveness 인증이 아니다. 최종 승인(2026-09-30) 기준 HEAD `af0a341`.
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
7. **로그 무결성 ≠ 물리 correctness (V0의 audit/provenance 한계, 숨기지 않는다).** 해시 체인은 formal tamper-proof가 아니다. (a) **events 마지막 줄** 자체의 변조는 체인이 볼 수 없다(뒤에서 가리키는 줄이 없다). (b) **index와 events의 꼬리를 둘 다 일관되게 다시 쓰면**(체인·교차 참조 유지) 정직한 입고와 구별할 수 없다. 이것은 시험으로 확인했다(`corrupt`가 `None`으로 남음). 이 한계가 **세계 상태로 전파되지 않는 것**도 시험한다: 로그·색인의 어떤 문구도 raw를 승인하지 않고(로그에 raw 필드가 없고, bytes → usable raw로 가는 곳은 `_check`의 `verify_witness` 한 곳뿐), 위조된 항목은 쓸 때마다 bytes → 주소 해시 → parse → binding → 정확한 입력 → checker V2 VALID 순서로 다시 검증되어 거부되며, 세계 상태는 캐시 없는 실행과 같다. 위조가 할 수 있는 일은 가용성 손실(정상 항목이 있어도 못 찾음)이나 죽은 항목의 재검사뿐이다.

## 6. 결과

### 6.1 시험 (Proof Cache 42개 + 관련 시험)

| 실행 | 결과 |
|---|---|
| 로컬 `test_c1b1_proof_cache.py` 직렬·병렬(`-n 6`), 마지막 보강 뒤 | **42 passed, 60초** |
| **VAST 관련 시험 묶음(REMOTE LINUX, `-n 12`, RTX 3090 노드 52763685)** | **529 passed + 1 xfailed, 실패·error·skip 0(junit의 skipped 1 = strict xfail), exit 0, 194.43초** |
| 위 묶음 구성 | proof_cache 42 · runtime_wrapper 42 · point_prover 24 · checker V2 95 · checker V1 185 · runtime_local_witness 23 · step_fail_closed 8 · two_atom 41 + xfail 1 · blind_execution 16 · blind_protocol 25 · blind_session 28 |
| 코드 동일성 | 원격에서 돌린 `c1b1_proof_cache.py`·`c1b1_runtime_wrapper.py`·`test_c1b1_proof_cache.py`의 SHA-256이 로컬과 같다 |

- **위 원격 실행은 REMOTE LINUX의 관련 시험 묶음**이지 REMOTE LINUX FULL도 LOCAL FULL도 아니다.
- **LOCAL FULL(설계자 지시: 기존 runtime source에 wrapper 통합을 넣었으므로 Gate를 닫을 때 1회):** `python -m pytest tests -q -n 6`, HEAD `1636b1d`, **3289 passed + 1 xfailed, skip 0, 실패·error 0, exit 0, 554.35초.** xfailed는 기존 strict xfail(`test_representation_preserving_translation_b64`)이다. junit도 같다(tests 3290, failures 0, errors 0, skipped 1 = 그 xfail). 이전 공식 기준선 2834 + 1 xfailed(2026-09-28)보다 455개 많다: 그 사이 여러 Gate(checker V1/V2, prover, wrapper, Proof Cache 등)가 관련 시험만으로 LOCAL FULL을 생략했고 이번 실행이 한 번에 확인했다. **회귀는 없다.** 컴파일러 출력 인코딩 경고: 이번 로그의 요약(-q)에는 경고 줄이 없다. 원인은 조사하지 않았고 해결됐다고 보고하지 않는다. 증거: `runs/c1b1_proof_cache_v0_validation_20260930/{local_full.log,local_full.xml,local_full_head.txt}`.
- **첫 원격 실행의 2건 실패는 제 설정 오류였다(보존).** `test_c1b1_two_atom.py`의 두 시험이 `D:\reference\ar2_lang2024\S2_ar2_pot.f90`을 찾지 못했다. 참조 파일 심볼릭 링크를 만들 때 셸 따옴표 처리 오류로 이름이 틀렸다. 코드·물리와 무관하다. 링크를 고친 뒤 `two_atom` 41 passed + 1 xfailed를 확인하고, 깨끗한 단일 실행으로 전체 묶음을 다시 돌려 위 결과를 얻었다. 첫 실행 로그(527 passed, 2 failed)는 `runs/c1b1_proof_cache_v0_validation_20260930/vast_run1_setup_error/`에 보존했다.
- 증거: `runs/c1b1_proof_cache_v0_validation_20260930/vast_clean/{related.log,related.xml,head.txt,DONE}`.

### 6.2 요청된 시험 항목 (모두 실제로 실행·통과)

| 항목 | 시험 | 확인한 것 |
|---|---|---|
| OFF / 빈 캐시 / 찬 캐시 동일 | `test_cache_off_empty_and_full_are_bit_identical_in_every_state_and_every_decision` × 궤적 2개(1,640 / 5,775 step, cap 128 rehearsal) | 일반 실행기·캐시 없는 wrapper·빈 캐시·찬 캐시 4가지의 **매 step raw 상태와 매 witness 결정(step, 키, raw)이 모두 같다**. witness 25개 / 77개 |
| hit에서 prover 0회, checker는 재검증 | 같은 시험 | 찬 캐시 실행: prover 0회, **V2 checker는 witness당 정확히 1회**(25 / 77). 빈 캐시·캐시 없음: prover 25 / 77, checker는 2배(prover 내부 + wrapper 바이트 재검증) |
| certificate 1bit 변조 | `test_a_damaged_object_is_rejected_by_its_address[flip_byte]` | 주소 불일치 → REJECTED, prover로 진행, 상태 동일 |
| object 바꿔치기 | `[swapped]` | 다른 입력의 VALID witness 바이트를 같은 주소 파일에 넣음 → 주소 불일치 REJECTED |
| 다른 binding | `[stale_binding]` | STALE, 보존, 사용 안 함 |
| 다른 dr / component / dt | `other_dr`, `other_component`, `other_dt` | **각각 그 입력의 진짜 VALID witness**를 넣었는데도 input_mismatch → REJECTED |
| malformed / oversized | `malformed`, `oversized` | bad_json → REJECTED. 256 KiB 초과는 **`json.loads` 호출 전** 거부, REFUSED, 항목은 죽지 않음 |
| missing object | `[missing]` | REJECTED(`missing_object`) |
| index 변조 | 로그 변조 시험 4종 + 일관된 꼬리 재작성 4종 | 체인 불일치 → 선반 사용 중단(세계는 prover 경로로 동일 진행). 일관된 재작성은 로그가 못 잡지만 위조 witness는 검증에서 거부(7번 한계) |
| checker INVALID | `invalid_raw` | REJECTED, 상태 동일 |
| checker REFUSED | `test_refused_is_not_rejected...[checker_refused]` | 이번 사용만 실패, run 불변, 항목은 살아 있어 다음에 hit |
| REJECTED 재사용 시도 | `test_rejected_never_revives...`, `test_a_rejected_entry_is_not_checked_again` | 바이트를 고쳐도, 선반을 다시 열어도 다시 쓰지 않음 |
| 같은 key에 여러 content address | `test_one_lookup_key_with_several_content_addresses` × 2 | 나쁜 주소는 REJECTED 후 같은 조회에서 다음 주소 시도, 좋은 주소로 종료 |
| 캐시 모듈 변이체 4종 | `trusts_the_stored_bytes`, `refused_is_rejected`, `no_cap_rule`, `forgets_dead_entries` | 전부 잡힘 |

### 6.3 아직 증명되지 않은 것
1. ~~실제 production cap(16384) STOP의 종단 입고는 시험하지 않았다.~~ **6.4절에서 합성 near-tie 1건으로 시험했다.** 실제 궤적에서 관측된 production STOP은 여전히 0건이고 정식 선반 `runs/c1b1_proof_cache_v0/`는 비어 있다.
2. LOCAL FULL 통과. `AGENTS.md` 기준선을 3289 + 1 xfailed로 갱신했다(설계자 지시, FULL 재실행 없음).
3. single writer. 동시 쓰기, 스레드 안전성은 다루지 않았다.
4. A-EV 미해결(별도 작업선), ④-Safety Conditional, **④-Liveness NotCertified**. Proof Cache는 STOP을 검증된 witness로 푸는 저장소이며 D_valid 전체의 Liveness를 보이지 않는다.

### 6.4 실제 production cap 16384 종단 입고 1건 (설계자 지시, 승격 조건)

**시험:** 합성 near-tie `2^-17000`(부호 +, dt = 2·dt_kick 17,600비트 유리수, `validated_only=False`인 합성 스트레스 상태이며 물리 주장이 아니다) **한 사례**. 실행기 cap `MAX_PRECISION_BITS`는 16384 그대로이고 시험은 읽기만 했다(`precision_cap` 미사용, 시작·끝·OFF 실행 모두 16384). 같은 초기 상태에서 세 번: X1 = 새 임시 디렉터리의 **production 선반**(빈 선반), X2 = 같은 선반을 디스크에서 다시 열어 새 동일 run, Y = 캐시 OFF. X와 Y는 별도 프로세스에서 동시에 실행했다. 스크립트: `a_reference/c1b1_proof_cache_production_e2e.py`(survey_only, 스위트에 넣지 않음: 건당 12분 이상). 증거: `runs/c1b1_proof_cache_production_e2e_20260930/`.

| 조건 | 결과 |
|---|---|
| 실행기 단독 | `ReferenceUndecided` at cap 16384 (15.1초) |
| X1: STOP → prover → wrapper 바이트 재검증 → step 진행 | WITNESS_RESOLVED, **STOP 2회**(성분 0·1), prover 2회, checker 4회(prover 내부 2 + wrapper 재검증 2), `t_steps = 1`, **732.5초** |
| X1: new_certificates → production 입고 | 2개, certificate 각 33,692 바이트, object 2 / index 2 / admit event 2 생성 |
| 입고 metadata | 2건 모두 `kind = production`, `cap_before = 16384`, `cap_after = 16384`, `production_stop = true`, schedule 128 … 16384 |
| X2: 같은 선반 재실행 | 모든 witness `source = cache`, **prover 0회, checker 2회**(witness당 1회), use 이벤트 2건 모두 `hit`/`valid`, **299.3초** |
| raw 동일성 | X1 = X2 = OFF의 witness raw가 성분별로 같고 mpmath 구성 기대값 `1661044444155845687898841`과 같다 |
| 최종 상태 | X1 = X2 = OFF의 world state SHA-256 동일(`05fd14d2393a…`), `t_steps = 1` |
| 캐시 OFF | WITNESS_RESOLVED, prover 2회, checker 4회, source 전부 `prover`, **736.0초** |
| 전체 시간 | X와 Y 동시 실행 벽시계 **1047.5초** |

- 조건 14개가 모두 참이다. **"정확히 1건"의 의미:** 하나의 입력·하나의 step이다. 이 step은 x·y 성분의 정확한 충격량이 같아 STOP이 두 번 나오고(성분마다 별도 witness와 별도 object, 서로 다른 주소 2개) 두 번째 충격량은 실행기가 스스로 결정했다. 새 계산 캠페인이나 다른 STOP 탐색은 하지 않았다.
- **먼저 공개(실행 기록):** 첫 실행은 조건 13개가 참이고 1개(`raw_equals_mpmath_expected`)가 거짓이어서 스크립트가 exit 1로 끝났다(`run.exit`). 원인은 **제 스크립트의 비교 오류**였다: witness raw는 정수, 기대값은 문자열로 저장돼 있어 `int == str`이 항상 거짓이었다. 실제 값은 같다(위). 스크립트의 비교를 `int(...) == int(...)`로 고치고, **다시 실행하지 않고** 기록된 `summary.json`에서 조건을 재평가했다(`--recheck`, `recheck.json`, exit 0). 그러므로 이 조건 하나는 "실행 중 판정"이 아니라 "기록값 재평가"다. 캐시 모듈과 wrapper의 소스 해시는 시험 전후 같다(`sources.sha256`). 첫 실행 로그·exit는 보존했다.
- 이 시험은 **④-Liveness 전체 인증이 아니다.** 합성 입력 1건의 종단 경로 확인이다. A-EV 미해결, ④-Safety Conditional, ④-Liveness NotCertified는 변하지 않는다.
