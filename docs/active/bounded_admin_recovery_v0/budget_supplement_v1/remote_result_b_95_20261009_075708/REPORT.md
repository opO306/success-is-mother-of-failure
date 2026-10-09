# B 정책95 시험: 재시작 관문 DEADLINE 결과

**B_REMOTE_START_GATE_DEADLINE / B_95_NOT_EXECUTED / UNRESOLVED / NOT_PRODUCTION**

승인된 Vast54815136/machine56006/프랑스의 재시작 요청1회를 수행했지만, 봉인된45초 대기 안에 실제running 상태를 관측하지 못해 중단했다. 공급자의 재시작 원문은 `Required resources are currently unavailable, state change queued.`였다. 종료코드0은 실제 재시작 성공을 뜻하지 않았다. 이 메시지는 자원 부족으로 요청이 대기 중이라는 관측이며, 공급자의 내부 자원·큐 원인은 더 조사하지 않았다.

**B95개 시험은 시작되지 않았다.** 게스트 식별·SSH·패키지 전달·JUnit·정책fixture 실행은0회다. 시험 PASS/FAIL/error/skip 값은 미관측이며, 95개가 skip되거나 실패한 것으로 세지 않는다. A320·benchmark도 미실행이다. 새물리/GPU 호출0, 로컬 프로젝트 동적시험0, 시험자동재시도0, 현장코드수정0이다.

## 실제 시간·종료·비용

| 항목 | 관측 |
|---|---|
| 최초할당시계 | 2026-10-09 07:59:43.744168 UTC / KST16:59:43.744168 |
| supervisor READY | 07:59:43.885395 UTC, 재시작 요청 전 |
| 재시작 요청 종료코드 | 0, 원문은 자원부족·대기열 |
| 최초 실패 | 08:00:32.512577 UTC, BOUNDED_RESTART_NOT_RUNNING |
| controller 최종 상태 | DEADLINE / stop_status=STOP_CONFIRMED |
| 최초시계부터 최종확인 | 56.310073초 / 상한600초 |
| 외부 정지영수증 | supervisor fallback의 STOP_CONFIRMED, intended=stopped·actual=exited |
| fallback 정지 확인 | 요청1회, 해당 확인시계4.89초. controller DEADLINE에 대해 기존fallback은 trigger=FAILED로 기록 |
| 최종 controller API | 08:00:40경 actual=exited, intended=stopped |
| 추가 읽기전용 확인 | 08:06:17.956327 UTC 이후 조회에서도 actual=exited, intended=stopped |
| guardian | actualrunning 관문 미충족으로 시작·ARMED 미실행 |
| 관측 시간당단가 | $0.13462222222222225 |
| 해당 단가×56.310073초 | $0.0021057186557654325… **계산 추정**, 실제청구 아님 |
| 승인 최고단가.25×동일시간 | $0.003910421736111111… **보수적 계산 상한**, 실제청구 아님 |
| 실제 공급자 실행료 | **미확인**, $0으로 판정하지 않음 |

guardian/supervisor 전체 연동을 검증했다고 말할 수 없다. supervisor READY와 fallback 정지 요청·실제 종료 확인 경로는 이번 실행에서 관측됐다. guardian ARMED와 게스트시험·회수 경로는 미실행이다. 게스트 원본이 생성되지 않았으므로 원격 시험 결과 회수·recovery_verified는 false이며, 확보된 제어·승인·API 원본만 보존했다.

## 비용 조회와 부가 오류 기록

종료 후 읽기전용 `show invoices`를 당시 실행시각·인스턴스label로 조회했다. stdout은 비었고 stderr에는 deprecated 안내와 HTTP400 `contract_ids must be a non-empty list`가 남았다. CLI 종료코드0이었지만 비용 조회 성공으로 세지 않았다. 실제비용 확인receipt를 만들거나 비용0/VERIFIED 값을 넣지 않았다.

그 뒤 `show charges --help`라는 설치되지 않은 명령을 사용해 로컬CLI 인자 오류가1건 났다. API·유료호출은 없었다. 이 조회 오류도 result_summary에 보존하고 청구 조회를 더 고치거나 반복하지 않았다. 올바른 신규CLI·계약ID 방식에 대한 후속 읽기전용 준비는 별도 과제로 남긴다.

재시작stdout을 PowerShell ConvertFrom-Json으로 읽으려 한 진단에서도 plain text의 첫글자R 때문에 파싱오류1건이 났다. 텍스트 원문을 확인했고 서버·시험은 재시도하지 않았다. 이러한 기록은 프로젝트 기능시험의 failure/error 수로 혼합하지 않는다.

## 최초 로컬 실행 명령 오류와 승인 경위

사용자의 B95개 유료시험 승인 후 승인서는 b_95_20261009_075708.json으로 생성됐다. 제가 실행 명령에는 존재하지 않는075651 파일명을 직접 입력하여 FileNotFoundError가 났다. 원인은 출력된 실제경로를 그대로 사용하지 않은 제 행정 오류다. controller의API·supervisor·유료재시작 전에 발생했고, 사용자의 실패시중단·자동재시도금지에 따라 중단·정지상태 확인·실패기록 보존을 했다.

사용자가 이후 **“정확한 승인서 경로로 B 첫 원격 실행 진행”**을 명시적으로 승인했다. 두번째 로컬진입에서는 실패기록의 실제경로·원본SHA를 확인한 뒤 승인서와 봉인코드를 변경하지 않고 전달했다. 실제 유료재시작 요청은 이 명시적 승인 뒤1회뿐이다. 최초 로컬오류의 tool-rendered traceback은 대화 tool transcript f328c0와 별도failure.json에 참조로 보존했으며, 당시 raw stderr 파일을 확보했다고 주장하지 않는다.

과거admin실패3회와 이전실제tablet gate1회의 실패원본은 그대로다. 이번에 새로 로컬명령실패1건과 승인된B 유료재시작관문DEADLINE1건을 추가 기록했다. 기존숫자·최초ZIP·이전320JUnit·CLOSED 증거를 수정하거나 예산·시계를 초기화하지 않았다.

## 원본·해시·권한 보존

- B ZIP: `6613723aef35ea3929fd4110965014ceed5ba21ea04370622fc83a37d4f59acb`
- B inventory: `59632bab58b8df315794cd57708cdcea10aacc8f3bd91a6b08eb302639229619`
- B code seal: `f6fa75dd65d9555d417352b98203eb3eb41202ad434296245b71c0da31ec1f47`
- B protocol: `506dbcd747c5845dbdde92c1e27594ede7b97bcaa165d53ed4ed1f345d59b2ef`
- 실행 운송seal: `ea3acc4ddf5e3a34fb53d204059a603040ef1f51bc33fc7446ef5442f870e4b8`
- B 승인서: `a9c75353858cb8c97446e9c0812fc5d9a1a6991b9ebb325e9d298a5a15552759`

실행전 source_preflight에서 기존 봉인·새 B 멤버·ZIP/inventory raw SHA를 확인했다. 기존규약·운송·패키지 파일은 실행 중 수정하지 않았다.

raw_evidence_manifest는58개 확보원본의 개별SHA와 보존경로를 기록한다. external_final_confirmation은 추가2개API raw의 개별SHA를 기록한다. 원본 사본60개의 바이트가 일치한다. 원본 위치는 `C:/Users/zun24/.codex/evidence/bounded_admin_recovery_v0/b_95_20261009_075708`이며, 원래 실행폴더에도 그대로 남았다.

API 원본에 접근정보가 포함되어 새 runtime 폴더를 이 버전의 새.gitignore로 Git에서 제외했다. 원본을 삭제·수정하거나 redacted 자료를 원본이라고 표시하지 않았다. Git에는 개별SHA/원본경로와 접근정보를 제외한 **파생요약**만 보존한다. 비밀값 없는 supervisor/closure/source_preflight 등의 원문은 그대로 복사해 결합했다.

## 구분과 다음 경계

**구현됨:** 기존봉인 운송을 그대로 사용했고, 이번 관측의 실패·종료·해시·비용미확인 기록을 추가했다.

**시험됨:** 실제 재시작요청1회,45초관문DEADLINE, supervisor READY·fallback 정지·실제exited/stopped 관측. B95/A320/benchmark는 미실행이다.

**독립 검증됨:** 새 외부서명·독립권한 인증0건. 공급자API원본과 외부supervisor 영수증은 출처별 관측으로 보고하며 독립인증으로 격상하지 않는다.

**미확인:** 실제B청구액·전체청구액, 서버 자원부족의 내부원인, Linux런타임, guardian 실제ARMED·시험/회수, 정책95 및 CPU/경험탭 기능·성능. 실제 running이 없었으므로 게스트 CPU·메모리 시험측정값도 없다.

이번B관문은 실패했으며 A승인요건을 충족하지 않는다. A 실행·다른서버 임대·재시작·자동재시험·현장수정은 하지 않았다. 실패해도 시간상한을 늘리거나 원본을 고치지 않았다. 후속 실행은 실패원인·실제비용 확인과 새로운 명시적 지시·승인이 필요하다. GitHub push·master병합·LOCAL FULL은 수행하지 않았다.
