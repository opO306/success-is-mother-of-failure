# ADMIN_TRANSPORT_STATE_CONTRACT_AND_CRITICAL_REVIEW_V1 — 작업 계획

기준 HEAD `3090460280219b8964097caafc25a54861906121`, 기존 브랜치 유지. [공통 표준](../../IMPLEMENTATION_CRITICAL_QUESTIONS_STANDARD_V1.md)을 적용한다. 원래 실패·ZIP·B95/A320·계산기·서명 권한은 불변이다. 로컬 프로젝트 동적 시험, 새 물리/GPU, push/master 병합은 금지한다.

사용자는 원문 이후 **유료 서버에서 시험과 실제 검증 수행을 허가**했다. 로컬 동적 시험은 실행하지 않는다. 이번 실행 대상은 기존 Spain54988176/machine150665이며, 행정 CPU 격리 모의 시험 및 실제 원본 운송/종료 관측만 수행한다. B95/A320 시험을 호출하지 않는다. 기존 전체600s, 시험wall/CPU120s, affinity1, 주소공간512MiB, 회수420s, 종료180s, 시간당≤$0.25, 실행당≤$0.05, 캠페인≤$0.10을 유지한다. 실제 예산 자료를 다시 대조하기 전 충분하다고 판정하지 않는다. 현장 수정·자동 재시도는 금지한다.

## A. 목적과 대안

실제 정지 응답에 실행 포트가 없어 정상 서버가 거부된 문제가 있다. 한 줄의 포트 생략 허용은 실행 중 검사를 약화시키므로 선택하지 않는다. 모든 API 호출에 실제/요청 상태와 호출 역할을 적용하는 작은 상태 계약과 기존 운송 코드 재사용을 선택한다. 원래 수치/정책 시험은 수정하지 않는다.

## B. 가정과 실제 증거

기존 스페인 원본에는 running/running, running/stopped, exited/stopped가 있다. 포트 생략·종료 요청 후 실행 지속은 실제 자료로 확인된다. 완전한 시작 준비 응답은 `UNCONFIRMED`; 합성 시험을 실제 상태 관측으로 승격하지 않는다. 직접 SSH40470과 API 릴레이23876은 서로 다른 연결 정보다. 원본에서 실제 PID1 ID54988176과 Python3.12.3/pytest9.1.1/psutil7.2.2가 관측됐지만 재시작 후 환경 보존은 재확인이 필요하다.

## C. 자기반박과 위험한 반례

exited/intended=running인데 정지로 처리, running/intended=stopped인데 SSH 전송, API 조회 중 completion marker 발생, 승인 포트와 타 포트가 같이 존재, guardian armed 뒤 종료, clock drift로 finally 기록 탈락, 정지 가격 변화로 종료 사실 소실, API 손상/중복 키/NaN·회수 부분 자료가 핵심 반례다. 가장 약한 증거는 실제 STARTING 자료와 실제 OS 장애/프로세스 죽음의 전체 인증이다.

## D. 호출·영향 분석

| 변경 대상 | 영향을 받는 부분 | 필요한 시험 | 미확인 |
|---|---|---|---|
| show/state 검증 | initial, restart polling, control, final | 실제 stopped/running/stopping 원본·합성 starting/unknown/오염 | 실제 시작 준비 단계 |
| control | py/upload/recover의 API 이전·이후 경합 | marker/supervisor/guardian 종료 중 추가 SSH0 | API와 SSH 사이 OS 원자성 |
| age/finally | 마감·회수·supervisor wait·closure 비용 | wall/mono drift·기록보존·완료승격 금지 | OS 시계 모든 장애 |
| CLI 상태 검증 연결 | 기존 guardian 및 supervisor fallback | id/machine/country/정지 완료·API장애 | provider 전체 장애 인증 |
| process wait | 긴 SSH gate/회수 중 종료 감시 | guardian/supervisor 종료시 전달 중단 | 게스트 process kill의 완전한 인증 |
| 준비/최종 바인딩 | 기존 B ZIP·권한·비용·실패 기록 | 원본 hash, false 승인 거부, 반복 start0 | 미래 B/A 승인 및 개별 실청구 |

show 직접4곳: 기존 controller initial468/restart504/control352/final590. control 간접 py366/upload374/recover387. guest_gate는 게스트 PID1/ticket/seal을 다시 검증한다. generic guardian의 B 경로에는 A heartbeat가 없으며 완료 marker·시간 마감 방식이다. 원본 guardian를 수정하지 않고 새 연결부에서 관측 검증을 적용한다. 검사를 빠뜨리거나 승인 포트를 대체해서는 안 된다.

## E. 원인 분석

최초 실패 `EXACT_INSTANCE_API_BINDING`: 모든 상태에서 ports가 존재한다고 가정했다. 보존 stopped 응답을 준비 단계에서 대조하지 않았고, 같은 show가 final에도 쓰이는 영향을 추적하지 않았다. 원인과 호출 관계를 원본 해시 및 별도 검토 기록으로 남긴다. 기대값을 낮추는 방법은 금지한다.

## F. 입증할 시험

기존 실제 실패 원본으로 구 운송기 거부를 재현하고 새 운송기가 STOPPED 핵심 식별을 유지하는지 대조한다. 실제 execute/control/py/upload/recover/validate_result와 supervisor.main, guardian.main, confirm_stop 코드 경로를 사용하되 격리 모의 시험 안에서는 프로세스·CLI·SSH·시간만 가짜로 교체한다. fixture는 실제 원본의 허용 필드 투영이며 원본/투영 해시·출처·생략 필드를 연결한다. 합성 결과는 `TEST_ONLY`로 표시하고 B95 통과 영수증으로 사용하지 않는다. 각 입력/예상/실제/차단/명령 배열을 보존한다.

## G. 한계

실제 API 상태 형식 전체·통신 불연속·OS 권한 격리·지속 과금/서버 장애는 미확인이다. 모의 시험 합격은 실제 B95/A320 또는 독립 서명 인증이 아니다. 과거 일별 청구는 개별 시험 요금으로 확정하지 않는다. 로컬 FULL 및 공식 기준선은 갱신하지 않는다.

## H. 권한·수행 순서

원본/작업 트리 확인 → 원본 투영·가정/호출 관계 고정 → 반례 시험 작성 → 실제 실패 기록 및 모의 구 코드 실패 대조 → 최소 새 버전 수정 → 유료 CPU 격리 정상/오류 전체 영향 시험 → 별도 검토 → 결과/미확인 기록 → **시험 후에만** 새 준비 봉인·UNAPPROVED B 승인서 바인딩. 후보 실행 파일의 hash/전달 manifest는 입력 무결성 자료이며 READY 봉인이 아니다. 동료 검토는 독립 인증이 아니다. 유료 B95/A320 승인서의 자동 생성·자동 전환은 하지 않는다.

## 실제 행정 시험 실행 연결

`AdminTransport`는 새 controller의 `execute/show/control/run/py/upload/recover` 및 종료 finally를 그대로 상속한다. B payload 호출만 `execute_payload`에서 행정 입력 ZIP/승인서/armed 전송과 `remote_admin_entry`로 교체한다. KIND=ADMIN이므로 B 통과 영수증을 만들지 않는다. entry는 실제 PID1, 승인서/armed 원문 hash, ADMIN scope/원본 guardian/최초 시계/회수 여유를 다시 검증하고, 원본별 hash를 확인한 뒤 추출한다. CPU affinity 1, 주소 공간512MiB, CPU hard120s/soft119s, 시험 wall120s를 제한한다. 부모/자식 CPU·RSS도 측정한다. 원본 guest_recover와 전체 ZIP 개별 hash 검증을 재사용한다.

최초 42개 후보에서 새 행정 wrapper 직접 시험 3개를 추가해 **45개 행정 사례**를 준비했다. 개별 사례 안의 입력 변형은 원본 case_results와 trace로 남긴다. 기존 B95/A320 개수나 검사 기준은 바꾸지 않았다. 사전 검토가 발견한 정상 fixture의 KIND=None 문제도 TEST_ONLY 문맥 구성/복구로 고쳤다. 아직 실행되지 않은 후보 개수를 합격 수로 표시하지 않는다.

2026-10-09T09:41 UTC 읽기 전용 확인: actual=exited/intended=stopped, machine150665/ES, 시간당0.16162962962962962. Spain 일별 실행료0.020+저장료0.004는 이번 admin 개별 비용이 아니다. 기존 B실패 상한0.003910421736111111111111111111+준비 reserve0.012를 추가 중복 계상해 현재 보수 상한0.03991042173611111111111111111, 새600s를 최대요금0.25로 예약하면0.08157708840277777777777777778<0.10이다. `admin_budget_before.json`에 실제 원본 hash와 계산을 연결했다. 이 검사는 이번 ADMIN 창만 허용하며 미래 B/A 예산을 충분하다고 판정하지 않는다.

예상 밖의 FAIL/error 발생 시 runner failfast=True로 즉시 시험을 멈춘다. 부분 case/trace/log를 회수하고 서버 정지 후 UNRESOLVED로 보고한다. 이번 유료 창에서 코드 수정·시험 재실행은 하지 않는다.
