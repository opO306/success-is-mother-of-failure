# MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22

**문서 분류: 역사 / 과거 설계·실측 기록.** 본문의 “현재”, “다음”, 시험 개수와 후보는 기록 당시의 상태다. 현재 작업 지시나 새 동결 판정으로 읽지 않는다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


**상태:** 중간 결과 정리  
**날짜:** 2026-09-22  
**범위:** deterministic causal world / World Spec Language / causal v3 / local geometry / validation  
**테스트 상태:** 990 passing  
**목적:** 지금까지 무엇을 만들었고, 왜 구조를 바꿨으며, 현재 어디까지 구현되었는지 쉽게 설명한다.

---

# 1. 한 문장 요약

현재까지 만든 것은 **생명 자체가 아니라, 생명·고분자·촉매·주형 복사·변이 같은 복잡한 현상이 나중에 발생했을 때 그것이 하드코딩이나 particle ID 때문이 아니라 실제 물질·공간·에너지·상호작용 때문에 생겼다고 검증할 수 있는 결정론적 세계 언어와 물리 기반**이다.

---

# 2. 처음에는 무엇이 문제였는가

기존 causal v2는 다음을 할 수 있었다.

- 여러 입자가 결합
- 사슬 형성
- 다중 결합
- 사슬 이동
- 에너지와 운동량 계산

겉으로 보면 "사슬이 성장한다"는 목표가 어느 정도 달성된 것처럼 보였다.

하지만 실제로 조사해보니 여러 숨은 제한이 있었다.

대표적인 문제:

```text
사슬 성장
→ 특정 길이에서 멈춤

3개 이상이 같은 칸에 모임
→ 충돌 처리를 건너뜀

여러 결합 후보가 존재
→ particle ID가 작은 쪽을 선택

구조의 운동
→ 가장 낮은 particle ID가 대표
```

즉 코드에서 단순히 붙인 이름표나 실행 순서가 실제 물리 결과를 결정하고 있었다.

---

# 3. 가장 중요한 결함: ID가 물리를 결정했다

다음과 같이 물리적으로 동일한 상태를 만들고 입자 번호만 바꿨다.

```text
상태 A:
member 1
member 2
arrival 3

상태 B:
member 2
member 1
arrival 3
```

물리 상태는 동일하지만 결합 상대가 달라졌다.

항상 더 낮은 ID가 선택됐다.

즉:

```text
물리 상태 동일
+
particle ID만 변경
↓
결과 변경
```

이 발생했다.

이것은 particle ID가 단순한 이름표가 아니라 **숨은 물리 변수처럼 작동했다는 직접 증거**다.

---

# 4. 단순 패치 대신 일반 원칙을 만들었다

문제를 발견한 뒤 다음과 같은 식으로 고치지 않았다.

```text
if particle_count == 3:
    special_case()
```

이렇게 하면 나중에 4개, 5개, 8개에서 같은 문제가 반복될 수 있다.

대신 국소 상호작용 전체에 적용할 원칙을 만들었다.

## 4.1 Cardinality neutrality

> 참가자 수 자체가 물리 법칙을 고르는 스위치가 되어서는 안 된다.

```text
2개니까 규칙 A
3개니까 규칙 B
```

가 아니라:

```text
현재 위치
기하
포트
에너지
운동량
물성
기존 결합
↓
가능한 상호작용 결정
```

이어야 한다.

---

## 4.2 No forced pairwise decomposition

> 여러 물질이 동시에 상호작용할 수 있을 때 구현 편의를 위해 억지로 2체 사건으로 순서화하지 않는다.

예:

```text
A → B ← C
```

에서 A-B와 B-C가 서로 다른 포트를 사용하고 동시에 가능한 경우:

```text
A — B — C
```

를 하나의 국소 상태 전이에서 동시에 만들 수 있어야 한다.

---

## 4.3 No arbitrary collision ordering

> 현재 물리 상태로 결과를 하나로 결정할 수 없다면 ID·배열 순서·thread 순서로 결정하지 않는다.

이 경우:

```text
결정 불가능
→ 부족한 물리 정보가 무엇인지 조사
```

한다.

---

## 4.4 No artificial structural ceiling

> 사슬 길이, 구조 크기, 참가자 수 등에 임의 상한을 두지 않는다.

허용되는 제한:

- 필요한 물질이 없음
- 포트가 이미 차 있음
- 공간이 부족함
- 기하 조건 불일치
- 에너지 부족
- 운동량/보존 법칙 위반
- 실제 충돌이나 절단

금지되는 제한:

```text
길이 3 이상 금지
움직이는 사슬 성장 금지
3개 이상이면 처리 건너뜀
```

---

# 5. 변이도 별도 명령으로 만들지 않는다

변이는:

```text
MUTATE()
```

같은 특별 사건으로 만들지 않는다.

대신:

```text
결합
절단
충돌
다른 물질의 도착
에너지 변화
기하 변화
포트 경쟁
```

같은 정상적인 물리 과정 때문에 다른 구조가 생기도록 한다.

예:

```text
예상:
A-B-C

실제:
A-B-X
```

또는:

```text
A-B-C
↓ 충격
A-B + C
```

이런 차이를 나중에 관찰자가 **변이**라고 부른다.

핵심:

> **변이를 구현하는 것이 아니라, 변이가 발생할 수밖에 없는 자유도를 구현한다.**

---

# 6. ID 문제가 왜 생겼는지 근본 원인을 찾았다

기존 물질 명세에는 다음이 있었다.

```text
ports: 4
```

하지만 이 포트들은 서로 구별되지 않았다.

즉:

```text
포트 1
포트 2
포트 3
포트 4
```

가 물리적으로 어떤 방향인지 알 수 없었다.

그래서 커널은:

> 여러 결합 후보 중 누구를 선택해야 하지?

라는 문제를 만나고 결국 ID 순서에 의존했다.

---

# 7. causal v3: 이름 있는 포트 도입

기존:

```json
{
  "ports": 4
}
```

v3:

```json
{
  "ports": ["N", "E", "S", "W"]
}
```

이제 결합 슬롯 자체에 방향이 생겼다.

포트는 세계 좌표계 기준 절대 방향이다.

```text
N = 북쪽
E = 동쪽
S = 남쪽
W = 서쪽
```

현재 v3에서는 포트 회전을 지원하지 않는다.

이것은 숨은 제한이 아니라 **명시된 현재 버전의 한계**다.

---

# 8. same-cell 결합에서 adjacent-cell 결합으로

기존 구조:

```text
(10,10)

A
B
C
```

여러 구조 멤버가 같은 칸에 겹쳐 있었다.

v3 방향:

```text
(10,10)   (11,10)   (12,10)

   A   ─     B    ─     C
       E-W        E-W
```

즉 각 구조 멤버가 자기 위치를 가지며, 실제 이웃 칸에 있는 포트끼리 결합한다.

---

# 9. 이것으로 처음 생긴 개념

이제 세계가 다음을 구별할 수 있다.

- 누가 누구 옆에 있는가
- 어느 방향으로 연결됐는가
- 어느 포트가 사용 중인가
- 직선 구조인가
- 꺾인 구조인가
- 가지를 만들 수 있는가
- 특정 재료가 어떤 방향으로만 성장 가능한가

예:

```json
{
  "ports": ["E", "W"]
}
```

인 물질은:

```text
A — B — C
```

같은 직선 구조는 만들 수 있지만 북쪽/남쪽 가지는 만들 수 없다.

이 제한은 ID나 임의 상한이 아니라 **재료가 선언한 실제 기하 특성**에서 나온다.

---

# 10. v3 전용 PortBond를 만들었다

기존 v1/v2 결합:

```text
PhysicalBond
```

v3 결합:

```text
PortBond
```

로 타입을 분리했다.

하나의 dataclass에 다음을 다 섞지 않았다.

```text
x?
y?
left_port?
right_port?
```

이렇게 하면:

```text
v2인데 port 있음
v3인데 x,y 있음
둘 다 있음
둘 다 없음
```

같은 잘못된 상태가 표현될 수 있기 때문이다.

따라서 물리 의미가 다른 결합 타입 자체를 분리했다.

---

# 11. PortBond가 현재 검증하는 것

예:

```text
A.E ↔ B.W
```

이 결합이 유효하려면 최소한 다음이 맞아야 한다.

1. A와 B가 실제 존재
2. 자기 자신과 결합하지 않음
3. A와 B가 실제 이웃
4. 대각선이 아님
5. A의 포트가 B를 향함
6. B의 포트가 A를 향함
7. E↔W 또는 N↔S처럼 마주 보는 포트
8. 각 재료가 해당 포트를 실제 선언
9. 같은 포트를 다른 bond가 이미 점유하지 않음
10. world wrap 규칙과 동일한 인접성 사용

---

# 12. 이동과 결합의 인접성을 같은 규칙으로 통일했다

기존 입자 이동은:

```text
VELOCITY[direction]
+
world width/height modulo wrap
```

으로 계산된다.

v3 결합에서도 별도의 인접 규칙을 새로 만들지 않았다.

공유 `neighbour()` 로직을 사용한다.

따라서 세계 경계에서:

```text
오른쪽 끝 → 왼쪽 끝
```

으로 이동할 수 있다면 결합 관계도 동일하게 wrap을 이해한다.

즉:

> 이동은 wrap되는데 결합은 세계 끝에서 끊기는 이상한 우주

를 방지했다.

---

# 13. PortBond endpoint 순서는 물리 의미가 없다

다음 두 표현은 동일한 결합이다.

```text
PortBond(A.E, B.W)
```

```text
PortBond(B.W, A.E)
```

canonicalization을 통해 두 endpoint 순서는 같은 물리 관계로 정규화된다.

`left`와 `right`는 계산 우선순위를 의미하지 않는다.

---

# 14. 현재 테스트 결과

최신 실행 기준:

```text
990 tests passing
```

하지만 테스트 숫자 자체보다 중요한 것은 **무엇을 검증하는 테스트인지**다.

---

# 15. fault injection도 수행했다

검사기가 진짜로 문제를 잡는지 보기 위해 일부러 결함을 넣었다.

PortBond 관련 결함 주입:

```text
인접성 검사 제거
마주보는 포트 검사 제거
포트 중복 점유 검사 제거
선언되지 않은 포트 허용
대각선 인접 허용
```

모두 테스트가 검출했다.

앞선 contested-census 검사기에서도:

- 에너지 문턱 무시
- 포트 한도 무시
- 모호성 탐지 누락
- 과잉 경합 보고
- 3체 off-by-one

같은 결함을 일부러 넣고 모두 검출되는 것을 확인했다.

목표는:

```text
테스트가 통과한다
```

가 아니라:

```text
테스트가 실제 잘못된 구현을 잡는다
```

를 확인하는 것이다.

---

# 16. 기존 v1/v2는 보존했다

causal v3를 만들면서 기존 버전을 덮어쓰지 않았다.

```text
causal v1
causal v2
causal v3
```

각 버전을 분리한다.

특히 기존:

```text
deterministic_polymer_chain_v2
```

run digest가 이전과 byte 단위로 동일함을 확인했다.

즉 새 언어와 새 물리를 추가했지만 기존 실험의 의미는 바꾸지 않았다.

---

# 17. World Spec Language 구조

현재 A를 만드는 언어는 대략 다음 계통을 가진다.

```text
World Spec Language

├─ HPP
│
├─ causal
│   ├─ v1
│   ├─ v2
│   └─ v3
│
└─ environment
    ├─ v1
    ├─ v2
    ├─ v3
    └─ v4
```

각 버전은 기존 세계를 덮어쓰는 것이 아니라 새로운 표현 능력을 추가하는 방식으로 관리한다.

---

# 18. syntax와 runtime을 구분한다

다음 두 가지는 같지 않다.

```text
syntax_valid
runtime_capability
```

예:

```text
문법상 표현 가능
하지만 현재 kernel이 아직 실행 못 함
```

이 경우 문제는 언어가 아니라 runtime 구현이다.

반대로:

```text
현재 문법으로 표현 자체가 불가능
```

하면 Language Revision 후보가 된다.

---

# 19. B와 World Spec Language의 관계

장기적으로 B는 World Spec Language를 사용해 A를 설계한다.

```text
사람의 자연어
↓
B
↓
World Spec Language
↓
Parser / Validator
↓
A
```

B가 현재 언어의 한계를 발견하면 직접 언어를 바꾸는 것이 아니라 새로운 가능성을 제안한다.

---

# 20. Language Revision Governance

B의 역할:

```text
문제 발견
↓
원인 후보 분석
↓
현재 언어의 표현 한계 판단
↓
새 표현 후보 제안
↓
LanguageRevisionProposal
```

그 다음:

```text
인간 검토
↓
회귀 검사
↓
독립 검증
↓
반례 확인
↓
승인 / 기각 / 수정 요청
```

승인된 경우에만:

```text
World Spec Language vN+1
```

이 만들어진다.

즉:

> **B는 연구자이자 제안자이고, 인간은 최종 검토자다.**

---

# 21. 현재 전체 구조

```text
                    사람
                     │
                  자연어
                     ↓
                     B
           ┌─────────┴─────────┐
           │                   │
       세계 설계            세계 이해
           │                   │
           ↓                   ↓
 World Spec Language      B 내부 모델
           │                   │
           ↓                   ↓
 Parser / Validator    Claim / Prediction
           │                   │
           ↓                   │
           A ←────── Observation
      결정론적 세계
           │
           ↓
      Trace / Evidence
           │
           ↓
  Independent Audit / Test
```

그리고 언어 표현 한계가 발견되면:

```text
B
↓
LanguageRevisionProposal
↓
인간 검토
↓
검증
↓
승인
↓
새 World Spec Language 버전
```

---

# 22. 지금 실제로 구현된 것

## 완료

- 결정론 causal 기반
- 다중 결합 기반
- 숨은 ID 경합 탐지
- contested census
- local interaction 원칙
- causal v3 syntax
- named ports
- world-absolute port directions
- adjacent-cell 결합 명세
- v3 `PortBond`
- wrap-aware neighbour validation
- facing-port validation
- declared-port validation
- single-port occupancy validation
- endpoint canonicalization
- v1/v2 backward compatibility
- frozen v2 digest 보존
- fault injection 검증
- World Spec Language Dictionary
- Language Revision Governance 설계

최신 테스트:

```text
990 passing
```

---

# 23. 아직 구현되지 않은 것

다음은 아직 완료되지 않았다.

- StructureState
- 구조 전체가 가지는 운동량
- lowest-ID motion carrier 제거
- 구조 이동 시 상대 기하 유지
- Contact Graph
- 일반적인 simultaneous compatible transition commit
- genuine contested state의 부족한 자유도 보고
- irreducible N-body hyperedge
- 실제 촉매 구조
- catalyst intermediate
- template replication
- boundary material
- 독립적인 구조 분열
- 실제 학습형 B
- B의 자동 LanguageRevisionProposal 생성

---

# 24. 다음 핵심 단계: StructureState

현재 다음 목표는:

```text
A — B — C
```

라는 연결 구조 자체가 물리 상태를 갖도록 만드는 것이다.

현재 목표 후보:

```text
StructureState

members
total_mass
total_momentum
topology
geometry
```

가장 중요한 것은 기존의:

```text
lowest-numbered member가 구조 운동을 대표
```

하는 방식을 제거하는 것이다.

---

# 25. 다음 단계의 핵심 시험

입자 ID만 전부 바꾼다.

```text
1 → 91
2 → 17
3 → 44
```

그리고 동일한 물리 상태를 실행한다.

성공 조건:

```text
원본 실행 결과
≡
재명명된 실행 결과
```

즉 ID를 바꿔도 물리적으로 동일해야 한다.

이것을 **relabeling invariance / equivariance gate**로 본다.

---

# 26. 쉬운 비유

처음 세계는 이런 레고에 가까웠다.

```text
레고를 여러 개 붙일 수는 있음

하지만:
- 전부 같은 위치에 겹쳐 있음
- 어느 구멍에 붙었는지 모름
- 애매하면 번호 작은 블록에 붙음
- 구조 움직임도 번호 작은 블록이 대표
```

지금은:

```text
블록마다 N/E/S/W 연결부가 있음
각 블록이 실제 공간 위치를 가짐
서로 이웃한 블록끼리만 연결
마주 보는 연결부끼리만 결합
한 연결부는 한 결합만 사용
세계 끝 wrap도 이동과 결합에 동일 적용
```

까지 왔다.

다음은:

```text
연결된 레고 전체가
하나의 구조처럼 움직이는 것
```

이다.

---

# 27. 현재 단계의 의미

아직 생명을 만든 것은 아니다.

하지만 이전보다 더 중요한 기반을 만들고 있다.

앞으로 어떤 복잡한 현상이 발생했을 때:

```text
이게 우리가 직접 넣은 명령 때문인가?
ID 때문인가?
코드 순서 때문인가?
숨은 상한 때문인가?
아니면 실제 물리 상호작용 때문인가?
```

를 훨씬 엄격하게 구분할 수 있다.

---

# 28. 중간 결론

> 현재 프로젝트는 **고수준 생명 행동을 직접 구현하는 방식이 아니라, 낮은 수준의 결정론적 물리·공간·에너지·결합 관계만으로 복잡한 구조가 나타날 수 있는 세계를 만들고, 그 과정에서 구현상의 우연이 물리 법칙으로 새어나오지 않도록 지속적으로 감사하는 구조**로 발전하고 있다.

다음 핵심 목표는 `StructureState`와 relabeling invariance다.

그 단계가 통과되면:

> **입자의 이름이 아니라 실제 공간·물질·에너지·관계가 구조의 운동과 상호작용을 결정한다**

는 목표에 한 단계 더 가까워진다.
