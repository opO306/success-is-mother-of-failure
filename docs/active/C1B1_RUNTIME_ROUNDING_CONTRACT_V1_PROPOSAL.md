# C1-B1 Runtime Rounding Contract V1 — 제안

**문서 상태: 구조 승인(설계자 판정 2026-09-29, 9절). 같은 날 후속 판정으로 P1a 채택·D3(A-EV를 Safety 선행조건으로) 채택·다음 순서 변경(10절).** 2.2절의 D_valid 모양 설명은 구현자 오류로 정정했다([Liveness 경로 조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 2절). 파일 이름의 PROPOSAL은 링크 보존을 위해 유지한다. 승인된 것은 계약 **구조**이며,
runtime wrapper·point prover·Proof Cache 구현은 각각 별도 설계·승인 뒤에만 한다. 실행기·인증서·coverage·D_valid는 바꾸지 않는다.
**현재 상태(변경 없음):** coverage 14/64 region·gap 81, ④-4b NotCertified, ④ 미동결, ⑤ 미착수, 정밀도 cap 16384.
**근거:** [실행 기반 정밀도 조사](C1B1_RUNTIME_STRESS_SURVEY_V1.md), [Fail-Closed v0 + 국소 witness prototype](C1B1_RUNTIME_FAIL_CLOSED_V0.md), 설계자 판정(2026-09-29).
**관련 제안:** [A 실행 증명서](../proposals/A_RUNTIME_CERTIFICATE_PROPOSAL.md)(Proof Atom→Segment→Box→Domain),
[증명 조립 아키텍처](../proposals/A_PROOF_COMPOSITION_ARCHITECTURE_V1.md), Warehouse 설계(별도 브랜치 `claude/proof-warehouse-architecture-skrgwm`, 구현 보류).

## 0. 한 줄 요약

반올림 완전성(④-4)을 **사전 전수 인증**이 아니라 **실행 중 판정 + 판정 불가 시 정지 + 그 지점만 국소 증명**으로 다룬다.
버리는 것은 "shell마다 수억 개 경계를 미리 열거하는 방법"뿐이다. **④의 의무는 약화하지 않는다.** ④를 Safety와 Liveness로 나누고, 둘 다 닫혀야 ④가 끝난다.

## 1. 네 상태

판정 단위는 **충격량 한 성분의 반올림 판정**이다. step 단위 결과는 그 step 안의 모든 판정 상태로 정해진다.

| 상태 | 뜻 | 세계 진행 | 현재 코드 |
|---|---|---|---|
| **RESOLVED** | 실행기가 계약 schedule(128→256→…→16384) 안에서 구간 양 끝이 같은 raw로 반올림됨을 직접 확인 | 진행 | `C._decide` 반환 |
| **STOPPED** | 16384까지도 판정 불가. step 전체를 버리고 run은 **정지 전 그대로** | 멈춤 | `ReferenceUndecided` + Fail-Closed v0 시험 |
| **WITNESS_RESOLVED** | 바로 그 입력(상대 위치·성분·binding)에 대해 **검증된 국소 witness**가 있음 | 같은 step을 **처음부터** 재실행하고, 그 입력에서만 witness 값을 씀 | prototype만 존재(시험 설정 cap 128). **실제 cap에서 승인된 witness 방법은 아직 0개** |
| **UNPROVED** | 국소 prover도 해결 못 함 | **절대 진행하지 않음.** run은 STOPPED 상태로 끝나며 결과를 "실행기 정지"로 기록 | 해당 경로 없음 = 현재 모든 실제 STOP의 결말 |

규칙:
- STOPPED에서 벗어나는 길은 WITNESS_RESOLVED 하나뿐이다. 더 높은 cap으로 몰래 다시 돌리거나, 가까운 값·통계·Hazard Atlas(6절)로 채우는 경로는 없다.
- WITNESS_RESOLVED는 **실행기가 스스로 계산한 입력**이 witness의 입력과 정확히 같을 때만 성립한다. witness가 입력을 정하지 않는다.
- 이 네 상태는 **반올림 판정**에만 적용된다. `PhysicsDomainExceeded`, `IntegratorDomainExceeded`, 위치/운동량 범위 초과(`ExecutorLimitExceeded`), `_decide`의 같은 쪽 실제 overflow(`VMHalt`)는 witness로 풀지 않는 **종결 거부**다. Fail-Closed(run 불변)만 적용된다.
- 입장 검사(`check_integrator_domain`, E_rel ≤ 10 De)의 판정 불가도 `ReferenceUndecided`다. run이 만들어지지 않으므로 이 계약의 witness 경로 밖에 둔다(별도 결정 전까지 UNPROVED와 같이 취급).

## 2. ④를 두 조각으로

| | ④-Safety | ④-Liveness |
|---|---|---|
| 질문 | 애매한 반올림으로 **틀린 세계 상태를 만들지 않는가** | 인정한 C1-B1 영역의 모든 실행에서 **필요한 판정이 결국 모두 해결되는가** |
| 기차 비유 | 모르는 철길을 무시하고 지나가지 않는다 | 허용된 모든 기차가 목적지까지 간다 |
| 현재 | prototype과 시험으로 상당히 확인. 선행조건 A-EV + 아래 S1〜S6을 채우면 완료 후보(A-EV 미해결 동안은 Conditional) | **NotCertified** |

**④ 전체 동결 = ④-Safety 완료 + ④-Liveness 완료 + 설계자 판정.** 둘 중 하나만으로 ④를 동결하지 않는다.

### 2.1 ④-Safety 완료 조건

**선행조건 A-EV (Evaluator Validity, 설계자 판정 D3):** 사용되는 numerical enclosure가 해당 물리식의 참값을 포함한다.
Safety 논리는 "enclosure가 참값을 포함 → 두 endpoint가 같은 raw → 참값도 그 raw"이므로 첫 줄이 깨지면 뒤가 모두 무너진다. EXP cutoff 결함이 실제로 한 번 있었다.

```
A-EV 성립 + S1〜S6 성립 = ④-Safety
A-EV 미해결            → ④-Safety는 Conditional(전제하 성립). 완료로 쓰지 않는다
```

현재 A-EV는 **미해결**이다(아래 S2의 한계). 따라서 S1〜S6이 모두 채워져도 ④-Safety는 Conditional이다.

| # | 조건 | 현재 |
|---|---|---|
| S1 | **Fail-Closed:** 모든 거부에서 run이 불변(`vars(run)` 비교, validation 캐시 미접근) | 판정 불가(첫 충격량·kick/drift 뒤), drift 선분, 위치 범위, `_decide`의 실제 overflow(`VMHalt`), kick의 운동량 범위 초과 — **8 passed**. 기록: 충격량 자체의 overflow는 `VMHalt`가 감싸지지 않고 나오고, 다른 범위 초과는 `ExecutorLimitExceeded`다(이름 불일치, 실행기 수정 사항이라 변경하지 않음) |
| S2 | **RESOLVED의 정확성:** 실행기 판정 = 정확한 모델 값을 한 번 반올림한 값 | **평가기 구간이 참값을 감싼다는 전제(A-EV)에 조건부.** 아래 한계 참조 |
| S3 | **witness 계약:** binding 전체(7절), 입력 키, 빌더와 다른 검증 경로, 저장 형태 검증, 변조 거부, binding이 하나라도 다르면 stale | prototype에서 변조 15종 거부 확인. 실제 cap용 witness 방법은 없음 |
| S4 | **UNPROVED에서 진행하는 코드 경로가 없음:** RESOLVED/WITNESS_RESOLVED가 아닌 판정으로 step을 확정하는 경로 0개. 결함 주입(강제 진행 변형)을 시험이 잡음 | prototype의 "witness 없이 재개" 결함 주입은 잡힘. 정식 경로의 시험은 없음 |
| S5 | **차등 회귀 시험:** 기준 실행이 존재하는 모든 경우(cap을 낮춘 rehearsal 등) 매 step raw 상태가 기준 실행과 비트 동일, witness 수 = 거부 수 | prototype 3궤적(1,640 / 5,775 / 21,056 step) 동일 |
| S6 | **비간섭:** Proof Cache·Hazard Atlas를 켜고 끈 결과가 같다. 단 Proof Cache는 STOPPED를 WITNESS_RESOLVED로 바꾸는 것만 할 수 있다 | 미구현 |

**S2의 한계 (먼저 공개):** RESOLVED가 옳다는 것은 "구간 양 끝이 같은 raw로 반올림됨"과 "평가기 구간이 참값을 감쌈(A-EV)"의 결합이다.
A-EV는 지금까지의 모든 인증서가 공유하는 전제이며, 전 입력에 대해 증명된 것이 아니다. 과거에 EXP 고정 cutoff가 높은 정밀도에서 틀린 구간을 준 결함이 실제로 있었다([rounding-decision](C1B1_ROUNDING_DECISION_V1.md) 2.1절).
따라서 ④-Safety는 A-EV가 닫히기 전까지 **Conditional**이다(D3). A-EV 자체의 강화(예: 독립 구간 힘 평가기)는 별도 과제다. audit의 독립 Lang 모델은 V만 구간으로 감싸고 힘은 수치 미분이라 지금은 A-EV를 독립 검증하지 못한다.
[Liveness 경로 조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md)의 R7 prover에 필요한 독립 엄밀 구간 평가기는 이 A-EV 강화 부품과 같은 것이다.

### 2.2 ④-Liveness 완료 조건

**대상 영역(L0, 설계자 판정): D_valid.**

```
실행 가능 영역         = 입장 계약 (E_rel ≤ 10 De 등)   — "실행기에 들어올 수 있다"
④-Liveness 증명 목표  = D_valid numerical_validated      — "수치 근거를 명시적으로 관리하는 초기 상태"
```

입장 계약 전체를 바로 목표로 잡지 않는다. 다른 영역의 물리 검증이 쌓이면 L0를 넓힌다.

**정정(2026-09-29, 구현자 오류):** 이전 판의 이 자리에는 "D_valid = 정확히 7개 에너지, 에너지마다 b 한 줄"이라고 적혀 있었다. fixture 가지만 읽은 잘못된 요약이다.
코드(`evaluate_run` → `classify`)상 D_valid(`numerical_validated`)는 세 부분이다([조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 2.1절).
- **L:** 1e-8 De ≤ E < 약 0.14181 De(b_orb = 2Re가 되는 에너지), **모든 b ∈ [0, 2Re]**, 초기 배치 제한 없음(3D 가능).
- **H:** 약 0.99736 De < E ≤ 10 De(장벽 꼭대기 위), **모든 b ∈ [0, 2Re]**, 초기 배치 제한 없음.
- **F:** 정확히 7개 에너지(0.15 … 0.99 De)의 canonical 생성기 상태(출발 R=20, 평면). 에너지마다 궤도 포획 경계 **양옆의 짧은 b 구간 2개**(|ρ| ≈ 10⁻⁴〜5×10⁻³부터 0.01까지, 폭 0.04〜0.14 bohr). b=0은 포함하지 않는다.
- 그 밖의 에너지(0.1418〜0.9974 De)는 unsupported. 보간·근처 에너지 없음.

**Q1 설계자 판정(2026-09-29, 3차): L0 = D_valid 전체 유지**(정정된 모양 확인). F만이나 canonical만으로 줄이지 않는다.

**Liveness의 뜻(Q2 설계자 판정, 계약 변경):** ④-rounding의 수학적 Liveness는 **정성적 finite termination**이다.
- 16384는 실행기 **fast-path의 자원 한도**로 남는다(삭제하지 않는다). 별도 exact certificate prover가 **correctness path**다.
- 계약: ≤16384에서 RESOLVED, 아니면 prover가 유한한 exact certificate로 WITNESS_RESOLVED, 그것도 못 하면 STOP.
- 정량 CPU/bit 상한은 별도 **operational bound**로 관리한다.
- 기존 ④는 "필요한 모든 판정이 16384 안에서 결정됨"을 명시적으로 요구했으므로 **이것은 계약 변경이며 설계자 판정으로 기록한다.**
- 근거 요건: `no exact tie(Lemma A) + certified enclosure convergence(Lemma B) = qualitative finite rounding liveness` ([감사 v0](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md)).

**Q4 설계자 판정:** r_min 침범 없음·overflow 없음·포획 없이 R_J 도달은 ④-rounding Liveness에서 분리한다. C1-B1 최종 freeze 전의 **별도 trajectory-completion obligation**이다.

주장: D_valid의 모든 초기 상태에서, 종료 조건(R_J로 나가 tail에 인계)까지 **모든 판정이 RESOLVED 또는 승인된 방법의 WITNESS_RESOLVED**이다.
이 주장은 inbound(R 20→최근접)·안쪽·outgoing(→R_J) 전 구간의 판정을 포함한다. 기존 형식 증거는 outgoing 쪽 일부뿐이다(아래 표).

| 증거 | 상태 | 비고 |
|---|---|---|
| tail(R ≥ R_J = 10,240 bohr) | 형식 인증(최대 512 bit) | 기존. 모든 legal 3D 위치 |
| outgoing shell 16〜26 | 형식 인증(14/64 region) | **+x축 위 입력만**(예시 상태 q=(20,0,0), P=(1,0,0)의 1D enclosure). D_valid에서는 L·H의 정면충돌(b=0) 상태에만 해당하고 **F 궤적과는 겹치지 않는다**(정정 2026-09-29) |
| shell 0〜15의 gap 81 | **미인증** | 전수 hard-case 방식은 shell 15에서 STOP. 역시 +x축 기준 |
| 안쪽(R < 20)·inbound | 형식 liveness **없음** | 기존 ④ 범위 밖이기도 함 |
| 실행 조사(약 2.3억 판정, 바깥 비행 포함) | STOP 0 | **survey_only.** 증명 아님. D_valid 몫은 거의 전부 H다. F는 안쪽 6궤적, 바깥 비행 0 |

닫는 길(D4, 설계자 판정: **혼합형**):
- **목표는 L-a(D_valid 전체에 대한 별도 수학적 보장)를 유지한다. 방법은 shell 전수 열거가 아니어도 된다.**
  새 해석적 bound, point prover의 completeness 정리(“D_valid의 모든 필요한 입력에서 prover가 반드시 결론을 낸다”), Proof Box 등 더 싼 방법으로 D_valid 전체를 덮는다.
- **L-b(실행 단위 증명서) 단독으로는 ④-Liveness를 닫지 않는다.** 100개 궤적이 성공해도 101번째 입력이 멈출 가능성이 남는다.
  실행 증명서는 그동안 세계를 안전하게 돌리고 증거를 쌓는 수단이며, 영역 Liveness의 대체재가 아니다.
- **L-c(UNPROVED 정지를 허용하는 조건부 계약)는 채택하지 않는다.** ④ 약화다.

## 3. 차등 비교의 역할 분리

| 층 | 강제하는 것 | 이유 |
|---|---|---|
| 개발·회귀 시험 | 기준 실행이 존재하는 모든 경우 **매 step raw 상태 비트 동일**, witness 수 = 거부 수 | 마지막 상태만 비교하면 중간에 다른 길로 갔다 돌아온 것을 놓친다 |
| 실제 runtime 계약 | **같은 입력 + 검증된 witness → 정확히 그 rounding 결과만 허용** | 실제 16384 STOP에서는 비교할 "정상 16384 기준 실행"이 존재하지 않는다 |
| 결함 주입(상시 유지) | 틀린 witness, witness 없는 재개, 다른 입력용 witness, stale binding을 모두 잡는다 | 검사기가 눈을 감고 있지 않은지 |

차등 비교는 **시험 계약**이지 runtime의 수학적 정의가 아니다.

## 4. 국소 prover (설계만 — 이번 문서 승인 뒤 별도 설계)

입력: 상대 위치 dr, 성분 k, kick 간격, momentum profile, binding. 출력(검증 가능한 주장 중 하나):
- "정확한 값은 half-ulp 경계 b의 **왼쪽/오른쪽**에 있다 → raw = X"
- "정확한 값은 b와 **정확히 같다**(tie) → half-even 결과 raw = X"
- 해결 못 함 → UNPROVED

후보 방법(비용 낮은 순, 실제 STOP이 난 한 점에만 적용하며 shell 전체에 미리 뿌리지 않는다):
1. 기존 rational/modular-distance 기법의 **한 점 판**: 충격량의 유리식 부분 P/Q와 경계의 정확한 거리(≥ 1/(2Q)형 하한)와 지수 잔여항·수치 오차 상한을 비교. shell 19〜23 family 인증에서 쓴 방식의 점 버전.
2. 정확한 tie 판정: tie가 가능한지 유리식·valuation으로 판정(④-4b fractional phase 조사에서 24/24 domain의 rational tie를 배제한 방법의 점 버전).

**P1(설계자 판정): 조건부 허용. 고정밀도는 증거를 찾는 도구일 뿐, 증거 그 자체가 아니다.**

```
금지: 16384에서 실패 → prover가 32768로 계산 → "32768 결과가 이거니까 믿어" → 진행   (cap 우회)
허용: 16384에서 실패 → prover가 필요한 만큼 계산 → 정확 유리수 부등식 등 검증 가능한 certificate 생성
      → 작은 verifier가 정확 산술로 확인 → raw가 수학적으로 확정 → 같은 step 재실행
```

**P1a 설계자 판정(2026-09-29): 아래 구현자 해석 채택.** 허용 certificate는 두 종류뿐이다.
**A.** cap ≤ 16384 안에서 나온 검증 가능한 interval witness. **B.** 실행기 평가기와 다른 수학적 근거(exact rational inequality, modular-distance bound, exact tie 판정, algebraic bound).
prover 내부에서 쓴 bit 수는 상관없다. 기준은 **"최종 certificate를 검증할 때 그 고정밀 계산 결과를 믿어야만 하는가?"**다.
예: prover가 65536 bit로 `2N < (2k+1)D`를 찾고 verifier가 N·D·k를 정확한 정수로 확인하면 허용한다. "65536-bit evaluator 결과가 이렇다"뿐이면 불허한다.
**P1b 설계자 판정(2026-09-29, 3차): 허용, P1a 문구 수정.** B의 조건은 "평가기와 다른 수학 방법"이 아니다(`a_numeric.exp.enclosure`도 Taylor + 나머지를 쓴다). 정확한 조건은 다음과 같다.
**16384 초과 평가기의 결과를 신뢰하지 않아도 certificate의 참/거짓을 독립적인 작은 checker가 exact arithmetic으로 판정할 수 있어야 한다.**
구현 공유 금지, `C._model` 호출 금지, `a_numeric.exp.enclosure` 재사용 금지. 같은 Taylor 정리를 써도 증명 객체와 checker가 독립적이면 허용한다.
감사: [Lemma A·B 감사 v0](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md).

**(판정 전 기록) 구현자 해석(P1a):** "작은 verifier"가 **실행기 평가기(`C._model`)를 16384보다 높은 정밀도로 다시 돌려** 구간을 재계산하고 반올림을 비교하는 방식은
정확 정수 산술이긴 하지만 사실상 "고정밀 결과를 믿는" 금지 패턴과 같다고 본다(평가기를 cap 위에서 한 번 더 돌리는 것일 뿐).
그래서 허용되는 certificate는 **verifier가 cap 이하 정밀도 또는 평가기와 다른 정확 부등식(유리식 거리 하한 + 잔여항·오차 상한 등)만으로 확인할 수 있는 것**으로 좁히기를 제안한다.
현재 prototype witness(평가기 재계산)는 cap 안에서만 쓰므로 이 해석과 충돌하지 않는다.

각 방법은 채택 전에 자기 checker(빌더와 다른 경로)와 결함 주입 시험을 가져야 한다. 방법이 하나도 승인되지 않은 동안 모든 실제 STOP은 UNPROVED다.

## 5. Proof Cache — 재사용 가능한 실제 증명

- **넣는 것:** 실제 cap(16384)에서 STOPPED였고, 승인된 prover가 만든 뒤 검증된 witness **만**. 128→256처럼 실행기가 스스로 푼 판정은 넣지 않는다(실측 약 0.64%, 2억 판정이면 백만 건 이상 — 넣으면 창고가 철길보다 커진다).
- **쓰는 때:** 실행기가 STOPPED를 낸 입력에 대해서만 조회한다. 실행기의 계산을 건너뛰는 용도가 아니다.
- **쓸 때마다** binding 일치 확인 + witness 전체 재검증(Warehouse Q3 "④ 동결 전 full re-verify"와 같은 원칙). 저장된 `status`를 믿지 않는다.
- binding이 하나라도 다르면 STALE — 쓰지 않고 다시 증명한다. 지우지 않는다(STALE·REJECTED 보존).
- **Proof Box 승격:** 여러 witness가 한 구간에 모이면, 그 구간 **전체가** 같은 반올림 결과를 가진다는 구간 증명(기존 multi-output region·hard-case 인증서와 같은 종류)이 있을 때만 box로 올린다. "비슷해 보여서" 묶지 않는다.
  box가 있으면 그 안의 처음 보는 입력의 STOP도 box로 풀 수 있다. 이미 인증된 14개 region은 이 의미의 box/domain이다.
- 저장 형식: prototype witness는 `runs/`에만 둔다(fixture 아님). 정식 Proof Cache의 형식·위치는 첫 승인된 prover와 함께 정한다.

## 6. Hazard Atlas — 통계 지도 (증명 아님)

- 내용: 판정의 R 구간·성분·최종 정밀도·128-bit 구간 폭 분포, 높은 정밀도(예: ≥ 4096 bit) 판정과 모든 STOP의 위치 목록. 이번 조사 결과(R 20〜320은 0.6%대, 320〜640 전환, ≥ 640은 항상 256)가 첫 내용이다.
- 쓰임: prover 작업 우선순위, 캐시 예열, 비용 예측. **어떤 판정도 대신하지 않는다.** 인증 입력 금지(Warehouse의 `survey_only`와 같은 지위).
- 시험: Atlas를 켜고 끈 실행 결과가 비트 동일해야 한다(S6).

## 7. witness binding (필수 필드)

모델 지문(`L.parameter_fingerprint()`), C1-A 동결 지문, 실행기·모델 소스의 LF 정규화 SHA-256, 위치/운동량 profile(이름·폭·소수 비트), dt, kick 간격, drift 규칙, retardation, 반올림 방식(half-even), 정밀도 schedule(128…16384), 정확한 입력 위치(유리수), 성분 축, **proof method와 그 checker의 해시**.
prototype은 proof method 필드가 없다(방법이 하나뿐). 정식 witness에는 추가한다.

## 8. 기존 원칙과의 충돌 — 설계자 판단 필요

| # | 충돌 | 내용 | 구현자 의견 |
|---|---|---|---|
| C1 | Warehouse 8절 "Warehouse는 A의 실행 경로에 없다" | Proof Cache는 STOPPED 때 **실행 중에** 조회된다 | **설계자 판정: 분리.** Proof Warehouse = 연구·증명 자산 보관소, A 실행 경로 밖. Runtime Proof Cache = 실제 실행 중 검증된 witness 재사용, 아주 작고 엄격, 매 사용 시 재검증. Hazard Atlas = 통계, 판단 권한 0. Cache의 검증된 자료를 Warehouse로 **복사해 연구 자산화**하는 것은 가능하지만, A가 Warehouse를 조회해 실행 결정을 내리는 경로는 없다 |
| C2 | 헌법 제2조(과정 보존)·RULES "캐시는 인과 영향 반경 전체의 정확한 입력이 같을 때만" | witness는 계산을 생략하는 것이 아니라, 실행기가 무한 정밀도라면 냈을 **바로 그 값**을 증명으로 제공한다. 입력 키가 충격량 입력 전체(상대 위치 전 성분 + binding)다 | 충돌 없음으로 본다. 다만 "캐시"라는 이름이 오해를 부를 수 있어 문서에서는 "Proof Cache = 증명 저장, 계산 캐시 아님"으로 못 박는다 |
| C3 | ④ 동결 조건 | 기존 ④는 "reachable enclosure 전체의 사전 인증"을 요구했다 | 이 제안은 **방법**을 바꾸고 **의무**는 Safety+Liveness로 유지한다. Liveness를 무엇으로 닫을지(L-a/L-b)는 설계자 결정 |
| C4 | Proof Warehouse 보류 결정 | "반올림 전략이 바뀌면 저장할 proof의 양·종류도 달라진다"는 이유로 보류했다 | 전략이 바뀐 지금, 저장 대상은 **실제 STOP의 witness와 box뿐**이라 훨씬 작다. Warehouse v0 재개 여부는 첫 실제 witness가 생긴 뒤 판단해도 늦지 않다 |

## 9. 설계자 판정 (2026-09-29)

| # | 질문 | 구현자 권고 | 판정 |
|---|---|---|---|
| D1 | 네 상태와 규칙(1절)을 계약으로 채택 | 채택 | 승인 |
| D2 | ④를 Safety/Liveness로 나누고 둘 다 있어야 ④ 동결(2절) | 채택 | 승인. **④의 정의는 약화하지 않는다** |
| D3 | ④-Safety가 A-EV에 조건부임을 명시하고, A-EV 강화는 별도 과제로 둠 | 채택 | **채택(후속 판정).** A-EV를 S1〜S6보다 앞선 **선행조건**으로 둔다. A-EV 미해결이면 ④-Safety는 Conditional(2.1절) |
| L0 | ④-Liveness의 대상 영역 | 설계자 결정 | **D_valid.** 실행 가능 영역(입장 계약)과 분리 |
| D4 | Liveness를 닫는 길 | 첫 prover 설계 뒤 결정 | **혼합형.** L-a 목표 유지·전수 열거 방법 폐기, L-b 단독 불가, L-c 불채택 |
| P1 | 별도 prover의 16384 초과 정밀도 | 기본 불허 | **조건부 허용.** 고정밀은 탐색 도구, 재개는 정확 산술로 검증 가능한 certificate가 있을 때만. **P1a 채택(후속 판정, 4절):** 평가기 재실행 verifier 불허, A/B 두 종류만 허용 |
| D5 | 차등 비교는 개발·회귀 시험 계약, runtime 계약은 "같은 입력+검증된 witness"(3절) | 채택 | 승인 |
| D6 | Proof Cache를 Warehouse와 분리, STOPPED 입력에만(C1) | 채택 | 승인 |
| D7 | Hazard Atlas는 survey_only, 결과 비간섭 시험 필수 | 채택 | 승인(판단 권한 0) |
| S1 | 남은 Fail-Closed 시험 두 개 | 바로 추가 | 승인 → **완료**(8 passed) |

승인된 구조:

```
④-Safety   애매하면 STOP · 상태 변화 없음 · witness 없으면 진행 금지 · witness는 재검증 · cache가 없어도 결과 동일
           → runtime 구조로 닫는다. 선행조건 A-EV(D3). A-EV 미해결 동안은 Conditional
④-Liveness 대상 D_valid. 모든 허용 상태가 결국 RESOLVED 또는 증명 가능한 WITNESS_RESOLVED로 끝난다는 별도 수학적 보장
           → NotCertified
실제 16384 실패 → point prover (고정밀 사용 가능) → 정확 검증 가능한 certificate가 있을 때만 재개
                → 증명 못 함 = UNPROVED = 영구 STOP
```

## 10. 다음 순서

**설계자 판정(2026-09-29, 순서 변경):** 제안했던 "wrapper → point prover → Liveness 조사"를 **"Liveness 경로 조사 → point prover 설계 → 정말 필요하면 runtime wrapper"**로 바꾼다.
기계장치(STOP·상태 불변·witness 검증·재개·매 step 동일)는 prototype으로 가능성이 이미 확인됐다. 실제 16384 실패도 승인된 witness 방법도 0개인 지금 wrapper를 먼저 만들면 기능 없는 교통경찰부터 세우는 꼴이다.

1. ~~S1의 남은 Fail-Closed 시험~~ — 완료(`VMHalt`, 운동량 범위; 8 passed).
2. ~~④-Liveness(D_valid) 수학 경로 조사~~ — [조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 완료(survey_only, 문서만). 결론: 정량 Liveness의 싼 경로 없음. 전역 exact tie 배제 + 엄밀 구간 prover의 정성 경로가 유일한 후보. Q1〜Q4 판정 완료(2.2절·4절).
2a. **Lemma A(전역 no-tie)·Lemma B(독립 certificate 수렴·검사 가능) 감사** — [감사 v0](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md). 구현자 감사 통과(인증 아님). **설계자 판정 대기.** 승인되면 독립 checker + 시험을 구현한다.
3. **point prover 설계 문서**(P1/P1a/P1b 반영): certificate 형식, 작은 verifier, 결함 주입. 승인 뒤 구현. 실제 STOP이 없으므로 cap을 낮춘 rehearsal과 합성 사례로 시험한다.
4. 정말 필요하면 네 상태를 코드 상수·결과 기록으로 표현하는 **얇은 runtime wrapper**(실행기 무변경, prototype 대체).
5. Runtime Proof Cache·Hazard Atlas는 첫 승인된 prover가 생긴 뒤.
6. **④ 최종 동결 전 정리 대상:** `_decide` 안의 `VMHalt`(감싸지지 않음)와 다른 범위 초과의 `ExecutorLimitExceeded` 사이의 예외 분류 불일치. 둘 다 fail-closed지만 taxonomy가 일관되지 않다. 새 방향 설계와 섞이지 않게 지금은 실행기를 고치지 않는다.

이번 문서로 바꾸는 코드는 없다. 궤적 추가 주행·shell 14 탐색도 하지 않는다.
