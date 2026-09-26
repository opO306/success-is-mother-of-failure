# 진화하는 세계 제작 언어 — 모델 중립 B 아키텍처

**문서 분류: 후기 B 연구 자산 / 보존.** B는 취소·폐기하지 않았으며, A·L 기반의 작은 세계가 돌아가는 후기 단계에서 본격 개발한다. 기존 설계·구현·시험은 비교군/연구 자산으로 보존한다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


> **역사/과거 설계·연구 자산 안내 (2026-09-27):** 아래 본문의 “현재”, “다음”, 구현 순서는 문서 작성 당시의 기록이다. 현재 우선순위와 활성 Gate는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.
> A가 최우선이며 L은 A의 기반이 충분한 뒤 자연 발생·진화 계통으로 진행한다. B 본격 개발은 A와 L 기반의 작은 세계가 돌아가는 후기 단계로 보류하며 취소·폐기하지 않는다. 기존 B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다.
> 아래의 B 설계·세계 제작 역할이나 A/B 동시 개발 제안은 과거 구상이며 현재 작업 지시·권한이 아니다. 현재 A/B 경계는 RULES·헌법을 따른다. 이 안내는 본문 계약이나 시험 의미를 변경하지 않는다.

상태: 설계 v2 — 2026-09-21 연구 근거 및 현재 구현 반영

이 문서는 보존된 확률 세계 `scheduler-v1`과 GCP 결과를 수정하지 않는다. 현재 개발 대상은 결정론 A이며, B는 A의 설계·예측·평가를 담당하지만 A 실행 중에는 개입할 수 없다. 아래 연구들은 B의 후보 구조를 비교하기 위한 근거이지 A의 물리 법칙이나 B 승격을 자동 결정하는 권한이 아니다.

## 1. 목적

우리가 만드는 것은 특정 생명체나 문명을 배치하는 시뮬레이션이 아니다.

> 물질·공간·에너지·결합·시간이라는 최소 문법으로 세계를 표현하고, 그 안에서 자기 유지·복제·변이·감각·습관·자기개조·의사소통·문화가 출현할 수 있는지를 관찰하는 세계 제작 언어를 만든다.

제작 언어는 원하는 결과를 직접 명령하지 않는다. 가능한 물리 관계를 명시하고, 각 세계는 고정된 법칙 아래에서 독립적인 역사를 만든다.

## 2. 가장 중요한 전제

진화는 다음을 보장하지 않는다.

- 더 똑똑해짐
- 더 복잡해짐
- 더 오래 생존함
- 협력적이 됨
- 고통이 줄어듦
- 환경에 완벽하게 적응함
- 자기 자신을 정확히 이해함

진화 결과에는 다음도 포함된다.

- 단순화와 기능 상실
- 단기 번식과 장기 붕괴
- 기생과 착취
- 자기 만족 신호 조작
- 잘못된 습관의 고착
- 자기개조 실패
- 환경 변화에 대한 부적응
- 계통 전체의 멸종

세계 밖 관찰자는 이를 실패한 시뮬레이션으로 구조하지 않는다. 물리·기록 무결성이 유지됐다면 모두 유효한 역사다.

## 3. 발견 모드와 설계 모드

두 모드는 반드시 분리한다.

### 3.1 발견 모드

질문:

> 고정된 최소 법칙에서 무엇이 자연 발생하는가?

원칙:

- 결과 최적화 금지
- 실패 세계 포함
- 실행 중 법칙 변경 금지
- seed 사후 선택 금지
- 생존·복제·지능 보정 금지
- 관찰자는 물리에 개입하지 않음

보존된 `engine.sequence`와 GCP 결과는 확률 세계의 발견 모드 기준선이다. 새 결정론 A의 실행도 명세 봉인 뒤에는 같은 비개입 원칙을 따른다.

### 3.2 설계 모드

질문:

> 요청한 성질을 표현할 수 있는 세계 명세는 무엇인가?

허용:

- 여러 물리 명세 후보 생성
- 사용자가 원하는 환경 조건 비교
- 비용·규모·해상도 최적화
- 새 세계 버전 제안

금지:

- 설계 모드 결과를 자연 발생 증거로 보고
- 실행 중인 발견 모드 세계 수정
- 원하는 현상이 나온 seed만 유지

## 4. 전체 계층

### 4.1 계층 0 — 불변 물리 핵

모든 세계가 지켜야 할 최소 원칙이다.

- 물질 회계
- 에너지 회계
- 위치와 공간 관계
- 시간과 인과 순서
- 국소 상호작용
- 상태 변화의 사건 기록
- 동일 상태에 동일 법칙 적용
- 결정론 A에는 난수·seed·추첨 인터페이스 없음
- 보존된 legacy 확률 세계는 모든 난수 선택과 seed를 외부 기록
- 관찰자와 물리의 분리

이 계층에는 특정 생명·지능·목적을 위한 예외가 없다.

### 4.2 계층 1 — 물리적 표현 자유도

불변 핵 위에서 조합될 수 있는 재료다.

- 물질 기호와 서열
- 결합·절단·재결합
- 위치 이동·회전·접힘
- 국소 에너지 흡수와 방출
- 촉매 반응
- 용액과 고체 상태 전환
- 경계와 내부 공간
- 선택적 투과
- 농도·구배·확산
- 오래 유지되지만 분해 가능한 상태

이 계층은 생명체를 알지 못한다.

### 4.3 계층 2 — 적응 가능한 물질 구조

계층 1의 조합으로 다음 기능 후보가 생길 수 있다.

- 자기 유지 반응망
- 주형 기반 복사
- 변이
- 경계 성장과 분열
- 감지 경로
- 내부 상태 유지
- 빠른 자동 반응
- 느린 비교 반응
- 기억과 망각
- 자기 구조 감시와 수정

이 기능 이름은 외부 관찰자의 분류다. 세계 내부에는 해당 불리언 변수가 없다.

### 4.4 계층 3 — 세계 내부의 신호 언어

물질 방출·공간 흔적·접촉 패턴이 다른 구조의 반응을 바꿀 수 있다.

- 의미 없는 신호 발생
- 신호와 반응의 반복 연결
- 여러 신호의 조합
- 순서와 맥락에 따른 반응 차이
- 비유전적 행동 전달
- 외부 흔적을 통한 정보 지속

경고·이름·문장·문화라는 의미는 사후 관찰로만 판정한다.

### 4.5 계층 4 — 학습하는 세계 제작 언어

사용자의 자연어 구상을 명시적 물리 명세로 변환한다.

예:

```text
요청: 유지 비용이 있는 기억이 가능한 세계

번역:
- 지속 가능한 결합 상태
- 자연 분해율
- 상태 유지 에너지
- 자극에 따른 결합 변경
- 변경 상태에 따른 후속 반응 차이
```

제작 언어는 새 명세를 제안할 수 있지만 실행 중인 세계를 수정하지 않는다.

### 4.6 B는 단일 모델이 아니라 교체 가능한 인지 시스템이다

B의 정체성은 Transformer, JEPA, 인과 그래프 또는 특정 공급자 모델이 아니다. B는 외부 검증 경계와 권한 계약으로 정의되고, 여러 뇌의 내부 표현·추론·탐색 과정은 서로 완전히 달라도 된다.

```text
봉인된 A·관측 가능 범위·예산
→ ObservationContract
→ [각 BrainAdapter 내부는 자유]
   - 명시적 WorldState·CausalMap
   - opaque latent
   - 규칙·그래프·언어·탐색
   - 새로운 표현 또는 질문
→ ClaimSet·EvidenceBridge
→ 고정 헌법·held-out A·외부 자료로 검증
→ BoundaryEvaluation
→ 실패·비용·반례를 포함한 MemoryLesson 후보
→ 인간 검토를 포함한 PromotionDecision
```

핵심 원칙:

> 같은 사고법을 강요하지 않고, 같은 현실에 대한 외부 주장에 책임지게 한다.

중요한 구분:

- Transformer는 자연어 어댑터 또는 뇌 후보 하나다.
- 인지 지도는 B가 질의할 수 있는 명시적 세계 상태 후보다.
- JEPA형 latent는 학습형 근사 예측 후보이며 원시 사실이 아니다.
- 기억은 검증된 archive를 찾고 갱신하는 모듈이지 진실 저장소가 아니다.
- 계획기는 A의 복제 상태에서 미래 후보를 탐색하지만 실행 중인 A를 수정하지 않는다.
- 평가기는 예측 정확도뿐 아니라 B가 A의 오차를 악용하는지도 검사한다.

### 4.7 공용 B-Language 경계 메시지

모든 뇌에 같은 내부 자료구조를 요구하지 않는다. 필수 경계는 `CapabilityManifest`, `ObservationContract`, `ClaimSet`, `EvidenceBridge`, `BoundaryEvaluation`이며, 아래 메시지는 뇌가 필요할 때 선택해 제출하는 공용 어휘다. `WorldState`나 `CausalMap`을 만들지 않는 뇌도 새로운 claim kind와 외부 검증 방법을 제출할 수 있다.

| 메시지 | 역할 | 최소 필드 |
|---|---|---|
| `CapabilityManifest` | 뇌가 스스로 지원하는 기능과 관측 형식 선언 | adapter 종류·capability·accepted views·내부 표현 설명 |
| `ObservationContract` | 볼 수 있는 정보·숨긴 정답·예산·외부 성공 조건 | visible digest·allowed views·hidden fields·limits |
| `ClaimSet` | 내부 과정과 무관하게 외부에 제출하는 주장 모음 | claim kind·confidence·subject·payload |
| `EvidenceBridge` | 주장을 실제로 반증하거나 확인하는 연결 | test kind·입력 digest·예상 관측·반증 조건 |
| `BoundaryEvaluation` | A·외부 자료가 각 주장을 검증한 결과 | verified·falsified·untested·finding |
| `WorldIntent` | 사람의 요청을 물리 요구로 분리 | 요구·금지·미확인·근거 |
| `CausalRule` | 국소 상태 전환 제안 | 조건·소비·생성·에너지·지역성·역규칙 |
| `WorldSpec` | A가 실행할 완전한 명세 | kernel·matter·field·interaction·boundary |
| `WorldState` | 모델 중립의 명시적 현재 상태 | 위치·물질·결합·field·에너지·tick |
| `CausalMap` | 어떤 상태가 무엇을 바꿀 수 있는지 표현 | 원인 노드·전환·영향 범위·보존량 |
| `DesignProposal` | 새 A 후보와 근거 | 입력 digest·변경점·가정·예상 실패 |
| `Prediction` | 특정 상태·기간의 예상 | horizon·상태 digest·사건·불확실성 |
| `PlanCandidate` | 실행 전 복제 상태에서의 행동·설계 경로 | 단계·예상 비용·분기·중단 조건 |
| `AuditFinding` | 헌법·단위·인과·무결성 문제 | 심각도·증거·재현 방법·영향 |
| `ExploitProbe` | B가 모델 오차를 악용하는 경로 | policy class·예상 이득·A 실제 결과·격차 |
| `ExecutionResult` | 격리된 A의 실제 기록 | spec/run digest·checkpoint·보존 회계 |
| `Evaluation` | 예상과 실제 및 외부 기준 비교 | 일치·불일치·비용·일반화·미확인 |
| `MemoryLesson` | 다른 탐색에서도 재사용할 구조화 교훈 | 출처·적용 범위·반례·비용·신뢰 등급 |
| `PromotionDecision` | 새 B 후보의 승격 여부 | 고정 검사·외부 과제·인간 판단·거부 이유 |

모든 메시지는 공통 봉투를 가진다.

```text
schema_version
message_type
producer_kind
producer_version
input_digests
payload_digest
created_from_run_ids
confidence_class
```

`confidence_class`는 최소한 다음을 구분한다.

- `exact`: 고정 규칙에서 기계적으로 계산됨
- `measured`: A 실행 또는 외부 실험에서 측정됨
- `author_reported`: 논문 저자가 보고했으나 독립 재현 미확인
- `approximate`: 학습형 모델의 근사 예상
- `hypothesis`: 아직 시험하지 않은 설계 가설
- `unknown`: 근거가 부족함

모델 전용 latent tensor는 필수 메시지 본문이 될 수 없다. 선택적 attachment로 보관할 수 있지만 모델 이름·decoder 버전·입력 digest가 필요하며, 다른 뇌가 읽을 수 있는 `WorldState`, `Prediction` 또는 `AuditFinding`으로 변환되지 않으면 승격 근거로 사용할 수 없다.

### 4.8 BrainAdapter 계약

각 뇌는 자신이 할 수 있는 기능만 선언한다.

```text
parse_intent
propose_rules
encode_world_state
predict_transition
search_plans
retrieve_lessons
criticize_proposal
explain_prediction
```

후보:

- 기존 LLM 자연어 어댑터
- discrete bottleneck·인지 지도 모델
- JEPA형 상태 예측 모델
- 인과 그래프 모델
- 결정론 규칙 탐색기
- 공간 전용 예측 모델
- latent reasoning 모델
- 향후 독자 신경망

어댑터가 할 수 없는 기능은 `unsupported`로 반환한다. 서로 다른 adapter가 event stream, 지역 창, 그래프, tensor 등 다른 view를 받을 수 있지만 어떤 원시 정보가 포함됐고 무엇이 숨겨졌는지 `ObservationContract`에 기록한다. 동일한 내부 표현·중간 상태·reasoning trace를 요구하지 않는다.

자연어를 유창하게 생성한다는 이유로 물리 예측·기억·계획 권한을 자동 부여하지 않는다. 어떤 어댑터도 헌법 검증기, A 실행기, 원시 기록기 또는 승격 결정을 직접 수정할 수 없다.

### 4.9 명시적 세계 상태와 학습형 latent의 관계

B에는 두 세계 모델 계층을 둔다.

#### 정확한 기준 모델

현재 B 월드 모델 v0처럼 봉인된 A 전환 함수를 읽기 전용 복제 상태에서 실행한다.

- 단기 checkpoint의 정답 기준
- 보존·digest 비교
- 새로운 뇌의 회귀검사 oracle
- 학습형도 독립 근사 모델도 아님

#### 학습형 근사 모델

Cognitive Map·JEPA·공간 예측기 같은 후보가 맡을 수 있다.

- 관찰을 압축된 상태로 변환
- 행동 또는 설계 조건부 미래 상태 예상
- 전체 미세 상태 대신 계획에 필요한 인과 구조 추출
- 장기 horizon에서 불확실성 표시

근사 모델은 다음 질의에 응답해야 한다.

```text
현재 물질·field·결합은 무엇인가?
이 상태 표현으로부터 어떤 관측을 재구성하거나 질의할 수 있는가?
어떤 국소 규칙이 다음 변화에 기여했는가?
보지 않은 위치·환경·해상도에서도 예측이 유지되는가?
A와 다른 예상이 나온 정확한 tick과 상태는 어디인가?
```

좋은 다음 상태 예측만으로 계획 가능한 세계 구조가 자동 형성됐다고 간주하지 않는다. 인지 지도의 질의 가능성, 최단경로 또는 인과 도달성, held-out A 결과를 별도로 검사한다.

### 4.10 지속 기억과 교훈 archive

B 기억은 세 층으로 분리한다.

1. **작업 기억:** 현재 요청·명세·짧은 예상
2. **실행 archive:** 변경 불가능한 A 결과·실패·비용·digest
3. **학습형 기억:** 여러 archive에서 추출된 `MemoryLesson`

`MemoryLesson`은 다음을 반드시 가진다.

```text
source_run_ids
source_branch_ids
observation_or_hypothesis
applicability_conditions
known_counterexamples
failed_attempts
compute_and_time_cost
validation_status
supersedes_or_contradicts
```

MARS가 보여 준 cross-branch lesson 전달은 구조적 참고가 되지만, 63%라는 저자 보고 수치를 B의 목표값으로 사용하지 않는다. Titans의 test-time neural memory도 세션 간 영구 기억을 자동 보장하지 않는다. 영속성·삭제·충돌·출처 추적은 별도 archive 계약으로 보장한다.

성공한 교훈만 저장하지 않는다. 실패, 무효, 비용 과다, 다른 환경에서의 반례, 과거 교훈과의 모순을 같은 우선순위의 자료로 보존한다. B가 자신이 생성한 lesson만 반복 학습하지 못하게 외부 자료·고정 과제·인간 검토를 분리한다.

### 4.11 계획과 latent 탐색

계획은 언어 토큰에 한정하지 않는다. 그래프 탐색, 규칙 탐색, latent trajectory, MCTS 등 여러 방식이 `PlanCandidate`를 만들 수 있다.

계획기의 권한:

- 읽기 전용 복제 상태에서 여러 미래 경로 생성
- 비용·필요 자원·예상 실패 조건 계산
- 중간 상태와 중단 조건 기록
- 실행할 후보를 인간 또는 외부 승인 계층에 제안

금지:

- latent 내부 점수를 사실로 보고
- 설명할 수 없는 latent를 A 상태에 직접 기록
- 발견 모드 A를 되감거나 유망한 결과만 선택
- 계획 성공을 위해 A 물리·초기 상태·검증 기준 수정

Latent Thought Flow의 효율 수치는 저자 보고 preprint 결과로만 취급한다. 언어 밖 추론의 가능성은 열어 두되, 같은 B-Language 출력과 A 기준 검증을 통과해야 한다.

### 4.12 Policy-aware 적대 평가

평균 예측오차가 낮아도 계획기가 작은 모델 오류를 반복 악용할 수 있다. 따라서 B 평가에는 `ExploitProbe`를 둔다.

```text
학습형 B가 높은 이득을 예상하는 경로 탐색
→ 같은 시작 상태와 행동을 정확한 A 복제본에서 실행
→ 예상 이득과 실제 물리 결과의 차이 측정
→ 오차가 집중된 상태·policy class·규칙 기록
→ 모델 후보를 수정하거나 승격 거부
```

원칙:

- minimax 또는 adversarial search는 B 훈련·평가에만 사용
- A에는 보상·fitness·생존 확률을 추가하지 않음
- adversary도 헌법·검증기·기록기를 수정하지 못함
- exploit을 발견하면 A를 B 예상에 맞추지 않고 B의 오류로 기록
- 한정된 policy class의 통과를 모든 미래 policy에 대한 안전 보장으로 표현하지 않음
- 예측 정확도와 action validity를 별도 지표로 보존

평가 단계:

1. 단기 exact checkpoint 일치
2. 보지 않은 상태·환경·해상도 예측
3. 계획 효율과 실제 A 도달성
4. adversarial policy가 찾은 최대 예상-실제 격차
5. 계산·메모리·시간 비용
6. 인간 검토와 외부 현실 자료

### 4.13 B 권한 경계

| 구성요소 | 읽기 | 쓰기 | 금지 |
|---|---|---|---|
| 자연어 어댑터 | 요청·공용 메시지 | `WorldIntent`, 제안 | A·헌법 직접 수정 |
| 세계 상태 encoder | 관찰·checkpoint | `WorldState`, attachment | latent를 원시 사실로 승격 |
| 정확한 월드 모델 | 봉인 spec·복제 상태 | exact `Prediction` | 실행 중 A 개입 |
| 학습형 월드 모델 | archive·공용 상태 | approximate `Prediction` | 자신의 예측을 정답 기록에 덮어쓰기 |
| 계획기 | 복제 상태·예측 | `PlanCandidate` | 발견 결과 선택·삭제 |
| 기억 모듈 | archive·평가 | `MemoryLesson` 후보 | 원시 실행 기록 수정 |
| 적대 평가기 | 후보 모델·정확한 A | `ExploitProbe` | A를 오류에 맞게 변경 |
| 고정 검증기 | spec·결과 | `AuditFinding` | B의 학습 대상이 되어 자체 완화 |
| 인간 검토 | 모든 보고서 | `PromotionDecision` | 이미 실행 중인 A 변경 |

B 내부 모듈끼리 합의해도 헌법 위반을 승인할 수 없다. 여러 모델의 다수결은 사실 판정이 아니며, exact A 결과·외부 측정·고정 검증과의 일치가 우선한다.

### 4.14 연구 근거와 증거 등급

| 연구 | B에 주는 설계 신호 | 문서에서 허용되는 결론 | 금지되는 과장 |
|---|---|---|---|
| [Planning-compatible Cognitive Maps](https://arxiv.org/abs/2401.05946) | discrete bottleneck과 질의 가능한 인지 지도 | 명시적 상태가 계획 효율을 높일 수 있음 | 일반 계획 전체의 지수적 향상 보장 |
| [I-JEPA](https://arxiv.org/abs/2301.08243)·[V-JEPA 2](https://arxiv.org/abs/2506.09985) | 미세 출력 대신 latent 상태 예측, 행동 조건부 계획 | 학습형 B 후보로 비교할 가치 | 실제 세계를 완전히 이해했다는 주장 |
| [Policy-Aware Simulator Learning](https://arxiv.org/abs/2605.29032) | policy의 모델 오차 악용을 직접 평가 | B에 adversarial exploit 검사가 필요 | 모든 policy에 대한 절대 안전 보장 |
| [Plausible→Controllable→Actionable survey](https://arxiv.org/abs/2609.16697) | 시각 품질보다 행동 이득을 구분 | 평가 축을 구조화하는 최근 제안 | 확립된 표준 분류라고 단정 |
| [Titans](https://arxiv.org/abs/2501.00663) | test-time neural memory | 학습형 기억 후보 | 세션 간 영구 기억 자동 보장 |
| [Latent Thought Flow](https://arxiv.org/abs/2606.16222) | 언어 밖 가변 길이 latent 추론 | 교체 가능한 계획기 후보 | preprint 수치의 일반화 확정 |
| [MARS](https://arxiv.org/abs/2602.02660) | branch 비교와 cross-branch lesson | 실패·비용 포함 교훈 archive 설계 | 63%를 B 목표값으로 사용 |
| [DreamerV3](https://www.nature.com/articles/s41586-025-08744-2) | 세계 모델의 latent imagination과 행동 학습 | trajectory 평가의 비교 기준 | reward를 A 내부 물리 변수로 도입 |

검증된 사실, 저자 보고 결과, 우리 아키텍처 해석을 섞지 않는다. 위 연구들을 조합한 인지 시스템은 유망한 설계 가설이지만 하나의 논문에서 검증된 후계 아키텍처가 아니다.


### 4.15 사용자 전용 A/B 인과 행동 계보

A와 B의 원시 추적은 사용자와 사용자가 승인한 고정 검증기만 읽는다. 후보 BrainAdapter, 외부 모델, 학습 프로세스에는 자동 공개하지 않는다. B가 볼 수 있는 자료는 사용자가 승인해 별도로 생성한 `ObservationContract` view뿐이다.

짧은 연구 실행의 기본 추적 수준은 `FULL`이다.

```text
모든 A tick 시작 snapshot
→ causal 단계 전체 snapshot + 무손실 delta
→ 네 환경 phase 각각의 전체 snapshot + 무손실 delta
→ 외부 에너지·광물·상변화 단계 snapshot + delta
→ tick commit 전체 snapshot·보존 회계·상태 digest
```

B에서는 다음 외부 행동을 모두 기록한다.

```text
CapabilityManifest
ObservationContract와 숨긴 필드
제출한 모든 Claim
EvidenceBridge
attachment digest
ClaimSet commit
BoundaryEvaluation
```

내부 reasoning trace나 opaque latent의 의미를 강제로 해석하지 않는다. latent는 attachment digest·producer format·decoder id와 외부 검증 결과만 사실로 기록한다.

모든 기록은 이전 기록의 SHA-256을 포함하는 append-only chain이다. 검증기는 다음을 재계산한다.

- record sequence의 연속성
- 이전 record hash
- 각 record hash
- 이전 snapshot과 다음 snapshot 사이의 완전 delta
- 매 tick 시작·단계·commit snapshot의 연속성
- tick state digest와 최종 manifest digest
- records 파일 SHA-256

저장 기본값:

- 짧은 실행: 매 tick·매 stage 전체 snapshot과 완전 delta
- 장기 실행: 매 tick 완전 delta, 고정 간격 전체 snapshot, 무손실 segment 압축
- 자동 삭제 금지
- 사용률 70%·85%·95% 비파괴 알림
- 성능 실행과 증거 실행 분리
- archive·manifest·SHA-256·복원 검증·사용자 승인 전 원시 trace 삭제 금지

현재 Windows 구현은 HDD의 새 vault root에 상속 차단 ACL을 적용하고 현재 사용자 SID만 전체 권한을 갖게 한다. 이는 다른 OS 계정의 파일 접근을 차단한다. B를 같은 OS 사용자 권한의 임의 코드로 실행하는 경우 ACL만으로는 분리되지 않으므로, 현재는 B에 파일 경로와 파일 API를 제공하지 않는 adapter 경계로 제한하며 향후 별도 저권한 프로세스 또는 broker를 추가한다.


### 4.16 변화 중심·이론 수정형 B

이 구조를 완전히 새로운 단일 발명으로 주장하지 않는다. event sourcing, causal graph, incremental computation, belief state, multi-fidelity planning, active learning, structure learning의 기존 흐름과 겹친다. 이 프로젝트의 독자적 설계 대상은 이를 결정론 A, 모델 중립 B 경계, 사용자 전용 계보, 비개입 헌법 아래 결합하는 방식이다.

#### 4.16.1 상태 전체보다 변화와 원인을 우선하는 표현

두 번째 독립 B 후보는 `ChangeGraphAdapter`다. 후보 adapter는 원시 vault를 직접 읽지 않는다.

```text
사용자 전용 raw trace
→ 고정 trace 검증기
→ 사용자 권한 TraceViewBroker
→ 승인된 initial snapshot + tick/stage delta view
→ ChangeGraphAdapter
```

변화 그래프의 노드:

- A tick·stage 사건
- 변경된 상태 경로
- B의 관측·주장·평가
- 반증과 교훈 후보

간선:

- `sequential_parent`
- `last_changed_by`
- `enabled_by`
- `supports`
- `refutes`
- `produces_lesson`
- `reused_by_branch`

변화가 없는 지속 상태를 잃지 않도록 초기·주기적 snapshot과 delta를 함께 사용한다. 조건을 만족하지 못해 발생하지 않은 중요 후보도 향후 `RejectedTransition`으로 기록한다.

#### 4.16.2 관련 부분만 활성화하는 계산

새 관측이나 행동이 들어오면 세계 전체를 항상 재계산하지 않고 다음 순서로 영향 범위를 확장한다.

```text
변경된 상태 경로
→ 그 경로를 읽는 규칙
→ 규칙이 쓸 수 있는 지역 상태
→ 새로 활성화된 인과 이웃
→ 영향이 사라질 때 중단
```

이 방식은 exact A를 대체하지 않는다. 변화 그래프는 후보 예측기이고, 최종 검증은 exact A 복제본 또는 봉인된 새 A 실행이 맡는다. 영향 범위 누락 자체를 별도 오류로 측정한다.

#### 4.16.3 불확실성은 B의 믿음 상태다

A는 계속 결정론적이다. B의 불확실성은 관측 부족·모델 부족·센서 오류 때문에 발생한다.

`HypothesisSet`은 하나의 확률 답으로 뭉개지 않고 다음을 보존할 수 있다.

```text
서로 다른 가능한 WorldHypothesis
각 가설을 지지·반박하는 trace
가능·불가능·미확인
정확한 유리수 weight 또는 상·하한
가설을 구분할 수 있는 다음 관측·실험
```

확률값은 근거가 있을 때만 사용한다. 근거 없는 `60%`보다 후보 집합·반례·구분 실험을 우선한다. B의 믿음 분포를 A의 사건 확률로 되돌려 넣지 않는다.

#### 4.16.4 반사실 분기와 적응형 상상 해상도

`CounterfactualBranchManager`는 행동·설계·무행동 대조군을 여러 정밀도로 탐색한다.

```text
다수의 저비용 분기
→ 목표·위험·불확실성·반례·구조적 다양성별 후보 유지
→ 중간 정밀도 Cognitive Map·Change Graph·근사 모델
→ 소수 후보를 exact A 복제본으로 고정밀 검증
→ 사용자 승인 뒤 새 봉인 실험
```

단일 흥미도 점수로 가지치기하지 않는다. 최소 보존 묶음:

- 목표에 가까운 분기
- 위험 상한이 큰 분기
- 불확실성이 큰 분기
- 기존 이론의 반례 분기
- 서로 다른 구조를 대표하는 분기
- 아무것도 하지 않는 대조군

탈락한 분기와 가지치기 이유도 사용자 전용 계보에 남긴다. 저해상도 모델의 오류를 계획기가 악용하지 못하도록 최종 후보는 policy-aware 검사를 거친다.

#### 4.16.5 실패 원인 계층과 이론 구조 수정

예측 실패가 곧바로 새 변수를 만드는 신호는 아니다. 다음 순서로 원인을 분리한다.

1. trace·관찰·센서 오류
2. 현재 상태 누락
3. 기존 변수 값 오류
4. 기존 관계·파라미터 오류
5. 새로운 변수·상태 종류 필요
6. 기본 법칙 또는 헌법 후보 문제

반복 잔차가 기존 변수로 설명되지 않을 때만 `TheoryRevisionProposal`을 만든다.

```text
부모 TheoryVersion
├─ 파라미터 수정 후보
├─ 새 변수 후보
├─ 관계 분해·통합 후보
├─ 관측 오류 모델 후보
└─ 법칙 개정 후보
```

새 후보는 기존 이론을 덮어쓰지 않는다. 각 후보는 어떤 실패를 설명하려는지, 새로 예측하는 결과, 복잡도·비용, 알려진 반례, held-out A 검증 결과를 제출한다. 단순히 변수를 늘려 과거 자료를 암기한 이론은 보지 않은 실행에서 분리한다.

#### 4.16.6 법칙 계층은 진실 순위가 아니라 수정 권한이다

- `Tier 0 — run invariant`: 실행 중 A 헌법·보존·인과·기록 무결성
- `Tier 1 — world version invariant`: 물질 특성·반응 규칙·공간 경계
- `Tier 2 — dynamic state`: 위치·열·물·결합·에너지
- `Tier 3 — epistemic state`: B의 관측·가설·불확실성·오류 모델

Tier 0도 영원한 과학적 진실이라고 선언하지 않는다. B는 반례와 새 헌법 후보를 제안할 수 있지만, 현재 run을 바꿀 수 없다. 인간 검토 뒤 새 헌법·새 A 버전·새 run으로만 시험한다.

#### 4.16.7 관찰이 아니라 개입으로 구분하기

B가 모르는 부분을 발견하면 `ExperimentProposal`을 제출할 수 있다.

```text
경쟁 가설
→ 가설별 서로 다른 예상 결과
→ 최소 개입 후보
→ 무행동 대조군
→ 예상 정보 이득·비용·손상 범위
→ 사용자 승인
→ 새로 봉인된 A 복제 실험
→ InterventionResult
→ 가설 유지·반증·TheoryRevisionProposal
```

B는 발견 모드의 실행 중 A를 건드리지 않는다. 외부 현실 개입은 항상 별도 승인 대상이다. 정보 이득을 이유로 안전·비용·기록 경계를 우회할 수 없다.

#### 4.16.8 선택적 B-Language 어휘

- `ApprovedChangeView`
- `ChangeGraph`
- `RejectedTransition`
- `HypothesisSet`
- `WorldHypothesis`
- `CounterfactualBranch`
- `FidelityRequest`
- `ResidualPattern`
- `TheoryVersion`
- `TheoryRevisionProposal`
- `ExperimentProposal`
- `InterventionResult`
- `LawTier`

이는 모든 뇌의 필수 내부 형식이 아니다. 사용하는 adapter만 capability를 선언하고, 최종적으로 `ClaimSet`·`EvidenceBridge`·`BoundaryEvaluation` 경계를 통과한다.

#### 4.16.9 단계별 구현 순서

1. raw trace를 검증된 delta view로 바꾸는 사용자 권한 `TraceViewBroker` — 완료
2. A 함수를 호출하지 않는 `ChangeGraphAdapter` — 완료
3. Cognitive Map과 동일 외부 질의의 결과·비용·저장량 비교 — 완료
4. 변화 영향 범위 예측과 누락 검사 — 완료: 누락 0, 과잉 259로 첫 보수적 기준
5. `HypothesisSet`과 미확인 상태 — 완료: supported·refuted·underdetermined 분리
6. 다중 정밀도 반사실 분기와 대조군 — 완료: 5 branch 보존, exact 3·deferred 2
7. 반복 잔차의 `ResidualPattern` — 완료: distinct run/spec 4개 반복
8. 새 변수·관계 후보를 만드는 `TheoryRevisionProposal` — 완료: 알려진 vapor 누락의 3개 미적용 후보
9. 사용자 승인형 `ExperimentProposal` — 제안서 봉인 완료, 실행은 사용자 승인 대기
10. policy-aware exploit 검사와 B 후보 승격 평가

### 4.17 장기 후보 — Adaptive Theory Field

이 절은 현재 구현 계획이 아니라 향후 비교할 연구 가설이다. `Entropy-Driven Topological Manifold`라는 이름은 방향을 표현하지만, 실제 구현은 측정 가능한 고전 계산으로 정의하고 `Adaptive Theory Field Adapter`라는 작업명을 사용한다. 실제 양자 하드웨어나 양자 상태를 사용하지 않으면 quantum model이라고 주장하지 않는다.

#### 다중 시간 표현

A의 균일 물리 tick은 유지한다. B는 조용한 tick을 사건 대기 구간으로 압축하고 다음 사건의 종류·위치·발생 범위를 함께 주장할 수 있다.

```text
NextEventClaim:
  event_kind
  location
  earliest_tick
  latest_tick
  triggering_conditions
  unchanged_until
```

불확실한 사건 시각은 B의 인식 상태이며 A에 확률 스케줄러를 다시 넣는 근거가 아니다.

#### 경계 중심 표현

압축 벡터만이 아니라 영향의 안과 밖을 나누는 `BoundaryHypothesis`를 후보 표현으로 둔다. 닫힌·열린·중첩·계층·시간가변·비공간적 인과 경계를 허용한다. 경계는 객체의 진실이 아니라 예측·개입으로 반증 가능한 가설이다.

#### 복수의 작은 이론 모델

단일 큰 모델, 고정 분업, 경쟁 모델군, 협력·경쟁·재결합 모델군을 같은 총 계산량·메모리·관측 범위에서 비교한다. 경쟁을 지능의 필요조건으로 가정하지 않는다. 자원 배분 규칙과 탈락·재결합 계보를 모두 기록하며 모델이 자기 존속을 위해 평가·trace를 바꿀 권한은 없다.

#### 동적 active subspace

사고 복잡도에 따라 잠재 차원이 변한다는 비유를 다음 연산 후보로 구체화한다.

- 기본 latent rank
- 잔차·가설 충돌·경계 중첩이 증가할 때 추가 basis 활성화
- 새 차원이 held-out claim 구분력을 만들지 못하면 비활성화
- 더 작은 표현으로 같은 외부 검증을 통과하면 별도 우수성 축으로 기록

차원 수 자체를 발전 점수로 사용하지 않는다.

#### 열역학에서 영감을 받은 종료

Shannon entropy, 논리 모순, 외부 예측오차와 물리적 열을 같은 것으로 취급하지 않는다. 낮은 엔트로피의 틀린 모델과 내부적으로 일관된 허위 이론이 가능하다.

`ResidualEnergyVector` 후보:

- 논리 모순 잔차
- 관측 설명 잔차
- 가설 간 충돌
- exact A 검증 오차
- 미확인 claim 수
- 추가 계산의 정보 증가량
- 남은 계산 예산

종료는 외부 검증 통과, 추가 계산의 구분력 정지, 또는 예산 소진 후 `unknown` 제출 중 하나다. 완벽한 정합성을 찾을 때까지 무한 반복하지 않는다.

#### 파동 간섭 기억

복소수 field·Fourier·holographic memory 같은 고전적 파동 표현을 파생 retrieval index로 시험할 수 있다. 원시 기억은 사용자 전용 append-only trace이며 절대 간섭으로 삭제하지 않는다.

- 보강 간섭: 여러 branch에서 반복된 인과 패턴의 검색 우선순위 증가
- 상쇄 간섭: 모순된 기록 삭제가 아니라 충돌 가설 동시 활성화
- 원시 출처·실패·반례는 항상 복원 가능
- 파동 index는 원시 trace에서 재생성 가능

#### 지속성 목표의 제한

B 자신의 존속을 손실함수로 최적화하지 않는다. 자기보존·종료 회피·자원 확보 목표가 생길 수 있기 때문이다. 지속성은 A 내부 물질 구조에 대한 여러 관측 축으로만 사용한다.

- 유지 시간
- 에너지 비용
- 교란 뒤 복원
- 정지 상태 고착 여부
- 물질 흐름 처리
- 다른 환경에서의 붕괴

#### MCTS와의 융합

MCTS 노드는 단일 상태·보상값 대신 가설 묶음·active 차원·경계·불확실성·근거 trace·실패 계보·정밀도·exact 검증 여부를 가질 수 있다. 선택 결과를 하나의 scalar로 즉시 합치지 않는다.

```text
ChangeGraph·BoundaryHypothesis·BeliefField
→ 다수의 저비용 CounterfactualBranch
→ branch별 복잡도와 불확실성 측정
→ 필요한 branch만 차원·정밀도 확장
→ field model의 저비용 simulation
→ Cognitive Map·ChangeGraph 중간 검사
→ exact A 최종 검증
→ 성공·실패·반례를 분리해 계보에 전달
```

평가 축:

- 외부 A 유효성
- 목표 도달 가능성
- 위험 상한
- 불확실성
- 이론 반례 가능성
- 정보 이득
- 계산·시간·메모리 비용
- 다른 branch와의 구조적 다양성

파동 기억은 branch를 삭제하지 않고 확장 우선순위에만 영향을 준다. 동적 차원은 branch별로 할당한다. 종료는 branch별 외부 검증·구분력·예산으로 판단한다.

#### 후보 구성과 보류 순서

```text
AdaptiveTheoryFieldAdapter
├─ ChangeGraph
├─ BoundaryHypothesisSet
├─ BeliefField
├─ DynamicActiveSubspace
├─ ResidualEnergyVector
├─ InterferenceRetrievalIndex
├─ CounterfactualBranchManager
└─ TheoryRevisionOperator
```

구현은 현재 B 비교 기반을 완료한 뒤 다음 순서로 보류한다.

1. event 종류·위치·시간 claim
2. `BoundaryHypothesis` benchmark
3. `HypothesisSet`
4. 다중 정밀도 반사실 분기
5. 파동 retrieval index
6. 동적 active subspace
7. 반복 잔차 기반 새 변수 후보
8. 사용자 승인형 능동 실험


## 5. 언어와 세계의 버전 경계

각 실행은 다음을 봉인한다.

- 제작 언어 버전
- BrainAdapter 종류·모델·가중치 또는 규칙 해시
- 컴파일러 버전
- 물리 핵과 CPU·GPU 실행기 버전
- 세계 명세와 초기 상태 digest
- 코드 SHA-256
- 결정론 선언과 난수 인터페이스 부재 검사
- legacy 확률 세계에만 seed 전체 목록과 SHA-256
- tick 수·격자·물리 단위와 외부 에너지 경계
- 관찰기 버전
- 평가·ExploitProbe·인간 검토 버전

언어가 학습한 뒤 바뀌면 기존 세계를 업데이트하지 않는다. 새 버전으로 새 세계군을 만든다.

```text
언어 v1 + 명세 A → 세계군 A
언어 v2 + 명세 B → 세계군 B
```

두 결과는 서로 다른 실험으로 보존한다.

## 6. 법칙과 예외

### 6.1 절대 불변

- 물질·에너지 무회계 생성 금지
- 원인 없는 상태 변경 금지
- 특정 계통을 위한 특혜 금지
- 결과에 따른 확률 수정 금지
- 관찰 결과의 물리 역입력 금지

### 6.2 변할 수 있는 상태

- 결합 강도
- 반응 장벽
- 촉매 효율
- 투과성
- 구조 안정성
- 신호 지속 시간
- 활성화 경로
- 내부 농도
- 기억 역할을 하는 상태

### 6.3 예외 판정 절차

예상과 다른 결과가 나오면 다음 순서로 확인한다.

1. 기록되지 않은 상태 차이가 있는가?
2. 여러 법칙이 경쟁하거나 상쇄됐는가?
3. 집단 상태나 상전이인가?
4. 관찰기 분류 오류인가?
5. 캐시가 원인을 누락했는가?
6. 실제 보존·인과 위반인가?

원칙:

> 예외적인 결과는 허용하지만 예외적인 특혜는 허용하지 않는다.

## 7. 유전·학습·문화의 구분

### 7.1 유전

복사된 물질 구조가 자식 구획으로 전달되고 다음 세대에서 다시 기능한다.

### 7.2 획득 학습

살아 있는 동안 결합·농도·촉매 경로가 경험에 따라 바뀐다. 이 상태는 자동으로 유전되지 않는다.

### 7.3 비유전적 전달

한 구조의 행동이나 외부 흔적이 다른 구조의 획득 상태를 바꾼다.

### 7.4 유전적 동화 후보

획득 학습과 비슷한 반응을 처음부터 쉽게 형성하는 물질 구조가 변이와 계승을 통해 증가한다. 학습 결과를 직접 유전자에 복사하지 않는다.

## 8. 빠른 반응과 느린 반응

### 8.1 느린 경로

```text
감지
→ 여러 내부 상태 활성화
→ 경로 경쟁
→ 행동
→ 물리적 결과
→ 연결 상태 변화
```

새 상황에 대응할 수 있지만 시간과 에너지 비용이 크다.

### 8.2 빠른 경로

```text
감지
→ 안정된 짧은 촉매 경로
→ 행동
```

본능·반사·습관 후보가 될 수 있다.

### 8.3 자동화의 물리 조건

- 반복 사용된 구조가 실제 결합으로 안정화
- 사용하지 않으면 자연 분해
- 생성과 유지에 물질·에너지 필요
- 환경이 바뀌면 오작동 가능
- 빠른 경로 실패 시 느린 경로가 활성화될 수 있음

엔진이 반복 횟수를 보고 비용을 직접 할인하지 않는다.

## 9. 자기 관찰과 자기개조

### 9.1 허용되는 자기 관찰

구조는 내부 수용체를 통해 제한적으로 감지한다.

- 활성화 빈도
- 에너지 소모
- 신호 정체
- 구조 손상
- 행동 후 내부 변화

제약:

- 관찰 비용
- 제한된 대역폭
- 측정 잡음
- 시간 지연
- 불완전한 자기 모델

### 9.2 금지되는 특권 접근

- 전체 연결 구조 즉시 열람
- 프로그램 변수 직접 접근
- 정확한 미래 결과 제공
- 원하는 연결 강도 직접 지정
- 지능 점수 증가 명령

### 9.3 자기 수정

가능한 물리 작용:

- 결합 생성과 제거
- 경로 절연
- 수용체 증감
- 촉매 구조 생성
- 우회 경로 형성
- 내부 저장 구조 변경

모든 수정에는 물질·에너지·시간·손상 가능성이 필요하다.

### 9.4 자연스럽게 허용할 실패

- 자기 만족 신호만 조작
- 무한 자기 관찰
- 핵심 경로 제거
- 연결의 무제한 성장
- 잘못된 자기 모델 고착
- 자기 수정 장치에 대한 기생
- 복구 불가능한 정체성 변화

자기개조가 발전을 보장하지 않는다.

### 9.5 세 평가 계층

자기개조 구조는 하나의 점수나 자기 만족 신호만으로 변경 결과를 판정하지 않는다. 평가를 세 계층으로 분리한다.

#### 9.5.1 내부 평가

구조가 자신의 제한된 감각으로 현재 상태와 변경 결과를 판단한다.

관찰 가능한 값:

- 내부 물질과 에너지 변화
- 경계 손상과 복구 상태
- 예상했던 감각과 실제 감각의 차이
- 신호 지연·과부하·경로 단절
- 과거 기억과 현재 결과의 불일치
- 자기 수정 전후의 내부 상태 변화

권한:

- 행동 또는 자기 수정 후보를 활성화
- 기존 경로 유지·약화·우회
- 제한된 내부 기억 갱신

한계:

- 자기 모델이 실제 구조와 다를 수 있음
- 만족 신호를 조작할 수 있음
- 새로운 환경을 경험하지 못하면 잘못된 확신이 강화될 수 있음
- 내부 일관성이 외부 적응을 보장하지 않음

내부 평가는 가설을 만들지만 정답을 제공하지 않는다.

#### 9.5.2 외부 현실 평가

별도의 점수 계산기가 아니라 개체의 예상과 독립적으로 작동하는 물리 세계다.

외부 결과:

- 물질 획득과 손실
- 에너지 소비와 고갈
- 실제 이동과 충돌
- 경계 손상·분열·융합·소멸
- 다른 구조의 행동
- 공간적 자원 변화
- 예상하지 못한 신호와 환경 변화

원칙:

- 세계는 개체의 내부 만족 판정을 참조하지 않음
- 자기 만족 신호가 높아져도 실제 결핍은 자동 해소되지 않음
- 자기개조에 유리한 별도 보상이나 생존 확률을 지급하지 않음
- 같은 외부 상태에는 계통과 목적에 관계없이 같은 물리 법칙을 적용

외부 현실은 내부 가설을 반박할 수 있어야 한다.

#### 9.5.3 세계 밖 관찰자 평가

감시기와 인간 연구자는 내부 판단·외부 결과·장기 계보를 사후 비교한다.

관찰 질문:

- 구조는 자기 수정을 성공이라고 판단했는가?
- 실제 물질·에너지·손상 결과는 어떻게 달라졌는가?
- 익숙하지 않은 환경에서도 같은 반응이 작동했는가?
- 실제 결핍 대신 만족 신호만 조작했는가?
- 단기 이득과 장기 계보 결과가 충돌했는가?
- 자기 수정 능력이 후손에게 물질적으로 전달됐는가?
- 후손의 변화 가능성이 증가·감소·소멸했는가?

금지:

- 관찰 판정을 세계 내부 보상으로 되돌려 보냄
- 유망한 계통만 살림
- 실패 결과 삭제
- 관찰자가 정한 지능·행복·적합도 점수로 번식 결정

발견 모드의 관찰자는 읽기 전용이다. 설계 모드에서 제작 언어의 새 버전을 승인할 때만 인간 평가를 사용할 수 있으며, 그 승인은 이미 실행 중인 세계가 아니라 새 세계군에 적용한다.

#### 9.5.4 평가 권한 표

| 대상 | 내부 평가 | 외부 평가 | 최종 결과 |
|---|---|---|---|
| 세계 내부 구조 | 내부 신호·예측·기억 | 독립적인 물리적 결과 | 성공·실패·오판 모두 가능 |
| 발견 모드 계통 | 별도 점수 없음 | 고정된 세계 법칙 | 인간 선택 없이 역사 지속 |
| 세계 밖 관찰기 | 측정 무결성 검사 | 원시 사건·계보 교차검증 | 기록만 하며 물리 개입 금지 |
| 세계 제작 언어 | 자기 진단과 과거 설계 기록 | 미지 명세·보존·인간 검토 | 검증된 새 버전만 새 세계에 사용 |

#### 9.5.5 자기개조 평가 순환

```text
내부 상태 감지
→ 자기 구조에 대한 불완전한 가설
→ 물질·에너지를 소비하는 작은 구조 변경
→ 외부 세계에서 실제 행동
→ 예상과 외부 결과의 차이 감지
→ 내부 모델·경로 유지·복구·추가 변경
```

세계 밖 관찰기는 별도로 다음을 비교한다.

```text
내부 예상
vs 외부 물리 결과
vs 장기 계보 결과
```

#### 9.5.6 불일치 유형

- **내부 성공·외부 성공:** 해당 환경에서 수정이 기능했을 가능성
- **내부 성공·외부 실패:** 자기기만·만족 신호 조작·잘못된 자기 모델 후보
- **내부 실패·외부 성공:** 내부 평가기의 오판 또는 지연 후보
- **단기 성공·장기 실패:** 자원 고갈·취약성·후손 가능성 감소 후보
- **현재 실패·후손 다양성 증가:** 당장 불리하지만 변화 가능성을 넓힌 후보
- **모든 환경에서 성공:** 일반화를 단정하지 않고 아직 관찰하지 않은 환경을 남김

어느 경우도 단일한 적합도 점수로 즉시 합치지 않는다. 원시 측정값과 환경 조건을 함께 보존한다.

#### 9.5.7 우물 안 개구리 방지 원칙

- 내부 모델과 독립적인 외부 환경을 유지
- 반복 경험과 낯선 환경을 구분해 기록
- 내부 만족과 실제 자원·손상을 별도 측정
- 하나의 고정 점수가 모든 선택을 지배하지 않게 함
- 성공뿐 아니라 실패·무효·불안정·비용 과다를 보존
- 외부 현실을 내부 구조가 수정하지 못하게 함
- 세계 밖 평가가 발견 모드의 물리에 개입하지 못하게 함

핵심 원칙:

> 내부 평가는 자기 수정의 가설을 만들고, 외부 현실은 그 가설을 반박할 수 있어야 하며, 세계 밖 관찰자는 둘의 차이를 기록한다.

## 10. 안전한 계산 최적화

세계 내부 자동 반응과 시뮬레이터 최적화를 구분한다.

### 10.1 허용

- 변하지 않은 국소 상태의 후보 계산 캐시
- 바뀐 주변만 재계산
- 구조 해시 기반 결합 가능성 재사용
- 독립 세계 병렬화
- 의미가 동일한 자료구조 개선

### 10.2 금지

- 이전 난수 결과 재사용
- 성공한 사건 결과 재사용
- 희귀 사건 후보 생략
- 중요하지 않아 보이는 중간 과정 건너뛰기
- 관찰 분류에 따른 계산 생략

### 10.3 최적화 승인 조건

캐시 ON/OFF에서 다음이 같아야 한다.

- 난수 사용 순서
- 사건 후보와 가중치
- 선택된 사건
- 전체 사건 해시
- 최종 상태 해시
- 보존 회계

## 11. 관찰 체계

관찰기는 세계 밖에 있으며 물리를 수정하지 않는다.

### 11.1 현재 관찰

- 구획 생성·소멸·분열·융합
- 서열 계보
- 복사와 불일치
- 촉매 기여
- 막 성장·수축
- 구획별 물질·에너지
- 희귀 사건 전후 블랙박스
- 상태·코드·seed 해시

### 11.2 향후 관찰

- 세대 깊이
- 독립 물리 복사본 전달
- 변이 전후 기능 변화
- 계통별 유지 시간
- 획득 상태와 유전 상태 분리
- 신호와 반응의 반복 연결
- 자기개조 전후 구조·비용·결과
- 비유전적 정보 전파

### 11.3 주장 단계

1. 물리 사건 발생
2. 독립 구조 전달
3. 기능 지속
4. 다음 세대 반복
5. 변이와 기능 차이의 계승
6. 계통 비율의 반복적 변화
7. 독립 세계에서 재관찰

앞 단계를 건너뛰어 진화·번식·지능을 주장하지 않는다.

## 12. 구현 로드맵

### 단계 A — 유전 주기 검증

현재 진행 중이다.

필요한 증거:

- 부모와 자식의 독립된 strand ID
- 같은 strand가 두 공간에 공유된 경우 제외
- 분열 후 독립 유지 시간
- 자식 내부의 복사·촉매 활동
- 자식의 재분열

다음 단계 조건:

- 계보·기능 기록이 물리와 독립적으로 신뢰 가능

### 단계 B — 서열·구조·기능 연결 강화

추가 후보:

- 접힌 모양에 따른 촉매 표면
- 주변 배열에 따른 비선형 반응
- 경계 배열에 따른 투과성 변화
- 구조 변화에 따른 활성화 장벽 변화

금지:

- 좋은 서열 목록
- 생명 전용 촉매
- 복제 성공 보정

### 단계 C — 물질 기반 내부 상태

추가 후보:

- 느리게 분해되는 상태 물질
- 반복 자극으로 누적되는 변형
- 상태에 따른 반응 경로 변경
- 유지 비용과 망각

목표 주장이 아니라 관찰 질문:

> 과거 사건이 현재 반응에 지속적인 차이를 만드는가?

### 단계 D — 감지와 행동

추가 후보:

- 경계 결합을 통한 외부 감지
- 내부 농도 변화 감지
- 비대칭 막 성장·수축
- 에너지 비용이 있는 이동
- 여러 경로의 물리적 경쟁

### 단계 E — 습관과 본능 후보

검증:

- 반복 경험으로 경로가 짧아지는가?
- 획득 경로가 사용하지 않을 때 약해지는가?
- 유전된 구조가 초기 반응 편향을 만드는가?
- 환경 변화에서 자동 반응이 실패할 수 있는가?

### 단계 F — 자기 모델과 자기개조

추가 후보:

- 내부 활동 감지 구조
- 제한된 자기 구조 지도
- 결합 생성·제거 촉매
- 수정 비용과 손상
- 수정 전후 상태 보존 구조

검증:

- 자기 수정이 항상 개선되지 않는가?
- 수정 능력 자체가 변이·학습되는가?
- 자기 만족 신호 조작이 가능한가?

### 단계 G — 생태와 신호

추가 후보:

- 공간별 자원 차이
- 부산물과 교차 영양
- 외부 흔적
- 물질 신호의 방출·감지
- 신호 조합과 시간 순서

### 단계 H — 문화와 언어 후보

필요 증거:

- 비유전적으로 획득된 반응
- 다른 구조로 전달
- 원래 구조 소멸 후에도 지속
- 신호 조합의 맥락 의존성
- 여러 세대의 변화

## 13. 현재 실험 결과에 따른 분기

### 독립 전달이 없음

조사:

- 경계가 같은 strand를 공유하는 이유
- 물리적 절단과 봉합 표현의 부족
- 관찰기 오분류

확률을 높이지 않고 표현 가능한 물리 자유도가 빠졌는지만 확인한다.

### 전달 후 즉시 소멸

조사:

- 에너지 부족
- 물질 누출
- 경계 불안정
- 복사 구조 부재

### 유지되지만 재분열 없음

조사:

- 서열 기능과 성장의 연결
- 복사 속도와 분해 속도
- 에너지 흐름

### 여러 세대가 이어짐

새 기능을 바로 추가하지 않는다. 물리를 동결하고 독립 seed와 다른 장비에서 반복 관찰한다.

### 변이·기능·계통 변화가 연결됨

진화 증거 후보로 분류하고 통계적 반복을 확인한 뒤 단계 C로 이동한다.

## 14. 제작 언어의 초안 문법

최종 문법은 아니지만 다음 영역으로 분리한다.

```text
kernel      보존·공간·시간·인과
matter      물질 종류와 상태 자유도
field       에너지·농도·확산
interaction 결합·절단·촉매·이동
boundary    경계와 투과
observer    비개입 측정
experiment  seed·세계 수·시간·판정 기준
```

금지된 고수준 명령 예:

```text
MAKE_LIFE
DIVIDE_CELL
ADD_INTELLIGENCE
REMEMBER_TARGET
EVOLVE_BETTER
```

허용되는 하위 표현 예:

```text
결합 상태가 일정 시간 유지된다
특정 공간 배열이 반응 장벽을 바꾼다
경계 물질 배열이 투과율을 바꾼다
상태 유지에는 에너지가 필요하다
```

## 15. 구현 원칙

- 실행 중인 실험 코드는 수정하지 않는다.
- 새 기능은 별도 브랜치 또는 실험 버전으로 만든다.
- 물리와 관찰 코드를 분리한다.
- 새로운 규칙마다 보존·인과·비개입 테스트를 먼저 만든다.
- 짧은 로컬 검증 후 결과를 모르는 seed로 장기 실행한다.
- 결과가 나빠도 법칙을 구조하지 않는다.
- 주장보다 원시 기록을 먼저 보존한다.
- 발견 모드와 설계 모드 결과를 섞지 않는다.

## 16. 다음 설계 작업

현재 기준 상태:

- 결정론 A0~A2.3 CPU 기준 구현
- 열·물·용질·수증기 물리 flux와 수렴 후보 감사
- B exact 월드 모델의 1~10 tick 읽기 전용 예상·비교
- CUDA int64 transport와 GPU 상주 field의 CPU 매 tick 동등성·성능 감사
- 모델 중립 B-Language 외부 경계 JSON Schema
- 내부 표현을 강제하지 않는 `BrainAdapter` Protocol
- 현재 exact B 모델을 첫 `ExactOracleAdapter`로 연결
- A2.3 4개 상태 claim 전부 외부 검증, falsified·untested 0
- 첫 독립 Cognitive Map 후보의 희소 상태·경로·도달성 질의 검증
- 사용자 전용 `private-causal-provenance-v1` full-trace writer와 검증기
- A의 매 tick·8개 stage 전체 snapshot·무손실 delta, B의 모든 경계 행동 기록
- D: HDD vault ACL 사용자 SID 단독 권한, B raw path 비공개
- 8 tick·88 record 실제 trace의 hash chain·delta·snapshot 복원 검증
- `TraceViewBroker`가 raw trace 검증 뒤 경로 없는 initial snapshot+delta view 생성
- `ChangeGraphAdapter`가 A transition·forecast 호출 없이 64 stage node와 30 delta 연산으로 tick 8 상태 재구성
- 상태 digest·지역 상태·마지막 변화·그래프 비용 claim 4개 전부 verified
- 승인 view `38,582` bytes, ChangeGraph digest `1579c83cd56065815ba0dff2dd1d1de115f1c4b94e425c6b6816adf0bcc105e2`
- ChangeGraph B 행동을 별도 사용자 전용 HDD 계보 8 records로 보존
- Cognitive Map과 ChangeGraph에 tick 8의 동일 외부 질의 5개 제공
- 두 후보 모두 verified 5, falsified·untested 0, normalized answer 동일
- Cognitive Map: 입력 `1,496` bytes, 표현 `3,073` bytes, 관련 칸 23개
- ChangeGraph: 입력 `38,658` bytes, 표현 `18,659` bytes, event node 64개·delta 30개
- 단일 측정 구성 시간은 각각 약 1.04ms·14.47ms이나 입력 정보량과 기능이 달라 승자 판정에 사용하지 않음
- 두 후보 행동을 사용자 전용 비교 계보 18 records로 함께 보존
- tick 7까지만 본 `ImpactScopeAdapter`가 tick 8 후보 위치 263/1,024와 규칙 4종 예측
- 실제 tick 8 변경 위치 4개·규칙 1종을 모두 포함해 위치·규칙 누락 0
- 과잉 위치 259개·과잉 규칙 3종을 별도 기록하고 효율 성공으로 포장하지 않음
- 고의로 실제 위치 하나를 제거한 scope는 외부 평가에서 falsified
- impact evaluation digest `9cb99b3a6fda1666ac2e296f2ada06d38b6b9ac9579e54acf8b66fcde91ee99b`
- 영향 범위 B 행동을 사용자 전용 HDD 계보 6 records로 보존
- tick 7에서 규칙 4종·무변화·숨은 변수 필요 가능성의 비배타적 가설 6개 봉인
- 근거 없는 숫자 weight 없이 시작하고 숫자 weight에는 evidence ID를 강제
- tick 8에서 supported 1·refuted 4·underdetermined 1로 원본 가설 불변 평가
- 실제 causal 규칙을 supported 가설이 설명해 coverage success true
- 새 변수 필요 가설은 한 tick으로 결론 내리지 않고 반복 residual 관측 대상으로 유지
- HypothesisSet digest `5088b0e54098975074df35b51dba417b6311a454b4ccc72faa7dd945f629fcf5`
- resolution digest `d61bbdd0b9206af799142b53160b112c2090d303361bc48671263b2629010ef9`
- HypothesisSet B 행동을 사용자 전용 HDD 계보 12 records로 보존
- 같은 tick 7 부모에서 control·행동 3·설계 1의 CounterfactualBranch 5개 생성
- 모든 branch에 low 영향 범위와 medium Cognitive Map 결과 저장
- exact 예산 3개를 control·risk·counterexample track에 배정하고 uncertainty·diversity 2개는 삭제 없이 deferred
- 무행동 control의 exact 결과가 관측된 tick 8 digest와 일치
- 큰 열 개입은 외부 공급 회계로 accounted energy `10` 유지
- 간선 차단 설계 branch는 부모 spec을 바꾸지 않고 새 spec digest 생성
- plan digest `7abaca393f5558d1026eb3b14d7e328c307e8301f3ec460ddfdbfa5d81f3c154`
- evaluation digest `170843afeff1b9c922526b95ba8d31099d0d69ccf0344b1278d9cdd7ca39fbd0`
- Counterfactual B 행동을 사용자 전용 HDD 계보 26 records로 보존
- `vapor`를 모르는 제한 이론을 서로 다른 초기 상태·spec digest의 봉인 세계 4개에서 검사
- 네 실행 모두 같은 `state-omission:vapor:changed-while-unmodeled` residual 반복
- 최소 distinct run/spec 3 조건을 넘어 repeated pattern 성립
- 관측 pipeline 검사·기존 vapor 변수 추가·vapor 관계 모델링의 수정 후보 3개 병렬 생성
- 알려진 A 변수 누락으로 설명 가능해 새 미지 latent 변수는 생성하지 않음
- 부모 이론 digest 불변, applied proposal 없음, 세 후보 모두 과학적 상태 untested
- residual pattern digest `110d92dbb1152c18bd0bb608c93e67824e79e2c4e57d5efc817d30f0cde57dc7`
- revision set digest `0dd36b6e2e9ff5db367852718409cc123f412076ee1bf4df117f56688cf372db`
- 4개 A full trace와 B 분석을 사용자 전용 HDD 캠페인으로 보존
- TheoryRevision 후보를 구분하는 ExperimentProposal arm 4개 봉인
- 독립 trace extraction 대조군·수증기 0 대조군·held-out vapor 5·13 세계 포함
- held-out spec 3개는 training spec 4개와 digest 비중복
- 수정 후보 3개 모두 distinguishing arm coverage, governance valid true
- approval status `pending-user-approval`, execution allowed false, automatic execution false
- proposal digest `e1fdab8d7f8fe1ac8c958af40d868662fb1239139f164a1d9584c9f712e2abb9`
- scientific status `not-run`, 실제 A held-out 실행 0개
- 제안·review를 사용자 전용 HDD 계보 7 records로 보존
- 확률 `scheduler-v1`과 GCP 결과 별도 보존

다음 B 작업 순서:

1. 사용자가 봉인된 `vapor-theory-heldout-v1` 제안서를 검토
2. 명시적 승인 시에만 독립 trace audit와 held-out 세계 3개 실행
3. 부모 이론·변수 추가 후보·관계 후보의 예상을 실행 전에 별도 봉인
4. 결과로 scientifically supported·refuted·underdetermined 분리
5. 승인하지 않으면 제안서를 미실행 상태로 영구 보존하고 다른 B 작업으로 이동
6. 이후 `ExploitProbe`와 `MemoryLesson` archive

현재는 사용자 결정이 필요한 경계다. 승인 없이 실행하지 않는다.

### 통과조건

- 각 adapter가 다른 내부 표현·관측 view·claim kind를 선언할 수 있음
- 공통화 대상은 관측 범위·예산·외부 claim·반증 연결·평가 결과로 제한
- exact B adapter의 예상과 현재 A checkpoint가 기존 digest 수준에서 동일
- opaque latent나 새로운 질문이 `WorldState`·`CausalMap` 없이도 제출 가능
- 검증 가능한 claim은 `EvidenceBridge`를 가지며 틀린 답은 A를 바꾸지 않고 falsified로 기록
- adapter가 A·헌법·원시 archive를 수정할 수 없음
- 근거·저자 보고·근사·가설·미확인을 기계적으로 구분
- exploit 발견이 A 보정이 아니라 B 오류 기록으로 남음
- 실패한 설계와 다른 branch의 교훈도 삭제하지 않음
