# H₂ High-Precision AO Micro-Pilot V0

2026-10-02, Atomic / Electronic Foundation 전용 numerical research.
시작 HEAD와 origin/master는 모두 `6c53eec71e981cef35f850095da76b965457866c`,
ahead/behind 0/0, branch master였다. Verified Superoptimizer 파일은 작업하지 않았다.
commit 허용 / push 금지. 기존 미추적 `docs/superpowers/`, `experiments/`,
`tests/test_c1b1_candidate_b.py` 및 작업 중 나타난 다른 트랙 미추적 파일은 보존했다.

**한계부터:** 이번 full calculation은 binary64다. 독립 고정밀 AO는 좁은 spot-check다.
MO ERI pair-interchange 잔차는 남아 있다. 작은 H/eigen residual은 forward energy
error bound, 정식 인증, 전체 QZ curve 완료, 실제 H+H→H₂ 형성을 뜻하지 않는다.
초기 one-electron triangle 구현 불일치와 기타 실패를 삭제하지 않았다.
최종 판정은 수정 후 새 `B_v1/C_v1` 실행만 사용한다.

| 상태 | 이번 증거 |
|---|---|
| IMPLEMENTED | 독립 Cartesian Hermite Gaussian AO spot evaluator, 결정론 canonical reuse, 네 점 diagnostic campaign |
| TESTED | Windows 67 / WSL 77 passed, 실제 skip 0. 범위 중복 시험 수를 더해 unique 수로 세지 않음 |
| NUMERICALLY COMPARED | 독립 60/80자리 AO 비교, 기존 R=1.4 control, 기존 accepted R=1.5를 통한 local bracket |
| A. NUMERICAL CAUSE SUPPORTED | AO permutation 차이가 selected coupling에 유의미하게 증폭됨을 지지 |
| B. SAME-PHYSICS NUMERICAL PATH SUPPORTED | full M=60/D=1830 유지, control 차이 5.33e-15, 기존 refusal 세 점 제거 |
| C. QZ LOCAL MINIMUM RESOLVED | 1.3/1.4/기존1.5의 0.1-bohr sampled **local** bracket |
| NOT CERTIFIED / UNRESOLVED | 전체 QZ 44-point, 모든 AO/MO entry의 정확성 상한, formal equivalence/certificate, production 채택 |

## 사전 규칙과 같은 물리 문제

[실행 전 protocol](h2_ao_micro_v0/protocol.json.txt)은 거리 0.7/1.0/1.3/1.4,
cc-pVQZ, 기존 guard와 control 비교 1e-9 hartree를 고정했다.
fixed nuclei, nonrelativistic Coulomb, proton/electron 각각 2, full spatial singlet,
EBO=Ee+1/R를 유지한다. basis 삭제, eigenvalue cutoff, 새 potential, tolerance 완화,
reference/equilibrium/bond 입력, H 평균 대칭화가 없다. 세계 통합과 핵 dynamics도 없다.

실수 AO에 대해 S/h transpose identity와 Coulomb ERI의 eightfold symmetry는
적분의 곱 순서 및 전자 좌표 교환에서 직접 나온다. 정확한 같은 quantity를
한 대표값으로 계산하고 재사용하는 것은 같은 finite-basis Hamiltonian의 수치
표현이다. 평균값을 만들어 다른 quantity로 바꾸는 작업이 아니다.
full Cholesky C=L^-T는 같은 60개 AO span을 유지한다. occupied orbital 선택 없이
전체 spatial singlet 1830차원을 기존 `singlet_matrix`로 구성한다.
이 분석은 같은 정확한 식의 좌표/표현 동등성이며, 모든 반올림 오차에 대한 형식 증명은 아니다.

대표 규칙은 결과 전에 고정했다. AO one-electron은 shell/index lower triangle,
ERI는 각 pair를 큰 index부터 정렬하고 triangular pair index를 내림차순으로 둔다.
PySCF/libcint s8 driver가 unique AO ERI를 packed 형태로 계산한다.
MO ERI는 compact=True의 fourfold 계산에서 동일한 within-pair 값을 재사용한다.
MO one-electron은 각 lower-triangle bilinear integral을 한 번 평가해 counterpart에
동일 값을 쓴다. **MO ERI pair interchange는 강제하지 않고 잔차를 측정한다.**
singlet H를 구성한 뒤 copy/average repair하는 단계는 없다.

PySCF의 compact transform 및 restore 표현은 [공식 incore 소스](https://pyscf.org/_modules/pyscf/ao2mo/incore.html),
[restore 소스](https://pyscf.org/_modules/pyscf/ao2mo/addons.html)를 참고했다.
packing이 basis 함수를 줄이는 것이 아니라 정확히 같은 적분의 중복 저장을 줄이는 구조다.

## Stage A — 독립 고정밀 AO spot-check

기존 Cholesky/common-AO incore의 worst singlet coupling을 먼저 재생성하고,
그 coupling에 가중된 AO antisymmetry 항 중 절댓값 최대 항의 전체 symmetry class를
고른다. energy/reference/pass를 이용한 대표 선택이 아니다.
추가로 raw S 최대 transpose discrepancy의 class를 조사했다.

`gaussian.py`는 PySCF/libcint integral이나 기존 AO 값을 import하지 않는다.
Cartesian Hermite Gaussian recurrence, Coulomb auxiliary recurrence와 Boys lower
incomplete-gamma 식으로 적분을 새로 계산한다. primitive exponents, radial contraction
coefficients, Cartesian-to-real-solid-harmonic polynomial coefficients는 기존 molecule의
**공유된 rounded AO 표현**에서 추출한다. 이 메타데이터는 libcint 적분값이 아니다.
60/80자리에서 이 계수들을 exact binary64 input으로 올린 뒤 독립 적분을 평가한다.
basis specification/normalization metadata까지 독립이라는 주장은 하지 않는다.

Hermite recurrence는 [Ghent quantum chemistry 연구그룹의 식](https://gqcg-res.github.io/knowdes/the-mcmurchie-davidson-integral-scheme.html),
Boys 식은 [MolSSI MIRP](https://molssi.github.io/MIRP/boys_function.html),
AO normalization convention은 [PySCF mole 소스](https://pyscf.org/_modules/pyscf/gto/mole.html)를 확인했다.
별도 시험에서 Boys 직접 quadrature, Cartesian polynomial overlap quadrature,
separated-center ssss closed formula, center derivative로 얻은 p-type Coulomb와 대조했다.
실제 QZ의 s/p/d/f spot도 libcint와 2e-14 이내이며 전체 tensor accuracy 검사는 아니다.

| R | selected ERI class, 0-based AO indices | libcint permutation spread | independent 80자리 대비 max abs error | 해당 class의 80자리 coupling 비대칭 기여 |
|---:|---|---:|---:|---:|
| 0.7 | (2,1,1,1) | 1.11022e-16 | 4.64616e-16 | +4.10979e-8 |
| 1.0 | (2,1,2,1) | 2.22045e-16 | 4.32567e-16 | −2.37732e-9 |
| 1.3 | (2,1,2,1) | 2.22045e-16 | 4.32567e-16 | −4.42838e-11 |
| 1.4 | (2,1,2,1) | 2.22045e-16 | 4.32567e-16 | −1.41126e-11 |

AO 1/2는 첫 원자 2s/3s이며, selected ERI는 같은 중심의 s functions다.
고정밀 permutation spread는 80자리 출력에서 모두 0이고 60→80 최대 변화는
3.48201e-61다. 선택 S classes (14,55)/(15,56)/(15,56)/(6,42)는 d/f 또는 p/d
cross-center이며, libcint max abs errors는 각각 3.482e-16/2.721e-16/3.023e-16/3.580e-16,
독립 transpose 차이는 최대 약 5e-82다.

class의 coupling 기여는 기존 binary64 C를 그대로 두고 80자리로 가중 수축했다.
개별 class는 다른 class와 상쇄될 수 있다. 예컨대 0.7에서 이 class 기여 4.11e-8은
이전 전체 AO 전파 성분 약 2.96e-8보다 크다. **전체 오차 상한이 아니다.**
libcint의 absolute error와 permutation spread가 동일하다는 주장도 하지 않는다.
Stage B gate(독립 symmetry/60→80 차이 <1e-45, libcint spread>0, class 기여≥1e-12)는
사전 diagnostic significance 기준이며 H guard 1e-10을 완화한 것이 아니다.
네 점 모두 gate를 만족했다.

## Stage B — AO reuse와 변환 표현을 분리

AO S/h/ERI는 최종 canonical 표현에서 모든 기록된 transpose/permutation 잔차가
bitwise 0이다. 이 0은 representation identity가 보존된다는 의미이며 integral accuracy
인증이 아니다. canonical lower S/h가 raw lower S/h와 네 점 모두 byte-identical인 것도 확인했다.
packed ERI driver의 arithmetic은 s1과 달라 대표 자체의 마지막 bit가 달라질 수 있다.
예를 들어 (2,1,2,1)은 s1 0.520615746021682, s8 0.5206157460216823이다.
reference나 PASS를 보고 이 값을 고른 것이 아니다.

| R | 기존 raw AO/비압축 경로 H asym | AO reuse만 적용 후 H asym | AO+MO integral reuse H asym | 최종 MO ERI pair-swap 잔차 |
|---:|---:|---:|---:|---:|
| 0.7 | 3.22241e-7 | 2.81097e-7, REFUSED | 8.88178e-16 | 4.17286e-7 |
| 1.0 | 9.07334e-9 | 9.19645e-9, REFUSED | 8.88178e-16 | 2.75816e-8 |
| 1.3 | 4.25338e-10 | 3.67628e-10, REFUSED | 4.44089e-16 | 4.12997e-10 |
| 1.4 | 9.46468e-11 | 8.52584e-11, pre-eigensolve guards pass | 4.44089e-16 | 8.07844e-11 |

Stage B에서는 energy를 계산하지 않았다. AO reuse만으로는 0.7/1.0/1.3 refusal이
남는다. within-pair 수량을 MO에서도 한 번 평가·재사용하는 사전 후보가 네 점의
H guard를 통과해 Stage C로 진행했다. AO보다 다음 변환 층까지 같은 수학적 identity를
보존하는 수치 표현이 필요하다는 결과다.

최종 transformed h와 ERI ij/kl swap 잔차는 모두 0이다. pair interchange 잔차는
표와 같이 여전히 남아 있다. 기존 guard는 H asymmetry이지 별도 모든 ERI-permutation
threshold가 아니므로 이 값을 숨기거나 새 pass criterion을 만들지 않았다.

## Stage C — 최종 B_v1/C_v1 네 점

기존 기준: Smin>1e-10, ||CᵀSC−I||₂≤1e-10, max|H−Hᵀ|≤1e-10,
eigen residual≤1e-9, vector norm error≤1e-10. full M=60/D=1830.
기존 SciPy evr direct eigensolve를 사용하며 iteration_count=null이다.

| R | raw AO S asym | raw AO h asym | raw AO ERI ij / kl / pair swap |
|---:|---:|---:|---|
| 0.7 | 4.99600e-16 | 3.77476e-15 | 1.64452e-15 / 1.85615e-15 / 2.20657e-15 |
| 1.0 | 3.60822e-16 | 6.43929e-15 | 4.81559e-15 / 8.35443e-15 / 9.77343e-15 |
| 1.3 | 5.13478e-16 | 9.32587e-15 | 1.60941e-14 / 1.52205e-14 / 2.30961e-14 |
| 1.4 | 6.66134e-16 | 8.17402e-15 | 1.63515e-14 / 2.94452e-14 / 2.75249e-14 |

| R | Smin | condition | orthogonality L2 | H asym | eigen residual L2 |
|---:|---:|---:|---:|---:|---:|
| 0.7 | 8.71864e-6 | 6.14406e5 | 1.92512e-11 | 8.88178e-16 | 1.64575e-14 |
| 1.0 | 6.14771e-5 | 8.56263e4 | 1.92800e-12 | 8.88178e-16 | 1.45438e-14 |
| 1.3 | 2.15413e-4 | 2.38461e4 | 5.26370e-13 | 4.44089e-16 | 1.04869e-14 |
| 1.4 | 3.22244e-4 | 1.57843e4 | 4.52312e-13 | 4.44089e-16 | 1.17502e-14 |

| R | EBO hartree | worker wall seconds | fresh-process peak RSS MiB | first refusal |
|---:|---:|---:|---:|---|
| 0.7 | −0.9207565303731988 | 2.409 | 500.078 | none, accepted |
| 1.0 | −1.1236771303170410 | 1.877 | 500.055 | none, accepted |
| 1.3 | −1.1716323320354258 | 1.950 | 500.266 | none, accepted |
| 1.4 | −1.1737957922495927 | 2.055 | 500.043 | none, accepted |

전체 overlap spectrum, Ee/ENN/vector norms/digests는 [C_v1 raw records](h2_ao_micro_v0/C_v1_results.json)
에 보존한다. EBO에 1/R는 한 번만 포함된다. control 차이는 새 값−기존 값 = **−5.32907e-15**
hartree이며 사전 same-problem 기준 1e-9 이내다. 새 CI에 고정밀 AO 값을 입력하지 않았다.
spot-check 뒤 같은 binary64 libcint / canonical representation을 사용한 결과다.

## Local minimum / 물리 비교 경계

E(1.3)−E(1.4)=**0.0021634602141669** hartree다.
기존 accepted 1.5는 −1.1722017793714454이며,
E(1.5)−E(1.4)=**0.0015940128781473** hartree다.
따라서 1.3 < 1.4 < 1.5의 sampled grid에서 R=1.4 local minimum이 bracket됐다.
1.5의 기존 source/result hash와 accepted 상태는 [summary](h2_ao_micro_v0/summary.json)에 기록한다.
이 값들을 새 44-point curve로 합치지 않았다.

이번 결과는 새 equilibrium distance 입력이나 fitting 없이 계산된 local energy ordering이다.
44점 전체 외부 reference/max-difference/minimum-depth/dissociation의 재판정은 하지 않았다.
기존 34/44 curve와 이전 부분 물리 비교를 그대로 보존한다. Global minimum, continuous
equilibrium, 실제 H₂ formation, production foundation은 이번 증거의 범위 밖이다.

## 시험·실패·원본 보존·비용

Windows 최종 **67 passed / 1.63초**, WSL 최종 **77 passed / 5.12초**다.
수정 전 시험 로그도 별도 보존한다. 최종 기록은 [WSL v4 log](h2_ao_micro_v0/tests_wsl_v4.log)를 본다.
failure/error/skip 0. 새 dependency-light 24개, 새 integration 4개, 관련 기존 시험을 포함한다.
새 checker는 evidence precision/permutation/significance, overlap/orth/H/eigen/norm/nonfinite,
control energy, dimension deletion, missing panel, nonminimum fault injection을 검사한다.
direct einsum/product-space singlet projection과 compact transformation/기존 assembly를
별도 구현으로 비교했다. source imports, 사전 thresholds, 실제 lower-triangle 일치도 검사했다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 experimental source/tests/docs만 추가했다.
기존 공용·production·frozen source/fixture/계약 불변이며 공식 통합 Gate 종료나 기준선 갱신이 아니다.
89개 기존 source/compact evidence hash와 초기 pilot raw265개/후속 raw145개를 모두 확인해
변경·누락 0. 기존 LOCAL FULL 숫자는 갱신하지 않는다.

실패는 다음과 같이 별도 보존한다.

- Windows 첫 관련 시험 1 failed/56 passed: `resource`가 import-time에 Linux를 요구했다.
  runtime metric 함수 안으로 import를 이동했다. 수치 적분 식·guard 변경 없음.
- post-analysis 첫 class contraction: list에 NumPy식 tuple index를 써 TypeError가 발생했다.
  list indexing 수정 및 별도 product-space projection 대조 시험을 추가했다.
- 첫 packaging: WSL absolute source path를 Windows에서 읽으려다 FileNotFoundError가 발생했다.
  path adapter와 세 플랫폼 표기 시험을 추가하고 partial package를 보존했다.
- 처음 B/C: `hermi=1` triangle이 선언한 lower representative와 불일치했다.
  **INVALID_MEASUREMENT_FOR_PREDECLARED_REPRESENTATIVE_RULE**로 표기했다.
  초기 energy가 numerical guards를 통과했어도 최종 판정에서 제외했다.
  raw records/source/처음 compact package를 유지하고 lower-shell 명시 평가 뒤 새 B_v1/C_v1을 실행했다.
  사전 protocol/tolerance/대표 선택 rule은 수정하지 않았다.

[원본 보존 확인](h2_ao_micro_v0/preservation.json), [raw manifest](h2_ao_micro_v0/raw_manifest.json)
및 각 source snapshot이 failure와 실행 소스를 결합한다. Raw는 `runs/h2_ao_micro_v0/`,
Git compact evidence는 `docs/active/h2_ao_micro_v0/`다.

완료된 최종 stage wall: selection9.377 + 독립 spot0.079 + B_v1 12.421 + C_v1 9.827
= **31.705초**다. 초기 무효 B/C 20.694초도 비용에서 숨기지 않으며, 둘을 포함한 numerical
stage 합계는 약 **52.399초**다. 환경 준비/구현/시험/해시 검사/실패한 postprocessor 시간은 별도다.
Stage C peak 약 500.27 MiB. 이 memory에는 raw AO 비교 및 artifact preparation도 포함한다.
WSL Ubuntu-24.04, Python3.12.3, PySCF2.12.1, NumPy2.5.3, SciPy1.18.1, mpmath1.3.0.
기존 local venv, 수치 thread 1, 거리마다 fresh worker다. 원격/Vast/GPU/새 설치 없음.

같은 binary64 canonical 경로를 44점으로 확대하면 9.827/4×44≈**108초**라는
단순 wall projection이지만, 실측 44점 비용/전체 통과 예측이 아니다.
짧은 거리 conditioning, 기존 guard refusal, platform/부하 차이를 새로 확인해야 한다.
full HP AO/CI의 비용을 이 0.079초 narrow spot으로 추정할 근거는 없다.

## 구상 대조와 다음 결정

작성자가 source/입력/실행 전 seal/실제 AO representative를 별도로 대조했다.
이는 독립 agent 승인이나 formal proof가 아니다. 비대칭 0을 accuracy error 0으로 오해하지 않고,
AO spot 독립성과 공유된 basis metadata를 구분한다. 교환 대칭을 유지하는 수치 표현으로
기존 guard refusal을 없앤 결과이며, 전자 법칙에 H₂ 목표를 입력한 것이 아니다.

최초 관측 오차층은 libcint binary64 AO permutation 평가다.
AO reuse 뒤에도 비압축 AO→MO transformation에서 오차가 다시 커지는 것을 확인했다.
compact within-pair reuse는 H refusal을 제거했지만 MO pair-interchange 잔차/전체 forward-error
통제는 미해결이다. canonical packing은 정확도를 고정밀로 올리는 수단과 구분한다.

**DESIGNER DECISION REQUIRED:** 다음 범위를 결정해야 한다.
같은 경로의 fresh 44-point numerical 조사, MO pair-interchange/forward-error의 추가 좁은
진단 중 무엇을 진행할지, 또는 중단할지 이번 결과 이후 선택한다.
44점 확대/force/dynamics/다른 basis/세계 통합/production 선택은 자동으로 진행하지 않았다.
