# ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0 — 오프라인 시험 결과

2026-10-08. `OFFLINE_CONTRACT_GATE_PASS / REAL_LEARNING_NOT_READY / NOT_PRODUCTION`.

새 서버에서 **122 passed, 실패·error·skip 0**을 확인했다. 실제 N14/N12 계산은 하지 않았다.
새 세션의 실제 성능 자료 승격, 다음 실제 계산의 개선, 학습 비용 회수는 아직 미확인이다.
`RwForce` 공유 문제와 OS 권한 격리는 해결되지 않았다. 이 결과는 완전 독립 수식 검증이나 형식 인증이 아니다.

## 설계·봉인과 승인 범위

기준 커밋은 `b2c6c0fc652173ee6eff8cad28ac97ea342d7123`, 작업 브랜치는
`codex/adaptive-execution-real-learning-pilot-v0`다. 프로토콜·예산·승격 기준·원본 282개 해시는
구현보다 먼저 `8a2f06c8`에서 봉인했고, 관련 시험을 `39977564`에서 먼저 추가했다.
[설계](ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0_DESIGN.md)와
[원래 프로토콜](../../experiments/adaptive_execution_real_learning_pilot_v0/protocol.json)은 보존한다.

이번에 사용자가 승인한 것은 인스턴스 **52763685 / machine 3448 / Norway**의 오프라인 시험이다.
표시 요금 `$0.2696296296296296/h`가 기존 상한을 넘으므로, 명시적 승인에 따라 이번 오프라인에만
`$0.28/h`, 총 `$0.10`, 할당 10분으로 제한했다. CPU 1개, runner wall·누적 CPU 각각 120초,
주소 공간 512MiB, 새 물리 계산·GPU 호출 0 조건을 유지했다.
[예외 승인 봉인](../../experiments/adaptive_execution_real_learning_pilot_v0/offline_budget_amendment_52763685.json)의
raw SHA256은 `daa8ec8f9b73deb3f5d212841372725aac522cc1154eb385766b7744d4a54173`이다.

실제 연구의 시간당 `$0.25` 상한은 바꾸지 않았다. 실제 단계 A/B는 이번 승인의 범위 밖이며,
이 서버의 현재 표시 요금은 원래 실제 연구 상한을 초과한다. 다른 사람이 사용하는 기존
인스턴스 54645489에는 접속·제어·정지하지 않았다. 로컬 수치 시험도 하지 않았다.

통과한 소스는 `d3ee98fd85808d385c91b628f4cd7dd9f5577323`이며
[코드 봉인](../../experiments/adaptive_execution_real_learning_pilot_v0/code_seal.json)의 raw SHA256은
`561578c779a6b0f3bfcaf2f2cadea62f0d27cdec09cd707a17d27b546cf50b67`이다.
이 봉인은 334개 파일을 고정하고, 전달 ZIP은 봉인 자체를 포함한 335개 파일이다.
봉인 안의 `NOT_EXECUTED` 및 이전 [준비 보고서](ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0.md)의
시험 대기 상태는 당시 기록이다. 이를 덮어쓰지 않고 본 결과를 별도로 추가했다.

## 작은 구현과 시험 결과

| 구분 | 구현됨 | 시험됨 | 독립 검증됨 | 아직 미확인 |
|---|---|---|---|---|
| 경험 수집·정보 공백 | 서비스 완료 기록 연결부, 세션별 UNKNOWN/CANDIDATE, 올바른 느린 선택 보존 | mock 완료·합성 기록·과거 증거로 확인 | 새 실제 비용 기록의 독립 검증은 미실행 | 실제 완료 기록의 장기 수집 |
| 학습 가치 | 예상 절감, 확인된 재사용, 측정·검증 비용, 정확성 범위·자원 판단, 정보 부족 시 보류 | 비용 회수 불가·정보 부족 등의 계약 시험 | 실제 경제성 검증 미실행 | 실현 이익이 전체 비용을 초과하는지 |
| 검사관·관리자 | 별도 검사관 프로세스가 자신의 키 보유, 원본 검증 후 제한된 영수증만 서명 | 변조·잘못된 승인·서명·세션 혼합·mock 자료 차단, 정적 권한 경계 검사 | 오프라인 별도 판독 경로를 확인; 실제 신규 비용 영수증은 미발급 | 실제 다중 프로세스 계산 연동, OS 권한 격리 |
| 다음 요청·복귀 | 승인 프로필, 시작 시 고정 snapshot, 세션 제한, 서명 복귀·실패 시 STOP | 합성 프로필로 다음 선택 변경·CPU_MIN/WALL_MIN 분리·중간 교체·복귀 실패 검출 | 실제 새 계산의 개선을 독립 확인하지 않음 | 실제 다음 요청 실행·전체 비용 비교 |
| 종료 제어 | 외부 ARMED, actual 상태 확인, 제한된 재시도·미확인 경고 | mock 결함 주입 및 실제 DEADLINE/COMPLETED 종료 | 외부 API에서 actual=exited 확인 | 장기 통신 장애, 실제 물리 FAILED 종료 |

| 시험 묶음 | 통과 | 실패 / error / skip |
|---|---:|---:|
| 기존 Verification V0 | 24 | 0 / 0 / 0 |
| 기존 Learning V1 | 53 | 0 / 0 / 0 |
| 이번 Real Learning Pilot V0 | 45 | 0 / 0 / 0 |
| 합계 | **122** | **0 / 0 / 0** |

첫 전달 ZIP은 기존 replay JSON 두 개가 의존성 목록에서 빠져 **94 passed / 28 failed**였다.
원인은 파일 누락이며 실제 계산의 정확성 불일치가 아니다. 실패 시 STOP 기록을 남겼다.
기존 N14/N12 replay 원본을 수정하지 않고 전달 의존성과 코드 봉인에 포함하여 두 번째 시험이 통과했다.
실패한 ZIP·로그·JUnit·상태를 성공 기록과 함께 보존한다.

두 번째 결과를 내려받기 전에 외부 기한이 도래해 서버가 정지했다. 사용자가 다시 켠 뒤에는
**시험 재실행 없이 결과 파일만 회수**했다. 회수한 4개 파일의 raw SHA256을 원격 목록과 대조했고
모두 일치했다. 로컬 XML 판독으로 24/53/45와 실패·error·skip 0을 다시 확인했다.

## 비용과 종료 확인

| 실행 | runner wall | runner 누적 CPU |
|---|---:|---:|
| 첫 실패 시험 | 5.165632194초 | 3.769172초 |
| 두 번째 통과 시험 | 4.666754680초 | 3.353710초 |
| 두 시험 합계 | **9.832386874초** | **7.122882초** |

두 번째 pytest 자체의 JUnit 시간은 4.381초다. 위 비용은 **시험 runner 측정값**이며 서버 준비·전송·
대기·외부 감시기·결과 회수 비용 전체가 아니다. 청구 영수증을 확보하지 않았으므로 실제 총 과금은
`UNVERIFIED_NO_BILLING_RECEIPT`다. 512MiB는 프로세스별 `RLIMIT_AS`이며, 전체 자식 프로세스 합산
최대 RSS를 측정·인증한 값이 아니다. 실제 계산을 통한 이익과 비용 회수는 주장하지 않는다.

외부 감시기는 `intended=stopped`만 보고 성공으로 판정하지 않았다.

- 첫 `DEADLINE` 종료: 정지 확인 절차 시작 후 27.516초에 `actual=exited`, `STOP_CONFIRMED`.
- 결과 회수 뒤 `COMPLETED` 종료: 같은 기준 20.797초에 `actual=exited`, `STOP_CONFIRMED`.
- 마지막 외부 조회 `2026-10-08T08:12:20.5633369Z`: `actual=exited / intended=stopped`.

첫 기한을 준비·수정·회수까지 충분히 반영하지 못해 불필요한 수동 재시작을 요구한 점을 기록한다.
회수·무결성 확인을 완료한 다음 정지했고, 이후 추가 재시작은 하지 않는다. 앞으로도 안전 기한은 필요하나
작업·회수·종료 확인 전체 예산을 먼저 잡아야 한다. 장기 통신 장애나 실제 물리 FAILED 종료는
이번 실제 확인과 구별하여 계속 미확인으로 둔다.

## 구상 일치성 및 다음 관문

반장의 올바른 선택을 느리다는 이유로 오류로 바꾸지 않고, 모르는 방법의 정보를 별도로 기록한다.
검증되지 않은 경험은 공식 선택에서 차단하고, CPU_MIN과 WALL_MIN은 목표·세션별로 분리한다.
합성 승인 프로필로 다음 요청의 선택 변화와 복귀는 확인했으나, 실제 더 빠른 계산을 확인한 것은 아니다.
성능 경험 승격은 GPU 지원 범위를 넓히지 않는다. N14 GPU 금지, 물리식·구간 산술·반올림·P2·원래 상태
재시작·GPU V1 경로를 보존한다.

규칙 관리자, 실행 담당, 독립 검사관의 논리·서명 권한을 분리했다. 실제 검사관은 자신의 키를 보유하고
임의 본문 서명 API를 제공하지 않는다. 같은 UID와 저장소 쓰기 권한은 관리자·원본·신뢰 루트의 악의적
교체를 막는 OS 격리가 아니다. 별도 계정/보호 저장소/외부 신뢰 루트·승인 전달은 후속 보안 설계 대상이다.
공유 `RwForce`의 독립 수식 검증은 `INDEPENDENT_FORMULA_VERIFICATION_V0` 후속으로 남긴다.

실제 서비스 연결 전에 별도 승인된 새 세션에서 A의 실제 비용·새 replay·검사관 영수증·관리자 승인·
다음 실제 선택·복귀를 확인해야 한다. B는 A 통과와 별도 B 승인, 현재 GPU 빌드/드라이버/지원 범위 확인이
필요하다. 실제 전체 학습 비용과 실현 절감도 비교해야 한다. 아직 이번 코드의 실제 다중 프로세스
계산 경로, 경쟁 요청의 활성 프로필 변경, production 운영을 검증하지 않았다.

`LOCAL FULL 생략 / 관련 원격 시험 122개로 대체 / 이유`: 새 연구 namespace·시험·문서·증거만 추가했고
원본 보호 대상 및 기존 물리·공용 실행 로직은 변경하지 않았다. 공식 LOCAL FULL 기준선은 갱신하지 않는다.
새 브랜치에서 로컬 커밋하며 master 병합과 GitHub push는 하지 않는다.

## 보존 증거

- [집계](adaptive_execution_real_learning_pilot_v0/offline_20261008/summary.json), [29개 파일 raw 해시 목록](adaptive_execution_real_learning_pilot_v0/offline_20261008/closeout.json)
- [통과 JUnit](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/output_attempt2/junit.xml), [통과 로그](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/output_attempt2/tests.log)
- [첫 실패 로그](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/output_attempt1/tests.log), [첫 실패 상태](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/output_attempt1/status.json)
- [DEADLINE 종료](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/guardian/final.json), [COMPLETED 종료](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/recovery/guardian/final.json), [최종 인스턴스 상태](adaptive_execution_real_learning_pilot_v0/offline_20261008/run/final_instance_status.json)
- [실패 전달 ZIP](adaptive_execution_real_learning_pilot_v0/offline_20261008/source_4bfa43ec.zip), [통과 전달 ZIP](adaptive_execution_real_learning_pilot_v0/offline_20261008/source_d3ee98fd.zip)
