"""Trusted broker for deriving B-visible change views from owner-private traces."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .environment_spec import EnvironmentWorldSpec
from .provenance import verify_trace


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApprovedChangeEvent:
    event_id: str
    tick: int
    phase: str
    before_digest: str
    after_digest: str
    delta: tuple[Mapping[str, Any], ...]
    source_record_hash: str

    def canonical(self) -> dict[str, object]:
        return {"after_digest": self.after_digest, "before_digest": self.before_digest,
                "delta": [dict(x) for x in self.delta], "event_id": self.event_id,
                "phase": self.phase, "source_record_hash": self.source_record_hash, "tick": self.tick}


@dataclass(frozen=True)
class ApprovedChangeView:
    spec_digest: str
    initial_state_digest: str
    initial_snapshot: Mapping[str, Any]
    target_tick: int
    events: tuple[ApprovedChangeEvent, ...]
    width: int
    height: int
    solute_kinds: int
    blocked_edges: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    source_chain_hash: str
    source_records_sha256: str
    allowed_content: tuple[str, ...]
    hidden_content: tuple[str, ...]

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"allowed_content": list(self.allowed_content),
                "blocked_edges": [[list(a), list(b)] for a, b in self.blocked_edges],
                "events": [x.canonical() for x in self.events],
                "format": "approved-change-view-v1", "height": self.height,
                "hidden_content": list(self.hidden_content),
                "initial_snapshot": dict(self.initial_snapshot), "initial_state_digest": self.initial_state_digest,
                "solute_kinds": self.solute_kinds,
                "source_chain_hash": self.source_chain_hash,
                "source_records_sha256": self.source_records_sha256,
                "spec_digest": self.spec_digest, "target_tick": self.target_tick, "width": self.width}


def build_approved_change_view(run_dir: Path, spec: EnvironmentWorldSpec,
                               target_tick: int) -> ApprovedChangeView:
    """Trusted operation: read raw trace, verify it, and return a path-free derived view."""
    if isinstance(target_tick, bool) or not isinstance(target_tick, int) or target_tick < 0:
        raise ValueError("target_tick must be a nonnegative integer")
    verification = verify_trace(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["spec_digest"] != spec.digest: raise ValueError("trace and specification digests differ")
    records = [json.loads(line) for line in (run_dir / manifest["records_file"]).read_text(encoding="utf-8").splitlines()]
    run_start = next((x for x in records if x["stream"] == "A" and x["kind"] == "run_start"), None)
    if run_start is None: raise ValueError("trace has no A run_start")
    commits = {int(x["tick"]) for x in records if x["stream"] == "A" and x["kind"] == "tick_commit"}
    if target_tick and target_tick not in commits: raise ValueError("target tick is not committed in the trace")
    events = []
    for raw in records:
        if raw["stream"] != "A" or raw["kind"] != "stage_commit" or int(raw["tick"]) > target_tick:
            continue
        payload = raw["payload"]
        events.append(ApprovedChangeEvent(
            f"a-stage-{raw['sequence']}", int(raw["tick"]), str(raw["phase"]),
            payload["before_digest"], payload["after_digest"],
            tuple(dict(item) for item in payload["delta"]), raw["record_hash"],
        ))
    return ApprovedChangeView(
        spec.digest, run_start["payload"]["state_digest"], run_start["payload"]["full_snapshot"],
        target_tick, tuple(events), spec.causal_world.kernel.width, spec.causal_world.kernel.height,
        spec.solute_kinds, tuple((edge.first, edge.second) for edge in spec.blocked_edges),
        verification["final_chain_hash"], verification["records_sha256"],
        ("initial_snapshot", "stage_deltas_through_target_tick", "topology_from_sealed_spec"),
        ("raw_vault_path", "B_records", "A_records_after_target_tick", "full_stage_snapshots_after_initial"),
    )
