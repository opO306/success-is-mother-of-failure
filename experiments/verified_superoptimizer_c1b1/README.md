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
기본 executor는 자동 변경되지 않는다. runtime gate 결과와 남은 한계는
[최종 보고서](../../docs/active/C1B1_CANDIDATE_B_PROMOTION_V1.md), 수학/소스 감사는
[독립 감사](../../docs/active/C1B1_CANDIDATE_B_PRIMITIVE_AUDIT_V1.md)에 있다.
