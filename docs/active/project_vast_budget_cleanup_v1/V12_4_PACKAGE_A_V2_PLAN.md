# V12.4 — 시험 1개 순서 수정 A 묶음 2판 계획 (2026-10-10, Claude 세션)

양식: [공통 검토 표준 V1](../IMPLEMENTATION_CRITICAL_QUESTIONS_STANDARD_V1.md) A–H.
상태: **계획 + 구현 대상 정의.** 유료 실행은 이 문서 범위 밖이며 별도 승인 기록이 필요하다.

## 0. 설계자 결정 (원문은 다른 세션이 전달)

이전 지시 "원래 봉인된 A320과 검색 측정 코드를 변경하지 않고 그대로 실행"(`revision_v12/search_contract_amendment.txt`)을
다음으로 바꾼다: **"시험 1개의 순서 실수만 고친 A 묶음 2판을 사용한다. 원본 묶음·원본 검문소·실패 원본은 기록으로 보존한다."**
판정 기준은 낮추지 않는다. 다른 319개 시험, 물리·수치 코드, 예산 규칙은 그대로.
설계자 원문 "승인 별도 세션으로 ㄱㄱ"는 이 세션이 직접 본 것이 아니라 시작 세션(local_e4aab317…)이 전달한 것이다.

## 1. 계획 전 전수 확인 결과 (실제 코드·원본 기준)

### 1-1. 묶음 안 (tablet_814.zip, SHA be06c9a7…, 814개)

| 확인 | 결과 | 방법 |
|---|---|---|
| 시험 파일 번호 41b7c97f…를 적은 묶음 안 파일 | `experiments/adaptive_experience_tablet_v0/code_seal.json` **하나뿐** | 814개 전 멤버 바이트 검색 |
| code_seal 번호 18a76f0e…를 적은 묶음 안 파일 | **없음** | 같은 검색 |
| protocol_seal(4개)·preservation_manifest(794개)가 시험 파일·code_seal을 포함 | 둘 다 **미포함** | JSON 키 대조 |
| protocol.json(f03bc97a…)이 시험 번호 포함 | 미포함 → **변하지 않음** | 바이트 검색 |
| 추가 봉인(pilot_a_resume_v1/code_seal.json, ec1b50b4…) | 시험·tablet 봉인 미언급 → **변하지 않음** | 바이트 검색 |

→ 2판에서 바뀌는 파일은 정확히 2개: 시험 파일, 그리고 그 번호 한 줄이 바뀐 code_seal.json. code_seal 번호가 18a76f0e…에서 새 값으로 바뀐다.

### 1-2. 묶음 밖에서 A 묶음 번호를 "원본과 같아야 통과"로 고정한 곳

| # | 위치 | 하는 일 | 2판 처리 |
|---|---|---|---|
| 1 | `revision_v12/transport/controller.py:33` `FIRST_CODE` + `:58-93` `verify_local_package` | 로컬 묶음 전수 대조(818→814개, 812+2 구조, 하드코딩 18a76f0e) | 2판 전용 확인 함수로 교체(같은 검사 + 원본과의 차이가 정확히 승인된 2개인지 추가 검사) |
| 2 | `controller.py:50-55` `configure` | package_bindings.json에서 CODE/ZIP/INVENTORY 등을 읽음 | A일 때 2판 장부를 읽도록 교체 |
| 3 | `controller.py:148-150` `local_preflight` 고정값 비교 | 승인 기록(binding)의 번호 == 모듈 번호 | #2·#5가 함께 바뀌므로 그대로 둠(한쪽만 바뀌면 실패하는 안전장치로 남음) |
| 4 | `controller.py:174-179` `local_preflight` | **이 PC 작업 폴더**의 원본 봉인 3종이 원본 파일과 맞는지 | 그대로 둠 — 원본 작업 폴더는 수정하지 않으므로 계속 통과해야 정상 |
| 5 | `revision_v12/campaign.py:214-232` `transport_binding` | 승인 기록에 묶음 번호를 적음 | A일 때 2판 번호로 덮어씀 |
| 6 | `campaign.py:34-49` `source_preflight` | 장부의 묶음 파일이 그대로인지 | 원본 검사는 그대로 실행 + 2판 파일 검사 추가 |
| 7 | `controller.py:395-398` `py_once` → 서버로 보내는 `guest_source_verify.py` (`:51` 18a76f0e 하드코딩) | 서버 안 검사 | `guest_source_verify.py`일 때만 2판 검사 프로그램을 보냄 |
| 8 | `controller.py:523-528` `validate_result` | 결과 status의 code_sha256 == CODE | #2로 자동 2판 |
| 9 | `revision_v12/lifecycle.py:200-222` `verified_recovery` → `terminal_proof.py:13` | 회수 결과 code_sha256 == 장부 번호. **부모 프로세스(cleanup)와 감시기(watchdog) 별도 프로세스 둘 다**에서 호출 | require_terminal을 감싸 원본 A 장부가 들어오면 2판 장부로 바꿈. 감시기에는 V12.4 다리(process_bridge)가 같은 장치를 설치 |
| 10 | 묶음 안 `offline.py:29-35,151-171` | 서버에서 봉인 3종 재검사, code_seal 번호를 결과에 기록 | 묶음 안 code_seal이 일관되게 바뀌므로 수정 불필요 |
| 11 | 시험 번호를 적은 역사 문서·장부(41b7c97f… grep 11곳, 18a76f0e… grep 50곳 이상) | 과거 기록 | **수정하지 않음**(역사 보존) |

`case_inventory_320.json`(시험 이름 320개)은 시험 이름이 바뀌지 않으므로 그대로 쓴다.
supervisor·guardian_driver는 묶음 번호를 읽지 않는다(import·grep 확인).

## A. 왜 하는가?

- 실제 문제: V12.3 유료 실행에서 A320이 319 통과 1 실패. 실패는 시험 자체의 순서 실수 — 파일 열기 기록을 켠 뒤 `request()`를 만들어서 `request()`/`environment()`가 직접 읽는 `A/session.json`이 기록됨(원본 `tests.log` 마지막 줄, 원격 PC 재현). 검색 함수(`catalog.py:195-197`)는 파일을 열지 않는다.
- 증거: 실패 원본 `C:\Users\zun24\.codex\evidence\project_vast_budget_cleanup_v1_20261009\project_v12_a_20261009_230201\transport\recovered\output\`(junit 320개 중 failure 1, status STOP/TEST_GATE_STOP, 서버 55109477 삭제 확인·장부 SETTLE 완료).
- 가장 단순한 해결: 시험 2줄만 바꾼 묶음 2판 + 그 번호를 확인하는 검문소 2판. 원본 파일을 덮어쓰는 방법은 다른 봉인 수십 곳과 원본 작업 폴더 검사(#4)를 깨뜨리므로 선택하지 않는다.
- 선택하지 않은 대안: (가) 원본 작업 폴더의 시험 파일 직접 수정 — #4·여러 역사 봉인 실패. (나) V12 폴더 전체 복사 — 60개 파일 재봉인·정책/승인 연결 재작성으로 변경 범위가 훨씬 큼. (다) V12.3 위에 얇은 층 — V12.3의 승인·감시기 다리가 자기 폴더에 묶여 있어 다른 모듈의 전역값을 바꿔야 함(더 취약).

**선택: V12.3 폴더를 `revision_v12_4/`로 복사하고(대부분 바이트 동일), 2판 연결 모듈 `package_v2.py`를 추가.**

### 시험 수정 내용 (2줄)

```python
# 원본 (tests/test_adaptive_experience_tablet_v0.py:243,246)
    tablet,_,_,_=archive; original=Path.read_bytes; accessed=[]
    hits=tablet.search(request())
# 2판
    tablet,_,_,_=archive; query=request(); original=Path.read_bytes; accessed=[]
    hits=tablet.search(query)
```
판정 `assert len(hits)==1 and accessed==[]`는 그대로. 즉 "검색은 파일을 하나도 열지 않는다"는 원래 의도를 그대로 검사한다.

## B. 무엇을 당연하게 여겼는가?

| 가정 | 근거 / 상태 |
|---|---|
| 묶음 안에서 바뀌는 파일은 2개 | 확인(1-1 전수 검색) |
| 다시 압축해도 나머지 812개 압축 바이트가 원본과 같다 | 확인(앞 200개 재압축 크기 일치, zlib 1.3.1). 빌더가 812개 전부의 CRC·압축 크기를 원본과 대조해 다르면 중단 |
| 원격 PC에서 같은 빌더로 만든 2판 zip 번호가 이 PC와 같다 | 원격 Python 3.12.10·zlib 1.3.1, 이 PC 3.12.7·1.3.1. **UNCONFIRMED → 원격 재생성으로 확인** |
| 원격 PC 저장소 사본의 V12·V12.3 파일이 이 PC와 같은 바이트 | 확인(V12 봉인 59/60 일치, 미추적 admin_payload.zip 1개만 없음; V12.3 26/26 일치) |
| 시험 수정이 다른 319개에 영향 없음 | 같은 파일 안 다른 함수는 바이트 동일. **원격 320개 실행으로 확인 예정** |
| 검색 측정이 시험 뒤 남은 시간 안에 끝난다 | **UNCONFIRMED.** 시험+측정 전체 한도 120초(`offline.py`), 지난 Vast 시험만 75.14초(CPU 1개 고정). 측정은 Vast에서 한 번도 실행된 적 없음 |

## C. 설계가 틀렸다면?

- 가장 먼저 깨질 곳: 2판 연결이 일부만 설치됨 → 승인 기록 번호와 검문소 번호 불일치. `local_preflight`(#3)가 서버 임대 **뒤에** 이를 잡으므로 돈이 든다. → 대책: 임대 전에 2판 검문소를 실제로 불러 확인하는 사전 점검을 `fresh_owned.main`에 추가, 원격 모의 시험으로 연결을 전부 검사.
- 감시기(별도 프로세스)가 2판을 모르면: 회수 결과를 "원본 번호 아님"으로 거부 → 서버를 삭제하지 않고 정지 보존(안전 쪽 실패지만 저장 요금·수동 폐기 필요). → V12.4 다리가 감시기에도 장치를 설치, 모의 시험으로 확인.
- "아무거나 통과" 위험: 2판 검사는 2판 번호를 하드코딩하고, 원본 묶음과 비교해 **차이가 정확히 2개 파일·code_seal은 그 번호 한 줄만**일 때만 통과. 원본 묶음·변조본은 거부해야 함 → 원격에서 실제 실행으로 확인.
- 정상처럼 보이는 반례: 2판이 통과해도 검색 측정이 120초 한도를 넘으면 `TOTAL_BUDGET_STOP` → 이 계통 3번째 유료 실패 → 3회 중단 규칙 발동. → 원격 PC 무료 예행(비공식, CPU 1개 고정)으로 시간 감을 먼저 본다(다른 기계라 참고값일 뿐).

## D. 다른 곳에 미치는 영향

| 변경 대상 | 영향 받는 부분 | 필요한 시험 | 미확인 |
|---|---|---|---|
| 새 2판 zip·장부 | 서버 업로드(40초 제한, 크기 ≈ 원본 36.8MB), guest_gate의 zip·inventory 번호 대조 | 원격 서버 안 검사 실제 실행 | Vast 업로드 속도 |
| controller 교체(configure/verify/py_once) | campaign이 파일 경로로 매번 다시 불러옴(`campaign.py:135-137,425-428`) — V12.3 로더 장치에 같이 연결 | 모의: 캠페인 경로로 불러온 모듈이 2판 값을 가짐, py_once 명령 모양이 원본과 같음 | — |
| transport_binding·source_preflight 감싸기 | 승인 기록·사전 점검 | 모의 | — |
| terminal_proof 감싸기 | 부모 cleanup, 감시기 | 모의(부모·다리 둘 다) | 실제 감시기 프로세스 사망 시나리오는 유료에서만 |
| 승인 형식 V12_4 | 이전 V12.3 승인 재사용 차단 | 모의 | — |
| 원본 파일 | **변경 0**(V12·V12.2·V12.3·tablet_814.zip·원본 봉인·작업 폴더 시험 파일) | 봉인 대조 | — |
| 권한·비용 | 무료 단계는 원격 PC만, 유료는 별도 승인 | — | — |

## E. 문제가 왜 발생했는가?

- 최초 실패: `test_only_selected_reference_files_are_opened` AssertionError(`accessed`에 session.json).
- 근본 원인: 시험 작성 시 기록 장치를 켠 뒤 입력을 만든 순서 실수. 이 시험은 묶음 봉인 전 실제 실행된 적이 없었다(`code_seal.json` status `SOURCE_PREPARED; REMOTE_TEST_AND_COST_BENCHMARK_PENDING`, 시험 수 `STATIC_AST_EXPANSION`).
- 사전 검토 공백: 이 PC 동적 시험 금지로 320개를 실제 돌리지 못한 채 봉인했다. 같은 가정(정적 검토로 충분)이 다른 65개 신규 시험에도 있었으나 이번 실행에서 그들은 통과했다.
- 같은 문제의 다른 사용처: 원본 작업 폴더의 같은 시험 파일도 같은 실수를 갖고 있다(이번 범위 밖, 후속 과제).

## F. 무엇으로 입증하는가?

1. 원격 PC(aic-2DESK-TOP, D 드라이브)에서 같은 빌더로 2판 zip을 다시 만들어 번호가 이 PC와 같은지.
2. 2판 zip을 그대로 풀어 `protocol.json`의 시험 파일 그대로 320개 실행: 실패·오류·건너뜀 0, 시험 이름 집합 == case_inventory_320.
3. 수정 전 반례: 원본 zip 풀이본에서 같은 시험 실패(이전 세션 재현 결과 재확인).
4. 서버 안 검사 2판을 가짜 경로로 실제 실행: 2판 통과 / 원본 묶음 거부 / 멤버 1바이트 변조본 거부 / 장부만 맞춘 변조본 거부 / 원본 서버 검사 프로그램은 2판을 거부.
5. 로컬 검문소 2판(verify_local_package 교체) 모의: 2판 통과, 원본·변조 거부.
6. V12.4 연결 모의 시험(원격): 모든 연결점 설치, 캠페인 경로 controller가 2판 값, 감시기 다리 장치, 승인 형식.
7. (선택·비공식) 검색 측정 함수 예행 시간 — 판정 입력 아님.
8. 별도 검토: Codex에게 실제 코드·봉인 대조 의뢰.

## G. 무엇을 아직 모르는가?

- Vast 기계에서 검색 측정 소요 시간(120초 한도 안 여부) — 유료 실행 전에는 모름.
- 원격 PC는 Windows: 서버(Linux)와 경로·CPU가 다름. 320개 통과가 Linux 통과를 보장하지 않는다(지난 Vast에서 319개는 Linux 통과).
- 감시기 실제 사망 경로·실제 SSH 단절 중 2판 회수는 유료에서만 확인 가능.
- 원격 모의 시험은 독립 권한 인증이 아니다.

## H. 지금 실행할 권한이 있는가?

- 2판 작성·봉인·원격 무료 시험: 설계자 결정(0절)으로 승인됨.
- 원본 보존: 새 경로만 생성, 원본 덮어쓰기 0, 루트 `.gitattributes` 수정 0.
- 유료 실행: **미승인.** 별도 V12_4 승인 기록 필요. 현재 장부(56행) 보수 계산: 상한 $2.00, 누적 경계 $0.903108, 활성 예약 0, 여유 $1.096892(최종 청구 아님). 예상 비용 약 $0.05, 예약 상한 $0.20.
- 3회 중단 규칙: 이 계통 유료 실패 2회(.gitattributes 봉인 실수, 이번 시험 결함). **다음 유료 실패 시 중단·보고.**
- push 하지 않음(사용자가 함). 커밋은 이름 지정 파일만.

## 2. 만들 파일 (전부 새 경로)

```
revision_v12_4/
  .gitattributes                 (* -text; 봉인 바이트 보호, 루트 파일 미수정)
  authority.py                   V12.3 복사, 승인 형식 V12_4_ACTUAL_BUNDLED_PAID_APPROVAL, 사용 기록 폴더 v12_4_paid_approval_use
  closure.py reads.py            V12.3과 바이트 동일
  process_bridge.py              V12.3 복사 + 감시기 모드에서 package_v2.install_recovery()
  fresh_owned.py                 V12.3 복사 + package_v2 설치 + 임대 전 2판 검문소 사전 점검
  package_v2.py                  2판 연결점(1-2절 #1,#2,#5,#6,#7,#9)
  guest_source_verify_v2.py      서버 안 검사 2판
  package_bindings_v2.json       A=2판, B=원본과 동일
  seal.py / operational_seal.json
  authorization_request.txt      변경 사유·설계자 원문(전달 사실 명시)
  package_A_v2/build_package_v2.py, tablet_814_v2.zip, inventory.json, revision_manifest.json
  tests/                         V12.3 모의 시험 복사(V12.4 대상) + test_package_v2.py
```
