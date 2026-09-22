"""G6a: the one door B0 uses to run a spec through any A, physical or synthetic.

`causal_kernel.run_causal_world` can raise -- a v1/v2/v3 world under
unequal-energy head-on collisions trips its own conservation `AssertionError`
(see `tests/test_legacy_causal_semantics.py`). To B that failure is itself a
research-worthy observation, not a crash: `AExecutor.execute` never lets an
exception escape, it reports `ExecutionResult(status="failed", ...)` instead,
so the research loop can record an execution anomaly and keep going.

Before G6a, `AExecutor.execute` took `CausalWorldSpec` and `ExecutionResult.run`
was typed `CausalRun | None` -- Broad Research had already moved onto
`ResearchWorldAdapter` (G3-G5), so the execution boundary was the one place
still typed physical-only, a door the adapter behind it could not actually
walk anyone else through. Both are now typed against `ResearchWorldSpec`/
`ResearchRun` (research_world.py). `RealCausalAExecutor` and `StubAExecutor`
are unchanged in behavior -- see
`tests/test_deterministic_research_world_characterization.py` and
`tests/test_deterministic_physical_research_adapter.py`, both of which
still pass unmodified -- this widens only the type each accepts, not what
either one does with a `CausalWorldSpec` specifically.
"""
from __future__ import annotations

import hashlib
import json
import traceback
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .causal_kernel import run_causal_world
from .causal_spec import CausalWorldSpec
from .research_world import ResearchRun, ResearchWorldSpec

FORMAT = "causal-execution-result-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    executed_spec_digest: str
    run: ResearchRun | None = None
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("success", "failed"):
            raise ValueError("unsupported execution status")
        if not isinstance(self.executed_spec_digest, str) or not self.executed_spec_digest.strip():
            raise ValueError("executed_spec_digest must be non-empty text")
        if self.status == "success" and self.run is None:
            raise ValueError("a successful execution must carry its run")
        if self.status == "failed" and (self.error_kind is None or self.error_message is None):
            raise ValueError("a failed execution must carry an error kind and message")

    def canonical(self) -> dict[str, object]:
        return {
            "error_kind": self.error_kind, "error_message": self.error_message,
            "executed_spec_digest": self.executed_spec_digest, "format": FORMAT,
            "run_digest": self.run.digest if self.run is not None else None,
            "status": self.status,
        }


@runtime_checkable
class AExecutor(Protocol):
    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult: ...


class RealCausalAExecutor:
    """Runs a `CausalWorldSpec` through the real deterministic causal kernel.

    Still physical-only in what it actually does -- `run_causal_world` only
    understands `CausalWorldSpec` -- but now satisfies the widened `AExecutor`
    Protocol like any other executor would. A caller that hands this a
    non-`CausalWorldSpec` gets whatever `run_causal_world`/`spec.digest`
    itself raises (an `AttributeError` or similar), not a clean
    `WorldCompatibilityError` -- unlike `PhysicalCausalResearchAdapter`,
    this class predates the `ResearchWorldError` hierarchy and has not been
    rewritten to raise it; that cleanup, if wanted, is separate from G6a.
    """

    def execute(self, spec: CausalWorldSpec) -> ExecutionResult:
        try:
            run = run_causal_world(spec)
        except Exception as exc:  # noqa: BLE001 -- deliberately wide: any A failure is B data
            return ExecutionResult("failed", spec.digest, None, type(exc).__name__,
                                   "".join(traceback.format_exception_only(type(exc), exc)).strip())
        return ExecutionResult("success", spec.digest, run)


class StubAExecutor:
    """A deterministic fake for B0 unit tests that must not touch the real kernel.

    Returns a fixed, pre-registered `ExecutionResult` per spec digest so tests
    can exercise the research loop's control flow without depending on causal
    A's actual physics. Not used in the end-to-end demo -- see
    `RealCausalAExecutor` for that. Works for any `ResearchWorldSpec` --
    registration is keyed on `spec.digest` alone, so a synthetic spec
    registers and looks up exactly the same way a physical one does.
    """

    def __init__(self) -> None:
        self._results: dict[str, ExecutionResult] = {}

    def register(self, spec: ResearchWorldSpec, result: ExecutionResult) -> None:
        self._results[spec.digest] = result

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        try:
            return self._results[spec.digest]
        except KeyError:
            raise ValueError(f"StubAExecutor has no registered result for spec {spec.digest}") from None
