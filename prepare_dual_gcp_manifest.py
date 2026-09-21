"""Precommit two GCP observer cohorts before either experiment starts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_experiment_manifest import _sha256, build_manifest


COHORTS = (
    {
        "cohort": "gcp1-breadth",
        "duration_seconds": 6 * 60 * 60,
        "instance": "instance-20260917-193145",
        "machine_type": "n2-custom-80-65536",
        "project": "project-55159e30-6b02-4339-b2f",
        "world_count": 64,
        "zone": "us-west1-b",
    },
    {
        "cohort": "gcp2-depth",
        "duration_seconds": 32 * 60 * 60,
        "instance": "instance-20260919-091113",
        "machine_type": "n2-custom-12-21504",
        "project": "project-a2e66968-df2f-43a4-a77",
        "world_count": 12,
        "zone": "us-central1-a",
    },
)


def build_dual_manifest(root: Path) -> dict[str, object]:
    total = sum(int(item["world_count"]) for item in COHORTS)
    common = build_manifest(root, total, max(int(item["duration_seconds"]) for item in COHORTS))
    seeds = list(common.pop("seeds"))
    cohorts = []
    offset = 0
    for definition in COHORTS:
        count = int(definition["world_count"])
        cohort_seeds = seeds[offset:offset + count]
        offset += count
        cohorts.append({
            **definition,
            "code_digest": common["code_digest"],
            "observer_format": common["observer_format"],
            "protocol": common["protocol"],
            "seed_digest": _sha256(json.dumps(cohort_seeds, separators=(",", ":")).encode("ascii")),
            "seed_source": common["seed_source"],
            "seeds": cohort_seeds,
        })
    return {
        **common,
        "cohorts": cohorts,
        "experiment": "dual-gcp-observer-v1",
        "seed_digest": _sha256(json.dumps(seeds, separators=(",", ":")).encode("ascii")),
        "total_world_count": total,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("output directory already exists; precommit data cannot be replaced")
    root = Path(__file__).resolve().parent
    manifest = build_dual_manifest(root)
    args.output_dir.mkdir(parents=True)
    master_path = args.output_dir / "master_precommit.json"
    master_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for cohort in manifest["cohorts"]:
        path = args.output_dir / f"{cohort['cohort']}_precommit.json"
        path.write_text(json.dumps(cohort, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(master_path.resolve())
    print(f"seed_digest={manifest['seed_digest']}")
    print(f"code_digest={manifest['code_digest']}")


if __name__ == "__main__":
    main()
