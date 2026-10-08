# 경험 탭 V0 행정 운송 수정·정적 검토 결과

2026-10-09 KST. 기준 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`, 시작 HEAD `284f655c`.

**ADMIN_TRANSPORT_STATIC_READY / REMOTE_NOT_EXECUTED / PROJECT_NOT_VALIDATED.** 과거 유료 시도의 인용 처리·컨테이너 식별·준비 시간 경계 결함을 운송 코드에서 보완했다. 코드 변경과 실패 반례의 정적 검토, 보호 원본과 패키지 해시 대조를 완료했다. 이 판정은 원격 실행 성공이나 320개 시험 통과가 아니다. 이번에 서버 API·SSH·SCP·guardian·프로젝트 import·pytest·계산을 실행하지 않았다. 로컬 `ssh-keygen -F`는 저장된 호스트 키의 존재만 읽었다. 실제 서버 상태·요금은 새로 조회하지 않았다.

## 기존 성공 사례 확인과 재사용

성공 기준은 `docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3/controller.py`다. 성공 여부를 문서 제목으로 판단하지 않고, 해당 `closure.json`의 COMPLETED/actual_shutdown=exited, `guardian/final.json`의 STOP_CONFIRMED/COMPLETED, `recovery_verified.json`의 111 raw 파일 및 ZIP 해시를 확인했다. 원래 evidence ZIP과 회수된 111파일을 개별 해시로 다시 대조해 모두 일치했다. 역사 자료이며 이번 실행 결과로 세지 않았다.

새 경로는 `docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/`다. 성공 코드의 `utc`, `canonical`, `sha`, 배타적 `write` 함수 4개는 AST가 동일하다. subprocess 인자 배열·POSIX shlex 인용·SCP `-O`·새 출력·회수 ZIP 및 개별 원문 해시 대조·외부 완료 marker·실제 stopped 확인 방식을 재사용했다. generic `guardian.py` 원본을 그대로 실행하도록 연결했고 fallback `Cli`와 `confirm_stop`도 원본과 AST가 동일한 복사본이다. 새 전송 틀을 성공 사례와 무관하게 처음부터 만들었다고 주장하지 않는다.

| 성공한 A-resume와의 차이 | 이번 적용과 이유 |
|---|---|
| 긴 원격 Python을 shlex.quote 후 `-c`로 전달 | Python 코드는 SSH stdin, 인자는 shlex.join으로 전달. 성공 코드의 argv/POSIX quoting을 유지하면서 중첩 인용을 제거 |
| PID 1 ID 검증 뒤 기대 ID 상수로 환경 설정 | probe와 gate 직전에 PID 1 ID를 다시 읽고 동일성을 확인한 **실제 읽은 값**만 환경 설정. 누락/중복/불일치는 거부 |
| A의 실제 물리·3600초·REAL A safety와 heartbeat relay | 이번 OFFLINE_ONLY/600초/새 물리·GPU 0 계약과 다르므로 REAL A ticket/safety/relay를 재사용하지 않음. 봉인 정책을 바꾸거나 A용 권한을 넣지 않음 |
| generic guardian은 ARMED부터 상대 마감 | 재시작 전 별도 supervisor를 준비하고 최초 시계에서 절대 400초 정지 인계. 원본 guardian은 그대로 두고 상대 마감을 좁힌 뒤 실제 ARMED 시각 재검사 |
| 회수 111파일·254개 시험·actual A 출력 | 탭 gate 320개·JUnit/guard/benchmark/탭 원문 출력. ZIP 전체 해시·정확한 파일 집합·개별 해시·경로/중복/symlink를 검사하고 새 결과만 판정 |
| 과거 컨트롤러가 코드 안에 당시 승인 문구 보유 | 새 별도 인간 승인 JSON과 행정 봉인 해시 필요. controller가 승인 문구나 `true` 값을 스스로 생성하지 않음 |

## 이전 세 오류의 수정

1. **PowerShell → SSH → Python 인용 오류:** PowerShell은 Python 파일 경로와 CLI 인자만 실행한다. Python에서 SSH를 `subprocess` 인자 배열로 호출하며 shell=True는 없다. Linux 셸에 전달하는 토큰은 shlex.join으로 인용한다. Python 본문은 stdin으로 전달하여 셸 문자열에 끼워 넣지 않는다. 공백·따옴표·한글·달러·역따옴표·명령 치환 형태·세미콜론·개행·빈 인자의 stdlib 토큰 왕복 3벡터를 확인했다. 실제 셸/SSH 실행 시험은 아니다.
2. **SSH 셸 CONTAINER_ID 가정 오류:** `/proc/1/environ`에서 실제 `CONTAINER_ID=` 항목 하나를 읽어 승인 instance와 비교한다. 빠짐·중복·잘못된 값이면 출력 디렉터리 생성과 소스 전달 전에 거부한다. wrapper도 실행 직전에 다시 읽고 확인한 실제 값으로만 게스트 환경을 구성한다. ticket/armed raw 및 canonical 해시와 서버 범위도 대조한다. 식별 정보를 만들어 넣거나 검사를 생략하지 않는다.
3. **수정 중 최초 창 소진:** 소스/행정 봉인/승인 검토는 서버 조회·유료 재시작 전에 끝낸다. 최초 UTC/monotonic 시계는 재시작 전에 배타적으로 기록한다. 준비 진입은 100초 미만, gate 시작은 150초 미만이며 wrapper/회수/API에 필요한 시간을 확보한다. 현장에서 수정·재시도하지 않는다. 기존 실패 3회와 종료 창 해시는 유지하고 **새 창의 명시적 별도 승인** 없이는 API 호출 전에 거부한다.

## 실패 반례와 시간·종료 검토

`failure_matrix.json`에는 19개 반례의 거부 지점·다음 실행 차단·남길 자료를 기록했다. 이전 3가지 오류뿐 아니라 SSH 인증/host key/연결 실패, PID 1 정보 누락·불일치, API 서버/단가 불일치, ZIP·원문·파일 집합 불일치, ZIP 경로 탈출/중복/symlink, guardian 미작동/영수증 불일치, 만료 승인, runtime 누락, 시험 fail/error/skip, 원본 회수 실패, controller 소실, clock drift, 정지 API 장애, marker/종료 영수증 오류를 검토했다.

실패하면 다음 guest 단계/시험을 시작하지 않으며 원본·stdout/stderr·오류 이벤트를 보존한다. 검증된 guest 식별 후 생긴 결과는 한 번 회수하고, 패키징/회수가 실패하면 자동 재패키징·재실행하지 않는다. 식별을 확인하지 못한 연결에는 회수 SSH도 보내지 않는다. 다운로드된 불완전 ZIP은 삭제하지 않으며 회수 성공을 주장하지 않는다. 서버는 destroy하지 않고 stop만 한다. 소스 업로드 또는 root 생성 후 연결이 끊기면 원격 파일이 정지된 저장 공간에 남을 수 있다. 로컬 보호 원본은 불변이다.

종료 감시기는 재시작 전에 READY/lease 해시가 확인되어야 한다. 서버 running 확인 뒤 원본 guardian을 실행하고 ARMED의 instance/machine/country/승인/guardian hash를 확인한다. generic guardian은 REAL A heartbeat를 제공하지 않으므로 각 guest 단계 전에 새 API와 외부 process/receipt 상태를 확인한다. 긴 guest 단계 중에는 독립 종료 마감에 의존하며 이를 연속 제어 검증으로 표현하지 않는다.

시간 경계는 최초 시계 하나다. 전체 600초, CPU/계산 120초, 원본 회수 상한 420초, 정지 확인 180초를 바꾸지 않았다. 보조 supervisor는 400초에 정지 인계를 시작한다. 원본 guardian의 상대 마감은 초기 API 지연을 고려해 20초 더 좁히며 실제 ARMED 시각+deadline≤420을 다시 확인한다. supervisor는 590초까지 확인을 시도하고 마지막 fresh API 여유를 남긴다. 실제 `exited/stopped`와 외부 STOP_CONFIRMED 둘 다 있어야 종료 확인으로 판정한다. API 장애/스케줄 지연으로 확인하지 못하면 UNRESOLVED이며 성공으로 표시하지 않는다. 새 supervisor 결합 방식과 이 시간 여유의 실제 충분성은 아직 실행 검증되지 않았다.

## 정적 근거와 무결성

최종 분석은 `static_review_result_v4.json`이다. transport와 guest 스크립트 7파일을 AST로 읽고, 원본 재사용 6개 함수/클래스의 AST 동일성, local controller의 project import 0, shell=True 0, 실제 ID 변수 전달, 원본 소스/전달 ZIP/과거 실패 자료 해시를 확인했다. AST 분석은 코드 분기의 완전한 증명이나 실제 결함 주입 실행이 아니다. 작성자가 별도로 제어 흐름과 19반례를 검토했으며 독립 감사 영수증은 아니다.

| 보호 대상 | 실제 정적 대조 |
|---|---|
| 정책 봉인 | 4파일, 불일치 0 |
| 기존 보호 원본 | 794파일, 불일치 0 |
| 탭 코드 봉인 | 812파일, 불일치 0 |
| 전달 ZIP | 813항목, 정확한 파일 집합·CRC·개별 raw hash 일치 |
| 이전 원격 실패 증거 | 34파일, raw hash 불일치 0 |
| 성공한 A-resume 회수 자료 | 111파일, ZIP 및 회수 raw hash 일치 |

원래 프로젝트 지문:

```text
protocol.json: f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c
code_seal.json: 18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09
source ZIP: ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392
```

최종 새 행정 봉인 `transport_seal_v3.json` SHA256은 `753c2f1407e7f42e54b5d344513228f736811716475c7bb777fba8c1b1953352`다. 이 별도 봉인은 프로젝트 code_seal에 파일을 추가하거나 기존 ZIP을 다시 만드는 방식이 아니다. 행정 코드 변경 시 새 별도 검토·봉인·승인이 필요하다.

이번 정적 검토 중 보조 분석 스크립트의 CLI 변수 `args`를 토큰 벡터 반복문에서 덮어써 보고서 기록 직전에 AttributeError가 발생했다. `lexical_args`로 분리해 수정했으며 오류 요약, 첫 PASS 자료, 중간 행정 봉인/미승인 template을 보존했다. 이어서 외부 종료 marker가 있으면 다음 guest 단계를 거부하는 조건을 보완하고 최종 v4 검토를 최종 행정 코드 해시와 결합했다. 이 오류와 정적 보완은 유료 실행 시도가 아니고 서버 창/기존 실패 횟수를 초기화하지 않았다.

## Git 범위·실행되지 않은 부분·구상 일치성

시작은 사용자 지정 HEAD `284f655c`의 clean tree였다. 기존 추적 파일 변경 0이며 추가한 파일은 이 보고서와 `admin_transport_static_20261009/` 안의 행정 코드·검토·별도 봉인·미승인 template·증거 목록뿐이다. 실제 변경 파일은 `change_inventory.json`에 기록한다. 새 로컬 commit과 최종 작업 트리는 종료 보고의 실제 Git 명령 결과로 확인한다. GitHub push/master 병합 0, 새 브랜치/worktree 없음.

**LOCAL FULL 생략 / 프로젝트 관련 동적 시험도 미실행 / 이유:** 이번 범위는 행정 운송 정적 준비이며 사용자가 로컬 프로젝트 동적 실행을 금지했다. 공식 기준선 숫자는 갱신하지 않았다. 새 유료 실행·서버 재시작·SSH 환경 조회·GPU·물리 0이다.

아직 실행 검증되지 않은 부분은 실제 SSH/stdin/SCP 왕복, 서버 PID 1 ID와 런타임/단가의 현재 상태, guest 스크립트, supervisor와 generic guardian의 결합, fail/timeout 때 실제 회수·정지, 120초 계산·회수 시간 여유, 320개 pytest와 검색/CPU/메모리 측정이다. 로컬 도구·키 파일·저장된 host key의 존재는 확인했으나 현재 원격 인증 성공을 뜻하지 않는다.

구상 일치성 검토: 봉인된 반장의 경험 탭 기능·수식·기존 시험·정책·원본은 바꾸지 않았고, 과거 결과를 새 시험의 통과로 승격하지 않았다. 알려진 운송 결함을 유료 창 진입 전에 검토할 수 있게 옮겼으며, 승인/식별/해시/마감/회수/종료 실패가 프로젝트 실행으로 이어지지 않도록 차단했다. 새 실행 성공을 보장하는 판정은 아니며 설계자가 승인할 다음 원격 시도의 구체적인 운송 코드와 검토 근거를 준비한 판정이다. 현재는 **ADMIN_TRANSPORT_STATIC_READY**이고 재실행은 별도 승인 대기다.
