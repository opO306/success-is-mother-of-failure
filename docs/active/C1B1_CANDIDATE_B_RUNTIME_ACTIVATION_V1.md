# C1-B1 Candidate B mainline merge and runtime activation V1

작업 시작 2026-10-02, 실행·판정 2026-10-03. 이 문서는 별도 후보 승격 후의
master 재검증과 실제 runtime 선택기 연결을 기록한다. push 없음.

## 범위와 남은 의무

대상은 production replay producer의 세계 생성 경로다. 별도 세계 서비스·무한 live
pipe·새 확인 controller는 만들지 않았다. REF/FAST의 같은 정수 endpoint 및 저장
전이를 실행 증거로 확인하며, 전체 물리 영역·무한 궤적·모든 입력의 cap 내 판정이나
proof-assistant 검증을 새로 닫지 않는다. A-EV·native J·기존 O-1 STOP은 유지한다.
이번 여섯 궤적을 새 CONFIRMED history로 승격하거나 승인 verifier 조합을 재승인하지 않았다.
기존 high 직접 4건의 별도 checker 미실행, 공유 Python int/Fraction 기반도 그대로다.

## 단계별 결과

| 항목 | 판정 | 근거 |
|---|---|---|
| MAINLINE MERGE | PASS | 6c53eec → 951b076 fast-forward, merge commit 없음 |
| MASTER FULL | PASS | 3713 passed / FAIL0 ERROR0 XFAIL1 actual SKIP0 |
| RUNTIME ACTIVATION | PASS | 별도 selector FAST 기본, explicit reference mode 및 실제 producer 연결 |
| DIFFERENTIAL EQUIVALENCE | PASS | 6개 완주 55,845 step / 실제 거부·STOP 5개; 모든 impulse·저장 상태·종료 상태 일치 |
| POST-ACTIVATION FULL | PASS | 3744 passed / FAIL0 ERROR0 XFAIL1 actual SKIP0 |
| PERFORMANCE | PASS, 아래 측정 범위 | impulse1.600× / step1.410× / 원래3개1.385× / 전체6개1.410× |
| NEW BOTTLENECK PROFILE | PASS | FAST6개 완주233.796875 CPU s, 원본 pstats와 top5 재계산 일치 |
| UNRESOLVED | 유지 | 위 범위·신뢰 기반·프로파일 해석 및 아래 실패 기록 참조 |

## Mainline와 실제 연결

깨끗한 shared checkout에서 H₂ branch를 보존하고 master로 이동했다. fetch 후
master/origin 모두 `6c53eec71e981cef35f850095da76b965457866c`, 후보 merge base도
같았다. `reset --hard origin/master`와 `merge --ff-only codex/c1b1-candidate-b-verified`를
실행해 master를 `951b07695e74abc633168ddb672b11e2289184c9`로 이동했다.
Windows checkout의 507 source-byte 차이는 newline 외 차이가 없음을 확인하고
검토된 candidate worktree 바이트로 복원했다. 모든 기존 Git blob은 그대로다.
master 새 closure/audit/FULL을 실행했으며 다른 worktree의 옛 FULL로 대체하지 않았다.

`a_reference/c1b1_runtime.py`는 `step/impulse`의 기본 FAST와 명시적
`mode='reference'`를 제공한다. `new_run`은 기존 REF 함수 그대로다. mode 오류는
상태를 건드리기 전에 거부한다. 자동 fallback·retry·global patch·cap 변경은 없다.
`tools/c1b1_replay_benchmark.execute()`의 실제 step 지점을 이 선택기로 연결했다.
CLI `executor reference`도 같은 producer를 사용한다. 새 executor batch 비용 기록은
새 UUID 디렉터리를 사용하여 원래 결과를 덮어쓰지 않는다.

slow REF, `_model_R`, energy/potential, `_decide`, proof/checker, historical O-1 producer,
witness-prover wrapper, 물리 상수·profile·dt40·rounding·domain·cap16384는 그대로다.
`step_fast.__code__ is C.step.__code__`; private namespace의 impulse만 FAST다.
저장소 밖 CWD에서 import/AST 합성 및 같은 step 연결도 확인했다. 런타임은 Codex
worktree나 branch 이름을 참조하지 않는다. producer의 기존 raw 입력 위치는 명시된
repo-relative 자산이며 별도의 branch 전용 경로가 아니다.

preserved production 입력 `e10_b0` 하나로 실제 producer를 새로 실행했다.
REF/기본 FAST 각각 **1491 step**, 기존 raw state·J와 전부 일치.
이는 보존 입력을 사용한 새 실행이며 새 trusted origin/확정 history가 아니다.

## 차등 검사와 FULL

| 입력 | E/De | b/Re | 성공 step | 종료 |
|---|---:|---:|---:|---|
| head_on | 9 | 0 | 1564 | outgoing R≥20 |
| oblique | 1/2 | 1 | 6456 | outgoing R≥20 |
| weak | 1/100 | 2 | 26285 | outgoing R≥20 |
| extra_head_on | 1/2 | 0 | 5597 | outgoing R≥20 |
| extra_high_oblique | 5 | 3/2 | 2454 | outgoing R≥20 |
| extra_low_oblique | 1/10 | 3/2 | 13489 | outgoing R≥20 |

같은 초기 raw에서 실제 selector를 거쳐 매 impulse 인수·raw·예외와 매 저장
state/J_cache, 시도·step·최종 상태를 비교했다. trace 계측은 별도 단일 프로세스의
scope에서만 step을 동일 code object의 관측 함수로 연결하고 항상 복원한다.
production runtime 자체는 module globals를 바꾸지 않는다.

domain, initial impulse overflow, stored momentum overflow, stored position overflow,
실제 cap16384 precision STOP의 **5개 시도 모두 attempt1 / committed step0**,
REF/FAST 예외·상태 보존 일치. precision STOP의 매우 큰 합성 dt는 진단용이며
정상 world trajectory나 dt40 계약 변경으로 해석하지 않는다.
정상 impulse55,851회 + 거부/STOP impulse5회 = **55,856회**를 보존했다.

같은 `python -m pytest tests -q -n 6`에 JUnit 출력만 추가했다.

| FULL | PASS | FAIL | ERROR | strict XFAIL | actual SKIP | pytest elapsed | subprocess wall |
|---|---:|---:|---:|---:|---:|---:|---:|
| 병합 직후 master | 3713 | 0 | 0 | 1 | 0 | 717.36 s | 718.871749 s |
| activation 이후 master | 3744 | 0 | 0 | 1 | 0 | 702.25 s | 703.739897 s |

둘 다 warnings25. 기존 compiler-output 해독 경고는 해결하지 않았다.
공식 AGENTS 기준선 3289는 자동 갱신하지 않았다. 31개 증가는 이번 새 시험이다.
새 runtime 시험22개 RED→GREEN, median 위조1개 RED→GREEN; 독립 검토의 history
완전성 결함6개 RED→GREEN 및 changed-refusal/intact-fixture 시험을 추가했다.
최종 31개 관련 시험 PASS 뒤 같은 소스로 두 번째 FULL을 새로 실행했다.

## 적용 후 성능

Ryzen5 5600 / 6 core·12 logical CPU, Python3.12.7 MSC1941 64bit.
한 CPU affinity11, 실행 thread1, 모든 여섯 궤적의 warmup1회, 측정3회,
REF/FAST 순서 교대, 반복별 합계의 median. CPU/wall 원본과 결과 fingerprint를 저장했다.
trajectory는 동일 raw-state collection을 포함하고 admission/hashing은 측정 밖이다.
background load는 통제하지 않았다. 로컬 입력 표본의 결과이며 전체 A 비용이 아니다.

| 범위 | REF median CPU s | FAST median CPU s | CPU speedup | CPU 감소 | 이전 candidate 배율 |
|---|---:|---:|---:|---:|---:|
| impulse1000 | 0.625000 | 0.390625 | 1.600000× | 37.50% | 1.880× |
| 연속 step1000 | 0.859375 | 0.609375 | 1.410256× | 29.09% | 1.475× |
| 기존3개 trajectory 합계 | 32.406250 | 23.406250 | 1.384513× | 27.77% | 1.400761× |
| 전체6개 trajectory 합계 | 53.296875 | 37.812500 | 1.409504× | 29.05% | 비교 대상 없음 |

wall speedup은 순서대로 1.626228 / 1.442912 / 1.383107 / 1.415491×.
예전 배율보다 낮은 항목도 그대로 기록했다. 차이의 원인 분리는 수행하지 않았다.
모든 반복의 raw-state digest·step 수·최종 상태가 REF/FAST와 서로 일치한다.

## 병목 프로파일

완료된 FAST 여섯 궤적의 `time.process_time` cProfile 결과를 여기에 기재한다.
실행기·드리프트·impulse·outgoing 검사 포함, admission/serialization/replay 제외.
계측 overhead가 포함되므로 프로파일 시간을 성능 median으로 재사용하지 않는다.
exclusive CPU를 전체 계측 CPU로 나눠 순위를 정한다. inclusive 값의 중복 합산은 없다.
표의 Amdahl 값은 해당 self cost가 0이 되는 이상적인 상한이며 실현 가능한 예상값이 아니다.

| 계산 | exclusive CPU | 호출 수 | self 비용/호출 | 0비용 가정 전체 상한 |
|---|---:|---:|---:|---:|
| `_impulse_model_R_fast` | 8.8752% | 56,474 | 367.4257 μs | 1.097396× |
| `Fraction.__new__` | 7.2245% | 8,274,470 | 2.0413 μs | 1.077871× |
| `Fraction.forward` | 7.0039% | 8,615,479 | 1.9006 μs | 1.075314× |
| `math.gcd` | 5.2262% | 19,825,340 | 0.6163 μs | 1.055144× |
| `Fraction._mul` | 5.0859% | 4,817,971 | 2.4680 μs | 1.053584× |

전체 계측 CPU233.796875s, 함수 self 합233.531250s. FAST 여섯 최종 상태/step은
차등 증거와 모두 같다. 단일 profile 결과이며 timer/계측 비용 때문에 다른 실행의
절대 시간이나 다른 장비의 순위를 보장하지 않는다.

각 항목의 exact/reference 구분과 현재 중복 가능성:

1. `_impulse_model_R_fast`: FAST의 정확 정수 endpoint derivative 계산이다.
   per-impulse G(M), M별 상수, inverse-power table은 이미 재사용한다.
   전체 impulse 인수 반복은 아래 5회이며 내부 중복 인수의 CPU 기여는 미계측이다.
2. `Fraction.__new__`: REF/FAST 양쪽의 정확 분수 생성이다. 관측된 가장 큰 caller는
   `FixedPoint.to_exact` 3,685,806회다. kick/drift/relative에서 저장 raw의 정확 변환을
   반복한다. 같은 profile/raw의 변환 재사용 가능성은 있지만 절감 CPU는 미계측이다.
3. `Fraction.forward`: 정확 int/Fraction 연산의 공용 dispatch다. 이 입력의 연산은
   float fallback을 쓰지 않는다. REF `_drift`의 exact_new와 displacement가 같은
   atom/component의 p*dt/m를 각각 계산하는 중복이 소스에 있다. 분리 비용은 미계측이다.
4. `math.gcd`: 분수 약분·정규화의 정확 정수 연산이며 공용이다. 위 반복 산술/변환에서
   정규화도 반복될 수 있다. 내부 GCD 인수의 반복 수와 CPU 절감은 아직 측정하지 않았다.
   Fraction 곱은 이미 교차 약분 두 번 뒤 coprime 생성 경로로 마지막 GCD를 생략한다.
5. `Fraction._mul`: FAST interval `_mul`과 구별되는 공용 정확 분수 곱이다.
   REF drift의 p*dt 중복을 확인했다. 교차 약분과 저장·guard의 모든 연산을 유지해야 하며
   같은 정확 값의 재사용을 구현하거나 다음 대상을 선정하지 않았다.

상세 원본 caller 통계와 소스 해시/해석은 별도 `profile_interpretation.json`에 보존했다.
프로파일 원본은 수정하지 않았다. 자기 시간 상한은 서로 곱하거나 더해 적용하지 않는다.
정상 여섯 궤적의 동일 exact dr/dt 입력은 55,851회 중 unique55,846, 반복5회다.
같은 FX96,80·물리·rounding에서 초기 입력 하나가 여섯 번 나온 것이다.
이것은 impulse 전체 인수 반복이며 내부 primitive 중복이나 CPU 절감 측정이 아니다.
새 최적화 대상은 선정하지 않았다.

## 결속·실패 보존·검토

master run `f33c954e-addd-4304-a5ae-33117298e40a`:
source `c3534d1a2437d7d0fe0b6fb12cd7ba93d29e76bd66c8bf06ea0bad287c82dc87`,
input `3a6092587435a7045daba58d3c6f64096e579c434e55431a5e61fbf0c665f5d2`.
activation run `a63addfc-9862-45be-9843-5596897da037`:
source `4789c1d4d7b8fee72c7279b93bb66e36f34a50f6a9a762207e182016f68ba2c7`,
input `453506ce3f782c0cdb46db2afaa7b68737f2971f4496b84a3fd0558de031d122`.
candidate hash `1d0183969752ab37da2dd28ca6b4d18542fc1936b1adc8628c06ba64407731b5`,
checker hash `d9940e4d93369c7c95d55adcc2e5c1f34c676e7995a4348037ec8979d6b463cc`.

원본은 `runs/c1b1_candidate_b_master_gate_v1/`와
`runs/c1b1_candidate_b_activation_v1/`에 있다. 단계별 command/rc/log/hash,
endpoint·정밀도·거부, JUnit, 매 step gzip, benchmark samples, pstats를 보관한다.
이들은 Git 밖의 로컬 증거이며 commit에는 포함하지 않는다.

독립 검토는 read-only로 Critical0 / Important1(history completeness)를 기록했고,
실행 전에 메모리 내 결함 주입으로 문제를 지적했다. 작성자가 RED→GREEN으로
수정하고 fresh FULL로 확인했다. 검토자 자신은 FULL/trajectory/benchmark를
재실행하지 않았다. 기존 Candidate B 수학 증명 전체, 전체 물리 영역, formal 증명은
이번 검토 범위 밖이라는 판단을 유지한다. 기존 수학 전제가 틀렸다면 이번 integration
equality만으로 보완할 수 없다.

수동 import 검사 한 번은 Python default digit limit4300 때문에 큰 진단 분수의
처리를 거부했다. `manual_inspection_diagnostics.json`에 보존했고 CLI와 같은
진단 설정으로 재검증 PASS했다. 정상 dt40 runtime에는 이 설정이 필요 없으며 cap은
바꾸지 않았다. source/assertions의 정상 실행과 Python 정확 정수/Fraction은 신뢰
기반이다. 모든 artifact/hash를 동시에 위조하는 자에 대한 암호학적 실행 증명은 아니다.

## Gitと最終判定

mainline 후보 통합 commit951b076은 새 merge commit을 만들지 않고 유지했다.
runtime 변경은 별도 local commit으로 보존한다. 정확한 종료 HEAD·ahead/behind·dirty는
완료 응답과 `runs/c1b1_candidate_b_activation_v1/final_git_state.json`에서 확인한다.
push하지 않는다. 기존 slow source와 증명/checker/fixture의 Git 변경은 없다.

사용자 요청 전문과 필수 시작 문서를 확인했고 CURRENT_STATE/REPO_MAP은 C1-B1·runtime
관련 범위를 읽었다. 관련 후보/선택기/producer/검사기/드리프트 및 프로파일에 나타난
stdlib Fraction 소스를 읽었다. 전체 저장소나 runs를 통째로 의미 감사하지 않았다.
