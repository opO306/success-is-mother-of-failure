# H2SOLV Pilot 1 — Vendor Build Resume V2

2026-10-03. **README_SUPPORTED_BUILD_PATH_WORKS /
VENDOR_BUILD_ENVIRONMENT_COMPATIBILITY_SUPPORTED /
ALL_FIVE_VENDOR_PRINTED_OUTPUTS_REPRODUCED / STOP.**

승인된 README 정적 연결 빌드 1회가 성공했고, 배포 예제 5개의 solver+example
합친 출력이 reference output과 **byte-for-byte 동일**했다.
다만 원본 프로그램은 내부 반복 횟수·반복 한도 도달 여부를 출력하지 않는다.
**NATIVE_ROOT_CONVERGENCE_UNAVAILABLE / VENDOR_GUARD_QUALIFICATION_UNRESOLVED**다.
출력 재현 성공을 독립 수렴 guard PASS나 lowest-root 인증으로 승격하지 않았다.
**NOT_CERTIFIED / NOT_PRODUCTION_APPROVED**. R=.4 계산0, B2 시작0.

## GIT / AUTHORIZED SCOPE

시작 HEAD `0b79ee32e153085d00514628d1c9d840c16a67cd`,
`codex/h2-representation-pilot1` worktree에서 계속 작업했다.
실제 `git ls-remote`는 master `0f7b744cf754450424a63c47f305e0327c5b37c1`,
Pilot `264f5880ee1dedd5a97b008c29dd8d67057664b9`.
[시작 상태](evidence/git_before.json). Fetch/merge/rebase/push 없음.
첨부 지시 9·10절의 범위: vendor build → 5 examples → 보고 후 STOP.
B1 R=.4 실행 계약과 B2 clean-room 구현은 이번 승인 범위가 아니다.

## ATTEMPT LEDGER / SOURCE PROVENANCE

| Attempt | 절차 | 실제 결과 |
|---|---|---|
| 1 | 원본 default Makefile, dynamic -lmpfr가 객체 앞 | 링크 FAIL exit2; 과거 실제 실패 유지 |
| 2 | 이번 새 build copy, README 정적 MPFR/GMP 연결 | h2solv/example 모두 build exit0 |

[Attempt1 봉인 보고서](../h2_representation_pilot1_resume_v1/REPORT.md)는 수정·덮어쓰기하지 않았다.
원본 ZIP / tar.gz / vendor tree, 새 build copy의 원래20파일은 실행 전후 동일하다.
[보존 검사](evidence/preservation.json), [실행 전 protocol](evidence/protocol.json),
[protocol SHA-256](evidence/protocol.sha256).
기존 문서·시험·실패 로그 **61개 bindings**를 전후 확인해 불일치0.

ZIP SHA-256 `3a2756179b4f74abe450b5383fd9d8c656501cc5e39b39af74de42ffcd4d615d`,
tar.gz `a0f2967b1d110e88fd929f3effd1b8616a6e4fcb0477a988cb564952814a86db`,
h2solv.f `aa109cbd47cf5dcd2db57ce3da67bdaf69e22dfd9023e1219328e21413703d2d` 유지.
README/Makefile/MPFUN/input/output도 원래 inventory hashes 유지.
원본 source·executable은 Git에 넣지 않았고 raw build tree는
`runs/h2_representation_pilot1/vendor_build_resume_v2_20261003/vendor_build/`에 있다.
Wavefunction 원본도 각 raw case 경로에 남겼으며 [raw inventory](evidence/raw_inventory.json)로 봉인한다.
이 기록의 B1 출력을 미래 B2의 구현 입력으로 전달해서는 안 된다.

## BUILD ENVIRONMENT / EXACT BUILD PATH

Ubuntu-24.04 WSL2 x86_64, GCC/gfortran13.3.0, GNU ld2.42,
MPFR4.2.1, GMP6.3.0. [환경·라이브러리 hash](evidence/environment_before.json).
LDFLAGS는 unset, gfortran/GCC specs에는 `--as-needed`가 존재한다.
다른 compiler/임의 flags/소스 patch를 시도하지 않았다.

```sh
make 'LD=gfortran -fopenmp' \
  'MPFR=/usr/lib/x86_64-linux-gnu/libmpfr.a /usr/lib/x86_64-linux-gnu/libgmp.a'
```

Makefile bytes는 그대로이고 command-line Make 변수만 README 지원 설정으로 선택했다.
실제 link command는 객체들 **뒤**에 두 static library path가 온다.
[실제 build stdout](evidence/build.stdout)에 두 명령 전체가 있다.
[ldd](evidence/h2solv.ldd.stdout) / [readelf](evidence/h2solv.readelf.stdout):
MPFR/GMP는 static; libgfortran/libm/libgomp/libgcc_s/libc는 dynamic.
실행은 OpenMP compile 옵션 유지, OMP_NUM_THREADS=1 / OMP_DYNAMIC=FALSE.

Build wall5.312966초, GNU time CPU user3.61/system0.48초,
peak RSS139588 KiB. `mpfr_root` deprecation warning은 남아 있다.
[build stderr](evidence/build.stderr). 해결됐다고 보고하지 않는다.
이번 결과는 README-supported path의 호환성을 확인했다는 의미다.
Static/dynamic 연결과 library 순서를 함께 바꿨으므로 `--as-needed` 단독 원인을
통제 실험으로 확정한 것이 아니며 default Makefile이 올바르다는 판정도 아니다.

## VENDOR EXAMPLE REPRODUCTION

각 case는 별도 폴더에서 원래 input을 사용했다.
solver와 `example <wf_7.dat`를 각각 실행하고 exit/runtime/RSS/stdout/stderr hashes를 기록했다.
Vendor script 마지막 exit0에 의존하지 않았다.
[모든 case 결과](evidence/result.json), [비교표](evidence/table.json).

| 예제 | basis | NMAX | 출력 BO energy Eh | solver wall s | peak RSS MiB |
|---|---:|---:|---:|---:|---:|
| H–He⁺ / h-h+ | 416 | 140 | −2.904311531728328003 | 29.361282 | 507.000 |
| JC symmetric | 228 | 80 | −1.057326153651244754 | 8.297019 | 194.500 |
| H₂ symmetric | 416 | 140 | −1.000835673013415305 | 49.609827 | 511.000 |
| JC asymmetric | 416 | 80 | −0.6907469540168939787 | 17.900653 | 198.500 |
| General basis | 792 | 140 | −0.6942666307257072980 | 131.800421 | 518.875 |

모든 case의 표시 정밀도는 integral80 / linear algebra60이다.
모두 solver exit0 및 example exit0, stderr 빈 파일이다.
출력 energy의 exact Decimal equality5/5, 모든 numeric token 차이0,
basis/symmetry/restrictions/precision/추가 delta(r12) 값도 일치했다.
허용오차 통과에 더해 실제 combined output의 SHA-256까지 reference와 동일5/5다.
각 [input/ref/actual hashes·세부 비교](evidence/cases/)는 case별 result.json 및 파일에 있다.

Solver wall 합236.969203초, example wall 합0.139983초.
각 example wall0.020445–0.042941초, peak RSS3.000–3.250 MiB.
표의 wall은 WSL 안에서 time.monotonic으로 subprocess 실행·완료까지 잰 값이며
GNU time의 coarse elapsed/CPU/RSS도 별도로 보존한다. 비용 합계는 순차 process 범위다.
이 결과를 R=.4 비용·표현 우열·Gaussian과의 공정한 비용 비교로 사용하지 않는다.

## PRESEALED COMPARISON / WRAPPER FAILURE DETECTION

사전 기준은 final energy abs≤1e−17 Eh,
그 외 float token은 abs≤5e−16×max(1,|expected|), integer/text 구조는 exact.
공백 tokenization 외에는 scientific-field 차이를 허용하지 않는다.
Exact decimal comparison과 whole-output byte comparison을 별도로 기록했다.

Wrapper는 process failure/timeout, 오류·warning·NaN/Inf, missing completion,
missing/duplicate energy, missing wavefunction/example, basis/symmetry/restriction/precision
변경과 energy/추가 관측값 mismatch를 거부한다. Exit0만으로 PASS하지 않는다.
오류·NaN·iteration-limit 문자열을 주입한 synthetic output은 거부됐다.
이 결함 주입은 wrapper 시험이며 공식 solver 내부 수치 fault injection은 아니다.

## EN / NMAX / NDIGITS / REMAINING NATIVE GUARD GAP

Source hash가 같은 [V1 partial audit](../h2_representation_pilot1_resume_v1/evidence/source_audit.json)의
EN=shifted inverse iteration, 최대40회, 내부 reps=1e−64,
NMAX=integral Taylor-series 길이, default integral80 / matrix-stage NDIGITS word-precision 의미를 유지한다.
다섯 input의 저자 EN/nonlinear parameters를 바꾸지 않았다.
새 Pachucki/reference-valued optimizer/hint/R=.4 input을 만들지 않았다.

중요한 사각지대: 원본은 반복 한도에 도달해도 별도 flag 없이 normalization/output으로 간다.
이번 실제 출력에는 반복 횟수·정상 수렴 branch 여부·residual이 없다.
Wrapper는 보고된 failure를 잡지만 **출력되지 않은 한도 도달 여부를 알아낼 수 없다.**
따라서 native_iteration_count=null, native_iteration_limit_reached=null,
native_root_convergence=UNAVAILABLE로 봉인했다.
배포 energy와 동일함은 terminal output 재현의 강한 증거지만
1e−64 내부 수렴/independent residual/lowest-root 검사 결과를 대신하지 않는다.

이 때문에 무조건적인 `H2SOLV_VENDOR_EXAMPLES_REPRODUCED` 또는
strict vendor guard 전체 PASS로 표시하지 않았다.
지원되는 범위는 **ALL_FIVE_VENDOR_PRINTED_OUTPUTS_REPRODUCED**다.
전체 수렴 guard qualification은 UNRESOLVED이며 다음 scope에 조용히 넘어가지 않는다.

## WHAT IS SUPPORTED / UNRESOLVED / STOP

지원: 원본 불변, README static path build success, local5 vendor printed outputs exact reproduction,
observable wrapper guards 및 실행별 비용 기록.
미확인: native termination branch/count, residual/conditioning/lowest root,
integral recurrence correctness, R=.4 physics/precision/representation/비용, B2 독립 동등성.
H2SOLV/논문/우리 checker 모두 계속 감사 대상이다.
NOT_CERTIFIED / NOT_PRODUCTION_APPROVED, 기존 QZ FAIL·reconstruction UNRESOLVED 유지.

사용자 9·10절에 따라 **보고 후 STOP**, R=.4 실행과 B2는 시작하지 않았다.
다음 결정 대상은 원본 실행과 분리한 수렴 상태 관측 또는 독립 residual/root 검사의 범위다.
별도 계측 복사본이 필요하더라도 원본·이번 authoritative output은 그대로 보존해야 한다.
그 실험이나 B1 실행 계약은 이번에 승인·실행한 것으로 간주하지 않는다.

## TESTS / FAILED PREFLIGHT / READ SCOPE

Windows 관련 시험 **86 passed / failure0 / error0 / skip0, 1.11초**. 새 시험36개 포함.
문서·출력·wrapper 시험이며 native root convergence/physics 인증은 아니다.
[관련 시험·검증](evidence/verification.json), [최종 byte seal](evidence/final_seal.json).
LOCAL FULL 생략 / 관련 시험으로 대체 / 새 isolated wrapper·시험·문서·증거와
대시보드 안내만 추가, A physics/common/frozen/fixture 불변. 기준선 갱신 없음.
처음 wrapper 시험은 공백을 늘린 output1건을 잘못 거부하여 1failed/24passed였다.
Vendor 실행 전 공백 정규화 처리를 고친 뒤25passed. 두 로그 모두 보존했다.
결과를 보고 tolerance나 solver source를 고친 일이 아니다.

이번 지시 전체, 필수 문서의 현재 Gate/범위와 V1 감사 기록, 공식5 input/output을 확인했다.
모든 source/recurrence를 재독·재증명했다는 뜻은 아니다.
Scientific-critical-thinking의 증거/해석 분리 절차를 이어 적용했다.
절차 출처 Kassis et al. (2026), [Scientific Agent Skills](https://arxiv.org/abs/2609.00065)는
V1 보고서에 기록했으며 H₂ 물리 reference로 사용하지 않는다.
