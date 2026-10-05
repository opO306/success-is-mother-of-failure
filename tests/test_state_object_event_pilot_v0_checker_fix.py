"""Stage 0 regression tests: the three checker defects found by the external limited review (F-METRIC, F-INCOMPLETE,
F-COMPLETENESS). Each test tampers a COPY of the committed PART B evidence; the committed files are never changed.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from experiments.state_object_event_pilot_v0 import checker as CK

EV = Path(CK.ROOT) / "docs/active/state_object_event_pilot_v0"
CERT = EV / "derivative_certificate.json.gz"


def _part_b(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        files = json.loads(f.read())["partB"]
    d = tmp_path / "partB"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    return d


def _edit(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")


def _not_positive(v):
    return v["LINEAGE_SOUNDNESS"] != "PASS" and v["LINEAGE_CORRELATION"] not in ("YES", "NO")


def test_untampered_evidence_still_passes(tmp_path):
    v = CK.check_part_b(_part_b(tmp_path), CERT)
    assert v["LINEAGE_SOUNDNESS"] == "PASS" and not v["invalid_evidence"] and not v["incomplete"]


def test_f_metric_forged_radius_is_rejected(tmp_path):
    d = _part_b(tmp_path)

    def forge(doc):
        for s in doc["read"].values():
            s["norm_radius_mom_exact"] = "1/" + "1" + "0" * 100
            s["norm_radius_mom"] = 1e-100
    for rep in range(3):
        _edit(d / f"B__candidate__p96__s100__t{rep}.json", forge)
    v = CK.check_part_b(d, CERT)
    assert any("radius" in x for x in v["invalid_evidence"])
    assert _not_positive(v)


def test_f_incomplete_missing_stage2_leaves_no_positive_label(tmp_path):
    d = _part_b(tmp_path)
    for f in list(d.iterdir()):
        if "__s1000__" in f.name or f.name == "execution_seal_stage2.json":
            f.unlink()
    v = CK.check_part_b(d, CERT)
    assert any("stage 2" in x for x in v["incomplete"])
    assert _not_positive(v)
    assert v["stage1_extension_eligibility"] == "EXTEND"          # stage-1 eligibility itself is not rewritten


def test_f_completeness_inconsistent_completed_steps_is_rejected(tmp_path):
    d = _part_b(tmp_path)
    _edit(d / "B__candidate__p96__s100__t1.json", lambda doc: doc.update(completed_steps=0))
    v = CK.check_part_b(d, CERT)
    assert any("completed_steps" in x for x in v["invalid_evidence"])
    assert _not_positive(v)


def test_f_completeness_metadata_mismatch_is_rejected(tmp_path):
    d = _part_b(tmp_path)
    _edit(d / "B__baseline__p128__s1000__t2.json", lambda doc: doc.update(prec=96))
    v = CK.check_part_b(d, CERT)
    assert any("metadata" in x for x in v["invalid_evidence"])
    assert _not_positive(v)
