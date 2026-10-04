# 설계 구상과의 별도 대조 — R04 JC V1

자동 시험 외의 source/data/계약 대조. 작성자 검토이며 외부 독립 승인 아님.

| 설계 요구 | 실제 작동과 근거 | 판정/한계 |
|---|---|---|
| 실제 R=.4 symmetric JC target | ZA/ZB1, IE/IAB1, x/y0, 공통 u/w1; 실제 original caller HS/EV 캡처, 원문 strip exact | 일치. R의 REAL*16 rounding 존재 |
| nuclear repulsion 중복 금지 | 원문 HAM Coulomb의 ZA*ZB 포함, wrapper energy에 추가1/R 없음 | 일치; physical Hamiltonian 전면 independent derivation 아님 |
| Ω/NMAX/NDIGITS 분리 | Ω5u1 NMAX ladder, 고정N120 ND60/80; 이후 common-u3Ω 및 각N100 spot | 일치. NMAX truncation bound 미증명 |
| 에너지 전 size/optimizer 봉인 | native enumeration-only STOP; protocol timestamp/hash 이후 execute | 일치. 사전 비용 예측은 실측 cost 주장 아님 |
| reference leakage 방지 | 비교값은 separate compare.py에만 존재, runner/contract에 reference 없음, energy_seal이 먼저 | 일치. 사용자 지시로 이미 알려진 값이지만 계산 경로에서 분리 |
| finite variational 자체검색 | MEDIUM7evaluation만, own accepted E; common u transfer | 일치한 선택. 각Ω개별 optimum 주장 안함; limited search/global optimum 미확인 |
| 정상 convergence 자체감사 | real branch/40iteration refusal retained, 단1retry; accepted17 모두 strict branch | 일치. exit0/printed E만으로 승격하지 않음 |
| 실제 stored SPD/lowest/residual | unchanged V1hash, positive SPD margin, independent count0→1, exact Einside, HPresidual240 | 저장 유한문제 지지. generator/model/continuous integrals formal certification 아님 |
| representation 진행 | common-u degree-prefix nested20→78→228; E 실제감소 | 3점 조건부지지. 무한Ωerror bound 아님 |
| Gaussian 공정 비용 | target후 samehost/wrapper freshV5Z, unchangedphysics/basis/guards | measurement비교가능. validation/task 차이는 공개. totalJC79.55s vsV5Z33.30s로 전체wall우위미지지 |
| 실패/역사보존 | prepare1failure+MAXIT1refusal, old985bindings unchanged | 일치. oldHHe/General/JCasy anomaly unresolved |
| 범위/STOP | final3/spots3만, noR1.4/6/B2/curve/A/push | 일치. 다음실험은 새설계자결정 필요 |

근사: finite representation, finite Taylor/working precision, REAL*16 input, 제한된u검색, 240-digit residual 측정.
미구현: B2clean-room, wholecurve, independentCoulombintegrals proof, model/reference error budget, production/dynamics.
숨기지 않은 강제조건: vendorITMAX40, checkerunpivoted LDL/precision cap240decimal, accepted당proof 비용, wavefunction/export측정부하, genericu searchbounds[.5,1.5], mediumcommonu transfer.
후속 판단: 이번accepted문제를B2비교기준으로 쓸 수 있다. 전체승인이나효율일반화는 하지 않는다.
