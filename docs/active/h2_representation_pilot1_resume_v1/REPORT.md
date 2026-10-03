# H₂ Representation Pilot 1 — 공식 H2SOLV / 독립 JC 이중 감사 재개 V1

2026-10-03. **H2SOLV_ARCHIVE_PROVENANCE_PASS / BUILD_ENVIRONMENT_DIFFERENCE /
STOP / NOT_CERTIFIED / NOT_PRODUCTION_APPROVED.**

공식 소스는 확보했지만 첫 `make`가 링크 단계에서 실패했다.
배포 예제 실행 0회, R=.4 B1 계산 0회, B2 구현·계산 0회다.
에너지·수렴·표현 효율·B1/B2 일치는 아직 판정할 수 없다.
이는 James–Coolidge 물리나 표현의 실패를 측정한 결과가 아니다.

공식 H2SOLV, 논문, 우리 독립 구현 모두 감사 대상이다.
공식 코드의 출력은 정답으로 승인하지 않는다. 구조는 A=Gaussian QZ/V5Z,
B1=공식 H2SOLV, B2=별도 수학 경로의 독립 James–Coolidge다.
여기의 A/B1/B2는 연구 비교 arm 이름이며 프로젝트의 세계 A / 관찰자 B와 다르다.
기존 [feasibility STOP](../h2_representation_pilot1/REPORT.md)은 당시 기록 그대로 보존했다.

## SOURCE PROVENANCE / GIT

[실제 Git 확인](evidence/git_preflight.json):
HEAD와 origin/codex/h2-representation-pilot1은
`264f5880ee1dedd5a97b008c29dd8d67057664b9`, branch는 `codex/h2-representation-pilot1`.
origin/master는 `6c53eec71e981cef35f850095da76b965457866c`.
`git ls-remote`로 실제 원격도 같은 값을 확인했다. 시작 ahead/behind=0/0,
dirty/untracked 없음. 주 작업 폴더의 다른 수정은 건드리지 않았다. Push 없음.

설계자 ZIP을 Downloads에서 직접 읽고 [전체 20개 파일 manifest](evidence/archive_manifest.json)를 만들었다.

| 대상 | 실제 SHA-256 |
|---|---|
| 제공 ZIP | `3a2756179b4f74abe450b5383fd9d8c656501cc5e39b39af74de42ffcd4d615d` |
| afba_v1_0.tar.gz | `a0f2967b1d110e88fd929f3effd1b8616a6e4fcb0477a988cb564952814a86db` |
| h2solv.f | `aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d` |
| README | `9967704407e40ec47406eaa415d8d90baa544a60a6959b46e85dbc67065992f8` |
| Makefile | `870b0368598405586f2320724dc950722599d7ebb665ffd8ca19a8ba4df617cf` |

지정값 5개 모두 일치한다. 5개 input, 5개 reference output,
solver/example, MPFUN 5개 파일, Makefile/test script/README가 실제로 존재한다.
Archive는 AFBA_v1_0 이름이고 solver 내부 주석은 VERSION 2.0이다.
배포 등록 번호와 내부 프로그램 번호를 임의로 같게 고치지 않았다.

원본과 빌드용 복사본은 Git 밖
`runs/h2_representation_pilot1/resume_v1_20261003/vendor_original/`, `vendor_build/`에 있다.
빌드 후 양쪽 20개씩, 총 40개 byte hash를 다시 검사해 불일치 0.
기존 Pilot의 문서·증거·시험 22개도 전후 불일치 0.
[보존 검사](evidence/preservation.json). 공식 source나 executable은 Git에 넣지 않았다.

## LICENSE / REDISTRIBUTION STATUS

실제 archive 20개 파일에는 별도 LICENSE 파일이 없고 README에 재배포 허락은 없다.
[공식 배포 Version 1](https://data.mendeley.com/datasets/835yrp4rww/1)은 CPC로 표시된다.
[현재 CPC 조건](https://www.elsevier.com/about/policies-and-standards/open-access-licenses/elsevier-user/cpc)은
연구 그룹의 academic/non-profit 사용과 저자의 서면 허락 없는 제3자 source/executable 재배포,
commercial/proprietary 사용을 구분한다. 공개 저장소 재배포·production 권한을 얻었다고 판단하지 않는다.
이번에는 지정된 연구 비교 범위에서 로컬 빌드만 시도했다. 이용 권한과 과학적 정확성은 별도 판정이다.

## BUILD ENVIRONMENT / VENDOR TEST REPRODUCTION

로컬 Ubuntu-24.04 WSL, x86_64, GCC/gfortran 13.3.0, GNU ld 2.42,
MPFR 4.2.1, GMP 6.3.0. 패키지·컴파일러·헤더·라이브러리 경로는
[환경 기록](evidence/build_environment.json)과 해당 raw logs에 있다.
부족한 gfortran/libmpfr-dev/libgmp-dev/time을 WSL에 설치했고,
apt update/install은 exit0이며 측정 wall 합 11.985초다.
README의 2016년 환경(gfortran/gcc4.8.4, MPFR3.1.3, GMP6.1.0)과 현재 환경은 다르다.

원본을 수정하지 않고 빌드 복사본에서 `make` 1회.
[실행 전 봉인한 예제 프로토콜](evidence/vendor_protocol.json),
[protocol hash](evidence/vendor_protocol.sha256), [실제 build exit2](evidence/build_result.json),
[실패 raw log](evidence/build.log)를 보존한다. 로그에는 stdout/stderr의 끼어든 줄이 있어
깔끔하게 재작성하지 않았다. Fortran/C 객체 생성 뒤 `h2solv` 링크가 실패했고
`example` 링크·수치 실행은 도달하지 않았다. `mpfr_root` deprecation warning도 해결하지 않았다.

실제 링크 명령은 `gfortran -fopenmp -lmpfr -o h2solv <objects>` 형태다.
`mpfr_set`, `mpfr_mul` 등 다수 함수가 undefined reference다.
라이브러리는 `/lib/x86_64-linux-gnu/libmpfr.so.6`에 있고
[nm 결과](evidence/library_symbols.log)에는 해당 심볼이 존재한다.
[GCC specs](evidence/compiler_link_specs.log)에 `--as-needed`가 있다.
따라서 객체 앞의 `-lmpfr`가 연결에서 빠지는 순서 문제는 **근거 있는 원인 후보**다.
순서 변경 재빌드로 검증하지 않았으므로 원인 확정/해결이라고 보고하지 않는다.

linked library path / dynamic-static linkage / MPFR 산술 환경의 실행 검증은
**UNAVAILABLE: 실행 파일 없음**이다. Makefile에는 OpenMP 옵션이 있지만
계획한 OMP_NUM_THREADS=1 수치 실행은 도달하지 않았다.
5개 vendor example은 전부 **NOT_EXECUTED_BUILD_STOP**.
`H2SOLV_VENDOR_TEST_REPRODUCED`나 `H2SOLV_VENDOR_TEST_MISMATCH` 판정은 없다.

## SOURCE AUDIT — 확인한 의미와 미검증 범위

[항목별 파일·줄 근거](evidence/source_audit.json)는 **STATIC_SOURCE_REVIEW_PARTIAL**이다.
모든 recurrence를 독립 증명하거나 소스 전체를 읽었다는 뜻이 아니다.

| 항목 | 실제 source에서 확인한 것 |
|---|---|
| Parser | R/EN/X/Y/U/W는 REAL*16로 읽어 문자열로 출력한 뒤 MPREAL로 변환. nominal `.4`를 정확한 분수로 읽는 경로가 아니다. |
| Hamiltonian | `HAM`에서 `H=T+V`; V에 `ZA*ZB/R` times overlap이 포함. 출력 BO에 +1/R 재가산 금지. |
| Basis | 비음수 다섯 지수의 총합≤OMEGA를 열거해 restrictions로 거른다. 같은 parameters/restrictions에서는 공간이 포함 관계지만 실제 retained rank/선형독립성은 미검증. |
| IAB / I12 | IAB=핵 교환 parity, input I12를 IE에 읽어 전자 교환 parity로 사용. +1/+1가 목표 singlet gerade sector. |
| Restrictions | JC gerade는 n2+n3 짝수; 전자 교환쌍 하나만 선택하는 지수 순서 제한. 실제 tuple list의 독립 대조는 미실행. |
| X/Y/U/W | X/Y는 핵 거리 차이, U/W는 합의 지수 계수. HAMLNORM에서 R을 곱한다. JC symmetric는 X=Y=0, U=W. |
| NMAX | 적분 Taylor 급수의 길이. ≤0이면 정수 변수에 80+10*R16을 넣는다. 정밀도 자리 수가 아니다. |
| Arithmetic | mpfunf의 default mpipl=80. 적분·행렬 구성 뒤 NDIGITS를 mantissa word 수로 변환하여 행렬 산술을 낮춘다. NDIGITS 그 자체가 정확한 decimal 자리 수와 같지는 않다. |
| Integral path | P_G → zero-parameter 분기 → REC_JC를 확인했다. Taylor/recurrence 식 전체의 수학적 정확성·수렴은 아직 미감사. |
| Matrix | HH/DN packed symmetric arrays. JC에서 원함수와 전자 교환함수의 matrix elements를 projector 평균. 실제 S/H 대조는 미실행. |
| EN/root | H−EN*S를 분해하는 shifted inverse iteration. 원하는 고유값 근처를 찾는 입력이며 ground root를 자동 보장하지 않는다. |
| Root guard | 최대40회; 내부 reps=1e−64 고정. iteration 한도 도달의 별도 실패 표시는 없고, ierror를 출력한 뒤 main 결과 출력이 계속된다. |
| Normalization | 최종 vᵀSv=1로 정규화. 소스의 적분 측도는 d³r1/(4π)d³r2/(4π), basis는 R 지수 scaling을 포함한다. |
| Wavefunction | wf_OMEGA.dat에 parameter/symmetry/count/tuple/coefficient. Parameter20자리·coefficient60자리 출력은 내부 수치 전체의 공개가 아니다. |

Inverse solver의 inertia count는 WA(1)에 반환된다고 문서화되어 있지만
CALCEN은 읽어 ground-root를 확인하지 않는다. 낮은 NDIGITS와 고정 `1e-64`
종료 기준의 관계, residual/metric conditioning/root qualification을 별도로 검사해야 한다.
LG2=false로 matrix export는 일반 input에서 켤 수 없다.
그 branch를 켜려면 별도 instrumented copy와 authoritative 원본 실행을 나눠야 하며 이번에는 하지 않았다.
Vendor test script는 diff 실패를 종합하는 fail-fast가 없어 마지막 script exit0만으로 재현 PASS를 줄 수 없다.

## B1 CONTRACT / SMALL–MEDIUM–LARGE / 세 수렴 장부

확정할 물리는 H₂, ZA=ZB=1, 두 전자, nominal R=.4 bohr,
singlet gerade ¹Σg⁺, nonrelativistic clamped nuclei, total BO energy다.
그 이후 입력 수치/ground root/guard 계약은 **NOT_SEALED_VENDOR_GATE_STOP**.
실제 R의 REAL*16→MPREAL 값을 봉인하고 B2와 같은 finite problem으로 맞출 의무도 남아 있다.

SMALL/MEDIUM/LARGE OMEGA, NMAX ladder, NDIGITS ladder, nonlinear 초기값·범위·optimizer·종료·비용,
reference를 보지 않는 EN 규칙 모두 미선택·미봉인·미실행이다.
Vendor gate를 넘지 못했으므로 예비 숫자를 계산 계약으로 채택하지 않았다.
향후 OMEGA / integral-series NMAX / arithmetic NDIGITS를 별도 장부로 유지한다.

## B2 INDEPENDENCE CONTRACT / IMPLEMENTATION METHOD / B1 vs B2

B2는 H2SOLV 번역이 아닌 논문 수학·물리 계약에서 시작할 별도 구현이다.
재개 후 source를 읽지 않은 별도 agent/session에 공개 수학과 interface만 전달한다.
이번 B1 source 검토자가 B2를 구현하지 않았고 B2 agent도 아직 시작하지 않았다.
H2SOLV recurrence/tuple list/intermediate integrals/S/H/eigenvector/energy를
B2 구현이나 종료 기준으로 전달하지 않는다. Source-reading isolation은 실제 시작 때 기록해야 한다.

B2 V0는 H₂ R=.4 symmetric JC, singlet gerade, low OMEGA, energy-only 범위다.
독립 analytic derivation / quadrature / 다른 published recurrence 중 방법은 미선택이다.
Basis → normalization → overlap → Hamiltonian → full low-order S/H → eigenvalue 순서와
첫 불일치 STOP 의무는 유지한다. Tolerance 미봉인, 독립 구현 및 finite-problem 비교 미실행.
공식 solver의 fault injection도 미실행이다. 이번 byte-evidence 결함 주입은 물리 fault injection이 아니다.

## R=.4 ENERGY / REFERENCE / GAUSSIAN vs EXPLICIT-R12 COST

| Arm | 에너지·정확도 | 이번 runtime/비용 판정 |
|---|---|---|
| A-QZ | 과거 gap0.0021992075572529746 Eh, .001 초과 | 새 실행 없음 |
| A-V5Z | 과거 gap0.0006333466089347428 Eh, 해당점 .001 이내 | 새 실행 없음; 정확도 기준의 주 비교군 |
| B1-small/medium/large | 미실행 | 미측정 |
| B2-low/medium | 미구현·미실행 | 미측정 |

과거 Gaussian bytes는 기존 봉인 자료 그대로이며 이번 새 수치 결과가 아니다.
Reference를 EN/optimizer/OMEGA/precision 종료에 사용한 계산은 없다.
B1 output 자체도 reference로 승인하지 않는다.
R04_TARGET_ACCURACY_MET, B1_B2_FINITE_PROBLEM_EQUIVALENCE_SUPPORTED,
COST_COMPARISON_AVAILABLE은 **판정 없음**이다.

Build의 개별 wall/CPU/peak RAM timer는 미수집이라 null로 기록했다.
함수 수나 tool-call 시간으로 solver 비용을 대체하지 않는다.
Integral/basis/optimization/assembly/eigensolve/validation/precision overhead 모두 미측정.
실패 build1회와 재시도0회를 보존한다. B1 runtime, B2 runtime, B2 개발 비용은 구분할 예정이다.
**COST_COMPARISON_NOT_COMPARABLE / GENERALIZATION_UNRESOLVED**.
H₂ 정적 특화 결과를 many-electron/force/reaction/dynamics/world foundation으로 일반화하지 않는다.

## FAILURES / WHAT IS SUPPORTED / WHAT IS UNRESOLVED

지원되는 결론은 지정된 배포 bytes 확보, 파일 존재·원본 보존,
현재 환경의 공식 default build 링크 실패, source의 위 부분 의미다.
배포 예제 재현, MPFR 실행 정확성, integrals/S/H/root, representation/arithmetic convergence,
독립 JC 구현, numerical tolerance 내 동등성, physical accuracy, 비용 우열은 미해결이다.
기존 QZ44 FAIL / same-basis reconstruction UNRESOLVED / production 미승인 유지.

## DESIGNER DECISION REQUIRED — 준비된 다음 실험, 아직 실행 안 함

첨부 지시 7·8·30절의 실패 STOP를 적용했다.
README가 설명한 static linkage를 command-line Make 변수로 선택하는 다음 실험을 준비했다.
현재 설치된 두 static library 파일은 실제로 존재한다.
새 빌드 폴더에서 원본을 다시 복사해 다음 명령만 사용한다.

```sh
make 'LD=gfortran -fopenmp' \
  'MPFR=/usr/lib/x86_64-linux-gnu/libmpfr.a /usr/lib/x86_64-linux-gnu/libgmp.a'
```

이는 solver/Makefile/MPFUN 원본 수정이 없는 README 지원 설정이다.
**아직 실행하지 않았다.** 재개 승인 뒤 새로운 attempt 기록과 입력/source hashes를 봉인하고,
5개 예제의 solver와 example 종료 코드·의미 대조를 각각 검사한다.
문자열 공백 차이는 허용하되 정수/구조는 일치, float 토큰은 봉인한 범위,
에너지는 abs1e−17 Eh 범위다. Error/warning/누락 출력은 fail-closed로 처리한다.
재현 PASS는 확보한 배포본을 그 환경에서 실행했다는 증거까지만 뜻한다.

## VERIFICATION / READ SCOPE

Windows 관련 시험 **50 passed / failure0 / error0 / skip0, 0.46초**.
새 시험8개 포함이며 초기 수집 오류와 인코딩 오류를 별도 보존했다.
Byte 증거의 오염·누락 결함 주입은 각각 거부됐다.
검증 결과와 새 source/evidence seal은 [verification](evidence/verification.json),
[final seal](evidence/final_seal.json)에 별도로 기록한다.
LOCAL FULL 생략 / 관련 시험으로 대체 / 새 독립 문서·증거·시험과 안내만 추가,
기존 numerical/production/common/frozen/fixture 불변. 공식 기준선은 갱신하지 않는다.
관련 시험 PASS를 vendor 또는 physics PASS로 승격하지 않는다.

첨부 지시/AGENTS/RULES, README/Makefile/test script/example/JC symmetric input/output은 전체 읽음.
CURRENT_STATE/REPO_MAP/docs 안내는 관련 초기 절과 H₂ 범위 읽음; 긴 과거 전체 재독 아님.
H2SOLV source는 위 partial scope, MPFUN은 default precision 및 word 정의 관련 절만 읽음.
다른 input/output은 inventory/hash 확인이며 이번 계산·전체 의미 검토 아님.
절차에는 scientific-critical-thinking의 증거/해석/주장 분리를 적용했다.
Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026),
[Scientific Agent Skills](https://arxiv.org/abs/2609.00065), 현재 v2 metadata 확인.
이 절차 문헌은 H₂ 물리 reference가 아니다.
