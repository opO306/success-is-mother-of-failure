# 프로젝트 문서 안내

[H₂ R=.4 symmetric JC B1 V1](active/h2_r04_jc_v1/REPORT.md):
세nested기저·분리수치보정·최저근검증 및NMAXspots지원, SMALL부터 .001 target MET.
전체목표확보79.55s vsfreshV5Z33.30s로 전체wall우위미지원, NOT_CERTIFIED/production미승인/STOP.
JCasy intended rootUNRESOLVED·이전anomalies보존. 아래 V1이하 R=.4미착수는 당시 범위 기록이다.


[H₂ stored-matrix lowest-root audit V1](active/h2_stored_root_v1/REPORT.md):
저장 finite H/S 독립 interval 감사. 두 예제 lowest 확인, JC asymmetric non-lowest 반박,
H–He⁺ S 정확 음의방향, General240자리SPD미확정. 전체 UNRESOLVED/STOP,
NMAX/물리 적분 미판정/R=.4/B2미착수/NOT_CERTIFIED/production미승인.

[H₂ internal convergence audit V0](active/h2_internal_convergence_v0/REPORT.md):
Vendor/AUDIT 출력·WF불변5/5, 실제 수렴 종료5/5, exit0/ierror0 MAXIT mutant 소진 탐지.
독립 residual160자리 MEASURED/acceptance미승인, root/integral미확인, R=.4/B2미착수/STOP.

[H₂ vendor build 재개 V2](active/h2_vendor_build_resume_v2/REPORT.md):
README static build성공/배포5예제 출력byte동일5/5. 원본불변, default make 실패보존.
Native convergence미출력→guard qualification UNRESOLVED. R=.4/B2 미착수, STOP/NOT_CERTIFIED.


[H₂ H2SOLV / 독립 JC 이중 감사 재개](active/h2_representation_pilot1_resume_v1/REPORT.md):
제공 archive hashPASS, source 부분 검토, 첫 default build MPFR 링크 실패로 STOP.
Vendor example/R04계산0, B2미구현, NOT_CERTIFIED / production미승인.
아래 source미확보 feasibility는 당시 역사 기록이며 bytes를 보존했다.


[H₂ Representation Comparison Pilot 1](active/h2_representation_pilot1/REPORT.md)는
기존 QZ 감사와 분리된 explicit-r12 후보 feasibility 조사다.
배포/제한 라이선스 확인, source 접근 세 경로 실패 뒤 B 구현·계산 전 STOP.
FEASIBILITY_UNRESOLVED / COST_NOT_COMPARABLE / NOT_CERTIFIED / production 미승인.
과거 QZ/V5Z 원본 hash를 확인했으며 이번 numerical run은 없다.

[H₂ R=0.4 Same-Basis Independent Reconstruction V0](active/H2_R04_SAME_BASIS_INDEPENDENT_RECONSTRUCTION_V0.md)는
설계자 보완 계약을 먼저 봉인한 실제 두-arm 실행이다. 같은 AO60/singlet1830, 자체 C,
113-bit direct 경로의 mandatory guards는 accepted2. 그러나 L–I1.12513e-9>기존1e-9로
동등성 미통과. Common representation/state-weighted AO 영향·독립 narrow AO spots를 보존한다.
전체 AO/energy bounds 미확보, UNRESOLVED / NOT CERTIFIED / QZ44 FAIL / production 미승인 / STOP.

[H₂ R=0.4 Open-Hypothesis Adversarial Audit V0](active/H2_R04_OPEN_HYPOTHESIS_ADVERSARIAL_AUDIT_V0.md)는
설계자 추가 승인 뒤 실제 spatial symmetry, BSE coefficient span, cardinal one-points,
Libint2 independentAO/directMO connected experiment를 기록한다. Cardinal approach는 강한 조건부 증거;
strict inversion·uncontracted/native refusals·reference uncertainty·MO residual은 미해결이다.
이전 보고서/실패 보존 / QZ44 FAIL / NOT CERTIFIED / production 미승인.
아래 front-end 보고서의 D–G 미실행/STOP는 당시 단계의 기록이다.

[H₂ R=0.4 Front-End / Reference Cause Separation V0](active/H2_R04_FRONTEND_REFERENCE_CAUSE_SEPARATION_V0.md)는
Pachucki 원문 표 재전사와 BO 물리량 계약, Sims–Hagstrom 독립 source 교차검증을 기록한다.
수치는9.586e-13 차이지만 R=.4 reported uncertainty가 없어 REFERENCE_SIDE_UNRESOLVED.
Reference 오류 확정 아님; basis/AO/변환/새 energy 미실행, 기존 QZ44 FAIL/NOT CERTIFIED 유지.
DESIGNER DECISION REQUIRED, production 미승인.

[H₂ R=0.4 Ground-State Independent Validation V0](active/H2_R04_GROUND_STATE_INDEPENDENT_VALIDATION_V0.md)는
누락된 direct vector의 sealed replay/bitwise energy 재현, full1830 independent SC action,
힌트 없는 full-spectrum 최저 energy 일치를 기록한다. CI ground-state 계층 SUPPORTED;
같은 MO를 공유하므로 AO/MO/finite-basis 원인 UNRESOLVED, QZ44 FAIL/NOT CERTIFIED 유지.
수치 연구 STOP / DESIGNER DECISION REQUIRED, production 승인 아님.

[H₂ R=0.4 CI-Layer Micro-Audit V0](active/H2_R04_CI_LAYER_MICRO_AUDIT_V0.md)는
original direct-pair와 독립 Slater–Condon의 검사 범위 일치, 이전 determinant action의
단일 반례를 보존한다. h1e 흡수 뒤 fourfold packing 정보 손실을 분리했고 첫 mismatch에서
다른 벡터·eigen/energy 비교를 중단했다. 기존 QZ44 FAIL·physical UNRESOLVED·NOT CERTIFIED 유지.

[H₂ QZ Failure Cause Separation V0](active/H2_QZ_FAILURE_CAUSE_SEPARATION_V0.md)는
R=0.5 guard 평가 오류를 exact residual enclosure로 분리했다. adaptive prototype만 구현,
R=0.4 독립 CI reference 후보는 invalid, 네 short-R 원인은 UNRESOLVED다.
3회 실패 중단 규칙에 따라 추가 numerical 실행 중단 / DESIGNER DECISION REQUIRED.
기존 QZ44 FAIL·source·기준은 보존하며 production에 통합하지 않는다.

[H₂ sealed QZ44 fresh validation V1](active/H2_STATIC_QZ44_SEALED_VALIDATION_V1.md)은
V0 최종 source/config/rule을 봉인한 44점 전체 재실행이다. 43 accepted / 1 refused,
reference 0.001 hartree 초과 4점으로 Gate NUMERICAL FAIL. 실패점 진단·control 일치·
MO ERI UNRESOLVED를 함께 기록하며 계산법 조정이나 production 승인은 하지 않는다.

[H₂ High-Precision AO Micro-Pilot V0](active/H2_HIGH_PRECISION_AO_MICRO_PILOT_V0.md)는
독립 AO spot-check와 같은 basis의 canonical integral reuse로 네 점 guard 통과 및
R=1.4 sampled local minimum bracket을 기록한다. 전체44점/정확성 상한/인증은 별도 미해결이다.
초기 대표 규칙 구현 불일치는 보존하며 최종 B_v1/C_v1만 판정에 사용한다.

[고정 핵 H₂ static reference pilot](active/H2_STATIC_REFERENCE_PILOT_V1.md)은
2026-10-02의 독립 numerical research다. DZ/TZ 표본 minimum·해리 방향 및 부분
external comparison, QZ short-R refusal/최소점 미해결을 함께 기록한다.
NOT CERTIFIED / foundation 미승인, 기존 C1-B1 Gate 상태와 구별한다.
[같은 basis의 수치 원인 분리 후속](active/H2_NUMERICAL_CAUSE_ISOLATION_V1.md)은
16점 실패 재현·AO/변환 오차 분리와 fresh QZ 34/44를 기록한다. 전체 곡선·최소점은 미해결이다.

**현재 상태 정본:** [CURRENT_STATE.md](../CURRENT_STATE.md). **구현 위치:** [REPO_MAP.md](../REPO_MAP.md).
A가 최우선이다. L은 A의 물리 기반이 충분해진 뒤 자연 발생·진화 계통으로 진행한다. B 본격 개발은 A·L 기반의 작은 세계가 돌아가는 후기 단계로 보류하며 취소·폐기하지 않는다.

## 폴더로 문서 상태를 구분한다

| 폴더 | 의미 | 읽는 기준 |
|---|---|---|
| [active/](active/README.md) | 현재 활성 A / C1-B1 | 세 층 분리 기준 C1-B1 종료 조건. ④ 사전 증명은 연구 과제, 공식 ⑤ 미착수 |
| [frozen/](frozen/README.md) | 동결 계약 및 동결 자산의 원문 안내 | 동결은 “낡아서 버린 문서”가 아니라 현재 지켜야 할 버전별 계약 |
| [reference/](reference/README.md) | 공통 원칙·실행 구조·검증 기준 | 본문의 승인·초안·보류 범위를 유지. 폴더 배치로 새 승인하지 않음 |
| [history/](history/README.md) | 과거 설계·철회·실측·점검 기록 | 본문 속 “현재/다음”은 당시 상태. 이 폴더의 문서가 모두 동결됐다는 뜻은 아님 |
| [deferred/](deferred/README.md) | 후기 B 연구 자산과 B-classic 관련 설계 | 보존·비교·후기 연구용. B 취소나 폐기 아님 |
| [proposals/](proposals/README.md) | 아직 구현·동결하지 않은 장기 제안 | 현재 Gate의 승인·완료 근거로 사용하지 않음 |
| [legacy-probabilistic/](legacy-probabilistic/README.md) | 동결된 확률 세계 기준선·실패 기록 | 새 결정론 세계의 증거와 합산하지 않음 |
| [legacy-society-brain/](legacy-society-brain/README.md) | 이전 사회·원시인·뇌 계통 자료 | 현재 활성 구현 대상 아님 |
| [current/](current/README.md) | 옛 경로 호환 안내와 경로 고정 원문 | 현재 작업 문서 폴더로 읽지 않음. 코드·시험의 기존 경로 보존용 |

[전체 분류·이동 경로표](DOCUMENT_STATUS_INDEX.md)에서 파일별 원문 위치를 찾을 수 있다.
폴더 이름만으로 판정을 올리지 않는다. **FROZEN / 승인 / 구현 / 수치 검증 / 초안 / 역사**는 서로 다른 상태다.

## 현재 읽는 순서

1. 루트의 [AGENTS.md](../AGENTS.md)·[RULES.md](../RULES.md)·[CURRENT_STATE.md](../CURRENT_STATE.md).
2. [active 안내](active/README.md)에서 C1-B1 설계 23·24·25·26절과 rounding-decision 상태를 함께 확인.
3. [동결 안내](frozen/README.md)에서 C1-A와 D_valid v2의 동결 범위를 확인.
4. 필요한 공통 원칙은 reference, 과거 판단의 이유는 history, 후기 B 자산은 deferred에서 찾는다.

D_valid evidence는 `numerical_validated` / `unsupported`다. 별도 analytic outer certificate와 자동 승격·연결하지 않는다.

O-1 독립 수치 재현 V1은 [불일치 STOP 보고서](active/C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md)를 본다.
AGREE 8 / DISAGREE 1 / UNRESOLVED 0이며 O-1 전체 통과가 아니다. O-3는 착수하지 않았다.
후속 [단일 불일치 원인 격리 진단](active/C1B1_O1_CAUSE_ISOLATION_V1.md)은 HP-KDK40과 production A의 차이를 별도로 조사한다. 기존 O-1 STOP 판정을 유지하며 production 계약을 변경하지 않는다.
[outer dt40 적분기 최초 실패 기록](active/C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md)은 두 후보 준비 후 Vast 제어 실패 3회로 중단했던 단계다. 당시 후보 궤적은 미실행이었다.
[SSH 정보 제공 후 재개 기록](active/C1B1_DT40_INTEGRATOR_BENCHMARK_SSH_RESUME_V1.md)은 직접 SSH/전송 성공 및 Linux reference alias 사전 검사 실패를 보존한다. 당시 수치 실험은 미실행이었다.
[플랫폼 독립 배포 재개](active/C1B1_DT40_PORTABLE_DEPLOYMENT_V1.md)는 `code/`·`reference/` 상대 배치, 원본 272개 보존과 별도 실행 봉인, 실제 복원된 코드의 사전 검사 및 원격 수치 결과를 기록한다. 앞선 실패 기록을 대체하지 않는다.
현재 수치 비교는 완료됐고 Yoshida 9-input 관측/정밀도 PASS, Chin 비용 탈락이다. 측정한 kernel은 두 후보 모두 더 비싸며 전체 실행 비용 질문은 C로 남긴다. [전체 결과](active/C1B1_DT40_PORTABLE_RESULTS_V2.json).
[KDK20/Yoshida40 동일 노드 전체 비용](active/C1B1_KDK20_YOSHIDA40_COST_V1.md)은 공통 성능 하네스와 로컬 복원 검사를 준비했으나, 원격 SCP 연결 실패로 C / INCONCLUSIVE STOP했다. 성능 실행 0회, 모든 노드 종료 확인. 이전 수치 결과는 유지한다.

[KDK20/Yoshida40 로컬 전체 비용 최종 비교](active/C1B1_KDK20_YOSHIDA40_COST_LOCAL_V1.md)는 사용자 로컬 지시로 26 궤적을 완료했다. 양쪽 기존 9-input 관측 기준 PASS지만 Yoshida CPU/wall 합계 1.396210/1.449380배로 B / YOSHIDA_ACCURATE_BUT_COSTLIER. 관련 시험 70 passed, LOCAL FULL 생략. 로컬 부하 미통제·panel 1회·production 미채택·기존 O-1 STOP 유지, 이전 원격 실패 기록 보존.

[Yoshida40 후보 상태](active/C1B1_YOSHIDA40_CANDIDATE_STATUS_V1.md)는 VALIDATED NUMERICAL CANDIDATE / NOT PRODUCTION / NOT FORMALLY CERTIFIED로 보존한다. implemented / numerically validated on sealed C1-B1 O-1 panel / cost benchmarked locally 수준이다. 더 엄격한 관측 오차 또는 KDK timestep 축소 비용 증가 시 재검토하며, negative internal stage 위험·기존 O-1 STOP·모든 실패 기록을 유지한다.

## 보존 및 경로 예외

58개 문서를 실제로 분류 폴더로 이동했고, 코드·도구·규칙이 참조하던 옛 경로에는 원문으로 연결하는 짧은 안내를 남겼다. 계약이나 설계 본문을 두 군데 복사해 관리하지 않는다.
신체 계약의 원문은 시험이 경로와 1~8절 해시를 직접 고정하므로 [기존 위치](current/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)에 유지한다. [frozen의 신체 계약 안내](frozen/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)에서 바로 연결된다.
`docs/README/`와 `docs/중간 결과/`는 옛 경로 안내용이다. 실제 문서는 deferred/b-design 및 history로 이동했다.
LLM_HANDOFF의 JSON manifest는 생성 당시의 스냅샷이며 이번에 재생성하지 않았다. 현재 원문은 이 안내와 분류표를 기준으로 읽는다.
