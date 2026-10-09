# 후보 작성 중 원인·영향·반례 분석

아래는 동적 실행 전에 실제 코드에서 발견한 문제다. 실행 결과로 표현하지 않는다. 기존 실패 코드/봉인에는 적용하지 않고 새 후보에만 수정한다.

| 최초 문제 | 원인/사전 검토 공백 | 공유 사용처·수정 영향 | 수정 전후 반례 | 권한·비용 |
|---|---|---|---|---|
| Windows `os.kill(pid,0)` 사용 | POSIX의 무신호 생존 확인을 Windows에도 적용한다고 가정. Windows에서 해당 호출은 종료 효과가 가능하므로 부적합 | controller stop_control_check→모든 API/SSH/회수. psutil의 신호 없는 is_running/status 확인으로 대체 | 생존/소실/zombie, OS signal 호출0 | 정적 발견, 서버 실행0 |
| subprocess fake에 PIPE 없음 | Popen 입력 경계의 상수 목록이 실제 run과 불일치 | 정상 guest stdin 및 모든 모의 SSH | 실제 argv/input/stdout 전달을 기록하며 PIPE 상수 보유 | 모의 입력 경계만 수정, 실 코드 권한 불변 |
| exited/intended=running 정지 오인 | 실제 confirm_stop은 actual만 검사. 관측 어댑터가 queued STARTING을 그대로 반환 | guardian·supervisor fallback·최종 상태 | 실제 confirm_stop + queued 응답은 STOP_UNCONFIRMED여야 함. 완전 stopped만 확인 완료 | 기존 guardian 원본 유지, 얇은 CLI 관측부 강화 |
| 명령 성공 직후 marker 경합 | communicate 직전만 감시해 성공 반환 순간 경합이 빠짐 | raw download→validate_result→완료승격 | download 도중 marker 생성, 성공 stdout가 와도 COMPLETED/다음 명령 금지 | 해당 실행 중단, 원본/종료 보존 |
| 마지막 cleanup에서 발견한 drift | fault 판정 이후 시간 측정이 다시 fault를 설정할 수 있음 | finally→closure→policy_completion | 최종 API 중 최초 drift, 완료 영수증 금지·clock warning 보존 | 최초 시계 재설정 금지, stop-only cleanup |
| 관측 rate parsing 오류 분류 | Decimal 변환 예외를 일정한 상태 거부로 감싸지 않았음 | 모든 core API 관측 | 누락/string/object/bool/NaN/Infinity/음수 요금 거부 | 계산식/요금 상한 불변 |
| 기본 SIGALRM이 원본을 남기기 전 프로세스를 종료 | 리밋 설정만으로 finally 보존이 된다고 가정 | 행정 runner의 전체 시험·부분 JUnit/trace | SIGALRM/SIGXCPU를 KeyboardInterrupt로 전달하여 unittest 중단·outer finally 보존. 강제 kill/OOM 원본은 여전히 OS 한계 | 실제 signal 전체 장애 인증 아님 |
| 초기 생성기가 수정 전 결함을 재도입 | 산출 코드만 고치고 다른 생성 호출 경로를 놓침 | prepare_candidate.py 재실행 | 초기 생성기 RETIRED_DO_NOT_RUN, __main__은 쓰기 전에 거부. 실제 최종 소스/해시만 실행 패키지로 전달 | 초기 작성 이력은 보존, 재생성 금지 |

각 수정 전에는 근본 원인, 놓친 이유, 모든 호출 영향, 새 반례를 위 표로 확인했다. 검토자는 `REVIEW_CANDIDATE.md`에 별도 코드 검토를 남긴다. 모의 경계가 guest Python 실행 자체를 대체하는 부분은 별도 guest 검증 시험 또는 미확인 범위로 보고한다. 별도 검토는 독립 권한 인증이 아니다.


실행 전 별도 검토 추가 반례:
- 게스트 entry의 승인서/armed/최초 시간 재검증 누락: host 검사만으로 게스트 실행 권한을 대체했다. 기존 guest_gate가 검증하던 hash/scope/ID/clock/회수 여유를 ADMIN에도 적용했다. 실제 entry 직접 반례 시험을 추가했다.
- 현재 예산 원장을 읽고 과거 비용 값으로 덮어쓰기: old B 비용과 새 admin 비용을 모두 포함하도록 max(current, carried)를 유지한다. 미래 A는 B 종료 뒤 새 원장과 별도 승인이 필요하다.
- admin 정상 결과 fixture의 KIND=None: 새 import controller 전역은 기존 alias와 달랐다. 시험의 KIND/EXPECTED를 TEST_ONLY patch 문맥에서 설정·복구한다. 실제 bootstrap main의 ADMIN 설정은 이미 존재했다.
- payload 분리 뒤 실패 returncode 기록 누락: payload_returncode를 실제 응답 직후 저장하고 finally가 그 값을 기록한다. 기존 실패 코드/상한/criteria는 바꾸지 않았다.

이 항목들은 유료 실행 전에 정적 검토로 발견했다. 45개 후보의 실행 결과는 아직 없다. 기존 실패와 봉인은 수정하지 않았다.

실제 billing 원본 추가 반례: provider next_token은 false가 아니라 null이고 success=true/count=total=6이다. 최초 후보의 is False 단정은 정상 예산 응답을 거부한다. 이를 유료 재시작 전 원본 조회에서 발견했다. 원본 null을 유지하고 success/count/total/next_token을 확인한 query_complete 결과를 별도 예산 파생 자료에 바인딩한다. 최초 후보 ZIP은 별도 정적 snapshot으로 불변 보존하며 변경 후보를 새로 생성한다. 이 작업은 원격/시험 재시도가 아니다.
