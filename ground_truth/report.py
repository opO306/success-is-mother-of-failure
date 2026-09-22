"""Shared sealed-report shape for all three ground-truth worlds.

A `GroundTruthReport` is the only thing this package hands back to a caller.
Its `verdict` is one of four values, never a bare pass/fail:

    VALID           every check this world defines actually held in A
    INVALID_WORLD   a check failed -- the *world's* intended structure is
                    not what A actually does; this is not B's fault, and not
                    something to quietly edit away -- see README section on
                    sealing
    AMBIGUOUS       a check could not be run to a conclusion with the public
                    controls/observables available (never silently treated
                    as VALID)
    AUDIT_ERROR     this auditor's own code hit an unexpected condition

`digest` is computed over `canonical()`, which excludes `digest` itself, so
sealing a report and re-hashing it later reproduces the same value as long
as nothing in the checks changed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

VERDICTS = frozenset({"VALID", "INVALID_WORLD", "AMBIGUOUS", "AUDIT_ERROR"})


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CheckResult:
    """One named check this world ran, and what it found.

    `expected`/`observed` are stored as plain JSON-safe values so the report
    is self-contained -- reading it back does not require re-running A.
    """
    name: str
    passed: bool
    expected: Any
    observed: Any
    detail: str = ""

    def canonical(self) -> dict[str, Any]:
        return {"detail": self.detail, "expected": self.expected, "name": self.name,
                "observed": self.observed, "passed": self.passed}


@dataclass
class GroundTruthReport:
    world_id: str
    world_spec_digest: str
    expected_edges: tuple[tuple[str, str], ...]
    forbidden_edges: tuple[tuple[str, str], ...]
    checks: list[CheckResult] = field(default_factory=list)
    exhaustive: bool = False
    exhaustive_cases_checked: int = 0
    notes: tuple[str, ...] = ()

    @property
    def verdict(self) -> str:
        if any(c.name == "__audit_error__" for c in self.checks):
            return "AUDIT_ERROR"
        if any(c.name.startswith("__ambiguous__") for c in self.checks):
            return "AMBIGUOUS"
        if all(c.passed for c in self.checks) and self.checks:
            return "VALID"
        if not self.checks:
            return "AMBIGUOUS"
        return "INVALID_WORLD"

    def add(self, name: str, passed: bool, expected: Any, observed: Any, detail: str = "") -> None:
        self.checks.append(CheckResult(name, passed, expected, observed, detail))

    def mark_ambiguous(self, name: str, reason: str) -> None:
        self.checks.append(CheckResult(f"__ambiguous__{name}", False, None, None, reason))

    def mark_audit_error(self, reason: str) -> None:
        self.checks.append(CheckResult("__audit_error__", False, None, None, reason))

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, Any]:
        return {
            "checks": [c.canonical() for c in self.checks],
            "exhaustive": self.exhaustive,
            "exhaustive_cases_checked": self.exhaustive_cases_checked,
            "expected_edges": [list(pair) for pair in self.expected_edges],
            "forbidden_edges": [list(pair) for pair in self.forbidden_edges],
            "format": "ground-truth-report-v1",
            "notes": list(self.notes),
            "verdict": self.verdict,
            "world_id": self.world_id,
            "world_spec_digest": self.world_spec_digest,
        }

    def sealed(self) -> dict[str, Any]:
        """The report plus its own digest -- what gets written to disk."""
        body = self.canonical()
        body["ground_truth_digest"] = self.digest
        return body
