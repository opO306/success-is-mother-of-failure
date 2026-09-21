"""Owner-private, lossless A/B causal provenance tracing.

The recorder writes full snapshots and exact deltas for every A tick and stage,
plus every externally observable B boundary action. Raw vault paths are never
placed in ObservationContract or ClaimSet messages. Candidate brains receive
only separately constructed approved views.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .b_language import BoundaryEvaluation, CapabilityManifest, ClaimSet, ObservationContract
from .causal_kernel import CausalWorldState, step_causal_world
from .environment_kernel import (
    EnvironmentState,
    _change_water_phase,
    _convert_local_mineral,
    _exchange_external_energy,
    _phase,
    initial_environment_state,
    step_environment_world,
)
from .environment_spec import EnvironmentWorldSpec

FORMAT = "private-causal-provenance-v1"
GENESIS_HASH = "0" * 64


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _json_copy(value: object) -> object:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _delta(before: object, after: object, path: str = "$") -> list[dict[str, object]]:
    if type(before) is not type(after):
        return [{"after": _json_copy(after), "before": _json_copy(before), "op": "replace", "path": path}]
    if isinstance(before, Mapping):
        changes = []
        before_keys, after_keys = set(before), set(after)
        for key in sorted(before_keys - after_keys):
            changes.append({"before": _json_copy(before[key]), "op": "remove", "path": f"{path}.{key}"})
        for key in sorted(after_keys - before_keys):
            changes.append({"after": _json_copy(after[key]), "op": "add", "path": f"{path}.{key}"})
        for key in sorted(before_keys & after_keys): changes.extend(_delta(before[key], after[key], f"{path}.{key}"))
        return changes
    if isinstance(before, list):
        if before == after: return []
        return [{"after": _json_copy(after), "before": _json_copy(before), "op": "replace", "path": path}]
    if before != after:
        return [{"after": _json_copy(after), "before": _json_copy(before), "op": "replace", "path": path}]
    return []


@dataclass(frozen=True)
class TracePolicy:
    access: str = "owner-and-fixed-verifier"
    raw_visible_to_brains: bool = False
    tick_snapshots: str = "every-tick"
    stage_snapshots: str = "every-stage"
    deltas: str = "lossless"
    compression: str = "none"
    automatic_deletion: bool = False

    def canonical(self) -> dict[str, object]:
        return {"access": self.access, "automatic_deletion": self.automatic_deletion,
                "compression": self.compression, "deltas": self.deltas,
                "raw_visible_to_brains": self.raw_visible_to_brains,
                "stage_snapshots": self.stage_snapshots, "tick_snapshots": self.tick_snapshots}


@dataclass(frozen=True)
class TraceRecord:
    sequence: int
    stream: str
    kind: str
    tick: int | None
    phase: str | None
    previous_hash: str
    payload: Mapping[str, Any]
    record_hash: str

    @classmethod
    def create(cls, sequence: int, stream: str, kind: str, tick: int | None,
               phase: str | None, previous_hash: str, payload: Mapping[str, Any]) -> "TraceRecord":
        body = {"format": FORMAT, "kind": kind, "payload": dict(payload), "phase": phase,
                "previous_hash": previous_hash, "sequence": sequence, "stream": stream, "tick": tick}
        return cls(sequence, stream, kind, tick, phase, previous_hash, payload, _digest(body))

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "kind": self.kind, "payload": dict(self.payload),
                "phase": self.phase, "previous_hash": self.previous_hash,
                "record_hash": self.record_hash, "sequence": self.sequence,
                "stream": self.stream, "tick": self.tick}


def storage_pressure(path: Path) -> dict[str, object]:
    usage = shutil.disk_usage(path)
    used_percent = (usage.used * 100) // usage.total if usage.total else 100
    level = "critical" if used_percent >= 95 else ("high" if used_percent >= 85 else ("warning" if used_percent >= 70 else "ok"))
    return {"free_bytes": usage.free, "level": level, "total_bytes": usage.total,
            "used_bytes": usage.used, "used_percent_floor": used_percent}


class PrivateTraceWriter:
    def __init__(self, run_dir: Path, run_id: str, policy: TracePolicy | None = None) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.policy = policy or TracePolicy()
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.records_path = self.run_dir / "records.jsonl"
        self._handle = self.records_path.open("x", encoding="utf-8", newline="\n")
        self._sequence = 0
        self._previous_hash = GENESIS_HASH
        self._closed = False

    def append(self, stream: str, kind: str, payload: Mapping[str, Any],
               tick: int | None = None, phase: str | None = None) -> TraceRecord:
        if self._closed: raise RuntimeError("trace writer is closed")
        record = TraceRecord.create(self._sequence, stream, kind, tick, phase, self._previous_hash, payload)
        self._handle.write(json.dumps(record.canonical(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        self._handle.flush(); os.fsync(self._handle.fileno())
        self._sequence += 1; self._previous_hash = record.record_hash
        return record

    def close(self, spec_digest: str, final_state_digest: str) -> dict[str, object]:
        if self._closed: raise RuntimeError("trace writer is already closed")
        self._handle.close(); self._closed = True
        records_sha256 = hashlib.sha256(self.records_path.read_bytes()).hexdigest()
        pressure = storage_pressure(self.run_dir)
        manifest = {"access_policy": self.policy.canonical(), "final_chain_hash": self._previous_hash,
                    "final_state_digest": final_state_digest, "format": FORMAT,
                    "record_count": self._sequence, "records_file": "records.jsonl",
                    "records_sha256": records_sha256, "run_id": self.run_id,
                    "spec_digest": spec_digest, "storage_pressure": pressure}
        manifest_path = self.run_dir / "manifest.json"
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)
        return manifest


def _stage_payload(before: EnvironmentState, after: EnvironmentState) -> dict[str, object]:
    before_state, after_state = before.canonical(), after.canonical()
    changes = _delta(before_state, after_state)
    return {"after_digest": after.digest, "after_snapshot": after_state,
            "before_digest": before.digest, "delta": changes, "delta_count": len(changes)}


def trace_environment_run(spec: EnvironmentWorldSpec, writer: PrivateTraceWriter) -> EnvironmentState:
    state = initial_environment_state(spec)
    writer.append("A", "run_start", {"full_snapshot": state.canonical(), "spec_digest": spec.digest,
                                      "state_digest": state.digest}, tick=0)
    for _ in range(spec.causal_world.ticks):
        tick = state.tick + 1
        writer.append("A", "tick_start", {"full_snapshot": state.canonical(), "state_digest": state.digest}, tick=tick)
        official = step_environment_world(spec, state)
        causal = step_causal_world(spec.causal_world, state.causal)
        traced = EnvironmentState(causal, state.cells, state.energy_supplied, state.energy_removed, state.format)
        writer.append("A", "stage_commit", _stage_payload(state, traced), tick=tick, phase="causal")
        phases = list(spec.law.phase_order); start = state.tick % len(phases)
        for phase in phases[start:] + phases[:start]:
            before = traced; traced = _phase(spec, traced, phase)
            writer.append("A", "stage_commit", _stage_payload(before, traced), tick=tick, phase=phase)
        for phase, transition in (("external_energy", _exchange_external_energy),
                                  ("mineral_conversion", _convert_local_mineral),
                                  ("water_phase_change", _change_water_phase)):
            before = traced; traced = transition(spec, traced)
            writer.append("A", "stage_commit", _stage_payload(before, traced), tick=tick, phase=phase)
        if traced != official: raise AssertionError("traced stages differ from sealed A transition")
        writer.append("A", "tick_commit", {"conserved_resources": official.conserved_resources(spec),
                                             "energy_account": official.energy_account(spec),
                                             "full_snapshot": official.canonical(),
                                             "state_digest": official.digest}, tick=tick)
        state = official
    return state


def trace_b_exchange(writer: PrivateTraceWriter, manifest: CapabilityManifest,
                     challenge: ObservationContract, claim_set: ClaimSet,
                     evaluation: BoundaryEvaluation) -> None:
    if challenge.digest != claim_set.challenge_digest: raise ValueError("B claim set belongs to another challenge")
    if manifest.digest != claim_set.manifest_digest: raise ValueError("B manifest does not match claim set")
    if evaluation.challenge_digest != challenge.digest or evaluation.claim_set_digest != claim_set.digest:
        raise ValueError("B evaluation does not match challenge and claim set")
    writer.append("B", "capability_manifest", {"manifest": manifest.canonical(), "manifest_digest": manifest.digest})
    writer.append("B", "observation_contract", {"challenge": challenge.canonical(),
                                                  "challenge_digest": challenge.digest,
                                                  "raw_trace_path_disclosed": False})
    for claim in claim_set.claims:
        bridges = [item.canonical() for item in claim_set.evidence_bridges if item.claim_id == claim.claim_id]
        writer.append("B", "claim_submitted", {"claim": claim.canonical(), "evidence_bridges": bridges})
    writer.append("B", "claim_set_commit", {"claim_set_digest": claim_set.digest,
                                              "attachments": [item.canonical() for item in claim_set.attachments]})
    writer.append("B", "boundary_evaluation", {"evaluation": evaluation.canonical(),
                                                 "evaluation_digest": evaluation.digest})


def verify_trace(run_dir: Path) -> dict[str, object]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records_path = run_dir / manifest["records_file"]
    previous = GENESIS_HASH; count = 0; tick_digests: dict[int, str] = {}; current_snapshot = None
    for line in records_path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if raw["sequence"] != count: raise ValueError("trace sequence is not contiguous")
        if raw["previous_hash"] != previous: raise ValueError("trace previous hash mismatch")
        body = {key: raw[key] for key in ("format", "kind", "payload", "phase", "previous_hash", "sequence", "stream", "tick")}
        expected = _digest(body)
        if raw["record_hash"] != expected: raise ValueError("trace record hash mismatch")
        previous = expected; count += 1
        if raw["stream"] == "A" and raw["kind"] == "run_start":
            current_snapshot = raw["payload"]["full_snapshot"]
            if _digest(current_snapshot) != raw["payload"]["state_digest"]:
                raise ValueError("initial snapshot digest mismatch")
        elif raw["stream"] == "A" and raw["kind"] == "tick_start":
            snapshot = raw["payload"]["full_snapshot"]
            if current_snapshot != snapshot or _digest(snapshot) != raw["payload"]["state_digest"]:
                raise ValueError("tick start snapshot continuity mismatch")
        elif raw["stream"] == "A" and raw["kind"] == "stage_commit":
            if current_snapshot is None: raise ValueError("stage has no preceding snapshot")
            payload = raw["payload"]; after_snapshot = payload["after_snapshot"]
            expected_delta = _delta(current_snapshot, after_snapshot)
            if _digest(current_snapshot) != payload["before_digest"]:
                raise ValueError("stage before digest mismatch")
            if _digest(after_snapshot) != payload["after_digest"]:
                raise ValueError("stage after digest mismatch")
            if payload["delta"] != expected_delta or payload["delta_count"] != len(expected_delta):
                raise ValueError("stage delta does not reconstruct the snapshot")
            current_snapshot = after_snapshot
        elif raw["stream"] == "A" and raw["kind"] == "tick_commit":
            snapshot = raw["payload"]["full_snapshot"]
            if current_snapshot != snapshot or _digest(snapshot) != raw["payload"]["state_digest"]:
                raise ValueError("tick commit snapshot continuity mismatch")
            tick_digests[int(raw["tick"])] = raw["payload"]["state_digest"]
    if count != manifest["record_count"]: raise ValueError("trace record count mismatch")
    if previous != manifest["final_chain_hash"]: raise ValueError("trace final chain hash mismatch")
    if hashlib.sha256(records_path.read_bytes()).hexdigest() != manifest["records_sha256"]:
        raise ValueError("trace file SHA-256 mismatch")
    if tick_digests and tick_digests[max(tick_digests)] != manifest["final_state_digest"]:
        raise ValueError("trace final state digest mismatch")
    return {"final_chain_hash": previous, "record_count": count, "tick_digests": tick_digests,
            "records_sha256": manifest["records_sha256"], "valid": True}
