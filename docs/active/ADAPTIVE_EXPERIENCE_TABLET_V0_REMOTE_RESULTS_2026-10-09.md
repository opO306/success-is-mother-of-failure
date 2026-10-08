# 경험 탭 V0 승인 원격 시험 결과

2026-10-09 KST. 기준 `0c0932ec`, 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`.

**REMOTE_TEST_GATE_FAILED / UNRESOLVED / NOT_VALIDATED.** 실제 320개를 실행했으나 **239 passed / 50 failed / 31 errors / skip 0**이다. pytest 로그 요약은 12.70초, JUnit suite time은 12.598초로 각각 원문 값을 보존한다. 두 숫자를 같은 계측으로 합치지 않는다. 기능 관문 실패 때문에 benchmark는 시작하지 않았다. 이전 행정 실패 3회를 유지하고 새 승인 창에서 시험 1회만 실행했다. 자동 재시도·현장 코드 수정 없음.

## 승인과 실제 운송·종료

사용자가 Vast54815136/machine56006/France, 경험 탭 320개와 합성 검색 측정, 600초/실행료 계산 기준 $0.05/시간당 $0.25, 새 물리·GPU·재시도·현장 수정 금지, 실패 원본 보존과 정지를 승인했다. 원문은 `admin_transport_static_20261009/authorization_approved_20261009_0130.json`에 보존했다. 이전 창의 종료 해시와 실패 3회를 포함한 새 승인 창이며 과거 시간을 초기화한 재시도가 아니다.

최초 새 API는 actual exited/intended stopped, machine56006/FR와 SSH ssh9.vast.ai:26992 및 실행 단가 $0.13462222222222225/h를 확인했다. 로컬 원문/행정 봉인/ZIP 확인 뒤 최초 시계를 기록하고 supervisor READY/lease 해시를 확인한 다음 승인된 재시작을 한 번 수행했다. 원본 guardian ARMED는 deadline371초/confirmation180초, 실제 서버와 승인·guardian hash가 일치했다.

실제 PID 1 환경에서 읽은 container ID54815136을 확인했다. 새 guest root `/workspace/tablet_v0_approved_20261009_0130`에 ZIP을 전달하고 813항목의 해제 원문 해시를 확인했다. 실제 runtime은 Python3.12.3, mpmath1.3.0/python backend, cryptography49.0.0, psutil7.2.2, pytest9.1.1이다. 검증한 실제 ID를 wrapper 환경으로 전달했으며 임의 ID를 만들거나 식별 관문을 우회하지 않았다.

gate는 returncode2/TEST_GATE_STOP으로 종료했다. 원격 실패 원본 10파일을 회수한 뒤 FAILED marker를 전달했다. guardian과 supervisor는 **STOP_CONFIRMED / trigger FAILED**를 기록했고 STOP 요청은 한 번이었다. 정지 절차 시작 뒤 19.891초에 actual exited를 확인했다. controller의 별도 API와 보고서 작성 전 추가 읽기 전용 API에서도 actual exited/intended stopped를 확인했다. 서버 destroy·추가 재시작 없음.

이 실행으로 새 supervisor→기존 guardian→실패 marker→실제 정지의 연결은 관측했다. 새 조합의 COMPLETED/DEADLINE·controller 소실·API 장애 등 모든 종료 반례가 실증된 것은 아니다. guardian final과 supervisor final, 새 API는 각각 보존했다.

## 실제 시험 결과와 직접 원인

| 시험 모듈 | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|
| adaptive_execution_verification_v0 | 24 | 0 | 0 | 0 |
| adaptive_execution_learning_v1 | 53 | 0 | 0 | 0 |
| adaptive_execution_real_learning_pilot_v0 | 64 | 1 | 0 | 0 |
| evidence_canonicalization_v0 | 44 | 16 | 0 | 0 |
| adaptive_execution_real_learning_pilot_a_resume_v1 | 19 | 33 | 0 | 0 |
| adaptive_experience_tablet_v0 | 35 | 0 | 31 | 0 |
| **실제 총계** | **239** | **50** | **31** | **0** |

JUnit의 실패·오류 81항목 모두 다음 경로의 FileNotFoundError를 직접 기록한다.

```text
experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json
```

로컬 checkout에는 해당 파일이 있고 raw SHA256은 `ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60`이다. 봉인된 탭 전달 ZIP/package manifest에는 포함되지 않았다. 기존 governance 및 A-resume 검증이 이 과거 봉인 파일을 읽으므로, 원문 해시가 전부 일치해도 이 패키지는 실제 실행 의존성을 완전히 담지 못했다. 작성자가 패키지의 의존성 폐쇄를 확인하지 못한 준비 결함이다. 셸 인용·CONTAINER_ID·guardian 미시작으로 시험 진입을 못 한 과거 실패와 구별한다.

현재 81건의 직접 원인은 같지만 이 파일을 포함하면 모든 기능이 통과한다고 추론하지 않는다. 다음 누락이나 기능 결함은 이번 결과만으로 배제할 수 없다. 이번 승인에서는 소스·시험·정책·기존 봉인·행정 코드를 수정하지 않았고 누락 파일을 원격에 추가하거나 재시험하지 않았다.

## 측정·예산·원본 해시

| 항목 | 결과 |
|---|---|
| 실제 시험 총수 | 320, 실패·error·skip 0 요구 **미충족** |
| 합성100/1000/10000건 검색 wall/CPU | **미측정**, 기능 관문 실패로 benchmark 미진입 |
| 선택 증거 재검증·CPU 경로 생성 비용 | **미측정** |
| Python traced peak/RSS/색인 증가 | **미측정** |
| 전체 gate 누적 CPU/메모리 실측 | STOP status에 기록 없음. 상한 설정을 실측 수치로 대신하지 않음 |
| 새 물리·GPU | 회수된 physics_guard: new_physics_calls0, gpu_calls0, blocked_attempts=[] |
| 전체 새 창 | UTC110.304039초 / monotonic110.313초, 보수적110.313초 |
| 실행료 계산 기준 추정 | **$0.0041251614444444453**, $0.05 미만 |

최초 시계는 2026-10-09 **01:30:47.727238 KST**, controller의 종료 API는 **01:32:38.031277 KST**다. 원본 회수는 01:32:14.847021 KST, 정지 확인은 guardian과 이후 API에 남았다. 전체600초/회수420초/정지 확인180초 범위 안이다. 실패 상태에는 시험+benchmark 전체 CPU/wall 정산이 생성되지 않아 pytest 시간과 전체 할당 시간만 따로 보고한다.

비용은 사용자가 승인한 실행 단가×보수적 창의 계산 기준이다. 실제 청구서·과거 사용료·별도 전송/장기 정지 저장 요금의 합계가 아니다. 시간당 상한은 조회 단가로 확인했다. physics guard는 기존 offline plugin의 관측 범위이며 OS 수준의 전 계산 증명으로 승격하지 않는다.

회수 ZIP SHA256은 `1c7e8090e74c50d4183ce2587721d6578c3f7041acbbb671fd50773bcf4ae9f4`, 회수 원본10파일의 ZIP member와 로컬 raw hash는 모두 일치한다. 행정 controller의 회수 영수증에 더해 사후 stdlib 분석으로 ZIP 파일 집합·CRC·개별 원문을 다시 확인했다. 이것은 작성자 별도 재대조이며 독립 감사 영수증은 아니다.

실행 전후 보호 원본794파일/정책4파일/코드812파일 불일치0, 행정 봉인8파일 raw 일치. 기존 지문은 유지됐다.

```text
protocol.json: f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c
code_seal.json: 18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09
source ZIP: ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392
administrative seal: 753c2f1407e7f42e54b5d344513228f736811716475c7bb777fba8c1b1953352
```

## 상태 구분·Git·한계

| 구분 | 이번에 말할 수 있는 상태 |
|---|---|
| **구현됨** | 기존 경험 탭과 운송 코드가 봉인대로 유지됨. 패키지 실행 의존성 누락 발견 |
| **시험됨** | 320개 실제 실행, 239통과/50실패/31오류. 새 운송·식별·회수·FAILED 종료 경로 실제 관측 |
| **독립 검증됨** | 이번 새 관문에 대한 독립 검토·감사 영수증 없음. 기존 서명 자료를 이번 성공으로 승격하지 않음 |
| **미확인** | 전체 오프라인 기능 통과, benchmark 비용, 성공/마감·모든 실패 종료 경로, 실제 전체 청구 |

원격 원본은 `admin_transport_static_20261009/run_approved_20261009_0130/recovered/`, controller·guardian·supervisor 원문은 같은 run 경로에 있다. 사후 원문 대조와 새 최종 API는 `remote_results_20261009_0130/author_analysis.json`, `fresh_final_instance.*`에 있다. 새 증거 전체 해시 목록과 변경 파일 목록을 별도로 보존한다. 기존 원본·봉인·구현 변경0, 새 승인/실행/실패/정지/분석 기록만 추가했다. GitHub push/master 병합0, 새 브랜치/worktree 없음.

이번 추가는 91파일이며 기존 추적 파일 변경은0이다. 원문 pytest 로그·JUnit에 pytest가 생성한 trailing whitespace가 있어 기본 Git 공백 검사에서 보고됐다. 이를 고쳐 원본 해시를 바꾸지 않았다. 해당 두 raw 파일을 제외한 추가 자료는 CRLF 원문을 인정한 공백 검사를 수행하고, raw 증거는 해시 목록으로 보존 여부를 확인했다.

**LOCAL FULL 생략 / 로컬 프로젝트 동적 시험 미실행 / 이유:** 사용자 금지이며 승인한 원격 관련 시험320개만 실행했다. 기준선 갱신 없음. 실패를 skip이나 PASS로 바꾸지 않았다.

구상 일치성 검토: 시험 전에 실제 서버/원문/승인을 결합했고, 실패 뒤 benchmark/새 물리/GPU/경험 승격 없이 원본을 회수하고 정지했다. 다른 CPU의 실제 성능 개선이나 경험 이전 실증은 없다. 다음 작업은 누락된 과거 봉인 파일 및 그 의존성의 정적 폐쇄 검토와 별도 수정 승인이다. 이번 승인으로 재패키징·봉인 변경·재실행을 자동 진행하지 않는다.
