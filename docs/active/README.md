# 현재 활성 A — C1-B1

**상태: ACTIVE / C1-B1 / outer formal bound ④ 진행.** A가 최우선이며 L·B의 진행 시점은 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.

| 문서 | 현재 읽을 범위 |
|---|---|
| [C1-B1 설계·결정·검증](A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) | 23절 D_valid v2 동결, 24절 ④-1, 25절 ④-2/④-3, 26절 rounding 진행. 1~22절은 설계·측정 이력 |
| [원인별 outer 1-step bound](C1B1_OUTER_FORMAL_BOUND_V1.md) | ④-1 구현 완료. 유한 shell·half-step 운동량 cap 아래의 조건부 상한 |
| [outgoing bootstrap와 tail](C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md) | ④-2 shell induction·유한 체류 상한과 ④-3 R_J·zero discrete impulse·analytic continuous tail 구현. rounding completeness에 조건부 |
| [rounding-decision completeness](C1B1_ROUNDING_DECISION_V1.md) | tail 결정성은 최대 512 bit로 닫음. 일반 pre-tail reachable enclosure의 비영 impulse cover는 미완료 |
| [reachable coordinate·direction 제약](C1B1_REACHABLE_GEOMETRY_V1.md) | ④-4b 귀납적 projection 축소와 frozen 181개 probe replay. Completeness 전체는 미완료 |
| [64-cell 미해결 원인 진단](C1B1_ROUNDING_DIAGNOSIS_V1.md) | 76개 기록 전부 분류. 현재 projection에 최소 65 uniform leaf 필요, ④-4b NotCertified 유지 |
| [multi-output 결정성 계약·결과](C1B1_MULTI_OUTPUT_DECISION_V1.md) | 65점 한 region·256 bit 인증, 29개 그룹 단조성 증명, 마지막 전체 축 구간 인증. 27개 그룹 margin 미증명, 전체 NotCertified |
| [half-ulp boundary 역상 배제](C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md) | 후속 27개 domain 측정·3개 전체 인증. 51개 경계→후보 3개, 24개 family 의무 남음. 6/64 region·gap 89, 전체 NotCertified |
| [fractional phase 식 구조 조사](C1B1_FRACTIONAL_PHASE_SURVEY_V1.md) | 남은 24개 정규형·signed residual·modular tie 조사. 간격 충분조건 5개, rational tie 24개 배제(유한 예외 1점 포함). survey_only, 새 region 0개 |
| [rational spacing family 인증](C1B1_RATIONAL_SPACING_FAMILY_V1.md) | 별도 checker·proof-object 변조 검사 후 shell 19〜23 전체 인증. coverage 11/64 region·gap 84, 큰 family 19개와 전체 NotCertified 유지 |
| [19-domain exact modular-distance 조사](C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md) | 2,679점 exact Δ·약분·인수별 residue·generalized CRT. 4+1+14로 조사 분리, shell 15〜18 표본 후보. 전체 하한 미증명·coverage 유지 |
| [shell 15〜18 full residue-class 조사](C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md) | 전체 격자 class cover·정확 normalized polynomial·고정 CRT period. 14,271 class 중 8,730 가변 gap 미해결, 새 shell lemma/인증 0 |
| [정규화 gap·가변 divisor·quotient 조사](C1B1_NORMALIZED_QUOTIENT_GAP_SURVEY_V1.md) | ceil(M/g)·D² remainder identity·홀수 quotient 조건. 작은 654 class 하한 추가, 큰 8,076 class 미해결. 새 shell lemma/인증 0·11/64·gap 84 유지 |
| [같은 입력 correlation 단계 계획](C1B1_SAME_INPUT_CORRELATION_PLAN_V1.md) | ④-4c-4의 설계. 최소 구현 결과는 아래 조사에 기록하며 큰 class 수학 의무는 미완료 |
| [같은 입력 gap 필터·별도 checker 조사](C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md) | 기존 미해결 8,076 class 전부 root 검사. 작은 241 class·2,980 입력 추가 확인, 7,835 미해결. 실제 큰 class symbolic 하한 0·새 region 0. 이후 h 합동 lemma 방향은 보류 |
| [shell 18 hard-case 탐색 조사](C1B1_HARD_CASE_SEARCH_SURVEY_V1.md) | 블록 보간 + 엄밀 오차로 T=G+δ 유도. affine 부적합, quadratic L=2^34 전체 실행: 교차 1,568,498·후보 109·hazard 0, checker 1024/1024. survey_only, 다른 shell 미적용 |
| [shell 15 hard-case 전수 조사 (마지막)](C1B1_HARD_CASE_SEARCH_SHELL15_SURVEY_V1.md) | shell별 전수 hard-case 탐색의 마지막 조사. 교차 250,139,754·후보 54,419·hazard 0. shell 14 이하로 이 방식을 이어가지 않는다(STOP) |
| [shell 16 hard-case 인증서](C1B1_HARD_CASE_CERTIFICATE_SHELL16_V1.md) | ④-4c-10: shell 17과 같은 계약으로 shell 16 인증. 후보 6,581·hazard 0. fresh coverage 14/64·gap 81, shell 15는 미승인 |
| [shell 16 hard-case 전수 조사](C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md) | ④-4c-9: survey_only. 교차 46,892,493·후보 6,581·hazard 0, checker 1024/1024, 같은 기계 shell 17 기준선. 후보 밀도 1.47배(휴리스틱 추종) — 설계자 판단 사항 |
| [shell 17 hard-case 인증서](C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md) | ④-4c-8: shell 18과 같은 계약으로 shell 17 인증. 후보 827·hazard 0, 단계별 비용 실측(원격 32스레드). fresh coverage 13/64·gap 82, 전체 NotCertified |
| [shell 17 hard-case 확장성 조사](C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md) | ④-4c-7: shell 17 단독 실측. 교차 8,645,949·후보 827·hazard 0, checker 1024/1024. checker 비용이 교차 수에 비례해 커짐. survey_only |
| [실행 기반 정밀도 조사](C1B1_RUNTIME_STRESS_SURVEY_V1.md) | survey_only. 실제 궤적 판정 약 2.3억 회: R ≤ 320에서 256 bit 0.6%대, R ≥ 640에서 100%, 512+ 0. 256 비율 = 128-bit 구간 폭 |
| [Fail-Closed v0 + 국소 witness prototype](C1B1_RUNTIME_FAIL_CLOSED_V0.md) | 거부된 step의 run 불변을 시험으로 고정. cap 128 강제 정지→재판정→검증→재실행이 3궤적 매 step 정상 실행과 동일. prototype |
| [Runtime Rounding Contract V1](C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) | **구조 승인(2026-09-29). P1a·D3 채택(A-EV = Safety 선행조건). ④-Liveness 대상 D_valid, NotCertified.** RESOLVED/STOPPED/WITNESS_RESOLVED/UNPROVED, ④-Safety/④-Liveness 분리, Proof Cache/Hazard Atlas. 코드 변경 근거 아님 |
| [④-Liveness(D_valid) 경로 조사 v0](C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) | survey_only·문서만. **D_valid 모양 정정(L·H 넓은 영역 + F 14구간)**, 기존 14 region은 +x축 전용이라 F와 겹침 0. 정량 경로 없음, 전역 exact tie 배제(Lindemann–Weierstrass) + 엄밀 구간 prover의 정성 경로 후보. Q1〜Q4 판정 완료 |
| [반올림 Liveness Lemma A·B 감사 v0](C1B1_ROUNDING_LIVENESS_LEMMAS_AB_AUDIT_V0.md) | 구현자 감사(인증 아님). **A: QED short-2 단일 계수로 전역 no-tie 통과. B: 독립 exact-rational certificate 수렴·검사 가능, 구현 전(식 전사 충실도가 주 위험).** Liveness = 정성적 finite termination(계약 변경). **A 승인, B 표현 정정 뒤 방향 승인 — accepted design basis, not frozen certificate** |
| [exact impulse certificate·독립 checker 사양 V1](C1B1_EXACT_IMPULSE_CERTIFICATE_SPEC_V1.md) | S1〜S4 승인, **checker 신뢰 승인(`e9b30eb`)**. 매개변수만 담는 certificate, 표준 라이브러리 전용 checker(VALID/INVALID/REFUSED), 지문 binding, `full`/`zero_floor` exp 모드. **독립 checker 구현 완료(8절): 시험 185개, 교차검증 14,102건 불일치 0, 식 결함 주입 40종 전부 잡힘, 초대형 정수 문자열은 REFUSED(8.5).** Operational limits affect availability, never truth |
| [point prover generator 설계 V0](C1B1_POINT_PROVER_DESIGN_V0.md) | **V0 구현 완료.** 비신뢰 생성기, 최종 권한은 checker V2 VALID 하나. FOUND/NOT_A_DECISION/EXHAUSTED/ANOMALY. 시험 24, 표본 2,660건 첫 시도 100%, cap-128 rehearsal 실제 궤적 3개 682 성분 전부 해결, **2^-17000 합성 STOP을 위·아래 모두 스스로 raw를 찾아 FOUND.** **승인**(비신뢰 generator). runtime wrapper·Proof Cache와 연결됨 |
| [runtime wrapper V0](C1B1_RUNTIME_WRAPPER_V0.md) | 실제 STOP → prover → 바이트 재검증 → 같은 step 재실행. 계약 W1〜W8, 시험 42(결함 주입 포함), cap-128 rehearsal 궤적 3개 매 step 비트 동일, **실제 cap 16384 STOP(합성 2^-17000)을 한 step 안에서 WITNESS_RESOLVED.** **승인**(구조·동작, profile identity binding). `Config.cache`로 Proof Cache V0와 연결 |
| [Proof Cache ↔ Warehouse 관계 V0](C1B1_PROOF_CACHE_WAREHOUSE_RELATION_V0.md) | 검토(문서만). 두 저장소를 만들지 않는다: Proof Cache = 실행 경로 안의 witness 선반, Warehouse = 밖의 색인(계약 D6). Cache가 따를 Warehouse 규칙 R1〜R7, 불일치 5개, 설계자 확인 Q-PC1〜4 |
| [Proof Cache V0](C1B1_PROOF_CACHE_V0.md) | 검증된 witness 선반: 하나의 append-only 선반, hit도 wrapper의 전체 재검증(checker 생략 없음), STALE/REJECTED/REFUSED 구분, 입고는 wrapper 밖 admission 층. 시험 42 + 관련 묶음(VAST) 529 passed. **APPROVED**(LOCAL FULL 3289 passed, production cap 종단 입고 1건 통과). 로그 무결성 ≠ 물리 correctness 한계 명시 |
| [Point Prover 완결성 감사 V0](C1B1_POINT_PROVER_COMPLETENESS_AUDIT_V0.md) | 분류 B → 설계자 판정 D1·D2 승인·D3 진행·D4 정확 상한. **prover V0.1로 H1·H2 제거**(추정은 힌트, raw는 신뢰 enclosure가 결정). **D4 성립: \|J\| ≤ 1277.3 a.u.(경계의 3.9%).** LOCAL FULL 3294 passed. ④-Liveness NotCertified |
| [Checker V2 수렴 lemma V0 (D3)](C1B1_CHECKER_V2_CONVERGENCE_LEMMA_V0.md) | Lemma B의 V2 확장(반올림 P·zero_floor·차수 선택) + prover V0.1 완결성 조립 초안. **독립 감사 대기, 승인 아님.** 남는 가정 H-float(부동소수 차수 선택), 권고 H-B |
| [checker V2 — outward dyadic rounding](C1B1_EXACT_IMPULSE_CHECKER_V2_DESIGN.md) | V1 보존(변경 0), 별도 모듈. 끝점 바깥쪽 dyadic 반올림으로 정수 크기를 work_bits에 묶음. 시험 95, 결함 주입 50종 전부 잡힘, 교차검증 14,102건 불일치 0, N=2048에서 800배. **실행기 cap 16384가 멈춘 2^-17000 합성 사례를 142〜147초에 VALID.** **신뢰 checker 승인**(설계자 판정 2026-09-29, formal certified 아님) |
| [shell 18 hard-case 인증서](C1B1_HARD_CASE_CERTIFICATE_V1.md) | ④-4c-6: 위 조사를 인증 계약·proof object로 승격. 전체 재계산 verify, 후보 109·hazard 0. shell 18 원래 domain Certified, fresh coverage 12/64·gap 83, 전체 NotCertified |

**④ 전체는 FROZEN이 아니고 ⑤는 아직 시작하지 않았다.** 미래의 필요한 impulse가 `MAX_PRECISION_BITS=16384` 안에서 항상 결정되는지는 미증명이다.
다음 Gate는 **④-Safety(A-EV 선행) + ④-Liveness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증**이다(Runtime Rounding Contract V1).
inbound / inner / global shadowing / 전체 산란각 / E_min 재생성 / 속박 궤도 / native J / C1-B1 전체 freeze도 남아 있다.

[동결 안내](../frozen/README.md)와 [공통 참조](../reference/README.md)를 함께 확인한다. D_valid의 수치 검증 범위와 analytic outer certificate는 별도이며 자동 승격·연결이 없다.
C0 수치 후보와 Ar 퍼텐셜 선정 이유는 [역사 기록](../history/README.md)에 보존한다. 파일 이름이 과거 시점이어도 현재 계약을 설명하는 근거로 참고할 수 있으며, 현재 Gate를 대신하지 않는다.
