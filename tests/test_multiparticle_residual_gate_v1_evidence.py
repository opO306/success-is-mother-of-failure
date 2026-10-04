"""Residual / Carry Gate V1 evidence: the stored verdict is reproduced by the independent checker."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from multiparticle_residual_gate_v1 import checker

EVID = Path(__file__).resolve().parents[1] / "docs" / "active" / "multiparticle_residual_gate_v1"


def test_verdict_recomputed():
    raw = gzip.decompress((EVID / "results.json.gz").read_bytes())
    stored = json.loads((EVID / "verdict.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == stored["results_sha256"]
    again = json.loads(json.dumps(checker.check(json.loads(raw))))
    assert again == {k: v for k, v in stored.items() if k != "results_sha256"}
    assert stored["verdict"].startswith("B")
    assert stored["equivalence"] == "SAME_SEMANTICS_DIFFERENT_NORMALIZATION"
