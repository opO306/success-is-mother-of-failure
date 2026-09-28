# 장기 제안 — 구현·동결 아님

현재 활성 Gate는 [C1-B1](../active/README.md)이다. 이 폴더의 제안을 근거로 scheduler·region·학습 관리자나 새 물리 규칙을 구현하지 않는다.

- [A 실행 증명서 제안](A_RUNTIME_CERTIFICATE_PROPOSAL.md): 장기 후보. 전역 증명과 한 실행의 증거를 구분하는 제안이며 구현·동결 아님.
- [A 계산·메모리·기록 아키텍처 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md): 요구사항·후보이며 구현·동결 아님.
- [A 증명 조립 아키텍처](A_PROOF_COMPOSITION_ARCHITECTURE_V1.md): 장기 구조 제안. 현재 C1-B1 최소 proof/checker 구현과 전체 구조 완료는 구별한다.
- [A 증명 조립 로드맵](A_PROOF_COMPOSITION_ROADMAP_V1.md): 실제 큰 class 수학 효과를 확인한 뒤 범용화·창고·자동화로 진행하는 순서. 이후 단계는 미구현.
- [A 계산·증명 Warehouse 아키텍처](A_PROOF_COMPUTE_WAREHOUSE_ARCHITECTURE_V1.md): 위 두 문서가 이름만 부른 Proof Warehouse(5.4·5.5절, Phase 6·7)의 저장·metadata·의존성 골조 설계. **설계 전용·미구현.** 현재 구조와의 충돌 13곳과 기존 결과를 바꾸지 않는 read-only v0 범위를 보고한다. 설계자 승인 전 코드 변경 없음.

옛 [C1-B1 profile 동결 초안](../history/C1B1_PROFILE_FREEZE_DRAFT.md)은 역사로 이동했다. 이름에 FREEZE가 있어도 실제 상태는 보류·미동결이다.
