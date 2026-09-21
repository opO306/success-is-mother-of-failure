# Legacy — 확률 세계 (scheduler-v1)

**동결된 비교 기준선이다. 수정 대상이 아니다.** 결정론 결과와 직접 합산하지 않는다.

코드: `engine/sequence/`, `engine/living/events.py`
(`engine.sequence`가 `engine.living.events`의 사건 기록 형식에 의존하므로 `engine/living/`을 통째로 지우면 안 된다.)

## 먼저 읽을 것

1. [`EVENT_RATE_AND_TIME_AUDIT_V1.md`](EVENT_RATE_AND_TIME_AUDIT_V1.md) — 사건율·시간 확장성 감사
2. [`SCHEDULER_V1_AUDIT.md`](SCHEDULER_V1_AUDIT.md) — 실패 원인 분석 (전역 후보 경쟁)
3. [`DUAL_GCP_EVALUATION_PROTOCOL.md`](DUAL_GCP_EVALUATION_PROTOCOL.md) — GCP 실험 사전 판정 기준

## 확정된 판정

- GCP1: 64세계×6시간, 분할 4·융합 4
- GCP2: 12세계×32시간, 분할·융합 0
- 통합 768 세계·시간, 독립 후손 0
- 관찰된 분할은 같은 cyclic strand가 만든 일시적 위상 분할
- 독립 경계 scission+closure 경로 없음
- 원인: 전역 후보 경쟁, 단위 불일치, 벽시계 노출량 차이
- **추가 장기 확률 VM 실험 중단**

## 나머지 파일

- `SEQUENCE_*_V0.md` / `STAGE_C_*_REVIEW.md` — 2026-09-17 단계별 설계-검토 쌍 (약 40개)
- `SPATIAL_*_REVIEW.md` — 공간 sequence 검증
- `INTEGRATED_GENETIC_WORLD_V0_REVIEW.md`, `COMPONENT_MOTION_V1.md`, `CONTEXTUAL_INHERITANCE_V1.md`,
  `PHYSICAL_RECOMBINATION_V1.md`, `LOCAL_DYNAMICS_V1.md` — 후반부 물리 확장
- `SELF_INTERPRETING_SEQUENCE_SUBSTRATE_V0.md`, `STAGE_B_CONCEPT_REVIEW.md` — 초기 서열 언어 설계
