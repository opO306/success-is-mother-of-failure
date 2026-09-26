# 결정론 A · 진화형 B 다음 구현 순서 v1

**문서 분류: 역사 / 과거 설계·실측 기록.** 본문의 “현재”, “다음”, 시험 개수와 후보는 기록 당시의 상태다. 현재 작업 지시나 새 동결 판정으로 읽지 않는다.
현재 상태는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 본다.


> **역사/과거 설계·연구 자산 안내 (2026-09-27):** 아래 본문의 “현재”, “다음”, 구현 순서는 문서 작성 당시의 기록이다. 현재 우선순위와 활성 Gate는 [CURRENT_STATE.md](../../CURRENT_STATE.md)를 따른다.
> A가 최우선이며 L은 A의 기반이 충분한 뒤 자연 발생·진화 계통으로 진행한다. B 본격 개발은 A와 L 기반의 작은 세계가 돌아가는 후기 단계로 보류하며 취소·폐기하지 않는다. 기존 B-classic 구현·문서·시험은 비교군/연구 자산으로 보존한다.
> 아래의 B 설계·세계 제작 역할이나 A/B 동시 개발 제안은 과거 구상이며 현재 작업 지시·권한이 아니다. 현재 A/B 경계는 RULES·헌법을 따른다. 이 안내는 본문 계약이나 시험 의미를 변경하지 않는다.

상태: 구현 순서 설계\
기준 문서: [DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md](DETERMINISTIC_WORLD_LANGUAGE_DEEP_DESIGN_V1.md)

## 1. 현재 완성된 것

### B0 설계 문법

- 결정론 세계 JSON 명세
- 허용된 필드만 통과
- 생명·적합도·본능 같은 직접 명령 거부
- 난수 seed와 부동소수점 거부
- 안정적인 설계도 해시

### A0 CPU 기준 세계

- 64×64 정수 격자 예제
- 방향을 가진 입자 이동
- 무작위 없는 정면충돌
- 물질 수와 운동 방향 합 보존
- 같은 초기 상태 100회 동일 결과
- 평행이동·90도 회전 대칭
- 관찰 주기가 물리에 영향 없음

### 아직 없는 것

- 저장 에너지
- 결합과 분리
- 실제 화학
- 자원과 환경
- 고분자와 막
- GPU 실행기
- B 월드 모델
- AI B-Architect

## 2. 첫 번째로 만들 것

첫 구현 묶음은 **B0.1 인과 규칙 언어 + A1 에너지·결합 물리**다.

둘을 함께 만드는 이유:

- A만 먼저 만들면 B가 코드를 직접 해석해야 한다.
- B만 먼저 만들면 실제로 예측하고 검증할 세계가 없다.
- 물리 규칙과 그 규칙의 원인·결과 설명을 같은 시점에 만든다.

```text
B0.1 설계도:
이 충돌은 무엇을 요구하고 무엇을 바꾸는가

A1 실행기:
그 조건을 실제 입자 상태에 적용

검증기:
물질·에너지·운동량이 맞는지 확인
```

## 3. 1단계 — 물리 단위와 불변 헌법

### 만들 것

모든 A 규칙이 공통으로 사용하는 최소 단위를 정한다.

- 질량: 정수
- 위치: 격자 좌표
- 방향: 이산 방향
- 운동량: 질량 × 방향 속도
- 운동에너지: 정수 단위
- 저장 에너지: 입자 또는 결합에 보관
- 열: 지역별 정수 에너지
- 물리시간: 고정 tick

### 중요한 결정

에너지는 세계 전체 통장 하나로 두지 않는다.

```text
입자의 운동에너지
결합에 저장된 에너지
해당 지역의 열에너지
외부 유입·유출 장부
```

로 나눈다.

### 통과조건

- 닫힌 세계에서 총질량 불변
- 닫힌 세계에서 총에너지 불변
- 외력이 없으면 총운동량 불변
- 에너지 위치를 추적할 수 있음
- 멀리 떨어진 지역이 즉시 에너지를 공유하지 않음

## 4. 2단계 — B0.1 인과 규칙 언어

### 목적

B가 A의 소스 코드를 읽지 않아도 물리 규칙의 원인과 결과를 이해하게 한다.

각 규칙은 다음을 선언한다.

```text
rule_id
적용되는 작은 공간 범위
필요한 물질 상태
필요한 방향과 접촉
필요한 에너지
소비되는 것
생성되는 것
이동하는 에너지
실패 조건
역반응 규칙
보존해야 하는 양
```

### 예시

```text
규칙: opposite_collision

조건:
- 같은 위치
- 반대 방향으로 접근
- 같은 물질 종류

결과:
- 입자 수 유지
- 진행 방향 직각 전환
- 운동량 유지
- 에너지 유지

실패:
- 반대 방향이 아니면 그대로 통과
```

### 금지

- 성공 확률
- fitness 증가
- 생존 보너스
- 세포 분열 명령
- 완료 진행률
- 실행 중 결과를 보고 규칙 변경

### 통과조건

- 모든 실행 규칙에 인과 설명 존재
- 규칙에 선언되지 않은 상태 변경 불가
- 소비량과 생성량 자동 대조
- 역반응이 필요한 규칙은 대응 규칙 확인
- B가 규칙의 영향을 기계적으로 읽을 수 있음

## 5. 3단계 — A1 결정론적 에너지·결합

### 입자 상태 확장

```text
물질 종류
질량
위치
방향
운동에너지
방향성 결합면
결합에 저장된 에너지
```

### 결합 과정

```text
두 입자가 실제로 접근
→ 결합면 방향 확인
→ 활성화 에너지 확인
→ 충돌 에너지 일부가 결합에 저장
→ 나머지는 지역 열로 이동
→ 실제 결합 구조 생성
```

### 분리 과정

```text
결합에 충분한 지역 에너지 전달
또는 실제 충격
→ 결합 절단
→ 저장 에너지와 운동량 재분배
→ 입자 분리
```

확률표는 없다. 같은 상태는 항상 같은 결과를 만든다.

### 실패도 실제 결과

- 방향 불일치
- 에너지 부족
- 이미 사용 중인 결합면
- 공간 부족
- 불안정한 중간 구조

### 통과조건

- 결합 전후 물질·에너지·운동량 보존
- 분리 전후 동일 회계
- 결합과 분리의 반복 재현
- 멀리 있는 물질은 반응하지 않음
- 큰 구조가 구성원 수만큼 이동권을 얻지 않음
- 동일 초기 상태 완전 동일

## 6. 4단계 — B 월드 모델 v0

이 단계의 B 월드 모델은 신경망이 아니다. 먼저 정확한 규칙 지도부터 만든다.

### 구성

#### 상태 지도

- 어떤 물질이 어디에 있는가
- 어떤 결합이 존재하는가
- 에너지가 어디에 저장돼 있는가

#### 인과 지도

```text
충돌
→ 에너지 전달
→ 결합 생성
→ 이동 가능한 구조 변화
```

#### 예상기

A를 실행하기 전에 최소한 다음을 계산한다.

- 보존 가능 여부
- 규칙 사이 충돌
- 도달 불가능한 상태
- 필요한 메모리
- 한 tick의 계산량

#### 오차 기록

```text
B의 예상
A의 실제 결과
차이
예상이 틀린 원인
```

### 통과조건

- B 월드 모델이 A를 수정하지 않음
- A 실행 전 보존 위반 설계를 거부
- 간단한 1~10 tick 결과를 정확히 예측
- 장기 결과는 확신 대신 미확인으로 표시
- 예상과 실제 차이를 archive에 저장

## 7. 5단계 — 여러 뇌가 사용하는 외부 B 경계 규격

B 월드 모델은 특정 트랜스포머에 종속되지 않는다. 기존 LLM, 인과 그래프, 규칙 탐색기, 공간 모델, opaque latent, 향후 독자 신경망은 서로 다른 관측 view와 내부 표현을 사용할 수 있다.

공통화할 것은 내부 사고 과정이 아니다.

```text
CapabilityManifest       무엇을 할 수 있는가
ObservationContract      무엇을 보고 무엇을 보지 못했는가
ClaimSet                 외부에 무엇을 주장하는가
EvidenceBridge           그 주장을 어떻게 반증·확인하는가
BoundaryEvaluation       실제 A·외부 자료에서 무엇이 맞고 틀렸는가
```

`WorldIntent`, `WorldState`, `CausalMap`, `Prediction`, `PlanCandidate` 등은 선택적 공용 어휘다. 모든 뇌가 이를 중간 표현으로 만들 필요는 없다. 새로운 claim kind나 표현도 외부 검증 연결을 제출하면 허용한다.

### 통과조건

- 서로 다른 내부 표현과 관측 view를 선언할 수 있음
- 같은 추론 trace나 정공법을 요구하지 않음
- 검증 가능한 주장은 외부 `EvidenceBridge`를 가짐
- exact·measured·author-reported·approximate·hypothesis·unknown을 구분
- 자연어 설명 없이도 최종 claim과 반증 조건을 교환 가능
- opaque latent를 원시 사실로 승격하지 않음
- 다수결을 사실 판정으로 사용하지 않음

### 현재 구현

- `b-language-boundary-v1` Python 계약과 JSON Schema
- `BrainAdapter` Protocol과 capability manifest
- exact B 월드 모델을 `ExactOracleAdapter`로 연결
- A2.3 4 tick state claim 전부 verified
- 틀린 claim은 A를 바꾸지 않고 falsified로 기록
- `WorldState`·`CausalMap` 없는 opaque·새 질문 claim 허용
- schema SHA-256 `822749bd506bf014ae3ff724c2b3057d51d6899d72015c1addc48d80ebaaeb38`
- exact exchange SHA-256 `5049438157b3de9926451425a13646fc032fd9aa858ea1007be6fa650dde371a`
- 첫 독립 후보 `CognitiveMapAdapter` 구현: A 전환·forecast 함수 호출 없음
- 1,024칸 중 관련 상태 7칸을 저장하는 희소 지도
- 지역 상태·최단경로·제한 단계 도달성 질의 5개 모두 verified
- 동일 최소 길이의 다른 우회 경로도 정답으로 인정, 불필요한 긴 경로는 falsified
- Cognitive Map benchmark SHA-256 `b9d201342ece0bb056d0e07da3e0cbdf71ae384a587df706956e5e9c4622c696`
- 전체 프로젝트 테스트 `790`개 통과

## 8. 6단계 — A2 환경 field

에너지·결합이 안정된 뒤 환경을 추가한다.

### 추가할 것

- 지역 열
- 물 또는 매질 흐름
- 용질 이동
- 광물 표면
- 빛과 외부 에너지
- 공급·고갈·침전

### 원칙

```text
환경 변화
→ 지역 물질과 에너지 변화
→ 실제 충돌과 반응 변화
```

환경이 사건 확률을 직접 조정하지 않는다.

### 통과조건

- 닫힌 환경 보존
- 열린 환경 유입·유출 장부
- 자원 1·2·4배에서 충돌 빈도 변화 설명 가능
- 독립 지역을 추가해도 기존 지역 속도 불변
- 격자 크기·회전·평행이동 검사

## 9. 7단계 — GPU 동등 실행기

GPU는 A2까지 상태 형식이 안정된 뒤 붙인다.

먼저 붙이지 않는 이유:

- 물리 상태가 계속 바뀌면 CPU와 GPU를 동시에 고쳐야 함
- 잘못된 물리를 더 빠르게 계산할 위험
- 원인 추적이 어려워짐

### 통과조건

- CPU와 GPU 매 tick 상태 해시 동일
- 물질·에너지·운동량 동일
- 실행 순서 차이 없음
- GPU thread 경쟁으로 결과가 달라지지 않음

## 10. 8단계 — 결정론 화학과 고분자

### 추가할 것

- 여러 단계 중간 반응물
- 방향성 화학 결합
- 실제 촉매 구조
- 고분자 결합과 절단
- 구조 접힘
- 주형 근처의 결정론적 복사

### 통과조건

- 복사 성공 확률 없음
- 실제 물질 도착 순서가 복사 결과 결정
- 중간에 정지·후퇴·붕괴 가능
- 촉매는 실제 경로를 제공하며 반응 후 회수 가능
- 변이는 실제 충돌 역사로 설명 가능

## 11. 9단계 — 경계와 독립 분열

### 추가할 것

- 경계 물질
- 선택적 통과
- 내부와 외부
- 경계 성장
- 두 지점 절단
- 네 끝 재결합
- 두 독립 순환 경계

### 통과조건

- 자식 둘이 같은 경계 구조를 공유하지 않음
- 분열 명령 없음
- 실패·누출·재융합·붕괴 허용
- 모든 물질과 에너지 회계

## 12. 10단계 — 초기 지구 환경군

결정론 화학이 작동한 뒤에 구성한다.

### 먼저 조사할 것

- 열수구
- 얕은 연못과 건습 반복
- 화산성 해안
- 다공성 광물
- 얼음 아래 농축 환경

### B의 역할

- 공개 연구 범위 수집
- 확실한 값과 불확실한 값 분리
- 여러 환경 명세 생성
- 모든 환경을 실행 전에 봉인

### 통과조건

- 하나의 정답 지구를 주장하지 않음
- 환경 범위마다 출처 존재
- 생명이 나온 환경만 선택하지 않음
- Earth-analogue와 Open-world 결과 분리

## 13. 11단계 — B-Architect v0

이때 기존 LLM을 임시 설계자로 연결한다.

### 역할 분리

- 자연어 해석
- 물리 요구사항 분해
- 연구자료 조사
- A 설계 제안
- 반대 검토
- B0.1 명세 작성

### 고정 프로그램이 맡는 것

- 보존 검사
- 금지 명령 검사
- CPU·GPU 동일성
- 실행 승인
- 기록 해시

### 통과조건

- LLM이 검증기를 우회할 수 없음
- 같은 공용 B 규격으로 여러 LLM 비교
- 보지 않은 설계 요청으로 외부 평가
- 생명 발생 빈도를 설계 점수로 사용하지 않음

## 14. 12단계 — B 학습과 자기개조

충분한 설계·실패 archive가 쌓인 뒤 시작한다.

### 순서

1. 외부 기억 검색으로 경험 재사용
2. 여러 뇌 후보 비교
3. 충분한 데이터 이후 제한적 학습
4. 자기관찰 모듈 추가
5. 복제본 B'에서만 구조 변경
6. 외부 평가와 인간 승인

### 통과조건

- 성공뿐 아니라 실패를 학습
- 자기 생성 자료만 반복 학습하지 않음
- 트랜스포머 이외 후보도 같은 조건으로 평가
- B가 헌법·평가기·기록기를 수정할 수 없음
- 현재 성능과 후손 설계 능력을 분리 평가

## 15. 실제 작업 단위

### 작업 묶음 1 — 완료

완료 내용:

- 물리 단위 명세
- B0.1 `CausalRule` 문법
- 지역 에너지 장부
- 결정론적 결합·분리
- 보존·대칭·재현 테스트
- 같은 위치의 열만 결합 분리에 사용
- 독립된 두 위치에서 같은 tick 결합 가능
- 입자 ID를 바꿔도 물리 결과 동일

검증:

- 결합 수 `0 → 1 → 0`
- 전 tick 총에너지 `6` 유지
- 전 tick 총운동량 `(0, 0)` 유지
- 동일 실행 해시 반복 일치
- 전체 프로젝트 테스트 `689`개 통과

**완료 데모:** 두 입자가 접근해 조건에 따라 항상 결합하고, 해당 위치의 열에 의해 항상 같은 방식으로 분리된다.

### 작업 묶음 2 — 완료

완료 내용:

- B 월드 모델 v0
- 최대 10 tick 읽기 전용 예측
- A1 결합 물리의 조건·결과·보존 지도
- 결합 생성·분리·입자 이동·지역 열 변화 예상
- A2/A2.1 열·물·용질 이동과 광물 용해·침전의 인과 지도
- 환경의 원시 자원량과 통합 보존 재고를 함께 예상
- 예상과 실제 A checkpoint 자동 비교
- 잘못된 설계 해시와 상태 해시 불일치 탐지
- 여러 모델이 읽을 수 있는 구조화된 예측·평가 형식

검증:

- A1 예제 4 tick 예상과 실제 결과 전부 일치
- A2.1 예제 6 tick 예상과 실제 결과 전부 일치
- 보존된 A2 v1 예제 8 tick 예상과 실제 결과 전부 일치
- 환경 규칙 사건 6종을 기계 판독 지도에 기록
- 예상이 A 명세와 상태를 수정하지 않음
- 난수·seed 인터페이스 없음
- 동일 forecast 반복 해시 일치
- 전체 프로젝트 테스트 `726`개 통과

한계:

- 현재 v0는 A1/A2.1의 정확한 규칙을 읽기 전용 복제 상태에서 실행하는 모델
- 학습형·독립 근사 모델이 아니므로 자기 예측 능력의 우수성을 증명한 것은 아님
- 예측·평가·archive 계약을 먼저 확정한 단계

**완료 데모:** B가 결합과 지역 환경 변화의 결과를 실행 전에 예상하고 A 결과와 자동 비교한다.

### 작업 묶음 3 — A2.3 CPU·GPU field 기준 완료

완료 내용:

- 위치별 열·물·광물·용질 환경
- 높은 수면에서 낮은 수면으로 결정론적 물 이동
- 흐르는 물 단위가 제한된 용질을 함께 운반
- 남은 용질의 이웃 간 확산
- 같은 위치의 열·물·광물·용질에 따른 고온 용해와 저온 침전
- 용해 시 지역 열을 화학 저장 에너지로 이전하고 침전 시 다시 방출
- 액체 물과 수증기의 지역 상변화
- 수증기의 이웃 간 결정론적 확산
- 증발 시 지역 열을 잠열로 저장하고 응축 시 다시 방출
- 위치별 고정 외부 에너지 공급과 지역 열 한도 내 제거
- 내부·공급·제거·상쇄 회계 에너지의 누적 장부
- 지형 경계의 직접 이동 차단
- 겹치지 않는 이웃쌍 네 단계 처리
- 서로 먼 두 열 지역의 같은 tick 독립 변화
- 물·통합 물질 재고·총에너지 보존
- 동일 환경 실행 반복 해시 일치
- A2 v1 명세·실행 해시 호환성 유지

검증:

- A2 v1 8 tick 동안 물 `16`, 광물 `12`, 용질 `[6, 6]`, 총에너지 `10` 유지
- A2.1 v2 6 tick 동안 물 `12`, 통합 물질 재고 `[10, 2]`, 총에너지 `12` 유지
- A2.1에서 광물 `4 → 5`, 대응 용질 `6 → 5`로 형태가 변해도 통합 재고 보존
- A2.2 v3 6 tick 동안 액체+수증기 `8`, 통합 물질 재고 `[2, 0]` 유지
- A2.2 외부 공급 `24`, 제거 `2`, 최종 내부 에너지 `32`에서도 상쇄 회계 에너지 `10` 유지
- B 환경 월드 모델의 A2.2 1~6 tick 예상과 실제 결과 전부 일치
- A2 v1과 A2.1 v2의 기존 명세·실행 해시 유지
- 32·64·128 격자에서 동일 국소 실험 서명 완전 일치
- 16·32·64 해상도에서 두 tick 배율 가설 모두 정규화 차이 감소 경향 관찰
- 칸 길이와 tick 시간의 물리 단위 대응이 없어 수렴 판정은 `not-established`로 보존
- 512×512 CPU 4 tick 약 `16.83`초, 물 `20`, 통합 물질 재고 `[12, 4]`, 에너지 `40` 유지
- 수렴 감사 digest `0c8a52621d4377b94b5b0ce8bcbf84906a8a4fc079a8f7ffa31f1216c90be954`
- 보존 파일 SHA-256 `2243309f89d02d20f646973f000f40be104d7e71df3f1e52db7d9b8a751e1f59`
- B0.2 기준 영역 `64 pm`, 비교 시간 `16 fs`, 해상도 `16·32·64`
- 열 flux의 `D·Δt/Δx² = 1/4`를 모든 해상도에서 정확한 유리수로 유지
- 세 해상도 모두 열 에너지 `65,536` 보존, 연속 차이 감소로 `candidate-converging`
- 낮은 에너지 밀도 시험의 미세 격자 정수 절삭 실패를 `rejected-low-density`로 보존
- B0.2 contract digest `da4573065438d9936158d8bc328d2f54e61637b97c9c9541812db585602bc8d8`
- B0.2 audit digest `448b488b20ae362a1918da86e2c318fe782d5200b7b849eb26abe351a8150a7f`
- B0.2 보존 파일 SHA-256 `9a229c7998d24f7b4dcb134d641eef2a2fb09c88ed8eeeede32eb9be461102cc`
- A2.3 v4에서 열·물 표면·용질·수증기 이동을 동일한 물리 flux 계약에 통합
- 물 이동 시 원래 물의 용질 비율에 따른 정수 운반
- 네 채널 모두 세 해상도에서 물리량 `65,536` 보존과 연속 차이 감소
- 네 채널 판정 `candidate-converging`, 전체 후보 판정 true
- A2.3 B 예상과 실제 1~4 tick 완전 일치
- A2.3 spec digest `728195e4ab88dc2b58da27f0ab2cf2c4bde266045a151e7f0ec0d73078bc074b`
- A2.3 run digest `a7046ae5352c193106f333e5e673ddd0ba7b5afdc29d6fa51e0b0bdddd52ef39`
- A2.3 forecast digest `87d786a32962d16e0ae4a1b0cd61dae9d9d8853729b27f65c67b6502f12ff78d`
- 전체 채널 감사 digest `5b8388a8e1944c966dd3e8eac49092b6cd2c341f04c8aa287769b8dbb98387ff`
- 전체 채널 감사 파일 SHA-256 `8192b606f0a5f176bb85121496cb5b980a30ca3fe592a9caa581d216016a8b71`
- A2 v1·A2.1 v2·A2.2 v3 명세와 실행 해시 유지
- RTX 4060에서 CUDA int64 열·물·용질·수증기 transport 실행
- 겹치지 않는 이웃쌍 직접 대입으로 atomic·scatter reduction 미사용
- v4 예제 CPU·CUDA 1~4 tick 상태 해시 각각 완전 일치
- 네 채널 단독 세계와 외부 에너지·상변화 6 tick 세계도 완전 일치
- CUDA parity 보고서 SHA-256 `e39825eb311fc51352c3fdd02017f5a94a7c2ddf50904507a7e38a1f1123245d`
- 순수 v4 field 상태를 GPU에 여러 tick 상주시켜 최초 업로드·최종 회수만 수행
- 검증 모드에서 상주 상태의 CPU·GPU 1~4 tick digest 완전 일치
- 성능 모드에서 64² `2.34×`, 128² `3.60×`, 256² `3.80×`, 512² `3.90×` CPU 대비 속도
- 512² 4 tick GPU peak memory `46,538,752` bytes, 최종 digest 일치
- 성능 수치는 물리 상태·run digest와 분리
- GPU 상주 성능 보고서 SHA-256 `e6b004eec8b2700c06119cc5cfc742c0269c4f5b8efc107d788d37664a5b98eb`
- 전체 프로젝트 테스트 `774`개 통과

남은 내용:

- 초기 지구 근거에 따른 실제 환경 수치와 환경군
- 여러 광물 종류와 표면별 결합 성질
- 현재 기준 단위를 초기 지구 근거 값과 연결
- 장기 외부 에너지 공급·제거 균형 검사
- 선택적 후속 최적화: 결합·광물 전환·상변화의 GPU 동등 구현
- 선택적 후속 최적화: 장기 상주 상태의 checkpoint 비용 감소


### 작업 묶음 3.5 — 사용자 전용 A/B 인과 행동 계보 완료

완료 내용:

- `private-causal-provenance-v1` append-only SHA-256 hash chain
- A의 매 tick 시작·commit 전체 snapshot
- 매 tick causal·환경 4 phase·외부 에너지·광물·상변화 8개 stage 전체 snapshot
- 모든 stage의 변경 전·후 digest와 무손실 delta
- B의 capability·observation·claim·evidence·evaluation 전체 경계 행동
- 원시 vault 경로를 B 메시지에 넣지 않음
- HDD 사용률 70%·85%·95% 알림, 자동 삭제 없음
- trace 파일·chain·delta·snapshot·최종 상태 독립 재검증

실제 검증:

- HDD `D:`: 931.51GB, 실행 전 여유 약 712.36GB, 상태 Healthy
- vault `D:\KiroCrewTraceVault\success-is-mother-of-failure`
- vault root ACL 상속 차단, 현재 사용자 SID 단독 FullControl
- 실제 A 8 tick과 B 3개 claim에서 총 88 records
- 최종 chain hash `7eecc2e8fe22934845f168020ac66c2437fe978e371cbbc36468584368f65704`
- records SHA-256 `e793a1d9cf02c28f2d8989eefea0c276a5df2c5f9aa6b4090fe8b35af3c97524`
- manifest SHA-256 `43fb0ca55df8f54ecd22698703108d4e73a68be8868567848e2c9d90b3f8afe0`
- 추적 ON 최종 상태와 일반 A 실행 최종 상태 동일
- 전체 프로젝트 테스트 `796`개 통과

한계:

- 현재 full stage trace는 CPU A2 환경 실행에 연결됨
- GPU 증거 모드의 device-resident delta segment는 아직 미구현
- 같은 Windows 사용자 권한으로 임의 코드를 실행하는 B는 ACL만으로 격리되지 않으므로 별도 저권한 process/broker가 필요
- 장기 trace의 segment 압축·주기적 snapshot 모드는 아직 미구현

**현재 데모:** 서로 떨어진 지역이 같은 물리 tick에 함께 변하며, 열·물·용질 이동과 광물의 용해·침전이 지역 정수 규칙으로 일어나고 통합 물질량과 에너지가 보존된다.

### 작업 묶음 4

- 결정론 화학
- 고분자
- 경계
- 독립 분열

**완료 시 데모:** 고수준 복사·분열 명령 없이 실제 충돌 과정이 고분자와 두 독립 경계를 만들거나 실패한다.

### 작업 묶음 5

- 초기 지구 환경군
- B-Architect v0
- 다중 LLM 검토
- 외부 평가

**완료 시 데모:** 사용자의 초기 지구 구상을 B가 여러 근거 기반 A 명세로 만들고, 검증된 명세만 독립 실행한다.


### B 기반 작업 — 변화 중심 B와 ChangeGraph 독립 후보 완료

설계 반영:

- 상태 전체 재계산 대신 변경 경로에서 관련 규칙·지역으로 영향 범위 확장
- A의 결정론과 B의 인식 불확실성 분리
- `HypothesisSet`으로 가능한 세계·반례·구분 실험 보존
- 목표·위험·불확실성·반례·다양성·무행동 대조군을 보존하는 다중 정밀도 반사실 분기
- 관측 오류→상태 누락→파라미터→새 변수→법칙 후보 순서의 실패 원인 계층
- 기존 이론을 덮어쓰지 않는 `TheoryRevisionProposal`
- 진실 순위가 아닌 수정 권한으로서의 `LawTier`
- 실행 중 A를 바꾸지 않는 사용자 승인형 `ExperimentProposal`

구현:

- trusted `TraceViewBroker`가 사용자 전용 raw trace를 먼저 완전 검증
- B에는 raw 경로·B 기록·목표 이후 A 기록·full stage snapshot을 제외한 승인 view만 전달
- initial snapshot과 목표 tick까지의 모든 stage delta는 무손실 제공
- `ChangeGraphAdapter`는 A transition·forecast 함수를 호출하지 않음
- event sequence와 마지막 변경 경로를 연결한 독립 change graph 생성
- approved delta만으로 최종 상태 재구성
- trusted evaluator는 raw trace를 별도 읽어 B claim 검증

실제 결과:

- 목표 tick 8, stage node 64개, 실제 delta 연산 30개
- 승인 view `38,582` bytes
- 재구성 상태 digest `721a5ecd9a5ea7ac59397070dc0ae90e198b2923bde00a4a0af61f2de3a99887`
- 상태 재구성·지역 상태·마지막 변화·그래프 비용 4개 claim 전부 verified
- falsified 0, untested 0
- ChangeGraph digest `1579c83cd56065815ba0dff2dd1d1de115f1c4b94e425c6b6816adf0bcc105e2`
- B 행동 계보 records SHA-256 `269b232da10a852120235cd65df5c16f31d9455db182a4522795f3db4f488849`
- B 행동 계보 final chain hash `7e3d9dae31df600605bc2688546c84e705bfa934f92329efc0cf822c0d7ff65c`
- Cognitive Map·ChangeGraph에 동일한 지역 상태·최단경로·도달성 질의 5개 제공
- 두 후보 모두 verified 5, falsified·untested 0, 경로를 정규화한 외부 답 동일
- Cognitive Map 입력/표현 `1,496`/`3,073` bytes, 관련 칸 23개
- ChangeGraph 입력/표현 `38,658`/`18,659` bytes, event node 64개·delta 30개
- 다른 입력 역사와 고유 기능 때문에 단일 승자 점수 없이 각 축 보존
- 비교 계보 records SHA-256 `a70f70f317ebd7951410a2a198b66b97392d1daa4ebb3e0af5d19d34751d6e39`
- 비교 계보 final chain hash `b1b50f8c4d6973993387935743afc6f5bc84359a282511ba241467b491399bb1`
- tick 7까지만 보고 tick 8 영향 범위 263/1,024칸과 규칙 4종 예측
- 실제 변경 위치 4개·규칙 1종 모두 포함, 누락 위치·규칙 0
- 과잉 위치 259개·과잉 규칙 3종을 별도 보존
- 고의 실제 위치 제거 시 `next-impact-scope` claim falsified
- prediction digest `386d007eb0c3cb42c4b137279d977d1b093446de2cb90078b8769e1d6f5180ef`
- impact evaluation digest `9cb99b3a6fda1666ac2e296f2ada06d38b6b9ac9579e54acf8b66fcde91ee99b`
- 영향 범위 계보 records SHA-256 `c3aa1157e3925a4f5aeaa6a0ce658bc514c4bf7d1d7b6a584c45a2bc478494e7`
- 영향 범위 계보 final chain hash `5e65c473b553f8699e36bb0136aed943d901581845b838c1b162dd92d5d6327c`
- 비배타적 규칙·무변화·숨은 변수 가설 6개를 tick 8 관측 전에 봉인
- 숫자 weight 기본 없음, 사용할 경우 evidence provenance 필수
- 실제 결과에서 supported 1·refuted 4·underdetermined 1
- `missing-variable-needed`는 한 tick으로 판단하지 않고 반복 residual 관측 대상으로 유지
- 실제 규칙 coverage success true, 가설 원본 digest 불변
- HypothesisSet digest `5088b0e54098975074df35b51dba417b6311a454b4ccc72faa7dd945f629fcf5`
- resolution digest `d61bbdd0b9206af799142b53160b112c2090d303361bc48671263b2629010ef9`
- 가설 계보 records SHA-256 `40ce73cdb1f6da1ecde8f485e68f93e3b95faed004b2f0027be7f201566bca73`
- 가설 계보 final chain hash `6d53333ac846b73262e2b88edd66233f357b438e0bab63bbe17ac092060f2476`
- 같은 부모에서 무행동 control·작은 열·큰 열·먼 열·간선 차단 branch 5개 생성
- 모든 branch low·medium 완료, exact 예산 3개 완료, 2개 `deferred_budget` 보존
- exact 선택은 control·risk·counterexample 명시 track이며 단일 종합 점수 없음
- 무행동 exact digest가 관측 tick 8과 일치
- 큰 열 개입 accounted energy `10`, 설계 변경은 새 spec digest로 분리
- plan digest `7abaca393f5558d1026eb3b14d7e328c307e8301f3ec460ddfdbfa5d81f3c154`
- evaluation digest `170843afeff1b9c922526b95ba8d31099d0d69ccf0344b1278d9cdd7ca39fbd0`
- Counterfactual 계보 records SHA-256 `0c958ffb98b44f76efb2974df98d7e3842006a2d6fff806b6c8108b0aded0f02`
- Counterfactual 계보 final chain hash `e83f1f532e28d2c429f947b938eddc50ff7e0e4eef67eee618972911d5b25a21`
- 서로 다른 vapor 초기량과 spec digest의 봉인 세계 4개 full trace
- 제한 이론이 네 세계 모두에서 vapor 변경 위치 2개를 누락
- residual signature `state-omission:vapor:changed-while-unmodeled` 반복, distinct run/spec 4
- 관측 pipeline·기존 vapor 변수·vapor 관계의 병렬 수정 후보 3개 생성
- 새 미지 latent 변수는 생성하지 않음, 부모 이론 불변, 자동 적용 없음
- governance admissible 3, scientifically verified 0, untested 3
- residual pattern digest `110d92dbb1152c18bd0bb608c93e67824e79e2c4e57d5efc817d30f0cde57dc7`
- revision set digest `0dd36b6e2e9ff5db367852718409cc123f412076ee1bf4df117f56688cf372db`
- review digest `58762f57376d51f3b284be2f6ac10243550a0bd39e70081ad59873b582635441`
- 분석 records SHA-256 `101575ac3d58fb57b8bff328ad3e881e89fd541176108341e556a7832fdf6151`
- 분석 final chain hash `c6538c9f466ae56c6bc495bc76f12bbf32be1d707c412958264b789450b088e2`
- 캠페인 14파일 manifest SHA-256 `ad76423a164a22be41e9c758865f28cfd183cd9ec7806b5d33b1e2689a76d0b3`
- TheoryRevision 후보를 구분하는 held-out ExperimentProposal arm 4개 봉인
- 독립 trace audit·수증기 0 control·held-out vapor 5·13 포함
- training spec과 held-out spec digest 비중복, 세 수정 후보 coverage 완전
- approval `pending-user-approval`, execution allowed false, automatic execution false
- 미승인 실행 함수 호출 시 PermissionError
- proposal digest `e1fdab8d7f8fe1ac8c958af40d868662fb1239139f164a1d9584c9f712e2abb9`
- proposal review digest `8637335326eaf09ce4af2873673d0cc5d1bb7da4ffc83d8a22b0a072f93cd186`
- 제안 계보 records SHA-256 `900fee08e4d5be6f324458e25f4160aaec4d8ef6216001a31e83a44bcf72444e`
- 제안 계보 final chain hash `0264daaf8c2dd47f78763e68c203ad15b3a439da03f544fab2eebc09da8fc5b6`
- scientific status `not-run`, held-out A 실행 0개
- 전체 프로젝트 테스트 `837`개 통과

한계:

- 현재 영향 범위 모델은 실제 변화 4칸을 모두 포함하지만 259칸을 과잉 활성화하는 보수적 첫 기준
- Counterfactual v1은 한 tick·고정 5 branch·명시 track 예산 배정만 지원
- TheoryRevision 후보 3개는 governance 형식만 통과했으며 과학적으로 모두 미검사
- 현재 residual은 이미 A에 존재하는 vapor 변수를 제한 이론이 누락한 인위적 기준 사례
- 진짜 미지 변수 생성은 알려진 변수·관측 오류·관계 후보가 held-out에서 실패한 뒤에만 허용
- 다음 구현은 사용자 승인형 `ExperimentProposal`과 held-out 검증 경계


## 16. 현재 최우선 결정

세 TheoryRevision 후보를 구분할 held-out ExperimentProposal이 봉인됐고 governance 검사를 통과했다. 실제 held-out A 실행은 0개이며 과학적 상태는 `not-run`이다.

> **현재 경계에서는 사용자가 제안서 실행을 명시적으로 승인할지, 미실행 상태로 보존하고 다른 B 작업으로 이동할지 결정해야 한다.**

승인 시에도 부모 이론과 후보별 예상을 먼저 봉인한 뒤 새 campaign을 만든다. 승인하지 않으면 어떤 실험도 실행하지 않는다.

## 17. 중단 조건

다음 중 하나라도 발생하면 다음 단계로 넘어가지 않는다.

- 동일 초기 상태 결과 불일치
- 보존 위반
- 규칙에 선언되지 않은 상태 변경
- B의 예상이 A 결과를 바꿈
- 구조 크기에 따른 숨은 추가 행동권
- CPU·GPU 결과 불일치
- 고수준 생명 명령 유입
- 실패 결과 삭제

## 18. 최종 순서

```text
B0 문법 + A0 이동·충돌                         완료
↓
물리 단위 + B0.1 인과 규칙 + A1 결합           완료
↓
B 월드 모델 v0                                완료
↓
A2/A2.1 환경 field + 환경 B 월드 모델           완료
↓
A2.2 증발·응축 + 외부 에너지 회계                완료
↓
CPU 대규모 격자·크기 독립성 감사                  완료
↓
물리 단위·열 flux 계약 + 열 수렴 재감사            완료
↓
물·용질·수증기 flux 통합 + 전체 수렴 재감사        완료
↓
CUDA int64 transport 매 tick 동등성 기준               완료
↓
GPU 상주형 전체 field 실행 + 성능 감사                  완료
↓
모델 중립 B-Language schema + exact BrainAdapter          완료
↓
독립 Cognitive Map adapter + 상태 질의 benchmark          완료
↓
사용자 전용 매 tick A/B full trace + hash chain            완료
↓
TraceViewBroker + 독립 ChangeGraphAdapter                  완료
↓
Cognitive Map·ChangeGraph 동일 외부 질의 병렬 비교         완료
↓
ChangeGraph 다음 영향 범위 예측 + 누락·과잉 검사           완료
↓
HypothesisSet + 미확인 상태 + 구분 관측                    완료
↓
다중 정밀도 CounterfactualBranch + 무행동 대조군           완료
↓
반복 ResidualPattern + TheoryRevisionProposal              완료
↓
사용자 승인형 held-out ExperimentProposal                  제안 완료
↓
held-out A 실행·후보 이론 검증                              사용자 승인 대기
↓
결정론 화학·고분자
↓
경계·독립 분열
↓
초기 지구 환경군
↓
B-Architect v0
↓
B 학습·자기개조
```
