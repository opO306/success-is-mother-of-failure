"""C1-B1 runtime local witness prototype: refuse at 128 bits -> re-decide that impulse -> verify -> resume must give,
step by step, the raw states of the plain full-cap executor. Witnesses are executor rounding-decision
re-verification witnesses (same evaluator), not independent physics proofs."""
import copy
import json
from fractions import Fraction as Q

import pytest

import a_reference.c1b1_two_atom as C
from a_reference import c1b1_runtime_local_witness as W
from a_reference import c1b1_stress_survey as X

N = 200                                                     # e = 9 De, b = Re/2: 200 steps cross the close approach


def mk(e=9, bf=Q(1, 2)):
    st = X.canonical(Q(e), Q(bf) * X.RE)
    return C.new_run(X.POS, X.DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=X.MOM)


def plain(n, e=9, bf=Q(1, 2)):
    run, tel = mk(e, bf), X.Telemetry()
    states = [W._raw(run)]
    with X.instrumented(tel):
        for _ in range(n):
            C.step(run)
            states.append(W._raw(run))
    return states, tel


@pytest.fixture(scope='module')
def witness_run():
    return W.run_with_local_witnesses(mk(), N)


@pytest.fixture(scope='module')
def one_witness(witness_run):
    return witness_run[1][0]


def test_every_step_equals_the_plain_executor_and_counts_match(witness_run):
    """The core test (2-5): every raw state, not only the last; one witness per refusal; and the components that
    needed more than 128 bits are exactly the plain run's 256-bit decisions."""
    states, witnesses, refusals = witness_run
    ref, tel = plain(N)
    assert states == ref
    assert len(witnesses) == len(refusals) >= 3
    assert sum(len(r['axes_above_exec_cap']) for r in refusals) == tel.decisions[256]
    assert set(tel.decisions) == {128, 256}


def test_the_plain_run_restores_the_executor(witness_run):
    assert C.impulse.__module__ == 'a_reference.c1b1_two_atom' and C._decide.__module__ == 'a_reference.c1b1_two_atom'
    assert C.MAX_PRECISION_BITS == W.FULL_CAP == 16384


def test_a_witness_binds_model_profiles_step_and_schedule(one_witness):
    b = one_witness['binding']
    assert b['precision_schedule'] == [128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    assert b['position_profile']['name'] == 'FX(96,48)' and b['momentum_profile']['name'] == 'FX(96,80)'
    assert (b['dt'], b['dt_kick'], b['retardation'], b['drift']) == ('40', '20', True, 'v2')
    assert set(b['sources_lf_sha256']) == set(W.SOURCES) and b['model_fingerprint']
    assert any(not c.get('zero_input') and c['bits'] == 256 for c in one_witness['components'])


def _tamper(w, f):
    w = copy.deepcopy(w)
    f(w)
    return w


def _first_nonzero(w):
    return next(c for c in w['components'] if not c.get('zero_input'))


TAMPERS = {
    'raw_plus_one': lambda w: (_first_nonzero(w).__setitem__('raw', _first_nonzero(w)['raw'] + 1),
                               w['impulse_raw'].__setitem__(_first_nonzero(w)['axis'], _first_nonzero(w)['raw'])),
    'impulse_raw_only': lambda w: w['impulse_raw'].__setitem__(_first_nonzero(w)['axis'], 12345),
    'bits_changed': lambda w: _first_nonzero(w).__setitem__('bits', 512),
    'bits_above_cap': lambda w: _first_nonzero(w).__setitem__('bits', 32768),
    'input_moved': lambda w: w['input']['dr'].__setitem__(0, str(Q(w['input']['dr'][0]) + Q(1, 1 << 48))),
    'axis_swapped': lambda w: w['components'].reverse(),
    'lo_changed': lambda w: _first_nonzero(w).__setitem__('lo', str(Q(_first_nonzero(w)['lo']) - Q(1, 1 << 90))),
    'hi_changed': lambda w: _first_nonzero(w).__setitem__('hi', str(Q(_first_nonzero(w)['hi']) + Q(1, 1 << 90))),
    'source_hash': lambda w: w['binding']['sources_lf_sha256'].__setitem__(W.SOURCES[0], '0' * 64),
    'model_fingerprint': lambda w: w['binding'].__setitem__('model_fingerprint', 'x'),
    'profile': lambda w: w['binding']['momentum_profile'].__setitem__('frac_bits', 79),
    'dt': lambda w: w['binding'].__setitem__('dt_kick', '21'),
    'retardation': lambda w: w['binding'].__setitem__('retardation', False),
    'schedule': lambda w: w['binding'].__setitem__('precision_schedule', [128, 256]),
    'version': lambda w: w.__setitem__('version', 'v-other'),
}


def test_the_stored_witness_verifies(one_witness):
    run = mk()
    assert W.verify_witness(json.loads(json.dumps(one_witness)), run) == tuple(one_witness['impulse_raw'])


@pytest.mark.parametrize('name', sorted(TAMPERS))
def test_every_tampered_witness_is_rejected(one_witness, name):
    with pytest.raises(W.NotWitnessed):
        W.verify_witness(_tamper(one_witness, TAMPERS[name]), mk())


def test_a_witness_is_used_only_for_exactly_its_input(one_witness):
    """Resume keys on the input the executor computes: a witness for another input never answers."""
    dr = tuple(Q(x) for x in one_witness['input']['dr'])
    verified = {W._key(dr, Q(20), X.MOM): (1, 2, 3)}
    seen = []
    other = (dr[0] + Q(1, 1 << 48), dr[1], dr[2])
    with W._executor_hooks(verified, seen):
        assert C.impulse(dr, Q(20), X.MOM) == (1, 2, 3)
        assert C.impulse(other, Q(20), X.MOM) != (1, 2, 3)


def test_resuming_without_a_witness_is_caught():
    """DEFECT switch: resume with the cap still at 128 and no witness -> the same input refuses again."""
    with pytest.raises(AssertionError, match='refused again|already has'):
        W.run_with_local_witnesses(mk(), N, use_witnesses=False)


def test_a_wrong_witness_value_would_change_the_world(one_witness, monkeypatch):
    """DEFECT: accept a witness value one ulp off without verification -> the trajectory differs from the plain
    run, so the core comparison (test 2-5) is able to see a wrong witness."""
    real_verify = W.verify_witness

    def lying_verify(w, run):
        J = list(real_verify(w, run))
        J[0] += 1
        return tuple(J)
    monkeypatch.setattr(W, 'verify_witness', lying_verify)
    states, _, _ = W.run_with_local_witnesses(mk(), N)
    assert states != plain(N)[0]


def test_the_full_schedule_is_never_exceeded():
    """2-7: a decision the builder's cap cannot close stays refused; a cap above the contract is itself refused."""
    dr = (Q(20) + 46 * Q(1, 1 << 48), Q(0), Q(0))          # needs 256 bits (see test_c1b1_step_fail_closed)
    run = mk()
    with pytest.raises(W.NotWitnessed):
        W.build_witness(dr, run, cap=128)
    with pytest.raises(W.NotWitnessed, match='above the contract cap'):
        W.build_witness(dr, run, cap=32768)
    assert W.build_witness(dr, run)['components'][0]['bits'] == 256
