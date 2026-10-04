# H₂ Multi-Step Pilot V0 — Layered Validation + Checkpoint/Rollback

**H2_MULTISTEP_LAYERED_VALIDATION_PILOT_SUPPORTED / NOT CERTIFIED / NOT PRODUCTION APPROVED.**

2026-10-04. C0 이후 추가5steps만 실제 실행하고 STOP했다. 동일한 전자 모델/basis/solver/binary64/guard와 dt/h/Verlet 계약을 유지한 workflow 증거다. 물리 정확도 유지의 엄밀한 증명, force/BO dynamics/진동/formation/장시간 인증, canonical A 채택은 아니다. 전체 source hash 감사의 탐지 시점만 시작/끝으로 옮겼으며 숨겨진 모든 오류의 탐지 보장은 없다.

## GIT STATE / CAMPAIGN CONTRACT

시작HEAD `fddb6957947045257c8a591490d10a666dab0f93`, branch codex/h2-representation-pilot1; 기존 Pilot worktree 사용. root master 및 원격 master `0f7b744`, 원격 Pilot `264f588` 유지 확인. 새 독립 Pilot/시험/문서만; 기존 계산기/공용/frozen source·공식 최적화branch 변경0, merge/rebase/push0. 최종commit SHA는 Git과 Git밖 postcommit receipt에서 확인한다.

R=bohr,E=hartree,F=Eh/bohr,mass=electron mass,P/time=atomic units. dt=1,h=.1,Decimal80/ROUND_HALF_EVEN,μ=mp/2=1836.152673426/2. mass는 이전 NIST nominal local 상수를 그대로 재사용, 불확실성 전파 미평가. R=zB−zA,zA=−R/2,zB=R/2,pA=−P,pB=P. COM 및 pA+pB는0.

`P_half=P_n+F_n/2; R_next=R_n+P_half/μ; F_next=(E_left−E_right)/.2; P_next=P_half+F_next/2`.
각 step은 새로운 stencil2점만; 추가3/5에서만 중앙E 계산. 추가호출 실제12=12, 초기F 재계산0.

## C0 TRUSTED CHECKPOINT / SNAPSHOT

C0 R=`1.4999839841775447537652184575595995968932634691351373193510208189297258568083880`, P=`-0.0294053504019942124614317435771226882934570312500000`, F=`-0.029403205585671887689613868133164942264556884765625`, H=`-1.1726087883593682110101233478733519730209824245462905549200823757479840322779073`. 이전 accepted 최종 상태 그대로이며 이전 초기 H0와 혼합하지 않았다.
source result SHA256 `02ef9504234a86d104e02ab02dcfd39df1167d617335a2cf9590c49a559e9c99`. [C0](C0.json), [protocol](protocol.json), [snapshot seal](snapshot_seal.json).

2584 historical required hash bindings와 immutable snapshot25파일을 시작/끝에 검사했다. 이전 CURRENT_STATE/REPO_MAP/verification lessons의 mutable dashboard snapshot은 당시 기록이며 현재의 불변제약에서 제외했음을 protocol에 명시했다. 원래 보고서/봉인/raw/계산기/test는 유지한다. protocol SHA256 `9021e91b7c37a77fe2d219014d6cc4ed5f9a9556e97440150e4f405faab5096d`, snapshot seal SHA256 `95242ea2d83ea9ceae47ff62433374884e57b5bbd173e49494bd859ec7a54e89`를 dispatch 인자로 고정했다.

snapshot은 Python source/rawbasis/mass/C0/protocol/wrapper다. controller와12workers는 `Python -I snapshot/launch.py`로 실행했고 모든 electronic_pilot module origin은 snapshot 아래였다. 원래 numerical kernel은 byte복사되어 변화없다. 외부 Python/PySCF/NumPy/SciPy/native 라이브러리는 기존 환경과 등록된 과거hash에 의존한다. 완전한 container나 read-only/tamper-proof memory image는 아니다. 시작/끝 hash는 양끝에 존재하는 변경을 찾지만 중간변경 후 복원이나 메모리결함을 모두 탐지한다고 주장하지 않는다.

## VALIDATION LEVELS / PUBLICATION

Quick는 매step 필수: 두 electronic guard(Smin/orth/H asym/residual/norm), NaN/Inf fail-closed, R[1.2,1.6], 요청/실제stencil geometry·rounding, Fraction force/Verlet 재검산, COM/pA+pB, JSON roundtrip/최초statehash. 매step 중앙 R의 binary64 인코딩도 기록하지만 energy 미평가로 표시한다. 이것은 domain의 interval 물리 인증이 아니다.

Quick에는 historical 전체hash/과거전체replay/pytest/중앙E/full seal 재작성 없음. force error bound는 없다. Decimal80 vs Fraction의1e−75는 scalar 산술검사만이며 ΔH tolerance가 아니다.

Medium=추가3번째의 중앙E+K+H+ΔH from C0. 마지막5에서도 같은 진단. 둘 다 MEASURED만, C3은 trusted checkpoint로 승격하지 않는다. 최종 full audit 전 모든5개state는 SPECULATIVE로 보존한다.

Full start/end는 C0 prior R1/P1/F1; source/protocol/basis/config/mass/integrator and historical required bindings; immutable snapshot25 files를 검사한다. 종료에는 새 raw·최초공개point·state hash와5step 독립 scalar-chain replay가 추가된다. Full start PASS(2624 bindings), end PASS(2737 bindings / scalar replay5). 이것은 작성자 구현과 다른 Fraction 코드로 재계산한 내부 검증이며 외부 독립기관 감사나 canonical REPLAY_VERIFIED 인증이 아니다.

종료 감사 후 별도 [authority decision](authority_decision.json)에서 C5를 Pilot 내 CONFIRMED로 승격했다. 원래 임시state파일은 수정하지 않았다. 실패 시 C0가 authoritative로 유지되고 이후 state는 DISCARDED 표시, raw는 삭제하지 않으며 자동 재실행0. Quick hardfailure는 즉시 STOP 후 full audit으로 승격한다. 실제 최대위험창5steps; rollback failure-path는 synthetic/fault 시험으로 검증했고 실제 campaign rollback은 발생하지 않았다.

## FIVE-STEP TRAJECTORY

| added step | requested R | P | F | ΔR | ΔP | stencil2 outer(s) | Quick(s) | pair peak RSS(MiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.49993594138259 | -0.05880212144177 | -0.02939033649388 | -4.80427950e-5 | -2.93967710e-2 | 50.960547 | 0.018811 | 3874.781 |
| 2 | 1.49985588563260 | -0.08818173337020 | -0.02936888736298 | -8.00557500e-5 | -2.93796119e-2 | 52.688250 | 0.017438 | 3874.738 |
| 3 | 1.49974384029068 | -0.11753560566749 | -0.02933885723160 | -1.12045342e-4 | -2.93538723e-2 | 48.637673 | 0.016100 | 3874.785 |
| 4 | 1.49959983806669 | -0.14685515666488 | -0.02930024476317 | -1.44002224e-4 | -2.93195510e-2 | 56.817931 | 0.017612 | 3874.746 |
| 5 | 1.49942392101863 | -0.17613180317485 | -0.02925304825678 | -1.75917048e-4 | -2.92766465e-2 | 51.446127 | 0.017710 | 3874.719 |

각step F/P 및 R/P 변화는 위 실측값이다. 매step COM0/p합0, NaN/Inf없음, domain내, Quick PASS. 개별핵좌표/운동량·P_half·center encoding·stencil rounding/hex·guard 원문은 [results](results.json)와 Git밖 state_1…5.json에 있다. 실제전자계산에서의좌표와 단순encoding만한중앙좌표는 구분한다.

| added step point | actual stored R | EBO(Eh) | guard | outer(s) | GNUwall(s) | peak RSS(MiB) |
|---|---:|---:|---|---:|---:|---:|
| 1 left | 1.3999359413825929 | -1.1742226382711816 | ACCEPTED | 26.941057 | 26.89 | 3873.855 |
| 1 right | 1.5999359413825929 | -1.1683445709724061 | ACCEPTED | 24.019489 | 26.15 | 3874.781 |
| 2 left | 1.3998558856325973 | -1.1742225965803192 | ACCEPTED | 26.423103 | 26.37 | 3874.484 |
| 2 right | 1.5998558856325973 | -1.1683488191077225 | ACCEPTED | 26.265148 | 28.75 | 3874.738 |
| 3 left | 1.3997438402906817 | -1.1742225342285204 | ACCEPTED | 23.967783 | 23.95 | 3874.785 |
| 3 right | 1.5997438402906816 | -1.1683547627822004 | ACCEPTED | 24.669890 | 26.41 | 3874.672 |
| 3 center | 1.4997438402906818 | -1.1726166835997238 | ACCEPTED | 28.329849 | 30.65 | 3874.426 |
| 4 left | 1.3995998380666874 | -1.1742224472355014 | ACCEPTED | 27.524714 | 29.81 | 3874.746 |
| 4 right | 1.5995998380666874 | -1.1683623982828670 | ACCEPTED | 29.293217 | 31.57 | 3874.387 |
| 5 left | 1.3994239210186292 | -1.1742223304900623 | ACCEPTED | 26.075476 | 28.46 | 3874.719 |
| 5 right | 1.5994239210186294 | -1.1683717208387066 | ACCEPTED | 25.370651 | 25.31 | 3874.598 |
| 5 center | 1.4994239210186293 | -1.1726265506934357 | ACCEPTED | 26.627356 | 28.90 | 3874.547 |

## CHECKPOINT ENERGY — MEASURED ONLY

| added step | E_center(Eh) | K(Eh) | H_total(Eh) | ΔH from C0(Eh) | status |
|---:|---:|---:|---:|---:|---|
| 3 | -1.1726166835997238191424685282981954514980316162109375 | 7.52367643473129e-6 | -1.1726091599232890878572524997740527055739480343720904831660019367988636051332880 | -3.71563920876847e-7 | MEASURED |
| 5 | -1.1726265506934356874779723511892370879650115966796875 | 1.68953336716503e-5 | -1.1726096553597640371648964174148673796119389450638571772690896768488214019125513 | -8.67000395826155e-7 | MEASURED |

energy-drift PASS tolerance는 없다. h=.1 차분, 전자 basis/산술, Verlet, geometry rounding, mass uncertainty를 원인별로 분리하거나 상한을 제시하지 않았다. 측정 결과만 기록했다.

## COST BREAKDOWN / OLD COMPARISON

| component | actual wall(s) |
|---|---:|
| stencil10전자calls outer | 260.550528 |
| Velocity Verlet scalar | 0.000578704 |
| Raw dynamics(stencil+scalar) | 260.551107 |
| Quick Kit 5회(guard/geometry/Fraction/state roundtrip+hash) | 0.087671 |
| Medium(추가3step중앙call+diagnostic) | 28.455703 |
| Final checkpoint(추가5step중앙call+diagnostic) | 26.767259 |
| Full Audit start | 26.522745 |
| Full Audit end | 26.982749 |
| 기타 capture/controller | 1.353245 |
| Campaign total | 370.720480 |

Raw dynamics는 앞의 두 행을 합한 소계이며 total에 중복 합산하지 않았다. 같은 perf_counter의 outer clock으로 분해했다. 전자 worker 내부 wall, GNU time, outer는 구별한다. GNU wall 합333.22s와 outer 합315.507733s의 차이17.712267s는 원인 미조사이며 두 원문을 보존했다. 이 계측 차이를 숨기거나 다른 clock 값을 성분 합에 섞지 않았다. snapshot 준비0.278969s, 의존 환경 설치, preflight, 최종 pytest, report/seal 포장은 campaign total에 포함하지 않았다.

이번 평균은74.144096s/step이며 시작·종료 audit와 중앙 진단 두 번을 포함한다. Raw dynamics 평균52.110221s/step, Quick 평균0.017534s/step이다.
이전1step incremental140.271748s, 전자3calls87.506782s, validation52.684139s는 역사 실측이다. 이번 차이에는 중앙E의 매step 계산 생략과 audit 주기 변경이 모두 포함된다. 같은 step을 두 방식으로 재실행한 통제 비교는 아니다. host 부하, 측정 시기, WSL 시작·cache 차이와 위 clock 차이도 남는다.

workflow의 sampled aggregate peak는3.804653GiB, controller peak는19.680MiB, 표본은18032개다. 20ms마다 Linux controller+descendants의 RSS를 합했으며 shared pages 중복과 표본 사이 peak 누락 가능성이 있다. Windows/전체 host 메모리가 아니다. per-call GNU 최대 RSS는 위 표에 있다. 한 campaign 실측이며 장기 성능과 보편적인 비용 상한은 미평가다.

## AUDIT CADENCE MODEL / ROLLBACK RISK

| interval K | end full audit/K(s per step) | fresh start+end audits/K(s per step) | maximum discarded work |
|---:|---:|---:|---:|
| 1 | 26.982749 | 53.505494 | 1 steps |
| 5 | 5.396550 | 10.701099 | 5 steps |
| 10 | 2.698275 | 5.350549 | 10 steps |
| 50 | 0.539655 | 1.070110 | 50 steps |
| 100 | 0.269827 | 0.535055 | 100 steps |

지정한 full_audit_cost/K에는 이번 end audit 실측26.982749s를 사용했다. 다른 열은 campaign마다 시작·종료 audit를 모두 지불하는 경우다. 가상 산술이며10/50/100steps는 실행하지 않았다. K가 커지면 늦게 발견한 오류 때문에 버리는 step 수도 커진다. 최종K는 미선택이며 설계자가 결정한다. 이 주기에서 모든 오류가 탐지된다는 보장은 없다.

## ACTUAL BLOCKERS / TESTS / CONCEPT ALIGNMENT

실제 전자 계산12회는 모두 ACCEPTED, Quick hard failure0, full audit mismatch0이며5step 뒤 STOP했다. 이번 실행을 막는 비용/RSS 장애는 없었다. 전자 계산은 성분 합의 대부분을 차지했다. 다음 최적화나 연속 실행 가능 범위는 별도 설계자 결정이다.
실행 전 별도 reviewer는 실패step 비용 누락·실패launch 집계 누락, 공개point 최초hash 종료감사 누락, 매step center serialized R 미기록을 발견했다. RED3→GREEN41 및 관련171 PASS로 수정한 후에만 snapshot을 봉인했다. 최초 구현 시험의 zero 문자열 자릿수 기대값1 failed/24passed도 수치 zero 비교로 고쳤고 원문을 보존했다. center geometry corruption RED→GREEN도 기록했다. TDD missing-feature RED 실패는 의도된 사전 시험이며 물리계산 실패와 구별한다.

최종 관련176passed / failure,error,actual skip0 / 5.130s(JUnit)다. 로그 점검과 별도로 이 작업에서 실제 시험을 실행했다. capture 시험은 데이터 취득 후 추가했다. source/config/hash를 바꾼 사본, force/μ/COM/geometry/guard/유한값/serialization, nonzero process receipt와 부분 비용, ΔH 승격, 종료 audit 실패 시 C0 유지를 검사했다. 전자 물리 정확도의 외부 독립 감사는 하지 않았다.

[별도 agent review](REVIEW.md)도 완료했다. 프로젝트 checker 없이 별도 Fraction 식으로5step/진단2개를 확인했고, 남은 중대한 구현·보고 결함은 발견하지 않았다. 물리 인증·미래K안전·clock차이해결은 판정 범위에서 제외했다. 후처리 표시 인코딩·report helper import 실패는 [postprocessing notes](postprocessing_notes.json)에 보존했으며 수치 재실행0이다.

`LOCAL FULL 생략 / 관련 시험으로 대체 / 이유`: 새 독립 Pilot/tests/docs만 추가했고 기존 calculator/common/frozen source/fixture 변경0이다. 공식 통합 Gate나 FULL 기준선 갱신은 아니다.
자동 시험과 별도로 spec 전체 항목을 대조했다. 추가5steps, C0 force reuse, dt/h/μ, Decimal80, V5Z guard, stencil2, center3/5, Quick 매step, Full 시작·끝, snapshot module origins, rollback5, 비용 분해, 가상K, STOP을 확인했다. adaptive/공식optimizer/JC/B2/formation/장시간/merge/rebase/push0이다.

읽은 범위: 첨부 전체, Pilot AGENTS/RULES 전체, CURRENT_STATE/REPO_MAP/docs 안내·상태표의 관련 항목, 이전1step/force/electronic reuse 관련 source와 봉인이다. 전체 repo와 과거 runs 전체를 재귀 감사하지 않았다.

## FINAL CLASSIFICATION / DESIGNER DECISION

**H2_MULTISTEP_LAYERED_VALIDATION_PILOT_SUPPORTED / NOT CERTIFIED / NOT PRODUCTION APPROVED**.
설계자가 이 비용과 rollback 범위를 보고 다음K와 추가 실행 길이를 결정한다. 이번에는 자동 선택이나 연장을 하지 않았다.
