# C1-B1 Runtime Fail-Closed Contract v0 + 국소 witness prototype

**상태:** 1단계 = 시험으로 고정한 계약(실행기 무변경). 2단계 = **prototype, survey_only**. 인증·coverage·D_valid·④ 상태 변경 없음
(14/64 region·gap 81·④-4b NotCertified·④ 미동결·⑤ 미착수 유지). 설계자 승인 2026-09-29.
**코드:** `tests/test_c1b1_step_fail_closed.py`(1단계), `a_reference/c1b1_runtime_local_witness.py` + `tests/test_c1b1_runtime_local_witness.py`(2단계).
**증거:** `runs/c1b1_runtime_local_witness_20260929/`(witness·거부 기록·비교 보고, fixture로 올리지 않음).
배경: [실행 기반 정밀도 조사](C1B1_RUNTIME_STRESS_SURVEY_V1.md), 장기 제안 [A 실행 증명서](../proposals/A_RUNTIME_CERTIFICATE_PROPOSAL.md).

## 무엇을 증명하고 무엇을 증명하지 않는가

| 이번에 확인한 것 | 이번 범위 밖 |
|---|---|
| 판정 불가로 거부된 step은 run을 전혀 바꾸지 않는다 | 실제 16384-bit 판정 불가의 해결(정지 유지. 필요하면 나중에 정확 유리수 tie/근접 배제 같은 별도 수학) |
| "128에서 정지 → 그 충격량만 재판정 → 검증 → 같은 step 재실행"이 정상 실행과 매 step 비트 동일 | 독립 물리 검증(witness와 검증기가 실행기와 같은 평가기 `C._model`을 사용) |
| witness 변조·오래된 witness(모델·소스·profile·dt·retardation·schedule 변경)를 거부 | 제안서의 누적 오차 상한(④-1〜3은 별도 해석적 인증) |
| 정밀도 schedule 128〜16384를 넘지 않는다 | 어떤 인증 상태의 승격 |

128 bit 거부는 **시험 설정으로 일부러 만든 것**이다. 실행기의 계약 cap(16384)은 바뀌지 않았고, witness 생성도 그 cap을 넘지 않는다.

## 1단계: Fail-Closed Contract v0

`C.step`은 kick·drift·충격량을 지역 변수로 계산하고, 마지막 세 줄(`run.atoms`, `run.J_cache`, `run.t_steps`)에서만 run을 쓴다. 이를 시험으로 고정했다.
비교는 `vars(run)` 원본 필드끼리 하며 `run.validation`(지연 캐시)은 읽지 않는다. 실패 전후 `_validation`이 비어 있음도 확인한다.

| 시험 | 결과 |
|---|---|
| 첫 step의 첫 충격량(J_cache 없음, 상대 위치 20+46·2⁻⁴⁸)이 128에서 판정 불가 | run 불변, cap 복원 뒤 정상 진행 |
| kick·drift 계산 뒤 두 번째 충격량(e=9 De, b=Re/2, step 4)이 판정 불가 | run 불변 |
| 판정 불가 뒤 cap 복원·계속 진행 | 60 step raw 상태 전부 정상 실행과 동일 |
| drift 선분이 r_min 안으로(PhysicsDomainExceeded, step 1) | run 불변 |
| 위치가 profile 범위를 넘음(FX(40,32), ExecutorLimitExceeded, step 2) | run 불변 |
| 결함 주입: 두 번째 충격량 전에 원자 위치를 먼저 쓰는 step | 검사가 "changed the run"으로 잡음 |

6 passed, 0.38초.

## 2단계: 국소 witness prototype

흐름(`run_with_local_witnesses`):
1. cap 128로 `C.step` 시도. 판정 불가면 run이 그대로인지 확인(1단계 계약)하고, 거부된 충격량의 입력(실행기가 계산한 상대 위치)을 기록한다.
2. `build_witness`: 그 입력의 충격량을 **실행기 자신의 경로**로 계약 schedule(cap 16384 이하)에서 다시 판정하고, 성분별로 판정이 닫힌 정밀도와 구간 양 끝을 기록한다.
3. `verify_witness`: 빌더와 다른 코드 경로(C.impulse·C._decide를 부르지 않음)로 구간을 다시 계산해, 기록과 정확히 같고 양 끝이 주장한 raw로 반올림되는지 확인한다. **JSON으로 저장한 형태**를 검증한다.
4. 같은 step을 처음부터 다시 실행한다. 실행기가 스스로 계산한 입력이 witness의 입력과 **정확히 같을 때만** 검증된 값을 쓴다.

witness 묶음(fingerprint): 동결 모델 지문, C1-A 지문, 실행기·모델 소스의 LF 정규화 SHA-256, 위치/운동량 profile(이름·폭·소수 비트), dt, kick 간격, drift 규칙, retardation, 반올림 방식(half-even), 정밀도 schedule, 정확한 입력 위치, 성분 축.
하나라도 다르면 오래된 witness로 거부한다.

### 결과

| 궤적(출발 거리로 돌아올 때까지) | step | 정상 실행의 256-bit 판정 | 128 거부 | witness | 매 step raw 동일 | 시간(정상 / witness) |
|---|---|---|---|---|---|---|
| e=9 De, b=Re/2 | 1,640 | 25 | 25 | 25 | 예 | 1.50 / 1.64초 |
| e=1/2 De, b=Re/2 | 5,775 | 77 | 77 | 77 | 예 | 5.30 / 6.24초 |
| e=1/10 De, b=2 Re | 21,056 | 239 | 239 | 239 | 예 | 19.8 / 21.4초 |

세 수(정상 256 판정 = 거부 = witness)가 모든 궤적에서 같고, **마지막 상태가 아니라 모든 step의 raw 상태**가 같다.

### 시험 (23 passed, 1.10초)

- 핵심: 200 step에서 매 step raw 동일, witness 수 = 거부 수, 128 초과 성분 수 = 정상 실행의 256 판정 수(3).
- 변조 15종을 **의도한 이유로** 거부: raw±1, impulse_raw만 변경, 정밀도 변경, 정밀도 32768, 입력 이동, 축 순서, 구간 아래/위 끝, 소스 해시, 모델 지문, profile, dt, retardation, schedule, version.
- witness는 정확히 같은 입력에만 쓰인다.
- 결함 주입: witness 없이 재개하면 같은 입력에서 다시 거부되어 잡힌다. 검증 없이 1 ulp 틀린 값을 받아들이면 궤적이 정상 실행과 달라져 핵심 비교가 잡는다.
- schedule 한도: 빌더의 cap이 128이면 거부, 32768 요청은 "contract cap 초과"로 거부.
- 실행기 함수(`C.impulse`, `C._decide`)와 cap은 항상 원래대로 복원된다.

## 한계 (먼저 공개)

- **독립 물리 검증이 아니다.** witness는 "executor rounding decision 재검증 witness"다. 평가기 구간이 참값을 감싼다는 실행기의 전제를 그대로 믿는다.
  audit의 독립 Lang 모델은 V만 구간으로 감싸고 힘은 수치 미분이라 이 검증에 쓸 수 없다.
- **prototype의 "국소 증명 = 더 높은 정밀도로 재판정"은 cap을 128로 낮췄기 때문에 성립한다.** 실제 16384 판정 불가에는 쓸 수 없고, 그 경우 계속 정지한다.
- 한 번 실패는 한 충격량(성분 1〜3개)에 대한 witness 하나로 처리한다. 이번 세 궤적에서는 모두 성분 하나만 128을 넘었다.
- cap을 모듈 전역값으로 잠시 바꾸는 방식이라 같은 프로세스의 병렬 스레드에서는 안전하지 않다(현재 사용 없음).
- 결과는 "그 실행"에 대한 것이다. 초기 상태 전체나 gap 81 영역의 인증이 아니다.

## 검증

LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 새 파일(시험 2개·prototype 1개·문서)만 추가했고 실행기·공용 로직·동결 계약·해시 고정 소스·fixture를 수정하지 않았다(`git status`로 확인).
관련 시험: 새 시험 29개 + 직접 영향 범위(`test_c1b1_stress_survey.py`, `test_c1b1_two_atom.py`) → **83 passed + 1 strict xfailed**(`-n 6`, 32.2초). 기준선 숫자는 갱신하지 않는다.

## 다음 판단 (설계자)

이 구조가 싸고 깔끔하다고 판단되면, shell 전체 사전 전수 인증 대신 "실행 + 판정 불가 시 정지 + 국소 증명"을 정식 방향으로 검토한다.
그때 정할 것: (1) 실제 16384 판정 불가에 쓸 국소 증명 방법(정확 유리수 tie/근접 배제 등), (2) 재개된 실행 = 기준 실행기라는 차등 계약을 정식 계약으로 둘지, (3) witness 저장 형식(fixture 승격 여부), (4) ④ 동결 조건을 "모든 초기 상태 사전 인증"에서 바꿀지.
