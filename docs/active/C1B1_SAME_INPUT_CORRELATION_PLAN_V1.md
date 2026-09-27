# C1-B1 ④-4c-4 — Same-Input Correlation Proof Plan V1
## 큰 class의 quotient·remainder·가변 분모 인수·odd h를 같은 입력에서 결합하는 단계 설계

**문서 상태:** ACTIVE PLAN / 최소 구현 착수, 전체 계획 미완료  
**대상:** C1-B1 outer formal bound ④의 ④-4c-4  
**직전 상태:** ④-4c-3 normalized quotient-gap survey 완료  
**현재 판정:** ④-4b `NotCertified`, `11/64 region`, gap `84` 유지  
**새 인증 region:** 0  
**precision cap:** `16384-bit` 유지

**2026-09-28 구현 기록:** [최소 필터·proof object·별도 checker 조사](C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md).
아래 6,195 하한/8,076 미해결은 착수 시점의 기준이다. 현재 집계는 6,436/7,835다.
증가한 241 class는 9〜16입력을 singleton까지 나눠 확인한 결과이며, 큰 class의 새 symbolic 하한은 0개다.
큰 class를 같은 입력 조건으로 닫는 목표와 범용 시스템은 미완료다.

---

# 1. 현재 상태

shell 15~18의 전체 분석 class:

```text
14,271
```

현재 하한 확보:

```text
6,195
```

미해결:

```text
8,076
```

직전 단계에서 큰 class에 적용한 quotient 범위와 고정 coefficient coset 조건으로 새로 닫힌 class:

```text
0
```

실제 small-gap 입력 반례:

```text
0
```

따라서 현재 문제는 "실제 반례가 발견됐다"가 아니다.

현재 문제는:

> 필요한 조건들을 너무 느슨하게 분리해서 보므로,  
> 서로 다른 입력에서 가능한 조건이 한 입력에서 동시에 가능한 것처럼 남을 수 있다.

---

# 2. 이번 단계의 핵심 질문

직전 단계의 질문:

```text
quotient 조건 가능한 값이 있는가?
remainder 조건 가능한 값이 있는가?
분모 인수 조건 가능한 값이 있는가?
odd h 조건 가능한 값이 있는가?
```

이번 단계의 질문:

```text
하나의 동일한 입력 j에서
이 조건들이 동시에 성립 가능한가?
```

즉 이번 단계는 **same-input correlation 보존**이 핵심이다.

---

# 3. 쉬운 예시

예를 들어 어떤 class에서:

```text
A 조건 → j = 3에서만 가능
B 조건 → j = 8에서만 가능
C 조건 → j = 20에서만 가능
```

이라면 각 조건은 따로 보면 가능하다.

하지만:

```text
A + B + C를 동시에 만족하는 j
```

는 없다.

이 경우 이 class는 현재의 느슨한 조건에서는 `unresolved`로 남을 수 있지만,
same-input lemma에서는 배제할 수 있다.

---

# 4. 유지해야 할 정확한 구조

class 내부 입력을 하나의 공통 parameter로 둔다.

예:

```text
n = n0 + s*j
j ∈ {0, 1, ..., N-1}
```

다음 모든 값을 같은 `j`의 함수로 유지한다.

```text
P'(j)
Q'(j)
B(j)
V(j)
R(j)
A(j)
h(j) 또는 h 후보
k(j, h)
```

직전 identity:

```text
c·2P' = A·V + R
Q' = B·V
```

small gap 변수:

```text
z = 2P' - hQ'
```

같은 입력에서:

```text
c z = (A - c h B)V + R
```

여기서

```text
k = A - c h B
```

이다.

이번 단계는 `A`, `B`, `R`, `V`, `h`, `k`를 같은 `j`에서 연결해야 한다.

---

# 5. 절대 하면 안 되는 단순화

## 5.1 서로 다른 j의 가능성을 합치지 않는다

금지:

```text
j1에서 quotient 가능
j2에서 remainder 가능
j3에서 denominator 가능

→ 동시에 가능할 수 있음
```

이 결론은 너무 느슨하다.

---

## 5.2 c의 modular inverse를 가정하지 않는다

형태:

```text
a x ≡ b (mod m)
```

에서 `a^-1 mod m`이 있다고 가정하지 않는다.

정확한 처리:

```text
g = gcd(a, m)

g ∤ b → 해 없음
g | b → 축약된 합동식
```

여러 합동식을 결합할 때도 서로소를 가정하지 않는다.

generalized CRT 또는 동등한 exact integer 처리를 사용한다.

---

## 5.3 remainder만 보고 결론내리지 않는다

`R`은 전체 `Q'` remainder가 아니다.

기존 exact identity의 의미를 유지한다.

---

## 5.4 interval overlap을 실제 witness로 바꾸지 않는다

interval/coset이 겹친다는 것은:

```text
현재 relaxation으로 배제하지 못함
```

이라는 뜻이다.

다음 뜻이 아니다.

```text
실제 정수 j가 존재함
```

---

# 6. 1차 구현 목표

처음부터 8,076 class 전체를 해결하는 거대한 theorem을 만들지 않는다.

우선 다음을 구현한다.

```text
same_input_filter_v1
```

역할:

1. 기존 class identity 로드
2. `j` 범위 유지
3. 후보 `h` / `k` 조건 유지
4. 같은 `j`에서 조건 교차
5. 불가능하면 class 하한 후보
6. 가능성이 남으면 `unresolved`
7. 실제 입력을 찾았으면 별도 witness 상태

---

# 7. 추천 접근 순서

## Step A — 미해결 8,076 class 유형 분류

먼저 unresolved 이유를 분류한다.

예:

- h range가 너무 넓음
- k range가 너무 넓음
- B(j) 변화가 큼
- remainder dependence가 큼
- positivity enclosure가 약함
- congruence만으로 부족
- class가 너무 큼

이 단계는 survey다.

인증 수치는 바꾸지 않는다.

---

## Step B — 대표 class 선택

각 유형에서 대표 class를 고른다.

목적:

> same-j를 보존하면 실제로 false overlap이 사라지는 유형이 있는지 확인

대표 class는 proof가 아니라 수학 구조를 이해하기 위한 조사다.

---

## Step C — 최소 same-input lemma

처음 lemma는 최대한 작게 만든다.

예시 목표:

```text
필요한 모든 small-gap condition을 만족하는
정수 (j, h)가 존재하지 않음을 증명
```

가능한 방법:

- exact residue intersection
- bounded h enumeration
- exact integer interval
- generalized CRT
- polynomial residue structure

큰 symbolic solver를 바로 만들지 않는다.

---

## Step D — Synthetic Fault Tests

반드시 다음 실패를 검출한다.

1. 다른 j의 조건을 잘못 합침
2. odd h 조건 제거
3. denominator factor 제거
4. remainder 변조
5. multiplier 변조
6. non-coprime congruence를 coprime로 잘못 처리
7. interval overlap을 witness로 승격
8. class domain 일부 누락

---

## Step E — 실제 8,076 class survey

실제 unresolved class에 적용한다.

결과는 최소 세 상태로 나눈다.

```text
whole_class_lower_bound_candidate
actual_small_gap_input
unresolved
```

아직 독립 verifier가 없으면 `candidate`를 바로 certified로 바꾸지 않는다.

---

# 8. Proof Object 최소형

same-input lemma로 새 하한 후보가 생기면 최소 proof object를 만든다.

예:

```yaml
proof_version: c1b1-same-input-v1

target:
  shell: 18
  class_index: 1234

source:
  normalized_class_hash: ...
  identity_hash: ...

claim:
  required_normalized_gap: ...
  proven_lower_bound: ...

method:
  lemma: SAME_INPUT_CORRELATION_V1

payload:
  j_domain: [0, 12345]
  h_constraints: ...
  congruence_constraints: ...
  exclusion_result: ...

status:
  candidate
```

`status: candidate`는 인증이 아니다.

---

# 9. Independent Verifier 최소형

별도 checker는 builder의 내부 판정을 믿지 않는다.

재검사:

- target class가 실제 존재하는가
- source hash가 일치하는가
- exact identity가 맞는가
- j domain이 원래 class와 같은가
- threshold가 정확히 `ceil(M/g)`인가
- odd h 조건이 보존되는가
- non-coprime congruence가 정확히 처리되는가
- claim된 exclusion이 실제로 성립하는가

Verifier 통과 전:

```text
coverage 변경 금지
```

---

# 10. Adaptive refinement는 이번 단계에서 제한적으로만 허용

same-input lemma가 큰 class에서 너무 느슨하면
미해결 class만 sub-class로 나눌 수 있다.

단, 이번 단계에서는 범용 framework를 만들지 않는다.

최소 규칙:

```text
max_depth
max_subclasses
max_total_work
```

를 고정한다.

분할할 때 반드시:

- 전체 원래 class cover
- 누락 0
- endpoint 보존

을 검사한다.

---

# 11. 보간 사용 규칙

이번 단계에서 보간/샘플링은 다음 용도로만 허용한다.

```text
어디를 나눌지 찾기
어떤 class를 먼저 볼지 정하기
```

이 경우 결과는 `survey_only`.

보간을 proof에 사용하려면:

```text
rigorous error enclosure
```

가 반드시 추가되어야 한다.

단순히 몇 점이 안전하다는 이유로 사이를 인증하지 않는다.

---

# 12. 이번 단계에서 바꾸면 안 되는 것

다음은 고정한다.

- ④-4b `NotCertified`
- `11/64 region`
- gap `84`
- `MAX_PRECISION_BITS = 16384`
- 기존 rational-spacing certified family
- 기존 physics
- D_valid
- multi-output contract
- reference executor 의미
- shell/domain inventory

새 proof가 independent verifier를 통과하고 fresh coverage를 재계산하기 전까지
위 값을 올리지 않는다.

---

# 13. 테스트 요구

## 최소 집중 시험

- exact identity round-trip
- threshold `ceil(M/g)`
- same-j synthetic exclusion
- false overlap case
- non-coprime congruence
- generalized CRT
- odd h preservation
- corrupted proof rejection
- class inventory preservation
- source hash binding

## 전체 회귀

기존 repository 표준 LOCAL FULL을 실행한다.

현재 기준선보다 줄면 회귀로 취급한다.

skip을 pass로 세지 않는다.

---

# 14. 실제 성공 수준

## 최소 성공

- same-input correlation을 실제 코드에서 끝까지 유지
- 기존 relaxed 조건보다 엄격한 판정
- fault injection으로 잘못된 분리를 검출
- 실제 반례와 unresolved를 구분

## 좋은 성공

- 큰 8,076 class 중 일부에서 새 전체 class 하한 후보 확보
- proof object 생성
- 독립 verifier 통과

## 큰 성공

- 여러 작은 lemma 조합으로 많은 class cover
- 남은 class만 제한적으로 세분화
- fresh coverage 증가

단, 큰 성공을 위해 현재 scope를 무리하게 넓히지 않는다.

---

# 15. 실패 의미

## 새 하한 0개

same-input lemma가 약한 것일 수 있다.
물리 반례 증거가 아니다.

## actual small-gap input 발견

해당 rational-gap sufficient condition의 실제 반례다.

그러나 이것만으로:

- 전체 impulse rounding failure
- 16384-bit 초과
- 물리식 오류

를 자동으로 의미하지 않는다.

## verifier 실패

proof builder 또는 proof object의 결함 가능성을 먼저 본다.

---

# 16. 구현 순서

```text
1. unresolved 유형 분류
2. representative class exact study
3. minimal same-input lemma
4. synthetic + fault tests
5. real 8,076-class survey
6. proof object minimal schema
7. independent verifier
8. verified class 집계
9. fresh coverage 계산
10. 그 뒤에만 certification 상태 검토
```

---

# 17. 이번 단계에서 하지 않는 것

- 범용 theorem prover
- 대규모 proof warehouse
- 자동 proof synthesis 전체 구현
- machine learning proof search
- A 전체 proof language
- B와 연결
- physics 수정
- precision cap 확대
- brute force만 무작정 확대
- 181 probe replay를 아무 변경 없이 습관적으로 반복
- 새 proof 없이 coverage 수치 변경
- ④ 전체 완료 선언

---

# 18. 구현자에게 전달할 한 문장

> 이번 단계의 목표는 "각 조건이 따로 가능한가?"를 다시 계산하는 것이 아니라, **같은 class의 같은 입력 j에서 quotient·remainder·가변 분모 인수·odd h 조건이 동시에 가능한지 정확히 판정하는 것**이다.
