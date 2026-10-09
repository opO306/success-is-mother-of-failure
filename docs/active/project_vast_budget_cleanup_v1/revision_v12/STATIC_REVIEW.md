# V12 실제 소스 별도 검토와 정적 확인 — 동적 미실행

판정은 정적 후보 검토다. 원격 시험 통과·독립 권한 인증·A320 완료가 아니다. 로컬 프로젝트 import/수집/시험 0회, 새 유료 실행 승인 전이다. V11 기존10 및 V12 영향 시험은 서버에서 먼저 수행한다. LOCAL FULL은 사용자 V12 로컬 동적 금지 지시 때문에 실행하지 않고 기존 기준선을 갱신하지 않는다.

별도 검토자가 실제 소스·V10 원본·V11 10시험을 읽어 다음 반례를 찾았고 V12 사본에서만 정정했다.

- stdin 실행의 __file__가 detached wrapper 경로를 보장하지 않음 → 업로드된 실제 wrapper 경로를 실행하고 SHA 확인.
- 승인·직접 stage·직접 transport의 재사용/정책 변경 → 고정 승인 SHA의 사용·단계·A transport 소비, 봉인 policy·장부·키·B 원본·현재 예산 대조를 API 전에 수행.
- 원래 테스트의 /workspace 준비 경로 및 spec guest_root 불일치 → 실제 job root 경계와 spec을 동일하게 묶음.
- ADMIN/probe의 파일 몇 개만 회수하고 임시 원본 누락 → 전체 생성 원본 ZIP/닫힌 작업 증명/로컬 모든 해시를 삭제 관문에 연결. 준비한 입력 ZIP·불변 source는 hash anchor로 보존하며 동적 .simulated/실제process_cases는 회수 범위에 포함.
- status의 간접 ADMIN callback이 phase deadline 무시 → API timeout을 남은 시간 안으로 제한하고 조회 뒤 시각·watchdog 재검사.
- SafetyStop과 키/permission 오류를 연결 유실로 취급 → 신원·종료 통제·키 오류 즉시 중단; 알려진 연결 오류/단절 timeout만 재조회.
- gate 업로드 뒤 실제 launch 여유 재검사 누락 → 마지막 API 뒤에도 140초 작업+96초 회수+launch 여유가 있어야 A를 시작.
- 새로운 probe에 이전 writer/recovery flag가 남음 → 새 exclusive job마다 초기화, 각 회수 최대3회.
- 회수 뒤 중복 SSH fetch가 불필요한 실패를 추가 → 이미 검증된 회수 원문으로 판정.
- pytest fixture의 심볼릭 링크를 원본으로 따라갈 위험 → 지정된 ADMIN_TESTS 임시 경로만 링크 문자열을 manifest metadata로 보존. 연구 경로·다른 역할·외부 경로는 거부.
- Python 최적화 환경에서 준비/로그 회수의 assert 검사 소실 → 명시 if/raise로 신원·경로·파일 범위를 검사하고 로그 결과의 instance_id도 실제 PID1 값으로 작성.

실제 새 worker/setsid 하위 writer/launch 응답 유실/실패 종료/timeout/미확인 PID/다른job/PID 재사용의 시험 소스를 추가했다. 시험 결과는 아직 없다. Linux subreaper와 /proc는 봉인된 정상 실행 경로의 증거이며 악성 root를 독립 인증하는 수단이 아니다.

준비의 빈 폴더 재확인·준비 로그 읽기·SCP·상태 조회·닫힌 회수에는 동일 서버/동일 절대시간/최대3회 연결 재검증이 있다. 원본 추출(source_verify)은 동기 경로로 남고 연결 유실 시 작성자 상태가 불명확하므로 추출 중복 실행을 하지 않는다. 그 경우 STOP/부분회수/보존이며 모든 행정 오류가 자동 복구된다고 주장하지 않는다. 실제 문제 수정은 기존 원본·봉인과 승인 창을 보존한 별도 버전으로 하며 물리 계산 재실행 권한을 늘리지 않는다.

사용자 최신 검색 정정은 search_contract_amendment.txt다. 개별 반복 저장 요구 철회/추가93회 금지. 원래 A320·100/1000/10000 각각31회 검색·중앙값/최댓값·완료 증거만 검증한다.

패키지 마지막 확인은 capsule/operational_seal 생성 시 V1–V11 원본 해시, 기존 V11 10시험 원문, A814 ZIP의 전 멤버·고정320 목록을 직접 대조해 외부 정적 영수증에 보존한다. ADMIN capsule은 새 seal의 자기참조를 포함하지 않으며 외부 봉인의 ZIP SHA가 입력을 고정한다. 실제 최신 별도 검토 기록은 후보 외부 증거에 추가 보존한다.
