# 문서 분류와 이동 경로표 — 2026-09-27

현재 상태는 [CURRENT_STATE.md](../CURRENT_STATE.md), 읽는 순서는 [문서 안내](README.md)를 본다.
**58개 원문을 실제 이동했다.** 폴더 분류는 새 물리 규칙·승인·동결 판정이 아니다.
동결·역사·초안·후기 자산은 서로 다른 상태다. 코드·fixture·D_valid·시험 의미는 변경하지 않는다.

## 현재 활성 A / C1-B1

| 실제 원문 | 이전 위치 |
|---|---|
| [A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md](active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md) | docs/current/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md |
| [C1B1_PRODUCTION_REPLAY_VERIFIER_V1.md](active/C1B1_PRODUCTION_REPLAY_VERIFIER_V1.md) | 신규(2026-10-01). production verifier 계약·구현. 8996aa60 지정 fingerprint 조합 설계자 승인 완료 |
| [C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md](active/C1B1_REPLAY_VERIFIER_APPROVAL_RECORD_V1.md) | 신규(2026-10-01). production 승인 manifest·재검증·독립 시험 origin 기록. 원본 witness 보존 필수 |
| [C1B1_DECIDE_EXCEPTION_CLASSIFICATION_V1.md](active/C1B1_DECIDE_EXCEPTION_CLASSIFICATION_V1.md) | 신규(2026-10-01). 분류 정리 완료. 초기 STOP·실패와 후속 해결 기록 |
| [C1B1_SOURCE_BINDING_REAUDIT_V1.md](active/C1B1_SOURCE_BINDING_REAUDIT_V1.md) | 신규(2026-10-01). 이번 예외 변경에 한정한 의미 대조·11개 증거 재생성·소스 결합 감사 완료. LOCAL FULL 통과, A-EV 전체 미해결 유지 |
| [C1B1_O1_PROTOCOL_V1.md](active/C1B1_O1_PROTOCOL_V1.md) | 신규(2026-10-01). 실행 전 입력·오차 배분·판정·STOP 봉인. 결과 뒤 변경 금지 |
| [C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md](active/C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md) | 신규(2026-10-01). AGREE 8 / DISAGREE 1 / UNRESOLVED 0 / 미실행 1, 불일치 STOP. O-1 전체 통과 아님 |
| [C1B1_O1_CAUSE_ISOLATION_PROTOCOL_V1.md](active/C1B1_O1_CAUSE_ISOLATION_PROTOCOL_V1.md) | 신규(2026-10-01). 단일 raw HP-KDK40 원인 분리·조건부 dt 축소 기준의 실행 전 봉인 |
| [C1B1_O1_CAUSE_ISOLATION_V1.md](active/C1B1_O1_CAUSE_ISOLATION_V1.md) | 신규(2026-10-01). 독립 HP-KDK numerical diagnostic. production 계약·기존 O-1 STOP·unsupported 범위 유지 |
| [C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md](active/C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md) | 신규(2026-10-01). 두 후보·outer dt40·정확도/비용/원격 기준 사전 봉인 |
| [C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md](active/C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md) | 신규(2026-10-01). Vast 제어 시도 3회 실패, 궤적 미실행. C: 아직 판정 불가. 후보 성능/production 채택 판정 없음 |
| [A_THREE_LAYER_SEPARATION_V1.md](active/A_THREE_LAYER_SEPARATION_V1.md) | 신규(2026-10-01). 세 층 분리·증거 등급·C1-B1 종료 조건 재정의 |
| [C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md](active/C1B1_O3_SCATTERING_VS_VISCOSITY_SURVEY_V0.md) | 신규(2026-10-01). O-3 대상 조사, 직접 산란 O-3 weak 채택 |
| [C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md](active/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md) | docs/current/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md |
| [C1B1_OUTER_FORMAL_BOUND_V1.md](active/C1B1_OUTER_FORMAL_BOUND_V1.md) | docs/current/C1B1_OUTER_FORMAL_BOUND_V1.md |
| [C1B1_ROUNDING_DECISION_V1.md](active/C1B1_ROUNDING_DECISION_V1.md) | docs/current/C1B1_ROUNDING_DECISION_V1.md |
| [C1B1_REACHABLE_GEOMETRY_V1.md](active/C1B1_REACHABLE_GEOMETRY_V1.md) | ④-4b 신규 귀납 제약·frozen replay 기록 |
| [C1B1_ROUNDING_DIAGNOSIS_V1.md](active/C1B1_ROUNDING_DIAGNOSIS_V1.md) | ④-4b 미해결 76개 기록 분류·64-cell uniform cover 한계 |
| [C1B1_MULTI_OUTPUT_DECISION_V1.md](active/C1B1_MULTI_OUTPUT_DECISION_V1.md) | multi-output region 계약·65점 수용 사례·29개 그룹 분석·남은 margin 의무 |
| [C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md](active/C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md) | boundary 역상 배제 계약·27개 domain 측정·3개 추가 인증·24개 family 미증명 |
| [C1B1_FRACTIONAL_PHASE_SURVEY_V1.md](active/C1B1_FRACTIONAL_PHASE_SURVEY_V1.md) | 남은 24개 정확 식·signed residual·간격/tie 구조 조사, 새 인증 계약은 미구현 |
| [C1B1_RATIONAL_SPACING_FAMILY_V1.md](active/C1B1_RATIONAL_SPACING_FAMILY_V1.md) | 후속 별도 checker·proof object·5개 domain 인증, coverage 11/64·gap 84, 남은 19개 수학은 별도 |
| [C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md](active/C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md) | ④-4c-1: 원래 19 domain·2,679점 exact Δ/CRT survey_only, 새 family 하한 0·coverage 유지 |
| [C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md](active/C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md) | ④-4c-2: shell 15〜18 전체 class cover·fixed prime-power 한계·가변 CRT gap 미해결, 새 shell lemma 0 |
| [C1B1_NORMALIZED_QUOTIENT_GAP_SURVEY_V1.md](active/C1B1_NORMALIZED_QUOTIENT_GAP_SURVEY_V1.md) | ④-4c-3: ceil(M/g)·변수 치환 D² identity·odd quotient 범위/coset, 작은 654 class 하한 추가·큰 8,076 class 미해결 |
| [C1B1_SAME_INPUT_CORRELATION_PLAN_V1.md](active/C1B1_SAME_INPUT_CORRELATION_PLAN_V1.md) | ④-4c-4 단계 계획. 최소 구현 착수, 전체 계획 완료·큰 class 인증 아님 |
| [C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md](active/C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md) | 최소 필터·proof object·별도 checker. 작은 241 class 하한 추가·7,835 미해결·큰 class symbolic 하한 0 |
| [C1B1_HARD_CASE_SEARCH_SURVEY_V1.md](active/C1B1_HARD_CASE_SEARCH_SURVEY_V1.md) | ④-4c-5: shell 18 hard-case 탐색 실현 가능성. quadratic 전체 실행 후보 109·hazard 0·checker 일치, survey_only |
| [C1B1_HARD_CASE_SEARCH_SHELL15_SURVEY_V1.md](active/C1B1_HARD_CASE_SEARCH_SHELL15_SURVEY_V1.md) | shell 15 survey_only(마지막 shell별 전수 조사). 후보 54,419·hazard 0. shell 14 이하로 방식을 잇지 않음(STOP) |
| [C1B1_HARD_CASE_CERTIFICATE_SHELL16_V1.md](active/C1B1_HARD_CASE_CERTIFICATE_SHELL16_V1.md) | ④-4c-10: shell 16 인증(같은 계약). 14/64·gap 81, shell 15 미승인 |
| [C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md](active/C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md) | ④-4c-9: shell 16 survey_only 전수 조사. 후보 6,581·hazard 0·checker 일치, 인증·coverage 변경 없음 |
| [C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md](active/C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md) | ④-4c-8: shell 17 인증(같은 계약)·단계별 비용. 13/64·gap 82, 전체 NotCertified |
| [C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md](active/C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md) | ④-4c-7: shell 17 단독 확장성 실측. 후보 827·hazard 0·checker 일치, survey_only |
| [C1B1_HARD_CASE_CERTIFICATE_V1.md](active/C1B1_HARD_CASE_CERTIFICATE_V1.md) | ④-4c-6: shell 18 hard-case 인증 계약·proof object·coverage 연결. shell 18 Certified, 12/64·gap 83, 전체 NotCertified |

## 동결 원문

| 실제 원문 | 이전 위치 |
|---|---|
| [C1A_AR2_FREEZE_V1.md](frozen/C1A_AR2_FREEZE_V1.md) | docs/current/C1A_AR2_FREEZE_V1.md |
| [PROBE_V3_FREEZE.md](frozen/PROBE_V3_FREEZE.md) | docs/current/PROBE_V3_FREEZE.md |

## 공통 참조

| 실제 원문 | 이전 위치 |
|---|---|
| [A_EXECUTION_ARCHITECTURE_V1.md](reference/A_EXECUTION_ARCHITECTURE_V1.md) | docs/current/A_EXECUTION_ARCHITECTURE_V1.md |
| [A_MICRO_V6_PHYSICS_CLOSURE_V1.md](reference/A_MICRO_V6_PHYSICS_CLOSURE_V1.md) | docs/current/A_MICRO_V6_PHYSICS_CLOSURE_V1.md |
| [A_NUMERIC_EXECUTION_STACK_V1.md](reference/A_NUMERIC_EXECUTION_STACK_V1.md) | docs/current/A_NUMERIC_EXECUTION_STACK_V1.md |
| [A_REALITY_GROUNDING_V1.md](reference/A_REALITY_GROUNDING_V1.md) | docs/current/A_REALITY_GROUNDING_V1.md |
| [A_V6_DEFORMABLE_MATERIAL_ARCHITECTURE_V1.md](reference/A_V6_DEFORMABLE_MATERIAL_ARCHITECTURE_V1.md) | docs/current/A_V6_DEFORMABLE_MATERIAL_ARCHITECTURE_V1.md |
| [PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md](reference/PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md) | docs/current/PREIMPLEMENTATION_POSSIBILITY_CHECK_V1.md |
| [VERIFICATION_LIMITS_AND_LESSONS.md](reference/VERIFICATION_LIMITS_AND_LESSONS.md) | docs/current/VERIFICATION_LIMITS_AND_LESSONS.md |
| [L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md](reference/L_ORIGIN_AND_OBSERVATION_PRINCIPLES_V2.md) | 신규(2026-10-01). L 최상위 원칙, 헌법 v0.3과 함께 적용 |

## 역사 / 과거 설계·실측

| 실제 원문 | 이전 위치 |
|---|---|
| [A_MICRO_SPATIAL_REPRESENTATION_V2.md](history/A_MICRO_SPATIAL_REPRESENTATION_V2.md) | docs/current/A_MICRO_SPATIAL_REPRESENTATION_V2.md |
| [A_MICRO_V5_BENCHMARKS_V1.md](history/A_MICRO_V5_BENCHMARKS_V1.md) | docs/current/A_MICRO_V5_BENCHMARKS_V1.md |
| [A_MICRO_V5_C1_RESULTS.md](history/A_MICRO_V5_C1_RESULTS.md) | docs/current/A_MICRO_V5_C1_RESULTS.md |
| [A_MICRO_V5_COLLISION_ROTATION_PLAN_V1.md](history/A_MICRO_V5_COLLISION_ROTATION_PLAN_V1.md) | docs/current/A_MICRO_V5_COLLISION_ROTATION_PLAN_V1.md |
| [A_MICRO_V5_ENERGY_V1.md](history/A_MICRO_V5_ENERGY_V1.md) | docs/current/A_MICRO_V5_ENERGY_V1.md |
| [A_MICRO_V5_GEO_V1B_PLAN.md](history/A_MICRO_V5_GEO_V1B_PLAN.md) | docs/current/A_MICRO_V5_GEO_V1B_PLAN.md |
| [A_MICRO_V5_GEO_V1B_RESULTS.md](history/A_MICRO_V5_GEO_V1B_RESULTS.md) | docs/current/A_MICRO_V5_GEO_V1B_RESULTS.md |
| [A_MICRO_V5_KINEMATICS_TIME_V1.md](history/A_MICRO_V5_KINEMATICS_TIME_V1.md) | docs/current/A_MICRO_V5_KINEMATICS_TIME_V1.md |
| [A_MICRO_V5_REFERENCE_EXECUTOR_PLAN_V1.md](history/A_MICRO_V5_REFERENCE_EXECUTOR_PLAN_V1.md) | docs/current/A_MICRO_V5_REFERENCE_EXECUTOR_PLAN_V1.md |
| [A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md](history/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md) | docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md |
| [A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md](history/A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md) | docs/current/A_MICRO_V6_C0_NUMERIC_EXECUTION_PLAN_V1.md |
| [A_MICRO_V6_N3B_BORN_MAYER_SURVEY_V1.md](history/A_MICRO_V6_N3B_BORN_MAYER_SURVEY_V1.md) | docs/current/A_MICRO_V6_N3B_BORN_MAYER_SURVEY_V1.md |
| [A_MICRO_V6_PARTICLE_DESIGN_V1.md](history/A_MICRO_V6_PARTICLE_DESIGN_V1.md) | docs/current/A_MICRO_V6_PARTICLE_DESIGN_V1.md |
| [A_V4_GEO_CONTACT_GROWTH_V1.md](history/A_V4_GEO_CONTACT_GROWTH_V1.md) | docs/current/A_V4_GEO_CONTACT_GROWTH_V1.md |
| [CAUSAL_COLLISION_SEMANTICS_V4.md](history/CAUSAL_COLLISION_SEMANTICS_V4.md) | docs/current/CAUSAL_COLLISION_SEMANTICS_V4.md |
| [DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md](history/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md) | docs/current/DETERMINISTIC_A_B_BUILD_SEQUENCE_V1.md |
| [DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md](history/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md) | docs/current/DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md |
| [LOCAL_INTERACTION_PRINCIPLES_V1.md](history/LOCAL_INTERACTION_PRINCIPLES_V1.md) | docs/current/LOCAL_INTERACTION_PRINCIPLES_V1.md |
| [MIDPOINT_A_B_AUDIT_2026-09-21.md](history/MIDPOINT_A_B_AUDIT_2026-09-21.md) | docs/current/MIDPOINT_A_B_AUDIT_2026-09-21.md |
| [MINIMAL_LOCAL_GEOMETRY_V1.md](history/MINIMAL_LOCAL_GEOMETRY_V1.md) | docs/current/MINIMAL_LOCAL_GEOMETRY_V1.md |
| [PRECONDITION_CENSUS_2026-09-21.md](history/PRECONDITION_CENSUS_2026-09-21.md) | docs/current/PRECONDITION_CENSUS_2026-09-21.md |
| [PROJECT_HANDOVER_REVIEW_2026-09-27.md](history/PROJECT_HANDOVER_REVIEW_2026-09-27.md) | docs/current/PROJECT_HANDOVER_REVIEW_2026-09-27.md |
| [PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md](history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md) | docs/current/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md |
| [DOCUMENT_ENTRY_GUIDE_BEFORE_FOLDER_CLEANUP_2026-09-27.md](history/DOCUMENT_ENTRY_GUIDE_BEFORE_FOLDER_CLEANUP_2026-09-27.md) | docs/current/README.md |
| [STRUCTURE_STATE_V1.md](history/STRUCTURE_STATE_V1.md) | docs/current/STRUCTURE_STATE_V1.md |
| [MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md](history/MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md) | docs/중간 결과/MIDPOINT_LOCAL_GEOMETRY_AND_WORLD_LANGUAGE_2026-09-22.md |
| [PROJECT_CLEANUP_AUDIT_V1.md](history/PROJECT_CLEANUP_AUDIT_V1.md) | docs/PROJECT_CLEANUP_AUDIT_V1.md |
| [C1B1_PROFILE_FREEZE_DRAFT.md](history/C1B1_PROFILE_FREEZE_DRAFT.md) | docs/proposals/C1B1_PROFILE_FREEZE_DRAFT.md |

## 후기 B 연구 자산

| 실제 원문 | 이전 위치 |
|---|---|
| [EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md](deferred/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md) | docs/current/EVOLVING_WORLD_LANGUAGE_ARCHITECTURE.md |
| [LANGUAGE_REVISION_GOVERNANCE_V1.md](deferred/LANGUAGE_REVISION_GOVERNANCE_V1.md) | docs/current/LANGUAGE_REVISION_GOVERNANCE_V1.md |
| [RESEARCH_STORE_V1.md](deferred/RESEARCH_STORE_V1.md) | docs/current/RESEARCH_STORE_V1.md |
| [WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md](deferred/WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md) | docs/current/WORLD_SPEC_LANGUAGE_DICTIONARY_V1.md |
| [00_전체_지도와_읽는_순서(1).md](deferred/b-design/00_%EC%A0%84%EC%B2%B4_%EC%A7%80%EB%8F%84%EC%99%80_%EC%9D%BD%EB%8A%94_%EC%88%9C%EC%84%9C%281%29.md) | docs/README/00_전체_지도와_읽는_순서(1).md |
| [01_프로젝트가_이해하기_어려워진_이유(1).md](deferred/b-design/01_%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8%EA%B0%80_%EC%9D%B4%ED%95%B4%ED%95%98%EA%B8%B0_%EC%96%B4%EB%A0%A4%EC%9B%8C%EC%A7%84_%EC%9D%B4%EC%9C%A0%281%29.md) | docs/README/01_프로젝트가_이해하기_어려워진_이유(1).md |
| [02_원래_목표와_World_Language_재정의(1).md](deferred/b-design/02_%EC%9B%90%EB%9E%98_%EB%AA%A9%ED%91%9C%EC%99%80_World_Language_%EC%9E%AC%EC%A0%95%EC%9D%98%281%29.md) | docs/README/02_원래_목표와_World_Language_재정의(1).md |
| [03_A와_B의_역할_재설계(1).md](deferred/b-design/03_A%EC%99%80_B%EC%9D%98_%EC%97%AD%ED%95%A0_%EC%9E%AC%EC%84%A4%EA%B3%84%281%29.md) | docs/README/03_A와_B의_역할_재설계(1).md |
| [04_B의_CPU_GPU_이중_탐색_구조(1).md](deferred/b-design/04_B%EC%9D%98_CPU_GPU_%EC%9D%B4%EC%A4%91_%ED%83%90%EC%83%89_%EA%B5%AC%EC%A1%B0%281%29.md) | docs/README/04_B의_CPU_GPU_이중_탐색_구조(1).md |
| [05_가설_실패_우연을_다루는_연구_방법(1).md](deferred/b-design/05_%EA%B0%80%EC%84%A4_%EC%8B%A4%ED%8C%A8_%EC%9A%B0%EC%97%B0%EC%9D%84_%EB%8B%A4%EB%A3%A8%EB%8A%94_%EC%97%B0%EA%B5%AC_%EB%B0%A9%EB%B2%95%281%29.md) | docs/README/05_가설_실패_우연을_다루는_연구_방법(1).md |
| [06_B의_기억_구조_파라미터_SSD_RAM_VRAM(1).md](deferred/b-design/06_B%EC%9D%98_%EA%B8%B0%EC%96%B5_%EA%B5%AC%EC%A1%B0_%ED%8C%8C%EB%9D%BC%EB%AF%B8%ED%84%B0_SSD_RAM_VRAM%281%29.md) | docs/README/06_B의_기억_구조_파라미터_SSD_RAM_VRAM(1).md |
| [07_자연어_없는_사고와_자모_수준_학습(1).md](deferred/b-design/07_%EC%9E%90%EC%97%B0%EC%96%B4_%EC%97%86%EB%8A%94_%EC%82%AC%EA%B3%A0%EC%99%80_%EC%9E%90%EB%AA%A8_%EC%88%98%EC%A4%80_%ED%95%99%EC%8A%B5%281%29.md) | docs/README/07_자연어_없는_사고와_자모_수준_학습(1).md |
| [08_B0_구현_학습_로드맵(1).md](deferred/b-design/08_B0_%EA%B5%AC%ED%98%84_%ED%95%99%EC%8A%B5_%EB%A1%9C%EB%93%9C%EB%A7%B5%281%29.md) | docs/README/08_B0_구현_학습_로드맵(1).md |
| [B0.6_Causal_Path_Builder_Deep_Design.md](deferred/b-design/B0.6_Causal_Path_Builder_Deep_Design.md) | docs/README/B0.6_Causal_Path_Builder_Deep_Design.md |
| [B0.6_Causal_Timeline_Evidence_Rules.md](deferred/b-design/B0.6_Causal_Timeline_Evidence_Rules.md) | docs/README/B0.6_Causal_Timeline_Evidence_Rules.md |
| [B_deep_causal_research_design.md](deferred/b-design/B_deep_causal_research_design.md) | docs/README/B_deep_causal_research_design.md |
| [EMERGENT_B_COMMUNICATION_LAYER_V1.md](deferred/EMERGENT_B_COMMUNICATION_LAYER_V1.md) | docs/EMERGENT_B_COMMUNICATION_LAYER_V1.md |

## 경로를 고정한 동결 원문

[연구자 B 신체 계약 원문](current/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)은 기존 경로와 바이트를 그대로 유지한다. [frozen 안내](frozen/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)에서 연결된다.
D_valid v2의 생성기·계약·fixture는 코드와 데이터 위치를 그대로 유지하며 [동결 범위 색인](frozen/D_VALID_V2.md)에서 찾는다.

## 기존에 분리돼 있던 자료

[확률 세계](legacy-probabilistic/README.md), [이전 사회·원시인·뇌](legacy-society-brain/README.md)는 기존 분류를 유지한다.
[장기 제안](proposals/README.md)은 구현·동결 상태와 구분한다.
[A 증명 조립 아키텍처](proposals/A_PROOF_COMPOSITION_ARCHITECTURE_V1.md)와
[로드맵](proposals/A_PROOF_COMPOSITION_ROADMAP_V1.md)은 장기 제안이다.
[Warehouse 아키텍처](proposals/A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md)도 PROPOSAL·미구현이다(2026-09-30 문서만 편입, Q9〜Q11 미판정). Runtime Proof Cache와 별개다.
[A 세계 계산 구조와 규모 설계 v0](proposals/A_WORLD_COMPUTE_ARCHITECTURE_AND_SCALE_V0.md)도 PROPOSAL·미구현·승인 아님이다(2026-09-30). 멀티스케일은 미승인·A급 미결(X2·X4와 충돌), GPU는 조건부 후보이며, X2·X4와 C1-B1·④-Liveness 상태는 바뀌지 않는다.
[A 수치 재료 설계 메모 v0](proposals/A_NUMERIC_DREAM_MATERIALS_V0.md)도 PROPOSAL·미구현·승인 아님이다(2026-09-30). 물리는 그대로 두고 실행기 내부 수치 표현만 특화하는 연구 아이디어이며, 기준 실행기(X2)와의 비교가 채택 조건이다.
[Exact Aggregate 연구 제안 v0](proposals/A_EXACT_AGGREGATE_RESEARCH_PROPOSAL_V0.md)도 PROPOSAL·미구현·승인 아님이다(2026-09-30). Exact Aggregate는 물리 입자가 아니라 실행기 쪽 정확 압축 표현이며, X2·X4를 바꾸지 않는다.
현재 C1-B1의 최소 proof/checker 구현을 장기 구조 전체 완료로 승격하지 않는다.
옛 경로가 필요한 코드·시험·규칙은 호환 안내를 통해 실제 원문을 찾는다. LLM_HANDOFF의 manifest는 생성 당시 스냅샷이므로 현재 파일의 해시 목록으로 사용하지 않는다.
