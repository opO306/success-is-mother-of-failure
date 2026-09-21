"""Parallel, non-ranking comparison of Cognitive Map and Change Graph candidates."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .change_graph import (
    ChangeGraphAdapter,
    build_change_graph,
    evaluate_change_graph_claims,
    make_change_graph_challenge,
)
from .cognitive_map import (
    CognitiveMapAdapter,
    build_cognitive_map,
    evaluate_cognitive_map_claims,
    make_cognitive_map_challenge,
)
from .environment_kernel import run_environment_world
from .environment_spec import EnvironmentWorldSpec
from .trace_view_broker import build_approved_change_view


def _bytes(value: object) -> int:
    if hasattr(value, "canonical"): value = value.canonical()
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def common_query_suite(solute_kinds: int) -> tuple[dict[str, object], ...]:
    return (
        {"query_id": "local-source", "kind": "local_state", "point": [4, 4], "solute_kinds": solute_kinds},
        {"query_id": "blocked-shortest", "kind": "shortest_path", "start": [20, 20], "goal": [21, 20]},
        {"query_id": "blocked-two", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 2},
        {"query_id": "blocked-three", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 3},
        {"query_id": "wrapped-neighbor", "kind": "shortest_path", "start": [0, 0], "goal": [31, 0]},
    )


def _outcomes(claims) -> dict[str, object]:
    result = {}
    for claim in claims.claims:
        answer = claim.payload.get("answer")
        if claim.claim_kind == "shortest_path" and isinstance(answer, dict):
            result[claim.claim_id] = {"steps": answer.get("steps")}
        else:
            result[claim.claim_id] = answer
    return result


@dataclass(frozen=True)
class AdapterComparisonMetrics:
    adapter_id: str
    input_bytes: int
    representation_bytes: int
    construction_nanoseconds: int
    structural_counts: dict[str, int]
    verified_claims: int
    falsified_claims: int
    untested_claims: int
    complete_match: bool

    def canonical(self) -> dict[str, object]:
        return {"adapter_id": self.adapter_id, "complete_match": self.complete_match,
                "construction_nanoseconds": self.construction_nanoseconds,
                "falsified_claims": self.falsified_claims, "input_bytes": self.input_bytes,
                "representation_bytes": self.representation_bytes,
                "structural_counts": self.structural_counts, "untested_claims": self.untested_claims,
                "verified_claims": self.verified_claims}


@dataclass(frozen=True)
class AdapterComparison:
    task_id: str
    query_ids: tuple[str, ...]
    cognitive_map: AdapterComparisonMetrics
    change_graph: AdapterComparisonMetrics
    normalized_answers_equal: bool
    ranking_policy: str

    def canonical(self) -> dict[str, object]:
        return {"change_graph": self.change_graph.canonical(), "cognitive_map": self.cognitive_map.canonical(),
                "format": "model-neutral-adapter-comparison-v1",
                "normalized_answers_equal": self.normalized_answers_equal,
                "query_ids": list(self.query_ids), "ranking_policy": self.ranking_policy,
                "task_id": self.task_id}


def compare_cognitive_and_change_graph(
    spec: EnvironmentWorldSpec, source_trace: Path, target_tick: int,
):
    if target_tick != spec.causal_world.ticks:
        raise ValueError("comparison v1 requires the committed final tick")
    exact_state = run_environment_world(spec).final_state
    view = build_approved_change_view(source_trace, spec, target_tick)
    graph = build_change_graph(view)
    if graph.reconstructed_state_digest != exact_state.digest:
        raise AssertionError("approved trace and exact A final state differ")
    queries = common_query_suite(spec.solute_kinds)

    cognitive = CognitiveMapAdapter()
    cognitive_challenge = make_cognitive_map_challenge(spec, queries, exact_state)
    started = time.perf_counter_ns(); cognitive_claims = cognitive.respond(cognitive_challenge, spec, exact_state)
    cognitive_ns = time.perf_counter_ns() - started
    cognitive_eval = evaluate_cognitive_map_claims(cognitive_challenge, cognitive_claims, spec, exact_state)
    cognitive_map = build_cognitive_map(spec, exact_state)

    change = ChangeGraphAdapter()
    change_challenge = make_change_graph_challenge(view, queries)
    started = time.perf_counter_ns(); change_claims = change.respond(change_challenge, view)
    change_ns = time.perf_counter_ns() - started
    change_eval = evaluate_change_graph_claims(change_challenge, change_claims, source_trace, spec)

    cognitive_metrics = AdapterComparisonMetrics(
        cognitive.manifest.adapter_id, _bytes(exact_state), _bytes(cognitive_map), cognitive_ns,
        {"full_cells": cognitive_map.full_cell_count, "stored_cells": cognitive_map.stored_cell_count},
        len(cognitive_eval.verified_claim_ids), len(cognitive_eval.falsified_claim_ids),
        len(cognitive_eval.untested_claim_ids), cognitive_eval.complete_match,
    )
    change_metrics = AdapterComparisonMetrics(
        change.manifest.adapter_id, _bytes(view), _bytes(graph), change_ns,
        {"delta_operations": graph.delta_operation_count, "event_nodes": len(graph.nodes)},
        len(change_eval.verified_claim_ids), len(change_eval.falsified_claim_ids),
        len(change_eval.untested_claim_ids), change_eval.complete_match,
    )
    comparison = AdapterComparison(
        f"{spec.causal_world.world_id}:tick-{target_tick}:shared-query-v1",
        tuple(query["query_id"] for query in queries), cognitive_metrics, change_metrics,
        _outcomes(cognitive_claims) == _outcomes(change_claims),
        "no aggregate score; preserve correctness, input, storage, structure, and time separately",
    )
    return comparison, ((cognitive, cognitive_challenge, cognitive_claims, cognitive_eval),
                        (change, change_challenge, change_claims, change_eval))
