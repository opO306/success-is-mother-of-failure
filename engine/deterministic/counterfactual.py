"""Multi-fidelity counterfactual branches with an explicit no-action control."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, Mapping

from .b_language import (
    AttachmentDescriptor,
    BoundaryEvaluation,
    CapabilityManifest,
    Claim,
    ClaimSet,
    ObservationContract,
)
from .causal_kernel import CausalWorldState
from .causal_spec import HeatCellSpec
from .cognitive_map import build_cognitive_map
from .environment_kernel import EnvironmentState, initial_environment_state, step_environment_world
from .environment_spec import BlockedEdgeSpec, EnvironmentWorldSpec
from .impact_scope import predict_next_impact_scope
from .trace_view_broker import ApprovedChangeView


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bytes(value: object) -> int:
    if hasattr(value, "canonical"): value = value.canonical()
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


@dataclass(frozen=True)
class CounterfactualAction:
    action_kind: str
    parameters: Mapping[str, Any]

    def canonical(self) -> dict[str, object]:
        return {"action_kind": self.action_kind, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class CounterfactualBranch:
    branch_id: str
    parent_state_digest: str
    branch_kind: str
    action: CounterfactualAction
    preservation_dimensions: tuple[str, ...]
    rationale: str

    def canonical(self) -> dict[str, object]:
        return {"action": self.action.canonical(), "branch_id": self.branch_id,
                "branch_kind": self.branch_kind, "parent_state_digest": self.parent_state_digest,
                "preservation_dimensions": list(self.preservation_dimensions), "rationale": self.rationale}


@dataclass(frozen=True)
class FidelityResult:
    branch_id: str
    fidelity: str
    status: str
    compute_units: int
    payload: Mapping[str, Any]

    def canonical(self) -> dict[str, object]:
        return {"branch_id": self.branch_id, "compute_units": self.compute_units,
                "fidelity": self.fidelity, "payload": dict(self.payload), "status": self.status}


@dataclass(frozen=True)
class CounterfactualPlan:
    parent_state_digest: str
    source_tick: int
    target_tick: int
    branches: tuple[CounterfactualBranch, ...]
    exact_budget: int
    exact_selection_tracks: tuple[str, ...]
    ranking_policy: str

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"branches": [x.canonical() for x in self.branches], "exact_budget": self.exact_budget,
                "exact_selection_tracks": list(self.exact_selection_tracks),
                "format": "counterfactual-plan-v1", "parent_state_digest": self.parent_state_digest,
                "ranking_policy": self.ranking_policy, "source_tick": self.source_tick,
                "target_tick": self.target_tick}


@dataclass(frozen=True)
class CounterfactualEvaluation:
    plan_digest: str
    fidelity_results: tuple[FidelityResult, ...]
    exact_branch_ids: tuple[str, ...]
    deferred_branch_ids: tuple[str, ...]
    control_present: bool
    all_branches_retained: bool

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"all_branches_retained": self.all_branches_retained,
                "control_present": self.control_present,
                "deferred_branch_ids": list(self.deferred_branch_ids),
                "exact_branch_ids": list(self.exact_branch_ids),
                "fidelity_results": [x.canonical() for x in self.fidelity_results],
                "format": "counterfactual-evaluation-v1", "plan_digest": self.plan_digest}


def make_counterfactual_challenge(view: ApprovedChangeView,
                                  spec: EnvironmentWorldSpec) -> ObservationContract:
    return ObservationContract(
        f"counterfactual:{view.digest[:20]}:{view.target_tick + 1}", "propose_counterfactual_branches",
        (("approved_change_view", view.digest), ("spec", spec.digest)),
        ("approved_change_view", "sealed_rule_parameters"),
        ("raw_vault_path", "actual_future_checkpoints", "exact_branch_results", "other_adapter_answers"),
        1, view.width * view.height * 8, view.width * view.height * 32,
        ("no-action control is retained", "every proposed branch remains in lineage",
         "exact budget is allocated by declared tracks without an aggregate score"),
        {"source_tick": view.target_tick, "target_tick": view.target_tick + 1},
    )


class CounterfactualBranchAdapter:
    def __init__(self, exact_budget: int = 3) -> None:
        if exact_budget < 1: raise ValueError("exact budget must be positive")
        self.exact_budget = exact_budget
        self._manifest = CapabilityManifest(
            "multi-fidelity-counterfactual", "branch-preserving-counterfactual-manager", "1",
            ("propose_counterfactual_branches", "preserve_no_action_control",
             "allocate_fidelity_by_tracks", "retain_deferred_branches"),
            ("approved_change_view", "sealed_rule_parameters"),
            "private branch set with separate control, risk, uncertainty, diversity, and counterexample tracks", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, view: ApprovedChangeView,
                spec: EnvironmentWorldSpec) -> tuple[ClaimSet, CounterfactualPlan]:
        if challenge.task_kind != "propose_counterfactual_branches": raise ValueError("unsupported counterfactual task")
        if challenge.visible_digest("approved_change_view") != view.digest: raise ValueError("challenge view differs")
        branches = (
            CounterfactualBranch("control-no-action", view.events[-1].after_digest, "control",
                                 CounterfactualAction("no_action", {}), ("control",),
                                 "preserve the world without intervention"),
            CounterfactualBranch("heat-pulse-small", view.events[-1].after_digest, "action",
                                 CounterfactualAction("add_local_heat", {"amount": 1, "point": [4, 4]}),
                                 ("uncertainty",), "test a minimal local energy intervention"),
            CounterfactualBranch("heat-pulse-large", view.events[-1].after_digest, "action",
                                 CounterfactualAction("add_local_heat", {"amount": 4, "point": [4, 4]}),
                                 ("risk",), "retain a stronger intervention as the risk track"),
            CounterfactualBranch("heat-pulse-far", view.events[-1].after_digest, "action",
                                 CounterfactualAction("add_local_heat", {"amount": 4, "point": [28, 28]}),
                                 ("structural_diversity",), "test a distant independent intervention"),
            CounterfactualBranch("block-source-edge", view.events[-1].after_digest, "design",
                                 CounterfactualAction("add_blocked_edge", {"first": [4, 4], "second": [5, 4]}),
                                 ("counterexample",), "test whether a local topology change alters the next transition"),
        )
        plan = CounterfactualPlan(view.events[-1].after_digest, view.target_tick, view.target_tick + 1,
                                  branches, self.exact_budget, ("control", "risk", "counterexample"),
                                  "no aggregate score; preserve every branch and allocate exact slots by named tracks")
        claims = tuple(Claim(item.branch_id, "counterfactual_branch", "hypothesis", view.digest,
                             {"branch": item.canonical()}) for item in branches)
        attachment = AttachmentDescriptor("counterfactual_plan", plan.digest,
                                          "counterfactual-plan-v1", "counterfactual-plan-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, claims, (), (attachment,)), plan


def _state_at_tick(spec: EnvironmentWorldSpec, tick: int) -> EnvironmentState:
    state = initial_environment_state(spec)
    for _ in range(tick): state = step_environment_world(spec, state)
    return state


def _apply_action(spec: EnvironmentWorldSpec, state: EnvironmentState,
                  action: CounterfactualAction) -> tuple[EnvironmentWorldSpec, EnvironmentState]:
    if action.action_kind == "no_action": return spec, state
    if action.action_kind == "add_local_heat":
        x, y = action.parameters["point"]; amount = int(action.parameters["amount"])
        heat = {(item.x, item.y): item.energy for item in state.causal.heat}
        heat[(x, y)] = heat.get((x, y), 0) + amount
        causal = replace(state.causal, tick=state.tick,
                         heat=tuple(HeatCellSpec(px, py, value)
                                    for (px, py), value in sorted(heat.items()) if value))
        return spec, EnvironmentState(causal, state.cells, state.energy_supplied + amount,
                                      state.energy_removed, state.format)
    if action.action_kind == "add_blocked_edge":
        first = tuple(action.parameters["first"]); second = tuple(action.parameters["second"])
        edge = BlockedEdgeSpec(first, second)
        if edge in spec.blocked_edges: return spec, state
        return replace(spec, blocked_edges=tuple(sorted(spec.blocked_edges + (edge,)))), state
    raise ValueError("unsupported counterfactual action")


def _select_exact(plan: CounterfactualPlan) -> tuple[str, ...]:
    selected = []
    for track in plan.exact_selection_tracks:
        candidate = next((branch for branch in plan.branches
                          if track in branch.preservation_dimensions and branch.branch_id not in selected), None)
        if candidate is not None and len(selected) < plan.exact_budget: selected.append(candidate.branch_id)
    return tuple(selected)


def execute_counterfactual_plan(challenge: ObservationContract, claim_set: ClaimSet,
                                plan: CounterfactualPlan, view: ApprovedChangeView,
                                spec: EnvironmentWorldSpec) -> tuple[BoundaryEvaluation, CounterfactualEvaluation]:
    if claim_set.challenge_digest != challenge.digest: raise ValueError("claim set belongs to another challenge")
    if {item.claim_id for item in claim_set.claims} != {item.branch_id for item in plan.branches}:
        raise ValueError("claim set and branch plan ids differ")
    parent = _state_at_tick(spec, plan.source_tick)
    if parent.digest != plan.parent_state_digest: raise ValueError("counterfactual parent differs from approved trace")
    base_scope = predict_next_impact_scope(view, spec); exact_ids = _select_exact(plan)
    results = []
    for branch in plan.branches:
        branch_spec, branch_state = _apply_action(spec, parent, branch.action)
        direct = branch.action.parameters.get("point") if branch.action.action_kind == "add_local_heat" else None
        scope = set(base_scope.predicted_locations)
        if isinstance(direct, list): scope.add((direct[0], direct[1]))
        results.append(FidelityResult(branch.branch_id, "low", "completed", len(scope),
                                      {"candidate_locations": len(scope), "direct_intervention": direct}))
        cognitive = build_cognitive_map(branch_spec, branch_state)
        results.append(FidelityResult(branch.branch_id, "medium", "completed", cognitive.stored_cell_count,
                                      {"map_digest": cognitive.digest,
                                       "representation_bytes": _bytes(cognitive),
                                       "stored_cells": cognitive.stored_cell_count}))
        if branch.branch_id in exact_ids:
            final = step_environment_world(branch_spec, branch_state)
            results.append(FidelityResult(branch.branch_id, "exact", "completed",
                                          branch_spec.causal_world.kernel.width * branch_spec.causal_world.kernel.height,
                                          {"accounted_energy": final.energy_account(branch_spec)["accounted"],
                                           "final_state_digest": final.digest,
                                           "spec_digest": branch_spec.digest}))
        else:
            results.append(FidelityResult(branch.branch_id, "exact", "deferred_budget", 0,
                                          {"reason": "exact slot not allocated by preserved selection tracks"}))
    deferred = tuple(item.branch_id for item in plan.branches if item.branch_id not in exact_ids)
    evaluation = CounterfactualEvaluation(
        plan.digest, tuple(results), exact_ids, deferred,
        any(item.action.action_kind == "no_action" for item in plan.branches),
        len({item.branch_id for item in plan.branches}) == len(plan.branches),
    )
    claim_ids = tuple(item.branch_id for item in plan.branches)
    boundary = BoundaryEvaluation(
        challenge.digest, claim_set.digest, parent.digest,
        exact_ids, (), deferred,
        ({"all_branches_retained": evaluation.all_branches_retained,
          "control_present": evaluation.control_present,
          "deferred_count": len(deferred), "evaluation_digest": evaluation.digest,
          "exact_count": len(exact_ids), "proposed_count": len(claim_ids)},),
    )
    return boundary, evaluation
