"""Run one precommitted observer cohort without restarting failed worlds."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prepare_experiment_manifest import _code_hashes, _sha256


def _write(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_code(root: Path, manifest: dict[str, object]) -> None:
    expected = manifest.get("code_digest")
    if not isinstance(expected, str):
        raise ValueError("cohort manifest needs code_digest")
    hashes = _code_hashes(root)
    actual = _sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("ascii"))
    if actual != expected:
        raise ValueError(f"code digest changed: expected {expected}, observed {actual}")


def run_cohort(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    root = Path(__file__).resolve().parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    _verify_code(root, manifest)
    seeds = manifest.get("seeds")
    duration = manifest.get("duration_seconds")
    if not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("cohort seeds must be a non-empty unique list")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        raise ValueError("duration_seconds must be positive")
    output_dir.mkdir(parents=True, exist_ok=False)
    deadline = datetime.now(timezone.utc) + timedelta(seconds=duration)
    processes: list[tuple[int, subprocess.Popen[bytes], object, object]] = []
    launched = []
    for raw_seed in seeds:
        seed = int(raw_seed)
        result = output_dir / f"result_seed{seed}.json"
        lineage = output_dir / f"lineage_seed{seed}.json"
        observer = output_dir / f"observer_seed{seed}.json"
        stdout_path = output_dir / f"stdout_seed{seed}.log"
        stderr_path = output_dir / f"stderr_seed{seed}.log"
        stdout = stdout_path.open("wb")
        stderr = stderr_path.open("wb")
        command = [
            sys.executable,
            str(root / "run_nonliving_face_until.py"),
            "--seed", str(seed),
            "--until", deadline.isoformat(),
            "--output", str(result),
            "--checkpoint-events", "10000",
            "--lineage-output", str(lineage),
            "--lineage-checkpoint-events", "10000",
            "--observer-output", str(observer),
            "--observer-checkpoint-events", "10000",
            "--observer-census-events", "10000",
            "--observer-ring-events", "20000",
            "--observer-post-trigger-events", "20000",
        ]
        process = subprocess.Popen(command, cwd=root, stdout=stdout, stderr=stderr)
        processes.append((seed, process, stdout, stderr))
        launched.append({"pid": process.pid, "seed": seed})
    _write(output_dir / "launch.json", {
        "cohort": manifest.get("cohort"),
        "deadline_utc": deadline.isoformat(),
        "launched": launched,
        "manifest": str(manifest_path.resolve()),
        "started_utc": datetime.now(timezone.utc).isoformat(),
    })
    return_codes = {}
    for seed, process, stdout, stderr in processes:
        return_codes[str(seed)] = process.wait()
        stdout.close()
        stderr.close()
    worlds = []
    for raw_seed in seeds:
        seed = int(raw_seed)
        paths = {
            kind: output_dir / f"{kind}_seed{seed}.{suffix}"
            for kind, suffix in (("result", "json"), ("lineage", "json"), ("observer", "json"),
                                 ("stdout", "log"), ("stderr", "log"))
        }
        complete = False
        integrity_violations = None
        error = None
        try:
            result = json.loads(paths["result"].read_text(encoding="utf-8-sig"))
            lineage = json.loads(paths["lineage"].read_text(encoding="utf-8-sig"))
            observer = json.loads(paths["observer"].read_text(encoding="utf-8-sig"))
            integrity_violations = len(observer["integrity_violations"])
            complete = bool(result["complete"] and lineage["complete"] and observer["complete"])
            complete = complete and observer["digest"] == result["observer_digest"]
            complete = complete and lineage["digest"] == result["lineage_digest"] == observer["lineage"]["digest"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            error = str(exc)
        worlds.append({
            "complete": complete,
            "error": error,
            "integrity_violations": integrity_violations,
            "return_code": return_codes[str(seed)],
            "seed": seed,
            "stderr_bytes": paths["stderr"].stat().st_size if paths["stderr"].exists() else None,
            "stdout_bytes": paths["stdout"].stat().st_size if paths["stdout"].exists() else None,
        })
    hashes = {
        path.name: _file_sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name not in {"sha256.json", "batch_summary.json"}
    }
    _write(output_dir / "sha256.json", hashes)
    summary = {
        "cohort": manifest.get("cohort"),
        "complete": all(
            item["complete"] and item["return_code"] == 0 and item["integrity_violations"] == 0
            and item["stdout_bytes"] == 0 and item["stderr_bytes"] == 0
            for item in worlds
        ),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "worlds": worlds,
    }
    _write(output_dir / "batch_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = run_cohort(args.manifest, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if summary["complete"] else 1)


if __name__ == "__main__":
    main()
