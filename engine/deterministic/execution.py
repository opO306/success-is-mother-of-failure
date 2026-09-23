"""The execution door's *shape*: what B hands an executor and what comes back.

Moved out of `causal_executor.py` (which re-exports both): that module also
holds `RealCausalAExecutor`, so every B-side module that needed only the
`AExecutor` protocol was pulling A's particle kernel into its import
closure. Found while freezing grammar v3 (G11 follow-up), the same kind of
gap as `evidence.py`. This module imports only the research-world types.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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
