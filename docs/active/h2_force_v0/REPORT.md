# Electronic Calculation Stack V0 / H2 Force Vertical Slice V0

**H2_LOCAL_BO_CURVE_SUPPORTED / H2_FORCE_INTERFACE_PILOT_SUPPORTED / NOT CERTIFIED / NOT PRODUCTION APPROVED.**

2026-10-04. 고정 핵 5점의 국소 BO 에너지를 실제 계산하고 diagnostic radial force로 연결했다. 힘 정확도·해석적 힘·정확한 평형 위치·핵 운동·A foundation 인증은 미구현/미승인이다. 전체 구간의 연속성이나 global minimum도 인증하지 않는다. 기존 numerical guard acceptance는 물리 오차 상한이 아니다.

## GIT STATE

실제 작업 HEAD `2cfd4c8b3ec59dd6a525b702486c4cf1e5cdf906`, branch `codex/h2-representation-pilot1`. 시작 tracked tree clean. 기본 체크아웃 master는 별도 `0f7b744cf754450424a63c47f305e0327c5b37c1`이다. 실제 원격 master와 pilot SHA는 요청의 `0f7b744` / `264f588`과 일치했다. 기존 Pilot branch에 새 연구 파일/시험/문서만 추가했다. merge/rebase/push 없음; 최종 local commit은 Git 이력으로 확인한다.

## ELECTRONIC STACK V0 FREEZE STATUS

`ELECTRONIC_CALC_STACK_V0`: 다음 층 개발·탐색·실제 병목 발견용. Gaussian/QZ 기존 FAIL·수치 미해결은 보존한다. V5Z의 R=.4 기존 0.001 Eh 기준 만족은 그 한 점의 역사 결과다. JC B1 R=.4 Pilot SUPPORTED / 목표 만족 / NOT CERTIFIED / NOT PRODUCTION APPROVED는 그대로다. H2SOLV vendor 실행·수렴 관련 감사는 전체 solver 인증이 아니며 B2 independent JC는 NOT IMPLEMENTED다. 미해결 문제 자체는 현재 blocker가 아니며, downstream 결과를 무효화하는 명백한 correctness 반례를 발견하면 STOP한다.

## R=1.2~1.6 ENERGY TABLE

동일 cc-pV5Z raw basis definition, proton2/electron2, clamped nonrelativistic Coulomb, full spatial singlet, spherical AO110/full CI6105, binary64, 1 thread, Cholesky, canonical AO + compact MO integral reuse, unchanged singlet_matrix, LAPACK evr roots0/1. `EBO=Ee+1/R`이며 핵 반발을 한 번만 더했다. SCF·warm start·reference energy·basis 삭제·threshold 완화 없음. 새 worker는 기존 cardinal 경로의 고정 R=.4를 사전 지정 R로 받도록 별도 분석 파일에서 호출한다.

| R (bohr) | BO total E (Eh) | Guard | 내부 계산 wall (s) | fresh process wall (s) | peak RSS (MiB) |
|---:|---:|---|---:|---:|---:|
| 1.2 | -1.1646609186125532 | ACCEPTED | 27.893 | 28.81 | 3873.95 |
| 1.3 | -1.1720847311717035 | ACCEPTED | 25.698 | 26.26 | 3874.43 |
| 1.4 | -1.1742226699153213 | ACCEPTED | 28.171 | 29.44 | 3874.45 |
| 1.5 | -1.1726087635888724 | ACCEPTED | 28.560 | 29.99 | 3874.53 |
| 1.6 | -1.1683411708716580 | ACCEPTED | 25.617 | 27.05 | 3874.39 |

## GUARD RESULTS

기존 필수 guard를 그대로 적용했다. Norm 열은 `abs(v.T @ v - 1)`이다. 변환 h/ERI 대칭 진단은 point JSON에 있으며 기존 필수 guard와 구별한다.

| R | Smin (>1e-10) | orth L2 (<=1e-10) | H asym max (<=1e-10) | eigen residual L2 (<=1e-9) | norm error (<=1e-10) |
|---:|---:|---:|---:|---:|---:|
| 1.2 | 3.173531e-05 | 2.548266e-12 | 8.881784e-16 | 3.160150e-14 | 2.220446e-16 |
| 1.3 | 3.819697e-05 | 1.553056e-12 | 8.881784e-16 | 2.621891e-14 | 4.440892e-16 |
| 1.4 | 4.565134e-05 | 1.274997e-12 | 8.881784e-16 | 2.575279e-14 | 2.220446e-16 |
| 1.5 | 5.428899e-05 | 1.190419e-12 | 1.776357e-15 | 3.294089e-14 | 1.110223e-16 |
| 1.6 | 6.417441e-05 | 2.352375e-12 | 8.881784e-16 | 1.755527e-14 | 4.440892e-16 |

## LOCAL MINIMUM CHECK / FINITE-DIFFERENCE FORCE

`E(1.4)<E(1.3)` true, `E(1.4)<E(1.5)` true. 이것은 지정된 0.1 bohr 표본의 local minimum 구조다. 정확한 equilibrium 위치나 global minimum 주장이 아니다.

`F(R)=-(E(R+0.1)-E(R-0.1))/0.2`. 양수는 R 증가 방향, 음수는 R 감소 방향인 generalized radial force다. 개별 핵의 Cartesian force evaluator는 없다. 저장 binary64 에너지를 정확한 분수로 해석해 차분하고 최종 표시만 float로 변환했다. 이 정확 산술은 물리/표현/차분 오차를 제거하지 않는다.

| R (bohr) | F (Eh/bohr) | 판정 |
|---:|---:|---|
| 1.3 | +0.0478087565138408 | R 증가 방향: 조건 만족 |
| 1.4 | +0.0026201620858446 | 측정값만 기록; 새 0 근처 tolerance 없음 |
| 1.5 | -0.0294074952183165 | R 감소 방향: 조건 만족 |

## RUNTIME / MEMORY

5점 outer execution wall **144.757s**, GNU time fresh process wall 합 **141.55s**, 최대 process RSS **3.783722 GiB**. Outer wall은 순차 WSL 시작·기록을 포함하며 준비/전후 provenance hash 검사/시험은 제외한다. RSS는 GNU time이 측정한 단일 계산 process의 최대 상주 메모리이며 전체 호스트 동시 메모리가 아니다. 설치·basis 개발 비용은 미측정. 한 host에서 1회 측정했고 다른 local 부하는 통제하지 않았다.
정적 한 점 fresh process는 26.26~29.99s였다. 실제 다음 핵 운동의 시간/메모리 예산이 지정되지 않았으므로 dynamics 병목 또는 진행 불가를 판정하지 않았다. 반복 step·다전자 scaling·캐시 성능은 NOT_EVALUATED다.

## ACTUAL BLOCKERS FOUND

이 5점 실행의 필수 guard refusal·local minimum 구조 실패·반대 force sign은 없었다. 별도 jump tolerance를 만들지 않았으며 5표본 사이의 연속성을 인증하지 않았다. 첫 관련 시험의 3 failures/3 errors는 historical raw 자료가 이 checkout에 없고 과거 source seal과 checkout bytes가 다르기 때문이었다. 원본 자료가 있는 parent checkout에서 과거 35시험을 다시 실행해 PASS했고, 처음 실패 로그/원인은 삭제하지 않았다. 계산기 layer 재조사·JC reference 실행·geometry 추가 없음.

## BACKLOG ITEMS NOT TOUCHED

B2 independent JC, H-He+ indefinite S, General SPD, JC asymmetric intended root, Pachucki 마지막 자리/reference uncertainty, AO/MO rigorous error bounds, H2SOLV 전체 인증, representation generalization, adaptive representation을 재개하지 않았다. 기존 FAIL/UNRESOLVED 및 원본을 보존했다.

## VERIFICATION / CONCEPT ALIGNMENT

실행 전 preflight 88 passed / failure,error,skip0. 실행 후 신규28개(24 synthetic+4capture)를 포함한 현재 관련 **92 passed / failure,error,skip0 (2.75s)**. parent historical **35 passed / failure,error,skip0 (7.18s)**. 서로 다른 시험 파일 범위의 합 127개이며 preflight나 첫 실패 실행의 117개를 중복 합산하지 않는다. 첫 실패 결과는 3 failed / 117 passed / 3 errors로 보존한다.

새 false-acceptance 시험은 guard 초과·NaN/Inf·norm 누락·geometry 중복/불일치·basis/driver contract 혼합·차원 축소·반대 ordering과 force sign을 주입한다. 실제 저장 에너지는 별도 Decimal100 산술에서 중앙 차분과 부호를 다시 확인했다. 이는 작성자의 2차 검증이며 외부 독립기관 감사나 formal proof가 아니다.

자동 시험과 별도로 구상 대조: primary=기존 V5Z, R5점/h 사전 고정, 동일 물리/basis/guard/precision/solver, 모든 수치 accepted 이후 diagnostic force, F1.4 tolerance 없음, 실제 cost 기록, nuclear motion/velocity/mass integration/trajectory/H+H formation/adaptive representation0, JC0, extra geometry0, push0. 모든 요청 범위에 일치했다.

이전 source/checker/raw/증거 **2451 hash bindings 전후 불변**. [사전 봉인](protocol.json), [실행 봉인](execution_seal.json), [전체 결과](results.json), [관련 시험](related_tests.log), [parent 시험](parent_related_tests.log), [초기 실패 로그](initial_related_failure.log). 새 4capture tests는 데이터 취득 이후 추가했으며 energy 생성/설정을 바꾸지 않았다.
`LOCAL FULL 생략 / 관련 시험으로 대체 / 이유`: 새 독립 분석 파일·시험·문서만 추가, 기존 실행 코드·공용 로직·물리식·동결 계약/fixture·해시 고정 소스 변경0. 공식 통합 Gate 종료나 FULL 기준선 갱신을 하지 않았다. 공식 기준선 유지.

읽은 범위: 사용자 첨부 전체, AGENTS/RULES 전체, CURRENT_STATE/REPO_MAP/doc 안내·상태 색인의 관련 부분, 기존 cardinal/reuse/core/solver/guard 구현 전체, JC 보고서·measurement/binding의 필요한 부분. 저장소 전체·제3자 전체 재귀를 새로 감사하지 않았다. 이번 수치는 새로 실행했으며 역사 로그를 fresh 실행으로 세지 않았다.

## FINAL CLASSIFICATION / NEXT STEP

`H2_LOCAL_BO_CURVE_SUPPORTED` / `H2_FORCE_INTERFACE_PILOT_SUPPORTED` / `NOT CERTIFIED` / `NOT PRODUCTION APPROVED`. 이번 범위 완료 후 STOP. 다음 작업 후보는 별도 승인 범위의 아주 작은 핵 운동 1-step이며 이번에는 구현하지 않았다. force error budget·energy consistency·실제 비용은 그 다음 단계에서 다룰 항목이다.
