# 서버 52763685 변경 — 읽기 전용 확인과 미승인 예산 예외안

현재 실행 승인 상태: **현재 시간당 상한으로 REFUSED / 예산·독점 종료 결정 대기**. 사용자 서버 사용 지시는 대상 변경 권한으로 기록한다. 기존 시간당0.25·합산0.10 규약을 묵시적으로 바꾼 것으로 처리하지 않는다.

## A. 목적·대안

이전 Spain54988176은 자원 부족으로 행정45개 시작 전 중단됐다. 사용자 화면이 지정한 이미 켜진 Norway52763685를 사용하려는 요청이다. 직접 SSH가 되는지와 실제 PID1을 먼저 확인했다. 더 단순한 대안은 시간당0.25 이하의 서버를 사용하는 것이지만 현재 대상 지시를 임의로 바꾸지 않는다.

## B. 실제 근거와 가정

실제 API id52763685/machine3448/Norway,NO/actual=running/intended=running. 직접81.166.162.13:12408과 API22/tcp mapping 일치, PID1CONTAINER_ID52763685 실제 관측. Python3.12.3/pytest9.1.1/psutil7.2.2, affinity64. Proxy 화면13685와 API13684는 다르므로 직접 연결만 검증하고 가상의 일치값을 만들지 않는다. 단가0.2696296296296296은0.25를 넘는다. GPU99.999908%와 기존python6프로세스를 관측했지만 작업 소유·역할은 미확인이다. 어떤 GPU 계산도 호출하지 않았다.

## C. 틀렸을 때의 반례

켜진 서버에도 stopped-only controller를 사용하면 다시 행정 관문에서 거부된다. 시간당0.25를 유지한 guardian는0.26963을 거부해야 한다. 기존 GPU/python 작업이 별도 작업이면 무조건 STOP할 수 없다. screenshot proxy와 API proxy를 같다고 가정하면 주소 확인 실패다. 현 승인 없이 상한·식별값을 고쳐 통과시키는 것은 허용하지 않는다.

## D. 변경 영향

| 변경 대상 | 영향 | 필요한 검사 | 현재 미확인 |
|---|---|---|---|
| 대상 식별 | controller initial/restart/control/final, probe, guardian lease, 회수 | id/machine/country/직접SSH/API 차이 | 새 대상 전체 동작 |
| running 인수 | stopped-only initial/start 경로 | 이미 running을 명시적으로 인수하고 start0, 종료 책임/최초 clock 기록 | 독점 STOP 권한 |
| 시간당 예외안 | 상태 검사·승인서·guardian·비용 원장 | 명시적 새승인/raw protocol hash/cap 초과 거부 |0.28 새승인 |
| 결과 패키지 | 기존45행정 실제 코드·새 대상 연결/회수 | 원본 hash/추가 변경 영향 반례/자원 한도 | 동적 미실행 |

## E. 원인과 재사용 제한

이전 실패는 공급자가 자원 부족/queued를 보고한 실제 자료이며 코드 인용 실패가 아니다. 그 실패·입력 ZIP·봉인은 바꾸지 않는다. 기존 검증된 argv/SSH stdin/SCP/회수 hash/supervisor 및 원본 guardian를 재사용하는 방향이다. 이전 Spain fixed target/stopped-only 시작은 새 running 대상에 그대로 적용할 수 없으므로 새 버전 연결이 필요하다.

원본 guardian의 과거 offline0.28 예외 파일52763685는 별도 실험(2026-10-08)에 속하고 guardian deadline240s다. 이를 이번 권한으로 자동 재사용하거나 시간 검사를 우회하지 않는다. 현재 ADMIN의120초 시험+회수·종료 여유 및 전체600초와 연결하는 별도 예외 버전/검토가 승인 후 필요하다. 계산 코드·검사관 서명 권한을 변경하지 않는다.

## F. 입증 방법

현재 읽기 전용 실제 API/SSH/PID1/runtime/billing 원본과 개별 SHA는 readonly_preflight.json에 연결했다. 대상 변경이 승인된 예산과 종료 범위에 들어오면 최소 새 transport 연결을 작성·정적 검토하고 고정한 뒤 원격 행정 시험을1회 수행한다. 기존 정상/실패 행정45개와 실제 guardian ARM/회수/종료를 확인한다. 새 변경에 영향 반례가 필요하면 먼저 명시하며 통과 기준을 낮추지 않는다. B95/A320은 실행하지 않는다.

## G. 미확인·한계

동적 행정시험0, 새 transport 인수 모드 미구현, 새로운 실행 승인서 없음. 기존GPU 작업 소유/중단 가능성, guardian 예외 연결의 동적 검증, 미래B/A 예산·실청구는 미확인이다. 현재 readonly runtime 관측을 프로젝트 시험 합격으로 표현하지 않는다. 로컬 프로젝트 동적 시험·물리/GPU·push/master merge0. LOCAL FULL 생략/정적 원본 및 문서 확인만/사용자 동적 시험 금지, 기준선 불변.

## H. 승인·예산·종료

제안은 **ADMIN만**, 시간당 상한만 별도0.28로 예외 적용.600초·wall/CPU120초·affinity1·주소공간512MiB·회수420초·종료180초·창0.05·캠페인0.10·실패 중단/원본 보존·자동 재시도 금지 유지.0.28*600/3600=0.04666666666666666666666666667. 이전 보수 원장0.04491355611111111111111111111을 유지한 임시 합계0.09158022277777777777777777778다. 실제 직전 원장은 다시 대조해야 하며 현재 켜진 NO서버의 기존 일별 비용0.054는 이번 새시험 비용으로 잘못 표시하지 않는다.

필요한 설계자 결정은 시간당0.28 예외와 이 서버의 독점 사용/완료·실패 시 STOP 허용이다. 이미 running이므로 시작 시 재시작을 추가 요청하는 방식은 피하고 인수 모드를 준비한다. 종료하면 기존GPU/python 작업도 중단되므로 그 효과를 승인안에 명시한다. 아직 서버 start/stop/시험/소스 업로드는0회다. proposed_budget_and_target.json의 승인 필드는 false이고 READY 봉인이 아니다.

## 이후 승인과 실행 버전 연결 — 2026-10-09

위 A–H는 승인 전 제안 원문을 보존한 것이다. 사용자가 call_dbc2f565a36449c3981be1f2db692099에 “이번 행정 시험 $0.28/h·독점 사용·종료 승인”으로 답했다. 현재 권한은 target_protocol.json에 별도로 연결한다. 기존 proposed_budget_and_target.json의 false와 REVIEW_READONLY.md의 승인 전 상태는 바꾸지 않는다.

이번 실행은 ADOPT_RUNNING이며 start/restart 요청0, 추가 임대0이다. 새 승인서의 restart_exact_instance_authorized=false, adopt_existing_running_authorized=true를 요구한다. 기존 사용자 작업이 함께 중단되는 효과를 포함해 독점 STOP을 승인받았다. 승인 전 기존 NO 실행료와 이번 인계 후 실행료를 구분하고, 공급자의 반올림된 일별 청구를 정확한 시험별 비용으로 표현하지 않는다.

변경 함수 호출 경로는 admin_bootstrap.preflight→Transport.execute→initial/show→supervisor 준비→running 인계→원본 guardian arm→PID1 probe→ZIP/승인/ARM 전달→remote_admin_entry→run_admin_simulation→회수→행별 검증→completion→원본 guardian STOP→supervisor 종료 영수증→외부 final API다. 실패 경로는 controller 예외→회수 여유와 신원 확인 시 회수1회→FAILED marker→guardian STOP/미확인 시 supervisor fallback STOP→외부 final이며 시험 자동 재실행은 없다. 최초 allocation clock을 한 번만 기록한다.

원본 guardian는 변경하지 않는다. 현재 승인이 정확히 같은 NO 대상의 시간당0.28을 허용하므로 기존 immutable hourly exception의 확인 함수를 재사용하되, 이번 승인과 target_protocol SHA를 supervisor/상태 관문에서 별도로 검증한다. 그 함수의240초 종료 기한을 완화하지 않기 위해 ADMIN entry wall을30초, SSH entry timeout50초로 더 좁혔다. 원래 시험 wall/CPU 상한120초, 전체600초, 회수420초, 종료180초, 창0.05, 합산0.10은 유지한다. 시험 전50+96초 회수·정지 여유가 확보되지 않으면 실행을 거부한다.

기존45개 시험의 원본은 state_contract_v1에 불변 보존했다. 새 namespace 사본에서 guest runner 경로만 바꾸고 새 NO 승인 누락/잘못된 protocol SHA/기계/초과요금/stopping 거부, 원본 guardian240초·해시·기계 반례, 실제 controller의 인계 start0/STOP1을 확인하는3개를 추가했다. 예상48개·fail/error/skip0이 이번 행정 관문이며 B95/A320 성공이나 독립 승인권 인증을 뜻하지 않는다. 현재 동적 결과는 미확인이다. 실패하면 현장 코드 수정과 재시험을 하지 않는다.

기존 소스858개·과거 실패·원본45개·기존 candidate ZIP은 SHA로 유지하고 새 candidate는 독립 입력 봉인으로 만든다. 패킷 생성은 필요한 파일 하나라도 없으면 실패하며 누락 파일을 조용히 제외하지 않는다. 별도 검토자가 실제 새 소스·원본 차이·실패 반례를 정적으로 확인한 뒤, 입력을 고정하고 승인된 유료 ADMIN1회를 수행한다. B95/A320·새 물리·GPU·LOCAL FULL·push/master merge0 유지.

### 실행 전 별도 검토의 실제 수정

REVIEW_PRE_EXECUTION.md의 최초 UNRESOLVED는 보존한다. 현재 승인 참조/원문을 pinned protocol과 정확히 대조하고, 이미 running인 대상의 supervisor Popen/ready/pin 실패에서도 인수 직후 STOP 책임을 유지하도록 수정했다. 기존 confirm_stop 함수를 controller fallback에서도 재사용하며, exited/running 의도는 거부하여 거짓 STOP 영수증을 방지한다. 같은 새 NO 시험 method에 정상·Popen 실패·ready ID 불일치·supervisor 종료·queued exit를 추가해 48개 top-level 시험 수는 유지했다. 기존 fake clock을 새 승인 반례에도 적용해 실제 시각이 다른 오류를 만들지 않게 했다. 이 변경은 입력 ZIP 생성 및 유료 ADMIN 시작 전이며 현장 수정이 아니다.

읽기 전용 비용 파생 작업에서도 deprecated invoices 응답 list와 v1 metadata의 차이, 잘못된 instance list 가정, Vast CLI의 start-date만 지정시 TypeError를 발견했다. 실패 원본을 보존하고 CLI 코드를 읽어 날짜 양 끝을 명시한 v1 조회로 대조했다. 이 과정의 서버 start/stop/시험은0이며 운송 코드 자동 재시험으로 세지 않는다. 최초부터 이미 running인 NO 서버의 현재 일별 누적은0.174(실행0.143/저장0.031)이다. 이 금액과 읽기 준비 중 기존 서버의 청구 증가는 인계 후 제한 시험의 비용과 별도로 공개한다. 전체 사용자 계정의 청구가0.05/0.10 이하라는 주장은 하지 않는다. 최초 인계 allocation의 실행료와 이전 봉인 시험 캠페인 원장은 계속 각각0.05/0.10으로 제한한다.
