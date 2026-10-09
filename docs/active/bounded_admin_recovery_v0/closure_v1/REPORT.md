# BOUNDED_ADMIN_RECOVERY_V0_DYNAMIC_VALIDATION_AND_PACKAGE_CLOSURE_V1

## 현재 판정과 먼저 공개하는 한계

**PACKAGE_CLOSURE_STATIC_READY / DYNAMIC_VALIDATION_PENDING / NOT_PRODUCTION**

패키지 A는 기존813개를 그대로 보존하고 지정된 기존 원본 봉인1개만 추가한 실제814개다. 정적 완전성 결과는 **COMPLETE_DECLARED_ONLY**다. 이는 조사하고 선언한 의존성에 대한 확인이다. 실제 Linux 실행, 모든 동적 파일 접근, 95개 정책 시험, 새320개 전체 시험, benchmark의 성공을 뜻하지 않는다.

**기존 REMOTE_TEST_GATE_FAILED / UNRESOLVED는 그대로 유지한다.** 이전 admin 운송 실패3회, 실제320개 중239pass/50failure/31error/skip0, 최초ZIP과 실패JUnit 및 FAILED 종료 영수증은 변경하지 않았다. 종료된 기존 시간창을 복구하거나 실패 횟수·예산을 초기화하지 않았다.

유료 서버 실행·재시작·임대·SSH·원격 전달은 이번 작업에서0회다. 로컬 프로젝트 동적 시험·물리 계산·GPU 호출도0회다. 로컬 stdlib로 ZIP을 만들고 바이트 해시·AST·정적 메타데이터를 확인했다. GitHub push와 master 병합은 하지 않았다.

## 구현됨

### 패키지 A: 경험 탭 원본 포장

새 경로 `package_A/tablet_814.zip`에 원본813개 경로와 raw 바이트를 유지했다. 추가는 아래 하나뿐이다.

`experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json`

원본 로컬 파일, 기준 Git 원본, 과거 성공 실행의 authorization_used.json이 고정한 code seal 해시를 대조했다. 이것은 출처 해시 확인이며 외부 독립 인증 판정은 아니다. 추가된 봉인이 참조하는683개 파일도 원래813에 포함되어 있다.

| 자료 | 실제 확인값 |
|---|---|
| 최초ZIP SHA-256 | `ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392` |
| 새A ZIP SHA-256 | `be06c9a7b8cc31c1e414b03f85485a9bb5e9e69226e34f1917553fac2673f4ff` |
| 새A inventory SHA-256 | `0bb1631ffb6adaaea69eb3c7b15b07a29b19429a8b98b2cfe9c7e5086b4d22b3` |
| 추가 봉인 raw SHA-256 | `ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60` |
| 기존 파일 | 813/813 동일, 변경·삭제0 |
| 추가 파일 | 정확히1개, 109,288바이트 |
| 새A 총 항목 / raw 크기 | 814개 / 48,642,482바이트 |
| ZIP 구조 | CRC 이상·중복·case alias·경로 탈출·symlink·암호화0 |

기존 경험 탭 code_seal 자체는 그대로다. 새 파일 집합은 별도 inventory로 결합했으며 새 계산 코드·권한 파일을 A 안에 넣지 않았다. `member_comparison.json`에 813개 전후 해시를 개별 보존했다.

### 실행 의존성 확인

기존 package_gate의 핵심 함수 본문은 AST 기준 동일하게 재사용했다. 새 별도 CLI에서 후보 inventory의 외부 SHA를 전달할 수 있도록 했다. planning.py는 변경하지 않았다.

선언된15개 실행 봉인과 원본 파일 참조를 출발점으로 과거 실측의 session/profile/manager roots/events/witness 및 raw 자료99개를 확인했다. signed receipt가 지정한 raw 참조74건의 해시를 대조했다. read_bytes/read/open/glob/copytree 등 파일 접근 표현194건을 AST에서 따로 기록했다. 운영체제 관측과 임시·동적 생성 경로는 동적 확인 대상으로 명시했다. 서명 자체를 새 방식으로 검증하거나 모든 실행 의존성을 발견했다고 판정하지 않았다.

새 계약의 명시적 필수 파일은115개, 실행 봉인은15개이며 완전성 검사에서 참조3,356건을 확인했다. missing/errors는 모두 빈 목록이고, 패키지 멤버814개 raw hash가 일치했다. 로컬 추출·프로젝트 import 없이 검사했다.

### 패키지 B: 원본95개 행정 정책 사례의 실행 준비

별도 최종 경로 `package_B_v3/admin_policy_95.zip`을 만들었다. 정확히10개 파일이며 raw 크기는48,965바이트다. 원래 정책 init/package_gate/planning/protocol/시험파일5개의 바이트는 변하지 않았다. 별도 admin_policy runner/guard/pytest 설정/하네스 규약/봉인을 포함했다. A에는 이 코드가 들어가지 않았다.

- B ZIP SHA: `6613723aef35ea3929fd4110965014ceed5ba21ea04370622fc83a37d4f59acb`
- B inventory SHA: `59632bab58b8df315794cd57708cdcea10aacc8f3bd91a6b08eb302639229619`
- B source seal SHA: `f6fa75dd65d9555d417352b98203eb3eb41202ad434296245b71c0da31ec1f47`
- B harness protocol SHA: `506dbcd747c5845dbdde92c1e27594ede7b97bcaa165d53ed4ed1f345d59b2ef`

시험파일의17개 함수를 AST로 세어 parametrize 전개 기대수95를 확인했다. 이 확인은 pytest 실행이 아니다.

runner는 새 명시적 인간 승인ticket과 기존guardian ARMED를 요구한다. Linux에서1CPU affinity, 프로세스별AS512MiB, CPU/wall120초, pytest95초timeout, 부모·자식 자원감시를 설정하고 실패 시 child process-group을 종료하도록 준비했다. pytest 환경주입을 제거하고 봉인 pytest.ini와 confcutdir를 명시한다. 실제 실행·종료·자원제어 동작은 아직 검증되지 않았다.

합성 결함95개는 누락·원본변조·ZIP구조·독립성 위장·금지 오류분류·사전승인·횟수·최초예산·회수정지여유·320개 전체결과 위장을 다룬다. 이 합성 receipt는 TEST_ONLY다. 기존 검토기는 적합 후보여도 execution_authorized=false이며 현장 복구 실행기를 추가하지 않았다.

### 새 별도 운송 버전

`transport/transport_seal.json` SHA는 `e40e3d59d7ee17685631b2a93d96e34d510bfe49779d98b8a1a42fcb6501e802`다.

기존 supervisor/probe/recover3개 파일을 raw 그대로 재사용했다. generic guardian의 Cli/confirm_stop AST도 그대로다. controller의 run/py/upload와 utc/canonical/sha/write/load를 재사용하며 argv 배열·SSH stdin·shlex 인자 처리를 보존했다.

새 연결에서 A814/B10의 ZIP·inventory·code·protocol·시험 수를 정확하게 결합한다. A는 과거 실패JUnit에서 고정한 고유320개 ID와 새 전체결과가 일치해야 한다. B는 새로운95개 실제 JUnit의 모두통과/실패error skip0 및 guard0, 회수 raw SHA, 실제 종료 결과가 있어야 한다. 이 B결과 원본을 별도 A승인에 외부 SHA로 결합하지 않으면 A를 거부한다. B를 통과해도 A가 자동 실행되지 않는다.

새창 승인에는 과거 admin실패3회·tablet gate1회와 두 기존 CLOSED 파일의 SHA가 포함된다. `approval_UNAPPROVED_A/B.json`은 explicit/newwindow/restart/exclusive 모두false이며 승인번호·시각은 비어 있다. 코드가 이 템플릿을 승인서로 생성하지 않는다. 서버 시작 전 이를 거부한다.

실제 PID1 식별값 누락·불일치, source raw hash 오류, guardian 불일치 또는 충분한 회수·정지 예약이 없으면 다음 시험을 시작하지 않는다. 중단은 FAILED/DEADLINE로 기록하고 정지 확인이 없으면 UNRESOLVED로 남긴다. 원본 회수는1회이며 시험 자동 재시도·현장 패키지 수정 경로는 없다. 정지 재요청은 기존 봉인된 종료 state machine의 제한된 정지 확인이며 시험 재실행 권한이 아니다.

## 시험됨

| 항목 | 이번 작업의 실제 관측 |
|---|---|
| A 포장·정적 완전성 | 814개 raw hash 및 구조 검사 완료 / COMPLETE_DECLARED_ONLY |
| 새 운송 정적 확인 | stdlib AST·cross-file prefix·pins·승인 전 순서 확인 완료 |
| 보존 검사 | protocol4 / preservation794 / code812 / 기존운송8 / 원본정책16 / admin실패34 / 실제실패89 파일 모두 해시 일치 |
| 95개 정책 실제시험 | NOT_EXECUTED / 공식 새PASS0, 실제 FAIL·error·skip 수 미관측 |
| 새320개 실제시험 | NOT_EXECUTED / 공식 새PASS0, 실제 FAIL·error·skip 수 미관측 |
| benchmark | NOT_EXECUTED / 측정값 없음 |
| supervisor·guardian 연동 / 종료 실증 | 이번새버전 NOT_EXECUTED |

기존 실제320의239/50/31/0은 과거 실패 결과로만 남긴다. 이번 공식 PASS에 합산하지 않는다. 초기 B초안2개와 운송 중간 봉인3개를 보존했다. 별도 검토에서 guardian 상대마감, pytest 설정주입, 감시시작 순서, probe 경로 불일치, TimeoutExpired 분류를 발견·보완했다. stdlib 정적 검사의 assertion 실패1건과 보조도구 오류도 `FAILURE_REVIEW.md`와 원본 기록에 남겼다.

**LOCAL FULL 생략 / 관련 동적 시험도 미실행 / 이유: 이번 사용자 지시가 로컬 프로젝트 동적 시험을 금지하고 실제 검증은 별도 승인 후 원격으로 지정했다.** 로컬 stdlib 정적 검사만 수행했으며 공식 회귀 기준선 숫자를 갱신하지 않는다.

## 독립 검증됨

이번 단계에서 새로운 외부 권한·서명 기반 독립 인증은0건이다. 별도 검토 에이전트가 ZIP raw/원본보존/운송연결을 읽기 전용으로 재확인하고 실제 정적 결함을 지적했다. 이는 별도 기술 검토이며 외부 권한·실제 서명 검증이나 운영 인증이 아니다. 검토 범위·결론은 `REVIEWER_CONFIRMATION.md`에 남긴다.

## 다음 승인 전 실행 계획과 비용

합산95+320+benchmark의 실제 소요시간은 미확인이다. B최악 계산예약120초와 A최악 계산예약120초의 합계240초를 한120초 창에 넣는다고 입증할 수 없다. **먼저 B창만 승인받고, 실제95통과·회수·정지 후 별도 A창을 승인받는 순서**로 준비했다. 이 제안은 두 창의 실행권한을 부여하지 않는다.

각 창 상한은 전체600초/시험wall120초/누적CPU120초/affinity1/AS512MiB/회수420초/종료확인180초/시간당.25달러/실행료.05달러다. 최초 시계는 각각 새로 승인된 재시작 전에 한 번 만들고 그 창 안에서는 초기화하지 않는다. 이전 닫힌창은 승인·예산 모두 그대로 닫힌 상태다.

두 새 창의 **합계 실행료 상한도.05달러**를 유지하는 보수적 관문을 추가했다. B의 실제 최초시계부터 최종회수·정지확인까지 elapsed×.25/3600을 비용상한으로 고정하고, A재시작 전에 여기에 A전체600초×.25/3600을 예약한다. 합계가.05를 넘으면 A를 거부한다. 따라서 B전체elapsed가120초를 넘으면 현재 A600초 예약 계획으로는 A실행 불가다. 더 싼 과거 가격을 이용해 이 관문을 통과시키지 않는다.

두600초 창을 최고단가로 전부 사용하면 합계1/12달러≈.083333달러이므로 .05달러 안이라고 주장할 수 없다. 이 경우 승인·계획을 다시 마련해야 하며 현장에서 제한을 변경하거나 새 창을 임의로 추가하지 않는다. 위 계산은 실행료의 보수적 예산 검사이지 전체 청구액 실측이나 회계 인증이 아니다.

대상 제안은 Vast54815136 / machine56006 / FR / ssh9.vast.ai:26992다. **현재 상태·단가·SSH·Python3.12·의존성·남아 있는 venv는 이번 단계에서 새로 확인하지 않았다.** 과거 가격과 런타임을 현재 보장값으로 쓰지 않았다. 새 실행 승인 전 읽기 전용 API로 ID/machine/국가/단가/정지상태/SSH정보를 확인한다. 정지 서버의 실제 Linux환경은 재시작 승인 후 guard를 먼저 확보하고 source/runtime 검증에서 재확인하며, 누락 시 설치·수정·재시험하지 않고 정지한다.

최초시계→supervisor READY→승인된 단일재시작→guardian ARMED→실제PID1→전달본검증→95 또는320/측정→회수·SHA→completion→외부정지영수증→final actual=exited/stopped 순서다. guardian 실제 상대마감과 절대400초 handoff를 함께 예약하고, controller 시험140초 및 회수96초 여유가 없으면 시작하지 않는다. 420초 회수/180초 종료 상한보다 앞선 예약이 거부를 유발할 수 있다.

A승인 후에는 새고유320개 모두통과·실패error skip0 이후에만 봉인된100/1,000/10,000건×31회 검색·CPU경로·선택증거 재검증·메모리·색인/capsule 크기 측정을 수행한다. 중앙값10ms는 목표이며 아직 결과가 없다. 다른CPU 실제속도개선·경험이전경제성·새물리/GPU 계산 실증으로 해석하지 않는다.

## 미확인·미구현과 구상 일치성

다른CPU 실제 성능, 경험 이전 경제성, 독립RwForce 수식검증, OS권한 격리, 모든 동적 의존성, 전체청구액, 운영서비스 연결은 미확인이다. 미래현장복구의 독립영수증 인증·외부회수/재시험 원장·실제 누적 집행·1회복구 실행기는 미구현이다. 계산 일반경로에 이러한 복구 정책을 붙이지 않았다.

구상과 맞는 부분은 기존 계산기·검사기·정책·실패를 유지하면서 누락된 원본만 포장하고 두 시험의 원본 결과를 분리해 받을 준비를 했다는 점이다. 한계는 정적으로 확인한 의존성만 충족한다는 점이다. 아직 충족하지 못한 핵심은 실제95/320/benchmark 및 새종료연동의 실증이다. 준비 완료를 프로젝트 시험 성공으로 표현하지 않는다.

## Git과 증거

기준브랜치는 `codex/adaptive-experience-tablet-cpu-route-v0`, 시작HEAD는 `352f9d1b09c24901a08adc6cf7d0af0a5f63fa5e`였고 작업트리는 깨끗했다. 변경전 범위봉인은 로컬 `0701d448`에 먼저 커밋했다. 최종 추가파일은 전부 `docs/active/bounded_admin_recovery_v0/closure_v1/` 내부다. 기존파일 수정·삭제와 다른브랜치 변경은 없다.

새 `.gitattributes`는 이 소유폴더의 raw바이트만 보호한다. 기존 root/document attributes를 변경하지 않았다. `closure_seal.json`은 최종 새산출물의 개별SHA와 이 보고서·검토서를 결합한다. `git_change_manifest.json`은 기준커밋 대비 실제 추가파일 목록을 보존한다. 최종 로컬 커밋ID와 커밋후 작업트리 상태는 완료응답에 실제조회값을 보고한다. 원격실행과 push/merge는 수행하지 않는다.
