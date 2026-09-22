"""G6c-3: SyntheticResearchAdapter -- same shape as PhysicalCausalResearchAdapter,
and (the real point) run_research_exploration actually accepts it: the same
generic Broad Research core that runs physical A also runs a synthetic
world, with zero changes to broad_explorer.py or research_loop.py.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.deterministic.broad_explorer import run_research_exploration
from engine.deterministic.exploration_space import ExplorationPlan, SweepDimension
from engine.deterministic.research_observable_prediction import ObservablePrediction
from engine.deterministic.research_journal import ResearchJournal
from engine.deterministic.research_loop import observe_world
from engine.deterministic.research_prediction import FunctionalPredictionProvider, StaticPredictionProvider
from engine.deterministic.research_world import (
    InvalidControlValueError,
    UnsupportedPredictionError,
    WorldCompatibilityError,
)
from engine.deterministic.synthetic_adapter import (
    SYNTHETIC_AXIS_REGISTRY,
    SyntheticControlDefinition,
    SyntheticResearchAdapter,
)
from engine.deterministic.synthetic_executor import SyntheticAExecutor
from engine.deterministic.synthetic_spec import SyntheticClamp, SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]

CTRL_X1 = SyntheticControlDefinition("CTRL-X1", "axis.synthetic.x1", "x1")
CTRL_X2 = SyntheticControlDefinition("CTRL-X2", "axis.synthetic.x2", "x2")


def _s01_spec() -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S01", world_revision="R-7F93C2", variables=("x1", "x3"),
        initial_values=(("x1", False), ("x3", False)), clamps=(),
        public_controls=("x1",), public_observables=("x1", "x3"), ticks=1,
    )


def _s02_spec() -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S02", world_revision="R-A18D40", variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", False), ("x3", False)), clamps=(),
        public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=1,
    )


def test_adapter_id_is_stable() -> None:
    assert SyntheticResearchAdapter().adapter_id == "synthetic-research-v1"


def test_assert_compatible_rejects_a_causal_world_spec(tmp_path: Path) -> None:
    from engine.deterministic import load_causal_world_spec

    physical_spec = load_causal_world_spec(ROOT / "worlds" / "deterministic_bond_cycle_v1.json")
    with pytest.raises(WorldCompatibilityError):
        SyntheticResearchAdapter().assert_compatible(physical_spec)


def test_apply_control_1_clamps_on() -> None:
    adapter = SyntheticResearchAdapter()
    spec = adapter.apply_control(_s01_spec(), CTRL_X1, 1)
    assert spec.clamp_for("x1") == "ON"


def test_apply_control_0_clamps_off() -> None:
    adapter = SyntheticResearchAdapter()
    spec = adapter.apply_control(_s01_spec(), CTRL_X1, 0)
    assert spec.clamp_for("x1") == "OFF"


def test_apply_control_none_clears_the_clamp() -> None:
    adapter = SyntheticResearchAdapter()
    clamped = adapter.apply_control(_s01_spec(), CTRL_X1, 1)
    freed = adapter.apply_control(clamped, CTRL_X1, None)
    assert freed.clamp_for("x1") == "FREE"


def test_apply_control_rejects_a_non_integer_value() -> None:
    adapter = SyntheticResearchAdapter()
    with pytest.raises(InvalidControlValueError):
        adapter.apply_control(_s01_spec(), CTRL_X1, "not-an-int")


def test_apply_control_rejects_a_bool_value_even_though_bool_equals_int() -> None:
    """SweepDimension itself rejects bool values outright (exploration_space.py),
    so apply_control must too -- accepting True/False silently would let a
    sweep author write a control axis SweepDimension can never actually carry."""
    adapter = SyntheticResearchAdapter()
    with pytest.raises(InvalidControlValueError):
        adapter.apply_control(_s01_spec(), CTRL_X1, True)


def test_apply_control_rejects_a_control_targeting_a_non_public_variable() -> None:
    """G6c-3.1.D: CTRL_X2 targets x2, which _s01_spec never declares a
    public control -- this is a wiring mistake (the caller built a control
    for the wrong world), not an illegal value a candidate tried, so it
    must raise WorldCompatibilityError rather than eventually surfacing as
    a bare ValueError from SyntheticWorldSpec.__post_init__ that
    broad_explorer would swallow as a CandidateCompilationFailure."""
    adapter = SyntheticResearchAdapter()
    with pytest.raises(WorldCompatibilityError, match="x2"):
        adapter.apply_control(_s01_spec(), CTRL_X2, 1)


def test_initial_observation_reflects_clamps() -> None:
    adapter = SyntheticResearchAdapter()
    clamped = adapter.apply_control(_s01_spec(), CTRL_X1, 1)
    observation = adapter.initial_observation(clamped)
    assert observation.observables["x1"] is True


def test_evaluate_prediction_match() -> None:
    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    spec = adapter.apply_control(_s01_spec(), CTRL_X1, 1)
    spec = adapter.validate(spec)
    result = executor.execute(spec)
    evaluation = adapter.evaluate_prediction(ObservablePrediction(1, "x3", True), result)
    assert evaluation.status == "match"


def test_evaluate_prediction_mismatch() -> None:
    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    spec = adapter.apply_control(_s01_spec(), CTRL_X1, 1)
    spec = adapter.validate(spec)
    result = executor.execute(spec)
    evaluation = adapter.evaluate_prediction(ObservablePrediction(1, "x3", False), result)
    assert evaluation.status == "mismatch"


def test_evaluate_prediction_rejects_unsupported_prediction_type() -> None:
    from engine.deterministic import BondCountPrediction

    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    spec = adapter.validate(_s01_spec())
    result = executor.execute(spec)
    with pytest.raises(UnsupportedPredictionError):
        adapter.evaluate_prediction(BondCountPrediction(1, 1), result)


# ---------------------------------------------------------------------------
# The real point: run_research_exploration works for a synthetic world with
# zero changes to broad_explorer.py's own code.
# ---------------------------------------------------------------------------

def test_run_research_exploration_sweeps_a_synthetic_world(tmp_path: Path) -> None:
    base_spec = _s01_spec()
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    observation = observe_world(journal, adapter, base_spec, "sweeping x1 on a synthetic world")

    plan = ExplorationPlan("P-s01-sweep", base_spec.digest, ("H1",),
                           (SweepDimension(CTRL_X1.control_id, (0, 1)),), "full_factorial", 10)

    def predictions_for(candidate, compiled_spec):
        (_, value), = candidate.control_values
        return {"H1": (ObservablePrediction(1, "x3", bool(value)),)}

    outcome = run_research_exploration(
        journal, executor, adapter, FunctionalPredictionProvider(predictions_for),
        plan, base_spec, {CTRL_X1.control_id: CTRL_X1}, observation.observation_id,
        axis_registry=SYNTHETIC_AXIS_REGISTRY,
    )

    assert outcome.compilation_failures == ()
    assert len(outcome.evidence) == 2
    assert all(item.relation == "supports" for item in outcome.evidence)


def test_run_research_exploration_full_factorial_over_s02(tmp_path: Path) -> None:
    base_spec = _s02_spec()
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    observation = observe_world(journal, adapter, base_spec, "full factorial over x1,x2")

    plan = ExplorationPlan(
        "P-s02-full", base_spec.digest, ("H1",),
        (SweepDimension(CTRL_X1.control_id, (0, 1)), SweepDimension(CTRL_X2.control_id, (0, 1))),
        "full_factorial", 10,
    )

    def predictions_for(candidate, compiled_spec):
        values = dict(candidate.control_values)
        expected = bool(values[CTRL_X1.control_id]) and bool(values[CTRL_X2.control_id])
        return {"H1": (ObservablePrediction(1, "x3", expected),)}

    outcome = run_research_exploration(
        journal, executor, adapter, FunctionalPredictionProvider(predictions_for),
        plan, base_spec, {CTRL_X1.control_id: CTRL_X1, CTRL_X2.control_id: CTRL_X2}, observation.observation_id,
        axis_registry=SYNTHETIC_AXIS_REGISTRY,
    )

    assert outcome.compilation_failures == ()
    assert len(outcome.evidence) == 4  # full 2x2 factorial
    assert all(item.relation == "supports" for item in outcome.evidence)


def test_run_research_exploration_never_swallows_synthetic_world_compatibility_error(tmp_path: Path) -> None:
    """The physical-A version of this guarantee is already pinned
    (test_deterministic_broad_explorer_adapter.py); confirms the same holds
    when the mismatched adapter/executor pair is the synthetic one."""
    base_spec = _s01_spec()
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = SyntheticAExecutor()
    adapter = SyntheticResearchAdapter()
    observation = observe_world(journal, adapter, base_spec, "wrong control type")

    plan = ExplorationPlan("P-s01-wrong-control", base_spec.digest, ("H1",),
                           (SweepDimension("some-physical-control-id", (0, 2)),), "full_factorial", 10)

    class _WrongControl:
        control_id = "some-physical-control-id"
        research_axis = "causal.heat.energy"

        def canonical(self):
            return {}

    with pytest.raises(WorldCompatibilityError):
        run_research_exploration(
            journal, executor, adapter, StaticPredictionProvider({"H1": (ObservablePrediction(1, "x3", True),)}),
            plan, base_spec, {"some-physical-control-id": _WrongControl()}, observation.observation_id,
        )


# ---------------------------------------------------------------------------
# Independence from ground_truth/, and no leaking answer-key variable names.
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


def test_synthetic_adapter_does_not_import_ground_truth() -> None:
    path = ROOT / "engine" / "deterministic" / "synthetic_adapter.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name == "ground_truth" or name.startswith("ground_truth.") for name in imported)


def test_no_answer_revealing_names_in_b_facing_synthetic_world_data() -> None:
    """B never sees engine source code or docstrings -- it sees a spec's
    canonical() form (world_id, world_revision, variable names, control ids)
    and whatever a control definition's own fields say. None of that
    B-facing *data* may spell out what a variable or world is for:
    direct/conditional/mediator, or names like source_active/mediator_active/
    gate_enabled that ground_truth/'s own modules use for the same roles.
    (Source comments explaining this rule, like this docstring, are not
    B-facing data and are exempt -- that's why this checks canonical()/field
    values, not file text.)

    world_revision itself is exactly the field G6c-3.1 replaced rule_id
    with, specifically so no selector-shaped B-facing string would exist at
    all -- this check would have caught rule_id="RULE-S01" too, since
    "mediator" is not literally in it, but a hidden-rule *selector* sitting
    in B's own research subject was the deeper problem world_revision's
    opacity (a token with no interpretable structure) fixes.
    """
    forbidden = ("direct", "conditional", "mediator", "source_active", "mediator_active",
                "gate_enabled", "conditional_source")

    b_facing_strings = [
        *_s01_spec().canonical().get("variables", []),
        _s01_spec().canonical()["world_id"],
        _s01_spec().canonical()["world_revision"],
        *_s02_spec().canonical().get("variables", []),
        _s02_spec().canonical()["world_id"],
        _s02_spec().canonical()["world_revision"],
        CTRL_X1.control_id, CTRL_X1.research_axis, CTRL_X1.variable_id,
        CTRL_X2.control_id, CTRL_X2.research_axis, CTRL_X2.variable_id,
    ]
    lowered = " ".join(b_facing_strings).lower()
    hits = [word for word in forbidden if word in lowered]
    assert hits == [], f"B-facing synthetic world data leaks answer-revealing name(s): {hits}"
