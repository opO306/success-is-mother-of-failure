"""Native AO checks against closed-form integrals; engine names do not suffice."""
import json,math
from pathlib import Path
import numpy as np
import pytest

ROOT=Path('runs/h2_adversarial_v0/libint_v0')
@pytest.fixture(scope='module')
def data():
    assert (ROOT/'postcheck.json').is_file(), 'actual independent native run evidence required'
    d=json.loads(Path('runs/h2_adversarial_v0/definitions_v1/basis_definitions.json').read_text(encoding='utf-8'))
    return d['records']['cc-pVQZ'],{k:np.load(ROOT/(k+'.npy'),allow_pickle=False) for k in ('s','t','v','g')}

def test_full_native_overlap_function_norms(data):
    row,a=data;assert row['orbital_count']==60
    assert np.max(abs(np.diag(a['s'])-1))<1e-14

def test_single_primitive_kinetic_against_analytic_harmonics(data):
    row,a=data;start=0;checked=0
    for sh in row['actual_shells']:
        size=sh['nctr']*(2*sh['l']+1)
        if len(sh['exponents'])==1:
            expected=(sh['l']+1.5)*sh['exponents'][0]
            assert np.max(abs(np.diag(a['t'])[start:start+size]-expected))<1e-13
            checked+=size
        start+=size
    assert checked>=40

def test_single_primitive_s_nuclear_and_coulomb_analytic(data):
    row,a=data;start=0;checked=0
    for sh in row['actual_shells']:
        size=sh['nctr']*(2*sh['l']+1)
        if sh['l']==0 and len(sh['exponents'])==1:
            alpha=sh['exponents'][0]
            expected_v=-2*math.sqrt(2*alpha/math.pi)-math.erf(math.sqrt(2*alpha)*.4)/.4
            expected_g=2*math.sqrt(alpha/math.pi)
            assert a['v'][start,start]==pytest.approx(expected_v,abs=1e-13)
            assert a['g'][start,start,start,start]==pytest.approx(expected_g,abs=1e-13)
            checked+=1
        start+=size
    assert checked>=4
