# 장기 제안 — 구현·동결 아님

현재 활성 Gate는 [C1-B1](../active/README.md)이다. 이 폴더의 제안을 근거로 scheduler·region·학습 관리자나 새 물리 규칙을 구현하지 않는다.

- [A 실행 증명서 제안](A_RUNTIME_CERTIFICATE_PROPOSAL.md): 장기 후보. 전역 증명과 한 실행의 증거를 구분하는 제안이며 구현·동결 아님.
- [A 계산·메모리·기록 아키텍처 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md): 요구사항·후보이며 구현·동결 아님.
- [A 증명 조립 아키텍처](A_PROOF_COMPOSITION_ARCHITECTURE_V1.md): 장기 구조 제안. 현재 C1-B1 최소 proof/checker 구현과 전체 구조 완료는 구별한다.
- [A 증명 조립 로드맵](A_PROOF_COMPOSITION_ROADMAP_V1.md): 실제 큰 class 수학 효과를 확인한 뒤 범용화·창고·자동화로 진행하는 순서. 이후 단계는 미구현.
- [A 세계 계산 구조와 규모 설계 v0](A_WORLD_COMPUTE_ARCHITECTURE_AND_SCALE_V0.md): 미국급 가상 대륙 + 큰 바다, CPU 64코어 + GPU 규모의 미래 A 확장 상위 설계. **PROPOSAL·미구현·승인 아님.** 멀티스케일은 미승인·A급 미결(X2·X4·헌법 제2조와 충돌), GPU는 조건부 후보(수 체계 미정), X2·X4 변경 없음, C1-B1·④-Liveness 상태 변화 없음. 끝의 32절이 본문보다 우선한다.
- [MacroAtom 연구 제안 v0](A_MACROATOM_RESEARCH_PROPOSAL_V0.md): 원자 집단을 기준 실행기와 정확히 같은 결과로 하나의 계산 단위로 압축할 수 있는지, 압축률은 얼마인지 묻는 연구 제안. **MacroAtom = physical particle 아님, executor-side exact aggregate.** PROPOSAL·미구현·승인 아님. Level 0은 승인된 X4 "지금"(정확한 요약) 안, 손실 압축은 금지. 물리 선택(v5/v6/C1-B1 계열)과 시작 시점은 설계자 결정.
- [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md): 증명·계산 결과의 색인·의존성 장부 설계. **PROPOSAL·미구현·Q9〜Q11 미판정.** 2026-09-30 문서만 master에 편입(브랜치 병합 아님). A 실행 경로 밖이며 Runtime Proof Cache와 별개다.

옛 [C1-B1 profile 동결 초안](../history/C1B1_PROFILE_FREEZE_DRAFT.md)은 역사로 이동했다. 이름에 FREEZE가 있어도 실제 상태는 보류·미동결이다.
