# V12.2 조회 복구 연결 계획

첨부지시 SHA1b506d4a6732f0ed6a42ca49c415c7647b8c276bae84cc8b7a77bb8c27c25e83. 코드수정/검증준비권한이며새유료실행권한은아니다. V12/V12.1/실패원본/원래A320·검색을보존한다.

A 목적: 일시적인읽기실패를운영실패로즉시승격하는공백을관리driver뿐아니라실제A Transport.show와기존guardian CheckedCli에도연결한다. 새감시기관0.
B 가정: Provider가항상8/12초내응답한다는가정은실제8초Timeout원문으로깨졌다. 지연의공급자원인은UNCONFIRMED. 실제선행관리10/228 PASS·A0는기존stage_closeout6099raw를대조한다.
C 반례: 8초timeout뒤2초정상응답/3빠른통신실패/신원·JSON·가격변조/STOPPING변경/작성자RUNNING인데API실패/STOP응답유실/기한끝응답/initial감시생성전/final완료표식후. 최대3회지만caller의고정12초또는phase잔여를3배늘리지않는다. 실제각attempt최대8초이며모든응답에기존exact검사를한다. 상태변경명령은재조회helper를통과하지않는다.
D 호출·영향: driver Provider.call→sharedread; subclassTransport.show→원show(run/decode/inspect); control→원control에phasedeadline일시주입; execute초기/실행/최종/fallback별guard. 기존supervisor/guardian_driver실행입구만versionedbootstrap을경유하여CheckedCli.show를같은helper로연결하며stop/main/confirm_stop원문은불변이다. 소유·원문·최초시계·원예약·queuedSTOP·준비새회수·과거미완성probe삭제관문·두정산은V12.1재사용한다.
E 원인/누락: 기존시험은SSH/SCP유실과종료를다뤘지만실제Provider read timeout 복구연결을검사하지못했다. 원timeout증거는project_v12_a_20261009_181249/failure.json 및APIexception원문. V10 SSH종료원인과동일원인이라고주장하지않는다.
F 증거: 새관리모의시험+영향받는기존state/transport/STOP시험을새detached ADMIN_TESTS job에서실행해고유JUnit·전체closed원본회수. 이후실제SSHclient종료ADMIN_PROBE→RUNNING재관측→작성자완전종료/전체회수. 이두단계통과후원A320320/검색각31회원래600초관문1회. 정적AST/hash와원격동적통과를분리한다. 로컬import/pytest/collect등동적0.
G 미확인: 새후보동적NOT_TESTED,원Provider지연원인UNCONFIRMED,원동기소스추출중연결유실작성자UNKNOWN이면STOP·보존. 실제A는불변payload/검사기준을사용한다. 관리조회최대8초시도는최초12초caller안8+잔여4로복구할수있지만모든지연을해결한다는보장은없다.
H 권한/시간/비용: 원30분과미승인60분고정04:12:57창을자동연장하지않는다. 검토완료후새실제승인기록UTC·monotonic을한번만저장한30분종료창을요청한다. 원최초임대190077406000000/03:12:57.932772는계속기록하고새끝시각을그최초시계기준절대seconds로동일하게계산한다. 재시도·재개때now+1800재설정0. 기존grant만료는새실제승인·후보봉인·exact55069864/m37055·A미시작count에결합된명시적bridge만으로대체한다. 추가보수예약$.06후보/총$2/기존예약$.052382승계/새임대0/B재실행0/추가93=0. 시간과비용의실행승인은별도로필요하다.

최소 대안: 실제A Transport만연결하면guardian초기조회가같은공백이라같이연결한다. 보호된수치코드/시험/STOPstate machine을바꾸는대안은배제한다. 별도실제소스검토는필수이며권한인증·실제시험대체가아니다.

구현 연결: revision_v12_2/transport_reads.py(원A show/control와원CheckedCli show), process_bridge.py(원supervisor/guardian_driver진입만연결), read_retry.py(고정기한/예외선별), continue_owned.py(같은서버/원시계/순서), closure_bridge.py(부모·watch공유실패보존/원문검사/두예약), time_authority.py(새승인clock1회/원grant·카운터승계), guest_admin_runner.py(새24함수+기존6시험파일). 기존ADMIN228은재실행하지않으며영향시험만선별한다. 정적함수명목록62개는실제pytest항목수나PASS수가아니다.

검증 시간 예약: 승인기록창1800초 중 종료·정산220초를먼저제외한다. watchdog준비10/공급자확인과원문체크40/재개준비120/새setup100/이전probe회수24/새관리job90+회수96/단절job90+회수96/원A전체600/작은파일전달·mkdir110 = 합계1476초,종료포함1696초이며여유104초다. 실제준비시간을소모하면각단계control에서A600+마감여유를확인하고미달시거부한다. 기존600초에는원A전달·A320·검색·회수·STOP자체가포함되므로이중계산하지않는다. 현재실제각단계최대시간전체경로의보수적정적예산이며동적완료시간을측정했다는뜻이아니다.

실제readonly확인(2026-10-10 04:10:12.638222 KST): exact55069864/m37055 actualexited/intendedstopped,다른인스턴스0/볼륨0,장부43/원active$.052381944444/잔여$1.261141203704. 현재요금$.055111111111/h와storage_cost.4기준새30분보수견적$.052381944444(계산.027555555556/디스크.002222222222/up.001302083333/down.001302083333/불확실여유.02). 새예약상한.06이면전체active.112381944444<.20/차감후여유1.201141203704. 공급자display.360/13행보수관측.406이며기존장부spentbound.686476851852가더크다. 실제최종청구가아니며이번readonly는장부를변경하지않았다.
