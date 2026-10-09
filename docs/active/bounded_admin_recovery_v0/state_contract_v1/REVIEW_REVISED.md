# 개정 후보 별도 정적 검토

검토자 `/root/state_contract_reviewer`. 실제 개정 transport·반례 시험·CPU 모의 runner·기존 생성기를 다시 읽었다. 네트워크, 유료 API, SSH, 로컬/원격 동적시험은 수행하지 않았다. 이 파일만 작성했다. 별도 동료 검토이며 독립 인증이나 유료 실행 승인서가 아니다. 동적시험 결과는 현재 0이다.

| 파일 | 검토 스냅샷 SHA-256 |
|---|---|
| transport/controller.py | `e160c439ceaa54016095046ed215f35f588b32cfe63a3c3e071f493e882d6eb9` |
| transport/state_contract.py | `a361141a27af264e955fdf28610d5a94722996a5ab58dabb00ac5a87da02cb20` |
| transport/supervisor.py | `55b0fee869b68221ca3401039122e1438987afbf4afe41cc6126c908589ac005` |
| transport/guardian_driver.py | `1a2ba8b5f66118da8f212178dde9364f141c87a475213fb4728683c86e287a37` |
| tests/test_admin_transport.py | `5bcf56adf5493ad291ed5c7fbd9156544eda96fdd93177f39321b876913a6dd9` |
| run_admin_simulation.py | `503f07e4a5bbd642f4b73b78a63851efdbec08ffc5bc2a3259a7f0472f884709` |
| prepare_candidate.py | `5038ac7cf051a1435ace2be8cdee4964040875f09da129401b9a4b1b4d3f1e5f` |

## 이전 5개 지적의 수정 확인

- mock subprocess는 PIPE를 제공한다(tests127). 실제 controller354의 Python source stdin 분기가 같은 상수를 사용한다.
- CheckedCli는 초기 guardian 역할을 검사한 뒤 종료 관찰 역할로 바꾸며(state_contract65–83), queued STARTING raw를 confirm_stop에 공급하지 않고 거부한다. stop 요청 시 관찰 역할로 전환하므로 최초 API 실패 뒤 실제 stopped도 확인할 수 있다. 직접 confirm_stop의 queued/machine/API 장애 반례가 추가됐다(tests220–238).
- controller363–365는 communicate 성공 뒤 stop_control_check와 age를 다시 검사한다. 마지막 download 중 marker 경합 반례도 추가됐다.
- 최종 cleanup_age와 measured_clocks가 fault 판정보다 먼저 실행된다(controller649–652). final API 중 늦은 drift를 주입하는 반례가 추가됐다.
- 신호 호출 대신 psutil is_running/status를 사용한다(controller23–27). 모의 경계는 guardian_alive만 바꿔 실제 실행 정책을 시험한다. PID 재사용 등 실제 OS 정체성의 완전한 증명은 여전히 제공하지 않는다.

정상 execute 경로에 대해 외부 fake run/Popen/communicate 경계를 읽어 보았으며, PIPE 누락과 같은 즉시 명백한 정상 분기 오류는 새 스냅샷에서 추가로 찾지 못했다. 이는 정상 동작 확인이 아니라 정적 검토 결과다.

## 새 발견 및 준비 차단 조건

1. **runner의 SIGALRM은 실패 원본을 보존하지 못한다.** run_admin_simulation63은 signal.alarm(110)을 설정하지만 SIGALRM 핸들러를 지정하지 않는다. 기본 동작으로 프로세스가 종료되면 except70/finally71 이하의 status·JUnit·trace 보존을 실행하지 않는다. 승인된 외부 supervisor/runner wrapper가 시간초과 원본과 STOP을 반드시 남기거나, runner가 SIGALRM을 명시적인 TimeoutError로 연결하여 실패를 기록해야 한다. RLIMIT_CPU/메모리 강제 종료도 Python finally를 보장하지 않으므로 외부 영수증은 계속 필요하다. timeout을 정상 합격으로 낮춰 처리하면 안 된다.
2. **생성기와 최종 후보가 어긋난다.** prepare_candidate60은 아직 os.kill(pid,0), 성공 communicate 뒤 검사 누락, late fault 검사 순서 오류를 생성한다. 파일을 다시 실행하면 이전 blocker가 재도입된다. 기존 초안을 불변 역사로 보존할 경우 RETIRED/DO_NOT_RUN으로 명확히 표시하고 다음 실행/재생성 명세에서 제외해야 한다. 생성기를 활성 도구로 유지한다면 최종 후보와 일치하도록 별도 수정·검토가 필요하다. 현재 후보 자체의 수정 확인과 생성기의 안전성은 구분한다.

위 두 조건을 해결하거나 외부 원본보존/사용금지 연결이 실제 코드에 명확히 마련되기 전에는 행정 시험의 준비가 완료됐다고 판정하지 않는다.

## 모의 경계·가짜 시간·경로·권한 검토

실제 supervisor.main→guardian_driver.main→원본 guardian.main/confirm_stop를 호출하는 tests240–289가 추가됐다. Child는 실제 OS 실행을 대체하고, guardian_driver의 load_guardian 경계만 미리 로드한 원본으로 연결한다. CheckedCli는 가짜 CLI만 연결한다. confirm_stop의 import 시 기본 clock/sleep 문제는 timed_confirm/timed_guard에서 명시적으로 fake now/sleep을 넘겨 해결한다. fake module.time만 바꾼 시험으로 끝내지 않는다.

원본 guest_probe·source_verify·gate·recover를 직접 runpy로 호출하는 tests291–359가 추가됐다. probe는 PID1/runtime/mkdir만 가짜로 바꾸고, source verifier와 recovery packer는 TEST_ONLY 디렉터리의 실제 ZIP/해시를 검사한다. gate는 실제 PID1/ticket/ZIP 관문을 실행하되 계산용 자식 프로세스 호출은 가짜로 막는다. 따라서 B95/A320은 실행하지 않는다. 운영 프로세스·실제 서버 ID를 조작해 통과시키는 경로가 아니라 합성 입력의 명시적 경계다.

controller HERE.parents[4], tests/runner BASE.parents[3]은 현재 `repo/docs/active/bounded_admin_recovery_v0/state_contract_v1` 배치와 일치한다. 원격 패키지도 동일한 repo mirror 깊이를 유지하고 B ZIP·inventory·source_seal·기존 실패/guardian/a_safety·승인 원본을 필요한 위치에 넣어야 한다. 실제 원격 파일 배치와 설치 의존성은 이번 검토만으로 확인되지 않는다.

모의 승인 입력은 TEST_ONLY_NO_HUMAN_EXECUTION_AUTHORITY와 SYNTHETIC_INPUT으로 표시되고 synthetic JUnit은 TEST_ONLY_NEVER_B95다. 모의 정책 완료 영수증이 TEST_ONLY_simulated_raw 안에 생성될 수 있으므로 실제 B95 승인·A 관문에 사용할 수 없다는 연결을 결과 봉인에도 유지해야 한다. runner는 B95_executed/A320_executed=False로 구분한다. 실제 유료 bootstrap의 승인·단가·남은 예산·최초시계·STOP·회수 코드는 아직 작성 중이므로 여기서 확인하지 않았다.

## 남은 미확인 및 판정

42개 행정 case는 작성된 시험 계획 숫자다. 실행한 PASS 숫자가 아니다. 실제 STARTING 원본, 실제 Windows psutil 프로세스 식별/OS scheduling, 완전한 통신 장애와 PID 재사용, 강제 자원 종료 뒤 원본 보존, 신규 실행 개별 실청구는 미확인이다. 테스트의 실 I/O/import audit은 읽은 코드의 우발적 호출을 차단하는 경계이며 악의적 native 코드까지 격리하는 OS sandbox 인증이 아니다.

현재 판정은 **이전 지적 5개 정적 수정 확인 / 신규 원본보존·생성기 위험 2개 해결 필요 / 동적시험0 / 새 준비봉인 없음**이다. 이 기록을 ADMIN_TRANSPORT_SIMULATED_VALIDATED나 실제 B95 성공으로 사용할 수 없다.
