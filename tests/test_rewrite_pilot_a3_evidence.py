"""Evidence test: the committed REWRITE_PILOT_A3 run files re-check to the committed verdict, and tampering is caught:
a plan coefficient (S3a), a stored S4 enclosure, the selection, a policy choice, a missing INVESTIGATE pass, a cell."""

from __future__ import annotations

import gzip
import json
from fractions import Fraction as F
from pathlib import Path

from experiments.rewrite_pilot_a3 import checker as CK

EV = Path(CK.ROOT) / "docs/active/rewrite_pilot_a3"


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


def committed():
    return json.loads((EV / "checker_verdict.json").read_text(encoding="utf-8"))


def test_evidence_rechecks_to_committed_verdict(tmp_path):
    v = CK.check(unpack(tmp_path))
    c = committed()
    assert v["EVIDENCE"] == c["EVIDENCE"] == "OK"
    assert v["incomplete"] == v["invalid_evidence"] == v["conflicts"] == []
    assert json.loads(json.dumps(v["tables"], default=str)) == c["tables"]
    assert v["selection_rederived"] == c["selection_rederived"] and v["passing_candidates"] == c["passing_candidates"]
    assert v["enclosure_pairs_checked"] == c["enclosure_pairs_checked"] > 0


def test_forged_plan_coefficient_fails_s3a(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        P = doc["plan"]["blocks"][0]
        k = next(iter(P))
        P[k] = str(F(P[k]) * (1 + F(1, 10 ** 30)))
    edit(d / "verify__rw-R1_R2.json", f)
    v = CK.check(d)
    assert any("rw:R1+R2: S3a claimed True but re-check gives False" in x for x in v["invalid_evidence"])


def test_narrowed_s4_enclosure_is_caught(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        e = doc["stages"]["S4"]["point_enclosures"]["128"][10]
        mid = (F(e[0]) + F(e[1])) / 2
        doc["stages"]["S4"]["point_enclosures"]["128"][10] = [str(mid), str(mid)]
    edit(d / "verify__rw-R1.json", f)
    assert any("rw:R1: S4 claimed True but re-check gives False" in x for x in CK.check(d)["invalid_evidence"])


def test_tampered_selection_is_caught(tmp_path):
    d = unpack(tmp_path)

    def f(doc):
        doc["FAST"] = "rw:R1"
    edit(d / "selection.json", f)
    assert any(x.startswith("selection ") for x in CK.check(d)["invalid_evidence"])


def test_forged_policy_choice_is_caught(tmp_path):
    d = unpack(tmp_path)
    fast = committed()["selection_rederived"]["FAST"]

    def f(doc):
        doc["passes"][1]["requested_p"] += 1
        doc["passes"][1]["effective_p"] += 1
    edit(d / f"eval__A2_bound__T1000__{CK.safe(fast)}__P2__r1.json", f)
    assert any("but the rule gives" in x for x in CK.check(d)["invalid_evidence"])


def test_missing_investigate_pass_is_incomplete(tmp_path):
    d = unpack(tmp_path)
    sorted(d.glob("inv__*.json"))[0].unlink()
    v = CK.check(d)
    assert v["EVIDENCE"] == "NOT_OK" and any(x.startswith("missing investigate pass") for x in v["incomplete"])


def test_tampered_cell_is_caught(tmp_path):
    d = unpack(tmp_path)
    fast = committed()["selection_rederived"]["FAST"]

    def f(doc):
        doc["passes"][-1]["cells"][0] += 1
    edit(d / f"eval__A3_high__T1000__{CK.safe(fast)}__P3__r0.json", f)
    assert any("cells not reproduced" in x for x in CK.check(d)["invalid_evidence"])
