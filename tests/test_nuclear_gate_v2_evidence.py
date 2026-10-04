"""Gate V2 evidence: stored verdicts are reproduced by the independent checker."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from nuclear_gate_v2 import checker

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "active" / "nuclear_gate_v2"


def _load():
    raw = gzip.decompress((EVID / "results.json.gz").read_bytes())
    stored = json.loads((EVID / "verdicts.json").read_text(encoding="utf-8"))
    return raw, json.loads(raw), stored


def test_hash_and_recomputed_verdicts():
    raw, results, stored = _load()
    assert hashlib.sha256(raw).hexdigest() == stored["results_sha256"]
    proto = json.loads((ROOT / "nuclear_gate_v2" / "protocol.json").read_text(encoding="utf-8"))
    again = json.loads(json.dumps(checker.check(results, proto)))
    assert again == {k: v for k, v in stored.items() if k != "results_sha256"}


def test_headline_facts():
    _, results, _ = _load()
    v = checker.check(results)
    assert all(c["machinery_check"]["pass"] for c in v["S1"])
    # CT branch separation never passes the trajectory-count convergence rule
    assert all(c["methods"]["CT"]["verdict"]["branch_separation"] == "REFUSED" for c in v["S1"])
    # S2r is not a tunnelling discriminator: classical Wigner mass above the barrier is large
    assert v["S2r"]["BOCL_exact"]["wigner_mass_above_barrier"] > 0.3
    assert v["S3"]["phase_verdict"]["CT"]["verdict"] == "REFUSED"
    assert set(v["S3"]["phase_verdict"]["CT"]["per_P0"]) == {"UNSUPPORTED"}
