"""Finite-shell induction and independent analytic tail obligations."""
from copy import deepcopy
from fractions import Fraction as Q
import importlib
import importlib.util

import mpmath
import pytest

from a_numeric import FixedPoint
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B


def outer():
    assert importlib.util.find_spec('a_reference.c1b1_outer_bootstrap') is not None, 'outer bootstrap is not implemented'
    return importlib.import_module('a_reference.c1b1_outer_bootstrap')


def run_at(r=Q(20), p=(Q(1), Q(0), Q(0))):
    return C.new_run(FixedPoint(96, 48), Q(40), (-r/2, 0, 0), tuple(-v for v in p),
                     (r/2, 0, 0), p, momentum_profile=FixedPoint(96, 80))


def norm2(v):
    return sum((x*x for x in v), Q(0))


def test_residence_ceiling_is_exact_including_equality():
    o = outer()
    assert o.residence_steps(Q(0), Q(3)) == 0
    assert o.residence_steps(Q(6), Q(3)) == 2
    assert o.residence_steps(Q(7), Q(3)) == 3
    with pytest.raises(o.NotCertified):
        o.residence_steps(Q(1), Q(0))


@pytest.mark.parametrize('p', [(Q(1), Q(0), Q(0)), (Q(1), Q(1,2), Q(1,4))])
def test_induction_covers_real_quantized_steps_and_exit(p):
    o = outer()
    run = run_at(p=p)
    before = deepcopy(run,{id(run.pos):run.pos,id(run.mom):run.mom})
    cert = o.certify_shell(run, Q(20), Q(2001,100), Q(2), 32)
    assert run == before and run._validation is None
    assert cert['g_min'] > 0
    assert cert['max_steps'] <= 32
    previous = norm2(C.relative(run.pos, *run.atoms))
    for n in range(1, cert['max_steps']+1):
        C.step(run)
        q = C.relative(run.pos, *run.atoms)
        current = norm2(q)
        assert current-previous >= cert['g_min']
        assert current <= cert['guard_b']**2
        pi, pj = (C.exact(run.mom, x.p) for x in run.atoms)
        pp = tuple((y-x)/2 for x,y in zip(pi,pj))
        assert norm2(pp) <= cert['p_cap']**2
        assert sum((x*y for x,y in zip(q,pp)), Q(0)) >= cert['w_floor']
        if current >= Q(2001,100)**2:
            break
        previous = current
    else:
        pytest.fail('proved residence bound did not reach the handoff boundary')
    assert cert['energy_hartree']['total'] == cert['max_steps']*cert['step_budget']['energy_hartree']['total']
    assert cert['angular_scope'] == 'finite_shell_only'


def test_stall_and_inward_initial_drift_are_refused():
    o = outer()
    stall = run_at(Q(10**9), (B.UP,Q(0),Q(0)))
    assert C.relative_energy_enclosure(stall,256)[0] > 0
    with pytest.raises(o.NotCertified, match='stored drift'):
        o.certify_shell(stall,Q(10**9),Q(10**9+1),2*B.UP,100)
    with pytest.raises(o.NotCertified):
        o.certify_shell(run_at(p=(Q(-1),Q(0),Q(0))),Q(20),Q(21),Q(2),2000)


def test_displacement_norm_is_not_radial_progress():
    o = outer()
    # A quarter-turn has nonzero displacement but exactly zero delta R^2.
    assert o.radius_squared_increment((Q(20),Q(0),Q(0)),(Q(-20),Q(20),Q(0))) == 0
    assert o.radius_squared_increment((Q(20),Q(0),Q(0)),(Q(1),Q(0),Q(0))) == 41


def test_insufficient_count_or_momentum_budget_cannot_be_certified():
    o = outer()
    with pytest.raises(o.NotCertified):
        o.certify_shell(run_at(),Q(20),Q(21),Q(2),1)
    with pytest.raises(o.NotCertified):
        o.certify_shell(run_at(),Q(20),Q(21),Q(1),2000)


@pytest.mark.parametrize('bad',[1.0,True,'20'])
def test_approximate_shell_inputs_are_not_proof_inputs(bad):
    with pytest.raises(TypeError):
        outer().certify_shell(run_at(),bad,Q(21),Q(2),2000)


def test_profile_cache_and_overflow_guards_are_proof_obligations():
    o = outer()
    wrong = run_at()
    wrong.drift = 'v1'
    with pytest.raises(o.NotCertified,match='profile'):
        o.certify_shell(wrong,Q(20),Q(21),Q(2),2000)
    bad_cache = run_at()
    bad_cache.J_cache = (1,0,0)
    with pytest.raises(o.NotCertified,match='cache'):
        o.certify_shell(bad_cache,Q(20),Q(21),Q(2),2000)
    near_edge = run_at()
    shift = Q(2**47)-Q(11)
    near_edge.atoms = tuple(C.Atom(a.species,tuple(near_edge.pos.from_exact(v+(shift if k==0 else 0))
                           for k,v in enumerate(C.exact(near_edge.pos,a.r))),a.p) for a in near_edge.atoms)
    with pytest.raises(o.NotCertified,match='overflow'):
        o.certify_shell(near_edge,Q(20),Q(21),Q(2),2000)


@pytest.mark.parametrize('r',[Q(20),Q(21),Q(100),Q(10000),Q(100000)])
def test_global_force_envelope_covers_exact_model_derivative(r):
    o = outer()
    cap = o.ForceEnvelope().value(r)
    _,dv,_ = C._model(r*r,1024,True)
    assert cap >= max(abs(Q(x,2**1024)) for x in dv)


def test_global_tail_is_integrable_and_radius_is_model_derived():
    o = outer()
    envelope = o.ForceEnvelope()
    assert all(k>1 and c>0 for k,c in envelope.terms)
    radius = o.zero_impulse_radius()
    assert B.H*envelope.value(radius) < B.UP
    assert B.H*envelope.value(radius/2) >= B.UP
    assert envelope.integral(radius) > 0
    # Integrating the monomial envelope is an exact symbolic operation.
    assert envelope.integral(radius) == sum((c*radius**(1-k)/(k-1) for k,c in envelope.terms),Q(0))
    assert envelope.value(2*radius) < envelope.value(radius)


def test_tail_proves_zero_discrete_kicks_but_not_zero_continuous_tail():
    o = outer()
    run = run_at(o.zero_impulse_radius(),(Q(1),Q(2),Q(3)))
    before = deepcopy(run,{id(run.pos):run.pos,id(run.mom):run.mom})
    cert = o.certify_tail(run)
    assert run == before and run._validation is None
    assert cert['executor_remaining_impulse'] == 0
    assert cert['continuous_tail_impulse'] > 0
    assert 0 < cert['direction_error_radians'] < 1
    assert cert['angular_scope'] == 'infinite_uniform_bound_not_claimed'
    p0 = tuple(C.exact(run.mom,a.p) for a in run.atoms)
    for _ in range(4):
        C.step(run)
        assert not any(run.J_cache)
        assert tuple(C.exact(run.mom,a.p) for a in run.atoms) == p0


def test_tail_rejects_stall_inward_motion_and_insufficient_continuous_escape_margin():
    o = outer()
    radius = o.zero_impulse_radius()
    for p in ((B.UP,Q(0),Q(0)),(Q(-1),Q(0),Q(0)),(Q(1,2**38),Q(0),Q(0))):
        with pytest.raises(o.NotCertified):
            o.certify_tail(run_at(radius,p))
    with pytest.raises(o.NotCertified):
        o.certify_tail(run_at(Q(20)))


def test_zero_impulse_angular_drift_remains_explicit():
    o = outer()
    run = run_at(Q(100000),(Q(1),Q(2),Q(3)))
    cert = o.certify_tail(run)
    before = C.angular_momentum(run)
    C.step(run)
    delta = tuple(y-x for x,y in zip(before,C.angular_momentum(run)))
    assert delta == (Q(-1,2**47),Q(-1,2**47),Q(1,2**47))
    assert cert['angular_scope'] == 'infinite_uniform_bound_not_claimed'


def test_certificates_are_independent_of_global_precision():
    o = outer()
    expected = o.certify_shell(run_at(),Q(20),Q(2001,100),Q(2),32)
    tail = o.certify_tail(run_at(o.zero_impulse_radius()))
    for dps in (15,40,60,100):
        with mpmath.workdps(dps):
            assert o.certify_shell(run_at(),Q(20),Q(2001,100),Q(2),32) == expected
            assert o.certify_tail(run_at(o.zero_impulse_radius())) == tail


def test_mutation_zero_force_envelope_is_detected(monkeypatch):
    o = outer()
    monkeypatch.setattr(o.ForceEnvelope,'value',lambda self,r:Q(0))
    with pytest.raises(AssertionError):
        test_global_force_envelope_covers_exact_model_derivative(Q(20))


def test_malformed_zero_cache_is_not_a_proved_zero_kick():
    o = outer()
    run = run_at(o.zero_impulse_radius())
    run.J_cache = (0,)
    with pytest.raises(o.NotCertified,match='cache'):
        o.certify_tail(run)


@pytest.mark.parametrize('constant',['retardation','mass'])
def test_live_model_configuration_must_match_proved_contract(monkeypatch,constant):
    from a_reference import ar2_lang2024 as lang
    o = outer()
    run = run_at(o.zero_impulse_radius())
    if constant=='retardation':
        monkeypatch.setattr(lang,'WORLD_RETARDATION',False)
    else:
        monkeypatch.setitem(C.SPECIES_MASS,'Ar40',2*C.AR40_MASS_ME)
    with pytest.raises(o.NotCertified,match='model configuration'):
        o.certify_tail(run)


def test_proofs_do_not_read_initial_state_validation(monkeypatch):
    o = outer()
    def forbidden(_):
        raise AssertionError('D_valid evidence cannot be consulted for an analytic proof')
    monkeypatch.setattr(C.Run,'validation',property(forbidden))
    assert o.certify_shell(run_at(),Q(20),Q(2001,100),Q(2),32)['g_min']>0
    assert o.certify_tail(run_at(o.zero_impulse_radius()))['continuous_tail_impulse']>0


def test_outgoing_chain_closes_all_shells_without_running_a_trajectory(monkeypatch):
    o = outer()
    assert hasattr(o,'certify_outgoing_outer'), 'outer shell composition is not implemented'
    def forbidden(_):
        raise AssertionError('analytic composition cannot measure a trajectory')
    monkeypatch.setattr(C,'step',forbidden)
    run = run_at()
    before = deepcopy(run,{id(run.pos):run.pos,id(run.mom):run.mom})
    cert = o.certify_outgoing_outer(run,Q(2))
    assert run == before and run.t_steps == 0
    assert cert['shells'][0]['a'] == 20
    assert cert['shells'][-1]['b'] == cert['tail']['R_J']
    assert all(s['g_min']>0 and s['max_steps']<=s['induction_budget'] for s in cert['shells'])
    assert cert['max_steps_to_R_J'] == sum(s['max_steps'] for s in cert['shells'])
    assert cert['tail']['executor_remaining_impulse'] == 0
    assert cert['tail']['continuous_tail_impulse'] > 0
    assert cert['angular_scope'] == 'finite_entry_to_R_J_only'
    assert cert['global_trajectory_shadowing'] == 'not_claimed'
    assert cert['reference_decision_within_precision_cap'] == 'not_proved_for_future_steps'
    assert all(s['reference_decision_within_precision_cap']=='not_proved_for_future_steps' for s in cert['shells'])
    assert cert['tail']['reference_decision_within_precision_cap']=='not_proved_for_future_steps'
    assert cert['energy_hartree']['total'] >= cert['finite_energy_hartree']['total']


def test_outgoing_chain_cannot_turn_zero_progress_into_escape():
    o = outer()
    assert hasattr(o,'certify_outgoing_outer'), 'outer shell composition is not implemented'
    with pytest.raises(o.NotCertified):
        o.certify_outgoing_outer(run_at(p=(Q(-1),Q(0),Q(0))),Q(2))
    with pytest.raises(o.NotCertified):
        o.certify_outgoing_outer(run_at(Q(10**9),(B.UP,Q(0),Q(0))),2*B.UP)


def test_small_outward_momentum_survives_radial_drag_induction():
    o = outer()
    run = run_at(p=(Q(1,5),Q(0),Q(0)))
    cert = o.certify_shell(run,Q(20),Q(201,10),Q(2,5),600)
    assert cert['w_loss_per_step'] > 0
    old = norm2(C.relative(run.pos,*run.atoms))
    for _ in range(cert['max_steps']):
        C.step(run)
        new = norm2(C.relative(run.pos,*run.atoms))
        assert new-old >= cert['g_min']
        old = new
        if new >= Q(201,10)**2:
            return
    pytest.fail('radial drag invalidated the proved exit count')


def test_mutation_omitted_radial_drag_is_detected_by_actual_steps(monkeypatch):
    o = outer()
    real = o._shell_induction
    def missing_loss(a,b,p_hi,p_lo,w0,p_cap,n,width):
        record = real(a,b,p_hi,p_lo,w0,p_cap,n,width)
        omitted = n*record['w_loss_per_step']
        assert omitted > 0
        record['g_min'] += 2*o.ALPHA*omitted
        record['w_floor'] += omitted
        record['max_steps'] = o.residence_steps(width,record['g_min'])
        return record
    monkeypatch.setattr(o,'_shell_induction',missing_loss)
    with pytest.raises(AssertionError):
        test_small_outward_momentum_survives_radial_drag_induction()


def test_mutation_residence_floor_is_detected_by_actual_exit(monkeypatch):
    o = outer()
    monkeypatch.setattr(o,'residence_steps',lambda width,g: int(width//g))
    with pytest.raises(pytest.fail.Exception):
        test_induction_covers_real_quantized_steps_and_exit((Q(1),Q(0),Q(0)))


def test_generated_example_preserves_exact_bounds_and_code_provenance():
    import json
    from pathlib import Path
    from a_reference import c1b1_outer_chain as chain
    assert hasattr(chain,'example_report'), 'analytic proof example is not implemented'
    report = chain.example_report()
    assert report['kind']=='analytic_certificate_example_not_measurement'
    assert len(report['source_sha256'])==7
    cert=report['certificate']
    assert Q(cert['energy_hartree']['total']) == sum((Q(v) for k,v in cert['energy_hartree'].items() if k!='total'),Q(0))
    assert cert['angular_scope']=='finite_entry_to_R_J_only'
    assert cert['reference_decision_within_precision_cap']=='not_proved_for_future_steps'
    path=Path(__file__).resolve().parents[1]/'a_reference/fixtures/c1b1_outer_bootstrap_example_v1.json'
    assert json.loads(path.read_text(encoding='utf-8')) == report
