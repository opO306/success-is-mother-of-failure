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
