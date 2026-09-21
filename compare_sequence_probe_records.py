"""Compare trial identity and observations between two sequence probe files."""

from __future__ import annotations

import argparse
import gzip
import json
from itertools import zip_longest
from pathlib import Path


def _open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--archive-frame-prefix", type=int)
    args = parser.parse_args()

    compared = 0
    with _open_text(args.first) as left, _open_text(args.second) as right:
        for index, (left_line, right_line) in enumerate(zip_longest(left, right)):
            if left_line is None or right_line is None:
                raise SystemExit(f"record count differs at trial {index}")
            first = json.loads(left_line)
            second = json.loads(right_line)
            identity_keys = ("case_tag", "seed")
            for key in identity_keys:
                if first[key] != second[key]:
                    raise SystemExit(f"{key} differs at trial {index}")
            if args.archive_frame_prefix is not None:
                limit = args.archive_frame_prefix
                first_frames = first["archive"]["frames"][:limit]
                second_frames = second["archive"]["frames"][:limit]
                if first_frames != second_frames or len(first_frames) != min(limit, len(second_frames)):
                    raise SystemExit(f"archive prefix differs at trial {index}")
            else:
                for key in ("max_events", "observation"):
                    if first[key] != second[key]:
                        raise SystemExit(f"{key} differs at trial {index}")
            compared += 1
    result = {"trials_compared": compared}
    if args.archive_frame_prefix is None:
        result["observations_identical"] = True
    else:
        result["archive_frame_prefix"] = args.archive_frame_prefix
        result["prefixes_identical"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
