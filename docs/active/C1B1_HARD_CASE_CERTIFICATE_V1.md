# ④-4c-6 — shell 18 hard-case 인증서 v1

**2026-09-28. 상태: shell 18 원래 domain 하나 Certified. 전체 ④-4b는 NotCertified.**
**fresh coverage 결과: 12/64 region, gap 83.** 이 숫자는 coverage 함수가 새로 계산한 값이며 미리 정해 적은 값이 아니다.
shell 0〜17로 일반화하지 않는다. precision cap 16384, 64-region 예산, 물리, D_valid는 그대로다.

## 무엇을 했는가

설계자 판정(1): [④-4c-5 조사](C1B1_HARD_CASE_SEARCH_SURVEY_V1.md)의 shell 18 결과를 정식 인증 계약과 proof object로 올린다.
[rational spacing family checker](C1B1_RATIONAL_SPACING_FAMILY_V1.md)와 같은 잠금을 걸고, 통과한 뒤에만 coverage를 새로 계산한다.

인증하는 명제는 다음과 같다.

\[
\forall n\in[312500000000000000,\ 390625618227463140]:\quad \operatorname{dist}\!\left(\frac{P(n)}{Q(n)}-\frac12,\ \mathbb Z\right) > G .
\]

- G는 signed residual 구간의 최대 절댓값에 numeric endpoint error를 더한 값이다(약 2^-1614).
- 이 명제가 성립하면 family checker와 같은 논리로, 해당 domain의 모든 격자점에서 axis impulse 반올림이 4096 bit 안에서 결정된다.
- 명제는 **선언된 축 격자 domain 전체**에 대한 것이다. 실제 궤적이 이 점들을 방문하는지는 주장하지 않는다(`actual_trajectory_membership: not_claimed`).

## 인증 계약 (`c1b1-hard-case-certificate-v1`)

`verify_certificate(cert, expected_domain, execution_limit=16384)`는 아래 항목을 전부 **다시 계산해 정확히 같은지** 확인한다. 하나라도 다르면 `NotCertified`다.

| 잠금 | 검사 |
|---|---|
| domain binding | 외부에서 받은 원래 domain(양수 축 격자)과 cert의 domain·domain_hash가 같아야 한다 |
| 계약 필드 | version, status=certified, scope=`declared_positive_axis_lattice_domain_only`, global_4_4b=NotCertified |
| source 출처 | family checker의 foundation 해시와 hard-case checker 소스 해시(LF 정규화)가 같아야 한다 |
| precision | required_bits = residual_bits = max_decision_bits = 4096 ≤ execution_limit ≤ MAX_PRECISION_BITS(16384). execution_limit 2048이면 거부 |
| frozen P/Q | 동결 항등식을 다시 전개한 P(22차)/Q(29차) 정수 계수와 같아야 하고, Q 계수는 모두 양수여야 한다(단조 증가) |
| Q_max·격자점 수 | Q(hi)와 hi−lo+1을 다시 계산한다 |
| residual/error 출처 | signed residual 구간(4096-bit enclosure), numeric endpoint error(4096-bit 진단), G를 원시 함수에서 다시 만든다. ④-4c-5 fixture의 guard와 정확히 같다 |
| 탐색 행 | superblock 1024개가 domain을 빈틈 없이 연속으로 덮어야 한다. 행마다 도함수 상한, 교차 수, 후보 구간을 hard-case checker의 block loop(block_points = 2^34+1)로 재계산해 비교한다 |
| 후보·hazard | 후보 수를 다시 세고, 모든 후보를 원래 정확 P/Q로 평가한다. dist ≤ G이면 거부한다 |
| legal momentum | \|impulse\| 상한 = Σ\|p_k\|·hi^k / Q(lo) + G. 20배(모멘텀 ULP 환산)가 (2^96−1)/2 미만이어야 한다 |
| 작업 한도 | 후보 점이 2^20개를 넘으면 계산하지 않고 거부한다(물리 cap이 아니라 멈춤 방지) |

coverage 연결: `check_outgoing_coverage`는 기존 compositor 층(rounding_regions → half_ulp_boundaries → family_certificates) 위에 한 층을 더 쌓는다.
검증을 통과한 인증서의 domain만 이전 층의 미피복 구간을 줄이고, 전체 region 수가 64를 넘으면 거부한다.

## 결과 (6 워커)

| 항목 | 값 |
|---|---|
| domain | n ∈ [312500000000000000, 390625618227463140], 격자점 78,125,618,227,463,141개 |
| block_points / superblock | 2^34+1 / 1024 |
| 후보 | **109개**. 전부 정확 재평가, **hazard 0** |
| 교차 수 합 | 1,568,498(④-4c-5와 같음) |
| required_bits | 4096 |
| build | 551초 |
| verify(독립 재계산) | 547초 |
| coverage 합성(인증서 재검증 포함) | 567초 |
| **fresh coverage** | **used_regions 12/64, gap 83, status not_certified** |
| 남은 gap 분포 | shell 0: 65개, shell 1: 2개, shell 2〜17: 각 1개. **shell 18: 0개** |

- 시간은 최종 실행 기준이다. 설명문만 고친 뒤 전체를 재생성했고, 인증서와 coverage가 이전 실행과 완전히 같았다(이전 결과: `certificate_full_pre_docstring.json`).
- 저장된 JSON 인증서를 파일에서 그대로 읽어 `verify_certificate`로 전체 재검증했다(`runs/c1b1_hard_case_certificate_20260928/verify_wire.log`).
- 인증서의 1024개 행은 ④-4c-5 조사에서 **생성기**가 만든 행과 전부 일치한다. 생성기와 checker는 서로 다른 구현이다.

**읽는 방법:**
- region 하나가 늘었고 gap이 하나 줄었다(84→83). shell 18 domain이 기존 gap 하나와 정확히 겹쳤기 때문이다. 이 대응은 coverage 함수가 계산한 결과다.
- 전체 ④-4b와 R=20 예시는 여전히 **NotCertified**다. shell 0〜17의 gap 83개가 남아 있다.
- checker는 동결 P/Q 항등식, 기존 numeric error lemma, 정수 EXP 기반을 공유한다. 새 독립 물리 감사가 아니다.

## 첫 전체 실행의 결함 (보존)

첫 전체 인증 실행(05:21 시작)은 1시간 46분 뒤 수동으로 멈췄다.

- **원인:** `_recompute_row`가 superblock 하나(2^34 블록 약 4441개)를 **quadratic 블록 하나로 통째로** 처리했다.
- δ는 블록 길이의 세제곱에 비례한다. 그래서 후보가 약 109개에서 천문학적인 수로 불었고, 이를 정확 평가로 하나씩 도느라 멈췄다. 결과가 틀리지는 않지만(sound) 끝낼 수 없는 계산이었다.
- **시험이 못 잡은 이유:** build와 verify가 같은 `_recompute_row`를 불렀다. 같은 부품으로 자기를 검사한 셈이다([검증 한계 유형 A](../reference/VERIFICATION_LIMITS_AND_LESSONS.md)).
- 작은 smoke 시험에서 같은 64블록의 후보 수가 superblock 1개일 때 945개, 4개일 때 10개로 달랐다. 이 신호를 조사하지 않았다.
- **수정:**
  - `_recompute_row`가 checker의 `superblock()` block loop에 맡긴다. ④-4c-5에서 1024/1024 일치한 경로다.
  - `block_points`를 인증서 필드로 명시했다.
  - 후보 작업 한도를 두어, 오래 멈추는 대신 거부하게 했다.
  - 시험 추가: 생성기 fixture 행과의 교차 구현 대조, 통째 처리 회귀, 작업 한도 거부.
- 기록: `runs/c1b1_hard_case_certificate_20260928/attempt_notes.json`.

## 시험 (`tests/test_c1b1_hard_case_certificate.py`, 34개)

- guard 재현, 작은 slice(64블록)의 build·verify, 직렬/병렬 build 동일, JSON 직렬화 뒤 verify.
- hazard가 실제로 남는 합성 항등식에서 build 거부.
- 변조 거부 13종: guard, candidate_count, impulse 상한, domain 끝, momentum_scale, foundation 해시, P 계수, residual 구간, status, version, scope, required_bits, Q_max.
- 작은 도함수 상한 위조, 후보 삽입·삭제, superblock 삭제(비연속), 외부 domain 불일치, execution_limit 2048 거부.
- coverage: 작은 slice는 region을 1개 늘리지만 not_certified를 유지. 65 region은 거부.
- 저장된 인증서:
  - 현재 소스 해시와 일치
  - 1024행 전부 생성기 행과 일치
  - 표본 행(처음·후보 있는 첫 행·마지막) 새 재계산과 일치
  - coverage 재합성이 저장값과 일치(12/64, gap 83, shell 18 gap 없음). 이 시험만 10분짜리 인증서 재검증을 동일성 검사로 바꿨다.
- 회귀 시험: superblock 통째 처리가 후보를 100배 넘게 부풀림, 후보 작업 한도 거부.

## 구현·재현

| 파일 | 역할 |
|---|---|
| `a_reference/c1b1_hard_case_certificate.py` | 인증 계약: build, verify_certificate, check_outgoing_coverage, certify_shell_18, example_report |
| `a_reference/fixtures/c1b1_hard_case_certificate_v1.json` | shell 18 인증서(superblock 1024행) + fresh coverage + source 해시 |
| `tests/test_c1b1_hard_case_certificate.py` | 위 시험 |

재생성: `python -m a_reference.c1b1_hard_case_certificate <out.json>`(6 워커, 약 30분). 실행 로그는 `runs/c1b1_hard_case_certificate_20260928/`에 있다.

## 다음 (설계자 판정 순서)

1. ④-4c-7: shell 17 **하나만** 같은 방식으로 실측한다. 후보 수, 교차당 비용, checker 비용, 병렬 효율을 잰다. 16/15로 함께 넓히지 않는다.
2. shell 0〜6은 전체 impulse I(n)=P/Q+S를 다루는 별도 설계 트랙으로 둔다(shell 5〜6의 병목은 따로 표시). 이번에는 구현하지 않는다.
3. proof 창고와 자동화는 만들지 않는다. same-input filter/checker는 유지한다.
