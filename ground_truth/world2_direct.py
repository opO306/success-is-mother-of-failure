"""GT-2: a direct relation A -> C, with no mediator role to find.

Deliberately not built on `causal_kernel` (see package docstring): reusing
A0's heat/bond physics for "no mediator exists" would mean editing the same
engine World 1 uses to prove a mediator DOES exist there, and any accident
in that edit would make both answers suspect. This world is instead a
free-standing two-field state with one step function, defined only here.

    state: (source_active: bool, outcome_active: bool)
    step:  outcome_active := source_active

There is no third field for a mediator to be. The audit is exhaustive over
both source states (only two exist) rather than sampled, and separately
inspects `step` itself to confirm it reads nothing but `source_active`.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass

from .report import GroundTruthReport

FORMAT = "ground-truth-direct-world-v1"


@dataclass(frozen=True)
class DirectState:
    source_active: bool
    outcome_active: bool

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "outcome_active": self.outcome_active, "source_active": self.source_active}


def step(state: DirectState) -> DirectState:
    """The entire A2 rule: C copies A. No other field is read or written."""
    return DirectState(source_active=state.source_active, outcome_active=state.source_active)


def _world_digest() -> str:
    # Stands in for `CausalWorldSpec.digest` in World 1: for a synthetic
    # world defined entirely in source, the rule's own source text (not a
    # JSON file) is what a caller would need to reproduce this world, so
    # that is what gets hashed and sealed.
    import hashlib
    return hashlib.sha256(inspect.getsource(step).encode("utf-8")).hexdigest()


def audit_world2_direct() -> GroundTruthReport:
    report = GroundTruthReport(
        world_id="GT-2-direct-A-to-C",
        world_spec_digest=_world_digest(),
        expected_edges=(("source_active", "outcome_active"),),
        forbidden_edges=(),  # no mediator field exists to name as a forbidden intermediate
        exhaustive=True,
    )

    try:
        cases_checked = 0
        for source_active in (False, True):
            initial = DirectState(source_active=source_active, outcome_active=False)
            result = step(initial)
            cases_checked += 1
            report.add(f"A_directly_sets_C_when_source_active={source_active}",
                       result.outcome_active == source_active,
                       expected=source_active, observed=result.outcome_active,
                       detail="one exhaustive case out of the two possible source_active values")
        report.exhaustive_cases_checked = cases_checked

        # A only changes C when initial outcome_active differs from source_active --
        # confirm the initial value of outcome_active is never consulted (no hidden
        # persistence/memory that would make this secretly mediated by its own past).
        forced_true_start = step(DirectState(source_active=False, outcome_active=True))
        forced_false_start = step(DirectState(source_active=False, outcome_active=False))
        outcome_ignores_its_own_prior_value = forced_true_start == forced_false_start
        report.add("no_hidden_state_outcome_prior_value_is_not_read",
                   outcome_ignores_its_own_prior_value,
                   expected="step() output identical regardless of incoming outcome_active",
                   observed={"from_prior_true": forced_true_start.canonical(),
                             "from_prior_false": forced_false_start.canonical()},
                   detail="rules out outcome_active acting as its own hidden mediator across steps")

        # Source-reading check: the step function's own body should reference no
        # field but source_active. This is read directly off the function, the
        # same way World 1's expected structure came off causal_kernel.py's own
        # break_heat rule rather than a guess about the rule.
        source_text = inspect.getsource(step)
        only_reads_source_active = "state.outcome_active" not in source_text
        report.add("step_function_reads_only_source_active", only_reads_source_active,
                   expected="step()'s body does not reference state.outcome_active as an input",
                   observed={"source": source_text.strip()},
                   detail="static confirmation there is no field this world could be smuggling "
                          "a mediator relationship through")
    except Exception as error:  # noqa: BLE001
        report.mark_audit_error(f"{type(error).__name__}: {error}")

    return report
