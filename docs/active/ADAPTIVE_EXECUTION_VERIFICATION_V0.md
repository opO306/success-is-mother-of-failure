# ADAPTIVE_EXECUTION_VERIFICATION_V0 — 제한 구현 준비 상태

2026-10-08. **IMPLEMENTED_SOURCE / NOT_EXECUTED / NOT_VALIDATED / NOT_PRODUCTION.**
시험·오프라인 재현을 아직 실행하지 않았다. 검증된 새 경험 0개, 새 프로필 활성화 0개다.
Vast 시작·유료 계산·로컬 시험·궤적·GPU 실행 0회다. 물리 수식 독립성은 미해결이다.

## 설계

[설계 결정](ADAPTIVE_EXECUTION_VERIFICATION_V0_DESIGN.md),
[프로토콜](../../experiments/adaptive_execution_verification_v0/protocol.json).
반장이 모르는 비용 정보를 기록하고, 원본에서 후보를 수집한 뒤 별도 검사기를 통과한
경험만 다음 요청의 프로필에 사용할 수 있게 준비했다. 느렸다는 사실만으로 기존 판단을
수치 오류로 판정하지 않는다. 현재 실행 서비스에는 연결하지 않았다.

초기 범위는 R1·R7의 35개 서비스 기록이다. 검증 경험은 exact request/N/T/p와 원본
Vast 세션에만 묶는다. 같은 env_id의 다른 서버는 새 교정 없이 이 비용 경험을 쓰지 않는다.
CPU_MIN의 새 GPU CPU 비용 추천도 별도 프로필 안에서만 가능하고 V1 always-serial은 유지된다.

## 봉인

구현 전 local commit **f135cd92**로 프로토콜·예산·승격 기준·설계·44개 source manifest를 봉인했다.
프로토콜 raw SHA-256: `de5e76c6b7b6f9beda4810f819f5b260cf44e3f36b087d6a9e5b0be9c1dd21b9`.
원본 manifest raw SHA-256: `c1583e8b2c55d88e3d105e1bea36a6a82efdf1ff7f8d8ad6f439a5b72581528d`.
원본 바이트를 기준으로 하므로 원격 전달은 줄바꿈을 바꾸지 않는 ZIP snapshot으로 한다.
일반 Git checkout의 CRLF/LF 변환을 원본 동일성으로 간주하지 않는다.

현재 계산 승인 예산은 **0**이다. 원격 소규모 검증 제안은 작업자 1개, wall/CPU 각각 최대
120초, 메모리 512MiB, 신규 궤적/GPU 호출 0이다. 승인 후에도 봉인 범위를 넘으면 STOP한다.
유료 서버 제안 상한은 $0.25/h·합계 $0.10·할당 10분이며, 이것은 지출 승인이 아니다.

## 구현

| 코드 | 하는 일 | 권한·한계 |
|---|---|---|
| collector.py | 원본을 해시 확인하고 후보·정보 공백 구성 | 승격·실행 권한 없음 |
| journal.py | UNKNOWN→CANDIDATE→VERIFIED 이력·거부 영수증 보존 | 상태 건너뛰기 거부, append-only 원장 |
| exploration.py | 이득 하한·재사용·측정/검증 비용·위험으로 시험 제안 | 정보 부족은 DEFER, 제안은 실행하지 않음 |
| verifier.py | 원본부터 별도 판독, 결과·정밀도·배치·비용·반복·후보 재도출 대조 | stdlib만 import, 물리 재계산·활성화 없음 |
| manager.py | 별도 receipt/source/protocol pins 확인, 프로필 버전·활성/복귀 원장 | 요청 시작 snapshot, 단일 작성자 파일 프로토타입 |
| selector.py | VERIFIED snapshot에서 WALL_MIN/CPU_MIN 오프라인 추천 | exact scope와 실행기 자격이 없으면 V1 fallback |
| shutdown.py | 독점 lease의 정확한 instance ID에 stop, actual stopped/exited 확인 | injected transport만, 실제 API·guardian 미구현 |
| offline.py | 승인된 원격 Linux 인스턴스에서 새 시험·기존 증거 판독 | launch API 없음, 일괄 리소스 제한, exclusive 출력 |

삼권분립은 파일·모듈·명시적 해시 handoff까지 구현했다. OS 계정/ACL/서명 격리는 미구현이다.
오프라인 시험 하네스의 자동 handoff는 production 승인이나 별도 감사자의 서명이 아니다.
실제 서비스 연결·새 세션 재교정·새 계산 경험 ingest·온라인 실행·전력 최적화는 미구현이다.

## 소규모 검증 결과

**시험 미실행 / 원본 오프라인 재현 미실행 / V0 VERIFIED 0개.**
새 시험 파일은 변조·승격 거부·세션 거부·CPU_MIN 추천·N14 추천·snapshot·복귀·종료 mock·
검사기 import 경계를 다룬다. 통과 개수와 속도는 실행 후 원본 로그로만 추가한다.
static Git 변경 범위·공백 검사와 봉인 해시 확인은 파일 준비 검사이며 실행 검증이 아니다.
확인 결과: 프로토콜/설계/manifest 봉인 일치, 원본 44개 해시 일치(합계 2,086,350 bytes),
`git diff --cached --check` 오류 0. 변경은 신규 V0 패키지·시험·문서와 상태/지도/색인 추가뿐이다.
V1·GPU·물리·반올림·P2·기존 fixture/실행 코드는 변경 목록에 없다.

LOCAL FULL 생략 / 관련 시험 대체도 아직 미실행 / 이유: 새 연구 패키지·시험·문서만 추가,
기존 실행 코드·fixture·동결 계약은 보존하며 사용자 로컬 실행 금지에 따라 원격 승인 대기.
공식 기준선은 갱신하지 않는다. 이 단계의 검증 완료나 Gate 종료로 보고하지 않는다.

## Vast 종료와 독립 수식 검증

과거 `ps`가 자기 자신을 busy로 잡는 경로는 새 종료 제어에서 제거했다. 기존 V1 job.sh·
원본 로그는 보존했다. 새 경로는 유효한 독점 lease 없이는 stop을 요청하지 않고, timeout도
actual 상태를 확인한다. 최대 3회 stop·6회 조회 후 실패를 남긴다. 실제 API adapter 및 외부
guardian은 미구현, mock 시험도 미실행이다. **자동 종료 해결 완료 아님 / 유료 계산 차단.**

`INDEPENDENT_FORMULA_VERIFICATION_V0`는 별도 미착수 과제다. 기존 RwForce 공유를 유지한다.
비용 경험 검증을 완전 독립 물리 검증, `REPLAY_VERIFIED`, `CERTIFIED`로 승격하지 않는다.

## 구상 일치성의 별도 확인

자료 없음→보류, 후보→공식 선택 차단, 정확한 기존 선택→보존, 검증→다음 요청에만,
복귀→이전 영수증 보존이라는 사용자 요구를 코드 경로와 대조했다. 이는 작성자의 정적
검토이며, 실제 시험 결과나 독립 감사와 구별한다. 현재의 중요한 미완성 부분은 실제
시험, 실서비스 연결, 운영 권한 격리, 실제 Vast 종료와 guardian, 독립 힘 수식 검증이다.
