"""G11b: B proposes effect claims from what it saw, and finds conditions when surprised.

Proposing. For every (action, direction) B has tried and every subject, a
nonzero change B actually observed becomes an unconditional claim ("doing
this changes that by d").

Refining. When a claim meets steps it does not fit -- the action was done
but the change did not happen -- B looks back over *all* its steps with that
action and searches for what separates "changed by d" from "did not change",
in the designer's fixed order:

    no condition  ->  one atomic condition  ->  ALL of two

It moves to two only when no single condition separates the cases, and it
never enumerates two-condition claims up front. If even two cannot separate
them -- or the subject sometimes changed by some *other* amount the claim
cannot express -- the claim is marked unexplained: a gap in the language,
kept as data, never forced.

Atomic conditions are tried in a fixed simplicity order: the probe's own
state first, then cells nearest the probe, "> = 1" before "= 0". The first
that separates is taken -- it may be a coincidence of the data so far, which
is why the loop tests every refined claim on steps it has not seen.

B-facing: imports only `probe_grammar` and `blind_probe`.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterable, Sequence

from .probe_grammar import (
    OFFSETS, SELF_SUBJECTS, AtomicCondition, EffectClaim, Geometry, Transition, cell_subject, observed_delta,
)


def subjects_for(channels: Sequence[str]) -> tuple[str, ...]:
    ordered = sorted(OFFSETS, key=lambda o: (abs(o[0]) + abs(o[1]), o[1], o[0]))
    return SELF_SUBJECTS + tuple(cell_subject(dx, dy, ch) for dx, dy in ordered for ch in sorted(channels))


def atoms_for(subjects: Sequence[str]) -> tuple[AtomicCondition, ...]:
    return tuple(AtomicCondition(s, op, v) for s in subjects for op, v in ((">=", 1), ("=", 0)))


def propose(transitions: Iterable[Transition], subjects: Sequence[str], geometry: Geometry,
            known: set[tuple[str, str | None, str]]) -> list[EffectClaim]:
    """Unconditional claims for every (action, direction, subject) that was
    seen to change and is not already held. Deterministic order."""
    seen: dict[tuple[str, str | None, str], int] = {}
    for step in transitions:
        for subject in subjects:
            change = observed_delta(subject, step.before, step.after, geometry)
            key = (step.action, step.direction, subject)
            if change and key not in known and key not in seen:
                seen[key] = change
    return [EffectClaim(a, d, s, delta) for (a, d, s), delta in sorted(seen.items(), key=lambda kv: (
        kv[0][0], kv[0][1] or "", subjects.index(kv[0][2])))]


def refine(claim: EffectClaim, transitions: Sequence[Transition], atoms: Sequence[AtomicCondition],
           geometry: Geometry) -> tuple[EffectClaim | None, str]:
    """(refined claim, how) -- how is "unchanged", "one", "two", or
    "unexplained" (claim is None then)."""
    relevant = [t for t in transitions if (t.action, t.direction) == (claim.action, claim.direction)]
    positives, negatives = [], []
    for step in relevant:
        change = observed_delta(claim.subject, step.before, step.after, geometry)
        if change == claim.delta:
            positives.append(step.before)
        elif change == 0:
            negatives.append(step.before)
        else:
            return None, "unexplained"          # a change of another size: not this sentence
    if not negatives:
        return EffectClaim(claim.action, claim.direction, claim.subject, claim.delta), "unchanged"

    def separates(conditions: tuple[AtomicCondition, ...]) -> bool:
        return (all(all(c.holds(b, geometry) for c in conditions) for b in positives)
                and not any(all(c.holds(b, geometry) for c in conditions) for b in negatives))

    for atom in atoms:
        if separates((atom,)):
            return EffectClaim(claim.action, claim.direction, claim.subject, claim.delta, (atom,)), "one"
    for pair in combinations(atoms, 2):
        if pair[0].subject == pair[1].subject:
            continue
        ordered = tuple(sorted(pair))
        if separates(ordered):
            return EffectClaim(claim.action, claim.direction, claim.subject, claim.delta, ordered), "two"
    return None, "unexplained"
