"""Classical orbiting (barrier-top circular orbit) for the bench potentials, from the effective potential only.

At the barrier top: V_eff'(r*) = 0 -> L^2 = mu r*^3 V'(r*), and V_eff(r*) = E -> V(r*) + r* V'(r*)/2 = E.
g(r) = V + r V'/2 rises from -De at the well minimum to E_max and decays to 0+; for 0 < E < E_max it has an inner
and an outer root. The orbiting radius is the root where the circular orbit is UNSTABLE: V'' + 3 V'/r < 0.
"""
import mpmath as mm

from .potentials import RE


def g(pot, r):
    return pot.V(r) + r * pot.dV(r) / 2


def e_max(pot, lo=None, hi=40):
    lo = mm.mpf(lo or RE)
    return mm.findroot(lambda r: mm.diff(lambda x: g(pot, x), r), (lo + 1, lo + 4), solver='anderson') if False else \
        max(g(pot, lo + (hi - lo) * mm.mpf(k) / 4000) for k in range(1, 4000))


def orbit(pot, mu, E, lo=None, hi=40, n=4000):
    """Return dict(r_star, L, b_orb) for 0 < E < E_max, choosing the unstable root (fail closed otherwise)."""
    lo, hi, E = mm.mpf(lo or RE), mm.mpf(hi), mm.mpf(E)
    rs = [lo + (hi - lo) * mm.mpf(k) / n for k in range(n + 1)]
    roots = []
    for a, b in zip(rs, rs[1:]):
        fa, fb = g(pot, a) - E, g(pot, b) - E
        if fa == 0 or fa * fb < 0:
            for _ in range(mm.mp.prec + 20):
                m = (a + b) / 2
                if (g(pot, m) - E) * fa > 0: a = m
                else: b = m
            roots.append((a + b) / 2)
    unstable = [r for r in roots if pot.d2V(r) + 3 * pot.dV(r) / r < 0]
    if len(unstable) != 1:
        raise ValueError(f'expected one unstable circular orbit, found {len(unstable)} of {len(roots)} roots')
    r = unstable[0]
    L = mm.sqrt(mu * r ** 3 * pot.dV(r))
    return dict(r_star=r, L=L, b_orb=L / mm.sqrt(2 * mu * E))
