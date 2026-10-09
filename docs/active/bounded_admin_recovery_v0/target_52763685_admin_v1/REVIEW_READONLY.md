# 새 NO 대상 읽기 전용 원본 및 미승인안 검토

검토자 `/root/state_contract_reviewer`. PLAN·readonly_preflight·proposed_budget_and_target·billing_baseline과 지정된 비공개 원본을 직접 읽었다. 새 네트워크/API/SSH·동적시험·start/stop·업로드는 수행하지 않았다. 이 파일만 작성했다. 별도 동료 검토이며 독립 서명 인증이 아니다.

## 실제 원본과 문서 대조

원본 폴더는 `C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\target_52763685_readonly_20261009_100644`다. readonly_preflight에 기재된10개 원본의 SHA를 각각 대조했으며 불일치0이다. API 공개 투영14개 필드는 raw instance.json과 일치한다. 인증 토큰과 원문 cmdline은 이 기록에 복사하지 않았다.

| 실제 관측 | 근거 SHA-256 |
|---|---|
| API id52763685/machine3448/geolocation=Norway,NO/actual=running/intended=running; 직접81.166.162.13:12408과22/tcp HostPort12408; API relay ssh2.vast.ai:13684 | instance.json `20bbb7155cf92ebec4a92da929b38c9dd16501d6a3adc3f476c9e12b3097cf4c` |
| PID1 CONTAINER_ID=52763685, /usr/bin/python3, Python3.12.3, pytest9.1.1/psutil7.2.2, affinity64; read_only=true/project_imports0/gpu_calls0 | ssh.stdout `060bf8798301b962690d0ed2aad87583725f3245d4e9c471e751d752a2cefc51` |
| Python7개 중 unknown_python6개와 stdin_readonly_probe1개 | process_labels.stdout `7946db9c952b7dfed88a8ded55f5e2d851c33032033f3ce2027ca9c55cd6fc00` |
| Provider billing metadata success=true/next_token=null/count=total=results길이6 | charges.json `a98e96ab102abb2766bacccac5bf2fa686dceae600a7b35e6ea0248cbaf587f3` |

따라서 문서의 '기존 python6개'는 probe 자기 자신을 제외한 자료와 일치한다. 그러나 unknown_python이라는 라벨과 GPU util99.999908%만으로 각 프로세스가 GPU 계산기인지, 누구 소유인지, 중단해도 되는지 확인할 수 없다. draft가 ownership/역할을 UNCONFIRMED로 표시한 것은 정확하다. 읽기 전용 probe 원문도 /proc·runtime metadata 읽기와 JSON 출력만 수행하며 물리/GPU/project import를 호출하지 않는다.

API relay13684와 화면13685의 차이는 API 원본으로 실제13684만 확인했다. 화면은 이 검토에서 다시 열지 않았으므로 화면13685는 전달된 사용자/구현자 문맥에 근거한다. 직접 연결을 검증한 증거와 relay 불일치 기록을 구분하고 일치값을 임의로 만들면 안 된다.

## 단가 관문과 승인 상태

실제 dph_total은 **0.2696296296296296**으로 기존 승인 cap0.25보다 높다. 현재 cap에서 새 실행은 **REFUSED**해야 한다. runtime/SSH/PID1 성공은 cap 변경 승인이나 독점 사용·STOP 권한이 아니다.

proposed_budget_and_target의 explicit_user_approval=false, exclusive_stop_authorized=false, B95_authorized=false/A320_authorized=false 및 UNAPPROVED_PROPOSAL_ONLY는 현재 결정을 정확히 반영한다. 구현자 설명상 사용자에게 cap0.28 예외와 독점 완료/실패 STOP 결정을 요청했고 아직 답이 없다. 이 동료 검토가 그 결정을 대체하지 않는다.

서버가 이미 running이므로 기존 stopped-only initial/start를 그대로 사용하면 거부 또는 불필요한 재시작이 발생할 수 있다. adopt-existing-running 연결은 아직 미구현/미검증이다. 명시적 독점 인수, 최초 시계, 종료 책임, 기존 workload 중단 효과를 확정한 별도 ADMIN 승인과 연결이 필요하다. 현재 읽기 자료는 start/stop/실험/업로드가 있었다는 증거가 아니며, 이번 검토도 추가 행동을 하지 않았다.

## 과거 guardian0.28 예외의 적용 금지

`experiments/adaptive_execution_real_learning_pilot_v0/offline_budget_amendment_52763685.json` SHA는 `daa8ec8f9b73deb3f5d212841372725aac522cc1154eb385766b7744d4a54173`이다. 실제 파일은 2026-10-08의 REAL_LEARNING_PILOT offline 별도 gate·scope, 시간당0.28·총0.10·전체600초·guardian deadline240초를 명시한다. 이번 ADMIN gate의 승인이나 독점 STOP 결정으로 자동 재사용할 수 없다.

기존 guardian의 hourly_cap은 이 과거 파일·hash·scope·target·deadline을 검사한다. 새 ADMIN의 시험120초·회수/종료 여유·원래600초를 묶는 새 예외안은 별도 승인·byte binding·검토가 필요하다. 과거 코드/승인서를 덮어쓰거나 cap 검사를 무조건 통과시키는 방식은 허용되지 않는다.

## 원장과 비용 임시 계산

charges raw의 source=instance-52763685 행은 amount0.054이고 구성은 gpu0.024/disk0.030/다운로드0/업로드0이다. billing_baseline의 값을 실제 행과 대조해 일치함을 확인했다. 이는 이미 running인 서버의 일별 누적/반올림 자료이고 새 ADMIN 시험은 실행0이므로 이번 시험 비용으로 기재하면 안 된다. 기존 workload 비용의 실소유 및 현재 캠페인 회계 포함 경계도 별도로 명시해야 한다.

previous ledger 실제 SHA는 `c4fb17ecd5f9af6faa382a18a4f9ef0f8b538a3ec1d8621d6ca770b905185b4c`로 proposal의 핀과 같고 conservative_spent_bound_usd는0.04491355611111111111111111111이다. cap0.28*600/3600의 제안 window 최대0.04666666666666666666666666667과 합계0.09158022277777777777777777778은 보존 값과의 산술상 일치다.

이 합계는 **미승인 예외안의 임시 예약 계산**이다. 최신 새 대상의 기존 runtime·읽기 전용 준비 시간·실제 청구 및 캠페인 귀속을 다시 대조하지 않고 실행 가능한 잔여 예산으로 확정할 수 없다. 다음 B/A 두 window까지 충분하다는 근거도 아니며 각 stage는 별도 승인/최신 원장 검토가 필요하다. 과거 ADMIN/B/tablet/filename 실패와 비용 보존 값은 초기화하지 않는다.

## 분류와 결론

| 구분 | 확인 범위 |
|---|---|
| 구현됨 | 새 대상 읽기 투영·draft PLAN·미승인 cap/target proposal·billing baseline |
| 시험됨 | 이전 수행자가 남긴 실제 읽기 SSH/PID1/runtime/API 원본 존재. 동적 ADMIN 시험0 |
| 독립 검증됨 | 독립 서명 인증0. 동료 검토의 raw hash10개/투영14개/청구 행/이전 ledger 대조 |
| 실패·반례 | 기존 cap 초과, proxy 화면/API 차이, stopped-only mode 불일치, 미확인 기존 workload 중단 위험 |
| 비용·성능 | 관측 단가0.2696296296296296, 일별 baseline0.054, cap0.28 임시예약 산술; 새 시험 실청구 미확인 |
| 미확인 | cap/독점STOP 승인, 새 adopt mode·guardian 예외·동적45개·회수/실제종료·workload 소유 |
| 다음 행동 | 명시적 cap 및 독점STOP 결정 전 유료 행정 실행 보류 |

현재 상태는 **읽기 전용 대상 확인 완료 / 기존 cap에서 REFUSED / 새 예외·독점 종료 권한 미승인 / ADMIN 동작 UNRESOLVED**다. 승인false인 proposal을 READY 봉인·실제 실행 승인·B95/A320 통과로 사용할 수 없다.
