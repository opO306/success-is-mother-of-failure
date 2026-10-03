# Verified Superoptimizer Pilot2 — prepared drift / raw integer exact arithmetic

2026-10-03. Base 41605579606cabe6a1ee161a5364e689fa11fbc1.
Separate `codex/c1b1-pilot2-prepared-drift` worktree; master/local verified commits preserved.
No H2/foundation change, no push or mainline merge. Production default remains current Candidate B FAST.

**Measurement protocol correction:** the first cost campaign below is retained history,
not the final closure. Its bigint100000-call multiplication batches each had one zero
process-CPU sample on Windows; wall time was positive. Final check returned INCOMPLETE,
without weakening the positive-clock gate. New batches are1000000 calls with explicit
calls/warmup metadata and negative payload tests. All arithmetic kernels are unchanged.
New source16a42af7f10a6a56a3ac1de05c261a4415e47b57f22b942420b8856ab3cb54ca,
same input c9591c4e26a31504142ecf32cb7aa0c5fb50d92f52421630ec8ed8deb5baa5e0,
run4b794fa7-d372-4d52-a0c5-067b2d994e22 in `runs/c1b1_pilot2_v1/final_clockfix_v1`.
Fresh campaign and FULL are rerun; first source snapshots/results/zero samples remain intact.
Clock-fix tests: intentional RED2/pass2, then121 pilot PASS and199 related PASS83.98s.
An attempted PowerShell wildcard invocation collected no tests and is retained as a command
error log; the explicit rg-selected file list was executed successfully.

Clock-fix component/differential PASS:336 inputs/387 midpoint-neighbor inputs,
all six55845 steps, four refusals and actual cap16384 STOP. New FULL3865 passed /
FAIL0 ERROR0 XFAIL1 actual SKIP0,25 warnings; pytest653.56s/subprocess654.902211s.
New bigint1e6 batches all have positive CPU/wall and validate PASS. Fresh benchmark/profile
and all-stage closure PASS. Final current-source results are in the final clock-fix section;
first-campaign measurements remain separately labeled retained history.

## Scope and limits

Only canonical FixedPoint raw arithmetic is optimized. Exact displacement and rounded
displacement stay separate. Existing original slow REF, FAST impulse, `_model_R`, `_decide`,
FixedPoint rounding/range semantics, original step/segment/stored-domain guard and producer
are untouched. Pilot executes unchanged step code with private drift/kick function bindings.
Profile lookalikes/subclasses/per-instance overrides remain on original arithmetic.
Bound executors have immutable local conversion coefficients; changed run bindings refuse
before execution. There is no global cache, extra rounding, reduced precision or automatic retry.
Algebraic argument: [exact arithmetic transformation](C1B1_PILOT2_EXACT_ARITHMETIC_ARGUMENT_V1.md).
Finite numerical comparisons and integer identities do not close A-EV, entire physical
regions, unlimited trajectories or proof-assistant obligations. New CONFIRMED histories: 0.

## Initial evidence and preserved failures

Initial root master HEAD4160557, origin/master6c53eec, ahead2/behind0; two user untracked
directories left intact. Native worktree created from local HEAD; no reset to remote.
46 original related tests PASS. New A tests26 RED→GREEN, B tests33 RED→GREEN, extra stale
component bindings3 RED→GREEN, C tests24 RED→GREEN. A and then B each completed six
trajectories55,845 steps against original REF/current FAST before proceeding.
Early measurement/source metadata is preliminary; final source-pinned campaign supersedes it.
109 newline-only checkout source differences were restored from base checkout without Git
blob changes. A-stage pre-restoration source binding is not final closure evidence.
First integrated related run had two existing producer test failures: our profile-mutating
test changed a shared fixture object. Test changed to mutate local clones; next132 PASS.
The failure log is retained. Driver fault tests additionally catch wrong raw impulse/state.

Whole-branch independent review: Critical0 / Important2 / Minor1. Important findings
were incomplete per-mode witness retention and incomplete payload/measurement validation.
Minor finding was failure rows not reaching the witness before assertion. All were accepted
and fixed in one pass. Retained 21 negative payload tests were RED before validation existed;
final related163 PASS. Review did not independently execute final FULL/cost campaign.
No second review was used to label final campaign independently approved.

First LOCAL FULL: 3859 passed / FAIL2 ERROR0 XFAIL1 actual SKIP0, 25 warnings,
pytest812.40s / subprocess814.3594695s. Both failures were missing Git-excluded historical
assets (`test_real_package_roundtrip_and_tamper_refusal` and
`test_stored_reference_uses_exact_raw_outlet_not_display_float`). The named original
artifact inventory98 files/108930634 bytes was copied with SHA verification; no runs scan.
Related retest additionally found CRLF checkout differences in two frozen protocol MDs.
Both matched original bytes after newline-only restoration, Git blobs unchanged.
Final related package/O-1 tests25 PASS20.60s. Original failures and logs are preserved;
second FULL is a new log/JUnit, not a replacement of the first result.

Second LOCAL FULL PASS: 3861 passed / FAIL0 ERROR0 XFAIL1 actual SKIP0,
25 warnings, pytest792.36s / subprocess794.2197153s, returncode0.
JUnit independently counted3862 entries; the one skipped XML node is the strict xfail.
The existing cp949 compiler-output decoding warnings remain unresolved.
Official AGENTS baseline is not changed by this opt-in pilot worktree result.

Final component and saved differential validation PASS: 336 arithmetic inputs,
387 ties/neighbors, six trajectories55,845 steps, four refusal/overflow cases and one real
cap16384 STOP, each matching all REF/BASE/A/B/C/Combined observations.
Actual normal trajectories contain335,070 displacements: max numerator132 bits,
fixed denominator139 bits, scaled numerator180 bits. This is actual half-kick-derived
data, separate from larger-denominator synthetic stress microcosts.

## Required final status

The fields below are filled from retained fresh campaign results after all stages complete.

| Field | Status |
|---|---|
| BASELINE PROFILE | fresh BASE six trajectories PASS; profile own CPU229.46875s including instrumentation |
| CANDIDATE A — Prepared Drift Packet | exact/component/trajectory PASS; final CPU step0.974x / trajectory1.029x, standalone step CPU gate not met |
| CANDIDATE B — Raw-Integer FixedPoint Drift | canonical FX exact/component/trajectory PASS; final CPU step1.000x / trajectory1.031x, standalone step CPU gain unconfirmed |
| CANDIDATE C — Raw Momentum Kick | exact/refusal/trajectory PASS; final CPU step1.086x / trajectory1.101x; first-campaign step variation retained |
| EXACT EQUIVALENCE | algebraic argument,121 pilot tests(117 prior+4 measurement), REF/BASE/all pilot modes55,845-step differential PASS; finite integration scope |
| ROUNDING / REFUSAL EQUIVALENCE | 336 component inputs,387 half-even/neighbor inputs, four refusals and actual cap16384 STOP PASS |
| FRACTION / GCD REDUCTION | PASS:Combined normal Fraction allocation routes27.5010% / gcd calls27.4606% fewer; self CPU separately recorded |
| BIGINT HIDDEN COST | PASS measured:normal actual132/139/180bit, fixed denominator; synthetic stress separately retained;1e6-call positive CPU samples |
| STEP / TRAJECTORY PERFORMANCE | final CPU Combined step1.085714x / trajectories1.128121x; both campaigns retained |
| LOCAL FULL | fresh clock-fix PASS:3865 passed, FAIL0 ERROR0 XFAIL1 SKIP0, 653.56s pytest / 654.902211s subprocess; 25 warnings retained |
| PRODUCTION PROMOTION | NOT_APPLIED; opt-in Combined worth review under measured conditions; production selector/default unchanged |
| UNRESOLVED | warnings25,timing variation,standalone A/B step gain,total production latency,broad FX/world/formal/native scope |

## Reproduction

Pilot API: `PreparedRuntime(run, 'BASE'|'A'|'B'|'C'|'Combined').step()`.
C changes only kick; Combined combines B drift with C kick. A keeps Fraction internally.
B keeps unreduced numerator/denominator until the exact endpoint/guard boundary.
CLI: `python -m experiments.verified_superoptimizer_c1b1.pilot2_stages seal --out <fresh-run>`;
then component, differential, benchmark, profile, bigint, check with the same --out.
Each stage is single execution and retains source/input binding, raw outputs and witnesses.
Whole-run benchmark has warm-up1000 steps/input/mode, 3 rotating/reversing repeats,
median CPU and wall; one CPU worker with affinity, admission/setup/hash outside timer.
Profiling uses process CPU timer and includes measurement overhead; it is not speedup evidence.
Synthetic real-cap stress needs CLI decimal text limit disabled; numerical cap stays16384.

## First campaign benchmark results — retained before clock fix

Ryzen5 5600, physical6/logical12, Python3.12.7 on Windows11. One worker, affinity logical11.
Component30000 calls, atom10000 calls, step1000 continuous head-on steps, all six complete
trajectories55845 steps. Warm-up1000 component/atom calls plus1000 steps per input/mode.
Three repeats, rotating/reversed mode order; median of each repeat's six trajectory CPU sums.
Admission, executor preparation and output hashing are outside the timer; identical raw-state
retention is inside the full-trajectory timer. Production IO/verifier costs are outside scope.

| Mode | component CPU us/call (ratio) | atom CPU us/call (ratio) | step CPU us/call (ratio) | six trajectories CPU s (ratio) |
|---|---:|---:|---:|---:|
| BASE/current Candidate B FAST | 6.250 (1.000x) | 28.125 (1.000x) | 625.000 (1.000x) | 37.531250 (1.000x) |
| A | 3.646 (1.714x) | 23.438 (1.200x) | 593.750 (1.053x) | 37.000000 (1.014x) |
| B | 4.688 (1.333x) | 17.188 (1.636x) | 578.125 (1.081x) | 36.750000 (1.021x) |
| C | 7.292 (0.857x) | 32.813 (0.857x) | 640.625 (0.976x) | 34.828125 (1.078x) |
| Combined/B+C | 4.688 (1.333x) | 17.188 (1.636x) | 531.250 (1.176x) | 33.203125 (1.130x) |

C uses identical BASE drift component/atom code. The apparent0.857x there is variation,
not an arithmetic change. B and Combined use identical drift; public component helpers
validate twice, while the atom packet validates once, explaining a different measured
component-vs-atom boundary. Short CPU batches show15.625ms increments and only3 samples.
A/B trajectory gains are small and do not establish a robust standalone production benefit.
C standalone step is2.5% more CPU than BASE in this campaign, so it does not pass a
standalone all-workload performance gate; Combined passes the measured step+trajectory gate.

| Mode | component wall s/30000 | atom wall s/10000 | step wall s/1000 | six trajectory wall s |
|---|---:|---:|---:|---:|
| BASE | 0.192824 | 0.279053 | 0.616814 | 37.998483 |
| A | 0.117320 | 0.239469 | 0.593984 | 37.678109 |
| B | 0.146466 | 0.172023 | 0.592494 | 37.076493 |
| C | 0.228440 | 0.332716 | 0.683101 | 35.222583 |
| Combined | 0.149973 | 0.171476 | 0.607915 | 33.590601 |

Combined CPU reduction is15.0% step /11.5321% trajectory. Wall step improvement is only
1.01464x; trajectory wall1.13122x. These are separate measured medians, not an end-user
latency guarantee. Original step CPU samples0.53125/0.5/0.59375 and wall0.5404641/
0.6174501/0.6079149 are retained. Desktop background load/frequency was not controlled;
no simultaneous pytest/native compiler process was found in the in-run snapshot.

| Mode | trajectory CPU repeat0 | repeat1 | repeat2 |
|---|---:|---:|---:|
| BASE | 37.437500 | 37.531250 | 38.406250 |
| A | 36.734375 | 37.000000 | 39.359375 |
| B | 36.718750 | 36.750000 | 41.734375 |
| C | 34.828125 | 34.437500 | 43.265625 |
| Combined | 33.203125 | 33.156250 | 35.984375 |

Raw samples, every result hash and environment: `runs/c1b1_pilot2_v1/final/benchmark.json`.
Derived units/ratios/repeat totals: `derived_benchmark_analysis.json` in the same directory.
Source d686b3a4bbf28f1d57b13a9ddbfd7e604ca05805fdf93ac2dd7161252bedde00;
input c9591c4e26a31504142ecf32cb7aa0c5fb50d92f52421630ec8ed8deb5baa5e0.

## First campaign BASE profile — retained before clock fix

Full six normal trajectories, setup/admission/output hashing outside profiler. No synthetic
STOP/refusal stress is included. cProfile process CPU timer,247.65625s total own CPU.
Instrumentation makes this much higher than37.53125s benchmark and its time is not a speedup.

| Function | Calls | Own CPU s | Profile CPU share |
|---|---:|---:|---:|
| FAST `_impulse_model_R_fast` | 56474 | 22.109375 | 8.927% |
| Fraction `__new__` | 8274470 | 18.234375 | 7.363% |
| Fraction `forward` | 8615479 | 18.234375 | 7.363% |
| math.gcd | 19825340 | 13.171875 | 5.319% |
| Fraction `_mul` | 4817971 | 12.296875 | 4.965% |

Fraction `_from_coprime_ints` additionally creates8783020 objects (own CPU10.765625s).
Normal Fraction constructor-route total17057490; `__new__` alone is not allocation count.
Calls are exact profiler counters. Own CPU is instrumentation/clock-sensitive attribution,
not an isolated unprofiled kernel cost. Force enclosure calls are not impulse-call count.

## Input coverage and differential boundary

| Input | Energy exact | Impact parameter fraction exact | Successful steps |
|---|---|---|---:|
| head_on | 9 | 0 | 1564 |
| oblique | 1/2 | 1 | 6456 |
| weak | 1/100 | 2 | 26285 |
| extra_head_on | 1/2 | 0 | 5597 |
| extra_high_oblique | 5 | 3/2 | 2454 |
| extra_low_oblique | 1/10 | 3/2 | 13489 |

All normal trajectories use dt40, position FX96.48, momentum FX96.80, original Ar40 mass,
and the same R20 outgoing exit; each has original REF, BASE/current FAST, A,B,C,Combined.
Stored witnesses retain each actual mode's initial/spec/source, every impulse raw and call
arguments, exact guard inputs/minimum, successful raw state, final state and STOP result.
Cold-start/final impulse cache connections and outgoing boundary are validated.
The checker independently reconstructs kick/drift/endpoint using original `_kick`/`_drift`,
never candidate packet helpers. Separate numerical trajectory evidence supplements the
integer identities and existing endpoint proof; it does not replace them.

Four diagnostics refuse on the first attempt, step0 with unchanged raw state and run
metadata: PhysicsDomainExceeded, impulse VMHalt/overflow, momentum ExecutorLimitExceeded,
position ExecutorLimitExceeded. The huge exact-dt stress reaches original16384bit cap and
ReferenceUndecided at step0, preserving reason/message/state; this is not a normal-world input.
Six normal paths contain55851 impulse calls per mode; adding five diagnostics gives55856.
Numerical precision cap16384 is distinct from the stress diagnostic's one-step attempt cap.

Component catalog varies widths8/16/96/192, position fractional bits0/4/48/110, momentum
fractional bits0/7/80/150, dt0/40/7over11/-9over13, Ar40/13over17/1over(2^127-1) masses,
zero/sign/small/large raws. Midpoint tests use129 integer cells times exact tie and two
adjacent rational values. Tests separately cover displacement-vs-endpoint rounding,
overflow order, r_min-near guard, unsupported profile/retired-v1 fallback, stale contracts,
invalid raw and corrupted saved witnesses/measurements. This is not all FixedPoint coverage.

Final hashes and witness digests: `runs/c1b1_pilot2_v1/final/differential.json` plus11 compressed
histories. Full benchmark stored-trajectory fingerprints are recorded in `benchmark.json`;
all modes/repetitions match. Independent saved-data recheck before cost stages:
`exact_differential_validation.json` (PASS). Final all-stage closure is reported separately.

## 최종 clock-fix 캠페인 — 전체 closure PASS

Run `4b794fa7-d372-4d52-a0c5-067b2d994e22`, source `16a42af7f10a6a56a3ac1de05c261a4415e47b57f22b942420b8856ab3cb54ca`,
input `c9591c4e26a31504142ecf32cb7aa0c5fb50d92f52421630ec8ed8deb5baa5e0`.
현재 산술·측정 소스와 입력을 그대로 봉인한 새 실행이다. 이전 결과를 새 hash로 바꾸거나 복사해 PASS로 세지 않았다.
최종 `pilot2_stages check`는 returncode0/PASS,21.625405초였다.
보존된 source snapshot·첫 측정의 0초 샘플·실패 FULL·명령 수집 오류를 삭제하지 않았다.

이 검사는 승인된 조건의 exact 값과 현재 실행 의미를 확인한다. 모든 FixedPoint·모든 물리 영역·무한 궤적·외부 감사/정식 증명을 닫는 결과는 아니다. Production은 NOT_APPLIED다.

### STEP / TRAJECTORY PERFORMANCE

Ryzen5 5600/6코어12논리스레드, Python3.12.7, Windows11. Benchmark/profile는 논리CPU11에 고정한 작업자1개다. Bigint는 작업자1개이며 affinity를 고정하지 않았다. 워밍업과 반복/시계 경계는 앞의 동일한 규약을 사용했다. 각 mode 3회, trajectory는 반복별6개 합계의 중앙값이다. BASE는 현재 production Candidate B FAST이며, 이전 slow REF의 배속을 곱하지 않았다.

| Mode | drift component CPU us/회 | drift atom CPU us/회 | step CPU us/회 | 6 trajectory CPU s | step 배속 | trajectory 배속 |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 6.250 | 28.125 | 593.750 | 37.421875 | 1.000x | 1.000x |
| A | 4.167 | 21.875 | 609.375 | 36.375000 | 0.974x | 1.029x |
| B | 4.688 | 17.188 | 593.750 | 36.312500 | 1.000x | 1.031x |
| C | 5.729 | 28.125 | 546.875 | 34.000000 | 1.086x | 1.101x |
| Combined | 5.208 | 17.188 | 546.875 | 33.171875 | 1.086x | 1.128x |

| Mode | component wall s/30000 | atom wall s/10000 | step wall s/1000 | trajectory wall s | trajectory CPU repeat0/1/2 s |
|---|---:|---:|---:|---:|---|
| BASE | 0.1828933 | 0.2822577 | 0.5941535 | 37.6966705 | 37.421875 / 37.015625 / 40.390625 |
| A | 0.1149032 | 0.2206465 | 0.6028090 | 36.6891033 | 36.375000 / 36.281250 / 37.875000 |
| B | 0.1470555 | 0.1678093 | 0.5887267 | 36.5970354 | 36.312500 / 36.203125 / 36.625000 |
| C | 0.1842056 | 0.2831642 | 0.5531085 | 34.2202166 | 33.953125 / 34.000000 / 40.828125 |
| Combined | 0.1483611 | 0.1652082 | 0.5426886 | 33.5161061 | 33.171875 / 32.953125 / 36.468750 |

Combined CPU 감소는 step7.8947% / trajectory11.3570%다. Wall step1.094833x / trajectory1.124733x는 별도 중앙값이다. Step CPU 샘플은 0.546875 / 0.53125 / 0.90625초, wall은 0.5423259 / 0.5426886 / 1.7335505초다.
A는 step0.974x, B는1.000x로 이번 step CPU 감소 조건을 충족하지 못했다. C는 이번에는 두 경로가 개선됐으나 첫 캠페인의 step0.976x와 함께 보존한다. 작은 단독 이득의 재현성은 충분히 확정하지 않는다. Combined는 두 캠페인 모두 전체 trajectory CPU 감소(1.130x/1.128x)를 보였다.
C의 drift는 BASE와 동일하며, B/Combined의 drift도 서로 동일한 코드다. 그 control 구간의 작은 차이는 구현 효과로 판정하지 않았다. 성분 API는 계약2회 검사, atom packet은1회 검사라는 측정 경계 차이가 있다. 짧은 CPU 배치의15.625ms 단계와 배경 부하/GC/CPU 주파수 미통제,3회 표본의 한계를 유지한다. Setup/admission/준비/hash/producer IO/verifier는 측정 밖이며, 전체 trajectory raw-state 보존은 측정 안이다.

### FRACTION / GCD REDUCTION

각 칸은 **호출 수 / 자체 CPU 초**다. 아래 시간은 profiler 오버헤드와 process CPU 귀속을 포함하며 benchmark 배속을 대신하지 않는다. 호출 수는 원본 pstats의 실제 카운터다.

| Function | BASE | A | B | C | Combined |
|---|---:|---:|---:|---:|---:|
| __new__ | 8274470 / 16.203125 | 7939400 / 16.218750 | 7604330 / 14.921875 | 6264050 / 12.187500 | 5593910 / 10.359375 |
| _from_coprime_ints | 8783020 / 10.062500 | 8112880 / 10.515625 | 7442740 / 9.234375 | 8112880 / 10.015625 | 6772600 / 8.828125 |
| Fraction_allocation_routes_total | 17057490 / 26.265625 | 16052280 / 26.734375 | 15047070 / 24.156250 | 14376930 / 22.203125 | 12366510 / 19.187500 |
| forward | 8615479 / 17.343750 | 7945339 / 16.375000 | 7275199 / 14.515625 | 7945339 / 15.343750 | 6605059 / 14.000000 |
| _mul | 4817971 / 11.203125 | 4482901 / 10.875000 | 4147831 / 10.453125 | 4817971 / 11.468750 | 4147831 / 10.218750 |
| math.gcd | 19825340 / 12.968750 | 18149990 / 9.859375 | 16809710 / 9.531250 | 17396812 / 10.375000 | 14381182 / 8.593750 |

| Mode | Fraction 생성 경로 합계 감소 | gcd 호출 감소 | profile 자체 CPU 합계 s |
|---|---:|---:|---:|
| BASE | 0.0000% | 0.0000% | 229.468750 |
| A | 5.8931% | 8.4505% | 226.046875 |
| B | 11.7861% | 15.2110% | 220.437500 |
| C | 15.7149% | 12.2496% | 206.265625 |
| Combined | 27.5010% | 27.4606% | 190.046875 |

정상 Fraction 생성 수는 설치된CPython3.12.7의 `__new__`와 `_from_coprime_ints` 두 실제 생성 경로를 합했다. stdlib 소스 SHA는 `environment.json`에 저장했다. __new__만으로 전체 생성을 세지 않았다. Combined의 요청4개 항목 자체 CPU 감소는 __new__36.0656%, forward19.2793%, gcd33.7349%, _mul8.7866%였다. A는 생성 수가 줄어도 두 생성 경로의 자체 CPU 합계가1.7847% 증가했다. 계측 시간의 잡음을 숨기거나 모든 항목의 자체 CPU가 감소했다고 보고하지 않는다.

### BASELINE PROFILE / 최종 새 병목

| BASE 자체 CPU 상위5 | 자체 CPU 비율 | 호출 수 | 자체 CPU us/호출 |
|---|---:|---:|---:|
| _impulse_model_R_fast | 8.729% | 56474 | 354.699 |
| forward | 7.558% | 8615479 | 2.013 |
| __new__ | 7.061% | 8274470 | 1.958 |
| math.gcd | 5.652% | 19825340 | 0.654 |
| _mul | 4.882% | 4817971 | 2.325 |

| Combined 자체 CPU 상위5 | 비율 | 호출 수 | us/호출 | exact/reference 위치 | 중복 계산 | 해당 비용이0일 때의 조건부 상한 |
|---|---:|---:|---:|---|---|---:|
| _impulse_model_R_fast | 10.442% | 56474 | 351.379 | 기존 verified FAST exact enclosure | 미판정 | 1.117x |
| forward | 7.367% | 6605059 | 2.120 | CPython exact Fraction | 미판정 | 1.080x |
| __new__ | 5.451% | 5593910 | 1.852 | CPython exact Fraction | 미판정 | 1.058x |
| _mul | 5.377% | 4147831 | 2.464 | CPython exact Fraction | 미판정 | 1.057x |
| _scale | 4.769% | 5082660 | 1.783 | 기존 impulse 정수 interval scalar | 미판정 | 1.050x |

조건부 상한은 계측된 자체 CPU 비율f에1/(1-f)를 적용한 표다. 실제 unprofiled 전체 CPU의 최대 배속을 확정한 수치가 아니며 호출당 시간도 계측 귀속값이다. 다음 최적화 대상을 선정하지 않았다. 기존 impulse의 `_scale`은 정수 곱셈/나눗셈을 포함하며 상대 순위가 올라왔다. 새 raw drift의 bigint 곱셈/rounding이 상위5 병목으로 올라온 증거는 관측되지 않았다.

### BIGINT HIDDEN COST

실제6개 궤적의 REF half-kick raw에서335070개 displacement를 다시 계산했다. 분자최대132bit, 고정 분모139bit, position scaling 후180bit였다. Contract 분모는 run-local 고정값이며 step 간 유리수 분모를 누적 곱하지 않는다.

| Micro 입력 | raw bit | n/D/shifted n bit | 약분 후 n/D bit | unreduced/reduced 두 정수 storage bytes |
|---|---:|---|---|---|
| production | 90 | 138/139/186 | 129/129 | 88/88 |
| large_denominator_stress | 186 | 316/154/426 | 316/154 | 116/116 |

각 primitive는1000회 warm-up,1000000회×3, median이다. 비용에는 Python loop/lambda 호출을 포함한다. 아래 칸은 **CPU ns/회 / wall ns/회 / peak bytes**다. Peak는 별도의1000회 tracer 실행이며 current live bytes는 모든 칸0이었다.

| Primitive | production 대표 | 큰 분모 synthetic stress |
|---|---:|---:|
| integer_multiplication | 62.500 / 69.584 / 152 | 109.375 / 110.243 / 208 |
| integer_round_division | 421.875 / 417.026 / 284 | 531.250 / 524.270 / 416 |
| gcd | 421.875 / 419.182 / 184 | 296.875 / 301.475 / 232 |
| Fraction_ratio | 828.125 / 831.957 / 368 | 750.000 / 744.722 / 444 |
| original_exact | 2187.500 / 2190.711 / 552 | 2046.875 / 2040.188 / 580 |

production micro 입력은FX96.48/FX96.80, dt40, 기존Ar40 mass, mom.hi//32로 실제 궤적보다 큰 대표 raw다. Synthetic은FX192.110/FX192.150, dt7/11, mass1/(2^127-1)이며 world trajectory가 아니다. 그 rounded raw는 FX position 범위를 넘으므로 여기서는 rounding 나눗셈 primitive만 계측했고 runtime의 overflow check는 유지했다. Stress와 정상 세계 비용을 합산하지 않았다.
Shared denominator의 sys.getsizeof는 두 정수 storage 비교이며 packet당 할당량은 아니다. tracemalloc peak/live bytes는 누적 allocation count나 전체 trajectory 메모리 감소량이 아니다. 이번 정상 world/측정 stress에서 bigint 폭발에 따른 전체 역전은 관측되지 않았다. 훨씬 큰 DT/분모/다른 grid의 performance는 미검증이다.

### 쉽게 답하는10개 질문

1. 기존 v2는 d=p*dt/m을 성분당2회, 원자당6회, 두 원자 step당12회 계산했다.
2. A/B/Combined는 성분당1회, 원자당3회, step당6회로 줄였다. C 단독은 drift의12회를 유지한다. Unsupported/retired-v1는 원래 경로를 사용한다.
3. 6개 완주에서 두 Fraction 생성 경로 합계가17057490→12366510회,27.5010% 줄었다.
4. gcd는19825340→14381182회,27.4606% 줄었다.
5. 양의 exact mass와 valid canonical FX라는 조건에서 원래 exact rational과 같은 정수 항등식이며, 현재 모든 component/rounded/endpoint/guard/state 관측이 일치했다. 전체 물리 영역 증명은 아니다.
6. 같은 momentum 격자의 kick은 p_raw±J_raw와 같은 range check로 동등했다. C의 kick 내부 Fraction 변환을 제거했고 overflow/거부 순서와 원인을 보존했다.
7. 최종 Combined step CPU median1.085714배, CPU7.8947% 감소였다. Wall median1.094833배는 별도다.
8. 최종6개 trajectory CPU median1.128121배, CPU11.3570% 감소였다. 37.421875→33.171875초다.
9. 새 raw drift에서 numerator/denominator 누적 성장과 bigint 비용의 상위5 진입은 관측되지 않았다. 기존 impulse 정수 `_scale`의 상대 순위 상승은 별도로 기록했다.
10. Combined는 이번 조건에서 production 승격을 검토할 가치가 있다. 기존 production selector/default는 NOT_APPLIED이며, 이 커밋은 검증된 opt-in 후보와 evidence를 보존한다. A/B 단독의 step 이득은 미확정이다.

### LOCAL FULL / PRODUCTION PROMOTION / UNRESOLVED

최종 FULL은3865 PASS/FAIL0/ERROR0/XFAIL1/SKIP0,25 warnings, pytest653.56초/프로세스654.902211초다. JUnit3866건을 별도로 집계해 strict xfail1을 실제 skip과 분리했다. 공식 AGENTS 기준선은 갱신하지 않았다.

모든 required source/input/stage 기록과 측정 일관성 gate, 선택된Combined의 exact/rounding/guard/overflow/STOP/state/trajectory/FULL/CPU 감소 gate가 통과했다. A/B 단독의 step CPU gate는 충족하지 못하거나 중립이다. 기존 slow REF/current FAST impulse/profiles/runtime/실제 producer/원래 checker의7개 파일은 root/base와 현재 bytes가 모두 같음을 재확인했다. 새 산술은 기존 step code object의 private namespace에서 drift/kick만 bind한다.

새 원자/모델/physics/rounding/precision/cap/cutoff/전역 cache는 추가하지 않았다. Production의 default/REF 선택과 기존 audit/endpoint proof는 그대로다. 검토할 구체 결과는 opt-in Combined이며 적용은 NOT_APPLIED, mainline merge와 push는 하지 않는다.

남은 한계: cp949 compiler 출력 해독 warnings25,3회 timing/짧은 CPU clock의 변동, A/B의 standalone step 이득, 초기 준비/IO/verifier를 포함한 총 production latency, 전체 FX/큰 profile 확장성, 정식 증명·전 물리 영역·무한 궤적·A-EV/native J. Reviewer는 첫 whole-branch 판독의 Important2/Minor1을 지적했으며 수정했다. 최종 cost/FULL/clock protocol 수정은 구현자의 실행/검증이고 별도의 외부 독립 승인으로 부르지 않는다. 새 CONFIRMED history0.

최종 실행·상세 samples·pstats·11개 gzip witness·closure·파생 수치·derivation provenance는 `runs/c1b1_pilot2_v1/final_clockfix_v1/`에 보존했다. source suffix inventory는 문서를 제외하므로 이 보고서/문서 entry 갱신은 산술 및 측정 binding을 바꾸지 않는다. ignored run evidence와 필요한 원래 assets는 worktree에 보존하며 자동 삭제/아카이브하지 않았다.
