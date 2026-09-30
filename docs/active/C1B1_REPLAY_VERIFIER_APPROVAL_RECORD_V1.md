# Production Replay Verifier V1 승인 및 보존 witness 재검증

설계자가 commit `8996aa60afbc098e09333ad878184dcc99a58f4d`의 네 fingerprint 조합을
C1-B1 REPLAY_VERIFIED verifier로 승인했다. 승인 원문 및 신뢰 기반은
[production approval manifest](C1B1_REPLAY_VERIFIER_PRODUCTION_APPROVAL_V1.json)에 기록했다.

mpmath1.3.0 pure-Python interval enclosure, Python int/Fraction 의미는 명시적
신뢰 기반이다. **REPLAY_VERIFIED로 사용 가능, CERTIFIED로 승격 금지**다.
N-1 공식 첫 비용은 CPU약2.773배 / 같은4-worker batch wall약2.537배다.
scratch의 약1배 wall은 공식 비용값이 아니다.

## 이번 작업 범위와 검증 순서

시작 HEAD `8996aa60`, origin/master `ac14385`, clean tree. verifier/executor 소스,
물리·D_valid·dt·r_min·fixture는 수정하지 않는다. 승인 전 결과 파일을 개명하지 않고
보존된 7개의 `.c1br` bytes/sha/길이를 확인해 별도 보존한 뒤 승인된 verifier를 새로 실행한다.
신규 결과에는 승인 manifest hash와 네 fingerprint, 원본 witness hash,
구간 step, 처음/끝 raw 상태를 결합한다.

자료 범위: AGENTS/RULES 전문, CURRENT_STATE/REPO_MAP 활성 부분, V1 승인/전이 계약과
기존 history/provenance 구현을 확인했다. 관련 없는 계통과 runs 전체를 탐색하지 않았다.

승인된 verifier는 조건부 수학적 전이 이력을 검증한다. CONFIRMED에는 독립적으로
신뢰한 초기 origin 또는 직전 CONFIRMED 끝 상태 및 step의 정확한 연결이 추가로 필요하다.
verifier 승인만으로 보존 witness header를 trusted origin이라고 선언하지 않는다.
7개는 서로 다른 입력의 독립 실행이며 하나의 연속 역사로 이어 붙이지 않는다.

재검증 원본과 새 결과는 `runs/c1b1_replay_approval_20261001/`에 보존한다.
summary만으로 전체 재검증할 수 없으므로 원본 witness를 함께 유지한다.

## 새 실행 결과

**7/7 VALID, 각각 REPLAY_VERIFIED 및 CONFIRMED test history.**
설계자가 7개 시작 상태를 **각각 별개의 trusted test origin**으로 추가 승인했다.
[origin manifest 목록](c1b1_trusted_test_origins_v1/index.json)의 각 파일에는 초기12 raw,
사례·E·b·해당 rho, replay spec fingerprint, 초기 admission, 재구성 정보,
원본 source/witness hash, origin content hash 및 설계자 승인·제한을 봉인했다.
content hash는 해당 hash 필드만 제외한 canonical UTF-8 JSON의 SHA256이며
파일 byte hash는 목록에 별도로 기록한다. `.gitattributes`는 새 JSON artifact만 LF로
유지해 checkout의 줄바꿈 변환으로 file hash가 바뀌지 않도록 한다.

| 독립 시험 history | 검증 step | witness B | verdict / evidence / history |
|---|---:|---:|---|
| 0.5 De, rho=-0.01 | 13,093 | 296,807 | VALID / REPLAY_VERIFIED / CONFIRMED test history |
| 0.5 De, rho=-0.005 | 14,367 | 324,353 | 동일 |
| 0.15 De, rho=-0.005 | 26,451 | 586,820 | 동일 |
| 1 De, b=10 | 7,221 | 163,657 | 동일 |
| 0.5 De, b=6 | 6,162 | 137,928 | 동일 |
| 0.5 De, rho=+0.005 | 10,302 | 227,201 | 동일 |
| 10 De, b=0 | 1,491 | 20,576 | 동일 |
| **합계(7개 독립 history)** | **79,087** | **1,757,342** | **INVALID 0 / REFUSED 0** |

[새 history 증거 기록](C1B1_REPLAY_VERIFIER_APPROVED_TEST_HISTORIES_V1.json)은 각 승인
origin의 content/file hash, 승인 manifest hash, 네 fingerprint, witness hash,
구간과 최종 raw, 새 검증 결과를 결합한다. 초기 raw 및 start_step=0의 정확한
일치를 먼저 확인하고 **origin 봉인 뒤 기존 History.verify_next를 새로 실행**했다.
SPECULATIVE/EXECUTED에서 VALID를 거쳐 REPLAY_VERIFIED/CONFIRMED로 전이한다.
7개를 서로 이어 붙이거나 하나의 세계 역사로 합치지 않았다.

origin 승인 전에 이번 production approval 아래에서 실행한 7개 새 replay 결과도
REPLAY_VERIFIED로 별도 보존한다(`approved_reverification_batch.json`, 79,087 step,
4-worker wall103.544s). 그 파일은 origin 미연결의 SPECULATIVE 기록으로 유지했고
이를 이름만 바꿔 CONFIRMED로 승격하지 않았다. 이후 origin 봉인 후의 별도 전체
History 재검증은 CPU 합287.9375s / 4-worker batch wall104.518s다. 같은 7개 witness를
두 번 새로 검증한 것이며 14개 다른 trajectory의 증거라고 세지 않는다.
**이 승인 작업의 시간은 비용 재benchmark가 아니며 공식 첫 비용 2.773/2.537배를
대체하지 않는다.** executor trajectory는 새로 만들지 않았다.

## 초기 admission과 독립성

7개 모두 exact signed96 범위 / R²≥r_min² / E_rel≤10De를 통과했다.
공유 동결 사양과 approved Model의 128-bit interval을 사용해 energy enclosure의
**상한**이 10De 이내임을 확인하고 정확한 유리수 끝점을 manifest에 남겼다.
명목 E만 보고 admission을 통과시키지 않았다. D_valid 분류나 전체 domain 인증이 아니다.

입력 재구성은 원본의 canonical_initial_state(E,b)와 new_run을 사용했고
step을 실행하지 않았다. 초기12 raw가 원본·witness와 정확히 같았다.
이는 초기 입력을 설명하는 provenance용이며 trajectory 검증의 결정 경로는 아니다.
새 History 검증은 별도 fresh process에서 **a_reference/a_numeric/engine/audit import 0**,
production 모듈의 AST 검사 위반0, 승인된 네 fingerprint와 실행 전후 동일성을 확인했다.
verifier/executor가 공유하는 것은 동결 사양뿐이고 구현 소스는 그대로 유지했다.

## 보존·시험·한계

원본 전체 witness는 원래 production runs 폴더, 이번 replay 보존 폴더, 각 시험
History의 content-addressed witness store에 남겼다. 각 SHA256/byte size를 검사했다.
**summary는 제3자 전체 재검증 원본이 아니다.** 전체 `.c1br`과 approval/origin manifest를
함께 보존해야 한다. runs는 Git 밖이므로 이 commit만 전달해도 원본 witness가 함께
전달된다고 주장하지 않는다. [증거 기록](C1B1_REPLAY_VERIFIER_APPROVED_TEST_HISTORIES_V1.json)에
원본 경로와 hash 및 이번 재검증 driver hash를 기록했다.

이번에 새로 실행한 관련 시험: replay / step fail-closed / body contract freeze
**60 passed, 5.11s**. **LOCAL FULL 생략 / 관련 시험으로 대체**: 이번 변경은 문서·승인
manifest·원본에 결합한 새 증거와 Git 밖의 승인 실행 script뿐이며 기존 실행 코드·공용
로직·시험·동결 계약·fixture 변경0이다. 이전 구현 단계의 LOCAL FULL 3433 passed +
1 strict xfailed는 이전 실행 기록이며 이번에 다시 실행한 결과가 아니다. 공식 기준선은
갱신하지 않았다. 새 origin/hash/approval/retained witness/step/final raw 일치 검사도 완료했다.
변경된 Markdown 7개에서 local link 283개를 확인했으며 신규 깨진 링크0이다.
CURRENT_STATE에 이미 있던 비파일 설명형 링크1개는 이번 변경과 무관하게 그대로 남겼다.

승인된 trust는 mpmath interval 및 Python int/Fraction 의미다. CERTIFIED 아님.
7개 origin은 **검증 파이프라인 시험 전용**이고 D_valid 전체·공식 O-3·장기 운영 세계의
origin/CONFIRMED history로 자동 승격·재사용하지 않는다. 실제 세계 상태 commit,
unknown-length live pipe·장기 rollback·native J·공식 O-3 실행·새 물리/아키텍처 작업은 없다.
Energy Bound v0=APPROVED / ④-Liveness=NotCertified / ④-Safety=Conditional / A-EV=unresolved 유지.

Git 종료 전 실제 원격 조회에서 master 및 origin/master는 `8996aa60afbc098e09333ad878184dcc99a58f4d`였다.
시작 때 기록한 `ac14385`보다 현재 Git 상태를 우선한다. 이번 승인 작업에서 push하지 않았다.
