# O-1 단일 불일치 원인 격리 — 사전 프로토콜

2026-10-01. 시작 HEAD/실제 origin/master: `504e83748074f25d9ce4cec182bf11f537795e8c`, clean, ahead/behind 0/0. 직전 O-1 기록 커밋이다. 사용자의 첨부 원인 격리 지시를 실행 권한으로 사용한다. push 금지.

대상은 기존 `boundary_pass` 단 하나: E=0.5 De, rho=-0.001, b=11.707286169880804 bohr. 초기 12 raw는 기존 봉인에서 읽는다. 기존 D_valid: unsupported. 기존 DISAGREE 및 9개 CONFIRMED/REPLAY_VERIFIED 역사는 보존한다. rho=-0.0001은 실행하지 않는다.

독립 HP-KDK는 중심력의 정확한 두 입자 환원 q=rj-ri, P=(pj-pi)/2, mu=m/2를 사용한다. P_half=P+h F(q)/2, q_new=q+h P_half/mu, P_new=P_half+h F(q_new)/2. fixed-point 양자화는 없다. mpmath는 유한 자릿수 반올림이 있는 arbitrary-precision floating arithmetic이며 수학적 정확 실수라고 주장하지 않는다. 공개 Lang 십진 specification 파서와 질량/단위만 기존 독립 O-1에서 공유하고, analytic dV/dr와 KDK 갱신은 새 구현이다. production step/kick/drift/force/rounding/replay를 호출하지 않는다.

먼저 dt=40을 40/60 decimal digits에서 실행한다. 산란각/방향/최접근 chord/최종 q,p/에너지 최대 변화/L 최대 변화의 자릿수 차이를 보존한다. 각도·거리 변화 <=1e-20, 상대 에너지 변화/De 차이 <=1e-20, q,p 차이 <=1e-20가 아니면 UNRESOLVED STOP. dt=40 결과를 보기 전 기준:

- HP40와 production A 각도 차이 <=1e-8 rad, HP40와 연속 기준 차이 >1e-5 rad, 그 차이 >=100배 HP40-A 차이이면 TIME_DISCRETIZATION_SUPPORTED. 이것만 dt 축소를 허용한다.
- HP40와 연속 기준 차이 <=1e-8 rad이고 production A만 >1e-5 rad이면 FIXED_POINT_SUPPORTED_STOP.
- 다른 경우 UNRESOLVED_STOP. O-1 절대 1e-5 rad 기준을 변경하지 않는다.

공통 출구: 기존 A의 실제 출구 반경을 종료 표면으로 쓰고, HP의 최초 outbound 저장 끝점까지 매 dt의 전체 걸음을 수행한다. 끝점 snap/운동량 보정/부분 step 없음. 서로 다른 overshoot가 산란각 비교에 섞이지 않도록 기존 연속 기준의 H,L을 이용해 이전 출구와 HP 출구 사이의 짧은 outbound radial angle 적분만 추가한다. direction=기존 direction+추가 theta+atan2(L/r,sqrt(g(r)))의 변화, g=2mu(H-V)-L²/r². 기존 기준을 전체 재계산하지 않는다. r_exit는 기존 raw 정수에서 계산한 고정밀 반경을 사용한다. 표시용 binary64 반경으로 대체하지 않는다. endpoint 보정은 40/60자리 비교 및 별도 허용 테스트로 검증하며, 한계는 보고한다. HP40-A 직접 비교는 step 수가 같고 출구 반경 차이 <=1e-8 bohr이어야 한다. 아니면 STOP.

시간 이산화 조건 충족 시에만 dt20/10/5를 60자리에서 순서대로 수행한다. 각도/r_min/방향/에너지/L/비용/출구 보정량을 기록한다. 2차 수렴을 가정하거나 결과로 판정 기준을 넓히지 않는다. 감소하지 않는 오차나 새 불안정은 STOP/보고한다. 축소 dt의 독립 arithmetic 재실행은 필요 시만 수행하고 미검증 범위를 밝힌다.

모든 진단 stored state를 gzip JSONL로 별도 runs 경로에 보존한다. 입력·기존 증거·protected source·새 진단 소스·본 프로토콜 SHA-256을 첫 물리 실행 전에 봉인한다. 기존 원본의 저장 해시 전수 대조와 저장 production angle 재관측을 먼저 수행한다. 새 진단은 numerical diagnostic이며 CONFIRMED production history나 formal certified가 아니다.

새 package/driver/시험/문서만 추가하며 production/공용 코드/fixture/기존 봉인 수정 없음. 우선 관련 시험을 수행한다. 변경 목록·해시 불변 조건을 충족하면 LOCAL FULL 생략/관련 시험 대체를 명시하고 기존 기준선을 갱신하지 않는다. Energy Bound v0 APPROVED, Liveness NotCertified, Safety Conditional, A-EV unresolved, Production Replay Verifier V1 APPROVED, O-1 STOPPED/NOT PASSED 유지. 사용자 금지 범위의 작업은 시작하지 않는다.
