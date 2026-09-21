"""Count the chances a causal world had, not the outcomes it reached.

The 2026-09-20 failure was structural: the probabilistic scheduler handled
exactly one ordinary event per tick, so competition could not occur at any
scale. Sixty-four worlds ran for six hours waiting for something the code
forbade. Nobody counted the precondition first.

Work bundle 4 adds catalysts, template copying, membranes and division. Every
one of those needs an opportunity before it needs a rule:

    a catalyst needs three particles meeting in one cell
    a chain needs to reach four before length is interesting
    template copying needs a chain standing still with a free port
    division needs two separate chains existing at once

This module counts those opportunities under the physics we already have. It
adds no rule and changes no state -- it replays the declared tick order and
tallies what the world offered.

A zero here is the finding. It means the matching rule would never fire, and
building it first would repeat 2026-09-20 with new vocabulary.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

from .causal_kernel import (
    CausalWorldState,
    chains,
    initial_causal_state,
    step_causal_world,
)
from .causal_spec import CausalWorldSpec


@dataclass(frozen=True)
class TickCensus:
    """What one tick's state offered, counted before the next tick ran."""

    tick: int
    free_particles: int
    # Cells holding two free particles: the only arrangement the current
    # kernel resolves as a collision at all.
    cells_with_two_free: int
    # Cells holding three or more free particles. The kernel skips these
    # outright (`if len(group) != 2: continue`), so today they are missed
    # chances rather than events -- and they are exactly what a catalyst,
    # being a third body, would need.
    cells_with_three_or_more_free: int
    # A free particle arriving where a chain already sits. This is the only
    # path by which a chain grows past two under v2.
    chain_arrival_cells: int
    bonds: int
    chain_count: int
    longest_chain: int
    # Chains of four or more. Two is a pair and three is the smoke test; a
    # polymer worth the name starts here.
    chains_of_four_or_more: int
    # Chains standing still with a port free -- what a template would need in
    # order to be copied alongside rather than merely extended.
    standing_chains_with_free_port: int
    # More than one chain alive at once. Division has nothing to divide into
    # unless this exceeds one at some point.
    coexisting_chains: int

    def canonical(self) -> dict[str, int]:
        return {
            "bonds": self.bonds,
            "cells_with_three_or_more_free": self.cells_with_three_or_more_free,
            "cells_with_two_free": self.cells_with_two_free,
            "chain_arrival_cells": self.chain_arrival_cells,
            "chain_count": self.chain_count,
            "chains_of_four_or_more": self.chains_of_four_or_more,
            "coexisting_chains": self.coexisting_chains,
            "free_particles": self.free_particles,
            "longest_chain": self.longest_chain,
            "standing_chains_with_free_port": self.standing_chains_with_free_port,
            "tick": self.tick,
        }


@dataclass(frozen=True)
class WorldCensus:
    """Per-tick counts and the totals that decide whether a rule could fire."""

    world_id: str
    spec_digest: str
    ticks: int
    per_tick: tuple[TickCensus, ...]
    # Peaks and sums across the run. `ticks_with_*` counts ticks, not events:
    # the same standing chain waiting ten ticks is ten chances offered.
    ticks_with_three_or_more_free: int
    ticks_with_chain_arrival: int
    ticks_with_four_chain: int
    ticks_with_two_chains: int
    ticks_with_standing_free_port: int
    peak_longest_chain: int
    peak_coexisting_chains: int
    peak_cell_crowding: int

    def canonical(self) -> dict[str, object]:
        return {
            "format": "deterministic-precondition-census-v1",
            "peak_cell_crowding": self.peak_cell_crowding,
            "peak_coexisting_chains": self.peak_coexisting_chains,
            "peak_longest_chain": self.peak_longest_chain,
            "per_tick": [item.canonical() for item in self.per_tick],
            "spec_digest": self.spec_digest,
            "ticks": self.ticks,
            "ticks_with_chain_arrival": self.ticks_with_chain_arrival,
            "ticks_with_four_chain": self.ticks_with_four_chain,
            "ticks_with_standing_free_port": self.ticks_with_standing_free_port,
            "ticks_with_three_or_more_free": self.ticks_with_three_or_more_free,
            "ticks_with_two_chains": self.ticks_with_two_chains,
            "world_id": self.world_id,
        }

    def blocked(self) -> tuple[str, ...]:
        """Which bundle-4 rules this world never offered a chance to fire.

        Named for the rule that would be blocked, not for the counter that
        read zero, so the answer says what is forbidden rather than what was
        tallied.
        """
        missing = []
        if not self.ticks_with_three_or_more_free:
            missing.append("catalyst-needs-three-bodies-in-one-cell")
        if self.peak_longest_chain < 4:
            missing.append("polymer-needs-chain-of-four")
        if not self.ticks_with_standing_free_port:
            missing.append("template-needs-standing-chain-with-free-port")
        if self.peak_coexisting_chains < 2:
            missing.append("division-needs-two-chains-at-once")
        return tuple(missing)


def _census(spec: CausalWorldSpec, state: CausalWorldState) -> TickCensus:
    membership = chains(state.bonds)
    bonded = set(membership)
    by_id = {item.particle_id: item for item in state.particles}

    crowd: dict[tuple[int, int], int] = defaultdict(int)
    for item in state.particles:
        if item.particle_id not in bonded:
            crowd[(item.x, item.y)] += 1

    # Where the chains sit. A chain occupies one cell today, so its anchor's
    # position stands for the whole body.
    groups = set(membership.values())
    chain_cells: dict[tuple[int, int], int] = defaultdict(int)
    for members in groups:
        anchor = by_id[min(members)]
        chain_cells[(anchor.x, anchor.y)] += 1

    ports = state.port_limits
    held: dict[int, int] = defaultdict(int)
    for bond in state.bonds:
        held[bond.left_id] += 1
        held[bond.right_id] += 1

    standing_free_port = 0
    for members in groups:
        anchor = by_id[min(members)]
        if anchor.kinetic_energy:
            continue        # a travelling chain is not available as a template
        if any(held[item] < ports.get(by_id[item].kind, 1) for item in members):
            standing_free_port += 1

    lengths = [len(members) for members in groups]
    return TickCensus(
        tick=state.tick,
        free_particles=len(state.particles) - len(bonded),
        cells_with_two_free=sum(1 for count in crowd.values() if count == 2),
        cells_with_three_or_more_free=sum(1 for count in crowd.values() if count >= 3),
        chain_arrival_cells=sum(1 for point, count in chain_cells.items()
                                if count and crowd.get(point, 0)),
        bonds=len(state.bonds),
        chain_count=len(groups),
        longest_chain=max(lengths, default=0),
        chains_of_four_or_more=sum(1 for value in lengths if value >= 4),
        standing_chains_with_free_port=standing_free_port,
        coexisting_chains=len(groups),
    )


def census_causal_world(spec: CausalWorldSpec) -> WorldCensus:
    """Replay the world's declared ticks and tally the chances it offered."""
    state = initial_causal_state(spec)
    per_tick = [_census(spec, state)]
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        per_tick.append(_census(spec, state))

    rows = tuple(per_tick)
    return WorldCensus(
        world_id=spec.world_id,
        spec_digest=spec.digest,
        ticks=spec.ticks,
        per_tick=rows,
        ticks_with_three_or_more_free=sum(1 for r in rows if r.cells_with_three_or_more_free),
        ticks_with_chain_arrival=sum(1 for r in rows if r.chain_arrival_cells),
        ticks_with_four_chain=sum(1 for r in rows if r.chains_of_four_or_more),
        ticks_with_two_chains=sum(1 for r in rows if r.coexisting_chains >= 2),
        ticks_with_standing_free_port=sum(1 for r in rows if r.standing_chains_with_free_port),
        peak_longest_chain=max((r.longest_chain for r in rows), default=0),
        peak_coexisting_chains=max((r.coexisting_chains for r in rows), default=0),
        peak_cell_crowding=max((r.cells_with_three_or_more_free for r in rows), default=0),
    )


def render_census(census: WorldCensus) -> str:
    return json.dumps(census.canonical(), ensure_ascii=False,
                      indent=2, sort_keys=True) + "\n"
