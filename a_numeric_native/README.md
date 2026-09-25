# a_numeric_native — 네이티브 실행기 (B0 직렬, B1 병렬, B2 CUDA)

A-Numeric VM(`a_numeric/`) 프로그램을 네이티브 코드로 실행한다. **VM이 판정자다** — 네이티브 코드는 VM을 부르지 않고,
같은 프로그램·같은 입력을 받아 결과(레지스터·분기 기록·멈춤)를 내고, `harness.py`가 VM 결과와 비트 단위로 비교한다.
설명과 결과: `docs/current/A_NUMERIC_EXECUTION_STACK_V1.md` 4.1절.

| 파일 | 역할 |
|---|---|
| `anvm_core.hpp` | 공통 산술 핵심 — binary64 사칙·제곱근은 하드웨어(`/fp:strict`), SUM·DOT·CONST는 **정확 정수 누적 후 1회 반올림**, FX는 전부 정확 정수 |
| `b0_serial.cpp` | B0: 직렬, 스레드 없음 |
| `b1_parallel.cpp` | B1: 프로그램 단위 병렬 + SUM·DOT 항을 T개 스레드로 나눠 정확 부분합 → 합침 → 1회 반올림 |
| `b2_cuda.cu` | B2: 블록 하나가 프로그램 하나, SUM·DOT은 블록 스레드가 4,480비트 정확 누적기로 나눠 합침. 장치 산술은 별도 작성, CONST만 호스트(`anvm_core.hpp`) |
| `harness.py` | 빌드(MSVC, nvcc), 프로그램 직렬화, 결과 파싱, VM과 비교, 사례 모음 9개, 순서 섞기, 폭 계약 사례 |
| `l2.py` | L2 구조: 시험 충격량 +J/−J, 입자별 SUM 한 번, 재명명·쌍 순서·방향 변형 |

시험: `tests/test_a_numeric_native_b0.py`, `_b1.py`, `_b2.py`, `_l2.py` (MSVC·nvcc·GPU가 없으면 건너뜀).
`INJECT=n`으로 결함을 넣어 컴파일해 차등 시험이 잡는지 확인한다(B0 12종, B1 2종, B2 11종). B2는 SUM·DOT 항 수 65,536까지만 계약(`NATIVE_MAX_REDUCTION_TERMS`), 넘으면 실행 전 거부.
