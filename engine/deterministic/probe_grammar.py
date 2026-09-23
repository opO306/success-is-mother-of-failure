"""G11a: grammar v3 -- what B can say about its own probe's actions.

One sentence form, the *effect claim*:

    doing (ACT, DIR) changes SUBJECT by DELTA -- when CONDITION holds
    just before the step; otherwise SUBJECT does not change.

Nothing in it names a purpose ("move", "pick up"): only three parts, all
general.

    SUBJECT     self.x / self.y / self.energy / self.holding, or a channel of
                the cell at a *relative* offset (dx, dy) in {-1, 0, 1}^2 from
                where the probe stood before the step: "rel:+1,0:CH-44D0".
    DELTA       a signed integer. For self.x / self.y it is measured on the
                wrapping grid (the observation contract publishes the grid
                size and that it wraps -- the coordinate system is B's
                measuring tape, not something to discover), so stepping off
                one edge onto the other is +1, never -5.
    CONDITION   none, one atomic comparison, or ALL of two -- each atomic
                comparison reads one subject before the step: ">= 1" or "= 0".

Multiple effects of one action are separate claims (designer decision): B
builds an action's meaning from independent claims ("position +1", "energy
-1") rather than being handed one bundled meaning.

Scope (G11, designer decision): the probe's own actions only. The world's
own dynamics (water flowing, heat spreading) are grammar v3.1; G11 worlds
keep them still, so every observed change is the probe's.

B-facing: reads only `BlindProbeCheckpoint` values. Imports nothing from A.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .blind_probe import BlindProbeCheckpoint

FORMAT = "probe-grammar-v3"
SELF_SUBJECTS = ("self.x", "self.y", "self.energy", "self.holding")
OFFSETS = tuple((dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
OPS = (">=", "=")
MAX_CONDITIONS = 2

GRAMMAR = {
    "version": "blind-grammar-v3",
    "sentence": "doing (action, direction) changes subject by delta when condition holds before the step; "
                "otherwise the subject does not change",
    "subjects": list(SELF_SUBJECTS) + ["rel:dx,dy:channel, dx,dy in -1..1, relative to the probe before the step"],
    "delta": "signed integer; self.x/self.y measured on the published wrapping grid",
    "conditions": "none | atom | ALL(atom, atom); atom = subject before the step compared '>= 1' or '= 0'",
    "search_order": "no condition, then one, then two -- only when fewer cannot separate what happened",
    "scope": "the probe's own actions only; world dynamics are v3.1",
}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


GRAMMAR_DIGEST = _digest(GRAMMAR)


def cell_subject(dx: int, dy: int, channel: str) -> str:
    if (dx, dy) not in OFFSETS:
        raise ValueError("cell offsets are within one step")
    return f"rel:{dx:+d},{dy:+d}:{channel}"


def _check_subject(subject: str) -> None:
    if subject in SELF_SUBJECTS:
        return
    parts = subject.split(":")
    if len(parts) != 3 or parts[0] != "rel" or not parts[2]:
        raise ValueError(f"unknown subject {subject!r}")
    dx, dy = (int(v) for v in parts[1].split(","))
    if (dx, dy) not in OFFSETS:
        raise ValueError("cell offsets are within one step")


@dataclass(frozen=True)
class Geometry:
    """The published coordinate contract: grid size, and that it wraps."""
    width: int
    height: int
    wraps: bool = True


def value_of(subject: str, checkpoint: BlindProbeCheckpoint, anchor: tuple[int, int], geometry: Geometry) -> int:
    """`subject` read from `checkpoint`, with relative cells taken around
    `anchor` (the probe's position before the step)."""
    if subject in SELF_SUBJECTS:
        return checkpoint.value("probe." + subject.split(".")[1])
    _, offset, channel = subject.split(":")
    dx, dy = (int(v) for v in offset.split(","))
    x, y = anchor[0] + dx, anchor[1] + dy
    if geometry.wraps:
        x, y = x % geometry.width, y % geometry.height
    return checkpoint.value(f"cell:{x},{y}:{channel}")


def observed_delta(subject: str, before: BlindProbeCheckpoint, after: BlindProbeCheckpoint,
                   geometry: Geometry) -> int:
    anchor = before.probe[:2]
    change = value_of(subject, after, anchor, geometry) - value_of(subject, before, anchor, geometry)
    if subject in ("self.x", "self.y") and geometry.wraps:
        size = geometry.width if subject == "self.x" else geometry.height
        change %= size
        if change > size // 2:
            change -= size
    return change


@dataclass(frozen=True, order=True)
class AtomicCondition:
    subject: str
    op: str
    value: int

    def __post_init__(self) -> None:
        _check_subject(self.subject)
        if (self.op, self.value) not in ((">=", 1), ("=", 0)):
            raise ValueError("an atomic condition is '>= 1' or '= 0'")

    def holds(self, before: BlindProbeCheckpoint, geometry: Geometry) -> bool:
        value = value_of(self.subject, before, before.probe[:2], geometry)
        return value >= 1 if self.op == ">=" else value == 0

    def text(self) -> str:
        return f"{self.subject} {self.op} {self.value}"


@dataclass(frozen=True)
class EffectClaim:
    action: str
    direction: str | None
    subject: str
    delta: int
    conditions: tuple[AtomicCondition, ...] = ()
    format: str = FORMAT

    def __post_init__(self) -> None:
        _check_subject(self.subject)
        if isinstance(self.delta, bool) or not isinstance(self.delta, int) or self.delta == 0:
            raise ValueError("an effect claim names a nonzero change")
        if len(self.conditions) > MAX_CONDITIONS:
            raise ValueError("at most two conditions")
        if list(self.conditions) != sorted(set(self.conditions)):
            raise ValueError("conditions must be distinct and sorted")

    @property
    def claim_id(self) -> str:
        return "BPC-" + _digest(self.canonical())[:16]

    def canonical(self) -> dict[str, object]:
        return {"action": self.action, "conditions": [[c.subject, c.op, c.value] for c in self.conditions],
                "delta": self.delta, "direction": self.direction, "format": self.format, "subject": self.subject}

    def statement(self) -> str:
        head = f"{self.action}{'' if self.direction is None else ' ' + self.direction}: {self.subject} {self.delta:+d}"
        if not self.conditions:
            return head
        return head + " when " + " AND ".join(c.text() for c in self.conditions)

    def predicted_delta(self, before: BlindProbeCheckpoint, geometry: Geometry) -> int:
        return self.delta if all(c.holds(before, geometry) for c in self.conditions) else 0


@dataclass(frozen=True)
class Transition:
    """One step B observed: the state before, what it did, the state after."""
    arm_id: str
    step: int
    action: str
    direction: str | None
    before: BlindProbeCheckpoint
    after: BlindProbeCheckpoint


def claim_fits(claim: EffectClaim, transition: Transition, geometry: Geometry) -> bool:
    """Whether one observed step agrees with the claim. Steps of another
    action/direction say nothing about it and always fit."""
    if (transition.action, transition.direction) != (claim.action, claim.direction):
        return True
    return observed_delta(claim.subject, transition.before, transition.after, geometry) == \
        claim.predicted_delta(transition.before, geometry)


@dataclass(frozen=True)
class SealedClaim:
    """A claim committed before a test program runs -- the object sealed in a
    `PredictionSeal`. The commitment is the whole rule, checked afterwards on
    every step of the program against the states actually observed."""
    claim: EffectClaim

    def canonical(self) -> dict[str, object]:
        return {"claim": self.claim.canonical(), "kind": "probe_effect_claim"}
