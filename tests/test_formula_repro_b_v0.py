"""FORMULA_REPRO_B_V0: identity of the upstream copy, constants, and harness behaviour (no long runs here)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path

import a_reference.ar2_lang2024 as REPO_L

HERE = Path(__file__).resolve().parents[1] / "experiments" / "formula_repro_b_v0"
UP = HERE / "upstream"


def test_upstream_copy_is_byte_identical_to_its_sha256sums():
    sums = json.loads((UP / "SHA256SUMS.json").read_text(encoding="utf-8"))
    present = [k for k in sums if (UP / k).exists()]
    assert {"probe.py", "test_probe.py", "vendor/exact_expression_gate_v0/lang_iv.py",
            "vendor/a_reference/ar2_lang2024.py"} <= set(present)
    for k in present:
        assert hashlib.sha256((UP / k).read_bytes()).hexdigest() == sums[k], k


def _vendor_constants():
    spec = importlib.util.spec_from_file_location("vendor_ar2_excerpt", UP / "vendor/a_reference/ar2_lang2024.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_vendor_constants_equal_repository_constants():
    V = _vendor_constants()
    assert V.R_MIN_BOHR == REPO_L.R_MIN_BOHR
    assert V.COMPONENTS == REPO_L.COMPONENTS
    assert V.RET_A == REPO_L.RET_A and V.RET_B == REPO_L.RET_B


def test_vendor_gate_files_equal_repository_files():
    root = HERE.parents[1]
    for f in ("exact_expression_gate_v0/lang_iv.py", "exact_expression_gate_v1/common.py",
              "exact_expression_gate_v1/stream.py"):
        a = (UP / "vendor" / f).read_bytes().replace(b"\r\n", b"\n")
        b = (root / f).read_bytes().replace(b"\r\n", b"\n")
        assert a == b, f


def test_rearrangement_applicability_condition():
    assert all(b > 0 for b in REPO_L.RET_B)      # den(R) = 1 + sum RET_B R^(m+1) >= 1 for R > 0
    assert REPO_L.R_MIN_BOHR > 0


def test_harness_defers_program_only_in_memory():
    from experiments.formula_repro_b_v0 import harness as H
    src_before = (UP / "probe.py").read_bytes()
    P = H.load_probe()
    assert P.PROGRAM is None
    assert (UP / "probe.py").read_bytes() == src_before
    assert H.COMPILED == {"original": False, "cache": "cache", "algebra": True}


def test_checker_imports_no_harness():
    import ast
    tree = ast.parse((HERE / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    assert not any(n.split(".")[-1] in ("harness", "campaign", "transform_checks", "probe") for n in names)
