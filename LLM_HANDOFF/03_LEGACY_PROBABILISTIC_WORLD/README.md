# Legacy 확률 세계

scheduler-v1 sequence 계통과 GCP·계보·실패 실험 증거

- 파일 수: 865
- 총 bytes: 3329098989
- manifest SHA-256: `724d3217c71aac66d4aadafa7fb4fd7fa621617484b2f16f97f645c011c71eef`

다른 LLM에는 먼저 이 README와 필요한 원본 경로만 전달한다.

## 이 계통의 의미

현재 수정 대상이 아니라 보존된 비교 기준 `scheduler-v1`이다. 결정론 결과와 직접 합산하지 않는다.

## 가장 먼저 읽을 것

1. `docs/EVENT_RATE_AND_TIME_AUDIT_V1.md`
2. `docs/SCHEDULER_V1_AUDIT.md`
3. `docs/DUAL_GCP_EVALUATION_PROTOCOL.md`
4. `engine/sequence/nonliving_world.py`, `observation.py`, `lineage.py`
5. `engine/living/events.py`
6. `runs/dual_gcp_precommit_20260919_185150/`

## 확정된 판정

- GCP1: 64세계×6시간, 분할 4·융합 4
- GCP2: 12세계×32시간, 분할·융합 0
- 통합 768 세계·시간, 독립 후손 0
- 관찰된 분할은 같은 cyclic strand가 만든 일시적 위상 분할
- 독립 경계 scission+closure 경로 없음
- 전역 후보 경쟁·단위 불일치·벽시계 노출량 차이가 확인됨
- 추가 장기 확률 VM 실험은 중단
