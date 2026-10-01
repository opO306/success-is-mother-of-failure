# KDK20 vs Yoshida40 동일 노드 전체 비용 — C / INCONCLUSIVE

2026-10-01. **원격 패키지 업로드 중 SCP 연결이 끊겨 성능 비교는 실행되지 않았다.** 두 방법의 비용 우열은 미측정이다. 이 결과로 기존 수치 정확도 결과나 production 선택을 변경하지 않는다.

작업 전 실제 HEAD / origin/master / remote master는 모두 `63e5b953c643e4da6cb26a4dd32aabbcaecc5703`, clean, ahead/behind 0/0이었다. 최근 관련 commit은 63e5b95(portable 결과), 130df0d(최초 inconclusive), 508bba4(원인 격리)다. 종료 HEAD 동일, 독립 benchmark/배포 도구/시험/문서 추가로 dirty, commit/push 없음.

[사전 프로토콜](C1B1_KDK20_YOSHIDA40_COST_PROTOCOL_V1.md), [실행 봉인 V3](C1B1_KDK20_YOSHIDA40_COST_SEAL_V3.json), [로컬 사전 검사](C1B1_KDK20_YOSHIDA40_COST_PREFLIGHT_V3.json), [실패·Git·환경·원본 해시 기록](C1B1_KDK20_YOSHIDA40_COST_RESULTS_V1.json).

## 준비된 비교 구조와 미검증 범위

별도 `c1b1_cost_benchmark.py`가 기존 KDK20 step과 Yoshida40 advance를 동일 observer/loop 안에서 호출한다. 공용 물리/production/기존 수치 source는 수정하지 않았다. 같은 60자리·Lang Field·질량/단위·raw·출구 조건·관측 정책·JSONL/gzip 저장 정책을 사용하고, single CPU affinity worker 하나씩 순차 실행하도록 했다. Warm-up 각 1회 → K/Y/Y/K/K/Y 각 3회 → 원래 9-input 순서에서 방법 순서를 번갈아 1회씩. 총 계획 26회다.

초기 모델 준비·force·integrator·내부 chord guard·outer 관측·각 상태 기록·압축 close·trace hash·endpoint 보정·필수 수치 summary 첫 write까지 timer에 포함한다. import/봉인 hash 확인·worker 시작·최종 타이밍 metadata rewrite·제어 progress 파일은 제외한다. 이 저장 정책과 CPU/wall 구분은 양쪽 동일하다. 실제 production/replay 비용 비교는 아니다.

로컬에서는 Ar-Ar trajectory 0회다. 자유 운동의 한 step 단위 시험으로 두 방법의 갱신/힘 계측/저장 정책을 확인했으며, Windows에서는 Linux OS telemetry 경계만 시험 shim으로 공급했다. 이는 원격 Ar-Ar 전체 loop 실행 검증을 대신하지 않는다. 이번 하네스의 실제 Ar-Ar 실행은 아직 미검증이다.

## 로컬 사전 검사

첫 복원에서는 새 packaging 모듈의 기존 helper 의존성이 빠져 59 passed / 1 failed였다. 두 번째는 해당 역사 helper를 넣자 그 안의 Windows 경로 literal이 기존 active-code guard에 걸렸다. 둘 다 서버 시작 전 실패다. 실패 package/복원 로그 및 봉인 V1/V2는 보존했다. 수치 계수·관측 허용오차를 바꾼 수정이 아니다. 최종 packaging extension helper는 표준 라이브러리만 사용한다.

세 번째 package: 원본 **272/272**, 객체 **286/286** 해시 일치. 기존 portable 원본 객체를 덮어쓰지 않고 새 benchmark/시험/프로토콜/실행 봉인만 추가했다. package SHA `82e41c01d15b01c0d22ca0d638b96bfdfa143984d74743928f2e55ab25a2cf3c`. 공개 Lang 원문 SHA `a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049`. 새 폴더 복원 뒤 sealed input 9개/60자리 load와 관련 시험 **60 passed, 2.51초**, failure/error/skip 0. 시험 후 inventory도 다시 일치했다.

최종 로컬 관련 시험 **68 passed, 24.42초**, failure/error/skip 0. 신선한 실행이며 nested 동일 시험을 새로운 고유 시험으로 합산하지 않는다. 기존 수치 source 12개·protected source 134개·O-1 artifact 97개·원인 격리 artifact 27개 현재 hash 불변을 확인했다.

## Vast 실행과 실패

- AMD Ryzen 9 5950X 16-Core Processor, API effective vCPU 32, RAM 64,231 MB.
- 기존 인스턴스 52763629 한 대, GPU 계산 없음, API 가격 $0.191111111/hr.
- 시작 요청 `2026-10-01T07:34:14Z`, 최종 stop 확인 `2026-10-01T07:36:57Z`.
- 제어 구간 163.375초. 가격×구간 참고값 **$0.00867299**. 실제 청구액/정확한 running interval은 확인하지 않았고 저장·전송 요금은 제외한다. 전부 운영 구간이며 integrator runtime이 아니다.
- start 성공 및 실제 running, 직접 SSH Python 3.12.3/sentinel 확인 후 SCP 업로드를 시작했다.
- SCP가 `remote host closed connection`, `Broken pipe`, `lost connection`과 exit 1로 실패했다. timeout 예외가 아니다. 네트워크/SSH daemon/노드 가용성 중 어느 것이 원인인지는 확인하지 못했다.
- bootstrap 전송·원격 hash·원격 시험·warm-up·측정·panel 모두 미실행. 원격 수치 결과는 없어 회수했다고 주장하지 않는다. 로컬 package·preflight·lifecycle·SCP 실패 증거는 hash와 함께 보존했다.
- 자동 stop exit 0 및 `exited/stopped` 직접 확인. 이후 기존 네 인스턴스 모두 exited/stopped를 재확인했다.

첨부 사용자 지시 12절은 infrastructure 오류를 `C / INCONCLUSIVE`로 STOP하고 추가 서버 실험을 시작하지 말라고 명시한다. 따라서 유료 재시작이나 다른 노드 시도는 하지 않았다. 실패 원인 조사/전송 경로 개선 및 실제 비교 재개는 이후 설계자 결정 대상이다.

## Single-input benchmark

| method | measured runs | median CPU | median wall | force eval | χ error |
|---|---:|---:|---:|---:|---:|
| KDK20 | 0 | N/A | N/A | N/A | 미측정 |
| Yoshida40 | 0 | N/A | N/A | N/A | 미측정 |

warm-up도 0회다. 이전 로컬 KDK20이나 이전 Vast Yoshida 시간을 이번 성능 결과에 대입하지 않았다.

## 9-input aggregate

| method | total CPU | total wall | force eval | accuracy | verdict |
|---|---:|---:|---:|---|---|
| KDK20 | N/A | N/A | N/A | 이번 미실행 | C |
| Yoshida40 | N/A | N/A | N/A | 이전 9/9 보존, 이번 미실행 | C |

total outer steps / additional derivative eval / output bytes / peak memory도 이번 성능 실행은 모두 N/A다. 새로운 실제 force/derivative 횟수나 시간 값을 추정해 채우지 않았다.

**최종: C. INCONCLUSIVE.** 동일 노드 전체 비용 비교는 완료하지 못했다. 기존 9/9 Yoshida 정확도·kernel 비용 기록은 유효한 원본으로 보존하며 이번 전체 비용 증거로 바꾸지 않는다.

## 한계와 상태

Yoshida의 negative internal stage는 r_min boundary/hard domain/many-body/chemical interactions에서 별도 위험이다. 이번 준비나 이전 2-body 관측 통과로 A 전체 production 안전성을 인증하지 않는다. 새 candidate/Chin/최적화/계수 tuning/adaptive dt/production substep/계약 변경은 없었다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 사용자 14절에 따라 독립 benchmark·배포 도구·시험·문서만 추가했고 기존 production/common/frozen source 및 fixture는 불변이다. 사용자 로컬을 다른 작업에 사용하므로 불필요한 FULL을 실행하지 않았다. 공식 기준선 갱신 없음.

Energy Bound APPROVED / Liveness NotCertified / Safety Conditional / A-EV unresolved / Production Replay Verifier APPROVED / O-1 STOPPED·NOT PASSED / TIME_DISCRETIZATION_SUPPORTED numerical diagnostic 유지. O-3·A-EV·native J·새 물리·상태 snap·에너지/운동량 보정 미착수. 이번 C는 인프라 실패이며 두 적분기의 물리/정확도 실패 판정이 아니다.
