"""Extract genuine state-change events from a single trace, merged across every role into one timeline.

`DivergenceChain` (B0.4) records where *two* traces differ from each other,
snapshot by snapshot -- it does not say when a value inside *one* trace
actually changed versus merely persisted. `MechanismCandidate.path` inherits
that same-value repetition (a field held steady across several observations
appears once per observation it was sampled at), which is exactly why it
cannot be walked directly as a causal sequence.

Measurement showed `(tick, phase)` cannot serve as a time coordinate either:
because the tick loop feeds one call's result state directly into the next
call, a tick N `POST_TICK` observation is reported *before* that same tick
N's `PRE_TICK` observation in actual call order, even though the names
suggest the reverse. Every ordering decision in this module therefore sorts
by `TraceSnapshot.observation_seq` alone -- the strictly increasing counter
`trace_model.run_traced` assigns in real `KernelObserver` call order.
`tick`/`phase` are carried through as descriptive metadata only.

`extract_state_changes` reports a `StateChangeEvent` only where a
(role, field)'s value actually differs from its immediately preceding
observation -- never for a value that is merely still what it was.
`build_cross_role_timeline` then merges every role's change events into one
`observation_seq`-ordered sequence and groups same-instant changes into
`AtomicChangeGroup`s, which is the structure `causal_path_builder.py` should
walk instead of any one candidate's role-local path.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .causal_kernel import KernelPhase
from .trace_model import TraceSnapshot

FORMAT = "causal-timeline-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class StateChangeEvent:
    """One (role, field) actually changing value, within a single trace, at one observed instant.

    Never emitted for a value that simply persists from the previous
    observation -- see `extract_state_changes`. `before`/`after` are the
    immediately preceding and this observation's values, not the run's
    overall first/last values. `tick`/`phase` are descriptive metadata;
    `observation_seq` is the actual time coordinate.
    """
    observation_seq: int
    tick: int
    phase: KernelPhase
    role: str
    field: str
    before: Any
    after: Any

    def canonical(self) -> dict[str, object]:
        return {"after": self.after, "before": self.before, "field": self.field, "format": FORMAT,
                "observation_seq": self.observation_seq, "phase": self.phase.value, "role": self.role,
                "tick": self.tick}


def normalize_moments(snapshots: tuple[TraceSnapshot, ...]) -> tuple[TraceSnapshot, ...]:
    """Merge adjacent-in-call-order snapshots that are truly the same physical instant into one representative.

    Two snapshots are merged only when they are adjacent by `observation_seq`
    and their full `state_digest`s agree -- never merely because their
    sampled fields happen to match: a hidden state change the current
    `TraceSpec` does not watch must not be mistaken for "nothing happened".
    The later-in-call-order snapshot is kept as the group's representative,
    arbitrarily but consistently, since both carry identical `values`.

    Snapshots with an empty `state_digest` (pre-B0.6 callers that
    constructed `TraceSnapshot` directly, without going through
    `trace_model.collect_snapshot`) are never merged with anything.
    """
    ordered = sorted(snapshots, key=lambda s: s.observation_seq)
    result: list[TraceSnapshot] = []
    for snapshot in ordered:
        if result and snapshot.state_digest and result[-1].state_digest == snapshot.state_digest:
            result[-1] = snapshot
        else:
            result.append(snapshot)
    return tuple(result)


def extract_state_changes(snapshots: tuple[TraceSnapshot, ...]) -> tuple[StateChangeEvent, ...]:
    """Walk one trace's snapshots in real observation order, emitting only genuine value changes.

    Always normalizes moments first (see `normalize_moments`) so a
    same-instant pair of observations is never read as a value reverting and
    then changing back. The very first observation for a given (role, field)
    establishes its initial value and is never itself a change event (there
    is no "before" to compare it to).
    """
    ordered = normalize_moments(snapshots)
    last_value: dict[tuple[str, str], Any] = {}
    events: list[StateChangeEvent] = []
    for snapshot in ordered:
        for role, fields in sorted(snapshot.values.items()):
            for field, value in sorted(fields.items()):
                key = (role, field)
                if key in last_value and last_value[key] != value:
                    events.append(StateChangeEvent(snapshot.observation_seq, snapshot.tick, snapshot.phase,
                                                   role, field, last_value[key], value))
                last_value[key] = value
    return tuple(events)


@dataclass(frozen=True)
class AtomicChangeGroup:
    """Every StateChangeEvent observed at exactly one `observation_seq` -- siblings, no claimed internal order.

    This is the structural unit `causal_path_builder.build_from_evidence`
    walks: consecutive groups (different `observation_seq`) may become
    edges; changes within one group never do.
    """
    observation_seq: int
    tick: int
    phase: KernelPhase
    changes: tuple[StateChangeEvent, ...]

    def __post_init__(self) -> None:
        if not self.changes:
            raise ValueError("an atomic change group needs at least one change")
        if any(c.observation_seq != self.observation_seq for c in self.changes):
            raise ValueError("all changes in a group must share the group's observation_seq")

    def canonical(self) -> dict[str, object]:
        return {"changes": [c.canonical() for c in sorted(self.changes, key=lambda c: (c.role, c.field))],
                "format": FORMAT, "observation_seq": self.observation_seq, "phase": self.phase.value,
                "tick": self.tick}


def build_cross_role_timeline(events: tuple[StateChangeEvent, ...]) -> tuple[AtomicChangeGroup, ...]:
    """Merge every role's change events into one `observation_seq`-ordered sequence of atomic groups."""
    grouped: dict[int, list[StateChangeEvent]] = {}
    for event in events:
        grouped.setdefault(event.observation_seq, []).append(event)
    ordered_seqs = sorted(grouped)
    return tuple(AtomicChangeGroup(seq, grouped[seq][0].tick, grouped[seq][0].phase, tuple(grouped[seq]))
                for seq in ordered_seqs)
