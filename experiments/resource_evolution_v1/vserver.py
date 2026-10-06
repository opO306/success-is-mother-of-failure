"""Verifier subprocess for the S5 pipeline: reads {"key": [s, T], "rec": pass} lines, writes {"key", "v"} lines."""

from __future__ import annotations

import json
import sys

from . import verifier as VF


def main():
    for ln in sys.stdin:
        if ln.strip():
            d = json.loads(ln)
            v = VF.verify(d["rec"], d["key"][0], d["key"][1])
            sys.stdout.write(json.dumps({"key": d["key"], "v": v}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
