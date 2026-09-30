# C1-B1 _decide 예외 분류 V1

2026-10-01. 시작 HEAD/origin/master `53b73ea59fb27a5f29b33fce49751dd621a46696`, 시작 작업 트리 clean.
이 분류 계약을 실행 코드 수정 전에 고정했다. 새 물리·영역·반올림·정밀도 cap을 정의하지 않는다.
현재 상태는 **수정 후보 / STOP / 작업 미완료**다. LOCAL FULL이 실패했으며 commit/push하지 않았다.

## 분류 계약

| 상황 | 기존/최소 예외 | 의미와 처리 |
|---|---|---|
| 올바른 enclosure의 양 끝이 같은 raw로 반올림 | 정상 return | 해당 값만 사용 |
| malformed raw 또는 역전된 enclosure | ContractViolation(ValueError) | 실제 입력/내부 계약 위반. 자원 부족 아님. 즉시 정지 |
| R<r_min 또는 drift 선분의 r_min guard | PhysicsDomainExceeded | 물리 모델 미지원 영역의 정상 fail-closed 정지. 물리가 틀렸다는 판정 아님 |
| 초기 E_rel>10De | IntegratorDomainExceeded | 적분기 미지원 영역. 계산 오류 아님 |
| 반올림/초기 admission이 precision cap까지 미결정 | ReferenceUndecided | resource/precision refusal. INVALID 아님. ExecutorLimitExceeded보다 먼저 검사 |
| from_exact의 엄밀한 same-side overflow | VMHalt('overflow') | profile 안전 한계. impulse/진단 경로의 기존 예외 그대로 |
| kick/drift의 profile overflow | ExecutorLimitExceeded, cause=VMHalt('overflow') | 실행기 안전 한계. wrap/saturate/임의 보정 없음 |
| overflow 이외 VMHalt | 원래 VMHalt(reason) 그대로 | 원인별 VM 계약 정지. range 부족으로 오역하지 않음 |
| 메모리 부족 | MemoryError 그대로 | resource refusal. 물리적 실패/불일치 아님 |
| 조사 driver의 max_steps | end='step_cap' | 부분 계산·자원 한도. 성공/물리적 실패 아님 |
| 예상 밖 Python 오류 | 원래 오류; 조사 기록은 unexpected_exception | 원인 미상 bug 후보. 자동 INVALID/REFUSED 판정하지 않음 |

`ReferenceUndecided`의 상속과 legacy reason='executor_limit_exceeded'는 유지한다.
reason 문자열만으로 분류하지 않고 구체적인 클래스 및 cause를 보존한다.
`ExecutorLimitExceeded` 단독은 폭/정밀도/기타 구현 capability를 포함하는 역사적
상위형이다. 정확한 원인이 없으면 이를 모두 overflow라고 단정하지 않는다.
fail-closed는 원인 분류가 아니라 어떤 정지에서도 부분 상태를 확정하지 않는 성질이다.
예외를 default raw 값으로 바꾸거나 자동 재실행해 숨기지 않는다.

replay verifier의 INVALID는 제출 witness/claim의 실제 위반이고 REFUSED는 미판정이다.
executor의 미지원 입력이나 실행 정지 자체를 INVALID witness로 번역하는 adapter는 없다.
미완료 trace는 완료 witness로 위조하지 않는다. 금지 전이를 완료했다고 주장하는 witness는
독립 verifier에서 INVALID일 수 있지만, 이는 executor의 정상 guard 정지와 다른 사실이다.
승인된 `c1b1_replay/` 및 네 fingerprint는 이번 작업에서 수정하지 않는다.

## 호출·예외 흐름 감사

| 경로 | 발생 | 잡는 곳 / 전파 |
|---|---|---|
| potential / radial_force → _model → _decide | domain, endpoint VMHalt, precision, 내부 오류 | domain 선검사; _decide는 endpoint overflow만 보존하여 비교. 다른 VMHalt/내부 오류는 그대로 전파 |
| step → impulse → _model/G → component _decide | PhysicsDomainExceeded, VMHalt, ReferenceUndecided, 내부 오류 | step 자체는 잡지 않음; J_cache 재사용 및 0 성분은 _decide를 통과하지 않음 |
| step → _kick / _drift → _limit | profile VMHalt | overflow만 ExecutorLimitExceeded로 번역하며 cause 보존 |
| new_run → check_integrator_domain → energy enclosure | IntegratorDomainExceeded / ReferenceUndecided | 별도 admission refinement; _decide 호출 아님. new_run에서 전파 |
| step 저장 상태 경계 → exact / to_exact | malformed raw | valid_raw가 있는 profile의 저장 r/p/J_cache를 확인하고 ContractViolation 전파; 연구 중간값 변환 exact 및 비교용 profile 지원 유지 |
| step의 두 guard | PhysicsDomainExceeded | 모든 run 쓰기 전에 전파; 기존 불변 시험 유지 |
| stress instrumentation → original _decide | precision / VMHalt | 종류별 telemetry 기록 후 다시 raise; finally 원래 함수 복원 |
| stress run_trajectory / _point_job | 모든 Exception | 원래 예외명·내용·재현 상태 보존. classify로 구분; 정상 실행 계속 안 함 |
| runtime_wrapper._hooks / step | ReferenceUndecided 또는 terminal | 하위형 먼저 잡음. 기존 proof wrapper만 precision을 다룸; VMHalt/ExecutorLimit은 TERMINAL. 불변 위반 AssertionError |
| runtime_local_witness.build_witness | precision / VMHalt | NotWitnessed로 포장하나 구체적 예외명 및 __cause__ 보존. 독립 replay verifier 아님 |
| outgoing bootstrap / chain | ExecutorLimitExceeded(하위 precision 포함 가능) | NotCertified 포장. precision을 'arithmetic overflow'라고 오역하는 메시지 수정 |
| inbound / outgoing energy 연구 경로 | precision / ExecutorLimitExceeded | NotCertified 포장. 모호한 'overflow or undecided'를 하위형 먼저 나눔; formal status 변경 없음 |
| replay verify | Invalid / Refused / OSError / MemoryError | INVALID / REFUSED. 불일치와 자원 부족 분리 유지 |
| replay History.verify_next | verifier result + origin/hash binding | INVALID→DISCARDED, REFUSED→SPECULATIVE/halt, VALID+approved+binding→CONFIRMED. 자동 재실행 없음 |
| rounding_completeness point/cell checker | endpoint VMHalt | 점/셀 증명을 미결정으로 남기고 refine/split; 실제 값의 overflow 증거로 승격 안 함. finite step의 precision refusal은 not_certified_decision 기록 |
| rounding_diagnosis endpoint 비교 | VMHalt | endpoint_halt에 reason 기록. 이것만으로 실제 값 overflow를 주장하지 않음 |
| dt/numrep 연구 driver | PhysicsDomainExceeded / ReferenceUndecided / step cap | 각 원래 종류 또는 not_finished_within_cap 유지; momentum/drift 비교 driver의 미처리 예외는 전파 |
| wrapper survey / Proof Cache e2e | ReferenceUndecided | plain executor의 precision refusal만 기록. 이번 작업에서 실행/변경 안 함 |
| run.validation → frozen D_valid | validation_status='unsupported' | 초기 상태의 증거 metadata. 실행을 막거나 계산 오류라고 번역하지 않음; 동결 코드/fixture 수정 안 함 |

C1-A 자체 evaluator는 별도 동결 경로이므로 수정하지 않는다. 다원자/native/B 계통의
동명 함수는 이 호출 그래프에 속하지 않는다. 모든 일반 C1-B1 driver의 catch는 조사·시험용이고
운영 세계의 예외→history 상태 변환 controller는 아직 없다.
정적 목록은 `runs/c1b1_decide_classification_20261001/call_flow_inventory.json`에
보존했다(직접 C1-B1 호출63개, typed catch30개). callback으로 저장된 original _decide 및
세 instrumentation hook은 코드로 별도 확인했다. 정적 목록이 모든 동적 호출을 증명하는 것은 아니다.

## 발견한 충돌과 수정 범위

1. `_limit`는 모든 VMHalt를 range capability 부족으로 번역했다. 실제 overflow만 번역한다.
   `_decide`도 non-overflow VMHalt를 overflow endpoint처럼 비교/refine하지 않고 원래 예외로 정지한다.
2. `_decide`는 역전된 enclosure도 양 끝이 같은 raw면 수용할 수 있었다. 내부 계약 위반으로 정지한다.
3. FixedPoint.to_exact는 raw 유효성을 확인하지 않는다. C1-B1 step 저장 상태 경계에서 profile.valid_raw가
   제공된 경우 명시적으로 검사하여 malformed raw를 range/resource 부족과 구분한다.
4. stress classify는 직접 VMHalt overflow와 MemoryError를 unexpected_exception으로 기록했다.
   전자는 vm_overflow / 후자는 resource_refused, 기타 VMHalt는 vm_halt:<reason>으로 보존한다.
5. formal bootstrap의 broad base-class catch는 precision refusal도 arithmetic overflow라고 기록했다.
   하위형 먼저 분리하고 같은 NotCertified 및 원인 chain을 유지한다.

기존 ReferenceUndecided 상속·reason, impulse VMHalt와 kick/drift ExecutorLimitExceeded의
차이는 충돌을 해결한다며 합치지 않는다. 정상 입력의 수식·raw 결과는 바꾸지 않는다.

## 검증 결과

수정 후보는 아래 13개 파일이다. commit/push하지 않았으며 소스 결합 guard는 수정하지 않았다.

| 파일 | 변경 |
|---|---|
| [c1b1_two_atom.py](../../a_reference/c1b1_two_atom.py) | 잘못된 enclosure/저장 raw 정지, non-overflow VMHalt 보존 |
| [c1b1_stress_survey.py](../../a_reference/c1b1_stress_survey.py) | 계약 위반·VM halt·메모리 부족 기록 분리 |
| [c1b1_outer_bootstrap.py](../../a_reference/c1b1_outer_bootstrap.py), [c1b1_outer_chain.py](../../a_reference/c1b1_outer_chain.py), [c1b1_inbound_outer.py](../../a_reference/c1b1_inbound_outer.py), [c1b1_outgoing_energy.py](../../a_reference/c1b1_outgoing_energy.py) | precision refusal을 overflow로 기록하지 않도록 NotCertified 메시지/cause 분리 |
| [c1b1_outer_bootstrap_example_v1.json](../../a_reference/fixtures/c1b1_outer_bootstrap_example_v1.json), [c1b1_rounding_decision_examples_v1.json](../../a_reference/fixtures/c1b1_rounding_decision_examples_v1.json) | 비동결 생성 예시의 source_sha256만 갱신 |
| [test_c1b1_exception_classification.py](../../tests/test_c1b1_exception_classification.py) | 분류·정지 상태 보존·replay 연계 직접 시험 21개 |
| 이 문서, [CURRENT_STATE.md](../../CURRENT_STATE.md), [active/README.md](README.md), [DOCUMENT_STATUS_INDEX.md](../DOCUMENT_STATUS_INDEX.md) | 분류 계약, STOP 및 실패 근거, 문서 진입점 |

현재 코드 후보에서 추가 분류 시험 21개가 통과했다. 저장 raw 경계와 기존 inbound 시험을 합친
관련 재검증은 **44 passed, 38.61초**다. 정상 경로·미지원 영역·precision cap·기존 executor limit의
기존 시험은 유지했다. LOCAL FULL에서도 신규 21개는 모두 통과했다.

보존 witness와 같은 입력으로 7개 궤적을 다시 계산하여 **79,087 step 전체의 12 raw 상태 및 J가
기존 기록과 비트 동일**함을 확인했다. 이것은 해당 입력의 회귀 비교이며 D_valid 전체의 증명,
승인된 verifier의 재승인, 새로운 history 승격 또는 N-1 비용 측정이 아니다.
승인된 replay verifier의 네 fingerprint, origin/history 기록, 동결 계약은 변경하지 않았다.

**LOCAL FULL은 실패했다.** `python -m pytest tests -q -n 6` 결과:
**3253 passed / 58 failed / 143 errors / 1 strict xfailed / 실제 skip 0 / 25 warnings,
687.63초, exit 1**. 이 결과로 공식 통과 기준선을 갱신하지 않는다.

JUnit의 실패/error 201개를 분류하면 다음과 같다.

| 실패 경로 | 항목 수 | 원인 |
|---|---:|---|
| source-bound endpoint proof guard | 163 | 실행기 전체 소스 hash가 기존 증명 결합과 달라 재감사 요구 |
| prior group proof provenance | 17 | 이전 그룹 증명 기록의 소스 provenance 불일치 |
| diagnosis source provenance | 20 | 이전 진단 기록의 소스 provenance 불일치 |
| diagnosis fixture 재생성 비교 | 1 | 실제 계산 항목은 동일하나 source_sha256이 달라 비교 실패 |

중간 관련 실행의 7 failed / 295 passed / 1 xfailed도 로그에 보존했다.
그중 저장 raw 검사를 연구 중간값 변환 함수에 넣어 발생한 실패는 step 경계 검사로 옮겨
해결했다. 나머지 두 예시 기록은 동결 계약이 아닌 생성 예시이며, source_sha256 이외 모든
내용이 기존과 정확히 같음을 확인하여 provenance만 재생성했다. 이 두 기록의 갱신으로
아래의 소스 결합 증명이 갱신되는 것은 아니다.

## STOP 사유와 남은 결정

[endpoint proof_guard](../../a_reference/c1b1_axis_decision_bounds.py)는 `_decide`를 포함한
실행기 함수 binding과 `c1b1_two_atom.py` 전체 소스 hash를 검사한다.
기존 LF 정규화 hash는 `e5889e8af2901eaa594b9b593a2c47048c61a4b4811bb0af04fb6c5d25c32c0e`,
후보 hash는 `c09c080775768c27ae77deeabb7a55ddc136095138d06bddb7efaf8ac8b21591`다.
guard는 `source-bound endpoint error proof needs re-audit`로 정상 거부했다.
정상 궤적의 비트 비교만으로 기존 수학 증명의 소스 결합을 변경할 근거가 되지는 않는다.

재감사·재결합 또는 소스 결합 계약의 설계 변경 없이 이 후보를 공식 완료할 수 없다.
이번 요청은 A-EV 작업 시작과 임의 설계 변경을 금지하고 있으므로 여기서 STOP했다.
guard의 기대 hash를 교체하거나 guard를 우회하지 않았다. 그 재감사가 A-EV 전체를 닫는다는
의미도 아니다. 후속 실행기 소스 재감사·결합 갱신의 별도 범위를 설계자가 결정해야 한다.
대안은 실행기 소스 후보를 철회하고 문서·기록 분류만으로 범위를 줄이는 것이며,
이 경우 역전 enclosure와 malformed 저장 raw의 새 실행 guard는 이번에 도입되지 않는다.

남은 모호성: legacy `ReferenceUndecided.reason`은 executor_limit_exceeded이므로 클래스 우선
분류가 필요하다. 일반 `ExecutorLimitExceeded`는 cause 없이 overflow로 단정할 수 없다.
valid_raw를 제공하지 않는 비교용 profile의 전체 입력 schema 검증과 일반 운영 세계의
예외→history 변환 controller는 이번 범위에 포함하지 않았다. 원인 미상의 Python 오류도
자원 부족이나 INVALID로 자동 분류하지 않는다.

Energy Bound v0 APPROVED / ④-Liveness NotCertified / ④-Safety Conditional / A-EV unresolved를 유지한다.
O-1·공식 O-3·native J·live pipe·rollback controller·새 물리는 시작하지 않았다.

보존 근거는 Git 밖 `runs/c1b1_decide_classification_20261001/`의
`local_full.log`, `local_full.xml`, `corrected_boundaries.log`, `related_final.log`,
`bit_regression.json`, `call_flow_inventory.json`, `regenerate_examples.log`에 있다.
