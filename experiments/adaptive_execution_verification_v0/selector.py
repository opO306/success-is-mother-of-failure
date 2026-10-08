"""Pure offline recommendations from the request-start VERIFIED snapshot only."""
from __future__ import annotations

import json

LEGACY = "LEGACY_V1_PROFILE"


def recommend(scope, goal, snapshot, *, eligible_backends):
    if goal not in ("CPU_MIN", "WALL_MIN"):
        raise ValueError("UNSUPPORTED_GOAL")
    fallback = {"profile": LEGACY, "decision": "USE_LEGACY", "mode": "OFFLINE_SHADOW_ONLY"}
    if snapshot.profile_bytes is None:
        return dict(fallback, reason="PROFILE_DISABLED")
    profile = json.loads(snapshot.profile_bytes)
    if profile.get("state") != "VERIFIED" or profile.get("mode") != "OFFLINE_SHADOW_ONLY":
        return dict(fallback, reason="UNVERIFIED_PROFILE")
    candidates = []
    for row in profile["rows"]:
        if row["scope"] != scope or row["backend"] not in eligible_backends:
            continue
        wall = sorted(item["wall_ns"] for item in row["observations"])
        cpu = sorted(item["cpu_ns"] for item in row["observations"])
        if len(wall) != 5 or len(cpu) != 5 or min(wall + cpu) <= 0:
            return dict(fallback, reason="INVALID_VERIFIED_ROW")
        candidates.append((wall[2], cpu[2], row["worker_count"], row["backend"], row["placement_id"]))
    if not candidates or not any(item[3] == "CPU_SERIAL" for item in candidates):
        return dict(fallback, reason="NO_EXACT_SCOPE_OR_BASELINE")
    if goal == "WALL_MIN":
        minimum = min(item[0] for item in candidates)
        tied = [item for item in candidates if item[0] * 100 <= minimum * 105]
        winner = min(tied, key=lambda item: (item[1], item[2], item[3], item[4]))
    else:
        winner = min(candidates, key=lambda item: (item[1], item[0], item[2], item[3], item[4]))
    return {"profile": snapshot.version, "decision": "RECOMMEND", "backend": winner[3],
            "placement_id": winner[4], "goal": goal, "wall_median_ns": winner[0], "cpu_median_ns": winner[1],
            "mode": "OFFLINE_SHADOW_ONLY", "receipt_sha256": profile["receipt_sha256"]}
