"""G6c-2/G6c-3.1: the `AExecutor` for `SyntheticWorldSpec` -- same shape as `RealCausalAExecutor`.

Checks `isinstance(spec, SyntheticWorldSpec)` and resolves the
`(world_id, world_revision)` binding both before the `try/except` begins,
exactly like `causal_executor.RealCausalAExecutor` checks
`isinstance(spec, CausalWorldSpec)` (G6a.1) -- a wrong-world wiring mistake
or an unbound world both raise `WorldCompatibilityError` immediately, never
become `ExecutionResult(status="failed")` research data.

G6c-3.1 moved the rule lookup out of `run_synthetic_world` and into this
module specifically because an earlier draft did that lookup *inside*
`run_synthetic_world`, which ran inside this class's `try/except` -- so an
unbound world (a configuration mistake) and an actual A-internal failure
were indistinguishable from the caller's side, exactly the wiring-error/
research-data conflation G6a.1 spent a whole Gate removing from the
physical executor. This is the only module allowed to call
`synthetic_runtime.resolve_rule` -- `SyntheticResearchAdapter` never does,
since it only interprets an already-produced `ExecutionResult` and has no
reason to know which hidden rule produced it.
"""
from __future__ import annotations

import traceback

from .causal_executor import ExecutionResult
from .research_world import ResearchWorldSpec, WorldCompatibilityError
from .synthetic_kernel import run_synthetic_world
from .synthetic_runtime import resolve_rule
from .synthetic_spec import SyntheticWorldSpec


class SyntheticAExecutor:
    """Runs a `SyntheticWorldSpec` through `synthetic_kernel.run_synthetic_world`."""

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        if not isinstance(spec, SyntheticWorldSpec):
            raise WorldCompatibilityError(
                f"SyntheticAExecutor requires a SyntheticWorldSpec, got {type(spec).__name__}")
        # resolve_rule raises WorldCompatibilityError for an unbound
        # (world_id, world_revision) -- deliberately outside the try/except
        # below, since a spec naming a world/revision nothing is bound to is
        # a configuration mistake, not A failing during execution.
        rule = resolve_rule(spec.world_id, spec.world_revision)
        try:
            run = run_synthetic_world(spec, rule)
        except Exception as exc:  # noqa: BLE001 -- any world-internal failure is B data
            return ExecutionResult("failed", spec.digest, None, type(exc).__name__,
                                   "".join(traceback.format_exception_only(type(exc), exc)).strip())
        return ExecutionResult("success", spec.digest, run)
