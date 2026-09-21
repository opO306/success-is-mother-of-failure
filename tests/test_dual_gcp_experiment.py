import hashlib
import json
from pathlib import Path

from prepare_dual_gcp_manifest import build_dual_manifest
from prepare_experiment_manifest import build_manifest
from run_observer_cohort import run_cohort


def test_dual_manifest_precommits_disjoint_breadth_and_depth_cohorts() -> None:
    root = Path(__file__).resolve().parents[1]

    manifest = build_dual_manifest(root)

    breadth, depth = manifest["cohorts"]
    assert manifest["total_world_count"] == 76
    assert breadth["world_count"] == len(breadth["seeds"]) == 64
    assert breadth["duration_seconds"] == 6 * 60 * 60
    assert breadth["machine_type"] == "n2-custom-80-65536"
    assert depth["world_count"] == len(depth["seeds"]) == 12
    assert depth["duration_seconds"] == 32 * 60 * 60
    assert depth["machine_type"] == "n2-custom-12-21504"
    all_seeds = [*breadth["seeds"], *depth["seeds"]]
    assert len(all_seeds) == len(set(all_seeds)) == 76
    expected = hashlib.sha256(json.dumps(all_seeds, separators=(",", ":")).encode("ascii")).hexdigest()
    assert manifest["seed_digest"] == expected
    assert breadth["code_digest"] == depth["code_digest"] == manifest["code_digest"]


def test_cohort_runner_completes_and_hashes_a_short_world(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(root, count=1, duration_seconds=1)
    manifest["cohort"] = "test"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = run_cohort(manifest_path, tmp_path / "output")

    assert summary["complete"] is True
    world = summary["worlds"][0]
    assert world["return_code"] == 0
    assert world["integrity_violations"] == 0
    assert world["stdout_bytes"] == world["stderr_bytes"] == 0
    assert (tmp_path / "output" / "sha256.json").exists()
    assert (tmp_path / "output" / "batch_summary.json").exists()
