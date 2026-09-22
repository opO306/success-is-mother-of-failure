"""Count where the kernel decides by particle id instead of by physics.

`LOCAL_INTERACTION_PRINCIPLES_V1.md` principle 3: when the declared physical
state does not single out one outcome, an id, an array position or a thread
order must not be allowed to pick. That is a missing state variable, not a
tie to break.

The kernel breaks this today, and not only in the three-body case that the
precondition census found. `_grow_chains` walks `sorted(members)` and takes
the first member whose port accepts the arrival, then `break`s. When more
than one member would have accepted it, the lowest-numbered one wins -- a
rule no world specification declares.

This module counts those moments. It adds no rule, changes no state, and
decides nothing differently: it replays the declared tick order and, at each
collision resolution, asks which choices the physics left open.

Counted as contested:

    an arrival that more than one chain member could bond with
    an arrival that more than one chain could absorb
    a cell where a chain could grow and the arrival could also pair off
    a cell holding three or more free particles, where today nothing happens

A zero means the shipped worlds happen not to reach the ambiguity, not that
the kernel is sound. The census says how much of the physics currently rests
on id order, so the fix can be measured rather than asserted.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

from .causal_kernel import (
    CausalWorldState,
    _match_rule,
    chains,
    initial_causal_state,
    step_causal_world,
)
from .causal_spec import CausalWorldSpec


@dataclass(frozen=True)
class ContestedMoment:
    """One point where more than one lawful outcome was available."""

    tick: int
    x: int
    y: int
    kind: str
    # The particles whose fate the physics left open, lowest id first. The
    # kernel takes the first of these; nothing in any specification says it
    # should.
    candidates: tuple[int, ...]
    detail: str

    def canonical(self) -> dict[str, object]:
        return {"candidates": list(self.candidates), "detail": self.detail,
                "kind": self.kind, "tick": self.tick, "x": self.x, "y": self.y}


@dataclass(frozen=True)
class ContestedCensus:
    world_id: str
    spec_digest: str
    ticks: int
    moments: tuple[ContestedMoment, ...]

    def by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.moments:
            counts[item.kind] = counts.get(item.kind, 0) + 1
        return dict(sorted(counts.items()))

    def canonical(self) -> dict[str, object]:
        return {
            "by_kind": self.by_kind(),
            "format": "deterministic-contested-census-v1",
            "moments": [item.canonical() for item in self.moments],
            "spec_digest": self.spec_digest,
            "ticks": self.ticks,
            "total": len(self.moments),
            "world_id": self.world_id,
        }


def _contested_in(spec: CausalWorldSpec, state: CausalWorldState) -> list[ContestedMoment]:
    """Which choices this state leaves open, judged before the kernel picks.

    Mirrors what `_resolve_collisions` and `_grow_chains` see at the start of
    the collision phase, but records the alternatives instead of taking one.
    """
    found: list[ContestedMoment] = []
    membership = chains(state.bonds)
    bonded = set(membership)
    by_id = {item.particle_id: item for item in state.particles}

    free_at: dict[tuple[int, int], list[int]] = defaultdict(list)
    for item in state.particles:
        if item.particle_id not in bonded:
            free_at[(item.x, item.y)].append(item.particle_id)

    # Three or more free bodies in one cell. The kernel skips the cell
    # entirely, so every pairing the rules would allow goes unexplored.
    for (x, y), members in sorted(free_at.items()):
        if len(members) >= 3:
            found.append(ContestedMoment(
                state.tick, x, y, "three_or_more_free_in_one_cell",
                tuple(sorted(members)),
                f"{len(members)} free particles share this cell; the kernel "
                f"resolves only pairs, so none of them interact"))

    if not state.chains_may_move:
        return found

    held: dict[int, int] = defaultdict(int)
    for bond in state.bonds:
        held[bond.left_id] += 1
        held[bond.right_id] += 1

    # Which chains could take which arrivals. Recomputed from the same inputs
    # `_grow_chains` uses, so a disagreement here would be a real one.
    claims: dict[int, list[int]] = defaultdict(list)
    for members in sorted(set(membership.values()), key=min):
        anchor = min(members)
        if by_id[anchor].kinetic_energy:
            continue        # a moving chain is not offered arrivals today
        point = (by_id[anchor].x, by_id[anchor].y)
        for arriving_id in sorted(free_at.get(point, ())):
            arriving = by_id[arriving_id]
            if not arriving.kinetic_energy:
                continue
            accepting = []
            for item in sorted(members):
                if held[item] >= state.port_limits.get(by_id[item].kind, 1):
                    continue
                matched = _match_rule(spec.bond_rules, by_id[item], arriving)
                if matched is not None and arriving.kinetic_energy >= matched[0].minimum_collision_energy:
                    accepting.append(item)
            if not accepting:
                continue
            claims[arriving_id].append(anchor)
            if len(accepting) > 1:
                found.append(ContestedMoment(
                    state.tick, point[0], point[1], "several_ports_accept_one_arrival",
                    tuple(accepting),
                    f"particle {arriving_id} could bond with any of these chain "
                    f"members; the kernel takes the lowest-numbered one"))

    for arriving_id, anchors in sorted(claims.items()):
        if len(anchors) > 1:
            item = by_id[arriving_id]
            found.append(ContestedMoment(
                state.tick, item.x, item.y, "several_chains_claim_one_arrival",
                tuple(sorted(anchors)),
                f"particle {arriving_id} could join any of these chains; the "
                f"kernel gives it to whichever is processed first"))

    return found


def contested_causal_world(spec: CausalWorldSpec) -> ContestedCensus:
    """Replay the declared ticks and record every undetermined choice."""
    state = initial_causal_state(spec)
    moments = list(_contested_in(spec, state))
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        moments.extend(_contested_in(spec, state))
    return ContestedCensus(spec.world_id, spec.digest, spec.ticks, tuple(moments))


def render_contested(census: ContestedCensus) -> str:
    return json.dumps(census.canonical(), ensure_ascii=False,
                      indent=2, sort_keys=True) + "\n"
