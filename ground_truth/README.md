# 독립 Ground-Truth 감사기

## 왜 필요한가

`tests/test_deterministic_missing_link_investigator.py`의 "hidden mediator" 시나리오는
`investigate_missing_link`(B0.7 자체 코드)를 호출한 뒤 그 출력 status가 `TESTABLE`인지만
확인한다. **B가 낸 답을 보고 그 답이 맞다고 검증하는 순환논리**다. B의 로직이 애초에
틀려 있어도 같은 틀린 로직으로 "정답"과 "B의 답"을 둘 다 만들면 테스트는 통과한다.

이 감사기는 B0.3 이상(`MechanismCandidate`, `CausalPath`, `MissingLinkHypothesis`,
`causal_path_builder`, `missing_link_investigator` 등 무엇이든)을 **전혀 import하지 않고**,
A만 직접 조작해서 정답을 먼저 만든다. `tests/test_audit_ground_truth.py`의
`test_no_ground_truth_module_imports_b_code`가 이 경계를 AST로 강제한다.

## 접근 허용 범위

| 허용 | 금지 |
|---|---|
| `engine.deterministic.causal_kernel` (A0 물리 커널) | B0.3~B0.7 전체 |
| `engine.deterministic.causal_spec` (world spec 로더) | `MechanismCandidate` / `MechanismEvidence` |
| world spec JSON (`worlds/*.json`) | `CausalPath` / `MissingLinkHypothesis` |
| 이 패키지 안에서 새로 정의한 순수함수 world (World 2/3) | `trace_model`, `research_journal` |

World 1만 A0 커널을 직접 조작한다 — 실제 물리 엔진이 mediator 구조를 갖는지 묻는 질문이므로
A0를 쓰는 게 당연하다. World 2/3는 기존 heat/bond 세계를 재활용하지 않는다. World 1의 정답을
검증하는 데 쓰는 것과 같은 엔진을 다시 손대면, 그 편집의 실수가 세 world의 정답 전부를
의심스럽게 만들기 때문이다. 대신 이 패키지 안에서만 정의된, `causal_kernel`과 아무 상태도
공유하지 않는 아주 작은 순수함수로 만들었다.

## 세 world

### GT-1 — Mediator: `heat_cell.energy → bond.exists → particle.kinetic_energy`

`worlds/deterministic_bond_cycle_v1.json`을 그대로 쓴다 (A0 자체가 정답의 일부).

세 가지 개입 전부 통과해야 VALID:

1. **A가 B를 바꾸는가** — heat=0 vs heat=2, 나머지 전부 동일. A0의 `break_heat` 규칙상
   heat=0은 결합을 끊을 열량을 못 대고 heat=2는 낼 수 있다 (`causal_kernel.py::_break_existing`).
2. **B가 C를 바꾸는가** — 같은 충돌 지오메트리에서 결합이 끝까지 유지되는 경우(heat=0)와
   중간에 끊어지는 경우(heat=2)를 비교. 끊어지면 저장 에너지가 입자에 방출된다.
3. **B를 막으면 A→C 효과가 사라지는가** (mediator 판정의 핵심) — 두 입자를 애초에 절대
   충돌하지 않을 위치(멀리 떨어뜨림)에 배치해 결합이 영원히 생기지 않게 고정한 뒤, 그 상태에서
   heat=0 vs heat=2를 비교. 결합이 없으면 A0에는 heat이 입자에 닿을 다른 경로가 없으므로
   `particle_a.kinetic_energy`가 두 경우 모두 동일해야 한다.

A0는 heat과 무관하게 결합만 직접 켜고 끄는 public control을 제공하지 않는다 (강제로
`state.bonds`를 지우면 `_break_existing`의 방출 로직을 우회해 에너지가 그냥 사라진다 — 커널
자체의 상태 전이 함수를 우회하는 것은 공정한 개입이 아니다). **heat을 거치는 것이 B를 움직이는
유일한 합법적 경로라는 사실 자체가 "B가 mediator"라는 주장의 일부다.**

### GT-2 — Direct: `source_active → outcome_active`, 중간 상태 없음

`audit/ground_truth/world2_direct.py`에 정의된 전용 2필드 순수함수 world.
규칙은 `outcome_active := source_active`가 전부.

- `source_active`의 두 값(True/False) 전수검사
- `outcome_active`의 이전 값이 결과에 영향을 주지 않음을 확인 (자기 자신을 통한 숨은 mediator 배제)
- `step()` 함수 소스 자체를 읽어 `state.outcome_active`를 참조하지 않는지 정적으로 확인

### GT-3 — Conditional: `D=true일 때만 A → C` (`C := A AND D`)

`audit/ground_truth/world3_conditional.py`. 상태는 `source_active`(A) / `gate_enabled`(D) /
`outcome_active`(C) 셋뿐. 가능한 조합이 4개라 **전수검사**.

| A | D | 예상 C |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | 1 |

추가 확인:

- D=false 고정, A만 바꿔도 C 불변
- D=true 고정, A를 바꾸면 C도 바뀜
- A가 D를 바꾸지 않음 (D는 `A → D → C`의 중간 노드가 아니라 게이트 조건)

## 판정 네 가지

`GroundTruthReport.verdict`는 넷 중 하나:

- **VALID** — 이 world가 선언한 모든 검사가 실제 A에서 성립
- **INVALID_WORLD** — 검사 중 하나가 실패. **B의 잘못이 아니라 world 설계 자체가 잘못된 것**.
  이 경우 B0.7 테스트가 그 world를 정답으로 쓰면 안 된다
- **AMBIGUOUS** — public control/observable만으로는 결론을 못 냄 (예: GT-1의 "결합 차단"
  전제가 실제로 성립하지 않으면 intervention 3은 AMBIGUOUS로 빠지지 VALID로 우기지 않는다)
- **AUDIT_ERROR** — 감사기 자체 코드가 예외를 던짐

빈 검사 목록은 AMBIGUOUS로 처리한다 (`GroundTruthReport.verdict`) — 아무것도 안 물어보고
VALID로 선언하는 사태를 막기 위해서다.

## 봉인

```bash
python run_ground_truth_audit.py            # 실행만, 봉인 안 함
python run_ground_truth_audit.py --seal      # sealed/*.json에 기록
python run_ground_truth_audit.py --seal --force   # 의도적 변경 후 재봉인
```

`sealed/GT-*.json`은 `ground_truth_digest`를 포함한 채로 저장된다. 이미 봉인된 파일과
digest가 같으면 재실행은 아무것도 안 한다(no-op). digest가 다르면 `--force` 없이는
**거부**하고 옛 digest와 새 digest를 둘 다 출력한다 — 결과를 본 뒤 슬쩍 정답을 고치는
것을 막기 위해서다. 의도적으로 수정할 때는 `--force`를 쓰고 커밋 메시지에 왜 바뀌었는지
남긴다.

## 현재 결과 (2026-09-22)

3/3 VALID. `sealed/`에 세 파일 모두 봉인됨.

## 한계

- GT-1은 A0의 `execution.ticks=4`, 고정된 격자·입자 배치 안에서만 검증했다. 다른 world spec
  (다른 크기, 다른 `break_heat` 값)에서도 같은 구조가 성립하는지는 별도 검증이 필요하다
- GT-2/GT-3는 A0 물리와 완전히 분리된 synthetic world라서, "A0 안에도 순수 direct/conditional
  관계가 있는가"는 이 감사기가 답하지 않는다
- 이 패키지는 **정답을 만드는 도구**이지 B0.7을 채점하는 도구가 아니다. B가 찾아낸 구조와
  `sealed/*.json`을 비교하는 것은 별도 도구의 일이며, 그 도구도 B0.3+ 모듈을 이 패키지
  안으로 끌어들이면 안 된다
