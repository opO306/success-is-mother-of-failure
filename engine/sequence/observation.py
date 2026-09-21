"""Observer-only measurements for long nonliving-world experiments.

The observer receives completed transitions, never receives a choice source, and
returns no world state.  Measurements can therefore describe physics but cannot
select, repair, or rescue an outcome.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass

from engine.living.events import WorldEvent

from .face_chemistry import FaceChemistryLaw
from .face_space import ObservedFaceCompartment, observe_face_compartments
from .lineage import CompartmentLineageEvent, CompartmentLineageSnapshot, CompartmentLineageTracker
from .nonliving_world import NonlivingWorldState
from .substrate import pair_score


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _totals(state: NonlivingWorldState) -> dict[str, object]:
    strands = state.physical.sequence.strands
    return {
        "face_medium": sum(item.amount for item in state.face_medium),
        "material": sum(len(item.symbols) for item in strands) + sum(item.amount for item in state.face_solutes),
        "reservoir_adjusted_energy": state.reservoir_adjusted_energy,
        "symbols": {
            str(kind): sum(item.symbols.count(kind) for item in strands)
            + sum(item.amount for item in state.face_solutes if item.kind == kind)
            for kind in range(4)
        },
    }


def _conserved(totals: dict[str, object]) -> dict[str, object]:
    """Quantities fixed by physics; symbol kinds may transform chemically."""
    return {
        key: totals[key]
        for key in ("face_medium", "material", "reservoir_adjusted_energy")
    }



def _snapshot_strands(snapshot: CompartmentLineageSnapshot) -> tuple[object, ...]:
    return (*snapshot.boundary_strands, *snapshot.interior_strands)


@dataclass(frozen=True)
class ObserverCheckpoint:
    event_index: int
    draw_count: int
    state_hash: str
    totals: dict[str, object]

    def canonical(self) -> dict[str, object]:
        return {
            "draw_count": self.draw_count,
            "event_index": self.event_index,
            "state_hash": self.state_hash,
            "totals": self.totals,
        }


class ExperimentObserver:
    """Combine independent measurements without participating in physics."""

    def __init__(
        self,
        initial: NonlivingWorldState,
        *,
        chemistry_law: FaceChemistryLaw | None = None,
        census_interval: int = 10_000,
        ring_event_limit: int = 20_000,
        post_trigger_steps: int = 20_000,
    ) -> None:
        if census_interval <= 0 or ring_event_limit <= 0 or post_trigger_steps < 0:
            raise ValueError("observer intervals and limits are invalid")
        self._lineage = CompartmentLineageTracker(initial)
        self._chemistry_law = chemistry_law
        self._census_interval = census_interval
        self._post_trigger_steps = post_trigger_steps
        self._ring: deque[dict[str, object]] = deque(maxlen=ring_event_limit)
        self._censuses: list[dict[str, object]] = []
        self._activity: dict[str, dict[str, object]] = {}
        self._inheritance: list[dict[str, object]] = []
        self._copy_events: list[dict[str, object]] = []
        self._rare_captures: list[dict[str, object]] = []
        self._active_captures: list[dict[str, object]] = []
        self._checkpoints: list[ObserverCheckpoint] = []
        self._baseline = _totals(initial)
        self._baseline_conserved = _conserved(self._baseline)
        self._integrity_violations: list[dict[str, object]] = []
        self._face_reactions = 0
        self._record_census(0)

    @property
    def lineage(self) -> CompartmentLineageTracker:
        return self._lineage

    @property
    def digest(self) -> str:
        return str(self.canonical()["digest"])

    def _activity_for(self, lineage_digest: str, strand_id: int) -> dict[str, object]:
        item = self._activity.setdefault(lineage_digest, {
            "boundary_collapses": 0,
            "boundary_expansions": 0,
            "catalytic_contribution": 0,
            "strand_ids": set(),
            "template_uses": 0,
        })
        ids = item["strand_ids"]
        assert isinstance(ids, set)
        ids.add(strand_id)
        return item

    def _record_activity(
        self,
        event_index: int,
        before: NonlivingWorldState,
        events: tuple[WorldEvent, ...],
        before_lineages: dict[int, str],
    ) -> None:
        relevant = tuple(event for event in events if event.event_type in {
            "sequence.face_material_extend",
            "sequence.face_boundary_expand",
            "sequence.face_boundary_collapse",
            "sequence.face_reaction",
        })
        if not relevant:
            return
        after_lineage_items = self._lineage.strand_lineages
        after_lineages = {item.strand_id: item.digest for item in after_lineage_items}
        needs_reaction_context = any(event.event_type == "sequence.face_reaction" for event in relevant)
        strands = {item.strand_id: item for item in before.physical.sequence.strands} if needs_reaction_context else {}
        sites = (
            {(item.x, item.y): (item.strand_id, item.site_index) for item in before.physical.locations}
            if needs_reaction_context else {}
        )
        for event in relevant:
            payload = event.payload()
            if event.event_type == "sequence.face_material_extend":
                template_id = int(payload["template_id"])
                result_id = int(payload["result_strand_id"])
                if template_id in before_lineages:
                    self._activity_for(before_lineages[template_id], template_id)["template_uses"] += 1
                self._copy_events.append({
                    "copy_match": bool(payload["copy_match"]),
                    "descendant_lineages": sorted({
                        item.digest for item in after_lineage_items
                        if event_index in item.copy_event_ids
                    }),
                    "event_index": event_index,
                    "result_strand_id": result_id,
                    "template_lineage": before_lineages.get(template_id),
                    "template_strand_id": template_id,
                })
            elif event.event_type in {"sequence.face_boundary_expand", "sequence.face_boundary_collapse"}:
                strand_id = int(payload["strand_id"])
                lineage_digest = after_lineages.get(strand_id, before_lineages.get(strand_id))
                if lineage_digest is not None:
                    key = "boundary_expansions" if event.event_type.endswith("expand") else "boundary_collapses"
                    self._activity_for(lineage_digest, strand_id)[key] += 1
            elif event.event_type == "sequence.face_reaction":
                self._face_reactions += 1
                if self._chemistry_law is None:
                    continue
                face = tuple(int(value) for value in payload["face"])
                reaction_index = int(payload["reaction_index"])
                if not 0 <= reaction_index < len(self._chemistry_law.reactions):
                    continue
                signature = self._chemistry_law.reactions[reaction_index].signature
                x, y = face
                for point in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    site = sites.get(point)
                    if site is None:
                        continue
                    strand_id, site_index = site
                    lineage_digest = before_lineages.get(strand_id)
                    strand = strands.get(strand_id)
                    if lineage_digest is None or strand is None:
                        continue
                    contribution = sum(max(0, pair_score(strand.symbols[site_index], item)) for item in signature)
                    if contribution:
                        self._activity_for(lineage_digest, strand_id)["catalytic_contribution"] += contribution

    def _record_census(self, event_index: int) -> None:
        compartments = []
        for snapshot in self._lineage.active_compartments:
            compartments.append({
                "boundary_edges": len(snapshot.boundary_edges),
                "boundary_lineages": sorted({item.lineage_digest for item in snapshot.boundary_strands}),
                "compartment_id": snapshot.compartment_id,
                "interior_faces": len(snapshot.interior_faces),
                "interior_lineages": sorted({item.lineage_digest for item in snapshot.interior_strands}),
                "medium_amount": snapshot.medium_amount,
                "medium_energy": snapshot.medium_energy,
                "solutes_by_kind": {str(kind): amount for kind, amount in snapshot.solutes_by_kind},
            })
        self._censuses.append({"compartments": compartments, "event_index": event_index})

    def _record_inheritance(self, event: CompartmentLineageEvent) -> None:
        parent_strands = {item.strand_id: item.lineage_digest for parent in event.parents for item in _snapshot_strands(parent)}
        parent_lineages = set(parent_strands.values())
        children = []
        child_strand_sets: list[set[int]] = []
        for child in event.children:
            child_strands = {item.strand_id: item.lineage_digest for item in _snapshot_strands(child)}
            child_strand_sets.append(set(child_strands))
            child_lineages = set(child_strands.values())
            children.append({
                "compartment_id": child.compartment_id,
                "inherited_lineages": sorted(parent_lineages & child_lineages),
                "inherited_strand_ids": sorted(set(parent_strands) & set(child_strands)),
                "lineages": sorted(child_lineages),
                "medium_amount": child.medium_amount,
                "medium_energy": child.medium_energy,
                "solutes_by_kind": {str(kind): amount for kind, amount in child.solutes_by_kind},
                "strand_ids": sorted(child_strands),
            })
        shared_across_children = set.intersection(*child_strand_sets) if child_strand_sets else set()
        self._inheritance.append({
            "children": children,
            "event_index": event.event_index,
            "kind": event.kind,
            "parent_compartment_ids": [item.compartment_id for item in event.parents],
            "parent_lineages": sorted(parent_lineages),
            "parent_strand_ids": sorted(parent_strands),
            "shared_strand_ids_across_children": sorted(shared_across_children),
        })

    def observe(
        self,
        event_index: int,
        before: NonlivingWorldState,
        after: NonlivingWorldState,
        events: tuple[WorldEvent, ...] = (),
        *,
        before_observations: tuple[ObservedFaceCompartment, ...] | None = None,
        after_observations: tuple[ObservedFaceCompartment, ...] | None = None,
    ) -> None:
        """Observe one completed transition and deliberately return nothing."""
        canonical_events = [event.canonical() for event in events]
        for capture in tuple(self._active_captures):
            capture["after_events"].extend(canonical_events)
            capture["remaining_steps"] -= 1
            if capture["remaining_steps"] <= 0:
                self._active_captures.remove(capture)
        self._ring.extend(canonical_events)
        activity_event = any(event.event_type in {
            "sequence.face_material_extend",
            "sequence.face_boundary_expand",
            "sequence.face_boundary_collapse",
            "sequence.face_reaction",
        } for event in events)
        before_lineages = (
            {item.strand_id: item.digest for item in self._lineage.strand_lineages}
            if activity_event else {}
        )
        previous_event_count = len(self._lineage.events)
        self._lineage.observe(
            event_index,
            before,
            after,
            events,
            before_observations=before_observations,
            after_observations=after_observations,
        )
        self._record_activity(event_index, before, events, before_lineages)
        topology_events = self._lineage.events[previous_event_count:]
        for topology_event in topology_events:
            self._record_inheritance(topology_event)
            if topology_event.kind in {"split", "merge"}:
                if self._active_captures:
                    capture = self._active_captures[-1]
                    capture["topologies"].append(topology_event.canonical())
                    capture["remaining_steps"] = max(
                        int(capture["remaining_steps"]), self._post_trigger_steps
                    )
                else:
                    capture = {
                        "after_events": [],
                        "before_events": list(self._ring),
                        "remaining_steps": self._post_trigger_steps,
                        "topologies": [topology_event.canonical()],
                    }
                    self._rare_captures.append(capture)
                    if self._post_trigger_steps:
                        self._active_captures.append(capture)
        if topology_events or event_index % self._census_interval == 0:
            self._record_census(event_index)
        return None

    def checkpoint(self, event_index: int, state: NonlivingWorldState, draw_count: int) -> None:
        """Record externally visible integrity values without controlling execution."""
        totals = _totals(state)
        self._checkpoints.append(ObserverCheckpoint(event_index, draw_count, state.state_hash(), totals))
        observed = _conserved(totals)
        if observed != self._baseline_conserved:
            self._integrity_violations.append({
                "event_index": event_index,
                "expected": self._baseline_conserved,
                "observed": observed,
            })

    def checkpoint_canonical(self) -> dict[str, object]:
        """Small crash-visible progress report; full evidence is written once at completion."""
        activity_totals: dict[str, int] = {}
        for raw in self._activity.values():
            for key, value in raw.items():
                if key != "strand_ids":
                    activity_totals[key] = activity_totals.get(key, 0) + int(value)
        captures = [
            {
                "after_event_count": len(raw["after_events"]),
                "before_event_count": len(raw["before_events"]),
                "remaining_steps": raw["remaining_steps"],
                "topologies": raw["topologies"],
            }
            for raw in self._rare_captures
        ]
        data: dict[str, object] = {
            "activity_lineage_count": len(self._activity),
            "activity_totals": activity_totals,
            "baseline_totals": self._baseline,
            "checkpoints": [item.canonical() for item in self._checkpoints],
            "copy_event_count": len(self._copy_events),
            "copy_mismatch_count": sum(not bool(item["copy_match"]) for item in self._copy_events),
            "face_reactions": self._face_reactions,
            "format": "nonliving-observer-checkpoint-v1",
            "inheritance_events": self._inheritance,
            "integrity_violations": self._integrity_violations,
            "lineage": self._lineage.canonical(),
            "rare_event_captures": captures,
        }
        return {**data, "digest": _digest(data)}

    def canonical(self) -> dict[str, object]:
        activity = {}
        for lineage_digest, raw in sorted(self._activity.items()):
            activity[lineage_digest] = {
                **{key: value for key, value in raw.items() if key != "strand_ids"},
                "strand_ids": sorted(raw["strand_ids"]),
            }
        captures = []
        for raw in self._rare_captures:
            captures.append({
                "after_events": raw["after_events"],
                "before_events": raw["before_events"],
                "remaining_steps": raw["remaining_steps"],
                "topologies": raw["topologies"],
            })
        data: dict[str, object] = {
            "activity_by_lineage": activity,
            "baseline_totals": self._baseline,
            "censuses": self._censuses,
            "checkpoints": [item.canonical() for item in self._checkpoints],
            "copy_events": self._copy_events,
            "face_reactions": self._face_reactions,
            "format": "nonliving-observer-v1",
            "inheritance_events": self._inheritance,
            "integrity_violations": self._integrity_violations,
            "lineage": self._lineage.canonical(),
            "rare_event_captures": captures,
        }
        return {**data, "digest": _digest(data)}
