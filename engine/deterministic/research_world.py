"""G1: the minimum common contract between B's Broad Research path and any A it studies.

Nothing here changes what any existing type does. `ResearchWorldSpec` and
`ResearchRun` are Protocols that `CausalWorldSpec` and `CausalRun` already
satisfy structurally, with no code changes to either -- see
`tests/test_deterministic_research_world.py`.

Deliberately excluded from `ResearchWorldSpec`: `particles`, `heat`,
`bond_rules`, `gate`, `mediator`, or any field naming what the world is
*made of*. The moment such a field appears here, this Protocol stops being
a common contract and becomes "CausalWorldSpec with extra steps" again --
the exact failure mode this refactor exists to avoid (see
CURRENT_STATE.md's "(마)" entry on why the naive "just wrap AExecutor"
plan didn't survive contact with the real code). A world is a research
subject here only in the sense that it can be identified (`world_id`),
fingerprinted (`digest`), and serialized for journaling (`canonical()`) --
nothing about its internal structure.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ResearchWorldSpec(Protocol):
    """A world B can study: identifiable, fingerprintable, journalable. Nothing more."""
    world_id: str

    @property
    def digest(self) -> str: ...

    def canonical(self) -> dict[str, object]: ...


@runtime_checkable
class ResearchRun(Protocol):
    """The record of one execution of a `ResearchWorldSpec`. Only a digest is common."""

    @property
    def digest(self) -> str: ...


class ResearchWorldError(Exception):
    """Base class for every error this abstraction layer raises on its own.

    Distinct from a *research* failure (an illegal candidate, an A execution
    that fails, a prediction with no matching checkpoint) -- those are data
    B records and reasons about. `WorldCompatibilityError` and
    `UnknownControlError` mean the caller wired an adapter to a spec it was
    never built for, or named a control that does not exist at all -- these
    are programming/configuration mistakes, not observations about a world,
    so callers (`broad_explorer.run_research_exploration` included) must let
    them propagate rather than catching them as research data (see
    `causal_executor.py`'s docstring on the same distinction for A-execution
    failures specifically).

    `InvalidControlValueError` is the one exception to that rule -- see its
    own docstring below.
    """


class WorldCompatibilityError(ResearchWorldError):
    """An adapter was asked to handle a `ResearchWorldSpec` it does not recognize."""


class UnknownControlError(ResearchWorldError):
    """A control id was named that the adapter has no definition for."""


class InvalidControlValueError(ResearchWorldError):
    """A named, existing control was asked to take a value its world rejects as illegal.

    Grouped under `ResearchWorldError` by category (an adapter raises it,
    same as the others), but *not* a configuration mistake the way
    `WorldCompatibilityError`/`UnknownControlError` are: the control exists
    and the caller's wiring is correct, the *value* a particular candidate
    tried is simply outside what this world permits (heat=-1, say). That is
    research data about the candidate, exactly like the `ValueError` a
    physical `CausalWorldSpec.from_mapping` raises for the same kind of
    mistake -- `broad_explorer.run_research_exploration` catches this one
    (alongside `ValueError`/`TypeError`) as a `CandidateCompilationFailure`,
    never lets it propagate as a wiring error.
    """


class UnsupportedPredictionError(ResearchWorldError):
    """A prediction kind was given to an adapter that cannot evaluate it."""
