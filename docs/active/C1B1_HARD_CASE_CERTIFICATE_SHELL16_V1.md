# ④-4c-10 — shell 16 hard-case 인증서 v1

**2026-09-28. 상태: shell 16 원래 domain 하나 Certified. 전체 ④-4b는 NotCertified.**
**fresh coverage 결과: 14/64 region, gap 81.** shell 15는 승인되지 않았다.

## 설계자 판정 (판독 + 승격)

> **설계자 판정 — ④-4c-10**
> shell 16 survey에서 관측된 후보 밀도 증가는 보간 오차 δ 증가와 일관된 비용·탐색 현상으로 해석한다. **이 해석은 향후 비용 추정에만 사용하며 certification 또는 soundness의 증거로 사용하지 않는다.**
> shell 16은 hazard 0, checker 1024/1024 일치, brute-force 누락 0, 구조적 불일치 없음, 병렬 효율 유지, 메모리 문제 없음, 예측 비용과 실측 비용의 일치가 확인되었으므로 기존 hard-case certificate 계약으로의 승격을 승인한다.
> shell 15는 승인하지 않는다. shell 16 certificate와 fresh coverage, 실제 인증 비용을 확인한 뒤 별도로 판단한다.

[④-4c-9 조사](C1B1_HARD_CASE_SEARCH_SHELL16_SURVEY_V1.md)에서 밀도 변화는 δ 증가로 설명 가능한 패턴으로 관찰됐을 뿐이다. 이 문서의 인증은 그 관찰을 근거로 삼지 않는다 — 아래 결과는 인증 계약(정확 재평가·독립 재계산·hazard 검사)이 전부 통과했다는 사실만으로 성립한다.

## 무엇을 했는가

계약은 shell 17([④-4c-8](C1B1_HARD_CASE_CERTIFICATE_SHELL17_V1.md))과 **완전히 같다.** `c1b1_hard_case_certificate.py`는 수정하지 않았다.
새 driver `c1b1_hard_case_certificate_shell16.py`는 `c1b1_hard_case_certificate_shell17`의 `_stage`/`layers` helper를 그대로 불러 shell 16 domain을 묶고, coverage 층에 **shell 18·17·16 세 인증서**를 함께 넣는다.

| 단계 | 내용 |
|---|---|
| build | superblock 1024행을 checker primitive로 계산하고, 후보 전부를 정확 P/Q로 재평가 |
| verify | 인증서를 처음부터 다시 계산해 정확히 대조 |
| verify_stored_json | JSON 왕복 뒤 전체 재검증 |
| coverage | 기존 층 + shell 18·17·16 인증서(**세 개 모두 이 단계에서 재검증**)로 fresh coverage 계산 |

## 결과 (원격: AMD Ryzen 9 5950X, 32스레드)

| 항목 | 값 |
|---|---|
| domain | n ∈ [200000000000000000, 250000618227463140], 격자점 50,000,618,227,463,141개 |
| 후보 | **6,581개**, 전부 정확 재평가, **hazard 0** |
| 교차 수 합 | 46,892,493(④-4c-9와 같음) |
| required_bits | 4096 |
| **fresh coverage** | **used_regions 14/64, gap 81, status not_certified** |
| 남은 gap 분포 | shell 0: 65개, shell 1: 2개, shell 2〜15: 각 1개. **shell 16·17·18: 0개** |
| 교차 구현 대조 | 인증서 1024행이 ④-4c-9 조사의 **생성기** 행과 전부 일치 |

| 단계 | wall | 자식 프로세스 CPU | 병렬 효율 |
|---|---:|---:|---:|
| build | 628.0초 | 19,758.6초 | 0.983 |
| verify | 627.9초 | 19,760.8초 | 0.983 |
| verify_stored_json | 628.8초 | 19,770.1초 | 0.983 |
| coverage (shell 18·17·16 재검증 포함) | 988.0초 | 30,589.7초 | 0.968 |
| **전체** | **47분 57초** | | |

- ④-4c-9에서 예측한 shell 16 검증 1회(약 2.0×10⁴ CPU초)와 이번 실측(19,761초)의 차이는 약 1%다. shell 17에서 만든 비용 모델이 다음 shell에서도 거의 맞았다.
- coverage 단계는 shell 18·17·16 세 인증서를 모두 재검증하므로, 그 CPU 시간이 세 인증서 검증 CPU 합(약 6,379+19,761+α)에 근접한다. 계산해보면 순서가 맞는다(shell 18 몫은 이전 문서의 약 4,469초 추정과 같은 크기).

## 시험 (`tests/test_c1b1_hard_case_certificate_shell16.py`, 9개)

- shell 16 guard 재현, 작은 slice의 build·JSON 왕복·verify, 조작한 행 거부.
- driver가 조사 driver를 import하지 않고, 인증 모듈 두 개(shell 18·17)의 해시가 shell 17 fixture 기록과 같은지 확인.
- shell 16 이전 region 수가 정확히 14(기존 층 3+3+5, shell 18·17·16 각 1)인지 확인.
- 저장 인증서:
  - 현재 소스 해시와 일치
  - 헤드라인 필드·단계 목록
  - 1024행 전부 생성기 행과 일치
  - 표본 행(처음·후보 첫 행·끝) 재계산 일치
  - coverage 재합성이 저장값과 일치(14 region, shell 16·17·18 gap 없음). 세 인증서의 수 분짜리 재검증만 동일성 검사로 바꿨다.

## 구현·재현

| 파일 | 역할 |
|---|---|
| `a_reference/c1b1_hard_case_certificate_shell16.py` | shell 16 driver. shell 17 driver의 `_stage`/`layers`를 재사용하고, shell 18·17·16 세 인증서를 층으로 구성 |
| `a_reference/fixtures/c1b1_hard_case_certificate_shell16_v1.json` | 인증서(1024행) + fresh coverage + 단계 비용 + 소스 해시 |
| `tests/test_c1b1_hard_case_certificate_shell16.py` | 위 시험 |

재생성: `python -m a_reference.c1b1_hard_case_certificate_shell16 <out.json> <workers>`(원격 32스레드 약 48분).
로그: `runs/c1b1_hard_case_certificate_shell16_20260928/`.

## 검증 실행

- **LOCAL FULL(`0117cd8`): 2834 passed + 1 strict xfailed, skip 0, failure/error 0, 398.68초.**
- **REMOTE LINUX FULL(같은 커밋, 32워커): 첫 실행 1 failed + 2833 passed.** 실패한 시험은 이번 변경과 무관한 `tests/test_primal_precision.py::test_what_hands_feel_never_names_the_engine`이다(아래 참조).
- **REMOTE LINUX FULL 재실행: 2834 passed + 1 xfailed, skip 0, 361.87초.** LOCAL FULL과 시험 2835개의 목록·결과가 항목별로 같다.
- 첫 원격 실패의 원인은 시험 쪽 결함이다. 마지막 시험이 같은 파일의 다른 시험들이 모듈 전역 `FELT` 리스트에 채워 둔 값을 읽는다. 그런데 pytest-xdist의 기본 분배(`--dist load`)는 시험을 개별 단위로 작업자에 나누므로, 마지막 시험이 다른 작업자에 배정되면 빈 리스트를 읽는다. 회귀는 아니지만 원인이 남아 있는 **열린 결함**이다([검증 한계](../reference/VERIFICATION_LIMITS_AND_LESSONS.md)). 로그: `runs/c1b1_hard_case_certificate_shell16_20260928/{local_full.*,remote_linux_full.*}`(재실행분).

## 다음 판단 (설계자)

1. shell 15 조사(survey_only) 진입 여부. ④-4c-9 재추정으로는 원격 약 1시간 5분, 인증 전체는 약 3.5〜4시간이다.
