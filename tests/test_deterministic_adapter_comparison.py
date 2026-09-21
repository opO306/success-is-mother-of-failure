from pathlib import Path

from engine.deterministic import (
    PrivateTraceWriter,
    compare_cognitive_and_change_graph,
    load_environment_world_spec,
    trace_environment_run,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _source(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); run_dir = tmp_path / "raw"
    writer = PrivateTraceWriter(run_dir, "raw"); final = trace_environment_run(spec, writer)
    writer.close(spec.digest, final.digest)
    return spec, run_dir


def test_two_distinct_adapters_answer_same_external_queries(tmp_path: Path) -> None:
    spec, source = _source(tmp_path)
    comparison, exchanges = compare_cognitive_and_change_graph(spec, source, 8)

    assert comparison.query_ids == ("local-source", "blocked-shortest", "blocked-two",
                                    "blocked-three", "wrapped-neighbor")
    assert comparison.cognitive_map.adapter_id == "sparse-cognitive-map"
    assert comparison.change_graph.adapter_id == "approved-delta-change-graph"
    assert comparison.cognitive_map.complete_match is True
    assert comparison.change_graph.complete_match is True
    assert comparison.normalized_answers_equal is True
    assert len(exchanges) == 2


def test_comparison_keeps_cost_dimensions_separate(tmp_path: Path) -> None:
    spec, source = _source(tmp_path)
    comparison, _ = compare_cognitive_and_change_graph(spec, source, 8)
    canonical = comparison.canonical()

    assert "no aggregate score" in comparison.ranking_policy
    assert comparison.cognitive_map.input_bytes > 0
    assert comparison.change_graph.input_bytes > 0
    assert comparison.cognitive_map.representation_bytes > 0
    assert comparison.change_graph.representation_bytes > 0
    assert comparison.cognitive_map.construction_nanoseconds > 0
    assert comparison.change_graph.construction_nanoseconds > 0
    assert canonical.get("winner") is None


def test_comparison_preserves_different_structural_metrics(tmp_path: Path) -> None:
    spec, source = _source(tmp_path)
    comparison, _ = compare_cognitive_and_change_graph(spec, source, 8)

    assert comparison.cognitive_map.structural_counts == {"full_cells": 1024, "stored_cells": 23}
    assert comparison.change_graph.structural_counts == {"delta_operations": 30, "event_nodes": 64}
