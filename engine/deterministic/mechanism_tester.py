"""B0.5 orchestrator: MechanismCandidate(s) -> feasibility check -> intervention run -> MechanismEvidence.

Reuses B0.1-B0.4 unchanged: `ControlDefinition`/`apply_control` from B0.3,
`trace_model.run_traced` (the same public `KernelObserver` hook, not a new
tracer) from B0.4, and `ResearchJournal`'s append-only discipline from B0.1.
This module's only new responsibility is asking, before running anything,
"can this be done, and does it discriminate the mechanisms under test" --
and then executing exactly the plan that passed both checks.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable

from .causal_kernel import CausalWorldState
from .causal_spec import CausalWorldSpec
from .exploration_control import ControlDefinition, apply_control
from .intervention_feasibility import InterventionFeasibility, assess_intervention_feasibility
from .mechanism_test import (
    MechanismEvidence,
    MechanismTestPlan,
    MechanismTestResult,
    evaluate_mechanism_test,
)
from .research_journal import ResearchJournal
from .trace_model import TraceSpec, run_traced

FORMAT = "mechanism-tester-v1"


def check_plan_feasibility(
    base_spec: CausalWorldSpec, controls: dict[str, ControlDefinition], plan: MechanismTestPlan,
) -> InterventionFeasibility:
    """Assess whether every intervention in `plan` can be jointly applied to `base_spec`."""
    control_values = tuple((item.control_id, item.value) for item in plan.interventions)
    return assess_intervention_feasibility(base_spec, controls, control_values)


def _build_intervention_spec(base_spec: CausalWorldSpec, controls: dict[str, ControlDefinition],
                             plan: MechanismTestPlan) -> CausalWorldSpec:
    spec = base_spec
    for item in plan.interventions:
        spec = apply_control(spec, controls[item.control_id], item.value)
    return CausalWorldSpec.from_mapping(spec.canonical())


def _run_and_extract_outcome(
    spec: CausalWorldSpec, trace_spec: TraceSpec, extract_outcome: Callable[[tuple], str],
) -> tuple[str, str]:
    """Run `spec` traced and extract its outcome string, reporting execution failure instead of raising."""
    try:
        snapshots = run_traced(spec, trace_spec)
    except Exception as exc:  # noqa: BLE001 -- an A failure here is B data, exactly as in causal_executor.py
        return "failed", f"{type(exc).__name__}: {''.join(traceback.format_exception_only(type(exc), exc)).strip()}"
    return "success", extract_outcome(snapshots)


def run_mechanism_test(
    journal: ResearchJournal, base_spec: CausalWorldSpec, controls: dict[str, ControlDefinition],
    plan: MechanismTestPlan, trace_spec: TraceSpec, extract_outcome: Callable[[tuple], str],
) -> tuple[MechanismTestResult | None, tuple[MechanismEvidence, ...], InterventionFeasibility]:
    """Check feasibility, and only if AVAILABLE, run baseline vs. intervention and evaluate the plan.

    `extract_outcome` reads a `tuple[TraceSnapshot, ...]` down to the single
    outcome string `plan`'s predictions are phrased in terms of (e.g.
    `"bond_exists_at_tick_2"` -> `"bond_breaks"`/`"bond_survives"`) --
    supplied by the caller because only the caller's `MechanismCandidate`
    knows what observable actually distinguishes the competing mechanisms.

    If feasibility is not AVAILABLE, no A execution happens at all: this
    returns `(None, (), feasibility)` and journals only the feasibility
    check. "Cannot currently discriminate these mechanisms with A's public
    controls" is a valid, honest research result, not a caller error.
    """
    journal.append("mechanism_test_planned", plan.plan_id, plan.canonical())
    feasibility = check_plan_feasibility(base_spec, controls, plan)
    journal.append("intervention_feasibility_checked", plan.plan_id, feasibility.canonical())
    if feasibility.status != "AVAILABLE":
        return None, (), feasibility

    intervention_spec = _build_intervention_spec(base_spec, controls, plan)
    baseline_status, baseline_outcome = _run_and_extract_outcome(base_spec, trace_spec, extract_outcome)
    intervention_status, intervention_outcome = _run_and_extract_outcome(intervention_spec, trace_spec, extract_outcome)

    result = MechanismTestResult(plan.plan_id, base_spec.digest, intervention_spec.digest,
                                 baseline_outcome, intervention_outcome, baseline_status, intervention_status)
    journal.append("mechanism_test_executed", plan.plan_id, result.canonical())

    evidence = evaluate_mechanism_test(plan, result)
    for item in evidence:
        journal.append("mechanism_evidence_recorded",
                       f"{item.mechanism_candidate_id}-{plan.plan_id}", item.canonical())
    return result, evidence, feasibility
