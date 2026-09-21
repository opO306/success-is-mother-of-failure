"""User-approval-gated held-out experiment proposals for theory revisions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .b_language import (
    AttachmentDescriptor,
    BoundaryEvaluation,
    CapabilityManifest,
    Claim,
    ClaimSet,
    ObservationContract,
)
from .environment_spec import EnvironmentWorldSpec
from .theory_revision import ResidualPattern, TheoryRevisionSet, TheoryVersion


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExperimentArm:
    arm_id: str
    arm_kind: str
    no_action_control: bool
    sealed_spec: Mapping[str, Any] | None
    source_evidence_digests: tuple[str, ...]
    resolves_proposal_ids: tuple[str, ...]
    expected_discriminating_outcomes: tuple[str, ...]
    tick_budget: int
    storage_budget_bytes: int
    status: str = "sealed-not-run"

    @property
    def spec_digest(self) -> str | None:
        return _digest(self.sealed_spec) if self.sealed_spec is not None else None

    def canonical(self) -> dict[str, object]:
        result = {"arm_id": self.arm_id, "arm_kind": self.arm_kind,
                  "expected_discriminating_outcomes": list(self.expected_discriminating_outcomes),
                  "no_action_control": self.no_action_control,
                  "resolves_proposal_ids": list(self.resolves_proposal_ids),
                  "source_evidence_digests": list(self.source_evidence_digests),
                  "status": self.status, "storage_budget_bytes": self.storage_budget_bytes,
                  "tick_budget": self.tick_budget}
        if self.sealed_spec is not None:
            result["sealed_spec"] = dict(self.sealed_spec); result["spec_digest"] = self.spec_digest
        return result


@dataclass(frozen=True)
class ExperimentProposal:
    proposal_id: str
    parent_theory_digest: str
    revision_set_digest: str
    residual_pattern_digest: str
    arms: tuple[ExperimentArm, ...]
    approval_status: str
    execution_allowed: bool
    approval_required: bool
    automatic_execution: bool

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"approval_required": self.approval_required, "approval_status": self.approval_status,
                "arms": [x.canonical() for x in self.arms],
                "automatic_execution": self.automatic_execution,
                "execution_allowed": self.execution_allowed, "format": "experiment-proposal-v1",
                "parent_theory_digest": self.parent_theory_digest,
                "proposal_id": self.proposal_id, "residual_pattern_digest": self.residual_pattern_digest,
                "revision_set_digest": self.revision_set_digest}


@dataclass(frozen=True)
class ExperimentProposalReview:
    proposal_digest: str
    governance_valid: bool
    control_arm_ids: tuple[str, ...]
    held_out_spec_digests: tuple[str, ...]
    covered_revision_ids: tuple[str, ...]
    missing_revision_ids: tuple[str, ...]
    execution_blocked_pending_approval: bool
    scientific_status: str

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"control_arm_ids": list(self.control_arm_ids),
                "covered_revision_ids": list(self.covered_revision_ids),
                "execution_blocked_pending_approval": self.execution_blocked_pending_approval,
                "format": "experiment-proposal-review-v1", "governance_valid": self.governance_valid,
                "held_out_spec_digests": list(self.held_out_spec_digests),
                "missing_revision_ids": list(self.missing_revision_ids),
                "proposal_digest": self.proposal_digest, "scientific_status": self.scientific_status}


def _heldout_spec(base_raw: Mapping[str, Any], arm_id: str, vapor_amount: int) -> dict[str, Any]:
    raw = json.loads(json.dumps(base_raw))
    raw["causal_world"]["world_id"] = f"{arm_id}-sealed"
    raw["causal_world"]["execution"]["ticks"] = 2
    raw["causal_world"]["observer"]["hash_interval"] = 1
    raw["cells"][1]["vapor"] = vapor_amount
    spec = EnvironmentWorldSpec.from_mapping(raw)
    return spec.canonical()


def make_experiment_proposal_challenge(pattern: ResidualPattern, revisions: TheoryRevisionSet,
                                       parent: TheoryVersion) -> ObservationContract:
    return ObservationContract(
        f"experiment-proposal:{revisions.digest[:20]}", "propose_held_out_experiment",
        (("residual_pattern", pattern.digest), ("revision_set", revisions.digest),
         ("parent_theory", parent.digest)),
        ("approved_residual_pattern", "candidate_revision_set", "base_world_template"),
        ("held_out_results", "other_experiment_proposals", "approval_decision", "raw_vault_paths"),
        0, 4096, 262144,
        ("no-action control exists", "every revision candidate has a distinguishing arm",
         "all world specs are sealed before approval", "execution remains blocked pending user approval"),
        {"approval_required": True, "scientific_status": "not-run"},
    )


class ExperimentProposalAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "held-out-experiment-proposal", "approval-gated-experiment-design", "1",
            ("propose_trace_audit_control", "propose_no_action_control",
             "propose_held_out_worlds", "declare_budgets", "require_user_approval"),
            ("approved_residual_pattern", "candidate_revision_set", "base_world_template"),
            "private arm design with sealed specs and explicit approval gate", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, pattern: ResidualPattern,
                revisions: TheoryRevisionSet, parent: TheoryVersion,
                base_world_raw: Mapping[str, Any]) -> tuple[ClaimSet, ExperimentProposal]:
        if challenge.task_kind != "propose_held_out_experiment": raise ValueError("unsupported experiment task")
        revision_ids = tuple(item.proposal_id for item in revisions.proposals)
        trace_id = next(item for item in revision_ids if item == "check-observation-pipeline")
        variable_id = next(item for item in revision_ids if item.startswith("add-observed-"))
        relation_id = next(item for item in revision_ids if item.startswith("model-") and item.endswith("-relation"))
        evidence = tuple(item.evidence_digest for item in pattern.occurrences)
        arms = (
            ExperimentArm("trace-audit-control", "independent_trace_extraction", True, None, evidence,
                          (trace_id,),
                          ("independent extraction agrees: observation-error proposal loses support",
                           "independent extraction disagrees: inspect trace pipeline before theory changes"),
                          0, 65536),
            ExperimentArm("zero-vapor-control", "sealed_no_action_world", True,
                          _heldout_spec(base_world_raw, "zero-vapor-control", 0), (),
                          (variable_id, relation_id),
                          ("no vapor change should be reported when initial vapor is absent",
                           "a reported vapor residual would indicate extraction or relation error"),
                          2, 131072),
            ExperimentArm("heldout-vapor-5", "sealed_no_action_world", True,
                          _heldout_spec(base_world_raw, "heldout-vapor-5", 5), (),
                          (variable_id, relation_id),
                          ("parent theory predicts no vapor locations",
                           "variable-only theory observes vapor but does not predict its transition",
                           "relation theory must predict changed vapor locations and amounts"),
                          2, 131072),
            ExperimentArm("heldout-vapor-13", "sealed_no_action_world", True,
                          _heldout_spec(base_world_raw, "heldout-vapor-13", 13), (),
                          (variable_id, relation_id),
                          ("test relation outside training amounts 4,6,8,10",
                           "compare location and amount residuals against unchanged parent"),
                          2, 131072),
        )
        proposal = ExperimentProposal(
            "vapor-theory-heldout-v1", parent.digest, revisions.digest, pattern.digest,
            arms, "pending-user-approval", False, True, False,
        )
        claim = Claim("held-out-experiment-proposal", "experiment_proposal", "hypothesis",
                      revisions.digest, {"proposal": proposal.canonical()})
        attachment = AttachmentDescriptor("experiment_proposal", proposal.digest,
                                          "experiment-proposal-v1", "experiment-proposal-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, (claim,), (), (attachment,)), proposal


def review_experiment_proposal(challenge: ObservationContract, claim_set: ClaimSet,
                               proposal: ExperimentProposal,
                               revisions: TheoryRevisionSet,
                               training_spec_digests: tuple[str, ...]) -> tuple[BoundaryEvaluation, ExperimentProposalReview]:
    controls = tuple(item.arm_id for item in proposal.arms if item.no_action_control)
    heldout = tuple(item.spec_digest for item in proposal.arms if item.spec_digest is not None)
    covered = tuple(sorted({value for item in proposal.arms for value in item.resolves_proposal_ids}))
    revision_ids = {item.proposal_id for item in revisions.proposals}
    missing = tuple(sorted(revision_ids - set(covered)))
    unique_heldout = len(set(heldout)) == len(heldout)
    outside_training = not (set(heldout) & set(training_spec_digests))
    blocked = (proposal.approval_status == "pending-user-approval" and not proposal.execution_allowed
               and proposal.approval_required and not proposal.automatic_execution)
    valid = bool(controls) and not missing and unique_heldout and outside_training and blocked
    review = ExperimentProposalReview(proposal.digest, valid, controls, heldout, covered, missing,
                                      blocked, "not-run")
    boundary = BoundaryEvaluation(
        challenge.digest, claim_set.digest, revisions.digest, (),
        () if valid else ("held-out-experiment-proposal",),
        ("held-out-experiment-proposal",) if valid else (),
        ({"execution_blocked": blocked, "governance_valid": valid,
          "review_digest": review.digest, "scientific_status": "not-run"},),
    )
    return boundary, review


def require_experiment_authorization(proposal: ExperimentProposal) -> None:
    if not proposal.execution_allowed or proposal.approval_status != "approved":
        raise PermissionError("experiment proposal is pending explicit user approval")
