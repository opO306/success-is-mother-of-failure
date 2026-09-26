# B 심층 설계 문서

**문서 분류: 후기 B 연구 자산 / 보존.** B는 취소·폐기하지 않았으며, A·L 기반의 작은 세계가 돌아가는 후기 단계에서 본격 개발한다. 기존 설계·구현·시험은 비교군/연구 자산으로 보존한다.
현재 상태는 [CURRENT_STATE.md](../../../CURRENT_STATE.md)를 본다.

## A 세계의 복합 인과관계를 발견·검증하는 외부 연구 지능

**문서 상태:** 설계 기준 문서  
**트랙:** NEXT / B Research System  
**기준:** 현재 확정된 B0 Research Loop 설계를 보존하며, 본 문서는 후속 인과 추론 확장 방향을 정의한다.  
**핵심 원칙:** B는 세계를 대신 만드는 시스템이 아니라, A 세계에서 실제로 발생한 복합적인 인과관계를 관찰·가설화·개입·검증·축적하는 연구 시스템이다.

---

# 1. 문서 목적

이 문서는 B 시스템의 존재 이유와 장기 설계 방향을 명확히 고정하기 위한 문서다.

초기에는 난수와 확률 기반으로 세계의 변수를 만들거나, 인간이 사건별 규칙을 추가하는 방식으로 복잡성을 표현하려 했다. 그러나 세계 규모가 커질수록 다음 문제가 나타난다.

- 모든 사건의 확률을 인간이 미리 정의해야 한다.
- 예상하지 못한 변수는 표현할 수 없다.
- 작은 변화가 긴 시간 뒤 다른 결과로 이어지는 인과 사슬을 사람이 일일이 설계해야 한다.
- 사건 수가 증가할수록 조건문과 확률표가 폭발적으로 복잡해진다.
- 결과가 다양해 보여도 실제로는 인간이 미리 설계한 분포 안에서만 움직인다.
- 단순 상관관계와 실제 원인을 구분하기 어렵다.
- 세계 내부에서 자연적으로 생긴 새로운 구조나 행동의 이유를 인간이 로그만 보고 해석하기 어렵다.

따라서 B는 다음 질문을 자동으로 다루는 시스템으로 정의한다.

> 무슨 일이 일어났는가?  
> 그 전에 무엇이 있었는가?  
> 어떤 조건이 달랐는가?  
> 어떤 조건을 바꾸면 결과도 달라지는가?  
> 현재 관측 변수만으로 설명 가능한가?  
> 중간에 누락된 원인이 존재할 가능성이 있는가?  
> 작은 변화가 긴 시간 뒤 어떤 경로를 통해 큰 차이를 만들었는가?

B의 최종 목표는 **A 세계의 인과 구조를 연구하는 것**이다.

---

# 2. 전체 시스템에서의 역할

전체 시스템은 장기적으로 다음 세 계층으로 분리한다.

```text
┌─────────────────────────────────────────────┐
│                    인간                     │
│                                             │
│  세계의 기본 법칙 / 실험 목적 / 자원 한계    │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                     B                       │
│                                             │
│      외부 연구자 / 인과 추론 / 실험 설계     │
│                                             │
│ observe → hypothesize → intervene → verify │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                     A                       │
│                                             │
│            실제 물리적 세계                 │
│                                             │
│   환경 / 물질 / 에너지 / 생명 / 상호작용     │
│                                             │
│       ┌──────────────────────────┐          │
│       │      A 내부 생명 두뇌     │          │
│       │ 감각 → 기억 → 학습 → 행동 │          │
│       │       진화 / 변이         │          │
│       └──────────────────────────┘          │
└─────────────────────────────────────────────┘
```

## 2.1 A의 역할

A는 실제 상태 변화를 발생시키는 세계다.

A가 책임지는 것:

- 물리 법칙
- 물질 상태
- 에너지
- 공간
- 충돌
- 결합 및 분해
- 확산
- 생명체의 실제 행동 결과
- 환경 변화
- 시간 경과
- 세계 내부의 모든 직접 상태 전이

A는 "인과를 설명"하지 않는다.

A는 단지 법칙에 따라 실행되고 결과를 남긴다.

---

## 2.2 A 내부 생명 두뇌의 역할

생명 두뇌는 A 세계 내부에서 살아가는 지능이다.

주요 기능:

- 감각 입력
- 내부 상태 유지
- 기억
- 행동 선택
- 경험 기반 학습
- 세대 간 변이
- 진화 가능성
- 신호 생성 및 통신 가능성
- 필요하다면 자체 표현 체계 또는 언어의 진화

생명 두뇌는 B와 분리한다.

B가 생명에게 먹이 위치, 생존 전략, 정답 행동을 직접 알려주지 않는다.

---

## 2.3 B의 역할

B는 A 세계 외부에 있는 연구 시스템이다.

B가 책임지는 것:

- 관찰
- 이상 현상 탐지
- 관계 탐색
- 인과 가설 생성
- 개입 실험 설계
- 반사실 비교
- 실험 결과 비교
- 가설 상태 갱신
- 인과 지식 축적
- 설명되지 않는 잔차 탐지
- 장기 파급효과 추적

B는 다음 역할을 맡지 않는다.

- 생명체 행동 직접 제어
- 세계를 원하는 결과로 유도
- 확률표로 세계 사건 생성
- 생명체의 정답 전략 제공
- 사람이 원하는 결론에 맞춰 실험 결과 조정

---

# 3. B의 핵심 철학

## 3.1 B는 난수 생성기를 대체하는 것이 아니다

난수는 여전히 사용할 수 있다.

하지만 난수는 다음 용도로 제한한다.

- 초기 조건 다양화
- 미세 교란
- 샘플링
- 탐색
- 통제된 확률 과정

B의 역할은 난수를 "더 똑똑하게 뿌리는 것"이 아니다.

B는 난수나 자연적 변동으로 발생한 세계의 결과를 분석하여 **왜 그런 결과가 나왔는지** 탐색한다.

---

## 3.2 B는 상관관계보다 개입을 중시한다

다음 두 세계가 있다고 가정한다.

```text
세계 1:
온도 상승
막 분열 증가

세계 2:
온도 상승 없음
막 분열 감소
```

이것만으로는 온도가 원인이라고 확정할 수 없다.

다른 변수가 동시에 바뀌었을 수 있기 때문이다.

B는 다음 실험을 시도해야 한다.

```text
동일 초기 조건
+ 온도만 변경
```

그리고 결과를 비교한다.

따라서 B에서 중요한 질문은 다음이다.

> X와 Y가 같이 나타났는가?

보다

> X를 의도적으로 바꾸면 Y가 달라지는가?

이다.

---

## 3.3 단일 원인보다 인과 경로를 저장한다

현실적인 세계에서 결과는 대부분 다음처럼 발생한다.

```text
X → Y
```

가 아니라

```text
X
↓
A
↓
B ─────┐
↓      │
C      E
└──→ D ←┘
     ↓
     Y
```

따라서 B의 지식 단위는 단순한 2항 관계가 아니라 **경로와 그래프**여야 한다.

---

## 3.4 모르는 것을 표현할 수 있어야 한다

B는 설명하지 못한 관계를 억지로 설명하면 안 된다.

다음 표현이 가능해야 한다.

```text
A → ? → B
```

의미:

- A와 B 사이에 반복적인 관계가 있다.
- A를 개입하면 B가 변한다.
- 그러나 현재 관측된 중간 변수만으로 경로를 설명할 수 없다.
- 숨은 변수 또는 관측 누락이 존재할 가능성이 있다.

"모름"도 정식 상태다.

---

# 4. 현재 B0 Research Loop와의 관계

현재 확정된 B0 Research Loop의 기본 흐름은 유지한다.

```text
observe
→ generate
→ design
→ seal
→ execute
→ compare
→ update
→ archive
```

본 문서는 B0를 폐기하거나 변경하기 위한 문서가 아니다.

B0를 **인과 연구 시스템의 최소 실행 골격**으로 보고, 후속 버전에서 기능을 확장한다.

---

# 5. 현재 B0의 책임 범위

B0에서 우선 완성해야 하는 것은 연구 루프의 재현성과 검증 가능성이다.

## 5.1 B0 필수 책임

- Observation 수집
- CausalHypothesis 생성
- Prediction 생성
- Experiment 설계
- Prediction sealing
- A 실행
- 결과 비교
- Hypothesis 상태 갱신
- Research Journal 기록
- provenance 유지
- 결정적 직렬화
- digest / canonical 표현
- append-only 기록
- 실험 전후 상태 추적

## 5.2 B0에서 아직 강제하지 않는 기능

다음은 B0의 필수 구현 범위에서 제외한다.

- 전체 인과 그래프 자동 생성
- 장기 나비효과 분석
- 자동 숨은 변수 발견
- 복잡한 counterfactual planner
- 다단계 mediation 분석
- 구조적 causal discovery 전체 구현
- 자율적인 관측 센서 추가
- 생명 두뇌와의 직접 통합
- 자연언어 기반 설명 모델

B0를 무리하게 확장하지 않는다.

---

# 6. 후속 핵심 기능 개요

후속 B는 다음 기능을 순차적으로 추가한다.

```text
B0
연구 루프의 최소 골격
        ↓
B1
시간적 인과 사슬 + 개입 + 반사실
        ↓
B2
인과 그래프 + 조건부 원인 + 다중 변수
        ↓
B3
숨은 변수 후보 + 장기 파급효과 + 자동 관측 확장
        ↓
B4
복수 세계 연구 + 메타 가설 + 장기 지식 체계
```

---

# 7. 사건 모델

B가 세계를 연구하려면 A의 raw state만 저장해서는 부족하다.

B는 상태 변화를 **사건(Event)** 단위로 표현할 수 있어야 한다.

예시:

```text
Event:
    event_id
    world_id
    time_start
    time_end
    entity_ids
    event_type
    pre_state
    post_state
    delta
    source
    confidence
```

가능한 사건 예:

- 온도 상승
- 입자 결합
- 막 형성
- 막 파열
- 막 분열
- 물질 흡수
- 에너지 감소
- 개체 이동
- 신호 방출
- 개체 사망
- 복제
- 돌연변이
- 군집 형성

중요한 것은 event_type을 모든 경우에 사람이 고정할 필요는 없다는 점이다.

초기에는 사람이 정의한 사건 분류를 사용할 수 있지만, 장기적으로는 상태 변화 패턴을 묶어 새로운 사건 후보를 만들 수 있다.

---

# 8. 시간적 인과 사슬

B는 다음을 구분해야 한다.

```text
동시에 발생
먼저 발생
뒤에 발생
일정 시간 후 발생
반복 후 발생
누적 후 발생
```

예:

```text
t=100
온도 +0.2

t=145
확산 증가

t=270
특정 물질 농도 증가

t=510
막 응력 증가

t=840
막 분열
```

B는 이를 다음처럼 저장할 수 있다.

```text
TemperatureRise
    ↓ 45 step
DiffusionIncrease
    ↓ 125 step
ConcentrationShift
    ↓ 240 step
MembraneStress
    ↓ 330 step
MembraneDivision
```

단순히 "온도와 분열이 관련 있음"이라고 저장하지 않는다.

---

# 9. 인과 그래프

## 9.1 기본 구조

인과 그래프는 node와 edge로 구성한다.

### Node

- 상태
- 사건
- 조건
- 개체
- 환경 변수
- 집단 상태

### Edge

- precedes
- enables
- inhibits
- causes_candidate
- mediates
- depends_on
- amplifies
- suppresses
- unknown_link

예:

```text
[온도 상승]
   │
   ├─ causes_candidate → [확산 증가]
   │
   └─ causes_candidate → [막 탄성 변화]

[확산 증가]
   ↓
[농도 변화]
   ↓
[막 응력]

[막 탄성 변화] ──┐
                  ↓
              [막 분열]
```

---

## 9.2 Edge는 확정 법칙이 아니다

각 edge는 상태를 가진다.

예:

```text
PROPOSED
SUPPORTED
WEAKENED
CONTRADICTED
REJECTED
UNRESOLVED
```

추가로 다음 메타데이터를 보존한다.

```text
support_count
contradiction_count
experiment_ids
effect_size
confidence
known_conditions
known_failures
```

---

# 10. 조건부 인과관계

현실에서 A가 항상 B를 만드는 경우는 드물다.

다음과 같은 관계가 존재할 수 있다.

```text
A + C → B
```

또는

```text
A → B only if temperature > T
```

따라서 B는 조건을 edge의 일부로 표현할 수 있어야 한다.

예:

```text
Cause:
    high_energy_flux

Condition:
    membrane_thickness < 0.4
    local_density > 0.7

Effect:
    division_probability sharply increases
```

단, "확률 증가"만으로 원인이라고 결정하지 않는다.

조건부 개입 실험으로 검증해야 한다.

---

# 11. 개입 실험

## 11.1 개입 정의

개입은 관측과 다르다.

관측:

```text
온도가 높은 세계에서 분열이 많았다.
```

개입:

```text
동일한 세계 상태에서
온도만 의도적으로 높였다.
```

B는 후자를 더 강한 인과 증거로 취급한다.

---

## 11.2 최소 개입 원칙

가능하면 한 번에 하나의 주요 변수를 변경한다.

```text
baseline:
X=1
Y=1
Z=1

intervention:
X=0
Y=1
Z=1
```

여러 변수를 동시에 바꾸면 원인을 분리하기 어렵다.

---

## 11.3 개입 종류

### 제거

```text
remove(X)
```

### 고정

```text
clamp(X=value)
```

### 증가/감소

```text
delta(X, +0.1)
```

### 차단

```text
block(edge A→B)
```

### 치환

```text
replace(structure_A, structure_B)
```

### 시간 이동

```text
shift(event_X, +100 steps)
```

시간적 원인 검증에 중요하다.

---

# 12. 반사실 분석

B는 다음 질문을 다뤄야 한다.

> X가 없었다면 Y는 여전히 발생했을까?

가장 단순한 방법은 같은 초기 상태에서 분기된 두 세계를 실행하는 것이다.

```text
                 Initial State S
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
         Baseline             Counterfactual
          X 있음                 X 없음
             │                   │
             ▼                   ▼
         결과 Y1               결과 Y2
```

비교:

```text
Y1 != Y2
```

라고 해서 즉시 인과 확정은 아니다.

반복 실험과 조건 변화가 필요하다.

---

# 13. 반사실 실행의 결정론

반사실 비교에서 가장 중요한 문제는 **불필요한 차이를 막는 것**이다.

가능한 경우 다음을 동일하게 유지한다.

- initial state
- world seed
- deterministic engine version
- simulation parameters
- entity ordering
- control variables
- execution length

변경 대상만 다르게 한다.

```text
Baseline digest
Counterfactual digest
Intervention spec
```

를 반드시 기록한다.

---

# 14. 숨은 변수 후보

다음 패턴을 고려한다.

```text
A를 바꾸면 B가 변한다.
그러나 알려진 중간 변수로는 설명되지 않는다.
```

이때 B는 억지로 기존 변수에 원인을 할당하면 안 된다.

대신 다음 상태를 생성한다.

```text
LatentCauseCandidate:
    source=A
    target=B
    unexplained_effect=...
    missing_path=True
```

---

## 14.1 숨은 변수 탐색 전략

### 주변 상태 확대

A와 B 사이 시간 구간의 모든 관측 가능한 변수 조사

### 관측 해상도 증가

더 짧은 시간 간격으로 상태 기록

### 새로운 feature 생성

기존 변수 조합을 하나의 후보 상태로 구성

예:

```text
temperature_gradient
energy_density_ratio
local_topology
stress_accumulation
```

### 중간 사건 탐색

A 이후 반복적으로 등장하는 사건 후보 검색

### intervention decomposition

중간 후보 변수 C를 별도로 조작하여:

```text
A → C → B
```

여부를 확인

---

# 15. 장기 파급효과와 나비효과

B가 장기적으로 다루고 싶은 핵심 문제다.

작은 초기 차이가 매우 긴 시간 뒤 큰 차이를 만들 수 있다.

예:

```text
초기 온도 +0.01
↓
확산 패턴 미세 변화
↓
막 구조 위치 변화
↓
먹이 접근 가능성 변화
↓
특정 개체 생존
↓
특정 유전형 비율 증가
↓
군집 행동 변화
↓
수백 세대 후 생태계 구조 변화
```

B는 첫 상태와 마지막 상태만 연결해서는 안 된다.

가능한 중간 경로를 추적해야 한다.

---

## 15.1 장기 파급효과의 정의

B에서 butterfly effect 후보는 다음 조건을 만족하는 사례로 본다.

- 초기 개입 크기가 작다.
- 단기 효과가 제한적이다.
- 시간이 지나며 차이가 확대된다.
- 최종적으로 구조적 결과 차이가 발생한다.
- 반복 실험에서 경로 또는 효과 일부가 재현된다.

---

## 15.2 divergence curve

두 세계 사이의 차이를 시간에 따라 측정한다.

```text
D(t)
```

예:

```text
t=0       0.001
t=100     0.004
t=1000    0.021
t=10000   0.38
t=100000  0.91
```

중요한 것은 D 하나만 보는 것이 아니다.

어떤 변수군에서 divergence가 시작됐는지 추적한다.

---

# 16. 인과 경로의 중재 구조

다음 관계를 구분한다.

```text
X → Y
```

와

```text
X → M → Y
```

M은 mediator다.

예:

```text
온도 상승
↓
막 탄성 변화
↓
분열
```

B는 다음 실험을 할 수 있다.

1. 온도를 변경
2. 막 탄성 변화를 막음
3. 분열이 여전히 발생하는지 확인

만약 분열 효과가 사라진다면 M이 중요한 중재 변수일 가능성이 높아진다.

---

# 17. 경쟁 가설

B는 하나의 설명만 유지해서는 안 된다.

예:

```text
현상:
막 분열 증가
```

가능한 가설:

```text
H1: 온도 변화
H2: 에너지 밀도
H3: 막 두께
H4: 유체 흐름
H5: H1 + H3 상호작용
H6: 아직 관측되지 않은 변수
```

각 가설은 독립적으로 상태를 가진다.

```text
PROPOSED
TESTING
SUPPORTED
PARTIALLY_SUPPORTED
CONTRADICTED
REJECTED
UNRESOLVED
```

---

# 18. 실험 포트폴리오

한 가설에 대해 한 번의 실험만 실행하지 않는다.

예:

```text
Hypothesis H1
    ├─ Experiment A: X 제거
    ├─ Experiment B: X 증가
    ├─ Experiment C: X 감소
    ├─ Experiment D: 다른 초기 세계
    └─ Experiment E: mediator 차단
```

이를 `CausalExperimentPortfolio`가 관리한다.

목적:

- 특정 seed 의존성 감소
- 우연한 결과 방지
- 조건 범위 파악
- 반증 가능성 확보

---

# 19. Prediction Seal

실험 결과를 본 뒤 가설을 수정하는 것을 막기 위해 prediction을 실행 전에 고정한다.

예:

```text
Prediction:
    intervention = reduce_temperature(0.2)
    expected_effect = division_count decreases
    expected_window = 5000 steps
    failure_condition = no measurable change
```

실행 전 digest를 생성한다.

```text
PredictionSeal
```

실행 뒤 prediction을 변경하지 않는다.

이 기능은 B의 연구 신뢰성에 중요하다.

---

# 20. B가 저장해야 하는 지식의 종류

B의 지식 저장소는 최소 다음을 구분한다.

## Observation

실제로 관측된 사실

## Correlation

함께 변화하는 관계

## Temporal Relation

시간적 순서 관계

## Hypothesis

원인에 대한 설명 후보

## Intervention Result

변수를 직접 변경한 실험 결과

## Counterfactual Result

분기 세계 비교 결과

## Causal Edge

검증 중인 인과 관계

## Causal Path

다단계 인과 경로

## Latent Variable Candidate

설명되지 않는 관계

## Boundary Condition

관계가 성립하는 조건

## Contradiction

기존 가설과 충돌하는 결과

---

# 21. 확률과 인과의 구분

B는 확률을 버리지 않는다.

확률은 다음을 표현하는 데 유용하다.

```text
P(Y | X)
```

하지만 B의 최종 질문은 여기서 멈추지 않는다.

```text
P(Y | do(X))
```

즉 X를 직접 바꾸었을 때 Y가 어떻게 변하는지를 중요하게 본다.

구현에서 반드시 수학적 do-calculus 전체를 사용할 필요는 없지만, 개념적 구분은 유지한다.

---

# 22. 언어 표현과 내부 표현 분리

B가 자연어로 설명할 수 있다고 해서 내부 지식까지 자연어 문자열로 저장하면 안 된다.

권장 구조:

```text
내부:
typed structured data
graph
event
condition
prediction
experiment
evidence

외부:
human-readable explanation
```

예:

내부 표현:

```text
edge:
    source = event_102
    target = event_884
    relation = CAUSES_CANDIDATE
    condition = condition_31
```

사람에게 보여줄 때:

```text
"국소 에너지 밀도가 일정 수준 이상일 때
막 응력 상승이 분열에 선행하며,
에너지 밀도를 낮추면 분열 빈도가 감소했다."
```

---

# 23. B 언어의 역할 재정의

B 언어가 존재한다면 그것은 거대한 자연어 대체 언어가 아니라 **세계와 연구 시스템 사이의 정밀한 표현 규격**에 가깝다.

예:

```text
ENTITY
STATE
EVENT
RELATION
CAUSE
CONDITION
INTERVENTION
COUNTERFACTUAL
OBSERVATION
EVIDENCE
TIME
```

B 언어는 다음을 보장해야 한다.

- canonical representation
- deterministic serialization
- stable identifier
- machine-readable
- human-inspectable
- versionable
- hashable

---

# 24. 예상하지 못한 변수 처리

B는 사전에 등록된 변수만 연구하면 결국 인간의 설계 범위를 벗어나지 못한다.

따라서 후속 단계에서는 **derived feature**를 허용한다.

예:

A가 직접 제공하는 변수:

```text
temperature
density
energy
velocity
```

B가 생성하는 파생 변수:

```text
temperature_gradient
density_variance
energy_flux
local_entropy_proxy
cluster_compactness
stress_accumulation
```

단, 파생 변수가 너무 자유로우면 탐색 공간이 폭발한다.

따라서 생성 이유와 사용 실험을 기록한다.

---

# 25. 관측 해상도 자체를 연구 대상으로 만들기

어떤 현상이 현재 로그 해상도에서는 보이지 않을 수 있다.

예:

```text
100 step마다 기록
```

하는데 실제 원인 사건은 5 step 안에 발생할 수 있다.

따라서 B는 후속 단계에서 다음 요청을 만들 수 있다.

```text
ObservationRequest:
    variable_set
    spatial_region
    time_start
    time_end
    sampling_interval
    reason
```

이 기능을 통해 B는 "무엇을 더 자세히 봐야 하는지"도 연구한다.

---

# 26. 인과 발견에서의 시간 창

모든 과거 사건을 모든 미래 사건과 비교하면 계산량이 폭발한다.

따라서 다단계 window를 사용한다.

예:

```text
micro window
0 ~ 100 steps

meso window
100 ~ 10,000 steps

macro window
10,000 ~ 1,000,000 steps
```

현상 종류에 따라 탐색 범위를 다르게 한다.

---

# 27. 후보 생성과 pruning

인과 후보 수는 빠르게 폭발한다.

따라서 다음 필터를 사용할 수 있다.

1. 시간적으로 원인이 결과보다 먼저 발생했는가
2. 반복 세계에서 관계가 관찰되는가
3. effect magnitude가 최소 기준 이상인가
4. 개입 결과가 존재하는가
5. 다른 변수로 쉽게 설명되는가
6. 이미 반증된 관계인가

단, pruning은 탐색 비용을 줄이기 위한 것이며 "증거가 약한 가설 = 거짓"으로 취급하지 않는다.

---

# 28. 지식 충돌 처리

B는 서로 충돌하는 결과를 숨기면 안 된다.

예:

```text
Experiment 1: X → Y
Experiment 2: X → not Y
```

가능한 해석:

- 조건 차이
- 관측 오류
- stochastic effect
- 다른 숨은 변수
- 가설 자체가 잘못됨

따라서 충돌 자체를 연구 대상으로 승격한다.

```text
ContradictionRecord
```

를 별도로 남길 수 있다.

---

# 29. 재현성

모든 인과 주장은 재현 가능한 실험에 연결되어야 한다.

최소 provenance:

```text
world_id
engine_version
initial_state_digest
control_definition
intervention_definition
prediction_digest
result_digest
journal_entry
```

가능하면 어떤 주장도 "설명 문자열만 존재하는 상태"로 남기지 않는다.

---

# 30. Research Journal

Research Journal은 append-only 구조를 유지한다.

예:

```text
OBSERVATION
HYPOTHESIS_CREATED
PREDICTION_SEALED
EXPERIMENT_DESIGNED
EXPERIMENT_STARTED
EXPERIMENT_FINISHED
RESULT_COMPARED
HYPOTHESIS_UPDATED
CAUSAL_EDGE_UPDATED
CONTRADICTION_FOUND
LATENT_VARIABLE_PROPOSED
```

각 entry는 이전 entry hash를 포함하는 hash-chain 방식이 적합하다.

목적:

- 결과 조작 방지
- 연구 이력 추적
- 재현성
- 디버깅
- 나중에 B 자체의 판단 분석

---

# 31. B와 생명 두뇌의 인터페이스

B는 생명 두뇌를 직접 조종하지 않는다.

정상 흐름:

```text
A 내부 생명:
감각 → 두뇌 → 행동 → 세계 변화

B:
세계 변화 관찰
↓
현상 탐지
↓
가설
↓
통제된 별도 실험
```

B가 생명 두뇌에 접근하는 경우도 **실험 조건**으로 명시해야 한다.

예:

```text
특정 신호 채널 차단
특정 감각 입력 제거
기억 용량 제한
```

이것은 "생명을 도와주는 기능"이 아니라 causal intervention이다.

---

# 32. 생명 진화 연구에서의 B

장기적으로 B는 다음 질문을 연구할 수 있다.

- 왜 특정 구조가 살아남았는가?
- 특정 신호가 실제로 통신 기능을 가지는가?
- 기억이 생존에 영향을 주는가?
- 어떤 감각이 행동 변화의 원인인가?
- 특정 뇌 구조가 어떤 환경에서 유리한가?
- 집단 행동은 독립적으로 발생했는가?
- 언어 비슷한 신호가 자연선택에 의해 유지되는가?
- 환경의 작은 변화가 진화 경로를 바꾸는가?

---

# 33. 언어 출현 실험 예시

A 내부 개체가 임의 신호를 생성할 수 있다고 가정한다.

```text
Signal 17
Signal 43
Signal 88
```

B는 다음을 관찰한다.

```text
Signal 17 발생 후
근처 개체의 이동 방향이 반복적으로 변함
```

가능한 가설:

```text
H1:
Signal 17은 먹이 위치와 관련된 통신 기능을 가진다.
```

실험:

```text
Signal 17 차단
→ 이동 패턴 변화?

Signal 17 무작위 재생
→ 이동 유도?

발신자를 제거
→ 패턴 사라짐?
```

이를 통해 단순 동시 발생과 기능적 통신을 구분한다.

---

# 34. 새로운 두뇌 구조의 연구

A 내부 두뇌가 진화 가능하다면 B는 구조 자체도 연구 대상에 포함할 수 있다.

예:

```text
Brain Type A
Brain Type B
Brain Type C
```

관찰:

```text
환경 E에서 B가 높은 생존률
```

B는 단순히 "B가 좋다"고 결론내지 않는다.

질문:

- 기억 크기 때문인가?
- 재귀 연결 때문인가?
- 감각 채널 때문인가?
- 행동 출력 수 때문인가?
- 특정 환경과의 상호작용인가?

이를 개입 실험으로 분해한다.

---

# 35. B가 직접 새로운 세계 법칙을 만들지 않는 이유

B가 관찰 결과를 보고 A의 법칙을 자동 수정하면 연구자와 세계 설계자가 섞인다.

예:

```text
B:
"분열이 적다"
→ 물리법칙 수정
→ 분열 증가
```

이 구조는 금지한다.

허용 가능한 것은:

```text
B:
가설 제안
실험 world fork 생성
실험 결과 기록
```

A의 기본 법칙 변경은 별도 인간 승인 또는 별도 설계 트랙으로 분리한다.

---

# 36. 실패 모드

## 36.1 상관관계를 원인으로 오인

대응:

- 개입 실험
- 반사실 비교
- 경쟁 가설

## 36.2 실험 후 가설 수정

대응:

- PredictionSeal

## 36.3 결과 cherry-picking

대응:

- 전체 portfolio 기록
- 실패 실험 포함

## 36.4 seed 과적합

대응:

- 여러 world
- 여러 initial condition

## 36.5 탐색 공간 폭발

대응:

- temporal pruning
- effect threshold
- hierarchical search
- staged observation

## 36.6 숨은 변수 무시

대응:

- unexplained residual 기록
- latent candidate 허용

## 36.7 B가 세계를 직접 조종

대응:

- research interface와 world engine 권한 분리

---

# 37. 평가 지표

B의 성능을 "정답률 하나"로 평가하면 부족하다.

후보 지표:

## 재현성

같은 조건에서 같은 결과를 얻는 비율

## 인과 판별력

상관관계와 개입 효과를 구분하는 능력

## 반증 능력

자신의 기존 가설을 반박하는 실험을 설계할 수 있는가

## 설명되지 않는 잔차 탐지율

현재 모델로 설명되지 않는 현상을 발견하는가

## 경로 복원율

알려진 synthetic causal chain에서 중간 경로를 얼마나 찾아내는가

## 장기 영향 탐지

작은 초기 변화가 긴 시간 뒤 결과로 이어지는 경로를 추적하는가

## 실험 효율

동일한 지식을 얻기 위해 필요한 A 실행 횟수

## 지식 안정성

새로운 증거가 들어왔을 때 기존 가설을 적절히 수정하는가

---

# 38. Synthetic 검증 세계

실제 A 전체에서 바로 테스트하면 정답을 알 수 없다.

따라서 B 자체 검증용 작은 synthetic world를 만든다.

예:

```text
X → M → Y
Z → Y
```

실제 인과 구조를 개발자가 알고 있는 세계다.

B가 다음을 복원할 수 있는지 본다.

- X와 Y 관계
- M의 mediator 역할
- Z의 독립 효과
- X 제거 시 Y 변화
- M 차단 시 X 효과 감소

이런 작은 세계를 B의 단위 테스트처럼 사용한다.

---

# 39. 나비효과 검증용 synthetic world

예:

```text
initial perturbation p = 0.001
↓
state A
↓
state B
↓
branch decision
↓
population shift
```

정답 경로를 알고 있는 테스트 세계를 만든다.

B가 단순히 최종 divergence만 찾는 것이 아니라 중간 분기점을 찾는지 평가한다.

---

# 40. 데이터 구조 권장 방향

현재 deterministic 모듈 철학을 유지한다.

예상 구조:

```text
engine/deterministic/
    research_state.py
    causal_hypothesis.py
    causal_experiment.py
    causal_executor.py
    research_journal.py
    research_loop.py
```

후속 확장 후보:

```text
    causal_event.py
    causal_graph.py
    intervention.py
    counterfactual.py
    latent_variable.py
    causal_path.py
    observation_request.py
    contradiction.py
```

실제 파일 분할은 구현 시점의 복잡도에 따라 조정 가능하다.

중요한 것은 개념적 책임 분리다.

---

# 41. CausalEvent 초안

```text
CausalEvent
    event_id
    world_id
    start_step
    end_step
    subject_ids
    event_type
    state_before
    state_after
    delta
    provenance
```

요구사항:

- immutable
- canonical()
- digest
- deterministic ordering
- stable serialization

---

# 42. CausalEdge 초안

```text
CausalEdge
    edge_id
    source_event
    target_event
    relation
    status
    conditions
    supporting_evidence
    contradicting_evidence
    confidence
```

confidence는 단일 숫자만 사용하지 않는 것도 고려한다.

예:

```text
evidence_strength
replication_count
intervention_support
counterfactual_support
```

로 분리 가능하다.

---

# 43. CausalPath 초안

```text
CausalPath
    path_id
    nodes
    edges
    total_delay
    boundary_conditions
    status
```

예:

```text
TemperatureRise
→ DiffusionIncrease
→ ConcentrationShift
→ MembraneStress
→ Division
```

---

# 44. InterventionDefinition 초안

```text
InterventionDefinition
    target
    operation
    value
    start_step
    duration
    scope
    control_constraints
```

예:

```text
target = temperature.region_12
operation = DELTA
value = -0.2
```

---

# 45. CounterfactualPair 초안

```text
CounterfactualPair
    baseline_world
    intervention_world
    shared_initial_state_digest
    intervention
    divergence_summary
    outcome_comparison
```

---

# 46. LatentVariableCandidate 초안

```text
LatentVariableCandidate
    candidate_id
    source
    target
    unexplained_interval
    residual_effect
    candidate_features
    observation_requests
    status
```

---

# 47. 상태 관리

B는 "진실"을 바로 선언하지 않는다.

추천 상태 계층:

```text
UNKNOWN
OBSERVED
CORRELATED
PROPOSED_CAUSE
UNDER_TEST
SUPPORTED
STRONGLY_SUPPORTED
CONTRADICTED
REJECTED
UNRESOLVED
```

단, 현재 B0의 `HypothesisStatus`와 충돌하지 않도록 실제 구현에서는 기존 공통 enum을 우선한다.

본 문서는 의미적 요구사항을 정의하며, 기존 확정 구현 계약을 임의로 변경하지 않는다.

---

# 48. 장기 메모리

B는 연구 결과를 장기적으로 축적해야 한다.

다음 두 종류를 분리하는 것이 좋다.

## Episode Memory

특정 실험의 상세 기록

## Knowledge Memory

여러 실험에서 살아남은 일반화된 관계

예:

Episode:

```text
World 17 / experiment 882에서
온도 -0.2 → 분열 감소
```

Knowledge:

```text
특정 막 두께 범위에서
온도 감소는 분열률 감소와 반복적으로 연결되며
개입 실험 12회 중 10회 지지됨.
```

---

# 49. 세계 간 일반화

B는 하나의 세계에서 발견한 결과를 모든 세계에 적용하면 안 된다.

예:

```text
World family A:
X → Y

World family B:
X does not affect Y
```

따라서 지식에는 적용 범위를 저장한다.

```text
domain
world_family
boundary_conditions
engine_version
```

---

# 50. A 엔진 버전 변화

A의 물리 엔진이 바뀌면 기존 B 지식이 그대로 유효하지 않을 수 있다.

따라서 모든 지식은 최소 다음과 연결한다.

```text
engine_version
physics_version
world_schema_version
```

버전이 바뀌면:

```text
VALID
NEEDS_REVALIDATION
OUTDATED
```

등의 상태를 고려한다.

---

# 51. 인간 개입

인간은 다음 권한을 가진다.

- 연구 목표 지정
- 자원 한계 설정
- 실험 중단
- 위험한 실험 차단
- A 기본 법칙 변경 승인
- B 결과 검토

하지만 인간이 결과를 원하는 방향으로 직접 수정하면 provenance가 깨진다.

수정이 필요한 경우 별도 entry로 기록한다.

---

# 52. B와 LLM

B가 반드시 LLM일 필요는 없다.

B는 구조적으로 다음 구성요소를 가질 수 있다.

```text
deterministic research core
+
causal graph engine
+
experiment planner
+
optional reasoning model
+
optional natural-language interface
```

LLM은 다음 역할에 제한적으로 사용할 수 있다.

- 후보 가설 생성
- 사람이 읽는 설명 작성
- 넓은 탐색 아이디어 생성
- 비정형 로그 요약

하지만 최종 연구 기록과 인과 증거는 deterministic data structure에 남긴다.

---

# 53. B가 모델에 의존하지 않아야 하는 부분

다음은 LLM이 없어도 동작해야 한다.

- 실험 식별자
- PredictionSeal
- canonical serialization
- digest
- Journal
- evidence 연결
- experiment result comparison
- hypothesis state transition
- provenance

즉 모델 교체가 연구 이력을 깨뜨리면 안 된다.

---

# 54. 생명 두뇌와 B의 서로 다른 진화

A 내부 두뇌는 진화해도 된다.

B는 반드시 생물학적 의미로 진화할 필요는 없다.

두 시스템 목적이 다르다.

```text
A 내부 두뇌:
살아남기 위한 적응

B:
세계를 더 정확하게 설명하기 위한 연구
```

나중에 B의 연구 전략 자체를 진화시키는 것은 별도 연구 주제로 분리한다.

---

# 55. 장기적으로 가능한 연구 루프

```text
A 실행
↓
B 관찰
↓
이상 현상 탐지
↓
후보 인과 경로 생성
↓
경쟁 가설 구성
↓
가장 정보가치 높은 실험 선택
↓
Prediction Seal
↓
A fork 생성
↓
개입
↓
실행
↓
결과 비교
↓
인과 그래프 업데이트
↓
설명되지 않은 부분 탐색
↓
새로운 관측 요청
↓
다시 A 실행
```

이 루프가 B의 장기 형태다.

---

# 56. 정보 가치 기반 실험 선택

후속 단계에서 실험은 단순 순서대로 실행하지 않아도 된다.

가설 A와 B를 가장 잘 구분하는 실험을 우선할 수 있다.

예:

```text
Experiment 1
A와 B 모두 같은 결과 예측

Experiment 2
A는 증가 예측
B는 감소 예측
```

Experiment 2의 정보 가치가 더 높다.

이 기능은 compute 자원을 줄이는 데 중요하다.

---

# 57. 계산량 관리

인과 추론은 매우 비싸질 수 있다.

따라서 단계적으로 계산한다.

```text
1차
cheap observational screening

2차
candidate ranking

3차
small intervention

4차
replication

5차
long-running counterfactual
```

모든 후보에 장시간 A simulation을 실행하지 않는다.

---

# 58. World Fork

반사실과 개입을 위해 A는 가능한 경우 state fork를 지원하는 것이 좋다.

```text
World State S
    ├─ Fork A
    ├─ Fork B
    └─ Fork C
```

각 fork는 동일한 상태 digest에서 시작한다.

이 기능이 없다면 완전히 동일한 조건 재현이 어려워질 수 있다.

---

# 59. 결정론과 자연적 다양성의 공존

결정론은 "세계가 항상 똑같아야 한다"는 뜻이 아니다.

seed와 초기 조건을 명시적으로 관리하면 다양성과 재현성을 동시에 얻을 수 있다.

```text
same state + same seed + same engine
→ same result

different seed
→ different result
```

이 구조가 B 연구에 적합하다.

---

# 60. B가 발견해야 하는 것은 숫자가 아니라 구조다

컴퓨터 내부에서는 모든 것이 결국 숫자와 비트로 저장된다.

그러나 B가 표현해야 하는 연구 대상은 단순 숫자 목록이 아니다.

예:

```text
A가 먼저 발생했다.
B가 특정 조건에서만 발생했다.
A를 제거하면 B가 사라졌다.
C를 고정하면 A의 효과가 사라졌다.
```

즉 B가 다루는 핵심은 **관계의 구조**다.

---

# 61. 프로젝트의 핵심 질문 재정의

B의 장기 핵심 질문은 다음과 같이 정의한다.

> 복잡한 세계에서 사람이 모든 사건과 확률을 사전에 정의하지 않아도,  
> 시스템이 실제로 발생한 사건들 사이에서 반복적·조건부·장기적 인과 구조를 발견하고,  
> 스스로 실험을 설계하여 그 구조를 검증할 수 있는가?

A 내부 생명 연구까지 포함하면 다음 질문으로 확장된다.

> 최소한의 물리적 세계와 진화 가능한 생명 두뇌를 제공했을 때,  
> 어떤 행동·구조·통신·지능이 자연적으로 나타나며,  
> B는 그 출현 과정을 인과적으로 설명할 수 있는가?

---

# 62. 구현 우선순위

## 지금

B0 Research Loop 완성

```text
observe
generate
design
seal
execute
compare
update
archive
```

## 다음

B1

- CausalEvent
- temporal chain
- InterventionDefinition
- CounterfactualPair
- causal evidence 연결

## 그 다음

B2

- CausalGraph
- CausalPath
- conditional causal edge
- competing hypothesis
- mediator testing

## 이후

B3

- hidden variable candidate
- derived feature
- adaptive observation
- long-term divergence
- butterfly path analysis

## 장기

B4

- information-gain experiment selection
- cross-world generalization
- meta-hypothesis
- research strategy optimization

---

# 63. B0 구현 중 지켜야 할 호환성 원칙

현재 B0에서 모든 후속 기능을 구현할 필요는 없다.

다만 다음을 막는 설계는 피한다.

- 한 가설이 단 하나의 변수만 가리킬 수 있게 고정
- 결과가 단일 scalar만 가능하도록 고정
- 시간 정보를 버리는 구조
- experiment가 한 world에서만 실행 가능하도록 고정
- provenance 없이 자연어 결과만 저장
- hypothesis와 evidence를 직접 문자열로만 연결
- Prediction Seal을 나중에 수정 가능하게 구현
- Research Journal의 과거 entry 수정 허용

즉 현재 구현은 작게 유지하되 **확장 방향을 닫아버리지는 않는다.**

---

# 64. 명시적 비목표

현재 단계에서 다음을 목표로 하지 않는다.

- AGI 구현
- 인간 수준 자연어 이해
- 완전한 과학 자동화
- 모든 인과관계의 완벽한 증명
- 현실 세계 수준 물리 시뮬레이션
- 생명 출현 보장
- 언어 출현 보장
- 문명 출현 보장

이 프로젝트는 결과를 보장하는 프로젝트가 아니라 **출현 가능성을 검증하는 실험 시스템**이다.

---

# 65. 최종 아키텍처 요약

```text
                         HUMAN
                           │
                research goal / limits
                           │
                           ▼
                    ┌─────────────┐
                    │      B      │
                    │ Researcher  │
                    └──────┬──────┘
                           │
       observe / intervene / compare / explain
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                         A                            │
│                                                      │
│ physics / matter / energy / environment / time      │
│                                                      │
│       ┌──────────────┐       ┌──────────────┐       │
│       │ organism 1   │       │ organism 2   │       │
│       │              │       │              │       │
│       │ sensors      │       │ sensors      │       │
│       │ brain        │       │ brain        │       │
│       │ memory       │       │ memory       │       │
│       │ actions      │       │ actions      │       │
│       └──────────────┘       └──────────────┘       │
│                                                      │
│             learning / evolution / signals           │
└──────────────────────────────────────────────────────┘
```

---

# 66. 한 문장 정의

**A는 세계를 실행하고, A 내부 두뇌는 그 세계에서 살아남으며, B는 그 과정에서 왜 그런 일이 일어났는지를 실험으로 밝혀내는 시스템이다.**

---

# 67. 구현 계약 메모

본 문서에서 설명한 후속 기능은 **현재 B0 구현 계약을 자동으로 변경하지 않는다.**

현재 구현 시에는 가장 최근에 확정된 B0 설계를 우선한다.

본 문서는 다음 목적을 가진다.

1. B의 장기 존재 이유 고정
2. 현재 B0가 잘못된 방향으로 축소되는 것을 방지
3. B1 이후의 기능 요구사항 기록
4. A / B / 생명 두뇌의 책임 경계 명시
5. 나비효과·숨은 변수·반사실·장기 인과 추적을 후속 핵심 기능으로 예약

과거 문서와 충돌할 경우 실제 구현 계약은 **가장 최근에 명시적으로 확정된 설계**를 우선한다.

---

# 68. 핵심 설계 체크리스트

향후 B 설계를 검토할 때 아래 질문에 답할 수 있어야 한다.

- [ ] B가 세계 사건을 직접 만들어내고 있지는 않은가?
- [ ] 관측과 개입이 구분되어 있는가?
- [ ] 실험 전 prediction이 봉인되는가?
- [ ] 동일 초기 상태의 counterfactual 비교가 가능한가?
- [ ] 사건의 시간 순서를 보존하는가?
- [ ] 단일 X→Y가 아니라 다단계 causal path를 표현할 수 있는가?
- [ ] 조건부 원인을 표현할 수 있는가?
- [ ] 설명되지 않는 관계를 "모름"으로 남길 수 있는가?
- [ ] 숨은 변수 후보를 표현할 수 있는가?
- [ ] 장기 divergence를 추적할 수 있는가?
- [ ] 경쟁 가설을 동시에 유지할 수 있는가?
- [ ] 반증된 가설을 기록에서 지우지 않는가?
- [ ] 모든 연구 결과가 provenance와 연결되는가?
- [ ] A 내부 생명 두뇌와 B가 분리되어 있는가?
- [ ] 현재 B0 범위와 후속 확장 범위가 혼합되지 않았는가?

---

# 69. 결론

B가 필요한 이유는 세계를 더 화려하게 만들기 위해서가 아니다.

세계가 충분히 복잡해질수록 인간이 모든 조건, 확률, 사건, 예외를 직접 정의하는 방식은 한계에 도달한다.

A가 실제 세계의 변화 자체를 담당하고, 생명 두뇌가 그 안에서 경험하고 적응하며, B가 그 과정에서 발생한 복합적인 인과관계를 연구한다면 세 역할이 명확히 분리된다.

B는 단순한 확률 시스템이 아니라 다음 능력을 향해 확장되어야 한다.

```text
관찰
→ 관계 탐색
→ 인과 가설
→ 개입
→ 반사실
→ 다단계 경로
→ 숨은 변수
→ 장기 파급효과
→ 인과 지식 축적
```

현재 B0 Research Loop는 이 구조의 출발점으로 유지한다.

후속 단계에서는 "더 많은 기능"을 무작정 붙이는 것이 아니라, **세계에서 실제로 일어난 일을 더 정확하게 설명하고 반증할 수 있는 연구 능력**을 중심으로 확장한다.
