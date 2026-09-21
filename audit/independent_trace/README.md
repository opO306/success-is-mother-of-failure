# 독립 trace 검증기

## 왜 필요한가

세계를 돌리면 **기록장**(`records.jsonl`)에 매 순간 무엇이 어떻게 바뀌었는지 전부 적는다. B는 나중에 그 기록장을 읽고 이론을 만든다. 그래서 **기록장이 정확한지**가 모든 연구 결과의 전제다.

문제는 기존 검증 방식이었다.

```
기록할 때 :  _delta() 로 변경 목록을 만들어 적는다
검사할 때 :  같은 _delta() 를 다시 돌려 적힌 것과 비교한다
```

`_delta()`에 결함이 있으면 **적을 때도 틀리게 적고 검사할 때도 똑같이 틀리게 계산해서 "일치합니다"** 하고 통과시킨다. 체중계가 5kg 적게 나오는데 그 체중계로 두 번 재서 "두 번 다 같네" 하는 것과 같다.

`verify_trace()` 하나에 B 도구 5개(`change_graph`, `hypotheses`, `impact_scope`, `theory_revision`, `trace_view_broker`)가 전부 매달려 있다. 단일 실패 지점이다.

## 무엇이 다른가

`engine/`에서 **아무것도 import 하지 않는다.** 기록장(JSON)만 읽고 스스로 해석한다.

| | 엔진 검증기 | 이 검증기 |
|---|---|---|
| 해시 | `json.dumps(sort_keys, separators)` 에 의존 | 정규화 규칙을 직접 명시해 바이트 생성 |
| 델타 검증 | 델타를 **다시 만들어** 비교 | 기록된 델타를 **실제로 적용**해 결과 확인 |
| 실패 처리 | 첫 불일치에서 예외 발생 | 모두 수집해 한 번에 보고 |
| 파일 해시 | `hashlib` | `hashlib` + 외부 `sha256sum` 병행 |

**델타 검증 방향이 반대인 것이 핵심이다.** 엔진은 "같은 함수로 다시 만들어 같은지" 보고, 이쪽은 "적힌 대로 적용하면 실제로 그 결과가 나오는지" 본다. 델타가 잘못 계산됐으면 적용해도 후속 상태가 안 나오므로 드러난다.

## 실제로 작동하는가 — 결함 주입 실험

엔진의 `_delta()`가 `causal.tick` 변경을 누락하도록 결함을 심고 trace를 만들었다.

```
엔진 자체 검증기 : 통과 (valid=True)      ← 자기 결함을 자기가 검사해서 정상 판정
독립 검증기      : 거부, 8건 발견         ← 모든 tick에서 정확히 탐지
```

이 실험은 `tests/test_audit_independent_trace.py::test_catches_a_recorder_bug_the_engines_own_verifier_cannot_see` 로 영구화되어 있다. 이 테스트가 **이 패키지가 존재하는 이유**다.

## 독립성은 테스트가 강제한다

문서상의 약속이 아니다. `test_audit_package_imports_nothing_from_engine` 이 `audit/` 아래 모든 파일의 AST를 검사해서 `engine` import가 하나라도 있으면 실패한다. 누가 나중에 "이 함수 이미 있네" 하고 가져다 쓰면 테스트가 바로 깨진다.

## 사용법

```bash
# D: vault 전체를 검사하고 엔진 결과와 비교
python run_independent_trace_audit.py --vault --compare-engine

# 특정 trace만
python run_independent_trace_audit.py <run_dir>

# 기계 판독용
python run_independent_trace_audit.py --vault --json
```

종료 코드: 발견 사항이 있거나 두 경로가 불일치하면 `1`, 전부 정상이면 `0`.

## 현재 결과 (2026-09-21)

D: vault의 trace 12개 전부 **엔진·독립·외부도구 3중 일치**.

이것이 말해주는 것: 현재 저장된 trace에 대해 두 독립 경로가 같은 결론에 도달했다.
이것이 말해주지 않는 것: 두 경로가 **모든** 결함을 잡아낸다는 보장. 교차 검증은 공유되지 않은 결함만 드러낸다.

## 발견 코드

| 코드 | 의미 |
|---|---|
| `manifest_missing` / `manifest_unreadable` | manifest.json 없음/손상 |
| `records_missing` | records.jsonl 없음 |
| `records_sha256_mismatch` | 파일 해시가 manifest와 다름 |
| `sequence_not_contiguous` | 레코드 번호가 연속하지 않음 |
| `chain_broken` | 해시 체인 연결 끊김 |
| `record_hash_mismatch` | 레코드 내용이 기록된 해시와 다름 |
| `delta_not_applicable` | 델타를 적용할 수 없음 (경로 오류, before 불일치) |
| `delta_does_not_reconstruct` | **델타를 적용해도 후속 스냅샷이 안 나옴** |
| `delta_count_mismatch` | delta_count가 실제 개수와 다름 |
| `*_digest_mismatch` | 스냅샷 해시 불일치 |
| `*_discontinuous` | 스냅샷 연속성 끊김 |
| `record_not_canonical` / `snapshot_not_canonical` | 정규화 불가 (예: 정수 세계에 float) |

## 한계

- **경로 문법**: 기록기가 배열을 통째로 교체하므로 배열 인덱싱(`$.cells[0]`)은 지원하지 않는다. 그런 경로가 나오면 추측하지 않고 `delta_not_applicable`로 보고한다.
- **같은 언어**: Python과 `hashlib`은 공유한다. 파일 해시는 외부 `sha256sum`으로 한 번 더 확인하지만, 나머지 검증은 Python 런타임을 공유한다.
- **명세는 안 본다**: 기록장 내부 일관성만 검사한다. "이 세계 명세대로 물리가 돌았는가"는 검사 범위 밖이다.
