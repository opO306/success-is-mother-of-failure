# LLM Handoff Index

**현재 원문 위치 안내(2026-09-27):** [문서 상태별 안내](../docs/README.md)·[전체 분류/이동 경로표](../docs/DOCUMENT_STATUS_INDEX.md)를 먼저 본다.
문서 58개를 active / frozen / reference / history / deferred로 실제 이동했다. 기존 코드·규칙의 일부 경로는 원문으로 연결하는 안내로 보존했다.
이 폴더의 JSON manifest와 `physical_moves_performed`는 **카탈로그 생성 당시 스냅샷**이며 이번 폴더 정리에서 재생성하지 않았다. 현재 파일 위치·해시를 보증하는 목록으로 사용하지 않는다.

이 폴더는 원본 파일을 옮기거나 복사하지 않는 논리 카탈로그다. 각 하위 폴더의 `manifest.json`은 프로젝트 루트 기준 상대경로·크기·SHA-256을 제공한다.

## 먼저 읽을 것

1. `00_CURRENT_STATUS/README.md`
2. 확인하려는 계통의 `README.md`
3. 필요한 경우 같은 폴더의 `manifest.json`

## 계통

- `01_DETERMINISTIC_A`: 현재 결정론 물리·환경·CPU/GPU
- `02_MODEL_NEUTRAL_B`: B-Language·adapter·가설·계보·실험 제안
- `03_LEGACY_PROBABILISTIC_WORLD`: 보존된 scheduler-v1·sequence·GCP·계보 실험
- `04_LEGACY_SOCIETY_PRIMAL_BRAIN`: 현재 프로젝트 이전의 사회·원시인·뇌 계통
- `05_PRIVATE_TRACE`: 사용자 전용 D: trace 설명; raw 데이터는 이 카탈로그에 복사하지 않음
- `06_UNCLASSIFIED`: 자동 분류되지 않은 검토 대상
- `07_SHARED_CURRENT_DESIGN`: A·B 공용 현재 설계와 구현 순서
- `08_CURRENT_EVIDENCE`: 현재 결정론·GPU·B 기준 결과
- `09_SHARED_GOVERNANCE`: 헌법·중간 점검·정리 감사

## 주의

- 확률 세계와 결정론 세계의 결과를 합산하지 않는다.
- manifest는 생성 당시 파일 수집 지도다. 현재 문서 원문 위치는 docs의 상태별 안내·분류표를 따른다.
- 실제 이동·삭제는 별도 archive·SHA-256·시험 복원·사용자 승인 뒤에만 한다.
