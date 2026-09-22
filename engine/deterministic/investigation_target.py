"""What a Deep Investigator run is about, sealed before any trace is collected.

An `InvestigationTarget` names the two candidates being compared and which
outcome distinguishes them, before B0.4 goes looking for why. Usually built
from a `BoundaryCandidate` or `IsolatedCaseCandidate` B0.3 already found
(the "red dot on the map"), but nothing here requires that origin -- any two
candidates with a known outcome difference can be investigated.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not result:
        raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{context} values must be unique")
    return result


FORMAT = "investigation-target-v1"


@dataclass(frozen=True)
class InvestigationTarget:
    """Seals which two candidates B0.4 compares, and what outcome distinguishes them.

    `source_candidate_id` names where this target came from (typically a
    `BoundaryCandidate`'s pair or an `IsolatedCaseCandidate`'s id), kept for
    provenance -- the investigation itself only needs `baseline_spec_digest`
    and `contrast_spec_digest`.
    """
    target_id: str
    source_candidate_id: str
    baseline_spec_digest: str
    contrast_spec_digest: str
    outcome_description: str
    target_roles: tuple[str, ...]
    start_tick: int
    end_tick: int

    def __post_init__(self) -> None:
        _text(self.target_id, "target_id")
        _text(self.source_candidate_id, "source_candidate_id")
        _text(self.baseline_spec_digest, "baseline_spec_digest")
        _text(self.contrast_spec_digest, "contrast_spec_digest")
        _text(self.outcome_description, "outcome_description")
        _texts(self.target_roles, "target_roles")
        if self.baseline_spec_digest == self.contrast_spec_digest:
            raise ValueError("baseline and contrast must be different specs")
        if isinstance(self.start_tick, bool) or not isinstance(self.start_tick, int) or self.start_tick < 0:
            raise ValueError("start_tick must be a nonnegative integer")
        if isinstance(self.end_tick, bool) or not isinstance(self.end_tick, int) or self.end_tick < self.start_tick:
            raise ValueError("end_tick must be an integer at least start_tick")

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"baseline_spec_digest": self.baseline_spec_digest, "contrast_spec_digest": self.contrast_spec_digest,
                "end_tick": self.end_tick, "format": FORMAT, "outcome_description": self.outcome_description,
                "source_candidate_id": self.source_candidate_id, "start_tick": self.start_tick,
                "target_id": self.target_id, "target_roles": list(self.target_roles)}
