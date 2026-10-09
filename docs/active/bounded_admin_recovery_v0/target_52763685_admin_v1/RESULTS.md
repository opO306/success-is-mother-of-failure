# 승인된 NO 서버 ADMIN 원격 검증 결과

**ADMIN_TRANSPORT_SIMULATED_VALIDATED / 실제 ADMIN 운송 COMPLETED / STOP_CONFIRMED.**

Vast52763685 / machine3448 / Norway,NO에서 승인된 행정 시험을1회 수행했다. 기존45개와 새 대상3개 method의 **48개 PASS, failure0/error0/skip0**이다. 실제 외부 guardian ARM, SSH/PID1/ZIP 전달, 원본 회수, guardian STOP1, supervisor 종료 영수증, 별도 API의 actual=exited/intended=stopped를 확인했다. **B95/A320은 미실행이며 이전 REMOTE_TEST_GATE_FAILED / UNRESOLVED를 바꾸지 않는다.**

## 결과 구분

| 구분 | 실제 확인한 범위 | 한계 |
|---|---|---|
| 구현됨 | 상태별 식별/주소 검사, ADOPT_RUNNING start0, 현재 인간 승인·protocol SHA 정확 연결, .28 정확 NO 예외, supervisor 실패시 기존 종료 상태기 fallback | 새 ADMIN namespace의 연결이다. 향후 B/A 대상·승인·패킷 준비 완료를 뜻하지 않는다 |
| 시험됨 | 원격 Linux/Python3.12 CPU 행정48개 PASS. 실제 외부 supervisor→원본 guardian ARM→회수→STOP 완료 | 시험 내부 Vast/SSH/SCP/시간·프로세스 경계는 fake이며 외부 운송의 정상 경로만 이번 서버에서 실제 확인했다 |
| 독립 검증됨 | 별도 동료가 실제 ZIP/member·승인·원장·JUnit48·private2142·회수2076·외부 STOP 원본을 직접 대조. REVIEW_INPUT_BINDINGS.md / REVIEW_ACTUAL_ADMIN.md | 구현자와 별도 동료의 증거 대조다. 별도 서명권·인증기관·형식 증명은 없다 |
| 실패·반례 | 원본 Spain stopped 포트 결함 재현, 잘못된ID/machine/국가/주소/포트, 지연·SSH실패·누락/변조·guardian/supervisor 소실·시계·회수·부분결과·skip·종료장애를 실제 운송 코드의 mock 경계에서 확인 | 유료 실제 서버를 고장 내어 모든 장애를 재현하지 않았다. 이전 실패와 원본은 불변 보존 |
| 비용·성능 | suite wall3.236843640s/CPU1.195090497s/RSS36,728,832B. entry wall3.599478018s/aggregate CPU1.887512616s/aggregate RSS56,643,584B. affinity1/AS512MiB | 단일 서버·1회 행정 시험 측정이며 다른 CPU 개선이나 경험 이전의 근거가 아니다. 기존 사용자 프로세스 부하가 있던 서버다 |
| 미확인 | 정확한 시험별 공급자 청구액, 모든 실제 운송 장애의 재현, 독립 승인 서명 권한, B95/A320·합성검색 비용, 다른 CPU 개선·경험 이전 | provider의 일별 반올림 자료는 정확한 시험별 비용으로 바꾸지 않는다 |
| 다음 행동 | 이번 원본·새 승인·운송 입력·결과를 별도 버전으로 보존. 다음 B는 새 대상/원장·종료 계획과 별도 인간 승인 필요. A는 실제 B 통과와 비용 확인 후 별도 승인 | 현재 잔액으로 기존 최대단가600초 창을 그대로 예약할 수 없다. 이번 승인으로 추가 임대/재시작/재시험하지 않는다 |

## 실제 실행과 종료

- 인간 승인: call_dbc2f565a36449c3981be1f2db692099의 “이번 행정 시험 $0.28/h·독점 사용·종료 승인”. target_protocol.json과 실제 승인서의 참조·원문·ADMIN scope를 정확히 연결했다.
- 입력 고정 커밋643c532c. actual trial1회, start/restart0, 신규 임대0, 자동 재시험0, 실행 시작 후 코드 수정0.
- 최초 인계 clock:2026-10-09T10:40:30.508369Z(한국19:40:30). closure:10:41:52.474428Z, **81.965539초**. mono81.953/wall81.965539, clock fault 없음. 전체600초 내에서 한 번 기록하고 초기화하지 않았다.
- 실제 guardian: 원본 SHA2bd2dd3e… 유지, outside_guest ARM, deadline240초(기존 원본 예외의 더 좁은 기한), confirmation180초. 이번 entry의 실효 wall30/SSH50초로 원래120초 상한보다 좁게 제한했다.
- 회수·행별검증 후 COMPLETED marker. 실제 STOP_REQUEST1회, running/stopped→exited/stopped를 관측했다. supervisor failure=null. 외부 read-only API는2026-10-09T10:42:53.396505Z(한국19:42:53)에 같은NO52763685/m3448의 **actual=exited / intended=stopped**를 다시 확인했다.
- 잘못된 서버 식별/누락값을 만들지 않았다. 화면proxy13685와 API13684의 차이는 보존하고 검증된 직접81.166.162.13:12408만 사용했다. 실제 PID1CONTAINER_ID52763685를 확인했다.

## 비용과 회계 경계

실제 관측 단가는$0.2696296296296296/h이며 이번 ADMIN 승인 예외$0.28/h 안이다. 인계 제한창의 최대단가 산술 상한은 **$0.006375097477777777777777777778**($0.28×81.965539/3600)이다. 이는 provider가 분리 청구한 정확한 시험료가 아니다. 원래 창 상한0.05와 캠페인0.10은 유지한다.

서버는 처음부터 running이었다. 최초 읽기 자료의 NO 일별 누적0.054(실행0.024/저장0.030), 실행 직전 기준선0.174(실행0.143/저장0.031), 종료 후0.192(실행0.160/저장0.032)를 공개한다. **준비 중 기존 running 서버에 과금이 계속됐다.** 인계 전0.054→0.174의 증가0.120을 인계 후 시험료로 바꾸지 않는다. 전체 읽기·준비 기간 또는 계정 전체 지출이0.05/0.10 이하였다거나 준비 비용이0이었다고 주장하지 않는다. 기존 작업의 용도·비용 배분은 미확인이다.

직전→종료 후 일별 총액 차이0.018은 더 넓은 조회 간격의 값으로 인계 전 준비·저장 비용과 반올림을 포함한다. 비용 원장은 기존 보수액0.046913556111…를 유지하고, max(이번clock상한0.006375097478…, 더 넓은 일별 차이0.018+재량 반올림 예약0.002)=0.020을 추가 예약했다. 새 **보수 사용/예약액0.066913556111…**, **잔액0.033086443889…**다. 이 예약 방식은 정확한 공급자 비용 배분 인증이 아니다.

기존600초·0.25/h 최대 창 예약0.041666666667…는 현재 잔액보다 크다. 다음 B/A 최대 창의 예산 충분성을 선언하지 않는다. 정확한 청구 자료·실행 대상·상한 안의 계획과 별도 승인을 다시 연결해야 한다. stopped는 임대 삭제가 아니므로 저장료가 계속될 수 있으며 이번 승인은destroy가 아니다.

## 봉인·원본·해시

입력ZIP36개/member/raw·inventory 불일치0, 보존 대상858개 불일치0, 기존 state_contract_v1 입력34개·기존 ZIP 불변을 확인했다. 회수 evidence ZIP의2076개 파일을 manifest와 개별 SHA-256으로 검사하고, Windows 외부 제어 원본까지 포함한2142개를 raw_inventory.json에 연결했다. 모든 원본은 private evidence에 보존하고 토큰이 있을 수 있는 API raw는 Git에 넣지 않았다. 공개 사본도 원본 SHA와 연결했다.

| 원본 | SHA-256 |
|---|---|
| 기존 경험 탭 code_seal.json | 18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09 |
| 원본 guardian.py | 2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802 |
| 기존 B95 ZIP | 6613723aef35ea3929fd4110965014ceed5ba21ea04370622fc83a37d4f59acb |
| 이번 ADMIN 입력 ZIP | 1568db4b584335726be3a5d12a68bdef8f4c2aa2367fe5c5d03646cbddf41206 |
| 이번 입력 inventory | f85f24182a5c8851663b3f43de0dc6a6175781bccbe79db0294ea6e84f7bf88f |
| 이번 회수 evidence ZIP | ffa5b1802c211a875daa595cb0eb220e87457f3fc771fc36619d2838f65cda86 |
| 외부 정지 API raw | 5d22184757be8445d279dfc02f4f0bba2acb14889f309e44ee5a7ba29e135e0c |

전체 원본 위치는 evidence_location.json, 개별 해시는 actual_admin_result/raw_inventory.json이다. 일부 회수 원본은 mock 장애 시험의 TEST_ONLY 파일이며 실제 B95/A320 결과나 서명 권한으로 사용하지 않는다.

## 구현 전 검토가 실제로 잡은 결함과 Git

REVIEW_PRE_EXECUTION.md의 최초 UNRESOLVED와 각 입력 해시를 보존했다. 현재 승인 원문/참조 대조 누락, running 인계 후 supervisor 준비 실패시 STOP 책임 누락, fallback의 exited/running 거짓 정지 영수증, 새 승인 반례의 고정 만료시각 오류를 실행 전에 수정했다. 해당 반례는 이번48개 안에서 확인됐다. 읽기 비용 파생 작업의 응답형식/CLI 날짜 기본값 오류도 원본과 실패기록을 별도 보존했다. 실제 원격 시험 이후 코드는 수정하지 않았다.

실제 Git 변경 범위는 docs/active/bounded_admin_recovery_v0/target_52763685_admin_v1/ 새 버전과 그 결과뿐이다. 기존 봉인된 구현·검사 기준·물리/수치식·원본 실패·old input ZIP을 수정하지 않았다. historical administrative3, tablet gate1, B paid deadline1, local wrong filename1, Spain B prestart1, Spain ADMIN resource unavailable1을 유지했다. 별도 승인된 이번 ADMIN completed1만 추가한다.

구상 일치성: 잘못된 상태/승인/해시에서는 다음 계산을 막고, 불완전 STOP은 성공으로 승격하지 않는 실제 운송 경로와 반례를 연결했다. 이것이 이번 사용자 의도와 맞는 확인 범위다. 계산 정확성 오류의 자동 복구 권한은 추가하지 않았다.

**LOCAL FULL 생략 / 승인된 원격 ADMIN48개와 원본 해시 대조로 확인 / 로컬 프로젝트 동적 시험 금지 유지.** 기존 공식 기준선은 갱신하지 않았다. 새 물리 계산0/GPU 호출0/프로젝트·B95·A320 동적시험0/GitHub push0/master merge0. 사용자가 기존 작업까지 함께 종료되는 효과를 알고 서버 정지를 승인했으며, 기존 GPU 부하 관측은 이번 코드의 GPU 계산 호출이 아니다.
