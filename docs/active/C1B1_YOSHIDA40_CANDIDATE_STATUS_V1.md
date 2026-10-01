# C1-B1 Yoshida40 후보 보존 및 상태 V1

2026-10-01 설계자 결정. 이번 단계는 후보 보존과 문서 정리만 수행한다. 새 수치 실험·production 구현·추가 최적화는 수행하지 않는다. 시작 HEAD, origin/master 및 직접 조회한 원격 master는 `9e794a8cda0a9bcef13631f2cf49a20fa20caef5`; 시작 clean, ahead/behind 0/0이다.

## 후보 상태와 증거 등급

Yoshida4 outer `dt=40`의 현재 상태를 다음으로 고정한다.

```text
VALIDATED NUMERICAL CANDIDATE
NOT PRODUCTION
NOT FORMALLY CERTIFIED
```

정확한 증거 등급은 다음과 같다.

- implemented
- numerically validated on sealed C1-B1 O-1 panel
- cost benchmarked locally
- not production
- not formally certified

여기서 panel은 봉인된 기존 9개 Ar-Ar 입력을 뜻한다. 영역 전체나 A 전체를 검증했다는 뜻이 아니며, production A의 O-1 통과 또는 CONFIRMED history의 의미 변경도 아니다. 후보를 폐기하지 않고 재사용 가능한 연구 자산으로 보존하며 production 승격은 보류한다.

## 기존 결과 및 비용 판정의 의미

아래 값은 [완료된 로컬 비용 비교](C1B1_KDK20_YOSHIDA40_COST_LOCAL_V1.md)와 [기존 수치 JSON](C1B1_KDK20_YOSHIDA40_COST_LOCAL_RESULTS_V1.json)을 인용한 것이다. 이번 정리에서 재계산하거나 재측정하지 않았다.

| 항목 | KDK20 | Yoshida40 |
|---|---:|---:|
| 기존 9개 입력 관측 기준 | 9/9 PASS | 9/9 PASS |
| boundary_pass 산란각 오차 rad | 3.273184e-6 | 6.109620e-11 |
| boundary_pass median wall s | 48.984 | 69.036 |
| 9개 합계 CPU s | 297.625 | 415.546875 |
| 9개 합계 wall s | 301.431 | 436.888 |

기존 benchmark 판정 `YOSHIDA_ACCURATE_BUT_COSTLIER`(B)를 유지한다. 총 CPU는 KDK20의 약 1.3962배, wall은 약 1.4494배다. 문제 입력의 산란각 오차는 Yoshida40이 약 5만 배 작았다. 이는 그 입력의 각도 비교이며, 모든 관측량에서 같은 개선 비율을 보인다는 뜻은 아니다. 최접근 거리 오차는 모든 입력에서 Yoshida가 더 작지 않았다.

Yoshida40은 실패한 방법이 아니다. 현재 봉인된 panel의 `1e-5 rad` 수준 관측 요구에서는 KDK20도 기준을 만족하므로, 설계자는 Yoshida의 추가 정확도가 현재 비용을 정당화하지 못한다고 판단해 production 채택을 보류한다. 이 선택을 production KDK dt=40 자체의 정확도 통과로 해석하지 않는다.

로컬 비교는 같은 60자리·물리/초기조건·observer·저장 정책·CPU affinity에서 수행했다. 다른 로컬 부하는 통제하지 않았고 panel은 방법별 1회였다. 과거 원격 kernel 비용과 로컬 전체 비용은 별도 측정이며 합산하지 않는다. 상세 측정 한계는 원본 보고서에 보존한다.

## 재검토 조건

1. **관측 정확도 요구가 더 엄격해질 때:** 예를 들어 observable tolerance가 `1e-5 rad`보다 훨씬 작아지면 요구 오차와 비교 기준을 실행 전에 선언하고 Yoshida40을 다시 평가한다. 현재 문제 입력의 높은 정확도만으로 새 요구를 자동 충족한다고 승인하지 않는다.
2. **KDK timestep 축소 비용이 커질 때:** 향후 연구에서 KDK dt가 `20 → 10 → 5 → 2.5` 등으로 줄어야 한다면 비용 관계가 달라질 수 있으므로, 같은 입력·정확도 요구·환경·관측 정책으로 재비교한다. 이 단계에서는 timestep을 바꾸지 않는다.
3. **고정밀 reference trajectory가 필요할 때:** 독립 수치 reference, 진단용 고정밀 궤적, 수치 비교 연구에 활용할 후보로 보존한다. 적용 범위와 코드 독립성·정밀도 수렴·관측 오차를 별도 확인해야 하며, 현재 증거를 넘어 reference 역할을 자동 승인하지 않는다.

## 남아 있는 위험

Yoshida4에는 negative internal stage가 있다. 내부 drift가 음의 시간 방향으로 진행하므로 outer endpoint만 검사해서 내부 경로의 안전성을 보장할 수 없다. 현재 시험과 봉인된 panel의 내부 chord 검사는 유용한 수치 증거이지만 전체 영역 formal proof는 아니다.

향후 `r_min` 경계, hard domain, many-body, 충돌이 많은 환경, 화학 상호작용, 불연속 또는 조건부 모델에는 별도 검증이 필요하다. C1-B1의 9/9 성공을 A 전체의 안전성으로 일반화하지 않는다. 이 위험은 후보 보존으로 해소되거나 승인되지 않는다.

## 보존 자산과 원본 경로

기존 자산은 삭제·이동·덮어쓰기 없이 유지한다. 아래 목록은 관련 증거로 가는 입구이며 각 보고서가 연결하는 JSON·seal·실행 로그도 함께 보존한다.

| 자산 | 기존 경로 |
|---|---|
| 후보 구현·독립 수치 harness | [methods.py](../../c1b1_integrator_benchmark/methods.py), [study.py](../../c1b1_integrator_benchmark/study.py) |
| 전체 비용 harness·Windows adapter | [c1b1_cost_benchmark.py](../../c1b1_cost_benchmark.py), [c1b1_cost_local.py](../../tools/c1b1_cost_local.py) |
| 대수·mutation·negative-stage 시험 | [test_c1b1_integrator_benchmark.py](../../tests/test_c1b1_integrator_benchmark.py) |
| 비용 판정·출력·원본 보존·adapter 시험 | [test_c1b1_cost_benchmark.py](../../tests/test_c1b1_cost_benchmark.py), [test_c1b1_cost_local.py](../../tests/test_c1b1_cost_local.py) |
| sealed coefficients·입력·최초 계획 | [실행 seal](C1B1_DT40_INTEGRATOR_BENCHMARK_SEAL_V1.json), [protocol](C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md) |
| 이전 Vast 수치 결과·portable deployment | [배포 보고서](C1B1_DT40_PORTABLE_DEPLOYMENT_V1.md), [수치 JSON](C1B1_DT40_PORTABLE_RESULTS_V2.json) |
| 최초 Vast 실패·SSH 재개 실패 | [최초 실패](C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md), [SSH 재개 기록](C1B1_DT40_INTEGRATOR_BENCHMARK_SSH_RESUME_V1.md) |
| 비용 비교 Vast 배포 실패·준비 | [실패 보고서](C1B1_KDK20_YOSHIDA40_COST_V1.md), [결과 JSON](C1B1_KDK20_YOSHIDA40_COST_RESULTS_V1.json), [portable preflight](C1B1_KDK20_YOSHIDA40_COST_PREFLIGHT_V3.json) |
| 비용 비교 seal V1/V2/V3 | [V1](C1B1_KDK20_YOSHIDA40_COST_SEAL_V1.json), [V2](C1B1_KDK20_YOSHIDA40_COST_SEAL_V2.json), [V3](C1B1_KDK20_YOSHIDA40_COST_SEAL_V3.json) |
| 로컬 비용·입력·결과·adapter seal | [로컬 보고서](C1B1_KDK20_YOSHIDA40_COST_LOCAL_V1.md), [전체 JSON](C1B1_KDK20_YOSHIDA40_COST_LOCAL_RESULTS_V1.json), [로컬 seal](C1B1_KDK20_YOSHIDA40_COST_LOCAL_SEAL_V1.json) |

Git 밖의 기존 원본은 각 보고서에 기록된 `runs/c1b1_dt40_portable_v2/`, `runs/c1b1_kdk20_yoshida40_cost_v1/`, `runs/c1b1_cost_deployment_v2/`, `runs/c1b1_cost_deployment_v3/`, `runs/c1b1_cost_local_v1/` 경로 그대로 유지한다. 실패한 원격 시도도 history다. 이번 단계에서는 새 실행 폴더에 관련 시험 로그만 기록한다.

## production 및 Gate 유지

production KDK·production dt=40·D_valid·O-1 판정·replay verifier·Energy Bound·④-Liveness·④-Safety·A-EV·fixed-point format·physical constants·potential·r_min을 변경하지 않는다.

```text
Energy Bound v0 = APPROVED
④-Liveness = NotCertified
④-Safety = Conditional
A-EV = unresolved
Production Replay Verifier V1 = APPROVED
O-1 = STOPPED / NOT PASSED
TIME_DISCRETIZATION_SUPPORTED = numerical diagnostic
```

production 통합·추가 최적화·Chin 연구 재개·새 integrator 탐색·adaptive/substep production·force 최적화·Vast 계산·O-3·A-EV·native J·새 물리는 이번 단계에서 착수하지 않는다.

## 이번 정리의 검증

문서만 변경하며 기존 구현·시험·seal·JSON 결과 및 production/frozen/common source는 유지한다. 기존 단위 시험을 새로 실행해 **27 passed / failure 0 / error 0 / skip 0, 0.62초**를 확인했다. 명령은 `python -m pytest tests/test_c1b1_integrator_benchmark.py tests/test_c1b1_cost_benchmark.py tests/test_c1b1_cost_local.py -q --junitxml=runs/c1b1_yoshida40_candidate_status_v1/related_tests.xml`이다. 대수·mutation·negative-stage·비용 판정·원본 보존·실제 Windows telemetry 회귀 검사이며 Chin 관련 기존 단위 검사도 포함한다. Chin 연구를 재개하거나 장시간 Ar-Ar 궤적·비용 benchmark를 재실행한 것은 아니다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 설계자 요청 10절에 따라 문서와 후보 상태만 정리하며 핵심 실행 코드·계약·fixture를 변경하지 않는다. 공식 LOCAL FULL 기준선은 갱신하지 않는다. commit/push 없음.

기존 로컬 결과/log 85개 SHA-256을 다시 대조해 모두 일치했고, 이 문서의 링크 24개가 실제 파일을 가리킴을 확인했다. Git 변경 목록은 Markdown 5개뿐이다. 종료 HEAD 및 origin/master는 시작과 같은 `9e794a8cda0a9bcef13631f2cf49a20fa20caef5`, ahead/behind 0/0이며 문서 변경으로 dirty다. commit/push 없음. 자동 시험과 별도로 후보 보존·production 승격 보류·재검토 조건·미해결 위험·기존 Gate 유지가 설계자 요청과 일치하는지 확인했다.

Yoshida4 outer dt=40은 C1-B1의 봉인된 9개 O-1 입력에서 높은 수치 정확도를 보인 재사용 가능한 후보이며, 현재 구현에서는 KDK20보다 약 40~45% 높은 실행 비용과 negative internal stage 위험 때문에 production 채택은 보류한다. 향후 더 엄격한 관측 오차 요구 또는 KDK timestep 축소 비용 증가 시 재평가한다.
