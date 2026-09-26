# 현재 상태 진입점

현재 대시보드는 [CURRENT_STATE.md](../../CURRENT_STATE.md), 구현 위치는 [REPO_MAP.md](../../REPO_MAP.md)를 본다.

- **A: ACTIVE.** A의 물리 기반이 최우선이다.
- **L: DEFERRED UNTIL A FOUNDATION IS SUFFICIENT.** A 안에서 자연 발생·진화하는 계통으로 진행한다.
- **B: DEFERRED TO LATE STAGE, NOT CANCELLED.** A·L 기반의 작은 세계가 돌아가는 후기 단계에서 본격 개발하며 B-classic 구현·문서·시험은 보존한다.
- **활성 Gate:** C1-B1 / outer formal bound ④ 진행. **D_valid v2 FROZEN / ④ 전체 FROZEN 아님 / ⑤ 미착수.**
- **다음 Gate:** 16384-bit rounding-decision completeness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증.
- [C1-B1 설계 기록](../../docs/active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) 23·24·25·26절 및 [rounding 문서](../../docs/active/C1B1_ROUNDING_DECISION_V1.md)를 함께 읽는다.
- D_valid evidence(`numerical_validated` / `unsupported`)와 별도 analytic outer certificate 사이에 자동 승격·연결은 없다.
- ④-4 구현 당시 LOCAL FULL 기록: **2404 passed + 1 strict xfailed, skip 0, 388.84초, 인코딩 경고 25건**. 문서 정리의 재검증 결과와 구분한다.

카탈로그 manifest의 크기·해시는 생성 당시 스냅샷이며 이번 문서 정리에서 재생성하지 않았다. 현재 내용과 이동 위치는 [문서 안내](../../docs/README.md)·[분류표](../../docs/DOCUMENT_STATUS_INDEX.md)를 기준으로 읽는다.
과거 상세 기록은 [상태 역사](../../docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)에 보존한다.

## 과거 핸드오프 안내 — 원문 보존

아래 837 passed와 held-out 안내는 당시 기록이며 현재 기준선·새 실행 승인을 뜻하지 않는다.

### 당시 상태

- 중간 점검: [../../docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md](../../docs/history/MIDPOINT_A_B_AUDIT_2026-09-21.md)
- 구현 순서: [../../docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md](../../docs/history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md)
- B 아키텍처: [../../docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md](../../docs/deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md)
- 최신 전체 테스트: 837 passed
- held-out A 실행: 사용자 승인 대기, 현재 0개
