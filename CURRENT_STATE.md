# 현재 상태

**최종 갱신:** 2026-09-27 — 현재 상태 대시보드. 과거 기록은 [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)에 원문 전체를 보존한다.

## 현재 우선순위와 활성 Gate

| 계통 | 상태 | 진행 기준 |
|---|---|---|
| **A** | **ACTIVE** | 최우선. 세계의 물리 기반을 먼저 검증한다 |
| **L** | **DEFERRED UNTIL A FOUNDATION IS SUFFICIENT** | A의 기반이 충분히 생긴 뒤 A 안에서 자연 발생·진화하는 계통으로 진행한다 |
| **B** | **DEFERRED TO LATE STAGE, NOT CANCELLED** | A와 L이 어느 정도 완성되어 작더라도 “세계가 돌아간다”는 단계 뒤 마지막 단계에서 본격적으로 만든다 |

B를 중단·폐기한 것이 아니다. 기존 **B-classic 구현·문서·시험은 보존**하며 나중에 비교군/연구 자산으로 사용한다.
L은 별도로 생명 행동을 명령해 만드는 대상이 아니다. A의 물리에서 발생과 진화를 관찰한다. 생명·복사·진화의 새 증거는 아직 없다.

| 현재 진행 | 상태 |
|---|---|
| **현재 활성 Gate** | **C1-B1** |
| **현재 세부 단계** | **outer formal bound ④ 진행** |
| **다음 Gate** | **16384-bit rounding-decision completeness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증** |

위 순서는 앞으로 통과해야 할 관문이다. **④ 전체는 아직 FROZEN이 아니며 ⑤는 시작하지 않았다.**

## C1-B1: 완료된 부분과 남은 의무

현재 후보는 두 Ar40, 위치 FX(96,48), 운동량 FX(96,80), Δt = 40 a.u., drift v2(위치에 더하기 전에 변위를 반올림)다.
이 후보를 A 세계의 최종 수 체계나 C1-B1 전체 동결로 해석하지 않는다. binary64 절대 위치는 탈락 기록으로 strict xfail 1개를 유지한다.

| 항목 | 현재 상태 | 정확한 범위 |
|---|---|---|
| **D_valid v2** | **FROZEN** | canonical 생성기·기준 fixture·초기 상태 식별 계약. 궤적 전체 인증 아님 |
| **④-1** | **원인별 1-step formal bound 구현 완료** | 위치·초기 운동량·impulse·이산화 항을 분리. 유한 shell·half-step 운동량 cap 아래의 1-step 및 유한합 |
| **④-2** | **outgoing shell induction + 유한 체류 상한 구현** | 실제 ΔR²≥g_min>0 귀납, shell 유지·출구 packet 연결·overflow 검사. 모든 상태의 탈출을 보장하지 않음 |
| **④-3** | **R_J + zero discrete impulse + analytic continuous tail 구현** | 실행기 impulse=0과 동일 실제 입구의 연속 tail 잔여 impulse를 구분. L 상한은 유한 입구→R_J만 |
| **④-4** | **rounding-decision completeness 진행 중** | tail 결정성은 닫음. 일반 pre-tail reachable enclosure의 비영 impulse cover는 미완료 |
| **④ 전체** | **아직 FROZEN 아님** | ④-2/④-3은 rounding-decision completeness에 조건부 |
| **⑤** | **아직 시작하지 않음** | ④ 최종 감사/동결 뒤 독립 실측 교차검증 |

**④가 열려 있는 이유:** 미래의 모든 필요한 impulse 반올림이 기존 평가기의 **MAX_PRECISION_BITS=16384** 안에서 항상 결정되는지 아직 미증명이다.
유한 체류 step 수만으로 반올림 경계와의 분리가 보장되지는 않는다. 충분한 증거가 없으면 `NotCertified`이며 실행 중 `ReferenceUndecided` 가능성도 남는다.

현재 닫힌 부분은 **R_J=10240 bohr 이후 모든 legal FX 상대 위치의 tail impulse 결정성**(210 radial cell, 최대 512 bit)이다.
FX 범위를 넘어 프로그램이 무한히 실행된다는 뜻은 아니다. 일반적인 유한 outgoing 입구→R_J 구간은 기존 shell induction의 **reachable enclosure 전체**를 덮어야 한다.
R=20 예시는 64-cell 예산에서 미인증이고, 2-step prefix도 `incomplete_budget`이다. 단일 궤적 인증으로 전체 enclosure 인증을 대신하지 않는다.

**④-4b 진행(2026-09-27):** evaluator 수정 전·후 frozen 181개 probe replay는 exit 0, 181/181 초기 비트·D_valid 판정·KDK 전이 일치
(총 3,470,163 전이, 3815.645초), fixture 변경 없음. 기존 audit_fail 6개는 독립 감사 재실행 없이 보존했다.
실제 KDK에서 보존되는 상대 좌표 0과 누적 kick/유한 L bound를 유도한
[coordinate tube·direction projection](docs/active/C1B1_REACHABLE_GEOMETRY_V1.md)을 구현했으며 신규 시험 9개 통과.
Cell budget은 64 유지. 재생성한 R=20 예시는 상대 좌표 3D→1D로 줄었지만 64 cell 검사 뒤 미해결 record 76개가 남아 `NotCertified`다.
관련 시험 **106 passed, 51.59초**. VAST **REMOTE PYTHON FULL: 2292 passed + 121 skipped + 1 strict xfailed, 실패 0, 98.89초, exit 0**.
skip은 Windows/native 98개, CUDA 10개, 외부 원문 자료 13개이며 통과로 세지 않는다. 이번 LOCAL FULL은 설계자의 원격 이전 지시로 중단했으므로 새 LOCAL FULL 결과가 아니다.
로그 회수와 VAST 정지 확인 완료. **④-4b 전체 미완료**이며 다음 의무는 enclosure를 추가로 좁히는 수학적 제약이다.

**아직 남음:** inbound / inner / global shadowing / 전체 산란각 / E_min 재생성 / 속박 궤도 domain·error proof / native J evaluator와 실행기 비트 동등성 / C1-B1 전체 freeze.
무한시간 균일 L 상한과 무한 FX 실행도 인증 범위가 아니다. 이번 문서 정리에서 E_min을 재생성하거나 새로운 물리 규칙을 추가하지 않는다.

## 증거 종류: 수치 검증과 별도 수학 증거

| 증거 | 현재 표현 | 적용 범위 |
|---|---|---|
| **D_valid evidence** | **`numerical_validated` / `unsupported`** | 동결 규약이 식별하는 초기 상태의 수치 검증 범위 |
| **별도 수학 증거** | **analytic outer certificate** | 명시한 전제 아래 outgoing shell·유한 체류·tail에 관한 해석적 증거. 정밀도 완전성 등 남은 조건은 위 표를 따른다 |

**둘 사이 자동 승격이나 자동 연결은 없다.** Outer certificate가 생겨도 D_valid나 `run.validation`이 `formal_certified`로 바뀌지 않는다.
동결 D_valid 코드에는 `formal_certified`라는 수준 이름이 남아 있지만 현재 그 수준을 반환하는 상태는 없다. 이것은 analytic outer certificate의 존재 여부와 별개다.

D_valid v2는 설계자 판정 `0898ca3`(대상 구현 `a8619c8`)으로 동결했다. 단일 canonical 생성기 → 실제 경계 측정 → 기준 fixture → 초기 상태 식별이 연결되며,
7 에너지 × 2쪽의 181개 측정 상태가 식별 상태와 일치한다. 기준 fixture는 `a_reference/fixtures/c1b1_orbit_boundary_v3.json`, 계약은 `c1b1-dvalid-v2`다.
미측정 에너지 보간·외삽, 가장 바깥 탐침 밖 인정, 다른 profile로의 확대는 하지 않는다. 같은 에너지·같은 쪽의 탐침 사이는 단조 띠 모형에 근거하며 연속 구간 전체의 증명은 아니다.
`unsupported`는 운동 계산을 바꾸거나 막지 않는다. 동결 대상의 재측정은 새 결함 또는 다음 물리 단계의 필요가 생길 때만 별도 판단하며 이번에는 변경하지 않는다.

## 구현 자산과 정직한 한계

| 자산 | 현재 읽는 방식 |
|---|---|
| 결정론 A 환경·보존·CPU/GPU field | 기존 구현·검증 자산. 현재 v6 실제 물질 계산 기반과 같은 완성 단계로 묶지 않는다 |
| causal v5 | 이름·순서에 무관한 생성·성장·병합 및 사슬 31개 검증. 정사각형 기하·회전 없는 2D 충돌 한계가 있다 |
| A-MICRO v6 | 변형 가능한 실제 물질 기반을 향한 별도 계통. 현재 활성 작업은 C1-B1 |
| C1-A | Lang 2024 Ar–Ar 퍼텐셜·해석적 힘·한 번 반올림·출처·fixture 비트 동결. 직렬 CPU·병렬 CPU·CUDA 함수 계약이며 다입자 세계 실행기 아님 |
| B-classic·초기 B 도구 | 수작업 규칙 모델·비교군/연구 자산 보존. 학습형 B 없음. 본격 개발은 후기 단계 |
| B 인간 신체 계약 | 문서 동결, 구현 미착수. 동결 계약 보존 |
| L | 자연 발생·복사·진화의 새 증거 없음. 촉매·주형·반응 화학·다입자 응집·3체는 아직 남음 |
| 확률 세계·레거시 | 동결된 비교 기준선과 과거 연구 자료. 새 결정론 증거와 합산하지 않음 |

고전 Ar 모델의 물리적 한계, 반올림, 시간 이산화 오차를 구분한다. CPU/GPU 비트 일치나 시험 통과가 현실 물리 정확도 전체를 증명하지 않는다.
Physics IR/DSL·다중 해상도·계산/메모리/재생 구조는 요구사항·제안이며 구현·동결로 읽지 않는다.
네이티브 실행의 600초 하드 타임아웃과 별개로 컴파일 빌드 타임아웃은 미완 인프라 과제다. 원격 자원의 현재 가동·비용은 이 대시보드에서 주장하지 않는다.

## 검증 기록

아래는 실행별 기록이다. 문서 정리 재검증과 과거 구현 당시의 결과를 구분하며, 시험 통과를 새 물리 증거나 ④ 완료로 해석하지 않는다.

| 실행 기록 | 결과 | 로그·JUnit |
|---|---|---|
| 폴더 정리 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 454.67초**, cp949 경고 25건 | `runs/documentation_folder_cleanup_20260927/local_full.log`, `runs/documentation_folder_cleanup_20260927/local_full.xml` |
| 내용 정리 당시 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 395.50초**, cp949 경고 25건 | `runs/documentation_cleanup_20260927_local_full.log`, `runs/documentation_cleanup_20260927_local_full.xml` |
| ④-4 구현 당시 LOCAL FULL (2026-09-27) | **2404 passed + 1 strict xfailed, failure 0, skip 0, 388.84초**, cp949 경고 25건 | `runs/c1b1_rounding_decision_local_full_v1.*` |
| ④-1 당시 LOCAL FULL | 2335 passed + 1 strict xfailed, failure 0, skip 0, 447.41초, cp949 경고 25건 | `runs/c1b1_outer_bound_local_full.*` |
| ④-2/④-3 당시 REMOTE PYTHON FULL | 2258 passed + 108 skipped + 1 strict xfailed, failure 0, 71.23초 | `runs/c1b1_outer_bootstrap_full_v1.*` |
| Codex 인수인계 당시 LOCAL FULL (`0898ca3`) | 2307 passed + 1 strict xfailed, failure 0, skip 0, 445.58초, 인코딩 경고 24건 | `runs/project_review_20260927/local_full.*` |

`LOCAL FULL`은 로컬 Python + native CPU/CUDA + Windows/외부 참조 시험이다. `REMOTE PYTHON FULL`의 skip을 통과로 세지 않으며 두 범위를 합치지 않는다.
표준 검증 명령과 기준선 정본은 [AGENTS.md](AGENTS.md)를 본다. 컴파일러 출력 인코딩 경고가 남아 있으므로 경고 없는 실행으로 보고하지 않는다.

## 현재 문서 진입점과 역사 기록

문서는 [상태별 폴더 안내](docs/README.md)·[전체 분류/이동 경로표](docs/DOCUMENT_STATUS_INDEX.md)로 찾는다. `active`는 현재 C1-B1, `frozen`은 지켜야 할 계약, `history`는 과거 기록, `deferred`는 후기 B 자산이다. `docs/current`는 옛 경로 안내용이며 신체 계약 원문만 경로 고정 때문에 남아 있다.

- [C1-B1 설계·결정·검증 기록](docs/active/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md): **23절 D_valid 동결, 24절 ④-1, 25절 ④-2/④-3, 26절 rounding-decision 진행**을 함께 읽는다.
- [④-4 rounding-decision 상태](docs/active/C1B1_ROUNDING_DECISION_V1.md): tail 증거와 미완 pre-tail cover의 상세. **23절만을 최신 결정으로 읽지 않는다.**
- [저장소 지도](REPO_MAP.md): 구현 위치와 계통 구분.
- [인수인계 점검](docs/history/PROJECT_HANDOVER_REVIEW_2026-09-27.md): 현재 보충 안내와 `0898ca3` 당시 점검·시험 이력을 구분.
- [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md): 문서 정리 전 대시보드 원문, 과거 번호 체계·진행 순서·갈림길·B 연구·실험·기술 부채·최근 이력 전체. 본문 속 “다음”은 당시 기록이다.

A/B/L 역할과 불변조건은 [RULES.md](RULES.md)·[PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md)를 따른다.
Git은 2026-09-21 초기화했고 이전 상태는 `D:\KiroCrewTraceVault\success-is-mother-of-failure\project-snapshots\20260921_090715_pre_git_init\`에 봉인했다.
