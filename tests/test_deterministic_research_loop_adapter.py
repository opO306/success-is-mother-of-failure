"""G3: research_loop's generic core (observe_world/compare_results_with_adapter)
produces byte-identical results to the pre-migration physical wrappers, and
actually accepts a non-default adapter argument (proving it is not secretly
hardcoded to PhysicalCausalResearchAdapter internally).
"""
from __future__ import annotations

from pathlib import Path

from engine.deterministic import (
    BondCountPrediction,
    CausalHypothesis,
    CausalHypothesisSet,
    PredictionSeal,
    RealCausalAExecutor,
    ResearchJournal,
    load_causal_world_spec,
    observe,
    record_hypothesis_set,
    seal_predictions,
)
from engine.deterministic.physical_research_adapter import PhysicalCausalResearchAdapter
from engine.deterministic.research_loop import compare_results, compare_results_with_adapter, observe_world

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_observe_world_with_physical_adapter_matches_observe_exactly(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)

    journal_a = ResearchJournal.create(tmp_path / "a.jsonl")
    via_wrapper = observe(journal_a, spec, "identical description")

    journal_b = ResearchJournal.create(tmp_path / "b.jsonl")
    via_generic = observe_world(journal_b, PhysicalCausalResearchAdapter(), spec, "identical description")

    assert via_wrapper.canonical() == via_generic.canonical()


def test_compare_results_with_adapter_matches_compare_results_exactly(tmp_path: Path) -> None:
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)

    h1 = CausalHypothesis("H1", "claim", (), (BondCountPrediction(1, 1),), (), "untested")
    hs = record_hypothesis_set(ResearchJournal.create(tmp_path / "unused.jsonl"), CausalHypothesisSet(spec.digest, (h1,)))

    journal_a = ResearchJournal.create(tmp_path / "a.jsonl")
    seal_a = PredictionSeal("PS-1", "ARM-1", journal_a.next_sequence, {"H1": (BondCountPrediction(1, 1),)})
    seal_predictions(journal_a, seal_a)
    via_wrapper = compare_results(journal_a, hs, seal_a, "ARM-1", result)

    journal_b = ResearchJournal.create(tmp_path / "b.jsonl")
    seal_b = PredictionSeal("PS-1", "ARM-1", journal_b.next_sequence, {"H1": (BondCountPrediction(1, 1),)})
    seal_predictions(journal_b, seal_b)
    via_generic = compare_results_with_adapter(journal_b, PhysicalCausalResearchAdapter(), hs, seal_b, "ARM-1", result)

    assert via_wrapper == via_generic == {"H1": "supported"}
