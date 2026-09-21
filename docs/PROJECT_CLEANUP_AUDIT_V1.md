# 프로젝트 정리 감사 v1

상태: 읽기 전용 조사 완료, 삭제 미실행

## 1. 결론

현재 파일을 바로 삭제하지 않는다.

이유:

- 현재 폴더는 Git 저장소가 아니어서 파일별 복구 이력이 없다.
- 기존 확률 세계는 결정론 세계의 실패 원인과 비교 기준이다.
- 실패한 계측과 실험도 연구 방법의 증거다.
- 이전 사회·원시인·뇌 프로젝트는 현재 결정론 실행에 필요하지 않지만 별도 연구 계통으로서 가치가 있다.

권장 방식:

```text
분류
→ 이전 프로젝트 압축 보관
→ SHA-256 manifest 생성
→ 압축 해제 검증
→ 현재 핵심 테스트 재실행
→ 사용자가 목록 확인
→ 그 뒤에만 원본 삭제
```

## 2. 전체 용량

- `runs`: 약 4,238MB
- `data`: 약 51MB
- `tests`: 약 2.9MB
- `engine`: 약 2.7MB
- 나머지 문서·실행기: 비교적 작음

용량 대부분은 코드가 아니라 실험 결과다.

## 3. 반드시 유지

### 결정론 세계 핵심

- `engine/deterministic/`
- `worlds/deterministic_*.json`
- `run_deterministic_world.py`
- `run_deterministic_causal_world.py`
- `run_b_world_model.py`
- `tests/test_deterministic_*.py`
- 결정론 설계·감사 문서

### 확률 세계 기준선

사용자가 보존을 요청한 기존 확률 세계다.

- `engine/sequence/`
- `engine/living/events.py`
- sequence 실행기·probe·감사 도구
- `tests/test_sequence_*.py`
- 관련 설계 문서
- 관련 `runs` 결과

`engine.sequence`는 현재 `engine.living.events`의 사건 기록·난수 재생 형식에 의존하므로 `engine/living/` 전체를 즉시 삭제하면 안 된다.

### 실험 증거

- dual GCP 원본 archive·SHA-256·압축 해제 결과·분석
- VM 4시간 실험
- 30분·60분 계보 실험
- scheduler-v1 후보 감사 자료
- 실패한 첫 계보 측정 결과와 수정 근거

실패한 데이터도 오류 발견의 증거이므로 삭제보다 `invalid-measurement` 표시가 적절하다.

### 장기 설계 문서

- `PROJECT_CONSTITUTION.md`
- `EVOLVABLE_LANGUAGE_PLAN.md`
- `EVOLUTION_V2_PLAN.md`
- `docs/`의 단계별 판정·근사·감사 문서

이 문서들은 과거 병목을 다시 놓치지 않게 하는 설계 이력이다.

## 4. 이전 프로젝트 보관 후보

현재 결정론·확률 미시세계에서 직접 사용하지 않는 별도 사회·원시인 계통:

- `engine/agentworld/`
- `engine/primal/`
- `engine/brain/`
- 사회 시뮬레이션용 최상위 `engine/*.py`
- `run_agent_world*.py`
- `run_primal.py`
- `run_llm_comparison.py`
- 관련 `tools/`
- 관련 테스트
- `data/terrain/`
- 사회·원시인·두뇌 evolution 관련 `runs/`
- dashboard·CSV·로그 출력

판정:

- 현재 결정론 패키지는 이 계통에 의존하지 않음
- 현재 확률 `engine.sequence`도 `engine.living.events` 외에는 이 계통에 직접 의존하지 않음
- 그러나 기존 전체 테스트는 이 파일들을 사용하므로 바로 삭제하면 회귀 기준도 함께 사라짐

권장:

`legacy-society-primal-brain-v1`이라는 별도 archive로 묶고 manifest와 함께 보관한 뒤 현재 프로젝트에서 분리한다.

## 5. 안전 삭제 가능성이 높은 생성 캐시

다시 생성할 수 있는 항목:

- 프로젝트 최상위 `__pycache__/`
- `engine/**/__pycache__/`
- `tests/__pycache__/`
- `tools/__pycache__/`
- `.pytest_cache/`

현재 확인 용량은 크지 않다. 삭제해도 공간 절약 효과는 약 수백 KB 수준이므로 급하지 않다.

## 6. 보관 후 삭제 가능한 출력 후보

별도 이전 프로젝트 archive에 포함하고 검증한 뒤 원본 삭제를 검토할 수 있다.

- `agent_world_output.log`
- `llm_comparison_output.log`
- `primal*.log`
- `agentworld*.log`
- `dashboard_data.json`
- 생성된 `*_timeseries.csv`
- `experiment_*.csv`
- `events_summary.csv`
- `wmd_attempts.csv`
- 이전 dashboard 출력

이 파일들은 현재 결정론 세계 실행에는 필요하지 않다. 다만 이전 연구 결과이므로 바로 삭제보다 archive 우선이다.

## 7. runs 정리 원칙

사용자가 실험 결과 데이터는 유지하기로 했으므로 현재는 삭제 대상에서 제외한다.

가장 큰 항목:

- `dual_gcp_precommit_20260919_185150`: 약 2.9GB
- `sequence_probe_stage_c_length3.jsonl`: 약 127MB
- `local60_observer_20260919_165643`: 약 68MB
- `sequence_probe_stage_c_length3_long96_checkpoint8.jsonl.gz`: 약 43MB
- 이전 primal/evolution 실행 다수: 각각 수십 MB

`dual_gcp`는 원격 압축파일과 압축 해제본이 함께 있어 중복 용량이 크다. 그러나 현재 분석 경로가 압축 해제본을 참조하므로 별도 정리 승인 전 유지한다.

## 8. 삭제 전에 필요한 안전장치

1. 이전 프로젝트 파일 목록 생성
2. 파일별 SHA-256 manifest
3. 압축 archive 생성
4. archive SHA-256 생성
5. 임시 폴더에 시험 압축 해제
6. 원본과 archive 파일 수·총용량·개별 해시 비교
7. 결정론 테스트만 별도 실행
8. 확률 sequence 테스트 별도 실행
9. 사용자가 실제 삭제 목록 확인
10. 명시적 승인 후 삭제

## 9. 권장 프로젝트 구조

```text
current/
  engine/deterministic
  engine/sequence
  engine/living/events.py
  worlds
  docs/current
  tests/deterministic
  tests/sequence
  runs/current-evidence

archive/
  legacy-society-primal-brain-v1.tar.gz
  legacy-society-primal-brain-v1.sha256
  historical-docs/
  historical-runs/
```

실제 이동은 import 경로와 테스트를 깨뜨릴 수 있으므로 archive 검증 후 별도 작업으로 수행한다.

## 10. 최종 권장

- 확률 세계: 그대로 유지
- 결정론 세계: 현재 주 개발 계통
- 이전 사회·원시인·뇌 프로젝트: 삭제보다 먼저 별도 보관
- 실험 데이터: 유지
- 캐시: 원하면 즉시 삭제 가능하지만 절약량 작음
- 원본 삭제: archive 검증과 사용자 승인 뒤에만 수행
