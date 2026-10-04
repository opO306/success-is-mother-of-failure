import copy
import json
from pathlib import Path

import numpy as np
import pytest

from electronic_pilot.sector_panel.contract import dimension, validate, validate_charge_assertion
from electronic_pilot.sector_panel.evaluator import matrix
from electronic_pilot.sector_panel.action_check import action
from electronic_pilot.sector_panel.checker import valid, panel


SPEC = json.loads((Path(__file__).parents[1]/"electronic_pilot/sector_panel/protocol.json").read_text(encoding="utf-8"))


def test_charge_is_derived_and_conflicting_assertion_refused():
    case = SPEC["cases"]["pair_singlet_1.4"]
    assert validate(case) == 0
    assert validate_charge_assertion(case, 0) == 0
    with pytest.raises(ValueError, match="charge assertion conflicts"):
        validate_charge_assertion(case, 1)
    assert validate(SPEC["cases"]["pair_doublet_1.4"]) == 1
    assert validate(SPEC["cases"]["atom"]) == 0
    assert validate(SPEC["cases"]["ghost_20"]) == 0


@pytest.mark.parametrize("key", ["charge", "Q", "bond_id", "molecule_id", "reaction_id", "H2"])
def test_unallowed_authority_refused(key):
    case = copy.deepcopy(SPEC["cases"]["pair_singlet_1.4"])
    case[key] = 1
    with pytest.raises(ValueError, match="unknown/missing authority"):
        validate(case)


@pytest.mark.parametrize("change", [{"electrons": 1, "sector": "singlet"}, {"electrons": 2, "sector": "doublet"}, {"electrons": 3}, {"electrons": True}, {"basis": "cc-pVQZ"}, {"law": "bond_table"}])
def test_invalid_sector_or_model_refused(change):
    case = copy.deepcopy(SPEC["cases"]["pair_singlet_1.4"])
    case.update(change)
    with pytest.raises(ValueError):
        validate(case)


def test_nonfinite_and_coincident_positions_refused():
    case = copy.deepcopy(SPEC["cases"]["pair_singlet_1.4"])
    case["nuclei"][0]["position_bohr"][2] = float("nan")
    with pytest.raises(ValueError):
        validate(case)
    case["nuclei"][0]["position_bohr"] = case["nuclei"][1]["position_bohr"]
    with pytest.raises(ValueError):
        validate(case)


def test_full_sector_dimensions_and_onsite_fermion_exclusion():
    assert [dimension(28, n, s) for n, s in ((1, "doublet"), (2, "singlet"), (2, "triplet"))] == [28, 406, 378]
    h = np.diag(np.array([-0.5, 0.2], dtype=np.longdouble))
    g = np.zeros((2,)*4, dtype=np.longdouble)
    assert np.linalg.eigvalsh(np.asarray(matrix(h, g, 2, "singlet"), dtype=float))[0] == -1
    assert np.linalg.eigvalsh(np.asarray(matrix(h, g, 2, "triplet"), dtype=float))[0] == pytest.approx(-0.3)
    assert matrix(h, g, 1, "doublet").shape == (2, 2)


@pytest.mark.parametrize("sector", ["singlet", "triplet"])
def test_projected_matrix_equals_explicit_full_product_operator(sector):
    m = 3
    h = np.array([[-0.7, .1, .2], [.1, -.2, -.03], [.2, -.03, .5]], dtype=np.longdouble)
    # Explicit deterministic pair-symmetric tensor, no random draw.
    g = np.fromfunction(lambda a, b, c, d: ((a+b+1)*(c+d+1))*.017, (m,)*4).astype(np.longdouble)
    product = np.zeros((m*m, m*m), dtype=np.longdouble)
    for a in range(m):
        for b in range(m):
            for c in range(m):
                for d in range(m):
                    product[a*m+b, c*m+d] = h[a, c]*(b == d)+h[b, d]*(a == c)+g[a, c, b, d]
    columns = []
    for a in range(m):
        for b in range(a if sector == "singlet" else a+1, m):
            v = np.zeros((m, m), dtype=np.longdouble)
            if a == b:
                v[a, b] = 1
            else:
                v[a, b] = 1/np.sqrt(np.longdouble(2))
                v[b, a] = v[a, b]*(1 if sector == "singlet" else -1)
            columns.append(v.ravel())
    projection = np.array(columns).T
    built = matrix(h, g, 2, sector)
    assert np.max(np.abs(built-projection.T@product@projection)) < 32*np.finfo(np.longdouble).eps
    e, v = np.linalg.eigh(np.asarray(built, dtype=float))
    check = action(h, g, v[:, 0], e[0], 2, sector)
    assert check["product_residual_l2"] < 1e-14
    assert check["exchange_parity_error"] == 0
    # A coupling mutation must be visible to a separate product action.
    bad = h.copy(); bad[0, 0] += .1
    assert action(bad, g, v[:, 0], e[0], 2, sector)["product_residual_l2"] > 1e-5


def test_missing_or_duplicate_rows_do_not_pass():
    assert panel({"rows": []}, SPEC)["P1"] == "UNRESOLVED"
    assert panel({"rows": []}, SPEC)["P2"] == "UNRESOLVED"
    assert not valid({}, SPEC["cases"]["atom"], SPEC)


def test_sealed_grid_no_qz_and_same_law():
    assert SPEC["grid_bohr"] == [.8, 1.4, 2., 4., 20.]
    assert len(SPEC["cases"]) == 18
    assert len(set(SPEC["execution_order"])) == 18
    assert set(SPEC["execution_order"]) == set(SPEC["cases"])
    for case in SPEC["cases"].values():
        validate(case)
        assert case["basis"] == "cc-pVTZ"
