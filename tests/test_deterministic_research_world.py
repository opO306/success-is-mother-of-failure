"""G1: existing physical A types must satisfy the new Protocols with zero code changes.

If any of these need a change to CausalWorldSpec/CausalRun to pass, the
Protocol was drawn wrong -- it must generalize the existing type, not
require the existing type to grow toward it.
"""
from __future__ import annotations

from pathlib import Path

from engine.deterministic import load_causal_world_spec
from engine.deterministic.causal_kernel import run_causal_world
from engine.deterministic.research_world import (
    ResearchRun,
    ResearchWorldSpec,
    InvalidControlValueError,
    ResearchWorldError,
    UnknownControlError,
    UnsupportedPredictionError,
    WorldCompatibilityError,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_causal_world_spec_satisfies_research_world_protocol_unmodified() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    assert isinstance(spec, ResearchWorldSpec)
    assert isinstance(spec.world_id, str) and spec.world_id
    assert isinstance(spec.digest, str) and spec.digest
    assert isinstance(spec.canonical(), dict)


def test_causal_run_satisfies_research_run_protocol_unmodified() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    run = run_causal_world(spec)
    assert isinstance(run, ResearchRun)
    assert isinstance(run.digest, str) and run.digest


def test_configuration_mistake_errors_are_research_world_errors() -> None:
    # These three mean the caller wired something wrong -- never research data.
    for error_type in (WorldCompatibilityError, UnknownControlError, UnsupportedPredictionError):
        assert issubclass(error_type, ResearchWorldError)
        assert issubclass(error_type, Exception)


def test_invalid_control_value_error_is_deliberately_not_a_research_world_error() -> None:
    # A candidate's own illegal control value is research data (a
    # CandidateCompilationFailure), not a configuration mistake -- see
    # research_world.py's docstring on why this one type was pulled out of
    # the ResearchWorldError hierarchy. It subclasses ValueError instead, so
    # existing `except ValueError` handling (physical A's CausalWorldSpec.from_mapping,
    # broad_explorer's compilation-failure catch) picks it up without
    # needing to name it explicitly.
    assert not issubclass(InvalidControlValueError, ResearchWorldError)
    assert issubclass(InvalidControlValueError, ValueError)


def test_research_world_errors_are_distinct_types() -> None:
    # Catching WorldCompatibilityError must not also catch UnknownControlError --
    # callers need to tell configuration-mistake kinds apart.
    try:
        raise UnknownControlError("no such control")
    except WorldCompatibilityError:
        assert False, "UnknownControlError must not be caught as WorldCompatibilityError"
    except UnknownControlError:
        pass
