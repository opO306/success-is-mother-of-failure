# BOUNDED_ADMIN_RECOVERY_V0 준비 결과 — 2026-10-09

판정: **POLICY_AND_STATIC_GATE_PREPARED / DYNAMIC_VALIDATION_PENDING**.
복구·원격 재시험 승인이나 무결성 우회 방지의 동적 입증 완료를 뜻하지 않는다.
기존 경험 탭 결과 **REMOTE_TEST_GATE_FAILED / UNRESOLVED** 유지.

## 실제 변경과 구상 일치

기준 `394d16c9`, 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`에 새
`experiments/bounded_admin_recovery_v0/`, `tests/bounded_admin_recovery_v0/`와 보충 문서·
증거 폴더만 추가했다. 새 문서도 raw byte 보존 속성이 있는 증거 폴더에 보관한다.
기존 경험 탭, 원본 ZIP, 계산식, 서명 검사, 기존 운송·종료 코드는
수정하지 않았다. 최종 파일 목록은 `change_inventory_v2.json`이다.

허용하는 것은 기존 봉인 실행 파일 누락의 정확한 바이트 추가뿐이다. 계산·수치·서명·
변조·서버 식별·종료 제어 오류 또는 혼합/미분류 오류는 자동 복구 금지다.
사전 사용자 승인·독립 원본 확인·추가 전용 패키지·별도 봉인·전체 320개 재시험·
동일 최초 예산을 요구한다. 복구 최대 1회/전체 재시험 최대 1회를 외부 원장에 실행 전에
예약하는 설계이며 실패해도 취소하지 않는다. 실제 예약·실행 어댑터는 미연결이다.

## 확인 수준

| 구분 | 결과 |
|---|---|
| 구현됨 | stdlib 읽기 전용 ZIP/멤버/실행 봉인 참조 관문, 실행 권한 없는 복구 계약 검토기·결과 계약 검토기 |
| 시험됨 | 원래 ZIP 정적 관문: `INCOMPLETE`, exit 2. 813개 멤버 raw hash 일치, 존재하는 실행 봉인의 참조 2,673건 검사, 누락 봉인 1개 검출 |
| 시험 소스 준비 | synthetic ZIP·TEST_ONLY 영수증을 쓰는 결함 주입 95개 경우. Python 5파일 AST 파싱 완료. pytest 실행 0회, 통과 주장 없음 |
| 독립 검증됨 | 새 복구 정책·검토기·결함 주입의 독립 검증 없음. 과거 성공 승인 원본과 현재 파일의 해시 대조는 작성자 교차 확인 |
| 미확인/미구현 | 실제 독립 서명/승인 pin 공급 어댑터, 누적 잔여 CPU/wall 집행, 외부 횟수 예약, guardian/supervisor 복구 연동, 수정 패키지 실행, 320개 재시험·합성 성능 측정 |

정적 관문은 명시적으로 검토한 실행 봉인 15개와 그 참조를 대상으로 한다.
봉인 1개가 없으므로 나머지 14개의 참조 2,673건을 실제 검사했다.
일반적인 동적 파일 접근·Linux 라이브러리·실행 성공 전체를 증명하지 않는다.
계약 검토기는 적합 후보에서도 `execution_authorized=false`다.

## 누락 원인과 기존 원본

누락 파일:
`experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json`.
raw SHA-256:
`ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60`.
과거 성공 원격 시험의 `authorization_used.json`에 고정된 값과 같다.
그 파일의 683개 참조는 원래 ZIP에 모두 있으며 raw mismatch 0개다.
봉인 파일 자체가 빠진 것은 813개 멤버의 해시가 맞는지만 보던 기존 관문이 놓친 의존성이다.

최초 ZIP SHA-256:
`ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392`.
기존 경험 탭 protocol/code/preservation 4/812/794개 바인딩, 운송 봉인 8개 바인딩은
모두 mismatch 0개다. 과거 행정 실패 증거 34개와 승인된 실패·종료 증거 89개도
각각 기존 raw hash와 일치한다. 최초 ZIP·81개 nonpass·320개 JUnit·종료 영수증을
덮어쓰지 않았고 기존 실패 원장의 횟수도 초기화하지 않았다.

95개 새 행정 시험은 기존 320개에 포함하지 않는다. 원래 실패 JUnit에서 320개 고유
case ID를 별도 읽기 전용 inventory로 기록하여 미래에 부분·중복·추가 시험을 전체
관문 통과로 바꾸는 것을 거부할 수 있도록 준비했다. 기존 검사는 그대로다.

## 정적 반례 검토

| 주입/조건 | 기대 중단과 남길 기록 |
|---|---|
| 봉인 파일 누락·참조 파일 누락 | `INCOMPLETE`; 경로 목록 보존, 실행 전 중단 |
| 기존 멤버 변조/삭제·추가 코드·봉인 해시 변경 | `INTEGRITY_REFUSED`; 원본 변경 복구 금지 |
| 잘못된 ZIP 해시·CRC·경로 탈출·중복·링크·암호화·JSON 중복 키 | `INTEGRITY_REFUSED`; 모호한 해석 금지 |
| 외부 inventory/contract pin 누락·변조·자기 선언 영수증 | `REFUSED`; 패키지 자체 선언을 권한으로 사용 금지 |
| 혼합 오류·서명·수치·서버·종료 제어 오류 | `REFUSED`; 원본 보존·정지 우선 |
| 사전 승인 부재/사후 승인·횟수 1회 소진·초기 원장 재설정 | `REFUSED`; 최초 승인과 이전 3회 실패 보존 |
| CPU 미상·512 MiB/CPU 1개 초과·누적 120초 초과·마감/요금 부족 | `REFUSED`; 잔여량 추정으로 통과 금지 |
| 정지한 서버·오래된 제어/예산 관측·더 늦게 바꾼 마감 | `REFUSED`; 재시작 권한 생성 금지 |
| 부분·중복·추가 case·failure/error/skip·미완료 합성 측정 | 결과 계약 `REFUSED`; 320개 모두 통과 요구 |

이는 코드의 정적 검토와 준비한 **시험 기대값**이다. 실제 결함 주입 결과로 표시하지 않는다.
영수증 pin 자체의 독립 인증은 기존 외부 서명 경로가 먼저 담당해야 한다.
검토기에 JSON과 임의 pin을 같이 공급하는 것은 실제 독립 검증이 아니다.

## 준비 도중 오류와 다음 검증

정적 준비 스크립트의 최초 AST 시험 개수 집계가 `ast.literal_eval`의 문자열 곱셈
지원 부재로 1회 실패했다. 동적 프로젝트 시험이 아니며, 실패 기록은
`static_preparation_failure_1.json`에 보존했다. AST List/Tuple 바깥 원소의 수만 세는
방법으로 수정했고 최초 생성 contract·case inventory를 덮어쓰지 않았다.
중간 증거 v1/v2/v3을 보존하며 최종 소스와 맞는 증거는 **v4**다.
원래 ZIP 최종 관문 결과는 **original_package_gate_result_v2.json**이다.
최종 신규 준비 봉인은 `protocol_seal_v2.json`·`code_seal_v2.json`, 원본 목록은
`evidence_manifest_v2.json`이다. 최초 신규 준비 봉인·목록은 문서를 raw 보존 폴더로
배치하기 전의 초안 기록으로만 보존하며 실행에 사용하지 않는다.

LOCAL FULL 생략 / 관련 동적 시험도 미실행 / 이유: 이번 요청은 정책·시험 준비이며
기존 로컬 프로젝트 동적 시험 금지 유지. 공식 전체 시험 기준선은 갱신하지 않았다.
`git diff --cached --check`와 새 파일 staged/raw byte 대조는 별도 Git closeout 기록으로 남긴다.
로컬 커밋만 하며 GitHub push·master 병합 없음.

종료된 기존 시간창은 이 정책으로 되살릴 수 없다. 기존 STOP 원본에는 관문 전체 CPU
사용량도 없어 현재 기록으로 잔여 재시험 예산을 입증할 수 없다. 현재 복구 불허 사유는
사전 정책 승인 부재·이미 종료된 시간창·미상 누적 CPU·새 독립 영수증 미확보다.
추가 유료 서버 임대·재시작·시험을 시작하지 않았다. 다음 동적 시험과 실제 원격 실행은
각각 명시적 승인과 별도 검증 경로가 필요하다.
