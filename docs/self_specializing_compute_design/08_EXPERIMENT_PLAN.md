# 08. 첫 프로토타입 실험 계획

## 1. 실험 질문

첫 버전은 거대한 목표를 증명하려 하지 않는다.

다음 세 질문만 검증한다.

### Q1
원본 계산과 정확히 같은 더 짧은 계산을 자동으로 찾을 수 있는가?

### Q2
긴 계산을 분해했을 때 전체 탐색보다 더 효율적으로 최적화할 수 있는가?

### Q3
정확성 검증과 성능 측정을 분리한 구조가 실제로 동작하는가?

---

## 2. 실험 대상

처음에는 작은 정수 함수 50~100개를 만든다.

예:

```text
f1(x,y) = ...
f2(x,y,z) = ...
```

유형:

- 산술
- bitwise
- 조건식
- 반복되는 부분식
- 일부러 비효율적으로 쓴 식
- 이미 거의 최적인 식

---

## 3. 타입

권장:

```text
uint8
uint16
```

이유:
- exhaustive check 가능
- SMT 검증 쉬움
- overflow 의미가 명확

---

## 4. Baseline

각 함수마다 기록:

```text
instruction_count
graph_nodes
critical_path
runtime
```

---

## 5. 최적화 A — Rule Based

먼저 사람이 만든 rewrite만 사용한다.

목적:
- pipeline 검증

---

## 6. 최적화 B — Enumerative Search

작은 블록에 대해 길이 N 이하의 프로그램을 생성한다.

예:

```text
길이 1
길이 2
길이 3
...
```

동등한 더 짧은 프로그램을 찾는다.

---

## 7. 최적화 C — 분해 후 탐색

같은 함수에 대해:

### 방식 1
전체 함수 통째 탐색

### 방식 2
그래프를 여러 조각으로 분해 후 각각 탐색

비교:

- 탐색 시간
- 후보 수
- 최종 연산 수
- 검증 시간
- 런타임 성능

---

## 8. 성공 지표

### 정확성
- 잘못된 후보 채택: 0

### 탐색
- 최소 1개 이상 비자명한 자동 개선 발견

### 성능
- 일부 benchmark에서 실제 runtime 개선

### 재현성
- seed와 환경을 기록해 결과 재현

---

## 9. 로그

각 실험은 다음을 기록한다.

```text
source_hash
semantic_mode
search_strategy
candidate_count
verifier_result
counterexample
cost_before
cost_after
hardware
runtime_before
runtime_after
```

---

## 10. 실패도 결과다

다음도 중요한 데이터다.

- 어떤 블록에서는 전혀 개선되지 않음
- 탐색 비용이 너무 큼
- verifier가 병목
- 더 짧은 코드가 실제로는 느림
- 분해 오버헤드가 큼

이 결과들이 다음 설계를 결정한다.

---

## 11. 첫 번째 최소 데모

가장 작은 데모는 다음이면 충분하다.

```text
입력:
  작은 uint 함수 1개

출력:
  원본 IR
  최적 IR
  동등성 검증 PASS
  instruction count before/after
  실제 실행시간 before/after
```

이 한 사이클이 자동으로 돌아가면 핵심 개념의 첫 구현이 성립한다.
