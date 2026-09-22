# LANGUAGE_REVISION_GOVERNANCE_V1

**제목:** 세계 명세 언어 확장 제안 및 승인 거버넌스 v1  
**상태:** 설계 초안 / RULES.md 승격 전 후보  
**날짜:** 2026-09-22  
**적용 대상:** B, World Spec Language, B-Architect, 향후 LanguageRevisionProposal 구현  
**관련 개념:** TheoryRevisionProposal, World Spec Language, B-Language, CapabilityManifest, EvidenceBridge, BoundaryEvaluation

---

## 0. 한 문장 정의

> **World Spec Language는 스스로 진화하지 않는다. B가 현재 언어의 표현 한계와 새로운 가능성을 발견해 확장안을 제안하고, 인간이 증거와 검증 결과를 검토한 뒤 승인·기각·수정을 결정한다.**

B는 연구자이자 제안자다.

인간은 최종 승인권을 가진 검토자다.

언어 변경은 이 둘 사이의 검증 가능한 절차를 통과해야 한다.

---

# 1. 왜 이 문서가 필요한가

World Spec Language는 고정된 파일 포맷 하나가 아니다.

프로젝트가 발전하면 현재 언어로 표현할 수 없는 물리 관계나 상태가 발견될 수 있다.

예:

- 이름 없는 결합 슬롯으로는 실제 접촉 방향을 표현할 수 없음
- pairwise bond만으로는 환원 불가능한 N-body 관계를 표현할 수 없음
- 현재 상태 변수만으로는 여러 합법적 결과 중 하나를 결정할 수 없음
- 문법은 표현할 수 있지만 runtime kernel이 아직 실행하지 못함
- 새로운 물리 자유도가 필요함

이때 두 극단을 모두 피한다.

### 극단 A — 언어를 영원히 고정

```text
현재 문법으로 표현 불가
→ 그냥 포기
```

이러면 B가 새로운 가능성을 발견해도 세계 표현 능력이 성장하지 못한다.

### 극단 B — B가 마음대로 언어를 수정

```text
현재 문법으로 표현 불가
→ B가 새 문법 추가
→ parser/kernel 즉시 수정
```

이러면 검증되지 않은 개념이 물리법칙으로 바로 침투한다.

따라서 중간 구조가 필요하다.

```text
문제 발견
→ B가 확장 후보 제안
→ 인간 검토
→ 검증
→ 승인된 경우에만 새 버전
```

---

# 2. 기본 철학

이 프로젝트에서 언어 확장은 **자동 자기개조**가 아니다.

더 정확한 구조는 다음과 같다.

```text
현재 World Spec Language
        ↓
B가 세계를 관찰·예측·설계
        ↓
반복적인 설명 실패 또는 표현 한계 발견
        ↓
기존 언어로 해결 가능한지 먼저 검사
        ↓
해결 불가능하면 확장 후보 제안
        ↓
LanguageRevisionProposal
        ↓
인간 검토
        ↓
검증 / 회귀 검사 / 독립 감사
        ↓
승인 / 기각 / 수정 요청
        ↓
승인된 경우에만 World Spec Language vN+1
```

핵심:

> **B에게는 제안권이 있고, 최종 변경권은 없다.**

---

# 3. 역할 구분

## 3.1 B가 할 수 있는 일

B는 다음을 할 수 있다.

- 현재 언어로 표현하기 어려운 현상 탐지
- 현재 언어의 표현 한계 지적
- 반복되는 실패 패턴 수집
- 새로운 필드 후보 제안
- 새로운 관계 타입 후보 제안
- 새로운 문법 구조 후보 제안
- 기존 표현으로 우회 가능한지 비교
- 새 표현이 왜 필요한지 설명
- 예상되는 장점과 위험 제시
- 기존 세계에 미칠 영향 분석
- 검증 실험 제안
- 반례 탐색
- LanguageRevisionProposal 생성

B는 단순히 "새로운 아이디어"만 제출하면 안 된다.

가능하면 다음을 같이 제출해야 한다.

```text
문제
현재 언어의 한계
기존 방식으로 해결 시도
실패 사례
새 표현 후보
예상 효과
위험
검증 방법
반례 조건
```

---

## 3.2 B가 할 수 없는 일

B는 다음을 직접 수행할 수 없다.

- 승인 없이 World Spec Language 수정
- 승인 없이 parser 변경
- 승인 없이 validator 변경
- 승인 없이 runtime kernel의 물리 의미 변경
- 기존 버전의 의미를 조용히 변경
- 검증 없이 새 개념을 사실로 승격
- 실패 사례 삭제
- 반례를 숨김
- 새 언어가 필요하다는 이유만으로 임의의 물리 개념 추가
- 사용자 승인 없이 새로운 실험 권한 확장

특히 다음 패턴은 금지한다.

```text
예측 실패
→ "새 힘이 필요함"
→ magic_force 추가
```

새 표현은 **실패를 설명하기 위한 임시 핑계**가 되어서는 안 된다.

---

## 3.3 인간의 역할

인간 검토자는 다음을 결정한다.

- 제안의 필요성
- 기존 언어로 정말 표현 불가능한지
- 새 표현이 지나치게 특수한지
- 더 일반적인 표현이 가능한지
- 새 표현이 기존 세계의 의미를 깨뜨리는지
- 숨은 구조 상한을 만드는지
- 검증 계획이 충분한지
- 추가 반례 실험이 필요한지
- 승인 / 기각 / 수정 요청

인간은 단순한 `YES / NO` 버튼이 아니다.

프로젝트의 의미 변화에 대한 최종 책임자다.

---

# 4. Theory Revision과 Language Revision의 구분

이 둘은 반드시 분리한다.

## 4.1 Theory Revision

현재 World Spec Language 안에서 법칙이나 관계를 수정하는 것.

예:

```text
기존:
A + B → C

수정:
A + B + minimum_energy → C
```

언어 자체는 충분하다.

필요한 것은 현재 언어 안에서 법칙을 더 정확하게 만드는 것이다.

### 예시

- 결합에 필요한 최소 에너지 변경
- 특정 물질 속성 추가 조정
- 기존 CausalRule 수정
- 파라미터 변경
- 기존 변수 사이 관계 수정
- 잘못된 이론 폐기

## 4.2 Language Revision

현재 언어로 필요한 관계나 상태를 **표현 자체를 할 수 없는 경우**다.

예:

```text
현재:
Bond(A, B)

필요:
하나의 관계에 A, B, C가 동시에 참여
```

pairwise bond 두 개로는 물리적 성질이 보존되지 않는다면 현재 언어 자체가 부족하다.

이 경우 후보:

```text
InteractionRelation(
    participants=[A, B, C, ...]
)
```

### 예시

- named ports 추가
- `adjacent_cells` locality 추가
- 새로운 geometry 표현 추가
- 환원 불가능한 N-body relation
- 새로운 상태 자유도 추가
- 현재 parser/schema가 표현하지 못하는 관계 타입

---

# 5. Language Revision을 제안할 수 있는 조건

B는 단순히 "이게 더 좋아 보인다"는 이유로 언어 확장을 제안하면 안 된다.

최소한 다음 조건 중 하나 이상이 있어야 한다.

### 5.1 표현 불가능

현재 언어로 물리적으로 필요한 상태나 관계를 표현할 수 없다.

### 5.2 반복적인 설명 실패

같은 종류의 실패가 여러 사례에서 반복된다.

### 5.3 구현 세부사항이 물리를 결정

예:

- particle ID
- 배열 순서
- thread 순서
- 자료구조 정렬 순서

이런 비물리 정보가 실제 결과를 결정한다.

### 5.4 숨은 구조 상한

선언된 법칙이 아닌 구현 산술이나 자료구조가 다음을 만든다.

- 최대 사슬 길이
- 최대 결합 수
- 특정 구조 이상 성장 불가
- 특정 참가자 수 이상 상호작용 불가

### 5.5 현재 언어가 물리 자유도를 잃어버림

예:

```text
현실적으로는 서로 다른 접촉 위치
→ 언어에서는 같은 cell 하나로 붕괴
```

이 경우 필요한 자유도를 추가하는 언어 확장이 후보가 될 수 있다.

---

# 6. LanguageRevisionProposal

향후 B는 언어 확장안을 자유 형식 텍스트가 아니라 구조화된 제안으로 제출하는 것을 목표로 한다.

초기 개념 형식:

```text
LanguageRevisionProposal

proposal_id
title

problem_statement

current_language_version
current_capability

observed_failure_cases
counterexamples

why_current_language_is_insufficient

existing_workarounds_attempted
why_workarounds_failed

proposed_new_construct

syntax_candidate
semantic_meaning

expected_benefits
expected_risks

backward_compatibility_impact

runtime_requirements
audit_requirements

alternative_designs_considered

falsification_conditions

validation_plan
held_out_plan

human_decision
decision_reason
```

초기에는 Markdown 또는 구조화 JSON으로 구현할 수 있다.

형식 자체보다 중요한 것은 **근거와 반례를 같이 제출하는 것**이다.

---

# 7. 제안 수명주기

권장 상태:

```text
PROPOSED
↓
UNDER_REVIEW
↓
NEEDS_EVIDENCE
↓
APPROVED_FOR_EXPERIMENT
↓
IMPLEMENTED_EXPERIMENTALLY
↓
VALIDATED
↓
ADOPTED
```

실패 경로:

```text
REJECTED
FALSIFIED
SUPERSEDED
DEFERRED
```

중요:

`REJECTED`나 `FALSIFIED` 제안도 삭제하지 않는다.

나중에 같은 실패가 반복될 때 과거 제안과 반례가 중요한 증거가 될 수 있다.

---

# 8. 승인 단계

## 8.1 1차 — 필요성 검토

질문:

- 현재 언어로 정말 표현 불가능한가?
- 기존 construct 조합으로 해결할 수 없는가?
- 단순 kernel bug는 아닌가?
- 데이터 부족은 아닌가?
- 관측 오류는 아닌가?
- 새로운 언어가 아니라 새로운 state variable이면 충분한가?

## 8.2 2차 — 일반성 검토

질문:

- 특정 테스트 하나만 통과시키는 특수 규칙인가?
- 여러 상황에서 사용할 수 있는 일반 개념인가?
- 개수 기반 예외를 만드는가?
- ID나 코드 순서에 의존하는가?
- 물리적 의미가 명확한가?

## 8.3 3차 — 기존 세계 영향

반드시 확인:

- 기존 world spec이 그대로 파싱되는가?
- 기존 v1/v2/vN run digest가 보존되는가?
- 기존 법칙 의미가 조용히 바뀌지 않는가?
- 기존 audit가 여전히 유효한가?

가능하면 새 표현은 새 버전에서만 사용한다.

## 8.4 4차 — 실험 구현

승인 전 정식 문법으로 승격하지 않는다.

실험 버전에서:

- parser
- validator
- runtime
- auditor
- fault injection
- regression

을 검증한다.

## 8.5 5차 — 독립 검증

가능하면 다음을 포함한다.

- 독립 parser
- 독립 compliance audit
- fault injection
- held-out world
- relabeling test
- conservation test
- backward compatibility test

## 8.6 6차 — 인간 최종 승인

검증을 통과해도 자동 승격하지 않는다.

최종적으로 인간이:

```text
승인
기각
수정 요청
추가 실험 요청
보류
```

중 하나를 결정한다.

---

# 9. 버전 관리 원칙

언어 변경은 기존 버전을 덮어쓰지 않는다.

예:

```text
causal v1
causal v2
causal v3
causal v4
```

새로운 의미가 필요한 경우 새 버전을 만든다.

기존 버전은 기준선과 재현성을 위해 보존한다.

## 9.1 금지

```text
causal v2의 의미를 조용히 바꿈
```

## 9.2 허용

```text
causal v2 유지
+
causal v3에서 새로운 기능 추가
```

---

# 10. 첫 실제 사례 — causal v2 → causal v3

현재 프로젝트에는 이미 수동 형태의 Language Revision 사례가 있다.

## 문제 발견

사슬 성장 과정에서 여러 멤버가 동일하게 결합 가능할 때:

```text
sorted(members)
```

순서가 결합 결과를 결정했다.

particle ID를 바꾸면 물리 결과가 바뀌었다.

즉 ID가 물리적 일을 하고 있었다.

## 원인 분석

기존 표현:

```text
ports: 4
```

포트 수는 있었지만 각각의 포트를 구별할 물리 정보가 없었다.

`orientation` 하나가 입자 방향과 결합 방향 역할을 동시에 하고 있었다.

## 기존 언어의 한계

현재 상태만으로 어느 포트가 어느 방향인지 표현할 수 없었다.

따라서 kernel은 물리적으로 선택할 근거가 없었고 ID 순서에 의존했다.

## 확장 제안

causal v3:

```json
{
  "ports": ["N", "E", "S", "W"]
}
```

그리고:

```text
locality:
same_cell
→
adjacent_cells
```

결합 규칙도 orientation이 아니라 named port를 사용한다.

## 중요한 점

이 변경은 처음부터 존재했던 "계획 기능"이 아니다.

실제 결함:

```text
ID-order tie-break
```

를 발견하고,

원인을:

```text
물리 자유도 부족
```

으로 분석한 뒤,

표현 능력을 확장한 것이다.

즉 현재는 인간이 Language Revision 과정을 수행하고 있다.

장기적으로는 이 중 다음 부분을 B가 맡을 수 있다.

```text
문제 탐지
→ 원인 후보 분석
→ 표현 한계 판단
→ 확장안 제안
```

최종 승인은 인간에게 남는다.

---

# 11. B의 미래 역할

B의 수정 범위는 단계적으로 깊어질 수 있다.

```text
Level 1
파라미터 조정 제안

Level 2
기존 관계 수정 제안

Level 3
새 state variable 제안

Level 4
새 law candidate 제안

Level 5
현재 언어의 표현 한계 지적

Level 6
LanguageRevisionProposal 생성
```

높은 단계일수록 더 강한 증거가 필요하다.

특히 Level 6는 가장 강한 검토 대상 중 하나다.

---

# 12. 실패 진단 순서

언어 확장은 마지막 쪽에 있어야 한다.

B가 예측 실패를 볼 때 다음 순서로 의심한다.

```text
1. trace / sensor 문제인가?
2. 관측 누락인가?
3. state 값 오류인가?
4. parameter 오류인가?
5. relation 오류인가?
6. 새로운 variable/state type이 필요한가?
7. 기존 법칙이 잘못됐는가?
8. 현재 언어로 필요한 관계를 표현할 수 없는가?
```

8번까지 내려왔을 때 Language Revision을 검토한다.

즉:

> **설명이 틀렸다고 해서 바로 언어를 바꾸지 않는다.**

---

# 13. B-Language와의 관계

B-Language와 World Spec Language는 다르다.

## B-Language

B가 외부에 다음을 전달하는 공용 프로토콜:

- 주장
- 증거
- 예측
- 능력
- 관측 범위
- 반증 조건

## World Spec Language

A 세계 자체를 선언하는 언어:

- 물질
- 위치
- 결합 규칙
- 환경
- 물리 법칙
- geometry
- causal relation

## LanguageRevisionProposal

B-Language 쪽의 **제안 프로토콜**을 통해:

```text
"World Spec Language에 이런 표현을 추가해야 한다"
```

라는 제안을 전달할 수 있다.

즉:

```text
B internal reasoning
↓
B-Language
↓
LanguageRevisionProposal
↓
human review
↓
World Spec Language vN+1
```

---

# 14. CapabilityManifest와의 연결

B는 현재 언어와 runtime의 능력을 구분해서 알아야 한다.

예:

```text
syntax_valid = true
runtime_capability = unsupported
```

이것은 Language Revision과 Runtime Revision을 구분하는 데 중요하다.

## 사례 A — 문법도 표현 못 함

```text
syntax_valid = false
reason = no representation exists
```

Language Revision 후보.

## 사례 B — 문법은 표현 가능

```text
syntax_valid = true
runtime_capability = unsupported
```

이 경우 언어 문제가 아니다.

kernel/runtime 구현 문제다.

---

# 15. 새 언어 요소의 증거 요구

새 construct를 승인하려면 최소한 다음 중 가능한 만큼 확보한다.

- 실제 실패 사례
- 재현 가능한 trace
- 현재 표현으로 해결 실패
- 대안 설계 비교
- 반례
- 기존 세계 회귀 결과
- held-out 결과
- independent audit
- fault injection
- 보존 법칙 검사
- ID/relabeling 불변성 검사

새 표현이 더 많은 것을 설명한다는 이유만으로는 부족하다.

기존 세계를 망가뜨리지 않는지도 중요하다.

---

# 16. 특수 예외 금지

다음과 같은 문법 확장은 경계한다.

```text
if chain_length == 3:
    special_rule
```

```text
if particle_count == 3:
    special_collision
```

```text
if particle_id < other_id:
    winner
```

새 언어 요소는 특정 실패 하나를 패치하기 위한 예외가 아니라 가능한 한 일반적인 물리 개념이어야 한다.

---

# 17. 제안의 반증 가능성

LanguageRevisionProposal도 반증 가능해야 한다.

예:

```text
제안:
named ports가 ID-order ambiguity의 원인이다

반증 조건:
named ports + geometry를 추가해도
재명명 불변성이 회복되지 않는다
```

이 경우:

```text
제안 일부 또는 전체가 부족함
```

으로 기록한다.

즉 언어 확장안도 "아이디어"가 아니라 검증 대상이다.

---

# 18. 인간 승인 후에도 끝이 아니다

언어 요소가 승인되어도 다음 상태를 구분한다.

```text
문법 승인
↓
parser 구현
↓
validator 구현
↓
runtime 구현
↓
audit 구현
↓
검증 완료
```

따라서 다음 상태를 혼동하지 않는다.

```text
문법상 존재
≠
runtime 지원
≠
검증 완료
```

World Spec Language Dictionary의 상태 표기와 연결한다.

예:

```text
📜 문법만 존재
✅ 실제 구현·검증
🧭 설계 후보
🚫 의도적 금지
```

---

# 19. B에게 필요한 장기 능력

B가 Language Revision을 제대로 제안하려면 단순 생성 모델 이상이 필요하다.

필요 능력 후보:

- failure clustering
- counterexample memory
- causal diagnosis
- representation gap detection
- alternative proposal generation
- regression impact estimation
- falsification planning
- experiment proposal
- evidence retrieval
- prior failed proposal retrieval

이 능력은 하나의 거대 모델일 필요가 없다.

여러 BrainAdapter가 협력할 수 있다.

---

# 20. 금지되는 자기개조 해석

이 문서는 다음을 의미하지 않는다.

> B가 자기 마음대로 언어와 물리법칙을 다시 쓴다.

정반대다.

이 문서의 목적은:

> **B의 창의적 제안 능력과 인간의 최종 통제·검증을 동시에 유지하는 것**

이다.

---

# 21. 권장 사용자 인터페이스

향후 B가 제안을 만들면 인간에게 최소한 다음처럼 보여준다.

```text
[Language Revision Proposal]

문제:
현재 pairwise bond로는 이 상태를 표현할 수 없음

증거:
- run X
- run Y
- held-out Z

현재 방식:
Bond(A,B) + Bond(B,C)

문제점:
관계 전체의 성질을 보존하지 못함

제안:
InteractionRelation(participants=[...])

영향:
causal v4 필요

기존 세계 영향:
v1/v2/v3 unchanged

위험:
audit와 serializer 확장 필요

검증 계획:
1. parser
2. runtime
3. fault injection
4. held-out
5. independent audit
```

인간은 여기서 승인 여부를 결정한다.

---

# 22. 장기 목표

장기적으로 프로젝트는 다음 구조를 목표로 한다.

```text
세계 관찰
↓
B의 내부 모델
↓
예측
↓
실패
↓
실패 원인 진단
↓
theory 수정 가능?
├─ Yes → TheoryRevisionProposal
└─ No
    ↓
현재 언어 표현 한계인가?
├─ No → 다른 원인 탐색
└─ Yes
    ↓
LanguageRevisionProposal
    ↓
인간 검토
    ↓
검증
    ↓
승인된 경우에만 새 언어 버전
```

---

# 23. 핵심 원칙

1. World Spec Language는 스스로 변경되지 않는다.
2. B는 언어 확장을 제안할 수 있다.
3. B에게 최종 언어 변경 권한은 없다.
4. 인간이 최종 승인자다.
5. Language Revision은 Theory Revision과 구분한다.
6. 현재 언어로 해결 가능한 문제는 언어 확장으로 해결하지 않는다.
7. 새 표현은 실제 실패와 증거에서 출발해야 한다.
8. 반례와 실패 제안을 삭제하지 않는다.
9. 기존 버전의 의미를 조용히 바꾸지 않는다.
10. 새 의미는 새 버전으로 추가한다.
11. syntax capability와 runtime capability를 구분한다.
12. LanguageRevisionProposal 자체도 반증 가능해야 한다.
13. 특정 사례 하나를 위한 특수 예외는 경계한다.
14. 가능한 한 일반적인 표현을 선호한다.
15. 검증 전에는 문법 존재와 물리적 진실을 동일시하지 않는다.
16. 승인 후에도 parser/runtime/audit 검증이 모두 필요하다.
17. B의 창의성은 제안에서 발휘되고, 물리적 권위는 검증에서 나온다.

---

# 24. 최종 문장

> **B는 새로운 가능성을 상상할 자유를 가진다. 그러나 그 가능성이 세계의 언어가 되려면 증거, 반례, 검증, 그리고 인간의 승인을 통과해야 한다.**
