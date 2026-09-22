"""G6a: the execution boundary (AExecutor/ExecutionResult) no longer types
physical-only, and G6b: a plan naming an undefined control raises
UnknownControlError, never a bare KeyError or a CandidateCompilationFailure.

Neither a synthetic AExecutor nor a synthetic spec exists yet (G6c is
separate, later work) -- these tests confirm the *boundary itself* widened
without changing what RealCausalAExecutor/StubAExecutor actually do, using
a minimal fake ResearchWorldSpec/ResearchRun pair that is not CausalWorldSpec.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from engine.deterministic import (
    BondCountPrediction,
    CausalHypothesis,
    CausalHypothesisSet,
    ControlDefinition,
    ExplorationPlan,
    HeatCellRoleTarget,
    RealCausalAExecutor,
    ResearchJournal,
    StubAExecutor,
    SweepDimension,
    load_causal_world_spec,
    observe,
    record_hypothesis_set,
)
from engine.deterministic.broad_explorer import run_research_exploration
from engine.deterministic.causal_executor import AExecutor, ExecutionResult
from engine.deterministic.physical_research_adapter import PhysicalCausalResearchAdapter
from engine.deterministic.research_prediction import StaticPredictionProvider
from engine.deterministic.research_world import (
    InvalidControlValueError,
    ResearchRun,
    ResearchWorldSpec,
    UnknownControlError,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"

HEAT_CONTROL = ControlDefinition(
    "causal.control.local_heat_energy", HeatCellRoleTarget("local_heat_source", 10, 10, "energy"),
    "causal.heat.energy",
)


@dataclass(frozen=True)
class _FakeRun:
    """The minimum ResearchRun a non-physical executor's ExecutionResult would carry."""
    _digest: str

    @property
    def digest(self) -> str:
        return self._digest


@dataclass(frozen=True)
class _FakeSpec:
    """A ResearchWorldSpec that is deliberately not a CausalWorldSpec."""
    world_id: str

    @property
    def digest(self) -> str:
        return f"fake-digest-{self.world_id}"

    def canonical(self) -> dict[str, object]:
        return {"world_id": self.world_id}


class _FakeExecutor:
    """An AExecutor whose spec/run types are not the physical ones -- proves
    ExecutionResult.run accepts any ResearchRun, not just CausalRun."""

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        return ExecutionResult("success", spec.digest, _FakeRun(f"run-for-{spec.digest}"))


def test_a_executor_protocol_accepts_a_non_physical_executor_and_spec() -> None:
    spec = _FakeSpec("WORLD-FAKE-1")
    executor: AExecutor = _FakeExecutor()
    result = executor.execute(spec)

    assert isinstance(result.run, ResearchRun)
    assert result.status == "success"
    assert result.run.digest == "run-for-fake-digest-WORLD-FAKE-1"
    assert result.canonical()["run_digest"] == "run-for-fake-digest-WORLD-FAKE-1"


def test_real_causal_executor_still_behaves_identically_for_physical_specs() -> None:
    """G6a widened the type RealCausalAExecutor.execute accepts in principle
    (via the AExecutor Protocol) without changing what it does for the
    physical spec it has always handled."""
    spec = load_causal_world_spec(EXAMPLE)
    result = RealCausalAExecutor().execute(spec)
    assert result.status == "success"
    assert result.run is not None
    assert isinstance(result.run, ResearchRun)


def test_stub_a_executor_registers_and_looks_up_a_non_physical_spec() -> None:
    stub = StubAExecutor()
    fake_spec = _FakeSpec("WORLD-FAKE-2")
    fake_result = ExecutionResult("success", fake_spec.digest, _FakeRun("r1"))
    stub.register(fake_spec, fake_result)
    assert stub.execute(fake_spec) is fake_result


# ---------------------------------------------------------------------------
# G6b: KeyError -> UnknownControlError
# ---------------------------------------------------------------------------

def test_run_research_exploration_raises_unknown_control_error_not_key_error(tmp_path: Path) -> None:
    base_spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    observation = observe(journal, base_spec, "undefined control")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), (BondCountPrediction(2, 0),), (), "untested"),)))

    plan = ExplorationPlan("P-undefined-control", base_spec.digest, ("H1",),
                           (SweepDimension("causal.control.does_not_exist", (0, 1)),), "full_factorial", 10)

    empty_controls: Mapping[str, object] = {}
    with pytest.raises(UnknownControlError, match="does_not_exist"):
        run_research_exploration(
            journal, executor, PhysicalCausalResearchAdapter(),
            StaticPredictionProvider({"H1": (BondCountPrediction(2, 0),)}),
            plan, base_spec, empty_controls, observation.observation_id,
        )


def test_undefined_control_is_never_recorded_as_a_compilation_failure(tmp_path: Path) -> None:
    """An UnknownControlError must propagate, not silently become research
    data about the candidate -- verified by checking the exception's type,
    which test_run_research_exploration_raises_unknown_control_error_not_key_error
    already does; this test additionally confirms the sweep's *legal*
    control still works normally when it IS defined, so the fix did not
    accidentally break the happy path."""
    base_spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    observation = observe(journal, base_spec, "defined control still works")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), (BondCountPrediction(2, 0),), (), "untested"),)))

    plan = ExplorationPlan("P-defined-control", base_spec.digest, ("H1",),
                           (SweepDimension(HEAT_CONTROL.control_id, (0, 2)),), "full_factorial", 10)
    outcome = run_research_exploration(
        journal, executor, PhysicalCausalResearchAdapter(),
        StaticPredictionProvider({"H1": (BondCountPrediction(2, 0),)}),
        plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL}, observation.observation_id,
    )
    assert outcome.compilation_failures == ()
    assert len(outcome.evidence) == 2


def test_invalid_control_value_error_is_recorded_as_a_compilation_failure_not_raised(tmp_path: Path) -> None:
    """No adapter today actually raises InvalidControlValueError (see
    research_world.py's docstring: it is reserved for a future synthetic
    adapter's own value legality rules), but the except clause in
    run_research_exploration must treat it as research data about the
    candidate, same category as ValueError/TypeError -- confirmed directly
    against an adapter stub that raises it deliberately."""
    base_spec = load_causal_world_spec(EXAMPLE)
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    executor = RealCausalAExecutor()
    observation = observe(journal, base_spec, "invalid control value")
    record_hypothesis_set(journal, CausalHypothesisSet(base_spec.digest, (
        CausalHypothesis("H1", "claim", (), (BondCountPrediction(2, 0),), (), "untested"),)))

    class _RejectsEverythingAdapter(PhysicalCausalResearchAdapter):
        def apply_control(self, spec, control, value):
            raise InvalidControlValueError(f"value {value!r} is not legal for this world")

    plan = ExplorationPlan("P-invalid-value", base_spec.digest, ("H1",),
                           (SweepDimension(HEAT_CONTROL.control_id, (0, 2)),), "full_factorial", 10)
    outcome = run_research_exploration(
        journal, executor, _RejectsEverythingAdapter(),
        StaticPredictionProvider({"H1": (BondCountPrediction(2, 0),)}),
        plan, base_spec, {HEAT_CONTROL.control_id: HEAT_CONTROL}, observation.observation_id,
    )
    assert len(outcome.compilation_failures) == 2
    assert outcome.evidence == ()
