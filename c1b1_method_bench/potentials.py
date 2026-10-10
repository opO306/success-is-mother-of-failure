"""Bench potentials with analytic V, V', V'' (T1 free, T2 alpha/r^2, T3 alpha/r). Energies in hartree."""
import mpmath as mm

DE = mm.mpf('0.000451995775')          # Ar2 well depth (hartree), only as an energy scale for the bench
MU = mm.mpf(399623831237000000) / 5485799090441 / 2   # reduced mass of 40Ar2 (m_e)


class Free:
    name = 'T1_free'
    def V(self, r): return mm.mpf(0)
    def dV(self, r): return mm.mpf(0)
    def d2V(self, r): return mm.mpf(0)


class InvSquare:
    """V = alpha / r^2, alpha > 0 (repulsive)."""
    name = 'T2_inv_square'
    def __init__(self, alpha=49 * DE):
        self.alpha = mm.mpf(alpha)
    def V(self, r): return self.alpha / r ** 2
    def dV(self, r): return -2 * self.alpha / r ** 3
    def d2V(self, r): return 6 * self.alpha / r ** 4


class Coulomb:
    """V = alpha / r, alpha > 0 (repulsive, Rutherford)."""
    name = 'T3_coulomb'
    def __init__(self, alpha=7 * DE):
        self.alpha = mm.mpf(alpha)
    def V(self, r): return self.alpha / r
    def dV(self, r): return -self.alpha / r ** 2
    def d2V(self, r): return 2 * self.alpha / r ** 3


def force(pot, q):
    r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
    c = -pot.dV(r) / r
    return [c * q[0], c * q[1]]


def gradient_force(pot, q, h, mu):
    """F + h^2/(48 mu) grad|F|^2 for a central force: grad|F|^2 = 2 V' V'' q / r."""
    r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
    d1 = pot.dV(r)
    c = -d1 / r + h * h * d1 * pot.d2V(r) / (24 * mu * r)
    return [c * q[0], c * q[1]]


class ExpWall:
    """T4: V = A exp(-beta r), a steep repulsive wall (Born-Mayer type) for the high-energy pre-study.
    Defaults: beta = 2 / bohr, V(6.3 bohr) = 1 De; no closed form, reference is c1b1_method_bench.quadref."""
    name = 'T4_exp_wall'
    def __init__(self, beta=2, r_one_de='6.3'):
        self.beta = mm.mpf(beta)
        self.A = DE * mm.exp(self.beta * mm.mpf(r_one_de))
    def V(self, r): return self.A * mm.exp(-self.beta * r)
    def dV(self, r): return -self.beta * self.V(r)
    def d2V(self, r): return self.beta ** 2 * self.V(r)


RE = mm.mpf(71129) / 10000             # Ar2 equilibrium distance scale (bohr), bench only


class Morse:
    """T5: V = De[(1 - e^{-a(r-Re)})^2 - 1], well + wall + classical orbiting (a = 0.85 / bohr)."""
    name = 'T5_morse'
    def __init__(self, a='0.85'):
        self.a = mm.mpf(a)
    def _y(self, r): return mm.exp(-self.a * (r - RE))
    def V(self, r):
        y = self._y(r)
        return DE * (y * y - 2 * y)
    def dV(self, r):
        y = self._y(r)
        return 2 * self.a * DE * (y - y * y)
    def d2V(self, r):
        y = self._y(r)
        return 2 * self.a ** 2 * DE * (2 * y * y - y)


class LennardJones:
    """T6: V = 4 De [(s/r)^12 - (s/r)^6], minimum at Re (s = Re / 2^(1/6)); well, wall, orbiting, r^-6 tail."""
    name = 'T6_lennard_jones'
    def __init__(self):
        self.s = RE / mm.root(2, 6)
    def V(self, r):
        x = (self.s / r) ** 6
        return 4 * DE * (x * x - x)
    def dV(self, r):
        x = (self.s / r) ** 6
        return 4 * DE * (-12 * x * x + 6 * x) / r
    def d2V(self, r):
        x = (self.s / r) ** 6
        return 4 * DE * (156 * x * x - 42 * x) / (r * r)
