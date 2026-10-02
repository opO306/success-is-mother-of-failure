# H₂ sealed QZ44 evidence

판정은 **NUMERICAL FAIL: 44 attempted / 43 accepted / 1 refused**, 기존 reference 기준 초과 4점이다.
전체 설명은 [보고서](../H2_STATIC_QZ44_SEALED_VALIDATION_V1.md)를 본다.
이 폴더는 기존 V0 경로를 바꾸지 않은 fresh 실행의 compact evidence다.

| 파일 | 내용 |
|---|---|
| [points.csv](points.csv) | 44점별 accepted/refused·BO energy·orth/H/eigen/MO ERI residual·runtime·peak RSS·reference 비교 |
| [execution_seal.json](execution_seal.json) | 실행 전 source/config 152개·새 harness/시험 6개·runtime 34개 hash, grid/rule/guards/reference 기준 |
| [results.json](results.json) | 전체 fresh 기록, overlap spectra·AO 진단·44 artifact SHA-256 |
| [post_run_seal_check.json](post_run_seal_check.json) | 실행 후 seal 재확인과 results hash |
| [comparison_seal.json](comparison_seal.json) | 기존 reference/checker/criteria와 새 decision code 봉인 |
| [gate.json](gate.json) | 0.001 hartree pointwise 판정, refusal, 기존 accepted/control 72 비교 |
| [reference_comparison.json](reference_comparison.json) | 변경 없는 기존 checker의 P1/P2/P3·표본 minimum·해리 postprocessing |
| [checker_records.json](checker_records.json) | 기존 checker에 전달한 새 curve와 보존된 atomic/ghost 자료, 새 atomic solve 아님 |
| [failure_diagnostic_seal.json](failure_diagnostic_seal.json) | 실패 5점 진단 source/input 봉인, curve 교체 금지 |
| [failure_diagnostic_results.json](failure_diagnostic_results.json) | 동일 binary64 AO/C의 60/80자리 선택 MO contraction 및 R=0.5 residual 평가 진단 |
| [preservation.json](preservation.json) | 기존 raw 528개 변경 없음, frozen base 152개와 새 NPZ 44개 확인 |
| [raw_manifest.json](raw_manifest.json) | 새 scoped raw 118개 hash/byte 크기 |
| frozen_source/ | 기존 kernel/config/reference/checker 7개 byte-exact snapshot |
| *.py.txt / protocol.json.txt | 실행한 신규 harness·diagnostic·packager·시험 source |
| tests_*.log / *_console.log | 이번 실제 시험과 실행 로그 |
| [preflight_failure.json](preflight_failure.json) | numerical 실행 전 새 시험의 UTF-8 해독 실패 보존 |
| [preflight_test_executed.py.txt](preflight_test_executed.py.txt) | 실패한 첫 사전 시험 source, 최종 source와 구별 |

원시 curve JSON/NPZ와 실패점 진단은 `runs/h2_qz44_sealed_v1/`에 보존한다(Git 밖).
refused R=0.5 energy/eigen residual은 null이다. 고정밀 진단으로 판정을 대체하지 않았다.
MO ERI pair-interchange accuracy는 **UNRESOLVED**, 전체 solver/integral은 **NOT CERTIFIED**다.
`.gitattributes`의 `* -text`는 snapshot과 실행 증거의 byte 보존을 위한 것이다.
