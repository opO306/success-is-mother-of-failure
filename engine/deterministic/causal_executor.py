"""G6a/G6a.1: the one door B0 uses to run a spec through any A, physical or synthetic.

Two distinct kinds of "execution did not go as expected", never conflated:

  A's own physics failing (e.g. a v1/v2/v3 world's conservation
  `AssertionError` under unequal-energy head-on collisions -- see
  `tests/test_legacy_causal_semantics.py`) is research-worthy *data*.
  `AExecutor.execute` never lets that escape as an exception; it reports
  `ExecutionResult(status="failed", ...)` instead, so the research loop can
  record an execution anomaly and keep going.

  A caller handing an executor a spec kind it cannot run at all (a
  `SyntheticWorldSpec` to `RealCausalAExecutor`, say) is a wiring mistake,
  not a fact about any world. Every executor here raises
  `WorldCompatibilityError` for that case, checked before its `try/except`
  begins -- see `RealCausalAExecutor.execute`'s docstring for why the two
  must never share a code path.

`AExecutor.execute` takes `ResearchWorldSpec` and `ExecutionResult.run` is
typed `ResearchRun | None` (research_world.py) -- widened in G6a from
`CausalWorldSpec`/`CausalRun | None`, since Broad Research had already
moved onto `ResearchWorldAdapter` (G3-G5) and the execution boundary was
the one place still typed physical-only. `RealCausalAExecutor` and
`StubAExecutor` are unchanged in *physical* behavior throughout G6a/G6a.1 --
see `tests/test_deterministic_research_world_characterization.py` and
`tests/test_deterministic_physical_research_adapter.py`, both of which
still pass unmodified.
"""
from __future__ import annotations

import hashlib
import json
import traceback
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .causal_kernel import run_causal_world
from .causal_spec import CausalWorldSpec
from .research_world import ResearchRun, ResearchWorldSpec, WorldCompatibilityError

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

    G6a widened `AExecutor.execute`'s Protocol signature to accept any
    `ResearchWorldSpec`, which this class satisfies structurally (Python's
    `@runtime_checkable` does not check parameter types) without actually
    being able to run anything but physical A0 -- `run_causal_world` only
    understands `CausalWorldSpec`. G6a.1 makes that real narrowing an
    explicit, checked contract instead of an implicit one: a non-physical
    spec raises `WorldCompatibilityError` up front, before `run_causal_world`
    is ever called.

    This check sits outside the `try/except Exception` below on purpose. A
    wrong-executor-for-this-world wiring mistake is not a fact about A's
    physics the way an unequal-energy conservation `AssertionError` is --
    conflating the two would let a configuration error masquerade as
    `ExecutionResult(status="failed")` research data, exactly the failure
    mode `ResearchWorldError`'s docstring warns against.
    """

    def execute(self, spec: ResearchWorldSpec) -> ExecutionResult:
        if not isinstance(spec, CausalWorldSpec):
            raise WorldCompatibilityError(
                f"RealCausalAExecutor requires a CausalWorldSpec, got {type(spec).__name__}")
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
