"""Lang 2024 Ar2 jet in integer fixed point, second version (cost plan C1.1, survey_only).

Same formula, parameters and output contract as c1b1_t7.lang_fx.LangForceFX (kept unchanged: it is the version the
T7 bit-identity replay checked). C1.1 changes only how the same numbers are computed:
  * the nine exponentials call mpmath's low-level mpf_exp on (sign, man, exp, bc) tuples (no mpf objects), rounded
    toward -inf at P + EXP_GUARD bits, then floor-shifted to the 2^-P grid;
  * the fixed-point products are written inline ((a * b) >> P) instead of through a lambda;
  * EXTRA_BITS = 96 instead of 160 (the value test checks |error| <= 2^-(W - 5) max(1, |value|)).
"""
from fractions import Fraction

import mpmath as mm
from mpmath.libmp import from_man_exp, mpf_exp, round_floor

from c1b1_o1 import model

from .lang import TERMS, pes_path

EXTRA_BITS = 96
EXP_GUARD = 16


class LangForceFX2:
    name = 'Ar2_Lang2024_fx2'

    def __init__(self, path=None):
        self.params = model.parse(path or pes_path())
        self._fixed = {}
        self._key, self._val = None, None
        self.evaluations = 0

    def _params(self, P):
        if P not in self._fixed:
            self._fixed[P] = {k: [round(Fraction(v) * (1 << P)) for v in vs] for k, vs in self.params.items()}
        return self._fixed[P]

    @staticmethod
    def _exp_neg(X, P):
        """floor(exp(-X 2^-P) 2^P) via mpf_exp at P + EXP_GUARD bits (X >= 0)."""
        s, man, ex, bc = mpf_exp(from_man_exp(-X, -P), P + EXP_GUARD, round_floor)
        sh = ex + P
        return man << sh if sh >= 0 else man >> -sh

    def jet(self, r):
        r = mm.mpf(r)
        key = (r, mm.mp.prec)
        if key == self._key:
            return self._val
        self.evaluations += 1
        P = mm.mp.prec + EXTRA_BITS
        prm = self._params(P)
        ONE = 1 << P
        man, ex = r.man_exp
        R = man << (ex + P) if ex + P >= 0 else man >> -(ex + P)
        IR = (1 << (2 * P)) // R
        pw = {0: ONE, 1: R, -1: IR}
        for m in range(2, 7):
            pw[m] = (pw[m - 1] * R) >> P
        for m in range(2, 19):
            pw[-m] = (pw[-m + 1] * IR) >> P
        exp_neg = self._exp_neg
        v = d = dd = 0
        for name, imin, kmin, kadd in TERMS:
            a = prm['a_' + name]
            count = len(a) // 2
            for j, al in enumerate(prm['alpha_' + name]):
                e = exp_neg((al * R) >> P, P)
                Pv = P1 = P2 = 0
                for i in range(count):
                    m = imin + i
                    c = a[j * count + i]
                    Pv += (c * pw[m]) >> P
                    if m:
                        P1 += (c * m * pw[m - 1]) >> P
                        if m != 1:
                            P2 += (c * m * (m - 1) * pw[m - 2]) >> P
                alP, alP1 = (al * Pv) >> P, (al * P1) >> P
                v += (e * Pv) >> P
                d += (e * (P1 - alP)) >> P
                dd += (e * (P2 - 2 * alP1 + ((al * alP) >> P))) >> P
            eta = prm['eta_' + name][0]
            x = (eta * R) >> P
            exn = exp_neg(x, P)
            cs = prm['C_' + name]
            nmax = 2 * (kmin + len(cs) - 1) + kadd
            terms, sums = [ONE], [ONE]
            for m in range(1, nmax + 1):
                terms.append(((terms[-1] * x) >> P) // m)
                sums.append(sums[-1] + terms[-1])
            eta2 = (eta * eta) >> P
            for i, coef in enumerate(cs):
                k = kmin + i
                n = 2 * k + kadd
                f = ONE - ((exn * sums[n]) >> P)
                f1 = (eta * ((exn * terms[n]) >> P)) >> P
                f2 = (eta2 * ((exn * (terms[n - 1] - terms[n])) >> P)) >> P
                if i == 0 and name == 'BO':
                    N, N1, N2 = ONE, 0, 0
                    for jj, aa in enumerate(prm['A']):
                        N += (aa * pw[jj + 1]) >> P
                        N1 += (aa * (jj + 1) * pw[jj]) >> P
                        if jj:
                            N2 += (aa * (jj + 1) * jj * pw[jj - 1]) >> P
                    D, D1, D2 = ONE, 0, 0
                    for jj, bb in enumerate(prm['B']):
                        D += (bb * pw[jj + 1]) >> P
                        D1 += (bb * (jj + 1) * pw[jj]) >> P
                        if jj:
                            D2 += (bb * (jj + 1) * jj * pw[jj - 1]) >> P
                    DD = (D * D) >> P
                    Wn = ((N1 * D) >> P) - ((N * D1) >> P)
                    f += (N << P) // D - ONE
                    f1 += (Wn << P) // DD
                    f2 += ((((N2 * D) >> P) - ((N * D2) >> P)) << P) // DD \
                        - ((2 * ((D1 * Wn) >> P)) << P) // ((DD * D) >> P)
                if i == 0 and name == 'REL':
                    f -= ONE
                g, g1, g2 = pw[-2 * k], -2 * k * pw[-2 * k - 1], 2 * k * (2 * k + 1) * pw[-2 * k - 2]
                fg = (f * g) >> P
                f1g = (f1 * g) >> P
                v -= (coef * fg) >> P
                d -= (coef * (f1g + ((f * g1) >> P))) >> P
                dd -= (coef * (((f2 * g) >> P) + 2 * ((f1 * g1) >> P) + ((f * g2) >> P))) >> P
        out = tuple(mm.ldexp(mm.mpf(z), -P) for z in (v, d, dd))
        self._key, self._val = key, out
        return out

    def V(self, r):
        return self.jet(r)[0]

    def dV(self, r):
        return self.jet(r)[1]

    def d2V(self, r):
        return self.jet(r)[2]
