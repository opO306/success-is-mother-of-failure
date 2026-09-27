# 06. 하드웨어 매핑

## 1. 목표

하나의 계산을 반드시 하나의 종류의 프로세서에서 끝낼 필요는 없다.

예:

```text
F = A + B + C + D
```

를:

```text
A → CPU
B → GPU
C → SIMD
D → LUT/FPGA
```

로 나눌 수 있다.

단, 데이터 이동과 동기화 비용을 반드시 포함해야 한다.

---

## 2. CPU에 적합한 계산

대체로:

- 분기 많음
- 작업 크기 작음
- latency 민감
- 순차 의존성 큼
- irregular memory access
- 복잡한 control flow

---

## 3. GPU에 적합한 계산

대체로:

- 같은 연산 반복
- 대량 데이터
- 높은 병렬성
- 규칙적인 메모리 접근
- arithmetic intensity가 충분함

---

## 4. SIMD

CPU 내부에서도 여러 데이터를 한 명령으로 처리할 수 있다.

예:

```text
[a,b,c,d] + [e,f,g,h]
```

를 벡터 연산으로 처리한다.

작은 데이터에 GPU를 쓰는 것보다 SIMD가 유리한 경우가 많다.

---

## 5. LUT

작은 입력 공간, 반복 호출, 계산비용이 큰 함수에 유리하다.

비용:

- 메모리 용량
- lookup latency
- cache miss

---

## 6. FPGA

FPGA는 회로 자체를 구성할 수 있다.

가능한 장기 구조:

```text
CPU
 │
 ├─ 일반 계산
 │
 └─ FPGA region
       ├─ accelerator A
       ├─ accelerator B
       └─ 필요 시 재구성
```

특정 hot block을 회로로 만들 수 있다.

---

## 7. 동적 재구성

더 장기적으로는:

```text
현재 workload
   ↓
필요 accelerator 선택
   ↓
FPGA 일부 재구성
   ↓
해당 계산 실행
```

이 가능하다.

하지만 재구성 자체에 비용이 있으므로 자주 바꾸면 손해다.

---

## 8. 데이터 이동 비용

가장 흔한 함정이다.

예:

```text
CPU 계산 100 us
GPU 계산 20 us
```

만 보면 GPU가 빠르다.

하지만:

```text
CPU→GPU copy 60 us
GPU compute 20 us
GPU→CPU copy 60 us
```

이면 총 140 us다.

따라서 하드웨어 매핑 비용은 반드시:

```text
compute
+ transfer
+ synchronization
+ launch
+ conversion
```

을 포함해야 한다.

---

## 9. 배치 판단

개념적인 결정:

```text
후보 블록
   ↓
병렬성 높음?
   ├─ NO → CPU 후보
   └─ YES
        ↓
데이터 양 충분?
   ├─ NO → SIMD 후보
   └─ YES → GPU 후보
```

실제 시스템에서는 heuristic보다 benchmark가 더 신뢰할 수 있다.

---

## 10. 장기 하드웨어 구성

```text
┌───────────────────────────────┐
│ Host CPU                      │
│                               │
│  Runtime / Scheduler          │
│       │                       │
│       ├──────── GPU           │
│       ├──────── SIMD          │
│       └──────── FPGA Region   │
│                               │
└───────────────────────────────┘
```

즉 완전히 새로운 CPU를 처음부터 만들기보다:

> 기존 범용 프로세서 + 재구성/가속 영역

이 현실적인 출발점이다.
