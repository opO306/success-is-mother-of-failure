"""Multiparticle Rounding Gate V0 — law, physics-panel and checker tests (fast)."""

from __future__ import annotations

import ast
import copy
import json
from fractions import Fraction as Q
from pathlib import Path

import pytest

from multiparticle_rounding_v0 import campaign, checker, laws, physics as ph

PKG = Path(laws.__file__).resolve().parent


def test_rounding_matches_fixedpoint_profile():
    for k in range(-41, 42):
        x = Q(k, 8)
        assert laws.rhe(x) == ph.MOM.from_exact(x * ph.UNIT)
        assert laws.rhe(-x) == -laws.rhe(x)


def test_designer_examples():
    coll = {(1, 0): Q(2, 5), (2, 0): Q(2, 5), (3, 0): Q(2, 5)}
    assert laws.law_P(4, coll) == (0, 0, 0, 0)          # pair rounding loses the collective 1.2
    assert laws.law_T(4, coll) == (1, 0, 0, 0)          # total rounding keeps it, breaks conservation
    split = {(0, 1): Q(2, 5), (0, 2): Q(2, 5)}
    assert sum(laws.law_T(3, split)) == -1
    assert laws.law_P(2, {(0, 1): Q(3, 5)}) == laws.law_T(2, {(0, 1): Q(3, 5)}) == (-1, 1)


def test_hamilton_conserves_or_stops():
    for t, a in [([1, 0, 0], [Q(4, 5), Q(-2, 5), Q(-2, 5)]), ([1, 0, 0, 0], [Q(6, 5)] + [Q(-2, 5)] * 3)]:
        r = laws.hamilton(t, a)
        assert r == "STOP" or sum(r) == 0


def test_n2_physics_equals_c1b1():
    pos = [(Q(0), Q(0), Q(0)), ph.unit_scaled((3, 1, 2), Q(7))]
    J = ph.C.impulse(ph.rel(*pos), ph.KICK, ph.MOM)
    ref = [tuple(-x for x in J), tuple(J)]
    assert ph.law_P(pos) == ref
    assert ph.law_T(pos)[0] == ref
    assert ph.law_C(pos)[0] == ref


def test_checker_standard_library_only():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("laws", "physics", "campaign", "a_reference", "a_numeric", "numpy"):
        assert not any(bad in n for n in names), names


@pytest.fixture(scope="module")
def quick(tmp_path_factory):
    out = tmp_path_factory.mktemp("mr")
    campaign.main(["--out", str(out), "--quick"])
    return json.loads((out / "results.json").read_text(encoding="utf-8"))


def test_quick_checks_pass(quick):
    s = checker.check(quick)
    assert s["N2_equal_to_C1B1"] == {"P": True, "T": True, "C": True}
    for m in s["clusters"].values():
        assert m["P"]["conserving"]


def test_mutation_synthetic_result_detected(quick):
    bad = copy.deepcopy(quick)
    bad["synthetic"]["S_collective"]["P"]["result"] = [1, 0, 0, -1]
    with pytest.raises(checker.CheckError):
        checker.check(bad, skip_exhaustive=True)


def test_mutation_exhaustive_stats_detected(quick):
    bad = copy.deepcopy(quick)
    bad["exhaustive_N3"]["T"]["nonconserving"] = 0
    with pytest.raises(checker.CheckError):
        checker.check(bad)


def test_mutation_T_not_a_rounding_detected(quick):
    bad = copy.deepcopy(quick)
    row = bad["physics_clusters"]["chain_7.5"]
    row["T"][0][0] += 2
    with pytest.raises(checker.CheckError):
        checker.check(bad, skip_exhaustive=True)


def test_mutation_permutation_mismatch_detected(quick):
    bad = copy.deepcopy(quick)
    bad["synthetic"]["S_split"]["perm"]["mismatches"]["T"] = 1
    with pytest.raises(checker.CheckError):
        checker.check(bad, skip_exhaustive=True)
