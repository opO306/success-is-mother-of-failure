"""Continuous-number KDK and analytic Lang derivative, separately implemented.

Only public decimal specification parsing/constants are shared with O-1.
No fixed-point projection, rounding helpers, reference force or replay imports.
"""
import mpmath as m
from c1b1_o1.model import parse


class Lang:
    def __init__(self):
        self.p = {k: [m.mpf(x) for x in xs] for k, xs in parse().items()}

    def value_derivative(self, r):
        p = self.p
        v, dv = m.mpf(0), m.mpf(0)
        for name, imin, kmin, kadd in [('BO', -1, 3, 1), ('REL', 0, 2, 0), ('QED', 0, 3, 0)]:
            a = p['a_'+name]; count = len(a)//2
            for j, alpha in enumerate(p['alpha_'+name]):
                poly = sum(a[j*count+i]*r**(imin+i) for i in range(count))
                deriv = sum((imin+i)*a[j*count+i]*r**(imin+i-1) for i in range(count) if imin+i)
                exponential = m.exp(-alpha*r)
                v += exponential*poly
                dv += exponential*(deriv-alpha*poly)
            eta = p['eta_'+name][0]; x = eta*r; exponential = m.exp(-x)
            for i, coef in enumerate(p['C_'+name]):
                n = 2*(kmin+i)+kadd
                term = series = m.mpf(1)
                for j in range(1, n+1):
                    term *= x/j; series += term
                damping = 1-exponential*series
                ddamping = eta*exponential*term
                if i == 0 and name == 'BO':
                    num = 1+sum(a*r**(j+1) for j, a in enumerate(p['A']))
                    den = 1+sum(b*r**(j+1) for j, b in enumerate(p['B']))
                    dn = sum((j+1)*a*r**j for j, a in enumerate(p['A']))
                    dd = sum((j+1)*b*r**j for j, b in enumerate(p['B']))
                    damping += num/den-1
                    ddamping += (dn*den-num*dd)/(den*den)
                if i == 0 and name == 'REL':
                    damping -= 1
                power = 2*(kmin+i)
                v -= coef*damping/r**power
                dv -= coef*(ddamping/r**power-power*damping/r**(power+1))
        return v, dv


def relative(raw):
    if len(raw) != 12 or any(raw[i] for i in (2, 5, 8, 11)):
        raise ValueError('diagnostic requires the sealed planar raw state')
    return ([m.mpf(raw[i+6]-raw[i])/2**48 for i in range(2)],
            [m.mpf(raw[i+9]-raw[i+3])/2**81 for i in range(2)])


def step(q, p, dt, mu, force):
    f = force(q)
    half = [p[i]+dt*f[i]/2 for i in range(len(q))]
    out = [q[i]+dt*half[i]/mu for i in range(len(q))]
    f = force(out)
    return out, [half[i]+dt*f[i]/2 for i in range(len(q))]


def angle_difference(a, b):
    return abs(m.atan2(m.sin(a-b), m.cos(a-b)))


def isolate(continuous, hp, production, precision_change):
    if not all(m.isfinite(x) for x in (continuous, hp, production, precision_change)) or precision_change > m.mpf('1e-20'):
        return dict(verdict='UNRESOLVED_STOP')
    hp_a = angle_difference(hp, production)
    hp_c = angle_difference(hp, continuous)
    a_c = angle_difference(production, continuous)
    verdict = 'UNRESOLVED_STOP'
    if hp_a <= m.mpf('1e-8') and hp_c > m.mpf('1e-5') and hp_c >= 100*hp_a:
        verdict = 'TIME_DISCRETIZATION_SUPPORTED'
    elif hp_c <= m.mpf('1e-8') and a_c > m.mpf('1e-5'):
        verdict = 'FIXED_POINT_SUPPORTED_STOP'
    return dict(verdict=verdict, hp_vs_A=m.nstr(hp_a, 35), hp_vs_continuous=m.nstr(hp_c, 35), A_vs_continuous=m.nstr(a_c, 35))
