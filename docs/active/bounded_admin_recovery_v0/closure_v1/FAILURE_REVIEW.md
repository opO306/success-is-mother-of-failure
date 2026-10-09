# V1 정적 반례 검토와 실행 전 중단 계획

이번 파일의 반례는 코드·원본·AST를 읽어 확인한 중단 경로다. 실제 SSH 실패, Linux 실행, guardian 장애를 주입해 실행한 결과가 아니다. 기존 정책 시험 파일의 95개 결함 주입 사례는 원본 그대로 패키지 B에 포함했으며 이번 단계의 공식 동적 통과 수는 0이다.

| 반례 | 현재 정적 중단 경로 | 미래 실행에서 남길 원본 |
|---|---|---|
| PowerShell→SSH→Python 인용 깨짐 | Python argv 배열, Linux 인자는 shlex.join, 원문 Python은 SSH stdin. 기존 운송의 run/py/upload 본문 AST 보존 | stdout/stderr, 단계·종료 코드·예외 events |
| SSH 접속 실패 | 시험 시작 금지. 재접속·시험 자동 재시도 없음. supervisor가 승인된 인스턴스 정지 우선 | 접속 로그, completion, supervisor/guardian 정지 영수증, final API |
| CONTAINER_ID 누락·중복·비숫자 | /proc/1/environ의 실제 값 없으면 probe 거부 | 로컬 접속 stderr·실제 API 식별. 검증 안 된 게스트에서는 회수하지 않음 |
| 잘못된 서버 ID/machine/국가/SSH | API 정확한 대상 검증 및 게스트 PID1 재검사. 다른 대상 파일 회수·시험 금지 | API 원문, probe stderr, 승인된 서버의 정지 기록 |
| 최초 ZIP·기존 바이트 변조 | 서버 시작 전 정확한 ZIP/inventory/멤버/봉인 핀 거부 | 기존 실패 원본 유지, 로컬 검증 거부 오류 |
| 새 ZIP 누락·여분·잘못된 추가 봉인 | A814 집합=원본813+지정1개 외 전부 거부. B는 별도10개 | 패키지 완전성 원본 및 전후 비교 |
| CRC·중복·case alias·경로 탈출·symlink·암호화 | 모든 멤버의 구조와 raw hash 확인, 검증 완료 전에 추출 없음 | 검증 stderr와 전달본. 원본과 최초ZIP 불변 |
| guardian 시작 안 됨·ARMED 불일치 | supervisor READY 이전 재시작 금지. ARMED 없으면 게스트 시험 금지, supervisor가 정지 | supervisor/guardian 로그, 승인·lease·armed, 외부 종료 영수증 |
| 최초 시계/guardian 마감 불일치 | 절대 handoff=min(400, arm_age+deadline). gate140초+회수96초 예약 없으면 거부 | allocation_start, guardian_lease/armed, DEADLINE 원인 |
| 회수 시간 부족·회수 실패 | 반복 회수·재포장 없음. 확보한 로컬 raw 원본 보존 후 정지. 성공 판정 금지 | 부분 다운로드·회수 오류·정지 기록. 미회수 원본은 미확인으로 보고 |
| pytest 외부 설정·플러그인 주입 | B는 봉인 pytest.ini와 confcutdir, PYTEST_ADDOPTS/PLUGINS 제거. A의 동결 실행기는 변경하지 않고 게스트 상위 pytest 설정 발견 시 거부 | 설정 거부 stderr, 환경·버전 영수증 |
| CPU/wall/RSS 초과 | B120초 CPU/wall·512MiB AS·1 affinity, 프로세스 트리 감시와 child process-group 종료. A는 기존 봉인된 제한 그대로 | guard/status/JUnit/자원 원본. OS 권한 격리·실시간 집행 정확성은 실행 검증 대기 |
| 95개 정책 시험 실패/수 불일치/skip | B STOP. A 자동 실행 경로 없음. 별도 A 승인도 완료 B95 원본 없으면 거부 | B JUnit·guard·status·회수SHA·실제 stopped |
| 320개 일부 재사용·중복·실패 | 과거 실패 JUnit의 정확한 고유320 ID 집합과 새 JUnit 비교. 실패하면 benchmark 미실행 | 새 전체 JUnit·guard·status. 과거239 통과는 합산하지 않음 |
| 계산·수치·서명·증거 변조·종료 오류 | 기존 planning 정책 REFUSED, 신규 운송은 자동 복구나 재시험을 구현하지 않음 | 해당 실패 원본·FAILED/DEADLINE·종료 미확인 시 UNRESOLVED |
| 두 새 승인창의 예산을 별개로 늘림 | 합계 상한 $0.05도 고정. B최초시계 비용상한+.25×600/3600이 .05 초과하면 A재시작 전 거부 | Bclosure의 할당시간·보수적 비용상한과 A거부 오류 |
| 기존 종료 창·실패3회를 리셋 | 새 승인에 과거 admin3·tablet gate1·각 CLOSED 해시 바인딩. 과거창 복구 권한 없음 | 원본실패3회/320/종료 영수증과 새 승인 별도 |
| 종료 상태 확인 실패 | STOP_REQUEST를 성공으로 처리하지 않음. STOP_CONFIRMED 영수증과 final actual=exited/stopped 둘 다 요구 | 외부 guardian/supervisor 결과와 final API; 없으면 STOP_UNCONFIRMED/UNRESOLVED |

## 준비 중 발견하여 수정한 결함

별도 검토자가 B 초기 하네스에서 세 가지 결함을 찾아 정적으로 수정했다. (1) 전체 최초 시계만 보고 guardian의 실제 상대 마감이 빠른 경우를 놓침: arm_age+deadline에 시험·회수 예약을 결합. (2) pytest 환경·상위 설정의 개입: 환경 제거와 봉인 설정을 명시. (3) child 생성 전 감시 스레드가 실패하면 child가 남을 수 있음: 동기 사전 검사 뒤 child 생성, 즉시 감시 시작과 finally 종료. 초기 B ZIP과 B_v2 ZIP은 별도 초안으로 보존했고 최종 대상은 B_v3다.

새 운송에서 네 번째 결함도 발견했다. controller는 package_closure_ 경로를 만들었지만 raw 재사용 probe는 tablet_v0_만 허용했다. 새 controller의 경로를 tablet_v0_a/b_<run_id>로 맞추고 교차 파일 정적 확인을 추가했다. 기존 probe 원본은 수정하지 않았다. 이전 운송 봉인·승인 초안·정적 검사 결과는 transport_draft_v1에, 다음 중간 봉인은 transport_draft_v2에 보존한다. 이 초안들은 실행 대상이 아니다.

별도 검토자의 AST 사례 수 계산 보조 코드에서 BinOp에 literal_eval을 적용한 오류 1건이 있었고, 실행 없이 AST 리스트 길이 분석으로 고쳤다. 주 구현자의 patch 도구도 줄 위치 불일치로 1회 거부됐고 해당 호출에서 파일은 변경되지 않았다. 이 두 건은 프로젝트 시험이나 유료 실행 시도가 아니다. 이전 admin 실패3회와 최초 실제320 실패 기록은 계속 유지한다.

최종 정적 확인에서도 로컬 stdlib 검사 오류 1건이 났다. 합산 비용 관문을 show에 추가한 뒤 검사기가 여전히 old show와 AST 동일성을 요구했다. static_review_failure_1.json에 보존하고, 실제로 원문을 재사용하는 run/py/upload와 의도적으로 보강한 show를 구분하도록 정적 확인을 수정했다. subprocess.TimeoutExpired가 일반 TimeoutError의 하위 형식이 아니라서 DEADLINE 대신 FAILED로 기록될 수 있다는 별도 검토 지적도 반영했다. 실행·정지 동작을 실제 시험한 결과는 아니다.

## 검토의 한계

관련 소스 AST에서 파일 접근 표현194건, 선언된15개 실행 봉인, 추가 조사한 역사 원본99개와 signed raw 참조74개를 확인했다. 실행 중 만들어지는 모든 파일 경로를 발견했다고 주장하지 않는다. 서명 자체 검증은 기존320 시험의 실행 대상이다. 합성 fixture의 VERIFIED JSON은 실제 외부 검증자·권한·서명을 증명하지 않는다. 미래의 1회 복구 실행기, 외부 예약 원장, 독립 영수증 인증은 별도 구현·승인 대상으로 남긴다.
