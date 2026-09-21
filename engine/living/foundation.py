"""The narrow boundary shared by plants, animals and people.

This module deliberately does not decide what an organism is, what it should eat,
or which action is correct.  It only separates three things:

* abiotic rules, which a validated world may freeze;
* physical cues and inherited receptors, which are available to an organism;
* observer labels, which must never enter the organism's state.

The controller, development, reproduction and material exchange layers will grow
on this boundary.  Keeping it small makes semantic leakage testable first.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping


def _finite(value: float, field_name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


@dataclass(frozen=True)
class AbioticWorld:
    """Versioned non-living rules; populations and taxonomies are not part of it."""

    terrain_sha256: str
    climate_sha256: str
    matter_laws_sha256: str

    def fingerprint(self) -> str:
        payload = {
            "climate": self.climate_sha256,
            "matter_laws": self.matter_laws_sha256,
            "terrain": self.terrain_sha256,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PhysicalCue:
    """A source as physics exposes it, without species, object kind or food labels.

    ``source_key`` is opaque.  It permits continuity (the same moving thing can be
    followed) but says nothing about what the source is.  Channel positions are
    defined by the frozen world's physics and may represent light bands, volatile
    chemicals, pressure waves, contact chemistry, heat, or other measurable fields.
    """

    source_key: int
    distance: float
    bearing: float
    channels: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_key, int):
            raise TypeError("source_key must be an opaque integer")
        object.__setattr__(self, "distance", _finite(self.distance, "distance"))
        object.__setattr__(self, "bearing", _finite(self.bearing, "bearing"))
        if self.distance < 0:
            raise ValueError("distance cannot be negative")
        values = tuple(_finite(value, "channel") for value in self.channels)
        object.__setattr__(self, "channels", values)


@dataclass(frozen=True)
class ReceptorGene:
    """An inherited response curve, not a semantic detector."""

    channel: int
    gain: float = 1.0
    threshold: float = 0.0
    distance_decay: float = 1.0

    def __post_init__(self) -> None:
        if self.channel < 0:
            raise ValueError("channel must be non-negative")
        for name in ("gain", "threshold", "distance_decay"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.distance_decay < 0:
            raise ValueError("distance_decay cannot be negative")


@dataclass(frozen=True)
class CatalystGene:
    """Inherited ability to accelerate one world-defined material process."""

    process: int
    max_rate: float

    def __post_init__(self) -> None:
        if self.process < 0:
            raise ValueError("process index must be non-negative")
        object.__setattr__(self, "max_rate", _finite(self.max_rate, "max_rate"))
        if self.max_rate < 0:
            raise ValueError("max_rate cannot be negative")


@dataclass(frozen=True)
class ActionPattern:
    """One inherited physical request, without an observer-side action name."""

    exchange: tuple[float, ...]
    displacement: tuple[float, ...] = ()
    process_rates: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "exchange", tuple(_finite(v, "action exchange") for v in self.exchange))
        object.__setattr__(
            self,
            "displacement",
            tuple(_finite(v, "action displacement") for v in self.displacement),
        )
        rates = tuple(_finite(v, "action process rate") for v in self.process_rates)
        if any(value < 0 for value in rates):
            raise ValueError("action process rates cannot be negative")
        object.__setattr__(self, "process_rates", rates)


@dataclass(frozen=True)
class ControllerGene:
    """Inherited anonymous signal network shared by every possible lineage.

    Input columns receive graded internal signals followed by inherited receptor
    activities.  Nodes may excite or inhibit one another.  Output rows compete
    for physical action patterns; no row is assigned a meaning by the engine.
    """

    input_weights: tuple[tuple[float, ...], ...]
    recurrent_weights: tuple[tuple[float, ...], ...]
    action_weights: tuple[tuple[float, ...], ...]
    node_bias: tuple[float, ...]
    node_retention: tuple[float, ...]
    actions: tuple[ActionPattern, ...]
    persistence: float = 0.0
    commitment_decay: float = 1.0
    switch_margin: float = 0.0
    learning_rate: float = 0.0
    learning_decay: float = 1.0
    association_learning: float = 0.0
    memory_decay: float = 1.0
    control_cost: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        bias = tuple(_finite(v, "node bias") for v in self.node_bias)
        retention = tuple(_finite(v, "node retention") for v in self.node_retention)
        node_count = len(bias)
        if not node_count:
            raise ValueError("a controller needs at least one node")
        if len(retention) != node_count or any(not 0 <= value <= 1 for value in retention):
            raise ValueError("node retention must have one fraction per node")

        inputs = tuple(tuple(_finite(v, "input weight") for v in row) for row in self.input_weights)
        if len(inputs) != node_count or len({len(row) for row in inputs}) != 1:
            raise ValueError("input_weights must be a rectangular node matrix")
        recurrent = tuple(tuple(_finite(v, "recurrent weight") for v in row) for row in self.recurrent_weights)
        if len(recurrent) != node_count or any(len(row) != node_count for row in recurrent):
            raise ValueError("recurrent_weights must be a square node matrix")
        action_weights = tuple(tuple(_finite(v, "action weight") for v in row) for row in self.action_weights)
        if len(action_weights) != len(self.actions) or any(len(row) != node_count for row in action_weights):
            raise ValueError("action_weights must have one node-width row per action")
        if not self.actions:
            raise ValueError("a controller needs at least one physical action")
        for name in ("persistence", "switch_margin", "learning_rate", "association_learning"):
            value = _finite(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        decay = _finite(self.learning_decay, "learning_decay")
        commitment_decay = _finite(self.commitment_decay, "commitment_decay")
        memory_decay = _finite(self.memory_decay, "memory_decay")
        if not all(0 <= value <= 1 for value in (decay, commitment_decay, memory_decay)):
            raise ValueError("learning, commitment, and memory decay must be fractions")
        costs = tuple(_finite(v, "control cost") for v in self.control_cost)
        if any(value < 0 for value in costs):
            raise ValueError("control cost cannot be negative")
        object.__setattr__(self, "input_weights", inputs)
        object.__setattr__(self, "recurrent_weights", recurrent)
        object.__setattr__(self, "action_weights", action_weights)
        object.__setattr__(self, "node_bias", bias)
        object.__setattr__(self, "node_retention", retention)
        object.__setattr__(self, "learning_decay", decay)
        object.__setattr__(self, "commitment_decay", commitment_decay)
        object.__setattr__(self, "memory_decay", memory_decay)
        object.__setattr__(self, "control_cost", costs)


@dataclass(frozen=True)
class Genome:
    """Minimal inheritable start; structural development will extend this grammar."""

    receptors: tuple[ReceptorGene, ...] = ()
    neutral_markers: tuple[int, ...] = ()
    catalysts: tuple[CatalystGene, ...] = ()
    controller: ControllerGene | None = None


@dataclass
class ControllerState:
    """Acquired controller state; unlike ControllerGene this is not inherited."""

    activations: list[float]
    action_weights: list[list[float]]
    chosen_action: int | None = None
    commitment: float = 0.0
    last_inputs: tuple[float, ...] = ()

    def snapshot(self) -> tuple[object, ...]:
        return (
            tuple(self.activations),
            tuple(tuple(row) for row in self.action_weights),
            self.chosen_action,
            self.commitment,
            self.last_inputs,
        )


@dataclass(frozen=True)
class BoundaryPhenotype:
    """Developed physical limits of a body, expressed without taxonomic meaning.

    Every tuple uses the same anonymous material-channel order as the local world.
    A later developmental genome will produce these values; keeping the phenotype
    explicit now lets the physical accounting be tested independently.
    """

    capacities: tuple[float, ...]
    inward_limits: tuple[float, ...]
    outward_limits: tuple[float, ...]
    passive_loss: tuple[float, ...]
    targets: tuple[float, ...]
    maintenance: tuple[float, ...]
    motion_cost: tuple[float, ...]
    max_displacement: float = 0.0
    damage_from_total_shortfall: float = 0.05
    failure_damage: float = 1.0
    capacity_gain: tuple[tuple[float, ...], ...] = ()

    def __post_init__(self) -> None:
        names = (
            "capacities",
            "inward_limits",
            "outward_limits",
            "passive_loss",
            "targets",
            "maintenance",
            "motion_cost",
        )
        width = len(self.capacities)
        if not width:
            raise ValueError("a body boundary needs at least one material channel")
        for name in names:
            values = tuple(_finite(value, name) for value in getattr(self, name))
            if len(values) != width:
                raise ValueError("all body material vectors must have the same width")
            if any(value < 0 for value in values):
                raise ValueError(f"{name} cannot contain negative values")
            object.__setattr__(self, name, values)
        if any(target > cap for target, cap in zip(self.targets, self.capacities)):
            raise ValueError("homeostatic targets cannot exceed body capacities")
        if any(loss > 1 for loss in self.passive_loss):
            raise ValueError("passive_loss is a fraction and cannot exceed one")
        for name in ("max_displacement", "damage_from_total_shortfall", "failure_damage"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.failure_damage <= 0:
            raise ValueError("failure_damage must be positive")
        matrix = self.capacity_gain or tuple((0.0,) * width for _ in range(width))
        if len(matrix) != width:
            raise ValueError("capacity_gain must have one row per reserve channel")
        clean_rows = []
        for row in matrix:
            clean = tuple(_finite(value, "capacity_gain") for value in row)
            if len(clean) != width:
                raise ValueError("capacity_gain rows must match the material channel width")
            if any(value < 0 for value in clean):
                raise ValueError("capacity_gain cannot contain negative values")
            clean_rows.append(clean)
        object.__setattr__(self, "capacity_gain", tuple(clean_rows))

    def capacities_for(self, structure: tuple[float, ...] | list[float]) -> tuple[float, ...]:
        if len(structure) != len(self.capacities):
            raise ValueError("structure and boundary must use the same material channels")
        return tuple(
            base + sum(gain * bound for gain, bound in zip(row, structure))
            for base, row in zip(self.capacities, self.capacity_gain)
        )


@dataclass(frozen=True)
class Founder:
    """Internal initial conditions.  It intentionally has no species/name field."""

    organism_id: int
    genome: Genome
    reserves: tuple[float, ...]
    boundary: BoundaryPhenotype
    structure: tuple[float, ...]
    position: tuple[float, ...] = ()
    damage: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.organism_id, int):
            raise TypeError("organism_id must be an integer")
        reserves = tuple(_finite(value, "reserve") for value in self.reserves)
        if any(value < 0 for value in reserves):
            raise ValueError("reserves cannot be negative")
        if len(reserves) != len(self.boundary.capacities):
            raise ValueError("reserves and body boundary must use the same material channels")
        structure = tuple(_finite(value, "structure") for value in self.structure)
        if len(structure) != len(reserves):
            raise ValueError("structure and reserves must use the same material channels")
        if any(value < 0 for value in structure):
            raise ValueError("structure cannot contain negative values")
        capacities = self.boundary.capacities_for(structure)
        if any(value > cap for value, cap in zip(reserves, capacities)):
            raise ValueError("founder reserves cannot exceed body capacities")
        object.__setattr__(self, "reserves", reserves)
        object.__setattr__(self, "structure", structure)
        position = tuple(_finite(value, "position") for value in self.position)
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "damage", _finite(self.damage, "damage"))
        if self.damage < 0:
            raise ValueError("damage cannot be negative")


@dataclass
class LivingState:
    organism_id: int
    genome: Genome
    boundary: BoundaryPhenotype
    reserves: list[float]
    structure: list[float]
    position: list[float] = field(default_factory=list)
    damage: float = 0.0
    age_ticks: int = 0
    memory: dict[int, tuple[float, ...]] = field(default_factory=dict)
    controller: ControllerState | None = None

    def physical_snapshot(self) -> tuple[object, ...]:
        """State usable for deterministic comparisons; observer metadata is absent."""
        return (
            self.organism_id,
            self.genome,
            self.boundary,
            tuple(self.reserves),
            tuple(self.structure),
            tuple(self.position),
            self.damage,
            self.age_ticks,
            tuple(sorted(self.memory.items())),
            None if self.controller is None else self.controller.snapshot(),
        )


@dataclass(frozen=True)
class Sensation:
    source_key: int
    distance: float
    bearing: float
    receptor_activity: tuple[float, ...]


@dataclass(frozen=True)
class ObserverRecord:
    """Human-facing taxonomy kept outside LivingState and sensory calculations."""

    organism_id: int
    lineage: str
    description: str = ""


@dataclass
class WorldGenesis:
    abiotic: AbioticWorld
    tick: int
    living: dict[int, LivingState]
    observer_records: dict[int, ObserverRecord]

    def physical_snapshot(self) -> tuple[object, ...]:
        return (
            self.abiotic.fingerprint(),
            self.tick,
            tuple((key, state.physical_snapshot()) for key, state in sorted(self.living.items())),
        )


def perceive(genome: Genome, cues: Iterable[PhysicalCue]) -> tuple[Sensation, ...]:
    """Turn physical fields into receptor activity without adding meaning.

    Missing physical channels are silent.  Negative response is allowed because
    inhibition can be as useful as excitation; saturation merely keeps numerical
    values finite and bounded for later neural controllers.
    """
    out: list[Sensation] = []
    for cue in cues:
        activities = []
        for receptor in genome.receptors:
            raw = cue.channels[receptor.channel] if receptor.channel < len(cue.channels) else 0.0
            attenuated = raw / ((1.0 + cue.distance) ** receptor.distance_decay)
            response = receptor.gain * (attenuated - receptor.threshold)
            activities.append(math.tanh(response))
        out.append(Sensation(cue.source_key, cue.distance, cue.bearing, tuple(activities)))
    return tuple(sorted(out, key=lambda sensation: (sensation.distance, sensation.source_key)))


def found_world(
    abiotic: AbioticWorld,
    founders: Iterable[Founder],
    observer_records: Iterable[ObserverRecord] = (),
) -> WorldGenesis:
    """Place every founding lineage at tick zero without using observer taxonomy."""
    living: dict[int, LivingState] = {}
    for founder in founders:
        if founder.organism_id in living:
            raise ValueError(f"duplicate organism_id: {founder.organism_id}")
        living[founder.organism_id] = LivingState(
            organism_id=founder.organism_id,
            genome=founder.genome,
            boundary=founder.boundary,
            reserves=list(founder.reserves),
            structure=list(founder.structure),
            position=list(founder.position),
            damage=founder.damage,
            controller=(
                None
                if founder.genome.controller is None
                else ControllerState(
                    [0.0] * len(founder.genome.controller.node_bias),
                    [list(row) for row in founder.genome.controller.action_weights],
                )
            ),
        )

    records: dict[int, ObserverRecord] = {}
    for record in observer_records:
        if record.organism_id not in living:
            raise ValueError(f"observer record has no living organism: {record.organism_id}")
        if record.organism_id in records:
            raise ValueError(f"duplicate observer record: {record.organism_id}")
        records[record.organism_id] = record
    return WorldGenesis(abiotic=abiotic, tick=0, living=living, observer_records=records)


def observer_index(records: Mapping[int, ObserverRecord]) -> dict[str, tuple[int, ...]]:
    """Build a reporting index without handing it back to any organism."""
    grouped: dict[str, list[int]] = {}
    for organism_id, record in records.items():
        grouped.setdefault(record.lineage, []).append(organism_id)
    return {lineage: tuple(sorted(ids)) for lineage, ids in sorted(grouped.items())}
