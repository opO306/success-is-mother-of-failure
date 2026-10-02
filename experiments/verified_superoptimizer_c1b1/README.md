# C1-B1 Verified Superoptimizer — Candidate B promotion

이 패키지는 기존 Pilot A/B를 재검증한다. 새 후보 search·새 물리식·cutoff·근사·GPU 경로를 만들지 않는다.
`verify.py`에는 primitive/AST 검사 도우미만 남겼다. 실행과 판정은 새 `run_pilot.py`가 담당한다.
원래 다운로드와 counterexample은 보존하며 `PROOF.md`는 당시 논증 원문이다.

## 실제 실행

새 directory에서 아래 순서로 실행한다. 이미 실행한 stage와 run directory는 덮어쓸 수 없다.
정상 Python 환경에서 assertions를 켠 상태로 실행한다. `-O`/`PYTHONOPTIMIZE` 환경은 감사 대상이 아니다.

```powershell
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage closure
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage audit
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage local_full
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage trajectory
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage benchmark
python -u -m experiments.verified_superoptimizer_c1b1.run_pilot --run runs/NEW_RUN --stage summarize --promotion
```

source를 바꾼 뒤에는 reviewer 해시를 다시 확인하고 새 run을 만든다. 감사 JSON의 PASS만 읽어
promotion을 통과시키지 않는다. closure만 PASS인 경우 뒤의 네 단계는 미완료다.
입력은 저장된 178개 + 추가 악성 입력 51개, 실제 산란 3개, 실제 거부 4개와 benchmark 설정이다.
midpoint의 특수 dt는 impulse 진단용이며 실제 trajectory는 원본 dt=40을 사용한다.
pytest의 cap=128 fault rehearsal은 원본 cap=16384 실제 STOP 입력과 별도로 구분한다.

## 소스와 evidence

manifest는 하나의 run_id, Git HEAD/index blobs, 실제 source SHA inventory, input SHA,
B/checker SHA, profile/version, Python/platform 및 각 subprocess command/rc/output SHA를 묶는다.
ignored runs는 source inventory에서 제외하고 저장소 code/native/fixture와 신규 파일을 포함한다.
소스·입력·결과 파일 변경, stage 미실행, 중복, 누락·빈 상세 기록은 INCOMPLETE,
실제 failed check나 nonzero rc는 FAIL이다. stage별 성공은 저장된 임의 PASS 문자열로 정하지 않는다.
모든 output/hash를 함께 위조하는 공격에 대한 암호학적 실행 증명은 아니다.

dataset에는 각 입력/profile의 실제 dV/inv1/F_over_R, raw J 또는 거부, 실제 M 및 decision이 있다.
fixed-M은 실제 endpoint, high-M 직접 4건은 endpoint/F_over_R canonical SHA를 보존한다.
high 직접 4건에는 checker가 없지만, actual cap STOP의 adaptive dataset에는 checker가 있다.
trajectory gzip에는 매 step의 양쪽 raw state/cache, 실제 impulse 인수와 raw 결과, 예외를 보존한다.
benchmark는 실행 순서를 번갈아 하고 warm-up 1회 후 3회 반복 median을 사용한다.
동일 CPU affinity 한 개, Python CPU 시간·wall 시간을 모두 기록한다.

## 별도 production 후보

```python
from a_reference.c1b1_fast_impulse import impulse, step_fast
```

기존 `a_reference.c1b1_two_atom.impulse/step/_model_R`는 보존한다.
FAST는 impulse 전용 dV/inv1 evaluator이며 energy/potential에는 연결하지 않는다.
`step_fast`는 동일 step code object를 복제한 namespace에서 impulse만 교체한다.
위 승격 단계에서는 기본 executor를 변경하지 않았다. 해당 단계 결과와 남은 한계는
[최종 보고서](../../docs/active/C1B1_CANDIDATE_B_PROMOTION_V1.md), 수학/소스 감사는
[독립 감사](../../docs/active/C1B1_CANDIDATE_B_PRIMITIVE_AUDIT_V1.md)에 있다.

## master runtime activation (2026-10-02 시작)

별도 `a_reference.c1b1_runtime` 선택기의 기본값은 FAST다. 영구 slow REF와
historical O-1 producer / witness-prover wrapper / proof/checker는 그대로다.

```python
from a_reference import c1b1_runtime as runtime
runtime.step(run)                     # FAST
runtime.step(run, mode='reference')   # explicit slow REF
runtime.impulse(dr, dt_kick, profile, mode='reference')
```

실제 production replay producer는 `tools.c1b1_replay_benchmark.execute()`에서
이 선택기를 쓴다. `python tools/c1b1_replay_benchmark.py executor reference`로
같은 producer의 REF 모드를 실행할 수 있다. executor batch는 원래 비용 증거를
덮어쓰지 않고 새 UUID 폴더에 결과를 기록한다. 필요한 preserved raw 입력은
기존 producer의 명시된 `runs/c1b1_postverify_survey_20261001/` 자산이다.
runtime 자체에는 Codex worktree/branch 전용 경로가 없다.

새 단계 도구는 `python -u -m experiments.verified_superoptimizer_c1b1.runtime_activation
--run runs/<fresh-name> --stage <stage>`다. master 재검증 뒤
`seal → closure → differential → full → benchmark → profile → check` 순서다.
새 source/input을 고정하고 실제 subprocess command/rc/log/result/상세 witness를
결합한다. 성공 endpoint 증명은 원래 closure이며 trajectory는 integration 증거다.
6개 정상 궤적, 실제 거부 4개, 합성 dt의 cap16384 STOP을 구별한다.
CLI는 큰 진단 분수의 Python 문자열 자릿수 한도를 실행 프로세스에서 해제한다.
이 거대한 진단을 imported checker로 검사할 때도 같은 설정이 필요하다.
물리 precision cap은 16384 그대로다. 기존 기록·failed inspection은 보존한다.
최종 판정·측정값은 [activation 보고서](../../docs/active/C1B1_CANDIDATE_B_RUNTIME_ACTIVATION_V1.md)에 기록한다.
