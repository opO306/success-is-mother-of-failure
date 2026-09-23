"""G7.3b: Blind Hypothesis Space Generation.

B, holding only the blind interface of a world (`BlindWorldDescriptor` plus
its `BlindControlDescriptor`s/`BlindObservableDescriptor`s), builds its own
competing causal claims, turns them into `InterventionalPrediction`s over
its own experiment plan, lets G6d pick a discriminating experiment, and that
experiment is runnable by G7.3a's blind executor.

Sections:
  1. vocabulary (G7.3b-1): claim validation and per-kind semantics
  2. type boundary: the generator/materializer refuse real specs/manifests
  3. serialized leakage: no real world/variable/revision string anywhere
  4. determinism, including across PYTHONHASHSEED values
  5. competition: every question holds >= 2 claims, every pair separable
  6. G6d ranking + G7.3a execution of the selected experiment
  7. evaluator-side expressibility (harness only -- uses the manifest)
  8. transitive dependency boundary
  9. budgets and provider coverage
 10. G7.3b-4 temporal observation semantics (horizon is part of the experiment)

Not tested here, on purpose: updating hypotheses from results, repeating
the loop, FinalDiscoverySeal wiring (G7.3c); scoring against ground truth
(G7.4).
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_execution import BlindCandidateSpec
from engine.deterministic.blind_hypothesis import (
    BLIND_HYPOTHESIS_KINDS, CONDITIONAL, DELAYED, DIRECT, DISJUNCTIVE, ENUMERATED_KINDS, GRAMMAR_DIGEST, INVERTED,
    MEDIATED, NO_EFFECT,
    BlindCausalClaim, predict_target, simulate_claim,
)
from engine.deterministic.blind_hypothesis_generator import (
    BlindHypothesisGenerator, BlindHypothesisSpace, BlindQuestion, HypothesisSpaceBudgetExceeded,
)
from engine.deterministic.blind_execution import BlindCheckpoint, BlindRun
from engine.deterministic.blind_prediction_materializer import (
    BlindPredictionMaterializer, InterventionalPredictionProvider, check_prediction_at_horizon,
    inseparable_pairs, observation_horizon,
)
from engine.deterministic.research_observable_prediction import ObservablePrediction
from engine.deterministic.research_world import WorldCompatibilityError
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.causal_hypothesis import CausalHypothesisSet
from engine.deterministic.experiment_designer import rank_discriminating_candidates, select_next_experiment
from engine.deterministic.exploration_space import ExplorationBudgetExceeded, ExplorationCandidate
from engine.deterministic.interventional_prediction import InterventionalPrediction
from engine.deterministic.synthetic_spec import SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "engine" / "deterministic"


def _spec(world_id: str, revision: str, variables: tuple[str, ...], controls: tuple[str, ...],
          observables: tuple[str, ...], ticks: int) -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id=world_id, world_revision=revision, variables=variables,
        initial_values=tuple((v, False) for v in variables), clamps=(),
        public_controls=controls, public_observables=observables, ticks=ticks,
    )


def _s01() -> SyntheticWorldSpec:
    return _spec("WORLD-S01", "R-7F93C2", ("x1", "x3"), ("x1",), ("x1", "x3"), 1)


def _s02(ticks: int = 1) -> SyntheticWorldSpec:
    return _spec("WORLD-S02", "R-A18D40", ("x1", "x2", "x3"), ("x1", "x2"), ("x1", "x2", "x3"), ticks)


def _s03(ticks: int = 2) -> SyntheticWorldSpec:
    return _spec("WORLD-S03", "R-51E8B7", ("x1", "x2", "x3"), ("x1", "x2"), ("x1", "x2", "x3"), ticks)


ALL_WORLDS = (_s01, _s02, _s03)


def _interface(spec: SyntheticWorldSpec, seed: int = 0):
    """Harness side: the only place a real spec is touched. Returns the
    B-facing interface triple and, separately, the evaluator-only manifest."""
    descriptor, manifest = make_blind_session(spec, seed)
    return (descriptor, control_descriptors(spec, seed), observable_descriptors(spec, seed)), manifest


def _materialized(interface):
    world, controls, observables = interface
    space = BlindHypothesisGenerator().generate(world, controls, observables)
    materializer = BlindPredictionMaterializer()
    plan = materializer.plan(world, controls, observables)
    sets = tuple(materializer.materialize(q, world, controls, observables, plan) for q in space.questions)
    return space, plan, sets


# ---------------------------------------------------------------------------
# 1. Vocabulary (G7.3b-1).
# ---------------------------------------------------------------------------

def test_vocabulary_is_exactly_the_declared_kinds() -> None:
    """Grammar v2: six enumerated kinds, plus DELAYED -- statable, but only
    ever reached by noticing (blind_noticing.py), never enumerated."""
    assert ENUMERATED_KINDS == (NO_EFFECT, DIRECT, INVERTED, CONDITIONAL, DISJUNCTIVE, MEDIATED)
    assert BLIND_HYPOTHESIS_KINDS == ENUMERATED_KINDS + (DELAYED,)


def test_grammar_v2_is_frozen() -> None:
    """Frozen before any holdout world exists. A change here means the
    grammar changed: mint a new version deliberately."""
    assert GRAMMAR_DIGEST == "dedc4e8aceb17f33eff525fc9966a95d36417112a75302984e9bfbc22c2af356"


def test_generator_never_enumerates_delayed_claims() -> None:
    interface, _m = _interface(_s03())
    space = BlindHypothesisGenerator().generate(*interface)
    assert all(claim.kind != DELAYED for q in space.questions for claim in q.claims)


def test_grammar_v1_claim_ids_are_unchanged_by_v2() -> None:
    """Only DELAYED carries a lag, so every v1 claim keeps its id."""
    assert BlindCausalClaim(DIRECT, "T", ("A",)).claim_id == "BH-e474138464470504"


@pytest.mark.parametrize("kwargs", [
    dict(kind=DELAYED, target_variable_id="T", cause_variable_ids=("A",)),           # lag 1 is DIRECT
    dict(kind=DELAYED, target_variable_id="T", cause_variable_ids=("A",), lag=0),
    dict(kind=DIRECT, target_variable_id="T", cause_variable_ids=("A",), lag=2),     # only DELAYED has a lag
])
def test_delayed_claim_lag_rules(kwargs) -> None:
    with pytest.raises(ValueError):
        BlindCausalClaim(**kwargs)


def test_delayed_claim_keeps_initial_value_until_its_lag() -> None:
    claim = BlindCausalClaim(DELAYED, "T", ("A",), lag=2)
    assert [s["T"] for s in simulate_claim(claim, {"A": True}, 3)] == [False, False, True, True]
    assert [s["T"] for s in simulate_claim(claim, {"A": False}, 3, initial={"T": True})] == [True, True, False, False]


def test_observed_initial_value_replaces_the_baseline_assumption() -> None:
    assert predict_target(BlindCausalClaim(NO_EFFECT, "T"), {}, 1, initial={"T": True}) is True
    both = BlindCausalClaim(CONDITIONAL, "T", ("A", "B"))
    assert predict_target(both, {"A": True}, 1) is False                      # B assumed False
    assert predict_target(both, {"A": True}, 1, initial={"B": True}) is True  # B seen True


@pytest.mark.parametrize("kwargs", [
    dict(kind="CAUSES", target_variable_id="T"),                                   # unknown kind
    dict(kind=DIRECT, target_variable_id="T"),                                     # missing cause
    dict(kind=NO_EFFECT, target_variable_id="T", cause_variable_ids=("A",)),       # extra cause
    dict(kind=CONDITIONAL, target_variable_id="T", cause_variable_ids=("B", "A")),  # unsorted pair
    dict(kind=CONDITIONAL, target_variable_id="T", cause_variable_ids=("A", "A")),  # repeated
    dict(kind=DIRECT, target_variable_id="T", cause_variable_ids=("T",)),          # self-cause
    dict(kind=MEDIATED, target_variable_id="T", cause_variable_ids=("A",)),        # no mediator
    dict(kind=DIRECT, target_variable_id="T", cause_variable_ids=("A",), mediator_variable_id="M"),
    dict(kind=MEDIATED, target_variable_id="T", cause_variable_ids=("A",), mediator_variable_id="A"),
])
def test_claim_rejects_malformed_statements(kwargs) -> None:
    with pytest.raises(ValueError):
        BlindCausalClaim(**kwargs)


@pytest.mark.parametrize("claim,pinned,expected", [
    (BlindCausalClaim(NO_EFFECT, "T"), {"A": True}, False),
    (BlindCausalClaim(DIRECT, "T", ("A",)), {"A": True}, True),
    (BlindCausalClaim(DIRECT, "T", ("A",)), {}, False),                     # free cause -> baseline
    (BlindCausalClaim(INVERTED, "T", ("A",)), {"A": False}, True),
    (BlindCausalClaim(CONDITIONAL, "T", ("A", "B")), {"A": True, "B": False}, False),
    (BlindCausalClaim(CONDITIONAL, "T", ("A", "B")), {"A": True, "B": True}, True),
    (BlindCausalClaim(DISJUNCTIVE, "T", ("A", "B")), {"A": False, "B": True}, True),
    (BlindCausalClaim(MEDIATED, "T", ("A",), "M"), {"A": True}, True),       # free mediator follows cause
    (BlindCausalClaim(MEDIATED, "T", ("A",), "M"), {"A": True, "M": False}, False),  # pinned mediator blocks
    (BlindCausalClaim(DIRECT, "T", ("A",)), {"A": True, "T": False}, False),  # pinned target wins
])
def test_predict_target_semantics(claim, pinned, expected) -> None:
    """Every case above is one step, except the free-mediator case, which is
    checked at horizon 2 (it needs two ticks -- see section 10)."""
    horizon = 2 if claim.kind == MEDIATED and "M" not in pinned else 1
    assert predict_target(claim, pinned, horizon) is expected


def test_baseline_is_a_parameter_not_a_hidden_constant() -> None:
    assert predict_target(BlindCausalClaim(NO_EFFECT, "T"), {}, 1, baseline=True) is True


# ---------------------------------------------------------------------------
# 2. Type boundary.
# ---------------------------------------------------------------------------

FORBIDDEN_FIELD_NAMES = {"real_world_id", "real_world_revision", "ground_truth_id", "rule", "fingerprint",
                         "source", "manifest", "real_spec"}


@pytest.mark.parametrize("cls", [BlindCausalClaim, BlindQuestion, BlindHypothesisSpace])
def test_blind_hypothesis_types_have_no_real_identity_fields(cls) -> None:
    assert not {f.name for f in dataclasses.fields(cls)} & FORBIDDEN_FIELD_NAMES


def test_generator_and_materializer_signatures_name_only_blind_types() -> None:
    allowed = {"BlindWorldDescriptor", "tuple[BlindControlDescriptor, ...]",
               "tuple[BlindObservableDescriptor, ...]", "BlindQuestion", "BlindExperimentPlan",
               "Mapping[str, bool] | None"}  # G8: B's observed tick-0 values, alias ids only
    for function in (BlindHypothesisGenerator.generate, BlindPredictionMaterializer.plan,
                     BlindPredictionMaterializer.materialize):
        for name, parameter in inspect.signature(function).parameters.items():
            if name == "self":
                continue
            assert parameter.annotation in allowed, (function.__qualname__, name, parameter.annotation)


def test_generator_rejects_a_real_spec_in_place_of_the_descriptor() -> None:
    (_world, controls, observables), _manifest = _interface(_s02())
    with pytest.raises(TypeError):
        BlindHypothesisGenerator().generate(_s02(), controls, observables)


def test_generator_rejects_the_manifest() -> None:
    (world, controls, _observables), manifest = _interface(_s02())
    with pytest.raises(TypeError):
        BlindHypothesisGenerator().generate(world, controls, manifest)


def test_generator_rejects_descriptors_from_a_different_world() -> None:
    (world, _c, _o), _m = _interface(_s02())
    (_w, other_controls, other_observables), _m2 = _interface(_s01())
    with pytest.raises(ValueError):
        BlindHypothesisGenerator().generate(world, other_controls, other_observables)


# ---------------------------------------------------------------------------
# 3. Serialized leakage (Test 2 of the G7.3b skeleton).
# ---------------------------------------------------------------------------

SECRET_VALUES = (
    "WORLD-S01", "WORLD-S02", "WORLD-S03", "R-7F93C2", "R-A18D40", "R-51E8B7",
    "GT-2", "GT-3", "GT-M1", "RULE_S01", "RULE_S02", "RULE_S03",
)


@pytest.mark.parametrize("make_spec", ALL_WORLDS)
def test_space_hypotheses_and_plan_carry_no_real_identity(make_spec) -> None:
    spec = make_spec()
    interface, _manifest = _interface(spec)
    space, plan, sets = _materialized(interface)
    serialized = json.dumps({
        "space": space.canonical(),
        "sets": [s.canonical() for s in sets],
        "plan": [c.canonical() for c in plan.candidates] + [s.canonical() for s in plan.compiled_specs.values()],
        "statements": [h.statement for s in sets for h in s.hypotheses],
    })
    assert spec.digest not in serialized
    for secret in SECRET_VALUES:
        assert secret not in serialized
    for real_name in spec.variables:
        assert f'"{real_name}"' not in serialized
        assert f" {real_name} " not in serialized


# ---------------------------------------------------------------------------
# 4. Determinism (Test 3).
# ---------------------------------------------------------------------------

def test_same_interface_gives_the_same_space_and_predictions() -> None:
    interface, _m = _interface(_s02())
    first, first_plan, first_sets = _materialized(interface)
    second, second_plan, second_sets = _materialized(interface)
    assert first.digest == second.digest
    assert [c.candidate_id for c in first_plan.candidates] == [c.candidate_id for c in second_plan.candidates]
    assert [s.digest for s in first_sets] == [s.digest for s in second_sets]


_HASHSEED_PROBE = """
from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_hypothesis_generator import BlindHypothesisGenerator
from engine.deterministic.blind_prediction_materializer import BlindPredictionMaterializer
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
v = ("x1", "x2", "x3")
spec = SyntheticWorldSpec(world_id="WORLD-S02", world_revision="R-A18D40", variables=v,
    initial_values=tuple((x, False) for x in v), clamps=(), public_controls=("x1", "x2"),
    public_observables=v, ticks=1)
w, _ = make_blind_session(spec, 0)
c, o = control_descriptors(spec, 0), observable_descriptors(spec, 0)
space = BlindHypothesisGenerator().generate(w, c, o)
m = BlindPredictionMaterializer()
plan = m.plan(w, c, o)
print(space.digest, *[m.materialize(q, w, c, o, plan).digest for q in space.questions])
"""


def test_space_is_identical_across_python_hash_seeds() -> None:
    """Set/dict iteration order of strings changes with PYTHONHASHSEED; a
    generator that leaned on it would pass an in-process determinism test
    and still differ between two real sessions."""
    outputs = []
    for seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
        result = subprocess.run([sys.executable, "-c", _HASHSEED_PROBE], capture_output=True, text=True,
                                env=env, cwd=ROOT, check=True)
        outputs.append(result.stdout.strip())
    assert outputs[0] == outputs[1]
    assert outputs[0]


def test_alias_permutation_changes_names_but_not_structure() -> None:
    def shape(seed: int):
        space, _plan, _sets = _materialized(_interface(_s02(), seed)[0])
        return sorted(sorted(claim.kind for claim in q.claims) for q in space.questions)
    assert shape(0) == shape(1) == shape(2)
    assert _materialized(_interface(_s02(), 0)[0])[0].digest != _materialized(_interface(_s02(), 1)[0])[0].digest


# ---------------------------------------------------------------------------
# 5. Competition (Test 4).
# ---------------------------------------------------------------------------

def _s02_two_ticks() -> SyntheticWorldSpec:
    return _s02(ticks=2)


def _s03_one_tick() -> SyntheticWorldSpec:
    return _s03(ticks=1)


@pytest.mark.parametrize("make_spec", [_s01, _s02_two_ticks, _s03])
def test_with_two_tick_horizons_every_competing_pair_is_separable(make_spec) -> None:
    """Each question holds >= 2 claims, and once the harness allows a
    2-tick observation no two of them predict the same thing on every
    planned experiment -- G6d never carries a tie it cannot break."""
    interface, _m = _interface(make_spec())
    space, plan, sets = _materialized(interface)
    assert space.questions
    for hypothesis_set in sets:
        assert len(hypothesis_set.hypotheses) >= 2
        assert inseparable_pairs(hypothesis_set, plan) == ()


@pytest.mark.parametrize("make_spec", [_s02, _s03_one_tick])
def test_with_only_one_tick_the_only_ties_are_chains_vs_their_last_edge(make_spec) -> None:
    """A 2-step chain c -> m -> t and the single edge m -> t predict the same
    at tick 1 under every intervention; nothing else does. B reports these
    ties from its own predictions -- it does not need the answer to know an
    experiment it cannot run would be required."""
    interface, _m = _interface(make_spec())
    _space, plan, sets = _materialized(interface)
    found = 0
    for hypothesis_set in sets:
        claims = {h.hypothesis_id: h for h in hypothesis_set.hypotheses}
        for a, b in inseparable_pairs(hypothesis_set, plan):
            found += 1
            edge, chain = sorted((claims[a].statement, claims[b].statement), key=lambda st: st.count("->"))
            assert chain.count("->") == 2 and edge.count("->") == 1
            assert chain.split(" -> ")[1:] == edge.split(" -> ")  # same last edge m -> t
    assert found > 0


def test_s02_target_question_holds_every_structural_alternative() -> None:
    interface, manifest = _interface(_s02())
    space, _plan, _sets = _materialized(interface)
    target = manifest.variable_alias["x3"]
    [question] = [q for q in space.questions if q.target_variable_id == target]
    assert sorted(claim.kind for claim in question.claims) == sorted(
        [NO_EFFECT, DIRECT, DIRECT, INVERTED, INVERTED, CONDITIONAL, DISJUNCTIVE, MEDIATED, MEDIATED])


def test_observable_no_control_can_reach_is_recorded_not_silently_dropped() -> None:
    """S01's only control is x1; x1 itself as a target has no other
    pinnable cause, so only NO_EFFECT is statable about it."""
    interface, manifest = _interface(_s01())
    space = BlindHypothesisGenerator().generate(*interface)
    assert space.untestable_observable_ids == (manifest.observable_alias["x1"],)
    assert [q.target_observable_id for q in space.questions] == [manifest.observable_alias["x3"]]


# ---------------------------------------------------------------------------
# 6. G6d ranking and G7.3a execution (Tests 5 and 6).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("make_spec", ALL_WORLDS)
def test_generated_predictions_drive_g6d_to_a_runnable_blind_experiment(make_spec) -> None:
    spec = make_spec()
    interface, manifest = _interface(spec)
    space, plan, sets = _materialized(interface)
    for spec_value in plan.compiled_specs.values():
        assert isinstance(spec_value, BlindCandidateSpec)
        assert not isinstance(spec_value, SyntheticWorldSpec)

    executor = SyntheticBlindAExecutor(spec, manifest)  # harness-assembled, handed in as an AExecutor
    for question, hypothesis_set in zip(space.questions, sets):
        ranked = rank_discriminating_candidates(plan.candidates, plan.compiled_specs,
                                                InterventionalPredictionProvider(hypothesis_set))
        selected = select_next_experiment(ranked, frozenset())
        assert selected is not None and selected.disagreement_pair_count > 0
        assert selected.candidate_id == ranked[0].candidate_id

        result = executor.execute(plan.compiled_specs[selected.candidate_id])
        assert result.status == "success"
        final = result.run.checkpoint_at(observation_horizon(plan.compiled_specs[selected.candidate_id]))
        assert final is not None
        assert isinstance(final.value_of(question.target_observable_id), bool)


def test_every_hypothesis_predicts_every_planned_candidate_at_its_horizon() -> None:
    interface, _m = _interface(_s03())
    _space, plan, sets = _materialized(interface)
    planned = sorted((tuple(sorted(c.control_values)), plan.compiled_specs[c.candidate_id].ticks)
                     for c in plan.candidates)
    for hypothesis_set in sets:
        for hypothesis in hypothesis_set.hypotheses:
            assert all(isinstance(p, InterventionalPrediction) for p in hypothesis.predictions)
            assert sorted((tuple(sorted(p.control_values)), p.prediction.tick)
                          for p in hypothesis.predictions) == planned


def test_plan_leaves_controls_free_and_skips_the_all_free_baseline() -> None:
    interface, _m = _interface(_s02())
    plan = BlindPredictionMaterializer().plan(*interface)
    sizes = sorted(len(c.control_values) for c in plan.candidates)
    assert len(plan.candidates) == 3 ** 2 - 1
    assert sizes.count(1) == 4 and sizes.count(2) == 4 and 0 not in sizes


def test_plan_crosses_every_intervention_with_every_allowed_horizon() -> None:
    interface, _m = _interface(_s03(ticks=2))
    plan = BlindPredictionMaterializer().plan(*interface)
    horizons = [plan.compiled_specs[c.candidate_id].ticks for c in plan.candidates]
    assert len(plan.candidates) == (3 ** 2 - 1) * 2
    assert horizons.count(1) == 8 and horizons.count(2) == 8
    assert len({c.candidate_id for c in plan.candidates}) == len(plan.candidates)


# ---------------------------------------------------------------------------
# 7. Evaluator-side expressibility (harness only -- uses the manifest).
#
# Not a B capability test: B never sees these results in G7.3b. This checks
# that the vocabulary + plan *can* express and single out each world's real
# structure, and records where they cannot.
# ---------------------------------------------------------------------------

def _surviving_statements(spec: SyntheticWorldSpec, real_target: str) -> list[str]:
    interface, manifest = _interface(spec)
    space, plan, sets = _materialized(interface)
    executor = SyntheticBlindAExecutor(spec, manifest)
    runs = {cid: executor.execute(candidate_spec).run for cid, candidate_spec in plan.compiled_specs.items()}
    [index] = [i for i, q in enumerate(space.questions)
               if q.target_variable_id == manifest.variable_alias[real_target]]
    real_name = {alias: real for real, alias in manifest.variable_alias.items()}
    survivors = []
    for hypothesis in sets[index].hypotheses:
        if all(check_prediction_at_horizon(plan.compiled_specs[c.candidate_id], p.prediction, runs[c.candidate_id])
               for c, p in zip(plan.candidates, hypothesis.predictions)):
            survivors.append(" ".join(real_name.get(token, token) for token in hypothesis.statement.split()))
    return survivors


@pytest.mark.parametrize("make_spec,expected", [
    (_s01, ["x1 -> x3"]),
    (_s02, ["x1 AND x2 -> x3"]),
    (_s03, ["x1 -> x2 -> x3"]),
])
def test_exactly_the_real_structure_survives_the_full_plan(make_spec, expected) -> None:
    assert _surviving_statements(make_spec(), "x3") == expected


def test_one_tick_observation_of_a_chain_never_yields_a_wrong_singleton() -> None:
    """Regression (G7.3b-4). This was pinned as a KNOWN LIMIT under the old
    steady-state semantics: WORLD-S03 (x1 -> x2 -> x3) observed only at
    tick 1 left the *wrong* claim "x2 -> x3" surviving alone. Under tick
    semantics both claims predict the same at tick 1, so both must survive
    -- and B must itself report them as a tie no allowed experiment breaks.
    A lone survivor here is a failure again."""
    assert _surviving_statements(_s03(ticks=1), "x3") == ["x2 -> x3", "x1 -> x2 -> x3"]


def test_one_tick_tie_is_visible_to_b_without_the_answer() -> None:
    interface, manifest = _interface(_s03(ticks=1))
    space, plan, sets = _materialized(interface)
    [index] = [i for i, q in enumerate(space.questions) if q.target_variable_id == manifest.variable_alias["x3"]]
    claims = {h.hypothesis_id: h.statement for h in sets[index].hypotheses}
    x1, x2, x3 = (manifest.variable_alias[n] for n in ("x1", "x2", "x3"))
    tied = {frozenset((claims[a], claims[b])) for a, b in inseparable_pairs(sets[index], plan)}
    assert frozenset((f"{x2} -> {x3}", f"{x1} -> {x2} -> {x3}")) in tied


# ---------------------------------------------------------------------------
# 8. Transitive dependency boundary.
# ---------------------------------------------------------------------------

FORBIDDEN_MODULES = {"blind_evaluator", "blind_synthetic_executor", "synthetic_runtime", "synthetic_executor",
                     "environment_kernel", "environment_spec", "probe_world", "blind_probe_evaluator",
                     "synthetic_kernel", "ground_truth_signature"}
B_ENTRYPOINTS = ("blind_hypothesis", "blind_hypothesis_generator", "blind_prediction_materializer",
                 "experiment_designer", "blind_execution")


def _direct_package_imports(module: str) -> set[str]:
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level >= 1 and node.module:
                found.add(node.module.split(".")[0])
            elif node.level >= 1:
                found.update(alias.name for alias in node.names)
            elif node.module and node.module.startswith("engine.deterministic."):
                found.add(node.module.split(".")[2])
            elif node.module and node.module.split(".")[0] == "ground_truth":
                found.add("ground_truth")
            if any(alias.name == "*" for alias in node.names):
                found.add("*")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "ground_truth":
                    found.add("ground_truth")
                elif alias.name.startswith("engine.deterministic."):
                    found.add(alias.name.split(".")[2])
    return found


def _closure(start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        for name in _direct_package_imports(module) if (PACKAGE / f"{module}.py").exists() else ():
            stack.append(name)
    return seen


@pytest.mark.parametrize("entrypoint", B_ENTRYPOINTS)
def test_b_side_transitive_closure_never_reaches_evaluator_or_answer_modules(entrypoint) -> None:
    closure = _closure(entrypoint)
    assert not closure & FORBIDDEN_MODULES, sorted(closure & FORBIDDEN_MODULES)
    assert "ground_truth" not in closure
    assert "*" not in closure


def test_closure_walker_actually_follows_imports() -> None:
    """Guard against a walker that silently finds nothing: the evaluator
    side must be seen reaching the modules the B side is forbidden from."""
    assert "blind_evaluator" in _closure("blind_synthetic_executor")
    assert "synthetic_runtime" in _closure("blind_synthetic_executor")
    assert "causal_hypothesis" in _closure("blind_prediction_materializer")


def test_vocabulary_does_not_depend_on_generator_or_materializer() -> None:
    assert not _direct_package_imports("blind_hypothesis") & {"blind_hypothesis_generator",
                                                               "blind_prediction_materializer"}
    assert "blind_prediction_materializer" not in _direct_package_imports("blind_hypothesis_generator")


# ---------------------------------------------------------------------------
# 9. Budgets and provider coverage.
# ---------------------------------------------------------------------------

def test_hypothesis_budget_raises_instead_of_truncating() -> None:
    interface, _m = _interface(_s02())
    with pytest.raises(HypothesisSpaceBudgetExceeded):
        BlindHypothesisGenerator(max_claims_per_question=8).generate(*interface)


def test_experiment_budget_raises_instead_of_truncating() -> None:
    interface, _m = _interface(_s02())
    with pytest.raises(ExplorationBudgetExceeded):
        BlindPredictionMaterializer(max_candidates=7).plan(*interface)


def test_provider_refuses_a_candidate_a_hypothesis_never_predicted() -> None:
    interface, _m = _interface(_s02())
    _space, plan, sets = _materialized(interface)
    stranger = ExplorationCandidate("BCAND-unplanned", plan.plan_id, (("ALIAS-NOT-A-CONTROL", 1),))
    with pytest.raises(ValueError):
        InterventionalPredictionProvider(sets[0]).predictions_for(stranger, plan.compiled_specs[plan.candidates[0].candidate_id])


def test_materialized_sets_are_ordinary_causal_hypothesis_sets() -> None:
    interface, _m = _interface(_s02())
    _space, _plan, sets = _materialized(interface)
    for hypothesis_set in sets:
        assert isinstance(hypothesis_set, CausalHypothesisSet)
        assert all(h.status == "untested" and h.evidence == () for h in hypothesis_set.hypotheses)


# ---------------------------------------------------------------------------
# 10. G7.3b-4 temporal observation semantics.
# ---------------------------------------------------------------------------

def _x3_question(spec: SyntheticWorldSpec):
    interface, manifest = _interface(spec)
    space, plan, sets = _materialized(interface)
    [index] = [i for i, q in enumerate(space.questions) if q.target_variable_id == manifest.variable_alias["x3"]]
    return manifest, plan, sets[index]


def test_a_change_never_chains_through_two_variables_within_one_tick() -> None:
    chain = BlindCausalClaim(MEDIATED, "T", ("A",), "M")
    trajectory = simulate_claim(chain, {"A": True}, 2)
    assert [(state["M"], state["T"]) for state in trajectory] == [(False, False), (True, False), (True, True)]


def test_tick_zero_is_the_pinned_initial_state() -> None:
    assert predict_target(BlindCausalClaim(INVERTED, "T", ("A",)), {"A": False}, 0) is False
    assert predict_target(BlindCausalClaim(INVERTED, "T", ("A",)), {"A": False}, 1) is True
    assert predict_target(BlindCausalClaim(DIRECT, "T", ("A",)), {"T": True}, 0) is True


def test_predictor_tick_rule_matches_a_out_to_three_ticks() -> None:
    """Off-by-one guard: B's own tick rule and A's tick rule agree, horizon
    by horizon, for S03's real structure (checked evaluator side)."""
    assert _surviving_statements(_s03(ticks=3), "x3") == ["x1 -> x2 -> x3"]


def test_provider_serves_the_prediction_for_the_candidates_own_horizon() -> None:
    manifest, plan, hypothesis_set = _x3_question(_s03(ticks=2))
    x1, x2, x3 = (manifest.variable_alias[n] for n in ("x1", "x2", "x3"))
    [chain] = [h for h in hypothesis_set.hypotheses if h.statement == f"{x1} -> {x2} -> {x3}"]
    x1_only = ((manifest.control_alias["x1"], 1),)
    provider = InterventionalPredictionProvider(hypothesis_set)
    served = {}
    for candidate in plan.candidates:
        if candidate.control_values == x1_only:
            spec = plan.compiled_specs[candidate.candidate_id]
            served[spec.ticks] = provider.predictions_for(candidate, spec)[chain.hypothesis_id]
    assert [(p.tick, p.expected_value) for p in served[1]] == [(1, False)]
    assert [(p.tick, p.expected_value) for p in served[2]] == [(2, True)]


def test_executor_runs_exactly_the_candidates_horizon() -> None:
    spec = _s03(ticks=2)
    interface, manifest = _interface(spec)
    plan = BlindPredictionMaterializer().plan(*interface)
    executor = SyntheticBlindAExecutor(spec, manifest)
    for candidate in plan.candidates:
        candidate_spec = plan.compiled_specs[candidate.candidate_id]
        assert executor.execute(candidate_spec).run.checkpoints[-1].tick == candidate_spec.ticks


def test_executor_refuses_a_horizon_beyond_the_worlds_limit() -> None:
    spec = _s03(ticks=2)
    (world, _c, _o), manifest = _interface(spec)
    too_long = BlindCandidateSpec(world.alias_world_id, "BCAND-long", ((manifest.control_alias["x1"], 1),), ticks=3)
    with pytest.raises(WorldCompatibilityError):
        SyntheticBlindAExecutor(spec, manifest).execute(too_long)


def test_prediction_is_never_compared_across_horizons() -> None:
    spec = BlindCandidateSpec("ALIAS-W", "BCAND-1", (("ALIAS-C", 1),), ticks=1)
    run = BlindRun("ALIAS-W", (BlindCheckpoint(0, (("ALIAS-O", False),)), BlindCheckpoint(1, (("ALIAS-O", True),))))
    assert check_prediction_at_horizon(spec, ObservablePrediction(1, "ALIAS-O", True), run) is True
    with pytest.raises(ValueError):
        check_prediction_at_horizon(spec, ObservablePrediction(2, "ALIAS-O", True), run)
    with pytest.raises(ValueError):
        check_prediction_at_horizon(spec, ObservablePrediction(1, "ALIAS-MISSING", True), run)


def test_a_run_that_ignored_its_horizon_is_refused_not_scored() -> None:
    spec = BlindCandidateSpec("ALIAS-W", "BCAND-1", (("ALIAS-C", 1),), ticks=1)
    overlong = BlindRun("ALIAS-W", tuple(BlindCheckpoint(t, (("ALIAS-O", True),)) for t in range(3)))
    with pytest.raises(ValueError):
        check_prediction_at_horizon(spec, ObservablePrediction(1, "ALIAS-O", True), overlong)


def test_g6d_prefers_the_shorter_horizon_at_equal_discriminating_power() -> None:
    interface, _m = _interface(_s03(ticks=2))
    _space, plan, sets = _materialized(interface)
    for hypothesis_set in sets:
        ranked = rank_discriminating_candidates(plan.candidates, plan.compiled_specs,
                                                InterventionalPredictionProvider(hypothesis_set),
                                                cost=observation_horizon)
        best = ranked[0].disagreement_pair_count
        horizons = [plan.compiled_specs[r.candidate_id].ticks for r in ranked if r.disagreement_pair_count == best]
        assert horizons == sorted(horizons)
        assert 1 in horizons and 2 in horizons  # a real tie existed to be broken


def test_only_the_two_tick_observation_separates_a_chain_from_its_last_edge() -> None:
    """With x1 pinned and x2 free, "x1 -> x2 -> x3" and "x2 -> x3" agree at
    tick 1 and disagree at tick 2 -- so the 2-tick candidates are what makes
    the full plan separable (see the separability test above), even though
    the *total* pair count at each horizon happens to be equal here."""
    manifest, plan, hypothesis_set = _x3_question(_s03(ticks=2))
    x1, x2, x3 = (manifest.variable_alias[n] for n in ("x1", "x2", "x3"))
    ids = {h.statement: h.hypothesis_id for h in hypothesis_set.hypotheses}
    chain, edge = ids[f"{x1} -> {x2} -> {x3}"], ids[f"{x2} -> {x3}"]
    provider = InterventionalPredictionProvider(hypothesis_set)
    x1_only = ((manifest.control_alias["x1"], 1),)
    agrees = {}
    for candidate in plan.candidates:
        if candidate.control_values == x1_only:
            spec = plan.compiled_specs[candidate.candidate_id]
            row = provider.predictions_for(candidate, spec)
            agrees[spec.ticks] = row[chain] == row[edge]
    assert agrees == {1: True, 2: False}
