import hashlib
import json
from pathlib import Path

from prepare_experiment_manifest import build_manifest


def test_manifest_precommits_unique_os_seeds_code_and_protocol() -> None:
    root = Path(__file__).resolve().parents[1]

    manifest = build_manifest(root, count=4, duration_seconds=900)

    seeds = manifest["seeds"]
    assert len(seeds) == len(set(seeds)) == 4
    assert all(isinstance(seed, int) and 0 <= seed < 2**63 for seed in seeds)
    expected_seed_digest = hashlib.sha256(
        json.dumps(seeds, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    assert manifest["seed_digest"] == expected_seed_digest
    assert manifest["duration_seconds"] == 900
    assert manifest["protocol"] == {
        "include_every_world": True,
        "restart_failed_worlds": False,
        "select_seeds_after_results": False,
    }
    assert "engine/sequence/observation.py" in manifest["code_sha256"]
    assert "run_nonliving_face_until.py" in manifest["code_sha256"]
    assert len(manifest["code_digest"]) == 64
