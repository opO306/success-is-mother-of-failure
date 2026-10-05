"""Evidence test: the committed PRECISION_PILOT_A1 run files re-check to the committed verdict (independent checker:
cells recomputed from stored endpoints, every policy choice re-derived, frozen params re-derived), and tampering with
a cell, a policy choice, or the INVESTIGATE record is caught."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from experiments.precision_pilot_a1 import checker as CK

EV = Path(CK.ROOT) / "docs/active/precision_pilot_a1"


def unpack(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    for name, text in bundle["run"].items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_evidence_rechecks_to_committed_verdict(tmp_path):
    v = CK.check(unpack(tmp_path))
    committed = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    assert v["EVIDENCE"] == committed["EVIDENCE"] == "OK"
    assert v["incomplete"] == v["invalid_evidence"] == v["conflicts"] == []
    assert json.loads(json.dumps(v["tables"])) == committed["tables"]
    assert json.loads(json.dumps(v["frozen_params_rederived"])) == committed["frozen_params_rederived"]


def test_tampered_cells_are_rejected(tmp_path):
    d = unpack(tmp_path)
    p = d / "eval__A3_high__T1000__P3__r0.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["passes"][-1]["cells"][0] += 1
    p.write_text(json.dumps(doc), encoding="utf-8")
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and any("not reproduced" in x for x in v["invalid_evidence"])


def test_forged_policy_choice_is_rejected(tmp_path):
    d = unpack(tmp_path)
    p = d / "eval__A2_bound__T1000__P2__r1.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["passes"][1]["requested_p"] += 1
    doc["passes"][1]["effective_p"] += 1
    p.write_text(json.dumps(doc), encoding="utf-8")
    v = CK.check(d)
    assert any("but the rule gives" in x for x in v["invalid_evidence"])


def test_missing_investigate_pass_downgrades_min_claim(tmp_path):
    d = unpack(tmp_path)
    committed = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    row = committed["tables"]["A3_low@1000"]
    assert row["claim"] == "MIN_SUCCESS_IN_DECLARED_DOMAIN"
    gone = d / f"inv__A3_low__T1000__p{row['lowest_success'] - 1}.json"
    gone.unlink()
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and v["tables"] is None
    assert f"missing investigate pass: A3_low@1000 p{row['lowest_success'] - 1}" in v["incomplete"]
    t = v["tables_unverified"]["A3_low@1000"]
    assert t["claim"] == "LOWEST_SUCCESS_OBSERVED" and t["untried_below"] == 1
