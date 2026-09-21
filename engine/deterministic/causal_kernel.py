"""A1 deterministic local energy, bonding, and separation kernel."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, replace

from .causal_spec import BondRuleSpec, CausalParticleSpec, CausalWorldSpec, HeatCellSpec
from .spec import DIRECTIONS

VELOCITY = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class PhysicalBond:
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


@dataclass(frozen=True)
class CausalWorldState:
    tick: int
    particles: tuple[CausalParticleSpec, ...]
    heat: tuple[HeatCellSpec, ...]
    bonds: tuple[PhysicalBond, ...] = ()

    def __post_init__(self) -> None:
        particles, heat, bonds = tuple(sorted(self.particles)), tuple(sorted(self.heat)), tuple(sorted(self.bonds))
        if len({item.particle_id for item in particles}) != len(particles):
            raise ValueError("particle ids must be unique")
        if len({(item.kind, item.x, item.y, item.direction) for item in particles}) != len(particles):
            raise ValueError("directional material channels must be unique")
        if len({(item.x, item.y) for item in heat}) != len(heat):
            raise ValueError("heat cells must be unique")
        used = [value for bond in bonds for value in (bond.left_id, bond.right_id)]
        if len(used) != len(set(used)):
            raise ValueError("causal v1 permits at most one bond per particle")
        by_id = {item.particle_id: item for item in particles}
        for bond in bonds:
            if bond.left_id not in by_id or bond.right_id not in by_id:
                raise ValueError("bond refers to a missing particle")
            if by_id[bond.left_id].x != bond.x or by_id[bond.left_id].y != bond.y or by_id[bond.right_id].x != bond.x or by_id[bond.right_id].y != bond.y:
                raise ValueError("bonded particles must share the bond location")
            if by_id[bond.left_id].kinetic_energy or by_id[bond.right_id].kinetic_energy:
                raise ValueError("bonded particles must store motion energy in the bond")
        object.__setattr__(self, "particles", particles); object.__setattr__(self, "heat", heat); object.__setattr__(self, "bonds", bonds)

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "bonds": [item.canonical() for item in self.bonds],
            "heat": [item.canonical() for item in self.heat],
            "particles": [item.canonical() for item in self.particles],
            "tick": self.tick,
        }

    def total_energy(self) -> int:
        return sum(item.kinetic_energy for item in self.particles) + sum(item.energy for item in self.heat) + sum(item.stored_energy for item in self.bonds)

    def material_counts(self) -> dict[int, int]:
        result: dict[int, int] = {}
        for item in self.particles: result[item.kind] = result.get(item.kind, 0) + 1
        return dict(sorted(result.items()))

    def momentum(self, spec: CausalWorldSpec) -> tuple[int, int]:
        masses = {item.kind: item.mass for item in spec.materials}; x = y = 0
        bonded = {value for bond in self.bonds for value in (bond.left_id, bond.right_id)}
        for item in self.particles:
            if item.particle_id in bonded: continue
            dx, dy = VELOCITY[item.direction]
            x += masses[item.kind] * item.kinetic_energy * dx
            y += masses[item.kind] * item.kinetic_energy * dy
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


def initial_causal_state(spec: CausalWorldSpec) -> CausalWorldState:
    return CausalWorldState(0, spec.particles, spec.heat)


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
    return CausalWorldState(state.tick, tuple(particles.values()), _heat_cells(heat), tuple(remaining))


def _stream_free(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    bonded = {value for bond in state.bonds for value in (bond.left_id, bond.right_id)}; particles = []
    for item in state.particles:
        if item.particle_id in bonded or item.kinetic_energy == 0:
            particles.append(item); continue
        dx, dy = VELOCITY[item.direction]
        particles.append(replace(item, x=(item.x + dx) % spec.kernel.width, y=(item.y + dy) % spec.kernel.height))
    return CausalWorldState(state.tick, tuple(particles), state.heat, state.bonds)


def _match_rule(rules: tuple[BondRuleSpec, ...], first: CausalParticleSpec, second: CausalParticleSpec) -> tuple[BondRuleSpec, bool] | None:
    for rule in rules:
        direct = first.kind == rule.left_kind and second.kind == rule.right_kind and first.orientation == rule.left_orientation and second.orientation == rule.right_orientation
        reverse = second.kind == rule.left_kind and first.kind == rule.right_kind and second.orientation == rule.left_orientation and first.orientation == rule.right_orientation
        if direct: return rule, False
        if reverse: return rule, True
    return None


def _resolve_collisions(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    bonded = {value for bond in state.bonds for value in (bond.left_id, bond.right_id)}
    groups: dict[tuple[int, int], list[CausalParticleSpec]] = defaultdict(list)
    for item in state.particles:
        if item.particle_id not in bonded: groups[(item.x, item.y)].append(item)
    particles = {item.particle_id: item for item in state.particles}; bonds = list(state.bonds)
    masses = {item.kind: item.mass for item in spec.materials}
    for (x, y), group in sorted(groups.items()):
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
    return CausalWorldState(state.tick, tuple(particles.values()), state.heat, tuple(bonds))


def step_causal_world(spec: CausalWorldSpec, state: CausalWorldState) -> CausalWorldState:
    counts, energy, momentum = state.material_counts(), state.total_energy(), state.momentum(spec)
    result = _break_existing(spec, state)
    result = _stream_free(spec, result)
    result = _resolve_collisions(spec, result)
    result = CausalWorldState(state.tick + 1, result.particles, result.heat, result.bonds)
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
