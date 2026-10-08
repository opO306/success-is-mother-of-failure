# EVIDENCE_CANONICALIZATION_AND_LIGHTWEIGHT_VERIFICATION_V0 — 소스 준비

2026-10-08 / SOURCE_PREPARED / TEST_EXECUTION_PENDING / NOT_PRODUCTION

현재는 구현과 봉인, 원본 보존 확인까지 완료했다. 새 동적 시험, 검사관의 과거 증거 재검토, 경량 검사 비용 측정은 아직 실행하지 않았다. 따라서 EVIDENCE_FORMAT_V0_READY나 HISTORICAL_REVIEW_COMPLETE로 판정하지 않는다. 과거 프랑스 실측 A의 REAL_LEARNING_FAIL도 그대로 유지한다.

## 1. 기준과 먼저 봉인한 내용

실제 Git 기준은 `codex/adaptive-execution-real-learning-pilot-a @ 621548789a6857178f8070e98cc8fef77c6f8f2b`였다. 새 브랜치 `codex/evidence-canonicalization-lightweight-v0`에서 작업한다. master는 `15ae151851a163f4360b0c6930a3ba9308999f8c`이고 병합·push하지 않는다.

작업 전에 AGENTS.md, RULES.md, CURRENT_STATE.md, REPO_MAP.md를 읽고 실제 파일을 확인했다. 실행 및 유료 자원의 허가는 사용자 계획서에 따른다.

| 단계 | 로컬 커밋 | 봉인한 내용 |
|---|---|---|
| 프로토콜 선봉인 | `34386674` | INITIAL_STATE_CANON_V2, 버전 거부, 저장 즉시 판독, 원본 보존, 관리자 경계, 1% 비용 기준, 제한 원격 예산 |
| 시험 먼저 작성 | `e33455bd` | 실제 저장 파일·변조·승인 경계 시험 44개 |
| 수치 문자열 규약 보충 | `92e1e1af` | 원본 운동량의 `-6/7`, `-1/7`을 문자열 그대로 허용; 추가 결함 시험 8개 |
| 제한 구현 | `c3243b5b` | 작은 증거 모듈과 기존 pilot의 저장·판독·검사·관리자 연결부 |
| 새 코드 봉인 | `d4b65b00` | 별도 코드 manifest와 승인 대기 원격 runbook |

수치 문자열 보충은 새 내용을 코드 적용 전에 별도로 봉인했다. 소수·지수 문자열과 정수 분자/0이 아닌 양의 정수 분모 문자열을 허용하되, 계산·약분·반올림·표현 통일을 하지 않는다. `1`, `1.0`, `1/1`은 서로 다른 내용으로 남는다. 초기 상태 필드 `p`는 운동량이며 계산 정밀도 p와 별개다.

## 2. 이전 결함과 이번 수정

이전 producer는 초기 상태를 q,p 순서로 직렬화해 initial_sha256을 만들었다. 저장기는 키를 정렬해 p,q 순서로 저장했고, inspector는 다시 읽힌 순서로 과거 직렬화를 적용했다. 실제 값이 같아도 해시가 달라졌다. 이 진단과 과거 실패 기록은 원본에 남아 있다. 이번 독립 재검토의 실행 결과는 아직 없다.

새 기록은 원본 바이트 SHA-256과 INITIAL_STATE_CANON_V2 내용 지문을 구별한다. 내용 지문은 정확히 q,p 필드만 UTF-8 JSON의 정렬된 키·고정 구분자로 직렬화한다. 원자와 좌표 배열 순서, 각 수치 문자열은 그대로 둔다. 중복 키, 누락·추가 필드, 잘못된 배열, 비정상 숫자 문자열을 거부한다. 기존 initial_sha256은 명시적인 q 다음 p 규약 LEGACY_QP_JSON_V1을 유지한다.

새 live session과 기록에는 버전과 정책 해시가 모두 필요하다. 버전 삭제·낮춤은 과거 호환 경로로 통과하지 않는다. 과거 버전 판독은 해시로 고정된 프랑스 실패 원본에 대한 별도 읽기 전용 모드에서만 허용한다.

bridge는 원본을 독점 저장한 직후 실제 파일을 엄격하게 다시 읽고, 저장 전 메모리 자료와 전체 저장 자료, 요청·계획·초기 상태·결과·지문을 비교한다. runner가 받는 객체도 이 재판독 자료다. 실패 시 원본과 거부 이유를 남기고 예외를 반환해 다음 계산과 replay를 차단한다. 경량 검사에는 새 물리 계산이 없다.

## 3. 검사관과 관리자 경계

기존 inspector에 단발 historical review 모드를 추가했다. 새 검사관이나 상주 프로세스는 만들지 않았다. inspector는 원본 ZIP·개별 파일·세션·기존 replay·보호된 초기 상태를 직접 판독하고 내용과 비용 기록을 재도출한다. 생산자의 합격 표시는 승인 근거가 아니다. 직렬화 규약을 공유하는 것과 힘 수식의 완전 독립성은 별개다.

FORMAT_EQUIVALENT, CONTENT_MISMATCH, PROVENANCE_UNKNOWN, VERIFIED_CONTENT를 구별한다. 정정증명서는 원본 경로·raw hash·기존 및 새 지문·규약·코드 봉인·검사 영수증을 참조하는 별도 파생 자료다. 원본을 고치지 않는다.

기존 서명 영수증과 관리자 승인 절차를 사용한다. 관리자는 서명과 원본을 다시 확인하며 별도 명시적 승인 없이는 정정 자료를 승인하지 않는다. 이번 원격 제안은 관리자 승인 PENDING을 유지하고 공식 성능 프로필을 활성화하지 않는다. 과거 세션에서 학습 후 요청·복귀가 성공했다고 기록하거나 새 호스트에 비용 지식을 자동 적용하지 않는다.

RwForce 공유 문제는 여전히 미해결이다. 파일·해시·서명 수준 분리는 같은 OS 사용자 권한의 격리와 같지 않다. 서로 다른 OS 계정, 보호된 신뢰키/관리자 저장소, 코드 변경·키 접근 통제는 별도 보안 설계와 검증이 필요하다. 독립 수식 인증, OS 권한 격리, production 연결을 완료했다고 주장하지 않는다.

## 4. 변경 범위와 보존 확인

새 작은 모듈은 `experiments/evidence_canonicalization_v0/`에 둔다. 기존 pilot의 common, bridge, runner, replay_worker, inspector, governance에는 명시적인 새 manifest 및 증거 경로를 연결했다. 기존 pilot 시험의 mock session·request 식별자를 새 명시적 계약에 맞췄고 시험 수 65개는 유지했다.

기존 Verification V0, Learning V1, Adaptive Execution V1, CPU/GPU 계산기, 물리식, 반올림, 구간 산술, P2와 GPU 지원 범위는 수정하지 않았다. 원래 상태에서 재시작하는 수치 경로도 수정하지 않았다. 과거 봉인된 소스 ZIP과 과거 code_seal.json은 보존했다. 새 manifest는 과거 manifest로 자동 fallback하지 않는다.

이번 로컬 행정 확인에서는 다음 raw 바이트를 모두 SHA-256으로 대조했다. 이것은 독립 내용 검사나 동적 시험 결과가 아니다.

- 보호 대상 기존 파일 282개: 불일치 0.
- 기존 프랑스 보존 manifest의 파일 105개: 불일치 0. manifest 자체는 역사 pin으로 별도 보존한다.
- 새 code_seal의 465개 파일: 불일치 0.
- 전달 ZIP의 466개 항목(465개 + 새 code_seal): 각 항목의 raw 바이트 불일치 0.

원본 68개, 회수 ZIP, 최초 거부 영수증, REAL_LEARNING_FAIL 보고서 및 종료 증거를 유지한다. 기존 replay는 세션·환경·초기 상태·N/T/p·원본/소스 해시의 결합 조건이 맞는 historical review에서만 재사용한다. 새 수치 replay 횟수는 이번 범위에서 0이다.

## 5. 시험과 비용 상태

| 구분 | 현재 확인 |
|---|---|
| 구현됨 | 표준 지문, 엄격한 파일 재판독, 첫 실패 중단, 별도 정정증명서, 기존 검사관 및 관리자 경계, 비용 계측 코드 |
| 시험됨 | 동적 시험 0회. Python AST 구문 판독·시험 함수 수 확인과 위 raw 보존/ZIP 대조만 수행 |
| 독립 검증됨 | 이번 새 코드·과거 내용 재검토·비용 목표에는 해당 없음 |
| 미확인 | 새 시험 52개, 기존 회귀 142개, 10건 과거 내용 재검토, 관리자/서명 결함 검출, 경량 검사 1% 목표, 실제 연결 동작 |

준비한 원격 시험은 기존 Verification 24 + Learning 53 + Pilot 65 + 신규 52 = 194개다. 통과 개수로 보고하지 않는다. 새 시험은 키 순서, 숫자·운동량·배열 변조, 중복/누락 키, 버전 우회, 실제 파일 재판독, 첫 저장 실패 후 계산 중단, 다른 세션, 변조된 정정증명서/서명/관리자 승인, 기존 승인·snapshot·복귀 경계를 다룬다.

비용 benchmark는 보존된 10개 기록을 각 5회 저장·재판독한다(총 50표본). 내용 지문, 과거 지문, 저장, 판독, 경량 비교와 계측 기록 비용을 나누어 보고하고 추가 bytes, Python traced peak 및 RSS 변화도 남긴다. 기존 기록의 wall 시간은 비교용 과거 관측값이고 공식 학습 프로필이 아니다. 각 기록의 5회 중 최대 추가 시간이 해당 과거 wall 시간의 1%를 넘으면 OVERHEAD_NOT_ACCEPTABLE이다. 현재 시간·메모리·1% 달성 결과는 모두 미측정이다.

LOCAL FULL 생략 / 시험 실행 대기 / 이유: 사용자의 로컬 수치·동적 실행 금지 및 새 유료 시험 미승인. 이번에는 기존 pilot 실행 연결부도 수정했으므로 단순 문서 변경 예외로 공식 통합 Gate를 닫지 않는다. 관련 원격 194개도 아직 미실행이며, 실행하더라도 LOCAL FULL과 동일하게 부르지 않는다. 공식 기준선 수치는 갱신하지 않는다.

## 6. 별도 승인 대상으로 준비한 제한 원격 관문

2026-10-08 읽기 전용 Vast API 조회에서 기존 프랑스 인스턴스 54815136 / machine56006은 actual=exited, intended=stopped였다. CPU는 AMD Ryzen 9 3900X, API의 현재 표시 요금은 $0.13462222222222225/h였다. 가격과 상태는 시작 직전에 다시 확인해야 한다. 이번 구현에서 재시작·임대·원격 시험을 수행하지 않았다.

제안은 기존 서버를 별도 승인 후 재시작해 설치되어 있는 환경을 재사용하는 것이다. CPU1, 전체 wall/누적 CPU 각각 120초, 프로세스별 주소공간 512MiB, 새 물리/GPU0, 194개 시험·읽기 전용 재검토·파일 계측 50표본만 수행한다. 시간당 상한 $0.25, 총 $0.10, 할당 10분이다. 현재 시간요금으로 할당 10분은 약 $0.02244이며 실제 과금·전송·저장료는 별도다. 실제 실행시간 예상치 대신 계산 관문 상한 120초를 제시한다.

새 독점 종료 lease와 외부 guardian의 ARMED를 시작 후 60초 안에 확인한다. generic guardian 기한은 최대 300초, 정지 확인에 180초를 확보한다. ARMED 이후 60초 안에 gate를 시작한다. 회수 ZIP과 해시 확인 뒤 COMPLETED/FAILED를 기록하고 정지·actual 확인까지 수행한다. 기한을 자동 연장하거나 서버를 자동 재시작하지 않는다. 이 짧은 guardian은 최초 상태 조회와 기한·완료·실패 종료 경로다. 실측 A의 지속 heartbeat 경로와 같다고 주장하지 않으며 장기 통신 장애 보장은 미검증이다.

새 승인 없이는 이 관문을 실행하지 않는다. 실제 N14 학습 실측 재개에는 이번 관련 시험·과거 내용 재검토·비용 목표의 결과 판독, 정당한 관리자 승인, 새 세션의 명시적 실측 예산과 지속 감시/종료 제어 확인이 더 필요하다. 이번 단계는 N14 실측 재개 허가가 아니다.

## 7. 봉인과 증거 위치

- 규약 SHA-256: `2ffe33d67f2d2e6483f9629e0fb4e0a94c2d7f020a75e6b006aeebacb9344bc1`
- 새 코드 봉인 SHA-256: `8ad79b9e4655ef29ea1ab14f94cfa863db8f7c3214e39ebdea201d341f6e79de`
- 새 전달 ZIP SHA-256: `a9ca1b08451e915205d6c2a0c0b5da57e26a349e0cd38c94fd068bc0e80037ab`
- ZIP 크기: 9,034,131 bytes.
- [전달 ZIP](evidence_canonicalization_v0/source_d4b65b00/source_d4b65b00.zip)
- [행정 대조 기록](evidence_canonicalization_v0/source_d4b65b00/package_verification.json)
- [프로토콜](../../experiments/evidence_canonicalization_v0/protocol.json)·[새 코드 봉인](../../experiments/evidence_canonicalization_v0/code_seal.json)·[제한 원격 절차](../../experiments/evidence_canonicalization_v0/REMOTE_RUNBOOK.md)
- [변경하지 않은 과거 실측 A 보고서](ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0_A_RESULTS.md)

구상 일치성의 코드 검토에서는 기존 검사관의 원본 재도출, 명시적 관리자 승인, 원본 불변, 다음 계산 전 파일 검사, 비용 측정과 첫 실패 중단을 연결했음을 확인했다. 이는 구현자 검토이며 독립 승인이나 실행 증거가 아니다. 새 계층이 수치 계산을 바꾸지 않는다는 경계를 유지하되, 실제 동작과 비용의 증명은 위 제한 관문에 남겨 둔다.
