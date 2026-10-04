"""Nuclear State / Dynamics Gate V2 — CT-MQC survey prototype tests (fast)."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from nuclear_gate_v1.model import Grid, Params, adiabatic_states, dV_dR
from nuclear_gate_v2 import campaign, checker, ctmqc
from nuclear_gate_v2.table import AdiabaticTable

PKG = Path(campaign.__file__).resolve().parent
P = Params(19.0, 5.0, 3.1, 3.1, 1836.15267343)
XG = Grid(-32.0, 32.0, 128)


@pytest.fixture(scope="module")
def table():
    return AdiabaticTable(P, XG, 3, Grid(-9.0, 9.0, 256))


def test_table_adds_analytic_repulsion(table):
    pts = np.array([-8.7, -2.3, 0.4, 5.1])
    E, _ = adiabatic_states(pts, XG, P, 3)
    assert np.max(np.abs(table.E(pts) - E)) < 1e-4


def test_ehrenfest_force_equals_hellmann_feynman(table):
    R = np.array([-1.7])
    E, phi = adiabatic_states(R, XG, P, 3)
    # align the eigenvector sign gauge with the table (couplings d_0k must agree in sign)
    from nuclear_gate_v2.table import _matrix_elements
    d_direct = _matrix_elements(R, XG, P, 3)[2][0]
    d_table = table.D(R)[0]
    for k in (1, 2):
        if np.sign(d_direct[0, k]) != np.sign(d_table[0, k]):
            phi[0, k] = -phi[0, k]
    C = np.array([[0.8, 0.5j, 0.2 - 0.1j]])
    C = C / np.linalg.norm(C)
    F = ctmqc.force(C, table.E(R), table.G(R), table.D(R), None, None, P.M)
    psi = C[0] @ phi[0]
    direct = -np.sum(np.abs(psi) ** 2 * dV_dR(XG.points, np.full(XG.n, R[0]), P)) * XG.step
    assert F[0] == pytest.approx(direct, rel=2e-3)


def test_decoherence_term_conserves_norm_and_zero_net_transfer():
    n = 40
    R = np.linspace(-3, 3, n)
    W = np.exp(-R**2)
    W /= W.sum()
    C = np.zeros((n, 3), complex)
    C[:, 0] = np.sqrt(0.6)
    C[:, 1] = np.sqrt(0.4) * np.exp(1j * R)
    f = np.zeros((n, 3))
    f[:, 1] = 0.3 * R
    f[:, 0] = -0.1
    Q, _ = ctmqc.quantum_momentum(R, W, C, f)
    zero = np.zeros((n, 3))
    zd = np.zeros((n, 3, 3))
    dC = ctmqc.deriv_C(C, zero, zd, np.zeros(n), Q, f, P.M)
    dpop = 2 * np.real(np.conj(C) * dC)
    assert np.allclose(dpop.sum(axis=1), 0.0, atol=1e-15)          # per trajectory norm
    assert abs(np.sum(W * dpop[:, 1])) < 1e-15                      # zero net transfer (pair 0-1)


def test_quantum_momentum_of_gaussian_ensemble():
    from nuclear_gate_v1.dynamics import Scenario, wigner_nodes
    sc = Scenario("t", 1.0, 0.0, 0.8, None)
    R, _, W = wigner_nodes(sc, 14)
    C = np.zeros((R.size, 3), complex)
    C[:, 0] = 1
    Q, _ = ctmqc.quantum_momentum(R, W, C, np.zeros((R.size, 3)))
    s2 = (0.8 / 2) ** 2
    h = ctmqc.bandwidth(R, W)
    near = np.abs(R - 1.0) < 0.5
    assert np.allclose(Q[near, 0, 0], (R[near] - 1.0) / (2 * (s2 + h**2)), rtol=0.05, atol=1e-3)


def test_checker_is_standard_library_only():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("numpy", "scipy", "ctmqc", "q2", "table", "campaign", "bocl", "nuclear_gate_v1"):
        assert not any(bad in n for n in names), names


@pytest.fixture(scope="module")
def quick(tmp_path_factory):
    out = tmp_path_factory.mktemp("ng2")
    campaign.main(["--out", str(out), "--quick", "--processes", "1"])
    return json.loads((out / "results.json").read_text(encoding="utf-8"))


def test_quick_deterministic(tmp_path, quick):
    campaign.main(["--out", str(tmp_path), "--quick", "--processes", "1"])
    again = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))

    def strip(r):
        return [{k: (v if k != "cost" else None) for k, v in run.items()}
                for c in r["cells"] for run in c["runs"].values()]
    assert strip(again) == strip(quick)


def test_quick_checker_runs(quick):
    out = checker.check(quick)
    assert out["S1"] and out["S2r"] and out["S3"]


def test_mutation_s2r_rule_tamper(quick):
    bad = copy.deepcopy(quick)
    for c in bad["cells"]:
        if c["kind"] == "S2r":
            c["R0"] += 0.05
    with pytest.raises(checker.CheckError):
        checker.check(bad)


def test_mutation_protocol_swap(quick):
    bad = copy.deepcopy(quick)
    bad["seal"]["quick"] = False
    bad["protocol"]["scenarios"]["S2r_tunnelling"]["t_final"] = 999.0
    proto = json.loads((PKG / "protocol.json").read_text(encoding="utf-8"))
    with pytest.raises(checker.CheckError):
        checker.check(bad, proto)


def test_mutation_bocl_nonconvergence_refused(quick):
    bad = copy.deepcopy(quick)
    for c in bad["cells"]:
        if c["kind"] == "S2r":
            c["runs"]["Q"]["samples"][-1]["transmission"] = 0.5
            c["runs"]["Q_dt_fine"]["samples"][-1]["transmission"] = 0.5
            c["runs"]["Q_grid_fine"]["samples"][-1]["transmission"] = 0.5
            c["runs"]["BOCL_exact"]["transmission"] = 0.30
            c["runs"]["BOCL_exact_conv"]["transmission"] = 0.10
    assert checker.check(bad)["S2r"]["BOCL_exact"]["verdict"] == "REFUSED"


def test_mutation_machinery_failure_refuses_s1(quick):
    bad = copy.deepcopy(quick)
    bad["seal"]["quick"] = False  # loads V1 evidence; quick EHA cannot match the V1 Ehrenfest values
    out = checker.check(bad)
    s1 = out["S1"][0]
    assert s1["machinery_check"] is not None and not s1["machinery_check"]["pass"]
    assert set(s1["methods"]["CT"]["verdict"].values()) <= {"REFUSED", "NOT_APPLICABLE"}


def test_mutation_reference_edge_leak(quick):
    bad = copy.deepcopy(quick)
    bad["cells"][0]["runs"]["Q"]["samples"][1]["nuclear_edge"] = 1e-3
    s1 = checker.check(bad)["S1"][0]
    assert s1["reference"]["unsupported"] and not s1["reference"]["valid"]
