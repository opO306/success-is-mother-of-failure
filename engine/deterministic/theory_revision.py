"""Repeated residual patterns and non-destructive theory revision proposals."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .b_language import (
    AttachmentDescriptor,
    BoundaryEvaluation,
    CapabilityManifest,
    Claim,
    ClaimSet,
    ObservationContract,
)
from .environment_spec import EnvironmentWorldSpec
from .provenance import verify_trace


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TheoryVersion:
    theory_id: str
    parent_theory_digest: str | None
    state_variables: tuple[str, ...]
    relations: tuple[str, ...]
    status: str = "active-baseline"

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        result = {"format": "theory-version-v1", "relations": list(self.relations),
                  "state_variables": list(self.state_variables), "status": self.status,
                  "theory_id": self.theory_id}
        if self.parent_theory_digest is not None: result["parent_theory_digest"] = self.parent_theory_digest
        return result


@dataclass(frozen=True)
class PredictionResidual:
    residual_id: str
    run_id: str
    spec_digest: str
    evidence_digest: str
    source_tick: int
    target_tick: int
    component: str
    signature: str
    predicted_changed_locations: tuple[tuple[int, int], ...]
    actual_changed_locations: tuple[tuple[int, int], ...]

    def canonical(self) -> dict[str, object]:
        return {"actual_changed_locations": [list(x) for x in self.actual_changed_locations],
                "component": self.component, "evidence_digest": self.evidence_digest,
                "format": "prediction-residual-v1",
                "predicted_changed_locations": [list(x) for x in self.predicted_changed_locations],
                "residual_id": self.residual_id, "run_id": self.run_id,
                "signature": self.signature, "source_tick": self.source_tick,
                "spec_digest": self.spec_digest, "target_tick": self.target_tick}


@dataclass(frozen=True)
class ResidualPattern:
    pattern_id: str
    signature: str
    component: str
    cause_tier: str
    occurrences: tuple[PredictionResidual, ...]
    minimum_distinct_runs: int

    @property
    def distinct_run_count(self) -> int: return len({item.run_id for item in self.occurrences})

    @property
    def distinct_spec_count(self) -> int: return len({item.spec_digest for item in self.occurrences})

    @property
    def repeated(self) -> bool:
        return self.distinct_run_count >= self.minimum_distinct_runs and self.distinct_spec_count >= self.minimum_distinct_runs

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"cause_tier": self.cause_tier, "component": self.component,
                "distinct_run_count": self.distinct_run_count, "distinct_spec_count": self.distinct_spec_count,
                "format": "residual-pattern-v1", "minimum_distinct_runs": self.minimum_distinct_runs,
                "occurrences": [x.canonical() for x in self.occurrences],
                "pattern_id": self.pattern_id, "repeated": self.repeated, "signature": self.signature}


@dataclass(frozen=True)
class TheoryRevisionProposal:
    proposal_id: str
    parent_theory_digest: str
    trigger_pattern_digest: str
    cause_tier: str
    proposal_kind: str
    proposed_changes: tuple[str, ...]
    expected_new_predictions: tuple[str, ...]
    required_tests: tuple[str, ...]
    known_limitations: tuple[str, ...]
    status: str = "candidate-not-applied"

    def canonical(self) -> dict[str, object]:
        return {"cause_tier": self.cause_tier,
                "expected_new_predictions": list(self.expected_new_predictions),
                "known_limitations": list(self.known_limitations),
                "parent_theory_digest": self.parent_theory_digest,
                "proposal_id": self.proposal_id, "proposal_kind": self.proposal_kind,
                "proposed_changes": list(self.proposed_changes),
                "required_tests": list(self.required_tests), "status": self.status,
                "trigger_pattern_digest": self.trigger_pattern_digest}


@dataclass(frozen=True)
class TheoryRevisionSet:
    parent_theory_digest: str
    trigger_pattern_digest: str
    proposals: tuple[TheoryRevisionProposal, ...]
    applied_proposal_id: str | None
    selection_policy: str

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"applied_proposal_id": self.applied_proposal_id,
                "format": "theory-revision-set-v1", "parent_theory_digest": self.parent_theory_digest,
                "proposals": [x.canonical() for x in self.proposals],
                "selection_policy": self.selection_policy,
                "trigger_pattern_digest": self.trigger_pattern_digest}


@dataclass(frozen=True)
class TheoryRevisionReview:
    revision_set_digest: str
    governance_admissible_ids: tuple[str, ...]
    governance_rejected_ids: tuple[str, ...]
    scientifically_verified_ids: tuple[str, ...]
    scientifically_untested_ids: tuple[str, ...]
    parent_unchanged: bool

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"format": "theory-revision-review-v1",
                "governance_admissible_ids": list(self.governance_admissible_ids),
                "governance_rejected_ids": list(self.governance_rejected_ids),
                "parent_unchanged": self.parent_unchanged,
                "revision_set_digest": self.revision_set_digest,
                "scientifically_untested_ids": list(self.scientifically_untested_ids),
                "scientifically_verified_ids": list(self.scientifically_verified_ids)}


def _snapshot(records: list[dict[str, Any]], tick: int) -> dict[str, Any]:
    if tick == 0:
        return next(item["payload"]["full_snapshot"] for item in records
                    if item["stream"] == "A" and item["kind"] == "run_start")
    return next(item["payload"]["full_snapshot"] for item in records
                if item["stream"] == "A" and item["kind"] == "tick_commit" and int(item["tick"]) == tick)


def _component_locations(snapshot: dict[str, Any], component: str) -> dict[tuple[int, int], int]:
    if component == "vapor":
        return {(item["x"], item["y"]): int(item.get("vapor", 0))
                for item in snapshot.get("cells", []) if int(item.get("vapor", 0))}
    if component == "water":
        return {(item["x"], item["y"]): int(item.get("water", 0))
                for item in snapshot.get("cells", []) if int(item.get("water", 0))}
    if component == "heat":
        return {(item["x"], item["y"]): int(item["energy"])
                for item in snapshot.get("causal", {}).get("heat", [])}
    raise ValueError("unsupported residual component")


def collect_omitted_component_residual(run_dir: Path, run_id: str, spec: EnvironmentWorldSpec,
                                       theory: TheoryVersion, component: str,
                                       source_tick: int, target_tick: int) -> PredictionResidual:
    if component in theory.state_variables: raise ValueError("component is not omitted from this theory")
    verification = verify_trace(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["spec_digest"] != spec.digest: raise ValueError("trace and specification differ")
    records = [json.loads(line) for line in (run_dir / manifest["records_file"]).read_text(encoding="utf-8").splitlines()]
    before = _component_locations(_snapshot(records, source_tick), component)
    after = _component_locations(_snapshot(records, target_tick), component)
    actual = tuple(sorted(point for point in set(before) | set(after) if before.get(point, 0) != after.get(point, 0)))
    signature = f"state-omission:{component}:changed-while-unmodeled"
    return PredictionResidual(f"{run_id}:{component}:{source_tick}-{target_tick}", run_id, spec.digest,
                              verification["final_chain_hash"], source_tick, target_tick,
                              component, signature, (), actual)


def build_residual_pattern(residuals: tuple[PredictionResidual, ...],
                           minimum_distinct_runs: int = 3) -> ResidualPattern:
    if not residuals: raise ValueError("residual pattern needs occurrences")
    signatures = {item.signature for item in residuals}; components = {item.component for item in residuals}
    if len(signatures) != 1 or len(components) != 1: raise ValueError("residual pattern occurrences must share signature and component")
    component = residuals[0].component
    cause = "state_omission" if all(item.actual_changed_locations for item in residuals) else "observation_or_trace"
    return ResidualPattern(f"repeated-{component}-omission", residuals[0].signature, component,
                           cause, tuple(sorted(residuals, key=lambda x: x.run_id)), minimum_distinct_runs)


def make_theory_revision_challenge(pattern: ResidualPattern,
                                   theory: TheoryVersion) -> ObservationContract:
    return ObservationContract(
        f"theory-revision:{pattern.digest[:20]}", "propose_theory_revisions",
        (("residual_pattern", pattern.digest), ("parent_theory", theory.digest)),
        ("approved_residual_pattern", "parent_theory_manifest"),
        ("raw_vault_paths", "held_out_revision_results", "other_adapter_proposals"),
        0, max(1, len(pattern.occurrences) * 16), 65536,
        ("one residual is insufficient for structural revision",
         "parent theory remains unchanged", "all proposals remain scientifically untested until held-out evaluation"),
        {"distinct_runs": pattern.distinct_run_count, "minimum_distinct_runs": pattern.minimum_distinct_runs},
    )


class TheoryRevisionAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "hierarchical-theory-revision", "non-destructive-structure-revision", "1",
            ("group_repeated_residuals", "propose_observation_check", "propose_state_variable",
             "propose_relation_revision", "preserve_parent_theory"),
            ("approved_residual_pattern", "parent_theory_manifest"),
            "private failure-cause hierarchy with parallel candidate revisions", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, pattern: ResidualPattern,
                theory: TheoryVersion) -> tuple[ClaimSet, TheoryRevisionSet]:
        if challenge.task_kind != "propose_theory_revisions": raise ValueError("unsupported theory revision task")
        if challenge.visible_digest("residual_pattern") != pattern.digest: raise ValueError("challenge pattern differs")
        proposals = []
        if pattern.repeated:
            common_tests = ("evaluate on held-out sealed worlds", "compare against unchanged parent theory",
                            "record complexity and compute separately")
            proposals.extend((
                TheoryRevisionProposal(
                    "check-observation-pipeline", theory.digest, pattern.digest, "observation_or_trace",
                    "observation_error_model", (f"audit {pattern.component} extraction and trace reconstruction",),
                    ("predict whether residual disappears after independent extraction",), common_tests,
                    ("does not model the physical component",)),
                TheoryRevisionProposal(
                    f"add-observed-{pattern.component}", theory.digest, pattern.digest, "state_omission",
                    "add_observed_state_variable", (f"add existing observed variable {pattern.component}",),
                    (f"predict {pattern.component} changes explicitly",), common_tests,
                    ("adding the variable alone does not identify its transition relation",)),
                TheoryRevisionProposal(
                    f"model-{pattern.component}-relation", theory.digest, pattern.digest, "relation_error",
                    "revise_transition_relation", (f"add a local transition relation for {pattern.component}",),
                    (f"predict changed locations and amounts for {pattern.component}",), common_tests,
                    ("relation form is not selected by this proposal",)),
            ))
        revisions = TheoryRevisionSet(theory.digest, pattern.digest, tuple(proposals), None,
                                      "parallel candidates; no automatic application or scalar winner")
        claims = tuple(Claim(item.proposal_id, "theory_revision_proposal", "hypothesis", theory.digest,
                             {"proposal": item.canonical()}) for item in proposals)
        attachment = AttachmentDescriptor("theory_revision_set", revisions.digest,
                                          "theory-revision-set-v1", "theory-revision-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, claims, (), (attachment,)), revisions


def review_theory_revision_set(challenge: ObservationContract, claim_set: ClaimSet,
                               revisions: TheoryRevisionSet,
                               parent: TheoryVersion) -> tuple[BoundaryEvaluation, TheoryRevisionReview]:
    proposal_ids = tuple(item.proposal_id for item in revisions.proposals)
    parent_unchanged = parent.digest == revisions.parent_theory_digest and revisions.applied_proposal_id is None
    admissible = tuple(item.proposal_id for item in revisions.proposals
                       if item.status == "candidate-not-applied" and item.parent_theory_digest == parent.digest
                       and item.required_tests)
    rejected = tuple(item for item in proposal_ids if item not in admissible)
    review = TheoryRevisionReview(revisions.digest, admissible, rejected, (), admissible, parent_unchanged)
    boundary = BoundaryEvaluation(
        challenge.digest, claim_set.digest, parent.digest, (), rejected, admissible,
        ({"governance_admissible_count": len(admissible), "parent_unchanged": parent_unchanged,
          "review_digest": review.digest, "scientifically_verified_count": 0},),
    )
    return boundary, review
