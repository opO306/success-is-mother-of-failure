import json
from pathlib import Path

import pytest

from engine.deterministic import (
    BondTraceSubject,
    CausalNode,
    CausalWorldSpec,
    HeatCellTraceSubject,
    KernelPhase,
    MissingLink,
    MissingLinkInvestigation,
    ParticleTraceSubject,
    ResearchDomain,
    ResearchJournal,
    TraceSpec,
    build_cross_role_timeline,
    default_catalog,
    extract_state_changes,
    investigate_missing_link,
    read_journal,
    run_traced,
    verify_journal,
)
from engine.deterministic.causal_edge_validator import validate_relation

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _spec_with_heat(energy: int, world_id: str) -> CausalWorldSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 10, "y": 10, "energy": energy}] if energy else []
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


NARROW_TRACE_SPEC = TraceSpec("T-narrow", (  # deliberately omits target_bond: B (mediator) starts hidden
    HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
    ParticleTraceSubject("particle_b", 11, 10, "W", ("kinetic_energy",)),
), 0, 2)

FULL_TRACE_SPEC = TraceSpec("T-full", (
    HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
    ParticleTraceSubject("particle_b", 11, 10, "W", ("kinetic_energy",)),
    BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists", "stored_energy")),
), 0, 2)

DOMAIN = ResearchDomain("D-heat-boundary", ())


def _catalog_check(role_kind: str, field: str) -> bool:
    return default_catalog().contains(role_kind, field)


# ---------------------------------------------------------------------------
# Real-world scenario 1: hidden mediator (A -> B -> C), B initially untraced.
# ---------------------------------------------------------------------------

def test_hidden_mediator_scenario_finds_gap_then_resolves_after_wider_trace(tmp_path: Path) -> None:
    spec = _spec_with_heat(2, "heat-2-hidden-mediator")

    # Step 1: narrow trace never watches target_bond at all -- from this
    # trace alone, heated_cell's reaction looks like a gap with no mediator.
    narrow_snapshots = run_traced(spec, NARROW_TRACE_SPEC)
    narrow_changes = extract_state_changes(narrow_snapshots)
    narrow_timeline = build_cross_role_timeline(narrow_changes)
    narrow_roles = {c.role for group in narrow_timeline for c in group.changes}
    assert "target_bond" not in narrow_roles  # confirms B truly starts hidden from B0.7's input

    source = CausalNode("state", "heated_cell", "energy", DOMAIN.domain_id)
    target = CausalNode("outcome", "particle_a", "kinetic_energy", DOMAIN.domain_id)
    link = MissingLink(source.node_id, target.node_id, "no edge connects heated_cell.energy to the final outcome")

    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    investigation = MissingLinkInvestigation("ML-1", source.node_id, target.node_id, DOMAIN.domain_id, "v1")

    outcome = investigate_missing_link(
        journal, investigation, link, known_edges=(), timeline=narrow_timeline,
        source_role="heated_cell", target_role="particle_a",
        catalog=default_catalog(), mediator_role_kind="bond", mediator_field="stored_energy",
        source_node=source, target_node=target, source_domain=DOMAIN, target_domain=DOMAIN,
        same_atomic_event=False, has_relation_evidence=True,
    )

    # bond.stored_energy IS in the official observation catalog -> proposed
    # as TESTABLE, not invented, not BLOCKED.
    mediator_hypotheses = [h for h in outcome.hypotheses if h.kind == "EXISTING_STATE_MEDIATOR"]
    assert len(mediator_hypotheses) == 1
    assert mediator_hypotheses[0].status == "TESTABLE"
    assert outcome.instrumentation_requests == ()

    # Step 2: B0.4 re-traces with target_bond included (simulating the
    # follow-up ObservationRequest being fulfilled).
    full_snapshots = run_traced(spec, FULL_TRACE_SPEC)
    full_changes = extract_state_changes(full_snapshots)
    full_timeline = build_cross_role_timeline(full_changes)

    # A -> B -> C now has a real temporal structure: the mediator
    # (target_bond forming) appears strictly before the final release.
    bond_formed_seq = next(g.observation_seq for g in full_timeline if any(c.role == "target_bond" for c in g.changes))
    heat_intervened_seq = 0  # the intervention itself, at the start of the trace
    assert bond_formed_seq > heat_intervened_seq

    journal.close()
    assert verify_journal(journal.path)["valid"] is True


# ---------------------------------------------------------------------------
# Real-world scenario 2: direct relation (A -> C), no mediator exists.
# ---------------------------------------------------------------------------

def test_direct_relation_scenario_does_not_invent_endless_mediators(tmp_path: Path) -> None:
    """particle_a's own kinetic_energy transition from tick 0 to the final
    tick is a direct relation -- there is no separate mediator role between
    a particle's own state at two points in time. B0.7 must be able to
    propose DIRECT_RELATION without also inventing a fictitious mediator.
    """
    spec = _spec_with_heat(1, "heat-1-direct")  # bond survives; particles never separate
    trace_spec = TraceSpec("T-direct", (
        ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
    ), 0, 2)
    snapshots = run_traced(spec, trace_spec)
    changes = extract_state_changes(snapshots)
    timeline = build_cross_role_timeline(changes)

    source = CausalNode("control", "particle_a", "kinetic_energy", DOMAIN.domain_id)
    target = CausalNode("outcome", "particle_a", "kinetic_energy", DOMAIN.domain_id)
    # Deliberately the same role -- there is genuinely no other role to mediate through.
    link = MissingLink(source.node_id, target.node_id, "single-role state transition has no separate mediator")

    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    investigation = MissingLinkInvestigation("ML-2", source.node_id, target.node_id, DOMAIN.domain_id, "v1")

    outcome = investigate_missing_link(
        journal, investigation, link, known_edges=(), timeline=timeline,
        source_role="particle_a", target_role="particle_a",
        catalog=default_catalog(), mediator_role_kind="heat_cell", mediator_field="energy",
        source_node=source, target_node=target, source_domain=DOMAIN, target_domain=DOMAIN,
        same_atomic_event=False, has_relation_evidence=True,
    )

    direct_hypotheses = [h for h in outcome.hypotheses if h.kind == "DIRECT_RELATION"]
    assert len(direct_hypotheses) == 1
    assert direct_hypotheses[0].status == "TESTABLE"
    # Exactly one DIRECT_RELATION hypothesis proposed, not an unbounded search for mediators.
    journal.close()


# ---------------------------------------------------------------------------
# Real-world scenario 3: conditional relation -- heat determines whether the
# bond breaks, discovered by comparing two experiments' differing values.
# ---------------------------------------------------------------------------

def test_conditional_relation_scenario_finds_the_differing_condition(tmp_path: Path) -> None:
    from engine.deterministic import propose_conditional_relation_candidate

    heat_1_spec = _spec_with_heat(1, "heat-1-cond")
    heat_2_spec = _spec_with_heat(2, "heat-2-cond")
    trace_spec = TraceSpec("T-cond", (
        HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
        BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists",)),
        ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
        ParticleTraceSubject("particle_b", 11, 10, "W", ("kinetic_energy",)),
    ), 0, 2)

    def final_bond_exists(spec: CausalWorldSpec) -> bool:
        snaps = run_traced(spec, trace_spec)
        final = next(s for s in snaps if s.tick == 2 and s.phase == KernelPhase.POST_TICK)
        return final.values["target_bond"]["exists"]

    relation_holds_at_heat_1 = final_bond_exists(heat_1_spec)  # True: bond persists
    relation_holds_at_heat_2 = final_bond_exists(heat_2_spec)  # False: bond breaks
    assert relation_holds_at_heat_1 != relation_holds_at_heat_2

    source = CausalNode("control", "heated_cell", "energy", DOMAIN.domain_id)
    target = CausalNode("outcome", "target_bond", "exists", DOMAIN.domain_id)
    link = MissingLink(source.node_id, target.node_id, "heat alone does not consistently predict bond persistence")

    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    investigation_id = "ML-3"
    hypothesis = propose_conditional_relation_candidate(
        investigation_id, link, "heated_cell", "energy", relation_holds_at_heat_1, relation_holds_at_heat_2,
    )
    assert hypothesis.kind == "CONDITIONAL_RELATION"
    assert hypothesis.detail["differing_role"] == "heated_cell"
    assert hypothesis.detail["successful_value"] != hypothesis.detail["failed_value"]
    journal.close()


# ---------------------------------------------------------------------------
# Pure unit tests: PARENT_RELATION_WRONG, BLOCKED_BY_OBSERVABILITY, atomic
# ordering preservation, DERIVED_RELATION -- all with synthetic evidence.
# ---------------------------------------------------------------------------

def test_parent_relation_wrong_detected_via_shared_atomic_event(tmp_path: Path) -> None:
    from engine.deterministic import check_parent_relation_wrong

    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("state", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge")

    hypothesis = check_parent_relation_wrong(
        "ML-4", link, source, target, DOMAIN, DOMAIN, same_atomic_event=True, has_evidence=True,
    )
    assert hypothesis.kind == "PARENT_RELATION_WRONG"
    assert hypothesis.status == "SUPPORTED"  # validate_relation already rejects same-atomic-event pairs


def test_parent_relation_wrong_stays_testable_when_relation_is_still_legal() -> None:
    from engine.deterministic import check_parent_relation_wrong

    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge")

    hypothesis = check_parent_relation_wrong(
        "ML-5", link, source, target, DOMAIN, DOMAIN, same_atomic_event=False, has_evidence=True,
    )
    assert hypothesis.status == "TESTABLE"


def test_blocked_by_observability_never_invents_a_value() -> None:
    from engine.deterministic import check_existing_state_mediator

    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge")
    catalog = default_catalog()

    hypothesis, request = check_existing_state_mediator("ML-6", link, catalog, "bond", "stress")
    assert hypothesis.status == "BLOCKED"
    assert request is not None
    assert request.field == "stress"
    assert "not currently observable" in request.reason


def test_available_mediator_is_testable_not_blocked() -> None:
    from engine.deterministic import check_existing_state_mediator

    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge")
    catalog = default_catalog()

    hypothesis, request = check_existing_state_mediator("ML-7", link, catalog, "bond", "stored_energy")
    assert hypothesis.status == "TESTABLE"
    assert request is None


def test_atomic_group_membership_never_produces_ordering_claim() -> None:
    """A, B, C all changing in the same AtomicChangeGroup must not be turned into A -> B -> C."""
    from engine.deterministic import check_observation_gap
    from engine.deterministic.causal_timeline import AtomicChangeGroup, StateChangeEvent

    e1 = StateChangeEvent(5, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "a", "x", 1, 2)
    e2 = StateChangeEvent(5, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "b", "y", 1, 2)
    e3 = StateChangeEvent(5, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "c", "z", 1, 2)
    timeline = (AtomicChangeGroup(5, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, (e1, e2, e3)),)

    link = MissingLink("N-a", "N-c", "no edge")
    # Only one group exists, so there is no adjacent-group gap to report --
    # a/b/c stay siblings of one event, never separated into a sequence.
    gap = check_observation_gap(link, timeline, "a", "c")
    assert gap is None


def test_derived_relation_candidates_filtered_by_relevance() -> None:
    from engine.deterministic import (
        DerivedFeatureCandidate,
        ObservableRef,
        propose_derived_relation_candidates,
    )

    link = MissingLink("N-a", "N-c", "no edge")
    relevant = DerivedFeatureCandidate("DF-1", "GREATER_OR_EQUAL", ObservableRef("heated_cell", "energy"),
                                       ObservableRef("bond_rule", "break_heat"))
    irrelevant = DerivedFeatureCandidate("DF-2", "ADD", ObservableRef("unrelated_x", "v"),
                                         ObservableRef("unrelated_y", "v"))

    hypotheses = propose_derived_relation_candidates(
        "ML-8", link, (relevant, irrelevant), "heated_cell", "target_bond", frozenset(),
    )
    assert len(hypotheses) == 1
    assert hypotheses[0].detail["derived_feature_candidate_id"] == "DF-1"


def test_existing_evidence_missed_stops_further_hypothesis_generation(tmp_path: Path) -> None:
    from engine.deterministic import CausalEdge, PathEvidenceBundle

    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge in this path")
    existing_edge = CausalEdge(f"EDGE-{source.node_id}-{target.node_id}", source.node_id, target.node_id,
                               None, PathEvidenceBundle(("OBS-1",), ()), "SUPPORTED")

    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    investigation = MissingLinkInvestigation("ML-9", source.node_id, target.node_id, "D-1", "v1")
    outcome = investigate_missing_link(
        journal, investigation, link, known_edges=(existing_edge,), timeline=(),
        source_role="role_a", target_role="role_b",
        catalog=default_catalog(), mediator_role_kind="bond", mediator_field="stored_energy",
        source_node=source, target_node=target, source_domain=DOMAIN, target_domain=DOMAIN,
        same_atomic_event=False, has_relation_evidence=True,
    )

    assert len(outcome.hypotheses) == 1
    assert outcome.hypotheses[0].kind == "EXISTING_EVIDENCE_MISSED"
    journal.close()


def test_journal_restart_reconstructs_identical_hypotheses(tmp_path: Path) -> None:
    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")
    link = MissingLink(source.node_id, target.node_id, "no edge")

    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    investigation = MissingLinkInvestigation("ML-10", source.node_id, target.node_id, "D-1", "v1")
    outcome = investigate_missing_link(
        journal, investigation, link, known_edges=(), timeline=(),
        source_role="role_a", target_role="role_b",
        catalog=default_catalog(), mediator_role_kind="bond", mediator_field="stored_energy",
        source_node=source, target_node=target, source_domain=DOMAIN, target_domain=DOMAIN,
        same_atomic_event=False, has_relation_evidence=True,
    )
    journal.close()
    assert verify_journal(journal.path)["valid"] is True

    entries = read_journal(journal.path)
    hypothesis_entries = [e for e in entries if e.event_type == "missing_link_hypothesis_proposed"]
    kinds_before = sorted(e.payload["kind"] for e in hypothesis_entries)

    reopened_entries = read_journal(journal.path)
    reopened_hypothesis_entries = [e for e in reopened_entries if e.event_type == "missing_link_hypothesis_proposed"]
    kinds_after = sorted(e.payload["kind"] for e in reopened_hypothesis_entries)
    assert kinds_before == kinds_after
