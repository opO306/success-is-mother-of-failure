"""Verify every reconstruction and digest in a sequence checkpoint archive."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from engine.sequence import ExperimentArchive, restore_state, verify_archive


def _open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    trials = 0
    final_hashes = hashlib.sha256()
    with _open_text(args.path) as handle:
        for line in handle:
            raw = json.loads(line)
            archive = ExperimentArchive.from_canonical(raw["archive"])
            if archive.digest() != raw["archive_digest"] or not verify_archive(archive):
                raise SystemExit(f"invalid archive at trial {trials}")
            if len(archive.frames) > raw["max_events"]:
                raise SystemExit(f"event count exceeds its limit at trial {trials}")
            if archive.stop_reason == "event_limit" and len(archive.frames) != raw["max_events"]:
                raise SystemExit(f"event-limit archive is truncated at trial {trials}")
            final_state = restore_state(archive, len(archive.frames) - 1) if archive.frames else archive.initial_state
            if final_state.state_hash() != raw["observation"]["final_state_hash"]:
                raise SystemExit(f"final state mismatch at trial {trials}")
            final_hashes.update(final_state.state_hash().encode("ascii"))
            trials += 1
    print(json.dumps({"trials_verified": trials, "ordered_final_hash_digest": final_hashes.hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
