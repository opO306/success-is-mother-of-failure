# 최종 입력 검토 정정 — 실제 청구 API 형식 및 failfast

검토자 `/root/state_contract_reviewer`. 이전 `REVIEW_FINAL_INPUTS.md`의 provider_next_token=False 관문은 실제 API 자료를 이 검토자가 직접 확인하지 않은 채 코드만 검토한 항목이었다. 이번에 보존된 실제 raw를 읽어 **next_token=null**임을 확인했다. False를 정상 형식으로 단정한 준비 관문은 정상 원장을 거부할 수 있는 결함이며, 이전 검토를 삭제하거나 합격 사실로 고치지 않고 이 기록으로 정정한다. 서버 조회·SSH·동적시험은 수행하지 않았다. 이 파일만 작성했다.

## 실제 원본 대조

원본 `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\state_contract_v1_readonly_20261009_094122\charges.json`의 SHA-256은 `b82eaba7cdf011448906fe51c8f163e39b2e536beda2baadcaa07ef0c5c1e942`이다. 민감한 청구 행을 복사하지 않고 metadata만 읽었다.

- success=true
- next_token=null
- count=6, total=6, results 길이=6

이 원본에 대한 query completeness의 근거는 위 필드 조합이다. 임의의 False 값이나 next_token 하나만으로 완료를 추정하면 안 된다. 향후 원장 작성부는 success=True, 명시된 next_token 키의 null, 정수 count/total 및 results 길이 일치를 실제 raw에서 검증한 뒤 provider_query_complete=True와 raw SHA를 남겨야 한다. incomplete/missing metadata는 유료 시작을 허가하는 근거가 아니다.

## 수정 읽기 및 최신 해시

bootstrap107은 provider_next_token=False 조건을 제거하고 provider_query_complete is True를 요구한다. raw SHA·원장 hash·timezone·0~300초 신선도·finite/nonnegative spent·전체 비용 cap 검사는 유지한다. 보존된 admin_budget_before.json에는 아직 이 새 flag가 없으므로 기존 원장을 그대로 사용하면 정상적으로 실행을 거부해야 한다. 새 원장 append와 승인 바인딩이 필요하며, 새 값이 실제 raw와 연결되는 작성 코드는 이 파일에서 실행하지 않았다.

runner74에는 failfast=True가 추가됐다. 예상 밖 failure/error가 생기면 suite가 나머지 case 실행을 중단하고 기존 finally가 부분 result/trace/log를 보존한다. PASS는 여전히 정확한45개·0failure/error/skip·자원/감사 차단 조건을 모두 요구한다. 적게 실행된 상태나 실패 반례의 예외를 예상대로 잡은 상태를 혼동하지 않는다. failfast의 실제 동작은 아직 동적으로 실행하지 않았다.

| 최신 입력 | SHA-256 |
|---|---|
| transport/admin_bootstrap.py | `be498587106f50932c64978dd028129a5b47f62cd22114058ff555d4004654e3` |
| transport/controller.py | `1b71f2bdcf4da2aa93231f0271189ed87a81d994ac89bf7db77f46387f8cdaa4` |
| transport/remote_admin_entry.py | `8310348e891b29904dcd7319535e1ceb0ce1d6662eddcea9d777161148dc52ec` |
| tests/test_admin_transport.py | `936be7a2dfcfc91842de0f7dbe2eda857230028253e11777e4e702b2f75fd2f5` |
| run_admin_simulation.py | `5fa217cfb84dede39670d1e12ee82cf6087a9ddb6d89a506b657de6966f2cd30` |

candidate_static_snapshot_1에는 이전 candidate ZIP/inventory/input record 세 파일이 별도로 존재하는 것을 읽기 전용으로 확인했다. 그 스냅샷을 현재 수정한 byte binding과 같은 것으로 사용할 수 없다. 새 packet은 별도 raw hash로 만들어 승인서와 연결해야 한다.

## 판정과 한계

새 bootstrap과 runner의 이 두 수정에서 추가 명백한 호출/정상 입력 오류는 정적으로 발견하지 못했다. **실제 최신 원장의 완전성 검증·append 승인 연결이 마련되지 않으면 실행 관문은 미충족**이다. 이번 기록은 원본 대조와 정적 동료 검토이며 독립 인증·모의45개 통과·실제 transport 성공이 아니다. 동적 PASS는0이고 기존 STARTING/OS/통신/강제종료/실청구의 미확인 한계는 유지한다. B95/A320을 실행하거나 과거 실패·비용을 초기화하는 권한을 만들지 않는다.
