"""Tier-agnostic mechanics of the research store. Private: callers go through
`b_visible.py` or `evaluator.py`, which each bind to fixed tiers.

On disk, one directory per tier -- the tier boundary is a directory boundary,
not a tag on a shared file:

    <root>/<tier>/objects/<h[:2]>/<h>.json   content-addressed payloads
    <root>/<tier>/index.jsonl                append-only, hash-chained records

* Objects are named by the sha256 of their canonical JSON. Writing the same
  content twice stores it once; a file whose content no longer matches its
  name is corruption, detected by `verify_tier`.
* Records are never edited or deleted. A correction is a new record. Each
  record carries the digest of the one before it, so a removed, reordered,
  or edited line breaks the chain.
* A record may only reference objects in its own tier or in a tier *less*
  secret than itself (evaluator may point at b_visible; b_visible may point
  at nothing else). Checked on write and again by `verify_tier`.

Single writer per tier at a time is assumed (no file lock). This is
bookkeeping integrity, not an OS sandbox: a process that opens the
evaluator directory by hand can read it. What is enforced is that the
b_visible *module* has no code path to another tier, and B-side code
cannot import anything else from this package (checked by tests).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

B_VISIBLE = "b_visible"
EVALUATOR = "evaluator"
GROUND_TRUTH = "ground_truth"
TIERS = (B_VISIBLE, EVALUATOR, GROUND_TRUTH)
# A tier may reference objects in tiers at or below its own secrecy level.
_SECRECY = {B_VISIBLE: 0, EVALUATOR: 1, GROUND_TRUTH: 2}

RECORD_FORMAT = "research-store-record-v1"
GENESIS_DIGEST = "0" * 64


class StoreIntegrityError(RuntimeError):
    """The store on disk does not match what it claims (hash, chain, refs)."""


class SemanticsMismatchError(ValueError):
    """Records produced under different research semantics were mixed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _check_tier(tier: str) -> str:
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}")
    return tier


@dataclass(frozen=True)
class ObjectRef:
    tier: str
    object_hash: str

    def canonical(self) -> dict[str, str]:
        return {"object_hash": self.object_hash, "tier": self.tier}


@dataclass(frozen=True)
class StoreRecord:
    sequence: int
    record_type: str
    schema_version: int
    tier: str
    provenance: Mapping[str, Any]
    tags: Mapping[str, str]
    payload: ObjectRef
    refs: tuple[ObjectRef, ...]
    previous_digest: str
    record_digest: str

    def body(self) -> dict[str, Any]:
        return {"format": RECORD_FORMAT, "payload": self.payload.canonical(),
                "previous_digest": self.previous_digest, "provenance": dict(self.provenance),
                "record_type": self.record_type, "refs": [r.canonical() for r in self.refs],
                "schema_version": self.schema_version, "sequence": self.sequence,
                "tags": dict(self.tags), "tier": self.tier}

    def canonical(self) -> dict[str, Any]:
        return {**self.body(), "record_digest": self.record_digest}

    @property
    def semantics(self) -> str:
        return str(self.provenance.get("semantics"))


def _record_from_line(line: str) -> StoreRecord:
    raw = json.loads(line)
    return StoreRecord(
        sequence=raw["sequence"], record_type=raw["record_type"], schema_version=raw["schema_version"],
        tier=raw["tier"], provenance=raw["provenance"], tags=raw["tags"],
        payload=ObjectRef(**raw["payload"]), refs=tuple(ObjectRef(**r) for r in raw["refs"]),
        previous_digest=raw["previous_digest"], record_digest=raw["record_digest"])


class TierStore:
    """Read/write access to exactly one tier directory."""

    def __init__(self, root: Path, tier: str) -> None:
        self.root = Path(root)
        self.tier = _check_tier(tier)
        self.directory = self.root / tier
        self.index_path = self.directory / "index.jsonl"

    # -- objects ---------------------------------------------------------
    def _object_path(self, object_hash: str) -> Path:
        return self.directory / "objects" / object_hash[:2] / f"{object_hash}.json"

    def put_object(self, value: Any) -> ObjectRef:
        data = canonical_bytes(value)
        object_hash = hashlib.sha256(data).hexdigest()
        path = self._object_path(object_hash)
        if path.exists():
            if path.read_bytes() != data:
                raise StoreIntegrityError(f"object {object_hash} exists with different content")
            return ObjectRef(self.tier, object_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_bytes(data)
        os.replace(temp, path)
        return ObjectRef(self.tier, object_hash)

    def get_object(self, ref: ObjectRef) -> Any:
        if ref.tier != self.tier:
            raise ValueError(f"object lives in tier {ref.tier!r}, this store is {self.tier!r}")
        data = self._object_path(ref.object_hash).read_bytes()
        if hashlib.sha256(data).hexdigest() != ref.object_hash:
            raise StoreIntegrityError(f"object {ref.object_hash} content does not match its name")
        return json.loads(data)

    def has_object(self, ref: ObjectRef) -> bool:
        return ref.tier == self.tier and self._object_path(ref.object_hash).exists()

    # -- records ---------------------------------------------------------
    def records(self) -> Iterator[StoreRecord]:
        if not self.index_path.exists():
            return
        with self.index_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield _record_from_line(line)

    def _tail(self) -> tuple[int, str]:
        last = None
        for last in self.records():
            pass
        return (0, GENESIS_DIGEST) if last is None else (last.sequence + 1, last.record_digest)

    def append_record(self, record_type: str, schema_version: int, provenance: Mapping[str, Any],
                      tags: Mapping[str, str], payload: ObjectRef, refs: tuple[ObjectRef, ...] = ()) -> StoreRecord:
        if not isinstance(record_type, str) or not record_type:
            raise ValueError("record_type must be non-empty text")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version < 1:
            raise ValueError("schema_version must be a positive integer")
        if not provenance.get("semantics"):
            raise ValueError("provenance must name the research semantics the record was produced under")
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in tags.items()):
            raise ValueError("tags must map text to text")
        for ref in (payload, *refs):
            if _SECRECY[_check_tier(ref.tier)] > _SECRECY[self.tier]:
                raise ValueError(f"a {self.tier} record may not reference a {ref.tier} object")
            if not TierStore(self.root, ref.tier).has_object(ref):
                raise StoreIntegrityError(f"referenced object {ref.object_hash} missing from tier {ref.tier}")
        if payload.tier != self.tier:
            raise ValueError("a record's own payload must live in its own tier")
        sequence, previous = self._tail()
        draft = StoreRecord(sequence, record_type, schema_version, self.tier, dict(provenance), dict(tags),
                            payload, tuple(refs), previous, "")
        record = StoreRecord(**{**draft.__dict__, "record_digest": digest(draft.body())})
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.canonical(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record


def verify_tier(root: Path, tier: str) -> dict[str, int]:
    """Recompute every record digest, the chain, every referenced object's
    hash, and the cross-tier rule. Raises `StoreIntegrityError` on the first
    problem; returns counts when the tier is sound."""
    store = TierStore(root, tier)
    previous, expected_sequence, count = GENESIS_DIGEST, 0, 0
    referenced: set[tuple[str, str]] = set()
    for record in store.records():
        if record.tier != tier:
            raise StoreIntegrityError(f"record {record.sequence} claims tier {record.tier!r} inside {tier!r}")
        if record.sequence != expected_sequence:
            raise StoreIntegrityError(f"sequence gap at {record.sequence}, expected {expected_sequence}")
        if record.previous_digest != previous:
            raise StoreIntegrityError(f"chain broken at record {record.sequence}")
        if digest(record.body()) != record.record_digest:
            raise StoreIntegrityError(f"record {record.sequence} was edited")
        for ref in (record.payload, *record.refs):
            if _SECRECY[ref.tier] > _SECRECY[tier]:
                raise StoreIntegrityError(f"record {record.sequence} references more-secret tier {ref.tier}")
            TierStore(root, ref.tier).get_object(ref)  # raises on missing/corrupt
            referenced.add((ref.tier, ref.object_hash))
        previous, expected_sequence, count = record.record_digest, expected_sequence + 1, count + 1
    objects = 0
    objects_dir = store.directory / "objects"
    if objects_dir.exists():
        for path in objects_dir.rglob("*.json"):
            objects += 1
            if hashlib.sha256(path.read_bytes()).hexdigest() != path.stem:
                raise StoreIntegrityError(f"object {path.stem} content does not match its name")
    return {"records": count, "objects": objects, "referenced": len(referenced)}


def require_single_semantics(records: list[StoreRecord]) -> str:
    """The semantics every record in `records` shares; raises if they differ.
    Results produced under different research semantics (e.g. before and
    after G7.3b-4's tick rule) must never be aggregated silently."""
    found = sorted({r.semantics for r in records})
    if len(found) > 1:
        raise SemanticsMismatchError(f"records span several semantics: {found}")
    if not found:
        raise ValueError("no records")
    return found[0]
