# Pilot 1: 동일 M의 enclosure endpoint 보존 논증

**역사 Pilot 논증 원문.** 아래 commit·입력 수·경로·당시 판정은 Pilot 시점의 기록이다.
현재 승격 판정과 source binding은 [독립 감사](../../docs/active/C1B1_CANDIDATE_B_PRIMITIVE_AUDIT_V1.md)와
[최종 보고서](../../docs/active/C1B1_CANDIDATE_B_PROMOTION_V1.md)를 본다.

## 1. 증명할 명제와 범위

기준은 `71ab2b30be6e846b42994f3560f0642e305fd6a5`의 C1-B1 프로그램이다. 네 원본 파일의 전체 Git blob 해시는 `snapshot_manifest.json`과 재현 드라이버에 고정되어 있다. 종료 시 확인한 `f7c2c8dc2f46bc510b8399aadb3b690ef8fef313`에서도 네 blob이 동일하다.

`I = (lo, hi)`는 실제 구간 `[lo/2^M, hi/2^M]`를 뜻한다. 원본의 `_model_R(I,M,ret)`가 `(V,D,U)`를 반환할 때 후보 A/B는 **정수 쌍까지 정확히 같은 `(D,U)`**를 반환한다는 명제를 다룬다. 단지 같은 실수 함수를 enclosure한다거나 결과가 비슷하다는 명제가 아니다.

전제는 다음과 같다.

* 고정된 매개변수, 정수 `M >= 128`, 양의 순서 있는 거리 구간 `0 < lo <= hi`이다. 실제 public `impulse` 정밀도는 128부터 16384까지의 두 배 수열이다.
* Python 정수와 Fraction은 수학적으로 정확하게 계산된다. 원본의 함수나 매개변수를 실행 중 변경하지 않는다. 메모리 부족·운영체제 강제 종료 같은 외부 자원 실패는 알고리즘 결과 동등성의 대상이 아니다.
* EXP hook을 사용할 때에는 같은 순서의 같은 인수를 받는 결정론적인 enclosure 함수이다. 원본과 후보가 hook에 전달하는 인수와 호출 순서도 검사했다.
* public `impulse`에는 정확한 유리수 dr와 dt_kick을 사용하고 원본의 `R2 >= R_MIN2` 검사를 유지한다. 이 커널 검사로 임의 초기 상태가 세계의 D_valid 전체에 속한다고 주장하지 않는다.

이 문서는 수학적 유도와 원본/후보 코드의 연결을 제시한다. AST 비교와 일부 다항식 항등식은 기계 검사했다. 전체 Python 프로그램을 Lean/Coq 등의 증명기에 넣어 얻은 정리는 아니다.

## 2. 후보 A: V 누적은 D와 U에 영향을 주지 않는다

원본 `_model_R`의 V 이름 참조는 초기화, 두 누적식의 읽기/쓰기, 반환뿐이다. 삭제한 식은 다음 두 위치다.

```python
V = _add(V, _mul(E, P, M))
V = _add(V, _neg(_scale(_mul(D, power(-2 * k), M), c)))
```

첫 위치는 short 항 6개, 둘째 위치는 long 항 11개에서 실행된다. `_add`, `_mul`, `_scale`, `_neg`, `power`는 읽기 전용 값 연산이다. 삭제한 식에는 EXP 호출, 상태 갱신, dV 갱신이 없다. 따라서 V 누적만 제거하면 나머지 변수는 원본과 동일하다. 실제 `verify.structural_checks`는 V 참조 개수를 확인하고, V를 제외한 `_model_R` AST가 후보 A와 동일한지 비교한다. 후보 A의 `_model` 제곱근 경로도 원본과 같다.

**남기는 것:** short polynomial P는 `dP - alpha*P`에 필요하다. retardation g도 D와 그 힘 항에 필요하다. 이들은 에너지와 연관된 이름이더라도 삭제하지 않았다. 물리 성분을 생략하는 최적화가 아니다.

## 3. 후보 B의 추가 정수 변환

### 3.1 부호로 곱셈 극값 선택

원본 구간 곱은 `al*bl`, `al*bh`, `ah*bl`, `ah*bh` 네 정수의 최솟값과 최댓값을 선택한다. 양쪽 구간이 0을 가로지르는 경우를 제외하면 부호로 그 두 모서리를 정할 수 있다. 예를 들어 양수·양수는 `(al*bl, ah*bh)`, 음수·양수는 `(al*bh, ah*bl)`이다. 두 구간 모두 0을 가로지르면 원본과 같은 두 음수 후보의 min 및 두 양수 후보의 max를 사용한다.

선택한 정수 극값이 원본과 같으므로 마지막 `low >> M`, `-((-high) >> M)`도 같다. 반올림 위치를 이동하거나 두 번의 구간 곱을 하나로 합치지 않는다. 경계 0을 포함하는 경우에도 공식이 겹쳐 같은 값이다.

### 3.2 양수 분모 나눗셈

분모 구간이 `0 < bl <= bh`일 때, 원본의 네 모서리 floor와 네 모서리 ceil 중 극값은 분자 부호에 따라 다음 두 분모만 필요하다.

| 분자 구간 | 하한에 쓸 분모 | 상한에 쓸 분모 |
|---|---|---|
| `al >= 0` | bh | bl |
| `ah <= 0` | bl | bh |
| `al < 0 < ah` | bl | bl |

floor와 ceil은 단조 함수이므로 먼저 정확한 비율의 극값을 선택하고 floor/ceil을 적용한 결과가 원본과 같다. 정수 나눗셈 8회를 2회로 줄인다. exact rational 상수 배율도 상수 부호로 원본의 동일한 두 끝값을 선택한다.

### 3.3 반올림하지 않은 정수 거듭제곱 공유

원본 역수 구간은 각 n에 대해 아래와 같다.

```text
floor(2^(M*(n+1)) / hi^n), ceil(2^(M*(n+1)) / lo^n)
```

후보는 **raw 정수 lo, hi의 거듭제곱**을 정수 곱셈으로 재사용한다. `p2=x*x`, `p4=p2*p2`, `p[n]=p[n-1]*x`이다. 이 계산 중에는 grid shift나 반올림이 전혀 없다. 귀납적으로 모든 `p[n]=x^n`이다. 필요한 n 각각에 대해 SymPy의 정확한 다항식 항등식 검사도 통과했다.

필요한 역수 지수는 `{1,2,4,5,...,17}`이다. 3은 결과에 사용되지 않는다. 마지막 floor/ceil division은 원본 공식을 그대로 사용한다. 따라서 역수 구간이 같다. **반올림된 1/R 구간을 반복 곱하는 다른 후보와는 다르다.** 그 후보의 실패 반례는 `counterexamples.json`에 있다.

### 3.4 제곱근 두 번을 한 번으로

`s = R2 * 2^(2M) = q + rem/d`, `0 <= rem < d`, `l = isqrt(q)`라고 하자. 하한은 l이다. s가 정확한 정수 제곱일 필요충분조건은 `rem=0 and l*l=q`이다. 그때만 상한도 l이고, 나머지에서는 상한이 l+1이다.

후보 `_radius`는 이 판정을 쓴다. 원본의 floor 대상·ceil 대상에 대한 두 isqrt와 같은 바닥/천장 제곱근 구간이다. R 자체를 profile 값으로 먼저 반올림하지 않는다.

## 4. EXP: 같은 bound의 필요한 방향만 계산

원본 `_exp_neg((xl,xh),M)`은 `enc(xh)[0]`과 `enc(xl)[1]`를 사용한다. 두 enc는 각각 양 끝을 모두 계산하므로 반환받고 버리는 출력이 있다.

### 4.1 range reduction 보존

원본과 같은 `k = max(0, end.bit_length()-M+1)+8`를 사용한다. `x=-end/2^M`이므로 Taylor 입력 grid는 정확히 `-end/2^k`이다.

```text
Y_lower = floor(-end / 2^k) = (-end) >> k
Y_upper = ceil(-end / 2^k)  = -(end >> k)
```

이 값은 원본이 Fraction을 만들고 나서 계산한 정수와 같다.

### 4.2 Taylor의 출력 투영

원본 `_taylor`는 같은 lower_term/upper_term 수열로 s_lo와 s_hi를 동시에 누적한다. 각각의 누적값은 상대 누적값을 읽지 않는다. 후보 `_taylor_side`는 필요한 누적값만 유지하되 **두 term bound, 종료 조건 `upper_term <= 1`, 여유항 `2*upper_term+2`를 모두 유지한다.** 반복 차수에 대한 귀납으로 원본의 해당 누적값과 같다.

### 4.3 반복 제곱 투영

원본 EXP의 하한 반복 제곱은 이전 하한만, 상한 반복 제곱은 이전 상한만 사용한다. 후보는 선택한 방향에 대해 같은 k번의 floor 또는 ceil 제곱을 적용한다. 하한의 초기 `max(lo,0)`도 유지한다. 따라서 각각 원본 enc의 선택된 출력과 같다.

### 4.4 먼 거리 shortcut 보존

`xl * LN2_UPPER.denominator >= (M*LN2_UPPER.numerator) << M`의 조건, 상수 `6932/10000`, 반환 `(0,1)`을 원본과 동일하게 유지한다. 반환 `(0,0)`은 금지되며 mutation test에서 검출했다. 물리 항을 삭제하거나 새 거리 cutoff를 둔 것이 아니다.

따라서 short 6개와 long 3개의 물리 EXP는 여전히 9개다. shortcut이 없는 모델 평가에서 Taylor 호출 수가 36에서 18로 줄고, 필요 없는 방향의 제곱 수열도 제거된다. 이 변환은 Taylor 차수나 오차 허용값을 낮추는 변환이 아니다.

## 5. `_model_R`에서 최종 J까지의 합성

후보 A의 살아 있는 연산 순서는 원본과 같다. 후보 B도 역수 생성 위치 이외의 살아 있는 `_model_R` AST가 A와 같고, 바뀐 primitive는 위와 같이 동일한 정수 끝값을 반환한다. 같은 입력에서 연산 순서대로 귀납하면 dV와 inv1이 같다. B의 sqrt 구간도 같으므로 `_model(R2,M,ret)`에도 결과가 이어진다.

public impulse에서 다음 경로를 유지한다.

```text
같은 R2 domain guard
→ 같은 M의 (dV,inv1)
→ 같은 G = interval_mul(-dV,inv1,M)
→ 같은 정확한 유리수 c=dr[k]*dt_kick
→ 같은 c*G의 유리수 끝값
→ 같은 profile.from_exact 및 _decide
→ 같은 J raw 또는 같은 수치적 거부
```

A/B의 impulse AST는 원본에서 버려지는 V 반환값의 unpack만 제거한 형태다. 영 성분 처리, M별 cache, 성분 처리 순서, M 증가 수열과 cap은 같다. 따라서 순수하고 결정론적인 동일 profile에서는 모든 성공 결과와 refinement 순서가 같고, overflow·domain refusal·cap 미결정도 같은 경로를 따른다. 특히 `dt_kick=0`이어도 domain 검사 전에 반환하지 않는다.

**전체 domain에서 cap 내 해결된다는 정리는 주장하지 않는다.** 원본이 해결하지 못하는 입력을 후보가 마음대로 해결된 것으로 선언하지 않는다는 것이 동등성의 일부다.

## 6. 독립 검사기의 역할과 한계

`checker.py`는 원본 evaluator·numeric primitive·후보를 import하지 않는다. 구간을 Fraction 객체로 나타내고 각 연산 뒤 같은 grid로 내림/올림하는 방식으로 endpoint를 다시 산출한다. EXP/Taylor도 독립 전사했고 FX·Binary64·Carry의 rounding과 decision도 별도 구현했다. 178입력×4형식의 J raw뿐 아니라 실제 refinement에서 생긴 2,500개 J 구간 쌍과 결정 순서를 검사했다.

공유되는 것은 동결 상수, 의도한 수학적 알고리즘 명세, Python 정수/Fraction/isqrt 실행 기반이다. 따라서 이것은 원본 프로그램과 독립 구현 간 검사이지, Lang 물리 모델 자체의 새 soundness 감사나 독립 팀의 검토가 아니다. 최고 M=16384의 별도 4건은 원본/A/B 직접 비교이며 Fraction 검사기를 전체 모델에 재실행한 384건과 구분한다.

## 7. 판정

* `PROVED_EXPRESSION_EQUIVALENCE`: 위 정수·구간 연산 항등식과 noninterference 논증에 근거한 프로그램 변환 수준의 동등성.
* `CANONICAL_EQUIVALENCE_CANDIDATE`: 동일-M endpoint로부터 J raw 동등성까지 이어지는 증명 구조가 있다.
* `PRODUCTION APPROVED`: **아니다.** 전체 저장소 통합 검사, 별도 검토, 실제 실행기의 입력·자원 조건 확인은 이번 부분 snapshot 실험 밖이다.
* 표본 전수 일치는 위 논증을 대신하지 않는다. `counterexamples.json`의 탈락 후보는 최종 J가 같은 첫 입력에서도 중간 endpoint가 달라져 거부되었다.
