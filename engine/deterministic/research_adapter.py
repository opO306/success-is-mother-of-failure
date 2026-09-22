"""G1: the world-agnostic vocabulary an adapter uses to talk about a world.

`ResearchControlDefinition` is what `exploration_control.ControlDefinition`
already structurally satisfies, unmodified -- see
`tests/test_deterministic_research_adapter.py`. `WorldObservation` and
`PredictionEvaluation` are new dataclasses (not Protocols): every adapter
constructs and returns the same concrete type, so callers do not need to
know which adapter produced one.

`ResearchWorldAdapter` deliberately has no `execute()` method. Executing a
world and interpreting/mutating it are different responsibilities --
`AExecutor` (in `causal_executor.py`) owns the former, an adapter owns the
latter. Splitting them is what lets `AExecutor` stay exactly as narrow as
it already is (one method, `execute`) while still letting different world
kinds share the same executor abstraction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Protocol, runtime_checkable

from .research_world import ResearchWorldSpec

if TYPE_CHECKING:
    from .causal_executor import ExecutionResult

PREDICTION_EVALUATION_STATUSES = frozenset({"match", "mismatch", "unavailable"})


@runtime_checkable
class ResearchControlDefinition(Protocol):
    """A named, mutable axis of a world. `exploration_control.ControlDefinition` already satisfies this."""
    control_id: str
    research_axis: str

    def canonical(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class WorldObservation:
    """What an adapter read off a world's initial state, before any interpretation.

    Mirrors the shape `research_loop.observe()` already builds by hand for
    `CausalWorldSpec` (`material_counts`/`total_energy`/`momentum`/`state_digest`
    as a flat `observables` mapping) -- this type exists so that shape can be
    produced by any adapter, not just the physical one.
    """
    world_digest: str
    tick: int
    observables: Mapping[str, object]
    state_digest: str

    def canonical(self) -> dict[str, object]:
        return {"observables": dict(sorted(self.observables.items())), "state_digest": self.state_digest,
                "tick": self.tick, "world_digest": self.world_digest}


@dataclass(frozen=True)
class PredictionEvaluation:
    """The result of checking one prediction against one execution's outcome.

    Maps directly onto the three-way verdict `research_loop.compare_results`
    and `broad_explorer._compare` already produce by hand:
    match -> supported, mismatch -> contradicted_in_domain/contradicts,
    unavailable -> underspecified. An adapter reports only this triple; the
    research loop -- not the adapter -- decides what each status means for a
    hypothesis's evidence.
    """
    status: str
    expected: object
    observed: object | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in PREDICTION_EVALUATION_STATUSES:
            raise ValueError(f"unsupported prediction evaluation status {self.status!r}")

    def canonical(self) -> dict[str, object]:
        return {"expected": self.expected, "observed": self.observed, "reason": self.reason, "status": self.status}


@runtime_checkable
class ResearchWorldAdapter(Protocol):
    """Translates world-agnostic requests (apply this control, read this observable)
    into whatever a specific `ResearchWorldSpec` kind actually requires.

    No `execute()` here on purpose -- see module docstring.
    """
    adapter_id: str

    def assert_compatible(self, spec: ResearchWorldSpec) -> None: ...

    def validate(self, spec: ResearchWorldSpec) -> ResearchWorldSpec: ...

    def apply_control(self, spec: ResearchWorldSpec, control: ResearchControlDefinition,
                      value: object) -> ResearchWorldSpec: ...

    def initial_observation(self, spec: ResearchWorldSpec) -> WorldObservation: ...

    def evaluate_prediction(self, prediction: object, result: "ExecutionResult") -> PredictionEvaluation: ...
