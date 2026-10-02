# Reality-Anchored Small-A Initial State Pilot V0

2026-10-02 · **SURVEY + ISOLATED PROTOTYPE** · production Small-A 미구현 · 계약 승격 없음

1. **현실 원자 지도를 가져올 수 있는가?** 이번에 확보한 Ar 자료에서는 평균 결정 구조를 좌표표로 가져올 수 있다. 한 순간의 개별 원자 위치와 운동량을 함께 가져오지는 못했다. 다른 모든 실험에서도 불가능하다는 판정은 아니다.
2. **순간 실제 좌표인가, 평균 구조인가?** 평균·반복 구조다. 네 개의 점은 실험 논문에 연결된 결정학 자료의 대칭을 펼쳐 재구성한 자리이며, 네 원자를 촬영한 순간 지도도 원자 식별표도 아니다.
3. **동역학 시작에 무엇이 더 필요한가?** 현실 근거가 있는 순간 위치·각 원자의 운동량·동위원소 조성·상태 조건·주변 환경과 경계 계약이 필요하다. 현재 A의 두 40Ar 계약으로 이 네 자리의 다원자 운동을 실행할 수도 없다.
4. **조각을 자르면 어떤 문제가 생기는가?** 주변 원자가 빠지고 인공 표면이 생긴다. 이상적 평균 fcc 구조에서 각 자리의 최근접 이웃은 12개인데, 선택한 네 점 안에는 3개만 남는다. 원래 결정 내부의 힘과 에너지를 그대로 유지한 독립 물체가 아니다.
5. **임의로 N·밀도·구조를 고르는 것보다 현실적인가?** 평균 구조와 격자 간격을 실험 기록에 묶는 부분에서는 그렇다. 그러나 순간 상태·운동량·경계까지 현실에서 가져왔다는 뜻은 아니다. 이 네 자리와 계산된 평균 밀도는 Small-A의 N·밀도 결정이 아니다.

최종 verdict: **B — STRUCTURE_REALITY_ANCHORED_BUT_DYNAMIC_STATE_INCOMPLETE**.
선택 사례는 **R2 / EXPERIMENTALLY_ANCHORED_RECONSTRUCTION**.
동역학 상태는 **MISSING_DYNAMIC_STATE**, forward 실행은 **0 step**이다.
이 B는 공개 Ar 결정 기록의 평균 구조에 대한 판정이다. 순수 40Ar의 완전한 실험 초기상태 확보를 뜻하지 않는다.

## 1. 범위와 근거의 한계

작업 시작 시 master의 HEAD와 origin/master는 모두 `015c108324876c059110bbe53f647d85265cf075`, ahead/behind 0/0, dirty 없음이었다. origin을 fetch한 뒤에도 같았다. 이번 작업은 문헌 조사와 별도의 작은 구조 prototype까지다.

- 확보한 COD CIF에는 온도·압력·동위원소 조성·순간 운동량·측정 불확실도가 없다. 정밀한 상태점이 지정된 현실 샘플이라고 부를 수 없다.
- COD가 연결한 1956년 원 논문은 출판사 페이지의 서지·미리보기만 확인했다. 원 논문 전체나 원 회절 측정 데이터를 다시 감사하지 않았다. 따라서 CIF의 `a=5.4 Å`가 어떤 측정 조건에서 어떻게 추출됐는지 이번 작업으로 독립 확인하지 못했다.
- CIF를 정확히 복사하고 해시를 고정하는 것은 출처 바이트의 재현성이다. 원 측정의 정확성이나 데이터베이스 전사의 무오류를 증명하지 않는다.
- 고체 Ar 구조를 현재 기체 지향 C1-C의 채택 상태로 승격하지 않는다. pair Ar-Ar 모델이 있다는 사실만으로 고체의 다체 효과·양자 진동까지 충분히 설명한다는 주장도 하지 않는다.

## 2. R0–R3와 실제 조사 결과

| 등급 | 의미 | 이번 확보 결과 |
|---|---|---|
| R0 | 같은 순간의 개별 species, q, p가 직접 제공됨 | 조사한 공개 자료에서 확보하지 못함 |
| R1 | 개별 원자 위치 지도가 있고 p는 없음 | 조사한 Ar 자료에서 확보하지 못함 |
| R2 | 평균 격자·unit cell·평균 점유 위치 | 고체 Ar CIF 확보, 이번 prototype 대상으로 선택 |
| R3 | 밀도·S(q)·g(r)·T·P 등 통계 구조 | 액체와 저밀도 기체의 실험 논문에서 관측 종류 확인 |

R2 좌표 재구성은 `EXPERIMENTALLY_ANCHORED_RECONSTRUCTION`이다.
R3 통계에 맞춰 좌표 하나를 만들면 `REALITY-CONSTRAINED GENERATED STATE`이며, 측정된 개별 원자 지도와 다르다. 이번에는 R3 좌표를 생성하지 않았다.

### 조사한 구체적인 후보

| 후보와 1차 출처 | 이번 확인 범위 | 제공 정보와 분류 | 선택 여부 |
|---|---|---|---|
| 고체 Ar: Dobbs 외, Nature 178, 483 (1956), [원 논문](https://doi.org/10.1038/178483a0), [COD 1541541 CIF mirror](https://qiserver.ugr.es/cod/1541541.cif) | 출판사 서지·미리보기 + CIF 전체 다운로드·읽기 | fcc 평균 cell, a=5.4 Å, 평균 자리·대칭·점유율. R2. T/P/동위원소/p 없음 | **단일 prototype 사례** |
| 고체 Ar: Peterson, Batchelder, Simmons, Phys. Rev. 150, 703–711 (1966), [출판사 초록](https://journals.aps.org/pr/abstract/10.1103/PhysRev.150.703) | 초록; PDF 확보 실패 | X선 격자 상수·열팽창·압축률. 실측 온도 범위 2.3–83.2 K, 0 K 상수는 외삽값이며 kxu 단위. R2. 화학 순도 99.998%는 40Ar 동위원소 순도 증거가 아님 | 구조의 실험 근거 보강. 수치를 선택 CIF와 섞지 않음 |
| 액체 Ar: Yarnell 외, Phys. Rev. A 7, 2130–2144 (1973), [출판사 초록](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.7.2130) | 초록; 본문 표 전체 미확보 | 85 K 중성자 산란 S(q), 처리·변환한 g(r). R3. 개별 q,p가 아님 | 통계 구조 사례. 좌표 생성 안 함 |
| 저밀도 기체 후보: Magli 외, Phys. Rev. Lett. 77, 846 (1996), [출판사 초록](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.77.846) | 초록. 웹 텍스트의 T·밀도 수식값 유실, 본문 미확보 | 작은각 중성자 회절 S(k)와 장거리 pair 계수의 역추론. R3. 이번에는 정량적인 희박도까지 검증 못함 | inverse 사례. 미확인 T·밀도를 넣지 않음 |

선택 이유는 조사 범위 안에서 **실험 문헌에 연결된 구조 파일 전체를 공개적으로 확보하고 아주 작은 좌표표로 옮길 수 있는 사례**였기 때문이다. 최신·최정밀 Ar 상태라는 뜻은 아니다. 고체의 접근 가능한 평균 구조를 선택한 것이며 액체·기체를 동역학 실행 결과로 탈락시키지 않았다. 어느 후보도 forward 실행하지 않았다.

## 3. 단일 사례의 출처와 바이트 보존

- 파일: [1541541.cif](reality_anchor_ar_v0/1541541.cif)
- COD ID `1541541`, revision `301779`, 파일 헤더 날짜 2025-08-18.
- 원 논문 연결: E. R. Dobbs, B. F. Figgins, G. O. Jones, D. C. Piercey, D. P. Riley, “Density and Expansivity of Solid Argon”, Nature 178, 483 (1956).
- 다운로드일 2026-10-02, mirror URL은 위 표에 있다. 다운로드 **4438 bytes**를 줄바꿈까지 그대로 보존했다.
- SHA-256: `aca67f14c014e467887cdd678a1b74872c9c1d73a473e52ecd5a3ed8960142b6`.
- 자료 폴더의 `.gitattributes`에서 이 CIF에만 `-text`를 지정했다. 저장소의 `core.autocrlf=true`가 원자료 줄바꿈을 변환하지 않도록 한 신규 자료 보존 규칙이다.
- 파일 자체에 COD 기여자가 public domain으로 제공했다는 안내가 있다.
- 원 COD 웹 주소는 도구에서 접근 오류가 있었고 mirror를 통해 파일을 확보했다. APS 1966 PDF 접근은 웹 도구 오류 및 직접 요청 HTTP 401로 실패했다. 자료 접근 실패를 본문을 읽은 것으로 세지 않았다.

## 4. 무엇이 제공되고 무엇이 재구성됐는가

아래 표는 **선택한 CIF를 통해 확보한 것**의 분류다. 원 실험을 직접 수행하거나 raw 측정을 읽은 것이 아니므로 species와 격자도 이 작업에서는 측정 문헌에 연결된 기록을 통한 `DERIVED_FROM_MEASUREMENT`로 보수적으로 표시했다.

| 항목 | 상태 | 실제 확보 내용 / 제한 |
|---|---|---|
| species | DERIVED_FROM_MEASUREMENT | CIF element Ar. 동위원소와 개별 원자 식별 정보 없음 |
| position | RECONSTRUCTED | 평균 fractional 자리 하나와 대칭 연산으로 네 평균 자리를 재구성. 실제 순간 좌표 UNAVAILABLE |
| momentum | UNAVAILABLE | 개별 px,py,pz 없음. JSON null 유지 |
| lattice/structure | DERIVED_FROM_MEASUREMENT | F m -3 m, IT 225, a=b=c=5.4 Å, 각도 90°, Z=4 |
| density | DERIVED_FROM_MEASUREMENT | 점유율 1의 네 자리 / 기록된 cell 부피로 평균 bulk number density 계산. 질량 밀도·조각 밀도는 없음 |
| temperature | UNAVAILABLE | 선택 CIF에 기록 없음. 다른 논문의 온도를 붙이지 않음 |
| pressure | UNAVAILABLE | 선택 CIF에 기록 없음. 상압으로 추정하지 않음 |
| boundary/environment | UNAVAILABLE | 실제 표면·주변 원자·장치·외부 구속 상태 없음 |

동위원소 조성도 `UNAVAILABLE`다. Ar를 순수 40Ar로 치환하거나 질량을 자동 배정하지 않았다.
`_atom_site_U_iso_or_equiv=0.0`은 원문 값을 보존했지만, 의미를 검증하지 못했으므로 **열진동·zero-point effect·운동량이 0이라는 근거로 쓰지 않았다**.

## 5. 실제 prototype과 재구성 규칙

- 도구: [reality_anchored_ar_initial_state_pilot_v0.py](../../tools/reality_anchored_ar_initial_state_pilot_v0.py)
- 산출물: [initial_state_prototype_v0.json](reality_anchor_ar_v0/initial_state_prototype_v0.json)
- 시험: [test_reality_anchored_ar_initial_state_pilot_v0.py](../../tests/test_reality_anchored_ar_initial_state_pilot_v0.py)

표준 라이브러리만 쓰는 독립 도구다. A/engine/audit 물리 코드를 import하지 않는다. 실행 중 네트워크·난수·힘·에너지·시간 적분을 사용하지 않는다. source 해시가 다르면 좌표 재구성 전에 거부한다. 특정 CIF 하나를 지원하는 제한된 parser이며 범용 CIF 처리기를 주장하지 않는다.

원 자료의 평균 자리 `Ar1 (0,0,0)`, 점유율 1에 CIF의 192개 대칭 연산을 적용한 뒤 동일 fractional 대표점을 합쳤다. 결과는 다음 네 자리다. fractional 대표점 선택은 결정학 재구성을 위한 것이며 **A의 periodic motion 계약이 아니다**.

| 재구성 번호 | fractional 평균 자리 | Cartesian 평균 자리 (Å) | 운동량 |
|---|---|---|---|
| 1 | (0,0,0) | (0,0,0) | 없음 |
| 2 | (0,1/2,1/2) | (0,2.7,2.7) | 없음 |
| 3 | (1/2,0,1/2) | (2.7,0,2.7) | 없음 |
| 4 | (1/2,1/2,0) | (2.7,2.7,0) | 없음 |

번호는 출력 자리의 색인일 뿐 실험에서 식별한 원자 ID가 아니다. 네 개는 conventional cell의 대표 basis 점 수이며, 실제 물체에서 네 원자만 잘라낸 실험 기록이 아니다.

CIF의 [cell length 단위는 Å](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Icell_length_.html)이고 [fractional 좌표는 cell 기준](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Iatom_site_fract_.html)이다. 이 범위에서 Cartesian 구조 좌표 변환을 수행했다.

기록된 수치의 산술은 Fraction으로 보존했다. `27/10 Å` 같은 정확한 분수는 **기록된 5.4라는 명목값에 대한 정확한 산술**이며 현실 측정이 무오차라는 뜻이 아니다. A fixed-point q,p로 양자화하거나 기준 실행기 상태를 생성하지 않았다.

명목 cell 부피는 `157.464 Å³`, 평균 bulk number density는 `4 / 157.464 ≈ 0.0254026 atoms/Å³`다. 이 값의 측정 오차는 모른다. 이는 원 결정의 평균 템플릿에서 유도한 값이며 고립한 네 점의 물리 부피·밀도나 Small-A 밀도 계약이 아니다.

열진동/zero-point 변위·결함·동위원소·순간 위치·운동량·T/P·물리 경계·측정 불확실도는 모두 missing fields에 남겼다. 빠진 값을 0이나 통계 표본으로 채우지 않았다. 결과를 안정화하기 위한 좌표 수정도 하지 않았다.

## 6. 자르는 순간 무엇이 바뀌는가

이 네 basis 점만 물체처럼 취급하면 이상적 fcc 평균 기하에서 내부 최근접 쌍은 6개이고 각 자리마다 이웃 3개다. 원래 반복 구조에서는 최근접 이웃 12개다. 따라서 각 자리에서 **9개**, 전체 **36개의 방향 있는 최근접 이웃 연결**이 빠진다. 이는 서로 다른 외부 원자 36개라는 뜻이 아니다. 더 먼 이웃도 빠진다.

이 계산은 원래 평균 격자를 기하적으로 펼쳐 비교한 것이다. 실제 열진동이 있는 순간 샘플의 이웃 수를 측정했거나 simulation에 이웃을 공급한 것이 아니다. 같은 계산을 별도의 정수 반격자·짝수 parity FCC 표현으로 시험에서 대조했다.

네 점 내부의 pair 거리는 모두 명목 `a/√2 ≈ 3.81838 Å`다. 내부 구조를 보존해도 주변 상호작용은 보존되지 않는다. 원 결정의 에너지는 조각 내부·조각과 외부 사이·외부 내부의 기여를 포함한다. 외부를 지우면 교차 기여와 그에 따른 힘을 빼게 된다. 특정 대칭 자리에서 일부 힘이 상쇄됐을 가능성이 있어도 그 사실만으로 원래 환경과 같아지지 않는다. 이번에는 force나 energy의 변화량을 계산하지 않았다.

조각은 인공 표면이 있는 별도의 준비 상태가 된다. 원 결정에서 이미 독립적으로 존재했던 작은 물체라고 부르지 않는다. 주변을 명시적으로 포함할지, 외부 영향의 경계 표현을 승인할지, 실제 자유 표면이 있는 실험 사례를 새로 확보할지는 별도 설계 문제다. 자동 PBC를 적용하지 않았고 **C1-C D5는 PENDING**이다.

## 7. forward를 실행하지 않은 이유

현재 자료에는 p가 없고 q도 순간 측정값이 아니다. 원래 sample의 T/P와 40Ar 조성도 확인되지 않았다. 여기에 현재 기준 계약은 [두 40Ar C1-B1](../../a_reference/c1b1_two_atom.py)이고, C1-C의 다원자 합산·경계 등의 계약은 아직 미결이다.

따라서 상태를 억지로 완성하지 않고 `MISSING_DYNAMIC_STATE`로 종료했다. 1/10/100 step 모두 미실행이다. 누락 p=0, Maxwell 표본, 기존 두 원자만 뽑아서 대체 실행, 밀도 조절, 결과를 보고 샘플 교체는 하지 않았다.

이번에 확인된 기술 파이프는 **공개 구조 파일 → 출처 고정 → 평균 구조 좌표표와 누락 상태 기록**까지다. **완전한 현실 초기상태 → A 입력 → forward transition** 파이프는 미확인이다. C1-B1, D_valid, dt, Yoshida/KDK20, N-body, force accumulation, GPU, Vast에는 변경·실행이 없다. C1-B1은 여전히 NotCertified이며 이번 결과로 상태를 승격하지 않는다.

## 8. 역계산 survey

현실 관측에서 가능한 원인을 제한하는 것은 유용하지만 A의 전진 법칙과 역할이 다르다.

- **구조 후보:** [RMCProfile7 원 논문](https://journals.iucr.org/j/issues/2024/04/00/yr5127/index.html)의 서론은 산란 자료에 맞게 많은 원자의 위치를 조정하는 방법을 설명한다. 이런 결과는 관측과 양립하는 구조 후보다. 특정 순간의 원자 배치가 직접 측정됐다는 뜻이 아니다. 이번에는 RMC를 설치하거나 실행하지 않았다.
- **상호작용 후보:** 위 Magli 외 Ar 실험은 S(k)로 장거리 상호작용 계수를 제한하는 사례다. 관측량의 처리·모델 가정 아래 얻은 추론이며 그 값을 A의 새 참 법칙으로 넣지 않았다.
- **비유일성:** 유한한 거리/파수 범위와 오차가 있는 밀도·g(r)·S(q)는 대체로 수많은 미시 배치와 양립한다. 운동량이나 원자 정체도 복원하지 않는다. 불완전한 관측 아래 상호작용·다체항·환경 효과의 설명이 여러 개일 수 있다.
- **유일성에 관한 예외:** [Frommer, Hanke, Jansen의 inverse Henderson 연구](https://arxiv.org/abs/1903.03317)는 지정된 평형 온도·밀도와 pair correlation, 정해진 pair-potential 허용 클래스 등 조건 아래 유일성 결과를 다룬다. 따라서 모든 역문제가 원천적으로 비유일하다고 주장하지 않는다. 이 제한된 유일성은 실험의 불완전한 통계로 특정 순간 q,p를 알아낸다는 뜻이 아니다.

즉 **현실 관측 → inverse inference → 가능한 구조/원인 후보**는 외부 연구 단계이고, **A의 승인된 법칙 + 현재 상태 → 다음 상태**는 세계 실행 단계다. 통계에 맞춘 후보나 fitted potential을 A의 진실로 자동 편입하지 않았다.

## 9. 검증 결과와 구상 일치성 재점검

2026-10-02 새로 실행한 명령:

```text
python -m pytest tests/test_reality_anchored_ar_initial_state_pilot_v0.py tests/test_c1a_freeze.py -q
```

**14 passed / 실패 0 / error 0 / skip 0 / xfail 0, 1.53초**.
Junit 기록과 stdout 로그는 아래에 보존했다. Git의 sha256sum 경로를 시험 subprocess PATH에 넣어 동결 원문 해시 검사가 skip되지 않도록 했다.

- [pytest stdout](../../runs/reality_anchored_ar_initial_state_pilot_20261002_v0/pytest_related.log)
- [junit](../../runs/reality_anchored_ar_initial_state_pilot_20261002_v0/pytest_related.xml)

검증한 것은 원자료 바이트·네 자리 좌표·빠진 상태 유지·별도 FCC 표현과 경계 이웃 수 대조·변조 파일 거부·위험한 대칭 표현 거부·오프라인 JSON 재현성·도구의 import 범위·기존 C1-A 동결 계약이다. 실험 원데이터 감사·물리 모델 정확성·현실 이행·지역 인증·생명 검증은 아니다.

자동 시험과 별도로 요청의 의미를 다시 점검했다. 다음 표는 작성자의 구상 일치성 재점검이며 독립 에이전트 승인을 뜻하지 않는다.

| 사용자 의도 | 실제 산출물과 대조 |
|---|---|
| t=0만 현실에서 가져오기 | 가져온 것은 평균 구조뿐. 미래 결과 자료를 주입하지 않음 |
| 없는 정보를 발명하지 않기 | p/T/P/isotope/boundary null, 순간 q missing, Uiso 0.0을 무진동으로 해석하지 않음 |
| 현실/재구성/통계를 구분 | 고체 R2, 액체·기체 R3, R0/R1 확보 실패 범위를 명시 |
| 작은 조각의 인공 경계 공개 | 자리당 최근접 이웃 9개 손실 및 힘/에너지 환경 변경 공개 |
| 미결 C1-C 보존 | 네 자리 수는 출력 basis 수, N 선택 아님. D5 PENDING, production 연결 없음 |
| 비용·실행 범위 제한 | 작은 로컬 구조 처리와 관련 시험만 실행, forward 0, 원격 비용 없음 |

**LOCAL FULL 생략 / 관련 시험으로 대체 / 이유:** 신규 독립 prototype·시험·자료·보고서와 문서 색인 링크만 추가/수정했고 기존 실행 코드·공용 모듈·동결 fixture·계약을 변경하지 않았다. 공식 LOCAL FULL 기준선 숫자는 갱신하지 않았다.

## 10. 읽은 범위, Git 및 산출물 상태

저장소 시작 문서 AGENTS.md·RULES.md를 읽었고 CURRENT_STATE.md·REPO_MAP.md는 이번 Gate 및 해당 모듈 범위를 읽었다. C1-C proposal의 상태·미결 결정 목록, A_REALITY_GROUNDING_V1의 관련 부분, C1-B1 두 원자 모듈의 계약 설명과 C1-A 단위 상수를 확인했다. 큰 문서 전체·runs 전체를 읽은 것으로 보고하지 않는다.

학술 자료는 위 후보 표의 읽기 범위를 따른다. RMCProfile7 서론과 inverse Henderson 초록·서론·가정의 관련 부분, IUCr 단위·좌표 정의를 읽었다. 모든 논문을 끝까지 읽거나 원 실험을 재감사했다고 주장하지 않는다.

| 항목 | 상태 |
|---|---|
| start HEAD | `015c108324876c059110bbe53f647d85265cf075` |
| end HEAD | `015c108324876c059110bbe53f647d85265cf075` |
| origin/master | `015c108324876c059110bbe53f647d85265cf075` |
| ahead/behind | 0/0 |
| start dirty | 없음 |
| end dirty | 아래 신규 6개 파일 + 문서 색인 2개 수정 |
| tests | 14 passed, 1.53초, skip/xfail/실패/error 0 |
| LOCAL FULL | 생략, 관련 시험 대체. 공식 기준선 유지 |
| commit | 하지 않음 |
| push | 하지 않음 |

변경 파일:

1. 이 보고서 신규 추가.
2. `docs/proposals/reality_anchor_ar_v0/1541541.cif` 신규: 원자료 바이트 보존.
3. `docs/proposals/reality_anchor_ar_v0/initial_state_prototype_v0.json` 신규: R2 평균 구조와 누락 상태.
4. `tools/reality_anchored_ar_initial_state_pilot_v0.py` 신규: 격리된 구조 재구성 도구.
5. `tests/test_reality_anchored_ar_initial_state_pilot_v0.py` 신규: 출처/경계/누락 상태 시험.
6. `docs/proposals/README.md` 수정: 이 pilot 링크.
7. `docs/DOCUMENT_STATUS_INDEX.md` 수정: 이 pilot의 상태 링크.
8. `docs/proposals/reality_anchor_ar_v0/.gitattributes` 신규: 이 CIF 하나의 원문 줄바꿈 보존.

Git 제외된 `runs/reality_anchored_ar_initial_state_pilot_20261002_v0/`에는 다운로드 원본·시험 로그·재현성/최종 범위 점검 기록을 따로 보존한다. 이 기록은 production 변경 파일에 포함하지 않는다.

다음 정보가 생기기 전에는 이 prototype으로 A를 시작할 수 없다: 실험적으로 근거 있는 완전한 동역학 초기상태 또는 누락 상태 준비를 위한 별도 설계자 계약, 동위원소 정합성, 환경과 경계, 다원자 계약. 이는 후속 작업의 조건이며 이번에 승인하거나 구현하지 않았다.

방법론 참고: 이번 보고서의 관측/추론 분리에는 저장소의 scientific-critical-thinking skill을 적용했다. Kassis, Agarwal, He, Patel, Brueckner (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). 2026-10-02 arXiv 최신 record(v2)을 확인했다. 이 문헌은 Ar 측정값의 출처가 아니다.
