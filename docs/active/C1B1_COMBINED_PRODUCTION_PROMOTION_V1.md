# C1-B1 Combined production promotion

2026-10-03. Fresh campaign and all promotion gates PASS.
Status: PRODUCTION FAST-PATH CANDIDATE / OPT-IN APPLIED. Default remains Candidate B `fast`; Combined is opt-in.

## Implemented behavior and preserved references

Only Combined is connected to production. `a_reference/c1b1_combined_arithmetic.py`
contains raw prepared drift and raw kick; no research A/B/C selector is imported.
`c1b1_runtime` provides `reference`, existing/default `fast`, and `fast_combined`.
The actual `tools/c1b1_replay_benchmark.py` producer calls `bind(run,mode=...)` once
and repeatedly calls its step. Single-call `runtime.step(run,mode='fast_combined')`
is also supported, but repeat execution should retain the prepared executor.

```python
executor = runtime.bind(run, mode='fast_combined')
executor.step()
# For a separate comparison Run: bind(other_run, mode='reference' or 'fast').
```

Slow REF, original Fraction drift/kick, Candidate B impulse/step and differential
path, generic `_model_R`, profile arithmetic, checker/proof remain unchanged.
Each executor uses the original step code object and private globals. Combined
changes only drift/kick bindings; Candidate B supplies impulse. Guard, stored-domain
check, refusal, cap16384 and final commit order stay original. No world metadata is
added by binding. Unsupported arithmetic profiles and retired drift-v1 keep original
Fraction arithmetic; explicit reference mode stays reachable without retry.

The prepared ratio represents exactly p*dt/m using Python integers. It rounds the
displacement at the original position, then retains Fraction where exact endpoint
is consumed by the segment guard. This reduces repeated exact work while preserving
Fraction's role at the guard. Momentum kick uses the same grid's raw sum/difference
and original range refusal, without intermediate Fraction conversion.

Prepared constants are bound to exact Run identity, species, masses, dt, profile
objects/fields and drift rule. Changes are refused before state mutation. Construct
a fresh executor for an intentionally different Run/specification.

## Independent audit and concept alignment

[Independent audit](C1B1_COMBINED_PROMOTION_AUDIT_V1.md) separately compared production
against original Fraction: ratio660/rounding660/drift2310/kick605. It found and resolved
Run-retarget binding and evidence-completeness defects. Final review had no open
Critical/Important findings; the minor source-map consistency assertion was added
before sealing. The later CLI text-limit repair was implementation verification,
not a fresh whole-change independent review; production arithmetic was unchanged.

The requested concept is exact arithmetic performed more cheaply, without replacing
the world law or its reference. This matches the code's integer identity and preserved
original integration order. No A/B/C standalone production mode exists. Default fast
does not become Combined. This work creates no new CONFIRMED history and does not
replace existing endpoint proof or approved replay obligations.

## Fresh source/input and differential

Base master41605579606cabe6a1ee161a5364e689fa11fbc1; Pilot2 base5e409c0adae165f837bc2186f5cd40e707ccb228.
Promotion branch `codex/c1b1-pilot2-combined-promotion`, local worktree inherited from
Pilot2. Root master and old branch commits are preserved; push and mainline merge absent.

Fresh run55f358a0-1b95-4619-a874-c5dbb3f36e03,
source1d68c8c3a366680a4eb4f0546e945565f306de46ffb7c0c9686de4dee079f1e8,
input6f8a2265acbea23e10a1b3ed4eaad636484cca91dcad12a54e3baa58835399c2.
`runs/c1b1_combined_promotion_v1/campaign_textfix_v1/` is append-only stage evidence.
Source/input binding is rechecked; stage outputs require complete artifact inventory.

Six existing trajectories complete with1564/6456/26285/5597/2454/13489 steps, total55845.
All three production modes match initial raw, impulse raw, rounded displacement raw,
exact endpoints, kicks, exact segment input/minimum, stored-domain result, every stored
state, final state, overflow/refusal and precision STOP. Four original refusals and
actual cap16384 synthetic stress agree. Nine additional adversarial states exercise
reversed/zero/mirrored momentum, cached raw extrema, invalid bool/Fraction raw,
exact-only segment rejection and preserved retired-v1. Truncated diagnostic trajectories
end at declared caps and are not counted as completed scattering trajectories.

Actual drift outputs provide the recorded stored-position difference and exact endpoint.
Checker independently verifies displacement with original Fraction displacement, kick,
drift, guard and impulse functions, and checks ordered def-use continuity and final commit.
Stored trace facts are integration evidence, not a replacement for endpoint arguments.

Supplemental actual producer executes seven preserved inputs79087 steps per mode,
237261 across three modes, all raw/state/J equal. These ran under the first campaign's
whole source hash558672d4345e6c2f47f8110bd1f9923960139f6606479b09e3af5cbffcea8500.
The production/runtime/reference source parts match final campaign byte-for-byte, but
whole hashes differ after harness text-limit/test repair. This supplemental evidence
is kept with its original binding, not relabeled as the new run. Its concurrent clocks
are functional diagnostics, not performance measurements.

## Preserved failures and boundaries

First actual-producer probe stopped before execution because seven named historical
witness assets were absent in the isolated worktree. Exactly those seven files were
copied from root and SHA-verified; `producer_assets.json` records this environmental repair.

First sealed campaign completed55845 normal steps and four refusal cases, then parsing
the precision stress dt4908digits hit Python's4300-digit text conversion limit. It remains
INCOMPLETE with its original source/input/witnesses. New campaign uses the same CLI text
setting as prior Pilot2; arithmetic cap16384 remains unchanged. RED/GREEN parsing regression
and final related190 tests pass. Old witnesses are not reused as the new campaign's output.



## 최종 gate 판정

| Gate | 결과 | 근거 |
|---|---|---|
| Exact arithmetic audit | PASS | 독립 ratio660 / rounding660 / drift2310 / kick605, component224 |
| Rounding / exact guard | PASS | 변위 반올림·exact endpoint 분리, 선분 침범 반례와 trace 변조 검출 |
| Overflow / refusal / precision STOP | PASS | 네 기존 거부·실제 cap16384 STOP·추가 악성9건, 거부 시 Run 불변 |
| Three-way trajectory differential | PASS | 정상6개55845step, 매 impulse/변위/endpoint/저장 상태 일치 |
| Post-integration LOCAL FULL | PASS | 3903 PASS / FAIL0 / ERROR0 / strict XFAIL1 / 실제 SKIP0 |
| Measured trajectory CPU reduction | PASS | 같은 캠페인 B37.53125초 → Combined33.43750초,10.9076% 감소 |
| Bigint scaling observation | PASS(측정 범위) | 정상335070성분132/139/180bit, 고정 분모·누적 rational chain 없음 |
| Source/input/stage closure | PASS | exact catalog, all artifacts, original Fraction/impulse 재계산, pstats 재도출 |

FULL pytest742.24초, 프로세스743.8203744초. 정확한3904 item 목록과 알려진 binary64 absolute-position strict xfail1건을 확인했다. cp949 컴파일러 출력 해독 경고25건은 미해결이다. 공식 AGENTS 기준선 숫자를 갱신하지 않았다.

## 같은 캠페인의 성능

Ryzen5 5600,6 physical cores/12 logical threads, 측정 worker1, logicalCPU11 고정, Python3.12.7. Drift/kick 및 각6입력의 step1000회 warm-up 후3회 반복, mode 순서 회전/반전, CPU와 wall 중앙값을 저장했다. 초기 준비/admission/binding/hash는 타이머 밖이며, trajectory는 동일한 상태 저장과 R20 종료 검사를 타이머 안에 포함한다. 원래 producer의 I/O/verifier를 포함한 end-to-end latency는 이번 수치의 범위가 아니다.

| CPU workload | slow REF(s) | Candidate B(s) | Combined(s) | Combined vs B | Combined vs REF |
|---|---:|---:|---:|---:|---:|
| 원자 drift30000회 | 0.828125 | 0.828125 | 0.546875 | 1.514x | 1.514x |
| 두 원자 kick30000회 | 0.765625 | 0.750000 | 0.171875 | 4.364x | 4.455x |
| 연속 step1000회 | 0.906250 | 0.609375 | 0.531250 | 1.147x | 1.706x |
| 6 trajectory55845step 합계 | 52.953125 | 37.531250 | 33.437500 | 1.122x | 1.584x |

| Wall workload | REF(s) | B(s) | Combined(s) |
|---|---:|---:|---:|
| 원자 drift30000회 | 0.861747 | 0.868673 | 0.544372 |
| 두 원자 kick30000회 | 0.764740 | 0.748859 | 0.163085 |
| 연속 step1000회 | 0.904583 | 0.606333 | 0.539196 |
| 6 trajectory55845step 합계 | 53.631466 | 37.873172 | 33.740819 |

81개 측정 행의 동일 output/state fingerprints, 반복×mode×workload/trajectory 전체 표, 호출 수, 양수·유한 clock 및 중앙값 재계산이 통과했다. 이전 캠페인 speedup을 곱하지 않았으며 누적1.583645x는 이번 REF와 Combined 중앙값의 직접 비율이다. 이전 Pilot2 step1.086x/trajectory1.128x와 이번1.147x/1.122x를 각각 보존한다.3회 표본과 Windows CPU clock의15.625ms 단위 변동으로 짧은 micro/step 수치의 정밀도는 제한된다. REF와 B의 drift/kick은 같은 함수이며 그 두 열의 작은 비용 차이는 측정 변동이다.

## Post-Combined production CPU Top10

Production-only profile은 검증된6개 step 수만큼 실제 `runtime.bind(...,fast_combined).step()`을 실행했다. R20 연구용 종료 검사·상태 저장·producer I/O·verifier·초기 준비를 제외한다. 모든 final fingerprint가 differential과 같다. process_time cProfile 계측이며 총 selfCPU187.8125초에는 profiler overhead가 있으므로 앞의33.4375초 benchmark와 직접 비교하지 않는다. 아래는 exclusive selfCPU 비율이며 cumulative time을 더하지 않는다.

| 계산/함수 | 전체 self CPU | 호출 수 | self 비용/호출(µs) | 의미 | 중복/재사용 검토 | self 비용0일 때 전체 상한 |
|---|---:|---:|---:|---|---|---:|
| _impulse_model_R_fast | 11.9468% | 56,474 | 397.3067 | Candidate B exact 정수 구간 derivative | 현재 radius powers/inverse는 한 호출 안에서 공유, const cache 존재. 계수곱 c*i 재생성 있음; 반복 인수율 미측정 | 1.1357x |
| Fraction.forward | 7.0466% | 5,990,734 | 2.2091 | 원래 exact Fraction 연산 dispatch | 다양한 산술 호출의 공통 래퍼. 같은 인수 중복률 미측정 | 1.0758x |
| Fraction._mul | 5.7488% | 3,980,278 | 2.7126 | 원래 exact Fraction 곱셈/약분 | 정확한 곱과 약분. 반복 피연산자율 미측정 | 1.0610x |
| _scale | 5.1913% | 5,082,660 | 1.9183 | Candidate B exact outward 정수 scale | 계수 numerator/denominator를 반복 읽음. 같은 interval 재사용율 미측정 | 1.0548x |
| Fraction.__new__ | 4.8087% | 4,867,919 | 1.8553 | 원래 Fraction exact 구성/정규화 | 동일 raw/profile 변환이 반복되는 지점 있음; 일반 재사용율 미측정 | 1.0505x |
| _taylor_side | 4.4260% | 938,650 | 8.8558 | 원래 REF Taylor 출력과 같은 정수 enclosure | upper/lower side 별 점화식, 종료/방향 rounding 보존 의무. 동일 Y/M 비율 미측정 | 1.0463x |
| <built-in method builtins.isinstance> | 4.2845% | 10,379,230 | 0.7753 | 원래 타입/산술 dispatch predicate | 공통 검사가 여러 연산에 호출됨; 안전하게 생략 가능한 비율 미측정 | 1.0448x |
| <built-in method math.gcd> | 4.1764% | 12,615,567 | 0.6218 | 원래 exact 정규화/교차 약분 | 공통 분모/피연산자 일부 있음; 실제 동일 gcd 인수율 미측정 | 1.0436x |
| Fraction._from_coprime_ints | 3.8270% | 6,102,424 | 1.1778 | 원래 exact Fraction 구성, 약분 전제 | 이미 서로소인 결과 생성 경로. __new__와 별도 allocation route | 1.0398x |
| object.__new__ | 2.9285% | 10,970,343 | 0.5014 | Python object allocation | Fraction 두 생성 경로의 객체 구성 비용 포함; 별도 math 연산이 아님 | 1.0302x |

상한은 계측된 selfCPU share f에서1/(1-f)이며 그 함수의 모든 self 비용을0으로 만들 수 있다고 둔 이상적 값이다. 수치의 계측 overhead와 실제 최적화의 잔여 비용 때문에 실제 전체 speedup을 보장하지 않는다. 중복 인수의 실제 반복률을 계측하지 않았으므로 함수 호출 수를 곧 중복 계산 횟수로 해석하지 않는다. 다음 최적화 대상은 아직 선정하지 않았다.

### 요청한 Fraction/gcd/raw primitive 상세

| production-only 함수 | 호출 | self CPU(s) | cumulative CPU(s) |
|---|---:|---:|---:|
| kick | 111,690 | 1.234375 | 6.562500 |
| _rounded | 335,070 | 0.765625 | 3.062500 |
| Fraction._mul | 3,980,278 | 10.796875 | 22.187500 |
| Fraction.forward | 5,990,734 | 13.234375 | 61.890625 |
| drift | 111,690 | 1.562500 | 18.031250 |
| Fraction.__new__ | 4,867,919 | 9.031250 | 13.109375 |
| _ratio | 335,070 | 0.484375 | 0.671875 |
| Fraction._from_coprime_ints | 6,102,424 | 7.187500 | 10.375000 |
| prepare_drift | 111,690 | 1.000000 | 6.781250 |
| <built-in method math.gcd> | 12,615,567 | 7.843750 | 7.843750 |

`_ratio`는 정수 곱셈과 raw 유효성 검사를 포함하고 `_rounded`는 shift/division/rounding/range check를 포함한다. 개별 곱셈·나눗셈의 순수 비용은 아래 microkernel에서 따로 측정했다. 이 새 helper들은 Top10에 들어오지 않았다. 가장 큰 단일 selfCPU 계산은 기존 FAST impulse derivative11.9468%이며 exact Fraction 계산도 계속 큰 비중을 차지한다.

R20 종료 검사 포함의 비교용 세 모드 profile도 별도로 보존했다. 동일 scope의 B→Combined Fraction 생성 두 경로 합계17057490→12366510(27.5010% 감소), gcd19825340→14381182(27.4606% 감소)다. __new__만을 전체 Fraction allocation count로 부르지 않는다. Production-only Combined의 두 생성 경로는4867919+6102424=10970343회이며 다른 scope의 count와 섞어 비율을 만들지 않는다.

## Bigint와 비용

실제 정상6개 trajectory335070성분에서 N최대132bit/D139bit/shifted N180bit. D는 해당 Run의 dt/species/profile로 고정되고 이전 rational 결과를 다음 denominator로 누적하지 않는다. 원래 stored momentum 폭과 immutable 준비 계수의 곱으로 N 폭이 제한된다. 악성 cached maximum 입력의143/139/191bit와 exact guard synthetic180/181/180bit도 별도로 기록했다.

| microkernel(1e6회×3,1000 warm-up) | production(ns/op CPU median) | large-denominator stress(ns/op) |
|---|---:|---:|
| Fraction_ratio | 859.375 | 765.625 |
| gcd | 421.875 | 296.875 |
| integer_multiplication | 62.500 | 109.375 |
| integer_round_division | 390.625 | 500.000 |
| original_exact | 2281.250 | 2125.000 |

Production micro 입력은FX96.48/FX96.80,dt40,Ar40 mass,mom.hi//32이며 N/D/scaled138/139/186bit다. Stress는FX192.110/FX192.150,dt7/11,mass1/(2^127-1),316/154/426bit다. Stress의 position raw는 범위를 넘으므로 division primitive만 계측한 별도 diagnostic이며 정상 world trajectory가 아니다. Integer pair storage88/88bytes(production),116/116bytes(stress), reduced/unreduced 비교에서 증가 없음. 반복1000회 traced peak/live memory는 누적 allocation count가 아니며 현재 live0으로 복귀했다. 정상 및 이 stress에서 누적 bigint 폭발/전체 trajectory 역전은 관측되지 않았다. 더 큰 profile/DT/분모의 보편적인 performance를 보장하지 않는다.

## 최종 상태와 한계

Combined만 PRODUCTION FAST-PATH CANDIDATE. `fast_combined` opt-in production 연결 완료, 기본 `fast` 및 reference 유지. A/B/C 개별 production 승격 없음. Mainline merge/push 없음; root master4160557과 Pilot2 branch5e409c0 보존, promotion은 별도 로컬 브랜치다.

미해결: 컴파일러 cp949 warnings25,3회 표본/짧은 clock의 변동, 초기 준비·producer I/O·verifier를 포함한 총 latency, 더 큰 profile/DT/분모 확장성, 정식 증명·전체 domain·무한 궤적·A-EV/native J·새 runtime/source 조합의 replay 승인. 새 CONFIRMED history0. 원래 endpoint proof와 이번 trajectory integration evidence는 별도다.

추가 production-only driver는 첫 direct-file 실행에서 import 경로가 빠져 ModuleNotFoundError로 계산 전에 종료됐다. 저장한 실패와 함께 __file__ 기준 저장소 경로를 추가하여 다시 실행했고6개 final 일치 및 raw pstats 재도출을 확인했다. 이 driver/파생 분석은 ignored run 안에 두고 own SHA를 기록했으며 main campaign source map을 변경하지 않는다.

읽은 범위: AGENTS/RULES 전체, CURRENT_STATE 상단 및 관련 C1-B1, REPO_MAP 관련 행, docs 안내/분류 상단, 관련 runtime/arithmetic/reference/producer/campaign/tests와 산술 논증. 저장소 전체 및 ignored runs 전체를 읽지 않았다. FULL·trajectory·cost·profile은 이번 실제 새 실행이며 audit reviewer는 자신이 실행한 probe와 최종 campaign 미실행을 구분해 기록했다.

Raw stage manifest/19개 gzip trace/3개 study pstats/production pstats/FULL log·XML/check/derived_results·derivation_provenance를 새 campaign 폴더에 보존한다. 문서는 source suffix inventory에 포함되지 않으며 문서 정리와 commit 뒤 현재 source binding을 다시 확인한다. ignored evidence/worktree 자동 삭제나 archive 없음.
