# 경험 탭 및 CPU별 경로 V0 — 소스 준비 결과

2026-10-09 KST. 정책과 최초 시험은 2026-10-08에 기록했다. 기준 `2fa56010`, 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`, 구현 소스 커밋 `7b264a42936e3aa0359def3521bb3d13d4b4741e`.

**SOURCE_PREPARED / REMOTE_TEST_PENDING / COST_BENCHMARK_PENDING / NOT_PRODUCTION.**
로컬 동적 실행 금지와 새 유료 실행 별도 승인 조건을 유지했다. 따라서 TABLET_INDEX_OFFLINE_VALIDATED와 CPU_ROUTE_CANDIDATES_OFFLINE_VALIDATED는 아직 발급하지 않는다. 실제 다른 CPU의 성능이나 교육비 절감도 미확인이다.

## 구현된 동작과 재사용

반장은 작은 색인에서 같은 문제의 과거 경험을 찾는다. 선택한 경험의 원본·검사관 서명·관리자 승인·복귀 이력을 확인하고, 현재 CPU에서 기존 경로 중 배치할 수 있는 후보를 만든다. CPU/세션이 바뀐 과거 성능은 참고 자료로 남긴다. 현재 세션의 승격은 기존 관리자가 동일 세션과 승인 프로필 snapshot을 확인해야 한다. 탭은 관리자 권한을 갖지 않는다.

| 새 파일 | 실제 구현 범위 |
|---|---|
| catalog.py | JSON 색인, exact problem key 검색, 불변 원본 참조, 공개 root 결합, 선택 원본 재검사, 중복 억제, 손상 STOP/명시적 재구성 |
| host.py | 기존 env_id를 보존한 환경 설명·차이 비교, quota 관측/동질 코어 근거 확인, cache/NUMA/ISA UNKNOWN |
| routes.py | selector.placements/check_request/fixed, AdaptivePlan.execution_plan, adapters.validate_plan/executed_matches 재사용. SERIAL/W3/W4/W6 후보와 재검사만 수행 |
| policy.py | CURRENT_SESSION_VERIFIED/TRANSFER_HINT_ONLY/NEEDS_CALIBRATION/INCOMPATIBLE/REFUSED 분류, 기본 직렬, 기존 knowledge.value를 이용한 보수적 학습 제안 |
| offline.py | 새 승인·소스·외부 guardian 결합 확인, 원격 제한 pytest와 검색/후보/선택 원본 비용 측정 준비, JUnit/예산/guard 관문 |
| protocol.json 및 봉인 | 구현 전 정책, 보호 원본, 정확한 실행 예상 항목·소스 패키지 결합 |

기존 environment.py/selector.py/adapters.py/ExecutionPlan, 검사관, 관리자, 경험 원장, CPU/GPU 계산기, RwForce, 물리·수치 계약, P2, 반올림, 초기 상태 재시작, 기존 V1 CPU_MIN 직렬 규칙은 수정하지 않았다. 원본 개인 서명키를 읽거나 탭에 보관하지 않았다. 시험에 있는 임시 키 생성 코드는 실행하지 않았으며 연구 모듈에는 서명기나 키 생성 함수가 없다.

현재 소스가 등록하는 실제 형식은 **A resume V1의 승인된 SERIAL/W6 각 5회 프로필**이다. 이전 버전·GPU·OFFLINE_CONTRACT_ONLY 비용 원장의 자동 등록은 지원하지 않고 REFUSED한다. 기존 OFFLINE_CONTRACT_ONLY 관리자는 복귀 회귀 시험에만 재사용한다. 이는 모든 옛 경험 형식을 이미 가져올 수 있다는 구현이 아니다.

## 저장 및 경량 검색

기존 원본 보관함은 archive_root로 지정한다. tablet/references에는 원본 상대 경로·원본 해시·공개 root 지문·문제 key·측정 범위·서명 승인/복귀 참조를 담는 최대 1MiB capsule을 불변 저장한다. index_<digest>.json은 작은 profile 색인 snapshot이고 index_head.json만 파생 head로 갱신한다. 이전 index snapshot과 손상 원본은 지우지 않는다. 기존 계산 원본은 복제·재작성하지 않는다.

한 경험은 하나의 프로필이며, 10개 관측을 색인 10개로 중복 집계하지 않는다. 같은 프로필 재등록은 새 신뢰를 만들지 않으며 동일 세션·목표의 중복 프로필도 거부한다. 반환한 검색 결과를 수정해도 메모리 색인을 수정하지 않는다. 검색은 요청 key의 메모리 사전을 보고 최대 64개만 반환하며 원본 파일을 열지 않도록 작성했다. 선택 원본 검사와 대량 재구성은 별도 경로다. 등록된 참조를 보존한 경우 재구성이 가능하고, 참조까지 잃으면 기존 승인 원본 위치/프로필/승인 이벤트로 다시 등록해야 한다. 색인의 모든 과거 경험 누락 여부를 암호학적으로 인증하는 기능은 없다.

source/precision/goal 계약이 다른 경험을 그 요청의 비용으로 사용하지 않는다. 가능한 W3/W4에 비용 자료가 없으면 NEEDS_CALIBRATION이다. 동일 모델 또는 동일 env_id라는 이유로 다른 세션을 승인하지 않는다. 현재 manager가 인정한 동일 세션 snapshot이 없으면 기존 직렬 제안을 유지한다.

**비용 한계:** lookup은 작은 색인만 보지만, CURRENT_SESSION_VERIFIED 판정과 safe_method의 명시적 현재 프로필 선택은 기존 Manager.choose를 그대로 호출한다. 기존 관리자의 소스 봉인 재검사 비용을 삭제하거나 경량화하지 않았다. 현재 선택 경로의 전체 관리 비용, 중복 관리자 검사 제거, 실제 서비스 연결은 미검증/후속 대상이다. 이 준비의 검색 10ms 목표를 전체 서명·원본·관리자 검사 시간으로 해석하면 안 된다.

색인·참조는 경험 수에 따라 늘어나는 구조다. 100/1000/10000건에서 실제 저장 크기·검색 wall/CPU·Python heap peak 증가를 측정하는 코드를 작성했으나 실행하지 않았다. 따라서 검색 10ms, 메모리 사용량, 10배/100배 증가 추세의 수치 성과는 아직 없다. capsule의 최대 허용 크기 1MiB는 예산 정책이고 측정값이 아니다. 새 상주 검사관이나 GPU 작업자를 실행하지 않았다.

## CPU 후보와 현재 PC

다음은 기존 소스를 읽어 얻은 규칙과 새 모의 시험의 **예상 결과**다. 이 변경 트리에서 동적 확인하지 않았다.

| 확인된 서로 다른 물리 코어와 quota | 후보 |
|---|---|
| 1~2 | SERIAL |
| 4 | SERIAL, W3 |
| 5 | SERIAL, W3, W4 |
| 6 이상 | SERIAL, W3, W4, W6 |

W6는 main과 마지막 작업자가 같은 CPU를 공유하고 여섯 물리 코어를 요구한다. 7개 필요 또는 5개 충분으로 바꾸지 않았다. SMT 형제는 중복 계산하지 않고 비연속 affinity를 유지한다. quota는 올림하지 않는다. OS 허용 목록·물리 코어 식별·quota 관측·수치 계약·계획 검사 중 하나라도 불명확하면 낙관적으로 후보를 허용하지 않는다. 실행 전 재검사 함수는 준비했지만 실제 실행기는 연결하지 않았다.

읽기 전용 Windows CIM 조회: **AMD Ryzen 5 5600 / 물리 6코어 / 논리 12개 / Windows 11 Home 10.0.26200**. 조회한 PowerShell 프로세스 affinity mask는 4095다. 각 논리 CPU의 물리 코어 대응은 이번 조회에서 수집하지 않아 UNKNOWN이다. 이것을 실제 Python 실행 배치로 간주하지 않는다. [조회 원본](adaptive_experience_tablet_v0/local_hardware_readonly.json)을 보존했다.

V0는 Linux의 명시적으로 관측된 quota와 동질 코어 근거를 요구한다. Windows/macOS, 혼합형·미확인 core class, 일부 코어 식별 누락, quota 관측 불명, 기존 mpmath/물리·수치 정확성 계약 밖의 환경은 REFUSED다. Windows에서 기존 environment 수집 기능이 존재한다는 사실을 이 새 연구 경로의 실행 자격으로 확대하지 않았다. W3/W4의 실제 학습 서비스 연결은 여전히 미구현이다.

## 확인된 것과 실행하지 않은 것

| 구분 | 현재 증거 |
|---|---|
| 구현됨 | 연구 namespace의 소스와 원격 시험 진입점. 운영 서비스 연결 0 |
| 정적으로 확인됨 | 새 Python 7개 파일(시험 포함)의 AST 문법 파싱 성공, 보호 794개 raw hash 불일치 0, 이전 코드 봉인 683개 raw 불일치 0, git diff --check 통과 |
| 오프라인 시험됨 | **이번 변경 트리에서 미실행. PASS/FAIL/ERROR/SKIP 실측 없음** |
| 예상 시험 수 | 기존 254 + 신규 66 = **320**. literal pytest 매개변수를 AST로 펼친 숫자이며 실제 pytest 수집·JUnit 수치가 아님 |
| 실제 CPU에서 측정됨 | 이 단계의 계산·검색·후보 생성·관리 비용 측정 0. 현재 PC의 읽기 전용 하드웨어 조회만 수행 |
| 독립 검증됨 | 이 단계의 새 independent 검사관 영수증/별도 검토 0. 옛 실제 A의 서명·결과는 불변 보존하고 시험 입력으로 참조 |
| 미확인 | 현재 선택 경로 전체 비용, 다른 CPU의 유리한 경로, 교육비 감소, 전체 회귀, OS 격리, 수식 독립성, 운영 적용 |

시험 코드는 기존 실제 서명 원본과 임시 변조 복사본, 모의 CPU 구조를 사용한다. 다른 세션의 최소 승격 반례, 정확성·정밀도·목표·source 혼입, quota·SMT·affinity 변경, 기록 배치 불일치, 잘못된 공개 root·서명·원본, 중복·색인 손상·1000건 손상 참조, 이전 snapshot과 서명 복귀, 미래 재사용 정보 부족의 자동 실행 금지를 담았다. TDD의 동적 RED/GREEN은 로컬 금지 때문에 수행하지 못했다. 처음 작성한 시험 commit과 후속 반례 추가 commit을 각각 보존한다.

**LOCAL FULL 생략 / 관련 시험으로 대체 예정이나 아직 미실행 / 이유:** 사용자 로컬 동적 시험 금지 및 새 원격 실행 별도 승인 조건. 기존 실행 코드·공용 로직·동결 fixture를 바꾸지 않은 연구 namespace 추가지만, 관련 시험도 아직 실행하지 않아 검증 완료를 주장하지 않는다. 공식 LOCAL FULL 기준선 숫자는 갱신하지 않았다. 기존 실제 A의 254 passed는 과거 증거이며 이 320개의 결과를 대신하지 않는다.

## 구상 일치성의 별도 검토

작성자가 소스 흐름을 다시 검토했다. 탭은 원본을 찾는 역할이며 검사관/관리자 권한을 새로 만들지 않는다. 과거 CPU 성능의 무단 승격 경로를 차단하는 조건을 넣었고, 후보 생성은 실제 최적 경로 판정과 분리했다. 수학적 계산 경로·P2·물리 법칙을 생성하지 않는다. 기본 직렬 선택과 CPU_MIN은 유지하고 학습 가치는 예상 재사용·검증된 기준 비용·보수적 후보 비용·시간/요금/위험 조건이 없으면 보류하며 execution_authorized=false다.

그러나 이것은 **작성자의 정적 개념 검토**다. 신규 시험을 실행한 2차 검증이나 독립 감사 완료는 아니다. archive 상대 경로 이전을 지원하지만 원본 보관함 자체의 자동 운송·모든 옛 자료 형식·실제 서비스·W3/W4 학습 연결은 준비하지 않았다. 현재 선택의 기존 관리자 심층 검사 비용도 유지되어 비용 목표 충족은 미확인이다.

`RwForce` 공유, 동일 UID에서의 OS 권한 격리 부재, 공식 통합 회귀 미완료를 유지한다. 옛 REAL_LEARNING_FAIL과 이후 REAL_LEARNING_LOOP_VALIDATED/COST_NOT_YET_RECOVERED 기록을 고치지 않았다. 실제 다른 CPU에서 같은 N14/T1000/p163의 유리한 경로가 달라지는지와 탭으로 전체 교육비가 감소하는지는 별도 유료 실측의 질문으로 남는다.

## 봉인·패키지·다음 경계

정책 봉인 `3c251ea8`, 최초 시험 `74b30e7b`, 현재 세션 snapshot 시험 보강 `e3c2ff14`, 손상 자료/경로 반례 `7f0610d1`, 구현 및 정적 자료 `7b264a42`를 보존했다. [정적 점검](adaptive_experience_tablet_v0/static_checks.json), [예상 시험 목록](adaptive_experience_tablet_v0/static_test_inventory.json), [코드 봉인](../../experiments/adaptive_experience_tablet_v0/code_seal.json)이 있다.

코드 봉인 SHA256 `18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09`.
[전달 ZIP](adaptive_experience_tablet_v0/source_7b264a42/source_7b264a42.zip)은 **813개 항목 / 36,740,453바이트**, 비압축 합계 48,533,194바이트다. SHA256 `ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392`. 항목 중복 0, 원문 hash 불일치 0, CRC 오류 0을 재개방해 확인했다. [패키지 원문 목록](adaptive_experience_tablet_v0/source_7b264a42/package_manifest.json)을 보존했다. 기존 보호 파일의 Git EOL 차이를 재작성하지 않았으며, 패키지 raw 바이트가 전달 기준이다.

실제 변경은 새 `experiments/adaptive_experience_tablet_v0/`, 새 시험 한 파일, 새 프로토콜/준비 보고와 `docs/active/adaptive_experience_tablet_v0/` 자료뿐이다. 기존 추적 파일 변경 0, 새 worktree 0, GitHub push/master 병합 0이다.

[원격 계획](../../experiments/adaptive_experience_tablet_v0/REMOTE_RUNBOOK.md)은 Linux CPU 1개, wall/누적 CPU 각 120초, AS/프로세스 트리 RSS 512MiB, 전체 할당 600초, 회수 마감 420초, 정지 확인 180초, 시간당 $0.25/총 $0.05 상한이다. 서버는 미선정이며 임대/재시작/전달/동적 시험을 하지 않았다. 실제 대상과 요금·잔여 예산·외부 guardian/marker 운송을 확정한 새 승인 후에만 320개 관문과 비용 측정으로 진행할 수 있다. 다음 단계로 실제 다른 CPU 성능 실측을 자동 시작하지 않는다.
