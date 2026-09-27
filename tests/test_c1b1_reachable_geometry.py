"""Actual FX KDK transitions and fault injection for induced projections."""
from fractions import Fraction as Q

import pytest

from a_numeric import FixedPoint
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_reachable_geometry as G


def run_at(p=(Q(1), Q(0), Q(0)), common=(Q(0), Q(0), Q(0))):
    return C.new_run(FixedPoint(96, 48), 40, (-10, 7, 3),
                     tuple(c-x for c, x in zip(common, p)), (10, 7, 3),
                     tuple(c+x for c, x in zip(common, p)),
                     momentum_profile=FixedPoint(96, 80))


def projection(run):
    shell = O.certify_shell(run, Q(20), Q(2001, 100), Q(2), 32)
    geometry = {'initial_state': shell['initial_state'], 'shells': [shell]}
    return shell, G._attach(run, geometry)


def assert_actual_contained(run):
    shell, proof = projection(run)
    constraint = proof['shells'][0]
    q0, p0, _ = O._state(run)
    for n in range(shell['max_steps']+1):
        q, p, _ = O._state(run)
        raw = tuple(x/B.UX for x in q)
        assert all(x.denominator == 1 for x in raw)
        assert all(lo <= x <= hi for x, (lo, hi) in zip(raw, constraint['root_box']))
        assert O._norm2(tuple(x-y for x, y in zip(p, p0))) <= constraint['momentum_change_norm_cap']**2
        assert O._norm2(G.cross(q, p)) <= constraint['relative_angular_norm_cap']**2
        assert G.exclude_direction_cell(tuple((int(x), int(x)) for x in raw), constraint) is None
        for axis in proof['exact_zero_relative_axes']:
            assert q[axis] == p[axis] == 0
            assert run.atoms[0].r[axis] == run.atoms[1].r[axis]
            assert run.atoms[0].p[axis] == run.atoms[1].p[axis]
        if O._norm2(q) >= shell['b']**2:
            return proof
        assert n < shell['max_steps']
        C.step(run)
    pytest.fail('actual exit did not occur within the proved count')


@pytest.mark.parametrize('p,common,zero_axes', [
    ((Q(1), Q(0), Q(0)), (Q(0), Q(1, 7), Q(-1, 9)), (1, 2)),
    ((Q(1), Q(1, 10), Q(0)), (Q(1, 11), Q(0), Q(1, 13)), (2,)),
    ((Q(1), Q(1, 10), Q(-1, 10)), (Q(0),)*3, ()),
])
def test_actual_kdk_and_moving_center_of_mass_stay_in_projection(p, common, zero_axes):
    proof = assert_actual_contained(run_at(p, common))
    assert proof['exact_zero_relative_axes'] == zero_axes
    assert proof['relative_coordinate_dimension'] == 3-len(zero_axes)
    assert proof['oblique_plane_preservation'] == 'not_assumed'
    assert proof['rounding_decision_completeness'] == 'not_proved'


def test_composed_root_boxes_are_narrowed_without_replay_or_D_valid(monkeypatch):
    def forbidden(*args):
        raise AssertionError('projection must come from induction, not measured states')
    monkeypatch.setattr(C, 'step', forbidden)
    monkeypatch.setattr(C.Run, 'validation', property(forbidden))
    run = run_at((Q(1), Q(1, 10), Q(0)))
    before = tuple((a.r, a.p) for a in run.atoms)
    geometry, proof = G.certify_outgoing_reachable(run, Q(2))
    assert len(proof['shells']) == len(geometry['shells'])
    assert proof['exact_zero_relative_axes'] == (2,)
    for shell, record in zip(geometry['shells'], proof['shells']):
        bound = int(shell['guard_b']/B.UX)
        assert record['root_box'][2] == (0, 0)
        assert record['root_box'][0][0] >= 20*2**48
        assert all(-bound <= lo <= hi <= bound for lo, hi in record['root_box'])
    assert run.t_steps == 0 and run._validation is None
    assert before == tuple((a.r, a.p) for a in run.atoms)


def test_oblique_plane_is_not_exactly_preserved_by_component_rounding():
    pos, mom = FixedPoint(96, 48), FixedPoint(96, 80)
    px = mom.from_exact(C.AR40_MASS_ME*B.UX/100)
    # Initially r_z=r_x+r_y and p_z=p_x+p_y. Drift raw x=y~0.4,
    # z~0.8: half-even gives (0,0,1), outside that oblique plane.
    atom = C.Atom('Ar40', (20*2**48, 0, 20*2**48), (px, px, 2*px))
    moved, _ = C._drift(pos, mom, atom, B.H, 'v2')
    assert atom.r[2] == atom.r[0]+atom.r[1]
    assert atom.p[2] == atom.p[0]+atom.p[1]
    assert moved.r[2] != moved.r[0]+moved.r[1]


def test_zero_position_with_nonzero_relative_momentum_is_not_a_frozen_axis():
    proof = assert_actual_contained(run_at((Q(1), Q(0), Q(1, 10))))
    assert proof['exact_zero_relative_axes'] == (1,)
    assert proof['shells'][0]['root_box'][2][1] > 0


def test_mutation_ignoring_momentum_in_plane_induction_is_detected(monkeypatch):
    monkeypatch.setattr(G, '_exact_zero_axes', lambda q, p: tuple(k for k in range(3) if q[k] == 0))
    with pytest.raises(AssertionError):
        test_zero_position_with_nonzero_relative_momentum_is_not_a_frozen_axis()


def test_mutation_omitting_initial_angular_momentum_is_detected(monkeypatch):
    monkeypatch.setattr(G, 'cross', lambda q, p: (Q(0),)*3)
    with pytest.raises(AssertionError):
        assert_actual_contained(run_at((Q(1), Q(1, 10), Q(0))))


def test_cone_exclusions_are_strict_and_do_not_drop_boundaries():
    _, proof = projection(run_at())
    constraint = proof['shells'][0]
    behind = ((-20*2**48, -20*2**48), (0, 0), (0, 0))
    assert G.exclude_direction_cell(behind, constraint) == 'empty_outward_dot_intersection'
    transverse = ((20*2**48, 20*2**48), (2**48, 2**48), (0, 0))
    assert G.exclude_direction_cell(transverse, constraint) == 'empty_direction_cross_intersection'
    # Equality is retained even where the sufficient inequalities are tight.
    boundary = dict(constraint, dot_initial_momentum_lower=Q(20),
                    cross_initial_momentum_norm_cap=Q(1))
    assert G.exclude_direction_cell(transverse, boundary) is None
