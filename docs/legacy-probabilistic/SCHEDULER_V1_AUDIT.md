# scheduler-v1 사건률·시간 의존성 전수 감사

**작성:** 2026-09-21
**대상 코드:** `engine/sequence/` (dual-gcp-observer-v1 실행에 쓰인 상태)
**목적:** 연속시간 스케줄러 v2 설계 **이전에**, 현재 모든 사건의 가중치 출처와 시간 의존성을 분류한다.
**원칙:** 기존 `weight`를 그대로 `λ`로 이름만 바꾸면 사람이 정한 임시값을 물리 사건률로 포장하게 된다. 그래서 코딩보다 이 표가 먼저다.

---

## 1. 핵심 결함 요약 (코드 확인 완료)

### 1-1. 두 개의 카운터가 있고, 둘 다 물리 시간이 아니다

| 카운터 | 위치 | 증가 방식 | 용도 |
|---|---|---|---|
| `ordinary_events` | [nonliving_world.py:42](../../engine/sequence/nonliving_world.py) | 사건 1개 실행마다 `+1` | 모든 `interval` 법칙의 기준 |
| `sequence.time` | [substrate.py:159](../../engine/sequence/substrate.py) | 상태 전이마다 `+1` | `WorldEvent` 타임스탬프 |

둘 다 **무엇이 선택됐든 상관없이 `+1`**이다. 후보 수가 몇 개였는지, 그 사건이 물리적으로 얼마나 드문 일이었는지가 시간에 반영되지 않는다.

### 1-2. 선택식에 서로 다른 단위가 섞여 있다

[spatial_sequence.py:752-758](../../engine/sequence/spatial_sequence.py):

```python
moves = tuple((item.site, dx, dy) for item in state.locations for dx, dy in DIRECTIONS)
rotations = spatial_rotation_candidates(state)
flexes = spatial_flex_candidates(state)
reactions = spatial_event_candidates(state)
reaction_weight = sum(item.weight for item in reactions)
sample = chance.choice_index(len(moves) + len(rotations) + len(flexes) + reaction_weight)
```

- `moves`, `rotations`, `flexes` → **가중치 필드가 아예 없음**. `len()`으로 세어져 각각 암묵적 가중치 `1`.
  - 확인: `SpatialRotationCandidate`([:216](../../engine/sequence/spatial_sequence.py))와 `SpatialFlexCandidate`([:227](../../engine/sequence/spatial_sequence.py))에는 `weight` 필드가 정의되어 있지 않다.
- `reactions` → `EventCandidate.weight`([substrate.py:257](../../engine/sequence/substrate.py)) 합계. 이 값은 열에너지·결합결함에서 유도된 **큰 정수**가 될 수 있다.

**결과: "이동 1칸"과 "결합 해제"가 같은 추첨 분모에서 경쟁하는데, 전자는 무조건 1, 후자는 물성 기반 수백~수천.** 두 사건의 상대 빈도는 물리가 아니라 이 단위 불일치가 정한다.

### 1-3. 희석이 이중으로 일어난다

1. **1차 희석** — `moves`는 `물질 자리 수 × 방향 4`다. 물질이 늘면 분모가 선형 증가 → 특정 반응이 뽑힐 확률 하락.
2. **2차 왜곡** — 그런데 `ordinary_events`는 뭐가 뽑히든 `+1`이므로, `interval` 기반 법칙(막 성장 등)은 **여전히 고정 주기로 발동**한다.

→ 세계가 복잡해질수록 **사건 종류 사이의 상대 속도 비율 자체가 뒤틀린다.** 단순히 전체가 느려지는 게 아니다. 구획이 1개에서 2개가 되는 순간 그 세계의 실효 물리 법칙이 달라진다.

---

## 2. 사건별 가중치 출처 전수 분류

### 2-1. ordinary 사건 (매 step 정확히 1개 선택)

| 사건 | 정의 위치 | 가중치 | 출처 판정 | v2 처리 |
|---|---|---|---|---|
| `spatial_move` | [spatial_sequence.py:753](../../engine/sequence/spatial_sequence.py) | 없음 (자리당 4방향, 각 1) | **사람이 정한 구조** — 확산계수·질량·점성 개념 없음 | 국소 이동률 λ 정의 필요 |
| `spatial_rotate` | [:530](../../engine/sequence/spatial_sequence.py) | 없음 (후보당 1) | **사람이 정한 구조** — `SPATIAL_ROTATION_COST` 문턱만 있고 율은 없음 | 활성화 장벽 기반 λ |
| `spatial_flex` | [:622](../../engine/sequence/spatial_sequence.py) | 없음 (후보당 1) | **사람이 정한 구조** — 동일 | 활성화 장벽 기반 λ |
| `bind` / `fold` | [substrate.py](../../engine/sequence/substrate.py) `_binding_candidates` | 결합에너지 기반 | **물성에서 부분 유도** | 활성화 장벽으로 통일 |
| `unbind` / `unfold` | [substrate.py:386-396](../../engine/sequence/substrate.py) | `thermal_factor * (1 << min(defect,20))` | **물성에서 비교적 강하게 유도** (열에너지 − 결합에너지, 결함 지수) | 같은 단위의 λ로 환산 |
| `backbone_cleave` / `ligate` / `cyclize` | substrate | `EventCandidate.weight` | 부분 유도 | 활성화 장벽 |

**주의:** `unbind`의 `1 << defect`는 결함 1당 가중치 2배다. `defect`가 20이면 가중치가 **100만 배**가 된다. 이 지수 스케일이 `moves`의 가중치 1과 같은 분모에 들어간다.

### 2-2. interval 기반 환경 사건 (고정 주기 발동)

[nonliving_world.py:259-316](../../engine/sequence/nonliving_world.py)에서 전부 `state.ordinary_events % law.interval == 0`으로 판정.

| 법칙 | GCP 실행값 | 정의 위치 | 내부 가중치 | 출처 판정 |
|---|---:|---|---|---|
| `energy_law` | interval **1000000** | [run_nonliving_world_probe.py:75](../../run_nonliving_world_probe.py) | `diffusion_divisor=8`, `absorption_per_site=1` | 사람이 정한 주기 |
| `face_law` (확산) | interval **20** | [:84](../../run_nonliving_world_probe.py) | `diffusion_divisor=8` | 사람이 정한 주기 |
| `chemistry_law` (촉매) | interval **3** | [:93](../../run_nonliving_world_probe.py) | `spontaneous_weight=1`, `catalytic_weight=1` (둘 다 기본값) | **전부 사람이 정한 임시값** |
| `material_law` (복사) | interval **2** | [:105](../../run_nonliving_world_probe.py) | `activation_energy=1`, `spontaneous_weight=1`, `affinity_weight=1`, `dissolution_weight=1` | **전부 기본값 1** |
| `boundary_law` (막 성장·수축) | interval **4** | [:107](../../run_nonliving_world_probe.py) | `weight=1` (기본값) | **전부 사람이 정한 임시값** |

**이 표의 의미:** 복사·촉매·막 성장의 모든 가중치가 기본값 `1`이다. 즉 GCP 실험에서 관찰된 "복사 38,409회 vs 촉매 6,071만 회" 같은 비율은 물성이 만든 게 아니라 **interval 2 vs 3과 후보 개수 차이가 만든 것**이다.

### 2-3. 관찰자 주기 (세계에 영향 없음, 단 기록 해상도를 결정)

| 항목 | 기본값 | 위치 |
|---|---:|---|
| `observer_census_events` | 10,000 | [run_nonliving_face_until.py:37](../../run_nonliving_face_until.py) |
| `observer_ring_events` | 20,000 | [:38](../../run_nonliving_face_until.py) |
| `observer_post_trigger_events` | 20,000 | [:39](../../run_nonliving_face_until.py) |
| `lineage_checkpoint_events` | 10,000 | [:34](../../run_nonliving_face_until.py) |

이들도 `ordinary_events` 기준이므로, v2에서 `physical_time` 도입 시 **관찰 해상도가 물리 시간에 대해 불균일해진다**는 점을 함께 처리해야 한다(세계가 복잡할 때 같은 10,000 이벤트가 더 짧은 물리 시간을 덮음).

---

## 3. 판정 요약

| 분류 | 사건 | 개수 |
|---|---|---:|
| **물성에서 비교적 강하게 유도** | `unbind`/`unfold` (열-결합에너지 차, 결함 지수) | 1계열 |
| **물성에서 부분 유도** | `bind`/`fold`, `cleave`/`ligate`/`cyclize` | 2계열 |
| **사람이 정한 구조 (가중치 없음 = 암묵적 1)** | `move`, `rotate`, `flex` | 3계열 |
| **사람이 정한 임시값 (전부 기본값 1)** | 복사, 촉매, 막 성장·수축 | 3계열 |
| **사람이 정한 고정 주기** | 5개 `interval` 법칙 전부 | 5개 |

**결론: 현재 가중치 중 물성에서 온전히 유도된 것은 사실상 `unbind` 계열뿐이다.** 나머지는 전부 구조적 암묵값(1) 또는 명시적 임시값(1)이거나 고정 주기다.

---

## 4. v2 설계에 주는 제약

1. **`weight`를 `λ`로 직접 이름 변경 금지.** 위 표에서 "사람이 정한" 6계열은 λ로 쓰기 전에 물리적 근거를 새로 정의해야 한다.
2. **공통 단위를 먼저 정의해야 한다.** 현재 `moves`의 1과 `unbind`의 100만이 같은 저울에 있다. 활성화 장벽·열에너지를 공통 기준으로 삼아 전 사건을 같은 차원으로 환산하는 정의가 선행되어야 한다.
3. **`interval` 법칙 5개는 전부 λ로 전환 대상이다.** 고정 주기는 물리 시간이 아니다. 특히 `energy_law`의 interval 1,000,000은 사실상 "거의 발동 안 함"을 뜻하는데, 이것이 의도된 물리인지 확인이 필요하다.
4. **`ordinary_events`는 사건 수로 보존하고, `physical_time`을 별도 도입한다.** 기존 v1 결과와의 비교 가능성을 위해 전자를 지우면 안 된다.
5. **관찰자 주기도 물리 시간 기준으로 재정의해야** 세계 복잡도에 따라 기록 해상도가 흔들리지 않는다.

---

## 5. 추가 확인 완료 항목

### 5-1. `pair_score`는 물성 유도가 맞다 — 판정 상향

[substrate.py:19-24, 61-65](../../engine/sequence/substrate.py):

```python
BASE_PROPERTIES = ((-1,-1), (-1,+1), (+1,-1), (+1,+1))   # 네 기호의 2D 물리 좌표
def pair_score(left, right):
    lx, ly = BASE_PROPERTIES[_symbol(left)]
    rx, ry = BASE_PROPERTIES[_symbol(right)]
    return -(lx*rx + ly*ry)                               # 내적의 음수
```

네 기호가 2차원 좌표계의 네 사분면에 **대칭적으로** 배치되어 있고, 친화도는 두 좌표의 내적에 음수를 취한 값이다. 즉 반대 방향일수록 강하게 끌린다. **기호 이름(A/C/G/T)은 `DEFAULT_LABELS`로 분리되어 있고 물리 계산에 쓰이지 않는다** — 헌법 18조(기호에 고수준 의미 배정 금지)를 지키는 구조다. 값 범위는 `-2, 0, +2`.

이는 사람이 자의적으로 고른 테이블이 아니라 **대칭적 기하에서 유도된 값**이다. 판정을 "물성 유도"로 상향한다.

### 5-2. `bind` 가중치 = 결합에너지 그 자체 — 판정 상향

[substrate.py:339-346](../../engine/sequence/substrate.py):

```python
energy = sum(pair_score(...) for offset in range(length))
if energy <= 0: continue
candidates.append(EventCandidate("bind", contact, energy))
```

가중치가 별도 계수 없이 **결합에너지와 동일**하다. `unbind`와 같은 물리량 계열이므로 이 둘은 이미 같은 차원에 있다. 판정을 "물성 유도"로 상향한다.

### 5-3. 상수 두 개 확인

| 상수 | 값 | 위치 | 판정 |
|---|---:|---|---|
| `SPATIAL_ROTATION_COST` | **1** | [spatial_sequence.py:27](../../engine/sequence/spatial_sequence.py) | 사람이 정한 문턱값. 회전의 *율*이 아니라 *가능 여부*만 결정 |
| `BACKBONE_COST` | **2** | [substrate.py:26](../../engine/sequence/substrate.py) | 사람이 정한 값. `pair_score` 최대치(+2)와 같은 크기 |

`BACKBONE_COST=2`가 `pair_score` 최대값과 같다는 점은 우연이 아닐 수 있으나, 코드에 근거 주석이 없다. 설계자 확인 필요.

### 5-4. 아직 미확인

- `diffusion_divisor=8`, `absorption_per_site=1`의 근거 (확산 법칙 내부).
- `MAX_CONTEXT_MULTIPLIER=64`의 근거와 `context_multiplier`가 가중치를 최대 64배까지 곱하는 구조의 물리적 의미.

---

## 6. 감사 후 최종 판정 (5절 반영)

| 분류 | 사건 | 비고 |
|---|---|---|
| **물성 유도 (확정)** | `bind`/`fold`, `unbind`/`unfold` | 대칭 기하 → `pair_score` → 결합에너지 → 가중치. 일관된 단위 |
| **물성 부분 유도** | `cleave`/`ligate`/`cyclize` | `BACKBONE_COST=2` 등 임의 상수가 섞임 |
| **사람이 정한 구조 (가중치 없음 = 암묵적 1)** | `move`, `rotate`, `flex` | **λ 정의 필요** |
| **사람이 정한 임시값 (기본값 1)** | 복사, 촉매, 막 성장·수축 | **λ 정의 필요** |
| **사람이 정한 고정 주기** | 5개 `interval` | **전부 λ 전환 대상** |

**핵심 결론 (수정):** 최초 판정보다 물성 기반 영역이 넓다 — `bind`/`unbind` 계열은 대칭 기하에서 일관되게 유도된 진짜 물리량이다. 문제는 **그 물리량 계열과, 가중치가 아예 없는 `move`/`rotate`/`flex`(암묵값 1), 그리고 전부 기본값 1인 복사·촉매·막 성장이 하나의 추첨 분모에 함께 들어간다**는 점이다.

즉 v2의 과제는 "물성 가중치를 새로 만드는 것"이 아니라 **이미 있는 물성 계열(`pair_score` 기반 에너지)을 기준 단위로 삼아, 나머지 6계열을 같은 차원으로 환산하는 것**이다. 이 방향이 새 임의값을 최소화한다.
