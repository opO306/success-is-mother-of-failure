# A Proof Composition Roadmap V1
## 장기 Proof System을 현재 C1-B1에서 안전하게 키우는 단계 설계

**문서 상태:** PROPOSAL / 장기 로드맵  
**현재 Gate를 대신하지 않음:** 현재 활성 작업은 C1-B1 outer formal bound ④다.  
**우선순위:** 현재 ④ 문제 해결 > 범용화 > 자동화  
**금지:** 로드맵의 미래 단계를 현재 구현 완료로 취급하지 않는다.

**2026-09-28 착수 기록:** [최소 구현 결과](../active/C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md)에 same-input 필터와 최소 proof object/checker를 기록한다.
실제 큰 class의 symbolic 하한은 0개라 Phase 1의 수학 목표는 미완료다.
최소 proof object/checker가 존재한다는 사실로 Phase 2/3 전체 또는 이후 창고·범용화·자동화를 완료 처리하지 않는다.

---

# 1. 로드맵 목적

전체 proof architecture를 한 번에 구현하면 현재 C1-B1을 해결하는 대신 새로운 프레임워크 프로젝트가 생긴다.

따라서 다음 원칙을 따른다.

> 지금 필요한 기능만 만든다.  
> 실제로 효과가 확인된 구조만 다음 단계로 승격한다.

각 Phase는 앞 단계가 실제 문제에서 유용하다는 증거가 생긴 뒤 진행한다.

---

# 2. 전체 단계

```text
Phase 0  현재 상태 고정
Phase 1  Same-input correlation
Phase 2  Minimal proof object
Phase 3  Independent verifier
Phase 4  Adaptive refinement
Phase 5  Multi-lemma composition
Phase 6  Proof warehouse
Phase 7  Proof dependency graph
Phase 8  Automated proof search
Phase 9  Rigorous interpolation/enclosure
Phase 10 A 전체 인증 계층으로 일반화
```

---

# Phase 0 — 현재 상태 고정

## 목적

새 구조를 만들기 전에 현재 인증 상태가 무엇인지 고정한다.

기준:

- ④-4b `NotCertified`
- `11/64 region`
- gap `84`
- precision cap `16384`
- shell 15~18 전체 class `14,271`
- 하한 확보 `6,195`
- 미해결 `8,076`
- 큰 class 신규 하한 `0`
- 실제 small-gap 반례 `0`

## 성공 조건

- 기존 fixture/source hash 고정
- 기존 checker/physics/D_valid 변경 없음
- 현재 LOCAL FULL 기준 보존

---

# Phase 1 — Same-input Correlation

## 목적

현재 가장 직접적인 수학적 병목을 해결한다.

현재 문제:

```text
A 조건은 어떤 j에서 가능
B 조건은 다른 j에서 가능
C 조건은 또 다른 j에서 가능

느슨한 분석:
A/B/C 모두 가능 → unresolved
```

목표:

```text
같은 j에서 A+B+C가 동시에 가능한가?
```

추적 대상:

- quotient
- remainder
- variable denominator factor
- odd h
- 필요한 congruence
- normalized threshold

## 구현 범위

- 정확한 same-j identity 유지
- non-coprime congruence 처리
- generalized CRT 또는 동등한 정확 정수 처리
- false overlap을 제거하는 synthetic test
- 실제 8,076 unresolved class에 survey 적용

## 성공 조건

최소:
- same-input correlation이 코드에서 실제 보존됨
- 기존 relaxed 방식보다 강한 판정
- fault injection에서 상관관계 파괴를 검출

좋은 결과:
- 일부 큰 class의 새 하한 확보

---

# Phase 2 — Minimal Proof Object

## 목적

"왜 이 class가 안전한지"를 구조화한다.

최소 schema:

```text
proof_id
target
lemma_id
preconditions
dependencies
claim
source_hashes
```

## 하지 않을 것

- 범용 proof language
- 범용 theorem prover
- 복잡한 database

## 성공 조건

- 같은 proof object를 다른 프로세스에서 재검증 가능
- 원자료 변경 시 stale로 거부

---

# Phase 3 — Independent Verifier

## 목적

proof 생성 코드와 판정 코드를 분리한다.

Verifier는:

- builder의 status를 믿지 않음
- proof object의 전제를 재검사
- source hash 확인
- identity 재구성
- target domain 재확인
- claim 검증

## 필수 fault injection

- remainder 변조
- divisor 변조
- multiplier 변조
- odd condition 제거
- class id 교체
- source hash 교체
- proof dependency 교체
- threshold 교체

모두 거부되어야 한다.

---

# Phase 4 — Adaptive Refinement

## 목적

큰 class에서만 필요한 경우 부분 분할한다.

흐름:

```text
class
→ proof attempt
→ 성공: 종료
→ 실패: sub-class
→ 다시 proof attempt
```

## 제한

- 최대 depth
- 최대 sub-class 수
- 총 proof cost budget
- 같은 unresolved 유형 반복 감지

## 성공 조건

분할 전에는 미해결이던 class 일부가
분할 후에는 완전 coverage로 닫힘.

---

# Phase 5 — Multi-Lemma Composition

## 목적

서로 다른 작은 lemma를 조합한다.

예:

```text
positive denominator
+
odd h range
+
same-input congruence
+
remainder bound
=
gap exclusion
```

## 필수 조건

- lemma 전제 명시
- dependency DAG
- 적용 domain 명시
- 결론 범위 명시
- 같은 사실을 서로 순환 보증 금지

---

# Phase 6 — Proof Warehouse

> 설계 명세: [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md) (설계 전용·미구현). 읽기 전용 v0는 shell 16 인증서와 LOCAL FULL 확정 뒤 별도 Gate에서만 착수한다(2026-09-28 설계자 판정 Q7·Q8).

## 목적

proof가 많아졌을 때 찾고 재사용한다.

최소 기능:

- proof_id 조회
- target 조회
- dependency 조회
- source/version 조회
- stale proof 표시

## 하지 않을 것

- warehouse 내부 status를 최종 인증으로 사용
- verifier 없이 coverage 증가

---

# Phase 7 — Proof Dependency Graph

## 목적

수백~수천 proof의 의존성을 관리한다.

필수 검사:

- cycle
- stale dependency
- incompatible version
- unknown lemma
- missing source
- duplicate contradictory claim

---

# Phase 8 — Automated Proof Search

## 목적

프로그램이 lemma 조합을 자동 탐색한다.

입력:

```text
target claim
available lemma set
proof cost model
```

출력:

```text
proof candidate
```

최종 판정:

```text
independent verifier
```

## search 전략 후보

- bounded breadth-first
- cost-guided search
- dependency-aware search
- domain-specialized rule selection

학습/AI는 이 단계에서 후보 생성기로 사용 가능하지만,
검증 권한은 주지 않는다.

---

# Phase 9 — Rigorous Interpolation / Enclosure

## 목적

연속 또는 큰 이산 영역을 더 싸게 감싼다.

허용되는 정식 proof 구조:

```text
approximation
+
rigorous error bound
+
whole-domain enclosure
+
decision-boundary separation
```

단순 샘플링이나 보간은 계속 `survey_only`.

---

# Phase 10 — A 전체 인증 계층으로 일반화

## 전제

C1-B1에서 다음이 실제로 검증된 뒤만 진행한다.

- proof object가 유용함
- verifier가 독립적임
- adaptive refinement가 class 폭발 없이 작동
- multi-lemma composition이 실제 coverage를 올림

그 뒤 다음 영역에 적용을 검토한다.

- collision
- force
- energy
- time integration
- native/reference equivalence
- multi-resolution exactness

---

# 3. 단계별 Gate

각 Phase는 다음 질문을 통과해야 한다.

## 왜 필요한가?

현재 실제 병목을 해결하는가?

## 무엇을 검증하는가?

정확히 어떤 claim을 다루는가?

## 실패하면 무엇을 의미하는가?

물리 반례인가, proof 방법 실패인가, 구현 오류인가?

## 기존 계약을 바꾸는가?

바꾸면 별도 설계자 승인이 필요하다.

## 더 작은 방법이 있는가?

있으면 더 작은 방법부터 한다.

---

# 4. 현재 우선순위

현재는 다음만 진행한다.

```text
Phase 1
↓
Phase 2 최소형
↓
Phase 3 최소형
```

즉:

> same-input lemma  
> + 최소 proof object  
> + 독립 verifier

여기까지.

Phase 4 이후는 현재 구현 결과를 보고 판단한다.

---

# 5. 중단 조건

다음 상황에서는 framework 확장을 중단한다.

- ④ 해결보다 framework 코드가 더 커짐
- 미해결 class가 줄지 않음
- proof object가 사람이 읽기만 편하고 검증에는 도움 안 됨
- verifier가 builder와 사실상 같은 구현이 됨
- class subdivision만 계속 늘어남
- 현재 Gate보다 장기 구조 구현이 우선되기 시작함

이 경우 다시 현재 수학 의무로 돌아간다.

---

# 6. 문서 상태 규칙

| 문서 종류 | 위치 |
|---|---|
| 현재 실제 구현/검증 | `docs/active/` |
| 장기 설계 | `docs/proposals/` |
| 공통 검증 원칙 | 충분히 검증된 뒤 `docs/reference/` 후보 |
| 완료·동결 계약 | 별도 승인 후 `docs/frozen/` |

폴더 이동 자체가 승인이나 동결을 의미하지 않는다.

---

# 7. 한 줄 요약

> 현재 문제를 해결하는 데 필요한 최소 proof system부터 만들고, 실제로 효과가 확인될 때만 다음 기능을 추가한다.
