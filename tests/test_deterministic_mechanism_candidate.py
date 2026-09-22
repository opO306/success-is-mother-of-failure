import pytest

from engine.deterministic import KernelPhase
from engine.deterministic.divergence_analysis import DivergenceEvent
from engine.deterministic.mechanism_candidate import (
    FollowupExperimentProposal,
    MechanismCandidate,
    MechanismCandidateSet,
    MechanismStep,
    propose_mechanism_candidates,
)


def _event(tick: int, phase: KernelPhase, role: str, field: str, origin: str = "ENDOGENOUS_RESPONSE") -> DivergenceEvent:
    return DivergenceEvent(tick, phase, role, field, "a", "b", "STATE", origin)


def test_propose_mechanism_candidates_groups_one_candidate_per_role() -> None:
    events = (
        _event(1, KernelPhase.AFTER_BOND_BREAK_PHASE, "heat", "energy"),
        _event(1, KernelPhase.AFTER_BOND_BREAK_PHASE, "bond", "exists"),
        _event(2, KernelPhase.POST_TICK, "bond", "stored_energy"),
    )
    candidate_set = propose_mechanism_candidates("IT-1", events, "heat")

    roles = {c.candidate_id.rsplit("-", 1)[-1] for c in candidate_set.candidates}
    assert roles == {"heat", "bond"}
    bond_candidate = next(c for c in candidate_set.candidates if c.candidate_id.endswith("bond"))
    assert [s.field for s in bond_candidate.path] == ["exists", "stored_energy"]
    assert all(c.status == "NEEDS_INTERVENTION" for c in candidate_set.candidates)
    assert all(c.source_role == "heat" for c in candidate_set.candidates)


def test_propose_mechanism_candidates_rejects_empty_events() -> None:
    with pytest.raises(ValueError, match="empty divergence chain"):
        propose_mechanism_candidates("IT-1", (), "heat")


def test_mechanism_candidate_set_rejects_duplicate_ids() -> None:
    c1 = MechanismCandidate("C1", "IT-1", "heat", (MechanismStep("bond", "exists"),))
    c2 = MechanismCandidate("C1", "IT-1", "heat", c1.path)
    with pytest.raises(ValueError, match="unique"):
        MechanismCandidateSet("IT-1", (c1, c2))


def test_followup_experiment_proposal_rejects_unsupported_operation() -> None:
    with pytest.raises(ValueError, match="unsupported intervention operation"):
        FollowupExperimentProposal("FE-1", "C1", "bond", "stored_energy", "teleport", "true", "false")
