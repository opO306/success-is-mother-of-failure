# 현재 문서와 보존된 연구 기록

**문서 분류: 역사 / 과거 설계·실측 기록.** 본문의 “현재”, “다음”, 시험 개수와 후보는 기록 당시의 상태다. 현재 작업 지시나 새 동결 판정으로 읽지 않는다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


현재 우선순위·활성 Gate는 [CURRENT_STATE.md](../../CURRENT_STATE.md)가 정본이다.
**A: ACTIVE / L: DEFERRED UNTIL A FOUNDATION IS SUFFICIENT / B: DEFERRED TO LATE STAGE, NOT CANCELLED.**
A를 먼저 검증하고, 기반이 충분해진 뒤 L의 자연 발생·진화를 진행하며, A·L 기반의 작은 세계가 돌아가는 후기 단계에서 B를 본격적으로 만든다.
B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다. `current/`에는 활성 A 문서와 과거 B 설계·계약·실험 기록이 함께 있다.

현재 C1-B1에서 읽을 문서:

1. [CURRENT_STATE.md](../../CURRENT_STATE.md) — D_valid v2 FROZEN, outer ④ 진행, ④ 전체 FROZEN 아님, ⑤ 미착수.
2. [C1-B1 설계 기록](../active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) — 23절 D_valid 동결, 24절 ④-1, 25절 ④-2/④-3, 26절 rounding 진행.
3. [Rounding-decision completeness](../active/C1B1_ROUNDING_DECISION_V1.md) — 16384-bit 한도에서 tail은 닫힘, 일반 pre-tail reachable cover는 미완료.
4. [Outer 1-step bound](../active/C1B1_OUTER_FORMAL_BOUND_V1.md)·[outgoing bootstrap/tail](../active/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md) — 별도 analytic outer certificate. D_valid evidence와 자동 승격·연결 없음.
5. [인수인계 점검](PROJECT_HANDOVER_REVIEW_2026-09-27.md) — 현재 보충 안내와 `0898ca3` 당시 점검 기록.
6. [상태 역사](PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md) — 정리 전 CURRENT_STATE 원문 전체.

## 과거 진입 안내에 대한 해석

아래는 v2→v3→v4 시기의 안내를 원문으로 보존한다. “최신 판정”, “다음 작업”, “구현 진행 중”은 당시 상태다.
v2의 ID 의존·길이 3 천장은 v5에서 해소됐고, `StructureState`도 v4에 구현됐다. 현재 활성 작업은 v6 C1-B1이다.
`test_known_defects_causal_kernel.py`에는 현재 살아 있는 결함 시험이 없으며, 동결 v2 결함은 `test_legacy_causal_semantics.py`가 보존한다.
아래 B가 A를 제작한다는 옛 설계 설명은 현재 연구자 B의 권한이 아니다. 현재 A/B 경계는 RULES·헌법을 따른다.

---

# 과거 진입 안내 — 결정론 A/B (원문 보존)

지금 실제로 개발 중인 계통. 코드는 `engine/deterministic/`, 독립 검증기는 `audit/`.

읽는 순서:

1. [[DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md](DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md)](DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md) — A 물리 심화 설계
2. [[EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md](../deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md)](../deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md) — B 전체 아키텍처 + 장기 후보
3. [[DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md](DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md)](DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md) — 구현 순서·완료 판정
4. [[MIDPOINT_A_B_AUDIT_2026-09-21.md](MIDPOINT_A_B_AUDIT_2026-09-21.md)](MIDPOINT_A_B_AUDIT_2026-09-21.md) — 중간 점검, 한계가 솔직히 적혀 있음
5. [[VERIFICATION_LIMITS_AND_LESSONS.md](../reference/VERIFICATION_LIMITS_AND_LESSONS.md)](../reference/VERIFICATION_LIMITS_AND_LESSONS.md) — 검증이 무엇을 못 잡는지, 결함 주입 기록
6. [[PRECONDITION_CENSUS_2026-09-21.md](PRECONDITION_CENSUS_2026-09-21.md)](PRECONDITION_CENSUS_2026-09-21.md) — 작업 묶음 4의 전제조건을 먼저 센 결과
7. [[LOCAL_INTERACTION_PRINCIPLES_V1.md](LOCAL_INTERACTION_PRINCIPLES_V1.md)](LOCAL_INTERACTION_PRINCIPLES_V1.md) — **국소 상호작용 원칙 4종 + 현재 커널 결함 증거.**
   1~4번 설계 문서보다 **이쪽이 최신 판정이다.** 충돌하면 이 문서가 우선한다
8. [[MINIMAL_LOCAL_GEOMETRY_V1.md](MINIMAL_LOCAL_GEOMETRY_V1.md)](MINIMAL_LOCAL_GEOMETRY_V1.md) — 7번의 단계 2 설계.
   **승인됨. 구현 진행 중** — 단계별 완료 표시는 문서 안에 있다
9. [[WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md](../deferred/WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md)](../deferred/WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md) —
   **B가 A를 만들 때 쓰는 명세 언어 사전.** 세계 JSON을 쓰거나 읽을 때 이 문서를 본다.
   B-Language(`b_language.py`)와는 다른 언어이니 헷갈리지 말 것
10. [[LANGUAGE_REVISION_GOVERNANCE_V1.md](../deferred/LANGUAGE_REVISION_GOVERNANCE_V1.md)](../deferred/LANGUAGE_REVISION_GOVERNANCE_V1.md) —
    **7·8번(causal v2→v3)을 실제 사례로 삼아, 앞으로 B가 언어 확장을 제안하고
    인간이 승인하는 절차를 정의한다.** B에게는 제안권만 있고 최종 변경권은 없다.
    설계 초안, [RULES.md](../../RULES.md) 승격 전
11. [[PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md](../reference/PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md)](../reference/PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md) —
    **새 국소 상호작용을 짜기 전에 통과해야 하는 5문장 검사.**
    "무엇이 존재하는가 → 어떤 결과가 가능한가 → 뭐가 동시에 가능한가 →
    하나만 골라야 하면 뭐가 정하는가 → 답이 ID·순서면 뭐가 빠졌는가."
    "둘씩 처리" 제안이 기각된 사건(7번)에서 나온 절차를 일반화했다.
    **`StructureState`(다음 작업)를 포함해 모든 새 물리는 이 검사를 먼저 문서로
    통과시키고 시작한다.**

12. [[STRUCTURE_STATE_V1.md](STRUCTURE_STATE_V1.md)](STRUCTURE_STATE_V1.md) — **8번의 단계 3 설계.**
    구조의 운동을 최저 번호 멤버에게서 빼앗아 구조 자체에 준다.
    11번의 5문장 검사를 실제 코드 측정으로 통과시킨 첫 문서.
    **승인됨 (Q1~Q5 확정).** Q2는 측정으로 두 번 반박돼 별도 상태량 저장으로 확정됐다

**중간 점검 기록:** [[../중간 결과/MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md](MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md)](MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md) —
7~10번 작업 전체(원칙 채택부터 `PortBond` 구현까지)를 처음부터 요약. 지금까지
구현된 것과 아직 안 된 것(`StructureState` 등)을 한 문서에서 대조하고 싶을 때 여기부터 본다.

**커널을 건드리기 전에 7번을 먼저 읽는다.** 현재 물리가 particle_id에 의존하고 있고,
`tests/test_known_defects_causal_kernel.py`의 테스트들은 **깨지라고 만든 것**이다.

더 빠른 진입점은 루트의 [[../../CURRENT_STATE.md](../../CURRENT_STATE.md)](../../CURRENT_STATE.md) — 영역별 상태표와 다음 갈림길이 정리돼 있다.
