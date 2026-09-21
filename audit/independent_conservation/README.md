# 독립 보존 검증기

## 왜 필요한가

A 세계의 가장 기본적인 주장은 **"물질과 에너지가 보존된다"**이다. 커널은 매 tick 이걸 스스로 검사한다.

```python
# engine/deterministic/environment_kernel.py:298
resources = state.conserved_resources(spec)        # 시작 전에 센다
...                                                # 물리 진행
if result.conserved_resources(spec) != resources:  # 끝나고 다시 센다
    raise AssertionError("environment tick changed conserved resources")
```

**세기 전과 세기 후가 같은 함수다.** 그 함수가 잘못 세면 양쪽이 똑같이 잘못 세니까 "보존됐다"가 나온다.

체중계가 항상 5kg 적게 나오는데, 아침과 저녁에 재보고 "변화 없네, 정상" 하는 것과 같다. 변화는 없지만 **숫자 자체가 틀렸다.**

## 무엇이 다른가

`engine/`에서 **아무것도 import 하지 않는다.** 기록된 스냅샷의 숫자와 세계 명세의 파라미터만 읽고 직접 센다.

두 가지를 **따로** 묻는다:

| 질문 | 의미 |
|---|---|
| **보존** | tick 사이에 총량이 그대로인가? |
| **일치** | 커널이 기록한 수치가 독립 집계와 같은가? |

**두 번째가 커널이 자기에게 못 묻는 질문이다.** 물질이 실제로 보존되면서도 커널이 그 양을 틀리게 보고할 수 있다.

## 사각지대의 모양 — 생각보다 좁다

결함 주입 실험을 세 번 했고, 처음 두 번은 **엔진이 잡았다.** 이게 중요한 정보다.

| 심은 결함 | 엔진 | 왜 |
|---|---|---|
| 첫 번째 칸을 빼고 셈 | **잡음** | 물질이 그 칸을 드나들면 빠지는 양이 tick마다 달라져서 전후 비교에 걸림 |
| 수증기 잠열 항 누락 | **잡음** | 수증기가 이동하면 누락량이 tick마다 달라짐 |
| **물을 2배로 셈** (상변화 없는 세계) | **못 잡음** | 틀린 양이 **전 기간 일정**해서 전후 비교로는 안 걸림 |

**결론: 엔진의 자기검사는 "상태에 따라 변하는 오류"에는 강하고, "일정하게 틀리는 오류"에는 눈이 멀었다.**

독립 집계는 후자를 위해 존재한다. 엔진이 아무것도 검사하지 않는다는 뜻이 아니다.

## 실제 결과

```
엔진 자체 보존 검사 : 통과 — 매 tick 보존 성립으로 판정하고 완주
독립 보존 검증기     : 거부, 4건 발견
   [kernel_water_tally_differs] tick=1 water
     kernel recorded 192, independent recount is 112
```

실제 총량이 112인데 커널은 내내 192라고 보고하면서, 스스로는 "192 = 192, 보존됨"이라고 판정했다.

이 실험은 `tests/test_audit_independent_conservation.py::test_catches_a_constant_miscount_the_kernel_cannot_see` 로 영구화되어 있다. 반대쪽(엔진이 잡는 경우)도 `test_a_state_dependent_miscount_is_caught_by_the_kernel_itself` 로 기록해서 사각지대를 과장하지 않게 했다.

## 무엇을 세는가

| 항목 | 구성 |
|---|---|
| **에너지** | 입자 운동에너지 + 열 + 결합 저장에너지 + 용해광물×변환에너지 + 수증기×기화에너지 |
| **물** | 액체 물 + 수증기 (상변화는 둘 사이를 옮길 뿐 만들거나 없애지 않음) |
| **물질 목록** | 용질 종류별 합계, 고체 광물은 녹는 용질 종류에 합산 |
| **입자 수** | 종류별 개수 |
| **운동량** | 질량 × 운동에너지 × 방향, **결합 안 된 입자만** |

에너지에서 **용해광물과 수증기의 잠열을 반드시 세야 한다.** 녹거나 증발할 때 저장된 에너지가 침전·응축 때 다시 나오므로, 안 세면 상변화가 "에너지가 무에서 생겨난 것"처럼 보인다.

## 구현 중 실제로 잡힌 것

초안에서 입자 방향을 `"north"`/`"south"`로 가정했는데 실제 기록은 `"N"`/`"S"`였다. **독립 구현이라 엔진 값을 물려받지 않았고, 그래서 첫 실행에서 바로 드러났다** — 만약 엔진에서 import 했다면 이 실수 자체가 불가능했겠지만, 동시에 엔진의 방향 정의가 틀렸을 때 그걸 잡을 수도 없었을 것이다.

알 수 없는 방향 코드는 **오류로 처리한다.** 조용히 건너뛰면 그 입자의 운동량이 사라진다.

## 사용법

```bash
# 모든 세계를 실행하고 매 tick 재집계
python run_independent_conservation_audit.py --worlds

# D: vault에 spec.json이 함께 저장된 trace
python run_independent_conservation_audit.py --vault

# 특정 실행
python run_independent_conservation_audit.py <run_dir> --spec <spec.json>
```

종료 코드: 발견 사항이 있으면 `1`, 전부 보존이면 `0`.

**명세 파일이 필요하다.** 질량과 잠열 상수는 스냅샷에 안 들어 있고 세계 명세에만 있다. vault trace 중 `spec.json`을 함께 저장한 것만 감사할 수 있다.

## 현재 결과 (2026-09-21)

| 대상 | 결과 |
|---|---|
| 세계 명세 4개 (v1~v4) | 보존 성립, 커널 집계와 일치 |
| vault trace 4개 (theory-revision world-0~3) | 보존 성립, 커널 집계와 일치 |

합계 8/8.

## 한계

- **명세 준수는 검사하지 않는다.** "물질이 보존됐는가"만 보고 "물리 규칙대로 움직였는가"는 안 본다. 물이 순간이동해도 총량만 맞으면 통과한다
- **결합 구조·위치는 안 본다.** 총량 중심 검사다
- **spec.json 없는 trace는 감사 불가.** vault trace 12개 중 4개만 가능하다
- **같은 런타임 공유.** Python과 정수 연산은 엔진과 공유한다
- **커널 집계 대조는 기록에 있을 때만.** `conserved_resources`/`energy_account`가 payload에 없으면 보존만 검사하고 일치는 못 본다

## 발견 코드

| 코드 | 의미 |
|---|---|
| `energy_not_conserved` | tick 사이 에너지 총량 변화 |
| `water_not_conserved` | 물+수증기 총량 변화 |
| `inventory_not_conserved` | 물질 목록 변화 |
| `particle_counts_not_conserved` | 입자 수 변화 |
| `kernel_water_tally_differs` | **커널 기록과 독립 집계 불일치 (물)** |
| `kernel_inventory_tally_differs` | 커널 기록과 독립 집계 불일치 (물질) |
| `kernel_energy_tally_differs` | 커널 기록과 독립 집계 불일치 (에너지) |
| `snapshot_unreadable` | 스냅샷을 정수 세계로 읽을 수 없음 (float, 미지 방향 등) |
| `spec_unreadable` / `manifest_missing` / `records_missing` / `no_snapshots` | 입력 문제 |
