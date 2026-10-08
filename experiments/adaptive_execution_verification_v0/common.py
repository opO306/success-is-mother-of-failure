"""Collector/manager utilities. The independent verifier deliberately does not import this."""
from __future__ import annotations

import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULT_FIELDS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def seconds_ns(value):
    if isinstance(value, bool):
        raise ValueError("invalid timing")
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0:
        raise ValueError("invalid timing")
    # Explicit decimal conversion of stored measurements, not physics rounding.
    return int((number * 1_000_000_000).to_integral_value(rounding="ROUND_HALF_EVEN"))


def exclusive_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(canonical(value) + b"\n")


def check_seals(root=ROOT):
    root = Path(root)
    seal = read(root / "experiments/adaptive_execution_verification_v0/protocol_seal.json")
    for relative, expected in seal["files"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("PROTOCOL_SEAL_MISMATCH:" + relative)
    manifest = read(root / "experiments/adaptive_execution_verification_v0/source_manifest.json")
    budget = read(root / "experiments/adaptive_execution_verification_v0/protocol.json")["initial_evidence"]["source_budget"]
    if len(manifest["files"]) > budget["max_files"]:
        raise ValueError("SOURCE_FILE_BUDGET")
    total = 0
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("PATH_OUTSIDE_ROOT")
        size = path.stat().st_size
        total += size
        if size > budget["max_file_bytes"] or total > budget["max_total_bytes"]:
            raise ValueError("SOURCE_BYTE_BUDGET")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("SOURCE_SEAL_MISMATCH:" + relative)
    return manifest
