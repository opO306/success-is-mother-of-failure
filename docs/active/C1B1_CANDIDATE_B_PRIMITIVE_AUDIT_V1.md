# C1-B1 Candidate B 독립 primitive / 합성 감사 V1

2026-10-02. 읽기 전용 독립 reviewer `/root/candidate_b_audit`가 검토하고 짧은 재검산을 새로 실행했다.
**소스 감사 PASS.** 최종 Evidence Closure·LOCAL FULL·trajectory·benchmark 결과는 별도
[승격 보고서](C1B1_CANDIDATE_B_PROMOTION_V1.md)에서 판정한다.

## 범위와 전제

이것은 원본 C1-B1 impulse 프로그램이 반환하는 정수 끝값·raw J·거부의 동일성 감사다.
물리 모델의 soundness, 모든 입력의 cap 내 결정, A 전체 인증 또는 Lean/Coq formal proof가 아니다.
동결된 immutable 매개변수, 정확한 정수/Fraction 입력, M≥128, 양의 순서 있는 radius,
순수 결정론 profile, 정상 Python 실행 및 활성 assertions를 전제로 한다.
실행 중 함수·매개변수 변조, OS 강제 종료, 메모리 부족은 동등성 범위 밖이다.

검사기는 evaluator·candidate·a_numeric를 import하지 않고 Fraction 구간과 별도 rounding/decision을
구현한다. 동결 상수·의도한 수학 명세와 Python int/Fraction/isqrt는 공유하므로 공통 원인 오류를
배제하는 물리 감사는 아니다. 별도 high-M 4건은 checker 없이 REF/A/B/FAST 직접 비교다.

## primitive 검토

### one-sided EXP

원본 enc(xh)의 lower, enc(xl)의 upper만 투영한다. 같은 reduction k에서
Y_lower=(-end)>>k, Y_upper=-(end>>k)는 원본 floor/ceil과 같다.
Taylor lower_term/upper_term 둘 다 유지하고 같은 `upper_term<=1` 종료와
`2*upper_term+2` margin을 사용한다. 출력 누적만 한쪽으로 투영하며 반복 제곱도
하한 floor·상한 ceil의 동일 수열이다. 원본 `LN2_UPPER=6932/10000`, `>=` shortcut과
반환 `(0,1)`을 보존한다. EXP 물리 항·차수·오차 허용값을 바꾸지 않는다.

### interval multiplication

P: al≥0, N: ah≤0, Z: al<0<ah. 아래 raw extrema 뒤 원본의 마지막 floor/ceil shift를 그대로 쓴다.
0 경계에서 겹치는 분기는 동일 값을 준다.

| A | B | lower product | upper product |
|---|---|---|---|
| P | P | al·bl | ah·bh |
| P | N | ah·bl | al·bh |
| P | Z | ah·bl | ah·bh |
| N | P | al·bh | ah·bl |
| N | N | ah·bh | al·bl |
| N | Z | al·bh | al·bl |
| Z | P | al·bh | ah·bh |
| Z | N | ah·bl | al·bl |
| Z | Z | min(al·bh, ah·bl) | max(al·bl, ah·bh) |

### positive denominator division

`0<bl<=bh`를 experimental/production 양쪽 코드에서 검사하고 실패 시 실행을 거부한다.
분자 P는 하한 bh·상한 bl, N은 하한 bl·상한 bh, Z는 둘 다 bl을 쓴다.
정확한 비율의 extrema와 단조 floor/ceil에 따라 원본 여덟 나눗셈과 같다.
현재 RET_B는 모두 양수이고 Dn.lower≥2^M, Dn².lower≥2^M이므로 정상 model 분모에서
새 guard가 거부를 만들지 않는다. FAST model에도 `0<lo<=hi` guard가 있다.

### exact integer inverse powers

p2=x², p4=p2², p[n]=p[n-1]·x의 연산 중 shift/rounding은 없다.
귀납 및 정확한 다항식 검사로 p[n]=x^n, 필요한 지수 `{1,2,4,...,17}`를 확인했다.
최종 `floor(2^(M(n+1))/hi^n), ceil(2^(M(n+1))/lo^n)`는 원본 그대로다.
반올림된 reciprocal interval recurrence는 사용하지 않는다. 역사 반례에서는 dV lower가
-490, upper가 +64 raw 달라졌으며 최종 J가 같아도 중간 endpoint 오류로 거부한다.

### one-isqrt radius

R²·2^(2M)=q+rem/d, l=isqrt(q)에서 하한은 l이다.
상한도 l일 필요충분조건은 rem=0 및 l²=q이며 나머지는 l+1이다.
원본 두 isqrt enclosure와 정확히 같고 radius를 먼저 profile로 반올림하지 않는다.

## 합성과 저장소 연결

원본에서 V-only 두 누적을 제거해도 EXP·dV·inv1·상태를 건드리지 않는 것을 live AST로 검사했다.
B는 inverse table 대체 이외의 살아 있는 model AST가 A와 같다.
public impulse는 V 반환값 unpack 제거 이외 원본 AST와 같으므로 동일 R² guard,
M별 dV/inv1, 실제 G=mul(-dV,inv1), 정확 dr·dt, profile decision 및 refinement 순서를 보존한다.
0 dt도 domain 검사 뒤 처리한다.

production `_impulse_model_R_fast`는 B와 같고 명시적 radius guard만 추가한다.
production primitives AST도 감사한 experimental primitives와 같다.
`step_fast.__code__ is REF.step.__code__`; 사용하는 globals는 impulse 이외 모두 같은 객체다.
원본 step은 원본 impulse를 계속 사용하며 generic model·energy·potential은 원본 경로다.

## 새로 실행한 독립 재검산

- 곱셈 13,068, 양수 division 2,970, scale 792.
- 독립 checker EXP 648, inverse 160, radius 160, rounding 575.
- reference→A→B 및 B→production FAST live AST 검사.
- EXP lower ±1, sqrt upper -1, inverse power 오염, sign branch, division 방향,
  dV 항 삭제 및 역사 rounded reciprocal 반례: 실행 가능한 8개 모두 검출.
- actual model/G/J/decision trace 5개 입력에서 REF/FAST/checker 일치.
- 실제 paired refusal 4개에서 예외·원인·걸음·실패 후 상태 일치.

| 입력 | 실제 결과 | 원인 |
|---|---|---|
| domain | PhysicsDomainExceeded | physics_domain_exceeded |
| impulse overflow | VMHalt | overflow |
| stored momentum overflow | ExecutorLimitExceeded | overflow in from_exact; cause VMHalt(overflow) |
| stored position overflow | ExecutorLimitExceeded | overflow in add; cause VMHalt(overflow) |

마지막 두 원인은 `_kick`의 mom.from_exact와 `_drift`의 pos.add에서 발생하며 기존 `_limit`가 감싼다.
reviewer가 처음 exception type만 보고 제기한 우려는 해당 cause·호출 경로 확인 후 철회했다.

## 증거 orchestration 재감사

stage command·check schema·필수 상세 output·반복/입력/profile/정밀도별 coverage를 검사한다.
빈 payload, 누락·중복, stale/mixed binding, 바뀐 output/input/source, nonzero rc는 PASS가 될 수 없다.
별도 stage도 검사 집합에 포함하며 verify의 옛 search/main summary 경로는 제거했다.
이 보장은 로컬 provenance/integrity 범위이며 모든 artifact와 해시를 함께 위조하는 공격에 대한
암호학적 실행 증명은 아니다. 실행 중 assertions가 비활성화되는 환경은 감사 범위 밖이다.

검토 bytes SHA256은 `experiments/verified_superoptimizer_c1b1/audit_acceptance.json`에 보존한다.
그 목록은 계산 전후 동일했다. 같은 bytes를 관리 worktree로 옮겨도 소스 감사 판정은 유지된다.
이후 실행 판정은 감사 기록 자체의 PASS를 재사용하지 않고 새 run의 실제 stage 결과로 계산한다.

관리 worktree의 원본 c1b1_two_atom.py(608 CRLF)·exp.py(100 CRLF)는 root LF와 raw hash가
달랐다. reviewer가 splitlines·전체 AST·Git HEAD blob 동일성을 독립 재검사해 PASS를 유지했다.
다른 검토 파일 19개는 bytes 동일이다. 당시 감사 JSON은 실제 worktree CRLF SHA를 고정했으며,
수정 전 JSON에 결합된 promotion_v1은 최종 승격 증거에서 제외한다.

최초 FULL v2는 Git 밖의 과거 배포 묶음/O-1 raw data 누락으로 두 시험이 실패했다.
관련 봉인 manifest가 열거한 원본 bytes와 artifact만 복원했고 기존 source 차이는 newline뿐이었다.
복원 후 reviewer가 21개 SHA가 최초 목록과 모두 동일함을 확인하고 primitive/AST/합성을 새로 검사해 PASS했다.
현재 감사 기록은 최초 LF 해시에 다시 결합된다. v2 실패는 보존하고 fresh v3를 최종 실행으로 사용한다.
191개 복원 metadata SHA: f87dd5163eb726655c6bf3aa31c29345a47c40f9e1d25a20548a34e9e852bccf.
복사/전수 hash 확인과 관련 두 시험 재실행은 구현자의 작업이며 reviewer가 이를 자기 실행으로 보고하지 않았다.
