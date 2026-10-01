# KDK20 vs Yoshida40 로컬 전체 비용 비교 — B

**B. YOSHIDA_ACCURATE_BUT_COSTLIER.** 사용자 지시에 따라 로컬에서 실제 비교를 완료했다. KDK20과 Yoshida40 모두 기존 9개 입력의 관측 기준을 만족했고, Yoshida는 이전 60자리 결과 9개를 재현했다. 하지만 이 구현/관측/저장 정책에서는 Yoshida의 총 CPU가 39.62%, 총 wall이 44.94% 더 높았다. production 채택 여부는 판정하지 않는다.

[로컬 실행 봉인](C1B1_KDK20_YOSHIDA40_COST_LOCAL_SEAL_V1.json), [전체 수치·입력·환경·원본 hash](C1B1_KDK20_YOSHIDA40_COST_LOCAL_RESULTS_V1.json). [이전 Vast 실패](C1B1_KDK20_YOSHIDA40_COST_V1.md)는 보존하며 덮어쓰지 않는다.

## Git 및 실제 실행 환경

시작/종료 HEAD와 실제 remote master는 `2c17350be8f89be5689e0736c08fd6246a668caa`, 시작 clean·ahead/behind 0/0, 종료는 새 adapter/시험/보고서 및 상태 문서로 dirty다. commit/push 없음. Vast 시작/SSH/업로드 없음, 이번 Vast 비용 0.

AMD Ryzen 5 5600 6-core / logical processor 12, Win32_ComputerSystem TotalPhysicalMemory 34,278,981,632 bytes(약 31.93 GiB). Windows 11 build 26200, Python 3.12.7, mpmath 1.3.0 Python backend, GPU 계산 없음. 모든 run은 CPU affinity 11에 새 worker 하나씩 **순차** 실행했다. 사용자 로컬의 다른 작업 부하는 통제하지 않았다.

기존 portable package 원본 272/객체 286을 새 snapshot으로 복원·hash 확인했다. reference는 code/상위 reference/의 프로젝트 경로로 찾으며 D: alias를 도입하지 않았다. benchmark/두 integrator/force/observer/timing 루프의 byte는 이전 봉인 그대로다. 새 Windows adapter만 별도 hash로 봉인했다. 실제 Set/GetProcessAffinityMask 및 GetProcessMemoryInfo PeakWorkingSetSize를 사용한다. 수치 계산기를 흉내내는 OS mock으로 측정하지 않았다.

기존 REMOTE 이름의 permit flag는 사용자 로컬 승인에 따라 호환용으로만 설정했고 실행 origin은 **LOCAL_WINDOWS**로 기록했다. __file__의 자식 launcher 위치만 adapter로 연결했으며 ROOT/입력/SEAL/수치 함수는 바꾸지 않았다. 기존 원격 봉인 또는 history의 의미를 재정의하지 않았다.

## 공정성 및 시간 범위

60자리 / 같은 정확 initial raw / 같은 PES·질량·단위 / 같은 첫 outbound base_radius 출구 조건 / 같은 observer / 모든 outer state 기록 / JSONL / gzip level 9, mtime 0, filename 없음. 실제 출구 반경 overshoot까지 이전 continuous reference의 짧은 구간만 보정한다. 방법의 실제 내부 drift chord를 동일 관측 함수로 감시하고 outer chord도 동일 정책으로 관측한다.

초기 모델 준비·force·integrator/guard·관측 루프·모든 상태 기록·압축 close·trace SHA·endpoint 보정·수치 summary 첫 write가 timer 안이다. Python import·source/seal 검증·worker launch/affinity·최종 timing metadata rewrite·제어 progress는 timer 밖이다. 출력 크기는 gzip trace와 최종 수치 summary 합이다. 양쪽 buffered file write를 사용하며 fsync/durable disk latency를 측정한 것은 아니다.

Warm-up 각 1회는 공식 통계에서 제외했다. 측정 순서 K/Y/Y/K/K/Y 각 3회. panel은 원래 input 순서와 번갈아 method 순서를 유지해 방법별 1회씩이다. 총 26회 = warm-up 2 + single 6 + panel 18. 40/60 재수렴, Chin, 새 입력, rho=-0.0001은 실행하지 않았다.

## Single-input benchmark

문제 입력 E=0.5 De, rho=-0.001, b=11.707286169880804 bohr. force count는 각 run 값이며 세 run에서 같다.

| method | runs | median CPU s | median wall s | force eval | χ error rad |
|---|---:|---:|---:|---:|---:|
| kdk20 | 3 | 48.453125 | 48.984035 | 34,569 | 3.273184e-06 |
| yoshida4 | 3 | 68.125000 | 69.035521 | 51,853 | 6.109620e-11 |

Yoshida/KDK ratio: median CPU **1.405998**, median wall **1.409347**. 1차 SLOWER(>1.10). KDK CPU/wall max/min 1.008125/1.008651, Yoshida 1.016813/1.015337: 모두 사전 1.2 상한 안이다. 최소 시간을 골라 비교하지 않았다.

## 9-input aggregate

| method | total CPU s | total wall s | force eval | accuracy | verdict |
|---|---:|---:|---:|---|---|
| kdk20 | 297.625000 | 301.430784 | 209,701 | 9/9 관측 기준 만족 | baseline |
| yoshida4 | 415.546875 | 436.887645 | 314,556 | 9/9 관측 기준 만족 | B: 정확하지만 더 비쌈 |

| 항목 | KDK20 | Yoshida40 |
|---|---:|---:|
| total outer steps | 209,692 | 104,849 |
| force eval | 209,701 | 314,556 |
| additional derivative eval | 0 | 0 |
| output bytes | 25,054,936 | 12,593,033 |
| whole-worker peak KiB | 81,188 | 81,216 |

총 wall ratio **1.449380**, 총 CPU ratio **1.396210**. 사전 전체 판정 기준에서 둘 다 1.10을 넘어 B다. 9개 각각에서도 Yoshida의 CPU와 wall이 모두 KDK보다 높았다. Yoshida는 outer step·출력 수를 약 절반으로 줄였지만 force/PES 평가가 약 1.5배라 비용 이득을 얻지 못했다. 이것은 이번 실제 구현의 측정 결과이며 수학적으로 모든 Yoshida 구현이 느리다는 정리는 아니다.

## 각 입력 비교

출구 조건을 맞춘 χ 오차. 초기 raw·rational b 및 rho 전체는 JSON에 보존하며 표의 b는 표시용 decimal이다.

| input | E/De | b bohr | rho | K χ error | Y χ error | K CPU/wall s | Y CPU/wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| ordinary | 0.5 | 6 | — | 2.824961e-07 | 2.590173e-10 | 18.328/18.671 | 23.594/23.855 |
| small_b | 0.5 | 0.1 | — | 5.730861e-09 | 6.167665e-12 | 15.625/15.715 | 21.547/21.679 |
| large_b | 0.5 | 14 | — | 4.979744e-10 | 9.775681e-16 | 19.688/19.849 | 26.250/26.414 |
| low_energy | 0.01 | 7 | — | 4.696666e-08 | 4.148173e-11 | 60.328/60.916 | 81.844/82.061 |
| high_energy | 9.9 | 0 | — | 4.356111e-60 | 4.356111e-60 | 5.484/6.800 | 6.734/8.494 |
| s4d_passing | 0.15 | 14.032171609409 | -0.005 | 7.470665e-08 | 1.630846e-10 | 75.391/75.720 | 113.875/131.286 |
| s4d_no_wall | 1 | 10 | — | 1.495773e-07 | 3.106115e-11 | 20.828/20.880 | 28.953/29.159 |
| boundary_reflect | 0.5 | 11.7307241802309 | 0.001 | 1.476186e-06 | 3.082769e-12 | 32.969/33.274 | 46.562/47.071 |
| boundary_pass | 0.5 | 11.7072861698808 | -0.001 | 3.273184e-06 | 6.109620e-11 | 48.984/49.606 | 66.188/66.869 |

| input | K/Y Rmin error bohr | K/Y max energy/De | K/Y max ΔL |
|---|---:|---:|---:|
| ordinary | 1.208231e-07/2.366964e-09 | 3.192714e-06/1.014246e-09 | 1.941581e-58/9.956824e-59 |
| small_b | 7.958303e-07/1.237330e-06 | 5.128406e-06/2.024969e-09 | 2.473649e-59/6.067440e-60 |
| large_b | 6.525987e-10/8.114855e-08 | 3.916624e-10/1.481032e-16 | 3.435104e-58/4.480571e-58 |
| low_energy | 7.829458e-07/7.597670e-07 | 2.751669e-06/8.716231e-10 | 1.717552e-58/1.151258e-58 |
| high_energy | 4.891954e-06/2.641506e-06 | 1.394991e-04/2.160325e-07 | 0.000000e+00/0.000000e+00 |
| s4d_passing | 2.940998e-07/6.357344e-07 | 1.064738e-06/2.235483e-10 | 6.372368e-58/4.032514e-58 |
| s4d_no_wall | 6.954854e-09/3.949369e-11 | 1.139181e-07/3.961102e-12 | 5.675390e-58/4.928628e-58 |
| boundary_reflect | 2.442594e-07/9.030730e-07 | 4.068163e-09/5.726731e-15 | 8.214380e-58/7.268482e-58 |
| boundary_pass | 9.698363e-08/3.720340e-09 | 1.962023e-07/1.587108e-11 | 3.584457e-58/9.160278e-58 |

각도·방향 오차 <=1e-5 rad, 상대 Rmin 오차 <=1e-5, max |ΔH|/De <=1e-3, max |ΔL| <=1e-20, 모든 내부 chord r>=2.4를 두 방법 모두 만족했다. Yoshida 최악 각도 오차 2.59017e-10, KDK20 최악 3.27318e-6 rad다. 패널 최저 내부 Rmin은 KDK 5.50925345 / Yoshida 5.50926098 bohr다.

Yoshida가 최접근 거리까지 모든 입력에서 더 정확한 것은 아니다. small_b/large_b/s4d_passing/boundary_reflect는 기록한 Rmin 차이가 KDK20보다 크지만 사전 기준 안이다. b=0 high_energy 각도 차이는 두 방법 모두 약 4.36e-60이며 이 대칭 입력의 결과를 일반 정확도 증거로 확대하지 않는다.

출구 momentum 방향·q/p·closest approach·보존량·step/force/endpoint count·memory·output bytes는 모든 run의 JSON에 보존한다. Yoshida9 및 boundary KDK20의 이전 60자리 직접 비교 최대 변화는 4.97842e-59(<1e-20), step 수도 일치했다. 다른 8개의 KDK20에는 이전 KDK20 값이 없어 continuous와 관측 기준을 대조했으며, 기본 reproduction_pass=True를 과거 결과 재현 증거로 세지 않았다. JSON previous_method_result_available 필드로 구분했다.

## 비용·한계·검증

전체 launcher wall 1220.074250초(약 20분20초), campaign wall 1219.049303초. 모든 26개 timed run wall 합 1210.888748초, CPU 합 1179.421875초. warm-up timed wall 118.030962초 / CPU 116.296875초는 공식 median/panel 합에서 제외했다. launcher minus run wall 약 9.185502초는 import·hash·worker/제어 등 timer 밖 실행 운영 구간이며 두 방법의 trajectory runtime에 넣지 않았다. 로컬 준비/사후 검증 시간은 이 launcher 구간 밖이다.

S4d passing의 Yoshida CPU 113.875초 / wall 131.285824초 등 로컬 scheduling/I/O 대기 영향이 있었다. 다른 로컬 작업은 통제하지 않았고 각 panel은 1회여서 반복분산/신뢰구간을 제공하지 않는다. 모든 입력에서 CPU도 더 높았다는 실제 측정은 유지한다. Windows peak working set은 archive hash preflight를 포함한 전체 worker 생애 최대값이므로 integrator만의 메모리라고 주장하지 않는다.

이번 benchmark는 공통 observer와 모든-state 저장 정책의 비용이다. 승인된 production/replay end-to-end 비용까지 측정하거나 미래 many-body를 인증하지 않았다. negative internal stage의 r_min/hard-domain/many-body/chemical interaction 위험은 그대로다. coefficient/force 최적화·snap·에너지/운동량 보정·계약 변경은 하지 않았다.

exit 0, 26개 trace hash·gzip CRC·연속 step번호/개수 검증 PASS(521,975 records, outer step 합 521,949). 결과·로그 85개 SHA manifest 보존. 데이터는 runs/c1b1_cost_local_v1/snapshot/code/runs/c1b1_kdk20_yoshida40_cost_v1/; 로컬 환경·launcher·로그는 runs/c1b1_cost_local_v1/.

새 플랫폼/기존 비용 판정 관련 13 passed(0.59초), 최종 전체 관련 **70 passed(19.36초)**, failure/error/실제 skip 0. 실제 Windows affinity roundtrip·실제 memory 양수, adapter hash fault 거부를 확인했다. 기존 numeric source 12·protected 134·O-1 원본 97·원인 격리 원본 27 hash 불변.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 사용자 14절에 따라 독립 실행 adapter·시험·보고서만 추가했다. 기존 benchmark·물리·production/common/frozen source 및 fixture를 변경하지 않았다. 공식 기준선 갱신 없음.

구상 일치성 별도 확인: 같은 물리/입력에서 실제 전체 관측·기록 비용까지 비교했고, 더 높은 각도 정확도와 더 높은 계산 비용을 동시에 기록했다. 이번 B는 이 2-body panel과 구현에서의 진단이며 production 선택은 설계자 판단이다.

Energy Bound APPROVED / Liveness NotCertified / Safety Conditional / A-EV unresolved / Production Replay Verifier APPROVED / O-1 STOPPED·NOT PASSED / TIME_DISCRETIZATION_SUPPORTED numerical diagnostic 유지. O-3·A-EV·native J·새 물리 미착수.
