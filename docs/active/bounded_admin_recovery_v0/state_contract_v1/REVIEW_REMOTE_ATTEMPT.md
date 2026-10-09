# 승인된 ADMIN 첫 원격 시도 원본 검토 — 미실행 / UNRESOLVED

검토자 `/root/state_contract_reviewer`. 실행 후 이미 보존된 API·명령 stdout/stderr·events·supervisor/closure·승인·소스/패키지 hash를 읽었다. 새 네트워크/API/SSH/서버 행동과 동적시험은 수행하지 않았다. 이 파일만 작성했다. 별도 동료 검토이며 독립 서명 인증은 아니다.

검토 대상 실행 source commit은 `169f7df673a675eabd1305e4fac41c3d6c1694e2`, run은 `admin_20261009_095328`이다. 실제 source HEAD를 읽어 일치함을 확인했다. 원본 실행 폴더는 `transport/run_admin_20261009_095328`, private launch/외부 API/청구 원본은 `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\admin_20261009_095328`에 있다.

## 실제 최초 실패와 동작

start 호출은 1회다. `002_restart.stdout`에는 `Required resources are currently unavailable, state change queued.`가 기록돼 있다. CLI 반환0은 실제 실행 성공이 아니다. 재시작 상태 조회 14개는 모두 actual=exited/intended=stopped를 관측했으며 RUNNING 관측은0이다. controller는 `BOUNDED_RESTART_NOT_RUNNING`으로 중단했다. 이 자료는 provider가 자원 부족·대기열을 보고했고 승인된 시간 안에 running이 관측되지 않았다는 증거다. 내부 provider 실패 원인 전체를 독립적으로 증명하는 자료는 아니다.

events의 TRANSPORT_EXIT17개는 initial1/start1/restart_status14/final1이다. SSH/SCP·guest·upload·simulation·download 단계는 없다. running_instance marker, guardian lease/폴더, recovery_attempt, recovered JUnit, B policy_completion이 모두 없음을 직접 확인했다. 따라서 행정45개, B95, A320은 실행하지 않았다.

| 시각 UTC / KST | 실제 관측 |
|---|---|
| 09:54:21.852316 / 18:54:21.852316 | 최초 allocation clock, 승인된 restart 전 기록 |
| 09:54:24.505461 / 18:54:24.505461 | start CLI0, 자원 부족 queued stdout |
| 09:55:12.157455 / 18:55:12.157455 | DEADLINE completion, gate_returncode=null, recovered=false |
| 09:55:17.170221 / 18:55:17.170221 | supervisor fallback STOP_CONFIRMED, STOP 요청1, exited/stopped 관측 |
| 09:55:19.498457 / 18:55:19.498457 | controller closure DEADLINE / actual_stop_confirmed=true |
| 09:56:13.136809 / 18:56:13.136809 | 별도 외부 API 영수증: 정확한 서버 exited/stopped |

재시작 대기 코드는45초 타이머를 쓰지만 마지막 API 지연·sleep까지 포함한 실제 중단 관측은 start 반환 후 약47.65초다. 전체 실제 allocation57.645135초는600초 상한 안이다. 이 구간을 정확히45초 실측으로 표현하지 않는다.

## 종료 제어와 상태 계약의 확인 범위

기존 정지 포트 오류는 실제 initial/final 관찰에서 재발하지 않았다. 두 관찰은 포트 없는 exited/stopped를 STOPPED로 인정했고 핵심 ID54988176/machine150665/ES 및 단가 검사를 유지했다. 실제 supervisor 준비와 fallback 종료 제어는 작동했다. generic guardian은 running marker가 없어 시작되지 않았으므로 guardian 실제 armed/heartbeat/guest 연동이 검증됐다고 표현하면 안 된다.

supervisor_final은 fallback trigger=FAILED를 보존하고 controller completion/closure는 trigger=DEADLINE을 보존한다. 두 원본의 종료 제어 trigger 차이를 임의로 일치시키거나 정상화하지 않았다. 실제 상태·결과와 원래 판정이 각각 남아 있다.

별도 external raw의 SHA `4b2284156fcd5fb418e8e0b98594a3b155e54380952c7e31bb487594e48feb63`를 읽어 external_stop_receipt의 핀과 같음을 확인했다. id54988176/machine150665/geolocation=Spain,ES/actual=exited/intended=stopped이며 ports는 없다. STOP 요청만으로 종료 성공을 판정한 것이 아니다.

## 원본·소스·권한 검토

candidate_input_record의34개 파일을 현재 파일과 개별 SHA로 대조했으며 불일치0이었다. preservation_before의858개 원본·봉인·실패 파일도 개별 SHA 대조 불일치0이다. 소스 현장 수정 없이 최초 고정 입력을 사용했다는 근거가 유지된다.

| 주요 원본 | SHA-256 |
|---|---|
| candidate ZIP | `b5390ec3292d7bfef9d180058e834ffa7747aae4fccbfa80a87972e3ac88c110` |
| candidate inventory | `09d2bc3403eab0e3a365dffdeace7ef6720a280fee09cf871cc67efd2439c8b7` |
| candidate input record | `999053ada62f3b2df57d721c7cc83652037bddfb644e9a9daeee6498edbd17ba` |
| launch.json private | `01602a84b6aae9f9c0571c1670c3e409b1db6c8ba10fc85a096e5618fcb7232f` |
| closure.json | `48e6456d9482fb1dc32f5ad2da658224ab621a9f66f700977f2fc446e9573509` |
| supervisor_final.json | `4851f00d599b620eab3f55f04cc567e90de2ea9f21bb533b610b434291b89b65` |
| restart stdout | `291c2a19799c4c27d8235787a5df1b5fb3d43450ebb94c1b6d455c27604f6726` |
| external_stop_receipt.json | `00f111581a231e443bde67bc32ce809b926de89b939a780379d616974b90e12e` |
| actual external API raw | `4b2284156fcd5fb418e8e0b98594a3b155e54380952c7e31bb487594e48feb63` |
| prestart budget ledger | `c5a6a13337093e77195a4ad8ed48b84e6d4597aee1598e592f92f1baa6a35bf7` |
| charges_after.json private | `5c27457afc8ac4410c40c11100f2ac9bc54d5ceb26e4ae5eb041a4a769262e7e` |

소스 controller SHA는 `1b71f2bdcf4da2aa93231f0271189ed87a81d994ac89bf7db77f46387f8cdaa4`, bootstrap은 `be498587106f50932c64978dd028129a5b47f62cd22114058ff555d4004654e3`, runner는 `5fa217cfb84dede39670d1e12ee82cf6087a9ddb6d89a506b657de6966f2cd30`로 고정 입력과 같다.

실제 승인서는 HUMAN_PAID_ADMIN_VALIDATION_ONLY_V1, ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY, package_kind=ADMIN, B95_authorized=False/A320_authorized=False, expected_tests45다. 후보 record와 budget ledger의 승인서 SHA가 실제 파일에 일치한다. 이 승인을 B95/A320 실행 승인으로 바꾸지 않았다. start1회·자동 재시도0·코드 수정0을 유지했다. 기존 역사 실패3·tablet gate1·B paid start 실패1·filename 실패1·Spain B prestart1도 원본/승인/closure에 보존돼 있다.

## 비용과 미확인

allocation57.645135초와 승인 최대단가$0.25/h의 산술 상한은 **$0.004003134375**로 closure와 같다. 이는 실제 provider 개별 청구액이 아니다. prestart conservative spent bound는$0.04091042173611111111111111111이고, 이번 산술 상한을 더한 값은$0.04491355611111111111111111111이다. 이 계산도 캠페인 예약/상한이며 실제 개별 비용이나 미래 B/A 실행 충분성으로 확정할 수 없다. charges_after metadata는 success=true/next_token=null/count=total=results6임을 읽었지만 일별 누적 청구를 이번 시도의 개별 요금으로 분리·인증하지 않았다.

45개 JUnit/status가 없으므로 failure/error/skip을0으로 판정하지 않는다. 상태는 미실행이며 실제 PASS0이다. 실제 CPU·메모리 비용, guest 실행 환경, 행정 반례 동작, 정상 full lifecycle, generic guardian 시작·연동, STARTING 자료, 실제 source/results 원격 회수는 미확인이다. 원격 게스트 원본이 만들어지지 않았으므로 local/API/supervisor 실패 원본을 보존한 것이다.

## 완료 분류와 판정

| 구분 | 이 검토에서 확인한 범위 |
|---|---|
| 구현됨 | 별도 ADMIN 운송·상태 계약·예산/승인 경계·45개 반례 코드는 고정 입력으로 존재 |
| 시험됨 | 실제 initial STOPPED·restart 요청1·bounded wait·DEADLINE·supervisor fallback STOP·final STOPPED |
| 독립 검증됨 | 독립 서명 인증0. 별도 동료 검토가 보존된 원본/hash/명령수/외부 API 영수증을 읽어 대조 |
| 실패·반례 | provider 자원 부족 queued, running 미관측, BOUNDED_RESTART_NOT_RUNNING |
| 비용·성능 | allocation57.645135s·상한$0.004003134375; 개별 실청구/시험 CPU·RSS 미확인 |
| 미확인 | 행정45개·B95·A320·guardian armed·원격 회수 및 정상/오류 모의 전이 |
| 다음 행동 | 별도 사용자 지시·자원 상태·현재 예산 확인 전 추가 실행 없음 |

원격 시도의 raw closure는 **DEADLINE / STOP_CONFIRMED**다. 전체 행정 모의 검증 목표는 **UNRESOLVED**다. **ADMIN_TRANSPORT_SIMULATED_VALIDATED 또는 새 준비 READY 봉인을 생성할 근거가 없으며 생성하면 안 된다.** 실제 종료 확인과 미실행 시험을 합쳐 프로젝트 시험 통과로 표현하지 않는다.
