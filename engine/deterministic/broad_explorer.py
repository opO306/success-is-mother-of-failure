"""Broad Explorer: plan -> candidates -> execute -> evidence -> coverage/boundary analysis.

`run_research_exploration` (G4-G5) is the world-agnostic core: each candidate
compiles to a `ResearchWorldSpec` via `adapter.apply_control`/`adapter.validate`,
runs through the same `execute_through_a`/`PredictionSeal`/`record_domain_evidence`
path a hand-written experiment would use, with `prediction_provider` supplying
each candidate's sealed predictions. `run_exploration` is the physical-A
compatibility wrapper -- `PhysicalCausalResearchAdapter` and
`StaticPredictionProvider`, unchanged signature for existing callers. This
module's own job either way is generating many candidates systematically and
registering one *point* domain per candidate -- never one shared domain for
the whole sweep, which would make every disagreeing pair of candidates look
like a same-domain `ContradictionRecord` instead of the expected "different
points, different outcomes" (see docs/README's point-domain requirement).

As of G6a, `AExecutor.execute` itself accepts any `ResearchWorldSpec`
(`causal_executor.py`) -- so which A a candidate actually runs through is
entirely the `executor`/`adapter` pair a caller supplies, not something this
module hardcodes. `RealCausalAExecutor` is still physical-only in what it
does (it calls `causal_kernel.run_causal_world`, which only understands
`CausalWorldSpec`), but nothing here or in `AExecutor`'s own Protocol says
that has to be the only kind of executor.

"Broad" names a research strategy (many different conditions), not a
hardware target -- each candidate runs sequentially on CPU, whatever
executor is in use. Parallelizing is a later, purely mechanical change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .causal_experiment import PredictionSeal
from .causal_executor import AExecutor
from .causal_spec import CausalWorldSpec
from .exploration_analysis import (
    CoverageReport,
    compute_coverage,
    find_boundary_candidates,
    find_isolated_cases,
)
from .exploration_control import ControlDefinition, apply_control, bind_control
from .exploration_space import ExplorationCandidate, ExplorationPlan, generate_candidates
from .physical_research_adapter import PhysicalCausalResearchAdapter
from .research_adapter import ResearchControlDefinition, ResearchWorldAdapter
from .research_axis import AxisRegistry, CAUSAL_AXIS_REGISTRY
from .research_domain import ExactConstraint, ResearchDomain
from .research_journal import ResearchJournal
from .research_loop import (
    _observed_value,
    _predicted_value,
    execute_through_a,
    record_domain_evidence,
    register_domain,
    seal_predictions,
)
from .research_memory import DomainEvidence
from .research_prediction import CandidatePredictionProvider, StaticPredictionProvider
from .research_world import (
    InvalidControlValueError,
    ResearchWorldSpec,
    UnknownControlError,
    WorldCompatibilityError,
)

_PHYSICAL_ADAPTER = PhysicalCausalResearchAdapter()

FORMAT = "broad-explorer-outcome-v1"


@dataclass(frozen=True)
class CandidateCompilationFailure:
    """A candidate's control values could not produce a legal `CausalWorldSpec`.

    Neither a hypothesis contradiction nor an anomaly: the experiment was
    never legally formed, so it carries no evidence for or against anything.
    Preserved anyway, because "which regions of control-space are not even
    representable" is itself research information.
    """
    candidate_id: str
    control_values: tuple[tuple[str, object], ...]
    reason: str

    def canonical(self) -> dict[str, object]:
        return {"candidate_id": self.candidate_id, "control_values": [list(pair) for pair in self.control_values],
                "format": FORMAT, "reason": self.reason}


@dataclass(frozen=True)
class ExplorationOutcome:
    plan: ExplorationPlan
    candidates: tuple[ExplorationCandidate, ...]
    evidence: tuple[DomainEvidence, ...]
    compilation_failures: tuple[CandidateCompilationFailure, ...]
    coverage: CoverageReport
    boundary_candidates: tuple[object, ...]
    isolated_cases: tuple[object, ...]

    def canonical(self) -> dict[str, object]:
        return {"boundary_candidates": [x.canonical() for x in self.boundary_candidates],
                "coverage": self.coverage.canonical(),
                "compilation_failures": [x.canonical() for x in self.compilation_failures],
                "evidence": [x.canonical() for x in sorted(self.evidence)], "format": FORMAT,
                "isolated_cases": [x.canonical() for x in self.isolated_cases],
                "plan": self.plan.canonical()}


def _point_domain(plan: ExplorationPlan, candidate: ExplorationCandidate,
                  controls: Mapping[str, ResearchControlDefinition]) -> ResearchDomain:
    """One exact-value domain per candidate, on the *research* axes its controls declare.

    Uses `controls[control_id].research_axis`, never the raw `control_id`:
    a control id such as `"causal.control.local_heat_energy"` names a
    mechanism, not a registered research axis, and would fail
    `ResearchDomain.validate_against` if used directly.
    """
    constraints = tuple(ExactConstraint(controls[control_id].research_axis, value)
                        for control_id, value in candidate.control_values)
    return ResearchDomain(f"POINT-{candidate.candidate_id}", constraints,
                          f"single point from plan {plan.plan_id}")


_EVALUATION_STATUS_TO_RELATION = {"match": "supports", "mismatch": "contradicts", "unavailable": "underspecified"}


def run_research_exploration(
    journal: ResearchJournal, executor: AExecutor, adapter: ResearchWorldAdapter,
    prediction_provider: CandidatePredictionProvider, plan: ExplorationPlan,
    base_spec: ResearchWorldSpec, controls: Mapping[str, ResearchControlDefinition],
    observation_id: str, axis_registry: AxisRegistry = CAUSAL_AXIS_REGISTRY,
) -> ExplorationOutcome:
    """World-agnostic core of `run_exploration`: run every candidate in `plan`
    through `executor`, via `adapter`, recording a point domain and evidence
    for each.

    `prediction_provider` gives, per candidate and its compiled spec, the
    sealed predictions to check per target hypothesis -- generalizes the old
    fixed `predictions_for_hypothesis` mapping (still available as
    `StaticPredictionProvider` for callers whose predictions do not vary by
    candidate, which is every existing caller).

    A `WorldCompatibilityError` or `UnknownControlError` from `adapter` is a
    configuration mistake (the caller wired the wrong adapter, or named a
    control that was never defined) and is never caught here -- only a
    candidate's own illegal *value* (an `InvalidControlValueError`, or
    whatever `adapter.validate` raises for its world's legality rules)
    becomes a `CandidateCompilationFailure`.
    """
    if base_spec.digest != plan.base_spec_digest:
        raise ValueError("base_spec does not match the plan's declared base_spec_digest")
    candidates = generate_candidates(plan)

    evidence: list[DomainEvidence] = []
    compilation_failures: list[CandidateCompilationFailure] = []
    tested_values_by_axis: dict[str, set[object]] = {}
    relation_points: dict[str, list[tuple[object, str]]] = {}
    grouping_relations: list[tuple[str, tuple[object, ...], str]] = []

    for candidate in candidates:
        for control_id, value in candidate.control_values:
            tested_values_by_axis.setdefault(control_id, set()).add(value)

        try:
            spec = base_spec
            for control_id, value in candidate.control_values:
                try:
                    control = controls[control_id]
                except KeyError:
                    # A plan naming a control this call never defined is a
                    # wiring mistake, not a fact about the candidate -- same
                    # category as WorldCompatibilityError below, so it must
                    # not be swallowed as a CandidateCompilationFailure
                    # either. Converted explicitly here because a bare dict
                    # lookup raises plain KeyError, not the ResearchWorldError
                    # this module's contract promises for configuration
                    # mistakes (see run_research_exploration's docstring).
                    raise UnknownControlError(
                        f"plan names control {control_id!r}, which is not in `controls`") from None
                spec = adapter.apply_control(spec, control, value)
            # `apply_control` mutates the spec and does not itself validate,
            # so round-trip through the adapter's own validation to catch an
            # illegal combination -- negative energy, an unknown material
            # kind, and so on -- before it ever reaches the executor.
            spec = adapter.validate(spec)
        except (InvalidControlValueError, ValueError, TypeError) as exc:
            # A candidate's own illegal control value or combination --
            # research data about this candidate, not a wiring mistake.
            # ValueError/TypeError (rather than only InvalidControlValueError)
            # matches what CausalWorldSpec.from_mapping and
            # exploration_control's ControlTarget.resolve() actually raise
            # for the physical adapter today (see test_deterministic_broad_explorer.py's
            # negative-heat compilation-failure test).
            compilation_failures.append(CandidateCompilationFailure(
                candidate.candidate_id, candidate.control_values, f"{type(exc).__name__}: {exc}",
            ))
            continue
        except (WorldCompatibilityError, UnknownControlError):
            raise  # configuration mistakes, never a candidate's data

        domain = _point_domain(plan, candidate, controls)
        domain.validate_against(axis_registry)
        register_domain(journal, domain)

        predictions_for_hypothesis = prediction_provider.predictions_for(candidate, spec)
        seal = PredictionSeal(f"PS-{candidate.candidate_id}", candidate.candidate_id, journal.next_sequence,
                              dict(predictions_for_hypothesis))
        seal_predictions(journal, seal)
        result = execute_through_a(journal, executor, candidate.candidate_id, spec)

        for hypothesis_id, predictions in predictions_for_hypothesis.items():
            relation = _compare_with_adapter(adapter, result, predictions)
            item = DomainEvidence(
                f"DE-{candidate.candidate_id}-{hypothesis_id}", hypothesis_id, domain.domain_id,
                candidate.candidate_id, seal.seal_id, relation, (observation_id,),
                spec.digest, result.executed_spec_digest,
            )
            recorded, _contradiction = record_domain_evidence(journal, item, tuple(evidence))
            evidence.append(recorded)

            if len(candidate.control_values) == 1:
                axis, value = candidate.control_values[0]
                relation_points.setdefault(axis, []).append((value, relation))
            else:
                for axis, value in candidate.control_values:
                    other = tuple(v for a, v in candidate.control_values if a != axis)
                    grouping_relations.append((candidate.candidate_id, other, relation))

    dimensions = {d.control_id: d.values for d in plan.dimensions}
    coverage = compute_coverage(plan.plan_id, dimensions, plan.planned_candidate_count,
                                tested_values_by_axis, len(candidates) - len(compilation_failures),
                                len(compilation_failures))

    boundary_candidates: list[object] = []
    for axis, points in relation_points.items():
        boundary_candidates.extend(find_boundary_candidates(axis, tuple(points)))

    isolated_cases = find_isolated_cases(tuple(grouping_relations)) if grouping_relations else ()

    return ExplorationOutcome(plan, candidates, tuple(evidence), tuple(compilation_failures), coverage,
                              tuple(boundary_candidates), isolated_cases)


def run_exploration(
    journal: ResearchJournal, executor: AExecutor, plan: ExplorationPlan,
    base_spec: CausalWorldSpec, controls: Mapping[str, ControlDefinition],
    predictions_for_hypothesis: Mapping[str, tuple[object, ...]],
    observation_id: str, axis_registry: AxisRegistry = CAUSAL_AXIS_REGISTRY,
) -> ExplorationOutcome:
    """Run every candidate in `plan` through `executor`, recording a point domain and evidence for each.

    `predictions_for_hypothesis` gives, per target hypothesis, the sealed
    predictions to check against every candidate's tick-checkpoints (the same
    shape `PredictionSeal.predictions_by_hypothesis` expects) -- callers
    decide what a hypothesis predicts; this function only runs it many times.

    Physical-A compatibility wrapper around `run_research_exploration` --
    unchanged signature and behavior for existing callers.
    """
    return run_research_exploration(
        journal, executor, _PHYSICAL_ADAPTER, StaticPredictionProvider(predictions_for_hypothesis),
        plan, base_spec, controls, observation_id, axis_registry,
    )


def _compare_with_adapter(adapter: ResearchWorldAdapter, result, predictions: tuple[object, ...]) -> str:
    """Folds several predictions for one hypothesis into one evidence relation,
    exactly as the old `_compare` did -- but asks `adapter.evaluate_prediction`
    per prediction instead of hardcoding physical A's comparison."""
    if result.status == "failed":
        return "underspecified"
    outcomes = [_EVALUATION_STATUS_TO_RELATION[adapter.evaluate_prediction(prediction, result).status]
               for prediction in predictions]
    if "contradicts" in outcomes:
        return "contradicts"
    if "underspecified" in outcomes:
        return "underspecified"
    return "supports"


def _compare(result, predictions: tuple[object, ...]) -> str:
    """Physical-A compatibility wrapper around `_compare_with_adapter`."""
    return _compare_with_adapter(_PHYSICAL_ADAPTER, result, predictions)
