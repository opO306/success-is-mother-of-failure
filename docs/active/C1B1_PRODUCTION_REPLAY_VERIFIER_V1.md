# C1-B1 independent replay verifier V1

상태: 구현·로컬 검증 완료, 설계자 정식 승인 대기. 설계자 승인 manifest가 없으면 VALID 계산 결과도 공식
REPLAY_VERIFIED/CONFIRMED로 자동 승격하지 않는다. scratch 결과는 승격하지 않는다.

## 고정 전이 계약

C1-B1 two-atom-v2, Ar40 두 원자, FX(96,48) 위치, FX(96,80) 운동량,
dt=40, retardation ON, round nearest/ties even, drift v2만 지원한다.
원점 초기 admission은 E_rel<=10 De, r_min=1.2 angstrom이다. 중간 구간은
초기 admission을 다시 요구하지 않으며, CONFIRMED 연결은 검증된 이전 끝 상태에
정확히 결합한다. D_valid 분류나 영역 인증은 이 검증의 결론이 아니다.

허용 공유는 동결 사양뿐이다. 퍼텐셜 기존 fingerprint와 전이 전체 fingerprint를
별도로 확인한다. a_reference/a_numeric/engine/audit를 verifier에서 import하지 않는다.
J는 독립 V 식의 forward automatic differentiation과 별도 mpmath interval context로
검증한다. **mpmath 1.3.0 interval 및 Python 정수/Fraction의 올바름은 신뢰 가정**이다.
코드·의존성 fingerprint는 승인과 결과에 결합하며 라이브러리 자체 형식 증명은 하지 않는다.
V1은 mpmath pure-Python backend만 수용한다. 다른 backend는 REFUSED다.

## Witness wire V1 (먼저 고정한 형식)

magic C1BRPV1 newline, 4-byte little-endian JSON header length, canonical UTF-8 JSON,
이후 n_steps개의 record. header에는 schema, spec fingerprint, start_step, n_steps,
initial state(원자 i 위치/운동량, j 위치/운동량 순서의 12 signed raw 정수), initial J,
executor의 final state, 종료 요구 SEGMENT 또는 R20_OUTBOUND가 있다. 큰 정수는
정규 decimal 문자열이다. JSON 부동소수점·중복 key·예상 밖 필드는 거부한다.

record = 다음 J의 3개 canonical signed zigzag varint + state residual tag.
tag 0은 독립 정수 전이로 재구성한 상태와 executor 기록의 12 raw가 모두 같다는
무손실 표현이다. tag 1은 12 signed residual varint를 보존한다. 매 step의 executor
상태를 단지 마지막 hash로 비교하지 않고 정확한 raw 정수로 비교한다. 정상 witness는
초기 상태+각 J+0 tag이며, 오류가 있는 executor 기록도 residual로 손실 없이 보존한다.
모든 raw는 signed96, residual은 두 signed96 차이, varint는 최대14 bytes,
header 최대16 KiB다. 뒤의 여분 bytes/비정규 encoding은 INVALID다.

## 검증과 판정

첫 J와 각 후속 J의 real enclosure가 해당 ties-even rounding cell에 포함됨을 확인한다.
각 kick, displacement rounding, displacement와 저장값 overflow, **unrounded drift
선분 전체**의 r_min, 저장 위치 r_min, 두 번째 kick, executor claimed state를 확인한다.
검증 성공한 이전 상태만 다음 전이의 trusted 입력이다. event-only 대체는 없다.

VALID: 선언한 구간의 모든 전이와 executor raw equality 및 종료 요구가 검증됨.
INVALID: malformed witness, 금지 상태/전이, 정확한 불일치, disjoint J rounding cell.
REFUSED: 미지원 사양, 의존성 문제, precision/step/byte/evaluation/time 자원 한도,
불완전 witness, 또는 선언된 outbound 종료에 도달하지 못함. REFUSED는 INVALID가 아니다.

## 보존·streaming·history

streaming은 header+현재 trusted state+J+한 record만 유지한다. 전체 witness 원본을
content-addressed 파일로 보존해야 제3자가 재검증할 수 있다. 결과 summary와
fingerprint만으로 전체 trajectory를 재검증할 수 없으며 증거 원본 대체 금지다.
full replay는 같은 checker에 materialized input을 전달한다. 병렬 실행은 서로 다른
독립 구간/trajectory 검증만 병렬화하고 trusted 전이 순서를 유지한다.
V1 wire header는 구간 길이·최종 claim을 미리 포함하므로 완료된 TEMP 구간의 파일/stream
재검증을 지원한다. 아직 종료 시각을 모르는 무한 live executor pipe의 framing과 runtime
동시 배선은 미구현이다. time cap은 전이/평가/입력 chunk 사이에서 확인하는 cooperative
한도이며, 막힌 외부 stream read나 단일 backend 호출을 OS 수준으로 강제 중단하지 않는다.

최소 history는 retained speculative witness queue, trusted origin, 마지막 confirmed
상태, verdict를 유지한다. 승인 manifest가 현재 spec/implementation/dependency에
일치하고 VALID일 때만 REPLAY_VERIFIED→CONFIRMED. INVALID이면 마지막 confirmed
뒤 모든 queue 항목을 DISCARDED로 보존하고 halt한다. REFUSED는 SPECULATIVE로
남으며 자동 재실행하지 않는다. 운영 세계 rollback, Proof Cache, native J, O-3는 범위 밖이다.

## 승인 조건 및 한계

전체 step 검증, 독립 import 검사, 정상/영구 결함주입/자원 한도/streaming 일치 시험,
7개 기존 trajectory에 대한 새 검증과 비용 기록, LOCAL FULL을 승인 자료로 제출한다.
형식 증명, 임의 many-body, 전체 미래 완주, 실제 세계/실험과 일치, mpmath 무결성
자체의 증명은 이 결과로 얻지 못한다. A-EV의 방법 건전성 의무를 대체하지 않는다.


## 2026-10-01 구현·검증 기록

Git 시작: HEAD=origin/master=`ac143855bec21352aaa86241b31baf86d6075eae`.
기존 문서 13개만 별도로 검증·commit한 `c85beb5627f9179fcf8eb42e1f4d96fb2fe76c1a`
뒤 깨끗한 tree에서 구현했다. 문서 단계 `git diff --check`, body freeze 3 passed,
로컬 링크 신규 깨짐 0. CURRENT_STATE의 기존 pseudo link 하나는 역사 문구로 보존했다.
기존 실행기·동결 fixture·물리 계약 변경은 0, push는 하지 않는다.

구현 파일: `c1b1_replay/{spec,types,exact,model,witness,verify,provenance,history,__main__}.py`,
package entry point, `tests/test_c1b1_replay.py`, 신규 raw-window test fixture,
`tools/c1b1_replay_benchmark.py`. 실제 executor의 생성·계측은 도구에만 있고
verifier 결정 경로에는 없다. A-EV/Proof Cache/native J/공식 O-3는 이번 작업에서 실행·변경하지 않았다.

### 의존성·fingerprint·독립성

공유 사양: Ar40 질량, dt, potential decimal parameters와 retardation,
FX width/fraction bits, nearest-ties-even, drift v2, r_min, 최초 E<=10 De,
16384-bit cap. 공유 구현 의존성은 Python 표준 라이브러리(정수·Fraction 포함)뿐이며
J/enclosure는 mpmath 1.3.0 pure-Python + fresh AD다. 독립 per-precision interval
context를 사용하고 state-dependent R²는 캐시하지 않는다.

AST 검사 `a_reference/a_numeric/engine/audit` import 0. 별도 Python 프로세스와
모든 benchmark verifier worker의 sys.modules에서도 금지 import 0.
동결 사양 비교 시험이 원 실행기 mass/r_min/De/퍼텐셜 fingerprint 일치를 확인했다.

- C1-A parameter fingerprint: `ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e`.
- 전이/witness spec fingerprint: `87a049429ac8f83f3cf43b1ea8ce745505fc2e0135fd1bc2a125200a88b92209`.
- 구현 fingerprint: `dcaa2214124cee485978dfa9845d35461ae50d3023f9eeececb7a61cb5c1a788`.
- 의존성 fingerprint: `0d0d896374cc7fb36da3398b398b204d2e25fcd5fcea5577924345b28b973ec7`.

의존성 fingerprint는 Python 구현/버전, mpmath 버전/backend 및 mpmath .py 소스 전체에
결합한다. 구현 fingerprint는 package 소스 전체에 결합한다(LF canonical bytes).
mpmath interval 및 Python 산술 의미는 신뢰 기반이며 이 hash가 수학적 건전성을
증명하지 않는다. 승인 decision이 빈 candidate manifest는 승인이 아니다.

### 7개 전체 궤적의 새 결과와 비용

scratch JSON은 등급 없는 raw 입력으로만 사용했다. 변경하지 않은 reference executor로
7개를 다시 실행해 **매 상태 및 J가 원 raw 입력과 정확히 일치**함을 확인했다.
그 입력을 V1 witness로 무손실 변환하고 production checker가 새로 모든 step을 검증했다.
아래 VALID는 계산 판정이며 승인 전 REPLAY_VERIFIED/CONFIRMED 역사로 승격하지 않는다.

| 입력 | step | executor CPU s | streaming verifier CPU s | CPU 비율 | witness B | stream/full |
|---|---:|---:|---:|---:|---:|---|
| e0.5_rho-0.01 | 13,093 | 18.062 | 50.094 | 2.773 | 296,807 | VALID / VALID |
| e0.5_rho-0.005 | 14,367 | 20.078 | 55.016 | 2.740 | 324,353 | VALID / VALID |
| e0.15_rho-0.005 | 26,451 | 36.047 | 100.594 | 2.791 | 586,820 | VALID / VALID |
| e1_b10 | 7,221 | 9.938 | 27.406 | 2.758 | 163,657 | VALID / VALID |
| e0.5_b6 | 6,162 | 8.688 | 23.766 | 2.736 | 137,928 | VALID / VALID |
| e0.5_rho+0.005 | 10,302 | 14.656 | 41.156 | 2.808 | 227,201 | VALID / VALID |
| e10_b0 | 1,491 | 2.156 | 5.984 | 2.775 | 20,576 | VALID / VALID |

총 79,087 step. J interval 평가 79,094회(각 initial J 포함), 모두 128 bit에서 결정.
stream/full 7/7의 verdict·step 수·마지막 12 raw·원본 witness SHA·구현/의존성 fingerprint가
정확히 같다. 통과한 모든 intermediate state도 각 record에서 비교했다.

같은 로컬 기계, 같은 7개, **executor/verifier 양쪽 모두 4-worker**:

- executor 총 step CPU 109.625s, batch wall 40.952s.
- streaming verifier CPU 304.016s, batch wall 103.905s.
- streaming CPU 비율 2.773, 병렬 batch wall 비율 2.537.
- full verifier CPU 300.828s, batch wall 102.761s.
- full CPU 비율 2.744, 병렬 batch wall 비율 2.509.

executor CPU는 step 호출을 측정하고 원본 비교·JSON 읽기는 제외했다. verifier CPU는
파싱·fingerprint·엄밀 검증 전체다. batch wall은 프로세스 시작과 producer 비교/읽기도
포함한다. 개별 trajectory step을 병렬화한 수치나 단일 executor 대비 verifier 4-worker
속도라고 해석하지 않는다. 제어기 RSS sampler의 CPU는 별도로 parent에 기록했다.
반복 측정의 신뢰구간이나 장기 처리량 예측은 이번에 얻지 않았다.

witness 총 1,757,342 B, 평균 22.220 B/step.
기존 survey JSON(상태+J+진단) 총 24,854,334 B와 내용 범위를 구분한다.
결과 summary는 880〜970 B이며 **재검증 원본이 아니다**.
stream worker OS peak working set 28.18〜29.95 MiB.
50ms 간격으로 부모+4-worker RSS를 합산한 표본 peak는 executor 188.83 MiB,
stream 145.64 MiB, full 148.60 MiB다.
RSS는 Python/라이브러리·제어기 비용도 포함하며 50ms보다 짧은 peak를 놓칠 수 있다.

원본·원본 hash·새 witness·양 방식 결과·CPU/메모리 batch 기록은
`runs/c1b1_production_replay_20261001/`에 보존한다(Git 제외, 현재 장치의 로컬 증거).
원본을 삭제하고 summary만 남기면 제3자 전체 재검증이 불가능하다.

### 영구 결함주입 및 최소 history

scratch 12행은 결함 11종+정상 control 1행이었다. 모두 보존하고 미분 경로 결함을
추가해 **결함 12종**을 영구 시험했다. 12/12가 기대 verdict와 일치한다.

| 결함 | 기대/실제 |
|---|---|
| turning Jx +1 ulp, 상태 그대로 | INVALID |
| turning Jx +1 ulp, 이후 상태 일관 재구성 | INVALID |
| recross Jy -1 ulp, 이후 상태 일관 위조 | INVALID |
| dr_z=0에서 Jz=1 | INVALID |
| 원자 j 위치 +1 raw | INVALID |
| 원자 i 운동량 +1 raw | INVALID |
| 출구 60 step 전 종료 | REFUSED |
| verifier QED short 항 누락 | INVALID |
| verifier BO C6 끝자리 +1e-7 | INVALID |
| verifier half-kick dt/4 | INVALID |
| verifier force 부호 반전 | INVALID |
| 추가: verifier AD 미분을 0으로 변경 | INVALID |

정상 control은 VALID. step/byte/evaluation/precision/time cap은 REFUSED.
비정규 encoding, raw 범위·overflow, unrounded chord guard, 최초 energy admission,
지원 밖 version/backend, 불완전 입력, 보존 파일 대체도 구분해 시험했다.
streaming 상수 캐시가 상태 수에 따라 늘지 않는 회귀 시험도 포함한다.
관련 시험: `test_c1b1_replay.py` + `test_c1b1_step_fail_closed.py` + body freeze:
**60 passed in 5.25s**. 최종 LOCAL FULL은 아래 별도 기록으로 갱신한다.

history 시험에서 synthetic TEST ONLY approval을 써서 VALID→REPLAY_VERIFIED→CONFIRMED,
미승인/오래된 approval→SPECULATIVE 유지, REFUSED→미확정 유지,
INVALID→마지막 CONFIRMED 뒤 자손 전부 DISCARDED를 확인했다.
보존 witness root/start_step/content identity를 검사하고 마지막 CONFIRMED를 보존한다.
중단 뒤 자동 검증 재시도·자동 executor 재실행은 없다. 실제 세계 상태 commit은 하지 않았다.

### 수정·한계·다음 최소 작업

초기 계측에서 R²를 상수 캐시에 넣어 메모리가 길이에 비례하는 결함을 발견했다.
수정과 회귀 시험 후 두 방식의 7개 전체 검증을 모두 다시 실행했으며 위 수치는 최종
fingerprint의 완료 결과뿐이다. 수정 전에 중단한 full-replay 비용 계측은 완료 증거가 아니다.

계약에 맞는 특정 궤적을 독립 재검증하는 구조가 구현됐다. 정확한 history에는 모든 step이
필요하며 event-only 대체·짧은 summary 증명은 구현하지 않았다. 구간 단위 증거 연결은
모든 step 검증을 유지한다. 비용은 executor보다 약 2.8배 CPU이며 무료 검증이 아니다.
S4d의 모든 미래 worst-case closure를 요구하지 않고 실제 이력만 검증하지만,
D_valid 전체·future completeness·Safety/Liveness 형식 인증을 얻은 것은 아니다.

아직 남은 것: 설계자 승인, A-EV 별도 건전성 의무, 지원 밖 profile/spec/many-body,
unknown-length live pipe, 운영 세계 장기 rollback·복구 제어기, 강제 OS resource isolation.
Energy Bound v0 APPROVED / ④-Liveness NotCertified / ④-Safety Conditional / A-EV unresolved 유지.
native J는 별도 Gate이며 공식 O-3는 승인 후 CONFIRMED 궤적만 사용한다.

다음 최소 작업은 이 계약·신뢰 기반·비용과 최종 회귀 로그를 설계자가 검토해
특정 spec/implementation/dependency fingerprint를 승인하는 것이다. 그 이후에만
새 운영 witness를 승인된 checker로 검증하여 최소 C1-B1 history에 확정한다.


### 자동 시험과 별도의 구상 일치성 점검

AGENTS.md/RULES.md를 읽고 CURRENT_STATE/REPO_MAP의 활성 구간 및 관련 사양을 대조했다.
reference의 계약·KDK 전이와 scratch verifier/결함주입 경로를 읽었으며,
관련 없는 계통과 runs 전체는 탐색하지 않았다.

세계 실행기에는 verifier import/승인 요청/새 물리가 들어가지 않았다. J 및 전이 판정은
독립 경로이며, prefix를 확인한 다음에만 trusted state를 전진한다. 최소 history는
승인 여부·전체 VALID·원본 보존·확정 origin 결합을 모두 요구한다. INVALID 자손 폐기와
REFUSED 미확정은 다른 가지다. 자동 재실행·event shortcut·캐시 승격은 없다.
이것은 세 층 분리 구상과 일치한다. 운영 세계 controller의 양측 정지·장기 복구 및
history.enqueue의 streaming 입력 배선은 아직 범위 밖이며, 현재 enqueue는 immutable
bytes 입력을 파일로 보존한다. verifier의 file/stream 검증 API와 이를 구분한다.


### 최종 LOCAL FULL (이번에 새로 실행)

`python -m pytest tests -q -n 6` + JUnit 기록: **3433 passed, 1 strict xfailed,
실제 skip 0, failure/error 0, exit 0, pytest 736.56s**(wrapper 738.27s).
JUnit tests 3434 / skipped 1은 고정된 binary64 절대 위치 탈락 strict xfail이다.
새 replay 시험 49개가 모두 통과했고 관련 묶음 60개와 구별한다.
공식 AGENTS 기준선 3289 이후의 증가 144 = 이번 신규 49 + 기존 코드에 있던 순증 95다.
그 95개를 이번 verifier에서 만든 시험으로 계산하지 않는다(기존 six test files의 Git
1636b1d→ac14385 차이). 중간 LOCAL FULL 3333 이력도 CURRENT_STATE에 이미 있으며
그 결과를 새로 실행했다고 세지 않는다. **공식 AGENTS 기준선은 설계자 판정 없이
갱신하지 않았다.**

기존 native(CPU/CUDA) 시험의 subprocess 출력 cp949 해독 경고 25건이 남았다.
새 replay 시험의 경고가 아니며 기존 compiler/출력 경로는 이번에 수정하지 않았다.
원인 조사·해결로 보고하지 않는다. 원문 log/JUnit은 위 runs 경로에 보존했다.
동결 body contract와 기존 물리/fixture는 그대로이고 문서 링크 신규 깨짐 0,
최종 staged diff check를 별도로 확인한다. 이 완료 결과로 C1-B1 전체 Gate나
A-EV/Safety/Liveness를 승격하지 않는다.
