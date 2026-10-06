"""Evidence test: the committed RESOURCE_EVOLUTION_PILOT_V1 run 2 records re-check to the committed verdict, and
tampering is caught: an accepted cell (false accept), an affinity read-back, a conditioned choice, a leaked selector
input, a missing record."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from experiments.resource_evolution_v1 import checker as CK

EV = Path(CK.ROOT) / "docs/active/resource_evolution_v1/run2"


def unpack(tmp_path):
    with gzip.open(EV / "results.json.gz", "rb") as f:
        bundle = json.loads(f.read())
    for name, text in bundle["run"].items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def edit(path, fn):
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_run2_rechecks_to_committed_verdict(tmp_path):
    v = CK.check(unpack(tmp_path))
    c = json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))
    assert v["EVIDENCE"] == c["EVIDENCE"] == "OK"
    assert v["incomplete"] == v["invalid_evidence"] == v["conflicts"] == v["false_accepts"] == []
    assert json.loads(json.dumps(v["tables"], default=str)) == c["tables"]


def test_tampered_accepted_cell_is_a_false_accept(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        w = next(x for x in doc["workers"] if x["accepted"])
        w["passes"][-1]["cells"][0] += 1
    edit(d / "T8__BASE__A3_high_1000__r0.json", f)
    assert CK.check(d)["false_accepts"]


def test_affinity_readback_outside_the_core_set_is_caught(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["workers"][0]["start"]["affinity_readback"] = [0, 1, 2, 3, 4, 5]
    edit(d / "T10__H3__CONS__A2_bound_1000__r0.json", f)
    assert any("affinity" in x for x in CK.check(d)["invalid_evidence"])


def test_forged_conditioned_choice_and_leak_are_caught(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["plan"] = "CONS" if doc["plan"] != "CONS" else "AGG3"
        doc["selector_input"]["hidden_cpu_s"] = 1.0
    edit(d / "T6__05__COND.json", f)
    inv = CK.check(d)["invalid_evidence"]
    assert any("not re-derivable" in x for x in inv) and any("leaks" in x for x in inv)


def test_missing_record_is_incomplete(tmp_path):
    d = unpack(tmp_path)
    (d / "T34__H2__ADAPTIVE__A3_low_1000.json").unlink()
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and "missing: T34__H2__ADAPTIVE__A3_low_1000" in v["incomplete"]
