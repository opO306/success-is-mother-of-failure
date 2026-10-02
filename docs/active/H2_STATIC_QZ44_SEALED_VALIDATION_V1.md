# H₂ Static QZ44 Sealed Validation V1 — 2026-10-02

**H₂ STATIC QZ 44-POINT REFERENCE-COMPARISON GATE = NUMERICAL FAIL.**
봉인한 V0 최종 경로로 원래 44점을 전부 새로 실행했다. **43 accepted / 1 refused**이며,
accepted 4점이 기존 Pachucki 비교 기준 `0.001 hartree`를 초과했다.
실패 결과를 그대로 유지한다. 실행 뒤 tolerance, canonical rule, 적분 표현 또는 계산 경로를
바꾸지 않았고, 실패점 진단으로 curve의 energy나 accepted/refused 판정을 대체하지 않았다.

**NOT CERTIFIED / MO ERI pair-interchange accuracy UNRESOLVED / production foundation 미승인.**
작은 Hamiltonian 비대칭이나 eigen residual은 전체 적분·solver 정확성의 상한이 아니다.
force, nuclear dynamics, H + H → H₂ formation, 복잡한 원자계, world integration은 미구현이다.
이번 결과는 H₂ 생성 증거가 아니다. 정적 표본 최소점이 보여도 전체 44점 Gate 실패를 덮지 않는다.

## 봉인 대상과 실행 조건

시작 branch는 `codex/h2-ao-micro-v0`, HEAD와 로컬에서 확인한 해당 origin ref는 모두
`0e9e454246d700efd0303c59eb9120ef9bc78f2e`였다. 원격 fetch나 push는 하지 않았다.
그 commit의 `electronic_pilot/ao_micro_v0/reuse.py` 최종 `AO_and_MO_integral_reuse`를
직접 호출했다. 새 `electronic_pilot/qz44_sealed_v1/`는 봉인·44점 실행·비교·실패점 진단·
증거 포장용 독립 분석 코드다. 기존 numerical source와 config를 수정하지 않았다.
V0 사양의 과거 4-point scope 문구도 보존하고, 이번 설계자의 명시적 44-point 실행 지시를
새 protocol에 기록했다.

물리 문제는 fixed-nuclei nonrelativistic Coulomb Hamiltonian, H nuclei 2개·전자 2개,
cc-pVQZ full AO span, singlet full finite-basis CI다. AO 60개·singlet dimension 1830을 유지했다.
basis deletion, eigenvalue cutoff, 행렬 평균 또는 강제 대칭화는 사용하지 않았다.
원래 grid는 `R=0.4,0.5,…,4.0,5,6,8,10,12,16,20 bohr`의 44점이다.
기존 accepted energy를 재사용하거나 누락점만 채운 실행이 아니다.

canonical representative는 아래와 같이 실행 전에 고정했다.

- AO pair: `(max(i,j), min(i,j))`, packed index `i*(i+1)/2+j`.
- AO ERI quartet: 두 packed pair index를 내림차순으로 정렬한 eightfold 대표.
- AO S/h: lower shell/index 대표를 한 번 계산하여 같은 양의 counterpart에 복사.
- AO ERI: PySCF `aosym='s8'`의 unique representative를 사용.
- MO h: lower 대표 bilinear quantity를 한 번 계산하여 같은 counterpart에 복사.
- MO ERI: 기존 `ao2mo.incore.full(..., compact=True)`와 restore 경로로 within-pair 값을 재사용.
- **MO pair-interchange는 독립 계산 상태로 남겨 잔차를 측정한다. 평균 또는 강제 동일화 없음.**

Cholesky coordinates, full singlet matrix assembly, `eigh`와 guard 함수까지 V0 최종 source
그대로다. 원래 call order의 raw AO 진단도 실행했다. identity에 따른 대표값 재사용은
새 근사 추가나 실행 뒤 residual을 보고 값을 선택하는 규칙이 아니다.

| 봉인한 guard | 기존 값 |
|---|---:|
| Smin floor | `1e-10` |
| orthogonality operator 2-norm maximum | `1e-10` |
| singlet Hamiltonian max element asymmetry | `1e-10` |
| eigen residual 2-norm maximum | `1e-9` |
| eigenvector norm error maximum | `1e-10` |
| pointwise absolute reference error maximum | `0.001 hartree` |
| 이전 accepted/control energy difference maximum | 기존 V0 `1e-9 hartree` |

실행 전 기존 source/config/reference/compact evidence **152개**, 새 harness·사전 시험 **6개**,
PySCF/NumPy/SciPy 및 native runtime **34개**를 SHA-256으로 봉인했다.
kernel/config/checker/reference 7개는 byte 그대로 별도 snapshot에 보존했다.
각 point 전후와 전체 실행 후 봉인을 재검사했다. source drift는 없었다.

| 대상 | SHA-256 |
|---|---|
| execution seal | `2b05954ad85bfd449a36db4855d027860a7919e5b2e86d00d9ee33a281e66bb4` |
| fresh 44-point results | `9564be2e8e23c2dbbb39bd0a9f5eb854ce888a2337ce398c5927a003a5dc0baf` |
| 기존 Pachucki CSV | `9576b17e1dbea93b1010d15068fdf83a6a54aeb7923a88ffe9898f7be08f66a2` |

실행 환경은 기존 로컬 Ubuntu-24.04 WSL의 Python 3.12.3, PySCF 2.12.1,
NumPy 2.5.3, SciPy 1.18.1이다. OMP/OPENBLAS/MKL threads=1, PySCF threads=1을 유지했다.
GPU·Vast 작업·새 package 설치는 없었다. 모든 point는 별도 새 worker에서 순차 실행했다.

## 전체 결과와 독립 reference 판정

모든 point의 accepted/refused, BO energy, orthogonality residual, H asymmetry,
eigen residual, MO ERI pair-interchange residual, runtime, process peak RSS를
[points.csv](h2_qz44_sealed_v1/points.csv)에 기록했다.
[results.json](h2_qz44_sealed_v1/results.json)은 overlap spectrum·AO 진단·artifact hash까지 담는다.
R=0.5는 첫 guard에서 거부하여 BO energy와 eigen residual이 null이다. 추정값으로 채우지 않았다.

| R (bohr) | numerical 결과 | BO energy (hartree) | energy − reference (hartree) | 최초 실패 |
|---:|---|---:|---:|---|
| 0.4 | accepted | −0.11803113362157003 | +0.00219920755725297 | reference 기준 |
| 0.5 | refused | 미계산 | 비교 불가 | orthonormalization |
| 0.6 | accepted | −0.7680645543359941 | +0.0015708751499151 | reference 기준 |
| 0.7 | accepted | −0.9207565303731988 | +0.0012709311542648 | reference 기준 |
| 0.8 | accepted | −1.0189864733406209 | +0.0010701930198942 | reference 기준 |

나머지 **39점은 numerical accepted와 reference 기준을 모두 만족**했다.
43 accepted subset의 max absolute difference는 R=0.4의 `0.00219920755725297 hartree`,
RMS는 `0.0007889692405682467 hartree`다. RMS가 작아도 pointwise 최대 기준 실패는 그대로다.
미계산 1점을 제외한 subset도 max 기준을 실패하므로 full-curve PASS로 보고하지 않는다.

reference 비교기는 evaluator와 AO/CI 계산 모듈을 import하지 않는다.
실행에 사용되지 않은 기존 CSV에 새 결과를 대조하고, 변경 없는 기존
`electronic_pilot/check_reference.py`의 사전 P1/P2/P3 판정도 별도로 실행했다.
reference는 이전에 보존한 [Pachucki 2010 v2](https://arxiv.org/pdf/1007.0322v2)의
독립 explicitly correlated 계산 자료다. 이번에 외부 계산 자체를 재실행한 것은 아니다.
R=16/20의 표에는 명시적 uncertainty가 없다는 이전 caveat도 유지한다.
`0.001 hartree`는 사전 pilot 판정 기준이며 외부 reference의 측정 uncertainty가 아니다.

### 이전 control 및 accepted 영역

초기 QZ accepted 33점, 앞선 numerical-cause fresh QZ accepted 34점, V0 최종 4점,
명시적 R=1.4 control을 새 curve와 비교했다. **72 비교 기록에서 모순 0건**이다.
같은 R에 대한 여러 역사 경로의 비교가 포함되므로 72개 고유 geometry라는 뜻이 아니다.
최대 absolute difference는 초기 R=1.5와의 `8.477e-13 hartree`다.
V0의 R=0.7/1.0/1.3/1.4 네 energy는 이번 fresh run과 **binary64 bit 단위로 일치**했다.
원래 R=1.4 control `−1.1737957922495874`와 새 `−1.1737957922495927`의 실제 binary64
차이는 `−5.329070518200751e-15 hartree`다.
controls 일치가 전 영역 정확성 인증이나 short-R reference 실패 해소를 뜻하지 않는다.

### 기존 물리 진단의 개별 결과

표본 최소는 R=1.4, BO energy `−1.1737957922495927 hartree`, 새 이웃 bracket은
R=1.3/1.5다. equilibrium distance를 입력하거나 fitting한 결과가 아니다.
외부 minimum 위치와의 차이 `−0.0011 bohr`, depth difference `−0.000680139150624 hartree`는
기존 각 기준 0.1 bohr/0.001 hartree 안에 있다. **전체 Gate는 계속 FAIL**이다.

해리 진단에는 원래 보존된 isolated-QZ H energy `−0.49994556858298833 hartree`를
postprocessing에만 사용했다. 이번에 atomic solve를 새로 돌린 것은 아니다.
R=10/12/16/20의 `E(R)−2E_H`는 차례로
`−4.68542428374e-6`, `−1.29448034574e-6`, `−2.1578894584e-7`, `−5.631403414e-8 hartree`다.
absolute difference가 줄고 R=20에서 기존 `1e-6` 기준을 만족한다.
finite-range 진단이며 무한 거리 증명·formation·nuclear dynamics가 아니다.
기존 ghost-basis 자료도 과거 자료를 postprocessing에 실었으며 이번 새 계산으로 세지 않는다.

## 실패점만 분리한 진단

결과를 확인한 뒤 전체 경로를 재조정하지 않았다. 실패한 **R=0.4/0.5/0.6/0.7/0.8만**
따로 조사했다. diagnosis source와 선택점·입력 hash를 별도 봉인하고, 원래 curve 기록과
AO/C artifact를 읽었다. 변환을 재구성했을 때 MO pair-interchange 최대 잔차는 다섯 점 모두
원래 fresh 기록과 정확히 같았다. 이 진단은 accepted/refused를 뒤집는 새 curve가 아니다.

### R=0.5: 최초 실패 계층

Smin=`4.942509508629897e-7`, condition=`1.0927664624610187e7`이고,
binary64 guard의 `||CᵀSC−I||₂=1.5495072148621564e-10`으로 기존 `1e-10`을 넘었다.
따라서 original refusal은 **orthonormalization**이며 eigen solve는 하지 않았다.

저장된 동일한 binary64 C와 canonical S를 MPFR 80자리로 평가한 Frobenius residual은
`1.0634011993883382e-11`이었다. Frobenius norm은 operator 2-norm의 상한이다.
같은 C/S에서 고정밀로 평가한 상한이 원래 binary64 operator residual보다 훨씬 작으므로,
**guard residual 평가의 반올림·상쇄 오차가 refusal에 크게 기여했다는 수치 근거**다.
이 값은 엄밀한 interval certificate가 아니며, 기존 guard 판정을 고칠 권한도 아니다.
기존 MP Cholesky를 진단으로만 평가한 80자리 Frobenius residual `1.5067379032943294e-75`도
보존했다. 그 C를 fresh curve에 사용하거나 R=0.5 energy를 추가하지 않았다.

### MO ERI: 선택 entry의 변환 오차

다섯 실패점 각각에서 가장 큰 pair-interchange 잔차를 가진 entry 한 쌍만 선택하여,
같은 canonical binary64 AO와 저장된 C를 MPFR 60/80자리로 contraction했다.
packed-pair density의 모든 nonzero 항을 사용하고 정확한 zero만 건너뛴다. cutoff는 없다.
AO generator를 새로 만들거나 binary64 AO를 고정밀 integral로 바꾼 진단이 아니다.

| R | 원래 MO pair-interchange max | 선택 entry의 binary64 − 80자리 contraction | 80자리 pair difference 절댓값 |
|---:|---:|---:|---:|
| 0.4 | `2.981148007941484e-5` | `−7.49949855602228e-5` | `2.0241e-79` |
| 0.5 | `3.2818213498503335e-4` | `+7.95903419418638e-5` | `2.6566e-79` |
| 0.6 | `4.331406895902168e-6` | `+2.1983510088732943e-6` | `1.7222e-80` |
| 0.7 | `4.172855684707322e-7` | `−1.7841499851678244e-7` | `8.5655e-82` |
| 0.8 | `1.413271396855098e-7` | `−6.313396220029731e-8` | `5.2711e-82` |

60/80자리 선택 contraction은 binary64로 반올림했을 때 일치했다.
따라서 조사한 entry에서 **binary64 MO transformation의 연산 오차**가 확인됐다.
하지만 한 entry의 forward difference 또는 pair-interchange 잔차는 전체 Hamiltonian이나
BO energy 오차 상한이 아니다. 대칭인 잘못된 값도 가능하다.
R=0.4/0.6/0.7/0.8의 guard는 통과했으며 최초 실패 기준은 외부 reference 차이다.
그 차이를 finite-basis 오차 하나 또는 수치 오차 하나로 확정할 근거는 확보하지 못했다.
**MO ERI 전체 정확성·reference energy 편차의 완전한 원인 분류는 UNRESOLVED**다.
고정밀 linear algebra는 libcint의 원래 binary64 AO precision을 높이지 않는다.

## 비용과 잔차

| 측정 | 실제 값 |
|---|---:|
| fresh 44-point campaign elapsed | 329.835063288 s |
| point worker 함수 내 wall 합계 (imports·AO 진단·artifact 작업 포함) | 262.021839516 s |
| 기존 transform/assembly/solve 구간 합계 (44점) | 54.306433646 s |
| 같은 구간 accepted 43점 합계 | 53.672415163 s |
| curve 최대 process peak RSS | 501.01171875 MiB |
| 실패 5점 diagnostic elapsed | 10.893474304 s |
| diagnostic 최대 process peak RSS | 405.1640625 MiB |
| accepted 최대 orthogonality operator residual | `6.914554652894015e-11` |
| 44점 최대 Hamiltonian element asymmetry | `1.7763568394002505e-15` |
| accepted 최대 eigen residual | `2.3698840968310653e-14` |
| 44점 최대 MO ERI pair-interchange residual (R=0.5) | `3.2818213498503335e-4` |

전체 campaign 시간은 worker startup, source/runtime hash 재검사, 저장 작업을 포함한다.
peak memory는 WSL worker process의 `ru_maxrss`이며 system 전체 RAM 사용량이 아니다.
앞선 V0 비용 추정 약 108초와 이번 전체 elapsed는 같지 않았다.
실제 load를 통제한 timing experiment가 아니므로 차이의 단일 원인을 확정하지 않는다.

## 시험·보존·구상 일치성

이번 실행에서 새로 확인한 결과다. 과거 로그만 읽은 수치를 새 시험으로 세지 않는다.

- Windows 관련 시험: **85 passed, 2.99 s**, failed/error/skip 0.
  새 sealed-run 18개, 기존 AO micro/numerical-cause/static-pilot/body-contract 시험을 포함한다.
- 로컬 WSL 관련 시험: **96 passed, 9.90 s**, failed/error/skip 0.
  새 18개와 MP diagnostic 1개, 기존 세 H₂ 계통의 unit/integration 시험을 포함한다.
- MP diagnostic 단독 사전 확인: **1 passed, 3.07 s**. 96개와 중복이므로 더하지 않는다.
- 첫 Windows 사전 시험은 **17 passed / 1 failed, 1.21 s**였다.
  새 AST source-read 시험의 cp949/UTF-8 해독 오류를 보존했다. numerical 실행 전
  그 시험만 UTF-8 명시로 고쳐 18 passed를 확인한 다음 source/config를 봉인했다.
  kernel 변경·실행 중 변경·실제 curve 재시도는 없었다.

새 fault-injection 시험은 44점 누락·중복, 기존 reference 경계값, refusal, control 모순,
dimension/sector 삭제, nonfinite, Smin/orth/H/eigen/norm 결함, canonical provenance,
source hash drift를 거부하는지 확인한다. synthetic PASS panel은 물리 계산 결과가 아니다.
reference checker의 evaluator import 금지도 AST로 확인한다.
MP diagnostic unit은 작은 packed contraction을 별도 full four-index contraction과 대조한다.
선택 QZ entry 진단을 모든 MO entry의 인증으로 확대하지 않는다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 독립 분석 harness·시험·문서만 추가했다.
기존 실행 code/common module/동결 contract/fixture는 수정하지 않았고 관련 시험은 통과했다.
이번 numerical Gate 자체는 FAIL이며, 여러 미실행 변경을 합쳐 통과한 통합 Gate로 종료하지 않는다.
공식 LOCAL FULL 기준선 숫자는 갱신하지 않았다.

기존 raw manifests를 지정 경로로 확인했다: initial pilot 265개, numerical-cause 145개,
AO micro 118개, 합계 **528개 변경 0**. 기존 compact evidence·source 152개도 봉인 hash와 같다.
새 44개 NPZ를 각 결과의 SHA-256과 대조했다. 새 scoped raw manifest는 118개 파일을 기록한다.
Git-excluded raw는 `runs/h2_qz44_sealed_v1/`, commit 대상 compact evidence는
`docs/active/h2_qz44_sealed_v1/`다. 원래 실패·historical hash를 덮어쓰지 않았다.

구상 일치성 별도 확인: 같은 Hamiltonian/basis/full singlet 공간과 사전 representative rule을
유지하고, 모든 44점을 재계산했으며, 실패 후에는 5개 실패점만 진단했다.
기존 결과와의 수치 일치가 independent reference의 기준 초과를 숨기지 않는다.
기존 C1-B1, A/B/L 우선순위, production foundation 승인 상태를 변경하지 않는다.
별도 작업선의 untracked 파일은 staging/commit 대상에서 제외한다. **push 없음.**

## 최종 상태

| 상태 | 판정 |
|---|---|
| SEALED SAME-PHYSICS PATH | 기존 V0 source/config/rule 보존, source drift 없음 |
| SAME-FINITE-BASIS EQUIVALENCE | full-span 구조 및 기존 72 비교에서 supported; 전 영역 정확성 증명 아님 |
| QZ 44-POINT EXECUTION | COMPLETE: 44/44 fresh attempted |
| QZ ACCEPTED CURVE | INCOMPLETE: 43/44 accepted, R=0.5 refusal 유지 |
| REFERENCE-COMPARISON GATE | **NUMERICAL FAIL**: refusal 1개, reference 기준 초과 4개 |
| NUMERICAL CAUSE | R=0.5 guard 평가 roundoff 기여 supported; 선택 MO entry transformation error 확인 |
| PHYSICAL COMPARISON | local sampled minimum·depth·tail 개별 기준 만족, full reference 기준 실패 |
| UNRESOLVED | MO ERI 전체 정확성, 전체 energy 편차 원인과 오차 상한 |
| NOT CERTIFIED | 전체 solver/integral 정확성·formal certification·production 승인 없음 |

이번 승인 범위의 fresh 검증과 실패점 진단을 완료하고 실패 결과를 설계자에게 보고한다.
canonical rule/tolerance를 결과에 맞춰 바꾸거나 추가 static precision 연구·다음 물리 단계로
자동 확장하지 않는다.
