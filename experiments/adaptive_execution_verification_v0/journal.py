"""Append-only experience transitions; refusals stay CANDIDATE and retain receipts."""
from pathlib import Path

from .common import digest, exclusive_json, read


class ExperienceJournal:
    def __init__(self, directory):
        self.directory = Path(directory)

    def history(self):
        entries, previous = [], None
        for number, path in enumerate(sorted(self.directory.glob("experience_*.json"))):
            event = read(path)
            claimed = event.pop("sha256")
            if event["index"] != number or event["previous"] != previous or digest(event) != claimed:
                raise ValueError("EXPERIENCE_CHAIN_INVALID")
            event["sha256"] = claimed
            entries.append(event)
            previous = claimed
        return entries

    def _append(self, state, payload, authority):
        events = self.history()
        event = {"index": len(events), "previous": events[-1]["sha256"] if events else None,
                 "state": state, "payload": payload, "authority": authority}
        event["sha256"] = digest(event)
        exclusive_json(self.directory / f"experience_{len(events):06d}.json", event)
        return event

    def unknown(self, missing_fields):
        if self.history() or not missing_fields:
            raise ValueError("UNKNOWN_MUST_START_JOURNAL_WITH_MISSING_INFORMATION")
        return self._append("UNKNOWN", {"missing": list(missing_fields)}, "COLLECTOR")

    def candidate(self, candidate):
        prior = self.history()
        if not prior or prior[-1]["state"] != "UNKNOWN" or candidate.get("state") != "CANDIDATE":
            raise ValueError("INVALID_CANDIDATE_TRANSITION")
        return self._append("CANDIDATE", {"candidate_sha256": digest(candidate), "candidate": candidate}, "COLLECTOR")

    def receipt(self, receipt, *, trusted_receipt_sha256):
        prior = self.history()
        if not prior or prior[-1]["state"] != "CANDIDATE" or digest(receipt) != trusted_receipt_sha256:
            raise ValueError("INVALID_RECEIPT_TRANSITION")
        original = next(event for event in prior if "candidate_sha256" in event["payload"])
        if receipt["candidate_sha256"] != original["payload"]["candidate_sha256"]:
            raise ValueError("RECEIPT_CANDIDATE_MISMATCH")
        return self._append("CANDIDATE", {"verification_receipt": receipt, "receipt_sha256": trusted_receipt_sha256}, "VERIFIER_HANDOFF")

    def verified(self, profile, *, trusted_profile_sha256):
        prior = self.history()
        if not prior or prior[-1]["state"] != "CANDIDATE" or digest(profile) != trusted_profile_sha256:
            raise ValueError("INVALID_VERIFIED_TRANSITION")
        receipt = prior[-1]["payload"].get("verification_receipt", {})
        if receipt.get("verdict") != "VERIFIED" or receipt.get("errors") or profile.get("state") != "VERIFIED":
            raise ValueError("VERIFIED_REQUIRES_PASSED_RECEIPT_AND_MANAGER_ADMISSION")
        if profile.get("receipt_sha256") != prior[-1]["payload"]["receipt_sha256"]:
            raise ValueError("PROFILE_RECEIPT_MISMATCH")
        return self._append("VERIFIED", {"profile_sha256": trusted_profile_sha256}, "RULE_MANAGER")
