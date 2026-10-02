# Reality-Constrained Deterministic Initial State Pilot V0

2026-10-02 · SURVEY + ISOLATED PROTOTYPE · 미승인 · production 입력 아님

## 1. 먼저 답할 여섯 질문

1. **현실 자료만으로 원자 위치 하나를 만들 수 있는가?** 이번에 확보한 자료만으로는 안 된다. 추가 밀도·배치 가정을 명시하면 위치 집합은 만들 수 있지만, 그 가정까지 실험이 정해 준 것은 아니다.
2. **각 원자의 움직임도 만들 수 있는가?** 온도를 이용한 분포 대표점은 만들었다. 실제 원자의 운동량을 측정한 결과가 아니며, 현실적인 방향·위치와의 결합까지 닫히지 않았다.
3. **난수 없이 가짜 격자·방향 패턴을 피했는가?** 아직 아니다. 격자 후보에는 결정 구조가, 운동량 후보에는 두 방향 영역 집중 또는 빠른 원자의 방향 집중이 남았다. 난수를 없애는 것만으로 현실성이 확보되지 않는다.
4. **실제 측정 상태인가?** 아니다. 실험 조건 일부에 묶고 추가 가정으로 만든 가상 후보다. 확보하지 못한 현실 통계와 양립한다고까지 확인하지 못했다.
5. **사람이 임의로 정하는 것보다 나은가?** 온도를 실험에 묶고, 생성 규칙과 모든 비교 결과를 고정·공개하는 점은 낫다. 현실 기체의 대표성까지 더 좋다고 입증하지는 못했다. 공식 원자 수도 선택하지 않았다.
6. **A에 넣기 전에 무엇이 부족한가?** 같은 상태점의 밀도/EOS·동위원소·구조 통계와 불확실성, 인공 상관을 허용할 준비 계약, C1-C의 힘 합산·경계·반올림 계약이 필요하다.

## 2. 판정과 범위

**E — REALITY_DATA_INSUFFICIENT**

같은 상태점의 온도와 압력은 확보했으나, 검증된 number density/EOS와 g(r)/S(q), 동위원소 조성은 확보하지 못했다. 따라서 **현실 자료만 사용하는 생성 경로는 REFUSED**다. 자료 부족은 이번에 확인한 출처·조회 범위의 판정이며, 그런 실험 자료가 세상에 존재하지 않는다는 증명이 아니다.

별도 명시적 조건부 모드에서 위치 후보 3종 × 운동량 후보 2종 × N 5종 = **30개 완전한 q,p 후보**를 생성했다. 이 모드의 뜻은 다음과 같다.

```text
REALITY_CONSTRAINED_GENERATED_STATE
qualification = CONDITIONAL_ASSUMED_PROXY_ONLY
NOT AN OBSERVED MICROSTATE
reality_only_eligible = false
production_A_input = false
forward_steps = 0
C1-C D5 = PENDING
```

분류 이름은 현실성 합격 표시가 아니다. **이상기체 밀도, 순수 Ar40, 고전 평형 운동량 분포라는 가정이 포함된 비교 표본**이다. A/B/C 판정으로 승격하지 않는다. D에 해당할 수 있는 인공 구조는 발견했지만, 모든 결정론적 생성법이 불가능하다고 일반화하지 않는다.

이전 [고체 Ar 파일럿](REALITY_ANCHORED_SMALL_A_INITIAL_STATE_PILOT_V0.md)의 **B / R2 / MISSING_DYNAMIC_STATE**는 그대로다. C1-B1, D_valid, dt, production N, PBC, GPU 및 C1-C 계약을 변경하지 않았다. 힘·적분·점성·원격 계산을 실행하지 않았다.

## 3. 현실 상태점과 조회 범위

선택한 출처는 Segovia 등의 [Ar 음향 측정 논문](https://arxiv.org/pdf/2409.10140)이다. Table 1(PDF 22쪽)의 **273.16 K 기준 등온선, 0.08090 MPa**를 사용했다. 이는 순간 온도계 원시값이 아니라 기준 온도에 보정된 실험 상태점이다. 생성 전에, 논문이 명시한 측정 범위 안에서 Table 1에 실린 가장 낮은 압력 행을 선택했다.

| 조회 후보 | 실제 확인 범위 | 채택/미채택 이유 |
|---|---|---|
| Segovia 등, Ar 음향 측정 | 온도·압력·시료 관련 2.2/2.3절과 Table 1 | T와 p가 같은 상태점에 있음. 밀도·구조·동위원소는 미확보 |
| May·Berg·Moldover, [저밀도 기준 점성](https://www.nist.gov/publications/reference-viscosities-h2-ch4-ar-and-xe-low-densities) | 초록, 장치·저밀도 외삽·Ar 관련 부분 | 영밀도 점성 외삽값을 유한 원자 수의 밀도로 사용하지 않음. 흐름 장치 압력도 단일 균질 초기상태로 옮기지 않음 |
| Vogel, [ThermoML 기록](https://trc.nist.gov/ThermoML/10.1007/s10765-010-0760-6.html) | 공개 메타데이터·초록 | 수치 JSON 전체 다운로드가 HTTP 403으로 실패. 자료가 없다고 판정하지 않음 |
| 저밀도 Ar 구조 통계 검색 | 검색 결과 수준의 후보 발견 | 선택한 상태점과 일치하는 1차 수치 g(r)/S(q)를 검증·확보하지 못함 |

선택 논문 원본 PDF SHA256은 `664f76a44a38b8428e6581e3d120d080374407da694a28c3bde1cd0268be3c87`이다. 원본은 `runs/reality_constrained_ar_state_20261002_v0/segovia_argon.pdf`에 보존했다. 조회 실패를 숨기지 않으며, 이번 조사는 모든 Ar 문헌을 망라한 조사도 아니다.

## 4. 입력·출력 필드의 출처 구분

| 필드 | 값/내용 | 분류 |
|---|---|---|
| 기준 T | 273.16 K, 실험 기준 등온선 | DERIVED_FROM_MEASUREMENT |
| 압력 p | 80900 Pa, 출판된 표의 값 | DERIVED_FROM_MEASUREMENT |
| 압력 표준 불확실성 | 논문 식 3.75×10⁻⁵ p + 100 Pa → 103.03375 Pa | DERIVED_FROM_MEASUREMENT |
| 온도 보정 표준 불확실성 | 0.1 mK; 최대 안정성 범위 0.6 mK도 별도 보고 | DERIVED_FROM_MEASUREMENT |
| 해당 상태점의 온도 종합 불확실성 | 전체 항목을 합친 값은 확보하지 못함 | UNAVAILABLE |
| 시료 원소·공급자 순도 | Ar, 몰분율 0.999999 | DERIVED_FROM_MEASUREMENT |
| 동위원소 비율 | 논문에서 직접 측정하지 않았다고 명시 | UNAVAILABLE |
| number density / 검증된 EOS | 해당 점의 수치·불확실성 미확보 | UNAVAILABLE |
| g(r), S(q) 및 그 불확실성 | 해당 점의 수치 미확보 | UNAVAILABLE |
| 실제 개별 q,p | 관측 미시상태 자료 없음 | UNAVAILABLE |
| 조건부 n_proxy | p/(kBT) ≈ 2.14510×10²⁵ m⁻³; Z=1 | ASSUMED |
| 조건부 입자 종류 | 순수 Ar40로 매핑 | ASSUMED |
| 조건부 운동량 법칙 | 고전 평형 Maxwell–Boltzmann 분포 | ASSUMED |
| N, 큐브 모양, 배치·대표점·방향 규칙 | 비교용 4/8/16/32/64, 사전 고정 규칙 | ASSUMED |
| 생성 q,p, 저장 순서 | 위 입력·규칙으로 생성한 값 | REALITY_CONSTRAINED_GENERATED |
| K, Tkin, Σp, 거리·분포·편향 진단 | 생성값의 계산 관측; 실험값 아님 | REALITY_CONSTRAINED_GENERATED |
| FX 원시 정수·변화 진단 | 생성값을 별도로 투영한 관측 | REALITY_CONSTRAINED_GENERATED |
| 단위 변환·명목 질량 상수 | 기존 문서/소스 버전의 숫자를 복사한 준비 선택 | ASSUMED |

원시 계측 시계열은 가져오지 않았으므로 이번 입력에는 DIRECTLY_MEASURED라고 붙인 원시 데이터가 없다. 공급자 화학 순도는 Ar40 순도가 아니다. 논문의 가정된 평균 몰질량을 순수 Ar40의 측정 증거로 쓰지 않았다. 온도 교정의 0.1 mK를 전체 상태점 불확실성으로 사용하지 않았고, EOS가 없는 밀도 불확실성도 계산해 꾸미지 않았다.

KB_SI=1.380649×10⁻²³ J/K는 SI의 정확한 정의다. 관측 변환에는 문서의 KB_AU=3.1668115634564×10⁻⁶ Eh/K, a0=5.29177210903×10⁻¹¹ m 및 기존 Ar40/me 명목 질량 비를 복사했다. 서로 다른 출처 버전의 상수와 실험 불확실성을 통합한 계량학적 보증은 아니다. 기존 A 모듈을 import하지 않는다.

## 5. 생성 전에 고정한 규칙

[protocol_v0.json](reality_constrained_ar_state_v0/protocol_v0.json)에 후보·N·진단·거부 조건을 먼저 고정하고, [execution_seal_v0.json](reality_constrained_ar_state_v0/execution_seal_v0.json)에 첫 실행 소스 해시와 유한 수치 규칙을 묶었다. 밀도·구조 자료가 부족한 현실 전용 경로, 미지원 입력, 불가능한 최소 간격은 REFUSED다. 조건부 모드는 명시적으로 요청해야 한다.

배치 공간은 조건부 n_proxy를 사용한 V=N/n_proxy, L³=V의 큐브다. **초기 배치 좌표틀만 제공하며 벽·PBC·최소 이미지 거리·힘 법칙은 없다.** 모든 후보를 보존하고, 진단 점수가 좋은 후보를 실행 입력으로 선택하지 않았다. 1.2 Å 간격 점검은 현재 pair 모델과의 호환 관측일 뿐 현실 Ar의 hard core 선언이 아니다. 실패한 위치를 이동·재생성하지 않는다.

| 위치 후보 | 고정된 생성법 | 남은 문제 |
|---|---|---|
| Q1_GRID | ceil(cuberoot(N)) 격자의 셀 중심, 사전 정의된 첫 N개 | 결정·평면·슬랩 구조 |
| Q2_HALTON | index 1..N, bases 2/3/5의 정확한 radical inverse, scrambling 없음 | 유한 저불일치 표본의 결정론 상관; 현실 구조 통계 적합성 미확인 |
| Q3_EXPERIMENTAL_RECONSTRUCTION | 미구현; 입력 구조 통계가 없으므로 REFUSED | 역문제는 유일하지 않으며 불확실성·목적함수·tie 규칙도 필요 |
| Q4_RANK1 | 축별 고정 모듈러 rank-1 규칙, multiplier 1/3/5 | 적은 N에서 평면, 제한된 거리 종류 |

[Halton 공식 문서](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Halton.html)의 정의를 참고했다. 이 prototype은 SciPy·난수를 사용하지 않는다. 저불일치 특성은 실험 기체의 g(r) 보증이 아니다.

| 운동량 후보 | 대표점·방향·총운동량 규칙 | 남은 문제 |
|---|---|---|
| P1_CARTESIAN_QUANTILES | 각 축의 양의 Gaussian 중간 quantile을 고정 순열로 결합; v와 −v를 교대로 저장 | +++와 --- 두 octant만 점유, 축 사이 강한 상관 |
| P2_RADIAL_SPHERE_ANTIPODAL | Maxwell 속력 quantile + 상반구 Fibonacci형 방향, 반대 방향 쌍 | 속력과 z 방향이 함께 증가하여 에너지 방향 편향 |

두 후보 모두 마지막 원자에 잔차를 몰지 않는다. ± 쌍 자체가 정확한 Σp=0을 준다. 그러나 이 대칭은 단순 COM=0 제약보다 강한 추가 인공 조건이다. 독립적으로 뽑은 평형 기체 상태와 같다고 볼 수 없다. 반복 속력은 반대쌍마다 정확히 두 번 발생하며, 완전한 반대 방향 짝 구조도 유지된다.

원자 ID는 생성 입력이 아니다. 생성 후 ID 재명명·행 permutation이 물리 레코드 집합을 바꾸지 않는 것은 확인했다. **그러나 위치를 기하 순서로 정렬한 뒤 운동량을 배정하므로, canonical ordering이 외부 표현에만 머물지 않고 q-p 초기 상관에 관여한다.** 따라서 엄격한 준비 계약에 합격한 initializer라고 부를 수 없다.

## 6. exact representation과 근사 범위

q는 유리수 계수 × cbrt(V/a0³), p는 유리수 계수 × sqrt(m kB_AU T)로 저장한다. 대표점 계수는 고정 Decimal 70자리, erf 240항, 이분 128회, 삼각함수 120항 및 10⁻³⁰ 계수 격자로 정의한다. 유리수로 바꾼 **그 유한 대표값**과 공통 근호의 표현은 정확하지만, 진짜 분포 quantile·삼각함수를 무한 정확도로 계산했다는 뜻은 아니다. [NIST DLMF의 erf 정의](https://dlmf.nist.gov/7.2)를 참고했다.

별도 libm 기반 CDF 대조에서 생성 quantile의 수치 잔차를 검사했다. 이것은 독립 수치 확인이며 formal quantile certificate가 아니다. 일부 진단 tensor/covariance는 사전 고정 25자리, 비교 요약은 6자리 유효숫자로 표시한다. 실제 후보 계수·K·Σp를 이 요약 반올림으로 수정하지 않는다.

K=Σp²/(2m)를 정확한 유리수 식으로 관측하고 Tkin=2K/[3(N−1)kB]를 표시한다. 이 Tkin은 유한 표본의 진단이며 각 원자의 실제 열적 온도가 아니다. 생성 뒤 p를 재조정하지 않았다.

정확한 K 자체는 원리상 COM=0 부분공간의 고정 에너지 구면에서 좌표를 직접 구성해 맞출 수 있다. 다만 그 방향 선택·유한 분포·현실 준비 과정은 별도 계약이고, 사후 공통 rescaling과 같은 효과를 가진 구성이 될 수도 있다. **이 파일럿에서는 구현·채택하지 않았다.** 정확한 K와 현실 Maxwell 대표성을 동시에 얻었다고 주장하지 않는다.

## 7. 위치 결과 — 실험 구조와의 비교는 아직 아님

다음 수치는 사전 고정한 거리제곱 7개 bin에서, **유한 비주기 큐브의 독립 균일 배치 참고 CDF**와 생성 pair CDF의 최대 차이다. 참고값은 고정 32³ quadrature이며 실험 g(r), 무한기체 통계, 인증된 quadrature 오차, 통계 검정 p-value가 아니다. pair들을 독립 표본으로 가정하지 않는다.

| N | Q1_GRID | Q2_HALTON | Q4_RANK1 |
|---:|---:|---:|---:|
| 4 | 0.389030 | 0.207677 | 0.292323 |
| 8 | 0.231487 | 0.0546319 | 0.0899418 |
| 16 | 0.224344 | 0.0410106 | 0.0491761 |
| 32 | 0.164667 | 0.0236043 | 0.0236043 |
| 64 | 0.0469630 | 0.0177159 | 0.0209014 |

Halton은 이 제한된 참고 지표에서 격자보다 차이가 작았다. 이것을 **현실 통계 접근 정도**로 읽으면 안 된다. 실험 구조 데이터가 없어 그 항목은 UNAVAILABLE이다. Q1 N=4는 평면, N=16/32는 슬랩, N=64는 규칙 격자다. Q4 N=4는 z=x 평면이다.

N=64의 2016개 pair 중 서로 다른 거리제곱 종류는 Q1 18, Q2 1299, Q4 167개다. 최소 최근접 거리제곱/L²는 각각 0.0625, 0.00292568, 0.00854492다. 최소·최대 최근접 거리, 축 공분산 등 원자료는 생성 JSON에 남겼다. 모두 간격 관측을 통과했지만 이는 현실적인 거리 분포의 증거가 아니다.

## 8. 운동량 결과 — 분포 한 지표 개선과 방향 편향을 함께 보존

각 운동량 후보의 값은 위치 방법 3종에 공통이다. speed CDF gap은 Maxwell 가정에 대한 최대 차이이고, kinetic anisotropy는 에너지 가중 방향 tensor와 등방 tensor의 성분별 최대 차이다.

| N | P1 Tkin/T | P2 Tkin/T | P1 speed CDF gap | P2 speed CDF gap | P1 kinetic anisotropy | P2 kinetic anisotropy |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.949890 | 1.18242 | 0.432109 | 0.25 | 0.333333 | 0.258734 |
| 8 | 0.972630 | 1.07577 | 0.288992 | 0.125 | 0.281589 | 0.186028 |
| 16 | 0.985259 | 1.03476 | 0.168155 | 0.0625 | 0.257187 | 0.212576 |
| 32 | 0.992158 | 1.01668 | 0.0924801 | 0.03125 | 0.266790 | 0.223154 |
| 64 | 0.995872 | 1.00818 | 0.0680443 | 0.015625 | 0.253719 | 0.227632 |

| N | P1 K/(kBT) | P2 K/(kBT) |
|---:|---:|---:|
| 4 | 4.27450 | 5.32088 |
| 8 | 10.2126 | 11.2956 |
| 16 | 22.1683 | 23.2821 |
| 32 | 46.1354 | 47.2755 |
| 64 | 94.1099 | 95.2726 |

30개 후보 모두 생성 q,p를 직접 계산하여 **Σp=0**을 확인했다.

P1은 모든 N에서 두 octant만 사용한다. P2는 속력 CDF 차이가 줄어도 빠른 원자가 z 방향에 집중하는 편향이 남으며, N 증가만으로 해소되지 않았다. N=64의 Tkin은 P1 272.032 K, P2 275.393 K이고, 목표 273.16 K로 맞춰 보정하지 않았다.

Halton의 q_x-p_z 무차원 공분산은 P1이 N=4에서 −0.0558634, N=64에서 −0.00620019이고, P2는 −0.103614, −0.00768712였다. 교대로 놓은 반대 운동량을 정렬된 위치에 배정하여 Σ(q_x[2j]−q_x[2j+1])p_jz/N의 상관이 생긴다. P1의 양의 성분, P2의 상반구 성분 때문에 부호까지 체계적이다. ID 독립성과 위치·운동량의 자연스러운 독립성은 서로 다른 문제다.

축 성분 CDF, 속력 4차 모멘트, 비가중 방향 tensor, octant 점유, 위치 조건부 octant와 실제로 센 반대 방향 pair 수도 기록했다. 균형 있는 부호 조합, 속력과 방향의 별도 배열, COM 조건부 분포 등은 재설계 후보이며 이번 결과를 보고 채택·재생성하지 않았다.

## 9. fixed-point는 별도 투영 관측

생성식을 먼저 고정하고 q→FX(96,48), p→FX(96,80)을 정수/Fraction의 근·중점 비교로 round-to-nearest ties-to-even 투영했다. 음수 대칭도 확인했다. fixed-point에 맞춘 위치 변경·운동량 보정은 없다. 160-bit 근의 포위 구간에서 성분·pair R² 변화의 상계를 계산했고, K 변화는 투영 후 유리수 값으로 계산했다.

| 30개 후보 전체의 관측 | 최대값 또는 결과 |
|---|---:|
| q成分変化上界 | 1.77071×10⁻¹⁵ bohr |
| p成分変化上界 | 4.13071×10⁻²⁵ atomic momentum |
| pair R²変化上界 | 1.45519×10⁻¹¹ bohr² |
| K 상대 변화 절대값 | 5.60485×10⁻²⁶ |
| Σp | 30개 모두 투영 전·후 실제 계산에서 엄밀한 0 |

Σp 보존은 이번 반대 방향 pair와 홀수 대칭 양자화의 조합이 가진 성질이며, 임의의 생성법에 대한 보증이 아니다. 원시 정수는 **OBSERVATION_ONLY_NOT_A_INPUT_OR_BOUNDARY**다. 양자화 변화가 작다는 결과는 현실성, C1-C 합산 계약, 궤적의 건전성을 증명하지 않는다.

## 10. 실행 전 고정·독립 리뷰·검증

첫 소스의 LF 정규화 SHA256은 `bd695b1a63c058c1e6db000bed6be6d20f269ffa6537a723ca631af5ba6afddf`다. 첫 생성은 7.355초에 30개를 모두 보존했다. 생성 JSON SHA256은 `f01f2fa6603a0ea71d7e1ed82b1da44c667aa923a6cc1e33677348c6d22bbc3e`다.

**첫 생성 뒤 검사 코드를 보강했다.** 미지원 quantile 거부, 고정하지 않은 최소 간격 override 거부, 후보별 REFUSED 보존, Decimal 설명 수정이며 q,p 생성 규칙이나 기준은 바꾸지 않았다. 30개 후보와 외부 레코드 전체를 재생성하여 첫 JSON과 전 바이트 일치를 확인했다. 변경 내용과 전후 소스 해시는 [execution_validation_amendment_v1.json](reality_constrained_ar_state_v0/execution_validation_amendment_v1.json)에 공개했다. 실행 후 변경을 처음부터 고정했던 것으로 취급하지 않는다.

독립된 기존 reviewer가 후보·코드·준비 의미를 정적으로 점검했다. [리뷰 기록](reality_constrained_ar_state_v0/independent_review_v0.md)의 지적을 부정적 결과로 보존했다. 독립 static review이며, 독립 실행 인증이나 설계자 승인이 아니다. scientific-brainstorming / scientific-critical-thinking 스킬을 사용했다. 작업 틀의 문헌은 [Kassis 등의 ScientificAgentSkills, arXiv:2609.00065 v2](https://arxiv.org/abs/2609.00065)이며 Ar 물성의 근거는 아니다.

이번에 새로 실행한 관련 시험은 **76 passed / failure 0 / error 0 / skip 0 / xfail 0, 2.79초**다.

```text
python -m pytest tests/test_reality_constrained_ar_state_v0.py tests/test_reality_anchored_ar_initial_state_pilot_v0.py tests/test_c1a_freeze.py -q --junitxml=runs/reality_constrained_ar_state_20261002_v0/pytest_related_first.xml
```

| 검증 대상 | 실제 확인 / 한계 |
|---|---|
| 같은 입력 재생성 | 30개 후보 전체 JSON을 첫 생성과 비교하여 byte-identical |
| 입력 1 byte 변경 | source/protocol 해시로 거부. 의미가 같은 공백 변경도 거부 |
| N 변경 | 허용된 비교 범위 5종의 서로 다른 완전한 상태. 범위 밖·bool·비정수는 거부 |
| ID/행 permutation | 저장된 30개 후보를 재명명·재배열해 같은 물리 레코드 집합 확인 |
| locale/수치 환경 | Windows 별도 Python 과정에서 외부 Decimal 정밀도/반올림, LC_ALL 환경 문자열, hash seed를 바꿔 byte 일치 |
| OS | 실제 OS는 Windows뿐. Linux/macOS 미실행, 다른 OS의 일치 미확인 |
| tie | 유리수 제곱/세제곱근 중점, 음수, 짝수 반올림 검사 |
| unsupported T/density | 고정 입력 변경 거부. 연속 T/n 영역을 지원한 것은 아님 |
| impossible separation | 불가능한 간격 거부, 이동·수정 없음 |
| 실패 후보 보존 | fault 주입으로 2개 REFUSED, 나머지 유지. 성공 후보로 교체 없음 |
| 근사 분포 함수 | 별도 libm 식으로 수치 잔차 점검. formal proof 아님 |
| FX 변환 | 중점 범위, Σp, K를 별도 유리수 계산으로 대조 |
| 의존성 | A/random/network import, binary float 사용을 AST 검사 |

로그는 `runs/reality_constrained_ar_state_20261002_v0/pytest_related_first.log`와 동명 XML에 저장했다. 위 결과는 과거 로그 인용이 아니라 이번 새 실행이다.

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 새 독립 survey prototype·시험·자료와 색인 링크만 변경했다. 기존 실행 코드·공용 물리·인증·fixture·계약·해시 고정 소스를 변경하지 않았고, 관련 시험과 기존 freeze 확인이 통과했다. 공식 LOCAL FULL 기준선은 갱신하지 않는다. prototype의 76개 통과를 A 인증이나 현실성 합격으로 세지 않는다.

읽은 범위 공개: 최신 요청, AGENTS, 헌법, L 원칙, 이번 source/protocol/구현을 확인했다. RULES, CURRENT_STATE, REPO_MAP과 긴 C1-C안은 관련 조항·범위를 읽었으며 전체 재감사가 아니다. 이전 pilot의 판정·구조/동적 상태 부분을 재확인했다. 원 논문은 위 관련 절·표를 읽었으며 전체 페이지 정독이나 그림 이미지의 육안 확인은 아니다.

## 11. 실패·제한 기록

ThermoML 수치 JSON의 HTTP 403, XML 조회 도구 오류, 후보 논문의 HTML/추측 URL 조회 실패를 기록했다. 확인된 PDF 조회는 성공했다. PubMed 후보는 내용을 확인하지 못해 실험 수치 근거로 사용하지 않았다. 문서 표시 중 cp949 문자 출력 실패 2회는 PowerShell 읽기와 UTF-8 출력으로 처리했으며, 물리 계산·시험 실패가 아니다. 최종 Git 조회에는 기존 색인 2개의 LF→CRLF 예상 경고가 있었고 diff 검사는 통과했다. 해시 고정 JSON은 별도 LF 속성과 원본 바이트 확인으로 보호했다. 생성·pytest의 이번 실행에는 실패가 없었다. 자세한 기록은 `runs/reality_constrained_ar_state_20261002_v0/execution_record_v0.json`에 있다.

구상 일치성 2차 확인: 사후 결과 선택 없음·난수 없음·미래 성공을 심지 않음·A 세계와 외부 준비/관측 분리는 요청과 일치한다. 현실 입력만으로 닫는 것, 인공 구조를 피하는 것, canonical ordering을 외부에만 두는 것은 달성하지 못했다. 생명·발생·재생산·현실 전이·C1-B1 closure의 새 증거는 없다.

## 12. Git과 산출물

| 項目 | 結果 |
|---|---|
| start HEAD | cc0fd1c414eb6fba57d53263289def901a758e84 |
| end HEAD | cc0fd1c414eb6fba57d53263289def901a758e84 |
| origin/master | cc0fd1c414eb6fba57d53263289def901a758e84（今回fetch後） |
| ahead/behind | 0 / 0 |
| start dirty | 없음 |
| end dirty | 새 파일 11개, 기존 색인 2개 변경, 미commit |
| commit / push | 모두 실행하지 않음 |

변경 파일:

- `docs/proposals/REALITY_CONSTRAINED_DETERMINISTIC_INITIAL_STATE_V0.md`
- `tools/reality_constrained_ar_state_v0.py`
- `tests/test_reality_constrained_ar_state_v0.py`
- `docs/proposals/reality_constrained_ar_state_v0/source_manifest.json`
- `docs/proposals/reality_constrained_ar_state_v0/protocol_v0.json`
- `docs/proposals/reality_constrained_ar_state_v0/execution_seal_v0.json`
- `docs/proposals/reality_constrained_ar_state_v0/generated_state_examples.json`
- `docs/proposals/reality_constrained_ar_state_v0/execution_validation_amendment_v1.json`
- `docs/proposals/reality_constrained_ar_state_v0/comparison_summary.json`
- `docs/proposals/reality_constrained_ar_state_v0/independent_review_v0.md`
- `docs/proposals/reality_constrained_ar_state_v0/.gitattributes`
- `docs/proposals/README.md` (색인 1항목 추가)
- `docs/DOCUMENT_STATUS_INDEX.md` (색인 1항목 추가)

원본 PDF·첫 소스·재생성·시험 로그는 지정한 `runs/`에 보존하고 기존 이력은 변경하지 않았다. 최종 Git·해시·링크 확인은 같은 디렉터리의 execution_record에 저장한다.

조사와 비교 pilot은 완료했다. 현실 입력만으로 A에 전달하는 경로는 자료/준비 계약 부족으로 거부를 유지한다. 설계자 판단 전에 후보 채택이나 C1-C 구현으로 진행하지 않는다.

READY FOR DESIGNER REVIEW
