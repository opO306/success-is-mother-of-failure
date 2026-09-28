# A 계산·증명 Warehouse 아키텍처 V1
## 계산 결과 → 검수 → 분류 → 저장 → 재사용 → 의존성 추적 → 필요한 부분만 재계산

**문서 상태:** PROPOSAL / 설계 전용 (2026-09-28).
**구현 상태:** **미구현.** 이 문서를 근거로 코드를 만들지 않는다. 설계자 승인 전에는 기존 계산 구조를 한 줄도 바꾸지 않는다.
**현재 활성 Gate:** C1-B1 outer formal bound ④. 이 문서는 ④의 완료·인증 근거가 아니다.
**현재 기준 상태(이 문서 작성 시점):** ④-4c-10 설계자 판정으로 shell 16 인증이 승인되어 driver(`a_reference/c1b1_hard_case_certificate_shell16.py`)만 추가된 상태. shell 16 인증서·fresh coverage는 아직 생성 전. 직전 확정 coverage **13/64 region·gap 82**, **④-4b NotCertified**, precision cap **16384**, LOCAL FULL 기준선 **2815 passed + 1 strict xfailed, skip 0**.
**상태 갱신(개정 1 뒤, 2026-09-28):** shell 16 인증은 이 문서와 별도로 master에서 끝났다(`0117cd8`, 문서·검증 `d236842`). fresh coverage **14/64 region·gap 81**, LOCAL FULL 기준선 **2834 passed + 1 strict xfailed, skip 0**, ④-4b는 여전히 NotCertified다. 이 문서는 그 인증 경로를 건드리지 않았다.
**B와의 관계:** Warehouse는 연구자 B가 아니라 **세계 밖 설계자·감사 도구**다(헌법 제24조). B는 Warehouse의 존재도 내용도 모른다.
**개정 1 (2026-09-28, 설계자 판정 반영):** Q1을 세 축 상태 모델로 대체했다(6절). 해시를 셋으로 나누고 artifact 정체성을 내용 해시와 분리했으며, 자료형 추측 대신 명시적 mapper를 쓴다(7절). registry는 정본이 아닌 파생 인덱스로 정의했다(13절). Q2~Q8은 승인됐다(17절). **문서만 바꿨다. Warehouse 코드는 여전히 미구현이다.**

---

## 0. 먼저 읽을 것 — 이 문서가 금지하는 것

이 문서는 "아이디어는 설계에 반영하되, 지금 진행 중인 반올림 인증 경로는 건드리지 않는다"를 최상위 조건으로 둔다.

| 금지 | 이유 |
|---|---|
| 현재 shell survey / certificate / generator / checker 경로 수정 | 인증서 fixture가 이 파일들의 source 해시를 고정한다(12절 C2). 한 글자만 바꿔도 shell 18·17 인증서가 `foundation provenance changed`로 거부된다 |
| 해시가 고정된 fixture 재생성·형식 변환 | `prior_fixture_sha256`가 상위 fixture의 파일 바이트를 고정한다. 들여쓰기만 바꿔도 하위 인증서가 stale이 된다 |
| Warehouse를 이유로 shell 16 인증 일정·결과 변경 | shell 16은 승인된 살아 있는 작업선이다. Warehouse는 그 결과가 나온 **뒤에** 그것을 등록하는 쪽이다 |
| 기존 인증 계약(`c1b1-hard-case-certificate-v1` 등)에 필드 추가 | 계약 모듈 수정 = source 해시 변경 = 기존 인증서 무효 |
| 기존 계산기 대규모 리팩터링, certificate 형식 일괄 변환, R<20 adaptive proof engine, 자동 셀 분할, GPU scheduler | 전부 ④가 정리된 뒤 별도 Gate(14절) |

**Warehouse v0는 기존 결과를 읽기만 하고(read-only), 밖에서 metadata를 붙여 등록만 한다(13절).** 기존 파일은 바이트 하나도 바뀌지 않아야 한다.

---

## 1. 왜 이 문서가 필요한가 — 기존 제안과의 관계

이 저장소에는 이미 "창고"를 **이름으로** 부르는 제안이 셋 있다. 이 문서는 그것들과 경쟁하지 않고, 셋이 모두 필요로 하지만 아무도 설계하지 않은 **저장·metadata·의존성 계층**을 설계한다.

| 기존 문서 | 그 문서가 맡는 것 | 이 문서가 맡는 것 |
|---|---|---|
| [A 증명 조립 아키텍처](A_PROOF_COMPOSITION_ARCHITECTURE_V1.md) | 분할·lemma·proof object·verifier·adaptive refinement의 **논리 구조**. 5.4절 "Proof Warehouse"는 최소 저장 정보 9개만 나열 | 그 5.4·5.5절의 **실제 골조**: artifact schema, 증거 수준, 의존성 종류, 저장 backend, API, 재계산 규칙 |
| [A 증명 조립 로드맵](A_PROOF_COMPOSITION_ROADMAP_V1.md) | Phase 6 Proof Warehouse, Phase 7 dependency graph의 **순서** | Phase 6·7의 설계 내용과, 그 전에도 해도 되는 read-only v0의 범위 |
| [A 계산·메모리·기록 아키텍처 제안](A_COMPUTE_MEMORY_RECORD_ARCHITECTURE_PROPOSAL.md) | **세계 실행**의 계산·메모리·기록(snapshot + 외부 입력 = authoritative history, 나머지는 파생 cache) | **증명·계산 결과**의 저장. 세계 역사는 다루지 않는다. 저장 계층(RAM/NVMe/HDD)의 기준은 그 문서 5.5절과 맞춘다 |
| [A 실행 증명서 제안](A_RUNTIME_CERTIFICATE_PROPOSAL.md) | Proof Atom → Segment → Box → Domain 계층 | 그 계층을 담을 artifact 종류(5절)와 의존성 표현 |
| [연구 데이터 저장소 v1](../deferred/RESEARCH_STORE_V1.md) | **B 연구 데이터**의 신뢰 등급별(b_visible/evaluator/ground_truth) 저장 | 별개의 저장소. 단, 그 문서가 증명한 **계약 기법**(내용 해시 이름, 추가 전용 해시 체인, 필수 `semantics`, `commit`/`dirty` 출처)을 그대로 빌려 쓴다(8절) |

한 줄로: **증명 조립 문서는 "무엇을 어떻게 증명하는가", 이 문서는 "증명한 것을 어디에 어떤 꼬리표로 두고, 언제 다시 계산하는가"다.**

---

## 2. 기본 철학 — 물류창고

Warehouse는 파일을 담는 폴더가 아니라 다음을 관리하는 **시스템**이다.

```text
계산 결과 → 검수 → 분류 → 저장 → 재사용 → 의존성 추적 → 필요한 부분만 재계산
```

| 물류창고 | 이 프로젝트의 실제 대상 | 현재 코드에서 이미 있는 것 |
|---|---|---|
| 물품 | 계산 결과 하나(artifact) | `a_reference/fixtures/c1b1_*.json` 32개 + `ar2_lang2024_c1a_v1.json` (Git), `runs/` 결과(Git 밖, D:) |
| 완성품 | certificate / proof (region·shell·domain·최종 C1-B1) | shell 18·17 hard-case 인증서, family 인증서 5개, half-ulp 인증 3개 |
| 개별 부품 | 작은 bound / cell / result | force bound, guard G, residual 구간, 도함수 상한 행(superblock 1024행), class 하한 |
| 바코드 | artifact_id(정체성)·payload_hash(내용) — 7.3절 | `source_sha256`, `foundation_sha256`, `prior_fixture_sha256`, `domain_hash` (전부 SHA-256) |
| 조립표 | dependency graph — 어떤 부품으로 어떤 완성품이 만들어졌나 | 인증서 안의 세 종류 해시 + coverage compositor의 층 순서(코드로만 존재) |
| 검수원 | independent checker / verifier | `c1b1_hard_case_checker.py`(생성기 import 금지), `c1b1_family_checker.py`, `c1b1_same_input_checker.py` |
| 피킹 시스템 | scheduler — 아직 증명되지 않은 영역만 골라 작업자에게 | 없음. 사람이 shell 번호를 정해 driver를 만든다 |
| 작업자·설비 | CPU / GPU / exact 계산기 | `ProcessPoolExecutor` 6·32 워커, native CPU/CUDA(세계 실행기 아님) |

핵심은 비유가 아니라 **권한 경계**다(증명 조립 문서 2절과 동일). 창고는 보관·색인·추적만 한다. 판정은 checker가, 승격은 fresh coverage와 설계자가 한다. **창고 안의 `status` 필드를 믿고 인증으로 쓰는 일은 없다.**

---

## 3. 가장 중요한 원칙 — 계산 생략이 아니라 무손실 압축

계산 효율화를 위해 **어떤 상태나 변수도 임의로 무시하지 않는다.** 각도·좌표·방향 같은 변수를 계산 상태에서 제거하려면 다음 셋 중 하나가 **증명으로** 있어야 한다.

1. 물리적/수학적으로 동등하다는 증명 (예: 대칭으로 두 상태가 같은 결과를 낸다)
2. 축약된 변수에 필요한 정보가 완전히 보존된다는 증명 (예: 상대 좌표 tube)
3. 제거된 변수의 가능한 모든 영향이 엄밀한 bound 안에 포함된다는 증명 (예: 방향 성분의 impulse 기여를 |I| 상한으로 덮음)

셋 다 없으면 그 변수는 계산 상태에 남긴다.

| 허용 | 금지 |
|---|---|
| 많은 상태 전체가 하나의 엄밀한 범위(enclosure)에 포함됨을 증명하고, 그 범위에서 판정 | 대표 몇 개를 계산해서 나머지도 같다고 가정 |
| 양 끝점 + 도함수 상한 + 보간 오차 δ로 구간 전체를 감싼 뒤 T=G+δ로 판정(④-4c-5·6의 실제 방식) | 양 끝이 안전하니 가운데도 안전하다고 봄 |
| 3D 상대 좌표를 1D로 줄일 때 좌표 tube·direction projection을 **먼저 증명**(④-4b, `c1b1_reachable_geometry.py`) | 궤적 몇 개를 돌려 보고 "평면에서 안 벗어나더라"로 축소 |

이 원칙은 새 규칙이 아니다. RULES의 "손실 요약은 결과가 같다는 것을 증명하기 전에는 금지", 실행 아키텍처 X3 "캐시는 정확한 입력 전체가 같을 때만", 증명 조립 문서 4.1 "원래 domain을 줄이지 않는다"·8.2 "보간은 error enclosure 없이는 증명이 아니다"를 **저장 계층에도 똑같이 적용**하는 것이다. 특히 Warehouse에서는 다음을 뜻한다.

- **중복 제거(dedup)는 artifact_id(7.3절)가 정확히 같을 때만.** payload가 같아도 domain·계약·proof method가 다르면 다른 artifact다. "domain이 비슷하다", "같은 shell이다"로 결과를 재사용하지 않는다.
- **survey_only 결과는 절대 인증 입력이 되지 않는다.** 표본 몇 점의 최소값은 그 점에만 해당한다(④-4c-1의 원칙 그대로).

---

## 4. 거시/미시 통합 계산 구조 — 장기 목표, 현재 ④에는 적용하지 않음

미래의 R<20 formal proof 같은 문제에서는 상태 하나씩이 아니라 **상태공간의 영역 전체를 하나의 Cell**로 계산할 수 있어야 한다.

```text
Cell
  R   = [7.0, 7.1]
  p_r = [...]
  L   = [...]
  E   = [...]
  θ   = [...]    # 3절의 증명으로 제거되지 않은 경우에만 남긴다
```

- 큰 Cell 전체를 엄밀한 bound로 처리할 수 있으면 그대로 인증한다.
- 처리할 수 없으면 **그 Cell만** 세분화한다. 처음부터 전부 미세하게 나누지 않는다.

```text
Large Cell
├─ Certified
└─ Unresolved
     ├─ Certified
     └─ 다시 분할
```

즉 **거시 영역부터 계산 → 어려운 영역만 미시적으로 확대**하는 adaptive refinement다(증명 조립 문서 7절과 같은 내용이며, 중단 조건도 그 문서를 따른다: class 폭발, 같은 유형의 unresolved 반복, 전수보다 비싸짐, 상관관계 상실).

**현재 코드와의 대응 — 정직하게:**

| 개념 | 지금 있는 것 | 없는 것 |
|---|---|---|
| Cell | `domain.kind = axis_lattice_interval {axis, lo, hi}`(1차원 축 격자), `finite_points`, valuation/residue **class** 행 | R·p_r·L·E·θ 다차원 구간 Cell. ④-4b는 3D→1D projection **뒤**의 1차원 문제라 아직 필요가 없다 |
| Cell 예산 | 64-region(`R.MAX_REGIONS`), boundary/candidate 작업 한도 64, 후보 2^20 | 예산은 **증명 쪽 작업 한도**다. 물리 cap이 아니며 Warehouse가 물리 한계로 취급해서는 안 된다 |
| 분할 | shell → domain → superblock(1024) → block(2^34+1점) | 실패한 Cell만 골라 자동으로 더 나누는 코드 |

이 절의 내용은 **④에 바로 구현하지 않는다.** v0에서는 domain을 **종류가 붙은 불투명 객체 + 정규 해시**로만 다루고(7절), 다차원 Cell 스키마는 R<20 트랙에 착수할 때 별도 설계한다.

---

## 5. Proof를 레고처럼 — 부품과 완성품

계산 결과를 두 종류로 나눈다.

| 구분 | artifact_type 후보 | 현재 코드의 실제 예 |
|---|---|---|
| **Proof Atom / 부품** | `force_bound`, `derivative_bound`, `rounding_bound`, `transition_bound`, `domain_cell`, `candidate_result`, `crossing_result`, `class_bound`, `small_proof` | 원인별 1-step bound(④-1), residual 구간·numeric error·guard G, superblock 행(도함수 상한·교차 수·후보 구간), 후보 109/827/6,581개의 정확 재평가, class 하한 6,436개 |
| **Composite Proof / 완성품** | `region_proof`, `shell_certificate`, `domain_certificate`, `coverage_report`, `final_c1b1_certificate` | shell 18·17 인증서, family 인증서 5개, half-ulp 인증 3개, fresh coverage 보고(13/64·gap 82), (미래) C1-B1 최종 인증 |

완성된 certificate에는 **어떤 부품·어떤 코드·어떤 계약으로 만들어졌는지** 추적할 수 있어야 한다.

```text
Certificate shell18 (c1b1-hard-case-certificate-v1)
├─ Domain           axis_lattice_interval [312500000000000000, 390625618227463140]  (domain_hash)
├─ Guard G          residual 4096-bit enclosure + numeric endpoint error(4096-bit 진단)
├─ Rows ×1024       도함수 상한 · 교차 수 · 후보 구간 (block_points = 2^34+1)
├─ Candidates 109   전부 정확 P/Q 재평가, hazard 0
├─ Numeric Contract FX(96,80) momentum, required_bits 4096 ≤ execution_limit ≤ 16384
├─ Foundation ×6    ar2_lang2024 · axis_decision_bounds · rounding_regions · two_atom · a_numeric/exp · hard_case_checker (해시)
├─ Checker          verify_certificate (source 해시)
└─ Verdict          설계자 판정 ④-4c-6
```

**부품 하나라도 빠지면 전체 certificate를 Certified로 취급하지 않는다.** 지금 이미 그렇게 동작한다: `verify_certificate`는 위 항목을 **전부 다시 계산해 정확히 같은지** 보고, 하나라도 다르면 `NotCertified`를 던진다. Warehouse는 이 판정을 대신하지 않고, 판정에 쓰인 부품 목록을 **조립표로 기록**한다.

현재 coverage compositor가 이 조립의 원형이다: `rounding_regions → half_ulp_boundaries → family_certificates → hard_case`의 네 층이 각각 **독립 검증된 domain만으로** 앞 층의 미피복 구간을 줄이고, 전체 region 수가 64를 넘으면 거부한다. 다만 이 층 순서는 **코드**로만 존재한다(12절 C4).

---

## 6. 상태를 한 칸에 섞지 않는다 — 세 축 상태 모델 (개정 1)

**개정 1 (설계자 판정, 2026-09-28):** 초판은 RAW·SURVEY_ONLY·CHECKED·CERTIFIED·STALE·REJECTED·UNRESOLVED·COUNTEREXAMPLE을 `evidence_level` 한 칸에 넣었다. 이것들은 서로 다른 종류의 정보라 한 칸에 들어가지 않는다. Q1을 아래 **세 축** 모델로 대체한다. 초판은 6.2절에서 "artifact의 신뢰 수준과 claim은 다른 축"이라고 적어 놓고 6.1절에서 다시 한 enum에 섞었다. 이 개정이 그 자기모순을 없앤다.

### 6.0 왜 한 칸이 안 되는가

| 실제 상황 | 한 칸 모델의 문제 | 세 축 모델 |
|---|---|---|
| 반례를 막 발견했고 아직 아무도 검증하지 않았다 | RAW와 COUNTEREXAMPLE 중 하나만 고를 수 있다 | `RAW` + `ACTIVE` + claim `counterexample` |
| 완전히 검증된 인증서의 foundation 파일이 바뀌었다 | STALE로 바꾸면 "CERTIFIED까지 검증됐었다"는 사실이 지워진다 | `CERTIFIED` + `STALE` (검증 이력 보존) |
| survey가 실제 hazard witness를 찾았다 | SURVEY_ONLY와 COUNTEREXAMPLE이 충돌한다 | usage `survey_only` + claim `counterexample` |
| coverage 보고서는 검증됐지만 "gap 82, 미인증"이라고 말한다 | CHECKED만 보면 영역이 인증된 것처럼 읽힌다 | `CHECKED` + `ACTIVE` + claim `not_certified` |

### 6.1 축 1 — `verification_level`: 지금까지 어디까지 검증됐나

| 값 | 뜻 | 올라가는 조건 |
|---|---|---|
| `RAW` | 등록만 됐다. 선언된 `status`가 무엇이든 검증 기록이 없다 | 기본값 |
| `CHECKED` | 독립 checker가 다시 계산해 통과했다는 **검증 기록**이 있다 | 검증 기록(7.5절) 첨부. 선언 status로는 절대 오르지 않는다(Q2 승인) |
| `CERTIFIED` | CHECKED + 이 artifact를 소비한 fresh coverage가 CHECKED + 설계자 판정 기록 | 세 조건 모두의 기록 |

- **이 축은 이력이라 떨어지지 않는다.** 지금 믿어도 되는지는 축 2와 함께 읽는다.
- report 종류(coverage 보고서 등)의 최고 수준은 CHECKED다. CERTIFIED는 인증 입력이 되는 artifact에만 의미가 있다.
- 증명 조립 문서 11절의 세부 사다리(`proof_object_generated → independent_verified → coverage_candidate → coverage_recomputed → certified`)는 CHECKED와 CERTIFIED 사이의 하위 기록으로 남긴다.

### 6.2 축 2 — `lifecycle_state`: 그 검증이 지금도 유효한가

| 값 | 뜻 | 전이 |
|---|---|---|
| `ACTIVE` | 검증 당시의 의미상 의존성·checker 해시가 지금 저장소와 같다 | 기본값 |
| `STALE` | 의미상 의존성(7.4절) 또는 검증에 쓴 checker의 해시가 바뀌었다 | registry 재생성 때 **자동 계산**한다. 신뢰를 낮추는 전이라 자동을 허용한다. 원인 간선을 기록한다 |
| `REJECTED` | checker가 거부했거나 변조·위조가 확인됐다 | `result: fail` 검증 기록 또는 위조 증거가 있을 때만 |

- **신뢰를 낮추는 전이는 자동, 올리는 전이는 검증 기록 필수.** STALE에서 ACTIVE로는 현재 해시에서 새로 검증한 기록이 붙을 때만 돌아간다.
- **REJECTED는 스스로 풀리지 않는다.** 같은 artifact에 `fail` 기록이 하나라도 있으면, 나중에 다른 checker가 `pass`를 내도 REJECTED로 둔다. 새 checker가 약해져서 통과시켰을 수도 있기 때문이다. 되돌리려면 원인을 적은 설계자 판정 기록이 필요하다.
- REJECTED·STALE artifact도 지우지 않는다(RULES "실패를 삭제하지 않는다").

### 6.3 축 3 — `claim`: 무엇을 말하고 어디에 쓸 수 있나

설계자 판정의 claim/usage 축을 **두 필드**로 적는다. 6.0절 셋째 줄처럼 "survey가 찾은 반례"는 두 값을 동시에 가져야 하기 때문이다(17절 Q10). 값은 소문자로 쓴다. 기존 fixture의 status 어휘(`survey_only`, `certified`, `not_certified`)와 같고, 대문자인 축 1의 `CERTIFIED`와 눈으로 구별된다.

`claim.status` — artifact가 자기 domain에 대해 주장하는 내용:

| 값 | 뜻 | 예 |
|---|---|---|
| `certified` | 선언한 domain 전체가 인증됐다고 주장 | shell 18·17 인증서, family group 5개, half-ulp group 3개 |
| `not_certified` | 미인증 부분이 남았다고 주장 | coverage 보고서(gap 82), family·half-ulp 묶음 보고서 |
| `unresolved` | 현재 방법으로 판정하지 못함. 반례라는 뜻이 아니다 | E_min 조건부 후보 |
| `counterexample` | 실제 반례·hazard witness가 있다고 주장 | 현재 0개 |
| `measurement` | 수치 검증 증거. 형식 증명이 아니다 | D_valid, orbit·inner validation |
| `observation` | 탐색·표본 관측. 아무것도 인증한다고 주장하지 않는다 | 각종 survey |
| `none` | 주장 없음 | study·compare·example 자료 |

`claim.usage` — 이 artifact를 어디에 써도 되나:

| 값 | 뜻 |
|---|---|
| `survey_only` | **인증 입력 금지.** 설계·비용 판단용 |
| `certification_input` | 6.4절 조건을 모두 만족할 때만 인증·coverage 입력이 된다 |
| `report` | 판정 결과 보고서. 다른 인증의 입력으로 쓰지 않는다 |
| `reference` | 기준값·측정 자료(fixture 대조용) |

- `claim.usage`와 `claim.status`는 **artifact 종류로 정한다**(mapper가 `version` 접두어로 결정). 파일 안의 `status` 문자열로 정하지 않는다. 종류와 선언 status가 모순이면 등록을 거부한다(13.6절).
- 기존 필드(`status`, `scope`, `global_4_4b`, `actual_trajectory_membership` …)는 `claim.declared`에 원문 그대로 보존한다.

### 6.4 세 축을 합치는 규칙 — 인증 입력이 되는 유일한 조합

```text
verification_level == CERTIFIED
and lifecycle_state == ACTIVE
and claim.usage     == certification_input
and claim.status    == certified
```

- 이 네 조건을 모두 만족하는 artifact만 다른 인증·coverage의 입력이 된다. 하나라도 어긋나면 입력이 아니다. `survey_only`는 어떤 경우에도 이 조합에 들어오지 못한다(12절 C5).
- `find()`는 `verification_level`과 `lifecycle_state`를 **둘 다 반드시** 받는다. 기본값이 없다(연구 저장소의 필수 `semantics`와 같은 방식).
- 인증 입력 조회는 위 조합을 코드로 고정한 `certification_inputs()`만 쓴다.
- 이 조합은 **창고 쪽 조회 규칙**이다. 실제 인증은 지금처럼 checker가 다시 계산해서 판정한다(Q3: ④ 동결 전 full re-verify). 창고의 축 값이 checker를 대신하지 않는다.

### 6.5 조합 예시

| 상황 | verification_level | lifecycle_state | claim.status | claim.usage |
|---|---|---|---|---|
| shell 18 인증서, 검증 기록 첨부 전 | RAW | ACTIVE | certified | certification_input |
| 같은 인증서, LOCAL FULL 통과 기록 첨부 | CHECKED | ACTIVE | certified | certification_input |
| fresh coverage 소비·판정 기록까지 | CERTIFIED | ACTIVE | certified | certification_input |
| 그 뒤 `a_numeric/exp.py`가 바뀜 | CERTIFIED | **STALE** | certified | certification_input |
| 이후 새 검증에서 거부됨 | CERTIFIED | **REJECTED** | certified | certification_input |
| coverage 보고서 13/64·gap 82 | CHECKED | ACTIVE | not_certified | report |
| shell 16 survey, 검증 기록 첨부 전 | RAW | ACTIVE | observation | survey_only |
| survey가 실제 witness를 찾음 | RAW | ACTIVE | counterexample | survey_only |
| 그 반례를 별도 정확 재평가로 확인 | CHECKED | ACTIVE | counterexample | report |
| E_min 조건부 후보 | RAW | ACTIVE | unresolved | report |
| D_valid v2 기준 fixture, 검증 기록 첨부 뒤 | CHECKED | ACTIVE | measurement | reference |

### 6.6 기존 어휘 → 세 축 매핑 (기존 파일은 바꾸지 않는다)

| 기존 값 (fixture/코드) | 나오는 곳 | claim.status / usage | 비고 |
|---|---|---|---|
| `status: survey_only` | hard-case survey 18·17·16, modular-distance·residue-class·quotient-gap·fractional-phase·same-input survey (8개) | observation / survey_only | witness가 있으면 counterexample / survey_only |
| `status: certified` | shell 18·17 인증서 | certified / certification_input | verification_level은 검증 기록으로만 |
| 묶음 보고서 안의 certified group | family 5개, half-ulp 3개 | certified / certification_input | 묶음 자체는 not_certified / report. `contained_in` 간선 |
| `status: not_certified` 보고서 | rounding_regions, rounding_diagnosis, half_ulp, family | not_certified / report | |
| 인증서·보고서 안의 `coverage` 객체 | shell 18·17 인증서, family·half-ulp 보고서 | not_certified / report | used_regions·gap 원문 보존 |
| `global_4_4b: NotCertified` | 거의 모든 fixture | `claim.declared`에 보존 | 축 값에 영향 없음 |
| `NUMERICALLY VALIDATED …`, D_valid `numerical_validated`·`unsupported` | orbit_boundary v1·v2·v3, orbit_validation, inner_validation, inner_energy, D_valid | measurement / reference | CERTIFIED 입력 불가. D_valid와 analytic certificate는 자동 연결이 없다 |
| `formal_certified` | D_valid 코드에 이름만 존재, 도달 상태 없음 | 매핑하지 않음 | 이름이 있다는 이유로 값을 만들지 않는다 |
| `CONDITIONAL CANDIDATE -- not certified (C2, C4, C5 open)` | `c1b1_emin_candidate_v2.json` | unresolved / report | 열린 조건 보존 |
| `status` 필드 없음 | study·compare·example 12개 | none / reference | 없는 것을 지어내지 않는다 |
| 증명 조립 문서의 `counterexample`, `invalid_evidence` | 제안 4.2절 | `counterexample`는 claim.status, `invalid_evidence`는 lifecycle `REJECTED` | |

증거가 없는 곳은 **모른다고 기록한다.** 비용을 모르면 `compute_cost: unknown`, 검증 기록이 없으면 `RAW`로 남긴다.

---

## 7. Warehouse의 최소 고정 골조 — artifact schema (개정 1)

**개정 1:** 해시를 셋으로 나눴다(7.2절). artifact 정체성을 내용 해시와 분리했다(7.3절). 자료형으로 의미를 추측하던 "float면 측정값" 규칙을 없애고 mapper가 명시적으로 나눈다(7.2절). 검증 기록 형식을 정했다(7.5절).

장기간 유지될 핵심 계약은 작게 만든다. 각 artifact는 최소한 다음을 가진다.

```text
artifact_id            # 7.3절 정체성 해시. payload_hash와 다르다
payload_hash           # = content_hash. semantic_payload의 정규 직렬화 SHA-256
raw_file_sha256        # 파일 바이트 그대로의 SHA-256
legacy_lf_sha256       # CRLF→LF 정규화 뒤 SHA-256. 기존 source_sha256·prior_fixture_sha256 pin과 같은 규칙
schema_version         # 이 schema의 판
artifact_type          # 5절의 종류
domain, domain_hash    # 종류가 붙은 domain 객체(기존 그대로) + 정규 해시
model_contract         # 계약 id 묶음: c1b1-two-atom-v2, c1b1-dvalid-v2, c1a-ar2-lang2024-v1, model_fingerprint
numeric_contract       # profile FX(96,48)/FX(96,80), Δt, required_bits, residual_bits, precision_cap (구조체, 문자열 아님)
proof_method           # 예: hard-case-quadratic-v1, rational-spacing-family-v1. 없으면 none
semantic_payload       # 주장과 증명 자료. mapper가 명시한 필드만
semantic_dependencies  # 정체성에 들어가는 간선 (7.4절)
provenance_edges       # 정체성 밖의 간선: producer 코드, contained_in, verdict (7.4절)
run_metadata           # wall·CPU 시간, worker 수, host, 실행 날짜, 비용 측정표. 해시·정체성 밖
compute_cost           # run_metadata에서 요약. 없으면 unknown
verify_cost            # 같은 형식 또는 unknown
verification_level     # 6.1
lifecycle_state        # 6.2 (+ stale_causes)
claim                  # 6.3: status, usage, declared
verification           # 7.5절 검증 기록 (attestation log에서 읽는다)
storage_location       # {backend, path, available_here}
designer_verdict       # 판정 id(예: ④-4c-6) 또는 none
aliases                # 예: "c1b1-hard-case-certificate-v1/shell18"
```

**한 파일 = 한 artifact가 아니다.** `c1b1_family_certificates_v1.json`은 최상위 `status: not_certified`(보고서)이지만 안에 `certified` group 인증서 5개와 coverage를 담는다. half-ulp fixture는 27개 group 중 3개가 certified다. 등록기는 묶음 파일을 `report` artifact 하나로, 내부 인증서를 각각 별도 artifact로 등록하고 `contained_in` 간선(7.3절)으로 잇는다. 그렇지 않으면 "보고서가 not_certified니까 안의 인증서도 미인증" 또는 그 반대의 오독이 생긴다.

필요한 필드는 추가할 수 있다. 그러나 **계산 코드는 이 저장 형식에 직접 종속되지 않는다.** 계산 코드는 지금처럼 자기 JSON을 만들고, Warehouse가 밖에서 읽어 이 schema로 등록한다.

### 7.1 기존 fixture 필드 → schema 매핑 (등록 시 추출 가능한 것)

| schema 필드 | 지금 fixture에 있는 것 | 비고 |
|---|---|---|
| `artifact_type`, `aliases` | `version` (예: `c1b1-hard-case-certificate-shell17-v1`), `shell_index` | 접두어 규칙으로 종류 결정 |
| `domain`, `domain_hash` | `certificate.domain`, `certificate.domain_hash`, `expected_domain`, survey의 `domain{lo,hi,lattice_points}` | 인증서는 해시가 있고 survey는 없다. v0가 계산해 붙인다(파일은 안 바꿈) |
| `claim.declared` | `status`, `scope`, `global_4_4b`, `actual_trajectory_membership`, `new_certified_regions`, `coverage_modified`, `certificate_created` | 원문 그대로 보존. 축 값은 종류로 정한다(6.3절) |
| `numeric_contract` | `required_bits`, `residual_bits`, `max_decision_bits`, `momentum_scale`, `precision_cap`, `profile`, `model_fingerprint` | 파일마다 있는 필드가 다르다. 없는 것은 `unknown` |
| `legacy_lf_sha256` 대조 대상 | `source_sha256`, `prior_fixture_sha256` | 현재 pin은 모두 LF 정규화 SHA-256이다 |
| `semantic_dependencies` | `foundation_sha256`(6개), `prior_fixture_sha256`(dict **또는 문자열**), `diagnosis_sha256`, `sample_policy_sha256`, `expected_domain` | 형태가 파일마다 다르다(12절 C3) |
| `provenance_edges` | `source_sha256`, 묶음 파일 구조, 문서의 판정 id | 정체성 밖 |
| `run_metadata` → `compute_cost`, `verify_cost` | shell 17: `stages[]`(wall·CPU·workers·효율)·`host`, survey: `preparation_seconds`·`cost_table`·`cost_split_same_host`·`host`, orbit: `seconds`. **shell 18 인증서 fixture에는 비용 필드가 없다**(문서에만 551/547/567초) | 없는 것은 `unknown`. 문서 값은 `source: docs`로 구분 |
| `provenance` | orbit boundary만 `provenance{git_head, uncommitted_changes, code_sha256}` | fixture 안에 있으면 그대로 옮긴다. **Git 이력에서 가져오지 않는다.** 재생성 결과가 clone 깊이에 따라 달라지면 안 된다(이 문서를 쓴 원격 세션의 clone도 얕은 clone이었다). 커밋은 검증 기록(7.5절)에 적는다 |
| `verification` | 없음. 검증은 `tests/test_c1b1_*.py`가 LOCAL FULL에서 수행 | 7.5절 형식으로 attestation log에 추가한다. Warehouse가 스스로 검증하지 않는다 |

### 7.2 해시 셋과 semantic / run 분리

| 해시 | 계산 대상 | 쓰임 |
|---|---|---|
| `raw_file_sha256` | 파일 바이트 그대로 | 바이트 수준 동일성, 복사·전송 검사 |
| `legacy_lf_sha256` | CRLF→LF만 바꾼 바이트 | 기존 `source_sha256`·`prior_fixture_sha256` pin 대조. 현재 인증서가 쓰는 규칙과 같다. 새 설계의 동일성 판단에는 쓰지 않는다 |
| `payload_hash` (= content_hash) | `semantic_payload`의 정규 직렬화 | 의미 내용 동일성. 들여쓰기·키 순서·줄바꿈·run metadata와 무관 |

변경별 기대값 (13.6절 결함 주입의 기준):

| 변경 | raw_file | legacy_lf | payload_hash | artifact_id |
|---|---|---|---|---|
| CRLF↔LF만 | 다름 | **같음** | 같음 | 같음 |
| 들여쓰기·키 순서만 | 다름 | 다름 | 같음 | 같음 |
| run_metadata만(시간·worker·host) | 다름 | 다름 | 같음 | 같음 |
| semantic 값 하나 | 다름 | 다름 | 다름 | 다름 |
| payload는 같고 domain·계약·proof method가 다름 | (다른 파일) | (다른 파일) | 같을 수 있음 | **다름** |

초판은 `file_sha256`을 "LF 정규화 해시"로 정의하면서 결함 주입 표에서는 "CRLF만 바꾸면 file_sha256이 달라야 한다"고 적었다. 둘은 동시에 성립할 수 없다. 위 표가 그 모순을 대체한다.

**semantic_payload와 run_metadata의 분리 규칙:**

- mapper가 artifact 종류마다 **필드 목록을 명시**한다: 어떤 필드가 semantic, run_metadata, provenance인지.
- **자료형으로 추측하지 않는다.** 초판의 "float면 측정값" 규칙은 폐기한다. 지금 fixture에서는 float가 우연히 대부분 시간·효율 측정값이지만, 미래의 물리 자료에서는 float가 의미 있는 입력값일 수 있다.
- **모르는 필드가 나오면 등록을 거부한다.** 추측으로 분류하지 않는다. 새 필드는 mapper에 추가해야 통과한다. 연구 저장소의 허용 목록과 같은 원칙이다.
- 정규 직렬화 규칙은 `audit/independent_trace/canonical.py`처럼 문서에 직접 적는다: 키 정렬, 공백 없음, 정수 최단 십진, 문자열 escape, UTF-8, bool은 정수가 아니다. semantic_payload 안의 binary64 값은 **정확한 표현**(`float.hex()` 형식 문자열)으로 직렬화하고 NaN·무한대는 거부한다. 반올림된 십진 표기는 쓰지 않는다.
- 기존 fixture에서 run_metadata로 명시할 필드: `stages`, `host`, `preparation_seconds`, `seconds`, 비용 측정표(`cost_table`, `cost_split_same_host` 등). 이것도 "float라서"가 아니라 **목록에 있어서** run_metadata다. 측정값은 버리지 않고 보존하되 정체성 밖에 둔다.
- 어느 쪽인지 애매한 필드는 **semantic에 둔다.** 그러면 정체성이 조금 더 민감해질 뿐, 서로 다른 것이 하나로 합쳐지거나 정보가 사라지지는 않는다.

### 7.3 artifact 정체성 — payload_hash와 분리

```text
artifact_id = "a1:" + SHA-256( canonical({
    schema_version,
    artifact_type,
    domain,                 # 정규 형
    model_contract,
    numeric_contract,
    proof_method,
    semantic_dependencies,  # 정렬된 (kind, target) 목록
    payload_hash
}) )
```

- 서로 다른 domain·계약에서 우연히 payload가 같아도(`hazard 0`, `candidate_count 0`) artifact_id는 다르다. 초판의 `artifact_id = content_hash`는 이 둘을 하나로 합쳤을 것이다.
- 같은 증명을 6 worker와 32 worker로 만들면 payload_hash와 artifact_id가 **둘 다 같다**. run_metadata만 다르다.
- 정체성에 넣지 않는 것: run_metadata, storage_location, aliases, 검증 기록, verification_level, lifecycle_state, producer 코드 해시. 뒤의 다섯은 artifact **자체**가 아니라 artifact에 **대한** 사실이다.
- **구현자 해석, 설계자 확인 필요(17절 Q9):** producer 코드 해시를 정체성에서 뺐다. 같은 주장을 리팩터링한 코드가 다시 만들면 같은 artifact로 보고, 어느 코드가 만들고 검증했는지는 검증 기록이 말한다. 단 현재 hard-case·family 인증서는 checker와 foundation 해시를 **인증서 본문 안에** 갖고 있어서 이미 payload_hash에 들어간다.

### 7.4 의존성 간선 — semantic과 provenance를 나눈다

지금 인증서는 이미 **여러 종류**의 의존성을 구분해 쓴다. 평평한 목록으로 뭉개지 않는다.

| 종류 | 뜻 | 기존 필드 | 정체성 |
|---|---|---|---|
| `foundation` | 동결된 수학·수치 항등식 코드. 바뀌면 증명의 전제가 바뀐다 | `foundation_sha256` (ar2_lang2024, axis_decision_bounds, rounding_regions, two_atom, a_numeric/exp, hard_case_checker) | 포함 |
| `prior_artifact` | 이 결과가 입력으로 소비한 상위 결과 | `prior_fixture_sha256`, `diagnosis_sha256`, `sample_policy_sha256` | 포함 |
| `domain_binding` | 외부에서 받은 원래 domain | `expected_domain`, `domain_hash` | 포함 |
| `producer` | 이 결과를 만든 코드 | `source_sha256` | 제외 |
| `contained_in` | 한 fixture 파일이 여러 artifact를 담을 때 묶음 파일을 가리키는 간선 | fixture의 `groups[]`, `coverage`, `certificate` 중첩 구조 | 제외 |
| `consumed_by_coverage` *(역방향)* | 어느 coverage 보고서가 이 인증서를 소비했나 | 코드로만 존재(`check_outgoing_coverage` 인자) | 제외(파생) |
| `verdict` | 설계자 판정 | 문서(`④-4c-6` 등) | 제외 |

- `prior_artifact`의 대상은 알려진 fixture들의 `legacy_lf_sha256`과 **정확히 일치할 때만** 푼다. 풀리면 대상 artifact_id를, 안 풀리면 원래 해시를 `unresolved_target`으로 둔다. 파일 이름이 없는 문자열형 pin도 해시 일치로만 풀고 추측하지 않는다.
- 의존성 그래프는 **DAG**이어야 하며 순환·미지 의존·버전 불일치·해시 불일치를 자동 검사한다(증명 조립 문서 5.5절). 불일치는 lifecycle `STALE`로 자동 계산된다(6.2절).

### 7.5 검증 기록 (attestation) 형식

```text
verification_record:
  seq, prev_record_sha256   # 추가 전용 해시 체인                                (구현자 추가)
  artifact_id
  result                    # pass | fail
  commit                    # 검증을 실행한 커밋. dirty 트리면 기록 거부
  checker                   # 모듈 경로                                          (구현자 추가)
  checker_hash              # 실행 시점 checker의 legacy_lf_sha256
  test_manifest             # 실행한 시험 node id 목록 + 각 시험 파일 해시, 또는 manifest 파일과 그 해시
  run_kind                  # LOCAL FULL | REMOTE LINUX FULL | focused | driver    (구현자 추가)
  log_path                  # 예: runs/<실행>/local_full.log. Git 밖일 수 있다
  log_sha256                # 로그 파일 해시. 나중에 로그가 바뀌면 탐지한다
  junit_path, junit_sha256  # 있으면                                              (구현자 추가)
  when, host                #                                                    (구현자 추가)
```

- 설계자 판정의 필수 필드는 commit, checker_hash, test_manifest, log_path, log_sha256, result다. 나머지는 구현자 추가다.
- 로그 파일이 이 컴퓨터에 없으면(`runs/`는 Git 밖) 해시 대조 결과는 `unavailable_here`로 적는다. "확인됨"으로 쓰지 않는다.
- 검증 기록은 **fixture에서 재생성할 수 없는 사건 기록**이다. 그래서 파생 인덱스와 다른 파일, 곧 추가 전용 attestation log에 둔다(13.3절, 17절 Q11). 로그 본문이 아니라 경로와 해시만 담는다.

---

## 8. 샌드위치 패널식 모듈 구조

나중에 계산법이나 저장장치가 바뀌어도 전체를 다시 만들 필요가 없게, **교체 가능한 판**으로 쌓는다.

```text
Warehouse Core (schema · 증거 수준 규칙 · DAG 규칙 · API)
├─ Storage Backend      RAM | NVMe | HDD | Remote        ← 교체 가능
├─ Proof Engine         current exact/bound | interval | affine | future   ← 교체 가능, artifact에 proof_method로 기록
├─ Checker Backend      기존 checker 모듈들 (창고가 부르지 않는다. 결과 기록만 받는다)
├─ Scheduler            (장기) 미해결 영역 피킹 → CPU/GPU/Exact worker
└─ Dependency Graph     7.3절 간선, DAG 검사, stale 전파
```

**API (계산 코드는 JSON/SQLite/파일 경로를 직접 다루지 않고 이것만 쓴다):**

```text
v0 (읽기 전용):
warehouse.regenerate()                              → fixture·현재 파일 해시·attestation log에서 registry를 결정적으로 다시 만든다
warehouse.get(artifact_id)                          → artifact metadata + payload 위치
warehouse.find(verification_level=..., lifecycle_state=..., **filters)
                                                    → 두 축 모두 필수. 기본값 없음
warehouse.certification_inputs(**filters)           → 6.4절 조합만 반환
warehouse.attest(artifact_id, verification_record)  → attestation log에 추가(해시 체인). 재생성 뒤 verification_level에 반영
warehouse.verify_dependencies(artifact_id)          → 의존성 해시 재계산·대조 보고. 아무것도 바꾸지 않는다

장기 (별도 Gate):
warehouse.put(semantic_payload, metadata)           → 계산 코드가 결과를 창고에 직접 넣는 경로
warehouse.invalidate(artifact_id, evidence)         → REJECTED 기록(추가 전용). 증거 필수
```

**권한과 의존 방향 — 절대 규칙:**

| 규칙 | 이유 · 근거 |
|---|---|
| 창고는 판정자가 아니다. `status`를 스스로 올리지 않는다 | 증명 조립 문서 5.4절. "창고 안 certified를 검증 없이 신뢰" 금지 |
| `a_reference/`·`a_numeric/`·`audit/`의 어떤 모듈도 Warehouse를 import하지 않는다 | 해시 고정 파일에 손대지 않기 위해, 그리고 검사기가 창고에 기대는 순환을 막기 위해(검증 한계 유형 A) |
| Warehouse 패키지는 `engine`·`a_reference`·`audit`·`research_store`·`ground_truth`를 import하지 않는다 | 순수 metadata 계층. 검증은 기존 checker가 자기 자리에서 하고 결과만 기록한다 |
| B 쪽 모듈(`engine/deterministic/blind_*`, `probe_*`, `research_store.b_visible`)은 Warehouse에 닿지 않는다 | 헌법 제24·26조. 전체 수식·fixture·domain은 설계자·감사 정보다. AST import 시험으로 강제(`tests/test_audit_*`와 같은 방식) |
| Warehouse는 A의 실행 경로에 없다 | 헌법 제2·3조. 창고는 **증명에 관한** 재사용이지, 세계 계산의 생략이 아니다. 실행기가 "이 구간은 인증됐으니 계산을 건너뛰자"를 하는 일은 없다 |
| Warehouse는 authoritative history가 아니다 | 계산·메모리·기록 제안 5.2절. 잃어도 물리 역사는 잃지 않는다. 다만 인증서는 재생성에 수백 CPU초~수만 CPU초가 들므로 **파생물 중 값비싼 파생물**이다 |

연구 저장소에서 이미 검증된 기법을 그대로 가져온다: 내용 해시가 이름(같은 내용 1번 저장), 레코드는 추가 전용 해시 체인, 정정은 새 레코드로만, `commit`/`dirty`/`producer` 필수, 커밋되지 않은 코드로는 쓰기 거부, 조회 시 필수 축(`semantics` ↔ 여기서는 `verification_level`·`lifecycle_state`) 생략 불가.

---

## 9. 기존 결과를 삭제하지 않는 versioned 구조

- 새 proof 방법이 나와도 기존 결과를 덮어쓰지 않는다. `proof_method`를 artifact에 기록하고(`interval-v1`, `affine-v1`, `hard-case-quadratic-v1`, `future-v2` …), 새 방법은 **별도 artifact**를 만든다. 지금도 그렇다: constant-output 인증기를 보존한 채 multi-output 계약을 추가했고, survey 옆에 certificate가 별도 fixture로 있다.
- 의존하는 코드·모델이 바뀌면 삭제하지 않고 전이한다.

```text
verification_level: CERTIFIED   (그대로 남는다. 이력이다)
lifecycle_state:    ACTIVE
                      ↓  (registry 재생성이 semantic dependency 또는 checker 해시 불일치를 발견)
lifecycle_state:    STALE  { cause: 간선 종류 · 대상 · 기록된 해시 · 현재 해시 }
```

- **무엇 때문에 stale이 됐는지**를 간선 단위로 남긴다. 예: `a_numeric/exp.py` 해시 변경 → foundation 간선을 가진 모든 인증서가 STALE 후보(현재 6개 foundation 파일 중 하나라도 바뀌면 shell 18·17 인증서와 family 인증서 5개 전부).
- RULES "실패를 삭제하지 않는다"가 여기 그대로 적용된다. lifecycle `REJECTED`·`STALE`과 claim `counterexample`도 보존하며 `invalid-measurement`처럼 표시만 한다.
- 기존 계산은 **재현 가능하게 보존**한다: 재생성 명령(`python -m a_reference.c1b1_hard_case_certificate <out.json>`), 워커 수, 커밋, 호스트를 함께 기록한다.

---

## 10. 저장장치 계층화 — 기준만 정하고 정책은 미정

향후 데이터 특성에 따라 저장 위치를 자동 선택할 수 있게 한다. **사용 빈도만이 아니라** 다음을 함께 본다.

| 기준 | 뜻 | 지금 측정 가능한가 |
|---|---|---|
| 재사용 빈도 | 얼마나 자주 읽히나 | 아니오(조회 기록 없음) |
| 재계산 비용 | 잃으면 다시 만드는 데 얼마나 드나 | 일부(shell 17: build 약 6,380 CPU초, shell 16 checker 약 19,751 CPU초; shell 18은 문서 값만) |
| 검증 비용 | 소비 전에 다시 검사하는 데 얼마나 드나 | 일부(shell 17 verify 약 6,379 CPU초 — **build와 거의 같다**) |
| 의존하는 artifact 수 | 이것이 바뀌면 몇 개가 stale이 되나 | 등록 뒤 DAG에서 계산 가능 |
| 현재 작업 중요도 | 활성 Gate와의 거리 | 설계자 판정 |

```text
RAM         → 지금 계산 중인 working set (superblock 행, 후보 구간)
NVMe        → 자주 쓰거나 재생성 비용이 큰 proof/certificate (활성 shell 인증서, coverage 입력 층)
HDD/archive → 오래된 실행 기록, 저빈도 결과 (runs/ 4.2GB, 옛 survey)
Remote      → 원격 노드에서 만든 결과의 회수·복제
```

로컬 P41 NVMe는 **미래의 active proof warehouse 후보**다. 지금 결정하지 않는다.

**RULES 5절과의 충돌(12절 C10):** 파일을 다른 계층으로 **옮기는** 것은 원본 위치에서 보면 삭제다. 현재 삭제 권한이 없고, `runs/`는 Git 밖이라 목록·SHA-256 manifest·archive·시험 복원·대조·시험 재실행·사용자 확인·명시적 승인의 8단계가 적용된다. 따라서 **자동 계층 이동은 그 절차를 코드로 만들고 설계자가 승인하기 전에는 금지**다. 계층화는 우선 "어디에 있는가"를 **기록**하는 것(`storage_location`)에서 시작한다.

---

## 11. Batch / Zone / 자동 피킹

비슷한 계산은 batch로 묶는다: 동일 potential, 동일 numeric profile, 동일 proof method, **서로 다른 domain cell** → 한 batch로 CPU/GPU에 전달. 지금 superblock 1024개를 워커에 나누는 것이 그 원형이다.

Worker는 저장소 전체를 뒤지지 않는다. WMS(창고 관리)가 필요한 작업만 전달한다.

| 상태 | 피킹 결정 | **정확한 뜻** |
|---|---|---|
| `CERTIFIED` + `ACTIVE` | skip | **재생성(build)만 생략한다. 소비 전 재검증(verify)은 생략하지 않는다(Q3 승인, ④ 동결 전).** 지금 shell 17·16 driver가 coverage 단계에서 shell 18·17 인증서를 매번 다시 verify하는 것이 현재 정책이다(11.1절) |
| artifact 없음 | compute | 아직 어떤 artifact도 없는 cell |
| `STALE` | reverify / recompute | 먼저 재검증. foundation이 바뀌었으면 재계산 |
| claim `unresolved` | subdivide | 4절의 중단 조건 안에서만 |

### 11.1 "skip"의 경제학 — 정직한 계산

hard-case 인증서는 verify가 **모든 행을 다시 계산**하므로 verify 비용 ≈ build 비용이다(shell 17: 203초 vs 203초, 32스레드). 이런 종류에서는 "Certified → skip"이 절약하는 것이 **build 한 번**뿐이고, 소비할 때마다 verify 비용은 그대로 든다. 반대로 family 인증서는 build에 탐색이 들고 verify는 결정적 재계산이라 절약 폭이 크다.

그래서 Warehouse가 `compute_cost`와 `verify_cost`를 **둘 다** 기록해야 한다: 어디서 창고가 돈을 벌고 어디서는 벌지 못하는지를 설계자가 숫자로 볼 수 있어야 한다. "해시만 맞으면 verify 생략"(hash-verified 소비)은 큰 절약이지만 **증거 강도를 낮추는 결정**이다. 구현자 의견은 16절: ④가 동결되기 전에는 full re-verify를 유지한다.

향후 CPU/GPU/Exact worker 자동 선택은 계산·메모리·기록 제안 9절의 제한(결과 bit를 바꾸지 않는 실행 전략만) 아래에서만 고려한다.

---

## 12. 현재 구조와 충돌하는 지점 — 보고

아래는 이 설계를 **그대로** 현재 코드에 얹으면 깨지거나 규칙을 어기는 곳이다. 전부 v0 범위(13절)에서 피해 가도록 설계했다.

| # | 충돌 | 근거(현재 코드·규칙) | v0에서의 처리 |
|---|---|---|---|
| **C1** | 상태 어휘가 세 갈래다: 이 지시의 7수준 / 증명 조립 제안 4.2절 5수준(`counterexample`, `invalid_evidence` 포함) / 코드(`certified`·`not_certified`·`survey_only`, `global_4_4b: NotCertified`, D_valid `numerical_validated`·`unsupported`·`formal_certified`, orbit `'NUMERICALLY VALIDATED evidence (not certified)'`) | 6.6절 표 | **개정 1: 세 축 모델(6절)로 해결.** 기존 값은 `claim.declared`에 원문 보존, 축 값은 종류로 정한다 |
| **C2** | **해시 고정.** 인증서 fixture가 producer·checker·foundation 파일의 source 해시를 박아 둔다. 창고용 필드를 계약 모듈에 추가하면 shell 18·17 인증서가 즉시 거부된다. shell 17·16 driver가 별도 파일인 이유가 이것이다 | `c1b1_hard_case_certificate.py` `FOUNDATION_HASHES`, `c1b1_family_checker.py` FOUNDATION_HASHES 5개, `tests/test_c1b1_hard_case_certificate_shell17.py`의 해시 단언 | Warehouse는 **별도 패키지**, 기존 모듈은 import도 수정도 하지 않는다. metadata는 밖에 붙인다 |
| **C3** | 의존성 표현이 파일마다 다르다: `prior_fixture_sha256`가 dict(hard-case)인 곳과 **파일 이름 없는 문자열**(family·half-ulp·fractional-phase)인 곳이 섞여 있다. 해시 대상도 파일 바이트(LF 정규화)라 형식 변화에 취약하다. 2026-09-28 리눅스에서 잡힌 "줄바꿈 의존 해시"가 같은 계열이다 | 7.1절 표, fixture 실측 | 기존 값을 고치지 않는다. **개정 1:** raw_file·legacy_lf·payload 해시 셋으로 분리(7.2절). 문자열형 pin은 legacy_lf 해시 정확 일치로만 대상을 푼다(7.4절) |
| **C4** | coverage 합성이 **코드로 고정된 층 순서**다. 새 층 = 새 모듈(+ shell별 driver). 이 지시의 "dependency graph → 자동 피킹"은 데이터 주도 합성을 원하지만, 그것은 해시 고정 모듈의 리팩터링이다 | `check_outgoing_coverage` 4층, `R.MAX_REGIONS` | v0는 합성을 **하지 않고 기록만** 한다(`consumed_by_coverage` 간선). fresh coverage 숫자는 기존 함수만 계산한다 |
| **C5** | 증거 수준 혼입 위험은 지금 **관례로만** 막혀 있다. shell 16 survey fixture와 (곧 나올) shell 16 인증서는 같은 domain·비슷한 `superblock_rows`를 가진다. 인증 계약이 survey 주장을 전혀 읽지 않아 안전하지만, 범용 `find(domain=shell16)`가 둘을 함께 돌려주면 위험이 생긴다 | `build()`는 "trusts no survey claim" | **개정 1:** `find`는 `verification_level`·`lifecycle_state` 필수, usage `survey_only`는 `certification_inputs()`에서 구조적으로 배제(6.4절). 결함 주입 시험 |
| **C6** | `research_store/`와 역할이 겹쳐 보인다. 그러나 축이 다르다: 연구 저장소는 **B로부터의 비밀 등급**, Warehouse는 **증거 강도**. 연구 저장소 문서가 "물리 A 실행은 아직 저장 대상이 아니다"라고 명시한다 | RESEARCH_STORE_V1 계약 8개 | 별도 저장소. 기법(내용 해시·해시 체인·필수 축·provenance)만 차용. B 접근 금지 시험 공유 |
| **C7** | 증거의 절반이 Git 밖이다. `runs/`(233 디렉터리·4.2GB, D:)의 `verification_summary.json`·`unchanged_contracts.json`·로그는 설계자 로컬에만 있고 원격·이 세션에는 없다 | REPO_MAP 데이터 표, 이 세션에서 `runs/` 부재 확인 | v0 등록 대상은 **Git fixture 33개**. `runs/`는 로컬에서만 `storage_location{available_here:false}`로 등록. 4.2GB를 읽지 않는다 |
| **C8** | `model_version`·`numeric_contract`가 한 값이 아니다: 계약 id 3종, profile 2종, Δt, `model_fingerprint`, `precision_cap`, `required_bits`가 파일마다 다른 조합으로 있다 | 7.1절 | 구조체로 기록, 없는 항목은 `unknown`. 문자열 하나로 뭉개지 않는다 |
| **C9** | 다차원 Cell(R, p_r, L, E, θ)이 코드에 없다. 현재 문제는 projection 뒤 **1차원 축 격자**다. 지금 일반 Cell 스키마를 만들면 로드맵의 중단 조건("④ 해결보다 framework 코드가 더 커짐")에 걸린다 | `axis_lattice_interval`, `finite_points`, class 행 | domain은 **종류 + 정규 해시의 불투명 객체**. 다차원 Cell은 R<20 트랙에서 별도 설계 |
| **C10** | 저장 계층 자동 이동은 RULES 5절(삭제 권한 없음, 8단계 절차)과 충돌한다. `runs/`는 Git 밖이라 절차가 그대로 적용된다 | RULES 5절 | 이동 금지. `storage_location` 기록만 |
| **C11** | fixture가 **결정적 payload와 비결정 측정값을 한 파일에** 섞는다(`stages` wall/CPU, `host`, `preparation_seconds`, float 효율). 파일 해시로는 같은 증명의 중복을 알 수 없다 | 7.2절 | **개정 1:** mapper가 종류별 필드 목록으로 semantic_payload·run_metadata·provenance를 명시적으로 나눈다. 자료형 추측 금지, 모르는 필드는 등록 거부(7.2절) |
| **C12** | "Certified → skip"이 증명 조립 제안 5.4절("검증 없이 신뢰 금지")과 정면 충돌하는 것처럼 읽힌다 | 11절 | skip = **build 생략**, verify는 생략 아님으로 정의. hash-verified 소비는 설계자 결정 항목(17절 Q3) |
| **C13** | 기존 문서 어디에도 "어느 시험·어느 실행이 이 인증서를 검증했나"가 **기계가 읽는 형식**으로 없다. 검증 사실은 CURRENT_STATE 본문과 `runs/*/local_full.xml`에만 있다 | 7.1절 `verification` 행 | v0가 검증 기록을 **처음** 만든다. **개정 1:** 로그·manifest 해시까지 기록(7.5절) |
| **C14** | **registry의 권위.** 창고 장부와 선반이 어긋날 위험: fixture는 바뀌었는데 Git의 registry만 옛 상태로 남을 수 있다 | Q4 조건(설계자 판정) | registry는 **정본이 아닌 파생 인덱스**다. 정본은 fixture와 코드다. fixture에서 결정적으로 재생성하고, 재생성 결과 = Git 사본을 시험한다. Git 이력(얕은 clone에서 달라짐)·시각·호스트에 의존하지 않는다. 검증 기록은 재생성할 수 없는 사건이라 별도 추가 전용 log에 둔다(13.3절) |
| **C15** | **payload 우연 일치.** 서로 다른 domain·계약에서 payload가 같으면 초판의 `artifact_id = content_hash`는 두 artifact를 하나로 합친다 | 초판 7절 | 정체성과 payload 해시 분리(7.3절) |

이 표의 어느 항목도 "현재 코드가 틀렸다"는 뜻이 아니다. 현재 코드는 각 인증서를 **닫힌 단위**로 정확히 잠그고 있다. 충돌은 그 닫힌 단위들을 **가로질러 색인하려 할 때** 생기며, 그래서 v0는 색인만 밖에서 한다.

---

## 13. Warehouse v0 — 현재 ④에 적용할 최소 범위

### 13.1 목표

기존 shell 계산 결과에 다음 metadata를 **밖에서** 붙이고, 향후 등록·조회할 인터페이스를 정한다.

```text
shell · domain · artifact_id · payload_hash · raw_file_sha256 · legacy_lf_sha256
verification_level · lifecycle_state · claim(status, usage)
source_hash · checker_hash · dependencies(semantic / provenance) · compute_cost · verify_cost
```

### 13.2 범위 / 비범위

| v0가 하는 것 | v0가 하지 않는 것 |
|---|---|
| Git fixture(`a_reference/fixtures/*.json`)를 읽어 7절 schema로 **파생 인덱스를 재생성** | fixture 파일 수정·재생성·이동 |
| 기존 필드를 mapper의 **명시 목록**으로 매핑. 모르는 필드는 등록 거부 | 기존 인증 계약에 필드 추가, 자료형으로 의미 추측 |
| 해시 셋(raw_file·legacy_lf·payload)과 artifact_id 계산 | coverage 합성·숫자 재계산 |
| 의존성 간선 기록, lifecycle STALE 자동 계산(신뢰를 낮추는 방향만) | 신뢰를 올리는 자동 전이 |
| 검증 기록을 attestation log에 추가(로그·manifest 해시 포함) | Warehouse가 스스로 verify 실행 |
| `regenerate`, `get`, `find`(두 축 필수), `certification_inputs`, `attest`, `verify_dependencies` | scheduler, worker 선택, GPU, 자동 분할, R<20 Cell, `put` |
| 재생성 결과 = Git 사본 시험, B 접근 금지·기존 모듈 비의존 AST 시험 | 기존 시험·fixture·기준선 변경 |

### 13.3 패키지 경계 (제안, 이름은 Q4로 조건부 승인)

```text
proof_warehouse/                 # 최상위, audit/·research_store/와 형제
├─ __init__.py                   # 아무것도 import하지 않음
├─ schema.py                     # 7절 필드, 세 축 값, 정규 직렬화 규칙(문서와 같은 문장)
├─ registry.py                   # regenerate/get/find/certification_inputs/attest/verify_dependencies
├─ backends/json_file.py         # v0 backend: JSON 파일
├─ mappers/c1b1_fixture.py       # 종류별 필드 목록(semantic/run/provenance), 모르는 필드 거부
├─ registry/c1b1_v0.json         # 파생 인덱스. 정본이 아니다. 재생성 결과와 바이트까지 같아야 한다
└─ attestations/c1b1_v0.jsonl    # 추가 전용 검증 기록 log(해시 체인). 재생성 대상이 아니다
```

- `proof_warehouse/`는 표준 라이브러리만 쓴다. `a_reference`·`a_numeric`·`engine`·`audit`·`research_store`를 import하지 않는다.
- `a_reference/`·`tests/test_c1b1_*.py`는 `proof_warehouse`를 import하지 않는다. 기존 시험은 그대로다.
- **registry는 파생 인덱스다(Q4 조건).** Git에 두는 이유는 변화가 diff로 보이게 하기 위해서다. 정본은 fixture와 코드다. 시험이 "현재 fixture로 재생성한 결과 = Git의 registry"를 확인한다. 다르면 누군가 fixture를 바꾸고 장부를 갱신하지 않은 것이다.
- **검증 기록은 파생 인덱스와 분리한다(17절 Q11).** 누가 언제 어떤 로그로 검증했는지는 fixture에서 만들 수 없는 사건이다. 재생성 대상에 넣으면 재생성할 때마다 사라진다. 그래서 추가 전용 해시 체인 log에 두고, 재생성은 그 log를 **입력으로 읽기만** 한다.
- `runs/` 항목은 로컬 등록 시 `available_here`로만 표시한다.

### 13.4 재생성 절차 (한 fixture당)

1. 파일 바이트를 읽어 `raw_file_sha256`, `legacy_lf_sha256`을 계산한다.
2. JSON을 파싱하고 mapper가 `version` 접두어로 종류를 정한다. 종류별 필드 목록으로 semantic_payload / run_metadata / provenance를 나눈다. **목록에 없는 필드가 있으면 등록을 거부한다.**
3. semantic_payload를 정규 직렬화해 `payload_hash`를 계산한다.
4. 묶음 파일은 내부 artifact로 분해하고 `contained_in` 간선을 기록한다.
5. 간선을 변환한다: foundation·prior_artifact·domain_binding은 semantic, producer·verdict는 provenance. 문자열형 pin은 `legacy_lf_sha256` 정확 일치로만 대상을 정하고, 없으면 `unresolved_target`으로 둔다.
6. `artifact_id`를 계산한다(7.3절).
7. `claim.status`·`claim.usage`를 종류로 정하고 선언 status는 `claim.declared`에 원문 보존한다. 종류와 선언이 모순이면 거부한다.
8. `verification_level`은 attestation log의 `pass` 기록으로만 계산한다(없으면 RAW). `lifecycle_state`는 현재 파일 해시를 간선·checker 해시와 대조해 ACTIVE/STALE로 계산한다. `fail` 기록이 하나라도 있으면 설계자 판정 기록으로 해소되기 전까지 REJECTED다(6.2절).
9. 결과를 정렬된 정규 JSON으로 쓴다. **같은 입력이면 바이트까지 같은 registry가 나와야 한다.** Git 이력·현재 시각·호스트를 읽지 않는다.

### 13.5 등록 결과의 1차 검증 — 문서와 fixture의 대조

등록만 해도 읽기 전용으로 확인할 수 있는 것이 있다. 이것이 v0의 첫 쓸모다.

이 문서 작성 시점의 fixture 33개를 선언된 `status`로 세면 다음과 같다(2026-09-28 실측, shell 16 인증서가 master에 들어오기 전. 지금은 `certified` 인증서가 하나 늘어 34개다): `survey_only` 8, `certified` 2(shell 18·17), `not_certified` 보고서 4(rounding_regions·rounding_diagnosis·half_ulp·family — 안에 certified group 3+5개 포함), `NUMERICALLY VALIDATED …` 6, `CONDITIONAL CANDIDATE …` 1(E_min), `status` 없음 12. 이 분포 자체가 6.3절 매핑표가 빠뜨린 값이 없는지의 첫 시험이다.

- 인증서 fixture 안의 coverage 값이 문서와 같은가: shell 17 fixture `used_regions 13 · gap 82`, shell 18 fixture `12 · 83`.
- family 인증서 5개·half-ulp 인증 3개·hard-case 2개(shell 16 뒤 3개)가 claim `certified`로 읽히고, survey 8개가 전부 usage `survey_only`로 읽히는가.
- shell 17 fixture가 shell 18 fixture의 해시를, shell 16 survey가 shell 17 인증서·survey의 해시를 가리키는 DAG가 순환 없이 닫히는가.
- foundation 6개 파일의 현재 해시가 인증서 안의 값과 같은가(다르면 그 순간 STALE 후보 — 지금은 같다).

AGENTS.md 규칙("문서와 코드가 어긋나면 코드가 옳고 문서가 낡은 것")을 **기계적으로 적용하는 첫 도구**가 된다.

### 13.6 결함 주입 시험 (구현 전에 정한다 — 검증 한계 문서 3절 체크리스트)

| 심는 결함 | 기대 |
|---|---|
| survey fixture 사본의 `status`를 `certified`로 위조 | 종류(survey)와 선언이 모순이라 **등록 거부** |
| 인증서 종류 fixture에 검증 기록이 없음 | `RAW`. `certification_inputs()`에 나오지 않음 |
| `find()`를 `verification_level`·`lifecycle_state` 중 하나라도 빼고 호출 | 오류 |
| foundation 파일 사본 1바이트 변경 뒤 재생성 | 그 간선을 가진 artifact 전부 `STALE`. verification_level은 그대로 |
| CRLF↔LF만 변경 | raw_file 다름. legacy_lf·payload_hash·artifact_id 같음 |
| 들여쓰기·키 순서만 변경 | raw_file·legacy_lf 다름. payload_hash·artifact_id 같음 |
| run_metadata(시간·worker·host)만 변경 | payload_hash·artifact_id 같음 |
| semantic 정수 하나 변경(예: `candidate_count`) | payload_hash·artifact_id 다름 |
| payload는 같고 domain만 다른 두 artifact | artifact_id 다름 |
| semantic 필드에 float 값을 넣음 | 정확 표현으로 payload_hash에 반영됨. 자동으로 run_metadata로 빠지지 않음 |
| mapper 목록에 없는 필드 추가 | 등록 거부 |
| fixture 하나를 바꾸고 registry를 재생성하지 않음 | 재생성 결과 = Git 사본 시험 실패 |
| 같은 입력으로 두 번 재생성 | 바이트까지 같은 registry |
| attest 시점에 checker 해시가 현재 파일과 다른 기록 | attest 거부 |
| 기록 뒤 checker 파일이 바뀜 | 기록 보존, lifecycle `STALE` |
| 검증 기록이 가리키는 로그 파일 1바이트 변경 | `log_sha256` 불일치 보고 |
| attestation log의 앞 기록 하나 변조 | 해시 체인 불일치로 거부 |
| `fail` 기록 뒤에 다른 checker의 `pass` 기록 추가 | 여전히 `REJECTED`. 설계자 판정 기록이 있어야 풀림 |
| `engine/deterministic/blind_*.py`에 `import proof_warehouse` 삽입 | AST 시험 실패 |
| `a_reference/*.py`에 `import proof_warehouse` 삽입 | AST 시험 실패 |

시험이 결함을 못 잡으면 그 시험은 무의미하다. 결과는 `docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md` 4절 결함 주입 표에 기록한다.

### 13.7 v0가 shell 16 인증에 주는 영향

**없어야 한다.** shell 16 인증서는 기존 driver로 생성·검증·coverage 합성되고, v0는 그 결과 fixture가 커밋된 **뒤에** 등록만 한다. 실제로 shell 16 인증서는 이 문서와 무관하게 master에서 만들어졌고(`0117cd8`), 기준선은 2834 passed + 1 xfailed가 됐다. v0 시험은 이 기준선에 **더해질** 뿐 기존 시험은 바뀌지 않는다.

---

## 14. 구현 순서와 아직 하지 않는 것

우선순위:

1. 현재 승인된 **shell 16 certification 완료** (기존 driver, 기존 계약)
2. **LOCAL FULL 및 현재 gate 결과 확정** (REMOTE LINUX FULL 교차 포함)
3. **Warehouse 아키텍처 문서** — 이 문서. 설계자 검토·수정
4. **최소 artifact schema / interface 설계 확정** (7·8절, 17절 결정 반영)
5. **기존 결과를 변경하지 않는 read-only 등록 방식 Warehouse v0** (13절) — 별도 승인 뒤

아직 하지 않는 것:

- × 기존 계산기 대규모 리팩터링
- × 기존 certificate 형식 일괄 변환
- × R<20 adaptive proof engine 구현
- × 자동 셀 분할 구현
- × GPU scheduler 대규모 구현
- × 저장 계층 자동 이동(RULES 5절)
- × hash-verified 소비(verify 생략)

v1 이상의 규모는 ④의 최종 형태(조건부 계약 여부)와 수치 실행 방식이 정해진 뒤에 정한다(설계자 검토 의견, 2026-09-28). 증명을 대량으로 만드는 전략을 계속할지가 정해지기 전에 큰 창고를 짓지 않는다.

이것들은 ④가 정리된 뒤 별도 Gate에서 진행한다. 로드맵 5절의 중단 조건이 그대로 적용된다: **④ 해결보다 창고 코드가 더 커지기 시작하면 멈춘다.**

---

## 15. 설계 목표

```text
물리 상태공간
      ↓
큰 계산 Cell
      ↓
영역 전체 bound/proof
      ↓
성공 ─────────────→ Proof Warehouse
      │
      └─ 실패
           ↓
        Cell 분할
           ↓
        재계산
           ↓
        Proof Warehouse

Proof Warehouse
      ↓
dependency graph
      ↓
아직 증명되지 않은 영역만 자동 피킹
      ↓
CPU / GPU / Exact worker
```

목표는 계산을 대충 생략하는 것이 아니다. **이미 증명한 계산을 다시 만들지 않고**, 여러 개별 상태를 **엄밀하게 하나의 영역 계산으로 압축**하며, **정말 어려운 부분에만** 계산 자원을 집중시키는 것이다. 어느 단계에서도 물리를 증명에 맞춰 바꾸지 않고, 창고가 판정하지 않고, B는 창고를 모른다.

---

## 16. 구현자 의견 (설계자 판단을 위해 분리해 적는다)

개정 1에서 2·5·6번을 설계자 판정에 맞춰 고쳤다. 초판 의견이 무엇이었는지는 Git 이력에 남아 있다.

1. **경쟁 문서를 만들지 않는 편이 낫다.** 증명 조립 아키텍처·로드맵이 "Proof Warehouse"를 이미 이름 붙였으므로, 이 문서는 그 5.4·5.5절과 Phase 6·7의 **골조 명세**로 두고 그쪽 문서에는 한 줄 참조만 두는 것이 문서 부채를 줄인다.
2. **`counterexample`은 수준이 아니라 claim 값이다(개정 1, 설계자 판정 수용).** 초판은 여덟째 수준으로 제안했지만, 반례는 검증 전(RAW)에도 존재할 수 있으므로 claim.status가 맞다. "실패는 증거"라는 원래 취지는 `counterexample` 값과 보존 규칙으로 그대로 유지된다.
3. **선언된 `status`는 절대 자동으로 CHECKED/CERTIFIED가 되면 안 된다.** 검증 기록 첨부(`attest`)를 거치지 않은 `certified`는 RAW다. 이것이 없으면 창고가 "상태 세탁기"가 된다. 비용은 기록 한 줄이고, 얻는 것은 창고를 믿지 않아도 되는 구조다.
4. **④ 동결 전에는 full re-verify를 유지하기를 권한다.** hash-verified 소비(11.1절)는 hard-case 인증서에서 소비당 약 6,400 CPU초를 아끼지만 증거 강도를 낮춘다. 지금 인증서가 2~3개이고 coverage 단계가 6분(32스레드)이라 아직 아플 만큼 비싸지 않다. 인증서가 10개를 넘어 coverage 단계가 시간 단위가 되면 그때 설계자가 결정할 문제다.
5. **payload_hash는 semantic_payload만, 분리는 mapper의 명시 목록으로(개정 1).** 초판의 "float면 측정값" 규칙은 철회한다. 자료형으로 의미를 추측하면 미래 물리 자료에서 지뢰가 된다는 설계자 지적이 옳다. 같은 증명을 워커 수만 다르게 만들었을 때 같은 artifact_id가 나와야 한다는 원래 목표는 7.3절이 지킨다.
6. **`find`의 필수 축은 타협하지 않기를 권한다(개정 1: `verification_level`·`lifecycle_state` 둘 다).** 연구 저장소의 필수 `semantics`가 이미 같은 이유로 존재하고 효과가 있었다.
7. **다차원 Cell은 지금 설계하지 않기를 권한다.** 현재 ④의 남은 gap 82개는 전부 1차원 축 격자다. 필요가 생기기 전의 일반화는 로드맵이 스스로 정한 중단 조건이다.
8. **v0 backend는 Git 추적 JSON 하나로 충분하다.** artifact 33개에 SQLite·서버는 과하다. backend 교체 가능성은 인터페이스로 확보하되, 첫 구현은 가장 단순하게.
9. **v0의 첫 쓸모는 문서-코드 대조다(13.5절).** 스케줄링·재사용보다 먼저, "문서의 13/64·gap 82가 fixture와 같은가, foundation 해시가 지금도 맞는가"를 기계가 확인하는 것이 이 프로젝트의 실패 유형(정상으로 보이는데 검증이 안 되고 있던 것)에 가장 직접 닿는다.
10. **시점.** 이 문서와 13절 범위는 shell 16 인증서·LOCAL FULL 확정 뒤 별도 Gate로만 착수해야 한다. 창고 아이디어가 좋을수록 지금 살아 있는 작업선에 삽을 꽂고 싶은 유혹이 커진다.

---

## 17. 설계자 결정 — 판정 기록과 남은 확인 항목

| # | 질문 | 구현자 권고(초판) | 설계자 판정 (2026-09-28) |
|---|---|---|---|
| Q1 | 증거 수준을 7개로 갈지, `COUNTEREXAMPLE`을 더해 8개로 갈지 | 8개 | **수정.** 한 축을 세 축(verification_level · lifecycle_state · claim/usage)으로 대체. 6절에 반영 |
| Q2 | 선언 `status`의 자동 승격 금지(검증 기록 필수) | 채택 | 승인 |
| Q3 | CERTIFIED 소비 시 full re-verify 유지 vs hash-verified 허용 | ④ 동결 전 full 유지 | 승인(④ 동결 전 유지) |
| Q4 | v0 패키지 이름·위치, registry Git 추적 여부 | `proof_warehouse/`, Git 추적 JSON | **조건부 승인.** registry는 정본이 아닌 파생 인덱스, 재생성 결과 = Git 사본 시험. 검증 기록에 로그·manifest 해시 |
| Q5 | 저장 계층 이동은 RULES 5절 절차 확립 전 금지 | 금지 확인 | 승인 |
| Q6 | 다차원 Cell 스키마는 R<20 트랙 착수 시 별도 설계 | 별도 설계 | 승인 |
| Q7 | v0 착수 시점: shell 16 인증서 + LOCAL FULL 확정 뒤 별도 Gate | 그렇게 | 승인. 선행 조건은 master `0117cd8`·`d236842`로 충족됐다. 착수는 Q9~Q11 확인 뒤 별도 Gate |
| Q8 | 이 문서를 증명 조립 아키텍처 5.4·5.5절의 명세로 연결 | 연결 | 승인. 증명 조립 아키텍처 5.4절과 로드맵 Phase 6에 한 줄 참조를 추가했다 |

**개정 1에서 새로 생긴 확인 항목.** 구현자 해석이 판정 문장보다 한 걸음 더 나간 곳이다. v0 구현 전에 확인받는다.

| # | 질문 | 구현자 권고 |
|---|---|---|
| Q9 | 정체성의 "의미상 dependency" 범위: foundation·소비한 상위 artifact·domain binding만 넣고 producer 코드 해시는 뺀다(7.3절) | 그렇게. 어느 코드가 만들고 검증했는지는 검증 기록이 말한다 |
| Q10 | claim/usage 축을 `claim.status`와 `claim.usage` 두 필드로 적는다(6.3절) | 그렇게. survey가 찾은 반례처럼 두 값이 동시에 필요하다 |
| Q11 | 검증 기록은 파생 인덱스와 분리한 추가 전용 log로 둔다(13.3절) | 그렇게. 검증 사건은 fixture에서 재생성할 수 없다 |

**승인 전 기존 계산 구조를 변경하지 않는다.** 이 문서의 어떤 문장도 코드 변경의 근거가 아니다. 개정 1 뒤에도 Warehouse 코드는 미구현이다.
