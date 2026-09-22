"""G6c-2: the `AExecutor` for `SyntheticWorldSpec` -- same shape as `RealCausalAExecutor`.

Checks `isinstance(spec, SyntheticWorldSpec)` before its `try/except`
begins, exactly like `causal_executor.RealCausalAExecutor` checks
`isinstance(spec, CausalWorldSpec)` (G6a.1) -- a wrong-world wiring mistake
raises `WorldCompatibilityError` immediately, never becomes
`ExecutionResult(status="failed")` research data. An unrecognized `rule_id`
inside a syntactically valid spec, by contrast, is exactly that kind of A
failure (`run_synthetic_world` raises `WorldCompatibilityError` for it too,
but from *inside* the world's own execution, not from a spec/executor
mismatch) -- caught by the `try/except` below like any other A failure
would be.
"""
from __future__ import annotations

import traceback

from .causal_executor import ExecutionResult
from .research_world import ResearchWorldSpec, WorldCompatibilityError
from .synthetic_kernel import run_synthetic_world
from .synthetic_spec import SyntheticWorldSpec


class SyntheticAExecutor:
    """Runs a `SyntheticWorldSpec` through `synthetic_kernel.run_synthetic_world`."""

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        if not isinstance(spec, SyntheticWorldSpec):
            raise WorldCompatibilityError(
                f"SyntheticAExecutor requires a SyntheticWorldSpec, got {type(spec).__name__}")
        try:
            run = run_synthetic_world(spec)
        except Exception as exc:  # noqa: BLE001 -- any world-internal failure is B data
            return ExecutionResult("failed", spec.digest, None, type(exc).__name__,
                                   "".join(traceback.format_exception_only(type(exc), exc)).strip())
        return ExecutionResult("success", spec.digest, run)
