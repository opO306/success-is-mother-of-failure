# 제한 원격 관문 — 새 물리 계산 0

이 문서는 승인서가 아니다. 유료 시작·임대는 별도 사용자 승인이 필요하다.
준비된 source.zip과 전체 raw manifest를 원격의 새 디렉터리에 전달한다. 기존 결과를 덮어쓰지 않는다.
Python3.12/mpmath1.3.0/python backend와 이미 설치된 psutil/cryptography/pytest를 확인한다.
패키지가 없으면 시험을 시작하지 않고 필요한 환경 준비를 보고한다.

할당 시작 시각을 외부에 기록하고 기존 guardian.py를 독점 종료 lease로 실행한다.
scope STOP_CONTROL_ONLY, explicit_user_approval true, exact instance/machine/country,
approval_reference, guardian_sha256, completion_marker, deadline_seconds 최대300을 쓴다.
이 제한 오프라인 scope는 과거 실측A의60분 lease와 별개다. 과거 승인 파일을 재사용하지 않는다.
시작 후60초 안에 ARMED를 확인하지 못하면 시험 없이 정지한다. 종료 확인180초를 별도 확보한다.
ARMED 후60초 안에 guest gate를 시작해야 한다. 계산 제한120초 뒤 회수할 시간도 남긴다.
이 짧은 generic guardian lease는 최초 상태 조회·기한/완료/실패 정지 경로이며,
실측A의 지속 heartbeat 제어와 같은 것으로 주장하지 않는다. 장기 통신 장애 보장은 미검증이다.

같은 authorization 폴더에 외부 armed.json을 전달한다. 새 ticket:

- gate EVIDENCE_CANONICALIZATION_AND_LIGHTWEIGHT_VERIFICATION_V0
- scope EVIDENCE_OFFLINE_ONLY
- explicit_user_approval true와 사용자 승인 reference
- exact instance_id/machine_id/country, allocation_start_utc
- 이번 code_seal_sha256, protocol.json의 policy_sha256
- physics_calls0, gpu_calls0

게스트 CONTAINER_ID는 PID1 환경 및 외부 API와 일치해야 한다. SSH가 환경을 생략했다면
실제 값을 먼저 확인한 뒤 해당 값만 shell 환경에 전달한다. 임의 다른 인스턴스 ID는 금지다.

source 루트에서 `python -m experiments.evidence_canonicalization_v0.offline
--authorization /absolute/authorization.json --out /absolute/fresh_output`을 실행한다.
CPU1, 전체wall/누적CPU120초, 프로세스별주소공간512MiB, core dump0이다.
194개 회귀/새 시험을 수행한 뒤 기존 inspector의 단발 historical review 모드와 비용 benchmark를 실행한다.
새 검사관/상주 서비스를 만들지 않는다. calculator 진입점은 시험 플러그인에서 차단하며 mock만 허용한다.
검사관 공개키는 실제 원본 판독 전에 출력 파일에 기록된다. 개인키는 검사관 프로세스에만 있다.
파생 정정증명서는 PENDING 상태로 생성한다. 실제 관리자 승인·공식 성능 프로필 활성화는 수행하지 않는다.

모든 원본/거부/시험 로그/서명 영수증/파생 자료/비용50표본을 보존한다.
실패하면 추가 고비용 단계로 넘어가지 않는다. 회수 ZIP의 raw 해시와 모든 파일을 확인한 뒤
COMPLETED 또는 FAILED를 외부 marker에 기록한다. actual=exited/stopped와 외부 final.json을 확인한다.
기한을 늘리거나 자동 재시작하지 않는다. 세 번 같은 실패가 반복되면 중단·원인·후속 실험을 보고한다.
