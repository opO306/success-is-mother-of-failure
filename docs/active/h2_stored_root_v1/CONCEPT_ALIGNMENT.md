# 구상 일치성 2차 검토 — Stored-Matrix Lowest-Root V1

자동 시험과 별도로 승인 요청을 실제 구현·결과에 대조했다. 구현 작성자 검토이며 외부 독립 승인 아님.

| 설계자 요구 | 실제 작동 | 한계/판정 |
|---|---|---|
| 공식 H2SOLV도 독립 감사 대상 | 기존 실제 pre-invsg H/S와 returned E/v를 자체 parser로 읽고 새 MPFR interval LDL/inertia로 판정 | transport format은 공유 사양, vendor numerical code는 공유하지 않음 |
| 수렴과 최저 root 분리 | 5/5 원래 수렴 기록을 그대로 보존하면서 lowest는2/5만 확인, JC asymmetric1→2 반례 | 의도한 desired root가 반드시 lowest여야 하는지는 별도 source/입력 의미 진단 대상 |
| S SPD 먼저, 불확실할 때 추정 금지 | 3개 interval SPD, H–He⁺ exact negative direction, General 최대 rung에서도 UNCERTAIN | General의 미확정은 indefinite/특이 판정이 아님; unpivoted factor의 interval wrapping 한계 포함 |
| WA1을 정답으로 쓰지 않음 | SPD3개 actual EN에서 independent count와 WA1 일치, root는 새 shift에서 독립 계산 | S 실패2개는 count 미실행, 전체 WA1 semantics승격 안 함 |
| 임의 residual PASS값 추가 금지 | 240자리 raw/nS/RQ와 SPD일 때 rho 측정, 성공 root구간과 일관성만 비교 | interval residual bound/eigenvector formal certificate가 아님 |
| 검사기 자체를 감사 | 실행 전 합성33개, 실제5개 S test copy의 negative 방향 탐지, 후속 별도 exact Fraction action 재검증 | 사후 proof replay를 blind external audit로 명명하지 않음 |
| 5개 검사와 실패 STOP | 모든 case를 기록하되 실패 S의 dependent root/rho는 미실행; 전체 UNRESOLVED/STOP | all-five/precondition control은 사전 PLAN에 명시, 추가 precision/root search로 결과를 맞추지 않음 |
| 원본과 실패 보존 | 과거660binding 전후 hash불변; 최대 precision 미확정/첫 test collection error 로그 모두 보존 | byte provenance는 물리 적분 정확성 인증이 아님 |
| 범위/비용/운영 제한 | R=.4/B2/sweep/optimization0, 새 수치 library 설치0, vendor 재실행0, 관련시험대체, local commit만 | production미승인/NOT_CERTIFIED, 다음 진단은 새 설계자 결정 대상 |
