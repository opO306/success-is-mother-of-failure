"""Exact Expression Gate V1 — domain obligation, stream identity, controls, checker and its fault injections."""

from __future__ import annotations

import ast
import json
import shutil
import sys
import types
from fractions import Fraction as Q
from pathlib import Path

import pytest
from mpmath import iv

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_two_atom as C1
from exact_expression_gate_v0 import dag as dag_v0
from exact_expression_gate_v1 import campaign, checker, common as K, paths, stream
from exact_expression_gate_v1.dag import DAG, build_kdk

PKG = Path(campaign.__file__).resolve().parent
GRID = json.loads((PKG / "protocol.json").read_text(encoding="utf-8"))["precision_grid"]
Z3 = (Q(0), Q(0), Q(0))


def test_constants_match_reference():
    assert K.MASS == C1.AR40_MASS_ME == checker.MASS
    assert K.R_MIN2 == Q(L.R_MIN_BOHR) ** 2 == checker.RMIN2


def test_domain_three_way_and_boundary():
    assert K.domain(K.R_MIN2) == K.PROVEN                       # R = r_min is inside (reference refuses only R < r_min)
    assert K.domain(K.R_MIN2 - Q(1, 10 ** 30)) == K.VIOLATED
    iv.prec = 64
    assert K.domain(iv.mpf([0, 100])) == K.UNPROVEN
    assert K.domain(iv.mpf([10, 11])) == K.PROVEN
    assert K.domain(iv.mpf([0, 1])) == K.VIOLATED


def test_measuring_device_range_and_nonfinite():
    assert K.cell(Q(1, 2 ** 49), K.POS_F) == 0                  # exact tie, half even
    with pytest.raises(K.OutOfRange):
        K.cell(Q(2 ** 47), K.POS_F)                             # raw 2^95 does not fit FX(96, 48)
    assert K.cell(Q(2 ** 47) - Q(1, 2 ** 48), K.POS_F) == 2 ** 95 - 1
    iv.prec = 64
    assert K.cell(iv.mpf(["-inf", "inf"]), K.POS_F) is None


def test_legacy_defect_v0_b_erases_domain_and_v1_keeps_it():
    """legacy_defect: sealed V0 path B returns cells for two coincident atoms (G(0) folded away, never checked)."""
    q0, p0 = [Z3, Z3], [Z3, Z3]
    out = {}
    for opt in (False, True):
        d = dag_v0.DAG(opt)
        qi, pi = dag_v0.build_kdk(d, q0, p0, K.MASS, K.DT, 1, {1})[1]
        try:
            out[opt] = d.evaluate(qi + pi, 128)
        except ValueError:
            out[opt] = "refused"
    assert out[False] == "refused" and out[True] != "refused"     # the V0 defect, preserved as found
    for path in paths.PATHS:                                      # V1: every path refuses
        r = paths.run_workload(path, q0, p0, [[1]], GRID)["results"]["1"]
        assert r["status"] == K.REFUSED_DOMAIN and r["completed_steps"] == 0, (path, r)


def test_obligations_survive_folding_in_b():
    d = DAG(True)
    snaps = build_kdk(d, [Z3, Z3], [Z3, Z3], 1, {1})
    qi, pi, nob = snaps[1]
    reach, _ = d.reachable(qi + pi)
    g_nodes = [g for g, _ in d.obligations[:nob]]
    assert nob == 2 and all(d.nodes[g][0] == "G" for g in g_nodes)
    assert not any(d.nodes[i][0] == "G" for i in d._collect(qi + pi))   # value no longer depends on G ...
    with pytest.raises(K.DomainStop) as e:                                # ... but the duty is still checked
        d.evaluate(qi + pi + g_nodes, 64)
    assert e.value.kind == K.VIOLATED and reach > 0


def test_mid_trajectory_refusal_identical_on_every_path():
    disp = Q(1, 4)
    pm = disp * K.MASS / K.DT
    q0 = [(Q(-7, 4), Q(0), Q(0)), (Q(7, 4), Q(0), Q(0))]
    p0 = [(pm, Q(0), Q(0)), (-pm, Q(0), Q(0))]
    seen = set()
    for path in paths.PATHS:
        res = paths.run_workload(path, q0, p0, [[1, 2, 3, 4]], GRID)["results"]
        sig = tuple((k, r["status"], r.get("completed_steps"), r.get("bits")) for k, r in sorted(res.items()))
        seen.add(sig)
    assert len(seen) == 1
    (sig,) = seen
    assert [s[1] for s in sig] == ["DECIDED", "DECIDED", "REFUSED_DOMAIN", "REFUSED_DOMAIN"]
    assert sig[2][2] == 2


def test_halfway_counterexample_regression():
    """Handover counterexample: exact folding (B, CX) decides an exact tie at 64 bits; interval paths cannot."""
    q0, p0 = campaign.scenarios()["H_halfway"]
    want = checker.halfway_expected()
    for path in paths.PATHS:
        r = paths.run_workload(path, q0, p0, [[1]], GRID)["results"]["1"]
        if path in ("B", "CX"):
            assert r["status"] == K.DECIDED and r["bits"] == 64 and r["cells"] == want
        else:
            assert r["status"] == K.UNDECIDED_AT_CAP


def test_c_and_cs_bit_identical_and_observation_invariant():
    q0, p0 = campaign.scenarios()["A3_high"]
    full = stream.run(q0, p0, 128, 6, {2, 4, 6})
    sparse = stream.run(q0, p0, 128, 6, {6})
    every = stream.run(q0, p0, 128, 6, set(range(1, 7)))
    assert full["read"][6] == sparse["read"][6] == every["read"][6]
    assert full["read"][4] == every["read"][4]
    cold = paths.run_workload("C", q0, p0, [[2], [4]], GRID)["results"]
    warm = paths.run_workload("CS", q0, p0, [[2, 4]], GRID)["results"]
    assert cold == warm


def test_cx_matches_cs_cells_and_keeps_free_flight_exact():
    q0, p0 = campaign.scenarios()["A2_bound"]
    cs = paths.run_workload("CS", q0, p0, [[1, 5]], GRID)["results"]
    cx = paths.run_workload("CX", q0, p0, [[1, 5]], GRID)["results"]
    assert {k: v["cells"] for k, v in cs.items()} == {k: v["cells"] for k, v in cx.items()}
    q0, p0 = campaign.scenarios()["F_free"]
    r = stream.run(q0, p0, 64, 50, {50}, exact=True)
    assert r["read"][50][1].count("Q") == 6                     # every state value still an exact Fraction


def test_checker_independent_of_executor():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("dag", "stream", "paths", "common", "campaign"):
        assert not any(n.split(".")[-1] == bad or n == "." + bad for n in names), names


def test_sealed_source_list_identical():
    assert campaign.SEALED == checker.SEALED


@pytest.fixture(scope="module")
def quick_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("ee1")
    campaign.main(["--out", str(out), "--quick", "--workers", "6"])
    return out


def test_quick_campaign_and_checker(quick_dir):
    v = checker.check(quick_dir)
    assert v["verdict"] == "INCOMPLETE" and any("quick" in r for r in v["incomplete_reasons"])
    assert not any("missing" in r or "failed" in r for r in v["incomplete_reasons"])
    assert v["claims"]["K1_DOMAIN"] == "HOLDS"
    assert v["claims"]["K2_HALFWAY"] == "HOLDS"
    assert v["claims"]["K3_STREAM_IDENTITY"] == "HOLDS"
    assert all(c["confirmed"] for c in v["replay_confirmations"]) and len(v["replay_confirmations"]) == 8


# ---- fault injection: each forged or damaged run must be caught --------------------------------------------------

def _copy(quick_dir, tmp_path):
    d = tmp_path / "run"
    shutil.copytree(quick_dir, d)
    return d


def _edit(d, stem, fn):
    f = d / f"{stem}.json"
    doc = json.loads(f.read_text(encoding="utf-8"))
    fn(doc)
    f.write_text(json.dumps(doc), encoding="utf-8")


def test_fault_empty_evidence_is_never_positive(quick_dir, tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    shutil.copy(quick_dir / "execution_seal.json", d)
    v = checker.check(d)
    assert v["verdict"] == "INCOMPLETE" and sum(r.startswith("job missing:") for r in v["incomplete_reasons"]) == 70
    assert v["claims"]["K1_DOMAIN"] == "UNDETERMINED" and v["predictions"]["P1"] == "UNDETERMINED"


def test_fault_results_emptied(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    _edit(d, "A2_bound__B__warm", lambda doc: doc["record"].update(results={}))
    assert any("requested steps missing" in r for r in checker.check(d)["incomplete_reasons"])


def test_fault_tampered_cells(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)

    def f(doc):
        doc["record"]["results"]["3"]["cells"][0] += 1
    _edit(d, "A3_low__CS__warm", f)
    with pytest.raises(checker.CheckError):
        checker.check(d)


def test_fault_consistent_forgery_caught_by_replay(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    for p in checker.PATHS:
        for w in ("cold", "warm", "every"):
            def f(doc):
                r = doc["record"]["results"].get("5")
                if r and r["status"] == "DECIDED":
                    r["cells"][1] += 1
            _edit(d, f"A2_bound__{p}__{w}", f)
    with pytest.raises(checker.CheckError, match="independent replay"):
        checker.check(d)


def test_fault_stored_total_not_trusted_and_missing_cost(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    _edit(d, "A3_high__C__every", lambda doc: doc["record"]["total"].update(cpu_s=0.0))
    v = checker.check(d)
    assert v["comparison"]["A3_high"]["every"]["cpu_s"]["C"] > 0
    _edit(d, "A3_high__C__every", lambda doc: doc["record"]["queries"][0]["attempts"][0].pop("cpu_s"))
    assert any("cost fields" in r for r in checker.check(d)["incomplete_reasons"])


def test_fault_binding(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    _edit(d, "F_free__A__cold", lambda doc: doc.update(protocol_sha256="0" * 64))
    with pytest.raises(checker.CheckError, match="not bound"):
        checker.check(d)
    d2 = _copy(quick_dir, tmp_path / "x")
    seal = json.loads((d2 / "execution_seal.json").read_text(encoding="utf-8"))
    seal["source_sha256_lf"]["exact_expression_gate_v1/dag.py"] = "0" * 64
    (d2 / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    with pytest.raises(checker.CheckError, match="source changed"):
        checker.check(d2)


def test_fault_domain_erasure_regression_flagged(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    _edit(d, "D_zero__B__control",
          lambda doc: doc["record"]["results"].update({"1": {"status": "DECIDED", "bits": 64, "cells": [0] * 12}}))
    assert checker.check(d)["claims"]["K1_DOMAIN"] == "FAILS"


def test_fault_halfway_wrong_cells(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)

    def f(doc):
        doc["record"]["results"]["1"]["cells"][0] = 1
    _edit(d, "H_halfway__CX__control", f)
    with pytest.raises(checker.CheckError, match="cells differ"):       # B still has the true cells
        checker.check(d)
    _edit(d, "H_halfway__B__control", f)                                # consistent forgery of both deciders
    with pytest.raises(checker.CheckError, match="exact answer"):
        checker.check(d)


def test_fault_missing_job_and_error_file(quick_dir, tmp_path):
    d = _copy(quick_dir, tmp_path)
    (d / "A3_high__A__warm.json").unlink()
    (d / "A3_high__A__warm.ERROR.txt").write_text("boom", encoding="utf-8")
    v = checker.check(d)
    assert v["verdict"] == "INCOMPLETE"
    assert any("missing: A3_high__A__warm" in r for r in v["incomplete_reasons"])
    assert any("failed: A3_high__A__warm" in r for r in v["incomplete_reasons"])
