# ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0 — 준비 상태

2026-10-08. 기준 b2c6c0fc, 별도 브랜치 `codex/adaptive-execution-real-learning-pilot-v0`.
**SOURCE_PREPARED / TEST_EXECUTION_PENDING / REAL_LEARNING_NOT_READY / NOT_PRODUCTION.**

아직 신규 시험, 실제 새 물리 계산, 실제 서명 승격, 실제 선택 개선, 새 종료 제어 실행을 수행하지 않았다.
로컬 계산 금지와 이번 단계 유료 실행 별도 승인 조건을 유지한다. 과거 V0/V1 통과 숫자는 이번 결과가 아니다.

## 설계와 봉인

프로토콜·예산·승격 기준·원본 보존 목록·ADR은 구현보다 먼저 커밋 `8a2f06c8`로 봉인했다.
결함 시험 첫 버전은 `39977564`. [설계](ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0_DESIGN.md),
[프로토콜](../../experiments/adaptive_execution_real_learning_pilot_v0/protocol.json),
[원격 관문](../../experiments/adaptive_execution_real_learning_pilot_v0/REMOTE_RUNBOOK.md).
원본 282개 raw 해시는 유지한다. 추가 실행 의존성은 별도 목록과 새 코드 봉인에 포함한다.

공식 A는 N14/T1000/p163 WALL_MIN 직렬/W6, 각 5회 교대. N14 GPU는 금지한다.
B는 N12/T1000/p163 CPU_MIN 직렬/GPU이며 A 통과와 명시적 B 승인 뒤에만 가능하다.
변동 상한 1.25, 기존 P2/시작 상태/반올림/계산 경로는 보존한다.
54분 compute + 3분 종료 확인 + 3분 전달·준비 여유, 시간당 $0.25/총 $0.25 상한 제안이다.
현재 승인된 신규 유료 비용은 **$0**다.

## 구현됨 — 아직 실행 시험 전

- 실제 V1 서비스 완료를 원본·전체 초기 상태·세션·프로세스 CPU 시간과 함께 CANDIDATE로 저장하는 연결부.
- 부족한 방법 정보를 UNKNOWN으로 기록하고, 이득·반복 횟수·측정/검증 비용·정확성 범위·자원에 따른 시험 제안.
- 별도 검사관 프로세스가 원본/배치/정밀도/비용/새 재계산을 확인하고 자신의 키로만 연구 영수증 서명.
- 관리자 승인 후 다음 요청에 적용하는 연구 프로필, 요청 시작 snapshot, 세션 변경 시 legacy, 서명 복귀.
- 원본 해시·목표·세션·서명·출처 검사와 별도 서명 count/head를 통한 ledger 끝 삭제 탐지.
- 실제 다음 요청 결과의 검사관 재확인, 목표별 학습 비용·손익분기·실현 이익 계산.
- 외부 guardian 180초 actual 상태 확인과 최대 3회 정지 요청, 미확인 경고·수동 확인 기록.

새 시험 38개를 작성했으며 V0 24 + Learning V1 53을 함께 원격에서 확인하도록 준비했다.
총 115개는 **예정 항목 수**이며 통과 숫자가 아니다. guardian 늦은 종료/통신 실패/다른 인스턴스,
세션 혼합/변조/정밀도/배치/지원 밖 GPU/누락 CPU/잘못된 승인/복귀 실패/끝 삭제/중간 교체 등을 다룬다.
새 경험 연결부의 mock 시험은 test_only를 명시하고 실제 영수증 승격이 거부되는지 확인한다.

## 구상 일치성과 한계

반장은 올바른 직렬 선택을 느렸다는 이유로 오류라 부르지 않는다. 새 방법의 정보 공백과 성능 지식의
검증 상태를 분리한다. CPU_MIN을 연구 프로필로 교육할 수 있지만 봉인된 V1 CPU_MIN 규칙은 수정하지 않는다.
공식 서비스에는 연결하지 않으며, 승인된 연구 wrapper가 기존 fixed 실행 인터페이스를 호출한다.

분리된 검사관의 개인키를 실행 담당에게 전달하는 API는 없다. 그러나 같은 OS 계정은 프로세스/공개키
기준을 바꿀 권한이 있다. OS 계정·ACL·외부 서명기관·원격 append-only witness·동시성 트랜잭션과
신뢰 가능한 환경/시계 증명은 실제 서비스 전 별도 보안 설계다.

기존 검사기의 자체 KDK/readout 재계산을 재사용하며 힘 원시식 `RwForce`는 공유한다.
**완전 독립 수식 검증·형식 인증은 아니다.** `INDEPENDENT_FORMULA_VERIFICATION_V0`는 후속 과제다.
일초 간격 RSS 감시는 샘플링 방식이며 kernel hard cap이 아니다. 실제 FAILED 종료·장기 통신 장애·
새 guardian 실서비스 동작·새 GPU 세션 CPU 비용·실현 순이익은 아직 미확인이다.

원격 자원 승인 전 관찰: 인스턴스 54645489, machine 32736, Utah US, RTX4060Ti,
actual=exited/intended=stopped, 표시 요금 약 $0.1888889/h. 새 승인·시작 시 다시 확인해야 한다.
청구 영수증이나 실제 청구액으로 해석하지 않는다.

LOCAL FULL 생략 / 관련 시험 원격 실행 승인 대기 / 이유: 새 연구 namespace·신규 시험·문서만 추가하며
동결 기존 코드/fixture를 변경하지 않았고 로컬 계산은 승인되지 않았다. 공식 기준선 갱신 없음.
실제 서비스 연결은 원격 회귀·결함 시험, 새 실제 계산/재계산, 종료 제어 확인, 연구 승인/복귀 실측과
비용 평가 뒤 별도 판단해야 한다. master 병합·push 없음.
