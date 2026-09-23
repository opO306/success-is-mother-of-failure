"""Model-neutral hypothesis sets for epistemic uncertainty over deterministic A."""
from __future__ import annotations

import hashlib
import json
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
# RationalWeight / EvidenceReference live in `evidence.py` (pure, no world
# imports) and are re-exported here so every existing import keeps working.
from .evidence import EvidenceReference, RationalWeight  # noqa: F401
from .impact_scope import actual_rule_classes, enabled_rule_scope
from .provenance import verify_trace
from .trace_view_broker import ApprovedChangeView


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorldHypothesis:
    hypothesis_id: str
    statement: str
    prediction_kind: str
    predicted_observables: Mapping[str, Any]
    applicability_conditions: tuple[str, ...]
    evidence: tuple[EvidenceReference, ...]
    weight: RationalWeight | None = None

    def canonical(self) -> dict[str, object]:
        result = {"applicability_conditions": list(self.applicability_conditions),
                  "evidence": [x.canonical() for x in self.evidence],
                  "hypothesis_id": self.hypothesis_id,
                  "predicted_observables": dict(self.predicted_observables),
                  "prediction_kind": self.prediction_kind, "statement": self.statement}
        if self.weight is not None: result["weight"] = self.weight.canonical()
        return result


@dataclass(frozen=True)
class DistinguishingObservation:
    observation_id: str
    description: str
    required_view: str
    resolves_hypothesis_ids: tuple[str, ...]
    compute_cost_units: int
    intervention_required: bool

    def canonical(self) -> dict[str, object]:
        return {"compute_cost_units": self.compute_cost_units, "description": self.description,
                "intervention_required": self.intervention_required,
                "observation_id": self.observation_id, "required_view": self.required_view,
                "resolves_hypothesis_ids": list(self.resolves_hypothesis_ids)}


@dataclass(frozen=True)
class HypothesisSet:
    subject_digest: str
    source_tick: int
    target_tick: int
    combination_policy: str
    hypotheses: tuple[WorldHypothesis, ...]
    distinguishing_observations: tuple[DistinguishingObservation, ...]

    def __post_init__(self) -> None:
        if self.combination_policy not in ("nonexclusive", "exclusive"):
            raise ValueError("unsupported hypothesis combination policy")
        ids = [item.hypothesis_id for item in self.hypotheses]
        if not ids or len(set(ids)) != len(ids): raise ValueError("hypothesis ids must be unique and non-empty")
        known = set(ids)
        for observation in self.distinguishing_observations:
            if not set(observation.resolves_hypothesis_ids) <= known:
                raise ValueError("distinguishing observation refers to unknown hypothesis")

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"combination_policy": self.combination_policy,
                "distinguishing_observations": [x.canonical() for x in self.distinguishing_observations],
                "format": "hypothesis-set-v1", "hypotheses": [x.canonical() for x in self.hypotheses],
                "source_tick": self.source_tick, "subject_digest": self.subject_digest,
                "target_tick": self.target_tick}


@dataclass(frozen=True)
class HypothesisVerdict:
    hypothesis_id: str
    verdict: str
    evidence_digest: str
    reason: str

    def __post_init__(self) -> None:
        if self.verdict not in ("supported", "refuted", "underdetermined"):
            raise ValueError("unsupported hypothesis verdict")

    def canonical(self) -> dict[str, str]:
        return {"evidence_digest": self.evidence_digest, "hypothesis_id": self.hypothesis_id,
                "reason": self.reason, "verdict": self.verdict}


@dataclass(frozen=True)
class HypothesisResolution:
    hypothesis_set_digest: str
    actual_rule_classes: tuple[str, ...]
    verdicts: tuple[HypothesisVerdict, ...]
    uncovered_actual_rules: tuple[str, ...]

    @property
    def coverage_success(self) -> bool: return not self.uncovered_actual_rules

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"actual_rule_classes": list(self.actual_rule_classes),
                "coverage_success": self.coverage_success, "format": "hypothesis-resolution-v1",
                "hypothesis_set_digest": self.hypothesis_set_digest,
                "uncovered_actual_rules": list(self.uncovered_actual_rules),
                "verdicts": [x.canonical() for x in self.verdicts]}


def make_hypothesis_challenge(view: ApprovedChangeView,
                              spec: EnvironmentWorldSpec) -> ObservationContract:
    return ObservationContract(
        f"hypotheses:{view.digest[:20]}:{view.target_tick + 1}", "propose_next_rule_hypotheses",
        (("approved_change_view", view.digest), ("spec", spec.digest)),
        ("approved_change_view", "sealed_rule_parameters"),
        ("raw_vault_path", "actual_target_tick_delta", "A_records_after_source_tick", "other_adapter_answers"),
        1, max(1, len(enabled_rule_scope(spec)) * 16), view.width * view.height * 8,
        ("all currently enabled rule explanations remain available before observation",
         "numerical weights require explicit evidence", "next observation can support, refute, or leave hypotheses open"),
        {"source_tick": view.target_tick, "target_tick": view.target_tick + 1},
    )


class HypothesisSetAdapter:
    def __init__(self) -> None:
        self._manifest = CapabilityManifest(
            "rule-hypothesis-set", "nonexclusive-epistemic-hypotheses", "1",
            ("propose_rule_hypotheses", "preserve_unknown", "propose_distinguishing_observation"),
            ("approved_change_view", "sealed_rule_parameters"),
            "private set of nonexclusive rule and missing-variable hypotheses", True,
        )

    @property
    def manifest(self) -> CapabilityManifest: return self._manifest

    def respond(self, challenge: ObservationContract, view: ApprovedChangeView,
                spec: EnvironmentWorldSpec) -> tuple[ClaimSet, HypothesisSet]:
        if challenge.task_kind != "propose_next_rule_hypotheses": raise ValueError("unsupported hypothesis task")
        if challenge.visible_digest("approved_change_view") != view.digest: raise ValueError("challenge view differs")
        candidates = []
        source = EvidenceReference("enabled-rules", "leaves_open", spec.digest,
                                   "sealed rule exists but target tick outcome is hidden")
        for rule in enabled_rule_scope(spec):
            candidates.append(WorldHypothesis(
                f"rule-{rule}", f"{rule} will contribute a physical change in target tick",
                "target_rule_active", {"rule_class": rule, "target_tick": view.target_tick + 1},
                ("rule is enabled in the sealed specification",), (source,), None,
            ))
        candidates.append(WorldHypothesis(
            "no-physical-change", "no enabled rule will produce a physical state change in target tick",
            "no_physical_change", {"actual_rule_classes": [], "target_tick": view.target_tick + 1},
            ("enabled rules may all fail their local conditions",), (source,), None,
        ))
        candidates.append(WorldHypothesis(
            "missing-variable-needed", "repeated unexplained residuals may require a state variable absent from the current theory",
            "structural_unknown", {},
            ("one target tick cannot establish a missing variable", "requires repeated held-out residual pattern"),
            (EvidenceReference("single-tick-limit", "leaves_open", view.digest,
                               "one hidden next tick cannot distinguish structural insufficiency"),), None,
        ))
        rule_ids = tuple(item.hypothesis_id for item in candidates if item.prediction_kind != "structural_unknown")
        observations = (
            DistinguishingObservation("observe-target-stage-deltas",
                                      "reveal only target-tick rule classes after every hypothesis is sealed",
                                      "trusted_private_trace_evaluation", rule_ids, 1, False),
            DistinguishingObservation("collect-repeated-residuals",
                                      "collect the same unexplained residual across multiple sealed worlds before adding variables",
                                      "held_out_residual_archive", ("missing-variable-needed",), 4, False),
        )
        hypothesis_set = HypothesisSet(view.digest, view.target_tick, view.target_tick + 1,
                                       "nonexclusive", tuple(candidates), observations)
        claims = []; bridges = []
        for hypothesis in hypothesis_set.hypotheses:
            confidence = "hypothesis" if hypothesis.prediction_kind == "structural_unknown" else "approximate"
            claims.append(Claim(hypothesis.hypothesis_id, "world_hypothesis", confidence,
                                view.digest, {"hypothesis": hypothesis.canonical()}))
            if confidence == "approximate":
                bridges.append(EvidenceBridge(
                    hypothesis.hypothesis_id, "compare_hidden_target_rule_classes",
                    (view.source_chain_hash, view.source_records_sha256),
                    {"target_tick": hypothesis_set.target_tick},
                    ("target rule observation contradicts this hypothesis",),
                ))
        attachment = AttachmentDescriptor("hypothesis_set", hypothesis_set.digest,
                                          "hypothesis-set-v1", "hypothesis-set-decoder-v1")
        return ClaimSet(challenge.digest, self.manifest.digest, tuple(claims), tuple(bridges), (attachment,)), hypothesis_set


def evaluate_hypothesis_set(challenge: ObservationContract, claim_set: ClaimSet,
                            hypothesis_set: HypothesisSet, run_dir: Path,
                            spec: EnvironmentWorldSpec) -> tuple[BoundaryEvaluation, HypothesisResolution]:
    verification = verify_trace(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["spec_digest"] != spec.digest: raise ValueError("trace and specification differ")
    if claim_set.challenge_digest != challenge.digest: raise ValueError("claim set belongs to another challenge")
    if {item.claim_id for item in claim_set.claims} != {item.hypothesis_id for item in hypothesis_set.hypotheses}:
        raise ValueError("claim set and hypothesis set ids differ")
    records = [json.loads(line) for line in (run_dir / manifest["records_file"]).read_text(encoding="utf-8").splitlines()]
    actual = tuple(sorted(actual_rule_classes(records, hypothesis_set.target_tick)))
    verdicts = []; covered = set(); evidence_digest = verification["final_chain_hash"]
    for hypothesis in hypothesis_set.hypotheses:
        if hypothesis.prediction_kind == "target_rule_active":
            rule = str(hypothesis.predicted_observables["rule_class"])
            if rule in actual:
                verdicts.append(HypothesisVerdict(hypothesis.hypothesis_id, "supported", evidence_digest,
                                                  "target tick contains the predicted active rule class"))
                covered.add(rule)
            else:
                verdicts.append(HypothesisVerdict(hypothesis.hypothesis_id, "refuted", evidence_digest,
                                                  "target tick does not contain the predicted active rule class"))
        elif hypothesis.prediction_kind == "no_physical_change":
            verdict = "supported" if not actual else "refuted"
            reason = "target tick has no physical rule class" if not actual else "target tick contains physical change"
            verdicts.append(HypothesisVerdict(hypothesis.hypothesis_id, verdict, evidence_digest, reason))
        else:
            verdicts.append(HypothesisVerdict(hypothesis.hypothesis_id, "underdetermined", view_digest(hypothesis_set),
                                              "one observed tick cannot establish or refute a missing variable"))
    resolution = HypothesisResolution(hypothesis_set.digest, actual, tuple(verdicts),
                                      tuple(sorted(set(actual) - covered)))
    supported = tuple(item.hypothesis_id for item in verdicts if item.verdict == "supported")
    refuted = tuple(item.hypothesis_id for item in verdicts if item.verdict == "refuted")
    unknown = tuple(item.hypothesis_id for item in verdicts if item.verdict == "underdetermined")
    findings = ({"coverage_success": resolution.coverage_success, "resolution_digest": resolution.digest,
                 "supported_count": len(supported), "refuted_count": len(refuted),
                 "underdetermined_count": len(unknown)},)
    boundary = BoundaryEvaluation(challenge.digest, claim_set.digest, evidence_digest,
                                  supported, refuted, unknown, findings)
    return boundary, resolution


def view_digest(hypothesis_set: HypothesisSet) -> str:
    return hypothesis_set.subject_digest
