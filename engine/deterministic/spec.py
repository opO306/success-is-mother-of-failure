"""B0 world specification and immutable constitution checks."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

FORMAT = "deterministic-world-spec-v1"
DIRECTIONS = ("N", "E", "S", "W")
FORBIDDEN_KEYS = {
    "alive", "cell_type", "fitness", "fitness_score", "gene", "goal",
    "instinct", "intelligence", "organism", "reproduction_success",
    "survival_bonus", "species",
}
FORBIDDEN_COMMANDS = {
    "ADD_INSTINCT", "COPY_GENE", "DIVIDE_CELL", "INCREASE_FITNESS",
    "MAKE_LIFE", "PROTECT_ORGANISM",
}


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        raise ValueError(f"{context} keys differ: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{context} must be an integer of at least {minimum}")
    return value


def _scan_constitution(value: Any, path: str = "world") -> None:
    if isinstance(value, float):
        raise ValueError(f"floating point is forbidden in deterministic v1 at {path}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden high-level field at {path}.{key}")
            _scan_constitution(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_constitution(item, f"{path}[{index}]")
    elif isinstance(value, str) and value.strip().upper() in FORBIDDEN_COMMANDS:
        raise ValueError(f"forbidden high-level command at {path}")


@dataclass(frozen=True, order=True)
class MaterialSpec:
    kind: int
    mass: int

    def canonical(self) -> dict[str, int]:
        return {"kind": self.kind, "mass": self.mass}


@dataclass(frozen=True, order=True)
class ParticleSpec:
    kind: int
    x: int
    y: int
    direction: str

    def canonical(self) -> dict[str, object]:
        return {"direction": self.direction, "kind": self.kind, "x": self.x, "y": self.y}


@dataclass(frozen=True)
class KernelSpec:
    kind: str
    deterministic: bool
    arithmetic: str
    dimensions: int
    width: int
    height: int
    boundary: str
    collision: str

    def canonical(self) -> dict[str, object]:
        return {
            "arithmetic": self.arithmetic,
            "boundary": self.boundary,
            "collision": self.collision,
            "deterministic": self.deterministic,
            "dimensions": self.dimensions,
            "height": self.height,
            "kind": self.kind,
            "width": self.width,
        }


@dataclass(frozen=True)
class ExecutionSpec:
    ticks: int

    def canonical(self) -> dict[str, int]:
        return {"ticks": self.ticks}


@dataclass(frozen=True)
class ObserverSpec:
    hash_interval: int

    def canonical(self) -> dict[str, int]:
        return {"hash_interval": self.hash_interval}


@dataclass(frozen=True)
class DeterministicWorldSpec:
    world_id: str
    kernel: KernelSpec
    materials: tuple[MaterialSpec, ...]
    initial_particles: tuple[ParticleSpec, ...]
    execution: ExecutionSpec
    observer: ObserverSpec
    format: str = FORMAT

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {
            "execution": self.execution.canonical(),
            "format": self.format,
            "initial_particles": [item.canonical() for item in self.initial_particles],
            "kernel": self.kernel.canonical(),
            "materials": [item.canonical() for item in self.materials],
            "observer": self.observer.canonical(),
            "world_id": self.world_id,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DeterministicWorldSpec":
        _scan_constitution(raw)
        _exact_keys(raw, {"format", "world_id", "kernel", "materials", "initial_particles", "execution", "observer"}, "world")
        if raw["format"] != FORMAT:
            raise ValueError(f"unsupported world format: {raw['format']}")
        world_id = raw["world_id"]
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id must be a non-empty string")

        kernel_raw = _object(raw["kernel"], "kernel")
        _exact_keys(kernel_raw, {"kind", "deterministic", "arithmetic", "dimensions", "width", "height", "boundary", "collision"}, "kernel")
        kernel = KernelSpec(
            str(kernel_raw["kind"]), kernel_raw["deterministic"], str(kernel_raw["arithmetic"]),
            _integer(kernel_raw["dimensions"], "kernel.dimensions", minimum=1),
            _integer(kernel_raw["width"], "kernel.width", minimum=4),
            _integer(kernel_raw["height"], "kernel.height", minimum=4),
            str(kernel_raw["boundary"]), str(kernel_raw["collision"]),
        )
        if kernel.kind != "hpp-lattice-v1" or kernel.deterministic is not True:
            raise ValueError("deterministic v1 requires hpp-lattice-v1 and deterministic=true")
        if kernel.arithmetic != "integer" or kernel.dimensions != 2:
            raise ValueError("deterministic v1 requires integer arithmetic in two dimensions")
        if kernel.boundary != "wrap" or kernel.collision != "head-on-right-angle-v1":
            raise ValueError("unsupported deterministic v1 boundary or collision law")

        materials_raw = raw["materials"]
        if not isinstance(materials_raw, list) or not materials_raw:
            raise ValueError("materials must be a non-empty list")
        materials = []
        for index, value in enumerate(materials_raw):
            item = _object(value, f"materials[{index}]")
            _exact_keys(item, {"kind", "mass"}, f"materials[{index}]")
            materials.append(MaterialSpec(
                _integer(item["kind"], f"materials[{index}].kind"),
                _integer(item["mass"], f"materials[{index}].mass", minimum=1),
            ))
        if len({item.kind for item in materials}) != len(materials):
            raise ValueError("material kinds must be unique")
        kinds = {item.kind for item in materials}

        particles_raw = raw["initial_particles"]
        if not isinstance(particles_raw, list):
            raise ValueError("initial_particles must be a list")
        particles = []
        for index, value in enumerate(particles_raw):
            item = _object(value, f"initial_particles[{index}]")
            _exact_keys(item, {"kind", "x", "y", "direction"}, f"initial_particles[{index}]")
            particle = ParticleSpec(
                _integer(item["kind"], f"initial_particles[{index}].kind"),
                _integer(item["x"], f"initial_particles[{index}].x"),
                _integer(item["y"], f"initial_particles[{index}].y"),
                str(item["direction"]),
            )
            if particle.kind not in kinds:
                raise ValueError("initial particle refers to an unknown material kind")
            if particle.direction not in DIRECTIONS:
                raise ValueError("particle direction must be N, E, S, or W")
            if not (0 <= particle.x < kernel.width and 0 <= particle.y < kernel.height):
                raise ValueError("initial particle lies outside the world")
            particles.append(particle)
        if len(set(particles)) != len(particles):
            raise ValueError("a material direction channel cannot contain duplicate particles")

        execution_raw = _object(raw["execution"], "execution")
        _exact_keys(execution_raw, {"ticks"}, "execution")
        execution = ExecutionSpec(_integer(execution_raw["ticks"], "execution.ticks"))
        observer_raw = _object(raw["observer"], "observer")
        _exact_keys(observer_raw, {"hash_interval"}, "observer")
        observer = ObserverSpec(_integer(observer_raw["hash_interval"], "observer.hash_interval", minimum=1))
        return cls(world_id.strip(), kernel, tuple(sorted(materials)), tuple(sorted(particles)), execution, observer)


def load_world_spec(path: Path) -> DeterministicWorldSpec:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError("world specification is not valid JSON") from exc
    return DeterministicWorldSpec.from_mapping(_object(raw, "world"))
