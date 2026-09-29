# 현재 상태

**최종 갱신:** 2026-09-29 — 현재 상태 대시보드. 과거 기록은 [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)에 원문 전체를 보존한다.

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
| **현재 세부 단계** | **outer formal bound ④ 진행 — Runtime Rounding Contract V1 구조 승인, ④-Liveness(D_valid) 경로 조사 v0 완료, 설계자 판단 Q1〜Q4 대기** |
| **다음 Gate** | **④-Safety(A-EV 선행) + ④-Liveness → ④ 최종 감사/동결 → ⑤ 독립 실측 교차검증** |

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

**④-4b 미해결 원인 진단(2026-09-27, 기준 `4088061`):** 기존 64-cell 결과의 76개 기록은
첫 shell 대기 cell 49개 + 미검사 shell 27개다. [진단](docs/active/C1B1_ROUNDING_DIAGNOSIS_V1.md)에서
74개는 두 끝 격자점의 실제 raw impulse가 다르고, 1개 singleton은 개별 판정 성공,
1개는 끝점은 0이지만 parent enclosure 미분리임을 기록했다.
현재 첫 shell projection에 서로 다른 output을 갖는 격자점 65개가 있어 **최소 65 uniform leaf가 필요하다**.
따라서 현재 projection을 유지한 동일-output cover는 64-cell 안에서 완료할 수 없다.
이것은 실제 궤적의 ReferenceUndecided 반례나 16384-bit 불가능성 증명이 아니다.
64-cell/16384-bit 한도·물리·D_valid는 유지한다. 다음 의무는 더 강한 이산 도달가능 제약 또는
서로 다른 output을 허용하는 전체 격자점의 rounding separation 증명이며 아직 미완료다.
추가 조건부 유도에서 첫 64회 정상 전이의 65개 kick 입력도 서로 다른 output을 가져야 함을 확인했다.
따라서 도달가능 제약만으로 64개의 동일-output cell을 만드는 것은 이 초기 상태의 해결책이 아니다.
**서로 다른 output을 허용하는 pointwise 판정 증명 표현이 우선**, 추가 불변량은 그 대상 축소의 보조 수단이다.

**④-4b multi-output 증명 계약 구현(2026-09-27):** 기존 constant-output 인증기를 보존한 채
[서로 다른 output의 결정성 인증](docs/active/C1B1_MULTI_OUTPUT_DECISION_V1.md)을 추가했다.
명시한 65개 서로 다른 impulse 입력을 **한 region·공통 256-bit**로 인증했다.
이것은 65점 전수 평가이며 큰 격자 구간이나 실제 궤적 전체의 인증은 아니다.
29개 그룹 전부 V′>0·V″<0, impulse 엄격 증가와 인접 separation 하한을 해석적으로 증명했다.
마지막 특이 구간은 내부 극값·zero crossing 없이 **전체 선언 격자점 553,997,943,205,884,291개**를
분할 없이 256-bit impulse=0으로 인증했다. singleton도 128-bit로 인증했다.
나머지 **27개 그룹은 격자 rounding-boundary margin 미증명**이다. 공통 수치 endpoint error bound는 확보했다.
새 coverage checker는 fresh shell projection의 정확한 gap 92개를 남긴다(원래 미해결 기록 76개와 다른 집계).
사용 region 3/64, precision cap 16384 유지. **R=20 및 ④-4b 전체 NotCertified**다.
물리 실행기·기존 인증기·도달 projection·181 Frozen D_valid는 변경하지 않았다.
⑤·E_min·전체 산란각은 계속 보류하며 다음 의무는 27개 큰 격자 domain 전체의 half-ulp 경계 분리 증명이다.
신규 직렬 시험 **41 passed, 22.82초**. **LOCAL FULL: 2471 passed + 1 strict xfailed, skip 0,
실패/error 0, 359.84초, exit 0**. 신규 41개 시험의 직렬/병렬 결과가 항목별로 동일하다.
컴파일러 출력 cp949 해독 경고 26건은 남아 있으며 해결됐다고 해석하지 않는다.
실행기·기존 인증기·도달 geometry·동결 fixture 등을 포함한 16개 파일이 `6184700`과 LF 바이트 동일하다.
증거: `runs/c1b1_multi_output_20260927/{local_full.log,local_full.xml,verification_summary.json,unchanged_contracts.json}`.

**④-4b boundary 역상 배제(2026-09-27, 기준 `d59b565`):**
[half-ulp boundary 증명](docs/active/C1B1_HALF_ULP_BOUNDARY_EXCLUSION_V1.md)에서 기존 미인증 domain 27개의
정확한 endpoint enclosure·ulp span·경계 개수를 기록했다. shell 24〜26은
**51개 경계 → 후보 정수 3개 → 직접 인증 3개**로 각 domain 전체를 256-bit 안에서 닫았다.
선언된 격자점 수는 각각 298,023,842,104,416,266 / 372,529,648,073,654,547 /
465,661,905,535,202,398개이며 실제 방문 점 수는 아니다.
나머지 **24개 큰 domain**은 경계 작업 한도 64를 넘어 symbolic-family 대상으로 남겼다.
경계 수는 249〜6,304,880,043,134,911,522개이며 후보 수는 미열거로 기록했다.
64-region과 16384-bit 유지. 별도 경계/후보 작업 한도는 물리 cap이 아니다.
새 compositor가 검증된 기존/신규 6개 region을 fresh geometry와 대조한 결과 gap은 92→89다.
**R=20 및 ④-4b 전체 NotCertified**, ④ 동결·⑤·E_min·전체 산란각 보류 유지.
기존 물리·D_valid·multi-output/constant-output 증명 및 fixture는 변경하지 않았다.
신규 직렬 **31 passed, 26.86초**. 최종 **LOCAL FULL: 2502 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 405.59초**, 컴파일러 cp949 해독 경고 27건.
신규 31개 결과는 직렬/병렬 항목별 동일하며, 관련 기존 소스/fixture 19개가 `d59b565`와 LF 바이트 동일하다.
증거: `runs/c1b1_boundary_exclusion_20260927/{local_full_final.log,local_full_final.xml,verification_summary.json,unchanged_contracts.json}`.
최대 precision 필드 보강 전의 LOCAL FULL(2501 passed, 403.78초)은 별도 이전 실행 로그로 보존한다.

**④-4b fractional phase 구조 조사(2026-09-27, 기준 `f275d0b`):**
[24개 식 조사](docs/active/C1B1_FRACTIONAL_PHASE_SURVEY_V1.md)는 원래 domain을 그대로 유지하고
ULP 단위 exact impulse를 정수 유리식 P(n)/Q(n)+지수 잔여항으로 분리했다.
P는 22차, Q는 29차이며 정확히 **Q=5^8·n^17·D_int(n)^2**다. 고정/2의 거듭제곱 분모가 아니고 점별 약분은 별도다.
4096-bit 수학 enclosure의 signed residual과 기존 numeric endpoint error를 합친 결과,
**shell 19〜23의 5개 domain**에서 guard<1/(2Q_max)가 성립했다(실행 precision 2048/2048/2048/4096/4096).
23개 domain의 유리식 exact tie는 bounded 합동류와 square valuation parity로 배제했고,
마지막 하나는 미해결 합동류를 정확히 **n=1071856711314178048 한 점**으로 줄였다.
그 점의 정확 유리식도 tie가 아니며 기존 finite-point 인증기에서 256-bit 이하로 결정된다.
따라서 유한 fallback 포함 rational tie 배제는 24/24다. 전체 impulse의 경계 분리로 연결 가능한 것은 충분조건을 만족한 5개뿐이다.
나머지 19개는 현재 residual 상한이 최소 간격보다 크며, 홀수 n에 대한 2-adic 정보만으로 간격을 더 키울 수 없다.
더 강한 signed modular family bound는 미증명이다. 현재 enclosure의 부호 미결정을 실제 부호 변화나 precision 실패로 해석하지 않는다.
이번 결과는 **survey_only**, family certificate 계약·독립 checker·coverage 연결은 아직 없다.
새 region 0개, 기존 **6/64 region·gap 89**, **R=20/④-4b NotCertified** 유지.
물리·기존 인증기/fixture·181 Frozen D_valid를 보존하며 ④ 동결·⑤·E_min·전체 산란각은 계속 보류한다.
다음은 충분조건 5개를 독립 checker로 연결하고 남은 19개의 실제 위상 거리 하한을 조사하는 것이다.
신규 직렬 **37 passed, 12.21초**. 최종 **LOCAL FULL: 2539 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 426.25초**, 컴파일러 cp949 해독 경고 27건.
신규 37개 결과는 직렬/병렬 항목별 동일하며, 관련 기존 소스/fixture/시험 23개가 `f275d0b`와 LF 바이트 동일하다.
181 probe의 긴 replay를 새로 실행한 결과는 아니다. 소스/fixture 보존과 이번 전체 회귀 검증을 구분한다.
증거: `runs/c1b1_fractional_phase_20260927/{local_full_final.log,local_full_final.xml,verification_summary.json,unchanged_contracts.json}`.
중간 집중 시험의 JSON 키 비교/API 호출 오류 및 최종 진단 필드 추가로 중단한 첫 전체 실행 로그는 별도로 보존하며 최종 결과로 세지 않는다.

**④-4b rational spacing family 인증(2026-09-28, 기준 `f0484af`):**
[별도 family checker](docs/active/C1B1_RATIONAL_SPACING_FAMILY_V1.md)는 survey/생성기를 import하거나 pass flag를 사용하지 않는다.
동결 component를 직접 미분해 exact P/Q·지수항 계수를 재구성하고, 닫힌 domain 전체 Q_max·signed residual·numeric E·strict guard를 재계산한다.
완전한 valuation/residue tree와 유한 exception을 검사하며 요구 precision과 실제 execution cap을 대조한다.
**shell 19〜23의 원래 5개 domain 전체 Certified**, p 상한 2048/2048/2048/4096/4096.
마지막 exception n=1071856711314178048은 정확 rational tie 배제 및 실제 point proof 256-bit 재검증.
momentum legal output도 exact triangle bound로 확인한다. 64-region·16384-bit, 원래 domain과 물리는 유지한다.
기존 6개와 새 5개를 각 checker로 확인한 fresh coverage는 **11/64 region·gap 84개**다.
남은 큰 family 19개에는 새 수학을 추가하지 않았으며 **R=20/④-4b 전체 NotCertified**를 유지한다.
④ 동결·⑤·E_min·전체 산란각은 계속 보류. 다음은 별도의 ④-4c modular-distance lower-bound survey다.
source-bound numeric error lemma·정수 EXP·동결 상수·기존 point API는 공통 기반으로 재사용하므로 전역 독립 물리 감사와 구별한다.
신규 직렬 시험 **54 passed, 32.93초**. 최종 **LOCAL FULL: 2593 passed + 1 strict xfailed,
skip 0, 실패/error 0, exit 0, 385.03초**, cp949 출력 해독 경고 25건은 남았다.
신규 54개 결과는 직렬/병렬 항목별 동일하며, 기존 관련 소스/fixture/시험 26개가 `f0484af`와 LF 바이트 동일하다.
181 probe의 장시간 replay를 새로 실행한 결과가 아니라 보존 해시와 이번 전체 회귀 검증이다.
증거: `runs/c1b1_family_checker_20260928/{local_full_complete.log,local_full_complete.xml,verification_summary.json,unchanged_contracts.json,exception_structure.json}`.
초기 검사에서 잡힌 integer / float division 오류와 이전 전체 실행(2590 passed, 427.65초)은 로그로 보존하며 최종 버전 검증과 구별한다.

**④-4c-1 exact modular-distance 조사(2026-09-28, 기준 `561a91e`):**
[19-domain 별도 survey](docs/active/C1B1_EXACT_MODULAR_DISTANCE_SURVEY_V1.md)는 원래 shell 0〜18의 domain을 유지하고
미리 정한 bounded selection의 **2,679점**에서 정수 Δ=|2P−(2k+1)Q|·약분·정확 경계 거리·분모 인수별 residue·gcd·generalized CRT를 기록했다.
관측 최소값은 선택한 점에만 해당하며 새 family 하한은 없다. **survey_only·새 region 0·11/64 region·gap 84·전체 NotCertified** 유지.
19개는 **4+1+14**로 갈린다. shell 0〜3은 residual guard≥½ ULP여서 unshifted rational 거리만으로 기존 조건을 닫을 수 없고,
shell 4는 guard<½지만 공통 M/(2Q_max) 방식에 필요한 M이 Q_min을 넘어 현재 구조가 너무 강하다.
shell 5〜18의 모든 선택 점은 guard보다 멀었지만 전체 격자 분리 증명은 없다.
특히 shell 15〜18의 선택 점 **570개** 모두에서 point CRT 하한이 M_req 이상이므로 다음 lemma 조사 후보다. 인증 승격하지 않는다.
D_int(0)=2^318·5^32와 gcd(n,D(n))|D_int(0)을 확인했다. D/D² remainder는 정수화 multiplier를 포함하며 역원을 가정하지 않는다.
모든 domain이 작은 modulus의 모든 residue를 포함하며, mod 5^8 단독 거리 하한은 실제 5의 배수 witness에서 0이다.
약분 전 큰 Δ나 16-bit zero를 강한 separation/tie로 해석하지 않는다. 이전 checker·물리·Frozen D_valid를 변경하지 않았고
기존 관련 소스/fixture/시험 30개가 `561a91e`와 LF 바이트 동일하다. 181 probe 장시간 replay 재실행은 아니다.
신규 직렬 **32 passed, 25.73초**. **LOCAL FULL: 2625 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 383.44초**, cp949 출력 해독 경고 25건 유지. 신규 32개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_modular_distance_20260928/{focused_final.log,focused_final.xml,local_full.log,local_full.xml,raw_samples_final.jsonl,unchanged_contracts.json,verification_summary.json,concept_alignment.json}`.
다음은 15〜18 우선의 **전 domain** 합동류 하한 조사이며 새 lemma가 확보되기 전에는 checker·coverage를 변경하지 않는다.
④ 동결·⑤·E_min·전체 산란각 보류 유지.

**④-4c-2 full residue-class 조사(2026-09-28, 기준 `23144df`):**
[shell 15〜18 전수 class survey](docs/active/C1B1_FULL_RESIDUE_CLASS_SURVEY_V1.md)는
n=2^a·5^b·u, gcd(u,10)=1의 모든 valuation/unit class와 필요한 normalized zero residue refinement를 포함한다.
원래 격자점 **230,627,472,909,852,564개**의 덮개를 **14,271개 분석 class**로 구성했다.
합계·닫힌 endpoint·class의 서로 겹치지 않음을 검사했다. 추가 point 표본은 없으며 singleton class 1,005개는 전체 허용 입력을 정확 계산했다.
**5,541개 class**에서 필요한 Δ 하한을 확인했지만 **8,730개 class의 가변 CRT gap은 미해결**이다.
shell별 미해결 class는 3272/2802/2065/591이고 새 shell 전체 lemma 후보 0, 실제 작은 Δ 입력 반례 0이다.
보장되는 2/5 공통 인수를 제거한 integer polynomial identity를 확인했고, 추가 odd gcd를 없어졌다고 가정하지 않았다.
Q′=F·v, gcd(v,10)=1인 경우 높은 모든 2/5 prime-power 제약은 Δ′≡2P′−F mod2F로 합쳐진다.
**미해결 5,370개 class**에서는 2gF<M_req이므로 odd quotient 범위를 제한하지 않는 이 고정 정보만으로 작은 Δ를 전부 배제할 수 없음을 확인했다.
예를 들어 n≡3 mod10 class는 고정 2/5 정보와 양립하는 비영 gap≤781250을 가진다. 실제 full Δ 반례라는 뜻은 아니다.
현재 남은 의무는 u^17·D_normalized²의 **가변 divisor와 odd quotient 범위**를 유지한 parametric gap lemma다.
고정 class가 full CRT residue를 하나로 정한다는 가정은 같은 class의 서로 다른 Q로 반박됐다.
**survey_only·새 region 0·11/64 region·gap 84·전체 NotCertified** 유지. shell 0〜14·기존 checker·물리·Frozen D_valid를 변경하지 않았다.
기존 관련 소스/fixture/시험 33개가 `23144df`와 LF 바이트 동일하다. 181 probe의 긴 replay 재실행은 아니다.
신규 직렬 **27 passed, 22.48초**. **LOCAL FULL: 2652 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 425.76초**, cp949 출력 해독 경고 25건 유지. 신규 27개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_residue_class_20260928/{focused_with_fixed_power.log,focused_with_fixed_power.xml,local_full.log,local_full.xml,unchanged_contracts.json,verification_summary.json,concept_alignment.json}`.
오류 문구 정규식에서 괄호를 escape하지 않아 실패한 중간 시험 로그는 보존한다. 알고리즘의 변조 거부 자체는 정상 작동했다.
shell 전체 하한이 확보되지 않았으므로 새 independent lemma checker/coverage 승격은 보류하고 ④ 동결·⑤·E_min·전체 산란각 보류도 유지한다.

**④-4c-3 normalized quotient-gap 조사(2026-09-28, 기준 `875aa31`):**
[정규화 gap·quotient 조사](docs/active/C1B1_NORMALIZED_QUOTIENT_GAP_SURVEY_V1.md)는 기존 shell 15〜18의 14,271 class 전체를 유지한다.
class 공통 인수 g에 맞춰 필요한 기준을 **ceil(M/g)**로 바꾸고,
기존 D² remainder 항등식을 선형 변수 치환과 scalar 정리 후 계수별로 재검사했다.
`Q′=B·D_normalized²`, `c·z=(A−c·h·B)D_normalized²+R`에서 홀수 h·multiplier·cofactor를 함께 보존한다.
R 부호만으로 gap을 판정하거나 c의 modular 역원을 가정하지 않는다. non-singleton P′/Q′ 차수는 22/29다.
exact Bernstein ratio 범위와 quotient coefficient coset을 조사했지만 **큰 class의 새 하한은 0개**다.
입력 8개 이하의 미해결 작은 class **654개·2,680 입력**을 전수 계산하고 별도 정수 평가로 확인해 class 하한을 추가했다.
기존 하한 5,541개와 합쳐 **6,195 class 하한**, **8,076 class 미해결**이며 shell별 미해결은 3014/2587/1894/581이다.
전체 shell lemma 후보 0·실제 작은 gap 반례 0이며, 큰 class의 느슨한 조건에 후보가 남는 것을 존재 증거로 바꾸지 않는다.
실제 유리식 gap 반례라도 전체 impulse 반올림 실패/16384-bit 초과 증거와는 별개다.
**survey_only·새 region 0·11/64 region·gap 84·④-4b NotCertified** 유지. 새 independent checker/coverage 연결은 없다.
기존 물리·D_valid·인증 관련 36개 파일은 `875aa31`과 LF 바이트 동일하며 181 probe replay 재실행은 아니다.
신규 집중 직렬 **34 passed, 1.38초**. **LOCAL FULL: 2686 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 433.59초**, cp949 경고 25건 유지. 신규 34개 직렬/병렬 결과는 항목별로 동일하다.
원자료 14,271행 해시·정규화 기준·작은 class 독립 전수·보존 해시·구상 경계는
`runs/c1b1_quotient_gap_20260928/{raw_verification.json,unchanged_contracts.json,concept_alignment.json,verification_summary.json}`에 기록한다.
다음은 가변 B(j)와 quotient의 같은-j 상관관계를 더 보존하거나 다른 분모 인수와 remainder를 함께 쓰는 lemma다.
④ 동결·⑤·E_min·전체 산란각 보류 유지.

**④-4c-4 same-input 필터 최소 구현(2026-09-28, 기준 `0bdfa49`):**
[같은 입력 필터·별도 checker 조사](docs/active/C1B1_SAME_INPUT_CORRELATION_SURVEY_V1.md)는
기존 미해결 8,076 class 전부의 정규화 항등식·홀수 h inventory를 검사한다.
`F_h=(A−c·h·B)V+R=c(2P′−hQ′)`를 같은 j에서 결합한 뒤 범위를 계산하며 m=ceil(M/g)를 유지한다.
입력 16개 이하 241 class와 사전 선정 대표 12개에만 깊이 4·노드 31의 추가 분할을 적용했다.
**추가 하한은 작은 241 class·2,980 입력이며 전부 singleton leaf까지 나눈 결과다.**
실제 큰 class symbolic 하한 0·실제 joint-polynomial-sign leaf 0, 합성 이차 사례의 개선과 구별한다.
class 하한 집계 **6,436**, 남은 **7,835 미해결**, 전체 shell lemma·실제 small-gap witness·새 region 0이다.
최소 proof object와 별도 checker는 원래 class/항등식/기준/정수 분할/홀수 inventory를 재구성한다.
builder를 import하지 않지만 frozen 물리 항등식과 기존 numeric foundation은 공유하며 새 독립 물리 감사는 아니다.
기존 6,195 survey 하한을 이번 checker로 일괄 승격하지 않았고 coverage 연결도 추가하지 않았다.
**④-4b NotCertified·11/64 region·gap 84·16384-bit·④ 미동결·⑤ 미착수** 유지.
기존 물리·D_valid·인증·직전 survey 관련 **39파일**은 `0bdfa49`와 LF 바이트 동일하다.
새 집중 직렬 **38 passed, 9.06초**. **LOCAL FULL: 2724 passed + 1 strict xfailed, skip 0,
failure/error 0, exit 0, 453.76초**, cp949 출력 해독 경고 25건 유지. 신규 38개 직렬/병렬 결과가 항목별로 같다.
증거: `runs/c1b1_same_input_20260928/{raw_classes_final.jsonl,proofs_final.jsonl,raw_verification.json,unchanged_contracts.json,concept_alignment.json,verification_summary.json}`.
범용 증명 언어·창고·자동화·B 연결은 미구현이다. 다음은 실제 29차 식의 같은-j 조건을 열거 없이 유지할 lemma다.

**④-4c-5 shell 18 hard-case 탐색 실현 가능성 조사(2026-09-28, 기준 `0bab51b`):**
설계자 판정으로 h 합동 lemma 방향은 **보류(폐기 아님)**하고 (b) Lefèvre/SLZ 계열의 가장 싼 단계부터 실측했다.
[조사 결과](docs/active/C1B1_HARD_CASE_SEARCH_SURVEY_V1.md)는 ψ=P/Q−½의 원래 shell 18 domain 전체에서
블록별 보간다항식 + 엄밀한 보간 오차 δ(도함수 분자 N_k의 Bernstein 비율 상한)를 쓰고, search threshold를 **T=G+δ**(G는 ④-4c-1의 고정 guard, 약 2^-1614)로 유도했다.
affine은 거짓 후보를 수천 개 이하로 두려면 블록 약 47억 개가 필요해 부적합했고, **quadratic L=2^34(블록 4,547,510)**로 shell 전체를 실행했다.
교차 수 **1,568,498**은 half-ulp fixture의 경계 수와 정확히 같고, 후보 **109개**를 원래 P/Q로 전부 재평가한 결과 **hazard 0·거짓 후보 109**다.
별도 checker(생성기 import 금지)가 superblock **1024/1024**를 독립 재계산해 일치했다. 6 워커로 생성기 562초·checker 582초.
합성 12설정과 실제 shell 18 창 24설정의 brute force 대조는 모두 **누락 0**(창은 대조를 위해 τ를 명시적으로 키움)이며, 결함 주입 4종과 proof row 조작을 잡았다.
cubic은 오차만 계산했고 lattice/SLZ는 구현하지 않았다. 교차별 처리 비용은 경계 수에 선형이라 경계가 격자점보다 많은 shell 0〜4에는 원리적으로 쓸 수 없고,
고정 guard로 2GN을 계산하면 shell 0〜6은 guard 안 입력이 휴리스틱으로 매우 많아 전체 impulse를 대상으로 한 별도 설계가 필요하다(추정, 미측정).
**survey_only**: 인증 계약·coverage 연결 없음, **④-4b NotCertified·11/64 region·gap 84·16384-bit·새 region 0** 유지, shell 0〜17로 일반화하지 않는다.
checker는 동결 P/Q 항등식과 기존 guard를 공유하므로 새 독립 물리 감사가 아니다. 기존 파일 수정 0(신규 5파일).
신규 집중 직렬 **40 passed, 13.86초**. **LOCAL FULL: 2764 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 455.87초**. 신규 40개 직렬/병렬 결과가 항목별로 같다.
이번 실행 요약에는 컴파일러 인코딩 경고 줄이 없었으나 원인을 조사하지 않았으므로 해결로 보고하지 않는다.
증거: `runs/c1b1_hard_case_20260928/{survey_full.json,survey_full.log,focused_final.log,focused_final.xml,local_full.log,local_full.xml,local_full.exit,verification_summary.json,attempt_notes.json}`.
다음 판단: shell 18 결과의 인증 계약 승격 여부, shell 17→15 실측 확대 여부, shell 0〜6 별도 설계 여부.

**④-4c-6 shell 18 hard-case 인증서(2026-09-28, 기준 `7ab8de3`):**
설계자 판정(1)에 따라 ④-4c-5 결과를 [인증 계약·proof object](docs/active/C1B1_HARD_CASE_CERTIFICATE_V1.md)로 올렸다.
family checker와 같은 잠금을 건다: 외부 domain binding, frozen P/Q, residual/numeric error 출처와 G 재계산, precision 4096 ≤ execution limit ≤ 16384, legal momentum 출력, source 해시.
verify는 superblock 1024행의 도함수 상한·교차 수·후보 구간을 전부 다시 계산해 정확히 대조하고, 후보 **109개**를 원래 P/Q로 재평가한다(**hazard 0**).
**shell 18 원래 domain 전체(격자점 78,125,618,227,463,141개) Certified.** 통과 뒤 계산한 **fresh coverage는 12/64 region·gap 83**이며 shell 18 gap은 0이다.
남은 gap은 shell 0에 65개, shell 1에 2개, shell 2〜17에 각 1개다. **R=20/④-4b 전체 NotCertified**, ④ 미동결·⑤ 미착수다.
인증서 1024행은 ④-4c-5 생성기 행과 전부 일치한다. 저장 JSON을 그대로 읽은 전체 재검증도 통과했다(560.7초). 독립 물리 감사는 아니다(동결 P/Q·numeric lemma·정수 EXP 공유).
첫 전체 실행은 superblock을 quadratic 블록 하나로 통째 처리한 결함으로 1시간 46분 멈췄다. build/verify가 같은 함수를 공유해 시험이 못 잡은 유형 A다.
수정 뒤 교차 구현 대조·회귀·작업 한도 시험을 추가했다. 설명문 수정 뒤 전체를 재생성했으며 인증서·coverage가 이전 실행과 동일하다.
최종 실행 build 551초·verify 547초·coverage 합성 567초(6 워커). 신규 직렬 **34 passed**(관련 74개 65.95초).
**LOCAL FULL: 2798 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 448.71초**, 신규 74개 직렬/병렬 항목별 동일, 로그에 경고 줄 없음(원인 미조사).
증거: `runs/c1b1_hard_case_certificate_20260928/{certificate_full.json,certificate_full.log,verify_wire.log,focused_serial.xml,local_full.log,local_full.xml,attempt_notes.json}`.
다음은 ④-4c-7 shell 17 단독 확장성 실측이다(16/15 함께 하지 않음). shell 0〜6은 전체 impulse I(n)=P/Q+S의 별도 설계 트랙으로 기록만 한다.

**④-4c-7 shell 17 hard-case 확장성 실측(2026-09-28, 기준 `1d75da3`):**
설계자 지시대로 shell 17 **하나만** 같은 생성기·checker·정책으로 쟀다([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md)).
블록 3,638,015개, 교차 **8,645,949**(half-ulp fixture 경계 수와 같음), 후보 **827**(휴리스틱 예상 2,148), exact recheck **hazard 0**, 독립 checker 1024/1024.
brute force 대조(합성 12, 실제 창 24)는 누락 0이다. 병렬 효율은 생성기 0.986, checker 0.991이다.
교차가 5.5배로 늘었지만 생성기 CPU는 오히려 줄었고(2,989초), checker CPU는 35% 늘었다(4,654초).
두 실행으로 푼 추정 교차당 비용은 생성기 약 45 µs, checker 약 256 µs다. 실행마다 흔들리며 측정이 아니다.
**survey_only**: 인증·coverage 변경 없음, **12/64·gap 83** 유지, shell 16/15로 확장하지 않았다.
이 과정의 결함 세 가지(옛 coverage 숫자 고정, 줄바꿈 의존 해시, 전제가 틀린 시험 단언)는 수정 뒤 재실행했고 기록으로 보존한다. 세 실행의 결정적 결과는 모두 같다.

**native 리눅스 빌드와 원격 노드(2026-09-28, `90efde0`):** native harness가 Windows(MSVC, 명령 그대로)와 리눅스(g++/nvcc)를 모두 빌드한다.
원격 Vast 노드(RTX 3090, CPU 32)에서 native·GPU 시험 104개가 Windows와 항목별로 같은 결과로 통과했다.
원문 참조 파일도 복사했다. 그래서 **원격 전체 시험이 skip 0으로 2807개를 실행**한다(`894cf5e`에서 1건 실패 → 줄바꿈 해시 수정 `91a5c38`).
원격은 LOCAL FULL을 대신하지 않는다. Windows 경로(MSVC)는 로컬에서만 확인된다.
**LOCAL FULL(`91a5c38`): 2807 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 405.49초.**
증거: `runs/native_linux_port_20260928/{windows_native.*,linux_native.*,local_full.*}`, `runs/c1b1_hard_case_shell17_20260928/{survey_full.json,local_full.*,first_run/,second_run/}`.
다음 판단(설계자): shell 17 인증 승격 여부, shell 16/15 확장 여부. shell 0〜6 전체 impulse 트랙은 기록만 한다.

**④-4c-8 shell 17 hard-case 인증서(2026-09-28, 기준 `ce5f28f`):**
설계자 판정대로 shell 17을 ④-4c-6과 **같은 계약**으로 올렸다([계약·결과](docs/active/C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md)). 인증 모듈은 수정하지 않았고, shell 17 driver만 추가했다.
단계: build → verify → 저장 JSON 재로드 후 전체 검증 → fresh coverage(shell 18·17 재검증 포함).
후보 **827개**를 전부 정확 재평가했다(**hazard 0**). **shell 17 원래 domain 전체(격자점 62,500,618,227,463,141개) Certified.**
**fresh coverage 13/64 region·gap 82**이며 shell 17·18 gap은 0이다. **R=20/④-4b 전체 NotCertified**다.
인증서 1024행은 ④-4c-7 생성기 행과 전부 일치한다.
원격 32스레드(Ryzen 9 5950X, 물리 16코어) 실측: build·verify·저장본 verify 각 약 203초 wall/약 6,380 CPU초(효율 0.98), coverage 361초. 전체 16분 15초.
이 값으로 다시 푼 shell 16 검증 1회는 약 2.0×10⁴ CPU초(32스레드 단계당 약 11분)이고, shell 15는 약 9.7×10⁴ CPU초다. 추정이며 측정이 아니다.
**LOCAL FULL(`8d45209`): 2815 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 408.27초.**
**REMOTE LINUX FULL(같은 커밋): 2815 passed + 1 strict xfailed, skip 0, 356.36초.** 시험 2816개가 항목별로 같다.
리눅스는 작업자를 fork로 띄워 DeprecationWarning이 6건 나왔다. 그래서 spawn 전달 검증은 Windows에서만 실제로 일어난다.
증거: `runs/c1b1_hard_case_certificate_shell17_20260928/{certificate_full.json,certificate_full.log,local_full.*,remote_linux_full.*}`.
다음 판단(설계자): shell 16 survey_only 진입 여부. shell 15는 그 뒤에 따로 판단한다.

**④-4c-9 shell 16 survey_only(2026-09-28, 기준 `018bb65`):**
설계자 판정: shell 16은 인증에 앞서 survey_only 전수 조사만 한다. coverage·인증 상태는 바꾸지 않는다([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md)).
원격 32스레드 실행 결과는 다음과 같다.
- 교차 **46,892,493**(fixture 경계 수와 같음), 후보 **6,581**, **hazard 0**(독립 재평가 동일), checker **1024/1024**, brute force 누락 0.
- 생성기 213초/6,719 CPU초, checker 628초/19,751 CPU초, 효율 0.98, 작업자 메모리 약 30 MB.
- 같은 기계에서 다시 돈 shell 17 기준선의 행이 기존 fixture와 같다.
- shell 17 대비 교차 5.42배, 후보 7.96배, **후보 밀도 1.47배**, checker CPU 3.10배.
- 후보는 휴리스틱 2N(G+δ)를 일정 비율(0.43→0.39→0.37)로 따르며, 밀도 증가는 δ 증가로 설명된다(구현자 해석). 판정 기준의 "밀도 변화" 항목이므로 설계자 판단 사항이다.
- 예측했던 shell 16 checker 약 2.0×10⁴ CPU초와 실측 차이는 약 1%다. shell 15 조사 재추정은 원격 약 1시간 5분이다.
- 검증: 설계자 판정대로 LOCAL FULL은 생략했다. 관련 시험 101개와 변경 범위(새 파일만, 해시 고정 소스 4개 불변)를 확인했다. 새 시험 10개는 아직 기준선 2815에 포함되지 않았다.
증거: `runs/c1b1_hard_case_shell16_20260928/{survey_full.json,survey_full.log}`.
다음 판단(설계자): 밀도 변화 해석 수용 여부 → shell 16 인증 여부 → shell 15 조사 진입 여부.

**④-4c-10 shell 16 hard-case 인증서(2026-09-28, 기준 `a4eb67b`):**
설계자 판정: shell 16 survey의 후보 밀도 증가(1.47배)는 δ 증가로 설명 가능한 **진행 판단용 관측**으로만 받아들이고, 증명으로 승격하지 않는다. 인증 여부는 hazard 0·checker 일치·brute-force 누락 0·구조 불일치 없음·효율 유지·메모리 문제 없음·비용 예측 오차 약 1%로 판단해 shell 16 인증을 승인했다([계약·결과](docs/active/C1B1_HARD_CASE_CERTIFICATE_SHELL16_V1.md)).
계약은 shell 17과 완전히 같다(모듈 미수정). fresh coverage는 shell 18·17·16 세 인증서를 함께 재검증해 계산했다.
**shell 16 원래 domain 전체(격자점 50,000,618,227,463,141개) Certified.** 후보 **6,581개** 전부 정확 재평가, **hazard 0**.
**fresh coverage 14/64 region·gap 81**이며 shell 16·17·18 gap은 0이다. **R=20/④-4b 전체 NotCertified**다.
인증서 1024행은 ④-4c-9 생성기 행과 전부 일치한다. 원격 32스레드 실측: build·verify·저장본 verify 각 약 628초/19,760 CPU초(효율 0.98), coverage(세 인증서 재검증) 988초/30,590 CPU초. 전체 47분 57초.
예측한 shell 16 검증 비용(약 2.0×10⁴ CPU초)과 실측(19,761초)의 차이는 약 1%다.
**LOCAL FULL(`0117cd8`): 2834 passed + 1 strict xfailed, skip 0, failure/error 0, exit 0, 398.68초.**
**REMOTE LINUX FULL(같은 커밋, 32워커 재실행): 2834 passed + 1 xfailed, skip 0, 361.87초, 2835개 항목별 로컬과 완전 동일.**
첫 원격 실행에서 `test_primal_precision.py`의 마지막 시험이 1회 실패했다. 원인은 시험 결함이다: xdist가 시험을 개별 단위로 나눠, 모듈 전역 `FELT`를 채우는 시험들과 다른 작업자에 배정되면 빈 리스트를 읽는다. 회귀는 아니지만 열린 결함으로 남긴다(처음의 "스케줄링 문제" 기록은 부정확해 정정).
증거: `runs/c1b1_hard_case_certificate_shell16_20260928/{certificate_full.json,certificate_full.log,local_full.*,remote_linux_full.*}`.
다음 판단(설계자): shell 15 survey_only 진입 여부(원격 약 1시간 5분 추정).

**설계자 판정 — shell 15를 마지막 확장성 조사로 두는 방향(2026-09-28):**
shell 15는 survey_only 한 번만 한다. 결과를 본 뒤 **현재 shell별 전수 hard-case 탐색 방식을 shell 14 이하로 계속 내려가지 않는다(STOP)**.
STOP은 반올림 연구 전체 중단이 아니다. exact 반올림 의미(정확한 값을 한 번 반올림)는 유지한다. 버리는 것은 "shell마다 무식하게 전수 인증"이라는 방법이다.
STOP 뒤 두 갈래: (A) 더 싼 수학적 방법(예: lattice reduction) 조사, (B) 판정 불가능한 부분을 명시적으로 멈추는 조건부 계약으로 정리.
**Proof Warehouse**(별도 브랜치 `claude/proof-warehouse-architecture-skrgwm`, 설계 문서만, 코드 0)는 **구현 보류·문서만 보존**한다. 반올림 전략이 바뀌면 저장할 proof의 양·종류도 달라지므로, 지금 v0를 시작하지 않는다. master와는 아직 합치지 않는다.
**화학/다입자**는 이번 결정에 포함되지 않는다. Ar-Ar 반올림 증명에 갇히지 않기 위한 방향 경고로만 기록한다. 지금 착수하지 않는다.
전체 순서: shell 16(완료) → shell 15 survey → 전수 방식 종료 판정 → 반올림 계약 최종 정리 → C1-B1 나머지 정리(inbound/inner/전체 산란각/E_min/native J) → C1-B1 freeze → 다입자·화학 조사. B/L은 건드리지 않는다.

**shell 15 hard-case 전수 조사(2026-09-28, 기준 `ab81005`) — 마지막 shell별 전수 조사:**
설계자 판정대로 shell 15를 마지막으로 한 번만 돌리고, **shell별 전수 hard-case 탐색 방식을 shell 14 이하로 잇지 않는다(STOP)**([결과](docs/active/C1B1_HARD_CASE_SEARCH_SHELL15_SURVEY_V1.md)).
STOP은 반올림 연구 중단이 아니다. exact 반올림 의미는 유지하고, "shell마다 전수 인증"이라는 방법만 버린다.
원격 32스레드 실측: 교차 **250,139,754**(fixture 경계 수와 같음), 후보 **54,419**, **hazard 0**, checker **1024/1024**, brute force 누락 0.
같은 기계에서 다시 돈 shell 16 기준선의 행이 기존 fixture와 완전히 같다.
shell 16 대비 교차 5.33배, 후보 8.27배, 후보 밀도 1.55배, checker CPU 4.70배. ④-4c-9 예측(shell 16 실측 기반)과 이번 실측의 오차는 생성기 약 −1%, checker 약 −0.7%다.
교차당 비용(생성기 약 87µs, checker 약 363µs)으로 손 계산하면 shell 14 조사는 약 5시간, 인증은 약 17시간, shell 13은 각각 약 27시간·88시간으로 추정된다(측정 아님). shell 0〜4는 경계 수가 격자점 수보다 많아 교차별 처리가 원리적으로 불가능하다.
검증: survey_only라 LOCAL FULL은 생략했다. 새 시험 10개와 관련 시험 28개 통과, 변경은 새 파일만이며 해시 고정 소스 4개는 불변이다.
증거: `runs/c1b1_hard_case_shell15_20260928/{survey_full.json,survey_full.log}`.
다음 판단(설계자): 남은 gap 81개를 (A) 더 싼 수학적 방법(lattice reduction/SLZ, 또는 shell 0〜6 전체 impulse 트랙)으로 좁힐지, (B) 판정 불가를 명시적으로 멈추는 조건부 계약으로 정리할지.

**실행 기반 정밀도 조사(runtime stress survey, 2026-09-28〜29, survey_only):**
설계자 질문 "실제 궤적의 반올림 판정은 거의 128〜256 bit에서 끝나는가"를 실행기 무변경·읽기 전용 계측으로 쟀다([결과](docs/active/C1B1_RUNTIME_STRESS_SURVEY_V1.md)).
- R ≤ 20 bohr 주행: 궤적 10,481개·판정 약 1억 9,835만 회, 128 bit 99.36%·256 bit 0.644%, **512+ 0·판정 불가 0**. D_valid 안/밖 모두 같은 구조.
- hard-case 61,936점: 전부 256 bit(128 bit 구간 폭이 ulp의 2^3〜2^25배라 원리적으로 128 불가).
- 원인(관측에 맞는 해석, 증명 아님): 256 비율 = 128-bit 구간 폭(약 2^-7.5 ulp). 값이 경계에 대해 고르게 흩어진 것과 맞다.
- **처음 주행은 R=20으로 돌아오면 멈춰 pre-tail shell 0〜26에 들어가지 않았다.** 바깥 비행 14개로 R_J=10,240까지 가자
  R 640 이상은 256 bit 100%, 256-bit 폭 최대 2^-126 ulp, 판정 3,636만 회 **512+ 0**.
- 인증·coverage 변경 없음(14/64·gap 81), **④-4b NotCertified·④ 미동결·⑤ 미착수** 유지. 운영 실패(분석 파일로 캠페인 종료, 노드 약 12시간 유휴 과금)는 문서 5절에 기록.
- 검증: 관련 시험 26개는 원격 Linux에서 통과(캠페인 코드 기준). LOCAL FULL은 설계자 지시로 92%에서 중단했고(통과·기준선으로 세지 않음, 로그는 미완료 실행으로 보존), 변경이 새 파일·시험·문서뿐이라 관련 시험으로 대체했다. LOCAL FULL은 작업 묶음 끝의 push 또는 기준선 갱신 직전에 한 번 실행한다.
다음 판단(설계자): 전수 사전 인증 대신 "실행 + 판정 불가 정지 + 국소 증명" 구조를 검토할지, 남은 형식 의무(256-bit 폭 해석적 상한·유리수 tie 배제 확장·정지 계약) 범위.

**Runtime Fail-Closed Contract v0 + 국소 witness prototype(2026-09-29, 설계자 승인):**
([결과](docs/active/C1B1_RUNTIME_FAIL_CLOSED_V0.md)) 실행기 무변경.
- 1단계(계약 시험): 판정 불가·drift 선분·위치 범위로 거부된 step은 run을 전혀 바꾸지 않는다. 일찍 쓰는 결함 step을 검사가 잡는다. 6 passed.
- 2단계(prototype, survey_only): cap을 시험 설정으로 128에 두고 "정지 → 그 충격량만 계약 schedule로 재판정 → 저장 형태 검증 → 같은 step 재실행"을 돌렸다.
  궤적 3개(1,640 / 5,775 / 21,056 step) 모두 **매 step raw 상태가 정상 실행과 동일**, 정상 256 판정 = 거부 = witness(25/77/239). 변조 15종 거부. 23 passed.
- 한계: witness는 실행기와 같은 평가기를 쓰는 "executor rounding decision 재검증 witness"이며 독립 물리 검증이 아니다.
  실제 16384 판정 불가는 범위 밖(정지 유지). witness는 `runs/`에만 둔다. 14/64·gap 81·④-4b NotCertified 유지.
- 검증: LOCAL FULL 생략 / 관련 시험으로 대체(83 passed + 1 strict xfailed) / 새 파일만 추가.
다음 판단(설계자): 이 구조를 정식 방향으로 검토할지, 실제 16384 실패용 국소 증명 방법, 차등 계약·witness 형식·④ 동결 조건.

**설계자 판정(2026-09-29):** runtime + 국소 증명을 C1-B1 반올림 완전성의 **주력 방향으로 승격**. 버리는 것은 shell별 경계 사전 열거 방법뿐이며 ④의 의무는 약화하지 않는다.
④를 **Safety**(틀린 상태를 만들지 않음)와 **Liveness**(인정한 영역의 판정이 모두 해결됨)로 나눈다. 둘 다 닫혀야 ④ 동결. 실제 16384 실패용 point prover는 설계만 하고 구현하지 않는다.
계약: [Runtime Rounding Contract V1](docs/active/C1B1_RUNTIME_ROUNDING_CONTRACT_V1_PROPOSAL.md) — **구조 승인(2026-09-29).**
- 네 상태 RESOLVED / STOPPED / WITNESS_RESOLVED / UNPROVED(영구 STOP).
- **④-Safety**는 runtime 구조로 닫는다. 남았던 Fail-Closed 시험(`VMHalt`, 운동량 범위)을 추가해 8 passed.
  **후속 판정 D3:** A-EV(평가기 구간이 참값을 포함)를 S1〜S6보다 앞선 **선행조건**으로 둔다. A-EV 미해결이면 ④-Safety는 **Conditional**이다(현재 미해결).
- **④-Liveness 대상 = D_valid.** 실행 가능 영역(입장 계약)과 분리. 별도 수학적 보장이 필요하며 **NotCertified**.
  실행 단위 증명서 단독으로는 닫지 않는다. shell 전수 열거 대신 더 싼 방법(해석적 bound·prover completeness·Proof Box)으로 덮는다.
  (당시 문서의 "정확히 7개 에너지의 b 한 줄씩"은 구현자의 잘못된 요약이었다. 아래 조사 v0 참조.)
- 실제 16384 실패: point prover가 고정밀을 **탐색 도구로** 쓸 수 있으나, 정확 산술로 검증 가능한 certificate가 있을 때만 재개.
  **후속 판정 P1a:** 평가기를 cap 위에서 다시 돌리는 verifier는 불허. 허용은 (A) cap ≤ 16384 안의 검증 가능한 interval witness, (B) 평가기와 다른 수학적 근거(정확 유리수 부등식·modular-distance·exact tie·대수적 bound). 기준은 "검증할 때 고정밀 결과를 믿어야만 하는가".
- Runtime Proof Cache(엄격·매 사용 재검증)와 Proof Warehouse(실행 경로 밖) 분리, Hazard Atlas 판단 권한 0.
- 구현(wrapper·prover·cache)은 각각 별도 설계·승인 뒤. 14/64·gap 81·④-4b NotCertified 유지.
- **순서 변경(후속 판정):** Liveness 경로 조사 → point prover 설계 → 정말 필요하면 runtime wrapper. `_decide`의 `VMHalt`/`ExecutorLimitExceeded` 예외 분류 불일치는 ④ 최종 동결 전 정리 대상(지금은 실행기 무변경).

**④-Liveness(D_valid) 수학 경로 조사 v0(2026-09-29, survey_only, 문서만):**
([조사](docs/active/C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md)) 코드 변경·Vast·시험 추가 0. 수치는 동결 fixture·기존 모듈·기존 `runs/`를 읽기만 한 스크래치 계산이다.
- **전제 정정(먼저 공개):** 코드상 D_valid는 7개 에너지만이 아니다. **L**(1e-8〜약 0.1418 De, 모든 b, 임의 3D 배치) + **H**(약 0.9974〜10 De, 모든 b, 임의 배치) + **F**(7개 에너지의 궤도 포획 경계 옆 짧은 b 구간 14개, 폭 0.04〜0.14 bohr, b=0 없음)로 이루어진다. 계약 V1 2.2절을 정정했고 L0 재확인을 요청했다.
- **기존 형식 증거와 D_valid의 겹침:** 14 region은 전부 **+x축 1D 입력**이라 F 궤적과는 겹치지 않고, L·H의 정면충돌 상태에만 해당한다. 안쪽 R<20의 형식 증거는 없다. 실행 조사의 F 몫은 안쪽 6궤적이고 바깥 비행은 0이다.
- **결론:** 정량 Liveness(16384 안에서, 또는 정밀도 상한이 있는 증명으로)의 싼 경로는 없다. 안쪽은 exp가 지배해 유리식·합동류 방법이 원리적으로 불성립하고, 경계 전수 방법은 평면/3D에서 폭발한다.
- **새 후보(구현자 유도, 인증 아님):** 계수 전부 유리수 + 서로 다른 exp 지수 9개 → Lindemann–Weierstrass로 **모든 격자 입력(q_k≠0)의 정확 충격량은 유리수가 아니다 → 정확 tie 불가능**(exp 계수함수 5개가 양의 근 없음, 공약수 1). 영역 크기·차원 무관, 정성적. 엄밀 유리수 구간 prover와 결합하면 D_valid 전체의 **정성적** Liveness 후보가 된다.
- 기타: 격자 KDK의 정확한 시간 가역성(유도), 운동량 offset 다발(위치열 공유)을 기록했다. 둘 다 입력 간격 문제를 줄이지는 않는다.
- 검증: LOCAL FULL 생략 / 관련 시험 해당 없음 / 문서만 변경.
다음 판단(설계자): **Q1** L0 재확인, **Q2** Liveness가 정성인지 정량인지, **Q3(P1b)** 엄밀 유리수 구간 certificate가 P1a의 B 범주인지, **Q4** "모든 run이 R_J 도착"을 ④-Liveness에 포함할지.

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
계약상 `numerical_validated`에는 이 fixture 에너지들 외에 capture band가 없는 두 넓은 영역도 포함된다. L은 b_orb > 2Re인 저에너지(약 0.1418 De 미만), H는 장벽 꼭대기 위(약 0.9974 De 초과)이며 둘 다 모든 b와 임의 배치를 받는다([Liveness 조사 v0](docs/active/C1B1_DVALID_LIVENESS_ROUTE_SURVEY_V0.md) 2.1절).
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
| ④-4c-10 shell 16 인증서 LOCAL FULL (2026-09-28, `0117cd8`) | **2834 passed + 1 strict xfailed, failure/error 0, skip 0, 398.68초**. REMOTE LINUX FULL 재실행 2834 passed, 361.87초, 항목별 동일(첫 원격 실행 간헐적 실패 1건은 재현 안 됨) | `runs/c1b1_hard_case_certificate_shell16_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_shell16_20260928/local_full.xml` |
| ④-4c-8 shell 17 인증서 LOCAL FULL (2026-09-28, `8d45209`) | **2815 passed + 1 strict xfailed, failure/error 0, skip 0, 408.27초**. REMOTE LINUX FULL 같은 커밋 2815 passed + 1 xfailed, skip 0, 356.36초, 항목별 동일 | `runs/c1b1_hard_case_certificate_shell17_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_shell17_20260928/local_full.xml` |
| ④-4c-7 shell 17 조사 + native 리눅스 빌드 LOCAL FULL (2026-09-28, `91a5c38`) | **2807 passed + 1 strict xfailed, failure/error 0, skip 0, 405.49초**. 원격 전체(`894cf5e`)는 skip 0·2806 passed·1 failed(줄바꿈 해시, 이후 수정) | `runs/c1b1_hard_case_shell17_20260928/local_full.log`, `runs/c1b1_hard_case_shell17_20260928/local_full.xml` |
| ④-4c-6 shell 18 hard-case 인증서 LOCAL FULL (2026-09-28) | **2798 passed + 1 strict xfailed, failure/error 0, skip 0, 448.71초**, 로그에 경고 줄 없음(원인 미조사). 신규 관련 74개 직렬/병렬 동일 | `runs/c1b1_hard_case_certificate_20260928/local_full.log`, `runs/c1b1_hard_case_certificate_20260928/local_full.xml` |
| ④-4c-5 shell 18 hard-case search survey LOCAL FULL (2026-09-28) | **2764 passed + 1 strict xfailed, failure/error 0, skip 0, 455.87초**, 요약에 경고 줄 없음(원인 미조사). 신규 40개 직렬/병렬 동일 | `runs/c1b1_hard_case_20260928/local_full.log`, `runs/c1b1_hard_case_20260928/local_full.xml` |
| ④-4c-4 same-input 최소 구현 LOCAL FULL (2026-09-28) | **2724 passed + 1 strict xfailed, failure/error 0, skip 0, 453.76초**, cp949 경고 25건. 신규 38개 직렬/병렬 동일 | `runs/c1b1_same_input_20260928/local_full.log`, `runs/c1b1_same_input_20260928/local_full.xml` |
| ④-4c-3 normalized quotient-gap survey LOCAL FULL (2026-09-28) | **2686 passed + 1 strict xfailed, failure/error 0, skip 0, 433.59초**, cp949 경고 25건. 신규 34개 직렬/병렬 동일 | `runs/c1b1_quotient_gap_20260928/local_full.log`, `runs/c1b1_quotient_gap_20260928/local_full.xml` |
| ④-4c-2 full residue-class survey LOCAL FULL (2026-09-28) | **2652 passed + 1 strict xfailed, failure/error 0, skip 0, 425.76초**, cp949 경고 25건. 신규 27개 직렬/병렬 동일 | `runs/c1b1_residue_class_20260928/local_full.log`, `runs/c1b1_residue_class_20260928/local_full.xml` |
| ④-4c-1 modular-distance survey LOCAL FULL (2026-09-28) | **2625 passed + 1 strict xfailed, failure/error 0, skip 0, 383.44초**, cp949 경고 25건. 신규 32개 직렬/병렬 동일 | `runs/c1b1_modular_distance_20260928/local_full.log`, `runs/c1b1_modular_distance_20260928/local_full.xml` |
| ④-4b boundary 역상 배제 최종 LOCAL FULL (2026-09-27) | **2502 passed + 1 strict xfailed, failure/error 0, skip 0, 405.59초**, cp949 경고 27건. 신규 31개 시험 | `runs/c1b1_boundary_exclusion_20260927/local_full_final.log`, `runs/c1b1_boundary_exclusion_20260927/local_full_final.xml` |
| ④-4b 미해결 진단 LOCAL FULL (2026-09-27) | **2430 passed + 1 strict xfailed, failure/error 0, skip 0, 362.74초**, cp949 경고 25건. 진단 시험 17개 | `runs/c1b1_unresolved_diagnosis_20260927/local_full.log`, `runs/c1b1_unresolved_diagnosis_20260927/local_full.xml` |
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
