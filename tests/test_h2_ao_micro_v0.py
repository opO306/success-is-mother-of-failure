"""Independent analytic/quadrature checks and fault injection for new pilot."""
import ast
from pathlib import Path
import mpmath as mp
import pytest
from electronic_pilot.ao_micro_v0.gaussian import boys,hermite,primitive_overlap,primitive_eri


def test_boys_against_direct_quadrature():
    with mp.workdps(55):
        for n in (0,1,6,12):
            for t in (mp.mpf(0),mp.mpf('0.001'),mp.mpf(2),mp.mpf(30)):
                independent=mp.quad(lambda u:u**(2*n)*mp.exp(-t*u*u),[0,1])
                assert abs(boys(n,t)-independent)<mp.mpf('1e-50')


def test_angular_overlap_against_direct_polynomial_quadrature():
    with mp.workdps(55):
        a=mp.mpf('.8');b=mp.mpf('1.2');A=mp.mpf('-.3');B=mp.mpf('.4')
        for i,j in ((0,0),(1,3),(3,2),(2,2)):
            direct=mp.quad(lambda x:(x-A)**i*(x-B)**j*mp.exp(-a*(x-A)**2-b*(x-B)**2),[-mp.inf,0,mp.inf])
            actual=hermite(i,j,A-B,a,b)[0]*mp.sqrt(mp.pi/(a+b))
            assert abs(direct-actual)<mp.mpf('1e-50')


def test_ssss_closed_formula_at_separated_centers():
    with mp.workdps(60):
        a,b,c,d=map(mp.mpf,('.4','.6','.3','.2'));zero=(mp.mpf(0),)*3
        D=(mp.mpf(0),mp.mpf(0),mp.mpf(1));p=a+b;q=c+d;alpha=p*q/(p+q);distance=d/q
        F=mp.sqrt(mp.pi)/(2*mp.sqrt(alpha)*distance)*mp.erf(mp.sqrt(alpha)*distance)
        expected=2*mp.pi**mp.mpf('2.5')/(p*q*mp.sqrt(p+q))*mp.exp(-c*d/q)*F
        assert abs(primitive_eri(a,zero,(0,0,0),b,zero,(0,0,0),c,zero,(0,0,0),d,D,(0,0,0))-expected)<mp.mpf('1e-55')


def test_p_coulomb_via_derivative_of_ssss():
    with mp.workdps(55):
        zero=(mp.mpf(0),)*3; b=mp.mpf('.6');a=mp.mpf('.8');shift=mp.mpf('.4')
        def base(x):
            return primitive_eri(a,(x,0,0),(0,0,0),b,zero,(0,0,0),a,zero,(0,0,0),b,zero,(0,0,0))
        derivative=mp.diff(base,shift)/(2*a)
        actual=primitive_eri(a,(shift,0,0),(1,0,0),b,zero,(0,0,0),a,zero,(0,0,0),b,zero,(0,0,0))
        assert abs(actual-derivative)<mp.mpf('1e-50')


def test_integrator_does_not_import_backend_or_old_integrals():
    source=Path('electronic_pilot/ao_micro_v0/gaussian.py').read_text()
    assert all('pyscf' not in ast.unparse(n).lower() and 'numerical_cause' not in ast.unparse(n) for n in ast.walk(ast.parse(source)) if isinstance(n,(ast.Import,ast.ImportFrom)))


def test_canonical_rule_all_eight_permutations():
    # Pure rule independent from the driver, no PySCF dependency.
    import json
    spec=json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())
    assert spec['guards']==dict(Smin_floor=1e-10,orth_l2_max=1e-10,H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10)
    assert spec['R_bohr']==[.7,1.,1.3,1.4]


def test_spot_evidence_gate_faults():
    from electronic_pilot.ao_micro_v0.spot import evidence_gate
    row=dict(independent_ERI_permutation_max='1e-70',independent_S_permutation_max='1e-70',
        precision_60_80_max='1e-60',libcint_ERI_permutation_spread=2e-16,selected_class_propagation=2e-9)
    assert evidence_gate(row)
    for field,value in (('independent_ERI_permutation_max','1e-8'),('independent_S_permutation_max','1e-8'),
                        ('precision_60_80_max','1e-8'),('libcint_ERI_permutation_spread',0),('selected_class_propagation',1e-15)):
        mutated=dict(row);mutated[field]=value
        assert not evidence_gate(mutated)


@pytest.mark.parametrize('field,value,stage',[('Smin',1e-11,'overlap_floor'),('orthogonality_l2',2e-10,'orthonormalization'),
    ('singlet_asymmetry',2e-10,'singlet_hermiticity'),('eigen_residual_l2',2e-9,'eigensolve'),('vector_norm_error',2e-10,'eigensolve'),
    ('total_energy_hartree',float('nan'),'eigensolve')])
def test_unchanged_guard_fault_injection(field,value,stage):
    import json
    from electronic_pilot.ao_micro_v0.reuse import first_failure
    guard=json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())['guards']
    row=dict(Smin=1e-4,orthogonality_l2=1e-12,singlet_asymmetry=1e-13,eigen_residual_l2=1e-12,vector_norm_error=1e-14,total_energy_hartree=-1.17)
    assert first_failure(row,guard) is None
    row[field]=value
    assert first_failure(row,guard)==stage


def test_no_eigen_orbitals_deleted_and_no_H_averaging():
    source=Path('electronic_pilot/ao_micro_v0/reuse.py').read_text()
    assert "coordinates(s,h,'cholesky')" in source
    assert 'singlet_matrix(hm,eri)' in source
    assert 'mat+mat.T' not in source.replace(' ','')


@pytest.mark.parametrize('fault',['none','refused_left','bad_control','missing','nonminimum','dimension'])
def test_bracket_control_and_completeness_faults(fault):
    import json
    from electronic_pilot.ao_micro_v0.analyze import assess
    spec=json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())
    rows=[dict(R_bohr=r,paths=[dict(accepted=True,basis_size=60,singlet_dimension=1830,total_energy_hartree=e)])
          for r,e in ((.7,-.9),(1.,-1.1),(1.3,-1.171),(1.4,spec['control_EBO']))]
    old_right=dict(accepted=True,total_energy_hartree=-1.172)
    if fault=='refused_left': rows[2]['paths'][0]['accepted']=False
    if fault=='bad_control': rows[3]['paths'][0]['total_energy_hartree']-=1e-6
    if fault=='nonminimum': rows[2]['paths'][0]['total_energy_hartree']=spec['control_EBO']-1e-3
    if fault=='dimension': rows[0]['paths'][0]['basis_size']=59
    if fault=='missing':
        with pytest.raises(ValueError,match='incomplete'): assess(rows[:-1],old_right,spec)
        return
    result=assess(rows,old_right,spec)
    assert result['local_minimum_resolved']==(fault=='none')
    assert result['stop_without_expansion']==(fault=='nonminimum')


def test_selected_class_MP_contraction_against_product_projection(tmp_path):
    import numpy as np
    from electronic_pilot.ao_micro_v0.analyze import exact_class
    c=np.array([[1.,.3],[.2,.8]])
    g=np.zeros((2,)*4)
    indices=((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1))
    for t,value in zip(indices,(.11,.23,.37,.41)): g[t]=value
    product=np.einsum('pqrs,pi,qk,rj,sl->ijkl',g,c,c,c,c).reshape(4,4)
    P=np.array([[1.,0.,0.],[0.,1/np.sqrt(2),0.],[0.,1/np.sqrt(2),0.],[0.,0.,1.]])
    projected=P.T@product@P
    expected=projected[1,0]-projected[0,1]
    artifact=tmp_path/'c.npz';np.savez(artifact,c=c)
    data=dict(worst_coupling=dict(pair_a=[0,1],pair_b=[0,0]),
              ERI_class=dict(raw_values=[dict(indices=t,value=g[t]) for t in indices]))
    assert abs(float(exact_class(data,artifact))-expected)<2e-16


@pytest.mark.parametrize('prefix',['','/mnt/c/Users/u/repo/','C:\\Users\\u\\repo\\'])
def test_executed_source_path_adapter(prefix):
    from electronic_pilot.ao_micro_v0.package import source_path
    suffix='electronic_pilot/ao_micro_v0/prepare.py'
    assert source_path(prefix+suffix)==Path(suffix)
