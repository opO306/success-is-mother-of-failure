# 유료 행정 시험 전 후속 동료 검토

검토자 `/root/state_contract_reviewer`. 실제 최신 entry·bootstrap·controller·45개 예정 시험·packet 작성 코드를 다시 읽었다. 네트워크·API·SSH·동적시험은 실행하지 않았다. 이 파일만 작성했다. 별도 동료 검토이며 독립 서명 인증과 유료 B95/A320 실행 권한이 아니다.

| 최종 읽기 스냅샷 | SHA-256 |
|---|---|
| transport/admin_bootstrap.py | `3ac61fb126570c9dab6c0e7ba8e90b8fafdfd3768af472e78ced6849a79202c7` |
| transport/remote_admin_entry.py | `8310348e891b29904dcd7319535e1ceb0ce1d6662eddcea9d777161148dc52ec` |
| transport/controller.py | `fef47a468a97ca70852ba1ec0ce815e2279ef0b15a1ab13799f141c9577d7578` |
| tests/test_admin_transport.py | `936be7a2dfcfc91842de0f7dbe2eda857230028253e11777e4e702b2f75fd2f5` |
| prepare_packet.py | `fe6187c3584e9383c0802e89edad0af6c2a7db3935beb0be3588443a5b38092e` |

## 추가 정상 fixture 결함 발견과 수정 확인

이번 검토에서 `AdministrativeEntryTests.test_admin_result_raw_counterexamples`가 boot.c.EXPECTED만 설정하고 AdminTransport를 생성하는 결함을 발견했다. bootstrap이 import하는 canonical `controller` 모듈은 configured()가 별도 이름으로 로드하는 transport_candidate와 다르다. main을 호출하지 않은 canonical controller의 KIND는 None이므로 Transport 초기화의 KIND.lower()가 정상 fixture를 AttributeError로 실패시킬 수 있었다. 정적 호출 경로에서 발견했으며 실제 실행 실패를 재현한 것은 아니다.

구현자에게 전달 후 tests388의 전체 for 문을 patch.object(boot.c,'KIND','ADMIN')와 patch.object(boot.c,'EXPECTED',2) 안에 넣은 것을 다시 읽어 확인했다. 정상/반례 fixture 모두 필요한 초기값을 받고, 문맥 종료 시 전역을 복구한다. 외부 실제 bootstrap의 main115가 ADMIN을 지정하는 경로를 바꾼 것이 아니라 시험 fixture의 잘못된 초기화만 고친 것이다.

## 이전 지적 해결 및 최신 경계 검토

- bootstrap16–24는 최초 allocation_start_utc와 armed raw SHA를 admin ticket에 넣고 ticket/armed 외부 SHA를 entry args로 전달한다. entry28–50은 실행 전에 raw hash, ADMIN schema/scope, caps, ID/machine/country/reference, 원본 guardian hash, 승인 유효시간, 최초 할당 age, armed age와 140+96 여유를 검사한다. 이전 누락된 게스트 관문이 정적으로 연결됐다.
- controller의 최신 ledger spent는 과거 carried bound와 max로 이어진다. 새 비용을 이전 target 값으로 덮어쓰는 지적은 수정됐다. 원장 최신성과 provider 개별 실청구는 코드 정적 확인과 별개다.
- 새 행정 시험 세 개는 false scope, 실제 AdminTransport 결과 validator의 정상·변조·CPU·affinity·skip·누락 자료, 실제 remote_admin_entry의 정상·hash·scope·armed·child failure를 직접 읽은 코드 경로로 연결한다. 정상 entry fixture는 원래 caps를 유지하고 ADMIN scope/time/hash만 명시적으로 TEST_ONLY 값으로 만든다.
- fake pathlib는 `/workspace`와 지정된 guest root만 실제 TEST_ONLY 디렉터리에 대응시키고 다른 값은 원래 Path로 처리한다. PurePosixPath는 실제 구현이다. sys.modules 교체와 Path.read_bytes·Popen·psutil.Process patch는 문맥 종료 시 복구된다. raw 파일/hash와 ZIP 검사는 실제로 수행하는 시험이며 child만 가짜다. 실제 유료 권한과 provider 호출이 이 fixture에 들어 있지 않다.
- remote packet의 repo 상대 깊이는 controller와 tests의 ROOT 계산에 맞는다. 원본 guardian/a_safety와 B ZIP/inventory/source seal 및 기존 실패/승인 원본은 prepare_packet의 fixed 목록에 들어 있다. 파일 누락이나 실제 원격 설치 상태는 전송 후 원본 hash/runtime 관문에서 확인해야 한다.
- 기존 actual supervisor/guardian main 시험의 explicit fake now/sleep 전달은 그대로 유지됐다. BEGIN/STOP 경계는 CheckedCli의 역할 전환과 복합 actual/intended 분류로 연결된다. ADMIN KIND은 B policy completion 영수증을 만들지 않는다.

## 결론과 정확한 한계

읽은 최신 스냅샷에서 **추가로 즉시 유료 첫 행정 시험을 차단할 명백한 정상 fixture/호출 논리 오류는 발견하지 못했다**. 앞선 정적 지적과 이번 KIND fixture 지적은 수정 확인했다. 이것은 정적 반례 검토의 결론이며 모의 45개 통과나 실제 transport 성공이 아니다. 지금까지 동적 PASS는 0이다.

아직 승인된 행정 실제 window의 provider runtime·최신 단가·누적 예산 raw·전송 원본·원격 supervisor/guardian 시작/STOP·45개 결과 회수·실제 종료·개별 비용 확인은 실행 검증 전이다. STARTING 실제 원본, PID 재사용, 실제 OS scheduling 및 API/SSH 원자성, 강제 자원 종료 전체의 부분 기록 보존도 완전 인증하지 않았다. static pass 뒤에 현장 수정·자동 재시도하거나 실패 기대값을 낮추는 것을 허용하지 않는다.

유료 행정 시험을 진행하더라도 B95/A320은 호출하지 않으며, TEST_ONLY 원본과 정책 영수증은 실제 B/A 관문 자료로 승격할 수 없다. 새 준비봉인은 실제 결과를 검토한 다음 작성하고, B95/A320 실행 승인은 별도로 받아야 한다.

## 종료값 보존 추가 읽기

위 스냅샷 뒤 payload 분리로 실패 시 반환값이 사라지는 문제를 구현자가 추가 수정했다. controller 초기화322의 payload_returncode=None, B 응답 직후546와 ADMIN 응답 직후26의 실제 반환값 저장, execute finally644의 관측값 복원을 정적으로 읽었다. 회수/결과 검증 실패가 실행의 실제 반환값을 덮어 없애지 않도록 하는 기록 변경이며 추가 실행이나 권한 확대는 아니다. 추가 읽기 SHA는 controller `1b71f2bdcf4da2aa93231f0271189ed87a81d994ac89bf7db77f46387f8cdaa4`, admin_bootstrap `4af8ac0258c6c5d8be3be568eaffee97310f37dc0097677b1dcbbceed2039c7c`이다. 동적 확인은 하지 않았다.
