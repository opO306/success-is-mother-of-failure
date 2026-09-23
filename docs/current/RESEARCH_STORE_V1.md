# 연구 데이터 저장소 v1 (2026-09-23)

**목적:** 모든 연구 실행을 나중에 분석하고, 학습형 B의 학습 데이터로 쓸 수 있게 영구 보관한다.
**위치:** `D:\KiroCrewTraceVault\success-is-mother-of-failure\research_store\` (Git 밖. `--root` 또는 `SIMOF_RESEARCH_STORE`로 변경 가능)
**코드:** 저장소 최상위 `research_store/`, 채우는 스크립트 `run_blind_benchmark.py`

## 불변 계약

1. **신뢰 등급 = 디렉터리.** `b_visible/`(B가 볼 수 있었던 별칭 데이터), `evaluator/`(실제 이름·spec·대응표), `ground_truth/`(정답·채점).
   태그가 아니라 저장 위치로 나눈다.
2. **학습형 B는 `b_visible`만 읽는다.** `research_store/b_visible.py`만 import 가능. 이 모듈은 다른 tier로 가는 코드 경로가 없다(테스트로 강제).
   `research_store/__init__.py`는 아무것도 import하지 않는다.
3. **b_visible 쓰기는 반드시 누출 검사를 거친다.** 그 세계의 비밀(실제 world id·revision·변수 이름·spec digest)이 한 글자라도 있으면 거부.
   검사 목록은 필수 인자라 생략할 수 없다.
4. **참조는 덜 비밀스러운 쪽으로만.** evaluator 레코드는 b_visible 객체를 가리킬 수 있지만, 반대는 금지.
5. **수정 불가.** 객체는 내용 해시가 이름(같은 내용은 1번만 저장). 레코드는 해시 체인으로 연결된 추가 전용 로그.
   정정은 새 레코드로만. 실패·반박·프로토콜 위반 실행도 지우지 않고 태그로 표시(`protocol_valid=false`).
6. **출처 필수.** 모든 레코드에 `commit`, `dirty`, `producer`, `semantics`. 스크립트는 커밋되지 않은 코드로는 쓰기를 거부한다.
7. **의미론이 다른 결과는 섞지 않는다.** 읽을 때 `semantics`를 반드시 지정해야 하고(기본값 없음), 섞이면 오류.
   의미가 바뀌는 변경(가설 어휘, 시간 규칙, baseline, 계획 형태, 판정 규칙)을 하면 `provenance.BLIND_RESEARCH_SEMANTICS`를 올린다.

## 지금 저장되는 것 (G7.3c blind 연구 실행 1회당)

| tier | record_type | 내용 |
|---|---|---|
| b_visible | `blind_research_run` | B의 journal 전체(가설 집합, 봉인된 예측, **실제 관측 궤적**, 비교, 탈락, 최종 봉인), 결과, G7.2 감사 결과 |
| evaluator | `blind_run_binding` | 실제 세계·revision·seed·spec, 별칭↔실제 대응표, b_visible 레코드 참조 |
| ground_truth | (G7.4부터) | 정답 대비 채점 |

## 한계 (정직하게)

- OS 수준 격리는 아니다. 사람이 evaluator 폴더를 직접 열면 읽힌다. 보장하는 건 **B 쪽 코드 경로**가 닿지 못한다는 것.
- 쓰기는 한 번에 한 프로세스만 가정(파일 잠금 없음).
- 이 저장소 도입 이전의 `runs/`(4.2GB)는 출처 정보가 없어 넣지 않았다.
- 물리 A 실행은 아직 저장 대상이 아니다.
