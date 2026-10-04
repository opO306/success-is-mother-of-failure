"""Synthetic trajectory/fault tests; no electronic calculations."""
import copy
import importlib.util
from decimal import Decimal as D
from fractions import Fraction as Q
from pathlib import Path
import pytest
from electronic_pilot.h2_nuclear_v0.scalar import geometry
from electronic_pilot.h2_force_v0.interface import GUARDS

def api(name):
    assert importlib.util.find_spec('electronic_pilot.h2_multistep_v0.'+name),name+' missing'
    return __import__('electronic_pilot.h2_multistep_v0.'+name,fromlist=['*'])

def point(requested):
    g=geometry(requested);r=g['actual_serialized_R']
    return dict(requested_R=requested,geometry=g,actual_stored_positions_bohr=g['positions_bohr'],
        accepted=True,failure_stage=None,basis='cc-pV5Z',mode='AO_and_MO_integral_reuse',basis_size=110,
        singlet_dimension=6105,arithmetic='IEEE binary64',driver='evr',energy_convention='EBO=Ee+1/R',
        guards=GUARDS.copy(),Smin=.001,orthogonality_l2=0.,singlet_asymmetry=0.,eigen_residual_l2=0.,
        vector_norm_error=0.,total_energy_hartree=(r-1.4)**2,runtime_module_origins={'electronic_pilot.solver':'/snapshot/electronic_pilot/solver.py'})

def sample():
    scalar=api('scalar');previous=dict(R='1.5',P='0',F='-0.2')
    half=scalar.drift(previous,'2000')
    left,right=(point(half['requested_geometries'][label]) for label in ('left','right'))
    return previous,scalar.finish(previous,half,left,right,'2000')

def test_quadratic_update_and_carried_force():
    previous,step=sample()
    assert step['P_half']=='-0.1' and D(step['R'])==D('1.4999')
    assert abs(D(step['P'])-D('-.1999'))<D('1e-14')
    assert api('kit').quick(previous,step,'2000','/snapshot')['status']=='QUICK_KIT_PASS'
    assert Q(step['nuclei']['COM_position'])==0 and Q(step['nuclei']['total_momentum'])==0

@pytest.mark.parametrize('fault',['mass','R','P','F','P_half','COM','momentum','geometry','rounding','origin','guard','refused','energy_nan','dt','h','tolerance'])
def test_quick_faults_fail_closed(fault):
    previous,step=sample();mass='2000'
    if fault=='mass':mass='4000'
    elif fault in ('R','P','F','P_half'):step[fault]=str(Q(step[fault])+Q(1,1000))
    elif fault=='COM':step['nuclei']['z_A']='-.5'
    elif fault=='momentum':step['nuclei']['p_A']='0'
    elif fault=='geometry':step['points'][0]['actual_stored_positions_bohr'][0][2]=0.
    elif fault=='rounding':step['points'][0]['geometry']['R_rounding_delta']='1'
    elif fault=='origin':step['points'][0]['runtime_module_origins']['electronic_pilot.solver']='/checkout/solver.py'
    elif fault=='guard':step['points'][0]['eigen_residual_l2']=1.
    elif fault=='refused':step['points'][0]['accepted']=False
    elif fault=='energy_nan':step['points'][0]['total_energy_hartree']=float('nan')
    elif fault in ('dt','h'):step[fault]='2'
    elif fault=='tolerance':step['energy_conservation_tolerance']='1e-6'
    with pytest.raises((ValueError,ZeroDivisionError,TypeError)):
        api('kit').quick(previous,step,mass,'/snapshot')

@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity','1.199','1.601'])
def test_drift_rejects_nonfinite_or_outside_domain(value):
    with pytest.raises(ValueError):api('scalar').drift(dict(R=value,P='0',F='0'),'2000')

def test_rollback_and_final_promotion():
    kit=api('kit');c0=dict(R='1.5',P='0',F='-.2');states=[dict(R=str(1.5-i*.001),P='-.1',F='-.2') for i in range(1,6)]
    failed=kit.decide(c0,states,False,True)
    assert failed['authoritative_state']==c0 and failed['state_statuses']==['DISCARDED']*5
    assert failed['event']=='CAMPAIGN_POST_AUDIT_FAILED' and not failed['promoted']
    stopped=kit.decide(c0,states[:2],True,False)
    assert stopped['event']=='QUICK_KIT_TRIGGERED_STOP' and stopped['authoritative_state']==c0
    good=kit.decide(c0,states,True,True)
    assert good['promoted'] and good['authoritative_state']==states[-1] and good['state_statuses']==['CONFIRMED']*5
    with pytest.raises(ValueError):kit.decide(c0,states[:3],True,True)

def test_cadence_model_does_not_choose_K():
    model=api('kit').cadence(50.)
    assert [x['K'] for x in model]==[1,5,10,50,100]
    assert [x['amortized_audit_seconds_per_step'] for x in model]==[50.,10.,5.,1.,.5]
    assert [x['maximum_discarded_steps'] for x in model]==[1,5,10,50,100]

def test_snapshot_hash_mutation_and_state_serialization(tmp_path):
    kit=api('kit');p=tmp_path/'constant.json';p.write_bytes(b'old')
    import hashlib
    expected={str(p):hashlib.sha256(b'old').hexdigest()}
    assert kit.verify(expected)==1
    p.write_bytes(b'new')
    with pytest.raises(ValueError):kit.verify(expected)
    state=tmp_path/'state.json'
    receipt=kit.persist(state,dict(R='1.5',P='0',F='-.2'))
    assert receipt['sha256']==hashlib.sha256(state.read_bytes()).hexdigest()
    with pytest.raises(ValueError):kit.persist(tmp_path/'invalid.json',dict(R=float('nan')))

@pytest.mark.parametrize('guard',['Smin','orthogonality_l2','singlet_asymmetry','eigen_residual_l2','vector_norm_error'])
def test_each_electronic_guard_is_retained(guard):
    prev,state=sample();state['points'][1][guard]=0. if guard=='Smin' else 1.
    with pytest.raises(ValueError):api('kit').quick(prev,state,'2000','/snapshot')

def test_center_diagnostic_has_no_tolerance_or_promotion():
    prev,state=sample();center=point(state['R'])
    diag=api('scalar').diagnostic(state,center,'2000','.01')
    assert diag['status']=='MEASURED' and diag['energy_conservation_tolerance'] is None
    assert api('kit').diagnostic_check(state,center,'2000','.01',diag)=='MEASURED_SCALAR_RECOMPUTATION_PASS'
    assert state['state_status']=='SPECULATIVE'
    diag['delta_H_from_C0']='1'
    with pytest.raises(ValueError):api('kit').diagnostic_check(state,center,'2000','.01',diag)

def test_center_geometry_corruption_is_not_a_valid_diagnostic():
    prev,state=sample();center=point(state['R'])
    diag=api('scalar').diagnostic(state,center,'2000','.01')
    center['actual_stored_positions_bohr'][0][2]=0.
    with pytest.raises(ValueError):api('kit').diagnostic_check(state,center,'2000','.01',diag)

@pytest.mark.parametrize('key',['P','F'])
def test_nonfinite_carried_state_stops_before_new_calls(key):
    prev=dict(R='1.5',P='0',F='-.2');prev[key]='NaN'
    with pytest.raises(ValueError):api('scalar').drift(prev,'2000')
