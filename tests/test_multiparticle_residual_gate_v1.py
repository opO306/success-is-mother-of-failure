"""Multiparticle Residual / Carry Gate V1 — executor, checker and mutation tests (fast)."""

from __future__ import annotations

import ast
import copy
import json
from fractions import Fraction as Q
from pathlib import Path

import pytest

from multiparticle_residual_gate_v1 import campaign, checker, ledger as LG

PKG = Path(LG.__file__).resolve().parent


def test_designer_example_carry():
    s = LG.apply_U(LG.State([Q(0)] * 4), [("pair", k, 0, Q(2, 5)) for k in (1, 2, 3)])
    assert s.P[0] == 1 and s.r[0] == Q(1, 5) and s.p()[0] == Q(6, 5)
    assert sum(s.p()) == 0


def test_cancellation_leaves_no_ghost_residual():
    for apply in (LG.apply_U, LG.apply_L):
        s = apply(LG.State([Q(0)] * 3), [("pair", 1, 0, Q(2, 5)), ("pair", 2, 0, Q(-2, 5))])
        assert s.P[0] == 0 and s.r[0] == 0


def test_u_and_l_differ_only_in_representation():
    e = [("pair", 1, 0, Q(3, 5)), ("pair", 2, 0, Q(-3, 5)), ("pair", 3, 0, Q(3, 5))]
    u = LG.apply_U(LG.State([Q(0)] * 4), e)
    l = LG.apply_L(LG.State([Q(0)] * 4), e)
    assert u.p() == l.p()
    assert (u.P[0], u.r[0]) == (0, Q(3, 5)) and (l.P[0], l.r[0]) == (1, Q(-2, 5))  # same p = 3/5


def test_drift_uses_residual():
    s = LG.State([Q(0)])
    s.P, s.r = [1], [Q(1, 5)]
    assert LG.drift_grid([0], s, Q(1, 2)) == [1]
    assert LG.drift_grid([0], s, Q(1, 2), P_only=True) == [0]


def test_external_ledger_conserves():
    s = LG.apply_L(LG.State([Q(0)] * 2), [("pair", 0, 1, Q(3, 5)), ("ext", 1, Q(-3, 5), "wall")])
    assert sum(s.p()) + sum(s.ext.values()) == 0


def test_checker_independent_of_executor():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("ledger", "campaign", "multiparticle_rounding_v0", "a_reference", "numpy"):
        assert not any(bad in n for n in names), names


@pytest.fixture(scope="module")
def quick(tmp_path_factory):
    out = tmp_path_factory.mktemp("rc")
    campaign.main(["--out", str(out), "--quick"])
    return json.loads((out / "results.json").read_text(encoding="utf-8"))


def test_quick_verdict(quick):
    v = checker.check(quick)
    assert v["equivalence"] == "SAME_SEMANTICS_DIFFERENT_NORMALIZATION"
    assert all(v["core_conditions"].values())


def test_mutation_lost_collective_gives_C(quick):
    bad = copy.deepcopy(quick)
    row = bad["named"]["T1_repeat_0.4x3"]
    for k in ("U", "L"):
        row[k]["P"][0] = 0
        row[k]["p"][0] = row[k]["r"][0]
    assert checker.check(bad)["verdict"].startswith("C")


def test_mutation_inconsistent_snapshot_rejected(quick):
    bad = copy.deepcopy(quick)
    bad["named"]["T5_closed_pair"]["U"]["r"][0] = "1/7"
    with pytest.raises(checker.CheckError):
        checker.check(bad)


def test_mutation_negative_control_blind_rejected(quick):
    bad = copy.deepcopy(quick)
    bad["T11"]["grid_Ponly"] = bad["T11"]["grid_U_L"]
    bad["T11"]["exact_Ponly"] = bad["T11"]["exact_U_L"]
    with pytest.raises(checker.CheckError):
        checker.check(bad)


def test_mutation_drift_ignores_residual_gives_D(quick):
    bad = copy.deepcopy(quick)
    bad["T11"]["grid_U_L"] = 0
    assert checker.check(bad)["verdict"].startswith("D")


def test_mutation_order_dependence_flagged(quick):
    bad = copy.deepcopy(quick)
    bad["named"]["T3_partial"]["T8"]["U_mismatch"] = 1
    assert not checker.check(bad)["core_conditions"]["C4"]
