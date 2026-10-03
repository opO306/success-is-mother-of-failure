import json
from pathlib import Path
import pytest
from electronic_pilot.reconstruction_v0.policy import (
    overall_status, compare_interval, classifications, require_comparison_context, signed_budget,
)
from electronic_pilot.reconstruction_v0.measure import retained_rank,exact_guard
import numpy as np


def test_exact_guard_and_rank_detect_corrupt_inputs():
    s=np.eye(3);c=np.eye(3)
    assert exact_guard(s,c)['status']=='PASS'
    c[1,1]+=1e-8
    assert exact_guard(s,c)['status']=='FAIL'
    c[1,1]=0
    with pytest.raises(ValueError):retained_rank(c)
    assert retained_rank(np.eye(3))['actual_retained_rank']==3


@pytest.mark.parametrize("n,s,result", [
    ({"orth":"PASS"},{"inversion":"PASS"},"ACCEPTED"),
    ({"orth":"PASS"},{"inversion":"FAIL"},"REFUSED"),
    ({"orth":"FAIL"},{"inversion":"PASS"},"REFUSED"),
    ({"orth":"UNRESOLVED"},{"inversion":"PASS"},"UNRESOLVED"),
    ({"orth":"PASS"},{},"UNRESOLVED"),
    ({},{"inversion":"PASS"},"UNRESOLVED"),
    ({"orth":True},{"inversion":"PASS"},"UNRESOLVED"),
])
def test_acceptance_never_ignores_failed_or_missing_spatial_guard(n,s,result):
    assert overall_status(n,s)==result


def test_uncertainty_and_signed_difference_are_not_erased():
    r=compare_interval("-2","-2.0000000005")
    assert r["signed_difference"]=="5E-10" and r["measured_relation"]=="WITHIN_BAND"
    assert r["uncertainty_relation"]=="UNRESOLVED"
    assert compare_interval("0","0.0000000005","0","0")["uncertainty_relation"]=="WITHIN_BAND"
    assert compare_interval("0","0.0000000005","1e-9","0")["uncertainty_relation"]=="UNRESOLVED"
    assert compare_interval("0","0.000000003","1e-10","1e-10")["uncertainty_relation"]=="OUTSIDE_BAND"
    with pytest.raises(ValueError): compare_interval("0","0","-1","0")
    with pytest.raises(ValueError): compare_interval("NaN","0")


@pytest.mark.parametrize("count",[0,1,2])
def test_all_accepted_counts_are_outcomes_not_forced_goals(count):
    arms={k:("ACCEPTED" if i<count else "REFUSED") for i,k in enumerate(("L","I"))}
    r=classifications(arms,{"L":"WITHIN_BAND","I":"WITHIN_BAND"},"WITHIN_BAND",False)
    assert r["accepted_arm_count"]==count
    assert r["SAME_BASIS_ENERGY_EQUIVALENCE_SUPPORTED"]==(count==2)


def test_shift_disagreement_and_precision_are_independent():
    r=classifications({"L":"ACCEPTED","I":"REFUSED"},
                     {"L":"OUTSIDE_BAND","I":"OUTSIDE_BAND"},"OUTSIDE_BAND",True)
    assert r["NUMERICAL_FRONTEND_ENERGY_SHIFT_CONFIRMED"]
    assert r["INDEPENDENT_AO_PATH_DISAGREEMENT"]
    assert r["PRECISION_SENSITIVITY_SUPPORTED"]
    assert not r["SAME_BASIS_ENERGY_EQUIVALENCE_SUPPORTED"]


def test_unaligned_mo_and_changed_C_are_rejected():
    a={"AO_sha256":"ao","C_sha256":"c1"};b={"AO_sha256":"ao","C_sha256":"c2"}
    with pytest.raises(ValueError):require_comparison_context(a,b,cross_arm=True)
    with pytest.raises(ValueError):require_comparison_context(a,b)
    require_comparison_context(a,b,cross_arm=True,common_mapping_verified=True)
    require_comparison_context(a,a)


def test_signed_budget_does_not_name_residue_as_basis_error():
    r=signed_budget("-.11803113362157003","-.11803113362","-.120230341178823")
    assert r["E_old_minus_E_new"]=="-1.57003E-12"
    assert r["sum_equals_old_minus_reference"]
    assert r["pure_finite_basis_error"]=="NOT_ESTABLISHED"
    assert r["numerical_error_bound"] is None


def test_unchanged_thresholds_and_explicit_three_precision_layers():
    p=json.loads(Path("electronic_pilot/reconstruction_v0/protocol.json").read_text(encoding="utf-8"))
    old=json.loads(Path("electronic_pilot/ao_micro_v0/protocol.json").read_text(encoding="utf-8"))
    for key,value in old["guards"].items():assert p["guards"][key]==value
    assert p["guards"]["same_basis_energy_abs_max_hartree"]==1e-9
    assert p["acceptance"]["allowed_accepted_counts"]==[0,1,2]
    assert all(k in p["precision_layers"] for k in ("1_guard","2_fixed_AO","3_recomputed_AO"))
