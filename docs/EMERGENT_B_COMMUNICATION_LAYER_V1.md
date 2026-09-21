# B 내부 자연 발생 통신 계층 설계 v1

**상태:** 설계 초안  
**날짜:** 2026-09-21  
**목적:** B 내부의 여러 BrainAdapter가 사람이 정한 언어로 사고·소통하도록 강제하지 않고, 제한된 통신 환경 속에서 자체적인 표현과 통신 체계를 형성할 수 있도록 한다. 기존 B-Language는 제거하지 않고 외부 검증과 책임 추적을 위한 공용 경계 프로토콜로 유지한다.

---

## 1. 한 문장 목표

> B 내부의 뇌들은 어떤 언어를 써야 하는지 미리 지시받지 않는다. 대신 서로 협력해야 하지만 전체 내부 상태를 그대로 복사할 수 없는 환경을 만들고, 그 안에서 반복되는 성공·실패를 통해 유용한 통신 체계가 자연스럽게 형성되는지 관찰한다.

---

## 2. 기존 구조와의 관계

현재 B는 특정 Transformer, GNN, JEPA 또는 단일 신경망으로 정의되지 않는다.

B의 핵심 경계는 다음과 같다.

```text
사용자 요청
→ 자연어 해석
→ WorldIntent / WorldSpec / CausalRule
→ A 생성 및 실행

A의 상태·변화
→ BrainAdapter
→ 내부 표현
→ ClaimSet / EvidenceBridge / Prediction
→ BoundaryEvaluation
→ 검증된 결과와 실패 archive
```

기존 B-Language의 역할은 유지한다.

- `CapabilityManifest`
- `ObservationContract`
- `ClaimSet`
- `EvidenceBridge`
- `BoundaryEvaluation`
- 선택적 `WorldState`
- 선택적 `CausalMap`
- 선택적 `Prediction`
- 선택적 `PlanCandidate`
- 선택적 `MemoryLesson`

이 언어는 B 내부의 사고 언어가 아니다.

> B-Language는 서로 다른 인지 시스템이 외부에 제출하는 주장, 증거, 반증 조건, 능력과 관측 범위를 검증 가능하게 만드는 과학적 통신 프로토콜이다.

---

## 3. 새로 추가할 계층

기존 구조에 `Emergent Communication Layer`를 추가한다.

```text
                         A
                         │
                 Observation View
                         │
            ┌────────────┴────────────┐
            ↓                         ↓
        Brain A                   Brain B
      내부 표현 자유              내부 표현 자유
            │                         │
            └──── 제한 통신 채널 ─────┘
                         │
               반복적 협력·실패
                         │
             자연 발생 통신 체계
                         │
                Emergent Language
                         │
                      Bridge
                         │
              공식 B-Language 경계
                         │
      ClaimSet / EvidenceBridge / Evaluation
                         │
                    Exact A / 감사기
```

두 층을 명확히 분리한다.

### 내부 통신 계층

- 의미를 미리 지정하지 않는다.
- 문법을 미리 지정하지 않는다.
- 단어를 미리 지정하지 않는다.
- 특정 인코딩 방식을 강제하지 않는다.
- 여러 Brain 사이에서만 통신에 사용될 수 있다.
- 실패하거나 아무 언어도 형성되지 않아도 유효한 결과다.

### 외부 검증 계층

- 의미가 명시적이어야 한다.
- 주장과 반증 조건을 기계적으로 검사할 수 있어야 한다.
- A의 원시 사실과 B의 근사를 구분한다.
- 내부 통신 방식과 무관하게 같은 현실에 대한 주장에 책임을 묻는다.

---

## 4. 왜 언어를 직접 지정하지 않는가

사람이 B 내부 통신 언어를 직접 설계하면 모델이 세계를 분해하는 방식까지 사람이 고정할 위험이 있다.

예를 들어 우리가 다음 개념을 필수 어휘로 만들 수 있다.

```text
heat
water
bond
danger
resource
object
cause
```

그러면 Brain은 자연스럽게 세계를 이 개념 단위로 나누도록 압박받는다.

하지만 이것이 최선의 내부 표현이라는 근거는 없다.

다른 인지 시스템은 같은 세계를 다음처럼 전혀 다르게 압축할 수도 있다.

```text
현재 인간이 이름 붙이지 않은 반복 패턴
특정 변화 조합
공간적 대칭
에너지 흐름의 묶음
장기적으로 함께 변하는 상태 집합
```

따라서 내부 통신은 가능한 한 의미 중립적인 채널에서 시작한다.

---

## 5. 통신 채널의 최소 조건

자연 발생 언어가 필요해지려면 Brain끼리 전체 상태를 그대로 복사할 수 없어야 한다.

### 금지

```text
Brain A latent 전체 tensor → Brain B에 그대로 전달
Brain A 전체 memory → Brain B에 그대로 복사
A 원시 상태 전체 → 모든 Brain에 무제한 공개
```

이렇게 하면 언어가 필요하지 않다.

### 허용 예시

#### 이산 심볼 채널

```text
symbol vocabulary: 32 또는 64
message length: 최대 8~32 symbols
```

각 symbol에는 사전 의미가 없다.

```text
0
1
2
...
63
```

#### 연속 벡터 채널

```text
message dimension: 8 / 16 / 32
quantization: 선택적
bandwidth limit: 고정
```

#### 가변 길이 메시지

```text
START
anonymous symbols...
STOP
```

문법 규칙은 미리 정의하지 않는다.

---

## 6. 정보 병목

통신에는 비용 또는 한계를 둔다.

목적은 모델을 괴롭히는 것이 아니라 다음을 강제하기 위해서다.

> 상대에게 필요한 정보를 선택하고 압축해야 한다.

가능한 제약:

- 최대 메시지 길이
- 단위 시간당 전송량
- 사용할 수 있는 symbol 수
- message memory 크기
- 반복 전송 제한
- 지연 시간
- 일부 메시지 손실 실험
- 송신과 수신에 필요한 계산 예산

단, 비용을 A의 생존 보상이나 fitness와 섞지 않는다.

B 내부 실험의 계산 비용일 뿐 A의 물리 법칙이 아니다.

---

## 7. 의미는 사용에서 형성된다

예를 들어 `symbol 7`에 아무 의미도 주지 않는다.

하지만 반복적으로 다음 패턴이 나타날 수 있다.

```text
Brain A가 특정 상태를 관측
→ symbol 7 전송
→ Brain B가 특정 예측 또는 행동 전략 선택
→ 실제 A 검증에서 반복적으로 유효
```

그 결과 `7`이 특정 상태 또는 변화와 통계적으로 연결될 수 있다.

그러나 관찰자는 곧바로

```text
7 = 위험
```

이라고 선언하지 않는다.

대신 다음을 검사한다.

```text
어떤 상태에서 7이 사용됐는가
7을 제거하면 협력 성능이 어떻게 변하는가
7을 다른 symbol로 치환하면 어떤 변화가 있는가
수신자가 7을 받을 때 내부 상태가 어떻게 달라지는가
새 환경에서도 같은 역할을 유지하는가
```

의미는 이름이 아니라 기능적 관계로 분석한다.

---

## 8. 문맥과 조합

자연 발생 통신은 하나의 symbol과 하나의 뜻이 고정 대응할 필요가 없다.

예:

```text
7
7 3
5 7
7 7
```

각 메시지가 서로 다른 효과를 가질 수 있다.

따라서 다음이 자연스럽게 생기는지 관찰한다.

- 순서 민감성
- 반복
- 위치별 기능
- 조합적 의미
- 문맥 의존성
- 메시지 길이에 따른 의미 차이
- 같은 symbol의 다의적 사용
- 특정 symbol 조합의 고정화

`명사`, `동사`, `문장`, `문법`이라는 분류는 사후 분석 용어다.

세계 내부에 이를 직접 넣지 않는다.

---

## 9. 협력이 필요한 환경

언어는 단순히 채널이 있다고 생기지 않는다.

각 Brain이 서로 다른 정보를 가지고 있어야 한다.

### 예시 1 — 분할 관측

```text
Brain A:
좌측 영역만 관측

Brain B:
우측 영역만 관측

공통 과제:
다음 전체 변화 예측
```

둘이 통신하지 않으면 전체 상태를 알 수 없다.

### 예시 2 — 서로 다른 능력

```text
Brain A:
공간 구조 예측에 강함

Brain B:
시간적 변화 예측에 강함

공통 과제:
장기 trajectory 예측
```

### 예시 3 — 다른 기억

```text
Brain A:
최근 변화 기록 보유

Brain B:
장기 archive 일부 보유
```

### 예시 4 — 반사실 협력

```text
Brain A:
행동 후보 생성

Brain B:
위험 또는 실패 경로 탐색

통신 후:
PlanCandidate 제출
```

어떤 구조가 가장 효과적인지는 미리 정하지 않는다.

---

## 10. 새로운 Brain의 유입

자연 발생 통신 체계가 만들어진 뒤 새로운 Brain C를 투입할 수 있다.

```text
Brain A ↔ Brain B
      기존 통신 체계 L1
             ↓
          Brain C
```

관찰 질문:

- C가 L1을 학습하는가?
- A와 B가 C에게 맞춰 통신을 수정하는가?
- L1이 유지되는가?
- 새로운 L2가 형성되는가?
- 일부 표현만 유지되는가?
- 특정 Brain에만 통하는 방언형 구조가 생기는가?
- 기존 표현이 다른 의미로 재사용되는가?

결과가 없거나 기존 통신이 붕괴해도 실패한 실험이 아니다.

---

## 11. 언어의 세대 변화

여러 Brain 세대에서 같은 통신 채널을 유지하면 언어 자체의 변화도 추적할 수 있다.

```text
Generation 1
Brain A + Brain B
→ L1

Generation 2
Brain B + Brain C
→ L1 일부 유지 + 변화

Generation 3
Brain C + Brain D
→ L2

Generation N
→ 장기 언어 계보
```

기록할 것:

- symbol 사용 빈도
- message length
- symbol 조합
- 특정 상황과 message의 연결
- 이전 세대에서의 사용
- 의미 기능의 변화
- 사라진 표현
- 새 표현
- 새로운 Brain의 습득 속도

언어 진화를 성능 향상과 동일시하지 않는다.

언어는 더 길어지거나 비효율적으로 변할 수도 있다.

---

## 12. 공식 B-Language Bridge

자연 발생 언어를 외부 사실로 직접 해석하지 않는다.

Bridge가 필요하다.

```text
Emergent message
+ Brain internal state
+ current ObservationContract
↓
Bridge
↓
Prediction / ClaimSet / EvidenceBridge
```

Bridge의 역할:

- 내부 메시지를 직접 진실로 승격하지 않음
- 외부 검증 가능한 주장으로 변환
- 어떤 emergent message가 어떤 claim 생성에 기여했는지 기록
- 같은 메시지가 다른 상황에서 다른 claim을 만들 수 있음을 허용
- 해석 실패 시 `unknown` 또는 `untested`로 남김

Bridge도 검증 대상이다.

---

## 13. 자연 발생 언어와 B-Language 비교

둘은 경쟁 관계가 아니다.

| 항목 | Emergent Communication | B-Language |
|---|---|---|
| 목적 | Brain끼리 효율적으로 협력 | 외부 검증·책임·상호운용 |
| 의미 | 자연 발생 가능 | 명시적 |
| 문법 | 사전 미지정 | Schema가 존재 |
| 내부 표현 | 자유 | 경계 형식만 고정 |
| 검증 | 기능적 효과 분석 | 직접 기계 검증 |
| 변경 | 학습 중 변화 가능 | 버전 관리된 계약 |
| 인간 가독성 | 보장하지 않음 | 가능한 범위에서 유지 |
| 진실 판정 권한 | 없음 | Claim을 제출할 뿐, 최종 판정은 외부 검증 |

---

## 14. 비교 실험

### 실험 A — 사람이 만든 공용 언어

Brain끼리 직접 구조화된 B-Language만 사용한다.

### 실험 B — 자연 발생 통신

Brain끼리 제한된 anonymous channel을 사용한다.

최종 외부 출력만 B-Language로 변환한다.

### 실험 C — 혼합

Brain끼리는 emergent channel을 사용하되 일부 고수준 B-Language 메시지를 선택적으로 공유할 수 있다.

### 비교 항목

- 예측 정확도
- 반사실 계획 성능
- held-out 세계 일반화
- 새 Brain 적응 속도
- 메시지 bit 수
- message length
- compute cost
- 오류율
- adversarial exploit 취약성
- 표현 안정성
- 새로운 환경에서 의미 보존 여부

단일 총점으로 승자를 정하지 않는다.

각 축을 따로 보존한다.

---

## 15. 언어 효율성의 정의

단순히 메시지가 짧다고 효율적인 것은 아니다.

예:

```text
1 symbol
```

만 보내고 아무 정보도 전달하지 않으면 짧지만 쓸모없다.

따라서 최소한 다음을 같이 본다.

```text
전송 정보량
÷
검증된 협력 성능 향상
```

그리고 다음도 별도 기록한다.

- 메시지 압축률
- 수신자의 예측 개선량
- 오류 감소량
- 새 환경에서의 일반화
- 언어 습득에 필요한 경험량

정확한 단일 지표는 사전 실험 이후 정의한다.

---

## 16. 해석 가능성 실험

자연 발생 언어를 사람이 이해할 수 있다는 보장은 없다.

이를 강제하지 않는다.

대신 독립 분석 도구로 다음을 수행한다.

### Intervention

```text
message 일부 삭제
symbol 교체
순서 뒤집기
반복 제거
```

그리고 외부 claim과 성능 변화 측정.

### Counterfactual message

같은 A 상태에서 다른 메시지를 보냈을 때 수신자 행동 비교.

### Cross-context test

같은 symbol을 여러 환경에서 사용했을 때 기능 비교.

### New receiver test

훈련되지 않은 새 Brain이 통신 규칙을 얼마나 빨리 습득하는지 측정.

이런 실험을 통해 의미 후보를 분석한다.

---

## 17. 인지 구조와 언어의 공동 진화

장기적으로는 Brain 구조와 통신 체계를 완전히 독립된 것으로 볼 필요가 없다.

가능한 경로:

```text
Brain 구조 변화
→ 기존 언어 사용 방식 변화
→ 통신 병목 변화
→ 새로운 표현 등장
→ 새로운 표현이 Brain 학습에 영향
→ 다음 Brain 구조 변화
```

그러나 초기 구현에서는 동시에 모든 것을 진화시키지 않는다.

원인 분리가 불가능해지기 때문이다.

초기 단계에서는 Brain 구조를 고정하고 통신만 학습시킨다.

---

## 18. 단계별 구현 순서

### 단계 0 — 기존 B-Language 보존

- 현재 Schema와 BrainAdapter 계약 유지
- ClaimSet / EvidenceBridge / BoundaryEvaluation 유지
- 기존 Cognitive Map / ChangeGraph 결과와 호환성 유지

### 단계 1 — AnonymousChannel

구현:

```text
send(sender, receiver, message)
receive(receiver)
bandwidth_limit
message_length_limit
channel_log
```

symbol에 의미를 부여하지 않는다.

### 단계 2 — 두 Brain 분할 관측 benchmark

- 동일 A
- 서로 다른 ObservationContract
- 단독으로는 전체 문제 해결 불가
- 통신하면 정보 결합 가능

### 단계 3 — 통신 없는 baseline

먼저 통신 없이 동일 과제를 수행한다.

이 결과가 비교 기준이다.

### 단계 4 — 학습 가능한 sender / receiver

Brain 내부 표현은 자유.

초기 후보:

- GNN
- sparse Transformer
- JEPA-style latent model
- 작은 MLP baseline

### 단계 5 — Bridge

Emergent message가 외부 ClaimSet 생성에 어떤 영향을 미쳤는지 기록한다.

### 단계 6 — 통신 ablation

- message 제거
- symbol shuffle
- message length 감소
- channel noise
- sender 교체
- receiver 교체

### 단계 7 — 새로운 Brain 적응

기존 통신 체계에 미학습 Brain 투입.

### 단계 8 — 세대별 언어 변화

언어 계보와 기능 변화 기록.

### 단계 9 — 다중 Brain

2개에서 시작해 3개, 4개 이상으로 확장.

처음부터 사회 전체를 만들지 않는다.

---

## 19. 실패로 취급하지 않는 결과

다음은 모두 유효한 결과다.

- 언어가 생기지 않음
- 모든 symbol 사용이 붕괴
- 하나의 symbol만 반복
- 매우 긴 메시지가 필요
- Brain끼리 서로 다른 private code를 유지
- 새 Brain이 언어를 배우지 못함
- 언어가 세대마다 완전히 교체
- 사람이 해석할 수 없음
- B-Language 직접 통신보다 성능이 낮음
- 더 좋은 예측 대신 exploit code가 발생
- 특정 환경에서만 통하는 표현이 형성

실험 실패는 결과가 기대와 다른 것이 아니라 다음과 같은 경우다.

- 숨은 의미를 사람이 코드에 넣음
- test 정답이 통신 채널로 누출됨
- Bridge가 내부 메시지를 검증 없이 사실로 승격
- 결과를 본 뒤 채널 규칙 변경
- 실패 run 삭제
- 특정 언어가 생긴 run만 선택
- B가 A를 실행 중 수정

---

## 20. 공격적 검증

자연 발생 언어가 실제 정보를 전달하는지 검증해야 한다.

### Null test

메시지를 무작위 또는 고정 symbol로 바꿔도 성능이 같다면 언어 기능이 없는 것이다.

### Permutation test

symbol ID 전체를 일관되게 치환했을 때 성능이 유지되면 의미는 symbol 이름이 아니라 관계에 있다는 증거다.

### Receiver swap

수신자를 교체해 성능 붕괴 여부를 본다.

### Sender swap

송신자만 교체해 기존 언어의 공유 정도를 본다.

### Hidden leakage test

통신이 실제 관측이 아니라 benchmark ID나 seed 같은 숨은 정보에 의존하지 않는지 검사한다.

### Held-out semantics test

훈련에 없던 환경에서도 비슷한 메시지 기능이 유지되는지 본다.

---

## 21. 사용자 전용 계보

모든 통신 기록은 기존 A/B 사용자 전용 provenance와 연결한다.

기록:

```text
sender adapter version
receiver adapter version
ObservationContract digest
raw anonymous message
message digest
sender visible state digest
receiver visible state digest
resulting ClaimSet
BoundaryEvaluation
communication cost
training update reference
```

내부 reasoning trace를 강제로 저장하지 않는다.

통신과 외부 결과의 관계만 기록한다.

---

## 22. Knowledge Claim Registry와의 연결

언어에 대한 해석도 claim으로 취급한다.

예:

```text
Claim:
"symbol 7은 높은 열 구배를 표현한다"

type:
interpretation

status:
hypothesis

evidence:
- 해당 조건에서 사용 빈도 증가
- symbol 7 제거 시 예측 성능 감소

counterevidence:
- 다른 환경에서 같은 기능 미확인

next_test:
- held-out heat-gradient world
```

관찰자가 붙인 의미를 사실로 굳히지 않는다.

---

## 23. 장기 목표

최종적으로 보고 싶은 것은 특정 언어의 탄생 자체가 아니다.

질문은 더 크다.

> 서로 다른 인지 시스템이 제한된 경험과 통신 자원 아래에서 세계를 어떤 개념 단위로 나누고, 어떤 정보를 공유하며, 그 표현 체계가 새로운 환경과 새로운 인지 시스템에 어떻게 전달·변형되는가?

가능한 결과:

```text
관측
→ 내부 세계 표현
→ 통신 필요
→ 압축된 신호
→ 반복적 상호작용
→ 기능적 의미
→ 조합과 문맥
→ 새로운 Brain으로 전달
→ 표현 체계 변화
```

이 과정이 일어난다면 언어는 외부에서 주입한 기능이 아니라 B의 상호작용 과정에서 형성된 인지 도구가 된다.

---

## 24. 최종 원칙

1. B 내부 언어를 미리 정답으로 지정하지 않는다.
2. 언어가 필요해지는 정보 비대칭과 통신 병목을 만든다.
3. 내부 표현과 통신 방식은 자유롭게 둔다.
4. 전체 latent 복사는 허용하지 않는다.
5. 의미는 symbol 이름이 아니라 반복되는 기능과 인과 관계로 분석한다.
6. 문법과 개념은 사후 관찰 대상이지 엔진 변수가 아니다.
7. 기존 B-Language는 외부 검증 프로토콜로 유지한다.
8. Emergent Language가 직접 사실 판정 권한을 갖지 않는다.
9. Bridge 역시 검증 대상이다.
10. 실패·붕괴·비효율적 언어도 모두 보존한다.
11. 새로운 Brain의 유입으로 언어의 전달과 변화를 시험한다.
12. 자연 발생 언어가 인간 설계 언어보다 낫다고 미리 가정하지 않는다.
13. 단일 총점으로 통신 체계를 평가하지 않는다.
14. 언어 분석은 독립적인 intervention과 held-out 검증으로 수행한다.
15. A의 물리와 B의 통신 학습을 섞지 않는다.

---

## 25. 현재 프로젝트에서의 위치

```text
결정론 A 기반
→ B-Language 외부 경계
→ 독립 B 표현 후보
→ 학습형 BrainAdapter
→ Emergent Communication Layer
→ 두 Brain 통신 실험
→ Bridge와 외부 검증
→ 새 Brain 적응
→ 언어 계보
→ 장기적으로 인지 구조와 언어의 공동 진화
```

현재 단계에서 바로 필요한 것은 거대한 언어 진화 실험이 아니다.

첫 구현 목표는 작게 잡는다.

> **서로 다른 관측을 받은 두 작은 Brain이, 의미 없는 제한 채널을 통해 통신했을 때 통신 없는 baseline보다 held-out A 예측을 더 잘할 수 있는가?**

이 질문이 통과한 뒤에야 조합적 언어, 세대 변화, 새로운 Brain의 언어 습득으로 넘어간다.
