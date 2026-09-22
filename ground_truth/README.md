# Ground-Truth 답안지 (`ground_truth/`)

## 왜 `audit/` 밑이 아니라 저장소 최상위인가

이 패키지는 **감사 로직이 아니라 감사기가 참조하는 독립 기준(답안지)**이다.
`audit/`는 "engine이 이미 만든 기록을 독립적으로 재검증하는 감사기" 전용 네임스페이스이고,
그 안의 모든 코드는 `engine`을 전혀 import하지 않는다는 게 불변식이다
(`tests/test_audit_independent_trace.py::test_audit_package_imports_nothing_from_engine`).

이 패키지의 World 1은 A0 커널(`engine.deterministic.causal_kernel`)을 직접 구동해서 정답을
만든다 — 이건 `audit/`의 불변식과 정면으로 부딪힌다. 예외를 추가해 `audit/`의 규칙을
약화시키는 대신, 애초에 성격이 다른 물건이니 저장소 최상위 `ground_truth/`로 분리했다.
`audit/`는 원래의 강한 규칙을 그대로 유지하고, 이 패키지는 자기만의 더 좁은 규칙
(B0.3 이상 금지)을 따로 갖는다.

## 왜 필요한가

`tests/test_deterministic_missing_link_investigator.py`의 "hidden mediator" 시나리오는
`investigate_missing_link`(B0.7 자체 코드)를 호출한 뒤 그 출력 status가 `TESTABLE`인지만
확인한다. **B가 낸 답을 보고 그 답이 맞다고 검증하는 순환논리**다. B의 로직이 애초에
틀려 있어도 같은 틀린 로직으로 "정답"과 "B의 답"을 둘 다 만들면 테스트는 통과한다.

이 패키지는 B0.3 이상(`MechanismCandidate`, `CausalPath`, `MissingLinkHypothesis`,
`causal_path_builder`, `missing_link_investigator` 등 무엇이든)을 **전혀 import하지 않고**,
A만 직접 조작해서 정답을 먼저 만든다. `tests/test_ground_truth.py`의
`test_no_ground_truth_module_imports_b_code`가 이 경계를 AST로 강제한다.

## 접근 허용 범위

| 허용 | 금지 |
|---|---|
| `engine.deterministic.causal_kernel` (A0 물리 커널, GT-1만) | B0.3~B0.7 전체 |
| `engine.deterministic.causal_spec` (world spec 로더, GT-1만) | `MechanismCandidate` / `MechanismEvidence` |
| world spec JSON (`worlds/*.json`, GT-1만) | `CausalPath` / `MissingLinkHypothesis` |
| 이 패키지 안에서 새로 정의한 순수함수 world (GT-M1/GT-2/GT-3) | `trace_model`, `research_journal` |

GT-1만 A0 커널을 직접 조작한다 — 실제 물리 엔진이 mediator 구조를 갖는지 묻는 질문이므로
A0를 쓰는 게 당연하다. GT-M1/GT-2/GT-3는 기존 heat/bond 세계를 재활용하지 않는다. GT-1의
정답을 검증하는 데 쓰는 것과 같은 엔진을 다시 손대면, 그 편집의 실수가 world들의 정답 전부를
의심스럽게 만들기 때문이다. 대신 이 패키지 안에서만 정의된, `causal_kernel`과 아무 상태도
공유하지 않는 아주 작은 순수함수로 만들었다.

## 네 world

### GT-1 (레거시 sanity test) — 실제 물리: `heat_cell.energy → bond.exists → particle.kinetic_energy`

`worlds/deterministic_bond_cycle_v1.json`을 그대로 쓴다 (A0 자체가 정답의 일부).

세 가지 개입 전부 통과해야 VALID:

1. **A가 B를 바꾸는가** — heat=0 vs heat=2, 나머지 전부 동일. A0의 `break_heat` 규칙상
   heat=0은 결합을 끊을 열량을 못 대고 heat=2는 낼 수 있다 (`causal_kernel.py::_break_existing`).
2. **B가 C를 바꾸는가** — 같은 충돌 지오메트리에서 결합이 끝까지 유지되는 경우(heat=0)와
   중간에 끊어지는 경우(heat=2)를 비교. 끊어지면 저장 에너지가 입자에 방출된다.
3. **B를 막으면 A→C 효과가 사라지는가** — 두 입자를 애초에 절대 충돌하지 않을 위치(멀리
   떨어뜨림)에 배치해 결합이 영원히 생기지 않게 고정한 뒤, 그 상태에서 heat=0 vs heat=2를
   비교. 결합이 없으면 A0에는 heat이 입자에 닿을 다른 경로가 없으므로 `particle_a.kinetic_energy`가
   두 경우 모두 동일해야 한다.

**주의(왜 이게 정답지가 아니라 참고용 sanity test인가):** A0는 heat과 무관하게 결합만
직접 켜고 끄는 public control을 제공하지 않는다 (강제로 `state.bonds`를 지우면
`_break_existing`의 방출 로직을 우회해 에너지가 그냥 사라진다 — 커널 자체의 상태 전이
함수를 우회하는 것은 공정한 개입이 아니다). 그래서 intervention 3은 "B만" 막는 게 아니라
입자 배치를 바꿔 **다른 초기 세계**를 만든다. 엄밀히는 "B를 차단했더니 A→C가 사라졌다"가
아니라 "결합이 애초에 불가능한 다른 세계에서는 heat→particle 효과가 없다"는 더 약한
주장이다. 좋은 보조 증거이긴 하지만, mediator 정답지로 쓰기엔 애매함이 남는다 — 그래서
GT-M1이 정답지 역할을 대신한다.

### GT-M1 (정답지) — Mediator: `source_active → mediator_active → outcome_active`

`gt_m1_mediator.py`. mediator(`mediator_active`, B)에 `source_active`(A)와는 독립된
public control(`step_with_mediator_override`)이 있는 전용 synthetic world. GT-1이 풀지
못했던 "B만 차단하고 A를 바꿔도 같은 세계 안에서 C가 불변인가"를 엄밀하게 검사한다.

세 가지 개입, 8케이스 전수검사:

1. **A가 B를 바꾸는가** (통상 진행, 개입 없음) — `source_active`의 두 값 전수검사.
   `mediator_active`가 그대로 따라감.
2. **B가 C를 바꾸는가** — `source_active=True`로 고정, `step_with_mediator_override`로
   `mediator_active`만 False/True로 강제. `outcome_active`가 달라져야 함.
3. **B를 막으면 A→C 효과가 사라지는가** (mediator 판정의 핵심) — `mediator_active`를
   False로 고정한 채 `source_active`를 0/1로 바꾸고, 다시 True로 고정한 채 같은 걸 반복.
   **같은 world, 같은 step 함수** 안에서 `mediator_active`만 진짜로 독립 변수이므로,
   GT-1과 달리 세계를 바꾸지 않고 B만 차단한 엄밀한 검사다.

결함 주입 sanity: `outcome_active`가 `mediator_active` 대신 `source_active`를 직접 읽는
가짜 world를 만들면 intervention 3이 실제로 실패를 잡아낸다
(`tests/test_ground_truth.py::test_world_m1_detects_a_world_where_C_bypasses_the_mediator`).

**GT-M1은 현재 답안지 레벨에만 존재한다.** B가 실제로 연구할 수 있는 A-compatible 실행
가능 world(엔진 레벨 public control 포함)는 아직 없다 — GT-2/GT-3와 함께 공통
`ResearchWorldAdapter` 경로가 설계된 뒤에 같은 경로의 세 번째 사용자로 추가될 예정
(`CURRENT_STATE.md` 참고).

### GT-2 — Direct: `source_active → outcome_active`, 중간 상태 없음

`ground_truth/world2_direct.py`에 정의된 전용 2필드 순수함수 world.
규칙은 `outcome_active := source_active`가 전부.

- `source_active`의 두 값(True/False) 전수검사
- `outcome_active`의 이전 값이 결과에 영향을 주지 않음을 확인 (자기 자신을 통한 숨은 mediator 배제)
- `step()` 함수 소스 자체를 읽어 `state.outcome_active`를 참조하지 않는지 정적으로 확인

### GT-3 — Conditional: `D=true일 때만 A → C` (`C := A AND D`)

`ground_truth/world3_conditional.py`. 상태는 `source_active`(A) / `gate_enabled`(D) /
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
- **AMBIGUOUS** — public control/observable만으로는 결론을 못 냄 (예: GT-1의 "충돌 불가"
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

## 현재 결과 (2026-09-23)

4/4 VALID (GT-1, GT-M1, GT-2, GT-3). `sealed/`에 네 파일 모두 봉인됨.

## 한계

- GT-1은 A0의 `execution.ticks=4`, 고정된 격자·입자 배치 안에서만 검증했고, 위에서 설명한
  이유로 정답지가 아니라 참고용 sanity test다
- GT-M1/GT-2/GT-3는 A0 물리와 완전히 분리된 synthetic world라서, "A0 안에도 순수
  mediator/direct/conditional 관계가 있는가"는 이 패키지가 답하지 않는다
- GT-M1/GT-2/GT-3는 아직 답안지 레벨에서만 존재한다. B가 실제로 연구 가능한 A-compatible
  실행 world(엔진 레벨 public control 포함)는 별도 설계가 필요하다 — `CausalWorldSpec`이
  `causal_hypothesis.py`(prediction 어휘가 물리 필드에 폐쇄), `exploration_control.py`
  (control 필드가 A0 물리 어휘에 화이트리스트로 고정) 등 B0 모듈 20개에 구조적으로 얽혀
  있어서, "AExecutor만 얇게 감싸면 된다"는 낙관적 가정이 실제 조사에서 틀린 것으로 확인됐다
- 이 패키지는 **정답을 만드는 도구**이지 B0.7을 채점하는 도구가 아니다. B가 찾아낸 구조와
  `sealed/*.json`을 비교하는 것은 별도 도구의 일이며, 그 도구도 B0.3+ 모듈을 이 패키지
  안으로 끌어들이면 안 된다
