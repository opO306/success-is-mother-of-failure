# 경험 탭 V0 — 오프라인 검증 완료 기록

2026-10-10 KST. 브랜치 `codex/adaptive-experience-tablet-cpu-route-v0`.

**TABLET_INDEX_OFFLINE_VALIDATED / CPU_ROUTE_CANDIDATES_OFFLINE_VALIDATED — 근거 등급: 관문 동일 실행(Vast 공식 실행 아님), 설계자 인정.**
**NOT_PRODUCTION / OTHER_CPU_PERFORMANCE_UNMEASURED / COST_REDUCTION_UNKNOWN.**

이 문서는 [준비 보고](ADAPTIVE_EXPERIENCE_TABLET_AND_CPU_ROUTE_V0_PREPARED.md)의 "원격 시험 대기"를 이어받는다. 준비 보고는 당시 기록이고 봉인 목록(`adaptive_experience_tablet_v0/change_inventory.json`)에 있으므로 고치지 않았다.

## 발급 근거

[실행 전 봉인](ADAPTIVE_EXPERIENCE_TABLET_AND_CPU_ROUTE_V0_PROTOCOL.md)은 "제한 시험이 끝나기 전에는 두 라벨을 발급하지 않는다"고 정했다. 제한 시험이 아래처럼 끝났고, 설계자가 결과를 인정했다(원문 "인정해", 2026-10-10).

| 실행 | 묶음 | 결과 |
|---|---|---|
| 원격 PC(최하영바보) WSL2, 진짜 Linux 커널 6.18 | 2판 `93e8f08e…` | **PASS** 320/320, 실패·오류·건너뜀 0, 전체 25.17초(한도 120초), 검색 조회 중앙값 100/1000/10000건 = 0.058/0.060/0.063 ms(목표 10 ms) |
| 원격 PC WSL1(번역 방식) | 2판 | PASS 320/320, 50.57초, 조회 중앙값 0.191/0.191/0.195 ms |
| 노트북(aic-labtop) WSL2 | 2판 | PASS 320/320, 33.42초 |
| 위 세 곳 모두 | 원본 `be06c9a7…` | STOP `TEST_GATE_STOP`(같은 시험 1개 실패) — Vast V12.3 결과와 같음 |
| 노트북 WSL2 | 경험 탭 v0 66개 + v1 공유 힌트 24개 | 90/90 통과, 물리 차단 시도 0 |

- 실행기: `project_vast_budget_cleanup_v1/v12_4_remote_mock/local_gate_equivalent.py`. 공식 관문 `offline.py main()`의 승인 이후 본문(CPU 1개, CPU 120초, 메모리 512MiB, 120초 제한, 같은 pytest 명령·물리 차단 장치, 같은 검색 측정, 봉인 재검사, `validate_status`)을 따른다.
- 뺀 것: 유료 서버용 승인표(ticket/armed)와 바깥 감시 장치 확인. 가짜로 만들지 않았다.
- 원본 결과 위치: 원격 PC `D:\v12_4_mock\gate_outputs_wsl2`(목록 번호 `cb869d98…`), WSL1 `D:\v12_4_mock\wsl1_outputs`. 상세: [V12.5 결과](project_vast_budget_cleanup_v1/V12_5_DISCONNECT_CONFIRM_RESULTS.md), [2판 결과](project_vast_budget_cleanup_v1/V12_4_PACKAGE_A_V2_RESULTS.md).
- 2판은 시험 파일 하나의 순서 결함(`test_only_selected_reference_files_are_opened`에서 요청을 만들기 전에 파일 열기 기록 장치를 켬)만 고친 묶음이다. 판정 기준은 바꾸지 않았다. 프로젝트 폴더의 시험 파일과 코드 봉인도 2판과 같게 맞췄다(커밋 `e1f21711`, 장부 번호 `10e8c73f…`).

## 두 라벨이 뜻하는 것

- **TABLET_INDEX_OFFLINE_VALIDATED:** 색인 등록·검색·선택 원본 재검사·손상 처리 규칙이 봉인된 시험에서 모두 기대대로 동작했고, 합성 색인 1만 건까지 검색 조회가 10 ms 목표 안에 들었다.
- **CPU_ROUTE_CANDIDATES_OFFLINE_VALIDATED:** 확인된 물리 코어 수와 quota에 따라 SERIAL/W3/W4/W6 후보를 만들고, 불확실하면 거부하는 규칙이 모의 CPU 구조 시험에서 기대대로 동작했다.

## 두 라벨이 뜻하지 않는 것

| 아직 모르는 것 | 이유 |
|---|---|
| 다른 CPU에서 어느 방식이 실제로 빠른가 | 후보를 "만들 수 있다"만 확인했다. SERIAL과 W6의 실제 시간 비교는 Vast 서버 한 곳(Ryzen 9 3900X, 물리 12코어, 각 5회 중앙값 63.51초 → 13.51초, wall 약 4.8배 단축·CPU는 증가)뿐이다([A resume V1 결과](ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_A_RESUME_V1_RESULTS.md)) |
| 탭으로 전체 교육비가 줄어드는가 | 측정하지 않았다 |
| 실제 선택 경로 전체 비용 | 검색은 빠르지만, 기록을 쓰기 전 기존 관리자(Manager.choose)의 서명·원본 재검사 시간은 재지 않았다 |
| 운영 서비스 연결, W3/W4 학습 연결 | 구현하지 않았다 |
| OS 권한 격리, `RwForce` 수식 독립성 | 기존 한계 그대로 |
| Vast 공식 기록 | 없다. 같은 사람이 관리하는 PC에서의 관문 동일 실행이다 |

## 다음 경계

다른 CPU 실측은 이 라벨로 자동 시작하지 않는다. 별도 계획서(공통 A–H 검토 포함)와 설계자 승인 후에만 진행한다.
LOCAL FULL 생략 / 원격 관문 동일 실행으로 대체 / 이유: 사용자 로컬 동적 시험 금지, 기존 실행 코드 변경 없음(연구 폴더와 시험 파일 하나). 공식 기준선 숫자는 갱신하지 않았다.
