# A 세계 계산기의 ‘꿈의 재질’ 설계 메모 v0

**상태:** 연구 아이디어 / 설계 제안. **미구현, 미승인.**  
**범위:** 사용자가 “기차의 재질은 무엇에 해당하나?”라고 질문한 지점부터 이어진 아이디어를 정리한다.  
**핵심 목적:** A 세계의 물리법칙은 바꾸지 않고, **A를 계산하는 실행기 내부의 숫자·자료형·표현 방식만 현실의 재료공학처럼 특화**하여 계산량과 메모리를 줄일 수 있는지 탐색한다.

---

## 0. 가장 중요한 구분

이 문서에서 말하는 “꿈의 재질”은 **A 세계 안에 존재하는 가짜 물질**이 아니다.

예를 들어 다음과 같은 것은 A의 정규 물리에는 넣지 않는다.

- 에너지를 스스로 증폭하는 물질
- 질량이나 관성을 마음대로 조절하는 물질
- 열역학 법칙을 어기는 영구기관성 물질
- 현실에 없는 임의의 물리 법칙

그렇게 하면 A는 현실 지구를 충실히 구현하는 세계가 아니라 새로운 허구 물리 세계가 된다.

여기서 말하는 꿈의 재질은 전혀 다른 것이다.

> **A 세계의 물리는 현실 그대로 유지한다.**  
> 대신 그 세계를 계산하는 컴퓨터 내부에서, 숫자를 표현하고 계산하는 방법은 현실의 금속·폴리머처럼 우리가 설계할 수 있다.

즉 “꿈의 열차 전용 물질”이 아니라:

> **꿈의 계산 전용 수치 재료**

를 만드는 아이디어다.

---

# 1. 현재 C1-B1 기관차의 “재질”

현재 C1-B1 코드를 현실의 기관차로 비유하면, 기차가 무거운 이유는 엔진 출력이 부족해서가 아니라 **부품 하나하나를 지나치게 튼튼하고 보수적인 재료로 만들었기 때문**에 가깝다.

## 1.1 FixedPoint = 정밀한 톱니가 깎인 선로/바퀴

예:

- 위치: `FX(96,48)`
- 운동량: `FX(96,80)`

컴퓨터 내부에는 실수 자체가 들어 있는 것이 아니라 **정수 raw 값**이 들어 있다.

예를 들어 위치 `x`는 대략 다음 형태다.

```text
x = raw / 2^48
```

즉 위치가 아무 실수나 되는 것이 아니라 `2^-48` 간격의 매우 촘촘한 격자에 놓인다.

장점:

- 같은 입력이면 같은 비트 결과
- 반올림 규칙이 명확함
- CPU/GPU 간 재현성을 만들기 쉬움
- 정수 연산으로 처리 가능

단점:

- 표현 범위가 제한됨
- 해상도가 고정됨
- 아주 작은 값과 아주 큰 값을 동시에 자유롭게 표현하기 어려움

범용 숫자로 보면 불편하지만 A의 결정론에는 유리하다.

---

## 1.2 Python BigInt = 엄청 두꺼운 특수강

일반 CPU 정수는 64비트처럼 크기가 고정되어 있다.

반면 Python 큰 정수는 필요한 만큼 자릿수가 커진다.

예:

```text
128 bit
256 bit
1024 bit
16384 bit
...
```

장점:

- 숫자가 커져도 잘라버리지 않음
- 정확한 계산을 계속할 수 있음

단점:

- 숫자가 커질수록 메모리 사용량 증가
- 곱셈/나눗셈 비용 증가
- 캐시 효율 악화
- GPU에 매우 부적합

즉 **부러지지는 않지만 점점 두꺼워지는 쇳덩어리**에 가깝다.

---

## 1.3 Fraction = 정확하지만 무거운 기어

`Fraction(1, 3)`은 `0.333333...`로 근사하지 않는다.

그냥:

```text
분자 = 1
분모 = 3
```

을 그대로 들고 다닌다.

장점:

- 정확함
- 반올림 오차가 없음

단점:

- 분자와 분모가 계속 커질 수 있음
- 곱셈/나눗셈 후 정규화 비용
- 최대공약수 계산 비용
- 일반적인 dyadic 숫자까지도 범용 유리수 구조로 처리하면 낭비가 큼

현실 비유로는 **아무 형태의 하중에도 견디도록 모든 부품을 초대형 볼트 체결 구조로 만든 것**과 비슷하다.

---

## 1.4 Interval arithmetic = 숫자 하나 대신 허용오차 전체를 들고 다니는 구조

일반 프로그램:

```text
힘 = 12.345
```

엄밀 구간 계산:

```text
12.344999998 <= 진짜 힘 <= 12.345000003
```

항상 `[lo, hi]` 두 값을 관리한다.

장점:

- 진짜 값을 구간 안에 가둘 수 있음
- 반올림 판정을 엄밀하게 할 수 있음
- 증명에 적합함

단점:

- 숫자 하나 대신 두 경계를 계산
- 매 연산마다 바깥쪽 반올림 필요
- 식이 복잡할수록 구간이 과도하게 넓어질 수 있음

현재 Checker V2가 사용하는 outward dyadic interval은 **진짜 값이 밖으로 빠지지 않도록 항상 넉넉하게 가공하는 안전 부품**이라고 보면 된다.

---

## 1.5 `exp()` 구간 계산 = 현재 가장 무거운 엔진 부품 중 하나

Ar-Ar potential에는 지수함수가 들어간다.

보통 프로그램은:

```python
math.exp(-x)
```

로 끝낼 수 있다.

하지만 엄밀한 계산에서는 `e^-x`가 어느 구간에 있는지 증명해야 한다.

그래서 Taylor 급수와 remainder bound를 사용한다.

```text
1 + x + x^2/2! + x^3/3! + ...
```

문제는 정밀도가 높아지면 필요한 항 수가 커질 수 있다는 것이다.

각 항도 큰 정수/유리수/구간으로 계산한다.

즉 현재 구조에서 가장 비싼 재질은 대체로:

1. 큰 정수
2. 정확 유리수
3. interval propagation
4. 엄밀한 exp 계산

쪽이다.

---

# 2. 왜 “현대식 기차”로 바꾸고 싶은가

현재 구조는 처음부터 속도를 극한으로 뽑으려고 만든 구조가 아니다.

오히려:

> **느리더라도 무엇이 맞는지 설명하기 쉬운 기준 실행기**

에 가깝다.

이는 초기에 중요하다.

처음부터 다음을 전부 넣으면:

- GPU kernel
- custom bigint
- RNS
- minimax polynomial
- lazy exact
- symbolic DAG
- 자동 표현 전환

무언가 틀렸을 때 어디서 틀렸는지 추적하기 어려워진다.

따라서 현재 C1-B1은 일종의 **기준 기관차(reference train)** 다.

미래의 고속 실행기는 이 기준 기관차와 결과를 비교해서 정확성을 확인해야 한다.

---

# 3. 첫 번째 꿈의 재료: Dyadic 특화 숫자

많은 값이 실제로 다음 꼴이라면:

```text
n * 2^-k
```

일반 Fraction을 쓸 이유가 줄어든다.

일반 Fraction:

```text
numerator / denominator
```

Dyadic:

```text
integer n
scale k
```

예:

```text
123456789 / 2^48
```

을 그냥:

```text
raw = 123456789
scale = -48
```

로 표현한다.

## 장점

- 분모가 항상 2의 거듭제곱
- 정규화가 단순
- bit shift로 스케일 조정 가능
- CPU 친화적
- GPU 친화적으로 만들 가능성
- outward rounding 구현이 쉬움

## 단점

다음 같은 값은 정확하게 표현할 수 없다.

```text
1/3
1/7
...
```

하지만 해당 kernel에서 그런 일반 유리수가 필요 없다면 이 단점은 사실상 의미가 없다.

이게 바로:

> **“음파에는 약한 비브라늄인데, 우리 환경에는 음파 공격이 없다.”**

라는 발상이다.

---

# 4. 두 번째 꿈의 재료: 필요할 때만 강해지는 Adaptive Exact Number

하나의 숫자가 항상 같은 표현을 사용할 필요는 없다.

예:

```text
128-bit dyadic
    ↓ 애매함
256-bit dyadic
    ↓ 더 애매함
512-bit dyadic
    ↓
BigInt interval
    ↓
arbitrary precision
    ↓
정말 필요하면 exact rational
```

평범한 계산에서는 가볍다.

반올림 경계처럼 위험한 지점에서만 무거워진다.

현실 비유:

> 평소에는 알루미늄처럼 가볍고, 충격이 오는 부분만 순간적으로 초고장력강으로 변하는 재료.

현재 C1-B1의 128 → 256 → … → 16384 정밀도 escalation이 이 철학의 초기형이라고 볼 수 있다.

미래에는 더 세밀하게:

- 전체 step 정밀도를 올리는 대신
- **문제가 생긴 연산 또는 변수만**
- 더 높은 정밀도로 승격

하는 구조를 연구할 수 있다.

---

# 5. 세 번째 꿈의 재료: RNS / Modular Arithmetic

## 5.1 기본 발상

거대한 정수 `N`을 그대로 들고 다니지 않고 여러 나머지로 분해한다.

```text
N mod p1
N mod p2
N mod p3
N mod p4
...
```

각 조각은 서로 독립적이다.

그래서:

```text
core 1 → mod p1
core 2 → mod p2
core 3 → mod p3
GPU thread 1 → mod p4
...
```

같이 병렬 계산하기 좋다.

## 5.2 장점

특히 다음 연산은 매우 잘 맞는다.

- 덧셈
- 뺄셈
- 곱셈
- 큰 정수 polynomial
- 대량 병렬 계산

## 5.3 치명적인 약점

다음은 불편해진다.

- 대소 비교
- 부호 판정
- 일반 나눗셈
- “0.5보다 큰가?” 같은 직접 비교
- 값의 일반적인 크기 확인

범용 숫자형으로는 큰 약점이다.

하지만 특정 A kernel이:

```text
곱셈
곱셈
덧셈
곱셈
덧셈
...
마지막에만 비교
```

형태라면 약점의 중요도가 크게 줄어든다.

즉 **특정 부품에서만 쓰는 복합재** 후보가 된다.

---

# 6. 네 번째 꿈의 재료: 로그 표현 같은 연산 특화 숫자

숫자 `x` 대신 `log(x)`를 저장하는 방식이 있다.

그러면:

```text
x * y
```

는:

```text
log(x) + log(y)
```

가 된다.

거듭제곱도 쉬워진다.

반면:

```text
x + y
```

가 매우 귀찮아진다.

따라서:

```text
곱셈 10000회
덧셈 3회
```

같은 kernel이라면 가치가 있을 수 있다.

전체 A에 쓰기보다 **곱셈 특화 부품**으로 생각해야 한다.

---

# 7. 다섯 번째 꿈의 재료: Symbolic DAG / 식 구조 유지

매 연산마다 즉시 숫자를 계산하지 않고 식 구조 자체를 유지한다.

예:

```text
x*x + 2*x*y + y*y
```

를 그대로 계산하지 않고:

```text
(x+y)^2
```

형태로 유지할 수 있다.

또:

```text
a/b + c/b
```

를 두 Fraction으로 만들지 않고:

```text
(a+c)/b
```

로 유지할 수 있다.

## 장점

- 중간 수 폭증 감소 가능
- 반복 구조 공유 가능
- 공통 부분식 제거 가능
- 동일 계산 재사용 가능

## 단점

- 식 그래프가 계속 커질 수 있음
- 비교/반올림을 위해 결국 수치화해야 함
- simplification 자체가 비싸질 수 있음
- 잘못 설계하면 숫자 폭증 대신 “식 폭증”이 생김

따라서 **반복 구조가 강한 kernel**에서만 가치가 있다.

---

# 8. 여섯 번째 꿈의 재료: exp 전용 현대식 엔진

현재처럼 Taylor 항을 길게 계산하는 구조는 증명하기는 쉽지만 비쌀 수 있다.

미래에는 다음 구조를 연구할 수 있다.

```text
x
↓
range reduction
↓
작은 r로 변환
↓
certified polynomial / rational approximation
↓
엄밀한 오차 상한
↓
e^x enclosure
```

예:

```text
e^x = 2^k * e^r
```

처럼 `r`을 작은 범위로 줄인다.

그 작은 구간에서:

- minimax polynomial
- rational approximation
- table + correction
- certified polynomial

등을 사용할 수 있다.

핵심은 빠른 근사 자체가 아니라:

> **최대 오차가 정확히 얼마 이하인지 증명할 수 있어야 한다.**

일반적인 Taylor 10000항 대신:

```text
range reduction
+
20~30차 다항식
+
엄밀 error bound
```

같은 구조가 가능하다면 큰 이득이 될 수 있다.

---

# 9. “아이언맨 나노테크”식 숫자

가장 흥미로운 장기 구조는 **하나의 만능 자료형**이 아니라 필요에 따라 표현을 바꾸는 시스템이다.

예:

```text
                     ┌─ Fixed Dyadic
                     │
A Numeric Object ────┼─ Dyadic Interval
                     │
                     ├─ RNS
                     │
                     ├─ BigInt
                     │
                     ├─ Rational
                     │
                     └─ Symbolic DAG
```

상황에 따라:

```text
평범한 이동
→ Fixed Dyadic

대량 곱셈
→ RNS

반올림 경계
→ Dyadic Interval

초고정밀 필요
→ BigInt / arbitrary precision

정확 유리수가 꼭 필요
→ Rational

반복되는 식 구조
→ Symbolic DAG
```

로 바뀐다.

현실의 나노 슈트 비유로 보면:

> 평소에는 얇고 가볍다가 충격을 받는 부위만 두꺼워지고, 필요가 끝나면 다시 얇아지는 갑옷.

---

# 10. 그러나 “변신 비용”이 있다

표현 변환은 공짜가 아니다.

예:

```text
dyadic
→ RNS
→ dyadic
→ RNS
→ dyadic
```

를 매 연산마다 반복하면 계산보다 변환 비용이 더 커질 수 있다.

따라서 중요한 것은:

> **한 표현으로 오래 머무르는 계산 구간(kernel)이 있는가?**

이다.

좋은 경우:

```text
RNS로 한 번 변환
↓
수천~수백만 연산
↓
마지막에 한 번 복원
```

나쁜 경우:

```text
연산 1회
↓
표현 변환
↓
연산 1회
↓
다시 변환
```

즉 “나노테크”는 멋져 보여도 **옷 갈아입는 시간이 실제 전투보다 길면 실패**다.

---

# 11. A에는 범용 숫자형이 필요하지 않을 수 있다

A는 범용 수학 프로그램이 아니다.

예를 들어 C1-B1 force 계산은 대략 다음 패턴을 반복한다.

```text
R^2
sqrt
R의 거듭제곱
exp(-λR)
고정 rational polynomial
force
impulse
rounding
```

그렇다면 다음 기능을 전부 지원하는 범용 숫자형이 필요하지 않을 수 있다.

- 일반 삼각함수
- 복소수
- 임의 행렬
- 일반 symbolic algebra
- 임의 transcendental 함수
- 모든 종류의 division

대신 C1-B1 또는 미래 force kernel에 필요한 것만 지원하는 수치 재료를 만들 수 있다.

예:

## `AForceNumber` 가상 사양

지원:

- `+`
- `-`
- `×`
- power-of-two scale
- 특정 polynomial
- 특정 exp enclosure
- rounding-bound 판정

지원하지 않음:

- 일반 trig
- complex
- arbitrary matrix
- 임의 log
- 임의 symbolic calculus

범용성은 형편없지만 해당 kernel에는 필요한 것이 전부 있다.

이것이 계산 세계의 진짜 **비브라늄**에 가장 가깝다.

---

# 12. “아무짝에도 쓸모없는 단점”을 의도적으로 받아들이는 설계

이 접근의 핵심은 약점을 없애는 것이 아니다.

오히려:

> **A가 사용하지 않는 능력은 과감하게 버린다.**

예:

### 재료 A

장점:

- add/mul 초고속
- GPU 병렬화 쉬움
- exact

단점:

- 비교 느림
- division 불편

A의 해당 kernel이 비교를 마지막에 한 번만 한다면 좋은 재료가 될 수 있다.

### 재료 B

장점:

- 비교와 rounding 매우 빠름
- dyadic exact

단점:

- `1/3`을 정확히 저장 못함

해당 kernel에 `1/3`이 필요 없다면 문제 없음.

### 재료 C

장점:

- polynomial 계산 엄청 빠름

단점:

- 일반 transcendental 함수 없음

force kernel이 고정 함수만 쓴다면 문제 없음.

즉 재료 설계에서 중요한 질문은:

> “이 자료형이 무엇을 못 하는가?”

가 아니라:

> **“못 하는 기능을 A의 해당 계산 구간이 실제로 요구하는가?”**

이다.

---

# 13. A Numeric Foundry 개념

하나의 만능 숫자형을 만들기보다 **재료 창고**를 만드는 방향도 가능하다.

```text
A Numeric Foundry

├─ Fixed Dyadic
│  빠른 일반 계산
│
├─ Dyadic Interval
│  엄밀한 반올림 판정
│
├─ RNS / Modular
│  대량 add/mul
│
├─ BigInt
│  거대한 exact 정수
│
├─ Rational
│  정말 필요한 exact fraction
│
├─ Symbolic DAG
│  식 구조 공유/보존
│
└─ Certified Function Kernels
   exp, sqrt 등 특수함수 전용
```

각 계산 kernel이 필요한 재질을 선택한다.

---

# 14. CPU와 GPU 역할도 재료에 따라 달라진다

GPU는 모든 수학을 잘하는 기계가 아니다.

GPU가 좋아하는 것:

- 같은 연산을 대량으로 반복
- 고정폭 숫자
- 규칙적인 메모리 접근
- branch가 적음
- 독립적인 작은 계산이 많음

GPU가 싫어하는 것:

- 제각각 다른 BigInt 크기
- 긴 Fraction 정규화
- gcd
- 한 thread는 128비트, 다른 thread는 17000비트
- 각 입력마다 다른 Taylor 항 수
- 복잡한 branch

따라서 미래 구조 후보:

```text
GPU
→ regular fixed-width / dyadic / RNS fast path

CPU
→ arbitrary precision
→ prover
→ checker
→ rare difficult cases
```

GPU는 “더 강한 CPU”가 아니라 **수천 개의 작은 모터**에 가깝다.

재료도 그 구조에 맞춰야 한다.

---

# 15. Fast candidate + Exact verifier

가장 중요한 장기 패턴 중 하나는 다음이다.

```text
빠른 계산기
→ 후보를 제안

정확한 작은 검증기
→ 후보가 정말 맞는지 확인
```

예:

```text
float:
"Taylor 137항 정도면 될 것 같음"

exact certifier:
"137항이 실제 조건을 만족함"

YES
→ 사용

NO
→ exact fallback
```

빠른 계산기는 틀려도 된다.

단:

> **틀린 후보가 세계 상태로 들어가면 안 된다.**

이 원칙은 현재 Point Prover / Checker 구조와도 잘 맞는다.

---

# 16. “꿈의 재질”과 Exact Aggregate(EA)의 공통 철학

앞서 나온 EA와 이 숫자 재질 아이디어는 구조적으로 비슷하다.

## 세계 상태 수준

```text
많은 원자
↓
Exact Aggregate
↓
필요하면 다시 펼침
```

## 숫자 수준

```text
무거운 exact representation
↓
더 싼 specialized representation
↓
필요하면 더 강한 representation으로 승격
```

공통 원칙:

> **정보를 버려서 싸게 만드는 것이 아니라, 같은 정보를 더 싼 표현으로 바꿀 수 있는지 찾는다.**

이 점이 매우 중요하다.

---

# 17. 진짜 한계: 정보량 자체는 마법으로 없앨 수 없다

소프트웨어에서는 현실에 없는 “재료 변신”이 가능하다.

하지만 다음은 동시에 얻을 수 없다.

```text
무한 정밀도
+
O(1) 저장공간
+
O(1) 연산
+
완전 exact
+
모든 연산 지원
+
완벽한 병렬화
```

정확한 값 자체가 100만 비트의 정보를 필요로 한다면 그 정보를 완전히 64비트에 넣을 수는 없다.

따라서 우리가 노리는 것은 **정보 자체를 없애는 마법**이 아니라:

- 반복 구조 제거
- 불필요한 범용 기능 제거
- 공통 분모 공유
- 공통 식 공유
- 필요한 순간에만 정밀도 확대
- kernel별 최적 표현
- 병렬 가능한 표현
- 증명 가능한 approximation

같은 구조적 절감이다.

---

# 18. 근본 전제 점검

이 아이디어가 가치 있으려면 먼저 확인해야 한다.

## 18.1 해결하려는 문제가 실제 문제인가?

현재 C1-B1에서 큰 비용은 실제로:

- arbitrary precision
- Fraction
- interval propagation
- exp enclosure
- high-precision escalation

등에 집중되어 있다.

따라서 수치 표현을 특화하는 연구는 문제와 직접 연결되어 있다.

그러나 C1-B1 전체가 끝나기도 전에 전면 교체를 시작하면 안 된다.

현재 기준 실행기가 먼저 필요하다.

---

# 19. 확장하면 어디서 깨지는가

가장 위험한 부분들:

## 19.1 표현 전환 폭발

```text
A → B → C → A → B
```

가 너무 자주 일어나면 변환 비용이 이득을 삼킨다.

## 19.2 메타데이터 폭발

adaptive number 하나가:

- 현재 표현
- error bound
- provenance
- scale
- residues
- conversion history

를 너무 많이 들고 다니면 작은 숫자 하나가 구조체 괴물이 된다.

## 19.3 분기 폭발

GPU에서 숫자마다 서로 다른 표현으로 갈라지면 warp divergence가 심해질 수 있다.

## 19.4 검증 복잡도 폭발

자료형 종류가 6개이고 변환이 20종이면:

> 값이 맞는가?

보다:

> 모든 변환 조합이 맞는가?

를 시험하는 비용이 더 커질 수 있다.

## 19.5 유지보수 폭발

A 세계가 아니라 numeric infrastructure 자체가 프로젝트의 대부분이 될 위험이 있다.

---

# 20. 숨은 비용

이 구조의 숨은 비용은 성능만이 아니다.

- conversion 비용
- certificate 형식 증가
- checker 복잡도 증가
- CPU/GPU 코드 이중화
- 저장 포맷 버전 관리
- cache identity 확대
- 테스트 조합 폭증
- 디버깅 난이도
- 새로운 bug class
- 미래 모델 변경 시 migration 비용

따라서 “새 숫자형이 빠르다” 하나만으로 채택하면 안 된다.

---

# 21. 더 싼 대안 먼저

새 자료형을 만들기 전에 다음을 먼저 비교해야 한다.

1. 기존 식 재배열만으로 충분한가?
2. Fraction 대신 dyadic만 바꾸면 충분한가?
3. exp 알고리즘만 개선하면 대부분의 비용이 사라지는가?
4. 캐시로 반복 계산을 줄이는 것이 더 싼가?
5. CPU bigint 라이브러리를 바꾸는 것만으로 충분한가?
6. 고정폭 128/256비트 fast path만 추가해도 충분한가?
7. GPU에 옮기지 않고 SIMD만 써도 충분한가?

즉 처음부터 “A Numeric Foundry” 전체를 만들지 않는다.

---

# 22. 성공 기준

이 연구는 멋있어 보이는 것만으로 성공이 아니다.

최소한 다음을 측정해야 한다.

## 정확성

- reference executor와 normalized result 동일
- rounding decisions 동일
- 필요 시 event history 동일
- certificate 검증 가능

## 속도

- wall time
- CPU time
- GPU time
- conversion time
- verifier time

## 메모리

- peak RAM
- VRAM
- per-number metadata

## 확장성

- precision 증가 시 비용
- particle 수 증가 시 비용
- thread/core/GPU scaling

## 유지보수

- 코드량
- trusted core 크기
- 테스트 수
- 새 버그 표면

---

# 23. 폐기 기준

다음이면 과감히 버린다.

- 변환 비용이 연산 절약보다 큼
- 정확성을 검증하기 위해 원래 계산을 거의 다시 해야 함
- trusted core가 너무 커짐
- GPU branch divergence가 이득을 잡아먹음
- small benchmark만 빠르고 실제 A kernel에서 이득 없음
- 메모리 metadata가 절약분을 상쇄
- 결과 동일성을 설명하기 어려움
- 구현 복잡도로 다른 A 작업이 장기간 지연됨

---

# 24. 추천 연구 순서

이 아이디어는 C1-B1이 끝난 뒤 바로 모든 것을 구현하는 방식이 아니라, 작은 실험으로 죽이거나 살리는 것이 좋다.

## 단계 1: 비용 프로파일

먼저 실제 A kernel에서 시간을 어디에 쓰는지 측정한다.

예:

```text
Fraction normalization
BigInt multiplication
exp enclosure
sqrt
interval rounding
certificate serialization
checker
```

가 각각 몇 %인지 본다.

가장 큰 병목부터 공격한다.

---

## 단계 2: Dyadic 전용 prototype

Fraction을 전부 없애지 않는다.

특정 경로 하나에서만:

```text
Fraction
vs
Dyadic
```

을 비교한다.

정확도는 동일해야 한다.

---

## 단계 3: exp 전용 modern kernel

현재 Taylor 방식과:

```text
range reduction + certified polynomial
```

을 비교한다.

검증기 구조는 가능한 한 단순하게 유지한다.

---

## 단계 4: fixed-width fast path

128/256비트 안에서 해결되는 대부분의 입력을 매우 빠르게 처리한다.

실패하면 기존 arbitrary precision 경로로 보낸다.

---

## 단계 5: RNS 실험

add/mul 비율이 높은 kernel 하나만 선택한다.

전체 시스템에 넣지 않는다.

변환 비용까지 포함해서 실제 이득을 본다.

---

## 단계 6: Adaptive Numeric prototype

여러 표현을 자동 전환한다.

단, 처음에는 2개만 사용한다.

예:

```text
Fixed Dyadic
↔
Arbitrary Dyadic
```

그다음 필요할 때만 확장한다.

---

## 단계 7: GPU 적합성

GPU에 올릴 수 있는 regular kernel만 선별한다.

Prover/Checker/arbitrary precision 전체를 억지로 GPU로 옮기지 않는다.

---

# 25. EA와 결합했을 때의 장기 그림

장기적으로 A가 커진다면 두 층의 압축/특화가 동시에 필요할 수 있다.

```text
A 세계
│
├─ 세계 상태 수준
│   └─ Exact Aggregate
│
└─ 수치 계산 수준
    └─ Adaptive / Specialized Exact Numeric
```

그리고 실행 장치는:

```text
regular bulk
→ GPU fast path

rare difficult
→ CPU exact path

truth decision
→ small independent checker
```

형태가 될 수 있다.

중요:

> 이것은 현재 승인 구조가 아니라 장기 후보 아키텍처다.

---

# 26. 현재 C1-B1과의 관계

현재 C1-B1을 당장 갈아엎지 않는다.

현재 구조는 다음 역할을 한다.

> **느리지만 믿을 수 있는 기준 실행기**

새로운 수치 재료는 반드시 이 기준과 비교되어야 한다.

따라서:

```text
현재 C1-B1
→ 기준선 확립

그 뒤
→ 새로운 numeric material prototype

비교
→ 정확히 같음?

YES
→ 성능 비교

NO
→ 탈락
```

순서가 맞다.

---

# 27. 중요한 설계 원칙

## 27.1 물리와 계산 재료를 분리한다

새 numeric representation이 물리 결과를 바꾸면 안 된다.

## 27.2 빠른 계산은 후보를 만들 수 있다

float, heuristic, GPU fast path는 후보를 만들 수 있다.

## 27.3 최종 판정은 엄밀한 경로가 한다

후보가 틀려도 세계 상태가 틀리면 안 된다.

## 27.4 필요 없는 기능은 버릴 수 있다

단, 해당 kernel이 정말 그 기능을 요구하지 않는다는 근거가 필요하다.

## 27.5 범용성보다 목적 적합성

A를 계산하기 위한 재료이지, 모든 프로그램을 위한 숫자형이 아니다.

---

# 28. 비유로 요약

현재 기관차:

```text
차체     = BigInt
기어     = Fraction
서스펜션 = Interval
엔진     = Ar-Ar potential
터보     = Taylor exp
변속기   = certified order selector
ECU      = Runtime Wrapper
검사장비 = Checker V2
창고     = Proof Cache
```

미래 후보:

```text
차체      = Fixed/Dyadic
고하중 축  = BigInt
복합재     = RNS
충격부     = Interval
나노 갑옷  = Adaptive Representation
고성능 터보 = Certified Polynomial exp
대량 모터  = GPU
특수정비반 = CPU arbitrary precision
검사관     = small exact checker
```

---

# 29. 가장 중요한 한 문장

> **A의 물리법칙을 바꾸는 마법 재료를 만들자는 것이 아니라, A가 실제로 사용하는 계산 패턴에만 특화된 ‘결함 많은 대신 필요한 성능에 몰빵한 수치 재료’를 만들 수 있는지 연구한다.**

범용 계산에서 치명적인 단점이라도 A가 그 기능을 사용하지 않는다면 단점이 아닐 수 있다.

그게 “비브라늄”, “나노테크”, “텅스텐급 강도의 고무 나사” 비유의 실제 기술적 의미다.

---

# 30. 상태 정리

**현재 상태:**

- 아이디어/연구 후보
- 구현 안 됨
- C1-B1 현 구조 변경 없음
- A의 물리법칙 변경 없음
- Exact Aggregate와 별도이지만 철학적으로 연결됨

**현재 하지 말 것:**

- C1-B1 기준 실행기 폐기
- 검증 전 새 numeric core를 정규 A에 사용
- GPU를 이유 없이 모든 계산에 사용
- approximate fast path 결과를 exact처럼 취급
- “가벼워 보인다”는 이유만으로 전체 아키텍처 교체

**C1-B1 이후 가장 먼저 할 일:**

> 실제 profiler를 통해 어떤 수치 재료가 가장 많은 비용을 먹는지 측정하고, 가장 큰 병목 하나를 대상으로 작은 prototype을 만들어 기존 기준 실행기와 정확성·속도·메모리를 비교한다.

---

# 31. 임시 이름 후보

전체 개념:

- **A Numeric Foundry**
- **Adaptive Exact Numeric**
- **Specialized Exact Materials**
- **A-Numeric Material System**

세계 수준 묶음:

- **EA = Exact Aggregate**

수치 수준 후보:

- **AExact**
- **AForceNumber**
- **Adaptive Exact Representation**

이름은 아직 확정하지 않는다. 개념 검증이 먼저다.
