# C1-B1 outer dt40 적분기 비교 V1 — 원격 제어 실패로 중단

2026-10-01. **최종 판정 C: 아직 판정 불가.** 후보의 Ar-Ar 궤적, 정밀도 수렴, 실제 비용을 측정하지 못했다. `NO_CANDIDATE_BEATS_BASELINE`이나 후보 정확도 실패로 판정하지 않는다. 준비와 짧은 대수 시험만 완료했으며 실험은 미완료다.

작업 시작 HEAD·local origin/master·실제 원격 master는 모두 `508bba4fd01826aa6fb52f91c5011413a114f1aa`, master, clean, ahead/behind 0/0이었다. 최근 O-1 `504e837`, 원인 격리 `508bba4` 결과를 재사용했다. commit/push 없음.

## 보존 자료와 읽기 범위

[실행 전 프로토콜](C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md), [입력·계수·소스 봉인](C1B1_DT40_INTEGRATOR_BENCHMARK_SEAL_V1.json), [기계 판독 결과·실패 기록·해시](C1B1_DT40_INTEGRATOR_BENCHMARK_RESULTS_V1.json).
실행 전 봉인 payload SHA-256: `bbe64ed6ad96adf3654a13afea8b9ebec35743243d7fb91f1b7f268edd370232`.
로컬 배포 bundle 272개 파일, 64,353,518 bytes, SHA-256 `cb19888ccd6ff47d40a7fbddc8d646b706fea5687a969c7f1360957869e9307d`. 업로드되지 않았다.
로그·배포 준비물·JUnit은 `runs/c1b1_dt40_integrator_benchmark_20261001_v1/`에 보존했다(Git 제외). 중요한 실패 상태·하드웨어·시각·해시는 위 결과 JSON에도 보존했다.

사용자의 첨부 요청 전체를 읽고, 루트 AGENTS/RULES/CURRENT_STATE/REPO_MAP 및 관련 O-1·원인 격리 코드와 결과를 범위 지정해 확인했다. 큰 현재 상태·맵은 해당 부분을 재확인했다. 저장소 전체 역사 감사나 새 O-1 재실행은 하지 않았다.

## 두 후보와 코드 경계

1. **A: Yoshida/Forest–Ruth 4차 대칭 합성.** `s=2^(1/3)`, `w=1/(2-s)`, `z=-s/(2-s)`. kick 계수 `[w/2,(w+z)/2,(w+z)/2,w/2]`, drift `[w,z,w]`. outer dt40에서 내부 음수 drift가 있다. 모든 내부 drift 선분의 최소 반경을 검사하도록 구현했다. 음수 stage의 domain 안전이나 production 적합성을 확인한 것은 아니다. 출처: [Yoshida 1990](https://tlakoba.w3.uvm.edu/math6737/for_final_topics/SSM_1990_Yoshida.pdf).
2. **B: Chin–Chen forward 4A.** kick `1/6,2/3,1/6`, drift `1/2,1/2`, 중앙 힘 `F + h²/(48μ) grad(|F|²)`. 중심력에서는 추가항 `h² V' V'' q/(24μr)`이다. `V''`는 기존 analytic `V'`에 mpmath.diff를 적용하며 추가 PES/derivative 호출을 따로 세도록 구현했다. 출처: [Chin–Chen 식15–18](https://arxiv.org/html/astro-ph/0304223).

**프로토콜 오기 정정:** 봉인된 프로토콜의 음수 drift 근삿값 `-68.0976568`은 오기다. 봉인된 정확 식과 60자리 계수에 따른 값은 약 `-68.09657535677261 a.u.`다. 정확 식·코드·봉인은 변경하지 않았다. 이 오기는 어떤 궤적 계산에도 사용되지 않았다. 재개 시 prose 오기 정정을 별도 이력으로 유지해야 한다.

새 코드: `c1b1_integrator_benchmark/methods.py`의 계수 흐름, `study.py`의 관측·호출 계측·조건부 panel runner, `__init__.py`.
공유한 코드는 기존 `c1b1_o1`의 질량/단위/입력 모델, 기존 `c1b1_o1_diagnostic.kdk.Lang.value_derivative` 및 relative/angle 관측 도구, 출구 반경 보정용 기존 continuous extension이다. force evaluator 자체는 변경·최적화하지 않았다. 공개 Fortran 원문 hash `a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049`를 유지했다.
기존 독립 HP-KDK step은 저장된 KDK20 상태의 비용 표본에만 사용하도록 구성했다. 새로운 후보 갱신에 production KDK step/kick/drift·reference force/rounding·replay verifier를 복사하거나 호출하지 않았다. production `a_reference/a_numeric/engine/audit/c1b1_replay` import 경계를 시험했다.

many-body 확장성은 아직 실측하지 않았다. 합성법은 separable Hamiltonian에 적용할 수 있으나 음수 stage의 domain 처리가 남는다. 4A의 이번 radial V'' 구현은 Ar-Ar 전용이며 일반 many-body에는 질량을 반영한 Hessian-force product가 필요하다. 구현된 runner의 Linux 환경·Ar-Ar 관측·remote 전체 실행도 아직 검증되지 않았다.

## 실행 전에 봉인한 입력

1차는 기존 DISAGREE `boundary_pass` 하나뿐이다. 1차 생존 후보만 나머지 8개로 진행하도록 준비했다. 아래 b는 읽기 편한 근삿값이며 실제 raw·정확 유리수·입력 해시는 봉인 JSON에 있다.

| 입력 | E/De | b (bohr) | rho | 이번 후보 실행 |
|---|---:|---:|---:|---|
| ordinary | 0.5 | 6 | — | 미실행 |
| small_b | 0.5 | 0.1 | — | 미실행 |
| large_b | 0.5 | 14 | — | 미실행 |
| low_energy | 0.01 | 7 | — | 미실행 |
| high_energy | 9.9 | 0 | — | 미실행 |
| s4d_passing | 0.15 | 14.032171609409 | -0.005 | 미실행 |
| s4d_no_wall | 1 | 10 | — | 미실행 |
| boundary_reflect | 0.5 | 11.730724180230917 | +0.001 | 미실행 |
| boundary_pass | 0.5 | 11.707286169880804 | -0.001 | 미실행 |

원래 CONFIRMED/REPLAY_VERIFIED 9개 history를 입력과 기준 자료로만 재사용한다. 후보 trajectory는 CONFIRMED가 아니며 실제 생성된 후보 trajectory도 없다. `boundary_pass`의 D_valid unsupported와 기존 O-1 STOP 의미를 유지한다. rho=-0.0001·새 random 표본은 추가하지 않았다.

40/60자리 수렴 변화 <=1e-20, 각도 <=1e-5 rad, 상대 최접근 차이 <=1e-5, 모든 내부 drift r>=2.4, 저장 상태 max |ΔH|/De<=1e-3, max |ΔL|<=1e-20를 실행 전에 고정했다. 비용 표본은 기존 KDK20 trace의 균등 1024개 저장 상태, 3회 반복으로 고정했다. 동일 CPU/정밀도에서 후보 outer40 대 KDK20 두 step 비용을 비교하되 이는 kernel 비용이며 전체 실행 비용은 별도다. 불안정·domain 위반·정확도 초과·비용 부적합 후보 STOP 기준은 프로토콜에 있다. 후보의 수렴·안전·비용 조건은 **모두 미시험**이다.

## 필수 비교표 — 기존 역사값과 미실행 구분

문제 입력 E=0.5 De, rho=-0.001. 아래 KDK40/20은 기존 **60자리 로컬 원인 격리 진단** 결과다. χ 오차는 각 궤적의 출구 반경에 맞춘 기존 continuous reference와의 차이이며 CPU/wall은 당시 trajectory 관측 시간이다. 이번 Vast의 시간이나 같은 하드웨어 비교가 아니다. energy=max |ΔH|/De, L=max |ΔL|이다.

| 방법 | outer dt | χ 오차 (rad) | force eval | CPU (s) | wall (s) | energy | L | 판정 |
|---|---:|---:|---|---:|---:|---:|---:|---|
| HP-KDK40, 기존 | 40 | 1.30927965e-5 | N/A: 당시 별도 계측 없음 | 28.21875 | 28.359743 | 7.84810118e-7 | 5.52603757e-58 | 기존 각도 기준 초과 |
| HP-KDK20, 기존 | 20 | 3.27318382e-6 | N/A: 당시 별도 계측 없음 | 45.46875 | 45.593633 | 1.96202314e-7 | 3.58445680e-58 | 기존 관측 진단값 |
| A: Yoshida4 | 40 | N/A | N/A | N/A | N/A | N/A | N/A | NOT_RUN_REMOTE |
| B: Chin4A | 40 | N/A | N/A | N/A | N/A | N/A | N/A | NOT_RUN_REMOTE |

기존 KDK40/20 outer step은 17,284 / 34,568이다. 후보 outer step·PES/force/derivative 횟수·출구 방향·최접근 거리·에너지·L·peak memory 모두 미측정이다. 기존 KDK10/5 오차 8.18294999e-7 / 2.04573690e-7, production A40 대 HP-KDK40 차이 약2.20e-11도 저장 자료로만 재사용했다. 기존 continuous/reference/KDK 궤적을 재생성하지 않았다.

## Vast 제어 시도와 중단

승인 상한 $1/hr·총 $1. 한 번에 기존 stopped instance 하나만 선택했으며 GPU 계산을 하지 않았다. 다음 하드웨어·가격은 Vast API의 보고값이다. 게스트 내부 lscpu/affinity/RAM을 원격 확인하지 못했다.

| 시도 | instance / CPU | API core / effective vCPU | RAM 보고값 (MB) | $/hr | 시작→종료 (UTC) | 경과 (s) | 결과 |
|---|---|---|---:|---:|---|---:|---|
| 1 | 52731349 / Core Ultra 7 265K | 20 / 20 | 64007 | 0.16074074 | 05:33:23→05:36:04 | 161.7593 | running 전환 확인 못함 |
| 2 | 52764050 / Threadripper PRO 9975WX | 64 / 32 | 160318 | 0.26962963 | 05:38:00→05:40:38 | 157.9991 | running 전환 확인 못함 |
| 3 | 52764050 / 동일 | 64 / 32 | 160318 | 0.26962963 | 05:41:35→05:41:41 | 5.7121 | 로컬 SDK 제어 오류 |

모든 날짜는 2026-10-01. KST는 UTC+9다. 첫 두 CLI 시도는 실제 start 응답 본문을 보존하지 못해 시작 거절·상태 전환 실패의 원인을 구별할 수 없다. `--raw`가 start에서 구조화 응답을 보장하지 않고 CLI exit 0도 start 성공을 보장하지 않는 점을 설치된 코드에서 확인했다.

세 번째는 에이전트가 `VastAI(retry=0)`을 사용한 실수다. 설치된 API client `_request`는 `range(0,self.retry)` 안에서 요청하며, retry=0이면 요청 없이 None을 반환한다. 따라서 `raise_for_status`에서 NoneType 오류가 났다. **세 번째 start HTTP 요청은 전송되지 않았다.** Vast 서버·host·잔액 실패의 증거가 아니다. 이를 바로잡아 네 번째 실행으로 넘어가지 않고 **AGENTS.md의 “3회 시도해서 실패하면 멈추고 보고한다”**에 따라 중단했다.

각 제어 시도 뒤 stop을 호출하고 `actual_status=exited`, `intended_status=stopped`, `cur_state=stopped`를 확인했다. 최종 read-only 확인에서도 기존 네 인스턴스 모두 exited/stopped였다. 로그의 `started=true`는 시작 제어를 시도했다는 표시이며 **running 확인 표시가 아니다**.
이번 궤적 0건, 비용 probe 0건, SSH/업로드/원격 사전 시험·원격 campaign 0건, 결과 archive 회수 0건이다. 회수할 물리 결과가 생기지 않았으며 제어 실패 로그는 로컬에 보존했다. 설치된 client/CLI 동작은 로컬 코드 확인으로 검증했다.

각 제어 기간×보고 가격을 단순 곱한 값은 $0.00722258 / $0.01183368 / $0.00042782, 합계 **$0.01948408**이다. 이는 running 계산 시간·실제 청구액이 아니다. 청구서 미확인으로 실제 과금은 **unknown**이며 전송비·정지된 기존 인스턴스 보관비를 포함하지 않는다. 실제 지출 총액을 이 숫자로 확정하거나 총비용 상한 준수 증거라고 부르지 않는다.

원인 후보/다음 실험: 첫 두 시도는 start API 응답을 제대로 보존하는 제어 경로를 통해 host/요청 거절/상태 문제를 분리해야 한다. SDK 호출은 retry 의미를 고친 뒤 제어 전용 사전 확인이 필요하다. 이는 다음 재개 작업이며 이번 시도에서 추가 노드 시작이나 로컬 산란 대체를 하지 않았다.

## 시험·구상 대조·변경 범위

새 관련 시험: `python -m pytest tests/test_c1b1_integrator_benchmark.py -q --junitxml=runs/c1b1_dt40_integrator_benchmark_20261001_v1/local_unit_junit.xml` → **14 passed, 0.65초, failure/error/skip 0, exit 0**.
작은 harmonic 예제의 4차 수렴·역행, gradient의 inverse mass·추가 호출·cache, 음수 내부 선분, domain 침범, 판정 gate, import 경계, remote marker 없는 궤적 호출 거부를 시험했다. 이 시험은 Ar-Ar 물리 재현·실제 비용·Vast runner 통과 증거가 아니다.

별도 구상 대조: 두 후보는 다른 수치 흐름이며 동일 PES·질량·outer dt40을 유지한다. snap/에너지·운동량 보정/결과 뒤 계수·허용오차 조정은 없다. 내부 음수 stage와 force-gradient 추가 평가 비용을 드러낸다. 원격 계산으로 로컬 장시간 점유를 피하는 목적은 지켰지만, 핵심 질문인 KDK20 대비 정확도·비용 우위는 아직 답하지 못했다.

봉인 재확인: 새/공유 소스 12, 기존 protected 소스 134, 기존 O-1 원본 97, 원인 격리 원본 27, 공개 PES 원문 1 모두 hash 불일치 0. 기존 실행 코드·공용 코드·동결 fixture·계약 수정 0. 새 관측 코드/시험/문서와 기존 문서의 링크·현재 상태만 추가했다.
**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 이번 첨부 요청 및 AGENTS 예외에 따라 독립 진단 파일·시험·문서만 추가했으며 기존 실행·공용·동결 자산은 불변이다. 공식 기준선 갱신 없음. 앞선 O-1 LOCAL FULL 수치를 이번 신규 FULL로 세지 않는다.

Energy Bound v0 APPROVED, ④-Liveness NotCertified, ④-Safety Conditional, A-EV unresolved, Production Replay Verifier V1 APPROVED, O-1 STOPPED / NOT PASSED, 원인 격리 TIME_DISCRETIZATION_SUPPORTED 유지. production 변경/채택·O-3·A-EV·native J·adaptive dt·production substep·live pipe·rollback controller·D_valid 재설계·새 물리 미착수.

**C. 아직 판정 불가.**
