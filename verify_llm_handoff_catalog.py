"""Verify every file referenced by the non-destructive LLM handoff catalog."""
from __future__ import annotations

import json
from pathlib import Path

from build_llm_handoff_catalog import DESCRIPTIONS, OUT, ROOT, classify, sha256


def main() -> None:
    catalog_path = OUT / "catalog_summary.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    errors = []
    seen: dict[str, str] = {}
    verified_files = 0
    verified_bytes = 0
    for lane, metadata in sorted(catalog["lanes"].items()):
        folder = OUT / metadata["folder"]
        manifest_path = folder / "manifest.json"
        if sha256(manifest_path) != metadata["manifest_sha256"]:
            errors.append(f"manifest hash mismatch: {lane}")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["file_count"] != len(manifest["files"]): errors.append(f"file count mismatch: {lane}")
        if manifest["bytes"] != sum(item["bytes"] for item in manifest["files"]):
            errors.append(f"byte total mismatch: {lane}")
        for item in manifest["files"]:
            relative = item["path"]
            if relative in seen: errors.append(f"duplicate path: {relative} in {seen[relative]} and {lane}")
            seen[relative] = lane
            path = ROOT / relative
            if not path.is_file():
                errors.append(f"missing source: {relative}")
                continue
            if path.stat().st_size != item["bytes"]: errors.append(f"size mismatch: {relative}")
            elif sha256(path) != item["sha256"]: errors.append(f"hash mismatch: {relative}")
            verified_files += 1; verified_bytes += path.stat().st_size
    expected = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or "LLM_HANDOFF" in path.parts: continue
        lane = classify(path)
        if lane not in {"generated_cache", "excluded_private_or_catalog"}: expected.add(path.relative_to(ROOT).as_posix())
    missing_from_catalog = sorted(expected - set(seen))
    unexpected = sorted(set(seen) - expected)
    errors.extend(f"not cataloged: {path}" for path in missing_from_catalog)
    errors.extend(f"unexpected catalog path: {path}" for path in unexpected)
    result = {"catalog_sha256": sha256(catalog_path), "errors": errors,
              "missing_from_catalog": len(missing_from_catalog),
              "physical_moves_performed": catalog["physical_moves_performed"],
              "unexpected_paths": len(unexpected), "valid": not errors,
              "verified_bytes": verified_bytes, "verified_files": verified_files}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
