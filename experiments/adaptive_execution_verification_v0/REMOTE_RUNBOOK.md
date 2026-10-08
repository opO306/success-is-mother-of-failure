# 원격 검증 실행 준비 — 아직 승인·실행되지 않음

프로토콜 local commit: `f135cd92`. initial source set: 44개, 서비스 원본 35개.
준비된 ZIP은 실제 바이트를 보존한다. 새 코드/봉인/원본/시험만 담고 물리 실행 모듈·CUDA·
V1 campaign·Vast credentials는 담지 않는다. 원본 파일은 `.gz` 그대로 전달한다.

실행 조건은 설계자가 지정한 원격 Linux 서버, Python 3.10 이상, pytest가 있는 환경이다.
GPU는 쓰지 않는다. 사용자 서버 활성화와 인스턴스 ID·명시적 실행 승인을 받은 뒤에만
authorization.json을 작성한다. Linux나 CONTAINER_ID만으로 승인이라 간주하지 않는다.

```json
{
  "gate": "ADAPTIVE_EXECUTION_VERIFICATION_V0",
  "scope": "OFFLINE_ONLY",
  "explicit_user_approval": false,
  "approval_reference": "REPLACE_ONLY_AFTER_EXPLICIT_USER_APPROVAL",
  "instance_id": "USER_SPECIFIED_INSTANCE_ID",
  "code_seal_sha256": "RAW_SHA256_OF_CODE_SEAL_JSON",
  "new_trajectories": 0,
  "gpu_calls": 0
}
```

봉인된 원격 root에서 다음 명령을 실행한다. output은 신규 경로여야 한다.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m experiments.adaptive_execution_verification_v0.offline \
  --authorization /approved/authorization.json \
  --code-seal-sha256 APPROVED_CODE_SEAL_SHA256 \
  --out /approved/new-output
```

작업자 1개, 시험 subprocess wall 90초 + 원본 재판독 25초, CPU 전체 상한 120초,
주소공간 512MiB를 제한한다. 기존 V1 시험 전체에는 실제 계산이 있어 실행하지 않는다.
새 시험의 V1 관련 검사는 pinned 원본 selector의 AST CPU_MIN 규칙과 과거 전체 결과
대조로 제한한다. 이것은 V1 전체 회귀 시험을 대체했다는 뜻이 아니다.

output은 tests.log, 후보, 정보 공백, 검증 영수증, 오프라인 manager handoff,
UNKNOWN/CANDIDATE/VERIFIED 원장, 프로필, 추천, 활성/복귀 원장, 상태 파일이다.
실패·시간 초과는 STOP하고 원본 출력은 보존한다. 수정 없이 재실행·다음 단계 자동 시작 없음.

Vast 종료 source 경로에서 global ps 부하 스캔을 제거했지만 실제 API adapter와
외부 guardian은 미구현이다. **실제 자동 종료가 검증되기 전에는 유료 계산을 시작하지 않는다.**
서버가 제공되더라도 먼저 종료 제어 점검 범위와 종료 담당을 승인받고, stopped/exited 확인
증거를 남겨야 한다. 새 shutdown mock의 통과를 실제 종료 성공으로 보고하지 않는다.
Vast의 요청 상태와 actual 상태가 다를 수 있다는 점은
[공식 CLI 안내](https://github.com/vast-ai/vast-cli/blob/master/vastai/SKILL.md)를 참고한다.
