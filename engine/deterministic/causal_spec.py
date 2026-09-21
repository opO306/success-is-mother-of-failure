"""B0.1 causal rule language for local deterministic energy and bonding."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .spec import DIRECTIONS, FORBIDDEN_COMMANDS, FORBIDDEN_KEYS

FORMAT = "deterministic-causal-world-spec-v1"


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _exact(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    missing, unknown = expected - set(value), set(value) - expected
    if missing or unknown:
        raise ValueError(f"{context} keys differ: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{context} must be an integer of at least {minimum}")
    return value


def _scan(value: Any, path: str = "world") -> None:
    if isinstance(value, float):
        raise ValueError(f"floating point is forbidden at {path}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden high-level field at {path}.{key}")
            _scan(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan(item, f"{path}[{index}]")
    elif isinstance(value, str) and value.strip().upper() in FORBIDDEN_COMMANDS:
        raise ValueError(f"forbidden high-level command at {path}")


@dataclass(frozen=True, order=True)
class CausalMaterialSpec:
    kind: int
    mass: int
    ports: int

    def canonical(self) -> dict[str, int]:
        return {"kind": self.kind, "mass": self.mass, "ports": self.ports}


@dataclass(frozen=True, order=True)
class CausalParticleSpec:
    particle_id: int
    kind: int
    x: int
    y: int
    direction: str
    orientation: str
    kinetic_energy: int

    def canonical(self) -> dict[str, object]:
        return {
            "direction": self.direction,
            "kind": self.kind,
            "kinetic_energy": self.kinetic_energy,
            "orientation": self.orientation,
            "particle_id": self.particle_id,
            "x": self.x,
            "y": self.y,
        }


@dataclass(frozen=True, order=True)
class HeatCellSpec:
    x: int
    y: int
    energy: int

    def canonical(self) -> dict[str, int]:
        return {"energy": self.energy, "x": self.x, "y": self.y}


@dataclass(frozen=True, order=True)
class BondRuleSpec:
    rule_id: str
    left_kind: int
    right_kind: int
    left_orientation: str
    right_orientation: str
    minimum_collision_energy: int
    break_heat: int
    release_left: str
    release_right: str

    def canonical(self) -> dict[str, object]:
        return {
            "break_heat": self.break_heat,
            "conserves": ["material", "energy", "momentum"],
            "event": "local_reversible_bond",
            "left_kind": self.left_kind,
            "left_orientation": self.left_orientation,
            "locality": "same_cell",
            "minimum_collision_energy": self.minimum_collision_energy,
            "release_left": self.release_left,
            "release_right": self.release_right,
            "right_kind": self.right_kind,
            "right_orientation": self.right_orientation,
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True)
class CausalKernelSpec:
    width: int
    height: int
    boundary: str
    arithmetic: str
    deterministic: bool
    tick_order: tuple[str, ...]

    def canonical(self) -> dict[str, object]:
        return {
            "arithmetic": self.arithmetic,
            "boundary": self.boundary,
            "deterministic": self.deterministic,
            "height": self.height,
            "tick_order": list(self.tick_order),
            "width": self.width,
        }


@dataclass(frozen=True)
class CausalWorldSpec:
    world_id: str
    kernel: CausalKernelSpec
    materials: tuple[CausalMaterialSpec, ...]
    particles: tuple[CausalParticleSpec, ...]
    heat: tuple[HeatCellSpec, ...]
    bond_rules: tuple[BondRuleSpec, ...]
    ticks: int
    hash_interval: int
    format: str = FORMAT

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "bond_rules": [item.canonical() for item in self.bond_rules],
            "execution": {"ticks": self.ticks},
            "format": self.format,
            "heat": [item.canonical() for item in self.heat],
            "kernel": self.kernel.canonical(),
            "materials": [item.canonical() for item in self.materials],
            "observer": {"hash_interval": self.hash_interval},
            "particles": [item.canonical() for item in self.particles],
            "world_id": self.world_id,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CausalWorldSpec":
        _scan(raw)
        _exact(raw, {"format", "world_id", "kernel", "materials", "particles", "heat", "bond_rules", "execution", "observer"}, "world")
        if raw["format"] != FORMAT:
            raise ValueError("unsupported causal world format")
        world_id = raw["world_id"]
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id must be a non-empty string")

        kr = _object(raw["kernel"], "kernel")
        _exact(kr, {"width", "height", "boundary", "arithmetic", "deterministic", "tick_order"}, "kernel")
        order = kr["tick_order"]
        required_order = ("break_existing_bonds", "stream_free_particles", "resolve_local_collisions")
        if not isinstance(order, list) or tuple(order) != required_order:
            raise ValueError("causal v1 requires the declared three-phase tick order")
        kernel = CausalKernelSpec(
            _integer(kr["width"], "kernel.width", 4), _integer(kr["height"], "kernel.height", 4),
            str(kr["boundary"]), str(kr["arithmetic"]), kr["deterministic"], tuple(order),
        )
        if kernel.boundary != "wrap" or kernel.arithmetic != "integer" or kernel.deterministic is not True:
            raise ValueError("causal v1 requires wrap, integer arithmetic, and deterministic=true")

        mr = raw["materials"]
        if not isinstance(mr, list) or not mr:
            raise ValueError("materials must be a non-empty list")
        materials = []
        for index, value in enumerate(mr):
            item = _object(value, f"materials[{index}]")
            _exact(item, {"kind", "mass", "ports"}, f"materials[{index}]")
            materials.append(CausalMaterialSpec(
                _integer(item["kind"], "material.kind"), _integer(item["mass"], "material.mass", 1),
                _integer(item["ports"], "material.ports", 1),
            ))
        if len({item.kind for item in materials}) != len(materials):
            raise ValueError("material kinds must be unique")
        kinds = {item.kind for item in materials}

        pr = raw["particles"]
        if not isinstance(pr, list):
            raise ValueError("particles must be a list")
        particles = []
        for index, value in enumerate(pr):
            item = _object(value, f"particles[{index}]")
            _exact(item, {"particle_id", "kind", "x", "y", "direction", "orientation", "kinetic_energy"}, f"particles[{index}]")
            particle = CausalParticleSpec(
                _integer(item["particle_id"], "particle_id", 1), _integer(item["kind"], "particle.kind"),
                _integer(item["x"], "particle.x"), _integer(item["y"], "particle.y"),
                str(item["direction"]), str(item["orientation"]),
                _integer(item["kinetic_energy"], "particle.kinetic_energy"),
            )
            if particle.kind not in kinds or particle.direction not in DIRECTIONS or particle.orientation not in DIRECTIONS:
                raise ValueError("particle has an unknown kind, direction, or orientation")
            if not (0 <= particle.x < kernel.width and 0 <= particle.y < kernel.height):
                raise ValueError("particle lies outside the world")
            particles.append(particle)
        if len({item.particle_id for item in particles}) != len(particles):
            raise ValueError("particle ids must be unique")
        if len({(item.kind, item.x, item.y, item.direction) for item in particles}) != len(particles):
            raise ValueError("directional material channels must be unique")

        hr = raw["heat"]
        if not isinstance(hr, list):
            raise ValueError("heat must be a list")
        heat = []
        for index, value in enumerate(hr):
            item = _object(value, f"heat[{index}]")
            _exact(item, {"x", "y", "energy"}, f"heat[{index}]")
            cell = HeatCellSpec(_integer(item["x"], "heat.x"), _integer(item["y"], "heat.y"), _integer(item["energy"], "heat.energy"))
            if not (0 <= cell.x < kernel.width and 0 <= cell.y < kernel.height):
                raise ValueError("heat cell lies outside the world")
            heat.append(cell)
        if len({(item.x, item.y) for item in heat}) != len(heat):
            raise ValueError("heat locations must be unique")

        rr = raw["bond_rules"]
        if not isinstance(rr, list):
            raise ValueError("bond_rules must be a list")
        rules = []
        for index, value in enumerate(rr):
            item = _object(value, f"bond_rules[{index}]")
            _exact(item, {"rule_id", "event", "locality", "conserves", "left_kind", "right_kind", "left_orientation", "right_orientation", "minimum_collision_energy", "break_heat", "release_left", "release_right"}, f"bond_rules[{index}]")
            if item["event"] != "local_reversible_bond" or item["locality"] != "same_cell" or item["conserves"] != ["material", "energy", "momentum"]:
                raise ValueError("bond rule must declare the fixed local event and conservation contract")
            rule = BondRuleSpec(
                str(item["rule_id"]), _integer(item["left_kind"], "rule.left_kind"),
                _integer(item["right_kind"], "rule.right_kind"), str(item["left_orientation"]),
                str(item["right_orientation"]), _integer(item["minimum_collision_energy"], "rule.minimum_collision_energy"),
                _integer(item["break_heat"], "rule.break_heat"), str(item["release_left"]), str(item["release_right"]),
            )
            if not rule.rule_id or rule.left_kind not in kinds or rule.right_kind not in kinds:
                raise ValueError("bond rule has an invalid id or material kind")
            if any(value not in DIRECTIONS for value in (rule.left_orientation, rule.right_orientation, rule.release_left, rule.release_right)):
                raise ValueError("bond rule orientations must be cardinal directions")
            lv, rv = rule.release_left, rule.release_right
            if {lv, rv} not in ({"N", "S"}, {"E", "W"}):
                raise ValueError("bond release directions must be opposite")
            rules.append(rule)
        if len({item.rule_id for item in rules}) != len(rules):
            raise ValueError("bond rule ids must be unique")
        signatures = [(r.left_kind, r.right_kind, r.left_orientation, r.right_orientation) for r in rules]
        if len(set(signatures)) != len(signatures):
            raise ValueError("bond rule physical signatures must be unique")

        masses = {item.kind: item.mass for item in materials}
        for rule in rules:
            if masses[rule.left_kind] != masses[rule.right_kind]:
                raise ValueError("causal v1 bond rules require equal masses for momentum-preserving release")
            if rule.break_heat % 2:
                raise ValueError("causal v1 break_heat must be even")
        er = _object(raw["execution"], "execution"); _exact(er, {"ticks"}, "execution")
        obs = _object(raw["observer"], "observer"); _exact(obs, {"hash_interval"}, "observer")
        return cls(world_id.strip(), kernel, tuple(sorted(materials)), tuple(sorted(particles)), tuple(sorted(heat)),
                   tuple(sorted(rules)), _integer(er["ticks"], "execution.ticks"),
                   _integer(obs["hash_interval"], "observer.hash_interval", 1))


def load_causal_world_spec(path: Path) -> CausalWorldSpec:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError("causal world specification is not valid JSON") from exc
    return CausalWorldSpec.from_mapping(_object(raw, "world"))
