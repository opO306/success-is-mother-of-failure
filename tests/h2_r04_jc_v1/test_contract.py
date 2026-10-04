from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import pytest
from electronic_pilot.h2_r04_jc_v1 import contract as c
from electronic_pilot.h2_r04_jc_v1.instrument import clocks,enumeration,strip

@pytest.mark.parametrize('o,n',[(1,3),(2,9),(3,20),(4,42),(5,78),(6,138),(7,228),(8,363),(9,553)])
def test_energy_blind_count_and_nesting(o,n):
    b=c.basis(o);assert len(b)==n and len(set(b))==n
    if o>1:assert set(c.basis(o-1))<set(b)

def test_source_preservation():
    src=Path('runs/h2_representation_pilot1/resume_v1_20261003/vendor_original/h2solv/f/h2solv.f').read_bytes()
    assert strip(clocks(src))==strip(enumeration(src))==src

def test_fixed_input_no_added_repulsion():
    v=c.input_bytes(3,F(1),80,60,F(-2)).decode().splitlines()
    assert len(v)==15 and [x.split()[0] for x in v[:5]]==['1','1','1','1','0.4']
    assert [x.split()[0] for x in v[11:]]==['0.0','0.0','1.0','1.0']

@pytest.mark.parametrize('o,u,n,d',[(9,1,80,60),(3,2,80,60),(3,1,140,60),(3,1,80,40)])
def test_refuse_unsealed_expansion(o,u,n,d):
    with pytest.raises(ValueError):c.input_bytes(o,F(u),n,d,F(-2))

def test_numeric_selection_and_fail_closed():
    e={f'n{n}d60':F(0) for n in c.NMAX};e['n120d80']=F(0)
    assert c.choose_numeric(e)==(80,60)
    e['n80d60']=F(1,10**9);assert c.choose_numeric(e)==(100,60)
    e['n120d80']=F(1,10**9)
    with pytest.raises(ValueError):c.choose_numeric(e)

def row():
    return dict(observation=dict(inverse_iteration_supported=True,maxit_exhausted=False),SPD=True,
                root=dict(status='LOWEST_ROOT_ENCLOSED',E_inside=True,inertia_low=0,inertia_high=1),
                WA1_status='MATCH',consistency=dict(RQ_inside=True,RQ_cauchy=True,residual_intersects=True,rho_contained=True))

@pytest.mark.parametrize('mutation,status',[
    ('maxit','REFUSED_ITERATION'),('SPD','REFUSED_SPD'),('excited','NOT_GROUND_ROOT'),
    ('outside','REFUSED_ROOT'),('wa','REFUSED_CONSISTENCY'),('residual','REFUSED_CONSISTENCY')])
def test_false_success_faults(mutation,status):
    r=row();assert c.acceptance(r)=='ACCEPTED_FINITE_STORED_PROBLEM'
    if mutation=='maxit':r['observation']['maxit_exhausted']=True
    elif mutation=='SPD':r['SPD']=False
    elif mutation=='excited':r['root'].update(status='LOWEST_TRANSITION_FAILED',inertia_low=1,inertia_high=2)
    elif mutation=='outside':r['root']['E_inside']=False
    elif mutation=='wa':r['WA1_status']='MISMATCH'
    else:r['consistency']['rho_contained']=False
    assert c.acceptance(r)==status

def test_root_search_and_optimizer_are_bounded():
    assert c.MAX_ROOT_RETRIES==1 and c.MAX_EVALUATIONS==7
    assert c.SIZES=={'SMALL':3,'MEDIUM':5,'LARGE':7}
    for name in ('contract.py','instrument.py','measure.py','run.py'):
        text=Path('electronic_pilot/h2_r04_jc_v1',name).read_text()
        assert '120230341' not in text and 'Pachucki' not in text

def test_missing_consistency_and_failed_metric_cannot_be_retried_as_maxit():
    r=row();r['consistency']={};assert c.acceptance(r)=='REFUSED_CONSISTENCY'
    r=row();r['SPD']=False;r['observation']['maxit_exhausted']=True
    assert c.acceptance(r)=='REFUSED_SPD'
