"""Parental contributions preserved separately while physics remains ancestry-blind."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .local_dynamics import LocalDynamicsState, MatterUnit, PortBond, _port
from .substrate import pair_score


@dataclass(frozen=True, order=True)
class InheritedBond:
    left_index: int
    left_port: int
    right_index: int
    right_port: int

    def __post_init__(self) -> None:
        left = (self.left_index, _port(self.left_port))
        right = (self.right_index, _port(self.right_port))
        if left >= right or self.left_index == self.right_index:
            raise ValueError("inherited bond endpoints must be distinct and canonical")


@dataclass(frozen=True)
class InheritedContribution:
    observer_tag: str
    symbols: tuple[int, ...]
    bonds: tuple[InheritedBond, ...] = ()

    def __post_init__(self) -> None:
        if not self.observer_tag:
            raise ValueError("observer_tag cannot be empty")
        symbols = tuple(self.symbols)
        if not symbols:
            raise ValueError("an inherited contribution needs at least one matter unit")
        if any(isinstance(symbol, bool) or not isinstance(symbol, int) or not 0 <= symbol < 4 for symbol in symbols):
            raise ValueError("inherited symbols must be integers from zero through three")
        occupied: set[tuple[int, int]] = set()
        bonds = tuple(sorted(self.bonds))
        for bond in bonds:
            if bond.left_index < 0 or bond.right_index >= len(symbols):
                raise ValueError("inherited bond index is outside its contribution")
            if pair_score(symbols[bond.left_index], symbols[bond.right_index]) <= 0:
                raise ValueError("inherited bonds must obey the same local affinity law")
            endpoints = ((bond.left_index, bond.left_port), (bond.right_index, bond.right_port))
            if any(endpoint in occupied for endpoint in endpoints):
                raise ValueError("each inherited port can hold at most one bond")
            occupied.update(endpoints)
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "bonds", bonds)

    def physical_canonical(self) -> dict[str, object]:
        return {
            "bonds": [
                {
                    "left_index": bond.left_index,
                    "left_port": bond.left_port,
                    "right_index": bond.right_index,
                    "right_port": bond.right_port,
                }
                for bond in self.bonds
            ],
            "symbols": list(self.symbols),
        }

    def physical_key(self) -> str:
        return json.dumps(self.physical_canonical(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, order=True)
class UnitOrigin:
    unit_id: int
    observer_tag: str
    local_index: int


@dataclass(frozen=True, order=True)
class MaterialAncestry:
    """Observer-only ancestry for one unit inside a connected material piece."""

    local_index: int
    observer_tag: str
    source_local_index: int

    def __post_init__(self) -> None:
        if min(self.local_index, self.source_local_index) < 0:
            raise ValueError("ancestry indices cannot be negative")
        if not self.observer_tag:
            raise ValueError("observer_tag cannot be empty")


@dataclass(frozen=True)
class ConnectedMaterial:
    """A physical connected component; it has no gene or trait meaning."""

    symbols: tuple[int, ...]
    bonds: tuple[InheritedBond, ...]
    ancestry: tuple[MaterialAncestry, ...]

    def __post_init__(self) -> None:
        physical = InheritedContribution("validation-only", self.symbols, self.bonds)
        ancestry = tuple(sorted(self.ancestry))
        if tuple(mark.local_index for mark in ancestry) != tuple(range(len(physical.symbols))):
            raise ValueError("connected material needs exactly one ancestry mark per unit")
        adjacency = {index: set() for index in range(len(physical.symbols))}
        for bond in physical.bonds:
            adjacency[bond.left_index].add(bond.right_index)
            adjacency[bond.right_index].add(bond.left_index)
        reached = {0}
        pending = [0]
        while pending:
            index = pending.pop()
            unseen = adjacency[index] - reached
            reached.update(unseen)
            pending.extend(unseen)
        if len(reached) != len(physical.symbols):
            raise ValueError("connected material cannot contain disconnected units")
        object.__setattr__(self, "symbols", physical.symbols)
        object.__setattr__(self, "bonds", physical.bonds)
        object.__setattr__(self, "ancestry", ancestry)

    def physical_canonical(self) -> dict[str, object]:
        return InheritedContribution("ignored", self.symbols, self.bonds).physical_canonical()

    @property
    def observer_tags(self) -> frozenset[str]:
        return frozenset(mark.observer_tag for mark in self.ancestry)


@dataclass(frozen=True)
class DevelopmentSeed:
    state: LocalDynamicsState
    origins: tuple[UnitOrigin, ...]

    def __post_init__(self) -> None:
        origins = tuple(sorted(self.origins))
        unit_ids = tuple(unit.unit_id for unit in self.state.units)
        origin_ids = tuple(origin.unit_id for origin in origins)
        if origin_ids != unit_ids:
            raise ValueError("development seed needs exactly one observer origin per matter unit")
        if len({(origin.observer_tag, origin.local_index) for origin in origins}) != len(origins):
            raise ValueError("observer origins must be unambiguous")
        object.__setattr__(self, "origins", origins)

    def unit_id(self, observer_tag: str, local_index: int = 0) -> int:
        matches = [
            origin.unit_id
            for origin in self.origins
            if origin.observer_tag == observer_tag and origin.local_index == local_index
        ]
        if len(matches) != 1:
            raise KeyError("origin does not identify exactly one matter unit")
        return matches[0]


def assemble_inherited_world(
    contributions: tuple[InheritedContribution, ...],
    thermal_energy: int,
) -> DevelopmentSeed:
    """Combine matter without averaging it; ancestry labels remain observer-only."""
    if not contributions:
        raise ValueError("at least one inherited contribution is required")
    if len({item.observer_tag for item in contributions}) != len(contributions):
        raise ValueError("observer tags must be unique")
    ordered = tuple(sorted(enumerate(contributions), key=lambda item: (item[1].physical_key(), item[0])))
    units: list[MatterUnit] = []
    bonds: list[PortBond] = []
    origins: list[UnitOrigin] = []
    next_id = 1
    for _, contribution in ordered:
        id_map: dict[int, int] = {}
        for local_index, symbol in enumerate(contribution.symbols):
            unit_id = next_id
            next_id += 1
            id_map[local_index] = unit_id
            units.append(MatterUnit(unit_id, symbol))
            origins.append(UnitOrigin(unit_id, contribution.observer_tag, local_index))
        for inherited in contribution.bonds:
            left_id = id_map[inherited.left_index]
            right_id = id_map[inherited.right_index]
            bonds.append(
                PortBond(
                    left_id,
                    inherited.left_port,
                    right_id,
                    inherited.right_port,
                    pair_score(contribution.symbols[inherited.left_index], contribution.symbols[inherited.right_index]),
                )
            )
    return DevelopmentSeed(
        LocalDynamicsState(tuple(units), thermal_energy, tuple(bonds)),
        tuple(sorted(origins)),
    )


def connected_materials(seed: DevelopmentSeed) -> tuple[ConnectedMaterial, ...]:
    """Observe physical connected components without assigning gene boundaries."""
    unit_map = {unit.unit_id: unit for unit in seed.state.units}
    origin_map = {origin.unit_id: origin for origin in seed.origins}
    adjacency = {unit_id: set() for unit_id in unit_map}
    for bond in seed.state.bonds:
        adjacency[bond.left_id].add(bond.right_id)
        adjacency[bond.right_id].add(bond.left_id)

    remaining = set(unit_map)
    components: list[ConnectedMaterial] = []
    while remaining:
        start = min(remaining)
        pending = [start]
        member_ids: set[int] = set()
        while pending:
            unit_id = pending.pop()
            if unit_id in member_ids:
                continue
            member_ids.add(unit_id)
            pending.extend(sorted(adjacency[unit_id] - member_ids, reverse=True))
        remaining.difference_update(member_ids)

        ordered_ids = tuple(sorted(member_ids))
        local_index = {unit_id: index for index, unit_id in enumerate(ordered_ids)}
        inherited_bonds = tuple(
            InheritedBond(
                local_index[bond.left_id],
                bond.left_port,
                local_index[bond.right_id],
                bond.right_port,
            )
            for bond in seed.state.bonds
            if bond.left_id in member_ids and bond.right_id in member_ids
        )
        ancestry = tuple(
            MaterialAncestry(
                local_index[unit_id],
                origin_map[unit_id].observer_tag,
                origin_map[unit_id].local_index,
            )
            for unit_id in ordered_ids
        )
        components.append(
            ConnectedMaterial(
                tuple(unit_map[unit_id].symbol for unit_id in ordered_ids),
                inherited_bonds,
                ancestry,
            )
        )
    return tuple(components)
