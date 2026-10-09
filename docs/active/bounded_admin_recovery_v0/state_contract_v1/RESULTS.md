# 행정 운송 상태 계약 V1 — 첫 유료 행정 실행 결과

판정 **UNRESOLVED**. 구현과 정적 반례 검토를 마쳤지만, 공급자 자원 부족으로 원격 행정 시험이 시작되지 않았다. 새 `ADMIN_TRANSPORT_SIMULATED_VALIDATED`/READY 봉인은 만들지 않았다. 기존 `REMOTE_TEST_GATE_FAILED / UNRESOLVED` 및 모든 실패 원본은 그대로 유지한다.

사용자의 별도 유료 허가로 수행한 범위는 행정 CPU 격리 모의 시험과 실제 운송·종료 검증이다. B95/A320을 호출하지 않았다. 유료 재시작 1회, 자동 재시도 0회, 현장 코드 수정 0회다.

## 실제 실행과 종료

대상 Vast **54988176 / machine 150665 / Spain, ES**, API 시간당 **$0.16162962962962962**. 실행 소스 커밋 `169f7df673a675eabd1305e4fac41c3d6c1694e2`, 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`.

- 최초 시계: **2026-10-09 09:54:21.852316 UTC**. 과거 창·실패·비용을 초기화하지 않았다.
- 실제 start 응답: `Required resources are currently unavailable, state change queued.` CLI exit0은 실행 준비 완료로 인정하지 않았다.
- actual/intended 상태를 14회 관측했지만 running/SSH readiness를 확인하지 못했다. 재시작 명령은 추가로 보내지 않았다.
- 45초 타이머의 대기 관문에서 **BOUNDED_RESTART_NOT_RUNNING**. API 지연·sleep을 포함한 실제 중단 관측은 start 반환 뒤 약47.65초이며 정확히45초 실측으로 주장하지 않는다. 전체 관측·종료 창은 **57.645135초**다. [최초 closure 원본](remote_admin_attempt_20261009_095328/closure.json)의 상태는 `DEADLINE`로 보존한다.
- 실제 supervisor 시작/READY를 확인했다. generic guardian는 running 조건에 도달하지 않아 **미시작·미ARM**이다. supervisor fallback이 STOP 1회와 actual=exited/intended=stopped를 확인했다. [종료 영수증](remote_admin_attempt_20261009_095328/supervisor_final.json).
- 별도 읽기 전용 API **2026-10-09 09:56:13.136809 UTC / 18:56:13.136809 KST**에서 id/machine/country 및 **actual=exited / intended=stopped**를 다시 확인했다. [외부 종료 영수증](remote_admin_attempt_20261009_095328/external_stop_receipt.json).
- SSH0/SCP0/게스트 작업 디렉터리0/ZIP 업로드0. 게스트 시험 결과·회수 대상이 생성되지 않았으므로 원격 회수는 `NOT_APPLICABLE_NO_GUEST_CREATED`다. 호스트 실행·실패·종료·청구·후보 원본 **58파일**은 개인 evidence 폴더에 보존하고 [개별 SHA-256 목록](remote_admin_attempt_20261009_095328/raw_evidence_inventory.json)을 기록했다. API 비밀값이 포함될 수 있는 원본은 Git 밖에 있다.

## 시험과 비용을 구별한 결과

| 구분 | 이번에 확인한 사실 |
|---|---|
| 구현됨 | stopped/starting/running/stopping과 initial/restart/control/final 역할 검사. 실행 중 SSH 주소/포트 불일치 거부, API 전후 종료 제어 검사, wall/mono drift 중단·stop-only cleanup. 기존 Transport lifecycle/guest helpers/guardian 원문 재사용, ADMIN 전용 payload/승인/회수 validator. 공통 A–H 구현 계획 표준과 AGENTS 연결 |
| 시험됨 | 실제 유료 ADMIN 재시작1/제한 대기/timeout 중단/실제 supervisor fallback STOP/외부 종료 확인. 준비한 **45개 행정 시험은 실행0**, PASS/FAIL/error/skip 숫자는 미측정이다. B95/A320 실행0 |
| 독립 검증됨 | 별도 동료가 원본 실패·실제 API fixtures·직접/간접 호출·반례·최신 source hashes를 검토하고 누락을 찾았다. 별도 실행 후 검토는 [REVIEW_REMOTE_ATTEMPT.md](REVIEW_REMOTE_ATTEMPT.md). 독립 서명 권한 인증, 동적45개 합격 인증은 없다 |
| 실패·반례 | 구 stopped 포트 오류 재현 시험과 누락/잘못된 주소/ID/원본변조/guardian 소실/시간 부족/회수 실패 등 후보 작성. 정적 검토에서 Windows kill0, fake PIPE, queued exit 거짓 정지, API/SSH 중단 경합, clock/부분 기록, 게스트 승인/armed 관문, 비용 덮어쓰기, KIND=None 정상 fixture, billing null 형식 단정을 발견·보완. 후보 동적 재현은 미실행. 이번 실제 실패는 공급자 자원 부족이며 이 원인을 코드 인용 오류로 바꾸어 기록하지 않는다 |
| 비용·성능 | 최초부터 종료 확인까지57.645135s. 최대요금0.25 기준 보수 실행료 상한 **$0.004003134375**. 게스트 시험 wall/CPU/RSS는 **미측정**. provider 일별 실행료0.020+저장료0.005=0.025, 실행 전후 표시가 같지만 반올림/이전 사용자 시간 때문에 이번 개별 실청구0으로 확정할 수 없다 |
| 미확인 | 45개 전체 실제 모의 결과, 새 supervisor+기존 guardian ARM/종료 실제 연동, 실제 원본 ZIP 전송·게스트 hash·회수, 실제 STARTING 응답, 모든 OS/통신 장애와 PID 재사용, 개별 확정 실청구. 다른 CPU 성능 개선·경험 이전·새 수치 증거는 없다 |
| 다음 행동 | 현 소스 유지. 공급자 자원 확보와 이번 실패 검토, 최신 예산 원장 대조 및 **새 명시적 행정 재실행 승인** 뒤에만 다음 창 가능. 행정 검증 완료 후에도 B95 별도 승인, B 실제 통과·종료·비용 확인 뒤 A320 별도 승인이 필요하다 |

[현재 비용 원장](budget_execution_ledger.json)은 실행 전 일별 총액을 중복 계상한 과거 상한과 이번 전체 창 상한을 모두 보존한다. 보수 누적 상한 **$0.04491355611111111111111111111**이다. 여기에 최대요금으로 미래600초 창 두 개를 더 예약하면 **$0.1282468894444444444444444444**가 되어0.10을 넘는다. 이는 확정 실청구 합계가 아니라 보수 예약 계산이다. 현재 자료로 두 최대창을 미리 승인 가능한 예산이라고 주장하지 않는다. 더 짧은 실제 실행이나 정밀한 공급자 비용 자료로 판단하려면 새 원장 대조가 필요하다.

## 원본과 입력의 무결성

기존 보호 **858파일**, 이번 후보 **34파일**을 실행 후에도 raw hash로 대조해 불일치0을 확인했다. [보존 전](preservation_before.json)·[보존 후](preservation_after.json)·[후보 입력](candidate_input_record.json). 새 준비 봉인 대신 [실패 원본 보존 봉인](remote_admin_attempt_20261009_095328/failed_attempt_evidence_seal.json)만 작성했다. 이 봉인은 실행 권한이나 합격 증명이 아니다.

| 원본 | SHA-256 |
|---|---|
| 기존 경험 탭 code seal | `18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09` |
| 기존 B95 ZIP | `6613723aef35ea3929fd4110965014ceed5ba21ea04370622fc83a37d4f59acb` |
| 기존 generic guardian | `2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802` |
| 실제 이번 후보 ZIP | `b5390ec3292d7bfef9d180058e834ffa7747aae4fccbfa80a87972e3ac88c110` |
| 후보 inventory | `09d2bc3403eab0e3a365dffdeace7ef6720a280fee09cf871cc67efd2439c8b7` |
| 실행한 새 controller | `1b71f2bdcf4da2aa93231f0271189ed87a81d994ac89bf7db77f46387f8cdaa4` |
| 실제 외부 종료 API 원본 | `4b2284156fcd5fb418e8e0b98594a3b155e54380952c7e31bb487594e48feb63` |

최초 후보의 billing False 가정은 실제 null 원본 대조에서 시작 전에 발견했다. 그 후보 ZIP/입력 기록은 `candidate_static_snapshot_1`에 불변 보존하며 이번 후보와 구별한다. 정적 수정은 유료 실행 전 완료했고, 유료 실행 이후 실행 코드는 변경하지 않았다.

기존 봉인된 구현·시험·물리/수치/정책·서명 권한·원본·공식 기준선은 바꾸지 않았다. 이번 변경은 새 행정 namespace, 공통 미래 구현 표준과 AGENTS 연결, 현재 상태/문서 지도, 별도 검토·실패 증거다. `UNAPPROVED_B.json`은 명시적으로 false이며 새 승인서가 아니다.

실패 stdout은 공급자가 반환한 CR/줄바꿈을 포함해 원문 그대로 유지한다. 새 namespace의 `*.stdout -text -diff`는 Git에서 그 원문을 binary로 보존·비교하게 하는 표시다. whitespace 경고를 없애려고 실패 출력 원본을 정규화하지 않았다. 실행 이후 바뀐 것은 결과/검토/현재 문서/이 Git 보존 표시이며, 고정된 실행 소스34개는 변경하지 않았다.

**LOCAL FULL 생략 / 정적 검사와 원본 대조만 수행 / 이유:** 사용자 로컬 프로젝트 동적 시험·물리/GPU 금지. 실제 원격 행정시험은 공급자 자원 관문에서 미실행으로 끝났으므로 관련 동적 시험으로 대체했다는 주장도 하지 않는다. 기준선 갱신0, 새 물리0/GPU0, push0/master 병합0.

구상 일치성: 실행 상태마다 필요한 자료가 달라지는 문제를 명시적으로 검증하는 구조와 기존 코드 재사용은 구현했다. 이를 실제45개 동작으로 입증하는 목표는 달성하지 못했다. 정상 종료 요청과 실제 외부 종료를 구별하는 부분은 이번 실패 경로에서 관측했다.
