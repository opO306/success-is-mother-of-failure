"""Independent batch algebra, semantic guards, and intentional fault injection."""
import ast
import math
from pathlib import Path
import numpy as np
import pytest
from electronic_pilot.ground_state_audit_v0 import operator
from electronic_pilot.ground_state_audit_v0.run import mapping, validate
from electronic_pilot.ci_layer_audit_v0 import fermion

GUARDS = {'eigen_l2_max': 1e-9, 'norm_max': 1e-10, 'H_asym_max': 1e-10}


def tiny(n, symmetric=False):
    h = np.arange(n*n, dtype=float).reshape(n,n)/16
    g = np.arange(n**4, dtype=float).reshape((n,)*4)/32
    if symmetric:
        h = h+h.T
        for a,b,c,d in np.ndindex(g.shape):
            x,y = sorted((a,b)), sorted((c,d))
            g[a,b,c,d] = (1+2*x[0]+3*x[1]+5*y[0]+7*y[1])/32
    return h,g


@pytest.mark.parametrize('n,symmetric', [(1, False), (2, False), (2, True), (3, False), (3, True)])
def test_all_elements_against_scalar_fermion_operator(n,symmetric):
    h,g = tiny(n,symmetric)
    matrix, states = operator.dense(h,g,block=2)
    expected = np.array([[fermion.value(h,g,a['pair'],b['pair']) for b in states] for a in states])
    assert np.max(abs(matrix-expected)) < 1e-13
    parts = operator.rows(h,g,states,0,len(states),decomposition=True)
    for i,a in enumerate(states):
        for j,b in enumerate(states):
            detail = fermion.breakdown(h,g,a['pair'],b['pair'])['contribution']
            for kind in parts:
                assert abs(parts[kind][i,j]-float(detail[kind])) < 1e-13


def test_manual_closed_and_open_terms_and_raw_permutation_faults():
    h,g = tiny(2, True)
    m,states = operator.dense(h,g)
    assert m[0,0] == 2*h[0,0]+g[0,0,0,0]
    expected = math.sqrt(2)*h[0,1]+(g[0,0,0,1]+g[0,1,0,0])/math.sqrt(2)
    assert abs(m[0,1]-expected) < 1e-14
    faulty = g.copy();faulty[0,0,0,1] += .001
    changed,_ = operator.dense(h,faulty)
    assert abs(changed[0,1]-m[0,1]) > 1e-4  # raw counterpart is not silently folded


def test_full60_canonical_semantics_and_vector_mapping():
    states=operator.catalog(60)
    order=np.array([s['pair'] for s in states])[::-1]
    v=np.arange(1830,dtype=float)
    output,record=mapping(v,order,states)
    assert np.array_equal(output,v[::-1])
    assert record['dimensions']==1830 and not record['identity_permutation']
    order[0]=order[1]
    with pytest.raises(ValueError,match='coverage'):
        mapping(v,order,states)


@pytest.mark.parametrize('fault',['energy','vector','norm','asymmetry','nonfinite'])
def test_stage_a_failures_prevent_every_independent_eigen_call(fault):
    matrix=np.diag([1.,2.,3.]);vector=np.array([1.,0.,0.]);energy=1.
    if fault=='energy':energy+=1e-5
    elif fault=='vector':vector=np.array([math.sqrt(.5),math.sqrt(.5),0.])
    elif fault=='norm':vector*=2
    elif fault=='asymmetry':matrix[0,1]=1e-5
    else:matrix[1,1]=float('nan')
    def forbidden(*args):
        pytest.fail('Stage B reached after action failure')
    a,b,*_=validate(matrix,operator.catalog(2),energy,vector,GUARDS,1e-9,solver=forbidden)
    assert a['classification']=='GROUND_STATE_ACTION_MISMATCH' and b is None


def test_unhinted_eigensolve_and_sign_invariant_comparison():
    matrix=np.diag([1.,2.,3.]);vector=np.array([-1.,0.,0.]);calls=[]
    def solver(only_matrix):
        calls.append(only_matrix)
        return np.linalg.eigh(only_matrix)
    a,b,*_=validate(matrix,operator.catalog(2),1.,vector,GUARDS,1e-9,solver=solver)
    assert len(calls)==1 and b['classification']=='INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED'
    assert b['overlap_absolute']==b['normalized_overlap']==1 and b['next_singlet_gap']==1


def test_passed_action_can_still_have_different_lowest_energy():
    matrix=np.diag([0.,1.,2.]);vector=np.array([0.,1.,0.])
    a,b,*_=validate(matrix,operator.catalog(2),1.,vector,GUARDS,1e-9)
    assert a['classification']=='GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED'
    assert b['classification']=='INDEPENDENT_EIGENSOLVE_MISMATCH' and b['absolute_difference']==1


def test_degenerate_lowest_subspace_is_reported():
    matrix=np.diag([1.,1.,3.]);vector=np.array([math.sqrt(.5),math.sqrt(.5),0.])
    _,b,*_=validate(matrix,operator.catalog(2),1.,vector,GUARDS,1e-9)
    assert b['lowest_cluster_dimension_at_existing_band']==2
    assert abs(b['subspace_overlap']-1)<1e-15


def test_no_old_ci_or_invalid_packing_or_reference_in_independent_evaluator():
    source=Path(operator.__file__).read_text(encoding='utf-8')
    tree=ast.parse(source)
    modules=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert modules==['electronic_pilot.ci_layer_audit_v0']
    for name in ['singlet_matrix(', 'absorb_h1e(', 'contract_2e(', 'ao2mo', 'reference_pachucki']:
        assert name not in source
    assert len(ast.parse(source).body)>0
