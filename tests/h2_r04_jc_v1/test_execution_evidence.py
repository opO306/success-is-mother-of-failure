"""Run after capture; assertions bind real executed data, not canned energies."""
from pathlib import Path
from electronic_pilot.h2_r04_jc_v1.run import read,DOC,RAW,verify,check_seal,energy
from electronic_pilot.h2_r04_jc_v1 import contract as c
from electronic_pilot.h2_stored_root_v1 import checker as ck

def test_protocol_and_old_bytes_unchanged():check_seal()

def test_real_native_enumeration():
    data=read(DOC/'evidence/basis_enumeration.json')
    assert len(data)==9 and all(r['native_order_and_tuples_match'] and not r['energy_executed'] for r in data)

def test_energy_seal():
    seal=read(DOC/'evidence/energy_seal.json');verify(seal['bound_sha256'])
    assert seal['all_B1_energies_before_reference'] and seal['status']=='R04_FINITE_CAMPAIGN_ACCEPTED'

def test_three_actual_final_problems_and_spots():
    campaign=read(DOC/'evidence/campaign.json')
    assert campaign['status']=='R04_FINITE_CAMPAIGN_ACCEPTED' and campaign['STOP']
    us=set()
    for size,omega in c.SIZES.items():
        r=campaign['final'][size];spot=campaign['spots'][size];us.add(r['u'])
        assert r['OMEGA']==omega and r['dimension']==len(c.basis(omega))
        assert c.acceptance(r)==c.acceptance(spot)=='ACCEPTED_FINITE_STORED_PROBLEM'
        assert r['observation']['final_ierror']==0 and not r['observation']['maxit_exhausted']
        assert (r['root']['inertia_low'],r['root']['inertia_high'])==(0,1)
        assert spot['NMAX']==r['NMAX']+20 and abs(energy(spot)-energy(r))<=c.STABILITY
        v=campaign['vendor_checks'][size];assert v['scientific_stdout_identical'] and v['wavefunctions_identical']
        base=RAW/'runs'/r['label']
        assert ck.sha(base/'audit_HS.bin')==r['hashes']['audit_HS.bin']
    assert len(us)==1 and campaign['nested_energy_nonincreasing']

def test_calibration_axes_and_optimizer_budget():
    camp=read(DOC/'evidence/campaign.json');by={r['label']:r for r in camp['all_runs']}
    for key,label in camp['calibration']['points'].items():
        r=by[label];assert r['OMEGA']==5 and r['u']=='1.0'
    assert camp['optimizer']['evaluation_count']==7 and len(camp['optimizer']['evaluations'])==7
    assert all(r['status']=='REFUSED_ITERATION' for r in camp['all_runs'] if r['status']!='ACCEPTED_FINITE_STORED_PROBLEM')

def test_reference_only_after_seal_and_fresh_cost_gate():
    ref=read(DOC/'evidence/reference_comparison.json')
    assert ref['energy_seal_sha256']==ck.sha(DOC/'evidence/energy_seal.json')
    cost=read(DOC/'evidence/cost_comparison.json')
    if ref['first_target_meeting']:
        assert cost['physical_basis_guards_unchanged'] and cost['fresh_result']['accepted']
        verify(cost['bindings'])
    else:assert cost['classification']=='COST_COMPARISON_NOT_COMPARABLE'
