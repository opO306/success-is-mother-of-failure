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
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. 활성 Gate는 C1-B1의 outer formal bound ④다. **④ 전체는 FROZEN 아님, ⑤ 미착수.** 상세·다음 Gate는 `CURRENT_STATE.md`를 본다.

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

### 검증 명령 (고정)

작업 후 반드시 실행한다. "아마 됐을 것"은 보고로 인정하지 않는다.

```bash
python -m pytest tests -q -n 6          # 표준 (LOCAL FULL): pytest-xdist, 작업자 6개, 약 6분
python -m pytest tests -q               # 직렬 기준 경로: 약 13분 — 병렬 결과를 의심할 때, 그리고 큰 변경 뒤 대조용
```

**기준선: 2404개 통과 + 1 xfailed, skip 0** (2026-09-27 기준, `-n 6` 388.84초; outgoing bootstrap/tail 및 rounding decision cover 구현. tail 결정성 인증 완료, R=20 비영 reachable cover는 미인증이며 ④ FROZEN 아님. D_valid 동결 유지. 컴파일러 출력 인코딩 경고 25건. xfail은 strict: binary64 절대 위치 탈락 사유 고정). 이보다 줄면 회귀다.
skip이 생기면 통과로 세지 않는다(MSVC·nvcc·GPU·`D:
eference`가 없으면 해당 시험이 skip된다).

**Codex 인수인계 재실측(2026-09-27, 당시 이력):** 2307 passed + 1 strict xfailed / skip 0, 445.58초, 컴파일러 출력 인코딩 경고 24건. 현재 기준선과 구별한다. 기본 셸에서 외부 해시 검사가 skip되면 설치된 `C:\Program Files\Git\usr\bin\sha256sum.exe`가 PATH에 있는지 확인한다. 기본 cp949와 `PYTHONUTF8=1` 모두에서 진단 출력 해독 경고가 남았으므로 UTF-8 강제로 해결됐다고 보고하지 않는다. 상세·로그 위치: [docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md](docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md).

**병렬 채택 근거 (2026-09-26 측정, 설계자 승인 조건 충족):** 직렬 793초 / `-n 6` 369초 / `-n 8` 377초 / `-n 10` 389초 / `-n 12` 376초 —
네 설정 모두 **시험 2248개의 결과가 직렬과 하나하나 동일**(junit 대조, 병렬에서만 깨지는 시험 0). 속도는 약 2.1배에서 멈춘다: GPU를 쓰는
시험의 합(약 365초)이 GPU 한 장에서 병렬로 줄지 않기 때문이다. 작업자를 늘리면 GPU·컴파일러 경합만 커진다(`-n 12`에서 시험 시간 합 1551초).
**실행 이름을 구분한다:** `LOCAL FULL` = 이 로컬 전체(Python + native CPU/CUDA + Windows 계약 + `D:
eference`). 원격 리눅스에서는 native가 skip되므로
`REMOTE PYTHON FULL`로 부르고 LOCAL FULL과 같은 의미로 보고하지 않는다. `REMOTE STUDY` = 궤적·정밀도·감사 계산.

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
