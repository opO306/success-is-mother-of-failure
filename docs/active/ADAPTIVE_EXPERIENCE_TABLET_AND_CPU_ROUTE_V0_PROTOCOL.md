# 경험 탭 및 CPU 경로 V0 — 실행 전 봉인

2026-10-08 KST, 기준 `codex/adaptive-execution-real-learning-pilot-a-resume-v1 @ 2fa56010`.
새 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`. 로컬 동적 시험 금지, 유료 실행 미승인.
원문 요청은 이 단계 자료 폴더에 그대로 보존한다. 코드보다 먼저 protocol.json과 보호 바이트 목록을 커밋한다.

기존 selector.placements는 SMT 형제 중 하나만 사용한다. quota를 정수 부분으로 제한하며 W3는 네 물리 코어, W4는 다섯, W6는 여섯을 사용한다. W6는 main과 마지막 worker가 같은 CPU다. ExecutionPlan 및 adapters.validate_plan을 그대로 사용한다. 검증 어댑터가 현재 요청의 CPU 정확성 계약을 대신 확인하는 것은 아니므로 check_request도 호출한다. 기존 fixed 함수가 W3/W4 계획을 생성할 수 있지만 실제 learning service 연결은 SERIAL/W6만 자격을 주장한다.

환경 수집기는 Linux sysfs와 Windows group 0의 물리 코어를 읽지만 cache/NUMA/ISA/혼합 코어 능력과 quota 관측 성공 여부를 구분하는 필드를 제공하지 않는다. 기존 env_id는 수정하지 않는다. 새 읽기 전용 설명에서 cache/NUMA/ISA는 UNKNOWN, quota observation과 homogeneous core attestation은 호출자가 근거를 제공해야 한다. 이 V0는 Linux만 후보 자격을 준다. 미확인 혼합 코어와 일부 코어 누락, 관측하지 못한 quota는 REFUSED다. CPU 구조 정보만으로 CPU가 실제 더 빠르다는 판정은 하지 않는다.

탭은 기존 원본 파일을 복사하거나 수정하지 않는다. 작은 JSON 색인과 불변 참조 capsule이 원본을 가리킨다. capsule 등록/재구성 때 전체 관련 증거를 검사하며 평상시에는 정확한 요청 key의 최대 64개 후보만 검사한다. 원본 탐색·검사는 색인과 분리한다. 색인은 권한이 없고 private key를 받거나 보관하지 않는다. inspector/manager의 공개 root는 호출자가 별도로 제공한다. 자기 capsule에 든 키만으로 신뢰를 만들지 않는다.

실제 경험 등록은 기존 REAL_PILOT 서명 검증과 A resume check_receipt를 재사용한다. OFFLINE_CONTRACT_ONLY는 시험 자료로만 보관한다. 현재 세션 판정은 문제 key·세션 전체 digest·env_id 일치와 기존 manager의 snapshot 확인을 모두 요구한다. 다른 세션은 모델명/env_id가 같아도 TRANSFER_HINT_ONLY다. snapshot은 탭이 만들거나 활성화하지 않는다. 복귀 후 새 snapshot은 기존 정책을 유지한다. 과거 snapshot의 유효성은 기존 manager의 규칙에 따른다.

과거 실제 A의 완료/실패 원문, profile/cost/서명/복귀를 보호한다. 지원하는 최초 실제 자료 형식은 A resume V1의 SERIAL/W6, 각 5개 실측과 전체 요청 비용이다. 다른 형식과 GPU 경험은 REFUSED 또는 INCOMPATIBLE로 보존하며 지원을 추측하지 않는다. T/p/목표/물리·수치/source key가 다르면 해당 요청에 사용하지 않는다. 중복 profile/session은 가중치나 신뢰를 늘리지 않는다. 손상 자료는 재승인하지 않고 REFUSED 목록으로 보존한다. 색인 손상은 STOP 후 명시적 재구성이 필요하다.

학습 가치 판단은 기존 knowledge.value에 보수적 이익 하한과 검증된 기준 비용, 예상 재사용 수, 학습·검사 비용, 시간·예산·불확실성 정보를 넘긴다. 결과는 제안이며 execution_authorized=false다. 5회 실측 규약과 CPU_MIN 직렬 원칙을 낮추지 않는다.

비용 시험은 100/1000/10000건의 합성 색인, 각 31회로 봉인한다. 검색 wall/CPU와 메모리·직렬화 크기 증가, 후보 생성 비용, 실제 선택 원본 검사 비용을 구분한다. 색인 검색 중앙값 10ms는 목표이며 미측정이다. 상주 검사관/GPU 0. Linux 원격 시험은 기존 254개와 신규 시험을 같은 트리에서 수행하며 물리 guard를 적용한다. 실패·error·skip 또는 예산 초과는 STOP, 로그를 남기며 다음 단계 자동 실행 0.

원격 제안: Linux CPU 1개, 계산 wall/누적 CPU 120초, AS/RSS 512MiB, 전체 할당 600초, 회수 마감 420초, 종료 확인 180초, 시간당 $0.25/총 $0.05 상한. 대상 서버는 미선정이며 새 사용자 승인 없이는 조회 외 임대/재시작/전달/실행을 하지 않는다. 외부 guardian을 먼저 ARMED하고 원본 회수·SHA256 확인 후 COMPLETED/FAILED/DEADLINE을 전달해 actual exited를 확인한다. 3회 실패 중단과 전체 예산을 유지한다.

`RwForce` 공유, OS 권한 격리 부재, 공식 통합 회귀 미완료를 유지한다. 탭은 연구 도구로 준비하며 운영 서비스에 연결하지 않는다. 제한 시험이 끝나기 전 TABLET_INDEX_OFFLINE_VALIDATED 또는 CPU_ROUTE_CANDIDATES_OFFLINE_VALIDATED를 발급하지 않는다.
