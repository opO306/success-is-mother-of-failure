"""Full-span algebra, fail-closed controls and adversarial bracket checks."""
import ast
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from electronic_pilot.minimum_bracket.checker import bracket, controls, valid
from electronic_pilot.minimum_bracket.evaluator import guard, singlet, transform
from electronic_pilot.minimum_bracket.postrun.action_audit import action

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT/"electronic_pilot/minimum_bracket/protocol.json").read_text())


def row(r=1.5, e=-1.1):
    return dict(R_bohr=r, accepted=True, failure_stage=None, basis="cc-pVQZ",
                basis_size=60, singlet_dimension=1830, electrons=2, sector=SPEC["sector"],
                charge=0, multiplicity=1, spherical=True,
                positions_bohr=[[0., 0., -r/2], [0., 0., r/2]],
                overlap_eigenvalues=[0.1]*60, Smin=0.1, condition=1,
                orthonormalization_error=1e-14, transformed_h_asymmetry=1e-14,
                transformed_eri_symmetry=dict(ij_swap_max=1e-14, kl_swap_max=1e-14, pair_swap_max=1e-14),
                singlet_asymmetry=1e-14, eigen_residual_l2=1e-14, vector_norm_error=1e-15,
                nuclear_repulsion_hartree=1/r, electronic_energy_hartree=e-1/r,
                total_energy_hartree=e)


def historical(rows):
    return {"rows": [dict(basis="cc-pVQZ", R_bohr=x["R_bohr"],
                         original=dict(accepted=True, energy=x["total_energy_hartree"]),
                         paths=[dict(overlap_eigenvalues=x["overlap_eigenvalues"])]) for x in rows]}


@pytest.mark.parametrize("n", [1, 2, 4])
def test_singlet_against_explicit_projection(n):
    h = (np.arange(n*n).reshape(n, n)+1).astype(np.longdouble)
    g = (np.arange(n**4).reshape((n,)*4)/17).astype(np.longdouble)
    ordered = np.empty((n*n, n*n), dtype=np.longdouble)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                for l in range(n):
                    ordered[i*n+j, k*n+l] = h[i, k]*(j == l)+h[j, l]*(i == k)+g[i, k, j, l]
    pairs = [(i, j) for i in range(n) for j in range(i, n)]
    p = np.zeros((n*n, len(pairs)), dtype=np.longdouble)
    for col, (i, j) in enumerate(pairs):
        if i == j:
            p[i*n+j, col] = 1
        else:
            p[i*n+j, col] = p[j*n+i, col] = 1/np.sqrt(np.longdouble(2))
    np.testing.assert_allclose(singlet(h, g), p.T@ordered@p, rtol=1e-14, atol=1e-14)


@pytest.mark.parametrize("coordinate_path", ["cholesky", "generalized_h"])
def test_full_transform_against_scalar_sums_and_raw_asymmetry(coordinate_path):
    s = np.array([[1., .3], [.3, 1.]])
    h = np.array([[1., 2.], [3., 4.]])
    g = np.arange(16, dtype=float).reshape((2,)*4)
    c, sh, hh, gg = transform(s, h, g, coordinate_path)
    np.testing.assert_allclose(sh, np.eye(2), atol=2e-15)
    x = c.astype(np.longdouble)
    expected = np.zeros((2,)*4, dtype=np.longdouble)
    for a, b, d, e in np.ndindex((2,)*4):
        for p, q, r, t in np.ndindex((2,)*4):
            expected[a, b, d, e] += x[p, a]*x[q, b]*x[r, d]*x[t, e]*g[p, q, r, t]
    np.testing.assert_allclose(gg, expected, rtol=1e-14, atol=1e-14)
    assert np.max(np.abs(hh-hh.T)) > .5
    assert np.max(np.abs(gg-gg.swapaxes(0, 1))) > .5
    assert c.shape == (2, 2) and np.linalg.det(c) != 0


@pytest.mark.parametrize("key,value", [
    ("accepted", False), ("basis_size", 59), ("singlet_dimension", 1829),
    ("sector", "triplet"), ("electrons", 1), ("spherical", False),
    ("multiplicity", 3), ("charge", 1), ("total_energy_hartree", float("nan")),
    ("nuclear_repulsion_hartree", 0), ("eigen_residual_l2", 2e-9),
    ("singlet_asymmetry", 2e-10), ("transformed_h_asymmetry", 2e-10),
    ("orthonormalization_error", 2e-10), ("failure_stage", "singlet_hermiticity")])
def test_invalid_result_cannot_form_minimum(key, value):
    rows = [row(1.3, -1.16), row(1.4, -1.17), row(1.5, -1.16)]
    rows[0][key] = value
    assert not valid(rows[0], SPEC)
    assert bracket(rows, {"status": "PASS"}, SPEC)["status"] == "UNRESOLVED"


def test_control_equivalence_and_tampered_energy_spectrum():
    rows = [row(r) for r in SPEC["controls_bohr"]]
    old = historical(rows)
    assert controls(rows, old, SPEC)["status"] == "PASS"
    bad = copy.deepcopy(rows)
    bad[0]["total_energy_hartree"] += 1e-8
    bad[0]["electronic_energy_hartree"] += 1e-8
    assert controls(bad, old, SPEC)["status"] == "FAIL"
    bad = copy.deepcopy(rows)
    bad[0]["overlap_eigenvalues"] = [.100001]*60
    assert controls(bad, old, SPEC)["status"] == "FAIL"
    assert controls(rows[:-1], old, SPEC)["status"] == "FAIL"
    assert controls(rows+[rows[0]], old, SPEC)["status"] == "FAIL"


def test_bracket_gaps_missing_duplicate_and_failed_control():
    rows = [row(1.3, -1.16), row(1.4, -1.17), row(1.5, -1.165)]
    answer = bracket(rows, {"status": "PASS"}, SPEC)
    assert answer["status"] == "PASS"
    assert answer["E13_minus_E14_hartree"] > 0
    assert answer["E15_minus_E14_hartree"] > 0
    assert bracket(rows[:-1], {"status": "PASS"}, SPEC)["status"] == "UNRESOLVED"
    assert bracket(rows+[rows[0]], {"status": "PASS"}, SPEC)["status"] == "UNRESOLVED"
    assert bracket(rows, {"status": "FAIL"}, SPEC)["status"] == "UNRESOLVED"
    rows[1] = row(1.4, -1.15)
    assert bracket(rows, {"status": "PASS"}, SPEC)["status"] == "NO_SAMPLED_MINIMUM_AT_1_4"


@pytest.mark.parametrize("key,value,failure", [
    ("basis_size", 59, "basis_dimension"), ("Smin", 1e-11, "overlap_floor"),
    ("orthonormalization_error", 2e-10, "orthonormalization"),
    ("transformed_h_asymmetry", 2e-10, "h_hermiticity"),
    ("singlet_asymmetry", 2e-10, "singlet_hermiticity")])
def test_matrix_guard_refuses_before_energy(key, value, failure):
    x = row()
    x[key] = value
    assert guard(x, SPEC, "matrix") == failure


def test_unmodified_tolerances_and_import_independence():
    parent = json.loads((ROOT/"electronic_pilot/numerical_cause/protocol.json").read_text())
    for key in ("overlap_min_eigenvalue_floor", "orthonormalization_max_norm", "hermitian_max_asymmetry",
                "eigen_residual_max_l2_hartree", "vector_norm_error_max"):
        assert SPEC[key] == parent[key]
    assert SPEC["same_problem_energy_abs_hartree"] == parent["comparison_energy_abs_max_hartree"]
    path = ROOT/"electronic_pilot/minimum_bracket"
    for name in ("evaluator.py", "checker.py"):
        tree = ast.parse((path/name).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [x.name for node in ast.walk(tree) if isinstance(node, ast.Import) for x in node.names]
        assert not any(x and x.startswith(("pyscf", "engine", "a_reference", "electronic_pilot.solver", "electronic_pilot.numerical_cause")) for x in imports)
        if name == "checker.py":
            assert not any(x and x.startswith(("psi4", "numpy", "scipy", "electronic_pilot.minimum_bracket.evaluator")) for x in imports)


def test_independent_product_action_detects_energy_and_vector_fault():
    h = np.diag([-1., -.4]).astype(np.longdouble)
    g = np.zeros((2,)*4, dtype=np.longdouble)
    v = np.array([1., 0., 0.])
    assert action(h, g, v, -2.)["full_product_residual_l2"] == 0
    assert action(h, g, v, -1.9)["full_product_residual_l2"] > .09
    assert action(h, g, np.array([.8, .6, 0]), -2.)["full_product_residual_l2"] > .3
    with pytest.raises(ValueError):
        action(h, g, v[:-1], -2.)
