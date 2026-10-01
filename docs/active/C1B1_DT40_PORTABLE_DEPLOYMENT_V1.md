# dt40 비교 — 플랫폼 독립 배포와 재개

2026-10-01. 시작 HEAD/실제 origin/master `130df0d4cf419e349888fe0138d7d3cfc14b8b72`, ahead/behind 0/0. 이전 재개 기록의 문서 변경은 보존했다. 사용자의 이번 지시에 따라 서버 시작 전에 패키징을 로컬에서 검증했다. 앞선 실패 원본·봉인·O-1 STOP 판정을 유지한다.

`code/`는 실행 코드, `reference/ar2_lang2024/S2_ar2_pot.f90`는 공개 원문이다. 데이터 경로는 실행 코드 위치를 기준으로 찾는다. Linux에 Windows drive alias를 만들지 않는다. 원래 272개 원본을 SHA-256 동일하게 보존한다. 실행용 경로 수정본 3개·별도 실행 봉인·패키지 checker를 더해 manifest에는 277개 객체가 있다. 역사 소스는 실행되지 않는 evidence 폴더에 보존한다.

수정은 배포 snapshot의 SOURCE 두 곳과 SEAL 위치 한 곳뿐이다. 세 위치 assignment를 제외한 AST는 동일하며, 부모와 새 실행 봉인의 payload는 source hashes 외에 동일하다. 계수·질량·PES 원문·초기 raw·연속 기준·dt40·오차/비용/정밀도 기준·9-input 순서는 그대로다. 저장소의 기존 물리/공용/수치 실행 코드는 수정하지 않았다. 새 패키징·원격 bootstrap·단일 노드 controller와 시험만 추가했다.

[실행 전 사전 검사](C1B1_DT40_PORTABLE_PREFLIGHT_V1.json): 새 폴더에 실제 압축 해제, 원본 272/272 및 객체 277/277 해시 일치, 활성 Python 코드 compile 및 drive-path 검사, 임의 cwd의 별도 Python에서 공개 원문 parse/실행 봉인 load 성공. reference hash `a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049`. package SHA `352b63b7c8b6cb42eead2d2fa4c81e462cb86665773a55426bfffdded070d30d`, 실행 payload SHA `7df664a9b5ea52f0e45120d90849fad4cd48032e41243b11025f14e5faaebb46`, 부모 payload SHA `bbe64ed6ad96adf3654a13afea8b9ebec35743243d7fb91f1b7f268edd370232`.

로컬 관련 시험 `tests/test_c1b1_dt40_package.py` + `tests/test_c1b1_integrator_benchmark.py`: **22 passed, 15.19초, failure/error/skip 0, exit 0**. 경로 탈출·절대 경로·변조 파일·수치 AST 변경 거부와 실제 복원/읽기를 확인했다. 로컬 Ar-Ar 궤적 0. 준비 단계 통과가 수치 결과는 아니다.

원격은 기존 5950X 52763629 한 대, API 가격 $0.19111111/hr, GPU 계산 없음. 원격 archive hash→277-object/272-original 검증→resource parse→관련 시험→봉인된 campaign 순서다. 먼저 boundary_pass 두 후보 40/60자리, 생존 후보만 원래 panel. 기존 baseline 궤적을 재생성하지 않는다. 실패도 archive로 회수하고 hash 확인 뒤 즉시 stop한다. 승인 상한 $1/hr·총 $1 유지. 결과는 후속 문단에 별도로 기록한다. commit/push 금지.

## 첫 portable 배포 실패와 수정된 사전 검사

portable v1에서 원격 archive/272-original/277-object 해시 검사와 resource parse는 통과했다. 그러나 관련 시험은 47 passed / 2 failed였다. 원본 역사 봉인의 파일을 evidence 아래 보존했으나 두 역사 시험이 옛 ROOT 아래에서 찾았기 때문이다. 궤적과 cost probe는 실행되지 않았다. 실패 증거 9개를 회수하여 해시 확인했고 노드는 stop 확인했다. 제어 구간 200.563초 × API 가격은 $0.01064717이며 실제 청구액이 아니다. 원본 실패 로그는 `runs/c1b1_dt40_portable_v1/remote_results/deployment_logs/`에 보존한다.

v2는 역사 시험용 pristine 원본 view를 pytest session 임시 폴더에 만든다. 원본 위치를 요구하는 역사 study 두 개의 ROOT/INPUT만 그 view를 사용하고, benchmark 실행 ROOT·물리식·수치 함수는 바꾸지 않는다. campaign은 별도 Python process이므로 이 fixture의 영향을 받지 않는다. 현재 실행 수정은 별도 package checker와 실행 봉인으로 검증한다. 부모 봉인이나 원본 source-binding의 의미를 바꾸지 않는다.

[v2 실행 전 사전 검사](C1B1_DT40_PORTABLE_PREFLIGHT_V2.json): 원본 272/272, 객체 278/278, package SHA `b2ea927b606018018f53a0de427f2c4e03fb3298dc28d96311e4235bb496de14`. 실제 새 폴더에 복원한 코드에서 관련 시험 전체 **49 passed, 2.23초**, failure/error/skip 0. 패키징/benchmark 관련 로컬 시험 **22 passed, 16.15초**, failure/error/skip 0. 시험 뒤 inventory도 다시 일치했다. 로컬 Ar-Ar 궤적 0. 이제 이 v2만 재개한다.

## 원격 수치 결과 — 2026-10-01 portable v2

**최종 C: 전체 실행 비용까지 KDK20과 같거나 더 싼 후보인지는 아직 판정 불가.** 수치 실험은 완료됐다. Yoshida는 9/9 입력의 관측 기준 및 40/60자리 안정성을 만족했다. Chin은 첫 입력의 관측 기준과 정밀도 안정성을 만족했으나 사전 kernel 비용 상한 2배를 넘어 나머지 panel은 실행하지 않았다. 측정한 kernel 비용은 각각 KDK20 두 step의 1.471993배·2.174726배다.

원격 runner의 원문 결론은 `B_KERNEL_COST`이며 그대로 보존했다. 그것은 두 후보 모두 측정한 kernel에서 더 비싸다는 제한된 결론이다. 이 보고서는 동일 노드의 전체 KDK20 CPU/wall이 없는 점 때문에 전체 비용 질문을 C로 남긴다. 정확도/정밀도 불안정 때문에 C인 것은 아니다. 이전 로컬 시간을 원격 시간과 직접 비교해 전체 비용 결론을 만들지 않았다.

[전체 수치·입력·원본·환경·artifact 해시](C1B1_DT40_PORTABLE_RESULTS_V2.json). 로컬 회수 원문은 `runs/c1b1_dt40_portable_v2/remote_results/observations/summary.json`, manifest는 `remote_results/deployment_logs/artifact_manifest.json`이다. 새 Ar-Ar 궤적 20회(각 정밀도 별도), outer step 합 244,266, 기록된 trajectory CPU 합 791.010654초. 기존 KDK/연속 기준 궤적 재생성 0.

### 문제 입력: E=0.5 De, rho=-0.001, b=11.707286169880804 bohr

energy는 저장된 outer state의 max |ΔH|/De, L은 max |ΔL|의 원자 단위다. CPU/wall은 궤적 및 관측 계측이며 endpoint 보정은 별도다. KDK 행의 CPU/wall은 **이전 로컬 역사값**, 후보는 **이번 원격 값**으로 하드웨어가 달라 직접 속도비로 쓰지 않는다. baseline의 force 횟수는 원래 계측되지 않아 N/A다.

| 방법 | outer dt | χ 오차 rad | force eval | CPU s | wall s | energy | L | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| HP-KDK40 (역사) | 40 | 1.309280e-05 | N/A | 28.219 | 28.360 | 7.848101e-07 | 5.526038e-58 | 각도 기준 초과 |
| HP-KDK20 (역사) | 20 | 3.273184e-06 | N/A | 45.469 | 45.594 | 1.962023e-07 | 3.584457e-58 | 각도 기준 만족 |
| yoshida4 | 40 | 6.109620e-11 | 51,853 | 54.645 | 54.658 | 1.587108e-11 | 9.160278e-58 | 관측 PASS / PROMISING_PARETO |
| chin4a | 40 | 5.256011e-13 | 34,569 | 76.788 | 76.806 | 8.828761e-13 | 3.136400e-58 | 관측 PASS / REJECT_COST |

두 후보 outer step은 각각 17,284개다. Chin은 force 외에 derivative PES 평가 34,568회, gradient vector 17,284회가 추가된다. 이 비용은 force 수에 숨기지 않았다. endpoint PES 평가는 각각 438회이며 별도 CPU는 Yoshida 0.410016초 / Chin 0.397733초다. Peak RSS는 22,720 / 22,960 KiB다.

Yoshida χ=-0.123632304110323273989764224761924458855026567754704910652297, 출구 방향=2.39432644469123322976067042679722664841162656775291340585499 rad, 내부 chord Rmin=6.88188052010138662401410790538825945813903509616335614068698 bohr, Rmin 차이=3.720340e-09 bohr. Chin χ=-0.12363230417079583781990693553254515445423539079085934193276, 출구 방향=2.39432644463076066593052771602660595281241774471675897457452 rad, 내부 chord Rmin=6.88188036154429661040088672781440186769694843210105627768179 bohr, Rmin 차이=1.548368e-07 bohr. Chin은 각도가 더 정확하지만 Rmin 차이는 Yoshida보다 크다. 둘 다 사전 Rmin 상대 오차 기준 안에 있다.

최초 outbound outer step의 출구 반경 overshoot에 맞춰 이전 연속 해의 짧은 구간만 보정했다. 예를 들어 Yoshida의 matched continuous χ는 -0.12363230417141947716469256840534879040981279330086376925208 rad다. 원래 유한 출구 χ≈-0.123632348441596061에 대한 방향 보정은 약 4.4270e-8 rad다. 후보 χ와 원래 다른 출구 반경의 χ를 그대로 빼지 않았다. 원래 reference는 변경하지 않았다.

### 같은 노드·같은 CPU 0에서 봉인된 1024-state kernel 측정

60자리 / 동일 analytic Lang evaluator / 3회 반복 median. 이전 force cache 준비는 측정 밖에 있고, 각 갱신과 chord 검사를 측정했다. KDK20 한 step median을 2배 하여 outer40 구간 비용 기준으로 썼다. 연속 궤적이나 새 KDK20 산란각을 생성하지 않았다.

| 방법 | timed force / derivative (1024개) | median CPU s | median wall s | CPU max/min | KDK20 두 step 대비 |
|---|---:|---:|---:|---:|---:|
| kdk20 | 1024 / 0 | 0.962335 | 0.962565 | 1.029852 | 1 step 측정; 기준은 그 2배 |
| yoshida4 | 3072 / 0 | 2.833100 | 2.833787 | 1.015161 | 1.4719931322974258 |
| chin4a | 2048 / 2048 | 4.185629 | 4.186595 | 1.003828 | 2.174726246782087 |

세 방법 모두 max/min 1.2 상한 안에서 비용 측정이 안정됐다. boundary_pass에서 KDK20 대비 각도 오차 개선은 Yoshida 53,574.26배, Chin 6,227,505.32배다. 이 정확도 이득이 더 싼 전체 실행을 뜻하지 않는다.

### 기존 9-input panel: Yoshida 60자리

KDK40은 기존 production A의 각 입력별 연속 기준 오차, Yoshida는 자기 실제 출구 반경에 맞춘 연속 기준 오차다. 같은 initial raw와 Hamiltonian을 사용했다. 공식 A history는 REPLAY_VERIFIED/CONFIRMED인 기존 원본을 재사용했고 후보 궤적을 CONFIRMED로 승격하지 않았다.

| 입력 | E/De | b bohr | rho | 기존 A40 χ 오차 | Yoshida χ/방향 오차 | Rmin 차이 bohr | 관측/정밀도 |
|---|---:|---:|---:|---:|---:|---:|---|
| ordinary | 0.5 | 6 | — | 1.129995e-06 | 2.590173e-10 / 2.590173e-10 | 2.366964e-09 | PASS / 안정 |
| small_b | 0.5 | 0.1 | — | 2.292370e-08 | 6.167665e-12 / 6.167665e-12 | 1.237330e-06 | PASS / 안정 |
| large_b | 0.5 | 14 | — | 1.992059e-09 | 9.775681e-16 / 9.775681e-16 | 8.114855e-08 | PASS / 안정 |
| low_energy | 0.01 | 7 | — | 1.878672e-07 | 4.148173e-11 / 4.148173e-11 | 7.597670e-07 | PASS / 안정 |
| high_energy | 9.9 | 0 | — | 0.000000e+00 | 0.000000e+00 / 0.000000e+00 | 2.641506e-06 | PASS / 안정 |
| s4d_passing | 0.15 | 14.032171609409 | -0.005 | 2.988322e-07 | 1.630846e-10 / 1.630846e-10 | 6.357344e-07 | PASS / 안정 |
| s4d_no_wall | 1 | 10 | — | 5.983088e-07 | 3.106115e-11 / 3.106115e-11 | 3.949369e-11 | PASS / 안정 |
| boundary_reflect | 0.5 | 11.7307241802309 | 0.001 | 5.904717e-06 | 3.082769e-12 / 3.082769e-12 | 9.030730e-07 | PASS / 안정 |
| boundary_pass | 0.5 | 11.7072861698808 | -0.001 | 1.309282e-05 | 6.109620e-11 / 6.109620e-11 | 3.720340e-09 | PASS / 안정 |

| 입력 | outer steps | force eval | CPU s | wall s | max energy/De | max ΔL | Peak KiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| ordinary | 6163 | 18490 | 18.858 | 18.863 | 1.014246e-09 | 9.956824e-59 | 24616 |
| small_b | 5598 | 16795 | 17.313 | 17.317 | 2.024969e-09 | 6.067440e-60 | 24216 |
| large_b | 6817 | 20452 | 22.402 | 22.408 | 1.481032e-16 | 4.480571e-58 | 24632 |
| low_energy | 22087 | 66262 | 70.563 | 70.579 | 8.716231e-10 | 1.151258e-58 | 24480 |
| high_energy | 1498 | 4495 | 4.617 | 4.618 | 2.160325e-07 | 0.000000e+00 | 24636 |
| s4d_passing | 26451 | 79354 | 80.450 | 80.461 | 2.235483e-10 | 4.032514e-58 | 24488 |
| s4d_no_wall | 7221 | 21664 | 22.430 | 22.376 | 3.961102e-12 | 4.928628e-58 | 24648 |
| boundary_reflect | 11730 | 35191 | 36.240 | 36.185 | 5.726731e-15 | 7.268482e-58 | 24496 |
| boundary_pass | 17284 | 51853 | 54.645 | 54.658 | 1.587108e-11 | 9.160278e-58 | 22720 |

40→60자리 변화의 전체 관측/출구 성분 최대값은 8.6771015e-36이며 봉인된 1e-20 안정 기준 안에 있다. panel 최악 각도/방향 차이는 ordinary의 2.59017275e-10 rad, 최악 Rmin 차이는 high_energy의 2.64150563e-6 bohr다. high_energy b=0의 각도 차이 0은 이 대칭 표본의 결과이며 위치까지 오차가 0이라는 뜻이 아니다. 모든 내부 drift chord는 r>=2.4 검사를 만족했고 panel 최저 Rmin은 약 5.50926098 bohr다.

### 구조, 공유 코드 및 확장 한계

Yoshida: 고정된 symmetric 4차 composition의 4 kick/3 drift, 인접 force cache 공유. 내부 음수 drift가 있으며 h=40에서 -68.09657535677261 a.u.다. 원래 프로토콜의 근사 수치 -68.0976568은 오기이며 실제 봉인된 대수 계수/코드는 변경하지 않았다. 이번 chord 검사 통과가 향후 전체 domain 안전 증명이나 production 채택은 아니다.

Chin 4A: forward 2 drift와 3 kick, middle force에 mass-weighted force-gradient. 현재 중앙력의 V'V'' 항을 사용하며 mpmath.diff의 추가 PES 호출까지 계측한다. 이 radial gradient 구현은 Ar-Ar 2-body 전용이다. many-body는 일반 mass-weighted Hessian-force product와 별도 계약/검증이 필요하며 구현하지 않았다.

공유: 기존 독립 Lang analytic PES/공개 원문 파서, mass/units/retardation/Hamiltonian, 정확 initial raw, 연속 reference와 endpoint quadrature, 비용 probe에만 기존 diagnostic KDK20 kernel. 비공유: production A의 step/kick/drift/force/rounding 구현 및 replay verifier를 후보 계산기로 사용하는 경로. 두 후보의 갱신은 새 methods.py에 있고 기존 production은 수정하지 않았다. force evaluator 최적화·상태 snap·보존량 보정·계수 tuning은 없다.

### 검증, 비용, 종료 및 상태

원격 AMD Ryzen 9 5950X 16-core, API effective vCPU 32, RAM 64,231 MB. affinity 0/1/2/3은 서로 다른 물리 core로 lscpu에서 확인했다. Python 3.12.3 / mpmath 1.3.0 Python backend, GPU 계산 없음. API 가격 $0.191111111/hr. 시작 2026-10-01T06:54:14Z / 종료 확인 2026-10-01T07:01:48Z, 제어 구간 454.157000초. 가격×구간 환산 $0.02410957; portable v1 실패 구간을 포함하면 $0.03475674. 이는 청구서가 아니며 저장/전송 요금을 포함하지 않는다. 이전 alias/제어 실패의 비용도 별도 역사 기록에 보존했다.

원격 exit 0, 결과/로그 52개 회수·SHA-256 일치. archive SHA e3832f9d8763ca20b42d8587915d3045e2ede5a62146099acb70e9ce1d4483d6. 52763629 종료 확인 및 기존 네 노드 모두 exited/stopped 재확인. 서버를 결과 해석 대기로 켜두지 않았다.

신선한 관련 시험: 로컬 57 passed / 18.08초, 실제 복원 패키지 49 passed / 2.23초, 원격 49 passed / 1.45초, 모두 failure/error/skip 0. nested 동일 시험을 합산하여 새로운 고유 시험 개수로 주장하지 않는다. 첫 portable v1의 47 passed / 2 failed 기록은 보존한다. 기존 source 12개·protected 134개 및 O-1 artifact 97개·원인 격리 artifact 27개 모두 현재 로컬 원본 hash가 불변이다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 이번 변경은 새 독립 배포 도구·시험·문서만이다. 기존 실행 코드·공용 물리·동결 계약/fixture는 변경하지 않았다. 배포 snapshot의 위치 assignment 3개는 원본 보존·AST 동등성·별도 실행 봉인과 실제 복원 시험으로 검증했다. 공식 LOCAL FULL 기준선 갱신 없음. 이전 3501 passed + strict xfail은 이번 실행으로 세지 않는다.

구상 일치성 별도 확인: outer40과 같은 물리/초기 raw를 유지하면서 방법만 비교했다. 관측 오차가 작아진 것은 확인했지만 같은/더 싼 전체 실행과 many-body 검증 가능성은 미확인이다. 원래 O-1 STOP을 푸는 작업이 아니며 production 채택하지 않는다.

Energy Bound APPROVED / Liveness NotCertified / Safety Conditional / A-EV unresolved / approved replay verifier / O-1 STOPPED·NOT PASSED / cause TIME_DISCRETIZATION_SUPPORTED 유지. O-3·A-EV·native J·live pipe·rollback·D_valid 재설계·④ 재증명·새 물리 미착수. HEAD와 실제 remote master는 130df0d4cf419e349888fe0138d7d3cfc14b8b72 그대로이며 commit/push 없음.
