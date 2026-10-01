"""Independent KDK diagnostics: catch force sign, half-kick and gating faults."""
import ast
from pathlib import Path
import mpmath as m
import pytest


def test_kdk_harmonic_hand_computed_and_reversible():
    from c1b1_o1_diagnostic.kdk import step
    with m.workdps(50):
        force = lambda q: [-x for x in q]
        q, p = step([m.mpf(1), m.mpf(0)], [m.mpf(0), m.mpf(0)], m.mpf('.2'), m.mpf(1), force)
        assert abs(q[0]-m.mpf('.98')) < m.mpf('1e-45')
        assert abs(p[0]-m.mpf('-.198')) < m.mpf('1e-45')
        q, p = step(q, p, m.mpf('-.2'), m.mpf(1), force)
        assert abs(q[0]-1)+abs(p[0]) < m.mpf('1e-45')


@pytest.mark.parametrize('radius', ['5.4', '6.88', '9.5', '10', '20.01'])
def test_analytic_pes_derivative_matches_separate_numerical_derivative(radius):
    from c1b1_o1_diagnostic.kdk import Lang
    from c1b1_o1.model import Potential
    with m.workdps(60):
        r = m.mpf(radius)
        v, dv = Lang().value_derivative(r)
        assert abs(v-Potential()(r)) < m.mpf('1e-50')
        assert abs(dv-m.diff(Potential(), r)) < m.mpf('1e-50')


@pytest.mark.parametrize('hp,prod,want', [
    ('0.000013', '0.00001300001', 'TIME_DISCRETIZATION_SUPPORTED'),
    ('0.00000000001', '0.000013', 'FIXED_POINT_SUPPORTED_STOP'),
    ('0.000006', '0.000013', 'UNRESOLVED_STOP'),
    ('nan', '0.000013', 'UNRESOLVED_STOP'),
])
def test_gate_separates_candidates_without_loosening_o1(hp, prod, want):
    from c1b1_o1_diagnostic.kdk import isolate
    assert isolate(m.mpf(0), m.mpf(hp), m.mpf(prod), m.mpf('1e-25'))['verdict'] == want


def test_unstable_arithmetic_stops_dt_reduction():
    from c1b1_o1_diagnostic.kdk import isolate
    assert isolate(m.mpf(0), m.mpf('.000013'), m.mpf('.000013'), m.mpf('1e-15'))['verdict'] == 'UNRESOLVED_STOP'


def test_raw_relative_reduction_preserves_exact_binary_values():
    from c1b1_o1_diagnostic.kdk import relative
    with m.workdps(60):
        raw = [-2**48, 0, 0, -2**80, 0, 0, 2**48, 0, 0, 2**80, 0, 0]
        q, p = relative(raw)
        assert q == [2, 0] and p == [1, 0]


def test_independence_no_executor_or_verifier_imports():
    files = list(Path('c1b1_o1_diagnostic').glob('*.py'))
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
            assert not any(n.split('.')[0] in {'a_reference', 'a_numeric', 'engine', 'audit', 'c1b1_replay'} for n in names)


def test_free_trajectory_exit_chord_and_energy(tmp_path):
    from c1b1_o1_diagnostic.study import simulate
    class Free:
        def value_derivative(self, r):
            return m.mpf(0), m.mpf(0)
    raw = [-10*2**48, 0, 0, 3*2**80, -2**80, 0,
           10*2**48, 0, 0, -3*2**80, 2**80, 0]
    result = simulate(raw, 1, 40, '1', '20', tmp_path/'free.gz', Free)
    with m.workdps(40):
        assert result['steps'] == 12
        assert abs(m.mpf(result['chi'])) < m.mpf('1e-30')
        assert abs(m.mpf(result['r_min_chord'])-20/m.sqrt(10)) < m.mpf('1e-30')
        assert m.mpf(result['energy_max_change_De']) == 0


def test_outlet_extension_preserves_free_momentum_direction():
    from c1b1_o1_diagnostic.study import extend_reference
    with m.workdps(50):
        ref = dict(H='5', L='20', chi='0', direction='0', sweep='1', r_min='1', time='12')
        result = extend_reference(ref, m.mpf(20), m.mpf(21), m.mpf(1), lambda r: m.mpf(0))
        assert abs(m.mpf(result['chi'])) < m.mpf('1e-40')
        assert m.mpf(result['time']) > 12


def test_evidence_tamper_stops_before_calculation(tmp_path):
    from c1b1_o1_diagnostic.study import verify_artifacts
    path = tmp_path/'evidence'; path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='evidence hash'):
        verify_artifacts({str(path): {'sha256': '0'*64}})


def test_stored_reference_uses_exact_raw_outlet_not_display_float():
    from c1b1_o1_diagnostic.study import original_evidence
    row, ref, observation, reproduction = original_evidence()
    assert row['id'] == 'boundary_pass'
    assert observation['verdict'] == 'DISAGREE'
    assert m.mpf(reproduction['stored_angle_difference']) < m.mpf('1e-14')
