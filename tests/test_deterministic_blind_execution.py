"""G7.3a: Blind Execution Substrate -- B can run G6d's experiment selector
without ever holding a real `SyntheticWorldSpec`, real spec digest, or real
run digest.

This Gate does not do autonomous discovery (G7.3b/c) or hypothesis
generation -- it only proves the *execution boundary* itself is blind-safe:
a candidate built purely from alias data (`BlindCandidateSpec`) satisfies
`ResearchWorldSpec` well enough for `rank_discriminating_candidates` to use
it, and running that candidate through `SyntheticBlindAExecutor` returns an
`ExecutionResult` whose `run` (a `BlindRun`) and `executed_spec_digest`
never touch a real digest or a real variable name.

Sections:
  1. BlindCandidateSpec/BlindRun satisfy ResearchWorldSpec/ResearchRun
  2. end-to-end blind execution (alias controls in, alias observables out)
     matches what the same intervention would show on the real spec
  3. G6d integration -- rank_discriminating_candidates works over
     BlindCandidateSpec compiled_specs without ever seeing a real spec
  4. data leakage (serialized ExecutionResult/BlindRun never carries a real
     digest, real world/variable name, or real fingerprint)
  5. dependency boundary (blind_execution.py -- B-facing -- never imports
     blind_evaluator/blind_synthetic_executor/ground_truth/synthetic_runtime)
  6. deliberate mutation (four scenarios from the G7.3a spec)

What this file does NOT test, on purpose (see CURRENT_STATE.md's G7.3a
scope note): autonomous hypothesis generation, the full discovery loop,
FinalDiscoverySeal wiring, or ground-truth scoring. Those are G7.3b/c/G7.4.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import make_blind_session
from engine.deterministic.blind_execution import BlindCandidateSpec, BlindCheckpoint, BlindRun
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.causal_executor import ExecutionResult
from engine.deterministic.experiment_designer import rank_discriminating_candidates
from engine.deterministic.exploration_space import ExplorationCandidate
from engine.deterministic.research_prediction import FunctionalPredictionProvider
from engine.deterministic.research_observable_prediction import ObservablePrediction
from engine.deterministic.research_world import ResearchRun, ResearchWorldSpec, WorldCompatibilityError
from engine.deterministic.synthetic_spec import SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]


def _s02_real_spec() -> SyntheticWorldSpec:
    """RULE_S02: x3 := x1 AND x2 -- see synthetic_kernel.py. x2 is both a
    public control and a public observable, matching the alias-identity
    fixture already used in test_deterministic_blind_session.py."""
    return SyntheticWorldSpec(
        world_id="WORLD-S02", world_revision="R-A18D40",
        variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", False), ("x3", False)),
        clamps=(), public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=1,
    )


def _blind_session():
    real_spec = _s02_real_spec()
    descriptor, manifest = make_blind_session(real_spec, seed=0)
    return real_spec, descriptor, manifest


# ---------------------------------------------------------------------------
# 1. Protocol satisfaction.
# ---------------------------------------------------------------------------

def test_blind_candidate_spec_satisfies_research_world_spec() -> None:
    spec = BlindCandidateSpec("ALIAS-WORLD", "CAND-1", (("ALIAS-CTRL-1", 1),), ticks=1)
    assert isinstance(spec, ResearchWorldSpec)
    assert spec.world_id == "ALIAS-WORLD"
    assert isinstance(spec.digest, str) and spec.digest


def test_blind_run_satisfies_research_run() -> None:
    run = BlindRun("ALIAS-WORLD", (BlindCheckpoint(0, (("ALIAS-OBS-1", True),)),))
    assert isinstance(run, ResearchRun)
    assert isinstance(run.digest, str) and run.digest


def test_blind_candidate_spec_digest_never_equals_a_real_spec_digest() -> None:
    real_spec, descriptor, _manifest = _blind_session()
    candidate = BlindCandidateSpec(descriptor.alias_world_id, "CAND-1", (), ticks=1)
    assert candidate.digest != real_spec.digest


def test_blind_candidate_spec_world_id_field_is_the_only_world_reference() -> None:
    """world_id *is* the alias -- there is no separate real_world_id field
    to accidentally leave populated."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(BlindCandidateSpec)}
    assert "world_id" in field_names
    assert "real_world_id" not in field_names
    assert "alias_world_id" not in field_names  # world_id itself holds the alias


# ---------------------------------------------------------------------------
# 2. End-to-end blind execution matches the real intervention.
# ---------------------------------------------------------------------------

def test_blind_execution_and_gate_matches_real_rule() -> None:
    """RULE_S02 is x3 := x1 AND x2. Setting both alias controls ON must
    show x3 = True through the alias observable, exactly as the real rule
    predicts -- proving the alias translation round-trips correctly, not
    just that it doesn't crash."""
    real_spec, descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)

    candidate = BlindCandidateSpec(
        descriptor.alias_world_id, "CAND-11",
        ((manifest.control_alias["x1"], 1), (manifest.control_alias["x2"], 1)), ticks=1,
    )
    result = executor.execute(candidate)
    assert result.status == "success"
    checkpoint = result.run.checkpoint_at(1)
    assert checkpoint is not None
    assert checkpoint.value_of(manifest.observable_alias["x3"]) is True


def test_blind_execution_gate_off_matches_real_rule() -> None:
    real_spec, descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)

    candidate = BlindCandidateSpec(
        descriptor.alias_world_id, "CAND-10",
        ((manifest.control_alias["x1"], 1), (manifest.control_alias["x2"], 0)), ticks=1,
    )
    result = executor.execute(candidate)
    checkpoint = result.run.checkpoint_at(1)
    assert checkpoint.value_of(manifest.observable_alias["x3"]) is False


def test_blind_executor_rejects_a_candidate_for_a_different_alias_world() -> None:
    real_spec, _descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)
    wrong_world_candidate = BlindCandidateSpec("ALIAS-WRONG-WORLD", "CAND-1", (), ticks=1)
    with pytest.raises(WorldCompatibilityError):
        executor.execute(wrong_world_candidate)


def test_blind_executor_rejects_an_unbound_alias_control() -> None:
    real_spec, descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)
    candidate = BlindCandidateSpec(descriptor.alias_world_id, "CAND-1",
                                   (("ALIAS-DOES-NOT-EXIST", 1),), ticks=1)
    with pytest.raises(WorldCompatibilityError):
        executor.execute(candidate)


def test_blind_executor_rejects_a_real_synthetic_world_spec() -> None:
    """The wiring mistake this Gate exists to prevent: handing the blind
    executor a real spec instead of a BlindCandidateSpec."""
    real_spec, _descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)
    with pytest.raises(WorldCompatibilityError):
        executor.execute(real_spec)


# ---------------------------------------------------------------------------
# 3. G6d integration: rank_discriminating_candidates over blind specs only.
# ---------------------------------------------------------------------------

def test_g6d_ranks_candidates_using_only_blind_candidate_specs() -> None:
    """The exact scenario G7.3a exists to close: compiled_specs never holds
    a real SyntheticWorldSpec, only BlindCandidateSpec -- and ranking still
    works, using the same H-always/H-gated competing-hypotheses shape as
    test_deterministic_experiment_designer.py."""
    real_spec, descriptor, manifest = _blind_session()
    x1c, x2c = manifest.control_alias["x1"], manifest.control_alias["x2"]
    x3o = manifest.observable_alias["x3"]

    def _candidate(candidate_id: str, x1: int, x2: int) -> ExplorationCandidate:
        return ExplorationCandidate(candidate_id, "P-blind", ((x1c, x1), (x2c, x2)))

    candidates = (_candidate("E-00", 0, 0), _candidate("E-01", 0, 1),
                 _candidate("E-10", 1, 0), _candidate("E-11", 1, 1))
    compiled_specs: dict[str, ResearchWorldSpec] = {
        c.candidate_id: BlindCandidateSpec(descriptor.alias_world_id, c.candidate_id, c.control_values, ticks=1)
        for c in candidates
    }
    # None of compiled_specs' values is (or contains) the real spec.
    for spec in compiled_specs.values():
        assert not isinstance(spec, SyntheticWorldSpec)

    def _predictions_for(candidate: ExplorationCandidate, spec) -> dict[str, tuple[object, ...]]:
        values = dict(candidate.control_values)
        x1, x2 = bool(values[x1c]), bool(values[x2c])
        always = ObservablePrediction(1, x3o, x1)             # H-always: x3 just copies x1
        gated = ObservablePrediction(1, x3o, x1 and x2)        # H-gated: x3 needs x1 AND x2
        return {"H-always": (always,), "H-gated": (gated,)}

    ranked = rank_discriminating_candidates(candidates, compiled_specs, FunctionalPredictionProvider(_predictions_for))
    by_id = {item.candidate_id: item for item in ranked}
    assert by_id["E-10"].disagreement_pair_count == 1  # x1=1,x2=0: always=True, gated=False
    assert ranked[0].candidate_id == "E-10"


# ---------------------------------------------------------------------------
# 4. Serialized-data leakage.
# ---------------------------------------------------------------------------

SECRET_VALUES = (
    "WORLD-S01", "WORLD-S02", "WORLD-S03",
    "R-7F93C2", "R-A18D40", "R-51E8B7",
    "GT-2", "GT-3", "GT-M1",
)


def test_execution_result_serialization_has_no_real_digests_or_names() -> None:
    real_spec, descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)
    candidate = BlindCandidateSpec(
        descriptor.alias_world_id, "CAND-11",
        ((manifest.control_alias["x1"], 1), (manifest.control_alias["x2"], 1)), ticks=1,
    )
    result = executor.execute(candidate)
    serialized = json.dumps({"result": result.canonical(), "run": result.run.canonical()})

    assert real_spec.digest not in serialized
    assert result.run.digest != real_spec.canonical().get("world_revision")
    for secret in SECRET_VALUES:
        assert secret not in serialized
    for real_name in ("x1", "x2", "x3"):
        assert f'"{real_name}"' not in serialized


def test_execution_result_executed_spec_digest_is_the_blind_digest() -> None:
    real_spec, descriptor, manifest = _blind_session()
    executor = SyntheticBlindAExecutor(real_spec, manifest)
    candidate = BlindCandidateSpec(descriptor.alias_world_id, "CAND-1", (), ticks=1)
    result = executor.execute(candidate)
    assert result.executed_spec_digest == candidate.digest
    assert result.executed_spec_digest != real_spec.digest


def test_execution_result_run_digest_is_never_the_real_run_digest() -> None:
    from engine.deterministic.synthetic_executor import SyntheticAExecutor
    real_spec, descriptor, manifest = _blind_session()
    real_result = SyntheticAExecutor().execute(real_spec)

    executor = SyntheticBlindAExecutor(real_spec, manifest)
    candidate = BlindCandidateSpec(descriptor.alias_world_id, "CAND-1", (), ticks=1)
    blind_result = executor.execute(candidate)

    assert blind_result.run.digest != real_result.run.digest


# ---------------------------------------------------------------------------
# 5. Dependency boundary.
# ---------------------------------------------------------------------------

def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


FORBIDDEN_FOR_B_FACING = {
    "ground_truth", "engine.deterministic.synthetic_runtime", ".synthetic_runtime", "synthetic_runtime",
    "engine.deterministic.blind_evaluator", ".blind_evaluator", "blind_evaluator",
    "engine.deterministic.blind_synthetic_executor", ".blind_synthetic_executor", "blind_synthetic_executor",
}


def test_blind_execution_module_does_not_import_forbidden_modules() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_execution.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name in FORBIDDEN_FOR_B_FACING or name.startswith("ground_truth.") for name in imported)


def test_blind_execution_module_has_no_wildcard_imports() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_execution.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    has_star = any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
                  for node in ast.walk(tree))
    assert not has_star


def test_blind_synthetic_executor_is_the_only_module_allowed_evaluator_access() -> None:
    """Sanity check on the intended shape, not a boundary test on
    blind_execution.py itself: blind_synthetic_executor.py DOES import
    blind_evaluator/synthetic_executor/synthetic_spec (it is evaluator-only
    by design) -- confirms that's true, so the "forbidden for B-facing"
    list above isn't accidentally checking the wrong file."""
    path = ROOT / "engine" / "deterministic" / "blind_synthetic_executor.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert any(name in {"engine.deterministic.blind_evaluator", ".blind_evaluator", "blind_evaluator"}
              for name in imported)


# ---------------------------------------------------------------------------
# 6. Deliberate mutation (four scenarios from the G7.3a spec).
# ---------------------------------------------------------------------------
#
# Not permanent test code -- performed by hand against the working tree
# during this Gate's implementation session (temporarily breaking each
# invariant, confirming the relevant test above fails, then reverting), per
# RULES.md's checker-defect-injection requirement:
#
#   A. Passing a real SyntheticWorldSpec instead of a BlindCandidateSpec to
#      rank_discriminating_candidates' compiled_specs -- caught by
#      test_g6d_ranks_candidates_using_only_blind_candidate_specs' own
#      isinstance assertion and, independently, by
#      test_blind_executor_rejects_a_real_synthetic_world_spec.
#   B. SyntheticBlindAExecutor returning the real executed_spec_digest/
#      run_digest unchanged -- caught by
#      test_execution_result_executed_spec_digest_is_the_blind_digest and
#      test_execution_result_run_digest_is_never_the_real_run_digest.
#   C. rank_discriminating_candidates-driven selection ignoring the ranking
#      and always picking the first candidate -- caught by
#      test_g6d_ranks_candidates_using_only_blind_candidate_specs'
#      disagreement_pair_count/ranked[0] assertions (this is
#      experiment_designer.py's own existing logic, re-exercised here
#      through the blind substrate rather than mutated again in this file).
#   D. A hypothesis-elimination updater that fails to remove a mismatched
#      hypothesis -- out of scope for G7.3a (no hypothesis-space or
#      elimination logic exists yet; that is G7.3b/c). See
#      CURRENT_STATE.md's G7.3a entry for what was verified in this session.
