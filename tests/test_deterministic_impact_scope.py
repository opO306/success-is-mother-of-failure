import inspect
from dataclasses import replace
from pathlib import Path

from engine.deterministic import (
    ImpactScopeAdapter,
    PrivateTraceWriter,
    build_approved_change_view,
    evaluate_impact_scope,
    load_environment_world_spec,
    make_impact_scope_challenge,
    predict_next_impact_scope,
    trace_environment_run,
)
import engine.deterministic.impact_scope as impact_module

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _source(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); run_dir = tmp_path / "raw"
    writer = PrivateTraceWriter(run_dir, "raw"); final = trace_environment_run(spec, writer)
    writer.close(spec.digest, final.digest)
    return spec, run_dir


def test_scope_predicts_tick_eight_without_seeing_tick_eight(tmp_path: Path) -> None:
    spec, run_dir = _source(tmp_path); view = build_approved_change_view(run_dir, spec, 7)
    challenge = make_impact_scope_challenge(view, spec)
    claims, prediction = ImpactScopeAdapter().respond(challenge, view, spec)
    boundary, impact = evaluate_impact_scope(challenge, claims, prediction, run_dir, spec)

    assert all(event.tick <= 7 for event in view.events)
    assert "A_records_after_target_tick" in view.hidden_content
    assert prediction.source_tick == 7 and prediction.target_tick == 8
    assert boundary.complete_match is True
    assert impact.complete_coverage is True
    assert impact.missed_locations == ()
    assert impact.missed_rules == ()


def test_scope_records_excess_separately_instead_of_hiding_it(tmp_path: Path) -> None:
    spec, run_dir = _source(tmp_path); view = build_approved_change_view(run_dir, spec, 7)
    challenge = make_impact_scope_challenge(view, spec)
    claims, prediction = ImpactScopeAdapter().respond(challenge, view, spec)
    boundary, impact = evaluate_impact_scope(challenge, claims, prediction, run_dir, spec)

    assert prediction.coverage_cells == 263
    assert len(impact.actual_locations) == 4
    assert len(impact.excess_locations) == 259
    assert impact.actual_rules == ("causal_particle_or_bond",)
    assert impact.excess_rules == ("heat_transfer", "solute_transport", "water_surface_transfer")
    assert boundary.findings[0]["excess_location_count"] == 259


def test_deliberately_removed_actual_location_is_falsified(tmp_path: Path) -> None:
    spec, run_dir = _source(tmp_path); view = build_approved_change_view(run_dir, spec, 7)
    challenge = make_impact_scope_challenge(view, spec)
    claims, prediction = ImpactScopeAdapter().respond(challenge, view, spec)
    _, actual = evaluate_impact_scope(challenge, claims, prediction, run_dir, spec)
    removed = actual.actual_locations[0]
    bad = replace(prediction, predicted_locations=tuple(x for x in prediction.predicted_locations if x != removed))
    boundary, impact = evaluate_impact_scope(challenge, claims, bad, run_dir, spec)

    assert impact.missed_locations == (removed,)
    assert boundary.falsified_claim_ids == ("next-impact-scope",)


def test_scope_prediction_is_reproducible(tmp_path: Path) -> None:
    spec, run_dir = _source(tmp_path); view = build_approved_change_view(run_dir, spec, 7)

    first = predict_next_impact_scope(view, spec); second = predict_next_impact_scope(view, spec)

    assert first == second
    assert first.digest == second.digest
    assert first.coverage_cells < first.full_grid_cells


def test_scope_adapter_does_not_call_a_transition_or_forecast() -> None:
    source = inspect.getsource(impact_module)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "forecast_environment_world" not in source
    assert "import random" not in source
