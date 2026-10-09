# V12 최소 운송·최종 회수 구현 계획 — 새 유료 실행 승인 전

사용자 V12 원문은 attachment ba842e21-e181-485f-a31d-d74067151c39다. 구현 승인과 새 유료 실행 승인을 분리한다. A320·검색 완료가 목표이며 B95 재실행은 하지 않는다. V1–V11/과거 실패/계산기/320항목/판정/검색 계약/누적 장부는 보존한다. LOCAL FULL 및 사용자 로컬 프로젝트 동적 시험은 금지다.

| A–H | 실제 근거·반례·구현 경계 |
|---|---|
| A 목적/대안 | V10 partial180점, 완료JUnit 없음, snapshot 뒤 STOP/삭제 결함. 단순 SSH 재접속만으로 writer 종료는 증명되지 않는다. 기존 Transport/guardian/watchdog를 유지하고 짧은 작업 wrapper의 launch/status/recover만 추가한다. 별도 상주 기관은 없다. |
| B 가정 | Linux /proc, PID1 CONTAINER_ID, PID+startticks+bootID, prctl subreaper 가능 여부는 원격 NOT_TESTED. 실행 코드·wrapper를 봉인하며 wrapper 기능 거부면 A 시작 금지. PID 숫자·SSH exit만으로 종료 판단 금지. |
| C 반례 | launch 응답 유실·PID 재사용·다른job terminal·live child/setsid child·zombie·완료파일누락·byte-validpartial·조회불능·snapshot 후작성·해시변조→중복 launch 또는 자동삭제 금지. |
| D 영향 | campaign.stage→remote admin→새 wrapper launch/status→회수 gate→Transport.execute/execute_payload→recover→lifecycle.verified_recovery→terminal_proof 정상판정 또는 별도 실패회수판정→cleanup.close_owned→직접destroy/outerfinally/watchdog→기존 SETTLE. 직접·예외·시작·종료 관문 모두 실제 소스 별도 검토한다. |
| E 원인/검토공백 | V10 run_once RPC 종료를 payload 종료로 혼동했고 guest_recover.rglob snapshot SHA를 최종성으로 승격했다. 기존 모의에는 실제 child가 SSH보다 오래 사는 반례가 없었다. 정확한 이전SSH 종료 원인은 UNCONFIRMED. |
| F 증거 | V11 기존10시험 먼저 원격 실행, 영향 회귀·실제 동일 wrapper 프로세스/세션단절/하위writer시험 후 A320. 최종job terminal·PID/startticks·boot·빈하위writer·원격두inventory·ZIP/local SHA·원래320JUnit/guard/status/benchmark를 결합한다. 정적준비와 실제통과 분리. |
| G 미확인 | V10 삭제 이후 파일존재 UNKNOWN/복구불가. 신규wrapper의 Linux실제동작 미시험. root권한 악성프로세스/OS독립인증 아님. 사용자 최신 정정으로 개별반복 저장 요구 철회·보충93회 금지. 원래100/1000/10000각31회 루프·집계·완료만 검증하며 개별값 확인 주장을 하지 않는다. 원문은 revision_v12/search_contract_amendment.txt에 보존한다. |
| H 권한/비용 | 구현 허용. 새 임대 전 실제목록/요금/장부 재조회와 최대1800초·총$2·예약최대$0.20·행정시험→A3201회→회수/STOP/안전삭제 범위를 한 번 묶어 승인 요청한다. 과거40분 승인 전용 금지. B95 재실행/GPU/새물리/push/merge 없음. 원본미확인은STOP보존·유한보고, 손실승인 없음은삭제불가. |

변경 영향: Transport 동기 gate 호출을 launch/poll로 바꾼다. launch consume 전 원격쓰기 표식과 exclusive job claim, 응답 유실은 같은 job status 조회만 허용한다. wrapper는 subreaper로 하위작성자를 기다리고 제한 넘으면 stable identity로 종료하며, 원래 guardian의 절대시간도 유지한다. 성공/실패 terminal 원자쓰기 뒤 wrapper 실제종료와 자식 부재를 관측한다. 회수 packer는 종료된 작업만 final manifest를 만들고, 임시파일을 최종파일로 보지 않으며 전체 파일 집합·원문을 재확인한다. 정상판정은 기존 require_terminal 기준 유지; 실패종료 회수는 별도 등급으로 성공승격 금지. 미확인 writer는 원격partial회수만 허용/자동삭제 금지.

자기반박: /proc 관측 단독으로 악성 root가 탈출하지 않았다는 OS증명은 없다. 허용된 원래 코드와 wrapper 하위프로세스 경로를 읽고 subreaper+terminal+PID start/boot/집합을 결합한다. 이 근거가 깨지거나 terminal이 없으면 최종회수·삭제를 거부한다. 아직 동적 입증하지 않았으므로 STATIC_READY가 실험통과를 뜻하지 않는다.

실제 소스 호출 경계: campaign.main→source_preflight/로컬 도구 사전 확인→고정 승인 소비→stage(직접 진입도 봉인 policy·장부·키·B 원본 확인)→watchdog→준비 재접속/전달→remote_admin→Transport.run_remote_job→guest_job.launch/run_job/observe→recover_final→guest_recover→job_proof.closed_archive. 같은 경로로 순수 관리 SSH 단절 probe를 수행하며 두 작업의 전체 원본도 verify_admin 삭제 관문에 포함한다. pytest fixture 심볼릭 링크는 ADMIN_TESTS의 지정된 임시 경로에만 한정해 링크 문자열을 manifest에 보존하고 따라가지 않는다. 실제 연구 경로의 링크는 회수 거부다.

A 실행은 기존 ARM→guest_gate→원래 offline gate 한 번→guest_job terminal→recover_final→validate_result/verified_recovery→terminal_proof다. 실패한 프로그램의 작성자가 모두 종료됐고 존재 파일 전체를 회수했으면 CLOSED_FAILED_JOB로 보존하며 PASS로 승격하지 않는다. main 예외·Transport 예외·finally·독립 watchdog 모두 원래 STOP/close_owned→verify_startup/verify_admin/verified_recovery→destroy_with_disposition→실제 목록·볼륨→SETTLE로 연결된다. 확인 불능은 정지 보존·요금 보고이며 새 서버를 자동 임대하지 않는다.

행정 대응: 준비 지연·전달·상태 조회·최종 회수 연결 오류는 동일 서버/작업/절대시간 안에서 유한 재검증하며 같은 원인 최대3회다. 세션 유실 때 새 A320 launch를 하지 않는다. 코드 수정이 필요한 수집/설치/경로 문제는 실패 원본과 봉인을 보존한 별도 버전을 사용하며 같은 승인 창을 다시 시작하거나 예산 예약을 초기화하지 않는다. 안전 관문 실패를 일상 연결 오류로 분류해 재실행하는 경로는 없다.

보완 범위와 한계: PID1·키·종료 통제를 다시 확인한 빈 준비 폴더 생성과 준비 로그 읽기도 최대3회/같은 짧은 기한으로 재확인한다. guest_source_verify의 원본 추출은 아직 동기식이다. 그 연결이 끊기면 이전 추출 작성자의 상태가 불명확하므로 추출을 중복 실행하지 않고 STOP/부분회수/보존으로 간다. 이것은 모든 행정 오류가 자동 복구된다는 구현이 아니다. 실제 장애가 생기면 원본과 작성자 상태를 먼저 조사해 같은 승인 창 안에서 별도 수정 버전을 사용하며, 기준 완화·기존 봉인 덮어쓰기·새 임대 자동 반복은 금지다.

Linux subreaper는 고아가 된 하위 프로세스를 재수집해 종료를 기다리는 수단이다. 커널 문서: https://www.man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html . 실제 후보는 detached group 밖으로 setsid한 하위 작성자도 기다리는 시험 소스를 포함한다. 해당 기능의 실제 원격 통과는 아직 NOT_TESTED다.
