"""A1 deterministic local energy, bonding, and separation kernel."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Mapping

from .causal_spec import (
    FORMAT_V2,
    FORMAT_V3,
    OPPOSITE_PORT,
    BondRuleSpec,
    CausalParticleSpec,
    CausalWorldSpec,
    HeatCellSpec,
)
from .spec import DIRECTIONS

VELOCITY = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def neighbour(x: int, y: int, direction: str, width: int, height: int) -> tuple[int, int]:
    """The cell one step from `(x, y)` in `direction`, on this wrapped grid.

    This is the SAME formula `_stream_free` uses to move a particle
    (`VELOCITY[direction]` plus modulo wrap). Bond adjacency must use exactly
    this and nothing else: if movement wraps at the edge but a bond's notion
    of "neighbour" did not, particles would stream across the seam while
    bonds could not reach across it -- one wrapped world with two different
    geometries, silently.
    """
    dx, dy = VELOCITY[direction]
    return (x + dx) % width, (y + dy) % height


@dataclass(frozen=True, order=True)
class PhysicalBond:
    """A v1/v2 bond: two particles sharing one cell, no named ports.

    Kept exactly as it was. v3 does not extend this type -- see `PortBond`
    below and `LOCAL_INTERACTION_PRINCIPLES_V1.md` on why a bond with
    optional, version-dependent fields was rejected in favour of two
    separate types.
    """
    left_id: int
    right_id: int
    rule_id: str
    stored_energy: int
    x: int
    y: int

    def canonical(self) -> dict[str, object]:
        return {
            "left_id": self.left_id, "right_id": self.right_id, "rule_id": self.rule_id,
            "stored_energy": self.stored_energy, "x": self.x, "y": self.y,
        }


@dataclass(frozen=True, order=True)
class PortBond:
    """A v3 bond: a relation between two particles' named ports, not a place.

    `left_id`/`right_id` name the pair; the ordering carries no physics.
    `canonical()` always emits the lower id first specifically so that a bond
    built as `(A, port, B, port)` and one built as `(B, port, A, port)` for
    the same physical contact hash identically -- "left" and "right" are
    labels for this record, not "processed first" and "processed second".

    No `x, y`: position belongs to the particles. A bond is legal exactly
    when the two particles are neighbours (via `neighbour()` above, so it
    agrees with how particles actually move) and each side's port faces the
    other's cell -- checked in `CausalWorldState.__post_init__`.
    """
    left_id: int
    left_port: str
    right_id: int
    right_port: str
    rule_id: str
    stored_energy: int

    def __post_init__(self) -> None:
        if self.right_id < self.left_id:
            left_id, left_port = self.left_id, self.left_port
            object.__setattr__(self, "left_id", self.right_id)
            object.__setattr__(self, "left_port", self.right_port)
            object.__setattr__(self, "right_id", left_id)
            object.__setattr__(self, "right_port", left_port)

    def canonical(self) -> dict[str, object]:
        return {
            "left_id": self.left_id, "left_port": self.left_port,
            "right_id": self.right_id, "right_port": self.right_port,
            "rule_id": self.rule_id, "stored_energy": self.stored_energy,
        }


@dataclass(frozen=True)
class CausalWorldState:
    tick: int
    particles: tuple[CausalParticleSpec, ...]
    heat: tuple[HeatCellSpec, ...]
    bonds: tuple[PhysicalBond, ...] = ()
    # How many bonds each material may hold at once, by kind. Empty means the
    # v1 rule: one bond per particle, whatever the material declares. A world
    # passes its own `ports` here to allow chains.
    #
    # This is a rule the world is run under, not part of the state itself, so
    # it stays out of `canonical()`, out of the digest, and out of equality:
    # two states with the same particles are the same state regardless of what
    # the surrounding world would permit.
    port_limits: Mapping[int, int] = field(default_factory=dict, compare=False, repr=False)
    # Whether a bonded group may carry motion. Under v1 a bond parks all the
    # motion it absorbed, so bonded particles are always at rest; under v2 a
    # chain can travel, which is what lets a moving particle join a standing
    # chain without the collision having to cancel to zero momentum.
    chains_may_move: bool = field(default=False, compare=False, repr=False)
    # The grid a `port_bonds` adjacency check is judged against, and which
    # ports each material declares. Like `port_limits` above, these are rules
    # the world is run under, not part of the state: two states with the same
    # particles and bonds are the same state regardless of the grid size or
    # the materials' port declarations, so both stay out of `canonical()`,
    # the digest, and equality.
    grid_size: tuple[int, int] | None = field(default=None, compare=False, repr=False)
    named_ports: Mapping[int, tuple[str, ...]] = field(default_factory=dict, compare=False, repr=False)
    # v3 bonds, kept in a field of their own rather than folded into `bonds`.
    # A single bond type carrying both `x, y` (v1/v2's meaning: a place) and
    # `left_port`/`right_port` (v3's meaning: a relation between neighbours)
    # would need every reader to ask "which fields does this bond actually
    # use" -- a state space with combinations no world can produce. Two types
    # make the illegal combinations unrepresentable instead of merely
    # unvalidated. v3 worlds populate this and leave `bonds` empty; v1/v2
    # worlds do the reverse. The kernel does not yet step `port_bonds`
    # forward (that is stage 3+, once structures can move) -- this stage only
    # asks whether a given set of them is spatially and physically legal.
    #
    # Placed last, after every v1/v2 field, so existing positional
    # constructions of this state (internal to the kernel; there is no public
    # constructor contract otherwise) keep meaning exactly what they meant
    # before this field existed.
    port_bonds: tuple[PortBond, ...] = ()

    def __post_init__(self) -> None:
        particles, heat, bonds = tuple(sorted(self.particles)), tuple(sorted(self.heat)), tuple(sorted(self.bonds))
        port_bonds_sorted = tuple(sorted(self.port_bonds))
        if len({item.particle_id for item in particles}) != len(particles):
            raise ValueError("particle ids must be unique")
        if len({(item.x, item.y) for item in heat}) != len(heat):
            raise ValueError("heat cells must be unique")
        by_id = {item.particle_id: item for item in particles}
        held = {value for bond in self.bonds for value in (bond.left_id, bond.right_id)}
        held |= {value for bond in port_bonds_sorted for value in (bond.left_id, bond.right_id)}
        # Two free particles of one material travelling the same way through the
        # same cell are the same channel and cannot be told apart. Chain members
        # are exempt: sitting together in one cell is what being bonded means,
        # and they are distinguished by the bonds rather than by their heading.
        free = [item for item in particles if item.particle_id not in held]
        if len({(item.kind, item.x, item.y, item.direction) for item in free}) != len(free):
            raise ValueError("directional material channels must be unique")

        occupied: dict[int, int] = {}
        for bond in bonds:
            if bond.left_id == bond.right_id:
                raise ValueError("a bond cannot join a particle to itself")
            occupied[bond.left_id] = occupied.get(bond.left_id, 0) + 1
            occupied[bond.right_id] = occupied.get(bond.right_id, 0) + 1
        if len({(bond.left_id, bond.right_id) for bond in bonds}) != len(bonds):
            raise ValueError("the same pair cannot be bonded twice")
        for particle_id, count in occupied.items():
            if particle_id not in by_id:
                raise ValueError("bond refers to a missing particle")
            allowed = self.port_limits.get(by_id[particle_id].kind, 1) if self.port_limits else 1
            if count > allowed:
                raise ValueError(
                    f"particle {particle_id} holds {count} bonds, above the {allowed} "
                    f"its material declares")

        for bond in bonds:
            if bond.left_id not in by_id or bond.right_id not in by_id:
                raise ValueError("bond refers to a missing particle")
            if by_id[bond.left_id].x != bond.x or by_id[bond.left_id].y != bond.y or by_id[bond.right_id].x != bond.x or by_id[bond.right_id].y != bond.y:
                raise ValueError("bonded particles must share the bond location")
            if not self.chains_may_move and (by_id[bond.left_id].kinetic_energy
                                             or by_id[bond.right_id].kinetic_energy):
                raise ValueError("bonded particles must store motion energy in the bond")

        # v3 port bonds: a relation between neighbours' named ports, checked
        # entirely from the state -- no `x, y` on the bond to trust or distrust.
        port_bonds = port_bonds_sorted
        if port_bonds and self.grid_size is None:
            raise ValueError("port bonds need a grid size to judge adjacency against")
        width, height = self.grid_size or (0, 0)
        port_occupied: dict[tuple[int, str], int] = {}
        for bond in port_bonds:
            if bond.left_id == bond.right_id:
                raise ValueError("a bond cannot join a particle to itself")
            if bond.left_id not in by_id or bond.right_id not in by_id:
                raise ValueError("port bond refers to a missing particle")
            left, right = by_id[bond.left_id], by_id[bond.right_id]

            left_ports = self.named_ports.get(left.kind, ())
            right_ports = self.named_ports.get(right.kind, ())
            if bond.left_port not in left_ports:
                raise ValueError(
                    f"particle {bond.left_id} has no {bond.left_port!r} port "
                    f"to bond with (declares {list(left_ports)})")
            if bond.right_port not in right_ports:
                raise ValueError(
                    f"particle {bond.right_id} has no {bond.right_port!r} port "
                    f"to bond with (declares {list(right_ports)})")
            if OPPOSITE_PORT[bond.left_port] != bond.right_port:
                raise ValueError(
                    f"ports {bond.left_port!r} and {bond.right_port!r} do not "
                    f"face each other")

            # Adjacency is judged with the SAME formula streaming uses to move
            # a particle (`neighbour()`, which wraps by `grid_size`). Using
            # any other rule here would let one wrapped world have two
            # different geometries -- particles that stream across the seam,
            # bonds that cannot reach across it.
            expected = neighbour(left.x, left.y, bond.left_port, width, height)
            if (right.x, right.y) != expected:
                raise ValueError(
                    f"particle {bond.right_id} at ({right.x},{right.y}) is not "
                    f"{left.particle_id}'s {bond.left_port!r} neighbour "
                    f"(expected {expected})")

            port_occupied[(bond.left_id, bond.left_port)] = port_occupied.get(
                (bond.left_id, bond.left_port), 0) + 1
            port_occupied[(bond.right_id, bond.right_port)] = port_occupied.get(
                (bond.right_id, bond.right_port), 0) + 1
        if len({(b.left_id, b.left_port, b.right_id, b.right_port) for b in port_bonds}) != len(port_bonds):
            raise ValueError("the same port pair cannot be bonded twice")
        for (particle_id, port_name), count in port_occupied.items():
            if count > 1:
                raise ValueError(
                    f"particle {particle_id}'s {port_name!r} port is claimed "
                    f"by {count} bonds at once")

        if self.chains_may_move:
            # A travelling chain keeps its motion on exactly one member — the
            # lowest id. Spreading a copy across every member would count the
            # same motion several times in the energy and momentum totals, so
            # the single holder is what makes "the chain moves" a quantity
            # rather than a description.
            for members in set(chains(bonds).values()):
                holders = [item for item in sorted(members) if by_id[item].kinetic_energy]
                if len(holders) > 1:
                    raise ValueError("a chain carries its motion on one member, not several")
                if holders and holders[0] != min(members):
                    # DEFECT: an id decides where a structure's motion lives.
                    # Momentum belongs to the connected component, not to a
                    # member picked by number.
                    raise ValueError("a chain carries its motion on its lowest-numbered member")
        object.__setattr__(self, "particles", particles); object.__setattr__(self, "heat", heat); object.__setattr__(self, "bonds", bonds)
        object.__setattr__(self, "port_bonds", port_bonds)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {
            "bonds": [item.canonical() for item in self.bonds],
            "heat": [item.canonical() for item in self.heat],
            "particles": [item.canonical() for item in self.particles],
            "tick": self.tick,
        }
        if self.port_bonds:
            result["port_bonds"] = [item.canonical() for item in self.port_bonds]
        return result

    def total_energy(self) -> int:
        return (sum(item.kinetic_energy for item in self.particles)
                + sum(item.energy for item in self.heat)
                + sum(item.stored_energy for item in self.bonds)
                + sum(item.stored_energy for item in self.port_bonds))

    def material_counts(self) -> dict[int, int]:
        result: dict[int, int] = {}
        for item in self.particles: result[item.kind] = result.get(item.kind, 0) + 1
        return dict(sorted(result.items()))

    def momentum(self, spec: CausalWorldSpec) -> tuple[int, int]:
        """Total momentum carried by everything that is free to move.

        Under v1 a bond parks every bit of motion it absorbed, so bonded
        particles contribute nothing and are skipped. Under v2 a chain may
        travel: one member holds the velocity for the whole body, and the
        chain contributes that velocity carried by the chain's total mass.
        """
        masses = {item.kind: item.mass for item in spec.materials}
        bonded = {value for bond in self.bonds for value in (bond.left_id, bond.right_id)}
        x = y = 0
        for item in self.particles:
            if item.particle_id in bonded:
                continue
            dx, dy = VELOCITY[item.direction]
            x += masses[item.kind] * item.kinetic_energy * dx
            y += masses[item.kind] * item.kinetic_energy * dy
        if not self.chains_may_move:
            return x, y

        by_id = {item.particle_id: item for item in self.particles}
        for members in set(chains(self.bonds).values()):
            holder = by_id[min(members)]
            if not holder.kinetic_energy:
                continue
            dx, dy = VELOCITY[holder.direction]
            mass = sum(masses[by_id[item].kind] for item in members)
            x += mass * holder.kinetic_energy * dx
            y += mass * holder.kinetic_energy * dy
        return x, y


@dataclass(frozen=True)
class CausalTickRecord:
    tick: int
    state_digest: str
    material_counts: tuple[tuple[int, int], ...]
    total_energy: int
    momentum: tuple[int, int]
    bonds: int

    def canonical(self) -> dict[str, object]:
        return {"bonds": self.bonds, "material_counts": {str(k): v for k, v in self.material_counts},
                "momentum": list(self.momentum), "state_digest": self.state_digest,
                "tick": self.tick, "total_energy": self.total_energy}


@dataclass(frozen=True)
class CausalRun:
    spec_digest: str
    initial_state: CausalWorldState
    final_state: CausalWorldState
    checkpoints: tuple[CausalTickRecord, ...]

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"checkpoints": [x.canonical() for x in self.checkpoints], "final_state": self.final_state.canonical(),
                "format": "deterministic-causal-run-v1", "initial_state": self.initial_state.canonical(),
                "spec_digest": self.spec_digest}


def chains(bonds: tuple[PhysicalBond, ...]) -> dict[int, frozenset[int]]:
    """Group bonded particles into the chains they form.

    Returns `{particle_id: the whole chain it belongs to}`. Unbonded particles
    are absent. Built by union-find rather than a fresh graph walk per query,
    so the cost is near-linear in the number of bonds — the chain structure is
    only ever rebuilt when bonds actually change.
    """
    parent: dict[int, int] = {}

    def find(item: int) -> int:
        parent.setdefault(item, item)
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:          # path compression
            parent[item], item = root, parent[item]
        return root

    for bond in bonds:
        left, right = find(bond.left_id), find(bond.right_id)
        if left != right:
            parent[left] = right

    grouped: dict[int, set[int]] = {}
    for item in parent:
        grouped.setdefault(find(item), set()).add(item)
    return {item: frozenset(members) for members in grouped.values() for item in members}


def port_limits(spec: CausalWorldSpec) -> dict[int, int]:
    """How many bonds each material may hold at once under this world.

    v1 worlds keep the original rule of one bond per particle regardless of
    what their materials declare, so existing runs reproduce exactly. v2
    worlds honour the `ports` their materials already carry, which is what
    lets a collision extend a chain instead of being refused.
    """
    if spec.format != FORMAT_V2:
        return {item.kind: 1 for item in spec.materials}
    return {item.kind: item.ports for item in spec.materials}


def initial_causal_state(spec: CausalWorldSpec) -> CausalWorldState:
    # A v3 world carries its grid and its materials' named ports in the state so
    # that a `PortBond`'s adjacency can be judged from the state alone. Without
    # them the state cannot tell a legal bond from an illegal one, so v3 worlds
    # have to start with them rather than acquire them later.
    named = {item.kind: item.port_names for item in spec.materials if item.port_names}
    return CausalWorldState(0, spec.particles, spec.heat, (), port_limits(spec),
                            spec.format == FORMAT_V2,
                            (spec.kernel.width, spec.kernel.height) if named else None,
                            named)


def _heat_map(state: CausalWorldState) -> dict[tuple[int, int], int]:
    return {(item.x, item.y): item.energy for item in state.heat}


def _heat_cells(values: dict[tuple[int, int], int]) -> tuple[HeatCellSpec, ...]:
    return tuple(HeatCellSpec(x, y, energy) for (x, y), energy in sorted(values.items()) if energy)


def _break_existing(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    particles = {item.particle_id: item for item in state.particles}
    heat = _heat_map(state)
    rules = {item.rule_id: item for item in spec.bond_rules}
    by_point: dict[tuple[int, int], list[PhysicalBond]] = defaultdict(list)
    for bond in state.bonds:
        by_point[(bond.x, bond.y)].append(bond)
    remaining = []
    for point, local_bonds in sorted(by_point.items()):
        required = sum(rules[bond.rule_id].break_heat for bond in local_bonds)
        releases = [bond.stored_energy + rules[bond.rule_id].break_heat for bond in local_bonds]
        if heat.get(point, 0) < required or any(value % 2 for value in releases):
            remaining.extend(local_bonds)
            continue
        heat[point] = heat.get(point, 0) - required
        for bond, released in zip(local_bonds, releases):
            rule = rules[bond.rule_id]
            each = released // 2
            left, right = particles[bond.left_id], particles[bond.right_id]
            particles[bond.left_id] = replace(left, direction=rule.release_left, orientation=rule.release_left, kinetic_energy=each)
            particles[bond.right_id] = replace(right, direction=rule.release_right, orientation=rule.release_right, kinetic_energy=each)
    return replace(state, particles=tuple(particles.values()), heat=_heat_cells(heat),
                   bonds=tuple(remaining))


def _stream_free(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    bonded = {value for bond in state.bonds for value in (bond.left_id, bond.right_id)}
    membership = chains(state.bonds) if state.chains_may_move else {}
    by_id = {item.particle_id: item for item in state.particles}

    # A travelling chain moves as one body: every member steps together, in the
    # direction its holder carries. Working out the step once per chain rather
    # than once per member is also what keeps this linear in the particle count.
    chain_step: dict[int, tuple[int, int]] = {}
    for members in set(membership.values()):
        holder = by_id[min(members)]
        if holder.kinetic_energy:
            chain_step[min(members)] = VELOCITY[holder.direction]

    particles = []
    for item in state.particles:
        if item.particle_id in bonded:
            members = membership.get(item.particle_id)
            step = chain_step.get(min(members)) if members else None
            if step is None:
                particles.append(item)
                continue
            dx, dy = step
        elif item.kinetic_energy == 0:
            particles.append(item)
            continue
        else:
            dx, dy = VELOCITY[item.direction]
        particles.append(replace(item, x=(item.x + dx) % spec.kernel.width,
                                 y=(item.y + dy) % spec.kernel.height))

    moved = tuple(particles)
    # Bonds record where their particles are, so a chain that stepped carries
    # its bonds with it rather than leaving them behind at the old cell.
    if chain_step:
        placed = {item.particle_id: item for item in moved}
        bonds = tuple(replace(bond, x=placed[bond.left_id].x, y=placed[bond.left_id].y)
                      for bond in state.bonds)
    else:
        bonds = state.bonds
    return replace(state, particles=moved, bonds=bonds)


def _match_rule(rules: tuple[BondRuleSpec, ...], first: CausalParticleSpec, second: CausalParticleSpec) -> tuple[BondRuleSpec, bool] | None:
    for rule in rules:
        direct = first.kind == rule.left_kind and second.kind == rule.right_kind and first.orientation == rule.left_orientation and second.orientation == rule.right_orientation
        reverse = second.kind == rule.left_kind and first.kind == rule.right_kind and second.orientation == rule.left_orientation and first.orientation == rule.right_orientation
        if direct: return rule, False
        if reverse: return rule, True
    return None


def _grow_chains(spec: CausalWorldSpec, state: CausalWorldState,
                 particles: dict[int, CausalParticleSpec],
                 bonds: list[PhysicalBond]) -> None:
    """Let a free particle join a chain it has arrived at, in place.

    A standing chain cannot take part in a head-on collision, so under v1 a
    chain could never reach three: every bond needed two free particles whose
    momenta cancelled. Here the arriving particle is absorbed instead, and the
    chain takes up the momentum it brought — total mass moving slower, rather
    than the motion vanishing.

    The exchange only happens when it comes out exact in integers. A collision
    that would need a fractional velocity is left alone, which is a real
    outcome rather than a rounding.
    """
    masses = {item.kind: item.mass for item in spec.materials}
    membership = chains(tuple(bonds))
    occupied: dict[int, int] = {}
    for bond in bonds:
        occupied[bond.left_id] = occupied.get(bond.left_id, 0) + 1
        occupied[bond.right_id] = occupied.get(bond.right_id, 0) + 1

    free_at: dict[tuple[int, int], list[CausalParticleSpec]] = defaultdict(list)
    for item in particles.values():
        if item.particle_id not in membership and item.kinetic_energy:
            free_at[(item.x, item.y)].append(item)

    # KNOWN DEFECT (2026-09-22): the next few lines let particle ids decide
    # physics, and cap growth for no declared reason. See
    # `docs/current/LOCAL_INTERACTION_PRINCIPLES_V1.md` and the recorded
    # evidence in `tests/test_known_defects_causal_kernel.py`. These are
    # scheduled for replacement once local geometry exists; do not build new
    # rules on top of them.
    for members in sorted(set(membership.values()), key=min):
        anchor = min(members)
        holder = particles[anchor]
        if holder.kinetic_energy:
            continue            # DEFECT: no declared law stops a moving chain growing
        point = (particles[anchor].x, particles[anchor].y)
        arrivals = sorted(free_at.get(point, ()),
                          key=lambda p: (p.kind, p.orientation, p.direction, p.particle_id))
        for arriving in arrivals:
            if arriving.particle_id in membership:
                continue        # already absorbed by an earlier chain this tick
            # Try every member with a free port, not just the first: whether a
            # bond forms depends on the pair's orientations, so one end of a
            # chain can accept an arrival the other end has no rule for.
            attachment = None
            # DEFECT: `sorted` means the lowest-numbered member wins whenever
            # more than one could accept this arrival. The physics does not
            # choose; the name does.
            for item in sorted(members):
                if occupied.get(item, 0) >= state.port_limits.get(particles[item].kind, 1):
                    continue
                matched = _match_rule(spec.bond_rules, particles[item], arriving)
                if matched is not None:
                    attachment = (item, matched)
                    break
            if attachment is None:
                continue        # no free port on this chain bonds with this arrival
            attach, (rule, reversed_roles) = attachment
            if arriving.kinetic_energy < rule.minimum_collision_energy:
                continue

            chain_mass = sum(masses[particles[item].kind] for item in members)
            total_mass = chain_mass + masses[arriving.kind]
            carried = masses[arriving.kind] * arriving.kinetic_energy
            if carried % total_mass:
                continue        # no exact integer velocity for the joined body
            speed = carried // total_mass
            absorbed = arriving.kinetic_energy - speed

            left, right = ((arriving, particles[attach]) if reversed_roles
                           else (particles[attach], arriving))
            bonds.append(PhysicalBond(left.particle_id, right.particle_id,
                                      rule.rule_id, absorbed, point[0], point[1]))
            particles[arriving.particle_id] = replace(arriving, kinetic_energy=0)
            if speed:
                particles[anchor] = replace(particles[anchor],
                                            direction=arriving.direction, kinetic_energy=speed)
            occupied[attach] = occupied.get(attach, 0) + 1
            occupied[arriving.particle_id] = occupied.get(arriving.particle_id, 0) + 1
            membership = chains(tuple(bonds))
            break               # DEFECT: an undeclared one-bond-per-tick ceiling


def _resolve_collisions(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    bonded = {value for bond in state.bonds for value in (bond.left_id, bond.right_id)}
    groups: dict[tuple[int, int], list[CausalParticleSpec]] = defaultdict(list)
    for item in state.particles:
        if item.particle_id not in bonded: groups[(item.x, item.y)].append(item)
    particles = {item.particle_id: item for item in state.particles}; bonds = list(state.bonds)
    masses = {item.kind: item.mass for item in spec.materials}
    for (x, y), group in sorted(groups.items()):
        # KNOWN DEFECT (2026-09-21): three or more free bodies in one cell are
        # skipped entirely, so they pass through each other. Counted in
        # `precondition_census`; do not simply delete this line -- without
        # local geometry there is no way to say which of them touched which.
        if len(group) != 2: continue
        first, second = sorted(group, key=lambda p: (p.kind, p.orientation, p.direction, p.kinetic_energy, p.particle_id))
        matched = _match_rule(spec.bond_rules, first, second)
        if matched is not None:
            rule, reversed_roles = matched; total = first.kinetic_energy + second.kinetic_energy
            momentum = (masses[first.kind] * first.kinetic_energy * VELOCITY[first.direction][0] + masses[second.kind] * second.kinetic_energy * VELOCITY[second.direction][0],
                        masses[first.kind] * first.kinetic_energy * VELOCITY[first.direction][1] + masses[second.kind] * second.kinetic_energy * VELOCITY[second.direction][1])
            if total >= rule.minimum_collision_energy and momentum == (0, 0):
                left, right = (second, first) if reversed_roles else (first, second)
                particles[first.particle_id] = replace(first, kinetic_energy=0)
                particles[second.particle_id] = replace(second, kinetic_energy=0)
                bonds.append(PhysicalBond(left.particle_id, right.particle_id, rule.rule_id, total, x, y))
                continue
        if first.kind == second.kind and {first.direction, second.direction} in ({"N", "S"}, {"E", "W"}):
            replacement = ("E", "W") if {first.direction, second.direction} == {"N", "S"} else ("N", "S")
            ordered = sorted((first, second), key=lambda p: DIRECTIONS.index(p.direction))
            for particle, direction in zip(ordered, replacement):
                particles[particle.particle_id] = replace(particle, direction=direction, orientation=direction)
    if state.chains_may_move:
        _grow_chains(spec, state, particles, bonds)
    return replace(state, particles=tuple(particles.values()), bonds=tuple(bonds))


def step_causal_world(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    counts, energy, momentum = state.material_counts(), state.total_energy(), state.momentum(spec)
    result = _break_existing(spec, state)
    result = _stream_free(spec, result)
    result = _resolve_collisions(spec, result)
    result = replace(result, tick=state.tick + 1)
    if result.material_counts() != counts: raise AssertionError("causal tick changed material counts")
    if result.total_energy() != energy: raise AssertionError("causal tick changed total energy")
    if result.momentum(spec) != momentum: raise AssertionError("causal tick changed momentum")
    return result


def _record(spec: CausalWorldSpec, state: CausalWorldState) -> CausalTickRecord:
    return CausalTickRecord(state.tick, state.digest, tuple(state.material_counts().items()), state.total_energy(), state.momentum(spec), len(state.bonds))


def run_causal_world(spec: CausalWorldSpec) -> CausalRun:
    state = initial_causal_state(spec); initial = state; checkpoints = [_record(spec, state)]
    for _ in range(spec.ticks):
        state = step_causal_world(spec, state)
        if state.tick % spec.hash_interval == 0 or state.tick == spec.ticks: checkpoints.append(_record(spec, state))
    return CausalRun(spec.digest, initial, state, tuple(checkpoints))
