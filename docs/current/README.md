# 현재 — 결정론 A/B

지금 실제로 개발 중인 계통. 코드는 `engine/deterministic/`, 독립 검증기는 `audit/`.

읽는 순서:

1. [`DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md`](DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md) — A 물리 심화 설계
2. [`EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md`](EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md) — B 전체 아키텍처 + 장기 후보
3. [`DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md`](DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md) — 구현 순서·완료 판정
4. [`MIDPOINT_A_B_AUDIT_2026-09-21.md`](MIDPOINT_A_B_AUDIT_2026-09-21.md) — 중간 점검, 한계가 솔직히 적혀 있음
5. [`VERIFICATION_LIMITS_AND_LESSONS.md`](VERIFICATION_LIMITS_AND_LESSONS.md) — 검증이 무엇을 못 잡는지, 결함 주입 기록
6. [`PRECONDITION_CENSUS_2026-09-21.md`](PRECONDITION_CENSUS_2026-09-21.md) — 작업 묶음 4의 전제조건을 먼저 센 결과
7. [`LOCAL_INTERACTION_PRINCIPLES_V1.md`](LOCAL_INTERACTION_PRINCIPLES_V1.md) — **국소 상호작용 원칙 4종 + 현재 커널 결함 증거.**
   1~4번 설계 문서보다 **이쪽이 최신 판정이다.** 충돌하면 이 문서가 우선한다
8. [`MINIMAL_LOCAL_GEOMETRY_V1.md`](MINIMAL_LOCAL_GEOMETRY_V1.md) — 7번의 단계 2 설계.
   **승인됨. 구현 진행 중** — 단계별 완료 표시는 문서 안에 있다
9. [`WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md`](WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md) —
   **B가 A를 만들 때 쓰는 명세 언어 사전.** 세계 JSON을 쓰거나 읽을 때 이 문서를 본다.
   B-Language(`b_language.py`)와는 다른 언어이니 헷갈리지 말 것
10. [`LANGUAGE_REVISION_GOVERNANCE_V1.md`](LANGUAGE_REVISION_GOVERNANCE_V1.md) —
    **7·8번(causal v2→v3)을 실제 사례로 삼아, 앞으로 B가 언어 확장을 제안하고
    인간이 승인하는 절차를 정의한다.** B에게는 제안권만 있고 최종 변경권은 없다.
    설계 초안, `RULES.md` 승격 전
11. [`PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md`](PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md) —
    **새 국소 상호작용을 짜기 전에 통과해야 하는 5문장 검사.**
    "무엇이 존재하는가 → 어떤 결과가 가능한가 → 뭐가 동시에 가능한가 →
    하나만 골라야 하면 뭐가 정하는가 → 답이 ID·순서면 뭐가 빠졌는가."
    "둘씩 처리" 제안이 기각된 사건(7번)에서 나온 절차를 일반화했다.
    **`StructureState`(다음 작업)를 포함해 모든 새 물리는 이 검사를 먼저 문서로
    통과시키고 시작한다.**

**중간 점검 기록:** [`../중간 결과/MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md`](../중간%20결과/MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md) —
7~10번 작업 전체(원칙 채택부터 `PortBond` 구현까지)를 처음부터 요약. 지금까지
구현된 것과 아직 안 된 것(`StructureState` 등)을 한 문서에서 대조하고 싶을 때 여기부터 본다.

**커널을 건드리기 전에 7번을 먼저 읽는다.** 현재 물리가 particle_id에 의존하고 있고,
`tests/test_known_defects_causal_kernel.py`의 테스트들은 **깨지라고 만든 것**이다.

더 빠른 진입점은 루트의 [`../../CURRENT_STATE.md`](../../CURRENT_STATE.md) — 영역별 상태표와 다음 갈림길이 정리돼 있다.
