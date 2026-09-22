import copy
import json
from pathlib import Path

import pytest

from engine.deterministic import (
    BondCountPrediction,
    CausalExperimentArm,
    CausalExperimentPortfolio,
    CausalHypothesis,
    CausalHypothesisSet,
    CausalWorldSpec,
    DomainEvidence,
    EvidenceReference,
    ExactConstraint,
    HypothesisDomainLink,
    HypothesisEdge,
    IntegerRangeConstraint,
    PredictionSeal,
    RealCausalAExecutor,
    ResearchDomain,
    ResearchJournal,
    add_hypothesis_edge,
    design_experiments,
    execute_through_a,
    link_hypothesis_domain,
    load_causal_world_spec,
    observe,
    rebuild_hypothesis_graph,
    rebuild_memory_index,
    rebuild_research_state,
    record_domain_evidence,
    record_hypothesis_set,
    register_domain,
    seal_predictions,
    verify_journal,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def _spec_with_energy(energy: int, world_id: str) -> CausalWorldSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["particles"][0]["kinetic_energy"] = energy
    raw["particles"][1]["kinetic_energy"] = energy
    raw["world_id"] = world_id
    return CausalWorldSpec.from_mapping(raw)


def _evidence_ref(digest: str) -> tuple[EvidenceReference, ...]:
    return (EvidenceReference("E1", "leaves_open", digest, "initial spec"),)


def test_full_b02_scenario_head_on_bond_hypothesis_specialized(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(journal_path)
    executor = RealCausalAExecutor()

    base_spec = load_causal_world_spec(EXAMPLE)
    observation = observe(journal, base_spec, "two kind-0 particles approach head-on")

    # H1: "head-on collision bonds" -- domain D1 is equal-energy, energy 1..3.
    h1 = CausalHypothesis(
        "H1", "head-on collision leads to a bond by tick 1", ("head_on", "equal_energy"),
        (BondCountPrediction(1, 1),), _evidence_ref(base_spec.digest), "untested",
    )
    hypothesis_set = CausalHypothesisSet(base_spec.digest, (h1,))
    record_hypothesis_set(journal, hypothesis_set)

    # H1's domain is split into two sub-domains along the axis that actually
    # matters here (energy magnitude): energy=1 sits below
    # minimum_collision_energy=4 and never bonds, energy=2/3 clear it and bond.
    # These are different points of condition-space, not conflicting evidence
    # about the same one -- so evidence from the two domains combines into
    # `conditional`, with no `ContradictionRecord` (that is reserved for two
    # evidence items disagreeing about the *same* domain; see the dedicated
    # contradiction test below).
    d1_low = ResearchDomain("D1-low", (
        ExactConstraint("causal.collision.energy_relation", "equal"),
        IntegerRangeConstraint("causal.collision.left_energy", 1, 1),
    ))
    d1_high = ResearchDomain("D1-high", (
        ExactConstraint("causal.collision.energy_relation", "equal"),
        IntegerRangeConstraint("causal.collision.left_energy", 2, 3),
    ))
    register_domain(journal, d1_low)
    register_domain(journal, d1_high)
    link_hypothesis_domain(journal, HypothesisDomainLink("H1", "D1-low", "applicability"))
    link_hypothesis_domain(journal, HypothesisDomainLink("H1", "D1-high", "applicability"))

    existing_evidence: list[DomainEvidence] = []
    for index, (energy, expect_bond, domain_id) in enumerate(
        ((1, False, "D1-low"), (2, True, "D1-high"), (3, True, "D1-high")),
    ):
        spec = _spec_with_energy(energy, f"equal-{energy}")
        arm = CausalExperimentArm(f"ARM-{index}", "energy", spec, spec, ("H1",))
        portfolio = CausalExperimentPortfolio(f"P-{index}", ("H1",), (arm,), {"energy": True})
        design_experiments(journal, portfolio)

        predicted_bonds = 1  # H1 predicts a bond regardless of the energy sub-range
        seal = PredictionSeal(f"PS-{index}", arm.arm_id, journal.next_sequence,
                              {"H1": (BondCountPrediction(1, 1),)})
        seal_predictions(journal, seal)

        result = execute_through_a(journal, executor, arm.arm_id, arm.submitted_spec)
        assert result.status == "success"
        actual_bonds = next(cp.bonds for cp in result.run.checkpoints if cp.tick == 1)
        assert (actual_bonds == 1) == expect_bond

        relation = "supports" if actual_bonds == predicted_bonds else "contradicts"
        evidence = DomainEvidence(
            f"DE-{index}", "H1", domain_id, arm.arm_id, seal.seal_id, relation, (observation.observation_id,),
            arm.intended_spec.digest, result.executed_spec_digest,
        )
        recorded, contradiction = record_domain_evidence(journal, evidence, tuple(existing_evidence))
        assert contradiction is None  # different domains disagreeing is not a same-domain clash
        existing_evidence.append(recorded)

    # H1 now has a contradiction in D1-low and support in D1-high: conditional.
    state = rebuild_research_state(journal_path)
    assert state.hypothesis_evidence_status["H1"] == "conditional"
    assert state.domain_status["D1-low"] == "tested"
    assert state.domain_status["D1-high"] == "tested"

    # H2: narrower hypothesis restricted to energy >= 2 within the same relation.
    h2 = CausalHypothesis(
        "H2", "equal-energy head-on collision with enough energy bonds by tick 1",
        ("head_on", "equal_energy", "energy>=2"), (BondCountPrediction(1, 1),),
        _evidence_ref(base_spec.digest), "untested",
    )
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (h2,)))
    d2 = ResearchDomain("D2", (
        ExactConstraint("causal.collision.energy_relation", "equal"),
        IntegerRangeConstraint("causal.collision.left_energy", 2, 3),
    ))
    register_domain(journal, d2)
    link_hypothesis_domain(journal, HypothesisDomainLink("H2", "D2", "applicability"))

    edge = HypothesisEdge("HE-1", "H1", "H2", "specialized_into", ("DE-1", "DE-2"))
    add_hypothesis_edge(journal, edge)

    final_state = rebuild_hypothesis_graph(journal_path)
    assert final_state.children_of("H1")[0].target_hypothesis_id == "H2"
    assert final_state.parents_of("H2")[0].source_hypothesis_id == "H1"

    memory = rebuild_memory_index(journal_path)
    assert memory.hypotheses_in_domain("D1-high") == ("H1",)
    assert set(memory.evidence_for_hypothesis("H1")) == set(existing_evidence)

    state_before_close = rebuild_research_state(journal_path)
    journal.close()

    assert verify_journal(journal_path)["valid"] is True

    reopened_state = rebuild_research_state(journal_path)
    reopened_graph = rebuild_hypothesis_graph(journal_path)
    reopened_memory = rebuild_memory_index(journal_path)

    assert reopened_state == state_before_close
    assert reopened_graph.digest == final_state.digest
    assert reopened_memory.digest == memory.digest
    assert reopened_state.hypothesis_evidence_status["H1"] == "conditional"
    assert reopened_state.hypothesis_evidence_status["H2"] == "untested"
    assert reopened_state.hypothesis_lifecycle_status["H1"] == "active"


def test_same_domain_conflicting_evidence_creates_contradiction_record(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    base_spec = load_causal_world_spec(EXAMPLE)
    observation = observe(journal, base_spec, "baseline")

    h1 = CausalHypothesis("H1", "claim", ("d",), (BondCountPrediction(1, 1),), (), "untested")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (h1,)))
    domain = ResearchDomain("D1", (ExactConstraint("causal.collision.energy_relation", "equal"),))
    register_domain(journal, domain)

    e1 = DomainEvidence("DE-1", "H1", "D1", "ARM-1", "PS-1", "supports", (observation.observation_id,), "sd", "sd")
    recorded1, contradiction1 = record_domain_evidence(journal, e1, ())
    assert contradiction1 is None

    e2 = DomainEvidence("DE-2", "H1", "D1", "ARM-2", "PS-2", "contradicts", (observation.observation_id,), "sd", "sd")
    recorded2, contradiction2 = record_domain_evidence(journal, e2, (recorded1,))

    assert contradiction2 is not None
    assert contradiction2.supporting_evidence_ids == ("DE-1",)
    assert contradiction2.contradicting_evidence_ids == ("DE-2",)

    state = rebuild_research_state(journal.path)
    assert (h1.hypothesis_id, contradiction2.contradiction_id) in state.unresolved_contradictions


def test_domain_registration_rejects_unregistered_axis(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    bad_domain = ResearchDomain("D-bad", (ExactConstraint("nonsense.axis", 1),))
    with pytest.raises(ValueError, match="unregistered research axis"):
        register_domain(journal, bad_domain)
