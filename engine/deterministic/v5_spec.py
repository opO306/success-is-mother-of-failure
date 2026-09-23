"""causal v5: the world specification and the run request (plan section 3).

Three things are kept apart:

    world spec      the laws and the first picture of the world      (here, digest)
    runtime state   where everything is now                          (v5_state)
    run request     how long to run and how often to look             (here, NOT in the digest)

The spec holds nothing an executor invents: no event queue, no cache, no
observation interval. Two runs of one world looked at every 1 or every 1/3
time unit share one spec digest (designer decision K1: time is continuous,
the observation interval is not physics).

Geometry (designer decisions K3, P1): every element is a non-rotating
axis-aligned square of half width `contact_half_width`, on an unbounded
2-D plane (v5-v1 domain only, not a universal law). Ports are the square's
faces: E = +x, W = -x, S = +y, N = -y (y grows southward, as in v1-v4).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Mapping

from .v5_number import Vec, q, ser, ser_vec, vec

FORMAT = "deterministic-causal-world-spec-v5"
PORTS = ("E", "N", "S", "W")
OPPOSITE = {"E": "W", "W": "E", "N": "S", "S": "N"}
OUTWARD = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _no_floats(value: Any, path: str = "spec") -> None:
    if isinstance(value, float):
        raise TypeError(f"{path}: floats are refused in a v5 spec")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _no_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _no_floats(item, f"{path}[{index}]")


@dataclass(frozen=True)
class Unit:
    name: str
    si: Fraction                       # how many SI base units one unit is

    def canonical(self) -> dict[str, object]:
        return {"name": self.name, "si": ser(self.si)}


@dataclass(frozen=True)
class Units:
    """Required (designer decision E8). Energy's unit is derived: mass * length^2 / time^2."""
    mass: Unit
    length: Unit
    time: Unit

    def canonical(self) -> dict[str, object]:
        return {"length": self.length.canonical(), "mass": self.mass.canonical(), "time": self.time.canonical()}


@dataclass(frozen=True)
class Material:
    kind: int
    mass: Fraction
    contact_half_width: Fraction       # reach of contact, not an excluded volume (S2 as amended)
    ports: frozenset[str]

    def canonical(self) -> dict[str, object]:
        return {"contact_half_width": ser(self.contact_half_width), "kind": self.kind,
                "mass": ser(self.mass), "ports": sorted(self.ports)}


@dataclass(frozen=True)
class BondRule:
    rule_id: str
    a: tuple[int, str]                 # (kind, port)
    b: tuple[int, str]
    threshold: Fraction                # compared with the pair's relative KE, 1/2 mu |dv|^2 (E5)

    @property
    def key(self) -> frozenset:
        return frozenset([self.a, self.b]) if self.a != self.b else frozenset([self.a])

    def matches(self, one: tuple[int, str], other: tuple[int, str]) -> bool:
        return sorted([one, other]) == sorted([self.a, self.b])

    def canonical(self) -> dict[str, object]:
        a, b = sorted([self.a, self.b])
        return {"a": list(a), "b": list(b), "rule_id": self.rule_id, "threshold": ser(self.threshold)}


@dataclass(frozen=True, order=True)
class BondSpec:
    """A bond between two elements' ports. Stored in one canonical endpoint
    order so (A,E,B,W) and (B,W,A,E) are the same record -- the order is a
    serialisation convention, never physics."""
    a_label: str
    a_port: str
    b_label: str
    b_port: str

    def __post_init__(self) -> None:
        if (self.b_label, self.b_port) < (self.a_label, self.a_port):
            a_label, a_port = self.a_label, self.a_port
            object.__setattr__(self, "a_label", self.b_label)
            object.__setattr__(self, "a_port", self.b_port)
            object.__setattr__(self, "b_label", a_label)
            object.__setattr__(self, "b_port", a_port)

    def ends(self) -> tuple[tuple[str, str], tuple[str, str]]:
        return (self.a_label, self.a_port), (self.b_label, self.b_port)

    def relabeled(self, mapping: Mapping[str, str]) -> "BondSpec":
        return BondSpec(mapping[self.a_label], self.a_port, mapping[self.b_label], self.b_port)

    def canonical(self) -> list[str]:
        return [self.a_label, self.a_port, self.b_label, self.b_port]


@dataclass(frozen=True)
class ElementSpec:
    label: str
    kind: int
    position: Vec

    def canonical(self) -> dict[str, object]:
        return {"kind": self.kind, "label": self.label, "position": ser_vec(self.position)}


@dataclass(frozen=True)
class StructureSpec:
    members: frozenset[str]
    bonds: frozenset[BondSpec] = frozenset()
    momentum: Vec = (Fraction(0), Fraction(0))
    internal_energy: Fraction = Fraction(0)

    def canonical(self) -> dict[str, object]:
        return {"bonds": [b.canonical() for b in sorted(self.bonds)], "internal_energy": ser(self.internal_energy),
                "members": sorted(self.members), "momentum": ser_vec(self.momentum)}


@dataclass(frozen=True)
class WorldSpecV5:
    world_id: str
    units: Units
    materials: tuple[Material, ...]
    bond_rules: tuple[BondRule, ...]
    elements: tuple[ElementSpec, ...]
    structures: tuple[StructureSpec, ...]
    format: str = FORMAT

    def __post_init__(self) -> None:
        kinds = [m.kind for m in self.materials]
        if len(set(kinds)) != len(kinds):
            raise ValueError("material kinds must be unique")
        for material in self.materials:
            if material.mass <= 0:
                raise ValueError("mass must be > 0 (P5)")
            if material.contact_half_width <= 0:
                raise ValueError("contact_half_width must be > 0")
            if not material.ports <= set(PORTS):
                raise ValueError(f"ports are faces {PORTS}")
        by_kind = {m.kind: m for m in self.materials}
        keys = set()
        for rule in self.bond_rules:
            for kind, port in (rule.a, rule.b):
                if kind not in by_kind or port not in by_kind[kind].ports:
                    raise ValueError(f"rule {rule.rule_id} names a port its material does not have")
            if OPPOSITE[rule.a[1]] != rule.b[1]:
                raise ValueError(f"rule {rule.rule_id}: its two faces must face each other")
            if rule.threshold < 0:
                raise ValueError("thresholds are >= 0")
            if rule.key in keys:
                raise ValueError("at most one rule per (kind, port) pair -- two would need an order to choose")
            keys.add(rule.key)
        labels = [e.label for e in self.elements]
        if len(set(labels)) != len(labels):
            raise ValueError("element labels must be unique")
        for element in self.elements:
            if element.kind not in by_kind:
                raise ValueError(f"element {element.label} has an undeclared kind")
        members = [label for s in self.structures for label in s.members]
        if sorted(members) != sorted(labels):
            raise ValueError("every element belongs to exactly one structure (a free particle is a structure of one)")

    def material(self, kind: int) -> Material:
        return next(m for m in self.materials if m.kind == kind)

    def rule_for(self, one: tuple[int, str], other: tuple[int, str]) -> BondRule | None:
        return next((r for r in self.bond_rules if r.matches(one, other)), None)

    def canonical(self) -> dict[str, object]:
        return {"bond_rules": sorted((r.canonical() for r in self.bond_rules), key=lambda r: (r["a"], r["b"])),
                "elements": sorted((e.canonical() for e in self.elements), key=lambda e: e["label"]),
                "format": self.format,
                "materials": sorted((m.canonical() for m in self.materials), key=lambda m: m["kind"]),
                "structures": sorted((s.canonical() for s in self.structures), key=lambda s: s["members"]),
                "units": self.units.canonical(), "world_id": self.world_id}

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def relabeled(self, mapping: Mapping[str, str]) -> "WorldSpecV5":
        return WorldSpecV5(
            self.world_id, self.units, self.materials, self.bond_rules,
            tuple(ElementSpec(mapping[e.label], e.kind, e.position) for e in self.elements),
            tuple(StructureSpec(frozenset(mapping[m] for m in s.members),
                                frozenset(b.relabeled(mapping) for b in s.bonds), s.momentum, s.internal_energy)
                  for s in self.structures), self.format)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "WorldSpecV5":
        _no_floats(raw)
        if raw.get("format") != FORMAT:
            raise ValueError(f"format must be {FORMAT}")
        if "units" not in raw:
            raise ValueError("units are required (E8)")
        u = raw["units"]
        units = Units(*(Unit(str(u[k]["name"]), q(u[k]["si"])) for k in ("mass", "length", "time")))
        materials = tuple(Material(int(m["kind"]), q(m["mass"]), q(m["contact_half_width"]), frozenset(m["ports"]))
                          for m in raw["materials"])
        rules = tuple(BondRule(str(r["rule_id"]), (int(r["a"]["kind"]), str(r["a"]["port"])),
                               (int(r["b"]["kind"]), str(r["b"]["port"])), q(r["threshold"]))
                      for r in raw.get("bond_rules", ()))
        elements = tuple(ElementSpec(str(e["label"]), int(e["kind"]), vec(e["position"])) for e in raw["elements"])
        structures = tuple(StructureSpec(frozenset(str(x) for x in s["members"]),
                                         frozenset(BondSpec(*map(str, b)) for b in s.get("bonds", ())),
                                         vec(s.get("momentum", ("0", "0"))), q(s.get("internal_energy", "0")))
                           for s in raw["structures"])
        return cls(str(raw["world_id"]), units, materials, rules, elements, structures)


@dataclass(frozen=True)
class RunRequest:
    """How to look at a world -- never part of the world's digest."""
    end_time: Fraction
    observation_interval: Fraction
    meter: bool = field(default=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "end_time", q(self.end_time))
        object.__setattr__(self, "observation_interval", q(self.observation_interval))
        if self.end_time < 0 or self.observation_interval <= 0:
            raise ValueError("end_time >= 0 and observation_interval > 0")

    def canonical(self) -> dict[str, object]:
        return {"end_time": ser(self.end_time), "observation_interval": ser(self.observation_interval)}
