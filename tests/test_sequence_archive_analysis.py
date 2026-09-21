from analyze_sequence_archive import analyze_records


def _frame(index: int, event_type: str, payload: dict) -> dict:
    return {"index": index, "event": {"event_type": event_type, "payload": payload}}


def _row(frames: list[dict]) -> dict:
    return {
        "archive": {"frames": frames, "stop_reason": "event_limit"},
        "case_tag": "pair:test",
        "seed": 0,
        "observation": {"longest_contact_state_span": 0},
    }


def test_cleavage_of_another_strand_does_not_end_growth_product() -> None:
    result = analyze_records(
        (
            _row(
                [
                    _frame(0, "sequence.backbone_join", {"new_strand_id": 7}),
                    _frame(1, "sequence.backbone_cleave", {"parent_strand_id": 3}),
                ]
            ),
        )
    )

    assert result["exact_growth_outcomes"] == {"present_at_end": 1}
    assert result["maximum_exact_growth_state_span"] == 2


def test_only_cleavage_of_the_product_ends_its_exact_identity() -> None:
    result = analyze_records(
        (
            _row(
                [
                    _frame(0, "sequence.backbone_join", {"new_strand_id": 7}),
                    _frame(1, "sequence.bind", {}),
                    _frame(2, "sequence.backbone_cleave", {"parent_strand_id": 7}),
                ]
            ),
        )
    )

    assert result["exact_growth_outcomes"] == {"cleaved": 1}
    assert result["maximum_exact_growth_state_span"] == 2
