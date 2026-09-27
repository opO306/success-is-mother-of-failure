# 현재 상태

**최종 갱신:** 2026-09-28 — 현재 상태 대시보드. 과거 기록은 [상태 역사](docs/history/PROJECT_STATE_HISTORY_THROUGH_2026-09-27.md)에 원문 전체를 보존한다.

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
