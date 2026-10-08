# 실측 A 운영 보충 — 원래 runbook 보존

2026-10-08. A만, 상품53170012/machine56006/FR, 시간당0.25·총0.25·60분.
사용자가 서버를 준비한다. 임대/시작/재시작 자동 명령 없음. 새 인스턴스 ID와 SSH 주소를 받아
fresh API 가격·running·machine/country를 확인한다. 다른 작업과 공유하지 않고 완료/실패 때 정지한다.

## 준비 및 시간 원점

외부에 독점 종료 lease를 만들고 사용자 시작 시각을 기록한다. 제공되지 않은 경우 최초 running
외부 관측을 시간 원점으로 쓰되 `allocation_start_provenance=FIRST_OBSERVED_RUNNING; EARLIER_TIME_UNKNOWN`
으로 명시한다. 관측 이전 청구·대기를 숨기지 않고 경제성 전체 인증은 보류한다.
외부 guardian은 시작 전에 봉인된 최신 파일과 A supplement를 사용한다. lease:
scope STOP_CONTROL_ONLY, exclusive true, explicit_user_approval true, approval_reference,
instance_id/machine_id/country, guardian_sha256, completion_marker, stages ['A'],
safety_policy_sha256, allocation_start_utc/provenance, deadline_seconds3420.
allocation_start+3240 compute 종료, +3420 회수 종료/강제 정지, +3600 정지 확인 상한이다.
처음 ARMED 뒤 준비·파일 전달이 3분 넘게 걸려도 신선한 외부 control pulse와 남은 예산으로 판단한다.

## 전달 및 원격 오프라인 관문

밖에서 guardian ARMED 확인 → fresh ZIP 전달/raw 해시/원문 확인 → 게스트 안내·CPU topology/
quota/memory·수치 환경 확인. 전달 ZIP에 원래 N14/N12 replay가 있는지 확인한다.
게스트에서 relay 대상의 `/workspace/<fresh>/heartbeat.json` 경로를 준비한다.
밖에서 heartbeat_relay.py를 숨김 프로세스로 실행한다. 이는 SSH를 통해 관리 JSON만 전달하며
계산기·시험·임대·시작은 호출하지 않는다. 장기 통신 장애의 완전한 정지 보장이 아니다.

원격 offline 승인에는 기존 gate/explicit_user_approval/reference/code_seal/instance와 scope OFFLINE_ONLY,
machine56006/countryFR/safety_policy_sha256/hourly_cap_usd0.25/heartbeat_path,
physics_calls0/gpu_calls0을 기록한다. 같은 승인 파일 폴더의 armed.json과 현재 heartbeat가 일치해야 한다.
CPU1, runner wall/누적CPU120초, 프로세스별 주소 공간512MiB, 총142개 skip/error/fail0을 요구한다.
새 물리 계산은 이 시험에서0이다. 누락된 패키지를 자동 설치하지 않는다. 필요한 설치는 별도 환경
준비로 범위·버전·시간을 기록하고 기존 정확성 조건 mpmath1.3.0/python backend를 유지한다.
재검증 FAIL이면 실제 계산을 시작하지 않고 실패 원본을 회수한 뒤 FAILED를 밖의 marker에 쓴다.

## 실측 A

fresh remote authorization: scope REAL_RESEARCH, stages ['A'], 해당 exact instance/machine/country,
explicit_user_approval/reference, actual code seal, hourly_usd<=0.25,
approve_research_profile true, safety_policy_sha256, heartbeat_path. 기존 runner CLI를 사용한다.
외부 guardian 상태는 5초 기록/15초 API 상태 재확인, guest TTL45초+미래 시계 허용2초,
lease/ARMED hash/instance/machine/국가/순번/CONTROL_OK 확인. 실행 직전과1초 RSS watcher에서 검사한다.
이는 신뢰된 관리 relay 경로이며 같은 UID 공격에 대한 OS 격리가 아니다. 상태 조회 성공은 앞으로
정지 요청 권한이 취소되지 않을 것의 증명도 아니다. 실제 정지 응답·actual 상태로 확인한다.

같은 초기 상태 p163 CPU직렬/W6 각각5회, 교대 순서, fresh replay, 각 결과 즉시 검사,
별도 검사관의 원본 판독/서명, 관리자 위임 승인, 다음 실제요청1회, LEGACY 서명 복귀.
첫 직렬 요청은5회 안에 포함한다. 과거 성능을 주입하지 않는다. N14 GPU실행·B 자동진행은 금지다.
p163 재시도/변동비1.25 초과 등 충분한 프로필을 만들 수 없으면 중단·증거 보존한다.

## 회수, 종료, 경제성

report/서명/원장/모든 실패 파일을 exclusive ZIP으로 묶고 raw 목록을 만들어 회수한다.
밖에서 원격/로컬 raw SHA를 대조한 뒤 COMPLETED를 지정 marker에 기록한다.
시간이 부족하면 추가 계산을 중단하고 가능한 증거만 회수한다. 강제 회수 기한을 연장하지 않는다.
정확성/무결성/승인 위반은 FAILED, 완료된 scientific NOT_READY는 원본 보고서와 구분한다.
actual exited/stopped를 확인한 final.json과 fresh API 상태를 회수한다. 확인 실패는 경고·수동 확인이다.
원격 결과가 생겼다는 이유만으로 회수 전에 정상 COMPLETED를 보내지 않는다.

외부의 원점/준비/전송/대기/회수/종료 확인 시각과 raw 가격을 별도 보존한다.
runner job_total은 내부 비용이며 전체 할당 손익은 a_safety.allocation_cost로 따로 계산한다.
외부 total_wall - 첫 직렬 요청 - 실제 learned request를 보수적인 전체 학습 overhead로 계상한다.
한 번 관측한 절감만 realized 이익으로 쓰고 break-even에서 이미 수행한 재사용1회를 따로 명시한다.
할당 시작 이전 비용이 미확인인 경우 UNKNOWN_ALLOCATION_START로 두고 COST_USEFUL 승격을 금지한다.
청구 영수증 없이는 RATE_ESTIMATE이며 전송료까지 확인되지 않은 값은 전체 금액 인증이 아니다.
학습 순환 성공은 경제성 성공과 다르다. RwForce 공유·OS 격리·실제 FAILED·장기 통신 장애 한계를 보고한다.
