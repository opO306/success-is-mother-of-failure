# C1-B1 Candidate B 승격 검증 V1

2026-10-02. 공식 최적화 트랙. H₂/Atomic-Electronic Foundation과 분리.

## 한계와 판정

**PRODUCTION FAST-PATH CANDIDATE.** 요청한 10개 stage가 같은 run/source/input에서 returncode 0,
최종 promotion 검사 PASS다. slow REF를 보존한 별도 명시적 선택 경로로 제공한다.
동일 원본 프로그램의 정수 결과를 적은 계산으로 재현하는 후보다. 새 물리 검증·formal certification,
A 전체 speedup, 모든 입력의 cap 내 결정 또는 C1-B1 전체 Gate 종료를 뜻하지 않는다.
독립 checker도 Python int/Fraction/isqrt와 의도한 수학 명세를 공유한다.
고정밀 직접 4건은 checker 없이 REF/A/B/FAST 비교이며 adaptive 실제 cap STOP은 checker도 검사했다.
기존 generic model·energy·potential·slow step을 보존하고 별도 impulse/step_fast를 제공한다.
기본 executor를 자동 변경하지 않는다.

| 상태 | 최종 증거 |
|---|---|
| EVIDENCE CLOSURE | PASS, 같은 run/source/input의 실제 6개 subprocess |
| PRIMITIVE AUDIT | PASS, 독립 소스 검토·새 재검산·worktree 줄바꿈 재검토 |
| CANONICAL EQUIVALENCE | PASS, primitive lemmas + live AST + 80 fixed/4 high/1,081 adaptive cases |
| LOCAL FULL | PASS, 3713 passed + 1 strict xfailed, failure/error/actual skip 0 |
| TRAJECTORY DIFFERENTIAL | PASS, 산란 3개 34,305 step 및 실제 거부 4개 |
| PERFORMANCE | COMPLETED, CPU median impulse 1.880× / step 1.475× / trajectory 1.400761× |
| PRODUCTION PROMOTION | PRODUCTION FAST-PATH CANDIDATE, 기본 경로 자동 변경 없음 |
| UNRESOLVED | formal/global physical certification, A-EV·native J·전체 C1-B1 Gate는 별도 |

## 구현과 개념 일치성

목적은 기존 C1-B1 impulse의 바로 그 endpoint/raw J를 얻는 것이다.
물리 EXP 9개와 모든 dV 항을 유지하며 반환에 쓰이지 않는 EXP 방향과 V-only 누적을 제거했다.
정수 power는 반올림 전에 공유하고, 부호별 곱셈 극값·양수 분모 극값·one-isqrt를 사용한다.
분모와 radius가 양의 순서 있는 구간이라는 전제를 실행 guard로 명시했다.
새 cutoff·surrogate·ML·GPU 경로, 매개변수·rounding·production cap 변경은 없다.

`a_reference/c1b1_fast_impulse.py`의 `_impulse_model_R_fast`는 dV/inv1만 반환한다.
V가 필요한 energy bound/domain proof/potential 진단은 기존 `_model_R`를 사용한다.
`step_fast`는 원본 step의 code object와 같은 helper 객체를 쓰고 private namespace의 impulse만 바꾼다.
원본 모듈을 monkeypatch하지 않는다. 자동 시험 외의 개념 검토는
[독립 primitive 감사](C1B1_CANDIDATE_B_PRIMITIVE_AUDIT_V1.md)의 noninterference·합성 논증으로 수행했다.

## 증거 결합과 비교 결과

최종 run: `runs/c1b1_candidate_b_promotion_v3/` (Git 밖, 관리 worktree에 보존).

```text
run_id       3e404fde-e116-4248-ba00-7d78c6244f2f
Git parent   6c53eec71e981cef35f850095da76b965457866c
source_hash  c3534d1a2437d7d0fe0b6fb12cd7ba93d29e76bd66c8bf06ea0bad287c82dc87
input_hash   3a6092587435a7045daba58d3c6f64096e579c434e55431a5e61fbf0c665f5d2
B SHA256     1d0183969752ab37da2dd28ca6b4d18542fc1936b1adc8628c06ba64407731b5
checker SHA  d9940e4d93369c7c95d55adcc2e5c1f34c676e7995a4348037ec8979d6b463cc
```

manifest에는 source inventory·Git index blobs·환경·각 stage의 실제 command/rc/output SHA가 있다.
검사 집합은 caller가 고정하고 exact command/check schema 및 필수 상세 파일/coverage까지 확인한다.
`run_pilot.py --stage summarize --promotion`은 저장된 PASS 플래그를 믿지 않고 이를 다시 검사한다.
source/input 변경·미실행·누락·빈/중복 기록·오래된 JSON 혼합은 INCOMPLETE, 실제 실패는 FAIL이다.
암호학적인 실행 증명 또는 모든 기록·해시를 함께 위조하는 공격의 방어는 아니다.
normal Python/assertions 활성 환경을 전제로 하며 reviewer 승인 bytes를 바꾸면 새 감사와 run이 필요하다.

- 저장 Pilot 입력 178개 + 악성 입력 51개 = 229개. midpoint dt는 impulse 진단용이다.
- REF/A/B/FAST/checker의 actual dV/inv1/F_over_R, raw J/거부, M 및 decision sequence: 1,081 조합 일치.
- 값 1,036 / physics domain 35 / overflow 9 / cap STOP 1.
- refinement: M128만 486, 128→256 472, →512 65, →1024 11, →2048 1, →16384 1; model 미호출 45.
- fixed M128/256/512/1024: sqrt 경유 + widened radius, ret on/off, 80건 실제 endpoint 보존.
- high M2048/4096/8192/16384: 4건 endpoint와 실제 F/R canonical SHA 보존.
- 실행 결함 8개 검출: EXP lower ±1, sqrt upper -1, inverse power 오염, dV 삭제,
  sign branch, division 방향, 탈락한 rounded reciprocal recurrence.
- 역사 reciprocal 반례의 dV lower -490 / upper +64 차이 재현. 최종 J가 같은 경우도 endpoint에서 거부.
- Candidate B 관련 시험 47 passed / 95.43초, 격리 시작의 C1-A freeze 3 passed / 0.63초.

## 전체 시험 및 실제 궤적

LOCAL FULL: `python -m pytest tests -q -n 6 --junitxml ...` 완료.
**3713 passed + 1 strict xfailed, failure/error/actual skip 0, pytest 774.77초**
(subprocess wall 776.175486초). 기존 cp949 compiler-output reader 경고 25건은 미해결로 보존한다.
공식 3289 대비 +424이며 그 전 여러 단계의 추가 시험을 합쳐 확인한 숫자다. 이번 신규 시험은 47개다.
공식 AGENTS 기준선 3289 passed + 1 strict xfailed / 실제 skip 0은 갱신하지 않는다.
로그·JUnit은 같은 run의 `local_full.pytest.log`·`local_full.junit.xml`에 저장한다.
병행 H₂ 신규 untracked 작업은 격리 폴더로 가져오지 않았다. 시작 HEAD에 이미 있던 시험은 포함한다.

사전 봉인한 실제 산란은 원본 dt40, 위치 FX96/48, 운동량 FX96/80,
e/De=9 b/Re=0; e/De=1/2 b/Re=1; e/De=1/100 b/Re=2.
canonical 초기 상태에서 출발해 outgoing R≥20 및 dr·dp>0까지 모든 step을 비교한다.
무한 시간 tail 또는 세계 전체 궤적을 측정하는 것은 아니다. 임의 step cap 도달은 PASS가 아니다.
각 impulse 인수/raw 결과와 매 stored state/J cache, 실제 예외·실패 후 상태를 gzip JSONL로 보존한다.
추가 domain·impulse overflow·stored momentum overflow·stored position overflow 4개도 같은 방식으로 기록한다.
실제 결과: 정면 1,564 / 비스듬한 산란 6,456 / 약한 산란 26,285 step, 합계 **34,305 step**.
세 궤적 모두 outgoing R20에 도달했고 34,308 impulse 비교가 일치했다(첫 step의 2회 호출 포함).
추가 거부 4개의 실제 impulse 4회도 일치했으며 attempted step=1, committed steps=0,
예외 type/reason/message와 실패 후 raw state 보존을 확인했다. 전체 **34,312 impulse** 비교다.
momentum/position overflow는 기존 `_limit`가 VMHalt를 ExecutorLimitExceeded로 감싸는 실제 계약이다.
pytest의 cap128 fault rehearsal은 실제 production cap16384 STOP과 별도로 구분한다.

## 성능 측정

로컬 AMD Ryzen 5 5600 6-Core / 12 logical CPU, Python 3.12.7,
CPU affinity logical 11 한 개·thread 1, warm-up 1회, 반복 3회, 실행 순서 교대, median CPU/wall 시간.
impulse 1000회는 head-on 초기 입력 한 개, step 1000회는 실제 연속 실행이다.
trajectory는 위 세 산란 전체를 각 반복에 실행한다.
trajectory 시간에는 동일 raw-state 수집을 포함하고 admission·hashing은 제외한다.
동일 결과 digest와 실행 걸음 수를 확인하며 background load는 통제되지 않은 로컬 측정이다.
Pilot의 1.680×/40.47%는 이번 전체 trajectory 성능으로 사용하지 않는다.

| workload | REF median CPU | FAST median CPU | CPU speedup | CPU 시간 감소 | wall speedup |
|---|---|---|---|---|---|
| impulse 1,000회 | 0.734375 s | 0.390625 s | 1.880× | 46.81% | 1.914× |
| 연속 step 1,000회 | 0.921875 s | 0.625000 s | 1.475× | 32.20% | 1.493× |
| 세 완주 trajectory 합계/반복 | 34.515625 s | 24.640625 s | 1.400761× | 28.61% | 1.401293× |

trajectory median wall은 REF 34.7727965 s / FAST 24.8147995 s.
모든 반복과 REF/FAST의 raw-state digest·걸음 수가 같았다. 3개 표본 전체 비용의 로컬 median이며
모든 입력·모든 A 작업·admission까지 포함한 성능으로 일반화하지 않는다. GPU 최적화·측정 없음.

## 최종 질문에 대한 답

1. exact/canonical equivalence: 전제 아래 primitive 정수 항등식·live AST 합성 논증과
   80 fixed/4 high/1,081 adaptive 비교까지. 전체 프로그램의 proof-assistant 인증은 아니다.
2. 기존 evidence 문제: 하나의 fresh run에서 실제 command/rc/output/source/input 결합 및
   상세 coverage 검사를 닫았다. 모든 record/hash의 악의적 동시 위조에 대한 실행 증명은 범위 밖이다.
3. repository 재현: production FAST의 AST/primitive/step code 연결 및 실제 raw-state 비교 PASS.
4. LOCAL FULL: 3713 passed + 1 strict xfailed / failure/error/actual skip 0. 최초 실패도 보존했다.
5. refusal/overflow: adaptive panel·실제 거부 4개에서 같은 결과·걸음·실패 후 상태.
   실제 cap16384 STOP도 같고 test cap128 rehearsal과 구별했다.
6. 전체 trajectory 속도: 선정한 R20 출구까지 3개 완주 workload 합계 CPU 1.400761×, 28.61% 절감.
7. correctness gap: proof-assistant 검증·물리 soundness·A 전체/무한 tail 인증·모든 입력의
   cap 내 결정은 미해결/별도 범위. 승인된 production replay verifier의 지정 조합은 재승인하지 않았다.
   high 직접 4건의 checker 미실행과 공통 Python 기반도 명시한다.
8. 승격: 요청한 candidate 조건은 모두 충족한다. 별도 `impulse/step_fast`를 제공하고 slow REF를
   보존한다. 기본 executor·C1-B1 전체 Gate·A-EV·native J 상태를 자동 승격하지 않는다.

최종 raw 증거는 같은 run의 manifest, closure, promotion_decision, 10개 stage log/result,
endpoint JSON/JSONL, JUnit, trajectory gzip 및 benchmark samples에 보존했다.

## 읽기 범위

사용자 요청 첨부는 전문을 읽었다. 필수 시작 문서 AGENTS/RULES/CURRENT_STATE/REPO_MAP를
확인하고 현재 C1-B1·검증·경로 항목을 중심으로 분할 열람했다. 관련 후보/primitive/checker와
model/impulse/step 연산은 source·AST 및 실행으로 검토했다. historical runs는 지정한 결과와
봉인 manifest가 열거한 artifact만 읽었으며 전 저장소의 의미 감사는 하지 않았다.

## 실패·중간 기록과 Git

처음 root HEAD/origin은 모두 6c53eec…; clean / ahead0 behind0. fetch origin 성공, push 없음.
root의 감사 전 closure 및 이후 worktree promotion_v1은 보존하며 최종 승격에 합치지 않는다.
강화 도중 import 목록의 순서 오류를 고쳤고, 관련 시험 도중 source 변화를 감지한 실행은 완료된 FULL이 아니다.
root에서 병행 H₂ 파일의 실제 source 변경을 두 번 감지해 그 실행을 통과로 인정하지 않았다.
`using-git-worktrees`로 시작 HEAD에서 관리 worktree를 만든 뒤 우리 변경만 복사했다.
worktree checkout의 원본 두 파일은 root LF→CRLF 차이만 있었지만 raw SHA가 달랐다.
독립 splitlines·전체 AST·Git blob 재감사 후 v2를 실행했지만 FULL은 아래 환경 누락으로 실패했다.
v2 FULL: **3711 passed / 2 failed / 1 strict xfailed / 실제 skip 0 / 25 warnings / 699.86초**.
두 실패는 `test_real_package_roundtrip_and_tamper_refusal` 및
`test_stored_reference_uses_exact_raw_outlet_not_display_float`의 FileNotFoundError였다.
배포 묶음 1개·O-1 봉인 artifacts 97개·기존 source newline bytes 93개를 기존 seal의 hash대로
복원했다(191개). 기존 file에 newline 외 차이가 있거나 원본 hash가 다르면 복사를 거부했다.
Git상의 기존 코드 변경은 없고, 관련 두 시험 재실행은 **2 passed / 16.60초**였다.
reviewer가 첫 감사의 21개 SHA와 모두 같음을 확인하고 primitive/AST/합성을 다시 실행해 PASS했다.
복원된 LF bytes를 고정한 **fresh v3**만 최종 승격에 사용한다.
metadata: `runs/c1b1_candidate_b_environment_restoration_v1.json`,
SHA256 `f87dd5163eb726655c6bf3aa31c29345a47c40f9e1d25a20548a34e9e852bccf`.
첫 FULL과 경고를 보존하며, cp949 compiler-output reader 경고 원인은 이번 범위에서 해결하지 않았다.
원래 다운로드·historical fixture/source와 실패 기록은 덮어쓰지 않았다.

관리 worktree:
`C:\Users\zun24\.codex\worktrees\c1b1-candidate-b\성공은 실패의 어머니`
branch `codex/c1b1-candidate-b-verified`. 최종 local commit·end HEAD·Git status는 완료 후 보고한다.
기존 source 파일의 Git 변경은 없고 신규 FAST/package/tests와 이번 문서만 commit한다.
