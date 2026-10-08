# 경험 탭 V0 원격 시도 — 시험 전 중단

2026-10-09 KST. 봉인된 변경 트리 `ac02951e`, 코드 봉인 `18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09`.

**REMOTE_EXECUTION_REFUSED_BEFORE_TEST / NOT_VALIDATED.** 예상 320개 시험과 비용 benchmark는 시작하지 못했다. pytest PASS/FAIL/ERROR/SKIP 수치와 검색·CPU·메모리 측정값은 없다. 예상 항목을 skipped로 기록하거나 과거 254개 통과를 이번 결과로 옮기지 않는다. source 준비 상태를 검증 완료로 변경하지 않는다.

## 승인·서버·예산

사용자는 봉인된 V0의 유료 Linux 원격 시험과 비용 측정을 승인하고 서버·예산을 승인 범위로 제한했다. 대상 질문에 `ssh -p 26992 root@ssh9.vast.ai -L 8080:localhost:8080`을 지정했다. 새 읽기 전용 API 조회로 instance **54815136**, machine **56006**, France **FR**, SSH host/port 일치를 확인했다. 조회 단가는 **$0.13462222222222225/h**였으며 시간당 $0.25 상한 안이었다.

처음 조회했을 때 서버는 이미 running이었다. 이 요청에서 서버 임대·재시작은 하지 않았다. 원격 셸은 Linux/Python 3.12.3, 허용 CPU 0~23과 기존 `/workspace/rlp_A_8d4115e5/venv/bin/python` 존재를 관측했다. 새 코어/물리 실행 능력 검증은 하지 않았다. 사용자 명령의 포트 forwarding은 시험에 필요하지 않아 SSH 명령 실행만 사용했다.

계획의 CPU 1개, 계산 wall/누적 CPU 각 120초, AS/프로세스 트리 RSS 512MiB, 물리/GPU 0, 전체 할당 600초, 회수 마감 420초, 종료 확인 180초, 총 $0.05 상한을 유지했다. 관측 창은 최초 서버 조회 전 **2026-10-08 15:31:09.761490 UTC = 2026-10-09 00:31:09.761490 KST**부터 고정하고 재시도로 초기화하지 않았다.

## 발생한 오류와 중단

| 행정 시도 | 실제 결과 | 시험·물리 시작 여부 |
|---|---|---|
| 1 | PowerShell에서 SSH에 넘긴 Python 명령의 인용 처리가 깨져 원격 SyntaxError | 프로젝트 import/pytest/계산 없음 |
| 2 | 외부 guardian ARMED 후 Linux·venv 조회 성공. SSH 셸의 CONTAINER_ID가 null이라 운송 코드의 식별 관문이 거부 | 소스 업로드·pytest·benchmark 없음 |
| 3 | 기존 방식처럼 `/proc/1/environ`에서 실제 container ID를 읽고 검증된 ID를 guest environment에 전달하도록 **새 행정 운송 코드만** 보완. 실행 시작에서 최초 예산 시계의 **275.774140초**가 경과해 준비 잔여시간 관문 `PACKAGE_OR_REMAINING_ALLOCATION`이 거부 | 서버 재시작·소스 업로드·pytest·benchmark 없음 |

두 번째 시도의 원격 probe는 단순 표준 라이브러리 환경 조회다. 컨테이너 ID를 추정하거나 검사를 생략해 승인하지 않았다. 이전의 성공한 실제 A 운송 코드를 읽어 PID 1 환경에서 container ID를 검사하던 방식을 확인했지만, 세 번째 시도에서는 시간 관문이 먼저 거부해 이 보완 코드를 원격 실행하지 못했다.

인용 처리와 셸 환경변수 사용은 작성자의 행정 운송 코드 오류다. 봉인된 탭 구현의 실패나 물리·정확성 결함으로 분류하지 않는다. 준비 시간이 예산을 소비했고, 종료·회수 여유를 침해하기 전에 fail-closed로 멈췄다. `AGENTS.md`의 **"3회 시도해서 실패하면 멈추고 보고한다"** 규칙에 따라 네 번째 시도·재시작·새 예산 창을 만들지 않았다.

## 결과와 비용 측정

| 요청된 항목 | 실제 결과 |
|---|---|
| 예상 320개 pytest | **미실행**, 실제 수집/JUnit 없음 |
| PASS/FAIL/ERROR/SKIP | **측정 없음**. 0 passed나 320 skipped라는 시험 결과를 생성하지 않음 |
| 100/1000/10000건 색인 검색 wall/CPU | **미측정** |
| CPU 경로 생성 비용 | **미측정** |
| 선택 원본 재판독 비용 | **미측정** |
| Python traced peak/RSS/저장 크기 증가 | **미측정** |
| 새 물리/GPU | 실행 진입점 호출 없음; pytest guard report는 시험 미실행으로 생성되지 않음 |
| 독립 검사·승격 | 새 검사관 영수증/관리자 활성화 없음 |

첫 원격 시도 창의 서버 정지 확인까지 보수적 관측 시간은 **191.207436초**다. 조회 단가와 전체 관측 창을 적용한 추정은 약 **$0.007150214**이며, 중간의 실제 정지 시각보다 늦은 새 API 확인 시각까지 포함한다. 세 번째 시도는 서버가 exited인 채로 시간 관문에서 거부되어 새 running 시간을 추가하지 않았다. 최종 세 번째 시도 종료 기록은 최초 시계에서 **278.173727초**다.

이 추정은 실제 청구서가 아니다. 서버는 이 요청 전부터 running이었으므로 그 이전의 전체 임대 시작·과금, exited 상태의 저장 비용과 실제 청구는 미확인이다. 계산 비용 성공이나 전체 청구 상한 준수의 인증으로 승격하지 않는다.

## 원본·봉인 보존

실행 전 정책 봉인 4파일, 보호 794파일, 코드 봉인 812파일을 재해시하여 **불일치 0**을 확인했다. 전달 ZIP 813항목의 raw hash/중복/CRC도 다시 확인했다. 실제 업로드는 하지 않았다.

- 프로토콜 raw SHA256: `f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c`
- 코드 봉인 raw SHA256: `18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09`
- 기존 소스 ZIP raw SHA256: `ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392`

원래 소스·시험·정책·코드 봉인·보호 원본·과거 성능/실패 기록은 바꾸지 않았다. 새로 만든 것은 서버 조회, 새 사용자 승인, 행정 운송 코드와 그 봉인, 오류 이벤트, 외부 종료 영수증 및 이 보고서뿐이다. 원격 프로젝트 출력이 없으므로 회수 ZIP·JUnit·benchmark·guard report를 만들어냈다고 주장하지 않는다. 서버에서 회수할 프로젝트 원본이 없었으며, 실제 원격 환경 조회 stdout/stderr는 로컬 운송 기록으로 보존했다.

자료는 `docs/active/adaptive_experience_tablet_v0/remote_20261009_preflight/`와 `remote_20261009_attempt3/`에 있다. 두 번째 운송 코드와 보완한 세 번째 코드는 각각 남겨 덮어쓰지 않았다. 새 행정 증거의 raw hash 목록은 `remote_20261009_evidence_manifest.json`에 별도로 보존한다. 첫 SSH 오류는 도구 출력과 오류 요약으로 보존했으며 별도의 원격 pytest 오류 로그가 아니다.

커밋 준비 후 새 행정 증거 34파일을 목록의 raw SHA256과 다시 대조해 불일치 0을 확인했다. 기본 `git diff --cached --check`는 보존된 CRLF 원문을 trailing whitespace로 보고했다. 원문 바이트를 바꾸지 않고 `git -c core.whitespace=cr-at-eol diff --cached --check`로 줄 끝 CR을 인정한 검사를 수행했다. 이는 시험 통과 증거가 아니다.

## 실제 서버 종료

두 번째 시도에서 외부 guardian은 **FAILED → STOP_CONFIRMED**를 기록했다. STOP 요청 후 첫 API는 actual running/intended stopped, 다음 API는 **actual exited/intended stopped**를 확인했다. 정확한 instance는 54815136이고 STOP 요청은 한 번이었다. guardian의 actual exited 확인은 정지 확인 절차 시작부터 **12.094초** 안에 이뤄졌다.

운송 controller가 별도로 새 API를 조회하여 actual exited를 확인했고, 세 번째 중단 뒤의 새 API 조회에서도 actual exited를 다시 확인했다. 단순 게스트 프로세스 종료를 서버 정지로 간주하지 않았다. 외부 감시기/확인 원문은 `remote_20261009_preflight/guardian/final.json`과 양쪽 시도의 `final_instance.json`/`closure.json`에 있다.

## 한계·다음 실험

구상 일치성의 작성자 검토: 과거 경험을 새 CPU 성능으로 승격하지 않았고, 실패를 보존했으며, 봉인 코드 변경·추가 물리·GPU·로컬 동적 시험·push/master 병합 없이 정지했다. 이것은 운송·중단 경계의 실제 관측이며 탭 기능의 오프라인 검증이나 독립 수식 감사가 아니다. `RwForce` 공유, OS 권한 격리 부재, 공식 통합 회귀 미완료는 그대로다.

**LOCAL FULL 생략 / 원격 관련 시험도 미실행 / 이유:** 사용자 로컬 동적 실행 금지와 원격 준비 실패·3회 중단 규칙. 공식 기준선 숫자를 갱신하지 않았다.

다음 실험은 봉인된 동일 소스 320개 관문과 비용 측정이다. 준비 운송 코드의 인용 처리/PID 1 identity/동일 승인 환경 전달을 먼저 정적으로 검토하고, 기존 승인 서버의 fresh API/SSH/요금을 다시 확인한 뒤 새로 승인된 단일 600초/$0.05 창에서 실행해야 한다. 기존 예산 창을 초기화해 자동 재시작하지 않는다. 이 보고서는 새 실행 승인서가 아니다.
