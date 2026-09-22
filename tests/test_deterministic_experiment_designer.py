"""G6d: rank_discriminating_candidates/select_next_experiment choose the
next experiment from hypothesis disagreement alone -- never from
ground_truth/ or synthetic_runtime.py's hidden rule. These tests build
competing hypotheses by hand (the way a human researcher's guesses would
look) and confirm the ranking prefers candidates that actually separate
them, without ever checking which guess turns out to be correct -- that
question belongs to G7, not here.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.deterministic.exploration_space import ExplorationCandidate
from engine.deterministic.experiment_designer import (
    DiscriminatingCandidate,
    rank_discriminating_candidates,
    select_next_experiment,
)
from engine.deterministic.research_observable_prediction import ObservablePrediction
from engine.deterministic.research_prediction import FunctionalPredictionProvider
from engine.deterministic.research_world import ResearchWorldSpec
from engine.deterministic.synthetic_spec import SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]


def _s02_spec() -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S02", world_revision="R-A18D40", variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", False), ("x3", False)), clamps=(),
        public_controls=("x1", "x2"), public_observables=("x1", "x2", "x3"), ticks=1,
    )


def _candidate(candidate_id: str, x1: bool, x2: bool) -> ExplorationCandidate:
    return ExplorationCandidate(candidate_id, "P-designer", (("CTRL-X1", x1), ("CTRL-X2", x2)))


def _compiled_specs() -> dict[str, ResearchWorldSpec]:
    """Candidates only ever need a compiled spec to be handed to the
    prediction provider -- this module never inspects the spec itself, so
    a single shared spec per candidate id is enough (its digest is not
    used as a lookup key anywhere in experiment_designer.py)."""
    return {
        "E-00": _s02_spec(), "E-01": _s02_spec(), "E-10": _s02_spec(), "E-11": _s02_spec(),
    }


# ---------------------------------------------------------------------------
# Two hand-built competing hypotheses over WORLD-S02, exactly as a human
# researcher's guesses would look: "H-always" (x1 unconditionally sets x3)
# vs "H-gated" (x1's effect on x3 depends on x2). Neither is asserted to be
# correct here -- only that a candidate where they disagree ranks higher
# than one where they agree.
# ---------------------------------------------------------------------------

def _predictions_for(candidate: ExplorationCandidate, spec) -> dict[str, tuple[object, ...]]:
    values = dict(candidate.control_values)
    x1 = bool(values["CTRL-X1"])
    x2 = bool(values["CTRL-X2"])
    always = ObservablePrediction(1, "x3", x1)              # H-always: x3 just copies x1
    gated = ObservablePrediction(1, "x3", x1 and x2)         # H-gated: x3 needs x1 AND x2
    return {"H-always": (always,), "H-gated": (gated,)}


def test_rank_prefers_the_candidate_where_hypotheses_actually_disagree() -> None:
    """x1=1,x2=0 is exactly where H-always predicts x3=True and H-gated
    predicts x3=False -- the gate-defining candidate -- so it must rank
    at least as high as every candidate where the two agree."""
    candidates = (_candidate("E-00", False, False), _candidate("E-01", False, True),
                 _candidate("E-10", True, False), _candidate("E-11", True, True))
    ranked = rank_discriminating_candidates(candidates, _compiled_specs(), FunctionalPredictionProvider(_predictions_for))

    by_id = {item.candidate_id: item for item in ranked}
    assert by_id["E-10"].disagreement_pair_count == 1   # x1=1,x2=0: always=True, gated=False -- disagree
    assert by_id["E-00"].disagreement_pair_count == 0   # x1=0,x2=0: both predict False -- agree
    assert by_id["E-01"].disagreement_pair_count == 0   # x1=0,x2=1: both predict False -- agree
    assert by_id["E-11"].disagreement_pair_count == 0   # x1=1,x2=1: both predict True -- agree
    assert ranked[0].candidate_id == "E-10"


def test_rank_orders_by_disagreement_pair_count_then_candidate_id() -> None:
    def three_way(candidate: ExplorationCandidate, spec) -> dict[str, tuple[object, ...]]:
        values = dict(candidate.control_values)
        x1, x2 = bool(values["CTRL-X1"]), bool(values["CTRL-X2"])
        # Three hypotheses. On E-11 all three agree (0 pairs differ). On
        # E-10 exactly two of three differ from the third (2 pairs differ:
        # (H1,H3) and (H2,H3)). On E-01 all three differ pairwise (3 pairs).
        if not x1 and not x2:
            return {"H1": (ObservablePrediction(1, "x3", False),),
                   "H2": (ObservablePrediction(1, "x3", False),),
                   "H3": (ObservablePrediction(1, "x3", False),)}
        if x1 and not x2:
            return {"H1": (ObservablePrediction(1, "x3", True),),
                   "H2": (ObservablePrediction(1, "x3", True),),
                   "H3": (ObservablePrediction(1, "x3", False),)}
        if not x1 and x2:
            return {"H1": (ObservablePrediction(1, "x3", True),),
                   "H2": (ObservablePrediction(1, "x3", False),),
                   "H3": (ObservablePrediction(2, "x3", True),)}
        return {"H1": (ObservablePrediction(1, "x3", True),),
               "H2": (ObservablePrediction(1, "x3", True),),
               "H3": (ObservablePrediction(1, "x3", True),)}

    candidates = (_candidate("E-00", False, False), _candidate("E-01", False, True),
                 _candidate("E-10", True, False), _candidate("E-11", True, True))
    ranked = rank_discriminating_candidates(candidates, _compiled_specs(), FunctionalPredictionProvider(three_way))

    assert [item.candidate_id for item in ranked] == ["E-01", "E-10", "E-00", "E-11"]
    assert [item.disagreement_pair_count for item in ranked] == [3, 2, 0, 0]
    # E-00 and E-11 tie at 0 -- broken by candidate_id ascending.


def test_rank_returns_zero_disagreement_when_all_hypotheses_agree() -> None:
    def always_agree(candidate: ExplorationCandidate, spec) -> dict[str, tuple[object, ...]]:
        return {"H1": (ObservablePrediction(1, "x3", True),), "H2": (ObservablePrediction(1, "x3", True),)}

    candidates = (_candidate("E-10", True, False),)
    ranked = rank_discriminating_candidates(candidates, _compiled_specs(), FunctionalPredictionProvider(always_agree))
    assert ranked == (DiscriminatingCandidate("E-10", 0, {"H1": (ObservablePrediction(1, "x3", True),),
                                                          "H2": (ObservablePrediction(1, "x3", True),)}),)


def test_rank_skips_a_candidate_with_no_compiled_spec() -> None:
    """A candidate whose control values failed to compile into a legal spec
    (a CandidateCompilationFailure at the caller's level) was never a
    legally-formed experiment -- it must not appear in the ranking at all,
    the same "uncompilable is not research data" discipline broad_explorer.py
    already applies to compilation failures."""
    candidates = (_candidate("E-10", True, False), _candidate("E-UNCOMPILED", True, True))
    compiled = {"E-10": _s02_spec()}  # E-UNCOMPILED deliberately missing
    ranked = rank_discriminating_candidates(candidates, compiled, FunctionalPredictionProvider(_predictions_for))
    assert {item.candidate_id for item in ranked} == {"E-10"}


# ---------------------------------------------------------------------------
# select_next_experiment
# ---------------------------------------------------------------------------

def test_select_next_experiment_picks_the_top_ranked_unexecuted_candidate() -> None:
    ranked = (
        DiscriminatingCandidate("E-A", 3, {}),
        DiscriminatingCandidate("E-B", 1, {}),
    )
    selected = select_next_experiment(ranked, already_executed_candidate_ids=frozenset())
    assert selected.candidate_id == "E-A"


def test_select_next_experiment_skips_already_executed_candidates() -> None:
    ranked = (
        DiscriminatingCandidate("E-A", 3, {}),
        DiscriminatingCandidate("E-B", 1, {}),
    )
    selected = select_next_experiment(ranked, already_executed_candidate_ids=frozenset({"E-A"}))
    assert selected.candidate_id == "E-B"


def test_select_next_experiment_never_returns_a_zero_disagreement_candidate() -> None:
    """Even if it is the only not-yet-run candidate left, a candidate no
    live hypothesis disagrees on must never be selected -- running it
    could not produce evidence favoring one live hypothesis over another,
    so selecting it would blur EXPLORATION_FAILURE (no discriminating
    experiment exists) into a false PASS-shaped "B ran something."""
    ranked = (
        DiscriminatingCandidate("E-A", 0, {}),
        DiscriminatingCandidate("E-B", 0, {}),
    )
    assert select_next_experiment(ranked, already_executed_candidate_ids=frozenset()) is None


def test_select_next_experiment_returns_none_when_no_discriminating_candidate_remains() -> None:
    ranked = (
        DiscriminatingCandidate("E-A", 2, {}),
        DiscriminatingCandidate("E-B", 0, {}),
    )
    selected = select_next_experiment(ranked, already_executed_candidate_ids=frozenset({"E-A"}))
    assert selected is None


# ---------------------------------------------------------------------------
# Independence from ground_truth/ and synthetic_runtime.py.
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


def test_experiment_designer_does_not_import_ground_truth_or_synthetic_runtime() -> None:
    path = ROOT / "engine" / "deterministic" / "experiment_designer.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    forbidden = {"ground_truth", "engine.deterministic.synthetic_runtime", ".synthetic_runtime"}
    assert not any(name in forbidden or name.startswith("ground_truth.") for name in imported)
