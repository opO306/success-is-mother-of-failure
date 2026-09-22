# 세계 명세 언어 사전 v1 — B가 A를 만들 때 쓰는 언어

**상태:** 실제 코드에서 뽑은 사전. 구현된 부분은 상세, 예정된 부분은 이름과 자리만
**날짜:** 2026-09-22
**대상:** B가 A를 만들 때 쓰는 JSON 명세 형식 — `engine/deterministic/spec.py`,
`causal_spec.py`, `environment_spec.py`
**주의:** 이건 B-Language(`b_language.py`, `CapabilityManifest`/`ClaimSet`/...)와
**다른 언어다.** 그건 B가 외부에 주장을 제출하는 프로토콜이고, 이 문서는
**B가 A라는 세계 자체를 선언하는 언어**다. 헷갈리면 안 된다.
**장르:** 이 문서는 formal grammar(구문·정적 제약·의미론을 분리한 명세)가
**아니다.** 구문(스키마)·타입·의미·커널 동작·감사기 해석·예정 기능을 한 절
안에서 같이 다루는 **참고 사전(reference)**이다. 지금 목적 — 사람이 코드
전체를 뒤지지 않고 언어를 이해하는 것 — 에는 이 형식이 formal grammar보다
읽기 편하다. B-Architect가 이 언어로 A를 실제로 자동 생성하기 시작하면,
그때는 역할이 뒤집힐 수 있다 — 지금은 `코드 → 이 사전`(코드가 진실)이지만,
나중에는 `언어 명세 → 파서/검증기/커널`(명세가 코드의 계약)이 되는 편이
더 맞을 수 있다. 지금 당장 그 구조로 바꿀 필요는 없다.
**관련:** `LOCAL_INTERACTION_PRINCIPLES_V1.md`(왜 causal v3가 필요했는가),
`MINIMAL_LOCAL_GEOMETRY_V1.md`(v3를 어떻게 구현하는가, 단계별 진행),
`LANGUAGE_REVISION_GOVERNANCE_V1.md`(앞으로 이런 언어 확장을 어떤 절차로
제안·승인할 것인가 — 이 셋을 하나의 사례로 다룬다).

---

## 0. 이 언어의 성격 — 읽기 전에

이 언어는 세 갈래로 갈라져 있다. **각 갈래가 별도 진화 계통**이고 서로 버전이 다르다.

| 갈래 | 파일 | 다루는 것 | 현재 최신 |
|---|---|---|---|
| **입자 격자 (HPP)** | `spec.py` | 가장 오래된 입자 물리. 결합 없음, 충돌만 | v1 (유일) |
| **인과 (causal)** | `causal_spec.py` | 입자·결합·사슬. **지금 활발히 개발 중** | v3 |
| **환경 (environment)** | `environment_spec.py` | 열·물·광물·용질. causal 세계를 감싼다 | v4 |

**공통 원칙 (세 갈래 전부에 적용):**

1. **정수만.** 부동소수점이 어디에 있든 거부된다(`_scan_constitution`, 재귀적으로 전체를 훑는다).
2. **금지 어휘가 있다.** 아래 1절.
3. **`format` 필드가 버전을 고정한다.** 명세를 파싱하기 전에 먼저 읽고, 그 버전의
   문법으로만 나머지를 검사한다. 다른 버전의 키를 섞으면 거부된다.
4. **모든 dataclass가 `canonical()`을 갖는다.** JSON으로 직렬화 가능한 정규형이고,
   `digest`(SHA-256)가 여기서 나온다. 필드 순서가 아니라 **정렬된 키**로 해시하므로
   같은 내용이면 어떻게 썼든 같은 해시가 나온다.
5. **`_exact()`가 키를 정확히 검사한다.** 없는 키도, 남는 키도 거부한다.
   "선택적 필드를 빼먹었다"가 조용히 통과하는 일이 없다.

### 상태 기호 — 이 문서 전체에서 쓴다

| 기호 | 뜻 |
|---|---|
| ✅ 구현됨 | 파서와 커널이 실제로 지원. 코드에서 직접 확인함 |
| 📜 문법만 | **명세는 파싱되지만 커널이 아직 그 물리를 실행하지 않는다** — 6.1절의 "문법 간극 vs 실행 간극" |
| 🧭 예정 | 파서에도 커널에도 없다. 설계 문서에만 있다. 이름과 링크만 적는다 |
| 🚫 금지 | 문법이 명시적으로 거부하도록 만들어졌다 (헌법 4조 강제) |

**규칙: 예정(🧭) 항목을 구현된 문법인 척 쓰지 않는다.** 표에 넣을 때
반드시 이 넷 중 하나를 붙인다. `LOCAL_INTERACTION_PRINCIPLES_V1.md`의
`InteractionRelation`(hyperedge)이 좋은 예다 — 필요해지기 전에는 🧭로
남기고, 실제 환원 불가능 N체 관계가 나오면 그때 ✅ 절로 승격한다.

---

## 1. 금지 어휘 — 모든 갈래에 공통

`spec.py`에 선언되어 있고 `causal_spec.py`가 그대로 가져다 쓴다.
헌법 제4조(고수준 명령 금지)를 코드로 강제하는 부분이다.

### 금지된 필드 이름 (`FORBIDDEN_KEYS`)

대소문자·하이픈/언더스코어 구분 없이 검사한다 (`normalized = key.strip().lower().replace("-", "_")`).

```
alive, cell_type, fitness, fitness_score, gene, goal,
instinct, intelligence, organism, reproduction_success,
survival_bonus, species
```

어느 깊이에서 나타나든(`_scan_constitution`이 재귀) 거부된다.

### 금지된 명령 문자열 (`FORBIDDEN_COMMANDS`)

명세 안의 **문자열 값**이 이것과 일치하면(대문자로 변환 후) 거부된다.

```
ADD_INSTINCT, COPY_GENE, DIVIDE_CELL, INCREASE_FITNESS,
MAKE_LIFE, PROTECT_ORGANISM
```

**예정:** 주형 복사·독립 분열이 구현되면 `COPY_WITH_MUTATION` 같은 이름도
같은 이유로 금지 후보다 — `LOCAL_INTERACTION_PRINCIPLES_V1.md`의
"변이는 명령이 아니라 자유도의 결과"에 따라. **아직 코드에 없다.**

---

## 2. 공통 원시 어휘

세 갈래 모두 이 타입들을 공유하거나 변형해서 쓴다.

| 용어 | 의미 | 값의 범위 |
|---|---|---|
| `world_id` | 이 세계의 이름 | 비어있지 않은 문자열 |
| `format` | 어느 문법 버전인가 | 갈래마다 고정된 문자열 목록 |
| `tick` | 이산 시간 단위. 하나의 물리 스텝 | 음이 아닌 정수 |
| `direction` | 카디널 방향 | `N`, `E`, `S`, `W` 넷뿐 (`DIRECTIONS`) |
| `kind` | 재료 종류를 가리키는 번호 | 음이 아닌 정수, 세계 안에서 유일 |
| `mass` | 재료의 질량 | 1 이상 정수 |
| `x`, `y` | 격자 좌표 | `0 <= x < width`, `0 <= y < height` |
| `kinetic_energy` | 입자가 가진 운동 에너지 | 음이 아닌 정수 |
| `digest` | 정규형의 SHA-256 | 64자 16진 문자열 |

---

## 3. 갈래 1 — 입자 격자 (HPP), `spec.py`

**가장 단순한 세계.** 결합이 없다. 입자가 충돌하면 정해진 규칙대로 방향만 바뀐다.
`worlds/deterministic_collision_smoke_v1.json`이 이 문법으로 쓰여 있다.

`format`: `"deterministic-world-spec-v1"` (유일한 버전)

### 3.1 최상위 구조

```
world = {
    format: "deterministic-world-spec-v1"
    world_id: str
    kernel: KernelSpec
    materials: [MaterialSpec, ...]      비어있지 않음
    initial_particles: [ParticleSpec, ...]
    execution: ExecutionSpec
    observer: ObserverSpec
}
```

### 3.2 `KernelSpec`

```
kernel = {
    kind: "hpp-lattice-v1"              고정값. 다른 값은 거부
    deterministic: true                  고정값
    arithmetic: "integer"                고정값
    dimensions: 2                        고정값
    width: int (>= 4)
    height: int (>= 4)
    boundary: "wrap"                     고정값 — 격자가 원환면(toroidal)
    collision: "head-on-right-angle-v1"  고정값 — 정면 충돌 시 직각으로 흩어짐
}
```

**왜 전부 고정값인가:** 이 세계는 문법이 하나뿐이다. 다른 값을 받아주면
"세계가 다양하다"가 아니라 "검증 안 된 새 물리를 몰래 들여온다"가 된다.

### 3.3 `MaterialSpec`

```
material = { kind: int, mass: int (>= 1) }
```

세계 안에서 `kind`는 유일해야 한다.

### 3.4 `ParticleSpec`

```
particle = { kind: int, x: int, y: int, direction: N|E|S|W }
```

**채널 유일성:** 같은 `(kind, x, y, direction)`을 가진 입자가 둘이면 거부된다.
같은 칸을 같은 방향으로 지나가는 같은 재료 두 개는 구별할 수 없기 때문이다.

### 3.5 `ExecutionSpec`, `ObserverSpec`

```
execution = { ticks: int (>= 0) }
observer  = { hash_interval: int (>= 1) }    -- 몇 tick마다 체크포인트를 남기는가
```

### 3.6 물리 — `collide()`

한 칸에 같은 재료가 정확히 두 방향으로 있으면(`OPPOSITE_COLLISION`에 있는 쌍),
직각으로 튕긴다. 그 외에는 통과한다. **이 갈래에는 결합이라는 개념이 없다.**

---

## 4. 갈래 2 — 인과 (causal), `causal_spec.py`

**입자·결합·사슬을 다루는, 지금 개발 중인 핵심 갈래.** v1 → v2 → v3로 진화했고
각 버전이 실제로 다른 물리를 허용한다 — 이름만 바뀐 게 아니다.

### 4.1 버전 한눈에 비교

| | v1 | v2 | v3 |
|---|---|---|---|
| `format` | `...-causal-world-spec-v1` | `...-v2` | `...-v3` |
| 포트 | ✅ 개수만 (`ports: 4`) | ✅ 개수만 | ✅ **이름** (`ports: ["N","E","S","W"]`) |
| 결합 위치 (명세) | ✅ 같은 칸 | ✅ 같은 칸 | ✅ **이웃 칸** 선언 가능 (`locality: adjacent_cells`) |
| 결합 위치 (커널 실행) | ✅ 같은 칸 강제 (`PhysicalBond`) | ✅ 같은 칸 강제 (`PhysicalBond`) | ✅ **인접 강제 (`PortBond`, 2026-09-22 구현)** — 별도 필드 `port_bonds`. `PhysicalBond`는 무손상 |
| 규칙 필드 | `left_orientation`/`right_orientation` | 동일 | `left_port`/`right_port` |
| 최대 결합 수 | 1 (선언과 무관) | 재료가 선언한 `ports`(개수)만큼 | 재료가 선언한 `ports`(이름 목록) 길이만큼 |
| 사슬 이동 | 불가 (`chains_may_move=False`) | ✅ 가능 | 📜 명세는 표현 가능, 커널 미구현 |

**용어 주의 — JSON 필드명과 파싱 후 필드명이 다르다:**

```
JSON 명세 필드 (쓸 때):        "ports": ["N","E","S","W"]
파싱된 CausalMaterialSpec (읽을 때):
    .ports        -> 4                      (개수. v1/v2/v3 전부 존재)
    .port_names   -> ("N","E","S","W")      (이름 목록. v3만 채워짐, v1/v2는 빈 튜플)
```

즉 JSON을 쓸 때는 항상 `ports` 키 하나만 쓴다(개수 또는 이름 목록).
파싱된 객체를 코드에서 다룰 때는 `.ports`(개수, 항상 존재)와
`.port_names`(이름, v3에서만 비어있지 않음)가 별도 필드로 나뉜다.

### 4.2 최상위 구조 (공통 골격)

```
world = {
    format: v1|v2|v3
    world_id: str
    kernel: CausalKernelSpec
    materials: [CausalMaterialSpec, ...]
    particles: [CausalParticleSpec, ...]
    heat: [HeatCellSpec, ...]
    bond_rules: [BondRuleSpec, ...]
    execution: { ticks: int }
    observer: { hash_interval: int (>= 1) }
}
```

### 4.3 `CausalKernelSpec`

```
kernel = {
    width: int (>= 4)
    height: int (>= 4)
    boundary: "wrap"                      고정값
    arithmetic: "integer"                 고정값
    deterministic: true                   고정값
    tick_order: [
        "break_existing_bonds",
        "stream_free_particles",
        "resolve_local_collisions"
    ]                                      고정 순서. 다른 순서 거부
}
```

`tick_order`가 **선언**이다. 검사기(`audit/independent_compliance/particles.py`)가
이걸 읽어서 "결합이 먼저 풀리고 그 다음 스트리밍이 일어난다"를 판정한다.
`docs/current/VERIFICATION_LIMITS_AND_LESSONS.md` 유형 D가
이걸 안 읽고 추론해서 틀렸던 사례를 기록해뒀다.

### 4.4 `CausalMaterialSpec`

**v1/v2:**
```
material = { kind: int, mass: int (>= 1), ports: int (>= 1) }
```
`ports`는 **개수**일 뿐이다 — 몇 개까지 결합할 수 있는지. **어느 방향의 포트인지는
말하지 않는다.** 이게 `LOCAL_INTERACTION_PRINCIPLES_V1.md`가 찾아낸 근본 원인이다:
포트 4개가 전부 구별 불가능해서, 여러 포트가 같은 도착을 받을 수 있을 때
고를 물리적 근거가 없었다.

**v3:**
```
material = { kind: int, mass: int (>= 1), ports: [direction, ...] }
```
`ports`가 이제 **목록**이다. 각 원소는 `N`/`E`/`S`/`W` 중 하나, 중복 불가, 비어있으면 안 됨.

```
예: ports: ["E", "W"]     -- 동서로만 결합. 직선 사슬만 가능, 가지 불가
    ports: ["N","E","S","W"]  -- 네 방향 전부. 십자 가지 가능
```

**이것이 "기하가 구조를 제한한다"의 첫 사례다.** 몇 개가 아니라 어느 방향인지가
사슬의 모양을 결정한다.

**결정적으로 명시해야 할 것 — 포트 방향의 기준계 (설계자 확인, 2026-09-22):**

> **v3의 포트 방향(`N`/`E`/`S`/`W`)은 세계 좌표계의 절대 방향이다.
> 입자의 `orientation`에 따라 회전하지 않는다. 구조·포트의 회전은
> v3에서 지원하지 않는다.**

이걸 못 박아야 하는 이유는 바로 위 4.5절이 `orientation`을 "v3부터는 입자
고유의 방향만 뜻한다"고 정의했기 때문이다. 그 정의만 읽으면 자연스럽게
**"입자가 orientation E에서 N으로 돌면 포트도 같이 도는가?"** 라는 질문이
생긴다. 답은 **아니오**다 — 포트는 재료가 선언한 절대 방향에 고정되고,
`orientation`이 바뀌어도 포트의 방향은 바뀌지 않는다.

`MINIMAL_LOCAL_GEOMETRY_V1.md` Q2가 이걸 명시적으로 확정했다: 회전이
실제로 필요해지면 그때 포트를 추상 이름(`a,b,c,d`)과 방향 매핑으로 분리한다.
**지금은 회전 불가가 선언된 한계다 — 코드 구조 때문에 우연히 못 하는
숨은 천장이 아니다.** 이 구분이 `RULES.md` 원칙("한계는 물질·기하·에너지·
보존 법칙에서만 나와야 하고, 자료형이나 구현 순서에서 우연히 떨어져 나온
것이면 숨은 법칙")과 맞다.

### 4.5 `CausalParticleSpec`

```
particle = {
    particle_id: int (>= 1)     -- 세계 안에서 유일
    kind: int                    -- 선언된 재료 중 하나
    x, y: int                    -- 격자 안
    direction: N|E|S|W           -- 입자가 움직이는 방향
    orientation: N|E|S|W         -- v1/v2: 결합 면도 겸함. v3: 입자 자체의 방향만
    kinetic_energy: int (>= 0)
}
```

**`direction` vs `orientation`의 차이:**
- `direction`은 이 입자가 다음 tick에 어느 쪽으로 스트리밍하는가
- `orientation`은 v1/v2에서 "어느 면으로 결합하는가"까지 겸했다.
  v3부터는 `orientation`이 입자 고유의 방향만 뜻하고, 결합 면은 규칙의
  `left_port`/`right_port`가 따로 말한다 (4.7절)

**채널 유일성:** 결합되지 않은 자유 입자 중 같은 `(kind, x, y, direction)`을
가진 게 둘이면 거부. 이건 세 버전 모두 같다 — 자유 입자에 대한 규칙이기 때문이다.

**결합된 입자의 위치 — 버전마다 다르다. 여기서 절대 뭉뚱그리면 안 된다.**

```
v1/v2 (명세로 선언됨, 커널이 실행함):
    locality: "same_cell"
    결합된 두 입자는 반드시 같은 (x, y)를 공유한다.
    채널 유일성 예외의 근거가 여기서 나온다 — "같은 칸에 모여 있는 것
    자체가 결합의 정의"이므로, 결합된 입자는 자유 채널 검사에서 빠진다.

v3 (명세로 선언됨, 그러나 커널이 아직 실행하지 않음 — 2026-09-22 기준):
    locality: "adjacent_cells"
    결합된 두 입자는 이웃한 서로 다른 (x, y)에 있어야 하고,
    각자의 결합 포트가 상대 칸을 향해야 한다.
    "같은 칸 점유"는 v3 결합의 근거가 아니다 — 오히려 반대다:
    포트가 마주 보는 두 이웃 칸이 결합의 정의다.
```

**✅ 단계 2 완료 (2026-09-22).** `CausalWorldState`에 v3 전용 `PortBond`와
`port_bonds` 필드가 추가됐다. `bonded particles must share the bond location`
불변조건은 **`PhysicalBond`(v1/v2)에만 그대로 적용된다** — 손대지 않았다.
`PortBond`는 별도 검증 경로를 갖는다.

**타입을 나눈 이유:** 하나의 dataclass에 `x,y`(v1/v2 의미: 위치)와
`left_port`/`right_port`(v3 의미: 관계)를 optional로 같이 두면, 어느
조합이 합법인지 검증기가 계속 떠안아야 한다("x도 있고 port도 있음",
"v2인데 port 있음" 같은 쓰레기 상태 공간). 두 타입으로 나누면 그런
조합 자체가 표현 불가능해진다.

**`PortBond`의 검증 규칙 (전부 상태만 보고 판정, `x,y` 없음):**

```
left_id, right_id       -- 서로 달라야 함 (자기 결합 금지)
left_port, right_port   -- 각 입자가 실제로 선언한 포트여야 함
                            서로 마주 봐야 함 (OPPOSITE_PORT)
인접성                    -- neighbour() 로 판정. 스트리밍(_stream_free)이
                            입자를 옮길 때 쓰는 것과 완전히 같은 공식
                            (VELOCITY[direction] + wrap). 새 인접 규칙을
                            발명하지 않는다 -- 안 그러면 "이동은 wrap되는데
                            결합은 세계 끝에서 끊기는" 세계가 생긴다
포트 점유                 -- 한 입자의 한 포트를 두 결합이 동시에 못 씀
좌우 순서                 -- 물리적 의미 없음. canonical()이 항상 낮은 id를
                            left로 정규화 -- (A,B) 순서로 지어도
                            (B,A) 순서로 지어도 같은 해시가 나온다
```

**아직 안 하는 것 (단계 3+):** 이 결합들로 이루어진 구조가 실제로 움직이는
것. 지금은 "이 결합 하나가 공간적으로 유효한가"만 판정한다.

**결함 주입 5종 (전부 검출됨):**

| 주입 | 결과 |
|---|---|
| 인접성 검사 제거 | 검출 |
| 마주보는 포트 검사 제거 | 검출 |
| 포트 중복 점유 검사 제거 | 검출 |
| 선언 안 된 포트 허용 | 검출 |
| 대각선도 인접으로 인정 | 검출 |

`v1/v2` `PhysicalBond`는 한 글자도 안 바뀌었고, `deterministic_polymer_chain_v2`의
run digest가 byte 단위로 그대로임을 테스트로 고정했다.

### 4.6 `HeatCellSpec`

```
heat = { x: int, y: int, energy: int (>= 0) }
```
위치는 세계 안에서 유일해야 한다. 에너지 0인 칸은 목록에 넣을 필요 없다
(커널이 렌더링할 때 0인 칸은 생략한다 — `_heat_cells`).

### 4.7 `BondRuleSpec`

**v1/v2:**
```
rule = {
    rule_id: str                              세계 안에서 유일
    event: "local_reversible_bond"            고정값
    locality: "same_cell"                     고정값
    conserves: ["material","energy","momentum"]  고정값
    left_kind, right_kind: int
    left_orientation, right_orientation: N|E|S|W
    minimum_collision_energy: int (>= 0)
    break_heat: int (>= 0, 짝수여야 함)         -- 결합을 끊는 데 필요한 열
    release_left, release_right: N|E|S|W       -- 끊어질 때 방출되는 방향
}
```

**v3 (같은 필드, 이름과 의미가 바뀐 것만):**
```
rule = {
    ...
    locality: "adjacent_cells"                고정값
    left_port, right_port: N|E|S|W            -- orientation 대신
    ...
}
```

**제약 (모든 버전):**
- `release_left`/`release_right`는 반드시 서로 반대 방향이어야 한다
  (`{N,S}` 또는 `{E,W}`) — 운동량을 정반대로 나눠 보존하기 위해
- 결합하는 두 재료는 **질량이 같아야** 한다 (`causal v1 bond rules require equal masses`) —
  방출 시 정확히 반씩 나누기 위해
- `break_heat`는 짝수여야 한다 — 정수로 반씩 방출하기 위해
- 같은 물리적 서명(`left_kind, right_kind, left_orientation/port, right_orientation/port`)을
  가진 규칙 두 개는 거부된다

**v3 전용 추가 제약:**
- `left_port`/`right_port`는 **해당 재료가 실제로 선언한 포트**여야 한다
  (`material 0 does not declare`)
- 두 포트는 **서로 마주 봐야** 한다 — `OPPOSITE_PORT[left_port] == right_port`.
  `E`는 반드시 `W`를 만나야 하고, `E`와 `N`을 잇는 규칙은 거부된다

### 4.8 물리 어휘 (커널이 만들어내는 것, 명세에는 없음)

명세 언어는 아니지만, 명세를 읽고 커널이 만드는 상태의 어휘도 여기 적어둔다 —
B가 A를 "읽을" 때 만나는 것들이기 때문이다.

| 용어 | 뜻 |
|---|---|
| `PhysicalBond` | ✅ v1/v2 결합 하나. `(left_id, right_id, rule_id, stored_energy, x, y)`. v3 도입 이후에도 **손대지 않음** |
| `PortBond` | ✅ **v3 결합 하나 (2026-09-22 구현).** `(left_id, left_port, right_id, right_port, rule_id, stored_energy)` — `x,y` 없음, 위치는 참가 입자에서 유도. `canonical()`이 항상 낮은 id를 `left`로 정규화하므로 끝점을 뒤집어 지어도 같은 해시가 나온다 |
| `port_bonds` | ✅ `CausalWorldState`의 별도 필드. v3 세계가 채우고 `bonds`는 비워둔다. **합법성 판정(단계 2)과 tick 통과(2026-09-22) 완료.** 아래 상태 표 참조 — 커널은 `port_bonds`를 **보존**하지만 아직 **변경**하지 않는다 |
| `neighbour()` | ✅ `(x,y,direction) → 이웃 칸`. `_stream_free`가 입자를 옮길 때 쓰는 것과 **완전히 같은 공식**을 `PortBond` 인접 판정에도 그대로 재사용. 새 인접 규칙을 따로 만들지 않음 |
| `chain` (사슬) | 결합으로 이어진 입자들의 연결 성분. `chains()` 함수가 union-find로 계산. **`port_bonds`는 아직 `chains()`가 못 읽는다** — union-find는 `bonds`(v1/v2)만 본다 |
| `stored_energy` | 결합이 흡수해 저장한 운동 에너지. 끊어질 때 `break_heat`와 함께 방출. v3에서는 `total_energy()`가 `port_bonds`의 몫도 합산 |
| `port_limits` | 이 세계에서 재료별로 몇 개까지 결합 가능한지 — 단, `PhysicalBond`(v1/v2)에만 적용된다. **실측(2026-09-22): v1은 전부 1, v2는 선언값, v3도 1** — `port_limits()`가 `spec.format != FORMAT_V2`로 판정하므로 v3는 v2가 아니라 v1과 같은 갈래를 탄다. `PortBond`의 포트 점유는 이 숫자를 전혀 안 쓰고 **포트 단위**(`(particle_id, port_name)`)로 개별 검사한다 — 숫자형 한도와 이름 있는 포트 점유는 **서로 다른 메커니즘**이다 |
| `chains_may_move` | 사슬이 운동을 가질 수 있는가 — 단, `PhysicalBond`(v1/v2)에만 적용된다. **실측(2026-09-22): v1은 불가, v2는 가능, v3도 불가** — `initial_causal_state()`가 `spec.format == FORMAT_V2`로만 켠다. v3에서 `False`인 것은 결함이 아니라 **현재 단계에 맞는 값**이다: `chains()`가 아직 `port_bonds`를 안 읽고, 런타임에 `PortBond`를 만드는 경로도 없고, 구조 이동도 미구현이므로 지금 `True`로 켜면 아직 설계하지 않은 이동 의미를 선구현하는 꼴이 된다. `StructureState`/구조 이동을 구현한 뒤 다시 정의한다 |

### v3 `PortBond`의 정확한 현재 상태 (2026-09-22)

"v3가 되었다"와 "v3가 동작한다"는 다르므로 항목별로 적는다.

| 항목 | 상태 |
|---|---|
| 합법성 판정 (인접·포트 마주봄·중복) | ✅ 단계 2 |
| tick 통과 (상태가 살아남음) | ✅ 2026-09-22 |
| `chains()` 통합 | ❌ union-find가 `bonds`만 본다 |
| 런타임 결합 생성·갱신 | ❌ `_resolve_collisions`가 `PhysicalBond`만 만든다 |
| 구조 이동 | ❌ 단계 4 |

**"tick 통과"가 따로 있는 이유:** 2026-09-22까지 커널의 각 단계가
`CausalWorldState`를 위치 인수로 재구성하고 있었다. `chains_may_move` 뒤에
추가된 `grid_size`·`named_ports`·`port_bonds`는 전달되지 않아 **매 tick
증발했다.** 즉 v3 구조는 움직이기는커녕 존재를 유지하지 못했다. 네 곳을
`dataclasses.replace`로 바꿔 해결했고, 같은 문제가 environment(4곳)·GPU(2곳)·
counterfactual(1곳)에도 있었다 — 그쪽은 `port_limits`와 `chains_may_move`까지
잃고 있었으므로 **v2 사슬도 환경 세계 안에서는 작동하지 않았다.**

지속성 게이트: `tests/test_deterministic_v3_state_persistence.py`

**🧭 예정 (파서에도 커널에도 없음 — 설계 문서에만 있다):**

| 기호 | 용어 | 왜 필요한가 | 어느 문서에 설계됐나 |
|---|---|---|---|
| 🧭 | `StructureState` | 사슬의 운동량을 최저 번호 멤버가 아니라 구조 자체가 가짐 | `LOCAL_INTERACTION_PRINCIPLES_V1.md` §운동량, `MINIMAL_LOCAL_GEOMETRY_V1.md` 4.4 |
| 🧭 | Contact Graph | 실제 접촉 가능한 쌍을 기하에서 유도 | `MINIMAL_LOCAL_GEOMETRY_V1.md` §5 |
| 🧭 | `InteractionRelation` (hyperedge) | 환원 불가능한 N체 결합 (`Bond(A,B,C)` 자체가 하나의 관계) | `LOCAL_INTERACTION_PRINCIPLES_V1.md` §②, §목표 구조 8단계 |
| 🧭 | 촉매 중간체 | `C+A → C-A → C-A-B → C+AB` | `DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md` 8.4, `LOCAL_INTERACTION_PRINCIPLES_V1.md` §촉매 정정 |
| 🧭 | 주형 복사 | 사슬 옆에 상보적 사슬이 자람 | 위 문서들, "옆"이 아직 없어서 막혀 있었음 |
| 🧭 | 경계 물질 / 독립 분열 | 안팎을 나누는 막, 끊고 다시 닫힘 | `CURRENT_STATE.md` "다음 갈림길 (나)" |

**구현되면 이 표에서 빼고 §4의 본문 절로 승격하며 🧭를 ✅로 바꾼다.**

---

## 5. 갈래 3 — 환경 (environment), `environment_spec.py`

**causal 세계를 감싸서** 열·물·광물·용질·수증기를 추가한다.
`causal_world` 필드로 인과 세계 하나를 통째로 품는다.

### 5.1 버전 한눈에 비교

| | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| `format` | `...-v1` | `...-v2` | `...-v3` | `...-v4` |
| 열·물·용질 이동 | O | O | O | O |
| 광물 용해·침전 | — | O | O | O |
| 물 상변화(증발·응축) | — | — | O | O |
| 에너지 경계 | — | — | O | O |
| 물리 단위 계약 | — | — | — | O |

### 5.2 최상위 구조

```
environment_world = {
    format: v1|v2|v3|v4
    causal_world: CausalWorldSpec       -- 인과 세계 전체를 내장
    solute_kinds: int (>= 1)             -- 용질 종류 수
    cells: [EnvironmentCellSpec, ...]
    blocked_edges: [BlockedEdgeSpec, ...]
    law: EnvironmentLawSpec
    energy_boundaries: [EnergyBoundarySpec, ...]   v3/v4만
    physical_scale: PhysicalWorldScale             v4만, 필수
}
```

**제약:** 내장된 `causal_world`의 격자는 **가로세로 모두 짝수**여야 한다
(`environment v1 needs even grid dimensions for disjoint edge phases`) —
네 위상(짝/홀 × 가로/세로)이 겹치지 않고 나뉘게 하기 위해.

### 5.3 `EnvironmentCellSpec`

```
cell = {
    x, y: int
    elevation: int      -- 지형 고도. 절대 안 바뀜 (RULES.md 위반 코드 참조)
    water: int
    mineral: int
    solutes: [int, ...]  -- solute_kinds 개, 종류별 양
    vapor: int = 0        -- v3/v4만 canonical에 나타남
}
```

위치는 세계 안에서 유일해야 한다.

### 5.4 `BlockedEdgeSpec`

```
edge = { first: [x,y], second: [x,y] }
```

두 점은 **감긴 격자에서 카디널 이웃**이어야 한다 (`dx+dy == 1`, wrap 거리 기준).
정렬은 정규화된다 — `first`가 항상 `second`보다 작거나 같다.
막힌 벽으로 물질·열이 넘어가면 `audit/independent_compliance/field.py`의
`blocked_edge_crossed`가 잡는다.

### 5.5 `EnergyBoundarySpec` (v3/v4)

```
boundary = { x, y: int, input_per_tick: int, output_per_tick: int }
```

**한 경계가 같은 tick에 공급과 회수를 동시에 할 수 없다** —
`input_per_tick`과 `output_per_tick` 중 하나는 반드시 0.
이게 헌법 "외부 에너지는 장부에 기록한다"를 강제하는 지점이다.

### 5.6 `EnvironmentLawSpec` — 버전별로 늘어나는 필드

**v1 (기본):**
```
law = {
    max_heat_transfer, max_water_transfer, max_solute_transfer: int
    phase_order: ["horizontal_even","horizontal_odd","vertical_even","vertical_odd"]  고정 순서
}
```

**v2 추가 (광물):**
```
    max_carried_solute_per_water: int   -- 물 한 단위가 옮길 수 있는 용질 최대량
    mineral_solute_kind: int             -- 어느 용질 채널이 "광물이 녹은 것"인가
    dissolve_heat_at_least: int          -- 이 이상 뜨거워야 용해
    precipitate_heat_at_most: int        -- 이 이하로 식어야 침전
    hot_solubility_per_water: int        -- 뜨거울 때 물 단위당 용해 한도
    cold_solubility_per_water: int       -- 차가울 때 (>= 0, hot 이하)
    max_mineral_conversion: int          -- 한 tick당 변환 한도
    mineral_conversion_energy: int       -- 변환 시 열 교환량
```
제약: `dissolve_heat_at_least > precipitate_heat_at_most` (역전되면 무의미),
`hot_solubility_per_water >= cold_solubility_per_water`,
변환을 허용하면(`max_mineral_conversion > 0`) 에너지도 양수여야 함.

**v3 추가 (수증기):**
```
    max_vapor_transfer: int
    evaporation_heat_at_least: int
    condensation_heat_at_most: int
    max_water_phase_change: int
    vaporization_energy: int
```
같은 형태의 제약: 증발 문턱 > 응축 문턱, 상변화 허용 시 잠열도 양수.

**`phase_order`가 왜 고정인가:** 네 위상이 서로 겹치지 않는 짝을 짓게 하는
분할이다. `independent_compliance`가 이 순서를 읽어서 "이 위상이 이 짝을
건드릴 자격이 있는가"를 판정한다.

### 5.7 `PhysicalWorldScale` (v4 전용)

물리 단위를 실제 단위(피코미터, 펨토초, 욕토몰, 젭토줄)에 고정한다.

```
physical_scale = {
    cell_length_pm: int        -- 한 칸의 실제 길이 (피코미터)
    tick_duration_fs: int      -- 한 tick의 실제 시간 (펨토초)
    units: {
        cell_length_unit: "picometer"       고정값
        tick_duration_unit: "femtosecond"   고정값
        height_quantum_pm: int
        matter_quantum_unit: "yoctomole"    고정값
        matter_quantum_yoctomol: int
        energy_quantum_unit: "zeptojoule"   고정값
        energy_quantum_zj: int
    }
    flux_laws: [
        { channel: str, diffusivity: { numerator_pm2: int, denominator_fs: int } }
    ]
}
```

**단위 이름은 전부 고정 문자열이다.** 다른 단위계를 붙이려는 시도는 거부된다 —
"단위가 있다"가 아니라 "이 다섯 단위 중 하나로 고정돼 있다"가 계약이다.

---

## 6. 세 갈래가 서로 참조하는 방식

```
spec.py (HPP)          <- 독립. 아무것도 참조하지 않음
causal_spec.py          <- spec.py 에서 DIRECTIONS, FORBIDDEN_* 를 가져옴
environment_spec.py     <- causal_spec.py 의 CausalWorldSpec 을 통째로 내장
                           physical_scale.py 의 단위 계약을 가져옴 (v4)
```

**중요:** `environment_spec.py`는 `causal_spec.py`가 v1이든 v2든 v3든
받아들인다 — `CausalWorldSpec.from_mapping`이 포맷을 스스로 판별하기 때문이다.
즉 **환경 세계 안에 v3 인과 세계를 넣는 것이 이미 문법적으로 가능하다**
(직접 파싱해서 확인함, 2026-09-22). 다만 커널(`CausalWorldState`)이 v3의
`adjacent_cells` 물리를 아직 실행하지 않는다 — 4.5절 참조.

### 6.1 문법 간극(syntax gap)과 실행 간극(runtime gap)은 다른 것이다

이 사전이 다루는 것은 대부분 **문법 간극**이다 — 명세가 파서를 통과하는가.
그런데 v3의 경우처럼 **파서는 통과하는데 커널이 그 물리를 실행하지 못하는**
경우가 있다. 이 둘을 구분해서 부르는 게 중요하다.

```
문법(syntax) 관점:   environment v1(v3 causal_world 포함) -> 파싱 성공
실행(runtime) 관점:  같은 명세 -> 커널 실행 시 v3 물리 미지원
```

**이 구분이 왜 유용한가:** B가 `environment v4 └ causal v3` 같은 명세를
만들었을 때, "이 명세는 문법적으로 유효하지만 지금 이 엔진 버전은 실행할
능력이 없다"고 **정확히** 답할 수 있어야 한다. 이걸

```
syntax_valid = true
runtime_capability = unsupported
```

처럼 나눠 표현하면, `b_language.py`의 `CapabilityManifest`(B가 자신의
관측·실행 능력 범위를 선언하는 것)와 자연스럽게 연결될 자리가 생긴다.
**지금은 이 연결이 구현돼 있지 않다** — 이 사전이 그 필요성을 기록해두는
수준이다.

---

## 7. 실제로 존재하는 세계 파일과 그 문법

| 파일 | 갈래 | 버전 |
|---|---|---|
| `deterministic_collision_smoke_v1.json` | HPP | v1 |
| `deterministic_bond_cycle_v1.json` | causal | v1 |
| `deterministic_polymer_chain_v2.json` | causal | v2 |
| `deterministic_environment_v1.json` | environment | v1 |
| `deterministic_geochemical_cycle_v2.json` | environment | v2 |
| `deterministic_open_water_cycle_v3.json` | environment | v3 |
| `deterministic_physical_flux_v4.json` | environment | v4 |

**v3 causal 세계 파일은 아직 없다.** 명세 파서는 완성됐지만(2026-09-22),
커널이 아직 실행하지 못하고 예시 세계도 없다.

---

## 8. 이 사전을 최신으로 유지하는 법

- 새 `format` 상수가 추가되면 이 문서의 해당 갈래 절에 버전 행을 추가한다
- 새 필드가 추가되면 "제약" 항목까지 함께 적는다 — 필드 이름만으로는
  왜 그 값이어야 하는지 알 수 없다 (예: `break_heat`가 짝수인 이유)
- 🧭 "예정" 표로 적힌 항목이 구현되면, 표에서 빼고 본문 절로 승격하며 기호를 ✅로 바꾼다
- 📜 "문법만" 항목(명세는 되는데 커널이 안 도는 것)이 커널까지 구현되면,
  기호를 ✅로 바꾸고 "커널이 아직 실행하지 않음" 문구를 지운 뒤 검증 방법을 채운다
  (4.5절이 지금 이 상태의 예시다)
- 새 버전 비교표를 만들 때는 §0의 상태 기호(✅/📜/🧭/🚫) 중 하나를 반드시 붙인다.
  기호 없이 "됨"이라고만 쓰면 문법 지원과 커널 실행이 섞여서 다시 헷갈리게 된다
- 이 문서와 코드가 어긋나면 **코드가 옳다** (`AGENTS.md` 원칙) — 이 문서를 고친다
