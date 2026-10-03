# H₂ R=0.4 Front-End / Reference Cause Separation V0

2026-10-03. **REFERENCE_SIDE_UNRESOLVED / discrepancy cause UNRESOLVED / NOT CERTIFIED.**
이번 단계는 원문 reference 전사와 물리량 정의를 다시 확인했다. 전사 오류나 `+1/R`
누락은 관측되지 않았다. 독립 저자의 두 번째 BO 계산은 수치적으로 가깝지만,
R=0.4의 불확실도가 보고되지 않아 요청한 교차검증 기준을 완료하지 못했다.
이것은 reference 오류 발견이 아니다. `0.002199...` 차이의 원인을 reference,
basis, AO, 변환 중 하나로 결정하지 않는다. 기존 QZ44 NUMERICAL FAIL을 유지한다.

## GIT STATE · 읽은 범위

기존 관리 worktree `h2-qz-cause-v0/성공은 실패의 어머니`를 재사용했다.
출발 branch `codex/h2-qz-cause-v0`, HEAD 및 origin branch
`c05aa9de9044ee37fecd67bd85a175ae1f2f8a91`, origin/master
`6c53eec71e981cef35f850095da76b965457866c`, ahead/behind 0/0, tracked/untracked clean.
다른 main checkout으로 옮기거나 그 checkout의 파일을 수정하지 않았다. Push 없음.
완료 commit/Git 상태는 최종 응답의 실제 Git 확인으로 보고한다.

사용자 첨부 지시문 전체, AGENTS/RULES, CURRENT_STATE의 활성 H₂ 부분,
REPO_MAP의 관련 계통, 문서 안내/상태표의 관련 항목을 읽었다.
CURRENT_STATE/REPO_MAP 전체 역사나 runs 전체를 읽었다는 주장은 하지 않는다.
원문 PDF는 전체 텍스트를 추출하고 다음 관련 페이지를 이미지로 직접 확인했다:
Pachucki 3/12, Sims–Hagstrom published 1/4/5, author preprint 9/10.
원문 acquisition과 이미지 확인은 audit seal보다 앞서 끝났다. 새 energy의 blind run이 아니다.

## REFERENCE PROVENANCE · Stage A

Primary source: [Pachucki, arXiv:1007.0322v2](https://arxiv.org/pdf/1007.0322v2),
Physical Review A 82, 032509 (2010), DOI 10.1103/PhysRevA.82.032509.
PDF 12쪽 / 인쇄 12쪽, **Table IV**, 왼쪽 r/au–E(r) 쌍의 R=0.40 행이다.
오른쪽 같은 높이의 R=3.30과 혼동하지 않았다.

| 항목 | 원문 직접 재전사 | 기존 CSV | Decimal 차이 |
|---|---|---|---|
| R / bohr | 0.40 | 0.4 | 0 |
| total BO / hartree | −0.120230341178823 | −0.120230341178823 | 0 |
| 불확실도 / hartree | (15) = 1.5×10⁻¹⁴ | 0.000000000000015 | 0 |

수치는 clamped-nuclei nonrelativistic ground-state BO potential의 complete-basis
extrapolation이다. 괄호는 마지막 자리의 추정 불확실도이며 rigorous enclosure가 아니다.
이미지 수동 전사와 별도 pdfplumber 텍스트 행 추출이 일치했다.
기존 `verify_reference_transcription.py`/comparison helper를 호출하지 않았다.
두 전사 방식은 **같은 원문을 읽는 두 방식**이며 두 독립 물리 계산은 아니다.
판정: **REFERENCE_TRANSCRIPTION_MATCH_SUPPORTED**.

PDF SHA256 `55bc19137751110a2162f1aaa2268ff8577d2282dad77e9e89f7872743d3dd6e`.
[표 행 이미지](h2_frontend_reference_v0/evidence/pachucki_R04_row.png),
[전사 판정](h2_frontend_reference_v0/evidence/stage_A.json).

## PHYSICAL COMPARISON CONTRACT · Stage B

Pachucki PDF 3쪽 Eq.(1)/(2)는 직접 다음 연산자를 적는다.

`H = -½∇₁² -½∇₂² -1/r₁A -1/r₁B -1/r₂A -1/r₂B +1/r₁₂ +1/R`.

r≡r_AB이다. 현재 sealed QZ44 worker의 `ao_data('cc-pVQZ',r)`는
H 두 중심 `(0,0,-r/2)`/`(0,0,+r/2)`, Bohr, charge=0, spin=0,
symmetry=False, cart=False를 사용한다. h 호출은 kinetic+nuclear attraction,
ERI는 electron repulsion이다. `ao_micro_v0/reuse.py`는 singlet electronic
최저 energy에 `mol.energy_nuc()`를 더한다. 저장 R=0.4의 nuclear repulsion은 2.5다.
기존 문서의 같은 문제 선언만 읽고 판정한 것이 아니라 이 호출/조립식/저장값을 대조했다.
이는 의도된 operator/quantity 정의 확인이며 integral 값의 정확성 확인은 아니다.

| 계약 항목 | 우리 쪽 | Pachucki 원문 쪽 | 판정 |
|---|---|---|---|
| nuclei | 고정, Z=1 두 중심 | clamped protons | 정의 일치 |
| electronic problem | 2전자 비상대론 Coulomb BO | Eq.(2)의 2전자 Coulomb BO | 정의 일치 |
| nuclear repulsion | +1/R, R=.4에서 2.5 | Eq.(2)의 +1/r | 포함 일치 |
| 비교 energy | E_electronic+E_NN | total BO E(r) | 물리량 일치 |
| zero | Coulomb 연산자에 추가 offset 없음 | Eq.(2)에 offset 없음 | 일치 |
| 단위 / R | hartree / bohr, 실제 두 중심 간격 | atomic units, r_AB | 일치 |
| spin | 전체 S=0 singlet | ¹Σg⁺ ground state, S=0 | spin 일치 |
| 공간 대칭 선택 | finite AO span의 모든 singlet; g/Σ 강제 투영 없음 | ¹Σg⁺ ground-state expansion | 선택 공간 다름, 아래 제한 |
| finite mass / relativity / QED | 추가 없음 | BO 밖의 보정은 별도 계산 | 비교에 포함 안 됨 |

판정: **PHYSICAL_QUANTITY_MATCH_SUPPORTED**, 전체 front-end 정상 판정이 아니다.
Reference의 ¹Σg⁺와 우리의 전체 singlet finite trial space는 같은 공간이 아니다.
해당 symmetry가 포함되는 target 정의와 실제 저장된 최저 상태의 irrep 확인은 별개다.
이번에는 그 상태의 spatial irrep를 독립 측정하지 않았다. **NOT_INDEPENDENTLY_CHECKED**.
이 차이만으로 energy convention mismatch를 확정하지도, 공간 대칭 확인이 끝났다고 하지도 않는다.
[원문 식 이미지](h2_frontend_reference_v0/evidence/pachucki_Hamiltonian.png),
[계약 항목과 source anchors](../../electronic_pilot/frontend_reference_v0/primary_transcriptions.json),
[판정](h2_frontend_reference_v0/evidence/stage_B.json).

## REFERENCE CROSSCHECK · Stage C

두 번째 primary source:
[Sims–Hagstrom, JCP 124, 094101 (2006)](https://www.nist.gov/system/files/documents/2017/05/09/sims-h2.pdf),
DOI 10.1063/1.2173250. PDF 5쪽 / 인쇄 094101-5, **Table VI**, 첫 R=.4 행,
Energy(E)(hartree), N=7034, α₁=.5075 / α₂=.98286:

`E_Sims = -0.1202303411778644 hartree`

`E_Sims - E_Pachucki = +0.0000000000009586 hartree = +9.586×10⁻¹³ hartree`.

서로 다른 저자·구현·integral 평가 계통이다. Sims–Hagstrom은 numerical two-centre
integrals, 명시적 r₁₂를 포함한 variational Hylleraas expansion 및 quadruple arithmetic,
Pachucki는 analytic integral recurrences/James–Coolidge extrapolation을 쓴다.
명시적 상관 variational 이론 계열은 연관되어 있다. 계산법의 완전한 수학적 독립성이나
이번 agent가 원 계산을 새로 재현한 것은 아니다. Published source는 neutral H₂
¹Σg⁺의 비상대론 BO energy라고 정의하며 보정은 별도라고 명시한다.
Sims의 operator는 BO 정의/설명에 따른 비교이며 Pachucki Eq.(2) 같은 원식의 독립 재유도는 하지 않았다.

**불확실도 gate를 닫을 수 없는 근거:** PDF 4쪽 오른쪽 설명은
R=1.4의 error estimate를 ≤0.001 nanohartree(1×10⁻¹² hartree)로 제시한다.
다른 R 값에 대해서는 그 질문을 조사하지 않았다고 명시한다.
R=.4 Table VI에는 pointwise reported uncertainty가 없다.
마지막 열 `ΔE(α₂)×10¹²=285.9`는 α₂ expansion terms의 기여이며 total error가 아니다.
16자리 인쇄나 R=1.4의 추정치를 R=.4 uncertainty로 바꾸지 않았다.

[NIST author preprint](https://math.nist.gov/mcsd/savg/papers/h2.pdf)의
PDF 9/10쪽도 같은 제한/값을 확인한다. 같은 계산 계통이므로 세 번째 독립 source로 세지 않는다.
추가 검색에서도 이번 확보 범위 안에서는 R=.4 pointwise uncertainty가 있는
세 번째 독립 primary source를 확보하지 못했다. 그런 source가 존재하지 않는다는 주장은 아니다.

판정: **REFERENCE_SIDE_UNRESOLVED**. 의미 있는 reference 불일치가 확인된 것은 아니다.
수치적 근접성을 기록하지만 두 source의 **보고된 R=.4 불확실도 안에서 일치** 판정은 null이다.
0.001 물리 비교 기준을 reference 불확실도 gate의 대체 기준으로 사용하지 않았다.
[표 행](h2_frontend_reference_v0/evidence/sims_R04_row.png),
[오차 조사 범위](h2_frontend_reference_v0/evidence/sims_uncertainty_scope.png),
[판정](h2_frontend_reference_v0/evidence/stage_C.json).

Published PDF SHA256 `3ba26d2428f0876d76dff83d074572780331b3c1416557a29d22497c3b74834b`.
Preprint SHA256 `8477ebfd06b192f1dd0dc98cfa987abe1476afc0ed478acab5f5d9cec06cd3b2`.

## BASIS / AO INTEGRALS / AO→MO / SAME-BASIS ENERGY · Stages D–G

사용자 지시의 의존 순서에서 D는 reference 쪽 일관성 확보 뒤, G는 A–F가 충분히 닫힌 뒤다.
C의 요청된 pointwise uncertainty 기준을 닫지 못했으므로 downstream 정상 전제를 만들지 않았다.
이는 비용 때문에 생략한 것도, basis/AO가 맞다고 가정한 것도 아니다.

| Stage | 이번 실행 | 아직 필요한 근거 |
|---|---|---|
| D basis definition | NOT_EXECUTED | BSE와 exponents, contractions, primitive/contracted normalization, spherical/cartesian, ordering, 중심/ghost 대조 |
| E independent AO | NOT_EXECUTED | 독립 integral engine의 S/T/V/h/ERI, max/relative discrepancy, worst index, ill-conditioned entries; 값은 UNAVAILABLE |
| F independent AO→MO | NOT_EXECUTED | 같은 AO에서 기존 helper 없이 직접 contraction, h/ERI/pair symmetry와 worst discrepancy; 값은 UNAVAILABLE |
| G independent same-basis energy | NOT_EXECUTED | 앞 단계 closure 및 독립 front-end energy; 새 수치는 UNAVAILABLE |

S/T/V/ERI 차이를 0으로 기입하지 않는다. 기존 cart=False/60 orbital 정보는 입력 코드/이전 기록이며
이번 authoritative basis 감사 결과가 아니다. AO engine을 새로 호출하지 않았다.
기존 same-MO independent CI는 유지되지만 독립 AO+변환 energy로 확대할 수 없다.

## HIGH-PRECISION BO COMPARISON · 기존 결과의 새 전사 대조

다음은 이전 봉인 ground-state 증거를 다시 읽고 새 primary 전사와 Decimal로 비교한 것이다.
**이번 fresh energy 실행이 아니다.**

| 항목 | hartree |
|---|---:|
| 기존 direct electronic | −2.61803113362157 |
| 기존 independent raw-MO SC electronic | −2.6180311336215656 |
| 두 CI energy 차이 | 4.440892098500626×10⁻¹⁵ |
| 기존 direct total BO | −0.11803113362157003 |
| 기존 independent total BO | −0.11803113362156559 |
| direct BO − 재전사 Pachucki | +0.00219920755725297 |
| independent BO − 재전사 Pachucki | +0.00219920755725741 |
| direct BO − Sims–Hagstrom | +0.00219920755629437 |
| **기존 기준** | **0.001** |

두 reference 중 어느 값을 택해도 기록된 우리 BO 수치와의 차이는 기존 기준을 초과한다.
그러나 그것으로 reference 오차나 finite-basis limitation을 증명하지 않는다.
두 CI가 공유한 AO/MO와 residual pair-interchange 문제는 여전히 독립 front-end 근거가 없다.
기존 pair-interchange residual 약2.9811×10⁻⁵는 이전 증거이며 이번에 재측정하지 않았다.
그 residual의 energy discrepancy 기여를 확정하지 않는다.
[대조 증거](h2_frontend_reference_v0/evidence/prior_energy_comparison.json).

## FINAL CLASSIFICATION · 실제 확인과 남은 질문

| 요청 분류 | 이번 근거 |
|---|---|
| REFERENCE_TRANSCRIPTION_ERROR_CONFIRMED | NOT_OBSERVED: 원문 에너지/uncertainty와 CSV 동일 |
| COMPARISON_CONTRACT_MISMATCH_CONFIRMED | NOT_OBSERVED for operator/BO quantity; 공간 대칭 선택 차이는 공개, 저장 상태 irrep 미확인 |
| **REFERENCE_SIDE_UNRESOLVED** | **YES: 독립 source의 R=.4 pointwise uncertainty 미보고** |
| BASIS_DEFINITION_MISMATCH_CONFIRMED | NOT_TESTED |
| AO_INTEGRAL_MISMATCH_CONFIRMED | NOT_TESTED |
| AO_TO_MO_TRANSFORM_MISMATCH_CONFIRMED | NOT_TESTED |
| MO_REPRESENTATION_NUMERICAL_ERROR_SUPPORTED | energy causation NOT_ESTABLISHED; 기존 residual UNRESOLVED |
| FINITE_BASIS_LIMIT_SUPPORTED | **NO: 요구 전제 미완료** |
| **UNRESOLVED** | **YES: 0.002199... 원인은 미확정** |

가능성을 유명한 논문/라이브러리라는 이유로 닫지 않았다. 이번 상태는 시험 통과나
고정밀 인쇄값을 인증으로 바꾸지 않는다. 형식 인증, 모든 MO 정확성, production 승인 없음.
Pachucki 값은 **high-precision BO reference**이며 현실 자체가 아니다.

**다음 가장 중요한 질문 / DESIGNER DECISION REQUIRED:** R=.4에서 동일 BO 연산자/단위의
독립 high-accuracy 계산에 pointwise uncertainty를 어떻게 확보할 것인가?
예를 들어 독립 source의 R=.4 convergence/오차 근거 확보 또는 별도 승인된
R=.4 BO 계산과 그 uncertainty 조사다. 기존 R=1.4 오차를 가져오는 방법은 근거가 아니다.
이 질문을 닫기 전에는 basis 원인을 확정하지 않는다. 이후 full-singlet 최저 상태의
공간 irrep와 basis/AO/변환은 별도 미해결 질문으로 이어진다. 이번 실행 뒤 계산 확대 없음.

## 보존 · 실행 문제 · 시험 · 구상 일치성

[execution seal](h2_frontend_reference_v0/evidence/execution_seal.json)은 source/config,
수동 primary 전사, 원문 다운로드/hash/render, 기존 source와 evidence를 실행 전에 묶었다.
이전 단계의 972 byte bindings를 이어받고 총1,095 bindings를 전후 확인했다.
R=.5 MEASUREMENT_ERROR/adaptive prototype, R=.4 CI/ground-state, invalid packed
`(50,50)→(39,50)` 반례, QZ44 raw/failure 증거는 불변이다.
반례 파일 hash `5b83f96032a696a060be049ef80b81c420f9d25f90c719bb37c449bfa791c414`도 별도 시험했다.

실행 문제를 삭제하지 않았다. (1) seal 준비의 상대/절대 경로 혼용 오류는 audit 이전,
(2) package script file-mode import 경로 오류는 audit 완료 후였다.
각 코드 hash/오류 기록과 첫 실패 로그를 보존한다. 둘 다 계산법/criterion 수정이 아니다.
(3) 관련 suite 첫 Windows/WSL 실행은 동명 test_evidence.py 충돌로 collection error 각1이었다.
새 test 폴더의 __init__.py로 namespace만 분리하고 같은 suite를 재실행했다.
최초 실패를 PASS로 세지 않는다.

새 audit gate/fault-injection26 + compact evidence9 =35 tests.
관련 Windows **182 passed / failure0 / error0 / skip0, 2.51s**.
관련 WSL **185 passed / failure0 / error0 / skip0, 10.34s**.
WSL만 기존 PySCF-dependent diagnostic1와 integration2를 추가한다.
새로운 physical energy 결과 획득은0, audit AO/MO/CI call0이다.
**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 isolated audit·시험·문서만 추가,
기존 실행/physical/common/frozen source와 fixture의 불변을 변경 목록/hash로 확인했다.
공식 LOCAL FULL 기준선은 갱신하지 않는다. 자세한 명령/JUnit/첫 실패는 validation에 보존한다.

자동 검사와 별도로 구상 일치성을 검토했다: 어느 쪽도 정답으로 놓지 않았고,
독립 저자 source와 동일 source의 preprint를 구분했고, unknown uncertainty를 숫자로
만들지 않았으며, source 설명/finite-basis approximation/numerical error를 섞지 않았다.
이 검토는 구현 agent의 author review이며 fresh external audit나 formal proof가 아니다.

실행/재검사 명령은 새 모듈 `audit seal` → `audit run`; 각각 `--main`,
`--acquisition`, `--output`이 필요하다. 새 output 디렉터리에서만 실행한다.
`protocol.json`의 base Git precondition 때문에 후속 HEAD에서 원 작업을 재현하려면
원 base checkout와 raw 증거가 필요하며 그 제한을 조용히 완화하지 않는다.
Full primary PDFs/text/pages는 raw `runs/h2_frontend_reference_v0/acquisition_v0/`에 보존하고
Git에는 필요한 좁은 crop·전사·hash·판정·source snapshots를 저장한다.
Clone의 compact tests는 full PDF/raw 수치 replay를 대신하지 않는다.
