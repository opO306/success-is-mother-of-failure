import pytest

from engine.living.events import HistoryLog, RandomDraw, ReplayEventSource, SeededEventSource
from engine.sequence import (
    Contact,
    SequenceState,
    Strand,
    event_candidates,
    pair_score,
    parse_symbols,
    render_symbols,
    step,
)


def _pair() -> SequenceState:
    return SequenceState(
        strands=(Strand(20, parse_symbols("TTTT")), Strand(10, parse_symbols("AAAA"))),
        thermal_energy=8,
    )


def _choose(state: SequenceState, predicate):
    candidates = event_candidates(state)
    target = next(candidate for candidate in candidates if predicate(candidate))
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    source = ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),))
    return step(state, source)


def test_pair_score_is_symmetric_and_has_no_behavior_opcode() -> None:
    scores = {(left, right): pair_score(left, right) for left in range(4) for right in range(4)}
    assert all(scores[left, right] == scores[right, left] for left in range(4) for right in range(4))
    assert set(scores.values()) == {-2, 0, 2}


def test_display_alphabet_does_not_change_internal_sequence() -> None:
    symbols = parse_symbols("ACGT")
    assert render_symbols(symbols) == "ACGT"
    assert render_symbols(symbols, ("가", "나", "다", "라")) == "가나다라"
    assert symbols == (0, 1, 2, 3)


def test_every_nonempty_internal_sequence_is_valid() -> None:
    assert Strand(1, (0,)).symbols == (0,)
    assert Strand(2, (3, 3, 1, 0)).symbols == (3, 3, 1, 0)
    with pytest.raises(ValueError):
        Strand(3, ())
    with pytest.raises(ValueError):
        Strand(4, (4,))


def test_state_order_is_canonical_not_input_order() -> None:
    forward = _pair()
    reverse = SequenceState(tuple(reversed(forward.strands)), thermal_energy=8)
    assert forward.state_hash() == reverse.state_hash()
    assert event_candidates(forward) == event_candidates(reverse)


def test_exact_complement_has_stronger_full_overlap_than_one_mutation() -> None:
    exact = SequenceState((Strand(1, parse_symbols("ACGT")), Strand(2, parse_symbols("TGCA"))), 8)
    mutated = SequenceState((Strand(1, parse_symbols("ACGT")), Strand(2, parse_symbols("TGCC"))), 8)
    exact_full = [c for c in event_candidates(exact) if c.kind == "bind" and c.contact.length == 4][0]
    mutated_full = [c for c in event_candidates(mutated) if c.kind == "bind" and c.contact.length == 4][0]
    assert exact_full.weight == 8
    assert mutated_full.weight == 6


def test_binding_conserves_total_energy() -> None:
    state = _pair()
    result = _choose(state, lambda candidate: candidate.kind == "bind" and candidate.contact.length == 4)
    assert result.event is not None
    assert result.event.event_type == "sequence.bind"
    assert result.state.total_energy == state.total_energy
    assert result.state.time == 1


def test_separation_returns_bond_energy_to_potential() -> None:
    contact = Contact(10, 0, 20, 0, 4, 8)
    state = SequenceState(_pair().strands, thermal_energy=16, contacts=(contact,))
    result = step(state, SeededEventSource(1))
    assert result.event is not None
    assert result.event.event_type == "sequence.unbind"
    assert result.state.contacts == ()
    assert result.state.thermal_energy == 8
    assert result.state.total_energy == state.total_energy


def test_recording_does_not_change_world_result() -> None:
    state = _pair()
    plain_source = SeededEventSource(99)
    recorded_source = SeededEventSource(99)
    plain = step(state, plain_source)
    recorded = step(state, recorded_source)
    history = HistoryLog()
    history.append(recorded.random_draw.as_event(recorded.state.time))
    history.append(recorded.event)
    assert recorded.state == plain.state
    assert recorded_source.draw_count == plain_source.draw_count == 1
    assert history.verify()


def test_recorded_choice_replays_the_same_transition() -> None:
    state = _pair()
    source = SeededEventSource(123)
    original = step(state, source)
    history = HistoryLog()
    history.append(original.random_draw.as_event(original.state.time))
    replay = step(state, ReplayEventSource.from_history(history))
    assert replay.state == original.state
    assert replay.event == original.event


def test_occupied_sites_cannot_bind_twice() -> None:
    state = _pair()
    bound = _choose(state, lambda candidate: candidate.kind == "bind" and candidate.contact.length == 4).state
    assert all(candidate.kind == "unbind" for candidate in event_candidates(bound))


def test_a_strand_can_fold_without_a_special_motif_table() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGTATGCA")),), thermal_energy=8)
    folds = [candidate for candidate in event_candidates(state) if candidate.kind == "fold"]
    assert any(
        candidate.contact.left_start == 0
        and candidate.contact.right_start == 5
        and candidate.contact.length == 4
        and candidate.weight == 8
        for candidate in folds
    )


def test_folding_and_unfolding_conserve_total_energy() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGTATGCA")),), thermal_energy=8)
    folded = _choose(state, lambda candidate: candidate.kind == "fold" and candidate.contact.length == 4)
    assert folded.event.event_type == "sequence.fold"
    assert folded.state.total_energy == state.total_energy
    unfolded = _choose(folded.state, lambda candidate: candidate.kind == "unfold")
    assert unfolded.event.event_type == "sequence.unfold"
    assert unfolded.state == SequenceState(state.strands, state.thermal_energy, time=2)
    assert unfolded.state.total_energy == state.total_energy


def test_folded_sites_are_hidden_from_external_binding() -> None:
    folded_strand = Strand(1, parse_symbols("ACGTATGCA"))
    outsider = Strand(2, parse_symbols("TGCA"))
    fold = Contact(1, 0, 1, 5, 4, 8)
    state = SequenceState((folded_strand, outsider), thermal_energy=16, contacts=(fold,))
    hidden = {0, 1, 2, 3, 5, 6, 7, 8}
    for candidate in event_candidates(state):
        if candidate.kind != "bind" or candidate.contact.left_id != 1:
            continue
        used = set(range(candidate.contact.left_start, candidate.contact.left_start + candidate.contact.length))
        assert used.isdisjoint(hidden)


def test_unfolding_exposes_sites_for_external_binding_again() -> None:
    folded_strand = Strand(1, parse_symbols("ACGTATGCA"))
    outsider = Strand(2, parse_symbols("TGCA"))
    fold = Contact(1, 0, 1, 5, 4, 8)
    state = SequenceState((folded_strand, outsider), thermal_energy=16, contacts=(fold,))
    unfolded = _choose(state, lambda candidate: candidate.kind == "unfold").state
    assert any(
        candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 0
        and candidate.contact.length == 4
        for candidate in event_candidates(unfolded)
    )


def test_fold_requires_nonoverlap_and_a_loop_site() -> None:
    with pytest.raises(ValueError):
        Contact(1, 0, 1, 2, 2, 4)
    with pytest.raises(ValueError):
        Contact(1, 0, 1, 1, 1, 2)


def test_recorded_fold_replays_the_same_history() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGTATGCA")),), thermal_energy=8)
    candidates = event_candidates(state)
    target = next(c for c in candidates if c.kind == "fold" and c.contact.length == 4)
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    source = ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),))
    original = step(state, source)
    history = HistoryLog()
    history.append(original.random_draw.as_event(original.state.time))
    replay = step(state, ReplayEventSource.from_history(history))
    assert replay.state == original.state
    assert replay.event == original.event


def _template_with_two_bound_monomers(thermal_energy: int = 12) -> SequenceState:
    template = Strand(1, parse_symbols("TT"))
    first = Strand(2, parse_symbols("A"))
    second = Strand(3, parse_symbols("A"))
    return SequenceState(
        (template, first, second),
        thermal_energy,
        contacts=(Contact(1, 0, 2, 0, 1, 2), Contact(1, 1, 3, 0, 1, 2)),
    )


def test_two_monomers_can_bind_then_form_one_backbone_fragment() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("TT")), Strand(2, parse_symbols("A")), Strand(3, parse_symbols("A"))),
        thermal_energy=12,
    )
    first_bound = _choose(
        state,
        lambda candidate: candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 0
        and candidate.contact.right_id == 2,
    ).state
    both_bound = _choose(
        first_bound,
        lambda candidate: candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 1
        and candidate.contact.right_id == 3,
    ).state
    joined = _choose(both_bound, lambda candidate: candidate.kind == "join")
    assert joined.event.event_type == "sequence.backbone_join"
    assert [(strand.strand_id, render_symbols(strand.symbols)) for strand in joined.state.strands] == [
        (1, "TT"),
        (4, "AA"),
    ]
    assert joined.event.payload()["parent_strand_ids"] == [2, 3]
    assert joined.event.payload()["new_strand_id"] == 4


def test_backbone_join_conserves_symbols_and_total_energy() -> None:
    state = _template_with_two_bound_monomers()
    before_symbols = sum(len(strand.symbols) for strand in state.strands)
    joined = _choose(state, lambda candidate: candidate.kind == "join")
    after_symbols = sum(len(strand.symbols) for strand in joined.state.strands)
    assert after_symbols == before_symbols
    assert joined.state.total_energy == state.total_energy
    assert joined.state.thermal_energy == state.thermal_energy - 2


def test_nonadjacent_template_fragments_cannot_join() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("TTT")), Strand(2, (0,)), Strand(3, (0,))),
        thermal_energy=12,
        contacts=(Contact(1, 0, 2, 0, 1, 2), Contact(1, 2, 3, 0, 1, 2)),
    )
    assert not any(candidate.kind == "join" for candidate in event_candidates(state))


def test_backbone_join_requires_energy() -> None:
    state = _template_with_two_bound_monomers(thermal_energy=1)
    assert not any(candidate.kind == "join" for candidate in event_candidates(state))


def test_existing_fragment_can_extend_by_one_monomer() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("TTT")), Strand(2, parse_symbols("AA")), Strand(3, (0,))),
        thermal_energy=12,
        contacts=(Contact(1, 0, 2, 0, 2, 4), Contact(1, 2, 3, 0, 1, 2)),
    )
    joined = _choose(state, lambda candidate: candidate.kind == "join")
    product = next(strand for strand in joined.state.strands if strand.strand_id == 4)
    assert render_symbols(product.symbols) == "AAA"
    assert joined.state.contacts == (Contact(1, 0, 4, 0, 3, 6),)


def test_one_event_cannot_create_a_complete_copy_from_free_monomers() -> None:
    state = SequenceState(
        (
            Strand(1, parse_symbols("TTTT")),
            Strand(2, (0,)),
            Strand(3, (0,)),
            Strand(4, (0,)),
            Strand(5, (0,)),
        ),
        thermal_energy=20,
    )
    result = _choose(state, lambda candidate: candidate.kind == "bind")
    assert len(result.state.strands) == len(state.strands)
    assert max(len(strand.symbols) for strand in result.state.strands) == 4
    assert not any(strand.strand_id != 1 and len(strand.symbols) > 1 for strand in result.state.strands)
    assert result.event.event_type == "sequence.bind"


def test_recorded_backbone_join_replays_identically() -> None:
    state = _template_with_two_bound_monomers()
    candidates = event_candidates(state)
    target = next(candidate for candidate in candidates if candidate.kind == "join")
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    original = step(
        state,
        ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),)),
    )
    history = HistoryLog()
    history.append(original.random_draw.as_event(original.state.time))
    replay = step(state, ReplayEventSource.from_history(history))
    assert replay.state == original.state
    assert replay.event == original.event


def test_exposed_strand_has_one_cleavage_candidate_per_backbone() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGT")),), thermal_energy=4)
    cuts = [candidate.cut.cut_index for candidate in event_candidates(state) if candidate.kind == "cleave"]
    assert cuts == [1, 2, 3]


def test_cleavage_conserves_symbols_and_total_energy() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGT")),), thermal_energy=4)
    result = _choose(state, lambda candidate: candidate.kind == "cleave" and candidate.cut.cut_index == 2)
    assert result.event.event_type == "sequence.backbone_cleave"
    assert [render_symbols(strand.symbols) for strand in result.state.strands] == ["AC", "GT"]
    assert result.state.thermal_energy == state.thermal_energy + 2
    assert result.state.total_energy == state.total_energy
    assert sum(len(strand.symbols) for strand in result.state.strands) == 4
    assert result.event.payload()["parent_strand_id"] == 1
    assert result.event.payload()["child_strand_ids"] == [2, 3]


def test_side_contact_protects_adjacent_backbones_from_cleavage() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("AAA")), Strand(2, parse_symbols("T"))),
        thermal_energy=4,
        contacts=(Contact(1, 1, 2, 0, 1, 2),),
    )
    assert not any(candidate.kind == "cleave" and candidate.cut.strand_id == 1 for candidate in event_candidates(state))


def test_unbinding_makes_protected_backbones_cleavable_again() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("AAA")), Strand(2, parse_symbols("T"))),
        thermal_energy=4,
        contacts=(Contact(1, 1, 2, 0, 1, 2),),
    )
    unbound = _choose(state, lambda candidate: candidate.kind == "unbind").state
    cuts = [
        candidate.cut.cut_index
        for candidate in event_candidates(unbound)
        if candidate.kind == "cleave" and candidate.cut.strand_id == 1
    ]
    assert cuts == [1, 2]


def test_contact_outside_cut_is_remapped_to_the_correct_child() -> None:
    state = SequenceState(
        (Strand(1, parse_symbols("AAAA")), Strand(2, parse_symbols("T"))),
        thermal_energy=4,
        contacts=(Contact(1, 0, 2, 0, 1, 2),),
    )
    result = _choose(
        state,
        lambda candidate: candidate.kind == "cleave"
        and candidate.cut.strand_id == 1
        and candidate.cut.cut_index == 2,
    )
    assert result.state.contacts == (Contact(2, 0, 3, 0, 1, 2),)
    assert [(strand.strand_id, render_symbols(strand.symbols)) for strand in result.state.strands] == [
        (2, "T"),
        (3, "AA"),
        (4, "AA"),
    ]


def test_recorded_cleavage_replays_identically() -> None:
    state = SequenceState((Strand(1, parse_symbols("ACGT")),), thermal_energy=4)
    candidates = event_candidates(state)
    target = next(
        candidate for candidate in candidates if candidate.kind == "cleave" and candidate.cut.cut_index == 2
    )
    ticket = sum(candidate.weight for candidate in candidates[: candidates.index(target)])
    total = sum(candidate.weight for candidate in candidates)
    original = step(
        state,
        ReplayEventSource((RandomDraw(0, "choice_index", (total,), ticket),)),
    )
    history = HistoryLog()
    history.append(original.random_draw.as_event(original.state.time))
    replay = step(state, ReplayEventSource.from_history(history))
    assert replay.state == original.state
    assert replay.event == original.event


def test_join_release_and_cleave_form_an_energy_conserving_cycle() -> None:
    state = _template_with_two_bound_monomers()
    joined = _choose(state, lambda candidate: candidate.kind == "join").state
    released = _choose(joined, lambda candidate: candidate.kind == "unbind").state
    cleaved = _choose(
        released,
        lambda candidate: candidate.kind == "cleave" and candidate.cut.strand_id == 4,
    ).state
    assert cleaved.total_energy == state.total_energy
    assert sorted(render_symbols(strand.symbols) for strand in cleaved.strands) == ["A", "A", "TT"]


def _folded_pocket_with_outsider() -> SequenceState:
    scaffold = Strand(1, parse_symbols("ATTT"))
    outsider = Strand(2, parse_symbols("A"))
    return SequenceState(
        (scaffold, outsider),
        thermal_energy=8,
        contacts=(Contact(1, 0, 1, 3, 1, 2),),
    )


def test_fold_pocket_increases_binding_residence_weight_without_a_motif_table() -> None:
    open_state = SequenceState(
        (Strand(1, parse_symbols("ATTT")), Strand(2, parse_symbols("A"))),
        thermal_energy=8,
    )
    folded_state = _folded_pocket_with_outsider()

    def target(candidate):
        return (
            candidate.kind == "bind"
            and candidate.contact.left_id == 1
            and candidate.contact.left_start == 1
            and candidate.contact.right_id == 2
        )

    open_candidate = next(candidate for candidate in event_candidates(open_state) if target(candidate))
    folded_candidate = next(candidate for candidate in event_candidates(folded_state) if target(candidate))
    assert open_candidate.base_weight == folded_candidate.base_weight == 2
    assert open_candidate.context_multiplier == 1
    assert folded_candidate.context_multiplier == 3
    assert folded_candidate.weight == 6


def test_fold_pocket_accelerates_backbone_join_by_geometry_only() -> None:
    state = SequenceState(
        (
            Strand(1, parse_symbols("ATTT")),
            Strand(2, parse_symbols("A")),
            Strand(3, parse_symbols("A")),
        ),
        thermal_energy=12,
        contacts=(
            Contact(1, 0, 1, 3, 1, 2),
            Contact(1, 1, 2, 0, 1, 2),
            Contact(1, 2, 3, 0, 1, 2),
        ),
    )
    candidate = next(candidate for candidate in event_candidates(state) if candidate.kind == "join")
    assert candidate.base_weight == 1
    assert candidate.context_multiplier == 3
    assert candidate.weight == 3


def test_fold_context_does_not_change_unfold_or_cleavage_weights() -> None:
    state = _folded_pocket_with_outsider()
    unaffected = [
        candidate
        for candidate in event_candidates(state)
        if candidate.kind in {"unfold", "cleave"}
    ]
    assert unaffected
    assert all(candidate.context_multiplier == 1 for candidate in unaffected)
    assert all(candidate.weight == candidate.base_weight for candidate in unaffected)


def test_event_records_base_weight_and_structural_context_multiplier() -> None:
    state = _folded_pocket_with_outsider()
    result = _choose(
        state,
        lambda candidate: candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 1
        and candidate.contact.right_id == 2,
    )
    payload = result.event.payload()
    assert payload["base_weight"] == 2
    assert payload["context_multiplier"] == 3


def test_nested_pocket_multiplier_is_capped() -> None:
    symbols = (0,) * 32 + (3, 3) + (3,) * 32
    scaffold = Strand(1, symbols)
    outsider = Strand(2, (0,))
    folds = tuple(Contact(1, index, 1, 65 - index, 1, 2) for index in range(32))
    state = SequenceState((scaffold, outsider), thermal_energy=128, contacts=folds)
    candidate = next(
        candidate
        for candidate in event_candidates(state)
        if candidate.kind == "bind"
        and candidate.contact.left_id == 1
        and candidate.contact.left_start == 32
        and candidate.contact.right_id == 2
    )
    assert candidate.base_weight == 2
    assert candidate.context_multiplier == 64
    assert candidate.weight == 128
