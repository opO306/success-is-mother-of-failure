# 먼저 읽을 것 — 작업 시작 전 필수

이 저장소에서 작업하는 모든 에이전트는 **작업 전에 이 파일과 아래 3개를 읽는다.**

| 파일 | 내용 | 언제 |
|---|---|---|
| `RULES.md` | 절대 깨면 안 되는 불변조건 | 항상 |
| `CURRENT_STATE.md` | 지금 어디까지 왔고 다음이 뭔지 | 항상 |
| `REPO_MAP.md` | 디렉터리·모듈·데이터 흐름 | 코드를 건드릴 때 |

저장소 전체를 탐색하지 말고 이 4개로 시작한다. 이 문서들이 실제 코드와 어긋나면 **코드가 옳고 문서가 낡은 것이다** — 그 사실을 보고하고 문서를 고친다.

---

## 이 프로젝트가 뭔지 (1분 요약)

**목표:** 생명 발생 이전(LUCA 이전) 수준의 세계를 결정론 물리로 만들고, 그 세계를 스스로 관찰해 법칙을 발견하는 모델을 만든다.

**A와 B의 분리가 이 프로젝트의 핵심 구조다.**

- **A = 세계.** 결정론 물리가 실제로 돌아간다. 난수·확률·추첨 없음. 같은 입력이면 항상 같은 결과.
- **B = 관찰자.** A를 들여다보고 이론을 세우고 예측하고 틀리면 고친다. **A를 직접 조작하지 않는다.**

B가 A를 만들거나 바꾸면 자기 답을 자기가 채점하는 꼴이 된다. 이 분리는 타협 대상이 아니다.

**현재 개발 우선순위(2026-09-27):** A: ACTIVE → L: DEFERRED UNTIL A FOUNDATION IS SUFFICIENT → B: DEFERRED TO LATE STAGE, NOT CANCELLED.
A의 기반이 충분해진 뒤 L은 A 안에서 자연 발생·진화하는 계통으로 진행한다. A와 L이 어느 정도 완성되어 작은 세계가 돌아가는 단계 뒤 B를 본격적으로 만든다.
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1이며, 2026-10-01부터 **세계 / 검증 / 관측 세 층 분리** 기준으로 종료 조건을 재정의했다(`docs/active/A_THREE_LAYER_SEPARATION_V1.md`). 한 걸음의 건전성과 승인된 independent replay verifier의 전 step 재검증은 Gate, 전 궤적 사전 증명은 연구 과제다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.
**L 원칙(헌법 v0.3):** L은 생명을 만들지 않고 관측한다. 가능성 차단은 실패, 미발생은 유효한 결과다(`docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md`).

**현재 정직한 한계:**
- B는 학습형 신경망이 아니다. 사람이 규칙을 적어준 결정론 어댑터다.
- A는 v2에서 다중 결합과 사슬 성장까지 왔다. 촉매·주형 복사는 아직 없음.
  단, **"사슬 성장 완료"를 "사슬이 자유롭게 자란다"로 읽으면 안 된다** — 실측 최장 길이는 3이고,
  움직이는 사슬은 자랄 수 없으며, 한 tick에 결합 하나만 생긴다. 전부 선언된 법칙이 아니라
  구현에서 떨어져 나온 천장이다. [docs/history/LOCAL_INTERACTION_PRINCIPLES_V1.md](docs/history/LOCAL_INTERACTION_PRINCIPLES_V1.md) 참조.
- **v2 성장 경로의 물리는 particle_id에 의존한다** — 구별 불가능한 후보 중 번호가 작은 쪽이 이긴다. v2는 동결 형식이라
  이 잘못된 동작을 재현성 때문에 보존한다(`tests/test_legacy_causal_semantics.py`의 `legacy_defect`).
  **causal v5에서는 해소됐다**(GEO v1B, 2026-09-24): 성장·병합이 이름·순서와 무관하며, v2의 길이 3 천장이 제거되어 31개 사슬까지 검증됐다.
  별도 크기 상한은 구현되어 있지 않지만, 정사각형 기하와 미정의 충돌은 성장 경로를 제한한다.
  수정된 성질의 증거는 `tests/test_v5_geo_v1b.py`, 동결 v2의 잘못된 동작은 `tests/test_legacy_causal_semantics.py`에 있다.
  `tests/test_known_defects_causal_kernel.py`에는 현재 살아 있는 결함 시험이 없고, 다음 결함을 기록할 자리로 남아 있다. 새 결함 시험을 추가하거나 해석할 때 파일 맨 위를 읽을 것.
- 따라서 **생명·복사·진화의 새 증거는 아직 나오지 않았다.**

---

## 작업 방식

### 새 계획의 의문·영향·반례 검토 (2026-10-09 설계자 지시)

앞으로 모든 새 구현·수정·실험 계획서는 [공통 검토 표준 V1](docs/active/IMPLEMENTATION_CRITICAL_QUESTIONS_STANDARD_V1.md)의 A–H 항목을 필수로 포함한다. 중요한 가정에는 실제 원본·코드 위치·시험 결과를 연결하고 근거가 없으면 `UNCONFIRMED`로 표시한다. 변경 함수의 모든 직접·간접·예외·시작·종료 호출 경로를 분석한다. 오류가 나면 수정 전에 원인·영향·반례 분석 관문을 수행하고, 자기반박 및 실제 코드/원본을 보는 별도 검토를 남긴다. 기존 역사 계획·실패 원본·봉인은 변경하지 않는다. 별도 검토는 독립 권한 인증이 아니다. 실행 승인·중단 규칙·기존 계산/검사 기준을 이 표준으로 완화하지 않는다.

### 검증 명령 (고정)

작업 후 아래 기준으로 검증한다. "아마 됐을 것"은 보고로 인정하지 않는다.

**LOCAL FULL이 필요한 경우 (2026-09-29 설계자 결정)**
- 기존 실행 코드, 물리식, 인증 로직, 공용 모듈, 동결 fixture 또는 계약을 수정한 경우
- 여러 번 LOCAL FULL을 생략한 독립 변경을 하나의 공식 개발 단계/Gate로 묶어 종료하는 경우
- 공식 LOCAL FULL 기준선 숫자를 새로 갱신하는 경우

**관련 시험으로 대체할 수 있는 경우 (아래를 모두 만족)**
- 새 survey_only/분석 파일, 새 시험, 문서만 추가했고 기존 실행 코드와 공용 로직을 수정하지 않았다
- 동결 계약, 해시 고정 소스, fixture가 바뀌지 않았음을 변경 파일 목록으로 확인했다
- 신규 시험과 직접 영향 범위의 기존 시험이 통과했다

단순 commit 또는 push 자체는 LOCAL FULL 실행 사유가 아니다.
LOCAL FULL을 생략했다면 보고에 `LOCAL FULL 생략 / 관련 시험으로 대체 / 이유`를 명시하고 아래 기준선 숫자는 갱신하지 않는다.
생략된 변경들은 다음 공식 통합 Gate에서 LOCAL FULL 한 번으로 확인한다.
중단되거나 미완료된 FULL은 통과나 기준선으로 세지 않고 로그를 보존한다.

```bash
python -m pytest tests -q -n 6          # 표준 (LOCAL FULL): pytest-xdist, 작업자 6개, 약 6분
python -m pytest tests -q               # 직렬 기준 경로: 약 13분 — 병렬 결과를 의심할 때, 그리고 큰 변경 뒤 대조용
```

**기준선: 3289개 통과 + 1 xfailed, skip 0** (2026-09-30 기준, HEAD `1636b1d`, LOCAL FULL `-n 6` 554.35초, 실패·error 0, junit tests 3290 / skipped 1 = 아래 strict xfail. 2834 → 3289의 455개는 그 사이 checker V1/V2·point prover·runtime wrapper·Proof Cache 등 여러 Gate가 관련 시험만으로 LOCAL FULL을 생략했고 이번 실행이 한 번에 확인한 몫이며 회귀가 아니다. 컴파일러 출력 인코딩 경고는 이번 -q 요약에 보이지 않았으나 원인 미조사, 해결로 보고하지 않음. xfail은 strict: binary64 절대 위치 탈락 사유 고정). 이보다 줄면 회귀다. 이 숫자는 이미 완료된 LOCAL FULL 결과의 문서 갱신이며(설계자 판정 2026-09-30) 갱신하려고 FULL을 다시 돌리지 않았다.

**이전 기준선(2026-09-28, 역사): 2834개 통과 + 1 xfailed, skip 0** (2026-09-28 기준, `-n 6` 398.68초, 같은 커밋 REMOTE LINUX FULL(32워커) 재실행 2835개 항목별 동일(첫 실행의 무관 간헐적 실패 1건 제외); rational-spacing family checker·exact modular-distance·full residue-class·normalized quotient-gap·same-input filter/checker·shell-18 hard-case search·certificate·shell-16/17 survey·certificate 시험 포함. shell 16/17/18 hard-case 인증서(후보 6,581/827/109·hazard 0). shell 18 hard-case 인증서로 원래 domain 하나 Certified(후보 109·hazard 0), shell 19〜23 5개와 합친 fresh coverage 14/64 region·gap 81. shell 15는 미승인. same-input 최소 구현에서 작은 241 class의 2,980 입력을 singleton 분할로 추가 확인해 class 하한 집계 6,436·미해결 7,835다. 실제 큰 class symbolic 하한·새 shell lemma·인증 0개. 남은 큰 family 19개와 R=20 전체 미인증이며 ④ FROZEN 아님. D_valid 동결 유지. 컴파일러 출력 인코딩 경고는 직전까지 25건이었고 이번 실행 요약에는 경고 줄이 없었다(원인 미조사, 해결로 보고하지 않음). xfail은 strict: binary64 절대 위치 탈락 사유 고정).
skip이 생기면 통과로 세지 않는다(C++ 컴파일러(MSVC 또는 g++)·nvcc·GPU·`D:\reference`가 없으면 해당 시험이 skip된다).

**Codex 인수인계 재실측(2026-09-27, 당시 이력):** 2307 passed + 1 strict xfailed / skip 0, 445.58초, 컴파일러 출력 인코딩 경고 24건. 현재 기준선과 구별한다. 기본 셸에서 외부 해시 검사가 skip되면 설치된 `C:\Program Files\Git\usr\bin\sha256sum.exe`가 PATH에 있는지 확인한다. 기본 cp949와 `PYTHONUTF8=1` 모두에서 진단 출력 해독 경고가 남았으므로 UTF-8 강제로 해결됐다고 보고하지 않는다. 상세·로그 위치: [docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md](docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md).

**병렬 채택 근거 (2026-09-26 측정, 설계자 승인 조건 충족):** 직렬 793초 / `-n 6` 369초 / `-n 8` 377초 / `-n 10` 389초 / `-n 12` 376초 —
네 설정 모두 **시험 2248개의 결과가 직렬과 하나하나 동일**(junit 대조, 병렬에서만 깨지는 시험 0). 속도는 약 2.1배에서 멈춘다: GPU를 쓰는
시험의 합(약 365초)이 GPU 한 장에서 병렬로 줄지 않기 때문이다. 작업자를 늘리면 GPU·컴파일러 경합만 커진다(`-n 12`에서 시험 시간 합 1551초).
**실행 이름과 역할을 구분한다(설계자 판정 2026-09-28):**
- `LOCAL FULL` = **공식 기준선.** 이 로컬 전체(Python + native CPU/CUDA + Windows 계약 + `D:\reference`).
- `REMOTE LINUX FULL` = **플랫폼 독립성·fixture/hash·native/GPU 교차검증 게이트.** 원격 리눅스 노드에서 native를 g++/nvcc로 빌드하고 원문 파일을 복사해 skip 0으로 전체를 실행한다. Windows에서는 통과하고 리눅스에서만 깨지는 결함(줄바꿈 의존 해시)을 실제로 잡은 사례가 있다(2026-09-28). LOCAL FULL과 같은 것으로 취급하지 않는다.
- 그 이전의 skip 있는 원격 실행은 `REMOTE PYTHON FULL`로 구별한다. `REMOTE STUDY` = 궤적·정밀도·감사 계산.

특정 계통만 빠르게 볼 때:

```bash
python -m pytest tests/test_deterministic_*.py -q    # 결정론 A/B
python -m pytest tests/test_audit_*.py -q            # 독립 감사
python -m pytest tests/test_sequence_*.py -q         # 동결된 확률 세계
```

### 읽기 범위 제한

관련 없는 파일을 대량으로 읽지 않는다. 작업 대상에 맞춰 범위를 지정한다.

| 작업 | 읽을 범위 |
|---|---|
| 결정론 A 물리 | `engine/deterministic/` + `worlds/` + 해당 테스트 |
| 모델 중립 B | `engine/deterministic/` (b_language, *_adapter, cognitive_map, change_graph 등) + `schemas/` |
| 독립 감사 | `audit/` — **`engine` import 금지** (테스트가 강제) |
| 연구 데이터 저장소 | `research_store/` + [docs/deferred/RESEARCH_STORE_V1.md](docs/deferred/RESEARCH_STORE_V1.md). 데이터는 D: (Git 밖). **학습형 B는 `research_store.b_visible`만 import** |
| 확률 세계 (동결) | `engine/sequence/`, `engine/living/` — **수정 금지, 읽기만** |
| 레거시 | `engine/primal|brain|agentworld/` — 현재 작업 대상 아님 |

`runs/`(4.2GB)는 통째로 읽지 않는다. 특정 결과가 필요하면 경로를 지정해 해당 파일만 읽는다.

### 실패 시 중단 규칙

**3회 시도해서 실패하면 멈추고 보고한다.** 계속 고치려 들지 않는다.

보고에 포함할 것: 시도한 것, 실패한 지점, 원인 후보, 다음에 해볼 실험.

테스트 1회가 약 2분이므로 무한 디버깅 루프는 비용이 크다.

### 모델 선택

| 작업 | 권장 |
|---|---|
| A 물리 커널 설계·구현 | 강한 모델 (여기서 틀리면 위의 모든 실험이 무효) |
| 원인 불명 버그, 여러 모듈 상호작용 | 강한 모델 |
| B 도구 구현 | 중간 모델 (B는 A가 독립 채점하므로 안전망 있음) |
| 테스트 실행·결과 확인·문서 정리 | 가벼운 모델 |

---

## 설계자와 에이전트의 관계 (헌법 제23조)

사용자는 **코드를 직접 검증하는 개발자가 아니라 방향을 결정하는 설계자다.**

따라서 매 변경 후:

1. **쉬운 말로** 실제 작동을 설명한다. 전문용어를 늘어놓지 않는다.
2. 자동 테스트와 **별도로** 구상 일치성을 2차 검증한다.
3. 근사·미구현·충돌·숨은 강제 조건을 **먼저 공개한다.** 설계자가 판단할 수 있어야 한다.

잘 된 것만 보고하고 한계를 숨기는 것은 이 프로젝트에서 가장 심각한 실패다.

---

## 참조 문서

문서 상태·폴더·이동 경로는 [docs/README.md](docs/README.md)·[DOCUMENT_STATUS_INDEX.md](docs/DOCUMENT_STATUS_INDEX.md)를 먼저 본다. `docs/current/`는 옛 경로 호환 안내이며 활성 문서는 `docs/active/`에 있다. 동결 계약과 과거 설계는 구분한다.

위 4개로 부족할 때만 본다. 크기가 커서 매번 읽지 않는다.

| 문서 | 내용 | 크기 |
|---|---|---|
| `PROJECT_CONSTITUTION.md` | 헌법 26조. 모든 설계 판단의 최종 기준 | 9KB |
| [docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md](docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md) | B 전체 아키텍처 + 장기 후보 | 58KB |
| [docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md](docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md) | 구현 순서와 완료 판정 | 32KB |
| [docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md](docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md) | 당시 중간 점검 (역사). 한계가 솔직히 적혀 있음 | 5KB |
| [docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md](docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md) | **검증이 무엇을 못 잡는가.** 오류 유형·결함 주입 기록·체크리스트 | 6KB |
| [docs/history/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md](docs/history/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md) | A 물리 심화 설계 | 22KB |
| `LLM_HANDOFF/README.md` | 계통별 파일 카탈로그 (외부 LLM 전달용) | 1KB |
