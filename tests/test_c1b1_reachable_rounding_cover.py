"""Adaptive covers must cover the induced grid, not promote a sampled path."""
from fractions import Fraction as Q
import importlib
import pytest

from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_numeric import FixedPoint


def cover():
    from a_reference import c1b1_rounding_completeness as D
    assert hasattr(D,'certify_reachable_rounding'), 'induced enclosure cover missing'
    return D


def run_at(r):
    return C.new_run(FixedPoint(96,48),Q(40),(-r/2,0,0),(-1,0,0),
                     (r/2,0,0),(1,0,0),momentum_profile=FixedPoint(96,80))


def test_nonzero_exact_grid_cell_matches_actual_signed_impulse():
    d=cover()
    raw=(20*2**48,-2**48,3*2**48)
    proof=d.certify_grid_cell(tuple((x,x) for x in raw),Q(20),Q(21))
    assert proof['rounded_impulse']==C.impulse(tuple(Q(x,2**48) for x in raw),Q(20),FixedPoint(96,80))
    assert proof['rounded_impulse']!=(0,0,0)


def test_parent_exp_cover_contains_actual_taylor_and_shortcut_endpoints():
    d=cover()
    for bits in (128,256):
        for a,b in ((Q(20),Q(21)),(Q(80),Q(90)),(Q(100),Q(200))):
            x=(int(a*(1<<bits)),int(b*(1<<bits)))
            lo,hi=d.execution_exp_cover(x,bits)
            for v in (x[0],(x[0]+x[1])//2,x[1]):
                actual=C._exp_neg((v,v),bits)
                assert lo<=actual[0]<=actual[1]<=hi


def test_nonzero_induced_shell_budget_exhaustion_is_not_certified(monkeypatch):
    d=cover()
    def forbidden(_):
        raise AssertionError('analytic cover must not replay a trajectory')
    monkeypatch.setattr(C,'step',forbidden)
    run=run_at(Q(20))
    with pytest.raises(O.NotCertified,match='unresolved') as failure:
        d.certify_reachable_rounding(run,Q(2),max_cells=4)
    assert failure.value.report['scope']=='shell_induction_reachable_enclosure_projection'
    assert failure.value.report['status']=='not_certified'
    assert failure.value.report['unresolved_cells']
    assert failure.value.report['checked_cells']<=4
    assert run.t_steps==0 and run._validation is None


def test_late_induced_enclosure_cover_closes_without_replay(monkeypatch):
    d=cover()
    def forbidden(_):
        raise AssertionError('no measured path permitted')
    monkeypatch.setattr(C,'step',forbidden)
    proof=d.certify_reachable_rounding(run_at(Q(10240)-Q(1,100)),Q(2),max_cells=4)
    assert proof['status']=='certified'
    assert proof['rounding_decision_completeness']=='certified_for_induced_enclosure'
    assert proof['tail_decision']['max_decision_bits']<=16384


def test_grid_split_has_neither_gap_nor_lattice_overlap():
    d=cover()
    parent=((-3,4),(0,0),(1,2))
    left,right=d.split_grid_cell(parent)
    expected={(x,0,z) for x in range(-3,5) for z in range(1,3)}
    def points(box):
        return {(x,y,z) for x in range(box[0][0],box[0][1]+1)
                for y in range(box[1][0],box[1][1]+1)
                for z in range(box[2][0],box[2][1]+1)}
    assert points(left)|points(right)==expected
    assert not points(left)&points(right)


def test_nonzero_multistate_cell_contains_actual_endpoint_results():
    d=cover()
    raw=2000*2**48
    box=((raw,raw+1),(0,0),(0,0))
    proof=d.certify_grid_cell(box,Q(2000),Q(2001))
    assert proof['kind']=='uniform_rounding_cell'
    assert proof['rounded_impulse']!=(0,0,0)
    for x in (raw,raw+1):
        assert proof['rounded_impulse']==C.impulse((Q(x,2**48),Q(0),Q(0)),Q(20),FixedPoint(96,80))


def test_lowered_cap_must_not_certify_nonzero_grid_cell(monkeypatch):
    d=cover()
    monkeypatch.setattr(C,'START_PRECISION_BITS',32)
    monkeypatch.setattr(C,'MAX_PRECISION_BITS',32)
    raw=20*2**48
    with pytest.raises(O.NotCertified):
        d.certify_grid_cell(((raw,raw),(0,0),(0,0)),Q(20),Q(21))


def test_mutation_lattice_gap_is_detected(monkeypatch):
    d=cover()
    real=d.split_grid_cell
    def bad(box):
        left,right=real(box)
        right=list(right)
        for axis in range(3):
            if left[axis]!=right[axis]:
                right[axis]=(right[axis][0]+1,right[axis][1])
                break
        return left,tuple(right)
    monkeypatch.setattr(d,'split_grid_cell',bad)
    with pytest.raises(AssertionError):
        test_grid_split_has_neither_gap_nor_lattice_overlap()


def test_exact_tie_inside_nonsingleton_cell_is_not_assumed_decidable(monkeypatch):
    # Deliberate evaluator fault, not a claim that Lang has this reachable tie.
    d=cover()
    bits=128
    monkeypatch.setattr(C,'START_PRECISION_BITS',bits)
    monkeypatch.setattr(C,'MAX_PRECISION_BITS',bits)
    def tie_model(radius,m,ret,**kwargs):
        # q_x=20, h/2=20: 400/(800*2^80)=2^-81 exactly.
        return (0,0),C._const(Q(-1,800*2**80),m),(1<<m,1<<m)
    monkeypatch.setattr(C,'_model_R',tie_model)
    with pytest.raises(C.ReferenceUndecided):
        C.impulse((Q(20),Q(0),Q(0)),Q(20),FixedPoint(96,80))
    with pytest.raises(O.NotCertified,match='unresolved'):
        d.certify_grid_cell(((20*2**48,20*2**48+1),(0,0),(0,0)),Q(20),Q(21))


@pytest.mark.parametrize('ends',[(0,0),(0,1),(1,2**130),
                               (89*2**128,90*2**128),
                               (2**134-1,2**134+1)])
def test_exp_cover_also_contains_mixed_endpoint_evaluator(ends):
    d=cover()
    lo,hi=d.execution_exp_cover(ends,128)
    actual=C._exp_neg(ends,128)
    assert lo<=actual[0]<=actual[1]<=hi
