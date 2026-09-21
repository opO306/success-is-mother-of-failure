"""Check that particles, bonds and chains obeyed their declared rules.

The environment checks cover water, heat, vapour and minerals. Particles are
governed by a different contract — bond rules, collision energies, port
limits, one cell of travel per tick — and nothing verified it.

A trace records the causal stage as one commit: breaking, streaming and
collisions have all happened by the time the snapshot is written. So this does
not replay the three phases. It asks a weaker but checkable question of the
before/after pair:

    could this change have come out of those rules at all?

Things that pass conservation and still answer no:

    a particle that moved two cells in one tick, or sideways to its heading
    a bond between particles the world declares no rule for
    a bond formed below the collision energy its rule demands
    a particle holding more bonds than its material has ports
    a bond that appeared while the particles sat apart
    a chain whose members drifted into different cells
    a bond that broke without the heat its rule requires

Every one of those leaves the material counts, the energy and the momentum
untouched, because the totals are exactly what the kernel already guards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

_VELOCITY = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


class ParticleRuleError(ValueError):
    """A specification cannot be read as a set of particle rules."""


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ParticleRuleError(f"{what} must be an integer, found {value!r}")
    return value


@dataclass(frozen=True)
class BondRule:
    rule_id: str
    left_kind: int
    right_kind: int
    left_orientation: str
    right_orientation: str
    minimum_collision_energy: int
    break_heat: int
    release_left: str
    release_right: str

    def accepts(self, left_kind: int, left_orientation: str,
                right_kind: int, right_orientation: str) -> bool:
        """Whether this rule joins that ordered pair, in either role order."""
        direct = (left_kind == self.left_kind and right_kind == self.right_kind
                  and left_orientation == self.left_orientation
                  and right_orientation == self.right_orientation)
        reverse = (right_kind == self.left_kind and left_kind == self.right_kind
                   and right_orientation == self.left_orientation
                   and left_orientation == self.right_orientation)
        return direct or reverse


@dataclass(frozen=True)
class ParticleRules:
    width: int
    height: int
    boundary: str
    masses: Mapping[int, int]
    ports: Mapping[int, int]
    bond_rules: tuple[BondRule, ...]
    chains_may_move: bool

    @property
    def wraps(self) -> bool:
        return self.boundary == "wrap"

    def rule(self, rule_id: str) -> BondRule | None:
        return next((item for item in self.bond_rules if item.rule_id == rule_id), None)

    def port_limit(self, kind: int) -> int:
        return self.ports.get(kind, 1) if self.chains_may_move else 1

    def steps(self, start: tuple[int, int], end: tuple[int, int]) -> int:
        """How many single-cell steps separate the two positions, or -1.

        Returns 0 for no movement, 1 for one legal step, and -1 for anything
        a single tick of streaming cannot produce.
        """
        if start == end:
            return 0
        dx, dy = end[0] - start[0], end[1] - start[1]
        if self.wraps:
            if dx > self.width // 2:
                dx -= self.width
            elif dx < -(self.width // 2):
                dx += self.width
            if dy > self.height // 2:
                dy -= self.height
            elif dy < -(self.height // 2):
                dy += self.height
        return 1 if (abs(dx), abs(dy)) in ((1, 0), (0, 1)) else -1

    def heading(self, start: tuple[int, int], end: tuple[int, int]) -> str | None:
        """The direction a single step from `start` to `end` corresponds to."""
        for name, (dx, dy) in _VELOCITY.items():
            moved = ((start[0] + dx) % self.width if self.wraps else start[0] + dx,
                     (start[1] + dy) % self.height if self.wraps else start[1] + dy)
            if moved == end:
                return name
        return None


def read_particle_rules(spec: Mapping[str, Any]) -> ParticleRules:
    """Extract the particle contract from a world specification document."""
    if not isinstance(spec, Mapping):
        raise ParticleRuleError("world spec must be a mapping")
    causal = spec.get("causal_world") if "causal_world" in spec else spec
    if not isinstance(causal, Mapping):
        raise ParticleRuleError("no causal world section")
    kernel = causal.get("kernel") or {}

    masses: dict[int, int] = {}
    ports: dict[int, int] = {}
    for material in causal.get("materials") or ():
        kind = _integer(material.get("kind"), "material kind")
        masses[kind] = _integer(material.get("mass"), f"mass of kind {kind}")
        ports[kind] = _integer(material.get("ports", 1), f"ports of kind {kind}")

    rules = []
    for raw in causal.get("bond_rules") or ():
        rules.append(BondRule(
            rule_id=str(raw.get("rule_id")),
            left_kind=_integer(raw.get("left_kind"), "left_kind"),
            right_kind=_integer(raw.get("right_kind"), "right_kind"),
            left_orientation=str(raw.get("left_orientation")),
            right_orientation=str(raw.get("right_orientation")),
            minimum_collision_energy=_integer(
                raw.get("minimum_collision_energy", 0), "minimum_collision_energy"),
            break_heat=_integer(raw.get("break_heat", 0), "break_heat"),
            release_left=str(raw.get("release_left")),
            release_right=str(raw.get("release_right")),
        ))

    return ParticleRules(
        width=_integer(kernel.get("width"), "kernel width"),
        height=_integer(kernel.get("height"), "kernel height"),
        boundary=str(kernel.get("boundary", "wrap")),
        masses=masses,
        ports=ports,
        bond_rules=tuple(rules),
        # Only a v2 causal world lets a particle hold several bonds or a chain
        # travel; under v1 both are violations rather than permitted behaviour.
        chains_may_move=str(causal.get("format", "")).endswith("-v2"),
    )


@dataclass(frozen=True)
class ParticleView:
    """The particle side of one snapshot."""

    particles: Mapping[int, Mapping[str, Any]]
    bonds: tuple[Mapping[str, Any], ...]
    heat: Mapping[tuple[int, int], int]

    def at(self, particle_id: int) -> tuple[int, int]:
        item = self.particles[particle_id]
        return (item["x"], item["y"])

    def bonded_pairs(self) -> set[frozenset[int]]:
        return {frozenset((bond["left_id"], bond["right_id"])) for bond in self.bonds}

    def bond_count(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for bond in self.bonds:
            for side in ("left_id", "right_id"):
                counts[bond[side]] = counts.get(bond[side], 0) + 1
        return counts

    def chains(self) -> list[set[int]]:
        """Connected groups of bonded particles, by breadth-first walk."""
        neighbours: dict[int, set[int]] = {}
        for bond in self.bonds:
            neighbours.setdefault(bond["left_id"], set()).add(bond["right_id"])
            neighbours.setdefault(bond["right_id"], set()).add(bond["left_id"])
        seen: set[int] = set()
        groups: list[set[int]] = []
        for start in sorted(neighbours):
            if start in seen:
                continue
            group, queue = {start}, [start]
            seen.add(start)
            while queue:
                for neighbour in neighbours[queue.pop()]:
                    if neighbour not in group:
                        group.add(neighbour)
                        seen.add(neighbour)
                        queue.append(neighbour)
            groups.append(group)
        return groups


def read_particles(snapshot: Mapping[str, Any]) -> ParticleView:
    causal = snapshot.get("causal")
    if not isinstance(causal, Mapping):
        raise ParticleRuleError("snapshot has no causal section")
    particles = {}
    for item in causal.get("particles") or ():
        particles[_integer(item.get("particle_id"), "particle_id")] = item
    heat = {}
    for cell in causal.get("heat") or ():
        heat[(cell["x"], cell["y"])] = _integer(cell.get("energy", 0), "heat energy")
    return ParticleView(particles=particles,
                        bonds=tuple(causal.get("bonds") or ()),
                        heat=heat)


def check_particle_transition(rules: ParticleRules, before: ParticleView,
                              after: ParticleView) -> list[tuple[str, str, int | None]]:
    """Judge one causal stage. Returns `(code, detail, particle_id)` findings."""
    found: list[tuple[str, str, int | None]] = []

    def note(code: str, detail: str, particle_id: int | None = None) -> None:
        found.append((code, detail, particle_id))

    if set(before.particles) != set(after.particles):
        appeared = sorted(set(after.particles) - set(before.particles))
        vanished = sorted(set(before.particles) - set(after.particles))
        note("particle_roster_changed",
             f"appeared {appeared}, vanished {vanished}; the causal stage neither "
             f"creates nor destroys particles")
        return found

    before_pairs, after_pairs = before.bonded_pairs(), after.bonded_pairs()
    held_after = {item for pair in after_pairs for item in pair}

    # --- movement -----------------------------------------------------------
    for particle_id, item in sorted(after.particles.items()):
        start, end = before.at(particle_id), after.at(particle_id)
        steps = rules.steps(start, end)
        if steps < 0:
            note("particle_moved_more_than_one_cell",
                 f"moved {start} -> {end}, which one tick of streaming cannot do",
                 particle_id)
            continue
        if steps == 0:
            continue
        heading = rules.heading(start, end)
        was_held = particle_id in {member for pair in before_pairs for member in pair}
        still_held = particle_id in held_after

        if was_held and still_held:
            # Bonded at both ends of the tick. Under v1 it should not have
            # moved at all; under v2 it may have travelled with its chain,
            # which the chain checks below cover.
            if not rules.chains_may_move:
                note("bonded_particle_moved",
                     f"moved {start} -> {end} while bonded, which v1 does not permit",
                     particle_id)
            continue
        if was_held:
            # Released this tick: breaking runs before streaming, so a freed
            # particle legitimately takes one step in the direction its rule
            # sent it. Its pre-tick heading says nothing about that step.
            continue
        if still_held:
            # Arrived and bonded in the same tick: it moved while still free.
            if before.particles[particle_id].get("kinetic_energy", 0) == 0:
                note("still_particle_moved",
                     f"moved {start} -> {end} while carrying no motion", particle_id)
            continue
        if before.particles[particle_id].get("kinetic_energy", 0) == 0:
            note("still_particle_moved",
                 f"moved {start} -> {end} while carrying no motion", particle_id)
        elif heading != before.particles[particle_id].get("direction"):
            note("particle_moved_off_its_heading",
                 f"headed {before.particles[particle_id].get('direction')!r} but moved "
                 f"{start} -> {end}", particle_id)

    # --- bonds that appeared ------------------------------------------------
    for pair in sorted(after_pairs - before_pairs, key=sorted):
        left, right = sorted(pair)
        bond = next(item for item in after.bonds
                    if frozenset((item["left_id"], item["right_id"])) == pair)
        rule = rules.rule(str(bond.get("rule_id")))
        if rule is None:
            note("bond_without_a_declared_rule",
                 f"{left}-{right} formed under rule {bond.get('rule_id')!r}, "
                 f"which the world does not declare", left)
            continue
        first, second = before.particles[left], before.particles[right]
        if not rule.accepts(first["kind"], first.get("orientation"),
                            second["kind"], second.get("orientation")):
            note("bond_rule_does_not_match_the_pair",
                 f"{left}-{right} bonded under {rule.rule_id!r}, which does not join "
                 f"{first.get('orientation')}/{second.get('orientation')} of those kinds",
                 left)
        if after.at(left) != after.at(right):
            note("bond_across_separate_cells",
                 f"{left}-{right} bonded while at {after.at(left)} and {after.at(right)}",
                 left)
        arriving = first.get("kinetic_energy", 0) + second.get("kinetic_energy", 0)
        if arriving < rule.minimum_collision_energy:
            note("bond_below_minimum_collision_energy",
                 f"{left}-{right} bonded with {arriving} of motion, under the "
                 f"{rule.minimum_collision_energy} its rule requires", left)

    # --- bonds that broke ---------------------------------------------------
    for pair in sorted(before_pairs - after_pairs, key=sorted):
        left, right = sorted(pair)
        bond = next(item for item in before.bonds
                    if frozenset((item["left_id"], item["right_id"])) == pair)
        rule = rules.rule(str(bond.get("rule_id")))
        if rule is None:
            continue
        point = (bond["x"], bond["y"])
        available = before.heat.get(point, 0)
        if available < rule.break_heat:
            note("bond_broke_without_the_heat_its_rule_requires",
                 f"{left}-{right} broke at {point} with {available} heat, under the "
                 f"{rule.break_heat} its rule requires", left)

    # --- ports and chain integrity -----------------------------------------
    for particle_id, count in sorted(after.bond_count().items()):
        kind = after.particles[particle_id]["kind"]
        allowed = rules.port_limit(kind)
        if count > allowed:
            note("more_bonds_than_declared_ports",
                 f"holds {count} bonds; material {kind} declares {allowed}", particle_id)

    for members in after.chains():
        places = {after.at(item) for item in members}
        if len(places) > 1:
            note("chain_members_in_different_cells",
                 f"chain {sorted(members)} spans {sorted(places)}", min(members))
        holders = [item for item in sorted(members)
                   if after.particles[item].get("kinetic_energy", 0)]
        if len(holders) > 1:
            note("chain_records_motion_on_several_members",
                 f"chain {sorted(members)} has motion on {holders}", min(members))
        if not rules.chains_may_move and holders:
            note("bonded_particle_carries_motion",
                 f"chain {sorted(members)} carries motion, which v1 stores in the bond",
                 min(members))

    if not rules.chains_may_move:
        for particle_id in sorted(held_after):
            if after.particles[particle_id].get("kinetic_energy", 0):
                note("bonded_particle_carries_motion",
                     "a v1 bond parks the motion it absorbed", particle_id)

    return found
