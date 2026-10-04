import ast
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from electronic_pilot.compressibility_hotline import tensor,baseline,checker,campaign

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'electronic_pilot/compressibility_hotline/protocol.json').read_text())


@pytest.mark.parametrize('electrons',[1,2])
@pytest.mark.parametrize('cut',[7,14,21])
def test_occupation_factorization(electrons,cut):
    # Deterministic analytic coefficient pattern, no random generator.
    if electrons==1:x=np.arange(1,29).astype(complex)*(1+0.3j);x/=np.linalg.norm(x);v=x
    else:
        grid=np.arange(28);x=1/(1+grid[:,None]+grid[None,:])+1j*(grid[:,None]*grid[None,:])/1000
        x/=np.linalg.norm(x);v=tensor.pack(x)
    direct=np.linalg.svd(checker.fock_matrix(v,electrons,cut),compute_uv=False)
    d=tensor.decompose(x,cut)
    assert np.allclose(direct[:len(d['singular'])],d['singular'],atol=1e-12)
    for chi in P['chi']:
        z,_,used=tensor.truncate(d,chi)
        assert used<=chi
        assert np.linalg.norm(x-z)**2==pytest.approx(sum(d['singular']**2)-np.linalg.norm(z)**2,abs=2e-12)
        if electrons==2:assert np.array_equal(z,z.T)
    assert np.allclose(tensor.truncate(d,32)[0],x,atol=1e-12)


@pytest.mark.parametrize('kind',['hidden','thrash'])
@pytest.mark.parametrize('order',P['orders'])
def test_controls(kind,order):
    r=baseline.controls(P,kind,order)
    assert checker.control(r,P)
    assert all(next(x for x in row['blocks'] if x['block']==1)['status']=='COARSE_CERTIFIED' for row in r['rows'])
    if kind=='hidden':
        assert next(x for x in r['rows'][3]['blocks'] if x['block']==0)['reason']=='SAFETY_OVERRIDE'
    else:
        state=[next(x for x in row['blocks'] if x['block']==0)['status'] for row in r['rows']]
        assert sum(a!=b for a,b in zip(state,state[1:]))==2


@pytest.mark.parametrize('fault',P['mutations'])
def test_eight_faults(fault):
    r=campaign.faults(baseline.controls(P,'hidden'),P)
    assert next(x for x in r if x['fault']==fault)['caught']


def small_problem():
    p=copy.deepcopy(P);p['block_sizes']['A']=2
    v=np.array([.13+.17j,.27-.11j,.31+.19j,.43-.07j]);v/=np.linalg.norm(v)
    h=np.array([[1.,.2,.01,.03],[.2,2.,.07,.04],[.01,.07,3.,.11],[.03,.04,.11,4.]])
    d=dict(label='A',electrons=1,s=np.eye(4),h=h,dipoles=np.array([h/7,h/9,h/11]))
    from scipy.linalg import expm
    waves=np.array([expm(-1j*h*t)@v for t in P['times_atomic']])
    return p,d,waves


@pytest.mark.parametrize('path',['REF','BASELINE','HOTLINE'])
@pytest.mark.parametrize('order',P['orders'])
def test_complete_coupling_and_canonical_order(path,order):
    p,d,waves=small_problem();r,out=baseline.run(waves,d,p,path,order)
    assert checker.electronic(r,waves,d,p,out)
    assert out.tobytes()==waves.tobytes()


@pytest.mark.parametrize('mutation',['pair','source','epoch','center','radius','output'])
def test_electronic_checker_adversaries(mutation):
    p,d,waves=small_problem();r,out=baseline.run(waves,d,p,'BASELINE','ascending')
    if mutation=='pair':r['trace'][0]['accounts'][1].pop()
    elif mutation=='source':r['trace'][1]['blocks'][0]['source_real'][0]+=1
    elif mutation=='epoch':r['trace'][1]['blocks'][0]['epoch']=0
    elif mutation=='center':r['trace'][0]['blocks'][0]['center_real']=[0.,0.]
    elif mutation=='radius':r['trace'][1]['blocks'][0]['input_radius_num']=0
    else:out[0,0]+=1e-5
    with pytest.raises(ValueError):checker.electronic(r,waves,d,p,out)


def test_safety_overrides_entry_and_hysteresis():
    assert baseline.transition('COARSE_CERTIFIED',.009,.02,.002,.008)==('FULL','SAFETY_OVERRIDE')
    assert baseline.transition('FULL',.009,.02,.002,.008)==('FULL','SAFETY_OVERRIDE')


def test_checker_does_not_import_implementation():
    tree=ast.parse((ROOT/'electronic_pilot/compressibility_hotline/checker.py').read_text())
    assert not any(isinstance(n,ast.ImportFrom) and n.module and any(w in n.module for w in ['tensor','baseline','campaign','engine']) for n in ast.walk(tree))


def test_fixed_protocol_preserves_gate_limits():
    assert P['push']=='PROHIBITED' and P['scheduler_K']==1
    assert P['hot_enter_radius_l1']>P['cold_return_radius_l1']
    assert 'IGNORED' not in (ROOT/'electronic_pilot/compressibility_hotline/baseline.py').read_text()
