import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic import (
    HypothesisSetAdapter,
    PrivateTraceWriter,
    RationalWeight,
    build_approved_change_view,
    evaluate_hypothesis_set,
    load_environment_world_spec,
    make_hypothesis_challenge,
    trace_environment_run,
)
import engine.deterministic.hypotheses as hypotheses_module

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"


def _source(tmp_path: Path):
    spec = load_environment_world_spec(EXAMPLE); run_dir = tmp_path / "raw"
    writer = PrivateTraceWriter(run_dir, "raw"); final = trace_environment_run(spec, writer)
    writer.close(spec.digest, final.digest)
    return spec, run_dir


def _make(tmp_path: Path):
    spec, run_dir = _source(tmp_path); view = build_approved_change_view(run_dir, spec, 7)
    challenge = make_hypothesis_challenge(view, spec); adapter = HypothesisSetAdapter()
    claims, hypotheses = adapter.respond(challenge, view, spec)
    return spec, run_dir, view, challenge, adapter, claims, hypotheses


def test_all_enabled_explanations_and_unknown_are_preserved_before_observation(tmp_path: Path) -> None:
    _, _, _, _, _, claims, hypotheses = _make(tmp_path)
    ids = {item.hypothesis_id for item in hypotheses.hypotheses}

    assert {"rule-causal_particle_or_bond", "rule-heat_transfer",
            "rule-water_surface_transfer", "rule-solute_transport",
            "no-physical-change", "missing-variable-needed"} == ids
    assert hypotheses.combination_policy == "nonexclusive"
    assert all(item.weight is None for item in hypotheses.hypotheses)
    assert len(claims.claims) == 6
    assert len(claims.evidence_bridges) == 5


def test_target_observation_supports_refutes_and_leaves_unknown(tmp_path: Path) -> None:
    spec, run_dir, _, challenge, _, claims, hypotheses = _make(tmp_path)
    before = hypotheses.digest
    boundary, resolution = evaluate_hypothesis_set(challenge, claims, hypotheses, run_dir, spec)
    verdicts = {item.hypothesis_id: item.verdict for item in resolution.verdicts}

    assert verdicts["rule-causal_particle_or_bond"] == "supported"
    assert verdicts["rule-heat_transfer"] == "refuted"
    assert verdicts["rule-water_surface_transfer"] == "refuted"
    assert verdicts["rule-solute_transport"] == "refuted"
    assert verdicts["no-physical-change"] == "refuted"
    assert verdicts["missing-variable-needed"] == "underdetermined"
    assert resolution.coverage_success is True
    assert resolution.uncovered_actual_rules == ()
    assert boundary.verified_claim_ids == ("rule-causal_particle_or_bond",)
    assert len(boundary.falsified_claim_ids) == 4
    assert boundary.untested_claim_ids == ("missing-variable-needed",)
    assert hypotheses.digest == before


def test_distinguishing_observations_separate_next_tick_and_structural_unknown(tmp_path: Path) -> None:
    _, _, _, _, _, _, hypotheses = _make(tmp_path)
    by_id = {item.observation_id: item for item in hypotheses.distinguishing_observations}

    assert by_id["observe-target-stage-deltas"].intervention_required is False
    assert "missing-variable-needed" not in by_id["observe-target-stage-deltas"].resolves_hypothesis_ids
    assert by_id["collect-repeated-residuals"].resolves_hypothesis_ids == ("missing-variable-needed",)
    assert by_id["collect-repeated-residuals"].compute_cost_units == 4


def test_numerical_weight_is_optional_and_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence provenance"):
        RationalWeight(1, 2, ())

    weight = RationalWeight(1, 2, ("measured-frequency-study",))
    assert weight.canonical() == {"numerator": 1, "denominator": 2,
                                  "evidence_ids": ["measured-frequency-study"]}


def test_missing_actual_rule_is_reported_as_uncovered(tmp_path: Path) -> None:
    spec, run_dir, _, challenge, _, claims, hypotheses = _make(tmp_path)
    kept_hypotheses = tuple(item for item in hypotheses.hypotheses
                            if item.hypothesis_id != "rule-causal_particle_or_bond")
    kept_observations = tuple(
        replace(item, resolves_hypothesis_ids=tuple(value for value in item.resolves_hypothesis_ids
                                                    if value != "rule-causal_particle_or_bond"))
        for item in hypotheses.distinguishing_observations
    )
    reduced = replace(hypotheses, hypotheses=kept_hypotheses,
                      distinguishing_observations=kept_observations)
    kept_claims = tuple(item for item in claims.claims if item.claim_id != "rule-causal_particle_or_bond")
    kept_bridges = tuple(item for item in claims.evidence_bridges if item.claim_id != "rule-causal_particle_or_bond")
    reduced_claims = replace(claims, claims=kept_claims, evidence_bridges=kept_bridges)

    _, resolution = evaluate_hypothesis_set(challenge, reduced_claims, reduced, run_dir, spec)

    assert resolution.coverage_success is False
    assert resolution.uncovered_actual_rules == ("causal_particle_or_bond",)


def test_hypothesis_generation_is_reproducible(tmp_path: Path) -> None:
    spec, run_dir, view, challenge, adapter, first_claims, first_set = _make(tmp_path)
    second_claims, second_set = adapter.respond(challenge, view, spec)

    assert first_claims == second_claims
    assert first_set == second_set
    assert first_set.digest == second_set.digest


def test_hypothesis_adapter_does_not_call_a_transition_or_forecast() -> None:
    source = inspect.getsource(hypotheses_module)

    assert "step_environment_world" not in source
    assert "run_environment_world" not in source
    assert "forecast_environment_world" not in source
    assert "import random" not in source
