# NO ADMIN 실제 실행 원본의 별도 동료 검토

검토자 `/root/state_contract_reviewer`. 소스 HEAD `643c532c8d0d578d35ce01ea254780fe7af49bfd`, actual_admin_result 및 지정된 비공개 실제 원본을 직접 읽었다. 신규 네트워크/API/SSH·시험·서버 행동·소스 수정은 하지 않았고 이 문서만 작성한다. 별도 동료의 원본 재대조이며 독립 서명 인증·독립 재실행·계산기 인증이 아니다.

**대조 결론: 이번 ADMIN48개 실제 실행의 PASS·원본 회수·외부 실제 종료 기록은 서로 일치한다.** B95/A320는 실행되지 않았고 정확한 개별 시험별 실제 청구는 미확인이다. 이번 제한 행정 시험을 프로젝트 시험 통과나 경험 이전·다른 CPU 성능 개선으로 표현하면 안 된다.

## 원본·입력 바인딩

private root `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\admin_no_20261009_103957\transport_raw`의 실제2142개 파일 전체 SHA를 raw_inventory와 다시 대조해 불일치0이다. 공개한 subset copies의 기재된 rawSHA도 불일치0이다. public JSON의 API key/password/access token/secret 필드 패턴은 발견하지 않았고 raw API/full billing은 private에 유지했다. 이 확인은 알려진 필드 패턴과 공개 파일 범위를 대조한 것으로 모든 가능한 민감정보의 형식적 부재 증명은 아니다.

회수 evidence.zip은2077개 member, manifest 기재2076개 원본+manifest다. 모든 member의 raw hash 불일치0이며 instance52763685/run_admin_no_20261009_103957/controllerSHA `5ddf91ed03e1abc011944dfd848de12b2bc640446dfcd0174ca6336291e579ef` 바인딩이 일치한다. 전체ZIP SHA는 `ffa5b1802c211a875daa595cb0eb220e87457f3fc771fc36619d2838f65cda86`으로 recovery_verified 원본과 같다. recovered admin_ticket/armed bytes는 transport 송신 원본과 동일하고 ticket의 armed_sha256/승인 참조/expected48/실제ID와 일치한다.

실행 후 candidate36개 소스 재해시 불일치0, preservation858개 기존 소스·실패·봉인 재해시 불일치0이다. 원본 ZIP `1568db4b584335726be3a5d12a68bdef8f4c2aa2367fe5c5d03646cbddf41206` 및 inventory `f85f24182a5c8851663b3f43de0dc6a6175781bccbe79db0294ea6e84f7bf88f`는 candidate_verified·closure·승인 입력과 같다. local project dynamic/GPU/새 물리/push/mastermerge는 이번 실행 범위에서0으로 남는다.

## 48개 결과와 자원

JUnit 실제 testcase48개, 이름 unique48개, failure/error/skipped node0개다. case_results48행의 ID집합은 JUnit과 같고 전부PASS다. status tests=expected_tests48/failed0/errors0/skipped0/error=null/blocked_attempts=[]와 unittest 원문의 'Ran48 / OK'가 일치한다. 이것은 실제 유료 서버에서 돌린 CPU 행정 모의 시험 결과이며 외부 실제 provider/SSH/SCP 호출은 시험 내부의 fake 경계다.

| 측정 범위 | wall | CPU | 메모리 | affinity |
|---|---:|---:|---:|---|
| 행정48개 suite |3.236843640초 |1.195090497초 |peak RSS36,728,832B |[0] |
| 실제 remote entry와 child 합계 |3.599478017538786초 |aggregate1.887512616초 |aggregate peak RSS56,643,584B |[0] |
| 최초 승인 인계부터 외부 transport closure |81.965539초 |시험 CPU와 구분 |시험 RSS와 구분 |인계 제어 |

suite/entry는512MiB·CPU120초 및 entry30초 안이다. status의 physics/GPU/real_provider_inside_simulation/real_subprocess_inside_simulation은 모두0, B95/A320 false, independent_authority_certification false다. 외부 actual execution의 command 영수증19개는 모두 rc0: API initial1/control9/final1, identity1, SCP upload4, admin_simulation1, package_evidence1, download1이다. restart0·실제 admin payload1·자동 시험 재실행0이다. 내부 fake 반례의 start/stop/Gate 숫자를 실제 명령 수에 더하지 않는다.

## 실제 guardian·supervisor·종료

guardian ARM UTC10:40:35.704673, instance52763685/machine3448/NO/현재 승인 참조/unchanged guardianSHA `2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802`/기존 immutable amendment SHA/현재hourly cap0.28/실제rate0.2696296296296296/deadline240/confirmation180이 연결된다. 이번에는 generic guardian가 실제 시작했고 외부 STOP_REQUEST는1회다. final 원본의 관측은 running/stopped에서 exited/stopped로 바뀌며 STOP_CONFIRMED/triggerCOMPLETED를 기록했다. supervisor final은 같은 영수증과 failure=null, allocation age79.484초를 가진다.

closure status/execution_outcome=COMPLETED, gate_returncode0, recovery_verified=true, actual_stop_confirmed=true, clock_fault=null, 최초10:40:30.508369UTC→closure10:41:52.474428UTC/81.965539초다. 독립된 이후 외부 provider readonly 원본10:42:53.396505UTC도 정확한NO52763685/m3448에서 actual=exited/intended=stopped다. 외부 fullraw SHA `5d22184757be8445d279dfc02f4f0bba2acb14889f309e44ee5a7ba29e135e0c`와 receipt projection을 직접 대조해 일치했다. 이는 live 재조회가 아닌 보존된 별도 조회 원본의 peer 대조다.

## 청구와 다음 예산의 제한

closure의 cap-rate 계산 상한은0.28×81.965539/3600=`0.006375097477777777777777777778`달러다. 실제 시험별 청구값으로 표현하지 않는다. after charges rawSHA `ccddfd1f5530ea61ced98a1775b0cc5ae539b3c64203a16225cec4e2f521bda2`를 다시 계산했고 billing_after의 success=true/next_token=null/count=total=results길이6과 일치한다. 실제NO 일별 amount0.192(gpu rental0.160+disk0.032), Spain0.027이다. 'gpu' 청구 항목명은 서버 임대 요금이며 이번 GPU 계산 호출 증거가 아니다.

NO prestart0.174(rental0.143+disk0.031)→after0.192의 전체 차이0.018은10:38 전조회부터10:42:53 후조회 구간을 포함해 인계 전 준비도 포함한다. 개별 시험별 정확한 비용은null이다. 최초 readonly 일별0.054→prestart0.174의0.120도 이미running 사용자 서버의 준비 기간 기준선 변화이며 이번81.965539초 실행료로 귀속하지 않는다.

기존 보수 원장0.04691355611111111111111111111을 유지하고 max(이번clock 상한0.006375097477…, 전체청구interval0.018+rounding reserve0.002)=0.020을 더하는 제안 계산은0.06691355611111111111111111111이다. 이는 단순 시험 비용 추정값을 낮추지 않는 보수 방법이지만 formal invoice certification은 아니다. 이 문서 작성 시 최종 append 원장 생성은 검토하지 않았다.

이 보수 방법을 적용하면 잔여0.03308644388888888888888888889는 현재 controller가 요구하는 다음600초 예약0.25×600/3600=0.04166666666666666666666666667보다 작다. 이번 통과와 다음B/A의 승인·예산 충분성을 구분해야 한다. 새예산/범위 결정 없이 다음 full-window를 자동 실행하거나 잔액을 초기화하면 안 된다.

## 핵심 개별 SHA-256

| 실제 원본/공개 동일 bytes | SHA-256 |
|---|---|
| raw_inventory.json |27599b326aba4d4f33d07188376c52891bbe3e3a4c4f7dc4ee64b94fc4ddedc7 |
| closure.json |380c9e08149d7622582d6f6fdd1d50132829a82567877398f1fc386e70d682c8 |
| guardian/armed.json |c8e80b25f730147643d65eeac250ceb302fb67a9d006639be78580fb1574f59e |
| guardian/final.json |224f4b8ad46dd5e43aaa1f2256ccc1b942bbbda1daf7d81d557eb83135228674 |
| supervisor_final.json |cf5909043cdd3d0356a7d0acdfe8086599b432b16ce165e1ad812b97802e50df |
| recovered/admin_entry_exit.json |53de395ecd7111e5a16b4607037bc0f90ea09c70a638becc9fe2628129b1f4c0 |
| recovered/output/status.json |142c60420ddf897717df4ac007f7460ecef3212468d39b77c8a325576eeedc58 |
| recovered/output/case_results.json |0a9eec7a7023594fb203df80d3d78c32c5f420da732fbfc75275e0de952eeebc |
| recovered/output/junit.xml |4daf1a459af991b3c8ccf348635522425899d5f8ef3995ae8079bcad66b519db |
| external_stop_receipt.json |873b2b6102c7a40e2ca9896630f4ce9d205a5efa2ef579f3db5225628af73c24 |
| billing_after.json |33a7a1f539d6b8a77f14160ec8a694674da5fc35077f967b42b788e5a41e6320 |

## 구상·판정 범위

행정 오류를 실제 계산 오류와 분리하고 승인·원본·최초clock·종료를 유지하면서 모의48개 및 outer 실제운송 종료를 확인하는 목적에는 이번 증거가 맞는다. 새로운 계산 결과 정확성, 기존 경험 탭320개, B정책95개, 성능이전·학습·CPU성능개선, 독립 서명권은 확인하지 않았다. 이전 실패3회·태블릿failed gate·추가 서버/명령 실패의 원본을 그대로 유지하고 이번 별도 성공만 append해야 한다. LOCAL FULL은 실행하지 않았으며 프로젝트 기준선 숫자는 불변이다.
