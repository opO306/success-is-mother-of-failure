# 유료 행정 시험 전 별도 정적 검토

검토자 `/root/state_contract_reviewer`. 새 admin_bootstrap, remote_admin_entry, prepare_packet, controller.execute_payload 분리, supervisor/guardian 연동, 42개 모의 case와 runner를 실제로 읽었다. 네트워크·서버 조회·SSH·모의 동작을 포함한 동적시험은 실행하지 않았다. 이 파일만 작성했다. 동료 검토는 독립 서명 인증이 아니며 B95/A320 승인이나 통과 영수증을 만들지 않는다.

| 검토 스냅샷 | SHA-256 |
|---|---|
| transport/admin_bootstrap.py | `f19accd95194423f03701ef64a1d640bcb43b9a5a11501fd89a04b83243aa37c` |
| transport/remote_admin_entry.py | `81a9c2ddce538b1304da6fdaffa191e90e0c43b92092d14494441a92d60c12d9` |
| transport/controller.py | `6c7f91027cdacf8d6c320e28b3ff2e30d0071630ed32ba84269973dc3ad35564` |
| transport/supervisor.py | `55b0fee869b68221ca3401039122e1438987afbf4afe41cc6126c908589ac005` |
| transport/state_contract.py | `a361141a27af264e955fdf28610d5a94722996a5ab58dabb00ac5a87da02cb20` |
| transport/guardian_driver.py | `1a2ba8b5f66118da8f212178dde9364f141c87a475213fb4728683c86e287a37` |
| tests/test_admin_transport.py | `5bcf56adf5493ad291ed5c7fbd9156544eda96fdd93177f39321b876913a6dd9` |
| run_admin_simulation.py | `f894920211e68345cf19303153554fb4c8d1a9cd2fdd9b2a46b87f05d04d3e63` |
| prepare_packet.py | `fe6187c3584e9383c0802e89edad0af6c2a7db3935beb0be3588443a5b38092e` |
| prepare_candidate.py | `a65ef9a335c148a4714af0e6f419974a9d8050510466b60cd73b95df083fcf96` |

행 번호는 위 스냅샷 기준이다. 후속 수정은 새 hash와 검토 범위가 필요하다.

## 실행 전 해결할 결함

### 1. 게스트의 ADMIN 승인·armed·최초 시계 검사가 빠짐

admin_bootstrap16–18은 admin_ticket와 armed를 전달하지만 remote_admin_entry는 두 파일을 전혀 읽지 않는다. PID1·Python·ZIP/hash·경로 확인 후 runner를 호출한다. 원본 guest_gate23–34에 있던 ticket/armed hash·ID/machine/country/approval_reference·최초 할당 시간과 실행/회수 여유 재확인을 새 행정 entry에서 누락했다.

행정 payload가 물리 계산이나 B95/A320을 실제 호출하지 않는 것은 정적으로 확인했다. 그러나 ADMIN 시험도 승인된 원본·최초 시계·종료 여유에 묶여야 하며, 사후 회수 시 admin_ticket/armed raw를 비교하는 admin_bootstrap33–35는 실행 전 관문을 대신하지 못한다. 전달한 ticket/armed의 SHA 핀을 entry args로 보내고 ADMIN 전용 schema/scope/실행권한·ID·핀·최초시계·120초 실행 및 회수96초 여유를 runner 시작 전에 검사해야 한다. 잘못된 ticket/armed 또는 부족한 시간을 넣었을 때 runner 호출0인 직접 반례가 필요하다.

### 2. B의 현재 예산 원장이 과거 값으로 덮임

controller215–227은 새 ledger의 conservative_spent_bound_usd를 검사하지만 241행에서 PRIOR_POLICY_FEE_BOUND를 오래된 target의 prior_B_fee_bound와 preparation_fee_reserve 합으로 덮어쓴다. 행정 시험의 새 비용을 포함한 current ledger를 전달해도 이후 show의 잔여 예산 검사와 closure 비용 기록에는 과거 낮은 값이 남을 수 있다. 이번 ADMIN bootstrap은 별도 spent를 유지하지만 향후 B 승인 경로의 공유 결함이다.

current spent와 과거 보존 bound의 관계를 명확히 정의하고 최소한 더 큰 값을 보존해야 한다. 실제 최신 원장의 핀·출처를 유지하며 값을 초기화하거나 이전 실패 비용을 지우면 안 된다. 과거 bound보다 큰 current spent를 넣은 반례로 closure/show에 그 값이 이어지는지 확인해야 한다.

## 새 행정 실행 경로의 시험 공백

42개 execute 모의 case는 controller.Transport의 합성 B payload를 시험한다. 새 AdminTransport.execute_payload/validate_result/preflight와 remote_admin_entry 경로 자체는 아직 시험 목록에서 직접 호출하지 않는다. 기존 guardian·실제 guest wrapper를 직접 시험한 것은 의미가 있지만 신규 행정 bootstrap의 시작/회수/authority 오류를 그 시험으로 덮을 수는 없다.

실제 AdminTransport의 정상 회수와 잘못된 admin_ticket/armed, entry timeout/자원값/ID 불일치, 반환 role 오류, JUnit 부족·중복, false ADMIN 승인·손상 candidate 입력·불충분 예산을 직접 격리된 경계에서 검증하는 추가 case가 필요하다. 반례 추가로 expected 숫자가 변하면 입력 record와 계획 숫자를 정확히 연결해야 한다. 기존 B95/A320 시험을 바꾸는 작업은 아니다.

## 정적으로 확인한 수정과 연결

- SIGALRM/SIGXCPU를 KeyboardInterrupt로 연결하고 unittest가 보유한 부분 result 객체를 finally에서 회수한다(runner22–24,66,72–79). 강제 SIGKILL·CPU hard limit·메모리 실패에서 Python finally가 반드시 실행되는 것은 아니므로 외부 entry/STOP/부분 원본 영수증은 계속 필요하다.
- 초기 생성기는 __main__에서 RETIRED_INITIAL_BUILDER_DO_NOT_RUN으로 종료한다(prepare_candidate16). 이전 결함 생성 본문은 그 아래 불변 역사로 남으며 활성 재생성 경로가 아니다.
- Windows 생존 관찰은 신호 호출 없이 psutil is_running/status다. NoSuchProcess/AccessDenied는 생존 근거로 쓰지 않고 거부한다. 실제 Windows 프로세스 정체성·PID 재사용을 인증한 것은 아니다.
- CheckedCli는 최초 guardian 관찰과 종료 관찰을 구분하고 STARTING을 raw confirm_stop 완료 조건에 공급하지 않는다. supervisor는 원본 guardian 대신 hash 검증한 guardian_driver를 실행해 원본 main에 CheckedCli를 연결한다. supervisor fallback도 같은 CheckedCli를 사용한다.
- actual supervisor/guardian main 모의 시험은 confirm_stop 기본 시계를 명시적으로 fake now/sleep으로 교체한다. import 시점 기본함수에 실제 대기가 남는 문제는 해당 case에서 피했다.
- prepare_packet은 repo 상대 경로로 기존 B ZIP·inventory·source seal·정책 seal·guardian/a_safety·기존 실패·원래 controller/bindings/승인 원본과 새 모의 코드를 포함한다. controller HERE.parents[4]와 BASE.parents[3]이 기대하는 repo mirror 깊이와 일치한다. 실제 원격 배치·의존성은 여전히 실행 검증 전이다.
- entry는 affinity1을 상속시키고 주소공간512MiB, CPU soft119/hard120, parent/child CPU·RSS 표본을 합산해 wall/CPU120·메모리 상한에서 중단한다. 최종 CHILDREN rusage도 기록한다. 짧은 프로세스의 메모리 피크와 OS 강제 종료 전체를 인증하는 cgroup 격리는 아니다.
- admin preflight는 finite/nonnegative spent 및 캠페인 $0.10과 추가600초 최대비용을 검사한다. provider 실제 요금·출처·남은 예산을 독립적으로 다시 계산하는 함수는 아니므로 최신 raw ledger 검토가 외부에서 실제로 수행돼야 한다.
- ADMIN KIND은 최종 B policy_completion 분기를 실행하지 않는다. admin_result_verified도 B95_passed/A320_passed=False로 기록한다. synthetic 승인/영수증은 TEST_ONLY로 회수되며 실제 A 승인 근거가 될 수 없다.

## 미확인과 판정

이 검토에 동적 PASS는 0이다. 새 행정 entry의 승인/시계 관문 누락과 현재 ledger 전달 오류를 해결하고 추가 행정 경로 반례를 준비하기 전에는 실행 준비가 완료됐다고 판정하지 않는다. 실제 STARTING 원본, 실제 OS/SSH 장애, 자원 강제종료 뒤 부분 원본 보존, 실제 guardian·supervisor의 provider 상태 연동, 개별 실청구는 미확인이다.

기존 실패·ZIP·guardian 원본·B95/A320·물리/수치식·서명 권한·기준선은 수정 대상이 아니다. 사용자의 유료 행정 시험 허가와 향후 별도 B/A 승인을 구분해야 한다.
