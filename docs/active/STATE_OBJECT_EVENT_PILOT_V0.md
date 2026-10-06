# STATE_OBJECT_EVENT_PILOT_V0 — 결과

2026-10-05. **SURVEY_ONLY / NOT CERTIFIED / NOT PRODUCTION APPROVED.** 브랜치 `codex/state-object-event-pilot-v0`, 기준 `0ecfb7f`.
설계 근거: STATE_OBJECT_EVENT_ARCHITECTURE_V0_2.md(설계자 인계 2026-10-05)와 같은 날 구현 지시.
protocol은 코드보다 먼저 봉인했다(`ed0e372`). PART A 코드는 실행 전에 봉인했고(`3688624`), PART B 코드·증명서·checker도 실행 전에 봉인했다(`29035e4`).
**PART A와 PART B는 서로 다른 세계 의미론이다. 결과와 판정을 합치지 않는다.**

## 판정 (독립 checker, 봉인 규칙 그대로)

| 축 | 판정 | 한 줄 |
|---|---|---|
| OBSERVER_ISOLATION | **PASS** | 관측자를 켜든 끄든 4개 궤적 모두 10,000 step까지 모든 step이 비트 단위로 같다 |
| WORLD_LIVE_MEMORY | **GROWS (규칙 결함, 아래 참조)** | 실제 측정값은 늘지 않았다. 봉인한 "max/min ≤ 1.25" 규칙이 **감소**(1421→1129 B)를 잡았다 |
| PORT_MODEL | **BIT_IDENTICAL** | 객체·포트·사건 구조가 기존 실행기와 비트 단위로 같다 |
| PORT_COST | **TIE** (PORT_STRUCTURE_ONLY = true) | CPU 비율 0.95〜1.04. 포장만 바뀌었고 비용 이득은 없다 |
| PAIR_CURRENT_STATE | **LOSSLESS** (대칭 A2만) | 합·차 정수 상태에서 원자 raw를 매 step 정확히 복원했다 |
| PAIR_COST | **TIE** | CPU 0.98배 |
| LINEAGE_SOUNDNESS | **PASS** (필요조건 수준, 한계 참조) | 단위 oracle·결함 주입 시험, 512비트 기준 교집합, 칸 일치 모두 통과 |
| LINEAGE_CORRELATION | **YES** | 96비트 step 100에서 후보는 칸을 결정하고 기준선은 못 함. 최악 정규화 반경 4.04배 작음 |
| LINEAGE_COST | **WORSE** (stage 1: 3.17배) | 1000 step에서는 **28.5배**로 커진다(10배 벽 초과. 봉인 규칙은 stage 1에만 적용) |
| TAG_GROWTH | **CONTROLLED** | step당 정확히 3개(3,002개 @1000), 상한 3(s+1) 이내. 비용은 제곱으로 증가 |

## 쉬운 결론

**PART A (생산 C1-B1, 반올림된 저장 상태가 다음 입력인 세계)**
1. **세계는 현재 상태만 들고 있어도 같은 미래를 만든다.** 이 사실은 이미 구조상 그렇다. 기존 실행기 `c1b1_two_atom.step`은 처음부터 현재 `Run`만 읽는다. 관측자가 과거 기록 10,000개를 쌓아도 물리 결과는 SHA-256까지 같았다.
2. **기록 비용은 관측자 쪽에만 있다.** 기록은 step당 약 908 B씩 선형으로 늘어 10,000 step에서 9.1 MB가 됐다(프로세스 피크 RSS +약 10 MB). 세계 쪽 현재 상태는 약 1.1〜1.6 KB로 일정했다. 관측자를 켜도 CPU 차이는 측정 잡음(±5%) 안이었다.
3. **원자를 '나사·볼트' 객체로 만들고 상호작용을 사건 하나로 묶어도 결과는 비트 단위로 같다.** 사건마다 "i가 받는 충격 = −(j가 받는 충격)"과 "저장 격자에서 총운동량 불변"을 직접 검사했고, 모든 step에서 성립했다(궤적당 사건 10,000개, 사건 적용 검사 20,000회). 하지만 기존 실행기도 같은 J를 두 원자에 쓰므로 이 성질은 원래 성립한다. 객체화는 그것을 **검사 가능하게 드러냈을 뿐** 계산을 줄이지 않았다.
4. **대칭 A2의 쌍 상태(합·차)는 손실 없이 동작한다.** 중심 위치를 반 격자로 만들지 않으려고 합(=2×중심)을 정수로 저장했다. 대칭 조건(합 = 0)이 유지되는 동안 원자 하나의 변위 반올림을 생략한다. 그래도 CPU는 같은 수준이었다. 힘 계산이 비용의 대부분이라서다.

**PART B (Exact Expression V1, 반올림 없는 정확 실수 세계)**
5. **"같은 사건에서 나온 +오차와 −오차"를 같은 이름표로 묶는 것은 실제로 효과가 있다.** 96비트 step 100에서 운동량 반경이 4배 작아져 기준선이 못 정한 칸을 정했다. 1000 step에서는 운동량 반경이 약 **200만 배** 작았다(96·128비트 모두).
6. **하지만 장부가 비싸다.** 이름표가 step마다 3개씩 쌓이고, 매 연산이 쌓인 이름표 전부를 훑는다. 그래서 100 step에서 3.2배이던 CPU가 1000 step에서 28.5배가 됐다. 같은 칸을 정하는 더 싼 방법이 이미 있다. 기준선을 128비트로 돌리면 step 100과 1000 칸을 정하는 데 1000 step 기준 5.9초가 들고, 후보(128비트)는 167초가 든다.
7. **96비트 step 1000은 후보도 못 정했다**(운동량 정규화 반경 1.27 > 0.5). 정밀도를 한 단계 낮추는 이득은 100 step까지만 확인됐다.
8. **초기 step에서는 후보의 위치 반경이 오히려 넓다**(step 10: 2.7e-13 대 8.5e-14). 반올림 오차를 연산마다 2^(1−p)|결과|로 보수적으로 묶어 상관 없는 잔차에 쌓기 때문이다. 이 잔차는 step에 따라 선형으로 증가한다.

## PART A 수치 (10,000 step, 3회 중앙값, 새 프로세스, 순차 실행)

| case | WORLD_ONLY CPU | OBSERVER | PORT | PAIR | 세계 상태 크기(deep) | 관측 기록 @10,000 | 피크 RSS 세계/관측 |
|---|---|---|---|---|---|---|---|
| e0.5_rho-0.005 | 13.64 s | 13.03 (0.955) | 12.95 (0.950) | — | 1301〜1589 B | 9.08 MB | 24.5 / 34.5 MB |
| e1_b10 | 12.39 | 12.23 (0.987) | 12.25 (0.989) | — | 1297〜1589 B | 9.07 MB | 24.9 / 35.2 MB |
| e10_b0 | 8.77 | 8.75 (0.998) | 9.00 (1.027) | — | 1129〜1421 B | 7.33 MB | 24.9 / 32.7 MB |
| A2_sym | 12.55 | 12.75 (1.016) | 13.02 (1.037) | 12.31 (0.981) | 1305〜1589 B (PAIR 721〜725) | 9.09 MB | 24.9 / 35.1 MB |

- 4개 case 모두 10,000 step을 정상 완주했다(도메인 거부 없음). case마다 모든 실행(12개, A2_sym은 16개)의 궤적 identity가 하나였다. checker는 자체 기록 형식과 자체 hash로 기존 REF 실행기를 다시 돌려 같은 값을 얻었다.
- tracemalloc 현재값(세계만 있을 때): step 1에서 1.141 MB, step 100까지 약 135 KB 증가(실행 초기의 캐시·지연 import), 그 뒤 1000→10,000 사이 +0.6〜0.9 KB. 마지막 증가분은 측정 장부(체크포인트 기록 문자열과 측정값 dict)로 보인다. 추정이며 추적하지 않았다.
- **WORLD_LIVE_MEMORY 규칙 결함:** 봉인 규칙 "live state deep size max/min ≤ 1.25"는 방향을 보지 않는다. e10_b0에서 step 1의 1421 B와 이후 1129 B의 비율이 1.2586이라 GROWS가 됐다. 감소의 원인은 `sys.getsizeof(vars(dataclass))`가 CPython의 인스턴스 사전 표현에 따라 다른 값을 내는 측정 방식이다(같은 정수 12개 + J 3개를 들고 있음을 확인했다). 결과를 본 뒤 규칙을 고치지 않았다. **판정은 GROWS로 남기되, 실제 성장은 관측되지 않았다**는 것이 이 문서의 해석이다. 다음 Gate의 규칙은 설계자가 정한다.
- 비용 판정 대역(±10%)은 이번 잡음(같은 모드 3회 사이 차이 최대 약 5%)보다 넓다. 측정 중 다른 세션의 Python 프로세스(PID 25700, `cstream_event_lineage_scratch.py`, 10:40 시작)가 코어 하나를 계속 쓰고 있었다(12 논리 코어 중 1개). 제가 시작한 프로세스가 아니라 종료하지 않았다.

## PART B 수치 (A2_bound, 3회 중앙값)

정규화 반경 = 반경 / 칸 크기(위치 2⁻⁴⁸, 운동량 2⁻⁸⁰). 0.5 미만이고 경계를 넘지 않아야 칸이 정해진다.

| 정밀도·길이 | 경로 | CPU | step 10 (결정 / 위치 / 운동량) | step 100 | step 1000 | tag |
|---|---|---|---|---|---|---|
| 96 / 100 | 기준선 | 0.55 s | ✔ / 8.5e-14 / 2.6e-3 | ✘ / 1.6e-12 / 0.222 | — | — |
| 96 / 100 | 후보 | 1.73 s (3.17×) | ✔ / 2.7e-13 / 1.9e-3 | **✔** / 2.8e-12 / **0.055** | — | 32 / 302 |
| 96 / 1000 | 기준선 | 5.27 s | 같음 | 같음 | ✘ / 2.2e-5 / 2.7e6 | — |
| 96 / 1000 | 후보 | 150.2 s (28.5×) | 같음 | 같음 | ✘ / 7.5e-11 / **1.27** | 3,002 |
| 128 / 1000 | 기준선 | 5.88 s | ✔ | ✔ | ✔ / 5.0e-15 / 6.0e-4 | — |
| 128 / 1000 | 후보 | 167.4 s (28.5×) | ✔ | ✔ | ✔ / 1.7e-20 / **2.9e-10** | 3,002 |

- 확장 판정(사전 고정 규칙): 후보 96비트 step 100 결정 ✔, 반경비 4.04 ≥ 2, 건전성 통과, CPU 3.17 ≤ 10 → **EXTEND**. campaign이 판정했고, checker가 512비트 기준으로 독립 재도출한 값과 일치했다.
- 피크 RSS: 기준선 약 27 MB, 후보 1000 step 37.5 MB.
- 1000 step 후보 CPU는 반복 간 133〜197 s로 흔들렸다. 위 PID 25700 부하 아래에서 측정한 값이다.

## 증명서 (미분 enclosure 표)

R ∈ [7065/1024, 7680/1024] bohr, 1/1024 간격 615 cell. 각 cell에 `radial_derivatives`의 V′·V″와 G′(s) = (V′ − R V″)/(2R³) 구간을 정확 분수로 저장했다(생성 52.7 s, 작업자 6개).
checker는 별도 프로세스에서 615 cell을 **모두** 다시 계산해 저장값과 같음을 확인했다. G′는 자체 구간 코드로 다시 계산했다. 독립 필요조건 검사도 했다. `c1b1_two_atom._model_R`로 cell 양 끝의 V′ 점 enclosure를 구해 V′(cell)과 만나는지, 평균값 기울기가 V″(cell)과 만나는지 봤다. 문제 0이었다.
cell 안 G′의 상대 폭은 약 3.6%다(Taylor 구간 과대평가). 정확히 R = 7.5인 상단 경계는 보수적으로 거부한다(A2 궤적은 R ≤ 7.41이라 영향 없음).

## 결함 주입 (검사기가 눈을 감고 있지 않은지)

| 주입한 결함 | 잡혔나 | 어디서 |
|---|---|---|
| 관측자가 Run에 써서 raw 1 변경 | ✔ | stream hash 불일치 |
| 사건의 impulse_i를 1 raw 위조 | ✔ | EventInvariantViolation |
| 쌍 상태의 합 ≠ 0 | ✔ | PAIR_STATE_REFUSED |
| 같은 tag +X/−X | ✔ 정확히 상쇄 | 단위 시험 |
| 다른 사건에 같은 tag id | ✔ | 할당기 TagReuse. oracle은 거짓 상쇄를 보임 |
| 비선형 잔차를 0으로 위조 | ✔ | 표본 정확 oracle(ε = ±1) |
| 반올림 오차를 안쪽으로 | ✔ | 8비트에서 1 + 2⁻²⁰ 미포함 |
| R < / = / > r_min | ✔ | VIOLATED / PROVEN / PROVEN, 경계 걸침은 UNPROVEN |
| cell 경계 걸침 | ✔ | 두 cell의 hull 사용 |
| 증명서 밖 R | ✔ | EVENT_DERIVATIVE_DOMAIN_UNSUPPORTED |
| 관측·판정이 상태를 바꿈 | ✔ 안 바뀜 | 매 step 판정한 경우와 비트 동일 |
| 사건 J 중심을 1e-12 이동(참값 이탈) | ✔ | 512비트 기준과 교집합 없음 |
| **사건 tag 계수 전부 삭제** | **✘ 못 잡음** | 아래 한계 1 |
| 증명서 G′ 좁히기 / cell 빠짐 / 중복 / 저장 V′ 변경 / protocol hash | ✔ | 증명서 checker |

## 먼저 공개할 한계

1. **campaign의 건전성 검사(512비트 기준과 교집합, 칸 일치)는 필요조건일 뿐이다.** 사건 tag 계수를 전부 지운 후보도 24/32/40/96비트 모두에서 기준과 계속 만났다. 연산마다 잡는 반올림 상계(2 ulp)가 실제 오차(≤ 0.5 ulp)보다 크고, lang_iv 점 평가 구간도 실제 오차보다 넓어서, 위조된 범위도 참값을 실제로 포함했기 때문이다. 따라서 후보의 건전성 근거는 **연산 단위 oracle 시험과 코드 검토**다. 궤적 전체에 대한 증명은 없다.
2. **힘 계산 TCB는 공유다.** G(s₀)는 기준선과 같은 `exact_expression_gate_v0/lang_iv.py`를 쓰고, checker 기준도 같은 코드를 쓴다. 증명서 재계산도 같은 `radial_derivatives`를 쓰므로 함수 자체의 결함은 잡지 못한다. `_model_R` 교차검사는 독립이지만 필요조건이다.
3. **PART A의 checker 재실행은 같은 REF 실행기 코드를 쓴다.** 이것은 "기준이 REF 실행기"라는 정의에 맞는 검사다. REF 실행기 자체의 물리 정확성은 이번 범위가 아니다.
4. **시간은 단일 장비에서 순차 측정했다**(3회 중앙값). 다른 세션 프로세스 하나가 동시에 돌았다. PART A 비용 차이(±5%)는 판정 대역 안의 잡음이다.
5. **checker 버그를 실행 뒤 고쳤다.** PART B checker가 protocol 키를 `part_b`로 읽어 KeyError로 멈췄다. `part_B`로 고쳤고 판정 로직은 바꾸지 않았다. checker는 실행기 seal 대상이 아니다.
6. **확장 판정의 건전성 입력이 둘이다.** campaign은 기준선과의 교집합과 칸 일치로 판정했고, checker는 512비트 기준으로 재도출했다. 결과는 같았다(EXTEND).
7. **추가한 파일:** `campaign_b.py`. PART A seal 뒤 `campaign.py`를 고치지 않으려고 PART B 진행을 별도 모듈로 뺐다. `campaign.py` 안의 `SEALED_B` 목록은 쓰이지 않는다(PART B는 `campaign_b.SEALED_B` 사용).
8. **쌍 상태는 대칭 A2 하나만** 시험했다. 일반 쌍이나 N체로 승격하지 않는다.
9. **이름표 비용:** step당 tag 3개면 연산 하나가 O(T)이고 궤적 전체는 O(T²)다. 100→1000 step에서 후보 CPU는 약 87배 늘었다. 10,000 step은 시험하지 않았다(protocol상 금지는 아니지만 확장 규칙이 1000까지만 정함).

## 방향

- PART A는 "기존 current-state 실행기 + 관측자 분리"만으로 목적이 이미 달성된다. 객체·포트 계층은 불변식을 드러내는 데 쓸 수 있지만 성능 구조는 아니다(인계 문서 20절의 더 싼 대안이 이겼다).
- PART B는 **원인 규명으로서는 유효**하다. 구간 폭 증가의 상당 부분이 "같은 사건의 ± 상관을 잃는 것"과 "힘 식 내부의 의존성"이라는 해석을 지지한다. **성능 최적화로서는** 같은 칸을 정하는 데 정밀도를 올린 구간 계산보다 비싸다.
- 다음 후보(승인 필요, 자동 착수하지 않음): ① 반올림 상계를 덜 보수적으로 잡아 초기 위치 반경 악화를 없애는 것 ② 오래된 tag를 압축하는 규칙. 다만 ②는 이번 금지 목록(병합·삭제)과 충돌하므로 설계자 결정 대상이다.

## 재현

```
python -m experiments.state_object_event_pilot_v0.campaign part_a --out runs/<dir_a>
python -m experiments.state_object_event_pilot_v0.derivative_certificate generate --out <cert> --workers 6
python -m experiments.state_object_event_pilot_v0.campaign part_b_stage1 --out runs/<dir_b>
python -m experiments.state_object_event_pilot_v0.campaign part_b_stage2 --out runs/<dir_b>
python -m experiments.state_object_event_pilot_v0.checker --part-a runs/<dir_a> --part-b runs/<dir_b> --cert <cert> --out verdict.json
```

증거: [results.json.gz](state_object_event_pilot_v0/results.json.gz)(실행 파일 77개 묶음), [checker_verdict.json](state_object_event_pilot_v0/checker_verdict.json), [execution_seal.json](state_object_event_pilot_v0/execution_seal.json), [campaign.log](state_object_event_pilot_v0/campaign.log), [derivative_certificate.json.gz](state_object_event_pilot_v0/derivative_certificate.json.gz).

**검증:** 관련 시험 통과. 새 시험 35개(단위·결함 주입 33 + 증거 2)와 기존 V0/V1 시험 33개. LOCAL FULL은 생략하고 관련 시험으로 대체했다. 이유: 새 survey 패키지·시험·문서만 추가했고, `a_reference/`·`a_numeric/`·`exact_expression_gate_v0/`·`exact_expression_gate_v1/`는 기준점 대비 변경 0이다(git diff로 확인). 공식 기준선 숫자는 갱신하지 않았다.
