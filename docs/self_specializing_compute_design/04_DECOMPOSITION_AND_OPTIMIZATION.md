# 04. 계산 분해와 최적화 전략

## 1. 왜 분해가 중요한가

거대한 식 하나:

```text
F(x)
```

를 통째로 최적화하려 하면 탐색 공간이 너무 커진다.

따라서:

```text
F
├─ A
├─ B
├─ C
└─ D
```

로 나눈다.

분해의 목적은 단순히 병렬화가 아니다.

- 탐색 공간 축소
- 공통 계산 발견
- 하드웨어별 배치
- 캐시 가능성 발견
- 구간별 특화
- 검증 범위 축소

가 가능해진다.

---

## 2. 계산 그래프

예:

```text
t0 = a + b
t1 = t0 * c
t2 = t0 * d
t3 = t1 + t2
```

그래프:

```text
 a ─┐
    ├ ADD ─ t0 ─┬ MUL(c) ─ t1 ─┐
 b ─┘           └ MUL(d) ─ t2 ─┴ ADD → t3
```

이 표현만으로도 보이는 것이 있다.

- `a+b`는 한 번만 계산하면 된다.
- `t0*c`와 `t0*d`는 독립적이다.
- 두 MUL은 동시에 실행할 수 있다.

---

## 3. 최적화 종류

### O1 — Common Subexpression Elimination

반복되는 부분식을 한 번만 계산한다.

원본:

```text
(a+b)*c + (a+b)*d
```

개선:

```text
t = a+b
t*c + t*d
```

---

### O2 — Algebraic Rewrite

예:

```text
x*2
```

를 상황에 따라:

```text
x+x
```

또는 shift로 바꿀 수 있다.

단, 타입/overflow 의미론이 동일해야 한다.

---

### O3 — Constant Folding

```text
x * (3+5)
```

→

```text
x * 8
```

---

### O4 — Strength Reduction

비싼 연산을 싼 연산으로 바꾼다.

예:
- 특정 정수 곱셈 → shift/add
- 특정 나눗셈 → reciprocal/multiply 조건부 사용

---

### O5 — Parallel Decomposition

독립 블록을 동시에 실행한다.

```text
A ┐
B ├ parallel
C ┤
D ┘
```

총 work는 같아도 latency는 줄어들 수 있다.

---

### O6 — Vectorization

동일 연산을 여러 데이터에 동시에 적용한다.

```text
x0+x1
x2+x3
...
```

을 SIMD 형태로 묶는다.

---

### O7 — Memoization / Cache

같은 입력에 같은 계산을 반복하면 결과를 저장한다.

조건:
- 함수가 순수해야 함
- 캐시 lookup 비용이 계산 비용보다 작아야 함

---

### O8 — LUT

입력 공간이 작거나 제한되어 있다면 미리 결과를 계산한다.

```text
input → table → output
```

장점:
- 매우 빠를 수 있음

단점:
- 메모리 사용
- cache behavior
- 큰 입력 공간에는 불가능

---

### O9 — Piecewise Specialization

입력 범위를 나눈다.

```text
x ∈ D1 → G1
x ∈ D2 → G2
x ∈ D3 → G3
```

각 구간에서 더 단순한 정확 계산이 존재할 수 있다.

---

### O10 — Backend Specialization

같은 계산이라도 하드웨어에 따라 다르게 생성한다.

```text
CPU version
GPU version
FPGA version
```

---

## 4. 계층적 최적화

권장 반복:

```text
원본 그래프
  ↓
큰 블록 분해
  ↓
각 블록 최적화
  ↓
다시 합침
  ↓
새 그래프 분석
  ↓
블록 경계 재설정
  ↓
재최적화
```

한 번의 분해가 정답일 필요는 없다.

---

## 5. 위험: 지나친 분해

너무 잘게 쪼개면 다음 비용이 생긴다.

- 함수 호출
- synchronization
- thread launch
- GPU kernel launch
- CPU↔GPU 데이터 이동
- cache locality 악화
- 중간 값 저장 증가

따라서:

> 더 많이 쪼갠다고 항상 빨라지는 것은 아니다.

분해 자체도 비용 모델의 대상이어야 한다.

---

## 6. 병렬화 가능성 판정

A와 B가 동시에 계산 가능하려면 기본적으로:

```text
A가 B의 결과를 필요로 하지 않고
B가 A의 결과를 필요로 하지 않아야 한다.
```

즉 dependency graph가 중요하다.

---

## 7. Critical Path

전체 그래프에서 가장 긴 의존 경로가 최소 latency의 하한을 결정한다.

예:

```text
A → B → C → D
 \ E → F /
```

E와 F가 아무리 빨라도 A-B-C-D가 오래 걸리면 전체 완료 시간은 줄지 않는다.

따라서 단순히 "연산 수가 많은 블록"보다 **critical path에 있는 블록**을 먼저 최적화할 가치가 있다.

---

## 8. 최적화 우선순위 점수 예시

```text
priority =
    call_frequency
  × current_latency
  × optimization_headroom
```

자주 호출되고 느리며 개선 여지가 큰 블록을 먼저 탐색한다.
