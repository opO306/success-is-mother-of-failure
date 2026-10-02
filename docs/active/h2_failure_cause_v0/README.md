# H₂ QZ Failure Cause Separation V0 evidence

**PARTIAL / STOPPED / NOT CERTIFIED.**
R=0.5 residual measurement error는 exact enclosure로 분리했다.
독립 C1 reference 후보는 R=0.4에서 invalid, 네 short-R 원인은 UNRESOLVED다.
원래 QZ44 NUMERICAL FAIL과 43/1 acceptance는 보존한다.

- [보고서](../H2_QZ_FAILURE_CAUSE_SEPARATION_V0.md)
- [summary.json](summary.json): 분류·한계·threshold semantics·비용·설계자 결정
- [seal.json](seal.json): protected200/source7/input10, 사전 protocol과 package versions
- [A_R_0.5.json](A_R_0.5.json): binary64 bit 일치 및 exact squared norm 하·상한
- [B_R_0.5.json](B_R_0.5.json): interval → exact fallback prototype, production 미적용
- [results.json](results.json): 완료된 A/B와 R=0.4 invalid C1 두 후보, 전체 완료 아님
- C_R_0.4_*.json: invalid candidate residual/action/energy/cost; accepted reference 아님
- [preseal_failures.json](preseal_failures.json), [checkout_audit.json](checkout_audit.json):
  Git 경로·CRLF checkout 문제, numerical 시작 전 실패
- [controlled_stop.json](controlled_stop.json): R=0.6 worker 중단 이유와 process 상태
- audit*_console.log: 실패/실행/중단 원문, 삭제·재시도 덮어쓰기 없음
- tests*_final.log: 이번 Windows99/WSL15 관련 시험, skip0
- *.py.txt / protocol.json.txt: sealed source·시험·postprocessor snapshot
- [preservation.json](preservation.json): 원래 raw646개 hash 보존, protected200·입력 검증
- [raw_manifest.json](raw_manifest.json): worktree runs/h2_failure_cause_v0/의 scoped raw16개

raw NPZ는 worktree runs/에 보존하며 Git 밖이다. 원래 source·config·QZ44 결과는 수정하지 않았다.
C2/C3 확대·새 QZ44·production 통합은 미실행이며 추가 numerical 실행은 설계자 결정이 필요하다.
