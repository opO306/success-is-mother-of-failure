# 경험 탭 V0 행정 운송 정적 준비

이 경로는 봉인된 프로젝트 ZIP 밖의 행정 운송 코드다. 프로젝트 구현·시험·봉인을 바꾸지 않는다. 현재 **ADMIN_TRANSPORT_STATIC_READY / REMOTE_NOT_EXECUTED**다. 준비는 원격 성공, 320개 시험 통과 또는 비용 측정 완료가 아니다.

실행용 행정 봉인은 `transport_seal_v3.json`이다. 이전 행정 봉인 v1/v2와 template은 중간 정적 준비 기록이며 다음 실행에 사용하지 않는다. 최종 템플릿 `approval_UNAPPROVED_TEMPLATE_v3.json`도 모든 승인 값이 false이고 실행 승인서가 아니다. 컨트롤러가 이를 입력받으면 API 호출 전에 거부한다. 이전 실패 3회·종료 기록 해시·새 창의 별도 승인·정확한 서버·600초/$0.05·행정 봉인 해시가 모두 결합된 **새 인간 승인**이 필요하다. 자동 예산 초기화/재시도 없음.

유료 실행 없는 정적 확인 명령:

```powershell
& 'C:/Users/zun24/AppData/Local/Programs/Python/Python312/python.exe' -B 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/static_review.py' --out 'static_review_result_NEW.json'
```

이는 stdlib AST·원문 해시·POSIX 인자 토큰화와 로컬 `ssh-keygen -F` 조회만 한다. controller/guest/guardian을 import하거나 실행하지 않는다. 결과 파일은 새 이름을 써서 기존 검토 기록을 보존한다.

**다음 별도 실행 승인 이후에만** controller를 Python 파일로 직접 실행한다. PowerShell에서 원격 Python 문자열을 구성하지 않는다. CLI 인자는 `--approval <새 승인 JSON 절대 경로> --cli <기존 vastai.exe 절대 경로> --key <기존 SSH 키 경로>`다. 키 내용은 코드나 기록에 넣지 않는다. 현재 준비 작업에서는 이 명령을 실행하지 않았다.

controller는 source/행정 봉인/승인을 로컬 원문으로 먼저 검증하고, 정확한 서버가 stopped/exited인지 조회한다. stopped 대상의 별도 재시작 승인 후 한 번만 재시작하며, 이미 running이면 독점 창을 임의로 이어받지 않고 거부한다. 새 출력 디렉터리와 allocation_start 기록은 배타적으로 만들며 최초 UTC/monotonic 시계를 재시도 때 초기화하지 않는다. supervisor가 시작되기 전에는 재시작하지 않는다.

SSH·SCP는 성공한 A-resume의 subprocess argv/`shlex` 방식과 SCP `-O`를 재사용한다. 길고 중첩된 `python -c` 인용은 제거하고, 검토된 guest 스크립트를 SSH stdin으로 전달한다. PID 1 환경에 실제 ID 하나가 있어야 하며 기대 ID와 같아야 한다. wrapper는 실행 직전 다시 읽은 실제 값만 `CONTAINER_ID`로 전달한다. 게스트 출력 디렉터리·운송 기록·회수 자료는 기존 자료를 덮어쓰지 않는다.

초기 준비 100초, gate 시작 150초, 개별 명령 제한과 단계별 fresh API 검사를 둔다. gate 전 140초 wrapper·96초 회수/API 여유를 확보한다. supervisor는 최초 시계에서 400초에 정지 절차를 시작하므로 420초 회수 마감/180초 확인 경계보다 여유를 둔다. 기존 generic guardian의 ARMED 상대 마감은 초기 조회 12초 등을 감안해 20초 먼저 좁히고, 실제 ARMED 시각과 다시 대조한다. supervisor는 590초까지 정지 확인을 시도하며 controller는 마지막 fresh API 확인을 남은 전체 600초 안에서 시도한다. OS 스케줄 지연·API 장애 때 확정 종료를 보장하지 않으며 `STOP_UNCONFIRMED / UNRESOLVED`로 기록한다.

generic guardian 원본은 수정하지 않고 별도 프로세스로 실행한다. 보조 supervisor의 fallback `Cli`·`confirm_stop`도 기존 guardian의 AST와 동일한 복사본이다. A-resume의 REAL A safety/heartbeat relay는 오프라인 예산과 계약이 달라 재사용하지 않는다. generic guardian은 A 모드의 주기적인 heartbeat/API 확인을 제공하지 않는다. 이 운송 코드는 각 단계 전에 새 API를 조회하며, 긴 단일 guest phase 동안에는 guardian의 독립 종료 마감에 의존한다. 연속 하드웨어 인증/OS 권한 격리는 제공하지 않는다.

`failure_matrix.json`은 19개 실패 상황의 작성자 정적 제어 흐름 검토다. 실제 결함 주입 실행은 하지 않았다. 최종 근거는 `static_review_result_v4.json`이며 첫 결과와 보조 검토 스크립트의 변수 이름 충돌 오류도 보존했다. 마지막 보완은 종료 marker가 있으면 다음 guest 단계도 즉시 거부하는 조건이며 그 뒤의 최종 코드에 다시 정적 검토를 적용했다. 실제 SSH 왕복·게스트 실행·새 supervisor 조합·원본 회수 시간은 다음 승인 실행에서 확인해야 한다. 코드 오류를 현장에서 고치며 예산을 소비하는 운용은 금지하고, 실패하면 회수·정지·기록으로 끝낸다.
