"""Evaluator-only tiers: `evaluator` (real world identity, real spec,
alias<->real mapping) and `ground_truth` (answers, scoring). Never imported
by B-side code or by anything that builds training data for a learned B --
checked by the dependency tests in `tests/test_research_store.py`.

Evaluator records may reference b_visible objects (e.g. "this mapping
belongs to that blind run"); the reverse is refused by `_core`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ._core import EVALUATOR, GROUND_TRUTH, ObjectRef, StoreRecord, TierStore, verify_tier


class EvaluatorStore:
    """Read/write for the evaluator and ground_truth tiers, plus read access
    to b_visible objects an evaluator record points at."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._tiers = {EVALUATOR: TierStore(root, EVALUATOR), GROUND_TRUTH: TierStore(root, GROUND_TRUTH)}

    def put(self, tier: str, value: Any) -> ObjectRef:
        return self._tier(tier).put_object(value)

    def record(self, tier: str, record_type: str, schema_version: int, provenance: Mapping[str, Any],
               tags: Mapping[str, str], payload: ObjectRef, refs: tuple[ObjectRef, ...] = ()) -> StoreRecord:
        return self._tier(tier).append_record(record_type, schema_version, provenance, tags, payload, refs)

    def records(self, tier: str, record_type: str, *, semantics: str) -> list[StoreRecord]:
        return [r for r in self._tier(tier).records() if r.record_type == record_type and r.semantics == semantics]

    def get(self, ref: ObjectRef) -> Any:
        return TierStore(self.root, ref.tier).get_object(ref)

    def verify(self) -> dict[str, dict[str, int]]:
        return {tier: verify_tier(self.root, tier) for tier in self._tiers}

    def _tier(self, tier: str) -> TierStore:
        if tier not in self._tiers:
            raise ValueError(f"EvaluatorStore writes only {sorted(self._tiers)}, not {tier!r}")
        return self._tiers[tier]


def verify_store(root: Path) -> dict[str, dict[str, int]]:
    """Every tier's chain, record digests, object hashes, and cross-tier
    references. Raises `StoreIntegrityError` on the first problem."""
    from ._core import TIERS
    return {tier: verify_tier(Path(root), tier) for tier in TIERS}
