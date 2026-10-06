# RESOURCE EVOLUTION PILOT V1 — 구현자 인계서
## 코어·병렬화·자원 압박·조건학습·리스크 성향을 이용한 진화형 계산기 실험

**작성일:** 2026-10-06  
**상태:** DESIGN / IMPLEMENTATION NOT STARTED / NOT CERTIFIED / NO PRODUCTION PROMOTION  
**대상:** Exact Expression 계열의 진화형 계산기 후속 연구  
**이번 범위:** T0~T10  
**후속 범위:** T11~T13은 설계만 보존하고 이번 단계에서는 구현하지 않음

---

# 0. 이 문서의 목적

이 문서는 지금까지 진행한 정밀도 정책(A1), algebra evaluator 전이(A2-T), 동등 수식 재작성 탐색(A3) 다음에 수행할 **Resource Evolution Pilot**의 구현·실험 범위를 고정한다.

이번 단계의 질문은 다음과 같다.

> **동일한 정확성 계약을 유지하면서, 사용할 수 있는 CPU 코어·시간·메모리·병렬 배치·탐색 성향을 바꾸면 계산기는 어떤 실행 전략을 선택해야 가장 싸고 안정적으로 답을 얻는가?**

추가로 다음을 실험한다.

- 자원 부족을 반복해서 경험하면 그 환경에 맞게 실행 전략을 바꿀 수 있는가?
- 자원 부족을 예고하는 중립 신호를 학습해 선제적으로 전략을 전환할 수 있는가?
- 공격적인 계산 전략과 보수적인 계산 전략은 어떤 자원 환경에서 각각 유리한가?
- 일부 요청에서만 성공하는 빠른 후보를 exact verifier + fallback 구조 안에서 안전하게 사용할 수 있는가?

이번 단계는 하드웨어를 손상시키거나 실제 CPU 온도를 강제로 올리는 실험이 아니다.

여기서 말하는 **“배고픔”, “자원 압박”, “열량 부족”은 계산기에 허용한 연산 자원이 줄어드는 것**을 뜻한다.

예:

- 사용 가능한 CPU 코어 수
- CPU-seconds 예산
- wall-time 예산
- RAM 예산
- 후보 실행 횟수
- speculative work 예산

전압 조작, undervolting, overclocking, thermal throttling 유도, electromigration/aging 실험은 이번 범위 밖이다.

---

# 1. 현재 기준점

아래는 사용자 제공 완료 보고를 기준으로 한 현재 계보이며, 실제 착수 시 Git에서 다시 확인해야 한다.

## 1.1 완료된 단계

### A1 — Precision Policy Pilot
- original evaluator 위에서 P0/P1/P2/P3 비교.
- 정수 단위 작업 정밀도 사용.
- P3는 학습 기반 시작 p 추천.
- P2는 학습 없는 adaptive fallback 역할.
- 최소 p와 service cost를 분리.

보고된 결과 commit:
- `942bcd4`
- checker 강화 commit `0e49576`

### A2-T — Algebra evaluator × frozen precision policy
- algebra evaluator에 A1의 P0/P1/P2/P3를 재학습 없이 전달.
- frozen P2/P3가 깨지지 않음을 확인.
- algebra의 주된 이득은 필요한 p 감소보다 same-p 계산 비용 감소에서 나옴.
- formal certification은 없음.

보고된 결과 commit:
- `1c6557c`

### A3 — Equivalent Rewrite / Reverse Rewrite Pilot
- 힘 함수 내부의 다항식 평가 블록을 대상으로 rewrite 규칙 탐색.
- 23개 후보를 생성.
- R1, R2 조합은 screen에서 interval-width 손실 없이 same-p 비용 감소.
- R3/R4/R5 계열은 일부 연산을 줄여도 interval width를 넓혀 장기 service 비용을 악화시킬 수 있음.
- 봉인 규칙이 선택한 FAST(R1+R2+R5)는 전체 service에서 확정 승자가 아니었음.
- 수식 재작성만 더 깊게 파는 것의 한계효용이 드러남.

사용자 제공 보고 기준 결과 commit:
- protocol `53ff815`
- code `b9e2612`
- result `7cba21d`

**주의:** 위 commit과 branch 상태는 이 문서를 작성하면서 현재 Git에서 독립 확인한 것이 아니다. 실제 구현자는 착수 전에 반드시 현재 repository/worktree에서 재확인한다.

---

# 2. 이번 단계의 절대 규칙

## 2.1 VERIFIED 결과 정확성은 거래 대상이 아니다

이번 연구에서 진화 가능한 것은 다음이다.

- evaluator 선택
- 시작 precision
- precision 탐색 순서
- worker/core 수
- 병렬화 위치
- speculative candidate 수
- cache 사용
- fallback 정책
- 자원 부족 시 탐색 폭
- 공격형/보수형 risk profile
- 조건신호에 대한 실행 전략

다음은 진화 대상이 아니다.

- 물리 법칙
- 물리 상수
- 정확한 입력 의미
- domain 규칙
- rounding 규칙
- Exact Expression의 정확 상태 의미
- 최종 acceptance rule
- verifier가 인정하는 정답의 기준

**정확성 90%와 속도 2배를 교환하지 않는다.**

공격적인 계산기는 오답을 감수하는 계산기가 아니다.

공격형이 감수할 수 있는 리스크는 다음뿐이다.

- 싼 후보가 실패해 버린 CPU가 생김
- 낮은 p에서 시작했다가 retry가 생김
- speculative branch를 실행했지만 채택되지 않음
- latency tail이 길어짐
- 자원 예산을 더 빨리 소모함

최종 결과는 independent verifier를 통과한 `VERIFIED_RESULT`만 반환한다.

---

# 3. 핵심 아키텍처

```text
                Fixed ProblemContract
                        │
                        ▼
               Resource Environment
        core / RAM / CPU / wall / cue
                        │
                        ▼
             Execution Strategy Selector
          evaluator / p / workers / risk
                        │
                        ▼
               Isolated Candidate Run
                        │
                        ▼
               Independent Verifier
                  │              │
             VERIFIED         NOT VERIFIED
                  │              │
                  ▼              ▼
             결과 채택       fallback / refuse
                  │
                  ▼
           Cost & Resource Ledger
                  │
                  ▼
         Policy / Conditioning Memory
```

가장 중요한 원칙:

> **selector는 무엇을 먼저 시도할지 고를 수 있지만, 무엇이 정답인지 고를 수 없다.**

---

# 4. 기본 evaluator / policy 후보

## 4.1 기준 evaluator

### E0 — original
역사적 baseline.

### E1 — algebra
현재 Resource Pilot의 주 baseline evaluator.

이유:
- A2-T에서 기존 precision policy와 결합 가능함을 확인.
- 현재까지의 검증 자료가 가장 많음.
- A3의 FAST보다 service 동작이 안정적.

### E2 — R1+R2
A3에서 screen상 다음이 관측된 보조 후보.

- zero-coefficient folding
- reciprocal/power reuse
- interval-width 손실이 관측되지 않은 범위 존재
- same-p 연산 비용 감소 후보

단, **전체 service 순이득은 아직 확인되지 않았으므로 baseline으로 승격하지 않는다.**

이번 Resource Pilot에서 보조 evaluator로 사용할 수 있으나, E1과 같은 correctness gate를 다시 통과해야 한다.

### 제외
A3의 FAST `R1+R2+R5`를 기본 후보로 쓰지 않는다.

이유:
- same-p 비용은 줄일 수 있어도 interval width 증가가 precision/retry 비용을 증가시킴.
- service 전체에서 확정적인 승자가 아니었음.

---

## 4.2 precision policy

이번 단계에서는 A1/A2-T에서 이미 사용한 정책을 우선 재사용한다.

- P0: 기존 coarse grid
- P2: 학습 없는 adaptive precision
- P3: 기존 frozen predictor + P2 fallback

Resource Pilot의 기본 service path는 우선:

```text
E1 algebra
+
P3 first proposal
+
P2 fallback
```

으로 한다.

새 precision 학습기를 이번 단계에서 동시에 튜닝하지 않는다.

A2-R은 별도 후속 후보이며 이번 Resource Pilot과 섞지 않는다.

---

# 5. 측정값

모든 성능 실험은 최소 다음을 분리해서 기록한다.

## 5.1 정확성/완결성
- verifier status
- decided raw
- interval endpoints
- domain status
- completed steps
- requested horizon
- fallback status
- RESULT_CONFLICT 여부
- INVALID_EVIDENCE 여부

## 5.2 latency
- wall time
- p50
- p95
- p99

단, p95/p99를 주장할 반복 수가 충분하지 않으면 계산하지 않거나 `INSUFFICIENT_SAMPLES`로 남긴다.

## 5.3 총 계산량
- process CPU
- child CPU
- total CPU-seconds
- 가능하면 core-seconds
- worker별 CPU

## 5.4 메모리
- peak RSS
- candidate memory
- cache memory
- verifier memory
- evidence/record memory

## 5.5 탐색 비용
- attempts
- retry count
- speculative candidate count
- speculative wasted CPU
- unused candidate CPU
- fallback CPU

## 5.6 검증 비용
- verify CPU
- verify wall
- evidence record cost

## 5.7 에너지
실제 신뢰할 수 있는 에너지 측정 방법이 준비된 경우만 별도 기록한다.

CPU 온도는 energy proxy로 사용하지 않는다.

---

# 6. T0 — Baseline / Regression Seal

## 목적
Resource Evolution을 시작하기 전에 정확성 바닥과 기준 실행을 봉인한다.

## 입력
A1/A2-T에서 사용한 대표 short/long requests 중 실행 비용이 과하지 않은 subset.

## 확인
- 1 core 제한에서도 기존 결과와 같은 VERIFIED raw.
- affinity를 바꿔도 물리 의미가 변하지 않음.
- 동일 plan 반복 시 결정성이 유지됨.
- worker 수 변경이 arithmetic order를 바꾸지 않음.

## 필수 구현 원칙
병렬화를 위해 연산 순서를 임의로 바꾸지 않는다.

가능하면:
- pair 계산은 독립 실행
- 합산은 canonical fixed order
- precision retry 순서도 plan에 기록
- schedule만 병렬화하고 산술 graph는 유지

## 완료 조건
- baseline evidence pass
- frozen source hash 확인
- no result conflict
- resource accounting 동작
- affinity/worker 제한이 실제 적용됐다는 증거

---

# 7. T1 — Core Scaling Test

## 질문

> 같은 정확한 계산을 1/2/3/4/6 core 환경에서 실행하면 wall time과 총 CPU work가 어떻게 변하는가?

실제 machine에 해당 core 수가 없으면 지원 가능한 physical-core set으로 protocol을 조정한다.

## 독립 변수
`core_budget`

권고 후보:
- 1
- 2
- 3
- 4
- 6

## 고정
- evaluator
- precision policy
- input
- request
- cache 조건
- verifier
- arithmetic order

## 우선 baseline
`algebra + frozen P3→P2`

## 보조 후보
`R1+R2 + frozen P3→P2`

## 측정
- wall
- total CPU
- speedup
- parallel efficiency
- peak RSS
- verifier cost
- result equality

## 해석 예

```text
1 core: 100 wall-s / 100 CPU-s
2 core: 58 wall-s / 112 CPU-s
6 core: 40 wall-s / 210 CPU-s
```

이 경우:
- latency는 6 core가 최고
- total resource efficiency는 1~2 core가 나을 수 있음

하나의 “speed” 숫자로 합치지 않는다.

## 실패 조건
- 결과 불일치
- hidden extra cores 사용
- arithmetic order가 바뀌어 계약 위반
- process spawn 비용이 본 계산보다 큼
- CPU 감소 없이 wall만 우연히 흔들림

---

# 8. T2 — Parallel Placement Test

## 질문

> 코어를 어디에 배치해야 실제 이득이 생기는가?

## 전략 후보

### S0 — Serial
완전 직렬 기준선.

### S1 — Independent Request Parallel
서로 독립적인 request/scenario를 병렬 실행.

정확성 위험이 가장 작고 구현도 단순하므로 첫 병렬 baseline.

### S2 — Speculative Precision Parallel
서로 다른 p 후보를 동시에 실행.

예:
```text
p=320
p=352
p=384
```

먼저 VERIFIED 되는 경로를 채택.

주의:
- latency를 줄일 수 있음
- 버리는 CPU가 늘어날 수 있음
- exact answer 기준은 그대로

### S3 — Evaluator Candidate Parallel
E1 algebra와 E2 R1+R2 등 verifier-approved evaluator 후보를 동시에 시도.

### S4 — Pair Force Parallel
한 step 내부의 atom-pair force 계산을 병렬화.

주의:
- 현재 2/3 atom 문제에서는 pair 수가 매우 작음.
- overhead가 이득보다 클 가능성이 큼.
- 실패도 유효한 결과.

### S5 — Execution / Verification Pipeline
여러 독립 요청이 있을 때 이전 요청을 verifier가 검사하는 동안 다음 요청 candidate 실행.

하나의 요청에서 verifier를 생략하거나 acceptance 전에 다음 world state를 확정하는 구조는 금지.

## 완료 조건
각 placement별:
- accuracy pass
- wall/CPU/RAM
- overhead
- scaling
- 어느 입력 규모부터 이득인지 bracket

---

# 9. T3 — Resource Pressure Curve

## 개념

“배고픔”을 물리적 온도가 아니라 resource budget으로 정의한다.

## 질문

> 자원을 점점 줄이면 효율이 좋아지는 구간과 계산이 붕괴하는 구간은 어디인가?

## Environment tier

실제 숫자는 실행 전 protocol에 봉인한다.

예시 구조:

```text
H0  풍족
H1  약한 압박
H2  중간 압박
H3  높은 압박
H4  극한 압박
```

각 tier는 다음의 조합으로 정의한다.

- core budget
- CPU budget
- wall budget
- RAM budget
- speculative candidate budget

## 금지
“pressure=0.7” 같은 숫자만 저장하고 실제 자원 조건을 숨기지 않는다.

항상 실제 budget도 함께 기록한다.

## 측정
- VERIFIED completion rate
- RESOURCE_REFUSED
- retries
- wall
- CPU
- memory
- strategy changes
- wasted work

## 핵심
압력이 너무 약하면 비효율 탐색이 계속될 수 있고,
압력이 너무 강하면 모든 후보가 RESOURCE_REFUSED로 끝날 수 있다.

중간 압력이 최적이라는 결론을 미리 넣지 않는다.

---

# 10. T4 — Resource Adaptation Test

## 질문

> 계산기가 현재 resource budget을 보고 계산 전략을 바꾸면 실제 이득이 있는가?

## 가변 형질
- worker count
- evaluator
- start p
- number of speculative candidates
- cache policy
- exploration budget
- fallback reserve
- risk profile

## control
자원 환경을 보지 못하고 항상 같은 plan을 사용하는 fixed policy.

## adaptive
환경을 읽어 approved plan 중 하나를 선택.

## 금지
- evaluation answer를 미리 보고 plan 선택
- future minimum-p table 사용
- verifier result를 plan 입력으로 선사용
- test-set leakage

## 성공
정확성 동일 + total cost 또는 latency의 조건부 개선.

---

# 11. T5 — Neutral Cue Test

파블로프식 조건학습의 사전 대조군.

## 목적

중립 신호 자체가 원래 아무 의미가 없음을 확인한다.

## Cue
예: `CUE_A`

이 cue는 계산 세계의 물리 입력이 아니다.
executor 외부의 resource-environment metadata이다.

## 실험

```text
CUE_A
→ resource change 없음
```

을 반복.

## 기대
계산 전략이 의미 있게 변하지 않아야 한다.

## 실패
중립 cue만으로:
- worker 수 변화
- p 변화
- risk profile 변화
- evaluator 변화

가 지속적으로 생기면 conditioning 이전부터 bias가 존재함.

---

# 12. T6 — Conditioning Test

## 질문

> 중립 신호가 반복적으로 자원 부족을 예고하면, 실제 자원 제한 전에 계산기가 선제적으로 저자원 전략을 선택하는가?

## pairing

```text
CUE_A
↓
고정 delay
↓
resource pressure 상승
```

반복.

## test

```text
CUE_A
↓
아직 resource는 풍족
```

이 상태에서 plan 변화를 확인.

## 허용되는 conditioned response
- worker 수 감소/재배치
- exploration 감소
- start p margin 조정
- conservative/aggressive profile 전환
- cache 우선
- speculative count 변경

## 금지
- 정확성 기준 하향
- domain 검사 생략
- verifier 생략
- physics 변경

## 측정
- cue→plan reaction rate
- 실제 shortage에서의 이득
- false positive cost
- no-shortage 상황에서의 불필요한 손해

---

# 13. T7 — Extinction / Reversal Test

조건학습이 단순한 영구 플래그인지 검사한다.

## T7-A Extinction

조건화 후:

```text
CUE_A
→ 더 이상 resource pressure 없음
```

을 반복.

### 질문
불필요한 conditioned response가 점차 사라지는가?

### 실패
cue를 한 번 배운 뒤 환경이 바뀌어도 영구히 같은 plan을 고집.

---

## T7-B Reversal

환경을 바꾼다.

```text
CUE_A → 아무 일 없음
CUE_B → resource pressure 상승
```

### 질문
새 관계를 학습하고 오래된 관계를 버리거나 약화시키는가?

### 측정
- adaptation delay
- old-cue false response
- new-cue correct response
- transition cost

---

# 14. T8 — Aggressive vs Conservative Risk Profile

## 절대 규칙

두 profile 모두:

```text
VERIFIED final correctness = 100%
```

공격성은 오답 허용이 아니다.

---

## Aggressive

예:
- 더 낮은 start p
- 빠른 신규 evaluator 우선
- speculative execution 허용
- 여러 후보 동시 실행 가능
- 낮은 safety margin
- 실패 시 빠른 fallback

### 장점 후보
성공하면 latency 크게 감소.

### 손해
- retry
- wasted CPU
- 높은 tail latency
- budget starvation 위험

---

## Conservative

예:
- 높은-confidence evaluator
- 넉넉한 p
- 적은 후보
- 높은 first-try success 목표
- fallback reserve 크게 유지

### 장점
- latency 분산 작음
- retry 적음
- 예측 가능성

### 손해
- 쉬운 요청에도 과잉 p
- unused safety margin
- 평균 latency 증가 가능

---

## 측정
- verified accuracy
- mean latency
- p50/p95/p99
- CPU-seconds
- fallback rate
- wasted speculative CPU
- RAM
- RESOURCE_REFUSED
- BUDGET_STARVATION
- verifier cost

## 중요한 해석
평균만 보고 공격형을 승자로 만들지 않는다.

예:
```text
9회 매우 빠름
1회 매우 느림
```

이라면 tail cost를 별도로 보고한다.

---

# 15. T9 — Speculative Candidate + Exact Verifier

사용자가 제안한 “80%짜리 후보도 다른 위치에서 100% 시스템의 부품이 될 수 있는가?”를 직접 다룬다.

## 세 종류를 구분

### Type A — Domain-limited exact candidate
```text
지원 영역 80%
그 영역에서는 exact/certified
나머지 20%는 REFUSE
```

좋은 후보가 될 수 있다.

### Type B — Unchecked 80%-correct candidate
```text
전체 입력에서 80% 맞음
20% 오답
오답 검출 불가
```

**금지.**

world result 후보로 사용할 수 없다.

### Type C — Speculative candidate with sound verifier
```text
빠른 후보 생성
↓
independent exact/sound verifier
↓
통과 → 채택
실패/불확실 → fallback
```

사용 가능.

단, verifier가 후보보다 비싸면 성능 이득이 없을 수 있음.

---

## T9의 핵심 지표
- candidate hit rate
- verifier reject rate
- false accept
- fallback rate
- speculative wasted CPU
- verify cost
- total cost

### 절대 acceptance condition
`false accept = 0`

관측 표본에서 0이라는 것과 수학적으로 불가능함이 증명됐다는 것은 구분한다.

formal guarantee가 없으면 증거 수준을 명시한다.

---

# 16. T10 — Pressure × Risk Interaction

## 질문

> 자원이 부족할수록 공격형이 유리한가, 아니면 retry 여유가 줄기 때문에 보수형이 유리한가?

결론을 미리 넣지 않는다.

## 첫 screening

모든 pressure tier × 모든 profile을 처음부터 전수 실행하지 말고,
정보 가치가 높은 대표 3수준으로 시작한다.

예:
- low pressure
- medium pressure
- high pressure

각각:
- aggressive
- conservative

총 6칸.

교차점이 보이면 인접 pressure level을 추가한다.

## 결과표 예

| Pressure | Aggressive | Conservative | Winner/Tradeoff |
|---|---:|---:|---|
| Low |  |  |  |
| Medium |  |  |  |
| High |  |  |  |

비교:
- wall
- total CPU
- tail latency
- fallback
- resource refusal
- wasted work

---

# 17. 이번 단계의 실행 순서

```text
T0 baseline seal
↓
T1 core scaling
↓
T2 parallel placement
↓
T3 resource pressure
↓
T4 resource adaptation
↓
T5 neutral cue
↓
T6 conditioning
↓
T7 extinction / reversal
↓
T8 aggressive vs conservative
↓
T9 speculative candidate + verifier
↓
T10 pressure × risk interaction
↓
STOP / REPORT
```

**T10 뒤 자동으로 다음 세대로 진행하지 않는다.**

---

# 18. 후속 단계 — 이번에는 구현하지 않음

## T11 — Joint Genome

후보가 다음 형질을 함께 가짐.

```text
CandidateGenome
- evaluator
- precision_policy
- start_p
- worker_count
- parallel_strategy
- risk_profile
- cache_policy
- fallback_policy
- resource_response
```

환경:

```text
Environment
- core_budget
- RAM_budget
- wall_budget
- CPU_budget
- resource_pressure
- conditioned_cue
```

목표:
단일 전역 승자가 아니라 환경별 champion을 찾음.

예:
- 1-core champion
- 2-core champion
- latency champion
- low-CPU champion
- low-memory champion

---

## T12 — Simple Selector

신경망 전에:
- lookup/table
- rule
- linear regression
- decision tree

를 비교.

복잡한 모델이 단순 모델보다 실제로 이겨야 다음으로 감.

---

## T13 — Neural Selector

T12가 부족할 때만.

신경망이 계산 값을 직접 대체하지 않는다.

역할:
```text
입력 특징 + resource environment
→ 어떤 verified execution strategy를 먼저 시도할지 추천
```

신경망의 잘못된 선택은 비용 증가로 끝나야 하며 오답으로 이어지면 안 된다.

---

# 19. 기록 스키마 제안

## ResourceContract

- contract_id
- problem_contract_hash
- allowed_core_set
- RAM_budget
- wall_budget
- CPU_budget
- candidate_budget
- affinity_mode
- energy_measurement_mode
- protocol_hash

## ExecutionPlan

- evaluator_id
- precision_policy_id
- start_p
- worker_count
- parallel_strategy
- risk_profile
- speculative_count
- cache_policy
- fallback_plan

## ConditioningRecord

- cue_id
- cue_timestamp/order
- paired_pressure
- delay
- response_plan
- extinction_count
- reversal_generation

## ResourceEvidence

- request_id
- plan_id
- actual_affinity
- requested_p sequence
- actual_p sequence
- completed_steps
- raw result
- exact endpoints
- verifier status
- wall
- parent CPU
- child CPU
- total CPU
- peak RSS
- retry CPU
- speculative wasted CPU
- verify CPU
- record CPU
- refusal reason

## RiskEvidence

- risk_profile
- first_try_success
- fallback_count
- wasted_work
- tail_latency
- budget_starvation
- result_status

---

# 20. 비용 함수

정확성은 비용함수에 넣지 않는다.

먼저 correctness hard gate.

그 다음:

```text
C_total =
    C_execute
  + C_retry
  + C_speculative_waste
  + C_verify
  + C_convert
  + C_memory_manage
  + C_record
  + C_recover
```

latency와 total CPU는 하나로 합치지 않고 별도 축으로 보존한다.

필요하면 Pareto frontier를 사용한다.

예:
- wall은 더 작지만 CPU는 더 큼
- CPU는 작지만 tail latency가 큼

이런 후보를 하나의 가중치로 억지로 지우지 않는다.

---

# 21. Git / Evidence 규칙

실제 구현 착수 시 먼저 확인:

- HEAD
- branch
- origin/master 또는 기준 branch
- dirty/untracked
- A1/A2-T/A3 commits 존재 여부
- frozen directories diff
- 현재 checker version

각 단계는 가능하면 별도 commit으로 분리한다.

권고:

```text
protocol
→ implementation
→ tests
→ source seal
→ campaign
→ evidence/checker
→ results document
```

금지:
- 기존 raw result 덮어쓰기
- 과거 evidence 수정
- 누락 파일을 재측정하고 원본인 척 저장
- push/merge/rebase 자동 실행
- 다른 session/process 종료
- 실행 뒤 결과를 보고 protocol 수정 후 같은 campaign으로 포장

checker 결함을 발견하면:
1. 반례 보존
2. 영향 범위 기록
3. 별도 commit
4. raw evidence 재판정
5. 결과 생성 코드와 checker 수정 분리

---

# 22. 측정 공정성

- 같은 request끼리 비교
- 같은 evaluator/version binding
- candidate와 baseline의 cold/warm 조건 대칭
- run order 고정 또는 counterbalance
- 외부 부하 기록
- affinity 실제 적용 확인
- worker/child process 종료 확인
- incomplete file은 INVALID 처리
- 1회 long run의 작은 차이를 승리로 확정하지 않음
- short run은 timer resolution보다 충분히 길게 하거나 반복을 늘림

특히 multi-core에서:
- parent process time만 보고 total CPU라고 부르지 않는다.
- child CPU를 포함한다.

---

# 23. 최소 반례 / fault injection

각 기능은 정상 성공 사례 전에 작은 반례를 가진다.

## Core
- affinity가 무시됨
- worker가 core budget보다 많이 생성됨
- child가 종료되지 않음

## Parallel
- 결과 순서 바뀜
- canonical reduction 누락
- duplicate candidate를 success처럼 이중 계산

## Pressure
- 너무 작은 budget → RESOURCE_REFUSED
- fallback reserve를 탐색이 모두 소비 → BUDGET_STARVATION

## Conditioning
- neutral cue만으로 반응
- cue가 바뀌어도 옛 cue 고집
- cue 없이 미래 pressure를 미리 아는 leakage

## Risk
- aggressive candidate 실패 후 wrong result 채택
- conservative가 항상 high-p를 골라 resource budget 초과
- p95/p99 악화가 평균에 숨음

## Speculation
- false accept
- verifier missing
- verifier timeout
- candidate와 verifier가 동일한 buggy derived flag 공유

---

# 24. 이번 단계에서 하지 않을 것

- undervolting
- overclocking
- CPU/GPU 열화
- 의도적 hardware fault
- thermal throttling 유도
- 정확성 90%를 최종 답으로 허용
- physics / constants / domain / rounding 변경
- validator 자체 진화
- unrestricted source-code self-modification
- 무제한 neural architecture search
- GPU/Tensor Core 통합
- RNS/LNS/Posit 동시 추가
- A2-R 동시 실행
- T11~T13 자동 진입

---

# 25. 완료 기준

Resource Evolution V1(T0~T10)은 다음을 모두 만족해야 완료다.

## Correctness
- planned evidence complete
- no silent missing
- no undetected wrong result
- no result conflict
- verifier scope 명시
- unsupported/formal-unproven 범위 공개

## Resource
- actual core affinity 기록
- total CPU accounting
- wall/CPU 분리
- RAM 기록
- retry/speculative waste 기록

## Learning
- neutral cue control 존재
- conditioning test 존재
- extinction/reversal 존재
- future/test leakage 검사

## Risk
- aggressive/conservative 모두 100% final verified
- fallback cost 기록
- tail latency 기록 가능한 범위에서 보고
- false accept 0 requirement

## Reporting
- 승리 사례
- 손해 사례
- resource refused
- budget starvation
- measurement noise
- untested 영역
- simpler policy가 이긴 사례

## Operations
- commits 기록
- source seal
- working tree clean
- push/merge 없음
- 잔류 child process 없음

---

# 26. 최종 보고서에서 반드시 답할 질문

1. 몇 core가 wall time 기준으로 가장 빨랐는가?
2. 몇 core가 total CPU 기준으로 가장 효율적이었는가?
3. 병렬화는 어느 위치에서 실제 이득이 있었는가?
4. pair-level parallelism은 현재 작은 원자계에서 가치가 있었는가?
5. 적당한 resource pressure가 실제 효율을 높였는가?
6. 어느 pressure부터 RESOURCE_REFUSED가 급증했는가?
7. resource-aware adaptation이 fixed policy보다 이겼는가?
8. neutral cue가 conditioning 전에는 정말 중립이었는가?
9. conditioned response가 실제 shortage에서 도움이 됐는가?
10. false cue 비용은 얼마였는가?
11. extinction과 reversal이 일어났는가?
12. aggressive와 conservative 중 어느 환경에서 누가 이겼는가?
13. 공격형의 평균 이득이 tail latency 손해보다 컸는가?
14. speculative candidate의 hit rate와 verifier 비용은 얼마였는가?
15. false accept가 있었는가?
16. “80% 후보”가 전체 100% exact system의 안전한 부품이 될 수 있었는가?
17. resource pressure가 높을수록 공격적 전략이 유리했는가, 보수적 전략이 유리했는가?
18. R1+R2 evaluator는 resource 환경에서도 algebra보다 순이득이 있었는가?
19. 이번 단계에서 신경망이 실제로 필요한 근거가 생겼는가?
20. 다음 단계 T11을 시작할 정보 가치가 충분한가?

---

# 27. 구현자에게 주는 마지막 요약

이번 단계의 목표는 “모든 코어를 사용해서 빨리 만들기”가 아니다.

목표는:

> **정확한 같은 답을 유지하면서, 자원 환경에 따라 가장 적절한 계산 계획을 선택하고, 그 선택이 실제 비용을 줄이는지 증거로 확인하는 것**이다.

또한 “배고픔”과 “공격성”은 비유일 뿐이다.

실제 구현에서는 다음으로 치환한다.

```text
배고픔
→ resource budget / pressure

공격성
→ 실패·retry·speculative waste를 감수하고 낮은 expected latency를 노리는 execution policy

보수성
→ 높은 first-try success와 낮은 tail risk를 우선하는 execution policy

파블로프 조건화
→ resource shortage를 예고하는 neutral cue와 execution-plan 선택 사이의 학습
```

그리고 모든 계층 바깥에는 변하지 않는 규칙이 있다.

```text
             EXACT / SOUND VERIFIER
                      │
             통과한 결과만 채택
                      │
             성능·자원 경쟁 시작
```

**정확성은 투자금이 아니다. 정확성은 경기장 입장 조건이다.**
