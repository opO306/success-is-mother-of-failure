"""Append-only, hash-chained journal: the authoritative history of a B0 research run.

Mirrors the hash-chain discipline in `provenance.py` (`previous_hash` +
`record_hash` per line, verified by replay) but journals *research* events --
observations, hypotheses, seals, execution results, anomalies, accidents,
status changes -- rather than A tick-by-tick provenance. `ResearchState` is
never stored directly: it is always rebuilt by folding this journal from the
beginning, so "read the journal back and reconstruct the same state" is the
correctness property this file exists to make checkable.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

FORMAT = "b0-research-journal-v1"
GENESIS_DIGEST = "0" * 64

EVENT_TYPES = frozenset({
    # B0.1 events -- kept unchanged so old journals keep replaying identically.
    "observation_recorded", "hypothesis_set_created", "portfolio_designed",
    "prediction_sealed", "execution_completed", "result_compared",
    "hypothesis_status_changed", "anomaly_recorded", "accident_recorded",
    # B0.2 events -- structured memory: domains, evidence, lineage, contradictions.
    "domain_registered", "hypothesis_domain_linked", "domain_evidence_recorded",
    "hypothesis_edge_added", "contradiction_detected", "contradiction_status_changed",
    "anomaly_status_changed", "accident_status_changed",
    # B0.4 events -- deep investigation: divergence tracing and mechanism candidates.
    "investigation_target_sealed", "divergence_chain_recorded", "mechanism_candidates_proposed",
    "followup_experiment_proposed",
    # B0.5 events -- mechanism testing: feasibility, executed interventions, evidence.
    "mechanism_test_planned", "intervention_feasibility_checked", "mechanism_test_executed",
    "mechanism_evidence_recorded",
    # B0.6 events -- causal path building: edges, atomic co-occurring events, paths, missing links.
    "atomic_event_recorded", "causal_edge_proposed", "causal_edge_rejected", "causal_edge_updated",
    "missing_link_recorded", "causal_path_created", "causal_path_updated",
    # B0.7 events -- missing link investigation: hypotheses, follow-up requests, results.
    "missing_link_investigation_sealed", "missing_link_hypothesis_proposed", "missing_link_result_recorded",
    "observation_request_submitted", "mechanism_test_request_submitted", "instrumentation_request_submitted",
    # G6d event -- autonomous experiment design: which candidate was ranked/selected, and why.
    "experiment_candidate_ranked",
    # G7.2 event -- blind protocol: B's terminal answer for one blind research
    # journal, sealed before any evaluator appears. See blind_protocol.py.
    "final_discovery_sealed",
})


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class JournalEntry:
    """One envelope in the journal: every event carries the same shape.

    `record_digest` covers `previous_digest` too, so entries form a hash
    chain identical in spirit to `provenance.TraceRecord` -- tampering with or
    reordering an old entry is detectable by replay, not just by inspection.
    """
    sequence: int
    event_type: str
    record_id: str
    previous_digest: str
    payload: Mapping[str, Any]
    record_digest: str

    @classmethod
    def create(cls, sequence: int, event_type: str, record_id: str,
               previous_digest: str, payload: Mapping[str, Any]) -> "JournalEntry":
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported journal event type {event_type!r}")
        body = {"event_type": event_type, "format": FORMAT, "payload": dict(payload),
                "previous_digest": previous_digest, "record_id": record_id, "sequence": sequence}
        return cls(sequence, event_type, record_id, previous_digest, payload, _digest(body))

    def canonical(self) -> dict[str, object]:
        return {"event_type": self.event_type, "format": FORMAT, "payload": dict(self.payload),
                "previous_digest": self.previous_digest, "record_digest": self.record_digest,
                "record_id": self.record_id, "sequence": self.sequence}


class ResearchJournal:
    """An append-only JSONL file, opened for a single research run.

    One instance either creates a fresh journal (`path` must not exist) or
    reopens an existing one to keep appending (`ResearchJournal.open`), which
    replays it first to recover the hash chain's tail and the next sequence
    number.
    """

    def __init__(self, path: Path, *, _sequence: int = 0, _previous_digest: str = GENESIS_DIGEST,
                _handle=None) -> None:
        self.path = path
        self._sequence = _sequence
        self._previous_digest = _previous_digest
        self._handle = _handle if _handle is not None else path.open("a", encoding="utf-8", newline="\n")

    @classmethod
    def create(cls, path: Path) -> "ResearchJournal":
        if path.exists():
            raise FileExistsError(f"journal already exists at {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("x", encoding="utf-8", newline="\n")
        return cls(path, _handle=handle)

    @classmethod
    def open(cls, path: Path) -> "ResearchJournal":
        entries = read_journal(path)
        sequence = entries[-1].sequence + 1 if entries else 0
        previous = entries[-1].record_digest if entries else GENESIS_DIGEST
        handle = path.open("a", encoding="utf-8", newline="\n")
        return cls(path, _sequence=sequence, _previous_digest=previous, _handle=handle)

    def append(self, event_type: str, record_id: str, payload: Mapping[str, Any]) -> JournalEntry:
        entry = JournalEntry.create(self._sequence, event_type, record_id, self._previous_digest, payload)
        self._handle.write(json.dumps(entry.canonical(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._sequence += 1
        self._previous_digest = entry.record_digest
        return entry

    @property
    def next_sequence(self) -> int:
        return self._sequence

    def close(self) -> None:
        self._handle.close()


def read_journal(path: Path) -> tuple[JournalEntry, ...]:
    if not path.exists():
        return ()
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        entries.append(JournalEntry(raw["sequence"], raw["event_type"], raw["record_id"],
                                    raw["previous_digest"], raw["payload"], raw["record_digest"]))
    return tuple(entries)


def verify_journal(path: Path) -> dict[str, object]:
    """Replay the hash chain from genesis and confirm every link holds."""
    previous = GENESIS_DIGEST
    count = 0
    for entry in read_journal(path):
        if entry.sequence != count:
            raise ValueError("journal sequence is not contiguous")
        if entry.previous_digest != previous:
            raise ValueError("journal previous-digest mismatch")
        body = {"event_type": entry.event_type, "format": FORMAT, "payload": dict(entry.payload),
                "previous_digest": entry.previous_digest, "record_id": entry.record_id, "sequence": entry.sequence}
        if entry.record_digest != _digest(body):
            raise ValueError("journal record digest mismatch")
        previous = entry.record_digest
        count += 1
    return {"final_digest": previous, "record_count": count, "valid": True}
