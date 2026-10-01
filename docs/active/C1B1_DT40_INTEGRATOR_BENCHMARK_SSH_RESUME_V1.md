# dt40 비교 실험 — SSH 정보 제공 후 재개 기록

2026-10-01. 시작 HEAD·local origin/master·실제 원격 master `130df0d4cf419e349888fe0138d7d3cfc14b8b72`, clean, ahead/behind 0/0. 사용자가 제공한 네 SSH 주소로 원격 접근을 다시 확인했다. 기존 [중단 보고서](C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md)·봉인·실패 결과는 덮어쓰지 않았다. 이번 재개 기록과 파일 해시는 [별도 JSON](C1B1_DT40_INTEGRATOR_BENCHMARK_SSH_RESUME_V1.json)에 있다.

**SSH/배포 전송 경로는 확인했지만 수치 실험은 여전히 미실행이다. 최종 C: 아직 판정 불가.**

## 확인된 사실

- 9975WX의 새 proxy 주소 `ssh9:14051`은 정지 상태에서 연결 거부였다. 이후 올바른 SDK `retry=1`로 시작 요청을 보냈다. 9975WX와 265K는 각각 `success=false / resources_unavailable / state change queued`를 반환했다. 두 요청 모두 stop으로 대기 상태를 취소하고 exited/stopped를 확인했다. 이 응답은 이번 요청의 사실이며 앞선 응답 미보존 시도의 원인을 소급 확정하지 않는다.
- 5950X 시작 요청은 `success=true`, API의 actual/intended/cur 상태 모두 running이었다. 사용자가 제공한 `ssh4:13629` 경로로 SSH 명령의 exit 0을 받았지만 당시 stdout은 저장하지 않았다. 이어 기본 scp(SFTP) 전송이 `Connection closed`, exit 255로 실패했다. 성공적인 Python 실행을 이 첫 exit 0만으로 확정하지 않는다. 실패 처리에서 노드를 정지했다.
- 시작은 성공했으므로 전송 실패를 별도로 격리했다. 같은 5950X만 다시 시작해 API의 실제 `22/tcp` 매핑 `65.108.94.15:42811`로 접속했다. **원격 sentinel 314159와 Python 3.12.3 출력, exit 0**을 기록했다. `scp -O`로 동일한 64,353,518-byte bundle과 bootstrap 전송이 완료돼 원격 bootstrap이 실행됐다.
- 직접 경로와 전송 방식 모두 바꾸었으므로 proxy/SFTP 중 무엇이 앞선 전송 실패의 원인인지는 분리하지 못했다. [Vast 공식 SSH 문서](https://docs.vast.ai/guides/instances/connect/ssh)와 [OpenSSH scp 설명](https://man.openbsd.org/scp)을 확인했다. 후자는 기본 SFTP와 `-O`의 legacy SCP 선택을 설명한다.

## 새 중단 지점: 경로 복원 누락

원격 bootstrap은 source-manifest 검사에서 다음 오류로 exit 1이었다.

```text
FileNotFoundError: 'D:/reference/ar2_lang2024/S2_ar2_pot.f90'
```

로컬 archive를 직접 확인한 결과, Windows tar 생성 시 drive prefix가 제거돼 파일 이름은 `reference/ar2_lang2024/S2_ar2_pot.f90`였으며 manifest는 `D:/reference/...`를 요구했다. **원문 누락이나 PES hash 불일치가 아니라 배포 alias 복원 누락이다.**

archive의 실제 이름에 매핑해 내부 파일 272개 전부를 manifest SHA-256과 비교했으며 불일치 0이었다. 공개 원문 hash `a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049`, 원래 bundle hash `cb19888ccd6ff47d40a7fbddc8d646b706fea5687a969c7f1360957869e9307d`는 유지된다.

수정안은 원문 byte/hash를 먼저 확인한 다음 Linux에 정확한 `D:/reference/...` alias를 복원하는 것이다. `runs/c1b1_dt40_integrator_benchmark_20261001_resume/restore_reference_alias.py`와 이를 포함한 `remote_bootstrap_alias_v2.py`를 준비했다. Windows에서 D: 원본을 건드리지 않도록 Linux 전용 guard를 추가했고, 로컬 구문 검사·Windows 거부 guard·archive hash 대조는 통과했다. **수정안의 Linux 실행은 미시험**이며 이번 재개에서 추가 원격 실행은 하지 않았다. 기존 봉인된 수치 코드는 수정하지 않았다.

반복 실패를 보존하고 이번 재개를 중단했다. 결과 archive는 source 검사 전에 만들어지지 않았고, observer 출력 디렉터리도 생성 전이었다. 로컬 lifecycle·관측된 오류 전사·배포 제어 코드·alias 진단을 별도 보존했다. 원격 결과 파일을 회수했다고 보고하지 않는다.

## 노드·시간·비용

API 하드웨어 보고값: 9975WX effective vCPU 32/RAM 160318 MB/$0.26962963/hr, 265K effective vCPU 20/RAM 64007 MB/$0.16074074/hr, 5950X effective vCPU 32/RAM 64231 MB/$0.19111111/hr. 원격 lscpu/RAM/affinity 사전 기록 전에 실패했다. GPU 계산은 하지 않았다.

| 제어 시도 | 노드 | 시작→정지 확인 (KST, 2026-10-01) | 경과(s) | 결과 |
|---|---|---|---:|---|
| 시작 응답 확인 1 | 9975WX / 52764050 | 14:56:30→14:56:37 | 6.7301 | resources_unavailable |
| 시작 응답 확인 2 | 265K / 52731349 | 14:57:10→14:57:16 | 6.7475 | resources_unavailable |
| 시작·proxy 배포 | 5950X / 52763629 | 14:57:31→14:58:25 | 54.4014 | 시작 성공, scp 실패 |
| 전송 복구·사전 검사 | 동일 5950X | 15:00:38→15:02:44 | 126.1347 | 직접 SSH/전송 성공, alias 검사 실패 |

한 번에 한 노드만 실행했다. 각 시도 끝에 stop/정지 상태를 확인했고, 최종 read-only 확인에서 **기존 네 노드 모두 exited/stopped**였다. 미시도 3975WX를 시작하지 않았다.

승인 비용 상한 $1/hr·총 $1 유지. 제어 기간×API 가격의 참고 합계는 **$0.01038936**이다. 실제 running 청구 시간이나 invoice 금액이 아니며 전송비·기존 정지 저장 비용을 포함하지 않는다. 실제 청구액은 미확인이다. 이전 시도의 비용 참고값과 이번 값을 물리 계산 비용으로 합산하지 않는다.

## 수치·시험·현재 판정

Ar-Ar 궤적 0, kernel cost probe 0, 원격 관련 시험 0, 후보 40/60자리 수렴 0. 기존 KDK/continuous 결과는 재생성하지 않았다. [기존 필수 비교표](C1B1_DT40_INTEGRATOR_BENCHMARK_V1.md)는 그대로이며 두 후보의 χ/최접근/에너지/L/force count/CPU/wall은 여전히 미측정이다. 9-input panel/rho=-0.0001 미실행. 이전 14 passed는 앞선 로컬 대수 시험 결과이며 이번 새 시험으로 세지 않는다.

소스/원본 재확인: 봉인된 새·공유 소스 12, protected 134, O-1 원본 97, 원인 격리 원본 27 모두 hash 불일치 0. Linux alias 수정안만 Git 밖 배포 준비물로 추가했다. 현재 상태·문서 안내와 이 보고서만 Git 문서 변경이다.
**LOCAL FULL 생략 / 배포 준비물의 구문·guard 및 기존 원본 hash 대조로 확인 / 이유:** 물리·기존 실행 코드·공용 코드·동결 자산·계약 변경 없음, 공식 기준선 갱신 없음. 새 수치 검증 통과 주장은 없다.

Energy Bound v0 APPROVED, Liveness NotCertified, Safety Conditional, A-EV unresolved, Replay Verifier APPROVED, O-1 STOPPED / NOT PASSED, 원인 격리 TIME_DISCRETIZATION_SUPPORTED 유지. production 채택·새 물리·O-3·A-EV·native J 작업 미착수. commit/push 없음.

**C. 아직 판정 불가.** 다음 필요한 확인은 준비된 alias 복원을 Linux 사전 검사에서 검증하는 것이며, 그 뒤에만 봉인된 첫 입력 실험을 진행할 수 있다.
