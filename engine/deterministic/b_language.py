"""Model-neutral B-Language boundary contract.

Only observable inputs, claims, evidence bridges, and evaluations are shared.
An adapter's internal representation and reasoning path remain private and are
never required to match an oracle or another adapter.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

FORMAT = "b-language-boundary-v1"
CONFIDENCE_CLASSES = frozenset({"exact", "measured", "author_reported", "approximate", "hypothesis", "unknown"})
TESTABLE_CONFIDENCE = frozenset({"exact", "measured", "approximate"})


def _json_value(value: Any, context: str = "payload") -> None:
    if value is None or isinstance(value, (str, int, bool)): return
    if isinstance(value, float): raise ValueError(f"{context} cannot contain floating point")
    if isinstance(value, list) or isinstance(value, tuple):
        for index, item in enumerate(value): _json_value(item, f"{context}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str): raise ValueError(f"{context} keys must be text")
            _json_value(item, f"{context}.{key}")
        return
    raise ValueError(f"{context} contains unsupported value type {type(value).__name__}")


def _text(value: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{context} must be non-empty text")
    return value


def _texts(values: tuple[str, ...], context: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple): raise ValueError(f"{context} must be a tuple")
    result = tuple(_text(value, context) for value in values)
    if not allow_empty and not result: raise ValueError(f"{context} cannot be empty")
    if len(set(result)) != len(result): raise ValueError(f"{context} values must be unique")
    return result


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityManifest:
    adapter_id: str
    adapter_kind: str
    adapter_version: str
    capabilities: tuple[str, ...]
    accepted_observation_views: tuple[str, ...]
    internal_representation: str
    deterministic: bool

    def __post_init__(self) -> None:
        _text(self.adapter_id, "adapter_id"); _text(self.adapter_kind, "adapter_kind")
        _text(self.adapter_version, "adapter_version"); _texts(self.capabilities, "capabilities")
        _texts(self.accepted_observation_views, "accepted_observation_views")
        _text(self.internal_representation, "internal_representation")
        if not isinstance(self.deterministic, bool): raise ValueError("deterministic must be boolean")

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"accepted_observation_views": list(self.accepted_observation_views),
                "adapter_id": self.adapter_id, "adapter_kind": self.adapter_kind,
                "adapter_version": self.adapter_version, "capabilities": list(self.capabilities),
                "deterministic": self.deterministic, "format": FORMAT,
                "internal_representation": self.internal_representation,
                "message_type": "capability_manifest"}


@dataclass(frozen=True)
class ObservationContract:
    challenge_id: str
    task_kind: str
    visible_digests: tuple[tuple[str, str], ...]
    allowed_views: tuple[str, ...]
    hidden_fields: tuple[str, ...]
    max_ticks: int
    max_compute_units: int
    max_memory_bytes: int
    success_conditions: tuple[str, ...]
    task_payload: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        _text(self.challenge_id, "challenge_id"); _text(self.task_kind, "task_kind")
        if not isinstance(self.visible_digests, tuple) or not self.visible_digests:
            raise ValueError("visible_digests must be a non-empty tuple")
        names = []
        for name, digest in self.visible_digests:
            names.append(_text(name, "visible digest name")); _text(digest, "visible digest")
        if len(set(names)) != len(names): raise ValueError("visible digest names must be unique")
        _texts(self.allowed_views, "allowed_views"); _texts(self.hidden_fields, "hidden_fields", allow_empty=True)
        _texts(self.success_conditions, "success_conditions")
        if self.task_payload is not None:
            if not isinstance(self.task_payload, Mapping): raise ValueError("task_payload must be an object")
            _json_value(self.task_payload, "task_payload")
        for name in ("max_ticks", "max_compute_units", "max_memory_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def visible_digest(self, name: str) -> str | None:
        return dict(self.visible_digests).get(name)

    def canonical(self) -> dict[str, object]:
        result = {"allowed_views": list(self.allowed_views), "challenge_id": self.challenge_id,
                  "format": FORMAT, "hidden_fields": list(self.hidden_fields),
                  "limits": {"max_compute_units": self.max_compute_units,
                             "max_memory_bytes": self.max_memory_bytes, "max_ticks": self.max_ticks},
                  "message_type": "observation_contract", "success_conditions": list(self.success_conditions),
                  "task_kind": self.task_kind,
                  "visible_digests": {name: digest for name, digest in self.visible_digests}}
        if self.task_payload is not None:
            result["task_payload"] = dict(self.task_payload)
        return result


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_kind: str
    confidence_class: str
    subject_digest: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        _text(self.claim_id, "claim_id"); _text(self.claim_kind, "claim_kind")
        _text(self.subject_digest, "subject_digest")
        if self.confidence_class not in CONFIDENCE_CLASSES: raise ValueError("unsupported confidence_class")
        if not isinstance(self.payload, Mapping): raise ValueError("claim payload must be an object")
        _json_value(self.payload, "claim.payload")

    def canonical(self) -> dict[str, object]:
        return {"claim_id": self.claim_id, "claim_kind": self.claim_kind,
                "confidence_class": self.confidence_class, "payload": dict(self.payload),
                "subject_digest": self.subject_digest}


@dataclass(frozen=True)
class EvidenceBridge:
    claim_id: str
    test_kind: str
    test_input_digests: tuple[str, ...]
    expected_observables: Mapping[str, Any]
    falsification_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.claim_id, "claim_id"); _text(self.test_kind, "test_kind")
        _texts(self.test_input_digests, "test_input_digests")
        if not isinstance(self.expected_observables, Mapping): raise ValueError("expected_observables must be an object")
        _json_value(self.expected_observables, "expected_observables")
        _texts(self.falsification_conditions, "falsification_conditions")

    def canonical(self) -> dict[str, object]:
        return {"claim_id": self.claim_id, "expected_observables": dict(self.expected_observables),
                "falsification_conditions": list(self.falsification_conditions),
                "test_input_digests": list(self.test_input_digests), "test_kind": self.test_kind}


@dataclass(frozen=True)
class AttachmentDescriptor:
    attachment_kind: str
    content_digest: str
    producer_format: str
    decoder_id: str | None = None

    def __post_init__(self) -> None:
        _text(self.attachment_kind, "attachment_kind"); _text(self.content_digest, "content_digest")
        _text(self.producer_format, "producer_format")
        if self.decoder_id is not None: _text(self.decoder_id, "decoder_id")

    def canonical(self) -> dict[str, object]:
        result = {"attachment_kind": self.attachment_kind, "content_digest": self.content_digest,
                  "producer_format": self.producer_format}
        if self.decoder_id is not None: result["decoder_id"] = self.decoder_id
        return result


@dataclass(frozen=True)
class ClaimSet:
    challenge_digest: str
    manifest_digest: str
    claims: tuple[Claim, ...]
    evidence_bridges: tuple[EvidenceBridge, ...]
    attachments: tuple[AttachmentDescriptor, ...] = ()

    def __post_init__(self) -> None:
        _text(self.challenge_digest, "challenge_digest"); _text(self.manifest_digest, "manifest_digest")
        if not isinstance(self.claims, tuple): raise ValueError("claims must be a tuple")
        if not isinstance(self.evidence_bridges, tuple): raise ValueError("evidence_bridges must be a tuple")
        if not isinstance(self.attachments, tuple): raise ValueError("attachments must be a tuple")
        claim_ids = [item.claim_id for item in self.claims]
        if len(set(claim_ids)) != len(claim_ids): raise ValueError("claim ids must be unique")
        bridges = {item.claim_id for item in self.evidence_bridges}
        if not bridges <= set(claim_ids): raise ValueError("evidence bridge refers to an unknown claim")
        for claim in self.claims:
            if claim.confidence_class in TESTABLE_CONFIDENCE and claim.claim_id not in bridges:
                raise ValueError(f"testable claim {claim.claim_id} needs an evidence bridge")

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"attachments": [x.canonical() for x in self.attachments],
                "challenge_digest": self.challenge_digest, "claims": [x.canonical() for x in self.claims],
                "evidence_bridges": [x.canonical() for x in self.evidence_bridges], "format": FORMAT,
                "manifest_digest": self.manifest_digest, "message_type": "claim_set"}


@dataclass(frozen=True)
class BoundaryEvaluation:
    challenge_digest: str
    claim_set_digest: str
    oracle_digest: str
    verified_claim_ids: tuple[str, ...]
    falsified_claim_ids: tuple[str, ...]
    untested_claim_ids: tuple[str, ...]
    findings: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        _text(self.challenge_digest, "challenge_digest"); _text(self.claim_set_digest, "claim_set_digest")
        _text(self.oracle_digest, "oracle_digest")
        verified = set(_texts(self.verified_claim_ids, "verified_claim_ids", allow_empty=True))
        falsified = set(_texts(self.falsified_claim_ids, "falsified_claim_ids", allow_empty=True))
        untested = set(_texts(self.untested_claim_ids, "untested_claim_ids", allow_empty=True))
        if verified & falsified or verified & untested or falsified & untested:
            raise ValueError("evaluation claim groups must be disjoint")
        for finding in self.findings: _json_value(finding, "evaluation.finding")

    @property
    def complete_match(self) -> bool:
        return not self.falsified_claim_ids and not self.untested_claim_ids

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"challenge_digest": self.challenge_digest, "claim_set_digest": self.claim_set_digest,
                "complete_match": self.complete_match, "falsified_claim_ids": list(self.falsified_claim_ids),
                "findings": [dict(x) for x in self.findings], "format": FORMAT,
                "message_type": "boundary_evaluation", "oracle_digest": self.oracle_digest,
                "untested_claim_ids": list(self.untested_claim_ids),
                "verified_claim_ids": list(self.verified_claim_ids)}
