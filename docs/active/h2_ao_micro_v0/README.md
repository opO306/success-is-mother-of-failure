# Micro-pilot evidence versions

정본 결과는 `B_v1_results.json`, `C_v1_results.json`, `summary.json`이다.
`selection_*`와 `spot_*`는 수정 전후 공통의 유효한 Stage A 증거다.

`B_results.json`, `C_results.json`, `INVALID_v0_summary.json`은
**INVALID_MEASUREMENT_FOR_PREDECLARED_REPRESENTATIVE_RULE**이다.
initial `hermi=1`의 AO one-electron representative가 사전 lower-triangle rule과 달랐다.
guard 통과 energy도 사전 규칙을 충족한 최종 결과로 세지 않는다.
원본 내용은 그대로 보존했고 판정은 별도 finding에 기록했다.

각 stage seal의 실행 당시 source hash는 `preservation.json`의 version mapping으로 연결한다.
현재 source snapshot과 당시 실행 source가 다른 경우 archived source도 함께 보존한다.
Windows resource import, post-analysis list indexing, packaging WSL path 실패도 별도 기록한다.

`raw_manifest.json`은 저장소 밖이 아니라 Git-excluded `runs/h2_ao_micro_v0/`의
특정 파일들만 가리킨다. 큰 NPZ는 Git에 넣지 않았다. historical H₂ raw265+145개와
기존 source/compact89개 hash가 유지됐음을 summary/preservation에서 확인할 수 있다.

Numerical research / NOT CERTIFIED / production 미채택 / 전체44점 미실행.
