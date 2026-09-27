# 07. 구현 로드맵

## Phase 0 — 의미론 고정

목표:
- 시스템이 무엇을 "같은 계산"이라고 보는지 고정

결정:
- 지원 타입
- overflow
- division
- shift
- comparison
- undefined behavior
- equivalence level

권장 시작:
- unsigned 8/16/32-bit integer
- bit-vector semantics

성공 조건:
- IR 명세가 완전히 문서화됨

---

## Phase 1 — 최소 IR + 실행기

구현:

```text
Parser
IR
Reference interpreter
```

지원 연산:
- ADD
- SUB
- MUL
- AND
- OR
- XOR
- SHL
- SHR
- SELECT

성공 조건:
- 같은 IR은 항상 같은 결과
- randomized differential tests 통과

---

## Phase 2 — 기본 Rewrite Optimizer

구현:
- constant folding
- algebraic simplification
- dead code elimination
- common subexpression elimination

성공 조건:
- 변환 전후 결과 검증
- 성능/연산 수 보고서 생성

---

## Phase 3 — Formal Verifier

구현:
- Z3 같은 SMT backend
- 원본 vs 후보 비교
- 반례 생성

성공 조건:

```text
equivalent
or
counterexample
```

둘 중 하나를 안정적으로 반환

---

## Phase 4 — Superoptimization

작은 블록 대상으로:

- enumerative search
- stochastic search

도입.

성공 조건:
- 사람이 작성한 baseline보다 짧은 정확 계산을 적어도 일부 benchmark에서 자동 발견

---

## Phase 5 — 계산 그래프 분해

구현:
- dependency graph
- independent subgraph detection
- critical path
- hot block identification

성공 조건:
- 전체 함수를 여러 검증 가능한 블록으로 자동 분할

---

## Phase 6 — Runtime Profiling

측정:
- call count
- latency
- input range
- repeated input
- branch ratio

성공 조건:
- hot block 우선 최적화

---

## Phase 7 — CPU Backend

구현:
- C/LLVM IR
- 실제 머신 성능 측정

성공 조건:
- IR 비용이 아니라 실제 wall-clock 성능으로 후보 비교 가능

---

## Phase 8 — SIMD Backend

구현:
- vectorization 후보
- intrinsic/codegen

---

## Phase 9 — GPU Backend

구현:
- CUDA kernel generation
- transfer cost model
- batch threshold

성공 조건:
- GPU가 실제로 이득일 때만 자동 선택

---

## Phase 10 — Learned Search Policy

탐색 이력으로:

```text
어떤 패턴에 어떤 변환이 잘 먹히는가
```

를 학습한다.

AI는 탐색 우선순위만 결정한다.

---

## Phase 11 — FPGA Prototype

작은 arithmetic kernel 하나를:

```text
IR
→ HLS/RTL
→ FPGA
```

로 변환.

이 단계까지 가면 "계산 방법을 하드웨어에 박는다"는 최초 아이디어를 실제로 검증할 수 있다.

---

## Phase 12 — Adaptive Runtime

최종적으로:

```text
실행
↓
관찰
↓
자동 최적화
↓
검증
↓
배포
↓
재사용
```

을 하나의 런타임에서 연결한다.

---

## 우선순위

중요도 순:

1. 의미론
2. 검증
3. 작은 블록 최적화
4. 실제 성능 측정
5. 자동 분해
6. 하드웨어 다양화
7. 학습 기반 탐색
8. FPGA

처음부터 FPGA를 만지면 프로젝트가 하드웨어 툴체인에 잡아먹힌다.
