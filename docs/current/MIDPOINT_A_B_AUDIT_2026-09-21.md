# A·B 프로젝트 중간 점검 — 2026-09-21

상태: 코드·저장 증거 read-only 감사 완료

## 1. 결론

현재 프로젝트는 결정론 A와 모델 중립 B를 연구할 기술 기반은 강하지만, 독립 학습 모델이 새 이론을 발견했다고 주장할 단계는 아니다.

| 영역 | 상태 | 판정 |
|---|---|---|
| 결정론 A 물리 기반 | 안정 | 재현·보존·지역성 검증 |
| CPU/GPU field 동등성 | 안정 | 매 tick 동일, 512²에서 약 3.9배 기준 |
| B 외부 경계·권한 | 안정 | 내부 자유·외부 claim 검증 |
| 사용자 전용 계보 | 안정 | 12/12 private trace 검증 통과 |
| 독립 B 표현 | 초기 후보 | Cognitive Map·ChangeGraph는 수작업 규칙 모델 |
| 불확실성·반사실 | 초기 후보 | 작은 고정 benchmark |
| 이론 수정 | 기준 사례 | A에 이미 존재하는 vapor를 제한 이론에서 누락한 실험 |
| Held-out 실험 | 실행 금지 | 제안서는 봉인됐지만 과학적 실행 준비 전 |
| 실제 학습형 B | 미착수 | JEPA·신경망·자율 변수 발견 없음 |
| 결정론 화학·고분자 | 미착수 | 환경 기반까지만 구현 |

## 2. 확인된 구현

### A

- 난수·seed·추첨 없는 결정론 CPU 기준
- 물질·에너지·운동량과 외부 에너지 장부
- 지역 열·물·용질·수증기 이동
- 광물 용해·침전과 물 상변화
- 물리 단위·flux 계약과 해상도 수렴 후보
- CUDA int64 field transport와 CPU 매 tick 동등성
- GPU 상주 field 기준에서 CPU 대비 최대 약 3.9배

### B

- exact oracle
- B-Language 외부 경계와 BrainAdapter
- Cognitive Map
- ChangeGraph와 trusted TraceViewBroker
- 동일 외부 질의 병렬 비교
- 다음 영향 범위 예측
- HypothesisSet
- CounterfactualBranch
- ResidualPattern
- TheoryRevisionProposal
- 사용자 승인형 ExperimentProposal

### 증거

- 최신 전체 테스트: 837개 통과
- 결정론 모듈: 25개, 약 5,395줄
- 결정론 테스트: 26개 파일, 약 1,858줄
- 사용자 전용 HDD trace: 12/12 hash chain·delta·snapshot 검증 통과
- held-out 제안서 상태: `pending-user-approval`
- held-out 제안서의 A record: 0개
- C: 여유 약 312GB, D: HDD 여유 약 712GB

## 3. 강한 한계

### 진짜 학습 모델은 아직 없다

Cognitive Map과 ChangeGraph는 A transition을 직접 호출하지 않는 독립 표현 후보지만 학습형 신경망이 아니다. TheoryRevision도 알려진 `vapor`를 의도적으로 뺀 제한 이론의 기준 시험이다.

### 영향 범위가 넓다

- 후보 범위 263칸
- 실제 변화 4칸
- 누락 0
- 과잉 259칸

안전한 첫 기준이지만 효율적 영향 예측이라고 부르지 않는다.

### A는 아직 단순하다

> **2026-09-22 갱신:** 이 절은 causal v2 이전 상태다. "입자당 결합 하나"는 더 이상
> 사실이 아니다(`ports`만큼 다중 결합). 최신 판정은
> `../../CURRENT_STATE.md`와 `LOCAL_INTERACTION_PRINCIPLES_V1.md`를 본다.

- ~~입자당 결합 하나~~ → v2에서 다중 결합. 단 **실측 최장 사슬은 3**
- 다중 화학 중간체·실제 촉매·고분자 없음
- 주형 복사 없음
- 실제 경계 물질과 독립 경계 절단·봉합 없음
- 초기 지구 실측 환경군 없음

따라서 생명·복사·진화의 새로운 증거가 나온 것은 아니다.

## 4. Held-out 제안서 차단 조건

현재 제안서:

`D:\KiroCrewTraceVault\success-is-mother-of-failure\heldout-experiment-proposal-v1`

상태:

```text
governance_valid = true
scientific_status = not-run
execution_allowed = false
A records = 0
```

그대로 실행하기 전에 다음이 필요하다.

1. 부모·변수 추가·관계 추가 후보의 구체적 수치 예측 봉인
2. 기존 `verify_trace()`와 코드를 공유하지 않는 두 번째 독립 trace parser
3. vapor 값뿐 아니라 위치·열 경계·격자 조건이 다른 강한 held-out spec
4. 새 제안서 v2 생성; v1은 삭제하지 않음

현재 코드 검색에서 `independent_trace_extraction`은 제안서 arm으로만 존재하며 별도 parser 구현은 없다. 후보별 held-out prediction 구현도 아직 없다. 결과를 본 뒤 설명을 맞추는 위험을 피하려면 지금 v1을 실행하지 않는 것이 맞다.

## 5. 구조적 기술 부채

- full trace와 GPU가 환경 커널의 private stage 함수에 결합됨
- `BoundaryEvaluation.complete_match=false`가 반박·미검사·예산 보류를 함께 표현함
- 같은 Windows 사용자 권한의 임의 B 코드는 ACL만으로 차단할 수 없음
- 현재 프로젝트가 Git 저장소가 아니므로 코드 버전 복구 기반이 약함

권장 보완:

- 공개 stage API
- `protocol_valid`, `scientific_status`, `coverage_status`, `execution_status` 분리
- 저권한 B process 또는 trace broker
- D:에 코드·문서·테스트 snapshot과 SHA-256 manifest

## 6. 보존 원칙

- legacy 확률 세계 `scheduler-v1`과 GCP 결과 유지
- 확률 결과와 결정론 결과 직접 합산 금지
- 실패·반박·deferred branch·미검사 후보 삭제 금지
- 사용자 전용 raw trace를 B에 자동 공개하지 않음
- 실제 삭제는 archive·SHA-256·시험 복원·사용자 승인 뒤에만 수행

## 7. 다음 권장 순서

1. 파일을 물리적으로 옮기기 전에 LLM용 논리 카탈로그 생성
2. 현재 코드·문서 snapshot 봉인
3. held-out 제안서 v2에 독립 parser와 후보별 예측 추가
4. 사용자 승인 뒤에만 새 held-out A 실행
5. 또는 B를 보류하고 결정론 화학·고분자로 이동
