# 별도 읽기 전용 기술 검토의 확인 기록

검토자: 이 작업에서 별도로 요청한 closure_reviewer 에이전트. 작성자가 받은 검토 결과를 이 문서에 보존했다. 외부 서명·권한 인증자가 아니며 새로운 독립 인증 판정은0건이다. 검토자는 프로젝트 import·동적시험·API·SSH·유료작업·파일쓰기를 수행하지 않았다.

## 원본과 패키지 확인

- A ZIP814개, raw48,642,482바이트. 원래813개 경로·바이트 동일, 지정봉인1개만 추가. ZIP/inventory/code/protocol 핀 일치, 구조상 이상0.
- 선언된15개 실행봉인, 필수파일115개, 정적참조3,356건, 역사 원본99개, signed raw 해시참조74건을 대조. 파일 접근 표현194건의 AST 기록은 전체 동적 의존성 증명이 아니다.
- 기존 protocol4/preservation794/code812/운송8/정책16/admin실패34/원격실패89 해시와 범위봉인0701d448 불변.
- package_gate의 main을 제외한 핵심 함수 AST 동일. planning 및 원본95시험을 변경하지 않았다.
- 최종 B_v3 ZIP10개, raw48,965바이트. 기존5개 원본 동일, source seal9개+봉인자체 구성. 17함수의 기대95개는 작성 수이며 실제 pytest 실행0.

## 발견한 결함과 조치 확인

초기 B하네스에서 guardian 상대마감을 충분히 예약하지 않은 경우, 외부pytest 환경·상위설정의 영향, 감시스레드가 child 생성 전 종료하는 순서 문제를 지적했다. 최종 B_v3의 시간예약·환경제거·봉인설정·동기사전검사 후 child 생성과 감시 순서를 다시 읽어 확인했다.

새 운송기가 package_closure_ 경로를 만들지만 재사용 probe가 tablet_v0_만 허용하는 확실결함1건을 찾았다. 첫 접속 검사에서 GUEST_ROOT_SCOPE로 반드시 중단할 경로였다. 새 controller는 최종 tablet_v0_<kind>_<run_id>로 일치하며 probe 원본은 그대로다.

subprocess.TimeoutExpired를 일반 TimeoutError와 별개로 DEADLINE 분류해야 하는 기록상 불일치도 지적했다. 최종 except는 두 형식을 함께 분류한다. 정지확인된 실패는 FAILED, 종료 미확인은 UNRESOLVED다.

## 최종 운송 확인

최종 transport seal SHA:

`e40e3d59d7ee17685631b2a93d96e34d510bfe49779d98b8a1a42fcb6501e802`

봉인9개 raw 해시 불일치0. 기존guardian 핀 일치, seal의 A/B metadata와 package_bindings 동일. supervisor/probe/recover3개는 과거raw와 같다. A320개 ID는 과거 실패JUnit의 고유320 ID 집합과 정확하게 같다.

미승인 템플릿 raw SHA:

- A: `f989f9d8281044534e97f3f1181966164a7c6e0419ac10449e805c1cabff51d8`
- B: `ee2389541ddb53d4ca561267468182015c2886828fd997f1e3abbd57879f379e`

두 템플릿은 exact package·seal·시험수·합계.05 예산을 결합하고 explicit/newwindow/restart/exclusive 모두false다. local_preflight가 API·SSH 전에 승인 확인을 한다. 승인·시간·원본 경로의 실제 거부 동작을 실행한 결과는 아니다.

A 선행receipt는 완료된 B95개 관문, raw hashes, 실제JUnit95고유/실패error skip0, guard0, 자원한도, actual exited/stopped를 요구한다. 자기 작성 원본 회수receipt를 외부 독립 권한 인증으로 승격하지 않았다. A에는 새별도승인이 필요하며 자동진행이 없다.

최초시계는 재시작 전에 생성, supervisor READY를 먼저 확인, guardian ARMED 뒤 전달, 단계마다 시간·대상·감시상태 확인. Python은 SSH stdin, Linux 인자는 shlex.join, 로컬 도구는 argv배열로 전달한다. ID는 /proc/1/environ에서 직접 관측·시험 직전 재검사한다. 실패는 회수1회 후 정지하며 재시험·현장수정 경로가 없다. COMPLETED는 관문·회수 및 외부 STOP_CONFIRMED·actual stopped/exited가 모두 확인된 경우에만 기록한다.

B의 최초할당시계부터 종료까지 elapsed×.25/3600 상한을 A의 선행receipt에서 재계산한다. 초기 읽기전용 API 단계에서 B상한+A600초×.25/3600≤.05를 요구해 재시작 전에 거부한다. B할당이120초보다 길면 현재 A예약은 실행 불가다. 전체청구액·과거 닫힌창 권한을 인증하는 기능은 아니다.

## 남은 범위

새 하네스·운송의 실제95/320/benchmark, 자원집행, SSH/guardian/supervisor의 실행 연동, 회수·실제 종료는 미실행이다. OS격리·외부 독립서명 인증·현장복구 실행기는 미확인 또는 미구현이다. 정적 기술 검토 완료를 원격 성공으로 표현할 근거는 없다.
