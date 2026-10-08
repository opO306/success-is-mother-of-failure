"""Rule-manager store: fixed provisioned public roots, signed inspector and approvals."""
from __future__ import annotations
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .core import Ledger, canonical, check_frozen, digest, raw_hash, read, stop, stopped, write_new


@dataclass(frozen=True)
class TrustRoots:
    inspector_public_hex: str
    manager_public_hex: str
    protocol_sha256: str
    verifier_sha256: str
    mode: str = "TEST_ONLY"


@dataclass(frozen=True)
class Snapshot:
    version: str
    goal: str
    profile_bytes: bytes | None
    inspector_public_hex: str
    manager_public_hex: str
    approval_bytes: bytes | None


def _signature(public, prefix, envelope):
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(
            bytes.fromhex(envelope["signature"]), prefix + canonical(envelope["body"]))
    except (InvalidSignature, ValueError, KeyError, TypeError) as error:
        raise ValueError("INVALID_AUTHORITY_SIGNATURE") from error


def _serialized(function):
    @wraps(function)
    def call(self, *args, **kwargs):
        import fcntl
        with (self.directory / "manager_writer.lock").open("ab") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError("CONCURRENT_MANAGER_REFUSED") from error
            return function(self, *args, **kwargs)
    return call


class Registry:
    def __init__(self, directory, roots):
        if not isinstance(roots, TrustRoots) or roots.mode != "TEST_ONLY":
            raise ValueError("PRODUCTION_ROOTS_NOT_IMPLEMENTED")
        if roots.inspector_public_hex == roots.manager_public_hex:
            raise ValueError("AUTHORITIES_MUST_DIFFER")
        self.directory = Path(directory)
        self.roots = roots  # immutable provisioned config; no per-receipt key/pin arguments
        self.events = Ledger(self.directory / "activations")
        self.rejections = Ledger(self.directory / "rejections")
        (self.directory / "profiles").mkdir(parents=True, exist_ok=True)
        config = self.directory / "trust_roots.json"
        value = dict(roots.__dict__)
        if config.exists():
            if read(config) != value:
                raise ValueError("TRUST_ROOT_REPLACEMENT_REFUSED")
        else:
            write_new(config, value)

    def _roots_intact(self):
        if read(self.directory / "trust_roots.json") != self.roots.__dict__:
            raise ValueError("TRUST_ROOT_INTEGRITY")

    def _reject(self, operation, evidence, error):
        self.rejections.append({"operation": operation, "verdict": "REFUSED", "error": str(error), "evidence": evidence})

    def _receipt(self, candidate, receipt):
        self._roots_intact()
        _signature(self.roots.inspector_public_hex, b"AEL1_RECEIPT\0", receipt)
        body = receipt["body"]
        if (body.get("schema") != "ael1-cost-receipt" or body.get("mode") != "TEST_ONLY"
                or body.get("verdict") != "VERIFIED" or body.get("errors") or body.get("stop_required")
                or body.get("scope") != "SYNTHETIC_TEST_ONLY"
                or body.get("formula_independence") != "UNRESOLVED_SHARED_RWFORCE"
                or body.get("verifier_sha256") != self.roots.verifier_sha256
                or body.get("protocol_sha256") != self.roots.protocol_sha256
                or body.get("candidate_sha256") != digest(candidate)
                or body.get("session_scope") != candidate.get("scope") or body.get("rows") != candidate.get("rows")
                or candidate.get("state") != "CANDIDATE" or candidate.get("measurement_kind") != "SYNTHETIC_TEST_ONLY"):
            raise ValueError("INSPECTOR_ADMISSION_REFUSED")

    @_serialized
    def admit(self, candidate, receipt):
        if stopped(self.directory):
            raise ValueError("STOP_MANAGER")
        try:
            check_frozen()
            self._receipt(candidate, receipt)
            # Sources must still match the signed manifest at manager handoff.
            for source in candidate["sources"]:
                if raw_hash(source["path"]) != source["sha256"]:
                    raise ValueError("SOURCE_INTEGRITY")
            profile = {"schema": "ael1-profile", "state": "VERIFIED", "mode": "TEST_ONLY",
                       "scope": candidate["scope"], "rows": candidate["rows"], "candidate_sha256": digest(candidate),
                       "receipt": receipt, "candidate": candidate}
            profile["id"] = digest(profile)
            path = self.directory / "profiles" / (profile["id"] + ".json")
            if path.exists():
                if path.read_bytes() != canonical(profile):
                    raise ValueError("PROFILE_INTEGRITY")
            else:
                write_new(path, profile)
            return read(path)
        except Exception as error:
            self._reject("ADMIT", {"candidate": candidate, "receipt": receipt}, error)
            if "INTEGRITY" in str(error): stop(self.directory, str(error), digest(candidate))
            raise ValueError(str(error)) from error

    def profiles(self):
        return [path.stem for path in (self.directory / "profiles").glob("*.json")]

    def _load(self, profile_id):
        if len(profile_id) != 64 or any(char not in "0123456789abcdef" for char in profile_id):
            raise ValueError("PROFILE_NOT_ADMITTED")
        path = self.directory / "profiles" / (profile_id + ".json")
        if not path.exists():
            raise ValueError("PROFILE_NOT_ADMITTED")
        raw = path.read_bytes()
        profile = read(path)
        body = {key: val for key, val in profile.items() if key != "id"}
        if profile.get("id") != profile_id or digest(body) != profile_id or raw != canonical(profile):
            raise ValueError("PROFILE_INTEGRITY")
        self._receipt(profile["candidate"], profile["receipt"])
        if (profile.get("schema") != "ael1-profile" or profile.get("state") != "VERIFIED" or profile.get("mode") != "TEST_ONLY"
                or profile["scope"] != profile["candidate"]["scope"] or profile["rows"] != profile["candidate"]["rows"]
                or profile["candidate_sha256"] != digest(profile["candidate"])):
            raise ValueError("PROFILE_INTEGRITY")
        for source in profile["candidate"]["sources"]:
            if raw_hash(source["path"]) != source["sha256"]:
                raise ValueError("SOURCE_INTEGRITY")
        return raw

    def owns(self, profile, candidate_sha256):
        try:
            return (profile["candidate_sha256"] == candidate_sha256
                    and self._load(profile["id"]) == canonical(profile))
        except (KeyError, ValueError):
            return False

    def version(self):
        events = self.events.history()
        return events[-1]["sha256"] if events else "GENESIS"

    @_serialized
    def activate(self, approval):
        if stopped(self.directory):
            raise ValueError("STOP_MANAGER")
        try:
            self._roots_intact()
            _signature(self.roots.manager_public_hex, b"AEL1_ACTIVATION\0", approval)
            body = approval["body"]
            if (body.get("schema") != "ael1-activation" or body.get("mode") != "TEST_ONLY"
                    or body.get("goal") not in ("WALL_MIN", "CPU_MIN") or not body.get("reason")
                    or not body.get("decision_id") or body.get("predecessor") != self.version()):
                raise ValueError("INVALID_MANAGER_APPROVAL")
            if any(event["payload"]["approval"]["body"]["decision_id"] == body["decision_id"] for event in self.events.history()):
                raise ValueError("REPLAYED_MANAGER_APPROVAL")
            if body["profile_id"] != "LEGACY":
                self._load(body["profile_id"])
            return self.events.append({"operation": "ACTIVATE", "approval": approval})
        except Exception as error:
            self._reject("ACTIVATE", approval, error)
            if "INTEGRITY" in str(error): stop(self.directory, str(error), approval)
            raise ValueError(str(error)) from error

    def rollback(self, approval):
        try:
            target = approval["body"]["profile_id"]
            previous = {event["payload"]["approval"]["body"]["profile_id"] for event in self.events.history()}
            if target != "LEGACY" and target not in previous:
                raise ValueError("ROLLBACK_TARGET_NOT_PREVIOUS")
            return self.activate(approval)
        except Exception as error:
            self._reject("ROLLBACK", approval, error)
            stop(self.directory, "ROLLBACK_FAILED", approval)
            raise ValueError(str(error)) from error

    @_serialized
    def begin_request(self, goal):
        if stopped(self.directory):
            raise ValueError("STOP_NEW_REQUEST")
        if goal not in ("WALL_MIN", "CPU_MIN"):
            raise ValueError("INVALID_GOAL")
        try:
            self._roots_intact()
            profile_id, approval_bytes = "LEGACY", None
            for event in self.events.history():
                _signature(self.roots.manager_public_hex, b"AEL1_ACTIVATION\0", event["payload"]["approval"])
                body = event["payload"]["approval"]["body"]
                if body["goal"] == goal:
                    profile_id = body["profile_id"]
                    approval_bytes = canonical(event["payload"]["approval"])
            return Snapshot(self.version(), goal, None if profile_id == "LEGACY" else self._load(profile_id),
                            self.roots.inspector_public_hex, self.roots.manager_public_hex, approval_bytes)
        except Exception as error:
            stop(self.directory, "REQUEST_INTEGRITY_FAILURE", str(error))
            raise ValueError(str(error)) from error
