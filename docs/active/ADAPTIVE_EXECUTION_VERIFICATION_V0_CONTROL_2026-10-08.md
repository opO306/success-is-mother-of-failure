# V0 실제 종료 제어 점검 — 2026-10-08

## 수정 후 원격 검증 종료까지 실제 확인

설계자가 같은 서버를 다시 켠 뒤 접속 주소·CONTAINER_ID·API ID가 같음을 확인했다.
원격 계산 전에 수정된 외부 감시기를 등록했다. 승인된 오프라인 시험 및 원본 판독만
실행하고 증거를 회수했다. 완료 신호에 따른 **COMPLETED 실제 종료**도 확인했다.

| 실제 관측 | UTC | 한국 시각 |
|---|---|---|
| ARMED, actual=running | 05:50:04.750 | 14:50:04.750 |
| STOP_REQUEST, CLI exit 0 | 05:51:26.125 | 14:51:26.125 |
| actual=running, intended=stopped | 05:51:30.587 | 14:51:30.587 |
| actual=exited, intended=stopped | 05:51:34.986 | 14:51:34.986 |

수정 source raw SHA-256 `10ddb2fe46ecb3e40cfbc4827be5f6dadae3034255c2e3c956c74ac7f1043030`.
[실행 source](adaptive_execution_verification_v0/run_20261008/guardian_v2_executed.ps1),
[영수증](adaptive_execution_verification_v0/run_20261008/guardian_receipt.json),
[별도 최종 API 조회](adaptive_execution_verification_v0/run_20261008/independent_final_status.json)를 보존했다.
수정 경로에 STOP_REQUEST_ERROR/STATE_READ_ERROR 없음. 초기 오류 영수증은 그대로 남긴다.
DEADLINE과 COMPLETED의 실제 종료 확인이며, 장기 API 장애·관리 호스트 종료·FAILED 실제
분기의 검증을 대체하지 않는다. 실제 청구액 영수증은 확보하지 않았으므로 비용을 확정하지 않는다.
API 당시 시간당 요금과 각 관측 시각을 증거로 남긴다. 새 서버 생성·자동 restart·destroy는 없다.

## 최초 점검 원문 — 아래 미실행/미재실행 표기는 최초 점검 당시 상태

**LIVE DEADLINE STOP CONFIRMED / CLI 응답 처리 오류 1건 보존 / 오프라인 검증은 미실행.**

설계자가 전달한 `ssh -p 34259 root@ssh7.vast.ai`에 Vast 전용 SSH 키를 지정해 접속했다.
원격 CONTAINER_ID와 사용자 계정 API에서 같은 인스턴스 **54645489**를 확인했다.
API 당시 요금 $0.1888888889/h, 봉인 $0.25/h 상한 이내다. 새 서버 생성·시작은 하지 않았다.
첫 접속은 기본 키로 publickey 거부, 키를 명시한 두 번째 접속은 성공했다.

이번 승인 범위는 원격 접속·지정 인스턴스 종료 제어 점검이다. 수치 시험·궤적·GPU 호출·
오프라인 원본 재현은 0회다. 로컬에서는 파일/Git/SSH 및 Vast 관리 API 제어만 수행했고
로컬 수치 계산·시험은 수행하지 않았다. 계정 키·컨테이너 키는 기록에 포함하지 않았다.

## 실제 동작과 증거

게스트 밖에서 별도 hidden PowerShell 관리 프로세스를 실행했다. 관리자는 인스턴스 ID·
독점 lease·사용자 제공 접속 정보의 승인 근거·source hash를 확인한 뒤 15초 기한을 걸었다。
이 경로는 ps, 프로세스 CPU%, 다른 사용자 작업 목록을 사용하지 않는다. 서버 시작/생성/삭제
명령이 없으며, stop 최대 3회·실제 상태 조회 최대 6회로 제한했다.

| 실제 관측 | UTC | 한국 시각 |
|---|---|---|
| ARMED, actual=running | 05:46:01.910 | 14:46:01.910 |
| actual=running, intended=stopped | 05:46:23.892 | 14:46:23.892 |
| actual=exited, intended=stopped | 05:46:28.389 | 14:46:28.389 |

[종료 영수증](adaptive_execution_verification_v0/control_20261008/control_receipt.json)과
[별도 API 조회](adaptive_execution_verification_v0/control_20261008/independent_status.json)를 보존했다.
실행 당시 source는 [guardian_v1_executed.ps1](adaptive_execution_verification_v0/control_20261008/guardian_v1_executed.ps1),
raw SHA-256 `e53b46ea989aee29e4965d24690c13156e392e7af8de0b266384de5927ce21e8`다.

첫 stop 호출의 CLI stdout을 JSON으로 읽다 ArgumentException을 기록했다. 요청이 전달됐다는
사실은 뒤의 actual 상태로 확인했으며, 호출 응답만으로 성공 판정하지 않았다. 오류를 지우지 않는다.
새 source는 stop CLI의 exit만 기록하고 show instance의 JSON actual 상태로 판정한다.
이 **수정 source의 재실행은 아직 하지 않았다.** 최초 실제 종료와 수정 source의 검증 상태를 구별한다.

## 판정 범위와 다음 작업

실제 확인한 것은 외부 관리 프로세스의 DEADLINE 분기와 지정 인스턴스의 종료다.
COMPLETED/FAILED 경로 mock 시험, 관리 호스트 자체 종료/장기 네트워크 장애, 실제 job 결합은
아직 검증하지 않았다. stop 요청이 실패하고 모든 API 조회도 실패하면 자동 종료를 보장하지 않는다.
원본 V1/GPU job.sh 및 과거 NOT_STOPPING 기록은 그대로 보존한다. 유료 job에 옛 경로를 재사용하지 않는다.

최초 점검 뒤 서버는 정지했다. 설계자가 같은 서버를 다시 켜서 다음 단계 실행을 허용했다.
다음 단계는 새 guardian을 먼저 등록한 뒤 봉인 코드의 120초 이내 오프라인 시험·35개 원본 판독이다.
실제 수치 재계산·GPU 실행은 없다. 프로토콜 `f135cd92`와 오프라인 코드 봉인 `6bca97f4`를 변경하지 않는다.
