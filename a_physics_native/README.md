# a_physics_native — 물리 함수의 네이티브 실행기 (C1-A Ar–Ar V·F)

기준 평가기(`a_reference/ar2_lang2024.py`)와 그 Git fixture(`a_reference/fixtures/ar2_lang2024_c1a_v1.json`)가 **판정자**다.
네이티브 실행기는 기준을 부르지 않고 (양, 지연, profile, R) 만 받아 결과 비트를 내거나 거부한다.
설명과 결과: `docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md` 11절 (설계자 9판).

| 파일 | 역할 |
|---|---|
| `ar2_core.hpp` | B0·B1 공통 핵심 — anvm_core 정수 위의 고정소수점 **구간** 산술(바깥쪽 반올림), 해석적 미분, 정밀도 96→3072비트, 못 정하면 거부. 영역·범위(R ≤ 2²⁰ bohr) 판정 |
| `ar2_b0.cpp` | B0 직렬. `selftest`(Knuth 나눗셈 대조), `bench n lo hi`(파일 입출력 없는 시간 측정 + 평범한 binary64 비교) |
| `ar2_b1.cpp` | B1 병렬: 질의를 스레드에(chunk / stride), `split`이면 질의 안에서 BO·REL·QED 성분도 스레드로 |
| `ar2_b2.cu` | B2 CUDA: **장치 산술 별도 작성**, 96 limb 고정폭(넘치면 거부), 정밀도 시도 4회(96~768비트, 넘으면 거부) |
| `harness.py` | 빌드(MSVC, nvcc), 질의 직렬화, 답 파싱 |

답: `ok <raw> <M>` · `domain physics_domain_exceeded`(물리) · `halt overflow` · `refuse <이유>`(실행기 한계: `beyond_native_range`,
`undecided`, `device_precision_cap`, `device_width`, `invalid_input`).

시험: `tests/test_c1a_ar2_native_b0.py`, `_b1.py`, `_b2.py` (도구가 없으면 건너뜀). `INJECT=n`으로 결함을 넣어 컴파일(B0 11종, B1 2종, B2 5종).
