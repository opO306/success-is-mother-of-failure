"""Post-acquisition checks from recorded scalars; no calculator invocation."""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

DOC = Path('docs/active/h2_force_v0')


def read(name):
    return json.loads((DOC/name).read_text(encoding='utf-8'))


def test_real_point_geometry_contract_and_guard_data():
    result = read('results.json')
    protocol = read('protocol.json')
    assert [x['R_decimal'] for x in result['points']] == protocol['R_bohr']
    for row in result['points']:
        assert row['process']['exit'] == 0
        assert row['basis'] == 'cc-pV5Z' and row['basis_size'] == 110
        assert row['singlet_dimension'] == 6105 and row['R_bohr'] == float(row['R_decimal'])
        assert row['numerical_guard_status'] == 'ACCEPTED'
        assert row['Smin'] > 1e-10
        for key, limit in [('orthogonality_l2', 1e-10), ('singlet_asymmetry', 1e-10),
                           ('eigen_residual_l2', 1e-9), ('vector_norm_error', 1e-10)]:
            assert Decimal(0) <= Decimal.from_float(row[key]) <= Decimal.from_float(limit)
        assert row['total_energy_hartree'] == row['electronic_energy_hartree'] + row['nuclear_repulsion_hartree']
        assert row['nuclear_repulsion_hartree'] == 1 / row['R_bohr']


def test_force_recomputed_independently_from_stored_scalars():
    result = read('results.json')
    e = {x['R_decimal']: Decimal.from_float(x['total_energy_hartree']) for x in result['points']}
    with localcontext() as ctx:
        ctx.prec = 100
        for force, left, right in zip(result['forces'], ['1.2','1.3','1.4'], ['1.4','1.5','1.6']):
            recomputed = (e[left] - e[right]) * Decimal(5)
            assert force['force_Eh_per_bohr'] == float(recomputed)
        assert e['1.4'] < e['1.3'] and e['1.4'] < e['1.5']
        assert result['forces'][0]['force_Eh_per_bohr'] > 0
        assert result['forces'][2]['force_Eh_per_bohr'] < 0


def test_executed_evidence_and_sources_preserved():
    seal = read('execution_seal.json')
    protocol = read('protocol.json')
    bindings = {**seal['bound_sha256'], **protocol['protected_sha256'], **protocol['implementation_sha256']}
    for key, expected in bindings.items():
        with Path(key).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected, key
    assert read('protocol_seal.json')['sha256'] == hashlib.sha256((DOC/'protocol.json').read_bytes()).hexdigest()
    assert seal['source_unchanged'] and read('protocol_seal.json')['sealed_before_energy']


def test_actual_cost_and_scope_not_promoted():
    result = read('results.json')
    assert result['native_peak_rss_kib'] == max(x['process']['measurement']['peak_rss_kib'] for x in result['points'])
    assert result['total_execution_wall_seconds'] >= sum(x['process']['outer_wall_seconds'] for x in result['points'])
    assert result['JC_runs'] == result['extra_geometries'] == 0
    assert result['NOT_CERTIFIED'] and result['NOT_PRODUCTION_APPROVED']
    assert not result['nuclear_motion_implemented'] and not result['analytic_force']
    assert result['F14_acceptance_tolerance'] is None
