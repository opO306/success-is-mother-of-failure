# 모델 중립 B

B-Language·adapter·world model·trace·가설·반사실·실험 제안

- 파일 수: 39
- 총 bytes: 260011
- manifest SHA-256: `477caab19bd90c2a81c48e76cb6b8d7a3967a1f567ae40fc22b57581d0e7686f`

다른 LLM에는 먼저 이 README와 필요한 원본 경로만 전달한다.

## 권장 읽기 순서

1. `docs/current/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md`
2. `schemas/b_language_boundary_v1.schema.json`
3. `engine/deterministic/b_language.py`, `brain_adapter.py`
4. `cognitive_map.py`, `change_graph.py`, `provenance.py`
5. `hypotheses.py`, `counterfactual.py`, `theory_revision.py`, `experiment_proposal.py`
6. 대응하는 `tests/test_deterministic_*.py`

## 해석 주의

현재 B 후보는 수작업 결정론 adapter다. 독립 학습형 JEPA·신경망이나 진짜 미지 변수 발견은 아직 없다. held-out 제안서는 미실행 상태다.
