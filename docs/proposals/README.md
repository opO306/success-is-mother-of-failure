# 장기 제안 — 구현·동결 아님

현재 활성 Gate는 [C1-B1](../active/README.md)이다. 이 폴더의 제안을 근거로 scheduler·region·학습 관리자나 새 물리 규칙을 구현하지 않는다.

- [A 실행 증명서 제안](A_RUNTIME_CERTIFICATE_PROPOSAL.md): 장기 후보. 전역 증명과 한 실행의 증거를 구분하는 제안이며 구현·동결 아님.
- [A 계산·메모리·기록 아키텍처 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md): 요구사항·후보이며 구현·동결 아님.
- [A 증명 조립 아키텍처](A_PROOF_COMPOSITION_ARCHITECTURE_V1.md): 장기 구조 제안. 현재 C1-B1 최소 proof/checker 구현과 전체 구조 완료는 구별한다.
- [A 증명 조립 로드맵](A_PROOF_COMPOSITION_ROADMAP_V1.md): 실제 큰 class 수학 효과를 확인한 뒤 범용화·창고·자동화로 진행하는 순서. 이후 단계는 미구현.
- [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md): 증명·계산 결과의 색인·의존성 장부 설계. **PROPOSAL·미구현·Q9〜Q11 미판정.** 2026-09-30 문서만 master에 편입(브랜치 병합 아님). A 실행 경로 밖이며 Runtime Proof Cache와 별개다.

옛 [C1-B1 profile 동결 초안](../history/C1B1_PROFILE_FREEZE_DRAFT.md)은 역사로 이동했다. 이름에 FREEZE가 있어도 실제 상태는 보류·미동결이다.
