# 활성 사건률·시간·공간 확장성 전수 감사 v1

**대상 실행 경로:** `run_nonliving_face_until.py` → `step_nonliving_world()`  
**대상 코드 해시:** `e3d8ba1ec377649bb658a970cf9ef1c5fe5d7bbd19f7c728c8fba1d8d1c458ae`  
**대상 실험:** `dual-gcp-observer-v1`  
**판정:** 보존·재생·관찰 격리는 유효하나, 현재 사건 가중치와 시간은 공간적으로 확장 가능한 공통 물리 사건률이 아니다. 다음 과학 실험 전에 별도 scheduler-v2 계통이 필요하다.

## 1. 감사 질문

1. 세계 하나가 어떤 사건들을 어떤 순서로 실행하는가?
2. 각 사건의 선택 가중치는 어떤 물리량에서 유도되는가?
3. 서로 다른 사건 종류의 가중치를 같은 분모에서 비교할 수 있는가?
4. 공간이나 독립 영역을 늘려도 기존 지역의 사건률이 유지되는가?
5. 코드의 `time`, `ordinary_events`, 실제 벽시계 시간이 각각 무엇을 뜻하는가?
6. 현재 VM 결과에서 어떤 결론은 유지되고 어떤 결론은 제한해야 하는가?

## 2. 최종 요약

### 유지되는 검증

- 모든 상태 전환의 물질·매질·에너지 회계
- seed 기반 난수 재생
- 관찰기 ON/OFF 물리 결과 동일성
- 구획·서열 계보의 사후 추적
- 현재 정의된 이산 사건계 안에서의 실제 사건 기록
- `fold → 잠시 두 내부 공간 → unfold`라는 분할 원인

### 다음 장기 실험을 막는 핵심 문제

1. **공통 물리 시간 부재:** 사건마다 `sequence.time += 1`이지만 실행 주기는 별도 `ordinary_events`로 결정된다.
2. **비확장적 전역 스케줄:** 세계가 커져도 ordinary·화학·물질·막 사건은 각 채널에서 최대 하나씩만 발생한다.
3. **단위가 다른 가중치 혼합:** 이동 후보 개수, 회전 후보 개수, 결합 에너지, 열 기반 지수 해제 가중치를 한 추첨 분모에서 더한다.
4. **전역 열 저장고:** 공간적으로 먼 접촉·골격 반응이 같은 `thermal_energy`를 소비·반환한다.
5. **농도 법칙 부재:** 화학·응결 후보는 필요한 양이 존재하는지만 보고, 그 이상 농도 차이를 사건률에 반영하지 않는다.
6. **구조 크기 이동 편향:** 연결 성분의 모든 site가 동일한 전체 성분 이동을 촉발하므로 큰 구조가 더 많은 이동 추첨권을 갖는다.
7. **벽시계 종료 편향:** 계산이 빠른 세계가 같은 실험 시간에 더 많은 물리 사건을 겪는다.
8. **막 독립 분열 경로 부재:** 하나의 순환 경계가 두 독립 순환 경계로 절단·봉합되는 사건이 없다.

## 3. 실제 활성 스케줄

한 `step_nonliving_world()` 호출의 고정 순서는 다음과 같다.

1. spatial energy cycle — `ordinary_events % 1,000,000 == 0`
2. medium transport cycle — 현재 장기 실행에서는 비활성
3. face transport cycle — `ordinary_events % 20 == 0`
4. face chemistry — `ordinary_events % 3 == 0`
5. face material — `ordinary_events % 2 == 0`
6. face boundary — `ordinary_events % 4 == 0`
7. ordinary spatial sequence event — 매 step 정확히 하나

같은 outer step에서 여러 보조 사건이 발생할 수 있으므로 “세계 전체에서 항상 사건 하나뿐”이라는 설명은 부정확하다. 그러나 각 확률 채널은 예정된 step마다 전역 후보 중 최대 하나만 선택하며, 순서는 항상 위와 같다.

이 고정 순서는 사람이 정한 operator ordering이다. 예를 들어 같은 step에서는 화학이 물질 전환보다 먼저, 물질 전환이 막 변화보다 먼저, 막 변화가 ordinary 이동·접촉보다 먼저 적용된다.

## 4. 세 종류의 시간

### 4.1 `ordinary_events`

- outer step마다 정확히 1 증가한다.
- 모든 `interval` 실행 여부를 결정한다.
- 실제 장기 결과의 주 진행 척도다.

### 4.2 `sequence.time`

다음 각각이 실행될 때 1 증가한다.

- face source
- face diffusion
- face absorption
- chemistry
- material
- boundary
- ordinary movement/reaction
- 드물게 spatial energy source/diffusion/absorption

따라서 한 outer step에서 1보다 많이 증가할 수 있다. 반면 cadence는 이 값이 아니라 `ordinary_events`로 결정된다.

### 4.3 벽시계 시간

장기 실행기는 물리 시간이나 사건 수가 아니라 `time.time() < deadline` 동안 실행한다. 따라서 동일한 6시간이어도 세계마다 실행한 사건 수가 다르다.

### 판정

현재 두 정수 clock은 사건 기록 순서와 실행 cadence를 나타내지만, 초·분과 같은 물리적 시간도 아니고 전체 propensity에서 유도된 확률적 대기시간도 아니다.

## 5. ordinary 전역 추첨

`step_spatial_sequence()`의 추첨 폭은 다음 합이다.

```text
4 × sequence site 수
+ 유효 rotation 후보 수
+ 유효 flex 후보 수
+ 모든 sequence reaction 후보의 weight 합
```

### 5.1 이동

- 모든 sequence site마다 상·하·좌·우 4개 후보를 만든다.
- 막힘·세계 경계·점유 충돌 후보도 제거하지 않고 선택 후 실패 사건으로 기록한다.
- 선택된 site가 속한 연결 성분 전체가 이동한다.
- 이동 에너지 비용은 없다.
- 연결 성분 크기가 `N`이면 동일한 성분 이동을 촉발할 site가 `N`개이므로 이동 추첨권이 대략 `N`배다.
- 질량·마찰·확산계수에 따른 크기 보정은 없다.

**판정: 치명적 확장 편향.** 큰 구조가 더 무거워 느려지는 대신 더 많은 site ticket을 가져 전체 이동 시도가 증가한다.

### 5.2 회전

- 충돌이 없고 실제로 가능한 quarter-turn만 후보에 포함한다.
- 후보 하나당 ordinary 추첨 폭 1이다.
- 움직이는 성분 크기와 관계없이 비용은 `SPATIAL_ROTATION_COST = 1`이다.
- 큰 성분을 회전해도 작은 성분과 같은 에너지 비용이다.

### 5.3 굽힘

- 가능한 corner flip만 후보에 포함한다.
- 후보 하나당 ordinary 추첨 폭 1이다.
- 비용은 구조 크기와 관계없이 1이다.

### 5.4 후보 포함 기준 불일치

- 이동은 실패 가능한 시도까지 후보에 넣고 시간을 소비한다.
- 회전·굽힘은 성공 가능한 후보만 넣는다.
- 결합·절단도 사전 조건을 통과한 후보만 넣는다.

따라서 “충돌 시도율”과 “성공 가능한 반응률”이 같은 분모에서 서로 다른 방식으로 표현된다.

## 6. 서열 접촉·골격 사건

기본 물성:

- 네 기호의 두 익명 축: `(-1,-1), (-1,+1), (+1,-1), (+1,+1)`
- 친화도: 두 축 내적의 음수
- `BACKBONE_COST = 2`
- 구조 문맥 배율 상한: `64`

### 6.1 결합·접힘

```text
base weight = 접촉 구간 pair_score 합 = bond_energy
final weight = base weight × structural context multiplier
```

- 양의 접촉만 후보가 된다.
- 형성 시 `bond_energy`만큼 전역 thermal energy가 증가한다.
- 별도 활성화 장벽은 없다.
- 구조 문맥은 결합·접힘·join의 형성률만 높이고 해제에는 같은 방식으로 적용되지 않는다.

### 6.2 결합 해제·풀림

후보 조건:

```text
thermal_energy >= bond_energy
```

가중치:

```text
ideal = 2 × contact length
defect = max(0, ideal - bond_energy)
thermal_factor = thermal_energy - bond_energy + 1
weight = thermal_factor × 2^min(defect, 20)
```

- 전역 thermal energy가 높을수록 모든 공간의 해제가 동시에 빨라진다.
- 불완전 접촉은 defect에 따라 지수적으로 해제 가중치가 증가한다.
- 해제 시 bond energy를 전역 thermal에서 뺀다.

**실측 예시:** seed `123456`, 2,000 ordinary events 후 ordinary 총 추첨 폭은 `941`이었다. 이 중 접촉 해제 후보 하나의 weight가 `790`으로 약 84%를 차지했다.

같은 상태에서:

- 이동 ticket: 116
- 회전: 3
- 결합 후보 5개의 총 weight: 10
- 골격 절단: 3
- ligation 후보 19개의 총 weight: 19
- unbind 후보 1개의 weight: 790

이는 현재 구획과 접촉이 매우 짧게 유지되는 결과에 강한 영향을 준다. 이 식은 기록 가능한 v0 근사이지 다른 사건과 단위가 통일된 물리 rate가 아니다.

### 6.3 골격 결합·주형 join

- 후보 weight 기본값: 1
- 접힘 주머니 안에서는 structural context multiplier가 적용될 수 있다.
- 에너지 비용: 2
- 주형 join은 정확한 두 접촉·완전 결합·인접 위치 등 강한 기하 관문을 요구한다.

### 6.4 노출 골격 절단

- 노출된 모든 절단점 weight: 1
- 절단 시 thermal energy에 2 반환
- 기호 종류와 국소 화학 환경에 따른 안정성 차이 없음

### 6.5 cyclization / cycle opening

- 둘 다 후보 weight 1
- cyclization은 전역 thermal 2 소비
- cycle opening은 전역 thermal 2 반환
- 실제 공간에서는 양 끝이 인접해야 cyclization 가능

### 판정

가역 쌍의 에너지 회계는 존재하지만 형성·해제 사건률은 공통 장벽식이나 detailed balance에서 유도되지 않는다. 특히 weight 1 계열과 열 기반 지수 weight를 직접 경쟁시키므로 결과를 자연적인 반응 우열로 해석할 수 없다.

## 7. face chemistry

실행 주기: ordinary 3회마다 최대 1개 전역 반응.

후보 조건:

- 한 face에 반응식의 최소 반응물 수가 존재함
- 최소량을 넘는 추가 농도는 후보 수와 weight에 반영되지 않음

가중치:

```text
weight = spontaneous_weight(1)
       + catalytic_weight(1) × nearby catalytic pair_score 합
```

반응:

- 네 익명 물질 종류 사이의 질량 보존 변환
- 반응당 정해진 정수 단위만 소비·생성
- 명시적 에너지 소비·방출 없음
- 활성화 에너지 없음
- 정반응·역반응식은 있으나 열역학 평형상수에서 rate가 유도되지 않음

### 확장성 문제

반응 가능한 face가 10개든 1,000개든 ordinary 3회마다 세계 전체에서 최대 1개 반응만 발생한다. 독립적인 공간을 추가하면 기존 face의 반응 선택 확률이 감소한다.

### 농도 문제

한 face에 반응물이 1회분 있든 100회분 있든 후보는 반응식당 하나다. mass-action kinetics가 아니다.

## 8. face material: 응결·용해·침식·복사 연장

실행 주기: ordinary 2회마다 최대 1개 전역 사건.

기본값:

- activation energy: 1
- spontaneous weight: 1
- affinity weight: 1
- dissolution weight: 1

### 8.1 응결

```text
weight = 1 + 주변 기호와의 양의 affinity 합
```

- 특정 종류 용질이 1개 이상 있으면 후보 생성
- 용질량 1과 100이 동일 후보 하나를 만든다.
- 빈 lattice corner마다 후보가 생겨 geometry multiplicity가 rate가 된다.
- face medium energy가 threshold 이상이면 가능하며, 그 이상 에너지 차이는 rate에 반영되지 않는다.

### 8.2 주형 복사 연장

```text
weight = 1 + 새 기호와 주형 기호의 양의 affinity
```

- 모든 네 기호는 가능하며 일치 여부는 결과로만 기록
- 각 기호 용질이 1개 이상이면 후보 하나
- 농도 차이는 반영하지 않음
- activation energy 1 + backbone cost 2 소비
- 양의 affinity이고 주형 자리가 비점유이면 side contact 안정화로 affinity만큼 thermal 증가

### 8.3 용해·침식

- 인접 face마다 후보 하나가 생김
- 후보 weight는 모두 1
- 같은 strand end가 최대 네 인접 face에서 중복 후보를 가져 geometry가 암묵적 rate multiplier가 됨
- 전역 thermal threshold만 사용

### 확장성 문제

공간 전체에서 ordinary 2회마다 최대 한 사건이다. 물질량·부피 증가에 따라 전체 사건률이 비례하지 않는다.

## 9. face boundary: 팽창·수축

실행 주기: ordinary 4회마다 최대 1개 전역 사건.

### 팽창

- cyclic strand의 비접촉 edge와 인접 빈 face 필요
- face energy `>= 2 × BACKBONE_COST`
- 두 새 기호 조합을 모두 열거: 최대 `4 × 4 = 16` 후보
- 각 후보 weight 1
- 두 용질과 에너지 4를 소비

### 수축

- 특정 4-site 형상과 접촉되지 않은 중간 두 site 필요
- 형상당 후보 하나
- weight 1
- 두 기호와 에너지 4를 반환

### 조합 편향

충분한 용질이 있으면 같은 팽창 위치가 기호쌍 16개의 서로 다른 후보로 표현된다. 수축은 같은 형상당 후보 하나다. 따라서 명시적 rate 식이 없어도 후보 개수 자체가 팽창에 최대 16배의 추첨 폭을 줄 수 있다.

반대로 실제 결과에서는 수축·해제 등 다른 채널과 구조 불안정성이 장기 성장을 막는다. 후보 개수를 물리 rate로 해석할 근거가 없다.

## 10. face transport와 확산

실행 주기: ordinary 20회마다 다음 세 전역 sweep을 고정 순서로 모두 수행한다.

1. source/sink
2. medium + solute diffusion
3. material absorption

각 sweep마다 `sequence.time += 1`이다.

### 10.1 source/sink

- 좌상단 source `+8`
- 우하단 sink `-8` 가능한 만큼
- 세계 크기를 바꿀 때 source 밀도나 경계 면적에 따른 scaling 규칙 없음

### 10.2 face medium diffusion

- 모든 face를 한 번에 sweep
- 각 이웃으로 `amount // 8`, `energy // 8` 이동
- barrier가 있으면 차단
- 정수 절삭과 divisor 8은 명시적 수치 근사

### 10.3 solute diffusion

- 열린 edge는 `amount // 8` 이동
- barrier edge는 `min(share, permeability)`
- permeability는 경계 기호 pair_score 합에서 계산
- barrier 통과량은 농도 기반 flux 식이 아니라 cycle당 정수 상한

### 10.4 absorption

- 모든 sequence site가 sweep마다 인접 face에서 최대 에너지 1 흡수
- site 수가 많으면 한 cycle의 총흡수량도 증가

### 확장성 불일치

확산·흡수는 전체 격자 sweep이어서 물질·site 수에 따라 총 변화량이 늘 수 있다. 반면 chemistry·material·boundary는 각 cadence에서 세계 전체 사건 하나로 제한된다. 같은 물리 시간 단위 안에서 extensive scaling 방식이 서로 다르다.

## 11. spatial energy와 medium transport

### 실제 장기 실행 활성 여부

- spatial energy law: 활성, interval `1,000,000`
- medium transport law: 인자로 전달되지 않아 비활성
- face transport: 활성, interval `20`

### spatial energy cycle

interval 도달 시:

1. source/sink 전체 적용
2. field diffusion 전체 sweep
3. material site absorption 전체 sweep

각 단계가 `sequence.time += 1`이다. interval 1,000,000은 물리량에서 유도되지 않은 cadence다.

### 전역 thermal coupling

공간 field와 face medium은 좌표를 가지지만 sequence reaction이 소비·방출하는 `thermal_energy`는 세계 전체 단일 정수다. 멀리 떨어진 결합 형성이 다른 지역의 해제·골격 결합 가능성을 즉시 바꾼다.

## 12. 고정 실행 순서 편향

같은 outer step에서 다음 인과 순서가 항상 고정된다.

```text
face source
→ face diffusion
→ face absorption
→ chemistry
→ material
→ boundary
→ ordinary movement/reaction
```

예:

- 이번 step에서 diffusion으로 도착한 용질은 즉시 chemistry에 사용 가능
- chemistry가 바꾼 용질은 같은 step의 material 후보에 반영
- material 변화는 같은 step의 boundary 후보에 반영
- boundary 변화는 마지막 ordinary 사건에 반영
- 반대 방향의 영향은 다음 outer step까지 기다림

이 순서는 자연스러운 동시성에서 유도되지 않고 구현 순서로 정해졌다.

## 13. 초기·진행 상태 수치 감사

고정 기술 seed `123456`의 후보 inventory다. 이는 자연현상 증거가 아니라 scheduler 구조 진단이다.

### 초기 상태

- sequence sites: 40
- strands: 12
- ordinary pool:
  - 이동: 160
  - 회전: 57
  - 굽힘: 0
  - 골격 절단: 28
  - 총 추첨 폭: 245
- chemistry pool:
  - 후보: 72
  - 총 weight: 108
- material pool:
  - 응결 60, 용해 32, 침식 32
  - 총 weight: 130
- boundary 후보: 0

### 2,000 ordinary events 후

- sequence sites: 29
- strands: 25
- thermal energy: 791
- ordinary pool 총 추첨 폭: 941
  - 이동 116
  - 회전 3
  - 결합 총 weight 10
  - 절단 3
  - ligation 19
  - unbind 1개, weight 790
- chemistry 후보 323개, 총 weight 483
- material 후보 163개, 총 weight 197
- boundary 후보 0

### 판정

동일한 한 추첨 폭에서 “이동 시도 한 개”, “유효 회전 한 개”, “결합 에너지 한 단위”, “열 기반 해제 weight 한 단위”가 같은 단위처럼 더해진다. 공통 사건률 차원은 정의되어 있지 않다.

## 14. 벽시계 종료 편향 실측

### gcp1-breadth: 동일 6시간, 64세계

- ordinary events 최소: `1,340,894`
- 중앙값: `1,357,331.5`
- 최대: `2,539,181`
- 최대/최소: `1.89배`
- 중앙 처리량: 약 `226,222 events/hour`

### gcp2-depth: 동일 32시간, 12세계

- 최소: `6,383,363`
- 중앙값: `6,399,080`
- 최대: `6,416,680`
- 최대/최소: `1.005배`
- 중앙 처리량: 약 `199,971 events/hour`

### 판정

벽시계 실행은 고정된 계산 예산 실험이지 고정 물리시간 실험이 아니다. gcp1의 1.89배 편차 원인이 구조 복잡도, OS scheduling, 후보 열거 비용 중 무엇인지 현재 결과만으로 분리할 수 없다. 그러나 세계별로 노출된 사건 수가 크게 달랐다는 사실은 확실하다.

후보 생성에는 다음 고비용 구조가 있다.

- 모든 strand 쌍과 모든 displacement 결합 검사
- 한 strand 안의 여러 시작점·길이 접힘 검사
- 모든 site × 4 이동 후보
- 회전마다 연결 성분과 충돌 재계산
- material 복사 후보에서 strand end × 모든 template site × 양방향 × 네 기호 검사

따라서 구조가 달라지면 wall-clock당 사건 수가 달라질 수 있다. 복잡한 구조가 계산이 느려져 더 적은 붕괴 사건에 노출되는 “계산 비용에 의한 가짜 안정성” 가능성을 배제할 수 없다.

## 15. 과거 문서와 현재 코드의 관계

### 15.1 이미 기록된 병목

`EVOLVABLE_LANGUAGE_PLAN.md`와 `STAGE_C_JOIN_BOTTLENECK_REVIEW.md`는 다음을 이미 기록했다.

- 접촉 동시성 부족
- join weight 1과 해제 가중치 공식의 경쟁 편향
- 공통 에너지 장벽 사건률 필요

이 지적은 여전히 현재 `substrate.py` 가중치 계통에 적용된다.

### 15.2 이미 해소된 이전 병목

`STAGE_C_LOCAL_DYNAMICS_V1_REVIEW.md`의 “공간 없는 완전 혼합”은 이후 2차원 위치·장벽·국소 이동을 추가하면서 현재 active spatial path에서는 제거됐다.

따라서 “이전 완전 혼합 문제를 그대로 방치했다”는 표현은 부정확하다. 그러나 공간을 추가한 뒤에도 전역 후보율과 시간 확장성을 별도로 감사하지 않은 것은 사실이다.

## 16. 기존 실험의 유효 범위

### 유효

- 현재 scheduler-v1 법칙 아래 실제 발생한 사건
- 물질·매질·에너지 보존
- seed 재생 가능성
- 관찰기 비개입
- 분할이 `fold → unfold`인 원인
- 독립 경계 분열과 후손이 0회였다는 사실

### 주장 금지

- 현실적인 물리 시간 동안의 발생률
- 넓은 공간에서의 지역별 독립 사건률
- 여러 세포 생태가 충분히 시험됐다는 주장
- 구획이 적은 이유가 자연적 진화 결과라는 주장
- 복잡한 구조의 유지시간이 계산 비용과 독립적이라는 주장
- scheduler-v1과 향후 scheduler-v2 결과의 직접 합산

## 17. 심각도 분류

### BLOCKER — 다음 과학 실험 전에 수정

1. 물리시간과 propensity가 없는 전역 event clock
2. 서로 다른 단위의 ordinary 후보 가중치 혼합
3. wall-clock 종료로 인한 세계별 사건 노출량 차이
4. chemistry/material/boundary의 세계당 고정 최대 사건 수
5. 전역 thermal energy에 의한 원거리 즉시 결합

### HIGH — scheduler-v2와 함께 수정

6. component size에 비례하는 이동 ticket
7. 이동 실패 후보와 다른 유효 후보의 포함 기준 불일치
8. 농도와 무관한 chemistry/material 후보율
9. 화학 반응의 에너지 회계 부재
10. 고정 operator ordering
11. 팽창 16조합 대 수축 1후보의 암묵적 multiplicity
12. 구조 크기와 무관한 회전 비용

### MEDIUM — 근사로 명시하고 수렴 검사

13. 정수 diffusion divisor와 절삭
14. 2차원 격자
15. 네 기호의 고정 pair_score 물성
16. 구조 문맥 multiplier와 상한 64
17. 고정 source 위치·세기

### 별도 기능 BLOCKER

18. 하나의 순환 경계를 두 독립 순환 경계로 만드는 scission + closure 경로 부재

이 항목은 scheduler 문제와 별개다. 시간계를 고쳐도 독립 세포 분열 사건이 자동으로 생기지는 않는다.

## 18. scheduler-v2 요구사항

### 18.1 상태

- `event_index`: 기록 순번, 정수
- `physical_time`: 실제 스케줄의 연속시간
- 각 후보의 `propensity`: `1 / physical_time` 단위
- 국소 energy/temperature field
- 후보가 참조하는 위치·물질·에너지 범위

### 18.2 다음 사건 선택

정확 SSA 출발안:

```text
A = 모든 후보 propensity 합
Δt = -ln(U_time) / A
후보 i 선택 확률 = propensity_i / A
physical_time += Δt
후보 i 실행
영향 지역의 propensity만 재계산
```

사건을 하나씩 순차 실행해도 된다. 핵심은 독립 영역이 추가될 때 전체 propensity가 증가하고 지역별 propensity는 유지되는 것이다.

### 18.3 rate law 원칙

- 가역 반응은 같은 에너지 장벽 체계에서 정·역률을 유도
- 농도·가용 분자 수·기하 degeneracy를 명시적으로 분리
- 후보 중복 개수와 물리 degeneracy를 구분
- movement는 connected component당 rate를 부여하고 크기 의존 확산계수를 명시
- thermal energy를 국소 field로 이동
- chemistry는 mass-action 또는 명시적으로 선택한 대체 kinetics 사용
- 환경 source·diffusion은 physical time에 따른 flux로 표현
- 임시 상수는 단위·근거·민감도 범위를 문서화

### 18.4 고정 순서 제거

선택지:

1. 모든 확률 사건을 하나의 propensity queue에 통합
2. diffusion처럼 결정론적 근사가 필요한 경우 physical-time operator splitting을 사용하고 시간 간격 수렴 검사를 수행

같은 step 내부의 숨은 우선순위를 두지 않는다.

## 19. 필수 검증 관문

### G1. 독립 영역 extensive scaling

동일하고 상호작용하지 않는 영역을 1개, 2개, 4개 배치한다.

- 전체 사건률은 영역 수에 비례
- 각 영역의 사건률 분포는 동일
- 한 영역 추가가 기존 영역의 과정 속도를 늦추지 않음

### G2. 빈 공간 불변성

물질 배치는 그대로 두고 빈 격자만 확장한다.

- 기존 지역 propensity 불변
- source 경계조건을 제외한 지역 동역학 불변

### G3. 농도 스케일링

반응물 수를 1배, 2배, 4배로 바꾼다.

- 선택한 kinetics 법칙의 예측에 맞게 rate 변화
- 단순 존재 여부만 반영하는 결과 금지

### G4. 가역 반응 평형

닫힌 작은 세계에서 정·역반응을 장기 실행한다.

- 에너지 보존
- 초기 조건 여러 개가 같은 명세상 평형 분포에 접근
- rate 상수 변경 시 예상 방향으로 평형/완화시간 변화

### G5. component 이동

크기 1, 2, 4, 8의 구조를 둔다.

- 이동률의 크기 의존식을 사전에 명시
- site 수만큼 중복 ticket이 생기지 않음
- 회전 비용과 이동한 질량의 관계 검증

### G6. event replay

- event selection 난수와 Δt 난수를 모두 기록
- 모든 physical_time과 상태 해시 재생
- 관찰기 ON/OFF 동일

### G7. 실행 종료 불변성

- wall-clock은 성능 예산으로만 사용
- 과학 결과는 고정 physical_time 또는 사전 정의된 event exposure로 비교
- 중간 종료 세계는 불완전 결과로 보존

### G8. 구현 독립성

- 전역 재계산 버전과 국소 캐시 버전의 사건·시간·최종 상태 동일
- 독립 사건 병렬 batch는 합법적인 순차 순서와 동일할 때만 허용

### G9. 독립 막 분열

- 부모 경계 1개에서 자식 cyclic strand 2개 생성
- 두 자식이 같은 strand ID를 공유하지 않음
- 모든 절단·봉합에 물질·에너지 회계
- 열린 경계·재융합·붕괴 실패도 허용

## 20. 실제 장기 실행 사건 전수 대조

두 GCP cohort 합계 `182,147,661` ordinary events에서 실제 기록된 event type은 다음 24개다. 모든 종류가 위 감사의 ordinary·face material·chemistry·boundary·transport·energy 범위에 포함됐음을 확인했다.

| event type | 횟수 |
|---|---:|
| `sequence.spatial_move` | 160,720,086 |
| `sequence.face_reaction` | 60,715,841 |
| `sequence.face_material_condense` | 45,497,635 |
| `sequence.face_material_dissolve` | 40,668,875 |
| `sequence.face_energy_sources` | 9,107,347 |
| `sequence.face_medium_diffusion` | 9,107,347 |
| `sequence.face_collision_absorption` | 9,107,347 |
| `sequence.spatial_rotate` | 7,040,916 |
| `sequence.backbone_ligate` | 6,887,003 |
| `sequence.face_material_erode` | 4,868,861 |
| `sequence.unbind` | 2,683,187 |
| `sequence.bind` | 2,665,911 |
| `sequence.backbone_cleave` | 2,058,634 |
| `sequence.spatial_flex` | 82,294 |
| `sequence.face_material_extend` | 38,409 |
| `sequence.backbone_cycle_open` | 2,514 |
| `sequence.backbone_cyclize` | 2,514 |
| `sequence.fold` | 2,301 |
| `sequence.unfold` | 2,301 |
| `sequence.face_boundary_expand` | 240 |
| `sequence.face_boundary_collapse` | 215 |
| `sequence.environment_energy_sources` | 150 |
| `sequence.environment_energy_diffusion` | 150 |
| `sequence.environment_energy_absorption` | 150 |

`backbone_join`은 현재 장기 결과에서 발생하지 않았다. 후보 생성 경로와 weight 1 규칙은 코드 감사 범위에 포함했다. `medium transport`는 장기 실행 인자로 전달되지 않아 비활성이었으며 코드 구조만 별도 감사했다.

## 21. 구현 순서

1. scheduler-v1 코드와 결과를 동결하고 버전 라벨 부여
2. 현재 모든 상수를 단위·근거·민감도로 분류
3. 최소 SSA scheduler와 `physical_time` 타입 구현
4. 이동·접촉·골격 가역률을 공통 장벽식으로 이전
5. chemistry/material 농도 기반 rate 이전
6. face transport를 physical-time flux로 이전
7. 전역 thermal을 국소 energy field로 이전
8. G1~G8 통과
9. 독립 막 scission + closure를 기존 공통 결합 법칙으로 추가
10. G9 통과
11. 작은 로컬 무개입 세계 실행
12. 결과를 모르는 seed를 사전 봉인한 뒤에만 새 장기 실험 검토

## 22. 최종 판정

현재 엔진은 “한 번에 사건 하나를 실행해서 여러 구조가 존재할 수 없는 엔진”은 아니다. 여러 구조는 공존할 수 있고 사건 기반 순차 실행 자체도 정당한 방법이다.

정확한 문제는 다음이다.

> 전역 후보 하나를 선택하면서 전체 propensity에 따른 물리시간을 계산하지 않고, 서로 다른 공식의 가중치와 고정 cadence를 섞으며, 벽시계로 실행을 종료한다. 따라서 세계 크기·물질량·구조 복잡도가 바뀔 때 지역별 물리 속도가 보존되지 않는다.

이 문제를 해결하기 전에는 더 긴 실행이 물리적 시간의 증가를 뜻하지 않는다. 다음 작업은 발생 확률을 임의 조정하는 것이 아니라, 모든 현상을 같은 시간·에너지·농도 단위 아래 놓는 scheduler-v2를 만드는 것이다.
