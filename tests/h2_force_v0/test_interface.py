"""Synthetic counterexamples: fail closed and preserve radial-force signs."""
from copy import deepcopy
import pytest
from electronic_pilot.h2_force_v0.interface import GRID, GUARDS, analyze


def rows():
    # E=(R-1.4)^2 gives exactly known central derivative -2(R-1.4).
    return [dict(R_decimal=r, R_bohr=float(r), total_energy_hartree=e,
                 accepted=True, failure_stage=None, basis='cc-pV5Z',
                 basis_size=110, singlet_dimension=6105, mode='AO_and_MO_integral_reuse',
                 guards=deepcopy(GUARDS), arithmetic='IEEE binary64', driver='evr',
                 energy_convention='EBO=Ee+1/R', Smin=1e-5, orthogonality_l2=1e-14,
                 singlet_asymmetry=1e-14, eigen_residual_l2=1e-13, vector_norm_error=1e-15)
            for r, e in zip(GRID, (.04, .01, 0., .01, .04))]


def test_radial_sign_units_and_no_f14_tolerance():
    result = analyze(rows())
    assert result['forces'][0]['force_Eh_per_bohr'] == pytest.approx(.2)
    assert result['forces'][1]['force_Eh_per_bohr'] == 0
    assert result['forces'][2]['force_Eh_per_bohr'] == pytest.approx(-.2)
    assert result['classification'] == ['H2_LOCAL_BO_CURVE_SUPPORTED', 'H2_FORCE_INTERFACE_PILOT_SUPPORTED']
    assert result['F14_acceptance_tolerance'] is None
    assert result['NOT_CERTIFIED'] and result['NOT_PRODUCTION_APPROVED']


@pytest.mark.parametrize('key,bad', [('Smin', 1e-10), ('orthogonality_l2', 2e-10),
    ('singlet_asymmetry', 2e-10), ('eigen_residual_l2', 2e-9), ('vector_norm_error', 2e-10),
    ('eigen_residual_l2', float('nan')), ('total_energy_hartree', float('inf')),
    ('vector_norm_error', None), ('orthogonality_l2', -1.), ('accepted', False),
    ('basis', 'cc-pVQZ'), ('mode', 'AO_reuse_only'), ('singlet_dimension', 6104),
    ('guards', {}), ('arithmetic', 'HP'), ('energy_convention', 'Ee only')])
def test_false_acceptance_is_refused(key, bad):
    table = rows()
    table[2][key] = bad
    result = analyze(table)
    assert result['classification'] == ['H2_FORCE_VERTICAL_SLICE_BLOCKED']
    assert result['first_blocker']['R_decimal'] == '1.4'
    assert all(f['force_Eh_per_bohr'] is None for f in result['forces'])


def test_missing_point_is_not_estimated():
    result = analyze(rows()[:2])
    assert result['refused_points']['1.4'] == 'NOT_EVALUATED'
    assert result['local_minimum'] is None
    assert all(f['force_Eh_per_bohr'] is None for f in result['forces'])


@pytest.mark.parametrize('mutation', ['extra', 'duplicate', 'geometry'])
def test_grid_identity(mutation):
    table = rows()
    if mutation == 'extra': table[0]['R_decimal'] = '1.1'
    elif mutation == 'duplicate': table.append(table[0])
    else: table[0]['R_bohr'] = 1.3
    with pytest.raises(ValueError): analyze(table)


def test_reversed_energy_order_and_force_sign_are_blockers():
    table = rows()
    for row in table: row['total_energy_hartree'] *= -1
    result = analyze(table)
    assert result['first_blocker']['reason'] == 'local_minimum_structure_failed'
    assert not any(result['force_signs'].values())


def test_no_invented_near_zero_force_tolerance():
    table = rows()
    table[1]['total_energy_hartree'] = .001
    table[3]['total_energy_hartree'] = .039
    result = analyze(table)
    assert result['forces'][1]['force_Eh_per_bohr'] == pytest.approx(-.19)
    assert result['classification'][1] == 'H2_FORCE_INTERFACE_PILOT_SUPPORTED'


def test_empty_campaign_remains_blocked():
    assert analyze([])['first_blocker'] == dict(R_decimal='1.2', reason='NOT_EVALUATED')
