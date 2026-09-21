"""Conservative next-tick impact-scope prediction from an approved ChangeGraph view."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from .b_language import BoundaryEvaluation, CapabilityManifest, Claim, ClaimSet, EvidenceBridge, ObservationContract
from .change_graph import build_change_graph
from .environment_spec import EnvironmentWorldSpec
from .provenance import verify_trace
from .trace_view_broker import ApprovedChangeView


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _neighbors(point: tuple[int, int], view: ApprovedChangeView) -> tuple[tuple[int, int], ...]:
    x, y = point
    candidates = ((x, (y - 1) % view.height), ((x + 1) % view.width, y),
                  (x, (y + 1) % view.height), ((x - 1) % view.width, y))
    blocked = {frozenset(edge) for edge in view.blocked_edges}
    return tuple(item for item in candidates if frozenset((point, item)) not in blocked)


def _active_points(snapshot: Mapping[str, Any], spec: EnvironmentWorldSpec) -> set[tuple[int, int]]:
    points = {(item["x"], item["y"]) for item in snapshot.get("cells", [])}
    causal = snapshot.get("causal", {})
    for collection in ("heat", "particles", "bonds"):
        points.update((item["x"], item["y"]) for item in causal.get(collection, []))
    points.update((item.x, item.y) for item in spec.energy_boundaries)
    return points


def _expanded(points: set[tuple[int, int]], radius: int,
              view: ApprovedChangeView) -> set[tuple[int, int]]:
    result = set(points); frontier = set(points)
    for _ in range(radius):
        following = {candidate for point in frontier for candidate in _neighbors(point, view)} - result
        result.update(following); frontier = following
        if not frontier: break
    return result


def enabled_rule_scope(spec: EnvironmentWorldSpec) -> tuple[str, ...]:
    rules = []
    if spec.causal_world.particles or spec.causal_world.bond_rules: rules.append("causal_particle_or_bond")
    if spec.law.max_heat_transfer: rules.append("heat_transfer")
    if spec.law.max_water_transfer: rules.append("water_surface_transfer")
    if spec.law.max_solute_transfer or spec.law.max_carried_solute_per_water: rules.append("solute_transport")
    if spec.law.max_vapor_transfer: rules.append("vapor_transfer")
    if spec.energy_boundaries: rules.append("external_energy")
    if spec.law.max_mineral_conversion: rules.append("mineral_conversion")
    if spec.law.max_water_phase_change: rules.append("water_phase_change")
    return tuple(rules)


@dataclass(frozen=True)
class ImpactScopePrediction:
    source_view_digest: str
    source_tick: int
    target_tick: int
    predicted_locations: tuple[tuple[int, int], ...]
    predicted_rules: tuple[str, ...]
    full_grid_cells: int

    @property
    def coverage_cells(self) -> int: return len(self.predicted_locations)

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"coverage_cells": self.coverage_cells, "format": "next-impact-scope-v1",
                "full_grid_cells": self.full_grid_cells,
                "predicted_locations": [list(x) for x in self.predicted_locations],
                "predicted_rules": list(self.predicted_rules), "source_tick": self.source_tick,
                "source_view_digest": self.source_view_digest, "target_tick": self.target_tick}


@dataclass(frozen=True)
class ImpactScopeEvaluation:
    prediction_digest: str
    actual_locations: tuple[tuple[int, int], ...]
    missed_locations: tuple[tuple[int, int], ...]
    excess_locations: tuple[tuple[int, int], ...]
    actual_rules: tuple[str, ...]
    missed_rules: tuple[str, ...]
    excess_rules: tuple[str, ...]

    @property
    def complete_coverage(self) -> bool: return not self.missed_locations and not self.missed_rules

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"actual_locations": [list(x) for x in self.actual_locations],
                "actual_rules": list(self.actual_rules), "complete_coverage": self.complete_coverage,
                "excess_locations": [list(x) for x in self.excess_locations],
                "excess_rules": list(self.excess_rules), "format": "impact-scope-evaluation-v1",
                "missed_locations": [list(x) for x in self.missed_locations],
                "missed_rules": list(self.missed_rules), "prediction_digest": self.prediction_digest}


def predict_next_impact_scope(view: ApprovedChangeView,
                              spec: EnvironmentWorldSpec) -> ImpactScopePrediction:
    if view.spec_digest != spec.digest: raise ValueError("approved view and specification differ")
    graph = build_change_graph(view); active = _active_points(graph.reconstructed_snapshot, spec)
    transport_enabled = any((spec.law.max_heat_transfer, spec.law.max_water_transfer,
                             spec.law.max_solute_transfer, spec.law.max_carried_solute_per_water,
                             spec.law.max_vapor_transfer))
    radius = len(spec.law.phase_order) if transport_enabled else 0
    locations = _expanded(active, radius, view)
    return ImpactScopePrediction(view.digest, view.target_tick, view.target_tick + 1,
                                 tuple(sorted(locations)), enabled_rule_scope(spec), view.width * view.height)


def make_impact_scope_challenge(view: ApprovedChangeView,
                                spec: EnvironmentWorldSpec) -> ObservationContract:
    return ObservationContract(
        f"impact-scope:{view.digest[:20]}:{view.target_tick + 1}", "predict_next_impact_scope",
        (("approved_change_view", view.digest), ("spec", spec.digest)),
        ("approved_change_view", "sealed_rule_parameters"),
        ("raw_vault_path", "actual_target_tick_delta", "A_records_after_source_tick", "B_records"),
        1, view.width * view.height * max(1, len(spec.law.phase_order)),
        view.width * view.height * 16,
        ("no actual changed location is outside predicted scope",
         "no actual active rule class is omitted", "excess scope is recorded separately"),
        {"source_tick": view.target_tick, "target_tick": view.target_tick + 1},
    )


class ImpactScopeAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "change-graph-impact-scope", "conservative-change-influence", "1",
            ("predict_next_impact_scope", "declare_enabled_rule_scope"),
            ("approved_change_view", "sealed_rule_parameters"),
            "private active-region expansion over change graph and local rule radius", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, view: ApprovedChangeView,
                spec: EnvironmentWorldSpec) -> tuple[ClaimSet, ImpactScopePrediction]:
        if challenge.task_kind != "predict_next_impact_scope": raise ValueError("unsupported impact task")
        if challenge.visible_digest("approved_change_view") != view.digest: raise ValueError("challenge view differs")
        prediction = predict_next_impact_scope(view, spec)
        claim = Claim("next-impact-scope", "next_impact_scope", "approximate", view.digest,
                      {"prediction": prediction.canonical()})
        bridge = EvidenceBridge("next-impact-scope", "compare_private_next_tick_delta",
                                (view.source_chain_hash, view.source_records_sha256),
                                {"target_tick": prediction.target_tick},
                                ("an actual changed location lies outside the predicted scope",
                                 "an actual active rule class was omitted"))
        return ClaimSet(challenge.digest, self.manifest.digest, (claim,), (bridge,)), prediction


def _snapshot_at(records: list[dict[str, Any]], tick: int) -> Mapping[str, Any]:
    if tick == 0:
        return next(x["payload"]["full_snapshot"] for x in records
                    if x["stream"] == "A" and x["kind"] == "run_start")
    return next(x["payload"]["full_snapshot"] for x in records
                if x["stream"] == "A" and x["kind"] == "tick_commit" and int(x["tick"]) == tick)


def _location_map(snapshot: Mapping[str, Any]) -> dict[tuple[int, int], object]:
    result: dict[tuple[int, int], object] = {}
    for item in snapshot.get("cells", []): result[(item["x"], item["y"])] = ("cell", item)
    causal = snapshot.get("causal", {})
    for name in ("heat", "particles", "bonds"):
        for item in causal.get(name, []):
            point = (item["x"], item["y"])
            result[point] = (result.get(point), name, item)
    return result


def _actual_changed_locations(before: Mapping[str, Any], after: Mapping[str, Any]) -> set[tuple[int, int]]:
    before_map, after_map = _location_map(before), _location_map(after)
    return {point for point in set(before_map) | set(after_map) if before_map.get(point) != after_map.get(point)}


def actual_rule_classes(records: list[dict[str, Any]], tick: int) -> set[str]:
    rules = set(); previous = None
    for raw in records:
        if raw["stream"] != "A" or raw["kind"] != "stage_commit" or int(raw["tick"]) != tick: continue
        payload = raw["payload"]; after = payload["after_snapshot"]
        physical = [item for item in payload["delta"] if item["path"] != "$.causal.tick"]
        if not physical: previous = after; continue
        phase = raw["phase"]
        if phase == "causal": rules.add("causal_particle_or_bond")
        elif phase in ("external_energy", "mineral_conversion", "water_phase_change"):
            rules.add(phase)
        else:
            before = previous if previous is not None else after
            if before.get("causal", {}).get("heat") != after.get("causal", {}).get("heat"): rules.add("heat_transfer")
            before_cells = before.get("cells", []); after_cells = after.get("cells", [])
            if before_cells != after_cells:
                # The raw list changed; enabled transport classes remain conservative and are evaluated separately.
                rules.update(("water_surface_transfer", "solute_transport"))
        previous = after
    return rules


def evaluate_impact_scope(challenge: ObservationContract, claim_set: ClaimSet,
                          prediction: ImpactScopePrediction, run_dir: Path,
                          spec: EnvironmentWorldSpec) -> tuple[BoundaryEvaluation, ImpactScopeEvaluation]:
    verification = verify_trace(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (run_dir / manifest["records_file"]).read_text(encoding="utf-8").splitlines()]
    before = _snapshot_at(records, prediction.source_tick); after = _snapshot_at(records, prediction.target_tick)
    actual_locations = _actual_changed_locations(before, after)
    predicted_locations = set(prediction.predicted_locations)
    actual_rules = actual_rule_classes(records, prediction.target_tick)
    predicted_rules = set(prediction.predicted_rules)
    impact = ImpactScopeEvaluation(
        prediction.digest, tuple(sorted(actual_locations)), tuple(sorted(actual_locations - predicted_locations)),
        tuple(sorted(predicted_locations - actual_locations)), tuple(sorted(actual_rules)),
        tuple(sorted(actual_rules - predicted_rules)), tuple(sorted(predicted_rules - actual_rules)),
    )
    claim_id = claim_set.claims[0].claim_id if claim_set.claims else "next-impact-scope"
    findings = ({"actual_location_count": len(impact.actual_locations),
                 "excess_location_count": len(impact.excess_locations),
                 "excess_rule_count": len(impact.excess_rules),
                 "impact_evaluation_digest": impact.digest,
                 "missed_location_count": len(impact.missed_locations),
                 "missed_rule_count": len(impact.missed_rules)},)
    boundary = BoundaryEvaluation(challenge.digest, claim_set.digest, verification["final_chain_hash"],
                                  (claim_id,) if impact.complete_coverage else (),
                                  () if impact.complete_coverage else (claim_id,), (), findings)
    return boundary, impact
