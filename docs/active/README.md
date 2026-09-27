# 현재 활성 A — C1-B1

**상태: ACTIVE / C1-B1 / outer formal bound ④ 진행.** A가 최우선이며 L·B의 진행 시점은 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.

| 문서 | 현재 읽을 범위 |
|---|---|
| [C1-B1 설계·결정·검증](A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) | 23절 D_valid v2 동결, 24절 ④-1, 25절 ④-2/④-3, 26절 rounding 진행. 1~22절은 설계·측정 이력 |
| [원인별 outer 1-step bound](C1B1_OUTER_FORMAL_BOUND_V1.md) | ④-1 구현 완료. 유한 shell·half-step 운동량 cap 아래의 조건부 상한 |
| [outgoing bootstrap와 tail](C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md) | ④-2 shell induction·유한 체류 상한과 ④-3 R_J·zero discrete impulse·analytic continuous tail 구현. rounding completeness에 조건부 |
| [rounding-decision completeness](C1B1_ROUNDING_DECISION_V1.md) | tail 결정성은 최대 512 bit로 닫음. 일반 pre-tail reachable enclosure의 비영 impulse cover는 미완료 |
| [reachable coordinate·direction 제약](C1B1_REACHABLE_GEOMETRY_V1.md) | ④-4b 귀납적 projection 축소와 frozen 181개 probe replay. Completeness 전체는 미완료 |
| [64-cell 미해결 원인 진단](C1B1_ROUNDING_DIAGNOSIS_V1.md) | 76개 기록 전부 분류. 현재 projection에 최소 65 uniform leaf 필요, ④-4b NotCertified 유지 |

**④ 전체는 FROZEN이 아니고 ⑤는 아직 시작하지 않았다.** 미래의 필요한 impulse가 `MAX_PRECISION_BITS=16384` 안에서 항상 결정되는지는 미증명이다.
다음 Gate는 **16384-bit rounding-decision completeness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증**이다.
inbound / inner / global shadowing / 전체 산란각 / E_min 재생성 / 속박 궤도 / native J / C1-B1 전체 freeze도 남아 있다.

[동결 안내](../frozen/README.md)와 [공통 참조](../reference/README.md)를 함께 확인한다. D_valid의 수치 검증 범위와 analytic outer certificate는 별도이며 자동 승격·연결이 없다.
C0 수치 후보와 Ar 퍼텐셜 선정 이유는 [역사 기록](../history/README.md)에 보존한다. 파일 이름이 과거 시점이어도 현재 계약을 설명하는 근거로 참고할 수 있으며, 현재 Gate를 대신하지 않는다.
