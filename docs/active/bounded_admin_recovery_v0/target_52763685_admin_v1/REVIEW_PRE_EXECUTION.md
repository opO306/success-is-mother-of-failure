# 새 NO ADMIN 후보 실행 전 별도 정적 검토

검토자 `/root/state_contract_reviewer`. 검토 시점 HEAD `42cf0b27912db273927153aa65aaa389f8c28ed4`, 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`. 새 대상 코드는 아직 untracked 후보다. 실제 새 소스, 원본 state_contract_v1, unchanged guardian 및 과거 hourly amendment를 읽고 대조했다. 네트워크/API/SSH·동적시험·서버행동·소스 수정은 수행하지 않았다. 이 문서만 작성한다. 별도 동료 검토이며 독립 서명 인증이 아니다.

**검토 시점 판정: UNRESOLVED.** 아래 인수 전 종료 책임 누락을 해결하고 새 입력을 다시 고정해야 한다. 실제 ADMIN48개 시험·ARM·회수·종료는 아직 미확인이고, 정적 읽기를 PASS 또는 READY 봉인으로 표현할 수 없다.

## 실행 전 차단 결함과 원인

### 1. ADOPT_RUNNING의 supervisor 시작 실패가 running 서버의 STOP 경로를 잃는다

`transport/controller.py:561–598`에서 initial running API를 확인하고 최초 clock/lease를 만든 후 supervisor를 시작한다. `owns_stop=True`는 supervisor_ready가 성공한 뒤 598행에 설정된다. 582행 Popen 예외, 589–597행 ready 미생성/조기 종료/lease 해시 불일치가 나면 이미 running 서버를 대상으로 했는데도 owns_stop=False다. finally는 존재하는 supervisor.wait를 시도하고 666행의 최종 API 조회를 생략하며 직접 STOP fallback을 호출하지 않는다. supervisor Popen 자체가 실패하거나 `supervisor.py:63–77`의 try 이전 pin 검사에서 종료되면 supervisor의 finally STOP도 없을 수 있다.

공유된 기존 가정은 'supervisor 준비 전에 서버는 stopped'였다. 기존 Spain restart에서는 이 가정이 성립했지만 NO ADOPT는 그렇지 않다. initial 확인 후 인수를 승인한 시점에 종료 책임을 잡고, supervisor가 준비되지 않거나 죽은 경우 정확한 인스턴스만 CheckedCli와 기존 confirm_stop 상태기로 정지하는 연결이 필요하다. 새 임대/start/restart/시험 재실행과 구별되는 stop-only 정리다. 승인서 preflight 거부 전의 미인수 상태와도 구별해야 한다.

현재 새 NO full-controller 시험 `tests/test_admin_transport.py:510–557`은 정상 NOSupervisor를 fake한다. Popen 실패, ready 누락, 잘못된 ready SHA, supervisor의 try 이전 실패를 넣는 NO 인수 반례가 빠져 있다. stopped 대상의 기존 `supervisor_not_ready`/`supervisor_exited` 시험만으로 NO 종료 책임을 검증할 수 없다.

### 2. 현재 승인 원문·참조와 실제 승인서 연결 검사가 느슨하다

`admin_bootstrap.py:82`는 approval_reference/human_approval_text가 비어 있지 않은지만 확인하고 88행에서 현재 protocol SHA를 확인한다. `state_contract.py:41–42`, `supervisor.py:102–104`는 protocol의 ID/machine/country/hourly와 허용 플래그를 확인하지만 현재 call_dbc2f565a36449c3981be1f2db692099의 승인 참조·원문을 대조하지 않는다. 현재 protocol SHA는 공개 입력이므로 과거 또는 TEST_ONLY 참조 문자열을 넣은 NO 승인서가 동일한 SHA를 붙여 현재 승인 연결 관문을 통과하는 반례가 있다.

실제 bootstrap preflight에서 raw pinned current protocol의 approval_reference·human_approval_text·ADMIN scope·B95/A320=false를 실제 승인서와 정확히 대조할 것을 권고한다. 이는 사용자 서명을 독립 인증하는 기능이 아니며, 이미 보존한 이번 인간 승인과 이번 실행 입력이 서로 다른 문자열을 허용하지 않도록 하는 행정 연결이다. 모의 승인에는 TEST_ONLY 역할을 유지해야 한다.

## 확인한 변경과 재사용

- 새 hourly0.28은 exact52763685/machine3448/NO, explicit/exclusive, 실제 target_protocol 파일 SHA·허용내용으로 제한된다. 부재/잘못된 protocol SHA·초과요금/stopping 반례가 새 시험에 있다.
- bootstrap은 restart_exact_instance_authorized=false, adopt_existing_running_authorized=true, allocation_mode=ADOPT_RUNNING을 요구한다. controller 정상 경로는 start 호출 없이 running을 재확인하고 marker를 만든다. 첫 clock은 인계 전 한 번만 기록한다.
- immutable 원본 guardian의 hourly_cap을 바꾸지 않고 같은 NO 대상의 기존 immutable amendment hash를 연결한다. supervisor는 현재 target protocol을 별도로 확인하고 guardian deadline을 최대240초로 좁힌다. 과거 실험의 인간 승인만으로 현재 실행을 허용한다는 주장은 하지 않는다.
- 새 entry wall30초, SSH50초, 시작 전50+96초 여유 관문이240초 guardian와 연결된다. 원래600/CPU120/affinity1/512MiB/회수420/확인180/창0.05/합산0.10 상한을 완화하지 않는다. 준비가 오래 걸리면 시작을 거부하는 보수적 경로다.
- argv+SSH stdin/shlex/SCP-O, 실제 PID1 신원, ZIP/inventory/member raw hash, 새 root, 결과 manifest 개별 hash, 실패 회수1회 관문과 marker 기반 종료를 재사용한다. 현장 코드 수정·시험 재실행 경로를 추가하지 않았다.
- prepare_packet은 transport/fixture/test/runner/current protocol과 원본 B ZIP·inventory/seal 및 guardian/a_safety/old amendment를 함께 넣는다. 필수파일 누락을 조용히 제외하지 않고 거부한다. expected=48 정적 숫자는 실제48회 PASS 증거가 아니다.
- guardian_driver 및 runner bytes는 원본 state_contract_v1과 동일하다. runner failfast=True, real subprocess/network audit 차단, project/physics/GPU import 차단, 부분 결과 보존은 유지된다. 원본 guardian bytes도 같다.
- entry의 ES/NO 두 고정 profile 때문에 보존한45개 중 ES 정상 runpy fixture는 NO profile로 잘못 검사되지 않는다. PID1/workspace/child 경계만 fake한 실제 wrapper 검사와 실제 provider 실행을 구분한다.

## 남은 반례와 미확인

새3개는 NO 상태·원본 hourly_cap·full controller 정상 인수다. 실제 supervisor.main→guardian_driver.main→original guardian.main의 직접시험은 ES lease이고 NO는 hourly_cap과 fake NOSupervisor로 분리되어 있다. 따라서 새 NO supervisor branch에서 protocol/old amendment/240초 deadline이 실제 generic guardian와 끝까지 연동되는 것은 아직 동적 검증되지 않았다. 새 NO ticket profile의 직접 remote_entry 실행도 아직 실제 서버에서 확인하지 않았다.

실제 SSH latency/API형식 변화/원장 최신성·반올림 실제 청구/기존 workload 경쟁/30초 안에48개 완주/외부 실제 stopped는 정적 코드만으로 보장할 수 없다. 과거 NO 일별 청구는 인계 후 신규 시험 비용과 구별해야 한다. 현재 새 승인서 final 및 후보 ZIP/record는 아직 생성 전이라 실제 final 승인서→record→source 연결은 검토하지 않았다.

시험 정의 자체는 synthetic PASS status/JUnit를 fake 경계에서 사용한다. `TRACE`와 recovered `TEST_ONLY_simulated_raw`는 실제 B95/A320 결과나 독립 승인권 인증이 아니다. 이번 ADMIN 관문 통과도 다른 CPU의 실제 성능 개선·경험 이전 실증으로 승격할 수 없다. 기존 실패3회와 모든 추가 실패 원본의 상태는 보존해야 한다.

LOCAL FULL 생략 / 동적 시험으로 대체하지 않음 / 이번 검토는 사용자 제한에 따른 정적 읽기만이며 프로젝트 기준선 숫자를 갱신하지 않는다.

## 검토 입력 SHA-256

아래는 두 지적을 보고한 시점의 실제 bytes다. 이후 수정본과 혼동하지 않는다.

| 파일 | SHA-256 |
|---|---|
| transport/admin_bootstrap.py | e5018dabcb8c2dff99b3365ce8ae7c2ea3dd6e17d8c6de366f97aca0fa320e99 |
| transport/controller.py | 858e9e62bd49e4c57763d23d2a0adab84c51b8a08480d023f5c4a10a4fe5aeb8 |
| transport/state_contract.py | e327704450b29e142334c8d37e53bde4c5fcb3789ae07d9814177e4756cb3cd7 |
| transport/supervisor.py | c3bd19b6ac455089ec1ccee842730a9597ff23a5cb1cba8df8bf585bf44bf29d |
| transport/guardian_driver.py | 1a2ba8b5f66118da8f212178dde9364f141c87a475213fb4728683c86e287a37 |
| transport/remote_admin_entry.py | 7b964579bad40a996c7d079920a5a2b3b1dc1e86c00ba6208ffe17c5c402543e |
| tests/test_admin_transport.py | f9367060faee9892772b1971ae567e20b9b92fc025dfcb54f8ed2e1bf164acfa |
| run_admin_simulation.py | 5fa217cfb84dede39670d1e12ee82cf6087a9ddb6d89a506b657de6966f2cd30 |
| prepare_packet.py | 8d3f6ef00e0bc401a16a74020193b52ccbebdcb6ef9890dd5b9900bc6cb4205e |
| target_protocol.json | 996d102f86b42acffcc5217fb7523e4aa93d8544f30bd665eea3963d8f1733f7 |
| budget_protocol.json | 16db1a2dae38d2fc9d5713e9340b966257611da49ae6856529d9e59d7f126f43 |
| 원본 guardian.py | 2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802 |
| 원본 offline_budget_amendment_52763685.json | daa8ec8f9b73deb3f5d212841372725aac522cc1154eb385766b7744d4a54173 |

## 후속 수정본 검토 1

최초 두 지적의 수정은 실제 코드로 확인했다. controller568행이 승인된 running 인수 직후 STOP 책임을 잡고 672–690행이 supervisor 원본 영수증 부재/미확인 시 기존 confirm_stop을 재사용한 exactID stop fallback과 별도 controller_fallback_final을 기록한다. bootstrap89–92행이 현재 pinned protocol의 approval_reference/human_approval_text/scope/B95/A320를 정확히 대조하고 supervisor104행도 현재 승인 참조를 검사한다. 새 NO controller 시험은 같은 method 안에서 정상·Popen 실패·ready wrongID·supervisor exited를 각각 다루고 시험 정의 수48은 유지한다.

그러나 새 fallback에 기존과 같은 actual-only 반례가 재도입됐다. `FallbackControl.show`(682행)는 `transport.show('final_instance')`를 그대로 반환한다. final role은 actual=exited/intended=running을 STARTING으로 정상 분류하지만 원본 confirm_stop은 actual만 보고 STOP_CONFIRMED를 반환한다. closure의 마지막 STOPPED 요구는 거짓 완료를 막지만 controller_fallback_final이라는 중간 종료 영수증이 거짓 STOP_CONFIRMED가 될 수 있다. 기존 CheckedCli처럼 STARTING을 거부하여 raw confirm_stop에 넣거나 exactSTOPPED 조건을 연결하고 인수 실패+queued 반례를 추가해야 한다.

또 새 승인 연결 반례505행은 실제 datetime을 사용하고 auth()의 고정 expires_utc=2026-10-09T12:15:00Z를 물려받는다. 그 시각 이후에는 intended CURRENT_HUMAN_APPROVAL_EXACT_LINK_REQUIRED보다 ADMIN_APPROVAL_TIME_INVALID가 먼저 발생해 시험이 허위 ERROR가 된다. 해당 반례에 승인 시간 범위를 상대 현재 시각으로 명시하거나 fake clock을 patch해야 한다. 기존 full Transport fixture의 fake clock과 달리 이 호출에는 patch가 없다.

따라서 이 수정본도 **UNRESOLVED**이며 위 반례를 구현자에게 즉시 보고했다. 네트워크·동적시험·서버행동0, 이 문서 외 수정0 유지한다.

| 후속 수정본 입력 | SHA-256 |
|---|---|
| transport/controller.py | af04ddc5efb77a0c7535b59d2cbf237d1f0add65325162ab3865c106b1ab9b9e |
| transport/admin_bootstrap.py | 272dc670f39c34b534bb94c0552708c465f6fdebfb8530d7b2030d42688e665d |
| transport/supervisor.py | 9a37827f788f66c5f13211fc2d471ab514c6b33ef740ffae596010feaffc6d6d |
| tests/test_admin_transport.py | ff203fa1234415f96a6338040e815bee5eda78cf701b1f1ea35f9d93d08c0c23 |

## 후속 수정본 검토 2 — 실행 전 소스 검토 결론

추가 두 지적도 최신 소스로 확인했다. FallbackControl.show는 STARTING을 명시적으로 거부한다. 새 no_fallback_queued_exit 반례는 Popen 실패 이후 stop 응답이 actual=exited/intended=running이어도 STOP3회를 거친 controller_fallback_final=STOP_UNCONFIRMED와 closure.actual_stop_confirmed=false를 요구한다. 새 승인 참조 반례의 bootstrap datetime은 기존 Clock로 patch되어 고정 만료 시각의 비의도 ERROR를 피한다. 기존45개는 변경하지 않은 ES fixture·일관된 fixed profile·같은 외부 mock 경계를 사용하며 추가 내용은 기존 NO3개 method 안의 반례이므로48개 정의는 유지된다.

**최신 소스의 이 별도 정적 검토에서 발견했던 차단 결함은 해결된 것으로 확인했다. 새 확정 BLOCKER는 발견하지 않았다.** 앞의 UNRESOLVED는 해당 이전 입력 해시에 대한 역사적 판정이며 덮어쓰지 않는다. 이 결론은 실행 허가·READY 봉인·ADMIN48개 통과·독립 인증이 아니다. 후보 ZIP/record/final 승인서의 생성 후 실제 bytes 연결, 최신 provider 비용 원장, NO outer supervisor→guardian ARM→회수→STOP와 외부 실제 stopped는 실행 준비/실행에서 확인해야 한다. 현재 단계의 동적 결과는 계속 미확인이다.

STOP fallback은 남은590초 경계 내에서 기존 confirm_stop을 재사용하고 미확인 종료를 UNRESOLVED로 남긴다. supervisor 대기가 전체 종료 여유를 소모하거나 실제 외부 API/호스트 자체가 응답하지 않는 경우 자동으로 성공하지 않는다. 그러한 종료 제어 장애의 외부 실제 확인과 STOP 우선 대응은 정적 모의 결과로 대체할 수 없다.

읽기 전용 청구 준비 스크립트의 타입 가정 실패/CLI 날짜 기본값 오류는 구현자가 전달한 보존 사실이며 이 검토자가 실행·원본 대조하지 않았다. 시험 실패나 성공으로 집계하지 않고 실제 시험의 raw 원장과 별도로 유지해야 한다.

| 최종 소스 입력 | SHA-256 |
|---|---|
| transport/controller.py | 5ddf91ed03e1abc011944dfd848de12b2bc640446dfcd0174ca6336291e579ef |
| transport/admin_bootstrap.py | 272dc670f39c34b534bb94c0552708c465f6fdebfb8530d7b2030d42688e665d |
| transport/supervisor.py | 9a37827f788f66c5f13211fc2d471ab514c6b33ef740ffae596010feaffc6d6d |
| transport/state_contract.py | e327704450b29e142334c8d37e53bde4c5fcb3789ae07d9814177e4756cb3cd7 |
| transport/guardian_driver.py | 1a2ba8b5f66118da8f212178dde9364f141c87a475213fb4728683c86e287a37 |
| transport/remote_admin_entry.py | 7b964579bad40a996c7d079920a5a2b3b1dc1e86c00ba6208ffe17c5c402543e |
| tests/test_admin_transport.py | e25bc24820c23a86d445bb68fbc73e1aa26f9901406ed055b1f9d5ec03808848 |
| run_admin_simulation.py | 5fa217cfb84dede39670d1e12ee82cf6087a9ddb6d89a506b657de6966f2cd30 |
| prepare_packet.py | 8d3f6ef00e0bc401a16a74020193b52ccbebdcb6ef9890dd5b9900bc6cb4205e |
| target_protocol.json | 996d102f86b42acffcc5217fb7523e4aa93d8544f30bd665eea3963d8f1733f7 |
| budget_protocol.json | 16db1a2dae38d2fc9d5713e9340b966257611da49ae6856529d9e59d7f126f43 |

네트워크·동적시험·서버행동0, 원본 guardian/계산/시험 봉인 수정0, 이 문서 외 파일 수정0. 이 소스 검토만으로 이전 실패 상태나 B95/A320 권한을 바꾸지 않는다.
