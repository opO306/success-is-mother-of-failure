# causal 충돌 의미 v4 — 설계

**상태:** **초안. 미승인.**
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

## 4. 미결 — 다음 세션에서 확정할 것

- v4 포맷 분기를 코드에서 어떻게 표현할지 (`FORMAT_V4`를 causal에도
  둘지, 아니면 다른 이름). **environment 쪽 `FORMAT_V4`와 이름이
  겹치므로 혼동 주의** — environment의 v4는 물리 단위·flux 계약이고
  전혀 다른 의미다
- known-defect 테스트 이름·문서를 정확히 어떻게 재규정할지
- `StructureState`를 v3 위에서 시작할지, v4가 확정된 뒤 시작할지
