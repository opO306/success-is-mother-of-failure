# 현재 상태

**ADAPTIVE_EXECUTION_VERIFICATION_V0 오프라인 검증(2026-10-08):**
[설계·봉인·제한 구현 상태](docs/active/ADAPTIVE_EXECUTION_VERIFICATION_V0.md).
별도 `codex/adaptive-execution-verification-v0`, V1/원본/GPU V1/물리/반올림/P2 보존.
프로토콜·예산·승격 기준을 구현 전 `f135cd92`로 봉인. 경험 수집·별도 원본 판독 검사·
오프라인 프로필·다음 요청 snapshot/복귀 구현. Vast 원격 시험 24 passed/0.61초, 35개 기록 별도 판독
VERIFIED/errors 0. 과거 세션 비용 프로필 1개, OFFLINE_VALIDATED_ONLY / NOT_PRODUCTION.
외부 guardian DEADLINE·COMPLETED actual=exited 확인, 초기 CLI 응답 형식 오류 1건 보존 후 수정.
RwForce 독립 수식·OS 권한 격리·실서비스 연결 미해결. 로컬 수치 실행·새 궤적·GPU 호출 0,
master merge/push 없음, 기존 Gate·공식 시험 기준선 불변.

**최종 갱신:** 2026-10-03 — 현재 상태 대시보드. 과거 기록은 [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)에 원문 전체를 보존한다.

## 현재 우선순위와 활성 Gate

**Exact Expression Gate V1 (2026-10-05, SURVEY_ONLY / ALTERNATIVE NUMERIC WORLD SEMANTICS):** [결과](docs/active/EXACT_EXPRESSION_GATE_V1.md), 봉인 `1c0e751`. 설계자 통합 판정(EXPERIMENT NEEDED) 단계 0·1·2 이행. V0는 수정하지 않음.
판정 **COMPARISON_COMPLETE**(승자·승격 없음): 70작업 완료, 독립 replay 12/12, 봉인 주장 K1〜K5·예측 P1〜P5 전부 HOLDS. 도메인 의무를 B의 접힘 뒤에도 유지(V0 B는 거리 0을 통과시켰음), 경로별 독립 정밀도 탐색.
C_stream은 replay와 끝점 해시까지 동일. 1…100 step 전부 질의에서 C가 32/34/40배 CPU, 드문 체크포인트에서는 동률. DAG는 시간 이득 없고 피크 RSS만 큼(최대 145 vs 31 MB). 정확 동점 반례는 B·CX만 64비트에 결정.
**공개:** CX는 "국소 대수 + 스트리밍"이 아니라 정확 수 유지 정도라 상호작용 시나리오에서 C_stream과 같음(P5는 자명한 통과), 시간은 1회 측정·6작업 동시, 1,000 step까지, 검사기는 힘 식(lang_iv)을 공유. 관련 시험 통과, LOCAL FULL 생략.

**Exact Expression State Gate V0 (2026-10-05, ALTERNATIVE NUMERIC WORLD SEMANTICS / SURVEY_ONLY):** [결과](docs/active/EXACT_EXPRESSION_STATE_GATE_V0.md), 봉인 `848ceaf`(+저장 형식 수정 `9dfd3f8`).
판정 **EXPRESSION_WALL**(REPLAY_DOMINATES와 3:3 동수, 동수 규칙 미봉인 공개). 식 크기 step 선형, 최적화 1.5〜2.2×, 3원자 10,000 step 상태 약 200만 단위.
식 평가 ≈ replay 속도. 인증 비트 10,000 step에서 192〜512(실제 민감도 2〜21 bit, 대부분 구간 과대추정). 자유 비행만 O(1)로 접힘.
자유 비행 판정 규칙 결함 공개(정밀도를 A 경로로만 측정). 관련 시험12 PASS, LOCAL FULL 생략.

**Multiparticle Residual / Carry Gate V1 (2026-10-05, SURVEY_ONLY):** [결과](docs/active/MULTIPARTICLE_RESIDUAL_CARRY_GATE_V1.md), 봉인 `a361c0f`.
판정 **B — U_AND_L_EQUIVALENT_BUT_COST_UNRESOLVED**. 설계자 carry(U)와 ledger(L)는 같은 의미(정규화 시점만 다름).
정확 유리수 입력에서 핵심 조건 9개 통과(보존·집단 효과·순서/번호 무관·drift가 P+r 사용·STOP 0·O(N)).
실제 Lang 충격량은 유한 잔여 격자가 필요해 R = 더 고운 격자의 P(손실 2⁻ᵏ배로 축소, 0 아님). 일반 유리수 잔여는 비트 수 무한 증가.
C1-B1 drift의 위치 격자 반올림도 계통적 손실 발견(별도 판단 대상). 관련 시험25 PASS, LOCAL FULL 생략.

**Multiparticle Rounding Gate V0 (2026-10-05, SURVEY_ONLY):** [결과](docs/active/MULTIPARTICLE_ROUNDING_GATE_V0.md), 봉인 `d4d43b3`.
P/T/C 모두 N=2 C1-B1 동일·번호/순서/평행이동 무관. P: 보존 항상, 집단 효과 손실(원거리 중심 3.03 u → 0). T: 오차 ≤0.5 u, 보존 깨짐(N=4 전수 32%·실제 배치).
C(새 후보): 보존, 그러나 STOP N=4 전수 25.6%·실제 원거리 배치. 법칙 선택은 설계자 결정. 관련 시험12 PASS, LOCAL FULL 생략.

**Nuclear State / Dynamics Gate V2 (2026-10-05, SURVEY_ONLY):** [결과](docs/active/NUCLEAR_STATE_DYNAMICS_GATE_V2.md), 봉인 `6ebc808`.
CT-MQC 후보로 "분리·위상 보존 + 비지수적"을 보이지 못함: S1 갈래 분리 3/3 궤적 수 수렴 실패(REFUSED, Rf4에서만 부호·크기 근접),
궤적별 에너지 최대 0.6 hartree 변화, S3 궤적 영역 이탈(UNSUPPORTED). 기계 검사(EHA = V1 Ehrenfest) 통과.
**시험 설계 실패 2건:** S2 수정판은 Wigner 질량 40%가 장벽 위(터널링 시험 아님), S3는 Q 결과가 단조 변화라 간섭 미입증.
실패 중단 규칙으로 다음 단계 자동 착수 없음. 관련 시험32 PASS, LOCAL FULL 생략/공식 기준선 불변.

**Nuclear State / Dynamics Gate V1 (2026-10-04, SURVEY_ONLY / 모델 시험 세계):**
[결과](docs/active/NUCLEAR_STATE_DYNAMICS_GATE_V1.md). 1D Shin–Metiu에서 Q(양자 핵+전자)/EH/BOQ/BOCL 비교, 실행 전 봉인 `b8f2b65`.
S1: BO 두 방식은 전이 ABSENT·전자 위치 DISTORTED(3/3), EH는 전이·전자 위치 REPRESENTED(3/3)지만 핵 갈래 분리 DISTORTED/REFUSED.
S2 장벽: 고전 핵 터널링은 표본 비수렴으로 판정 불가, Rf6 기준선 격자 수렴 실패로 REFUSED. 양자 핵은 핵 수에 지수적.
방법 선택 없음(설계자 결정). 관련 시험18 PASS, LOCAL FULL 생략/새 survey 패키지·문서만/공식 기준선 불변.
RULES §1 숫자 규칙 개정(`21fffab`, 문구 설계자 확인 대상).

**일반 핵·전자 세계 최소 계약 V0.1 — 설계자 승인(2026-10-04, 원칙·판정 체계 범위):**
[계약](docs/active/GENERAL_ATOMIC_ELECTRONIC_WORLD_CONTRACT_V0_1.md)·[V0 원문](docs/active/general_world_contract_v0/V0_ORIGINAL.md).
Gate 0-A World Definition DECIDED(승인된 현실 근거 법칙의 결정론적 실행 = A 세계) /
0-B Quantum Outcome Definiteness UNRESOLVED → 가상 실험실 진행 가능, L/B 단일 역사 세계 불가.
H₂는 benchmark/회귀 전용. 핵 운동·전자기장·표현·경계 선택 미승인. 다음: RULES §1 개정 문구 → 첫 일반 가상 실험실 최소 조건 → Gate 1.
근거 전자 연구(Sector/State-History/Survey/Hotline)는 원격 브랜치 `codex/electronic-compressibility-hotline-v1`(`d721435`)에 있고 master 미merge.
문서만 변경, LOCAL FULL 생략/공식 기준선 불변.

**C1-B1 Combined production opt-in 승격(2026-10-03):**
[최종 gate·성능·production Top10](docs/active/C1B1_COMBINED_PRODUCTION_PROMOTION_V1.md),
[독립 산술 promotion 감사](docs/active/C1B1_COMBINED_PROMOTION_AUDIT_V1.md).
Combined만 PRODUCTION FAST-PATH CANDIDATE, 실제 producer에 fast_combined opt-in 연결.
기본 fast(Candidate B)와 slow reference/기존 Fraction/proof/checker 보존, 원래 step code 사용.
REF/B/Combined6개55845step 및 기존거부4/실제STOP1/추가악성9 차등·source closure PASS.
독립 산술감사 및 FULL3903+1 strict xfail, 실패·error·실제skip0,742.24초, 기존warnings25.
같은Ryzen5600/worker1/affinity11/3repeat CPU: drift1.514x,kick4.364x,step1.147x,
6trajectory1.122x(B대비), 누적REF대비1.584x 직접 측정. CPU10.9076% 감소.
production step만의 profileTop10 별도완료, 기존FAST derivative11.9468% 최상위; 다음대상미선정.
Fraction routes27.5010%/gcd27.4606% 감소는 동일R20 연구용stop 포함 비교profile 범위다.
정상bigint132/139/180bit, 분모누적없음. 더큰scope/정식증명/A-EV/native J/replay승인은 별도.
로컬promotion브랜치 보존, rootmaster4160557 유지, mainline merge/push/새CONFIRMED 없음.


**별도 C1-B1 Pilot2 prepared drift / raw 정수 산술(2026-10-03):**
[결과와 보존된 실패](docs/active/C1B1_PREPARED_DRIFT_PILOT2_V1.md),
[조건부 exact 산술 논증](docs/active/C1B1_PILOT2_EXACT_ARITHMETIC_ARGUMENT_V1.md).
독립 `codex/c1b1-pilot2-prepared-drift` worktree의 opt-in 분석·후보이며 production 미적용.
기존 slow REF·현재 FAST impulse·step code·rounding·guard·cap·proof/checker 보존.
같은 d=p*dt/m을 성분당2회에서1회로 준비하고, B는 약분하지 않은 정수 쌍,
C는 같은 momentum 격자의 raw kick을 사용한다. 실제 guard에는 exact endpoint를 전달한다.
새121시험/관련199시험 및 FULL3865+1 strict xfail, 실패·error·실제 skip0; 기존 경고25.
측정 첫 closure의 짧은 CPU0초 샘플을 보존하고 배치를1e6회로 늘려 새 source/input 실행.
새 benchmark Combined CPU step1.086x / 여섯 궤적1.128x; profile/전체 source-input closure PASS.
Fraction 두 생성 경로 합계27.5010% / gcd 호출27.4606% 감소. 실제 raw drift bigint
132/139/180bit이며 분모 누적 성장 없음. A/B 단독 step CPU 개선은 미충족/미확정이다.
Combined는 측정 조건에서 승격 검토 가치가 있지만 production NOT_APPLIED. local commit만 보존한다.
공식 AGENTS 기준선·기존 C1-B1 Gate·A-EV/native J·새 CONFIRMED history는 갱신하지 않는다.

**C1-B1 Candidate B master 통합·runtime 활성화(2026-10-03):**
[단계별 결과·한계·새 병목](docs/active/C1B1_CANDIDATE_B_RUNTIME_ACTIVATION_V1.md).
master는 6c53eec→951b076 fast-forward. 실제 production replay producer에 별도
`c1b1_runtime` 선택기를 연결해 FAST 기본 / 명시적 reference mode를 제공한다.
slow REF·generic model·proof/checker·historical O-1/witness wrapper·물리 계약은 보존했다.
master FULL 3713+1 strict xfail(717.36초), activation FULL 3744+1 strict xfail(702.25초),
양쪽 fail/error/actual skip0, 기존 warnings25. 공식 AGENTS 기준선은 불변.
새 source/input closure 및 6개 산란55,845 step / 거부·실제 cap STOP5건 차등 PASS.
실제 producer의 preserved 입력1491 step도 REF/FAST 동일. 새 CONFIRMED history는 아니다.
로컬 CPU median impulse1.600× / step1.410× / 기존3개궤적1.385× / 전체6개1.410×.
FAST6개 완주 profile의 자기 CPU 상위5개와 이론상 상한을 기록했으며 다음 대상 미선정.
정식 증명·전체 물리 영역·무한 궤적·cap 내 보편적 결정·A-EV/native J는 미해결/별도 Gate다.
local commit, push 없음. 아래 10-02 후보 승격은 기본 경로 변경 전의 당시 기록이다.


**별도 C1-B1 Candidate B 최적화 승격(2026-10-02):**
[최종 결과·범위](docs/active/C1B1_CANDIDATE_B_PROMOTION_V1.md),
[독립 primitive 감사](docs/active/C1B1_CANDIDATE_B_PRIMITIVE_AUDIT_V1.md).
PRODUCTION FAST-PATH CANDIDATE / NOT FORMALLY CERTIFIED.
같은 source/input의 fresh run에서 evidence·audit·endpoint/raw·fault·LOCAL FULL·trajectory·benchmark PASS.
LOCAL FULL 3713 passed + 1 strict xfailed / 실패·error·실제 skip 0, 774.77초; 공식 AGENTS 기준선은 불변.
실제 3개 산란 34,305 step와 거부 4개에서 REF/FAST raw·상태·예외 일치.
로컬 CPU median impulse 1.880× / step 1.475× / 선정한 R20 출구까지 3개 완주 trajectory 합계 1.400761×(28.61% 절감).
slow generic model·energy·potential·step 보존, 별도 impulse/step_fast 제공, 기본 경로 자동 변경 없음.
최초 FULL의 historical artifact 누락 2개 실패 및 cp949 경고 25건을 보존했다.
A-EV·native J·전체 C1-B1 Gate·H2/foundation 상태 승격 없음. local commit만, push 없음.

**H₂ same-basis numerical 원인 분리 후속(2026-10-02):**
[수치 원인·미해결 범위](docs/active/H2_NUMERICAL_CAUSE_ISOLATION_V1.md).
원래 누락 16점 재현, 3 coordinates/2 backends의 기존 accepted controls 60개 통과.
동일 AO의 대표 coupling에서 AO 비대칭 전파와 binary64 변환·행렬 구성 오차를 분리했다.
선택 봉인 뒤 fresh QZ 44-point 실행은 34 accepted / 10 refused, QZ minimum·전체 curve 미해결.
NUMERICAL CAUSE IDENTIFIED(조사 범위) / SAME-FINITE-BASIS 표본 동등성 / NOT CERTIFIED.
Windows 관련 43 passed, 별도 WSL 49 passed, failure/error/skip 0.
LOCAL FULL 생략 / 새 독립 진단·시험·문서, 기존 source/fixture 불변 및 관련 시험 대체 / 기준선 불변.
기존 H₂ 원본과 C1-B1/production/foundation 상태 보존, push 없음.

**별도 고정 핵 H₂ static reference pilot(2026-10-02):**
[결과·한계](docs/active/H2_STATIC_REFERENCE_PILOT_V1.md).
IMPLEMENTED / TESTED / NUMERICALLY COMPARED / NOT CERTIFIED.
132 point 중 116 numerical result, 13 numerical refusal, 3 refusal-message errors 보존.
DZ/TZ의 R=1.4 bohr 내부 표본 최소와 세 basis의 같은-basis 2H 해리 방향은 관측됐다.
QZ 0.4–1.4 미계산으로 QZ minimum·전체 곡선 비교 미해결.
QZ supported 33점 max difference 0.000762525 hartree는 전체 PASS가 아니다.
production foundation/전자·핵 dynamics/formation/기존 C1-B1 Gate 상태 승격 없음.
Windows 관련 25 passed, 별도 로컬 WSL 27 passed, skip/failure/error 0.
LOCAL FULL 생략 / 새 독립 pilot·시험·문서만, 관련 시험 대체 / 공식 기준선 갱신 없음.
commit 허용 작업, push 없음.

| 계통 | 상태 | 진행 기준 |
|---|---|---|
| **A** | **ACTIVE** | 최우선. 세계의 물리 기반을 먼저 검증한다 |
| **L** | **DEFERRED UNTIL A FOUNDATION IS SUFFICIENT** | A의 기반이 충분히 생긴 뒤 A 안에서 자연 발생·진화하는 계통으로 진행한다 |
| **B** | **DEFERRED TO LATE STAGE, NOT CANCELLED** | A와 L이 어느 정도 완성되어 작더라도 “세계가 돌아간다”는 단계 뒤 마지막 단계에서 본격적으로 만든다 |

B를 중단·폐기한 것이 아니다. 기존 **B-classic 구현·문서·시험은 보존**하며 나중에 비교군/연구 자산으로 사용한다.
L은 별도로 생명 행동을 명령해 만드는 대상이 아니다. A의 물리에서 발생과 진화를 관찰한다. 생명·복사·진화의 새 증거는 아직 없다.

| 현재 진행 | 상태 |
|---|---|
| **현재 활성 Gate** | **C1-B1** (세 층 분리 기준으로 종료 조건 재정의, 2026-10-01) |
| **현재 세부 단계** | **Gate 잔여: A-EV(별도 작업선). `_decide` 예외 분류 및 source-binding 재감사 완료. production replay verifier V1 지정 fingerprint 조합 승인 완료(8996aa60). 관측 O-1 V1: AGREE 8 / DISAGREE 1 / UNRESOLVED 0, rho=-0.001의 절대 각도 기준 초과로 STOP; O-1 전체 통과 아님. O-3 weak 미착수. 별도 Gate: native J 비트 동등성. 전 궤적 사전 증명(④ step 4, S4d δ, global shadowing 등)은 연구 과제** |
| **다음 Gate** | **C1-B1 종료 → 다원자 기체 단계(첫 항목: 적분기 에너지 범위 확장, 강한 O-3 = 희박 Ar 점성) → C1-C 전 N-1 재평가** |

위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 FROZEN이 아니며 ⑤는 시작하지 않았다.**
2026-10-01 세 층 분리 결정으로 ④의 "전 궤적 사전 증명" 부분은 Gate에서 연구 과제로 이동했다(삭제·실패 판정 아님).
④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결 상태 표기는 그대로 유지한다.

**`_decide` 예외 분류·소스 결합 재감사 완료(2026-10-01):**
[제한된 재감사 보고서](docs/active/C1B1_SOURCE_BINDING_REAUDIT_V1.md).
실제 작업 시작 HEAD/origin/master는 `bdc9bfe7c5c763c2900121e4d8f2bcdcf56782e8`, clean이었다.
기존 예외 분류는 유지하고, `53b73ea`의 정상 proof 입력에서 함수 의미와 수학 본문을 대조했다.
기존 generator/checker로 증거 11개를 재생성해 certificate/bound/candidate/group/판정 등
전체 수학적 payload의 동일성을 확인했다. 원래 기대 hash·고정 parent inventory 8개와
역사 원본 20개를 보존하고, 감사한 변환만 허용하는 소스 결합을 추가했다.
관련 **364 passed(80.21초)**, 최종 **LOCAL FULL 3483 passed + 1 strict xfailed,
실제 skip 0, failure/error 0, exit 0, 25 warnings, 684.98초**. 기존 native 출력 해독 경고는
해결하지 않았다. 공식 AGENTS 기준선은 설계자 판정 없이 갱신하지 않는다.
새 bound/lemma/Certified region 0개. A-EV·D_valid·④ 전체 재증명 아님.
승인 replay verifier와 7개 CONFIRMED test history, 기존 네 상태는 그대로다.
O-1/O-3/native J/live pipe/rollback controller·새 물리는 시작하지 않았다. push 없음.

**O-1 독립 수치 재현 V1(2026-10-01, 기준 `f03fb30`): DISAGREE / STOP.**
[보고서](docs/active/C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md),
[사전 프로토콜](docs/active/C1B1_O1_PROTOCOL_V1.md),
[입력 봉인](docs/active/C1B1_O1_INPUTS_V1.json),
[전체 수치·비용·원본 해시](docs/active/C1B1_O1_RESULTS_V1.json).
입력 10개 봉인 → 새 궤적 9개/104,843 step 전부 approved production replay로
REPLAY_VERIFIED / CONFIRMED → 별도 공개 PES 파서·40/60/80자리 연속 radial quadrature와
Cartesian DOP853 보조 확인. reference step/force/rounding을 독립 계산기에 재사용하지 않았다.
**AGREE 8 / DISAGREE 1 / UNRESOLVED 0 / 미실행 1**.
E=0.5 De, rho=-0.001, b=11.707286169880804 bohr(기존 D_valid unsupported)의
각도 차이 1.30928186e-5 rad > 사전 절대 1e-5. 독립 60→80자리 각도 차이
8.40e-51 rad, 별도 ODE와 7.93e-11 rad 차이. 다음 rho=-0.0001은 실행하지 않았다.
최접근 거리·에너지 기준은 만족. 어느 계산기가 틀렸다고 자동 판정하지 않는다.
O-1 전체 통과/전체 D_valid 인증 아님. V1 종료 당시 원인별 분리는 미실행이었으며, 후속 사용자 지시에 따른 진단은 아래 별도 기록이다.
기존 7개 PIPELINE_TEST_ONLY history 재사용·의미 변경 없음. 물리/PES/dt/r_min/D_valid/승인 verifier 변경 0.
LOCAL FULL **3501 passed + 1 strict xfailed, 실제 skip 0, failure/error 0, exit 0,
25 기존 cp949 warnings, 669.38초**. 공식 AGENTS 기준선은 갱신하지 않았다.
순차 campaign wall 1176.569초; 기록 단계 CPU 합 1084.484초. 원본 runs 보존.
O-3·A-EV·native J·live pipe·rollback controller·④ 재증명 미착수, commit/push 없음.

**O-1 단일 불일치 원인 격리 V1(2026-10-01, 기준 `504e837`): numerical diagnostic.**
[진단 보고서](docs/active/C1B1_O1_CAUSE_ISOLATION_V1.md),
[실행 전 프로토콜](docs/active/C1B1_O1_CAUSE_ISOLATION_PROTOCOL_V1.md),
[입력·소스·원본 해시 봉인](docs/active/C1B1_O1_CAUSE_ISOLATION_SEAL_V1.json),
[전체 결과](docs/active/C1B1_O1_CAUSE_ISOLATION_RESULTS_V1.json).
같은 boundary_pass raw의 별도 HP-KDK40과 production A 각도 차이는 2.20133e-11 rad,
HP-KDK40과 연속 기준의 차이는 1.30928e-5 rad다. 40→60자리 변화 4.96446e-38 rad.
사전 원인 분리 기준은 TIME_DISCRETIZATION_SUPPORTED이며 dt20/10/5 관측 진단을 허용했다.
dt20/10/5의 출구 반경을 맞춘 각도 오차는 3.27318e-6 / 8.18295e-7 / 2.04574e-7 rad,
실측 수렴률은 세 구간 모두 약 2차다. 진단 5회(precision 비교 포함)/276,544 step 보존.
기존 O-1 DISAGREE / STOPPED / NOT PASSED, 기존 D_valid unsupported, 9개 CONFIRMED 의미를 유지한다.
production dt/profile/PES/허용오차/D_valid/승인 verifier를 변경하지 않았다. 형식 인증이나 Gate 승격이 아니다.
관련 140 passed + 1 strict xfailed, 실제 skip 0, failure/error 0, 37.33초.
LOCAL FULL 생략 / 독립 관측 코드·시험·문서만 추가, 기존 protected 소스 불변 확인 및 관련 시험으로 대체 / 기준선 갱신 없음.
O-3·A-EV·native J·adaptive dt·substep 등 금지 작업 미착수. commit/push 없음.

**outer dt40 적분기 비교 V1(2026-10-01, 기준 `508bba4`): C — 아직 판정 불가.**
[원격 제어 실패 보고서](docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md),
[실행 전 프로토콜](docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md),
[봉인](docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_SEAL_V1.json),
[결과·실패 기록](docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_RESULTS_V1.json).
Yoshida4/Chin4A 두 독립 후보·기존 9개 입력·기준을 실행 전에 봉인했다.
Vast 시작/제어 시도 3회 실패로 AGENTS 중단 규칙 적용. 첫 두 원인 미확정,
세 번째는 SDK retry=0 사용 실수로 start HTTP 요청 미전송. Ar-Ar 궤적·원격 시험·비용 probe 0건.
사용한 노드 및 최종 기존 네 인스턴스 exited/stopped 확인. 후보 정확도·수렴·비용은 미측정이다.
관련 작은 대수 시험 14 passed(0.65초), 기존 protected 134 및 기존 원본 97+27 hash 불변.
LOCAL FULL 생략 / 새 독립 진단·시험·문서만 추가, 관련 시험으로 대체 / 기준선 갱신 없음.
production/기존 O-1 STOP/원인 격리 판정 변경 없음. commit/push 없음.

**SSH 정보 제공 후 재개(2026-10-01, 기준 `130df0d`):**
[재개 기록](docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_SSH_RESUME_V1.md).
9975WX/265K의 새 시작 응답은 resources_unavailable였다. 5950X는 시작했고,
직접 SSH의 Python 3.12.3/sentinel 및 scp 전송을 확인했다. source 사전 검사에서
Windows tar의 D: prefix 제거에 따른 Linux alias 복원 누락으로 중단했다.
archive 272개 hash 대조 불일치 0, 복원 수정안 준비·Linux 실행 미시험.
수치 궤적/원격 시험/비용 probe 0. 최종 기존 네 노드 exited/stopped.
기존 봉인·원본·C 판정 불변. 이번 14 passed 재실행 아님. LOCAL FULL 생략(문서·배포 준비만), push 없음.

**플랫폼 독립 배포 및 dt40 수치 비교 완료(2026-10-01, 기준 `130df0d`): C — 전체 비용 판정 불가.**
[실행·비교 보고서](docs/active/C1B1_DT40_PORTABLE_DEPLOYMENT_V1.md),
[전체 결과](docs/active/C1B1_DT40_PORTABLE_RESULTS_V2.json).
`code/`·`reference/` 상대 배치와 원본 272개 보존·위치 변경 별도 봉인으로 경로 장애를 해결했다.
portable v1은 역사 시험 조회 2개 실패로 궤적 전에 중단·회수·종료했고, v2 실제 복원 시험을 통과한 뒤 재개했다.
Yoshida outer40은 기존 9개 입력 모두 관측 기준 및 40/60자리 안정성 PASS;
boundary_pass 각도 오차 6.1096203e-11 rad. Chin 4A는 5.2560113e-13 rad이나 비용 상한으로 첫 단계 탈락.
같은 노드의 봉인된 kernel 비용은 KDK20 두 step 대비 1.471993배 / 2.174726배다.
원문 `B_KERNEL_COST`는 측정한 kernel에서 더 비싸다는 결론이며, 동일 노드 전체 KDK20 비용이 없어 전체 질문은 C로 남긴다.
새 후보 궤적 20회 / 244,266 outer step, 기존 baseline 궤적 재생성 0, 결과/로그 52개 회수·hash 일치.
원격 exit 0, 사용 노드 stop 및 기존 네 노드 모두 exited/stopped 확인. GPU 계산 없음.
신선한 관련 시험 로컬 57 passed(18.08초), 복원 package 49 passed(2.23초), 원격 49 passed(1.45초), 모두 failure/error/skip 0.
LOCAL FULL 생략 / 새 독립 배포 도구·시험·문서만, 기존 source 12·protected 134·O-1 원본 97·원인 격리 원본 27 hash 불변 / 관련 시험 대체·기준선 갱신 없음.
production·기존 O-1 STOP·D_valid unsupported·원인 격리 판정 유지. O-3 등 금지 작업 미착수, commit/push 없음.

**KDK20 vs Yoshida40 동일 노드 전체 비용 준비(2026-10-01, 기준 `63e5b95`): C / INCONCLUSIVE.**
[실행 보고서](docs/active/C1B1_KDK20_YOSHIDA40_COST_V1.md), [실패·환경·해시](docs/active/C1B1_KDK20_YOSHIDA40_COST_RESULTS_V1.json).
같은 60자리/observer/저장 정책의 순차 성능 하네스와 warm-up/혼합 3회/9-input 계획을 봉인했다.
로컬 새 폴더 복원 원본 272/객체 286 hash 일치, 복원 시험 60 passed(2.51초), 로컬 관련 68 passed(24.42초), failure/error/skip 0.
5950X 시작·직접 SSH는 성공했으나 SCP package upload 중 remote host connection closed / Broken pipe / exit 1로 실패했다.
원격 hash/시험/성능 실행 미착수: warm-up 0 / single 0 / panel 0. 원인 미확정, 두 방법의 비용 우열 미측정.
사용자 12절 infrastructure 오류 STOP에 따라 추가 유료 시도 없이 종료했고 네 노드 모두 exited/stopped 확인.
제어 구간 163.375초·가격×시간 참고값 $0.00867299(청구액 아님). 이전 시간을 새 성능 결과로 사용하지 않았다.
LOCAL FULL 생략 / 사용자 14절 및 독립 benchmark·도구·시험·문서만 추가, 기존 source/fixture 불변 / 관련 시험 대체·기준선 갱신 없음.
기존 O-1 STOP 및 다른 Gate 상태 유지. Chin/새 방법/force 최적화/production 수정 미착수, commit/push 없음.

**KDK20 vs Yoshida40 로컬 전체 비용 완료(2026-10-01, 기준 `2c17350`): B / YOSHIDA_ACCURATE_BUT_COSTLIER.**
[로컬 보고서](docs/active/C1B1_KDK20_YOSHIDA40_COST_LOCAL_V1.md), [전체 수치·환경·해시](docs/active/C1B1_KDK20_YOSHIDA40_COST_LOCAL_RESULTS_V1.json).
사용자의 로컬 실행 지시에 따라 Ryzen 5 5600/Windows/Python 3.12.7/mpmath 1.3.0/60자리/CPU 11 affinity/worker 1개로 순차 비교했다.
warm-up 2회 제외, 문제 입력 K/Y 혼합 각 3회와 기존 9-input 방법별 1회를 완료했다(총 26 궤적, exit 0).
문제 입력 median CPU/wall Yoshida/KDK 비율 1.405998/1.409347, 반복 변동은 사전 1.2 상한 안이다.
9-input 합계 KDK CPU/wall 297.625/301.430784초, Yoshida 415.546875/436.887645초: 1.396210/1.449380배.
양쪽 관측 기준 9/9 PASS. 기존 Yoshida 9개와 KDK boundary_pass 재현 PASS; 나머지 KDK 8개는 이전 method 결과가 없어 재현 주장하지 않는다.
26 trace hash/CRC/step 순서·521,975 records와 결과/log 85개 hash 확인. 기존 수치 source 12/보호 대상 134/O-1 97/원인 격리 27개 불변.
관련 시험 70 passed(19.36초), failure/error/skip 0. LOCAL FULL 생략 / 사용자 14절·독립 도구/시험/문서만 추가 / 관련 시험 대체·기준선 갱신 없음.
로컬 다른 부하 미통제, panel 방법별 1회, peak memory는 checksum 준비를 포함한 worker 전체 값이다. 내부 negative-stage 위험·production 미채택·기존 O-1 STOP 유지.
Vast 시작/SSH 없음. 기존 원격 실패·봉인 보존, production/공용/동결 source 수정 없음, commit/push 없음.

**Yoshida40 후보 보존 결정(2026-10-01, 기준 `9e794a8`): VALIDATED NUMERICAL CANDIDATE / NOT PRODUCTION / NOT FORMALLY CERTIFIED.**
[후보 상태·재검토 조건·보존 자산](docs/active/C1B1_YOSHIDA40_CANDIDATE_STATUS_V1.md).
증거 등급: implemented / numerically validated on sealed C1-B1 O-1 panel / cost benchmarked locally / not production / not formally certified.
YOSHIDA_ACCURATE_BUT_COSTLIER 유지. 봉인된 9개 입력에서 KDK20도 현재 1e-5 rad 관측 기준을 만족하므로 추가 정확도의 비용을 이유로 production 채택 보류, 후보 폐기 없음.
더 엄격한 관측 오차 요구, KDK timestep 축소 비용 증가, 고정밀 reference 필요 시 재평가하되 자동 승인하지 않는다.
negative internal stage 위험은 r_min/hard domain/many-body/충돌/화학/불연속·조건부 모델에 별도 검증 필요. 표본 성공은 formal proof나 A 전체 안전성 증거가 아니다.
구현·harness·시험·coefficients/input seals·기존 JSON/보고서·로컬/원격 결과·실패 배포 기록 보존. production/Gate/기존 O-1 STOP 변경 없음.
이번 단계는 문서만 변경, 새 수치 실험·Vast 계산 없음. 관련 단위 시험 새 실행 27 passed(0.62초), failure/error/skip 0. LOCAL FULL 생략 / 사용자 10절·관련 시험 대체 / 기준선 갱신 없음. commit/push 없음.

**Small-world reachable domain 감사 V1(2026-10-01, 기준 `a1685e5`): C / SMALL_WORLD_ENVELOPE_UNDEFINED.**
[감사 보고서](docs/active/C1B1_SMALL_WORLD_REACHABLE_DOMAIN_V1.md).
일반 주기/저장소 경계 방향과 두 Ar40 산란 계약은 있지만 목표 작은 세계의 N·공간 치수·초기 위치/운동량 집합·전체 에너지/구동·운영 시간이 미정이다.
사양 없이 reachable envelope를 만들지 않았다. O-1 E=0.5 De/rho=-0.001 입력은 기존 직접 준비된 observed 두 원자 사례이며 목표 세계 판정은 **UNDECIDABLE_FROM_CURRENT_WORLD_SPEC**다.
D_valid는 초기 상태 수치 evidence이며 궤적 중간 상태의 불변 영역이 아니다. R1/R2/R3와 지원 gap 크기는 미판정, 새 bound/probe/sweep/Vast 0.
production/dt/profile/PES/r_min/D_valid/verifier/Energy Bound/기존 O-1 STOP/④-Liveness/④-Safety/A-EV/Yoshida 상태 유지. 검증은 보고서 9절을 따른다. commit/push 없음.

**초기 `_decide` 예외 분류 후보 STOP — 당시 기록(기준 `53b73ea`):**
[호출·예외 흐름 및 분류 계약](docs/active/C1B1_DECIDE_EXCEPTION_CLASSIFICATION_V1.md)을 고정하고
분류/guard 수정 후보와 직접 시험 21개를 만들었다. 관련 경계 시험 44개 통과,
보존된 7개 입력의 79,087 step raw/J는 비트 동일했다. 그러나 LOCAL FULL은
**3253 passed / 58 failed / 143 errors / 1 strict xfailed / 실제 skip 0, 687.63초**로 실패했다.
실패/error 201개는 기존 endpoint 증명 소스 결합 guard 및 진단·그룹 기록의 provenance 불일치다.
비트 비교만으로 증명 결합을 갱신하지 않고 재감사·재결합 범위의 설계자 결정 전 STOP했다.
당시 후보는 미완료·미commit이었다. 이후 분류 변경은 `bdc9bfe7`에 보존됐고,
설계자가 변경 유지·제한된 재감사를 승인해 위 결과로 STOP을 해소했다.
초기 실패 로그는 보존하며 공식 통과 실행으로 세지 않는다.

## C1-B1: 완료된 부분과 남은 의무

현재 후보는 두 Ar40, 위치 FX(96,48), 운동량 FX(96,80), Δt = 40 a.u., drift v2(위치에 더하기 전에 변위를 반올림)다.
이 후보를 A 세계의 최종 수 체계나 C1-B1 전체 동결로 해석하지 않는다. binary64 절대 위치는 탈락 기록으로 strict xfail 1개를 유지한다.

| 항목 | 현재 상태 | 정확한 범위 |
|---|---|---|
| **D_valid v2** | **FROZEN** | canonical 생성기·기준 fixture·초기 상태 식별 계약. 궤적 전체 인증 아님 |
| **④-1** | **원인별 1-step formal bound 구현 완료** | 위치·초기 운동량·impulse·이산화 항을 분리. 유한 shell·half-step 운동량 cap 아래의 1-step 및 유한합 |
| **④-2** | **outgoing shell induction + 유한 체류 상한 구현** | 실제 ΔR²≥g_min>0 귀납, shell 유지·출구 packet 연결·overflow 검사. 모든 상태의 탈출을 보장하지 않음 |
| **④-3** | **R_J + zero discrete impulse + analytic continuous tail 구현** | 실행기 impulse=0과 동일 실제 입구의 연속 tail 잔여 impulse를 구분. L 상한은 유한 입구→R_J만 |
| **④-4** | **rounding-decision completeness 진행 중** | tail 결정성은 닫음. 일반 pre-tail reachable enclosure의 비영 impulse cover는 미완료 |
| **④ 전체** | **아직 FROZEN 아님** | ④-2/④-3은 rounding-decision completeness에 조건부 |
| **⑤** | **공식 실행 미착수** | 자료 확보·봉인 준비는 가능. 공식 O-3는 production replay verifier 승인 뒤 CONFIRMED trajectory만 사용 |

**④ 사전 증명 연구가 열려 있는 이유(Gate 재분류 전 기록):** 미래의 모든 필요한 impulse 반올림이 기존 평가기의 **MAX_PRECISION_BITS=16384** 안에서 항상 결정되는지 아직 미증명이다.
유한 체류 step 수만으로 반올림 경계와의 분리가 보장되지는 않는다. 충분한 증거가 없으면 `NotCertified`이며 실행 중 `ReferenceUndecided` 가능성도 남는다.

현재 닫힌 부분은 **R_J=10240 bohr 이후 모든 legal FX 상대 위치의 tail impulse 결정성**(210 radial cell, 최대 512 bit)이다.
FX 범위를 넘어 프로그램이 무한히 실행된다는 뜻은 아니다. 일반적인 유한 outgoing 입구→R_J 구간은 기존 shell induction의 **reachable enclosure 전체**를 덮어야 한다.
R=20 예시는 64-cell 예산에서 미인증이고, 2-step prefix도 `incomplete_budget`이다. 단일 궤적 인증으로 전체 enclosure 인증을 대신하지 않는다.

**④-4b 진행(2026-09-27):** evaluator 수정 전·후 frozen 181개 probe replay는 exit 0, 181/181 초기 비트·D_valid 판정·KDK 전이 일치
(총 3,470,163 전이, 3815.645초), fixture 변경 없음. 기존 audit_fail 6개는 독립 감사 재실행 없이 보존했다.
실제 KDK에서 보존되는 상대 좌표 0과 누적 kick/유한 L bound를 유도한
[coordinate tube·direction projection](docs/active/C1B1_REACHABLE_GEOMETRY_V1.md)을 구현했으며 신규 시험 9개 통과.
Cell budget은 64 유지. 재생성한 R=20 예시는 상대 좌표 3D→1D로 줄었지만 64 cell 검사 뒤 미해결 record 76개가 남아 `NotCertified`다.
관련 시험 **106 passed, 51.59초**. VAST **REMOTE PYTHON FULL: 2292 passed + 121 skipped + 1 strict xfailed, 실패 0, 98.89초, exit 0**.
skip은 Windows/native 98개, CUDA 10개, 외부 원문 자료 13개이며 통과로 세지 않는다. 이번 LOCAL FULL은 설계자의 원격 이전 지시로 중단했으므로 새 LOCAL FULL 결과가 아니다.
로그 회수와 VAST 정지 확인 완료. **④-4b 전체 미완료**이며 다음 의무는 enclosure를 추가로 좁히는 수학적 제약이다.

**④-4b 미해결 원인 진단(2026-09-27, 기준 `4088061`):** 기존 64-cell 결과의 76개 기록은
첫 shell 대기 cell 49개 + 미검사 shell 27개다. [진단](docs/active/C1B1_ROUNDING_DIAGNOSIS_V1.md)에서
74개는 두 끝 격자점의 실제 raw impulse가 다르고, 1개 singleton은 개별 판정 성공,
1개는 끝점은 0이지만 parent enclosure 미분리임을 기록했다.
현재 첫 shell projection에 서로 다른 output을 갖는 격자점 65개가 있어 **최소 65 uniform leaf가 필요하다**.
따라서 현재 projection을 유지한 동일-output cover는 64-cell 안에서 완료할 수 없다.
이것은 실제 궤적의 ReferenceUndecided 반례나 16384-bit 불가능성 증명이 아니다.
64-cell/16384-bit 한도·물리·D_valid는 유지한다. 다음 의무는 더 강한 이산 도달가능 제약 또는
서로 다른 output을 허용하는 전체 격자점의 rounding separation 증명이며 아직 미완료다.
추가 조건부 유도에서 첫 64회 정상 전이의 65개 kick 입력도 서로 다른 output을 가져야 함을 확인했다.
따라서 도달가능 제약만으로 64개의 동일-output cell을 만드는 것은 이 초기 상태의 해결책이 아니다.
**서로 다른 output을 허용하는 pointwise 판정 증명 표현이 우선**, 추가 불변량은 그 대상 축소의 보조 수단이다.

**④-4b multi-output 증명 계약 구현(2026-09-27):** 기존 constant-output 인증기를 보존한 채
[서로 다른 output의 결정성 인증](docs/active/C1B1_MULTI_OUTPUT_DECISION_V1.md)을 추가했다.
명시한 65개 서로 다른 impulse 입력을 **한 region·공통 256-bit**로 인증했다.
이것은 65점 전수 평가이며 큰 격자 구간이나 실제 궤적 전체의 인증은 아니다.
29개 그룹 전부 V′>0·V″<0, impulse 엄격 증가와 인접 separation 하한을 해석적으로 증명했다.
마지막 특이 구간은 내부 극값·zero crossing 없이 **전체 선언 격자점 553,997,943,205,884,291개**를
분할 없이 256-bit impulse=0으로 인증했다. singleton도 128-bit로 인증했다.
나머지 **27개 그룹은 격자 rounding-boundary margin 미증명**이다. 공통 수치 endpoint error bound는 확보했다.
새 coverage checker는 fresh shell projection의 정확한 gap 92개를 남긴다(원래 미해결 기록 76개와 다른 집계).
사용 region 3/64, precision cap 16384 유지. **R=20 및 ④-4b 전체 NotCertified**다.
물리 실행기·기존 인증기·도달 projection·181 Frozen D_valid는 변경하지 않았다.
⑤·E_min·전체 산란각은 계속 보류하며 다음 의무는 27개 큰 격자 domain 전체의 half-ulp 경계 분리 증명이다.
신규 직렬 시험 **41 passed, 22.82초**. **LOCAL FULL: 2471 passed + 1 strict xfailed, skip 0,
실패/error 0, 359.84초, exit 0**. 신규 41개 시험의 직렬/병렬 결과가 항목별로 동일하다.
컴파일러 출력 cp949 해독 경고 26건은 남아 있으며 해결됐다고 해석하지 않는다.
실행기·기존 인증기·도달 geometry·동결 fixture 등을 포함한 16개 파일이 `6184700`과 LF 바이트 동일하다.
증거: `runs/c1b1_multi_output_20260927/{local_full.log,local_full.xml,verification_summary.json,unchanged_contracts.json}`.

**④-4b boundary 역상 배제(2026-09-27, 기준 `d59b565`):**
[half-ulp boundary 증명](docs/active/C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md)에서 기존 미인증 domain 27개의
정확한 endpoint enclosure·ulp span·경계 개수를 기록했다. shell 24〜26은
**51개 경계 → 후보 정수 3개 → 직접 인증 3개**로 각 domain 전체를 256-bit 안에서 닫았다.
선언된 격자점 수는 각각 298,023,842,104,416,266 / 372,529,648,073,654,547 /
465,661,905,535,202,398개이며 실제 방문 점 수는 아니다.
나머지 **24개 큰 domain**은 경계 작업 한도 64를 넘어 symbolic-family 대상으로 남겼다.
경계 수는 249〜6,304,880,043,134,911,522개이며 후보 수는 미열거로 기록했다.
64-region과 16384-bit 유지. 별도 경계/후보 작업 한도는 물리 cap이 아니다.
새 compositor가 검증된 기존/신규 6개 region을 fresh geometry와 대조한 결과 gap은 92→89다.
**R=20 및 ④-4b 전체 NotCertified**, ④ 동결·⑤·E_min·전체 산란각 보류 유지.
기존 물리·D_valid·multi-output/constant-output 증명 및 fixture는 변경하지 않았다.
신규 직렬 **31 passed, 26.86초**. 최종 **LOCAL FULL: 2502 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 405.59초**, 컴파일러 cp949 해독 경고 27건.
신규 31개 결과는 직렬/병렬 항목별 동일하며, 관련 기존 소스/fixture 19개가 `d59b565`와 LF 바이트 동일하다.
증거: `runs/c1b1_boundary_exclusion_20260927/{local_full_final.log,local_full_final.xml,verification_summary.json,unchanged_contracts.json}`.
최대 precision 필드 보강 전의 LOCAL FULL(2501 passed, 403.78초)은 별도 이전 실행 로그로 보존한다.

**④-4b fractional phase 구조 조사(2026-09-27, 기준 `f275d0b`):**
[24개 식 조사](docs/active/C1B1_FRACTIONAL_PHASE_SURVEY_V1.md)는 원래 domain을 그대로 유지하고
ULP 단위 exact impulse를 정수 유리식 P(n)/Q(n)+지수 잔여항으로 분리했다.
P는 22차, Q는 29차이며 정확히 **Q=5^8·n^17·D_int(n)^2**다. 고정/2의 거듭제곱 분모가 아니고 점별 약분은 별도다.
4096-bit 수학 enclosure의 signed residual과 기존 numeric endpoint error를 합친 결과,
**shell 19〜23의 5개 domain**에서 guard<1/(2Q_max)가 성립했다(실행 precision 2048/2048/2048/4096/4096).
23개 domain의 유리식 exact tie는 bounded 합동류와 square valuation parity로 배제했고,
마지막 하나는 미해결 합동류를 정확히 **n=1071856711314178048 한 점**으로 줄였다.
그 점의 정확 유리식도 tie가 아니며 기존 finite-point 인증기에서 256-bit 이하로 결정된다.
따라서 유한 fallback 포함 rational tie 배제는 24/24다. 전체 impulse의 경계 분리로 연결 가능한 것은 충분조건을 만족한 5개뿐이다.
나머지 19개는 현재 residual 상한이 최소 간격보다 크며, 홀수 n에 대한 2-adic 정보만으로 간격을 더 키울 수 없다.
더 강한 signed modular family bound는 미증명이다. 현재 enclosure의 부호 미결정을 실제 부호 변화나 precision 실패로 해석하지 않는다.
이번 결과는 **survey_only**, family certificate 계약·독립 checker·coverage 연결은 아직 없다.
새 region 0개, 기존 **6/64 region·gap 89**, **R=20/④-4b NotCertified** 유지.
물리·기존 인증기/fixture·181 Frozen D_valid를 보존하며 ④ 동결·⑤·E_min·전체 산란각은 계속 보류한다.
다음은 충분조건 5개를 독립 checker로 연결하고 남은 19개의 실제 위상 거리 하한을 조사하는 것이다.
신규 직렬 **37 passed, 12.21초**. 최종 **LOCAL FULL: 2539 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 426.25초**, 컴파일러 cp949 해독 경고 27건.
신규 37개 결과는 직렬/병렬 항목별 동일하며, 관련 기존 소스/fixture/시험 23개가 `f275d0b`와 LF 바이트 동일하다.
181 probe의 긴 replay를 새로 실행한 결과는 아니다. 소스/fixture 보존과 이번 전체 회귀 검증을 구분한다.
증거: `runs/c1b1_fractional_phase_20260927/{local_full_final.log,local_full_final.xml,verification_summary.json,unchanged_contracts.json}`.
중간 집중 시험의 JSON 키 비교/API 호출 오류 및 최종 진단 필드 추가로 중단한 첫 전체 실행 로그는 별도로 보존하며 최종 결과로 세지 않는다.

**④-4b rational spacing family 인증(2026-09-28, 기준 `f0484af`):**
[별도 family checker](docs/active/C1B1_RATIONAL_SPACING_FAMILY_V1.md)는 survey/생성기를 import하거나 pass flag를 사용하지 않는다.
동결 component를 직접 미분해 exact P/Q·지수항 계수를 재구성하고, 닫힌 domain 전체 Q_max·signed residual·numeric E·strict guard를 재계산한다.
완전한 valuation/residue tree와 유한 exception을 검사하며 요구 precision과 실제 execution cap을 대조한다.
**shell 19〜23의 원래 5개 domain 전체 Certified**, p 상한 2048/2048/2048/4096/4096.
마지막 exception n=1071856711314178048은 정확 rational tie 배제 및 실제 point proof 256-bit 재검증.
momentum legal output도 exact triangle bound로 확인한다. 64-region·16384-bit, 원래 domain과 물리는 유지한다.
기존 6개와 새 5개를 각 checker로 확인한 fresh coverage는 **11/64 region·gap 84개**다.
남은 큰 family 19개에는 새 수학을 추가하지 않았으며 **R=20/④-4b 전체 NotCertified**를 유지한다.
④ 동결·⑤·E_min·전체 산란각은 계속 보류. 다음은 별도의 ④-4c modular-distance lower-bound survey다.
source-bound numeric error lemma·정수 EXP·동결 상수·기존 point API는 공통 기반으로 재사용하므로 전역 독립 물리 감사와 구별한다.
신규 직렬 시험 **54 passed, 32.93초**. 최종 **LOCAL FULL: 2593 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 385.03초**, cp949 출력 해독 경고 25건은 남았다.
신규 54개 결과는 직렬/병렬 항목별 동일하며, 기존 관련 소스/fixture/시험 26개가 `f0484af`와 LF 바이트 동일하다.
181 probe의 장시간 replay를 새로 실행한 결과가 아니라 보존 해시와 이번 전체 회귀 검증이다.
증거: `runs/c1b1_family_checker_20260928/{local_full_complete.log,local_full_complete.xml,verification_summary.json,unchanged_contracts.json,exception_structure.json}`.
초기 검사에서 잡힌 integer / float division 오류와 이전 전체 실행(2590 passed, 427.65초)은 로그로 보존하며 최종 버전 검증과 구별한다.

**④-4c-1 exact modular-distance 조사(2026-09-28, 기준 `561a91e`):**
[19-domain 별도 survey](docs/active/C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md)는 원래 shell 0〜18의 domain을 유지하고
미리 정한 bounded selection의 **2,679점**에서 정수 Δ=|2P−(2k+1)Q|·약분·정확 경계 거리·분모 인수별 residue·gcd·generalized CRT를 기록했다.
관측 최소값은 선택한 점에만 해당하며 새 family 하한은 없다. **survey_only·새 region 0·11/64 region·gap 84·전체 NotCertified** 유지.
19개는 **4+1+14**로 갈린다. shell 0〜3은 residual guard≥½ ULP여서 unshifted rational 거리만으로 기존 조건을 닫을 수 없고,
shell 4는 guard<½지만 공통 M/(2Q_max) 방식에 필요한 M이 Q_min을 넘어 현재 구조가 너무 강하다.
shell 5〜18의 모든 선택 점은 guard보다 멀었지만 전체 격자 분리 증명은 없다.
특히 shell 15〜18의 선택 점 **570개** 모두에서 point CRT 하한이 M_req 이상이므로 다음 lemma 조사 후보다. 인증 승격하지 않는다.
D_int(0)=2^318·5^32와 gcd(n,D(n))|D_int(0)을 확인했다. D/D² remainder는 정수화 multiplier를 포함하며 역원을 가정하지 않는다.
모든 domain이 작은 modulus의 모든 residue를 포함하며, mod 5^8 단독 거리 하한은 실제 5의 배수 witness에서 0이다.
약분 전 큰 Δ나 16-bit zero를 강한 separation/tie로 해석하지 않는다. 이전 checker·물리·Frozen D_valid를 변경하지 않았고
기존 관련 소스/fixture/시험 30개가 `561a91e`와 LF 바이트 동일하다. 181 probe 장시간 replay 재실행은 아니다.
신규 직렬 **32 passed, 25.73초**. **LOCAL FULL: 2625 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 383.44초**, cp949 출력 해독 경고 25건 유지. 신규 32개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_modular_distance_20260928/{focused_final.log,focused_final.xml,local_full.log,local_full.xml,raw_samples_final.jsonl,unchanged_contracts.json,verification_summary.json,concept_alignment.json}`.
다음은 15〜18 우선의 **전 domain** 합동류 하한 조사이며 새 lemma가 확보되기 전에는 checker·coverage를 변경하지 않는다.
④ 동결·⑤·E_min·전체 산란각 보류 유지.

**④-4c-2 full residue-class 조사(2026-09-28, 기준 `23144df`):**
[shell 15〜18 전수 class survey](docs/active/C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md)는
n=2^a·5^b·u, gcd(u,10)=1의 모든 valuation/unit class와 필요한 normalized zero residue refinement를 포함한다.
원래 격자점 **230,627,472,909,852,564개**의 덮개를 **14,271개 분석 class**로 구성했다.
합계·닫힌 endpoint·class의 서로 겹치지 않음을 검사했다. 추가 point 표본은 없으며 singleton class 1,005개는 전체 허용 입력을 정확 계산했다.
**5,541개 class**에서 필요한 Δ 하한을 확인했지만 **8,730개 class의 가변 CRT gap은 미해결**이다.
shell별 미해결 class는 3272/2802/2065/591이고 새 shell 전체 lemma 후보 0, 실제 작은 Δ 입력 반례 0이다.
보장되는 2/5 공통 인수를 제거한 integer polynomial identity를 확인했고, 추가 odd gcd를 없어졌다고 가정하지 않았다.
Q′=F·v, gcd(v,10)=1인 경우 높은 모든 2/5 prime-power 제약은 Δ′≡2P′−F mod2F로 합쳐진다.
**미해결 5,370개 class**에서는 2gF<M_req이므로 odd quotient 범위를 제한하지 않는 이 고정 정보만으로 작은 Δ를 전부 배제할 수 없음을 확인했다.
예를 들어 n≡3 mod10 class는 고정 2/5 정보와 양립하는 비영 gap≤781250을 가진다. 실제 full Δ 반례라는 뜻은 아니다.
현재 남은 의무는 u^17·D_normalized²의 **가변 divisor와 odd quotient 범위**를 유지한 parametric gap lemma다.
고정 class가 full CRT residue를 하나로 정한다는 가정은 같은 class의 서로 다른 Q로 반박됐다.
**survey_only·새 region 0·11/64 region·gap 84·전체 NotCertified** 유지. shell 0〜14·기존 checker·물리·Frozen D_valid를 변경하지 않았다.
기존 관련 소스/fixture/시험 33개가 `23144df`와 LF 바이트 동일하다. 181 probe의 긴 replay 재실행은 아니다.
신규 직렬 **27 passed, 22.48초**. **LOCAL FULL: 2652 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 425.76초**, cp949 출력 해독 경고 25건 유지. 신규 27개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_residue_class_20260928/{focused_with_fixed_power.log,focused_with_fixed_power.xml,local_full.log,local_full.xml,unchanged_contracts.json,verification_summary.json,concept_alignment.json}`.
오류 문구 정규식에서 괄호를 escape하지 않아 실패한 중간 시험 로그는 보존한다. 알고리즘의 변조 거부 자체는 정상 작동했다.
shell 전체 하한이 확보되지 않았으므로 새 independent lemma checker/coverage 승격은 보류하고 ④ 동결·⑤·E_min·전체 산란각 보류도 유지한다.

**④-4c-3 normalized quotient-gap 조사(2026-09-28, 기준 `875aa31`):**
[정규화 gap·quotient 조사](docs/active/C1B1_NORMALIZED_QUOTIENT_GAP_SURVEY_V1.md)는 기존 shell 15〜18의 14,271 class 전체를 유지한다.
class 공통 인수 g에 맞춰 필요한 기준을 **ceil(M/g)**로 바꾸고,
기존 D² remainder 항등식을 선형 변수 치환과 scalar 정리 후 계수별로 재검사했다.
`Q′=B·D_normalized²`, `c·z=(A−c·h·B)D_normalized²+R`에서 홀수 h·multiplier·cofactor를 함께 보존한다.
R 부호만으로 gap을 판정하거나 c의 modular 역원을 가정하지 않는다. non-singleton P′/Q′ 차수는 22/29다.
exact Bernstein ratio 범위와 quotient coefficient coset을 조사했지만 **큰 class의 새 하한은 0개**다.
입력 8개 이하의 미해결 작은 class **654개·2,680 입력**을 전수 계산하고 별도 정수 평가로 확인해 class 하한을 추가했다.
기존 하한 5,541개와 합쳐 **6,195 class 하한**, **8,076 class 미해결**이며 shell별 미해결은 3014/2587/1894/581이다.
전체 shell lemma 후보 0·실제 작은 gap 반례 0이며, 큰 class의 느슨한 조건에 후보가 남는 것을 존재 증거로 바꾸지 않는다.
실제 유리식 gap 반례라도 전체 impulse 반올림 실패/16384-bit 초과 증거와는 별개다.
**survey_only·새 region 0·11/64 region·gap 84·④-4b NotCertified** 유지. 새 independent checker/coverage 연결은 없다.
기존 물리·D_valid·인증 관련 36개 파일은 `875aa31`과 LF 바이트 동일하며 181 probe replay 재실행은 아니다.
신규 집중 직렬 **34 passed, 1.38초**. **LOCAL FULL: 2686 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 433.59초**, cp949 경고 25건 유지. 신규 34개 직렬/병렬 결과는 항목별로 동일하다.
원자료 14,271행 해시·정규화 기준·작은 class 독립 전수·보존 해시·구상 경계는
`runs/c1b1_quotient_gap_20260928/{raw_verification.json,unchanged_contracts.json,concept_alignment.json,verification_summary.json}`에 기록한다.
다음은 가변 B(j)와 quotient의 같은-j 상관관계를 더 보존하거나 다른 분모 인수와 remainder를 함께 쓰는 lemma다.
④ 동결·⑤·E_min·전체 산란각 보류 유지.

**④-4c-4 same-input 필터 최소 구현(2026-09-28, 기준 `0bdfa49`):**
[같은 입력 필터·별도 checker 조사](docs/active/C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md)는
기존 미해결 8,076 class 전부의 정규화 항등식·홀수 h inventory를 검사한다.
`F_h=(A−c·h·B)V+R=c(2P′−hQ′)`를 같은 j에서 결합한 뒤 범위를 계산하며 m=ceil(M/g)를 유지한다.
입력 16개 이하 241 class와 사전 선정 대표 12개에만 깊이 4·노드 31의 추가 분할을 적용했다.
**추가 하한은 작은 241 class·2,980 입력이며 전부 singleton leaf까지 나눈 결과다.**
실제 큰 class symbolic 하한 0·실제 joint-polynomial-sign leaf 0, 합성 이차 사례의 개선과 구별한다.
class 하한 집계 **6,436**, 남은 **7,835 미해결**, 전체 shell lemma·실제 small-gap witness·새 region 0이다.
최소 proof object와 별도 checker는 원래 class/항등식/기준/정수 분할/홀수 inventory를 재구성한다.
builder를 import하지 않지만 frozen 물리 항등식과 기존 numeric foundation은 공유하며 새 독립 물리 감사는 아니다.
기존 6,195 survey 하한을 이번 checker로 일괄 승격하지 않았고 coverage 연결도 추가하지 않았다.
**④-4b NotCertified·11/64 region·gap 84·16384-bit·④ 미동결·⑤ 미착수** 유지.
기존 물리·D_valid·인증·직전 survey 관련 **39파일**은 `0bdfa49`와 LF 바이트 동일하다.
새 집중 직렬 **38 passed, 9.06초**. **LOCAL FULL: 2724 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 453.76초**, cp949 출력 해독 경고 25건 유지. 신규 38개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_same_input_20260928/{raw_classes_final.jsonl,proofs_final.jsonl,raw_verification.json,unchanged_contracts.json,concept_alignment.json,verification_summary.json}`.
범용 증명 언어·창고·자동화·B 연결은 미구현이다. 다음은 실제 29차 식의 같은-j 조건을 열거 없이 유지할 lemma다.

**④-4c-5 shell 18 hard-case 탐색 실현 가능성 조사(2026-09-28, 기준 `0bab51b`):**
설계자 판정으로 h 합동 lemma 방향은 **보류(폐기 아님)**하고 (b) Lefèvre/SLZ 계열의 가장 싼 단계부터 실측했다.
[조사 결과](docs/active/C1B1_HARD_CASE_SEARCH_SURVEY_V1.md)는 ψ=P/Q−½의 원래 shell 18 domain 전체에서
블록별 보간다항식 + 엄밀한 보간 오차 δ(도함수 분자 N_k의 Bernstein 비율 상한)를 쓰고, search threshold를 **T=G+δ**(G는 ④-4c-1의 고정 guard, 약 2^-1614)로 유도했다.
affine은 거짓 후보를 수천 개 이하로 두려면 블록 약 47억 개가 필요해 부적합했고, **quadratic L=2^34(블록 4,547,510)**로 shell 전체를 실행했다.
교차 수 **1,568,498**은 half-ulp fixture의 경계 수와 정확히 같고, 후보 **109개**를 원래 P/Q로 전부 재평가한 결과 **hazard 0·거짓 후보 109**다.
별도 checker(생성기 import 금지)가 superblock **1024/1024**를 독립 재계산해 일치했다. 6 워커로 생성기 562초·checker 582초.
합성 12설정과 실제 shell 18 창 24설정의 brute force 대조는 모두 **누락 0**(창은 대조를 위해 τ를 명시적으로 키움)이며, 결함 주입 4종과 proof row 조작을 잡았다.
cubic은 오차만 계산했고 lattice/SLZ는 구현하지 않았다. 교차별 처리 비용은 경계 수에 선형이라 경계가 격자점보다 많은 shell 0〜4에는 원리적으로 쓸 수 없고,
고정 guard로 2GN을 계산하면 shell 0〜6은 guard 안 입력이 휴리스틱으로 매우 많아 전체 impulse를 대상으로 한 별도 설계가 필요하다(추정, 미측정).
**survey_only**: 인증 계약·coverage 연결 없음, **④-4b NotCertified·11/64 region·gap 84·16384-bit·새 region 0** 유지, shell 0〜17로 일반화하지 않는다.
checker는 동결 P/Q 항등식과 기존 guard를 공유하므로 새 독립 물리 감사가 아니다. 기존 파일 수정 0(신규 5파일).
신규 집중 직렬 **40 passed, 13.86초**. **LOCAL FULL: 2764 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 455.87초**. 신규 40개 직렬/병렬 결과가 항목별로 같다.
이번 실행 요약에는 컴파일러 인코딩 경고 줄이 없었으나 원인을 조사하지 않았으므로 해결로 보고하지 않는다.
증거: `runs/c1b1_hard_case_20260928/{survey_full.json,survey_full.log,focused_final.log,focused_final.xml,local_full.log,local_full.xml,local_full.exit,verification_summary.json,attempt_notes.json}`.
다음 판단: shell 18 결과의 인증 계약 승격 여부, shell 17→15 실측 확대 여부, shell 0〜6 별도 설계 여부.

**④-4c-6 shell 18 hard-case 인증서(2026-09-28, 기준 `7ab8de3`):**
설계자 판정(1)에 따라 ④-4c-5 결과를 [인증 계약·proof object](docs/active/C1B1_HARD_CASE_CERTIFICATE_V1.md)로 올렸다.
family checker와 같은 잠금을 건다: 외부 domain binding, frozen P/Q, residual/numeric error 출처와 G 재계산, precision 4096 ≤ execution limit ≤ 16384, legal momentum 출력, source 해시.
verify는 superblock 1024행의 도함수 상한·교차 수·후보 구간을 전부 다시 계산해 정확히 대조하고, 후보 **109개**를 원래 P/Q로 재평가한다(**hazard 0**).
**shell 18 원래 domain 전체(격자점 78,125,618,227,463,141개) Certified.** 통과 뒤 계산한 **fresh coverage는 12/64 region·gap 83**이며 shell 18 gap은 0이다.
남은 gap은 shell 0에 65개, shell 1에 2개, shell 2〜17에 각 1개다. **R=20/④-4b 전체 NotCertified**, ④ 미동결·⑤ 미착수다.
인증서 1024행은 ④-4c-5 생성기 행과 전부 일치한다. 저장 JSON을 그대로 읽은 전체 재검증도 통과했다(560.7초). 독립 물리 감사는 아니다(동결 P/Q·numeric lemma·정수 EXP 공유).
첫 전체 실행은 superblock을 quadratic 블록 하나로 통째 처리한 결함으로 1시간 46분 멈췄다. build/verify가 같은 함수를 공유해 시험이 못 잡은 유형 A다.
수정 뒤 교차 구현 대조·회귀·작업 한도 시험을 추가했다. 설명문 수정 뒤 전체를 재생성했으며 인증서·coverage가 이전 실행과 동일하다.
최종 실행 build 551초·verify 547초·coverage 합성 567초(6 워커). 신규 직렬 **34 passed**(관련 74개 65.95초).
**LOCAL FULL: 2798 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 448.71초**, 신규 74개 직렬/병렬 항목별 동일, 로그에 경고 줄 없음(원인 미조사).
증거: `runs/c1b1_hard_case_certificate_20260928/{certificate_full.json,certificate_full.log,verify_wire.log,focused_serial.xml,local_full.log,local_full.xml,attempt_notes.json}`.
다음은 ④-4c-7 shell 17 단독 확장성 실측이다(16/15 함께 하지 않음). shell 0〜6은 전체 impulse I(n)=P/Q+S의 별도 설계 트랙으로 기록만 한다.

**④-4c-7 shell 17 hard-case 확장성 실측(2026-09-28, 기준 `1d75da3`):**
설계자 지시대로 shell 17 **하나만** 같은 생성기·checker·정책으로 쟀다([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md)).
블록 3,638,015개, 교차 **8,645,949**(half-ulp fixture 경계 수와 같음), 후보 **827**(휴리스틱 예상 2,148), exact recheck **hazard 0**, 독립 checker 1024/1024.
brute force 대조(합성 12, 실제 창 24)는 누락 0이다. 병렬 효율은 생성기 0.986, checker 0.991이다.
교차가 5.5배로 늘었지만 생성기 CPU는 오히려 줄었고(2,989초), checker CPU는 35% 늘었다(4,654초).
두 실행으로 푼 추정 교차당 비용은 생성기 약 45 µs, checker 약 256 µs다. 실행마다 흔들리며 측정이 아니다.
**survey_only**: 인증·coverage 변경 없음, **12/64·gap 83** 유지, shell 16/15로 확장하지 않았다.
이 과정의 결함 세 가지(옛 coverage 숫자 고정, 줄바꿈 의존 해시, 전제가 틀린 시험 단언)는 수정 뒤 재실행했고 기록으로 보존한다. 세 실행의 결정적 결과는 모두 같다.

**native 리눅스 빌드와 원격 노드(2026-09-28, `90efde0`):** native harness가 Windows(MSVC, 명령 그대로)와 리눅스(g++/nvcc)를 모두 빌드한다.
원격 Vast 노드(RTX 3090, CPU 32)에서 native·GPU 시험 104개가 Windows와 항목별로 같은 결과로 통과했다.
원문 참조 파일도 복사했다. 그래서 **원격 전체 시험이 skip 0으로 2807개를 실행**한다(`894cf5e`에서 1건 실패 → 줄바꿈 해시 수정 `91a5c38`).
원격은 LOCAL FULL을 대신하지 않는다. Windows 경로(MSVC)는 로컬에서만 확인된다.
**LOCAL FULL(`91a5c38`): 2807 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 405.49초.**
증거: `runs/native_linux_port_20260928/{windows_native.*,linux_native.*,local_full.*}`, `runs/c1b1_hard_case_shell17_20260928/{survey_full.json,local_full.*,first_run/,second_run/}`.
다음 판단(설계자): shell 17 인증 승격 여부, shell 16/15 확장 여부. shell 0〜6 전체 impulse 트랙은 기록만 한다.

**④-4c-8 shell 17 hard-case 인증서(2026-09-28, 기준 `ce5f28f`):**
설계자 판정대로 shell 17을 ④-4c-6과 **같은 계약**으로 올렸다([계약·결과](docs/active/C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md)). 인증 모듈은 수정하지 않았고, shell 17 driver만 추가했다.
단계: build → verify → 저장 JSON 재로드 후 전체 검증 → fresh coverage(shell 18·17 재검증 포함).
후보 **827개**를 전부 정확 재평가했다(**hazard 0**). **shell 17 원래 domain 전체(격자점 62,500,618,227,463,141개) Certified.**
**fresh coverage 13/64 region·gap 82**이며 shell 17·18 gap은 0이다. **R=20/④-4b 전체 NotCertified**다.
인증서 1024행은 ④-4c-7 생성기 행과 전부 일치한다.
원격 32스레드(Ryzen 9 5950X, 물리 16코어) 실측: build·verify·저장본 verify 각 약 203초 wall/약 6,380 CPU초(효율 0.98), coverage 361초. 전체 16분 15초.
이 값으로 다시 푼 shell 16 검증 1회는 약 2.0×10⁴ CPU초(32스레드 단계당 약 11분)이고, shell 15는 약 9.7×10⁴ CPU초다. 추정이며 측정이 아니다.
**LOCAL FULL(`8d45209`): 2815 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 408.27초.**
**REMOTE LINUX FULL(같은 커밋): 2815 passed + 1 strict xfailed, skip 0, 356.36초.** 시험 2816개가 항목별로 같다.
리눅스는 작업자를 fork로 띄워 DeprecationWarning이 6건 나왔다. 그래서 spawn 전달 검증은 Windows에서만 실제로 일어난다.
증거: `runs/c1b1_hard_case_certificate_shell17_20260928/{certificate_full.json,certificate_full.log,local_full.*,remote_linux_full.*}`.
다음 판단(설계자): shell 16 survey_only 진입 여부. shell 15는 그 뒤에 따로 판단한다.

**④-4c-9 shell 16 survey_only(2026-09-28, 기준 `018bb65`):**
설계자 판정: shell 16은 인증에 앞서 survey_only 전수 조사만 한다. coverage·인증 상태는 바꾸지 않는다([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md)).
원격 32스레드 실행 결과는 다음과 같다.
- 교차 **46,892,493**(fixture 경계 수와 같음), 후보 **6,581**, **hazard 0**(독립 재평가 동일), checker **1024/1024**, brute force 누락 0.
- 생성기 213초/6,719 CPU초, checker 628초/19,751 CPU초, 효율 0.98, 작업자 메모리 약 30 MB.
- 같은 기계에서 다시 돈 shell 17 기준선의 행이 기존 fixture와 같다.
- shell 17 대비 교차 5.42배, 후보 7.96배, **후보 밀도 1.47배**, checker CPU 3.10배.
- 후보는 휴리스틱 2N(G+δ)를 일정 비율(0.43→0.39→0.37)로 따르며, 밀도 증가는 δ 증가로 설명된다(구현자 해석). 판정 기준의 "밀도 변화" 항목이므로 설계자 판단 사항이다.
- 예측했던 shell 16 checker 약 2.0×10⁴ CPU초와 실측 차이는 약 1%다. shell 15 조사 재추정은 원격 약 1시간 5분이다.
- 검증: 설계자 판정대로 LOCAL FULL은 생략했다. 관련 시험 101개와 변경 범위(새 파일만, 해시 고정 소스 4개 불변)를 확인했다. 새 시험 10개는 아직 기준선 2815에 포함되지 않았다.
증거: `runs/c1b1_hard_case_shell16_20260928/{survey_full.json,survey_full.log}`.
다음 판단(설계자): 밀도 변화 해석 수용 여부 → shell 16 인증 여부 → shell 15 조사 진입 여부.

**④-4c-10 shell 16 hard-case 인증서(2026-09-28, 기준 `a4eb67b`):**
설계자 판정: shell 16 survey의 후보 밀도 증가(1.47배)는 δ 증가로 설명 가능한 **진행 판단용 관측**으로만 받아들이고, 증명으로 승격하지 않는다. 인증 여부는 hazard 0·checker 일치·brute-force 누락 0·구조 불일치 없음·효율 유지·메모리 문제 없음·비용 예측 오차 약 1%로 판단해 shell 16 인증을 승인했다([계약·결과](docs/active/C1B1_HARD_CASE_CERTIFICATE_SHELL16_V1.md)).
계약은 shell 17과 완전히 같다(모듈 미수정). fresh coverage는 shell 18·17·16 세 인증서를 함께 재검증해 계산했다.
**shell 16 원래 domain 전체(격자점 50,000,618,227,463,141개) Certified.** 후보 **6,581개** 전부 정확 재평가, **hazard 0**.
**fresh coverage 14/64 region·gap 81**이며 shell 16·17·18 gap은 0이다. **R=20/④-4b 전체 NotCertified**다.
인증서 1024행은 ④-4c-9 생성기 행과 전부 일치한다. 원격 32스레드 실측: build·verify·저장본 verify 각 약 628초/19,760 CPU초(효율 0.98), coverage(세 인증서 재검증) 988초/30,590 CPU초. 전체 47분 57초.
예측한 shell 16 검증 비용(약 2.0×10⁴ CPU초)과 실측(19,761초)의 차이는 약 1%다.
**LOCAL FULL(`0117cd8`): 2834 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 398.68초.**
**REMOTE LINUX FULL(같은 커밋, 32워커 재실행): 2834 passed + 1 xfailed, skip 0, 361.87초, 2835개 항목별 로컬과 완전 동일.**
첫 원격 실행에서 `test_primal_precision.py`의 마지막 시험이 1회 실패했다. 원인은 시험 결함이다: xdist가 시험을 개별 단위로 나눠, 모듈 전역 `FELT`를 채우는 시험들과 다른 작업자에 배정되면 빈 리스트를 읽는다. 회귀는 아니지만 열린 결함으로 남긴다(처음의 "스케줄링 문제" 기록은 부정확해 정정).
증거: `runs/c1b1_hard_case_certificate_shell16_20260928/{certificate_full.json,certificate_full.log,local_full.*,remote_linux_full.*}`.
다음 판단(설계자): shell 15 survey_only 진입 여부(원격 약 1시간 5분 추정).

**설계자 판정 — shell 15를 마지막 확장성 조사로 두는 방향(2026-09-28):**
shell 15는 survey_only 한 번만 한다. 결과를 본 뒤 **현재 shell별 전수 hard-case 탐색 방식을 shell 14 이하로 계속 내려가지 않는다(STOP)**.
STOP은 반올림 연구 전체 중단이 아니다. exact 반올림 의미(정확한 값을 한 번 반올림)는 유지한다. 버리는 것은 "shell마다 무식하게 전수 인증"이라는 방법이다.
STOP 뒤 두 갈래: (A) 더 싼 수학적 방법(예: lattice reduction) 조사, (B) 판정 불가능한 부분을 명시적으로 멈추는 조건부 계약으로 정리.
**Proof Warehouse**(별도 브랜치 `claude/proof-warehouse-architecture-skrgwm`, 설계 문서만, 코드 0)는 **구현 보류·문서만 보존**한다. 반올림 전략이 바뀌면 저장할 proof의 양·종류도 달라지므로, 지금 v0를 시작하지 않는다. master와는 아직 합치지 않는다.
**화학/다입자**는 이번 결정에 포함되지 않는다. Ar-Ar 반올림 증명에 갇히지 않기 위한 방향 경고로만 기록한다. 지금 착수하지 않는다.
전체 순서: shell 16(완료) → shell 15 survey → 전수 방식 종료 판정 → 반올림 계약 최종 정리 → C1-B1 나머지 정리(inbound/inner/전체 산란각/E_min/native J) → C1-B1 freeze → 다입자·화학 조사. B/L은 건드리지 않는다.

**shell 15 hard-case 전수 조사(2026-09-28, 기준 `ab81005`) — 마지막 shell별 전수 조사:**
설계자 판정대로 shell 15를 마지막으로 한 번만 돌리고, **shell별 전수 hard-case 탐색 방식을 shell 14 이하로 잇지 않는다(STOP)**([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL15_SURVEY_V1.md)).
STOP은 반올림 연구 중단이 아니다. exact 반올림 의미는 유지하고, "shell마다 전수 인증"이라는 방법만 버린다.
원격 32스레드 실측: 교차 **250,139,754**(fixture 경계 수와 같음), 후보 **54,419**, **hazard 0**, checker **1024/1024**, brute force 누락 0.
같은 기계에서 다시 돈 shell 16 기준선의 행이 기존 fixture와 완전히 같다.
shell 16 대비 교차 5.33배, 후보 8.27배, 후보 밀도 1.55배, checker CPU 4.70배. ④-4c-9 예측(shell 16 실측 기반)과 이번 실측의 오차는 생성기 약 −1%, checker 약 −0.7%다.
교차당 비용(생성기 약 87µs, checker 약 363µs)으로 손 계산하면 shell 14 조사는 약 5시간, 인증은 약 17시간, shell 13은 각각 약 27시간·88시간으로 추정된다(측정 아님). shell 0〜4는 경계 수가 격자점 수보다 많아 교차별 처리가 원리적으로 불가능하다.
검증: survey_only라 LOCAL FULL은 생략했다. 새 시험 10개와 관련 시험 28개 통과, 변경은 새 파일만이며 해시 고정 소스 4개는 불변이다.
증거: `runs/c1b1_hard_case_shell15_20260928/{survey_full.json,survey_full.log}`.
다음 판단(설계자): 남은 gap 81개를 (A) 더 싼 수학적 방법(lattice reduction/SLZ, 또는 shell 0〜6 전체 impulse 트랙)으로 좁힐지, (B) 판정 불가를 명시적으로 멈추는 조건부 계약으로 정리할지.

**실행 기반 정밀도 조사(runtime stress survey, 2026-09-28〜29, survey_only):**
설계자 질문 "실제 궤적의 반올림 판정은 거의 128〜256 bit에서 끝나는가"를 실행기 무변경·읽기 전용 계측으로 쟀다([결과](docs/active/C1B1_RUNTIME_STRESS_SURVEY_V1.md)).
- R ≤ 20 bohr 주행: 궤적 10,481개·판정 약 1억 9,835만 회, 128 bit 99.36%·256 bit 0.644%, **512+ 0·판정 불가 0**. D_valid 안/밖 모두 같은 구조.
- hard-case 61,936점: 전부 256 bit(128 bit 구간 폭이 ulp의 2^3〜2^25배라 원리적으로 128 불가).
- 원인(관측에 맞는 해석, 증명 아님): 256 비율 = 128-bit 구간 폭(약 2^-7.5 ulp). 값이 경계에 대해 고르게 흩어진 것과 맞다.
- **처음 주행은 R=20으로 돌아오면 멈춰 pre-tail shell 0〜26에 들어가지 않았다.** 바깥 비행 14개로 R_J=10,240까지 가자
  R 640 이상은 256 bit 100%, 256-bit 폭 최대 2^-126 ulp, 판정 3,636만 회 **512+ 0**.
- 인증·coverage 변경 없음(14/64·gap 81), **④-4b NotCertified·④ 미동결·⑤ 미착수** 유지. 운영 실패(분석 파일로 캠페인 종료, 노드 약 12시간 유휴 과금)는 문서 5절에 기록.
- 검증: 관련 시험 26개는 원격 Linux에서 통과(캠페인 코드 기준). LOCAL FULL은 설계자 지시로 92%에서 중단했고(통과·기준선으로 세지 않음, 로그는 미완료 실행으로 보존), 변경이 새 파일·시험·문서뿐이라 관련 시험으로 대체했다. LOCAL FULL은 작업 묶음 끝의 push 또는 기준선 갱신 직전에 한 번 실행한다.
다음 판단(설계자): 전수 사전 인증 대신 "실행 + 판정 불가 정지 + 국소 증명" 구조를 검토할지, 남은 형식 의무(256-bit 폭 해석적 상한·유리수 tie 배제 확장·정지 계약) 범위.

**Runtime Fail-Closed Contract v0 + 국소 witness prototype(2026-09-29, 설계자 승인):**
([결과](docs/active/C1B1_RUNTIME_FAIL_CLOSED_V0.md)) 실행기 무변경.
- 1단계(계약 시험): 판정 불가·drift 선분·위치 범위로 거부된 step은 run을 전혀 바꾸지 않는다. 일찍 쓰는 결함 step을 검사가 잡는다. 6 passed.
- 2단계(prototype, survey_only): cap을 시험 설정으로 128에 두고 "정지 → 그 충격량만 계약 schedule로 재판정 → 저장 형태 검증 → 같은 step 재실행"을 돌렸다.
  궤적 3개(1,640 / 5,775 / 21,056 step) 모두 **매 step raw 상태가 정상 실행과 동일**, 정상 256 판정 = 거부 = witness(25/77/239). 변조 15종 거부. 23 passed.
- 한계: witness는 실행기와 같은 평가기를 쓰는 "executor rounding decision 재검증 witness"이며 독립 물리 검증이 아니다.
  실제 16384 판정 불가는 범위 밖(정지 유지). witness는 `runs/`에만 둔다. 14/64·gap 81·④-4b NotCertified 유지.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체(83 passed + 1 strict xfailed) / 새 파일만 추가.
다음 판단(설계자): 이 구조를 정식 방향으로 검토할지, 실제 16384 실패용 국소 증명 방법, 차등 계약·witness 형식·④ 동결 조건.

**설계자 판정(2026-09-29):** runtime + 국소 증명을 C1-B1 반올림 완전성의 **주력 방향으로 승격**. 버리는 것은 shell별 경계 사전 열거 방법뿐이며 ④의 의무는 약화하지 않는다.
④를 **Safety**(틀린 상태를 만들지 않음)와 **Liveness**(인정한 영역의 판정이 모두 해결됨)로 나눈다. 둘 다 닫혀야 ④ 동결. 실제 16384 실패용 point prover는 설계만 하고 구현하지 않는다.
계약: [Runtime Rounding Contract V1](docs/active/C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) — **구조 승인(2026-09-29).**
- 네 상태 RESOLVED / STOPPED / WITNESS_RESOLVED / UNPROVED(영구 STOP).
- **④-Safety**는 runtime 구조로 닫는다. 남았던 Fail-Closed 시험(`VMHalt`, 운동량 범위)을 추가해 8 passed.
  **후속 판정 D3:** A-EV(평가기 구간이 참값을 포함)를 S1〜S6보다 앞선 **선행조건**으로 둔다. A-EV 미해결이면 ④-Safety는 **Conditional**이다(현재 미해결).
- **④-Liveness 대상 = D_valid.** 실행 가능 영역(입장 계약)과 분리. 별도 수학적 보장이 필요하며 **NotCertified**.
  실행 단위 증명서 단독으로는 닫지 않는다. shell 전수 열거 대신 더 싼 방법(해석적 bound·prover completeness·Proof Box)으로 덮는다.
  (당시 문서의 "정확히 7개 에너지의 b 한 줄씩"은 구현자의 잘못된 요약이었다. 아래 조사 v0 참조.)
- 실제 16384 실패: point prover가 고정밀을 **탐색 도구로** 쓸 수 있으나, 정확 산술로 검증 가능한 certificate가 있을 때만 재개.
  **후속 판정 P1a:** 평가기를 cap 위에서 다시 돌리는 verifier는 불허. 허용은 (A) cap ≤ 16384 안의 검증 가능한 interval witness, (B) 평가기와 다른 수학적 근거(정확 유리수 부등식·modular-distance·exact tie·대수적 bound). 기준은 "검증할 때 고정밀 결과를 믿어야만 하는가".
- Runtime Proof Cache(엄격·매 사용 재검증)와 Proof Warehouse(실행 경로 밖) 분리, Hazard Atlas 판단 권한 0.
- 구현(wrapper·prover·cache)은 각각 별도 설계·승인 뒤. 14/64·gap 81·④-4b NotCertified 유지.
- **순서 변경(후속 판정):** Liveness 경로 조사 → point prover 설계 → 정말 필요하면 runtime wrapper. `_decide`의 `VMHalt`/`ExecutorLimitExceeded` 예외 분류 불일치는 ④ 최종 동결 전 정리 대상(지금은 실행기 무변경).

**④-Liveness(D_valid) 수학 경로 조사 v0(2026-09-29, survey_only, 문서만):**
([조사](docs/active/C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md)) 코드 변경·Vast·시험 추가 0. 수치는 동결 fixture·기존 모듈·기존 `runs/`를 읽기만 한 스크래치 계산이다.
- **전제 정정(먼저 공개):** 코드상 D_valid는 7개 에너지만이 아니다. **L**(1e-8〜약 0.1418 De, 모든 b, 임의 3D 배치) + **H**(약 0.9974〜10 De, 모든 b, 임의 배치) + **F**(7개 에너지의 궤도 포획 경계 옆 짧은 b 구간 14개, 폭 0.04〜0.14 bohr, b=0 없음)로 이루어진다. 계약 V1 2.2절을 정정했고 L0 재확인을 요청했다.
- **기존 형식 증거와 D_valid의 겹침:** 14 region은 전부 **+x축 1D 입력**이라 F 궤적과는 겹치지 않고, L·H의 정면충돌 상태에만 해당한다. 안쪽 R<20의 형식 증거는 없다. 실행 조사의 F 몫은 안쪽 6궤적이고 바깥 비행은 0이다.
- **결론:** 정량 Liveness(16384 안에서, 또는 정밀도 상한이 있는 증명으로)의 싼 경로는 없다. 안쪽은 exp가 지배해 유리식·합동류 방법이 원리적으로 불성립하고, 경계 전수 방법은 평면/3D에서 폭발한다.
- **새 후보(구현자 유도, 인증 아님):** 계수 전부 유리수 + 서로 다른 exp 지수 9개 → Lindemann–Weierstrass로 **모든 격자 입력(q_k≠0)의 정확 충격량은 유리수가 아니다 → 정확 tie 불가능**(exp 계수함수 5개가 양의 근 없음, 공약수 1). 영역 크기·차원 무관, 정성적. 엄밀 유리수 구간 prover와 결합하면 D_valid 전체의 **정성적** Liveness 후보가 된다.
- 기타: 격자 KDK의 정확한 시간 가역성(유도), 운동량 offset 다발(위치열 공유)을 기록했다. 둘 다 입력 간격 문제를 줄이지는 않는다.
- 검증: LOCAL FULL 생략 / 관련 시험 해당 없음 / 문서만 변경.
다음 판단(설계자): Q1〜Q4 → 아래 판정.

**설계자 판정(2026-09-29, 3차) + Lemma A·B 감사 v0(문서만):**
- **Q1:** L0 = D_valid 전체 유지(정정된 모양 확인).
- **Q2(계약 변경):** ④-rounding의 수학적 Liveness = **정성적 finite termination**. 16384는 실행기 fast-path 자원 한도로 남고, 별도 exact certificate prover가 correctness path다. 계약은 ≤16384 RESOLVED → 아니면 유한 exact certificate로 WITNESS_RESOLVED → 아니면 STOP. 정량 상한은 operational bound로 관리. 기존 ④의 "16384 안에서 결정" 요구를 바꾸는 계약 변경으로 기록했다.
- **Q3/P1b:** 허용, P1a 문구 수정. "16384 초과 평가기를 신뢰하지 않아도 독립적인 작은 checker가 exact arithmetic으로 참/거짓을 판정할 수 있어야 함". 구현 공유·`C._model`·`a_numeric.exp.enclosure` 재사용 금지.
- **Q4:** r_min·overflow·포획 없는 R_J 도달은 별도 trajectory-completion obligation(C1-B1 freeze 전).
- **감사**([문서](docs/active/C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md), 구현자 감사, 인증 아님):
  - **Lemma A 통과.** QED short 2의 V′ 계수 cR(2−αR)가 R ≥ r_min에서 0이 아니다. 이것만으로 Lindemann–Weierstrass에 의해 dr_k ≠ 0인 모든 입력의 정확 충격량은 초월수이고 tie는 불가능하다. 9개 공통근 조사는 필요 없다.
  - **Lemma B 수학적으로 성립, 구현 전.** √ isqrt 구간, e^{−y} ∈ [(1−T_n)/S_n, 1/S_n], 유리수 구간 산술로 폭 → 0이다. 최대 위험은 checker 식 전사 충실도이며 구현 시험 의무로 둔다.
  - 정정: 조사 v0의 "새로 찾은 전역 결과"는 과장이었다. 동결 C1-A 머리말에 같은 관찰이 이미 있다.
- 검증: LOCAL FULL 생략 / 관련 시험 해당 없음 / 문서만 변경.
다음 판단(설계자): Lemma A·B 감사 판정 → 아래 판정.

**설계자 판정(2026-09-29, 4차) + certificate·checker 사양 V1(문서만):**
- **Lemma A 승인, Lemma B 방향 승인.** 둘 다 **accepted design basis, not frozen certificate**(audited mathematical lemma).
- Lemma B의 exp 구간을 **1/(S_n+U_n) ≤ e^{−y} ≤ 1/S_n**으로 정정했다. U_n = y^{n+1}/(n+1)!·(n+2)/(n+2−y), 조건 n+2 > y, 순수 급수 꼬리 상한이다. 이전 (1−T_n)/S_n은 정의대로라면 유효했고 같은 값이지만, 표현을 바꿨다. 스크래치 대조 28건 위반 0(증명 아님).
- P1b 재확인: 같은 수학 정리를 독립 구현하는 것은 허용. 금지 항목은 그대로다.
- **[사양 V1](docs/active/C1B1_EXACT_IMPULSE_CERTIFICATE_SPEC_V1.md):**
  - certificate는 매개변수만 담는다(√ bit N, exp 9개의 모드·차수).
  - checker는 표준 라이브러리만 쓰고, 상수표를 직접 적고, 동결 지문 `ada6153b…839e`로 묶는다.
  - 결과는 VALID(m)/INVALID/REFUSED(운영 한도) 중 하나다. 엄격 분리만 인정한다.
  - `zero_floor` 모드(e^{−x} ∈ [0, 1/S_n])는 큰 R의 운영 지름길이며, Liveness 증명은 `full`에만 의존한다.
  - 시험 의무 T1〜T9: 독립성, 지문, 교차검증 수천 건, 식 결함 주입, exp·√ 부등식, 음성, rehearsal, 운영 한도.
- 기존 shell 인증서는 삭제·무효화하지 않고 교차검증 자료로 쓴다. A-EV는 별개로 남고 ④-Safety는 Conditional이다.
- 검증: LOCAL FULL 생략 / 관련 시험 해당 없음 / 문서만 변경.
다음 판단(설계자): 사양 V1 승인(S1〜S4) → 아래 판정.

**설계자 판정(2026-09-29, 5차): S1〜S4 전부 승인 + 독립 checker 구현·시험(survey_only, 새 파일만):**
- 승인 원칙: *Operational limits affect availability, never truth.* 한도 초과는 REFUSED이며 INVALID가 아니다. 한도를 바꿔도 VALID/INVALID는 바뀌지 않는다(시험 T9).
- 구현: `a_reference/c1b1_exact_impulse_checker.py`(표준 라이브러리 5개만, 자체 상수표 + 동결 지문 binding), 탐색기(시험 보조), 교차검증 드라이버(mpmath 세 번째 구현 포함), `tests/test_c1b1_exact_impulse_checker.py` 127개. 실행기·C1-A 평가기·동결 fixture·기존 인증서 변경 0.
- **교차검증(T3, 로컬 5 워커 1,123초, Vast 없음): 10,191 입력·14,102 성분 판정에서 checker VALID raw = 실행기 raw, 불일치 0.** 안쪽·축·바깥·먼 점·65점·hard-case 후보 7,517(shell 16/17/18 전부)·shell 24〜26 후보 3·near-tie 200(경계에서 2^-10〜2^-140 ulp, 위·아래). 128비트로 충분 14,023건, 256비트 79건은 전부 near-tie.
- **식 결함 주입(T4) 40종 전부 잡힘**(전부 `raw_mismatch`; 부호·α·kadd·retardation 분기와 g′·2k·거듭제곱·dt·성분·단위·국소 고차항). 상수 오류는 지문이 막고, 지문을 우회해도 19건 중 18건은 교차검증이 잡는다. **예외: `RET_B[5]`(R⁶ 계수) 마지막 자리는 지문만이 막는다**(시험으로 고정).
- rehearsal(T8): cap 128로 멈춘 near-tie와 실제 궤적 거부 충격량 전부를 certificate가 full-cap raw로 증명. 필요한 √ 비트는 경계가 가까울수록 커진다.
- 한계: 식 전사는 시험으로만 보장(형식 증명 없음), A-EV는 별개(④-Safety Conditional 유지), 정성 Liveness는 Lemma A·B 논거에 기댐(관측은 sqrt_bits ≤ 256이지만 상한 아님), 운영 한도 기본값은 관측 기반 초기값. 사양에서 `time` import 1개 추가.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 새 파일(모듈 3·시험 1)과 문서만 추가, 기존 실행 코드·동결 계약·fixture 변경 0. 새 시험 127개 + 직접 영향 범위(`two_atom`, `runtime_local_witness`, `step_fail_closed`, `stress_survey`, `c1a_ar2_lang2024`) **222 passed + 1 xfailed**. 기준선 숫자는 갱신하지 않는다.
다음 판단(설계자): checker 신뢰 판정 → point prover generator → runtime wrapper·Proof Cache. 운영 한도 기본값과 `time` import 추가를 확인해 주세요.

**checker 초대형 정수 문자열 수정(2026-09-29, `e6a377d` 뒤 검토 지적, 범위 한정 수정):**
- 결함: 4301자리 이상의 십진 문자열이 `raw`·`dr_raw`·`sqrt_bits`·`order`·`dt_kick`에 있으면 Python `int()` 한도의 `ValueError`가 checker 밖으로 유출됐다(재현 확인, 4300자리 이하는 정상).
- 수정: 구문 오류 → INVALID(길이 무관, 크기보다 먼저), 구문이 맞고 자릿수 > `digits_max`(기본 4300) 또는 프로세스 `int()` 한도 초과 → **REFUSED(`integer_size_limit`)**. VALID/INVALID의 수학적 의미는 불변(4300자리 이하 결과가 수정 전과 같음을 시험으로 고정). 운영 한도는 가용성만 바꾼다.
- 시험: T10 35개 추가(9개 필드 × 4300/4301/10000자리, 구문 우선, 프로세스 한도 시뮬레이션, 결함 주입). 새 파일 전체 162개 통과. 사양 T1의 표준 라이브러리 수를 5개로 정정.
- 범위 밖으로 유지: point prover generator, 실행기·평가기·동결 계약, A-EV, ④-Safety Conditional 승격, 새 물리 계약. 대규모 교차검증 캠페인·LOCAL FULL은 재실행하지 않았다(검증기 파싱 경로만 변경, 판정 수식 불변).

**checker 파서 작업량 보강(2026-09-29, `1215b9c` 뒤 검토 지적, parser 방어 마감):**
- 결함(재현): 사전 통과가 `dr_raw`·`proof.exp`를 길이 확인 전에 전부 순회했다(100만 원소에서 0.3초·1.1초). 키 검사(`set(d)`)도 같은 종류였다. 수학적 soundness 문제는 아니며 가용성·작업량 문제다.
- 수정: 모양을 먼저 본다(`dr_raw` 3개, `exp` 9개, 키 개수). 틀린 크기의 리스트·딕셔너리는 원소를 보지 않고 즉시 INVALID. 100만 원소에서 순회 0회.
- 문구 정정: 사양의 "어떤 Python 예외도 checker 밖으로 나가지 않는다"를 "시험한 적대적 입력에서 `int()` 변환 예외를 포함해 유출하지 않는다, 모든 예외에 대한 형식적 보장은 아님"으로 좁혔다. 광역 `except Exception`은 넣지 않았다(버그가 REFUSED로 숨는 것을 막기 위해. AST 시험으로 고정).
- 시험: T11 23개 추가. checker 시험 전체 185개. 사양 8.6절. 설계 변경·point prover·A-EV·④-Safety 상태는 그대로다.

**설계자 판정(2026-09-29, 7차): independent exact impulse checker 신뢰 승인(`e9b30eb`, 원격 master HEAD 확인됨).**
- T1〜T11과 독립 교차검증 근거를 수용한다. parser robustness 보강은 현 단계에서 종료한다. 거대 문자열 O(N) 읽기는 나중에 runtime wrapper의 certificate 전체 바이트 크기 상한으로 막는다.
- A-EV 미해결, ④-Safety Conditional, ④ 전체 Certified/Frozen 아님(변경 없음).
- 다음: point prover generator 설계 및 구현. 원칙: 비신뢰 생성기(무엇을 써서 후보를 찾아도 됨), 최종 권한은 `check_certificate == VALID(raw)` 하나, 실행기 16384 cap을 늘리는 프로그램 금지(별도 correctness path), 싸게 시작해 올림, REFUSED와 "아직 못 찾음" 구분(Lemma A+B는 운영 한도 안의 발견을 보장하지 않음), 첫 검증은 cap 128 rehearsal과 near-tie 합성, 그 뒤 wrapper·Proof Cache.
- 설계 V0: [point prover 설계](docs/active/C1B1_POINT_PROVER_DESIGN_V0.md). 설계자 판정 대기(P-1〜P-5).
- **먼저 공개할 측정(scratchpad):** 합성 입력(경계에서 2^-17000 ulp)에서 실행기는 cap 16384로 `ReferenceUndecided`를 냈다(13초). 그러나 현재 checker V1(반올림 없는 정확 유리수)의 비용은 √ 비트 N에 대해 거의 N³이다(N=256/512/1024/2048에서 2.6/14.6/104.8/871초). 그래서 **실제 16384 STOP의 certificate는 며칠〜몇 주 걸려 현실적으로 불가능하다.** 정성 Liveness는 수학적으로 맞지만 지금은 운영상 쓸 수 없다. 해법 후보는 checker V2(구간 끝점의 바깥쪽 dyadic 반올림, 사양 변경, P-5)다.

**checker V2 — outward dyadic rounding(2026-09-29, 기준 HEAD `0ce4527`, survey_only·새 파일 중심):** ([설계·결과](docs/active/C1B1_EXACT_IMPULSE_CHECKER_V2_DESIGN.md))
- 목적: V1의 정확 유리수 폭증(√ 비트 N에 거의 N³)을 막는다. 구간 끝점을 work_bits 유효 비트로 **항상 바깥쪽** 반올림한다(하한은 −∞ 쪽 floor, 상한은 +∞ 쪽 ceiling. 잘린 비트는 구간 폭에 흡수). 세계 상태의 반올림이 아니며 실행기·물리·once-rounding은 그대로다.
- **V1 변경 0**(소스 해시를 `e9b30eb`판에 고정, V1 시험 185개 통과). V2는 별도 모듈·형식·method이고 V1·실행기·`a_numeric`를 import하지 않는다(상수표·파서도 독립). 기존 파일 수정은 1개(`c1b1_exact_impulse_crosscheck.near_tie_item`에 `dt_bits`, 기본값 동일)다.
- 반올림 지점: 곱·나눗셈·역수, exp·damping 급수의 매 단계, 항 조립마다 1회, 비-dyadic 상수. neg·항 내부의 고정 덧셈·√·최종 J는 반올림하지 않는다. `sqrt_bits`와 `work_bits`는 certificate의 별도 필드다. checker 안에 guard 상수는 없다(guard 96은 비신뢰 탐색기의 선택).
- 시험 95개 통과. **결함 주입 50종 전부 잡힘**(방향 반올림 5·구간 연산 7·√ 2·거듭제곱 2·exp 점별 7·exp 단계별 7·반올림 제거 2·식 전사 18). **먼저 공개:** 처음에는 exp 끝단 반올림 방향 뒤집기 3종이 점별 포함 시험을 통과했다(급수 여유가 가림). 단계별 정확값 비교 시험을 추가해 잡았다. work_bits를 N 이하로 낮춘 "guard 제거" certificate에서 틀린 VALID는 0건이다.
- **교차검증: 14,102건에서 V2 = 실행기 = V1, 불일치 0**(83초). 첫 요약의 "V1과 불일치 100건"은 near-tie 위·아래가 같은 대조 키로 겹친 드라이버 결함이었다. 키를 고친 뒤 0건이며, 잘못된 요약은 invalid-measurement로 보존했다.
- 성능(같은 입력): N=256/512/1024/2048에서 V1 2.5/14.5/106/871초 → V2 0.06/0.11/0.33/1.09초(40〜800배). enclosure 폭은 N=256/512/1024에서만 V1과 같음을 측정했다(N=2048은 V2 폭만 기록, V1과의 동일성은 **미측정**). V2 가수는 P+2비트로 묶인다(V1은 최대 1,060만 비트). V2는 4096/8192/16384에서 5.1/23.6/127초다.
- **2^-17000 합성 STOP:** 실행기는 cap 16384에서 `ReferenceUndecided`(13초). **V2는 N=17408에서 위·아래 모두 VALID(142/147초), raw = mpmath 5,700자리 기대값**, 틀린 raw는 전부 INVALID. 기본 한도로는 합성 `dt_kick`(약 5,300자리)이 `digits_max`에 걸려 REFUSED다(실제 runtime 입력에는 없는 합성법의 문제).
- 미증명: V2 건전성은 논증과 시험 기반(형식 증명 없음), 식 전사는 시험 기반, V2 신뢰 승인은 설계자 판정 대기, A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**, prover·wrapper·Proof Cache 미연결.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 새 파일(checker V2, 탐색기, 드라이버, 시험)과 문서, 그리고 survey 보조 모듈 1개에 기본값 동일한 선택 매개변수만 추가했다. 실행기·물리·동결 계약·fixture·V1 변경 0. **V2 95 + V1 185 = 280 passed**. 기준선 숫자는 갱신하지 않는다.
- 증거: `runs/c1b1_exact_impulse_crosscheck_v2_20260929/`, `runs/c1b1_exact_impulse_checker_v2_20260929/{perf_v1v2,v2_scaling,v1_scaling_17000_input,deep_ladder,stop17000}.txt`.
다음 판단(설계자): 아래 판정.

**설계자 판정(2026-09-29, 8차, 기준 HEAD `1baedc8`): checker V2 신뢰 승인.**
- V2를 V1과 같은 의미의 독립 trusted exact-impulse checker로 승격한다. **formal certified가 아니다**(시험 통과와 형식 증명은 분리).
- 승인 범위: 특정 `(dr_raw, component, dt_kick)`와 certificate에 대해 frozen C1-A exact impulse가 FX(96,80)의 제시된 raw로 반올림됨을 V2의 엄밀한 enclosure로 검증한다. **④-Liveness, ④-Safety, A-EV, 전체 궤적 정확성은 승인되지 않는다**(one-step과 trajectory correctness 분리).
- 정정: V1/V2 enclosure 폭의 동일성은 N=256/512/1024에서만 측정했고 N=2048은 V2만 기록했다(V1과의 동일성 미측정). 2^-17000 사례는 V2와 mpmath의 독립 일치이지 V1과의 교차검증이 아니다. 대규모 랜덤 캠페인은 더 돌리지 않는다.
- 다음: point prover V0(비신뢰 생성기, 성공은 `V2 checker == VALID(raw)`뿐, FOUND/NOT_A_DECISION/EXHAUSTED/ANOMALY, ANOMALY는 재시도로 FOUND를 만들지 않음) → cap-128 rehearsal·near-tie·2^-17000 → runtime wrapper(모델 상향 필요) → Proof Cache.

**point prover generator V0(2026-09-29, 기준 HEAD `1baedc8`, survey_only·새 파일):** ([설계·결과](docs/active/C1B1_POINT_PROVER_DESIGN_V0.md) 9절)
- **비신뢰 생성기.** 유일한 성공은 `V2 checker == VALID(raw)`이고 FOUND는 항상 checker 판정을 동반한다. 실행기 평가기·`MAX_PRECISION_BITS`·V1을 참조하지 않는다(AST 시험). 결과 4종: FOUND / NOT_A_DECISION / EXHAUSTED(prover 예산·checker REFUSED·직렬화 한도, 참/거짓 아님) / ANOMALY(재시도로 FOUND를 만들지 않고 정확히 1회 checker 호출 뒤 멈춤).
- 방식: mpmath로 raw와 경계까지 거리를 스스로 추정 → √ 비트 N·work_bits P 선택(N = round64(거리 비트 + |y| 비트 + 40), P = N + 96; 이 40·96은 **생성기의 휴리스틱**) → checker V2 1회 → not_separated이면 N을 3/2배.
- 시험 24개(35초), 결함 주입 5종(checker 건너뛰기, not_separated를 성공 처리, ANOMALY 재시도, REFUSED 무시, 거리 측정 상실) 전부 잡힘. V1·V2·실행기·평가기·동결 계약 변경 0.
- **검증(prover는 raw를 받지 않음):** 표본 2,660 성분 전부 FOUND·일치·**첫 시도 VALID 100%**(중앙값 0.05초). **cap-128 rehearsal 실제 궤적 3개(1,640 / 5,775 / 21,056 step): 거부된 충격량 25 / 77 / 239개(성분 682개) 전부 해결, raw = full-cap 실행기.** near-tie 2^-10〜2^-1000·2^-4000 위·아래 FOUND.
- **2^-17000(실행기 cap 16384 `ReferenceUndecided`): prover가 위·아래 모두 raw와 거리를 스스로 추정해 첫 시도(√ 17152)에 FOUND, raw = mpmath 기대값(각 188초).** 기본 한도로는 합성 `dt_kick`(약 5,300자리) 때문에 EXHAUSTED(`checker_refused:integer_size_limit`).
- 실패 기록(보존): 시험 25분은 변이체 설계 문제(35초로 수정), 3단계 첫 요약의 `agree: false`는 재검증을 기본 한도로 한 드라이버 결함(같은 한도로 재실행), 재실행의 BrokenProcessPool은 표준입력 스크립트의 spawn 문제(모듈 진입점으로 재실행).
- 미증명: 추정기 수락 규칙은 휴리스틱(틀리면 ANOMALY), 표본 결과는 전 입력 보장이 아님, A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**, wrapper·Proof Cache 미연결.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 새 파일(prover, survey, 시험)과 문서만 추가, 기존 코드 변경 0. **prover 24 + checker V2 95 + V1 185 = 304 passed**(아래 확인). 기준선 숫자는 갱신하지 않는다. 증거: `runs/c1b1_point_prover_20260929/`.
다음 판단(설계자): prover V0 판정 → runtime wrapper 설계(STOP 시 prover 호출, WITNESS_RESOLVED 기록, 같은 step 재실행, certificate 바이트 크기 상한; Opus 5.5 High 권장) → Proof Cache.

**설계자 판정(2026-09-30, 기준 HEAD `99830f2`): point prover V0 승인(비신뢰 generator). 추정 overflow의 상태 의미 1곳을 정정한 뒤 runtime wrapper 단독 구현, Proof Cache는 그 뒤.**
- 정정: prover의 추정값이 출력 범위 밖이면 `NOT_A_DECISION("overflow")`가 아니라 **`EXHAUSTED("estimate_out_of_output_range")`**다. NOT_A_DECISION은 입력만으로 정확히 정해지는 경우에만 쓴다. 실제 출력 overflow는 실행기의 종결 거부이며 prover로 오지 않는다.

**runtime wrapper V0(2026-09-30, survey_only·새 파일):** ([계약·결과](docs/active/C1B1_RUNTIME_WRAPPER_V0.md))
- 계약 W1〜W8(설계자 조건): 실제 `ReferenceUndecided`만 prover로, FOUND도 바이트에서 재검증(크기 → JSON → binding → 입력 동일성 → checker V2 VALID → raw 일치), step을 처음부터 재실행, 재실행 중 실행기가 **바로 그 입력에서 다시 멈출 때만** witness raw 사용, NOT_A_DECISION/EXHAUSTED/ANOMALY/REFUSED는 진행 금지, 파싱 전 바이트 상한(256 KiB, 가용성만), on/off 차등, 결함 주입.
- 실행기 소스는 바꾸지 않고 `C.impulse`·`C._decide`를 step 동안만 감싼다(모든 경로에서 복원, 스레드 안전하지 않음). wrapper는 cap을 건드리지 않는다.
- 시험 30개 통과. 결함 주입: checker 생략, 입력 검사 제거 ×3(일관된 위조), binding 검사 제거, witness 없이 재개, step 중간부터 재개, 실행기 결정보다 witness 우선, 심은 witness 5종, stale binding, 재검증 REFUSED — 전부 잡힘.
- **cap-128 rehearsal 실제 궤적 3개(1,640 / 5,775 / 21,056 step): 매 step full-cap 정상 실행과 비트 동일, witness 사용 25 / 77 / 239 = 정상 실행의 256-bit 판정 수.** 정상 궤적에서 wrapper on/off 동일, prover 호출 0.
- **실제 cap 16384 STOP을 한 step 안에서 닫음(합성 2^-17000, 위·아래): 실행기 단독은 `ReferenceUndecided`, wrapper는 WITNESS_RESOLVED(성분 2개, witness raw = mpmath 기대값), 한 step 791초**(W2 재검증이 checker 비용을 두 배로). 기본 한도로는 합성 `dt_kick` 때문에 UNPROVED(`exhausted:checker_refused:integer_size_limit`).
- 실패 기록: 첫 시험 12건 실패는 가짜 prover의 자기 재귀·변이체의 `__file__` 부재(시험 결함). "입력 검사 제거" 변이체가 raw 일치 검사에 막힌 것은 방어가 두 겹이라는 뜻이며, 입력 검사만 시험하도록 일관된 위조로 바꿨다.
- 미증명: wrapper 정확성은 시험·차등 비교 기반, `_decide` 순서와 성분 대응은 실행기 구현에 의존(어긋나면 차등 비교가 잡음), hook은 스레드 안전하지 않음, A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**, Proof Cache 없음.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 새 파일(wrapper, survey, 시험)과 prover의 상태 의미 1곳, 문서만 변경. 실행기·평가기·checker·동결 계약 변경 0. wrapper 30 + prover 24 + V2 95 + V1 185 + fail-closed·witness prototype·two_atom = **406 passed + 1 xfailed**(기존 strict xfail). 기준선 숫자는 갱신하지 않는다. 증거: `runs/c1b1_runtime_wrapper_20260930/`.
다음 판단(설계자): wrapper V0 판정 → Proof Cache(검증된 witness 재사용, 매 사용 재검증) 설계.

**설계자 판정(2026-09-30, 기준 HEAD `1140628`): Runtime Wrapper V0 구조·동작 승인(single-threaded C1-B1 reference 실행의 V0 구현 증거까지). 정식 witness binding은 profile identity 보강 전 미완.**
- 구멍: `_supported()`가 profile의 name/width/frac_bits만 봐서, 같은 메타데이터의 다른 반올림 구현이 half-even FX로 오인될 수 있었다(checker가 옳아도 세계에 틀린 raw가 들어가는 witness soundness 문제). binding의 `rounding: half_even`은 확인 없는 문자열이었다.
- 기록성: WITNESS_RESOLVED에 certificate 본문이 없어 `StepOutcome`만으로 재검증할 수 없다. Proof Cache에서 canonical certificate bytes를 불변 저장(SHA-256은 주소·변조 검사용)하고, canonical 실행에 쓰는 시점부터 content address를 기록한다.
- hook(`C.impulse`·`C._decide` 전역 교체)의 스레드 비안전은 V0에서 허용, 최종 병렬 world executor 전 정식 hook/callback으로 교체하는 기술부채.

**runtime wrapper profile identity 보강(2026-09-30, wrapper·시험·문서만):** ([9절](docs/active/C1B1_RUNTIME_WRAPPER_V0.md))
- 지원 조건을 `_canonical_fx`로 교체: `type(p) is FixedPoint`(subclass·look-alike 거부), 인스턴스 속성이 생성자의 5개뿐, 실행기가 부르는 클래스 메서드가 import 시점과 같은 객체, half-even 알려진 답 탐침. position·momentum 둘 다. stop 때 prover 전과 `verify_witness` 맨 앞(바이트 읽기 전) 두 곳.
- binding에 `profiles_sha256`(`a_numeric/profiles.py` LF SHA-256) 추가, profile 기록에 구현 클래스와 **확인된** rounding(`half_even`/`unverified`). 떠 있던 `rounding` 문자열 필드 삭제.
- 시험 12개 추가(wrapper 42개): 이름·폭·소수 비트가 같은 위조 7종이 모두 실제 cap-128 STOP에서 UNPROVED(`unsupported_profile`)·prover 0회·run 불변. 결함 주입: V0 메타데이터 게이트 변이체는 half-up 위조에 WITNESS_RESOLVED(원래 결함 재현), `isinstance` 변이체·탐침 제거 변이체는 각각 위조를 prover까지 보냄. `profiles_sha256`만 다른 binding은 stale.
- 한계: 3·4층은 실행 중 교체에 대한 방어이며 탐침 밖에서만 다른 교체는 못 잡는다(프로세스 내 코드 신뢰 전제). Proof Cache 미착수, A-EV 미해결, ④-Safety Conditional, **④-Liveness NotCertified**.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: wrapper(survey_only 계층)·시험·문서만 변경, 실행기·평가기·checker V1/V2·prover·동결 계약 변경 0. **418 passed + 1 xfailed**(기존 strict xfail), 245.59초. 기준선 숫자는 갱신하지 않는다. 증거: `runs/c1b1_runtime_wrapper_profile_identity_20260930/`.
다음 판단(설계자): profile identity 보강 재판정 → Proof Cache 설계(certificate bytes 불변 저장, 매 사용 재검증, prover 탐색만 생략).

**설계자 판정(2026-09-30, 기준 HEAD `e7b46c3`): Point Prover V0 승인, Runtime Wrapper V0 승인, witness profile binding 승인.** 실행 중 프로세스 자체를 악의적으로 monkey-patch하는 경우까지 막는 것은 위협 모델 밖이다(위협 모델 = 저장소의 잘못된 구현·실수). profile 방어나 랜덤 시험은 더 만들지 않는다. 418 passed + 1 xfailed는 구현자 실행 기록이며 설계자는 소스·시험 구조를 확인했다. 다음: 작업선 분리 → Warehouse 제안서와 Proof Cache의 관계 검토 → Proof Cache.
- 작업선 상태: Codex worktree `.codex/worktrees/a-ev-audit`가 `e7b46c3` 기준(detached HEAD)으로 존재한다. 이 작업선은 그 worktree와 `audit/independent_physics/`를 건드리지 않는다.

**Proof Cache ↔ Warehouse 관계 검토(2026-09-30, 문서만):** ([검토](docs/active/C1B1_PROOF_CACHE_WAREHOUSE_RELATION_V0.md))
- 결론: **저장소 두 개를 만들지 않는다.** 이미 계약 V1 D6으로 분리돼 있다. Proof Cache = 실행 경로 안의 작은 witness 선반(매 사용 재검증), Warehouse = 실행 경로 밖의 색인·의존성 장부. 관계는 한 방향이다: 나중에 Warehouse가 Cache 객체를 읽기 전용으로 등록한다.
- Cache가 따를 Warehouse 규칙 R1〜R7: 조회 키와 content address 분리, run metadata를 객체 밖에, 정규 바이트 그대로 저장, 추가 전용 해시 체인 색인, REJECTED는 스스로 풀리지 않음, 파일 형식 문서화, import 방향. 측정: prover certificate에는 시간·시도 필드와 float가 없고, 같은 입력을 두 번 증명하면 certificate가 필드 단위로 같다.
- 불일치 공개: (1) master 문서가 master에 없는 Warehouse 제안서(원격 브랜치에만 있음)를 인용한다, (2) 계약 7절의 "정밀도 schedule"이 binding에 없고, "실제 cap 16384 STOP만 저장" 조건은 "wrapper는 cap을 읽지 않음"과 충돌한다, (3) 선반 위치 미정, (4) Proof Box는 V0 범위 밖, (5) 실제 궤적에서 cap 16384 STOP은 아직 관측되지 않았다(합성 2건뿐).
- 코드·시험 변경 0. Warehouse 브랜치는 병합하지 않았다.
다음 판단(설계자): Q-PC1(선반 위치)·Q-PC2(cap 조건 충돌)·Q-PC3(REJECTED 처리)·Q-PC4(Warehouse 인용) 확인 → Proof Cache V0 구현.

**설계자 판정(2026-09-30, 기준 HEAD `56af433`→`073c9c3`): Q-PC1 수정(하나의 선반), Q-PC2 계약 수정(정밀도 schedule은 binding이 아니라 Cache admission metadata), Q-PC3 일부 수정(STALE/REJECTED/REFUSED 구분, REFUSED는 REJECTED가 아님), Q-PC4(Warehouse 제안서 파일 하나만 문서로 편입, branch 병합 금지, Q9~Q11 미승인).** 반영: `073c9c3`(문서만).

**Proof Cache V0(2026-09-30, 구현 `403a42d` + 시험 확장, 로컬):** ([계약·결과](docs/active/C1B1_PROOF_CACHE_V0.md))
- `runs/c1b1_proof_cache_v0/` 하나의 append-only 선반(`objects/<sha256>` = certificate 바이트 그대로, `index.jsonl` = 정확한 key → 주소, `events.jsonl` = 입고·사용 기록), 로그는 해시 체인 + 색인 줄 교차 참조. 조회는 STOP에서만, hit도 wrapper의 전체 재검증(크기 → 주소 해시 → JSON → binding → 정확한 입력 → checker V2 VALID)을 거친다. **캐시는 prover 탐색만 생략하고 checker는 생략하지 않는다.** STALE / REJECTED / REFUSED 구분, REJECTED는 부활하지 않음. 입고는 wrapper 밖의 admission 층이 하며(cap을 읽는 곳은 여기뿐) production 선반은 실제 cap 16384 STOP의 witness만 받는다.
- **시험:** Proof Cache 42개. 캐시 OFF / 빈 캐시 / 찬 캐시가 궤적 2개(1,640 / 5,775 step, cap-128 rehearsal)에서 매 step 상태·매 witness 결정이 비트 동일, 찬 캐시는 prover 0회·checker witness당 1회. 요청된 결함 주입 11종(1bit 변조·바꿔치기·다른 binding·다른 dr/component/dt·malformed/oversized·missing·index 변조·INVALID·REFUSED·REJECTED 재사용·한 key 여러 주소)과 캐시 변이체 4종 전부 잡힘. **VAST 관련 시험 묶음(REMOTE LINUX, RTX 3090): 529 passed + 1 xfailed, 실패·skip 0, 194초.** 첫 원격 실행의 2건 실패(527 passed)는 제 참조 파일 링크 설정 오류였고 로그를 보존했다.
- **한계(숨기지 않음):** 해시 체인은 formal tamper-proof가 아니다. events 마지막 줄의 변조와 index·events 꼬리의 일관된 재작성은 로그만으로는 못 잡는다(시험으로 확인). 이것이 물리 correctness로 전파되지 않음도 시험한다: 로그 문구는 raw를 승인하지 않고, 저장된 witness는 쓸 때마다 전부 재검증된다. 실제 production cap 종단 입고는 시험하지 않았다(13분/건). 정식 선반은 비어 있다. single writer.
- **검증:** 관련 시험 묶음(VAST) + **LOCAL FULL `-n 6`(HEAD `1636b1d`): 3289 passed + 1 xfailed, skip 0, 실패·error 0, exit 0, 554.35초**(설계자 지시: wrapper 통합을 넣었으므로 Gate 종료 시 1회). 이전 기준선 2834보다 455개 많은 것은 그 사이 Gate들이 LOCAL FULL을 생략한 몫이며 회귀가 아니다. 컴파일러 인코딩 경고는 이번 요약에 안 보이지만 원인 미조사, 해결로 보고하지 않는다. `AGENTS.md`의 기준선 숫자는 설계자 판단 전이라 고치지 않았다. 증거: `runs/c1b1_proof_cache_v0_validation_20260930/`.
- 상태: 아래 판정과 종단 시험으로 **Proof Cache V0 = APPROVED.** ④-Liveness 인증이 아니다. A-EV 미해결(별도 작업선), ④-Safety Conditional, **④-Liveness NotCertified**.

**설계자 판정(2026-09-30, 기준 HEAD `a0ec008`): Proof Cache V0 기본 구조·재검증·OFF/empty/warm 불변성·STALE/REJECTED/REFUSED 분리·로그 위조의 권한 없음·tail 한계 공개·관련 시험 529·LOCAL FULL 3289 승인. 마지막 조건: 실제 production cap 16384 STOP의 종단 입고 정확히 1건. 통과하면 APPROVED. `AGENTS.md` 기준선은 3289 + 1 xfailed, skip 0으로 갱신(FULL 재실행 없음).**

**Proof Cache V0 production cap 종단 입고 1건(2026-09-30):** ([6.4절](docs/active/C1B1_PROOF_CACHE_V0.md))
- 합성 near-tie `2^-17000`(합성 스트레스 상태, 물리 주장 아님), 실행기 cap 16384 그대로. X1(빈 production 선반) `ReferenceUndecided`(15.1초) → prover FOUND → wrapper 재검증 → step 진행 → 입고: STOP 2회(성분 0·1, 이 step의 정확한 충격량이 같음), certificate 각 33,692바이트, object/index/admit event 각 2개, metadata `production`·cap 16384/16384·`production_stop = true`, **732.5초**. X2(같은 선반 재실행): source 전부 `cache`, **prover 0회·checker 2회**(witness당 1회), hit 2건, **299.3초**. 캐시 OFF 736.0초. raw는 X1 = X2 = OFF = mpmath 기대값, 최종 world state SHA-256 동일. 조건 14개 모두 참.
- 실행 기록: 첫 실행은 13/14 참(exit 1). 1개는 제 스크립트의 `int == str` 비교 오류였고 값은 같았다. 스크립트를 고치고 다시 실행하지 않고 기록된 요약에서 재평가했다(그 조건 하나는 기록값 재평가). 로그 보존.
- 검증 범위: 종단 시험 1건만. **LOCAL FULL 재실행 없음**(지시). 스크립트는 스위트 밖 survey_only 새 파일이며 기존 코드 변경 0. 증거: `runs/c1b1_proof_cache_production_e2e_20260930/`.
- 한계: 합성 입력 1건의 종단 확인이다. 실제 궤적의 production STOP 관측은 0건이고 정식 선반은 비어 있다. **④-Liveness 인증 아님.** A-EV·④-Safety Conditional·④-Liveness NotCertified 변경 없음.
다음 판단(설계자): ④-Liveness 쪽 다음 단계(rounding-decision completeness) 지시.

**설계자 판정(2026-09-30, 기준 HEAD `af0a341`): Proof Cache V0 최종 승인.** 종단 입고 시험의 `int == str` 실패는 판정식의 자료형 오류이며, 저장값 재평가로 충분하다(재실행 없음). 이번 작업: 문서 정합성 정리 + ④-Liveness 수학 연결 감사(코드 변경 없음).

**Point Prover 정성적 완결성 감사 V0(2026-09-30, 문서·수학만):** ([감사](docs/active/C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md))
- 질문: prover의 무한 정밀도 schedule이 지원 입력 전부에서 유한 단계 안에 checker V2 VALID를 찾는가. **결과: 분류 B.** 수학적으로는 가능하지만 현재 `prove()` 경로에 구멍이 있다. **완결성 lemma를 쓰지 않았고 코드도 고치지 않았다.**
- 성립: Lemma A는 대상 입력 전부에 적용된다(d > 0). N은 1.5배로 무한히 증가하고 P = N + 96, exp 차수도 P를 따른다. raw가 맞으면 VALID 전까지는 `not_separated`만 나온다. 운영 한도(budget·Limits·정수 문자열)는 모두 가용성이다.
- **구멍 H1:** raw m을 비신뢰 mpmath 추정이 한 번 고정한다. 틀리면 checker가 `raw_mismatch` → ANOMALY로 영구 정지한다(재시도 금지 원칙). 추정 수락 규칙은 틀린 m을 배제하지 못한다(mpmath 정확도 가정, 임의 dt_kick, prover 자신의 식 전사에 기댐). 건전성 결함이 아니라 **Liveness가 비신뢰 구성요소에 기대는 결함**이다.
- **구멍 H2:** 추정이 출력 범위 밖이면 정밀도를 더 올리지 않고 즉시 EXHAUSTED다. 운영 한도가 아니다.
- **빈칸 G1:** 승인된 Lemma B는 V1형 정확 유리수 enclosure(N, n)에 대한 것이다. V2의 outward 반올림(P)·`zero_floor`·부동소수 차수 선택으로의 확장은 증명 가능(스케치 작성)하지만 미작성·미감사다. 범위 공개: 출력 overflow 경계의 STOP은 certificate로 표현할 수 없고, D_valid의 \|J\| 상한 기록은 이번에 찾지 못했다.
- 설계자 판단 요청: D1(raw를 신뢰 enclosure로 정하고 추정은 시작 N 힌트로만: H1 제거, ANOMALY 의미 변경), D2(H2 제거), D3(G1 정식 lemma + 독립 감사), D4(overflow·\|J\| 상한 가정 명시).
- **④-Liveness NotCertified 유지.** A-EV 미해결, ④-Safety Conditional.
다음 판단(설계자): 완결성 감사 V0의 D1〜D4.

**설계자 판정(2026-09-30, 기준 HEAD `82358cd`): D1 승인, D2 승인, D3 진행(정식 lemma + 독립 감사), D4는 가정 대신 정확 상한 증명.** Exact Aggregate·작은 완전세계는 미래 방향으로 대기하고, 작업선은 C1-B1 그대로다.

**D1·D2·D4 처리, D3 작성(2026-09-30):** ([감사 8절](docs/active/C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md), [prover 설계 10절](docs/active/C1B1_POINT_PROVER_DESIGN_V0.md), [D3 lemma](docs/active/C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md))
- **prover V0.1(D1·D2):** mpmath 추정은 힌트(시작 N, 첫 raw)뿐이다. 힌트가 `raw_mismatch`이면 같은 N에서 checker V2의 `enclosure()`가 raw를 정하고 `check_certificate`가 최종 판정한다. 추정이 실패해도 멈추지 않고 N = 128부터 enclosure 경로를 탄다. **H1·H2 제거.** 신뢰 enclosure가 참값이 범위 밖임을 보이면 `EXHAUSTED("output_out_of_range")`(상태 분류는 설계자 확인 대기).
- **D4 성립:** R ∈ [r_min, 2^49 bohr] × dt_kick = 20에서 checker V2 구간 산술로 빈틈없는 덮개(적응형 분할, 2,802 구간) 위의 sup\|V′\| ≤ 63.87 → **\|J\| ≤ 1277.3 a.u. = FX(96,80) 경계 32768의 3.9%.** 참 최댓값은 r_min에서 약 58.7 a.u.(점 값). dt = 40에서 실행기가 판정하는 모든 충격량(D_valid 포함)에서 overflow 경계 STOP은 일어나지 않는다. **첫 실행은 균일 덮개의 과대추정 때문에 실패(\|J\| 상한 72108 = 경계의 2.2배)했고, 적응형 분할로 고쳤다. 실패 기록 보존.**
- **D3:** Lemma B-V2(반올림 P·zero_floor·차수 선택을 포함한 수렴)와 prover V0.1 완결성 조립 초안을 작성했다. **독립 감사 대기, 승인 아님.** 남는 가정 **H-float**(차수 선택이 부동소수, P가 2^50을 넘는 영역에서 엄밀성 없음). 권고 H-B(정확 정수 차수 선택, 판정 전 미구현).
- 검증: prover 시험 24 → 29, D4 시험 11, 관련 묶음 **465 passed + 1 xfailed**, **LOCAL FULL(prover = 기존 실행 코드) 3294 passed + 1 xfailed, skip 0, 실패 0, 556.32초.** D4 시험 11은 FULL 뒤에 추가된 새 파일이다. 증거: `runs/c1b1_prover_d1d2_20260930/`, `runs/c1b1_impulse_magnitude_bound_20260930/`.
- **완결성 정리는 아직 성립으로 쓰지 않는다**(D3 감사·H-float 전). **④-Liveness NotCertified**, A-EV 미해결(별도 작업선), ④-Safety Conditional.
다음 판단(설계자): `output_out_of_range` 상태 분류, H-float(H-A/H-B), D3 독립 감사자 지정.

**설계자 판정(2026-09-30, 기준 HEAD `b6baa94`→`99077a4`): D1·D2 유지, D4 승인(C1-B1 dt = 40·FX(96,48) 상대 위치 전체·R ≥ r_min 범위, A-EV 아님). `output_out_of_range` → 새 상태 UNREPRESENTABLE, dt = 40 runtime에서는 RuntimeContractViolation. H-B 승인, 단 fallback은 반복 없는 닫힌 부등식으로 인증. D3 독립 감사는 H-B 뒤, 작성자와 다른 계열(GPT-5.6 Sol High).** `99077a4`는 미검증 WIP였고(원격에도 있음) 그 위에 검증 커밋을 쌓는다.

**prover V0.2 + wrapper + D3 개정 1(2026-09-30):** ([prover 설계 11절](docs/active/C1B1_POINT_PROVER_DESIGN_V0.md), [감사 9절](docs/active/C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md), [D3 lemma](docs/active/C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md), [wrapper 10절](docs/active/C1B1_RUNTIME_WRAPPER_V0.md))
- **UNREPRESENTABLE**: 신뢰 enclosure가 참값이 출력 범위 밖임을 보인 경우. dt = 40이면 wrapper가 **RuntimeContractViolation**(run 불변, TERMINAL 아님), 다른 dt에서는 UNPROVED.
- **H-B**: 부동소수 차수는 힌트다. 힌트는 checker와 같은 정확 x에서 한쪽 반올림 사슬(정수 가수·지수 쌍, 단계당 일정 비용)로 인증한다. fallback n_fb는 **O(1) 정확 비교 두 개**로 인증하고, 그 비교가 상대 꼬리 조건을 함의함을 증명했다(CERT_BITS 비의존). order_max 초과는 무거운 계산 전에 거부한다. WIP의 hang 원인(`Fraction` 사슬의 거대 분모)을 고쳐 차수 200,000 인증이 0.19초다. 표본에서 힌트 9/9 인증, 속도 유지.
- **D3 개정 1**: H-float 가정 제거. 정성 완결성은 O(1) fallback 경로에만 기대고, 힌트 인증기에는 건전성(True ⇒ 성질)만 필요하다.
- 검증: prover 48, wrapper 45, 관련 묶음 **498 passed + 1 xfailed**, **LOCAL FULL 3327 passed + 1 xfailed, skip 0, 실패 0, exit 0, 575.86초**(D4 시험 11 포함). 증거: `runs/c1b1_prover_v02_hb_20260930/`.
- **완결성 정리는 초안이며 독립 감사 전이다. ④-Liveness NotCertified**, A-EV 미해결, ④-Safety Conditional. Exact Aggregate·작은 완전세계는 대기.
다음 판단(설계자): D3 lemma 개정 1 + prover V0.2의 독립 감사(GPT-5.6 Sol High, 인계 자료 `docs/active/C1B1_D3_AUDIT_HANDOFF_V0.md`).

**D3 독립 감사 1회차: 불통과(GPT-5.6 Sol High, 대상 `5f1a4c7`, 2026-09-30).** F2·F3·exp 폭 수렴·`_dv` 수렴·enclosure↔checker 동일 J·UNREPRESENTABLE/runtime은 성립, H-B fallback 부등식은 성립. **막는 구멍 1개:** 부동소수 힌트가 실제로는 필수 경로였다(`_certified_plan`이 fallback 전에 `_exp_plan`을 무조건 호출, 큰 P에서 `bits * LN2`가 `OverflowError`). **문구 1개:** "budget·Limits 무한"은 코드 계약이 아니다. 부수: fallback "O(1)"은 부정확. Git 정정: 이전 보고의 "`5f1a4c7`은 로컬에만 있고 push 안 함"은 틀렸다 — remote-tracking reflog에 `5f1a4c7` push 07:29:34, `449ee9b` push 08:02:47이 있다(누가 실행했는지는 기록에 없음).

**감사 반영(2026-09-30):** ([D3 lemma 개정 2](docs/active/C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md), [prover 설계 12절](docs/active/C1B1_POINT_PROVER_DESIGN_V0.md))
- `_hint_plan`: P > `HINT_WORK_BITS_MAX` = 2^16이면 부동소수 planner를 **호출하지 않고** 전부 fallback. 그 아래에서 planner의 `ArithmeticError`·`ValueError`도 "힌트 없음" → fallback. 상한은 힌트/fallback 선택만 바꾸고 판정·거부는 바꾸지 않는다(속도만). 함께 발견: 수정 전 planner의 `ValueError`는 `EXHAUSTED(serialization_limit)`로 잘못 분류됐고 `OverflowError`는 `prove()` 밖으로 나갔다(`5f1a4c7` 소스에 주입해 확인).
- lemma 개정 2: 정리를 "입력마다 충분히 큰 **유한** Budget·Limits가 존재"로 바꾸고 증명 0단계(한도 고르기), planner·추정의 종료 논증(4절 0, 4절 끝)을 추가. 지원 입력 전체의 공통 유한 한도는 주장하지 않는다. fallback은 "Taylor 차수 n에 비례하는 반복 없는 상수 개수 정확 비교"로 표현 정정.
- 검증: prover 시험 48 → 54(상한 위 planner 호출 0회, 상한 안 planner 실패 3종 → FOUND, 변이체 2종), 관련 묶음 247 passed, **LOCAL FULL 3333 passed + 1 xfailed, skip 0, 실패·error 0, exit 0, 608.92초**(junit tests 3334 / skipped 1 = strict xfail). 증거: `runs/c1b1_prover_v02_hint_bound_20260930/`. AGENTS.md 기준선 숫자(3289)는 설계자 판정 없이 갱신하지 않았다.
- **D3 lemma = 개정 2, 재감사 대기(승인 아님). ④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결.** H-B fallback 수학은 감사 통과, H-B 전체 liveness는 재감사 전 미완료.
다음 판단(설계자): D3 개정 2 재감사(`5f1a4c7` 이후 diff만, lemma 6절 8).

**D3 독립 감사 2회차: 통과(GPT-5.6 Sol High, 대상 개정 2 / `8c5c4f7`, 2026-09-30).** 전 항목 성립, 1회차 blocker 닫힘(P > 2^16에서 planner 호출 0회, 산술 예외는 fallback, planner 종료, 입력별 유한 한도 존재). 남은 지적은 인계 문서의 낡은 문구뿐이었고 고쳤다(docs only). 통과한 명제: 지원 C1-B1 rounding-decision 입력 하나를 고정하고 참 raw가 FX(96,80) 안이면, Lemma A와 checker V2 enclosure 건전성 아래에서 그 입력에 대해 충분히 큰 유한 Budget·Limits가 존재하며 prover V0.2는 유한 단계에서 checker V2 VALID를 찾는다(dt = 40에서는 D4가 범위 가정을 보장). **증거 등급: 독립 수학/코드 감사 통과, formal certified 아님.** 감사 기록: `docs/active/C1B1_D3_AUDIT_HANDOFF_V0.md` 6절.
- **상태(설계자 승인 전):** D3 lemma 개정 2 = 독립 감사 통과. Point Prover V0.2 정성 완결성 = 명시한 전제 아래 감사됨. **④-Liveness 전체 NotCertified 유지**(A-EV, inbound, inner, global shadowing, 전체 산란각, E_min 재생성 등 남음), ④-Safety Conditional, A-EV 미해결.
- Git 사실(remote-tracking reflog): `8c5c4f7` push 08:28:49. 이 구현자 세션은 push를 실행하지 않았고 누가 했는지는 기록에 없다. 직전 보고의 "push 안 함(로컬이 1개 앞섬)"은 커밋 직후 시점에는 맞았지만 그 뒤 push되어 현재 상태와 다르다.

**설계자 판정(2026-09-30, 기준 HEAD `4f81898`): D3 lemma 개정 2 = APPROVED. Point Prover V0.2 rounding-decision qualitative completeness = APPROVED under stated premises.** 증거 등급은 독립 수학·코드 감사 통과이며 formal certified가 아니다. **승인 범위(넓히지 않는다):** (1) 기본 운영 한도에서 항상 FOUND라는 뜻이 아니다 — 각 입력에 대해 충분히 큰 유한 한도가 존재한다는 정성 완결성이다. (2) Checker V2 자체의 formal proof를 새로 한 것이 아니다 — Lemma A와 Checker V2 enclosure soundness를 전제로 한다. (3) ④-Liveness 전체 승인이 아니다. 코드·시험 변경 없음(문서 상태만).
```
D3 lemma revision 2                       = APPROVED (independent math/code audit; NOT formal certified)
Point Prover V0.2 qualitative completeness = APPROVED under stated premises
④-Liveness = NotCertified
④-Safety = Conditional
A-EV = Unresolved
```
Git 사실: 원격 `master`는 `4f81898`(reflog push 08:37:27). 로컬과 같다.
다음: 새 증명·FULL 재실행이 아니라 ④의 다음 미해결 조각(A-EV는 별도 작업선, inbound, inner, global shadowing, 전체 산란각, E_min 재생성 등).

**설계자 지시(2026-09-30): 다음 작업 = C1-B1 inbound V0**(순서 inbound → inner → global shadowing → 전체 산란각 → E_min 재생성, native J는 별도 병렬 가능). 범위: 시간역전 lemma + 재사용 경계 + handoff 계약만.

**inbound V0(2026-09-30, 기준 HEAD `c3e0e3c`):** ([C1B1_INBOUND_V0.md](docs/active/C1B1_INBOUND_V0.md))
- **Lemma TR 고정:** T(운동량 부호 반전) 뒤 한 step은 정확히 T s0로 돌아오거나, drift **선분** guard에서만 거부된다(정확한 조건: segment_min_R2(q0 + d, v·h) < r_min², d는 drift 반올림 잔차, \|d_k\| ≤ 2^−48). 역방향이 묻는 충격량은 모두 순방향이 판정한 것이다(같은 STOP·Proof Cache witness). 코드 `a_reference/c1b1_time_reversal.py`(실행기 변경 0), 시험 7개: R ≈ 28.4 inbound D_valid(H) 산란 사건 3,600 step을 중간 상태까지 비트 단위로 역추적, 새 판정 질문 없음, r_min 한 칸 위 실제 반례(순방향 합법·역방향 거부, 예측 일치), D_valid의 T 비불변(F 상태의 T 상은 unsupported), 전제 거부, 결함 주입(floor drift).
- **전제 정정 공개:** 조사 문서 R2의 "④-2 귀납을 inbound에 공유"는 과장, 6.2의 "선분 guard도 대칭"은 틀림(둘 다 조사 문서에 정정 표기). "inbound"가 Runtime Contract V1에서는 R 20→최근접(안쪽) 뜻으로도 쓰였다. D_valid L·H는 출발 반지름·방향 제한이 없어 R > 20 inbound 상태(및 R ≈ 10 출발 상태)도 `numerical_validated`다.
- **판정 제안(설계자 판정 대기):** 바깥 inbound는 outgoing과 **같은 계약**(1-step 상한, 힘 envelope, shell 덮개, R_J zero-impulse, packet·실패 형식)으로 다룰 수 있다. **그러나 시간역전만으로는 아니다:** T는 순방향 inbound를 역방향 outgoing으로 보내므로 ④-2의 순방향 탈출 정리는 infall을 주지 않는다. 작은 **거울 귀납** 하나(w 상한, 불리한 drift 항)가 필요하다(유도만, 미구현·미감사). handoff 계약(입력·(Z) R ≥ R_J 격자 직선·(S) 거울 shell·출력 s_h ∈ R [20, 20+g)·실패 조건) 명세.
- 검증: 신규 파일만(모듈·시험·문서) → **LOCAL FULL 생략 / 관련 시험으로 대체 / 기존 실행 코드·공용 모듈·동결 계약·fixture 변경 없음.** 관련 7개 파일 **181 passed + 1 xfailed**(신규 7 포함).
- 상태 변화 없음: **④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결.**
다음 판단(설계자): inbound V0의 IN-1〜IN-4(문서 7절). 구현자 권고: inbound V1(거울 귀납 + (Z) 구간 + chain) → inner.

**설계자 판정(2026-09-30, 기준 HEAD `d58f8bd`): IN-1 승인(1-step bound·envelope·shell/packet·실패 의미 재사용, 정리 재사용 아님, mirror induction 필요), IN-2 inbound V1 먼저, IN-3 승인(선분 전체 R ≥ 20인 step만, handoff R ∈ [20, 20+g), w < 0), IN-4 실행기 변경 없이 기록 — outer inbound에서는 R ≥ 20이라는 기하학적 여유 때문에 무관하다. 전체 D_valid/inner에 대해 무관하다고 아직 일반화하지 않는다(반례는 E ≫ 10 De라는 것만 보였을 뿐 D_valid 궤도가 r_min 한 칸 위에 오지 않는다는 증명이 아니다).** 상세: [inbound V0 7.1절](docs/active/C1B1_INBOUND_V0.md).

**inbound V1(2026-09-30, 기준 HEAD `5861a15`):** ([C1B1_INBOUND_V1.md](docs/active/C1B1_INBOUND_V1.md))
- 구현: `a_reference/c1b1_inbound_outer.py`(새 파일). (Z) R ≥ R_J 정확 격자 직선(2차식 정수 해) + 거울 shell 귀납(4/5 고정 분할) + handoff packet R ∈ [20, 20+g), w < 0. shell별 cap·w 천장 < 0·g_in > 0·선분 R ≥ 20·overflow를 정확 유리수로 검사, 못 닫으면 NotCertified. outgoing·실행기 코드 변경 없음(재사용만).
- **공개:** V0 스케치(누적 w 천장)만으로는 P_cap > \|P\|가 가짜 전환 반경 ≈ R0·√(2(P_cap/\|P\| − 1))을 만들어 R_J에서 오는 구간이 닫히지 않았다. **각운동량 항등식 천장**(④-1 1-step L 상한 사용)을 더해 고쳤다(V0에 없던 성분, 판정 요청 V1-1). survey 첫 실행은 전역 force envelope(R = 20에서 약 1.9·10⁷ hartree)로 cap을 정해 무의미한 0-step "인증"이 나왔고(무효, 기록 보존, 이제 cap < \|P\| 거부), 둘째 실행은 cap 여유 부족으로 전부 실패(기록 보존).
- 시험 16개(기록 재검사 checker, 실제 실행기와의 일치 검사 — 증명 아님, (Z) 380 step 비트 일치, 거부 8종, 결함 주입 3종). survey_only 격자 72개 중 **46개 인증: E ≥ 0.1 De 45/45(R 20000 출발 포함), 0.01 De 1/9, ≤ 1e-4 De 0/18.** 스크래치 비교에서 기존 outgoing chain도 E = 1e-4 De(R 25, b 7)에서 실패. 증거 `runs/c1b1_inbound_v1_survey_20260930/`.
- **독립 감사 전 — mirror induction은 승인된 정리로 쓰지 않는다.** 저에너지 L 부분은 이 방법으로 NotCertified. ④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결 그대로.
- 검증: 신규 파일만 → **LOCAL FULL 생략 / 관련 시험으로 대체 / 기존 실행 코드·공용 모듈·동결 계약·fixture 변경 없음.**
다음 판단(설계자): inbound V1의 V1-1(L 천장 승인), V1-2(저에너지: 인력 부호 정밀화 / 에너지 기반 운동량 상한 / 보류하고 inner), V1-3(inner 전 독립 감사).

**Field Map 조사 v0(2026-09-30, survey_only, 코드 변경 0):** ([C1B1_FIELD_MAP_SURVEY_V0.md](docs/active/C1B1_FIELD_MAP_SURVEY_V0.md))
- **판정: 독립 Field Map 계층은 도입 불필요.** `derivatives`/`Shell`/`_covered_shell`이 이미 R 1차원 구간 지도다. 새로운 가치는 지도가 아니라 **쓰는 방법**에서 나왔다.
- 스크래치 측정(증명 아님, `runs/c1b1_field_map_survey_20260930/`): 힘 부호만 쓰면 저에너지 inbound 0/6, **셀별 V 범위 + 에너지 기반 운동량 상한은 6/6**(E 1e-8〜1e-2 De, 출발 R 25·200). 부호는 기존 5/4 셀로 R ≤ 48.8에서만 인증된다. **에너지 장벽 셸:** [5.32, 5.35] 셀 3개로 V > 12.69 De(V = 10 De는 R ≈ 5.505) → D_valid 에너지 궤적이 r_min 근처에 못 간다는 후보 근거(inner 에너지 예산이 선행).
- **inner 약점:** R = 3 셀 폭 1/8에서 V′ 구간 [−721, 602] vs 참 [−0.90, −0.76](감쇠 항 상쇄). [r_min, 20] 적응 부호 지도는 셀 4,000개 예산 초과. inner 전에 상쇄 없는 재정식화가 필요.
- 채택 후보(설계자 판단): 에너지 기반 운동량 상한(inbound·outgoing 공용), 에너지 장벽 셸 lemma, inner 도함수 재정식화. 상태 변화 없음.

**설계자 판정(2026-09-30, 기준 HEAD `ba46940`): Field Map 조사 성공 종료(새 계층 만들지 않음).** (1) 에너지 기반 운동량 상한 = **진행 승인**, inbound/outgoing 공용 설계(방법 채택 ≠ 정리 승인: 정식 유도 → 코드 → 결함 주입 → 독립 감사). (2) 에너지 장벽 셸 = **같이 진행 승인**, 독립 lemma. D_valid 전체 도달 불가 주장에는 에너지 오차와 step overshoot(한 step 최대 이동 < 장벽 두께)를 포함. (3) inner 도함수 재정식화 = **보류**(장벽으로 R ≲ 5.3이 제거되는지 먼저). 순서: ① 공용 Energy Bound → ② inbound/outgoing 적용 → ③ Energy Barrier lemma → ④ D_valid가 R ≈ 5.3 아래에 못 감을 증명 → ⑤ 독립 감사 → ⑥ inner 필요 영역 확정 → ⑦ 부족하면 그때 재정식화.

**Energy Bound v0(①〜③, 2026-09-30, 기준 HEAD `99a2eec`):** ([C1B1_ENERGY_BOUND_V0.md](docs/active/C1B1_ENERGY_BOUND_V0.md))
- 공용 `a_reference/c1b1_energy_bound.py`: E~ 범위(④-1 1-step 예산 합), 셀 V 범위 → 운동량 범위(kick 누적 없음, 에너지 금지 셀 판정), **에너지 장벽 셸 lemma**(장벽 안 V > 에너지 상한 **그리고** 한 step 최대 이동 < 두께, 두 전제는 호출자 몫으로 기록), R > 0 도함수 구간(outer bound 공식 그대로, guard만 없음, 구문 트리 동일 시험). inbound는 `energy=True` 모드(기본 경로 불변), outgoing은 새 모듈 `c1b1_outgoing_energy.py`(각운동량 항등식 q·P 바닥 포함). 기존 outgoing·outer bound·실행기 변경 없음.
- 결과(survey_only 격자 72개, 같은 cap 사다리): **inbound 46 → 72/72, outgoing v1 63 → energy 69/72**(energy는 v1 인증 상태를 잃지 않음). 남은 outgoing 3개는 출발 R 25의 극저에너지(1e-8 De b 7·14, 1e-4 De b 14). 장벽 [5.32, 5.35]: 셀 3개로 V ≥ 12.6897 De, \|P_h\| ≤ 20에서 한 step 0.022 < 0.03. 증거 `runs/c1b1_energy_bound_survey_20260930/`.
- **공개:** inbound V1 기록 필드 `relative_L_change_before_last_kick_exact`가 `steps * tuple`(튜플 반복)이던 결함을 고침(증명 논리 무관, 느린 상태에서 메모리 오류). 처음 넣은 outgoing 결함 주입 하나(loss 부호)는 10 De에서 loss가 0이라 무의미한 변이여서 바꿈.
- 시험: `test_c1b1_energy_bound.py` 21개 + inbound energy 3개(기록 재검사, 실행기 일치 검사, 결함 주입 4종). **④ D_valid가 R ≈ 5.3 아래에 못 감은 아직 증명하지 않음**(inner 궤적의 에너지 예산 필요). 독립 감사 전 — 방법 채택 ≠ 정리 승인. ④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결.
- 검증: 신규 모듈·시험·문서 + 이번 세션의 비공용 모듈(inbound, survey) 수정 → **LOCAL FULL 생략 / 관련 시험으로 대체 / 공용 실행 코드·동결 계약·fixture 변경 없음.**
다음(설계자 순서 ④): inner 궤적 에너지 예산으로 D_valid의 R ≳ 5.35 유지를 증명하는 설계. 또는 ⑤ 독립 감사를 먼저.

**설계자 판정(2026-09-30, 기준 HEAD `e2613cd`): ⑤ Energy Bound 독립 감사를 먼저 한다. ④를 바로 만들지 않는다.** 이유: ④ 전체가 Energy Bound에 기댄다. 감사는 시험 통과보다 수학 연결(E1 누적, E2 방향, P와 P_h 구분, 교집합·q·P 부호·셸 출구 귀납, 장벽의 V′² 항·실제 저장 이동·호출자 전제, R < 20 도함수의 수학적 유효성)을 본다. 통과하면 ④의 첫 목표는 하나다: **R ≥ 5.35를 유지할 만큼의 E~ 상한과 half-step 운동량 cap을 닫을 수 있는가**(R = 20 → 최근접 → 20 전체를 한 번에 만들지 않는다).
- 감사 인계 자료: [C1B1_ENERGY_BOUND_AUDIT_HANDOFF_V0.md](docs/active/C1B1_ENERGY_BOUND_AUDIT_HANDOFF_V0.md)(체크리스트 6항목 ↔ 코드 줄, 작성자 주장은 확인 대상으로 분리). 작성자는 감사자가 아니다.
다음: 설계자가 지정한 감사자의 Energy Bound 감사.

**Energy Bound v0 독립 감사 결과 → 설계자 판정(2026-09-30, 기준 HEAD `df58aa5`):** E1 modified-energy 누적 PASS, E2 energy → stored momentum PASS, stored P ↔ half-step P_h PASS, inbound `_mirror_shell` 내부 귀납 PASS, outgoing energy shell/composition PASS, Energy Barrier lemma PASS, R < 20 `radial_derivatives` PASS, **inbound `certify_inbound_outer()` 전체 FAIL** → Energy Bound v0 전체 정리는 아직 승인하지 않는다. ④ inner energy budget은 시작하지 않는다.
- FAIL 원인(수학이 아니라 조립 경계 하나): 시작 R ≥ R_J → zero leg가 q_e로 이동 → 큰 p_cap으로 A = 20 + g ≥ R_e라 셸 0개 → handoff 반지름이 zero leg **이전** r2를 사용. 감사 반례 q0 = (10240, 0, 0), P0 = (−1, 0, 0), p_cap = 10⁷: 실제 R_e ≈ 10239.9989인데 packet [10240, 10240].
- **수정:** `_handoff_radius`로 세 경로를 명시 분리(셸 있음 → 마지막 셸 출구 / zero leg만 → q_e의 정확한 노름 구간 / 둘 다 없음 → 시작 상태). E1〜E3·outgoing·장벽·p_cap 범위는 바꾸지 않았다.
- regression: 감사 반례 그대로(옛 조합을 원문 변이로 재현해 packet 밖임을 확인, 수정 후 q_e 포함·셸 0·zero leg 있음·20 ≤ lower·upper ≤ A·q·P < 0·실제 실행기가 그 상태에 도달해 packet 안), energy=False/True 둘 다, 네 경로(zero±, shell±) 행렬. inbound 시험 23 passed.
- 검증: 이번 세션의 비공용 모듈 한 함수 수정 → **LOCAL FULL 생략 / 관련 시험으로 대체.** 다음: 이 경계 경로 수정만 독립 재감사(귀납·에너지 수학은 건드리지 않음).

**설계자 판정(2026-10-01, 기준 HEAD `c6bb35c`): 경계 수정 독립 재감사 PASS → Energy Bound v0 APPROVED.** 승인 범위: E1 modified-energy 유한 누적, E2 energy → stored momentum, stored P ↔ half-step P_h, inbound outer energy induction/composition, outgoing outer energy induction/composition, Energy Barrier lemma, 현재 사용 범위의 R < 20 radial derivative enclosure. **inner·global scattering·④-Liveness·A-EV로 넓히지 않는다.**
**④ 시작(설계자 지시):** 유일한 목표 = inbound handoff 이후 R ≥ 5.35인 동안 장벽 lemma의 두 호출자 전제(모든 저장 상태 E~ ≤ E_hi, 모든 step \|P_h\| ≤ P_half_cap)를 귀납으로 유지할 수 있는가. 결과는 CLOSED / NOT CLOSED / BLOCKED 중 하나. R < 5.35 계산·R ≈ 3 재정식화·새 Field Map·executor/dt/D_valid 변경·장벽 이동·Energy Bound 수학 변경·A-EV 혼합 금지.

**④ 결과(2026-10-01): NOT CLOSED.** ([C1B1_INNER_CONFINEMENT_S4_V0.md](docs/active/C1B1_INNER_CONFINEMENT_S4_V0.md), 스크래치 `runs/c1b1_step4_confinement_20261001/`)
- 닫히는 고리: E2로 P_half_cap = 21.15(E_hi = 12.5 De, [5.32, 21]) → 한 step 0.0232 < 장벽 두께 0.03, 장벽 연결, 순환 없는 귀납 순서(cap은 E~_k에서만 → 1-step 정리 → E~_(k+1)).
- **실패하는 부등식:** E~_0,hi + N·dE ≤ E_hi. 1-step dE 최대 3.39·10⁻⁷ hartree(R ≈ 5.32 벽 셀, 거의 전부 이산화 항), 여유 1.13·10⁻³ → **N ≤ 3,332 step**(1/256 셀이면 7,395). inner 체류 step 수 상한이 없다. 원인: long residence 때문에 누적이 터짐 + 최악 셀 dE를 모든 step에 적용. 도함수 폭·P_h cap·장벽 두께는 원인이 아님.
- 관측 1건(증명 아님): E ≈ 4.4 De 사건의 R < 20 step 2,385, 그중 R < 7은 251. dE는 R 5.32 → 12에서 약 10⁵〜10⁶배 작아진다.
- 개선 후보(구현 안 함): (1) 위치별 예산 + 벽 영역(R < 7) 체류 step 상한(벽 영역은 힘이 바깥쪽이라 셸 귀납 가능성, 단 반복 근접 횟수는 못 묶음), (2) 유효 퍼텐셜 기반 inner 체류 상한(사실상 inner 산란 정리의 일부). 여유 늘리기·장벽 이동은 금지, 셀 세분만으로는 해결 안 됨.
다음 판단(설계자): 후보 1·2 중 어느 쪽으로, 또는 다른 방향.

**inner 국소 작용·사건 압축 조사 v0(2026-10-01, survey_only, 코드 변경 0):** ([C1B1_INNER_EVENT_SURVEY_V0.md](docs/active/C1B1_INNER_EVENT_SURVEY_V0.md), `runs/c1b1_inner_event_survey_20261001/`)
- **ROUTE B.** wall [5.35, 7]의 모든 1/64 셀에서 1-step Δw 하한 > 0(반발 kick). 방문 한 번(들어옴 → 전환 → 나감)의 에너지 상한은 [5.35, 6.0]에서 여유의 28%, [5.35, 6.6]에서 83%. R ≳ 7.1(우물·궤도 영역)은 저에너지에서 인력 때문에 국소 progress가 실제로 없다 → 별도 체류 상한(유효 퍼텐셜 + D_valid의 \|ρ\| 하한)과 wall 방문 횟수 상한이 필요.
- 위치별 1-step dE: [5.35, 7] ≤ 1.5·10⁻⁶, [7, 8] ≤ 9.1·10⁻⁹, [8, 12] ≤ 1.2·10⁻⁹, [12, 20] ≤ 9.0·10⁻¹². Σ N_i·dE_i 형식은 가능.
- **사건 압축: LIMITED.** 관측 85개 통과 전부 바깥으로 나가고 R_min ≥ 5.75, 실제 \|ΔE~\| ≤ 7.7·10⁻¹⁵ hartree/통과(인증 도구보다 10⁸배 이상 작음). 입력은 E, \|L\| 두 스칼라로 충분(+1 ulp 운동량은 17/17 출력 동일, 30° 회전 영향 ≤ 10⁻⁹). 궤도 경계에서 체류가 자릿수당 약 +4,200 step 로그 발산, 편향각 증폭 약 10⁴(ρ = 10⁻⁴). 사건 **인증**은 통과 전체를 묶는 증명 방법이 필요해 형식만으로는 이득이 없다.
- 공개: wall 첫 계산(v1)은 넓힌 셀 하나를 써서 잘못된 비관 결론(6.69부터 progress 없음, 방문당 에너지 21〜25배)을 냈다. 같은 해상도의 이웃 셀 극값(v2)으로 고쳤다. 둘 다 보존. 초안에서 E~ 단위(De)를 hartree로 잘못 읽은 것도 고쳤다.
다음 판단(설계자): wall 방문 lemma 정식화 + 우물/궤도 영역 유효 퍼텐셜 체류 상한 설계로 갈지.

**궤도 직접 계산 / Event Map 조사 v0(2026-10-01, survey_only, 코드 변경 0, 시작 HEAD `148cce7`):** ([C1B1_DIRECT_ORBIT_SURVEY_V0.md](docs/active/C1B1_DIRECT_ORBIT_SURVEY_V0.md), `runs/c1b1_direct_orbit_survey_20261001/`)
- **판정 HYBRID.** (E, L)로 연속 궤도를 직접 계산하면(V_eff 전환점 + Δθ·T 적분) 21개 사례(궤도 경계 ρ = ±10⁻⁴ 포함)에서 실행기와 R_min ≤ 2.2·10⁻⁵ bohr, 편향각 ≤ 5·10⁻⁶ rad(\|ρ\| ≥ 0.005) / ≤ 1.3·10⁻⁴(ρ = ±10⁻⁴), step 수 ±1 일치. Δθ 차이 ≤ 4.8·10⁻⁴는 주로 실행기 출구 넘침.
- 궤도 경계 = V_eff 꼭대기의 불안정 원궤도(R_b = 9.733), 한 바퀴당 증폭 A ≈ 3.4·10⁵. 예측 0.181(튕김)·0.362(두 번 넘음) 바퀴/자릿수, 관측 0.177〜0.180·0.363〜0.371. 경계 근처 체류는 반복 바퀴가 아니라 쌍곡 안장 통과라 N바퀴 묶기의 이득이 없다(D_valid 산란 ≤ 1.65바퀴).
- 실행기 L은 정확 보존이 아님: step당 ≤ 8.9·10⁻¹⁴, 통과당 ≤ 3.7·10⁻¹². 계산 절감은 측정 1〜15배(추정 최대 수십 배). certification에는 shadowing 교량 정리(경계에서 A배 증폭), 보존량 교량, 직접 적분의 엄밀화가 새로 필요.
- 다음 최소 후보: ④에 필요한 것은 R_min뿐이고 R_min은 가장 둔감한 출력 → **유효 퍼텐셜 전환점 하한 정리**(E ≤ E_hi, 인증된 \|L\| 범위, V 구간 → R_min ≥ r*).

**R_min-only 조사 v0(2026-10-01, 코드 변경 0, 시작 HEAD `80ede0c`): 판정 CIRCULAR.** ([C1B1_RMIN_ONLY_SURVEY_V0.md](docs/active/C1B1_RMIN_ONLY_SURVEY_V0.md))
- R_min ≥ 5.35는 승인된 장벽 lemma로 "모든 저장 상태 E~ ≤ E_hi" 하나로 줄어든다. L 불필요(금지 판정은 \|P\|² ≥ 0, 정면충돌이 최악. L은 장벽을 높일 뿐), 연속 H 교량 불필요(E2·장벽이 E~로 직접), 전환점 세 종류(반지름 정지·궤도 준정지·정면 완전 정지) 추가 처리 불필요(위치 + 에너지 배제 + 한 step < 두께만 사용).
- **순환:** 실행기에 정확한 에너지 불변량이 없고, E~ 전 구간 상한은 E~_0 + Σ dE(R_k)라 N이 다시 들어간다. 오래 머무는 것은 R이 아니라 에너지 전제에 영향을 준다. ④ v0와 같은 지점이며 유효 퍼텐셜은 L 항을 더할 뿐이다(L 하한도 N 의존, 다만 N ≲ 10¹³으로 약함, 정면충돌엔 무효).
- 남는 정보: Safety 조각에 필요한 N은 정확한 체류 시간이 아니라 거친 두 숫자(wall 방문 횟수, [7, 20] 구간별 체류 ≲ 10⁵〜10⁸ step)다. wall 방문 1회는 N 없이 닫힌다(ROUTE B). 같은 거친 체류 상한이 별도 Liveness(유한 시간 outbound)의 핵심 재료이기도 하다(두 명제는 분리 유지).
다음 판단(설계자): 거친 체류 상한(wall 방문 횟수 + [7, 20] 구간별 체류) 설계로 갈지.

**S4d Coarse Residence Bootstrap 조사 v0(2026-10-01, 코드 변경 0, 시작 HEAD `2b58882`): 판정 BOOTSTRAP-PARTIAL.** ([C1B1_S4D_COARSE_RESIDENCE_BOOTSTRAP_V0.md](docs/active/C1B1_S4D_COARSE_RESIDENCE_BOOTSTRAP_V0.md), `runs/c1b1_s4d_bootstrap_20261001/`)
- first-crossing 밴드 가설(E~·\|L\| 밴드, k < n*) → 장벽으로 R ≥ 5.35, E2 → 셀 분류(FORBIDDEN / GAP: \|w\| 하한으로 부호 고정·R 단조 / PROGRESS: Δw ≥ c > 0) + 원심 장벽 차단 → 셀 방문 ≤ 2 → Σ N_i·dE_i ≤ ΔE로 모순. **Liveness도 R ≥ 5.35도 가정하지 않음(순환 없음).** 연속 → 이산 bridge 불필요(이산 w-산술 직접).
- 대표 18개 중 **14개 닫힘**(정면, 일반, 큰 b, 높은 E, 10⁻⁸ De까지, 궤도 경계 튕기는 쪽 ρ = +0.005〜+0.1, ρ = −0.1). wall 방문 K ≤ 1은 유도됨(튕김은 K = 0). 에너지는 wall이 지배(10⁻⁶〜10⁻⁵), [7, 20]은 ≤ 10⁻⁷.
- **닫히지 않는 4개 = 궤도 경계의 넘는 쪽**(0.5 De ρ = −0.01, −0.005, 0.15 De ρ = −0.005, 1 De b = 10: H 아래 끝도 경계 근처): 인증 wall 예산 ≈ 10⁻⁵ > 분리선 여유 δ(ρ) ≈ 10⁻⁶〜10⁻⁵. 누적 드리프트가 나갈 때 꼭대기 통과를 막아 갇힘을 배제하지 못함(실제 실행기 드리프트 ≤ 7.7·10⁻¹⁵은 관측일 뿐).
- 공개: 1차 실행(1/32 셀, 벽 차단 없음)은 경계 사례가 모두 막혔다(보존). 2차 개선은 고정 규칙(전 사례 1/128)과 논리(벽 차단)에서 나왔다. 초안의 사례 수(19/15)를 18/14로 고쳤다.
- 필요한 새 lemma: 셀 분류 건전성, 한 번 돌기, **넘는 쪽 경계 lemma**(후보: wall 1-step 예산을 δ 아래로, 국소 안장 lemma, D_valid 넘는 쪽 \|ρ\| 하한의 δ 직접 비교).
다음 판단(설계자): D_valid 실제 넘는 쪽 최소 \|ρ\|와 H 아래 끝의 δ를 재서 wall 예산 부족분이 규칙 고정 세분 한 단계로 메워지는지 확인할지.

**Actual-Trajectory Post-Verification 조사 v0(2026-10-01, 코드 변경 0, 시작 HEAD `5c5d6f8`): 판정 POSTVERIFY-HYBRID.** ([C1B1_POSTVERIFY_SURVEY_V0.md](docs/active/C1B1_POSTVERIFY_SURVEY_V0.md), `runs/c1b1_postverify_survey_20261001/`)
- 수정 없는 executor로 임시 실행 → 코드 비공유 verifier(a_reference·a_numeric·engine·audit import 0, 상수 전사 + 동결 fingerprint 일치, mpmath 구간 + 자동미분 도함수)가 모든 step의 J 반올림·정확 전이·R ≥ 5.35(drift 선분)·R = 20 출구를 확인. **S4d 미해결 4개 포함 7개 사례 전부 VALID**, 모든 J 128 bit 결정, 새 lemma 0. 결함 주입 12/12 잡음(일관 위조 J, 잘린 witness, 틀린 verifier 모형 포함).
- **비용은 실행 1회분:** step마다 구간 평가 1회가 필요하고 J 확인과 J 계산은 같은 구간을 요구한다. 직렬 4.9〜5.8배(scratch 구현 상수), 6 작업자 병렬 wall-clock 0.98〜1.19배. 정확 산술 부분은 실행의 약 7%. 저장: 초기 상태 + J 약 22 B/step, streaming 인증서 약 4 KB(재검증 불가, W1 인증서와 동일).
- **사건 경계만 검증(중간 건너뛰기)은 정확 상태 확정에 불가:** 위치 1 raw 교란 → 출구 운동량 10⁹〜10¹³ ulp 차이. (운동량 1 ulp 교란은 위치 반올림에 흡수되어 출구까지 그대로 2 raw.)
- **E~(verifier 엄밀 구간, 폭 ≤ 6·10⁻³⁹):** 넘는 쪽 barrier 진입 → 재통과 ΔE~ = 3.1·10⁻¹⁴ / 1.7·10⁻¹⁴ / 4·10⁻¹⁶ hartree vs 수치 δ 6.5·10⁻⁶ / 3.3·10⁻⁶ / 9.8·10⁻⁷. 통과 중 wall에서 ±2.5·10⁻¹⁰ 오르내렸다 되돌아옴 — S4d 예산은 이 상쇄를 모르고 누적. 1 De b 10은 실제로 wall 미진입(R_min 7.07). **이 궤적들에 대해서만** 엄밀.
- HYBRID인 이유: 실행 전 Liveness·D_valid 전체 명제·R_J 이후 무한 tail은 사후 검증으로 얻지 못한다(끝나지 않으면 REFUSED). 신뢰 기반은 verifier 구현 + mpmath 엄밀성 + 사양 공통 모드(A-EV와 별개 질문, 섞지 않음).
다음 판단(설계자): ④의 목적이 "모든 허용 입력의 실행 전 보장"인지 "확정되는 모든 결과의 독립 검증"인지. 후자면 실제 궤적 부분은 사후 검증, formal은 tail과 REFUSED 빈도만 남는 구성 — 결정 전 추가 구현 없음.

**설계자 판정(2026-10-01, 기준 HEAD `ac14385`): A 세 층 분리 채택, C1-B1 종료 조건 재정의.** ([A_THREE_LAYER_SEPARATION_V1.md](docs/active/A_THREE_LAYER_SEPARATION_V1.md))
- 세계 / 검증 / 관측 분리. formal proof의 역할은 "다음 단계 허가증"에서 "필요한 성질을 검증하는 도구"로 바뀐다. 기존 증명 자산은 전부 보존한다.
- 증거 등급 4단계와 확정 상태 3단계를 분리한다. 표본 감사는 승격하지 않는다.
- **N-1** C1-B1 CONFIRMED 최소 = `REPLAY_VERIFIED`. 자격은 native J 등 특정 구현이 아니라 **설계자가 승인한 independent replay verifier**에 둔다(C1-B1 한정, C1-C 전 재평가, 측정 항목 고정). **공식 첫 비용은 승인된 production V1 CPU 약2.773배 / 4-worker batch wall 약2.537배**([승인 기록](docs/active/C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md)). 위 scratch 직렬4.9〜5.8배 / 병렬0.98〜1.19배는 역사적 feasibility 자료이며 공식 비용값이 아니다. scratch verifier와 승인 전 결과는 자동 승격하지 않는다. mpmath 구간 엄밀성은 신뢰 기반으로 공개한다.
- native J 비트 동등성은 **C1-B1 종료 조건에서 제외**하고 별도 이종 실행기 Gate로 유지한다. native J 경로를 실제 세계 실행에 사용하기 전에 통과해야 한다.
- **A-EV와 replay verifier는 서로 대체하지 않는다. A-EV는 세계 실행기의 판정 방법 자체에 대한 건전성 의무이고, replay verifier는 실제 생성된 세계 역사의 독립 재검증이다. 두 작업에서 같은 증명을 중복 요구하지 않는다.**
- O-3 자료 확보·봉인·관측 코드 준비는 지금 가능하다. 공식 O-3는 production verifier 승인 뒤 CONFIRMED trajectory만 사용한다. 개발 탐색 결과는 `EXECUTED / NOT OFFICIAL O-3`로 표시한다.
- **N-2** 불일치 시 자동 재실행 금지, 하드웨어 오류는 독립 근거 필요. **N-3** r_min 실행 guard는 Gate 유지, S4d passing-side δ는 연구 과제로 이동. **N-4** C1-B1 O-3 = Ar-Ar 직접 산란 `O-3 weak`(착수 전 자료·수치화·E-QC·성공 기준 봉인), 희박 Ar 점성은 다원자 기체 단계로 이동. **N-5** 문서 먼저, 코드는 계약 확정 뒤.
- 위 사후 검증 조사의 "다음 판단(설계자)" 질문(④의 목적)은 이 판정으로 답해졌다: 확정되는 결과의 독립 검증이 Gate이고, 모든 허용 입력의 사전 보장은 연구 과제다.
- 채택 근거는 S4d 결과와 무관한 R1〜R4로 한정했다. S4d는 실패로도 닫힘으로도 판정하지 않는다.
- 기존 O-3 조사 추정: 충돌 빈도 가중 ∝ x e⁻ˣ를 적용하면 300 K에서 약 5%, 400 K에서 약 13%가 현재 10 De 범위를 넘는다(온도 모델 추정, 실제 세계 운영 실측 아님). 다원자 기체 단계 전 에너지 범위 확장이 필요하다.
- 검증: **LOCAL FULL 생략 / 관련 시험으로 대체 / 이유: 문서만 변경, 기존 실행 코드·동결 계약·fixture 변경 없음.** `tests/test_body_contract_freeze.py` 3 passed(이번 실행), 제13·26조 원문 유지 비교·문서 링크 검사·`git diff --check` 확인. 기존 LOCAL FULL 기준선 숫자는 갱신하지 않음.

**설계자 판정(2026-10-01): L 최상위 원칙과 헌법 v0.3 개정.** ([L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md](docs/reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md), [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md))
- L은 생명을 만들지 않는다. 현실적 초기 화학 조건에서 A를 실행하고 관측한다. 아무것도 발생하지 않는 결과도 유효하다.
- 헌법 제5·6·7·8·18·22조 의미 수정, 제21조 "가능성 차단(실패) ≠ 미발생(유효한 결과)" 명시, 제13조 원문·헌법 제목 유지, 목적·제4조 해석 메모. 제21조 예시는 해석 메모로 이동하고 검증된 유효모델의 정당한 경로 제외는 실패가 아님을 명시한다. 개정 전 v0.2는 `ac14385`에 보존.
- 유효 모델의 희귀 경로 계약: 제외 경로 목록 + 경로별 상한 + 선언 범위 전체의 누적 기여·예상 사건 수 상한.
- `EVOLUTION_V2_PLAN.md`·`EVOLVABLE_LANGUAGE_PLAN.md`는 L의 근거 문서가 아니다(레거시, 보존). 레거시·동결 확률 세계 코드는 개정 이전 기준선으로 보존하고 수정하지 않는다.

**작업선 분리(설계자 지시 2026-09-30):** A-C1B1 Core(wrapper·Proof Cache·rounding-decision completeness·④-Liveness)는 이 저장소의 현재 작업선에서 계속한다. **A-EV independent evaluator audit는 별도 병렬 작업선(worktree/branch `a-ev-audit`, `audit/independent_physics/` 중심)에서 진행될 예정이며 이 작업선에서는 구현하지 않는다.** 그 작업이 끝났다는 기록은 없다 — A-EV는 계속 미해결이고 ④-Safety Conditional을 승격하지 않는다. Proof Cache와 A-EV는 하나의 증명으로 섞지 않으며, 두 작업선이 합쳐지기 전에는 evidence level을 따로 유지한다.

**아직 남음 (Gate):** A-EV / O-1(독립 수치 V1에서 불일치 STOP, 전체 통과 아님) / O-3 weak(직접 산란) / C1-B1 전체 freeze. `_decide` 예외 분류·제한된 소스 결합 재감사, production independent replay verifier 구현·승인 및 증거 등급·확정 계약 최소 시험은 완료. 시험 history는 공식 O-3나 운영 세계 역사로 자동 재사용하지 않는다.
**별도 Gate:** native J evaluator와 실행기 비트 동등성(이종 실행기, CONFIRMED 전제 아님).
**연구 과제 (Gate 아님, 보존):** inbound 저에너지 잔여 / inner(④ step 4) / S4d passing-side δ / global shadowing / 전체 산란각 formal proof / E_min 재생성 / 속박 궤도 domain·error proof / 정확 분수 대리식 fast path survey.
무한시간 균일 L 상한과 무한 FX 실행도 인증 범위가 아니다. 이번 문서 정리에서 E_min을 재생성하거나 새로운 물리 규칙을 추가하지 않는다.

## 증거 종류: 수치 검증과 별도 수학 증거

| 증거 | 현재 표현 | 적용 범위 |
|---|---|---|
| **D_valid evidence** | **`numerical_validated` / `unsupported`** | 동결 규약이 식별하는 초기 상태의 수치 검증 범위 |
| **별도 수학 증거** | **analytic outer certificate** | 명시한 전제 아래 outgoing shell·유한 체류·tail에 관한 해석적 증거. 정밀도 완전성 등 남은 조건은 위 표를 따른다 |

**둘 사이 자동 승격이나 자동 연결은 없다.** Outer certificate가 생겨도 D_valid나 `run.validation`이 `formal_certified`로 바뀌지 않는다.
동결 D_valid 코드에는 `formal_certified`라는 수준 이름이 남아 있지만 현재 그 수준을 반환하는 상태는 없다. 이것은 analytic outer certificate의 존재 여부와 별개다.

D_valid v2는 설계자 판정 `0898ca3`(대상 구현 `a8619c8`)으로 동결했다. 단일 canonical 생성기 → 실제 경계 측정 → 기준 fixture → 초기 상태 식별이 연결되며,
7 에너지 × 2쪽의 181개 측정 상태가 식별 상태와 일치한다. 기준 fixture는 `a_reference/fixtures/c1b1_orbit_boundary_v3.json`, 계약은 `c1b1-dvalid-v2`다.
계약상 `numerical_validated`에는 이 fixture 에너지들 외에 capture band가 없는 두 넓은 영역도 포함된다. L은 b_orb > 2Re인 저에너지(약 0.1418 De 미만), H는 장벽 꼭대기 위(약 0.9974 De 초과)이며 둘 다 모든 b와 임의 배치를 받는다([Liveness 조사 v0](docs/active/C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 2.1절).
미측정 에너지 보간·외삽, 가장 바깥 탐침 밖 인정, 다른 profile로의 확대는 하지 않는다. 같은 에너지·같은 쪽의 탐침 사이는 단조 띠 모형에 근거하며 연속 구간 전체의 증명은 아니다.
`unsupported`는 운동 계산을 바꾸거나 막지 않는다. 동결 대상의 재측정은 새 결함 또는 다음 물리 단계의 필요가 생길 때만 별도 판단하며 이번에는 변경하지 않는다.

## 구현 자산과 정직한 한계

| 자산 | 현재 읽는 방식 |
|---|---|
| 결정론 A 환경·보존·CPU/GPU field | 기존 구현·검증 자산. 현재 v6 실제 물질 계산 기반과 같은 완성 단계로 묶지 않는다 |
| causal v5 | 이름·순서에 무관한 생성·성장·병합 및 사슬 31개 검증. 정사각형 기하·회전 없는 2D 충돌 한계가 있다 |
| A-MICRO v6 | 변형 가능한 실제 물질 기반을 향한 별도 계통. 현재 활성 작업은 C1-B1 |
| C1-A | Lang 2024 Ar–Ar 퍼텐셜·해석적 힘·한 번 반올림·출처·fixture 비트 동결. 직렬 CPU·병렬 CPU·CUDA 함수 계약이며 다입자 세계 실행기 아님 |
| B-classic·초기 B 도구 | 수작업 규칙 모델·비교군/연구 자산 보존. 학습형 B 없음. 본격 개발은 후기 단계 |
| B 인간 신체 계약 | 문서 동결, 구현 미착수. 동결 계약 보존 |
| L | 자연 발생·복사·진화의 새 증거 없음. 촉매·주형·반응 화학·다입자 응집·3체는 아직 남음 |
| 확률 세계·레거시 | 동결된 비교 기준선과 과거 연구 자료. 새 결정론 증거와 합산하지 않음 |

고전 Ar 모델의 물리적 한계, 반올림, 시간 이산화 오차를 구분한다. CPU/GPU 비트 일치나 시험 통과가 현실 물리 정확도 전체를 증명하지 않는다.
Physics IR/DSL·다중 해상도·계산/메모리/재생 구조는 요구사항·제안이며 구현·동결로 읽지 않는다.
네이티브 실행의 600초 하드 타임아웃과 별개로 컴파일 빌드 타임아웃은 미완 인프라 과제다. 원격 자원의 현재 가동·비용은 이 대시보드에서 주장하지 않는다.

## 검증 기록

아래는 실행별 기록이다. 문서 정리 재검증과 과거 구현 당시의 결과를 구분하며, 시험 통과를 새 물리 증거나 ④ 완료로 해석하지 않는다.

| 실행 기록 | 결과 | 로그·JUnit |
|---|---|---|
| ④-4c-10 shell 16 인증서 LOCAL FULL (2026-09-28, `0117cd8`) | **2834 passed + 1 strict xfailed, failure/error 0, skip 0, 398.68초**. REMOTE LINUX FULL 재실행 2834 passed, 361.87초, 항목별 동일(첫 원격 실행 간헐적 실패 1건은 재현 안 됨) | `runs/c1b1_hard_case_certificate_shell16_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_shell16_20260928/local_full.xml` |
| ④-4c-8 shell 17 인증서 LOCAL FULL (2026-09-28, `8d45209`) | **2815 passed + 1 strict xfailed, failure/error 0, skip 0, 408.27초**. REMOTE LINUX FULL 같은 커밋 2815 passed + 1 xfailed, skip 0, 356.36초, 항목별 동일 | `runs/c1b1_hard_case_certificate_shell17_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_shell17_20260928/local_full.xml` |
| ④-4c-7 shell 17 조사 + native 리눅스 빌드 LOCAL FULL (2026-09-28, `91a5c38`) | **2807 passed + 1 strict xfailed, failure/error 0, skip 0, 405.49초**. 원격 전체(`894cf5e`)는 skip 0·2806 passed·1 failed(줄바꿈 해시, 이후 수정) | `runs/c1b1_hard_case_shell17_20260928/local_full.log`, `runs/c1b1_hard_case_shell17_20260928/local_full.xml` |
| ④-4c-6 shell 18 hard-case 인증서 LOCAL FULL (2026-09-28) | **2798 passed + 1 strict xfailed, failure/error 0, skip 0, 448.71초**, 로그에 경고 줄 없음(원인 미조사). 신규 관련 74개 직렬/병렬 동일 | `runs/c1b1_hard_case_certificate_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_20260928/local_full.xml` |
| ④-4c-5 shell 18 hard-case search survey LOCAL FULL (2026-09-28) | **2764 passed + 1 strict xfailed, failure/error 0, skip 0, 455.87초**, 요약에 경고 줄 없음(원인 미조사). 신규 40개 직렬/병렬 동일 | `runs/c1b1_hard_case_20260928/local_full.log`, `runs/c1b1_hard_case_20260928/local_full.xml` |
| ④-4c-4 same-input 최소 구현 LOCAL FULL (2026-09-28) | **2724 passed + 1 strict xfailed, failure/error 0, skip 0, 453.76초**, cp949 경고 25건. 신규 38개 직렬/병렬 동일 | `runs/c1b1_same_input_20260928/local_full.log`, `runs/c1b1_same_input_20260928/local_full.xml` |
| ④-4c-3 normalized quotient-gap survey LOCAL FULL (2026-09-28) | **2686 passed + 1 strict xfailed, failure/error 0, skip 0, 433.59초**, cp949 경고 25건. 신규 34개 직렬/병렬 동일 | `runs/c1b1_quotient_gap_20260928/local_full.log`, `runs/c1b1_quotient_gap_20260928/local_full.xml` |
| ④-4c-2 full residue-class survey LOCAL FULL (2026-09-28) | **2652 passed + 1 strict xfailed, failure/error 0, skip 0, 425.76초**, cp949 경고 25건. 신규 27개 직렬/병렬 동일 | `runs/c1b1_residue_class_20260928/local_full.log`, `runs/c1b1_residue_class_20260928/local_full.xml` |
| ④-4c-1 modular-distance survey LOCAL FULL (2026-09-28) | **2625 passed + 1 strict xfailed, failure/error 0, skip 0, 383.44초**, cp949 경고 25건. 신규 32개 직렬/병렬 동일 | `runs/c1b1_modular_distance_20260928/local_full.log`, `runs/c1b1_modular_distance_20260928/local_full.xml` |
| ④-4b boundary 역상 배제 최종 LOCAL FULL (2026-09-27) | **2502 passed + 1 strict xfailed, failure/error 0, skip 0, 405.59초**, cp949 경고 27건. 신규 31개 시험 | `runs/c1b1_boundary_exclusion_20260927/local_full_final.log`, `runs/c1b1_boundary_exclusion_20260927/local_full_final.xml` |
| ④-4b 미해결 진단 LOCAL FULL (2026-09-27) | **2430 passed + 1 strict xfailed, failure/error 0, skip 0, 362.74초**, cp949 경고 25건. 진단 시험 17개 | `runs/c1b1_unresolved_diagnosis_20260927/local_full.log`, `runs/c1b1_unresolved_diagnosis_20260927/local_full.xml` |
| 폴더 정리 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 454.67초**, cp949 경고 25건 | `runs/documentation_folder_cleanup_20260927/local_full.log`, `runs/documentation_folder_cleanup_20260927/local_full.xml` |
| 내용 정리 당시 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 395.50초**, cp949 경고 25건 | `runs/documentation_cleanup_20260927_local_full.log`, `runs/documentation_cleanup_20260927_local_full.xml` |
| ④-4 구현 당시 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 388.84초**, cp949 경고 25건 | `runs/c1b1_rounding_decision_local_full_v1.*` |
| ④-1 당시 LOCAL FULL | 2335 passed + 1 strict xfailed, failure 0, skip 0, 447.41초, cp949 경고 25건 | `runs/c1b1_outer_bound_local_full.*` |
| ④-2/④-3 당시 REMOTE PYTHON FULL | 2258 passed + 108 skipped + 1 strict xfailed, failure 0, 71.23초 | `runs/c1b1_outer_bootstrap_full_v1.*` |
| Codex 인수인계 당시 LOCAL FULL (`0898ca3`) | 2307 passed + 1 strict xfailed, failure 0, skip 0, 445.58초, 인코딩 경고 24건 | `runs/project_review_20260927/local_full.*` |

`LOCAL FULL`은 로컬 Python + native CPU/CUDA + Windows/외부 참조 시험이다. `REMOTE PYTHON FULL`의 skip을 통과로 세지 않으며 두 범위를 합치지 않는다.
표준 검증 명령과 기준선 정본은 [AGENTS.md](AGENTS.md)를 본다. 컴파일러 출력 인코딩 경고가 남아 있으므로 경고 없는 실행으로 보고하지 않는다.

## 현재 문서 진입점과 역사 기록

문서는 [상태별 폴더 안내](docs/README.md)·[전체 분류/이동 경로표](docs/DOCUMENT_STATUS_INDEX.md)로 찾는다. `active`는 현재 C1-B1, `frozen`은 지켜야 할 계약, `history`는 과거 기록, `deferred`는 후기 B 자산이다. `docs/current`는 옛 경로 안내용이며 신체 계약 원문만 경로 고정 때문에 남아 있다.

- [C1-B1 설계·결정·검증 기록](docs/active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md): **23절 D_valid 동결, 24절 ④-1, 25절 ④-2/④-3, 26절 rounding-decision 진행**을 함께 읽는다.
- [④-4 rounding-decision 상태](docs/active/C1B1_ROUNDING_DECISION_V1.md): tail 증거와 미완 pre-tail cover의 상세. **23절만을 최신 결정으로 읽지 않는다.**
- [저장소 지도](REPO_MAP.md): 구현 위치와 계통 구분.
- [인수인계 점검](docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md): 현재 보충 안내와 `0898ca3` 당시 점검·시험 이력을 구분.
- [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md): 문서 정리 전 대시보드 원문, 과거 번호 체계·진행 순서·갈림길·B 연구·실험·기술 부채·최근 이력 전체. 본문 속 “다음”은 당시 기록이다.

A/B/L 역할과 불변조건은 [RULES.md](RULES.md)·[PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md)를 따른다.
Git은 2026-09-21 초기화했고 이전 상태는 `D:\KiroCrewTraceVault\success-is-mother-of-failure\project-snapshots\20260921_090715_pre_git_init\`에 봉인했다.


**Production independent replay verifier V1 구현 기록(2026-10-01): 아래는 승인 전 구현·검증 당시 기록. 지정 fingerprint 조합은 후속 설계자 승인 완료, 신규 증거는 [승인 기록](docs/active/C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md).**
([계약·전체 결과·비용·신뢰 기반](docs/active/C1B1_PRODUCTION_REPLAY_VERIFIER_V1.md))

- Git 시작 HEAD/origin/master `ac143855bec21352aaa86241b31baf86d6075eae`, 기존 13개 문서만 `c85beb5`에 별도 commit한 뒤 clean tree에서 신규 `c1b1_replay/` 구현. push 없음. 기존 executor·물리·D_valid·동결 fixture 변경 0.
- 초기 상태+매 J+무손실 state residual의 witness V1. 매 step의 독립 interval AD J enclosure/반올림, exact kick/drift/overflow/unrounded r_min guard, 12 raw equality를 검증. 금지 import 4계통 모두 0(AST+별도 프로세스+실측 worker).
- 기존 scratch 7개는 등급 없는 입력으로만 사용. 같은 raw 입력으로 reference executor를 새로 실행해 매 상태/J 동일함 확인. 새 production 검증은 7/7 VALID, 총 79,087 step, J 평가 79,094회 모두 128 bit. stream/full의 verdict·마지막 raw·원본 hash·구현/의존성 fingerprint도 7/7 동일. scratch 등급 자동 승격 0.
- 같은 4-worker 배치: executor CPU 109.625s / wall 40.952s, stream verifier CPU 304.016s / wall 103.905s. CPU 비율 2.773, 병렬 batch wall 비율 2.537. per-step 병렬화나 단일 executor 대비 수치가 아님. witness 1,757,342 B(22.220 B/step); summary는 재검증 원본 아님. stream worker peak 28.18〜29.95 MiB, 50ms 샘플 aggregate RSS peak 145.64 MiB.
- 원 scratch 12행(결함11+control1) 모두 유지+AD 미분 결함 추가: 결함12종 기대 판정 일치(11 INVALID, 출구 전 종료 REFUSED). resource/precision cap REFUSED, prefix/root/보존 증거 binding, 승인 없는 VALID 미확정, INVALID 자손 폐기·마지막 CONFIRMED 유지, 자동 재실행 금지를 영구 시험. 실제 세계 commit 0, TEST ONLY approval로 최소 history 성질만 검증.
- 관련 60 passed 5.25s. **이번 LOCAL FULL: 3433 passed + 1 strict xfailed, 실제 skip 0, failure/error 0, exit 0, 736.56s**(junit3434/skipped1=xfail). 신규 replay 시험49, 기존 코드 순증95로 공식 3289보다144 증가. 공식 AGENTS 기준선은 설계자 판정 대기로 그대로 유지. 기존 native subprocess cp949 경고25건 남음, 원인 미조사·해결 아님.
- 신뢰 기반: mpmath1.3.0 pure-Python interval enclosure 및 Python 정수/Fraction 의미. spec/implementation/dependency fingerprint에 approval을 결합하며 승인 candidate decision은 빈 값이다. 아직 REPLAY_VERIFIED/CONFIRMED 공식 역사 0. whole-future/형식 인증/many-body/live pipe/운영 rollback은 얻지 않았다.
- **남은 Gate:** 설계자 verifier 승인, A-EV, `_decide` 예외 분류, O-1/O-3 weak 및 C1-B1 전체 freeze. native J 별도 Gate, 공식 O-3 실행 없음. Energy Bound v0 APPROVED / ④-Liveness NotCertified / ④-Safety Conditional / A-EV unresolved 유지.
- 증거: `runs/c1b1_production_replay_20261001/`의 `.c1br` 원본·source manifest·stream/full 결과·CPU/메모리 batch·local_full.log/xml·49개 회귀 결과. 원본 없이 summary만으로 재검증 불가. 당시 다음 최소 작업이었던 fingerprint와 계약/신뢰 가정의 설계자 승인은 완료됐다. 승인 전 결과 파일은 역사적 실행 기록으로 유지한다.

**Production V1 승인·시험 history 봉인(2026-10-01):** commit `8996aa60`의 potential/replay spec/implementation/dependency fingerprint 조합 및 mpmath1.3.0 pure-Python·Python int/Fraction trust를 설계자가 REPLAY_VERIFIED용으로 승인했다. [approval manifest](docs/active/C1B1_REPLAY_VERIFIER_PRODUCTION_APPROVAL_V1.json), [7개 trusted test origin](docs/active/c1b1_trusted_test_origins_v1/index.json), [새 history 증거](docs/active/C1B1_REPLAY_VERIFIER_APPROVED_TEST_HISTORIES_V1.json), [상세 기록](docs/active/C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md).

- 보존 witness 7개를 승인 후 새로 재검증했고 origin 봉인 뒤 기존 History gate로 다시 전 step 검증했다. **7/7 VALID, 총79,087 step, 각각 REPLAY_VERIFIED / CONFIRMED test history**, INVALID/REFUSED 0. 시작12 raw/start_step와 승인 origin이 정확히 일치. 승인 전 결과 개명·자동 승격0, 7개를 하나의 세계 역사로 연결하지 않음.
- origin은 **PIPELINE_TEST_ONLY**. 정확한 초기 raw·E/b/rho·spec·초기 admission·재구성·hash·설계자 승인 봉인. 7개 모두 E_rel≤10De/r_min/raw 범위 통과. 공식 O-3·장기 운영 origin/세계 history로 자동 재사용 금지, D_valid 전체 인증/CERTIFIED 아님. verifier 승인만으로 origin을 자동 신뢰하지 않음.
- **N-1 공식 첫 비용 CPU약2.773배 / 4-worker batch wall약2.537배**. scratch 약1배 wall은 공식 비용값 아님. 이번 새 History 실행 CPU287.9375s / batch wall104.518s는 승인 재검증 실행 시간이며 공식 비용값 대체 아님.
- 이번 관련60 passed5.11s, import 위반0. 기존 verifier/executor/물리/계약/fixture 수정0. **LOCAL FULL 생략 / 관련 시험으로 대체**(문서·manifest·신규 증거 및 Git 밖 실행 script만, 기준선 미갱신). 모든 원본 `.c1br` 보존, summary만으로 재검증 불가. push 없음.
- Energy Bound v0 APPROVED, ④-Liveness NotCertified, ④-Safety Conditional, A-EV 미해결 유지. unknown-length live pipe·장기 rollback·native J·공식 O-3·새 물리/아키텍처 작업 없음.
