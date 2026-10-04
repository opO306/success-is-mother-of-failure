# C1-B1 Optimization Generation 1 종료 기록

계산·검증 실행일: 2026-10-03. 종료 문서 확정일: 2026-10-04.

**최종 상태: `VERIFIED FAST-PATH GENERATION / NOT FORMALLY CERTIFIED`. Optimization Generation 1 FROZEN.**

Generation 1 production default는 **`fast_pilot3`**다. 적용 범위는 `codex/c1b1-generation1-freeze` integration branch이며 root master를 변경하거나 push한 것은 아니다. 모든 아래 수치는 완료된 `post_default_v3` 기록에서 옮겼으며 이번 문서 종료 작업에서 재측정하거나 기존 evidence/result를 수정하지 않았다.

## 판정 범위와 남은 한계

동결 대상은 **Optimization Generation 1**이다. C1-B1 ④ 전체, A-EV, native J, 무한 domain/trajectory 완전성, independent replay 승인 또는 물리 Foundation 완료 판정이 아니다. finite exact arithmetic 검사와 integration witness는 서로 다른 증거이며 기존 endpoint 논증을 trajectory equality로 대체하지 않는다.

Python/표준 라이브러리/builtins와 binding 검사 코드 자체는 신뢰 경계 안이다. 악성 코드가 검사를 끄거나 private binding을 고치는 상황, step 실행 도중 다른 thread가 model/Run을 바꾸는 상황은 지원하지 않는다. FULL의 기존 CUDA/GPU 시험은 포함하되 새 계산 후보·성능 실험은 CPU만 사용했다.

지원 production 기준은 canonical FixedPoint v2, Ar40, dt=40, position FX(96,48), momentum FX(96,80)의 실제 입력과 기존 거부 경계다. FX(192,150), 큰 dt/raw, M=128〜16384 등의 추가 exact 표본도 검사하지만 모든 profile/domain의 보편적 속도나 결정 가능성을 주장하지 않는다. custom profile/Binary64/v1은 기존 explicit fallback 의미를 유지한다. stale prepared 조건은 fallback으로 숨기지 않고 계산 전에 거부한다.

## 통합과 production 선택

- 시작 master 및 origin/master: `0f7b744cf754450424a63c47f305e0327c5b37c1`.
- Pilot 3: `6714321523242ba777007a16ff2a9238a0c90b3c`, 공통 조상 `9ad2ed7280f84f51e5e6dd99a60e69c76bedd6ae`.
- 새 managed worktree `c1b1-gen1-integration`, branch `codex/c1b1-generation1-freeze`에서 local no-ff merge. Merge HEAD `10390717a0fc6888915c39b7262e49f626378ba3`.
- 최신 master의 별도 12개 추가 파일은 원래 Git blob/bytes를 보존했다. branch 전용 절대 경로를 runtime source에 넣지 않았다. enumerated ignored 검증 자산 105개만 SHA 검증해 복사했다.
- root master는 시작 위치에 남기며, 검증·default 변경·종료 commit은 integration branch에 둔다. push하지 않는다.

| mode | 실제 실행 | 보존 목적 |
|---|---|---|
| `reference` | `c1b1_two_atom` slow REF | proof/reference/audit 기준 |
| `fast` | Candidate B impulse + 기존 `step_fast` | 이전 verified 경로·차등 비교 |
| `fast_combined` | Candidate B impulse + prepared raw drift/kick | 중간 경로·차등 비교 |
| `fast_pilot3` | Combined 산술 + Pilot 3 ABCD impulse | Generation 1 guarded production default |

`c1b1_runtime.select/impulse/step/bind` 및 실제 producer의 execute/batch/CLI 기본값을 함께 연결했다. producer는 run당 한 번 bind한다. 편의 함수 `runtime.step(run)`은 매 호출 bind하므로 여기의 bound production trajectory 성능과 같은 비용이라고 주장하지 않는다. verifier worker에는 producer-side runtime import가 들어가지 않는다. Candidate B의 기존 differential/profile 도구는 명시적 `fast`를 호출하도록 유지했다.

slow REF, `_model_R`, primitives, 물리 parameter, rounding source, proof/checker는 보존했다. Combined/Pilot 3 numerical 함수 본문은 이전 source와 AST를 대조했고, Pilot 3 public `impulse`에는 world boundary check만 추가했다. 모든 prepared executor는 기존 `step` code object를 사용한다.

## Prepared binding 수명

상세 규칙은 [binding contract](C1B1_GENERATION1_BINDING_CONTRACT_V1.md)에 있다.

| 층 | bind 조건 | 유효 수명과 invalidation |
|---|---|---|
| WORLD | physics fingerprint, C1-A/C1-B1 contract, retardation, nearest-ties-even contract; parameter 원본 snapshot과 실제 numerical/rounding function 및 code identity | full fingerprint는 준비 때 한 번. hot path에서는 identity/value 비교. coefficient/version/rounding/함수 교체 시 stale 거부 |
| RUN | 정확한 Run 및 pos/mom 객체 identity; species 순서, mass/dt의 정수 비율, profile(W,F), drift, precision policy, mode/variant | dt/species/mass/profile/identity/mode가 달라지면 계산 전 거부. supported metadata 변경 뒤 재준비는 명시적 호출 |
| STEP | 현재 좌표/운동량과 실제 impulse cache provenance | 이전 step의 정상 J cache만 그 dependency가 같을 때 사용. 관련 조건/좌표/J 변화 시 옛 cache 거부 |
| COMPONENT | 현재 raw 성분/dt/scale/M, 해당 call에서 만든 exact endpoint | component/다른 Run 사이 결과 재사용 없음; full hash나 Fraction normalization 검사 없음 |

WORLD snapshot은 key/value의 타입까지 고정한다. Python에서 같은 값으로 비교되는 `3`과 `3.0`은 다른 계약 입력이며, fingerprint/실제 계산 의미를 바꾸는 변경을 거부한다. Run/profile/함수/code/준비 배열의 identity 변경과 다른 Run 재결속도 감지한다. stale binding은 보존된 step code로 진입하기 전에 거부한다.

RunKey는 mass/dt를 독립 immutable integer pair로 소유한다. source Fraction private slot 변경이 snapshot을 함께 바꾸지 않는다. exact displacement와 rounded 저장값은 별도로 유지하고 원래 segment guard에 exact endpoint를 전달한다. raw kick은 같은 momentum profile의 integer `p±J`이며 rounding 위치는 바뀌지 않았다.

successful prepared step 뒤 기록하는 J cache provenance는 world/Run 조건, 현재 저장 좌표와 raw J를 포함한다. stale cache가 있으면 새 binding도 거부한다. caller가 `J_cache=None`을 명시적으로 설정한 뒤 재bind해야 하며 자동 retry/repair는 없다. 초기 `t_steps=0`에서 제공된 cache는 기존 REF의 선언 입력으로 받아들인다. 그 값의 외부 물리 provenance를 증명한 것은 아니다. untagged mature Run은 cache를 명시적으로 비워야 한다.

## 검증과 evidence epoch

Opt-in epoch `runs/c1b1_gen1_v1/optin_v2`:

- source hash `cabcc286a7ebcf99f112216652e39a351f86f88db26fe13634e123ff6a2e8866`.
- 21 cases, 59,171 successful steps, 59,187 actual impulse events; REF/fast/Combined/Pilot3 every raw J/displacement/exact endpoint/guard/stored state/exception/final 일치.
- 기존 producer 7 witnesses, 79,087 steps: 네 mode의 실제 raw J/state 일치. 동일 기존 입력으로 **새 실행**했으며 새로운 CONFIRMED history 승격은 아니다.
- LOCAL FULL: 4128 PASS / 1 strict XFAIL / FAIL·ERROR·실제 SKIP 0. pytest 727.24초, process wall 728.683132초. 기존 compile decoding 경고 26개, 원인/해결 미확정.
- 마지막 checker에서 JSON array/Python tuple 표현을 그대로 비교해 실패했다. integer value/수학 불일치가 아니었다. original source snapshot과 모든 출력은 그대로 두고 narrow analysis-only repair를 검증해 `closure_rebound_v1.json` PASS. runtime/math/measurement source bytes는 이전 epoch와 같음을 별도 검사했다. 해당 PASS를 새 default source의 FULL로 재명명하지 않는다.

최종 default epoch `runs/c1b1_gen1_v1/post_default_v3` — 완료, 현 source의 live closure PASS:

- source hash `582323351e6dfa29bdf0cc26a9a029b85f3105fc15734433d3234e5724c3f206`.
- input hash `1100cfdbaef3c79e1a950c5903ddc8b47decaec8ab56302e7780ebecaea833bf`.
- run id `95dcf9fc-0ef6-48cd-9ec6-138e6b97dcc8`.
- **21 cases / 59,171 successful steps / 59,187 impulse events**. 기존 six trajectories 55,845 steps + 15 악성/3D/거부/STOP 진단. 실제 16384 precision STOP 포함. 모든 case의 정상 완주를 뜻하지 않으며 기존 거부·overflow·domain·precision STOP 결과를 보존했다. 매 raw J/displacement/exact drift endpoint/guard/stored state/refusal/final이 REF/fast/Combined/Pilot3에서 일치했다.
- **producer witness 7개 / 79,087 steps**: actual producer는 명시적 네 mode에 더해 **mode를 생략한 production default**도 모든 raw J/state와 비교해 PASS했다. 원본 seven witness hash/step count도 seal에 포함했다. 새 CONFIRMED history나 independent replay 승인으로 승격한 것은 아니다.
- fixed-M independent checker의 **889 endpoint rows / 222 output outcomes**, bigint stress **4개**, actual differential, producer, FULL, CPU samples 및 profile이 모두 새 source에서 PASS했다. 검사한 stress에서는 cross-step rational chain/누적 분모 폭발이 없었으며 무한 입력의 scaling 증명은 아니다.
- **LOCAL FULL: 4157 PASS / 1 strict XFAIL / FAIL 0 / ERROR 0 / real SKIP 0**. pytest **642.17초**, process wall **643.6113394초**, worker 6. 기존 CUDA/GPU 회귀 시험도 포함했다. **cp949 compiler reader-thread 경고 27건**은 보존하며 원인/해결을 확정하지 않았다.
- 이전 v2의 **4145 PASS / 1 strict XFAIL / FAIL·ERROR·실제 SKIP 0**, pytest **671.96초**, process wall **673.421016초**는 이전 source에서 완료한 실행으로만 보존한다. 새 source의 FULL로 세지 않는다.
- **evidence closure PASS**: `validation_source.kind=live`, source/checker hash 동일, `default_producer_verified=True`. fixed/bigint/integration/producer/FULL/benchmark/profile/check 8개 실행 모두 rc 0, 실행 전후 source 불변. [최종 closure](../../runs/c1b1_gen1_v1/post_default_v3/closure.json).
- 최종 reviewer의 읽기 검토에서도 남은 Critical/Important correctness blocker를 발견하지 않았다. reviewer는 저장 결과/schema/identity/성능 범위를 검토했으며 FULL/benchmark/closure를 다시 실행한 것은 아니다.
- 21개 integration trajectory fingerprint: `e6daafc76e631527b5fdc9c64034cfb6e87790a2fc9468918327cbff27753705` (id/step/final SHA/witness SHA의 canonical 집계). 개별 raw 기록과 final SHA는 [integration](../../runs/c1b1_gen1_v1/post_default_v3/integration.json), [fingerprints](../../runs/c1b1_gen1_v1/post_default_v3/trajectory_fingerprints.json)에 있다.
- [FULL raw log](../../runs/c1b1_gen1_v1/post_default_v3/full.log), [JUnit](../../runs/c1b1_gen1_v1/post_default_v3/full.xml), [process record](../../runs/c1b1_gen1_v1/post_default_v3/full_execution.json), [fresh source audit](../../runs/c1b1_gen1_v1/post_default_v3/source_audit_final.json)를 보존한다. 공식 AGENTS 역사 기준선은 바꾸지 않았다.

Fault tests는 최소 dt/species/mass/posF/momF/physics fingerprint/rounding version/otherRun뿐 아니라 source Fraction slot, LN2, primitive/function/code, segment/drift/rounder, mutable Candidate B cache 및 stale J reuse를 주입했다. numerical entry 0과 Run 불변 거부를 확인한다. 빠진/중복 CPU sample, 결과/median/hash/step 수/default mode 오염은 evidence gate에서 거부한다.

## CPU 측정과 검사 비용

Ryzen 5 5600, 6 physical cores / 12 logical threads, Python 3.12.7, worker 1, CPU affinity [11]. warmup 1000 steps/case/mode 및 1000 micro calls, repeat 3, order rotate/reverse, median process CPU time. drift/kick 100,000 calls, step 1000 calls, six complete trajectory 합계. trajectory timer는 Run admission/binding/hot guards/R20 종료/상태 보존을 포함하며 결과 hash는 timer 밖이다.

WORLD/Run/step guard의 별도 cost는 `WorldBinding.build`/실제 `runtime.bind`/`RunBinding.assert_current` 반복의 call당 median이다. module import와 Python process cold startup는 별도 cost에 포함하지 않는다. trajectory 비교는 warm world 조건이며 WORLD 일회 준비 비용은 따로 기록한다.

최종 campaign은 같은 source/input/run에서 직접 측정한 값이다. 이전 campaign들의 speedup 숫자를 곱하지 않는다.

| 경로 | six trajectory CPU 합의 median (s) |
|---|---:|
| slow REF `reference` | 51.625000 |
| Candidate B `fast` | 36.703125 |
| `fast_combined` | 50.500000 |
| Generation 1 default `fast_pilot3` | 31.671875 |
| isolated guard control | 27.406250 |

**최종 직접 누적 speedup은 REF 대비 1.629995×, CPU 시간 38.6501% 감소**다. Pilot3는 Candidate B 대비 1.158855×/CPU 13.7080% 감소, Combined 대비 1.594475×/CPU 37.2834% 감소다. 반면 **fast_combined는 Candidate B보다 CPU 시간이 37.5905% 증가**했다. 중간 mode의 이 최종 campaign 성능 회귀를 숨기지 않는다. 주장 범위는 로컬 CPU/선정된 six trajectories/3 repeats이며 향후 hardware/workload의 보편적 성능 보장은 아니다.

| call당 median 검사/준비 비용 | 값 |
|---|---:|
| World prepare | 1.453125 ms (약 1.453 ms) |
| Run binding | 152.343750 μs (약 152.344 μs) |
| empty-cache hot check | 59.375000 μs/call |

World 2000 calls/rep, Run 20000 calls/rep, hot check 50000 calls/rep로 별도 기록했다. 검사 control과의 **관측 차이 4.265625 s**, Pilot3 총 CPU의 **13.4682%**, 성공 step당 약 **76.38 μs**는 새 World/Run 검사와 성공 step의 cache provenance 기록을 함께 제거한 차이다. **World guard 단독 비용이 아니다.** empty-cache micro도 실제 mature cached-step 전체 비용과 다르다. control은 benchmark 안에서만 사용하며 production mode로 제공하지 않는다.

추가 isolated 계산 median(s):

| 범위/호출 수 | REF | Candidate B | Combined | Pilot3 |
|---|---:|---:|---:|---:|
| drift / 100000 | 2.796875 | 2.828125 | 1.750000 | 1.687500 |
| kick / 100000 | 2.515625 | 2.500000 | 0.531250 | 0.531250 |
| step / 1000 | 0.875000 | 0.593750 | 0.828125 | 0.515625 |

[raw CPU samples](../../runs/c1b1_gen1_v1/post_default_v3/benchmark_samples.jsonl), [benchmark medians/environment](../../runs/c1b1_gen1_v1/post_default_v3/benchmark.json), [성능과 profile 해석](../../runs/c1b1_gen1_v1/post_default_v3/performance_profile_analysis.json).

### 최종 production profile Top 10

계측 범위는 같은 six trajectories의 고정 55,845 production steps이며 admission/bind/R20 observer/hash/상태 저장은 제외한다. cProfile의 process CPU 계측 self 합은 Pilot3 **188.9375 s**, Combined **466.390625 s**다. call instrumentation이 비용을 더하므로 위의 unprofiled trajectory median과 같은 지표로 비교하지 않는다.

| 함수 | self CPU % | calls | self μs/call | 이상적 전체 speedup 상한 | exact/reference·중복 가능성 검토 |
|---|---:|---:|---:|---:|---|
| Pilot3 model_prepared | 8.9067 | 56,474 | 297.9800 | 1.097776× | exact rational enclosure; 현재 impulse/M마다 계산 |
| Fraction.__eq__ | 5.1356 | 4,355,910 | 2.2276 | 1.054137× | exact 계약/수치 비교; 반복 비교가 제거 가능하다는 증거는 없음 |
| binding _FrozenScalar.__eq__ | 5.0529 | 5,863,725 | 1.6281 | 1.053218× | typed snapshot 비교; 매 step stale 검사를 위한 반복 |
| FAST _taylor_side | 4.2838 | 938,650 | 8.6228 | 1.044755× | exact integer interval; 두 경계/M 시도 |
| builtins.isinstance | 4.2011 | 9,095,580 | 0.8727 | 1.043854× | type/ABC 검사; 여러 caller가 공유 |
| binding function-check genexpr | 4.1432 | 3,853,305 | 2.0315 | 1.043223× | function/code identity; 매 step 검사는 의도된 계약 |
| builtins.getattr | 3.0930 | 12,062,508 | 0.4845 | 1.031917× | identity/attribute 검사; 다른 caller의 비용 중첩 |
| FAST _mul | 2.7870 | 5,703,874 | 0.9232 | 1.028669× | exact interval 정수 곱; 같은 operand 재사용 증명 없음 |
| Pilot3 _scale | 2.7043 | 5,082,660 | 1.0053 | 1.027794× | exact integer-pair scale; coefficient/component마다 입력 상이 |
| binding World.assert_current | 2.6712 | 55,845 | 90.3729 | 1.027445× | WORLD stale guard; 반복 제거는 계약 변경이 될 수 있음 |

상한은 해당 함수의 **self 비용을 다른 비용 증가 없이 0으로 만들 때**의 이상적 Amdahl 상한이다. 실제 달성 가능한 개선 예측이나 다음 후보 선정이 아니다. exact/reference 표기는 계산/검사 성격을 뜻하며 새 formal proof 판정이 아니다. 전체 slow REF는 별도 보존했다.

선택 지표: Fraction.__new__ self **2.0096% / 1,451,988 calls**, Fraction.forward **2.1998% / 2,401,335 calls**, Fraction._mul **1.2488% / 893,520 calls**, math.gcd **2.0427% / 5,136,268 calls**. raw drift `_ratio` **0.2729% / 335,070 calls**, `_rounded` **0.2894% / 335,070 calls**, `prepare_drift` **0.5706% / 111,690 calls**다. cProfile은 함수 내부 integer multiply/divide operator를 따로 분리하지 못하며 해당 bounded 비용은 [bigint stress/micro](../../runs/c1b1_gen1_v1/post_default_v3/bigint.json)에 있다. Fraction 완전 제거나 이번 캠페인의 새 allocation-count 감소를 주장하지 않는다.

binding 모듈 self는 **13.8273%**, FAST impulse primitives 모듈 self는 **14.9686%**다. World.assert_current cumulative **31.3265%**와 Run.assert_current cumulative **33.0301%**는 중첩되므로 합산하지 않는다. 이 계측값은 unprofiled control 차이 13.4682%와도 다르다. 검사 비용은 주요 CPU 비용으로 남았지만 default Pilot3의 순이득은 유지됐다. 새 최적화 대상은 정하지 않았다. [Pilot3 pstats](../../runs/c1b1_gen1_v1/post_default_v3/fast_pilot3.pstats), [Combined pstats](../../runs/c1b1_gen1_v1/post_default_v3/fast_combined.pstats).

Historical 성과는 당시 source/환경의 결과다:

| 단계 | 당시 직접 CPU 결과 | 당시 FULL |
|---|---|---|
| slow REF | 현재 비교의 보존 기준 | 해당 epoch와 함께 실행 |
| Candidate B 첫 승격 | impulse 1.880×, step 1.475×, 당시 3 trajectories 1.401× | 3713 PASS + 1 strict XFAIL |
| Candidate B runtime activation | six trajectories REF 대비 1.410× | 3744 PASS + 1 strict XFAIL |
| Combined promotion | 같은 campaign REF 대비 1.584×, B 대비 1.122× | 3903 PASS + 1 strict XFAIL |
| Pilot 3 opt-in | 같은 campaign REF 52.90625 / ABCD 27.75초 = 1.906532×; Combined 대비 1.204955× | 4074 PASS + 1 strict XFAIL |

Generation 1은 새 binding 검사를 포함한다. **1.906532×는 이전 source/campaign의 Pilot3 opt-in 결과이며 최종값이 아니다. 최종값은 1.629995×다.** 기존 약 1.9×를 현재 값으로 재사용하거나 historical ratios를 곱하지 않는다. control에서도 기존 guard/numerical pipeline은 유지한다. 짧은 micro sample의 차이를 독립적 전체 overhead로 일반화하지 않는다.

## 미완료·실패 보존과 동결 기준

- `optin_v1`은 큰 exact integer JSON 출력이 Python digit serialization cap에 걸려 미완료. precision/arithmetic cap을 바꾸지 않고 trusted CLI serialization만 허용했다. 해당 로그/INCOMPLETE 표시를 보존했다.
- related 검증 도중 분석 source를 수정해 source-integrity 검사 1 ERROR가 생긴 실행을 보존했다. source를 멈춘 뒤 동일 시험이 통과했다. 해당 ERROR를 PASS 실행으로 세지 않았다.
- JSON 표현 비교의 첫 closure failure와 repair RED/재검사 로그를 보존했다.
- 최종 epoch launcher의 첫 호출은 PYTHONPATH 누락으로 runner import가 실패했다. 측정 stage 실행 전이며 동일 seal에서 workspace import path를 설정해 실행했다.
- `post_default_v1`은 리뷰에서 live manifest의 `producer_inputs` 누락 시 검사를 건너뛰는 경로를 발견해 중단했다. FULL/성능/closure 승인으로 세지 않는다. 필드 누락/빈 값/누락 case를 거부하는 RED4→관련171 PASS를 확인한 뒤 새 v2 source를 봉인했다.
- `post_default_v2`는 actual integration/producer/FULL/CPU가 통과했으나 WORLD dict key `3→3.0` 변경이 Python equality를 통과하는 실제 stale reuse 반례를 재현해 profile 중 중단했다. 이전 FULL/CPU 결과와 partial profile은 보존하고 최종 closure/freeze로 세지 않는다. typed key/value snapshot 및 exact ratio/precision/LN2 type check, type fault RED12→관련183 PASS를 확인했다. numerical 계산식은 바꾸지 않았다.
- finite 표본 밖 모든 input/trajectory의 결정 가능성·물리 정확성, hostile runtime tampering/concurrent mutation, 외부 초기 cache provenance, 컴파일러 출력 해독 경고 원인은 남아 있다. Fraction 완전 제거나 외부 formal proof를 주장하지 않는다.

최종 gate가 PASS했으므로 상태를 `VERIFIED FAST-PATH GENERATION / NOT FORMALLY CERTIFIED`로 확정하고 **Optimization Generation 1만 종료·동결**한다. 추가 병목은 남지만 전체 CPU 절감과 동일 계산/거부 의미를 확보했으므로 현재 Top10을 계속 깎는 작업은 멈춘다. 다음 목표는 설계자의 physics/Foundation 작업이다. **새 Atomic/Electronic workload·규모·하드웨어·representation에서 상위 프로젝트 진행을 실제로 막는 병목이 재확인되고 전체 예상 이득이 충분할 때만**, fresh profile과 별도 Generation 2 승인 범위에서 다시 연다. Pilot 4/다음 후보를 선정하지 않았다.

## 문서 종료 검사와 local commit

2026-10-04 사용자가 세 번 실패한 patch를 반복하지 않고 UTF-8 직접 편집으로 종료·상태 문서를 갱신하도록 승인했다. 계산 source/evidence/result는 수정하지 않고 완료된 값을 옮겼다. 문서 편집 전후 source inventory hash가 위의 `582323351e6dfa29bdf0cc26a9a029b85f3105fc15734433d3234e5724c3f206`와 동일한지 검사하며, 한 byte라도 달라지면 commit하지 않는 조건이다. UTF-8 strict decode, 줄바꿈/문자 깨짐, 문서 link/index, `git diff --check`와 최종 diff를 확인해 local commit으로 정리하는 종료 범위다. 확정 source/evidence byte 불변과 문서 검사 기록은 [closeout validation](../../runs/c1b1_gen1_v1/document_closeout_20261004_validation.json)에 보존한다. commit hash는 자기 문서 안에 순환 삽입하지 않고 별도 [최종 Git/closeout record](../../runs/c1b1_gen1_v1/git_closeout_20261004.json)와 최종 보고에 남긴다. root master는 0f7b744에 남으며 push하지 않는다.

**이번 문서 종료에서는 LOCAL FULL 생략 / 문서 관련 검사로 대체 / 이유:** 계산 source가 기존 FULL/closure와 byte 동일하고 사용자가 재측정을 금지했다. 완료된 4157 PASS + 1 strict XFAIL의 실행 기록을 보존하며 공식 AGENTS 역사 기준선은 갱신하지 않는다.

## 원본 기록 위치

worktree 안 `runs/c1b1_gen1_v1/`의 setup/source audit, RED/green logs, 각 epoch `manifest.json`, inputs, gzip trajectory witnesses, producer raw-check 결과, raw benchmark JSONL, pstats, FULL log/XML/execution, closure를 보존한다. Gitignored evidence는 managed worktree에 남으며 이 문서의 commit만 clone해서 증거 파일까지 자동으로 생기는 것은 아니다. Runtime 계산 자체는 이 ignored 경로나 branch 전용 경로를 필요로 하지 않는다.
