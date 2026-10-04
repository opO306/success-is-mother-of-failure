"""Gate V1 evidence: stored verdicts are reproduced by the independent checker
from the stored raw results under the sealed protocol."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from nuclear_gate_v1 import checker

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "active" / "nuclear_gate_v1"


def _load():
    raw = gzip.decompress((EVID / "results.json.gz").read_bytes())
    stored = json.loads((EVID / "verdicts.json").read_text(encoding="utf-8"))
    return raw, json.loads(raw), stored


def test_raw_results_match_verdict_hash():
    raw, _, stored = _load()
    assert hashlib.sha256(raw).hexdigest() == stored["results_sha256"]


def test_verdicts_recomputed_under_sealed_protocol():
    _, results, stored = _load()
    proto = json.loads((ROOT / "nuclear_gate_v1" / "protocol.json").read_text(encoding="utf-8"))
    again = checker.check(results, proto)
    stored = {k: v for k, v in stored.items() if k != "results_sha256"}
    assert json.loads(json.dumps(again)) == stored


def test_headline_verdicts():
    _, results, _ = _load()
    v = checker.check(results)
    for cell in v["cells"]:
        s1 = cell["scenarios"]["S1_slide"]
        assert s1["reference"]["valid"]
        assert s1["reference"]["final"]["P_exc"] > 0.6
        for m in ("BOQ", "BOCL"):
            assert s1["verdicts"][m]["verdict"]["P_exc"] == "ABSENT_BY_CONSTRUCTION"
            assert s1["verdicts"][m]["verdict"]["electron_right"] == "DISTORTED"
        assert s1["verdicts"]["EH"]["verdict"]["P_exc"] == "REPRESENTED"
        assert s1["verdicts"]["EH"]["verdict"]["branch_separation"] in ("DISTORTED", "REFUSED")
    assert v["cells"][2]["scenarios"]["S2_barrier"]["reference"]["valid"] is False
