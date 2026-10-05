"""Evidence test: the committed PRECISION_PILOT_A2T run files re-check to the committed verdict (independent checker),
and tampering is caught: a cell, a policy choice, a missing INVESTIGATE pass, a vendor module path, and an algebra
enclosure moved away from the original's."""

from __future__ import annotations

import gzip
import json
from fractions import Fraction as F
from pathlib import Path

from experiments.precision_pilot_a2t import checker as CK

EV = Path(CK.ROOT) / "docs/active/precision_pilot_a2t"


def unpack(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    for name, text in bundle["run"].items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def edit(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_evidence_rechecks_to_committed_verdict(tmp_path):
    v = CK.check(unpack(tmp_path))
    committed = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    assert v["EVIDENCE"] == committed["EVIDENCE"] == "OK"
    assert v["incomplete"] == v["invalid_evidence"] == v["conflicts"] == []
    assert json.loads(json.dumps(v["tables"])) == committed["tables"]
    assert v["enclosure_pairs_checked"] == committed["enclosure_pairs_checked"] > 0
    assert v["a1_shared_original_passes"] == committed["a1_shared_original_passes"] > 0


def test_tampered_algebra_cells_are_rejected(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["passes"][-1]["cells"][0] += 1
    edit(d / "eval__A3_high__T1000__algebra__P3__r0.json", f)
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and any("not reproduced" in x for x in v["invalid_evidence"])


def test_forged_policy_choice_is_rejected(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["passes"][1]["requested_p"] += 1
        doc["passes"][1]["effective_p"] += 1
    edit(d / "eval__A2_bound__T1000__algebra__P2__r1.json", f)
    assert any("but the rule gives" in x for x in CK.check(d)["invalid_evidence"])


def test_missing_investigate_pass_is_incomplete(tmp_path):
    d = unpack(tmp_path)
    victim = sorted(d.glob("inv__*__algebra__p*.json"))[0]
    victim.unlink()
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and any(x.startswith("missing investigate pass") for x in v["incomplete"])


def test_vendor_module_path_is_rejected(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["modules"]["exact_expression_gate_v0.lang_iv"] = str(
            Path(CK.UP) / "vendor/exact_expression_gate_v0/lang_iv.py")
    edit(d / "eval__A3_low__T100__algebra__P0__r2.json", f)
    assert any("not the repository modules" in x for x in CK.check(d)["invalid_evidence"])


def test_moved_algebra_enclosure_breaks_intersection(tmp_path):
    d = unpack(tmp_path)
    shift = 2 * 10 ** 9                                  # even integer: rounding (half-even) of both ends shifts alike

    def f(doc):
        h = doc["passes"][0]
        assert h["outcome"] == "UNDECIDED_AT_PRECISION"
        h["endpoints_scaled"] = [[str(F(a) + shift), str(F(b) + shift)] for a, b in h["endpoints_scaled"]]
    edit(d / "eval__A3_high__T1000__algebra__P0__r0.json", f)
    v = CK.check(d)
    assert any("do not intersect" in x for x in v["conflicts"])
