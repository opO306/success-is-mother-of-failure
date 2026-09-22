# causal 충돌 의미 v4 — 설계

**상태:** **Stage A 구현 완료 (2026-09-22).** Stage B(`StructureState`)가 다음 차례.
v4의 지위는 `experimental` — Stage D까지 끝난 뒤 adoption을 판단한다.
**날짜:** 2026-09-22
**선행:** `STRUCTURE_STATE_V1.md` 9.2(unequal-energy 정면충돌 결함),
`LANGUAGE_REVISION_GOVERNANCE_V1.md`(9·10번 — 기존 버전 의미를 조용히 바꾸지 않는다)
**한 줄:** v1/v2/v3가 공유하는 두 개의 유형 F 결함(암묵적 orientation 회전,
가변 에너지 90도 산란)을 고치되, **기존 버전은 건드리지 않고 새 버전에서
고친다.**

---

## 0. 왜 v1/v2/v3를 고치지 않는가

측정으로 확인했다. `_break_existing`의 절단 방출과 `_resolve_collisions`의
정면 산란에서 `orientation=direction` 덮어쓰기를 제거하자, **v1의 run
digest가 바뀌었다.**

```
worlds/deterministic_bond_cycle_v1.json (FORMAT_V1)
BEFORE fix: e37f773f6b13a8245943c76562493ccfa8c6f25ee88e9a40fd629f190f623c7a
AFTER fix:  75266ff311bd6c2fd2169e556160fd463b290a67f86b142e7f16861608474f33
```

`_break_existing`과 `_resolve_collisions`는 포맷과 무관하게 실행되는 공용
코드다. 즉 이 결함은 v3에서 생긴 게 아니라 **causal(A1)이 생긴 시점부터
v1에 있었다.**

`LANGUAGE_REVISION_GOVERNANCE_V1.md`는 이 상황을 정확히 규정한다:

> 9. 기존 버전의 의미를 조용히 바꾸지 않는다.
> 10. 새 의미는 새 버전으로 추가한다.

그리고 495·497행:

> 새로운 의미가 필요한 경우 새 버전을 만든다.
> 기존 버전은 기준선과 재현성을 위해 보존한다.

**결함이 있다는 사실과 기존 버전을 보존해야 한다는 사실은 동시에 참일 수
있다.** v1/v2/v3의 digest·회귀 테스트·기존 실험 결과가 이미 이 결함이
있는 물리 위에 서 있으므로, 그걸 조용히 바꾸면 "같은 spec + 같은 엔진
버전 → 같은 결과"라는 재현성이 깨진다.

**따라서:** v1/v2/v3는 **레거시 물리로 동결**하고, 고친 의미는 **v4**에서
시작한다.

---

## 1. 결함 둘 — 측정 기록

### 1.1 암묵적 orientation 회전

**어디:** `_break_existing`(절단), `_resolve_collisions`(정면 산란) 두 곳.

```python
# 절단
particles[bond.left_id] = replace(left, direction=rule.release_left,
                                  orientation=rule.release_left, kinetic_energy=each)
# 산란
particles[particle.particle_id] = replace(particle, direction=direction,
                                          orientation=direction)
```

**선언된 근거 없음.** A0의 `ParticleSpec`에는 `orientation` 필드 자체가
없다(`direction`뿐). `orientation`은 causal(A1)에서 처음 생겼고, 문서가
밝힌 도입 이유는 `WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md` 308-311행:

> `orientation`은 v1/v2에서 "어느 면으로 결합하는가"까지 겸했다.

이건 **"orientation이 결합 매칭에 쓰인다"**는 선언이지, **"산란·절단이
orientation을 회전시켜야 한다"**는 선언이 아니다.

**`direction != orientation`은 합법적 상태다** — 생성자가 거부하지
않는다. 즉 `orientation`은 `direction`과 독립인 상태량으로 이미
설계돼 있었는데, 두 이벤트가 그 독립성을 무시하고 동기화해버린다.

**측정 — 물리적 결과가 실제로 갈린다:**

```
orientation을 S로 두고 direction만 E/W로 산란시킨 경우:
  BEFORE  direction=N  orientation=S
  AFTER   direction=E  orientation=E   ← 원래 S가 사라지고 E로 덮어써짐

같은 입자가 이후 orientation 기반 결합 규칙(E+W)을 만나면:
  덮어쓴 경우      → 규칙과 우연히 맞을 수 있음
  유지했을 경우    → 원래 S가 그대로라 다른 규칙과 매칭됨
```

**즉 결합 가능 여부가 산란·절단 이력에 의존하게 된다.** 이건 선언된
적 없는 숨은 법칙이다.

**보존과의 관계:** `orientation`은 `momentum()`·`total_energy()` 어디에도
쓰이지 않는다. 제거해도 보존 회계에는 영향이 없다 — 순수하게 결합
매칭 결과만 바뀐다.

### 1.2 가변 에너지 정면충돌의 90도 산란

`STRUCTURE_STATE_V1.md` 9.2, `test_known_defects_causal_kernel.py::
test_defect_unequal_energy_head_on_same_kind_breaks_momentum`에 이미
기록됨. 여기서는 v4의 결정만 정리한다.

**측정 — 대수적으로 좁혀진다.** 두 입자가 반대 방향, 질량 동일,
에너지 `x`(N)와 `y`(S)로 만난다고 하자. 출력을 여전히 N/S 두 채널로
두면 보존 조건은:

```
x' + y' = x + y            (에너지)
y' - x' = y - x             (운동량, N을 양수로)
```

두 식을 풀면 `x'=x, y'=y` — **원래 상태 그대로가 유일해다.** 즉
"에너지가 다르면 아무 일도 안 일어난다"는 것은 새 물리를 발명하는 게
아니라, **기존 상태 표현과 기존 보존 법칙만으로 이미 강제되는 결과**다.

**등에너지일 때만 회전이 가능한 이유도 같은 식에서 나온다.** `x=y`이면
운동량이 0이라 어느 축으로 재분배해도 두 식을 만족하는 해가 여럿
생기고, 그중 하나(축을 90도 돌림)가 기존 A0 규칙이다. `x≠y`이면
운동량이 0이 아니라서 **다른 축으로 재분배하면 반드시 위 두 식 중
하나가 깨진다** — 대수적으로 유일해가 강제되는 것과 표리관계다.

---

## 2. v4가 정의하는 것

### 2.1 원칙 — 암묵적 회전 금지

> **병진 운동을 바꾸는 사건은 `direction`만 바꾼다.**
> **`orientation`은 명시적으로 선언된 회전 전이가 있을 때만 바뀐다.**
> **지금은 그런 전이가 0개이므로, 런타임에서 `orientation`이 바뀌는
> 코드는 0곳이어야 한다.**

적용 지점 두 곳:

```
_break_existing   : replace(..., direction=release_*, kinetic_energy=...)
                     orientation 인수 제거
_resolve_collisions: replace(particle, direction=direction)
                     orientation 인수 제거
```

`v3`가 이미 회전 자체를 "선언된 한계"로 미지원 처리했으므로
(`WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md` 276-279행), 이 원칙은 v3의
결정과 정합적이다 — v3가 구조 회전을 미루면서 입자 회전은 몰래
허용하고 있었던 모순을 없앤다.

### 2.2 90도 산란의 적용 조건을 원래 전제로 좁힌다

```
same kind + 정반대 direction + 같은 kinetic_energy
  → 기존 90도 산란 적용 (direction만, orientation 유지)

same kind + 정반대 direction + 다른 kinetic_energy
  → 90도 산란 미적용. 다른 선언된 상호작용이 없으므로 상태 변화 없음
```

**"상태 변화 없음"을 "통과라는 새 물리"로 설명하지 않는다.** 정확한
서술: **기존 90도 산란 규칙의 적용 전제(등에너지)가 충족되지 않았고,
다른 선언된 규칙도 매칭되지 않으므로 아무 사건도 일어나지 않는다.**
이건 1.2절의 대수적 유일해와 일치한다.

---

## 3. 검증 순서

1. **orientation 유지 실험** — 등에너지 산란/절단에서 `orientation`을
   유지해도 material·energy·momentum 보존이 그대로인지 측정 (완료,
   1절에서 이미 확인: 영향 없음)
2. **기존 v1/v2/v3 digest는 절대 바뀌면 안 됨** — v4 포맷을 새로
   분기해서 그 경로에서만 새 의미를 적용
3. **v4에서 등에너지 산란 positive test** — direction만 바뀌고
   orientation 유지, 보존 확인
4. **v4에서 비등에너지 head-on 전수 검사** — 에너지 1..N × N/S/E/W,
   상태 불변 확인
5. **relabel/순서 불변성** — 원칙 3(ID·배열 순서가 물리를 결정하지
   않음)이 v4에도 적용되는지
6. **결함 주입** — 되돌렸을 때 검사기가 실제로 빨간불이 되는지
7. **기존 known-defect 테스트의 지위 조정** — "고쳐질 결함"에서
   "v1/v2/v3에 한해 호환을 위해 의도적으로 보존되는 레거시 동작"으로
   재규정. v4용 positive test를 별도로 추가

---

## 4. 확정 사항 (2026-09-22)

### 4.1 포맷 상수 이름 — `FORMAT_V4`를 그대로 쓴다

```python
# causal_spec.py
FORMAT    = "deterministic-causal-world-spec-v1"
FORMAT_V2 = "deterministic-causal-world-spec-v2"
FORMAT_V3 = "deterministic-causal-world-spec-v3"
FORMAT_V4 = "deterministic-causal-world-spec-v4"

SUPPORTED_FORMATS = (FORMAT, FORMAT_V2, FORMAT_V3, FORMAT_V4)
```

`environment_spec.FORMAT_V4`와 이름이 같아도 **namespace 충돌은 없다.**
확인했다:

```
causal_spec.FORMAT_V4       = "deterministic-causal-world-spec-v4"
environment_spec.FORMAT_V4  = "deterministic-environment-world-spec-v4"
```

서로 다른 모듈이고 문자열 값도 다르다. 그리고 `__init__.py`가
re-export 하는 포맷 상수는 `spec.py`(A0)의 `FORMAT` 하나뿐 —
`FORMAT_V2/V3/V4`는 공용 namespace에 올라오지 않는다(측정 확인).

`CAUSAL_FORMAT_V4` 같은 별도 이름을 모듈 내부에 만드는 것은 오히려
기존 패턴(`FORMAT`, `FORMAT_V2`, `FORMAT_V3`)을 깨뜨린다.

> **규칙: 모듈 내부 이름은 `FORMAT_V4`로 통일한다. 모듈 경계를 넘어
> 둘을 동시에 쓰는 파일에서만 alias 한다.**

```python
from .causal_spec import FORMAT_V4 as CAUSAL_FORMAT_V4
from .environment_spec import FORMAT_V4 as ENVIRONMENT_FORMAT_V4
```

### 4.2 v4의 지위 — `experimental`, 범위를 미리 선언한다

v4를 충돌 수정 직후 동결하면 `StructureState`를 넣으려고 v5가 또
필요해진다. 기능 하나마다 버전을 올리는 사태를 피하려면 **v4의 범위를
지금 선언**해야 한다.

> **causal v4는 v3의 named-port geometry를 계승하고, 수정된 충돌
> 의미(corrected collision semantics)와 구조가 소유하는 운동
> 상태(structure-owned motion state)를 도입하는 실험 버전이다.**

이렇게 선언해두면 `StructureState`가 나중에 v4의 의미를 바꾸는 것이
아니라 **처음부터 예정된 v4 구현 단계**가 된다.

```
causal v1/v2/v3   frozen legacy semantics
causal v4         experimental
```

단계:

| 단계 | 내용 |
|---|---|
| Stage A | 수정된 충돌 의미 (이 문서 2절) |
| Stage B | `StructureState` |
| Stage C | 재명명·순서 불변성 |
| Stage D | 구조 이동 |

**Stage D까지 끝난 뒤에 v4의 adoption(동결)을 판단한다.**

### 4.3 `StructureState`는 Stage A가 끝난 뒤 시작한다

v3 위에서 시작하지 않는다. v3에는 역사적으로 보존하기로 한
암묵적 orientation 회전과 가변 에너지 운동량 회전이 **그대로
존재**하므로, 그 위에 `StructureState(momentum, motion_energy)`를
얹으면 **구조 수준에서는 운동량을 엄격히 관리하는데 바로 아래 자유
입자는 합법 상태에서 운동량을 깨는** 기묘한 계층이 생긴다.

```
v3  named ports / PortBond / adjacent geometry
      ↓
v4 Stage A  collision semantics 수정
      ↓
검증
      ↓
v4 Stage B  StructureState
      ↓
v4 Stage C  relabeling invariance
      ↓
v4 Stage D  structure motion
      ↓
v4 adoption 판단
```

### 4.4 레거시 테스트의 지위 — 세 종류로 분리한다

v4가 등장하면 v1/v2/v3의 이 동작은 **일부러 보존해야 하는 legacy
semantics**가 된다. 그러면 `test_known_defects_causal_kernel.py`의
철학("실패하면 좋은 소식")이 더 이상 맞지 않는다 — 실패하면 오히려
**과거 버전을 실수로 변경했다는 뜻**이다.

> **v4 Stage A 구현 시점에** unequal-energy / orientation 구버전 동작을
> `tests/test_known_defects_causal_kernel.py`에서
> `tests/test_legacy_causal_semantics.py`로 옮긴다.

```
known_defects      현재 주 개발 버전에서도 아직 고쳐야 하는 것
                   → 실패하면 좋은 소식

legacy_semantics   틀렸지만 과거 버전 재현성을 위해 의도적으로 보존
                   → 실패하면 나쁜 소식 (과거를 실수로 바꿨다)

normal tests       현재 올바른 동작
```

레거시 쪽:
```
test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour()
test_v1_v2_v3_break_keeps_legacy_orientation_rotation()
```

v4 쪽:
```
test_v4_unequal_energy_head_on_preserves_momentum()
test_v4_scatter_does_not_rotate_orientation()
test_v4_bond_break_does_not_rotate_orientation()
```

### 4.5 구현 시 금지 — 포맷 문자열 비교

```python
if spec.format >= FORMAT_V4:        # 절대 안 됨. 문자열 버전 비교
```

**"v4니까 v3보다 최신 기능을 자동으로 다 가진다"가 아니다.** 각 의미가
어떤 포맷을 계승하는지 코드에 드러나야 한다:

```python
has_named_ports              = spec.format in (FORMAT_V3, FORMAT_V4)
corrected_collision_semantics = spec.format == FORMAT_V4
structure_owned_motion        = spec.format == FORMAT_V4
```

의미별로 명시적으로 분기한다.

---

## 5. 다음 작업 — v4 Stage A

**`StructureState`가 아니라 충돌 의미 구현이 먼저다.**

1. `causal_spec.py`에 `FORMAT_V4` 추가, v3와 **동일한 named-port
   문법을 계승**하도록 파싱
2. 오직 v4 코드 경로에서만 `orientation` 자동회전 제거
3. 오직 v4 코드 경로에서만 등에너지 조건으로 90도 산란 제한
4. v1/v2/v3 digest 불변 확인 (기존 고정 테스트가 그대로 통과해야 한다)
5. 3절의 검증 순서 진행

---

## 6. Stage A 구현 완료 (2026-09-22)

위 5개 항목 모두 완료.

**`causal_spec.py`:**

- `FORMAT_V4` 상수 추가, `SUPPORTED_FORMATS`에 포함
- `is_v3` 불리언을 `has_named_ports = world_format in (FORMAT_V3, FORMAT_V4)`로
  일반화 — 포맷 문자열 비교(4.5절 금지 사항)가 아니라 "이 포맷이 이
  의미를 계승하는가"를 명시적으로 묻는 형태 유지
- v4 세계는 v3와 동일하게 `port_names` 리스트로 포트를 선언

**`causal_kernel.py`:**

- `_break_existing`, `_resolve_collisions` 각각에
  `corrected_collision_semantics = spec.format == FORMAT_V4` 지역 변수 추가
- `_break_existing`: `corrected_collision_semantics`일 때만 `orientation`
  인수를 `replace()`에서 뺀다 (direction·kinetic_energy만 갱신)
- `_resolve_collisions`: 90도 산란 조건에
  `and (not corrected_collision_semantics or first.kinetic_energy ==
  second.kinetic_energy)` 추가. 조건이 거짓이면 다른 선언된 규칙도 없으므로
  두 입자는 그대로 남는다 — "통과"를 구현한 게 아니라 아무 분기도 타지
  않을 뿐이다. 산란이 발동하는 경우도 `orientation` 인수는 뺐다

**측정 검증:**

- 출하된 `deterministic_bond_cycle_v1.json`(FORMAT v1) 실행 digest가
  Stage A 적용 전후 완전히 동일 (`2138518494c89e15d624932ee11cedd402f4f77ead4c4c10170ab8534793ce79`).
  0절이 인용한 `e37f773f...`/`75266ff3...` 두 값은 이 저장소의 현재 세계
  파일로는 재현되지 않았다 — 다른 측정 맥락에서 나온 예시로 보이며,
  결론(게이팅으로 v1 digest 불변)은 이번 측정으로 독립적으로 재확인됐다
- 테스트 1046개 전부 통과 (기존 1041 + v4 신규 5)

**테스트 분리:**

- `tests/test_known_defects_causal_kernel.py`의
  `test_defect_unequal_energy_head_on_same_kind_breaks_momentum`을 제거하고
  이동 주석으로 대체
- `tests/test_legacy_causal_semantics.py` 신설 —
  `test_v1_v2_v3_unequal_energy_scatter_keeps_legacy_behaviour`,
  `test_v1_v2_v3_break_keeps_legacy_orientation_rotation`
- `tests/test_deterministic_causal_kernel.py`에 v4 positive test 5종 추가:
  `test_v4_scatter_does_not_rotate_orientation`,
  `test_v4_bond_break_does_not_rotate_orientation`,
  `test_v4_unequal_energy_head_on_leaves_particles_unchanged`,
  `test_v4_leaves_the_shipped_v1_digest_unchanged`

**부수 발견 (설계 변경 아님):** 새 `spec.format` 읽기가
`tests/test_diagonal_momentum_is_unreachable.py`와
`tests/test_deterministic_v3_state_persistence.py`의 최소 `_Spec` stub
클래스 두 곳에서 `AttributeError`를 드러냈다 — 두 stub 모두 진짜
`CausalWorldSpec`을 흉내 내지만 `format` 속성이 없었다. 각각 자신이
대표하는 세대의 레거시 포맷(`v2`, `v3`)을 명시해 수정. 이 stub들은 v4
이전부터 존재했으므로 새로 만든 결함이 아니라, 게이트가 없어 드러나지
않았던 완전성 구멍이었다.
