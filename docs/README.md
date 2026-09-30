# 프로젝트 문서 안내

**현재 상태 정본:** [CURRENT_STATE.md](../CURRENT_STATE.md). **구현 위치:** [REPO_MAP.md](../REPO_MAP.md).
A가 최우선이다. L은 A의 물리 기반이 충분해진 뒤 자연 발생·진화 계통으로 진행한다. B 본격 개발은 A·L 기반의 작은 세계가 돌아가는 후기 단계로 보류하며 취소·폐기하지 않는다.

## 폴더로 문서 상태를 구분한다

| 폴더 | 의미 | 읽는 기준 |
|---|---|---|
| [active/](active/README.md) | 현재 활성 A / C1-B1 | 세 층 분리 기준 C1-B1 종료 조건. ④ 사전 증명은 연구 과제, 공식 ⑤ 미착수 |
| [frozen/](frozen/README.md) | 동결 계약 및 동결 자산의 원문 안내 | 동결은 “낡아서 버린 문서”가 아니라 현재 지켜야 할 버전별 계약 |
| [reference/](reference/README.md) | 공통 원칙·실행 구조·검증 기준 | 본문의 승인·초안·보류 범위를 유지. 폴더 배치로 새 승인하지 않음 |
| [history/](history/README.md) | 과거 설계·철회·실측·점검 기록 | 본문 속 “현재/다음”은 당시 상태. 이 폴더의 문서가 모두 동결됐다는 뜻은 아님 |
| [deferred/](deferred/README.md) | 후기 B 연구 자산과 B-classic 관련 설계 | 보존·비교·후기 연구용. B 취소나 폐기 아님 |
| [proposals/](proposals/README.md) | 아직 구현·동결하지 않은 장기 제안 | 현재 Gate의 승인·완료 근거로 사용하지 않음 |
| [legacy-probabilistic/](legacy-probabilistic/README.md) | 동결된 확률 세계 기준선·실패 기록 | 새 결정론 세계의 증거와 합산하지 않음 |
| [legacy-society-brain/](legacy-society-brain/README.md) | 이전 사회·원시인·뇌 계통 자료 | 현재 활성 구현 대상 아님 |
| [current/](current/README.md) | 옛 경로 호환 안내와 경로 고정 원문 | 현재 작업 문서 폴더로 읽지 않음. 코드·시험의 기존 경로 보존용 |

[전체 분류·이동 경로표](DOCUMENT_STATUS_INDEX.md)에서 파일별 원문 위치를 찾을 수 있다.
폴더 이름만으로 판정을 올리지 않는다. **FROZEN / 승인 / 구현 / 수치 검증 / 초안 / 역사**는 서로 다른 상태다.

## 현재 읽는 순서

1. 루트의 [AGENTS.md](../AGENTS.md)·[RULES.md](../RULES.md)·[CURRENT_STATE.md](../CURRENT_STATE.md).
2. [active 안내](active/README.md)에서 C1-B1 설계 23·24·25·26절과 rounding-decision 상태를 함께 확인.
3. [동결 안내](frozen/README.md)에서 C1-A와 D_valid v2의 동결 범위를 확인.
4. 필요한 공통 원칙은 reference, 과거 판단의 이유는 history, 후기 B 자산은 deferred에서 찾는다.

D_valid evidence는 `numerical_validated` / `unsupported`다. 별도 analytic outer certificate와 자동 승격·연결하지 않는다.

## 보존 및 경로 예외

58개 문서를 실제로 분류 폴더로 이동했고, 코드·도구·규칙이 참조하던 옛 경로에는 원문으로 연결하는 짧은 안내를 남겼다. 계약이나 설계 본문을 두 군데 복사해 관리하지 않는다.
신체 계약의 원문은 시험이 경로와 1~8절 해시를 직접 고정하므로 [기존 위치](current/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)에 유지한다. [frozen의 신체 계약 안내](frozen/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md)에서 바로 연결된다.
`docs/README/`와 `docs/중간 결과/`는 옛 경로 안내용이다. 실제 문서는 deferred/b-design 및 history로 이동했다.
LLM_HANDOFF의 JSON manifest는 생성 당시의 스냅샷이며 이번에 재생성하지 않았다. 현재 원문은 이 안내와 분류표를 기준으로 읽는다.
