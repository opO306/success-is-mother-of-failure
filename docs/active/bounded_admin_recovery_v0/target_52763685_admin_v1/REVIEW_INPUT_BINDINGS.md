# NO ADMIN 실행 입력의 별도 원본 대조

검토자 `/root/state_contract_reviewer`. HEAD `643c532c8d0d578d35ce01ea254780fe7af49bfd`의 고정 소스와 실제 ZIP/record/inventory/승인서/원장/지정 비공개 원본을 읽었다. 프로젝트·모의·원격 시험을 실행하지 않았고 네트워크/API/SSH·서버 행동·운송 소스 수정0이다. 이 문서만 작성했다. 별도 동료 원본 대조이며 독립 서명 인증이 아니다. 진행 중인 ADMIN의 결과를 이 문서에서 합격으로 판정하지 않는다.

## 입력 ZIP와 소스 무결성

ZIP36개 member 전체 SHA를 직접 계산하여 record의36개 및 실제 저장소 파일 각각과 대조했다. ZIP/record/inventory의 이름 집합·개별 hash 불일치0, duplicate0, casefold duplicate0, uncompressed bytes298303 일치다. preservation_before의858개 기존 원본과 과거 실패 파일을 직접 다시 해시하여 불일치0이다. 원본 guardian/기존 hourly amendment와 기존45개 시험은 해당 보존 목록으로 유지된다.

| 실제 입력 | SHA-256 |
|---|---|
| candidate_payload.zip | 1568db4b584335726be3a5d12a68bdef8f4c2aa2367fe5c5d03646cbddf41206 |
| candidate_inventory.json | f85f24182a5c8851663b3f43de0dc6a6175781bccbe79db0294ea6e84f7bf88f |
| candidate_input_record.json | 4bd6dedf24a371206f77fbcba33a821bf1c1b485abb3153e67a6e7ba12b3bd6c |
| human_approval_admin_no_20261009_103957.json | 9af28f3eed22841a203030a60062c3400ed9d2a29a74e282611dc8259602cfd4 |
| admin_budget_execution_prestart.json | aa62122e31d235e3147d4a9c85687db11d212f9926b5b8c58d70520dff8e8179 |

record의 role은 INPUT_BYTE_BINDING_ONLY이며 예상 ADMIN48개다. B95/A320 결과가 아니다. 마지막 시험 소스 hash는 `4aece035627d25e70b27eeb24776fe18b09d17ba2c67a8991f44e9d5906367b3`이다. 직전 검토 이후 변경은 532행의 fake fallback stop argv를 TRACE에 기록하는 문장으로 확인했다. 실제 controller `5ddf91ed03e1abc011944dfd848de12b2bc640446dfcd0174ca6336291e579ef`, bootstrap `272dc670f39c34b534bb94c0552708c465f6fdebfb8530d7b2030d42688e665d`, supervisor `9a37827f788f66c5f13211fc2d471ab514c6b33ef740ffae596010feaffc6d6d`는 최종 정적 검토 입력과 같다.

## 승인 연결

실제 승인서의 record SHA·ledger SHA는 해당 실제 bytes와 일치한다. target protocol SHA `996d102f86b42acffcc5217fb7523e4aa93d8544f30bd665eea3963d8f1733f7`와 승인 참조·원문·scope·B95/A320 false·ID52763685/machine3448/NO/hourly0.28의9개 필드를 protocol과 대조해 불일치0이다. 현재 인간 승인 참조는 call_dbc2f565a36449c3981be1f2db692099이며 raw 승인서는 REAL_CURRENT_HUMAN_APPROVAL 역할이다. ADOPT_RUNNING/adopt=true/restart=false/exclusive=true/auto_retry=false/field_code_changes=false이며 ADMIN만 허용한다.

승인 시간10:39:57.742066UTC부터10:54:57.742066UTC까지다. allocation_start 원본은10:40:30.508369UTC, BEFORE_AUTHORIZED_ADOPTION; NEVER_RESET로 기록되어 이 범위 안이다. prior_closed_window_sha256 `645f47f46a4bc5379c22cba1fb9c595c6597abcb8015b89d931d0fff2859ab47`는 최신 Spain ADMIN closure가 아니라 최초3회 중 역사적 attempt3 closure와 실제 일치한다. Spain ADMIN 실패 보존은 별도의 이전 원장·보존 목록 연결로 유지된다. 이 필드의 대상들을 혼동하지 않는다.

600초/CPU120초/affinity1/512MiB/회수420초/종료확인180초/창0.05/캠페인0.10/물리0/GPU0/이전 실패3회는 실제 승인서에 그대로 있다. hourly amendment SHA는 unchanged 원본 `daa8ec8f9b73deb3f5d212841372725aac522cc1154eb385766b7744d4a54173`와 연결된다. 과거 amendment 원문만으로 이번 실행 권한이 생기는 것은 아니다.

## 최신 비용 원장과 원본

비공개 final prestart 원본 폴더는 `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\admin_no_final_prestart_20261009_103755`다. 인증 토큰은 출력하지 않았다. 실제 instance.json SHA는 `f49c822985216bf3337a708f3208bcbad1ccdfeaa72671ad13c4ba9e85d26372`, charges.json SHA는 `7aa7077db66ae818c10c932310813153bff0b56d288b87c3b1e5a45715c17b1a`이며 projection/ledger 기재와 같다. 실제 billing은 success=true/next_token=null/count=total=results길이6이라 complete=true 근거와 일치한다.

원본 NO API는 id52763685/machine3448/Norway,NO/actual=running/intended=running/dph0.2696296296296296이며 승인된0.28 이하다. 원본 billing NO일별0.174는 인계 전 사용자 workload/readonly 비용 기준선으로 별도 공개했고 이번 ADMIN 시험별 실제 비용으로 사용하지 않는다. Spain일별0.027은 이전 원장의0.025보다0.002 늘어났으며 새 원장에 이를 보수적으로 추가했다. 이전 원장 rawSHA `c4fb17ecd5f9af6faa382a18a4f9ef0f8b538a3ec1d8621d6ca770b905185b4c`와 실제 bytes도 일치한다.

기존 보수 사용액0.04491355611111111111111111111 + 추가0.002 =0.04691355611111111111111111111을 유지한다.0.28×600/3600=0.04666666666666666666666666667을 신규 최대창으로 예약해 총0.09358022277777777777777777778≤0.10이다. 관측UTC10:38:00.644414에서 최초 allocation UTC까지149.863955초로300초 최신성 기준 안이다. 숫자들은 비용 상한과 반올림된 일별 청구이지 정확한 시험별 실행료 인증이 아니다. individual_actual_execution_fee_usd=null은 정직한 미확인 상태다.

## 이 확인의 한계

입력 연결과 보존 무결성에서는 새 불일치를 발견하지 않았다. 실제48개 행별 결과·suite자원·NO outer guardian ARM/종료·원본 회수·외부 stopped·종료 후 청구는 실행 완료 원본으로 별도 대조해야 한다. 입력 대조를 결과 PASS, SIMULATED_VALIDATED 또는 READY 봉인으로 승격하지 않는다. 기존 실패 기록은 유지한다.
