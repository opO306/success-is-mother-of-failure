# C1-B1 Pilot 3 결과·승격 검토

최종 상태: **PRODUCTION FAST-PATH CANDIDATE / LOCAL OPT-IN fast_pilot3 / EVIDENCE CLOSURE PASS**.
새 경로는 `fast_pilot3`로 실제 runtime에 연결되어 있다. 기본 mode는 기존 `fast`이며,
REF·Candidate B·Combined·checker/proof를 보존했다. 시작 시 master를 Combined `9ad2ed7`로 FF하고 검증했다.
작업 도중 외부 commit `0f7b744`가 root master/origin에 추가됐다(별도 문서·보존 자료12파일, C1-B1 source 변경0).
그 외부 commit의 FULL을 실행했다고 주장하지 않는다. Pilot3는 `9ad2ed7`에서 분리한 local branch `codex/c1b1-pilot3-rational-preparation`에서만 작업했다. push 없음.

한계부터 기록한다. raw relative 준비는 더 느렸고 raw R²/radius는 일부 조건에서 정수 객체를
더 만든다. 이득의 대부분은 A의 상수 준비다. 표본 exact 비교와 LOCAL FULL은 정식 프로그램
증명·전체 domain·무한 궤적·A-EV/native J·새 replay 승인이나 새 CONFIRMED history가 아니다.
새 최적화와 benchmark는 CPU만 사용했고 표준 FULL의 기존 CUDA/GPU 회귀는 그대로 포함했다.

## BASELINE FRACTION MAP

최적화 코드 작성 전에 실제 여섯 궤적 55,845 step을 계측했다.
주소는 function/source-line 조합 24개이며 실제 파일 line은 19개다.
[주소별 실제 계측 표](C1B1_PILOT3_BASELINE_FRACTION_MAP_V1.md)에 호출 수·denominator·수명·
반복 값·원래 함수 CPU span·정수 폭이 있다. 주소 계수는 기존 production-only cProfile과
하나하나 일치한다. span은 계측 중 원래 함수에 쓴 시간을 나타내며 unprofiled 성능이 아니다.

| 실제 호출 | Combined baseline |
|---|---:|
| Fraction.__new__ | 4,867,919 |
| Fraction._from_coprime_ints | 6,102,424 |
| Fraction 생성 합계 | 10,970,343 |
| Fraction.forward | 5,990,734 |
| Fraction._mul | 3,980,278 |
| math.gcd | 12,615,567 |

baseline_census_v2의 source hash는 `ed37d651e10a995b19ece3a67fee92327fa2b921af86fb61d46633356749285a`.
SQLite에는 실제 exact numerator/denominator byte identity를 남겼다. 반복 값은 답 캐시로 사용하지 않는다.

## DENOMINATOR / VALUE-LIFETIME CLASSIFICATION

world 고정 4주소, run 고정 1주소다. world 고정 주소에서 exact 값 53개가
5,082,660회 생성되었다(전체 생성의 46.330912%).
상대 위치·R²는 step 수명, signed component와 마지막 격자 변환은 component 수명이다.
profile의 scale은 2의 거듭제곱이며 world의 alpha/eta/계수는 일반 유리수다.
정확한 drift endpoint와 segment minimum은 일반 유리수이므로 Fraction으로 유지한다.
[수명별 분류표](C1B1_PILOT3_BASELINE_FRACTION_MAP_V1.md)는 raw와 일반 유리수의 경계를 설명한다.

## CANDIDATE A — CONSTANT PREPARATION

동결 world 계수의 numerator/denominator, c*i, 2*k*c와 RET derivative 계수를 immutable tuple로
한 번 준비했다. alpha/eta의 M별 directed grid endpoints만 bounded cache 8개로 보존한다.
R 또는 trajectory 입력을 답으로 바꾸는 lookup table은 없다.
A 단독 여섯 궤적 CPU median은 28.703125초, Combined 33.4375초 대비 1.164943배다.

## CANDIDATE B — RAW RELATIVE POSITION

canonical FixedPoint에서 rj_raw-ri_raw를 계산한다. 저장 위치의 raw 범위를 넘는 상대값도
정확히 보존하며 위치 profile에 다시 반올림하지 않는다. exact guard용 Fraction view는 유지한다.
공개 RawRelative도 raw/shift/view 일치를 integer crossproduct로 검사한다.
relative 100,000회 준비 CPU는 Combined 0.671875초, ABCD 0.78125초였다.
이 범위는 packet과 Fraction guard view 준비를 포함한다. B 자체의 개선이라고 보고하지 않는다.

## CANDIDATE C — RAW R² / RADIUS

세 raw 좌표의 제곱합 N을 계산하며 exact R²=N/2^(2F)다.
같은 M에서 quotient/remainder와 isqrt로 원래 radius lower/upper를 얻는다.
exact r_min 비교도 integer crossproduct로 유지한다.
실제 trajectory step37의 dyadic 좌표를 쓴 R² 생성+radius 보조 측정 200,000회에서
Combined 1.046875초, ABCD 0.265625초(3.941176배)였다.
주 benchmark의 radius는 이미 계산한 R²/N을 입력으로 하는 kernel만 측정한다.

## CANDIDATE D — RAW IMPULSE FINALIZATION

G*v*dt의 두 끝값을 integer numerator와 positive denominator로 만든다.
정확한 2의 거듭제곱 약분 후 원래 nearest-even 함수를 사용한다.
반올림 위치·축 순서·M 배증/공유·16384 cap·overflow·precision STOP은 같다.
성공한 canonical ABCD whole impulse는 packet 준비 이후 Fraction 생성/gcd 0회를 확인했다.
packet의 exact Fraction view, step drift/guard와 fallback은 이 0회 범위 밖이다.

## EXACT EQUIVALENCE

[조건부 exact 산술 논증](C1B1_PILOT3_EXACT_ARITHMETIC_ARGUMENT_V1.md)과 실행 증거를 별도로 보존했다.
새 물리식·근사·domain 확장·precision cap 확장은 없다.
최종 후보 비교 campaign_v3는 실제 선택된 함수와 실제 하위 함수를 보존해
REF / Candidate B / Combined / A / B / BC / BCD / ABCD를 대조했다.
21개 case, 59,171 성공 step, 59,187 impulse, 59,851 model call,
114,965 component decision에서 실제 endpoint·every raw impulse·displacement·exact drift
endpoint·guard·stored state·final state·exception과 실패 시 비변경 조건이 같았다.
기존 6개 궤적 55,845 step에 새 3축 회전 궤적 3,212 step과 악성 상태를 추가했다.

실제 production selector의 reference/fast/fast_combined/fast_pilot3 네 경로도
post_activation_v1/v2 및 최종 post_activation_v3에서 같은 21개 case를 각각 다시 실행했다.
기존 producer의 별도 7 witness 79,087 step도 세 번의 실제 integration epoch에서 네 경로마다 every stored state와 J가 같았다.
이 producer 검사는 새 independent replay verifier 실행으로 세지 않는다.

## FIXED-M ENDPOINT EQUIVALENCE

fresh fixed_audit_v2의 889개 same-M endpoints:
128/256/512/1024 각 222건, 실제 16384 한 건.
REF·기존 Candidate B·prepared·독립 Fraction checker의 dV/inverse/G/component가 같았다.
raw radius/component는 정확한 dyadic 좌표에만 적용했으며 입력을 새로 반올림하지 않았다.
독립 checker는 executor/profile/candidate를 import하지 않고 frozen parameter를 읽는다.

Fraction path radius trace는 실제 model 반환 뒤 재구성한 필드다.
raw radius는 실제 model 인수다. radius 동일성은 별도 independent same-M 검사로 확인했다.
trajectory equality는 endpoint proof를 대체하지 않는 integration evidence다.

## ROUNDING / REFUSAL

FX corpus 222건: value 215, overflow 6, 실제 16384 STOP 1. raw 적용 가능 99건.
추가 실제 refinement에서 M=512/1024/2048 결정과 128→…→16384 STOP을 확인했다.
이름의 target256/512/1024를 실제 결정 tier라고 읽으면 안 된다.
half-even 양쪽 이웃·양/음·영·minimum raw·정확한 한계·한계 전후·r_min·축 크기 차이·
large integer·stale binding·canonical fallback 시험을 포함한다.
대표 refusal의 step/type/reason/message와 state 비변경은 모든 실제 경로가 같았다.

## MUTATION

scale±1, 빠진 R² 축, radius upper−1, dt numerator, 잘못 재사용한 denominator,
parity/sign 등 실제 잘못된 구현 함수 14개를 독립 checker가 모두 검출했다.
실제 top-level/nested 함수 연결을 잘못 바꾼 경우도 RED→GREEN으로 확인했다.
원래 step code object를 사용하고 성공 뒤에만 state를 commit한다.

최종 review는 산술 오류를 발견하지 않았지만 evidence guard의 누락을 발견했다.
필수 stage/file·run/source/input envelope·profile/allocation inventory, 현재 Python/CPP observer,
actual output hashes와 주 지표 schema를 보강했다. 누락/stale/tampered/bool/negative/wrong-call
fault test를 추가했고 관련240 PASS6.38초, 분리된 reviewer의 guard 수정 검토 승인이다.
현재 관측기로 allocation_audit_v2를 다시 실행해 모든 값·연산·주/부분집합 지표가 v1과 같은 것을 확인했다.

## FRACTION / GCD REDUCTION

실제 production-only profile 6개 궤적 55,845 step에서 얻은 호출 수다.
초기 admission·binding·R20 관측·hash·state retention은 profile 범위 밖이다.

| 호출 | Combined | fast_pilot3 | 감소 |
|---|---:|---:|---:|
| Fraction.__new__ | 4,867,919 | 1,451,988 | 70.1723% |
| Fraction._from_coprime_ints | 6,102,424 | 2,513,025 | 58.8192% |
| Fraction 생성 합계 | 10,970,343 | 3,965,013 | **63.8570%** |
| Fraction.forward | 5,990,734 | 2,401,335 | 59.9158% |
| Fraction._mul | 3,980,278 | 893,520 | 77.5513% |
| math.gcd | 12,615,567 | 5,136,268 | **59.2863%** |

최종 profile의 self/cumulative CPU는 아래 Top10 및 pstats 원문에 기록한다.
계측 총 CPU의 비율을 unprofiled trajectory speedup으로 쓰지 않는다.

## BIGINT HIDDEN COST

CPython3.12 단일 Python thread에서 warmed leaf-call 5,000회씩 실제 OBJ allocator를 관측했다.
관측용 C++는 원래 allocator를 호출하고 종료/exception 뒤 복원한다. 계산 후보가 아니며
production에서 import하지 않는다. 성능 주장은 이 관측기의 시간으로 만들지 않는다.

먼저 모든 실제 heap PyLong 객체/call과 전체 OBJ allocator의 peak live bytes를 비교한다.

| 입력 | old R²→raw R² 객체/call | OBJ peak bytes | old component→raw component 객체/call | OBJ peak bytes |
|---|---:|---:|---:|---:|
| production | 24→29 | 568→536 | 22→5 | 492→156 |
| F150 stress | 42→35 | 928→624 | 20→6 | 616→284 |
| large dt | 54→33 | 864→496 | 38→6 | 556→280 |
| near raw limit | 69→35 | 996→648 | 46→6 | 1508→816 |
| actual M16384 cap | 96→100 | 17776→17808 | 299→118 | 33608→22776 |

raw R²는 production에서 5개, 실제 cap에서 4개 더 할당하며 cap peak도 32 bytes 증가했다.
large dt의 raw component 중간값 최대 최종 폭은 424 bits, old 395 bits보다 29 bits 크다.
반면 component의 일반 Fraction 약분 작업은 큰 폭으로 줄었다.
실제 Python integer opcode count production component는 old multiply10/gcd10에서
raw multiply4/gcd0으로 바뀌었다. raw R²는 square 곱 등 실제 5 integer multiply가 관측됐다.

`bigint_*`는 free/end 시점의 최종 abs_bits>30인 부분집합이다.
그 부분집합의 peak는 모든 임시 정수의 peak가 아니며 mutable gcd scratch의 과거 최대 폭도 아니다.
allocator 요청 bytes와 sys.getsizeof의 논리 digit 크기도 구별한다.
별도 campaign_v3/bigint.json에는 mul/div 비용, reduced/unreduced 폭, 논리 크기와 traced live peak가 있다.
200,000회·warm1000·repeat3의 연산당 CPU median을 별도로 저장했다.

| 입력 | raw integer product us | old Fraction product us | raw round divide us | old reduced round divide us |
|---|---:|---:|---:|---:|
| production | .156250 | 3.203125 | .390625 | .390625 |
| F150 stress | .156250 | 3.046875 | .390625 | .390625 |
| large dt | .156250 | 3.359375 | .468750 | .468750 |
| near raw limit | .312500 | 4.375000 | .703125 | .859375 |

이는 product/rounding 연산의 비용이며 whole impulse/trajectory의 speedup으로 바꾸지 않는다.

actual witness 입력/G endpoint를 exact 재구성한 trajectory_widths에는 여섯 정상 궤적의
raw R² 최대105 bits, radius quotient521 bits, component numerator 최대299 bits,
fixed denominator305 bits를 기록했다. 3축 새 궤적 numerator300 bits,
실제 STOP case quotient32775/component n32721/d32802 bits다.
각 M의 denominator는 해당 run에서 하나로 고정되어 이전 step의 denominator를 이어 곱하지 않는다.
이 자료는 재구성한 operand 폭이며 native allocation count와 섞지 않는다.
측정 범위에서 bigint 누적 폭발은 관측하지 않았고 일반 영역의 scaling 증명은 하지 않았다.

## STEP / TRAJECTORY PERFORMANCE

Ryzen5 5600, 6 physical cores/12 logical threads, Python3.12.7.
CPU worker 1개, logical11 affinity. warm-up micro/step 1,000회, repeat3,
mode 순서를 rotate/reverse, CPU와 wall의 median을 모두 저장했다.
264개 raw sample을 summary 전 별도 JSONL로 flush했다. micro CPU 최소0.234375초이며
허용 floor0.125초 이상이다. admission/bind/hash는 timer 밖, trajectory는 R20 stop/state retention 포함.
main input fingerprint `1100cfdbaef3c79e1a950c5903ddc8b47decaec8ab56302e7780ebecaea833bf`.

| workload / CPU median seconds | slow REF | 기존 Candidate B (fast) | Combined | Pilot3 A | Pilot3 B | BC | BCD | ABCD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| relative 100,000 | .671875 | .671875 | .671875 | .671875 | .750000 | .765625 | .765625 | .781250 |
| radius kernel 1,000,000 | .953125 | .937500 | .921875 | .921875 | .937500 | .875000 | .875000 | .906250 |
| component 100,000 | .718750 | .718750 | .718750 | .718750 | .718750 | .718750 | .265625 | .265625 |
| impulse 5,000 | 3.140625 | 1.875000 | 1.921875 | 1.515625 | 1.875000 | 1.843750 | 1.828125 | 1.406250 |
| step 1,000 | .875000 | .656250 | .531250 | .453125 | .546875 | .546875 | .546875 | .437500 |
| 6 trajectory sum | 52.906250 | 38.609375 | 33.437500 | 28.703125 | 33.343750 | 33.281250 | 32.515625 | **27.750000** |

ABCD/Combined trajectory speedup **1.204955배**, CPU **17.009346% 감소**.
ABCD/slow REF는 같은 캠페인에서 직접 **1.906532배**다. 과거 캠페인 비율을 곱하지 않았다.
ABCD step은 Combined 대비1.214286배, impulse1.366667배다.
A 대비 ABCD의 추가 trajectory 이득은1.034347배/CPU3.320631%이며 대부분의 이득은 A다.
B/BC 단독 전체 이득은 작고 relative 준비는 느리다. 따라서 모두 production 승격하지 않는다.
CPU clock 해상도와 repeat3 표본의 한계를 보존하며 통계적 보편성을 주장하지 않는다.
Combined repeat별 여섯 궤적 합은34.1875/33.4375/33.40625초,
A28.78125/28.5/28.703125초, ABCD27.796875/27.59375/27.75초다.
여섯 case 각각의 median도 모두 Combined보다 낮았으며1.1875～1.222089배 범위였다.
benchmark는 selector 추가 전 isolated ABCD binding이며 actual fast_pilot3는 동일 step code/globals/closure를
사용한다는 activation 시험과 actual four-mode differential로 연결했다. metadata 보강 뒤 재측정한
profile·allocation은 최종 current source에 직접 묶고, 과거 benchmark source hash는 보존했다.

## LOCAL FULL

Combined master fast-forward 뒤: **3903 PASS +1 strict XFAIL**, FAIL/ERROR/실제 SKIP0,
pytest753.62초/process755.643182초, warnings25.
Pilot3 실제 integration 후 첫 FULL(post_activation_v1): **4052 PASS +1 strict XFAIL**,
FAIL/ERROR/실제 SKIP0, pytest720.28초/process721.665858초, warnings32.
실행 중 source hash `db16322b3c8d23387d18f835153866547632a64e7df1b12dde2c11713a10a962` 유지 확인.

첫 guard 보강 뒤 post_activation_v2: **4066 PASS +1 strict XFAIL**, FAIL/ERROR/실제 SKIP0,
pytest816.22초/process817.868429초, warnings25, source e9b1646 유지.
최종 guard와 새 fault test를 포함한 post_activation_v3: **4074 PASS +1 strict XFAIL**,
FAIL/ERROR/실제 SKIP0, pytest823.89초/process825.819696초, warnings25.
최종 source hash `044c7c94655119ea0babca1192b5ddc0ccc46c10cfca0ac66785265221c922ec` 유지,
봉인된4075개 item identity와 JUnit의 항목별 목록도 같다.
기존 CUDA/GPU 회귀를 제외하지 않았다. warning은 기존 cp949 compiler reader-thread 해독 오류이며
빈도25→32→25→25 변화도 기록한다. 해결됐다고 보고하지 않는다. 공식 AGENTS 기준선 숫자는 변경하지 않는다.

## PRODUCTION PROMOTION

`fast_pilot3`는 실제 selector/binder를 통해 ABCD Runtime을 사용한다.
`reference`, 기본 `fast`(Candidate B), `fast_combined`와 함께 명시적으로 선택 가능하다.
slow REF와 _model_R, 기존 differential path, Fraction drift/kick 의미, checker/proof를 바꾸지 않았다.
unsupported Binary64/subclass/override/retired-v1은 기존 Combined 경로로 fallback한다.
standalone impulse의 일반 Fraction dr 인수는 기존 Candidate B로 fallback하며,
실제 canonical runtime binder가 준비한 RawRelative에서 ABCD를 사용한다.

arithmetic/rounding/guard/overflow/refusal·actual trajectory·FULL·measurable CPU reduction·
no observed bigint scaling regression·현재 source/evidence closure를 모두 확인했다.
최종 판정은 **PRODUCTION FAST-PATH CANDIDATE**다.
`post_activation_v3/closure.json`: PASS, source044c7c9, input1100cfd, run9954cc1a,
4074PASS/1strictXFAIL/FAIL·ERROR·실제SKIP0, actual trajectory59171step/producer79087step.
각 stage/file 필수 목록·실행 envelope·raw witness·raw timing samples·pstats·allocation schema와
현재 관측 source/native binary hashes를 실제로 대조했고 저장된 PASS 문자열에 의존하지 않았다.
구상 일치성도 자동 시험과 별도로 재검토했다. 바뀐 것은 같은 exact 값의 저장·연산 형식이다.
세계의 힘·상태 계약·반올림 지점·거부·관측 권한을 바꾸지 않았고 관측기는 state를 조작하지 않는다.
263줄 새 runtime module과 별도 raw arithmetic 검증 의무를 유지하는 비용은 있다.
A 대비 추가3.32%와 전체17.01% 감소를 함께 고려해 opt-in 후보로 판단하며 기본값 전환은 하지 않는다.

## NEW TOP 10 PROFILE

최종 post_activation_v3의 실제 production-only profile. self CPU 비율은 자식 함수 시간을 제외한다.
호출당 비용은 self CPU/calls다. 최대 전체 speedup은 해당 self 시간을 완전히 없앤다는
비현실적 이상 한계1/(1-f)이며 최적화 예측이나 여러 행을 곱하는 근거가 아니다.
profile의 CPU는 계측 오버헤드를 포함한다. 최종 Combined262.343750초/fast_pilot3 161.765625초를
unprofiled speedup으로 쓰지 않는다. 다음 최적화 대상을 선정하지 않는다.

| 계산 | calls | self CPU% | self us/call | 이상 전체 speedup | exact/reference | 중복 가능성의 현재 판정 |
|---|---:|---:|---:|---:|---|---|
| model_prepared | 56,474 | 13.6386 | 390.6665 | 1.1579 | REF 동일 directed endpoint | 입력 R/M에 종속 |
| _taylor_side | 938,650 | 7.3698 | 12.7011 | 1.0796 | REF 동일 directed endpoint | 입력 R/M에 종속 |
| grid _mul | 5,703,874 | 4.3949 | 1.2464 | 1.0460 | REF 동일 directed endpoint | 입력 R/M에 종속 |
| _exp_side | 938,650 | 4.1147 | 7.0913 | 1.0429 | REF 동일 directed endpoint | 입력 R/M에 종속 |
| pair _scale | 5,082,660 | 3.8057 | 1.2112 | 1.0396 | REF 동일 directed endpoint | 상수 pair 반복·interval은 동적 |
| grid _add | 7,341,620 | 3.0619 | 0.6747 | 1.0316 | REF 동일 directed endpoint | 입력 R/M에 종속 |
| Fraction.__new__ | 1,451,988 | 2.9363 | 3.2714 | 1.0303 | exact rational | 실제 guard/drift/view; 제거 가능성 미판정 |
| Fraction.forward | 2,401,335 | 2.8591 | 1.9260 | 1.0294 | exact rational | 실제 guard/drift/view; 제거 가능성 미판정 |
| math.gcd | 5,136,268 | 2.7432 | 0.8640 | 1.0282 | exact integer | 실제 guard/drift/view; 제거 가능성 미판정 |
| Fraction._from_coprime_ints | 2,513,025 | 2.4727 | 1.5917 | 1.0254 | exact rational | 실제 guard/drift/view; 제거 가능성 미판정 |

immutable constants와 같은 M grid는 준비되어 있고 R-dependent 답은 재사용하지 않는다.
pair scale의 n/d는 world 고정이나 directed scale 자체는 interval에 따라 필요하다.
Fraction/gcd의 남은 호출은 실제 exact guard/drift/view 등에서 나온다.
같은 값 반복은 baseline SQLite로 측정했지만 합법적인 제거 가능성은 별도 검토해야 한다.

- forward: calls 5,990,734→2,401,335, self CPU 17.843750→4.625000s, cumulative 83.671875→23.578125s.
- __new__: calls 4,867,919→1,451,988, self CPU 13.781250→4.750000s, cumulative 20.218750→6.750000s.
- _mul: calls 3,980,278→893,520, self CPU 13.765625→3.046875s, cumulative 29.375000→6.218750s.
- _from_coprime_ints: calls 6,102,424→2,513,025, self CPU 10.406250→4.000000s, cumulative 14.593750→6.156250s.
- <built-in method math.gcd>: calls 12,615,567→5,136,268, self CPU 10.500000→4.437500s, cumulative 10.500000→4.437500s.

raw 함수의 현재 비용도 별도로 읽었다.

- decide_raw: 104,535회, self CPU 0.676133%, 10.463003 us/call.
- relative_raw: 111,696회, self CPU 0.840336%, 12.170310 us/call.
- radius_raw: 56,474회, self CPU 0.173863%, 4.980168 us/call.
- component_interval: 105,161회, self CPU 0.251135%, 3.863124 us/call.
- round_operands: 210,322회, self CPU 0.309089%, 2.377307 us/call.

model_prepared가 self CPU 1위로 남았고 Fraction/gcd 부담은 감소했다. 모든 표는 실제 profile_reading.json/pstats 원문에서 계산했다.

## UNRESOLVED

- 정식 프로그램 증명, 전체 물리 영역, 무한 궤적, cap 내 보편적 결정은 미해결이다.
- A-EV/native J/새 independent replay 승인/새 CONFIRMED history/H2는 이번 작업 밖이다.
- Binary64·profile subclass·instance override·retired-v1의 새 최적화는 하지 않았다.
- Linux allocation observer build branch는 추가됐지만 Linux 측정은 하지 않았다.
- 기존 cp949 compiler 경고는 해결되지 않았다.
- baseline observer v1은 비용 때문에 중단했고 partial SQLite/log를 보존했다.
- observer campaign_v1은 재구성 endpoint 비교만 인정, v2는 실제 nested callee 관측 실패로
  INCOMPLETE 보존, 세 번째 수정 뒤 v3 실제 함수를 재실행했다.
- v1 pre-packet 소스의 mixed-newline byte 복구 2회는 실패했으며 old hash에 재결합하지 않았다.
  최종 산술은 fresh fixed_audit_v2/campaign_v3로 다시 실행했다.
- 함수 기본 인수/dispatch/short CPU floor 관련 개발 실패와 corrected raw samples를 보존했다.
- 최종 guard 검토에서 누락/오래된 evidence와 allocation 관측 소스 결합을 보강했다. 최종 guard 수정 검토는 승인됐고 새 실행 결과 gate는 별도다.
- Pilot4 목표 선정·새 GPU/Tensor Core 계산·Vast 사용·이 작업의 push는 하지 않았다.

### 설계자에게 필요한 직접 답

1. 실제 Fraction 생성 주소는 **24개 function/line, 19개 물리 line**이다.
2. world 고정 **4주소**, run 고정 **1주소**다.
3. world 고정 값 생성 **5,082,660회**가 가장 큰 준비 가능 몫이었다. 측정한 최종 전체 생성 감소는
   **7,005,330회**다. 모든 일반 유리수 생성을 없앨 수 있다는 뜻은 아니다.
4. 전체 Fraction 생성 **63.8570%**, gcd **59.2863%** 감소했다.
5. canonical FixedPoint의 raw relative는 **정확히 가능**하다. Fraction guard view는 유지한다.
6. canonical prepared impulse core는 **Fraction 없이 가능**하다. 전체 step/guard/reference는 Fraction을 유지한다.
7. 여섯 trajectory CPU는 **17.0093% 감소**, 같은 캠페인 slow REF 대비 **1.9065배**다.
8. bigint 비용은 0이 아니다. raw R²의 추가 객체/32-byte cap peak와 일부 더 넓은 중간값을 관측했다.
   component 비용 감소가 이를 상회했고 측정 범위에서 step 간 denominator 누적은 없었다.
9. 복잡성까지 고려한 판단은 **ABCD만 local opt-in 후보로 유지**다. 기본값 전환의 근거로 삼지 않는다.
10. 최종 승격·현재 source closure·표준 FULL·guard 수정 review는 **PASS**다.
    기본값은 유지하며 local branch의 명시적 opt-in으로 보존한다.

읽은 범위: 설계자 Pilot3 요청·AGENTS·RULES 및 Pilot3 산술/결과/계측 문서는 전체,
CURRENT_STATE·REPO_MAP·기존 REF/B/Combined/checker는 관련 범위다.
여기 기록한 최종 FULL·production/producer differential·allocation/profile·closure는 새 실행이다.
분리된 reviewer는 코드/증거 구조를 읽고 잘못된 metadata를 메모리에서 재현했으며
FULL·전체 gzip replay·benchmark를 새로 실행한 외부 감사로 세지 않는다.

원문 증거 경로: `runs/c1b1_pilot3_master_gate_v1`(root master),
`runs/c1b1_pilot3_v1/baseline_census_v2`, `fixed_audit_v2`, `campaign_v3`,
`allocation_audit_v1/v2`, `post_activation_v1/v2/v3`(이 worktree).
manifest의 historical source hash를 현재 hash로 다시 써서 같은 실행으로 만들지 않는다.
