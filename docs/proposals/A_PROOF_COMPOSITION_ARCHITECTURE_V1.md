# A Proof Composition Architecture V1
## A 수치 인증을 위한 계층적 분할·증명 조립·독립 검증 구조

**문서 상태:** PROPOSAL / 장기 설계  
**적용 범위:** A의 수치 인증·감사 계층  
**현재 구현 승인 문서가 아님:** 이 문서는 장기 구조를 정의한다. 현재 Gate의 완료·인증 근거로 사용하지 않는다.  
**현재 기준 상태:** C1-B1 outer formal bound ④ 진행, ④-4b `NotCertified`, coverage `11/64 region`, gap `84`, precision cap `16384-bit` 유지.  
**B와의 관계:** 이 시스템은 연구자 B가 아니라 **세계 밖 설계자·감사 도구**다.

**2026-09-28 착수 기록:** [C1-B1 최소 필터·proof object·별도 checker](../active/C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md)를 구현했다.
이 문서 전체 구조의 구현 완료가 아니다. 아래 6,195/8,076은 착수 기준이며 현재 class 집계는 6,436/7,835다.
새로 확인된 범위는 작은 class의 유한 입력뿐이며 실제 큰 class symbolic 하한·새 region은 0개다.

---

# 1. 왜 이 문서가 필요한가

현재 C1-B1 ④ 인증에서는 하나의 거대한 정리로 전체 입력 영역을 한 번에 닫기 어렵다.

이미 확인된 사실은 다음과 같다.

- 전체 shell 15~18의 분석 class는 14,271개다.
- 그중 6,195개 class는 필요한 하한을 확보했다.
- 8,076개 class는 아직 미해결이다.
- 실제 small-gap 반례는 현재 0개다.
- 그러나 "반례를 발견하지 못함"은 "없음을 증명함"과 다르다.
- 현재 큰 class의 문제는 여러 조건이 **서로 다른 입력에서 각각 가능**한데도, 느슨한 분석에서는 **같은 입력에서 동시에 가능한 것처럼** 남을 수 있다는 점이다.

따라서 앞으로는 다음 방식이 필요하다.

> 큰 문제를 작은 영역으로 나누고,  
> 각 영역에 맞는 작은 lemma를 적용하고,  
> 그 결과를 proof object로 조립한 뒤,  
> 독립 verifier가 최종적으로 검증한다.

이 문서는 이 구조를 장기적으로 일반화한 설계다.

---

# 2. 쉬운 비유와 실제 구조의 대응

| 비유 | 실제 구조 |
|---|---|
| 거대한 정사각형을 여러 칸으로 쪼갬 | hierarchical domain partition |
| 물류창고의 구역·선반·상자 | proof warehouse / proof index |
| 레고 블록 | reusable lemma |
| 레고 설명서 | proof object |
| 설명서를 보고 조립 | proof composition |
| 새로운 레고 조합을 창작 | automated proof search |
| 검수원 | independent verifier |
| 미해결 상자만 더 잘게 나눔 | adaptive refinement |
| 위치 안내 프로그램 | proof/dependency index |
| 샘플 몇 점으로 전체를 가늠 | heuristic survey only |
| 오차까지 감싼 보간 | rigorous enclosure lemma candidate |

핵심은 비유가 아니라 **권한 경계**다.

- 창고는 저장만 한다.
- 후보 생성기는 제안만 한다.
- verifier만 최종 판정한다.
- 미해결은 미해결로 남긴다.
- 물리를 증명에 맞춰 바꾸지 않는다.

---

# 3. 최상위 목표

최종 목표는 다음과 같은 인증 시스템이다.

```text
원래 물리/수치 계약
        ↓
전체 domain
        ↓
계층적 분할
        ↓
각 영역에 적용 가능한 lemma 탐색
        ↓
proof object 생성
        ↓
독립 verifier
        ↓
┌───────────────────┬───────────────────┐
│ Certified         │ Unresolved        │
└───────────────────┴───────────────────┘
        │                    │
        │                    └→ 필요한 경우만 더 세분화
        ↓
전체 coverage 계산
        ↓
모든 의무가 닫힌 경우에만 상위 인증 승격
```

이 구조는 "모든 영역이 같은 이유로 안전해야 한다"를 요구하지 않는다.

예를 들어 다음처럼 서로 다른 이유로 전체를 덮어도 된다.

```text
영역 A → quotient lemma
영역 B → remainder lemma
영역 C → parity lemma
영역 D → same-input congruence lemma
영역 E → exact finite enumeration
```

중요한 것은 **원래 domain에서 빠진 영역이 0개**이고, 각 영역의 증거가 독립 verifier를 통과하는 것이다.

---

# 4. 절대 깨면 안 되는 경계

## 4.1 원래 domain을 줄이지 않는다

분할은 분석 방법일 뿐이다.

금지:

```text
풀기 어려운 입력 제거
→ 남은 범위만 증명
→ 전체 인증이라고 주장
```

허용:

```text
전체 domain
→ disjoint sub-domain으로 분할
→ 각 sub-domain을 따로 증명
→ 합집합이 원래 domain과 정확히 같음을 검증
```

모든 분할 단계는 다음을 증명해야 한다.

- 누락 없음
- 중복 여부 명시
- endpoint 보존
- 원래 domain과 합집합 동일

---

## 4.2 미해결은 실패도 성공도 아니다

상태는 최소한 다음처럼 구분한다.

- `certified`
- `counterexample`
- `unresolved`
- `survey_only`
- `invalid_evidence`

특히 `unresolved`는 다음 뜻이다.

> 현재 증명 방법으로는 판정하지 못했다.

다음 뜻이 아니다.

> 실제 반례가 있다.

또한 반례를 찾지 못했다는 이유로 `certified`로 승격하지 않는다.

---

## 4.3 물리와 인증을 분리한다

증명을 쉽게 만들기 위해 다음을 바꾸면 안 된다.

- A의 물리식
- D_valid 계약
- multi-output 계약
- precision cap
- 실제 domain
- 기존 certified family
- reference executor의 의미

인증 시스템은 A를 설명하고 검증해야지, A를 인증 시스템에 맞게 바꾸면 안 된다.

---

## 4.4 이 시스템은 B가 아니다

이 proof system은 다음 정보에 접근할 수 있다.

- 전체 수학식
- fixture
- frozen identity
- class inventory
- 전체 domain
- 검사 전용 내부 상태

따라서 이는 **설계자·감사 계층**이다.

연구자 B에게 이 정보를 전달하면 안 된다.

```text
A ──→ 외부 감사/인증 시스템   허용
A ──→ B                       B의 감각/도구 계약을 통해서만 허용
외부 인증 시스템 ──→ B       금지
```

---

# 5. 핵심 구성요소

## 5.1 Domain Partition

전체 domain을 계층적으로 나눈다.

예:

```text
C1-B1
└─ shell
   └─ valuation class
      └─ residue class
         └─ parameter interval
            └─ 필요 시 sub-class
```

분할 기준은 물리 법칙이 아니라 **증명 편의용 외부 분석 구조**다.

### 규칙

- 큰 영역에서 증명되면 더 쪼개지 않는다.
- 실패한 영역만 세분화한다.
- 처음부터 모든 입력을 미세하게 나누지 않는다.
- 분할로 class 수가 폭발하면 중단하고 다른 lemma를 찾는다.

---

## 5.2 Lemma Block

lemma는 레고 블록이다.

각 lemma는 반드시 다음을 가진다.

```text
lemma_id
version
input_contract
preconditions
conclusion
valid_domain
dependencies
source_bindings
failure_meaning
```

예:

```text
lemma_id: SAME_INPUT_CRT_V1

preconditions:
  - j is integer in [0, N-1]
  - exact polynomial identity verified
  - denominator positive
  - odd quotient contract preserved

conclusion:
  - no j satisfies all small-gap necessary conditions
```

lemma는 가능한 한 작고 명확해야 한다.

---

## 5.3 Proof Object

proof object는 "이 class가 왜 안전한지"를 기계가 다시 확인할 수 있는 설명서다.

예:

```yaml
proof_id: C1B1-S18-CLASS-002381
target:
  shell: 18
  class_id: 2381

method:
  - PRIOR_WHOLE_CLASS_BOUND_V1

dependencies:
  - frozen_identity_hash: ...
  - class_fixture_hash: ...

claim:
  normalized_gap_lower: 123456
  required_gap: 100000
```

또는 여러 lemma를 조립할 수 있다.

```yaml
method:
  - POSITIVE_DENOMINATOR_V1
  - ODD_H_RANGE_V1
  - SAME_INPUT_CRT_V1
  - GAP_EXCLUSION_V2
```

proof object 자체는 판정자가 아니다.

---

## 5.4 Proof Warehouse

proof warehouse는 **증명 보관소**다.

> 저장·metadata·의존성 골조의 명세는 [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md)에 있다(설계 전용·미구현, 2026-09-28 설계자 판정 Q8). 아래 최소 저장 정보와 권한 경계는 그 문서의 세 축 상태 모델·정체성 규칙으로 구체화됐다.

최소 저장 정보:

```text
proof_id
target_domain
status
proof_method
dependencies
proof_payload
checker_version
source_hashes
created_from
```

warehouse가 해야 할 일:

- 증명 위치 찾기
- 같은 proof 중복 방지
- dependency 추적
- 어떤 source/version에 묶여 있는지 기록
- 기존 proof 재사용

warehouse가 하면 안 되는 일:

```text
status == "certified"
→ 검증 없이 신뢰
```

모든 certification은 verifier가 proof object를 다시 검사해야 한다.

---

## 5.5 Proof Dependency Graph

증명 의존성은 기본적으로 DAG로 유지한다.

허용:

```text
Frozen Identity
   ↓
Lemma A
   ↓
Lemma B
   ↓
Final Claim
```

금지:

```text
Lemma A depends on B
Lemma B depends on C
Lemma C depends on A
```

순환 보증은 증명이 아니다.

자동 검사 항목:

- dependency cycle
- unknown dependency
- version mismatch
- source hash mismatch
- stale proof

---

## 5.6 Candidate Builder

후보 생성기는 자유롭게 탐색할 수 있다.

가능한 역할:

- 어떤 lemma가 적용 가능한지 탐색
- 여러 lemma 조합
- subdivision 위치 제안
- exact enumeration으로 넘길 작은 영역 탐지
- 더 강한 congruence 조합 탐색

그러나 권한은 여기까지다.

```text
Candidate Builder
→ proof candidate
→ verifier
```

builder는 certification 상태를 직접 바꾸면 안 된다.

---

## 5.7 Independent Verifier

최종 판정자다.

독립성 원칙:

- builder의 `pass=True`를 믿지 않는다.
- 가능하면 원래 identity와 primitive data에서 다시 계산한다.
- 생성기와 동일한 helper를 무비판적으로 재사용하지 않는다.
- fault injection으로 잘못된 proof가 실제로 거부되는지 확인한다.

과거 프로젝트의 중요한 교훈:

> 같은 코드가 결과를 만들고 같은 코드가 결과를 검사하면, 둘이 같이 틀렸을 때 오류를 잡지 못할 수 있다.

따라서 verifier 독립성은 선택 사항이 아니다.

---

# 6. 여러 증명서를 합치는 방식

하나의 거대한 theorem만 허용하지 않는다.

예:

```text
전체 14,271 class

Proof A → 5,541
Exact Enumeration → 654
Proof B → 1,800
Proof C → 2,100
Proof D → 2,900
Adaptive Refinement → 1,276
────────────────────────
총 14,271
```

이 구조가 유효하려면 다음을 확인해야 한다.

1. 전체 원래 class inventory와 동일한가?
2. 빠진 class가 있는가?
3. 같은 class에 여러 proof가 있을 경우 모순은 없는가?
4. 각 proof가 최신 source/version과 연결되는가?
5. 모든 certified proof가 독립 verifier를 통과했는가?

---

# 7. Adaptive Refinement

큰 class가 바로 증명되지 않을 때만 나눈다.

```text
Class
 ↓
증명 시도
 ├─ 성공 → 끝
 └─ 실패
      ↓
   2~N개 sub-class
      ↓
   각각 증명
```

세분화 자체가 목표가 아니다.

다음 경우 세분화를 중단한다.

- class 수가 폭발
- 같은 유형의 unresolved만 반복
- proof strength가 증가하지 않음
- exact enumeration보다 비용이 큼
- 원래 문제의 상관관계를 오히려 잃음

---

# 8. 보간·근사·샘플링 규칙

## 8.1 탐색용으로 허용

보간·샘플링은 다음 용도로 사용할 수 있다.

- subdivision 후보 위치 찾기
- 위험해 보이는 영역 찾기
- lemma 후보 구조 탐색
- 계산 우선순위 정하기

이 경우 상태는 `survey_only`다.

---

## 8.2 인증으로 쓰려면 추가 증명이 필요

다음은 인증이 아니다.

```text
양 끝 안전
→ 가운데도 아마 안전
```

다음과 같이 전체 구간 오차를 엄밀히 감싸야 한다.

```text
approximation
+
rigorous error bound
+
whole-domain enclosure
+
boundary separation
```

이 조건을 만족한 경우에만 정식 lemma 후보가 된다.

특히 기존 D_valid의 미측정 에너지 보간·외삽 금지와 충돌하지 않도록 한다.

---

# 9. Exact Enumeration의 지위

유한 domain에서 모든 입력을 실제로 빠짐없이 확인했다면 강한 증거가 될 수 있다.

조건:

- domain 유한성 증명
- inventory 완전성
- 모든 입력 실제 평가
- source binding
- 독립 재평가 또는 checker
- 빠진 입력 0

금지:

```text
많이 계산했다
→ 사실상 전수
```

전수는 "많이"가 아니라 "전부"여야 한다.

---

# 10. 자동 Proof Search

장기적으로는 lemma 조합을 자동 탐색할 수 있다.

예:

```text
Goal:
  gap >= M for class X

Available blocks:
  L1, L2, L3, ... Ln

Search:
  L3 + L8 + L12
        ↓
  proof candidate
        ↓
  verifier
```

자동 search는 다음을 최적화할 수 있다.

- proof 길이
- 계산 비용
- dependency 수
- verifier 비용
- coverage 증가량

그러나 자동 search가 최종 판정을 내리면 안 된다.

---

# 11. Certification 상태 승격 규칙

예시 상태:

```text
survey_only
    ↓
lemma_candidate
    ↓
proof_object_generated
    ↓
independent_verified
    ↓
coverage_candidate
    ↓
coverage_recomputed
    ↓
certified
```

중간 단계를 생략하지 않는다.

특히 현재 C1-B1에서는 다음 값이 자동으로 바뀌면 안 된다.

```text
④-4b NotCertified
11/64 region
gap 84
MAX_PRECISION_BITS = 16384
```

새 proof가 나와도 독립 checker와 fresh coverage 계산 전에는 유지한다.

---

# 12. 실패 의미

각 실패는 의미가 다르다.

| 실패 | 의미 |
|---|---|
| lemma 적용 불가 | 다른 lemma 필요 |
| same-input 후보 존재 | 실제 반례일 수도, 추가 조건이 필요할 수도 있음 |
| verifier 거부 | proof object 또는 lemma 오류 |
| source hash mismatch | proof stale |
| subdivision 폭발 | 분할 전략 부적합 |
| exact enumeration에서 실제 작은 gap | sufficient condition 반례 |
| 전체 impulse rounding 실패 확인 | 훨씬 강한 실제 인증 반례 |

서로 다른 실패를 같은 것으로 취급하지 않는다.

---

# 13. 현재 C1-B1과의 연결

현재 직접 필요한 것은 전체 시스템 구현이 아니다.

현재 ④-4c-3의 다음 의무는:

> 큰 class에서 가변 B(j), quotient, remainder, denominator factor, odd h의 **같은-j 상관관계**를 더 강하게 보존하는 것.

따라서 현재 구현은 아래 최소 범위만 대상으로 한다.

```text
same-input lemma
→ proof object 최소형
→ independent verifier 최소형
```

다음은 현재 단계에서 하지 않는다.

- 범용 theorem prover
- 대규모 proof database
- 자동 proof synthesis 전면 구현
- A 전체 certification framework 전환
- B와 연결
- 물리식 수정

---

# 14. 장기 확장 가능성

C1-B1에서 구조가 검증되면 나중에 다음에도 재사용할 수 있다.

- rounding completeness
- force bound
- integration error
- collision decision
- energy/momentum conservation proof
- native/reference equivalence
- multi-resolution exactness proof

단, 각 분야의 실제 수학적 전제는 별도로 검증해야 한다.

"proof framework가 존재한다"는 이유만으로 다른 물리가 인증되는 것은 아니다.

---

# 15. 설계 원칙 요약

1. 큰 문제를 작은 검증 가능한 영역으로 나눈다.
2. 모든 영역에 같은 증명법을 강요하지 않는다.
3. lemma는 재사용 가능한 작은 블록으로 만든다.
4. proof object는 조립 설명서다.
5. warehouse는 보관소일 뿐 판정자가 아니다.
6. builder는 후보를 만들 뿐 인증하지 않는다.
7. verifier는 독립적으로 검사한다.
8. 미해결은 미해결로 남긴다.
9. 분할로 원래 domain을 줄이지 않는다.
10. 보간은 error enclosure 없이는 증명이 아니다.
11. proof dependency는 순환 없이 관리한다.
12. 물리를 증명에 맞춰 바꾸지 않는다.
13. 이 시스템은 B가 아니라 외부 감사 계층이다.
14. 현재 Gate가 요구하는 최소 구현부터 한다.
15. 실제 coverage가 독립적으로 닫히기 전에는 상위 인증 상태를 올리지 않는다.
