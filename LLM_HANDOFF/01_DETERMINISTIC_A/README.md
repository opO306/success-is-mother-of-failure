# 현재 결정론 A

물리 명세·CPU/GPU 커널·환경·world spec·검증 테스트

- 파일 수: 39
- 총 bytes: 193983
- manifest SHA-256: `e6c29ea632b5cfaf272a7909c48497bad2a58b712c7099d67d7acd0785889aed`

다른 LLM에는 먼저 이 README와 필요한 원본 경로만 전달한다.

## 권장 읽기 순서

1. `docs/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md`
2. `engine/deterministic/spec.py`, `causal_spec.py`, `environment_spec.py`
3. `engine/deterministic/kernel.py`, `causal_kernel.py`, `environment_kernel.py`
4. `engine/deterministic/physical_scale.py`, `gpu_environment.py`
5. `worlds/deterministic_physical_flux_v4.json`
6. `tests/test_deterministic_*.py`

## 확인된 범위

A0 이동·충돌, A1 에너지·결합, A2.3 환경 field, 물리 flux, CPU/GPU field 동등성까지다. 고분자·촉매·실제 경계·복사는 아직 없다.
