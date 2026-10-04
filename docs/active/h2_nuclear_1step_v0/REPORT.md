# H₂ Born–Oppenheimer Nuclear Motion 1-Step Pilot V0

**H2_BO_NUCLEAR_1STEP_SUPPORTED / NOT CERTIFIED / NOT PRODUCTION APPROVED.**

2026-10-04. 고정 COM의 1D 상대 좌표에서 BO energy → 중앙 차분 force → 핵 위치·운동량 업데이트를 정확히 한 step 연결했다. 정확한 vibration·평형·force·BO dynamics 인증, formation, 전자 실시간 운동, canonical A 채택은 아니다. 높은 scalar precision이 전자 에너지 정확도를 높이지 않는다. ΔH에 새 PASS tolerance를 만들지 않았다.

## GIT STATE

시작 local HEAD `e44309144baf46bfb23ebd62ff830809db045e7f`, branch `codex/h2-representation-pilot1`, tracked tree clean. 기본 master는 별도 `0f7b744cf754450424a63c47f305e0327c5b37c1`. 원격 master/pilot은 `0f7b744` / `264f588` 그대로였다. 새 독립 nuclear Pilot·시험·문서만 추가했다. 기존 calculator/common/frozen code 불변, merge/rebase/push 없음. 최종 local commit은 Git 이력으로 확인한다.

## PHYSICAL CONTRACT / STEP EQUATIONS

R0=1.5 bohr, P0=0, dt=1 atomic time unit, h=0.1 bohr. E=hartree, F=Eh/bohr, 질량=electron mass, P=atomic momentum unit. 중간 단위 변환 없음. 핵 운동은 고전적 1D BO 근사이며 회전·비단열·전자 실시간 운동을 포함하지 않는다.

저장소의 추적된 Python/JSON/Markdown에서 authoritative proton mass 상수는 찾지 못했다. [NIST 2022 CODATA](https://physics.nist.gov/cuu/Constants/Table/allascii.txt)의 proton-electron mass ratio **1836.152673426**, standard uncertainty **0.000000032**를 이 Pilot의 로컬 상수로만 채택했다. μ=**918.076336713**. nominal 값 사용이며 질량 불확실성 전파는 미평가다. [mass.json](../../../electronic_pilot/h2_nuclear_v0/mass.json)에 source/retrieval date(2026-10-04)/literal/fingerprint를 기록했다.

공식 NIST table은 web open/find로 확인했다. 별도 직접 byte 다운로드는 HTTP403이었다. fingerprint는 확인한 row의 전사와 literal에 대한 것이며 remote 전체 파일 raw hash라고 주장하지 않는다. Literal SHA256 `2fc335b770dee30b0df68d7874464fdb0119bd02554d0ec8a15be82375d497ed`.

부호를 구현 전에 고정했다. R=zB−zA, zA=−R/2, zB=+R/2. vA=−Rdot/2, vB=+Rdot/2이므로 K=m_p Rdot²/4=μ Rdot²/2, P=μ Rdot. 따라서 pA=−P, pB=+P이며 총 운동량과 COM은 0이다.

```text
P_half = P0 + dt*F0/2
R1 = R0 + dt*P_half/μ
F1 = -(E(R1+h)-E(R1-h))/(2h)
P1 = P_half + dt*F1/2
K = P²/(2μ)
```

작은 scalar는 Decimal80 / ROUND_HALF_EVEN으로 계산했다. 별도 check.py는 scalar.py/전자 계산기를 import하지 않고 exact Fraction으로 식·질량·저장 좌표·핵 운동량을 재계산한다. 사전 1e−75 검사는 Decimal80 산술 오차만 검사하며 ΔH 물리 tolerance가 아니다.

## REUSED SEALED INPUT

기존 accepted E1.4/E1.5/E1.6와 source/실행 봉인을 먼저 확인했다. 초기 세 점 재계산0. F0는 저장 binary64 에너지를 정확히 Decimal로 변환해 별도 산술로 계산했다.

| R | BO E (Eh) | point JSON SHA256 |
|---:|---:|---|
| 1.4 | -1.1742226699153213 | `a33326bef751cbe1dd1af4707ec3a3c1073a54b58dbc4d3d52194bbfd3b77516` |
| 1.5 | -1.1726087635888724 | `2ef9192fd325dac9262a4e82b3ee045e806e2d1c6a694f4462865be9a7c1b74c` |
| 1.6 | -1.1683411708716580 | `3ee42238840fcab4119c842737b1d0ffd96810cd8e131a13e9a92a24b5e92cf7` |

## NEW ELECTRONIC RUNS / GEOMETRY

R1과 requested 세 geometry를 사전 봉인한 뒤에만 실행했다. 같은 raw cc-pV5Z spherical AO110/full singlet6105, canonical AO/compact MO reuse + Cholesky, LAPACK evr roots0/1, binary64, 1 thread, 기존 guard. fit/spline/h 변경/고차 차분/JC 교체 없이 새3점 모두 ACCEPTED. 기존 에너지를 새 R에 보간·대입하지 않았다.

| point | actual stored R (bohr) | EBO (Eh) | guard | 내부 계산 wall (s) | 호출 outer wall (s) | GNU time wall (s) | peak RSS (MiB) |
|---|---:|---:|---|---:|---:|---:|---:|
| left | 1.3999839841775448 | -1.1742226621467093 | ACCEPTED | 24.567 | 25.650 | 25.59 | 3874.609 |
| center | 1.4999839841775449 | -1.1726092592758910 | ACCEPTED | 30.779 | 31.499 | 32.25 | 3875.484 |
| right | 1.5999839841775447 | -1.1683420210295750 | ACCEPTED | 29.564 | 30.358 | 31.34 | 3875.309 |

requested R1 = `1.4999839841775447537652184575595995968932634691351373193510208189297258568083880`

actual serialized/stored R1 exact decimal = `1.4999839841775448601168818640871904790401458740234375`

actual−requested = `1.063516634065275908821468824048883001806489791810702741431916120E-16` bohr. Binary64 hex `0x1.7ffef34c90fb7p+0`. 실제 PySCF 저장 좌표는 zA=`-0.74999199208877243005844093204359523952007293701171875`, zB=`0.74999199208877243005844093204359523952007293701171875` bohr다. 좌우 stencil의 requested/actual/delta/hex도 point JSON에 있다. F1 분모는 계약대로 2h=.2이며 binary64 stencil 폭에 맞춰 바꾸지 않았다. Scalar nuclear R1은 Decimal80 요청값을 보존하고 E1은 실제 serialized R1에서 평가한다.

| point | Smin (>1e−10) | orth L2 (≤1e−10) | H asym (≤1e−10) | residual L2 (≤1e−9) | norm error (≤1e−10) |
|---|---:|---:|---:|---:|---:|
| left | 4.565005e-05 | 2.587914e-12 | 1.776357e-15 | 2.882310e-14 | 0.000000e+00 |
| center | 5.428751e-05 | 3.280389e-12 | 8.881784e-16 | 2.720773e-14 | 8.881784e-16 |
| right | 6.417271e-05 | 2.181836e-12 | 8.881784e-16 | 1.832407e-14 | 0.000000e+00 |

## NUCLEAR STATE / INVARIANTS

| quantity | value (atomic units) |
|---|---:|
| F0 | -0.029407495218316537233249619021080434322357177734375 |
| P_half | -0.0147037476091582686166248095105402171611785888671875 |
| R1 requested | 1.4999839841775447537652184575595995968932634691351373193510208189297258568083880 |
| F1 | -0.029403205585671887689613868133164942264556884765625 |
| P1 | -0.0294053504019942124614317435771226882934570312500000 |

초기 zA=−.75,zB=+.75, pA=pB=0. 최종 scalar zA=`-0.7499919920887723768826092287797997984466317345675686596755104094648629284041940`, zB=`0.7499919920887723768826092287797997984466317345675686596755104094648629284041940`; pA=`0.0294053504019942124614317435771226882934570312500000`, pB=`-0.0294053504019942124614317435771226882934570312500000`.

F0<0/P_half<0/R1<R0/F1<0/P1<0 모두 true. 개별 핵도 안쪽으로 움직인다: A는 +z, B는 −z 방향이다. COM position=0, pA+pB=0을 exact Fraction으로 확인했고 실제 저장 binary64 좌표의 COM도0이다. 이는 equal-mass/fixed-COM 구조의 검증이며 일반3D·장시간 보존법칙 인증이 아니다.

## ENERGY DIAGNOSTIC — MEASURED

| quantity | value (Eh) |
|---|---:|
| K0 | 0 |
| K1 | 4.7091652278059274088497225244668726952857870944507991762425201596772209274494223E-7 |
| H0 | -1.172608763588872449190603219904005527496337890625 |
| H1 | -1.1726087883593682110101233478733519730209824245462905549200823757479840322779073 |
| ΔH | -2.47704957618195201279693464455246445339212905549200823757479840322779073E-8 |

ΔH≈−2.47705e−8 Eh는 측정값만이다. h=.1 finite difference force bias, basis/전자 산술 오차, Verlet 이산화, geometry rounding은 원인별로 분리하지 않았다. rigorous force/energy bound 없음. 높은 scalar precision이 이를 해결하지 않으며 에너지 보존 PASS/FAIL을 이 값으로 판정하지 않는다.

## COST / MEMORY

Incremental one-step wall **140.271748s**. F0/E0 기존 전제, WSL 실행 창 안의 입력/provenance 검사·새3점·독립 scalar 검사를 포함한다. 준비·mass 취득·preflight·최종 증거 포장·후속 pytest는 별도다.

| component | wall (s) |
|---|---:|
| new3 electronic calls incl process startup/capture | 87.506782 |
| validation incl 2525 historical hash checks and independent replay | 52.684139 |
| scalar integration (drift 재계산 + finish) | 0.000193292 |
| 기타 capture/controller overhead | 0.080633 |

같은 perf_counter로 위 분해를 기록했다. 별도 GNU time wall 합은89.18s이며 outer 합과1.673218s 차이가 있다. 원인 미조사, 양쪽 원문을 보존하고 다른 계측값을 성분 합에 섞지 않았다.

Cold-start equivalent **226.751748s** = 이번 incremental + 이전 E1.4/E1.5/E1.6 process wall86.48s. 이는 이전 같은 host 실측을 더한 **추정**이며 fresh cold-start 실행이 아니다. 초기 계산의 당시 validation/WSL 시작 비용·설치/basis 설계 비용은 포함하지 않았다. 계측 차이·측정 시기·local 부하 차이도 있어 엄밀 cost 보장은 아니다.

각 call GNUtime maximum RSS는 위 표. 최대 단일 call **3.784653GiB**. WSL workflow(controller+descendants)20ms sampled aggregate peak **3.795464GiB**, controller 자체 peak **20.207MiB**, 6842 samples. 공유 page를 process별로 더할 수 있고 20ms 사이 peak는 놓칠 수 있다. Windows launcher/전체 host RSS가 아니다.

실측에서 전자 계산과 historical provenance 확인이 주된 비용이었다. 1-step 자체는 완료돼 runtime/memory blocker가 아니었다. multi-step 예산·연속 step 성능·비용 절감은 이번에 평가/구현하지 않았다.

## ACTUAL BLOCKERS / VERIFICATION

전자 계산 REFUSED·반대 방향·COM drift·momentum 구조 위반·NaN/Inf의 실행 blocker 없음. NIST 직접 download403은 공식 web table에서 값을 확인할 수 있어 step을 막지 않았으며 raw 취득 성공으로 보고하지 않는다. 첫 preflight는 기대값의 Decimal 기본28자리 비교 때문에1 failed/124 passed. 기대값을 exact Fraction 비교로 고친 뒤125 passed. 실패log/XML 보존. 보고서 포장 첫 시도의 Windows 경로 표기 KeyError도 packaging_note.json에 기록했으며 수치/봉인 변경·재실행0이다.

최종 관련 **130 passed / failure,error,actual skip0 / 3.69s**. 신규38=scalar/fault33+actual capture5, 이전 force/calculator 직접 관련92. preflight는 중복 합산하지 않는다. 새5capture 시험은 데이터 취득 후 추가했다. reduced mass·momentum/COM 부호·dt/h/step 확장·geometry 혼합/rounding 숨김·guard 초과·force 반전·NaN/Inf·ΔH tolerance 승격을 주입해 거부를 확인했다. 별도 검사기는 scalar/geometry 식을 재계산하며 calculator 자체의 독립 물리 감사나 외부 독립기관 감사는 아니다.

기존 **2525 bindings**와 새 source/입력은 실행 전후 불변. [protocol](protocol.json) / [original execution seal](execution_seal.json) / [completed-evidence rebound seal](execution_seal_rebound_v1.json) / [results](results.json) / [cost summary](cost_summary.json) / [final tests](related_tests_v2.log) / [first test failure](initial_preflight_failure.log). CURRENT_STATE/REPO_MAP은 갱신 가능한 dashboard이며 기존 force 보고서/raw/봉인은 불변으로 보존했다.



후속 pytest를 실행 봉인 포장 완료 전에 시작한 탓에 원래 execution_seal에는 작성 전의 빈 related_tests.log 해시가 들어갔다. 최종 확인에서 유일한 불일치가 이 로그임을 확인했다. 원래 봉인·완료 로그를 보존하고 원래 해시와 일치하는 빈 스냅샷을 raw에 보존했다. [seal race receipt](seal_race_receipt.json)와 별도 execution_seal_rebound_v1은 완료 로그를 연결하며 모든 기존 수치·source binding은 같다. 전자 계산 재실행0. 포장 완료 후 다른 경로 related_tests_v2에 재검증하여 130 passed / failure,error,actual skip0 / 3.69s를 확인했다. 작성자 포장 순서 오류이며 물리 검증 성공으로 감추지 않는다.

`LOCAL FULL 생략 / 관련 시험으로 대체 / 이유`: 새 독립 nuclear Pilot·시험·문서만 추가, 기존 calculator/common/frozen source/fixture 변경0. 공식 통합 Gate/FULL 기준선 갱신은 아니다.

## CONCEPT ALIGNMENT / FINAL CLASSIFICATION / NEXT STEP

자동 시험과 별도로 요청 대조: 기존V5Z/h/.2차분, 초기3점 hash 재사용, 지정R0/P0/dt/mu, Velocity Verlet 정확히1step, requested/actual geometry 공개, 새3점만, COM/p합 확인, ΔH 측정만, 2종 cost/RSS 분리, multi-step/formation/real-time electrons/rotation/3D/thermostat/adaptive/JC/merge/rebase/push0. 전자 계산 stack V0와 B2/H2SOLV/QZ/reference/AO-MO bounds backlog는 동결 유지했다.

읽은 범위: 첨부 전체, AGENTS/RULES 전체, CURRENT_STATE/REPO_MAP/docs 안내·상태표의 관련 항목, 이전 force 보고서 및 interface/worker/reuse/campaign 관련 구현, NIST mass 해당 row. 전체 repo/제3자 전체 재귀를 새로 감사하지 않았다.

**H2_BO_NUCLEAR_1STEP_SUPPORTED / NOT CERTIFIED / NOT PRODUCTION APPROVED**. 1step 후 STOP. 다음에는 설계자가 이 실측 비용을 보고 multi-step을 계속할지 force 비용이 실제 blocker인지 결정한다. 이번에는 자동 확장·최적화하지 않았다.
