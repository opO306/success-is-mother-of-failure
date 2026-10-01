# KDK20 vs Yoshida40: 동일 노드 전체 비용 사전 프로토콜

시작 HEAD/actual remote master `63e5b953c643e4da6cb26a4dd32aabbcaecc5703`, clean, ahead/behind 0/0. 사용자 첨부 지시대로 기존 방법 둘만 비교한다. 같은 Hamiltonian/raw/PES/mass/units, 고정 precision 60, 출구는 기존 9-input 봉인의 각 base_radius 이상인 첫 outbound outer state다. 같은 실제 출구 반경까지 이전 연속 reference의 짧은 구간만 보정한다.

기존 KDK20 step, Yoshida coefficients/advance, analytic Lang Field/PES는 byte 불변이다. 새 파일은 성능/공통 관측 하네스·배포 도구·시험·문서뿐이다. production/common/frozen source 수정 및 force 최적화 없다. O-1 STOP과 다른 Gate 상태는 유지한다.

각 run은 새 worker 1개, 같은 CPU affinity 한 슬롯에서 **순차 실행**한다. BLAS/OMP threads 1, GPU 비사용. Python/mpmath 같은 환경, 60자리, 초기 raw와 출구 조건 동일. 초기 모델 준비와 force, integrator/guard, 모든 outer 상태의 에너지/L/최접근/회전 관측, JSONL 기록, gzip level 9/mtime 0/filename 빈 값, trace SHA, endpoint 보정, 필수 수치 summary 첫 write까지 CPU/wall timer에 포함한다. 같은 저장 정책이지만 KDK20의 step 수가 더 많아 출력 수는 더 많을 수 있다.

source/input/seal hash 검사·worker 시작/affinity 설정·Python import는 timer 밖이다. 시작 시간 기록 자체를 담는 최종 metadata rewrite와 제어용 progress/summary는 timer 밖이며 양쪽 동일하다. gzip file close 포함, fsync는 양쪽 모두 사용하지 않는다. 따라서 OS buffered-file 정책의 실제 사용자 실행 비용이며 durable-storage latency benchmark는 아니다. output bytes는 gzip trace와 최종 수치 summary 합이다. endpoint CPU/PES 횟수는 별도로도 기록하되 전체 timer에서 제외하지 않는다. fresh worker의 ru_maxrss로 run peak를 기록한다.

warm-up: boundary_pass KDK20 1회, Yoshida40 1회. 공식 median에서 제외하되 결과·비용·출력 보존. 측정 순서: KDK, Yoshida, Yoshida, KDK, KDK, Yoshida. 각 3회 median CPU/wall, min/max/변동 기록. CPU 또는 wall max/min >1.2면 C INCONCLUSIVE STOP. 이 기준은 이전 cost study와 동일하며 실행 전 고정한다.

1차 wall ratio <0.90 FASTER, 0.90~1.10 SIMILAR, >1.10 SLOWER. 어느 경우든 수치/환경/변동 문제가 없으면 사용자 지시대로 9-input panel을 입력당 방법별 1회 실행한다. 원래 봉인 순서 유지, 홀수 입력 KDK→Yoshida / 짝수 입력 Yoshida→KDK. boundary_pass도 panel에서 1회씩 실행하여 동일 집계 정책을 유지한다. 총 26회 = warm-up 2 + single 6 + panel 18. Chin/rho=-0.0001/새 입력은 실행하지 않는다.

수치 기준: 기존 |Δχ|/방향 <=1e-5 rad, 상대 Rmin 오차 <=1e-5, max |ΔH|/De <=1e-3, max |ΔL| <=1e-20, 모든 내부 drift chord r>=2.4. 방법의 실제 drift를 같은 chord observer로 관측한다(KDK 1, Yoshida 3). outer chord도 같은 정책으로 추가 기록한다. 이전 Yoshida60 각 입력의 χ/방향/Rmin/출구 반경/에너지 변동 절대 차이 <=1e-20 및 step 수 일치; boundary KDK20도 이전 60자리 결과와 같은 기준으로 재현 확인한다. 실패하면 다음 run 없이 C STOP. 다른 8개 KDK20은 기존 continuous와 관측 기준을 대조한다.

전체 panel CPU/wall 총합 각각 Yoshida/KDK 비를 계산한다. **A**: 둘 다 <=1.10, 9/9 관측/재현 PASS. **B**: 둘 다 >1.10, 9/9 PASS. 한 지표만 1.10을 넘거나 수치·환경·변동 문제는 **C**. panel은 1회씩이라 입력별 반복분산은 평가하지 않으며 단일 boundary의 반복 안정성만 보조 근거다. 최소 시간만 고르지 않는다.

negative internal stage의 domain/hard-boundary/many-body/chemistry 위험은 유지한다. 이 연구는 별도 성능 진단이며 A 세계 채택·인증·O-1 PASS가 아니다. 동일 관측 하네스 비용을 측정할 뿐 승인된 replay/production/native 비용까지 주장하지 않는다.

기존 5950X 한 노드, 이전 승인 $1/hr·총 $1 상한, 최대 제어 3500초. package를 로컬 새 폴더에 복원하고 전체 object hash/새 seal/실행 probe/관련 시험을 통과한 뒤 시작한다. 원격에서도 같은 순서로 검사 후 campaign. 실패와 warm-up 포함 모든 trace/결과/log를 회수하여 SHA 확인하고 즉시 stop 및 exited/stopped 확인. LOCAL FULL은 사용자 지시대로 불필요하게 실행하지 않고 관련 시험으로 대체한다. commit/push 없음.
