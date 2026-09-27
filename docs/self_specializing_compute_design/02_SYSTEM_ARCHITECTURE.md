# 02. 시스템 아키텍처

## 1. 전체 구성

시스템은 크게 8개 계층으로 나눈다.

```text
[1] Frontend / Input
        ↓
[2] Canonical IR
        ↓
[3] Decomposer
        ↓
[4] Search / Candidate Generator
        ↓
[5] Equivalence Verifier
        ↓
[6] Cost Model / Benchmark
        ↓
[7] Backend Code Generator
        ↓
[8] Runtime Profile & Cache
```

---

## 2. Frontend

역할:

- 사용자가 제공한 계산식을 읽는다.
- 초기 버전은 범용 언어 전체가 아니라 작은 DSL을 권장한다.
- 이후 LLVM IR 등으로 확장할 수 있다.

초기 입력 예:

```text
fn f(a:i32, b:i32, c:i32) -> i32 {
    t0 = add(a, b)
    t1 = mul(t0, c)
    t2 = add(t1, t0)
    return t2
}
```

초기 버전에서 허용할 연산 예:

- ADD
- SUB
- MUL
- DIV
- MOD
- NEG
- AND / OR / XOR
- SHL / SHR
- 비교
- SELECT
- 제한된 LOOP

---

## 3. Canonical IR

모든 입력을 하나의 내부 표현으로 바꾼다.

조건:

- 연산 의미가 명확해야 한다.
- 정수 오버플로 규칙이 명확해야 한다.
- 부동소수점 모드가 명확해야 한다.
- 미정의 동작을 허용하지 않는 편이 초기 구현에 유리하다.
- 각 노드의 입력과 출력 타입이 고정되어야 한다.

예:

```text
%0 = ADD_I32 a, b
%1 = MUL_I32 %0, c
%2 = ADD_I32 %1, %0
RET %2
```

이 IR이 시스템의 기준 언어다.

---

## 4. Decomposer

긴 계산을 블록으로 나눈다.

분해 기준 예:

- 데이터 의존성
- 독립 서브그래프
- 반복 호출되는 부분
- 공통 부분식
- 메모리 접근 경계
- 함수 호출 경계
- 병렬화 가능성
- 특정 하드웨어 친화성

예:

```text
            ROOT
           /    \
          A      B
        /  \    / \
       C    D  E   F
```

A와 B가 독립적이면 동시에 계산할 수 있다.

---

## 5. Search / Candidate Generator

이 모듈은 "아이디어 생성기"다.

가능한 전략:

- 대수적 rewrite
- peephole rewrite
- e-graph 기반 동등식 탐색
- exhaustive search
- stochastic search
- genetic programming
- MCTS
- LLM/신경망 후보 제안
- 강화학습 기반 변환 선택
- superoptimization

중요:

> 이 모듈은 신뢰 경계 밖에 둔다.

즉 후보가 틀려도 시스템의 정확성이 깨지면 안 된다.

---

## 6. Equivalence Verifier

후보 G가 원본 F와 같은지 확인한다.

가능한 도구:

- SMT solver
- SAT solver
- symbolic execution
- theorem proving
- exhaustive enumeration
- translation validation
- interval proof
- bit-vector reasoning

초기 버전에서는 정수/고정소수점 같은 유한 상태 공간이 특히 유리하다.

---

## 7. Cost Model

정확한 후보가 여러 개일 경우 무엇이 더 좋은지 판단한다.

비용은 하나의 숫자가 아닐 수 있다.

예:

```text
cost =
    α * latency
  + β * instruction_count
  + γ * memory_traffic
  + δ * power_estimate
  + ε * code_size
```

하지만 초기에는 가중합보다 **다목적 결과를 그대로 저장**하는 편이 좋다.

예:

```text
candidate A
  latency: 40 ns
  instructions: 11
  memory_reads: 3

candidate B
  latency: 44 ns
  instructions: 8
  memory_reads: 1
```

사용 목적에 따라 선택이 달라질 수 있기 때문이다.

---

## 8. Backend

검증된 IR을 실제 코드로 만든다.

초기:

- Python reference
- C/C++
- LLVM IR

다음 단계:

- x86-64
- CUDA
- SIMD intrinsics

장기:

- FPGA RTL
- HLS
- CGRA
- custom accelerator

---

## 9. Runtime Profile & Cache

실제 실행 중 다음을 기록할 수 있다.

- 어떤 블록이 자주 호출되는가
- 입력 범위
- 입력 분포
- 평균 실행시간
- cache miss
- branch behavior
- GPU occupancy
- memory bandwidth
- 최적화 후보의 실제 성능

그리고 검증된 최적 구현을 캐시한다.

```text
Block hash
Hardware fingerprint
Semantic mode
Input-domain contract
        ↓
Verified implementation
```

하드웨어나 규칙이 바뀌면 캐시를 무효화한다.

---

## 10. 신뢰 경계

권장 구조:

```text
신뢰하지 않아도 됨:
- AI
- 탐색기
- heuristic
- 성능 예측기

신뢰해야 함:
- IR 의미 정의
- verifier
- code generator의 검증 경로
- 실행 시 contract 검사
```

이 구분이 시스템 전체의 핵심 안전장치다.
