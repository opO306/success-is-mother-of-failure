# 경험 탭 V0 — 승인 전 원격 실행 제안

이 문서는 실행 승인서가 아니다. 로컬 import/pytest/bench 실행은 금지한다. 서버 대상은 아직 선정하지 않았다. 새 승인 전 임대·재시작·원격 실행은 0회다.

제안된 관문은 Linux, Python 3.12와 mpmath 1.3.0/python, cryptography/psutil/pytest다. 실제 버전은 첫 환경 기록에 남긴다. CPU affinity 1개, wall/누적 CPU 각각 120초, AS/프로세스 트리 RSS 512MiB, 새 물리/GPU 0. 기존 254개와 신규 66개의 소스상 예상 항목을 같은 전달 트리에서 실행한다. 실제 JUnit 총수와 실패/error/skip 0을 요구한다. 예상 숫자를 PASS로 쓰지 않는다.

전체 할당 600초, 원본 회수 마감 420초, 정지 확인 180초. 시간당 $0.25/총 $0.05 이하. 사용자가 승인한 실제 instance/machine/country와 조회 당시 단가를 고정한다. 임대·재시작 전부터 allocation_start_utc를 기록하며 재시도 때 초기화하지 않는다. 기존 guardian.py를 외부 컴퓨터에서 재사용한다. STOP_CONTROL_ONLY, exclusive=true, explicit_user_approval=true, 새 승인 원문 참조, 실제 인스턴스, guardian raw hash, 완료 marker, machine/country를 lease에 고정한다. REAL A용 safety_policy_sha256 필드는 사용하지 않는다.

guardian의 deadline은 ARMED부터 계산하므로 `floor(420 - 재시작 전 시계부터 ARMED까지 경과초)` 이하로 좁힌다. allocation 기준 420초 전에 정지 절차를 시작하고 남은 180초 안에 actual exited/stopped를 확인하도록 한다. 게스트 authorize는 이 관계를 다시 확인한다. 외부 guardian은 running·요금·machine/country를 재조회하고 제어 오류 때 FAILED 정지를 시도한다. 이 단계에서는 기존 generic guardian의 동작을 재사용한다. REAL A 모드의 heartbeat 연속성 규약으로 승격하지 않는다.

소스 ZIP은 Git checkout 재작성 대신 원문 바이트 그대로 해제한다. package manifest와 code_seal.json의 모든 파일 SHA256, 이전 code seal 683개 및 보호 794개를 확인한다. 개인 서명키는 패키지/탭에 넣지 않는다. 공개 roots는 기존 실제 A 자료의 provision된 roots이며 synthetic 자료나 capsule 자체의 키로 바꾸지 않는다.

외부 guardian ARMED 뒤 새 OFFLINE_ONLY ticket을 만든다. gate=ADAPTIVE_EXPERIENCE_TABLET_CPU_ROUTE_V0, explicit_user_approval=true, approval_reference, instance/machine/country, code_sha256, protocol_sha256, physics_calls=0, gpu_calls=0, armed_sha256(기존 canonical digest), allocation_start_utc, allocation_seconds=600을 고정한다. 코드 지문/소스 패키지/실제 서버/요금 변경 시 이전 승인을 재사용하지 않는다.

게스트에서 실행할 단일 진입점은 다음과 같다. `<...>`는 승인 후 확정할 실제 경로이며 아직 실행하지 않았다.

```sh
python -B -m experiments.adaptive_experience_tablet_v0.offline --authorization <fresh-ticket.json> --armed <armed.json> --out <new-exclusive-output>
```

pytest guard는 기존 실제 계산 및 GPU 진입점을 차단한다. 로그·JUnit·guard report·benchmark·상태·탭 참조·원본 SHA256 목록을 새 출력에 보존한다. source gate와 test gate가 모두 통과한 뒤에만 합성 100/1000/10000건 검색/경로 생성과 선택 원본 재판독 비용을 측정한다. 31회 중앙값/최대 wall, process CPU, Python traced peak, 색인/참조 크기를 분리한다. 합성 search 수치는 실제 물리 요청 성능과 교육비 절감의 증거가 아니다. 10ms 목표 미달이면 구조 시험과 비용 목표 판정을 따로 보고한다.

완료 원본을 로컬로 회수하고 개별 raw 해시와 ZIP 해시를 확인한 뒤 외부 marker에 COMPLETED를 기록한다. 실패·skip·error·비용 한도·원본 결합 실패는 FAILED이며 다음 계산/활성화 0회다. 외부 마감은 DEADLINE이다. marker는 외부 guardian이 보는 경로에 직접 전달하며 게스트 종료만을 서버 정지로 간주하지 않는다. guardian final의 STOP_CONFIRMED와 새 API actual exited를 각각 보존한다. STOP_UNCONFIRMED는 성공 판정이 아니며 수동 정확 인스턴스 확인이 필요하다. 3회 실패 중단과 단일 전체 예산을 유지한다.

이 준비에는 실제 서버 선정/운송 controller lease 생성이 포함되지 않는다. 승인 단계에서 인스턴스와 잔여 임대 상태, 경로, 예산 및 종료 운송 코드를 구체화해야 한다. guardian와 guest는 같은 UID에서 운영될 수 있으며 OS 권한 격리를 제공하지 않는다. source 준비는 독립 검증이나 공식 통합 회귀 완료가 아니다.
