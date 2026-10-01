"""O-1: physical identities, negative verdicts, and dependency independence."""
import ast
from pathlib import Path
import pytest
import mpmath as mp

def test_module_exists():
    # RED: independently implemented O-1 calculator is required.
    from c1b1_o1.continuous import scatter
    assert callable(scatter)

def test_free_scattering_known_geometry():
    from c1b1_o1.continuous import scatter
    with mp.workdps(40):
        r = scatter(lambda r: mp.mpf(0), mp.mpf(1), [20, 0], [-3, 1], mp.mpf(20), 40)
        assert abs(mp.mpf(r['r_min'])-20/mp.sqrt(10)) < mp.mpf('1e-25')
        assert abs(mp.mpf(r['chi'])) < mp.mpf('1e-25')
        assert abs(mp.mpf(r['time'])-12) < mp.mpf('1e-25')

def test_independence():
    for path in Path('c1b1_o1').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            assert not any(n.split('.')[0] in {'a_reference','a_numeric','engine','audit','c1b1_replay'} for n in names)

@pytest.mark.parametrize('metric', ['chi','sweep','direction','r_min','energy'])
def test_comparison_catches_fault(metric):
    from c1b1_o1.compare import classify
    baseline = dict(chi=0, sweep=1, direction=0, r_min=6, energy=0)
    actual = {**baseline, metric: baseline[metric]+1}
    assert classify(baseline,actual,True)['verdict']=='DISAGREE'

def test_unresolved_is_not_agreement():
    from c1b1_o1.compare import classify
    assert classify({}, {}, False)['verdict']=='UNRESOLVED'

def test_requires_confirmed():
    from c1b1_o1.compare import classify
    assert classify({}, {}, True, confirmed=False)['verdict']=='UNRESOLVED'

def test_convergence_failure_and_nonfinite_are_never_agree():
    from c1b1_o1.compare import converged, classify
    row=dict(r_min='6',chi='0',sweep='1',direction='0',time='2',quadrature_error='1e-50',target='1e-40')
    assert converged([row,row,row])
    assert not converged([row,row,{**row,'r_min':'6.001'}])
    assert not converged([row,row,{**row,'quadrature_error':'1e-10'}])
    baseline=dict(chi=0,sweep=1,direction=0,r_min=6,energy=0)
    assert classify(baseline,{**baseline,'r_min':float('nan')},True)['verdict']=='DISAGREE'

def test_outermost_turning_root():
    from c1b1_o1.continuous import turning_point
    with mp.workdps(40):
        root=turning_point(lambda r:(r-3)*(r-6)*(r-10),mp.mpf(20),40)
        assert abs(root-10)<mp.mpf('1e-35')

def test_potential_and_complex_step_force_crosscheck():
    from c1b1_o1.model import Potential
    with mp.workdps(60):
        potential=Potential()
        r=mp.mpf('7.1'); step=mp.mpf('1e-25')
        numerical=mp.diff(potential,r)
        complex_step=mp.im(potential(r+1j*step))/step
        assert abs(numerical-complex_step)<mp.mpf('1e-40')
        assert potential(r)<0

def test_modified_potential_changes_scattering():
    from c1b1_o1.continuous import scatter
    with mp.workdps(40):
        free=scatter(lambda r:mp.mpf(0),mp.mpf(1),[20,0],[-3,1],mp.mpf(20),40)
        wrong=scatter(lambda r:1/r,mp.mpf(1),[20,0],[-3,1],mp.mpf(20),40)
        assert abs(mp.mpf(wrong['chi'])-mp.mpf(free['chi']))>mp.mpf('1e-4')

def test_input_seal_rejects_raw_tampering(tmp_path,monkeypatch):
    import json
    import tools.c1b1_o1_study as driver
    original=json.loads(driver.INPUT.read_text(encoding='utf-8'))
    original['payload']['inputs'][0]['raw'][0]+=1
    bad=tmp_path/'bad.json';bad.write_text(json.dumps(original),encoding='utf-8')
    monkeypatch.setattr(driver,'INPUT',bad)
    with pytest.raises(ValueError,match='input seal mismatch'):
        driver.load_inputs()

@pytest.mark.parametrize('boundary,expected',[(0.000009999,'AGREE'),(0.000010001,'DISAGREE')])
def test_frozen_tolerance_boundary(boundary,expected):
    from c1b1_o1.compare import classify
    baseline=dict(chi=0,sweep=1,direction=0,r_min=6,energy=0)
    assert classify(baseline,{**baseline,'chi':boundary},True)['verdict']==expected

def test_invalid_initial_direction_and_no_turning_point_refuse():
    from c1b1_o1.continuous import scatter,turning_point,Unresolved
    with pytest.raises(Unresolved,match='inbound'):
        scatter(lambda r:0,mp.mpf(1),[20,0],[3,1],mp.mpf(20),40)
    with pytest.raises(Unresolved,match='no turning bracket'):
        turning_point(lambda r:mp.mpf(1),mp.mpf(20),40)
