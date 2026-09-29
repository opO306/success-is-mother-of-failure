# C1-B1 runtime wrapper V0 — 실제 STOP → prover → 검증된 witness → 같은 step 재실행

**상태:** 계약 + 구현 + 시험(아래 8절), profile identity 보강(9절, 기준 HEAD `1140628`). 기준 HEAD `99830f2`. **Proof Cache 없음**(설계자 판정: wrapper를 먼저 단독으로 닫는다).
**현재 상태(변경 없음):** A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**, 실행기·평가기·동결 계약·checker V1/V2 변경 0, 실행기 cap 16384.
**근거:** 설계자 판정 2026-09-30(8개 조건), [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) 1·3·7절, [checker V2](C1B1_EXACT_IMPULSE_CHECKER_V2_DESIGN.md)(신뢰 승인), [point prover V0](C1B1_POINT_PROVER_DESIGN_V0.md).

## 0. 한 줄

wrapper는 실행기가 **충격량 성분 하나의 반올림을 cap 안에서 결정하지 못해 `ReferenceUndecided`로 멈춘 경우에만** prover를 부른다. 결과를 **다시 검증하고 binding과 입력이 정확히 맞을 때만** witness로 받아 **같은 step을 처음부터** 다시 실행한다. 다시 실행할 때는 **실행기가 바로 그 입력·그 성분에서 다시 멈출 때만** witness raw를 쓴다. 그 밖의 모든 경우 run은 바뀌지 않고 진행하지 않는다.

## 1. 계약 (설계자 8개 조건)

| # | 조건 | 구현 |
|---|---|---|
| W1 | prover는 실제 충격량 계산이 `ReferenceUndecided`로 끝난 경우에만 | 실행기 모듈의 `impulse`·`_decide`를 step 동안만 감싼다. **`impulse` 안의 `_decide`가 `ReferenceUndecided`를 낼 때만** 그 입력 (dr, 성분, dt_kick, profile)을 STOP으로 기록한다. `PhysicsDomainExceeded`, `ExecutorLimitExceeded`, `VMHalt`(같은 쪽 overflow 포함), 입장 검사 실패는 **TERMINAL**이며 prover로 보내지 않는다 |
| W2 | FOUND라도 즉시 진행하지 않음 | FOUND의 certificate에 `runtime_binding`을 붙여 정규 JSON 바이트로 만들고, 그 **바이트에서 다시** 검증한다: (a) 바이트 크기 상한 → (b) JSON 해석 → (c) binding 일치 → (d) 입력 (dr_raw, 성분, dt_kick)이 STOP 입력과 정확히 같음 → (e) checker V2 VALID → (f) raw가 prover가 말한 raw와 같음. 전부 통과해야 WITNESS_RESOLVED 후보 |
| W3 | step 처음부터 재실행 | witness를 표에 넣은 뒤 `C.step(run)`을 **처음부터 다시** 부른다. 실행기 step은 실패하면 run을 바꾸지 않으므로(Fail-Closed v0, 8 passed) 부분 kick/drift가 섞일 수 없다. 거부 뒤 run이 바뀌었으면 즉시 AssertionError |
| W4 | 정확히 같은 입력에서만 witness 사용 | 재실행 중 **실행기가 다시 `ReferenceUndecided`를 낸 그 결정**의 키 `(dr 정확 유리수, 성분, dt_kick, momentum profile 이름·폭·소수 비트)`가 표에 있을 때만 그 raw를 돌려준다. 실행기가 스스로 결정하는 성분에는 **절대 끼어들지 않는다**. 표는 step마다 새로 만든다(교차 step 재사용 = Proof Cache, 이번 범위 밖) |
| W5 | NOT_A_DECISION / EXHAUSTED / ANOMALY / checker REFUSED → 진행 금지 | 모두 **UNPROVED**, run 불변, wrapper 정지. ANOMALY는 prover를 다시 부르지 않는다(prover 호출 1회) |
| W6 | 파싱 전 바이트 크기 상한 | `max_certificate_bytes`(기본 262,144 = 256 KiB)를 **`json.loads` 전에** 검사한다. 초과는 UNPROVED(`certificate_too_large`)이며 가용성만 제한한다(한도를 올리면 같은 raw로 WITNESS_RESOLVED) |
| W7 | on/off 차등 | 정상 full-cap 궤적에서 wrapper를 켜든 끄든 매 step 비트 동일하고 prover 호출 0. cap-128 rehearsal에서 매 step이 full-cap 정상 실행과 비트 동일하고 witness 사용 수 = 128 초과 판정 수 |
| W8 | 결함 주입 | 틀린 raw witness, 다른 dr용, 다른 성분, 다른 dt, binding 변경, checker 생략, witness 없이 재개, step 중간부터 재개 — 전부 잡혀야 한다 |

## 2. step 결과 상태

| 상태 | 뜻 | run |
|---|---|---|
| RESOLVED | 모든 판정을 실행기가 cap 안에서 결정 | 한 step 진행 |
| WITNESS_RESOLVED | 한 개 이상의 판정이 검증된 witness로 결정. 사용한 witness 목록(키, raw, certificate SHA-256, prover 시도)을 기록 | 한 step 진행 |
| UNPROVED | STOP을 witness로 풀지 못함. 이유는 prover 결과(`not_a_decision:*`, `exhausted:*`, `anomaly:*`) 또는 재검증 실패(`certificate_too_large`, `bad_json`, `stale_binding`, `input_mismatch`, `checker_invalid:*`, `checker_refused:*`, `raw_disagrees`), `unsupported_profile`, `attempt_limit`, `witness_not_applied` | **불변**, 진행 금지 |
| TERMINAL | 반올림이 아닌 종결 거부(`PhysicsDomainExceeded`, `ExecutorLimitExceeded`, `VMHalt`) | **불변**, 진행 금지 |

`run_steps`는 UNPROVED나 TERMINAL에서 멈추고 그때까지의 기록을 돌려준다.

## 3. binding (witness가 유효한 조건)

`runtime_binding` = wrapper 버전, checker V2 형식·method·소스 LF SHA-256, 실행기(`c1b1_two_atom.py`)·모델(`ar2_lang2024.py`)·**수 체계(`a_numeric/profiles.py`)** 소스 LF SHA-256, 동결 모델 지문, position/momentum profile(**구현 클래스**·이름·폭·소수 비트·**확인된** 반올림), dt, dt_kick, drift 규칙, retardation. 반올림 필드는 선언 문자열이 아니다: profile이 9절의 canonical 확인을 통과할 때만 `half_even`, 아니면 `unverified`다(9절에서 변경). 하나라도 다르면 `stale_binding`이다. checker V2는 이 필드를 읽지 않으므로(수학적 참/거짓과 무관) **binding 확인은 wrapper의 책임**이다.

## 4. 지원 범위

- position FX(96,48), momentum FX(96,80)만 지원한다(certificate 형식이 이 둘을 가정). **두 profile 모두 진짜 `a_numeric.profiles.FixedPoint`여야 한다**(9절). 이름·폭·소수 비트만 같은 다른 구현은 지원하지 않는다. 다른 profile이면 UNPROVED(`unsupported_profile`)다. STOP 입력의 상대 위치가 2^-48 격자의 정수배가 아니어도 같다.
- 한 step 안의 재시도는 `max_attempts_per_step`(기본 8)까지다. 한 step은 충격량 최대 2개(첫 step) × 성분 3개라 6을 넘지 않는다. 넘으면 UNPROVED(`attempt_limit`)다.

## 5. 실행기와의 연결 방식 (먼저 공개)

- **실행기 소스는 바꾸지 않는다.** 대신 `C.impulse`와 `C._decide`를 step 실행 동안에만 감싸고, 모든 종료 경로에서 되돌린다(witness prototype과 같은 방식).
- 결과: 같은 프로세스 안의 **병렬 스레드에서는 안전하지 않다**(현재 사용 없음). 프로세스 병렬(xdist·ProcessPool)은 주소공간이 따로라 괜찮다. 실행기에 정식 hook을 넣는 것은 실행기 변경이라 이번 범위 밖이다. **기술부채(설계자 판정 2026-09-30): V0에서는 허용하되, 최종 병렬 world executor 전에 정식 hook/callback 경로로 교체한다.**
- `_decide` 감싸기로 성분 번호를 아는 방법: `impulse`는 `dr_k × dt_kick ≠ 0`인 성분마다 순서대로 `_decide`를 한 번 부른다. wrapper는 같은 조건으로 성분 목록을 만들어 호출 순서와 맞춘다. 이 대응이 틀리면 witness가 다른 성분에 들어가겠지만, 그 경우 재실행 결과가 정상 실행과 달라져 차등 시험(W7)이 잡는다.
- wrapper는 `MAX_PRECISION_BITS`를 읽거나 바꾸지 않는다. cap-128 rehearsal에서 cap을 낮추는 것은 **시험 코드**다.

## 6. 이번에 함께 고친 것: prover의 overflow 의미 (설계자 지적)

prover의 `_estimate()`는 비신뢰 mpmath 추정값이 FX(96,80) 출력 범위 밖이면 `NOT_A_DECISION("overflow")`를 돌려주고 있었다. 그러나 NOT_A_DECISION은 **입력만으로 정확히 정해지는** 경우(dr_k = 0, dt = 0, R < r_min, 위치 profile 밖)에만 쓰기로 했다. 추정은 overflow의 증거가 아니다. 그래서 이 경우를 **`EXHAUSTED("estimate_out_of_output_range")`**로 바꿨다. 실제 출력 overflow는 실행기의 종결 거부(`VMHalt`/`ExecutorLimitExceeded`)이고 prover로 오지 않는다(W1). 시험은 추정 overflow가 어떤 크기에서도 NOT_A_DECISION이 되지 않음을 확인한다.

## 7. 구현

`a_reference/c1b1_runtime_wrapper.py`(wrapper), `a_reference/c1b1_runtime_wrapper_survey.py`(종단 검증 드라이버), `tests/test_c1b1_runtime_wrapper.py`(30개). 수정은 `c1b1_point_prover.py`(6절)와 그 시험이다. **실행기·평가기·checker V1/V2·동결 계약은 변경하지 않았다.**

## 8. 결과

### 8.1 시험 30개 (34초)

| 조건 | 시험 |
|---|---|
| W7 | 정상 궤적 2개(각 300 step, full cap)에서 wrapper on/off 매 step 비트 동일, **prover 호출 0**. cap-128 rehearsal(1,640 / 5,775 step)이 매 step full-cap 정상 실행과 같음. witness 사용 수 = 정상 실행의 256-bit 판정 수, WITNESS_RESOLVED step 수 = witness prototype의 거부 수. 첫 충격량(J_cache 없음)에서의 거부도 해결 |
| W1 | `PhysicsDomainExceeded`, `VMHalt`(같은 쪽 overflow), `ExecutorLimitExceeded`(운동량 범위, 위치 범위)는 TERMINAL이고 run이 불변. **prover가 불리면 시험이 실패**하게 해 두었다. 지원하지 않는 momentum profile의 STOP은 prover 없이 UNPROVED |
| W5 | prover의 NOT_A_DECISION, EXHAUSTED(예산), EXHAUSTED(checker 거부), ANOMALY는 모두 UNPROVED이고 run이 불변이며 **prover 호출은 정확히 1회**(ANOMALY 재시도 없음) |
| W2/W4 | 심은 witness: 틀린 raw(certificate), 틀린 raw 주장, 다른 dr / 성분 / dt의 certificate, stale binding, 재검증 시 checker REFUSED — 전부 UNPROVED이고 run 불변 |
| W6 | 바이트 상한을 넘으면 **`json.loads`가 한 번도 불리지 않고** UNPROVED. 5 MB 입력도 해석 전에 거부. 깨진 JSON은 `bad_json`. 상한을 올리면 같은 raw로 WITNESS_RESOLVED(가용성만 바뀜) |
| W4 | 실행기가 스스로 결정하는 입력에 틀린 witness를 심어도 무시된다(실행기 raw 사용). 모든 종료 경로에서 hook이 복원된다 |
| 정적 | wrapper는 `MAX_PRECISION_BITS`를 대입하지 않고, 평가기 내부 함수를 부르지 않으며, V1 checker를 import하지 않는다 |
| **W8 결함 주입** | wrapper 소스 변이체: **checker 생략**(틀린 raw를 받아들임 → 차등 비교가 잡음), **입력 검사 제거** × dr/성분/dt(일관된 위조를 받아들임 → 잡음), **binding 검사 제거**(stale witness를 받아들임 → 잡음), **witness 저장 제거 = witness 없이 재개**(진행 못 하고 `attempt_limit` → rehearsal 비교가 잡음), **step 중간부터 재개**(차등 비교가 잡음), **hook이 실행기 결정보다 witness를 우선**(W4 시험이 잡음). 심은 witness 5종, stale binding, REFUSED는 위 W2 행 |

**먼저 공개(시험 과정):**
1. 처음 12건 실패는 시험 결함이었다. `RW.P`와 `P`가 같은 모듈이라 가짜 prover 안에서 `P.prove`를 부르면 자기 자신을 불렀다(재귀). 원래 함수를 import 시점에 붙잡아 고쳤다. 변이체 모듈에 `__file__`이 없어 binding 해시 계산이 실패한 것도 같은 성격이다.
2. "입력 검사 제거" 변이체가 처음에는 여전히 거부됐다. 다른 dr의 certificate raw와 prover가 주장한 raw가 달라 **raw 일치 검사**(W2의 f)가 막았기 때문이다. 방어가 두 겹이라는 뜻이다. 결함 주입이 입력 검사 자체를 시험하도록, 다른 입력의 certificate에 **그 certificate의 raw를 함께 주장**하는 일관된 위조로 바꿨다. 이 위조는 입력 검사만이 막는다.

### 8.2 종단 검증 (survey_only, `runs/c1b1_runtime_wrapper_20260930/`)

**A. cap-128 rehearsal, 실제 궤적 3개 전부:**

| 궤적 | step | 매 step 비트 동일 | RESOLVED / WITNESS_RESOLVED | witness 사용 | 정상 실행의 256-bit 판정 | 시간(정상 / wrapper) |
|---|---|---|---|---|---|---|
| e=9 De, b=Re/2 | 1,640 | **예** | 1,615 / 25 | 25 | 25 | 1.6 / 5.4초 |
| e=1/2 De, b=Re/2 | 5,775 | **예** | 5,698 / 77 | 77 | 77 | 6.8 / 18.9초 |
| e=1/10 De, b=2Re | 21,056 | **예** | 20,817 / 239 | 239 | 239 | 25.6 / 46.4초 |

**B. 실제 cap 16384 STOP을 한 step 안에서 닫기(합성 2^-17000, 위·아래):**
step의 첫 충격량 입력을 2^-17000 near-tie로, dt를 그 두 배(17,600비트 유리수)로 만든 run이다(`validated_only=False`: 합성 스트레스 상태이며 물리 주장이 아니다).

| | 실행기 단독 | wrapper(한도 올림) | wrapper(기본 한도) |
|---|---|---|---|
| 위(+) | `ReferenceUndecided`(cap 16384, 13.9초) | **WITNESS_RESOLVED**, STOP 2회(성분 0·1), witness raw = mpmath 기대값, t_steps = 1, 791초 | UNPROVED `exhausted:checker_refused:integer_size_limit` |
| 아래(−) | 같음 | **WITNESS_RESOLVED**, 같은 방식, 791초 | 같음 |

- STOP이 두 번인 이유: 입력의 x·y 성분이 같아(방향 (0.6, 0.6, 0.5)) 두 성분의 정확한 충격량이 같고 둘 다 경계에 붙어 있다. 성분마다 별도의 prover 호출·certificate(33.5 KB)·재검증을 거쳤다. 두 번째 충격량(drift 뒤)은 실행기가 스스로 결정했다.
- 791초 = (prover의 checker 약 185초 + wrapper의 바이트 재검증 약 185초) × 성분 2 + 실행기 시도들. **W2 재검증이 깊은 사례의 비용을 두 배로 만든다.** 조건대로 유지했으며, 줄이는 방법(예: Proof Cache의 검증 재사용)은 이번 범위가 아니다.
- 기본 한도 결과는 합성 `dt_kick`(약 5,300자리)이 checker `digits_max`에 걸리는 합성법의 문제이고, 실제 runtime 입력(dt = 40)에는 없다.

### 8.3 아직 증명되지 않은 것 (먼저 공개)

1. **wrapper의 정확성은 시험과 차등 비교로만 뒷받침된다.** 특히 `_decide` 호출 순서와 성분 번호의 대응(5절)은 실행기 `impulse`의 현재 구현에 기대며, 어긋나면 차등 비교가 잡는 구조다. 실행기가 바뀌면 binding의 실행기 해시가 달라져 witness가 stale이 된다.
2. **hook 방식은 병렬 스레드에서 안전하지 않다.** 실행기에 정식 hook을 넣는 것은 실행기 변경이라 이번 범위 밖이다.
3. **④-Liveness NotCertified, ④-Safety Conditional(A-EV)은 그대로다.** wrapper가 실제 cap STOP 한 건을 닫았다는 것은 경로가 작동한다는 실측이며, D_valid 전체의 Liveness가 아니다. prover의 운영 한도 안에서 모든 STOP이 풀린다는 보장도 없다(Lemma A+B는 유한한 certificate의 존재만 준다).
4. trajectory-completion(Q4)과 `VMHalt`/`ExecutorLimitExceeded` 예외 분류 정리는 이번 범위 밖이다.
5. Proof Cache 없음. 같은 입력의 STOP이 다른 step에서 다시 나오면 prover와 재검증을 다시 한다.

## 9. profile identity 보강 (설계자 판정 2026-09-30, 기준 HEAD `1140628`)

**판정:** 실행 구조(STOP → prover → V2 검증 → 같은 step 재실행)는 승인. 단, 정식 witness binding은 profile identity 보강 전 미완.

**찾은 구멍(witness soundness):** V0의 `_supported()`는 profile의 `name/width/frac_bits`만 봤다. 같은 메타데이터를 가진 **다른 구현**(예: `from_exact`의 반올림을 바꾼 subclass)도 지원 profile로 통과했고, binding의 `"rounding": "half_even"`은 확인 없이 적은 문자열이었다. 그러면 실행기는 다른 반올림 규칙으로 도는데 wrapper는 **진짜 half-even FX(96,80)로 증명한 raw**를 그 세계에 넣을 수 있었다. checker가 옳아도 세계에 틀린 값이 들어가는 경로다. 결함 주입으로 V0 게이트가 half-up 위조 FX(96,80)에 실제로 WITNESS_RESOLVED를 준다는 것을 확인했다(아래 시험).

**수정(wrapper만, 실행기·checker·prover·물리 계약 변경 0):** `_canonical_fx(p, W, F)`가 참일 때만 지원한다. position·momentum 둘 다 확인한다.

| 층 | 확인 | 막는 것 |
|---|---|---|
| 1 | `type(p) is FixedPoint` (`isinstance` 아님) | subclass, 전혀 다른 look-alike 클래스 |
| 2 | 인스턴스 속성이 생성자가 만드는 5개(`width, frac_bits, lo, hi, name`)뿐이고 값이 W·F에서 계산한 것과 같음 | 인스턴스에 심은 `from_exact` 등 |
| 3 | 실행기가 부르는 클래스 메서드(`from_exact, to_exact, _check`)가 wrapper import 시점의 함수와 같은 객체 | 실행 중 클래스 메서드 교체 |
| 4 | 알려진 답 탐침: ±½, ±3/2, ±5/2 ULP가 0, ±2, ±2로(짝수 쪽), `to_exact`가 정확한 역 | 모듈 수준 반올림 함수(`_div_round`) 교체 등 1〜3이 못 보는 변경 |

- 이 확인은 **stop 때 prover를 부르기 전**과 **`verify_witness`의 맨 앞**(바이트를 읽기 전) 두 곳에서 한다. `verify_witness`는 Proof Cache가 재사용할 경로이므로 거기서도 막아 둔다.
- binding에 `profiles_sha256`(`a_numeric/profiles.py` LF SHA-256)을 추가했다. profile 기록은 `{impl, name, width, frac_bits, rounding}`이고 `rounding`은 위 확인을 통과해야만 `half_even`이다. 따로 떠 있던 `"rounding": "half_even"` 필드는 없앴다.
- 한계(먼저 공개): 3·4층은 **실행 중 교체**를 잡는 방어이고 완전하지 않다. 탐침이 보는 점 밖에서만 다르게 동작하도록 모듈 함수를 교체하면 4층도 통과한다. 이 경우 막는 것은 소스 해시가 아니라(해시는 파일만 본다) 프로세스 안의 코드를 신뢰한다는 전제다. 파일 변경은 `profiles_sha256`이 stale로 만든다.

**시험(12개 추가, wrapper 시험 30 → 42):**
- canonical 두 profile은 확인을 통과하고 binding에 `profiles_sha256`·`impl`·`rounding: half_even`이 들어간다.
- 위조 7종 — subclass(`from_exact` half-up), subclass(`to_exact`가 한 raw에서 다름), look-alike(비 FixedPoint, half-up), 진짜 FixedPoint 인스턴스에 심은 `from_exact`, position 쪽 subclass, 클래스 메서드 교체, 모듈 `_div_round` 교체 — 모두 이름·폭·소수 비트가 진짜와 같다. **모두 실제 cap-128 STOP까지 가서 UNPROVED(`unsupported_profile`), prover 호출 0, run 불변**, binding의 해당 profile은 `rounding: unverified`, `verify_witness`는 바이트를 보기 전에 거부.
- **결함 주입:** (a) V0의 메타데이터 게이트로 되돌린 변이체 → half-up 위조가 WITNESS_RESOLVED(원래 결함 재현), (b) `type is` 대신 `isinstance` → `to_exact` subclass가 prover까지 감, (c) 탐침 제거 → `_div_round` 교체가 prover까지 감. 각 층이 실제로 일을 한다.
- `profiles_sha256`만 다른 binding → `stale_binding`.

**Proof Cache 설계 필수 조건(설계자 판정, 아직 구현 안 함):**
1. hash만 저장하지 않는다. **canonical certificate bytes 자체를 불변 저장**하고 SHA-256은 content address·변조 검사용이다.
2. 사용할 때마다 bytes → 크기 검사 → parse → binding → 입력 → checker V2 VALID를 **다시** 한다(저장된 witness는 prover 탐색만 생략).
3. 현재 WITNESS_RESOLVED 기록에는 raw·certificate SHA-256·크기·prover 요약만 있고 **certificate 본문은 없다**. 즉 `StepOutcome`만으로는 그 결정을 다시 검증할 수 없다. survey/prototype인 지금은 세계 정확성 결함이 아니지만, wrapper를 실제 canonical 실행에 쓰기 시작하는 시점부터는 WITNESS_RESOLVED가 저장된 객체의 content address를 반드시 기록해야 한다.

**상태:** Point Prover V0 승인 / Runtime Wrapper V0 구조·동작 승인 / 정식 witness binding은 이 보강으로 profile identity 조건을 채움(설계자 재판정 대기) / Proof Cache 미착수 / ④-Safety Conditional / ④-Liveness NotCertified.

**검증:** LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: wrapper 파일(survey_only 새 계층)과 그 시험·문서만 변경, 실행기·평가기·checker V1/V2·prover·동결 계약 변경 0. wrapper 42 + prover 24 + V2 95 + V1 185 + fail-closed·witness prototype·two_atom = **418 passed + 1 xfailed**(기존 strict xfail), `-n 6`, 245.59초. 기준선 숫자는 갱신하지 않는다. 증거: `runs/c1b1_runtime_wrapper_profile_identity_20260930/{related.log,related.xml}`.
