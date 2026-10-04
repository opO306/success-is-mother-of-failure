"""Exact Expression State Gate V0 — force transcription, DAG, optimizer and checker tests."""

from __future__ import annotations

import ast
import copy
import json
from fractions import Fraction as Q
from pathlib import Path

import pytest
from mpmath import iv

import a_reference.ar2_lang2024 as L
from exact_expression_gate_v0 import campaign, checker, lang_iv as LI
from exact_expression_gate_v0.dag import DAG, build_kdk

PKG = Path(campaign.__file__).resolve().parent


@pytest.mark.parametrize("R", [Q(5), Q(71, 10), Q(12), Q(40)])
def test_interval_lang_encloses_reference(R):
    iv.prec = 256
    ref = L.enclose("dVdR", R, 256)
    mine = LI.dVdR(LI.c(R))
    lo, hi = LI.c(ref.lo), LI.c(ref.hi)
    assert mine.a <= hi.b and mine.b >= lo.a          # the two enclosures overlap
    assert float(mine.delta) < 1e-60


def test_free_flight_collapses_under_optimizer():
    q0, p0 = campaign.SCENARIOS["F_free"]
    for opt, expect_const in ((False, False), (True, True)):
        d = DAG(opt)
        snaps = build_kdk(d, q0, p0, campaign.MASS, campaign.DT, 50, {50})
        kinds = {d.nodes[i][0] for i in snaps[50][0]}
        assert (kinds == {"c"}) == expect_const


def test_paths_agree_on_short_n2_run():
    q0, p0 = campaign.SCENARIOS["A2_bound"]
    cells = []
    for opt in (False, True):
        d = DAG(opt)
        snaps = build_kdk(d, q0, p0, campaign.MASS, campaign.DT, 3, {3})
        qi, pi = snaps[3]
        vals = d.evaluate(qi + pi, 192)
        cells.append(campaign.decide(vals[:len(qi)], vals[len(qi):]))
    rep, _ = campaign.replay(q0, p0, 3, 192, {3})
    assert cells[0] is not None and cells[0] == cells[1] == rep[3]


def test_checker_independent_of_executor():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("dag", "campaign"):
        assert not any(bad in n for n in names), names


@pytest.fixture(scope="module")
def quick_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("ee")
    campaign.main(["--out", str(out), "--quick"])
    return out


def test_quick_checker_runs(quick_dir):
    v = checker.check(quick_dir, fast=True)
    assert v["scenarios"]["F_free"]["flags"]["free_passes"]
    assert all(c["confirmed"] for c in v["replay_confirmations"])


def _tamper(quick_dir, tmp_path, name, fn):
    for n in checker.NAMES:
        doc = json.loads((quick_dir / f"{n}.json").read_text(encoding="utf-8"))
        if n == name:
            fn(doc["result"])
        (tmp_path / f"{n}.json").write_text(json.dumps(doc), encoding="utf-8")
    return tmp_path


def test_mutation_tampered_cells_detected(quick_dir, tmp_path):
    def f(r):
        r["cells"]["10"][0] += 1
    d = _tamper(quick_dir, tmp_path, "A2_bound", f)
    with pytest.raises(checker.CheckError):
        checker.check(d, fast=True)


def test_mutation_b_disagreement_detected(quick_dir, tmp_path):
    def f(r):
        r["B"]["eval"]["10"]["agrees_with_A"] = False
    d = _tamper(quick_dir, tmp_path, "A3_low", f)
    with pytest.raises(checker.CheckError):
        checker.check(d, fast=True)


def test_mutation_undecided_gives_precision_wall(quick_dir, tmp_path):
    def f(r):
        r["A"]["required_bits"]["20"] = "UNDECIDED_AT_CAP"
    d = _tamper(quick_dir, tmp_path, "A2_bound", f)
    assert checker.check(d, fast=True)["scenarios"]["A2_bound"]["flags"]["precision_wall"]
