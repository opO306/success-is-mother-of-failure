# 첫 후보 코드 별도 검토 — 미해결 결함

검토자 `/root/state_contract_reviewer`. 이 검토는 실제 새 코드와 반례 시험 파일을 읽은 정적 동료 검토이며 독립 인증이 아니다. 모의 실행을 포함한 동적시험, 네트워크, SSH, 유료 API는 수행하지 않았다. 이 파일만 작성했다. 아래 행 번호와 해시는 **첫 후보 스냅샷**의 것이다. 후속 수정이 있으면 새로운 검토와 해시가 필요하다.

| 파일 | 검토 스냅샷 SHA-256 |
|---|---|
| `transport/controller.py` | `c6bec2b544b7ee13da6725385811b2f5894d3f16d5ccdad58a7b7bb5f112976d` |
| `transport/state_contract.py` | `93fea6ce3114e0a10a41c80d8bb8513157a572dc9cc226742131495948faee3d` |
| `transport/supervisor.py` | `55b0fee869b68221ca3401039122e1438987afbf4afe41cc6126c908589ac005` |
| `transport/guardian_driver.py` | `ef5be0e908c2f19d28f7bd78628724237559e14654eeb34c1fd1a816dad0c784` |
| `tests/test_admin_transport.py` | `4cf1f012e68f499d70ae1c7dfa72dd2674bd0c811983f22f36df3717102c8fdd` |
| `prepare_candidate.py` | `5038ac7cf051a1435ace2be8cdee4964040875f09da129401b9a4b1b4d3f1e5f` |

## 발견한 준비 차단 결함

1. **실제 STOP 판정에 STARTING이 통과한다.** state_contract31–35는 exited/intended=running을 STARTING으로 분류한다. CheckedCli72–74는 guardian_observe로 이를 허용한 raw를 그대로 반환한다. 변경하지 않은 guardian confirm_stop52와 후보 supervisor24는 actual=exited만으로 STOP_CONFIRMED를 만든다. controller의 최종 복합상태 확인이 이 오류의 일부를 막더라도 guardian·supervisor 영수증 자체는 거짓 정지확인이 될 수 있다. CheckedCli의 종료 관찰에서 STARTING을 완료로 공급하지 않도록 보류/거부하고, 실제 confirm_stop 코어와 두 main 경로에 queued 상태 반례를 넣어야 한다.
2. **모의 subprocess 경계가 실제 코드의 PIPE 상수를 빠뜨렸다.** tests120 Backend.shim은 run/Popen/TimeoutExpired/Windows 상수만 제공한다. controller347은 Python source 입력을 보낼 때 subprocess.PIPE를 읽으므로 정상 probe부터 AttributeError가 예상된다. 실제 경계가 사용하는 상수를 모두 제공하는지 정적으로 대조해야 한다. 이는 정적 발견이며 실제 시험 실패 재현은 아직 하지 않았다.
3. **명령 성공 직후의 제어 상실을 다시 검사하지 않는다.** controller356 communicate가 반환하면 곧바로 break한다. 마지막 evidence download가 성공한 순간 guardian final 또는 completion marker가 생겨도 run은 성공으로 돌아가고 execute599–603은 결과 검증 뒤 COMPLETED로 설정할 수 있다. 최종 API와 stop 영수증까지 정상이면 제어 상실을 무시한 완료 승격이 가능하다. communicate 성공 후 제어·시계·마감 재검사와 마지막 회수 성공 중 marker 발생 반례가 필요하다.
4. **늦게 발견한 시계 오류가 완료로 승격될 수 있다.** finally640에서 fault를 검사한 다음 cleanup_age644와 measured_clocks647이 fault를 새로 설정할 수 있다. 최종 API 이후 처음 drift가 관측되면 trigger=COMPLETED를 유지한 채 clock_fault=ALLOCATION_CLOCK_DRIFT인 closure와 policy_completion이 생성될 수 있다. 마지막 클록 관측을 먼저 수행하고 그 결과로 완료 판정을 고정해야 한다. final API 뒤 처음 발생하는 drift 반례가 필요하다.
5. **Windows에 Linux식 신호 없는 PID 조회를 가정했다.** controller332와 prepare_candidate60의 os.kill(pid,0)은 Windows에서도 안전한 생존 조회라는 근거가 없다. 구현자도 이미 이 가정을 발견했다고 전달했다. 이 코드는 그대로 유료 실행 후보에 포함하면 안 된다. psutil 기반 조회를 채택한다면 모의 경계도 그 실제 의존성을 연결하고 PID 재사용·zombie·권한거부 처리와 한계를 명시해야 한다.

## 시험 범위의 공백

- tests229는 supervisor/guardian main 직접시험을 나중에 추가한다는 주석이다. 현재 SupervisorBoundary는 실제 supervisor.main을 대신해 guardian lease/armed를 직접 만들며 wait151–160에서 confirm_stop만 직접 호출한다. 따라서 현재 전체 execute 시나리오는 실제 supervisor.main과 guardian_driver/main의 연동 검증을 대신하지 못한다.
- Backend75–86은 guest_probe/source_verify/gate/recover를 실제 실행하지 않고 응답이나 예외를 직접 만든다. container_mismatch와 ZIP 오류 시나리오는 **controller가 그 응답/오류를 받았을 때 중단하는 시험**이지 게스트 스크립트가 실제 PID1/ZIP 반례를 거부하는 시험이 아니다. 실제 게스트 검증 코드를 격리된 파일/환경 경계로 시험하거나 미확인으로 명시해야 한다.
- supervisor.confirm_stop 기본 now/sleep은 함수 정의 시점에 바인딩된다. supervisor.main 직접시험에서 module.time만 가짜로 바꾸면 기본 인자는 실제 시계/대기를 계속 사용할 수 있다. 실제 코어를 실행하면서 시간 경계를 올바르게 주입해야 한다. 원본 guardian 코어도 같은 형태다.
- tests의 guard_lost_during_gate는 가짜 communicate가 gate count를 늘리기 전에 final을 만들고 TimeoutExpired를 낸다. 현재 동작은 그 뒤 stop check에 의해 탈출할 수 있으나, 실제 gate 시작 후 guardian 종료·명령 kill·추가 gate0을 입증하는 반례도 필요하다.
- status/JUnit 모의 자료는 TEST_ONLY라고 명시돼 있으나 실제 B95 원본의 정확한 사례 ID는 시험하지 않는다. transport 결과 검증의 합성자료를 실제 B95 완료 영수증이나 별도 A 승인 근거로 사용하면 안 된다.
- readiness 검사199–207과 main681의 실제 승인/봉인 경로는 execute 시나리오가 직접 우회한다. 새 준비봉인이 아직 없는 현재 동작은 유료 B 실행 거부여야 하며 false 승인·누락 readiness·바뀐 봉인·이미 존재하는 run root의 실패를 별도 확인해야 한다.

## 긍정적으로 확인한 정적 변경과 남은 조건

실제/요청 복합상태를 분리했고, stopped에서 포트를 요구하지 않는다. restart의 running 포트 누락은 준비되지 않음으로 돌려 제한 대기를 가능하게 했으며, 명시적 연결 불일치와 여러 다른 포트 혼합은 거부한다. controller control은 API 전후 제어를 재검사한다. 새 guardian_driver는 기존 guardian 원문을 hash 검증하고 CheckedCli만 연결하며 기존 파일을 수정하지 않는다. 그러나 위 차단 결함과 main·게스트 검증 경로의 공백 때문에 현재 후보를 STATIC_READY나 ADMIN_TRANSPORT_SIMULATED_VALIDATED로 판정할 수 없다.

실제 STARTING 원본은 계속 UNCONFIRMED이다. 원본 guardian의 DEADLINE marker 처리와 fallback FAILED trigger 차이, 실제 OS 장애·PID 재사용·SSH와 API 사이 원자성, 개별 실청구 확인도 별도 한계로 남긴다. 모든 수정 후 전체 관련 영향 시험의 원본과 별도 후속 검토가 필요하다. 기존 봉인·실패·B95/A320·계산식·서명 권한은 유지해야 한다.
