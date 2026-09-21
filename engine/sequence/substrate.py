"""Minimal reversible physics for the self-interpreting sequence substrate.

The four internal symbols are material kinds, not opcodes.  The reference grows
in audited slices: reversible contacts, folding, template-guided backbone changes,
and structure-dependent event context.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Protocol

from engine.living.events import RandomDraw, WorldEvent


BASE_PROPERTIES: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, +1),
    (+1, -1),
    (+1, +1),
)
DEFAULT_LABELS: tuple[str, ...] = ("A", "C", "G", "T")
BACKBONE_COST = 2
MAX_CONTEXT_MULTIPLIER = 64


class ChoiceSource(Protocol):
    def choice_index(self, count: int): ...


def _symbol(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 4:
        raise ValueError("sequence symbols must be integers from zero through three")
    return value


def parse_symbols(text: str, labels: tuple[str, ...] = DEFAULT_LABELS) -> tuple[int, ...]:
    """Convert observer display labels to internal material kinds."""
    if len(labels) != 4 or len(set(labels)) != 4 or any(len(label) != 1 for label in labels):
        raise ValueError("labels must contain four distinct single characters")
    lookup = {label: index for index, label in enumerate(labels)}
    try:
        symbols = tuple(lookup[character] for character in text)
    except KeyError as exc:
        raise ValueError(f"unknown sequence label: {exc.args[0]}") from exc
    if not symbols:
        raise ValueError("a strand needs at least one symbol")
    return symbols


def render_symbols(symbols: tuple[int, ...], labels: tuple[str, ...] = DEFAULT_LABELS) -> str:
    """Render internal kinds; labels never enter physical state or event choice."""
    if len(labels) != 4 or len(set(labels)) != 4:
        raise ValueError("labels must contain four distinct values")
    return "".join(labels[_symbol(symbol)] for symbol in symbols)


def pair_score(left: int, right: int) -> int:
    """Symmetric integer affinity from two anonymous physical axes."""
    lx, ly = BASE_PROPERTIES[_symbol(left)]
    rx, ry = BASE_PROPERTIES[_symbol(right)]
    return -(lx * rx + ly * ry)


@dataclass(frozen=True, order=True)
class Strand:
    strand_id: int
    symbols: tuple[int, ...]
    cyclic: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.strand_id, bool) or not isinstance(self.strand_id, int):
            raise TypeError("strand_id must be an integer")
        clean = tuple(_symbol(symbol) for symbol in self.symbols)
        if not clean:
            raise ValueError("a strand needs at least one symbol")
        if not isinstance(self.cyclic, bool):
            raise TypeError("cyclic must be a boolean")
        if self.cyclic and len(clean) < 4:
            raise ValueError("a cyclic strand needs at least four sites")
        object.__setattr__(self, "symbols", clean)


@dataclass(frozen=True, order=True)
class Contact:
    left_id: int
    left_start: int
    right_id: int
    right_start: int
    length: int
    bond_energy: int

    def __post_init__(self) -> None:
        if self.left_id > self.right_id:
            raise ValueError("contact strand ids must be in canonical order")
        if min(self.left_start, self.right_start) < 0 or self.length <= 0:
            raise ValueError("contact positions and length are invalid")
        if self.left_id == self.right_id and self.left_start + self.length >= self.right_start:
            raise ValueError("a fold needs two disjoint regions separated by at least one site")
        if self.bond_energy <= 0:
            raise ValueError("contact bond energy must be positive")

    @property
    def is_fold(self) -> bool:
        return self.left_id == self.right_id


@dataclass(frozen=True, order=True)
class BackboneCut:
    strand_id: int
    cut_index: int

    def __post_init__(self) -> None:
        if isinstance(self.strand_id, bool) or not isinstance(self.strand_id, int):
            raise TypeError("cut strand_id must be an integer")
        if isinstance(self.cut_index, bool) or not isinstance(self.cut_index, int) or self.cut_index <= 0:
            raise ValueError("cut_index must be a positive integer")


@dataclass(frozen=True, order=True)
class BackboneLigation:
    """Directional end-to-end bond between two distinct physical fragments."""

    left_id: int
    right_id: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.left_id, self.right_id)):
            raise TypeError("ligation strand ids must be integers")
        if self.left_id == self.right_id:
            raise ValueError("ligation needs two distinct strands")


@dataclass(frozen=True, order=True)
class BackboneCyclization:
    strand_id: int


@dataclass(frozen=True, order=True)
class BackboneCycleCut:
    strand_id: int
    cut_index: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.strand_id, self.cut_index)):
            raise TypeError("cycle cut values must be integers")
        if self.cut_index < 0:
            raise ValueError("cycle cut index cannot be negative")


@dataclass(frozen=True)
class SequenceState:
    strands: tuple[Strand, ...]
    thermal_energy: int
    contacts: tuple[Contact, ...] = ()
    time: int = 0
    next_strand_id: int | None = None

    def __post_init__(self) -> None:
        strands = tuple(sorted(self.strands))
        if len({strand.strand_id for strand in strands}) != len(strands):
            raise ValueError("strand ids must be unique")
        if isinstance(self.thermal_energy, bool) or not isinstance(self.thermal_energy, int):
            raise TypeError("thermal_energy must be an integer")
        if self.thermal_energy < 0:
            raise ValueError("thermal_energy cannot be negative")
        if isinstance(self.time, bool) or not isinstance(self.time, int) or self.time < 0:
            raise ValueError("time must be a non-negative integer")
        next_id = self.next_strand_id
        minimum_next = max((strand.strand_id for strand in strands), default=-1) + 1
        if next_id is None:
            next_id = minimum_next
        if isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < minimum_next:
            raise ValueError("next_strand_id must exceed every existing strand id")
        contacts = tuple(sorted(self.contacts))
        strand_map = {strand.strand_id: strand for strand in strands}
        occupied: set[tuple[int, int]] = set()
        for contact in contacts:
            try:
                left = strand_map[contact.left_id]
                right = strand_map[contact.right_id]
            except KeyError as exc:
                raise ValueError("contact refers to a missing strand") from exc
            if contact.left_start + contact.length > len(left.symbols):
                raise ValueError("contact exceeds the left strand")
            if contact.right_start + contact.length > len(right.symbols):
                raise ValueError("contact exceeds the right strand")
            actual = sum(
                pair_score(left.symbols[contact.left_start + offset], right.symbols[contact.right_start + offset])
                for offset in range(contact.length)
            )
            if actual != contact.bond_energy:
                raise ValueError("contact energy does not match its symbols")
            sites = [
                *((contact.left_id, contact.left_start + offset) for offset in range(contact.length)),
                *((contact.right_id, contact.right_start + offset) for offset in range(contact.length)),
            ]
            if any(site in occupied for site in sites):
                raise ValueError("a strand site cannot participate in two side contacts")
            occupied.update(sites)
        object.__setattr__(self, "strands", strands)
        object.__setattr__(self, "contacts", contacts)
        object.__setattr__(self, "next_strand_id", next_id)

    @property
    def total_energy(self) -> int:
        backbone = BACKBONE_COST * sum(
            len(strand.symbols) - 1 + int(strand.cyclic) for strand in self.strands
        )
        return self.thermal_energy + backbone - sum(contact.bond_energy for contact in self.contacts)

    def canonical(self) -> dict[str, object]:
        return {
            "contacts": [
                {
                    "bond_energy": contact.bond_energy,
                    "left_id": contact.left_id,
                    "left_start": contact.left_start,
                    "length": contact.length,
                    "right_id": contact.right_id,
                    "right_start": contact.right_start,
                }
                for contact in self.contacts
            ],
            "strands": [
                {
                    "strand_id": strand.strand_id,
                    "symbols": list(strand.symbols),
                    **({"cyclic": True} if strand.cyclic else {}),
                }
                for strand in self.strands
            ],
            "next_strand_id": self.next_strand_id,
            "thermal_energy": self.thermal_energy,
            "time": self.time,
        }

    def state_hash(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def configuration_hash(self) -> str:
        """Hash physical configuration without the observer's timeline position."""
        payload = self.canonical()
        payload.pop("time")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EventCandidate:
    kind: str
    contact: Contact | None
    weight: int
    related_contacts: tuple[Contact, ...] = ()
    cut: BackboneCut | None = None
    base_weight: int | None = None
    context_multiplier: int = 1
    ligation: BackboneLigation | None = None
    cyclization: BackboneCyclization | None = None
    cycle_cut: BackboneCycleCut | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"bind", "cleave", "cycle_open", "cyclize", "fold", "join", "ligate", "unbind", "unfold"}:
            raise ValueError("unknown sequence event kind")
        if self.weight <= 0:
            raise ValueError("event weight must be positive")
        base_weight = self.weight if self.base_weight is None else self.base_weight
        if base_weight <= 0 or self.context_multiplier <= 0:
            raise ValueError("base weight and context multiplier must be positive")
        if self.weight != base_weight * self.context_multiplier:
            raise ValueError("event weight must equal base weight times context multiplier")
        object.__setattr__(self, "base_weight", base_weight)
        if self.kind == "join" and len(self.related_contacts) != 2:
            raise ValueError("a backbone join needs its two source contacts")
        if self.kind != "join" and self.related_contacts:
            raise ValueError("only a backbone join carries related contacts")
        if self.kind == "cleave":
            if self.contact is not None or self.cut is None or any((self.ligation, self.cyclization, self.cycle_cut)):
                raise ValueError("a cleavage needs a cut and no side contact")
        elif self.kind == "ligate":
            if self.contact is not None or self.cut is not None or self.ligation is None or any((self.cyclization, self.cycle_cut)):
                raise ValueError("a ligation needs two ends and no side contact")
        elif self.kind == "cyclize":
            if self.contact is not None or self.cut is not None or self.ligation is not None or self.cyclization is None or self.cycle_cut is not None:
                raise ValueError("cyclization needs one linear strand")
        elif self.kind == "cycle_open":
            if self.contact is not None or self.cut is not None or self.ligation is not None or self.cyclization is not None or self.cycle_cut is None:
                raise ValueError("cycle opening needs one cyclic backbone cut")
        elif self.contact is None or self.cut is not None:
            raise ValueError("non-cleavage events need one side contact and no cut")


@dataclass(frozen=True)
class JoinReadiness:
    energy_available: bool
    external_contacts: int
    contact_pairs: int
    shared_template_arrangements: int
    distinct_fragment_arrangements: int
    exclusive_fragment_arrangements: int
    fully_bound_arrangements: int
    adjacent_arrangements: int
    available_join_candidates: int


@dataclass(frozen=True)
class StepResult:
    state: SequenceState
    event: WorldEvent | None
    random_draw: RandomDraw | None


def _occupied_sites(state: SequenceState) -> set[tuple[int, int]]:
    occupied: set[tuple[int, int]] = set()
    for contact in state.contacts:
        occupied.update((contact.left_id, contact.left_start + offset) for offset in range(contact.length))
        occupied.update((contact.right_id, contact.right_start + offset) for offset in range(contact.length))
    return occupied


def _binding_candidates(state: SequenceState) -> list[EventCandidate]:
    occupied = _occupied_sites(state)
    candidates: list[EventCandidate] = []
    for left, right in combinations(state.strands, 2):
        for displacement in range(-(len(right.symbols) - 1), len(left.symbols)):
            left_start = max(0, displacement)
            right_start = max(0, -displacement)
            length = min(len(left.symbols) - left_start, len(right.symbols) - right_start)
            sites = [
                *((left.strand_id, left_start + offset) for offset in range(length)),
                *((right.strand_id, right_start + offset) for offset in range(length)),
            ]
            if any(site in occupied for site in sites):
                continue
            energy = sum(
                pair_score(left.symbols[left_start + offset], right.symbols[right_start + offset])
                for offset in range(length)
            )
            if energy <= 0:
                continue
            contact = Contact(left.strand_id, left_start, right.strand_id, right_start, length, energy)
            candidates.append(EventCandidate("bind", contact, energy))
    return candidates


def _folding_candidates(state: SequenceState) -> list[EventCandidate]:
    occupied = _occupied_sites(state)
    candidates: list[EventCandidate] = []
    for strand in state.strands:
        width = len(strand.symbols)
        for left_start in range(width):
            for right_start in range(left_start + 2, width):
                max_length = min(right_start - left_start - 1, width - right_start)
                for length in range(1, max_length + 1):
                    sites = [
                        *((strand.strand_id, left_start + offset) for offset in range(length)),
                        *((strand.strand_id, right_start + offset) for offset in range(length)),
                    ]
                    if any(site in occupied for site in sites):
                        continue
                    energy = sum(
                        pair_score(
                            strand.symbols[left_start + offset],
                            strand.symbols[right_start + offset],
                        )
                        for offset in range(length)
                    )
                    if energy <= 0:
                        continue
                    contact = Contact(
                        strand.strand_id,
                        left_start,
                        strand.strand_id,
                        right_start,
                        length,
                        energy,
                    )
                    candidates.append(EventCandidate("fold", contact, energy))
    return candidates


def _unbinding_candidates(state: SequenceState) -> list[EventCandidate]:
    candidates: list[EventCandidate] = []
    for contact in state.contacts:
        if state.thermal_energy < contact.bond_energy:
            continue
        ideal = 2 * contact.length
        defect = max(0, ideal - contact.bond_energy)
        thermal_factor = max(1, state.thermal_energy - contact.bond_energy + 1)
        weight = thermal_factor * (1 << min(defect, 20))
        kind = "unfold" if contact.is_fold else "unbind"
        candidates.append(EventCandidate(kind, contact, weight))
    return candidates


def _contact_start(contact: Contact, strand_id: int) -> int:
    if contact.left_id == strand_id:
        return contact.left_start
    if contact.right_id == strand_id:
        return contact.right_start
    raise ValueError("strand is not part of contact")


def _other_strand(contact: Contact, strand_id: int) -> int:
    if contact.left_id == strand_id and contact.right_id != strand_id:
        return contact.right_id
    if contact.right_id == strand_id and contact.left_id != strand_id:
        return contact.left_id
    raise ValueError("contact does not have one distinct partner for this strand")


def _scan_backbone_joins(state: SequenceState) -> tuple[list[EventCandidate], JoinReadiness]:
    energy_available = state.thermal_energy >= BACKBONE_COST
    strand_map = {strand.strand_id: strand for strand in state.strands}
    contact_counts: dict[int, int] = {}
    external_contacts = [contact for contact in state.contacts if not contact.is_fold]
    for contact in external_contacts:
        contact_counts[contact.left_id] = contact_counts.get(contact.left_id, 0) + 1
        contact_counts[contact.right_id] = contact_counts.get(contact.right_id, 0) + 1

    geometric_candidates: list[EventCandidate] = []
    contact_pairs = 0
    shared_template_arrangements = 0
    distinct_fragment_arrangements = 0
    exclusive_fragment_arrangements = 0
    fully_bound_arrangements = 0
    adjacent_arrangements = 0
    for first, second in combinations(external_contacts, 2):
        contact_pairs += 1
        shared = {first.left_id, first.right_id} & {second.left_id, second.right_id}
        for template_id in sorted(shared):
            shared_template_arrangements += 1
            first_fragment_id = _other_strand(first, template_id)
            second_fragment_id = _other_strand(second, template_id)
            if first_fragment_id == second_fragment_id:
                continue
            distinct_fragment_arrangements += 1
            first_fragment = strand_map[first_fragment_id]
            second_fragment = strand_map[second_fragment_id]
            if first_fragment.cyclic or second_fragment.cyclic:
                continue
            if contact_counts.get(first_fragment_id) != 1 or contact_counts.get(second_fragment_id) != 1:
                continue
            exclusive_fragment_arrangements += 1
            if _contact_start(first, first_fragment_id) != 0 or first.length != len(first_fragment.symbols):
                continue
            if _contact_start(second, second_fragment_id) != 0 or second.length != len(second_fragment.symbols):
                continue
            fully_bound_arrangements += 1
            first_template_start = _contact_start(first, template_id)
            second_template_start = _contact_start(second, template_id)
            if first_template_start + first.length == second_template_start:
                left_contact, right_contact = first, second
                left_fragment, right_fragment = first_fragment, second_fragment
                template_start = first_template_start
            elif second_template_start + second.length == first_template_start:
                left_contact, right_contact = second, first
                left_fragment, right_fragment = second_fragment, first_fragment
                template_start = second_template_start
            else:
                continue
            adjacent_arrangements += 1
            new_id = int(state.next_strand_id)
            combined_length = len(left_fragment.symbols) + len(right_fragment.symbols)
            combined_energy = left_contact.bond_energy + right_contact.bond_energy
            if template_id < new_id:
                result_contact = Contact(
                    template_id,
                    template_start,
                    new_id,
                    0,
                    combined_length,
                    combined_energy,
                )
            else:
                result_contact = Contact(
                    new_id,
                    0,
                    template_id,
                    template_start,
                    combined_length,
                    combined_energy,
                )
            geometric_candidates.append(
                EventCandidate(
                    "join",
                    result_contact,
                    1,
                    (left_contact, right_contact),
                )
            )
    candidates = geometric_candidates if energy_available else []
    readiness = JoinReadiness(
        energy_available=energy_available,
        external_contacts=len(external_contacts),
        contact_pairs=contact_pairs,
        shared_template_arrangements=shared_template_arrangements,
        distinct_fragment_arrangements=distinct_fragment_arrangements,
        exclusive_fragment_arrangements=exclusive_fragment_arrangements,
        fully_bound_arrangements=fully_bound_arrangements,
        adjacent_arrangements=adjacent_arrangements,
        available_join_candidates=len(candidates),
    )
    return candidates, readiness


def _backbone_join_candidates(state: SequenceState) -> list[EventCandidate]:
    return _scan_backbone_joins(state)[0]


def join_readiness(state: SequenceState) -> JoinReadiness:
    """Describe join prerequisites for an outside observer without changing candidates."""
    return _scan_backbone_joins(state)[1]


def _backbone_cleavage_candidates(state: SequenceState) -> list[EventCandidate]:
    occupied = _occupied_sites(state)
    candidates: list[EventCandidate] = []
    for strand in state.strands:
        if strand.cyclic:
            continue
        for cut_index in range(1, len(strand.symbols)):
            if (strand.strand_id, cut_index - 1) in occupied:
                continue
            if (strand.strand_id, cut_index) in occupied:
                continue
            candidates.append(EventCandidate("cleave", None, 1, cut=BackboneCut(strand.strand_id, cut_index)))
    return candidates


def _backbone_cyclization_candidates(state: SequenceState) -> list[EventCandidate]:
    if state.thermal_energy < BACKBONE_COST:
        return []
    occupied = _occupied_sites(state)
    return [
        EventCandidate("cyclize", None, 1, cyclization=BackboneCyclization(strand.strand_id))
        for strand in state.strands
        if not strand.cyclic and len(strand.symbols) >= 4
        and (strand.strand_id, 0) not in occupied
        and (strand.strand_id, len(strand.symbols) - 1) not in occupied
    ]


def _backbone_cycle_cut_candidates(state: SequenceState) -> list[EventCandidate]:
    occupied = _occupied_sites(state)
    candidates = []
    for strand in state.strands:
        if not strand.cyclic:
            continue
        width = len(strand.symbols)
        for cut_index in range(width):
            next_index = (cut_index + 1) % width
            if (strand.strand_id, cut_index) in occupied or (strand.strand_id, next_index) in occupied:
                continue
            candidates.append(EventCandidate(
                "cycle_open",
                None,
                1,
                cycle_cut=BackboneCycleCut(strand.strand_id, cut_index),
            ))
    return candidates


def backbone_ligation_candidates(
    state: SequenceState,
    ordered_pairs: Iterable[tuple[int, int]] | None = None,
) -> tuple[EventCandidate, ...]:
    """Return the same ligation law for either well-mixed or prefiltered locality.

    ``ordered_pairs`` is geometry, not probability: a spatial world may provide
    only end pairs that are actually adjacent.  Every provided pair still passes
    the same energy, identity, and occupied-contact rules used by a well-mixed
    world.
    """
    if state.thermal_energy < BACKBONE_COST:
        return ()
    strand_ids = {strand.strand_id for strand in state.strands if not strand.cyclic}
    directly_contacting = {
        frozenset((contact.left_id, contact.right_id))
        for contact in state.contacts
        if contact.left_id != contact.right_id
    }
    if ordered_pairs is None:
        pairs = (
            ordered
            for first, second in combinations(sorted(strand_ids), 2)
            for ordered in ((first, second), (second, first))
        )
    else:
        pairs = ordered_pairs
    candidates = []
    seen = set()
    for left_id, right_id in pairs:
        pair = (left_id, right_id)
        if pair in seen:
            continue
        seen.add(pair)
        if left_id not in strand_ids or right_id not in strand_ids:
            raise ValueError("ligation locality refers to a missing strand")
        if left_id == right_id or frozenset(pair) in directly_contacting:
            continue
        candidates.append(EventCandidate("ligate", None, 1, ligation=BackboneLigation(left_id, right_id)))
    return tuple(sorted(candidates, key=candidate_sort_key))


def candidate_sort_key(candidate: EventCandidate) -> tuple[object, ...]:
    if candidate.contact is None:
        contact_key = (-1, -1, -1, -1, -1, -1)
    else:
        contact_key = (
            candidate.contact.left_id,
            candidate.contact.left_start,
            candidate.contact.right_id,
            candidate.contact.right_start,
            candidate.contact.length,
            candidate.contact.bond_energy,
        )
    cut_key = (-1, -1) if candidate.cut is None else (candidate.cut.strand_id, candidate.cut.cut_index)
    ligation_key = (
        (-1, -1)
        if candidate.ligation is None
        else (candidate.ligation.left_id, candidate.ligation.right_id)
    )
    cyclization_key = (-1,) if candidate.cyclization is None else (candidate.cyclization.strand_id,)
    cycle_cut_key = (
        (-1, -1)
        if candidate.cycle_cut is None
        else (candidate.cycle_cut.strand_id, candidate.cycle_cut.cut_index)
    )
    return (
        candidate.kind,
        contact_key,
        candidate.related_contacts,
        cut_key,
        ligation_key,
        cyclization_key,
        cycle_cut_key,
        candidate.base_weight,
        candidate.context_multiplier,
        candidate.weight,
    )


def _candidate_sites(candidate: EventCandidate) -> set[tuple[int, int]]:
    if candidate.contact is None:
        if candidate.ligation is not None:
            return {(candidate.ligation.left_id, -1), (candidate.ligation.right_id, 0)}
        if candidate.cyclization is not None:
            return {(candidate.cyclization.strand_id, -1), (candidate.cyclization.strand_id, 0)}
        if candidate.cycle_cut is not None:
            return {
                (candidate.cycle_cut.strand_id, candidate.cycle_cut.cut_index),
                (candidate.cycle_cut.strand_id, candidate.cycle_cut.cut_index + 1),
            }
        if candidate.cut is None:
            return set()
        return {
            (candidate.cut.strand_id, candidate.cut.cut_index - 1),
            (candidate.cut.strand_id, candidate.cut.cut_index),
        }
    contact = candidate.contact
    sites = {
        (contact.left_id, contact.left_start + offset) for offset in range(contact.length)
    }
    sites.update(
        (contact.right_id, contact.right_start + offset) for offset in range(contact.length)
    )
    return sites


def _with_structural_context(state: SequenceState, candidate: EventCandidate) -> EventCandidate:
    if candidate.kind not in {"bind", "fold", "join"}:
        return candidate
    sites = _candidate_sites(candidate)
    context_energy = 0
    for fold in state.contacts:
        if not fold.is_fold:
            continue
        loop_start = fold.left_start + fold.length
        loop_end = fold.right_start
        if any(
            strand_id == fold.left_id and loop_start <= site_index < loop_end
            for strand_id, site_index in sites
        ):
            context_energy += fold.bond_energy
    multiplier = min(MAX_CONTEXT_MULTIPLIER, 1 + context_energy)
    base_weight = int(candidate.base_weight)
    if multiplier == candidate.context_multiplier:
        return candidate
    return EventCandidate(
        candidate.kind,
        candidate.contact,
        base_weight * multiplier,
        candidate.related_contacts,
        candidate.cut,
        base_weight,
        multiplier,
    )


def event_candidates(state: SequenceState, *, include_ligation: bool = True) -> tuple[EventCandidate, ...]:
    """Return canonically ordered local events without observing display names."""
    raw = (
        *_binding_candidates(state),
        *_backbone_cleavage_candidates(state),
        *_backbone_cycle_cut_candidates(state),
        *_backbone_cyclization_candidates(state),
        *(backbone_ligation_candidates(state) if include_ligation else ()),
        *_folding_candidates(state),
        *_backbone_join_candidates(state),
        *_unbinding_candidates(state),
    )
    contextual = (_with_structural_context(state, candidate) for candidate in raw)
    return tuple(sorted(contextual, key=candidate_sort_key))


def _select(candidates: tuple[EventCandidate, ...], ticket: int) -> EventCandidate:
    cursor = 0
    for candidate in candidates:
        cursor += candidate.weight
        if ticket < cursor:
            return candidate
    raise ValueError("event selection ticket is outside the candidate weights")


def _apply_backbone_join(state: SequenceState, selected: EventCandidate) -> tuple[SequenceState, dict[str, object]]:
    first, second = selected.related_contacts
    shared = {first.left_id, first.right_id} & {second.left_id, second.right_id}
    template_id = next(
        strand_id
        for strand_id in sorted(shared)
        if _contact_start(first, strand_id) != _contact_start(second, strand_id)
    )
    first_fragment_id = _other_strand(first, template_id)
    second_fragment_id = _other_strand(second, template_id)
    strand_map = {strand.strand_id: strand for strand in state.strands}
    first_template_start = _contact_start(first, template_id)
    second_template_start = _contact_start(second, template_id)
    if first_template_start < second_template_start:
        left_fragment = strand_map[first_fragment_id]
        right_fragment = strand_map[second_fragment_id]
    else:
        left_fragment = strand_map[second_fragment_id]
        right_fragment = strand_map[first_fragment_id]
    new_id = int(state.next_strand_id)
    new_strand = Strand(new_id, left_fragment.symbols + right_fragment.symbols)
    removed_ids = {first_fragment_id, second_fragment_id}
    strands = tuple(strand for strand in state.strands if strand.strand_id not in removed_ids) + (new_strand,)
    contacts = tuple(contact for contact in state.contacts if contact not in selected.related_contacts)
    contacts = tuple(sorted((*contacts, selected.contact)))
    next_state = SequenceState(
        strands,
        state.thermal_energy - BACKBONE_COST,
        contacts,
        state.time + 1,
        new_id + 1,
    )
    return next_state, {
        "new_strand_id": new_id,
        "parent_strand_ids": sorted(removed_ids),
        "template_id": template_id,
    }


def _apply_backbone_ligation(
    state: SequenceState,
    selected: EventCandidate,
) -> tuple[SequenceState, dict[str, object]]:
    ligation = selected.ligation
    if ligation is None:
        raise ValueError("ligation candidate has no ends")
    strand_map = {strand.strand_id: strand for strand in state.strands}
    try:
        left = strand_map[ligation.left_id]
        right = strand_map[ligation.right_id]
    except KeyError as exc:
        raise ValueError("ligation refers to a missing strand") from exc
    new_id = int(state.next_strand_id)
    new_strand = Strand(new_id, left.symbols + right.symbols)
    removed_ids = {left.strand_id, right.strand_id}
    strands = tuple(strand for strand in state.strands if strand.strand_id not in removed_ids) + (new_strand,)

    remapped = []
    left_length = len(left.symbols)
    for contact in state.contacts:
        def endpoint(strand_id: int, start: int) -> tuple[int, int]:
            if strand_id == left.strand_id:
                return new_id, start
            if strand_id == right.strand_id:
                return new_id, left_length + start
            return strand_id, start

        first_id, first_start = endpoint(contact.left_id, contact.left_start)
        second_id, second_start = endpoint(contact.right_id, contact.right_start)
        remapped.append(_canonical_contact(
            first_id, first_start, second_id, second_start, contact.length, contact.bond_energy
        ))
    next_state = SequenceState(
        strands,
        state.thermal_energy - BACKBONE_COST,
        tuple(remapped),
        state.time + 1,
        new_id + 1,
    )
    return next_state, {
        "new_strand_id": new_id,
        "parent_strand_ids": [left.strand_id, right.strand_id],
    }


def _apply_backbone_cyclization(
    state: SequenceState,
    selected: EventCandidate,
) -> tuple[SequenceState, dict[str, object]]:
    strand_id = selected.cyclization.strand_id
    parent = next(strand for strand in state.strands if strand.strand_id == strand_id)
    strands = tuple(
        Strand(strand.strand_id, strand.symbols, True) if strand.strand_id == strand_id else strand
        for strand in state.strands
    )
    next_state = SequenceState(
        strands,
        state.thermal_energy - BACKBONE_COST,
        state.contacts,
        state.time + 1,
        state.next_strand_id,
    )
    return next_state, {"strand_id": strand_id, "site_count": len(parent.symbols)}


def _apply_backbone_cycle_cut(
    state: SequenceState,
    selected: EventCandidate,
) -> tuple[SequenceState, dict[str, object]]:
    cycle_cut = selected.cycle_cut
    parent = next(strand for strand in state.strands if strand.strand_id == cycle_cut.strand_id)
    width = len(parent.symbols)
    start = (cycle_cut.cut_index + 1) % width
    order = tuple(range(start, width)) + tuple(range(0, start))
    old_to_new = {old: new for new, old in enumerate(order)}
    linear = Strand(parent.strand_id, tuple(parent.symbols[index] for index in order))
    strands = tuple(linear if strand.strand_id == parent.strand_id else strand for strand in state.strands)
    contacts = []
    for contact in state.contacts:
        def remap(strand_id: int, contact_start: int) -> tuple[int, int]:
            if strand_id != parent.strand_id:
                return strand_id, contact_start
            mapped = tuple(old_to_new[contact_start + offset] for offset in range(contact.length))
            if mapped != tuple(range(mapped[0], mapped[0] + contact.length)):
                raise AssertionError("cycle cut crossed an occupied contact")
            return strand_id, mapped[0]

        first_id, first_start = remap(contact.left_id, contact.left_start)
        second_id, second_start = remap(contact.right_id, contact.right_start)
        contacts.append(_canonical_contact(
            first_id, first_start, second_id, second_start, contact.length, contact.bond_energy
        ))
    next_state = SequenceState(
        strands,
        state.thermal_energy + BACKBONE_COST,
        tuple(contacts),
        state.time + 1,
        state.next_strand_id,
    )
    return next_state, {
        "cut_index": cycle_cut.cut_index,
        "index_order": list(order),
        "strand_id": parent.strand_id,
    }


def _canonical_contact(
    first_id: int,
    first_start: int,
    second_id: int,
    second_start: int,
    length: int,
    energy: int,
) -> Contact:
    if (first_id, first_start) <= (second_id, second_start):
        return Contact(first_id, first_start, second_id, second_start, length, energy)
    return Contact(second_id, second_start, first_id, first_start, length, energy)


def _remap_cut_endpoint(
    strand_id: int,
    start: int,
    length: int,
    parent_id: int,
    cut_index: int,
    left_id: int,
    right_id: int,
) -> tuple[int, int]:
    if strand_id != parent_id:
        return strand_id, start
    if start + length <= cut_index:
        return left_id, start
    if start >= cut_index:
        return right_id, start - cut_index
    raise ValueError("a cleavage cannot cross an occupied contact region")


def _apply_backbone_cleavage(
    state: SequenceState,
    selected: EventCandidate,
) -> tuple[SequenceState, dict[str, object]]:
    cut = selected.cut
    if cut is None:
        raise ValueError("cleavage candidate has no cut")
    strand_map = {strand.strand_id: strand for strand in state.strands}
    parent = strand_map[cut.strand_id]
    if cut.cut_index >= len(parent.symbols):
        raise ValueError("cut_index must be inside its parent strand")
    left_id = int(state.next_strand_id)
    right_id = left_id + 1
    left = Strand(left_id, parent.symbols[: cut.cut_index])
    right = Strand(right_id, parent.symbols[cut.cut_index :])
    strands = tuple(strand for strand in state.strands if strand.strand_id != parent.strand_id) + (left, right)

    remapped_contacts: list[Contact] = []
    for contact in state.contacts:
        first_id, first_start = _remap_cut_endpoint(
            contact.left_id,
            contact.left_start,
            contact.length,
            parent.strand_id,
            cut.cut_index,
            left_id,
            right_id,
        )
        second_id, second_start = _remap_cut_endpoint(
            contact.right_id,
            contact.right_start,
            contact.length,
            parent.strand_id,
            cut.cut_index,
            left_id,
            right_id,
        )
        remapped_contacts.append(
            _canonical_contact(
                first_id,
                first_start,
                second_id,
                second_start,
                contact.length,
                contact.bond_energy,
            )
        )

    next_state = SequenceState(
        strands,
        state.thermal_energy + BACKBONE_COST,
        tuple(remapped_contacts),
        state.time + 1,
        right_id + 1,
    )
    return next_state, {
        "child_strand_ids": [left_id, right_id],
        "cut_index": cut.cut_index,
        "parent_strand_id": parent.strand_id,
    }


def apply_candidate(state: SequenceState, selected: EventCandidate) -> StepResult:
    """Apply one already selected physical event without drawing randomness."""
    if selected not in event_candidates(state):
        raise ValueError("selected event is not available in this state")
    extra_payload: dict[str, object] = {}
    if selected.kind == "cleave":
        next_state, extra_payload = _apply_backbone_cleavage(state, selected)
        thermal = next_state.thermal_energy
    elif selected.kind == "cyclize":
        next_state, extra_payload = _apply_backbone_cyclization(state, selected)
        thermal = next_state.thermal_energy
    elif selected.kind == "cycle_open":
        next_state, extra_payload = _apply_backbone_cycle_cut(state, selected)
        thermal = next_state.thermal_energy
    elif selected.kind == "join":
        next_state, extra_payload = _apply_backbone_join(state, selected)
        thermal = next_state.thermal_energy
    elif selected.kind == "ligate":
        next_state, extra_payload = _apply_backbone_ligation(state, selected)
        thermal = next_state.thermal_energy
    elif selected.kind in {"bind", "fold"}:
        contacts = tuple(sorted((*state.contacts, selected.contact)))
        thermal = state.thermal_energy + selected.contact.bond_energy
        next_state = SequenceState(
            state.strands,
            thermal,
            contacts,
            state.time + 1,
            state.next_strand_id,
        )
    else:
        contacts = tuple(contact for contact in state.contacts if contact != selected.contact)
        thermal = state.thermal_energy - selected.contact.bond_energy
        next_state = SequenceState(
            state.strands,
            thermal,
            contacts,
            state.time + 1,
            state.next_strand_id,
        )
    contact = selected.contact
    if contact is None:
        contact_payload: dict[str, object] = {}
    else:
        contact_payload = {
            "bond_energy": contact.bond_energy,
            "left_id": contact.left_id,
            "left_start": contact.left_start,
            "length": contact.length,
            "right_id": contact.right_id,
            "right_start": contact.right_start,
        }
    event_kind = {
        "cleave": "backbone_cleave",
        "join": "backbone_join",
        "ligate": "backbone_ligate",
        "cyclize": "backbone_cyclize",
        "cycle_open": "backbone_cycle_open",
    }.get(selected.kind, selected.kind)
    event = WorldEvent.create(
        next_state.time,
        f"sequence.{event_kind}",
        {
            **contact_payload,
            "base_weight": selected.base_weight,
            "context_multiplier": selected.context_multiplier,
            "state_hash": next_state.state_hash(),
            "thermal_after": thermal,
            **extra_payload,
        },
    )
    return StepResult(next_state, event, None)


def step(state: SequenceState, chance: ChoiceSource) -> StepResult:
    """Advance one event; return observer copies but never receive a recorder."""
    candidates = event_candidates(state)
    if not candidates:
        return StepResult(state, None, None)
    total_weight = sum(candidate.weight for candidate in candidates)
    sample = chance.choice_index(total_weight)
    selected = _select(candidates, int(sample.value))
    applied = apply_candidate(state, selected)
    return StepResult(applied.state, applied.event, sample.draw)
