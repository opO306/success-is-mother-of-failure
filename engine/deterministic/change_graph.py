"""Independent change-centered B candidate over approved trace deltas.

The adapter never receives a vault path and never calls A transition or forecast
functions. A trusted evaluator separately checks claims against the raw trace.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
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
from .environment_spec import EnvironmentWorldSpec
from .provenance import verify_trace
from .trace_view_broker import ApprovedChangeEvent, ApprovedChangeView


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _apply_delta(snapshot: Mapping[str, Any], delta: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    result: Any = copy.deepcopy(dict(snapshot))
    for change in delta:
        path = change["path"]
        if path == "$":
            result = copy.deepcopy(change.get("after"))
            continue
        if not isinstance(path, str) or not path.startswith("$."):
            raise ValueError("unsupported delta path")
        keys = path[2:].split("."); parent = result
        for key in keys[:-1]:
            if not isinstance(parent, dict) or key not in parent: raise ValueError("delta path is absent")
            parent = parent[key]
        if not isinstance(parent, dict): raise ValueError("delta parent is not an object")
        key = keys[-1]; operation = change["op"]
        if operation == "remove":
            if key not in parent: raise ValueError("delta remove target is absent")
            del parent[key]
        elif operation in ("add", "replace"):
            parent[key] = copy.deepcopy(change["after"])
        else:
            raise ValueError("unsupported delta operation")
    return result


@dataclass(frozen=True)
class ChangeGraphNode:
    event_id: str
    tick: int
    phase: str
    touched_paths: tuple[str, ...]
    parent_event_ids: tuple[str, ...]
    before_digest: str
    after_digest: str

    def canonical(self) -> dict[str, object]:
        return {"after_digest": self.after_digest, "before_digest": self.before_digest,
                "event_id": self.event_id, "parent_event_ids": list(self.parent_event_ids),
                "phase": self.phase, "tick": self.tick, "touched_paths": list(self.touched_paths)}


@dataclass(frozen=True)
class ChangeGraph:
    source_view_digest: str
    nodes: tuple[ChangeGraphNode, ...]
    reconstructed_snapshot: Mapping[str, Any]
    target_tick: int
    delta_operation_count: int
    width: int
    height: int
    blocked_edges: tuple[tuple[tuple[int, int], tuple[int, int]], ...]

    @property
    def digest(self) -> str: return _digest(self.canonical())

    @property
    def reconstructed_state_digest(self) -> str: return _digest(self.reconstructed_snapshot)

    def canonical(self) -> dict[str, object]:
        return {"blocked_edges": [[list(a), list(b)] for a, b in self.blocked_edges],
                "delta_operation_count": self.delta_operation_count, "format": "change-graph-v1",
                "height": self.height, "nodes": [x.canonical() for x in self.nodes],
                "reconstructed_state_digest": self.reconstructed_state_digest,
                "source_view_digest": self.source_view_digest, "target_tick": self.target_tick,
                "width": self.width}

    def last_change(self, requested_path: str) -> ChangeGraphNode | None:
        for node in reversed(self.nodes):
            if any(path == requested_path or path.startswith(requested_path + ".") or
                   requested_path.startswith(path + ".") for path in node.touched_paths):
                return node
        return None

    def neighbors(self, point: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        x, y = point
        candidates = ((x, (y - 1) % self.height), ((x + 1) % self.width, y),
                      (x, (y + 1) % self.height), ((x - 1) % self.width, y))
        blocked = {frozenset(edge) for edge in self.blocked_edges}
        return tuple(candidate for candidate in candidates if frozenset((point, candidate)) not in blocked)

    def shortest_path(self, start: tuple[int, int], goal: tuple[int, int]) -> tuple[tuple[int, int], ...] | None:
        if start == goal: return (start,)
        queue = deque([start]); previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            point = queue.popleft()
            for candidate in self.neighbors(point):
                if candidate in previous: continue
                previous[candidate] = point
                if candidate == goal:
                    path = [goal]; cursor = point
                    while cursor is not None:
                        path.append(cursor); cursor = previous[cursor]
                    return tuple(reversed(path))
                queue.append(candidate)
        return None


def build_change_graph(view: ApprovedChangeView) -> ChangeGraph:
    snapshot = copy.deepcopy(dict(view.initial_snapshot)); nodes = []
    previous_event = None; last_by_path: dict[str, str] = {}; operations = 0
    for event in view.events:
        if _digest(snapshot) != event.before_digest: raise ValueError("approved event before digest mismatch")
        after = _apply_delta(snapshot, event.delta)
        if _digest(after) != event.after_digest: raise ValueError("approved event after digest mismatch")
        paths = tuple(sorted(str(change["path"]) for change in event.delta))
        parents = []
        if previous_event is not None: parents.append(previous_event)
        for path in paths:
            prior = last_by_path.get(path)
            if prior is not None and prior not in parents: parents.append(prior)
        node = ChangeGraphNode(event.event_id, event.tick, event.phase, paths, tuple(parents),
                               event.before_digest, event.after_digest)
        nodes.append(node); previous_event = event.event_id; operations += len(event.delta)
        for path in paths: last_by_path[path] = event.event_id
        snapshot = after
    return ChangeGraph(view.digest, tuple(nodes), snapshot, view.target_tick, operations,
                       view.width, view.height, view.blocked_edges)


def _cell_from_snapshot(snapshot: Mapping[str, Any], point: tuple[int, int], solute_kinds: int) -> dict[str, object]:
    cells = snapshot.get("cells", [])
    item = next((cell for cell in cells if (cell.get("x"), cell.get("y")) == point), None)
    causal = snapshot.get("causal", {})
    heat = next((cell.get("energy", 0) for cell in causal.get("heat", [])
                 if (cell.get("x"), cell.get("y")) == point), 0)
    particles = sorted(cell.get("kind") for cell in causal.get("particles", [])
                       if (cell.get("x"), cell.get("y")) == point)
    bonds = sorted(cell.get("rule_id") for cell in causal.get("bonds", [])
                   if (cell.get("x"), cell.get("y")) == point)
    return {"bond_rule_ids": bonds, "elevation": item.get("elevation", 0) if item else 0,
            "heat": heat, "mineral": item.get("mineral", 0) if item else 0,
            "particle_kinds": particles, "solutes": item.get("solutes", [0] * solute_kinds) if item else [0] * solute_kinds,
            "vapor": item.get("vapor", 0) if item else 0, "water": item.get("water", 0) if item else 0,
            "x": point[0], "y": point[1]}


def make_change_graph_challenge(view: ApprovedChangeView,
                                queries: tuple[Mapping[str, Any], ...]) -> ObservationContract:
    if not queries: raise ValueError("change graph challenge needs queries")
    return ObservationContract(
        f"change-graph:{view.digest[:20]}", "answer_change_queries",
        (("approved_change_view", view.digest), ("spec", view.spec_digest),
         ("initial_state", view.initial_state_digest)),
        ("approved_initial_snapshot", "approved_stage_deltas"),
        ("raw_vault_path", "raw_full_stage_snapshots", "A_records_after_target_tick", "B_records"),
        view.target_tick, max(1, len(view.events) * 16), len(_canonical(view)) * 2,
        ("reconstructed digest matches committed A state", "local state matches committed A state",
         "change origin and spatial answers match the private trace and sealed topology"),
        {"queries": [dict(query) for query in queries]},
    )


def _query_point(query: Mapping[str, Any], name: str, graph: ChangeGraph) -> tuple[int, int]:
    value = query.get(name)
    if not isinstance(value, list) or len(value) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        raise ValueError(f"{name} must contain integer x and y")
    point = (value[0], value[1])
    if not (0 <= point[0] < graph.width and 0 <= point[1] < graph.height):
        raise ValueError(f"{name} lies outside the topology")
    return point


def _canonical(value: object) -> bytes:
    if hasattr(value, "canonical"): value = value.canonical()
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ChangeGraphAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "approved-delta-change-graph", "event-change-graph", "1",
            ("reconstruct_state", "answer_local_state", "answer_shortest_path",
             "answer_reachability", "locate_last_change", "trace_change_parents"),
            ("approved_initial_snapshot", "approved_stage_deltas"),
            "private event graph linked by sequence and last-changed paths", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, view: ApprovedChangeView) -> ClaimSet:
        if challenge.task_kind != "answer_change_queries": raise ValueError("unsupported change graph task")
        if challenge.visible_digest("approved_change_view") != view.digest:
            raise ValueError("challenge and approved view differ")
        graph = build_change_graph(view); queries = (challenge.task_payload or {}).get("queries")
        if not isinstance(queries, list): raise ValueError("challenge needs query list")
        claims = []; bridges = []
        for query in queries:
            query_id = query.get("query_id"); kind = query.get("kind")
            if not isinstance(query_id, str) or not query_id: raise ValueError("query_id must be non-empty text")
            if kind == "reconstructed_state_digest":
                answer: object = {"state_digest": graph.reconstructed_state_digest, "target_tick": view.target_tick}
            elif kind == "local_state":
                point = query.get("point")
                if not isinstance(point, list) or len(point) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in point):
                    raise ValueError("local_state point must contain integer x and y")
                answer = _cell_from_snapshot(graph.reconstructed_snapshot, (point[0], point[1]),
                                             int(query.get("solute_kinds", 0)))
            elif kind == "last_change":
                path = query.get("path")
                if not isinstance(path, str) or not path.startswith("$"): raise ValueError("last_change path is invalid")
                node = graph.last_change(path)
                answer = None if node is None else {"event_id": node.event_id, "phase": node.phase,
                                                     "tick": node.tick, "touched_paths": list(node.touched_paths)}
            elif kind == "shortest_path":
                start = _query_point(query, "start", graph); goal = _query_point(query, "goal", graph)
                path = graph.shortest_path(start, goal)
                answer = {"path": [list(x) for x in path] if path else None,
                          "steps": len(path) - 1 if path else None}
            elif kind == "reachable_within":
                start = _query_point(query, "start", graph); goal = _query_point(query, "goal", graph)
                limit = query.get("max_steps")
                if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                    raise ValueError("max_steps must be a nonnegative integer")
                path = graph.shortest_path(start, goal)
                answer = {"reachable": path is not None and len(path) - 1 <= limit}
            elif kind == "graph_cost":
                answer = {"delta_operations": graph.delta_operation_count, "nodes": len(graph.nodes),
                          "view_bytes": len(_canonical(view))}
            else:
                claims.append(Claim(query_id, "unsupported_query", "unknown", view.digest,
                                    {"query_id": query_id, "query_kind": str(kind)}))
                continue
            claims.append(Claim(query_id, str(kind), "exact", view.digest,
                                {"answer": answer, "query_id": query_id, "query_kind": kind}))
            bridges.append(EvidenceBridge(query_id, f"verify_{kind}_against_private_trace",
                                          (view.source_chain_hash, view.source_records_sha256),
                                          {"target_tick": view.target_tick},
                                          ("answer differs from verified private trace",)))
        attachment = AttachmentDescriptor("change_graph", graph.digest, "change-graph-v1", "change-graph-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, tuple(claims), tuple(bridges), (attachment,))


def _target_snapshot(records: list[dict[str, Any]], target_tick: int) -> Mapping[str, Any]:
    if target_tick == 0:
        return next(x["payload"]["full_snapshot"] for x in records
                    if x["stream"] == "A" and x["kind"] == "run_start")
    return next(x["payload"]["full_snapshot"] for x in records
                if x["stream"] == "A" and x["kind"] == "tick_commit" and int(x["tick"]) == target_tick)


def _sealed_distance(spec: EnvironmentWorldSpec, start: tuple[int, int], goal: tuple[int, int]) -> int | None:
    if start == goal: return 0
    width, height = spec.causal_world.kernel.width, spec.causal_world.kernel.height
    blocked = {frozenset((edge.first, edge.second)) for edge in spec.blocked_edges}
    frontier = {start}; visited = {start}; distance = 0
    while frontier:
        distance += 1; following = set()
        for x, y in frontier:
            for point in ((x, (y - 1) % height), ((x + 1) % width, y),
                          (x, (y + 1) % height), ((x - 1) % width, y)):
                if point in visited or frozenset(((x, y), point)) in blocked: continue
                if point == goal: return distance
                visited.add(point); following.add(point)
        frontier = following
    return None


def _sealed_path_valid(spec: EnvironmentWorldSpec, path: Any,
                       start: tuple[int, int], goal: tuple[int, int]) -> bool:
    if not isinstance(path, list) or not path: return False
    points = []
    for value in path:
        if not isinstance(value, list) or len(value) != 2 or any(isinstance(x, bool) or not isinstance(x, int) for x in value):
            return False
        points.append((value[0], value[1]))
    if points[0] != start or points[-1] != goal: return False
    width, height = spec.causal_world.kernel.width, spec.causal_world.kernel.height
    blocked = {frozenset((edge.first, edge.second)) for edge in spec.blocked_edges}
    for first, second in zip(points, points[1:]):
        dx = min((first[0] - second[0]) % width, (second[0] - first[0]) % width)
        dy = min((first[1] - second[1]) % height, (second[1] - first[1]) % height)
        if dx + dy != 1 or frozenset((first, second)) in blocked: return False
    return True


def evaluate_change_graph_claims(challenge: ObservationContract, claim_set: ClaimSet,
                                 run_dir: Path, spec: EnvironmentWorldSpec) -> BoundaryEvaluation:
    """Trusted verifier reads raw trace; candidate adapter never receives run_dir."""
    verification = verify_trace(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["spec_digest"] != spec.digest: raise ValueError("trace and specification differ")
    records = [json.loads(line) for line in (run_dir / manifest["records_file"]).read_text(encoding="utf-8").splitlines()]
    queries = {item["query_id"]: item for item in (challenge.task_payload or {}).get("queries", [])}
    target_tick = challenge.max_ticks; snapshot = _target_snapshot(records, target_tick)
    verified = []; falsified = []; untested = []; findings = []
    stages = [x for x in records if x["stream"] == "A" and x["kind"] == "stage_commit" and int(x["tick"]) <= target_tick]
    for claim in claim_set.claims:
        query = queries.get(claim.claim_id)
        if query is None or claim.claim_kind == "unsupported_query":
            untested.append(claim.claim_id); findings.append({"claim_id": claim.claim_id, "reason": "unsupported query"})
            continue
        kind = query["kind"]; answer = claim.payload.get("answer"); expected: object
        if kind == "reconstructed_state_digest":
            expected = {"state_digest": _digest(snapshot), "target_tick": target_tick}
        elif kind == "local_state":
            point = query["point"]
            expected = _cell_from_snapshot(snapshot, (point[0], point[1]), int(query.get("solute_kinds", 0)))
        elif kind == "last_change":
            path = query["path"]; matched = None
            for stage in stages:
                paths = sorted(str(item["path"]) for item in stage["payload"]["delta"])
                if any(value == path or value.startswith(path + ".") or path.startswith(value + ".") for value in paths):
                    matched = {"event_id": f"a-stage-{stage['sequence']}", "phase": stage["phase"],
                               "tick": stage["tick"], "touched_paths": paths}
            expected = matched
        elif kind == "shortest_path":
            start = (query["start"][0], query["start"][1]); goal = (query["goal"][0], query["goal"][1])
            distance = _sealed_distance(spec, start, goal)
            path = answer.get("path") if isinstance(answer, Mapping) else None
            steps = answer.get("steps") if isinstance(answer, Mapping) else None
            valid = distance is not None and steps == distance and _sealed_path_valid(spec, path, start, goal)
            expected = answer if valid else {"minimum_steps": distance, "valid_minimum_path": True}
        elif kind == "reachable_within":
            start = (query["start"][0], query["start"][1]); goal = (query["goal"][0], query["goal"][1])
            distance = _sealed_distance(spec, start, goal); limit = query["max_steps"]
            expected = {"reachable": distance is not None and distance <= limit}
        elif kind == "graph_cost":
            expected = answer
        else:
            untested.append(claim.claim_id); findings.append({"claim_id": claim.claim_id, "reason": "no evaluator"})
            continue
        if answer == expected:
            verified.append(claim.claim_id)
        else:
            falsified.append(claim.claim_id)
            findings.append({"claim_id": claim.claim_id, "expected": expected,
                             "reason": "answer differs from private trace or sealed topology"})
    return BoundaryEvaluation(challenge.digest, claim_set.digest, verification["final_chain_hash"],
                              tuple(verified), tuple(falsified), tuple(untested), tuple(findings))
