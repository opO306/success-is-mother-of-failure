"""Decimal80 relative-coordinate velocity Verlet, fixed one-step contract.

R=zB-zA, zA=-R/2,zB=R/2. K=m/2*(Rdot/2)^2*2
=m*Rdot^2/4=mu*Rdot^2/2, mu=m/2. P=dK/dRdot=mu*Rdot,
so individual momenta are pA=m*(-Rdot/2)=-P and pB=P.
Only scalar propagation uses Decimal80; electronic data remain binary64.
"""
from decimal import Decimal as D, localcontext
import math
from electronic_pilot.h2_force_v0.interface import refusal

PRECISION = 80
R0, P0, DT, H = '1.5', '0', '1', '0.1'


def finite(value):
    if isinstance(value, (float, int)):
        if isinstance(value, bool) or not math.isfinite(value):
            raise ValueError('nonfinite/bool scalar')
        return D.from_float(value) if isinstance(value, float) else D(value)
    if not isinstance(value, (str, D)):
        raise ValueError('scalar type')
    out = D(value)
    if not out.is_finite():
        raise ValueError('nonfinite scalar')
    return out


def energy(row):
    if refusal(row) is not None:
        raise ValueError('REFUSED electronic energy')
    return finite(row['total_energy_hartree'])


def force(left, right):
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return -(energy(right) - energy(left)) / (2 * D(H))


def individual(r, p):
    with localcontext() as ctx:
        ctx.prec = PRECISION
        r, p = finite(r), finite(p)
        return dict(z_A=str(-r/2), z_B=str(r/2), p_A=str(-p), p_B=str(p),
                    COM_position=str((-r/2+r/2)/2), total_momentum=str(-p+p))


def start(e14, e15, e16, mass_literal):
    if [x.get('R_decimal') for x in (e14, e15, e16)] != ['1.4', '1.5', '1.6']:
        raise ValueError('reused geometry identity mismatch')
    with localcontext() as ctx:
        ctx.prec = PRECISION
        mass = finite(mass_literal)
        if mass <= 0:
            raise ValueError('nonpositive proton mass')
        mu = mass/2
        e0 = energy(e15)
        f0 = force(e14, e16)
        ph = D(P0) + D(DT)/2*f0
        r1 = D(R0) + D(DT)*ph/mu
        if not f0 < 0 or not ph < 0 or not 0 < r1 < D(R0):
            raise ValueError('initial direction blocker')
        return dict(precision=PRECISION, m_p=str(mass), mu=str(mu), R0=R0, P0=P0, dt=DT, h=H,
                    E0=str(e0), F0=str(f0), P_half=str(ph), requested_R1=str(r1),
                    K0='0', H0=str(e0), initial_nuclei=individual(D(R0), D(P0)),
                    drift_nuclei=individual(r1, ph),
                    requested_geometries={'left':str(r1-D(H)), 'center':str(r1), 'right':str(r1+D(H))})


def finish(initial, left, center, right):
    if initial.get('precision') != PRECISION or (initial.get('R0'), initial.get('P0'), initial.get('dt'), initial.get('h')) != (R0, P0, DT, H):
        raise ValueError('step contract mismatch')
    for label, row in zip(('left', 'center', 'right'), (left, center, right)):
        if row.get('requested_R') != initial['requested_geometries'][label]:
            raise ValueError('new geometry identity mismatch')
        energy(row)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        f1 = force(left, right)
        p1 = finite(initial['P_half']) + D(DT)/2*f1
        r1 = finite(initial['requested_R1'])
        mu = finite(initial['mu'])
        k1 = p1*p1/(2*mu)
        h1 = energy(center) + k1
        nuclei = individual(r1, p1)
        invariants = dict(COM_unchanged=D(nuclei['COM_position']) == 0,
                          total_nuclear_momentum_zero=D(nuclei['total_momentum']) == 0)
        signs = dict(F0_negative=finite(initial['F0']) < 0, P_half_negative=finite(initial['P_half']) < 0,
                     R1_lt_R0=r1 < D(R0), F1_negative=f1 < 0, P1_negative=p1 < 0)
        if not all(invariants.values()) or not all(signs.values()):
            raise ValueError('final direction/invariant blocker')
        return dict(classification='H2_BO_NUCLEAR_1STEP_SUPPORTED', initial=initial,
                    F1=str(f1), P1=str(p1), R1_requested=str(r1), R1_actual=center['geometry'],
                    nuclei=nuclei, invariants=invariants, signs=signs,
                    E1=str(energy(center)), K1=str(k1), H1=str(h1), delta_H=str(h1-finite(initial['H0'])),
                    energy_diagnostic_status='MEASURED', energy_conservation_tolerance=None,
                    energy_geometry_note='E1 evaluated at serialized binary64 R1; scalar R1 retained at Decimal80; discrepancy explicitly recorded',
                    executed_steps=1, NOT_CERTIFIED=True, NOT_PRODUCTION_APPROVED=True)


def geometry(requested):
    requested = finite(requested)
    r = float(requested)
    if not math.isfinite(r) or r <= 0:
        raise ValueError('invalid electronic geometry')
    z = [-r/2, r/2]
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return dict(requested_R=str(requested), actual_serialized_R=r,
                    actual_R_exact_decimal=str(D.from_float(r)), actual_R_hex=r.hex(),
                    R_rounding_delta=str(D.from_float(r)-requested),
                    positions_bohr=[[0.,0.,z[0]],[0.,0.,z[1]]],
                    z_exact_decimal=[str(D.from_float(x)) for x in z], z_hex=[x.hex() for x in z],
                    actual_COM_position=0., actual_internuclear_R=z[1]-z[0])
