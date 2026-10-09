# 수정 전 별도 동료 검토 — 상태 계약 V1

검토자 `/root/state_contract_reviewer`. 기준 HEAD `3090460280219b8964097caafc25a54861906121`. 구현자의 요약을 반복하는 대신 기존 controller·supervisor·guardian·게스트 운송 코드와 보존 API 원본을 직접 읽었다. 네트워크, SSH, 유료 API, 모의 실행, 프로젝트 동적 시험은 수행하지 않았다. 이 파일 외에는 수정하지 않았다. 이 기록은 **읽기 전용 동료 검토이며 독립 권한 인증이 아니다**. 아래 반례는 실행 재현 결과가 아니라 코드와 실제 원본 대조에서 찾은 정적 결함·위험이다.

## 실제 증거와 원본 해시

비공개 원본 위치: `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\target_54988176_b_v1`. 민감 토큰을 이 기록에 복사하지 않았다.

| 원본 | 실제 관측 | SHA-256 |
|---|---|---|
| `readonly_instance.json` | ID54988176/machine150665, ES, actual=running/intended=running, 직접 SSH40470, API 릴레이23876, ports 있음 | `f0f3f08c45b6ea95648b0c2ead523090af4e0f1b175e895e76a2cdeffb879fb1` |
| `preparation_stopped_instance.json` | actual=running/intended=stopped, ports 유지. 이름에 stopped가 있어도 실제 정지 완료 자료가 아니다 | `8d0e1d650751a083cb36874f02a2e67ca6f4f26ffb84a67cda3714a5afed60ec` |
| `preparation_final_instance.json` | actual=exited/intended=stopped, ports 생략 | `7e8970417a9e8d5133b8e8c0c856002de23845512c3ec8eee82e7e9348701fa7` |
| `external_final_instance.json` | actual=exited/intended=stopped, ports 생략 | `d844024c65120adef4bbb51ceaeddeab9f6c0fde79154fcabc638701062b2c77` |

완전한 STARTING 단계 원본은 위 자료에 없다. STARTING의 자료 형식과 지연 조건은 **UNCONFIRMED**이다. 합성 반례를 실제 관측으로 표현하면 안 된다. `exited/intended=running` 반례도 위 네 원본의 관측 사실이 아니라 queued 시작 가능성을 검토하기 위한 합성 입력이다.

| 검토 대상 | 원본 SHA-256 |
|---|---|
| `target_54988176_b_v1/transport/controller.py` | `4fdbd060957f9895adad7ac10cc38a4b33301f9325e8aaadf5c38c54642fe890` |
| `target_54988176_b_v1/transport/supervisor.py` | `205984492ec7eb5306ce6190f70c78b1c6057542c29a20c483adef0a23a13e57` |
| `experiments/adaptive_execution_real_learning_pilot_v0/guardian.py` | `2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802` |
| `target_54988176_b_v1/result_b_95_es_20261009_082647/closure.json` | `e479dd006a0f7747dd6af413ad874d7dc794b83512872c4c78e0e76ee0949118` |

## 최초 실패와 사전 검토 공백

기존 controller 325–341행의 `show()`는 상태와 관계없이 relay SSH, public IP, 직접 실행 포트 매핑을 요구한다. 333행은 `ports` 생략을 빈 목록으로 바꾸지만 승인 포트가 그 목록에 없다는 이유로 334행에서 거부한다. 실제 exited 원본 두 개는 정확한 핵심 식별값과 정지 상태를 담고 있으나 이 조건을 만족하지 않는다. 보존된 실패 closure는 `EXACT_INSTANCE_API_BINDING`, 할당 시작 null, 시험 returncode null, UNRESOLVED를 기록한다. 정지 원본이 이미 있었는데도 상태별 대조와 전체 호출 영향 검토를 하지 않은 것이 검토 공백이다.

## 모든 직접·간접 호출 경로

행 번호는 위 SHA의 기존 파일 기준이다.

| 변경 대상 | 영향을 받는 부분 | 필요한 시험 | 미확인 사항 |
|---|---|---|---|
| controller.show | initial468 → 정지 관문470, restart504 → running 판정505 | 실제 exited 포트 생략, wrong ID/machine/country, queued 상태, 시작 지연, UNKNOWN | 실제 STARTING 원본 |
| controller.show | control352 → running 판정353 | running/stopped 차단, 주소·포트 누락 지연과 명시적 불일치 구분 | API와 SSH 사이 환경 변화 |
| controller.show | final590 → closure stop 확인599 | 종료 중/완료 상태, 포트 생략, API 장애, machine/country 불일치 | provider 전체 장애 |
| controller.control | py366, upload374, recover387; recover의 py385도 control 경유 | API 전후 marker 경합, 추가 SSH0, 부족한 마감 여유 | OS 원자성 |
| controller.py/run | probe532, source_verify539, gate556, recovery385; upload537/538/549/550, download394 | 연결 실패·단절, PID1 불일치, ZIP 변조, 부분 회수 | 실제 guest 장애 전체 |
| controller.execute 예외 | except565 → recovery569 → finally575, closure602 | 모든 실패 뒤 원본/STOP/closure 유지, 자동 재시작0 | 실제 디스크·프로세스 장애 |
| supervisor.main | running marker86 → guardian95; finally107 → guardian wait119 → fallback132 | guardian 미시작/조기 exit, lease 오류, 완료 marker 경합, 확인 시간 부족 | 실제 OS scheduling |
| supervisor/guardian.confirm_stop | stop 요청 후 show와 actual 종료 확인 | STOP 요청 성공이어도 실제 running이면 미확인, API 장애, 핵심 식별 불일치 | provider 제어 가용성 |
| guardian.main | 최초 API108; ongoing API138은 real_a일 때만; marker133·deadline128·stop148/153 | B의 generic 분기와 A heartbeat 분기를 혼동하지 않음 | B 실행 중 연속 관측 |

## 구현자가 놓칠 수 있는 반례

1. **actual/intended 복합 상태.** 실제 running/stopped 원본은 종료 진행 중이며 신규 SSH 실행을 허용하면 안 된다. 반대로 exited/running을 초기 STOPPED로 받아들이면 이미 queued된 시작에 추가 restart를 보낼 수 있다. 초기 restart 관문에는 두 상태가 모두 정지인지 확인하는 조건이 필요하다.
2. **API 조회 중 제어 상실.** control345–357은 supervisor/marker/final을 API 조회 전에만 검사한다. 조회 중 completion marker가 생겨도 반환 후 py/upload/recover가 명령을 보낼 수 있다. API 조회 뒤 재검사와 명령 차단 여부를 시험해야 한다.
3. **긴 운송 명령 중 guardian 상실.** B generic guardian에는 A의 지속 API/heartbeat 분기가 없다(guardian136–145). controller는 gate 최대140초 대기 중 control을 재호출하지 않는다. armed 이후 guardian exit와 supervisor 종료를 주입하고 명령 중단·추가 시험0을 확인해야 한다. 기존 guardian 봉인은 유지한다.
4. **시계 오류가 finally를 다시 실패시킴.** age297–304가 drift를 거부하면 finally580/601의 age 재호출도 예외가 된다. STOP 절차와 별개로 closure가 탈락할 수 있다. drift 뒤에도 실패 원본·마감·실제 종료 확인 결과를 보존하되 COMPLETED 승격은 금지해야 한다.
5. **종료 관측과 실행 권한의 기준 혼합.** final show도 실행 포트와 단가 관문을 요구한다. 실제 정지·단가 변화를 관측한 원본은 보존하고, 실행 cap 위반 이유는 별도로 거부해야 한다. 포트가 사라져 실제 정지 확인을 잃는 오류를 final로 옮기면 안 된다.
6. **종료 확인의 핵심 식별 공백.** guardian confirm_stop49–53 및 supervisor20–24는 ID/actual만 확인한다. machine/country 불일치가 STOP_CONFIRMED가 될 가능성을 시험해야 한다. 원본 guardian를 수정하지 않는 새 CheckedCli 연결부가 실제 main 경로에 사용되는지 확인해야 한다.
7. **모호한 입력 구조.** ports=null, 빈 목록, 잘못된 자료형, duplicate JSON keys, NaN 요금, 승인 포트와 다른 포트 동시 포함, 다른 public IP/relay 경로, UNKNOWN actual 상태를 반례로 넣는다. 필드가 아직 준비되지 않은 경우의 제한 대기와 명시적 불일치 즉시 거부를 구분한다.
8. **판정 불일치.** controller는 DEADLINE marker를 쓸 수 있으나 guardian133–135는 COMPLETED/FAILED만 받는다. supervisor fallback132는 원래 종료 trigger와 무관하게 FAILED를 보낸다. 실행 결과와 종료 제어 결과를 혼동하거나 과거 실패를 정상화하지 않아야 한다.
9. **회수 후 승격 공백.** 명세와 manifest/hash가 맞아도 ticket/armed 불일치, JUnit 부족·중복·error/skip, 누락 status, 잘못된 메모리/CPU 값이면 completion 생성과 B 통과 영수증 생성을 차단해야 한다. TEST_ONLY 모의 결과는 실제 B95 통과 근거가 아니다.

## 검토 판정 및 후속 검토 기준

현재 결과는 **수정 전 결함·반례 확인 / 새 버전 미검토 / 동적 재현 미실행**이다. 준비 완료나 원격 시험 통과로 판정하지 않는다. 사용자 추가 지시에 따라 모의 동작 검증은 승인된 유료 CPU 격리 환경에서 진행하며 로컬 동적시험은 실행하지 않는다. 새 코드와 실제 모의 실행 결과를 다시 대조하고 모든 실패에서 잘못된 서버 명령0·추가 시험0·승인되지 않은 재시작0·원본/종료 기록 보존을 확인해야 한다. STARTING 실제 관측, 실제 OS/SSH 장애 전체, 시험 개별 실청구는 끝까지 미확인 범위를 남긴다.

기존 실패 기록·원본 ZIP·guardian·B95/A320 원본 시험·계산식·서명 권한·기준선은 수정 대상이 아니다. 이 동료 검토에는 유료 B95/A320 실행 승인이나 독립 인증 권한이 없다.
