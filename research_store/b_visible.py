"""The b_visible tier: only data B itself could have seen -- alias ids, its
own hypotheses, predictions, observations, verdicts. The only module in
`research_store` that B-side code, or a future learned B's training loader,
may import.

Two guarantees, both structural rather than by convention:

* This module binds to the b_visible directory and nothing else. It never
  imports `research_store.evaluator`, and no function here takes a tier
  argument -- there is no parameter a caller could flip to reach
  evaluator or ground-truth data (tests check the import closure).
* Every write is scanned for the secrets of the world it came from
  (`forbidden_values` -- real world id, revision, real variable names, real
  spec digest), passed by the evaluator-side ingest that knows them. A hit
  refuses the write: leaked data never lands in the one tier meant to be
  safe to train on. `forbidden_values` is required and must be non-empty,
  so a caller cannot skip the scan by forgetting it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ._core import (
    B_VISIBLE, ObjectRef, StoreRecord, TierStore, canonical_bytes, require_single_semantics, verify_tier,
)


class LeakageError(ValueError):
    """A value bound for the b_visible tier contains a secret of its world."""


def _scan(value: Any, forbidden_values: tuple[str, ...]) -> None:
    if not isinstance(forbidden_values, tuple) or not forbidden_values or \
            not all(isinstance(v, str) and v for v in forbidden_values):
        raise ValueError("forbidden_values must be a non-empty tuple of non-empty text")
    text = canonical_bytes(value).decode("utf-8")
    hits = sorted(v for v in forbidden_values if v in text)
    if hits:
        raise LeakageError(f"refusing b_visible write: contains {len(hits)} forbidden value(s)")


class BVisibleWriter:
    def __init__(self, root: Path) -> None:
        self._store = TierStore(root, B_VISIBLE)

    def put(self, value: Any, *, forbidden_values: tuple[str, ...]) -> ObjectRef:
        _scan(value, forbidden_values)
        return self._store.put_object(value)

    def record(self, record_type: str, schema_version: int, provenance: Mapping[str, Any],
               tags: Mapping[str, str], payload: ObjectRef, refs: tuple[ObjectRef, ...] = (), *,
               forbidden_values: tuple[str, ...]) -> StoreRecord:
        _scan({"provenance": dict(provenance), "record_type": record_type, "tags": dict(tags)}, forbidden_values)
        return self._store.append_record(record_type, schema_version, provenance, tags, payload, refs)


class BVisibleReader:
    def __init__(self, root: Path) -> None:
        self._store = TierStore(root, B_VISIBLE)

    def records(self, record_type: str, *, semantics: str) -> list[StoreRecord]:
        """Records of one type under one named semantics. `semantics` has
        no default on purpose: mixing results produced under different
        rules must be a decision someone wrote down, never the default."""
        return [r for r in self._store.records() if r.record_type == record_type and r.semantics == semantics]

    def all_records(self) -> list[StoreRecord]:
        return list(self._store.records())

    def get(self, ref: ObjectRef) -> Any:
        return self._store.get_object(ref)

    def verify(self) -> dict[str, int]:
        return verify_tier(self._store.root, B_VISIBLE)


__all__ = ["BVisibleReader", "BVisibleWriter", "LeakageError", "require_single_semantics"]
