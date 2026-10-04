"""Exact Expression Gate V1 evidence: the stored run is re-checked by the independent checker (full, incl. replay)."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

from exact_expression_gate_v1 import checker

EVID = Path(__file__).resolve().parents[1] / "docs" / "active" / "exact_expression_gate_v1"


def test_stored_run_rechecks_to_stored_verdict(tmp_path):
    with tarfile.open(EVID / "run_files.tar.gz") as t:
        t.extractall(tmp_path)
    run = tmp_path / "exact_expression_gate_v1_20261005"
    stored = json.loads((EVID / "verdict.json").read_text(encoding="utf-8"))
    again = json.loads(json.dumps(checker.check(run)))
    assert again["verdict"] == stored["verdict"] == "COMPARISON_COMPLETE"
    for k in ("claims", "predictions", "comparison", "controls", "replay_confirmations"):
        assert again[k] == stored[k]
    assert (EVID / "execution_seal.json").read_bytes() == (run / "execution_seal.json").read_bytes()
