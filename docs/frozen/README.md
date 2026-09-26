# 동결 계약 — 원문과 적용 범위

**동결은 과거 기록과 다르다.** 과거에 확정했더라도 해당 버전에 현재 적용되는 계약은 이 안내에서 확인한다. 새 버전·새 판정 없이 계약을 고치지 않는다.

| 자산 | 동결 범위·근거 | 원문 위치 |
|---|---|---|
| C1-A | `c1a-ar2-lang2024-v1`. 물리·수치 의미, 출처·매개변수·fixture 비트. 실행기 자원 한도·성능 전체를 동결한 것은 아님 | [C1-A 동결 원문](C1A_AR2_FREEZE_V1.md) |
| D_valid v2 | canonical 생성기·기준 fixture·초기 상태 식별. `numerical_validated` / `unsupported`, 궤적 전체 인증 아님 | [D_valid 동결 범위 안내](D_VALID_V2.md), [C1-B1 설계 23절](../active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) |
| B 탐침 문법 v3 | 방법·탐침 계약 7개 코드 파일의 동결 지문. B-classic 비교군/연구 자산으로 보존 | [탐침 동결 원문](PROBE_V3_FREEZE.md) |
| 연구자 B 신체 계약 v1 | 계약 1~8절의 본문 해시. 9절은 미결 사항이며 구현 완료를 뜻하지 않음 | [경로 고정 원문 안내](HUMAN_REALIZABLE_BODY_CONTRACT_V1.md) |

C1-A와 B 탐침 문서는 **내용을 한 바이트도 바꾸지 않고 이동**했다. 신체 계약은 `tests/test_body_contract_freeze.py`가 기존 경로를 직접 읽으므로 원문을 그대로 두고 여기서 연결한다.
D_valid 안내는 새 계약이나 복사본이 아니라 기존 동결 범위를 찾는 색인이다. D_valid 코드·fixture·기준 상태는 이동·재생성하지 않았다.
동결 원문 안에 남은 옛 근거 문서명은 [전체 분류표](../DOCUMENT_STATUS_INDEX.md)로 찾는다. C1-A의 [Ar 퍼텐셜 조사](../history/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md)와 [C0 수치 판정 이력](../history/A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md)은 history에 있다. 원문의 참조 표기를 고치기 위해 동결 본문을 편집하지 않았다.

**동결되지 않은 현재 작업:** C1-B1 전체와 outer ④ 전체. ⑤도 미착수다. 별도 analytic outer certificate가 D_valid를 자동으로 `formal_certified`로 승격시키지 않는다.

## 동결된 구형 계통의 역사 자료

- causal v1/v2/v3의 잘못된 동작은 동결 형식으로 보존한다. [구형 설계·실측](../history/README.md)에서 판정 이력을 찾는다. causal v4의 experimental 상태를 동결로 바꾸지 않는다.
- v5의 강체 기준 세계 설계·검증 기록도 [history](../history/README.md)에 보존한다. 문서 전체의 본문 해시가 동결됐다고 추가 선언하지 않는다.
- [확률 세계 기준선](../legacy-probabilistic/README.md)은 동결된 비교 자산이다. 생명·복사·진화의 새 증거로 합산하지 않는다.

현재 우선순위는 [CURRENT_STATE.md](../../CURRENT_STATE.md), 원문 전체의 이동 경로는 [분류표](../DOCUMENT_STATUS_INDEX.md)를 본다.
