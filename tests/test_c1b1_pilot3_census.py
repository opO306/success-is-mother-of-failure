"""Catch omitted constructor routes, incorrect gcd attribution and observer effects."""
from fractions import Fraction as Q
from pathlib import Path
import importlib
import sys


def observer():
    assert Path('experiments/verified_superoptimizer_c1b1/pilot3_census.py').exists(), 'call-site observer missing'
    return importlib.import_module('experiments.verified_superoptimizer_c1b1.pilot3_census')


def arithmetic():
    a = Q(3, 4)
    b = Q(5, 6)
    return a * b, a + a


def repeated():
    return [Q(3, 4) * 2 for _ in range(5)]


def test_observer_counts_both_constructor_routes_and_gcd(tmp_path):
    c = observer().Census(tmp_path/'values.sqlite')
    with c:
        assert arithmetic() == (Q(5, 8), Q(3, 2))
    # Observe only arithmetic, not construction of expected literals.
    rows = [r for r in c.summary()['sites'] if r['function'] == 'arithmetic']
    assert sum(r['new'] for r in rows) == 2
    assert sum(r['coprime'] for r in rows) == 2
    assert sum(r['mul'] for r in rows) == 1
    assert sum(r['gcd'] for r in rows) == 6
    assert sum(r['distinct_values'] for r in rows) == 4
    assert all(r['exclusive_cpu_seconds'] >= 0 for r in rows)


def test_repetition_uses_exact_numerator_denominator_identity(tmp_path):
    c = observer().Census(tmp_path/'values.sqlite')
    with c:
        got = repeated()
    assert got == [Q(3, 2)]*5
    # Python 3.12 (PEP 709) inlines the comprehension into repeated().
    rows = [r for r in c.summary()['sites'] if r['function'] in ('repeated','<listcomp>')]
    # Fraction's int operand fallback also constructs Fraction(2) each time.
    # Independently checked: cProfile __new__=10, _from_coprime_ints=5.
    assert sum(r['new']+r['coprime'] for r in rows) == 15
    assert sum(r['distinct_values'] for r in rows) == 3
    assert sum(r['repeat_creations'] for r in rows) == 12


def test_observer_restores_hook_after_exception_and_changes_no_arithmetic(tmp_path):
    import math
    descriptors = dict(Q.__dict__)
    original_gcd = math.gcd
    m = observer(); before = sys.getprofile(); c = m.Census(tmp_path/'values.sqlite')
    try:
        with c:
            raise RuntimeError('intentional observer exit')
    except RuntimeError:
        pass
    assert sys.getprofile() is before
    assert dict(Q.__dict__) == descriptors and math.gcd is original_gcd
    assert arithmetic() == (Q(5, 8), Q(3, 2))


def test_observed_real_combined_steps_keep_every_state(tmp_path):
    import copy
    from a_reference import c1b1_runtime as R
    from experiments.verified_superoptimizer_c1b1 import integration_stages as I
    base = I.make_run(dict(e='9',b_frac='0'))
    traced = copy.copy(base)
    a,b = R.bind(base,mode='fast_combined'),R.bind(traced,mode='fast_combined')
    c=observer().Census(tmp_path/'values.sqlite')
    for _ in range(10):
        a.step()
        with c:
            b.step()
        assert I.raw(base)==I.raw(traced)
    counts=c.summary()['counts']
    assert counts['new']>0 and counts['coprime']>0 and counts['gcd']>counts['mul']>0


def test_real_step_counts_match_independent_unwrapped_cprofile(tmp_path):
    import cProfile,pstats,copy
    from a_reference import c1b1_runtime as R
    from experiments.verified_superoptimizer_c1b1 import integration_stages as I
    run=I.make_run(dict(e='9',b_frac='0'));other=copy.copy(run)
    a,b=R.bind(run,mode='fast_combined'),R.bind(other,mode='fast_combined')
    profile=cProfile.Profile();profile.runcall(a.step)
    stats=pstats.Stats(profile).stats
    want={}
    for key,name in [('new','__new__'),('coprime','_from_coprime_ints'),('mul','_mul'),('forward','forward')]:
        want[key]=sum(v[1] for (f,l,n),v in stats.items() if n==name and f.endswith('fractions.py'))
    want['gcd']=sum(v[1] for (f,l,n),v in stats.items() if 'math.gcd' in n)
    c=observer().Census(tmp_path/'values.sqlite')
    with c:b.step()
    assert c.summary()['counts']==want
    assert I.raw(run)==I.raw(other)
