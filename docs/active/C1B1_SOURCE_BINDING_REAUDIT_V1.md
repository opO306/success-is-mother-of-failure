# C1-B1 예외 분류 변경의 source-binding 재감사 V1

2026-10-01. 시작 HEAD/origin/master `bdc9bfe7c5c763c2900121e4d8f2bcdcf56782e8`, clean.
설계자는 기존 예외 분류 변경의 유지와 이번 변경에 한정한 재감사·증거 재결합을 승인했다.
이번 예외 분류 변경의 source-binding 재감사·증거 재결합은 **완료**다.
최종 LOCAL FULL 통과 뒤 기록했다. A-EV 전체 및 기존 미해결 Gate를 닫는 작업이 아니다.

## 정상 입력 의미의 대조

수치적 재실행만으로 소스 결합을 갱신하지 않는다. `53b73ea`의 인증된 원본 소스를 보존하고
모듈 전체의 AST를 대조한다. 허용 변환은 정확한 예외 분류 문장과 guard의 감사 호출 연결뿐이다.
함수 본문·상수·반올림·도메인·precision schedule·import·기본값의 다른 변경은 거부한다.
docstring과 비실행 주석은 계산 의미 비교에서 제외한다.
동시에 감사한 현재 bytes fingerprint도 고정하므로, 주석만 바꾼 미승인 소스조차 자동으로
받아들이지 않는다. 변조 시험에서 AST만으로 주석 변경을 수용하던 문제를 확인해 수정했다.
guard/auditor의 서로 참조하는 hash 순환은 guard의 auditor-hash literal 한 곳만 template로
고정하여 피한다. 실제 literal 값은 전체 AST 비교와 guard 자체의 checksum 검사로 각각 확인한다.

| 변경 함수 | 기존 정상 proof 입력에서의 의미 | 새 전제 여부 |
|---|---|---|
| `_decide` | `lo<=hi`의 유한 Fraction enclosure에서 추가 순서 검사가 통과한다. FixedPoint.from_exact는 정확 반올림 뒤 overflow만 VMHalt로 발생시킨다. 추가 non-overflow 분기는 이 계약에서 실행되지 않는다. 같은 raw 반환, 같은 방향 overflow, 양쪽 overflow의 zero-crossing refinement, precision refusal의 순서와 schedule 모두 같다 | 없음. ordered enclosure와 canonical profile은 기존 구간/rounding 계약 |
| `_limit` | 정상 from_exact 반환과 overflow의 ExecutorLimitExceeded 번역/cause가 같다. 새 차이는 잘못 번역했던 non-overflow halt의 원인 보존 | 없음 |
| `step` 저장 raw 경계 | 기존 outer `_state`는 이미 canonical FX(96,48)/(96,80), int raw와 범위를 검사한다. 새 valid_raw는 같은 조건이다. 정상 J_cache는 실제 from_exact 반환 또는 기존 캐시 일치/zero-tail 검사로 유효하다. KDK kick/drift/segment guard/commit 본문은 동일 | 없음. malformed raw를 인정하는 기존 정상 proof 없음 |
| endpoint 수학 본문 | Iv/Num, EXP endpoint error, evaluator_ratio_error, axis_impulse_error 및 모든 bound 수식은 원본과 동일 | 없음 |
| formal wrapper 메시지 | 같은 NotCertified 정지이며 구체적인 precision refusal과 cause를 기록한다. certificate 계산 경로는 바뀌지 않는다 | 없음 |

순서 보존은 기존 outward interval 연산의 합성 성질에 따른다. `_mul/_scale/_div_pos`는
min/max와 outward floor/ceil을 쓰고 `_neg`는 끝점 순서를 뒤집어 부호를 바꾼다.
양의 radius/denominator와 유한 정수/Fraction은 기존 evaluator 및 endpoint lemma의 전제다.
signed impulse 끝점은 min/max로 정렬된다. 이 재감사는 그 전제를 확대하거나 새로 증명하지 않는다.

`_decide`의 동일 반환/refinement 상태에서 같은 M과 같은 endpoint round를 얻으므로 다음
refinement도 같다는 귀납을 적용한다. `_limit`의 정상 반환/overflow를 보존하고 저장 raw 검사가
기존 legal state에서 통과하므로, 나머지 동일 KDK 본문은 같은 전이/정지를 낸다.
malformed/reversed enclosure, malformed stored raw, non-overflow VM halt는 이 정상 계약 밖이다.
79,087-step 비트 비교는 보조 회귀 증거로만 인용한다.

## 소스 결합과 증거 보존

기존 `_SOURCE_HASHES` 및 family `FOUNDATION_HASHES`의 기대 값은 그대로 둔다.
source-binding checker는 현재 소스가 정확한 원본 hash이거나, hash 확인한 역사 원본에
위의 지정된 변경을 적용한 AST와 전체가 같은 경우에만 통과한다. executor 새 hash도 고정한다.
endpoint guard는 이 checker의 파일 hash, live 함수·상수 binding, 기존 evaluator binding과
모델/precision 상수를 함께 검사한다. 기존 guard를 monkeypatch하거나 무조건 통과시키지 않는다.
cache key는 매 호출에서 읽은 원본/현재 파일 bytes를 포함하므로 파일 변경을 숨기지 않는다.

역사 원본은 `docs/history/c1b1_source_binding_pre_classification_v1/`에 Git 원본 LF bytes와
manifest hash로 보존한다. 기존 mathematical foundation hash는 증거의 원래 출처를 의미하며,
새 감사 receipt는 그 출처와 현재 소스의 감사된 연결 및 재생성 결과를 별도로 기록한다.

| 영향받은 증거 | 재생성·검사 | 변경 함수 의존 |
|---|---|---|
| source-bound endpoint proof | 수학 본문 전체 AST 동일성, 재생성된 group의 endpoint error/물리 interval 및 기존 endpoint 시험 | `_model/_model_R` 등 동일, `_decide` 정상 의미 보존 |
| rounding diagnosis | `rounding_diagnosis.example_report` 전체 재계산 | 정상 `_decide`, legal state에서 같은 step/guard |
| prior group proof | `rounding_regions.example_report`, 각 region checker | endpoint lemma, diagnosis, 정상 rounding |
| half-ulp 경계 proof | `half_ulp_boundaries.example_report`, certified 3개 checker | 새 group proof와 같은 endpoint bound |
| family foundation의 연결 및 report | 기존 5개 family generator/checker와 coverage 재계산 | 같은 source-bound endpoint lemma. 새 family/범위 없음 |
| 비동결 bootstrap/rounding 예시 | 기존 example_report 전체 재생성 | `_limit`, legal stored raw, 기존 형식·판정 |

비교에서 제외하는 것은 명시한 top-level source_sha256 및 새 부모 artifact hash뿐이다.
certificate, bound, 후보/cell/group, 판정, 예산과 미해결 결과를 포함한 모든 수학적 payload는
기존 원본과 정확히 같아야 한다. 다르면 STOP하며 생성된 값의 일부를 옛 JSON에 끼워 넣지 않는다.

옛 `c1b1_half_ulp_boundaries_v1.json`은 후속 작업의 hash-pinned 원래 의무 목록이므로 유지한다.
새 실행 결과는 `c1b1_half_ulp_boundaries_rebound_v1.json`에 보존하고, 현재 report 재현 시험은
이 새 증거 전체와 비교한다. 옛 의무 목록의 hash와 모든 수학적 내용도 별도로 확인한다.

같은 보존 원칙을 원래 group/family/phase/modular/residue/quotient/same-input inventory에도
적용했다. 처음 LOCAL FULL에서 갱신된 group/family JSON의 전체 hash가 하위 원래 의무 목록과
맞지 않아 25개 항목이 거부됐다. 이 원래 파일들은 역사 원본과 정확히 같은 bytes로 유지하고
새 실행 결과는 각 `*_rebound_v1.json`으로 저장한다. Source 검사만 감사된 transport를 사용하며,
artifact/parent inventory의 실제 hash 검사는 변경하지 않았다.

그 하위 6개 provenance reader의 수학·policy·의무 목록·checker 본문도 전체 AST로 대조했다.
허용 변경은 source hash 비교를 감사된 source_matches 호출로 연결하는 것과 import뿐이다.
하위 기록 5개도 원래 고정된 의무 목록과 같은 generator/policy로 재생성했다. 새 조사 범위,
새 class/bound/lemma 또는 기존 survey_only 결과의 승격을 추가하지 않는다.
총 재생성 기록은 원래 6개와 하위 provenance 연결 기록 5개, **11개**다.
residue의 공식 lossless `packed_report` 형식을 그대로 사용하여 14,271 class 기록 전체를 비교했다.

### 현재 증거

현재 source hash, 각 원본/새 artifact hash, 수학적 payload hash 및 generator는
[감사 receipt](../../a_reference/fixtures/c1b1_source_binding_reaudit_v1.json)에 봉인했다.
재생성한 새 기록 8개는 원래 inventory와 별도의 `_rebound_v1` 파일이며,
비동결 bootstrap/rounding 예시와 diagnosis는 실제 재생성 결과를 현재 기록으로 유지한다.
역사 원본은 [manifest](../history/c1b1_source_binding_pre_classification_v1/manifest.json)로 확인한다.

## 검증 결과

관련 시험 **364 passed, 80.21초**. 정상 의미 비교·고정 inventory·원본/새 payload 및 실제
source fingerprint·guard literal·source 변조를 확인했다. 소스 기대 hash를 바꿔도 수학 본문을
바꾸면 AST transport가 거부하는 시험을 포함한다.
최종 LOCAL FULL `python -m pytest tests -q -n 6`은 **3483 passed + 1 strict xfailed,
실제 skip 0, failure/error 0, exit 0, 25 warnings, 684.98초**로 통과했다.
JUnit 3484개 중 skipped 1개는 기존 strict xfail이다. 기존 native subprocess 출력 해독
경고 25건은 남아 있으며 이번 작업에서 해결하지 않았다. 시험 대상은 시작 HEAD `bdc9bfe7`
위의 이번 재감사 변경이다. 공식 AGENTS 기준선은 설계자 판정 없이 갱신하지 않는다.

첫 LOCAL FULL은 **3451 passed / 4 failed / 21 errors / 1 strict xfailed / 실제 skip 0,
25 warnings, 652.69초**였다. 원래 group/family inventory hash 연결 때문에 먼저 거부되어
일부 fault-injection 시험도 기대한 거부 이유에 도달하지 못했다. 옛 inventory 보존과 명시적
source transport로 해결했다. 중간 관련 시험은 **362 passed / 1 failed, 101.81초**였으며,
주석 추가를 자동 허용하던 source 결합 문제를 잡았다. 정확한 현재 bytes fingerprint를
추가하여 같은 기존 시험을 통과시켰고 기준이나 수학 계약은 낮추지 않았다.

Driver 개발 중 region checker에 직렬화된 객체를 넘긴 오류와 residue의 packed wire 형식을
적용하지 않은 오류도 로그에 보존했다. checker 또는 certificate를 고치지 않고 원래 typed
checker API 및 공식 lossless serializer를 사용했다. 공식 packed 형식에서 residue 14,271
class 전체와 bound가 원본과 정확히 같음을 별도로 확인했다.

로그: Git 밖 `runs/c1b1_source_binding_reaudit_20261001/`의 `regenerate_pinned_final.log`,
`related_pinned_final.log/xml`, `local_full.log/xml`(첫 실패), `local_full_final.log/xml`(최종 실행).

현재 [receipt](../../a_reference/fixtures/c1b1_source_binding_reaudit_v1.json)의 LF SHA-256:
`4ef7101d98d90d566ed3f4f1bbf58bc0c19034ba290eb9b81552231705b5adb6`.
모든 실제 current source SHA-256과 원본/새 artifact 및 payload SHA-256을 receipt에 보존했다.

원래 Git `53b73ea`의 소스·증거 파일 **20개**가 역사 사본과 LF bytes로 정확히 같고,
고정 parent inventory **8개**는 작업 시작 HEAD와 같다. 실행기 `c1b1_two_atom.py`,
물리/숫자 공용 모듈·동결 D_valid·승인 replay verifier와 네 fingerprint·7개 test history는
이번 재감사에서 변경하지 않았다. 앞선 79,087-step 비교는 재실행한 시험이 아닌 보조 기존 기록이다.
최종 integrity 검사에서 실제 source hash 14개, 역사 원본 20개, parent inventory 8개와
proof guard 통과를 다시 확인했다. 새로 추가·변경한 문서 링크 10개는 깨진 링크 0개이며
`git diff --check`도 통과했다. 결과는 같은 로그 폴더의 `final_integrity.json`에 보존했다.

재생성 명령: `python -m tools.c1b1_source_binding_reaudit`.
범위 밖: Energy Bound 전체, S4d, D_valid 전체, A-EV 전체, O-1/O-3, native J,
live pipe 및 rollback controller. 기존 상태·승인 verifier fingerprint·7개 test history는 유지한다.

## 변경 파일과 남은 한계

소스 결합 helper `a_reference/c1b1_source_binding.py`, endpoint/family guard 및 하위 6개
provenance reader, 재생성 driver `tools/c1b1_source_binding_reaudit.py`를 추가·연결했다.
diagnosis는 재생성했고 새 rebound 기록 8개·receipt·역사 원본 20개와 manifest를 보존했다.
새 감사 시험 29개를 추가하고 기존 report 재현 시험 8개는 새 rebound 파일 전체를 비교한다.
기존 수학적 assertion·fault injection·inventory hash는 유지한다. 현재 상태·분류 문서와
진입점·repo map에 완료 범위를 연결했다. 실행기 예외 분류 코드는 되돌리거나 다시 수정하지 않았다.

이 checker는 지정된 소스 변환의 완전 AST 비교와 bytes 결합을 검사한다. 임의 Python
프로그램의 의미 동등성을 증명하는 일반 도구가 아니다. 정상 입력 동등성은 위 기존 계약의
전제별 논증과 원본 수학 본문 보존을 기반으로 하며, 차등 시험은 보조 검증이다.
기존 증명의 한계·신뢰 기반은 유지한다. 새 lemma/bound/Certified region은 0개이며,
전체 A-EV·D_valid·④ 재증명 또는 미인증 구간의 승격을 주장하지 않는다.
