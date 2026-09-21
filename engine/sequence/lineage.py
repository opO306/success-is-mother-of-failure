"""Observer-only compartment and strand lineage tracking.

The tracker receives completed world transitions.  It never receives a random
source and never returns a world state, so its records cannot affect physics.
Only topology changes are retained; ordinary frames update the active snapshot
in memory without growing the report.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from engine.living.events import WorldEvent

from .face_space import Edge, Face, ObservedFaceCompartment, observe_face_compartments
from .nonliving_world import NonlivingWorldState
from .spatial_sequence import SpatialSequenceState
from .substrate import Strand


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class StrandLineage:
    strand_id: int
    digest: str
    copy_event_ids: tuple[int, ...] = ()
    copy_mismatch_event_ids: tuple[int, ...] = ()
    transformations: int = 0

    @property
    def copy_steps(self) -> int:
        return len(self.copy_event_ids)

    @property
    def copy_mismatches(self) -> int:
        return len(self.copy_mismatch_event_ids)

    def canonical(self) -> dict[str, object]:
        return {
            "copy_event_ids": list(self.copy_event_ids),
            "copy_mismatch_event_ids": list(self.copy_mismatch_event_ids),
            "copy_mismatches": self.copy_mismatches,
            "copy_steps": self.copy_steps,
            "digest": self.digest,
            "strand_id": self.strand_id,
            "transformations": self.transformations,
        }


@dataclass(frozen=True, order=True)
class ObservedLineageStrand:
    strand_id: int
    symbols: tuple[int, ...]
    cyclic: bool
    lineage_digest: str
    copy_steps: int
    copy_mismatches: int

    def canonical(self) -> dict[str, object]:
        return {
            "copy_mismatches": self.copy_mismatches,
            "copy_steps": self.copy_steps,
            "cyclic": self.cyclic,
            "lineage_digest": self.lineage_digest,
            "strand_id": self.strand_id,
            "symbols": list(self.symbols),
        }


@dataclass(frozen=True)
class CompartmentLineageSnapshot:
    compartment_id: int
    boundary_edges: tuple[Edge, ...]
    interior_faces: tuple[Face, ...]
    boundary_strands: tuple[ObservedLineageStrand, ...]
    interior_strands: tuple[ObservedLineageStrand, ...]
    solutes_by_kind: tuple[tuple[int, int], ...]
    medium_amount: int
    medium_energy: int

    def canonical(self) -> dict[str, object]:
        def edge(edge: Edge) -> list[list[int]]:
            return [list(edge[0]), list(edge[1])]

        return {
            "boundary_edges": [edge(item) for item in self.boundary_edges],
            "boundary_strands": [item.canonical() for item in self.boundary_strands],
            "compartment_id": self.compartment_id,
            "interior_faces": [list(item) for item in self.interior_faces],
            "interior_strands": [item.canonical() for item in self.interior_strands],
            "medium_amount": self.medium_amount,
            "medium_energy": self.medium_energy,
            "solutes_by_kind": {str(kind): amount for kind, amount in self.solutes_by_kind},
        }


@dataclass(frozen=True)
class CompartmentLineageEvent:
    event_index: int
    kind: str
    parents: tuple[CompartmentLineageSnapshot, ...]
    children: tuple[CompartmentLineageSnapshot, ...]

    def canonical(self) -> dict[str, object]:
        return {
            "children": [item.canonical() for item in self.children],
            "event_index": self.event_index,
            "kind": self.kind,
            "parents": [item.canonical() for item in self.parents],
        }


def _root_lineage(strand: Strand) -> StrandLineage:
    return StrandLineage(
        strand.strand_id,
        _digest({"kind": "observed_root", "strand_id": strand.strand_id, "symbols": strand.symbols}),
    )


def _transition_digest(kind: str, parents: Iterable[StrandLineage], payload: dict[str, object]) -> str:
    ignored = {"base_weight", "context_multiplier", "spatial_state_hash", "state_hash", "thermal_after", "weight"}
    return _digest({
        "kind": kind,
        "parents": [item.digest for item in parents],
        "payload": {key: value for key, value in sorted(payload.items()) if key not in ignored},
    })


def _edge_members(state: SpatialSequenceState) -> dict[Edge, set[int]]:
    points = {item.site: item.point for item in state.locations}
    members: dict[Edge, set[int]] = {}

    def add(left: tuple[int, int], right: tuple[int, int]) -> None:
        first, second = points[left], points[right]
        edge = (first, second) if first < second else (second, first)
        members.setdefault(edge, set()).update((left[0], right[0]))

    for strand in state.sequence.strands:
        for index in range(len(strand.symbols) - 1):
            add((strand.strand_id, index), (strand.strand_id, index + 1))
        if strand.cyclic:
            add((strand.strand_id, len(strand.symbols) - 1), (strand.strand_id, 0))
    for contact in state.sequence.contacts:
        for offset in range(contact.length):
            add(
                (contact.left_id, contact.left_start + offset),
                (contact.right_id, contact.right_start + offset),
            )
    return members


def _face_vertices(faces: Iterable[Face]) -> set[tuple[int, int]]:
    vertices = set()
    for x, y in faces:
        vertices.update(((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)))
    return vertices


class CompartmentLineageTracker:
    """Track observed continuity without becoming part of the simulated world."""

    def __init__(self, initial: NonlivingWorldState) -> None:
        self._next_compartment_id = 1
        self._strands = {
            strand.strand_id: _root_lineage(strand)
            for strand in initial.physical.sequence.strands
        }
        self._events: list[CompartmentLineageEvent] = []
        self._active: dict[int, CompartmentLineageSnapshot] = {}
        for observed in observe_face_compartments(initial.physical, initial.face_medium):
            compartment_id = self._allocate_compartment_id()
            self._active[compartment_id] = self._snapshot(compartment_id, initial, observed)
        self._initial = tuple(self._active[item] for item in sorted(self._active))

    @property
    def events(self) -> tuple[CompartmentLineageEvent, ...]:
        return tuple(self._events)

    @property
    def active_compartments(self) -> tuple[CompartmentLineageSnapshot, ...]:
        return tuple(self._active[item] for item in sorted(self._active))

    @property
    def strand_lineages(self) -> tuple[StrandLineage, ...]:
        return tuple(self._strands[item] for item in sorted(self._strands))

    @property
    def digest(self) -> str:
        return str(self.canonical()["digest"])

    def _allocate_compartment_id(self) -> int:
        value = self._next_compartment_id
        self._next_compartment_id += 1
        return value

    def _observed_strand(self, strand: Strand) -> ObservedLineageStrand:
        lineage = self._strands[strand.strand_id]
        return ObservedLineageStrand(
            strand.strand_id,
            strand.symbols,
            strand.cyclic,
            lineage.digest,
            lineage.copy_steps,
            lineage.copy_mismatches,
        )

    def _snapshot(
        self,
        compartment_id: int,
        state: NonlivingWorldState,
        observed: ObservedFaceCompartment,
    ) -> CompartmentLineageSnapshot:
        edge_members = _edge_members(state.physical)
        boundary_ids = {
            strand_id
            for edge in observed.boundary_edges
            for strand_id in edge_members.get(edge, ())
        }
        boundary_vertices = {point for edge in observed.boundary_edges for point in edge}
        interior_vertices = _face_vertices(observed.interior_faces) - boundary_vertices
        interior_ids = {
            item.strand_id
            for item in state.physical.locations
            if item.point in interior_vertices and item.strand_id not in boundary_ids
        }
        strands = {strand.strand_id: strand for strand in state.physical.sequence.strands}
        solutes = tuple(
            (kind, sum(
                cell.amount for cell in state.face_solutes
                if cell.kind == kind and cell.face in observed.interior_faces
            ))
            for kind in range(4)
        )
        return CompartmentLineageSnapshot(
            compartment_id,
            observed.boundary_edges,
            observed.interior_faces,
            tuple(self._observed_strand(strands[item]) for item in sorted(boundary_ids)),
            tuple(self._observed_strand(strands[item]) for item in sorted(interior_ids)),
            solutes,
            observed.interior_medium_amount,
            observed.interior_medium_energy,
        )

    def _update_strands(
        self,
        event_index: int,
        before: NonlivingWorldState,
        after: NonlivingWorldState,
        events: tuple[WorldEvent, ...],
    ) -> None:
        for strand in before.physical.sequence.strands:
            self._strands.setdefault(strand.strand_id, _root_lineage(strand))
        for event in events:
            payload = event.payload()
            kind = event.event_type
            if kind in {"sequence.backbone_join", "sequence.backbone_ligate"}:
                parent_ids = tuple(int(item) for item in payload["parent_strand_ids"])
                parents = tuple(self._strands.pop(item) for item in parent_ids)
                new_id = int(payload["new_strand_id"])
                copy_events = tuple(sorted({
                    value for parent in parents for value in parent.copy_event_ids
                }))
                mismatch_events = tuple(sorted({
                    value for parent in parents for value in parent.copy_mismatch_event_ids
                }))
                self._strands[new_id] = StrandLineage(
                    new_id,
                    _transition_digest(kind, parents, payload),
                    copy_events,
                    mismatch_events,
                    1 + sum(item.transformations for item in parents),
                )
            elif kind == "sequence.backbone_cleave":
                parent_id = int(payload["parent_strand_id"])
                parent = self._strands.pop(parent_id)
                for side, child_id in enumerate(payload["child_strand_ids"]):
                    child_id = int(child_id)
                    child_payload = {**payload, "child_side": side}
                    self._strands[child_id] = StrandLineage(
                        child_id,
                        _transition_digest(kind, (parent,), child_payload),
                        parent.copy_event_ids,
                        parent.copy_mismatch_event_ids,
                        parent.transformations + 1,
                    )
            elif kind == "sequence.face_material_condense":
                new_id = int(payload["result_strand_id"])
                self._strands[new_id] = StrandLineage(
                    new_id, _transition_digest(kind, (), payload), transformations=1
                )
            elif kind == "sequence.face_material_dissolve":
                self._strands.pop(int(payload["strand_id"]))
            elif kind == "sequence.face_material_extend":
                strand_id = int(payload["result_strand_id"])
                parent = self._strands[strand_id]
                template = self._strands[int(payload["template_id"])]
                mismatch = not bool(payload["copy_match"])
                copy_events = tuple(sorted({*parent.copy_event_ids, event_index}))
                mismatch_events = tuple(sorted({
                    *parent.copy_mismatch_event_ids,
                    *(() if not mismatch else (event_index,)),
                }))
                self._strands[strand_id] = StrandLineage(
                    strand_id,
                    _transition_digest(kind, (parent, template), payload),
                    copy_events,
                    mismatch_events,
                    parent.transformations + 1,
                )
            elif kind in {
                "sequence.backbone_cycle_open",
                "sequence.backbone_cyclize",
                "sequence.face_boundary_collapse",
                "sequence.face_boundary_expand",
                "sequence.face_material_erode",
            }:
                strand_id = int(payload["strand_id"])
                parent = self._strands[strand_id]
                self._strands[strand_id] = StrandLineage(
                    strand_id,
                    _transition_digest(kind, (parent,), payload),
                    parent.copy_event_ids,
                    parent.copy_mismatch_event_ids,
                    parent.transformations + 1,
                )
        live_ids = {strand.strand_id for strand in after.physical.sequence.strands}
        if set(self._strands) != live_ids:
            raise AssertionError("lineage events did not account for every live strand")

    def observe(
        self,
        event_index: int,
        before: NonlivingWorldState,
        after: NonlivingWorldState,
        events: tuple[WorldEvent, ...] = (),
        before_observations: tuple[ObservedFaceCompartment, ...] | None = None,
        after_observations: tuple[ObservedFaceCompartment, ...] | None = None,
    ) -> None:
        if isinstance(event_index, bool) or not isinstance(event_index, int) or event_index < 0:
            raise ValueError("event_index must be a non-negative integer")
        observed_before_items = before_observations
        if observed_before_items is None:
            observed_before_items = observe_face_compartments(before.physical, before.face_medium)
        expected_before = {snapshot.interior_faces for snapshot in self._active.values()}
        observed_before = {item.interior_faces for item in observed_before_items}
        if expected_before != observed_before:
            raise ValueError("tracker observations must be consecutive")
        self._update_strands(event_index, before, after, events)
        observations = after_observations
        if observations is None:
            observations = observe_face_compartments(after.physical, after.face_medium)
        old_neighbors = {
            compartment_id: tuple(
                index for index, observed in enumerate(observations)
                if set(snapshot.interior_faces) & set(observed.interior_faces)
            )
            for compartment_id, snapshot in self._active.items()
        }
        new_neighbors = {
            index: tuple(
                compartment_id for compartment_id, snapshot in self._active.items()
                if set(snapshot.interior_faces) & set(observed.interior_faces)
            )
            for index, observed in enumerate(observations)
        }
        next_active: dict[int, CompartmentLineageSnapshot] = {}
        visited_old: set[int] = set()
        visited_new: set[int] = set()

        for start in sorted(item for item, neighbors in old_neighbors.items() if neighbors):
            if start in visited_old:
                continue
            component_old: set[int] = set()
            component_new: set[int] = set()
            pending_old = [start]
            while pending_old:
                old_id = pending_old.pop()
                if old_id in component_old:
                    continue
                component_old.add(old_id)
                for new_index in old_neighbors[old_id]:
                    if new_index in component_new:
                        continue
                    component_new.add(new_index)
                    pending_old.extend(new_neighbors[new_index])
            visited_old.update(component_old)
            visited_new.update(component_new)
            if len(component_old) == len(component_new) == 1:
                compartment_id = next(iter(component_old))
                observed = observations[next(iter(component_new))]
                next_active[compartment_id] = self._snapshot(compartment_id, after, observed)
                continue
            parents = tuple(self._active[item] for item in sorted(component_old))
            children = []
            for new_index in sorted(component_new, key=lambda item: observations[item].interior_faces):
                compartment_id = self._allocate_compartment_id()
                snapshot = self._snapshot(compartment_id, after, observations[new_index])
                next_active[compartment_id] = snapshot
                children.append(snapshot)
            kind = "split" if len(parents) == 1 else "merge" if len(children) == 1 else "reorganization"
            self._events.append(CompartmentLineageEvent(event_index, kind, parents, tuple(children)))

        for compartment_id in sorted(set(self._active) - visited_old):
            self._events.append(CompartmentLineageEvent(
                event_index, "destroyed", (self._active[compartment_id],), ()
            ))
        for new_index in sorted(set(range(len(observations))) - visited_new, key=lambda item: observations[item].interior_faces):
            compartment_id = self._allocate_compartment_id()
            snapshot = self._snapshot(compartment_id, after, observations[new_index])
            next_active[compartment_id] = snapshot
            self._events.append(CompartmentLineageEvent(event_index, "created", (), (snapshot,)))
        self._active = next_active

    def canonical(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "active_compartments": [item.canonical() for item in self.active_compartments],
            "events": [item.canonical() for item in self.events],
            "format": "compartment-lineage-v1",
            "initial_compartments": [item.canonical() for item in self._initial],
            "strand_lineages": [item.canonical() for item in self.strand_lineages],
        }
        return {**payload, "digest": _digest(payload)}
