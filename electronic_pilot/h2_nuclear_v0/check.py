"""Independent exact-rational replay of scalar equations and stored geometry.

Does not import scalar propagation or electronic calculator code. The 1e-75
bound checks Decimal80 arithmetic only, never physical energy conservation.
"""
import math
from fractions import Fraction as Q

ROUNDING_BOUND = Q(1, 10**75)


def exact(value):
    if isinstance(value, bool): raise ValueError('bool scalar')
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError('nonfinite scalar')
        return Q.from_float(value)
    return Q(value)


def electronic(row):
    if row.get('accepted') is not True or row.get('failure_stage') is not None:
        raise ValueError('REFUSED')
    if (row.get('basis'), row.get('mode'), row.get('basis_size'), row.get('singlet_dimension'),
        row.get('arithmetic'), row.get('driver'), row.get('energy_convention')) != (
        'cc-pV5Z','AO_and_MO_integral_reuse',110,6105,'IEEE binary64','evr','EBO=Ee+1/R'):
        raise ValueError('calculator contract')
    expected = dict(Smin_floor=1e-10,orth_l2_max=1e-10,H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10)
    if row.get('guards') != expected: raise ValueError('guard contract')
    if exact(row['Smin']) <= exact(1e-10): raise ValueError('overlap')
    for key, limit in [('orthogonality_l2',1e-10),('singlet_asymmetry',1e-10),
                       ('eigen_residual_l2',1e-9),('vector_norm_error',1e-10)]:
        if not 0 <= exact(row[key]) <= exact(limit): raise ValueError('guard '+key)
    return exact(row['total_energy_hartree'])


def check(result, reused, new, mass_literal):
    initial = result['initial']
    if (initial['R0'],initial['P0'],initial['dt'],initial['h'],initial['precision']) != ('1.5','0','1','0.1',80):
        raise ValueError('one-step contract')
    if exact(initial['m_p']) != exact(mass_literal): raise ValueError('mass')
    e14,e0,e16 = [electronic(x) for x in reused]
    if [x['R_decimal'] for x in reused] != ['1.4','1.5','1.6']: raise ValueError('reused geometry')
    mass=exact(mass_literal); mu=mass/2
    if exact(initial['mu']) != mu or mass<=0: raise ValueError('reduced mass')
    f0=(e14-e16)*5
    ph=f0/2
    r1=Q(3,2)+ph/mu
    values={'F0':(initial['F0'],f0),'P_half':(initial['P_half'],ph),
            'requested_R1':(initial['requested_R1'],r1)}
    for label,row in zip(('left','center','right'),new):
        requested=exact(initial['requested_geometries'][label])
        offset={'left':-Q(1,10),'center':Q(0),'right':Q(1,10)}[label]
        if abs(requested-(r1+offset))>ROUNDING_BOUND: raise ValueError('requested stencil')
        if exact(row['requested_R']) != requested: raise ValueError('geometry mix')
        g=row['geometry']; actual=g['actual_serialized_R']
        if actual != float(requested) or g['actual_R_hex'] != actual.hex(): raise ValueError('serialized R')
        z=g['positions_bohr']
        if z != row['actual_stored_positions_bohr'] or z != [[0.,0.,-actual/2],[0.,0.,actual/2]]:
            raise ValueError('stored positions')
        if exact(z[0][2])+exact(z[1][2]) != 0: raise ValueError('actual COM')
        if exact(g['actual_R_exact_decimal']) != exact(actual): raise ValueError('stored exact R')
        if abs(exact(g['R_rounding_delta'])-(exact(actual)-requested))>ROUNDING_BOUND:
            raise ValueError('rounding hidden')
    el,e1,er=[electronic(x) for x in new]
    f1=(el-er)*5
    p1=(f0+f1)/2
    k1=p1*p1/mass
    h1=e1+k1
    values.update(F1=(result['F1'],f1),P1=(result['P1'],p1),K1=(result['K1'],k1),
                  H1=(result['H1'],h1),delta_H=(result['delta_H'],h1-e0))
    errors={key:abs(exact(got)-want) for key,(got,want) in values.items()}
    if any(x>ROUNDING_BOUND for x in errors.values()): raise ValueError('scalar arithmetic')
    nuclei=result['nuclei']
    if exact(nuclei['p_A']) != -exact(result['P1']) or exact(nuclei['p_B']) != exact(result['P1']):
        raise ValueError('individual momentum sign')
    if exact(nuclei['p_A'])+exact(nuclei['p_B']) != 0: raise ValueError('momentum conservation')
    if exact(nuclei['z_A'])+exact(nuclei['z_B']) != 0: raise ValueError('COM conservation')
    if abs(exact(nuclei['z_B'])-exact(nuclei['z_A'])-r1)>ROUNDING_BOUND: raise ValueError('individual R')
    if exact(initial['K0']) != 0 or exact(initial['H0']) != e0: raise ValueError('initial energy')
    if not (f0<0 and ph<0 and r1<Q(3,2) and f1<0 and p1<0): raise ValueError('direction')
    if result['executed_steps'] != 1 or result['energy_diagnostic_status']!='MEASURED' or result['energy_conservation_tolerance'] is not None:
        raise ValueError('scope promotion')
    return dict(status='SCALAR_AND_GEOMETRY_REPLAY_PASS',method='independent exact Fraction equations from stored binary64 energy / nominal mass',
                arithmetic_only_bound='1e-75; not a deltaH tolerance',
                exact_scalar_errors={k:[v.numerator,v.denominator] for k,v in errors.items()},
                force_error_bound=False,external_independent_audit=False)
