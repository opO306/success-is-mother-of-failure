# ④-4c-8 — shell 17 hard-case 인증서 v1

**2026-09-28. 상태: shell 17 원래 domain 하나 Certified. 전체 ④-4b는 NotCertified.**
**fresh coverage 결과: 13/64 region, gap 82.** 이 숫자는 coverage 함수가 새로 계산한 값이다.
shell 16/15는 승인되지 않았다. precision cap 16384, 64-region 예산, 물리, D_valid는 그대로다.

## 무엇을 했는가

설계자 판정: [④-4c-7 조사](C1B1_HARD_CASE_SEARCH_SHELL17_SURVEY_V1.md) 결과가 양호하므로 shell 17을 [④-4c-6](C1B1_HARD_CASE_CERTIFICATE_V1.md)과 **같은 인증 계약**으로 올린다.
실제 인증 비용을 재서 shell 16 진입 여부를 판단한다.

- 계약은 `c1b1_hard_case_certificate.py`를 **그대로** 쓴다. `build`·`verify_certificate`·`check_outgoing_coverage`는 이미 domain·분할·블록 길이를 인자로 받는다.
- 그 모듈은 수정하지 않았다. shell 18 인증서 fixture가 그 소스 해시를 고정하고 있기 때문이다.
- 새 driver `c1b1_hard_case_certificate_shell17.py`는 shell 17 원래 domain을 묶고, 아래 단계를 실행하며 단계별 비용을 기록한다.

| 단계 | 내용 |
|---|---|
| build | superblock 1024행을 checker primitive로 전부 계산하고, 후보 전부를 정확 P/Q로 재평가한다 |
| verify | 같은 인증서 객체를 처음부터 다시 계산해 정확히 대조한다 |
| verify_stored_json | JSON으로 직렬화했다가 다시 읽은 인증서를 전체 재검증한다 |
| coverage | 기존 층 + shell 18 인증서(fixture) + shell 17 인증서로 fresh coverage를 계산한다. 이 단계에서 두 인증서를 다시 검증한다 |

## 결과 (원격 노드: AMD Ryzen 9 5950X, 물리 16코어·32스레드, 작업자 32)

| 항목 | 값 |
|---|---|
| domain | n ∈ [250000000000000000, 312500618227463140], 격자점 62,500,618,227,463,141개 |
| 후보 | **827개**, 전부 정확 재평가, **hazard 0** |
| 교차 수 합 | 8,645,949(④-4c-7과 같음) |
| required_bits | 4096 |
| **fresh coverage** | **used_regions 13/64, gap 82, status not_certified** |
| 남은 gap 분포 | shell 0: 65개, shell 1: 2개, shell 2〜16: 각 1개. **shell 17·18: 0개** |
| 교차 구현 대조 | 인증서 1024행이 ④-4c-7 조사의 **생성기** 행과 전부 일치 |

| 단계 | wall | 자식 프로세스 CPU | 병렬 효율 |
|---|---:|---:|---:|
| build | 203.1초 | 6,386.7초 | 0.983 |
| verify | 202.9초 | 6,378.8초 | 0.982 |
| verify_stored_json | 203.1초 | 6,382.5초 | 0.982 |
| coverage (shell 17·18 재검증 포함) | 361.0초 | 10,847.8초 | 0.939 |
| 전체 | 16분 15초 | | |

- CPU 시간은 32스레드가 물리 16코어를 나눠 쓴 값이다. **로컬 6코어의 CPU 초와 1:1로 비교하지 않는다.** 같은 계산(shell 17 checker)이 로컬 6코어에서는 약 4,650 CPU초였다.
- coverage 단계 효율이 낮은 것은 shell 18 재검증과 기존 층 계산이 들어가기 때문이다. 기존 층은 대부분 직렬이다(추정).

## shell 16/15 비용 재추정 (원격 기준, 측정 아님)

원격에서 shell 17 검증 CPU(6,379초)와 shell 18 검증 CPU(coverage 단계에서 shell 17 몫을 뺀 약 4,469초)로 `블록 × a + 경계 × b`를 풀었다. 결과는 a ≈ 852 µs, b ≈ 379 µs다.

| | 블록 | 경계(고정 fixture) | 검증 1회 CPU | 32스레드 wall(효율 0.98 가정) |
|---|---:|---:|---:|---:|
| shell 16 | 2,910,420 | 46,892,493 | 약 2.0×10⁴초 | 단계당 약 11분, 네 단계 약 45분 이상 |
| shell 15 | 2,328,343 | 250,139,754 | 약 9.7×10⁴초 | 단계당 약 52분, 네 단계 약 3.5시간 이상 |

- 점 두 개로 푼 값이다. shell 18 쪽 값에는 다른 coverage 층의 비용이 조금 섞여 있다.
- 후보 수가 늘면 정확 재평가 비용도 늘지만, 이 식에는 따로 들어가 있지 않다.
- ④-4c-7의 로컬 추정(shell 16 약 1.2×10⁴ CPU초)보다 크다. 원격 CPU 초가 SMT 때문에 부풀기 때문이며, 기계가 다르므로 두 값을 섞지 않는다.

## 시험 (`tests/test_c1b1_hard_case_certificate_shell17.py`, 8개)

- shell 17 guard 재현, 작은 slice의 build·JSON 왕복·verify, 조작한 행 거부.
- driver가 조사 driver를 import하지 않고, shell 18 인증 모듈 해시가 shell 18 fixture 기록과 같은지 확인.
- 저장 인증서:
  - 현재 소스 해시와 일치
  - 헤드라인 필드·단계 목록
  - 1024행 전부 생성기 행과 일치
  - 표본 행(처음·후보 첫 행·끝) 재계산 일치
  - coverage 재합성이 저장값과 일치(13 region, shell 17·18 gap 없음). 두 인증서의 수 분짜리 재검증만 동일성 검사로 바꿨다.

## 검증 실행

- **LOCAL FULL(`8d45209`): 2815 passed + 1 strict xfailed, skip 0, 408.27초.**
- **REMOTE LINUX FULL(같은 커밋): 2815 passed + 1 strict xfailed, skip 0, 356.36초.** 시험 2816개의 목록과 결과가 항목별로 같다.
- 리눅스는 작업자를 fork로 띄운다. 그래서 "spawn 작업자가 shell 번호를 받는다"는 실제 실행 검증은 Windows에서만 일어난다. 이 점은 원격 DeprecationWarning 6건으로 확인했다. 메커니즘 시험은 두 플랫폼 모두에서 돈다.

## 구현·재현

| 파일 | 역할 |
|---|---|
| `a_reference/c1b1_hard_case_certificate_shell17.py` | shell 17 driver: 단계 실행, 단계별 wall·CPU 기록, coverage 층 구성 |
| `a_reference/fixtures/c1b1_hard_case_certificate_shell17_v1.json` | 인증서(1024행) + fresh coverage + 단계 비용 + 소스 해시 |
| `tests/test_c1b1_hard_case_certificate_shell17.py` | 위 시험 |

재생성: `python -m a_reference.c1b1_hard_case_certificate_shell17 <out.json> <workers>`(원격 32스레드 약 16분).
로그: `runs/c1b1_hard_case_certificate_shell17_20260928/`.

## 다음 판단 (설계자)

1. shell 16을 survey_only로 먼저 잴지 여부. 위 추정으로는 원격에서 조사 1회(생성기 + checker)가 30분 안팎이다(추정).
2. shell 15는 shell 16 결과를 본 뒤 따로 결정한다.
