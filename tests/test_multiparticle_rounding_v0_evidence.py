"""Multiparticle Rounding Gate V0 evidence: the stored summary is reproduced by the independent checker."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from multiparticle_rounding_v0 import checker

EVID = Path(__file__).resolve().parents[1] / "docs" / "active" / "multiparticle_rounding_v0"


def test_summary_recomputed():
    raw = gzip.decompress((EVID / "results.json.gz").read_bytes())
    stored = json.loads((EVID / "summary.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == stored["results_sha256"]
    again = json.loads(json.dumps(checker.check(json.loads(raw), skip_exhaustive=True)))
    assert again == {k: v for k, v in stored.items() if k != "results_sha256"}


def test_headline_facts():
    s = json.loads((EVID / "summary.json").read_text(encoding="utf-8"))
    assert s["N2_equal_to_C1B1"] == {"P": True, "T": True, "C": True}
    assert s["exhaustive_N4"]["P"]["nonconserving"] == 0
    assert s["exhaustive_N4"]["T"]["nonconserving"] > 0
    assert s["exhaustive_N4"]["C"]["stop"] > 0
    assert s["far_field"]["P"]["center_dp_u"] == [0, 0, 0]
    assert s["far_field"]["T"]["conserving"] is False
