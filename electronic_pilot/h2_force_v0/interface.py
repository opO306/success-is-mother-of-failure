"""Fail-closed consumer of the five predeclared accepted BO energies.

F is the generalized radial force -dE/dR, in Eh/bohr. It is not a
three-dimensional force evaluator, analytic gradient, or dynamics approval.
"""
import math
from fractions import Fraction

GRID = ('1.2', '1.3', '1.4', '1.5', '1.6')
H = Fraction('0.1')
BASIS = 'cc-pV5Z'
MODE = 'AO_and_MO_integral_reuse'
GUARDS = dict(Smin_floor=1e-10, orth_l2_max=1e-10, H_asym_max=1e-10,
              eigen_l2_max=1e-9, norm_max=1e-10)


def refusal(row):
    if row.get('accepted') is not True or row.get('failure_stage') is not None:
        return 'numerical_guard_refused'
    if (row.get('basis') != BASIS or row.get('mode') != MODE
            or row.get('basis_size') != 110 or row.get('singlet_dimension') != 6105
            or row.get('guards') != GUARDS or row.get('arithmetic') != 'IEEE binary64'
            or row.get('driver') != 'evr' or row.get('energy_convention') != 'EBO=Ee+1/R'):
        return 'calculator_contract_mismatch'
    for key in ('Smin', 'orthogonality_l2', 'singlet_asymmetry',
                'eigen_residual_l2', 'vector_norm_error', 'total_energy_hartree'):
        value = row.get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            return 'missing_or_nonfinite_' + key
    if row['Smin'] <= GUARDS['Smin_floor']:
        return 'overlap_floor'
    for key, threshold in (('orthogonality_l2', 'orth_l2_max'),
                           ('singlet_asymmetry', 'H_asym_max'),
                           ('eigen_residual_l2', 'eigen_l2_max'),
                           ('vector_norm_error', 'norm_max')):
        if row[key] < 0 or row[key] > GUARDS[threshold]:
            return key
    return None


def analyze(rows):
    indexed = {}
    for row in rows:
        r = row.get('R_decimal')
        if r not in GRID or r in indexed:
            raise ValueError('unexpected or duplicate geometry')
        if row.get('R_bohr') != float(r):
            raise ValueError('geometry mismatch')
        indexed[r] = row
    refused = {r: 'NOT_EVALUATED' if r not in indexed else refusal(indexed[r]) for r in GRID}
    refused = {r: reason for r, reason in refused.items() if reason is not None}
    energies = {r: Fraction.from_float(float(row['total_energy_hartree']))
                for r, row in indexed.items() if r not in refused}
    forces = []
    for r, left, right in (('1.3', '1.2', '1.4'), ('1.4', '1.3', '1.5'), ('1.5', '1.4', '1.6')):
        # Also require the centre to be accepted: no force at a refused geometry.
        bad = [x for x in (left, r, right) if x not in energies]
        if bad:
            forces.append(dict(R_decimal=r, status='REFUSED', force_Eh_per_bohr=None, missing_or_refused=bad))
        else:
            f = -(energies[right] - energies[left]) / (2 * H)
            forces.append(dict(R_decimal=r, status='DIAGNOSTIC_NOT_CERTIFIED',
                               force_Eh_per_bohr=float(f), exact_from_stored_binary64=[f.numerator, f.denominator],
                               left_R=left, right_R=right, h_bohr='0.1'))
    local = None if any(r not in energies for r in ('1.3', '1.4', '1.5')) else dict(
        E14_lt_E13=energies['1.4'] < energies['1.3'], E14_lt_E15=energies['1.4'] < energies['1.5'])
    signs = dict(F13_positive=None if forces[0]['force_Eh_per_bohr'] is None else forces[0]['force_Eh_per_bohr'] > 0,
                 F15_negative=None if forces[2]['force_Eh_per_bohr'] is None else forces[2]['force_Eh_per_bohr'] < 0)
    supported = not refused and local is not None and all(local.values()) and all(signs.values())
    blocker = next((dict(R_decimal=r, reason=refused[r]) for r in GRID if r in refused), None)
    if blocker is None and not supported:
        blocker = dict(reason='local_minimum_structure_failed' if not all(local.values()) else 'force_sign_failed')
    return dict(classification=['H2_LOCAL_BO_CURVE_SUPPORTED', 'H2_FORCE_INTERFACE_PILOT_SUPPORTED'] if supported
                else ['H2_FORCE_VERTICAL_SLICE_BLOCKED'], refused_points=refused, first_blocker=blocker,
                local_minimum=local, force_signs=signs, forces=forces,
                F14_acceptance_tolerance=None, NOT_CERTIFIED=True, NOT_PRODUCTION_APPROVED=True,
                analytic_force=False, rigorous_force_error_bound=False, nuclear_motion=False,
                continuity='five samples only; no interval/global continuity certification')
