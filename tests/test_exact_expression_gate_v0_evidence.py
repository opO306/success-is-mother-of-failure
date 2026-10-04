"""Exact Expression State Gate V0 evidence: verdict flags recomputed from the stored scenario files."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from exact_expression_gate_v0 import checker

EVID = Path(__file__).resolve().parents[1] / "docs" / "active" / "exact_expression_gate_v0"


def test_flags_and_verdict_recomputed(tmp_path):
    for n in checker.NAMES:
        (tmp_path / f"{n}.json").write_bytes(gzip.decompress((EVID / f"{n}.json.gz").read_bytes()))
    stored = json.loads((EVID / "verdict.json").read_text(encoding="utf-8"))
    again = json.loads(json.dumps(checker.check(tmp_path, fast=True)))
    assert again["verdict"] == stored["verdict"] == "EXPRESSION_WALL"
    for n in checker.NAMES:
        assert again["scenarios"][n]["flags"] == stored["scenarios"][n]["flags"]
    assert all(c["confirmed"] for c in stored["replay_confirmations"])
