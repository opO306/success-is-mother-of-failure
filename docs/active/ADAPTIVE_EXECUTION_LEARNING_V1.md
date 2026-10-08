# ADAPTIVE_EXECUTION_LEARNING_V1 — 설계·제한 구현 상태

## 현재 결과 — 2026-10-08 원격 제한 검증 완료

**OFFLINE_TEST_VALIDATED_ONLY / TEST_ONLY / NOT_PRODUCTION.**
실제 새 세션의 물리 비용 측정·서비스 연결·운영 키/OS 격리는 하지 않았다.
이번 새 경험은 합성 비용과 과거 결과 payload를 가진 새 입력이며 실제 성능 증거가 아니다.
RwForce 공유 미해결과 `INDEPENDENT_FORMULA_VERIFICATION_V0` 후속 범위를 유지한다.

설계자 별도 승인으로 기존 인스턴스 54645489에서 CPU 0에 단일 worker를 고정해 실행했다.
**77 passed / failures 0 / errors 0 / skips 0, console 4.27초**.
기존 V0 24개 + 신규 V1 53개, 첫 시험 시도에서 통과했다. JUnit 시험 본체 시간은 4.238초다.
시험과 demo를 포함한 제한 runner wall 4.789초, 누적 CPU 4.053초.
Python 3.12.3 / pytest 9.1.1 / cryptography 49.0.0, 자동 설치 없음.
로컬 수치 계산/시험 0, 새 물리 궤적 0, GPU 호출 0, production 활성화 0.

[원격 closeout](adaptive_execution_learning_v1/closeout_20261008.json) ·
[시험 원문](adaptive_execution_learning_v1/run_20261008/output_attempt1/tests.log) ·
[학습/복귀 권고](adaptive_execution_learning_v1/run_20261008/output_attempt1/demo/recommendations.json) ·
[합성 경험 검사관 영수증](adaptive_execution_learning_v1/run_20261008/output_attempt1/demo/inspector_receipt.json).

### 구분한 세 가지 시험

| 구분 | 관찰한 결과 |
|---|---|
| 과거 경험 재현 | V0 24개 회귀, 기존 35개 서비스·7개 비용 묶음 유지; 보호 100개 파일 raw hash 불변 |
| 새 경험 후보 생성 | 새 합성 세션 입력 15개 생성·UNKNOWN/CANDIDATE 보존; 원장 갱신만으로 활성화 없음 |
| 검증 후 학습 | 독립 원본 판독·검사관 서명 → VERIFIED TEST_ONLY 프로필 1개 → 별도 WALL/CPU 승인 → 다음 요청 권고 변경 |

demo의 최초 비용 공백은 3방법 모두 UNKNOWN이었다. 검사/승격 뒤 같은 합성 세션에서
3방법 비용은 알려진 상태가 됐지만 재사용·실현 이득·독립 힘 수식은 계속 UNKNOWN이다.
시작된 요청은 LEGACY snapshot을 유지했고, 새 요청 WALL_MIN/CPU_MIN은 GPU_HYBRID를
권고했다. 복귀 뒤 새 WALL 요청은 LEGACY, 다른 세션도 LEGACY를 사용했다.
별도 합성 비용 panel에서는 WALL은 GPU, CPU_MIN은 직렬을 선택해 두 목표를 구별했다.
이 숫자에서 선택이 개선됐다는 의미이며 실제 GPU 실행이나 실제 시간 절감은 아니다.

악성 서명·공개키 교체·잘못된 승인·승인 재사용·후보/원본/프로필/snapshot 변조·
다른 환경/세션 혼합·중복/반복 부족·CPU/wall 미계상·정밀도/영역/결과 불일치·
복귀 실패·동시 manager 요청 거부 시험이 통과했다. N14는 CPU 방법만 학습하며
GPU 후보 자격을 얻지 않는다. 재시도 비용과 ORIGINAL_STATE 조건도 확인했다.
결함 주입 원본과 거부 원장까지 1,318개 파일을 byte 검증해 ZIP에 보존했다.
[결함 원본 포함 증거 ZIP](adaptive_execution_learning_v1/run_20261008/evidence_attempt1.zip).
시험 임시 경로 이름이 잘려 최초 export 경로 확인이 1회 실패한 기록도 보존했다.
시험/증거 내용은 바꾸지 않았고 실제 경로를 확인한 뒤 회수했다.

### 독립 검증의 정확한 범위

새 검사관의 별도 원본 판독·서명 확인·관리자 승인 경계를 실행으로 확인했다.
합성 경험 15개에 `VERIFIED / errors=[] / SYNTHETIC_TEST_ONLY` 영수증이 나왔다.
이는 독립 판독 코드의 제한 검증이며 별도 사람의 독립 감사나 OS 권한 격리 증거가 아니다.
동일 계정의 구현자/root에 대한 위조 불가능성, 실제 비용의 참값, 수식 독립성,
계산 정확성의 새 인증은 주장하지 않는다. 운영 승격은 여전히 차단한다.

### 설계자의 12가지 완료 질문

| 질문 | 현재 판정 |
|---|---|
| 1. 새 경험 수집 | 구현됨·시험됨. 입력 ingest 가능, 계산기 종료 훅 자동 연결은 미구현 |
| 2. 모르는 부분 구별 | 시험됨. exact scope/session 비용 공백과 GPU unsupported 분리; 느림을 오류로 처리하지 않음 |
| 3. 학습 가치 평가 | 시험됨. 비용/재사용/위험/자원 부족은 보류, 제안은 실행 권한을 주지 않음 |
| 4. 미검증 사용 차단 | 시험됨. 고정 공개키의 검사 서명·별도 관리자 승인 필요; production 사용은 전면 차단 |
| 5. 검증 뒤 다음 선택 개선 | 합성 비용 조건에서 시험됨. 실제 새로운 계산의 성능 향상은 미확인 |
| 6. CPU_MIN/WALL_MIN 교육 | 시험됨. 목표별 승인과 순위 분리, GPU CPU 감소를 세션 밖으로 일반화하지 않음 |
| 7. 환경/세션 재사용 방지 | 시험됨. 다른 환경/세션/초기 상태/정밀도/크기는 LEGACY fallback |
| 8. 잘못된 경험 거부·보존 | 시험됨. 원본·거부·서명·STOP 기록을 ZIP에 보존 |
| 9. 이전 프로필 복귀 | 시험됨. 이전 VERIFIED/LEGACY 승인 복귀, 실패 시 기존 버전 보존·새 요청 STOP |
| 10. 정확성 변경 여부 | 보호 100개 파일 hash 불변, V0 회귀 통과. 물리/GPU/P2/반올림/기준선 변경 없음 |
| 11. 비용보다 실제 이득이 큰가 | 아직 미확인. 실제 측정·검증·학습 비용과 실제 재사용 이득의 결산 필요 |
| 12. 서비스 연결 전 필요 | 실제 종료 훅, 세션/정확성 증명 어댑터, 운영 서명·OS 격리·외부 원장 증인, 종료 확인 지연 보강, 별도 승인 실측/결산 |

### 종료 제어와 예산의 별도 결과

기존 수정 guardian hash와 외부 `ARMED`를 실행 전에 확인했다.
현재 hourly API 값은 $0.18888888888888888로 승인 cap $0.25보다 낮았다.
총 결제 금액은 영수증이 없어 미확인이다. 결제 확정 비용이나 실제 계산 이득을 추정해 단정하지 않는다.

**이번 guardian 원본 결과는 `STOP_UNCONFIRMED`다.** COMPLETED 뒤 stop 요청을 3회
보냈지만 자체 6회 확인 구간에서는 actual=running/intended=stopped였다.
별도 API 재조회에서 `actual=exited / intended=stopped`를 확인했다(06:33:49 UTC).
감시기 영수증을 성공으로 다시 쓰지 않았다. 이번 종료 확인 지연은 별도 운영 제한이다.
다음 유료 실행 전, 제한 시간 안의 stop 수렴을 확인하는 추가 관찰/경고 경로를 보강해야 한다.
장기 통신 장애·실제 FAILED 종료·제어 호스트 장애는 여전히 미검증이다.
[감시기 원본](adaptive_execution_learning_v1/run_20261008/guardian_receipt.json) ·
[별도 최종 상태](adaptive_execution_learning_v1/run_20261008/independent_final_status.json).

LOCAL FULL 생략 / 관련 원격 시험77개로 대체 / 새 오프라인 namespace·시험·문서만 추가,
기존 실행 코드·공용 수치·동결 계약·fixture 변경 없음. 공식 기준선 불변.
로컬 커밋으로 보존, GitHub push/master merge 없음. 이후 실제 계산 단계 자동 시작 없음.

## 아래는 실행 전 준비 상태의 원문 — 현재 결과와 구별

2026-10-08 / SOURCE_PREPARED / TEST_EXECUTION_PENDING / NOT_PRODUCTION.

**아직 시험을 실행하지 않았다.** 로컬 계산·시험 금지를 유지했고,
유료 Vast 실행·새 물리 계산·GPU 호출·실제 서비스 활성화는 0이다.
아래는 구현과 정적 확인 결과이며 통과한 동적 시험 결과가 아니다.
기존 V0의 24 passed는 과거 완료 결과로 보존하며 V1 시험 수에 합산하지 않는다.

## 설계와 봉인

기준 HEAD `0f4450e889f33f437c1cafaf68966a3590c64bc3` 및 깨끗한 작업 상태를 확인했다.
브랜치 `codex/adaptive-execution-learning-v1`에서만 작업했다.

| 단계 | 로컬 commit | 내용 |
|---|---|---|
| 프로토콜 선봉인 | `8a3f6627` | 기준·예산·승격 기준·권한·설계·보호 파일 100개 raw hash |
| 시험 먼저 작성 | `d222055c` | 합성 새 세션·학습/복귀·결함 주입 계약 |
| 제한 구현 | `9e7842bf` | 수집·독립 판독·서명·목표별 승인·snapshot·STOP |
| 실행 소스 봉인 | `0d59cdd0` | 준비 코드/시험 raw SHA-256 pin |
| 정적 검토 보강·재봉인 | `48848fd0` | 활성 후 원본 재확인·승격된 지식만 공백 해소·추가 결함 시험 |

[설계](ADAPTIVE_EXECUTION_LEARNING_V1_DESIGN.md)와
[프로토콜](../../experiments/adaptive_execution_learning_v1/protocol.json)은 구현 전 봉인했다.
최신 실행 코드 seal SHA-256:
`11a0a713ebf2e704da59a1cbc032b102b953f13afdcbe58a3ac75b8910c23560`

최초 코드 pin `4a178ea46d2b2a3b478f3041f1e34db49dab97df23007e533265b5b53857196f`과
그 ZIP은 실행되지 않은 준비 이력으로 보존한다. 코드 seal에는 predecessor pin을 기록했다.

## 구현됨

새 기록은 UNKNOWN → CANDIDATE로 append한다. 반복 요청의 원장을 계속 추가할 수 있다.
요청/초기 상태/환경/세션/방법/이유/wall/모든 시도의 CPU/결과/정밀도/영역/증거를 저장한다.
실제 기록도 후보로 보존하되 실제 승격에는 미구현 외부 증명 어댑터가 필요하다.

독립 판독 검사관은 수집기/관리자/선택기를 import하지 않고 원본을 다시 읽는다.
다른 세션/환경 혼합·결과/초기상태/정밀도 불일치·미계상 시도·변조·반복 부족·
시간 불안정·GPU 지원 밖을 거부한다. 검사 서명과 활성화 승인 서명은 별도 키다.
관리자는 ingest 전 provision된 공개키로 검사하고 caller가 만든 신뢰 해시를 받지 않는다.

활성화는 목표별로 별도 승인한다. 읽는 요청은 시작 시 고정한 immutable bytes만 사용한다.
복귀도 승인하며, 복귀 실패/증거 무결성 실패는 STOP을 남겨 새 요청을 막는다.
구현의 선택 출력은 OFFLINE_TEST_ONLY 권고다. 실제 V1/GPU 계산기와 연결하지 않았다.

학습 가치는 목표별 이득·확인된 재사용·측정/검증/학습 비용·위험·자원 상한으로 평가한다.
모르는 값은 보류한다. 순이득이 양수여도 시험 제안만 하며 실행 권한은 없다.

서명은 cryptography의 maintained Ed25519 API를 사용한다.
[공식 서명/검증 문서](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/).
의존성이 없으면 실행은 거부하고 자동 설치하지 않는다.

## 시험됨 / 독립 검증됨

- 정적 파일 확인: 보호 100개 파일 raw hash 일치, protocol seal 일치.
- 변경 목록: 새 namespace/시험/문서와 신규 LF Git attributes에 한정.
- `git diff --check`: 통과.
- 신규 pytest·과거 V0 회귀·합성 demo: **미실행**.
- 신규 경험 독립 판독·서명 검증: **구현됨, 아직 실행 결과 없음**.
- 별도 사람/별도 OS 계정 감사: 미실시.
- LOCAL FULL 생략 / 관련 원격 시험 대기 / 새 오프라인 namespace만 추가,
  기존 실행/공용 수치/fixture/동결 계약 변경 없음. 공식 기준선은 갱신하지 않는다.

## 구상 일치성 2차 점검

| 설계자가 물은 것 | 현재 판정 |
|---|---|
| 1. 새로운 경험 수집 | 구현됨; 종료 훅 자동 연결은 미구현; 새 합성 입력 시험 대기 |
| 2. 모르는 부분 구별 | exact scope/session별 공백과 unsupported 분리 구현; 시험 대기 |
| 3. 가치·비용·위험 평가 | 비용/재사용/위험/자원 필수값과 보류 구현; 실제 사실값 미확인 |
| 4. 미검증 공식 사용 차단 | 서명/관리자 승인 및 production 전면 차단 구현; 악성 입력 시험 대기 |
| 5. 다음 선택 개선 | 합성 비용에 따른 다음 요청 선택 변경 구현; 실제 속도 개선 미확인 |
| 6. CPU_MIN/WALL_MIN 교육 | 목표별 승인/순위와 GPU CPU 비용 비교 구현; 합성 시험 대기 |
| 7. 환경/세션 성능 재사용 방지 | 전체 exact key 검사와 fallback 구현; 시험 대기 |
| 8. 잘못된 경험 거부·보존 | 거부/원본/서명/STOP 원장 구현; 결함 주입 시험 대기 |
| 9. 이전 프로필 복귀 | 이전 활성 VERIFIED/LEGACY 승인 복귀 구현; 실패 시 STOP; 시험 대기 |
| 10. 계산 정확성 유지 | 기존 V0/V1/GPU/물리 등 raw hash 보존 확인; 새로운 물리 실행 없음 |
| 11. 비용보다 이득이 큰가 | 아직 미확인. 합성 숫자/예상 순이득은 실제 이득의 증거가 아님 |
| 12. 서비스 연결 전 필요 | 실제 종료 훅·증명 어댑터·운영 키/OS 격리·새 측정/비용 결산·운영 승인 |

## 아직 미확인과 후속

합성 입력은 과거 결과 payload와 초기 상태의 **과거 해시 참조**를 복사한다.
전체 초기 상태 복원이나 새 계산 결과 생성 시험이 아니다. 비용은 의도적으로 만든 값이다.
실제 원본 상태 payload를 받는 기록 필드는 있지만 실제 종료 훅에서의 전달은 미확인이다.

시험 fixture/demo의 임시 서명은 TEST_ONLY 관리·검사 역할 모의다.
구현자가 운영 검사관 승인을 발급하는 경로는 없으며 운영 승격은 거부한다.
같은 OS 계정의 구현자가 코드/키/root를 바꾸지 못한다고 주장하지 않는다.
실서비스 전 별도 계정/ACL·외부 서명기·사용자 승인기·append-only 외부 원장 증인이 필요하다.
원장 tail 삭제/분기와 호스트 전체 손상은 현재 해시 체인만으로 보장하지 못한다.
단일 작성자 오프라인 프로토타입이며 운영 동시성·작업 중 취소 통신은 별도 과제다.

RwForce 공유는 미해결이다. 성능 VERIFIED와 계산 정확성 VERIFIED는 구분한다.
완전 독립 수식 검증·형식 인증을 주장하지 않는다.
`INDEPENDENT_FORMULA_VERIFICATION_V0`는 이번 범위 밖 후속으로 남긴다.

Vast 종료 경로는 기존 수정된 external guardian과 DEADLINE/COMPLETED exited 증거를 보존했다.
장기 통신 장애와 실제 FAILED 종료는 여전히 미검증이다.
실행 전 신규 전용 승인·현재 API 가격/정확한 인스턴스·guardian hash·ARMED를 확인해야 한다.

원격 승인 제안: 1 worker, wall/누적 CPU 각각 120초, 512 MiB,
최대 3시도(실패마다 보존), GPU/새 궤적 0. 총 $0.10 / 시간당 $0.25 / 할당 10분 이내.
새로운 실제 물리 측정이 필요해지면 별도 환경·비용·얻을 정보로 다시 승인받는다.
GitHub push/master 병합 없음.
