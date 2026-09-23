"""G11d: B designs its own severe test for a conditional claim.

Measured in the wall world (G11c): a coincidence can pass every test in a
fixed pool. MOVE E failed only at the start cell, which was also the only
cell B had ever stood on without heat under it (arriving deposits heat), so
"moves east *when the cell underfoot is warm*" fitted everything -- and no
alternation program ever warmed the start cell and then moved east. A human
scientist would design that experiment on purpose: "if warmth is the reason,
warm the start cell and try again."

That is what this module does, from B's own material only:

    1. B's claims are a model. Starting from the initial state B observed
       (every run starts there), it predicts what each step would do:
       every claim whose conditions hold applies its change.
    2. For a claim that has failed somewhere (it has conditions because of
       those failures), B searches short step prefixes (breadth-first,
       deterministic order) for a state where the claim *predicts success*
       yet which is as close as possible to a state where it *was seen to
       fail* -- closeness = how many observed quantities differ (absolute
       position, own state, the 3x3 cells around).
    3. The program is that prefix followed by the claim's action. It is
       sealed like any test; if the claim was a coincidence, the world
       refutes it and refinement looks again.

A prediction of the model can itself be wrong (the prefix may not reach
the planned state); the test is still a real sealed test -- only the
planned closeness is lost. Nothing here reads A; it imports only the
grammar and B's observation types.

B-facing: imports only `probe_grammar` and `blind_probe`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .blind_probe import BlindProbeCheckpoint
from .probe_grammar import SELF_SUBJECTS, AtomicCondition, EffectClaim, Geometry, Transition, observed_delta, value_of

MAX_PREFIX = 3


def _cell_key(subject: str, anchor: tuple[int, int], geometry: Geometry) -> tuple[int, int, str]:
    _, offset, channel = subject.split(":")
    dx, dy = (int(v) for v in offset.split(","))
    x, y = anchor[0] + dx, anchor[1] + dy
    if geometry.wraps:
        x, y = x % geometry.width, y % geometry.height
    return x, y, channel


def predict(claims: Iterable[EffectClaim], before: BlindProbeCheckpoint, action: str, direction: str | None,
            geometry: Geometry) -> BlindProbeCheckpoint:
    """B's model of one step: every claim for this action whose conditions
    hold before the step applies its change; everything else stays."""
    probe = list(before.probe)
    cells = {(x, y, ch): v for x, y, ch, v in before.cells}
    anchor = before.probe[:2]
    for claim in claims:
        if (claim.action, claim.direction) != (action, direction) or not claim.predicted_delta(before, geometry):
            continue
        if claim.subject in SELF_SUBJECTS:
            i = SELF_SUBJECTS.index(claim.subject)
            probe[i] += claim.delta
            if i < 2 and geometry.wraps:
                probe[i] %= geometry.width if i == 0 else geometry.height
        else:
            key = _cell_key(claim.subject, anchor, geometry)
            cells[key] = cells.get(key, 0) + claim.delta
    return BlindProbeCheckpoint(before.tick + 1, tuple(probe),
                                tuple(sorted((x, y, ch, v) for (x, y, ch), v in cells.items() if v)))


def features(state: BlindProbeCheckpoint, subjects: Sequence[str], geometry: Geometry) -> tuple:
    """What B compares when it asks "how close is this to that": absolute
    position plus every grammar subject read around the probe."""
    anchor = state.probe[:2]
    return anchor + tuple(value_of(s, state, anchor, geometry) for s in subjects)


@dataclass(frozen=True)
class SevereTest:
    steps: tuple[tuple[str, str | None], ...]     # prefix + the claim's action
    distance: int                                 # quantities differing from the nearest failure


def failures(claim: EffectClaim, transitions: Iterable[Transition], geometry: Geometry) -> list[BlindProbeCheckpoint]:
    return [t.before for t in transitions if (t.action, t.direction) == (claim.action, claim.direction)
            and observed_delta(claim.subject, t.before, t.after, geometry) == 0]


@dataclass(frozen=True)
class Reachable:
    """A state B's model says one program prefix reaches from the start."""
    prefix: tuple[tuple[str, str | None], ...]
    state: BlindProbeCheckpoint
    features: tuple


def reachable(model: Sequence[EffectClaim], initial: BlindProbeCheckpoint,
              options: Sequence[tuple[str, str | None]], subjects: Sequence[str], geometry: Geometry,
              max_prefix: int = MAX_PREFIX) -> list[Reachable]:
    """Breadth-first, deterministic order, each distinct predicted state
    once (at its shortest prefix). Depends only on the model, so the loop
    computes it once per claim set and reuses it for every claim."""
    by_option: dict[tuple[str, str | None], list[EffectClaim]] = {}
    for claim in model:
        by_option.setdefault((claim.action, claim.direction), []).append(claim)
    out = [Reachable((), initial, features(initial, subjects, geometry))]
    visited = {(initial.probe, initial.cells)}
    frontier = [out[0]]
    for _ in range(max_prefix):
        nxt_frontier = []
        for node in frontier:
            for option in options:
                nxt = predict(by_option.get(option, ()), node.state, option[0], option[1], geometry)
                if (nxt.probe, nxt.cells) in visited:
                    continue
                visited.add((nxt.probe, nxt.cells))
                item = Reachable(node.prefix + (option,), nxt, features(nxt, subjects, geometry))
                out.append(item)
                nxt_frontier.append(item)
        frontier = nxt_frontier
    return out


def successes(claim: EffectClaim, transitions: Iterable[Transition], geometry: Geometry) -> list[BlindProbeCheckpoint]:
    return [t.before for t in transitions if (t.action, t.direction) == (claim.action, claim.direction)
            and observed_delta(claim.subject, t.before, t.after, geometry) == claim.delta]


def design_severe_test(claim: EffectClaim, states: Sequence[Reachable], seen: Sequence[Transition],
                       subjects: Sequence[str], geometry: Geometry, max_length: int,
                       dropped: AtomicCondition | None = None) -> SevereTest | None:
    """Two kinds of severe test, both a planned state B has not tried the
    action in:

    sufficiency (`dropped` None): the claim predicts success, and the state
    is as close as possible to one where the effect was seen to *fail* --
    "is what I named really enough?"

    necessity (`dropped` = one of the claim's conditions): that condition is
    false and every other one true, so the claim predicts *no* change, and
    the state is as close as possible to one where the effect was seen to
    *happen* -- "is this condition really needed?"

    Shortest prefix among the closest; None if nothing qualifies. `states`
    comes from `reachable` (B's model of where its programs lead)."""
    anchors = successes(claim, seen, geometry) if dropped else failures(claim, seen, geometry)
    target = [features(b, subjects, geometry) for b in anchors]
    if not target:
        return None
    others = tuple(c for c in claim.conditions if c != dropped)
    tried = {features(t.before, subjects, geometry) for t in seen
             if (t.action, t.direction) == (claim.action, claim.direction)}
    best: SevereTest | None = None
    for node in states:
        if len(node.prefix) + 1 > max_length or node.features in tried:
            continue
        if not all(c.holds(node.state, geometry) for c in others):
            continue
        if dropped is not None and dropped.holds(node.state, geometry):
            continue
        distance = min(sum(a != b for a, b in zip(node.features, f)) for f in target)
        if best is None or distance < best.distance:
            best = SevereTest(node.prefix + ((claim.action, claim.direction),), distance)
    return best
