# B·A 합산 실행료 예산 보충 V1

**BUDGET_SUPPLEMENT_STATIC_READY / DYNAMIC_VALIDATION_PENDING / NOT_PRODUCTION**

기준은 codex/adaptive-experience-tablet-cpu-route-v0 @ d77e08d2다. 기존 closure_v1 전체, A814/B_v3 패키지, 과거 봉인·실패·종료 증거를 변경하지 않았다. 새 규약의 범위를 운송 복사·보강 전에 527ea32c에 먼저 봉인했다. 이 예산 보충 요청은 유료 서버 실행·재시작 승인이 아니다.

## 변경 및 유지한 상한

| 항목 | 새 버전 |
|---|---|
| B+A 합산 실행료 | **$0.10**: 기존 $0.05에서 상향 |
| 각 시험 실행료 | 기존 **$0.05** 유지 |
| 각 시험 전체 할당 | 600초 |
| 각 시험 계산·시험 wall / 누적 CPU | 각각120초 |
| CPU affinity | 1개 |
| 프로세스별 주소 공간 | 512MiB |
| 회수 마감 / 정지 확인 여유 | 420초 / 180초 |
| 시간당 단가 | $0.25 이하 |
| 새 물리 / GPU 호출 | 0회 |

최고 단가에서 B600초+A600초의 실행료 예약은 정확히1/12달러, 약$0.083333이다. $0.10 상한 안에 들어간다. 이것은 상한 계산이며 실제 단가·실행료·전체 청구액의 관측이 아니다. 기존의 “B 전체할당120초 초과 시 A600초 예약 거부”는 새 합산 상한에서 더 이상 적용하지 않는다. 각 창 내부의 시계·자원·회수·정지 여유 검사는 그대로다.

## 실행 순서와 비용 확인

1. 최신 서버·요금·정지상태를 읽기 전용으로 확인한 뒤, **B에 대한 새 명시적 실행 승인**을 받는다.
2. 기존 봉인 B_v3에서95개 전체 시험을1회 실행한다. 실패·error·skip0, 원본 회수·개별SHA, 외부STOP_CONFIRMED와 실제actual=exited/stopped가 모두 확인돼야 한다.
3. B가 실제로 종료된 뒤 공급자 실행료 원본을 확보하고, 사용자가 비용 내용을 확인한 별도cost confirmation을 작성한다. B completion·closure·final instance 해시와 비용 원본들의 개별SHA를 결합한다.
4. 그 비용 확인 기록과 B의 실제95개 결과를 **별도의 새 A 실행 승인**에 묶는다. 비용 확인 자체는 A 실행 승인이 아니다. 확인 시각은 B closure 후, A 승인 시각 이전이어야 한다.
5. A 승인과 남은 예산이 모두 맞으면 기존A814에서320개 전체 시험과 봉인 benchmark를 수행한다. 실패하면 다음 단계 없이 원본을 보존하고 정지를 우선한다.

A는 공급자 실행료 근거, 인간 확인, 정확한B 결과·종료 해시, 비용 원본의 raw SHA를 요구한다. 실제 B 실행료가 문자열로 명시되지 않거나 NaN/Infinity/음수/각 시험상한$0.05 초과이면 거부한다. 비용 확인이나95개/종료 확인이 없으면 A는 재시작 전에 거부한다.

보수적 예산 계산에는 **max(B 최초할당시계 비용상한, 확인된 실제B 실행료)+A600초 최고단가 예약≤$0.10**을 사용한다. 실제 비용이 싸게 보고돼도 최초시계 기준 예약을 줄이지 않는다. 공급자 전체 청구액·저장료 등을 실행료와 합치지 않는다.

중요한 한계: 공급자 비용자료의 금액·해당B 실행 귀속은 사용자 확인에 의존한다. 공급자 응답의 독립 인증·범용 청구자료 파서를 새로 구현한 것이 아니다. 코드의 해시 확인만으로 공급자 자료 내용이 독립 인증됐다고 주장하지 않는다. 비용 계산 상한이나 자기 작성 JSON을 실제 비용 확인으로 취급하지 않는다. 공급자 실행료 근거를 확보하지 못하면 A는 대기한다.

## 새 봉인 연결

- budget_protocol.json SHA: `16db1a2dae38d2fc9d5713e9340b966257611da49ae6856529d9e59d7f126f43`
- 새transport/transport_seal.json SHA: `ea3acc4ddf5e3a34fb53d204059a603040ef1f51bc33fc7446ef5442f870e4b8`
- 이전transport seal SHA: `e40e3d59d7ee17685631b2a93d96e34d510bfe49779d98b8a1a42fcb6501e802` 그대로 보존

새 운송 봉인은 원본 복사9개 중 별도controller만 보강하고 비용 미확인 템플릿을 추가한10개 파일을 결합한다. A/B 승인서는 새로운schema, 예산 규약SHA, 이전·새운송SHA, exact package/inventory/code/protocol/시험수, 각창상한과 합산$0.10을 고정한다.

approval_UNAPPROVED_A/B.json은 explicit/newwindow/restart/exclusive 모두false다. B_cost_confirmation_UNCONFIRMED.json도 human_confirmed=false이며 실제비용·원본·확인번호·시각은 비어 있다. 이 원본 템플릿을 수정해 봉인을 깨지 않고, 승인 또는 비용 확인 때 별도 파일로 작성해 정확한SHA를 결합하도록 준비했다.

기존guardian/supervisor의raw 코드, PID1 식별, 인자배열·SSH stdin, exact package 검사, 320개ID,95개결과 관문, 최초시계, 절대handoff 및 회수 예약, 종료 state machine은 그대로다. 과거admin실패3회/tablet gate1회/CLOSED SHA도 새승인에 유지했다. 이전 종료창을 재개·소급 복구·횟수 초기화하지 않았다.

## 검토와 미확인

**구현됨:** 새 예산 규약·운송 버전·미승인 승인서·B 종료 후 비용 확인 연결·개별 raw seal.

**정적으로 확인됨:** 이전closure가 봉인한68개 파일, 기존protocol4/preservation794/code812/운송8/정책16/admin실패34/실제실패89 해시 불변. 기존A/B ZIP 전체raw해시와inventory 핀 일치. supervisor·probe·회수·게스트wrapper 등 기존운송 복사8개 raw 동일. controller의 변경함수는 local_preflight/validate_policy_receipt, 변경메서드는 show/execute뿐이다. validate_policy_receipt는 기존 검증 후 비용확인 호출1개만 추가했다. show는 합산 상한만, execute는 비용·규약·시각 영수증 필드만 달라졌다. 신규 AST 문법·미승인false·정확한 예산 분수 계산을 확인했다.

**시험됨:** 실제B95/A320/benchmark와 새비용확인 거부·guardian/supervisor 동작은 이번 단계에서 미실행이다. 로컬 stdlib AST/hash/ZIP 검사만 했다. LOCAL FULL·관련 동적 시험은 사용자 금지에 따라 미실행이며 기존 기준선 숫자를 갱신하지 않는다.

**독립 검증됨:** 새로운 외부 권한·서명 인증0건. 이번 버전의 별도 검토 에이전트를 호출하지 않았다. 이전 별도 검토 기록은 당시 버전의 자료로 유지했다.

**미확인:** 현재Vast54815136/machine56006/FR의 실시간상태·단가·SSH·런타임, 실제B/A비용, 공급자 전체청구액, 새운송 동적 연동·자원 집행·OS격리·다른CPU 성능·경험이전경제성. 현장 자동복구·독립영수증 인증·외부재시도원장은 여전히 별도 미구현 범위다.

정적 반례 경로: 미승인·옛schema·예산규약SHA불일치→API전 거부. B 실패/미회수/종료미확인→A금지. 실제비용 근거/확인/해시/시각 누락·불일치→A금지. 각창자원·식별·guardian·회수시간 위반→시험중단·정지 우선. 이것은 소스에서 확인한 경로이며 실제 장애 주입 시험의 통과 기록이 아니다.

구상과 일치하는 점은 합산비용만 높이고 두 시험·승인·종료를 분리했다는 점이다. 아직 실제B종료·비용 확인이나95/320 검증을 수행하지 않았다는 한계를 유지한다. 기존REMOTE_TEST_GATE_FAILED / UNRESOLVED를 바꾸지 않았다.

## Git과 권한

새파일은 전부docs/active/bounded_admin_recovery_v0/budget_supplement_v1 아래다. 기존파일 수정·삭제0, 패키지 재생성0. evidence_seal.json에 새산출물 개별SHA, 변경 목록과 규약·운송·승인서를 결합한다. 최종 로컬 커밋ID와 작업트리 상태는 완료응답에서 실제조회값을 보고한다.

이번 유료 서버 재시작·임대·SSH·전달·원격시험·로컬 프로젝트 동적시험·물리/GPU·push·master 병합은 모두0회다. **이 예산 보충을 실제 B 또는 A 실행승인으로 처리하지 않았다.**
