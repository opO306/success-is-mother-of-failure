"""Nuclear State / Dynamics Gate V1 — survey prototype tests (fast, quick grids)."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from nuclear_gate_v1 import campaign, checker, dynamics as dyn
from nuclear_gate_v1.model import (Grid, Params, adiabatic_states, dV_dR, kinetic_matrix,
                                   potential, soft, soft_deriv)

PKG = Path(campaign.__file__).resolve().parent
P = Params(19.0, 5.0, 3.1, 3.1, 1836.15267343)


def test_soft_limit_and_derivative():
    r = np.array([0.0, 1e-9, 1e-5, 0.3, 2.0, 7.0])
    assert soft(r, 2.0)[0] == pytest.approx(2.0 / (np.sqrt(np.pi) * 2.0))
    h = 1e-6
    rr = np.array([0.5, 1.7, 4.0])
    fd = (soft(rr + h, 3.1) - soft(rr - h, 3.1)) / (2 * h)
    assert np.allclose(soft_deriv(rr, 3.1), fd, atol=1e-8)
    assert abs(soft_deriv(np.array([0.0]), 3.1)[0]) == 0.0


def test_dV_dR_matches_finite_difference():
    x = np.linspace(-20, 20, 41)
    for R in (-6.3, -0.4, 2.2):
        h = 1e-6
        fd = (potential(x, R + h, P) - potential(x, R - h, P)) / (2 * h)
        assert np.allclose(dV_dR(x, np.full_like(x, R), P), fd, atol=1e-6)


def test_kinetic_matrix_equals_fft_kinetic():
    g = Grid(-10.0, 10.0, 64)
    v = np.exp(-g.points**2)
    direct = kinetic_matrix(g, 1.0) @ v
    fft = np.fft.ifft(g.k**2 / 2 * np.fft.fft(v)).real
    assert np.allclose(direct, fft, atol=1e-12)


def test_adiabatic_orthonormal_and_symmetric_surface():
    xg = Grid(-32.0, 32.0, 128)
    R = np.array([-3.0, 3.0])
    E, phi = adiabatic_states(R, xg, P, 3)
    for i in range(2):
        gram = phi[i] @ phi[i].T * xg.step
        assert np.allclose(gram, np.eye(3), atol=1e-10)
        assert np.all(np.diff(E[i]) > 0)
    assert E[0, 0] == pytest.approx(E[1, 0], abs=1e-9)  # Rl = Rr symmetry


def test_wigner_nodes_moments():
    sc = dyn.Scenario("t", -7.0, 2.0, 0.59, None)
    R, Pn, W = dyn.wigner_nodes(sc, 10)
    assert W.sum() == pytest.approx(1.0)
    assert np.sum(W * R) == pytest.approx(-7.0)
    assert np.sqrt(np.sum(W * (R + 7.0) ** 2)) == pytest.approx(0.59 / 2)
    assert np.sqrt(np.sum(W * (Pn - 2.0) ** 2)) == pytest.approx(1 / 0.59)


def test_s2_rule_on_synthetic_double_well():
    g = Grid(-9.0, 9.0, 361)
    V = (g.points**2 - 9.0) ** 2 / 1000.0
    s = campaign.s2_rule(g, V)
    assert s["R_a"] == pytest.approx(-3.0, abs=0.06) and s["R_b"] == pytest.approx(0.0, abs=0.06)
    assert s["barrier"] == pytest.approx(0.081, abs=1e-3) and s["applicable"]
    flat = campaign.s2_rule(g, g.points * 1e-6)
    assert not flat["applicable"]


@pytest.fixture(scope="module")
def quick(tmp_path_factory):
    out = tmp_path_factory.mktemp("ng")
    campaign.main(["--out", str(out), "--quick", "--processes", "1"])
    return json.loads((out / "results.json").read_text(encoding="utf-8"))


def test_quick_run_is_deterministic(tmp_path, quick):
    campaign.main(["--out", str(tmp_path), "--quick", "--processes", "1"])
    again = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    strip = lambda r: [{k: v for k, v in run.items() if k != "cost"}
                       for c in r["cells"] for s in c["scenarios"].values() for run in s["runs"].values()]
    assert strip(again) == strip(quick)


def test_quick_physics_invariants(quick):
    for cell in quick["cells"]:
        for sc in cell["scenarios"].values():
            q = sc["runs"]["Q"]
            assert max(abs(s["norm"] - 1) for s in q["samples"]) < 1e-10
            for m in ("BOQ", "BOCL"):
                assert sc["runs"][m]["samples"][-1]["P_exc"] == 0.0


def test_checker_does_not_import_producer():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(("." * node.level) + (node.module or ""))
    for bad in ("model", "dynamics", "campaign", "numpy", "scipy"):
        assert not any(bad in n for n in names), names


def test_checker_quick_verdict_structure(quick):
    out = checker.check(quick)
    sc = out["cells"][0]["scenarios"]["S1_slide"]
    assert sc["verdicts"]["BOQ"]["verdict"]["P_exc"] == "ABSENT_BY_CONSTRUCTION"
    assert sc["verdicts"]["BOCL"]["verdict"]["P_exc"] == "ABSENT_BY_CONSTRUCTION"


def test_mutation_bo_claims_transition_is_rejected(quick):
    bad = copy.deepcopy(quick)
    bad["cells"][0]["scenarios"]["S1_slide"]["runs"]["BOQ"]["samples"][-1]["P_exc"] = 0.3
    with pytest.raises(checker.CheckError):
        checker.check(bad)


def test_mutation_protocol_swap_is_rejected(quick):
    bad = copy.deepcopy(quick)
    bad["seal"]["quick"] = False
    proto = json.loads((PKG / "protocol.json").read_text(encoding="utf-8"))
    with pytest.raises(checker.CheckError):
        checker.check(bad, proto)


def test_mutation_edge_leak_gives_unsupported(quick):
    bad = copy.deepcopy(quick)
    runs = bad["cells"][0]["scenarios"]["S1_slide"]["runs"]
    runs["EH"]["samples"][3]["electron_edge"] = 1e-3
    v = checker.check(bad)["cells"][0]["scenarios"]["S1_slide"]["verdicts"]["EH"]["verdict"]
    assert v["electron_right"] in ("UNSUPPORTED", "REFUSED")
    runs["Q"]["samples"][2]["nuclear_edge"] = 1e-3
    v = checker.check(bad)["cells"][0]["scenarios"]["S1_slide"]
    assert v["reference"]["unsupported"]
    assert v["verdicts"]["EH"]["verdict"]["electron_right"] == "REFUSED"


def test_mutation_reference_norm_loss_refuses_everything(quick):
    bad = copy.deepcopy(quick)
    bad["cells"][0]["scenarios"]["S1_slide"]["runs"]["Q"]["samples"][-1]["norm"] = 0.99
    sc = checker.check(bad)["cells"][0]["scenarios"]["S1_slide"]
    assert not sc["reference"]["valid"]
    for m in ("EH", "BOQ", "BOCL"):
        assert sc["verdicts"][m]["verdict"]["electron_right"] == "REFUSED"


def test_mutation_distorted_value_detected(quick):
    good = checker.check(quick)["cells"][0]["scenarios"]["S1_slide"]
    bad = copy.deepcopy(quick)
    runs = bad["cells"][0]["scenarios"]["S1_slide"]["runs"]
    for k in ("EH", "EH_quad_conv"):
        runs[k]["samples"][-1]["electron_right"] = 0.9
    sc = checker.check(bad)["cells"][0]["scenarios"]["S1_slide"]
    if good["reference"]["valid"]:
        assert sc["verdicts"]["EH"]["verdict"]["electron_right"] == "DISTORTED"
    else:
        assert sc["verdicts"]["EH"]["verdict"]["electron_right"] == "REFUSED"
