"""Rounding proof obligations: a finite count is not a decision proof."""
from fractions import Fraction as Q
import importlib
import importlib.util

import pytest

from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_numeric import FixedPoint
from copy import deepcopy


def decisions():
    assert importlib.util.find_spec('a_reference.c1b1_rounding_completeness') is not None, 'rounding certificates not implemented'
    return importlib.import_module('a_reference.c1b1_rounding_completeness')


def test_large_negative_exp_upper_end_must_depend_on_precision():
    # e < 3, hence e^-4096 > 3^-4096. A fixed 4096 cutoff at M=8192
    # would claim an upper end 2^-8192 < 3^-4096: a false enclosure.
    _,hi = C._exp_neg((4096<<8192,4096<<8192),8192)
    assert Q(hi,1<<8192) > Q(1,3**4096)


def test_opposite_overflow_endpoints_are_not_a_proof_of_overflow():
    # The exact value 0 is in both enclosures. Only the coarse endpoints overflow.
    def enclosure(bits):
        return (Q(-2**20),Q(2**20)) if bits==128 else (Q(0),Q(0))
    assert C._decide(FixedPoint(96,80),enclosure)==0


def test_real_far_tail_impulse_refines_past_coarse_endpoint_overflow():
    assert C.impulse((Q(2**47),Q(0),Q(0)),Q(20),FixedPoint(96,80))==(0,0,0)


def test_uniform_tail_is_a_decision_cover_not_a_sampled_trajectory():
    d = decisions()
    report = d.certify_zero_tail()
    assert report['scope']=='all_FX96_48_relative_geometries_in_tail'
    assert report['max_decision_bits'] <= C.MAX_PRECISION_BITS
    assert report['all_half_kicks']==(0,0,0)
    assert report['cells'][0]['a']==10240
    assert report['cells'][-1]['b']==2**49
    assert all(c['impulse_abs_cap']<Q(1,2**81) for c in report['cells'])
    assert all(c['all_exp_shortcut'] for c in report['cells'])
    assert all(c['minimum_exp_argument_lower']>=c['decision_bits']*Q(6932,10000) for c in report['cells'])
    assert all(x['b']==y['a'] for x,y in zip(report['cells'],report['cells'][1:]))
    assert report['finite_pre_tail_completeness']=='not_proved'


def run_at(r=Q(20),p=(Q(1),Q(0),Q(0))):
    return C.new_run(FixedPoint(96,48),Q(40),(-r/2,0,0),tuple(-x for x in p),
                     (r/2,0,0),p,momentum_profile=FixedPoint(96,80))


@pytest.mark.parametrize('q',[(Q(20),Q(0),Q(0)),(Q(21),Q(-1),Q(3))])
def test_point_witness_is_exact_actual_impulse_with_signed_intervals(q):
    d = decisions()
    proof = d.certify_impulse_point(q)
    assert proof['rounded_impulse']==C.impulse(q,Q(20),FixedPoint(96,80))
    assert proof['max_decision_bits']<=C.MAX_PRECISION_BITS
    for component,raw in zip(proof['components'],proof['rounded_impulse']):
        lo,hi = component['impulse_interval']
        assert lo<=hi
        assert FixedPoint(96,80).from_exact(lo)==FixedPoint(96,80).from_exact(hi)==raw


def test_finite_prefix_must_not_remove_global_condition_or_mutate_run():
    run = run_at()
    before = deepcopy(run,{id(run.pos):run.pos,id(run.mom):run.mom})
    proof = decisions().certify_outgoing_decisions(run,Q(2),max_steps=2)
    assert proof['status']=='incomplete_budget'
    assert proof['checked_transition_steps']==2
    assert proof['finite_pre_tail_completeness']=='not_proved'
    assert proof['rounding_decision_completeness']=='not_proved'
    assert proof['tail_decision']['all_half_kicks']==(0,0,0)
    assert len(proof['point_witnesses'])==3
    assert run==before and run._validation is None


def test_late_outgoing_uniform_zero_cells_close_without_trajectory(monkeypatch):
    run = run_at(Q(10240)-Q(1,100))
    def forbidden(_):
        raise AssertionError('a uniform zero cover must not measure a trajectory')
    monkeypatch.setattr(C,'step',forbidden)
    proof = decisions().certify_outgoing_decisions(run,Q(2),max_steps=0)
    assert proof['status']=='certified'
    assert proof['finite_pre_tail_completeness']=='certified_uniform_zero_cells'
    assert proof['rounding_decision_completeness']=='certified_for_this_initial_state'
    assert proof['checked_transition_steps']==0
    assert proof['zero_finite_cells']


def test_precision_cap_exhaustion_never_yields_a_point_certificate(monkeypatch):
    monkeypatch.setattr(C,'START_PRECISION_BITS',32)
    monkeypatch.setattr(C,'MAX_PRECISION_BITS',32)
    with pytest.raises(O.NotCertified,match='separation'):
        decisions().certify_impulse_point((Q(20),Q(0),Q(0)))
    with pytest.raises(C.ReferenceUndecided):
        C.impulse((Q(20),Q(0),Q(0)),Q(20),FixedPoint(96,80))


def test_tail_cover_cannot_be_reused_under_a_smaller_precision_cap(monkeypatch):
    decisions().certify_zero_tail()
    monkeypatch.setattr(C,'MAX_PRECISION_BITS',128)
    with pytest.raises(O.NotCertified,match='precision cap'):
        decisions().certify_zero_tail()


def test_returned_tail_records_do_not_poison_cached_proof():
    d = decisions()
    report = d.certify_zero_tail()
    report['cells'][0]['impulse_abs_cap']=Q(1)
    assert d.certify_zero_tail()['cells'][0]['impulse_abs_cap']<Q(1,2**81)


def test_nonzero_cell_cannot_be_claimed_as_uniform_zero():
    with pytest.raises(O.NotCertified,match='nonzero'):
        decisions().zero_cell(Q(20),Q(21))


@pytest.mark.parametrize('q',[(Q(20)+Q(1,2**49),Q(0),Q(0)),(Q(2**48),Q(0),Q(0)),(Q(19),Q(0),Q(0))])
def test_point_certificate_refuses_outside_grid_or_outer_domain(q):
    with pytest.raises(O.NotCertified,match='represented'):
        decisions().certify_impulse_point(q)


def test_undecided_future_endpoint_is_preserved_as_incomplete(monkeypatch):
    def undecided(_):
        raise C.ReferenceUndecided('injected future endpoint decision failure')
    monkeypatch.setattr(C,'step',undecided)
    run=run_at()
    proof=decisions().certify_outgoing_decisions(run,Q(2),max_steps=1)
    assert proof['status']=='not_certified_decision'
    assert proof['rounding_decision_completeness']=='not_proved'
    assert proof['failure']['kind']=='reference_undecided'
    assert 'future endpoint' in proof['failure']['message']
    assert run.t_steps==0


def test_mutation_fixed_exp_cutoff_is_detected(monkeypatch):
    real=C._exp_neg
    def bad(x,bits):
        return (0,1) if x[0]>=4096<<bits else real(x,bits)
    monkeypatch.setattr(C,'_exp_neg',bad)
    with pytest.raises(AssertionError):
        test_large_negative_exp_upper_end_must_depend_on_precision()


def test_mutation_tail_cover_gap_is_detected(monkeypatch):
    d=decisions()
    cells=d._tail_cover(C.START_PRECISION_BITS,C.MAX_PRECISION_BITS)
    monkeypatch.setattr(d,'_tail_cover',lambda *_: cells[:3]+cells[4:])
    with pytest.raises(AssertionError):
        test_uniform_tail_is_a_decision_cover_not_a_sampled_trajectory()


def test_mutation_prefix_promoted_to_complete_is_detected(monkeypatch):
    d=decisions()
    real=d.certify_outgoing_decisions
    def bad(*args,**kwargs):
        result=real(*args,**kwargs)
        result['status']='certified'
        result['rounding_decision_completeness']='certified_for_this_initial_state'
        return result
    monkeypatch.setattr(d,'certify_outgoing_decisions',bad)
    with pytest.raises(AssertionError):
        test_finite_prefix_must_not_remove_global_condition_or_mutate_run()


@pytest.mark.parametrize('sign',[-1,1])
def test_same_side_true_overflow_is_not_suppressed(sign):
    with pytest.raises(C.VMHalt,match='overflow'):
        C._decide(FixedPoint(96,80),lambda _: (sign*Q(2**20),sign*Q(2**20)))


def test_even_one_value_can_remain_undecided_at_finite_cap():
    # A decision-helper counterexample, NOT an alleged reachable Lang force.
    value=Q(1,2**81)+Q(1,2**20000)
    def enclosure(bits):
        scaled=value*(1<<bits)
        lo=scaled.numerator//scaled.denominator
        hi=-(-scaled.numerator//scaled.denominator)
        return Q(lo,1<<bits),Q(hi,1<<bits)
    assert FixedPoint(96,80).from_exact(value)==1
    with pytest.raises(C.ReferenceUndecided):
        C._decide(FixedPoint(96,80),enclosure)


def test_rounding_proof_does_not_read_D_valid(monkeypatch):
    run=run_at(Q(10240)-Q(1,100))
    def forbidden(_):
        raise AssertionError('rounding proof must be independent of D_valid')
    monkeypatch.setattr(C.Run,'validation',property(forbidden))
    assert decisions().certify_outgoing_decisions(run,Q(2),max_steps=0)['status']=='certified'


def test_static_example_is_regenerated_with_exact_code_provenance():
    import json
    from pathlib import Path
    d=decisions()
    assert hasattr(d,'example_report'), 'rounding proof example missing'
    report=d.example_report()
    assert report['kind']=='analytic_rounding_decision_examples_not_measurements'
    assert report['uniform_tail']['max_decision_bits']==512
    assert report['late_outgoing']['status']=='certified'
    assert report['early_outgoing_prefix']['status']=='incomplete_budget'
    assert report['induced_enclosure_attempt']['status']=='not_certified'
    assert report['induced_enclosure_attempt']['checked_cells']==64
    assert report['induced_enclosure_attempt']['unresolved_cells']
    path=Path(__file__).resolve().parents[1]/'a_reference/fixtures/c1b1_rounding_decision_examples_v1.json'
    assert json.loads(path.read_text(encoding='utf-8'))==report
