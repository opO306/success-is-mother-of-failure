import json
from pathlib import Path

import pytest

from engine.deterministic import (
    BondTraceSubject,
    CausalWorldSpec,
    FollowupExperimentProposal,
    HeatCellTraceSubject,
    InterventionRecord,
    InvestigationTarget,
    KernelPhase,
    ParticleTraceSubject,
    ResearchJournal,
    TraceSpec,
    investigate,
    load_causal_world_spec,
    propose_followup_experiment,
    read_journal,
    run_causal_world,
    run_traced,
    verify_journal,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _spec_with_heat(energy: int, world_id: str) -> CausalWorldSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["heat"] = [{"x": 10, "y": 10, "energy": energy}] if energy else []
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


HEAT_TRACE_SPEC = TraceSpec("T-heat-boundary", (
    HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ParticleTraceSubject("particle_a", 9, 10, "E", ("x", "y", "kinetic_energy")),
    ParticleTraceSubject("particle_b", 11, 10, "W", ("x", "y", "kinetic_energy")),
    BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists", "stored_energy")),
), 0, 2)


def test_kernel_observer_never_changes_the_run_digest() -> None:
    spec = load_causal_world_spec(EXAMPLE)

    class Recorder:
        def __init__(self) -> None:
            self.phases = []

        def on_phase(self, *, tick, phase, state) -> None:
            self.phases.append((tick, phase))

    recorder = Recorder()
    run_without = run_causal_world(spec)
    run_with = run_causal_world(spec, recorder)

    assert run_without.digest == run_with.digest
    assert (0, KernelPhase.PRE_TICK) in recorder.phases
    assert (0, KernelPhase.AFTER_BOND_BREAK_PHASE) in recorder.phases
    assert (1, KernelPhase.POST_TICK) in recorder.phases


def test_run_traced_covers_every_phase_in_range_without_duplication() -> None:
    spec = _spec_with_heat(2, "heat-2")
    snapshots = run_traced(spec, HEAT_TRACE_SPEC)

    keys = [(s.tick, s.phase) for s in snapshots]
    assert len(keys) == len(set(keys))  # no duplicate (tick, phase) pairs
    assert (0, KernelPhase.PRE_TICK) in keys
    assert (1, KernelPhase.AFTER_BOND_BREAK_PHASE) in keys
    assert (2, KernelPhase.POST_TICK) in keys


def test_deep_investigation_finds_first_response_after_heat_boundary(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    baseline_spec = _spec_with_heat(1, "heat-1")  # bond survives
    contrast_spec = _spec_with_heat(2, "heat-2")  # bond breaks

    target = InvestigationTarget(
        "IT-heat-boundary", "BOUNDARY-heat-1-2", baseline_spec.digest, contrast_spec.digest,
        "target_bond.exists differs at tick 2 (survives vs breaks)", ("heated_cell", "target_bond"), 0, 2,
    )
    interventions = (InterventionRecord("heated_cell", "energy", 1, 2, 0, "SET_ONCE"),)

    outcome = investigate(journal, target, HEAT_TRACE_SPEC, baseline_spec, contrast_spec, "heated_cell", interventions)

    # while heated_cell.energy still holds exactly its assigned value (tick 0,
    # and tick 1's PRE_TICK before the bond-break phase runs), the difference
    # is the intervention itself or its still-unchanged persistence -- never
    # mistaken for a response.
    persisted = [e for e in outcome.chain.events if e.role == "heated_cell" and e.field == "energy"
                and (e.tick, e.phase) in ((0, KernelPhase.PRE_TICK), (0, KernelPhase.AFTER_BOND_BREAK_PHASE),
                                          (1, KernelPhase.PRE_TICK))]
    assert len(persisted) == 3
    assert all(e.origin in ("DIRECT_INTERVENTION", "INTERVENTION_PERSISTED") for e in persisted)

    # once the bond-break phase actually runs at tick 1, the same field is A's own doing
    endogenous = next(e for e in outcome.chain.events
                      if e.role == "heated_cell" and e.field == "energy"
                      and (e.tick, e.phase) == (1, KernelPhase.AFTER_BOND_BREAK_PHASE))
    assert endogenous.origin == "ENDOGENOUS_RESPONSE"

    # the first genuine reaction happens where the bond actually breaks
    assert outcome.chain.first_response is not None
    assert outcome.chain.first_response.tick == 1
    assert outcome.chain.first_response.phase == KernelPhase.AFTER_BOND_BREAK_PHASE

    # every role that diverged got its own mechanism candidate
    candidate_roles = {c.source_role for c in outcome.mechanism_candidates.candidates}
    touched_roles = {e.role for e in outcome.chain.events}
    proposed_roles = {c.candidate_id.rsplit("-", 1)[-1] for c in outcome.mechanism_candidates.candidates}
    assert proposed_roles == touched_roles
    assert candidate_roles == {"heated_cell"}  # source_role is fixed per investigation

    # candidates start unresolved -- no candidate is claimed true from observation alone
    assert all(c.status == "NEEDS_INTERVENTION" for c in outcome.mechanism_candidates.candidates)

    # a follow-up proposal can be drafted for one candidate without running anything
    target_bond_candidate = next(c for c in outcome.mechanism_candidates.candidates
                                 if c.source_role == "heated_cell" and
                                 any(step.role == "target_bond" for step in c.path))
    proposal = FollowupExperimentProposal(
        "FE-1", target_bond_candidate.candidate_id, "target_bond", "stored_energy", "clamp",
        "bond survives if target_bond.stored_energy is the mechanism", "bond still breaks regardless",
    )
    recorded = propose_followup_experiment(journal, proposal)
    assert recorded is proposal

    journal.close()
    assert verify_journal(journal.path)["valid"] is True

    entries = read_journal(journal.path)
    event_types = [e.event_type for e in entries]
    assert event_types == [
        "investigation_target_sealed", "divergence_chain_recorded",
        "mechanism_candidates_proposed", "followup_experiment_proposed",
    ]


def test_investigate_rejects_spec_mismatched_with_sealed_target(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    baseline_spec = _spec_with_heat(1, "heat-1")
    contrast_spec = _spec_with_heat(2, "heat-2")
    wrong_spec = _spec_with_heat(3, "heat-3")

    target = InvestigationTarget(
        "IT-1", "SRC-1", baseline_spec.digest, contrast_spec.digest, "outcome differs", ("heated_cell",), 0, 2,
    )
    with pytest.raises(ValueError, match="does not match the sealed investigation target"):
        investigate(journal, target, HEAT_TRACE_SPEC, wrong_spec, contrast_spec, "heated_cell")


def test_investigation_target_rejects_identical_baseline_and_contrast() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    with pytest.raises(ValueError, match="must be different specs"):
        InvestigationTarget("IT-1", "SRC-1", spec.digest, spec.digest, "outcome", ("role",), 0, 2)
