# C1-B1 O-1 단일 불일치 원인 격리 V1

2026-10-01. **TIME_DISCRETIZATION_SUPPORTED — numerical diagnostic.**

같은 입력의 HP-KDK40과 production A는 각도 차이가 **2.20133e-11 rad**인데, HP-KDK40과 연속 기준의 차이는 **1.30928e-5 rad**다. 진단 dt를 20/10/5로 줄이자 출구 반경을 맞춘 각도 오차가 매번 약 1/4로 줄었다. 이 단일 입력의 불일치를 설명하는 주요 후보는 dt=40 KDK 시간 이산화다. fixed-point/rounding 영향이 없다는 증명이나 전체 영역의 보장은 아니다.

**기존 O-1 = STOPPED / NOT PASSED, AGREE 8 / DISAGREE 1 / UNRESOLVED 0 / NOT_RUN_AFTER_STOP 1을 유지한다.** 이번 입력의 기존 D_valid는 **unsupported**다. 지원된 D_valid 내부의 실패 반례로 쓰지 않는다. 기존 DISAGREE를 성공으로 재분류하지 않는다. production dt=40, FX(96,48)/FX(96,80), drift v2, PES, retardation, r_min, 1e-5 rad 기준, D_valid, approved verifier와 CONFIRMED 의미는 그대로다.

[실행 전 프로토콜](C1B1_O1_CAUSE_ISOLATION_PROTOCOL_V1.md) / [입력·source·원본 봉인](C1B1_O1_CAUSE_ISOLATION_SEAL_V1.json) / [전체 결과·비용·해시](C1B1_O1_CAUSE_ISOLATION_RESULTS_V1.json) / [이전 O-1 STOP 보고서](C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md).

## 1. 시작 Git 상태와 범위

시작 작업 트리 clean. HEAD, 로컬 origin/master, `git ls-remote origin refs/heads/master`로 확인한 실제 원격은 모두 **504e83748074f25d9ce4cec182bf11f537795e8c**, branch master, ahead/behind **0/0**이었다. 첨부의 이전 기준 f03fb30 뒤에 504e837 `Record O-1 numerical reproduction STOP`가 추가돼 있었다. 그 이전 커밋은 f03fb30의 source-binding 재감사다. 새로운 commit/push는 하지 않았다.

AGENTS.md와 RULES.md를 읽고, CURRENT_STATE.md의 활성 상태·O-1 기록 및 REPO_MAP.md의 관련 모듈 위치를 확인했다. 큰 상태/맵 문서의 최초 묶음 출력은 잘렸으므로 관련 절을 다시 읽었다. 모든 역사 문서를 전수 재감사한 것은 아니다. 이번 사용자의 첨부는 원인 격리·조건부 dt 축소 진단의 실행 권한이다.

대상은 **E=0.5 De, rho=-0.001, b=11.707286169880804 bohr** 한 입력이다. 기존 입력 봉인의 12 raw를 정확히 읽었다. 기존 9개 궤적 전체의 원본/파생 증거 97개 SHA-256을 대조했고, boundary_pass의 초기 상태·CONFIRMED/REPLAY_VERIFIED 기록·저장 기준을 결합했다. 기존 9개 trajectory를 새 production history로 다시 실행하지 않았다. rho=-0.0001도 실행하지 않았다.

## 2. 별도 계산기와 공유 경계

새 `c1b1_o1_diagnostic/kdk.py`는 공개 Lang 계수를 arbitrary precision으로 읽고, V(r)와 analytic dV/dr를 별도로 계산한다. BO/REL/QED 및 retardation ON을 유지한다. 상대 q=rj-ri, P=(pj-pi)/2, mu=m/2에 대해 별도 KDK를 실행한다:

```text
P_half = P + h F(q)/2
q_new = q + h P_half/mu
P_new = P_half + h F(q_new)/2
```

이는 같은 두 원자 중심력 방정식의 환원이다. fixed-point 투영·상태 snap·보정·substep은 없다. mpmath 40/60 decimal digits는 유한 정밀도 부동소수점이며 수학적 정확 실수라고 주장하지 않는다. 연속 기준은 기존 80자리 계산을 재사용하고, 출구 주변 짧은 radial 적분만 추가한다.

공유한 코드는 기존 독립 `c1b1_o1.model.parse`의 공개 십진 사양 파서와 MASS/DE/SOURCE 상수다. 질량, 단위, retardation, 정확 raw를 공유한다. 기존 `Potential` evaluator는 진단 갱신에 호출하지 않고 시험의 별도 수치 미분 대조에만 사용했다. reference step/kick/drift/force/impulse/rounding 및 production replay verifier를 계산기로 사용하지 않았다. 금지 import도 AST 시험으로 검사했다. 기존 O-1 공개 사양 파서를 공유하므로 specification/parsing의 공통 오류 가능성을 완전히 제거한 새 독립 물리 감사는 아니다.

새 `study.py`는 seal → forty → 조건 충족 시 reduce의 순서다. 모든 진단 stored state를 별도 gzip JSONL에 보존한다. 진단 기록은 CONFIRMED production history가 아니라 외부 관측 연구 자료다.

## 3. 저장 기준의 재관측 및 출구 비교

초기 H,L 및 기존 연속 direction을 raw에서 다시 대조했다. 기존 continuous direction 재관측 차이는 **2.10844e-80 rad**였다. production 최종 raw 운동량을 고정밀로 다시 관측한 χ는 **-0.1236192556230016579006338771 rad**, 기존 binary64 표시와 **3.58092e-18 rad** 차이다. 기존 기준의 재현 불일치는 발견되지 않았다.

봉인 전 새 검사에서 표시용 binary64 출구 반경을 잘못 사용해 **5.16560e-17 rad** 차이를 만드는 진단 코드 오류가 한 번 발생했다. 원인을 확인하고 정확 raw에서 복원한 반경으로 수정했다. 회귀 시험은 수정 전 실패, 수정 후 통과했다. 이때 물리 진단 실행은 0회였고 실패 기록은 attempt_notes.json에 보존했다. 기존 기준·trajectory는 변경하지 않았다.

원래 A의 정확 출구 반경은 **20.0023070306715183983 bohr**다. 각 HP 진단은 이 표면을 처음 넘는 outbound **전체 걸음 끝점**을 기록한다. snap/부분 걸음/운동량 보정은 없다. dt40의 끝점 step은 A와 같은 17,284이며 반경 차이는 약 **1.455e-10 bohr**다. 다른 dt에서 overshoot가 달라지므로 연속 해의 H,L로 기존 출구에서 HP의 실제 반경까지 짧은 outbound angle/time 적분을 한다. 원본 continuous 값은 덮어쓰지 않는다.

| dt | HP 실제 출구 반경(bohr) | continuous direction의 출구 보정(rad) |
|---:|---:|---:|
| 40 | 20.002307030817017 | 7.53217e-14 |
| 20 | 20.002371169706317 | 3.32029e-8 |
| 10 | 20.002387204349428 | 4.15035e-8 |
| 5 | 20.002391213005255 | 4.35786e-8 |

아래 수렴 오차는 **각 HP의 실제 출구에 맞춘 연속 기준**과의 차이다. 원래 출구 기준과의 차이도 전체 JSON의 원본 χ·보정량으로 별도 복원할 수 있다. χ는 유한 시작에서 유한 출구까지의 signed momentum angle이며 무한거리 χ∞가 아니다. 초기 방향이 공통이므로 χ와 출구 방향의 오차가 같다. 추가 회전은 sweep으로 별도 보존한다.

## 4. dt40의 세 값 비교와 판정

| 계산 경로 | χ(rad) | 원래 연속 기준과의 차이(rad) |
|---|---:|---:|
| 독립 연속 기준, 원래 출구 | -0.123632348441596061 | 0 |
| HP-KDK40, 60자리 | -0.123619255645015007 | 약 1.30927966e-5 |
| production A40, 최종 raw 재관측 | -0.123619255623001658 | 약 1.30928186e-5 |

HP40-A 직접 차이 **2.20133491e-11 rad**. HP40의 자기 출구에 맞춘 연속 기준과 차이 **1.30927965057321e-5 rad**. 40→60자리 χ 변화 **4.96446009e-38 rad**, direction **4.98977e-38**, chord Rmin **1.45843e-39 bohr**, 최종 q,p의 최대 차이는 **6.10592e-37**이다. 에너지 최대 변화/De 차이는 **5.63361e-40**이다. 선언한 arithmetic 안정 조건 <=1e-20을 만족했다.

사전 원인 분리 기준은 HP40-A <=1e-8, HP40-continuous >1e-5 및 >=100배 HP40-A다. 전부 충족해 **TIME_DISCRETIZATION_SUPPORTED**로 기록한 뒤에만 dt20/10/5를 시작했다. fixed-point 후보 또는 UNRESOLVED라면 축소 실험을 차단하는 시험도 통과했다. O-1의 1e-5 기준을 결과 뒤 넓히지 않았다.

HP40 chord Rmin은 **6.8818807993774414 bohr**이며 기존 A 관측 **6.881880799377411 bohr**와 약 3e-14 차이다. A의 Rmin 관측은 binary64이고, 이 차이에 관측 반올림도 포함돼 있어 순수 fixed-point 기여라고 부르지 않는다. 산란각의 HP40-A 비교는 고정밀 raw 재관측을 사용해 표시용 각도 계산 영향을 줄였다. 남은 차이도 두 구현의 전체 차이이며 force/rounding 각각의 엄밀 상한을 증명한 것은 아니다.

## 5. 조건부 dt 축소 결과

아래는 60자리 HP-KDK 진단이며 production dt를 바꾼 결과가 아니다. 연속 Rmin은 **6.8818805163810469892 bohr**다.

| dt | steps | HP χ(rad) | matched continuous와 χ 차이(rad) | HP chord Rmin(bohr) | Rmin 차이(bohr) |
|---:|---:|---:|---:|---:|---:|
| 40 | 17,284 | -0.123619255645015 | 1.30927965e-5 | 6.881880799377441 | 2.82996394e-7 |
| 20 | 34,568 | -0.123629042054850 | 3.27318382e-6 | 6.881880613364673 | 9.69836265e-8 |
| 10 | 69,136 | -0.123631488643147 | 8.18294999e-7 | 6.881880533724705 | 1.73436579e-8 |
| 5 | 138,272 | -0.123632100289336 | 2.04573690e-7 | 6.881880523258413 | 6.87736570e-9 |

χ 차이의 실제 `log2(error_h/error_h/2)`는 **2.000006745 / 2.000001686 / 2.000000422**다. 2차 수렴을 실행 전에 강제하지 않았다. Rmin 오차도 감소했지만 chord minimum과 step phase의 영향 때문에 같은 비율을 가정하지 않는다. 저장 끝점 최소 반경도 JSON에 따로 남겼다. chord minimum은 이산 drift 선분의 최소이며 연속 전환점을 그대로 측정하는 장치는 아니다.

| dt | 출구 운동량 방향(rad) | 모든 저장 상태 max energy 변화/De | max L 변화(a.u.) |
|---:|---:|---:|---:|
| 40 | 2.394339493156541 | 7.84810118e-7 | 5.52604e-58 |
| 20 | 2.394329706746706 | 1.96202314e-7 | 3.58446e-58 |
| 10 | 2.394327260158410 | 4.90505622e-8 | 1.15001e-57 |
| 5 | 2.394326648512221 | 1.22626426e-8 | 1.02057e-57 |

에너지 변동도 dt가 절반일 때 약 1/4로 감소했다. 원래 A40의 최대 변동/De는 **7.84810129e-7**, max L 변화는 **1.42766e-12 a.u.**다. 연속 기준 H,L은 일정하다. HP-KDK의 중심력 kick/drift는 정확 실수라면 L을 보존하며, 위 잔차는 유한 arithmetic의 관측이다. 에너지와 L을 보정하지 않았다.

## 6. 검증·보존·비용

관련 명령:

```text
python -m pytest tests/test_c1b1_o1_diagnostic.py tests/test_c1b1_o1.py tests/test_c1b1_replay.py tests/test_c1b1_two_atom.py tests/test_c1b1_canonical_state.py tests/test_c1a_freeze.py tests/test_body_contract_freeze.py -q --junitxml=runs/c1b1_o1_cause_isolation_20261001_v1/related_tests.xml
```

**140 passed + 1 strict xfailed, 실제 skip 0, failures/errors 0, exit 0, 37.33s.** 신규 진단 시험은 17개다. 자유 궤도·손계산 harmonic KDK·시간 역행·analytic force 대 수치 미분·원인 분리 분기·미수렴 차단·정확 raw 환원·증거 변조·출구 반경 회귀를 포함한다. 1 xfailed는 기존 binary64 absolute-position 탈락 사유 보존이다. 이번 관련 실행에 warnings는 없었지만 이전 FULL의 cp949 경고를 해결한 것은 아니다.
문서 정리 후 신규 진단+body contract 동결 시험도 **20 passed, 0.59s, exit 0**으로 완료했다. 봉인한 진단 소스는 실행·관련 시험 이후 변경하지 않았다.

수치 기준을 바꾼 mutant를 메모리에서 별도로 compile해 다섯 결함을 검사했다: 마지막 half-kick 누락, 첫 kick 배가, drift의 mass factor 오류, 분산항 derivative 부호 반전, retardation derivative 누락. **5/5 잡힘**. sealed 파일을 수정하지 않았으며 각 결함에 대한 손계산/수치 미분 시험은 신규 시험 파일에 남겼다. 이는 제한된 결함 검출 점검이지 완전성 증명은 아니다.

다섯 trajectory의 모든 **276,549 stored state(276,544 step + 각 초기 상태)**를 압축 기록에서 다시 읽어 index 연속성·finite 값·초기 raw·최종 q,p·전체 chord min·전체 sweep을 재검사했다. 최대 재관측 차이는 40자리 run에서 sweep 약 1.104e-39 rad였고, 60자리 run에서도 기준 안이었다. 에너지를 두 번째 force 구현으로 다시 전수 검사한 것은 아니다. all-state 에너지는 진단 계산 중 매 저장 상태에서 계산했다.

| 실행 | CPU(s) | wall(s) |
|---|---:|---:|
| dt40, 40자리 | 21.453125 | 21.533314 |
| dt40, 60자리 | 28.218750 | 28.359743 |
| dt20, 60자리 | 45.468750 | 45.593633 |
| dt10, 60자리 | 89.609375 | 89.810292 |
| dt5, 60자리 | 180.125000 | 180.571740 |
| 합계 | **364.875000** | **365.868724(6.10분)** |

위 시간은 trajectory 구성·전 상태 관측·압축 기록·trace hash에 대한 값이다. setup·기존 증거 검사·짧은 출구 적분·시험·보고·재관측 비용은 별도이며 전체 작업 wall이라고 쓰지 않는다. 원격 임대/과금은 없다. 압축 trajectory 5개의 합은 **32,566,739 bytes**다.

**LOCAL FULL 생략 / 관련 시험으로 대체.** 새 관측 분석 package·시험·문서만 추가했고 기존 실행 코드·공용 계산·fixture·핵심 계약을 수정하지 않았다. 기존 protected 파일 **134개**, 봉인한 새 진단/시험/프로토콜 **5개**, 기존 증거 **97개** 해시가 일치한다. LOCAL FULL 기준선은 갱신하지 않는다. 이전 O-1 단계의 3501 passed+1 xfailed FULL을 이번에 새로 실행한 것으로 보고하지 않는다.

원본은 `runs/c1b1_o1_cause_isolation_20261001_v1/`에 별도 보존했다. Git 밖이므로 JSON 요약과 Git 전달만으로 full traces를 전달한 것으로 주장하지 않는다. seal payload SHA-256은 **73bc45e98536ace2347c86a2906265d1f6a266c6a90bd12da6fc1e3f23f61844**다. 원본 기존 O-1 봉인과 DISAGREE 증거는 그대로다.

## 7. 구상 대조·한계·다음 판단

자동 시험과 별도로 요구사항과 데이터 흐름을 대조했다. 동일 raw에서 별도 arithmetic KDK를 만들고, dt40 분리 판정을 먼저 보존한 뒤 축소 dt를 실행했다. 진단은 A를 수정하지 않았고 관찰 자료만 추가했다. 이는 작성자의 설계 대조이며 다른 사람/모델의 독립 감사라고 주장하지 않는다.

관측된 차이와 dt 축소 결과는 시간 이산화 후보를 강하게 지지한다. 그러나 한 개 unsupported 입력의 finite-outlet numerical diagnostic이며 전체 D_valid·orbit boundary·장기 궤적·새 물리의 정확성을 인증하지 않는다. dt20/10/5는 60자리 한 번씩 실행했고, 이 축소 dt들 자체를 다시 40/80자리로 재적분하지 않았다. dt40의 arithmetic 안정 시험·작은 L 잔차·출구 보정 적분의 error estimate를 보고하되 이 한계를 숨기지 않는다. 출구 보정도 interval-certified error bound가 아니다.

새 physical counterexample는 추가 발견되지 않았고, 기존 불일치 표본만 원인 조사했다. 예상 밖 현상은 봉인 전 진단의 표시 반경 혼용 오류 한 건이며, 원본 불일치로 세지 않는다. 남은 것은 production 정확도 정책의 **별도 설계자 판단**이다: 전체 dt 축소, 영역별 substep, adaptive timestep, 현재 D_valid 유지의 정확도·비용·검증 복잡도를 이후 설계 단계에서 비교할 수 있다. 이번 작업에서는 설계·구현을 시작하지 않았다.

Energy Bound v0 APPROVED / ④-Liveness NotCertified / ④-Safety Conditional / A-EV unresolved / Production Replay Verifier V1 APPROVED / O-1 STOPPED·NOT PASSED 유지. O-3, A-EV, native J, adaptive timestep, production substep, snap, 보존 보정, fixed-point 형식 변경, D_valid 변경, 새 물리·일반 아키텍처 작업 없음. 이번 commit/push 없음.

변경 파일은 새 `c1b1_o1_diagnostic/{__init__,kdk,study}.py`, 신규 시험, protocol/seal/results/본 보고서와 상태·맵·문서 안내·결함 검출 기록의 문서뿐이다. 최종 Git/해시/링크 확인은 별도 final_integrity.json에 남긴다.
