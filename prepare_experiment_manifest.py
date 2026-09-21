"""Create an experiment manifest before any world process starts."""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


HASHED_PATHS = (
    "engine/sequence",
    "run_nonliving_face_until.py",
    "run_nonliving_world_probe.py",
    "run_observer_cohort.py",
    "prepare_experiment_manifest.py",
    "prepare_dual_gcp_manifest.py",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _code_hashes(root: Path) -> dict[str, str]:
    files: list[Path] = []
    for name in HASHED_PATHS:
        path = root / name
        files.extend(sorted(path.glob("*.py")) if path.is_dir() else (path,))
    return {
        path.relative_to(root).as_posix(): _sha256(path.read_bytes())
        for path in sorted(set(files))
    }


def build_manifest(root: Path, count: int, duration_seconds: int) -> dict[str, object]:
    if count <= 0 or duration_seconds <= 0:
        raise ValueError("count and duration_seconds must be positive")
    seeds: list[int] = []
    while len(seeds) < count:
        value = secrets.randbits(63)
        if value not in seeds:
            seeds.append(value)
    seed_bytes = json.dumps(seeds, separators=(",", ":")).encode("ascii")
    code_hashes = _code_hashes(root)
    code_bytes = json.dumps(code_hashes, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {
        "code_digest": _sha256(code_bytes),
        "code_sha256": code_hashes,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration_seconds,
        "observer_format": "nonliving-observer-v1",
        "protocol": {
            "include_every_world": True,
            "restart_failed_worlds": False,
            "select_seeds_after_results": False,
        },
        "seed_digest": _sha256(seed_bytes),
        "seed_source": "OS CSPRNG via Python secrets.randbits(63)",
        "seeds": seeds,
        "world_count": count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--duration-seconds", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; a precommit manifest cannot be replaced")
    root = Path(__file__).resolve().parent
    manifest = build_manifest(root, args.count, args.duration_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(f"seed_digest={manifest['seed_digest']}")
    print(f"code_digest={manifest['code_digest']}")


if __name__ == "__main__":
    main()
