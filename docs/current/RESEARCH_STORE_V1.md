# 연구 데이터 저장소 v1 (2026-09-23)

**목적:** 모든 연구 실행을 나중에 분석하고, 학습형 B의 학습 데이터로 쓸 수 있게 영구 보관한다.
**위치:** `D:\KiroCrewTraceVault\success-is-mother-of-failure\research_store\` (Git 밖. `--root` 또는 `SIMOF_RESEARCH_STORE`로 변경 가능)
**코드:** 저장소 최상위 `research_store/`, 채우는 스크립트 `run_blind_benchmark.py`

## 불변 계약

1. **신뢰 등급 = 디렉터리.** `b_visible/`(B가 볼 수 있었던 별칭 데이터), `evaluator/`(실제 이름·spec·대응표), `ground_truth/`(정답·채점).
   태그가 아니라 저장 위치로 나눈다.
2. **학습형 B는 `b_visible`만 읽는다.** `research_store/b_visible.py`만 import 가능. 이 모듈은 다른 tier로 가는 코드 경로가 없다(테스트로 강제).
   `research_store/__init__.py`는 아무것도 import하지 않는다.
3. **b_visible 쓰기는 이중 검사를 거친다. 둘 다 필수 인자라 생략할 수 없다.**
   - 금지 목록: 그 세계의 비밀(실제 world id·revision·변수 이름·spec digest)이 한 글자라도 있으면 거부.
   - 허용 목록(`research_store/b_visible_schema.py`): 모든 문자열(키 포함)이 별칭 ID 형태, 가설 문장 문법,
     고정 조건 형태, 판정 단어, 예외 클래스 이름, **손으로 열거한 어휘** 중 하나여야 한다. 나머지는 금지 목록에 없어도 거부.
     어휘를 "아무 snake_case 단어"로 풀지 않는 이유: 실제 변수 이름(`x1`)도 그 모양이라서. 새 필드는 여기 추가해야 통과한다.
     오류 메시지는 거부된 문자열을 되풀이하지 않는다.
   - 못 막는 것: 문자열이 아닌 구조(개수·순서·정수·참거짓)를 통한 간접 누출. 설계 단계에서 막아야 한다.
4. **참조는 덜 비밀스러운 쪽으로만.** evaluator 레코드는 b_visible 객체를 가리킬 수 있지만, 반대는 금지.
5. **수정 불가.** 객체는 내용 해시가 이름(같은 내용은 1번만 저장). 레코드는 해시 체인으로 연결된 추가 전용 로그.
   정정은 새 레코드로만. 실패·반박·프로토콜 위반 실행도 지우지 않고 태그로 표시(`protocol_valid=false`).
6. **출처 필수.** 모든 레코드에 `commit`, `dirty`, `producer`, `semantics`. 스크립트는 커밋되지 않은 코드로는 쓰기를 거부한다.
   **`dirty` 판정 규칙:** 추적되는 파일 중 `.claude/` 밖의 파일이 커밋과 다르면 dirty.
   `.claude/`는 편집기·에이전트 도구 상태(세션 잠금, 로컬 skill)라 연구 데이터를 만드는 코드가 아니므로 제외한다.
   추적되지 않는 파일은 제외(커밋된 코드가 import하려면 그것도 커밋돼야 하므로). **이 외의 예외는 없다.**
7. **의미론이 다른 결과는 섞지 않는다.** 읽을 때 `semantics`를 반드시 지정해야 하고(기본값 없음), 섞이면 오류.
   의미가 바뀌는 변경(가설 어휘, 시간 규칙, baseline, 계획 형태, 판정 규칙, 기록 형식)을 하면 `provenance.BLIND_RESEARCH_SEMANTICS`를 올린다.
   b_visible 쓰기는 현재 semantics 라벨로만 가능하다(허용 목록이 다른 라벨을 거부).
8. **평가 경로는 단방향.** `engine/`은 `research_store`를 import하지 않는다. `research_store/b_visible*.py`는 `evaluator`·`ingest_blind`·
   `engine`·`ground_truth`에 닿지 않는다. G7.4 채점 코드가 생기면 같은 import 추적 테스트에 추가한다.

## semantics 이력

| 라벨 | 기간 | 차이 |
|---|---|---|
| `blind-research/g7.3c/vocab6/tick1/baseline-false/validate-full` | 2026-09-23 첫 18회 | journal에 실험 선택 기록 없음, 허용 목록 검사 없음(schema v1) |
| `.../validate-full/selection-log` | 2026-09-23 | 실험마다 `experiment_candidate_ranked`(단계·horizon·예상 분리 쌍 수) 기록, 허용 목록 검사(schema v2) |
| `.../selection-log/evidence-limits` | 2026-09-23 | 최종 가설마다 근거 연결(`evidence`: 실험별 supports/refutes → journal의 비교 기록 digest), 질문마다 B 자신의 한계 진단(`limitation_assessed`) |
| `blind-research/g8/grammar-v2/observe-first/notice-delayed` | 2026-09-24~ | G8: 관찰 전용 첫 실행으로 초기값 관측, 놀람(`anomaly_recorded`) → 알아챈 가설(`hypothesis_noticed`, DELAYED), 미검증 제안은 `proposed_hypothesis_ids`. 채점은 기준표 v2 |

## 지금 저장되는 것 (G7.3c blind 연구 실행 1회당)

| tier | record_type | 내용 |
|---|---|---|
| b_visible | `blind_research_run` | B의 journal 전체(가설 집합, **실험 선택 이유**(단계·horizon·예상 분리 쌍 수), 봉인된 예측, **실제 관측 궤적**, 비교, 탈락, 최종 봉인), 결과, G7.2 감사 결과 |
| evaluator | `blind_run_binding` | 실제 세계·revision·seed·spec, 별칭↔실제 대응표, b_visible 레코드 참조 |
| ground_truth | `benchmark_answer_key` | 봉인된 기준표 전체(key digest당 1번) |
| ground_truth | `blind_run_score` | 질문별 판정 7종 + 별도 축(구조 일치·관측 일치·한계 3종·과대주장·덜 좁힘·검증 완료·**B 진단과 기준표 일치 여부**), 기준표·evaluator·b_visible 참조 |
| ground_truth | `language_gap_report` | 언어 공백: B의 기록(판정·생존 가설·자기 진단)은 같은데 실제 구조가 다른 경우 모음. 실제 구조를 담으므로 evaluator 쪽에만 |

## 한계 (정직하게)

- OS 수준 격리는 아니다. 사람이 evaluator 폴더를 직접 열면 읽힌다. 보장하는 건 **B 쪽 코드 경로**가 닿지 못한다는 것.
- 쓰기는 한 번에 한 프로세스만 가정(파일 잠금 없음).
- 이 저장소 도입 이전의 `runs/`(4.2GB)는 출처 정보가 없어 넣지 않았다.
- 물리 A 실행은 아직 저장 대상이 아니다.
