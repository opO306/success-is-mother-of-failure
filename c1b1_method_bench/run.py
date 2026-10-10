"""Run one bench trajectory and compare it with the closed form at the integrator's own exit radius."""
import mpmath as mm

from . import exact, quadref
from .methods import METHODS
from .potentials import Coulomb, ExpWall, Free, InvSquare, MU

R0 = 20
MAX_STEPS = 2_000_000


def reference(pot, mu, E, L, r1):
    if isinstance(pot, Free):
        return exact.free(mu, E, L, R0, r1)
    if isinstance(pot, InvSquare):
        return exact.inv_square(pot.alpha, mu, E, L, R0, r1)
    if isinstance(pot, Coulomb):
        return exact.coulomb(pot.alpha, mu, E, L, R0, r1)
    return quadref.reference(pot, mu, E, L, r1)          # no closed form: independent radial quadrature


def signed_angle(a, b):
    return mm.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])


def initial(pot, mu, E, b):
    """Total energy E (hartree), impact parameter b defined by L = b sqrt(2 mu E) (V -> 0 at infinity)."""
    L = b * mm.sqrt(2 * mu * E)
    pt = L / R0
    pr2 = 2 * mu * (E - pot.V(mm.mpf(R0))) - pt * pt
    if pr2 <= 0:
        raise ValueError('no inbound state at R0')
    return [mm.mpf(R0), mm.mpf(0)], [-mm.sqrt(pr2), pt], L


class Counting:
    """Counts V' (force) and V'' (force-gradient) evaluations of a potential, as implemented (no reuse)."""
    def __init__(self, pot):
        self.pot, self.name, self.n1, self.n2 = pot, pot.name, 0, 0
    def V(self, r): return self.pot.V(r)
    def dV(self, r):
        self.n1 += 1
        return self.pot.dV(r)
    def d2V(self, r):
        self.n2 += 1
        return self.pot.d2V(r)


def run(pot, method, E, b, h, dps=40, mu=MU, step=None, max_steps=MAX_STEPS):
    """step overrides the method function (fault injection in tests, adaptive tolerances)."""
    base, pot = pot, Counting(pot)
    with mm.workdps(dps):
        E, b, h = mm.mpf(E), mm.mpf(b), mm.mpf(h)
        q, p, L = initial(pot, mu, E, b)
        advance = step or METHODS[method]
        H0 = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + pot.V(mm.sqrt(q[0] ** 2 + q[1] ** 2))
        p0, sweep, n, rmin, dH = p[:], mm.mpf(0), 0, mm.mpf(R0), mm.mpf(0)
        while True:
            q_old = q
            q, p = advance(pot, q, p, h, mu)
            n += 1
            sweep += signed_angle(q_old, q)
            r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
            rmin = min(rmin, r)
            H = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + pot.V(r)
            dH = max(dH, abs(H - H0))
            if r >= R0 and q[0] * p[0] + q[1] * p[1] > 0:
                break
            if n >= max_steps:
                return dict(status='max_steps', steps=n)
        n_force, n_grad = pot.n1 - pot.n2, pot.n2
        ref = reference(base, mu, E, L, r)
        chi, chi_ref = signed_angle(p0, p), signed_angle(p0, ref['p_out'])
        return dict(status='ok', pot=pot.name, method=method, E_over_De=float(E / mm.mpf('0.000451995775')),
                    b=float(b), h=float(h), steps=n, r_exit=mm.nstr(r, 20),
                    err_chi=float(abs(chi - chi_ref)), err_sweep=float(abs(sweep - ref['sweep'])),
                    err_time=float(abs(n * h - ref['time']) / ref['time']),
                    rmin_endpoint=float(rmin), r_turn=float(ref['r_turn']), max_dH_over_E=float(dH / E),
                    d_sweep=float(sweep - ref['sweep']), d_time=float(n * h - ref['time']),
                    n_force=n_force, n_grad=n_grad, q0=[mm.nstr(x, 45) for x in initial(base, mu, E, b)[0]],
                    p0=[mm.nstr(x, 45) for x in initial(base, mu, E, b)[1]],
                    chi=mm.nstr(chi, 25), sweep=mm.nstr(sweep, 25))
