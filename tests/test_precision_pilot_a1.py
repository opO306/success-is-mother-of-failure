"""PRECISION_PILOT_A1: selector logic on exact mock oracles, policy rules, ledger claims, registry guards, and the
agreement of the checker's independent rule implementation with the runner's."""

from __future__ import annotations

import ast
import random
from fractions import Fraction as F
from pathlib import Path

import pytest

from experiments.precision_pilot_a1 import checker as CK
from experiments.precision_pilot_a1 import evaluator_adapter as E
from experiments.precision_pilot_a1 import policies as P

PKG = Path(P.__file__).resolve().parent


def mock_pass(p, x, T=1):
    """D01-style oracle: one observed component, enclosure [x - 2^-p, x + 2^-p] on the scale of the rounding grid."""
    lo, hi = x - F(1, 2 ** p), x + F(1, 2 ** p)
    decided = P.rhe(lo) == P.rhe(hi)
    return {"requested_p": p, "outcome": "DECIDED" if decided else "UNDECIDED_AT_PRECISION", "completed_steps": T,
            "endpoints_scaled": [[str(lo), str(hi)]], "cells": [P.rhe(lo)] if decided else None}


X = F(1, 2) + 3 * F(1, 2 ** 130)


def test_mock_128_undecided_129_decided_256_decided():
    assert mock_pass(128, X)["outcome"] == "UNDECIDED_AT_PRECISION"
    assert mock_pass(129, X)["outcome"] == "DECIDED"
    assert mock_pass(256, X)["outcome"] == "DECIDED"


def test_256_success_does_not_fail_129_and_untried_stay_untried():
    led = P.ledger([mock_pass(128, X), mock_pass(256, X)])
    assert led["states"] == {"128": "UNDECIDED_AT_PRECISION", "256": "DECIDED"}
    assert "129" not in led["states"] and led["claim"] == "LOWEST_SUCCESS_OBSERVED"


def test_policy_can_propose_and_run_non_grid_129():
    p = P.next_p("P1", {"s1": 129, "lines": {}, "scenario": "A2_bound"}, [], 1)
    assert p == 129 and 129 not in P.GRID
    nxt = P.p2_next(mock_pass(128, X), 1)                  # width rule from the 128 enclosure: an integer, not a grid value
    assert isinstance(nxt, int) and nxt > 128 and nxt not in P.GRID


def test_non_monotone_mock_does_not_copy_a_higher_failure_downward():
    hist = [{"requested_p": 128, "outcome": "UNDECIDED_AT_PRECISION"}, {"requested_p": 129, "outcome": "DECIDED"},
            {"requested_p": 130, "outcome": "UNDECIDED_AT_PRECISION"}]
    led = P.ledger(hist)
    assert led["lowest_success"] == 129 and led["claim"] == "LOWEST_SUCCESS_OBSERVED"
    assert led["untried_below_lowest"] == 129 - 64 - 1


def test_min_claim_only_with_every_lower_integer_recorded():
    hist = [{"requested_p": p, "outcome": "UNDECIDED_AT_PRECISION"} for p in range(64, 129)]
    hist.append({"requested_p": 129, "outcome": "DECIDED"})
    assert P.ledger(hist)["claim"] == "MIN_SUCCESS_IN_DECLARED_DOMAIN"
    del hist[10]
    assert P.ledger(hist)["claim"] == "LOWEST_SUCCESS_OBSERVED"


def test_conflicting_outcomes_for_one_p_are_marked():
    led = P.ledger([{"requested_p": 100, "outcome": "DECIDED"}], [{"requested_p": 100, "outcome": "UNDECIDED_AT_PRECISION"}])
    assert led["states"]["100"] == "RESULT_CONFLICT"


def test_p0_p1_p3_sequences_and_cap():
    h = []
    seq = []
    for _ in range(12):
        n = P.next_p("P0", {}, h, 100)
        if n is None or n == "CAP":
            break
        seq.append(n)
        h.append({"requested_p": n, "outcome": "UNDECIDED_AT_PRECISION", "completed_steps": 100})
    assert seq == P.GRID and P.next_p("P0", {}, h, 100) is None
    prm = {"s1": 150, "lines": {"A3_high": ["100", "1/25"]}, "scenario": "A3_high"}
    assert P.next_p("P1", prm, [], 5) == 150
    assert P.next_p("P1", prm, [{"requested_p": 150, "outcome": "UNDECIDED_AT_PRECISION"}], 5) == 192
    assert P.next_p("P3", prm, [], 1000) == 100 + 40 + 8
    big = [{"requested_p": 1024, "outcome": "DOMAIN_UNPROVEN", "completed_steps": 10}]
    assert P.next_p("P2", {}, big, 10000) == "CAP"


def test_p2_domain_stop_rule():
    last = {"requested_p": 128, "outcome": "DOMAIN_UNPROVEN", "completed_steps": 4570}
    assert P.p2_next(last, 10000) == -((-128 * 10000) // 4570) + 8


def test_training_freezes_median_and_lines():
    h = lambda p: [{"requested_p": p, "outcome": "DECIDED"}]  # noqa: E731
    runs = {("A2_bound", 200): h(100), ("A2_bound", 2000): h(160), ("A3_high", 200): h(110),
            ("A3_high", 2000): h(190), ("A3_low", 200): h(96), ("A3_low", 2000): h(130)}
    prm, digest = P.train(runs)
    assert prm["s1"] == 120 and prm["lines"]["A2_bound"] == [str(F(100) - F(60, 1800) * 200), str(F(60, 1800))]
    assert CK.my_train(runs) == (prm["s1"], prm["lines"]) and len(digest) == 64


def test_registry_guards():
    with pytest.raises(NotImplementedError):
        E.run_pass("algebra", "A2_bound", 96, 1)
    with pytest.raises(ValueError):
        E.run_pass("original", "A2_bound", 63, 1)
    with pytest.raises(ValueError):
        E.run_pass("original", "A2_bound", 1025, 1)


def _random_history(rnd, pol, prm, T):
    hist = []
    for _ in range(6):
        n = P.next_p(pol, prm, hist, T)
        if n is None or n == "CAP":
            break
        o = rnd.choice(["UNDECIDED_AT_PRECISION", "DOMAIN_UNPROVEN", "UNDECIDED_AT_PRECISION"])
        rec = {"requested_p": n, "outcome": o, "completed_steps": rnd.randint(1, T - 1) if o == "DOMAIN_UNPROVEN" else T}
        if o == "UNDECIDED_AT_PRECISION":
            c = F(rnd.randint(1, 10 ** 6), 1000)
            w = F(rnd.randint(1, 10 ** 6), 10 ** rnd.randint(3, 30))
            rec["endpoints_scaled"] = [[str(c - w), str(c + w)], ["7", "7"]]
        hist.append(rec)
    return hist


def test_checker_rule_implementation_agrees_with_runner_and_catches_forgery():
    rnd = random.Random(5)
    prm = {"s1": 133, "lines": {"A2_bound": ["90", "3/100"]}}
    for _ in range(200):
        pol, T = rnd.choice(["P0", "P1", "P2", "P3"]), rnd.choice([100, 1000, 10000])
        hist = _random_history(rnd, pol, dict(prm, scenario="A2_bound"), T)
        for i in range(len(hist) + 1):
            assert CK.my_next(pol, prm, "A2_bound", hist[:i], T) == P.next_p(pol, dict(prm, scenario="A2_bound"), hist[:i], T)
    hist = _random_history(rnd, "P2", dict(prm, scenario="A2_bound"), 1000)
    if len(hist) >= 2:
        forged = [dict(h) for h in hist]
        forged[1]["requested_p"] += 1
        assert CK.my_next("P2", prm, "A2_bound", forged[:1], 1000) != forged[1]["requested_p"]


def test_checker_imports_no_executor_module():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    assert not any(n.split(".")[-1] in ("policies", "runner", "campaign", "evaluator_adapter") for n in names)
