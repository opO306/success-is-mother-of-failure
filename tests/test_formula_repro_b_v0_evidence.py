"""Evidence test: the committed FORMULA_REPRO_B_V0 run files re-check to the committed verdict (cells recomputed from
stored endpoints by the independent checker; medians recomputed from raw rows)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from experiments.formula_repro_b_v0 import checker as CK

EV = Path(CK.ROOT) / "docs/active/formula_repro_b_v0"


def test_evidence_rechecks_to_committed_verdict(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    for name, text in bundle["run"].items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    v = CK.check(tmp_path)
    committed = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    assert v["incomplete"] == v["invalid_evidence"] == v["mismatches"] == []
    for k in ("OBSERVATION_AGREEMENT", "TRANSFORM_CHECKS", "UPSTREAM_TESTS"):
        assert v[k] == committed[k], k
    norm = lambda x: json.loads(json.dumps(x))  # noqa: E731  (tuples become lists as in the committed file)
    assert norm(v["fixed_precision"]) == committed["fixed_precision"]
    assert norm(v["policy"]) == committed["policy"]


def test_tampered_cells_are_rejected(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    for name, text in bundle["run"].items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    p = tmp_path / "policy__A3_high__s1000__algebra__t0.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["cells"][0] += 1
    p.write_text(json.dumps(doc), encoding="utf-8")
    v = CK.check(tmp_path)
    assert any("not reproduced" in x for x in v["invalid_evidence"])
    assert v["OBSERVATION_AGREEMENT"] == "INCOMPLETE"
