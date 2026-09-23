"""causal v5: the runtime state and its invariants (plan section 3.2).

State = time + elements (label, kind, position) + structures (members,
bonds, momentum, internal energy). A structure's identity is its member set
(P6): there is no separate id, so renaming elements cannot move physics.
Mass, velocity and kinetic energy are derived, never stored (E1).

Invariants checked on every construction:
  * every element belongs to exactly one structure;
  * a structure's members are exactly one connected component of its bonds;
  * a bond joins two faces that face each other, flush and overlapping
    along the face (a bond at a bare corner is not a face contact);
  * a port holds at most one bond;
  * no two elements' interiors overlap (touching is allowed);
  * internal energy >= 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping

from .v5_number import Vec, add, cross, scale, ser, ser_vec
from .v5_spec import OPPOSITE, BondSpec, WorldSpecV5


@dataclass(frozen=True)
class Element:
    label: str
    kind: int
    position: Vec


@dataclass(frozen=True)
class Structure:
    members: frozenset[str]
    bonds: frozenset[BondSpec]
    momentum: Vec
    internal_energy: Fraction

    @property
    def key(self) -> tuple[str, ...]:
        return tuple(sorted(self.members))


@dataclass(frozen=True)
class StateV5:
    time: Fraction
    elements: tuple[Element, ...]
    structures: tuple[Structure, ...]

    # -- derived quantities --------------------------------------------------
    def element(self, label: str) -> Element:
        return self._by_label()[label]

    def _by_label(self) -> dict[str, Element]:
        return {e.label: e for e in self.elements}

    def structure_of(self, label: str) -> Structure:
        return next(s for s in self.structures if label in s.members)

    def mass(self, spec: WorldSpecV5, structure: Structure) -> Fraction:
        by_label = self._by_label()
        return sum((spec.material(by_label[m].kind).mass for m in structure.members), Fraction(0))

    def velocity(self, spec: WorldSpecV5, structure: Structure) -> Vec:
        return scale(structure.momentum, 1 / self.mass(spec, structure))

    def kinetic_energy(self, spec: WorldSpecV5, structure: Structure) -> Fraction:
        p = structure.momentum
        return (p[0] * p[0] + p[1] * p[1]) / (2 * self.mass(spec, structure))

    def center_of_mass(self, spec: WorldSpecV5, structure: Structure) -> Vec:
        by_label = self._by_label()
        total = (Fraction(0), Fraction(0))
        for m in structure.members:
            total = add(total, scale(by_label[m].position, spec.material(by_label[m].kind).mass))
        return scale(total, 1 / self.mass(spec, structure))

    def angular_momentum(self, spec: WorldSpecV5, structures: Iterable[Structure]) -> Fraction:
        """z component about the origin. Rigid, non-rotating bodies: L = X_cm x P."""
        return sum((cross(self.center_of_mass(spec, s), s.momentum) for s in structures), Fraction(0))

    def totals(self, spec: WorldSpecV5) -> tuple[Vec, Fraction]:
        """(total momentum, total K + U)."""
        p = (Fraction(0), Fraction(0))
        energy = Fraction(0)
        for s in self.structures:
            p = add(p, s.momentum)
            energy += self.kinetic_energy(spec, s) + s.internal_energy
        return p, energy

    # -- canonical form ------------------------------------------------------
    def canonical(self) -> dict[str, object]:
        return {
            "elements": [{"kind": e.kind, "label": e.label, "position": ser_vec(e.position)}
                         for e in sorted(self.elements, key=lambda e: e.label)],
            "structures": [{"bonds": [b.canonical() for b in sorted(s.bonds)], "internal_energy": ser(s.internal_energy),
                            "members": list(s.key), "momentum": ser_vec(s.momentum)}
                           for s in sorted(self.structures, key=lambda s: s.key)],
            "time": ser(self.time),
        }

    def relabeled(self, mapping: Mapping[str, str]) -> "StateV5":
        return StateV5(self.time,
                       tuple(Element(mapping[e.label], e.kind, e.position) for e in self.elements),
                       tuple(Structure(frozenset(mapping[m] for m in s.members),
                                       frozenset(b.relabeled(mapping) for b in s.bonds), s.momentum,
                                       s.internal_energy) for s in self.structures))


def _components(members: frozenset[str], bonds: Iterable[BondSpec]) -> list[frozenset[str]]:
    parent = {m: m for m in members}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for bond in bonds:
        parent[find(bond.a_label)] = find(bond.b_label)
    groups: dict[str, set[str]] = {}
    for m in members:
        groups.setdefault(find(m), set()).add(m)
    return [frozenset(g) for g in groups.values()]


def face_touch(spec: WorldSpecV5, a: Element, b: Element) -> str | None:
    """The face of `a` that `b` is flush against with positive overlap along
    it, or None (apart, overlapping, or touching only at a corner)."""
    w = spec.material(a.kind).contact_half_width + spec.material(b.kind).contact_half_width
    dx, dy = b.position[0] - a.position[0], b.position[1] - a.position[1]
    if abs(dx) == w and abs(dy) < w:
        return "E" if dx > 0 else "W"
    if abs(dy) == w and abs(dx) < w:
        return "S" if dy > 0 else "N"
    return None


def interiors_overlap(spec: WorldSpecV5, a: Element, b: Element) -> bool:
    w = spec.material(a.kind).contact_half_width + spec.material(b.kind).contact_half_width
    return abs(b.position[0] - a.position[0]) < w and abs(b.position[1] - a.position[1]) < w


def validate(spec: WorldSpecV5, state: StateV5) -> None:
    by_label = {e.label: e for e in state.elements}
    if len(by_label) != len(state.elements):
        raise ValueError("element labels must be unique")
    seen: set[str] = set()
    ports_used: set[tuple[str, str]] = set()
    for s in state.structures:
        if not s.members:
            raise ValueError("a structure has at least one member")
        if s.members & seen:
            raise ValueError("an element belongs to at most one structure")
        seen |= s.members
        if s.internal_energy < 0:
            raise ValueError("internal energy is >= 0")
        for bond in s.bonds:
            for label, port in bond.ends():
                if label not in s.members:
                    raise ValueError("a bond joins members of its own structure")
                if port not in spec.material(by_label[label].kind).ports:
                    raise ValueError(f"{label} has no {port} port")
                if (label, port) in ports_used:
                    raise ValueError(f"port {label}.{port} holds two bonds")
                ports_used.add((label, port))
            if OPPOSITE[bond.a_port] != bond.b_port:
                raise ValueError("a bond's faces must face each other")
            if face_touch(spec, by_label[bond.a_label], by_label[bond.b_label]) != bond.a_port:
                raise ValueError(f"bond {bond.canonical()} is not a flush face contact on {bond.a_port}")
        if len(_components(s.members, s.bonds)) != 1:
            raise ValueError("a structure's members are exactly one connected component of its bonds")
    if seen != set(by_label):
        raise ValueError("every element belongs to exactly one structure")
    elements = sorted(state.elements, key=lambda e: e.label)
    for i, a in enumerate(elements):
        for b in elements[i + 1:]:
            if interiors_overlap(spec, a, b):
                raise ValueError(f"elements {a.label} and {b.label} overlap")


def initial_state(spec: WorldSpecV5) -> StateV5:
    state = StateV5(Fraction(0),
                    tuple(Element(e.label, e.kind, e.position) for e in spec.elements),
                    tuple(Structure(s.members, s.bonds, s.momentum, s.internal_energy) for s in spec.structures))
    validate(spec, state)
    return state

