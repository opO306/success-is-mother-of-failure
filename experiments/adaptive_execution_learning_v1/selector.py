"""Offline next-request recommendation only; never imports or changes V1 execution."""
import json
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .collector import eligible
from .core import canonical, digest


def choose(scope, snapshot, eligible_methods):
    fallback = {"method": "LEGACY_V1", "goal": snapshot.goal, "version": snapshot.version, "mode": "OFFLINE_TEST_ONLY"}
    if snapshot.profile_bytes is None:
        return fallback
    profile = json.loads(snapshot.profile_bytes)
    if (profile.get("state") != "VERIFIED" or profile.get("mode") != "TEST_ONLY" or profile.get("scope") != scope):
        return fallback
    try:
        approval = json.loads(snapshot.approval_bytes)
        receipt = profile["receipt"]
        for key, prefix, envelope in [(snapshot.inspector_public_hex, b"AEL1_RECEIPT\0", receipt),
                                      (snapshot.manager_public_hex, b"AEL1_ACTIVATION\0", approval)]:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(envelope["signature"]), prefix + canonical(envelope["body"]))
        body = {key: val for key, val in profile.items() if key != "id"}
        if (digest(body) != profile["id"] or approval["body"]["profile_id"] != profile["id"]
                or approval["body"]["goal"] != snapshot.goal or approval["body"]["mode"] != "TEST_ONLY"
                or receipt["body"]["verdict"] != "VERIFIED" or receipt["body"]["scope"] != "SYNTHETIC_TEST_ONLY"
                or receipt["body"]["candidate_sha256"] != digest(profile["candidate"])
                or profile["rows"] != receipt["body"]["rows"] or profile["scope"] != receipt["body"]["session_scope"]):
            raise ValueError("SNAPSHOT_INTEGRITY")
    except (ValueError, KeyError, TypeError, InvalidSignature) as error:
        raise ValueError("SNAPSHOT_INTEGRITY") from error
    rows = []
    for row in profile["rows"]:
        if row["method"] not in eligible_methods or not eligible(scope, row["method"]):
            continue
        observations = row["observations"]
        if len(observations) != 5:
            return fallback
        wall = sorted(obj["wall_ns"] for obj in observations)[2]
        cpu = sorted(obj["cpu_ns"] for obj in observations)[2]
        rows.append((row["method"], wall, cpu, 6 if row["method"] == "CPU_PARALLEL/W6" else 0))
    if not any(row[0] == "CPU_SERIAL" for row in rows):
        return fallback
    if snapshot.goal == "WALL_MIN":
        best_wall = min(row[1] for row in rows)
        choices = [row for row in rows if row[1] * 100 <= best_wall * 105]
        selected = min(choices, key=lambda row: (row[2], row[3], row[0]))
    elif snapshot.goal == "CPU_MIN":
        selected = min(rows, key=lambda row: (row[2], row[1], row[3], row[0]))
    else:
        return fallback
    return dict(fallback, method=selected[0], median_wall_ns=selected[1], median_cpu_ns=selected[2],
                knowledge_scope="SYNTHETIC_TEST_ONLY", correctness="UNCHANGED_HISTORICAL_SCOPE")
