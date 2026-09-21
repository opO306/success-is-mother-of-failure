"""Independent sparse Cognitive Map adapter for current-state queries.

This candidate does not call A transition functions or forecast models. It
encodes the supplied current state into a sparse map and answers topology/state
queries. The external evaluator accepts any valid minimum path, not one mandated
internal route.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping

from .b_language import (
    AttachmentDescriptor,
    BoundaryEvaluation,
    CapabilityManifest,
    Claim,
    ClaimSet,
    EvidenceBridge,
    ObservationContract,
)
from .environment_kernel import EnvironmentState, initial_environment_state
from .environment_spec import EnvironmentWorldSpec


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class CognitiveMapCell:
    x: int
    y: int
    heat: int
    elevation: int
    water: int
    vapor: int
    mineral: int
    solutes: tuple[int, ...]
    particle_kinds: tuple[int, ...]
    bond_rule_ids: tuple[str, ...]

    def canonical(self) -> dict[str, object]:
        return {"bond_rule_ids": list(self.bond_rule_ids), "elevation": self.elevation,
                "heat": self.heat, "mineral": self.mineral, "particle_kinds": list(self.particle_kinds),
                "solutes": list(self.solutes), "vapor": self.vapor, "water": self.water,
                "x": self.x, "y": self.y}


@dataclass(frozen=True)
class CognitiveMap:
    width: int
    height: int
    cells: tuple[CognitiveMapCell, ...]
    blocked_edges: tuple[tuple[tuple[int, int], tuple[int, int]], ...]
    source_state_digest: str

    @property
    def digest(self) -> str: return _digest(self.canonical())

    @property
    def full_cell_count(self) -> int: return self.width * self.height

    @property
    def stored_cell_count(self) -> int: return len(self.cells)

    def canonical(self) -> dict[str, object]:
        return {"blocked_edges": [[list(a), list(b)] for a, b in self.blocked_edges],
                "cells": [item.canonical() for item in self.cells], "format": "sparse-cognitive-map-v1",
                "height": self.height, "source_state_digest": self.source_state_digest, "width": self.width}

    def cell(self, point: tuple[int, int], solute_kinds: int) -> CognitiveMapCell:
        for item in self.cells:
            if (item.x, item.y) == point: return item
        return CognitiveMapCell(point[0], point[1], 0, 0, 0, 0, 0,
                                (0,) * solute_kinds, (), ())

    def neighbors(self, point: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        x, y = point
        candidates = ((x, (y - 1) % self.height), ((x + 1) % self.width, y),
                      (x, (y + 1) % self.height), ((x - 1) % self.width, y))
        blocked = {frozenset(edge) for edge in self.blocked_edges}
        return tuple(next_point for next_point in candidates
                     if frozenset((point, next_point)) not in blocked)

    def shortest_path(self, start: tuple[int, int], goal: tuple[int, int]) -> tuple[tuple[int, int], ...] | None:
        if start == goal: return (start,)
        queue = deque([start]); previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            point = queue.popleft()
            for next_point in self.neighbors(point):
                if next_point in previous: continue
                previous[next_point] = point
                if next_point == goal:
                    path = [goal]; cursor = point
                    while cursor is not None:
                        path.append(cursor); cursor = previous[cursor]
                    return tuple(reversed(path))
                queue.append(next_point)
        return None


def _cell_payload(item: CognitiveMapCell) -> dict[str, object]:
    return {"bond_rule_ids": list(item.bond_rule_ids), "elevation": item.elevation,
            "heat": item.heat, "mineral": item.mineral, "particle_kinds": list(item.particle_kinds),
            "solutes": list(item.solutes), "vapor": item.vapor, "water": item.water,
            "x": item.x, "y": item.y}


def build_cognitive_map(spec: EnvironmentWorldSpec, state: EnvironmentState) -> CognitiveMap:
    if state.format != spec.format: raise ValueError("state and specification formats differ")
    heat = {(item.x, item.y): item.energy for item in state.causal.heat}
    resources = {(item.x, item.y): item for item in state.cells}
    particles: dict[tuple[int, int], list[int]] = {}
    for item in state.causal.particles: particles.setdefault((item.x, item.y), []).append(item.kind)
    bonds: dict[tuple[int, int], list[str]] = {}
    for item in state.causal.bonds: bonds.setdefault((item.x, item.y), []).append(item.rule_id)
    points = sorted(set(heat) | set(resources) | set(particles) | set(bonds))
    cells = []
    for x, y in points:
        resource = resources.get((x, y))
        cells.append(CognitiveMapCell(
            x, y, heat.get((x, y), 0), resource.elevation if resource else 0,
            resource.water if resource else 0, resource.vapor if resource else 0,
            resource.mineral if resource else 0,
            resource.solutes if resource else (0,) * spec.solute_kinds,
            tuple(sorted(particles.get((x, y), []))), tuple(sorted(bonds.get((x, y), []))),
        ))
    edges = tuple((edge.first, edge.second) for edge in spec.blocked_edges)
    return CognitiveMap(spec.causal_world.kernel.width, spec.causal_world.kernel.height,
                        tuple(cells), edges, state.digest)


def make_cognitive_map_challenge(
    spec: EnvironmentWorldSpec, queries: tuple[Mapping[str, Any], ...],
    state: EnvironmentState | None = None,
) -> ObservationContract:
    state = initial_environment_state(spec) if state is None else state
    if not queries: raise ValueError("cognitive map challenge needs at least one query")
    ids = [query.get("query_id") for query in queries]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("query ids must be unique non-empty text")
    return ObservationContract(
        f"{spec.causal_world.world_id}:cognitive-map:{_digest(list(queries))[:16]}",
        "answer_state_queries", (("spec", spec.digest), ("initial_state", state.digest)),
        ("sealed_topology", "initial_state"), ("future_checkpoints",), 0,
        spec.causal_world.kernel.width * spec.causal_world.kernel.height,
        spec.causal_world.kernel.width * spec.causal_world.kernel.height * 16,
        ("local answers match the supplied state", "paths are valid and minimum length",
         "reachability answers match topology"), {"queries": [dict(query) for query in queries]},
    )


def _raw_state_payload(spec: EnvironmentWorldSpec, state: EnvironmentState,
                       point: tuple[int, int]) -> dict[str, object]:
    heat = next((item.energy for item in state.causal.heat if (item.x, item.y) == point), 0)
    resource = next((item for item in state.cells if (item.x, item.y) == point), None)
    particle_kinds = sorted(item.kind for item in state.causal.particles if (item.x, item.y) == point)
    bond_rule_ids = sorted(item.rule_id for item in state.causal.bonds if (item.x, item.y) == point)
    return {"bond_rule_ids": bond_rule_ids, "elevation": resource.elevation if resource else 0,
            "heat": heat, "mineral": resource.mineral if resource else 0,
            "particle_kinds": particle_kinds,
            "solutes": list(resource.solutes if resource else (0,) * spec.solute_kinds),
            "vapor": resource.vapor if resource else 0, "water": resource.water if resource else 0,
            "x": point[0], "y": point[1]}


class CognitiveMapAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "sparse-cognitive-map", "explicit-topology-state-map", "1",
            ("encode_sparse_map", "answer_local_state", "answer_shortest_path", "answer_reachability"),
            ("sealed_topology", "initial_state"), "private sparse topology and relevant-state map", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, spec: EnvironmentWorldSpec,
                state: EnvironmentState | None = None) -> ClaimSet:
        if challenge.task_kind != "answer_state_queries": raise ValueError("unsupported cognitive map task")
        state = initial_environment_state(spec) if state is None else state
        if challenge.visible_digest("spec") != spec.digest or challenge.visible_digest("initial_state") != state.digest:
            raise ValueError("challenge digests do not match supplied world")
        queries = (challenge.task_payload or {}).get("queries")
        if not isinstance(queries, list): raise ValueError("challenge needs a queries list")
        cognitive_map = build_cognitive_map(spec, state)
        claims = []; bridges = []
        for query in queries:
            query_id = query["query_id"]; kind = query.get("kind")
            if kind == "local_state":
                point = _point(query, "point", cognitive_map)
                answer = _cell_payload(cognitive_map.cell(point, spec.solute_kinds))
                payload = {"answer": answer, "query_id": query_id, "query_kind": kind}
                expected = {"local_state": answer}
            elif kind == "shortest_path":
                start = _point(query, "start", cognitive_map); goal = _point(query, "goal", cognitive_map)
                path = cognitive_map.shortest_path(start, goal)
                payload = {"answer": {"path": [list(x) for x in path] if path else None,
                                      "steps": len(path) - 1 if path else None},
                           "query_id": query_id, "query_kind": kind}
                expected = {"minimum_path_required": True, "start": list(start), "goal": list(goal)}
            elif kind == "reachable_within":
                start = _point(query, "start", cognitive_map); goal = _point(query, "goal", cognitive_map)
                limit = query.get("max_steps")
                if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                    raise ValueError("max_steps must be a nonnegative integer")
                path = cognitive_map.shortest_path(start, goal)
                reachable = path is not None and len(path) - 1 <= limit
                payload = {"answer": {"reachable": reachable}, "query_id": query_id, "query_kind": kind}
                expected = {"goal": list(goal), "max_steps": limit, "start": list(start)}
            else:
                claims.append(Claim(query_id, "unsupported_query", "unknown", state.digest,
                                    {"query_id": query_id, "query_kind": str(kind)}))
                continue
            claims.append(Claim(query_id, kind, "exact", state.digest, payload))
            bridges.append(EvidenceBridge(query_id, f"verify_{kind}", (spec.digest, state.digest), expected,
                                          ("answer differs from current state or topology",)))
        attachment = AttachmentDescriptor("cognitive_map", cognitive_map.digest,
                                          "sparse-cognitive-map-v1", "sparse-cognitive-map-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, tuple(claims), tuple(bridges), (attachment,))


def _point(query: Mapping[str, Any], name: str, cognitive_map: CognitiveMap) -> tuple[int, int]:
    value = query.get(name)
    if not isinstance(value, list) or len(value) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        raise ValueError(f"{name} must contain integer x and y")
    point = (value[0], value[1])
    if not (0 <= point[0] < cognitive_map.width and 0 <= point[1] < cognitive_map.height):
        raise ValueError(f"{name} lies outside the world")
    return point


def _oracle_distance(spec: EnvironmentWorldSpec, start: tuple[int, int], goal: tuple[int, int]) -> int | None:
    if start == goal: return 0
    blocked = {frozenset((edge.first, edge.second)) for edge in spec.blocked_edges}
    frontier = {start}; visited = {start}; distance = 0
    width, height = spec.causal_world.kernel.width, spec.causal_world.kernel.height
    while frontier:
        distance += 1; following = set()
        for x, y in frontier:
            for point in ((x, (y - 1) % height), ((x + 1) % width, y),
                          (x, (y + 1) % height), ((x - 1) % width, y)):
                if frozenset(((x, y), point)) in blocked or point in visited: continue
                if point == goal: return distance
                visited.add(point); following.add(point)
        frontier = following
    return None


def _valid_path(spec: EnvironmentWorldSpec, path: Any, start: tuple[int, int], goal: tuple[int, int]) -> bool:
    if not isinstance(path, list) or not path: return False
    points = []
    for value in path:
        if not isinstance(value, list) or len(value) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in value):
            return False
        points.append((value[0], value[1]))
    if points[0] != start or points[-1] != goal: return False
    blocked = {frozenset((edge.first, edge.second)) for edge in spec.blocked_edges}
    width, height = spec.causal_world.kernel.width, spec.causal_world.kernel.height
    for first, second in zip(points, points[1:]):
        dx = min((first[0] - second[0]) % width, (second[0] - first[0]) % width)
        dy = min((first[1] - second[1]) % height, (second[1] - first[1]) % height)
        if dx + dy != 1 or frozenset((first, second)) in blocked: return False
    return True


def evaluate_cognitive_map_claims(
    challenge: ObservationContract, claim_set: ClaimSet, spec: EnvironmentWorldSpec,
    state: EnvironmentState | None = None,
) -> BoundaryEvaluation:
    if claim_set.challenge_digest != challenge.digest: raise ValueError("claim set belongs to another challenge")
    state = initial_environment_state(spec) if state is None else state
    if challenge.visible_digest("spec") != spec.digest or challenge.visible_digest("initial_state") != state.digest:
        raise ValueError("challenge and world digests differ")
    queries = {item["query_id"]: item for item in (challenge.task_payload or {}).get("queries", [])}
    resource_map = build_cognitive_map(spec, state)
    verified = []; falsified = []; untested = []; findings = []
    for claim in claim_set.claims:
        query = queries.get(claim.claim_id)
        if query is None or claim.claim_kind == "unsupported_query":
            untested.append(claim.claim_id); findings.append({"claim_id": claim.claim_id, "reason": "unsupported query"})
            continue
        kind = query["kind"]; answer = claim.payload.get("answer")
        valid = False; detail: dict[str, object] = {}
        if kind == "local_state":
            point = _point(query, "point", resource_map)
            expected = _raw_state_payload(spec, state, point)
            valid = answer == expected; detail = {"expected": expected}
        elif kind == "shortest_path":
            start = _point(query, "start", resource_map); goal = _point(query, "goal", resource_map)
            distance = _oracle_distance(spec, start, goal)
            path = answer.get("path") if isinstance(answer, Mapping) else None
            steps = answer.get("steps") if isinstance(answer, Mapping) else None
            valid = distance is not None and steps == distance and _valid_path(spec, path, start, goal)
            detail = {"minimum_steps": distance}
        elif kind == "reachable_within":
            start = _point(query, "start", resource_map); goal = _point(query, "goal", resource_map)
            distance = _oracle_distance(spec, start, goal); limit = query["max_steps"]
            expected = distance is not None and distance <= limit
            valid = isinstance(answer, Mapping) and answer.get("reachable") is expected
            detail = {"minimum_steps": distance, "expected_reachable": expected}
        if valid:
            verified.append(claim.claim_id)
        else:
            falsified.append(claim.claim_id)
            findings.append({"claim_id": claim.claim_id, "reason": "query answer failed external verification", **detail})
    return BoundaryEvaluation(challenge.digest, claim_set.digest, state.digest,
                              tuple(verified), tuple(falsified), tuple(untested), tuple(findings))
