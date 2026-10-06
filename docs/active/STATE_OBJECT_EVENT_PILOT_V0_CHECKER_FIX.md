# STATE_OBJECT_EVENT_PILOT_V0 — 0단계: checker 결함 수정과 재판정

2026-10-05. 원 결과 문서 [STATE_OBJECT_EVENT_PILOT_V0.md](STATE_OBJECT_EVENT_PILOT_V0.md)와 원 판정 [checker_verdict.json](state_object_event_pilot_v0/checker_verdict.json)은 **수정하지 않았다**. 수정한 판정은 [checker_verdict_corrected.json](state_object_event_pilot_v0/checker_verdict_corrected.json)에 별도로 남겼다.
근거: 외부 제한 재검토(LIMITED_REVIEW, EVOLVING_CALCULATOR_DESIGN_V1 S03)가 보고한 세 결함. 범위는 이 세 결함으로 한정했다.

## 결함 재현 (원 checker, 증거 사본을 변조)

| 결함 | 변조 | 원 checker 판정 |
|---|---|---|
| F-METRIC | 후보 96/100 세 반복의 운동량 반경 기록만 10⁻¹⁰⁰으로 바꿈(구간은 그대로) | SOUNDNESS PASS, CORRELATION YES |
| F-INCOMPLETE | stage 2 파일과 stage-2 seal 삭제 | 누락을 찾기 **전에** PASS·YES를 계산해 그대로 반환 |
| F-COMPLETENESS | `completed_steps = 0`(읽은 체크포인트는 그대로) / 실행의 `prec` 기록을 96으로 바꿈 | 둘 다 PASS, YES |

## 제한 수정 (`checker.check_part_b`만 수정, 다른 판정 로직·실행기·원 증거는 변경 없음)

1. **F-METRIC:** 정규화 반경은 원시 끝점(`ranges`)에서 정확한 분수로 다시 계산한다. 기록된 반경은 비교 대상일 뿐이며, 다르면 `invalid_evidence`로 남긴다. 확장 판정의 신호 계산에도 다시 계산한 값만 쓴다. 반복 사이 반경 불일치도 기록한다.
2. **F-COMPLETENESS:** 실행마다 path·precision·horizon·요청 집합이 계획과 같은지 확인한다. 또 `completed_steps` 범위, stop이 없을 때 완주 여부, stop_step 존재, 요청하지 않은 체크포인트나 완료 수를 넘은 체크포인트, 완료 수 이내인데 빠진 체크포인트를 검사한다.
3. **F-INCOMPLETE:** stage-1 확장 적격성(`stage1_extension_eligibility`)은 stage-1 증거만으로 따로 계산하며, 나중의 누락이 이 값을 고쳐 쓰지 않는다. 그 뒤 캠페인 완결성(규칙이 요구한 stage 2의 존재)을 확인한다. **최종 등급은 모든 증거를 확인한 다음 마지막에** 계산한다. 누락이나 무효 증거가 있으면 SOUNDNESS·CORRELATION·COST·TAG_GROWTH는 긍정 등급을 내지 않는다(UNRESOLVED).

회귀시험: [test_state_object_event_pilot_v0_checker_fix.py](../../tests/test_state_object_event_pilot_v0_checker_fix.py) 5개. 변조하지 않은 증거 통과 1개, 세 결함의 변조 사본 거부 4개. 수정 전에는 5개 모두 실패했고, 수정 후에는 모두 통과한다.

## 기존 증거 재판정

원 결과 묶음(`results.json.gz`)을 수정 checker로 다시 판정했다.

| 축 | 원 판정 | 수정 판정 |
|---|---|---|
| LINEAGE_SOUNDNESS | PASS | PASS |
| LINEAGE_CORRELATION | YES | YES |
| LINEAGE_COST | WORSE | WORSE |
| TAG_GROWTH | CONTROLLED | CONTROLLED |
| stage-1 확장 적격성 | EXTEND | EXTEND |
| invalid_evidence / incomplete | (검사 없음) | 0 / 0 |

원시 끝점에서 다시 계산한 반경은 저장된 반경과 모두 같았다(stage-1 운동량 반경비 4.0367). PART A와 증명서 판정도 원래와 같다(PART A 코드는 수정하지 않음).
**해석:** 원 측정값이 이번 세 결함 때문에 틀렸다는 증거는 없다. 다만 원 checker의 PASS는 이 세 종류의 위조·누락을 걸러낼 수 없었다. 따라서 원 PASS를 근거로 쓰는 것은 수정 판정으로만 한다.

## 이 단계에서 하지 않은 것 / 정정해 둘 해석

- **WORLD_LIVE_MEMORY 규칙(감소도 GROWS로 셈)은 이번 범위가 아니다.** 원 판정을 그대로 두었다.
- **FOREST_PROBE_1(scratch)의 원시 끝점은 저장되지 않았다.** 복구한 것으로 취급하지 않는다. 그 JSON의 반경·결정 여부는 다시 검증할 수 없는 기록이다.
- **이전 채팅 보고 정정:**
  - 128비트(4,570 step에서 정지)와 512비트(10,000 step 완주)의 step당 평균으로 낸 "1.23배"는 같은 작업의 비교가 아니므로 P4를 판정할 수 없다.
  - "10만 step 1시간 / 1000만 step 역전 / 수백 년"은 검증 가능한 비용 모형이 없는 외삽이므로 결정 근거에서 철회한다.
  - "숲에서도 기존 방식이 이긴다"도 후보를 긴 시간에서 실제로 맞붙인 적이 없으므로 철회한다.
- PID 25700(`cstream_event_lineage_scratch.py`)은 외부 검토 세션이 종료했다고 기록되어 있다. 이 세션에서는 종료하지 않았다.

**검증:** 관련 시험 40개 통과(회귀 5, 단위·결함 주입 33, 증거 2). LOCAL FULL은 생략하고 관련 시험으로 대체했다. 이유: 이번 Gate의 checker와 시험·문서만 바꿨고, 동결 코드·공용 checker는 변경하지 않았다.
