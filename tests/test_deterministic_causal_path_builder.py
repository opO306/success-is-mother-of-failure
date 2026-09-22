import json
import tempfile
from pathlib import Path

import pytest

from engine.deterministic import (
    BondRuleRoleTarget,
    BondTraceSubject,
    CausalWorldSpec,
    ControlDefinition,
    DiscriminatingPrediction,
    ExactConstraint,
    HeatCellTraceSubject,
    InterventionDefinition,
    InterventionRecord,
    InvestigationTarget,
    KernelPhase,
    MechanismTestPlan,
    ParticleTraceSubject,
    ResearchDomain,
    ResearchJournal,
    TraceSpec,
    build_cross_role_timeline,
    build_from_evidence,
    can_chain,
    extract_state_changes,
    investigate,
    load_causal_world_spec,
    path_status,
    propose_causal_edge,
    read_journal,
    rebuild_causal_graph,
    run_mechanism_test,
    run_traced,
    strengthen_edge_with_contradiction,
    validate_relation,
    verify_journal,
)
from engine.deterministic.causal_graph_model import CausalNode
from engine.deterministic.causal_timeline import StateChangeEvent
from engine.deterministic.mechanism_candidate import MechanismCandidate, MechanismCandidateSet, MechanismStep
from engine.deterministic.mechanism_test import MechanismEvidence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

BREAK_HEAT_CONTROL = ControlDefinition(
    "causal.control.break_heat", BondRuleRoleTarget("bond_under_test", "kind0-facing-bond-v1", "break_heat"),
    "causal.bond.break_heat",
)

TRACE_SPEC = TraceSpec("T-mechanism", (
    HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
    ParticleTraceSubject("particle_b", 11, 10, "W", ("kinetic_energy",)),
    BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists",)),
), 0, 2)


def _spec_with_heat(energy: int, world_id: str) -> CausalWorldSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 10, "y": 10, "energy": energy}] if energy else []
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


def _bond_outcome(snapshots) -> str:
    final = next(s for s in snapshots if s.tick == 2 and s.phase == KernelPhase.POST_TICK)
    return "bond_breaks" if not final.values["target_bond"]["exists"] else "bond_survives"


def _run_full_b04_b05_pipeline(journal: ResearchJournal):
    """Reproduces the confirmed B0.4/B0.5 heat=2 scenario, returning its evidence for B0.6 to consume."""
    baseline_spec = _spec_with_heat(1, "heat-1")
    contrast_spec = _spec_with_heat(2, "heat-2")

    target = InvestigationTarget(
        "IT-heat-boundary", "BOUNDARY-heat-1-2", baseline_spec.digest, contrast_spec.digest,
        "target_bond.exists differs at tick 2 (survives vs breaks)", ("heated_cell", "target_bond"), 0, 2,
    )
    interventions = (InterventionRecord("heated_cell", "energy", 1, 2, 0, "SET_ONCE"),)
    b04_outcome = investigate(journal, target, TRACE_SPEC, baseline_spec, contrast_spec, "heated_cell", interventions)

    b05_base_spec = _spec_with_heat(2, "heat-2-base")
    intervention = InterventionDefinition("causal.control.break_heat", BREAK_HEAT_CONTROL, "SET_ONCE", 4)
    plan = MechanismTestPlan(
        "P-break-rule-vs-particle-state", "MECH-IT-heat-boundary-target_bond",
        ("MECH-IT-heat-boundary-heated_cell",), (intervention,),
        (DiscriminatingPrediction("MECH-IT-heat-boundary-target_bond", "bond_survives"),
         DiscriminatingPrediction("MECH-IT-heat-boundary-heated_cell", "bond_breaks")),
        ("particle_a", "particle_b"),
    )
    result, b05_evidence, feasibility = run_mechanism_test(
        journal, b05_base_spec, {"causal.control.break_heat": BREAK_HEAT_CONTROL}, plan, TRACE_SPEC, _bond_outcome,
    )
    return b04_outcome, plan, result, b05_evidence, feasibility


def _build_timeline_for_contrast_world():
    """The real, deduplicated cross-role timeline for the heat=2 (bond-breaks) world -- what
    build_from_evidence should actually be given, never a MechanismCandidate.path.
    """
    spec = _spec_with_heat(2, "heat-2-timeline")
    snapshots = run_traced(spec, TRACE_SPEC)
    changes = extract_state_changes(snapshots)
    return build_cross_role_timeline(changes)


def test_extract_state_changes_has_no_repeated_stationary_values() -> None:
    timeline = _build_timeline_for_contrast_world()
    # Ground truth established by direct measurement: 8 raw (tick, phase)
    # snapshots normalize to 4 real instants, with exactly two points where
    # anything actually changed (particles colliding/bonding, then the
    # bond-break phase consuming heat/removing the bond/releasing particles).
    assert len(timeline) == 2
    first, second = timeline
    assert {c.role for c in first.changes} == {"particle_a", "particle_b", "target_bond"}
    assert {c.role for c in second.changes} == {"heated_cell", "particle_a", "particle_b", "target_bond"}
    assert second.phase == KernelPhase.AFTER_BOND_BREAK_PHASE


def test_build_from_evidence_creates_conditional_edge_not_a_blanket_heat_rule(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    b04_outcome, plan, result, b05_evidence, feasibility = _run_full_b04_b05_pipeline(journal)

    assert feasibility.status == "AVAILABLE"
    assert result.intervention_outcome == "bond_survives"
    by_id = {e.mechanism_candidate_id: e.relation for e in b05_evidence}
    assert by_id["MECH-IT-heat-boundary-target_bond"] == "SUPPORTS"
    assert by_id["MECH-IT-heat-boundary-heated_cell"] == "CONTRADICTS"

    domain = ResearchDomain("D-heat-boundary", (ExactConstraint("causal.bond.break_heat", 2),))
    timeline = _build_timeline_for_contrast_world()
    path = build_from_evidence(journal, "PATH-heat-boundary", timeline, b04_outcome.mechanism_candidates,
                               b05_evidence, domain)

    assert path is not None
    graph = rebuild_causal_graph(journal.path)
    edge_node_pairs = [(graph["edges"][eid].source_node_id, graph["edges"][eid].target_node_id)
                      for eid in path.edge_ids]

    # No edge anywhere is a heat-only -> outcome shortcut: heated_cell only
    # appeared in the CONTRADICTS candidate's role, so it contributes no edges.
    heat_node = CausalNode("state", "heated_cell", "energy", domain.domain_id).node_id
    for source_id, target_id in edge_node_pairs:
        assert source_id != heat_node and target_id != heat_node

    journal.close()
    assert verify_journal(journal.path)["valid"] is True


def test_same_atomic_group_never_becomes_an_edge_with_itself(tmp_path: Path) -> None:
    """particle_a/particle_b/target_bond all change together in the same AtomicChangeGroup
    (AFTER_BOND_BREAK_PHASE). build_from_evidence must never propose an edge
    between two changes in that same group -- only between distinct groups.
    """
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    b04_outcome, _plan, _result, b05_evidence, _feasibility = _run_full_b04_b05_pipeline(journal)

    domain = ResearchDomain("D-heat-boundary", ())
    timeline = _build_timeline_for_contrast_world()
    assert len(timeline) == 2  # exactly two distinct instants of real change

    build_from_evidence(journal, "PATH-1", timeline, b04_outcome.mechanism_candidates, b05_evidence, domain)

    entries = read_journal(journal.path)
    atomic_recorded = [e for e in entries if e.event_type == "atomic_event_recorded"]
    edge_proposed = [e for e in entries if e.event_type == "causal_edge_proposed"]

    assert len(atomic_recorded) >= 1
    # Every proposed edge connects nodes from the two *different* groups
    # (target_bond, the only role in both b04_outcome.mechanism_candidates
    # SUPPORTS set) -- never two changes drawn from the same group.
    for entry in edge_proposed:
        assert entry.payload["source_node_id"] != entry.payload["target_node_id"]


def test_rejected_relation_never_produces_an_edge(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    domain = ResearchDomain("D-1", ())
    a = CausalNode("state", "role_a", "field_a", "D-1")
    b = CausalNode("state", "role_a", "field_a", "D-1")  # identical node -> self-loop rejection

    edge = propose_causal_edge(journal, a, b, domain, domain, False, ("OBS-1",), ())
    assert edge is None

    entries = read_journal(journal.path)
    assert [e.event_type for e in entries] == ["causal_edge_rejected"]


def test_contradiction_is_added_not_deleted(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    domain = ResearchDomain("D-1", ())
    source = CausalNode("state", "role_a", "field_a", "D-1")
    target = CausalNode("outcome", "role_b", "field_b", "D-1")

    edge = propose_causal_edge(journal, source, target, domain, domain, False, (), ("MECH-1",))
    assert edge.status == "SUPPORTED"

    updated = strengthen_edge_with_contradiction(journal, edge, "MECH-2")
    assert updated.status == "UNRESOLVED"
    assert "MECH-1" in updated.evidence.intervention_evidence_ids
    assert "MECH-2" in updated.evidence.contradiction_evidence_ids

    journal.close()
    entries = read_journal(journal.path)
    assert [e.event_type for e in entries] == ["causal_edge_proposed", "causal_edge_updated"]


def test_journal_restart_reconstructs_identical_causal_graph(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    b04_outcome, _plan, _result, b05_evidence, _feasibility = _run_full_b04_b05_pipeline(journal)
    domain = ResearchDomain("D-heat-boundary", ())
    timeline = _build_timeline_for_contrast_world()
    build_from_evidence(journal, "PATH-1", timeline, b04_outcome.mechanism_candidates, b05_evidence, domain)

    graph_before_close = rebuild_causal_graph(journal.path)
    journal.close()
    assert verify_journal(journal.path)["valid"] is True

    graph_after_reopen = rebuild_causal_graph(journal.path)
    assert {eid: e.canonical() for eid, e in graph_before_close["edges"].items()} == \
           {eid: e.canonical() for eid, e in graph_after_reopen["edges"].items()}
    assert {pid: p.canonical() for pid, p in graph_before_close["paths"].items()} == \
           {pid: p.canonical() for pid, p in graph_after_reopen["paths"].items()}


def test_validate_relation_rejects_non_overlapping_domains() -> None:
    a = CausalNode("state", "role_a", "field_a", "D-1")
    b = CausalNode("outcome", "role_b", "field_b", "D-1")
    d1 = ResearchDomain("D1", (ExactConstraint("causal.bond.break_heat", 2),))
    d2 = ResearchDomain("D2", (ExactConstraint("causal.bond.break_heat", 4),))
    rejection = validate_relation(a, b, d1, d2, False, True)
    assert rejection is not None
    assert "do not overlap" in rejection.reason


def test_can_chain_rejects_different_middle_nodes() -> None:
    ab_target = CausalNode("state", "role_b", "field_b", "D-1")
    bc_source = CausalNode("state", "role_b", "field_c", "D-1")  # different field -> different node
    domain = ResearchDomain("D-1", ())
    rejection = can_chain(ab_target, bc_source, domain, domain)
    assert rejection is not None


def test_build_from_evidence_uses_observed_role_not_source_role() -> None:
    """Field-semantics contract test (per docs/README's B0.6_Causal_Timeline_Evidence_Rules.md
    rule 10-12): a MechanismCandidate's `source_role` names where the
    investigation started, not the role its `path` actually concerns.
    build_from_evidence must derive which roles to build edges from by
    reading `candidate.path[*].role` -- never by reading `source_role`.
    This is deliberately set up so the two disagree: if a future change
    reintroduces the `source_role` bug, this test catches it immediately.
    """
    # source_role is "heated_cell" -- the investigation's starting point --
    # but this candidate's path is entirely about target_bond, a different role.
    candidate = MechanismCandidate(
        "MECH-IT-1-target_bond", "IT-1", "heated_cell",
        (MechanismStep("target_bond", "exists"), MechanismStep("target_bond", "stored_energy")),
    )
    candidate_set = MechanismCandidateSet("IT-1", (candidate,))
    evidence = (MechanismEvidence("MECH-IT-1-target_bond", "P-1", "SUPPORTS", "matched prediction"),)

    # A synthetic two-moment timeline touching only target_bond, so the
    # test isolates the role-selection logic from the real trace.
    e1 = StateChangeEvent(3, 1, KernelPhase.AFTER_BOND_BREAK_PHASE, "target_bond", "exists", True, False)
    e2 = StateChangeEvent(4, 1, KernelPhase.POST_TICK, "target_bond", "stored_energy", 4, None)
    timeline = build_cross_role_timeline((e1, e2))

    with tempfile.TemporaryDirectory() as tmp:
        journal = ResearchJournal.create(Path(tmp) / "journal.jsonl")
        domain = ResearchDomain("D-1", ())
        path = build_from_evidence(journal, "PATH-1", timeline, candidate_set, evidence, domain)

        # If the code mistakenly used source_role ("heated_cell") to select
        # relevant timeline groups, no group would match (heated_cell never
        # appears in this synthetic timeline) and path would be None.
        assert path is not None
        graph = rebuild_causal_graph(journal.path)
        edge = graph["edges"][path.edge_ids[0]]
        expected_source = CausalNode("state", "target_bond", "exists", domain.domain_id).node_id
        expected_target = CausalNode("state", "target_bond", "stored_energy", domain.domain_id).node_id
        heated_cell_node = CausalNode("state", "heated_cell", "energy", domain.domain_id).node_id
        assert edge.source_node_id == expected_source
        assert edge.target_node_id == expected_target
        assert edge.source_node_id != heated_cell_node
        assert edge.target_node_id != heated_cell_node
        journal.close()
