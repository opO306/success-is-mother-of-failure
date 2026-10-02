# 장기 제안 — 구현·동결 아님

현재 활성 Gate는 [C1-B1](../active/README.md)이다. 이 폴더의 제안을 근거로 scheduler·region·학습 관리자나 새 물리 규칙을 구현하지 않는다.

- [C1-C / Small-A Foundation v0](C1C_MULTIPARTICLE_GAS_FOUNDATION_V0.md): 최초 다원자 Ar 기체의 계약·온도/에너지·반올림 합산·periodic images·현실성·검증/기록 비용 설계. **DESIGN ONLY / 미구현 / 미승인 / 미동결.** N·박스·dt·GPU·경계·검증 전략은 설계자 미결이며 C1-B1 상태를 바꾸지 않는다.
- [Reality-Anchored Small-A Initial State Pilot V0](REALITY_ANCHORED_SMALL_A_INITIAL_STATE_PILOT_V0.md): 공개 고체 Ar CIF의 평균 구조를 네 자리로 재구성한 **SURVEY + ISOLATED PROTOTYPE**. R2 / B / MISSING_DYNAMIC_STATE, forward 0 step. 순간 q,p·순수 40Ar 자료 확보가 아니며 Small-A N·밀도·PBC·C1-C 계약을 확정하지 않는다.
- [Reality-Constrained Deterministic Initial State Pilot V0](REALITY_CONSTRAINED_DETERMINISTIC_INITIAL_STATE_V0.md): 희박 Ar의 실험 T/p와 조건부 가정을 이용한 q,p 후보 30개 비교. **E / REALITY_DATA_INSUFFICIENT / CONDITIONAL_ASSUMED_PROXY_ONLY**, 현실 전용 경로 REFUSED, forward 0 step. 인공 구조·방향 및 q-p 편향을 보존하며 production·C1-C 계약 확정이 아니다.

- [A 실행 증명서 제안](A_RUNTIME_CERTIFICATE_PROPOSAL.md): 장기 후보. 전역 증명과 한 실행의 증거를 구분하는 제안이며 구현·동결 아님.
- [A 계산·메모리·기록 아키텍처 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md): 요구사항·후보이며 구현·동결 아님.
- [A 증명 조립 아키텍처](A_PROOF_COMPOSITION_ARCHITECTURE_V1.md): 장기 구조 제안. 현재 C1-B1 최소 proof/checker 구현과 전체 구조 완료는 구별한다.
- [A 증명 조립 로드맵](A_PROOF_COMPOSITION_ROADMAP_V1.md): 실제 큰 class 수학 효과를 확인한 뒤 범용화·창고·자동화로 진행하는 순서. 이후 단계는 미구현.
- [A 세계 계산 구조와 규모 설계 v0](A_WORLD_COMPUTE_ARCHITECTURE_AND_SCALE_V0.md): 미국급 가상 대륙 + 큰 바다, CPU 64코어 + GPU 규모의 미래 A 확장 상위 설계. **PROPOSAL·미구현·승인 아님.** 멀티스케일은 미승인·A급 미결(X2·X4·헌법 제2조와 충돌), GPU는 조건부 후보(수 체계 미정), X2·X4 변경 없음, C1-B1·④-Liveness 상태 변화 없음. 끝의 32절이 본문보다 우선한다.
- [A 수치 재료(꿈의 재질) 설계 메모 v0](A_NUMERIC_DREAM_MATERIALS_V0.md): A의 물리는 그대로 두고 실행기 내부의 숫자·자료형·표현(dyadic, adaptive exact, RNS, exp 전용 엔진, GPU regular fast path 등)만 특화해 계산량·메모리를 줄일 수 있는지 탐색하는 연구 아이디어. **PROPOSAL·미구현·승인 아님.** 기존 [A 수치 실행 계층 v1](../reference/A_NUMERIC_EXECUTION_STACK_V1.md)(A-Numeric VM, 기준 의미)과 역할이 다르며 C1-B1 기준 실행기와의 비교가 채택 조건이다. 시작 시점은 C1-B1 이후 profiler 측정부터.
- [Exact Aggregate 연구 제안 v0](A_EXACT_AGGREGATE_RESEARCH_PROPOSAL_V0.md): 원자 집단을 기준 실행기와 정확히 같은 결과로 하나의 계산 단위로 압축할 수 있는지, 압축률은 얼마인지 묻는 연구 제안. **Exact Aggregate = physical particle 아님, 실행기 쪽의 정확한 집단 표현.** PROPOSAL·미구현·승인 아님. Level 0은 승인된 X4 "지금"(정확한 요약) 안, 손실 압축은 금지. 물리 선택(v5/v6/C1-B1 계열)과 시작 시점은 설계자 결정.
- [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md): 증명·계산 결과의 색인·의존성 장부 설계. **PROPOSAL·미구현·Q9〜Q11 미판정.** 2026-09-30 문서만 master에 편입(브랜치 병합 아님). A 실행 경로 밖이며 Runtime Proof Cache와 별개다.

옛 [C1-B1 profile 동결 초안](../history/C1B1_PROFILE_FREEZE_DRAFT.md)은 역사로 이동했다. 이름에 FREEZE가 있어도 실제 상태는 보류·미동결이다.
