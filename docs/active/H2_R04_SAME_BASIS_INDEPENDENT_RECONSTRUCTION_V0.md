# H₂ R=0.4 Same-Basis Independent Reconstruction V0

2026-10-03. **실제 두 arm 재구성 완료 / accepted 2개 / 두 arm 에너지 동등성 미통과 /
SAME_BASIS_RECONSTRUCTION_UNRESOLVED / NOT CERTIFIED / STOP.**

두 arm의 내부 numerical·spatial guard 통과와 에너지 정확도는 다른 판정이다.
L–I 차이 1.12512568e-9 Eh는 기존 same-basis 기준 1e-9 Eh를 넘는다.
AO 적분 전체의 정확성 상한과 reference 측 검증된 오차 상한은 없다.
남은 reference 차이를 순수 finite-basis error로 부르지 않는다.
기존 QZ44 FAIL과 과거 MO ERI pair-interchange UNRESOLVED는 덮어쓰지 않는다.

## 보완 계약과 실행 순서

설계자 첨부 지시문의 범위와 여덟 보완 조건을
[protocol.json](../../electronic_pilot/reconstruction_v0/protocol.json)에 반영했다.
첨부의 “최소 한 accepted energy 필수”는 **목표**로 바뀌었으며 0/1/2개를 모두 허용한다.
CASE B/C/precision 민감도는 독립 항목이고 동시에 성립할 수 있다.
에너지 재현 성공으로 필수 spatial guard 실패를 승격하지 않는다.

[execution.json](../../electronic_pilot/reconstruction_v0/execution.json)은 계산 전 precision 일정,
canonical rule, guard, 종료 기준을 고정한다. 결과나 reference 접근을 보고 바꾸지 않았다.
첫 source/config/input seal은 1,263 bindings, 파일명 수정 후 최종 실행 seal은 1,269 bindings다.
과거 1,178 bindings와 초기 봉인 source 모두 전후 불변이다.

실행 순서: 계약/source/input 봉인 → 실제 baseline 공간 검사 → L fresh AO/자체 C →
대각화 전 guard → 허용된 최저 root 계산/고정밀 refinement → spatial guard →
I에 동일 순서 → 비교 → 별도 봉인한 공통 표현·AO spot·state 영향 진단 → STOP.
pre-guard가 실패한 binary64/64-bit 경로에는 energy를 계산하거나 추정해 채우지 않았다.

시작 Git은 `codex/h2-qz-cause-v0`, HEAD/원격 branch
`251a7f395ca1e13cf41fe4b434399fec3bb1af95`, origin/master
`6c53eec71e981cef35f850095da76b965457866c`, ahead/behind 0/0, tracked dirty 없음이다.
새 audit 파일만 untracked인 상태에서 각 source seal을 만들었다. Commit 가능, push 금지.

## 같은 공간과 입력

고정 핵 nonrelativistic Coulomb, Z=1 핵 두 개, 전자 두 개, full singlet,
같은 **contracted spherical cc-pVQZ**다. Cartesian Libint 내부 70개 표현은 최종 60개
spherical AO로 명시적 polynomial map을 적용한다. 새로운 물리 공간을 추가하지 않는다.

R label=.4 Bohr, 중심=(0,0,−.2),(0,0,+.2).
실제 저장 좌표는 binary64 dyadic `±0x1.999999999999ap-3`이며 정확한 간격은
0.40000000000000002220446049250313080847263336181640625다.
기존 BO offset은 binary64 `1/float(.4)=2.5`; dyadic 간격의 정확한 역수와 구별해 보존했다.
새로 decimal geometry를 해석하거나 BO offset을 바꾸지 않았다.

[input_manifest.json](h2_reconstruction_v0/evidence/post/input_manifest.json)은 원시 지수,
수축 계수, normalization, AO 순서/위상, 실제 radial·real-spherical polynomial,
각 binary64 값의 hex/정확한 정수비를 담는다. BSE version/source SHA와 원본 decimal 문자열은
기존 [basis_sources/cc-pVQZ.json](h2_adversarial_v0/basis_sources/cc-pVQZ.json)에 보존돼 있다.
PySCF segmented columns와 BSE general contraction의 **exact coefficient span** 대조를 사용했다.
이름이나 AO 개수만으로 동일성을 인정하지 않았다.

기존 baseline artifact SHA256은
`40fcefcb1c2f190f7690e1ac018287e26217b482908200f55a8eac9dce521997`.
저장 C는 실제 60×60 삼각행렬이며 60개 diagonal이 모두 nonzero인 exact dyadic rank 증거다.
저장 vector 1830개, 실제 independent SC matrix 1830×1830,
전체 upper-lex pair order를 확인했다. 예상 차원과 실제 retained rank 모두 60/1830이다.
새 C_L/C_I도 각자 S로 만든 60×60 full Cholesky inverse transpose이며 삭제·cutoff 0이다.

## Engine과 수치 경로

L: PySCF 2.12.1 / libcint header 6.1.3, 배포 shared-library hash와 linkage 보존.
raw s1 AO를 fresh 생성했다. libcint exp-cutoff environment=0은 engine 기본값 사용을 뜻한다.
이를 screening OFF로 주장하지 않는다.
I: Libint2 2.7.2 Ubuntu 2.7.2-1.1build1 native binary, raw ordered Cartesian S/T/V/ERI.
normalization embedding OFF, standard Cartesian, `set_precision(0)` screening OFF.
두 engine 모두 **binary64 double 53-bit significand**다.
`set_precision`은 산술 비트 수를 높이지 않는다.
I의 Cartesian→spherical mapping도 binary64이며 그 오차는 engine difference와 분리된 미해결 항이다.

자체 C는 mpmath 60/80 decimal digits로 계산한 뒤 한 번 binary64로 저장했다.
C 변화 최대는 L 2.56e-55, I 2.13e-53으로 사전 내부 기준 1e-45 안이다.
각 arm의 compact/direct는 **동일 canonical AO와 동일 저장 C**를 사용한다.
compact PySCF의 within-pair reuse와 raw AO 압축·복사 공유를 명시했다.

독립 native direct는 GCC `-O3 -fno-fast-math`, long double 실제 significand 64,
`__float128` 실제 significand 113으로 네 index를 순차 수축하고 모든 ordered 결과를 계산한다.
**MO representative reuse, H transpose copy, averaging은 하지 않았다.**
AO만 사전 lower-one-body/descending eightfold quartet 값을 재사용한다.
그 전 raw ordered AO permutation diagnostics와 데이터 hash를 보존했다.
AO reuse가 만든 residual 0은 정확성 검사로 세지 않는다.

## Guard, 최저 root와 실제 결과

Orthogonality는 absolute operator 2-norm, exact rational Frobenius upper bound로 판정한다.
H asymmetry와 integral permutation은 absolute entrywise max, eigen residual은
absolute Euclidean `||Hv−Ev||₂` Eh, norm error는 `|vᵀv−1|`이다. 상대 정규화로 숨기지 않는다.
Spatial은 두 전자 AO S-metric norm이며 spin ladder는 Euclidean norm이다.
threshold는 orth/H/state/norm 1e-10, eigen/same-basis energy 1e-9 Eh 그대로다.

| 항목 | L | I |
|---|---:|---:|
| retained AO / full singlet | 60 / 1830 | 60 / 1830 |
| Smin | 5.503865868e-7 | 5.503865861e-7 |
| condition(S) | 9.844457374e6 | 9.844457388e6 |
| binary64 orth measurement | 1.90977e-10 | 7.16718e-11 |
| exact orth upper bound | 7.15847e-14 | 4.43002e-14 |
| 64-bit-significand H asymmetry | 1.21145e-7, REFUSED | 5.75179e-8, REFUSED |
| 113-bit MO pair-interchange residual | 8.22849e-23 | 5.49919e-23 |
| 113-bit H asymmetry before rounding | 5.93220e-23 | 5.39021e-23 |
| full independent SC matrix max difference | 1.42109e-14 | 1.42109e-14 |
| refined eigen residual | 1.03712e-28 | 2.79792e-28 |
| refined vector norm error | 3.85186e-34 | 9.62965e-35 |
| inversion S-metric residual | 3.82670e-11 | 3.86111e-11 |
| Sigma generator residual | 7.42357e-13 | 2.96281e-11 |
| runtime seconds, final arm | 64.045 | 67.747 |
| Python process peak RSS MiB | 683.14 | 746.75 |
| overall mandatory-guard status | ACCEPTED | ACCEPTED |

Peak RSS는 실행 프로세스의 누적 high-water 값으로 I에는 L 이력이 포함된다.
각 native transformation의 개별 peak RSS/runtime도 해당 `transform.json`에 보존했다.
Reflection/rotation/exchange/S+/S−/Sz도 기존 기준 통과, 80/100자리 측정 수렴을 보존했다.
Spatial HP 측정은 empirical convergence이며 rigorous enclosure가 아니다.
기존 state의 inversion6.2085e-10 실패는 과거 기록으로 그대로 남는다.

Binary64 compact H asymmetry L/I=2.49258e-10/2.40281e-10,
binary64 direct=3.50704e-5/5.94410e-5로 모두 refused, energy null이다.
64-bit도 refused여서 64→113 **energy 수렴은 판정할 수 없다**.
113-bit full-H refinement는 새 eigenbasis/물리/target 없이 max4 corrections,
내부 residual·energy-change 1e-24 기준에 따라 첫 correction 후 수렴했다.

최저 root 근거는 힌트 없는 **전체1830 `_syevd` spectrum**과 별도 SciPy `evr` 첫 두 roots다.
ground 차이 L2.66e-15/I4.44e-15, 다음 singlet gap 약 .716893 Eh다.
113-bit refinement는 이 root에 붙인 residual correction이며 eigenbasis는 preconditioner다.
고정밀 full-spectrum 대각화나 formal lowest-root certificate로 확대하지 않는다.
SC도 같은 MO를 공유하므로 AO 정확성을 증명하지 않는다.

## 에너지 비교와 의미 있는 차이

| BO energy, Eh | 값 | old와 차이 `E_old−E_new` |
|---|---:|---:|
| QZ baseline | −0.11803113362157003 | 0 |
| QZ independent L | −0.11803113360375748 | −1.78125465e-11 |
| QZ independent I | −0.11803113247863181 | −1.14293822e-9 |

`E_L−E_I=−1.12512568e-9`.
**측정값 기준** L은 old와 band 안, I는 밖이고 L–I도 밖이다.
따라서 CASE B와 C의 측정 조건이 동시에 성립한다. 공유 오류를 배제하는 인증은 아니다.
전체 upstream energy error enclosure가 없으므로 uncertainty-qualified 판정은 UNRESOLVED다.
`summary.json`의 measured/uncertainty-qualified classifications를 구별한다.

Raw S/T/V/ERI max differences는 7.77e-16/6.22e-15/7.11e-14/2.84e-14이다.
그 첫 bit 차이를 곧 오류로 명명하지 않았다. Raw S_L−S_I를 보존했다.
100자리 `U=C_L⁻¹C_I`에서 `C_L U−C_I` max3.66e-99,
I 좌표의 metric difference Frobenius1.34174e-10을 별도로 기록했다.
U를 unitary라고 가정하지 않았다.
검증된 C_I 공통 orbital 함수로 바꾼 **선택 네 MO entries** 중
`(50,50|39,50)` L−I=.004099706284 Eh다. 정렬 전 MO 차이는 계산하지 않았다.
이는 selected maximum이며 full cross-arm MO tensor maximum은 미측정이다.

L의 실제 AO wavefunction을 고정한 state-specific 영향 진단:
ERI signed effect +1.12690794e-9 Eh,
h effect −8.90e-16, S one-body −1.96e-16, overlap denominator −1.16e-17이다.
총 fixed-state Rayleigh shift +1.12690685e-9는 실제 ground shift +1.12512568e-9와
1.78e-12 차이다. 이는 **state-specific empirical 진단**, 엄밀 ground error bound가 아니다.
따라서 고정밀 downstream에서 남은 차이는 AO ERI engine/mapping variation의 energy 영향과
연결된다. 어느 engine 전체가 옳은지는 닫지 못했다.

가장 큰 weighted AO term `(31,31|1,1)`의 L/I 차이는 2.55351e-15,
가중치 약39187.85, 선택 entry 기여 약1.00067e-10이다.
상위16 entries에서 네 distinct classes를 고른 뒤 새 source/input seal을 만들고
independent Hermite Gaussian을 60/80자리로 각각 계산했다. 수렴 약1e-60, 독립 permutations 일치.
이 네 classes에서는 I가 independent 값에 더 가깝다. 이 국소 결과로 I를 전역 truth로 선택하지 않았다.
arm의 AO/energy를 사후 수정하지 않았다.

## 세 precision 계층과 한계

1. **저장 S/C guard 재측정:** old exact operator upper5.92112e-11, 기존 기준 PASS.
   새 L binary64 refusal처럼 보이는 값도 exact upper7.15847e-14로 PASS.
   AO나 C를 바꾸는 실험과 구분한다.
2. **고정 binary64 AO에 대한 HP 연산:** 60/80자리 own C, 53/64/113-bit 변환,
   113-bit root refinement. Integral promotion은 원래 잃은 digits를 복원하지 않는다.
3. **AO 자체 재계산:** 봉인한 dyadic exponent/radial/polynomial로 overlap1·ERI2 classes 및
   disagreement의 weighted ERI4 classes를 새로 적분했다. 높은 정확도의 경험적 수렴을 확인했다.
   **Full S/T/V/ERI 고정밀 재계산과 full AO energy error bound는 미수행**이다.
   배포 libcint/Libint engines는 double이며, 현재 검증된 HP 구현은 좁은 Gaussian spot 기능이다.
   더 높은 engine 전체 산술 precision을 구현했다고 주장하지 않는다.

내부 guard PASS, 경험적 precision 수렴, 두 독립 engine 일치/불일치,
엄밀 bound를 구별했다. 정확한 것은 saved-dyadic orth guard bound와 구조 rank 증거이며,
전체 물리 energy 정확성 상한은 아직 없다.

## 부호를 보존한 오차 장부와 상태

| 항목, Eh | L | I |
|---|---:|---:|
| E_old−E_new | −1.78125465e-11 | −1.14293822e-9 |
| E_new−Pachucki | +0.00219920757507 | +0.00219920870019 |
| verified full numerical energy bound | 없음 | 없음 |
| verified independent reference bound | 없음 | 없음 |

Pachucki는 비교 대상이며 precision/algorithm 종료의 target이 아니었다.
기존0.001 Eh physical band는 두 점 모두 여전히 넘는다.
남은 차이의 순수 finite-basis 배분은 미확정, 수치·reference 오차의 상쇄도 배제하지 않는다.
기존 cardinal trend는 조건부 FINITE_BASIS_LIMIT_SUPPORTED로 보존하며 새 QZ 결과를 별도 열로 기록했다.

상태: accepted2; SAME_BASIS_ENERGY_EQUIVALENCE_SUPPORTED **false**;
NUMERICAL_FRONTEND_ENERGY_SHIFT_CONFIRMED와 INDEPENDENT_AO_PATH_DISAGREEMENT는
**측정값 band 초과라는 empirical finding**, 엄밀 uncertainty 판정은 미해결;
PRECISION_SENSITIVITY_SUPPORTED; SAME_BASIS_RECONSTRUCTION_UNRESOLVED;
REFERENCE_SIDE_UNRESOLVED; NOT CERTIFIED. 과거 QZ44 FAIL 유지.

정확한 blocker는 두 accepted arm이 1e-9 Eh 안에서 일치하지 않고,
full high-accuracy AO/Cartesian mapping 및 전체 energy uncertainty bound가 없다는 점이다.
다음 설계자 결정 후보는 **같은 입력·공간에서 state-weighted ERI precision을 전체 bound까지
확장할지**, 또는 Libint mapping 산술 오차를 별도 좁은 실험으로 분리할지다.
이번 결과를 본 뒤 threshold/대표 규칙/engine 값을 맞추지 않았다.
추가 basis/uncontracting/V6Z/CBS, dynamics/world/production은 미실행하며 **여기서 STOP**한다.

## 실패 보존과 검증 범위

원래 봉인 source와 두 I/O 실패를 보존했다.
첫 실행은 Windows `h.bin`/`H.bin` 충돌로 대각화 전 중단.
후속은 파일명 치환 범위 오류로 preliminary L solve 뒤 refinement 중단.
최종 파일명 수정은 수학 표현·입력·precision·guard·canonical rule을 바꾸지 않았다.
세 번째 계산 실행은 두 arm을 완료했다. 네 번째 numerical retry 없음.
Windows packager가 WSL symlink를 읽지 못한 기록도 보존하고 package_v1은 그 한계만 처리했다.

새 시험은 failed/missing spatial guard, accepted0/1/2, B/C 동시 판정, 불확실성 interval,
unaligned MO·다른 C 차등 비교 거부, signed budget, threshold 불변,
정확한 rank/orth 결함, quad decode 및 원래/수정 I/O source의 수학 동일성을 검사한다.
WSL은 작은 native direct/독립 fermion CI 대조 및 비대칭 주입이 평균 보정되지 않음을 검사한다.
실제 전체 matrix의 독립 SC 비교와 실제 roots/symmetry 측정은 test 수와 별도 증거다.

LOCAL FULL 생략 / 관련 시험으로 대체 / 새 독립 audit·시험·문서만 추가,
기존 physics/production/frozen source·fixture 불변. 공식3289+1xfail 기준선 갱신 없음.
최종 실행된 시험 숫자와 로그는 [test_results.json](h2_reconstruction_v0/evidence/test_results.json).
실제 Windows237 passed(10.73s), WSL242 passed(38.17s), failure/error/skip0이다.
AGENTS.md/RULES.md와 첨부 명령은 전체 확인했고, CURRENT_STATE.md/REPO_MAP.md는 H₂ 관련 범위로 읽었다.

## 증거 위치

[실행·비교 summary](h2_reconstruction_v0/evidence/summary.json),
[최종 execution seal](h2_reconstruction_v0/evidence/execution_seal.json),
[raw inventory](h2_reconstruction_v0/evidence/raw_inventory.json),
[독립 AO cause spots](h2_reconstruction_v0/evidence/cause_spots/cause_spots.json),
[state 영향](h2_reconstruction_v0/evidence/influence/influence.json),
[실패 journal](h2_reconstruction_v0/evidence/failure_journal.json).
큰 raw AO/MO/H는 Git 밖 `runs/h2_reconstruction_v0/`의 지정된 phases에 남아 있으며 hash/크기를 Git에 보존한다.
봉인 byte provenance는 numerical/physical certification이나 외부 감사 승인이 아니다.

## 감사 절차 출처

`scientific-critical-thinking` skill의 관측/추론·공유 오류·불확실성 분리 절차를 사용했다.
Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026).
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065).
DOI: [10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065).
2026-10-03에 최신 record(v2, 2026-09-02)를 확인했다. H₂ physical evidence로 사용한 문헌이 아니다.
