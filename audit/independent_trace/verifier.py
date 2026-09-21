"""Independent verification of a private causal provenance trace.

This is a second opinion on `engine.deterministic.provenance.verify_trace`.
It shares no code with it. Where the engine regenerates and compares, this
reconstructs and applies. Where the engine relies on `json.dumps` for its
canonical form, this emits canonical bytes from stated rules.

Every finding is collected rather than raised, so one run reports everything
it can see instead of stopping at the first disagreement.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .canonical import CanonicalError, digest
from .delta import DeltaError, apply_delta

FORMAT = "private-causal-provenance-v1"
GENESIS_HASH = "0" * 64
_BODY_KEYS = ("format", "kind", "payload", "phase", "previous_hash", "sequence", "stream", "tick")


@dataclass
class Finding:
    """One disagreement, located precisely enough to act on."""

    code: str
    detail: str
    sequence: int | None = None
    tick: int | None = None

    def canonical(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail,
                "sequence": self.sequence, "tick": self.tick}


@dataclass
class IndependentVerification:
    run_dir: str
    record_count: int = 0
    final_chain_hash: str = GENESIS_HASH
    records_sha256: str = ""
    tick_digests: dict[int, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.findings

    def canonical(self) -> dict[str, Any]:
        return {"final_chain_hash": self.final_chain_hash,
                "findings": [item.canonical() for item in self.findings],
                "record_count": self.record_count,
                "records_sha256": self.records_sha256,
                "run_dir": self.run_dir,
                "tick_digests": {str(k): v for k, v in sorted(self.tick_digests.items())},
                "valid": self.valid}


def _record_hash(raw: dict[str, Any]) -> str:
    return digest({key: raw[key] for key in _BODY_KEYS})


def verify_trace_independently(run_dir: Path) -> IndependentVerification:
    """Check a trace directory without using any engine code."""
    run_dir = Path(run_dir)
    result = IndependentVerification(run_dir=str(run_dir))

    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        result.findings.append(Finding("manifest_missing", f"no manifest.json in {run_dir}"))
        return result
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        result.findings.append(Finding("manifest_unreadable", str(error)))
        return result

    if manifest.get("format") != FORMAT:
        result.findings.append(
            Finding("format_unexpected", f"manifest format is {manifest.get('format')!r}"))

    records_path = run_dir / manifest.get("records_file", "records.jsonl")
    if not records_path.is_file():
        result.findings.append(Finding("records_missing", f"no {records_path.name}"))
        return result

    raw_bytes = records_path.read_bytes()
    result.records_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if result.records_sha256 != manifest.get("records_sha256"):
        result.findings.append(Finding(
            "records_sha256_mismatch",
            f"file is {result.records_sha256}, manifest says {manifest.get('records_sha256')}"))

    previous = GENESIS_HASH
    snapshot: Any = None
    for index, line in enumerate(raw_bytes.decode("utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            result.findings.append(Finding("record_unparsable", str(error), sequence=index))
            return result

        sequence = raw.get("sequence")
        tick = raw.get("tick")

        if sequence != index:
            result.findings.append(Finding(
                "sequence_not_contiguous", f"expected {index}, found {sequence!r}",
                sequence=index, tick=tick))
        if raw.get("previous_hash") != previous:
            result.findings.append(Finding(
                "chain_broken",
                f"record links to {raw.get('previous_hash')}, previous record hashed to {previous}",
                sequence=sequence, tick=tick))

        missing = [key for key in _BODY_KEYS if key not in raw]
        if missing:
            result.findings.append(Finding(
                "record_incomplete", f"missing {', '.join(missing)}", sequence=sequence, tick=tick))
            return result

        try:
            expected = _record_hash(raw)
        except CanonicalError as error:
            result.findings.append(Finding(
                "record_not_canonical", str(error), sequence=sequence, tick=tick))
            return result
        if raw.get("record_hash") != expected:
            result.findings.append(Finding(
                "record_hash_mismatch",
                f"stored {raw.get('record_hash')}, independently computed {expected}",
                sequence=sequence, tick=tick))
        previous = expected
        result.record_count += 1

        payload = raw.get("payload") or {}
        stream, kind = raw.get("stream"), raw.get("kind")
        if stream != "A":
            continue

        if kind == "run_start":
            snapshot = payload.get("full_snapshot")
            _check_snapshot_digest(result, snapshot, payload.get("state_digest"), sequence, tick,
                                   "initial_snapshot_digest_mismatch")
        elif kind == "tick_start":
            recorded = payload.get("full_snapshot")
            if snapshot is not None and recorded != snapshot:
                result.findings.append(Finding(
                    "tick_start_discontinuous",
                    "tick start snapshot differs from the running reconstruction",
                    sequence=sequence, tick=tick))
            _check_snapshot_digest(result, recorded, payload.get("state_digest"), sequence, tick,
                                   "tick_start_digest_mismatch")
            snapshot = recorded
        elif kind == "stage_commit":
            snapshot = _check_stage(result, snapshot, payload, sequence, tick)
        elif kind == "tick_commit":
            recorded = payload.get("full_snapshot")
            if snapshot is not None and recorded != snapshot:
                result.findings.append(Finding(
                    "tick_commit_discontinuous",
                    "tick commit snapshot differs from the applied-delta reconstruction",
                    sequence=sequence, tick=tick))
            _check_snapshot_digest(result, recorded, payload.get("state_digest"), sequence, tick,
                                   "tick_commit_digest_mismatch")
            snapshot = recorded
            if isinstance(tick, int) and isinstance(payload.get("state_digest"), str):
                result.tick_digests[tick] = payload["state_digest"]

    result.final_chain_hash = previous

    if result.record_count != manifest.get("record_count"):
        result.findings.append(Finding(
            "record_count_mismatch",
            f"counted {result.record_count}, manifest says {manifest.get('record_count')}"))
    if previous != manifest.get("final_chain_hash"):
        result.findings.append(Finding(
            "final_chain_hash_mismatch",
            f"computed {previous}, manifest says {manifest.get('final_chain_hash')}"))
    if result.tick_digests:
        last = result.tick_digests[max(result.tick_digests)]
        declared = manifest.get("final_state_digest")
        if declared != last and declared != "experiment-not-run":
            result.findings.append(Finding(
                "final_state_digest_mismatch",
                f"last tick digest is {last}, manifest says {declared}"))
    return result


def _check_snapshot_digest(result: IndependentVerification, snapshot: Any, declared: Any,
                           sequence: int | None, tick: int | None, code: str) -> None:
    if snapshot is None:
        result.findings.append(Finding(code, "snapshot is absent", sequence=sequence, tick=tick))
        return
    try:
        computed = digest(snapshot)
    except CanonicalError as error:
        result.findings.append(Finding(
            "snapshot_not_canonical", str(error), sequence=sequence, tick=tick))
        return
    if computed != declared:
        result.findings.append(Finding(
            code, f"stored {declared}, independently computed {computed}",
            sequence=sequence, tick=tick))


def _check_stage(result: IndependentVerification, snapshot: Any, payload: dict[str, Any],
                 sequence: int | None, tick: int | None) -> Any:
    after = payload.get("after_snapshot")
    if snapshot is None:
        result.findings.append(Finding(
            "stage_without_snapshot", "stage commit has no preceding snapshot",
            sequence=sequence, tick=tick))
        return after

    _check_snapshot_digest(result, snapshot, payload.get("before_digest"), sequence, tick,
                           "stage_before_digest_mismatch")
    _check_snapshot_digest(result, after, payload.get("after_digest"), sequence, tick,
                           "stage_after_digest_mismatch")

    changes = payload.get("delta")
    declared_count = payload.get("delta_count")
    if isinstance(changes, list) and declared_count != len(changes):
        result.findings.append(Finding(
            "delta_count_mismatch",
            f"delta has {len(changes)} entries, delta_count says {declared_count}",
            sequence=sequence, tick=tick))

    # The engine regenerates the delta and compares. Here the recorded delta is
    # applied instead: a wrongly computed delta fails to rebuild its successor.
    try:
        rebuilt = apply_delta(snapshot, changes if isinstance(changes, list) else [])
    except DeltaError as error:
        result.findings.append(Finding(
            "delta_not_applicable", str(error), sequence=sequence, tick=tick))
        return after
    if rebuilt != after:
        result.findings.append(Finding(
            "delta_does_not_reconstruct",
            "applying the recorded delta to the before-snapshot did not yield after_snapshot",
            sequence=sequence, tick=tick))
    return after
