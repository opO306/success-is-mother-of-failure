"""Rules authority: pinned receipts, immutable profiles, append-only activation.

Pins must come from a separately reviewed verification output. Passing a digest
computed from an untrusted caller's receipt is not authorization (V0 OS isolation absent).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .common import canonical, digest, exclusive_json, read

LEGACY = "LEGACY_V1_PROFILE"


def admit(candidate, receipt, *, trusted_receipt_sha256, trusted_verifier_sha256,
          trusted_protocol_sha256, trusted_manifest_sha256):
    if digest(receipt) != trusted_receipt_sha256:
        raise ValueError("UNTRUSTED_RECEIPT")
    pins = {"verifier_sha256": trusted_verifier_sha256, "protocol_sha256": trusted_protocol_sha256,
            "manifest_sha256": trusted_manifest_sha256}
    if any(not pin or receipt.get(field) != pin for field, pin in pins.items()):
        raise ValueError("TRUSTED_IDENTITY_MISMATCH")
    if receipt.get("schema") != "aev0-cost-receipt" or receipt.get("verdict") != "VERIFIED" or receipt.get("errors"):
        raise ValueError("VERIFICATION_NOT_PASSED")
    if candidate.get("state") != "CANDIDATE" or receipt.get("candidate_sha256") != digest(candidate):
        raise ValueError("CANDIDATE_BINDING_MISMATCH")
    if receipt.get("scope") != "HISTORICAL_SESSION_EXECUTION_COST_ONLY" or receipt.get("rows") != candidate.get("rows"):
        raise ValueError("VERIFIED_SCOPE_MISMATCH")
    if receipt.get("formula_independence") != "UNRESOLVED_SHARED_RWFORCE":
        raise ValueError("INDEPENDENCE_OVERCLAIM")
    profile = {"schema": "aev0-profile", "state": "VERIFIED", "mode": "OFFLINE_SHADOW_ONLY",
               "session": candidate["session"], "rows": receipt["rows"],
               "receipt_sha256": trusted_receipt_sha256, "formula_independence": receipt["formula_independence"]}
    # Detach all nested lists from candidate/receipt ownership.
    return json.loads(canonical(profile))


@dataclass(frozen=True)
class RequestSnapshot:
    version: str
    profile_bytes: bytes | None


class Registry:
    """Local file journal prototype. Single writer; exclusive creation rejects races."""

    def __init__(self, directory):
        self.directory = Path(directory)

    def events(self):
        chain, previous = [], None
        for index, path in enumerate(sorted(self.directory.glob("event_*.json"))):
            record = read(path)
            claimed = record.pop("event_sha256")
            if record["sequence"] != index or record["previous"] != previous or digest(record) != claimed:
                raise ValueError("ACTIVATION_CHAIN_INVALID")
            record["event_sha256"] = claimed
            chain.append(record)
            previous = claimed
        return chain

    def activate(self, profile=None, *, reason, trusted_profile_sha256=None):
        if not reason:
            raise ValueError("REASON_REQUIRED")
        if profile is not None and (profile.get("state") != "VERIFIED" or profile.get("mode") != "OFFLINE_SHADOW_ONLY"):
            raise ValueError("CANDIDATE_CANNOT_ACTIVATE")
        if profile is not None and digest(profile) != trusted_profile_sha256:
            raise ValueError("UNTRUSTED_PROFILE")
        if profile is None:
            version = LEGACY
        else:
            version = digest(profile)
            target = self.directory / "profiles" / f"{version}.json"
            if target.exists():
                if digest(read(target)) != version:
                    raise ValueError("PROFILE_STORE_CORRUPTED")
            else:
                exclusive_json(target, profile)
        prior = self.events()
        event = {"sequence": len(prior), "previous": prior[-1]["event_sha256"] if prior else None,
                 "profile": version, "reason": reason, "authority": "RULE_MANAGER", "mode": "OFFLINE_SHADOW_ONLY"}
        event["event_sha256"] = digest(event)
        exclusive_json(self.directory / f"event_{len(prior):06d}.json", event)
        return event

    def begin_request(self):
        events = self.events()
        version = events[-1]["profile"] if events else LEGACY
        if version == LEGACY:
            return RequestSnapshot(version, None)
        profile = read(self.directory / "profiles" / f"{version}.json")
        if digest(profile) != version:
            raise ValueError("PROFILE_STORE_CORRUPTED")
        return RequestSnapshot(version, canonical(profile))
