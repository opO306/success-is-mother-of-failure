"""Evidence test: the committed STATE_OBJECT_EVENT_PILOT_V0 results re-check to the committed checker verdict.

The run files are bundled in results.json.gz. The checker re-runs its own replays (PART A: canonical REF executor,
PART B: 512-bit interval reference); the certificate is re-checked on a fixed spread of cells (the full recomputation
of all 615 cells is in the committed verdict).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from experiments.state_object_event_pilot_v0 import checker as CK

EV = Path(CK.ROOT) / "docs/active/state_object_event_pilot_v0"


def _extract(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    dirs = {}
    for part, files in bundle.items():
        d = tmp_path / part
        d.mkdir()
        for name, text in files.items():
            (d / name).write_text(text, encoding="utf-8")
        dirs[part] = d
    return dirs


def test_evidence_rechecks_to_committed_verdict(tmp_path):
    verdict = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    dirs = _extract(tmp_path)
    a = CK.check_part_a(dirs["partA"])
    for k in ("OBSERVER_ISOLATION", "WORLD_LIVE_MEMORY", "PORT_MODEL", "PORT_COST", "PORT_STRUCTURE_ONLY",
              "PAIR_CURRENT_STATE", "PAIR_COST"):
        assert a[k] == verdict["part_A"][k], k
    cert = EV / "derivative_certificate.json.gz"
    b = CK.check_part_b(dirs["partB"], cert)
    for k in ("LINEAGE_SOUNDNESS", "LINEAGE_CORRELATION", "LINEAGE_COST", "TAG_GROWTH", "extension_rederived"):
        assert b[k] == verdict["part_B"][k], k
    corrected = json.loads((EV / "checker_verdict_corrected.json").read_text(encoding="utf-8"))["part_B"]
    assert b["invalid_evidence"] == corrected["invalid_evidence"] == [] and b["incomplete"] == []
    for k in ("LINEAGE_SOUNDNESS", "LINEAGE_CORRELATION", "LINEAGE_COST", "TAG_GROWTH", "stage1_extension_eligibility"):
        assert b[k] == corrected[k], k
    spread = list(range(CK.MLO, CK.MHI + 1, 41)) + [CK.MHI]
    c = CK.check_certificate(cert, recompute=spread, workers=1)
    assert c["problems"] == [] and verdict["certificate"]["problems"] == []
    assert verdict["certificate"]["recomputed"] == 615 and c["content_sha256"] == verdict["certificate"]["content_sha256"]


def test_certificate_checker_catches_tampering(tmp_path):
    with gzip.open(EV / "derivative_certificate.json.gz", "rb") as f:
        body = json.loads(f.read())

    def write(b, name):
        p = tmp_path / name
        with gzip.open(p, "wb") as f:
            f.write(json.dumps(b).encode())
        return p
    m0 = body["cells"][100]["m"]
    t1 = json.loads(json.dumps(body))
    lo, hi = t1["cells"][100]["Gp"]
    t1["cells"][100]["Gp"] = [hi, hi]                                   # narrowed G' (forged tighter)
    assert any("G'" in p for p in CK.check_certificate(write(t1, "a.gz"), recompute=[m0], workers=1)["problems"])
    t2 = json.loads(json.dumps(body))
    del t2["cells"][50]                                                 # gap
    assert any("coverage" in p for p in CK.check_certificate(write(t2, "b.gz"), recompute=[], workers=1)["problems"])
    t3 = json.loads(json.dumps(body))
    t3["cells"].insert(10, t3["cells"][10])                             # overlap / duplicate
    assert any("coverage" in p for p in CK.check_certificate(write(t3, "c.gz"), recompute=[], workers=1)["problems"])
    t4 = json.loads(json.dumps(body))
    t4["cells"][100]["V1"] = [t4["cells"][100]["V1"][0], t4["cells"][100]["V1"][0]]   # stored V' changed
    assert any("recomputed" in p or "G'" in p for p in
               CK.check_certificate(write(t4, "d.gz"), recompute=[m0], workers=1)["problems"])
    t5 = json.loads(json.dumps(body))
    t5["protocol_sha256_lf"] = "0" * 64
    assert any("protocol" in p for p in CK.check_certificate(write(t5, "e.gz"), recompute=[], workers=1)["problems"])
