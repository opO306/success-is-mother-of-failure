"""PRECISION_PILOT_A2T: the algebra evaluator is the repository loop with only the force swapped (and restored), bound
to the repository modules; frozen A1 parameters; campaign plan; checker independence."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest

from experiments.precision_pilot_a2t import campaign as C
from experiments.precision_pilot_a2t import checker as CK
from experiments.precision_pilot_a2t import evaluator_adapter as E

PKG = Path(E.__file__).resolve().parent


def test_algebra_pass_is_same_loop_with_force_swapped_and_restored():
    E.prepare("algebra")
    from exact_expression_gate_v1 import stream
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    a = E.run_pass("algebra", "A2_bound", 128, 5)
    assert stream.LI is LI and a["force_swap_restored"] is True
    o = E.run_pass("original", "A2_bound", 128, 5)
    assert a["outcome"] == o["outcome"] == "DECIDED" and a["cells"] == o["cells"]
    assert a["effective_p"] == 128 and a["completed_steps"] == 5
    for (a0, a1), (b0, b1) in zip(a["endpoints_scaled"], o["endpoints_scaled"]):
        assert F(a0) <= F(b1) and F(b0) <= F(a1)
    assert a["endpoints_scaled"] != o["endpoints_scaled"]          # a different formula, not the same computation


def test_prepare_binds_repository_modules_and_drops_vendor_path():
    info = E.prepare("algebra")
    root = Path(CK.ROOT)
    for m, tail in CK.MODULE_TAILS.items():
        assert CK._repo_module(info["modules"][m], tail), m
    assert not any("upstream" in p and "vendor" in p for p in sys.path)
    assert info["prepare_cpu_s"] >= 0 and str(root) in info["probe_file"]


def test_domain_guard_and_unknown_evaluator():
    with pytest.raises(ValueError):
        E.run_pass("algebra", "A2_bound", 63, 1)
    with pytest.raises(ValueError):
        E.prepare("reverse-rule-X")


def test_frozen_params_are_a1_params():
    prm = json.loads((PKG / "frozen_policy_params_a1.json").read_text(encoding="utf-8"))
    core = {k: v for k, v in prm.items() if k != "policy_hash"}
    assert hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest() == prm["policy_hash"] == CK.POLICY_HASH
    assert prm["s1"] == 110


def test_campaign_order_runs_every_combination_once_per_rep():
    for rep in range(3):
        assert sorted(C.order(rep)) == sorted(C.COMBOS) and len(C.order(rep)) == 7
    assert {e for e, _ in C.COMBOS} == {"original", "algebra"} and ("original", "P1") not in C.COMBOS
    assert C.COMBOS == CK.COMBOS


def test_checker_imports_no_executor_module():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    banned = ("policies", "runner", "campaign", "evaluator_adapter", "harness", "probe", "transform_checks")
    assert not any(n.split(".")[-1] in banned for n in names), names
