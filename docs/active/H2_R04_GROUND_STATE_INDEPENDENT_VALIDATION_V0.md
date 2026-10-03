# H₂ R=0.4 Ground-State Independent Validation V0

2026-10-03. **같은 저장 MO에서 R=0.4의 CI ground-state 계층은 독립 경로로 지지됐다.**
AO 정확성, AO→MO 변환, MO 전체 정확성, finite-basis physical accuracy는 여전히
**UNRESOLVED / NOT CERTIFIED**다. 기존 **H₂ STATIC QZ44 = NUMERICAL FAIL** 유지.
이번 결과는 외부 제3자 감사·formal certification·production 승인·H₂ formation 증거가 아니다.

우선순위는 **가장 중요한 불확실성 → 정보 가치 → 의존성 → 같은 중요도에서 비용**이다.
일부 원소의 추가 검사보다 실제 ground-state 전체의 eigenpair와 최저 energy를 먼저 확인했다.
성공 후 numerical 연구를 **STOP**했다. **DESIGNER DECISION REQUIRED**.

## 입력과 Git 기준

- 작업 branch: `codex/h2-qz-cause-v0`.
- 시작 HEAD와 origin branch: `fad6df112a6b9351c577831a3980f38332053858`, ahead/behind 0/0, dirty/untracked 0.
- origin/master: `6c53eec71e981cef35f850095da76b965457866c`, 요청 기준과 일치.
- 기존 H₂ managed worktree에서 수행했다. 주 checkout이나 다른 계통의 작업을 전환하지 않았다.
- 기존 raw audit의 `runs/h2_ci_layer_audit_v0/audit_v0/h.npy`, `g.npy`를 그대로 사용했다.
  **MO 재구축·새 AO 생성 0회**. Full spherical cc-pVQZ 60 AO/MO, 전자 2, singlet 1830 유지.
- [실행 봉인](h2_ground_state_audit_v0/evidence/execution_seal.json)은 이전 910 bindings를 검증하고
  이번 source·저장 입력·전 단계 기록을 포함한 972 bindings를 physical 실행 전에 고정했다.
  guards는 기존 `ao_micro_v0/protocol.json`, energy agreement는 기존 `numerical_cause/protocol.json`에서 로드했다.
- source/input/config/canonical rule/sector/reference 기준 변경 없음. 새 audit source는 별도 모듈이다.

이번 두 CI 경로는 같은 저장 MO 숫자를 사용한다. h array SHA-256은
`052e348a12072c6b598e3f9972ca7bca4b0a4d3aa6853c878d5ab3ed838e160a`,
g array SHA-256은
`27f16faaef7bffdaf35e8ba6a2e5767126eca9a14459692d7919e1ab1f4b5026`.
파일/header 해시는 [MO metadata](h2_ground_state_audit_v0/evidence/MO_input.json)에 별도 기록했다.
이전 MO pair-interchange residual `2.9811480079414837e-5`는 같은 g에서 미해결로 유지한다.
이번 단계에서 새 precision이나 pair symmetrization을 적용하지 않았다.

## 원본 벡터 부재와 허용된 sealed replay

기존 QZ44 R=0.4 NPZ의 실제 keys는 `s/h/eri_s8/c`다. 기존 sealed runner도 이 네 배열만
저장했다. Energy는 있었지만 **원래 실행에서 저장한 v_direct는 없었다**.
이를 먼저 공개했고, 설계자는 동일 저장 입력/source/evr/guard와 bitwise energy 재현을
전제로 누락된 검증 입력의 replay 추출을 명시적으로 허용했다.

[replay 기록](h2_ground_state_audit_v0/evidence/replay.json)의 결과:

| 항목 | 실측 |
|---|---:|
| archived electronic E | -2.61803113362157 hartree |
| sealed replay E | -2.61803113362157 hartree |
| 둘의 binary64 hex | `-0x1.4f1ba4e9683fep+1`, bitwise 동일 |
| unchanged direct matrix asymmetry | 1.7763568394002505e-15 |
| direct eigen residual L2 | 2.3698840968310653e-14 |
| direct norm error, abs(vᵀv−1) | 4.440892098500626e-16 |
| replay next singlet gap | 0.7168930839894299 hartree |
| archived next gap 대조 | **UNAVAILABLE**, 원래 QZ44 기록이 저장하지 않음 |

별도 baseline export adapter만 해시 동일한 기존 `solver.singlet_matrix`를 호출했다.
SciPy `eigh(matrix, subset_by_index=(0,1), driver='evr')`도 원래 호출 그대로다.
그 원본 source hash가 QZ44 frozen source와 같음을 봉인 때 확인했다.
기존 eigen L2≤1e-9, norm error≤1e-10, H asymmetry≤1e-10을 그대로 통과했다.

벡터는 **REPRODUCED_FROM_SEALED_REPLAY**로 별도 저장했다. 원래 저장 벡터라고 부르지 않는다.
[v_direct_reproduced.npy](h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy)의
파일 SHA-256은 `cfb1113166b72f050f3d2d8c24de6d9aa2b00a72f64f10d83c65470f2f8d35b6`,
array SHA-256은 `a3495c5f03cdefe3c82175490e463928386d134fd5c5d48875599b2808cc381a`.
dtype `<f8`, little-endian, 길이 1830. 저장/로드 비트 일치 확인.
부호 변경·재정규화·SC에 맞춘 최적화 0회다.

[basis mapping](h2_ground_state_audit_v0/evidence/basis_mapping.json)은 1830/1830 state의
orbital pair/occupation/S=0/Ms=0/closed-unit 또는 open-1/√2 normalization/ordered determinants를
명시한다. 기존 upper-triangle order와 독립 occupation catalog의 대응은 identity이고,
duplicate/missing/extra 0개다. Canonical vector 파일은 replay 파일과 byte 동일하다.

## 독립 operator와 Stage A

새 operator는 검증된 independent `ci_layer_audit_v0.fermion`의 생성·소멸 연산자 정의와
singlet determinant expansion을 사용한다. 각각의 operator term에 occupied-lower parity를
직접 적용한다. One-electron/Coulomb/exchange와 normalization을 분리해 더한다.
전 bra/ket determinant의 surviving raw h/g 참조를 평가하며 permutation equality를 가정하지 않는다.
이 batching은 모든 원소의 synthetic scalar fermion 대조와 비대칭 입력/결함 주입 시험을 통과했다.

독립 operator는 direct-pair builder/action, absorb_h1e, fourfold packing, PySCF FCI를
import/call하지 않는다. 두 ordered-electron 항의 1/2 가중치는 원래 Hamiltonian의 항이다.
MO나 H를 평균·복사해 수리하지 않았다. [수학·구현 경계](../../electronic_pilot/ground_state_audit_v0/DERIVATION.md).
Full raw-SC 1830×1830 행렬을 직접 생성해 전체 `H_SC v_direct_reproduced − E_direct v`를 계산했다.

[Stage A 원본 기록](h2_ground_state_audit_v0/evidence/stage_A.json):

| 항목 | 실측 |
|---|---:|
| residual L2 | **2.3684997045187707e-14**, 기존 1e-9 이내 |
| residual Linf | **9.992007221626409e-15** |
| 최대 residual index, 0-based | 2 |
| canonical pair / sector | (0,2), S=0, Ms=0, open 1/√2 |
| H_SC v, 최대 성분 | -0.7461649959642097 |
| E_direct v, 최대 성분 | -0.7461649959641997 |
| difference | -9.992007221626409e-15 |
| vector L2 | 1.0000000000000002 |
| Rayleigh quotient | -2.6180311336215683 hartree |
| SC matrix asymmetry | 2.220446049250313e-16, 기존 1e-10 이내 |
| 독립 전체 행렬 구성 | 21.873066915초 |

**GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED**.
Stage A 파일을 저장한 뒤에만 Stage B를 호출했다. Synthetic fault tests는 A 실패 시
어떤 독립 eigen call도 실행되지 않음을 확인한다. Physical A mismatch는 없었다.

## Stage B: 힌트 없는 최저상태 solve

독립 SC 행렬의 전체 spectrum을 NumPy `linalg.eigh(UPLO='L')`로 처음부터 풀었다.
해당 런타임 문서는 LAPACK `_syevd`/`_heevd`를 명시한다. 실수 binary64이므로 `_syevd` 경로다.
기존 SciPy `evr` subset 경로와 다르다. Solver의 유일한 입력은 독립 행렬이다.
기존 v/E는 initial answer·shift·target으로 전달되지 않았고, 이후 비교에만 사용했다.
LAPACK이 lower triangle을 읽는 규약을 공개하며, 원본 전체 비대칭과 **전체 행렬 residual**을
전후 확인했다. `(H+Hᵀ)/2`는 없다.

[Stage B 원본 기록](h2_ground_state_audit_v0/evidence/stage_B.json):

| 항목 | 실측 |
|---|---:|
| E_direct | -2.61803113362157 hartree |
| E_independent | **-2.6180311336215656 hartree** |
| absolute difference | **4.440892098500626e-15**, 기존 1e-9 이내 |
| independent eigen residual L2 | 2.2289114448212103e-14, 기존 1e-9 이내 |
| independent vector L2 / norm error | 1.0 / 0.0 |
| next singlet gap | 0.7168930839894379 hartree |
| 기존 1e-9 band 내 lowest cluster | 1개 |
| abs(v_directᵀ v_independent) | 1.0000000000000004, 반올림상 약 1 |
| normalized overlap | 1.0000000000000002, 반올림상 약 1 |
| 반환 spectrum 크기 | 1830 |
| independent diagonalization | 0.795440798초 |
| replay+independent action/solve 전체 wall | 26.929067189초 |
| 동일 전체 process peak RSS | 365,113,344 bytes = 348.19921875 MiB |

Ground state는 이 수치 spectrum에서 다른 singlet와 충분히 떨어져 있다. Exact nondegeneracy
증명은 아니며 부호까지 같은 벡터라는 주장도 하지 않는다. Overlap을 1로 강제 clipping하지
않고 실측 floating-point 값을 보존했다. Canonical input 파일은 solve 후에도 hash 동일하다.

**INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED**.
CI construction/action + ground-state eigensolve에서 기존 결과의 강한 수치 지지를 얻었다.
범위는 이 **한 R/한 저장 MO/full singlet 문제**다. 전체 solver 정확성 인증은 아니다.

## Stage A/B 뒤의 physical comparison

별도 postprocessor가 A/B 종료 기록을 확인하고 reference/source/protocol hash를 봉인한 후에만
Pachucki CSV를 읽었다. CI evaluator는 reference를 읽지 않는다.
[독립 비교 기록](h2_ground_state_audit_v0/evidence/physical_comparison.json):

| 항목 | hartree |
|---|---:|
| nuclear repulsion, 1/R | 2.5 |
| direct BO | -0.11803113362157003 |
| independent BO | -0.11803113362156559 |
| 기존 Pachucki R=0.4 reference | -0.120230341178823 |
| direct − reference | 0.00219920755725297 |
| independent − reference | 0.00219920755725741 |
| 변경 없는 physical 기준 | **0.001** |

두 결과 모두 기준 초과. **PHYSICAL_COMPARISON_FAIL_AT_R04 / cause UNRESOLVED**.
QZ44는 재실행하지 않았고 43 accepted/1 refused 및 기존 reference FAIL을 수정하지 않았다.
두 CI가 같은 MO를 공유하므로 이 차이를 cc-pVQZ 한계로 확정할 수 없다.

## Regression·검증·구상 일치성

이전 (50,50) input → (39,50) output 반례는 [원래 파일](h2_ci_layer_audit_v0/evidence/counterexample.json)
그대로 보존했다. Hash `5b83f96032a696a060be049ef80b81c420f9d25f90c719bb37c449bfa791c414` 유지.
Direct `-4.231303534059128`, independent scalar SC `-4.231303534059129`,
invalid determinant candidate `-4.231297967351358`를 덮어쓰지 않았다.
이번 batch SC 행렬의 같은 원소 `-4.231303534059128`은 scalar와 8.881784197001252e-16 차이다.
Invalid 후보를 고치지 않았다. [보존 기록](h2_ground_state_audit_v0/evidence/regression_preservation.json).

- 새 algebra/guard/evidence 시험 **24개**. 합성 preflight16 이후 추가 evidence8을 실행했다.
- 관련 H₂ 기존 시험까지 Windows **147 passed, 2.66초**, WSL **150 passed, 9.61초**.
  둘 다 failure/error/skip 0. WSL 수치는 로컬 WSL이며 REMOTE LINUX FULL이 아니다.
- **LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 isolated analysis·시험·문서만 추가했고
  기존 실행 코드·공용 로직·동결 계약·fixture 불변을 hash와 변경 목록으로 확인했다.
  공식 LOCAL FULL 기준선 갱신 없음. 이 연구 결과를 통합/production Gate로 묶지 않았다.
- 한 valid physical approach, 재시도 0. 새 물리 실행 실패 0. NumPy/SciPy config 표시의 optional
  pyyaml 경고 2개는 console 원문에 보존했고, 환경을 변경하지 않았다.
- 별도 [구상 일치성 검토](h2_ground_state_audit_v0/validation/design_alignment.json)는 자동 시험과
  구분한 author review다. 중요도 우선, replay provenance, 전체1830 mapping/action, A→B gate,
  hint 부재, 같은 MO 한계, 원본 실패 보존, 성공 후 STOP을 대조했다. 외부 독립 승인은 아니다.

필수 문서는 AGENTS/RULES를 읽고 CURRENT_STATE의 활성 H₂와 Gate 부분, REPO_MAP의 구조와
해당 연구 모듈 부분을 읽었다. 두 대형 문서의 전체 역사 섹션을 정독했다고 주장하지 않는다.
이번 지시문 전체, 기존 micro-audit 보고서·fermion 정의·derivation, 기존 replay builder/call,
guard/config와 관련 artifact를 확인했다. 수치/시험 값은 과거 로그 추정이 아니라 이번 fresh 실행이다.

## 종료 상태

| 층 | 최종 판정 |
|---|---|
| replay 검증 입력 | bitwise E 재현, hash 고정; reproduced vector, 원래 archived vector 아님 |
| CI construction/action | **GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED**, R=0.4 실제 전체 eigenpair |
| ground-state eigensolver | **INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED**, full independent spectrum |
| action/eigensolve mismatch | 이번 실행에서 검출되지 않음; 보편적 부재 증명 아님 |
| MO 전체 정확성·pair interchange | **UNRESOLVED / NOT CERTIFIED** |
| AO 정확성·AO→MO transformation | **UNRESOLVED / NOT CERTIFIED** |
| finite-basis physical accuracy / R=0.4 reference 원인 | **UNRESOLVED**, 기준 초과 유지 |
| QZ44 / formal / production | **NUMERICAL FAIL / NOT CERTIFIED / NOT APPROVED** |

R=0.6/0.7/0.8, QZ44 rerun, basis expansion, HP AO campaign, force/nuclear dynamics,
formation/world integration은 미실행. 결과와 증거만 commit 가능, **push 없음**.
이제 AO/MO와 finite basis 중 무엇을 어떤 증거로 분리할지는 **설계자의 다음 결정**이다.

Raw full matrix는 `runs/h2_ground_state_audit_v0/validation_v0/H_SC.npy`에 보존했고 Git 밖이다.
벡터·전체 eigenvalues·residual·mapping·실행 seal·runtime metadata는 compact evidence에 commit한다.
[raw manifest](h2_ground_state_audit_v0/evidence/raw_manifest.json)는 raw matrix 포함 파일별 hash와 크기를 명시한다.
