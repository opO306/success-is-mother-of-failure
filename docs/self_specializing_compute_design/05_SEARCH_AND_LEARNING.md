# 05. 탐색과 학습

## 1. AI는 무엇을 학습해야 하는가

이 시스템에서 AI의 핵심 역할은:

> 정답을 근사하는 것이 아니라 더 좋은 계산 방법의 후보를 제안하는 것

이다.

---

## 2. 탐색기 역할

입력:

```text
원본 IR
동등성 규칙
하드웨어 정보
비용 목표
입력 범위
```

출력:

```text
후보 IR 1
후보 IR 2
후보 IR 3
...
```

후보는 틀려도 된다.

검증기가 차단한다.

---

## 3. 탐색 방법

### S1 — Rewrite Rules

사람이 정의한 규칙:

```text
x + 0 → x
x * 1 → x
```

가장 단순하고 안전하다.

---

### S2 — Equality Saturation

가능한 동등 표현을 하나씩 파괴적으로 선택하지 않고, 많은 표현을 함께 유지한 뒤 비용이 낮은 식을 찾는다.

장점:
- 초기에 잘못된 선택을 해 다른 최적화를 놓치는 문제를 줄일 수 있다.

---

### S3 — Enumerative Search

가능한 작은 프로그램을 전부 만들어 본다.

짧은 블록에는 강력하다.

단점:
- 탐색 공간 폭발

---

### S4 — Stochastic Search

무작위 변환을 반복하면서 좋은 후보를 찾는다.

장점:
- 사람이 예상하지 못한 표현을 찾을 가능성

단점:
- 재현성/탐색 비용 관리 필요

---

### S5 — Genetic Programming

프로그램을 개체로 보고:

- mutation
- crossover
- selection

을 반복한다.

---

### S6 — Neural Proposal Model

신경망은:

```text
현재 IR
→ 유망한 변환 제안
```

만 한다.

채택 여부는 verifier가 결정한다.

---

### S7 — LLM Proposal

LLM도 동일하게 후보 제안기로 사용할 수 있다.

다만 신뢰하지 않는다.

```text
LLM 제안
   ↓
IR parser
   ↓
verifier
```

를 반드시 거친다.

---

## 4. 학습 데이터

시스템이 축적할 수 있는 데이터:

- 원본 블록 형태
- 적용한 변환
- 검증 성공/실패
- 반례
- 성능 향상
- 하드웨어 종류
- 입력 분포
- 실패 원인

예:

```text
Pattern P
Transformation T
Hardware H
Domain D
Result:
  verified = true
  speedup = 1.82x
```

이 데이터는 이후 탐색 우선순위를 개선하는 데 사용한다.

---

## 5. 중요한 구분

다음 두 방식은 다르다.

### 근사 학습

```text
NN(x) ≈ F(x)
```

### 계산법 탐색

```text
AI proposes G
Verifier proves/checks G ≡ F
```

이 설계는 두 번째가 기본이다.

---

## 6. 자기 특화 루프

```text
실행
 ↓
관찰
 ↓
hot block 발견
 ↓
후보 탐색
 ↓
검증
 ↓
benchmark
 ↓
채택
 ↓
다음 실행 데이터 축적
 ↓
탐색 정책 개선
```

이 과정을 반복한다.

---

## 7. 탐색 예산

탐색은 공짜가 아니다.

따라서 블록마다 예산을 둔다.

예:

```text
max_candidates = 100000
max_solver_time = 5 s
max_search_time = 60 s
```

실제 절약되는 실행 비용보다 탐색 비용이 더 크면 의미가 없다.

단, 매우 자주 반복되는 계산은 한 번 비싸게 최적화해도 장기적으로 이득일 수 있다.

---

## 8. 탐색 결과의 수명

최적화 결과에는 조건을 붙인다.

```text
semantic_mode
hardware_id
compiler_backend_version
domain_contract
```

이 중 하나가 바뀌면 재검증 또는 재탐색한다.
