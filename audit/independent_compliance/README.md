# 독립 명세 준수 검증기

## 왜 필요한가

기존 검사 두 개가 확인하는 것:

- `independent_trace` — **기록이 정확한가**
- `independent_conservation` — **총량이 보존되는가**

**둘 다 "규칙을 어긴 경로"를 못 본다.** 물질이 사라지지만 않으면 어디로 어떻게 가든 통과한다.

구체적으로, 다음은 전부 **총량이 완벽히 보존되고 기록도 일관적이다**:

| 위반 | 총량 |
|---|---|
| 물이 `blocked_edges`로 선언된 막힌 벽을 통과 | 그대로 |
| 물이 인접하지 않은 먼 칸으로 순간이동 | 그대로 |
| `max_water_transfer` 한도를 넘겨 한 번에 이동 | 그대로 |
| 금지된 상변화가 일어남 | 그대로 (물+수증기 합은 유지) |
| 증발 온도 문턱 아래에서 증발 | 그대로 |
| 선언되지 않은 곳에서 에너지가 드나듦 | 장부에 기록되면 그대로 |

은행 금고에 돈이 오늘 100만원, 내일도 100만원이면 "정상"이라 판정하는 것과 같다. **그 사이에 돈이 벽을 통과해 옆방에 갔다 왔어도 모른다.**

## 왜 지금 중요한가

**2026-09-20 사건이 정확히 이 유형이었다.**

`exactly one ordinary event` — tick당 사건을 하나만 처리한 그 결함은:
- 총량을 어기지 않았다
- 기록도 일관적이었다
- 그냥 **규칙이 의도와 달랐을 뿐**이고, 두 달 가까이 아무도 몰랐다

그리고 앞으로 화학·고분자를 추가하면 규칙이 훨씬 복잡해진다. 결합 조건, 촉매, 사슬 절단 — 규칙이 늘어날수록 "총량은 맞는데 경로가 틀린" 여지가 커진다.

## 무엇을 검사하는가

trace의 **단계 이름**이 어떤 규칙을 적용할지 결정한다.

| 단계 | 규칙 |
|---|---|
| `causal` | 입자·결합·열만. **물·수증기·광물·용질은 건드리면 안 됨** |
| `horizontal_*` / `vertical_*` | 그 위상이 정한 짝끼리만, 막힌 벽 통과 금지, 한도 이내, 있는 만큼만 |
| `external_energy` | 선언된 경계에서만, 선언된 양만큼. 물질은 못 건드림 |
| `mineral_conversion` | 제자리에서 고체↔용해, 물 있는 칸만, 온도 조건, 열 교환 = 양×비용 |
| `water_phase_change` | 제자리에서 물↔수증기, 온도 조건, 한도 이내, 잠열 = 양×상수 |

**짝 균형 검사가 핵심이다.** 한쪽이 잃은 만큼 다른 쪽이 얻어야 한다. 이게 안 맞으면 물질이 어디선가 나타났거나 사라진 것이고, 총량이 맞더라도 경로가 불가능하다.

## 결함 주입 — 실효성 증명

각 위반은 **"기록된 실행이 이미 어기고 있는 규칙을 선언"**하는 방식으로 주입했다. 기록은 손대지 않는다.

| 시험 | 보존 검증기 | 준수 검증기 |
|---|---|---|
| 막힌 벽 통과 | **통과** | 거부 16건 (`blocked_edge_crossed`) — 열 64, 물 12 |
| 먼 칸 순간이동 | **통과** | 거부 4건 (`transport_did_not_balance`) |
| 이동 한도 초과 | **통과** | 거부 95건 (`transfer_limit_exceeded`) |
| 금지된 상변화 | **통과** | 거부 11건 (`phase_changed_when_disabled`) |
| 온도 문턱 위반 | **통과** | 거부 4건 (`evaporated_below_declared_heat`) |

**보존 검증기가 전부 통과하는 것이 주장의 일부다.** 그게 두 번째 검사기가 필요한 이유를 증명한다.

전부 `tests/test_audit_independent_compliance.py`로 영구화했다.

## 구현 중 실제로 잡힌 내 실수

초안에서 `causal` 단계가 "셀을 전혀 건드리면 안 된다"고 규칙을 잘못 잡았다. 첫 실행에서 v1 세계가 1건 걸렸고, 추적해보니 **열(heat)이 변한 것**이었다.

열은 `causal.heat`에 속한다 — 입자가 움직이면 열도 같이 재배치되는 게 정상이다. 내 규칙이 너무 엄격했다.

규칙을 "causal은 입자·결합·**열**을 다루고, 물·수증기·광물·용질은 못 건드린다"로 정정했다. **발견을 곧바로 "엔진 버그"로 단정하지 않고 실제로 추적한 결과다.**

## 사용법

```bash
python run_independent_compliance_audit.py --worlds
python run_independent_compliance_audit.py --vault
python run_independent_compliance_audit.py <run_dir> --spec <spec.json>
```

종료 코드: 위반이 있으면 `1`, 전부 준수면 `0`.

## 현재 결과 (2026-09-21)

| 대상 | 결과 |
|---|---|
| 세계 명세 4개 (v1~v4) | 준수. 단계 192개 (전송 96) 검사 |
| vault trace 4개 | 준수. 단계 64개 (전송 32) 검사 |

합계 8/8.

## 한계

- **명세 파일이 필요하다.** vault trace 12개 중 4개만 감사 가능
- **세밀한 이동량 공식은 검증하지 않는다.** "한도 이내인가"는 보지만 "정확히 `(차이)//2`만큼인가"는 안 본다. v4의 `physical_scale.transfer`는 확산 계수가 얽혀 있어 재구현하면 커널을 베끼는 꼴이 된다
- **격자가 2칸 이하인 축에서는 짝 균형 검사를 건너뛴다.** 양쪽 이웃이 같은 칸이 되어 한 위상이 같은 짝을 두 번 만날 수 있다
- **입자 물리는 검사 안 한다.** 충돌·결합 규칙 준수는 미검증 영역이다
- **용질 이동 공식 미검증.** 운반(carried)과 확산(diffused)의 분해는 커널 내부 계산이라 총량 균형만 본다

## 발견 코드

| 코드 | 의미 |
|---|---|
| `blocked_edge_crossed` | **막힌 벽으로 물질·열이 이동** |
| `transport_did_not_balance` | **한쪽이 잃은 양과 다른 쪽이 얻은 양이 다름** (순간이동·생성·소멸) |
| `transport_outside_phase_pairs` | 이 위상이 짝짓지 않는 칸이 변함 |
| `transport_between_non_neighbours` | 인접하지 않은 칸끼리 이동 |
| `transfer_limit_exceeded` | 선언된 한도 초과 |
| `moved_more_than_present` | 있는 것보다 많이 가져감 |
| `causal_stage_touched_environment` | causal 단계가 물·수증기·광물·용질을 건드림 |
| `solid_mineral_moved` | 수송 단계가 고체 광물을 옮김 |
| `elevation_changed` | 지형 고도가 변함 |
| `energy_crossed_undeclared_boundary` | 선언 안 된 곳에서 에너지 출입 |
| `energy_input_above_declared` / `energy_output_above_declared` | 선언량 초과 |
| `energy_ledger_went_backwards` / `energy_ledger_above_declared_input` | 외부 장부 이상 |
| `mineral_converted_when_disabled` / `_above_limit` / `_without_water` | 광물 변환 규칙 위반 |
| `mineral_conversion_unbalanced` / `_energy_mismatch` | 고체↔용해 불균형, 열 교환 불일치 |
| `dissolved_below_declared_heat` / `precipitated_above_declared_heat` | 온도 조건 위반 |
| `phase_changed_when_disabled` / `_above_limit` / `_unbalanced` / `_energy_mismatch` | 상변화 규칙 위반 |
| `evaporated_below_declared_heat` / `condensed_above_declared_heat` | 상변화 온도 조건 위반 |
| `phase_not_declared` / `unrecognised_stage` / `unknown_phase` | 명세에 없는 단계 |
